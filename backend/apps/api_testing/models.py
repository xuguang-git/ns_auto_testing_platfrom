from django.db import models

from apps.core.db_comments import apply_model_comments
from apps.core.models import OwnedModel, TimestampedModel
from apps.projects.models import Environment
from apps.projects.models import Platform as ManagedPlatform
from apps.projects.models import Project


class HttpMethod(models.TextChoices):
    GET = "GET", "GET"
    POST = "POST", "POST"
    PUT = "PUT", "PUT"
    PATCH = "PATCH", "PATCH"
    DELETE = "DELETE", "DELETE"


class Platform(models.TextChoices):
    ERP = "ERP", "ERP"
    WMS = "WMS", "WMS"
    PDA = "PDA", "PDA"
    CLIENT = "CLIENT", "Client"


class ApiModule(OwnedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="api_modules")
    managed_platform = models.ForeignKey(
        ManagedPlatform,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="api_modules",
    )
    platform = models.CharField(max_length=32)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=32, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table_comment = '接口目录表：按平台维护接口的多级模块/目录结构。'
        unique_together = [("project", "platform", "parent", "name")]
        ordering = ["platform", "sort_order", "id"]

    def __str__(self) -> str:
        return self.name


class ApiDefinition(OwnedModel):
    class Status(models.TextChoices):
        DEVELOPING = "developing", "Developing"
        RELEASED = "released", "Released"
        DEPRECATED = "deprecated", "Deprecated"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="api_definitions")
    platform = models.CharField(max_length=32)
    module = models.ForeignKey(ApiModule, null=True, blank=True, on_delete=models.SET_NULL, related_name="apis")
    name = models.CharField(max_length=100)
    path = models.CharField(max_length=512)
    method = models.CharField(max_length=16, choices=HttpMethod.choices, default=HttpMethod.GET)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DEVELOPING)
    tags = models.JSONField(default=list, blank=True)
    headers = models.JSONField(default=list, blank=True)
    query_params = models.JSONField(default=list, blank=True)
    body_type = models.CharField(max_length=32, default="none")
    body = models.JSONField(default=dict, blank=True)
    body_schema = models.JSONField(default=dict, blank=True)
    auth_config = models.JSONField(default=dict, blank=True)
    assertions = models.JSONField(default=list, blank=True)
    response_example = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table_comment = '接口定义表：维护平台接口的请求方式、路径、请求结构和示例。'
        unique_together = [("project", "platform", "method", "path")]
        ordering = ["platform", "module_id", "sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.method} {self.path}"


class ApiTestCase(OwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    class Priority(models.TextChoices):
        P0 = "P0", "P0"
        P1 = "P1", "P1"
        P2 = "P2", "P2"
        P3 = "P3", "P3"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="api_test_cases")
    api = models.ForeignKey(ApiDefinition, on_delete=models.CASCADE, related_name="test_cases")
    name = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    priority = models.CharField(max_length=8, choices=Priority.choices, default=Priority.P1)
    request_override = models.JSONField(default=dict, blank=True)
    pre_data_source_ids = models.JSONField(default=list, blank=True)
    post_data_source_ids = models.JSONField(default=list, blank=True)
    assertions = models.JSONField(default=list, blank=True)
    variables = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table_comment = '单接口测试用例表：绑定某个接口的功能用例和请求覆盖配置。'
        unique_together = [("project", "api", "name")]
        ordering = ["api_id", "priority", "id"]

    def __str__(self) -> str:
        return self.name


class ApiMockRule(OwnedModel):
    api = models.ForeignKey(ApiDefinition, on_delete=models.CASCADE, related_name="mock_rules")
    name = models.CharField(max_length=128, default="默认 Mock")
    enabled = models.BooleanField(default=False)
    status_code = models.PositiveSmallIntegerField(default=200)
    delay_ms = models.PositiveIntegerField(default=0)
    headers = models.JSONField(default=list, blank=True)
    response_body = models.JSONField(default=dict, blank=True)
    match_rules = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table_comment = '接口Mock规则表：维护接口模拟响应和匹配规则。'
        ordering = ["api_id", "-enabled", "id"]

    def __str__(self) -> str:
        return f"{self.api_id}/{self.name}"


class ApiSuite(OwnedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="api_suites")
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    platforms = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    case_ids = models.JSONField(default=list, blank=True, db_comment="套件包含的单接口用例ID列表。")
    run_config = models.JSONField(default=dict, blank=True, db_comment="套件运行配置JSON，如运行环境、运行模式、执行器和推送开关。")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table_comment = '接口测试套件表：组织接口用例和场景的集合。'
        unique_together = [("project", "name")]
        ordering = ["project_id", "name"]

    def __str__(self) -> str:
        return self.name


class ApiScenario(OwnedModel):
    suite = models.ForeignKey(ApiSuite, on_delete=models.CASCADE, related_name="scenarios")
    environment = models.ForeignKey(Environment, null=True, blank=True, on_delete=models.SET_NULL, related_name="api_scenarios")
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=8, default="P1")
    tags = models.JSONField(default=list, blank=True)
    run_config = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table_comment = '接口场景用例表：按业务流程编排多个接口步骤。'
        unique_together = [("suite", "name")]
        ordering = ["suite_id", "sort_order", "id"]

    def __str__(self) -> str:
        return self.name


