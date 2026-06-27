from django.core.management.base import BaseCommand

from apps.accounts.models import Permission, Role
from apps.accounts.services import HIDDEN_PERMISSION_CODES, PAGE_ACTION_COMPAT_MAP, PAGE_PERMISSION_DEFINITIONS, ROLE_PERMISSION_CODES, ensure_builtin_roles


class Command(BaseCommand):
    help = "同步权限树，并补齐内置角色的基础读取权限。"

    def handle(self, *args, **options):
        ensure_builtin_roles()
        hidden_permissions = list(Permission.objects.filter(code__in=HIDDEN_PERMISSION_CODES))
        required_read_permissions = list(Permission.objects.filter(code__in=["platform.read", "module.read"]))
        for role in Role.objects.prefetch_related("permissions"):
            if hidden_permissions:
                role.permissions.remove(*hidden_permissions)
            codes = set(role.permissions.values_list("code", flat=True))
            if codes.intersection({"api.read", "api.create", "api.update", "api.write", "api.delete", "api.debug"}):
                role.permissions.add(*required_read_permissions)
                codes.update(permission.code for permission in required_read_permissions)
            compatible_codes = self._compatible_action_codes(codes)
            if compatible_codes:
                role.permissions.add(*Permission.objects.filter(code__in=compatible_codes))
                codes.update(compatible_codes)
            builtin_role_codes = ROLE_PERMISSION_CODES.get(role.code) or ROLE_PERMISSION_CODES.get(self._builtin_code(role.code))
            if builtin_role_codes:
                builtin_codes = set(builtin_role_codes) - HIDDEN_PERMISSION_CODES
                role.permissions.add(*Permission.objects.filter(code__in=builtin_codes))
                codes.update(builtin_codes)
            if role.code == Role.BuiltinCode.SUPER_ADMIN:
                role.permissions.add(*Permission.objects.exclude(code__in=HIDDEN_PERMISSION_CODES))
                continue
            role.permissions.add(*Permission.objects.filter(code__in=self._navigation_codes(codes)))
            if hidden_permissions:
                role.permissions.remove(*hidden_permissions)
        self.stdout.write(self.style.SUCCESS("权限树已同步。"))

    def _navigation_codes(self, permission_codes: set[str]) -> set[str]:
        if not permission_codes:
            return set()
        navigation_codes = {"page.dashboard"}
        for page in PAGE_PERMISSION_DEFINITIONS:
            if page["code"] in permission_codes:
                navigation_codes.add(page["code"])
            for child in page.get("children", []):
                if child["code"] in permission_codes or permission_codes.intersection(set(child.get("actions", []))):
                    navigation_codes.update({page["code"], child["code"]})
        return navigation_codes

    def _compatible_action_codes(self, permission_codes: set[str]) -> set[str]:
        compatible_codes = set()
        for page_code, action_map in PAGE_ACTION_COMPAT_MAP.items():
            if page_code in permission_codes:
                compatible_codes.update(next_code for old_code, next_code in action_map.items() if old_code in permission_codes)
        return compatible_codes

    def _builtin_code(self, role_code: str):
        try:
            return Role.BuiltinCode(role_code)
        except ValueError:
            return None
