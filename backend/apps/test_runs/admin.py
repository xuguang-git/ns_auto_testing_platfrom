from django.contrib import admin

from apps.test_runs.models import TestPlan, TestRun, TestRunStep


@admin.register(TestPlan)
class TestPlanAdmin(admin.ModelAdmin):
    list_display = ["project", "name", "plan_type", "environment", "failure_strategy", "is_active", "updated_at"]
    search_fields = ["name", "project__name"]
    list_filter = ["plan_type", "is_active", "project"]
    filter_horizontal = ["api_suites", "api_scenarios", "ui_suites"]


@admin.register(TestRun)
class TestRunAdmin(admin.ModelAdmin):
    list_display = ["plan", "environment", "status", "trigger_type", "started_at", "finished_at", "duration_ms"]
    search_fields = ["plan__name", "celery_task_id"]
    list_filter = ["status", "trigger_type"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(TestRunStep)
class TestRunStepAdmin(admin.ModelAdmin):
    list_display = ["run", "sort_order", "scenario_name", "step_name", "status", "duration_ms"]
    search_fields = ["scenario_name", "step_name"]
    list_filter = ["status"]
