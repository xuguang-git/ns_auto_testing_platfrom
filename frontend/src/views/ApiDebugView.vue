<template>
  <div class="debug-workspace">
    <aside class="collection-panel">
      <div class="collection-header">
        <el-input v-model="keyword" size="small" placeholder="搜索接口..." clearable />
        <el-button size="small" type="primary" @click="newRequest">新建</el-button>
      </div>
      <div class="collection-tree">
        <section v-for="platform in platformOptions" :key="platform.code" class="tree-group">
          <button class="tree-group-header" @click="togglePlatform(platform.code)">
            <span v-if="platformHasChildren(platform.code)" class="tree-toggle" :class="{ expanded: expandedPlatforms.includes(platform.code) }">›</span>
            {{ platform.name }}
            <span :class="['platform-badge', platform.code.toLowerCase()]">{{ platform.code }}</span>
          </button>
          <div v-show="expandedPlatforms.includes(platform.code)" class="tree-group-body">
            <template v-for="module in rootModulesForPlatform(platform.code)" :key="module.id">
              <button class="tree-module-title tree-branch-title" @click="toggleModule(module.id)">
                <span v-if="moduleHasChildren(platform.code, module.id)" class="tree-toggle" :class="{ expanded: expandedModules.includes(module.id) }">›</span>
                <span>{{ module.name }}</span>
              </button>
              <template v-if="expandedModules.includes(module.id)">
                <button
                  v-for="item in groupedApisByModule(platform.code, module.id)"
                  :key="item.id"
                  class="tree-api-item"
                  :class="{ active: selectedApi?.id === item.id }"
                  @click="selectApi(item)"
                >
                  <span :class="['method-badge', item.method]">{{ item.method }}</span>
                  <span class="api-name">{{ item.name }}</span>
                </button>
              </template>
            </template>
            <button
              v-for="item in groupedApisWithoutModule(platform.code)"
              :key="item.id"
              class="tree-api-item"
              :class="{ active: selectedApi?.id === item.id }"
              @click="selectApi(item)"
            >
              <span :class="['method-badge', item.method]">{{ item.method }}</span>
              <span class="api-name">{{ item.name }}</span>
            </button>
            <div v-if="!groupedApis[platform.code]?.length" class="tree-empty">暂无接口</div>
          </div>
        </section>
      </div>
    </aside>

    <section class="debug-main-panel">
      <div class="request-tabs-bar">
        <button v-for="tab in openTabs" :key="tab.id" class="request-tab" :class="{ active: tab.id === activeRequestTab }" @click="activeRequestTab = tab.id">
          <span :class="['tab-method', tab.method]">{{ tab.method }}</span>
          <span>{{ tab.name }}</span>
          <span class="close-tab" @click.stop="closeTab(tab.id)">×</span>
        </button>
        <button class="new-tab-btn" title="新建请求" @click="newRequest">+</button>
      </div>

      <div class="url-bar">
        <el-select v-model="form.method" class="method-select" size="small">
          <el-option v-for="method in methods" :key="method" :label="method" :value="method" />
        </el-select>
        <el-select v-model="form.platform" placeholder="平台" class="debug-env-select" size="small" @change="form.module = undefined">
          <el-option v-for="platform in platformOptions" :key="platform.id" :label="platform.name" :value="platform.code" />
        </el-select>
        <div class="url-input-wrap">
          <span class="url-prefix">{{ currentBaseUrl }}</span>
          <el-input v-model="form.path" class="url-input" size="small" placeholder="/api/v1/orders" />
        </div>
        <el-select v-model="form.environment" placeholder="Env" clearable class="debug-env-select" size="small">
          <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
        </el-select>
        <el-select v-model="form.module" placeholder="模块" clearable class="debug-env-select" size="small">
          <el-option v-for="module in availableFormModules" :key="module.id" :label="module.name" :value="module.id" />
        </el-select>
        <el-button size="small" :loading="saving" @click="saveCurrent">Save</el-button>
        <el-button size="small" type="primary" :loading="sending" @click="send">Send</el-button>
      </div>

      <div class="editor-response-split">
        <section class="request-editor">
          <el-tabs v-model="activeReqTab" class="panel-tabs">
            <el-tab-pane name="params">
              <template #label><span class="panel-tab-label"><span class="tab-icon" v-html="tabIcons.params"></span>Params</span></template>
              <KeyValueEditor v-model="paramsRows" />
            </el-tab-pane>
            <el-tab-pane name="headers">
              <template #label><span class="panel-tab-label"><span class="tab-icon" v-html="tabIcons.headers"></span>Headers</span></template>
              <KeyValueEditor v-model="headerRows" />
            </el-tab-pane>
            <el-tab-pane name="auth">
              <template #label><span class="panel-tab-label"><span class="tab-icon" v-html="tabIcons.auth"></span>Auth</span></template>
              <div class="auth-grid">
                <el-select v-model="authType">
                  <el-option label="No Auth" value="none" />
                  <el-option label="Bearer Token" value="bearer" />
                  <el-option label="Basic Auth" value="basic" />
                  <el-option label="API Key" value="api_key" />
                  <el-option label="OAuth 2.0" value="oauth2" disabled />
                </el-select>
                <el-input v-model="authToken" placeholder="{{token}}" />
              </div>
            </el-tab-pane>
            <el-tab-pane name="body">
              <template #label><span class="panel-tab-label"><span class="tab-icon" v-html="tabIcons.body"></span>Body</span></template>
              <div class="body-type-row">
                <el-radio-group v-model="bodyType" size="small">
                  <el-radio-button label="none">none</el-radio-button>
                  <el-radio-button label="json">raw JSON</el-radio-button>
                  <el-radio-button label="form-data">form-data</el-radio-button>
                  <el-radio-button label="x-www-form-urlencoded">x-www-form-urlencoded</el-radio-button>
                </el-radio-group>
              </div>
              <el-input v-model="bodyText" type="textarea" :rows="8" placeholder='{"name":"demo"}' />
            </el-tab-pane>
            <el-tab-pane name="preScript">
              <template #label><span class="panel-tab-label"><span class="tab-icon" v-html="tabIcons.preScript"></span>Pre-Script</span></template>
              <el-input v-model="preScript" type="textarea" :rows="8" placeholder="// Runs before request" />
            </el-tab-pane>
            <el-tab-pane name="postScript">
              <template #label><span class="panel-tab-label"><span class="tab-icon" v-html="tabIcons.postScript"></span>Post-Script</span></template>
              <el-input v-model="postScript" type="textarea" :rows="8" placeholder="// Runs after response" />
            </el-tab-pane>
            <el-tab-pane name="assertions">
              <template #label><span class="panel-tab-label"><span class="tab-icon" v-html="tabIcons.tests"></span>Tests</span></template>
              <el-input v-model="assertionsText" type="textarea" :rows="8" placeholder='[{"type":"status_code","operator":"eq","expected":200}]' />
            </el-tab-pane>
          </el-tabs>
        </section>

        <div class="panel-resizer"></div>

        <section class="response-panel">
          <div class="response-tabs-bar">
            <button v-for="tab in responseTabs" :key="tab.name" class="panel-tab-button" :class="{ active: activeRespTab === tab.name }" @click="activeRespTab = tab.name">
              <span class="panel-tab-label"><span class="tab-icon" v-html="tab.icon"></span>{{ tab.label }}</span>
              <span v-if="tab.name === 'assertions'" class="tab-count">{{ assertionPassed }}/{{ debugResult?.assertions?.length || 0 }}</span>
            </button>
            <div class="response-status">
              <span :class="statusClass">{{ debugResult?.response?.status_code || "-" }}</span>
              <span>{{ debugResult?.response?.elapsed_ms || "-" }}ms</span>
              <span>{{ formatSize(debugResult?.response?.size) }}</span>
            </div>
          </div>
          <div class="response-body">
            <pre v-if="activeRespTab === 'body'">{{ responseBodyText }}</pre>
            <pre v-else-if="activeRespTab === 'headers'">{{ responseHeadersText }}</pre>
            <ul v-else-if="activeRespTab === 'assertions'" class="assertion-list">
              <li v-for="item in debugResult?.assertions || []" :key="item.name + item.type" :class="{ passed: item.passed }">
                <span>{{ item.passed ? "PASS" : "FAIL" }}</span>
                <strong>{{ item.name }}</strong>
                <em>expected {{ item.expected }}, actual {{ item.actual }}</em>
              </li>
            </ul>
            <pre v-else-if="activeRespTab === 'cookies'">No cookies parsed.</pre>
            <pre v-else>{{ (debugResult?.logs || []).join("\n") || "Logs will appear after sending a request." }}</pre>
          </div>
        </section>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, defineComponent, h, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";

