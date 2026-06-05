<template>
  <div class="module-layout">
    <aside class="secondary-panel">
      <div class="secondary-header">
        <strong>平台与模块</strong>
        <el-button size="small" @click="load">刷新</el-button>
      </div>
      <div class="secondary-body">
        <button class="secondary-item" :class="{ active: !platformFilter && !moduleFilter }" @click="selectAll">
          <span>全部接口</span>
          <el-tag size="small">{{ apis.length }}</el-tag>
        </button>
        <section v-for="platform in platformStats" :key="platform.code" class="api-tree-group">
          <button class="secondary-item" :class="{ active: platformFilter === platform.code && !moduleFilter }" @click="selectPlatform(platform.code)">
            <span class="tree-node-main">
              <button v-if="platformHasChildren(platform.code)" class="tree-toggle-btn" @click.stop="togglePlatform(platform.code)">
                <span class="tree-toggle" :class="{ expanded: isPlatformExpanded(platform.code) }">›</span>
              </button>
              <span>{{ platform.label }}</span>
            </span>
            <el-tag size="small">{{ platform.count }}</el-tag>
          </button>
          <template v-if="isPlatformExpanded(platform.code)">
            <button
              v-for="module in rootModulesForPlatform(platform.code)"
              :key="module.id"
              class="secondary-item child"
              :class="{ active: moduleFilter === module.id }"
              @click="selectModule(platform.code, module.id)"
            >
              <span class="tree-node-main">
                <button v-if="moduleHasChildren(module.id)" class="tree-toggle-btn" @click.stop="toggleModule(module.id)">
                  <span class="tree-toggle" :class="{ expanded: isModuleExpanded(module.id) }">›</span>
                </button>
                <span>{{ module.name }}</span>
              </span>
              <el-tag size="small">{{ module.api_count || countApisByModule(module.id) }}</el-tag>
            </button>
          </template>
        </section>
      </div>
    </aside>

    <section class="work-panel">
      <div class="work-toolbar">
        <div class="toolbar-left">
          <el-input v-model="keyword" clearable placeholder="搜索接口名称、路径" style="width: 260px" />
          <el-select v-model="methodFilter" clearable placeholder="方法" style="width: 110px">
            <el-option v-for="item in methods" :key="item" :label="item" :value="item" />
          </el-select>
          <el-select v-model="moduleFilter" clearable placeholder="模块" style="width: 150px">
            <el-option v-for="item in availableFilterModules" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
          <el-select v-model="statusFilter" clearable placeholder="状态" style="width: 130px">
            <el-option label="开发中" value="developing" />
            <el-option label="已发布" value="released" />
            <el-option label="已废弃" value="deprecated" />
          </el-select>
        </div>
        <div class="toolbar-right">
          <el-button @click="load">刷新</el-button>
          <el-button type="primary" @click="openCreate">新增接口</el-button>
        </div>
      </div>

      <div class="table-area">
        <el-table :data="filteredApis" v-loading="loading" stripe height="100%">
          <el-table-column prop="name" label="接口名称" min-width="180" show-overflow-tooltip />
          <el-table-column label="平台" width="110"><template #default="{ row }">{{ platformName(row.platform) }}</template></el-table-column>
          <el-table-column label="模块" width="130"><template #default="{ row }">{{ moduleName(row.module) }}</template></el-table-column>
          <el-table-column label="方法" width="95">
            <template #default="{ row }"><span class="method-tag" :class="row.method">{{ row.method }}</span></template>
          </el-table-column>
          <el-table-column prop="path" label="请求路径" min-width="260" show-overflow-tooltip />
          <el-table-column label="状态" width="120">
            <template #default="{ row }"><span><i class="status-dot" :class="row.status"></i>{{ statusText(row.status) }}</span></template>
          </el-table-column>
          <el-table-column label="操作" width="210" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="goDebug(row)">调试</el-button>
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button link class="danger-link" @click="removeApi(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <el-drawer v-model="drawerVisible" :title="editingId ? '编辑接口' : '新增接口'" size="560px">
      <el-form label-width="92px" :model="form">
        <el-form-item label="接口名称" required><el-input v-model="form.name" placeholder="例如：查询订单列表" /></el-form-item>
        <el-form-item label="平台" required>
          <el-select v-model="form.platform" style="width: 100%" @change="form.module = undefined">
            <el-option v-for="item in platforms" :key="item.id" :label="item.name" :value="platformCode(item)" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属模块" required>
          <el-select v-model="form.module" clearable style="width: 100%">
            <el-option v-for="item in availableFormModules" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="请求方法" required>
          <el-select v-model="form.method" style="width: 100%">
            <el-option v-for="item in methods" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="请求路径" required><el-input v-model="form.path" placeholder="/api/orders/" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="开发中" value="developing" />
            <el-option label="已发布" value="released" />
            <el-option label="已废弃" value="deprecated" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签"><el-input v-model="form.tagsText" placeholder="多个标签用英文逗号分隔" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="Headers"><textarea v-model="form.headersText" class="json-editor" placeholder='[{"key":"token","value":"{{token}}","enabled":true}]'></textarea></el-form-item>
        <el-form-item label="Query"><textarea v-model="form.queryText" class="json-editor" placeholder='[{"key":"page","value":"1","enabled":true}]'></textarea></el-form-item>
        <el-form-item label="Body"><textarea v-model="form.bodyText" class="json-editor" placeholder='{"name":"demo"}'></textarea></el-form-item>
        <el-form-item label="断言"><textarea v-model="form.assertionsText" class="json-editor" placeholder='[{"type":"status_code","operator":"eq","expected":200}]'></textarea></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="drawerVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveApi">保存</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { platformApi, unwrapList } from "@/api/platform";

