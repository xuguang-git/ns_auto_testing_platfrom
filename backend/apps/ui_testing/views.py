from rest_framework import decorators, response, viewsets

from apps.accounts.models import AuditLog
from apps.accounts.permissions import action_permission
from apps.core.viewsets import OperatorAuditModelViewSet
from apps.projects.services import get_default_project
from apps.ui_testing.models import UiAction, UiCase, UiElement, UiPage, UiSuite
from apps.ui_testing.serializers import UiActionSerializer, UiCaseSerializer, UiElementSerializer, UiPageSerializer, UiSuiteSerializer
from apps.ui_testing.services import run_ui_case


class UiSuiteViewSet(OperatorAuditModelViewSet):
    queryset = UiSuite.objects.select_related("project").all()
    serializer_class = UiSuiteSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    filterset_fields = ["project"]
    search_fields = ["name", "description"]
    audit_module = "ui_suite"

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(
            project=serializer.validated_data.get("project") or get_default_project(),
            created_by=user,
            updated_by=user,
        )
        self.write_operator_audit(AuditLog.ActionType.CREATE, instance)


class UiCaseViewSet(OperatorAuditModelViewSet):
    queryset = UiCase.objects.select_related("suite", "suite__project").prefetch_related("suites", "elements").all()
    serializer_class = UiCaseSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    filterset_fields = ["suite", "browser", "is_active"]
    search_fields = ["name", "start_url"]
    ordering_fields = ["sort_order", "created_at", "updated_at"]
    audit_module = "ui_case"

    def get_queryset(self):
        queryset = super().get_queryset()
        suite = self.request.query_params.get("suite")
        if suite:
            queryset = queryset.filter(suites=suite)
        return queryset.distinct()

    @decorators.action(detail=True, methods=["post"], url_path="run")
    def run(self, request, pk=None):
        case = self.get_object()
        return response.Response(run_ui_case(case, request.data))


class UiElementViewSet(OperatorAuditModelViewSet):
    queryset = UiElement.objects.select_related("suite", "page_node").all()
    serializer_class = UiElementSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    filterset_fields = ["suite", "page_node", "locator_type", "is_active"]
    search_fields = ["name", "page", "page_node__name", "selector", "description"]
    audit_module = "ui_element"


class UiPageViewSet(OperatorAuditModelViewSet):
    queryset = UiPage.objects.select_related("suite", "parent").prefetch_related("children", "elements").all()
    serializer_class = UiPageSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    filterset_fields = ["suite", "parent", "is_active"]
    search_fields = ["name", "path", "description"]
    audit_module = "ui_page"


class UiActionViewSet(OperatorAuditModelViewSet):
    queryset = UiAction.objects.all()
    serializer_class = UiActionSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    filterset_fields = ["action", "is_active"]
    search_fields = ["name", "description"]
    audit_module = "ui_action"
