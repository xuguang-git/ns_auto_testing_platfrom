import socket
import time
from urllib.parse import urlparse

import requests
from django.core.cache import cache
from rest_framework import decorators, mixins, status, viewsets
from rest_framework.response import Response

from apps.accounts.models import AuditLog
from apps.accounts.permissions import action_permission
from apps.api_testing.models import ApiModule
from apps.core.delete_guards import DeleteGuardMixin, DeleteGuardRule
from apps.api_testing.services import clear_environment_request_control_cache, run_pre_request_operation
from apps.core.viewsets import OperatorAuditModelViewSet
from apps.projects.db_services import check_database_connection, execute_test_data_source
from apps.projects.models import DataFactoryCapability, DatabaseConnection, Environment, EnvironmentPreRequestOperation, EnvironmentRequestControl, EnvironmentVariable, Platform, Project, TestDataSource
from apps.projects.serializers import (
    DataFactoryCapabilitySerializer,
    DatabaseConnectionSerializer,
    EnvironmentPreRequestOperationSerializer,
    EnvironmentRequestControlSerializer,
    EnvironmentSerializer,
    EnvironmentVariableSerializer,
    PlatformSerializer,
    ProjectSerializer,
    TestDataSourceSerializer,
)
from apps.projects.services import get_default_project
from apps.test_runs.snapshots import count_active_runs_using_test_data_source


class ProjectViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [action_permission("platform.read", "platform.create", "platform.update", "platform.delete")]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "created_at", "updated_at"]

    audit_module = "project"
    delete_object_label = "项目"
    delete_guard_rules = (
        DeleteGuardRule("environments", "环境配置"),
        DeleteGuardRule("api_modules", "接口目录"),
        DeleteGuardRule("api_definitions", "接口"),
        DeleteGuardRule("api_test_cases", "单接口用例"),
        DeleteGuardRule("api_suites", "测试套件"),
        DeleteGuardRule("test_data_sources", "测试数据源"),
        DeleteGuardRule("ui_suites", "UI测试套件"),
    )


class PlatformViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = Platform.objects.prefetch_related("api_modules").all()
    serializer_class = PlatformSerializer
    permission_classes = [action_permission("platform.read", "platform.create", "platform.update", "platform.delete")]
    filterset_fields = ["is_active"]
    search_fields = ["name", "code", "description"]
    ordering_fields = ["sort_order", "created_at", "updated_at"]
    audit_module = "platform"
    delete_object_label = "平台"
    delete_guard_rules = (
        DeleteGuardRule("api_modules", "接口目录"),
    )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user if request.user.is_authenticated else None
        platform = serializer.save(created_by=user, updated_by=user)
        project = get_default_project()
        legacy_code = platform.code.upper()
        if legacy_code not in (project.platforms or []):
            project.platforms = [*(project.platforms or []), legacy_code]
            project.save(update_fields=["platforms", "updated_at"])
        ApiModule.objects.get_or_create(
            project=project,
            managed_platform=platform,
            platform=legacy_code,
            parent=None,
            code="unassigned",
            defaults={
                "name": "未分配",
                "description": "平台默认模块，用于暂存尚未分类的接口",
                "sort_order": 0,
                "is_active": True,
            },
        )
        self.write_operator_audit(AuditLog.ActionType.CREATE, platform)
        return Response(self.get_serializer(platform).data, status=status.HTTP_201_CREATED)


class EnvironmentViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = Environment.objects.select_related("project").prefetch_related("variable_items", "pre_request_operations__modules", "request_controls").all()
    serializer_class = EnvironmentSerializer
    permission_classes = [action_permission("environment.read", "environment.create", "environment.update", "environment.delete")]
    filterset_fields = ["project", "env_type", "is_default", "is_readonly"]
    search_fields = ["name", "base_url"]
    audit_module = "environment"
    delete_object_label = "环境"
    delete_guard_rules = (
        DeleteGuardRule("variable_items", "环境变量"),
        DeleteGuardRule("pre_request_operations", "全局前置操作"),
        DeleteGuardRule("request_controls", "请求控件"),
        DeleteGuardRule("database_connections", "数据库连接"),
        DeleteGuardRule("data_capabilities", "执行能力"),
        DeleteGuardRule("test_data_sources", "测试数据源"),
        DeleteGuardRule("api_scenarios", "场景用例"),
        DeleteGuardRule("scheduled_plans", "定时任务"),
        DeleteGuardRule("runs", "测试报告"),
    )

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(project=serializer.validated_data.get("project") or get_default_project(), created_by=user, updated_by=user)
        self.write_operator_audit(AuditLog.ActionType.CREATE, instance)

    @decorators.action(detail=True, methods=["get"], url_path="health")
    def health(self, request, pk=None):
        environment = self.get_object()
        platform = request.query_params.get("platform") or ""
        cached = cache.get(_environment_health_cache_key(environment.id, platform))
        return Response(cached or _empty_environment_health(environment, platform))

    @decorators.action(detail=True, methods=["post"], url_path="health/run")
    def run_health(self, request, pk=None):
        environment = self.get_object()
        platform = request.data.get("platform") or request.query_params.get("platform") or ""
        force = bool(request.data.get("force"))
        cache_key = _environment_health_cache_key(environment.id, platform)
        if not force:
            cached = cache.get(cache_key)
            if cached:
                return Response(cached)
        result = _run_environment_health_check(environment, str(platform or ""))
        cache.set(cache_key, result, 60)
        return Response(result)


def _environment_health_cache_key(environment_id: int, platform: str | None = "") -> str:
    return f"environment-health:{environment_id}:{str(platform or '').upper()}"


def _empty_environment_health(environment: Environment, platform: str | None = "") -> dict:
    return {
        "environment": environment.id,
        "environment_name": environment.name,
        "platform": str(platform or "").upper(),
        "status": "unknown",
        "expired": True,
        "duration_ms": 0,
        "summary": "当前环境暂无健康检查结果。",
        "checks": [],
    }


def _run_environment_health_check(environment: Environment, platform: str) -> dict:
    started = time.perf_counter()
    checks = [
        _check_environment_base_url(environment, platform),
        _check_environment_request_control(environment),
        _check_environment_pre_request(environment, platform),
        _check_environment_databases(environment),
    ]
    failed = [item for item in checks if item["status"] == "failed"]
    warnings = [item for item in checks if item["status"] == "warning"]
    if failed:
        health_status = "unhealthy"
        summary = failed[0]["summary"]
    elif warnings:
        health_status = "warning"
        summary = warnings[0]["summary"]
    else:
        health_status = "healthy"
        summary = "环境核心检查通过。"
    return {
        "environment": environment.id,
        "environment_name": environment.name,
        "platform": platform.upper() if platform else "",
        "status": health_status,
        "expired": False,
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "summary": summary,
        "checks": checks,
    }


def _environment_base_url(environment: Environment, platform: str) -> str:
    platform_urls = environment.platform_base_urls or {}
    return platform_urls.get(platform.upper()) or platform_urls.get(platform.lower()) or environment.base_url or ""


def _masked_host(hostname: str) -> str:
    value = str(hostname or "").strip()
    if not value:
        return ""
    if "." not in value:
        return "***"
    parts = value.split(".")
    return f"{parts[0][:2]}***.{'.'.join(parts[-2:])}"


def _health_check_result(key: str, name: str, status_value: str, summary: str, advice: str = "", duration_ms: int = 0, evidence: dict | None = None) -> dict:
    return {
        "check_key": key,
        "check_name": name,
        "status": status_value,
        "duration_ms": duration_ms,
        "summary": summary,
        "advice": advice,
        "evidence": evidence or {},
    }


