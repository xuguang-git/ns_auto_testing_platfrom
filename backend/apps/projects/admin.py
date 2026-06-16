from django.contrib import admin

from apps.projects.models import DatabaseConnection, Environment, EnvironmentPreRequestOperation, EnvironmentRequestControl, EnvironmentVariable, Project, TestDataSource


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "platforms", "is_active", "created_at", "updated_at"]
    search_fields = ["name", "code"]
    list_filter = ["is_active"]


@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ["project", "name", "env_type", "is_default", "is_readonly", "updated_at"]
    search_fields = ["name", "base_url", "project__name"]
    list_filter = ["project", "env_type", "is_default", "is_readonly"]


@admin.register(EnvironmentVariable)
class EnvironmentVariableAdmin(admin.ModelAdmin):
    list_display = ["environment", "key", "platform", "scope", "is_secret", "is_enabled"]
    search_fields = ["key", "description"]
    list_filter = ["platform", "scope", "is_secret", "is_enabled"]


@admin.register(EnvironmentPreRequestOperation)
class EnvironmentPreRequestOperationAdmin(admin.ModelAdmin):
    list_display = ["environment", "name", "platforms", "is_enabled", "sort_order", "updated_at"]
    search_fields = ["name", "environment__name"]
    list_filter = ["environment", "is_enabled"]
    filter_horizontal = ["modules"]


@admin.register(EnvironmentRequestControl)
class EnvironmentRequestControlAdmin(admin.ModelAdmin):
    list_display = ["environment", "name", "methods", "is_enabled", "updated_at"]
    search_fields = ["name", "description", "environment__name"]
    list_filter = ["environment", "is_enabled"]


@admin.register(DatabaseConnection)
class DatabaseConnectionAdmin(admin.ModelAdmin):
    list_display = ["environment", "name", "db_type", "is_active", "last_check_status", "updated_at"]
    search_fields = ["name", "description"]
    list_filter = ["environment", "db_type", "is_active", "last_check_status"]


@admin.register(TestDataSource)
class TestDataSourceAdmin(admin.ModelAdmin):
    list_display = ["project", "environment", "database_connection", "name", "source_type", "is_active", "run_count"]
    search_fields = ["name", "description", "sql"]
    list_filter = ["project", "environment", "source_type", "is_active"]
