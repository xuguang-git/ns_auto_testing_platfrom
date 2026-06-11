<template>
  <div class="module-layout">
    <aside class="secondary-panel">
      <div class="secondary-header">
        <strong>环境列表</strong>
        <el-button size="small" type="primary" @click="openEnvCreate">新增</el-button>
      </div>
      <div class="secondary-body">
        <button
          v-for="env in environments"
          :key="env.id"
          class="secondary-item"
          :class="{ active: selectedEnvironment?.id === env.id }"
          @click="selectEnvironment(env)"
        >
          <span>{{ env.name }}</span>
          <el-tag size="small" :type="env.is_default ? 'success' : 'info'">{{ envTypeText(env.env_type) }}</el-tag>
        </button>
        <el-empty v-if="!environments.length && !loading" description="暂无环境" />
      </div>
    </aside>

    <section class="work-panel">
      <div class="work-toolbar">
        <div class="toolbar-left">
          <el-input v-model="keyword" clearable placeholder="搜索变量 key、说明" style="width: 300px" />
          <el-select v-model="platformFilter" clearable placeholder="平台" style="width: 150px">
            <el-option v-for="platform in platformOptions" :key="platform.code" :label="platform.name" :value="platform.code" />
          </el-select>
        </div>
        <div class="toolbar-right">
          <el-button @click="load">刷新</el-button>
          <el-button :disabled="!selectedEnvironment" @click="openEnvEdit">编辑环境</el-button>
          <el-button :disabled="!selectedEnvironment" class="danger-link" @click="removeEnvironment">删除环境</el-button>
          <el-button type="primary" :disabled="!selectedEnvironment" @click="openVarCreate">新增变量</el-button>
        </div>
      </div>

      <div class="table-area">
        <el-card v-if="selectedEnvironment" shadow="never" class="panel-card" style="margin-top: 0">
          <template #header>
            <div class="card-header">
              <span>{{ selectedEnvironment.name }}</span>
              <el-tag>{{ selectedEnvironment.is_default ? "默认环境" : envTypeText(selectedEnvironment.env_type) }}</el-tag>
            </div>
          </template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="环境类型">{{ envTypeText(selectedEnvironment.env_type) }}</el-descriptions-item>
            <el-descriptions-item label="默认环境">{{ selectedEnvironment.is_default ? "是" : "否" }}</el-descriptions-item>
            <el-descriptions-item label="只读">{{ selectedEnvironment.is_readonly ? "是" : "否" }}</el-descriptions-item>
            <el-descriptions-item label="兜底 Base URL" :span="3">{{ selectedEnvironment.base_url || "未配置" }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card v-if="selectedEnvironment" shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>平台访问地址</span>
              <span>接口调试会按接口所属平台优先取这里的地址</span>
            </div>
          </template>
          <el-table :data="platformUrlRows" stripe>
            <el-table-column prop="name" label="平台" width="180" />
            <el-table-column prop="code" label="平台编码" width="120" />
            <el-table-column label="IP / Base URL" min-width="360">
              <template #default="{ row }">
                <span class="inline-code">{{ row.url || selectedEnvironment.base_url || "未配置" }}</span>
                <el-tag v-if="!row.url && selectedEnvironment.base_url" size="small" type="info" style="margin-left: 8px">使用兜底</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card v-if="selectedEnvironment" shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>全局前置操作</span>
              <div class="card-header-actions">
                <el-tag :type="preRequestOperations.length ? 'success' : 'info'">共 {{ preRequestOperations.length }} 个</el-tag>
                <el-button size="small" type="primary" @click="openPreRequestCreate">新增前置操作</el-button>
              </div>
            </div>
          </template>
          <el-table :data="preRequestOperations" stripe>
            <el-table-column prop="name" label="操作名称" min-width="160" show-overflow-tooltip />
            <el-table-column label="生效模块" min-width="240" show-overflow-tooltip>
              <template #default="{ row }">{{ operationScopeText(row) }}</template>
            </el-table-column>
            <el-table-column label="Token 变量" width="130">
              <template #default="{ row }">{{ row.config?.token_key || "token" }}</template>
            </el-table-column>
            <el-table-column label="登录请求" min-width="240" show-overflow-tooltip>
              <template #default="{ row }">{{ operationLoginText(row) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="row.is_enabled ? 'success' : 'info'">{{ row.is_enabled ? "启用" : "停用" }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openPreRequestEdit(row)">编辑</el-button>
                <el-button link class="danger-link" @click="removePreRequest(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>环境变量</span>
              <span>共 {{ filteredVariables.length }} 个</span>
            </div>
          </template>
          <el-table :data="filteredVariables" v-loading="loading" stripe>
            <el-table-column prop="key" label="变量 Key" min-width="170" />
            <el-table-column label="变量值" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">{{ row.display_value ?? row.value }}</template>
            </el-table-column>
            <el-table-column label="平台" width="120">
              <template #default="{ row }">{{ row.platform ? platformName(row.platform) : "全局" }}</template>
            </el-table-column>
            <el-table-column prop="scope" label="作用域" width="120" />
            <el-table-column label="敏感" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.is_secret ? 'warning' : 'info'">{{ row.is_secret ? "是" : "否" }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openVarEdit(row)">编辑</el-button>
                <el-button link class="danger-link" @click="removeVariable(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </section>

    <el-dialog v-model="envDialogVisible" :title="editingEnvId ? '编辑环境' : '新增环境'" width="720px">
      <el-form :model="envForm" label-width="110px">
        <el-form-item label="环境名称" required>
          <el-input v-model="envForm.name" placeholder="测试环境" />
        </el-form-item>
        <el-form-item label="环境类型">
          <el-select v-model="envForm.env_type" style="width: 100%">
            <el-option label="开发" value="dev" />
            <el-option label="测试" value="test" />
            <el-option label="预发" value="staging" />
            <el-option label="生产" value="prod" />
          </el-select>
        </el-form-item>
        <el-form-item label="兜底 Base URL">
          <el-input v-model="envForm.base_url" placeholder="未配置平台地址时使用，例如 http://127.0.0.1:8000" />
        </el-form-item>
        <el-form-item label="平台地址">
          <div class="platform-url-editor">
            <div v-for="platform in platformOptions" :key="platform.code" class="platform-url-row">
              <span>{{ platform.name }}</span>
              <em>{{ platform.code }}</em>
              <el-input v-model="envForm.platform_base_urls[platform.code]" placeholder="例如 http://192.168.5.10:8080" />
            </div>
          </div>
        </el-form-item>
        <el-form-item label="默认环境">
          <el-switch v-model="envForm.is_default" />
        </el-form-item>
        <el-form-item label="只读环境">
          <el-switch v-model="envForm.is_readonly" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="envDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEnvironment">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="preRequestDialogVisible" :title="editingPreRequestId ? '编辑前置操作' : '新增前置操作'" width="780px">
      <el-form :model="preRequestForm" label-width="110px">
        <el-form-item label="操作名称" required>
          <el-input v-model="preRequestForm.name" placeholder="例如：ERP 登录鉴权" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="preRequestForm.is_enabled" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="preRequestForm.sort_order" :min="0" :max="9999" controls-position="right" />
        </el-form-item>
        <el-form-item label="生效模块" required>
          <el-select v-model="preRequestForm.scope_keys" multiple filterable style="width: 100%" placeholder="选择平台或模块" @change="handlePreRequestScopesChange">
            <el-option-group v-for="platform in platformOptions" :key="platform.code" :label="platform.name">
              <el-option :label="`${platform.name}（整个平台）`" :value="platformScopeKey(platform.code)" />
              <el-option v-for="module in modulesForPlatform(platform.code)" :key="module.id" :label="module.name" :value="moduleScopeKey(module.id)" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="Token 设置">
          <div class="pre-request-grid">
            <el-input v-model="preRequestForm.token_key" placeholder="变量名，例如 token">
              <template #prepend>变量名</template>
            </el-input>
            <el-input v-model="preRequestForm.session_key" placeholder="留空则按平台隔离">
              <template #prepend>会话 Key</template>
            </el-input>
            <el-input v-model="preRequestForm.inject_header" placeholder="Authorization">
              <template #prepend>注入 Header</template>
            </el-input>
            <el-input v-model="preRequestForm.inject_prefix" placeholder="Bearer ">
              <template #prepend>Header 前缀</template>
            </el-input>
          </div>
        </el-form-item>
        <el-form-item label="初始化 Token" required>
          <div class="pre-request-section">
            <div class="request-line">
              <el-select v-model="preRequestForm.login_method" style="width: 120px">
                <el-option v-for="method in httpMethods" :key="method" :label="method" :value="method" />
              </el-select>
              <el-input v-model="preRequestForm.login_path" placeholder="/api/login 或完整 URL" />
              <el-input v-model="preRequestForm.login_token_path" placeholder="$.data.token" style="width: 180px">
                <template #prepend>Token Path</template>
              </el-input>
            </div>
            <div class="header-editor">
              <div class="header-editor-title">
                <span>Headers</span>
                <el-button size="small" @click="addHeader(preRequestForm.login_headers)">新增 Header</el-button>
              </div>
              <div v-for="(header, index) in preRequestForm.login_headers" :key="index" class="header-row">
                <el-input v-model="header.key" placeholder="Header Key" />
                <el-input v-model="header.value" placeholder="Header Value" />
                <el-button link class="danger-link" @click="removeHeader(preRequestForm.login_headers, index)">删除</el-button>
              </div>
            </div>
            <el-input v-model="preRequestForm.login_body_text" type="textarea" :rows="4" placeholder='请求体，例如 {"username":"{{username}}","password":"{{password}}"}' />
          </div>
        </el-form-item>
        <el-form-item label="校验 Token">
          <div class="pre-request-section">
            <el-switch v-model="preRequestForm.validate_enabled" active-text="启用校验" inactive-text="不校验，直接复用已有 token" />
            <div class="request-line">
              <el-select v-model="preRequestForm.validate_method" :disabled="!preRequestForm.validate_enabled" style="width: 120px">
                <el-option v-for="method in httpMethods" :key="method" :label="method" :value="method" />
              </el-select>
              <el-input v-model="preRequestForm.validate_path" :disabled="!preRequestForm.validate_enabled" placeholder="/api/user/profile 或完整 URL" />
            </div>
            <div class="pre-request-grid">
              <el-select v-model="preRequestForm.validate_operator" :disabled="!preRequestForm.validate_enabled">
                <el-option label="小于" value="lt" />
                <el-option label="等于" value="eq" />
                <el-option label="大于" value="gt" />
              </el-select>
              <el-input-number v-model="preRequestForm.validate_expected" :disabled="!preRequestForm.validate_enabled" :min="100" :max="599" controls-position="right" />
            </div>
            <div class="header-editor">
              <div class="header-editor-title">
                <span>Headers</span>
                <el-button size="small" :disabled="!preRequestForm.validate_enabled" @click="addHeader(preRequestForm.validate_headers)">新增 Header</el-button>
              </div>
              <div v-for="(header, index) in preRequestForm.validate_headers" :key="index" class="header-row">
                <el-input v-model="header.key" :disabled="!preRequestForm.validate_enabled" placeholder="Header Key" />
                <el-input v-model="header.value" :disabled="!preRequestForm.validate_enabled" placeholder="Header Value" />
                <el-button link class="danger-link" :disabled="!preRequestForm.validate_enabled" @click="removeHeader(preRequestForm.validate_headers, index)">删除</el-button>
              </div>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="preRequestDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePreRequest">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="varDialogVisible" :title="editingVarId ? '编辑变量' : '新增变量'" width="560px">
      <el-form :model="varForm" label-width="98px">
        <el-form-item label="变量 Key" required>
          <el-input v-model="varForm.key" placeholder="token" />
        </el-form-item>
        <el-form-item label="变量值">
          <el-input v-model="varForm.value" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="varForm.platform" clearable style="width: 100%">
            <el-option label="全局" value="" />
            <el-option v-for="platform in platformOptions" :key="platform.code" :label="platform.name" :value="platform.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="作用域">
          <el-input v-model="varForm.scope" />
        </el-form-item>
        <el-form-item label="敏感变量">
          <el-switch v-model="varForm.is_secret" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="varForm.is_enabled" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="varForm.description" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="varDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveVariable">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";

const loading = ref(false);
const saving = ref(false);
const keyword = ref("");
const platformFilter = ref("");
const projects = ref<any[]>([]);
const environments = ref<any[]>([]);
const platforms = ref<any[]>([]);
const modules = ref<any[]>([]);
const selectedEnvironment = ref<any>();
const envDialogVisible = ref(false);
const preRequestDialogVisible = ref(false);
const varDialogVisible = ref(false);
const editingEnvId = ref<number>();
const editingPreRequestId = ref<number>();
const editingVarId = ref<number>();

const envForm = reactive({
  name: "",
  env_type: "test",
  base_url: "",
  platform_base_urls: {} as Record<string, string>,
  is_default: false,
  is_readonly: false,
});

const preRequestForm = reactive({
  name: "",
  is_enabled: true,
  sort_order: 0,
  scope_keys: [] as string[],
  token_key: "token",
  session_key: "",
  inject_header: "Authorization",
  inject_prefix: "Bearer ",
  login_method: "POST",
  login_path: "",
  login_headers: [] as Array<{ key: string; value: string }>,
  login_body_text: "",
  login_token_path: "$.data.token",
  validate_enabled: true,
  validate_method: "GET",
  validate_path: "",
  validate_headers: [] as Array<{ key: string; value: string }>,
  validate_operator: "lt",
  validate_expected: 400,
});

const varForm = reactive({
  key: "",
  value: "",
  scope: "environment",
  platform: "",
  is_secret: false,
  is_enabled: true,
  description: "",
});

const platformCode = (platform: any) => platform.code?.toUpperCase?.() || platform.code || "";
const platformOptions = computed(() => platforms.value.map((item) => ({ ...item, code: platformCode(item) })));
const modulePlatformCode = (module: any) => module.platform || platformCode(platforms.value.find((item) => item.id === module.managed_platform));
const modulesForPlatform = (code: string) => modules.value.filter((item) => modulePlatformCode(item) === code);
const preRequestOperations = computed(() => selectedEnvironment.value?.pre_request_operations || []);
const variables = computed(() => selectedEnvironment.value?.variable_items || []);
const filteredVariables = computed(() =>
  variables.value.filter((item: any) => {
    const text = `${item.key} ${item.description || ""}`.toLowerCase();
    return (!keyword.value || text.includes(keyword.value.toLowerCase())) && (!platformFilter.value || item.platform === platformFilter.value);
  }),
);
const platformUrlRows = computed(() =>
  platformOptions.value.map((platform) => ({
    code: platform.code,
    name: platform.name,
    url: selectedEnvironment.value?.platform_base_urls?.[platform.code] || selectedEnvironment.value?.platform_base_urls?.[platform.code.toLowerCase()] || "",
  })),
);

const platformName = (code: string) => platformOptions.value.find((item) => item.code === code)?.name || code;
const moduleName = (id: number) => modules.value.find((item) => item.id === id)?.name || `模块 ${id}`;
const envTypeText = (type: string) => ({ dev: "开发", test: "测试", staging: "预发", prod: "生产" }[type] || type);
const cleanPlatformUrls = (urls: Record<string, string>) =>
  Object.fromEntries(Object.entries(urls).map(([key, value]) => [key.toUpperCase(), value.trim()]).filter(([, value]) => value));
const httpMethods = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const platformScopeKey = (code: string) => `platform:${code}`;
const moduleScopeKey = (id: number) => `module:${id}`;
const scopePlatforms = (keys: string[]) => keys.filter((item) => item.startsWith("platform:")).map((item) => item.replace("platform:", ""));
const scopeModules = (keys: string[]) => keys.filter((item) => item.startsWith("module:")).map((item) => Number(item.replace("module:", ""))).filter(Number.isFinite);
const operationScopeKeys = (operation: any) => [...(operation.platforms || []).map(platformScopeKey), ...(operation.modules || []).map(moduleScopeKey)];
const operationScopeText = (operation: any) => {
  const labels = [
    ...(operation.platforms || []).map((code: string) => `${platformName(code)}（整个平台）`),
    ...(operation.modules || []).map((id: number) => moduleName(id)),
  ];
  return labels.join("、") || "-";
};
const operationLoginText = (operation: any) => {
  const login = operation.config?.login || {};
  return `${login.method || "POST"} ${login.path || login.url || "未配置"}`;
};

const ensureProject = async () => {
  if (projects.value[0]?.id) return projects.value[0].id;
  const { data } = await platformApi.createProject({
    name: "NS自动化测试平台",
    code: "ns-auto",
    platforms: platformOptions.value.map((item) => item.code),
    is_active: true,
  });
  projects.value = [data];
  return data.id;
};

const selectEnvironment = (env: any) => {
  selectedEnvironment.value = env;
};

const load = async () => {
  loading.value = true;
  try {
    const [projectResp, envResp, platformResp, moduleResp] = await Promise.all([platformApi.projects(), platformApi.environments(), platformApi.platforms(), platformApi.apiModules()]);
    projects.value = unwrapList(projectResp.data);
    environments.value = unwrapList(envResp.data);
    platforms.value = unwrapList(platformResp.data);
    modules.value = unwrapList(moduleResp.data);
    selectedEnvironment.value = environments.value.find((item) => item.id === selectedEnvironment.value?.id) || environments.value[0];
  } finally {
    loading.value = false;
  }
};

const buildEmptyPlatformUrls = () => Object.fromEntries(platformOptions.value.map((platform) => [platform.code, ""]));
const cloneHeaders = (headers: any) =>
  (Array.isArray(headers) ? headers : [])
    .filter((item) => item?.key || item?.name)
    .map((item) => ({ key: item.key || item.name || "", value: item.value ?? "" }));
const normalizeHeaders = (headers: Array<{ key: string; value: string }>) =>
  headers.filter((item) => item.key.trim()).map((item) => ({ enabled: true, key: item.key.trim(), value: item.value }));
const addHeader = (headers: Array<{ key: string; value: string }>) => {
  headers.push({ key: "", value: "" });
};
const removeHeader = (headers: Array<{ key: string; value: string }>, index: number) => {
  headers.splice(index, 1);
};
const parseBodyValue = (value: string) => {
  const text = value.trim();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return value;
  }
};
const bodyToText = (value: unknown) => {
  if (value === undefined || value === null || value === "") return "";
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
};

