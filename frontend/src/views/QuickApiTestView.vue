<template>
  <div class="quick-test-page">
    <section class="quick-request">
      <div class="quick-head">
        <div>
          <h1>快速测试</h1>
          <p>粘贴 curl 后解析请求，直接发送并查看响应结果。</p>
        </div>
        <div class="quick-actions">
          <el-button @click="clearData">清空数据</el-button>
          <el-button @click="parseCurlText">解析 curl</el-button>
          <el-button @click="openQuickCreate">快速新建</el-button>
          <el-button @click="openCapabilitySave">保存能力</el-button>
          <el-button type="primary" :loading="sending" @click="send">发送</el-button>
        </div>
      </div>

      <el-input v-model="curlText" type="textarea" :rows="9" placeholder="粘贴 curl 命令..." />

      <div class="quick-url-row">
        <el-select v-model="request.method" style="width: 110px">
          <el-option v-for="method in methods" :key="method" :label="method" :value="method" />
        </el-select>
        <el-input v-model="request.path" placeholder="请求 URL 或 Path" />
        <el-select v-model="request.environment" placeholder="环境" clearable style="width: 170px">
          <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
        </el-select>
      </div>

      <el-tabs v-model="activeReqTab" class="request-tabs quick-tabs">
        <el-tab-pane label="Headers" name="headers"><KeyValueEditor v-model="headers" /></el-tab-pane>
        <el-tab-pane label="Params" name="params"><KeyValueEditor v-model="params" /></el-tab-pane>
        <el-tab-pane label="Body" name="body">
          <div class="body-editor-toolbar">
            <el-button size="small" @click="formatBody">格式化</el-button>
          </div>
          <el-input v-model="bodyText" type="textarea" :rows="10" />
        </el-tab-pane>
      </el-tabs>
    </section>

    <section class="quick-response response-card-v2">
      <div class="response-meta">
        <strong>响应结果</strong>
        <span v-if="result" :class="responseStatusClass">{{ result.response?.status_code || "-" }} · {{ result.response?.elapsed_ms || "-" }}ms</span>
      </div>
      <el-tabs v-model="activeRespTab" class="response-tabs">
        <el-tab-pane label="Body" name="body"><pre>{{ responseBodyText }}</pre></el-tab-pane>
        <el-tab-pane label="提取器" name="extractor">
          <div class="extractor-panel">
            <div class="extractor-toolbar">
              <div>
                <strong>响应 JSON 提取</strong>
                <span>支持 $.data.token、$.items[0].id、$.items[*].id</span>
              </div>
              <div>
                <el-button size="small" @click="addExtractor">新增规则</el-button>
                <el-button size="small" type="primary" @click="runExtractors">执行提取</el-button>
                <el-button size="small" @click="exportExtractors">导出 Excel</el-button>
              </div>
            </div>
            <div class="extractor-table">
              <div class="extractor-row extractor-head">
                <span>变量名</span>
                <span>JSON 路径</span>
                <span>结果</span>
                <span>操作</span>
              </div>
              <div v-for="(item, index) in extractors" :key="item.uid" class="extractor-row">
                <el-input v-model="item.name" placeholder="token / ids" />
                <el-input v-model="item.path" placeholder="$.data.token" />
                <pre :class="{ error: !item.ok && item.message }">{{ item.message ? `${item.message}\n${item.valueText}` : "待提取" }}</pre>
                <div class="extractor-actions">
                  <el-button link type="primary" @click="copyExtractor(item)">复制</el-button>
                  <el-button link class="danger-link" @click="removeExtractor(index)">删除</el-button>
                </div>
              </div>
            </div>
            <el-empty v-if="!extractors.length" description="暂无提取规则" />
          </div>
        </el-tab-pane>
        <el-tab-pane label="Headers" name="headers"><pre>{{ responseHeadersText }}</pre></el-tab-pane>
        <el-tab-pane label="Logs" name="logs"><pre>{{ (result?.logs || []).join("\n") }}</pre></el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog v-model="createDialog" title="快速新建接口" width="560px">
      <el-form :model="createForm" label-width="92px">
        <el-form-item label="接口名称" required>
          <el-input v-model="createForm.name" placeholder="例如：查询订单列表" />
        </el-form-item>
        <el-form-item label="平台" required>
          <el-select v-model="createForm.platform" style="width: 100%" @change="createForm.module = undefined">
            <el-option v-for="item in platformOptions" :key="item.code" :label="item.name" :value="item.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="模块" required>
          <el-select v-model="createForm.module" style="width: 100%">
            <el-option v-for="item in modulesForPlatform(createForm.platform)" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="请求方式">
          <el-input :model-value="request.method" disabled />
        </el-form-item>
        <el-form-item label="请求路径">
          <el-input :model-value="request.path" disabled />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="saveQuickCreate">新建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="capabilityDialog" title="保存数据能力" width="560px">
      <el-form :model="capabilityForm" label-width="92px">
        <el-form-item label="能力名称" required>
          <el-input v-model="capabilityForm.name" placeholder="例如：创建订单并提取订单号" />
        </el-form-item>
        <el-form-item label="能力说明">
          <el-input v-model="capabilityForm.description" type="textarea" :rows="3" placeholder="说明该能力制造的数据和提取字段" />
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="capabilityForm.platform" clearable style="width: 100%">
            <el-option v-for="item in platformOptions" :key="item.code" :label="item.name" :value="item.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="环境">
          <el-select v-model="capabilityForm.environment" clearable style="width: 100%">
            <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="capabilityDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingCapability" @click="saveCapability">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, defineComponent, h, onMounted, reactive, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";
