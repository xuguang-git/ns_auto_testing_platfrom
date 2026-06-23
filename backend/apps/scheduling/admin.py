from django.contrib import admin

from apps.scheduling.models import NotificationChannel, NotificationSendLog, NotificationTemplate, ScheduledPlan


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ["name", "notification_type", "push_platform", "is_active", "updated_at"]
    list_filter = ["notification_type", "push_platform", "is_active"]
    search_fields = ["name"]
    readonly_fields = ["webhook_ciphertext", "signature_ciphertext"]


@admin.register(ScheduledPlan)
class ScheduledPlanAdmin(admin.ModelAdmin):
    list_display = ["suite", "name", "cron", "notify_on", "notification_template", "is_active", "last_run_at", "next_run_at"]
    search_fields = ["name", "suite__name"]
    list_filter = ["is_active", "notify_on"]
    filter_horizontal = ["notifications"]


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "biz_type", "channel", "is_active", "updated_at"]
    list_filter = ["biz_type", "channel", "is_active"]
    search_fields = ["name"]


@admin.register(NotificationSendLog)
class NotificationSendLogAdmin(admin.ModelAdmin):
    list_display = ["channel", "template", "schedule", "test_run", "status", "sent_at"]
    list_filter = ["status"]
    search_fields = ["title", "error_message"]
    readonly_fields = ["title", "content", "error_message"]
