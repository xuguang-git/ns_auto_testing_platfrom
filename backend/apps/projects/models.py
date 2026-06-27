from django.db import models

from apps.core.db_comments import apply_model_comments
from apps.core.models import OwnedModel, TimestampedModel


class Project(OwnedModel):
    class Platform(models.TextChoices):
        ERP = "ERP", "ERP"
        WMS = "WMS", "WMS"
        PDA = "PDA", "PDA"
        CLIENT = "CLIENT", "Client"

    name = models.CharField(max_length=128, unique=True)
    code = models.SlugField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    platforms = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table_comment = "项目表：平台内业务项目的基础配置。"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Platform(OwnedModel):
    name = models.CharField(max_length=64)
    code = models.SlugField(max_length=32, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table_comment = "平台表：ERP/WMS/PDA等业务平台字典。"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.name


class Environment(OwnedModel):
    class EnvType(models.TextChoices):
        DEV = "dev", "Dev"
        TEST = "test", "Test"
        STAGING = "staging", "Staging"
        PROD = "prod", "Prod"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="environments")
    name = models.CharField(max_length=64)
    env_type = models.CharField(max_length=16, choices=EnvType.choices, default=EnvType.TEST)
    base_url = models.URLField(blank=True)
    platform_base_urls = models.JSONField(default=dict, blank=True)
    variables = models.JSONField(default=dict, blank=True)
    secret_variables = models.JSONField(default=dict, blank=True)
    headers = models.JSONField(default=dict, blank=True)
    pre_request_enabled = models.BooleanField(default=False)
    pre_request_config = models.JSONField(default=dict, blank=True)
    token_session = models.JSONField(default=dict, blank=True)
    is_default = models.BooleanField(default=False)
    is_readonly = models.BooleanField(default=False)

    class Meta:
        db_table_comment = '环境表：维护测试/预发/生产等运行环境和基础变量。'
        unique_together = [("project", "name")]
        ordering = ["project_id", "-is_default", "name"]

    def __str__(self) -> str:
        return f"{self.project.name}/{self.name}"


class EnvironmentVariable(OwnedModel):
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name="variable_items")
    key = models.CharField(max_length=128)
    value = models.TextField(blank=True)
    scope = models.CharField(max_length=32, default="environment")
    platform = models.CharField(max_length=16, blank=True)
    is_secret = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        db_table_comment = '环境变量表：按环境和平台维护可引用变量。'
        unique_together = [("environment", "key", "platform")]
        ordering = ["environment_id", "platform", "key"]

    def __str__(self) -> str:
        return self.key


class EnvironmentPreRequestOperation(OwnedModel):
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name="pre_request_operations")
    name = models.CharField(max_length=128)
    is_enabled = models.BooleanField(default=True)
    platforms = models.JSONField(default=list, blank=True)
    modules = models.ManyToManyField("api_testing.ApiModule", blank=True, related_name="pre_request_operations")
    config = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table_comment = '环境全局前置操作表：按环境配置登录鉴权等前置请求。'
        ordering = ["environment_id", "sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.environment.name}/{self.name}"


class EnvironmentRequestControl(OwnedModel):
    class HttpMethod(models.TextChoices):
        GET = "GET", "GET"
        POST = "POST", "POST"
        PUT = "PUT", "PUT"
        PATCH = "PATCH", "PATCH"
        DELETE = "DELETE", "DELETE"

    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name="request_controls")
    name = models.CharField(max_length=128)
    methods = models.JSONField(default=list, blank=True)
    is_enabled = models.BooleanField(default=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table_comment = '环境请求控件表：限制指定环境允许执行的HTTP请求方式。'
        ordering = ["environment_id", "name", "id"]

    def __str__(self) -> str:
        return f"{self.environment.name}/{self.name}"


class DatabaseConnection(OwnedModel):
    class DatabaseType(models.TextChoices):
        MYSQL = "mysql", "MySQL"
        POSTGRESQL = "postgresql", "PostgreSQL"

    class CheckStatus(models.TextChoices):
        UNCHECKED = "unchecked", "Unchecked"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name="database_connections")
    name = models.CharField(max_length=128)
    db_type = models.CharField(max_length=16, choices=DatabaseType.choices, default=DatabaseType.MYSQL)
    env_prefix = models.SlugField(max_length=64, unique=True, blank=True)
    host = models.CharField(max_length=255, blank=True)
    port = models.PositiveIntegerField(default=3306)
    database_name = models.CharField(max_length=128, blank=True)
    username = models.CharField(max_length=128, blank=True)
    password_ciphertext = models.TextField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    last_check_status = models.CharField(max_length=16, choices=CheckStatus.choices, default=CheckStatus.UNCHECKED)
    last_check_message = models.CharField(max_length=255, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table_comment = '数据库连接表：测试数据源使用的数据库连接配置。'
        ordering = ["environment_id", "name"]

    def __str__(self) -> str:
        return f"{self.environment.name}/{self.name}"


class DataFactoryCapability(OwnedModel):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    platform = models.CharField(max_length=32, blank=True)
    environment = models.ForeignKey(Environment, null=True, blank=True, on_delete=models.SET_NULL, related_name="data_capabilities")
    method = models.CharField(max_length=16, default="GET")
    path = models.CharField(max_length=1024)
    curl = models.TextField(blank=True)
    headers = models.JSONField(default=list, blank=True)
    query_params = models.JSONField(default=list, blank=True)
    body = models.JSONField(default=dict, blank=True)
    body_text = models.TextField(blank=True)
    extractors = models.JSONField(default=list, blank=True)
    last_result = models.JSONField(default=dict, blank=True)
    run_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table_comment = '数据制造能力表：通过接口调用生成测试数据并提取变量。'
        ordering = ["-updated_at", "-id"]

    def __str__(self) -> str:
        return self.name


class TestDataSource(OwnedModel):
    class SourceType(models.TextChoices):
        DATABASE_QUERY = "database_query", "Database query"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="test_data_sources")
    environment = models.ForeignKey(Environment, null=True, blank=True, on_delete=models.SET_NULL, related_name="test_data_sources")
    database_connection = models.ForeignKey(DatabaseConnection, null=True, blank=True, on_delete=models.SET_NULL, related_name="test_data_sources")
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    source_type = models.CharField(max_length=32, choices=SourceType.choices, default=SourceType.DATABASE_QUERY)
    sql = models.TextField(blank=True)
    extractors = models.JSONField(default=list, blank=True)
    last_result = models.JSONField(default=dict, blank=True)
    run_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table_comment = '测试数据源表：通过SQL等方式准备测试数据并提取变量。'
        unique_together = [("project", "name")]
        ordering = ["project_id", "name"]

    def __str__(self) -> str:
        return self.name


