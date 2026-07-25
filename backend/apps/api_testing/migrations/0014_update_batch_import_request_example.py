from django.db import migrations


def update_request_example(apps, schema_editor):
    Capability = apps.get_model("api_testing", "OpenApiCapability")
    capability = Capability.objects.filter(code="api_definition.batch_import").first()
    if not capability:
        return
    documentation = dict(capability.documentation or {})
    documentation["request_example"] = {
        "module_code": "order-management",
        "items": [{
            "name": "创建订单",
            "path": "/api/orders",
            "method": "POST",
            "params": {"customer_id": "${customer_id}", "items": []},
        }],
    }
    capability.documentation = documentation
    capability.save(update_fields=["documentation", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [("api_testing", "0013_alter_apimodule_code_apiimportbatch_apiimportitem_and_more")]
    operations = [migrations.RunPython(update_request_example, migrations.RunPython.noop)]
