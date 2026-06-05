import base64
import ipaddress
import json
import re
import socket
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings
from django.utils import timezone

from apps.projects.models import Environment


VAR_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_.-]+)\s*}}")
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
BLOCKED_REQUEST_HEADERS = {
    "host",
    "content-length",
    "connection",
    "proxy-authorization",
    "proxy-authenticate",
    "transfer-encoding",
    "upgrade",
}


def execute_debug_request(payload: dict[str, Any]) -> dict[str, Any]:
    environment = _get_environment(payload.get("environment"))
    platform = payload.get("platform") or "ERP"
    variables = _build_variables(environment, platform, payload.get("variables") or {})
    pre_request_logs: list[str] = []
    method = (payload.get("method") or "GET").upper()
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
        token_context, pre_request_logs = _ensure_session_token(environment, platform, variables)
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
        assertion_results = evaluate_assertions(payload.get("assertions") or [], resp, response_body, elapsed_ms)
        passed = all(item["passed"] for item in assertion_results)
        return {
            "ok": True,
            "passed": passed,
            "request": {"method": method, "url": resp.request.url, "headers": dict(resp.request.headers)},
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
            "logs": [*pre_request_logs, f"{method} {resp.request.url}", f"HTTP {resp.status_code} {elapsed_ms}ms"],
        }
    except requests.RequestException as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": False,
            "passed": False,
            "request": {"method": method, "url": url, "headers": headers, "params": params, "body": body},
            "response": {"elapsed_ms": elapsed_ms},
            "assertions": [],
            "logs": [*pre_request_logs, str(exc)],
            "error": str(exc),
        }


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


def _ensure_session_token(environment, platform: str, variables: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    if not environment or not environment.pre_request_enabled:
        return None, []

    config = environment.pre_request_config or {}
    if not isinstance(config, dict):
        raise requests.RequestException("全局前置操作配置必须是对象")

    target_platform = config.get("platform")
    if target_platform and str(target_platform).lower() != str(platform or "").lower():
        return None, []

    token_key = config.get("token_key") or "token"
    session_key = str(config.get("session_key") or platform or "default").upper()
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
        return token_context, ["全局前置操作：复用会话 token"]

    login_config = config.get("login") or {}
    if not login_config.get("path") and not login_config.get("url"):
        return None, ["全局前置操作：未配置登录请求，已跳过 token 初始化"]

    login_resp, login_body = _send_configured_request(environment, platform, login_config, variables)
    success_rule = login_config.get("success") or {"type": "status_code", "operator": "lt", "expected": 400}
    if not _match_success_rule(success_rule, login_resp, login_body, 0):
        raise requests.RequestException(f"全局前置操作登录失败：HTTP {login_resp.status_code}")

    token_path = login_config.get("token_path") or "$.data.token"
    token = _json_path(login_body, token_path)
    if token is None:
        raise requests.RequestException(f"全局前置操作未从响应中提取到 token：{token_path}")

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
    logs.append("全局前置操作：已初始化会话 token")
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
    for part in path.removeprefix("$.").split("."):
        if part == "":
            continue
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            return None
    return current


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
