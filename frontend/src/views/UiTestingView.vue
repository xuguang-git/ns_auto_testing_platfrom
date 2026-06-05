<template>
  <div class="ui-test-page">
    <aside class="ui-suite-panel">
      <div class="ui-panel-head">
        <strong>UI 套件</strong>
        <el-button size="small" type="primary" @click="openSuite()">新增</el-button>
      </div>
      <el-input v-model="suiteKeyword" placeholder="搜索套件" clearable />
      <button
        v-for="suite in filteredSuites"
        :key="suite.id"
        class="ui-suite-item"
        :class="{ active: selectedSuite?.id === suite.id }"
        @click="selectSuite(suite)"
      >
        <b>{{ suite.name }}</b>
        <span>{{ suite.description || "暂无描述" }}</span>
      </button>
      <el-empty v-if="!filteredSuites.length" description="暂无套件" />
    </aside>

    <section class="ui-main-panel">
      <header class="ui-main-head">
        <div>
          <div class="breadcrumb-lite">UI测试 / 测试套件</div>
          <h1>{{ selectedSuite?.name || "请选择套件" }}</h1>
          <p>按测试套件组织 UI 用例，支持执行调试和结果预览。</p>
        </div>
        <div class="ui-main-actions">
          <el-button @click="load">刷新</el-button>
          <el-button @click="openSuite(selectedSuite)" :disabled="!selectedSuite">编辑套件</el-button>
          <el-button type="primary" @click="openCase()" :disabled="!selectedSuite">新增套件用例</el-button>
        </div>
      </header>

      <div class="ui-case-toolbar">
        <el-input v-model="caseKeyword" placeholder="搜索用例名称、URL" clearable style="width: 280px" />
        <el-select v-model="browserFilter" clearable placeholder="浏览器" style="width: 140px">
          <el-option label="Chromium" value="chromium" />
          <el-option label="Firefox" value="firefox" />
          <el-option label="WebKit" value="webkit" />
        </el-select>
        <el-segmented v-model="runMode" :options="runModeOptions" />
      </div>

      <div class="ui-case-table">
        <el-table :data="filteredCases" v-loading="loading" stripe height="100%">
          <el-table-column prop="name" label="用例名称" min-width="220" />
          <el-table-column label="所属套件" min-width="180"><template #default="{ row }">{{ row.suite_names?.join("、") || row.suite_name || "-" }}</template></el-table-column>
          <el-table-column prop="start_url" label="起始地址" min-width="260" show-overflow-tooltip />
          <el-table-column prop="created_by_name" label="创建人" width="120" show-overflow-tooltip />
          <el-table-column prop="updated_by_name" label="最后修改人" width="130" show-overflow-tooltip />
          <el-table-column prop="browser" label="浏览器" width="110" />
          <el-table-column label="步骤" width="80"><template #default="{ row }">{{ row.steps?.length || 0 }}</template></el-table-column>
          <el-table-column label="状态" width="90"><template #default="{ row }"><span class="badge" :class="row.is_active ? 'badge-success' : 'badge-warning'">{{ row.is_active ? "启用" : "停用" }}</span></template></el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openCase(row)">编辑</el-button>
              <el-button link type="primary" :loading="runningId === row.id" @click="runCase(row)">执行</el-button>
              <el-button link class="danger-link" @click="deleteCase(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <section class="ui-run-result">
        <div class="result-card-head">
          <div>
            <strong>执行结果</strong>
            <span v-if="lastRun.caseName">{{ lastRun.caseName }} · {{ lastRun.passed ? "PASS" : "FAIL" }} · {{ lastRun.duration_ms }}ms</span>
          </div>
          <el-button size="small" :disabled="!lastRun.results.length" @click="exportRunText">导出文本</el-button>
        </div>
        <div v-if="lastRun.snapshots.length" class="ui-browser-preview">
          <div class="ui-browser-frame">
            <div class="ui-browser-bar">
              <span></span>
              <span></span>
              <span></span>
              <b>{{ activeSnapshot?.url || "about:blank" }}</b>
            </div>
            <img v-if="activeSnapshot?.screenshot" :src="activeSnapshot.screenshot" alt="UI 执行页面截图" />
          </div>
          <div class="ui-snapshot-list">
            <button
              v-for="item in lastRun.snapshots"
              :key="`${item.order}-${item.name}`"
              :class="{ active: activeSnapshotOrder === item.order }"
              @click="activeSnapshotOrder = item.order"
            >
              <span>{{ item.order || "初始" }}</span>
              <b>{{ item.name }}</b>
              <em :class="item.passed ? 'passed' : 'failed'">{{ item.passed ? "PASS" : "FAIL" }}</em>
            </button>
          </div>
        </div>
        <el-table :data="lastRun.results" stripe height="100%">
          <el-table-column prop="order" label="#" width="56" />
          <el-table-column prop="name" label="步骤" min-width="180" />
          <el-table-column prop="action" label="动作" width="120" />
          <el-table-column prop="selector" label="选择器" min-width="220" show-overflow-tooltip />
          <el-table-column label="状态" width="90"><template #default="{ row }"><span class="badge" :class="row.passed ? 'badge-success' : 'badge-danger'">{{ row.passed ? "PASS" : "FAIL" }}</span></template></el-table-column>
          <el-table-column prop="duration_ms" label="耗时" width="90" />
          <el-table-column prop="message" label="信息" min-width="260" show-overflow-tooltip />
        </el-table>
        <el-empty v-if="!lastRun.results.length" description="执行用例后查看结果" />
      </section>
    </section>

    <el-dialog v-model="suiteDialog" :title="suiteForm.id ? '编辑套件' : '新增套件'" width="520px">
      <el-form :model="suiteForm" label-width="86px">
        <el-form-item label="套件名称" required><el-input v-model="suiteForm.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="suiteForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="suiteDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSuite">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="caseDrawer" size="82%" :with-header="false" destroy-on-close>
      <div class="ui-case-editor">
        <header class="ui-case-editor-head">
          <div>
            <div class="breadcrumb-lite">UI测试 / 套件用例编辑</div>
            <h2>{{ caseForm.name || "未命名用例" }}</h2>
            <p>{{ caseForm.browser }} · {{ caseForm.start_url || "未配置起始地址" }}</p>
          </div>
          <div class="ui-main-actions">
            <el-button @click="caseDrawer = false">关闭</el-button>
            <el-button type="primary" :loading="savingCase" @click="saveCase">保存用例</el-button>
          </div>
        </header>

        <section class="ui-case-editor-body">
          <div class="ui-case-base">
            <el-input v-model="caseForm.name" placeholder="用例名称" />
            <el-select v-model="caseForm.suites" multiple collapse-tags collapse-tags-tooltip placeholder="所属套件">
              <el-option v-for="suite in suites" :key="suite.id" :label="suite.name" :value="suite.id" />
            </el-select>
            <el-input v-model="caseForm.start_url" placeholder="起始地址，如 https://example.com/login" />
            <el-select v-model="caseForm.browser">
              <el-option label="Chromium" value="chromium" />
              <el-option label="Firefox" value="firefox" />
              <el-option label="WebKit" value="webkit" />
            </el-select>
            <el-switch v-model="caseForm.is_active" active-text="启用" inactive-text="停用" />
          </div>

          <div class="ui-step-toolbar">
            <strong>Playwright 步骤</strong>
            <el-button size="small" type="primary" @click="addStep">新增步骤</el-button>
          </div>

          <div class="ui-step-table">
            <div class="ui-step-row ui-step-head">
              <span>#</span>
              <span>步骤名称</span>
              <span>定位元素</span>
              <span>元素操作</span>
              <span>输入/期望</span>
              <span>高级选择器</span>
              <span>操作</span>
            </div>
            <div v-for="(step, index) in stepRows" :key="step.uid" class="ui-step-row">
              <span class="step-order">{{ index + 1 }}</span>
              <el-input v-model="step.name" placeholder="步骤名称" />
              <el-select v-model="step.element_id" clearable filterable placeholder="选择定位元素" @change="applyElement(step)">
                <el-option v-for="item in activeElements" :key="item.id" :label="elementLabel(item)" :value="item.id" />
              </el-select>
              <el-select v-model="step.action" filterable placeholder="选择元素操作" @change="applyAction(step)">
                <el-option v-for="item in actionOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
              <el-input v-model="step.value" :placeholder="valuePlaceholder(step.action)" />
              <el-input v-model="step.selector" :disabled="['goto', 'wait', 'assert_url'].includes(step.action)" placeholder="默认取定位元素，可在此覆盖" />
              <div class="step-actions">
                <el-button link type="primary" :disabled="index === 0" @click="moveStep(index, -1)">上移</el-button>
                <el-button link type="primary" :disabled="index === stepRows.length - 1" @click="moveStep(index, 1)">下移</el-button>
                <el-button link class="danger-link" @click="removeStep(index)">删除</el-button>
              </div>
            </div>
          </div>
          <el-empty v-if="!stepRows.length" description="暂无步骤，请新增 Playwright 步骤" />
        </section>
      </div>
    </el-drawer>

  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";

