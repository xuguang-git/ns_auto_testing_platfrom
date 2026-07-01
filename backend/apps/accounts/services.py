from __future__ import annotations

import re
import threading
from contextlib import contextmanager
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.accounts.models import AuditLog, LoginAttempt, Permission, Role, UserProfile, UserSession


PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,32}$")
MAX_LOGIN_FAILURES = 5
LOGIN_LOCK_MINUTES = 15
DEFAULT_PROTECTED_USERNAMES = {"admin"}
PROTECTED_USER_PROFILE_MESSAGE = "系统保护账号仅允许本人在个人中心维护基础信息和密码。"
_protected_user_guard = threading.local()

PAGE_PERMISSION_DEFINITIONS = [
    {
        "code": "page.dashboard",
        "module": "dashboard",
        "name": "控制台",
        "route_path": "/dashboard",
        "sort_order": 10,
        "children": [],
    },
    {
        "code": "page.platform",
        "module": "platform",
        "name": "平台管理",
        "route_path": "/platforms",
        "sort_order": 100,
        "children": [
            {"code": "page.platform.maintenance", "module": "platform", "name": "平台维护", "route_path": "/platforms", "sort_order": 110, "actions": ["platform.read", "platform.create", "platform.update", "platform.delete"]},
            {"code": "page.platform.module", "module": "module", "name": "模块管理", "route_path": "/modules", "sort_order": 120, "actions": ["module.read", "module.create", "module.update", "module.delete"]},
            {"code": "page.platform.environment", "module": "environment", "name": "环境管理", "route_path": "/projects", "sort_order": 130, "actions": ["environment.read", "environment.create", "environment.update", "environment.delete", "environment.request_control.read", "environment.request_control.create", "environment.request_control.update", "environment.request_control.delete"]},
        ],
    },
    {
        "code": "page.api_testing",
        "module": "api_testing",
        "name": "接口测试",
        "route_path": "/api-testing/apis",
        "sort_order": 200,
        "children": [
            {"code": "page.api_testing.api", "module": "api", "name": "接口管理", "route_path": "/api-testing/apis", "sort_order": 210, "actions": ["api.read", "api.create", "api.update", "api.delete", "api.debug"]},
            {"code": "page.api_testing.case", "module": "api_case", "name": "测试用例", "route_path": "/api-testing/cases", "sort_order": 220, "actions": ["api_case.read", "api_case.create", "api_case.update", "api_case.delete", "api_case.debug"]},
            {"code": "page.api_testing.automation", "module": "automation", "name": "自动化测试", "route_path": "/api-testing/automation", "sort_order": 230, "actions": ["automation.read", "automation.create", "automation.update", "automation.delete", "automation.execute"]},
        ],
    },
    {
        "code": "page.data_factory",
        "module": "data_factory",
        "name": "数据工厂",
        "route_path": "/test-tools/quick-test",
        "sort_order": 300,
        "children": [
            {"code": "page.data_factory.quick_test", "module": "quick_test", "name": "快速测试", "route_path": "/test-tools/quick-test", "sort_order": 310, "actions": ["quick_test.read", "quick_test.execute"]},
            {"code": "page.data_factory.capability", "module": "capability", "name": "能力列表", "route_path": "/test-tools/capabilities", "sort_order": 320, "actions": ["capability.read", "capability.create", "capability.update", "capability.delete", "capability.execute"]},
        ],
    },
    {
        "code": "page.ui_testing",
        "module": "ui_testing",
        "name": "UI测试",
        "route_path": "/ui-testing/suites",
        "sort_order": 400,
        "children": [
            {"code": "page.ui_testing.suite", "module": "ui_suite", "name": "测试套件", "route_path": "/ui-testing/suites", "sort_order": 410, "actions": ["ui_suite.read", "ui_suite.create", "ui_suite.update", "ui_suite.delete", "ui_suite.execute"]},
            {"code": "page.ui_testing.case", "module": "ui_case", "name": "测试用例", "route_path": "/ui-testing/cases", "sort_order": 420, "actions": ["ui_case.read", "ui_case.create", "ui_case.update", "ui_case.delete", "ui_case.execute"]},
            {"code": "page.ui_testing.element", "module": "ui_element", "name": "定位元素", "route_path": "/ui-testing/elements", "sort_order": 430, "actions": ["ui_element.read", "ui_element.create", "ui_element.update", "ui_element.delete", "ui_element.execute"]},
        ],
    },
    {
        "code": "page.performance",
        "module": "performance",
        "name": "性能测试",
        "route_path": "/performance-testing",
        "sort_order": 500,
        "children": [
            {"code": "page.performance.testing", "module": "performance", "name": "性能测试", "route_path": "/performance-testing", "sort_order": 510, "actions": ["performance.read", "performance.create", "performance.update", "performance.delete", "performance.execute"]},
        ],
    },
    {
        "code": "page.permission",
        "module": "permission",
        "name": "权限管理",
        "route_path": "/users",
        "sort_order": 600,
        "children": [
            {"code": "page.permission.user", "module": "user", "name": "用户管理", "route_path": "/users", "sort_order": 610, "actions": ["user.read", "user.create", "user.update", "user.delete"]},
            {"code": "page.permission.role", "module": "role", "name": "角色管理", "route_path": "/roles", "sort_order": 620, "actions": ["role.read", "role.create", "role.update", "role.delete"]},
            {"code": "page.permission.audit", "module": "audit", "name": "审计日志", "route_path": "/audit-logs", "sort_order": 630, "actions": ["audit.read", "audit.export"]},
        ],
    },
    {
        "code": "page.config",
        "module": "config",
        "name": "配置管理",
        "route_path": "/reports",
        "sort_order": 700,
        "children": [
            {"code": "page.config.report", "module": "report", "name": "测试报告", "route_path": "/reports", "sort_order": 710, "actions": ["report.read", "report.export"]},
            {"code": "page.config.schedule", "module": "schedule", "name": "调度计划", "route_path": "/scheduling", "sort_order": 720, "actions": ["schedule.read", "schedule.create", "schedule.update", "schedule.delete", "schedule.execute"]},
            {"code": "page.config.notification", "module": "notification", "name": "消息通知", "route_path": "/notifications", "sort_order": 730, "actions": ["notification.read", "notification.create", "notification.update", "notification.delete"]},
            {"code": "page.config.notification_template", "module": "notification_template", "name": "消息模板", "route_path": "/notification-templates", "sort_order": 740, "actions": ["notification_template.read", "notification_template.create", "notification_template.update", "notification_template.delete"]},
            {"code": "page.config.database", "module": "database", "name": "数据库管理", "route_path": "/database-management", "sort_order": 750, "actions": ["database.read", "database.create", "database.update", "database.delete", "database.execute"]},
        ],
    },
]

