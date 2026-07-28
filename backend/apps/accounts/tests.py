from django.test import TestCase

from apps.accounts.models import Permission
from apps.accounts.serializers import RoleSerializer
from apps.accounts.services import ensure_builtin_roles, expand_permission_hierarchy


class RolePermissionHierarchyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_builtin_roles()

    def test_import_permission_includes_view_and_page_ancestors(self):
        import_permission = Permission.objects.get(code="api.import")

        codes = {item.code for item in expand_permission_hierarchy([import_permission])}

        self.assertSetEqual(
            codes,
            {"api.import", "api_integration.read", "page.config.api_integration", "page.config"},
        )

    def test_menu_permission_includes_all_child_capabilities(self):
        menu_permission = Permission.objects.get(code="page.config.api_integration")

        codes = {item.code for item in expand_permission_hierarchy([menu_permission])}

        self.assertSetEqual(
            codes,
            {"api.import", "api_integration.read", "page.config.api_integration", "page.config"},
        )

    def test_role_serializer_normalizes_selected_permission_hierarchy(self):
        import_permission = Permission.objects.get(code="api.import")
        serializer = RoleSerializer(
            data={"name": "接口导入角色", "code": "api-import-role", "permissions": [import_permission.id]},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        role = serializer.save()

        self.assertSetEqual(
            set(role.permissions.values_list("code", flat=True)),
            {"api.import", "api_integration.read", "page.config.api_integration", "page.config"},
        )