interface UiSuite { id: number; name: string; description?: string; case_count?: number }
interface UiCase {
  id: number;
  suite: number;
  suites?: number[];
  suite_name?: string;
  suite_names?: string[];
  element_count?: number;
  name: string;
  browser: string;
  start_url: string;
  steps: UiStep[];
  assertions?: unknown[];
  sort_order?: number;
  is_active: boolean;
}
interface UiStep { uid?: number; name: string; action: string; selector: string; value: string; expected?: string; element_id?: number; action_id?: number }
interface UiElement {
  id: number;
  suite?: number;
  name: string;
  page?: string;
  page_node_name?: string;
  locator_type: string;
  selector: string;
  description?: string;
  is_active: boolean;
}
interface UiSnapshot { order: number; name: string; passed: boolean; url: string; screenshot: string }
const loading = ref(false);
const suites = ref<UiSuite[]>([]);
const cases = ref<UiCase[]>([]);
const elements = ref<UiElement[]>([]);
const selectedSuite = ref<UiSuite>();
const suiteKeyword = ref("");
const caseKeyword = ref("");
const browserFilter = ref("");
const runMode = ref<"headed" | "headless">("headless");
const suiteDialog = ref(false);
const caseDrawer = ref(false);
const savingCase = ref(false);
const runningId = ref<number>();
const stepRows = ref<UiStep[]>([]);
const suiteForm = reactive({ id: undefined as number | undefined, name: "", description: "" });
const caseForm = reactive({ id: undefined as number | undefined, name: "", suites: [] as number[], start_url: "", browser: "chromium", is_active: true });
const activeSnapshotOrder = ref(0);
const lastRun = reactive({ caseName: "", passed: false, duration_ms: 0, results: [] as any[], snapshots: [] as UiSnapshot[] });
const runModeOptions = [
  { label: "无头执行", value: "headless" },
  { label: "有头执行", value: "headed" },
];
const actionOptions = [
  { label: "打开页面", value: "goto" },
  { label: "点击", value: "click" },
  { label: "输入", value: "fill" },
  { label: "按键", value: "press" },
  { label: "下拉选择", value: "select" },
  { label: "勾选", value: "check" },
  { label: "取消勾选", value: "uncheck" },
  { label: "等待", value: "wait" },
  { label: "断言可见", value: "assert_visible" },
  { label: "断言文本", value: "assert_text" },
  { label: "断言 URL", value: "assert_url" },
  { label: "截图", value: "screenshot" },
];

