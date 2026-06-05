from rest_framework import serializers

from apps.api_testing.models import ApiDefinition
from apps.core.serializers import OperatorFieldsMixin
from apps.projects.models import DataFactoryCapability, Environment, EnvironmentVariable, Platform, Project


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


class EnvironmentSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    variable_items = EnvironmentVariableSerializer(many=True, read_only=True)

    class Meta:
        model = Environment
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name"]
        extra_kwargs = {"token_session": {"write_only": True, "required": False}}


class DataFactoryCapabilitySerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    environment_name = serializers.CharField(source="environment.name", read_only=True)

    class Meta:
        model = DataFactoryCapability
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by", "updated_by", "created_by_name", "updated_by_name", "environment_name"]
