from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    AuditLogViewSet,
    ChangePasswordView,
    LoginAttemptViewSet,
    LoginView,
    LogoutView,
    MeView,
    PermissionViewSet,
    ProfileView,
    RoleViewSet,
    UserSessionViewSet,
    UserViewSet,
)
from apps.api_testing.views import (
    ApiCaseViewSet,
    ApiDefinitionViewSet,
    ApiMockRuleViewSet,
    ApiModuleViewSet,
    ApiScenarioViewSet,
    ApiStepViewSet,
    ApiSuiteViewSet,
    ApiTestCaseViewSet,
)
from apps.performance_testing.views import ExecutorCheckViewSet, JMeterScriptViewSet, PerformanceRunViewSet, PerformanceTaskViewSet
from apps.projects.views import DataFactoryCapabilityViewSet, EnvironmentVariableViewSet, EnvironmentViewSet, PlatformViewSet, ProjectViewSet
from apps.scheduling.views import ScheduledPlanViewSet
from apps.test_runs.views import TestPlanViewSet, TestRunViewSet
from apps.ui_testing.views import UiActionViewSet, UiCaseViewSet, UiElementViewSet, UiPageViewSet, UiSuiteViewSet


router = DefaultRouter()
router.register("users", UserViewSet)
router.register("roles", RoleViewSet)
router.register("permissions", PermissionViewSet)
router.register("audit-logs", AuditLogViewSet)
router.register("login-attempts", LoginAttemptViewSet)
router.register("profile/devices", UserSessionViewSet, basename="profile-devices")
router.register("projects", ProjectViewSet)
router.register("platforms", PlatformViewSet)
router.register("environments", EnvironmentViewSet)
router.register("environment-variables", EnvironmentVariableViewSet)
router.register("data-factory-capabilities", DataFactoryCapabilityViewSet)
router.register("api-modules", ApiModuleViewSet)
router.register("api-definitions", ApiDefinitionViewSet)
router.register("api-test-cases", ApiTestCaseViewSet)
router.register("api-mock-rules", ApiMockRuleViewSet)
router.register("api-suites", ApiSuiteViewSet)
router.register("api-scenarios", ApiScenarioViewSet)
router.register("api-steps", ApiStepViewSet)
router.register("api-cases", ApiCaseViewSet)
router.register("ui-suites", UiSuiteViewSet)
router.register("ui-cases", UiCaseViewSet)
router.register("ui-elements", UiElementViewSet)
router.register("ui-pages", UiPageViewSet)
router.register("ui-actions", UiActionViewSet)
router.register("test-plans", TestPlanViewSet)
router.register("test-runs", TestRunViewSet)
router.register("scheduled-plans", ScheduledPlanViewSet)
router.register("performance/executor", ExecutorCheckViewSet, basename="performance-executor")
router.register("performance/scripts", JMeterScriptViewSet)
router.register("performance/tasks", PerformanceTaskViewSet)
router.register("performance/runs", PerformanceRunViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/login/", LoginView.as_view()),
    path("api/v1/auth/logout/", LogoutView.as_view()),
    path("api/v1/auth/me/", MeView.as_view()),
    path("api/v1/profile/", ProfileView.as_view()),
    path("api/v1/profile/password/", ChangePasswordView.as_view()),
    path("api/v1/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