import { platformApi, unwrapList } from "@/api/platform";

interface RowItem {
  enabled: boolean;
  key: string;
  value: string;
  description?: string;
}

interface ApiDefinition {
  id: number;
  project: number;
  name: string;
  platform: string;
  method: string;
  path: string;
  module?: number;
  status?: string;
  headers: RowItem[];
  query_params: RowItem[];
  body: unknown;
  body_type?: string;
  auth_config: Record<string, unknown>;
  assertions: unknown[];
}

interface Environment {
  id: number;
  name: string;
  platform_base_urls?: Record<string, string>;
  base_url?: string;
}

const KeyValueEditor = defineComponent({
  props: { modelValue: { type: Array, required: true } },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const update = (index: number, key: keyof RowItem, value: string | boolean) => {
      const rows = [...(props.modelValue as RowItem[])];
      rows[index] = { ...rows[index], [key]: value };
      emit("update:modelValue", rows);
    };
    const add = () => emit("update:modelValue", [...(props.modelValue as RowItem[]), { enabled: true, key: "", value: "", description: "" }]);
    return () =>
      h("div", { class: "kv-editor" }, [
        h("table", { class: "kv-table" }, [
          h("thead", [h("tr", [h("th", ""), h("th", "Key"), h("th", "Value"), h("th", "Description")])]),
          h(
            "tbody",
            (props.modelValue as RowItem[]).map((row, index) =>
              h("tr", { key: index }, [
                h("td", [h("input", { type: "checkbox", checked: row.enabled, onChange: (e: Event) => update(index, "enabled", (e.target as HTMLInputElement).checked) })]),
                h("td", [h("input", { value: row.key, onInput: (e: Event) => update(index, "key", (e.target as HTMLInputElement).value) })]),
                h("td", [h("input", { value: row.value, onInput: (e: Event) => update(index, "value", (e.target as HTMLInputElement).value) })]),
                h("td", [h("input", { value: row.description, onInput: (e: Event) => update(index, "description", (e.target as HTMLInputElement).value) })]),
              ]),
            ),
          ),
        ]),
        h("button", { class: "add-row", onClick: add }, "+ Add row"),
      ]);
  },
});

