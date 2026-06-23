<template>
  <div class="notification-page">
    <PageHeader title="消息通知" description="维护测试通知通道，Webhook 与签名信息按敏感配置处理。" />

    <section class="notification-toolbar">
      <el-select v-model="typeFilter" clearable placeholder="通知类型" style="width: 150px">
        <el-option label="接口测试" value="api_testing" />
        <el-option label="UI测试" value="ui_testing" />
      </el-select>
      <el-select v-model="platformFilter" clearable placeholder="推送平台" style="width: 150px">
        <el-option label="飞书" value="feishu" />
        <el-option label="企业微信" value="wechat_work" />
        <el-option label="钉钉" value="dingtalk" />
      </el-select>
      <el-select v-model="statusFilter" clearable placeholder="状态" style="width: 130px">
        <el-option label="启用" value="true" />
        <el-option label="停用" value="false" />
      </el-select>
      <el-button @click="loadNotifications">刷新</el-button>
      <el-button type="primary" @click="openDialog()">新增通知</el-button>
    </section>

    <section class="notification-card">
      <el-table :data="filteredNotifications" v-loading="loading" stripe height="100%">
        <el-table-column prop="name" label="通知名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="notification_type_display" label="通知类型" min-width="120" />
        <el-table-column prop="push_platform_display" label="推送平台" min-width="120" />
        <el-table-column prop="webhook_mask" label="Webhook" min-width="240" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <span class="badge" :class="row.is_active ? 'badge-success' : 'badge-gray'">{{ row.is_active ? "启用" : "停用" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="关联任务合计" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="openPlanDialog(row)">{{ row.scheduled_plan_count || 0 }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" min-width="170" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openLogDialog(row)">日志</el-button>
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link class="danger-link" @click="deleteNotification(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" :title="form.id ? '修改通知' : '新增通知'" width="620px">
      <el-form :model="form" label-width="104px">
        <el-form-item label="通知名称" required>
          <el-input v-model="form.name" maxlength="64" show-word-limit placeholder="请输入通知名称" />
        </el-form-item>
        <el-form-item label="通知类型" required>
          <el-radio-group v-model="form.notification_type">
            <el-radio-button label="api_testing">接口测试</el-radio-button>
            <el-radio-button label="ui_testing">UI测试</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="推送平台" required>
          <el-radio-group v-model="form.push_platform" @change="onPlatformChange">
            <el-radio-button label="feishu">飞书</el-radio-button>
            <el-radio-button label="wechat_work">企业微信</el-radio-button>
            <el-radio-button label="dingtalk">钉钉</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="Webhook" :required="!form.id">
          <el-input
            v-model="form.webhook"
            type="password"
            show-password
            :placeholder="form.id ? `当前：${form.webhook_mask || '已保存'}，留空表示不修改` : '请输入机器人 Webhook'"
            clearable
          />
        </el-form-item>
        <el-form-item v-if="form.push_platform === 'feishu'" label="签名校验">
          <el-input
            v-model="form.signature"
            type="password"
            show-password
            :placeholder="form.id ? `当前：${form.signature_mask || '未配置'}，留空表示不修改，清空保存则删除` : '飞书签名校验，非必填'"
            clearable
          />
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

    <el-dialog v-model="planDialogVisible" title="关联定时任务" width="420px">
      <div class="notification-plan-list">
        <div v-if="!selectedPlans.length" class="empty-small">暂无关联任务</div>
        <div v-for="plan in selectedPlans" :key="plan.id" class="notification-plan-item">
          <span>{{ plan.name }}</span>
          <span>{{ plan.next_run_at || "-" }}</span>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="logDialogVisible" title="推送日志" width="760px">
      <el-table :data="sendLogs" v-loading="logLoading" height="360px" stripe>
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column prop="status" label="结果" width="90">
          <template #default="{ row }">
            <span class="badge" :class="row.status === 'success' ? 'badge-success' : row.status === 'skipped' ? 'badge-gray' : 'badge-danger'">
              {{ statusText(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="schedule_name" label="任务" min-width="140" show-overflow-tooltip />
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="error_message" label="失败原因" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.error_message || "" }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";
import PageHeader from "@/components/PageHeader.vue";

type NotificationType = "api_testing" | "ui_testing";
type PushPlatform = "feishu" | "wechat_work" | "dingtalk";

interface ScheduledPlanBrief {
  id: number;
  name: string;
  next_run_at?: string;
}

interface NotificationChannel {
  id: number;
  name: string;
  notification_type: NotificationType;
  notification_type_display: string;
  push_platform: PushPlatform;
  push_platform_display: string;
  webhook_mask: string;
  signature_mask?: string;
  is_active: boolean;
  scheduled_plan_count: number;
  scheduled_plans: ScheduledPlanBrief[];
  updated_at?: string;
}

interface NotificationSendLog {
  id: number;
  status: "success" | "failed" | "skipped";
  schedule_name?: string;
  title: string;
  error_message?: string;
  created_at?: string;
}

const loading = ref(false);
const saving = ref(false);
const dialogVisible = ref(false);
const planDialogVisible = ref(false);
const logDialogVisible = ref(false);
const logLoading = ref(false);
const typeFilter = ref("");
const platformFilter = ref("");
const statusFilter = ref("");
const notifications = ref<NotificationChannel[]>([]);
const selectedPlans = ref<ScheduledPlanBrief[]>([]);
const sendLogs = ref<NotificationSendLog[]>([]);
const form = reactive({
  id: undefined as number | undefined,
  name: "",
  notification_type: "api_testing" as NotificationType,
  push_platform: "feishu" as PushPlatform,
  webhook: "",
  webhook_mask: "",
  signature: "",
  signature_mask: "",
  is_active: true,
});

const filteredNotifications = computed(() => notifications.value.filter((item) => {
  const typeMatched = !typeFilter.value || item.notification_type === typeFilter.value;
  const platformMatched = !platformFilter.value || item.push_platform === platformFilter.value;
  const statusMatched = !statusFilter.value || String(item.is_active) === statusFilter.value;
  return typeMatched && platformMatched && statusMatched;
}));

const loadNotifications = async () => {
  loading.value = true;
  try {
    const resp = await platformApi.notificationChannels();
    notifications.value = unwrapList<NotificationChannel>(resp.data);
  } finally {
    loading.value = false;
  }
};

const openDialog = (row?: NotificationChannel) => {
  Object.assign(form, {
    id: row?.id,
    name: row?.name || "",
    notification_type: row?.notification_type || "api_testing",
    push_platform: row?.push_platform || "feishu",
    webhook: "",
    webhook_mask: row?.webhook_mask || "",
    signature: "",
    signature_mask: row?.signature_mask || "",
    is_active: row?.is_active ?? true,
  });
  dialogVisible.value = true;
};

const onPlatformChange = () => {
  if (form.push_platform !== "feishu") form.signature = "";
};

const save = async () => {
  if (!form.name.trim()) {
    ElMessage.warning("请填写通知名称");
    return;
  }
  if (!form.id && !form.webhook.trim()) {
    ElMessage.warning("请填写Webhook地址");
    return;
  }
  saving.value = true;
  try {
    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      notification_type: form.notification_type,
      push_platform: form.push_platform,
      is_active: form.is_active,
    };
    if (form.webhook.trim()) payload.webhook = form.webhook.trim();
    if (form.push_platform === "feishu" && form.signature.trim()) payload.signature = form.signature.trim();
    if (form.push_platform !== "feishu") payload.signature = "";
    if (form.id) await platformApi.updateNotificationChannel(form.id, payload);
    else await platformApi.createNotificationChannel(payload);
    ElMessage.success("消息通知已保存");
    dialogVisible.value = false;
    await loadNotifications();
  } finally {
    saving.value = false;
  }
};

const deleteNotification = async (row: NotificationChannel) => {
  await ElMessageBox.confirm("确认删除该消息通知？", "删除确认", { type: "warning" });
  await platformApi.deleteNotificationChannel(row.id);
  ElMessage.success("已删除消息通知");
  await loadNotifications();
};

const openPlanDialog = (row: NotificationChannel) => {
  selectedPlans.value = row.scheduled_plans || [];
  planDialogVisible.value = true;
};

const statusText = (status: NotificationSendLog["status"]) => ({
  success: "成功",
  failed: "失败",
  skipped: "跳过",
}[status] || status);

const openLogDialog = async (row: NotificationChannel) => {
  logDialogVisible.value = true;
  logLoading.value = true;
  try {
    const resp = await platformApi.notificationSendLogs({ channel: row.id, ordering: "-created_at" });
    sendLogs.value = unwrapList<NotificationSendLog>(resp.data);
  } finally {
    logLoading.value = false;
  }
};

onMounted(loadNotifications);
</script>

<style scoped>
.notification-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.notification-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.notification-card {
  min-height: 0;
  flex: 1;
  padding: 16px;
  border: 1px solid #dbe3ef;
  border-radius: 14px;
  background: #fff;
}

.notification-plan-list {
  height: 100px;
  overflow: auto;
  border: 1px solid #e3e8f2;
  border-radius: 8px;
}

.notification-plan-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 10px;
  color: #23395d;
}

.notification-plan-item + .notification-plan-item {
  border-top: 1px solid #eef2f8;
}

.empty-small {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #8a97ad;
}
</style>
