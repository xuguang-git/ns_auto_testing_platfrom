from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import FileResponse, Http404, JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    AuditLogViewSet,
    ChangePasswordView,
    LoginAttemptViewSet,
    LoginCryptoView,
    LoginView,
    LogoutView,
    MeView,
    PermissionViewSet,
    ProfileView,
    RefreshTokenView,
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
from apps.projects.views import (
    DataFactoryCapabilityViewSet,
    DatabaseConnectionViewSet,
    EnvironmentPreRequestOperationViewSet,
    EnvironmentRequestControlViewSet,
    EnvironmentVariableViewSet,
    EnvironmentViewSet,
    PlatformViewSet,
    ProjectViewSet,
    TestDataSourceViewSet,
)
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
router.register("environment-pre-request-operations", EnvironmentPreRequestOperationViewSet)
router.register("environment-request-controls", EnvironmentRequestControlViewSet)
router.register("database-connections", DatabaseConnectionViewSet)
router.register("data-factory-capabilities", DataFactoryCapabilityViewSet)
router.register("test-data-sources", TestDataSourceViewSet)
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


def frontend_index(_request):
    index_path = settings.FRONTEND_DIST_DIR / "index.html"
    if not index_path.exists():
        raise Http404("Frontend build not found. Run npm run build in frontend first.")
    return FileResponse(index_path.open("rb"), content_type="text/html")


def api_not_found(_request, path=""):
    return JsonResponse({"code": 40400, "message": "接口不存在。", "data": None, "errors": {}}, status=404)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/login-crypto/", LoginCryptoView.as_view()),
    path("api/v1/auth/login/", LoginView.as_view()),
    path("api/v1/auth/refresh/", RefreshTokenView.as_view()),
    path("api/v1/auth/logout/", LogoutView.as_view()),
    path("api/v1/auth/me/", MeView.as_view()),
    path("api/v1/profile/", ProfileView.as_view()),
    path("api/v1/profile/password/", ChangePasswordView.as_view()),
    path("api/v1/", include(router.urls)),
    re_path(r"^api/v1/(?P<path>.*)$", api_not_found),
    re_path(r"^assets/(?P<path>.*)$", serve, {"document_root": settings.FRONTEND_DIST_DIR / "assets"}),
    re_path(r"^(?P<path>[^/]+\.(?:ico|png|jpg|jpeg|svg|webp|txt|json|webmanifest))$", serve, {"document_root": settings.FRONTEND_DIST_DIR}),
    re_path(r"^(?!api/|admin/|media/|static/|assets/).*$", frontend_index),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