const methods = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const route = useRoute();
const svg = (path: string) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;
const tabIcons = {
  request: svg('<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>'),
  body: svg('<path d="M8 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2h-2"/><rect x="8" y="2" width="8" height="4" rx="1"/><path d="M8 11h8"/><path d="M8 15h5"/>'),
  headers: svg('<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h10"/>'),
  auth: svg('<rect x="3" y="11" width="18" height="10" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>'),
  params: svg('<circle cx="6" cy="12" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 12h4"/><path d="M14 8l2-1"/><path d="M14 16l2 1"/>'),
  preScript: svg('<path d="M8 9l-4 3 4 3"/><path d="M16 9l4 3-4 3"/><path d="M14 4l-4 16"/>'),
  postScript: svg('<path d="M20 6L9 17l-5-5"/><path d="M14 6h6v6"/>'),
  tests: svg('<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>'),
  cookies: svg('<path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-4-4 4 4 0 0 1-6-6"/><circle cx="8.5" cy="10.5" r=".8"/><circle cx="13.5" cy="15.5" r=".8"/><circle cx="9.5" cy="16.5" r=".8"/>'),
  console: svg('<path d="M4 17l6-6-6-6"/><path d="M12 19h8"/>'),
};
const responseTabs = [
  { label: "Body", name: "body", icon: tabIcons.body },
  { label: "Headers", name: "headers", icon: tabIcons.headers },
  { label: "Test Results", name: "assertions", icon: tabIcons.tests },
  { label: "Cookies", name: "cookies", icon: tabIcons.cookies },
  { label: "Console", name: "logs", icon: tabIcons.console },
];
const requestTabIcon = (method: string) => (method === "GET" ? tabIcons.params : method === "DELETE" ? tabIcons.tests : tabIcons.request);

