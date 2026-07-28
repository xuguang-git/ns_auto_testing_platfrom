from types import SimpleNamespace

from django.conf import settings
from django.test import RequestFactory, SimpleTestCase

from config.admin import SuperuserAdminSite
from config.urls import admin_disabled


class SuperuserAdminSiteTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.site = SuperuserAdminSite()

    def test_only_active_superuser_can_access_admin(self):
        cases = [
            (False, False, False),
            (True, False, False),
            (False, True, False),
            (True, True, True),
        ]

        for is_active, is_superuser, expected in cases:
            with self.subTest(is_active=is_active, is_superuser=is_superuser):
                request = self.factory.get("/admin/")
                request.user = SimpleNamespace(is_active=is_active, is_superuser=is_superuser)

                self.assertEqual(self.site.has_permission(request), expected)

    def test_disabled_admin_redirects_to_frontend(self):
        response = admin_disabled(self.factory.get("/admin/"))

        self.assertRedirects(response, f"{settings.FRONTEND_BASE_URL}/", fetch_redirect_response=False)
