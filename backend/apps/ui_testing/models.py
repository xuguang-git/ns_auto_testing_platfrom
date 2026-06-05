from django.db import models

from apps.core.models import OwnedModel, TimestampedModel
from apps.projects.models import Project


class UiSuite(OwnedModel):
    project = models.ForeignKey(Project, verbose_name="项目", on_delete=models.CASCADE, related_name="ui_suites")
    name = models.CharField("套件名称", max_length=128)
    description = models.TextField("套件描述", blank=True)

    class Meta:
        verbose_name = "UI测试套件"
        verbose_name_plural = "UI测试套件"
        unique_together = [("project", "name")]
        ordering = ["project_id", "name"]

    def __str__(self) -> str:
        return self.name


class UiCase(OwnedModel):
    class Browser(models.TextChoices):
        CHROMIUM = "chromium", "Chromium"
        FIREFOX = "firefox", "Firefox"
        WEBKIT = "webkit", "WebKit"

    suite = models.ForeignKey(UiSuite, verbose_name="兼容套件", on_delete=models.CASCADE, related_name="cases")
    suites = models.ManyToManyField(UiSuite, verbose_name="所属套件", related_name="case_memberships", blank=True)
    name = models.CharField("用例名称", max_length=128)
    browser = models.CharField("浏览器", max_length=32, choices=Browser.choices, default=Browser.CHROMIUM)
    start_url = models.URLField("起始地址", blank=True)
    steps = models.JSONField("步骤", default=list, blank=True)
    elements = models.ManyToManyField("UiElement", verbose_name="关联定位元素", related_name="ui_cases", blank=True)
    assertions = models.JSONField("断言", default=list, blank=True)
    sort_order = models.PositiveIntegerField("排序", default=0)
    is_active = models.BooleanField("启用", default=True)

    class Meta:
        verbose_name = "UI测试用例"
        verbose_name_plural = "UI测试用例"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.name


class UiPage(OwnedModel):
    suite = models.ForeignKey(UiSuite, verbose_name="套件", on_delete=models.CASCADE, related_name="pages")
    parent = models.ForeignKey("self", verbose_name="父级页面", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    name = models.CharField("页面名称", max_length=128)
    path = models.CharField("页面路径", max_length=256, blank=True)
    description = models.TextField("描述", blank=True)
    sort_order = models.PositiveIntegerField("排序", default=0)
    is_active = models.BooleanField("启用", default=True)

    class Meta:
        verbose_name = "UI页面"
        verbose_name_plural = "UI页面"
        unique_together = [("suite", "parent", "name")]
        ordering = ["suite_id", "parent_id", "sort_order", "id"]

    def __str__(self) -> str:
        return self.name


class UiElement(OwnedModel):
    class LocatorType(models.TextChoices):
        CSS = "css", "CSS"
        TEXT = "text", "Text"
        ROLE = "role", "Role"
        XPATH = "xpath", "XPath"
        TEST_ID = "test_id", "TestId"

    suite = models.ForeignKey(UiSuite, verbose_name="套件", null=True, blank=True, on_delete=models.CASCADE, related_name="elements")
    page_node = models.ForeignKey(UiPage, verbose_name="页面节点", null=True, blank=True, on_delete=models.SET_NULL, related_name="elements")
    name = models.CharField("元素名称", max_length=128)
    page = models.CharField("页面", max_length=128, blank=True)
    locator_type = models.CharField("定位方式", max_length=32, choices=LocatorType.choices, default=LocatorType.CSS)
    selector = models.CharField("定位表达式", max_length=512)
    description = models.TextField("描述", blank=True)
    is_active = models.BooleanField("启用", default=True)

    class Meta:
        verbose_name = "UI定位元素"
        verbose_name_plural = "UI定位元素"
        unique_together = [("suite", "name")]
        ordering = ["suite_id", "page", "name"]

    def __str__(self) -> str:
        return self.name


class UiAction(OwnedModel):
    class ActionType(models.TextChoices):
        GOTO = "goto", "打开页面"
        CLICK = "click", "点击"
        FILL = "fill", "输入"
        PRESS = "press", "按键"
        SELECT = "select", "下拉选择"
        CHECK = "check", "勾选"
        UNCHECK = "uncheck", "取消勾选"
        WAIT = "wait", "等待"
        ASSERT_VISIBLE = "assert_visible", "断言可见"
        ASSERT_TEXT = "assert_text", "断言文本"
        ASSERT_URL = "assert_url", "断言 URL"
        SCREENSHOT = "screenshot", "截图"

    name = models.CharField("操作名称", max_length=128)
    action = models.CharField("动作", max_length=32, choices=ActionType.choices, default=ActionType.CLICK)
    default_value = models.CharField("默认输入/期望", max_length=512, blank=True)
    description = models.TextField("描述", blank=True)
    is_active = models.BooleanField("启用", default=True)

    class Meta:
        verbose_name = "UI元素操作"
        verbose_name_plural = "UI元素操作"
        unique_together = [("name", "action")]
        ordering = ["action", "name"]

    def __str__(self) -> str:
        return self.name
