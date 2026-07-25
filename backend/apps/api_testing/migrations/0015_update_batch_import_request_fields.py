from django.db import migrations


REQUEST_FIELDS = [
    {"name": "module_code", "type": "string", "required": True, "description": "模块管理中的唯一模块编码"},
    {"name": "items", "type": "array", "required": True, "description": "待导入接口列表"},
    {"name": "items[].name", "type": "string", "required": True, "description": "接口名称，最大 100 字符"},
    {"name": "items[].path", "type": "string", "required": True, "description": "接口路径，最大 512 字符"},
    {"name": "items[].method", "type": "string", "required": True, "description": "GET、POST、PUT、PATCH、DELETE"},
    {"name": "items[].params", "type": "object", "required": True, "description": "GET/DELETE 写入查询参数；POST/PUT/PATCH 写入 JSON 请求体"},
]


def update_request_fields(apps, schema_editor):
    Capability = apps.get_model("api_testing", "OpenApiCapability")
    capability = Capability.objects.filter(code="api_definition.batch_import").first()
    if not capability:
        return
    documentation = dict(capability.documentation or {})
    documentation["request_fields"] = REQUEST_FIELDS
    capability.documentation = documentation
    capability.save(update_fields=["documentation", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [("api_testing", "0014_update_batch_import_request_example")]
    operations = [migrations.RunPython(update_request_fields, migrations.RunPython.noop)]
