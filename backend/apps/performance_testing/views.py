import base64
import mimetypes
import re
import threading
from pathlib import Path

from celery.exceptions import TimeoutError as CeleryTimeoutError
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.utils import timezone
from kombu.exceptions import OperationalError
from rest_framework import decorators, mixins, response, status, viewsets

from apps.accounts.models import AuditLog
from apps.accounts.permissions import action_permission
from apps.core.viewsets import OperatorAuditModelViewSet
from apps.performance_testing.models import JMeterScript, PerformanceRun, PerformanceTask
from apps.performance_testing.serializers import JMeterScriptSerializer, PerformanceRunSerializer, PerformanceTaskSerializer
from apps.performance_testing.services import check_executor, perf_result_root
from apps.performance_testing.tasks import execute_performance_run, run_performance_task
from config.celery import app as celery_app

MAX_REPORT_ASSET_BYTES = 5 * 1024 * 1024
MAX_REPORT_INLINE_BYTES = 25 * 1024 * 1024


class ExecutorCheckViewSet(viewsets.ViewSet):
    permission_classes = [action_permission("run.execute")]

    def list(self, request):
        return response.Response(check_executor())


class JMeterScriptViewSet(OperatorAuditModelViewSet):
    queryset = JMeterScript.objects.prefetch_related("tasks").all()
    serializer_class = JMeterScriptSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    filterset_fields = ["is_active"]
    search_fields = ["name", "description"]
    audit_module = "jmeter_script"

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        self.write_operator_audit(AuditLog.ActionType.CREATE, serializer.save(created_by=user, updated_by=user))

    @decorators.action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        script = self.get_object()
        script.is_active = not script.is_active
        script.save(update_fields=["is_active", "updated_at"])
        return response.Response(self.get_serializer(script).data)


class PerformanceTaskViewSet(OperatorAuditModelViewSet):
    queryset = PerformanceTask.objects.select_related("script").all()
    serializer_class = PerformanceTaskSerializer
    permission_classes = [action_permission("api.read", "api.write", "api.delete")]
    filterset_fields = ["script", "is_active"]
    search_fields = ["name", "description", "script__name"]
    audit_module = "performance_task"

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        self.write_operator_audit(AuditLog.ActionType.CREATE, serializer.save(created_by=user, updated_by=user))

    @decorators.action(detail=True, methods=["post"], url_path="run")
    def run(self, request, pk=None):
        executor = check_executor()
        if not executor["ok"]:
            return response.Response(executor, status=status.HTTP_400_BAD_REQUEST)
        task = self.get_object()
        if not task.is_active or not task.script.is_active:
            return response.Response({"detail": "任务或脚本已停用，无法执行。"}, status=status.HTTP_400_BAD_REQUEST)

        perf_run = PerformanceRun.objects.create(task=task)
        _dispatch_run(perf_run)
        return response.Response(PerformanceRunSerializer(perf_run).data, status=status.HTTP_202_ACCEPTED)

    @decorators.action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        task = self.get_object()
        task.is_active = not task.is_active
        task.save(update_fields=["is_active", "updated_at"])
        return response.Response(self.get_serializer(task).data)


class PerformanceRunViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = PerformanceRun.objects.select_related("task", "task__script").all()
    serializer_class = PerformanceRunSerializer
    permission_classes = [action_permission("run.read")]
    filterset_fields = ["task", "status"]
    search_fields = ["task__name", "task__script__name", "celery_task_id"]

    @decorators.action(detail=True, methods=["get"], url_path="html-report")
    def html_report(self, request, pk=None):
        run = self.get_object()
        return _report_file_response(run, "index.html")

    @decorators.action(detail=True, methods=["get"], url_path=r"html-report-files/(?P<file_path>.+)")
    def html_report_file(self, request, pk=None, file_path=""):
        run = self.get_object()
        return _report_file_response(run, file_path)

    @decorators.action(detail=True, methods=["post"], url_path="mark-failed")
    def mark_failed(self, request, pk=None):
        perf_run = self.get_object()
        if perf_run.status != PerformanceRun.Status.PENDING:
            return response.Response(self.get_serializer(perf_run).data)
        perf_run.status = PerformanceRun.Status.FAILED
        perf_run.error_message = "任务长时间未被执行，已手动标记失败。"
        perf_run.logs = list(perf_run.logs or []) + [{"level": "error", "message": perf_run.error_message}]
        perf_run.finished_at = timezone.now()
        perf_run.save(update_fields=["status", "error_message", "logs", "finished_at", "updated_at"])
        return response.Response(self.get_serializer(perf_run).data)

    @decorators.action(detail=True, methods=["post"], url_path="execute")
    def execute(self, request, pk=None):
        perf_run = self.get_object()
        if perf_run.status == PerformanceRun.Status.RUNNING:
            return response.Response(self.get_serializer(perf_run).data)
        if not perf_run.task.is_active or not perf_run.task.script.is_active:
            return response.Response({"detail": "任务或脚本已停用，无法执行。"}, status=status.HTTP_400_BAD_REQUEST)
        perf_run.status = PerformanceRun.Status.PENDING
        perf_run.error_message = ""
        perf_run.started_at = None
        perf_run.finished_at = None
        perf_run.duration_ms = 0
        perf_run.logs = [{"level": "warning", "message": "重新提交执行记录"}]
        perf_run.save(update_fields=["status", "error_message", "started_at", "finished_at", "duration_ms", "logs", "updated_at"])

        _dispatch_run(perf_run)
        return response.Response(self.get_serializer(perf_run).data, status=status.HTTP_202_ACCEPTED)


