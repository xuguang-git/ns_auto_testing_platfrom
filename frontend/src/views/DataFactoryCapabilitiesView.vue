<template>
  <div class="data-factory-page">
    <header class="data-factory-head">
      <div>
        <h1>能力列表</h1>
        <p>沉淀 curl 请求和提取器规则，用于后续快速制造测试数据。</p>
      </div>
      <div class="data-factory-actions">
        <el-input v-model="keyword" placeholder="搜索能力名称、路径" clearable style="width: 260px" />
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="$router.push('/test-tools/quick-test')">去创建</el-button>
      </div>
    </header>

    <section class="data-factory-card">
      <el-table :data="filteredCapabilities" v-loading="loading" stripe height="100%">
        <el-table-column prop="name" label="能力名称" min-width="220" show-overflow-tooltip />
        <el-table-column label="请求" min-width="260" show-overflow-tooltip>
          <template #default="{ row }"><span class="inline-code">{{ row.method }} {{ row.path }}</span></template>
        </el-table-column>
        <el-table-column label="平台" width="120">
          <template #default="{ row }">{{ platformName(row.platform) }}</template>
        </el-table-column>
        <el-table-column prop="environment_name" label="环境" width="130" />
        <el-table-column label="提取字段" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ extractorNames(row) }}</template>
        </el-table-column>
        <el-table-column prop="created_by_name" label="创建人" width="120" show-overflow-tooltip />
        <el-table-column prop="updated_by_name" label="最后修改人" width="130" show-overflow-tooltip />
        <el-table-column prop="run_count" label="执行次数" width="100" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :loading="runningId === row.id" @click="runCapability(row)">执行</el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link class="danger-link" @click="deleteCapability(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="data-factory-card result-card">
      <div class="result-card-head">
        <div>
          <strong>最近执行结果</strong>
          <span v-if="lastCapability">{{ lastCapability.name }}</span>
        </div>
        <div class="result-export-actions">
          <el-button size="small" type="primary" :disabled="!lastRows.length" @click="exportLast('excel')">导出 Excel</el-button>
          <el-button size="small" :disabled="!lastRows.length" @click="exportLast('text')">导出文本</el-button>
        </div>
      </div>
      <el-table :data="lastRows" stripe height="100%">
        <el-table-column v-for="column in lastColumns" :key="column" :prop="column" :label="column" min-width="160" show-overflow-tooltip />
      </el-table>
      <el-empty v-if="!lastRows.length" description="执行能力后查看提取结果" />
    </section>

    <el-drawer v-model="editDrawer" size="78%" :with-header="false" destroy-on-close>
      <div class="capability-edit-shell">
        <header class="capability-edit-head">
          <div>
            <div class="breadcrumb-lite">数据工厂 / 能力编辑</div>
            <h2>{{ editForm.name || "未命名能力" }}</h2>
            <p>{{ editForm.method }} {{ editForm.path }}</p>
          </div>
          <div class="capability-edit-actions">
            <el-button @click="editDrawer = false">关闭</el-button>
            <el-button type="primary" :loading="savingEdit" @click="saveEdit">保存能力</el-button>
          </div>
        </header>

        <section class="capability-edit-card">
          <div class="capability-base-form">
            <el-input v-model="editForm.name" placeholder="能力名称" />
            <el-input v-model="editForm.description" placeholder="能力说明" />
            <el-select v-model="editForm.platform" clearable placeholder="平台">
              <el-option v-for="item in platforms" :key="item.code" :label="item.name" :value="item.code" />
            </el-select>
            <el-select v-model="editForm.environment" clearable placeholder="环境">
              <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
            </el-select>
          </div>

          <div class="request-line-v2 capability-request-line">
            <el-select v-model="editForm.method" style="width: 110px">
              <el-option v-for="method in methods" :key="method" :label="method" :value="method" />
            </el-select>
            <el-input v-model="editForm.path" placeholder="请求 URL 或 Path" />
          </div>

          <el-tabs v-model="editTab">
            <el-tab-pane label="Headers" name="headers"><KeyValueEditor v-model="editHeaders" /></el-tab-pane>
            <el-tab-pane label="Params" name="params"><KeyValueEditor v-model="editParams" /></el-tab-pane>
            <el-tab-pane label="Body" name="body">
              <div class="body-editor-toolbar">
                <el-button size="small" @click="formatEditBody">格式化</el-button>
              </div>
              <el-input v-model="editBodyText" type="textarea" :rows="12" />
            </el-tab-pane>
            <el-tab-pane label="提取器" name="extractors">
              <div class="extractor-panel">
                <div class="extractor-toolbar">
                  <div>
                    <strong>提取规则</strong>
                    <span>配置变量名和 JSONPath，执行能力后会按这些规则生成数据。</span>
                  </div>
                  <el-button size="small" type="primary" @click="addEditExtractor">新增规则</el-button>
                </div>
                <div class="extractor-table">
                  <div class="extractor-row extractor-head edit-extractor-row">
                    <span>变量名</span>
                    <span>JSONPath</span>
                    <span>操作</span>
                  </div>
                  <div v-for="(item, index) in editExtractors" :key="item.uid" class="extractor-row edit-extractor-row">
                    <el-input v-model="item.name" placeholder="orderNo" />
                    <el-input v-model="item.path" placeholder="$.data.orderNo" />
                    <el-button link class="danger-link" @click="removeEditExtractor(index)">删除</el-button>
                  </div>
                </div>
                <el-empty v-if="!editExtractors.length" description="暂无提取规则" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </section>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, defineComponent, h, onMounted, reactive, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";
