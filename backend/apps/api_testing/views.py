import json
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import decorators, response, status, viewsets
from rest_framework import exceptions as drf_exceptions

from apps.accounts.models import AuditLog
from apps.accounts.permissions import action_permission
from apps.accounts.security import authenticate_access_token, get_access_token_from_request
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
from apps.api_testing.mock_security import verify_mock_rule_token
from apps.api_testing.services import execute_debug_request
from apps.core.delete_guards import DeleteGuardMixin, DeleteGuardRule
from apps.core.viewsets import OperatorAuditModelViewSet
from apps.projects.services import get_default_project


MOCK_BLOCKED_RESPONSE_HEADERS = {
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "upgrade",
}


def _json_error(message: str, status_code: int) -> JsonResponse:
    return JsonResponse({"message": message}, status=status_code, json_dumps_params={"ensure_ascii": False})


def _mock_headers(headers) -> dict[str, str]:
    if isinstance(headers, dict):
        items = headers.items()
    elif isinstance(headers, list):
        items = ((item.get("key"), item.get("value")) for item in headers if isinstance(item, dict) and item.get("enabled", True) is not False)
    else:
        items = []
    result = {}
    for key, value in items:
        name = str(key or "").strip()
        if not name or name.lower() in MOCK_BLOCKED_RESPONSE_HEADERS:
            continue
        result[name] = str(value if value is not None else "")
    return result


def _mock_body_response(rule: ApiMockRule) -> HttpResponse:
    headers = _mock_headers(rule.headers)
    content_type = headers.pop("Content-Type", headers.pop("content-type", "application/json; charset=utf-8"))
    body = rule.response_body
    if isinstance(body, (dict, list)):
        content = json.dumps(body, ensure_ascii=False)
    elif body is None:
        content = ""
    else:
        content = str(body)
    resp = HttpResponse(content, status=rule.status_code, content_type=content_type)
    for key, value in headers.items():
        resp[key] = value
    return resp


def _is_active_user(user) -> bool:
    profile = getattr(user, "profile", None)
    return bool(user and user.is_authenticated and user.is_active and (not profile or profile.status == "active"))


def _is_authenticated_mock_request(request) -> bool:
    if _is_active_user(request.user):
        return True
    try:
        record = authenticate_access_token(get_access_token_from_request(request))
    except drf_exceptions.AuthenticationFailed:
        return False
    return _is_active_user(record.user)


def _client_ip(request) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _mock_rate_limited(request, rule: ApiMockRule) -> bool:
    limit = max(1, int(getattr(settings, "API_MOCK_RATE_LIMIT_PER_MINUTE", 120)))
    key = f"api-mock-rate:{rule.id}:{_client_ip(request)}"
    count = cache.get(key, 0) + 1
    cache.set(key, count, 60)
    return count > limit


def _can_access_mock(request, rule: ApiMockRule) -> bool:
    if _is_authenticated_mock_request(request):
        return True
    if not getattr(settings, "API_MOCK_PUBLIC_ACCESS_ENABLED", False):
        return False
    token = request.GET.get("token") or request.headers.get("X-Mock-Token", "")
    return verify_mock_rule_token(rule, token)


def _normalized_mock_path(path: str) -> str:
    value = f"/{str(path or '').strip().lstrip('/')}"
    return value.rstrip("/") or "/"


def _proxy_api_candidates(proxy_path: str) -> list[str]:
    normalized = _normalized_mock_path(proxy_path)
    return [normalized] if normalized == "/" else [normalized, f"{normalized}/"]


def _resolve_proxy_rule(request, proxy_path: str):
    api = ApiDefinition.objects.filter(
        method=request.method.upper(),
        path__in=_proxy_api_candidates(proxy_path),
        is_active=True,
    ).order_by("id").first()
    if not api:
        return None, _json_error("Mock 接口未命中", 404)

    rules = list(api.mock_rules.filter(enabled=True).order_by("id"))
    if not rules:
        return None, _json_error("Mock 规则未命中", 404)

    if _is_authenticated_mock_request(request):
        return rules[0], None

    if not getattr(settings, "API_MOCK_PUBLIC_ACCESS_ENABLED", False):
        return None, _json_error("Mock 访问未授权", 403)

    token = request.GET.get("token") or request.headers.get("X-Mock-Token", "")
    for rule in rules:
        if verify_mock_rule_token(rule, token):
            return rule, None
    return None, _json_error("Mock 访问未授权", 403)


