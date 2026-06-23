import django.db.models.deletion
from django.db import migrations, models


def clear_legacy_schedules(apps, schema_editor):
    ScheduledPlan = apps.get_model("scheduling", "ScheduledPlan")
    ScheduledPlan.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("api_testing", "0010_apisuite_case_ids_apisuite_run_config"),
        ("scheduling", "0005_alter_scheduledplan_cron_and_more"),
    ]

    operations = [
        migrations.RunPython(clear_legacy_schedules, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="scheduledplan",
            name="plan",
        ),
        migrations.AddField(
            model_name="scheduledplan",
            name="suite",
            field=models.ForeignKey(db_comment="关联测试套件ID。", on_delete=django.db.models.deletion.CASCADE, related_name="schedules", to="api_testing.apisuite", verbose_name="测试套件"),
        ),
        migrations.AlterModelOptions(
            name="scheduledplan",
            options={"ordering": ["suite_id", "name"], "verbose_name": "测试套件定时任务", "verbose_name_plural": "测试套件定时任务"},
        ),
        migrations.AlterModelTableComment(
            name="scheduledplan",
            table_comment="定时任务表：按Cron定期触发测试套件执行。",
        ),
    ]
