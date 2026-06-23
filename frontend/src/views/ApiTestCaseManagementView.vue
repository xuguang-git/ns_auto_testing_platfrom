<template>
  <div class="api-case-page">
    <aside class="case-api-tree unified-tree-panel">
      <div class="case-tree-head unified-tree-head">
        <div>
          <strong>接口目录</strong>
          <span>{{ totalCaseCount }} 个用例</span>
        </div>
        <el-button size="small" @click="load">刷新</el-button>
      </div>
      <div class="case-tree-filter">
        <el-input v-model="apiKeyword" placeholder="搜索目录名称" clearable />
      </div>
      <div class="case-tree-body unified-tree-body">
        <section v-for="platform in platformOptions" :key="platform.code" class="case-platform">
          <button class="platform-title tree-branch-title unified-tree-node" @click="togglePlatform(platform.code)">
            <span class="tree-toggle-slot">
              <span v-if="platformHasChildren(platform.code)" class="tree-toggle" :class="{ expanded: isPlatformExpanded(platform.code) }">›</span>
            </span>
            <span class="tree-node-name">{{ platform.name }}</span>
            <em>{{ platformCaseCount(platform.code) }}</em>
          </button>
          <template v-if="isPlatformExpanded(platform.code)">
            <template v-for="module in rootModulesForPlatform(platform.code)" :key="module.id">
              <button
                class="module-title tree-branch-title case-module-node unified-tree-node"
                :class="{ active: selectedModuleId === module.id }"
                @click="selectModule(platform.code, module.id)"
              >
                <span class="tree-toggle-slot">
                  <span v-if="moduleHasChildren(platform.code, module.id)" class="tree-toggle" :class="{ expanded: isModuleExpanded(module.id) }">›</span>
                </span>
                <span class="tree-node-name">{{ module.name }}</span>
                <em>{{ moduleCaseCount(module.id) }}</em>
              </button>
              <template v-if="isModuleExpanded(module.id)">
                <button
                  v-for="child in childModules(module.id)"
                  :key="child.id"
                  class="module-title tree-branch-title case-module-node child unified-tree-node"
                  :class="{ active: selectedModuleId === child.id }"
                  @click="selectModule(platform.code, child.id)"
                >
                  <span class="tree-toggle-slot">
                    <span v-if="moduleHasChildren(platform.code, child.id)" class="tree-toggle" :class="{ expanded: isModuleExpanded(child.id) }">›</span>
                  </span>
                  <span class="tree-node-name">{{ child.name }}</span>
                  <em>{{ moduleCaseCount(child.id) }}</em>
                </button>
              </template>
            </template>
            <button
              v-if="unassignedCaseCount(platform.code)"
              class="module-title tree-branch-title case-module-node unified-tree-node"
              :class="{ active: selectedModuleId === 'unassigned' && selectedPlatform === platform.code }"
              @click="selectModule(platform.code, 'unassigned')"
            >
              <span class="tree-toggle-slot"></span>
              <span class="tree-node-name">未分配</span>
              <em>{{ unassignedCaseCount(platform.code) }}</em>
            </button>
          </template>
        </section>
      </div>
    </aside>

    <section class="case-main">
      <header class="case-main-head">
        <div>
          <div class="breadcrumb-lite">接口测试 / 测试用例</div>
          <h1>{{ selectedDirectoryName || "请选择目录" }}</h1>
          <p v-if="selectedPlatform">
            <span>{{ platformName(selectedPlatform) }} / {{ selectedDirectoryName }}</span>
          </p>
          <p v-else>从左侧目录树选择模块后维护对应测试用例。</p>
        </div>
        <el-button type="primary" :disabled="!selectedPlatform" @click="openCaseForm()">新增用例</el-button>
      </header>

      <div class="case-query-bar">
        <el-input v-model="caseKeyword" placeholder="搜索用例名称" clearable style="width: 280px" />
        <el-select v-model="statusFilter" placeholder="用例状态" clearable style="width: 140px">
          <el-option label="草稿" value="draft" />
          <el-option label="启用" value="active" />
          <el-option label="停用" value="inactive" />
        </el-select>
        <el-button type="primary" @click="loadCases">查询</el-button>
        <el-button @click="resetQuery">重置</el-button>
      </div>

      <div v-if="!selectedPlatform" class="case-empty-panel">
        <el-empty description="请选择左侧目录查看测试用例" />
      </div>
      <div v-else-if="!caseLoading && !filteredCases.length" class="case-empty-panel">
        <el-empty description="当前目录暂无测试用例">
          <el-button type="primary" @click="openCaseForm()">新增用例</el-button>
        </el-empty>
      </div>
      <div v-else class="case-table-card">
        <el-table :data="filteredCases" v-loading="caseLoading" stripe height="100%">
          <el-table-column label="用例名称" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">
              <span>{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column label="请求方式" width="120">
            <template #default="{ row }"><span class="method-tag" :class="row.method">{{ row.method }}</span></template>
          </el-table-column>
          <el-table-column prop="api_name" label="所属接口" min-width="180" show-overflow-tooltip />
          <el-table-column prop="created_by_name" label="创建人" width="120" show-overflow-tooltip />
          <el-table-column prop="updated_by_name" label="最后修改人" width="130" show-overflow-tooltip />
          <el-table-column prop="api_path" label="接口路径" min-width="240" show-overflow-tooltip />
          <el-table-column label="用例状态" width="120">
            <template #default="{ row }">
              <el-select
                v-model="row.status"
                size="small"
                class="case-status-select"
                @change="changeCaseStatus(row)"
              >
                <el-option label="草稿" value="draft" />
                <el-option label="启用" value="active" />
                <el-option label="停用" value="inactive" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="130" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDebug(row)">调试</el-button>
              <el-button link class="danger-link" @click="removeCase(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <el-dialog v-model="caseDialog" :title="editingCaseId ? '编辑用例' : '新增用例'" width="560px">
      <el-form label-width="92px" :model="caseForm">
        <el-form-item label="所属接口">
          <el-select v-model="caseForm.api" filterable style="width: 100%">
            <el-option v-for="api in selectableApis" :key="api.id" :label="`${api.method} ${api.name}`" :value="api.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="用例名称" required>
          <el-input v-model="caseForm.name" placeholder="例如：查询订单详情 - 正常订单" />
        </el-form-item>
        <el-form-item label="用例状态">
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

    <el-drawer v-model="debugDrawer" size="86%" :with-header="false" destroy-on-close>
      <div v-if="debugCaseRow && selectedApi" class="case-debug-shell">
        <header class="case-debug-head">
          <div class="case-debug-title">
            <div class="breadcrumb-lite">测试用例调试</div>
            <h2 v-if="!editingDebugName" class="debug-case-title" @click="startEditDebugName">{{ debugCaseRow.name }}</h2>
            <el-input
              v-else
              ref="debugNameInputRef"
              v-model="debugNameDraft"
              class="debug-case-name-input"
              @blur="saveDebugCaseName"
              @keyup.enter="blurDebugNameInput"
              @keyup.esc="cancelEditDebugName"
            />
            <p>
              <span class="method-tag" :class="debugForm.method">{{ debugForm.method }}</span>
              <span>{{ selectedApi.name }}</span>
              <code>{{ resolvedRequestUrl }}</code>
            </p>
          </div>
          <div class="case-debug-actions">
            <el-button @click="debugDrawer = false">关闭</el-button>
            <el-button :loading="savingDebug" @click="saveDebugConfig">保存用例配置</el-button>
            <el-button type="primary" :loading="sending" @click="sendDebug">发送调试</el-button>
          </div>
        </header>

        <div class="case-debug-body">
          <section class="v2-card case-debug-request">
            <div class="request-line-v2">
              <el-select v-model="debugForm.method" style="width: 110px">
                <el-option v-for="item in methods" :key="item" :label="item" :value="item" />
              </el-select>
              <el-input v-model="debugForm.path" />
              <el-select v-model="debugForm.environment" placeholder="环境" clearable style="width: 180px">
                <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
              </el-select>
            </div>
            <div class="resolved-url-box">
              <span>实际请求地址</span>
              <code>{{ resolvedRequestUrl }}</code>
            </div>
            <div class="case-data-source-row">
              <el-select v-model="preDataSourceIds" multiple collapse-tags collapse-tags-tooltip clearable placeholder="前置数据源" style="width: 260px">
                <el-option v-for="source in activeTestDataSources" :key="source.id" :label="source.name" :value="source.id" />
              </el-select>
              <el-select v-model="postDataSourceIds" multiple collapse-tags collapse-tags-tooltip clearable placeholder="后置数据源" style="width: 260px">
                <el-option v-for="source in activeTestDataSources" :key="source.id" :label="source.name" :value="source.id" />
              </el-select>
            </div>
            <el-tabs v-model="debugReqTab">
              <el-tab-pane label="Params" name="params">
                <div class="variable-hint" v-pre>变量引用：在 Value 中使用 {{变量名}}；发送时先取当前环境全局变量，再用当前接口平台变量覆盖同名变量。</div>
                <KeyValueEditor v-model="paramsRows" />
              </el-tab-pane>
              <el-tab-pane label="Headers" name="headers"><KeyValueEditor v-model="headerRows" /></el-tab-pane>
              <el-tab-pane label="Body" name="body">
                <div class="body-editor-toolbar">
                  <span class="variable-hint inline" v-pre>Body 支持 {{变量名}} 引用，适用于字符串、JSON 字段值和嵌套对象。</span>
                  <el-button size="small" @click="formatBody">格式化</el-button>
                </div>
                <el-input v-model="bodyText" type="textarea" :rows="10" />
              </el-tab-pane>
              <el-tab-pane label="Auth" name="auth">
                <div class="inline-form">
                  <el-select v-model="authType">
                    <el-option label="No Auth" value="none" />
                    <el-option label="Bearer Token" value="bearer" />
                    <el-option label="Basic Auth" value="basic" />
                    <el-option label="API Key" value="api_key" />
                  </el-select>
                  <el-input v-model="authToken" placeholder="{{token}}" />
                </div>
              </el-tab-pane>
              <el-tab-pane label="断言" name="assertions">
                <div class="assertion-editor">
                  <div class="assertion-editor-head">
                    <strong>用例断言</strong>
                    <el-button size="small" type="primary" @click="addAssertion">新增断言</el-button>
                  </div>
                  <div class="assertion-editor-table">
                    <div class="assertion-row assertion-row-head">
                      <span>断言类型</span>
                      <span>目标字段</span>
                      <span>操作符</span>
                      <span>期望值</span>
                      <span>操作</span>
                    </div>
                    <div v-for="(assertion, index) in assertionRows" :key="assertion.uid" class="assertion-row">
                      <el-select v-model="assertion.type" @change="normalizeAssertion(assertion)">
                        <el-option label="状态码" value="status_code" />
                        <el-option label="响应时间" value="response_time" />
                        <el-option label="响应 Header" value="header" />
                        <el-option label="JSONPath" value="json_path" />
                        <el-option label="Body 包含" value="body_contains" />
                      </el-select>
                      <el-input v-model="assertion.key" :disabled="!needsAssertionKey(assertion.type)" :placeholder="assertionKeyPlaceholder(assertion.type)" />
                      <el-select v-model="assertion.operator">
                        <el-option label="等于" value="eq" />
                        <el-option label="不等于" value="ne" />
                        <el-option label="包含" value="contains" />
                        <el-option label="存在" value="exists" />
                        <el-option label="小于" value="lt" />
                        <el-option label="大于" value="gt" />
                      </el-select>
                      <el-input v-model="assertion.expected" :disabled="assertion.operator === 'exists'" placeholder="期望值" />
                      <el-button link class="danger-link" @click="removeAssertion(index)">删除</el-button>
                    </div>
                  </div>
                  <el-empty v-if="!assertionRows.length" description="暂无断言" />
                </div>
              </el-tab-pane>
            </el-tabs>
          </section>

          <section class="v2-card response-card-v2">
            <div class="response-meta">
              <strong>响应结果</strong>
              <span v-if="debugResult" :class="responseStatusClass">{{ debugResult.response?.status_code || "-" }} · {{ debugResult.response?.elapsed_ms || "-" }}ms</span>
            </div>
            <el-tabs v-model="debugRespTab">
              <el-tab-pane label="Body" name="body"><pre>{{ responseBodyText }}</pre></el-tab-pane>
              <el-tab-pane label="Headers" name="headers"><pre>{{ responseHeadersText }}</pre></el-tab-pane>
              <el-tab-pane label="提取器" name="extractor">
                <div class="extractor-panel">
                  <div class="extractor-toolbar">
                    <div>
                      <strong>响应提取器</strong>
                      <span>从响应 JSON 提取字段，可复制或保存为指定平台环境变量。</span>
                    </div>
                    <div>
                      <el-button size="small" @click="addExtractor">新增规则</el-button>
                      <el-button size="small" type="primary" @click="runExtractors">执行提取</el-button>
                    </div>
                  </div>
                  <div class="extractor-table">
                    <div class="extractor-row extractor-head case-extractor-row">
                      <span>变量名</span>
                      <span>JSONPath</span>
                      <span>环境</span>
                      <span>平台</span>
                      <span>结果</span>
                      <span>操作</span>
                    </div>
                    <div v-for="(item, index) in extractorRows" :key="item.uid" class="extractor-row case-extractor-row">
                      <el-input v-model="item.name" placeholder="token" />
                      <el-input v-model="item.path" placeholder="$.data.token" />
                      <el-select v-model="item.saveEnvironment" placeholder="环境">
                        <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
                      </el-select>
                      <el-select v-model="item.savePlatform" placeholder="平台">
                        <el-option v-for="platform in platformOptions" :key="platform.code" :label="platform.name" :value="platform.code" />
                      </el-select>
                      <pre :class="{ error: item.message && !item.ok }">{{ item.valueText || item.message || "-" }}</pre>
                      <div class="extractor-actions">
                        <el-button link type="primary" @click="copyExtractor(item)">复制</el-button>
                        <el-button link type="primary" :loading="item.saving" @click="saveExtractorVariable(item)">保存变量</el-button>
                        <el-button link class="danger-link" @click="removeExtractor(index)">删除</el-button>
                      </div>
                    </div>
                  </div>
                  <el-empty v-if="!extractorRows.length" description="暂无提取规则" />
                </div>
              </el-tab-pane>
              <el-tab-pane label="断言结果" name="assertions">
                <div v-if="debugResult?.assertions?.length" class="assertion-list-v2">
                  <div v-for="item in debugResult.assertions" :key="item.name + item.type" :class="{ passed: item.passed }">
                    <b>{{ item.passed ? "PASS" : "FAIL" }}</b>
                    <span>{{ item.name }}</span>
                    <em>expected {{ item.expected }}, actual {{ item.actual }}</em>
                  </div>
                </div>
                <el-empty v-else description="发送请求后查看断言结果" />
              </el-tab-pane>
            </el-tabs>
          </section>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, defineComponent, h, nextTick, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { platformApi, unwrapList } from "@/api/platform";
import { formatBodyText } from "@/utils/bodyFormat";
import { extractJsonPath, formatExtractValue } from "@/utils/jsonExtract";

interface RowItem { enabled: boolean; key: string; value: string; description?: string }
interface AssertionRow { uid: number; type: string; key: string; operator: string; expected: string }
interface ExtractorRow {
  uid: number;
  name: string;
  path: string;
  ok: boolean;
  message: string;
  valueText: string;
  saveEnvironment?: number;
  savePlatform: string;
  saving?: boolean;
}
interface ApiDefinition {
  id: number;
  name: string;
  platform: string;
  module?: number;
  method: string;
  path: string;
  headers?: RowItem[];
  query_params?: RowItem[];
  body?: unknown;
  body_type?: string;
  auth_config?: Record<string, unknown>;
  assertions?: unknown[];
  test_case_count?: number;
}
interface ApiTestCase {
  id: number;
  api: number;
  api_name?: string;
  api_path?: string;
  module?: number;
  platform?: string;
  name: string;
  method: string;
  status: string;
  priority?: string;
  description?: string;
  request_override?: Record<string, any>;
  pre_data_source_ids?: number[];
  post_data_source_ids?: number[];
  assertions?: unknown[];
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
    const remove = (index: number) => {
      const rows = [...(props.modelValue as RowItem[])];
      rows.splice(index, 1);
      emit("update:modelValue", rows);
    };
    const add = () => emit("update:modelValue", [...(props.modelValue as RowItem[]), { enabled: true, key: "", value: "", description: "" }]);
    return () => h("div", { class: "kv-editor" }, [
      h("table", { class: "kv-table" }, [
        h("thead", [h("tr", [h("th", ""), h("th", "Key"), h("th", "Value"), h("th", "Description"), h("th", "")])]),
        h("tbody", (props.modelValue as RowItem[]).map((row, index) => h("tr", { key: index }, [
          h("td", [h("input", { type: "checkbox", checked: row.enabled !== false, onChange: (e: Event) => update(index, "enabled", (e.target as HTMLInputElement).checked) })]),
          h("td", [h("input", { value: row.key, onInput: (e: Event) => update(index, "key", (e.target as HTMLInputElement).value) })]),
          h("td", [h("input", { value: row.value, onInput: (e: Event) => update(index, "value", (e.target as HTMLInputElement).value) })]),
          h("td", [h("input", { value: row.description, onInput: (e: Event) => update(index, "description", (e.target as HTMLInputElement).value) })]),
          h("td", [h("button", { class: "kv-remove-row", type: "button", title: "删除字段", onClick: () => remove(index) }, "-")]),
        ]))),
      ]),
      h("button", { class: "add-row", onClick: add }, "+ Add row"),
    ]);
  },
});

