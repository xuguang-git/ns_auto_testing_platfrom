import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";
import { ElMessage } from "element-plus";

import MainLayout from "@/layouts/MainLayout.vue";
import { useAuthStore } from "@/stores/auth";

const DISABLED_ROUTE_PATHS = new Set(["/performance-testing"]);

const routes: RouteRecordRaw[] = [
  { path: "/login", name: "login", component: () => import("@/views/LoginView.vue") },
  {
    path: "/",
    component: MainLayout,
    redirect: "/dashboard",
    children: [
      { path: "dashboard", name: "dashboard", component: () => import("@/views/DashboardView.vue") },
      { path: "platforms", name: "platforms", component: () => import("@/views/PlatformListView.vue") },
      { path: "modules", name: "modules", component: () => import("@/views/ModuleListView.vue") },
      { path: "projects", name: "projects", component: () => import("@/views/ProjectsView.vue") },
      { path: "api-testing", redirect: "/api-testing/apis" },
      { path: "api-testing/apis", name: "apiTestingApis", component: () => import("@/views/ApiTestingWorkbenchView.vue") },
      { path: "api-testing/cases", name: "apiTestingCases", component: () => import("@/views/ApiTestCaseManagementView.vue") },
      { path: "api-testing/quick-test", redirect: "/test-tools/quick-test" },
      { path: "api-testing/automation", name: "apiTestingAutomation", component: () => import("@/views/AutomationTestingWorkbenchView.vue") },
      { path: "test-tools", redirect: "/test-tools/quick-test" },
      { path: "test-tools/quick-test", name: "testToolsQuickTest", component: () => import("@/views/QuickApiTestView.vue") },
      { path: "test-tools/capabilities", name: "dataFactoryCapabilities", component: () => import("@/views/DataFactoryCapabilitiesView.vue") },
      { path: "api-debug", name: "apiDebug", component: () => import("@/views/ApiDebugView.vue") },
      { path: "ui-testing", redirect: "/ui-testing/suites" },
      { path: "ui-testing/suites", name: "uiTestingSuites", component: () => import("@/views/UiTestingView.vue") },
      { path: "ui-testing/cases", name: "uiTestingCases", component: () => import("@/views/UiCasesView.vue") },
      { path: "ui-testing/elements", name: "uiElements", component: () => import("@/views/UiElementsView.vue") },
      { path: "performance-testing", name: "performanceTesting", component: () => import("@/views/PerformanceTestingView.vue") },
      { path: "reports", name: "reports", component: () => import("@/views/ReportsView.vue") },
      { path: "scheduling", name: "scheduling", component: () => import("@/views/SchedulingView.vue") },
      { path: "notifications", name: "notifications", component: () => import("@/views/NotificationManagementView.vue") },
      { path: "notification-templates", name: "notificationTemplates", component: () => import("@/views/NotificationTemplateView.vue") },
      { path: "database-management", name: "databaseManagement", component: () => import("@/views/DatabaseManagementView.vue") },
      { path: "users", name: "users", component: () => import("@/views/UserManagementView.vue") },
      { path: "roles", name: "roles", component: () => import("@/views/RoleManagementView.vue") },
      { path: "audit-logs", name: "auditLogs", component: () => import("@/views/AuditLogView.vue") },
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
  if (to.path === "/login" && auth.isAuthenticated) return "/dashboard";
  if (DISABLED_ROUTE_PATHS.has(to.path)) {
    ElMessage.warning("性能测试功能暂时关闭");
    return "/dashboard";
  }
  return true;
});

export default router;
