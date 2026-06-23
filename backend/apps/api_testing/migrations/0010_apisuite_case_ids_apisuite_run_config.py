from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api_testing", "0009_apiscenario_run_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="apisuite",
            name="case_ids",
            field=models.JSONField(blank=True, db_comment="套件包含的单接口用例ID列表。", default=list),
        ),
        migrations.AddField(
            model_name="apisuite",
            name="run_config",
            field=models.JSONField(blank=True, db_comment="套件运行配置JSON，如运行环境、运行模式、执行器和推送开关。", default=dict),
        ),
    ]