def _serve_mock_rule(request, rule: ApiMockRule):
    if _mock_rate_limited(request, rule):
        return _json_error("Mock 访问过于频繁，请稍后重试", 429)
    if rule.delay_ms:
        time.sleep(min(rule.delay_ms, getattr(settings, "API_MOCK_MAX_DELAY_MS", 5000)) / 1000)
    return _mock_body_response(rule)


@csrf_exempt
def mock_api_response(request, api_id: int, rule_id: int):
    rule = ApiMockRule.objects.select_related("api").filter(pk=rule_id, api_id=api_id).first()
    if not rule:
        return _json_error("Mock 规则不存在", 404)
    if not _can_access_mock(request, rule):
        return _json_error("Mock 访问未授权", 403)
    if _mock_rate_limited(request, rule):
        return _json_error("Mock 访问过于频繁，请稍后重试", 429)
    if not rule.enabled:
        return _json_error("Mock 规则未启用", 404)
    if request.method.upper() != rule.api.method.upper():
        return _json_error(f"Mock 请求方式不匹配，应使用 {rule.api.method}", 405)
    return _serve_mock_rule(request, rule)


@csrf_exempt
def mock_proxy_response(request, proxy_path: str = ""):
    rule, error = _resolve_proxy_rule(request, proxy_path)
    if error:
        return error
    return _serve_mock_rule(request, rule)


class ApiModuleViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = ApiModule.objects.select_related("project", "managed_platform", "parent").prefetch_related("apis").all()
    serializer_class = ApiModuleSerializer
    permission_classes = [action_permission("module.read", "module.create", "module.update", "module.delete")]
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
    permission_classes = [action_permission(
        ("api.read", "api_case.read", "automation.read", "quick_test.read", "capability.read"),
        "api.create",
        "api.update",
        "api.delete",
        ("api.debug", "api_case.debug", "automation.execute", "quick_test.execute", "capability.execute"),
    )]
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
    permission_classes = [action_permission(("api_case.read", "automation.read"), ("api_case.create", "automation.create"), ("api_case.update", "automation.update"), ("api_case.delete", "automation.delete"), ("api_case.debug", "automation.execute"))]
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
    permission_classes = [action_permission("api.read", "api.create", "api.update", "api.delete")]
    filterset_fields = ["api", "enabled", "status_code"]
    search_fields = ["name", "description", "api__name", "api__path"]
    audit_module = "api_mock_rule"


class ApiSuiteViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = ApiSuite.objects.select_related("project").all()
    serializer_class = ApiSuiteSerializer
    permission_classes = [action_permission("automation.read", "automation.create", "automation.update", "automation.delete")]
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
    permission_classes = [action_permission("automation.read", "automation.create", "automation.update", "automation.delete")]
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
    permission_classes = [action_permission("automation.read", "automation.create", "automation.update", "automation.delete")]
    filterset_fields = ["scenario", "platform", "method", "is_active"]
    search_fields = ["name", "path"]
    ordering_fields = ["sort_order", "created_at", "updated_at"]
    audit_module = "api_step"


class ApiCaseViewSet(OperatorAuditModelViewSet):
    queryset = ApiCase.objects.select_related("suite", "suite__project").all()
    serializer_class = ApiCaseSerializer
    permission_classes = [action_permission("automation.read", "automation.create", "automation.update", "automation.delete")]
    filterset_fields = ["suite", "method", "is_active"]
    search_fields = ["name", "path"]
    ordering_fields = ["sort_order", "created_at", "updated_at"]
    audit_module = "api_case"
