import base64
import ipaddress
import json
import logging
import re
import socket
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings
from django.utils import timezone

from apps.projects.db_services import execute_test_data_source
from apps.projects.models import Environment, TestDataSource


logger = logging.getLogger(__name__)
VAR_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_.-]+)\s*}}")
EXACT_VAR_PATTERN = re.compile(r"^{{\s*([a-zA-Z0-9_.-]+)\s*}}$")
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
REQUEST_CONTROL_CACHE_SECONDS = 60
PRE_REQUEST_FAILURE_MESSAGE = "前置操作失败，请检查前置操作步骤和被测平台"
_REQUEST_CONTROL_METHOD_CACHE: dict[int, tuple[float, frozenset[str] | None]] = {}
BLOCKED_REQUEST_HEADERS = {
    "host",
    "content-length",
    "connection",
    "proxy-authorization",
    "proxy-authenticate",
    "transfer-encoding",
    "upgrade",
}
SENSITIVE_LOG_KEYS = {"authorization", "cookie", "password", "passwd", "secret", "token", "access_token", "refresh_token", "username", "email", "account"}


def execute_debug_request(payload: dict[str, Any]) -> dict[str, Any]:
    environment = _get_environment(payload.get("environment"))
    platform = payload.get("platform") or "ERP"
    module_id = payload.get("module")
    variables = _build_variables(environment, platform, payload.get("variables") or {})
    data_logs: list[str] = []
    session_logs: list[str] = []
    extracted_variables: dict[str, Any] = {}
    try:
        pre_source_ids = payload.get("pre_test_data_sources")
        if pre_source_ids is None:
            pre_source_ids = payload.get("test_data_sources") or []
        pre_logs, pre_variables = _apply_test_data_sources(pre_source_ids or [], variables, "pre")
        data_logs.extend(pre_logs)
        extracted_variables.update(pre_variables)
    except requests.RequestException as exc:
        error_fields = _request_error_fields(exc)
        return {
            "ok": False,
            "passed": False,
            "request": {"method": payload.get("method") or "GET", "url": payload.get("path") or payload.get("url") or "/"},
            "response": {"elapsed_ms": 0},
            "assertions": [],
            "variables": extracted_variables,
            "runtime_variables": _safe_variable_snapshot(variables),
            "logs": [*data_logs, *_request_error_logs(exc)],
            **error_fields,
        }
    method = (payload.get("method") or "GET").upper()
    if environment and not _is_method_allowed_by_environment(environment, method):
        message = f"当前环境不允许执行 {method} 请求，请联系管理员"
        return {
            "ok": False,
            "passed": False,
            "request": {"method": method, "url": payload.get("path") or payload.get("url") or "/"},
            "response": {"elapsed_ms": 0},
            "assertions": [],
            "variables": extracted_variables,
            "runtime_variables": _safe_variable_snapshot(variables),
            "logs": [*data_logs, message],
            "error": message,
        }
    path = payload.get("path") or payload.get("url") or "/"
    base_url = _get_base_url(environment, platform)
    url = _build_url(base_url, path)

    headers = _items_to_dict(payload.get("headers"), for_headers=True)
    params = _items_to_dict(payload.get("query_params") or payload.get("params"))
    body = payload.get("body")
    auth_config = payload.get("auth_config") or {}

    timeout = _safe_timeout(payload.get("timeout"))

    started = time.perf_counter()
    try:
        token_context, session_logs = _ensure_session_token(environment, platform, variables, module_id)
        if token_context:
            variables[token_context["token_key"]] = token_context["token"]
        headers = _apply_auth(headers, auth_config, variables)
        if token_context:
            headers = _inject_session_token(headers, token_context)
        url = _render_value(url, variables)
        headers = _render_value(headers, variables)
        params = _render_value(params, variables)
        body = _render_value(body, variables)

        _validate_outbound_request(method, url, headers)
        resp = requests.request(
            method=method,
            url=url,
            params=params,
            headers=headers,
            json=body if isinstance(body, (dict, list)) else None,
            data=body if isinstance(body, str) else None,
            timeout=timeout,
            allow_redirects=False,
            stream=True,
        )
        content = _read_limited_content(resp)
        resp._content = content
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        response_text = _decode_response_text(resp, content)
        response_body = _parse_response_body(resp, response_text)
        response_variables = _extract_response_variables(payload.get("extractors") or [], response_body)
        missing_extractors = _missing_response_extractors(payload.get("extractors") or [], response_body)
        if response_variables:
            variables.update(response_variables)
            extracted_variables.update(response_variables)
            data_logs.append(f"Response extractors captured {len(response_variables)} variable(s).")
        if missing_extractors:
            data_logs.append(f"Response extractors missed: {', '.join(missing_extractors)}.")
        post_logs, post_variables = _apply_test_data_sources(payload.get("post_test_data_sources") or [], variables, "post")
        data_logs.extend(post_logs)
        variables.update(post_variables)
        extracted_variables.update(post_variables)
        assertion_results = evaluate_assertions(payload.get("assertions") or [], resp, response_body, elapsed_ms)
        passed = all(item["passed"] for item in assertion_results)
        return {
            "ok": True,
            "passed": passed,
            "request": {
                "method": method,
                "url": resp.request.url,
                "headers": dict(resp.request.headers),
                "params": params,
                "body": body,
            },
            "response": {
                "status_code": resp.status_code,
                "reason": resp.reason,
                "elapsed_ms": elapsed_ms,
                "size": len(content),
                "headers": dict(resp.headers),
                "body": response_body,
                "text": response_text,
            },
            "assertions": assertion_results,
            "variables": extracted_variables,
            "runtime_variables": _safe_variable_snapshot(variables),
            "logs": [*data_logs, *session_logs, f"{method} {resp.request.url}", f"HTTP {resp.status_code} {elapsed_ms}ms"],
        }
    except requests.RequestException as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        error_fields = _request_error_fields(exc)
        logs = [*data_logs, *session_logs, *_request_error_logs(exc)]
        if _is_pre_request_error(exc):
            error_fields = {
                **error_fields,
                "error": PRE_REQUEST_FAILURE_MESSAGE,
                "error_type": "pre_request_error",
                "pre_request_error_detail": error_fields.get("error") or str(exc).strip(),
            }
            logs = [*data_logs, *session_logs, PRE_REQUEST_FAILURE_MESSAGE]
        return {
            "ok": False,
            "passed": False,
            "request": {"method": method, "url": url, "headers": headers, "params": params, "body": body},
            "response": {"elapsed_ms": elapsed_ms},
            "assertions": [],
            "variables": extracted_variables,
            "runtime_variables": _safe_variable_snapshot(variables),
            "logs": logs,
            **error_fields,
        }


