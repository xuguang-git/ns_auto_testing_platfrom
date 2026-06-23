from django.db import models

from apps.api_testing.models import ApiSuite
from apps.core.db_comments import apply_model_comments
from apps.core.models import OwnedModel
from apps.projects.models import Environment


class NotificationChannel(OwnedModel):
    class NotificationType(models.TextChoices):
        API_TESTING = "api_testing", "接口测试"
        UI_TESTING = "ui_testing", "UI测试"

    class PushPlatform(models.TextChoices):
        FEISHU = "feishu", "飞书"
        WECHAT_WORK = "wechat_work", "企业微信"
        DINGTALK = "dingtalk", "钉钉"

    name = models.CharField("通知名称", max_length=64, default="默认通知")
    notification_type = models.CharField("通知类型", max_length=32, choices=NotificationType.choices, default=NotificationType.API_TESTING)
    push_platform = models.CharField("推送平台", max_length=32, choices=PushPlatform.choices, default=PushPlatform.FEISHU)
    webhook_ciphertext = models.TextField("Webhook密文")
    signature_ciphertext = models.TextField("签名校验密文", blank=True)
    is_active = models.BooleanField("是否启用", default=True)

    class Meta:
        db_table_comment = "消息通知表：维护平台可复用的通知通道配置。"
        verbose_name = "消息通知"
        verbose_name_plural = "消息通知"
        ordering = ["-updated_at", "-id"]

    def __str__(self) -> str:
        return self.name


class NotificationTemplate(OwnedModel):
    class BizType(models.TextChoices):
        SCHEDULE_RUN = "schedule_run", "定时任务执行结果"

    name = models.CharField("模板名称", max_length=64)
    biz_type = models.CharField("适用业务", max_length=32, choices=BizType.choices, default=BizType.SCHEDULE_RUN)
    channel = models.ForeignKey(NotificationChannel, verbose_name="消息通知", null=True, blank=True, on_delete=models.SET_NULL, related_name="templates")
    title_template = models.CharField("标题模板", max_length=160)
    content_template = models.TextField("内容模板")
    is_active = models.BooleanField("是否启用", default=True)

    class Meta:
        db_table_comment = "消息模板表：维护不同业务场景下可复用的消息内容模板。"
        verbose_name = "消息模板"
        verbose_name_plural = "消息模板"
        ordering = ["-updated_at", "-id"]

    def __str__(self) -> str:
        return self.name


class ScheduledPlan(OwnedModel):
    class NotifyOn(models.TextChoices):
        DISABLED = "disabled", "不推送"
        ALWAYS = "always", "成功/失败都推送"
        FAILED_ONLY = "failed_only", "仅失败推送"

    suite = models.ForeignKey(ApiSuite, verbose_name="测试套件", on_delete=models.CASCADE, related_name="schedules")
    environment = models.ForeignKey(
        Environment,
        verbose_name="运行环境",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scheduled_plans",
    )
    notifications = models.ManyToManyField(NotificationChannel, verbose_name="消息通知", blank=True, related_name="scheduled_plans")
    notification_template = models.ForeignKey(
        NotificationTemplate,
        verbose_name="消息模板",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scheduled_plans",
    )
    notify_on = models.CharField("推送条件", max_length=24, choices=NotifyOn.choices, default=NotifyOn.DISABLED)
    name = models.CharField("任务名称", max_length=128)
    cron = models.CharField("Cron表达式", max_length=128)
    is_active = models.BooleanField("是否启用", default=True)
    last_run_at = models.DateTimeField("最近执行时间", null=True, blank=True)
    next_run_at = models.DateTimeField("下次执行时间", null=True, blank=True)
    last_run_id = models.PositiveBigIntegerField("最近执行记录ID", null=True, blank=True)
    last_status = models.CharField("最近执行状态", max_length=16, blank=True)
    run_count = models.PositiveIntegerField("累计执行次数", default=0)

    class Meta:
        db_table_comment = "定时任务表：按Cron定期触发测试套件执行。"
        verbose_name = "测试套件定时任务"
        verbose_name_plural = "测试套件定时任务"
        ordering = ["suite_id", "name"]

    def __str__(self) -> str:
        return self.name


