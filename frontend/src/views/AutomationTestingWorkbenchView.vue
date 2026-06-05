<template>
  <div class="automation-v2-shell">
    <aside class="automation-nav">
      <div class="automation-title">自动化测试</div>
      <button v-for="item in features" :key="item.key" class="automation-item" :class="{ active: activeFeature === item.key }" @click="activeFeature = item.key">
        <span class="feature-code">{{ item.code }}</span>
        <span>
          <b>{{ item.label }}</b>
          <em>{{ item.desc }}</em>
        </span>
      </button>
    </aside>

    <section class="automation-main">
      <header class="automation-head">
        <div>
          <h1>{{ currentFeature.label }}</h1>
          <p>{{ currentFeature.desc }}</p>
        </div>
        <div class="automation-actions">
          <el-button @click="load">刷新</el-button>
          <el-button type="primary" @click="primaryAction">{{ currentFeature.action }}</el-button>
        </div>
      </header>

      <template v-if="activeFeature === 'single'">
        <div class="automation-stats">
          <div class="auto-stat"><span>用例总数</span><strong>{{ cases.length }}</strong></div>
          <div class="auto-stat"><span>启用用例</span><strong>{{ activeCaseCount }}</strong></div>
          <div class="auto-stat"><span>覆盖接口</span><strong>{{ coveredApiCount }}</strong></div>
          <div class="auto-stat"><span>草稿用例</span><strong>{{ draftCaseCount }}</strong></div>
        </div>
        <div class="automation-toolbar">
          <el-input v-model="keyword" placeholder="搜索用例名称、接口路径" clearable style="width: 300px" />
          <el-select v-model="statusFilter" clearable placeholder="状态" style="width: 140px">
            <el-option label="草稿" value="draft" />
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
          <el-select v-model="platformFilter" clearable placeholder="平台" style="width: 150px">
            <el-option v-for="item in platforms" :key="item.code" :label="item.name" :value="item.code" />
          </el-select>
        </div>
        <div class="auto-table-card">
          <el-table :data="filteredCases" v-loading="loading" stripe height="100%">
            <el-table-column prop="name" label="用例名称" min-width="220" />
            <el-table-column label="关联接口" min-width="240"><template #default="{ row }"><span class="inline-code">{{ row.method }} {{ row.api_path }}</span></template></el-table-column>
            <el-table-column label="平台" width="120"><template #default="{ row }">{{ platformName(row.platform) }}</template></el-table-column>
            <el-table-column prop="priority" label="优先级" width="90" />
            <el-table-column label="状态" width="100"><template #default="{ row }"><span class="badge" :class="caseStatusClass(row.status)">{{ caseStatusText(row.status) }}</span></template></el-table-column>
            <el-table-column label="操作" width="190" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="goApi(row)">接口</el-button>
                <el-button link type="primary" @click="runCase(row)">执行</el-button>
                <el-button link class="danger-link" @click="deleteCase(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>

      <template v-else-if="activeFeature === 'scenario'">
        <div class="scenario-workbench">
          <aside class="scenario-list">
            <div class="scenario-list-head">
              <strong>场景列表</strong>
              <el-button size="small" type="primary" @click="newScenario">新增</el-button>
            </div>
            <el-input v-model="scenarioKeyword" placeholder="搜索场景" clearable />
            <button
              v-for="scenario in filteredScenarios"
              :key="scenario.id"
              class="scenario-list-item"
              :class="{ active: selectedScenario?.id === scenario.id }"
              @click="selectScenario(scenario)"
            >
              <b>{{ scenario.name }}</b>
              <span>{{ scenario.description || "暂无描述" }}</span>
            </button>
            <el-empty v-if="!filteredScenarios.length" description="暂无场景" />
          </aside>

          <section class="scenario-editor">
            <div class="scenario-editor-head">
              <div class="scenario-form">
                <el-input v-model="scenarioForm.name" placeholder="场景名称，例如：订单创建到出库流程" />
                <el-input v-model="scenarioForm.description" placeholder="场景说明" />
              </div>
              <div class="scenario-actions">
                <el-select v-model="runEnvironment" placeholder="执行环境" clearable style="width: 160px">
                  <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
                </el-select>
                <el-button @click="saveScenario" :loading="savingScenario">保存场景</el-button>
                <el-button type="primary" @click="runScenario" :loading="runningScenario">执行场景</el-button>
              </div>
            </div>

            <div class="scenario-add-step">
              <el-select v-model="apiToAdd" filterable placeholder="选择接口加入流程" style="min-width: 360px">
                <el-option v-for="api in apis" :key="api.id" :label="`${api.method} ${api.name} (${api.path})`" :value="api.id" />
              </el-select>
              <el-button type="primary" @click="addStepFromApi">加入流程</el-button>
              <el-button @click="exportScenario('excel')" :disabled="!scenarioResults.length">导出表格</el-button>
              <el-button @click="exportScenario('text')" :disabled="!scenarioResults.length">导出文本</el-button>
              <el-button @click="exportScenario('word')" :disabled="!scenarioResults.length">导出 Word</el-button>
            </div>

            <div class="scenario-step-table">
              <div class="scenario-step-row scenario-step-head">
                <span>#</span>
                <span>接口步骤</span>
                <span>提取变量</span>
                <span>断言</span>
                <span>操作</span>
              </div>
              <div v-for="(step, index) in scenarioSteps" :key="step.uid" class="scenario-step-row">
                <span class="step-order">{{ index + 1 }}</span>
                <div class="step-main">
                  <el-input v-model="step.name" placeholder="步骤名称" />
                  <span class="inline-code">{{ step.method }} {{ step.path }}</span>
                </div>
                <div class="step-mini-form">
                  <el-input v-model="step.extractName" placeholder="变量名，如 token" />
                  <el-input v-model="step.extractPath" placeholder="JSONPath，如 $.data.token" />
                </div>
                <div class="step-assert-form">
                  <el-input v-model="step.assertPath" placeholder="JSONPath，如 $.code" />
                  <el-select v-model="step.assertOperator">
                    <el-option label="等于" value="eq" />
                    <el-option label="包含" value="contains" />
                    <el-option label="存在" value="exists" />
                  </el-select>
                  <el-input v-model="step.assertExpected" :disabled="step.assertOperator === 'exists'" placeholder="期望值" />
                </div>
                <div class="step-actions">
                  <el-button link type="primary" :disabled="index === 0" @click="moveStep(index, -1)">上移</el-button>
                  <el-button link type="primary" :disabled="index === scenarioSteps.length - 1" @click="moveStep(index, 1)">下移</el-button>
                  <el-button link class="danger-link" @click="removeStep(index)">删除</el-button>
                </div>
              </div>
              <el-empty v-if="!scenarioSteps.length" description="请选择接口加入测试流程" />
            </div>

            <div class="scenario-results">
              <div class="scenario-results-head">
                <strong>执行结果</strong>
                <span v-if="scenarioResults.length">通过 {{ passedStepCount }} / {{ scenarioResults.length }}</span>
              </div>
              <el-table :data="scenarioResults" stripe height="100%">
                <el-table-column prop="order" label="#" width="56" />
                <el-table-column prop="name" label="步骤" min-width="180" />
                <el-table-column label="状态" width="90"><template #default="{ row }"><span class="badge" :class="row.passed ? 'badge-success' : 'badge-danger'">{{ row.passed ? "PASS" : "FAIL" }}</span></template></el-table-column>
                <el-table-column prop="statusCode" label="HTTP" width="90" />
                <el-table-column prop="elapsed" label="耗时" width="100" />
                <el-table-column prop="extractedText" label="提取数据" min-width="180" show-overflow-tooltip />
                <el-table-column prop="assertText" label="断言" min-width="220" show-overflow-tooltip />
                <el-table-column prop="error" label="错误" min-width="220" show-overflow-tooltip />
              </el-table>
            </div>
          </section>
        </div>
      </template>

      <template v-else>
        <div class="automation-placeholder">
          <div class="placeholder-icon">{{ currentFeature.code }}</div>
          <h2>{{ currentFeature.label }}</h2>
          <p>{{ currentFeature.longDesc }}</p>
          <div class="placeholder-grid">
            <div v-for="point in currentFeature.points" :key="point">{{ point }}</div>
          </div>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { platformApi, unwrapList } from "@/api/platform";
