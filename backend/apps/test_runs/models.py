from django.db import models

from apps.api_testing.models import ApiScenario, ApiSuite
from apps.core.db_comments import apply_model_comments
from apps.core.models import OwnedModel, TimestampedModel
from apps.projects.models import Environment, Platform, Project
from apps.ui_testing.models import UiSuite


class TestPlan(OwnedModel):
    class PlanType(models.TextChoices):
        API = "api", "API"
        UI = "ui", "UI"
        MIXED = "mixed", "Mixed"

    class FailureStrategy(models.TextChoices):
        CONTINUE = "continue", "Continue"
        FAST_FAIL = "fast_fail", "Fast fail"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="test_plans")
    platform_ref = models.ForeignKey(Platform, null=True, blank=True, on_delete=models.CASCADE, related_name="test_plans")
    environment = models.ForeignKey(
        Environment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="test_plans",
    )
    name = models.CharField(max_length=128)
    plan_type = models.CharField(max_length=16, choices=PlanType.choices, default=PlanType.API)
    api_suites = models.ManyToManyField(ApiSuite, blank=True, related_name="test_plans")
    api_scenarios = models.ManyToManyField(ApiScenario, blank=True, related_name="test_plans")
    ui_suites = models.ManyToManyField(UiSuite, blank=True, related_name="test_plans")
    module_ids = models.JSONField(default=list, blank=True)
    api_ids = models.JSONField(default=list, blank=True)
    variables = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    concurrency = models.PositiveSmallIntegerField(default=1)
    retry_count = models.PositiveSmallIntegerField(default=0)
    timeout_seconds = models.PositiveSmallIntegerField(default=30)
    failure_strategy = models.CharField(max_length=16, choices=FailureStrategy.choices, default=FailureStrategy.CONTINUE)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table_comment = '测试计划表：组合接口套件、接口场景和UI套件形成可执行计划。'
        unique_together = [("project", "name")]
        ordering = ["project_id", "name"]

    def __str__(self) -> str:
        return self.name


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

    plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE, related_name="runs")
    environment = models.ForeignKey(Environment, null=True, blank=True, on_delete=models.SET_NULL, related_name="runs")
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
        db_table_comment = '测试执行记录表：一次测试计划运行的总记录和报告汇总。'
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.plan.name}#{self.pk}"


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
        db_table_comment = '测试执行步骤表：一次测试运行中每个接口/场景/UI步骤的结果明细。'
        ordering = ["run_id", "sort_order", "id"]

    def __str__(self) -> str:
        return self.step_name


apply_model_comments(TestPlan, "测试计划表：组合接口套件、接口场景和UI套件形成可执行计划。", {
    "project": "所属项目ID。",
    "platform_ref": "关联平台ID。",
    "environment": "默认运行环境ID。",
    "name": "计划名称。",
    "plan_type": "计划类型：API/UI/混合。",
    "module_ids": "计划覆盖的接口目录ID列表。",
    "api_ids": "计划覆盖的接口ID列表。",
    "variables": "计划级运行变量。",
    "description": "计划说明。",
    "status": "计划状态。",
    "concurrency": "并发数。",
    "retry_count": "失败重试次数。",
    "timeout_seconds": "单步骤超时时间秒数。",
    "failure_strategy": "失败处理策略。",
    "is_active": "是否启用。",
})
apply_model_comments(TestRun, "测试执行记录表：一次测试计划运行的总记录和报告汇总。", {
    "plan": "关联测试计划ID。",
    "environment": "本次运行环境ID。",
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
