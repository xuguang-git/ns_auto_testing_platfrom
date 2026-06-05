from django.contrib import admin

from apps.scheduling.models import ScheduledPlan


@admin.register(ScheduledPlan)
class ScheduledPlanAdmin(admin.ModelAdmin):
    list_display = ["plan", "name", "cron", "is_active", "last_run_at", "next_run_at"]
    search_fields = ["name", "plan__name"]
    list_filter = ["is_active"]
