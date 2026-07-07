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

      <section class="report-diagnosis-card" :class="{ muted: !reportHasFailureAttribution }">
        <div>
          <strong>报告归因</strong>
          <p>{{ reportDiagnosisText }}</p>
        </div>
        <div class="report-diagnosis-tags">
          <span v-for="item in reportFailureTypeItems" :key="item.type">{{ failureTypeLabel(item.type) }} {{ item.count }}</span>
          <span v-if="reportDiagnosis.environment_issue_count">疑似环境问题 {{ reportDiagnosis.environment_issue_count }}</span>
          <span v-if="reportDiagnosis.retry_suggested_count">建议重试 {{ reportDiagnosis.retry_suggested_count }}</span>
          <span v-if="selectedRunFailedCount === 0">无失败</span>
          <span v-else-if="!reportHasFailureAttribution">待新执行沉淀</span>
        </div>
      </section>

      <section class="report-diagnosis-board">
        <div class="report-diagnosis-panel">
          <div class="panel-title">
            <strong>失败原因分布</strong>
            <span>{{ selectedRunFailedCount ? `${selectedRunFailedCount} 个失败步骤` : "本次无失败" }}</span>
          </div>
          <div v-if="reportFailureTypeRows.length" class="diagnosis-dist-list">
            <div v-for="item in reportFailureTypeRows" :key="item.type" class="diagnosis-dist-row">
              <span>{{ failureTypeLabel(item.type) }}</span>
              <div class="diagnosis-dist-track"><i :style="{ width: item.percent + '%' }"></i></div>
              <b>{{ item.count }}</b>
            </div>
          </div>
          <el-empty v-else description="暂无失败原因分布" :image-size="72" />
        </div>
        <div class="report-diagnosis-panel">
          <div class="panel-title">
            <strong>建议处理方向</strong>
            <span>{{ reportDiagnosisActionLabel }}</span>
          </div>
          <div class="diagnosis-action-list">
            <div v-for="item in reportDiagnosisActions" :key="item.title" class="diagnosis-action-item">
              <b>{{ item.title }}</b>
              <span>{{ item.text }}</span>
            </div>
          </div>
        </div>
      </section>

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
            <el-table-column label="失败类型" width="130">
              <template #default="{ row }">
                <span v-if="stepDiagnosis(row).failure_type" class="diagnosis-type-tag">{{ stepDiagnosis(row).failure_label || failureTypeLabel(stepDiagnosis(row).failure_type) }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
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
const storedReportDiagnosis = computed(() => selectedRun.value?.summary?.diagnosis || selectedRun.value?.report?.diagnosis || {});
const reportDiagnosis = computed(() => {
  if (Object.keys(storedReportDiagnosis.value || {}).length) return storedReportDiagnosis.value;
  return deriveReportDiagnosisFromSteps(stepGroups.value.flatMap((group: any) => group.steps || []));
});
const reportFailureTypeItems = computed(() => Object.entries(reportDiagnosis.value.failure_type_counts || {}).map(([type, count]) => ({ type, count: Number(count || 0) })).filter((item) => item.count > 0));
const reportFailureTypeRows = computed(() => {
  const max = Math.max(...reportFailureTypeItems.value.map((item) => item.count), 1);
  return reportFailureTypeItems.value.map((item) => ({ ...item, percent: Math.max(8, Math.round((item.count / max) * 100)) }));
});
const selectedRunFailedCount = computed(() => Number(selectedRun.value?.summary?.failed || 0));
const reportHasFailureAttribution = computed(() => reportFailureTypeItems.value.length > 0 || Number(reportDiagnosis.value.environment_issue_count || 0) > 0 || Number(reportDiagnosis.value.retry_suggested_count || 0) > 0);
const reportDiagnosisActionLabel = computed(() => selectedRunFailedCount.value ? "按失败类型优先处理" : "无需处理");
const reportDiagnosisActions = computed(() => {
  if (selectedRunFailedCount.value === 0) {
    return [
      { title: "执行结果正常", text: "本次套件全部通过，报告归因区保留展示，便于出现失败时直接查看诊断沉淀。" },
      { title: "持续观察趋势", text: "后续可结合定时任务结果查看同一套件的失败类型变化。" },
    ];
  }
  if (!reportHasFailureAttribution.value) {
    return [
      { title: "重新执行沉淀", text: "历史报告缺少诊断字段，重新执行后会写入步骤级归因和报告级汇总。" },
      { title: "先看步骤错误", text: "可先在步骤明细中查看接口错误摘要，判断是否为环境、鉴权或断言问题。" },
    ];
  }
  const top = reportDiagnosis.value.top_failure_type;
  return [
    { title: top ? `优先处理：${failureTypeLabel(top)}` : "优先处理高频失败", text: "先处理数量最多的失败类型，再重跑受影响用例，避免被次要失败干扰。" },
    { title: "需要重试判断", text: Number(reportDiagnosis.value.retry_suggested_count || 0) > 0 ? "存在网络、超时或服务异常类失败，修复或恢复后建议重试。" : "当前归因未提示必须重试，优先检查配置、断言或业务响应。" },
  ];
});
const reportDiagnosisText = computed(() => {
  if (selectedRunFailedCount.value === 0) return "本次报告全部通过，无需进行失败归因。若后续出现失败，系统会按环境、前置、鉴权、断言、网络和服务异常等维度生成归因摘要。";
  if (!reportHasFailureAttribution.value) return "当前报告存在失败步骤，但历史数据未保存归因明细。重新执行后会自动沉淀环境、前置、鉴权、断言和网络等归因信息。";
  const top = reportDiagnosis.value.top_failure_type;
  if (top) return `主要失败原因：${failureTypeLabel(top)}。建议优先处理数量最多的失败类型，再重跑受影响用例。`;
  return "本次执行存在失败归因数据，请查看步骤明细定位具体原因。";
});

const failureTypeText: Record<string, string> = {
  auth_error: "鉴权失败",
  assertion_failed: "断言失败",
  server_error: "服务异常",
  client_error: "请求错误",
  network_error: "网络不可达",
  connection_error: "网络不可达",
  ssl_error: "证书异常",
  connect_timeout: "连接超时",
  read_timeout: "响应超时",
  timeout: "请求超时",
  pre_request_error: "前置失败",
  data_prepare_error: "数据准备失败",
  request_blocked: "请求拦截",
  case_config_error: "配置错误",
  unknown_error: "未分类",
};
const failureTypeLabel = (type?: string) => type ? (failureTypeText[type] || type) : "-";
const stepDiagnosis = (step: any) => step?.response?.diagnosis || deriveStepDiagnosis(step);

const deriveStepDiagnosis = (step: any) => {
  if (step?.status !== "failed") return {};
  const response = step?.response || {};
  const statusCode = Number(response.status_code || response.status || response.http_status || 0);
  const errorText = stepErrorText(step);
  const sourceText = `${errorText} ${response.error || ""} ${response.message || ""}`.toLowerCase();
  let failureType = "unknown_error";
  if (statusCode === 401 || statusCode === 403 || /auth|token|鉴权|认证|授权|登录/.test(sourceText)) failureType = "auth_error";
  else if (statusCode >= 500) failureType = "server_error";
  else if (statusCode >= 400) failureType = "client_error";
  else if (/assert|断言|expect/.test(sourceText) || (step?.assertions || []).some((item: any) => item?.passed === false)) failureType = "assertion_failed";
  else if (/前置|pre[-_\s]?request/.test(sourceText)) failureType = "pre_request_error";
  else if (/数据源|数据库|sql|database|mysql|postgres/.test(sourceText)) failureType = "data_prepare_error";
  else if (/ssl|证书|certificate/.test(sourceText)) failureType = "ssl_error";
  else if (/timeout|timed out|超时/.test(sourceText)) failureType = "timeout";
  else if (/network|connect|dns|连接|无法访问|不可达/.test(sourceText)) failureType = "network_error";
  return {
    failure_type: failureType,
    failure_label: failureTypeLabel(failureType),
    summary: errorText || "历史报告未保存诊断详情，已根据状态和错误摘要做轻量归类。",
  };
};

const deriveReportDiagnosisFromSteps = (steps: any[]) => {
  const failureTypeCounts: Record<string, number> = {};
  let environmentIssueCount = 0;
  let retrySuggestedCount = 0;
  for (const step of steps) {
    const diagnosis = deriveStepDiagnosis(step);
    if (!diagnosis.failure_type) continue;
    failureTypeCounts[diagnosis.failure_type] = (failureTypeCounts[diagnosis.failure_type] || 0) + 1;
    if (["network_error", "connection_error", "ssl_error", "connect_timeout", "read_timeout", "timeout"].includes(diagnosis.failure_type)) environmentIssueCount += 1;
    if (["server_error", "network_error", "connection_error", "connect_timeout", "read_timeout", "timeout"].includes(diagnosis.failure_type)) retrySuggestedCount += 1;
  }
  const topFailureType = Object.entries(failureTypeCounts).sort((a, b) => b[1] - a[1])[0]?.[0];
  return {
    failure_type_counts: failureTypeCounts,
    environment_issue_count: environmentIssueCount,
    retry_suggested_count: retrySuggestedCount,
    top_failure_type: topFailureType,
  };
};

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
  diagnosis: stepDiagnosis(step),
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

<style scoped>
.report-diagnosis-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin: 14px 0;
  padding: 14px;
  border: 1px solid var(--el-color-warning-light-5);
  border-radius: 8px;
  background: var(--el-color-warning-light-9);
}

