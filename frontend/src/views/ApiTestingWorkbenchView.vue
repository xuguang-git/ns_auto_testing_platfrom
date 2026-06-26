<template>
  <div class="api-v2-shell">
    <aside class="api-v2-tree unified-tree-panel">
      <div class="tree-top unified-tree-head">
        <div class="api-work-title">
          <strong>接口管理</strong>
          <span>{{ apis.length }} 个接口</span>
        </div>
        <el-button size="small" type="primary" @click="openApiForm()">新增</el-button>
      </div>
      <div class="tree-filter">
        <el-input v-model="keyword" placeholder="搜索接口名称或路径" clearable />
      </div>
      <div class="tree-scroll unified-tree-body">
        <section v-for="platform in platformOptions" :key="platform.code" class="tree-platform">
          <button class="platform-title tree-branch-title unified-tree-node" @click="togglePlatform(platform.code)">
            <span v-if="platformHasChildren(platform.code)" class="tree-toggle" :class="{ expanded: isPlatformExpanded(platform.code) }">›</span>
            <span>{{ platform.name }}</span>
          </button>
          <template v-if="isPlatformExpanded(platform.code)">
            <template v-for="module in rootModulesForPlatform(platform.code)" :key="module.id">
              <button class="module-title tree-branch-title unified-tree-node" @click="toggleModule(module.id)">
                <span v-if="moduleHasChildren(platform.code, module.id)" class="tree-toggle" :class="{ expanded: isModuleExpanded(module.id) }">›</span>
                <span>{{ module.name }}</span>
              </button>
              <template v-if="isModuleExpanded(module.id)">
                <button
                  v-for="api in apisByModule(platform.code, module.id)"
                  :key="api.id"
                  class="api-node-v2 unified-tree-node"
                  :class="{ active: selectedApi?.id === api.id }"
                  @click="selectApi(api)"
                >
                  <span class="api-line"><i class="method-tag" :class="api.method">{{ api.method }}</i><b>{{ api.name }}</b></span>
                </button>
              </template>
            </template>
            <button
              v-for="api in apisWithoutModule(platform.code)"
              :key="api.id"
              class="api-node-v2 unified-tree-node"
              :class="{ active: selectedApi?.id === api.id }"
              @click="selectApi(api)"
            >
              <span class="api-line"><i class="method-tag" :class="api.method">{{ api.method }}</i><b>{{ api.name }}</b></span>
            </button>
          </template>
        </section>
      </div>
    </aside>

    <section v-if="selectedApi" class="api-v2-workbench">
      <header class="api-work-head">
        <div>
          <div class="api-title-row">
            <span class="method-tag" :class="selectedApi.method">{{ selectedApi.method }}</span>
            <el-input
              v-if="editingApiName"
              ref="apiNameInputRef"
              v-model="apiNameDraft"
              class="api-title-input"
              maxlength="20"
              show-word-limit
              @blur="saveApiNameIfChanged"
              @keyup.enter="blurApiNameInput"
              @keyup.esc="cancelApiNameEdit"
            />
            <button v-else class="api-title-name-button" type="button" title="点击编辑接口名称" @click="startApiNameEdit">
              <span>{{ selectedApi.name }}</span>
            </button>
            <span class="badge" :class="statusBadgeClass(selectedApi.status)">{{ statusText(selectedApi.status) }}</span>
          </div>
          <div class="api-meta-row">
            <span class="api-meta-pill">{{ platformName(selectedApi.platform) }}</span>
            <span class="api-meta-pill">{{ moduleName(selectedApi.module) }}</span>
            <span class="api-path-pill"><b>路由</b><code>{{ selectedApi.path }}</code></span>
          </div>
          <div class="api-url-card">
            <span>当前环境 URL</span>
            <code>{{ resolvedRequestUrl }}</code>
          </div>
        </div>
        <div class="api-head-actions">
          <el-button @click="goCasePage">测试用例</el-button>
          <el-button type="primary" :loading="savingApi" @click="saveCurrentApi">保存</el-button>
          <el-button :loading="sending" @click="sendDebug">发送</el-button>
        </div>
      </header>

      <el-tabs v-model="activeTab" class="api-work-tabs">
        <el-tab-pane label="调试" name="debug">
          <div class="debug-grid-v2">
            <section class="v2-card">
              <div class="request-line-v2">
                <el-select v-model="debugForm.method" style="width: 110px">
                  <el-option v-for="item in methods" :key="item" :label="item" :value="item" />
                </el-select>
                <el-input v-model="debugForm.path" />
                <el-select v-model="debugForm.environment" placeholder="环境" clearable style="width: 160px">
                  <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
                </el-select>
              </div>
              <div class="resolved-url-box">
                <span>实际请求地址</span>
                <code>{{ resolvedRequestUrl }}</code>
              </div>
              <el-tabs v-model="debugReqTab" class="request-tabs">
                <el-tab-pane label="Params" name="params"><KeyValueEditor v-model="paramsRows" /></el-tab-pane>
                <el-tab-pane label="Headers" name="headers"><KeyValueEditor v-model="headerRows" /></el-tab-pane>
                <el-tab-pane label="Body" name="body">
                  <div class="body-editor-toolbar">
                    <el-button size="small" @click="formatBody">格式化</el-button>
                  </div>
                  <el-input v-model="bodyText" type="textarea" :rows="10" placeholder='{"name":"demo"}' />
                </el-tab-pane>
                <el-tab-pane label="Auth" name="auth">
                  <div class="inline-form">
                    <el-select v-model="authType"><el-option label="不使用认证" value="none" /><el-option label="Bearer 令牌" value="bearer" /></el-select>
                    <el-input v-model="authToken" placeholder="{{token}}" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="Tests" name="tests">
                  <div class="assertion-editor">
                    <div class="assertion-editor-head">
                      <strong>可视化断言</strong>
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
                    <el-empty v-if="!assertionRows.length" description="暂无断言，点击新增断言开始配置" />
                  </div>
                </el-tab-pane>
              </el-tabs>
            </section>
            <section class="v2-card response-card-v2">
              <div class="response-meta">
                <strong>响应结果</strong>
                <span v-if="debugResult" :class="responseStatusClass">{{ debugResult.response?.status_code }} · {{ debugResult.response?.elapsed_ms }}ms</span>
              </div>
              <el-tabs v-model="debugRespTab" class="response-tabs">
                <el-tab-pane label="Body" name="body"><pre>{{ responseBodyText }}</pre></el-tab-pane>
                <el-tab-pane label="Headers" name="headers"><pre>{{ responseHeadersText }}</pre></el-tab-pane>
                <el-tab-pane label="断言" name="assertions">
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
        </el-tab-pane>

        <el-tab-pane label="设计" name="design">
          <section class="v2-card design-form-card">
            <el-form label-width="96px" :model="designForm">
              <el-form-item label="接口名称"><el-input v-model="designForm.name" /></el-form-item>
              <el-form-item label="请求路径"><el-input v-model="debugForm.path" /></el-form-item>
              <el-form-item label="状态">
                <el-select v-model="designForm.status"><el-option label="开发中" value="developing" /><el-option label="已发布" value="released" /><el-option label="已废弃" value="deprecated" /></el-select>
              </el-form-item>
              <el-form-item label="描述"><el-input v-model="designForm.description" type="textarea" :rows="4" /></el-form-item>
            </el-form>
          </section>
        </el-tab-pane>

        <el-tab-pane label="预览" name="preview">
          <section class="v2-card api-doc-preview">
            <h2>{{ selectedApi.name }}</h2>
            <p>{{ selectedApi.description || "暂无接口描述" }}</p>
            <div class="doc-line"><span>请求方式</span><b>{{ selectedApi.method }}</b></div>
            <div class="doc-line"><span>请求路径</span><code>{{ selectedApi.path }}</code></div>
            <div class="doc-line"><span>所属模块</span><b>{{ platformName(selectedApi.platform) }} / {{ moduleName(selectedApi.module) }}</b></div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="测试用例" name="cases">
          <section class="v2-card">
            <div class="card-toolbar">
              <div>
                <strong>测试用例</strong>
                <span>当前接口下的功能测试场景</span>
              </div>
              <el-button type="primary" @click="openCaseForm()">新增用例</el-button>
            </div>
            <el-table :data="cases" v-loading="caseLoading" stripe>
              <el-table-column prop="name" label="用例名称" min-width="220" />
              <el-table-column prop="method" label="请求方式" width="110"><template #default="{ row }"><span class="method-tag" :class="row.method">{{ row.method }}</span></template></el-table-column>
              <el-table-column prop="priority" label="优先级" width="100" />
              <el-table-column label="状态" width="110"><template #default="{ row }"><span class="badge" :class="caseStatusClass(row.status)">{{ caseStatusText(row.status) }}</span></template></el-table-column>
              <el-table-column prop="created_by_name" label="创建人" width="120" show-overflow-tooltip />
              <el-table-column prop="updated_by_name" label="最后修改人" width="130" show-overflow-tooltip />
              <el-table-column label="操作" width="160" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="openCaseForm(row)">编辑</el-button>
                  <el-button link class="danger-link" @click="removeCase(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="Mock" name="mock">
          <section class="v2-card">
            <div class="card-toolbar">
              <div>
                <strong>Mock</strong>
                <span>维护当前接口的模拟响应</span>
              </div>
              <el-button type="primary" @click="openMockForm()">新增规则</el-button>
            </div>
            <el-table :data="mocks" v-loading="mockLoading" stripe>
              <el-table-column prop="name" label="规则名称" min-width="180" />
              <el-table-column prop="enabled" label="开关" width="90"><template #default="{ row }"><el-switch v-model="row.enabled" @change="toggleMock(row)" /></template></el-table-column>
              <el-table-column prop="status_code" label="状态码" width="100" />
              <el-table-column prop="delay_ms" label="延迟(ms)" width="110" />
              <el-table-column label="Mock 地址" min-width="260"><template #default="{ row }"><code>/mock/api/{{ row.api }}/{{ row.id }}</code></template></el-table-column>
              <el-table-column label="操作" width="160" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="openMockForm(row)">编辑</el-button>
                  <el-button link class="danger-link" @click="removeMock(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </el-tab-pane>
      </el-tabs>
    </section>

    <section v-else class="api-v2-empty"><el-empty description="请选择左侧接口，或新增接口开始维护" /></section>

    <el-drawer v-model="apiDrawer" title="新增接口" size="560px">
      <el-form label-width="92px" :model="apiForm">
        <el-form-item label="接口名称" required><el-input v-model="apiForm.name" /></el-form-item>
        <el-form-item label="平台" required>
          <el-select v-model="apiForm.platform" style="width: 100%" @change="apiForm.module = undefined">
            <el-option v-for="item in platformOptions" :key="item.code" :label="item.name" :value="item.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="模块" required>
          <el-select v-model="apiForm.module" style="width: 100%">
            <el-option v-for="item in modulesForPlatform(apiForm.platform)" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="请求方式" required>
          <el-select v-model="apiForm.method" style="width: 100%"><el-option v-for="item in methods" :key="item" :label="item" :value="item" /></el-select>
        </el-form-item>
        <el-form-item label="请求路径" required>
          <div class="input-with-action">
            <el-input v-model="apiForm.path" placeholder="/api/orders" />
            <el-button @click="openCurlImport">解析 curl</el-button>
          </div>
        </el-form-item>
        <el-form-item label="状态"><el-select v-model="apiForm.status" style="width: 100%"><el-option label="开发中" value="developing" /><el-option label="已发布" value="released" /><el-option label="已废弃" value="deprecated" /></el-select></el-form-item>
        <el-form-item label="描述"><el-input v-model="apiForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="apiDrawer = false">取消</el-button><el-button type="primary" :loading="savingApi" @click="saveApi">保存</el-button></template>
    </el-drawer>

    <el-dialog v-model="curlDialog" title="解析 curl" width="680px">
      <el-input v-model="curlText" type="textarea" :rows="10" placeholder="粘贴 curl 命令，解析后会填充请求方式、路径、Headers、Query 和 Body" />
      <template #footer>
        <el-button @click="curlDialog = false">取消</el-button>
        <el-button type="primary" @click="applyCurlToApiForm">解析并填充</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="caseDialog" :title="editingCaseId ? '编辑用例' : '新增用例'" width="560px">
      <el-form label-width="92px" :model="caseForm">
        <el-form-item label="用例名称" required><el-input v-model="caseForm.name" /></el-form-item>
        <el-form-item label="优先级"><el-select v-model="caseForm.priority" style="width: 100%"><el-option label="P0" value="P0" /><el-option label="P1" value="P1" /><el-option label="P2" value="P2" /><el-option label="P3" value="P3" /></el-select></el-form-item>
        <el-form-item label="状态"><el-select v-model="caseForm.status" style="width: 100%"><el-option label="草稿" value="draft" /><el-option label="启用" value="active" /><el-option label="停用" value="inactive" /></el-select></el-form-item>
        <el-form-item label="描述"><el-input v-model="caseForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="caseDialog = false">取消</el-button><el-button type="primary" @click="saveCase">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="mockDialog" :title="editingMockId ? '编辑 Mock' : '新增 Mock'" width="620px">
      <el-form label-width="96px" :model="mockForm">
        <el-form-item label="规则名称" required><el-input v-model="mockForm.name" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="mockForm.enabled" /></el-form-item>
        <el-form-item label="状态码"><el-input-number v-model="mockForm.status_code" :min="100" :max="599" /></el-form-item>
        <el-form-item label="延迟"><el-input-number v-model="mockForm.delay_ms" :min="0" :max="60000" /> ms</el-form-item>
        <el-form-item label="响应 Body"><el-input v-model="mockForm.responseBodyText" type="textarea" :rows="8" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="mockDialog = false">取消</el-button><el-button type="primary" @click="saveMock">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, defineComponent, h, nextTick, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { platformApi, unwrapList } from "@/api/platform";
