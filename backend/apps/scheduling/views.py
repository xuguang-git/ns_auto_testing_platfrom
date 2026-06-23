from rest_framework import decorators, response, status

from apps.accounts.models import AuditLog
from apps.accounts.permissions import action_permission
from apps.core.delete_guards import DeleteGuardMixin, DeleteGuardRule
from apps.core.viewsets import OperatorAuditModelViewSet
from apps.scheduling.models import NotificationChannel, NotificationSendLog, NotificationTemplate, ScheduledPlan
from apps.scheduling.notification_services import TEMPLATE_VARIABLES
from apps.scheduling.serializers import (
    NotificationChannelSerializer,
    NotificationSendLogSerializer,
    NotificationTemplateSerializer,
    ScheduledPlanSerializer,
)
from apps.scheduling.services import refresh_next_run, trigger_scheduled_plan
from apps.test_runs.models import TestRun
from apps.test_runs.serializers import TestRunSerializer


def is_schedule_active(schedule: ScheduledPlan) -> bool:
    """判断定时任务是否处于启用状态。"""

    return schedule.is_active


class NotificationChannelViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = NotificationChannel.objects.prefetch_related("scheduled_plans", "templates", "send_logs").all()
    serializer_class = NotificationChannelSerializer
    permission_classes = [action_permission("schedule.read", "schedule.write", "schedule.delete")]
    filterset_fields = ["notification_type", "push_platform", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "updated_at"]
    audit_module = "notification_channel"
    delete_object_label = "消息通知"
    delete_guard_rules = (
        DeleteGuardRule("scheduled_plans", "定时任务"),
        DeleteGuardRule("templates", "消息模板"),
    )

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(created_by=user, updated_by=user)
        self.write_operator_audit(AuditLog.ActionType.CREATE, instance)


class NotificationTemplateViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = NotificationTemplate.objects.select_related("channel").prefetch_related("scheduled_plans", "send_logs").all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [action_permission("schedule.read", "schedule.write", "schedule.delete")]
    filterset_fields = ["biz_type", "channel", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "updated_at"]
    audit_module = "notification_template"
    delete_object_label = "消息模板"
    delete_guard_rules = (
        DeleteGuardRule("scheduled_plans", "定时任务"),
    )

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(created_by=user, updated_by=user)
        self.write_operator_audit(AuditLog.ActionType.CREATE, instance)

    @decorators.action(detail=False, methods=["get"], url_path="variables")
    def variables(self, request):
        return response.Response(TEMPLATE_VARIABLES)


class NotificationSendLogViewSet(OperatorAuditModelViewSet):
    queryset = NotificationSendLog.objects.select_related("channel", "template", "schedule", "test_run").all()
    serializer_class = NotificationSendLogSerializer
    permission_classes = [action_permission("schedule.read")]
    http_method_names = ["get", "head", "options"]
    filterset_fields = ["status", "channel", "template", "schedule", "test_run"]
    search_fields = ["title", "error_message"]
    ordering_fields = ["created_at", "sent_at"]
    audit_module = "notification_send_log"


class ScheduledPlanViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = (
        ScheduledPlan.objects.select_related("environment", "suite", "suite__project", "notification_template")
        .prefetch_related("notifications", "runs", "notification_logs")
        .all()
    )
    serializer_class = ScheduledPlanSerializer
    permission_classes = [action_permission("schedule.read", "schedule.write", "schedule.delete")]
    filterset_fields = ["suite", "environment", "is_active", "last_status"]
    search_fields = ["name", "cron", "suite__name"]
    ordering_fields = ["next_run_at", "last_run_at", "created_at", "updated_at"]
    audit_module = "scheduled_plan"
    delete_object_label = "定时任务"
    delete_guard_rules = (
        DeleteGuardRule(None, "启用状态", "启用中的定时任务不允许删除，请先停用后再删除。", is_schedule_active),
    )

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
        test_run = trigger_scheduled_plan(schedule, trigger_type=TestRun.TriggerType.MANUAL)
        return response.Response(TestRunSerializer(test_run).data, status=status.HTTP_202_ACCEPTED)