def _request_error_fields(exc: requests.RequestException) -> dict[str, Any]:
    message, error_type = _request_error_message(exc)
    detail = str(exc).strip()
    fields: dict[str, Any] = {"error": message, "error_type": error_type}
    if settings.DEBUG and detail and detail != message:
        fields["error_detail"] = detail
    if error_type != "request_error":
        logger.warning("API debug outbound request failed: %s", detail or message, exc_info=exc)
    return fields


def _request_error_logs(exc: requests.RequestException) -> list[str]:
    message, _ = _request_error_message(exc)
    detail = str(exc).strip()
    if settings.DEBUG and detail and detail != message:
        return [message, f"调试信息：{detail}"]
    return [message]


def _request_error_message(exc: requests.RequestException) -> tuple[str, str]:
    if isinstance(exc, requests.exceptions.SSLError):
        return "目标服务 HTTPS 握手失败，请检查目标服务证书、TLS 配置、网络白名单或稍后重试。", "ssl_error"
    if isinstance(exc, requests.exceptions.ConnectTimeout):
        return "连接目标服务超时，请检查目标地址、网络连通性或稍后重试。", "connect_timeout"
    if isinstance(exc, requests.exceptions.ReadTimeout):
        return "目标服务响应超时，请检查接口耗时、超时时间配置或稍后重试。", "read_timeout"
    if isinstance(exc, requests.exceptions.Timeout):
        return "请求目标服务超时，请稍后重试。", "timeout"
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "无法连接目标服务，请检查目标地址、网络、DNS、证书或访问白名单。", "connection_error"
    if isinstance(exc, requests.exceptions.TooManyRedirects):
        return "目标服务重定向次数过多，请检查接口地址或重定向配置。", "too_many_redirects"
    return str(exc).strip() or "请求执行失败，请检查目标服务配置。", "request_error"