const methods = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const enabledRows = (rows: RowItem[]) => rows.filter((row) => row.enabled !== false);
const route = useRoute();
const router = useRouter();
const apiKeyword = ref("");
const caseKeyword = ref("");
const statusFilter = ref("");
const caseLoading = ref(false);
const caseDialog = ref(false);
const debugDrawer = ref(false);
const sending = ref(false);
const savingDebug = ref(false);
const editingCaseId = ref<number>();
const apis = ref<ApiDefinition[]>([]);
const platforms = ref<any[]>([]);
const modules = ref<any[]>([]);
const environments = ref<any[]>([]);
const testDataSources = ref<any[]>([]);
const cases = ref<ApiTestCase[]>([]);
const selectedApi = ref<ApiDefinition>();
const selectedPlatform = ref("");
const selectedModuleId = ref<number | "unassigned">();
const expandedPlatforms = ref<string[]>([]);
const expandedModules = ref<number[]>([]);
const debugCaseRow = ref<ApiTestCase>();
const debugResult = ref<any>();
const editingDebugName = ref(false);
const debugNameDraft = ref("");
const debugNameInputRef = ref();
const debugReqTab = ref("params");
const debugRespTab = ref("body");
const paramsRows = ref<RowItem[]>([]);
const headerRows = ref<RowItem[]>([]);
const bodyText = ref("{}");
const assertionRows = ref<AssertionRow[]>([]);
const extractorRows = ref<ExtractorRow[]>([]);
const preDataSourceIds = ref<number[]>([]);
const postDataSourceIds = ref<number[]>([]);
const authType = ref("none");
const authToken = ref("");
const debugForm = reactive({ method: "GET", path: "", environment: undefined as number | undefined });
const caseForm = reactive({ api: undefined as number | undefined, name: "", status: "draft" });