import { formatBodyText } from "@/utils/bodyFormat";
import { parseCurl } from "@/utils/curl";
import { extractJsonPath, formatExtractValue } from "@/utils/jsonExtract";

interface RowItem { enabled: boolean; key: string; value: string; description?: string }
interface ExtractorRow { uid: number; name: string; path: string; ok: boolean; message: string; valueText: string; value?: unknown }

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
    return () => h("div", { class: "kv-editor" }, [
      h("table", { class: "kv-table" }, [
        h("thead", [h("tr", [h("th", ""), h("th", "Key"), h("th", "Value"), h("th", "Description")])]),
        h("tbody", (props.modelValue as RowItem[]).map((row, index) => h("tr", { key: index }, [
          h("td", [h("input", { type: "checkbox", checked: row.enabled, onChange: (e: Event) => update(index, "enabled", (e.target as HTMLInputElement).checked) })]),
          h("td", [h("input", { value: row.key, onInput: (e: Event) => update(index, "key", (e.target as HTMLInputElement).value) })]),
          h("td", [h("input", { value: row.value, onInput: (e: Event) => update(index, "value", (e.target as HTMLInputElement).value) })]),
          h("td", [h("input", { value: row.description, onInput: (e: Event) => update(index, "description", (e.target as HTMLInputElement).value) })]),
        ]))),
      ]),
      h("button", { class: "add-row", type: "button", onClick: add }, "+ 新增字段"),
    ]);
  },
});

const methods = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const curlText = ref("");
const sending = ref(false);
const activeReqTab = ref("headers");
const activeRespTab = ref("body");
const environments = ref<any[]>([]);
const platforms = ref<any[]>([]);
const modules = ref<any[]>([]);
const headers = ref<RowItem[]>([]);
const params = ref<RowItem[]>([]);
const bodyText = ref("{}");
const result = ref<any>();
const createDialog = ref(false);
const creating = ref(false);
const capabilityDialog = ref(false);
const savingCapability = ref(false);
const extractors = ref<ExtractorRow[]>([{ uid: Date.now(), name: "token", path: "$.data.token", ok: false, message: "", valueText: "", value: undefined }]);
const request = reactive({ method: "GET", path: "", environment: undefined as number | undefined });
const createForm = reactive({ name: "", platform: "", module: undefined as number | undefined });
const capabilityForm = reactive({ name: "", description: "", platform: "", environment: undefined as number | undefined });

const responseBodyText = computed(() => JSON.stringify(result.value?.response?.body ?? {}, null, 2));
const responseHeadersText = computed(() => JSON.stringify(result.value?.response?.headers ?? {}, null, 2));
const responseStatusClass = computed(() => Number(result.value?.response?.status_code || 0) >= 400 ? "status-error" : "status-ok");
const platformCode = (item: any) => item.code?.toUpperCase?.() || item.code || "";
const platformOptions = computed(() => platforms.value.map((item) => ({ ...item, code: platformCode(item) })));
const modulePlatformCode = (module: any) => module.platform || platformCode(platforms.value.find((item) => item.id === module.managed_platform));
const modulesForPlatform = (code: string) => modules.value.filter((item) => modulePlatformCode(item) === code);

