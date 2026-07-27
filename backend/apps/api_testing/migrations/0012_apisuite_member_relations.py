import django.db.models.deletion
from django.db import migrations, models


def migrate_suite_members(apps, schema_editor):
    ApiScenario = apps.get_model("api_testing", "ApiScenario")
    ApiSuiteScenario = apps.get_model("api_testing", "ApiSuiteScenario")
    ApiSuiteCase = apps.get_model("api_testing", "ApiSuiteCase")
    ApiTestCase = apps.get_model("api_testing", "ApiTestCase")
    ApiSuite = apps.get_model("api_testing", "ApiSuite")

    scenario_links = []
    for scenario in ApiScenario.objects.exclude(suite_id__isnull=True).only("id", "suite_id", "sort_order").iterator():
        suite = ApiSuite.objects.only("id", "project_id").get(pk=scenario.suite_id)
        ApiScenario.objects.filter(pk=scenario.pk).update(project_id=suite.project_id)
        scenario_links.append(ApiSuiteScenario(suite_id=suite.id, scenario_id=scenario.id, sort_order=scenario.sort_order))
    ApiSuiteScenario.objects.bulk_create(scenario_links, ignore_conflicts=True)

    missing_project_scenarios = list(ApiScenario.objects.filter(project_id__isnull=True).values_list("id", flat=True))
    if missing_project_scenarios:
        raise RuntimeError(f"存在无法确定所属项目的历史场景：{missing_project_scenarios[:20]}")

    invalid_case_ids = []
    for suite in ApiSuite.objects.only("id", "project_id", "case_ids").iterator():
        raw_case_ids = suite.case_ids if isinstance(suite.case_ids, list) else []
        case_ids = [item for item in raw_case_ids if isinstance(item, int) and item > 0]
        valid_case_ids = set(ApiTestCase.objects.filter(project_id=suite.project_id, id__in=case_ids).values_list("id", flat=True))
        invalid_case_ids.extend((suite.id, item) for item in case_ids if item not in valid_case_ids)
        ApiSuiteCase.objects.bulk_create(
            [ApiSuiteCase(suite_id=suite.id, case_id=case_id, sort_order=index) for index, case_id in enumerate(case_ids) if case_id in valid_case_ids],
            ignore_conflicts=True,
        )
    if invalid_case_ids:
        print(f"套件成员迁移跳过无效单接口用例引用：{invalid_case_ids[:20]}，共 {len(invalid_case_ids)} 条")


class Migration(migrations.Migration):

    dependencies = [
        ("api_testing", "0011_cleanup_apisuite_run_config"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApiSuiteCase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("case", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="suite_links", to="api_testing.apitestcase")),
                ("suite", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="case_links", to="api_testing.apisuite")),
            ],
            options={"db_table_comment": "测试套件与单接口用例关联表。", "ordering": ["suite_id", "sort_order", "id"], "unique_together": {("suite", "case")}},
        ),
        migrations.CreateModel(
            name="ApiSuiteScenario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("scenario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="suite_links", to="api_testing.apiscenario")),
                ("suite", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scenario_links", to="api_testing.apisuite")),
            ],
            options={"db_table_comment": "测试套件与场景用例关联表。", "ordering": ["suite_id", "sort_order", "id"], "unique_together": {("suite", "scenario")}},
        ),
        migrations.AddField(
            model_name="apiscenario",
            name="project",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="api_scenarios", to="projects.project"),
        ),
        migrations.AlterUniqueTogether(name="apiscenario", unique_together=set()),
        migrations.AlterModelOptions(name="apiscenario", options={"ordering": ["project_id", "sort_order", "id"]}),
        migrations.AlterField(
            model_name="apiscenario",
            name="suite",
            field=models.ForeignKey(blank=True, db_comment="所属接口测试套件ID。", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="legacy_scenarios", to="api_testing.apisuite"),
        ),
        migrations.AlterField(
            model_name="apisuite",
            name="case_ids",
            field=models.JSONField(blank=True, db_comment="套件历史单接口用例ID列表。", default=list),
        ),
        migrations.RunPython(migrate_suite_members, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="apiscenario",
            name="project",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="api_scenarios", to="projects.project"),
        ),
    ]