const resetPreRequestForm = (config: any = {}, operation: any = {}) => {
  const login = config.login || {};
  const validate = config.validate || {};
  const inject = config.inject || {};
  preRequestForm.name = operation.name || "";
  preRequestForm.is_enabled = operation.is_enabled !== false;
  preRequestForm.sort_order = Number(operation.sort_order || 0);
  preRequestForm.scope_keys = operationScopeKeys(operation);
  preRequestForm.token_key = config.token_key || "token";
  preRequestForm.session_key = config.session_key || "";
  preRequestForm.inject_header = inject.header || "Authorization";
  preRequestForm.inject_prefix = inject.prefix ?? "Bearer ";
  preRequestForm.login_method = login.method || "POST";
  preRequestForm.login_path = login.path || login.url || "";
  preRequestForm.login_headers = cloneHeaders(login.headers);
  preRequestForm.login_body_text = bodyToText(login.body);
  preRequestForm.login_token_path = login.token_path || "$.data.token";
  preRequestForm.validate_enabled = validate.enabled !== false;
  preRequestForm.validate_method = validate.method || "GET";
  preRequestForm.validate_path = validate.path || validate.url || "";
  preRequestForm.validate_headers = cloneHeaders(validate.headers);
  preRequestForm.validate_operator = validate.success?.operator || "lt";
  preRequestForm.validate_expected = Number(validate.success?.expected || 400);
};

