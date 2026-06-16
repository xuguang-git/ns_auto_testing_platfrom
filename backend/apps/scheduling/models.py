from django.db import models

from apps.core.db_comments import apply_model_comments
from apps.core.models import OwnedModel
from apps.projects.models import Environment
from apps.test_runs.models import TestPlan


class ScheduledPlan(OwnedModel):
    plan = models.ForeignKey(TestPlan, verbose_name="Test plan", on_delete=models.CASCADE, related_name="schedules")
    environment = models.ForeignKey(
        Environment,
        verbose_name="Run environment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scheduled_plans",
    )
    name = models.CharField("Schedule name", max_length=128)
    cron = models.CharField("Cron expression", max_length=128)
    is_active = models.BooleanField("Enabled", default=True)
    last_run_at = models.DateTimeField("Last run at", null=True, blank=True)
    next_run_at = models.DateTimeField("Next run at", null=True, blank=True)
    last_run_id = models.PositiveBigIntegerField("Last run ID", null=True, blank=True)
    last_status = models.CharField("Last status", max_length=16, blank=True)
    run_count = models.PositiveIntegerField("Run count", default=0)

    class Meta:
        db_table_comment = '定时任务表：按Cron定期触发测试计划执行。'
        verbose_name = "Scheduled test plan"
        verbose_name_plural = "Scheduled test plans"
        ordering = ["plan_id", "name"]

    def __str__(self) -> str:
        return self.name


apply_model_comments(ScheduledPlan, "定时任务表：按Cron定期触发测试计划执行。", {
    "plan": "关联测试计划ID。",
    "environment": "定时任务运行环境ID。",
    "name": "任务名称。",
    "cron": "Cron表达式。",
    "is_active": "是否启用。",
    "last_run_at": "最近执行时间。",
    "next_run_at": "下次预计执行时间。",
    "last_run_id": "最近执行记录ID。",
    "last_status": "最近执行状态。",
    "run_count": "累计执行次数。",
})
