from django.contrib import admin

from apps.ui_testing.models import UiCase, UiSuite


@admin.register(UiSuite)
class UiSuiteAdmin(admin.ModelAdmin):
    list_display = ["project", "name", "created_at", "updated_at"]
    search_fields = ["name", "project__name"]
    list_filter = ["project"]


@admin.register(UiCase)
class UiCaseAdmin(admin.ModelAdmin):
    list_display = ["suite", "name", "browser", "is_active", "sort_order"]
    search_fields = ["name", "start_url", "suite__name"]
    list_filter = ["browser", "is_active", "suite__project"]
