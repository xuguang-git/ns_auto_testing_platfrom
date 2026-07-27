from django.db import migrations, models


REMOVED_RUN_CONFIG_FIELDS = {"run_mode", "executor", "push"}


def cleanup_api_suite_run_config(apps, schema_editor):
    ApiSuite = apps.get_model("api_testing", "ApiSuite")
    for suite in ApiSuite.objects.all().only("id", "run_config").iterator():
        config = suite.run_config if isinstance(suite.run_config, dict) else {}
        cleaned_config = {key: value for key, value in config.items() if key not in REMOVED_RUN_CONFIG_FIELDS}
        if cleaned_config != config:
            ApiSuite.objects.filter(pk=suite.pk).update(run_config=cleaned_config)


class Migration(migrations.Migration):

    dependencies = [
        ("api_testing", "0010_apisuite_case_ids_apisuite_run_config"),
    ]

    operations = [
        migrations.AlterField(
            model_name="apisuite",
            name="run_config",
            field=models.JSONField(blank=True, db_comment="套件运行配置JSON，如优先级和运行环境。", default=dict),
        ),
        migrations.RunPython(cleanup_api_suite_run_config, migrations.RunPython.noop),
    ]