const buildPreRequestConfig = () => ({
  token_key: preRequestForm.token_key.trim() || "token",
  session_key: preRequestForm.session_key.trim(),
  inject: {
    enabled: true,
    header: preRequestForm.inject_header.trim() || "Authorization",
    prefix: preRequestForm.inject_prefix,
  },
  login: {
    method: preRequestForm.login_method,
    path: preRequestForm.login_path.trim(),
    headers: normalizeHeaders(preRequestForm.login_headers),
    body: parseBodyValue(preRequestForm.login_body_text),
    token_path: preRequestForm.login_token_path.trim() || "$.data.token",
    success: { type: "status_code", operator: "lt", expected: 400 },
  },
  validate: {
    enabled: preRequestForm.validate_enabled,
    method: preRequestForm.validate_method,
    path: preRequestForm.validate_path.trim(),
    headers: normalizeHeaders(preRequestForm.validate_headers),
    success: {
      type: "status_code",
      operator: preRequestForm.validate_operator,
      expected: preRequestForm.validate_expected,
    },
  },
});

const normalizePreRequestScopes = (keys: string[]) => {
  const next = Array.from(new Set(keys));
  const selectedPlatforms = new Set(scopePlatforms(next));
  return next.filter((key) => {
    if (!key.startsWith("module:")) return true;
    const module = modules.value.find((item) => item.id === Number(key.replace("module:", "")));
    return module ? !selectedPlatforms.has(modulePlatformCode(module)) : true;
  });
};

