from rest_framework import viewsets

from apps.accounts.permissions import action_permission
from apps.test_runs.models import TestRun
from apps.test_runs.serializers import TestRunSerializer


class TestRunViewSet(viewsets.ReadOnlyModelViewSet):
    """提供测试报告列表和详情查询，导出能力后续重新设计。"""

    queryset = TestRun.objects.select_related("suite", "suite__project", "environment").prefetch_related("steps").all()
    serializer_class = TestRunSerializer
    permission_classes = [action_permission(("report.read", "run.read"))]
    filterset_fields = ["suite", "status", "trigger_type", "environment"]
    search_fields = ["suite__name", "celery_task_id"]