import { extractJsonPath, formatExtractValue } from "@/utils/jsonExtract";

interface Feature {
  key: string;
  code: string;
  label: string;
  desc: string;
  action: string;
  longDesc: string;
  points: string[];
}
interface ApiDefinition {
  id: number;
  name: string;
  platform: string;
  module?: number;
  method: string;
  path: string;
  headers?: unknown[];
  query_params?: unknown[];
  body_type?: string;
  body?: unknown;
  auth_config?: Record<string, unknown>;
  assertions?: unknown[];
}
interface ApiTestCase {
  id: number;
  api: number;
  name: string;
  api_path: string;
  method: string;
  platform: string;
  status: string;
  priority: string;
}
interface ApiSuite { id: number; name: string; description?: string }
interface ApiScenario { id: number; suite: number; name: string; description?: string; priority?: string; is_active?: boolean }
interface ApiStep {
  id?: number;
  scenario?: number;
  api?: number;
  name: string;
  platform: string;
  method: string;
  path: string;
  headers?: unknown[];
  query_params?: unknown[];
  body_type?: string;
  body?: unknown;
  auth_config?: Record<string, unknown>;
  assertions?: any[];
  extractors?: any[];
  sort_order?: number;
  is_active?: boolean;
}
interface ScenarioStep extends ApiStep {
  uid: number;
  extractName: string;
  extractPath: string;
  assertPath: string;
  assertOperator: string;
  assertExpected: string;
}
interface ScenarioResult {
  order: number;
  name: string;
  passed: boolean;
  statusCode: string;
  elapsed: string;
  extractedText: string;
  assertText: string;
  error: string;
}

