from __future__ import annotations

import csv
import glob
import os
import shutil
import subprocess
from pathlib import Path
from statistics import mean
from typing import Any

from django.conf import settings
from django.utils import timezone


def perf_result_root() -> Path:
    root = Path(getattr(settings, "PERF_RESULT_DIR", settings.BASE_DIR / "perf_results"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def check_executor() -> dict[str, Any]:
    java_bin = resolve_java_bin()
    jmeter_bin = resolve_jmeter_bin()
    result_dir = perf_result_root()
    java = _probe_command([java_bin, "-version"])
    jmeter = _probe_command([jmeter_bin, "--version"], java_path=java["path"] if java["ok"] else "")
    writable = _check_writable(result_dir)
    ok = java["ok"] and jmeter["ok"] and writable
    return {
        "ok": ok,
        "java": java,
        "jmeter": jmeter,
        "result_dir": str(result_dir),
        "result_dir_writable": writable,
        "message": "" if ok else "当前未配置性能测试执行器，请先配置 Java 和 JMeter 路径。",
    }


def build_jmeter_command(run, jtl_path: Path, report_dir: Path) -> list[str]:
    task = run.task
    return [
        resolve_jmeter_bin(),
        "-n",
        "-t",
        str(task.script.file.path),
        "-l",
        str(jtl_path),
        "-e",
        "-o",
        str(report_dir),
        "-Jthreads=%s" % task.threads,
        "-Jramp_up=%s" % task.ramp_up_seconds,
        "-Jduration=%s" % task.duration_seconds,
        "-Jloops=%s" % task.loops,
    ]


def parse_jtl_summary(jtl_path: Path) -> dict[str, Any]:
    rows = []
    if not jtl_path.exists():
        return _empty_summary()
    with jtl_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            elapsed = _safe_float(row.get("elapsed") or row.get("time") or row.get("Latency"))
            timestamp = _safe_float(row.get("timeStamp"))
            success = str(row.get("success", "")).lower() in {"true", "1", "yes"}
            label = row.get("label") or row.get("samplerData") or "request"
            rows.append({"elapsed": elapsed, "success": success, "label": label, "timestamp": timestamp})
    if not rows:
        return _empty_summary()
    elapsed_values = sorted(item["elapsed"] for item in rows)
    total = len(rows)
    failed = len([item for item in rows if not item["success"]])
    timestamps = [item["timestamp"] for item in rows if item["timestamp"]]
    duration_seconds = max((max(timestamps) - min(timestamps)) / 1000, 1) if len(timestamps) > 1 else 1
    return {
        "total": total,
        "success": total - failed,
        "failed": failed,
        "error_rate": round(failed / total * 100, 2) if total else 0,
        "avg_ms": round(mean(elapsed_values), 2),
        "min_ms": round(elapsed_values[0], 2),
        "max_ms": round(elapsed_values[-1], 2),
        "p90_ms": round(_percentile(elapsed_values, 90), 2),
        "p95_ms": round(_percentile(elapsed_values, 95), 2),
        "p99_ms": round(_percentile(elapsed_values, 99), 2),
        "tps": round(total / duration_seconds, 2),
    }


def append_log(logs, level: str, message: str) -> list[dict[str, str]]:
    items = list(logs or [])
    items.append({"time": timezone.now().isoformat(), "level": level, "message": message})
    return items[-500:]


def resolve_java_bin() -> str:
    return _resolve_binary(
        getattr(settings, "JAVA_BIN", "java"),
        [
            _from_home("JAVA_HOME", "bin/java.exe"),
            _from_home("JAVA_HOME", "bin/java"),
            *_glob_paths("D:/testtools/Java*/bin/java.exe"),
            *_glob_paths("C:/Program Files/Java/*/bin/java.exe"),
            *_glob_paths("C:/Program Files/Eclipse Adoptium/*/bin/java.exe"),
        ],
    )


def resolve_jmeter_bin() -> str:
    return _resolve_binary(
        getattr(settings, "JMETER_BIN", "jmeter"),
        [
            _from_home("JMETER_HOME", "bin/jmeter.bat"),
            _from_home("JMETER_HOME", "bin/jmeter.cmd"),
            _from_home("JMETER_HOME", "bin/jmeter"),
            *_glob_paths("D:/testtools/apache-jmeter-*/bin/jmeter.bat"),
            *_glob_paths("C:/apache-jmeter-*/bin/jmeter.bat"),
            *_glob_paths("C:/tools/apache-jmeter-*/bin/jmeter.bat"),
        ],
    )


def executor_env(java_path: str = "", jmeter_path: str = "") -> dict[str, str]:
    env = os.environ.copy()
    env.pop("JMETER_BIN", None)
    java_bin = Path(java_path or resolve_java_bin())
    java_bin_dir = java_bin.parent if java_bin.name.lower().startswith("java") else None
    if java_bin_dir and java_bin_dir.exists():
        env["PATH"] = str(java_bin_dir) + os.pathsep + env.get("PATH", "")
        env.setdefault("JAVA_HOME", str(java_bin_dir.parent))
    jmeter_bin = Path(jmeter_path or resolve_jmeter_bin())
    if jmeter_bin.exists():
        env["JMETER_HOME"] = str(jmeter_bin.parent.parent)
        env["PATH"] = str(jmeter_bin.parent) + os.pathsep + env.get("PATH", "")
    return env


def _probe_command(command: list[str], java_path: str = "") -> dict[str, Any]:
    executable = _resolve_binary(command[0], [])
    executable_path = Path(executable)
    is_jmeter = executable_path.name.lower().startswith("jmeter")
    try:
        result = subprocess.run(
            [executable, *command[1:]],
            capture_output=True,
            text=True,
            timeout=10,
            env=executor_env(java_path=java_path, jmeter_path=executable) if java_path or is_jmeter else None,
            cwd=str(executable_path.parent) if is_jmeter and executable_path.parent.exists() else None,
        )
    except Exception as exc:
        return {"ok": False, "path": executable, "version": "", "error": str(exc)}
    output = "\n".join(part.strip() for part in [result.stdout, result.stderr] if part and part.strip())
    version = _pick_version_line(output)
    ok = result.returncode == 0 and not _has_probe_failure(output)
    return {"ok": ok, "path": executable, "version": version, "error": "" if ok else output}


def _resolve_binary(configured: str, candidates: list[str]) -> str:
    configured = str(configured or "").strip()
    if configured:
        configured_path = Path(configured)
        if configured_path.is_file():
            return str(configured_path)
        located = shutil.which(configured)
        if located:
            return located
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    return configured


def _from_home(env_name: str, relative_path: str) -> str:
    root = os.environ.get(env_name, "")
    return str(Path(root) / relative_path) if root else ""


def _glob_paths(pattern: str) -> list[str]:
    return sorted(glob.glob(pattern, recursive=False), reverse=True)


def _check_writable(path: Path) -> bool:
    try:
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _pick_version_line(output: str) -> str:
    for line in output.splitlines():
        text = line.strip()
        if text.startswith("/_/") and text.split()[-1].replace(".", "").isdigit():
            return f"Apache JMeter {text.split()[-1]}"
    for line in output.splitlines():
        text = line.strip()
        lowered = text.lower()
        if text and not text.startswith("WARN") and "errorlevel" not in lowered and "press any key" not in lowered and not lowered.startswith("error:"):
            return text
    return output.splitlines()[0].strip() if output else ""


def _has_probe_failure(output: str) -> bool:
    lowered = output.lower()
    failure_markers = [
        "unable to access jarfile",
        "not able to find java",
        "not defined correctly",
        "is too low to run jmeter",
    ]
    return any(marker in lowered for marker in failure_markers)


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0
    index = min(len(values) - 1, max(0, round((percentile / 100) * (len(values) - 1))))
    return values[index]


def _empty_summary() -> dict[str, Any]:
    return {"total": 0, "success": 0, "failed": 0, "error_rate": 0, "avg_ms": 0, "min_ms": 0, "max_ms": 0, "p90_ms": 0, "p95_ms": 0, "p99_ms": 0, "tps": 0}
