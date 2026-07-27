from django.db import migrations


DOCUMENTATION = {
    "overview": "用于将历史接口资产批量导入测试平台。调用前需使用平台现有登录态完成认证，并具备接口批量导入权限。",
    "headers": [
        {"name": "Authorization", "required": True, "description": "复用平台现有登录 Token，格式为 Token <access_token>"},
        {"name": "Content-Type", "required": True, "description": "application/json"},
    ],
    "request_fields": [
        {"name": "module_code", "type": "string", "required": True, "description": "模块管理中的唯一模块编码；本批次全部接口归属该模块"},
        {"name": "items", "type": "array", "required": True, "description": "待导入接口列表，单批最多 100 条"},
        {"name": "items[].name", "type": "string", "required": True, "description": "接口名称，最多 100 个字符"},
        {"name": "items[].path", "type": "string", "required": True, "description": "接口路径，最多 512 个字符"},
        {"name": "items[].method", "type": "string", "required": True, "description": "GET、POST、PUT、PATCH、DELETE"},
        {"name": "items[].params", "type": "object", "required": True, "description": "GET/DELETE 导入为查询参数；POST/PUT/PATCH 导入为 JSON 请求体"},
    ],
    "request_example": {
        "module_code": "order-management",
        "items": [
            {
                "name": "创建订单",
                "path": "/api/orders",
                "method": "POST",
                "params": {"customer_id": "${customer_id}", "items": []},
            },
        ],
    },
    "error_cases": [
        {"code": "MODULE_NOT_FOUND", "message": "模块编码不存在或已停用"},
    ],
}


def update_internal_api_documentation(apps, schema_editor):
    Capability = apps.get_model("api_testing", "OpenApiCapability")
    Capability.objects.filter(code="api_definition.batch_import").update(
        name="接口资产批量导入",
        documentation=DOCUMENTATION,
    )


def remove_api_integration_permissions(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Permission.objects.filter(code__in=[
        "page.config.api_integration",
        "api_integration.read",
        "api_integration.view_docs",
        "api_integration.view_call_log",
        "api_integration.view_batch_history",
    ]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_sync_granular_page_permissions"),
        ("api_testing", "0015_update_batch_import_request_fields"),
    ]

    operations = [
        migrations.RunPython(update_internal_api_documentation, migrations.RunPython.noop),
        migrations.RunPython(remove_api_integration_permissions, migrations.RunPython.noop),
    ]
