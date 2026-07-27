<template>
  <section class="api-integration-page">
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="接口说明" name="docs">
        <div class="docs-workbench">
          <aside class="capability-list panel">
            <el-input v-model="capabilityKeyword" placeholder="搜索接口名称、编码" clearable />
            <div class="capability-scroll">
              <button v-for="item in filteredCapabilities" :key="item.code" class="capability-item" :class="{ active: selectedCode === item.code }" @click="selectCapability(item.code)">
                <b>{{ item.name }}</b>
                <small>{{ item.code }} | {{ item.version }}</small>
              </button>
            </div>
          </aside>
          <article class="documentation panel" v-loading="documentationLoading">
            <template v-if="documentation">
              <header><div><h2>{{ documentation.name }}</h2><p>{{ documentation.method }} {{ documentation.path }}</p></div></header>
              <div class="documentation-scroll">
                <p>{{ documentation.documentation.overview }}</p>
                <h3>请求示例 <el-button size="small" @click="copyRequest">复制请求</el-button></h3>
                <pre>{{ requestDisplay }}</pre>
                <h3>请求 Headers</h3>
                <el-table :data="documentation.documentation.headers" size="small">
                  <el-table-column prop="name" label="Header" />
                  <el-table-column prop="required" label="必填" width="78"><template #default="scope">{{ scope.row.required ? "是" : "否" }}</template></el-table-column>
                  <el-table-column prop="description" label="说明" />
                </el-table>
                <h3>字段说明</h3>
                <el-table :data="documentation.documentation.request_fields" size="small">
                  <el-table-column prop="name" label="字段" min-width="160" />
                  <el-table-column prop="type" label="类型" width="100" />
                  <el-table-column prop="required" label="必填" width="78"><template #default="scope">{{ scope.row.required ? "是" : "否" }}</template></el-table-column>
                  <el-table-column prop="description" label="说明" min-width="260" />
                </el-table>
                <h3>模块编码说明</h3>
                <section class="module-table">
                  <div class="sticky-filter"><el-input v-model="moduleKeyword" placeholder="搜索模块名称" clearable /></div>
                  <el-table :data="filteredModules" size="small">
                    <el-table-column prop="code" label="模块编码" min-width="160" />
                    <el-table-column prop="name" label="模块名称" min-width="140" />
                    <el-table-column label="目录路径" min-width="260"><template #default="scope">{{ scope.row.path_names.join(" / ") }}</template></el-table-column>
                    <el-table-column prop="platform" label="平台" width="100" />
                  </el-table>
                </section>
              </div>
            </template>
          </article>
        </div>
      </el-tab-pane>

      <el-tab-pane label="调用日志" name="logs">
        <section class="log-panel panel">
          <div class="log-toolbar">
            <div class="log-filters">
              <el-input v-model="logFilters.keyword" placeholder="搜索请求 ID、批次号" clearable @keyup.enter="loadLogs(1)" @clear="loadLogs(1)" />
              <el-select v-model="logFilters.status" clearable placeholder="全部调用状态" @change="loadLogs(1)">
                <el-option v-for="item in callStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
              <el-button type="primary" @click="loadLogs(1)">查询</el-button>
            </div>
            <span class="log-tip">接口资产批量导入</span>
          </div>
          <el-table :data="logs" v-loading="logsLoading" stripe class="log-table">
            <el-table-column prop="request_id" label="请求 ID" min-width="190" show-overflow-tooltip />
            <el-table-column label="内部接口" min-width="180">
              <template #default="scope"><b>{{ scope.row.capability_name }}</b><small class="sub-text">{{ scope.row.capability_code }}</small></template>
            </el-table-column>
            <el-table-column prop="caller_name" label="调用人" width="120" />
            <el-table-column label="调用状态" width="115"><template #default="scope"><span class="status-badge" :class="callStatusClass(scope.row.status)">{{ callStatusText(scope.row.status) }}</span></template></el-table-column>
            <el-table-column label="数据处理结果" min-width="290" show-overflow-tooltip><template #default="scope">{{ formatSummary(scope.row.result_summary) }}</template></el-table-column>
            <el-table-column label="调用时间" min-width="165"><template #default="scope">{{ formatTime(scope.row.created_at) }}</template></el-table-column>
            <el-table-column label="操作" width="190" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="showLog(scope.row)">调用详情</el-button>
                <el-button v-if="scope.row.related_batch_no" link type="primary" @click="showBatch(scope.row.related_batch_no)">查看批次结果</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination"><el-pagination v-model:current-page="logPage" :page-size="15" :total="logTotal" layout="total, prev, pager, next" @current-change="loadLogs" /></div>
        </section>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="logDialog" title="调用详情" width="600px" destroy-on-close>
      <el-descriptions v-if="selectedLog" :column="1" border>
        <el-descriptions-item label="请求 ID">{{ selectedLog.request_id }}</el-descriptions-item>
        <el-descriptions-item label="内部接口">{{ selectedLog.capability_name }} <span class="sub-text">{{ selectedLog.capability_code }}</span></el-descriptions-item>
        <el-descriptions-item label="调用人">{{ selectedLog.caller_name || "-" }}</el-descriptions-item>
        <el-descriptions-item label="调用状态"><span class="status-badge" :class="callStatusClass(selectedLog.status)">{{ callStatusText(selectedLog.status) }}</span></el-descriptions-item>
        <el-descriptions-item label="数据处理结果">{{ formatSummary(selectedLog.result_summary) }}</el-descriptions-item>
        <el-descriptions-item v-if="selectedLog.related_batch_no" label="关联批次"><el-button link type="primary" @click="showBatch(selectedLog.related_batch_no)">{{ selectedLog.related_batch_no }}</el-button></el-descriptions-item>
        <el-descriptions-item label="调用时间">{{ formatTime(selectedLog.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <p class="safe-tip">调用日志仅展示调用状态和安全的数据处理结果，不展示请求内容、响应内容或内部异常信息。</p>
      <template #footer><el-button type="primary" @click="logDialog = false">关闭</el-button></template>
    </el-dialog>

    <el-dialog v-model="batchDialog" title="导入批次结果" width="820px">
      <el-descriptions v-if="batch" :column="3" border>
        <el-descriptions-item label="批次号">{{ batch.batch_no }}</el-descriptions-item>
        <el-descriptions-item label="处理状态"><span class="status-badge" :class="batchStatusClass(batch.status)">{{ batchStatusText(batch.status) }}</span></el-descriptions-item>
        <el-descriptions-item label="导入总数">{{ batch.total }}</el-descriptions-item>
        <el-descriptions-item label="成功导入"><span class="count-success">{{ batch.success_count }}</span></el-descriptions-item>
        <el-descriptions-item label="已跳过"><span class="count-warning">{{ batch.skipped_count }}</span></el-descriptions-item>
        <el-descriptions-item label="导入失败"><span class="count-danger">{{ batch.failed_count }}</span></el-descriptions-item>
      </el-descriptions>
      <h3>未成功处理项</h3>
      <div class="batch-table">
        <div class="sticky-filter"><el-input v-model="batchKeyword" placeholder="搜索接口名称" clearable /></div>
        <el-table :data="filteredBatchItems" size="small">
          <el-table-column prop="sequence_no" label="序号" width="70" />
          <el-table-column prop="name" label="接口名称" min-width="160" />
          <el-table-column prop="method" label="方法" width="90" />
          <el-table-column prop="path" label="路径" min-width="240" show-overflow-tooltip />
          <el-table-column label="处理结果" width="120"><template #default="scope"><span class="status-badge" :class="itemStatusClass(scope.row.status)">{{ itemStatusText(scope.row.status) }}</span></template></el-table-column>
        </el-table>
      </div>
      <p class="safe-tip">仅展示未成功处理的接口资产，不展示原始参数、请求内容或内部异常信息。</p>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";

import { platformApi } from "@/api/platform";

const CALL_STATUS: Record<string, { text: string; className: string }> = {
  success: { text: "调用成功", className: "success" },
  business_failed: { text: "业务失败", className: "danger" },
  auth_failed: { text: "鉴权失败", className: "danger" },
  system_failed: { text: "系统异常", className: "danger" },
};
const BATCH_STATUS: Record<string, { text: string; className: string }> = {
  queued: { text: "排队中", className: "warning" },
  running: { text: "处理中", className: "primary" },
  completed: { text: "已完成", className: "success" },
  completed_with_errors: { text: "部分完成", className: "warning" },
  failed: { text: "处理失败", className: "danger" },
};
const ITEM_STATUS: Record<string, { text: string; className: string }> = {
  pending: { text: "待处理", className: "warning" },
  success: { text: "已导入", className: "success" },
  skipped: { text: "已跳过", className: "warning" },
  failed: { text: "导入失败", className: "danger" },
};

const activeTab = ref("docs");
const capabilities = ref<any[]>([]);
const selectedCode = ref("");
const documentation = ref<any>();
const capabilityKeyword = ref("");
const moduleKeyword = ref("");
const documentationLoading = ref(false);
const logs = ref<any[]>([]);
const logsLoading = ref(false);
const logFilters = ref({ keyword: "", status: "" });
const logPage = ref(1);
const logTotal = ref(0);
const selectedLog = ref<any>();
const logDialog = ref(false);
const batch = ref<any>();
const batchDialog = ref(false);
const batchKeyword = ref("");

const callStatusOptions = Object.entries(CALL_STATUS).map(([value, item]) => ({ value, label: item.text }));
const filteredCapabilities = computed(() => capabilities.value.filter(item => (item.name + item.code).toLowerCase().includes(capabilityKeyword.value.toLowerCase())));
const filteredModules = computed(() => (documentation.value?.module_codes || []).filter((item: any) => item.name.includes(moduleKeyword.value)));
const filteredBatchItems = computed(() => (batch.value?.items || []).filter((item: any) => item.name.includes(batchKeyword.value)));
const requestDisplay = computed(() => documentation.value ? [documentation.value.method + " " + documentation.value.path, "Cookie: ns_access_token=<access_token>", "Content-Type: application/json", "", JSON.stringify(documentation.value.request_example, null, 2)].join("\n") : "");

const statusText = (mapping: Record<string, { text: string }>, value: string) => mapping[value]?.text || value || "-";
const statusClass = (mapping: Record<string, { className: string }>, value: string) => mapping[value]?.className || "default";
const callStatusText = (value: string) => statusText(CALL_STATUS, value);
const callStatusClass = (value: string) => statusClass(CALL_STATUS, value);
const batchStatusText = (value: string) => statusText(BATCH_STATUS, value);
const batchStatusClass = (value: string) => statusClass(BATCH_STATUS, value);
const itemStatusText = (value: string) => statusText(ITEM_STATUS, value);
const itemStatusClass = (value: string) => statusClass(ITEM_STATUS, value);
const formatTime = (value: string) => value ? value.replace("T", " ").replace(/\.\d+Z$/, "") : "-";
const formatSummary = (value: Record<string, any>) => {
  if (!value || !Object.keys(value).length) return "-";
  if (value.batch_no) return "批次 " + value.batch_no + "：" + batchStatusText(String(value.status || "")) + "，成功 " + (value.success_count || 0) + "，跳过 " + (value.skipped_count || 0) + "，失败 " + (value.failed_count || 0);
  return value.state === "未处理" ? "未创建导入批次" : Object.entries(value).map(([key, item]) => key + ": " + item).join("；");
};

const loadCapabilities = async () => {
  const { data } = await platformApi.internalApiDocuments();
  capabilities.value = data;
  if (data.length) await selectCapability(data[0].code);
};
const selectCapability = async (code: string) => {
  selectedCode.value = code;
  documentationLoading.value = true;
  try {
    documentation.value = (await platformApi.internalApiDocument(code)).data;
  } finally {
    documentationLoading.value = false;
  }
};
const copyRequest = async () => {
  await navigator.clipboard.writeText(documentation.value?.curl_example || "");
  ElMessage.success("cURL 请求已复制");
};
const loadLogs = async (page = logPage.value) => {
  logPage.value = page;
  logsLoading.value = true;
  try {
    const { data } = await platformApi.apiImportCallLogs({ page, keyword: logFilters.value.keyword || undefined, status: logFilters.value.status || undefined });
    logs.value = data.results;
    logTotal.value = data.count;
  } finally {
    logsLoading.value = false;
  }
};
const handleTabChange = async (tab: string | number) => {
  if (tab === "logs" && !logs.value.length) await loadLogs(1);
};
const showLog = async (row: any) => {
  selectedLog.value = (await platformApi.apiImportCallLog(row.request_id)).data;
  logDialog.value = true;
};
const showBatch = async (batchNo: string) => {
  batch.value = (await platformApi.apiImportBatch(batchNo)).data;
  batchKeyword.value = "";
  batchDialog.value = true;
};

onMounted(loadCapabilities);
</script>

<style scoped>
.api-integration-page{height:100%;min-height:0}.docs-workbench{display:grid;height:calc(100vh - 175px);min-height:580px;grid-template-columns:270px minmax(0,1fr);gap:16px}.panel{border:1px solid var(--el-border-color-lighter);border-radius:8px;background:#fff}.capability-list{display:flex;min-height:0;flex-direction:column;padding:12px}.capability-scroll,.documentation-scroll{min-height:0;overflow-y:auto}.capability-scroll{margin-top:10px}.capability-item{width:100%;border:0;border-radius:6px;padding:10px;background:transparent;text-align:left}.capability-item.active{background:var(--el-color-primary-light-9)}.capability-item small,.sub-text{display:block;margin-top:4px;color:var(--el-text-color-secondary);font-size:12px}.documentation{display:flex;min-height:0;flex-direction:column}.documentation>header{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--el-border-color-lighter)}.documentation h2{margin:0}.documentation header p{margin:5px 0 0;color:var(--el-text-color-secondary)}.documentation-scroll{padding:18px 20px}.documentation h3{margin:22px 0 10px;font-size:15px}.documentation pre{padding:14px;border-radius:6px;background:#172033;color:#dbeafe;white-space:pre-wrap}.module-table,.batch-table{height:482px;overflow-y:auto;border:1px solid var(--el-border-color-lighter);border-radius:6px}.batch-table{height:513px}.sticky-filter{position:sticky;top:0;z-index:2;padding:10px;background:#fff;border-bottom:1px solid var(--el-border-color-lighter)}.log-panel{overflow:hidden}.log-toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px;border-bottom:1px solid var(--el-border-color-lighter)}.log-filters{display:flex;gap:10px}.log-filters .el-input{width:270px}.log-filters .el-select{width:140px}.log-tip{color:var(--el-text-color-secondary);font-size:13px}.log-table :deep(.el-table__cell){vertical-align:middle}.pagination{display:flex;justify-content:flex-end;padding:14px}.status-badge{display:inline-flex;align-items:center;gap:5px;border-radius:12px;padding:3px 8px;font-size:12px;line-height:18px}.status-badge::before{width:6px;height:6px;border-radius:50%;background:currentColor;content:""}.status-badge.success{background:var(--el-color-success-light-9);color:var(--el-color-success)}.status-badge.warning{background:var(--el-color-warning-light-9);color:var(--el-color-warning)}.status-badge.danger{background:var(--el-color-danger-light-9);color:var(--el-color-danger)}.status-badge.primary{background:var(--el-color-primary-light-9);color:var(--el-color-primary)}.status-badge.default{background:var(--el-fill-color-light);color:var(--el-text-color-secondary)}.count-success{color:var(--el-color-success)}.count-warning{color:var(--el-color-warning)}.count-danger{color:var(--el-color-danger)}.safe-tip{margin:18px 0 0;border:1px solid var(--el-color-primary-light-7);border-radius:6px;padding:10px 12px;background:var(--el-color-primary-light-9);color:var(--el-color-primary-dark-2);line-height:1.6}@media (max-width:900px){.docs-workbench{height:auto;grid-template-columns:1fr}.capability-list{max-height:240px}.log-toolbar,.log-filters{align-items:stretch;flex-direction:column}.log-filters .el-input,.log-filters .el-select{width:100%}}
</style>
