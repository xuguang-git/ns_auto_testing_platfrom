from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.api_testing.models import ApiModule
from apps.projects.views import PlatformViewSet


class PlatformViewSetTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(username="platform-test-user")

    @patch("apps.accounts.permissions.has_permission", return_value=True)
    def test_create_platform_initializes_unique_unassigned_module_code(self, _mock_has_permission):
        first_response = self._create_platform("ERP", "erp")
        second_response = self._create_platform("WMS", "wms")
        long_platform_code = f"platform-{'a' * 23}"
        third_response = self._create_platform("长编码平台", long_platform_code)

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(third_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            ApiModule.objects.get(managed_platform_id=first_response.data["id"]).code,
            "unassigned-erp",
        )
        self.assertEqual(
            ApiModule.objects.get(managed_platform_id=second_response.data["id"]).code,
            "unassigned-wms",
        )
        self.assertEqual(
            ApiModule.objects.get(managed_platform_id=third_response.data["id"]).code,
            f"unassigned-{long_platform_code}",
        )

    def _create_platform(self, name, code):
        request = self.factory.post("/api/v1/platforms/", {"name": name, "code": code}, format="json")
        force_authenticate(request, user=self.user)
        return PlatformViewSet.as_view({"post": "create"})(request)
