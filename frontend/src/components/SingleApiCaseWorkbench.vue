<template>
  <div class="single-case-workbench">
    <aside class="single-case-tree unified-tree-panel">
      <div class="tree-head unified-tree-head">
        <div>
          <strong>接口目录</strong>
          <span>{{ totalCaseCount }} 个用例</span>
        </div>
        <el-button size="small" @click="load">刷新</el-button>
      </div>
      <el-input v-model="keyword" placeholder="搜索目录/接口" clearable />
      <div class="tree-body unified-tree-body">
        <section v-for="platform in platformOptions" :key="platform.code">
          <button class="tree-row platform unified-tree-node" @click="togglePlatform(platform.code)">
            <span class="twisty" :class="{ expanded: expandedPlatforms.includes(platform.code) }">›</span>
            <span class="tree-name">{{ platform.name }}</span>
            <em>{{ platformCaseCount(platform.code) }}</em>
          </button>
          <template v-if="expandedPlatforms.includes(platform.code)">
            <button
              v-for="node in visibleNodes(platform.code)"
              :key="node.key"
              class="tree-row unified-tree-node"
              :class="{ api: node.type === 'api', active: node.type === 'api' && selectedApiId === node.id }"
              :style="{ paddingLeft: `${18 + node.level * 18}px` }"
              @click="node.type === 'module' ? toggleModule(Number(node.id)) : selectApi(Number(node.id))"
            >
              <span class="twisty" :class="{ expanded: expandedModules.includes(Number(node.id)) }">
                {{ node.type === "module" && hasModuleChildren(Number(node.id)) ? "›" : "" }}
              </span>
              <span v-if="node.type === 'api'" class="method-mini" :class="node.method">{{ node.method }}</span>
              <span class="tree-name">{{ node.name }}</span>
              <em>{{ caseCountText(node.caseCount) }}</em>
            </button>
          </template>
        </section>
      </div>
    </aside>

    <section class="single-case-main">
      <header class="single-case-head">
        <div>
          <h2>{{ selectedApi?.name || "请选择接口" }}</h2>
          <p v-if="selectedApi">{{ selectedDirectory }} / {{ selectedApi.method }} {{ selectedApi.path }}</p>
          <p v-else>从左侧平台目录树选择接口后查看对应用例。</p>
        </div>
        <div class="head-actions">
          <el-button :disabled="!selectedApi || !filteredCases.length" :loading="batchRunning" @click="runAllCases">运行全部用例</el-button>
          <el-button type="primary" :disabled="!selectedApi" @click="openCreateDialog">新增用例</el-button>
        </div>
      </header>

      <div class="case-toolbar">
        <el-input v-model="caseKeyword" clearable placeholder="搜索用例名称" style="width: 260px" />
        <el-select v-model="statusFilter" clearable placeholder="状态" style="width: 130px">
          <el-option label="草稿" value="draft" />
          <el-option label="启用" value="active" />
          <el-option label="停用" value="inactive" />
        </el-select>
      </div>

      <div class="case-table">
        <el-empty v-if="!selectedApi" description="请选择接口" />
        <el-table v-else :data="filteredCases" v-loading="caseLoading" stripe height="100%">
          <el-table-column label="用例名称" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <el-button link type="primary" class="case-name-link" @click="openDebug(row)">{{ row.name }}</el-button>
            </template>
          </el-table-column>
          <el-table-column label="所属目录" min-width="200" show-overflow-tooltip>
            <template #default>{{ selectedDirectory }}</template>
          </el-table-column>
          <el-table-column label="运行结果" width="170">
            <template #default="{ row }">
              <span v-if="runResults[row.id]" class="run-result" :class="runResults[row.id].ok ? 'ok' : 'failed'">
                {{ runResults[row.id].ok ? "成功" : "失败" }} / {{ runResults[row.id].statusCode }}
              </span>
              <span v-else class="muted">未运行</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }"><span class="badge" :class="caseStatusClass(row.status)">{{ caseStatusText(row.status) }}</span></template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" :loading="runningCaseId === row.id" @click="runCase(row)">运行</el-button>
              <el-button link class="danger-link" @click="deleteCase(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <el-dialog v-model="caseDialog" title="新增用例" width="520px">
      <el-form :model="caseForm" label-width="86px">
        <el-form-item label="所属接口"><el-input :model-value="selectedApi?.name || ''" disabled /></el-form-item>
        <el-form-item label="用例名称" required><el-input v-model="caseForm.name" placeholder="例如：查询订单-正常订单" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="caseForm.status" style="width: 100%">
            <el-option label="草稿" value="draft" />
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="caseDialog = false">取消</el-button>
        <el-button type="primary" @click="saveCase">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="debugDrawer" direction="btt" size="72%" :with-header="false">
      <ApiCaseDebugDrawerContent
        v-if="debugCase && selectedApi"
        :case-name="debugCase.name"
        :request="currentDebugRequest"
        :result="debugResult"
        :environment-name="environmentName"
        :running="runningCaseId === debugCase.id"
        @run="runCase(debugCase)"
        @close="debugDrawer = false"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";
