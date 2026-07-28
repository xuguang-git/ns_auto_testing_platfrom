from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.test import RequestFactory, SimpleTestCase
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.accounts.authentication import StrongTokenAuthentication
from apps.accounts.security import ACCESS_COOKIE_NAME
from apps.core.response_codes import UNAUTHORIZED
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


class TokenOnlyBusinessApiTests(SimpleTestCase):
    class ProtectedView(APIView):
        permission_classes = [IsAuthenticated]

        def patch(self, request):
            return Response({"authenticated": request.user.is_authenticated})

    def setUp(self):
        self.factory = APIRequestFactory(enforce_csrf_checks=True)
        self.view = self.ProtectedView.as_view()

    def test_business_api_uses_only_platform_token_authentication(self):
        self.assertEqual(api_settings.DEFAULT_AUTHENTICATION_CLASSES, [StrongTokenAuthentication])

    @patch("apps.accounts.authentication.authenticate_access_token")
    def test_token_authenticated_patch_ignores_residual_django_session(self, authenticate_access_token):
        user = SimpleNamespace(pk=5, is_authenticated=True)
        token = SimpleNamespace(user=user)
        authenticate_access_token.return_value = token
        request = self.factory.patch(
            "/api/v1/users/5/",
            {},
            format="json",
            HTTP_COOKIE=f"sessionid=django-admin-session; {ACCESS_COOKIE_NAME}=platform-access-token",
        )

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"authenticated": True})
        authenticate_access_token.assert_called_once_with("platform-access-token")

    def test_request_without_platform_token_returns_unified_unauthorized_response(self):
        response = self.view(self.factory.patch("/api/v1/users/5/", {}, format="json"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["code"], UNAUTHORIZED)
