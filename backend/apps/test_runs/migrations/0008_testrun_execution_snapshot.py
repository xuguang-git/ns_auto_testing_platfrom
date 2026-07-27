import django.db.models.deletion
from django.db import migrations, models


def valid_ids(values):
    return [value for value in values or [] if isinstance(value, int) and value > 0]


def backfill_pending_execution_snapshots(apps, schema_editor):
    TestRun = apps.get_model("test_runs", "TestRun")
    TestRunResourceReference = apps.get_model("test_runs", "TestRunResourceReference")
    ApiSuiteCase = apps.get_model("api_testing", "ApiSuiteCase")
    ApiSuiteScenario = apps.get_model("api_testing", "ApiSuiteScenario")
    ApiStep = apps.get_model("api_testing", "ApiStep")
    references = []

    for run in TestRun.objects.filter(status="pending").select_related("suite", "environment").iterator():
        suite = run.suite
        resources = {("suite", suite.id)}
        if run.environment_id:
            resources.add(("environment", run.environment_id))
        cases = []
        for link in ApiSuiteCase.objects.filter(suite_id=suite.id, case__is_active=True, case__api__is_active=True).select_related("case", "case__api").order_by("sort_order", "id"):
            case = link.case
            api = case.api
            override = case.request_override or {}
            cases.append({
                "id": case.id, "name": case.name, "api_id": api.id, "environment_id": run.environment_id,
                "variables": case.variables or {}, "platform": api.platform, "module_id": api.module_id,
                "method": api.method, "path": api.path, "headers": override.get("headers", api.headers),
                "query_params": override.get("query_params", api.query_params), "body": override.get("body", api.body),
                "auth_config": override.get("auth_config", api.auth_config), "assertions": case.assertions or api.assertions,
            })
            resources.update({("case", case.id), ("api", api.id)})
        scenarios = []
        for link in ApiSuiteScenario.objects.filter(suite_id=suite.id, scenario__is_active=True).select_related("scenario").order_by("sort_order", "id"):
            scenario = link.scenario
            steps = []
            for step in ApiStep.objects.filter(scenario_id=scenario.id, is_active=True).select_related("api").order_by("sort_order", "id"):
                pre_source_ids = valid_ids(step.pre_data_source_ids)
                post_source_ids = valid_ids(step.post_data_source_ids)
                steps.append({
                    "id": step.id, "name": step.name, "api_id": step.api_id, "platform": step.platform,
                    "module_id": step.api.module_id if step.api_id else None, "method": step.method, "path": step.path,
                    "headers": step.headers, "query_params": step.query_params, "body": step.body,
                    "auth_config": step.auth_config, "pre_test_data_source_ids": pre_source_ids,
                    "post_test_data_source_ids": post_source_ids, "extractors": step.extractors, "assertions": step.assertions,
                })
                if step.api_id:
                    resources.add(("api", step.api_id))
                resources.update(("test_data_source", source_id) for source_id in pre_source_ids)
                resources.update(("test_data_source", source_id) for source_id in post_source_ids)
            scenarios.append({"id": scenario.id, "name": scenario.name, "environment_id": scenario.environment_id or run.environment_id, "steps": steps})
            resources.add(("scenario", scenario.id))
            if scenario.environment_id:
                resources.add(("environment", scenario.environment_id))
        snapshot = {
            "version": 1,
            "suite_id": suite.id,
            "suite_name": suite.name,
            "suite_updated_at": suite.updated_at.isoformat() if suite.updated_at else "",
            "run_config": suite.run_config or {},
            "cases": cases,
            "scenarios": scenarios,
        }
        TestRun.objects.filter(pk=run.pk).update(execution_snapshot=snapshot)
        references.extend(
            TestRunResourceReference(run_id=run.id, resource_type=resource_type, resource_id=resource_id)
            for resource_type, resource_id in resources
        )
    TestRunResourceReference.objects.bulk_create(references, ignore_conflicts=True, batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("api_testing", "0012_apisuite_member_relations"),
        ("test_runs", "0007_testrun_schedule"),
    ]

    operations = [
        migrations.AddField(
            model_name="testrun",
            name="execution_snapshot",
            field=models.JSONField(blank=True, db_comment="任务触发时固化的执行快照JSON。", default=dict),
        ),
        migrations.CreateModel(
            name="TestRunResourceReference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("resource_type", models.CharField(choices=[("suite", "测试套件"), ("scenario", "场景用例"), ("case", "单接口用例"), ("api", "接口"), ("environment", "运行环境"), ("test_data_source", "测试数据源")], max_length=32)),
                ("resource_id", models.PositiveBigIntegerField()),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="resource_references", to="test_runs.testrun")),
            ],
            options={"db_table_comment": "测试执行快照资源引用表。", "unique_together": {("run", "resource_type", "resource_id")}},
        ),
        migrations.AddIndex(
            model_name="testrunresourcereference",
            index=models.Index(fields=["resource_type", "resource_id"], name="test_runs_t_resourc_e938d8_idx"),
        ),
        migrations.RunPython(backfill_pending_execution_snapshots, migrations.RunPython.noop),
    ]
