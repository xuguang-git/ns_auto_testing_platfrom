import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";
import { ElMessage } from "element-plus";

import MainLayout from "@/layouts/MainLayout.vue";
import { useAuthStore } from "@/stores/auth";

const DISABLED_ROUTE_PATHS = new Set(["/performance-testing"]);
const DEFAULT_AUTH_PATH = "/dashboard";

const firstVisiblePath = (auth: ReturnType<typeof useAuthStore>) => {
  const candidates = [
    { path: "/dashboard", permission: "page.dashboard" },
    { path: "/platforms", permission: "page.platform.maintenance" },
    { path: "/modules", permission: "page.platform.module" },
    { path: "/projects", permission: "page.platform.environment" },
    { path: "/api-testing/apis", permission: "page.api_testing.api" },
    { path: "/api-testing/cases", permission: "page.api_testing.case" },
    { path: "/api-testing/automation", permission: "page.api_testing.automation" },
    { path: "/test-tools/quick-test", permission: "page.data_factory.quick_test" },
    { path: "/test-tools/capabilities", permission: "page.data_factory.capability" },
    { path: "/ui-testing/suites", permission: "page.ui_testing.suite" },
    { path: "/ui-testing/cases", permission: "page.ui_testing.case" },
    { path: "/ui-testing/elements", permission: "page.ui_testing.element" },
    { path: "/reports", permission: "page.config.report" },
    { path: "/scheduling", permission: "page.config.schedule" },
    { path: "/notifications", permission: "page.config.notification" },
    { path: "/notification-templates", permission: "page.config.notification_template" },
    { path: "/database-management", permission: "page.config.database" },
    { path: "/users", permission: "page.permission.user" },
    { path: "/roles", permission: "page.permission.role" },
    { path: "/audit-logs", permission: "page.permission.audit" },
  ];
  return candidates.find((item) => auth.has(item.permission))?.path || "/profile";
};

export const getFirstVisiblePath = () => firstVisiblePath(useAuthStore());
export const defaultAuthPath = DEFAULT_AUTH_PATH;

const routes: RouteRecordRaw[] = [
  { path: "/login", name: "login", component: () => import("@/views/LoginView.vue") },
  {
    path: "/",
    component: MainLayout,
    redirect: () => firstVisiblePath(useAuthStore()),
    children: [
      { path: "dashboard", name: "dashboard", component: () => import("@/views/DashboardView.vue"), meta: { pagePermission: "page.dashboard" } },
      { path: "platforms", name: "platforms", component: () => import("@/views/PlatformListView.vue"), meta: { pagePermission: "page.platform.maintenance" } },
      { path: "modules", name: "modules", component: () => import("@/views/ModuleListView.vue"), meta: { pagePermission: "page.platform.module" } },
      { path: "projects", name: "projects", component: () => import("@/views/ProjectsView.vue"), meta: { pagePermission: "page.platform.environment" } },
      { path: "api-testing", redirect: "/api-testing/apis" },
      { path: "api-testing/apis", name: "apiTestingApis", component: () => import("@/views/ApiTestingWorkbenchView.vue"), meta: { pagePermission: "page.api_testing.api" } },
      { path: "api-testing/cases", name: "apiTestingCases", component: () => import("@/views/ApiTestCaseManagementView.vue"), meta: { pagePermission: "page.api_testing.case" } },
      { path: "api-testing/quick-test", redirect: "/test-tools/quick-test" },
      { path: "api-testing/automation", name: "apiTestingAutomation", component: () => import("@/views/AutomationTestingWorkbenchView.vue"), meta: { pagePermission: "page.api_testing.automation" } },
      { path: "test-tools", redirect: "/test-tools/quick-test" },
      { path: "test-tools/quick-test", name: "testToolsQuickTest", component: () => import("@/views/QuickApiTestView.vue"), meta: { pagePermission: "page.data_factory.quick_test" } },
      { path: "test-tools/capabilities", name: "dataFactoryCapabilities", component: () => import("@/views/DataFactoryCapabilitiesView.vue"), meta: { pagePermission: "page.data_factory.capability" } },
      { path: "ui-testing", redirect: "/ui-testing/suites" },
      { path: "ui-testing/suites", name: "uiTestingSuites", component: () => import("@/views/UiTestingView.vue"), meta: { pagePermission: "page.ui_testing.suite" } },
      { path: "ui-testing/cases", name: "uiTestingCases", component: () => import("@/views/UiCasesView.vue"), meta: { pagePermission: "page.ui_testing.case" } },
      { path: "ui-testing/elements", name: "uiElements", component: () => import("@/views/UiElementsView.vue"), meta: { pagePermission: "page.ui_testing.element" } },
      { path: "performance-testing", name: "performanceTesting", component: () => import("@/views/PerformanceTestingView.vue"), meta: { pagePermission: "page.performance.testing" } },
      { path: "reports", name: "reports", component: () => import("@/views/ReportsView.vue"), meta: { pagePermission: "page.config.report" } },
      { path: "scheduling", name: "scheduling", component: () => import("@/views/SchedulingView.vue"), meta: { pagePermission: "page.config.schedule" } },
      { path: "notifications", name: "notifications", component: () => import("@/views/NotificationManagementView.vue"), meta: { pagePermission: "page.config.notification" } },
      { path: "notification-templates", name: "notificationTemplates", component: () => import("@/views/NotificationTemplateView.vue"), meta: { pagePermission: "page.config.notification_template" } },
      { path: "database-management", name: "databaseManagement", component: () => import("@/views/DatabaseManagementView.vue"), meta: { pagePermission: "page.config.database" } },
      { path: "users", name: "users", component: () => import("@/views/UserManagementView.vue"), meta: { pagePermission: "page.permission.user" } },
      { path: "roles", name: "roles", component: () => import("@/views/RoleManagementView.vue"), meta: { pagePermission: "page.permission.role" } },
      { path: "audit-logs", name: "auditLogs", component: () => import("@/views/AuditLogView.vue"), meta: { pagePermission: "page.permission.audit" } },
      { path: "profile", name: "profile", component: () => import("@/views/ProfileView.vue") },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (!auth.checked) {
    try {
      await auth.loadMe();
    } catch {
      auth.user = null;
      auth.checked = true;
    }
  }
  if (to.path !== "/login" && !auth.isAuthenticated) return { path: "/login", query: { redirect: to.fullPath } };
  if (to.path === "/login" && auth.isAuthenticated) return firstVisiblePath(auth);
  const pagePermission = to.meta.pagePermission as string | undefined;
  if (pagePermission && !auth.has(pagePermission)) {
    ElMessage.warning("当前账号没有该页面访问权限");
    return firstVisiblePath(auth);
  }
  if (DISABLED_ROUTE_PATHS.has(to.path)) {
    ElMessage.warning("性能测试功能暂时关闭");
    return firstVisiblePath(auth);
  }
  return true;
});

export default router;
