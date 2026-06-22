<template>
  <div class="case-debug-content">
    <header class="debug-head">
      <div>
        <span class="muted">用例调试</span>
        <h3>{{ caseName }}</h3>
        <p><span class="method-mini" :class="request.method">{{ request.method || "-" }}</span> {{ request.path || "-" }}</p>
      </div>
      <div class="debug-actions">
        <span class="environment-pill">环境：{{ environmentName }}</span>
        <el-button :loading="running" type="primary" @click="$emit('run')">运行</el-button>
        <el-button @click="$emit('close')">关闭</el-button>
      </div>
    </header>

    <div class="debug-panels">
      <section class="debug-panel">
        <div class="panel-title">
          <strong>请求内容</strong>
          <span>{{ request.platform || "-" }}</span>
        </div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="方法">{{ request.method || "-" }}</el-descriptions-item>
          <el-descriptions-item label="路径">{{ request.path || "-" }}</el-descriptions-item>
          <el-descriptions-item label="平台">{{ request.platform || "-" }}</el-descriptions-item>
          <el-descriptions-item label="环境">{{ environmentName }}</el-descriptions-item>
        </el-descriptions>
        <el-tabs v-model="requestTab">
          <el-tab-pane label="Params" name="params"><KeyValuePreview :rows="request.query_params" /></el-tab-pane>
          <el-tab-pane label="Headers" name="headers"><KeyValuePreview :rows="request.headers" /></el-tab-pane>
          <el-tab-pane label="Body" name="body"><JsonPreview :value="request.body" empty-text="无请求体" /></el-tab-pane>
          <el-tab-pane label="Auth" name="auth"><JsonPreview :value="request.auth_config" empty-text="无认证配置" /></el-tab-pane>
          <el-tab-pane label="断言" name="assertions"><AssertionPreview :rows="request.assertions" /></el-tab-pane>
        </el-tabs>
      </section>

      <section class="debug-panel">
        <div class="panel-title">
          <strong>响应内容</strong>
          <span v-if="result" :class="responseOk ? 'ok-text' : 'failed-text'">{{ responseStatusText }}</span>
          <span v-else>未运行</span>
        </div>
        <el-empty v-if="!result" description="运行用例后查看响应内容" />
        <template v-else>
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="结果">{{ responseOk ? "成功" : "失败" }}</el-descriptions-item>
            <el-descriptions-item label="状态码">{{ responseStatus }}</el-descriptions-item>
            <el-descriptions-item label="耗时">{{ responseElapsed }}</el-descriptions-item>
          </el-descriptions>
          <el-tabs v-model="responseTab">
            <el-tab-pane label="Body" name="body"><JsonPreview :value="responseBody" empty-text="无响应体" /></el-tab-pane>
            <el-tab-pane label="Headers" name="headers"><JsonPreview :value="responseHeaders" empty-text="无响应头" /></el-tab-pane>
            <el-tab-pane label="断言结果" name="assertions"><AssertionResultPreview :rows="assertionRows" /></el-tab-pane>
            <el-tab-pane label="Logs" name="logs"><LogPreview :rows="logRows" /></el-tab-pane>
          </el-tabs>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, ref } from "vue";

const props = defineProps<{
  caseName: string;
  request: Record<string, any>;
  result?: Record<string, any> | null;
  environmentName?: string;
  running?: boolean;
}>();

defineEmits<{
  run: [];
  close: [];
}>();

const requestTab = ref("params");
const responseTab = ref("body");
const environmentName = computed(() => props.environmentName || "-");
const responseStatus = computed(() => props.result?.response?.status_code || "-");
const responseElapsed = computed(() => props.result?.response?.elapsed_ms ? `${props.result.response.elapsed_ms}ms` : "-");
const responseOk = computed(() => Boolean(props.result?.ok) && Number(props.result?.response?.status_code || 0) < 400);
const responseStatusText = computed(() => `${responseOk.value ? "成功" : "失败"} / ${responseStatus.value}`);
const responseBody = computed(() => props.result?.response?.body);
const responseHeaders = computed(() => props.result?.response?.headers);
const assertionRows = computed(() => props.result?.assertions || []);
const logRows = computed(() => props.result?.logs || []);

const normalizeRows = (rows: any) => Array.isArray(rows) ? rows : [];
const prettyJson = (value: unknown, emptyText: string) => {
  if (value === undefined || value === null || value === "" || (Array.isArray(value) && !value.length)) return emptyText;
  if (typeof value === "object" && !Array.isArray(value) && !Object.keys(value as Record<string, unknown>).length) return emptyText;
  return JSON.stringify(value, null, 2);
};

