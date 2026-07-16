from datetime import datetime, time

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import response, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination

from apps.accounts.permissions import action_permission
from apps.test_runs.models import TestRun
from apps.test_runs.serializers import TestRunListSerializer, TestRunSerializer, TestRunStatusSerializer


class TestRunPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class TestRunViewSet(viewsets.ReadOnlyModelViewSet):
    """提供测试报告列表和详情查询，导出能力后续重新设计。"""

    queryset = TestRun.objects.all()
    serializer_class = TestRunSerializer
    pagination_class = TestRunPagination
    permission_classes = [action_permission(("report.read", "run.read"))]
    filterset_fields = ["suite", "status", "trigger_type", "environment"]
    search_fields = ["suite__name", "celery_task_id"]

    def get_queryset(self):
        return TestRun.objects.select_related("suite", "suite__project", "environment")

    def get_serializer_class(self):
        if self.action == "list":
            return TestRunListSerializer
        return TestRunSerializer

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        keyword = self.request.query_params.get("keyword", "").strip()
        if keyword:
            filters = Q(suite__name__icontains=keyword) | Q(celery_task_id__icontains=keyword)
            if keyword.isdigit():
                filters |= Q(pk=int(keyword))
            queryset = queryset.filter(filters)

        start_date = self._get_query_date("created_date_start")
        end_date = self._get_query_date("created_date_end")
        if start_date and end_date and start_date > end_date:
            raise ValidationError({"created_date_end": "结束日期不能早于开始日期。"})
        if start_date:
            queryset = queryset.filter(created_at__gte=timezone.make_aware(datetime.combine(start_date, time.min)))
        if end_date:
            queryset = queryset.filter(created_at__lte=timezone.make_aware(datetime.combine(end_date, time.max)))
        return self._filter_by_result_status(queryset)

    def _get_query_date(self, parameter_name):
        value = self.request.query_params.get(parameter_name, "").strip()
        if not value:
            return None
        parsed_date = parse_date(value)
        if not parsed_date:
            raise ValidationError({parameter_name: "日期格式必须为 YYYY-MM-DD。"})
        return parsed_date

    def _filter_by_result_status(self, queryset):
        result_status = self.request.query_params.get("result_status", "").strip()
        if not result_status:
            return queryset
        if result_status == TestRun.Status.PENDING:
            return queryset.filter(status=TestRun.Status.PENDING)
        if result_status == TestRun.Status.RUNNING:
            return queryset.filter(status=TestRun.Status.RUNNING)
        if result_status == "success":
            return queryset.filter(status=TestRun.Status.COMPLETED).filter(
                Q(summary__failed=0) | Q(summary__failed__isnull=True)
            )
        if result_status == "failed":
            return queryset.filter(Q(status=TestRun.Status.FAILED) | Q(status=TestRun.Status.COMPLETED, summary__failed__gt=0))
        raise ValidationError({"result_status": "状态筛选值无效。"})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status in {TestRun.Status.PENDING, TestRun.Status.RUNNING}:
            return response.Response(TestRunStatusSerializer(instance).data)
        instance = self.get_queryset().prefetch_related("steps").get(pk=instance.pk)
        return response.Response(TestRunSerializer(instance).data)