const handlePreRequestScopesChange = () => {
  preRequestForm.scope_keys = normalizePreRequestScopes(preRequestForm.scope_keys);
};

const validatePreRequestScopes = () => {
  const scopeKeys = normalizePreRequestScopes(preRequestForm.scope_keys);
  const selectedPlatforms = new Set(scopePlatforms(scopeKeys));
  const selectedModuleIds = new Set(scopeModules(scopeKeys));
  const selectedModulePlatforms = new Set(
    modules.value
      .filter((item) => selectedModuleIds.has(item.id))
      .map(modulePlatformCode),
  );
  if (!scopeKeys.length) return "请选择至少一个生效平台或模块";
  for (const operation of preRequestOperations.value) {
    if (operation.id === editingPreRequestId.value) continue;
    const operationPlatforms = new Set<string>((operation.platforms || []).map((item: string) => item.toUpperCase()));
    const operationModuleIds = new Set<number>(operation.modules || []);
    const operationModulePlatforms = new Set(
      modules.value
        .filter((item) => operationModuleIds.has(item.id))
        .map(modulePlatformCode),
    );
    if ([...selectedPlatforms].some((item) => operationPlatforms.has(item))) return `平台已被前置操作「${operation.name}」占用`;
    if ([...selectedModuleIds].some((item) => operationModuleIds.has(item))) return `模块已被前置操作「${operation.name}」占用`;
    if ([...selectedPlatforms].some((item) => operationModulePlatforms.has(item))) return `前置操作「${operation.name}」已选择该平台下的模块`;
    if ([...selectedModulePlatforms].some((item) => operationPlatforms.has(item))) return `前置操作「${operation.name}」已选择整个平台`;
  }
  return "";
};

