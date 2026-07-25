from django.test import SimpleTestCase
from apps.api_testing.serializers import BatchImportRequestSerializer
from apps.api_testing.views import _batch_import_validation_response


class BatchImportRequestSerializerTests(SimpleTestCase):
    def test_invalid_items_return_flat_details_and_all_item_numbers(self):
        serializer = BatchImportRequestSerializer(
            data={
                "module_code": "order-management",
                "items": [
                    {"name": "a" * 101, "path": "/api/orders", "method": "POST", "params": {}},
                    {"name": "", "path": "/api/orders/2", "method": "GET", "params": {}},
                ],
            }
        )

        self.assertFalse(serializer.is_valid())
        response = _batch_import_validation_response(serializer.errors)

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["message"], "接口参数校验失败，共 2 个接口存在问题。")
        self.assertEqual(response.data["data"]["invalid_item_nos"], [1, 2])
        self.assertFalse(response.data["data"]["truncated"])
        self.assertEqual(response.data["data"]["items"][0]["errors"][0]["field"], "name")
        self.assertEqual(response.data["errors"], {})

    def test_invalid_items_return_all_numbers_and_truncate_details_after_limit(self):
        serializer = BatchImportRequestSerializer(
            data={
                "module_code": "order-management",
                "items": [{"name": f"接口{index}", "method": "GET", "params": {}} for index in range(1, 12)],
            }
        )

        self.assertFalse(serializer.is_valid())
        response = _batch_import_validation_response(serializer.errors)

        self.assertEqual(response.data["message"], "本次共有 11 个接口存在参数问题，已展示前 10 个，请修正后重试。")
        self.assertEqual(response.data["data"]["invalid_item_nos"], list(range(1, 12)))
        self.assertTrue(response.data["data"]["truncated"])
        self.assertEqual(len(response.data["data"]["items"]), 10)