import { formatBodyText } from "@/utils/bodyFormat";
import { extractJsonPath, formatExtractValue } from "@/utils/jsonExtract";

interface DataCapability {
  id: number;
  name: string;
  description?: string;
  platform?: string;
  environment?: number;
  environment_name?: string;
  method: string;
  path: string;
  headers?: unknown[];
  query_params?: unknown[];
  body?: unknown;
  body_text?: string;
  extractors?: { name: string; path: string }[];
  run_count?: number;
}
interface RowItem { enabled: boolean; key: string; value: string; description?: string }
interface EditExtractor { uid: number; name: string; path: string }

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
      h("button", { class: "add-row", onClick: add }, "+ Add row"),
    ]);
  },
});

const loading = ref(false);
const runningId = ref<number>();
const methods = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const keyword = ref("");
const capabilities = ref<DataCapability[]>([]);
const platformRows = ref<any[]>([]);
const environments = ref<any[]>([]);
const lastRows = ref<Record<string, string>[]>([]);
const lastColumns = ref<string[]>([]);
const lastCapability = ref<DataCapability>();
const editDrawer = ref(false);
const savingEdit = ref(false);
const editingId = ref<number>();
const editTab = ref("headers");
const editHeaders = ref<RowItem[]>([]);
const editParams = ref<RowItem[]>([]);
const editBodyText = ref("{}");
const editExtractors = ref<EditExtractor[]>([]);
const editForm = reactive({
  name: "",
  description: "",
  platform: "",
  environment: undefined as number | undefined,
  method: "GET",
  path: "",
});

const filteredCapabilities = computed(() => capabilities.value.filter((item) => !keyword.value || `${item.name} ${item.path}`.toLowerCase().includes(keyword.value.toLowerCase())));
const platforms = computed(() => platformRows.value.map((item) => ({ ...item, code: item.code?.toUpperCase?.() || item.code })));
const platformName = (code?: string) => platforms.value.find((item) => item.code === code)?.name || code || "-";
const extractorNames = (row: DataCapability) => (row.extractors || []).map((item) => item.name).join("、") || "-";

const load = async () => {
  loading.value = true;
  try {
    const [capResp, platformResp, envResp] = await Promise.all([platformApi.dataFactoryCapabilities(), platformApi.platforms(), platformApi.environments()]);
    capabilities.value = unwrapList<DataCapability>(capResp.data);
    platformRows.value = unwrapList(platformResp.data);
    environments.value = unwrapList(envResp.data);
  } finally {
    loading.value = false;
  }
};

const parseJson = (text: string, fallback: unknown) => {
  if (!text.trim()) return fallback;
  try { return JSON.parse(text); } catch { throw new Error("Body JSON 格式不正确"); }
};

const openEdit = (row: DataCapability) => {
  editingId.value = row.id;
  Object.assign(editForm, {
    name: row.name,
    description: row.description || "",
    platform: row.platform || "",
    environment: row.environment,
    method: row.method || "GET",
    path: row.path || "",
  });
  editHeaders.value = (row.headers as RowItem[]) || [];
  editParams.value = (row.query_params as RowItem[]) || [];
  editBodyText.value = row.body_text || JSON.stringify(row.body ?? {}, null, 2);
  editExtractors.value = (row.extractors || []).map((item) => ({ uid: Date.now() + Math.floor(Math.random() * 100000), name: item.name, path: item.path }));
  editTab.value = "headers";
  editDrawer.value = true;
};

const formatEditBody = () => {
  editBodyText.value = formatBodyText(editBodyText.value);
};