import ApiCaseDebugDrawerContent from "@/components/ApiCaseDebugDrawerContent.vue";

const props = defineProps<{
  environmentId?: number;
  environmentName?: string;
}>();

interface ApiDefinition {
  id: number;
  name: string;
  platform: string;
  module?: number;
  method: string;
  path: string;
  headers?: unknown[];
  query_params?: unknown[];
  body?: unknown;
  auth_config?: Record<string, unknown>;
  assertions?: unknown[];
  test_case_count?: number | null;
  status?: string;
}
interface ApiCase {
  id: number;
  api: number;
  name: string;
  status: string;
  request_override?: Record<string, any>;
  assertions?: unknown[];
}
interface TreeNode {
  key: string;
  id: number;
  type: "module" | "api";
  name: string;
  method?: string;
  level: number;
  caseCount?: number | null;
}

const keyword = ref("");
const caseKeyword = ref("");
const statusFilter = ref("");
const caseLoading = ref(false);
const caseDialog = ref(false);
const debugDrawer = ref(false);
const runningCaseId = ref<number>();
const batchRunning = ref(false);
const platforms = ref<any[]>([]);
const modules = ref<any[]>([]);
const apis = ref<ApiDefinition[]>([]);
const cases = ref<ApiCase[]>([]);
const selectedApiId = ref<number>();
const expandedPlatforms = ref<string[]>([]);
const expandedModules = ref<number[]>([]);
const debugCase = ref<ApiCase>();
const debugResult = ref<any>();
const runResults = reactive<Record<number, { ok: boolean; statusCode: string; result: any }>>({});
const caseForm = reactive({ name: "", status: "draft" });
const debugPayload = reactive({ method: "GET", path: "" });

const platformCode = (item: any) => item.code?.toUpperCase?.() || item.code || "";
const platformOptions = computed(() => platforms.value.map((item) => ({ ...item, code: platformCode(item) })));
const selectedApi = computed(() => apis.value.find((item) => item.id === selectedApiId.value));
const caseCount = (api: ApiDefinition) => api.test_case_count === null || api.test_case_count === undefined ? 0 : Number(api.test_case_count || 0);
const caseCountText = (value: number | null | undefined) => value === null || value === undefined ? "-" : String(value);
const totalCaseCount = computed(() => apis.value.reduce((sum, api) => sum + caseCount(api), 0));
const filteredCases = computed(() => cases.value.filter((item) => {
  const nameMatched = !caseKeyword.value || item.name.toLowerCase().includes(caseKeyword.value.toLowerCase());
  const statusMatched = !statusFilter.value || item.status === statusFilter.value;
  return nameMatched && statusMatched;
}));
const selectedDirectory = computed(() => selectedApi.value ? directoryForApi(selectedApi.value).join(" / ") : "");
const currentDebugRequest = computed(() => buildDebugPayload());

const modulesForPlatform = (code: string) => modules.value.filter((item) => (item.platform || platformCode(platforms.value.find((p) => p.id === item.managed_platform))) === code);
const childModules = (parentId?: number) => modules.value.filter((item) => (item.parent || undefined) === parentId);
const apisForModule = (moduleId?: number, platform?: string) => apis.value.filter((api) => (moduleId ? api.module === moduleId : !api.module && api.platform === platform));
const hasModuleChildren = (moduleId: number) => childModules(moduleId).length > 0 || apisForModule(moduleId).length > 0;
const platformCaseCount = (platform: string) => apis.value.filter((api) => api.platform === platform).reduce((sum, api) => sum + caseCount(api), 0);
const moduleCaseCount = (moduleId: number): number => {
  const own = apisForModule(moduleId).reduce((sum, api) => sum + caseCount(api), 0);
  return own + childModules(moduleId).reduce((sum, child) => sum + moduleCaseCount(child.id), 0);
};
const platformHasChildren = (platform: string) => modulesForPlatform(platform).length > 0 || apisForModule(undefined, platform).length > 0;