ACTION_PERMISSION_DEFINITIONS = [
    ("platform.read", "platform", "read", "平台查看"),
    ("platform.create", "platform", "create", "平台新增"),
    ("platform.update", "platform", "update", "平台编辑"),
    ("platform.write", "platform", "write", "平台维护", False),
    ("platform.delete", "platform", "delete", "平台删除"),
    ("module.read", "module", "read", "模块查看"),
    ("module.create", "module", "create", "模块新增"),
    ("module.update", "module", "update", "模块编辑"),
    ("module.write", "module", "write", "模块维护", False),
    ("module.delete", "module", "delete", "模块删除"),
    ("environment.read", "environment", "read", "环境查看"),
    ("environment.create", "environment", "create", "环境新增"),
    ("environment.update", "environment", "update", "环境编辑"),
    ("environment.write", "environment", "write", "环境维护", False),
    ("environment.delete", "environment", "delete", "环境删除"),
    ("environment.request_control.read", "environment_request_control", "read", "请求控件查看"),
    ("environment.request_control.create", "environment_request_control", "create", "请求控件新增"),
    ("environment.request_control.update", "environment_request_control", "update", "请求控件编辑"),
    ("environment.request_control.write", "environment_request_control", "write", "请求控件维护", False),
    ("environment.request_control.delete", "environment_request_control", "delete", "请求控件删除"),
    ("api.read", "api", "read", "接口查看"),
    ("api.create", "api", "create", "接口新增"),
    ("api.update", "api", "update", "接口编辑"),
    ("api.write", "api", "write", "接口维护", False),
    ("api.delete", "api", "delete", "接口删除"),
    ("api.debug", "api", "execute", "接口调试"),
    ("api_case.read", "api_case", "read", "用例查看"),
    ("api_case.create", "api_case", "create", "用例新增"),
    ("api_case.update", "api_case", "update", "用例编辑"),
    ("api_case.delete", "api_case", "delete", "用例删除"),
    ("api_case.debug", "api_case", "execute", "用例调试"),
    ("automation.read", "automation", "read", "自动化查看"),
    ("automation.create", "automation", "create", "自动化新增"),
    ("automation.update", "automation", "update", "自动化编辑"),
    ("automation.delete", "automation", "delete", "自动化删除"),
    ("automation.execute", "automation", "execute", "自动化执行"),
    ("quick_test.read", "quick_test", "read", "快速测试查看"),
    ("quick_test.execute", "quick_test", "execute", "快速测试执行"),
    ("capability.read", "capability", "read", "能力查看"),
    ("capability.create", "capability", "create", "能力新增"),
    ("capability.update", "capability", "update", "能力编辑"),
    ("capability.delete", "capability", "delete", "能力删除"),
    ("capability.execute", "capability", "execute", "能力执行"),
    ("performance.read", "performance", "read", "性能查看"),
    ("performance.create", "performance", "create", "性能新增"),
    ("performance.update", "performance", "update", "性能编辑"),
    ("performance.delete", "performance", "delete", "性能删除"),
    ("performance.execute", "performance", "execute", "性能执行"),
    ("plan.read", "plan", "read", "测试计划查看", False),
    ("plan.create", "plan", "create", "测试计划新增", False),
    ("plan.update", "plan", "update", "测试计划编辑", False),
    ("plan.write", "plan", "write", "测试计划维护", False),
    ("plan.delete", "plan", "delete", "测试计划删除", False),
    ("run.read", "run", "read", "执行记录查看"),
    ("run.execute", "run", "execute", "执行测试计划"),
    ("report.read", "report", "read", "报告查看"),
    ("report.export", "report", "export", "报告导出"),
    ("schedule.read", "schedule", "read", "调度查看"),
    ("schedule.create", "schedule", "create", "调度新增"),
    ("schedule.update", "schedule", "update", "调度编辑"),
    ("schedule.write", "schedule", "write", "调度维护", False),
    ("schedule.delete", "schedule", "delete", "调度删除"),
    ("schedule.execute", "schedule", "execute", "调度执行"),
    ("notification.read", "notification", "read", "通知查看"),
    ("notification.create", "notification", "create", "通知新增"),
    ("notification.update", "notification", "update", "通知编辑"),
    ("notification.delete", "notification", "delete", "通知删除"),
    ("notification_template.read", "notification_template", "read", "模板查看"),
    ("notification_template.create", "notification_template", "create", "模板新增"),
    ("notification_template.update", "notification_template", "update", "模板编辑"),
    ("notification_template.delete", "notification_template", "delete", "模板删除"),
    ("database.read", "database", "read", "数据库查看"),
    ("database.create", "database", "create", "数据库新增"),
    ("database.update", "database", "update", "数据库编辑"),
    ("database.delete", "database", "delete", "数据库删除"),
    ("database.execute", "database", "execute", "数据库执行"),
    ("ui_suite.read", "ui_suite", "read", "UI套件查看"),
    ("ui_suite.create", "ui_suite", "create", "UI套件新增"),
    ("ui_suite.update", "ui_suite", "update", "UI套件编辑"),
    ("ui_suite.delete", "ui_suite", "delete", "UI套件删除"),
    ("ui_suite.execute", "ui_suite", "execute", "UI套件执行"),
    ("ui_case.read", "ui_case", "read", "UI用例查看"),
    ("ui_case.create", "ui_case", "create", "UI用例新增"),
    ("ui_case.update", "ui_case", "update", "UI用例编辑"),
    ("ui_case.delete", "ui_case", "delete", "UI用例删除"),
    ("ui_case.execute", "ui_case", "execute", "UI用例执行"),
    ("ui_element.read", "ui_element", "read", "定位元素查看"),
    ("ui_element.create", "ui_element", "create", "定位元素新增"),
    ("ui_element.update", "ui_element", "update", "定位元素编辑"),
    ("ui_element.delete", "ui_element", "delete", "定位元素删除"),
    ("ui_element.execute", "ui_element", "execute", "定位元素校验"),
    ("user.read", "user", "read", "用户查看"),
    ("user.create", "user", "create", "用户新增"),
    ("user.update", "user", "update", "用户编辑"),
    ("user.write", "user", "write", "用户维护", False),
    ("user.delete", "user", "delete", "用户删除"),
    ("role.read", "role", "read", "角色查看"),
    ("role.create", "role", "create", "角色新增"),
    ("role.update", "role", "update", "角色编辑"),
    ("role.write", "role", "write", "角色维护", False),
    ("role.delete", "role", "delete", "角色删除"),
    ("audit.read", "audit", "read", "审计查看"),
    ("audit.export", "audit", "export", "审计导出"),
    ("system.admin", "system", "admin", "系统设置", False),
]

