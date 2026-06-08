from django.db import models

from apps.core.models import OwnedModel, TimestampedModel


class JMeterScript(OwnedModel):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="performance/jmx/")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-updated_at", "name"]

    def __str__(self) -> str:
        return self.name


class PerformanceTask(OwnedModel):
    name = models.CharField(max_length=128)
    script = models.ForeignKey(JMeterScript, on_delete=models.CASCADE, related_name="tasks")
    threads = models.PositiveIntegerField(default=10)
    ramp_up_seconds = models.PositiveIntegerField(default=10)
    duration_seconds = models.PositiveIntegerField(default=60)
    loops = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-updated_at", "name"]

    def __str__(self) -> str:
        return self.name


class PerformanceRun(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    task = models.ForeignKey(PerformanceTask, on_delete=models.CASCADE, related_name="runs")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    celery_task_id = models.CharField(max_length=128, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    jtl_path = models.CharField(max_length=512, blank=True)
    html_report_dir = models.CharField(max_length=512, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    logs = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.task.name}#{self.pk}"
