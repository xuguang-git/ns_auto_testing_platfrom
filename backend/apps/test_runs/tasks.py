from celery import shared_task
from django.utils import timezone

from apps.api_testing.models import ApiDefinition
from apps.api_testing.services import execute_debug_request
from apps.test_runs.models import TestRun, TestRunStep


@shared_task(bind=True)
def run_test_plan(self, test_run_id: int) -> dict:
    test_run = TestRun.objects.select_related("plan", "environment").get(pk=test_run_id)
    test_run.status = TestRun.Status.RUNNING
    test_run.celery_task_id = self.request.id or test_run.celery_task_id
    test_run.started_at = timezone.now()
    test_run.save(update_fields=["status", "celery_task_id", "started_at", "updated_at"])

    total = passed = failed = skipped = 0
    sort_order = 0

    try:
        scenarios = list(test_run.plan.api_scenarios.prefetch_related("steps").all())
        if not scenarios:
            for suite in test_run.plan.api_suites.prefetch_related("scenarios__steps").all():
                scenarios.extend(list(suite.scenarios.all()))

        if not scenarios and test_run.plan.api_ids:
            for api in ApiDefinition.objects.filter(id__in=test_run.plan.api_ids, is_active=True).order_by("sort_order", "id"):
                total += 1
                sort_order += 1
                payload = {
                    "environment": test_run.environment_id or test_run.plan.environment_id,
                    "variables": test_run.plan.variables,
                    "platform": api.platform,
                    "method": api.method,
                    "path": api.path,
                    "headers": api.headers,
                    "query_params": api.query_params,
                    "body": api.body,
                    "auth_config": api.auth_config,
                    "assertions": api.assertions,
                    "timeout": test_run.plan.timeout_seconds,
                }
                result = execute_debug_request(payload)
                step_passed = bool(result.get("ok") and result.get("passed"))
                if step_passed:
                    passed += 1
                    step_status = TestRunStep.Status.PASSED
                else:
                    failed += 1
                    step_status = TestRunStep.Status.FAILED

                TestRunStep.objects.create(
                    run=test_run,
                    scenario_name=test_run.plan.name,
                    step_name=api.name,
                    status=step_status,
                    sort_order=sort_order,
                    request=result.get("request") or {},
                    response=result.get("response") or {},
                    assertions=result.get("assertions") or [],
                    logs=result.get("logs") or [],
                    error_message=result.get("error") or "",
                    duration_ms=(result.get("response") or {}).get("elapsed_ms") or 0,
                )

                if failed and test_run.plan.failure_strategy == test_run.plan.FailureStrategy.FAST_FAIL:
                    skipped = max(len(test_run.plan.api_ids) - total, 0)
                    raise StopIteration

        for scenario in scenarios:
            for step in scenario.steps.filter(is_active=True):
                total += 1
                sort_order += 1
                payload = {
                    "environment": test_run.environment_id or test_run.plan.environment_id,
                    "variables": test_run.plan.variables,
                    "platform": step.platform,
                    "method": step.method,
                    "path": step.path,
                    "headers": step.headers,
                    "query_params": step.query_params,
                    "body": step.body,
                    "auth_config": step.auth_config,
                    "assertions": step.assertions,
                    "timeout": test_run.plan.timeout_seconds,
                }
                result = execute_debug_request(payload)
                step_passed = bool(result.get("ok") and result.get("passed"))
                if step_passed:
                    passed += 1
                    status = TestRunStep.Status.PASSED
                else:
                    failed += 1
                    status = TestRunStep.Status.FAILED

                TestRunStep.objects.create(
                    run=test_run,
                    scenario_name=scenario.name,
                    step_name=step.name,
                    status=status,
                    sort_order=sort_order,
                    request=result.get("request") or {},
                    response=result.get("response") or {},
                    assertions=result.get("assertions") or [],
                    logs=result.get("logs") or [],
                    error_message=result.get("error") or "",
                    duration_ms=(result.get("response") or {}).get("elapsed_ms") or 0,
                )

                if failed and test_run.plan.failure_strategy == test_run.plan.FailureStrategy.FAST_FAIL:
                    skipped = _mark_remaining_skipped(test_run, scenarios, scenario.id, step.id, sort_order)
                    raise StopIteration

        final_status = TestRun.Status.PASSED if failed == 0 else TestRun.Status.FAILED
    except StopIteration:
        final_status = TestRun.Status.FAILED
    except Exception as exc:
        final_status = TestRun.Status.FAILED
        test_run.error_message = str(exc)

    finished_at = timezone.now()
    duration_ms = int((finished_at - test_run.started_at).total_seconds() * 1000) if test_run.started_at else 0
    summary = {
        "total": total + skipped,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": round((passed / total) * 100, 2) if total else 0,
    }
    test_run.status = final_status
    test_run.finished_at = finished_at
    test_run.duration_ms = duration_ms
    test_run.summary = summary
    test_run.report = {"summary": summary}
    test_run.save(
        update_fields=[
            "status",
            "finished_at",
            "duration_ms",
            "summary",
            "report",
            "error_message",
            "updated_at",
        ]
    )
    return summary


def _mark_remaining_skipped(test_run, scenarios, current_scenario_id, current_step_id, sort_order: int) -> int:
    skipped = 0
    after_current = False
    for scenario in scenarios:
        if scenario.id == current_scenario_id:
            after_current = True
        if not after_current:
            continue
        for step in scenario.steps.filter(is_active=True):
            if scenario.id == current_scenario_id and step.id <= current_step_id:
                continue
            sort_order += 1
            skipped += 1
            TestRunStep.objects.create(
                run=test_run,
                scenario_name=scenario.name,
                step_name=step.name,
                status=TestRunStep.Status.SKIPPED,
                sort_order=sort_order,
                logs=["Skipped because failure strategy is fast_fail."],
            )
    return skipped
