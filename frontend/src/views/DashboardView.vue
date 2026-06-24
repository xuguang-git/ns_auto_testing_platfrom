<template>
  <div>
    <div class="dashboard-welcome system-goal">
      <h2>自动化测试闭环工作台</h2>
      <p>围绕平台维护、模块管理、接口管理、测试计划、执行中心和报告沉淀，支撑“资产维护 -> 计划编排 -> 执行验证 -> 结果追踪”的测试流程。</p>
      <small>{{ todayText }} · 上次登录：昨天 18:32</small>
    </div>

    <div class="stat-row">
      <div v-for="item in metrics" :key="item.label" class="stat-card" :class="item.type">
        <div class="stat-icon">{{ item.icon }}</div>
        <div class="stat-value">{{ item.value }}</div>
        <div class="stat-label">{{ item.label }}</div>
        <div class="stat-trend" :style="{ color: item.trendColor }">{{ item.trend }}</div>
      </div>
    </div>

    <div class="dashboard-two-col">
      <section class="design-card">
        <div class="design-card-header">
          <h3>近 14 天执行趋势</h3>
          <span class="design-card-action" @click="$router.push('/reports')">查看详情 -></span>
        </div>
        <div class="design-card-body">
          <div class="chart-bars">
            <div v-for="item in trend" :key="item.label" class="chart-bar-group">
              <div class="chart-bar-wrap">
                <div class="chart-bar pass" :style="{ height: `${item.pass}%` }" :title="`通过 ${item.pass}`"></div>
                <div v-if="item.fail" class="chart-bar fail" :style="{ height: `${item.fail}%` }" :title="`失败 ${item.fail}`"></div>
              </div>
              <div class="chart-bar-label" :style="item.today ? 'color: var(--brand); font-weight: 600' : ''">{{ item.label }}</div>
            </div>
          </div>
          <div class="chart-legend">
            <span><i class="legend-dot" style="background: var(--brand)"></i>通过</span>
            <span><i class="legend-dot" style="background: var(--danger)"></i>失败</span>
          </div>
        </div>
      </section>

      <section class="design-card">
        <div class="design-card-header">
          <h3>平台通过率</h3>
          <span class="design-card-action" @click="$router.push('/api-testing')">查看详情 -></span>
        </div>
        <div class="design-card-body">
          <div class="platform-grid">
            <div v-for="item in platformCards" :key="item.key" class="platform-card">
              <div class="platform-card-head">
                <span class="platform-card-name">
                  <span class="platform-tag" :class="item.tagClass">{{ item.short }}</span>
                  {{ item.name }}
                </span>
                <span class="platform-rate" :style="{ color: item.color }">{{ item.rate }}%</span>
              </div>
              <div class="platform-card-stats">
                <span style="color: var(--success)">{{ item.passed }} 通过</span>
                <span v-if="item.failed" style="color: var(--danger)">{{ item.failed }} 失败</span>
                <span>总 {{ item.total }}</span>
              </div>
              <div class="platform-bar">
                <div class="platform-bar-fill" :style="{ width: `${item.rate}%`, background: item.color }"></div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <div class="dashboard-two-col">
      <section class="design-card">
        <div class="design-card-header">
          <h3>快速操作</h3>
        </div>
        <div class="design-card-body">
          <div class="quick-grid">
            <button v-for="item in quickActions" :key="item.title" class="quick-item" :class="item.type" @click="$router.push(item.path)">
              <span class="quick-icon">{{ item.icon }}</span>
              <span>
                <span class="quick-title">{{ item.title }}</span>
                <span class="quick-desc">{{ item.desc }}</span>
              </span>
            </button>
          </div>
        </div>
      </section>

      <section class="design-card">
        <div class="design-card-header">
          <h3>最近执行记录</h3>
          <span class="design-card-action" @click="$router.push('/reports')">全部记录 -></span>
        </div>
        <div class="design-card-body">
          <table class="exec-table">
            <thead>
              <tr>
                <th>执行编号</th>
                <th>状态</th>
                <th>通过率</th>
                <th>耗时</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="run in recentRuns" :key="run.id">
                <td>#{{ run.id }}</td>
                <td><span class="badge" :class="statusBadge(run.status)">{{ statusText(run.status) }}</span></td>
                <td>{{ run.summary?.pass_rate || 0 }}%</td>
                <td>{{ run.duration_ms || 0 }}ms</td>
              </tr>
              <tr v-if="!recentRuns.length && !loading">
                <td colspan="4">暂无执行记录</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";

