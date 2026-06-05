from django.contrib import admin

from apps.projects.models import Environment, EnvironmentVariable, Project


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