const keyword = ref("");
const sending = ref(false);
const saving = ref(false);
const apis = ref<ApiDefinition[]>([]);
const platforms = ref<any[]>([]);
const modules = ref<any[]>([]);
const environments = ref<Environment[]>([]);
const selectedApi = ref<ApiDefinition | null>(null);
const debugResult = ref<any>(null);
const expandedPlatforms = ref<string[]>([]);
const expandedModules = ref<number[]>([]);
const openTabs = ref<{ id: number; name: string; method: string }[]>([]);
const activeRequestTab = ref<number | null>(null);
const activeReqTab = ref("params");
const activeRespTab = ref("body");
const paramsRows = ref<RowItem[]>([{ enabled: true, key: "page", value: "1", description: "page number" }]);
const headerRows = ref<RowItem[]>([{ enabled: true, key: "Content-Type", value: "application/json", description: "" }]);
const bodyType = ref("none");
const bodyText = ref("{}");
const preScript = ref("");
const postScript = ref("");
const assertionsText = ref('[{"type":"status_code","operator":"eq","expected":200}]');
const authType = ref("none");
const authToken = ref("");
const form = reactive({ method: "GET", path: "", platform: "ERP", module: undefined as number | undefined, environment: undefined as number | undefined });

const filteredApis = computed(() => apis.value.filter((item) => !keyword.value || item.name.includes(keyword.value) || item.path.includes(keyword.value)));
const platformCode = (platform: any) => platform.code?.toUpperCase?.() || platform.code || "";
const platformOptions = computed(() => platforms.value.map((item) => ({ id: item.id, name: item.name, code: platformCode(item) })));
const modulePlatformCode = (module: any) => module.platform || platformCode(platforms.value.find((item) => item.id === module.managed_platform));
const modulesForPlatform = (code: string) => modules.value.filter((item) => modulePlatformCode(item) === code);
const rootModulesForPlatform = (code: string) => modulesForPlatform(code).filter((item) => !item.parent);
const childModules = (parentId: number) => modules.value.filter((item) => item.parent === parentId);
const availableFormModules = computed(() => modulesForPlatform(form.platform));
const groupedApis = computed(() =>
  platformOptions.value.reduce<Record<string, ApiDefinition[]>>((acc, platform) => {
    acc[platform.code] = filteredApis.value.filter((item) => item.platform === platform.code);
    return acc;
  }, {}),
);
const groupedApisByModule = (platform: string, moduleId: number) => (groupedApis.value[platform] || []).filter((item) => item.module === moduleId);
const groupedApisWithoutModule = (platform: string) => (groupedApis.value[platform] || []).filter((item) => !item.module);
const platformHasChildren = (platform: string) => rootModulesForPlatform(platform).length > 0 || groupedApisWithoutModule(platform).length > 0;
const moduleHasChildren = (platform: string, moduleId: number) => childModules(moduleId).length > 0 || groupedApisByModule(platform, moduleId).length > 0;
const currentEnvironment = computed(() => environments.value.find((item) => item.id === form.environment));
const currentBaseUrl = computed(() => currentEnvironment.value?.platform_base_urls?.[form.platform] || currentEnvironment.value?.base_url || "{{host}}");
const assertionPassed = computed(() => (debugResult.value?.assertions || []).filter((item: any) => item.passed).length);
const responseBodyText = computed(() => JSON.stringify(debugResult.value?.response?.body ?? {}, null, 2));
const responseHeadersText = computed(() => JSON.stringify(debugResult.value?.response?.headers ?? {}, null, 2));
const statusClass = computed(() => {
  const code = Number(debugResult.value?.response?.status_code || 0);
  if (code >= 200 && code < 300) return "status-ok";
  if (code >= 400 && code < 500) return "status-warn";
  if (code >= 500) return "status-error";
  return "";
});

const parseJson = (text: string, fallback: unknown) => {
  try {
    return JSON.parse(text);
  } catch {
    return fallback;
  }
};


const togglePlatform = (platform: string) => {
  if (!platformHasChildren(platform)) return;
  expandedPlatforms.value = expandedPlatforms.value.includes(platform)
    ? expandedPlatforms.value.filter((item) => item !== platform)
    : [...expandedPlatforms.value, platform];
};
const toggleModule = (moduleId: number) => {
  expandedModules.value = expandedModules.value.includes(moduleId) ? expandedModules.value.filter((item) => item !== moduleId) : [...expandedModules.value, moduleId];
};