const visibleNodes = (platform: string) => {
  const matches = (text: string) => !keyword.value || text.toLowerCase().includes(keyword.value.toLowerCase());
  const nodes: TreeNode[] = [];
  const visitModule = (module: any, level: number) => {
    const moduleApis = apisForModule(module.id);
    if (matches(module.name)) nodes.push({ key: `module-${module.id}`, id: module.id, type: "module", name: module.name, level, caseCount: moduleCaseCount(module.id) });
    if (expandedModules.value.includes(module.id) || keyword.value) {
      childModules(module.id).forEach((child) => visitModule(child, level + 1));
      moduleApis.filter((api) => matches(`${api.name} ${api.path}`)).forEach((api) => nodes.push({ key: `api-${api.id}`, id: api.id, type: "api", name: api.name, method: api.method, level: level + 1, caseCount: api.test_case_count }));
    }
  };
  modulesForPlatform(platform).filter((item) => !item.parent).forEach((module) => visitModule(module, 0));
  apisForModule(undefined, platform).filter((api) => matches(`${api.name} ${api.path}`)).forEach((api) => nodes.push({ key: `api-${api.id}`, id: api.id, type: "api", name: api.name, method: api.method, level: 0, caseCount: api.test_case_count }));
  return nodes;
};

const directoryForApi = (api: ApiDefinition) => {
  const names = [platformOptions.value.find((item) => item.code === api.platform)?.name || api.platform];
  let module = modules.value.find((item) => item.id === api.module);
  const moduleNames = [];
  while (module) {
    moduleNames.unshift(module.name);
    module = modules.value.find((item) => item.id === module.parent);
  }
  return [...names, ...moduleNames, api.name];
};

const togglePlatform = (platform: string) => {
  if (!platformHasChildren(platform)) return;
  expandedPlatforms.value = expandedPlatforms.value.includes(platform) ? expandedPlatforms.value.filter((item) => item !== platform) : [...expandedPlatforms.value, platform];
};
const toggleModule = (moduleId: number) => {
  expandedModules.value = expandedModules.value.includes(moduleId) ? expandedModules.value.filter((item) => item !== moduleId) : [...expandedModules.value, moduleId];
};
const selectApi = async (apiId: number) => {
  selectedApiId.value = apiId;
  await loadCases();
};

const load = async () => {
  const [platformResp, moduleResp, apiResp] = await Promise.all([
    platformApi.platforms(),
    platformApi.apiModules(),
    platformApi.apiDefinitions({ single_case_tree: true }),
  ]);
  platforms.value = unwrapList(platformResp.data);
  modules.value = unwrapList(moduleResp.data);
  apis.value = unwrapList<ApiDefinition>(apiResp.data);
  expandedPlatforms.value = platformOptions.value.map((item) => item.code);
  expandedModules.value = modules.value.map((item) => item.id);
  if (!selectedApiId.value && apis.value.length) selectedApiId.value = apis.value[0].id;
  await loadCases();
};

const loadCases = async () => {
  if (!selectedApiId.value) return;
  caseLoading.value = true;
  try {
    const { data } = await platformApi.apiTestCases({ api: selectedApiId.value });
    cases.value = unwrapList<ApiCase>(data);
  } finally {
    caseLoading.value = false;
  }
};

const caseStatusText = (status: string) => ({ draft: "草稿", active: "启用", inactive: "停用" }[status] || status);
const caseStatusClass = (status: string) => (status === "active" ? "badge-success" : status === "inactive" ? "badge-danger" : "badge-warning");

const openCreateDialog = () => {
  caseForm.name = "";
  caseForm.status = "draft";
  caseDialog.value = true;
};
const saveCase = async () => {
  if (!selectedApiId.value || !caseForm.name.trim()) {
    ElMessage.warning("请先选择接口并填写用例名称");
    return;
  }
  await platformApi.createApiTestCase({ api: selectedApiId.value, name: caseForm.name.trim(), status: caseForm.status, priority: "P1", is_active: caseForm.status !== "inactive" });
  ElMessage.success("用例已保存");
  caseDialog.value = false;
  await load();
};
const deleteCase = async (row: ApiCase) => {
  await ElMessageBox.confirm(`确认删除用例「${row.name}」？`, "删除确认", { type: "warning" });
  await platformApi.deleteApiTestCase(row.id);
  ElMessage.success("用例已删除");
  await load();
};

