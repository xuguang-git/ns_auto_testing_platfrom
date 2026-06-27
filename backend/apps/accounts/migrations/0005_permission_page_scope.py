from django.db import migrations, models
import django.db.models.deletion


PAGE_PERMISSION_DEFINITIONS = [
    ("page.dashboard", "dashboard", "控制台", "/dashboard", 10, None),
    ("page.platform", "platform", "平台管理", "/platforms", 100, None),
    ("page.platform.maintenance", "platform", "平台维护", "/platforms", 110, "page.platform"),
    ("page.platform.module", "module", "模块管理", "/modules", 120, "page.platform"),
    ("page.platform.environment", "environment", "环境管理", "/projects", 130, "page.platform"),
    ("page.api_testing", "api_testing", "接口测试", "/api-testing/apis", 200, None),
    ("page.api_testing.api", "api", "接口管理", "/api-testing/apis", 210, "page.api_testing"),
    ("page.api_testing.case", "api_case", "测试用例", "/api-testing/cases", 220, "page.api_testing"),
    ("page.api_testing.automation", "automation", "自动化测试", "/api-testing/automation", 230, "page.api_testing"),
    ("page.data_factory", "data_factory", "数据工厂", "/test-tools/quick-test", 300, None),
    ("page.data_factory.quick_test", "quick_test", "快速测试", "/test-tools/quick-test", 310, "page.data_factory"),
    ("page.data_factory.capability", "capability", "能力列表", "/test-tools/capabilities", 320, "page.data_factory"),
    ("page.ui_testing", "ui_testing", "UI测试", "/ui-testing/suites", 400, None),
    ("page.ui_testing.suite", "ui_suite", "测试套件", "/ui-testing/suites", 410, "page.ui_testing"),
    ("page.ui_testing.case", "ui_case", "测试用例", "/ui-testing/cases", 420, "page.ui_testing"),
    ("page.ui_testing.element", "ui_element", "定位元素", "/ui-testing/elements", 430, "page.ui_testing"),
    ("page.performance", "performance", "性能测试", "/performance-testing", 500, None),
    ("page.performance.testing", "performance", "性能测试", "/performance-testing", 510, "page.performance"),
    ("page.permission", "permission", "权限管理", "/users", 600, None),
    ("page.permission.user", "user", "用户管理", "/users", 610, "page.permission"),
    ("page.permission.role", "role", "角色管理", "/roles", 620, "page.permission"),
    ("page.permission.audit", "audit", "审计日志", "/audit-logs", 630, "page.permission"),
    ("page.config", "config", "配置管理", "/reports", 700, None),
    ("page.config.report", "report", "测试报告", "/reports", 710, "page.config"),
    ("page.config.schedule", "schedule", "调度计划", "/scheduling", 720, "page.config"),
    ("page.config.notification", "notification", "消息通知", "/notifications", 730, "page.config"),
    ("page.config.notification_template", "notification_template", "消息模板", "/notification-templates", 740, "page.config"),
    ("page.config.database", "database", "数据库管理", "/database-management", 750, "page.config"),
]

