import base64
import time
from typing import Any

from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


DEFAULT_TIMEOUT_MS = 30000
DEFAULT_NAVIGATION_TIMEOUT_MS = 45000
DEFAULT_GOTO_WAIT_UNTIL = "commit"
MAX_STEPS = 80
LOCAL_CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def run_ui_case(case, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    browser_name = payload.get("browser") or case.browser or "chromium"
    headless = bool(payload.get("headless", True))
    timeout_ms = _safe_timeout_ms(payload.get("timeout_ms"), DEFAULT_TIMEOUT_MS)
    navigation_timeout_ms = _safe_timeout_ms(payload.get("navigation_timeout_ms"), max(timeout_ms, DEFAULT_NAVIGATION_TIMEOUT_MS))
    wait_until = payload.get("wait_until") or DEFAULT_GOTO_WAIT_UNTIL
    viewport = payload.get("viewport") or {"width": 1366, "height": 768}
    capture_screenshots = bool(payload.get("capture_screenshots", True))
    steps = list(case.steps or [])[:MAX_STEPS]
    results: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    console_errors: list[dict[str, Any]] = []
    network_errors: list[dict[str, Any]] = []

    started = time.perf_counter()
    try:
        with sync_playwright() as p:
            browser_type = getattr(p, browser_name)
            browser = _launch_browser(p, browser_type, browser_name, headless)
            context = browser.new_context(viewport=viewport)
            page = context.new_page()
            _attach_diagnostics(page, console_errors, network_errors)
            page.set_default_timeout(timeout_ms)
            page.set_default_navigation_timeout(navigation_timeout_ms)

            if case.start_url:
                page.goto(case.start_url, wait_until=wait_until)
                if capture_screenshots:
                    snapshots.append(_capture_snapshot(page, 0, "初始页面", True))

            for index, step in enumerate(steps, start=1):
                result = _run_step(page, step, index, wait_until, capture_screenshots)
                result["diagnostics"] = _diagnostics_delta(result, console_errors, network_errors)
                results.append(result)
                if result.get("screenshot"):
                    snapshots.append(
                        {
                            "order": result["order"],
                            "name": result["name"],
                            "passed": result["passed"],
                            "url": result.get("url", ""),
                            "screenshot": result["screenshot"],
                        }
                    )
                if not result["passed"]:
                    break

            context.close()
            browser.close()
    except Exception as exc:
        return {
            "ok": False,
            "passed": False,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "browser": browser_name,
            "headless": headless,
            "results": results,
            "snapshots": snapshots,
            "diagnostics": {
                "console_errors": console_errors[-20:],
                "network_errors": network_errors[-20:],
            },
            "error": _friendly_error(exc),
        }

    passed = all(item["passed"] for item in results) and len(results) == len(steps)
    return {
        "ok": True,
        "passed": passed,
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "browser": browser_name,
        "headless": headless,
        "results": results,
        "snapshots": snapshots,
        "diagnostics": {
            "console_errors": console_errors[-20:],
            "network_errors": network_errors[-20:],
        },
        "error": "",
    }


def validate_ui_element(element, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    url = payload.get("url") or payload.get("start_url") or ""
    browser_name = payload.get("browser") or "chromium"
    headless = bool(payload.get("headless", True))
    timeout_ms = _safe_timeout_ms(payload.get("timeout_ms"), DEFAULT_TIMEOUT_MS)
    wait_until = payload.get("wait_until") or DEFAULT_GOTO_WAIT_UNTIL
    viewport = payload.get("viewport") or {"width": 1366, "height": 768}
    console_errors: list[dict[str, Any]] = []
    network_errors: list[dict[str, Any]] = []
    started = time.perf_counter()

    if not url:
        return {
            "ok": False,
            "passed": False,
            "duration_ms": 0,
            "error": "请填写待验证页面 URL",
            "suggestions": ["可使用用例起始地址或页面完整地址验证定位器。"],
        }

    try:
        with sync_playwright() as p:
            browser_type = getattr(p, browser_name)
            browser = _launch_browser(p, browser_type, browser_name, headless)
            context = browser.new_context(viewport=viewport)
            page = context.new_page()
            _attach_diagnostics(page, console_errors, network_errors)
            page.set_default_timeout(timeout_ms)
            page.goto(url, wait_until=wait_until)

            locator = _build_locator(page, element.selector, element.locator_type)
            count = locator.count()
            visible_count = 0
            first_text = ""
            if count:
                sample_count = min(count, 5)
                for index in range(sample_count):
                    item = locator.nth(index)
                    if item.is_visible():
                        visible_count += 1
                        if not first_text:
                            try:
                                first_text = item.inner_text(timeout=1000)[:200]
                            except PlaywrightError:
                                first_text = ""
            screenshot = _capture_snapshot(page, 0, element.name, visible_count > 0).get("screenshot", "")
            final_url = page.url
            context.close()
            browser.close()
    except Exception as exc:
        return {
            "ok": False,
            "passed": False,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "error": _friendly_error(exc),
            "diagnostics": {"console_errors": console_errors[-20:], "network_errors": network_errors[-20:]},
            "suggestions": _locator_suggestions(element),
        }

    passed = count > 0 and visible_count > 0
    return {
        "ok": True,
        "passed": passed,
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "url": final_url,
        "selector": element.selector,
        "locator_type": element.locator_type,
        "match_count": count,
        "visible_count": visible_count,
        "sample_text": first_text,
        "screenshot": screenshot,
        "diagnostics": {"console_errors": console_errors[-20:], "network_errors": network_errors[-20:]},
        "suggestions": [] if passed else _locator_suggestions(element),
    }


def _run_step(
    page,
    step: dict[str, Any],
    index: int,
    wait_until: str = DEFAULT_GOTO_WAIT_UNTIL,
    capture_screenshot: bool = True,
) -> dict[str, Any]:
    action = step.get("action") or "click"
    selector = _normalize_selector(step.get("selector") or "")
    value = step.get("value") or ""
    expected = step.get("expected") or value
    name = step.get("name") or action
    started = time.perf_counter()
    try:
        if action == "goto":
            page.goto(value, wait_until=wait_until)
        elif action == "click":
            _build_locator(page, selector, step.get("locator_type")).click()
        elif action == "fill":
            _build_locator(page, selector, step.get("locator_type")).fill(value)
        elif action == "press":
            _build_locator(page, selector or "body", step.get("locator_type")).press(value)
        elif action == "select":
            _build_locator(page, selector, step.get("locator_type")).select_option(value)
        elif action == "check":
            _build_locator(page, selector, step.get("locator_type")).check()
        elif action == "uncheck":
            _build_locator(page, selector, step.get("locator_type")).uncheck()
        elif action == "wait":
            page.wait_for_timeout(int(value or 1000))
        elif action == "assert_visible":
            _build_locator(page, selector, step.get("locator_type")).wait_for(state="visible")
        elif action == "assert_text":
            text = _build_locator(page, selector, step.get("locator_type")).inner_text()
            if expected not in text:
                raise AssertionError(f"expected text contains {expected}, actual {text}")
        elif action == "assert_url":
            if expected not in page.url:
                raise AssertionError(f"expected url contains {expected}, actual {page.url}")
        elif action == "screenshot":
            page.screenshot(full_page=True)
        else:
            raise ValueError(f"unsupported action: {action}")
        result = {
            "order": index,
            "name": name,
            "action": action,
            "selector": selector,
            "passed": True,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "message": "",
            "url": page.url,
        }
        if capture_screenshot:
            result.update(_capture_snapshot(page, index, name, True))
        return result
    except (AssertionError, ValueError, PlaywrightTimeoutError, PlaywrightError) as exc:
        result = {
            "order": index,
            "name": name,
            "action": action,
            "selector": selector,
            "passed": False,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "message": str(exc),
            "url": page.url,
        }
        if capture_screenshot:
            result.update(_capture_snapshot(page, index, name, False))
        return result


def _capture_snapshot(page, order: int, name: str, passed: bool) -> dict[str, Any]:
    try:
        image = page.screenshot(type="jpeg", quality=72, full_page=False)
        screenshot = f"data:image/jpeg;base64,{base64.b64encode(image).decode('ascii')}"
    except PlaywrightError:
        screenshot = ""
    return {
        "order": order,
        "name": name,
        "passed": passed,
        "url": page.url,
        "screenshot": screenshot,
    }


def _normalize_selector(selector: str) -> str:
    value = selector.strip()
    if value.startswith("/") or value.startswith("("):
        return f"xpath={value}"
    return value


def _build_locator(page, selector: str, locator_type: str | None = None):
    value = selector.strip()
    kind = (locator_type or "").lower()
    if kind == "text":
        return page.get_by_text(value)
    if kind == "role":
        role, _, name = value.partition("=")
        return page.get_by_role(role.strip() or value, name=name.strip() or None)
    if kind == "test_id":
        return page.get_by_test_id(value)
    if kind == "xpath":
        return page.locator(value if value.startswith("xpath=") else f"xpath={value}")
    return page.locator(_normalize_selector(value))


def _attach_diagnostics(page, console_errors: list[dict[str, Any]], network_errors: list[dict[str, Any]]) -> None:
    page.on(
        "console",
        lambda msg: console_errors.append({"type": msg.type, "text": msg.text, "url": page.url})
        if msg.type in {"error", "warning"}
        else None,
    )
    page.on(
        "requestfailed",
        lambda request: network_errors.append(
            {
                "url": request.url,
                "method": request.method,
                "failure": request.failure or "",
            }
        ),
    )
    page.on(
        "response",
        lambda resp: network_errors.append({"url": resp.url, "status": resp.status, "status_text": resp.status_text})
        if resp.status >= 400
        else None,
    )


def _diagnostics_delta(result: dict[str, Any], console_errors: list[dict[str, Any]], network_errors: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "console_error_count": len(console_errors),
        "network_error_count": len(network_errors),
        "failed": 0 if result.get("passed") else 1,
    }


def _locator_suggestions(element) -> list[str]:
    suggestions = [
        "优先使用 data-testid 或稳定业务属性，减少 CSS 层级变化带来的失效。",
        "如果元素是按钮/输入框，可尝试 Role、Text 或 TestId 定位方式。",
    ]
    if element.locator_type == "css" and ">" in element.selector:
        suggestions.insert(0, "当前 CSS 层级较深，建议改为更稳定的 class、name、aria-label 或 data-testid。")
    if element.locator_type == "xpath":
        suggestions.insert(0, "XPath 对页面结构变化较敏感，建议优先替换为 CSS、Role 或 TestId。")
    return suggestions


def _friendly_error(exc: Exception) -> str:
    message = str(exc)
    if "Executable doesn't exist" in message or "playwright install" in message:
        return "Playwright 浏览器未安装，且未找到本机 Chrome。请安装 Chrome 或执行：python -m playwright install chromium"
    return message


def _safe_timeout_ms(value: Any, default: int) -> int:
    try:
        timeout = int(value or default)
    except (TypeError, ValueError):
        timeout = default
    return max(1000, min(timeout, 180000))


def _launch_browser(playwright, browser_type, browser_name: str, headless: bool):
    try:
        return browser_type.launch(headless=headless)
    except PlaywrightError as exc:
        if not _is_missing_browser(exc):
            raise
        chrome_path = _local_chrome_path()
        if not chrome_path:
            raise
        return playwright.chromium.launch(executable_path=chrome_path, headless=headless)


def _is_missing_browser(exc: Exception) -> bool:
    message = str(exc)
    return "Executable doesn't exist" in message or "playwright install" in message


def _local_chrome_path() -> str:
    for path in LOCAL_CHROME_PATHS:
        if Path(path).exists():
            return path
    return ""
