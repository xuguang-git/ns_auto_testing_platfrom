from rest_framework import serializers

from apps.core.serializers import OperatorFieldsMixin
from apps.test_runs.models import TestPlan, TestRun, TestRunStep


class TestPlanSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    api_count = serializers.SerializerMethodField()
    module_count = serializers.SerializerMethodField()
    platform_name = serializers.CharField(source="platform_ref.name", read_only=True)

    class Meta:
        model = TestPlan
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name"]

    def get_api_count(self, obj):
        return len(obj.api_ids or [])

    def get_module_count(self, obj):
        return len(obj.module_ids or [])


class TestRunStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestRunStep
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class TestRunSerializer(serializers.ModelSerializer):
    steps = TestRunStepSerializer(many=True, read_only=True)

    class Meta:
        model = TestRun
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
            "duration_ms",
            "summary",
            "report",
            "error_message",
        ]
