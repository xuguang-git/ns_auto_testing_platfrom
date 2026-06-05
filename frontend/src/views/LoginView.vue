<template>
  <div class="login-page">
    <section class="login-brand">
      <img src="/system-icon.jpg" alt="NS" />
      <h1>NS-ATP</h1>
      <p>自动化测试平台</p>
    </section>
    <section class="login-panel">
      <div class="login-card">
        <h2>登录</h2>
        <p>使用平台账号进入工作台</p>
        <el-form :model="form" @keyup.enter="submit">
          <el-form-item>
            <el-input v-model="form.username" size="large" placeholder="用户名" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="form.password" size="large" type="password" show-password placeholder="密码" />
          </el-form-item>
          <div class="login-options">
            <el-checkbox v-model="form.remember_me">记住登录</el-checkbox>
          </div>
          <el-button type="primary" size="large" :loading="loading" class="login-submit" @click="submit">登录</el-button>
        </el-form>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const loading = ref(false);
const form = reactive({ username: "admin", password: "", remember_me: true });

const submit = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning("请输入用户名和密码");
    return;
  }
  loading.value = true;
  try {
    await auth.login(form);
    await router.push((route.query.redirect as string) || "/dashboard");
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.non_field_errors?.[0] || error?.response?.data?.detail || "登录失败");
  } finally {
    loading.value = false;
  }
};
</script>