const router = useRouter();
const features: Feature[] = [
  { key: "single", code: "API", label: "单接口用例", desc: "围绕单个接口沉淀功能测试场景", action: "新增用例", longDesc: "", points: [] },
  { key: "scenario", code: "FLOW", label: "场景测试", desc: "自选接口并串联为业务测试流程", action: "新增场景", longDesc: "场景测试用于编排多个接口步骤，支持变量传递、数据提取、断言和结果导出。", points: ["选择接口", "步骤编排", "变量提取", "流程断言"] },
  { key: "suite", code: "SET", label: "测试套件", desc: "组织单接口用例和场景用例统一执行", action: "新增套件", longDesc: "测试套件是自动化执行的核心入口，后续会承接执行环境、失败策略、并发和报告生成。", points: ["选择用例", "执行环境", "失败策略", "套件报告"] },
  { key: "data", code: "DATA", label: "测试数据", desc: "管理数据集、变量和敏感配置", action: "新增数据集", longDesc: "测试数据用于支撑数据驱动、环境变量、全局变量和敏感变量管理。", points: ["全局变量", "环境变量", "数据集", "敏感字段"] },
  { key: "schedule", code: "TIME", label: "定时任务", desc: "定期执行套件或场景", action: "新增任务", longDesc: "定时任务用于配置 Cron 执行、启停调度、执行历史和失败通知。", points: ["Cron 配置", "执行目标", "启停控制", "失败通知"] },
  { key: "report", code: "REP", label: "测试报告", desc: "查看执行结果、失败详情和趋势", action: "查看报告", longDesc: "测试报告用于聚合单次执行结果、趋势分析、失败原因和平台模块维度统计。", points: ["通过率趋势", "失败详情", "耗时统计", "报告导出"] },
];

const activeFeature = ref("single");
const loading = ref(false);
const keyword = ref("");
const statusFilter = ref("");
const platformFilter = ref("");
const cases = ref<ApiTestCase[]>([]);
const apis = ref<ApiDefinition[]>([]);
const platformRows = ref<any[]>([]);
const environments = ref<any[]>([]);
const suites = ref<ApiSuite[]>([]);
const scenarios = ref<ApiScenario[]>([]);
const selectedScenario = ref<ApiScenario>();
const scenarioKeyword = ref("");
const scenarioSteps = ref<ScenarioStep[]>([]);
const scenarioResults = ref<ScenarioResult[]>([]);
const apiToAdd = ref<number>();
const runEnvironment = ref<number>();
const savingScenario = ref(false);
const runningScenario = ref(false);
const scenarioForm = reactive({ name: "", description: "" });

