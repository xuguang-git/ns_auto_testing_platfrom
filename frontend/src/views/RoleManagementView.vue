<template>
  <div class="v11-page">
    <div class="v11-topbar">
      <div><h2>角色管理</h2><span>维护角色与权限矩阵</span></div>
      <el-button type="primary" @click="openCreate">新增角色</el-button>
    </div>
    <div class="v11-content">
      <div class="table-card">
        <el-table :data="roles" v-loading="loading" stripe>
          <el-table-column prop="name" label="角色名称" min-width="150" />
          <el-table-column prop="code" label="编码" width="150" />
          <el-table-column prop="user_count" label="用户数" width="90" />
          <el-table-column label="类型" width="100"><template #default="{ row }"><span class="badge" :class="row.is_builtin ? 'badge-primary' : 'badge-gray'">{{ row.is_builtin ? "预置" : "自定义" }}</span></template></el-table-column>
          <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openEdit(row)">编辑权限</el-button>
              <el-button v-if="!row.is_builtin" link class="danger-link" @click="deleteRole(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog v-model="visible" :title="editingId ? '编辑角色' : '新增角色'" width="760px">
      <el-form :model="form" label-width="92px">
        <el-form-item label="角色名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="角色编码" required><el-input v-model="form.code" :disabled="!!editingId && editingBuiltin" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="权限">
          <el-checkbox-group v-model="form.permissions" class="permission-grid">
            <el-checkbox v-for="item in permissions" :key="item.id" :value="item.id">{{ item.name }} <small>{{ item.code }}</small></el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="visible=false">取消</el-button><el-button type="primary" @click="saveRole">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import { accountApi } from "@/api/account";
import { unwrapList } from "@/api/platform";

const loading = ref(false);
const roles = ref<any[]>([]);
const permissions = ref<any[]>([]);
const visible = ref(false);
const editingId = ref<number>();
const editingBuiltin = ref(false);
const form = reactive({ name: "", code: "", description: "", permissions: [] as number[] });

const load = async () => {
  loading.value = true;
  try {
    const [roleResp, permResp] = await Promise.all([accountApi.roles(), accountApi.permissions()]);
    roles.value = unwrapList(roleResp.data);
    permissions.value = unwrapList(permResp.data);
  } finally {
    loading.value = false;
  }
};
const openCreate = () => {
  editingId.value = undefined;
  editingBuiltin.value = false;
  Object.assign(form, { name: "", code: "", description: "", permissions: [] });
  visible.value = true;
};
const openEdit = (row: any) => {
  editingId.value = row.id;
  editingBuiltin.value = row.is_builtin;
  Object.assign(form, { name: row.name, code: row.code, description: row.description || "", permissions: row.permissions || [] });
  visible.value = true;
};
const saveRole = async () => {
  if (editingId.value) await accountApi.updateRole(editingId.value, form);
  else await accountApi.createRole(form);
  ElMessage.success("角色已保存");
  visible.value = false;
  await load();
};
const deleteRole = async (row: any) => {
  await ElMessageBox.confirm(`确认删除角色 ${row.name}？`, "删除确认", { type: "warning" });
  await accountApi.deleteRole(row.id);
  await load();
};
onMounted(load);
</script>
