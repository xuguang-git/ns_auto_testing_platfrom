from django.db import models

from apps.api_testing.models import ApiScenario, ApiSuite
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
        ordering = ["run_id", "sort_order", "id"]

    def __str__(self) -> str:
        return self.step_name
