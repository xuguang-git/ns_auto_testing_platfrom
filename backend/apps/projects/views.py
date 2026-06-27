from rest_framework import decorators, mixins, status, viewsets
from rest_framework.response import Response

from apps.accounts.models import AuditLog
from apps.accounts.permissions import action_permission
from apps.api_testing.models import ApiModule
from apps.core.delete_guards import DeleteGuardMixin, DeleteGuardRule
from apps.api_testing.services import clear_environment_request_control_cache
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


class TestDataSourceViewSet(OperatorAuditModelViewSet):
    queryset = TestDataSource.objects.select_related("project", "environment", "database_connection", "created_by", "updated_by").all()
    serializer_class = TestDataSourceSerializer
    permission_classes = [action_permission(("database.read", "automation.read", "api_case.read"), "database.create", "database.update", "database.delete", "database.execute")]
    filterset_fields = ["project", "environment", "database_connection", "source_type", "is_active"]
    search_fields = ["name", "description", "sql"]
    audit_module = "test_data_source"

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(project=serializer.validated_data.get("project") or get_default_project(), created_by=user, updated_by=user)
        self.write_operator_audit(AuditLog.ActionType.CREATE, instance)

    @decorators.action(detail=True, methods=["post"], url_path="run")
    def run(self, request, pk=None):
        result = execute_test_data_source(self.get_object(), request.data.get("variables") or {})
        serializer = self.get_serializer(self.get_object())
        return Response({"ok": True, "result": result, "data_source": serializer.data})