const filteredSuites = computed(() => suites.value.filter((item) => !suiteKeyword.value || item.name.toLowerCase().includes(suiteKeyword.value.toLowerCase())));
const filteredCases = computed(() => cases.value.filter((item) => {
  const text = `${item.name} ${item.start_url}`.toLowerCase();
  return (!caseKeyword.value || text.includes(caseKeyword.value.toLowerCase())) && (!browserFilter.value || item.browser === browserFilter.value);
}));
const activeElements = computed(() => elements.value.filter((item) => item.is_active));
const activeSnapshot = computed(() => lastRun.snapshots.find((item) => item.order === activeSnapshotOrder.value) || lastRun.snapshots[0]);

const load = async () => {
  loading.value = true;
  try {
    const { data } = await platformApi.uiSuites();
    suites.value = unwrapList<UiSuite>(data);
    if (!selectedSuite.value && suites.value.length) selectedSuite.value = suites.value[0];
    if (selectedSuite.value) await Promise.all([loadCases(), loadElements()]);
  } finally {
    loading.value = false;
  }
};

const loadCases = async () => {
  if (!selectedSuite.value) return;
  const { data } = await platformApi.uiCases({ suite: selectedSuite.value.id });
  cases.value = unwrapList<UiCase>(data);
};

const loadElements = async () => {
  if (!selectedSuite.value) return;
  const { data } = await platformApi.uiElements({ suite: selectedSuite.value.id });
  elements.value = unwrapList<UiElement>(data);
};

const selectSuite = async (suite: UiSuite) => {
  selectedSuite.value = suite;
  await Promise.all([loadCases(), loadElements()]);
};

const openSuite = (suite?: UiSuite) => {
  Object.assign(suiteForm, { id: suite?.id, name: suite?.name || "", description: suite?.description || "" });
  suiteDialog.value = true;
};

const saveSuite = async () => {
  if (!suiteForm.name.trim()) {
    ElMessage.warning("请填写套件名称");
    return;
  }
  const payload = { name: suiteForm.name.trim(), description: suiteForm.description };
  if (suiteForm.id) await platformApi.updateUiSuite(suiteForm.id, payload);
  else await platformApi.createUiSuite(payload);
  ElMessage.success("套件已保存");
  suiteDialog.value = false;
  await load();
};

