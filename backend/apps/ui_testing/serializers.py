from rest_framework import serializers

from apps.core.serializers import OperatorFieldsMixin
from apps.ui_testing.models import UiAction, UiCase, UiElement, UiPage, UiSuite
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


class UiSuiteSerializer(DefaultProjectSerializerMixin, OperatorFieldsMixin, serializers.ModelSerializer):
    case_count = serializers.IntegerField(source="case_memberships.count", read_only=True)
    project_unique_fields = ("name",)

    class Meta:
        model = UiSuite
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "case_count"]
        extra_kwargs = {"project": {"required": False}}
        validators = []

    def validate(self, attrs):
        self.validate_project_unique(attrs)
        return attrs


class UiCaseSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    suite_name = serializers.CharField(source="suite.name", read_only=True)
    suite_names = serializers.SerializerMethodField()
    element_count = serializers.IntegerField(source="elements.count", read_only=True)

    class Meta:
        model = UiCase
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "suite_name", "suite_names", "element_count"]
        extra_kwargs = {"suite": {"required": False}}

    def validate(self, attrs):
        suites = attrs.get("suites")
        suite = attrs.get("suite") or getattr(self.instance, "suite", None)
        if not suite and suites:
            attrs["suite"] = suites[0]
        if not attrs.get("suite") and not suite:
            raise serializers.ValidationError("请选择至少一个测试套件。")
        return attrs

    def get_suite_names(self, obj):
        return [suite.name for suite in obj.suites.all()]

    def create(self, validated_data):
        suites = list(validated_data.pop("suites", []))
        elements = list(validated_data.pop("elements", []))
        instance = super().create(validated_data)
        self._sync_relations(instance, suites, elements)
        return instance

    def update(self, instance, validated_data):
        suites = list(validated_data.pop("suites", [])) if "suites" in validated_data else None
        elements = list(validated_data.pop("elements", [])) if "elements" in validated_data else None
        instance = super().update(instance, validated_data)
        self._sync_relations(instance, suites, elements)
        return instance

    def _sync_relations(self, instance, suites, elements):
        if suites is None:
            suites = list(instance.suites.all()) or [instance.suite]
        if not suites and instance.suite_id:
            suites = [instance.suite]
        instance.suites.set(suites)

        if elements is None:
            element_ids = {
                step.get("element_id")
                for step in instance.steps or []
                if isinstance(step, dict) and step.get("element_id")
            }
            elements = list(UiElement.objects.filter(id__in=element_ids))
        instance.elements.set(elements)


class UiElementSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    suite_name = serializers.CharField(source="suite.name", read_only=True)
    page_node_name = serializers.CharField(source="page_node.name", read_only=True)

    class Meta:
        model = UiElement
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "suite_name", "page_node_name"]


class UiPageSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    element_count = serializers.IntegerField(source="elements.count", read_only=True)

    class Meta:
        model = UiPage
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "element_count"]


class UiActionSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = UiAction
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name"]
