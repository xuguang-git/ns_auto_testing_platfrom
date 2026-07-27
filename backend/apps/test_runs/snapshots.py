from __future__ import annotations

from django.db import transaction
from django.db.models import Prefetch

from apps.api_testing.models import ApiStep, ApiSuiteCase, ApiSuiteScenario
from apps.test_runs.models import TestRun, TestRunResourceReference


ACTIVE_RUN_STATUSES = [TestRun.Status.PENDING, TestRun.Status.RUNNING]


def _ids(values) -> list[int]:
    return [value for value in values or [] if isinstance(value, int) and value > 0]


def build_execution_snapshot(suite, environment_id: int | None) -> tuple[dict, set[tuple[str, int]]]:
    """将套件当前可执行内容固化为 JSON 快照，并返回删除保护所需的资源引用。"""

    case_links = ApiSuiteCase.objects.filter(suite=suite, case__is_active=True, case__api__is_active=True).select_related("case", "case__api").order_by("sort_order", "id")
    scenario_links = ApiSuiteScenario.objects.filter(suite=suite, scenario__is_active=True).select_related("scenario").prefetch_related(
        Prefetch("scenario__steps", queryset=ApiStep.objects.filter(is_active=True).select_related("api").order_by("sort_order", "id"))
    ).order_by("sort_order", "id")
    resources: set[tuple[str, int]] = {("suite", suite.id)}
    if environment_id:
        resources.add(("environment", environment_id))

    cases = []
    for link in case_links:
        case = link.case
        api = case.api
        request_override = case.request_override or {}
        cases.append({
            "id": case.id,
            "name": case.name,
            "api_id": api.id,
            "environment_id": environment_id,
            "variables": case.variables or {},
            "platform": api.platform,
            "module_id": api.module_id,
            "method": api.method,
            "path": api.path,
            "headers": request_override.get("headers", api.headers),
            "query_params": request_override.get("query_params", api.query_params),
            "body": request_override.get("body", api.body),
            "auth_config": request_override.get("auth_config", api.auth_config),
            "assertions": case.assertions or api.assertions,
        })
        resources.update({("case", case.id), ("api", api.id)})

    scenarios = []
    for link in scenario_links:
        scenario = link.scenario
        steps = []
        for step in scenario.steps.all():
            steps.append({
                "id": step.id,
                "name": step.name,
                "api_id": step.api_id,
                "platform": step.platform,
                "module_id": step.api.module_id if step.api_id else None,
                "method": step.method,
                "path": step.path,
                "headers": step.headers,
                "query_params": step.query_params,
                "body": step.body,
                "auth_config": step.auth_config,
                "pre_test_data_source_ids": _ids(step.pre_data_source_ids),
                "post_test_data_source_ids": _ids(step.post_data_source_ids),
                "extractors": step.extractors,
                "assertions": step.assertions,
            })
            if step.api_id:
                resources.add(("api", step.api_id))
            resources.update(("test_data_source", item_id) for item_id in _ids(step.pre_data_source_ids))
            resources.update(("test_data_source", item_id) for item_id in _ids(step.post_data_source_ids))
        scenarios.append({"id": scenario.id, "name": scenario.name, "environment_id": scenario.environment_id or environment_id, "steps": steps})
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
    return snapshot, resources


def persist_execution_snapshot(test_run: TestRun) -> dict:
    """为待执行任务固化快照；已有快照保持不可变。"""

    if test_run.execution_snapshot:
        return test_run.execution_snapshot
    with transaction.atomic():
        locked_run = TestRun.objects.select_for_update().select_related("suite").get(pk=test_run.pk)
        if locked_run.execution_snapshot:
            test_run.execution_snapshot = locked_run.execution_snapshot
            return locked_run.execution_snapshot
        snapshot, resources = build_execution_snapshot(locked_run.suite, locked_run.environment_id)
        locked_run.execution_snapshot = snapshot
        locked_run.save(update_fields=["execution_snapshot", "updated_at"])
        TestRunResourceReference.objects.bulk_create(
            [TestRunResourceReference(run=locked_run, resource_type=resource_type, resource_id=resource_id) for resource_type, resource_id in resources],
            ignore_conflicts=True,
        )
        test_run.execution_snapshot = snapshot
        return snapshot


def count_active_run_references(resource_type: str, resource_id: int) -> int:
    return TestRunResourceReference.objects.filter(
        resource_type=resource_type,
        resource_id=resource_id,
        run__status__in=ACTIVE_RUN_STATUSES,
    ).count()


def count_active_runs_using_scenario(scenario) -> int:
    return count_active_run_references(TestRunResourceReference.ResourceType.SCENARIO, scenario.id)


def count_active_runs_using_case(case) -> int:
    return count_active_run_references(TestRunResourceReference.ResourceType.CASE, case.id)


def count_active_runs_using_api(api) -> int:
    return count_active_run_references(TestRunResourceReference.ResourceType.API, api.id)


def count_active_runs_using_test_data_source(source) -> int:
    return count_active_run_references(TestRunResourceReference.ResourceType.TEST_DATA_SOURCE, source.id)
