from django.conf import settings
from django.db import models

from apps.core.db_comments import apply_model_comments
from apps.core.models import TimestampedModel


class AuthToken(models.Model):
    key = models.CharField(max_length=128, primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strong_auth_tokens")
    access_token_hash = models.CharField(max_length=128, unique=True, null=True, blank=True)
    refresh_token_hash = models.CharField(max_length=128, unique=True, null=True, blank=True)
    access_expires_at = models.DateTimeField(null=True, blank=True)
    refresh_expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table_comment = '登录Token表：保存用户API访问Token。'
        ordering = ["-created"]

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    @staticmethod
    def generate_key() -> str:
        # 使用 64 字节随机数生成 URL 安全 Token，熵值约 512 bit。
        import secrets

        return secrets.token_urlsafe(64)

    def __str__(self) -> str:
        return self.key

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None


class Permission(TimestampedModel):
    class Type(models.TextChoices):
        TAB = "tab", "Tab权限"
        MENU = "menu", "菜单权限"
        ACTION = "action", "功能权限"

    class Action(models.TextChoices):
        PAGE = "page", "页面"
        READ = "read", "读取"
        CREATE = "create", "新增"
        UPDATE = "update", "编辑"
        WRITE = "write", "写入兼容"
        DELETE = "delete", "删除"
        EXPORT = "export", "导出"
        EXECUTE = "execute", "执行"
        ADMIN = "admin", "管理"

    code = models.CharField(max_length=96, unique=True)
    module = models.CharField(max_length=64)
    action = models.CharField(max_length=16, choices=Action.choices)
    name = models.CharField(max_length=64)
    description = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.ACTION)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    route_path = models.CharField(max_length=128, blank=True)
    is_visible = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table_comment = '权限点表：平台功能权限的最小授权单元。'
        ordering = ["sort_order", "module", "action", "code"]

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
        db_table_comment = '角色表：用户角色及其权限集合。'
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
        db_table_comment = '用户资料表：扩展Django用户的角色、状态和安全信息。'
        ordering = ["user__username"]

    def __str__(self) -> str:
        return self.nickname or self.user.username


class UserSession(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="account_sessions")
    token_key = models.CharField(max_length=128, db_index=True)
    device = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    last_active_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table_comment = '用户会话表：记录登录设备、IP和Token活跃状态。'
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
        db_table_comment = '登录尝试表：记录登录成功/失败和失败原因。'
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
        db_table_comment = '审计日志表：记录用户关键操作和目标对象。'
        ordering = ["-created_at"]


apply_model_comments(AuthToken, "登录Token表：保存用户API访问Token。", {
    "key": "Token字符串主键。",
    "user": "绑定用户ID。",
    "created": "Token创建时间。",
})
apply_model_comments(Permission, "权限点表：平台功能权限的最小授权单元。", {
    "code": "权限编码，如 api.read。",
    "module": "权限所属模块。",
    "action": "权限动作。",
    "name": "权限名称。",
    "description": "权限说明。",
    "type": "权限类型：Tab权限、菜单权限或功能权限。",
    "parent": "父级权限ID，用于页面与功能权限的展示归属关系。",
    "route_path": "页面权限对应的前端路由路径。",
    "is_visible": "是否在权限树中展示。",
    "sort_order": "权限树展示排序值。",
})
apply_model_comments(Role, "角色表：用户角色及其权限集合。", {
    "name": "角色名称。",
    "code": "角色编码。",
    "description": "角色说明。",
    "is_builtin": "是否系统内置角色。",
    "is_active": "是否启用。",
})
apply_model_comments(UserProfile, "用户资料表：扩展Django用户的角色、状态和安全信息。", {
    "user": "关联Django用户ID。",
    "nickname": "用户昵称。",
    "role": "用户角色ID。",
    "phone": "手机号。",
    "avatar": "头像URL。",
    "wechat_work_id": "企业微信用户ID。",
    "status": "账号状态。",
    "failed_login_count": "连续登录失败次数。",
    "locked_until": "锁定截止时间。",
    "password_changed_at": "最近密码修改时间。",
    "must_change_password": "是否必须修改密码。",
})
apply_model_comments(UserSession, "用户会话表：记录登录设备、IP和Token活跃状态。", {
    "user": "关联用户ID。",
    "token_key": "登录Token Key。",
    "device": "登录设备描述。",
    "ip_address": "登录IP地址。",
    "user_agent": "浏览器User-Agent。",
    "last_active_at": "最近活跃时间。",
    "expires_at": "会话过期时间。",
    "revoked_at": "会话撤销时间。",
})
apply_model_comments(LoginAttempt, "登录尝试表：记录登录成功/失败和失败原因。", {
    "username": "尝试登录的用户名。",
    "ip_address": "来源IP地址。",
    "success": "是否登录成功。",
    "reason": "失败或拦截原因。",
    "user_agent": "浏览器User-Agent。",
})
apply_model_comments(AuditLog, "审计日志表：记录用户关键操作和目标对象。", {
    "user": "操作用户ID。",
    "username": "操作用户名快照。",
    "action_type": "操作类型。",
    "module": "业务模块。",
    "target_type": "目标对象类型。",
    "target_id": "目标对象ID。",
    "summary": "操作摘要。",
    "detail": "操作详情JSON。",
    "ip_address": "操作来源IP。",
    "user_agent": "浏览器User-Agent。",
    "success": "操作是否成功。",
})
