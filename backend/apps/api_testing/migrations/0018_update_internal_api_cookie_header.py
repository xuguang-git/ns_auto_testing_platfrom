from django.db import migrations


def update_cookie_header(apps, schema_editor):
    Capability = apps.get_model("api_testing", "OpenApiCapability")
    capability = Capability.objects.filter(code="api_definition.batch_import").first()
    if not capability:
        return
    documentation = dict(capability.documentation or {})
    documentation["headers"] = [
        {"name": "Cookie", "required": True, "description": "ns_access_token=<access_token>，复用平台现有登录会话"},
        {"name": "Content-Type", "required": True, "description": "application/json"},
    ]
    capability.documentation = documentation
    capability.save(update_fields=["documentation", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [("api_testing", "0017_alter_openapicalllog_table_comment_and_more")]

    operations = [migrations.RunPython(update_cookie_header, migrations.RunPython.noop)]
