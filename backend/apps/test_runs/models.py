from django.db import models

from apps.api_testing.models import ApiSuite
from apps.core.db_comments import apply_model_comments
from apps.core.models import TimestampedModel
from apps.projects.models import Environment


class TestRun(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class TriggerType(models.TextChoices):
        MANUAL = "manual", "Manual"
        SCHEDULE = "schedule", "Schedule"
        WEBHOOK = "webhook", "Webhook"

    suite = models.ForeignKey(ApiSuite, on_delete=models.CASCADE, related_name="runs")
    environment = models.ForeignKey(Environment, null=True, blank=True, on_delete=models.SET_NULL, related_name="runs")
    schedule = models.ForeignKey("scheduling.ScheduledPlan", null=True, blank=True, on_delete=models.SET_NULL, related_name="runs")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    trigger_type = models.CharField(max_length=16, choices=TriggerType.choices, default=TriggerType.MANUAL)
    celery_task_id = models.CharField(max_length=128, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict, blank=True)
    report = models.JSONField(default=dict, blank=True)
    logs = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table_comment = "测试执行记录表：一次测试套件运行的总记录和报告汇总。"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.suite.name}#{self.pk}"


class TestRunStep(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name="steps")
    scenario_name = models.CharField(max_length=128, blank=True)
    step_name = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    sort_order = models.PositiveIntegerField(default=0)
    request = models.JSONField(default=dict, blank=True)
    response = models.JSONField(default=dict, blank=True)
    assertions = models.JSONField(default=list, blank=True)
    logs = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(default=0)

    class Meta:
        db_table_comment = "测试执行步骤表：一次测试运行中每个接口/场景/UI步骤的结果明细。"
        ordering = ["run_id", "sort_order", "id"]

    def __str__(self) -> str:
        return self.step_name


apply_model_comments(TestRun, "测试执行记录表：一次测试套件运行的总记录和报告汇总。", {
    "suite": "关联测试套件ID。",
    "environment": "本次运行环境ID。",
    "schedule": "来源定时任务ID。",
    "status": "执行状态。",
    "trigger_type": "触发方式：手动/定时/Webhook。",
    "celery_task_id": "异步任务ID。",
    "started_at": "开始时间。",
    "finished_at": "结束时间。",
    "duration_ms": "总耗时毫秒。",
    "summary": "执行摘要JSON。",
    "report": "执行报告JSON。",
    "logs": "执行日志列表。",
    "error_message": "失败错误信息。",
})
apply_model_comments(TestRunStep, "测试执行步骤表：一次测试运行中每个接口/场景/UI步骤的结果明细。", {
    "run": "所属执行记录ID。",
    "scenario_name": "所属场景名称。",
    "step_name": "步骤名称。",
    "status": "步骤执行状态。",
    "sort_order": "步骤排序值。",
    "request": "实际请求信息。",
    "response": "实际响应信息。",
    "assertions": "断言执行结果。",
    "logs": "步骤日志列表。",
    "error_message": "步骤错误信息。",
    "duration_ms": "步骤耗时毫秒。",
})
