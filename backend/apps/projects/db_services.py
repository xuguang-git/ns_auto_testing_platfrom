import logging
import re
from contextlib import closing
from dataclasses import dataclass
from typing import Any

import MySQLdb
import MySQLdb.cursors
import psycopg
from django.conf import settings
from django.utils import timezone
from psycopg.rows import dict_row
from rest_framework import serializers

from apps.projects.models import DatabaseConnection, TestDataSource
from apps.scheduling.crypto import decrypt_secret


logger = logging.getLogger(__name__)
BLOCKED_SQL_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|replace|merge|grant|revoke|call|exec|execute|load|outfile|dumpfile|set|use|lock|unlock)\b",
    re.IGNORECASE,
)
SQL_COMMENT_PATTERN = re.compile(r"(--|#|/\*)")
MAX_QUERY_ROWS = 1000
DEFAULT_QUERY_LIMIT = 100


@dataclass
class DatabaseCredentials:
    host: str
    port: int
    name: str
    user: str
    password: str


def load_credentials(connection: DatabaseConnection, require_password: bool = True) -> DatabaseCredentials:
    """从数据库连接表读取运行期连接信息，不再依赖 .env 配置。"""
    host = (connection.host or "").strip()
    default_port = 5432 if connection.db_type == DatabaseConnection.DatabaseType.POSTGRESQL else 3306
    port = _safe_int(connection.port, default_port)
    name = (connection.database_name or "").strip()
    user = (connection.username or "").strip()
    password = decrypt_secret(connection.password_ciphertext) if connection.password_ciphertext else ""
    missing = []
    for field, value in {"HOST": host, "NAME": name, "USER": user}.items():
        if not value:
            missing.append(field)
    if require_password and not password:
        missing.append("PASSWORD")
    if missing:
        raise serializers.ValidationError(f"数据库连接缺少必填配置：{', '.join(missing)}")
    return DatabaseCredentials(host=host, port=port, name=name, user=user, password=password)


def check_database_connection(connection: DatabaseConnection) -> dict[str, Any]:
    """检测数据库连接可用性，并记录最近一次检测结果。"""
    error_type = ""
    debug_message = ""
    try:
        credentials = load_credentials(connection)
        with database_connection(connection, credentials) as db:
            with db.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        connection.last_check_status = DatabaseConnection.CheckStatus.SUCCESS
        connection.last_check_message = "连接成功"
        ok = True
        message = "连接成功"
    except Exception as exc:
        logger.warning("Database connection check failed: id=%s, name=%s", connection.id, connection.name, exc_info=exc)
        connection.last_check_status = DatabaseConnection.CheckStatus.FAILED
        error_type, message = classify_database_connection_error(exc)
        debug_message = sanitize_database_error(exc)
        connection.last_check_message = message[:255]
        ok = False
    connection.last_checked_at = timezone.now()
    connection.save(update_fields=["last_check_status", "last_check_message", "last_checked_at", "updated_at"])
    result = {"ok": ok, "message": message, "checked_at": connection.last_checked_at.isoformat(), "status": str(connection.last_check_status)}
    if error_type:
        result["error_type"] = error_type
    if error_type and settings.DEBUG:
        result["debug_message"] = debug_message
    return result


def classify_database_connection_error(exc: Exception) -> tuple[str, str]:
    """把底层数据库连接异常转换为前端可读的中文提示。"""
    if isinstance(exc, serializers.ValidationError):
        return "missing_config", _validation_error_message(exc)

    detail = sanitize_database_error(exc).lower()
    if "password authentication failed" in detail or "access denied" in detail or "authentication failed" in detail:
        return "authentication_failed", "数据库连接失败：账号或密码不正确，请检查数据库连接配置。"
    if "does not exist" in detail or "unknown database" in detail or "unknown catalog" in detail:
        return "database_not_found", "数据库连接失败：数据库不存在或当前账号无权访问。"
    if "timeout" in detail or "timed out" in detail or "could not connect" in detail:
        return "connection_timeout", "数据库连接失败：无法连接到数据库，请检查地址、端口、网络白名单或安全组。"
    if "connection refused" in detail or "actively refused" in detail:
        return "connection_refused", "数据库连接失败：目标端口拒绝连接，请检查数据库服务和端口配置。"
    if "name or service not known" in detail or "nodename nor servname" in detail or "getaddrinfo" in detail:
        return "host_unresolved", "数据库连接失败：无法解析数据库主机，请检查数据库地址配置。"
    if "ssl" in detail or "tls" in detail:
        return "ssl_failed", "数据库连接失败：目标数据库可能要求 SSL 连接，请检查数据库 SSL 配置。"
    return "unknown", "数据库连接失败：请检查数据库连接配置。"