const openEnvCreate = () => {
  editingEnvId.value = undefined;
  Object.assign(envForm, {
    name: "",
    env_type: "test",
    base_url: "",
    platform_base_urls: buildEmptyPlatformUrls(),
    is_default: !environments.value.length,
    is_readonly: false,
  });
  envDialogVisible.value = true;
};

const openEnvEdit = () => {
  if (!selectedEnvironment.value) return;
  editingEnvId.value = selectedEnvironment.value.id;
  Object.assign(envForm, {
    name: selectedEnvironment.value.name,
    env_type: selectedEnvironment.value.env_type,
    base_url: selectedEnvironment.value.base_url || "",
    platform_base_urls: { ...buildEmptyPlatformUrls(), ...(selectedEnvironment.value.platform_base_urls || {}) },
    is_default: selectedEnvironment.value.is_default,
    is_readonly: selectedEnvironment.value.is_readonly,
  });
  envDialogVisible.value = true;
};

const saveEnvironment = async () => {
  if (!envForm.name.trim()) {
    ElMessage.warning("环境名称必填");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      name: envForm.name,
      env_type: envForm.env_type,
      base_url: envForm.base_url.trim(),
      platform_base_urls: cleanPlatformUrls(envForm.platform_base_urls),
      is_default: envForm.is_default,
      is_readonly: envForm.is_readonly,
      project: await ensureProject(),
    };
    if (editingEnvId.value) {
      await platformApi.updateEnvironment(editingEnvId.value, payload);
      ElMessage.success("环境已更新");
    } else {
      await platformApi.createEnvironment(payload);
      ElMessage.success("环境已新增");
    }
    envDialogVisible.value = false;
    await load();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || "保存环境失败");
  } finally {
    saving.value = false;
  }
};

