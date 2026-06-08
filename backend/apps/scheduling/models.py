from django.db import models

from apps.core.models import OwnedModel
from apps.test_runs.models import TestPlan


class ScheduledPlan(OwnedModel):
    plan = models.ForeignKey(TestPlan, verbose_name="测试计划", on_delete=models.CASCADE, related_name="schedules")
    name = models.CharField("调度名称", max_length=128)
    cron = models.CharField("Cron表达式", max_length=128)
    is_active = models.BooleanField("启用", default=True)
    last_run_at = models.DateTimeField("最近运行时间", null=True, blank=True)
    next_run_at = models.DateTimeField("下次运行时间", null=True, blank=True)
    last_run_id = models.PositiveBigIntegerField("最近执行ID", null=True, blank=True)
    last_status = models.CharField("最近执行状态", max_length=16, blank=True)
    run_count = models.PositiveIntegerField("执行次数", default=0)

    class Meta:
        verbose_name = "测试调度"
        verbose_name_plural = "测试调度"
        ordering = ["plan_id", "name"]

    def __str__(self) -> str:
        return self.name
