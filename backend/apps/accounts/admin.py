from django.contrib import admin

from apps.accounts.models import AuditLog, LoginAttempt, Permission, Role, UserProfile, UserSession


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["code", "module", "action", "name"]
    search_fields = ["code", "name", "module"]
    list_filter = ["module", "action"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_builtin", "is_active"]
    search_fields = ["name", "code"]
    list_filter = ["is_builtin", "is_active"]
    filter_horizontal = ["permissions"]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "nickname", "role", "status", "phone", "wechat_work_id"]
    search_fields = ["user__username", "nickname", "phone", "wechat_work_id"]
    list_filter = ["role", "status"]


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "ip_address", "last_active_at", "expires_at", "revoked_at"]
    search_fields = ["user__username", "ip_address", "device"]
    list_filter = ["revoked_at"]


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ["username", "ip_address", "success", "reason", "created_at"]
    search_fields = ["username", "ip_address", "reason"]
    list_filter = ["success"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "username", "action_type", "module", "summary", "success"]
    search_fields = ["username", "summary", "target_type", "target_id"]
    list_filter = ["action_type", "module", "success"]
    readonly_fields = ["created_at", "updated_at"]
