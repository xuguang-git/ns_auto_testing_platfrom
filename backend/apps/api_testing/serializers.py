from rest_framework import serializers

from apps.api_testing.mock_security import mock_proxy_path, mock_rule_path
from apps.api_testing.models import ApiCase, ApiDefinition, ApiMockRule, ApiModule, ApiScenario, ApiStep, ApiSuite, ApiSuiteCase, ApiSuiteScenario, ApiTestCase
from apps.core.serializers import OperatorFieldsMixin
from apps.projects.services import get_default_project


API_SUITE_RUN_CONFIG_FIELDS = {"priority", "environment"}


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
    depth = serializers.SerializerMethodField()
    path_ids = serializers.SerializerMethodField()
    path_names = serializers.SerializerMethodField()
    descendant_api_count = serializers.SerializerMethodField()
    project_unique_fields = ("platform", "parent", "name")

    class Meta:
        model = ApiModule
        fields = "__all__"
        read_only_fields = [
            "created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name",
            "api_count", "test_case_count", "depth", "path_ids", "path_names", "descendant_api_count",
        ]
        extra_kwargs = {"project": {"required": False}}
        validators = []

    def get_api_count(self, obj):
        return obj.apis.count()

    def get_test_case_count(self, obj):
        return sum(api.test_cases.count() for api in obj.apis.all())

    def _path(self, obj):
        nodes = []
        current = obj
        while current:
            nodes.append(current)
            current = current.parent
        return list(reversed(nodes))

    def _descendant_ids(self, obj):
        ids = [obj.id]
        pending = [obj.id]
        while pending:
            children = list(ApiModule.objects.filter(parent_id__in=pending).values_list("id", flat=True))
            ids.extend(children)
            pending = children
        return ids

    def get_depth(self, obj):
        return len(self._path(obj))

    def get_path_ids(self, obj):
        return [item.id for item in self._path(obj)]

    def get_path_names(self, obj):
        return [item.name for item in self._path(obj)]

    def get_descendant_api_count(self, obj):
        return ApiDefinition.objects.filter(module_id__in=self._descendant_ids(obj)).count()

    def validate(self, attrs):
        project = self.get_project_value(attrs)
        platform = attrs.get("platform", getattr(self.instance, "platform", ""))
        managed_platform = attrs.get("managed_platform", getattr(self.instance, "managed_platform", None))
        parent = attrs.get("parent", getattr(self.instance, "parent", None))

        if parent:
            if self.instance and parent.id == self.instance.id:
                raise serializers.ValidationError({"parent": "上级模块不能选择自身。"})
            if parent.project_id != project.id or parent.platform != platform:
                raise serializers.ValidationError({"parent": "上级模块必须属于同一项目、同一平台。"})
            if parent.managed_platform_id != getattr(managed_platform, "id", None):
                raise serializers.ValidationError({"parent": "上级模块必须属于同一平台管理记录。"})

            ancestor = parent
            while ancestor:
                if self.instance and ancestor.id == self.instance.id:
                    raise serializers.ValidationError({"parent": "不能将模块移动到自身或自身后代。"})
                ancestor = ancestor.parent

        parent_depth = 0
        ancestor = parent
        while ancestor:
            parent_depth += 1
            ancestor = ancestor.parent

        subtree_height = 1
        if self.instance:
            pending = [(self.instance.id, 1)]
            while pending:
                parent_id, height = pending.pop()
                subtree_height = max(subtree_height, height)
                pending.extend((child_id, height + 1) for child_id in ApiModule.objects.filter(parent_id=parent_id).values_list("id", flat=True))
        if parent_depth + subtree_height > 3:
            raise serializers.ValidationError({"parent": "模块最多支持三级，当前移动会超过层级限制。"})

        self.validate_project_unique(attrs)
        return attrs