const KeyValuePreview = defineComponent({
  props: { rows: { type: [Array, Object], default: () => [] } },
  setup(componentProps) {
    return () => {
      const rows = normalizeRows(componentProps.rows);
      if (!rows.length) return h("div", { class: "empty-lite" }, "暂无数据");
      return h("div", { class: "kv-preview" }, rows.map((row: any, index: number) =>
        h("div", { class: "kv-preview-row", key: index }, [
          h("span", { class: row.enabled === false ? "disabled" : "" }, row.key || "-"),
          h("code", row.value === undefined || row.value === "" ? "-" : String(row.value)),
          h("em", row.description || ""),
        ]),
      ));
    };
  },
});

const JsonPreview = defineComponent({
  props: { value: { type: null, default: undefined }, emptyText: { type: String, default: "暂无数据" } },
  setup(componentProps) {
    return () => h("pre", { class: "json-preview" }, prettyJson(componentProps.value, componentProps.emptyText));
  },
});

const AssertionPreview = defineComponent({
  props: { rows: { type: Array, default: () => [] } },
  setup(componentProps) {
    return () => {
      const rows = normalizeRows(componentProps.rows);
      if (!rows.length) return h("div", { class: "empty-lite" }, "暂无断言");
      return h("div", { class: "assertion-preview" }, rows.map((row: any, index: number) =>
        h("div", { class: "assertion-row", key: index }, [
          h("b", row.name || row.type || "鏂█"),
          h("span", `${row.key || row.path || ""} ${row.operator || ""} ${row.expected ?? ""}`.trim()),
        ]),
      ));
    };
  },
});

const AssertionResultPreview = defineComponent({
  props: { rows: { type: Array, default: () => [] } },
  setup(componentProps) {
    return () => {
      const rows = normalizeRows(componentProps.rows);
      if (!rows.length) return h("div", { class: "empty-lite" }, "暂无断言结果");
      return h("div", { class: "assertion-preview" }, rows.map((row: any, index: number) =>
        h("div", { class: ["assertion-row", row.passed ? "passed" : "failed"], key: index }, [
          h("b", row.passed ? "PASS" : "FAIL"),
          h("span", row.name || row.type || "鏂█"),
          h("em", `expected ${row.expected ?? "-"}, actual ${row.actual ?? "-"}`),
        ]),
      ));
    };
  },
});

const LogPreview = defineComponent({
  props: { rows: { type: Array, default: () => [] } },
  setup(componentProps) {
    return () => {
      const rows = normalizeRows(componentProps.rows);
      return h("pre", { class: "json-preview" }, rows.length ? rows.join("\n") : "暂无日志");
    };
  },
});
</script>

<style scoped>
.case-debug-content { height: 100%; display: flex; flex-direction: column; gap: 14px; padding: 18px; }
.debug-head, .debug-actions, .panel-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.debug-head h3, .debug-head p { margin: 0; }
.debug-head p { margin-top: 6px; }
.muted, .panel-title span { color: var(--el-text-color-secondary); font-size: 13px; }
.environment-pill { color: var(--el-text-color-secondary); font-size: 13px; }
.debug-panels { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.debug-panel { min-height: 0; border: 1px solid var(--el-border-color-light); border-radius: 8px; padding: 12px; overflow: auto; }
.panel-title { margin-bottom: 10px; }
.kv-preview { display: grid; gap: 8px; }
.kv-preview-row { display: grid; grid-template-columns: minmax(120px, 180px) minmax(160px, 1fr) minmax(100px, 180px); gap: 8px; align-items: center; min-height: 32px; border-bottom: 1px solid var(--el-border-color-lighter); }
.kv-preview-row span { font-weight: 600; }
.kv-preview-row .disabled { color: var(--el-text-color-disabled); text-decoration: line-through; }
.kv-preview-row code, .json-preview { background: var(--el-fill-color-light); border-radius: 6px; padding: 8px; }
.kv-preview-row em { color: var(--el-text-color-secondary); font-style: normal; }
.json-preview { margin: 0; white-space: pre-wrap; word-break: break-word; font-size: 12px; line-height: 1.55; }
.assertion-preview { display: grid; gap: 8px; }
.assertion-row { display: grid; gap: 3px; border: 1px solid var(--el-border-color-lighter); border-radius: 6px; padding: 8px; }
.assertion-row.passed b, .ok-text { color: var(--el-color-success); }
.assertion-row.failed b, .failed-text { color: var(--el-color-danger); }
.assertion-row span, .assertion-row em, .empty-lite { color: var(--el-text-color-secondary); }
.assertion-row em { font-style: normal; font-size: 12px; }
@media (max-width: 980px) { .debug-panels { grid-template-columns: 1fr; } }
</style>


