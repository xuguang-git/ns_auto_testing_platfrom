from celery import shared_task
from django.utils import timezone
import json

from apps.api_testing.services import execute_debug_request
from apps.scheduling.models import ScheduledPlan
from apps.scheduling.notification_services import dispatch_test_run_notifications
from apps.test_runs.models import TestRun, TestRunStep
from apps.test_runs.snapshots import persist_execution_snapshot


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
    pending_steps: list[TestRunStep] = []

    def add_step(record: TestRunStep) -> None:
        pending_steps.append(record)
        if len(pending_steps) >= 100:
            TestRunStep.objects.bulk_create(pending_steps)
            pending_steps.clear()

    try:
        snapshot = persist_execution_snapshot(test_run)
        run_config = snapshot.get("run_config") or {}
        timeout_seconds = int(run_config.get("timeout_seconds") or 30)
        failure_strategy = run_config.get("failure_strategy") or "continue"
        scenarios = snapshot.get("scenarios") or []
        cases = snapshot.get("cases") or []
        test_run.logs = _append_log(test_run.logs, "info", f"执行成员快照：场景 {len(scenarios)} 个，单接口用例 {len(cases)} 个")
        test_run.save(update_fields=["logs", "updated_at"])
        if cases:
            for case in cases:
                total += 1
                sort_order += 1
                payload = {
                    "environment": case.get("environment_id") or test_run.environment_id or run_config.get("environment"),
                    "variables": case.get("variables") or {},
                    "platform": case.get("platform"),
                    "module": case.get("module_id"),
                    "method": case.get("method"),
                    "path": case.get("path"),
                    "headers": case.get("headers") or [],
                    "query_params": case.get("query_params") or [],
                    "body": case.get("body") or {},
                    "auth_config": case.get("auth_config") or {},
                    "assertions": case.get("assertions") or [],
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

                add_step(TestRunStep(
                    run=test_run,
                    scenario_name="单接口用例",
                    step_name=case.get("name") or "单接口用例",
                    status=step_status,
                    sort_order=sort_order,
                    request=result.get("request") or {},
                    response={
                        **(result.get("response") or {}),
                        "diagnosis": result.get("diagnosis") or {},
                    },
                    assertions=result.get("assertions") or [],
                    logs=result.get("logs") or [],
                    error_message=result.get("error") or "",
                    duration_ms=(result.get("response") or {}).get("elapsed_ms") or 0,
                ))
                test_run.logs = _append_log(test_run.logs, "info" if step_passed else "error", f"{case.get('name') or '单接口用例'} {'通过' if step_passed else '失败'}")

                if failed and failure_strategy == "fast_fail":
                    skipped = max(len(cases) - total, 0)
                    raise StopIteration

        for scenario in scenarios:
            scenario_variables = dict(run_config.get("variables") or {})
            for step in scenario.get("steps") or []:
                total += 1
                sort_order += 1
                variables_before = _variable_snapshot(scenario_variables)
                payload = {
                    "environment": scenario.get("environment_id") or test_run.environment_id or run_config.get("environment"),
                    "variables": scenario_variables,
                    "platform": step.get("platform"),
                    "module": step.get("module_id"),
                    "method": step.get("method"),
                    "path": step.get("path"),
                    "headers": step.get("headers") or [],
                    "query_params": step.get("query_params") or [],
                    "body": step.get("body") or {},
                    "auth_config": step.get("auth_config") or {},
                    "pre_test_data_sources": step.get("pre_test_data_source_ids") or [],
                    "post_test_data_sources": step.get("post_test_data_source_ids") or [],
                    "extractors": step.get("extractors") or [],
                    "assertions": step.get("assertions") or [],
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

                add_step(TestRunStep(
                    run=test_run,
                    scenario_name=scenario.get("name") or "场景用例",
                    step_name=step.get("name") or "场景步骤",
                    status=status,
                    sort_order=sort_order,
                    request={
                        **(result.get("request") or {}),
                        "variables_before": variables_before,
                        "variables_after": variables_after,
                    },
                    response={
                        **(result.get("response") or {}),
                        "diagnosis": result.get("diagnosis") or {},
                    },
                    assertions=result.get("assertions") or [],
                    logs=result.get("logs") or [],
                    error_message=result.get("error") or "",
                    duration_ms=(result.get("response") or {}).get("elapsed_ms") or 0,
                ))
                test_run.logs = _append_log(test_run.logs, "info" if step_passed else "error", f"{scenario.get('name') or '场景用例'} / {step.get('name') or '场景步骤'} {'通过' if step_passed else '失败'}")

                if failed and failure_strategy == "fast_fail":
                    skipped = _mark_remaining_skipped(test_run, scenarios, scenario.get("id"), step.get("id"), sort_order)
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
    if pending_steps:
        TestRunStep.objects.bulk_create(pending_steps)
    duration_ms = int((finished_at - test_run.started_at).total_seconds() * 1000) if test_run.started_at else 0
    diagnosis_summary = _build_diagnosis_summary(test_run)
    summary = {
        "total": total + skipped,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": round((passed / total) * 100, 2) if total else 0,
        "diagnosis": diagnosis_summary,
    }
    test_run.status = final_status
    test_run.finished_at = finished_at
    test_run.duration_ms = duration_ms
    test_run.summary = summary
    test_run.report = {"summary": summary, "diagnosis": diagnosis_summary}
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


def _build_diagnosis_summary(test_run: TestRun) -> dict:
    """按步骤诊断结果聚合报告摘要，不在查询报告时重复扫描和推导。"""
    failure_type_counts: dict[str, int] = {}
    environment_issue_count = 0
    retry_suggested_count = 0
    for step in test_run.steps.all():
        diagnosis = (step.response or {}).get("diagnosis") or {}
        failure_type = diagnosis.get("failure_type")
        if not failure_type:
            continue
        failure_type_counts[failure_type] = failure_type_counts.get(failure_type, 0) + 1
        if diagnosis.get("is_environment_issue"):
            environment_issue_count += 1
        if diagnosis.get("retry_suggested"):
            retry_suggested_count += 1
    top_failure_type = ""
    if failure_type_counts:
        top_failure_type = max(failure_type_counts.items(), key=lambda item: item[1])[0]
    return {
        "failure_type_counts": failure_type_counts,
        "environment_issue_count": environment_issue_count,
        "retry_suggested_count": retry_suggested_count,
        "top_failure_type": top_failure_type,
    }


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
        if scenario.get("id") == current_scenario_id:
            after_current = True
        if not after_current:
            continue
        for step in scenario.get("steps") or []:
            if scenario.get("id") == current_scenario_id and step.get("id") <= current_step_id:
                continue
            sort_order += 1
            skipped += 1
            TestRunStep.objects.create(
                run=test_run,
                scenario_name=scenario.get("name") or "场景用例",
                step_name=step.get("name") or "场景步骤",
                status=TestRunStep.Status.SKIPPED,
                sort_order=sort_order,
                logs=["Skipped because failure strategy is fast_fail."],
            )
    return skipped