class ApiStep(OwnedModel):
    scenario = models.ForeignKey(ApiScenario, on_delete=models.CASCADE, related_name="steps")
    api = models.ForeignKey(ApiDefinition, null=True, blank=True, on_delete=models.SET_NULL, related_name="steps")
    name = models.CharField(max_length=128)
    platform = models.CharField(max_length=32, default=Platform.ERP)
    method = models.CharField(max_length=16, choices=HttpMethod.choices, default=HttpMethod.GET)
    path = models.CharField(max_length=512)
    headers = models.JSONField(default=list, blank=True)
    query_params = models.JSONField(default=list, blank=True)
    body_type = models.CharField(max_length=32, default="none")
    body = models.JSONField(default=dict, blank=True)
    auth_config = models.JSONField(default=dict, blank=True)
    pre_data_source_ids = models.JSONField(default=list, blank=True)
    post_data_source_ids = models.JSONField(default=list, blank=True)
    pre_script = models.TextField(blank=True)
    post_script = models.TextField(blank=True)
    assertions = models.JSONField(default=list, blank=True)
    extractors = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table_comment = '场景接口步骤表：场景内单个接口步骤的请求、断言和变量提取配置。'
        ordering = ["scenario_id", "sort_order", "id"]

    def __str__(self) -> str:
        return self.name


class ApiCase(OwnedModel):
    suite = models.ForeignKey(ApiSuite, on_delete=models.CASCADE, related_name="cases")
    name = models.CharField(max_length=128)
    method = models.CharField(max_length=16, choices=HttpMethod.choices, default=HttpMethod.GET)
    path = models.CharField(max_length=512)
    headers = models.JSONField(default=dict, blank=True)
    query_params = models.JSONField(default=dict, blank=True)
    body = models.JSONField(default=dict, blank=True)
    assertions = models.JSONField(default=list, blank=True)
    extractors = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table_comment = '旧版接口用例表：按套件保存的接口请求步骤，保留兼容历史功能。'
        ordering = ["suite_id", "sort_order", "id"]

    def __str__(self) -> str:
        return self.name