def _pre_request_exception(message: str) -> requests.RequestException:
    exc = requests.RequestException(message)
    setattr(exc, "is_pre_request_error", True)
    return exc


def _is_pre_request_error(exc: requests.RequestException) -> bool:
    return bool(getattr(exc, "is_pre_request_error", False))


def _apply_test_data_sources(source_ids: list[Any], variables: dict[str, Any], phase: str) -> tuple[list[str], dict[str, Any]]:
    logs: list[str] = []
    extracted: dict[str, Any] = {}
    ids: list[int] = []
    for item in source_ids:
        try:
            source_id = int(item)
        except (TypeError, ValueError):
            continue
        if source_id not in ids:
            ids.append(source_id)
    if not ids:
        return logs, extracted
    sources = {
        source.id: source
        for source in TestDataSource.objects.select_related("database_connection").filter(id__in=ids, is_active=True)
    }
    for source_id in ids:
        source = sources.get(source_id)
        if not source:
            continue
        try:
            result = execute_test_data_source(source, variables)
        except Exception as exc:
            raise requests.RequestException(f"Test data source [{source.name}] failed: {exc}") from exc
        source_variables = result.get("variables") or {}
        variables.update(source_variables)
        extracted.update(source_variables)
        logs.append(f"{phase} data source [{source.name}] extracted {len(source_variables)} variable(s).")
    return logs, extracted


def _extract_response_variables(extractors: list[dict[str, Any]], response_body: Any) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for extractor in extractors:
        name = str(extractor.get("name") or "").strip()
        path = str(extractor.get("path") or extractor.get("key") or "").strip()
        if not name or not path:
            continue
        if not re.match(r"^[a-zA-Z0-9_.-]+$", name):
            continue
        matched, value = _json_path_match(response_body, path)
        if matched:
            values[name] = value
    return values


def _missing_response_extractors(extractors: list[dict[str, Any]], response_body: Any) -> list[str]:
    missed: list[str] = []
    for extractor in extractors:
        name = str(extractor.get("name") or "").strip()
        path = str(extractor.get("path") or extractor.get("key") or "").strip()
        if not name or not path:
            continue
        if not re.match(r"^[a-zA-Z0-9_.-]+$", name):
            continue
        matched, _ = _json_path_match(response_body, path)
        if not matched:
            missed.append(name)
    return missed


def _safe_variable_snapshot(variables: dict[str, Any]) -> dict[str, Any]:
    try:
        json.dumps(variables, ensure_ascii=False)
        return dict(variables)
    except TypeError:
        return json.loads(json.dumps(variables, ensure_ascii=False, default=str))


def evaluate_assertions(assertions: list[dict[str, Any]], resp, response_body: Any, elapsed_ms: int) -> list[dict[str, Any]]:
    results = []
    for assertion in assertions:
        actual = _resolve_actual(assertion, resp, response_body, elapsed_ms)
        expected = assertion.get("expected")
        operator = assertion.get("operator") or assertion.get("op") or "eq"
        passed = _compare(actual, expected, operator)
        results.append(
            {
                "name": assertion.get("name") or assertion.get("type") or "assertion",
                "type": assertion.get("type") or "custom",
                "operator": operator,
                "expected": expected,
                "actual": actual,
                "passed": passed,
                "message": "" if passed else f"expected {expected}, actual {actual}",
            }
        )
    return results


def _get_environment(environment_id):
    if not environment_id:
        return None
    try:
        return Environment.objects.get(pk=environment_id)
    except Environment.DoesNotExist:
        return None


def _is_method_allowed_by_environment(environment, method: str) -> bool:
    allowed_methods = _get_environment_allowed_methods(environment.id)
    if allowed_methods is None:
        return True
    return method.upper() in allowed_methods