import { formatBodyText } from "@/utils/bodyFormat";
import { parseCurl } from "@/utils/curl";

interface RowItem { enabled: boolean; key: string; value: string; description?: string }
interface AssertionRow { uid: number; type: string; key: string; operator: string; expected: string }
interface ApiDefinition {
  id: number; name: string; platform: string; module?: number; method: string; path: string; status: string; description?: string;
  headers?: RowItem[]; query_params?: RowItem[]; body?: unknown; body_type?: string; assertions?: unknown[]; auth_config?: Record<string, unknown>;
  body_schema?: unknown; response_example?: unknown; tags?: unknown[]; sort_order?: number; is_active?: boolean; test_case_count?: number; mock_count?: number;
}
interface ApiTestCase { id: number; api: number; name: string; method: string; status: string; priority: string; description?: string }
interface ApiMockRule { id: number; api: number; name: string; enabled: boolean; status_code: number; delay_ms: number; response_body: unknown }

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
      h("button", { class: "add-row", type: "button", onClick: add }, "+ 新增字段"),
    ]);
  },
});

const methods = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const enabledRows = (rows: RowItem[]) => rows.filter((row) => row.enabled !== false);
const route = useRoute();
const router = useRouter();
const keyword = ref("");
const activeTab = ref("debug");
const debugReqTab = ref("params");
const debugRespTab = ref("body");
const loading = ref(false);
const sending = ref(false);
const savingApi = ref(false);
const savingApiName = ref(false);
const editingApiName = ref(false);
const apiNameDraft = ref("");
const apiNameInputRef = ref();
const caseLoading = ref(false);
const mockLoading = ref(false);
const apiDrawer = ref(false);
const caseDialog = ref(false);
const mockDialog = ref(false);
const curlDialog = ref(false);
const curlText = ref("");
const editingCaseId = ref<number>();
const editingMockId = ref<number>();
const apis = ref<ApiDefinition[]>([]);
const platforms = ref<any[]>([]);
const modules = ref<any[]>([]);
const environments = ref<any[]>([]);
const cases = ref<ApiTestCase[]>([]);
const mocks = ref<ApiMockRule[]>([]);
const selectedApi = ref<ApiDefinition>();
const debugResult = ref<any>();
const expandedPlatforms = ref<string[]>([]);
const expandedModules = ref<number[]>([]);
const paramsRows = ref<RowItem[]>([]);
const headerRows = ref<RowItem[]>([]);
const bodyText = ref("{}");
const assertionRows = ref<AssertionRow[]>([]);
const authType = ref("none");
const authToken = ref("");
const debugForm = reactive({ method: "GET", path: "", environment: undefined as number | undefined });
const apiForm = reactive({ name: "", platform: "", module: undefined as number | undefined, method: "GET", path: "", status: "developing", description: "" });
const apiRequestForm = reactive({ headers: [] as RowItem[], query_params: [] as RowItem[], body: {} as unknown, body_type: "none" });
const designForm = reactive({ name: "", path: "", status: "developing", description: "" });
const caseForm = reactive({ name: "", priority: "P1", status: "draft", description: "" });
const mockForm = reactive({ name: "默认 Mock", enabled: false, status_code: 200, delay_ms: 0, responseBodyText: "{}" });

