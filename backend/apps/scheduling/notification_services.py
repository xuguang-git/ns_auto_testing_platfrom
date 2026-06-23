from __future__ import annotations

import base64
import hashlib
import hmac
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone

from apps.scheduling.crypto import decrypt_secret
from apps.scheduling.models import NotificationChannel, NotificationSendLog, NotificationTemplate, ScheduledPlan
from apps.test_runs.models import TestRun


TEMPLATE_VARIABLES = {
    "schedule_name": "定时任务名称",
    "suite_name": "测试套件名称",
    "environment_name": "运行环境",
    "trigger_type": "触发方式",
    "status_text": "执行结果",
    "total_count": "总数",
    "passed_count": "通过数",
    "failed_count": "失败数",
    "skipped_count": "跳过数",
    "pass_rate": "通过率",
    "started_at": "开始时间",
    "finished_at": "结束时间",
    "duration": "总耗时",
    "report_url": "报告地址",
}
VARIABLE_RE = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


@dataclass
class RenderedMessage:
    title: str
    content: str


def dispatch_test_run_notifications(test_run: TestRun) -> None:
    """测试运行结束后，按定时任务配置推送消息。"""
    if not test_run.schedule_id:
        return
    schedule = (
        ScheduledPlan.objects.select_related("notification_template", "suite", "environment")
        .prefetch_related("notifications")
        .get(pk=test_run.schedule_id)
    )
    if not _should_notify(schedule, test_run):
        return
    template = schedule.notification_template
    if not template or not template.is_active:
        _write_skip_log(test_run, schedule, None, template, "未配置启用的消息模板。")
        return
    channels = [item for item in schedule.notifications.all() if item.is_active]
    if template.channel_id:
        channels = [item for item in channels if item.id == template.channel_id]
    if not channels:
        _write_skip_log(test_run, schedule, None, template, "未配置启用的消息通知。")
        return

    context = build_template_context(test_run, schedule)
    message = render_template_message(template, context)
    for channel in channels:
        send_notification(channel, template, schedule, test_run, message)


def build_template_context(test_run: TestRun, schedule: ScheduledPlan) -> dict[str, str]:
    summary = test_run.summary or {}
    status_text = "成功" if test_run.status == TestRun.Status.COMPLETED and not summary.get("failed") else "失败"
    report_url = f"{settings.FRONTEND_BASE_URL}/reports?run={test_run.id}"
    return {
        "schedule_name": schedule.name,
        "suite_name": test_run.suite.name if test_run.suite_id else "",
        "environment_name": test_run.environment.name if test_run.environment_id else "",
        "trigger_type": "定时" if test_run.trigger_type == TestRun.TriggerType.SCHEDULE else "手动",
        "status_text": status_text,
        "total_count": str(summary.get("total", 0)),
        "passed_count": str(summary.get("passed", 0)),
        "failed_count": str(summary.get("failed", 0)),
        "skipped_count": str(summary.get("skipped", 0)),
        "pass_rate": str(summary.get("pass_rate", 0)),
        "started_at": _format_dt(test_run.started_at),
        "finished_at": _format_dt(test_run.finished_at),
        "duration": _format_duration(test_run.duration_ms),
        "report_url": report_url,
    }


def render_template_message(template: NotificationTemplate, context: dict[str, str]) -> RenderedMessage:
    """按白名单变量渲染模板，未知变量保留原文，避免误替换。"""
    return RenderedMessage(
        title=_render_text(template.title_template, context),
        content=_render_text(template.content_template, context),
    )


def send_notification(
    channel: NotificationChannel,
    template: NotificationTemplate,
    schedule: ScheduledPlan,
    test_run: TestRun,
    message: RenderedMessage,
) -> NotificationSendLog:
    log = NotificationSendLog.objects.create(
        channel=channel,
        template=template,
        schedule=schedule,
        test_run=test_run,
        title=message.title,
        content=message.content,
        status=NotificationSendLog.Status.FAILED,
    )
    try:
        if channel.push_platform == NotificationChannel.PushPlatform.FEISHU:
            _send_feishu(channel, message)
        else:
            raise NotImplementedError("当前仅实现飞书推送。")
    except Exception as exc:
        log.error_message = _safe_error_message(exc)
        log.status = NotificationSendLog.Status.FAILED
    else:
        log.status = NotificationSendLog.Status.SUCCESS
        log.sent_at = timezone.now()
    log.save(update_fields=["status", "error_message", "sent_at", "updated_at"])
    return log


