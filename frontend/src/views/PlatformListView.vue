<template>
  <div class="v11-page">
    <div class="v11-topbar">
      <div>
        <h2>平台维护</h2>
        <span>管理测试平台列表，支持级联删除确认</span>
      </div>
      <el-button type="primary" @click="openCreate">+ 新增平台</el-button>
    </div>

    <div class="v11-content">
      <div class="table-card">
        <el-table :data="platforms" v-loading="loading" stripe>
          <el-table-column prop="name" label="平台名称" min-width="160" />
          <el-table-column prop="code" label="编码" width="130">
            <template #default="{ row }"><code class="inline-code">{{ row.code }}</code></template>
          </el-table-column>
          <el-table-column prop="module_count" label="模块数" width="100" />
          <el-table-column prop="api_count" label="接口数" width="100" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <span class="badge" :class="row.is_active ? 'badge-success' : 'badge-gray'">{{ row.is_active ? "启用" : "已停用" }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="created_by_name" label="创建人" width="120" show-overflow-tooltip />
          <el-table-column prop="updated_by_name" label="最后修改人" width="130" show-overflow-tooltip />
          <el-table-column prop="sort_order" label="排序" width="90" />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button link class="danger-link" @click="openDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog v-model="formVisible" :title="editingId ? '编辑平台' : '新增平台'" width="520px">
      <el-form :model="form" label-width="92px">
        <el-alert v-if="!editingId" type="info" :closable="false" show-icon class="form-tip">
          创建平台后，系统会自动初始化一个“未分配”模块，用于暂存尚未分类的接口。
        </el-alert>
        <el-form-item label="平台名称" required><el-input v-model="form.name" placeholder="如：ERP、WMS" /></el-form-item>
        <el-form-item label="平台编码" required>
          <el-input v-model="form.code" :disabled="!!editingId" placeholder="如：erp" />
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort_order" :min="0" :max="999" /></el-form-item>
        <el-form-item label="启用状态"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePlatform">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="deleteVisible" title="确认删除平台" width="560px">
      <div v-if="deleteTarget" class="cascade-box">
        <p>即将删除 <b>{{ deleteTarget.name }}</b>，此操作不可撤销。</p>
        <div class="cascade-tree">
          <div>{{ deleteTarget.name }} 平台</div>
          <div>↳ 关联模块：{{ deleteTarget.module_count || 0 }} 个</div>
          <div>↳ 模块下接口：{{ deleteTarget.api_count || 0 }} 个</div>
        </div>
        <p class="cascade-note">历史执行记录和测试报告将保留。</p>
        <el-input v-model="deleteConfirm" :placeholder="`输入 ${deleteTarget.code} 确认删除`" />
      </div>
      <template #footer>
        <el-button @click="deleteVisible = false">取消</el-button>
        <el-button type="danger" :disabled="deleteConfirm !== deleteTarget?.code" @click="deletePlatform">确认删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";

const loading = ref(false);
const saving = ref(false);
const formVisible = ref(false);
const deleteVisible = ref(false);
const editingId = ref<number>();
const platforms = ref<any[]>([]);
const deleteTarget = ref<any>();
const deleteConfirm = ref("");
const form = reactive({ name: "", code: "", description: "", sort_order: 0, is_active: true });

const load = async () => {
  loading.value = true;
  try {
    const { data } = await platformApi.platforms();
    platforms.value = unwrapList(data);
  } finally {
    loading.value = false;
  }
};

const openCreate = () => {
  editingId.value = undefined;
  Object.assign(form, { name: "", code: "", description: "", sort_order: platforms.value.length + 1, is_active: true });
  formVisible.value = true;
};

const openEdit = (row: any) => {
  editingId.value = row.id;
  Object.assign(form, {
    name: row.name,
    code: row.code,
    description: row.description || "",
    sort_order: row.sort_order || 0,
    is_active: row.is_active,
  });
  formVisible.value = true;
};

const savePlatform = async () => {
  if (!form.name.trim() || !form.code.trim()) {
    ElMessage.warning("平台名称和编码必填");
    return;
  }
  saving.value = true;
  try {
    if (editingId.value) await platformApi.updatePlatform(editingId.value, form);
    else await platformApi.createPlatform(form);
    ElMessage.success("平台已保存");
    formVisible.value = false;
    await load();
  } finally {
    saving.value = false;
  }
};

const openDelete = (row: any) => {
  deleteTarget.value = row;
  deleteConfirm.value = "";
  deleteVisible.value = true;
};

const deletePlatform = async () => {
  if (!deleteTarget.value) return;
  await platformApi.deletePlatform(deleteTarget.value.id);
  ElMessage.success("平台已删除");
  deleteVisible.value = false;
  await load();
};

onMounted(load);
</script>