class ApiDefinitionSerializer(DefaultProjectSerializerMixin, OperatorFieldsMixin, serializers.ModelSerializer):
    test_case_count = serializers.SerializerMethodField()
    mock_count = serializers.SerializerMethodField()
    module_path_names = serializers.SerializerMethodField()
    project_unique_fields = ("platform", "method", "path")

    class Meta:
        model = ApiDefinition
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "test_case_count", "mock_count", "module_path_names"]
        extra_kwargs = {"project": {"required": False}}
        validators = []

    def validate(self, attrs):
        module = attrs.get("module", getattr(self.instance, "module", None))
        project = self.get_project_value(attrs)
        platform = attrs.get("platform", getattr(self.instance, "platform", ""))
        if module and (module.project_id != project.id or module.platform != platform):
            raise serializers.ValidationError({"module": "所属模块必须与接口属于同一项目、同一平台。"})
        self.validate_project_unique(attrs)
        return attrs

    def get_test_case_count(self, obj):
        request = self.context.get("request")
        if request and request.query_params.get("single_case_tree") and obj.status != ApiDefinition.Status.RELEASED:
            return None
        return obj.test_cases.count()

    def get_mock_count(self, obj):
        return obj.mock_rules.count()

    def get_module_path_names(self, obj):
        names = []
        current = obj.module
        while current:
            names.append(current.name)
            current = current.parent
        return list(reversed(names))


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
    mock_path = serializers.SerializerMethodField()
    mock_public_path = serializers.SerializerMethodField()
    mock_proxy_path = serializers.SerializerMethodField()
    mock_public_proxy_path = serializers.SerializerMethodField()

    class Meta:
        model = ApiMockRule
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
            "api_name",
            "api_path",
            "method",
            "mock_path",
            "mock_public_path",
            "mock_proxy_path",
            "mock_public_proxy_path",
        ]

    def get_mock_path(self, obj):
        return mock_rule_path(obj)

    def get_mock_public_path(self, obj):
        return mock_rule_path(obj, with_token=True)

    def get_mock_proxy_path(self, obj):
        return mock_proxy_path(obj)

    def get_mock_public_proxy_path(self, obj):
        return mock_proxy_path(obj, with_token=True)


class ApiSuiteSerializer(DefaultProjectSerializerMixin, OperatorFieldsMixin, serializers.ModelSerializer):
    project_unique_fields = ("name",)
    case_count = serializers.SerializerMethodField()
    scenario_count = serializers.SerializerMethodField()

    class Meta:
        model = ApiSuite
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "case_ids", "case_count", "scenario_count"]
        extra_kwargs = {"project": {"required": False}}
        validators = []

    def validate(self, attrs):
        self.validate_project_unique(attrs)
        return attrs

    def validate_run_config(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("套件运行配置格式不正确。")
        return {key: value[key] for key in API_SUITE_RUN_CONFIG_FIELDS if key in value}

    def get_case_count(self, obj):
        return obj.case_links.count()

    def get_scenario_count(self, obj):
        return obj.scenario_links.count()


class ApiSuiteDetailSerializer(ApiSuiteSerializer):
    case_items = serializers.SerializerMethodField()
    scenario_items = serializers.SerializerMethodField()

    class Meta(ApiSuiteSerializer.Meta):
        read_only_fields = [*ApiSuiteSerializer.Meta.read_only_fields, "case_items", "scenario_items"]

    def get_case_items(self, obj):
        ordered_cases = [
            link.case
            for link in ApiSuiteCase.objects.filter(suite=obj).select_related("case", "case__api", "case__api__module")
        ]
        return ApiTestCaseSerializer(ordered_cases, many=True, context=self.context).data

    def get_scenario_items(self, obj):
        scenarios = [
            link.scenario
            for link in ApiSuiteScenario.objects.filter(suite=obj).select_related("scenario")
        ]
        return ApiScenarioSerializer(scenarios, many=True, context=self.context).data


class ApiSuiteMembersSerializer(serializers.Serializer):
    scenario_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)
    case_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)
    run_config = serializers.DictField(required=False)

    def validate(self, attrs):
        for field in ("scenario_ids", "case_ids"):
            values = attrs.get(field, [])
            if len(values) != len(set(values)):
                raise serializers.ValidationError({field: "不能包含重复成员。"})
        run_config = attrs.get("run_config")
        if run_config is not None:
            if not isinstance(run_config, dict):
                raise serializers.ValidationError({"run_config": "套件运行配置格式不正确。"})
            attrs["run_config"] = {key: run_config[key] for key in API_SUITE_RUN_CONFIG_FIELDS if key in run_config}
        return attrs


class ApiScenarioSerializer(DefaultProjectSerializerMixin, OperatorFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = ApiScenario
        fields = "__all__"
        read_only_fields = ["suite", "created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name"]
        extra_kwargs = {"project": {"required": False}}


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