const removeEnvironment = async () => {
  if (!selectedEnvironment.value) return;
  await ElMessageBox.confirm(`确认删除环境“${selectedEnvironment.value.name}”？变量会一并删除。`, "删除确认", { type: "warning" });
  await platformApi.deleteEnvironment(selectedEnvironment.value.id);
  ElMessage.success("环境已删除");
  selectedEnvironment.value = undefined;
  await load();
};

const openPreRequestCreate = () => {
  if (!selectedEnvironment.value) return;
  editingPreRequestId.value = undefined;
  resetPreRequestForm(
    {
      login: {
        method: "POST",
        headers: [{ key: "Content-Type", value: "application/json" }],
        body: { username: "{{username}}", password: "{{password}}" },
      },
    },
    {
      name: "",
      is_enabled: true,
      sort_order: preRequestOperations.value.length,
      platforms: [],
      modules: [],
    },
  );
  preRequestDialogVisible.value = true;
};

const openPreRequestEdit = (row: any) => {
  editingPreRequestId.value = row.id;
  resetPreRequestForm(row.config || {}, row);
  preRequestDialogVisible.value = true;
};

const savePreRequest = async () => {
  if (!selectedEnvironment.value) return;
  if (!preRequestForm.name.trim()) {
    ElMessage.warning("操作名称必填");
    return;
  }
  if (!preRequestForm.login_path.trim()) {
    ElMessage.warning("初始化 Token 的请求地址必填");
    return;
  }
  preRequestForm.scope_keys = normalizePreRequestScopes(preRequestForm.scope_keys);
  const scopeError = validatePreRequestScopes();
  if (scopeError) {
    ElMessage.warning(scopeError);
    return;
  }
  saving.value = true;
  try {
    const payload = {
      environment: selectedEnvironment.value.id,
      name: preRequestForm.name.trim(),
      is_enabled: preRequestForm.is_enabled,
      sort_order: preRequestForm.sort_order,
      platforms: scopePlatforms(preRequestForm.scope_keys),
      modules: scopeModules(preRequestForm.scope_keys),
      config: buildPreRequestConfig(),
    };
    if (editingPreRequestId.value) {
      await platformApi.updateEnvironmentPreRequestOperation(editingPreRequestId.value, payload);
      ElMessage.success("前置操作已更新");
    } else {
      await platformApi.createEnvironmentPreRequestOperation(payload);
      ElMessage.success("前置操作已新增");
    }
    preRequestDialogVisible.value = false;
    await load();
  } catch (error: any) {
    const data = error?.response?.data;
    ElMessage.error(data?.detail || data?.non_field_errors?.[0] || String(data || error?.message || "保存前置操作失败"));
  } finally {
    saving.value = false;
  }
};