def _validation_error_message(exc: serializers.ValidationError) -> str:
    detail = exc.detail if hasattr(exc, "detail") else str(exc)
    if isinstance(detail, list):
        return "；".join(str(item) for item in detail)
    if isinstance(detail, dict):
        return "；".join(f"{key}: {value}" for key, value in detail.items())
    return str(detail)


def sanitize_database_error(exc: Exception) -> str:
    """清洗数据库异常，避免把密码等敏感信息带到响应或日志。"""
    detail = str(exc)
    detail = re.sub(r"password\s*=\s*[^\s]+", "password=***", detail, flags=re.IGNORECASE)
    detail = re.sub(r"(://[^:/\s]+:)[^@\s]+@", r"\1***@", detail)
    return detail[:500]


def execute_test_data_source(data_source: TestDataSource, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    """执行只读测试数据源，并把配置的字段提取为场景变量。"""
    if data_source.source_type != TestDataSource.SourceType.DATABASE_QUERY:
        raise serializers.ValidationError("暂不支持的数据源类型。")
    if not data_source.is_active:
        raise serializers.ValidationError("测试数据源已停用。")
    if not data_source.database_connection or not data_source.database_connection.is_active:
        raise serializers.ValidationError("请选择已启用的数据库连接。")
    sql = render_sql(data_source.sql, normalize_variables(variables))
    rows = execute_select_query(data_source.database_connection, sql)
    extracted = extract_values(rows, data_source.extractors or [])
    result = {"rows": rows, "variables": extracted, "row_count": len(rows)}
    data_source.last_result = {"variables": extracted, "row_count": len(rows)}
    data_source.run_count = (data_source.run_count or 0) + 1
    data_source.save(update_fields=["last_result", "run_count", "updated_at"])
    return result


def execute_select_query(connection: DatabaseConnection, sql: str) -> list[dict[str, Any]]:
    """执行受控 SELECT 查询，统一做 SQL 安全校验和结果序列化。"""
    validate_select_sql(sql)
    credentials = load_credentials(connection)
    try:
        with database_connection(connection, credentials) as db:
            if connection.db_type == DatabaseConnection.DatabaseType.MYSQL:
                with db.cursor(MySQLdb.cursors.DictCursor) as cursor:
                    cursor.execute(_limit_sql(sql, DEFAULT_QUERY_LIMIT))
                    rows = cursor.fetchmany(MAX_QUERY_ROWS)
            else:
                with db.cursor() as cursor:
                    cursor.execute(_limit_sql(sql, DEFAULT_QUERY_LIMIT))
                    rows = cursor.fetchmany(MAX_QUERY_ROWS)
    except serializers.ValidationError:
        raise
    except Exception as exc:
        logger.warning("Test data source query failed: connection_id=%s", connection.id, exc_info=exc)
        raise serializers.ValidationError(classify_database_query_error(exc)) from exc
    return [serialize_row(row) for row in rows]


def classify_database_query_error(exc: Exception) -> str:
    detail = sanitize_database_error(exc).lower()
    if "syntax error" in detail:
        return "SQL执行失败：SQL语法错误，请检查查询语句。"
    if "column" in detail and "does not exist" in detail:
        return "SQL执行失败：字段不存在，PostgreSQL 字符串条件请使用单引号。"
    if "relation" in detail and "does not exist" in detail:
        return "SQL执行失败：表不存在或当前账号无权访问该表。"
    if "permission denied" in detail:
        return "SQL执行失败：当前数据库账号没有执行该查询的权限。"

    error_type, connection_message = classify_database_connection_error(exc)
    if error_type != "unknown":
        return connection_message

    return "SQL执行失败：请检查数据源 SQL、表字段和数据库权限。"


def parse_database_type(value: str) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    if normalized in {"postgres", "postgresql", "pg"}:
        return DatabaseConnection.DatabaseType.POSTGRESQL
    return DatabaseConnection.DatabaseType.MYSQL


def validate_select_sql(sql: str) -> None:
    """限制数据源只允许单条只读 SELECT/WITH 查询。"""
    normalized = (sql or "").strip()
    if not normalized:
        raise serializers.ValidationError("SQL 不能为空。")
    if ";" in normalized.rstrip(";"):
        raise serializers.ValidationError("只允许执行单条 SELECT 查询。")
    normalized = normalized.rstrip(";").strip()
    if not re.match(r"^(select|with)\b", normalized, re.IGNORECASE):
        raise serializers.ValidationError("当前只允许 SELECT 查询。")
    if SQL_COMMENT_PATTERN.search(normalized):
        raise serializers.ValidationError("SQL 中暂不允许注释。")
    if BLOCKED_SQL_PATTERN.search(normalized):
        raise serializers.ValidationError("SQL 包含非只读关键字，已拦截。")


def extract_values(rows: list[dict[str, Any]], extractors: list[dict[str, Any]]) -> dict[str, Any]:
    """按数据源提取器配置从查询结果中生成变量。"""
    result: dict[str, Any] = {}
    for extractor in extractors:
        name = str(extractor.get("name") or "").strip()
        if not name:
            continue
        column = str(extractor.get("column") or extractor.get("path") or "").strip()
        mode = extractor.get("mode") or "first"
        row_index = _safe_int(extractor.get("row"), 0)
        if not column:
            continue
        if mode == "column":
            result[name] = [row.get(column) for row in rows if column in row]
        elif rows and 0 <= row_index < len(rows):
            result[name] = rows[row_index].get(column)
        else:
            result[name] = None
    return result


def render_sql(sql: str, variables: dict[str, Any]) -> str:
    """渲染 SQL 中的 {{变量名}}，并对单引号做转义。"""
    def replace(match):
        value = variables.get(match.group(1), "")
        return str(value).replace("'", "''")

    return re.sub(r"{{\s*([a-zA-Z0-9_.-]+)\s*}}", replace, sql or "")


def normalize_variables(variables: Any) -> dict[str, Any]:
    if isinstance(variables, dict):
        return variables
    if isinstance(variables, list):
        result: dict[str, Any] = {}
        for item in variables:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or item.get("name") or "").strip()
            if key:
                result[key] = item.get("value", "")
        return result
    return {}