def _check_environment_base_url(environment: Environment, platform: str) -> dict:
    started = time.perf_counter()
    url = _environment_base_url(environment, platform)
    if not url:
        return _health_check_result("base_url_connectivity", "Base URL连通性", "failed", "当前环境未配置 Base URL。", "请在环境配置中补充平台 Base URL 或兜底 Base URL。")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return _health_check_result("base_url_connectivity", "Base URL连通性", "failed", "Base URL 格式不正确。", "请检查环境地址是否以 http:// 或 https:// 开头。")
    try:
        socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror:
        return _health_check_result("dns_resolve", "DNS解析", "failed", "目标域名无法解析。", "请检查 DNS、网络和环境 Base URL。", evidence={"host_masked": _masked_host(parsed.hostname)})
    try:
        response = requests.head(url, timeout=3, allow_redirects=False)
        if response.status_code in (405, 403):
            response = requests.get(url, timeout=3, allow_redirects=False, stream=True)
        status_value = "passed" if response.status_code < 500 else "warning"
        summary = "目标地址可访问。" if status_value == "passed" else f"目标地址返回 HTTP {response.status_code}。"
        return _health_check_result(
            "base_url_connectivity",
            "Base URL连通性",
            status_value,
            summary,
            "请检查被测服务状态。" if status_value == "warning" else "",
            int((time.perf_counter() - started) * 1000),
            {"scheme": parsed.scheme, "host_masked": _masked_host(parsed.hostname), "status_code": response.status_code},
        )
    except requests.exceptions.SSLError:
        return _health_check_result("tls_certificate", "TLS证书", "failed", "目标服务 HTTPS 握手失败。", "请检查证书、TLS配置和代理证书。", int((time.perf_counter() - started) * 1000), {"host_masked": _masked_host(parsed.hostname)})
    except requests.exceptions.Timeout:
        return _health_check_result("base_url_connectivity", "Base URL连通性", "failed", "连接目标地址超时。", "请检查网络白名单和被测服务状态。", int((time.perf_counter() - started) * 1000), {"host_masked": _masked_host(parsed.hostname)})
    except requests.RequestException:
        return _health_check_result("base_url_connectivity", "Base URL连通性", "failed", "目标地址不可访问。", "请检查环境地址、网络和被测服务状态。", int((time.perf_counter() - started) * 1000), {"host_masked": _masked_host(parsed.hostname)})


def _check_environment_request_control(environment: Environment) -> dict:
    controls = list(environment.request_controls.filter(is_enabled=True))
    if not controls:
        return _health_check_result("request_control", "请求方法控制", "passed", "当前环境未配置请求方法限制。")
    methods = sorted({str(method).upper() for control in controls for method in (control.methods or [])})
    if not methods:
        return _health_check_result("request_control", "请求方法控制", "warning", "当前环境请求控制未配置允许方法。", "请检查环境请求控制配置。")
    return _health_check_result("request_control", "请求方法控制", "passed", f"允许执行 {', '.join(methods)} 请求。", evidence={"methods": methods})


def _check_environment_pre_request(environment: Environment, platform: str) -> dict:
    operations = list(environment.pre_request_operations.filter(is_enabled=True).prefetch_related("modules").order_by("sort_order", "id"))
    if not operations and not environment.pre_request_enabled:
        return _health_check_result("pre_request", "前置登录/鉴权", "passed", "当前环境未启用前置登录。")
    if operations:
        matched = operations[0]
        if platform:
            platform_key = platform.upper()
            matched = next((item for item in operations if platform_key in {str(code).upper() for code in item.platforms or []}), operations[0])
        result = run_pre_request_operation(matched, platform=platform or None)
        if result.get("ok"):
            return _health_check_result("pre_request", "前置登录/鉴权", "passed", f"前置操作「{matched.name}」执行通过。", evidence={"operation": matched.name})
        return _health_check_result("pre_request", "前置登录/鉴权", "failed", result.get("error") or f"前置操作「{matched.name}」执行失败。", "请检查账号变量、Token提取规则和前置断言。", evidence={"operation": matched.name, "status_code": result.get("status_code")})
    return _health_check_result("pre_request", "前置登录/鉴权", "warning", "当前环境使用旧版全局前置配置，暂未纳入健康检查试运行。", "建议迁移到环境前置操作。")


def _check_environment_databases(environment: Environment) -> dict:
    connections = list(environment.database_connections.filter(is_active=True))
    if not connections:
        return _health_check_result("database_connection", "数据库连接", "passed", "当前环境未配置启用中的数据库连接。")
    failed = []
    for connection in connections[:3]:
        result = check_database_connection(connection)
        if not result.get("ok"):
            failed.append(connection.name)
    if failed:
        return _health_check_result("database_connection", "数据库连接", "failed", f"{len(failed)} 个数据库连接检查失败。", "请检查数据库连接配置和网络白名单。", evidence={"failed_count": len(failed)})
    return _health_check_result("database_connection", "数据库连接", "passed", f"{len(connections[:3])} 个数据库连接检查通过。")


class EnvironmentVariableViewSet(OperatorAuditModelViewSet):
    queryset = EnvironmentVariable.objects.select_related("environment", "environment__project").all()
    serializer_class = EnvironmentVariableSerializer
    permission_classes = [action_permission("environment.read", "environment.create", "environment.update", "environment.delete")]
    filterset_fields = ["environment", "platform", "is_secret", "is_enabled"]
    search_fields = ["key", "description"]
    audit_module = "environment_variable"


