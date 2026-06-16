from rest_framework import serializers

from apps.api_testing.models import ApiCase, ApiDefinition, ApiMockRule, ApiModule, ApiScenario, ApiStep, ApiSuite, ApiTestCase
from apps.core.serializers import OperatorFieldsMixin
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
            raise serializers.ValidationError("同一项目下已存在相同记录。")


class ApiModuleSerializer(DefaultProjectSerializerMixin, OperatorFieldsMixin, serializers.ModelSerializer):
    api_count = serializers.SerializerMethodField()
    test_case_count = serializers.SerializerMethodField()
    project_unique_fields = ("platform", "parent", "name")

    class Meta:
        model = ApiModule
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "api_count", "test_case_count"]
        extra_kwargs = {"project": {"required": False}}
        validators = []

    def get_api_count(self, obj):
        return obj.apis.count()

    def get_test_case_count(self, obj):
        return sum(api.test_cases.count() for api in obj.apis.all())

    def validate(self, attrs):
        self.validate_project_unique(attrs)
        return attrs


class ApiDefinitionSerializer(DefaultProjectSerializerMixin, OperatorFieldsMixin, serializers.ModelSerializer):
    test_case_count = serializers.SerializerMethodField()
    mock_count = serializers.SerializerMethodField()
    project_unique_fields = ("platform", "method", "path")

    class Meta:
        model = ApiDefinition
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "test_case_count", "mock_count"]
        extra_kwargs = {"project": {"required": False}}
        validators = []

    def validate(self, attrs):
        self.validate_project_unique(attrs)
        return attrs

    def get_test_case_count(self, obj):
        request = self.context.get("request")
        if request and request.query_params.get("single_case_tree") and obj.status != ApiDefinition.Status.RELEASED:
            return None
        return obj.test_cases.count()

    def get_mock_count(self, obj):
        return obj.mock_rules.count()


class ApiTestCaseSerializer(DefaultProjectSerializerMixin, OperatorFieldsMixin, serializers.ModelSerializer):
    api_name = serializers.CharField(source="api.name", read_only=True)
    api_path = serializers.CharField(source="api.path", read_only=True)
    method = serializers.CharField(source="api.method", read_only=True)
    platform = serializers.CharField(source="api.platform", read_only=True)
    module = serializers.IntegerField(source="api.module_id", read_only=True)
    project_unique_fields = ("api", "name")

    class Meta:
        model = ApiTestCase
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "api_name", "api_path", "method", "platform", "module"]
        extra_kwargs = {"project": {"required": False}}
        validators = []

    def validate(self, attrs):
        self.validate_project_unique(attrs)
        return attrs


class ApiMockRuleSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    api_name = serializers.CharField(source="api.name", read_only=True)
    api_path = serializers.CharField(source="api.path", read_only=True)
    method = serializers.CharField(source="api.method", read_only=True)

    class Meta:
        model = ApiMockRule
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "api_name", "api_path", "method"]


class ApiSuiteSerializer(DefaultProjectSerializerMixin, OperatorFieldsMixin, serializers.ModelSerializer):
    project_unique_fields = ("name",)

    class Meta:
        model = ApiSuite
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name"]
        extra_kwargs = {"project": {"required": False}}
        validators = []

    def validate(self, attrs):
        self.validate_project_unique(attrs)
        return attrs


class ApiScenarioSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = ApiScenario
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name"]


class ApiStepSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = ApiStep
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name"]


class ApiCaseSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = ApiCase
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name"]