def mysql_connection(credentials: DatabaseCredentials):
    return closing(MySQLdb.connect(
        host=credentials.host,
        port=credentials.port,
        user=credentials.user,
        passwd=credentials.password,
        db=credentials.name,
        charset="utf8mb4",
        connect_timeout=5,
        read_timeout=10,
        write_timeout=10,
        autocommit=True,
    ))


def postgresql_connection(credentials: DatabaseCredentials):
    return closing(psycopg.connect(
        host=credentials.host,
        port=credentials.port,
        user=credentials.user,
        password=credentials.password,
        dbname=credentials.name,
        connect_timeout=5,
        row_factory=dict_row,
        autocommit=True,
    ))


def database_connection(connection: DatabaseConnection, credentials: DatabaseCredentials):
    if connection.db_type == DatabaseConnection.DatabaseType.POSTGRESQL:
        return postgresql_connection(credentials)
    return mysql_connection(credentials)


def serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for key, value in row.items():
        if hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


def _limit_sql(sql: str, limit: int) -> str:
    normalized = sql.rstrip(";").strip()
    if re.search(r"\blimit\s+\d+\b", normalized, re.IGNORECASE):
        return normalized
    return f"{normalized} LIMIT {min(limit, MAX_QUERY_ROWS)}"


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
