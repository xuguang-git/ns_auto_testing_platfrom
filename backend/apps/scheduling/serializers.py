from rest_framework import serializers

from apps.core.serializers import OperatorFieldsMixin
from apps.scheduling.models import ScheduledPlan
from apps.scheduling.services import refresh_next_run


class ScheduledPlanSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = ScheduledPlan
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
            "plan_name",
            "last_run_at",
            "next_run_at",
            "last_run_id",
            "last_status",
            "run_count",
        ]

    def validate_cron(self, value):
        probe = ScheduledPlan(cron=value, is_active=True)
        refresh_next_run(probe)
        return value

    def create(self, validated_data):
        instance = ScheduledPlan(**validated_data)
        refresh_next_run(instance)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        refresh_next_run(instance)
        instance.save()
        return instance
