from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api_testing", "0008_alter_apicase_assertions_alter_apicase_body_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="apiscenario",
            name="run_config",
            field=models.JSONField(blank=True, db_comment="场景运行配置JSON，如测试数据、循环次数、线程数、执行机和通知配置。", default=dict),
        ),
    ]