class NotificationSendLog(OwnedModel):
    class Status(models.TextChoices):
        SUCCESS = "success", "成功"
        FAILED = "failed", "失败"
        SKIPPED = "skipped", "跳过"

    channel = models.ForeignKey(NotificationChannel, verbose_name="消息通知", null=True, blank=True, on_delete=models.SET_NULL, related_name="send_logs")
    template = models.ForeignKey(NotificationTemplate, verbose_name="消息模板", null=True, blank=True, on_delete=models.SET_NULL, related_name="send_logs")
    schedule = models.ForeignKey(ScheduledPlan, verbose_name="定时任务", null=True, blank=True, on_delete=models.SET_NULL, related_name="notification_logs")
    test_run = models.ForeignKey("test_runs.TestRun", verbose_name="执行记录", null=True, blank=True, on_delete=models.SET_NULL, related_name="notification_logs")
    title = models.CharField("发送标题", max_length=200)
    content = models.TextField("发送内容")
    status = models.CharField("发送状态", max_length=16, choices=Status.choices, default=Status.FAILED)
    error_message = models.TextField("失败原因", blank=True)
    retry_count = models.PositiveIntegerField("重试次数", default=0)
    sent_at = models.DateTimeField("发送时间", null=True, blank=True)

    class Meta:
        db_table_comment = "消息发送记录表：记录每次消息推送的结果和错误原因。"
        verbose_name = "消息发送记录"
        verbose_name_plural = "消息发送记录"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.channel_id or '-'}:{self.status}"


apply_model_comments(NotificationChannel, "消息通知表：维护平台可复用的通知通道配置。", {
    "name": "通知名称。",
    "notification_type": "通知类型：接口测试或UI测试。",
    "push_platform": "推送平台：飞书、企业微信或钉钉。",
    "webhook_ciphertext": "Webhook加密密文，不允许明文落库或列表返回。",
    "signature_ciphertext": "飞书签名校验密文，不允许明文落库或列表返回。",
    "is_active": "是否启用该通知通道。",
})
apply_model_comments(NotificationTemplate, "消息模板表：维护不同业务场景下可复用的消息内容模板。", {
    "name": "模板名称。",
    "biz_type": "适用业务场景。",
    "channel": "关联消息通知ID，用于界定模板实际推送通道。",
    "title_template": "标题模板，支持白名单变量。",
    "content_template": "内容模板，支持HTML富文本和白名单变量。",
    "is_active": "是否启用。",
})
apply_model_comments(ScheduledPlan, "定时任务表：按Cron定期触发测试套件执行。", {
    "suite": "关联测试套件ID。",
    "environment": "定时任务运行环境ID。",
    "notification_template": "关联消息模板ID。",
    "notify_on": "推送条件。",
    "name": "任务名称。",
    "cron": "Cron表达式。",
    "is_active": "是否启用。",
    "last_run_at": "最近执行时间。",
    "next_run_at": "下次预计执行时间。",
    "last_run_id": "最近执行记录ID。",
    "last_status": "最近执行状态。",
    "run_count": "累计执行次数。",
})
apply_model_comments(NotificationSendLog, "消息发送记录表：记录每次消息推送的结果和错误原因。", {
    "channel": "关联消息通知ID。",
    "template": "关联消息模板ID。",
    "schedule": "关联定时任务ID。",
    "test_run": "关联执行记录ID。",
    "title": "实际发送标题。",
    "content": "实际发送内容。",
    "status": "发送状态。",
    "error_message": "失败原因。",
    "retry_count": "重试次数。",
    "sent_at": "发送时间。",
})
