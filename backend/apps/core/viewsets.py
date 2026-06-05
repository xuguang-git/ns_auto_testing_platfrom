from rest_framework import viewsets

from apps.accounts.models import AuditLog
from apps.accounts.services import write_audit


class OperatorAuditModelViewSet(viewsets.ModelViewSet):
    audit_module = "system"

    def perform_create(self, serializer):
        kwargs = {}
        if self.model_has_field(serializer.Meta.model, "created_by"):
            kwargs["created_by"] = self.request.user if self.request.user.is_authenticated else None
        if self.model_has_field(serializer.Meta.model, "updated_by"):
            kwargs["updated_by"] = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(**kwargs)
        self.write_operator_audit(AuditLog.ActionType.CREATE, instance)

    def perform_update(self, serializer):
        kwargs = {}
        if self.model_has_field(serializer.Meta.model, "updated_by"):
            kwargs["updated_by"] = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(**kwargs)
        self.write_operator_audit(AuditLog.ActionType.UPDATE, instance)

    def perform_destroy(self, instance):
        self.write_operator_audit(AuditLog.ActionType.DELETE, instance)
        instance.delete()

    def write_operator_audit(self, action_type, instance):
        action_label = getattr(action_type, "label", str(action_type))
        write_audit(
            request=self.request,
            action_type=action_type,
            module=self.audit_module,
            target_type=instance.__class__.__name__,
            target_id=str(getattr(instance, "id", "")),
            summary=f"{action_label} {instance}",
        )

    def model_has_field(self, model, field_name: str) -> bool:
        return any(field.name == field_name for field in model._meta.fields)