def _send_feishu(channel: NotificationChannel, message: RenderedMessage) -> None:
    webhook = decrypt_secret(channel.webhook_ciphertext)
    payload: dict[str, Any] = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": _strip_html(message.title),
                    "content": _html_to_feishu_post(message.content),
                }
            }
        },
    }
    if channel.signature_ciphertext:
        timestamp = str(int(time.time()))
        secret = decrypt_secret(channel.signature_ciphertext)
        payload["timestamp"] = timestamp
        payload["sign"] = _build_feishu_sign(timestamp, secret)
    response = requests.post(webhook, json=payload, timeout=10)
    response.raise_for_status()
    data = response.json()
    if data.get("code") not in (None, 0):
        raise RuntimeError(data.get("msg") or data.get("message") or "飞书推送失败")


def _build_feishu_sign(timestamp: str, secret: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(string_to_sign.encode("utf-8"), b"", digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _should_notify(schedule: ScheduledPlan, test_run: TestRun) -> bool:
    if schedule.notify_on == ScheduledPlan.NotifyOn.DISABLED:
        return False
    failed_count = int((test_run.summary or {}).get("failed") or 0)
    if schedule.notify_on == ScheduledPlan.NotifyOn.FAILED_ONLY:
        return test_run.status == TestRun.Status.FAILED or failed_count > 0
    return True


def _write_skip_log(
    test_run: TestRun,
    schedule: ScheduledPlan,
    channel: NotificationChannel | None,
    template: NotificationTemplate | None,
    reason: str,
    message: RenderedMessage | None = None,
) -> None:
    NotificationSendLog.objects.create(
        channel=channel,
        template=template,
        schedule=schedule,
        test_run=test_run,
        title=message.title if message else "",
        content=message.content if message else "",
        status=NotificationSendLog.Status.SKIPPED,
        error_message=reason,
        sent_at=timezone.now(),
    )


def _render_text(text: str, context: dict[str, str]) -> str:
    def replace(match):
        key = match.group(1)
        if key not in TEMPLATE_VARIABLES:
            return match.group(0)
        return context.get(key, "")

    return VARIABLE_RE.sub(replace, text or "")


class _FeishuPostParser(HTMLParser):
    """把平台内富文本HTML转换为飞书机器人post消息片段。"""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[list[dict[str, Any]]] = [[]]
        self.styles: list[str] = []
        self.href_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "div", "br"}:
            self._new_line()
        elif tag in {"strong", "b"}:
            self.styles.append("bold")
        elif tag in {"em", "i"}:
            self.styles.append("italic")
        elif tag == "u":
            self.styles.append("underline")
        elif tag == "a":
            href = dict(attrs).get("href") or ""
            self.href_stack.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div"}:
            self._new_line()
        elif tag in {"strong", "b"} and "bold" in self.styles:
            self.styles.remove("bold")
        elif tag in {"em", "i"} and "italic" in self.styles:
            self.styles.remove("italic")
        elif tag == "u" and "underline" in self.styles:
            self.styles.remove("underline")
        elif tag == "a" and self.href_stack:
            self.href_stack.pop()

    def handle_data(self, data: str) -> None:
        text = data.replace("\xa0", " ")
        if not text:
            return
        item: dict[str, Any] = {"tag": "text", "text": text}
        if self.href_stack and self.href_stack[-1]:
            item = {"tag": "a", "text": text, "href": self.href_stack[-1]}
        self.lines[-1].append(item)

    def result(self) -> list[list[dict[str, Any]]]:
        return [line for line in self.lines if line]

    def _new_line(self) -> None:
        if self.lines[-1]:
            self.lines.append([])


def _html_to_feishu_post(value: str) -> list[list[dict[str, Any]]]:
    parser = _FeishuPostParser()
    parser.feed(value or "")
    return parser.result() or [[{"tag": "text", "text": _strip_html(value)}]]


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value or "")
    return text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").strip()


def _format_dt(value) -> str:
    if not value:
        return ""
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M:%S")


def _format_duration(duration_ms: int) -> str:
    if duration_ms < 1000:
        return f"{duration_ms}ms"
    return f"{round(duration_ms / 1000, 2)}s"


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    message = re.sub(r"https?://\S+", "[已脱敏URL]", message)
    return message[:500] if message else "消息推送失败。"
