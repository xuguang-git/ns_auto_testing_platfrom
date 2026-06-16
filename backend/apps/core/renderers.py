from __future__ import annotations

from typing import Any

from rest_framework.renderers import JSONRenderer

from apps.core.response_codes import SUCCESS, code_for_status


ENVELOPE_KEYS = {"code", "message", "data"}


class UnifiedJSONRenderer(JSONRenderer):
    def render(self, data: Any, accepted_media_type=None, renderer_context=None):
        response = (renderer_context or {}).get("response")
        if response is not None and response.status_code == 204:
            return super().render(data, accepted_media_type, renderer_context)
        return super().render(self._wrap(data, response), accepted_media_type, renderer_context)

    def _wrap(self, data: Any, response) -> dict[str, Any]:
        if isinstance(data, dict) and ENVELOPE_KEYS.issubset(data.keys()):
            return data

        status_code = getattr(response, "status_code", 200) or 200
        if 200 <= status_code < 300:
            return {"code": SUCCESS, "message": "success", "data": data}

        message = _extract_message(data) or "请求处理失败，请检查后重试。"
        return {
            "code": code_for_status(status_code),
            "message": message,
            "data": None,
            "errors": _normalize_errors(data),
        }


def _extract_message(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("message", "detail", "error", "non_field_errors"):
            if key in value:
                return _stringify_first(value[key])
        for item in value.values():
            message = _stringify_first(item)
            if message:
                return message
        return ""
    return _stringify_first(value)


def _stringify_first(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        for item in value:
            message = _stringify_first(item)
            if message:
                return message
        return ""
    if isinstance(value, dict):
        for key, item in value.items():
            message = _stringify_first(item)
            if message:
                return f"{key}: {message}" if key not in ("message", "detail") else message
        return ""
    return str(value)


def _normalize_errors(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if value in (None, ""):
        return {}
    return {"non_field_errors": _plain(value)}


def _plain(value: Any) -> Any:
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    return str(value)
