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
              <el-tag :type="selectedEnvironment.pre_request_enabled ? 'success' : 'info'">
                {{ selectedEnvironment.pre_request_enabled ? "已启用" : "未启用" }}
              </el-tag>
            </div>
          </template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="Token 变量">{{ selectedEnvironment.pre_request_config?.token_key || "token" }}</el-descriptions-item>
            <el-descriptions-item label="会话 Key">{{ selectedEnvironment.pre_request_config?.session_key || "按平台" }}</el-descriptions-item>
            <el-descriptions-item label="注入 Header">{{ selectedEnvironment.pre_request_config?.inject?.header || "Authorization" }}</el-descriptions-item>
            <el-descriptions-item label="登录请求" :span="3">
              {{ selectedEnvironment.pre_request_config?.login?.method || "POST" }}
              {{ selectedEnvironment.pre_request_config?.login?.path || selectedEnvironment.pre_request_config?.login?.url || "未配置" }}
            </el-descriptions-item>
            <el-descriptions-item label="校验请求" :span="3">
              {{ selectedEnvironment.pre_request_config?.validate?.path || selectedEnvironment.pre_request_config?.validate?.url || "未配置时直接复用已有 token" }}
            </el-descriptions-item>
          </el-descriptions>
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
        <el-divider content-position="left">全局前置操作</el-divider>
        <el-form-item label="启用前置">
          <el-switch v-model="envForm.pre_request_enabled" />
        </el-form-item>
        <el-form-item label="Token 设置">
          <div class="pre-request-grid">
            <el-input v-model="envForm.pre_token_key" placeholder="变量名，例如 token">
              <template #prepend>变量名</template>
            </el-input>
            <el-input v-model="envForm.pre_session_key" placeholder="留空则按平台隔离">
              <template #prepend>会话 Key</template>
            </el-input>
            <el-input v-model="envForm.pre_inject_header" placeholder="Authorization">
              <template #prepend>注入 Header</template>
            </el-input>
            <el-input v-model="envForm.pre_inject_prefix" placeholder="Bearer ">
              <template #prepend>Header 前缀</template>
            </el-input>
          </div>
        </el-form-item>
        <el-form-item label="初始化 Token">
          <div class="pre-request-section">
            <div class="request-line">
              <el-select v-model="envForm.pre_login_method" style="width: 120px">
                <el-option v-for="method in httpMethods" :key="method" :label="method" :value="method" />
              </el-select>
              <el-input v-model="envForm.pre_login_path" placeholder="/api/login 或完整 URL" />
              <el-input v-model="envForm.pre_login_token_path" placeholder="$.data.token" style="width: 180px">
                <template #prepend>Token Path</template>
              </el-input>
            </div>
            <div class="header-editor">
              <div class="header-editor-title">
                <span>Headers</span>
                <el-button size="small" @click="addHeader(envForm.pre_login_headers)">新增 Header</el-button>
              </div>
              <div v-for="(header, index) in envForm.pre_login_headers" :key="index" class="header-row">
                <el-input v-model="header.key" placeholder="Header Key" />
                <el-input v-model="header.value" placeholder="Header Value" />
                <el-button link class="danger-link" @click="removeHeader(envForm.pre_login_headers, index)">删除</el-button>
              </div>
            </div>
            <el-input v-model="envForm.pre_login_body_text" type="textarea" :rows="4" placeholder='请求体，例如 {"username":"{{username}}","password":"{{password}}"}' />
          </div>
        </el-form-item>
        <el-form-item label="校验 Token">
          <div class="pre-request-section">
            <el-switch v-model="envForm.pre_validate_enabled" active-text="启用校验" inactive-text="不校验，直接复用已有 token" />
            <div class="request-line">
              <el-select v-model="envForm.pre_validate_method" :disabled="!envForm.pre_validate_enabled" style="width: 120px">
                <el-option v-for="method in httpMethods" :key="method" :label="method" :value="method" />
              </el-select>
              <el-input v-model="envForm.pre_validate_path" :disabled="!envForm.pre_validate_enabled" placeholder="/api/user/profile 或完整 URL" />
            </div>
            <div class="pre-request-grid">
              <el-select v-model="envForm.pre_validate_operator" :disabled="!envForm.pre_validate_enabled">
                <el-option label="小于" value="lt" />
                <el-option label="等于" value="eq" />
                <el-option label="大于" value="gt" />
              </el-select>
              <el-input-number v-model="envForm.pre_validate_expected" :disabled="!envForm.pre_validate_enabled" :min="100" :max="599" controls-position="right" />
            </div>
            <div class="header-editor">
              <div class="header-editor-title">
                <span>Headers</span>
                <el-button size="small" :disabled="!envForm.pre_validate_enabled" @click="addHeader(envForm.pre_validate_headers)">新增 Header</el-button>
              </div>
              <div v-for="(header, index) in envForm.pre_validate_headers" :key="index" class="header-row">
                <el-input v-model="header.key" :disabled="!envForm.pre_validate_enabled" placeholder="Header Key" />
                <el-input v-model="header.value" :disabled="!envForm.pre_validate_enabled" placeholder="Header Value" />
                <el-button link class="danger-link" :disabled="!envForm.pre_validate_enabled" @click="removeHeader(envForm.pre_validate_headers, index)">删除</el-button>
              </div>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="envDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEnvironment">保存</el-button>
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
const selectedEnvironment = ref<any>();
const envDialogVisible = ref(false);
const varDialogVisible = ref(false);
const editingEnvId = ref<number>();
const editingVarId = ref<number>();