const addEditExtractor = () => {
  editExtractors.value.push({ uid: Date.now() + Math.floor(Math.random() * 100000), name: "", path: "$." });
};

const removeEditExtractor = (index: number) => {
  editExtractors.value.splice(index, 1);
};

const saveEdit = async () => {
  if (!editingId.value) return;
  if (!editForm.name.trim() || !editForm.path.trim()) {
    ElMessage.warning("能力名称和请求地址不能为空");
    return;
  }
  savingEdit.value = true;
  try {
    const payload = {
      name: editForm.name.trim(),
      description: editForm.description,
      platform: editForm.platform,
      environment: editForm.environment,
      method: editForm.method,
      path: editForm.path,
      headers: editHeaders.value,
      query_params: editParams.value,
      body: parseJson(editBodyText.value, {}),
      body_text: editBodyText.value,
      extractors: editExtractors.value
        .filter((item) => item.name.trim() && item.path.trim())
        .map((item) => ({ name: item.name.trim(), path: item.path.trim() })),
    };
    const { data } = await platformApi.updateDataFactoryCapability(editingId.value, payload);
    const index = capabilities.value.findIndex((item) => item.id === data.id);
    if (index >= 0) capabilities.value[index] = data;
    if (lastCapability.value?.id === data.id) lastCapability.value = data;
    ElMessage.success("能力已保存");
    editDrawer.value = false;
  } catch (error: any) {
    ElMessage.error(error?.message || "保存失败");
  } finally {
    savingEdit.value = false;
  }
};

const cellText = (value: unknown) => {
  if (value === undefined || value === null) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
};

const buildRows = (extractors: { name: string; path: string }[], body: unknown) => {
  const columns = extractors.filter((item) => item.name && item.path).map((item) => {
    const extracted = extractJsonPath(body, item.path);
    return {
      name: item.name,
      values: extracted.ok ? (Array.isArray(extracted.value) ? extracted.value : [extracted.value]) : [extracted.message],
    };
  });
  lastColumns.value = columns.map((item) => item.name);
  const rowCount = Math.max(...columns.map((item) => item.values.length), 1);
  lastRows.value = Array.from({ length: rowCount }, (_, rowIndex) => {
    const row: Record<string, string> = {};
    columns.forEach((column) => {
      row[column.name] = cellText(column.values[rowIndex]);
    });
    return row;
  });
};

const runCapability = async (row: DataCapability) => {
  runningId.value = row.id;
  try {
    const { data } = await platformApi.debugApi({
      method: row.method,
      path: row.path,
      platform: row.platform,
      environment: row.environment,
      headers: row.headers || [],
      query_params: row.query_params || [],
      body: row.body || {},
      assertions: [],
    });
    buildRows(row.extractors || [], data?.response?.body);
    lastCapability.value = row;
    await platformApi.updateDataFactoryCapability(row.id, {
      last_result: { response: data?.response, rows: lastRows.value },
      run_count: Number(row.run_count || 0) + 1,
    });
    row.run_count = Number(row.run_count || 0) + 1;
    ElMessage.success("能力执行完成");
  } finally {
    runningId.value = undefined;
  }
};

const escapeHtml = (value: string) => value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const safeFilename = (value: string) => value.trim().replace(/[\\/:*?"<>|]/g, "_") || "data-factory-result";
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

const exportLast = (type: "excel" | "text") => {
  if (!lastRows.value.length) return;
  const filename = safeFilename(lastCapability.value?.name || "data-factory-result");
  if (type === "text") {
    const text = lastRows.value.map((row) => lastColumns.value.map((column) => `${column}: ${row[column] || ""}`).join(", ")).join("\n");
    downloadFile(`${filename}.txt`, text, "text/plain;charset=utf-8");
    return;
  }
  const header = `<tr>${lastColumns.value.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr>`;
  const rows = lastRows.value.map((row) => `<tr>${lastColumns.value.map((column) => `<td>${escapeHtml(row[column] || "")}</td>`).join("")}</tr>`).join("");
  const html = `\uFEFF<html><head><meta charset="UTF-8"></head><body><table>${header}${rows}</table></body></html>`;
  downloadFile(`${filename}.xls`, html, "application/vnd.ms-excel;charset=utf-8");
};

const deleteCapability = async (row: DataCapability) => {
  await ElMessageBox.confirm(`确认删除能力「${row.name}」？`, "删除确认", { type: "warning" });
  await platformApi.deleteDataFactoryCapability(row.id);
  ElMessage.success("能力已删除");
  await load();
};

onMounted(load);
</script>
