from rest_framework import serializers

from apps.api_testing.models import ApiDefinition, ApiModule
from apps.core.serializers import OperatorFieldsMixin
from apps.projects.db_services import validate_select_sql
from apps.projects.models import (
    DataFactoryCapability,
    DatabaseConnection,
    Environment,
    EnvironmentPreRequestOperation,
    EnvironmentRequestControl,
    EnvironmentVariable,
    Platform,
    Project,
    TestDataSource,
)
from apps.projects.services import get_default_project


class DefaultProjectSerializerMixin:
    project_unique_fields: tuple[str, ...] = ()

    def get_project_value(self, attrs):
        return attrs.get("project") or getattr(self.instance, "project", None) or get_default_project()

    def validate_project_unique(self, attrs):
        if not self.project_unique_fields:
            return
        project = self.get_project_value(attrs)
        filters = {"project": project}
        for field in self.project_unique_fields:
            value = attrs.get(field, getattr(self.instance, field, None))
            filters[field] = value
        if any(value is None for value in filters.values()):
            return
        queryset = self.Meta.model.objects.filter(**filters)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("同一项目下已存在相同名称的数据源。")


class ProjectSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name"]


class PlatformSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    module_count = serializers.SerializerMethodField()
    api_count = serializers.SerializerMethodField()

    class Meta:
        model = Platform
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "module_count", "api_count"]

    def get_module_count(self, obj):
        return obj.api_modules.count()

    def get_api_count(self, obj):
        legacy_code = obj.code.upper()
        return ApiDefinition.objects.filter(platform=legacy_code).count()


class EnvironmentVariableSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    display_value = serializers.SerializerMethodField()

    class Meta:
        model = EnvironmentVariable
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "display_value"]

    def get_display_value(self, obj):
        return "***" if obj.is_secret and obj.value else obj.value


class EnvironmentPreRequestOperationSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    modules = serializers.PrimaryKeyRelatedField(queryset=ApiModule.objects.all(), many=True, required=False)
    module_names = serializers.SerializerMethodField()
    scope_labels = serializers.SerializerMethodField()

    class Meta:
        model = EnvironmentPreRequestOperation
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
            "module_names",
            "scope_labels",
        ]

    def get_module_names(self, obj):
        return [{"id": item.id, "name": item.name, "platform": item.platform} for item in obj.modules.all()]

    def get_scope_labels(self, obj):
        platform_names = {item.code.upper(): item.name for item in Platform.objects.all()}
        labels = [platform_names.get(str(code).upper(), str(code).upper()) for code in obj.platforms or []]
        labels.extend(f"{item.name}({item.platform})" for item in obj.modules.all())
        return labels

    def validate_platforms(self, value):
        return sorted({str(item).upper().strip() for item in value or [] if str(item).strip()})

    def validate_config(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("前置操作配置必须是对象。")
        return value

    def validate(self, attrs):
        environment = attrs.get("environment") or getattr(self.instance, "environment", None)
        platforms = attrs.get("platforms", getattr(self.instance, "platforms", []))
        modules = attrs.get("modules", None)
        selected_modules = list(modules) if modules is not None else list(self.instance.modules.all()) if self.instance else []
        if not environment:
            raise serializers.ValidationError({"environment": "请选择所属环境。"})
        if not platforms and not selected_modules:
            raise serializers.ValidationError("请选择至少一个生效平台或模块。")

        module_platforms = {str(item.platform).upper() for item in selected_modules}
        duplicate_platforms = sorted(set(platforms) & module_platforms)
        if duplicate_platforms:
            raise serializers.ValidationError(f"已选择平台 {', '.join(duplicate_platforms)}，无需再选择其下模块。")

        queryset = EnvironmentPreRequestOperation.objects.filter(environment=environment)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        queryset = queryset.prefetch_related("modules")
        selected_module_ids = {item.id for item in selected_modules}
        selected_platforms = {str(item).upper() for item in platforms}

        for operation in queryset:
            operation_platforms = {str(item).upper() for item in operation.platforms or []}
            operation_modules = list(operation.modules.all())
            operation_module_ids = {item.id for item in operation_modules}
            operation_module_platforms = {str(item.platform).upper() for item in operation_modules}

            if selected_platforms & operation_platforms:
                raise serializers.ValidationError(f"生效平台已被前置操作「{operation.name}」占用。")
            if selected_module_ids & operation_module_ids:
                raise serializers.ValidationError(f"生效模块已被前置操作「{operation.name}」占用。")
            if selected_platforms & operation_module_platforms:
                raise serializers.ValidationError(f"前置操作「{operation.name}」已选择该平台下的模块，不能再选择整个平台。")
            if selected_module_ids and operation_platforms & module_platforms:
                raise serializers.ValidationError(f"前置操作「{operation.name}」已选择整个平台，不能重复选择其下模块。")

        attrs["platforms"] = list(selected_platforms)
        return attrs


class EnvironmentRequestControlSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = EnvironmentRequestControl
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name"]

    def validate_methods(self, value):
        allowed = {choice[0] for choice in EnvironmentRequestControl.HttpMethod.choices}
        methods = sorted({str(item).upper().strip() for item in value or [] if str(item).strip()})
        invalid = [item for item in methods if item not in allowed]
        if invalid:
            raise serializers.ValidationError(f"不支持的请求方法：{', '.join(invalid)}")
        if not methods:
            raise serializers.ValidationError("请至少选择一个请求方法")
        return methods


class EnvironmentSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    variable_items = EnvironmentVariableSerializer(many=True, read_only=True)
    pre_request_operations = EnvironmentPreRequestOperationSerializer(many=True, read_only=True)
    request_controls = EnvironmentRequestControlSerializer(many=True, read_only=True)

    class Meta:
        model = Environment
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name"]
        extra_kwargs = {"token_session": {"write_only": True, "required": False}}


class DatabaseConnectionSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    environment_name = serializers.CharField(source="environment.name", read_only=True)

    class Meta:
        model = DatabaseConnection
        fields = [
            "id",
            "name",
            "db_type",
            "environment",
            "environment_name",
            "description",
            "is_active",
            "last_check_status",
            "last_check_message",
            "last_checked_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

class DataFactoryCapabilitySerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    environment_name = serializers.CharField(source="environment.name", read_only=True)

    class Meta:
        model = DataFactoryCapability
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "environment_name"]


class TestDataSourceSerializer(DefaultProjectSerializerMixin, OperatorFieldsMixin, serializers.ModelSerializer):
    environment_name = serializers.CharField(source="environment.name", read_only=True)
    database_connection_name = serializers.CharField(source="database_connection.name", read_only=True)
    project_unique_fields = ("name",)

    class Meta:
        model = TestDataSource
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
            "environment_name",
            "database_connection_name",
            "last_result",
            "run_count",
        ]
        extra_kwargs = {"project": {"required": False}}
        validators = []

    def validate_sql(self, value):
        validate_select_sql(value)
        return value

    def validate(self, attrs):
        attrs["project"] = self.get_project_value(attrs)
        self.validate_project_unique(attrs)
        connection = attrs.get("database_connection") or getattr(self.instance, "database_connection", None)
        environment = attrs.get("environment") or getattr(self.instance, "environment", None)
        if connection and environment and connection.environment_id != environment.id:
            raise serializers.ValidationError("查询数据源环境必须和数据库连接所属环境一致。")
        if connection and not environment:
            attrs["environment"] = connection.environment
        return attrs