const currentFeature = computed(() => features.find((item) => item.key === activeFeature.value) || features[0]);
const platforms = computed(() => platformRows.value.map((item) => ({ ...item, code: item.code?.toUpperCase?.() || item.code })));
const activeCaseCount = computed(() => cases.value.filter((item) => item.status === "active").length);
const draftCaseCount = computed(() => cases.value.filter((item) => item.status === "draft").length);
const coveredApiCount = computed(() => new Set(cases.value.map((item) => item.api)).size);
const filteredCases = computed(() =>
  cases.value.filter((item) => {
    const text = `${item.name} ${item.api_path}`.toLowerCase();
    return (
      (!keyword.value || text.includes(keyword.value.toLowerCase())) &&
      (!statusFilter.value || item.status === statusFilter.value) &&
      (!platformFilter.value || item.platform === platformFilter.value)
    );
  }),
);
const filteredScenarios = computed(() => scenarios.value.filter((item) => !scenarioKeyword.value || item.name.toLowerCase().includes(scenarioKeyword.value.toLowerCase())));
const passedStepCount = computed(() => scenarioResults.value.filter((item) => item.passed).length);

const platformName = (code: string) => platforms.value.find((item) => item.code === code)?.name || code;
const caseStatusText = (status: string) => ({ draft: "草稿", active: "启用", inactive: "停用" }[status] || status);
const caseStatusClass = (status: string) => (status === "active" ? "badge-success" : status === "inactive" ? "badge-danger" : "badge-warning");

const load = async () => {
  loading.value = true;
  try {
    const [caseResp, platformResp, apiResp, envResp, suiteResp, scenarioResp] = await Promise.all([
      platformApi.apiTestCases(),
      platformApi.platforms(),
      platformApi.apiDefinitions(),
      platformApi.environments(),
      platformApi.apiSuites(),
      platformApi.apiScenarios(),
    ]);
    cases.value = unwrapList<ApiTestCase>(caseResp.data);
    platformRows.value = unwrapList(platformResp.data);
    apis.value = unwrapList<ApiDefinition>(apiResp.data);
    environments.value = unwrapList(envResp.data);
    suites.value = unwrapList<ApiSuite>(suiteResp.data);
    scenarios.value = unwrapList<ApiScenario>(scenarioResp.data);
    runEnvironment.value = runEnvironment.value || environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id;
    if (!selectedScenario.value && scenarios.value.length) await selectScenario(scenarios.value[0]);
  } finally {
    loading.value = false;
  }
};

const primaryAction = () => {
  if (activeFeature.value === "single") {
    ElMessage.info("请进入接口管理，选中接口后在测试用例页新增用例。");
    return;
  }
  if (activeFeature.value === "scenario") {
    newScenario();
    return;
  }
  ElMessage.info(`${currentFeature.value.label}将在后续阶段接入。`);
};

const defaultSuite = async () => {
  const existing = suites.value[0];
  if (existing) return existing;
  const { data } = await platformApi.createApiSuite({ name: "默认场景套件", description: "系统自动创建，用于承载场景测试。" });
  suites.value = [data, ...suites.value];
  return data as ApiSuite;
};

const newScenario = () => {
  selectedScenario.value = undefined;
  Object.assign(scenarioForm, { name: "", description: "" });
  scenarioSteps.value = [];
  scenarioResults.value = [];
};

const toScenarioStep = (step: ApiStep): ScenarioStep => {
  const extractor = step.extractors?.[0] || {};
  const assertion = step.assertions?.[0] || {};
  return {
    ...step,
    uid: Date.now() + Math.floor(Math.random() * 100000),
    extractName: extractor.name || "",
    extractPath: extractor.path || "",
    assertPath: assertion.path || assertion.key || "",
    assertOperator: assertion.operator || "eq",
    assertExpected: assertion.expected === undefined || assertion.expected === null ? "" : String(assertion.expected),
  };
};