const removePreRequest = async (row: any) => {
  await ElMessageBox.confirm(`确认删除前置操作“${row.name}”？`, "删除确认", { type: "warning" });
  await platformApi.deleteEnvironmentPreRequestOperation(row.id);
  ElMessage.success("前置操作已删除");
  await load();
};

const openVarCreate = () => {
  editingVarId.value = undefined;
  Object.assign(varForm, { key: "", value: "", scope: "environment", platform: "", is_secret: false, is_enabled: true, description: "" });
  varDialogVisible.value = true;
};

const openVarEdit = (row: any) => {
  editingVarId.value = row.id;
  Object.assign(varForm, {
    key: row.key,
    value: row.value || "",
    scope: row.scope || "environment",
    platform: row.platform || "",
    is_secret: row.is_secret,
    is_enabled: row.is_enabled,
    description: row.description || "",
  });
  varDialogVisible.value = true;
};

const saveVariable = async () => {
  if (!selectedEnvironment.value || !varForm.key.trim()) {
    ElMessage.warning("变量 Key 必填");
    return;
  }
  saving.value = true;
  try {
    const payload = { ...varForm, environment: selectedEnvironment.value.id };
    if (editingVarId.value) {
      await platformApi.updateEnvironmentVariable(editingVarId.value, payload);
      ElMessage.success("变量已更新");
    } else {
      await platformApi.createEnvironmentVariable(payload);
      ElMessage.success("变量已新增");
    }
    varDialogVisible.value = false;
    await load();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || "保存变量失败");
  } finally {
    saving.value = false;
  }
};

const removeVariable = async (row: any) => {
  await ElMessageBox.confirm(`确认删除变量“${row.key}”？`, "删除确认", { type: "warning" });
  await platformApi.deleteEnvironmentVariable(row.id);
  ElMessage.success("变量已删除");
  await load();
};

onMounted(load);
</script>
