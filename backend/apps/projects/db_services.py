import os
import re
from contextlib import closing
from dataclasses import dataclass
from typing import Any

import MySQLdb
import MySQLdb.cursors
import psycopg
from psycopg.rows import dict_row
from django.utils import timezone
from rest_framework import serializers

from apps.projects.models import DatabaseConnection, TestDataSource


CONNECTION_LIST_ENV = "TEST_DATA_DB_CONNECTIONS"
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


def env_key(prefix: str, suffix: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_]", "_", prefix or "").upper().strip("_")
    return f"{normalized}_{suffix}"


def configured_connection_prefixes() -> list[str]:
    raw = _read_env(CONNECTION_LIST_ENV)
    prefixes = []
    for item in re.split(r"[,;\s]+", raw):
        prefix = re.sub(r"[^A-Za-z0-9_]", "_", item or "").upper().strip("_")
        if prefix and prefix not in prefixes:
            prefixes.append(prefix)
    return prefixes


def sync_configured_database_connections() -> list[str]:
    prefixes = configured_connection_prefixes()
    if not prefixes:
        return []
    for prefix in prefixes:
        environment = _resolve_connection_environment(prefix)
        if not environment:
            continue
        DatabaseConnection.objects.update_or_create(
            env_prefix=prefix,
            defaults={
                "environment": environment,
                "name": _read_env(env_key(prefix, "DISPLAY_NAME")) or prefix,
                "db_type": parse_database_type(_read_env(env_key(prefix, "TYPE"))),
                "description": _read_env(env_key(prefix, "DESCRIPTION")),
                "is_active": _read_bool(_read_env(env_key(prefix, "ENABLED")), True),
            },
        )
    return prefixes


def load_credentials(connection: DatabaseConnection, require_password: bool = True) -> DatabaseCredentials:
    prefix = connection.env_prefix
    host = _read_env(env_key(prefix, "HOST"))
    default_port = 5432 if connection.db_type == DatabaseConnection.DatabaseType.POSTGRESQL else 3306
    port = _safe_int(_read_env(env_key(prefix, "PORT")), default_port)
    name = _read_env(env_key(prefix, "NAME"))
    user = _read_env(env_key(prefix, "USER"))
    password = _read_env(env_key(prefix, "PASSWORD"))
    missing = []
    for field, value in {"HOST": host, "NAME": name, "USER": user}.items():
        if not value:
            missing.append(env_key(prefix, field))
    if require_password and not password:
        missing.append(env_key(prefix, "PASSWORD"))
    if missing:
        raise serializers.ValidationError(f"数据库连接缺少环境变量：{', '.join(missing)}")
    return DatabaseCredentials(host=host, port=port, name=name, user=user, password=password)


def check_database_connection(connection: DatabaseConnection) -> dict[str, Any]:
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
    except Exception:
        connection.last_check_status = DatabaseConnection.CheckStatus.FAILED
        connection.last_check_message = "连接失败，请检查服务端数据库配置。"
        ok = False
        message = connection.last_check_message
    connection.last_checked_at = timezone.now()
    connection.save(update_fields=["last_check_status", "last_check_message", "last_checked_at", "updated_at"])
    return {"ok": ok, "message": message, "checked_at": connection.last_checked_at.isoformat(), "status": str(connection.last_check_status)}


def execute_test_data_source(data_source: TestDataSource, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    if data_source.source_type != TestDataSource.SourceType.DATABASE_QUERY:
        raise serializers.ValidationError("暂不支持的数据源类型。")
    if not data_source.is_active:
        raise serializers.ValidationError("测试数据源已停用。")
    if not data_source.database_connection or not data_source.database_connection.is_active:
        raise serializers.ValidationError("请选择已启用的数据库连接。")
    sql = render_sql(data_source.sql, variables or {})
    rows = execute_select_query(data_source.database_connection, sql)
    extracted = extract_values(rows, data_source.extractors or [])
    result = {"rows": rows, "variables": extracted, "row_count": len(rows)}
    data_source.last_result = {"variables": extracted, "row_count": len(rows)}
    data_source.run_count = (data_source.run_count or 0) + 1
    data_source.save(update_fields=["last_result", "run_count", "updated_at"])
    return result


def execute_select_query(connection: DatabaseConnection, sql: str) -> list[dict[str, Any]]:
    validate_select_sql(sql)
    credentials = load_credentials(connection)
    with database_connection(connection, credentials) as db:
        if connection.db_type == DatabaseConnection.DatabaseType.MYSQL:
            with db.cursor(MySQLdb.cursors.DictCursor) as cursor:
                cursor.execute(_limit_sql(sql, DEFAULT_QUERY_LIMIT))
                rows = cursor.fetchmany(MAX_QUERY_ROWS)
        else:
            with db.cursor() as cursor:
                cursor.execute(_limit_sql(sql, DEFAULT_QUERY_LIMIT))
                rows = cursor.fetchmany(MAX_QUERY_ROWS)
    return [serialize_row(row) for row in rows]


def parse_database_type(value: str) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    if normalized in {"postgres", "postgresql", "pg"}:
        return DatabaseConnection.DatabaseType.POSTGRESQL
    return DatabaseConnection.DatabaseType.MYSQL


def validate_select_sql(sql: str) -> None:
    normalized = (sql or "").strip()
    if not normalized:
        raise serializers.ValidationError("SQL 不能为空。")
    if ";" in normalized.rstrip(";"):
        raise serializers.ValidationError("只允许执行单条 SELECT 查询。")
    normalized = normalized.rstrip(";").strip()
    if not re.match(r"^(select|with)\b", normalized, re.IGNORECASE):
        raise serializers.ValidationError("第一版只允许 SELECT 查询。")
    if SQL_COMMENT_PATTERN.search(normalized):
        raise serializers.ValidationError("SQL 中暂不允许注释。")
    if BLOCKED_SQL_PATTERN.search(normalized):
        raise serializers.ValidationError("SQL 包含非只读关键字，已拦截。")


def extract_values(rows: list[dict[str, Any]], extractors: list[dict[str, Any]]) -> dict[str, Any]:
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
    def replace(match):
        value = variables.get(match.group(1), "")
        return str(value).replace("'", "''")

    return re.sub(r"{{\s*([a-zA-Z0-9_.-]+)\s*}}", replace, sql or "")


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


def _read_env(key: str) -> str:
    return str(os.environ.get(key, "")).strip()


def _read_bool(value: str, default: bool) -> bool:
    if value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on", "enabled"}


def _resolve_connection_environment(prefix: str):
    from apps.projects.models import Environment

    value = _read_env(env_key(prefix, "ENVIRONMENT"))
    queryset = Environment.objects.select_related("project").all()
    if value:
        if value.isdigit():
            matched = queryset.filter(id=int(value)).first()
            if matched:
                return matched
        matched = queryset.filter(name__iexact=value).first()
        if matched:
            return matched
        matched = queryset.filter(env_type__iexact=value).first()
        if matched:
            return matched
    return queryset.filter(is_default=True).first() or queryset.first()


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