const loading = ref(false);
const apis = ref<any[]>([]);
const environments = ref<any[]>([]);
const runs = ref<any[]>([]);

const latestRun = computed(() => runs.value[0]);
const totalCases = computed(() => apis.value.length || latestRun.value?.summary?.total || 0);
const passRate = computed(() => latestRun.value?.summary?.pass_rate || 0);
const failedToday = computed(() => latestRun.value?.summary?.failed || 0);
const avgDuration = computed(() => latestRun.value?.duration_ms || 218);
const recentRuns = computed(() => runs.value.slice(0, 5));

const todayText = computed(() => {
  const formatter = new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric", weekday: "long" });
  return `今天是 ${formatter.format(new Date())}`;
});

const metrics = computed(() => [
  { type: "total", icon: "☑", value: totalCases.value, label: "用例总数", trend: "较上周 +12", trendColor: "var(--brand)" },
  { type: "pass", icon: "✓", value: `${passRate.value}%`, label: "整体通过率", trend: "▲ 2.3%", trendColor: "var(--success)" },
  { type: "fail", icon: "×", value: failedToday.value, label: "今日失败", trend: "▼ 较昨日 -1", trendColor: "var(--success)" },
  { type: "time", icon: "◷", value: `${avgDuration.value}ms`, label: "平均响应时间", trend: "▼ 12ms", trendColor: "var(--success)" },
]);

const trend = [
  { label: "5/17", pass: 85, fail: 10 },
  { label: "5/18", pass: 92, fail: 4 },
  { label: "5/19", pass: 88, fail: 8 },
  { label: "5/20", pass: 95, fail: 2 },
  { label: "5/21", pass: 90, fail: 6 },
  { label: "5/22", pass: 100, fail: 0 },
  { label: "5/23", pass: 100, fail: 0 },
  { label: "5/24", pass: 96, fail: 2 },
  { label: "5/25", pass: 100, fail: 0 },
  { label: "5/26", pass: 98, fail: 1 },
  { label: "5/27", pass: 100, fail: 0 },
  { label: "5/28", pass: 87, fail: 10 },
  { label: "5/29", pass: 100, fail: 0 },
  { label: "今天", pass: 95, fail: 4, today: true },
];

const platformMeta = [
  { key: "ERP", short: "ERP", name: "ERP 平台", tagClass: "pt-erp", color: "var(--brand)" },
  { key: "WMS", short: "WMS", name: "WMS 平台", tagClass: "pt-wms", color: "var(--success)" },
  { key: "PDA", short: "PDA", name: "PDA 平台", tagClass: "pt-pda", color: "var(--success)" },
  { key: "CLIENT", short: "Client", name: "Client 平台", tagClass: "pt-client", color: "var(--success)" },
];

const platformCards = computed(() =>
  platformMeta.map((item) => {
    const total = apis.value.filter((api) => api.platform === item.key).length || (item.key === "ERP" ? 30 : item.key === "WMS" ? 18 : 10);
    const failed = item.key === "ERP" ? 2 : item.key === "WMS" ? 1 : 0;
    const passed = Math.max(total - failed, 0);
    const rate = total ? Math.round((passed / total) * 1000) / 10 : 0;
    return { ...item, total, failed, passed, rate };
  }),
);

const quickActions = computed(() => [
  { type: "blue", icon: "⌁", title: "接口调试", desc: "调试单个 API 接口", path: "/api-debug" },
  { type: "green", icon: "▶", title: "查看执行报告", desc: `查看全部 ${totalCases.value || 66} 个用例的执行结果`, path: "/reports" },
  { type: "amber", icon: "☑", title: "维护接口资产", desc: "新增、编辑接口定义", path: "/api-testing" },
  { type: "red", icon: "↗", title: "查看失败报告", desc: "定位断言与响应差异", path: "/reports" },
]);

const statusText = (status: string) => ({ passed: "通过", failed: "失败", running: "执行中", pending: "等待中" }[status] || status || "未知");
const statusBadge = (status: string) => {
  if (status === "passed") return "badge-success";
  if (status === "failed") return "badge-danger";
  if (status === "running") return "badge-warning";
  return "badge-gray";
};

onMounted(async () => {
  loading.value = true;
  try {
    const [apiResp, envResp, runResp] = await Promise.all([platformApi.apiDefinitions(), platformApi.environments(), platformApi.testRuns()]);
    apis.value = unwrapList(apiResp.data);
    environments.value = unwrapList(envResp.data);
    runs.value = unwrapList(runResp.data);
  } finally {
    loading.value = false;
  }
});
</script>
