from rest_framework import decorators, response, status, viewsets

from apps.accounts.models import AuditLog
from apps.accounts.permissions import action_permission
from apps.api_testing.models import ApiCase, ApiDefinition, ApiMockRule, ApiModule, ApiScenario, ApiStep, ApiSuite, ApiTestCase
from apps.api_testing.serializers import (
    ApiCaseSerializer,
    ApiDefinitionSerializer,
    ApiMockRuleSerializer,
    ApiModuleSerializer,
    ApiScenarioSerializer,
    ApiStepSerializer,
    ApiSuiteSerializer,
    ApiTestCaseSerializer,
)
from apps.api_testing.services import execute_debug_request
from apps.core.delete_guards import DeleteGuardMixin, DeleteGuardRule
from apps.core.viewsets import OperatorAuditModelViewSet
from apps.projects.services import get_default_project


class ApiModuleViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = ApiModule.objects.select_related("project", "managed_platform", "parent").prefetch_related("apis").all()
    serializer_class = ApiModuleSerializer
    permission_classes = [action_permission("module.read", "module.write", "module.delete")]
    filterset_fields = ["project", "managed_platform", "platform", "parent", "is_active"]
    search_fields = ["name", "code", "description"]
    audit_module = "api_module"
    delete_object_label = "接口目录"
    delete_guard_rules = (
        DeleteGuardRule("children", "子目录"),
        DeleteGuardRule("apis", "接口"),
        DeleteGuardRule("pre_request_operations", "全局前置操作"),
    )

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(project=serializer.validated_data.get("project") or get_default_project(), created_by=user, updated_by=user)
        self.write_operator_audit(AuditLog.ActionType.CREATE, instance)


class ApiDefinitionViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = ApiDefinition.objects.select_related("project", "module").prefetch_related("test_cases", "mock_rules").all()
    serializer_class = ApiDefinitionSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    throttle_scope = None
    filterset_fields = ["project", "platform", "module", "method", "status", "is_active"]
    search_fields = ["name", "path", "description"]
    ordering_fields = ["sort_order", "created_at", "updated_at"]
    audit_module = "api_definition"
    delete_object_label = "接口"
    delete_guard_rules = (
        DeleteGuardRule("test_cases", "单接口用例"),
        DeleteGuardRule("mock_rules", "Mock规则"),
        DeleteGuardRule("steps", "场景步骤"),
    )

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(
            project=serializer.validated_data.get("project") or get_default_project(),
            created_by=user,
            updated_by=user,
        )
        self.write_operator_audit(AuditLog.ActionType.CREATE, instance)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("single_case_tree"):
            return queryset.filter(is_active=True).exclude(status=ApiDefinition.Status.DEPRECATED)
        return queryset

    @decorators.action(detail=False, methods=["post"], url_path="debug", throttle_scope="api_debug")
    def debug(self, request):
        result = execute_debug_request(request.data)
        if result.get("ok") is False:
            return response.Response(result, status=status.HTTP_400_BAD_REQUEST)
        return response.Response(result, status=status.HTTP_200_OK)


def count_suites_using_case(case: ApiTestCase) -> int:
    """统计当前单接口用例被多少个测试套件引用。"""

    suites = ApiSuite.objects.filter(project_id=case.project_id).only("case_ids")
    return sum(1 for suite in suites if case.id in (suite.case_ids or []))


class ApiTestCaseViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = ApiTestCase.objects.select_related("project", "api", "api__module").all()
    serializer_class = ApiTestCaseSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    filterset_fields = ["project", "api", "api__module", "status", "priority", "is_active"]
    search_fields = ["name", "description", "api__name", "api__path"]
    ordering_fields = ["created_at", "updated_at", "priority"]
    audit_module = "api_test_case"
    delete_object_label = "单接口用例"
    delete_guard_rules = (
        DeleteGuardRule(None, "测试套件", "当前测试用例已被测试套件引用，不允许删除，请先从套件中移除。", count_suites_using_case),
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        api_ids = self.request.query_params.get("api_ids")
        if api_ids:
            ids = [item for item in api_ids.split(",") if item.strip().isdigit()]
            queryset = queryset.filter(api_id__in=ids)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(
            project=serializer.validated_data.get("project") or get_default_project(),
            created_by=user,
            updated_by=user,
        )
        self.write_operator_audit(AuditLog.ActionType.CREATE, instance)


class ApiMockRuleViewSet(OperatorAuditModelViewSet):
    queryset = ApiMockRule.objects.select_related("api").all()
    serializer_class = ApiMockRuleSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    filterset_fields = ["api", "enabled", "status_code"]
    search_fields = ["name", "description", "api__name", "api__path"]
    audit_module = "api_mock_rule"


class ApiSuiteViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = ApiSuite.objects.select_related("project").all()
    serializer_class = ApiSuiteSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    filterset_fields = ["project", "is_active"]
    search_fields = ["name", "description"]
    audit_module = "api_suite"
    delete_object_label = "测试套件"
    delete_guard_rules = (
        DeleteGuardRule("scenarios", "场景用例"),
        DeleteGuardRule("cases", "旧版单接口用例"),
        DeleteGuardRule("schedules", "定时任务"),
        DeleteGuardRule("runs", "测试报告"),
    )

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(
            project=serializer.validated_data.get("project") or get_default_project(),
            created_by=user,
            updated_by=user,
        )
        self.write_operator_audit(AuditLog.ActionType.CREATE, instance)


class ApiScenarioViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = ApiScenario.objects.select_related("suite", "suite__project").all()
    serializer_class = ApiScenarioSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    filterset_fields = ["suite", "priority", "is_active"]
    search_fields = ["name", "description"]
    audit_module = "api_scenario"
    delete_object_label = "场景用例"
    delete_guard_rules = (
        DeleteGuardRule("steps", "场景步骤"),
    )


class ApiStepViewSet(OperatorAuditModelViewSet):
    queryset = ApiStep.objects.select_related("scenario", "scenario__suite", "api").all()
    serializer_class = ApiStepSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    filterset_fields = ["scenario", "platform", "method", "is_active"]
    search_fields = ["name", "path"]
    ordering_fields = ["sort_order", "created_at", "updated_at"]
    audit_module = "api_step"


class ApiCaseViewSet(OperatorAuditModelViewSet):
    queryset = ApiCase.objects.select_related("suite", "suite__project").all()
    serializer_class = ApiCaseSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    filterset_fields = ["suite", "method", "is_active"]
    search_fields = ["name", "path"]
    ordering_fields = ["sort_order", "created_at", "updated_at"]
    audit_module = "api_case"