def _get_environment_allowed_methods(environment_id: int) -> frozenset[str] | None:
    now = time.monotonic()
    cached = _REQUEST_CONTROL_METHOD_CACHE.get(environment_id)
    if cached and now - cached[0] < REQUEST_CONTROL_CACHE_SECONDS:
        return cached[1]
    controls = Environment.objects.filter(pk=environment_id).values_list("request_controls__methods", "request_controls__is_enabled")
    allowed: set[str] = set()
    has_enabled_control = False
    for methods, is_enabled in controls:
        if not is_enabled:
            continue
        has_enabled_control = True
        allowed.update(str(item).upper() for item in methods or [])
    value = frozenset(allowed) if has_enabled_control else None
    _REQUEST_CONTROL_METHOD_CACHE[environment_id] = (now, value)
    return value


def clear_environment_request_control_cache(environment_id: int | None = None) -> None:
    if environment_id is None:
        _REQUEST_CONTROL_METHOD_CACHE.clear()
        return
    _REQUEST_CONTROL_METHOD_CACHE.pop(environment_id, None)


def run_pre_request_operation(operation, platform: str | None = None, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    environment = operation.environment
    config = operation.config or {}
    if not isinstance(config, dict):
        return _pre_request_run_result(False, operation, platform or "", ["前置操作配置必须是对象"], "前置操作配置必须是对象")

    run_platform = _resolve_pre_request_run_platform(operation, platform, config)
    run_variables = _build_variables(environment, run_platform, variables or {})
    logs: list[str] = []

    target_platform = config.get("platform")
    if target_platform and str(target_platform).lower() != str(run_platform or "").lower():
        message = f"配置限定平台为 {target_platform}，当前试运行平台为 {run_platform or '未指定'}"
        return _pre_request_run_result(False, operation, run_platform, logs, message)

    login_config = config.get("login") or {}
    if not login_config.get("path") and not login_config.get("url"):
        message = "未配置登录请求，无法试运行 token 初始化"
        return _pre_request_run_result(False, operation, run_platform, logs, message)

    try:
        login_resp, login_body = _send_configured_request(environment, run_platform, login_config, run_variables)
        success_rule = login_config.get("success") or {"type": "status_code", "operator": "lt", "expected": 400}
        login_success = _match_success_rule(success_rule, login_resp, login_body, 0)
        logs.append(f"登录接口返回 Body：{_safe_log_text(login_body)}")
        if not login_success:
            message = f"{operation.name}登录失败：HTTP {login_resp.status_code}"
            return _pre_request_run_result(False, operation, run_platform, logs, message, login_resp.status_code)

        token_path = login_config.get("token_path") or "$.data.token"
        token = _json_path(login_body, token_path)
        if token is None:
            message = f"{operation.name}未从响应中提取到 token：{token_path}"
            return _pre_request_run_result(False, operation, run_platform, logs, message, login_resp.status_code)

        token_key = config.get("token_key") or "token"
        token_context = _build_token_context(str(token), token_key, config)
        logs.append(f"Token 提取成功：{token_path} -> {token_key}")

        validate_config = config.get("validate") or {}
        if validate_config.get("enabled") is False or (not validate_config.get("path") and not validate_config.get("url")):
            return _pre_request_run_result(True, operation, run_platform, logs, "")

        token_variables = {**run_variables, token_context["token_key"]: token_context["token"]}
        validate_resp, validate_body = _send_configured_request(environment, run_platform, validate_config, token_variables, token_context)
        validate_rule = validate_config.get("success") or {"type": "status_code", "operator": "lt", "expected": 400}
        validate_success = _match_success_rule(validate_rule, validate_resp, validate_body, 0)
        logs.append(f"校验接口返回 Body：{_safe_log_text(validate_body)}")
        if not validate_success:
            message = f"{operation.name}校验失败：HTTP {validate_resp.status_code}"
            return _pre_request_run_result(False, operation, run_platform, logs, message, validate_resp.status_code)
        return _pre_request_run_result(True, operation, run_platform, logs, "")
    except requests.RequestException as exc:
        message, error_type = _request_error_message(exc)
        detail = str(exc).strip()
        if detail and detail != message:
            logs.append(f"异常返回 Body：{_safe_log_text(detail)}")
        result = _pre_request_run_result(False, operation, run_platform, logs, message)
        result["error_type"] = error_type
        return result


def _resolve_pre_request_run_platform(operation, platform: str | None, config: dict[str, Any]) -> str:
    if platform:
        return str(platform).upper()
    if config.get("platform"):
        return str(config["platform"]).upper()
    if operation.platforms:
        return str(operation.platforms[0]).upper()
    module = operation.modules.first()
    if module and module.platform:
        return str(module.platform).upper()
    project_platforms = operation.environment.project.platforms or []
    if project_platforms:
        return str(project_platforms[0]).upper()
    platform_urls = operation.environment.platform_base_urls or {}
    if platform_urls:
        return str(next(iter(platform_urls.keys()))).upper()
    return "ERP"


def _pre_request_run_result(ok: bool, operation, platform: str, logs: list[str], error: str, status_code: int | None = None) -> dict[str, Any]:
    return {
        "ok": ok,
        "operation": {"id": operation.id, "name": operation.name},
        "environment": {"id": operation.environment_id, "name": operation.environment.name},
        "platform": platform,
        "status_code": status_code,
        "error": error,
        "logs": logs,
        "ran_at": timezone.now().isoformat(),
    }


def _configured_request_preview(environment, platform: str, request_config: dict[str, Any], variables: dict[str, Any], token_context: dict[str, Any] | None = None) -> str:
    method = (request_config.get("method") or "GET").upper()
    path = request_config.get("path") or request_config.get("url") or "/"
    url = _render_value(_build_url(_get_base_url(environment, platform), path), variables)
    headers = _render_value(_items_to_dict(request_config.get("headers"), for_headers=True), variables)
    if token_context:
        headers = _inject_session_token(headers, token_context)
    params = _render_value(_items_to_dict(request_config.get("query_params") or request_config.get("params")), variables)
    body = _render_value(request_config.get("body"), variables)
    parts = [f"{method} {_mask_url_for_log(url)}"]
    if params:
        parts.append(f"Params={_safe_log_text(params)}")
    if headers:
        parts.append(f"Headers={_safe_log_text(headers)}")
    if body not in (None, "", {}, []):
        parts.append(f"Body={_safe_log_text(body)}")
    return "；".join(parts)


def _safe_log_text(value: Any, max_length: int = 2000) -> str:
    try:
        text = json.dumps(_mask_sensitive_log_value(value), ensure_ascii=False, default=str)
    except TypeError:
        text = str(value)
    if len(text) > max_length:
        return f"{text[:max_length]}...（已截断）"
    return text


def _mask_url_for_log(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme}://***{path}{query}"


def _mask_sensitive_log_value(value: Any) -> Any:
    if isinstance(value, dict):
        masked = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if any(sensitive in normalized for sensitive in SENSITIVE_LOG_KEYS):
                masked[key] = "***"
            else:
                masked[key] = _mask_sensitive_log_value(item)
        return masked
    if isinstance(value, list):
        return [_mask_sensitive_log_value(item) for item in value]
    return value


def _build_variables(environment, platform: str, extra: dict[str, Any]) -> dict[str, Any]:
    variables: dict[str, Any] = {}
    if environment:
        variables.update(environment.variables or {})
        variables.update(environment.secret_variables or {})
        items = list(environment.variable_items.filter(is_enabled=True))
        for item in items:
            if not item.platform:
                variables[item.key] = item.value
        platform_key = (platform or "").lower()
        for item in items:
            if item.platform and item.platform.lower() == platform_key:
                variables[item.key] = item.value
    variables.update(extra)
    return variables


def _get_base_url(environment, platform: str) -> str:
    if not environment:
        return ""
    platform_urls = environment.platform_base_urls or {}
    return platform_urls.get(platform) or platform_urls.get(platform.lower()) or environment.base_url or ""


def _build_url(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not base_url:
        return path
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def _items_to_dict(items, for_headers: bool = False) -> dict[str, Any]:
    if isinstance(items, dict):
        return {str(k).strip(): v for k, v in items.items() if _is_safe_item_name(str(k), for_headers)}
    result = {}
    for item in items or []:
        if not item or item.get("enabled") is False:
            continue
        key = item.get("key") or item.get("name")
        if key and _is_safe_item_name(str(key), for_headers):
            result[key] = item.get("value", "")
    return result


def _apply_auth(headers: dict[str, Any], auth_config: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    auth_type = (auth_config.get("type") or "none").lower()
    if auth_type == "bearer":
        token = _render_value(auth_config.get("token") or "", variables)
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "basic":
        username = _render_value(auth_config.get("username") or "", variables)
        password = _render_value(auth_config.get("password") or "", variables)
        raw = f"{username}:{password}".encode()
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode()
    elif auth_type == "api_key":
        key = auth_config.get("key") or "X-API-Key"
        value = _render_value(auth_config.get("value") or "", variables)
        if value:
            headers[key] = value
    return headers


def _ensure_session_token(environment, platform: str, variables: dict[str, Any], module_id: Any = None) -> tuple[dict[str, Any] | None, list[str]]:
    operation = _match_pre_request_operation(environment, platform, module_id) if environment else None
    if operation:
        return _ensure_token_from_config(environment, platform, variables, operation.config or {}, operation_key=f"operation:{operation.id}", operation_name=operation.name)
    if not environment or not environment.pre_request_enabled:
        return None, []

    config = environment.pre_request_config or {}
    return _ensure_token_from_config(environment, platform, variables, config, operation_key="legacy", operation_name="全局前置操作")


def _match_pre_request_operation(environment, platform: str, module_id: Any = None):
    if not environment:
        return None
    platform_key = str(platform or "").upper()
    try:
        module_pk = int(module_id) if module_id not in (None, "") else None
    except (TypeError, ValueError):
        module_pk = None
    operations = environment.pre_request_operations.filter(is_enabled=True).prefetch_related("modules").order_by("sort_order", "id")
    module_match = None
    platform_match = None
    for operation in operations:
        operation_modules = list(operation.modules.all())
        if module_pk and any(item.id == module_pk for item in operation_modules):
            module_match = operation
            break
        operation_platforms = {str(item).upper() for item in operation.platforms or []}
        if platform_key and platform_key in operation_platforms:
            platform_match = operation
    return module_match or platform_match


def _ensure_token_from_config(
    environment,
    platform: str,
    variables: dict[str, Any],
    config: dict[str, Any],
    operation_key: str,
    operation_name: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    if not isinstance(config, dict):
        raise _pre_request_exception("全局前置操作配置必须是对象")

    target_platform = config.get("platform")
    if target_platform and str(target_platform).lower() != str(platform or "").lower():
        return None, []

    token_key = config.get("token_key") or "token"
    configured_session_key = str(config.get("session_key") or platform or "default").upper()
    session_key = f"{operation_key}:{configured_session_key}"
    session_store = environment.token_session or {}
    session = session_store.get(session_key) or {}
    token = session.get("token")
    logs: list[str] = []

    token_context = _build_token_context(token, token_key, config)
    if token and _validate_session_token(environment, platform, config, variables, token_context):
        session["validated_at"] = timezone.now().isoformat()
        session_store[session_key] = session
        environment.token_session = session_store
        environment.save(update_fields=["token_session", "updated_at"])
        return token_context, [f"{operation_name}：复用会话 token"]

    login_config = config.get("login") or {}
    if not login_config.get("path") and not login_config.get("url"):
        return None, [f"{operation_name}：未配置登录请求，已跳过 token 初始化"]

    login_resp, login_body = _send_configured_request(environment, platform, login_config, variables)
    success_rule = login_config.get("success") or {"type": "status_code", "operator": "lt", "expected": 400}
    if not _match_success_rule(success_rule, login_resp, login_body, 0):
        raise _pre_request_exception(f"{operation_name}登录失败：HTTP {login_resp.status_code}")

    token_path = login_config.get("token_path") or "$.data.token"
    token = _json_path(login_body, token_path)
    if token is None:
        raise _pre_request_exception(f"{operation_name}未从响应中提取到 token：{token_path}")

    token = str(token)
    token_context = _build_token_context(token, token_key, config)
    session_store[session_key] = {
        "token": token,
        "token_key": token_key,
        "created_at": timezone.now().isoformat(),
        "validated_at": None,
    }
    environment.token_session = session_store
    environment.save(update_fields=["token_session", "updated_at"])
    logs.append(f"{operation_name}：已初始化会话 token")
    return token_context, logs


def _build_token_context(token: str | None, token_key: str, config: dict[str, Any]) -> dict[str, Any]:
    inject_config = config.get("inject") or {}
    return {
        "token": token or "",
        "token_key": token_key,
        "inject_enabled": inject_config.get("enabled", True),
        "header": inject_config.get("header") or "Authorization",
        "prefix": inject_config.get("prefix", "Bearer "),
    }


def _validate_session_token(environment, platform: str, config: dict[str, Any], variables: dict[str, Any], token_context: dict[str, Any]) -> bool:
    validate_config = config.get("validate") or {}
    if validate_config.get("enabled") is False:
        return True
    if not validate_config.get("path") and not validate_config.get("url"):
        return True
    try:
        token_variables = {**variables, token_context["token_key"]: token_context["token"]}
        resp, response_body = _send_configured_request(environment, platform, validate_config, token_variables, token_context)
        success_rule = validate_config.get("success") or {"type": "status_code", "operator": "lt", "expected": 400}
        return _match_success_rule(success_rule, resp, response_body, 0)
    except requests.RequestException:
        return False


def _send_configured_request(
    environment,
    platform: str,
    request_config: dict[str, Any],
    variables: dict[str, Any],
    token_context: dict[str, Any] | None = None,
):
    method = (request_config.get("method") or "GET").upper()
    base_url = _get_base_url(environment, platform)
    path = request_config.get("path") or request_config.get("url") or "/"
    url = _render_value(_build_url(base_url, path), variables)
    headers = _render_value(_items_to_dict(request_config.get("headers"), for_headers=True), variables)
    params = _render_value(_items_to_dict(request_config.get("query_params") or request_config.get("params")), variables)
    body = _render_value(request_config.get("body"), variables)
    if token_context:
        headers = _inject_session_token(headers, token_context)

    _validate_outbound_request(method, url, headers)
    resp = requests.request(
        method=method,
        url=url,
        params=params,
        headers=headers,
        json=body if isinstance(body, (dict, list)) else None,
        data=body if isinstance(body, str) else None,
        timeout=_safe_timeout(request_config.get("timeout")),
        allow_redirects=False,
        stream=True,
    )
    content = _read_limited_content(resp)
    resp._content = content
    response_text = _decode_response_text(resp, content)
    return resp, _parse_response_body(resp, response_text)


def _inject_session_token(headers: dict[str, Any], token_context: dict[str, Any]) -> dict[str, Any]:
    if not token_context.get("inject_enabled") or not token_context.get("token"):
        return headers
    header = token_context.get("header") or "Authorization"
    if any(str(key).lower() == str(header).lower() for key in headers):
        return headers
    headers[header] = f"{token_context.get('prefix', '')}{token_context['token']}"
    return headers


def _match_success_rule(rule: dict[str, Any], resp, response_body: Any, elapsed_ms: int) -> bool:
    rule_type = rule.get("type") or "status_code"
    actual = resp.status_code if rule_type == "status_code" else _resolve_actual(rule, resp, response_body, elapsed_ms)
    return _compare(actual, rule.get("expected", 400), rule.get("operator") or "lt")


def _render_value(value, variables: dict[str, Any]):
    if isinstance(value, str):
        # 单独占位的变量保留原始类型，避免数字、布尔值在请求体中被转成字符串。
        exact_match = EXACT_VAR_PATTERN.match(value)
        if exact_match and exact_match.group(1) in variables:
            return variables[exact_match.group(1)]
        return VAR_PATTERN.sub(lambda match: str(variables.get(match.group(1), match.group(0))), value)
    if isinstance(value, list):
        return [_render_value(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: _render_value(val, variables) for key, val in value.items()}
    return value


def _safe_timeout(value) -> int:
    try:
        timeout = int(value or settings.API_DEBUG_MAX_TIMEOUT_SECONDS)
    except (TypeError, ValueError):
        timeout = settings.API_DEBUG_MAX_TIMEOUT_SECONDS
    return max(1, min(timeout, settings.API_DEBUG_MAX_TIMEOUT_SECONDS))


def _validate_outbound_request(method: str, url: str, headers: dict[str, Any]) -> None:
    if method not in ALLOWED_METHODS:
        raise requests.RequestException("不支持的请求方法")

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise requests.RequestException("仅允许 http/https URL")

    _validate_target_host(parsed.hostname)
    for key, value in headers.items():
        if not _is_safe_header_name(str(key)):
            raise requests.RequestException(f"不允许的请求 Header: {key}")
        if "\r" in str(value) or "\n" in str(value):
            raise requests.RequestException(f"Header 值包含非法换行: {key}")


def _validate_target_host(hostname: str) -> None:
    if settings.API_DEBUG_ALLOW_PRIVATE_NETWORK:
        return

    try:
        candidates = [ipaddress.ip_address(hostname)]
    except ValueError:
        try:
            infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise requests.RequestException(f"无法解析目标主机: {hostname}") from exc
        candidates = [ipaddress.ip_address(info[4][0]) for info in infos]

    for address in candidates:
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise requests.RequestException("出于安全原因，默认禁止调试请求访问内网、localhost 或保留地址")


def _is_safe_header_name(key: str) -> bool:
    normalized = key.strip().lower()
    if not normalized or normalized in BLOCKED_REQUEST_HEADERS:
        return False
    return "\r" not in normalized and "\n" not in normalized


def _is_safe_item_name(key: str, for_headers: bool) -> bool:
    if for_headers:
        return _is_safe_header_name(key)
    return bool(key.strip()) and "\r" not in key and "\n" not in key


def _read_limited_content(resp) -> bytes:
    max_bytes = settings.API_DEBUG_MAX_RESPONSE_BYTES
    chunks = []
    size = 0
    for chunk in resp.iter_content(chunk_size=8192):
        if not chunk:
            continue
        size += len(chunk)
        if size > max_bytes:
            raise requests.RequestException(f"响应体超过限制：{max_bytes} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


def _decode_response_text(resp, content: bytes) -> str:
    encoding = resp.encoding or resp.apparent_encoding or "utf-8"
    return content.decode(encoding, errors="replace")


def _parse_response_body(resp, response_text: str):
    content_type = resp.headers.get("content-type", "")
    if "json" in content_type.lower():
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return response_text
    return response_text


def _resolve_actual(assertion: dict[str, Any], resp, response_body: Any, elapsed_ms: int):
    assertion_type = assertion.get("type")
    if assertion_type == "status_code":
        return resp.status_code
    if assertion_type == "response_time":
        return elapsed_ms
    if assertion_type == "header":
        return resp.headers.get(assertion.get("key") or "")
    if assertion_type == "json_path":
        return _json_path(response_body, assertion.get("path") or assertion.get("key") or "")
    if assertion_type == "body_contains":
        return resp.text
    return None


def _json_path(data: Any, path: str):
    if not path:
        return data
    current = data
    for part in _json_path_parts(path):
        if isinstance(current, dict) and isinstance(part, str):
            current = current.get(part)
        elif isinstance(current, list) and isinstance(part, int):
            if part < 0 or part >= len(current):
                return None
            current = current[part]
        else:
            return None
    return current


def _json_path_match(data: Any, path: str) -> tuple[bool, Any]:
    if not path:
        return True, data
    current = data
    for part in _json_path_parts(path):
        if isinstance(current, dict) and isinstance(part, str):
            if part not in current:
                return False, None
            current = current.get(part)
        elif isinstance(current, list) and isinstance(part, int):
            if part < 0 or part >= len(current):
                return False, None
            current = current[part]
        else:
            return False, None
    return True, current


def _json_path_parts(path: str) -> list[str | int]:
    parts: list[str | int] = []
    normalized = path.strip().removeprefix("$").removeprefix(".")
    for segment in normalized.split("."):
        if not segment:
            continue
        cursor = 0
        for match in re.finditer(r"([^\[\]]+)|\[(\d+)\]", segment):
            if match.start() != cursor:
                return [segment]
            if match.group(1) is not None:
                parts.append(match.group(1))
            else:
                parts.append(int(match.group(2)))
            cursor = match.end()
        if cursor != len(segment):
            return [segment]
    return parts


def _compare(actual, expected, operator: str) -> bool:
    if operator in ("eq", "=", "=="):
        return str(actual) == str(expected)
    if operator in ("ne", "!=", "not_eq"):
        return str(actual) != str(expected)
    if operator in ("contains", "include"):
        return str(expected) in str(actual)
    if operator in ("exists",):
        return actual is not None
    if operator in ("lt", "<"):
        return float(actual) < float(expected)
    if operator in ("gt", ">"):
        return float(actual) > float(expected)
    return False
