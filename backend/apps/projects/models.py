from django.db import models

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
        unique_together = [("environment", "key", "platform")]
        ordering = ["environment_id", "platform", "key"]

    def __str__(self) -> str:
        return self.key


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
        ordering = ["-updated_at", "-id"]

    def __str__(self) -> str:
        return self.name