const platformCode = (item: any) => item.code?.toUpperCase?.() || item.code || "";
const platformOptions = computed(() => platforms.value.map((item) => ({ ...item, code: platformCode(item) })));
const filteredApis = computed(() => apis.value.filter((item) => !keyword.value || `${item.name} ${item.path}`.toLowerCase().includes(keyword.value.toLowerCase())));
const modulePlatformCode = (module: any) => module.platform || platformCode(platforms.value.find((item) => item.id === module.managed_platform));
const modulesForPlatform = (code: string) => modules.value.filter((item) => modulePlatformCode(item) === code);
const rootModulesForPlatform = (code: string) => modulesForPlatform(code).filter((item) => !item.parent);
const apisByModule = (platform: string, moduleId: number) => filteredApis.value.filter((item) => item.platform === platform && item.module === moduleId);
const apisWithoutModule = (platform: string) => filteredApis.value.filter((item) => item.platform === platform && !item.module);
const childModules = (parentId: number) => modules.value.filter((item) => item.parent === parentId);
const platformHasChildren = (platform: string) => rootModulesForPlatform(platform).length > 0 || apisWithoutModule(platform).length > 0;
const moduleHasChildren = (platform: string, moduleId: number) => childModules(moduleId).length > 0 || apisByModule(platform, moduleId).length > 0;
const isPlatformExpanded = (platform: string) => expandedPlatforms.value.includes(platform);
const isModuleExpanded = (moduleId: number) => expandedModules.value.includes(moduleId);
const togglePlatform = (platform: string) => {
  if (!platformHasChildren(platform)) return;
  expandedPlatforms.value = isPlatformExpanded(platform) ? expandedPlatforms.value.filter((item) => item !== platform) : [...expandedPlatforms.value, platform];
};
const toggleModule = (moduleId: number) => {
  expandedModules.value = isModuleExpanded(moduleId) ? expandedModules.value.filter((item) => item !== moduleId) : [...expandedModules.value, moduleId];
};
const platformName = (code: string) => platformOptions.value.find((item) => item.code === code)?.name || code;
const moduleName = (id?: number) => modules.value.find((item) => item.id === id)?.name || "未分配";
const responseBodyText = computed(() => JSON.stringify(debugResult.value?.response?.body ?? {}, null, 2));
const responseHeadersText = computed(() => JSON.stringify(debugResult.value?.response?.headers ?? {}, null, 2));
const responseStatusClass = computed(() => Number(debugResult.value?.response?.status_code || 0) >= 400 ? "status-error" : "status-ok");
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
const buildAssertions = () =>
  assertionRows.value.map((item) => ({
    name: assertionName(item),
    type: item.type,
    operator: item.operator,
    expected: item.operator === "exists" ? "" : item.expected,
    ...(item.type === "header" ? { key: item.key } : {}),
    ...(item.type === "json_path" ? { path: item.key } : {}),
  }));
