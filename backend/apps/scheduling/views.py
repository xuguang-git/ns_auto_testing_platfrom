from rest_framework import decorators, response, status

from apps.accounts.models import AuditLog
from apps.accounts.permissions import action_permission
from apps.core.viewsets import OperatorAuditModelViewSet
from apps.scheduling.models import ScheduledPlan
from apps.scheduling.serializers import ScheduledPlanSerializer
from apps.scheduling.services import refresh_next_run, trigger_scheduled_plan
from apps.test_runs.serializers import TestRunSerializer


class ScheduledPlanViewSet(OperatorAuditModelViewSet):
    queryset = ScheduledPlan.objects.select_related("plan", "plan__project").all()
    serializer_class = ScheduledPlanSerializer
    permission_classes = [action_permission("schedule.read", "schedule.write", "schedule.delete")]
    filterset_fields = ["plan", "is_active", "last_status"]
    search_fields = ["name", "cron", "plan__name"]
    ordering_fields = ["next_run_at", "last_run_at", "created_at", "updated_at"]
    audit_module = "scheduled_plan"

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(created_by=user, updated_by=user)
        self.write_operator_audit(AuditLog.ActionType.CREATE, instance)

    @decorators.action(detail=True, methods=["post"], url_path="toggle")
    def toggle(self, request, pk=None):
        schedule = self.get_object()
        schedule.is_active = not schedule.is_active
        refresh_next_run(schedule)
        schedule.save(update_fields=["is_active", "next_run_at", "updated_at"])
        self.write_operator_audit(AuditLog.ActionType.UPDATE, schedule)
        return response.Response(self.get_serializer(schedule).data)

    @decorators.action(detail=True, methods=["post"], url_path="run-now")
    def run_now(self, request, pk=None):
        schedule = self.get_object()
        test_run = trigger_scheduled_plan(schedule)
        return response.Response(TestRunSerializer(test_run).data, status=status.HTTP_202_ACCEPTED)