.report-diagnosis-card.muted {
  border-color: var(--el-border-color);
  background: var(--el-fill-color-light);
}

.report-diagnosis-card strong {
  color: var(--el-text-color-primary);
}

.report-diagnosis-card p {
  margin: 6px 0 0;
  color: var(--el-text-color-regular);
}

.report-diagnosis-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.report-diagnosis-tags span,
.diagnosis-type-tag {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-8);
  font-size: 12px;
  font-weight: 600;
}

.diagnosis-type-tag {
  color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
}

.report-diagnosis-board {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 0.72fr);
  gap: 14px;
  margin-bottom: 14px;
}

.report-diagnosis-panel {
  padding: 14px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: #fff;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.panel-title strong {
  color: var(--el-text-color-primary);
}

.panel-title span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.diagnosis-dist-list,
.diagnosis-action-list {
  display: grid;
  gap: 10px;
}

.diagnosis-dist-row {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr) 32px;
  align-items: center;
  gap: 10px;
}

.diagnosis-dist-row span {
  color: var(--el-text-color-regular);
  font-size: 12px;
  font-weight: 600;
}

.diagnosis-dist-row b {
  color: var(--el-text-color-primary);
  text-align: right;
}

.diagnosis-dist-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--el-fill-color-light);
}

.diagnosis-dist-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--el-color-warning);
}

.diagnosis-action-item {
  min-height: 58px;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
}

.diagnosis-action-item b,
.diagnosis-action-item span {
  display: block;
}

.diagnosis-action-item b {
  margin-bottom: 4px;
  color: var(--el-text-color-primary);
}

.diagnosis-action-item span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 980px) {
  .report-diagnosis-card {
    flex-direction: column;
  }

  .report-diagnosis-tags {
    justify-content: flex-start;
  }

  .report-diagnosis-board {
    grid-template-columns: 1fr;
  }
}
</style>
