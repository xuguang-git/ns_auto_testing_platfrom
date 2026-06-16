from django.contrib import admin

from apps.api_testing.models import ApiCase, ApiDefinition, ApiMockRule, ApiModule, ApiScenario, ApiStep, ApiSuite, ApiTestCase


@admin.register(ApiModule)
class ApiModuleAdmin(admin.ModelAdmin):
    list_display = ["project", "platform", "parent", "name", "sort_order"]
    search_fields = ["name", "project__name"]
    list_filter = ["project", "platform"]


@admin.register(ApiDefinition)
class ApiDefinitionAdmin(admin.ModelAdmin):
    list_display = ["project", "platform", "method", "path", "name", "status", "is_active"]
    search_fields = ["name", "path", "description"]
    list_filter = ["project", "platform", "method", "status", "is_active"]


@admin.register(ApiTestCase)
class ApiTestCaseAdmin(admin.ModelAdmin):
    list_display = ["project", "api", "name", "priority", "status", "is_active", "updated_at"]
    search_fields = ["name", "api__name", "api__path", "project__name"]
    list_filter = ["project", "status", "priority", "is_active"]


@admin.register(ApiMockRule)
class ApiMockRuleAdmin(admin.ModelAdmin):
    list_display = ["api", "name", "enabled", "status_code", "delay_ms", "updated_at"]
    search_fields = ["name", "api__name", "api__path"]
    list_filter = ["enabled", "status_code"]


@admin.register(ApiSuite)
class ApiSuiteAdmin(admin.ModelAdmin):
    list_display = ["project", "name", "platforms", "is_active", "created_at", "updated_at"]
    search_fields = ["name", "project__name"]
    list_filter = ["project", "is_active"]


@admin.register(ApiScenario)
class ApiScenarioAdmin(admin.ModelAdmin):
    list_display = ["suite", "name", "environment", "priority", "is_active", "sort_order"]
    search_fields = ["name", "suite__name", "environment__name"]
    list_filter = ["priority", "is_active", "environment"]


@admin.register(ApiStep)
class ApiStepAdmin(admin.ModelAdmin):
    list_display = ["scenario", "name", "platform", "method", "path", "is_active", "sort_order"]
    search_fields = ["name", "path", "scenario__name"]
    list_filter = ["platform", "method", "is_active"]


@admin.register(ApiCase)
class ApiCaseAdmin(admin.ModelAdmin):
    list_display = ["suite", "name", "method", "path", "is_active", "sort_order"]
    search_fields = ["name", "path", "suite__name"]
    list_filter = ["method", "is_active", "suite__project"]
