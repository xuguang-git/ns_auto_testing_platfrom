<template>
  <div class="template-page">
    <PageHeader title="消息模板" description="维护测试执行结果的推送标题和内容，变量由后端统一控制。" />

    <section class="template-toolbar">
      <el-select v-model="statusFilter" clearable placeholder="状态" style="width: 130px">
        <el-option label="启用" value="true" />
        <el-option label="停用" value="false" />
      </el-select>
      <el-button @click="loadTemplates">刷新</el-button>
      <el-button type="primary" @click="openDialog()">新增模板</el-button>
    </section>

    <section class="template-card">
      <el-table :data="filteredTemplates" v-loading="loading" stripe height="100%">
        <el-table-column prop="name" label="模板名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="适用业务" width="150">
          <template #default="{ row }">{{ bizTypeText(row.biz_type) }}</template>
        </el-table-column>
        <el-table-column prop="channel_name" label="消息通知" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.channel_name || "-" }}</template>
        </el-table-column>
        <el-table-column prop="title_template" label="标题模板" min-width="260" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span class="badge" :class="row.is_active ? 'badge-success' : 'badge-gray'">{{ row.is_active ? "启用" : "停用" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link class="danger-link" @click="deleteTemplate(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑消息模板' : '新增消息模板'" width="920px">
      <div class="template-dialog">
        <el-form :model="form" label-width="96px" class="template-form">
          <el-form-item label="模板名称" required>
            <el-input v-model="form.name" maxlength="64" show-word-limit placeholder="请输入模板名称" />
          </el-form-item>
          <el-form-item label="适用业务" required>
            <el-select v-model="form.biz_type" style="width: 100%">
              <el-option label="定时任务执行结果" value="schedule_run" />
            </el-select>
          </el-form-item>
          <el-form-item label="消息通知" required>
            <el-select v-model="form.channel" filterable clearable style="width: 100%" placeholder="请选择消息通知">
              <el-option
                v-for="item in channels"
                :key="item.id"
                :label="`${item.name}（${item.push_platform_display || item.push_platform}）`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="标题模板" required>
            <el-input
              ref="titleInput"
              v-model="form.title_template"
              maxlength="160"
              show-word-limit
              placeholder="例如：{{suite_name}} 执行{{status_text}}"
              @focus="activeEditor = 'title'"
            />
          </el-form-item>
          <el-form-item label="内容模板" required>
            <div class="rich-editor">
              <div class="rich-toolbar">
                <button type="button" @click="execContent('bold')">B</button>
                <button type="button" @click="execContent('italic')">I</button>
                <button type="button" @click="execContent('underline')">U</button>
                <button type="button" @click="execContent('insertUnorderedList')">列表</button>
                <button type="button" @click="execContent('removeFormat')">清除格式</button>
              </div>
              <div
                ref="contentEditor"
                class="rich-body"
                contenteditable="true"
                @focus="activeEditor = 'content'"
                @input="syncContent"
              ></div>
            </div>
          </el-form-item>
          <el-form-item label="状态">
            <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
          </el-form-item>
        </el-form>
        <aside class="variable-panel">
          <div class="variable-title">模板变量</div>
          <button v-for="(label, key) in variables" :key="key" class="variable-item" @click="insertVariable(String(key))">
            <span>{{ label }}</span>
            <code>{{ variableText(String(key)) }}</code>
          </button>
        </aside>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, nextTick, onMounted, reactive, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";
import PageHeader from "@/components/PageHeader.vue";

interface NotificationChannel {
  id: number;
  name: string;
  push_platform: string;
  push_platform_display?: string;
  is_active: boolean;
}

interface NotificationTemplate {
  id: number;
  name: string;
  biz_type: "schedule_run";
  channel: number | null;
  channel_name?: string;
  channel_platform?: string;
  title_template: string;
  content_template: string;
  is_active: boolean;
}

const loading = ref(false);
const saving = ref(false);
const dialogVisible = ref(false);
const statusFilter = ref("");
const templates = ref<NotificationTemplate[]>([]);
const channels = ref<NotificationChannel[]>([]);
const variables = ref<Record<string, string>>({});
const titleInput = ref();
const contentEditor = ref<HTMLElement>();
const activeEditor = ref<"title" | "content">("content");
const form = reactive({
  id: undefined as number | undefined,
  name: "",
  biz_type: "schedule_run" as const,
  channel: undefined as number | undefined,
  title_template: "",
  content_template: "",
  is_active: true,
});

const filteredTemplates = computed(() => templates.value.filter((item) => {
  return !statusFilter.value || String(item.is_active) === statusFilter.value;
}));

const bizTypeText = (value: string) => ({ schedule_run: "定时任务执行结果" }[value] || value);
const variableText = (key: string) => `{{${key}}}`;

const loadTemplates = async () => {
  loading.value = true;
  try {
    const resp = await platformApi.notificationTemplates();
    templates.value = unwrapList<NotificationTemplate>(resp.data);
  } finally {
    loading.value = false;
  }
};

const loadVariables = async () => {
  const resp = await platformApi.notificationTemplateVariables();
  variables.value = resp.data;
};

const loadChannels = async () => {
  const resp = await platformApi.notificationChannels({ is_active: true });
  channels.value = unwrapList<NotificationChannel>(resp.data);
};

const openDialog = async (row?: NotificationTemplate) => {
  Object.assign(form, {
    id: row?.id,
    name: row?.name || "",
    biz_type: row?.biz_type || "schedule_run",
    channel: row?.channel || undefined,
    title_template: row?.title_template || "",
    content_template: row?.content_template || "",
    is_active: row?.is_active ?? true,
  });
  dialogVisible.value = true;
  await nextTick();
  if (contentEditor.value) contentEditor.value.innerHTML = form.content_template;
};

const syncContent = () => {
  form.content_template = contentEditor.value?.innerHTML || "";
};

const execContent = (command: string) => {
  activeEditor.value = "content";
  contentEditor.value?.focus();
  document.execCommand(command);
  syncContent();
};

const insertVariable = (key: string) => {
  if (activeEditor.value === "title") {
    insertTitleVariable(key);
    return;
  }
  contentEditor.value?.focus();
  document.execCommand("insertText", false, variableText(key));
  syncContent();
};

const insertTitleVariable = (key: string) => {
  const input = titleInput.value?.input as HTMLInputElement | undefined;
  const text = variableText(key);
  const start = input?.selectionStart ?? form.title_template.length;
  const end = input?.selectionEnd ?? form.title_template.length;
  form.title_template = `${form.title_template.slice(0, start)}${text}${form.title_template.slice(end)}`;
  nextTick(() => {
    input?.focus();
    input?.setSelectionRange(start + text.length, start + text.length);
  });
};

const save = async () => {
  syncContent();
  if (!form.name.trim() || !form.title_template.trim() || !stripHtml(form.content_template) || !form.channel) {
    ElMessage.warning("请填写模板名称、消息通知、标题模板和内容模板");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      name: form.name.trim(),
      biz_type: form.biz_type,
      channel: form.channel,
      title_template: form.title_template.trim(),
      content_template: form.content_template.trim(),
      is_active: form.is_active,
    };
    if (form.id) await platformApi.updateNotificationTemplate(form.id, payload);
    else await platformApi.createNotificationTemplate(payload);
    ElMessage.success("消息模板已保存");
    dialogVisible.value = false;
    await loadTemplates();
  } finally {
    saving.value = false;
  }
};

const deleteTemplate = async (row: NotificationTemplate) => {
  await ElMessageBox.confirm(`确认删除消息模板“${row.name}”？`, "删除确认", { type: "warning" });
  await platformApi.deleteNotificationTemplate(row.id);
  ElMessage.success("消息模板已删除");
  await loadTemplates();
};

const stripHtml = (value: string) => value.replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").trim();

onMounted(async () => {
  await Promise.all([loadTemplates(), loadVariables(), loadChannels()]);
});
</script>

<style scoped>
.template-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.template-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.template-card {
  min-height: 0;
  flex: 1;
  padding: 16px;
  border: 1px solid #dbe3ef;
  border-radius: 14px;
  background: #fff;
}

.template-dialog {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 220px;
  gap: 16px;
}

.template-form {
  min-width: 0;
}

.rich-editor {
  width: 100%;
  min-width: 0;
  border: 1px solid #d8e0ec;
  border-radius: 8px;
  background: #fff;
  resize: vertical;
  overflow: auto;
}

.rich-toolbar {
  display: flex;
  gap: 6px;
  padding: 8px;
  border-bottom: 1px solid #edf1f7;
  background: #f8fafc;
}

.rich-toolbar button {
  min-width: 30px;
  height: 28px;
  border: 1px solid #d8e0ec;
  border-radius: 6px;
  background: #fff;
  color: #243b63;
  cursor: pointer;
}

.rich-body {
  min-height: 220px;
  max-height: 420px;
  overflow: auto;
  padding: 12px;
  outline: none;
  line-height: 1.7;
  color: #17233d;
}

.variable-panel {
  max-height: 540px;
  overflow: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  background: #f8fafc;
}

.variable-title {
  margin-bottom: 8px;
  font-weight: 700;
  color: #243b63;
}

.variable-item {
  width: 100%;
  border: 0;
  border-radius: 6px;
  background: transparent;
  padding: 7px 6px;
  text-align: left;
  cursor: pointer;
}

.variable-item:hover {
  background: #eef3ff;
}

.variable-item span,
.variable-item code {
  display: block;
}

.variable-item code {
  color: #5b6cff;
}
</style>