VISIBLE_PERMISSION_CODES = [item[0] for item in ACTION_PERMISSION_DEFINITIONS if len(item) < 5 or item[4]]
HIDDEN_PERMISSION_CODES = {item[0] for item in ACTION_PERMISSION_DEFINITIONS if len(item) > 4 and not item[4]}
ALL_PERMISSION_CODES = VISIBLE_PERMISSION_CODES + [
    code
    for page in PAGE_PERMISSION_DEFINITIONS
    for code in [page["code"], *[child["code"] for child in page.get("children", [])]]
]
WRITE_PERMISSION_COMPAT_MAP = {
    "platform.write": ["platform.create", "platform.update"],
    "module.write": ["module.create", "module.update"],
    "environment.write": ["environment.create", "environment.update"],
    "environment.request_control.write": ["environment.request_control.create", "environment.request_control.update"],
    "api.write": ["api.create", "api.update"],
    "plan.write": ["plan.create", "plan.update"],
    "schedule.write": ["schedule.create", "schedule.update"],
    "user.write": ["user.create", "user.update"],
    "role.write": ["role.create", "role.update"],
}
PAGE_ACTION_COMPAT_MAP = {
    "page.api_testing.case": {
        "api.read": "api_case.read",
        "api.create": "api_case.create",
        "api.update": "api_case.update",
        "api.delete": "api_case.delete",
        "api.debug": "api_case.debug",
    },
    "page.api_testing.automation": {
        "api.read": "automation.read",
        "api.create": "automation.create",
        "api.update": "automation.update",
        "api.delete": "automation.delete",
        "api.debug": "automation.execute",
        "run.execute": "automation.execute",
    },
    "page.data_factory.quick_test": {"api.read": "quick_test.read", "api.debug": "quick_test.execute"},
    "page.data_factory.capability": {
        "api.read": "capability.read",
        "api.create": "capability.create",
        "api.update": "capability.update",
        "api.delete": "capability.delete",
        "api.debug": "capability.execute",
    },
    "page.performance.testing": {"run.read": "performance.read", "run.execute": "performance.execute"},
    "page.ui_testing.suite": {
        "api.read": "ui_suite.read",
        "api.create": "ui_suite.create",
        "api.update": "ui_suite.update",
        "api.delete": "ui_suite.delete",
    },
    "page.ui_testing.case": {
        "api.read": "ui_case.read",
        "api.create": "ui_case.create",
        "api.update": "ui_case.update",
        "api.delete": "ui_case.delete",
    },
    "page.ui_testing.element": {
        "api.read": "ui_element.read",
        "api.create": "ui_element.create",
        "api.update": "ui_element.update",
        "api.delete": "ui_element.delete",
    },
    "page.config.schedule": {"run.execute": "schedule.execute"},
    "page.config.notification": {
        "schedule.read": "notification.read",
        "schedule.create": "notification.create",
        "schedule.update": "notification.update",
        "schedule.delete": "notification.delete",
    },
    "page.config.notification_template": {
        "schedule.read": "notification_template.read",
        "schedule.create": "notification_template.create",
        "schedule.update": "notification_template.update",
        "schedule.delete": "notification_template.delete",
    },
    "page.config.database": {
        "environment.read": "database.read",
        "environment.create": "database.create",
        "environment.update": "database.update",
        "environment.delete": "database.delete",
    },
}

