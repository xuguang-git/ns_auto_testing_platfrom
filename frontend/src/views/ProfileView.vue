<template>
  <div class="v11-page">
    <div class="v11-topbar"><div><h2>个人中心</h2><span>维护个人资料和密码</span></div></div>
    <div class="v11-content profile-grid">
      <div class="info-card">
        <h3>个人资料</h3>
        <el-form label-width="92px">
          <el-form-item label="用户名"><el-input :model-value="auth.user?.username" disabled /></el-form-item>
          <el-form-item label="昵称"><el-input v-model="profile.nickname" /></el-form-item>
          <el-form-item label="邮箱"><el-input v-model="profile.email" /></el-form-item>
          <el-form-item label="手机号"><el-input v-model="profile.phone" /></el-form-item>
          <el-form-item label="角色"><el-input :model-value="auth.user?.role_name" disabled /></el-form-item>
          <el-button type="primary" @click="saveProfile">保存资料</el-button>
        </el-form>
      </div>
      <div class="info-card">
        <h3>修改密码</h3>
        <el-form label-width="92px">
          <el-form-item label="当前密码"><el-input v-model="password.current_password" type="password" show-password /></el-form-item>
          <el-form-item label="新密码"><el-input v-model="password.new_password" type="password" show-password /></el-form-item>
          <el-form-item label="确认密码"><el-input v-model="password.confirm_password" type="password" show-password /></el-form-item>
          <el-button type="primary" @click="changePassword">修改密码</el-button>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive } from "vue";

import { accountApi } from "@/api/account";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const profile = reactive({ nickname: "", email: "", phone: "" });
const password = reactive({ current_password: "", new_password: "", confirm_password: "" });

const sync = () => {
  profile.nickname = auth.user?.nickname || "";
  profile.email = auth.user?.email || "";
  profile.phone = auth.user?.phone || "";
};
const saveProfile = async () => {
  await accountApi.updateProfile(profile);
  await auth.loadMe();
  sync();
  ElMessage.success("资料已更新");
};
const changePassword = async () => {
  await accountApi.changePassword(password);
  ElMessage.success("密码已修改，请重新登录");
  await auth.logout();
  location.href = "/login";
};
onMounted(async () => {
  if (!auth.user) await auth.loadMe();
  sync();
});
</script>