apply_model_comments(ApiModule, "接口目录表：按平台维护接口的多级模块/目录结构。", {
    "project": "所属项目ID。",
    "managed_platform": "关联的平台管理记录。",
    "platform": "平台编码，如 ERP/WMS/PDA。",
    "parent": "父级接口目录ID，空表示顶级目录。",
    "name": "目录名称。",
    "code": "目录编码。",
    "description": "目录说明。",
    "is_active": "是否启用。",
    "sort_order": "目录排序值。",
})
apply_model_comments(ApiDefinition, "接口定义表：维护平台接口的请求方式、路径、请求结构和示例。", {
    "project": "所属项目ID。",
    "platform": "平台编码，如 ERP/WMS/PDA。",
    "module": "所属接口目录ID。",
    "name": "接口名称。",
    "path": "接口路径或完整URL。",
    "method": "HTTP请求方式。",
    "description": "接口说明。",
    "status": "接口状态：开发中/已发布/已废弃。",
    "tags": "接口标签列表。",
    "headers": "默认请求头配置。",
    "query_params": "默认查询参数配置。",
    "body_type": "请求体类型。",
    "body": "默认请求体。",
    "body_schema": "请求体结构描述。",
    "auth_config": "接口鉴权配置。",
    "assertions": "接口默认断言配置。",
    "response_example": "响应示例。",
    "sort_order": "排序值。",
    "is_active": "是否启用。",
})
apply_model_comments(ApiTestCase, "单接口测试用例表：绑定某个接口的功能用例和请求覆盖配置。", {
    "project": "所属项目ID。",
    "api": "关联接口定义ID。",
    "name": "用例名称。",
    "status": "用例状态：草稿/启用/停用。",
    "priority": "优先级。",
    "request_override": "覆盖接口默认请求的配置。",
    "pre_data_source_ids": "前置测试数据源ID列表。",
    "post_data_source_ids": "后置测试数据源ID列表。",
    "assertions": "用例断言配置。",
    "variables": "用例变量配置。",
    "description": "用例说明。",
    "is_active": "是否启用。",
})
apply_model_comments(ApiMockRule, "接口Mock规则表：维护接口模拟响应和匹配规则。", {
    "api": "关联接口定义ID。",
    "name": "Mock规则名称。",
    "enabled": "是否启用该Mock规则。",
    "status_code": "Mock响应状态码。",
    "delay_ms": "Mock响应延迟毫秒数。",
    "headers": "Mock响应头。",
    "response_body": "Mock响应体。",
    "match_rules": "Mock匹配规则。",
    "description": "规则说明。",
})
apply_model_comments(ApiSuite, "接口测试套件表：组织接口用例和场景的集合。", {
    "project": "所属项目ID。",
    "name": "套件名称。",
    "description": "套件说明。",
    "platforms": "套件覆盖的平台编码列表。",
    "tags": "套件标签列表。",
    "is_active": "是否启用。",
})
apply_model_comments(ApiScenario, "接口场景用例表：按业务流程编排多个接口步骤。", {
    "suite": "所属接口测试套件ID。",
    "environment": "场景默认运行环境ID。",
    "name": "场景名称。",
    "description": "场景说明。",
    "priority": "优先级。",
    "tags": "场景标签列表。",
    "run_config": "场景运行配置JSON，如测试数据、循环次数、线程数、执行机和通知配置。",
    "sort_order": "排序值。",
    "is_active": "是否启用。",
})
apply_model_comments(ApiStep, "场景接口步骤表：场景内单个接口步骤的请求、断言和变量提取配置。", {
    "scenario": "所属场景ID。",
    "api": "继承来源接口定义ID，可为空。",
    "name": "步骤名称。",
    "platform": "步骤所属平台编码。",
    "method": "HTTP请求方式。",
    "path": "请求路径或完整URL。",
    "headers": "步骤请求头配置。",
    "query_params": "步骤查询参数配置。",
    "body_type": "请求体类型。",
    "body": "步骤请求体。",
    "auth_config": "步骤鉴权配置。",
    "pre_data_source_ids": "步骤执行前运行的数据源ID列表。",
    "post_data_source_ids": "步骤执行后运行的数据源ID列表。",
    "pre_script": "步骤前置脚本。",
    "post_script": "步骤后置脚本。",
    "assertions": "步骤断言配置。",
    "extractors": "响应变量提取规则。",
    "sort_order": "步骤排序值。",
    "is_active": "是否启用。",
})
apply_model_comments(ApiCase, "旧版接口用例表：按套件保存的接口请求步骤，保留兼容历史功能。", {
    "suite": "所属接口测试套件ID。",
    "name": "用例名称。",
    "method": "HTTP请求方式。",
    "path": "请求路径或完整URL。",
    "headers": "请求头配置。",
    "query_params": "查询参数配置。",
    "body": "请求体。",
    "assertions": "断言配置。",
    "extractors": "变量提取规则。",
    "sort_order": "排序值。",
    "is_active": "是否启用。",
})
