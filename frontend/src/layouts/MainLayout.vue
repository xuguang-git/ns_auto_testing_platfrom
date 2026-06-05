<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <RouterLink class="brand" to="/dashboard">
        <span class="brand-mark brand-image"><img src="/system-icon.jpg" alt="NS" /></span>
        <span class="brand-name">NS-ATP</span>
        <span class="brand-version">v2.0</span>
      </RouterLink>

      <nav class="side-nav grouped-nav">
        <section v-for="group in navGroups" :key="group.key" class="menu-group" :class="{ collapsed: collapsedGroups.includes(group.key) }">
          <button class="menu-group-header" @click="toggleGroup(group.key)">
            <span class="menu-group-title">
              <span class="menu-group-icon" v-html="group.icon"></span>
              <span>{{ group.label }}</span>
            </span>
            <span class="mgh-arrow" v-html="icons.chevron"></span>
          </button>
          <div class="menu-group-body">
            <RouterLink v-for="item in group.items" :key="item.path" class="side-nav-item" :class="{ disabled: item.disabled }" :to="item.disabled ? route.path : item.path">
              <span class="side-icon" v-html="item.icon"></span>
              <span>{{ item.label }}</span>
              <span v-if="item.tag" class="mi-tag">{{ item.tag }}</span>
            </RouterLink>
          </div>
        </section>
      </nav>

      <el-dropdown trigger="click" placement="top-start" @command="handleUserCommand">
        <button class="sidebar-footer user-menu-trigger">
          <div class="sidebar-avatar">{{ userInitial }}</div>
          <div class="sidebar-user-info">
            <div class="name">{{ auth.user?.nickname || auth.user?.username || "-" }}</div>
            <div class="role">{{ auth.user?.role_name || "-" }}</div>
          </div>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">个人中心</el-dropdown-item>
            <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </aside>

    <section class="app-main">
      <header class="app-header">
        <div class="breadcrumb">{{ activeItem.section }} / <span>{{ activeItem.label }}</span></div>
        <div class="header-tools">
          <RouterLink class="dashboard-link" to="/dashboard">首页概览</RouterLink>
          <div class="header-env">
            <span class="dot"></span>
            <el-select v-model="currentEnv" class="env-switcher" size="small" teleported>
              <el-option label="测试环境" value="test" />
              <el-option label="开发环境" value="dev" />
              <el-option label="预发环境" value="staging" />
              <el-option label="生产环境(只读)" value="prod" />
            </el-select>
          </div>
          <el-dropdown trigger="click" @command="handleUserCommand">
            <button class="header-avatar user-menu-trigger">{{ userInitial }}</button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <main class="content">
        <RouterView />
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

interface NavItem {
  label: string;
  path: string;
  icon: string;
  section: string;
  tag?: string;
  disabled?: boolean;
}

interface NavGroup {
  key: string;
  label: string;
  icon: string;
  items: NavItem[];
}

const currentEnv = ref("test");
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const collapsedGroups = ref<string[]>([]);

const svg = (path: string) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;
const icons = {
  platform: svg('<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>'),
  module: svg('<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h10"/>'),
  environment: svg('<circle cx="12" cy="12" r="3"/><path d="M12 1v4"/><path d="M12 19v4"/><path d="M4.22 4.22l2.83 2.83"/><path d="M16.95 16.95l2.83 2.83"/><path d="M1 12h4"/><path d="M19 12h4"/>'),
  api: svg('<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'),
  case: svg('<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>'),
  quick: svg('<path d="M13 2 3 14h8l-1 8 10-12h-8l1-8z"/>'),
  automation: svg('<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V5s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/>'),
  ui: svg('<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>'),
  report: svg('<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>'),
  schedule: svg('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'),
  user: svg('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6"/><path d="M22 11h-6"/>'),
  role: svg('<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0"/><circle cx="12" cy="12" r="3"/>'),
  audit: svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8"/><path d="M8 17h8"/>'),
  groupUser: svg('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'),
  groupPlatform: svg('<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/>'),
  groupApi: svg('<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M8.12 8.12 12 12"/><path d="M14.8 14.8 20 20"/><path d="M20 4 8.12 15.88"/>'),
  groupUi: svg('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/>'),
  groupConfig: svg('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4"/>'),
  chevron: svg('<polyline points="6 9 12 15 18 9"/>'),
};

const navGroups: NavGroup[] = [
  {
    key: "platform",
    label: "平台管理",
    icon: icons.groupPlatform,
    items: [
      { label: "平台维护", path: "/platforms", icon: icons.platform, section: "平台管理" },
      { label: "模块管理", path: "/modules", icon: icons.module, section: "平台管理" },
      { label: "环境管理", path: "/projects", icon: icons.environment, section: "平台管理" },
    ],
  },
  {
    key: "api",
    label: "接口测试",
    icon: icons.groupApi,
    items: [
      { label: "接口管理", path: "/api-testing/apis", icon: icons.api, section: "接口测试" },
      { label: "测试用例", path: "/api-testing/cases", icon: icons.case, section: "接口测试" },
      { label: "自动化测试", path: "/api-testing/automation", icon: icons.automation, section: "接口测试" },
    ],
  },
  {
    key: "tools",
    label: "数据工厂",
    icon: icons.quick,
    items: [
      { label: "快速测试", path: "/test-tools/quick-test", icon: icons.quick, section: "数据工厂" },
      { label: "能力列表", path: "/test-tools/capabilities", icon: icons.case, section: "数据工厂" },
    ],
  },
  {
    key: "ui",
    label: "UI测试",
    icon: icons.groupUi,
    items: [
      { label: "测试套件", path: "/ui-testing/suites", icon: icons.ui, section: "UI测试" },
      { label: "测试用例", path: "/ui-testing/cases", icon: icons.case, section: "UI测试" },
      { label: "定位元素", path: "/ui-testing/elements", icon: icons.case, section: "UI测试" },
    ],
  },
  {
    key: "user",
    label: "权限管理",
    icon: icons.groupUser,
    items: [
      { label: "用户管理", path: "/users", icon: icons.user, section: "权限管理" },
      { label: "角色管理", path: "/roles", icon: icons.role, section: "权限管理" },
      { label: "审计日志", path: "/audit-logs", icon: icons.audit, section: "权限管理" },
    ],
  },
  {
    key: "config",
    label: "配置管理",
    icon: icons.groupConfig,
    items: [
      { label: "测试报告", path: "/reports", icon: icons.report, section: "配置管理" },
      { label: "定时调度", path: "/scheduling", icon: icons.schedule, section: "配置管理" },
    ],
  },
];

const allItems = navGroups.flatMap((group) => group.items);
const activeItem = computed(() => allItems.find((item) => item.path === route.path) || { label: "首页概览", section: "首页" });
const userInitial = computed(() => (auth.user?.nickname || auth.user?.username || "U").slice(0, 1).toUpperCase());

const toggleGroup = (key: string) => {
  collapsedGroups.value = collapsedGroups.value.includes(key)
    ? collapsedGroups.value.filter((item) => item !== key)
    : [...collapsedGroups.value, key];
};

const logout = async () => {
  await auth.logout();
  await router.push("/login");
};

const handleUserCommand = async (command: string) => {
  if (command === "profile") {
    await router.push("/profile");
    return;
  }
  if (command === "logout") await logout();
};

onMounted(() => {
  if (!auth.user) auth.loadMe();
});
</script>