interface ApiDefinition {
  id: number;
  project: number;
  name: string;
  platform: string;
  module?: number;
  method: string;
  path: string;
  status: string;
  description?: string;
  tags?: string[];
  headers?: unknown[];
  query_params?: unknown[];
  body?: Record<string, unknown>;
  assertions?: unknown[];
}

const router = useRouter();
const methods = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const loading = ref(false);
const saving = ref(false);
const drawerVisible = ref(false);
const editingId = ref<number>();
const keyword = ref("");
const platformFilter = ref("");
const moduleFilter = ref<number>();
const methodFilter = ref("");
const statusFilter = ref("");
const expandedPlatforms = ref<string[]>([]);
const expandedModules = ref<number[]>([]);
const apis = ref<ApiDefinition[]>([]);
const platforms = ref<any[]>([]);
const modules = ref<any[]>([]);

const form = reactive({
  name: "",
  platform: "",
  module: undefined as number | undefined,
  method: "GET",
  path: "",
  status: "developing",
  description: "",
  tagsText: "",
  headersText: "[]",
  queryText: "[]",
  bodyText: "{}",
  assertionsText: "[]",
});

const platformCode = (platform: any) => platform.code?.toUpperCase?.() || platform.code || "";
const platformName = (code: string) => platforms.value.find((item) => platformCode(item) === code)?.name || code;
const moduleName = (id?: number) => modules.value.find((item) => item.id === id)?.name || "-";
const modulePlatformCode = (module: any) => module.platform || platformCode(platforms.value.find((item) => item.id === module.managed_platform));
const countApisByModule = (id: number) => apis.value.filter((api) => api.module === id).length;
const modulesForPlatform = (code: string) => modules.value.filter((item) => modulePlatformCode(item) === code);
const rootModulesForPlatform = (code: string) => modulesForPlatform(code).filter((item) => !item.parent);
const childModules = (parentId: number) => modules.value.filter((item) => item.parent === parentId);
const platformHasChildren = (code: string) => rootModulesForPlatform(code).length > 0;
const moduleHasChildren = (moduleId: number) => childModules(moduleId).length > 0;
const isPlatformExpanded = (code: string) => expandedPlatforms.value.includes(code);
const isModuleExpanded = (moduleId: number) => expandedModules.value.includes(moduleId);
const togglePlatform = (code: string) => {
  expandedPlatforms.value = isPlatformExpanded(code) ? expandedPlatforms.value.filter((item) => item !== code) : [...expandedPlatforms.value, code];
};
const toggleModule = (moduleId: number) => {
  expandedModules.value = isModuleExpanded(moduleId) ? expandedModules.value.filter((item) => item !== moduleId) : [...expandedModules.value, moduleId];
};
const availableFilterModules = computed(() => modules.value.filter((item) => !platformFilter.value || modulePlatformCode(item) === platformFilter.value));
const availableFormModules = computed(() => modules.value.filter((item) => !form.platform || modulePlatformCode(item) === form.platform));
const platformStats = computed(() =>
  platforms.value.map((item) => {
    const code = platformCode(item);
    return { code, label: item.name, count: apis.value.filter((api) => api.platform === code).length };
  }),
);

