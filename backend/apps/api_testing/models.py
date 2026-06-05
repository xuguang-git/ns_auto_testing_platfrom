from django.db import models

from apps.core.models import OwnedModel, TimestampedModel
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
    assertions = models.JSONField(default=list, blank=True)
    variables = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
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
        ordering = ["api_id", "-enabled", "id"]

    def __str__(self) -> str:
        return f"{self.api_id}/{self.name}"


class ApiSuite(OwnedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="api_suites")
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    platforms = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("project", "name")]
        ordering = ["project_id", "name"]

    def __str__(self) -> str:
        return self.name


class ApiScenario(OwnedModel):
    suite = models.ForeignKey(ApiSuite, on_delete=models.CASCADE, related_name="scenarios")
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=8, default="P1")
    tags = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
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
    pre_script = models.TextField(blank=True)
    post_script = models.TextField(blank=True)
    assertions = models.JSONField(default=list, blank=True)
    extractors = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
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
        ordering = ["suite_id", "sort_order", "id"]

    def __str__(self) -> str:
        return self.name