const selectScenario = async (scenario: ApiScenario) => {
  selectedScenario.value = scenario;
  Object.assign(scenarioForm, { name: scenario.name, description: scenario.description || "" });
  scenarioResults.value = [];
  const { data } = await platformApi.apiSteps({ scenario: scenario.id });
  scenarioSteps.value = unwrapList<ApiStep>(data).map(toScenarioStep);
};

const addStepFromApi = () => {
  const api = apis.value.find((item) => item.id === apiToAdd.value);
  if (!api) {
    ElMessage.warning("请先选择接口");
    return;
  }
  scenarioSteps.value.push(toScenarioStep({
    api: api.id,
    name: api.name,
    platform: api.platform,
    method: api.method,
    path: api.path,
    headers: api.headers || [],
    query_params: api.query_params || [],
    body_type: api.body_type || "none",
    body: api.body || {},
    auth_config: api.auth_config || {},
    assertions: api.assertions || [],
    extractors: [],
    is_active: true,
    sort_order: scenarioSteps.value.length,
  }));
  apiToAdd.value = undefined;
};

const moveStep = (index: number, direction: number) => {
  const nextIndex = index + direction;
  if (nextIndex < 0 || nextIndex >= scenarioSteps.value.length) return;
  const rows = [...scenarioSteps.value];
  const [item] = rows.splice(index, 1);
  rows.splice(nextIndex, 0, item);
  scenarioSteps.value = rows;
};

const removeStep = (index: number) => {
  scenarioSteps.value.splice(index, 1);
};

const stepPayload = (step: ScenarioStep, scenarioId: number, index: number) => ({
  scenario: scenarioId,
  api: step.api,
  name: step.name,
  platform: step.platform,
  method: step.method,
  path: step.path,
  headers: step.headers || [],
  query_params: step.query_params || [],
  body_type: step.body_type || "none",
  body: step.body || {},
  auth_config: step.auth_config || {},
  extractors: step.extractName && step.extractPath ? [{ name: step.extractName, path: step.extractPath }] : [],
  assertions: step.assertPath ? [{ type: "json_path", path: step.assertPath, operator: step.assertOperator, expected: step.assertOperator === "exists" ? "" : step.assertExpected }] : [],
  sort_order: index,
  is_active: true,
});

const saveScenario = async () => {
  if (!scenarioForm.name.trim()) {
    ElMessage.warning("请填写场景名称");
    return;
  }
  savingScenario.value = true;
  try {
    const suite = await defaultSuite();
    const scenarioPayload = {
      suite: suite.id,
      name: scenarioForm.name.trim(),
      description: scenarioForm.description,
      priority: "P1",
      is_active: true,
    };
    const { data: scenario } = selectedScenario.value
      ? await platformApi.updateApiScenario(selectedScenario.value.id, scenarioPayload)
      : await platformApi.createApiScenario(scenarioPayload);
    if (selectedScenario.value) {
      const { data: oldStepsResp } = await platformApi.apiSteps({ scenario: scenario.id });
      await Promise.all(unwrapList<ApiStep>(oldStepsResp).map((step) => step.id ? platformApi.deleteApiStep(step.id) : Promise.resolve()));
    }
    await Promise.all(scenarioSteps.value.map((step, index) => platformApi.createApiStep(stepPayload(step, scenario.id, index))));
    ElMessage.success("场景已保存");
    selectedScenario.value = scenario;
    await load();
    await selectScenario(scenario);
  } finally {
    savingScenario.value = false;
  }
};

const compareValue = (actual: unknown, expected: string, operator: string) => {
  if (operator === "exists") return actual !== undefined && actual !== null;
  const actualText = typeof actual === "string" ? actual : JSON.stringify(actual);
  if (operator === "contains") return actualText.includes(expected);
  return actualText === expected;
};

