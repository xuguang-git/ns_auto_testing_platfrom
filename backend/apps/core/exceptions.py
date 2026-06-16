from __future__ import annotations

import logging
from typing import Any

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ErrorDetail, NotAuthenticated, PermissionDenied, Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core.response_codes import BAD_REQUEST, FORBIDDEN, NOT_FOUND, SERVER_ERROR, THROTTLED, UNAUTHORIZED, VALIDATION_ERROR


logger = logging.getLogger(__name__)


def unified_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API exception", exc_info=exc)
        return Response(
            {"code": SERVER_ERROR, "message": "服务器内部错误，请稍后重试或联系管理员。", "data": None, "errors": {}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    message = _extract_message(response.data) or _fallback_message(exc, response.status_code)
    response.data = {
        "code": _business_code(exc, response.status_code),
        "message": message,
        "data": None,
        "errors": _normalize_errors(response.data),
    }
    return response


def _business_code(exc, status_code: int) -> int:
    if isinstance(exc, ValidationError):
        return VALIDATION_ERROR
    if isinstance(exc, (NotAuthenticated,)):
        return UNAUTHORIZED
    if isinstance(exc, PermissionDenied):
        return FORBIDDEN
    if isinstance(exc, Http404):
        return NOT_FOUND
    if isinstance(exc, Throttled):
        return THROTTLED
    if status_code >= 500:
        return SERVER_ERROR
    if status_code == 401:
        return UNAUTHORIZED
    if status_code == 403:
        return FORBIDDEN
    if status_code == 404:
        return NOT_FOUND
    if status_code == 422:
        return VALIDATION_ERROR
    if status_code == 429:
        return THROTTLED
    return BAD_REQUEST


def _extract_message(data: Any) -> str:
    if isinstance(data, dict):
        for key in ("message", "detail", "error", "non_field_errors"):
            if key in data:
                return _stringify_first(data[key])
        for value in data.values():
            message = _stringify_first(value)
            if message:
                return message
        return ""
    return _stringify_first(data)


def _stringify_first(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, ErrorDetail):
        return str(value)
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
                return f"{key}: {message}" if key not in ("detail", "message") else message
        return ""
    return str(value)


def _normalize_errors(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return {str(key): _plain_value(value) for key, value in data.items()}
    if data in (None, ""):
        return {}
    return {"non_field_errors": _plain_value(data)}


def _plain_value(value: Any) -> Any:
    if isinstance(value, ErrorDetail):
        return str(value)
    if isinstance(value, list):
        return [_plain_value(item) for item in value]
    if isinstance(value, tuple):
        return [_plain_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain_value(item) for key, item in value.items()}
    return value


def _fallback_message(exc, status_code: int) -> str:
    if isinstance(exc, Http404):
        return "资源不存在。"
    if isinstance(exc, APIException) and getattr(exc, "detail", None):
        return _stringify_first(exc.detail)
    if status_code >= 500:
        return "服务器内部错误，请稍后重试或联系管理员。"
    return "请求处理失败，请检查后重试。"