const filteredApis = computed(() =>
  apis.value.filter((item) => {
    const text = `${item.name} ${item.path}`.toLowerCase();
    return (
      (!keyword.value || text.includes(keyword.value.toLowerCase())) &&
      (!platformFilter.value || item.platform === platformFilter.value) &&
      (!moduleFilter.value || item.module === moduleFilter.value) &&
      (!methodFilter.value || item.method === methodFilter.value) &&
      (!statusFilter.value || item.status === statusFilter.value)
    );
  }),
);

const statusText = (status: string) => ({ developing: "开发中", released: "已发布", deprecated: "已废弃" }[status] || status);
const parseJson = (value: string, fallback: unknown) => {
  if (!value.trim()) return fallback;
  try {
    return JSON.parse(value);
  } catch {
    throw new Error("JSON 格式不正确");
  }
};


const load = async () => {
  loading.value = true;
  try {
    const [apiResp, platformResp, moduleResp] = await Promise.all([platformApi.apiDefinitions(), platformApi.platforms(), platformApi.apiModules()]);
    apis.value = unwrapList<ApiDefinition>(apiResp.data);
    platforms.value = unwrapList(platformResp.data);
    modules.value = unwrapList(moduleResp.data);
    expandedPlatforms.value = platformStats.value.filter((item) => platformHasChildren(item.code)).map((item) => item.code);
    expandedModules.value = modules.value.filter((item) => moduleHasChildren(item.id)).map((item) => item.id);
    if (!form.platform) form.platform = platformFilter.value || platformCode(platforms.value[0]) || "ERP";
  } finally {
    loading.value = false;
  }
};

const selectAll = () => {
  platformFilter.value = "";
  moduleFilter.value = undefined;
};
const selectPlatform = (code: string) => {
  platformFilter.value = code;
  moduleFilter.value = undefined;
};
const selectModule = (code: string, id: number) => {
  platformFilter.value = code;
  moduleFilter.value = id;
};

const resetForm = () => {
  editingId.value = undefined;
  Object.assign(form, {
    name: "",
    platform: platformFilter.value || platformCode(platforms.value[0]) || "ERP",
    module: moduleFilter.value,
    method: "GET",
    path: "",
    status: "developing",
    description: "",
    tagsText: "",
    headersText: "[]",
    queryText: "[]",
    bodyText: "{}",
    assertionsText: "[]",
  });
};
const openCreate = () => {
  resetForm();
  drawerVisible.value = true;
};
const openEdit = (row: ApiDefinition) => {
  editingId.value = row.id;
  Object.assign(form, {
    name: row.name,
    platform: row.platform,
    module: row.module,
    method: row.method,
    path: row.path,
    status: row.status,
    description: row.description || "",
    tagsText: (row.tags || []).join(","),
    headersText: JSON.stringify(row.headers || [], null, 2),
    queryText: JSON.stringify(row.query_params || [], null, 2),
    bodyText: JSON.stringify(row.body || {}, null, 2),
    assertionsText: JSON.stringify(row.assertions || [], null, 2),
  });
  drawerVisible.value = true;
};
const buildPayload = async () => {
  if (!form.name.trim() || !form.path.trim() || !form.platform || !form.module) throw new Error("接口名称、平台、模块和请求路径必填");
  return {
    name: form.name.trim(),
    platform: form.platform,
    module: form.module,
    method: form.method,
    path: form.path.trim(),
    status: form.status,
    description: form.description,
    tags: form.tagsText.split(",").map((item) => item.trim()).filter(Boolean),
    headers: parseJson(form.headersText, []),
    query_params: parseJson(form.queryText, []),
    body_type: form.bodyText.trim() && form.bodyText.trim() !== "{}" ? "json" : "none",
    body: parseJson(form.bodyText, {}),
    assertions: parseJson(form.assertionsText, []),
    is_active: true,
  };
};
const saveApi = async () => {
  saving.value = true;
  try {
    const payload = await buildPayload();
    if (editingId.value) await platformApi.updateApiDefinition(editingId.value, payload);
    else await platformApi.createApiDefinition(payload);
    ElMessage.success("接口已保存");
    drawerVisible.value = false;
    await load();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || "保存失败");
  } finally {
    saving.value = false;
  }
};
const removeApi = async (row: ApiDefinition) => {
  await ElMessageBox.confirm(`确认删除接口「${row.name}」？`, "删除确认", { type: "warning" });
  await platformApi.deleteApiDefinition(row.id);
  ElMessage.success("接口已删除");
  await load();
};
const goDebug = (row: ApiDefinition) => {
  router.push({ path: "/api-debug", query: { apiId: row.id } });
};

onMounted(load);
</script>
