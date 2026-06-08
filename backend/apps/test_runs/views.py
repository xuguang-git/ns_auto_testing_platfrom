from html import escape

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import decorators, response, status, viewsets
from kombu.exceptions import OperationalError

from apps.accounts.models import AuditLog
from apps.accounts.permissions import action_permission
from apps.core.viewsets import OperatorAuditModelViewSet
from apps.test_runs.models import TestPlan, TestRun
from apps.test_runs.serializers import TestPlanSerializer, TestRunSerializer
from apps.test_runs.tasks import run_test_plan
from apps.projects.services import get_default_project


class TestPlanViewSet(OperatorAuditModelViewSet):
    queryset = (
        TestPlan.objects.select_related("project", "platform_ref", "environment")
        .prefetch_related("api_suites", "api_scenarios", "ui_suites")
        .all()
    )
    serializer_class = TestPlanSerializer
    permission_classes = [action_permission("plan.read", "plan.write", "plan.delete")]
    filterset_fields = ["project", "platform_ref", "environment", "plan_type", "status", "is_active"]
    search_fields = ["name", "description"]
    audit_module = "test_plan"

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(
            project=serializer.validated_data.get("project") or get_default_project(),
            created_by=user,
            updated_by=user,
        )
        self.write_operator_audit(AuditLog.ActionType.CREATE, instance)

    @decorators.action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        if not request.user.is_superuser:
            from apps.accounts.services import has_permission

            if not has_permission(request.user, "run.execute"):
                return response.Response({"detail": "无执行测试计划权限"}, status=status.HTTP_403_FORBIDDEN)
        plan = self.get_object()
        environment_id = request.data.get("environment") or plan.environment_id
        test_run = TestRun.objects.create(
            plan=plan,
            environment_id=environment_id,
            trigger_type=TestRun.TriggerType.MANUAL,
        )
        try:
            async_result = run_test_plan.delay(test_run.id)
            test_run.celery_task_id = async_result.id
            test_run.save(update_fields=["celery_task_id", "updated_at"])
        except OperationalError as exc:
            test_run.status = TestRun.Status.FAILED
            test_run.started_at = timezone.now()
            test_run.finished_at = test_run.started_at
            test_run.error_message = f"Celery broker unavailable: {exc}"
            test_run.summary = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "pass_rate": 0}
            test_run.logs = [{"time": test_run.started_at.isoformat(), "level": "error", "message": test_run.error_message}]
            test_run.save(update_fields=["status", "started_at", "finished_at", "error_message", "summary", "logs", "updated_at"])
            serializer = TestRunSerializer(test_run)
            return response.Response(
                {
                    **serializer.data,
                    "detail": "执行任务创建成功，但 Celery/Redis 未连接，任务未异步投递。请启动 Redis 和 Celery worker 后重试。",
                },
                status=status.HTTP_202_ACCEPTED,
            )
        serializer = TestRunSerializer(test_run)
        return response.Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class TestRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TestRun.objects.select_related("plan", "plan__project", "environment").prefetch_related("steps").all()
    serializer_class = TestRunSerializer
    permission_classes = [action_permission("run.read")]
    filterset_fields = ["plan", "status", "trigger_type", "environment"]
    search_fields = ["plan__name", "celery_task_id"]

    @decorators.action(detail=True, methods=["get"], url_path="html-report")
    def html_report(self, request, pk=None):
        run = self.get_object()
        html = _render_html_report(run)
        return HttpResponse(html, content_type="text/html; charset=utf-8")


def _render_html_report(run: TestRun) -> str:
    rows = []
    for step in run.steps.all():
        rows.append(
            f"<tr><td>{step.sort_order}</td><td>{escape(step.scenario_name or '')}</td><td>{escape(step.step_name or '')}</td>"
            f"<td>{escape(step.status or '')}</td><td>{step.duration_ms}ms</td><td><pre>{escape(step.error_message or '')}</pre></td></tr>"
        )
    summary = run.summary or {}
    plan_name = escape(run.plan.name if run.plan else "")
    environment_name = escape(run.environment.name if run.environment else "-")
    run_status = escape(run.status or "")
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>NS-ATP Test Report #{run.id}</title>
  <style>
    body {{ font-family: Arial, 'Microsoft YaHei', sans-serif; margin: 24px; color: #1f2937; }}
    h1 {{ font-size: 22px; }}
    .summary {{ display: flex; gap: 12px; margin: 16px 0; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; min-width: 120px; }}
    .value {{ font-size: 24px; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 8px; text-align: left; font-size: 13px; }}
    th {{ background: #f9fafb; }}
    pre {{ white-space: pre-wrap; margin: 0; }}
  </style>
</head>
<body>
  <h1>{plan_name} - 执行报告 #{run.id}</h1>
  <p>状态：{run_status} ｜ 环境：{environment_name} ｜ 耗时：{run.duration_ms}ms</p>
  <div class="summary">
    <div class="card"><div>总数</div><div class="value">{summary.get('total', 0)}</div></div>
    <div class="card"><div>通过</div><div class="value">{summary.get('passed', 0)}</div></div>
    <div class="card"><div>失败</div><div class="value">{summary.get('failed', 0)}</div></div>
    <div class="card"><div>通过率</div><div class="value">{summary.get('pass_rate', 0)}%</div></div>
  </div>
  <table><thead><tr><th>#</th><th>场景</th><th>步骤</th><th>状态</th><th>耗时</th><th>错误</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
</body>
</html>
"""