const assertionName = (item: AssertionRow) => {
  const label = { status_code: "状态码", response_time: "响应时间", header: "Header", json_path: "JSONPath", body_contains: "Body 包含" }[item.type] || item.type;
  return item.key ? `${label} ${item.key}` : label;
};
const statusText = (status: string) => ({ developing: "开发中", released: "已发布", deprecated: "已废弃" }[status] || status);
const statusBadgeClass = (status: string) => (status === "released" ? "badge-success" : status === "deprecated" ? "badge-danger" : "badge-warning");
const caseStatusText = (status: string) => ({ draft: "草稿", active: "启用", inactive: "停用" }[status] || status);
const caseStatusClass = (status: string) => (status === "active" ? "badge-success" : status === "inactive" ? "badge-danger" : "badge-warning");

const load = async () => {
  loading.value = true;
  try {
    const [apiResp, platformData, moduleData, envData] = await Promise.all([platformApi.apiDefinitions(), platformApi.cachedPlatforms(), platformApi.cachedApiModules(), platformApi.cachedEnvironments()]);
    apis.value = unwrapList<ApiDefinition>(apiResp.data);
    platforms.value = unwrapList(platformData as any);
    modules.value = unwrapList(moduleData as any);
    environments.value = unwrapList(envData as any);
    expandedPlatforms.value = platformOptions.value.filter((item) => platformHasChildren(item.code)).map((item) => item.code);
    expandedModules.value = modules.value.filter((item) => moduleHasChildren(modulePlatformCode(item), item.id)).map((item) => item.id);
    debugForm.environment = environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id;
    const queryApi = Number(route.query.apiId);
    const next = apis.value.find((item) => item.id === queryApi) || apis.value[0];
    if (route.query.tab === "debug") activeTab.value = "debug";
    if (next) selectApi(next);
  } finally {
    loading.value = false;
  }
};
const loadCases = async () => {
  if (!selectedApi.value) return;
  caseLoading.value = true;
  try {
    const { data } = await platformApi.apiTestCases({ api: selectedApi.value.id });
    cases.value = unwrapList<ApiTestCase>(data);
  } finally {
    caseLoading.value = false;
  }
};
const loadMocks = async () => {
  if (!selectedApi.value) return;
  mockLoading.value = true;
  try {
    const { data } = await platformApi.apiMockRules({ api: selectedApi.value.id });
    mocks.value = unwrapList<ApiMockRule>(data);
  } finally {
    mockLoading.value = false;
  }
};
const selectApi = async (api: ApiDefinition) => {
  editingApiName.value = false;
  apiNameDraft.value = api.name || "";
  selectedApi.value = api;
  debugForm.method = api.method;
  debugForm.path = api.path;
  paramsRows.value = api.query_params?.length ? api.query_params : [{ enabled: true, key: "", value: "", description: "" }];
  headerRows.value = api.headers?.length ? api.headers : [{ enabled: true, key: "Content-Type", value: "application/json", description: "" }];
  bodyText.value = JSON.stringify(api.body || {}, null, 2);
  assertionRows.value = (api.assertions?.length ? api.assertions : [{ type: "status_code", operator: "eq", expected: 200 }]).map(createAssertion);
  authType.value = String(api.auth_config?.type || "none");
  authToken.value = String(api.auth_config?.token || "");
  Object.assign(designForm, { name: api.name, path: api.path, status: api.status, description: api.description || "" });
  await router.replace({ path: "/api-testing/apis", query: { apiId: api.id } });
  await Promise.all([loadCases(), loadMocks()]);
};
const goCasePage = () => {
  if (!selectedApi.value) return;
  router.push({ path: "/api-testing/cases", query: { apiId: selectedApi.value.id } });
};
const startApiNameEdit = async () => {
  if (!selectedApi.value) return;
  apiNameDraft.value = selectedApi.value.name || "";
  editingApiName.value = true;
  await nextTick();
  apiNameInputRef.value?.focus?.();
};
const blurApiNameInput = () => {
  apiNameInputRef.value?.blur?.();
};
const cancelApiNameEdit = () => {
  editingApiName.value = false;
  apiNameDraft.value = selectedApi.value?.name || "";
};
const saveApiNameIfChanged = async () => {
  if (!selectedApi.value || savingApiName.value) return;
  const nextName = apiNameDraft.value.trim();
  if (!nextName) {
    ElMessage.warning("接口名称必填");
    apiNameDraft.value = selectedApi.value.name || "";
    editingApiName.value = false;
    return;
  }
  if (nextName.length > 20) {
    ElMessage.warning("接口名称不能超过20个字");
    return;
  }
  if (nextName === selectedApi.value.name) {
    editingApiName.value = false;
    return;
  }
  const payload = buildCurrentApiPayload();
  if (!payload) return;
  savingApiName.value = true;
  try {
    const { data } = await platformApi.updateApiDefinition(selectedApi.value.id, { ...payload, name: nextName });
    ElMessage.success("接口名称已保存");
    selectedApi.value = data;
    designForm.name = data.name;
    const index = apis.value.findIndex((item) => item.id === data.id);
    if (index >= 0) apis.value[index] = data;
    editingApiName.value = false;
  } finally {
    savingApiName.value = false;
  }
};
const openApiForm = () => {
  Object.assign(apiForm, {
    name: "",
    platform: platformOptions.value[0]?.code || "ERP",
    module: undefined,
    method: "GET",
    path: "",
    status: "developing",
    description: "",
  });
  Object.assign(apiRequestForm, {
    headers: [],
    query_params: [],
    body: {},
    body_type: "none",
  });
  apiDrawer.value = true;
};
const openCurlImport = () => {
  curlText.value = "";
  curlDialog.value = true;
};
const applyCurlToApiForm = () => {
  try {
    const parsed = parseCurl(curlText.value);
    apiForm.method = parsed.method;
    apiForm.path = parsed.path;
    if (!apiForm.name) apiForm.name = `${parsed.method} ${parsed.path.split("?")[0]}`;
    apiRequestForm.headers = parsed.headers;
    apiRequestForm.query_params = parsed.query_params;
    apiRequestForm.body = parsed.body;
    apiRequestForm.body_type = parsed.bodyText && parsed.bodyText !== "{}" ? "json" : "none";
    curlDialog.value = false;
    ElMessage.success("curl 已解析");
  } catch (error: any) {
    ElMessage.error(error?.message || "curl 解析失败");
  }
};
const normalizePath = (value: string) => {
  const trimmed = value.trim();
  if (!trimmed) return "";
  try {
    const url = new URL(trimmed);
    return `${url.pathname}${url.search || ""}`;
  } catch {
    return trimmed;
  }
};
const saveApi = async () => {
  if (!apiForm.name.trim() || !apiForm.path.trim() || !apiForm.platform || !apiForm.module) {
    ElMessage.warning("接口名称、平台、模块和请求路径必填");
    return;
  }
  savingApi.value = true;
  try {
    const nextPath = normalizePath(apiForm.path);
    const { data: existingResp } = await platformApi.apiDefinitions({
      platform: apiForm.platform,
      method: apiForm.method,
      search: nextPath,
    });
    const duplicated = unwrapList<ApiDefinition>(existingResp).find(
      (item) =>
        item.platform === apiForm.platform &&
        item.method === apiForm.method &&
        normalizePath(item.path) === nextPath,
    );
    if (duplicated) {
      ElMessage.warning(`接口已存在：${duplicated.name}`);
      return;
    }
    const payload = { ...apiForm, path: nextPath, ...apiRequestForm, is_active: true };
    const { data } = await platformApi.createApiDefinition(payload);
    ElMessage.success("接口已保存");
    apiDrawer.value = false;
    await load();
    selectApi(data);
  } finally {
    savingApi.value = false;
  }
};
// 当前接口保存以主页面的设计区和调试区为准，避免弹窗状态与页面状态割裂。
const buildCurrentApiPayload = () => {
  if (!selectedApi.value) return undefined;
  const nextPath = normalizePath(debugForm.path || designForm.path);
  return {
    name: designForm.name.trim(),
    platform: selectedApi.value.platform,
    module: selectedApi.value.module,
    method: debugForm.method,
    path: nextPath,
    status: designForm.status,
    description: designForm.description,
    tags: selectedApi.value.tags || [],
    headers: headerRows.value,
    query_params: paramsRows.value,
    body_type: (bodyText.value.trim() && bodyText.value.trim() !== "{}") ? "json" : "none",
    body: parseJson(bodyText.value, {}),
    body_schema: selectedApi.value.body_schema || {},
    auth_config: { type: authType.value, token: authToken.value },
    assertions: buildAssertions(),
    response_example: selectedApi.value.response_example || {},
    sort_order: selectedApi.value.sort_order || 0,
    is_active: selectedApi.value.is_active !== false,
  };
};
const saveCurrentApi = async () => {
  if (!selectedApi.value) return;
  const payload = buildCurrentApiPayload();
  if (!payload) return;
  if (!payload.name || !payload.path) {
    ElMessage.warning("接口名称和请求路径必填");
    return;
  }
  savingApi.value = true;
  try {
    const { data } = await platformApi.updateApiDefinition(selectedApi.value.id, payload);
    ElMessage.success("接口已保存");
    selectedApi.value = data;
    const index = apis.value.findIndex((item) => item.id === data.id);
    if (index >= 0) apis.value[index] = data;
    await selectApi(data);
  } finally {
    savingApi.value = false;
  }
};
const sendDebug = async () => {
  if (!selectedApi.value) return;
  sending.value = true;
  try {
    const { data } = await platformApi.debugApi({
      method: debugForm.method,
      path: debugForm.path,
      platform: selectedApi.value.platform,
      module: selectedApi.value.module,
      environment: debugForm.environment,
      query_params: enabledRows(paramsRows.value),
      headers: enabledRows(headerRows.value),
      body: parseJson(bodyText.value, {}),
      auth_config: { type: authType.value, token: authToken.value },
      assertions: buildAssertions(),
    });
    debugResult.value = data;
    debugRespTab.value = "body";
  } catch (error: any) {
    ElMessage.error(error?.message || "请求失败");
  } finally {
    sending.value = false;
  }
};
const openCaseForm = (row?: ApiTestCase) => {
  editingCaseId.value = row?.id;
  Object.assign(caseForm, { name: row?.name || "", priority: row?.priority || "P1", status: row?.status || "draft", description: row?.description || "" });
  caseDialog.value = true;
};
const saveCase = async () => {
  if (!selectedApi.value || !caseForm.name.trim()) return;
  const payload = { ...caseForm, api: selectedApi.value.id, is_active: caseForm.status !== "inactive" };
  if (editingCaseId.value) await platformApi.updateApiTestCase(editingCaseId.value, payload);
  else await platformApi.createApiTestCase(payload);
  ElMessage.success("用例已保存");
  caseDialog.value = false;
  await loadCases();
};
const removeCase = async (row: ApiTestCase) => {
  await ElMessageBox.confirm(`确认删除用例“${row.name}”？`, "删除确认", { type: "warning" });
  await platformApi.deleteApiTestCase(row.id);
  await loadCases();
};
const openMockForm = (row?: ApiMockRule) => {
  editingMockId.value = row?.id;
  Object.assign(mockForm, {
    name: row?.name || "默认 Mock",
    enabled: row?.enabled || false,
    status_code: row?.status_code || 200,
    delay_ms: row?.delay_ms || 0,
    responseBodyText: JSON.stringify(row?.response_body || {}, null, 2),
  });
  mockDialog.value = true;
};
const saveMock = async () => {
  if (!selectedApi.value || !mockForm.name.trim()) return;
  const payload = { api: selectedApi.value.id, name: mockForm.name, enabled: mockForm.enabled, status_code: mockForm.status_code, delay_ms: mockForm.delay_ms, response_body: parseJson(mockForm.responseBodyText, {}) };
  if (editingMockId.value) await platformApi.updateApiMockRule(editingMockId.value, payload);
  else await platformApi.createApiMockRule(payload);
  ElMessage.success("Mock 规则已保存");
  mockDialog.value = false;
  await loadMocks();
};
const toggleMock = async (row: ApiMockRule) => {
  await platformApi.updateApiMockRule(row.id, { enabled: row.enabled });
};
const removeMock = async (row: ApiMockRule) => {
  await ElMessageBox.confirm(`确认删除 Mock“${row.name}”？`, "删除确认", { type: "warning" });
  await platformApi.deleteApiMockRule(row.id);
  await loadMocks();
};

watch(activeTab, (tab) => {
  if (tab === "cases") loadCases();
  if (tab === "mock") loadMocks();
});
onMounted(load);
</script>