class EnvironmentPreRequestOperationViewSet(OperatorAuditModelViewSet):
    queryset = EnvironmentPreRequestOperation.objects.select_related("environment", "environment__project").prefetch_related("modules").all()
    serializer_class = EnvironmentPreRequestOperationSerializer
    permission_classes = [action_permission("environment.read", "environment.create", "environment.update", "environment.delete")]
    filterset_fields = ["environment", "is_enabled"]
    search_fields = ["name"]
    audit_module = "environment_pre_request"

    @decorators.action(detail=True, methods=["post"], url_path="run")
    def run(self, request, pk=None):
        result = run_pre_request_operation(
            self.get_object(),
            platform=request.data.get("platform") or None,
            variables=request.data.get("variables") or {},
        )
        return Response(result, status=status.HTTP_200_OK if result.get("ok") else status.HTTP_400_BAD_REQUEST)


class EnvironmentRequestControlViewSet(OperatorAuditModelViewSet):
    queryset = EnvironmentRequestControl.objects.select_related("environment", "environment__project").all()
    serializer_class = EnvironmentRequestControlSerializer
    permission_classes = [action_permission("environment.request_control.read", "environment.request_control.create", "environment.request_control.update", "environment.request_control.delete")]
    filterset_fields = ["environment", "is_enabled"]
    search_fields = ["name", "description"]
    audit_module = "environment_request_control"

    def perform_create(self, serializer):
        super().perform_create(serializer)
        clear_environment_request_control_cache(serializer.instance.environment_id)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        clear_environment_request_control_cache(serializer.instance.environment_id)

    def perform_destroy(self, instance):
        environment_id = instance.environment_id
        super().perform_destroy(instance)
        clear_environment_request_control_cache(environment_id)


class DatabaseConnectionViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = DatabaseConnection.objects.select_related("environment", "created_by", "updated_by").all()
    serializer_class = DatabaseConnectionSerializer
    permission_classes = [action_permission("database.read", "database.create", "database.update", "database.delete", "database.execute")]
    filterset_fields = ["environment", "db_type", "is_active", "last_check_status"]
    search_fields = ["name", "description"]
    audit_module = "database_connection"
    delete_object_label = "数据库连接"
    delete_guard_rules = (
        DeleteGuardRule("test_data_sources", "测试数据源"),
    )

    @decorators.action(detail=True, methods=["post"], url_path="check")
    def check(self, request, pk=None):
        return Response(check_database_connection(self.get_object()))


class DataFactoryCapabilityViewSet(OperatorAuditModelViewSet):
    queryset = DataFactoryCapability.objects.select_related("environment", "created_by").all()
    serializer_class = DataFactoryCapabilitySerializer
    permission_classes = [action_permission("capability.read", "capability.create", "capability.update", "capability.delete", "capability.execute")]
    filterset_fields = ["platform", "environment", "is_active"]
    search_fields = ["name", "description", "path"]
    audit_module = "data_factory"


class TestDataSourceViewSet(DeleteGuardMixin, OperatorAuditModelViewSet):
    queryset = TestDataSource.objects.select_related("project", "environment", "database_connection", "created_by", "updated_by").all()
    serializer_class = TestDataSourceSerializer
    permission_classes = [action_permission(("database.read", "automation.read", "api_case.read"), "database.create", "database.update", "database.delete", "database.execute")]
    filterset_fields = ["project", "environment", "database_connection", "source_type", "is_active"]
    search_fields = ["name", "description", "sql"]
    audit_module = "test_data_source"
    delete_object_label = "测试数据源"
    delete_guard_rules = (
        DeleteGuardRule(None, "待执行任务", "当前测试数据源存在待执行或运行中的任务快照引用，请等待任务结束后再删除。", count_active_runs_using_test_data_source),
    )

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(project=serializer.validated_data.get("project") or get_default_project(), created_by=user, updated_by=user)
        self.write_operator_audit(AuditLog.ActionType.CREATE, instance)

    @decorators.action(detail=True, methods=["post"], url_path="run")
    def run(self, request, pk=None):
        result = execute_test_data_source(self.get_object(), request.data.get("variables") or {})
        serializer = self.get_serializer(self.get_object())
        return Response({"ok": True, "result": result, "data_source": serializer.data})