ROLE_PERMISSION_CODES = {
    Role.BuiltinCode.SUPER_ADMIN: ALL_PERMISSION_CODES,
    Role.BuiltinCode.TEST_MANAGER: [
        "platform.read",
        "module.read",
        "module.create", "module.update",
        "module.delete",
        "environment.read",
        "environment.create", "environment.update",
        "environment.delete",
        "environment.request_control.read",
        "environment.request_control.create", "environment.request_control.update",
        "environment.request_control.delete",
        "api.read",
        "api.create", "api.update",
        "api.delete",
        "api.debug",
        "api_case.read",
        "api_case.create", "api_case.update",
        "api_case.delete",
        "api_case.debug",
        "automation.read",
        "automation.create", "automation.update",
        "automation.delete",
        "automation.execute",
        "quick_test.read",
        "quick_test.execute",
        "capability.read",
        "capability.create", "capability.update",
        "capability.delete",
        "capability.execute",
        "performance.read",
        "performance.create", "performance.update",
        "performance.delete",
        "performance.execute",
        "run.read",
        "run.execute",
        "report.read",
        "report.export",
        "schedule.read",
        "schedule.create", "schedule.update",
        "schedule.delete",
        "schedule.execute",
        "notification.read",
        "notification.create", "notification.update",
        "notification.delete",
        "notification_template.read",
        "notification_template.create", "notification_template.update",
        "notification_template.delete",
        "database.read",
        "database.create", "database.update",
        "database.delete",
        "database.execute",
        "ui_suite.read",
        "ui_suite.create", "ui_suite.update",
        "ui_suite.delete",
        "ui_suite.execute",
        "ui_case.read",
        "ui_case.create", "ui_case.update",
        "ui_case.delete",
        "ui_case.execute",
        "ui_element.read",
        "ui_element.create", "ui_element.update",
        "ui_element.delete",
        "ui_element.execute",
        "user.read",
        "user.create", "user.update",
        "audit.read",
    ],
    Role.BuiltinCode.TEST_ENGINEER: [
        "module.read",
        "environment.read",
        "environment.create", "environment.update",
        "environment.request_control.read",
        "environment.request_control.create", "environment.request_control.update",
        "api.read",
        "api.create", "api.update",
        "api.delete",
        "api.debug",
        "api_case.read",
        "api_case.create", "api_case.update",
        "api_case.delete",
        "api_case.debug",
        "automation.read",
        "automation.create", "automation.update",
        "automation.delete",
        "automation.execute",
        "quick_test.read",
        "quick_test.execute",
        "capability.read",
        "capability.create", "capability.update",
        "capability.delete",
        "capability.execute",
        "platform.read",
        "run.read",
        "run.execute",
        "report.read",
        "report.export",
        "schedule.read",
        "schedule.execute",
        "notification.read",
        "notification_template.read",
        "database.read",
        "database.execute",
    ],
    Role.BuiltinCode.DEVELOPER: ["environment.read", "api.read", "api_case.read", "automation.read", "report.read", "run.read"],
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


def protected_usernames() -> set[str]:
    configured = getattr(settings, "PROTECTED_USERNAMES", DEFAULT_PROTECTED_USERNAMES)
    if not configured:
        configured = DEFAULT_PROTECTED_USERNAMES
    if isinstance(configured, str):
        configured = [configured]
    return {str(username).strip() for username in configured if str(username).strip()}


def is_protected_username(username: str | None) -> bool:
    return str(username or "").strip() in protected_usernames()


def is_protected_user(user) -> bool:
    return is_protected_username(getattr(user, "username", None))


def protected_user_operation_message(action: str = "操作") -> str:
    return f"系统保护账号不允许在用户管理中{action}，{PROTECTED_USER_PROFILE_MESSAGE}"


def assert_user_manageable(user, action: str = "操作") -> None:
    # 系统保护账号只能通过个人中心维护，避免用户管理、脚本或后台误改核心账号。
    if is_protected_user(user):
        raise PermissionDenied(protected_user_operation_message(action))


def allow_protected_user_security_fix() -> bool:
    return bool(getattr(_protected_user_guard, "allow_security_fix", False))


@contextmanager
def protected_user_security_fix():
    # 仅供系统内部把保护账号修复回安全状态时使用，不作为普通业务绕过入口。
    previous = allow_protected_user_security_fix()
    _protected_user_guard.allow_security_fix = True
    try:
        yield
    finally:
        _protected_user_guard.allow_security_fix = previous


def ensure_builtin_roles() -> None:
    permission_map = {}
    for definition in ACTION_PERMISSION_DEFINITIONS:
        code, module, action, name = definition[:4]
        is_visible = definition[4] if len(definition) > 4 else True
        permission, _ = Permission.objects.get_or_create(
            code=code,
            defaults={"module": module, "action": action, "name": name},
        )
        permission.module = module
        permission.action = action
        permission.name = name
        permission.type = Permission.Type.ACTION
        permission.is_visible = is_visible
        permission.save(update_fields=["module", "action", "name", "type", "is_visible", "updated_at"])
        permission_map[code] = permission

    page_permissions = _ensure_page_permissions()
    permission_map.update(page_permissions)

    for code, name in ROLE_NAMES.items():
        role, created = Role.objects.get_or_create(
            code=code,
            defaults={"name": name, "is_builtin": True, "description": f"系统预置角色：{name}"},
        )
        role.name = name
        role.is_builtin = True
        role.is_active = True
        role.save(update_fields=["name", "is_builtin", "is_active", "updated_at"])
        if created or code == Role.BuiltinCode.SUPER_ADMIN:
            role.permissions.set(permission_map[item] for item in _role_permission_codes(code))
        _migrate_write_permissions(role, permission_map)


def _ensure_page_permissions() -> dict[str, Permission]:
    page_permissions = {}
    for page in PAGE_PERMISSION_DEFINITIONS:
        parent = _upsert_page_permission(page, Permission.Type.TAB)
        page_permissions[parent.code] = parent
        for child in page.get("children", []):
            child_permission = _upsert_page_permission(child, Permission.Type.MENU, parent)
            page_permissions[child_permission.code] = child_permission
            for action_code in child.get("actions", []):
                action_permission = Permission.objects.filter(code=action_code).first()
                if action_permission and action_permission.parent_id != child_permission.id:
                    action_permission.parent = child_permission
                    action_permission.save(update_fields=["parent", "updated_at"])
    return page_permissions


def _upsert_page_permission(item: dict[str, Any], permission_type: Permission.Type, parent: Permission | None = None) -> Permission:
    permission, _ = Permission.objects.get_or_create(
        code=item["code"],
        defaults={
            "module": item["module"],
            "action": Permission.Action.PAGE,
            "name": item["name"],
            "type": permission_type,
            "route_path": item.get("route_path", ""),
            "sort_order": item.get("sort_order", 0),
            "parent": parent,
        },
    )
    permission.module = item["module"]
    permission.action = Permission.Action.PAGE
    permission.name = item["name"]
    permission.type = permission_type
    permission.parent = parent
    permission.route_path = item.get("route_path", "")
    permission.is_visible = True
    permission.sort_order = item.get("sort_order", 0)
    permission.save(update_fields=["module", "action", "name", "type", "parent", "route_path", "is_visible", "sort_order", "updated_at"])
    return permission


def _role_permission_codes(role_code: str) -> list[str]:
    codes = set(ROLE_PERMISSION_CODES[role_code])
    if role_code == Role.BuiltinCode.SUPER_ADMIN:
        return ALL_PERMISSION_CODES
    for page in PAGE_PERMISSION_DEFINITIONS:
        child_codes = {action for child in page.get("children", []) for action in child.get("actions", [])}
        if codes.intersection(child_codes):
            codes.add(page["code"])
        for child in page.get("children", []):
            if codes.intersection(set(child.get("actions", []))):
                codes.add(child["code"])
    if codes:
        codes.add("page.dashboard")
    return [code for code in ALL_PERMISSION_CODES if code in codes]


def _migrate_write_permissions(role: Role, permission_map: dict[str, Permission]) -> None:
    existing_codes = set(role.permissions.values_list("code", flat=True))
    target_codes = {
        next_code
        for old_code, next_codes in WRITE_PERMISSION_COMPAT_MAP.items()
        if old_code in existing_codes
        for next_code in next_codes
    }
    for page_code, action_map in PAGE_ACTION_COMPAT_MAP.items():
        if page_code in existing_codes:
            target_codes.update(next_code for old_code, next_code in action_map.items() if old_code in existing_codes)
    if target_codes:
        role.permissions.add(*(permission_map[code] for code in target_codes if code in permission_map))


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
        return set(ALL_PERMISSION_CODES)
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


def record_failed_login(username: str) -> None:
    if not username:
        return
    user = get_user_model().objects.filter(username=username).first()
    if not user:
        return
    profile = ensure_profile(user)
    profile.failed_login_count += 1
    if profile.failed_login_count >= MAX_LOGIN_FAILURES:
        profile.status = UserProfile.Status.LOCKED
        profile.locked_until = timezone.now() + timedelta(minutes=LOGIN_LOCK_MINUTES)
    profile.save(update_fields=["failed_login_count", "status", "locked_until", "updated_at"])


def create_user_session(request, user, token, remember_me: bool = False) -> UserSession:
    session_seconds = _session_seconds(remember_me)
    expires_at = timezone.now() + timedelta(seconds=session_seconds)
    return UserSession.objects.create(
        user=user,
        token_key=token.key,
        device=get_user_agent(request)[:255],
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        last_active_at=timezone.now(),
        expires_at=expires_at,
    )


def _session_seconds(remember_me: bool) -> int:
    setting_name = "REMEMBER_ME_USER_SESSION_SECONDS" if remember_me else "USER_SESSION_SECONDS"
    default = 30 * 24 * 60 * 60 if remember_me else 24 * 60 * 60
    try:
        value = int(getattr(settings, setting_name, default))
    except (TypeError, ValueError):
        value = default
    return max(60, value)


def revoke_user_sessions(user) -> int:
    count = UserSession.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
    from apps.accounts.models import AuthToken

    AuthToken.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
    return count


def bootstrap_superuser_profile() -> None:
    ensure_builtin_roles()
    User = get_user_model()
    super_role = Role.objects.get(code=Role.BuiltinCode.SUPER_ADMIN)
    for user in User.objects.filter(is_superuser=True):
        profile = ensure_profile(user, super_role)
        if profile.role_id != super_role.id:
            profile.role = super_role
            profile.save(update_fields=["role", "updated_at"])

