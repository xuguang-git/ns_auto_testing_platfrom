import subprocess
import uuid
from pathlib import Path

from celery import shared_task
from django.db import close_old_connections
from django.utils import timezone

from apps.performance_testing.models import PerformanceRun
from apps.performance_testing.services import append_log, build_jmeter_command, executor_env, parse_jtl_summary, perf_result_root


@shared_task(bind=True)
def run_performance_task(self, run_id: int) -> dict:
    return execute_performance_run(run_id, self.request.id)


def execute_performance_run(run_id: int, execution_id: str | None = None) -> dict:
    close_old_connections()
    run = PerformanceRun.objects.select_related("task", "task__script").get(pk=run_id)
    started = timezone.now()
    run.status = PerformanceRun.Status.RUNNING
    run.celery_task_id = execution_id or run.celery_task_id or f"local-{uuid.uuid4()}"
    run.started_at = started
    run.logs = append_log(run.logs, "info", f"开始执行性能任务：{run.task.name}")
    run.save(update_fields=["status", "celery_task_id", "started_at", "logs", "updated_at"])

    run_dir = perf_result_root() / f"run_{run.id}"
    report_dir = run_dir / "html"
    jtl_path = run_dir / "result.jtl"
    run_dir.mkdir(parents=True, exist_ok=True)
    if report_dir.exists():
        _remove_dir(report_dir)
    command = build_jmeter_command(run, jtl_path, report_dir)
    run.jtl_path = str(jtl_path)
    run.html_report_dir = str(report_dir)
    run.logs = append_log(run.logs, "info", "执行命令：" + " ".join(command))
    run.save(update_fields=["jtl_path", "html_report_dir", "logs", "updated_at"])

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=max(run.task.duration_seconds + 300, 600), env=executor_env())
        if result.stdout:
            run.logs = append_log(run.logs, "info", result.stdout[-2000:])
        if result.stderr:
            run.logs = append_log(run.logs, "warning", result.stderr[-2000:])
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or f"JMeter exited with code {result.returncode}")
        run.summary = parse_jtl_summary(jtl_path)
        run.status = PerformanceRun.Status.COMPLETED
        run.logs = append_log(run.logs, "info", "性能任务执行完成")
    except Exception as exc:
        run.status = PerformanceRun.Status.FAILED
        run.error_message = str(exc)
        run.summary = parse_jtl_summary(jtl_path)
        run.logs = append_log(run.logs, "error", f"性能任务执行失败：{exc}")

    finished = timezone.now()
    run.finished_at = finished
    run.duration_ms = int((finished - started).total_seconds() * 1000)
    run.save(update_fields=["status", "finished_at", "duration_ms", "summary", "logs", "error_message", "updated_at"])
    close_old_connections()
    return run.summary


def _remove_dir(path: Path) -> None:
    for child in path.iterdir():
        if child.is_dir():
            _remove_dir(child)
        else:
            child.unlink()
    path.rmdir()