apply_model_comments(Project, "项目表：平台内业务项目的基础配置。", {
    "name": "项目名称。",
    "code": "项目编码。",
    "description": "项目说明。",
    "platforms": "项目启用的平台编码列表。",
    "is_active": "是否启用。",
})
apply_model_comments(Platform, "平台表：ERP/WMS/PDA等业务平台字典。", {
    "name": "平台名称。",
    "code": "平台编码。",
    "description": "平台说明。",
    "is_active": "是否启用。",
    "sort_order": "排序值。",
})
apply_model_comments(Environment, "环境表：维护测试/预发/生产等运行环境和基础变量。", {
    "project": "所属项目ID。",
    "name": "环境名称。",
    "env_type": "环境类型：dev/test/staging/prod。",
    "base_url": "环境默认Base URL。",
    "platform_base_urls": "不同平台的Base URL映射。",
    "variables": "环境基础变量JSON。",
    "secret_variables": "环境敏感变量JSON。",
    "headers": "环境级默认请求头。",
    "pre_request_enabled": "是否启用旧版全局前置操作。",
    "pre_request_config": "旧版全局前置操作配置。",
    "token_session": "前置登录缓存的Token会话信息。",
    "is_default": "是否默认环境。",
    "is_readonly": "是否只读环境。",
})
apply_model_comments(EnvironmentVariable, "环境变量表：按环境和平台维护可引用变量。", {
    "environment": "所属环境ID。",
    "key": "变量Key，用于{{变量名}}引用。",
    "value": "变量值。",
    "scope": "变量作用域。",
    "platform": "平台编码，空表示环境通用变量。",
    "is_secret": "是否敏感变量。",
    "description": "变量说明。",
    "is_enabled": "是否启用。",
})
apply_model_comments(EnvironmentPreRequestOperation, "环境全局前置操作表：按环境配置登录鉴权等前置请求。", {
    "environment": "所属环境ID。",
    "name": "前置操作名称。",
    "is_enabled": "是否启用。",
    "platforms": "生效平台编码列表。",
    "config": "前置操作配置JSON。",
    "sort_order": "执行排序值。",
})
apply_model_comments(EnvironmentRequestControl, "环境请求控件表：限制指定环境允许执行的HTTP请求方式。", {
    "environment": "所属环境ID。",
    "name": "控件名称。",
    "methods": "允许执行的HTTP方法列表。",
    "is_enabled": "是否启用请求控件。",
    "description": "控件说明。",
})
apply_model_comments(DatabaseConnection, "数据库连接表：测试数据源使用的数据库连接配置。", {
    "environment": "所属环境ID。",
    "name": "数据库连接名称。",
    "db_type": "数据库类型。",
    "env_prefix": "历史兼容字段，不再作为运行期配置来源。",
    "host": "数据库主机地址。",
    "port": "数据库端口。",
    "database_name": "数据库名称。",
    "username": "数据库账号。",
    "password_ciphertext": "数据库密码密文。",
    "description": "连接说明。",
    "is_active": "是否启用。",
    "last_check_status": "最近连接检测状态。",
    "last_check_message": "最近连接检测消息。",
    "last_checked_at": "最近检测时间。",
})
apply_model_comments(DataFactoryCapability, "数据制造能力表：通过接口调用生成测试数据并提取变量。", {
    "name": "能力名称。",
    "description": "能力说明。",
    "platform": "所属平台编码。",
    "environment": "默认运行环境ID。",
    "method": "HTTP请求方式。",
    "path": "请求路径或完整URL。",
    "curl": "原始curl文本。",
    "headers": "请求头配置。",
    "query_params": "查询参数配置。",
    "body": "请求体JSON。",
    "body_text": "请求体文本。",
    "extractors": "变量提取规则。",
    "last_result": "最近一次执行结果。",
    "run_count": "执行次数。",
    "is_active": "是否启用。",
})
apply_model_comments(TestDataSource, "测试数据源表：通过SQL等方式准备测试数据并提取变量。", {
    "project": "所属项目ID。",
    "environment": "所属环境ID。",
    "database_connection": "使用的数据库连接ID。",
    "name": "数据源名称。",
    "description": "数据源说明。",
    "source_type": "数据源类型。",
    "sql": "数据源SQL。",
    "extractors": "从结果集中提取变量的规则。",
    "last_result": "最近一次试运行结果。",
    "run_count": "试运行次数。",
    "is_active": "是否启用。",
})
