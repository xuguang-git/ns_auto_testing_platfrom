from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import AuditLog, LoginAttempt, Permission, Role, UserProfile, UserSession


PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,32}$")

PERMISSION_DEFINITIONS = [
    ("platform.read", "platform", "read", "平台查看"),
    ("platform.write", "platform", "write", "平台维护"),
    ("platform.delete", "platform", "delete", "平台删除"),
    ("module.read", "module", "read", "模块查看"),
    ("module.write", "module", "write", "模块维护"),
    ("module.delete", "module", "delete", "模块删除"),
    ("environment.read", "environment", "read", "环境查看"),
    ("environment.write", "environment", "write", "环境维护"),
    ("environment.delete", "environment", "delete", "环境删除"),
    ("api.read", "api", "read", "接口查看"),
    ("api.write", "api", "write", "接口维护"),
    ("api.delete", "api", "delete", "接口删除"),
    ("api.debug", "api", "execute", "接口调试"),
    ("plan.read", "plan", "read", "测试计划查看"),
    ("plan.write", "plan", "write", "测试计划维护"),
    ("plan.delete", "plan", "delete", "测试计划删除"),
    ("run.read", "run", "read", "执行记录查看"),
    ("run.execute", "run", "execute", "执行测试计划"),
    ("report.read", "report", "read", "报告查看"),
    ("report.export", "report", "export", "报告导出"),
    ("schedule.read", "schedule", "read", "调度查看"),
    ("schedule.write", "schedule", "write", "调度维护"),
    ("schedule.delete", "schedule", "delete", "调度删除"),
    ("user.read", "user", "read", "用户查看"),
    ("user.write", "user", "write", "用户维护"),
    ("user.delete", "user", "delete", "用户删除"),
    ("role.read", "role", "read", "角色查看"),
    ("role.write", "role", "write", "角色维护"),
    ("role.delete", "role", "delete", "角色删除"),
    ("audit.read", "audit", "read", "审计查看"),
    ("audit.export", "audit", "export", "审计导出"),
    ("system.admin", "system", "admin", "系统设置"),
]

ROLE_PERMISSION_CODES = {
    Role.BuiltinCode.SUPER_ADMIN: [item[0] for item in PERMISSION_DEFINITIONS],
    Role.BuiltinCode.TEST_MANAGER: [
        "platform.read",
        "module.read",
        "module.write",
        "module.delete",
        "environment.read",
        "environment.write",
        "environment.delete",
        "api.read",
        "api.write",
        "api.delete",
        "api.debug",
        "plan.read",
        "plan.write",
        "plan.delete",
        "run.read",
        "run.execute",
        "report.read",
        "report.export",
        "schedule.read",
        "schedule.write",
        "schedule.delete",
        "user.read",
        "user.write",
        "audit.read",
    ],
    Role.BuiltinCode.TEST_ENGINEER: [
        "module.read",
        "environment.read",
        "environment.write",
        "api.read",
        "api.write",
        "api.delete",
        "api.debug",
        "plan.read",
        "plan.write",
        "run.read",
        "run.execute",
        "report.read",
        "report.export",
        "schedule.read",
    ],
    Role.BuiltinCode.DEVELOPER: ["environment.read", "api.read", "report.read", "run.read"],
    Role.BuiltinCode.GUEST: ["report.read"],
}

ROLE_NAMES = {
    Role.BuiltinCode.SUPER_ADMIN: "超级管理员",
    Role.BuiltinCode.TEST_MANAGER: "测试主管",
    Role.BuiltinCode.TEST_ENGINEER: "测试工程师",
    Role.BuiltinCode.DEVELOPER: "开发工程师",
    Role.BuiltinCode.GUEST: "访客",
}


def validate_password_policy(password: str) -> None:
    if not PASSWORD_RE.match(password or ""):
        raise ValueError("密码需为 8-32 位，并包含大写字母、小写字母和数字")


def ensure_builtin_roles() -> None:
    permission_map = {}
    for code, module, action, name in PERMISSION_DEFINITIONS:
        permission, _ = Permission.objects.get_or_create(
            code=code,
            defaults={"module": module, "action": action, "name": name},
        )
        permission_map[code] = permission

    for code, name in ROLE_NAMES.items():
        role, _ = Role.objects.get_or_create(
            code=code,
            defaults={"name": name, "is_builtin": True, "description": f"系统预置角色：{name}"},
        )
        role.name = name
        role.is_builtin = True
        role.is_active = True
        role.save(update_fields=["name", "is_builtin", "is_active", "updated_at"])
        role.permissions.set(permission_map[item] for item in ROLE_PERMISSION_CODES[code])


def get_default_role() -> Role | None:
    ensure_builtin_roles()
    return Role.objects.filter(code=Role.BuiltinCode.TEST_ENGINEER).first()


def ensure_profile(user, role: Role | None = None) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "nickname": user.get_full_name() or user.username,
            "role": role or get_default_role(),
            "password_changed_at": timezone.now(),
        },
    )
    return profile


def user_permission_codes(user) -> set[str]:
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return {item[0] for item in PERMISSION_DEFINITIONS}
    profile = getattr(user, "profile", None)
    if not profile or profile.status != UserProfile.Status.ACTIVE or not profile.role or not profile.role.is_active:
        return set()
    return set(profile.role.permissions.values_list("code", flat=True))


def has_permission(user, permission_code: str) -> bool:
    return permission_code in user_permission_codes(user)


def get_client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_user_agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")


def write_audit(
    *,
    request=None,
    user=None,
    action_type: str,
    module: str,
    summary: str,
    target_type: str = "",
    target_id: str = "",
    detail: dict[str, Any] | None = None,
    success: bool = True,
) -> AuditLog:
    actor = user or getattr(request, "user", None)
    if not getattr(actor, "is_authenticated", False):
        actor = None
    return AuditLog.objects.create(
        user=actor,
        username=getattr(actor, "username", "") or "",
        action_type=action_type,
        module=module,
        target_type=target_type,
        target_id=str(target_id or ""),
        summary=summary,
        detail=detail or {},
        ip_address=get_client_ip(request) if request else None,
        user_agent=get_user_agent(request) if request else "",
        success=success,
    )


def write_login_attempt(request, username: str, success: bool, reason: str = "") -> LoginAttempt:
    return LoginAttempt.objects.create(
        username=username,
        ip_address=get_client_ip(request),
        success=success,
        reason=reason,
        user_agent=get_user_agent(request),
    )


def create_user_session(request, user, token, remember_me: bool = False) -> UserSession:
    expires_at = timezone.now() + (timedelta(days=30) if remember_me else timedelta(hours=2))
    return UserSession.objects.create(
        user=user,
        token_key=token.key,
        device=get_user_agent(request)[:255],
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        last_active_at=timezone.now(),
        expires_at=expires_at,
    )


def revoke_user_sessions(user) -> int:
    return UserSession.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())


def bootstrap_superuser_profile() -> None:
    ensure_builtin_roles()
    User = get_user_model()
    super_role = Role.objects.get(code=Role.BuiltinCode.SUPER_ADMIN)
    for user in User.objects.filter(is_superuser=True):
        profile = ensure_profile(user, super_role)
        if profile.role_id != super_role.id:
            profile.role = super_role
            profile.save(update_fields=["role", "updated_at"])