PAGE_ACTION_MAP = {
    "page.platform.maintenance": ["platform.read", "platform.create", "platform.update", "platform.write", "platform.delete"],
    "page.platform.module": ["module.read", "module.create", "module.update", "module.write", "module.delete"],
    "page.platform.environment": ["environment.read", "environment.create", "environment.update", "environment.write", "environment.delete", "environment.request_control.read", "environment.request_control.create", "environment.request_control.update", "environment.request_control.write", "environment.request_control.delete"],
    "page.api_testing.api": ["api.read", "api.create", "api.update", "api.write", "api.delete", "api.debug"],
    "page.api_testing.case": ["api.read", "api.create", "api.update", "api.write", "api.delete", "api.debug"],
    "page.api_testing.automation": ["api.read", "api.create", "api.update", "api.write", "api.delete", "api.debug", "run.read", "run.execute"],
    "page.data_factory.quick_test": ["api.read", "api.create", "api.update", "api.write", "api.delete", "api.debug"],
    "page.data_factory.capability": ["api.read", "api.create", "api.update", "api.write", "api.delete"],
    "page.ui_testing.suite": ["api.read", "api.create", "api.update", "api.write", "api.delete"],
    "page.ui_testing.case": ["api.read", "api.create", "api.update", "api.write", "api.delete"],
    "page.ui_testing.element": ["api.read", "api.create", "api.update", "api.write", "api.delete"],
    "page.performance.testing": ["run.execute", "run.read"],
    "page.permission.user": ["user.read", "user.create", "user.update", "user.write", "user.delete"],
    "page.permission.role": ["role.read", "role.create", "role.update", "role.write", "role.delete"],
    "page.permission.audit": ["audit.read", "audit.export"],
    "page.config.report": ["report.read", "report.export", "run.read"],
    "page.config.schedule": ["schedule.read", "schedule.create", "schedule.update", "schedule.write", "schedule.delete"],
    "page.config.notification": ["schedule.read", "schedule.create", "schedule.update", "schedule.write", "schedule.delete"],
    "page.config.notification_template": ["schedule.read", "schedule.create", "schedule.update", "schedule.write", "schedule.delete"],
    "page.config.database": ["environment.read", "environment.create", "environment.update", "environment.write", "environment.delete"],
}

