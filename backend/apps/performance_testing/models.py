from django.db import models

from apps.core.db_comments import apply_model_comments
from apps.core.models import OwnedModel, TimestampedModel


class JMeterScript(OwnedModel):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="performance/jmx/")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table_comment = '性能测试脚本表：保存上传的JMeter JMX脚本文件。'
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
        db_table_comment = '性能测试任务表：基于JMeter脚本配置线程、循环和持续时间。'
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
        db_table_comment = '性能测试执行记录表：一次性能任务运行的状态、报告和日志。'
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.task.name}#{self.pk}"


apply_model_comments(JMeterScript, "性能测试脚本表：保存上传的JMeter JMX脚本文件。", {
    "name": "脚本名称。",
    "description": "脚本说明。",
    "file": "JMX脚本文件路径。",
    "is_active": "是否启用。",
})
apply_model_comments(PerformanceTask, "性能测试任务表：基于JMeter脚本配置线程、循环和持续时间。", {
    "name": "任务名称。",
    "script": "关联JMeter脚本ID。",
    "threads": "线程数。",
    "ramp_up_seconds": "启动预热秒数。",
    "duration_seconds": "持续执行秒数。",
    "loops": "循环次数。",
    "description": "任务说明。",
    "is_active": "是否启用。",
})
apply_model_comments(PerformanceRun, "性能测试执行记录表：一次性能任务运行的状态、报告和日志。", {
    "task": "关联性能任务ID。",
    "status": "执行状态。",
    "celery_task_id": "异步任务ID。",
    "started_at": "开始时间。",
    "finished_at": "结束时间。",
    "duration_ms": "总耗时毫秒。",
    "jtl_path": "JMeter JTL结果文件路径。",
    "html_report_dir": "HTML报告目录。",
    "summary": "性能摘要数据。",
    "logs": "执行日志列表。",
    "error_message": "失败错误信息。",
})
