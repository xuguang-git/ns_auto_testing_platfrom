<template>
  <div class="scheduling-page">
    <PageHeader title="调度计划" description="按 Cron 定时执行测试计划，支持启停、立即运行和最近执行状态追踪。" />

    <section class="scheduling-toolbar">
      <el-input v-model="keyword" placeholder="搜索任务名称、Cron、测试计划" clearable style="width: 320px" />
      <el-select v-model="statusFilter" clearable placeholder="状态" style="width: 140px">
        <el-option label="启用" value="true" />
        <el-option label="停用" value="false" />
      </el-select>
      <el-button @click="load">刷新</el-button>
      <el-button type="primary" @click="openDialog()">新增任务</el-button>
    </section>

    <section class="scheduling-card">
      <el-table :data="filteredSchedules" v-loading="loading" stripe height="100%">
        <el-table-column prop="name" label="任务名称" min-width="180" />
        <el-table-column prop="plan_name" label="测试计划" min-width="180" show-overflow-tooltip />
        <el-table-column prop="environment_name" label="运行环境" min-width="130" show-overflow-tooltip />
        <el-table-column prop="cron" label="Cron" width="150" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <span class="badge" :class="row.is_active ? 'badge-success' : 'badge-warning'">{{ row.is_active ? "启用" : "停用" }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="next_run_at" label="下次运行" min-width="170" />
        <el-table-column prop="last_run_at" label="最近运行" min-width="170" />
        <el-table-column label="最近结果" width="110">
          <template #default="{ row }">
            <span class="badge" :class="statusBadge(row.last_status)">{{ row.last_status || "-" }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="run_count" label="次数" width="80" />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :loading="runningId === row.id" @click="runNow(row)">立即执行</el-button>
            <el-button link type="primary" @click="toggle(row)">{{ row.is_active ? "停用" : "启用" }}</el-button>
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link class="danger-link" @click="deleteSchedule(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑调度任务' : '新增调度任务'" width="560px">
      <el-form :model="form" label-width="92px">
        <el-form-item label="任务名称" required>
          <el-input v-model="form.name" placeholder="每日冒烟测试" />
        </el-form-item>
        <el-form-item label="测试计划" required>
          <el-select v-model="form.plan" filterable style="width: 100%" @change="onPlanChange">
            <el-option v-for="plan in plans" :key="plan.id" :label="plan.name" :value="plan.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="运行环境" required>
          <el-select v-model="form.environment" filterable style="width: 100%">
            <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Cron" required>
          <el-input v-model="form.cron" placeholder="*/30 * * * *" />
        </el-form-item>
        <el-form-item label="快捷配置">
          <div class="cron-presets">
            <button v-for="item in cronPresets" :key="item.value" type="button" @click="form.cron = item.value">{{ item.label }}</button>
          </div>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";
import PageHeader from "@/components/PageHeader.vue";

interface TestPlan { id: number; name: string; is_active: boolean; environment?: number }
interface Environment { id: number; name: string; is_default?: boolean }
interface ScheduledPlan {
  id: number;
  name: string;
  plan: number;
  plan_name: string;
  environment?: number;
  environment_name?: string;
  cron: string;
  is_active: boolean;
  last_run_at?: string;
  next_run_at?: string;
  last_run_id?: number;
  last_status?: string;
  run_count: number;
}

const loading = ref(false);
const saving = ref(false);
const runningId = ref<number>();
const dialogVisible = ref(false);
const keyword = ref("");
const statusFilter = ref("");
const schedules = ref<ScheduledPlan[]>([]);
const plans = ref<TestPlan[]>([]);
const environments = ref<Environment[]>([]);
const form = reactive({ id: undefined as number | undefined, name: "", plan: undefined as number | undefined, environment: undefined as number | undefined, cron: "0 9 * * *", is_active: true });
const cronPresets = [
  { label: "每 30 分钟", value: "*/30 * * * *" },
  { label: "每小时", value: "0 * * * *" },
  { label: "每天 9 点", value: "0 9 * * *" },
  { label: "工作日 9 点", value: "0 9 * * 1-5" },
];

const filteredSchedules = computed(() => schedules.value.filter((item) => {
  const text = `${item.name} ${item.plan_name} ${item.cron}`.toLowerCase();
  const statusMatched = !statusFilter.value || String(item.is_active) === statusFilter.value;
  return statusMatched && (!keyword.value || text.includes(keyword.value.toLowerCase()));
}));

const statusBadge = (status?: string) => {
  if (status === "completed" || status === "passed") return "badge-success";
  if (status === "failed") return "badge-danger";
  if (status === "running" || status === "pending") return "badge-warning";
  return "badge-gray";
};

const load = async () => {
  loading.value = true;
  try {
    const [scheduleResp, planResp, envResp] = await Promise.all([platformApi.scheduledPlans(), platformApi.testPlans(), platformApi.environments()]);
    schedules.value = unwrapList<ScheduledPlan>(scheduleResp.data);
    plans.value = unwrapList<TestPlan>(planResp.data).filter((item) => item.is_active !== false);
    environments.value = unwrapList<Environment>(envResp.data);
  } finally {
    loading.value = false;
  }
};

const openDialog = (row?: ScheduledPlan) => {
  const plan = plans.value.find((item) => item.id === row?.plan) || plans.value[0];
  Object.assign(form, {
    id: row?.id,
    name: row?.name || "",
    plan: row?.plan || plan?.id,
    environment: row?.environment || plan?.environment || environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id,
    cron: row?.cron || "0 9 * * *",
    is_active: row?.is_active ?? true,
  });
  dialogVisible.value = true;
};

const onPlanChange = () => {
  const plan = plans.value.find((item) => item.id === form.plan);
  form.environment = plan?.environment || environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id;
};

const save = async () => {
  if (!form.name.trim() || !form.plan || !form.environment || !form.cron.trim()) {
    ElMessage.warning("请填写任务名称、测试计划、运行环境和 Cron");
    return;
  }
  saving.value = true;
  try {
    const payload = { name: form.name.trim(), plan: form.plan, environment: form.environment, cron: form.cron.trim(), is_active: form.is_active };
    if (form.id) await platformApi.updateScheduledPlan(form.id, payload);
    else await platformApi.createScheduledPlan(payload);
    ElMessage.success("调度任务已保存");
    dialogVisible.value = false;
    await load();
  } finally {
    saving.value = false;
  }
};

const toggle = async (row: ScheduledPlan) => {
  await platformApi.toggleScheduledPlan(row.id);
  ElMessage.success(row.is_active ? "调度任务已停用" : "调度任务已启用");
  await load();
};

const runNow = async (row: ScheduledPlan) => {
  runningId.value = row.id;
  try {
    await platformApi.runScheduledPlanNow(row.id);
    ElMessage.success("已创建调度执行任务");
    await load();
  } finally {
    runningId.value = undefined;
  }
};

const deleteSchedule = async (row: ScheduledPlan) => {
  await ElMessageBox.confirm(`确认删除调度任务「${row.name}」？`, "删除确认", { type: "warning" });
  await platformApi.deleteScheduledPlan(row.id);
  ElMessage.success("调度任务已删除");
  await load();
};

onMounted(load);
</script>