const envForm = reactive({
  name: "",
  env_type: "test",
  base_url: "",
  platform_base_urls: {} as Record<string, string>,
  pre_request_enabled: false,
  pre_token_key: "token",
  pre_session_key: "",
  pre_inject_header: "Authorization",
  pre_inject_prefix: "Bearer ",
  pre_login_method: "POST",
  pre_login_path: "",
  pre_login_headers: [] as Array<{ key: string; value: string }>,
  pre_login_body_text: "",
  pre_login_token_path: "$.data.token",
  pre_validate_enabled: true,
  pre_validate_method: "GET",
  pre_validate_path: "",
  pre_validate_headers: [] as Array<{ key: string; value: string }>,
  pre_validate_operator: "lt",
  pre_validate_expected: 400,
  is_default: false,
  is_readonly: false,
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
const envTypeText = (type: string) => ({ dev: "开发", test: "测试", staging: "预发", prod: "生产" }[type] || type);
const cleanPlatformUrls = (urls: Record<string, string>) =>
  Object.fromEntries(Object.entries(urls).map(([key, value]) => [key.toUpperCase(), value.trim()]).filter(([, value]) => value));
const httpMethods = ["GET", "POST", "PUT", "PATCH", "DELETE"];

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
    const [projectResp, envResp, platformResp] = await Promise.all([platformApi.projects(), platformApi.environments(), platformApi.platforms()]);
    projects.value = unwrapList(projectResp.data);
    environments.value = unwrapList(envResp.data);
    platforms.value = unwrapList(platformResp.data);
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

const resetPreRequestForm = (config: any = {}) => {
  const login = config.login || {};
  const validate = config.validate || {};
  const inject = config.inject || {};
  envForm.pre_token_key = config.token_key || "token";
  envForm.pre_session_key = config.session_key || "";
  envForm.pre_inject_header = inject.header || "Authorization";
  envForm.pre_inject_prefix = inject.prefix ?? "Bearer ";
  envForm.pre_login_method = login.method || "POST";
  envForm.pre_login_path = login.path || login.url || "";
  envForm.pre_login_headers = cloneHeaders(login.headers);
  envForm.pre_login_body_text = bodyToText(login.body);
  envForm.pre_login_token_path = login.token_path || "$.data.token";
  envForm.pre_validate_enabled = validate.enabled !== false;
  envForm.pre_validate_method = validate.method || "GET";
  envForm.pre_validate_path = validate.path || validate.url || "";
  envForm.pre_validate_headers = cloneHeaders(validate.headers);
  envForm.pre_validate_operator = validate.success?.operator || "lt";
  envForm.pre_validate_expected = Number(validate.success?.expected || 400);
};

const buildPreRequestConfig = () => ({
  token_key: envForm.pre_token_key.trim() || "token",
  session_key: envForm.pre_session_key.trim(),
  inject: {
    enabled: true,
    header: envForm.pre_inject_header.trim() || "Authorization",
    prefix: envForm.pre_inject_prefix,
  },
  login: {
    method: envForm.pre_login_method,
    path: envForm.pre_login_path.trim(),
    headers: normalizeHeaders(envForm.pre_login_headers),
    body: parseBodyValue(envForm.pre_login_body_text),
    token_path: envForm.pre_login_token_path.trim() || "$.data.token",
    success: { type: "status_code", operator: "lt", expected: 400 },
  },
  validate: {
    enabled: envForm.pre_validate_enabled,
    method: envForm.pre_validate_method,
    path: envForm.pre_validate_path.trim(),
    headers: normalizeHeaders(envForm.pre_validate_headers),
    success: {
      type: "status_code",
      operator: envForm.pre_validate_operator,
      expected: envForm.pre_validate_expected,
    },
  },
});

const openEnvCreate = () => {
  editingEnvId.value = undefined;
  resetPreRequestForm({
    login: {
      method: "POST",
      headers: [{ key: "Content-Type", value: "application/json" }],
      body: { username: "{{username}}", password: "{{password}}" },
    },
  });
  Object.assign(envForm, {
    name: "",
    env_type: "test",
    base_url: "",
    platform_base_urls: buildEmptyPlatformUrls(),
    pre_request_enabled: false,
    is_default: !environments.value.length,
    is_readonly: false,
  });
  envDialogVisible.value = true;
};

const openEnvEdit = () => {
  if (!selectedEnvironment.value) return;
  editingEnvId.value = selectedEnvironment.value.id;
  resetPreRequestForm(selectedEnvironment.value.pre_request_config || {});
  Object.assign(envForm, {
    name: selectedEnvironment.value.name,
    env_type: selectedEnvironment.value.env_type,
    base_url: selectedEnvironment.value.base_url || "",
    platform_base_urls: { ...buildEmptyPlatformUrls(), ...(selectedEnvironment.value.platform_base_urls || {}) },
    pre_request_enabled: Boolean(selectedEnvironment.value.pre_request_enabled),
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
  if (envForm.pre_request_enabled && !envForm.pre_login_path.trim()) {
    ElMessage.warning("启用全局前置操作后，初始化 Token 的请求地址必填");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      name: envForm.name,
      env_type: envForm.env_type,
      base_url: envForm.base_url.trim(),
      platform_base_urls: cleanPlatformUrls(envForm.platform_base_urls),
      pre_request_enabled: envForm.pre_request_enabled,
      pre_request_config: buildPreRequestConfig(),
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
