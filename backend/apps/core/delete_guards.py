from dataclasses import dataclass
from typing import Any, Callable

from django.db.models import Manager, QuerySet
from rest_framework import status
from rest_framework.exceptions import APIException


class DeleteProtectedError(APIException):
    """删除前置校验未通过时抛出的业务异常。"""

    status_code = status.HTTP_409_CONFLICT
    default_code = "delete_protected"

    def __init__(self, object_label: str, blocked_by: list[dict[str, Any]]):
        message = f"当前{object_label}存在关联数据，不允许删除，请先清理关联数据。"
        self.payload = {
            "code": 40901,
            "message": message,
            "data": {"blocked_by": blocked_by},
            "errors": {},
        }
        super().__init__(message)


@dataclass(frozen=True)
class DeleteGuardRule:
    """声明删除对象前需要检查的关联数据。"""

    relation: str | None
    label: str
    message: str = ""
    checker: Callable[[Any], int | bool] | None = None


class DeleteGuardMixin:
    """为 ViewSet 提供统一的删除前置校验能力。"""

    delete_object_label = "数据"
    delete_guard_rules: tuple[DeleteGuardRule, ...] = ()

    def perform_destroy(self, instance):
        self.validate_delete_guards(instance)
        super().perform_destroy(instance)

    def validate_delete_guards(self, instance) -> None:
        blocked_by = []
        for rule in self.delete_guard_rules:
            count = self.get_guard_count(instance, rule)
            if count <= 0:
                continue
            blocked_by.append(
                {
                    "relation": rule.relation,
                    "label": rule.label,
                    "count": count,
                    "message": rule.message or f"存在{rule.label}，不允许删除",
                }
            )
        if blocked_by:
            raise DeleteProtectedError(self.delete_object_label, blocked_by)

    def get_relation_count(self, instance, relation: str) -> int:
        related = getattr(instance, relation)
        if isinstance(related, (Manager, QuerySet)):
            return related.count()
        if callable(related):
            related = related()
        return int(bool(related))

    def get_guard_count(self, instance, rule: DeleteGuardRule) -> int:
        if rule.checker:
            result = rule.checker(instance)
            return int(result)
        if not rule.relation:
            return 0
        return self.get_relation_count(instance, rule.relation)
