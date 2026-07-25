from django.test import RequestFactory, SimpleTestCase
from rest_framework import status
from rest_framework.exceptions import ParseError, ValidationError

from apps.core.exceptions import unified_exception_handler
from apps.core.response_codes import BAD_REQUEST, VALIDATION_ERROR


class UnifiedExceptionHandlerTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().post("/api/v1/api-definitions/batch-import/", data="{", content_type="application/json")

    def test_parse_error_returns_safe_message(self):
        response = unified_exception_handler(
            ParseError("JSON parse error - Expecting property name enclosed in double quotes"),
            {"request": self.request},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], BAD_REQUEST)
        self.assertEqual(response.data["message"], "请求参数格式不正确，请检查 JSON 格式后重试。")
        self.assertEqual(response.data["errors"], {})

    def test_validation_error_keeps_field_detail(self):
        response = unified_exception_handler(ValidationError({"module_code": ["模块编码已存在"]}), {"request": self.request})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], VALIDATION_ERROR)
        self.assertEqual(response.data["errors"], {"module_code": ["模块编码已存在"]})