const parseJson = (text: string, fallback: unknown) => {
  if (!text.trim()) return fallback;
  try { return JSON.parse(text); } catch { return text; }
};

const parseCurlText = () => {
  try {
    const parsed = parseCurl(curlText.value);
    request.method = parsed.method;
    request.path = parsed.url;
    headers.value = parsed.headers;
    params.value = parsed.query_params;
    bodyText.value = parsed.bodyText;
    ElMessage.success("curl 已解析");
  } catch (error: any) {
    ElMessage.error(error?.message || "curl 解析失败");
  }
};

const clearData = () => {
  curlText.value = "";
  request.method = "GET";
  request.path = "";
  request.environment = environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id;
  headers.value = [];
  params.value = [];
  bodyText.value = "{}";
  result.value = undefined;
  extractors.value = [{ uid: Date.now(), name: "token", path: "$.data.token", ok: false, message: "", valueText: "", value: undefined }];
  activeReqTab.value = "headers";
  activeRespTab.value = "body";
};

const formatBody = () => {
  bodyText.value = formatBodyText(bodyText.value);
  ElMessage.success("Body 已格式化");
};

const inferName = () => {
  const path = request.path.trim();
  if (!path) return "";
  try {
    const url = new URL(path);
    return `${request.method} ${url.pathname}`;
  } catch {
    return `${request.method} ${path.split("?")[0]}`;
  }
};

const parseRequestTarget = (value: string) => {
  const trimmed = value.trim();
  if (!trimmed) return { path: "", queryParams: [] as RowItem[] };
  try {
    const url = new URL(trimmed);
    return {
      path: url.pathname || "/",
      queryParams: Array.from(url.searchParams.entries()).map(([key, value]) => ({ enabled: true, key, value, description: "" })),
    };
  } catch {
    const [path, search = ""] = trimmed.split("?");
    return {
      path: path || "/",
      queryParams: Array.from(new URLSearchParams(search).entries()).map(([key, value]) => ({ enabled: true, key, value, description: "" })),
    };
  }
};
const normalizePath = (value: string) => parseRequestTarget(value).path;
const mergeQueryParams = (parsedRows: RowItem[], currentRows: RowItem[]) => {
  const result = [...parsedRows];
  currentRows.forEach((row) => {
    if (!row.key.trim()) return;
    const index = result.findIndex((item) => item.key === row.key);
    if (index >= 0) {
      result[index] = row;
    } else {
      result.push(row);
    }
  });
  return result;
};

const openQuickCreate = () => {
  if (!request.path.trim()) {
    ElMessage.warning("请先解析 curl 或填写请求 URL");
    return;
  }
  createForm.name = inferName();
  createForm.platform = createForm.platform || platformOptions.value[0]?.code || "";
  createForm.module = createForm.module || modulesForPlatform(createForm.platform)[0]?.id;
  createDialog.value = true;
};

const saveQuickCreate = async () => {
  if (!createForm.name.trim() || !createForm.platform || !createForm.module) {
    ElMessage.warning("接口名称、平台和模块必填");
    return;
  }
  creating.value = true;
  try {
    const requestTarget = parseRequestTarget(request.path);
    const nextPath = requestTarget.path;
    const nextParams = mergeQueryParams(requestTarget.queryParams, params.value);
    const { data: existingResp } = await platformApi.apiDefinitions({
      platform: createForm.platform,
      method: request.method,
      search: nextPath,
    });
    const existingApis = unwrapList<any>(existingResp);
    const duplicated = existingApis.find((item) => item.platform === createForm.platform && item.method === request.method && normalizePath(item.path) === nextPath);
    if (duplicated) {
      ElMessage.warning(`接口已存在：${duplicated.name}`);
      return;
    }
    await platformApi.createApiDefinition({
      name: createForm.name.trim(),
      platform: createForm.platform,
      module: createForm.module,
      method: request.method,
      path: nextPath,
      status: "developing",
      headers: headers.value,
      query_params: nextParams,
      body_type: bodyText.value.trim() && bodyText.value.trim() !== "{}" ? "json" : "none",
      body: parseJson(bodyText.value, {}),
      assertions: [{ type: "status_code", operator: "eq", expected: 200 }],
      is_active: true,
    });
    ElMessage.success("接口已新建");
    createDialog.value = false;
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || "新建失败");
  } finally {
    creating.value = false;
  }
};

const cleanExtractors = () => extractors.value
  .filter((item) => item.name.trim() && item.path.trim())
  .map((item) => ({ name: item.name.trim(), path: item.path.trim() }));

