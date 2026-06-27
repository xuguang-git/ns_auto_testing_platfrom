<template>
  <div class="scheduling-page">
    <PageHeader title="调度计划" description="按 Cron 定时执行测试套件，支持启停、立即运行和最近执行状态追踪。" />

    <section class="scheduling-toolbar">
      <el-input v-model="keyword" placeholder="搜索任务名称、Cron、测试套件" clearable style="width: 320px" />
      <el-select v-model="statusFilter" clearable placeholder="状态" style="width: 140px">
        <el-option label="启用" value="true" />
        <el-option label="停用" value="false" />
      </el-select>
      <el-button @click="loadSchedules">刷新</el-button>
      <el-button type="primary" @click="openDialog()">新增任务</el-button>
    </section>

    <section class="scheduling-card">
      <el-table :data="filteredSchedules" v-loading="loading" stripe height="100%">
        <el-table-column prop="name" label="任务名称" min-width="180" />
        <el-table-column prop="suite_name" label="测试套件" min-width="180" show-overflow-tooltip />
        <el-table-column prop="environment_name" label="运行环境" min-width="130" show-overflow-tooltip />
        <el-table-column prop="cron" label="Cron" width="150" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <span class="badge" :class="row.is_active ? 'badge-success' : 'badge-warning'">{{ row.is_active ? "启用" : "停用" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="下次运行" min-width="170">
          <template #default="{ row }">{{ formatDateTime(row.next_run_at) }}</template>
        </el-table-column>
        <el-table-column label="最近运行" min-width="170">
          <template #default="{ row }">{{ formatDateTime(row.last_run_at) }}</template>
        </el-table-column>
        <el-table-column label="最近结果" width="110">
          <template #default="{ row }">
            <span class="badge" :class="statusBadge(row.last_status)">{{ lastStatusText(row.last_status) }}</span>
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
        <el-form-item label="测试套件" required>
          <el-select v-model="form.suite" filterable style="width: 100%" @change="onSuiteChange">
            <el-option v-for="suite in suites" :key="suite.id" :label="suite.name" :value="suite.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="运行环境" required>
          <el-select v-model="form.environment" filterable style="width: 100%">
            <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="消息通知">
          <el-select v-model="form.notifications" multiple filterable collapse-tags collapse-tags-tooltip clearable style="width: 100%" placeholder="选择消息通知">
            <el-option
              v-for="notification in notifications"
              :key="notification.id"
              :label="`${notification.name}（${notification.push_platform_display}）`"
              :value="notification.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="消息模板">
          <el-select v-model="form.notification_template" filterable clearable style="width: 100%" placeholder="选择消息模板">
            <el-option v-for="template in availableNotificationTemplates" :key="template.id" :label="template.name" :value="template.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="推送条件">
          <el-select v-model="form.notify_on" style="width: 100%">
            <el-option label="不推送" value="disabled" />
            <el-option label="成功/失败都推送" value="always" />
            <el-option label="仅失败推送" value="failed_only" />
          </el-select>
        </el-form-item>
        <el-form-item label="运行周期" required>
          <div class="schedule-period-control">
            <el-select v-model="form.period" style="width: 140px" @change="syncCronFromPeriod">
              <el-option label="按日" value="daily" />
              <el-option label="按周" value="weekly" />
            </el-select>
            <el-checkbox-group v-if="form.period === 'weekly'" v-model="form.weekdays" @change="syncCronFromPeriod">
              <el-checkbox-button v-for="item in weekdayOptions" :key="item.value" :label="item.value">{{ item.label }}</el-checkbox-button>
            </el-checkbox-group>
            <el-time-picker v-model="form.run_time" format="HH:mm" value-format="HH:mm" placeholder="12:00" @change="syncCronFromPeriod" />
          </div>
          <div class="schedule-cron-preview">Cron：{{ form.cron || "-" }}</div>
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

interface ApiSuite { id: number; name: string; is_active?: boolean; run_config?: Record<string, any> }
interface Environment { id: number; name: string; is_default?: boolean }
interface NotificationChannel { id: number; name: string; push_platform_display: string; is_active?: boolean }
interface NotificationTemplate { id: number; name: string; channel?: number; is_active?: boolean }
interface ScheduledPlan {
  id: number;
  name: string;
  suite: number;
  suite_name: string;
  environment?: number;
  environment_name?: string;
  notifications?: number[];
  notification_names?: string[];
  notification_template?: number;
  notification_template_name?: string;
  notify_on?: "disabled" | "always" | "failed_only";
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
const suites = ref<ApiSuite[]>([]);
const environments = ref<Environment[]>([]);
const notifications = ref<NotificationChannel[]>([]);
const notificationTemplates = ref<NotificationTemplate[]>([]);
const form = reactive({
  id: undefined as number | undefined,
  name: "",
  suite: undefined as number | undefined,
  environment: undefined as number | undefined,
  notifications: [] as number[],
  notification_template: undefined as number | undefined,
  notify_on: "disabled" as "disabled" | "always" | "failed_only",
  cron: "0 9 * * *",
  period: "daily" as "daily" | "weekly",
  weekdays: [1] as number[],
  run_time: "09:00",
  is_active: true,
});
const weekdayOptions = [
  { label: "一", value: 1 },
  { label: "二", value: 2 },
  { label: "三", value: 3 },
  { label: "四", value: 4 },
  { label: "五", value: 5 },
  { label: "六", value: 6 },
  { label: "日", value: 7 },
];

const filteredSchedules = computed(() => schedules.value.filter((item) => {
  const text = `${item.name} ${item.suite_name} ${item.cron}`.toLowerCase();
  const statusMatched = !statusFilter.value || String(item.is_active) === statusFilter.value;
  return statusMatched && (!keyword.value || text.includes(keyword.value.toLowerCase()));
}));

const statusBadge = (status?: string) => {
  if (status === "success" || status === "completed" || status === "passed") return "badge-success";
  if (status === "failed") return "badge-danger";
  if (status === "running" || status === "pending") return "badge-warning";
  return "badge-gray";
};

const lastStatusText = (status?: string) => ({
  success: "成功",
  failed: "失败",
  running: "执行中",
  pending: "待执行",
  completed: "完成",
  passed: "通过",
}[status || ""] || "-");

const formatDateTime = (value?: string) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).replace("T", " ").slice(0, 19);
  const pad = (item: number) => String(item).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
};

const loadSchedules = async (showLoading = true) => {
  if (showLoading) loading.value = true;
  try {
    const scheduleResp = await platformApi.scheduledPlans();
    schedules.value = unwrapList<ScheduledPlan>(scheduleResp.data);
  } finally {
    if (showLoading) loading.value = false;
  }
};

const ensureOptions = async () => {
  if (suites.value.length && environments.value.length && notifications.value.length && notificationTemplates.value.length) return;
  const [suiteData, envData, notificationResp, templateResp] = await Promise.all([
    platformApi.cachedApiSuites(),
    platformApi.cachedEnvironments(),
    platformApi.notificationChannels({ is_active: true }),
    platformApi.notificationTemplates({ is_active: true, biz_type: "schedule_run" }),
  ]);
  suites.value = unwrapList<ApiSuite>(suiteData as any).filter((item) => item.is_active !== false);
  environments.value = unwrapList<Environment>(envData as any);
  notifications.value = unwrapList<NotificationChannel>(notificationResp.data).filter((item) => item.is_active !== false);
  notificationTemplates.value = unwrapList<NotificationTemplate>(templateResp.data).filter((item) => item.is_active !== false);
};

const availableNotificationTemplates = computed(() => notificationTemplates.value.filter((item) => {
  return !form.notifications.length || !item.channel || form.notifications.includes(item.channel);
}));

const loadPage = async () => {
  loading.value = true;
  try {
    await Promise.all([loadSchedules(false), ensureOptions()]);
  } finally {
    loading.value = false;
  }
};

const parseCronToPeriod = (cron?: string) => {
  const fields = (cron || "0 9 * * *").trim().split(/\s+/);
  if (fields.length !== 5) return { period: "daily" as const, weekdays: [1], run_time: "09:00", cron: "0 9 * * *" };
  const [minute, hour, , , weekday] = fields;
  const runTime = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
  if (weekday === "*") return { period: "daily" as const, weekdays: [1], run_time: runTime, cron: fields.join(" ") };
  const weekdays = weekday
    .split(",")
    .map((item) => Number(item))
    .filter((item) => item >= 1 && item <= 7);
  return { period: "weekly" as const, weekdays: weekdays.length ? weekdays : [1], run_time: runTime, cron: fields.join(" ") };
};

const syncCronFromPeriod = () => {
  const [hour = "09", minute = "00"] = (form.run_time || "09:00").split(":");
  const dayField = form.period === "weekly" ? [...form.weekdays].sort().join(",") || "1" : "*";
  form.cron = `${Number(minute)} ${Number(hour)} * * ${dayField}`;
};

const openDialog = async (row?: ScheduledPlan) => {
  await ensureOptions();
  const suite = suites.value.find((item) => item.id === row?.suite) || suites.value[0];
  const scheduleConfig = parseCronToPeriod(row?.cron);
  Object.assign(form, {
    id: row?.id,
    name: row?.name || (suite?.name ? `定时执行-${suite.name}` : ""),
    suite: row?.suite || suite?.id,
    environment: row?.environment || suite?.run_config?.environment || environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id,
    notifications: [...(row?.notifications || [])],
    notification_template: row?.notification_template || notificationTemplates.value[0]?.id,
    notify_on: row?.notify_on || "disabled",
    cron: scheduleConfig.cron,
    period: scheduleConfig.period,
    weekdays: scheduleConfig.weekdays,
    run_time: scheduleConfig.run_time,
    is_active: row?.is_active ?? true,
  });
  dialogVisible.value = true;
};

const onSuiteChange = () => {
  const suite = suites.value.find((item) => item.id === form.suite);
  if (!form.name.trim() && suite?.name) form.name = `定时执行-${suite.name}`;
  form.environment = suite?.run_config?.environment || environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id;
};

const save = async () => {
  syncCronFromPeriod();
  if (!form.name.trim() || !form.suite || !form.environment || !form.cron.trim()) {
    ElMessage.warning("请填写任务名称、测试套件、运行环境和运行周期");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      name: form.name.trim(),
      suite: form.suite,
      environment: form.environment,
      notifications: form.notifications,
      notification_template: form.notification_template || null,
      notify_on: form.notify_on,
      cron: form.cron.trim(),
      is_active: form.is_active,
    };
    if (form.id) await platformApi.updateScheduledPlan(form.id, payload);
    else await platformApi.createScheduledPlan(payload);
    ElMessage.success("调度任务已保存");
    dialogVisible.value = false;
    await loadSchedules();
  } finally {
    saving.value = false;
  }
};

const toggle = async (row: ScheduledPlan) => {
  await platformApi.toggleScheduledPlan(row.id);
  ElMessage.success(row.is_active ? "调度任务已停用" : "调度任务已启用");
  await loadSchedules();
};

const runNow = async (row: ScheduledPlan) => {
  runningId.value = row.id;
  try {
    await platformApi.runScheduledPlanNow(row.id);
    ElMessage.success("已创建调度执行任务");
    await loadSchedules();
  } finally {
    runningId.value = undefined;
  }
};

const deleteSchedule = async (row: ScheduledPlan) => {
  await ElMessageBox.confirm(`确认删除调度任务「${row.name}」？`, "删除确认", { type: "warning" });
  await platformApi.deleteScheduledPlan(row.id);
  ElMessage.success("调度任务已删除");
  await loadSchedules();
};

onMounted(loadPage);
</script>