const runScenario = async () => {
  if (!scenarioSteps.value.length) {
    ElMessage.warning("请先添加接口步骤");
    return;
  }
  runningScenario.value = true;
  scenarioResults.value = [];
  const variables: Record<string, unknown> = {};
  try {
    for (const [index, step] of scenarioSteps.value.entries()) {
      const { data } = await platformApi.debugApi({
        method: step.method,
        path: step.path,
        platform: step.platform,
        environment: runEnvironment.value,
        headers: step.headers || [],
        query_params: step.query_params || [],
        body: step.body || {},
        auth_config: step.auth_config || {},
        assertions: [],
        variables,
      });
      const body = data?.response?.body;
      let extractedText = "";
      if (step.extractName && step.extractPath) {
        const extracted = extractJsonPath(body, step.extractPath);
        if (extracted.ok) {
          variables[step.extractName] = extracted.value;
          extractedText = `${step.extractName}=${formatExtractValue(extracted.value)}`;
        } else {
          extractedText = `${step.extractName}: ${extracted.message}`;
        }
      }
      let assertPassed = true;
      let assertText = "未配置断言";
      if (step.assertPath) {
        const actual = extractJsonPath(body, step.assertPath);
        assertPassed = actual.ok && compareValue(actual.value, step.assertExpected, step.assertOperator);
        assertText = `${step.assertPath} ${step.assertOperator} ${step.assertExpected || ""}，实际 ${actual.ok ? formatExtractValue(actual.value) : actual.message}`;
      }
      const httpOk = Boolean(data?.ok) && Number(data?.response?.status_code || 0) < 400;
      scenarioResults.value.push({
        order: index + 1,
        name: step.name,
        passed: httpOk && assertPassed,
        statusCode: String(data?.response?.status_code || "-"),
        elapsed: `${data?.response?.elapsed_ms || "-"}ms`,
        extractedText,
        assertText,
        error: data?.error || "",
      });
      if (!httpOk || !assertPassed) break;
    }
  } finally {
    runningScenario.value = false;
  }
};

const downloadFile = (filename: string, content: string, type: string) => {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

const escapeHtml = (value: string) => value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const exportScenario = (type: "excel" | "text" | "word") => {
  if (!scenarioResults.value.length) return;
  const name = scenarioForm.name.trim() || "scenario";
  if (type === "text") {
    const text = scenarioResults.value.map((item) => `${item.order}. ${item.name} ${item.passed ? "PASS" : "FAIL"} HTTP=${item.statusCode} ${item.elapsed} ${item.extractedText} ${item.assertText} ${item.error}`).join("\n");
    downloadFile(`${name}-result.txt`, text, "text/plain;charset=utf-8");
    return;
  }
  const rows = scenarioResults.value.map((item) => `<tr><td>${item.order}</td><td>${escapeHtml(item.name)}</td><td>${item.passed ? "PASS" : "FAIL"}</td><td>${item.statusCode}</td><td>${item.elapsed}</td><td>${escapeHtml(item.extractedText)}</td><td>${escapeHtml(item.assertText)}</td><td>${escapeHtml(item.error)}</td></tr>`).join("");
  const table = `<table><thead><tr><th>#</th><th>步骤</th><th>状态</th><th>HTTP</th><th>耗时</th><th>提取数据</th><th>断言</th><th>错误</th></tr></thead><tbody>${rows}</tbody></table>`;
  const html = `\uFEFF<html><head><meta charset="UTF-8"></head><body><h2>${escapeHtml(name)}</h2>${table}</body></html>`;
  if (type === "word") downloadFile(`${name}-result.doc`, html, "application/msword;charset=utf-8");
  else downloadFile(`${name}-result.xls`, html, "application/vnd.ms-excel;charset=utf-8");
};

const goApi = (row: ApiTestCase) => router.push({ path: "/api-testing/apis", query: { apiId: row.api, tab: "cases" } });
const runCase = (row: ApiTestCase) => ElMessage.info(`单用例执行将由测试计划执行器统一承接：${row.name}`);
const deleteCase = async (row: ApiTestCase) => {
  await ElMessageBox.confirm(`确认删除用例「${row.name}」？`, "删除确认", { type: "warning" });
  await platformApi.deleteApiTestCase(row.id);
  ElMessage.success("用例已删除");
  await load();
};

watch(activeFeature, () => {
  if (activeFeature.value === "scenario" && !selectedScenario.value && scenarios.value.length) selectScenario(scenarios.value[0]);
});

onMounted(load);
</script>