const openCapabilitySave = () => {
  if (!request.path.trim()) {
    ElMessage.warning("请先解析 curl 或填写请求 URL");
    return;
  }
  Object.assign(capabilityForm, {
    name: capabilityForm.name || inferName(),
    description: capabilityForm.description,
    platform: capabilityForm.platform || createForm.platform || platformOptions.value[0]?.code || "",
    environment: capabilityForm.environment || request.environment,
  });
  capabilityDialog.value = true;
};

const saveCapability = async () => {
  if (!capabilityForm.name.trim()) {
    ElMessage.warning("请填写能力名称");
    return;
  }
  savingCapability.value = true;
  try {
    await platformApi.createDataFactoryCapability({
      name: capabilityForm.name.trim(),
      description: capabilityForm.description,
      platform: capabilityForm.platform,
      environment: capabilityForm.environment,
      method: request.method,
      path: request.path,
      curl: curlText.value,
      headers: headers.value,
      query_params: params.value,
      body: parseJson(bodyText.value, {}),
      body_text: bodyText.value,
      extractors: cleanExtractors(),
      is_active: true,
    });
    ElMessage.success("数据能力已保存");
    capabilityDialog.value = false;
  } finally {
    savingCapability.value = false;
  }
};

const addExtractor = () => {
  extractors.value.push({ uid: Date.now() + Math.floor(Math.random() * 10000), name: "", path: "$.", ok: false, message: "", valueText: "", value: undefined });
};

const removeExtractor = (index: number) => {
  extractors.value.splice(index, 1);
};

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
  if (!result.value?.response) {
    ElMessage.warning("请先发送请求获取响应");
    return;
  }
  const body = result.value.response.body;
  extractors.value = extractors.value.map((item) => {
    const extracted = extractJsonPath(body, item.path);
    return {
      ...item,
      ok: extracted.ok,
      message: extracted.message,
      valueText: extracted.ok ? formatExtractValue(extracted.value) : "",
      value: extracted.ok ? extracted.value : undefined,
    };
  });
  activeRespTab.value = "extractor";
};

const excelCellText = (value: unknown) => {
  if (value === undefined || value === null) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
};

const escapeHtml = (value: string) => value
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;");

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

const exportExtractors = () => {
  const columns = extractors.value.filter((item) => item.ok && item.name.trim());
  if (!columns.length) {
    ElMessage.warning("暂无可导出的提取结果");
    return;
  }
  const columnValues = columns.map((item) => ({
    name: item.name.trim(),
    values: Array.isArray(item.value) ? item.value : [item.value],
  }));
  const rowCount = Math.max(...columnValues.map((item) => item.values.length), 1);
  const header = `<tr>${columnValues.map((column) => `<th>${escapeHtml(column.name)}</th>`).join("")}</tr>`;
  const rows = Array.from({ length: rowCount }, (_, rowIndex) =>
    `<tr>${columnValues.map((column) => `<td>${escapeHtml(excelCellText(column.values[rowIndex]))}</td>`).join("")}</tr>`,
  ).join("");
  const html = `\uFEFF<html><head><meta charset="UTF-8"></head><body><table>${header}${rows}</table></body></html>`;
  downloadFile(`quick-test-extractors-${Date.now()}.xls`, html, "application/vnd.ms-excel;charset=utf-8");
  ElMessage.success("提取结果已导出");
};

const send = async () => {
  if (!request.path.trim()) {
    ElMessage.warning("请先填写请求 URL 或粘贴 curl");
    return;
  }
  sending.value = true;
  try {
    const { data } = await platformApi.debugApi({
      method: request.method,
      path: request.path,
      environment: request.environment,
      headers: headers.value,
      query_params: params.value,
      body: parseJson(bodyText.value, {}),
      assertions: [],
    });
    result.value = data;
    activeRespTab.value = "body";
  } finally {
    sending.value = false;
  }
};

onMounted(async () => {
  const [envResp, platformResp, moduleResp] = await Promise.all([platformApi.environments(), platformApi.platforms(), platformApi.apiModules()]);
  environments.value = unwrapList(envResp.data);
  platforms.value = unwrapList(platformResp.data);
  modules.value = unwrapList(moduleResp.data);
  request.environment = environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id;
  createForm.platform = platformOptions.value[0]?.code || "";
  createForm.module = modulesForPlatform(createForm.platform)[0]?.id;
});
</script>
