<template>
  <div class="performance-page">
    <PageHeader title="性能测试" description="接入 JMeter 执行器，管理脚本、压测任务、执行记录和性能报告。" />

    <section class="perf-executor-card">
      <div>
        <strong>执行器状态</strong>
        <p>{{ executor?.message || (executor?.ok ? "Java、JMeter 和结果目录均可用。" : "点击检查当前服务器执行器配置。") }}</p>
        <div v-if="executor" class="perf-executor-detail">
          <span :class="executor.java?.ok ? 'ok' : 'failed'">Java：{{ executor.java?.version || executor.java?.error || "未识别" }}</span>
          <span :class="executor.jmeter?.ok ? 'ok' : 'failed'">JMeter：{{ executor.jmeter?.version || executor.jmeter?.error || "未识别" }}</span>
          <span :class="executor.result_dir_writable ? 'ok' : 'failed'">结果目录：{{ executor.result_dir }}</span>
        </div>
      </div>
      <span v-if="executor" class="badge" :class="executor.ok ? 'badge-success' : 'badge-danger'">{{ executor.ok ? "可用" : "未配置" }}</span>
      <el-button type="primary" :loading="checking" @click="checkExecutor">检查本机执行器</el-button>
    </section>

    <el-tabs v-model="activeTab" class="perf-tabs">
      <el-tab-pane label="JMeter 脚本" name="scripts">
        <section class="perf-toolbar">
          <el-input v-model="scriptKeyword" placeholder="搜索脚本名称" clearable style="width: 280px" />
          <el-button @click="load">刷新</el-button>
          <el-button type="primary" @click="openScriptDialog">上传 JMX</el-button>
        </section>
        <section class="perf-card">
          <el-table :data="filteredScripts" v-loading="loading" stripe height="100%">
            <el-table-column prop="name" label="脚本名称" min-width="180" />
            <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
            <el-table-column prop="task_count" label="任务数" width="90" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }"><span class="badge" :class="row.is_active ? 'badge-success' : 'badge-warning'">{{ row.is_active ? "启用" : "停用" }}</span></template>
            </el-table-column>
            <el-table-column prop="updated_at" label="更新时间" min-width="170" />
            <el-table-column label="操作" width="210" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" :disabled="!row.is_active" @click="openTaskDialog(undefined, row)">建任务</el-button>
                <el-button link type="primary" @click="toggleScript(row)">{{ row.is_active ? "停用" : "启用" }}</el-button>
                <el-button link class="danger-link" @click="deleteScript(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </el-tab-pane>

      <el-tab-pane label="性能任务" name="tasks">
        <section class="perf-toolbar">
          <el-input v-model="taskKeyword" placeholder="搜索任务名称" clearable style="width: 280px" />
          <el-button @click="load">刷新</el-button>
          <el-button type="primary" @click="openTaskDialog()">新增任务</el-button>
        </section>
        <section class="perf-card">
          <el-table :data="filteredTasks" v-loading="loading" stripe height="100%">
            <el-table-column prop="name" label="任务名称" min-width="180" />
            <el-table-column prop="script_name" label="JMX 脚本" min-width="170" />
            <el-table-column prop="threads" label="并发" width="80" />
            <el-table-column prop="ramp_up_seconds" label="Ramp-up" width="100" />
            <el-table-column prop="duration_seconds" label="持续(s)" width="100" />
            <el-table-column prop="loops" label="循环" width="80" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }"><span class="badge" :class="row.is_active ? 'badge-success' : 'badge-warning'">{{ row.is_active ? "启用" : "停用" }}</span></template>
            </el-table-column>
            <el-table-column label="操作" width="270" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" :disabled="!row.is_active" :loading="runningTaskId === row.id" @click="runTask(row)">执行</el-button>
                <el-button link type="primary" @click="openTaskDialog(row)">编辑</el-button>
                <el-button link type="primary" @click="toggleTask(row)">{{ row.is_active ? "停用" : "启用" }}</el-button>
                <el-button link class="danger-link" @click="deleteTask(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </el-tab-pane>

      <el-tab-pane label="执行记录" name="runs">
        <section class="perf-toolbar">
          <el-button @click="load">刷新</el-button>
        </section>
        <section class="perf-card">
          <el-table :data="runs" v-loading="loading" stripe height="100%">
            <el-table-column prop="id" label="#" width="70" />
            <el-table-column prop="task_name" label="任务" min-width="160" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }"><span class="badge" :class="runBadge(row.status)">{{ runStatusText(row.status) }}</span></template>
            </el-table-column>
            <el-table-column label="可执行" width="90">
              <template #default="{ row }">
                <span class="badge" :class="canExecuteRun(row) ? 'badge-success' : 'badge-warning'">{{ canExecuteRun(row) ? "可执行" : runBlockReason(row) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="总请求" width="90"><template #default="{ row }">{{ row.summary?.total || 0 }}</template></el-table-column>
            <el-table-column label="失败率" width="90"><template #default="{ row }">{{ row.summary?.error_rate || 0 }}%</template></el-table-column>
            <el-table-column label="平均(ms)" width="100"><template #default="{ row }">{{ row.summary?.avg_ms || 0 }}</template></el-table-column>
            <el-table-column label="P95(ms)" width="100"><template #default="{ row }">{{ row.summary?.p95_ms || 0 }}</template></el-table-column>
            <el-table-column label="TPS" width="90"><template #default="{ row }">{{ row.summary?.tps || 0 }}</template></el-table-column>
            <el-table-column prop="created_at" label="创建时间" min-width="170" />
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openRun(row)">详情</el-button>
                <el-button link type="primary" :disabled="row.status !== 'completed'" @click="openHtmlReport(row)">查看 HTML</el-button>
                <el-button v-if="row.status === 'pending'" link type="primary" :disabled="!canExecuteRun(row)" @click="executeRun(row)">继续执行</el-button>
                <el-button v-if="row.status === 'pending'" link class="danger-link" @click="markRunFailed(row)">标记失败</el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="scriptDialog" title="上传 JMeter 脚本" width="520px">
      <el-form label-width="86px">
        <el-form-item label="脚本名称" required><el-input v-model="scriptForm.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="scriptForm.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="JMX 文件" required>
          <input type="file" accept=".jmx" @change="onFileChange" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scriptDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveScript">上传</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="taskDialog" :title="taskForm.id ? '编辑性能任务' : '新增性能任务'" width="620px">
      <el-form :model="taskForm" label-width="100px">
        <el-form-item label="任务名称" required><el-input v-model="taskForm.name" /></el-form-item>
        <el-form-item label="JMX 脚本" required>
          <el-select v-model="taskForm.script" filterable style="width: 100%">
            <el-option v-for="script in scripts" :key="script.id" :label="script.name" :value="script.id" />
          </el-select>
        </el-form-item>
        <div class="perf-form-grid">
          <el-form-item label="并发数"><el-input-number v-model="taskForm.threads" :min="1" :max="100000" /></el-form-item>
          <el-form-item label="Ramp-up"><el-input-number v-model="taskForm.ramp_up_seconds" :min="0" :max="86400" /></el-form-item>
          <el-form-item label="持续时间"><el-input-number v-model="taskForm.duration_seconds" :min="1" :max="604800" /></el-form-item>
          <el-form-item label="循环次数"><el-input-number v-model="taskForm.loops" :min="1" :max="1000000" /></el-form-item>
        </div>
        <el-form-item label="描述"><el-input v-model="taskForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taskDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveTask">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="runDialog" title="性能报告详情" width="760px">
      <div v-if="activeRun" class="perf-run-detail">
        <div class="perf-summary-grid">
          <div><span>总请求</span><strong>{{ activeRun.summary?.total || 0 }}</strong></div>
          <div><span>失败率</span><strong>{{ activeRun.summary?.error_rate || 0 }}%</strong></div>
          <div><span>P95</span><strong>{{ activeRun.summary?.p95_ms || 0 }}ms</strong></div>
          <div><span>TPS</span><strong>{{ activeRun.summary?.tps || 0 }}</strong></div>
        </div>
        <div class="run-log-list">
          <div v-for="(item, index) in activeRun.logs || []" :key="index" class="run-log-item" :class="item.level || 'info'">
            <span>{{ formatLogTime(item.time) }}</span>
            <b>{{ item.level || "info" }}</b>
            <p>{{ item.message }}</p>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import { http } from "@/api/http";
import { platformApi, unwrapList } from "@/api/platform";
import PageHeader from "@/components/PageHeader.vue";

const activeTab = ref("scripts");
const loading = ref(false);
const saving = ref(false);
const checking = ref(false);
const runningTaskId = ref<number>();
const executor = ref<any>();
const scripts = ref<any[]>([]);
const tasks = ref<any[]>([]);
const runs = ref<any[]>([]);
const scriptKeyword = ref("");
const taskKeyword = ref("");
const scriptDialog = ref(false);
const taskDialog = ref(false);
const runDialog = ref(false);
const activeRun = ref<any>();
const selectedFile = ref<File>();
let refreshTimer: number | undefined;
const scriptForm = reactive({ name: "", description: "" });
const taskForm = reactive({ id: undefined as number | undefined, name: "", script: undefined as number | undefined, threads: 10, ramp_up_seconds: 10, duration_seconds: 60, loops: 1, description: "" });

const filteredScripts = computed(() => scripts.value.filter((item) => !scriptKeyword.value || item.name.toLowerCase().includes(scriptKeyword.value.toLowerCase())));
const filteredTasks = computed(() => tasks.value.filter((item) => !taskKeyword.value || item.name.toLowerCase().includes(taskKeyword.value.toLowerCase())));
const runStatusText = (status: string) => ({ pending: "待执行", running: "执行中", completed: "完成", failed: "失败" }[status] || status || "未知");
const runBadge = (status: string) => (status === "completed" ? "badge-success" : status === "failed" ? "badge-danger" : "badge-warning");
const formatLogTime = (value?: string) => value ? value.replace("T", " ").slice(0, 19) : "";
const canExecuteRun = (row: any) => row.task_is_active !== false && row.script_is_active !== false;
const runBlockReason = (row: any) => row.script_is_active === false ? "脚本停用" : row.task_is_active === false ? "任务停用" : "不可执行";

const load = async () => {
  loading.value = true;
  try {
    const [scriptResp, taskResp, runResp] = await Promise.all([
      platformApi.performanceScripts(),
      platformApi.performanceTasks(),
      platformApi.performanceRuns(),
    ]);
    scripts.value = unwrapList(scriptResp.data);
    tasks.value = unwrapList(taskResp.data);
    runs.value = unwrapList(runResp.data);
  } finally {
    loading.value = false;
  }
};

const checkExecutor = async () => {
  checking.value = true;
  try {
    const { data } = await platformApi.performanceExecutor();
    executor.value = data;
    if (data.ok) ElMessage.success("性能测试执行器可用");
    else ElMessage.warning(data.message || "当前未配置性能测试执行器");
  } finally {
    checking.value = false;
  }
};

const openScriptDialog = () => {
  Object.assign(scriptForm, { name: "", description: "" });
  selectedFile.value = undefined;
  scriptDialog.value = true;
};

const onFileChange = (event: Event) => {
  selectedFile.value = (event.target as HTMLInputElement).files?.[0];
  if (selectedFile.value && !scriptForm.name) scriptForm.name = selectedFile.value.name.replace(/\.jmx$/i, "");
};

const saveScript = async () => {
  if (!scriptForm.name.trim() || !selectedFile.value) {
    ElMessage.warning("请填写脚本名称并选择 JMX 文件");
    return;
  }
  saving.value = true;
  try {
    const form = new FormData();
    form.append("name", scriptForm.name.trim());
    form.append("description", scriptForm.description);
    form.append("file", selectedFile.value);
    await platformApi.createPerformanceScript(form);
    ElMessage.success("JMX 脚本已上传");
    scriptDialog.value = false;
    await load();
  } finally {
    saving.value = false;
  }
};

const openTaskDialog = (row?: any, script?: any) => {
  Object.assign(taskForm, {
    id: row?.id,
    name: row?.name || "",
    script: row?.script || script?.id || scripts.value[0]?.id,
    threads: row?.threads || 10,
    ramp_up_seconds: row?.ramp_up_seconds || 10,
    duration_seconds: row?.duration_seconds || 60,
    loops: row?.loops || 1,
    description: row?.description || "",
  });
  taskDialog.value = true;
};

const saveTask = async () => {
  if (!taskForm.name.trim() || !taskForm.script) {
    ElMessage.warning("请填写任务名称并选择 JMX 脚本");
    return;
  }
  saving.value = true;
  try {
    const payload = { ...taskForm, name: taskForm.name.trim() };
    if (taskForm.id) await platformApi.updatePerformanceTask(taskForm.id, payload);
    else await platformApi.createPerformanceTask(payload);
    ElMessage.success("性能任务已保存");
    taskDialog.value = false;
    await load();
  } finally {
    saving.value = false;
  }
};

const runTask = async (row: any) => {
  if (!executor.value?.ok) await checkExecutor();
  if (!executor.value?.ok) return;
  runningTaskId.value = row.id;
  try {
    await platformApi.runPerformanceTask(row.id);
    ElMessage.success("性能任务已提交执行");
    activeTab.value = "runs";
    await load();
    startRunRefresh();
  } catch (error: any) {
    ElMessage.warning(error?.response?.data?.detail || error?.response?.data?.message || "性能任务执行失败");
  } finally {
    runningTaskId.value = undefined;
  }
};

const openRun = (row: any) => {
  activeRun.value = row;
  runDialog.value = true;
};

const openHtmlReport = async (row: any) => {
  const { data } = await http.get(`/performance/runs/${row.id}/html-report/`, { responseType: "text", timeout: 120000 });
  const reportWindow = window.open("", `_blank`);
  if (!reportWindow) {
    ElMessage.warning("浏览器阻止了报告窗口，请允许弹窗后重试");
    return;
  }
  reportWindow.document.open();
  reportWindow.document.write(data);
  reportWindow.document.close();
};

const toggleScript = async (row: any) => {
  await platformApi.togglePerformanceScript(row.id);
  ElMessage.success(row.is_active ? "JMeter 脚本已停用" : "JMeter 脚本已启用");
  await load();
};

const toggleTask = async (row: any) => {
  await platformApi.togglePerformanceTask(row.id);
  ElMessage.success(row.is_active ? "性能任务已停用" : "性能任务已启用");
  await load();
};

const markRunFailed = async (row: any) => {
  await platformApi.markPerformanceRunFailed(row.id);
  ElMessage.success("执行记录已标记失败");
  await load();
};

const executeRun = async (row: any) => {
  if (!canExecuteRun(row)) {
    ElMessage.warning(`无法继续执行：${runBlockReason(row)}`);
    return;
  }
  try {
    await platformApi.executePerformanceRun(row.id);
    ElMessage.success("执行记录已重新提交");
    await load();
    startRunRefresh();
  } catch (error: any) {
    ElMessage.warning(error?.response?.data?.detail || "继续执行失败");
  }
};

const startRunRefresh = () => {
  if (refreshTimer) window.clearInterval(refreshTimer);
  let count = 0;
  refreshTimer = window.setInterval(async () => {
    count += 1;
    await load();
    const hasActiveRun = runs.value.some((item) => item.status === "pending" || item.status === "running");
    if (!hasActiveRun || count >= 20) {
      window.clearInterval(refreshTimer);
      refreshTimer = undefined;
    }
  }, 3000);
};

const deleteScript = async (row: any) => {
  await ElMessageBox.confirm(`确认删除脚本「${row.name}」？`, "删除确认", { type: "warning" });
  await platformApi.deletePerformanceScript(row.id);
  await load();
};

const deleteTask = async (row: any) => {
  await ElMessageBox.confirm(`确认删除任务「${row.name}」？`, "删除确认", { type: "warning" });
  await platformApi.deletePerformanceTask(row.id);
  await load();
};

onMounted(async () => {
  await Promise.all([load(), checkExecutor()]);
});
</script>
