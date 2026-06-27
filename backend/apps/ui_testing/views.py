from rest_framework import decorators, response, viewsets

from apps.accounts.models import AuditLog
from apps.accounts.permissions import action_permission
from apps.core.delete_guards import DeleteGuardMixin, DeleteGuardRule
from apps.core.viewsets import OperatorAuditModelViewSet
from apps.projects.services import get_default_project
from apps.ui_testing.models import UiAction, UiCase, UiElement, UiPage, UiSuite
from apps.ui_testing.serializers import UiActionSerializer, UiCaseSerializer, UiElementSerializer, UiPageSerializer, UiSuiteSerializer
from apps.ui_testing.services import run_ui_case, validate_ui_element


class UiSuiteViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = UiSuite.objects.select_related("project").all()
    serializer_class = UiSuiteSerializer
    permission_classes = [action_permission(("ui_suite.read", "ui_case.read", "ui_element.read"), "ui_suite.create", "ui_suite.update", "ui_suite.delete", "ui_suite.execute")]
    filterset_fields = ["project"]
    search_fields = ["name", "description"]
    audit_module = "ui_suite"
    delete_object_label = "UI测试套件"
    delete_guard_rules = (
        DeleteGuardRule("cases", "UI用例"),
        DeleteGuardRule("case_memberships", "UI用例关联"),
        DeleteGuardRule("pages", "页面目录"),
        DeleteGuardRule("elements", "定位元素"),
    )

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
    permission_classes = [action_permission(("ui_case.read", "ui_suite.read"), "ui_case.create", "ui_case.update", "ui_case.delete", "ui_case.execute")]
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


class UiElementViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = UiElement.objects.select_related("suite", "page_node").all()
    serializer_class = UiElementSerializer
    permission_classes = [action_permission(("ui_element.read", "ui_case.read", "ui_suite.read"), "ui_element.create", "ui_element.update", "ui_element.delete", "ui_element.execute")]
    filterset_fields = ["suite", "page_node", "locator_type", "is_active"]
    search_fields = ["name", "page", "page_node__name", "selector", "description"]
    audit_module = "ui_element"
    delete_object_label = "定位元素"
    delete_guard_rules = (
        DeleteGuardRule("ui_cases", "UI用例"),
    )

    @decorators.action(detail=True, methods=["post"], url_path="validate")
    def validate_locator(self, request, pk=None):
        element = self.get_object()
        return response.Response(validate_ui_element(element, request.data))


class UiPageViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = UiPage.objects.select_related("suite", "parent").prefetch_related("children", "elements").all()
    serializer_class = UiPageSerializer
    permission_classes = [action_permission("ui_element.read", "ui_element.create", "ui_element.update", "ui_element.delete")]
    filterset_fields = ["suite", "parent", "is_active"]
    search_fields = ["name", "path", "description"]
    audit_module = "ui_page"
    delete_object_label = "页面目录"
    delete_guard_rules = (
        DeleteGuardRule("children", "子页面"),
        DeleteGuardRule("elements", "定位元素"),
    )


class UiActionViewSet(OperatorAuditModelViewSet):
    queryset = UiAction.objects.all()
    serializer_class = UiActionSerializer
    permission_classes = [action_permission("ui_case.read", "ui_case.create", "ui_case.update", "ui_case.delete")]
    filterset_fields = ["action", "is_active"]
    search_fields = ["name", "description"]
    audit_module = "ui_action"
