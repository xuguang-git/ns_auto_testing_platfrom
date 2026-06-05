import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";

import MainLayout from "@/layouts/MainLayout.vue";

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
      { path: "test-plans", name: "testPlans", component: () => import("@/views/TestPlansView.vue") },
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
      { path: "test-runs", name: "testRuns", component: () => import("@/views/TestRunsView.vue") },
      { path: "reports", name: "reports", component: () => import("@/views/ReportsView.vue") },
      { path: "scheduling", name: "scheduling", component: () => import("@/views/SchedulingView.vue") },
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

router.beforeEach((to) => {
  const token = localStorage.getItem("ns_token") || sessionStorage.getItem("ns_token");
  if (to.path !== "/login" && !token) return { path: "/login", query: { redirect: to.fullPath } };
  if (to.path === "/login" && token) return "/dashboard";
  return true;
});

export default router;
