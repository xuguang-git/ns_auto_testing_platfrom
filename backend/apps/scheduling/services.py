from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from kombu.exceptions import OperationalError

from apps.scheduling.models import ScheduledPlan
from apps.test_runs.models import TestRun
from apps.test_runs.tasks import run_test_plan


MAX_LOOKAHEAD_MINUTES = 366 * 24 * 60


def compute_next_run_at(cron: str, base=None):
    base = base or timezone.now()
    current = base.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(MAX_LOOKAHEAD_MINUTES):
        if _cron_matches(cron, current):
            return current
        current += timedelta(minutes=1)
    raise ValueError("Cron 表达式在未来一年内没有匹配时间")


def trigger_scheduled_plan(schedule: ScheduledPlan) -> TestRun:
    with transaction.atomic():
        schedule = (
            ScheduledPlan.objects.select_for_update()
            .select_related("environment", "plan", "plan__environment")
            .get(pk=schedule.pk)
        )
        test_run = TestRun.objects.create(
            plan=schedule.plan,
            environment=schedule.environment or schedule.plan.environment,
            trigger_type=TestRun.TriggerType.SCHEDULE,
        )
        schedule.last_run_at = timezone.now()
        schedule.last_run_id = test_run.id
        schedule.last_status = test_run.status
        schedule.run_count += 1
        schedule.next_run_at = compute_next_run_at(schedule.cron, schedule.last_run_at) if schedule.is_active else None
        schedule.save(update_fields=["last_run_at", "last_run_id", "last_status", "run_count", "next_run_at", "updated_at"])

    try:
        async_result = run_test_plan.delay(test_run.id)
        test_run.celery_task_id = async_result.id
        test_run.save(update_fields=["celery_task_id", "updated_at"])
    except OperationalError as exc:
        now = timezone.now()
        test_run.status = TestRun.Status.FAILED
        test_run.started_at = now
        test_run.finished_at = now
        test_run.error_message = f"Celery broker unavailable: {exc}"
        test_run.summary = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "pass_rate": 0}
        test_run.logs = [{"time": now.isoformat(), "level": "error", "message": test_run.error_message}]
        test_run.save(update_fields=["status", "started_at", "finished_at", "error_message", "summary", "logs", "updated_at"])
        ScheduledPlan.objects.filter(pk=schedule.pk).update(last_status=test_run.status)
    return test_run


def dispatch_due_schedules(now=None) -> int:
    now = now or timezone.now()
    due_schedules = ScheduledPlan.objects.select_related("environment", "plan", "plan__environment").filter(
        is_active=True,
        plan__is_active=True,
        next_run_at__lte=now,
    )
    count = 0
    for schedule in due_schedules:
        trigger_scheduled_plan(schedule)
        count += 1
    return count


def refresh_next_run(schedule: ScheduledPlan) -> ScheduledPlan:
    schedule.next_run_at = compute_next_run_at(schedule.cron) if schedule.is_active else None
    return schedule


def _cron_matches(cron: str, value) -> bool:
    fields = cron.split()
    if len(fields) != 5:
        raise ValueError("Cron 表达式需要 5 段：分钟 小时 日期 月份 星期")
    minute, hour, day, month, weekday = fields
    return (
        _field_matches(minute, value.minute, 0, 59)
        and _field_matches(hour, value.hour, 0, 23)
        and _field_matches(day, value.day, 1, 31)
        and _field_matches(month, value.month, 1, 12)
        and _field_matches(weekday, (value.weekday() + 1) % 7, 0, 6)
    )


def _field_matches(field: str, value: int, minimum: int, maximum: int) -> bool:
    for part in field.split(","):
        if not part:
            continue
        if _part_matches(part, value, minimum, maximum):
            return True
    return False


def _part_matches(part: str, value: int, minimum: int, maximum: int) -> bool:
    step = 1
    base = part
    if "/" in part:
        base, step_text = part.split("/", 1)
        step = int(step_text)
        if step <= 0:
            raise ValueError("Cron 步长必须大于 0")
    if base == "*":
        start, end = minimum, maximum
    elif "-" in base:
        start_text, end_text = base.split("-", 1)
        start, end = int(start_text), int(end_text)
    else:
        start = end = int(base)
    if start < minimum or end > maximum or start > end:
        raise ValueError("Cron 字段超出允许范围")
    return start <= value <= end and (value - start) % step == 0