const openDebug = (row: ApiCase) => {
  debugCase.value = row;
  const override = row.request_override || {};
  debugPayload.method = override.method || selectedApi.value?.method || "GET";
  debugPayload.path = override.path || selectedApi.value?.path || "";
  debugResult.value = runResults[row.id]?.result || null;
  debugDrawer.value = true;
};
const buildDebugPayload = () => {
  const override = debugCase.value?.request_override || {};
  return {
    method: override.method || selectedApi.value?.method,
    path: override.path || selectedApi.value?.path,
    platform: selectedApi.value?.platform,
    module: selectedApi.value?.module,
    environment: props.environmentId,
    headers: override.headers || selectedApi.value?.headers || [],
    query_params: override.query_params || selectedApi.value?.query_params || [],
    body: override.body ?? selectedApi.value?.body ?? {},
    auth_config: override.auth_config || selectedApi.value?.auth_config || {},
    assertions: debugCase.value?.assertions?.length ? debugCase.value.assertions : selectedApi.value?.assertions || [],
  };
};
const runCase = async (row: ApiCase) => {
  if (!selectedApi.value) return;
  if (!props.environmentId) {
    ElMessage.warning("请先在页面顶部选择执行环境");
    return;
  }
  if (debugCase.value?.id !== row.id) openDebug(row);
  runningCaseId.value = row.id;
  try {
    const { data } = await platformApi.debugApi(buildDebugPayload());
    debugResult.value = data;
    const statusCode = String(data?.response?.status_code || "-");
    runResults[row.id] = { ok: Boolean(data?.ok) && Number(data?.response?.status_code || 0) < 400, statusCode, result: data };
  } catch (error: any) {
    const message = error?.message || "用例运行失败";
    const result = {
      ok: false,
      passed: false,
      request: buildDebugPayload(),
      response: { elapsed_ms: 0 },
      assertions: [],
      logs: [message],
      error: message,
    };
    debugResult.value = result;
    runResults[row.id] = { ok: false, statusCode: "-", result };
  } finally {
    runningCaseId.value = undefined;
  }
};

const runAllCases = async () => {
  if (!selectedApi.value || !filteredCases.value.length) return;
  batchRunning.value = true;
  try {
    for (const item of filteredCases.value) {
      await runCase(item);
    }
    ElMessage.success("当前接口下用例已运行完成");
  } finally {
    batchRunning.value = false;
  }
};

defineExpose({ load, openCreateDialog });

onMounted(load);
</script>

<style scoped>
.single-case-workbench { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 16px; height: calc(100vh - 176px); min-height: 620px; }
.single-case-tree, .single-case-main { min-height: 0; border: 1px solid var(--el-border-color-light); border-radius: 8px; background: var(--el-bg-color); }
.single-case-tree { display: flex; flex-direction: column; padding: 14px; gap: 12px; }
.tree-head, .single-case-head, .case-toolbar, .debug-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.tree-head strong, .single-case-head h2, .debug-head h3 { margin: 0; }
.tree-head span, .single-case-head p, .muted { color: var(--el-text-color-secondary); font-size: 13px; }
.tree-body { overflow: auto; min-height: 0; }
.tree-row { width: 100%; min-height: 36px; display: flex; align-items: center; gap: 6px; border: 0; background: transparent; color: var(--el-text-color-primary); cursor: pointer; border-radius: 8px; padding: 0 8px; text-align: left; }
.tree-row:hover, .tree-row.active { background: var(--brand-lighter, var(--el-fill-color-light)); color: var(--brand, var(--el-color-primary)); }
.tree-row.api.active { color: var(--brand, var(--el-color-primary)); font-weight: 600; }
.tree-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tree-row em { min-width: 28px; text-align: right; color: var(--el-text-color-secondary); font-style: normal; font-size: 12px; }
.twisty { width: 14px; display: inline-flex; justify-content: center; transition: transform .16s ease; }
.twisty.expanded { transform: rotate(90deg); }
.single-case-main { display: flex; flex-direction: column; padding: 16px; gap: 14px; }
.case-table { min-height: 0; flex: 1; }
.case-name-link { padding: 0; }
.run-result { font-weight: 600; }
.run-result.ok { color: var(--el-color-success); }
.run-result.failed { color: var(--el-color-danger); }
.debug-drawer { height: 100%; display: flex; flex-direction: column; gap: 14px; padding: 18px; }
.debug-grid { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.debug-grid section { min-height: 0; border: 1px solid var(--el-border-color-light); border-radius: 8px; padding: 12px; overflow: auto; }
.debug-grid h4 { margin: 0 0 10px; }
.debug-grid pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-size: 12px; }
@media (max-width: 980px) { .single-case-workbench { grid-template-columns: 1fr; height: auto; } .single-case-tree { max-height: 360px; } .debug-grid { grid-template-columns: 1fr; } }
</style>