const selectApi = (item: ApiDefinition) => {
  selectedApi.value = item;
  form.method = item.method;
  form.path = item.path;
  form.platform = item.platform;
  form.module = item.module;
  paramsRows.value = item.query_params?.length ? item.query_params : [{ enabled: true, key: "", value: "", description: "" }];
  headerRows.value = item.headers?.length ? item.headers : [{ enabled: true, key: "Content-Type", value: "application/json", description: "" }];
  bodyType.value = item.body_type || "none";
  bodyText.value = JSON.stringify(item.body || {}, null, 2);
  assertionsText.value = JSON.stringify(item.assertions?.length ? item.assertions : [{ type: "status_code", operator: "eq", expected: 200 }], null, 2);
  if (!openTabs.value.some((tab) => tab.id === item.id)) openTabs.value.push({ id: item.id, name: item.name, method: item.method });
  activeRequestTab.value = item.id;
};

const newRequest = () => {
  selectedApi.value = null;
  form.method = "GET";
  form.path = "";
  form.platform = platformOptions.value[0]?.code || "ERP";
  form.module = undefined;
  paramsRows.value = [{ enabled: true, key: "", value: "", description: "" }];
  headerRows.value = [{ enabled: true, key: "Content-Type", value: "application/json", description: "" }];
  bodyType.value = "none";
  bodyText.value = "{}";
  assertionsText.value = '[{"type":"status_code","operator":"eq","expected":200}]';
  debugResult.value = null;
};

const closeTab = (id: number) => {
  openTabs.value = openTabs.value.filter((tab) => tab.id !== id);
  if (activeRequestTab.value === id) activeRequestTab.value = openTabs.value[0]?.id || null;
};

const send = async () => {
  sending.value = true;
  try {
    const { data } = await platformApi.debugApi({
      method: form.method,
      path: form.path,
      platform: form.platform,
      module: form.module,
      environment: form.environment,
      query_params: paramsRows.value,
      headers: headerRows.value,
      body: parseJson(bodyText.value, {}),
      auth_config: { type: authType.value, token: authToken.value },
      assertions: parseJson(assertionsText.value, []),
    });
    debugResult.value = data;
    activeRespTab.value = "body";
  } finally {
    sending.value = false;
  }
};

const saveCurrent = async () => {
  if (!form.path.trim()) {
    ElMessage.warning("请先填写请求路径");
    return;
  }
  if (!form.platform || !form.module) {
    ElMessage.warning("请先选择平台和模块");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      name: selectedApi.value?.name || `${form.method} ${form.path}`,
      platform: form.platform,
      method: form.method,
      path: form.path,
      status: selectedApi.value?.status || "developing",
      headers: headerRows.value,
      query_params: paramsRows.value,
      body_type: bodyType.value,
      body: parseJson(bodyText.value, {}),
      assertions: parseJson(assertionsText.value, []),
      is_active: true,
    };
    if (selectedApi.value?.id) {
      const { data } = await platformApi.updateApiDefinition(selectedApi.value.id, payload);
      selectedApi.value = data;
      ElMessage.success("请求已保存");
    } else {
      const { data } = await platformApi.createApiDefinition(payload);
      apis.value.unshift(data);
      selectApi(data);
      ElMessage.success("请求已新增");
    }
  } finally {
    saving.value = false;
  }
};

const formatSize = (size?: number) => {
  if (!size) return "-";
  return size > 1024 ? `${(size / 1024).toFixed(1)}KB` : `${size}B`;
};

onMounted(async () => {
  const [apiResp, envResp, platformResp, moduleResp] = await Promise.all([
    platformApi.apiDefinitions(),
    platformApi.environments(),
    platformApi.platforms(),
    platformApi.apiModules(),
  ]);
  apis.value = unwrapList<ApiDefinition>(apiResp.data);
  environments.value = unwrapList<Environment>(envResp.data);
  platforms.value = unwrapList(platformResp.data);
  modules.value = unwrapList(moduleResp.data);
  expandedPlatforms.value = platformOptions.value.filter((item) => platformHasChildren(item.code)).map((item) => item.code);
  expandedModules.value = modules.value.filter((item) => moduleHasChildren(modulePlatformCode(item), item.id)).map((item) => item.id);
  form.platform = platformOptions.value[0]?.code || "ERP";
  form.environment = environments.value[0]?.id;
  const queryApi = Number(route.query.apiId);
  const initialApi = apis.value.find((item) => item.id === queryApi) || apis.value[0];
  if (initialApi) selectApi(initialApi);
});
</script>
