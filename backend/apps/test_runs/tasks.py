from celery import shared_task
from django.utils import timezone
import json

from apps.api_testing.models import ApiTestCase
from apps.api_testing.services import execute_debug_request
from apps.scheduling.models import ScheduledPlan
from apps.scheduling.notification_services import dispatch_test_run_notifications
from apps.test_runs.models import TestRun, TestRunStep


@shared_task(bind=True)
def run_api_suite(self, test_run_id: int) -> dict:
    """执行一个测试套件，并把每个场景步骤和单接口用例写入执行明细。"""
    test_run = TestRun.objects.select_related("suite", "environment").get(pk=test_run_id)
    test_run.status = TestRun.Status.RUNNING
    test_run.celery_task_id = self.request.id or test_run.celery_task_id
    test_run.started_at = timezone.now()
    test_run.logs = _append_log(test_run.logs, "info", f"测试套件开始执行：{test_run.suite.name}")
    test_run.save(update_fields=["status", "celery_task_id", "started_at", "logs", "updated_at"])
    _update_schedule_result(test_run, "running")

    total = passed = failed = skipped = 0
    sort_order = 0

    try:
        suite = test_run.suite
        run_config = suite.run_config or {}
        timeout_seconds = int(run_config.get("timeout_seconds") or 30)
        failure_strategy = run_config.get("failure_strategy") or "continue"
        scenarios = list(suite.scenarios.prefetch_related("steps").filter(is_active=True))

        case_ids = suite.case_ids or []
        if case_ids:
            cases = ApiTestCase.objects.select_related("api").filter(id__in=case_ids, is_active=True, api__is_active=True).order_by("id")
            for case in cases:
                api = case.api
                total += 1
                sort_order += 1
                request_override = case.request_override or {}
                payload = {
                    "environment": test_run.environment_id or run_config.get("environment"),
                    "variables": case.variables or {},
                    "platform": api.platform,
                    "module": api.module_id,
                    "method": api.method,
                    "path": api.path,
                    "headers": request_override.get("headers", api.headers),
                    "query_params": request_override.get("query_params", api.query_params),
                    "body": request_override.get("body", api.body),
                    "auth_config": request_override.get("auth_config", api.auth_config),
                    "assertions": case.assertions or api.assertions,
                    "timeout": timeout_seconds,
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
                    scenario_name="单接口用例",
                    step_name=case.name,
                    status=step_status,
                    sort_order=sort_order,
                    request=result.get("request") or {},
                    response=result.get("response") or {},
                    assertions=result.get("assertions") or [],
                    logs=result.get("logs") or [],
                    error_message=result.get("error") or "",
                    duration_ms=(result.get("response") or {}).get("elapsed_ms") or 0,
                )
                test_run.logs = _append_log(test_run.logs, "info" if step_passed else "error", f"{case.name} {'通过' if step_passed else '失败'}")

                if failed and failure_strategy == "fast_fail":
                    skipped = max(len(case_ids) - total, 0)
                    raise StopIteration

        for scenario in scenarios:
            scenario_variables = dict(run_config.get("variables") or {})
            for step in scenario.steps.filter(is_active=True):
                total += 1
                sort_order += 1
                variables_before = _variable_snapshot(scenario_variables)
                payload = {
                    "environment": test_run.environment_id or scenario.environment_id or run_config.get("environment"),
                    "variables": scenario_variables,
                    "platform": step.platform,
                    "module": step.api.module_id if step.api_id else None,
                    "method": step.method,
                    "path": step.path,
                    "headers": step.headers,
                    "query_params": step.query_params,
                    "body": step.body,
                    "auth_config": step.auth_config,
                    "pre_test_data_sources": step.pre_data_source_ids,
                    "post_test_data_sources": step.post_data_source_ids,
                    "extractors": step.extractors,
                    "assertions": step.assertions,
                    "timeout": timeout_seconds,
                }
                result = execute_debug_request(payload)
                scenario_variables.update(result.get("runtime_variables") or result.get("variables") or {})
                variables_after = _variable_snapshot(scenario_variables)
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
                    request={
                        **(result.get("request") or {}),
                        "variables_before": variables_before,
                        "variables_after": variables_after,
                    },
                    response=result.get("response") or {},
                    assertions=result.get("assertions") or [],
                    logs=result.get("logs") or [],
                    error_message=result.get("error") or "",
                    duration_ms=(result.get("response") or {}).get("elapsed_ms") or 0,
                )
                test_run.logs = _append_log(test_run.logs, "info" if step_passed else "error", f"{scenario.name} / {step.name} {'通过' if step_passed else '失败'}")

                if failed and failure_strategy == "fast_fail":
                    skipped = _mark_remaining_skipped(test_run, scenarios, scenario.id, step.id, sort_order)
                    raise StopIteration

        final_status = TestRun.Status.COMPLETED
    except StopIteration:
        final_status = TestRun.Status.COMPLETED
        test_run.logs = _append_log(test_run.logs, "warning", "已按失败快速停止策略终止剩余步骤")
    except Exception as exc:
        final_status = TestRun.Status.FAILED
        test_run.error_message = str(exc)
        test_run.logs = _append_log(test_run.logs, "error", f"执行异常：{exc}")

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
    test_run.logs = _append_log(test_run.logs, "info" if final_status == TestRun.Status.COMPLETED else "error", f"执行结束：总数 {summary['total']}，通过 {passed}，失败 {failed}，跳过 {skipped}")
    test_run.save(
        update_fields=[
            "status",
            "finished_at",
            "duration_ms",
            "summary",
            "report",
            "logs",
            "error_message",
            "updated_at",
        ]
    )
    _update_schedule_result(test_run, _schedule_result_status(test_run))
    dispatch_test_run_notifications(test_run)
    return summary


def _schedule_result_status(test_run: TestRun) -> str:
    """按业务结果计算调度计划最近结果，有失败步骤时整体视为失败。"""
    if test_run.status == TestRun.Status.FAILED:
        return "failed"
    return "failed" if int((test_run.summary or {}).get("failed") or 0) > 0 else "success"


def _update_schedule_result(test_run: TestRun, status: str) -> None:
    """回写调度计划最近执行结果，供调度计划列表直接展示。"""
    if not test_run.schedule_id:
        return
    ScheduledPlan.objects.filter(pk=test_run.schedule_id).update(last_status=status)


def _append_log(logs, level: str, message: str) -> list[dict]:
    items = list(logs or [])
    items.append({"time": timezone.now().isoformat(), "level": level, "message": message})
    return items[-500:]


def _variable_snapshot(variables: dict) -> dict:
    """复制一份可写入报告 JSON 的运行变量快照，便于排查场景步骤变量传递。"""
    try:
        json.dumps(variables, ensure_ascii=False)
        return dict(variables)
    except TypeError:
        return json.loads(json.dumps(variables, ensure_ascii=False, default=str))


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
