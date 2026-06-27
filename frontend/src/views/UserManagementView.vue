<template>
  <div class="v11-page">
    <div class="v11-topbar">
      <div><h2>用户管理</h2><span>维护平台用户、角色与账号状态</span></div>
      <el-button type="primary" @click="openCreate">新增用户</el-button>
    </div>
    <div class="v11-content">
      <div class="user-filter-bar">
        <el-input v-model="keyword" placeholder="搜索用户名/昵称/邮箱" clearable @change="load" />
        <el-select v-model="roleFilter" placeholder="全部角色" clearable @change="load">
          <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="全部状态" clearable @change="load">
          <el-option label="启用" value="active" />
          <el-option label="禁用" value="disabled" />
          <el-option label="锁定" value="locked" />
        </el-select>
        <el-button @click="load">刷新</el-button>
      </div>
      <div class="table-card">
        <el-table :data="users" v-loading="loading" stripe>
          <el-table-column label="用户" min-width="180">
            <template #default="{ row }">
              <div class="user-cell-mini">
                <span class="avatar-mini">{{ row.nickname?.[0] || row.username?.[0] }}</span>
                <div>
                  <b>{{ row.nickname || row.username }}</b>
                  <em>@{{ row.username }}</em>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="role_name" label="角色" width="130" />
          <el-table-column label="状态" width="100"><template #default="{ row }"><span class="badge" :class="row.status === 'active' ? 'badge-success' : 'badge-gray'">{{ statusText(row.status) }}</span></template></el-table-column>
          <el-table-column prop="email" label="邮箱" min-width="180" />
          <el-table-column prop="last_login" label="最后登录" width="180" />
          <el-table-column label="操作" width="260" fixed="right">
            <template #default="{ row }">
              <template v-if="!row.is_protected">
                <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
                <el-button link @click="openReset(row)">重置密码</el-button>
                <el-button v-if="row.status === 'active'" link class="danger-link" @click="disableUser(row)">禁用</el-button>
                <el-button v-else link type="primary" @click="enableUser(row)">启用</el-button>
                <el-button link @click="forceLogout(row)">强制下线</el-button>
              </template>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog v-model="formVisible" :title="editingId ? '编辑用户' : '新增用户'" width="620px">
      <el-form :model="form" label-width="92px">
        <el-form-item label="用户名" required><el-input v-model="form.username" :disabled="!!editingId" /></el-form-item>
        <el-form-item v-if="!editingId" label="初始密码" required><el-input v-model="form.password" type="password" show-password /></el-form-item>
        <el-form-item label="昵称" required><el-input v-model="form.nickname" /></el-form-item>
        <el-form-item label="角色" required><el-select v-model="form.role" :disabled="isEditingProtected" style="width:100%"><el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" /></el-select></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="form.enabled" :disabled="isEditingProtected" active-text="启用" inactive-text="禁用" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="formVisible=false">取消</el-button><el-button type="primary" :loading="saving" @click="saveUser">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="resetVisible" title="重置密码" width="420px">
      <el-form label-width="84px">
        <el-form-item label="新密码"><el-input v-model="resetPassword" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer><el-button @click="resetVisible=false">取消</el-button><el-button type="primary" @click="confirmReset">确认</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import { accountApi } from "@/api/account";
import { unwrapList } from "@/api/platform";

const loading = ref(false);
const saving = ref(false);
const users = ref<any[]>([]);
const roles = ref<any[]>([]);
const keyword = ref("");
const roleFilter = ref<number>();
const statusFilter = ref("");
const formVisible = ref(false);
const resetVisible = ref(false);
const editingId = ref<number>();
const isEditingProtected = ref(false);
const resetTarget = ref<any>();
const resetPassword = ref("Admin123@");
const form = reactive({ username: "", password: "Admin123@", nickname: "", role: undefined as number | undefined, email: "", phone: "", enabled: true });

const statusText = (status: string) => ({ active: "启用", disabled: "禁用", locked: "锁定" }[status] || status);
const load = async () => {
  loading.value = true;
  try {
    const [userResp, roleResp] = await Promise.all([
      accountApi.users({ keyword: keyword.value || undefined, profile__role: roleFilter.value, profile__status: statusFilter.value || undefined }),
      accountApi.roles(),
    ]);
    users.value = unwrapList(userResp.data);
    roles.value = unwrapList(roleResp.data);
  } finally {
    loading.value = false;
  }
};
const openCreate = () => {
  editingId.value = undefined;
  isEditingProtected.value = false;
  Object.assign(form, { username: "", password: "Admin123@", nickname: "", role: roles.value[0]?.id, email: "", phone: "", enabled: true });
  formVisible.value = true;
};
const openEdit = (row: any) => {
  if (row.is_protected) {
    return;
  }
  editingId.value = row.id;
  isEditingProtected.value = !!row.is_protected;
  Object.assign(form, { username: row.username, password: "", nickname: row.nickname, role: row.role, email: row.email, phone: row.phone, enabled: row.status === "active" });
  formVisible.value = true;
};
const saveUser = async () => {
  if (editingId.value && isEditingProtected.value) {
    return;
  }
  saving.value = true;
  try {
    const payload: any = { username: form.username, nickname: form.nickname, role: form.role, email: form.email, phone: form.phone, status: form.enabled ? "active" : "disabled", is_active: form.enabled };
    if (!editingId.value) payload.password = form.password;
    if (editingId.value) await accountApi.updateUser(editingId.value, payload);
    else await accountApi.createUser(payload);
    ElMessage.success("用户已保存");
    formVisible.value = false;
    await load();
  } finally {
    saving.value = false;
  }
};
const disableUser = async (row: any) => {
  if (row.is_protected) {
    return;
  }
  await ElMessageBox.confirm(`确认禁用用户 ${row.username}？`, "禁用确认", { type: "warning" });
  await accountApi.disableUser(row.id);
  await load();
};
const enableUser = async (row: any) => {
  if (row.is_protected) {
    return;
  }
  await accountApi.enableUser(row.id);
  await load();
};
const openReset = (row: any) => {
  if (row.is_protected) {
    return;
  }
  resetTarget.value = row;
  resetPassword.value = "Admin123@";
  resetVisible.value = true;
};
const confirmReset = async () => {
  await accountApi.resetPassword(resetTarget.value.id, { password: resetPassword.value, must_change_password: false });
  ElMessage.success("密码已重置");
  resetVisible.value = false;
};
const forceLogout = async (row: any) => {
  if (row.is_protected) {
    return;
  }
  await accountApi.forceLogout(row.id);
  ElMessage.success("已强制下线");
};

onMounted(load);
</script>