def _dispatch_run(perf_run: PerformanceRun) -> None:
    if getattr(settings, "PERF_USE_CELERY", False) and _celery_worker_available():
        async_result = run_performance_task.delay(perf_run.id)
        perf_run.celery_task_id = async_result.id
        perf_run.logs = list(perf_run.logs or []) + [{"level": "info", "message": "已提交 Celery worker 执行"}]
        perf_run.save(update_fields=["celery_task_id", "logs", "updated_at"])
        return

    perf_run.logs = list(perf_run.logs or []) + [{"level": "warning", "message": "已使用本地后台执行性能任务"}]
    perf_run.save(update_fields=["logs", "updated_at"])
    threading.Thread(target=execute_performance_run, args=(perf_run.id,), daemon=True).start()


def _celery_worker_available() -> bool:
    try:
        return bool(celery_app.control.ping(timeout=1.0))
    except (OperationalError, CeleryTimeoutError, OSError):
        return False
    except Exception:
        return False


def _report_file_response(run: PerformanceRun, file_path: str):
    report_dir, requested = _resolve_report_file(run, file_path)
    if not requested.exists() or not requested.is_file():
        raise Http404("文件不存在")
    if requested.suffix.lower() in {".html", ".htm"}:
        html = requested.read_text(encoding="utf-8", errors="ignore")
        return HttpResponse(_rewrite_report_html(run, report_dir, html), content_type="text/html; charset=utf-8")
    return FileResponse(requested.open("rb"), as_attachment=False)


def _resolve_report_file(run: PerformanceRun, file_path: str) -> tuple[Path, Path]:
    if not run.html_report_dir:
        raise Http404("报告不存在")

    report_dir = Path(run.html_report_dir).resolve()
    result_root = perf_result_root().resolve()
    try:
        report_dir.relative_to(result_root)
    except ValueError as exc:
        raise Http404("报告路径非法") from exc

    requested = (report_dir / file_path).resolve()
    try:
        requested.relative_to(report_dir)
    except ValueError as exc:
        raise Http404("文件路径非法") from exc
    return report_dir, requested


def _rewrite_report_html(run: PerformanceRun, report_dir: Path, html: str) -> str:
    total_inlined = 0

    def replace_path(match):
        nonlocal total_inlined
        prefix, path, suffix = match.group(1), match.group(2), match.group(3)
        if "://" in path or path.startswith("#") or path.startswith("/") or path.startswith("data:"):
            return match.group(0)
        clean_path = path.split("?", 1)[0].split("#", 1)[0]
        if not clean_path:
            return match.group(0)
        try:
            _, requested = _resolve_report_file(run, clean_path)
        except Http404:
            return match.group(0)
        if not requested.exists() or not requested.is_file():
            return match.group(0)
        size = requested.stat().st_size
        if size > MAX_REPORT_ASSET_BYTES or total_inlined + size > MAX_REPORT_INLINE_BYTES:
            return match.group(0)
        total_inlined += size
        mime_type = mimetypes.guess_type(str(requested))[0] or "application/octet-stream"
        encoded = base64.b64encode(requested.read_bytes()).decode("ascii")
        return f'{prefix}data:{mime_type};base64,{encoded}{suffix}'

    return re.sub(r'((?:src|href)=["\'])([^"\']+)(["\'])', replace_path, html)