const openCase = (row?: UiCase) => {
  if (!selectedSuite.value) return;
  Object.assign(caseForm, {
    id: row?.id,
    name: row?.name || "",
    suites: row?.suites?.length ? [...row.suites] : selectedSuite.value ? [selectedSuite.value.id] : [],
    start_url: row?.start_url || "",
    browser: row?.browser || "chromium",
    is_active: row?.is_active ?? true,
  });
  stepRows.value = (row?.steps || []).map((item) => ({ uid: Date.now() + Math.floor(Math.random() * 100000), ...item }));
  caseDrawer.value = true;
};

const addStep = () => {
  stepRows.value.push({ uid: Date.now() + Math.floor(Math.random() * 100000), name: "", action: "click", selector: "", value: "" });
};

const removeStep = (index: number) => stepRows.value.splice(index, 1);
const moveStep = (index: number, direction: number) => {
  const next = index + direction;
  if (next < 0 || next >= stepRows.value.length) return;
  const rows = [...stepRows.value];
  const [item] = rows.splice(index, 1);
  rows.splice(next, 0, item);
  stepRows.value = rows;
};

const valuePlaceholder = (action: string) => {
  if (action === "goto") return "目标 URL";
  if (action === "wait") return "等待毫秒，如 1000";
  if (action === "assert_text") return "期望文本";
  if (action === "assert_url") return "期望 URL 片段";
  if (action === "press") return "按键，如 Enter";
  return "输入值";
};

const elementLabel = (item: UiElement) => `${item.page_node_name || item.page ? `${item.page_node_name || item.page} / ` : ""}${item.name}`;
const actionLabel = (action: string) => actionOptions.find((item) => item.value === action)?.label || action;

const refreshStepName = (step: UiStep) => {
  const element = elements.value.find((item) => item.id === step.element_id);
  const action = actionLabel(step.action);
  if (element && step.action) step.name = `${action} - ${element.name}`;
  else if (element && !step.name) step.name = element.name;
  else if (step.action && !step.name) step.name = action;
};

const applyElement = (step: UiStep) => {
  const item = elements.value.find((element) => element.id === step.element_id);
  if (!item) return;
  step.selector = item.selector;
  refreshStepName(step);
};

const applyAction = (step: UiStep) => {
  step.action_id = undefined;
  refreshStepName(step);
};

const saveCase = async () => {
  if (!selectedSuite.value || !caseForm.name.trim()) {
    ElMessage.warning("请填写用例名称");
    return;
  }
  if (!caseForm.suites.length) {
    ElMessage.warning("请至少选择一个所属套件");
    return;
  }
  savingCase.value = true;
  try {
    const elementIds = [...new Set(stepRows.value.map((item) => item.element_id).filter(Boolean))];
    const payload = {
      suite: caseForm.suites[0],
      suites: caseForm.suites,
      name: caseForm.name.trim(),
      start_url: caseForm.start_url,
      browser: caseForm.browser,
      is_active: caseForm.is_active,
      steps: stepRows.value.map(({ uid, ...item }) => item),
      elements: elementIds,
      assertions: [],
    };
    if (caseForm.id) await platformApi.updateUiCase(caseForm.id, payload);
    else await platformApi.createUiCase(payload);
    ElMessage.success("用例已保存");
    caseDrawer.value = false;
    await loadCases();
  } finally {
    savingCase.value = false;
  }
};

const runCase = async (row: UiCase) => {
  runningId.value = row.id;
  try {
    const { data } = await platformApi.runUiCase(row.id, {
      headless: runMode.value === "headless",
      capture_screenshots: true,
      timeout_ms: 30000,
      navigation_timeout_ms: 45000,
      wait_until: "commit",
    });
    lastRun.caseName = row.name;
    lastRun.passed = Boolean(data.passed);
    lastRun.duration_ms = data.duration_ms || 0;
    lastRun.results = data.results || [];
    lastRun.snapshots = data.snapshots || [];
    activeSnapshotOrder.value = lastRun.snapshots[lastRun.snapshots.length - 1]?.order || lastRun.snapshots[0]?.order || 0;
    if (data.error) ElMessage.error(data.error);
    else ElMessage.success(data.passed ? "执行通过" : "执行失败");
  } finally {
    runningId.value = undefined;
  }
};

const deleteCase = async (row: UiCase) => {
  await ElMessageBox.confirm(`确认删除 UI 用例「${row.name}」？`, "删除确认", { type: "warning" });
  await platformApi.deleteUiCase(row.id);
  ElMessage.success("用例已删除");
  await loadCases();
};

const exportRunText = () => {
  const text = lastRun.results.map((item) => `${item.order}. ${item.name} ${item.passed ? "PASS" : "FAIL"} ${item.action} ${item.selector || ""} ${item.duration_ms}ms ${item.message || ""}`).join("\n");
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${lastRun.caseName || "ui-run-result"}.txt`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

onMounted(load);
</script>