const platformCode = (item: any) => item.code?.toUpperCase?.() || item.code || "";
const platformOptions = computed(() => platforms.value.map((item) => ({ ...item, code: platformCode(item) })));
const filteredModules = computed(() => modules.value.filter((item) => !apiKeyword.value || `${item.name} ${item.code || ""}`.toLowerCase().includes(apiKeyword.value.toLowerCase())));
const modulePlatformCode = (module: any) => module.platform || platformCode(platforms.value.find((item) => item.id === module.managed_platform));
const modulesForPlatform = (code: string) => filteredModules.value.filter((item) => modulePlatformCode(item) === code);
const rootModulesForPlatform = (code: string) => modulesForPlatform(code).filter((item) => !item.parent);
const childModules = (parentId: number) => modules.value.filter((item) => item.parent === parentId);
const platformApis = (platform: string) => apis.value.filter((item) => item.platform === platform);
const apisByModule = (moduleId: number | "unassigned") => apis.value.filter((item) => moduleId === "unassigned" ? !item.module : item.module === moduleId);
const platformHasChildren = (platform: string) => rootModulesForPlatform(platform).length > 0 || unassignedCaseCount(platform) > 0;
const moduleHasChildren = (_platform: string, moduleId: number) => childModules(moduleId).length > 0;
const isPlatformExpanded = (platform: string) => expandedPlatforms.value.includes(platform);
const isModuleExpanded = (moduleId: number) => expandedModules.value.includes(moduleId);
const togglePlatform = (platform: string) => {
  if (!platformHasChildren(platform)) return;
  expandedPlatforms.value = isPlatformExpanded(platform) ? expandedPlatforms.value.filter((item) => item !== platform) : [...expandedPlatforms.value, platform];
};
const toggleModule = (moduleId: number) => {
  expandedModules.value = isModuleExpanded(moduleId) ? expandedModules.value.filter((item) => item !== moduleId) : [...expandedModules.value, moduleId];
};
const selectableApis = computed(() => {
  if (!selectedPlatform.value) return [];
  if (selectedModuleId.value) return apisByModule(selectedModuleId.value).filter((item) => item.platform === selectedPlatform.value);
  return platformApis(selectedPlatform.value);
});
const selectedDirectoryName = computed(() => {
  if (selectedModuleId.value === "unassigned") return "未分配";
  return modules.value.find((item) => item.id === selectedModuleId.value)?.name || "";
});
const totalCaseCount = computed(() => modules.value.reduce((sum, item) => sum + Number(item.test_case_count || 0), 0) + apis.value.filter((api) => !api.module).reduce((sum, api) => sum + Number(api.test_case_count || 0), 0));
const moduleCaseCount = (moduleId: number) => Number(modules.value.find((item) => item.id === moduleId)?.test_case_count || 0);
const unassignedCaseCount = (platform: string) => apis.value.filter((api) => api.platform === platform && !api.module).reduce((sum, api) => sum + Number(api.test_case_count || 0), 0);
const platformCaseCount = (platform: string) => modules.value.filter((item) => modulePlatformCode(item) === platform).reduce((sum, item) => sum + Number(item.test_case_count || 0), 0) + unassignedCaseCount(platform);
const filteredCases = computed(() =>
  cases.value.filter((item) => (!caseKeyword.value || item.name.toLowerCase().includes(caseKeyword.value.toLowerCase())) && (!statusFilter.value || item.status === statusFilter.value)),
);
const currentEnvironment = computed(() => environments.value.find((item) => item.id === debugForm.environment));
const currentPlatformBaseUrl = computed(() => {
  if (!selectedApi.value) return "";
  const urls = currentEnvironment.value?.platform_base_urls || {};
  return urls[selectedApi.value.platform] || urls[selectedApi.value.platform.toLowerCase?.()] || currentEnvironment.value?.base_url || "";
});
const resolvedRequestUrl = computed(() => {
  const path = debugForm.path || selectedApi.value?.path || "";
  if (!path) return currentPlatformBaseUrl.value || "未配置环境地址";
  if (/^https?:\/\//i.test(path)) return path;
  if (!currentPlatformBaseUrl.value) return path;
  return `${currentPlatformBaseUrl.value.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
});
const responseBodyText = computed(() => JSON.stringify(debugResult.value?.response?.body ?? {}, null, 2));
const responseHeadersText = computed(() => JSON.stringify(debugResult.value?.response?.headers ?? {}, null, 2));
const responseStatusClass = computed(() => Number(debugResult.value?.response?.status_code || 0) >= 400 ? "status-error" : "status-ok");
const activeTestDataSources = computed(() => testDataSources.value.filter((item) => item.is_active));

const platformName = (code: string) => platformOptions.value.find((item) => item.code === code)?.name || code;
const moduleName = (id?: number) => modules.value.find((item) => item.id === id)?.name || "未分配";
const caseStatusText = (status: string) => ({ draft: "草稿", active: "启用", inactive: "停用" }[status] || status);
const caseStatusClass = (status: string) => (status === "active" ? "badge-success" : status === "inactive" ? "badge-danger" : "badge-warning");

const parseJson = (text: string, fallback: unknown) => {
  if (!text.trim()) return fallback;
  try { return JSON.parse(text); } catch { throw new Error("JSON 格式不正确"); }
};
const formatBody = () => {
  bodyText.value = formatBodyText(bodyText.value);
  ElMessage.success("Body 已格式化");
};
const createAssertion = (input?: any): AssertionRow => ({
  uid: Date.now() + Math.floor(Math.random() * 10000),
  type: input?.type || "status_code",
  key: input?.key || input?.path || "",
  operator: input?.operator || input?.op || "eq",
  expected: input?.expected === undefined || input?.expected === null ? "" : String(input.expected),
});
const normalizeAssertion = (assertion: AssertionRow) => {
  if (!needsAssertionKey(assertion.type)) assertion.key = "";
  if (assertion.type === "body_contains") assertion.operator = "contains";
  if (assertion.type === "response_time" && !["lt", "gt", "eq", "ne"].includes(assertion.operator)) assertion.operator = "lt";
};
const needsAssertionKey = (type: string) => ["header", "json_path"].includes(type);
const assertionKeyPlaceholder = (type: string) => {
  if (type === "header") return "例如 Content-Type";
  if (type === "json_path") return "例如 $.data.id";
  return "无需填写";
};
const addAssertion = () => assertionRows.value.push(createAssertion());
const removeAssertion = (index: number) => assertionRows.value.splice(index, 1);
const assertionName = (item: AssertionRow) => {
  const label = { status_code: "状态码", response_time: "响应时间", header: "Header", json_path: "JSONPath", body_contains: "Body 包含" }[item.type] || item.type;
  return item.key ? `${label} ${item.key}` : label;
};
const buildAssertions = () =>
  assertionRows.value.map((item) => ({
    name: assertionName(item),
    type: item.type,
    operator: item.operator,
    expected: item.operator === "exists" ? "" : item.expected,
    ...(item.type === "header" ? { key: item.key } : {}),
    ...(item.type === "json_path" ? { path: item.key } : {}),
  }));
const createExtractor = (input?: any): ExtractorRow => ({
  uid: Date.now() + Math.floor(Math.random() * 10000),
  name: input?.name || "token",
  path: input?.path || "$.data.token",
  ok: false,
  message: "",
  valueText: "",
  saveEnvironment: input?.saveEnvironment || input?.environment || debugForm.environment,
  savePlatform: input?.savePlatform || input?.platform || selectedApi.value?.platform || platformOptions.value[0]?.code || "",
});
const buildExtractors = () =>
  extractorRows.value
    .filter((item) => item.name.trim() || item.path.trim())
    .map((item) => ({
      name: item.name.trim(),
      path: item.path.trim(),
      environment: item.saveEnvironment,
      platform: item.savePlatform,
    }));
const addExtractor = () => extractorRows.value.push(createExtractor({ name: "", path: "$." }));
const removeExtractor = (index: number) => extractorRows.value.splice(index, 1);
const copyText = async (text: string) => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
};
const copyExtractor = async (item: ExtractorRow) => {
  if (!item.ok || !item.valueText) {
    ElMessage.warning("暂无可复制的提取结果");
    return;
  }
  await copyText(item.valueText);
  ElMessage.success("提取结果已复制");
};
const runExtractors = () => {
  if (!debugResult.value?.response) {
    ElMessage.warning("请先发送请求获取响应");
    return;
  }
  const body = debugResult.value.response.body;
  extractorRows.value = extractorRows.value.map((item) => {
    const extracted = extractJsonPath(body, item.path);
    return {
      ...item,
      ok: extracted.ok,
      message: extracted.message,
      valueText: extracted.ok ? formatExtractValue(extracted.value) : "",
    };
  });
  debugRespTab.value = "extractor";
};
const saveExtractorVariable = async (item: ExtractorRow) => {
  if (!item.name.trim()) {
    ElMessage.warning("请填写变量名");
    return;
  }
  if (!item.ok || !item.valueText) {
    ElMessage.warning("请先执行提取并确认有结果");
    return;
  }
  if (!item.saveEnvironment || !item.savePlatform) {
    ElMessage.warning("请先选择保存环境和平台");
    return;
  }
  item.saving = true;
  try {
    const key = item.name.trim();
    const { data } = await platformApi.environmentVariables({
      environment: item.saveEnvironment,
      platform: item.savePlatform,
    });
    const existing = unwrapList<any>(data).find((variable) => variable.key === key && variable.platform === item.savePlatform);
    if (existing) {
      await platformApi.updateEnvironmentVariable(existing.id, {
        value: item.valueText,
        is_enabled: true,
      });
      ElMessage.success("环境变量已更新");
    } else {
      await platformApi.createEnvironmentVariable({
        environment: item.saveEnvironment,
        key,
        value: item.valueText,
        platform: item.savePlatform,
        scope: "platform",
        is_secret: false,
        is_enabled: true,
        description: `由测试用例 ${debugCaseRow.value?.name || ""} 提取`,
      });
      ElMessage.success("环境变量已保存");
    }
  } finally {
    item.saving = false;
  }
};

const load = async () => {
  const [apiResp, platformData, moduleData, envData, dataSourceResp] = await Promise.all([platformApi.apiDefinitions(), platformApi.cachedPlatforms(), platformApi.cachedApiModules(), platformApi.cachedEnvironments(), platformApi.testDataSources()]);
  apis.value = unwrapList<ApiDefinition>(apiResp.data);
  platforms.value = unwrapList(platformData as any);
  modules.value = unwrapList(moduleData as any);
  environments.value = unwrapList(envData as any);
  testDataSources.value = unwrapList(dataSourceResp.data);
  expandedPlatforms.value = platformOptions.value.filter((item) => platformHasChildren(item.code)).map((item) => item.code);
  expandedModules.value = modules.value.filter((item) => moduleHasChildren(modulePlatformCode(item), item.id)).map((item) => item.id);
  debugForm.environment = environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id;
  const queryModule = route.query.module === "unassigned" ? "unassigned" : Number(route.query.module);
  const queryPlatform = String(route.query.platform || "");
  if (queryPlatform && (queryModule === "unassigned" || Number.isFinite(queryModule))) {
    await selectModule(queryPlatform, queryModule as number | "unassigned");
    return;
  }
  const firstPlatform = platformOptions.value.find((item) => platformHasChildren(item.code));
  const firstModule = firstPlatform ? rootModulesForPlatform(firstPlatform.code)[0] : undefined;
  if (firstPlatform && firstModule) await selectModule(firstPlatform.code, firstModule.id);
};

const selectModule = async (platform: string, moduleId: number | "unassigned") => {
  selectedPlatform.value = platform;
  selectedModuleId.value = moduleId;
  if (typeof moduleId === "number" && !isModuleExpanded(moduleId)) toggleModule(moduleId);
  selectedApi.value = undefined;
  caseKeyword.value = "";
  statusFilter.value = "";
  await router.replace({ path: "/api-testing/cases", query: { platform, module: moduleId } });
  await loadCases();
};

const loadCases = async () => {
  if (!selectedPlatform.value || !selectedModuleId.value) return;
  caseLoading.value = true;
  try {
    const params: Record<string, unknown> = {};
    if (selectedModuleId.value === "unassigned") {
      const ids = apisByModule("unassigned").filter((api) => api.platform === selectedPlatform.value).map((api) => api.id);
      params.api_ids = ids.join(",");
    } else {
      params.api__module = selectedModuleId.value;
    }
    const { data } = await platformApi.apiTestCases(params);
    cases.value = unwrapList<ApiTestCase>(data);
  } finally {
    caseLoading.value = false;
  }
};

const resetQuery = () => {
  caseKeyword.value = "";
  statusFilter.value = "";
  loadCases();
};

const openCaseForm = (row?: ApiTestCase) => {
  editingCaseId.value = row?.id;
  Object.assign(caseForm, { api: row?.api || selectableApis.value[0]?.id, name: row?.name || "", status: row?.status || "draft" });
  caseDialog.value = true;
};

const saveCase = async () => {
  if (!caseForm.api || !caseForm.name.trim()) {
    ElMessage.warning("请先选择所属接口并填写用例名称");
    return;
  }
  const payload = { api: caseForm.api, name: caseForm.name.trim(), status: caseForm.status, priority: "P1", is_active: caseForm.status !== "inactive" };
  if (editingCaseId.value) await platformApi.updateApiTestCase(editingCaseId.value, payload);
  else await platformApi.createApiTestCase(payload);
  ElMessage.success("用例已保存");
  caseDialog.value = false;
  await loadCases();
};

const changeCaseStatus = async (row: ApiTestCase) => {
  try {
    await platformApi.updateApiTestCase(row.id, {
      status: row.status,
      is_active: row.status !== "inactive",
    });
    ElMessage.success("用例状态已更新");
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || "更新状态失败");
    await loadCases();
  }
};

const removeCase = async (row: ApiTestCase) => {
  await ElMessageBox.confirm(`确认删除用例“${row.name}”？`, "删除确认", { type: "warning" });
  await platformApi.deleteApiTestCase(row.id);
  ElMessage.success("用例已删除");
  await loadCases();
};

const openDebug = (row: ApiTestCase, editName = false) => {
  const api = apis.value.find((item) => item.id === row.api);
  if (!api) {
    ElMessage.warning("未找到用例所属接口");
    return;
  }
  selectedApi.value = api;
  debugCaseRow.value = row;
  debugNameDraft.value = row.name;
  const override = row.request_override || {};
  debugForm.method = override.method || selectedApi.value.method;
  debugForm.path = override.path || selectedApi.value.path;
  debugForm.environment = override.environment || debugForm.environment;
  paramsRows.value = override.query_params || selectedApi.value.query_params || [{ enabled: true, key: "", value: "", description: "" }];
  headerRows.value = override.headers || selectedApi.value.headers || [{ enabled: true, key: "Content-Type", value: "application/json", description: "" }];
  bodyText.value = JSON.stringify(override.body ?? selectedApi.value.body ?? {}, null, 2);
  const auth = override.auth_config || selectedApi.value.auth_config || {};
  authType.value = String(auth.type || "none");
  authToken.value = String(auth.token || "");
  assertionRows.value = (row.assertions?.length ? row.assertions : selectedApi.value.assertions?.length ? selectedApi.value.assertions : [{ type: "status_code", operator: "eq", expected: 200 }]).map(createAssertion);
  extractorRows.value = (override.extractors?.length ? override.extractors : [{ name: "token", path: "$.data.token" }]).map(createExtractor);
  preDataSourceIds.value = Array.isArray(row.pre_data_source_ids) ? [...row.pre_data_source_ids] : [];
  postDataSourceIds.value = Array.isArray(row.post_data_source_ids) ? [...row.post_data_source_ids] : [];
  debugResult.value = null;
  debugReqTab.value = "params";
  debugRespTab.value = "body";
  debugDrawer.value = true;
  if (editName) nextTick(startEditDebugName);
};

const startEditDebugName = async () => {
  if (!debugCaseRow.value) return;
  debugNameDraft.value = debugCaseRow.value.name;
  editingDebugName.value = true;
  await nextTick();
  debugNameInputRef.value?.focus?.();
};

const blurDebugNameInput = () => {
  debugNameInputRef.value?.blur?.();
};

const cancelEditDebugName = () => {
  editingDebugName.value = false;
  debugNameDraft.value = debugCaseRow.value?.name || "";
};

const saveDebugCaseName = async () => {
  const currentCase = debugCaseRow.value;
  if (!currentCase) return;
  const nextName = debugNameDraft.value.trim();
  if (!nextName) {
    ElMessage.warning("用例名称不能为空");
    await nextTick();
    debugNameInputRef.value?.focus?.();
    return;
  }
  editingDebugName.value = false;
  if (nextName === currentCase.name) return;
  try {
    const { data } = await platformApi.updateApiTestCase(currentCase.id, { name: nextName });
    debugCaseRow.value = data;
    const index = cases.value.findIndex((item) => item.id === data.id);
    if (index >= 0) cases.value[index] = data;
    ElMessage.success("用例名称已保存");
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || "保存用例名称失败");
    debugNameDraft.value = currentCase.name;
  }
};

const buildDebugPayload = () => {
  if (!selectedApi.value) return {};
  return {
    method: debugForm.method,
    path: debugForm.path,
    platform: selectedApi.value.platform,
    module: selectedApi.value.module,
    environment: debugForm.environment,
    query_params: enabledRows(paramsRows.value),
    headers: enabledRows(headerRows.value),
    body: parseJson(bodyText.value, {}),
    auth_config: { type: authType.value, token: authToken.value },
    pre_test_data_sources: preDataSourceIds.value,
    post_test_data_sources: postDataSourceIds.value,
    extractors: buildExtractors(),
    assertions: buildAssertions(),
  };
};

const sendDebug = async () => {
  if (!debugCaseRow.value || !selectedApi.value) return;
  sending.value = true;
  try {
    const { data } = await platformApi.debugApi(buildDebugPayload());
    debugResult.value = data;
    debugRespTab.value = "body";
  } catch (error: any) {
    ElMessage.error(error?.message || "请求失败");
  } finally {
    sending.value = false;
  }
};

const saveDebugConfig = async () => {
  if (!debugCaseRow.value) return;
  savingDebug.value = true;
  try {
    const payload = {
      request_override: {
        method: debugForm.method,
        path: debugForm.path,
        environment: debugForm.environment,
        query_params: paramsRows.value,
        headers: headerRows.value,
        body: parseJson(bodyText.value, {}),
        auth_config: { type: authType.value, token: authToken.value },
        extractors: buildExtractors(),
      },
      pre_data_source_ids: preDataSourceIds.value,
      post_data_source_ids: postDataSourceIds.value,
      assertions: buildAssertions(),
    };
    const { data } = await platformApi.updateApiTestCase(debugCaseRow.value.id, payload);
    debugCaseRow.value = data;
    const index = cases.value.findIndex((item) => item.id === data.id);
    if (index >= 0) cases.value[index] = data;
    ElMessage.success("用例调试配置已保存");
  } catch (error: any) {
    ElMessage.error(error?.message || "保存失败");
  } finally {
    savingDebug.value = false;
  }
};

onMounted(load);
</script>
