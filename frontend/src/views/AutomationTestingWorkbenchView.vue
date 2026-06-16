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
          <el-select v-if="activeFeature === 'single'" v-model="runEnvironment" placeholder="执行环境" clearable style="width: 160px">
            <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
          </el-select>
          <el-button @click="load">刷新</el-button>
          <el-button type="primary" @click="primaryAction">{{ currentFeature.action }}</el-button>
        </div>
      </header>

      <SingleApiCaseWorkbench
        v-if="activeFeature === 'single'"
        ref="singleWorkbenchRef"
        :environment-id="runEnvironment"
        :environment-name="selectedEnvironmentName"
      />

      <template v-else-if="activeFeature === 'scenario'">
        <div class="scenario-stage">
          <section class="scenario-canvas">
            <nav class="scenario-tabs">
              <button :class="{ active: scenarioTab === 'steps' }" @click="scenarioTab = 'steps'">测试步骤</button>
              <button :class="{ active: scenarioTab === 'data' }" @click="scenarioTab = 'data'">测试数据</button>
              <button :class="{ active: scenarioTab === 'report' }" @click="scenarioTab = 'report'">测试报告</button>
              <el-select v-model="selectedScenarioId" filterable placeholder="选择场景" class="scenario-switch" @change="handleScenarioSwitch">
                <el-option v-for="scenario in filteredScenarios" :key="scenario.id" :label="scenario.name" :value="scenario.id" />
              </el-select>
              <el-button @click="openScenarioDialog()">新增场景</el-button>
            </nav>

            <template v-if="scenarioTab === 'steps'">
              <header class="scenario-hero">
                <div class="scenario-title-line">
                  <el-select v-model="scenarioPriority" class="scenario-priority">
                    <el-option label="P0" value="P0" />
                    <el-option label="P1" value="P1" />
                    <el-option label="P2" value="P2" />
                    <el-option label="P3" value="P3" />
                  </el-select>
                  <h2>{{ selectedScenario?.name || "请选择或新增场景" }}</h2>
                </div>
                <button class="scenario-desc-button" @click="openScenarioDialog(selectedScenario)">添加描述</button>
                <p>{{ scenarioUpdatedText }}</p>
              </header>

              <div class="scenario-step-count">
                <el-checkbox :model-value="Boolean(scenarioSteps.length)" />
                <span>已选 {{ scenarioSteps.length }} 项</span>
              </div>

              <div class="scenario-step-cards">
                <article v-for="(step, index) in scenarioSteps" :key="step.uid" class="scenario-step-card">
                  <div class="scenario-step-card-main" @click="openStepEditor(step, index)">
                    <el-checkbox :model-value="step.is_active !== false" @change="step.is_active = !step.is_active" @click.stop />
                    <span class="scenario-method" :class="step.method.toLowerCase()">{{ step.method }}</span>
                    <strong>{{ step.name }}</strong>
                    <small>{{ step.path }}</small>
                  </div>
                  <div class="scenario-step-card-actions">
                    <button @click="openStepEditor(step, index)">编辑</button>
                    <button :disabled="index === 0" @click="moveStep(index, -1)">上移</button>
                    <button :disabled="index === scenarioSteps.length - 1" @click="moveStep(index, 1)">下移</button>
                    <button class="danger-link" @click="removeStep(index)">删除</button>
                  </div>
                </article>
              </div>

              <div class="scenario-add-card">
                <el-select v-model="apiToAdd" filterable placeholder="选择接口添加为步骤">
                  <el-option v-for="api in apis" :key="api.id" :label="`${api.method} ${api.name} (${api.path})`" :value="api.id" />
                </el-select>
                <button @click="addStepFromApi">+ 添加步骤</button>
              </div>
            </template>

            <template v-else-if="scenarioTab === 'data'">
              <div class="scenario-panel-empty">
                <h2>测试数据</h2>
                <p>可在右侧选择本次运行使用的数据源，也可在步骤编辑中为每一步配置前置/后置数据源。</p>
                <el-table :data="activeTestDataSources" height="360">
                  <el-table-column prop="name" label="数据源" min-width="180" />
                  <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
                  <el-table-column prop="is_active" label="状态" width="90">
                    <template #default="{ row }">{{ row.is_active ? "启用" : "停用" }}</template>
                  </el-table-column>
                </el-table>
              </div>
            </template>

            <template v-else>
              <div class="scenario-panel-empty">
                <h2>测试报告</h2>
                <p v-if="!scenarioResults.length">执行场景后会在这里展示最近一次运行结果。</p>
                <el-table v-else :data="scenarioResults" height="420">
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
            </template>
          </section>

          <aside class="scenario-runner">
            <el-tabs v-model="scenarioRunMode">
              <el-tab-pane label="功能测试" name="functional" />
              <el-tab-pane label="性能测试" name="performance" />
            </el-tabs>
            <label>运行环境</label>
            <el-select v-model="scenarioRunnerEnvironment" placeholder="请选择运行环境" :disabled="!selectedScenario">
              <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
            </el-select>
            <label>测试数据</label>
            <el-select v-model="runnerDataSource" clearable placeholder="不使用测试数据">
              <el-option v-for="source in activeTestDataSources" :key="source.id" :label="source.name" :value="source.id" />
            </el-select>
            <div class="scenario-runner-grid">
              <div>
                <label>循环次数</label>
                <el-input-number v-model="runnerLoopCount" :min="1" :max="999" />
              </div>
              <div>
                <label>线程数</label>
                <el-input-number v-model="runnerThreadCount" :min="1" :max="100" />
              </div>
            </div>
            <label>运行于</label>
            <el-select v-model="runnerHost">
              <el-option label="本机" value="local" />
              <el-option label="远程执行机" value="remote" />
            </el-select>
            <div class="scenario-runner-line">
              <span>通知</span>
              <el-switch v-model="runnerNotify" />
            </div>
            <div class="scenario-runner-line">
              <span>高级设置</span>
              <el-checkbox v-model="runnerShare">共享</el-checkbox>
            </div>
            <div class="scenario-runner-actions">
              <el-button type="primary" :loading="runningScenario" @click="runScenario">运行</el-button>
              <el-button :loading="savingScenario" @click="saveScenarioRunner">保存</el-button>
            </div>
          </aside>
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

    <el-dialog v-model="scenarioDialog" :title="scenarioForm.id ? '编辑场景用例' : '新增场景用例'" width="560px" destroy-on-close>
      <el-form label-width="86px">
        <el-form-item label="名称" required>
          <el-input v-model="scenarioForm.name" maxlength="20" show-word-limit placeholder="请输入场景名称" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="scenarioForm.description" type="textarea" :rows="4" maxlength="200" show-word-limit placeholder="请输入场景说明" />
        </el-form-item>
        <el-form-item label="运行环境" required>
          <el-select v-model="scenarioForm.environment" filterable placeholder="请选择运行环境" style="width: 100%">
            <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scenarioDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingScenario" @click="saveScenarioMeta">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="stepDrawer" size="72%" :with-header="false" destroy-on-close>
      <div class="scenario-step-drawer">
        <header class="scenario-step-drawer-head">
          <div>
            <b>编辑接口步骤</b>
            <span>{{ stepEditForm.method }} {{ stepEditForm.path || "-" }}</span>
          </div>
          <div>
            <el-button @click="stepDrawer = false">取消</el-button>
            <el-button type="primary" @click="applyStepEdit">应用</el-button>
          </div>
        </header>

        <el-form label-width="86px" class="scenario-step-form">
          <el-form-item label="步骤名称" required><el-input v-model="stepEditForm.name" /></el-form-item>
          <el-form-item label="请求信息">
            <div class="step-request-line">
              <el-select v-model="stepEditForm.method" style="width: 120px">
                <el-option v-for="method in httpMethods" :key="method" :label="method" :value="method" />
              </el-select>
              <el-input v-model="stepEditForm.path" placeholder="/api/path" />
            </div>
          </el-form-item>
          <el-form-item label="所属平台">
            <el-select v-model="stepEditForm.platform" filterable>
              <el-option v-for="platform in platforms" :key="platform.code" :label="platform.name" :value="platform.code" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-tabs v-model="stepEditTab" class="scenario-step-tabs">
          <el-tab-pane label="Params" name="params">
            <div class="kv-editor">
              <div class="kv-row kv-head"><span>启用</span><span>Key</span><span>Value</span><span>说明</span><span></span></div>
              <div v-for="(row, index) in stepEditForm.query_params" :key="index" class="kv-row">
                <el-checkbox v-model="row.enabled" />
                <el-input v-model="row.key" placeholder="key" />
                <el-input v-model="row.value" placeholder="{{变量名}} 或固定值" />
                <el-input v-model="row.description" placeholder="说明" />
                <el-button link class="danger-link" @click="removeStepRow('query_params', index)">删除</el-button>
              </div>
              <el-button @click="addStepRow('query_params')">新增 Params</el-button>
            </div>
          </el-tab-pane>
          <el-tab-pane label="Headers" name="headers">
            <div class="kv-editor">
              <div class="kv-row kv-head"><span>启用</span><span>Key</span><span>Value</span><span>说明</span><span></span></div>
              <div v-for="(row, index) in stepEditForm.headers" :key="index" class="kv-row">
                <el-checkbox v-model="row.enabled" />
                <el-input v-model="row.key" placeholder="Header Key" />
                <el-input v-model="row.value" placeholder="{{token}} 或固定值" />
                <el-input v-model="row.description" placeholder="说明" />
                <el-button link class="danger-link" @click="removeStepRow('headers', index)">删除</el-button>
              </div>
              <el-button @click="addStepRow('headers')">新增 Header</el-button>
            </div>
          </el-tab-pane>
          <el-tab-pane label="Body" name="body">
            <el-select v-model="stepEditForm.body_type" style="width: 160px; margin-bottom: 10px">
              <el-option label="none" value="none" />
              <el-option label="json" value="json" />
              <el-option label="form" value="form" />
              <el-option label="raw" value="raw" />
            </el-select>
            <el-input v-model="stepBodyText" type="textarea" :rows="12" placeholder='{"id":"{{orderId}}"}' />
          </el-tab-pane>
          <el-tab-pane label="提取变量" name="extractors">
            <div class="kv-editor extractor-editor">
              <div class="kv-row extractor-row kv-head"><span>变量名</span><span>JSONPath</span><span></span></div>
              <div v-for="(row, index) in stepEditForm.extractors" :key="index" class="kv-row extractor-row">
                <el-input v-model="row.name" placeholder="orderId" />
                <el-input v-model="row.path" placeholder="$.data.id" />
                <el-button link class="danger-link" @click="stepEditForm.extractors.splice(index, 1)">删除</el-button>
              </div>
              <el-button @click="stepEditForm.extractors.push({ name: '', path: '' })">新增提取变量</el-button>
            </div>
          </el-tab-pane>
          <el-tab-pane label="断言" name="assertions">
            <div class="kv-editor assertion-editor">
              <div class="kv-row assertion-row kv-head"><span>JSONPath</span><span>关系</span><span>期望值</span><span></span></div>
              <div v-for="(row, index) in stepEditForm.assertions" :key="index" class="kv-row assertion-row">
                <el-input v-model="row.path" placeholder="$.code" />
                <el-select v-model="row.operator">
                  <el-option label="等于" value="eq" />
                  <el-option label="包含" value="contains" />
                  <el-option label="存在" value="exists" />
                </el-select>
                <el-input v-model="row.expected" :disabled="row.operator === 'exists'" placeholder="期望值" />
                <el-button link class="danger-link" @click="stepEditForm.assertions.splice(index, 1)">删除</el-button>
              </div>
              <el-button @click="stepEditForm.assertions.push({ type: 'json_path', path: '', operator: 'eq', expected: '' })">新增断言</el-button>
            </div>
          </el-tab-pane>
          <el-tab-pane label="Auth" name="auth">
            <el-input v-model="stepAuthText" type="textarea" :rows="10" placeholder='{"type":"bearer","token":"{{token}}"}' />
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";

