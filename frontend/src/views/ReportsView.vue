<template>
  <div class="report-layout">
    <aside class="report-list-panel">
      <div class="report-list-header">
        <strong>报告列表</strong>
        <span>共 {{ runs.length }} 份</span>
      </div>
      <el-input v-model="keyword" placeholder="搜索报告名称或套件名称" clearable class="report-search" />
      <button
        v-for="run in filteredRuns"
        :key="run.id"
        class="report-item"
        :class="{ active: selectedRun?.id === run.id }"
        @click="selectRunFromList(run)"
      >
        <div class="report-item-head">
          <strong>{{ reportName(run) }}</strong>
          <span>{{ runStatusText(run.status) }}</span>
        </div>
        <div class="report-item-stats">套件：{{ run.suite_name || "-" }}</div>
        <div class="report-item-time">{{ formatDateTime(run.started_at || run.created_at) }}</div>
        <div class="report-result-bar" :title="resultBarTitle(run)">
          <span class="passed" :style="{ width: resultPercent(run, 'passed') }"></span>
          <span class="failed" :style="{ width: resultPercent(run, 'failed') }"></span>
        </div>
        <div class="report-item-stats">
          通过 {{ run.summary?.passed || 0 }} / 失败 {{ run.summary?.failed || 0 }} / 总数 {{ run.summary?.total || 0 }}
        </div>
      </button>
    </aside>

    <section v-if="selectedRun" class="report-detail">
      <div class="report-header-card">
        <div>
          <h2>{{ reportName(selectedRun) }}</h2>
          <div class="report-run-meta">
            <span :class="['report-meta-pill', runStatusClass(selectedRun.status)]"><b>状态</b>{{ runStatusText(selectedRun.status) }}</span>
            <span class="report-meta-pill"><b>触发方式</b>{{ triggerTypeText(selectedRun.trigger_type) }}</span>
            <span class="report-meta-pill"><b>总耗时</b>{{ selectedRun.duration_ms || 0 }}ms</span>
          </div>
        </div>
        <div class="pass-circle">{{ selectedRun.summary?.pass_rate || 0 }}%</div>
      </div>

      <div class="stats-row">
        <div><strong>{{ selectedRun.summary?.total || 0 }}</strong><span>总数</span></div>
        <div><strong>{{ selectedRun.summary?.passed || 0 }}</strong><span>通过</span></div>
        <div><strong>{{ selectedRun.summary?.failed || 0 }}</strong><span>失败</span></div>
        <div><strong>{{ selectedRun.summary?.skipped || 0 }}</strong><span>跳过</span></div>
      </div>

      <div class="report-step-groups">
        <section v-for="group in stepGroups" :key="group.name" class="report-step-group" :class="{ collapsed: isGroupCollapsed(group) }">
          <header class="report-step-group-head" @click="toggleGroup(group)">
            <div>
              <strong><span class="group-toggle">{{ isGroupCollapsed(group) ? "›" : "⌄" }}</span>{{ group.name }}</strong>
              <span v-if="groupSubText(group)" class="group-subtext">{{ groupSubText(group) }}</span>
            </div>
            <div class="report-step-group-meta">
              <span>耗时 {{ group.duration_ms || 0 }}ms</span>
              <span>接口 {{ group.interface_count || 0 }}</span>
              <span v-if="isSingleApiGroup(group)">通过率 {{ groupPassRate(group) }}%</span>
              <span v-else :class="['group-result', groupResultClass(group)]">{{ groupResultText(group) }}</span>
            </div>
          </header>

          <el-table v-show="!isGroupCollapsed(group)" :data="group.steps || []" stripe>
            <el-table-column label="#" width="70">
              <template #default="{ $index }">{{ $index + 1 }}</template>
            </el-table-column>
            <el-table-column label="步骤" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">
                <el-button link type="primary" class="step-link" @click="openStepDetail(row)">{{ row.step_name || "-" }}</el-button>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <span class="report-step-status" :class="stepStatusClass(row.status)">{{ stepStatusText(row.status) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="duration_ms" label="耗时(ms)" width="120" />
            <el-table-column label="接口错误" min-width="240" show-overflow-tooltip>
              <template #default="{ row }">{{ stepErrorText(row) || "-" }}</template>
            </el-table-column>
          </el-table>
        </section>
      </div>
    </section>
    <el-empty v-else :description="emptyReportText" style="flex: 1" />

    <el-drawer v-model="stepDrawerVisible" direction="btt" size="72%" :with-header="false" destroy-on-close>
      <ApiCaseDebugDrawerContent
        v-if="activeStep"
        title="执行结果"
        :case-name="activeStep.step_name || '步骤详情'"
        :request="stepRequest(activeStep)"
        :result="stepResult(activeStep)"
        :environment-name="selectedRun?.environment_name || '-'"
        :show-run="false"
        @close="stepDrawerVisible = false"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { platformApi, unwrapList } from "@/api/platform";
import ApiCaseDebugDrawerContent from "@/components/ApiCaseDebugDrawerContent.vue";

const loading = ref(false);
const keyword = ref("");
const runs = ref<any[]>([]);
const selectedRun = ref<any>();
const route = useRoute();
const router = useRouter();
const stepDrawerVisible = ref(false);
const activeStep = ref<any>();
const expandedGroups = ref<Set<string>>(new Set());

const reportName = (run: any) => run.report_name || `${run.suite_name || "测试报告"}${formatCompactTime(run.started_at || run.created_at) || run.id}`;
const filteredRuns = computed(() => {
  const value = keyword.value.trim().toLowerCase();
  if (!value) return runs.value;
  return runs.value.filter((run) => {
    const name = reportName(run).toLowerCase();
    const suiteName = String(run.suite_name || "").toLowerCase();
    return name.includes(value) || suiteName.includes(value) || String(run.id).includes(value);
  });
});
const stepGroups = computed(() => selectedRun.value?.step_groups?.length ? selectedRun.value.step_groups : fallbackStepGroups(selectedRun.value?.steps || []));
const emptyReportText = computed(() => routeRunId.value ? "报告不存在或已被删除" : "暂无报告");

const runStatusText = (status: string) => ({ pending: "待执行", running: "执行中", completed: "完成", failed: "失败" }[status] || status || "未知");
const runStatusClass = (status: string) => ({ completed: "success", failed: "danger", running: "warning", pending: "muted" }[status] || "muted");
const stepStatusText = (status: string) => ({ pending: "待执行", running: "执行中", passed: "通过", failed: "失败", skipped: "跳过" }[status] || status || "未知");
const triggerTypeText = (type: string) => ({ manual: "手动", schedule: "定时", webhook: "Webhook" }[type] || type || "未知");
const formatDateTime = (value?: string) => value ? value.replace("T", " ").slice(0, 19) : "";
const formatCompactTime = (value?: string) => formatDateTime(value).replace(/[-:\s]/g, "");
const stepStatusClass = (status: string) => ({ passed: "passed", failed: "failed", skipped: "skipped", running: "running", pending: "pending" }[status] || "pending");
const resultCount = (run: any, key: "passed" | "failed" | "skipped") => Number(run?.summary?.[key] || 0);
const resultTotal = (run: any) => Math.max(Number(run?.summary?.total || 0), resultCount(run, "passed") + resultCount(run, "failed") + resultCount(run, "skipped"));
const resultPercent = (run: any, key: "passed" | "failed") => {
  const total = resultTotal(run);
  return total ? `${(resultCount(run, key) / total) * 100}%` : "0%";
};
const resultBarTitle = (run: any) => `通过 ${resultCount(run, "passed")} / 失败 ${resultCount(run, "failed")} / 总数 ${resultTotal(run)}`;

const isSingleApiGroup = (group: any) => group.name === "单接口用例";
const groupSubText = (group: any) => {
  if (isSingleApiGroup(group)) return "";
  return `通过 ${group.passed || 0} / 失败 ${group.failed || 0} / 跳过 ${group.skipped || 0}`;
};
const groupPassRate = (group: any) => {
  if (group.pass_rate !== undefined && group.pass_rate !== null) return group.pass_rate;
  const total = Number(group.interface_count || 0);
  return total ? Number(((Number(group.passed || 0) / total) * 100).toFixed(2)) : 0;
};
const groupResult = (group: any) => group.result || (Number(group.failed || 0) > 0 ? "failed" : "success");
const groupResultText = (group: any) => groupResult(group) === "failed" ? "失败" : "成功";
const groupResultClass = (group: any) => groupResult(group) === "failed" ? "failed" : "success";
const groupKey = (group: any) => group.name || "未命名分组";
const isGroupCollapsed = (group: any) => !expandedGroups.value.has(groupKey(group));
const toggleGroup = (group: any) => {
  const next = new Set(expandedGroups.value);
  const key = groupKey(group);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  expandedGroups.value = next;
};

const fallbackStepGroups = (steps: any[]) => {
  const groups = new Map<string, any>();
  for (const step of steps) {
    const name = step.scenario_name || "单接口用例";
    if (!groups.has(name)) {
      groups.set(name, { name, duration_ms: 0, interface_count: 0, passed: 0, failed: 0, skipped: 0, result: "success", pass_rate: 0, success_rate: 0, steps: [] });
    }
    const group = groups.get(name);
    group.duration_ms += Number(step.duration_ms || 0);
    group.interface_count += 1;
    if (step.status === "passed") group.passed += 1;
    else if (step.status === "failed") group.failed += 1;
    else if (step.status === "skipped") group.skipped += 1;
    group.steps.push(step);
  }
  for (const group of groups.values()) {
    group.pass_rate = group.interface_count ? Number(((group.passed / group.interface_count) * 100).toFixed(2)) : 0;
    group.success_rate = group.pass_rate;
    group.result = group.failed > 0 ? "failed" : "success";
  }
  return Array.from(groups.values());
};

const firstText = (...values: unknown[]) => {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
    if (typeof value === "number") return String(value);
  }
  return "";
};

const stepErrorText = (step: any) => {
  if (step?.status !== "failed") return "";
  const body = step?.response?.body;
  return firstText(
    body?.message,
    body?.error,
    body?.detail,
    step?.response?.message,
    step?.response?.error,
    step?.response?.text,
    step?.error_message,
  );
};

const stepRequest = (step: any) => {
  const request = step?.request || {};
  const responseRequest = step?.response?.request || {};
  const requestBody = request.body
    ?? request.json
    ?? request.data
    ?? request.payload
    ?? request.request_body
    ?? request.body_text
    ?? responseRequest.body
    ?? responseRequest.json
    ?? responseRequest.data
    ?? responseRequest.payload;
  return {
    platform: request.platform || selectedRun.value?.suite_name || "-",
    method: request.method || responseRequest.method || "-",
    path: request.path || request.url || responseRequest.path || responseRequest.url || "-",
    query_params: request.query_params || request.params || request.query || responseRequest.query_params || responseRequest.params || {},
    headers: request.headers || responseRequest.headers || {},
    body: requestBody,
    auth_config: request.auth_config || {},
    assertions: step?.assertions || request.assertions || [],
  };
};

const stepResult = (step: any) => ({
  ok: step?.status === "passed",
  response: step?.response || {},
  assertions: step?.assertions || [],
  logs: step?.logs || [],
});

const openStepDetail = (step: any) => {
  activeStep.value = step;
  stepDrawerVisible.value = true;
};

const routeRunId = computed(() => {
  const value = Array.isArray(route.query.run) ? route.query.run[0] : route.query.run;
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : undefined;
});

const selectRun = (run?: any) => {
  selectedRun.value = run;
  expandedGroups.value = new Set();
};

const resolveSelectedRun = async () => {
  const targetId = routeRunId.value;
  if (!targetId) {
    selectRun(runs.value[0]);
    return;
  }

  const localRun = runs.value.find((item) => item.id === targetId);
  if (localRun) {
    selectRun(localRun);
    return;
  }

  try {
    const { data } = await platformApi.testRun(targetId);
    runs.value = [data, ...runs.value.filter((item) => item.id !== data.id)];
    selectRun(data);
  } catch {
    selectRun(undefined);
  }
};

const selectRunFromList = (run: any) => {
  selectRun(run);
  router.replace({ path: route.path, query: { ...route.query, run: String(run.id) } });
};

const loadRuns = async () => {
  loading.value = true;
  try {
    const { data } = await platformApi.testRuns();
    runs.value = unwrapList(data);
    await resolveSelectedRun();
  } finally {
    loading.value = false;
  }
};

watch(() => route.query.run, () => {
  if (!loading.value) resolveSelectedRun();
});

onMounted(loadRuns);
</script>
