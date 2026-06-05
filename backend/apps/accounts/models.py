from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class Permission(TimestampedModel):
    class Action(models.TextChoices):
        READ = "read", "读取"
        WRITE = "write", "写入"
        DELETE = "delete", "删除"
        EXPORT = "export", "导出"
        EXECUTE = "execute", "执行"
        ADMIN = "admin", "管理"

    code = models.CharField(max_length=96, unique=True)
    module = models.CharField(max_length=64)
    action = models.CharField(max_length=16, choices=Action.choices)
    name = models.CharField(max_length=64)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["module", "action", "code"]

    def __str__(self) -> str:
        return self.name


class Role(TimestampedModel):
    class BuiltinCode(models.TextChoices):
        SUPER_ADMIN = "super_admin", "超级管理员"
        TEST_MANAGER = "test_manager", "测试主管"
        TEST_ENGINEER = "test_engineer", "测试工程师"
        DEVELOPER = "developer", "开发工程师"
        GUEST = "guest", "访客"

    name = models.CharField(max_length=32, unique=True)
    code = models.SlugField(max_length=32, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_builtin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")

    class Meta:
        ordering = ["-is_builtin", "id"]

    def __str__(self) -> str:
        return self.name


class UserProfile(TimestampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "启用"
        DISABLED = "disabled", "禁用"
        LOCKED = "locked", "锁定"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    nickname = models.CharField(max_length=32)
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.SET_NULL, related_name="users")
    phone = models.CharField(max_length=32, blank=True)
    avatar = models.URLField(blank=True)
    wechat_work_id = models.CharField(max_length=64, blank=True, unique=True, null=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    failed_login_count = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(default=False)

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:
        return self.nickname or self.user.username


class UserSession(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="account_sessions")
    token_key = models.CharField(max_length=40, db_index=True)
    device = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    last_active_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_active_at", "-created_at"]

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


class LoginAttempt(TimestampedModel):
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    success = models.BooleanField(default=False)
    reason = models.CharField(max_length=255, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class AuditLog(TimestampedModel):
    class ActionType(models.TextChoices):
        LOGIN = "login", "登录"
        LOGOUT = "logout", "退出"
        CREATE = "create", "创建"
        UPDATE = "update", "修改"
        DELETE = "delete", "删除"
        ENABLE = "enable", "启用"
        DISABLE = "disable", "禁用"
        RESET_PASSWORD = "reset_password", "重置密码"
        FORCE_LOGOUT = "force_logout", "强制下线"
        EXPORT = "export", "导出"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    username = models.CharField(max_length=150, blank=True)
    action_type = models.CharField(max_length=32, choices=ActionType.choices)
    module = models.CharField(max_length=64)
    target_type = models.CharField(max_length=64, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    summary = models.CharField(max_length=255)
    detail = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