import SingleApiCaseWorkbench from "@/components/SingleApiCaseWorkbench.vue";
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
interface RowItem { enabled: boolean; key: string; value: string; description?: string }
interface ExtractorItem { name: string; path: string }
interface AssertionItem { type?: string; path: string; key?: string; operator: string; expected?: string }
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
interface ApiScenario { id: number; suite: number; environment?: number; name: string; description?: string; priority?: string; is_active?: boolean }
interface ApiStep {
  id?: number;
  scenario?: number;
  api?: number;
  name: string;
  platform: string;
  method: string;
  path: string;
  headers?: RowItem[];
  query_params?: RowItem[];
  body_type?: string;
  body?: unknown;
  auth_config?: Record<string, unknown>;
  pre_data_source_ids?: number[];
  post_data_source_ids?: number[];
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
interface StepEditForm {
  name: string;
  platform: string;
  method: string;
  path: string;
  headers: RowItem[];
  query_params: RowItem[];
  body_type: string;
  extractors: ExtractorItem[];
  assertions: AssertionItem[];
}

const router = useRouter();
const singleWorkbenchRef = ref<InstanceType<typeof SingleApiCaseWorkbench>>();
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
const testDataSources = ref<any[]>([]);
const suites = ref<ApiSuite[]>([]);
const scenarios = ref<ApiScenario[]>([]);
const selectedScenario = ref<ApiScenario>();
const selectedScenarioId = ref<number>();
const scenarioKeyword = ref("");
const scenarioTab = ref<"steps" | "data" | "report">("steps");
const scenarioSteps = ref<ScenarioStep[]>([]);
const scenarioResults = ref<ScenarioResult[]>([]);
const apiToAdd = ref<number>();
const runEnvironment = ref<number>();
const savingScenario = ref(false);
const runningScenario = ref(false);
const scenarioDialog = ref(false);
const scenarioForm = reactive({ id: undefined as number | undefined, name: "", description: "", environment: undefined as number | undefined });
const scenarioRunMode = ref("functional");
const scenarioRunnerEnvironment = ref<number>();
const runnerDataSource = ref<number>();
const runnerLoopCount = ref(1);
const runnerThreadCount = ref(1);
const runnerHost = ref("local");
const runnerNotify = ref(false);
const runnerShare = ref(false);
const scenarioPriority = computed({
  get: () => selectedScenario.value?.priority || "P2",
  set: (priority: string) => {
    if (selectedScenario.value) selectedScenario.value.priority = priority;
  },
});
const httpMethods = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const stepDrawer = ref(false);
const stepEditTab = ref("params");
const editingStepIndex = ref<number>();
const stepBodyText = ref("{}");
const stepAuthText = ref("{}");
const stepEditForm = reactive<StepEditForm>({
  name: "",
  platform: "",
  method: "GET",
  path: "",
  headers: [],
  query_params: [],
  body_type: "none",
  extractors: [],
  assertions: [],
});

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
const activeTestDataSources = computed(() => testDataSources.value.filter((item) => item.is_active));
const selectedEnvironmentName = computed(() => environments.value.find((item) => item.id === runEnvironment.value)?.name || "-");
const scenarioEnvironmentName = computed(() => {
  const environmentId = selectedScenario.value?.environment;
  return environments.value.find((item) => item.id === environmentId)?.name || "未配置";
});
const scenarioUpdatedText = computed(() => {
  if (!selectedScenario.value) return "请选择场景后维护测试步骤";
  return `${selectedScenario.value.description || "暂无描述"} · 共 ${scenarioSteps.value.length} 个步骤`;
});
const platformName = (code: string) => platforms.value.find((item) => item.code === code)?.name || code;
const caseStatusText = (status: string) => ({ draft: "草稿", active: "启用", inactive: "停用" }[status] || status);
const caseStatusClass = (status: string) => (status === "active" ? "badge-success" : status === "inactive" ? "badge-danger" : "badge-warning");

const load = async () => {
  loading.value = true;
  try {
    const [caseResp, platformResp, apiResp, envResp, suiteResp, scenarioResp, dataSourceResp] = await Promise.all([
      platformApi.apiTestCases(),
      platformApi.platforms(),
      platformApi.apiDefinitions(),
      platformApi.environments(),
      platformApi.apiSuites(),
      platformApi.apiScenarios(),
      platformApi.testDataSources(),
    ]);
    cases.value = unwrapList<ApiTestCase>(caseResp.data);
    platformRows.value = unwrapList(platformResp.data);
    apis.value = unwrapList<ApiDefinition>(apiResp.data);
    environments.value = unwrapList(envResp.data);
    suites.value = unwrapList<ApiSuite>(suiteResp.data);
    scenarios.value = unwrapList<ApiScenario>(scenarioResp.data);
    testDataSources.value = unwrapList(dataSourceResp.data);
    runEnvironment.value = runEnvironment.value || environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id;
    if (!selectedScenario.value && scenarios.value.length) await selectScenario(scenarios.value[0]);
  } finally {
    loading.value = false;
  }
};

const primaryAction = () => {
  if (activeFeature.value === "single") {
    singleWorkbenchRef.value?.openCreateDialog();
    return;
  }
  if (activeFeature.value === "scenario") {
    openScenarioDialog();
    return;
  }
  if (activeFeature.value === "schedule") {
    router.push("/scheduling");
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

const cloneJson = <T>(value: T, fallback: T): T => {
  if (value === undefined || value === null) return fallback;
  try {
    return JSON.parse(JSON.stringify(value));
  } catch {
    return fallback;
  }
};

const parseJsonText = <T>(text: string, fallback: T): T => {
  try {
    return JSON.parse(text);
  } catch {
    ElMessage.warning("JSON 格式不正确");
    throw new Error("invalid json");
  }
};

const normalizeRows = (rows?: RowItem[]) =>
  (Array.isArray(rows) ? rows : [])
    .filter((row) => row.key?.trim())
    .map((row) => ({
      enabled: row.enabled !== false,
      key: row.key.trim(),
      value: row.value ?? "",
      description: row.description || "",
    }));

const normalizeExtractors = (rows?: ExtractorItem[]) =>
  (Array.isArray(rows) ? rows : [])
    .filter((row) => row.name?.trim() && row.path?.trim())
    .map((row) => ({ name: row.name.trim(), path: row.path.trim() }));

const normalizeAssertions = (rows?: AssertionItem[]) =>
  (Array.isArray(rows) ? rows : [])
    .filter((row) => row.path?.trim())
    .map((row) => ({
      type: "json_path",
      path: row.path.trim(),
      operator: row.operator || "eq",
      expected: row.operator === "exists" ? "" : row.expected ?? "",
    }));

const stepSummaryExtractor = (step: ApiStep) => normalizeExtractors(step.extractors as ExtractorItem[])[0] || {};
const stepSummaryAssertion = (step: ApiStep) => normalizeAssertions(step.assertions as AssertionItem[])[0] || {};

const resetScenarioForm = () => {
  Object.assign(scenarioForm, {
    id: undefined,
    name: "",
    description: "",
    environment: environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id,
  });
};

const openScenarioDialog = (scenario?: ApiScenario) => {
  if (scenario) {
    Object.assign(scenarioForm, {
      id: scenario.id,
      name: scenario.name,
      description: scenario.description || "",
      environment: scenario.environment || environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id,
    });
  } else {
    resetScenarioForm();
  }
  scenarioDialog.value = true;
};

const toScenarioStep = (step: ApiStep): ScenarioStep => {
  const extractor = stepSummaryExtractor(step);
  const assertion = stepSummaryAssertion(step);
  return {
    ...step,
    uid: Date.now() + Math.floor(Math.random() * 100000),
    extractName: extractor.name || "",
    extractPath: extractor.path || "",
    assertPath: assertion.path || "",
    assertOperator: assertion.operator || "eq",
    assertExpected: assertion.expected === undefined || assertion.expected === null ? "" : String(assertion.expected),
    headers: cloneJson(step.headers as RowItem[], []),
    query_params: cloneJson(step.query_params as RowItem[], []),
    body: cloneJson(step.body, {}),
    auth_config: cloneJson(step.auth_config || {}, {}),
    assertions: cloneJson(step.assertions || [], []),
    extractors: cloneJson(step.extractors || [], []),
    pre_data_source_ids: cloneJson(step.pre_data_source_ids || [], []),
    post_data_source_ids: cloneJson(step.post_data_source_ids || [], []),
  };
};

const selectScenario = async (scenario: ApiScenario) => {
  selectedScenario.value = scenario;
  selectedScenarioId.value = scenario.id;
  scenarioRunnerEnvironment.value = scenario.environment || environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id;
  scenarioResults.value = [];
  const { data } = await platformApi.apiSteps({ scenario: scenario.id, ordering: "sort_order,id" });
  scenarioSteps.value = unwrapList<ApiStep>(data).map(toScenarioStep);
};

const handleScenarioSwitch = async (id: number) => {
  const scenario = scenarios.value.find((item) => item.id === id);
  if (scenario) await selectScenario(scenario);
};

const addStepFromApi = () => {
  if (!selectedScenario.value) {
    ElMessage.warning("请先新增或选择场景");
    return;
  }
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
    headers: cloneJson(api.headers as RowItem[], []),
    query_params: cloneJson(api.query_params as RowItem[], []),
    body_type: api.body_type || "none",
    body: api.body || {},
    auth_config: api.auth_config || {},
    pre_data_source_ids: [],
    post_data_source_ids: [],
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

const openStepEditor = (step: ScenarioStep, index: number) => {
  editingStepIndex.value = index;
  Object.assign(stepEditForm, {
    name: step.name,
    platform: step.platform,
    method: step.method,
    path: step.path,
    headers: normalizeRows(cloneJson(step.headers as RowItem[], [])),
    query_params: normalizeRows(cloneJson(step.query_params as RowItem[], [])),
    body_type: step.body_type || "none",
    extractors: normalizeExtractors(cloneJson(step.extractors as ExtractorItem[], [])),
    assertions: normalizeAssertions(cloneJson(step.assertions as AssertionItem[], [])),
  });
  stepBodyText.value = JSON.stringify(step.body || {}, null, 2);
  stepAuthText.value = JSON.stringify(step.auth_config || {}, null, 2);
  stepEditTab.value = "params";
  stepDrawer.value = true;
};

const addStepRow = (field: "headers" | "query_params") => {
  stepEditForm[field].push({ enabled: true, key: "", value: "", description: "" });
};

const removeStepRow = (field: "headers" | "query_params", index: number) => {
  stepEditForm[field].splice(index, 1);
};

const applyStepEdit = () => {
  if (editingStepIndex.value === undefined) return;
  if (!stepEditForm.name.trim() || !stepEditForm.path.trim()) {
    ElMessage.warning("步骤名称和请求路径不能为空");
    return;
  }
  let body: unknown;
  let auth_config: Record<string, unknown>;
  try {
    body = parseJsonText(stepBodyText.value || "{}", {});
    auth_config = parseJsonText(stepAuthText.value || "{}", {});
  } catch {
    return;
  }
  const current = scenarioSteps.value[editingStepIndex.value];
  scenarioSteps.value.splice(editingStepIndex.value, 1, toScenarioStep({
    ...current,
    name: stepEditForm.name.trim(),
    platform: stepEditForm.platform,
    method: stepEditForm.method,
    path: stepEditForm.path.trim(),
    headers: normalizeRows(stepEditForm.headers),
    query_params: normalizeRows(stepEditForm.query_params),
    body_type: stepEditForm.body_type,
    body,
    auth_config,
    extractors: normalizeExtractors(stepEditForm.extractors),
    assertions: normalizeAssertions(stepEditForm.assertions),
  }));
  stepDrawer.value = false;
};

const stepPayload = (step: ScenarioStep, scenarioId: number, index: number) => ({
  scenario: scenarioId,
  api: step.api,
  name: step.name,
  platform: step.platform,
  method: step.method,
  path: step.path,
  headers: normalizeRows(step.headers as RowItem[]),
  query_params: normalizeRows(step.query_params as RowItem[]),
  body_type: step.body_type || "none",
  body: step.body || {},
  auth_config: step.auth_config || {},
  pre_data_source_ids: step.pre_data_source_ids || [],
  post_data_source_ids: step.post_data_source_ids || [],
  extractors: normalizeExtractors(step.extractors as ExtractorItem[]),
  assertions: normalizeAssertions(step.assertions as AssertionItem[]),
  sort_order: index,
  is_active: true,
});

const saveScenarioMeta = async () => {
  if (!scenarioForm.name.trim()) {
    ElMessage.warning("请填写场景名称");
    return;
  }
  if (scenarioForm.name.trim().length > 20) {
    ElMessage.warning("场景名称不能超过20个字");
    return;
  }
  if ((scenarioForm.description || "").length > 200) {
    ElMessage.warning("场景说明不能超过200个字");
    return;
  }
  if (!scenarioForm.environment) {
    ElMessage.warning("请选择运行环境");
    return;
  }
  savingScenario.value = true;
  try {
    const suite = await defaultSuite();
    const scenarioPayload = {
      suite: suite.id,
      environment: scenarioForm.environment,
      name: scenarioForm.name.trim(),
      description: scenarioForm.description,
      priority: "P1",
      is_active: true,
    };
    const { data: scenario } = scenarioForm.id
      ? await platformApi.updateApiScenario(scenarioForm.id, scenarioPayload)
      : await platformApi.createApiScenario(scenarioPayload);
    ElMessage.success("场景已保存");
    scenarioDialog.value = false;
    selectedScenario.value = scenario;
    selectedScenarioId.value = scenario.id;
    scenarioRunnerEnvironment.value = scenario.environment;
    await load();
    await selectScenario(scenario);
  } finally {
    savingScenario.value = false;
  }
};

const saveScenarioSteps = async () => {
  if (!selectedScenario.value) {
    ElMessage.warning("请先新增或选择场景");
    return;
  }
  savingScenario.value = true;
  try {
    const scenario = selectedScenario.value;
    const savedStepIds = scenarioSteps.value.map((step) => step.id).filter(Boolean) as number[];
    const { data: oldStepsResp } = await platformApi.apiSteps({ scenario: scenario.id, ordering: "sort_order,id" });
    await Promise.all(
      unwrapList<ApiStep>(oldStepsResp)
        .filter((step) => step.id && !savedStepIds.includes(step.id))
        .map((step) => platformApi.deleteApiStep(step.id as number)),
    );
    await Promise.all(
      scenarioSteps.value.map((step, index) =>
        step.id
          ? platformApi.updateApiStep(step.id, stepPayload(step, scenario.id, index))
          : platformApi.createApiStep(stepPayload(step, scenario.id, index)),
      ),
    );
    ElMessage.success("步骤已保存");
    await selectScenario(scenario);
  } finally {
    savingScenario.value = false;
  }
};

const saveScenarioRunner = async () => {
  if (!selectedScenario.value) {
    ElMessage.warning("请先新增或选择场景");
    return;
  }
  if (!scenarioRunnerEnvironment.value) {
    ElMessage.warning("请选择运行环境");
    return;
  }
  savingScenario.value = true;
  try {
    const { data } = await platformApi.updateApiScenario(selectedScenario.value.id, {
      suite: selectedScenario.value.suite,
      name: selectedScenario.value.name,
      description: selectedScenario.value.description || "",
      priority: scenarioPriority.value,
      environment: scenarioRunnerEnvironment.value,
      is_active: selectedScenario.value.is_active !== false,
    });
    selectedScenario.value = data;
    const index = scenarios.value.findIndex((item) => item.id === data.id);
    if (index >= 0) scenarios.value.splice(index, 1, data);
    ElMessage.success("运行配置已保存");
  } finally {
    savingScenario.value = false;
  }
};

const deleteScenario = async () => {
  if (!selectedScenario.value) return;
  await ElMessageBox.confirm(`确认删除场景「${selectedScenario.value.name}」？`, "删除确认", { type: "warning" });
  await platformApi.deleteApiScenario(selectedScenario.value.id);
  ElMessage.success("场景已删除");
  selectedScenario.value = undefined;
  selectedScenarioId.value = undefined;
  scenarioRunnerEnvironment.value = undefined;
  resetScenarioForm();
  scenarioSteps.value = [];
  scenarioResults.value = [];
  await load();
};

const compareValue = (actual: unknown, expected: string, operator: string) => {
  if (operator === "exists") return actual !== undefined && actual !== null;
  const actualText = typeof actual === "string" ? actual : JSON.stringify(actual);
  if (operator === "contains") return actualText.includes(expected);
  return actualText === expected;
};

const runScenario = async () => {
  if (!selectedScenario.value) {
    ElMessage.warning("请先新增或选择场景");
    return;
  }
  const runEnvironmentId = scenarioRunnerEnvironment.value || selectedScenario.value.environment;
  if (!runEnvironmentId) {
    ElMessage.warning("请先为当前场景配置运行环境");
    openScenarioDialog(selectedScenario.value);
    return;
  }
  if (!scenarioSteps.value.length) {
    ElMessage.warning("请先添加接口步骤");
    return;
  }
  runningScenario.value = true;
  scenarioResults.value = [];
  const variables: Record<string, unknown> = {};
  try {
    for (const [index, step] of scenarioSteps.value.entries()) {
      let data: any;
      try {
        const resp = await platformApi.debugApi({
          method: step.method,
          path: step.path,
          platform: step.platform,
          environment: runEnvironmentId,
          headers: step.headers || [],
          query_params: step.query_params || [],
          body: step.body || {},
          auth_config: step.auth_config || {},
          pre_test_data_sources: step.pre_data_source_ids || [],
          post_test_data_sources: step.post_data_source_ids || [],
          extractors: normalizeExtractors(step.extractors as ExtractorItem[]),
          assertions: normalizeAssertions(step.assertions as AssertionItem[]),
          variables,
        });
        data = resp.data;
      } catch (error: any) {
        scenarioResults.value.push({
          order: index + 1,
          name: step.name,
          passed: false,
          statusCode: "-",
          elapsed: "-",
          extractedText: "",
          assertText: "未执行",
          error: error?.message || "步骤执行失败",
        });
        break;
      }
      const body = data?.response?.body;
      Object.assign(variables, data?.variables || {});
      const extractors = normalizeExtractors(step.extractors as ExtractorItem[]);
      const extractedMessages: string[] = [];
      for (const extractor of extractors) {
        const extracted = extractJsonPath(body, extractor.path);
        if (extracted.ok) {
          variables[extractor.name] = extracted.value;
          extractedMessages.push(`${extractor.name}=${formatExtractValue(extracted.value)}`);
        } else {
          extractedMessages.push(`${extractor.name}: ${extracted.message}`);
        }
      }
      const extractedText = extractedMessages.join("；");
      let assertPassed = true;
      let assertText = "未配置断言";
      const assertions = normalizeAssertions(step.assertions as AssertionItem[]);
      if (assertions.length) {
        const assertMessages: string[] = [];
        assertPassed = true;
        for (const assertion of assertions) {
          const actual = extractJsonPath(body, assertion.path);
          const currentPassed = actual.ok && compareValue(actual.value, assertion.expected || "", assertion.operator);
          assertPassed = assertPassed && currentPassed;
          assertMessages.push(`${assertion.path} ${assertion.operator} ${assertion.expected || ""}，实际 ${actual.ok ? formatExtractValue(actual.value) : actual.message}`);
        }
        assertText = assertMessages.join("；");
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
    scenarioTab.value = "report";
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
  const name = selectedScenario.value?.name || "scenario";
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

