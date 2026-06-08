from rest_framework import serializers

from apps.core.serializers import OperatorFieldsMixin
from apps.performance_testing.models import JMeterScript, PerformanceRun, PerformanceTask


class JMeterScriptSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    task_count = serializers.IntegerField(source="tasks.count", read_only=True)

    class Meta:
        model = JMeterScript
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "task_count"]

    def validate_file(self, value):
        if not value.name.lower().endswith(".jmx"):
            raise serializers.ValidationError("仅支持上传 .jmx 文件")
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("JMX 文件不能超过 10MB")
        return value


class PerformanceTaskSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    script_name = serializers.CharField(source="script.name", read_only=True)

    class Meta:
        model = PerformanceTask
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "script_name"]


class PerformanceRunSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source="task.name", read_only=True)
    script_name = serializers.CharField(source="task.script.name", read_only=True)
    task_is_active = serializers.BooleanField(source="task.is_active", read_only=True)
    script_is_active = serializers.BooleanField(source="task.script.is_active", read_only=True)

    class Meta:
        model = PerformanceRun
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
            "duration_ms",
            "summary",
            "logs",
            "error_message",
            "task_name",
            "script_name",
            "task_is_active",
            "script_is_active",
        ]
