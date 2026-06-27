from django.db import migrations


NEW_ACTION_PERMISSIONS = [
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
]

PAGE_ACTION_MAP = {
    "page.api_testing.case": ["api_case.read", "api_case.create", "api_case.update", "api_case.delete", "api_case.debug"],
    "page.api_testing.automation": ["automation.read", "automation.create", "automation.update", "automation.delete", "automation.execute"],
    "page.data_factory.quick_test": ["quick_test.read", "quick_test.execute"],
    "page.data_factory.capability": ["capability.read", "capability.create", "capability.update", "capability.delete", "capability.execute"],
    "page.performance.testing": ["performance.read", "performance.create", "performance.update", "performance.delete", "performance.execute"],
    "page.ui_testing.suite": ["ui_suite.read", "ui_suite.create", "ui_suite.update", "ui_suite.delete", "ui_suite.execute"],
    "page.ui_testing.case": ["ui_case.read", "ui_case.create", "ui_case.update", "ui_case.delete", "ui_case.execute"],
    "page.ui_testing.element": ["ui_element.read", "ui_element.create", "ui_element.update", "ui_element.delete", "ui_element.execute"],
    "page.config.schedule": ["schedule.read", "schedule.create", "schedule.update", "schedule.delete", "schedule.execute"],
    "page.config.notification": ["notification.read", "notification.create", "notification.update", "notification.delete"],
    "page.config.notification_template": ["notification_template.read", "notification_template.create", "notification_template.update", "notification_template.delete"],
    "page.config.database": ["database.read", "database.create", "database.update", "database.delete", "database.execute"],
}

PAGE_ACTION_COMPAT_MAP = {
    "page.api_testing.case": {"api.read": "api_case.read", "api.create": "api_case.create", "api.update": "api_case.update", "api.delete": "api_case.delete", "api.debug": "api_case.debug"},
    "page.api_testing.automation": {"api.read": "automation.read", "api.create": "automation.create", "api.update": "automation.update", "api.delete": "automation.delete", "api.debug": "automation.execute", "run.execute": "automation.execute"},
    "page.data_factory.quick_test": {"api.read": "quick_test.read", "api.debug": "quick_test.execute"},
    "page.data_factory.capability": {"api.read": "capability.read", "api.create": "capability.create", "api.update": "capability.update", "api.delete": "capability.delete", "api.debug": "capability.execute"},
    "page.performance.testing": {"run.read": "performance.read", "run.execute": "performance.execute"},
    "page.ui_testing.suite": {"api.read": "ui_suite.read", "api.create": "ui_suite.create", "api.update": "ui_suite.update", "api.delete": "ui_suite.delete"},
    "page.ui_testing.case": {"api.read": "ui_case.read", "api.create": "ui_case.create", "api.update": "ui_case.update", "api.delete": "ui_case.delete"},
    "page.ui_testing.element": {"api.read": "ui_element.read", "api.create": "ui_element.create", "api.update": "ui_element.update", "api.delete": "ui_element.delete"},
    "page.config.schedule": {"run.execute": "schedule.execute"},
    "page.config.notification": {"schedule.read": "notification.read", "schedule.create": "notification.create", "schedule.update": "notification.update", "schedule.delete": "notification.delete"},
    "page.config.notification_template": {"schedule.read": "notification_template.read", "schedule.create": "notification_template.create", "schedule.update": "notification_template.update", "schedule.delete": "notification_template.delete"},
    "page.config.database": {"environment.read": "database.read", "environment.create": "database.create", "environment.update": "database.update", "environment.delete": "database.delete"},
}


def sync_granular_page_permissions(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Role = apps.get_model("accounts", "Role")

    for code, module, action, name in NEW_ACTION_PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(
            code=code,
            defaults={"module": module, "action": action, "name": name, "type": "action", "is_visible": True},
        )
        permission.module = module
        permission.action = action
        permission.name = name
        permission.type = "action"
        permission.is_visible = True
        permission.save()

    for page_code, action_codes in PAGE_ACTION_MAP.items():
        parent = Permission.objects.filter(code=page_code).first()
        if parent:
            Permission.objects.filter(code__in=action_codes).update(parent=parent, type="action", is_visible=True)

    for role in Role.objects.prefetch_related("permissions"):
        codes = set(role.permissions.values_list("code", flat=True))
        if role.code == "super_admin":
            role.permissions.add(*Permission.objects.filter(is_visible=True))
            continue
        target_codes = set()
        for page_code, action_map in PAGE_ACTION_COMPAT_MAP.items():
            if page_code in codes:
                target_codes.update(next_code for old_code, next_code in action_map.items() if old_code in codes)
        if target_codes:
            role.permissions.add(*Permission.objects.filter(code__in=target_codes))


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_permission_page_scope"),
    ]

    operations = [
        migrations.RunPython(sync_granular_page_permissions, migrations.RunPython.noop),
    ]
