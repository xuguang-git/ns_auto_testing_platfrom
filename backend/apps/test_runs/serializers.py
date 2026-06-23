from collections import OrderedDict

from django.utils import timezone
from rest_framework import serializers

from apps.test_runs.models import TestRun, TestRunStep


class TestRunStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestRunStep
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class TestRunSerializer(serializers.ModelSerializer):
    steps = TestRunStepSerializer(many=True, read_only=True)
    suite_name = serializers.CharField(source="suite.name", read_only=True)
    environment_name = serializers.CharField(source="environment.name", read_only=True)
    report_name = serializers.SerializerMethodField()
    step_groups = serializers.SerializerMethodField()

    def get_report_name(self, obj: TestRun) -> str:
        """按测试套件名称和执行时间生成业务可读的报告名称。"""
        suite_name = obj.suite.name if obj.suite_id and obj.suite else "测试报告"
        run_time = obj.started_at or obj.created_at
        if run_time:
            run_time = timezone.localtime(run_time)
            return f"{suite_name}{run_time.strftime('%Y%m%d%H%M%S')}"
        return f"{suite_name}{obj.pk}"

    def get_step_groups(self, obj: TestRun) -> list[dict]:
        """按场景聚合执行步骤，供前端分组展示报告明细。"""
        groups: OrderedDict[str, dict] = OrderedDict()
        steps = list(obj.steps.all())
        for step in steps:
            group_name = step.scenario_name or "单接口用例"
            group = groups.setdefault(
                group_name,
                {
                    "name": group_name,
                    "duration_ms": 0,
                    "interface_count": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "result": "success",
                    "pass_rate": 0,
                    "success_rate": 0,
                    "steps": [],
                },
            )
            group["duration_ms"] += step.duration_ms or 0
            group["interface_count"] += 1
            if step.status == TestRunStep.Status.PASSED:
                group["passed"] += 1
            elif step.status == TestRunStep.Status.FAILED:
                group["failed"] += 1
            elif step.status == TestRunStep.Status.SKIPPED:
                group["skipped"] += 1
            group["steps"].append(TestRunStepSerializer(step).data)

        for group in groups.values():
            total = group["interface_count"]
            pass_rate = round((group["passed"] / total) * 100, 2) if total else 0
            group["pass_rate"] = pass_rate
            group["success_rate"] = pass_rate
            group["result"] = "failed" if group["failed"] > 0 else "success"
        return list(groups.values())

    class Meta:
        model = TestRun
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
            "duration_ms",
            "summary",
            "report",
            "error_message",
        ]
