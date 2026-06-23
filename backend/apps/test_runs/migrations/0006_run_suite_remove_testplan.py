import django.db.models.deletion
from django.db import migrations, models


def clear_legacy_runs(apps, schema_editor):
    TestRun = apps.get_model("test_runs", "TestRun")
    TestRun.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("api_testing", "0010_apisuite_case_ids_apisuite_run_config"),
        ("scheduling", "0006_scheduledplan_suite"),
        ("test_runs", "0005_alter_testplan_api_ids_alter_testplan_concurrency_and_more"),
    ]

    operations = [
        migrations.RunPython(clear_legacy_runs, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="testrun",
            name="plan",
        ),
        migrations.AddField(
            model_name="testrun",
            name="suite",
            field=models.ForeignKey(db_comment="关联测试套件ID。", on_delete=django.db.models.deletion.CASCADE, related_name="runs", to="api_testing.apisuite"),
        ),
        migrations.AlterModelTableComment(
            name="testrun",
            table_comment="测试执行记录表：一次测试套件运行的总记录和报告汇总。",
        ),
        migrations.DeleteModel(
            name="TestPlan",
        ),
    ]