ACTION_PERMISSION_DEFINITIONS = [
    ("platform.create", "platform", "create", "平台新增", True),
    ("platform.update", "platform", "update", "平台编辑", True),
    ("platform.write", "platform", "write", "平台维护", False),
    ("module.create", "module", "create", "模块新增", True),
    ("module.update", "module", "update", "模块编辑", True),
    ("module.write", "module", "write", "模块维护", False),
    ("environment.create", "environment", "create", "环境新增", True),
    ("environment.update", "environment", "update", "环境编辑", True),
    ("environment.write", "environment", "write", "环境维护", False),
    ("environment.request_control.create", "environment_request_control", "create", "请求控件新增", True),
    ("environment.request_control.update", "environment_request_control", "update", "请求控件编辑", True),
    ("environment.request_control.write", "environment_request_control", "write", "请求控件维护", False),
    ("api.create", "api", "create", "接口新增", True),
    ("api.update", "api", "update", "接口编辑", True),
    ("api.write", "api", "write", "接口维护", False),
    ("plan.read", "plan", "read", "测试计划查看", False),
    ("plan.create", "plan", "create", "测试计划新增", False),
    ("plan.update", "plan", "update", "测试计划编辑", False),
    ("plan.write", "plan", "write", "测试计划维护", False),
    ("plan.delete", "plan", "delete", "测试计划删除", False),
    ("schedule.create", "schedule", "create", "调度新增", True),
    ("schedule.update", "schedule", "update", "调度编辑", True),
    ("schedule.write", "schedule", "write", "调度维护", False),
    ("user.create", "user", "create", "用户新增", True),
    ("user.update", "user", "update", "用户编辑", True),
    ("user.write", "user", "write", "用户维护", False),
    ("role.create", "role", "create", "角色新增", True),
    ("role.update", "role", "update", "角色编辑", True),
    ("role.write", "role", "write", "角色维护", False),
    ("system.admin", "system", "admin", "系统设置", False),
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

HIDDEN_PERMISSION_CODES = {code for code, _, _, _, is_visible in ACTION_PERMISSION_DEFINITIONS if not is_visible}


def sync_page_permissions(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Role = apps.get_model("accounts", "Role")
    permissions = {}

    Permission.objects.exclude(code__startswith="page.").update(type="action")
    for code, module, action, name, is_visible in ACTION_PERMISSION_DEFINITIONS:
        permission, _ = Permission.objects.get_or_create(
            code=code,
            defaults={"module": module, "action": action, "name": name, "type": "action", "is_visible": is_visible},
        )
        permission.module = module
        permission.action = action
        permission.name = name
        permission.type = "action"
        permission.is_visible = is_visible
        permission.save()

    for code, module, name, route_path, sort_order, parent_code in PAGE_PERMISSION_DEFINITIONS:
        parent = permissions.get(parent_code) if parent_code else None
        permission_type = "menu" if parent_code else "tab"
        permission, _ = Permission.objects.get_or_create(
            code=code,
            defaults={
                "module": module,
                "action": "page",
                "name": name,
                "type": permission_type,
                "route_path": route_path,
                "sort_order": sort_order,
                "parent": parent,
                "is_visible": True,
            },
        )
        permission.module = module
        permission.action = "page"
        permission.name = name
        permission.type = permission_type
        permission.route_path = route_path
        permission.sort_order = sort_order
        permission.parent = parent
        permission.is_visible = True
        permission.save()
        permissions[code] = permission

    for page_code, action_codes in PAGE_ACTION_MAP.items():
        parent = permissions.get(page_code)
        if parent:
            Permission.objects.filter(code__in=action_codes).update(parent=parent, type="action")
            Permission.objects.filter(code__in=set(action_codes) - HIDDEN_PERMISSION_CODES).update(is_visible=True)
            Permission.objects.filter(code__in=set(action_codes) & HIDDEN_PERMISSION_CODES).update(is_visible=False)

    page_parent_map = {code: parent for code, _, _, _, _, parent in PAGE_PERMISSION_DEFINITIONS}
    for role in Role.objects.prefetch_related("permissions"):
        existing_codes = set(role.permissions.values_list("code", flat=True))
        next_codes = {code for old_code, codes in WRITE_PERMISSION_COMPAT_MAP.items() if old_code in existing_codes for code in codes}
        if next_codes:
            role.permissions.add(*Permission.objects.filter(code__in=next_codes))
        if role.code == "super_admin":
            role.permissions.add(*Permission.objects.exclude(code__in=HIDDEN_PERMISSION_CODES))
            role.permissions.remove(*Permission.objects.filter(code__in=HIDDEN_PERMISSION_CODES))
            continue
        page_codes = {"page.dashboard"} if existing_codes else set()
        for page_code, action_codes in PAGE_ACTION_MAP.items():
            if existing_codes.intersection(action_codes):
                page_codes.add(page_code)
                parent_code = page_parent_map.get(page_code)
                if parent_code:
                    page_codes.add(parent_code)
        if page_codes:
            role.permissions.add(*Permission.objects.filter(code__in=page_codes))
        role.permissions.remove(*Permission.objects.filter(code__in=HIDDEN_PERMISSION_CODES))


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_authtoken_access_expires_at_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="permission",
            options={"ordering": ["sort_order", "module", "action", "code"]},
        ),
        migrations.AddField(
            model_name="permission",
            name="is_visible",
            field=models.BooleanField(db_comment="是否在权限树中展示。", default=True),
        ),
        migrations.AddField(
            model_name="permission",
            name="parent",
            field=models.ForeignKey(blank=True, db_comment="父级权限ID，用于页面与功能权限的展示归属关系。", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="children", to="accounts.permission"),
        ),
        migrations.AddField(
            model_name="permission",
            name="route_path",
            field=models.CharField(blank=True, db_comment="页面权限对应的前端路由路径。", max_length=128),
        ),
        migrations.AddField(
            model_name="permission",
            name="sort_order",
            field=models.PositiveIntegerField(db_comment="权限树展示排序值。", default=0),
        ),
        migrations.AddField(
            model_name="permission",
            name="type",
            field=models.CharField(choices=[("tab", "Tab权限"), ("menu", "菜单权限"), ("action", "功能权限")], db_comment="权限类型：Tab权限、菜单权限或功能权限。", default="action", max_length=16),
        ),
        migrations.AlterField(
            model_name="permission",
            name="action",
            field=models.CharField(choices=[("page", "页面"), ("read", "读取"), ("create", "新增"), ("update", "编辑"), ("write", "写入兼容"), ("delete", "删除"), ("export", "导出"), ("execute", "执行"), ("admin", "管理")], db_comment="权限动作。", max_length=16),
        ),
        migrations.RunPython(sync_page_permissions, migrations.RunPython.noop),
    ]
