from django.contrib import admin

from apps.test_runs.models import TestRun, TestRunStep


@admin.register(TestRun)
class TestRunAdmin(admin.ModelAdmin):
    list_display = ["suite", "environment", "status", "trigger_type", "started_at", "finished_at", "duration_ms"]
    search_fields = ["suite__name", "celery_task_id"]
    list_filter = ["status", "trigger_type"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(TestRunStep)
class TestRunStepAdmin(admin.ModelAdmin):
    list_display = ["run", "sort_order", "scenario_name", "step_name", "status", "duration_ms"]
    search_fields = ["scenario_name", "step_name"]
    list_filter = ["status"]
