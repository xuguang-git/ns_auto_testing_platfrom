<template>
  <div class="v11-page">
    <div class="v11-topbar">
      <div><h2>审计日志</h2><span>查看登录、用户、角色和业务写操作记录</span></div>
      <el-button @click="load">刷新</el-button>
    </div>
    <div class="v11-content">
      <div class="user-filter-bar">
        <el-input v-model="keyword" placeholder="搜索操作人/内容" clearable @change="load" />
        <el-select v-model="actionType" placeholder="全部类型" clearable @change="load">
          <el-option v-for="item in actionOptions" :key="item" :label="item" :value="item" />
        </el-select>
        <el-input v-model="moduleName" placeholder="模块" clearable @change="load" />
      </div>
      <div class="table-card">
        <el-table :data="logs" v-loading="loading" stripe>
          <el-table-column prop="created_at" label="时间" width="180" />
          <el-table-column prop="username" label="操作人" width="130" />
          <el-table-column prop="action_type" label="类型" width="110" />
          <el-table-column prop="module" label="模块" width="120" />
          <el-table-column prop="summary" label="操作内容" min-width="260" />
          <el-table-column prop="ip_address" label="IP" width="140" />
          <el-table-column label="结果" width="90"><template #default="{ row }"><span class="badge" :class="row.success ? 'badge-success' : 'badge-danger'">{{ row.success ? "成功" : "失败" }}</span></template></el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

import { accountApi } from "@/api/account";
import { unwrapList } from "@/api/platform";

const loading = ref(false);
const logs = ref<any[]>([]);
const keyword = ref("");
const actionType = ref("");
const moduleName = ref("");
const actionOptions = ["login", "logout", "create", "update", "delete", "enable", "disable", "reset_password", "force_logout", "export"];

const load = async () => {
  loading.value = true;
  try {
    const { data } = await accountApi.auditLogs({ search: keyword.value || undefined, action_type: actionType.value || undefined, module: moduleName.value || undefined });
    logs.value = unwrapList(data);
  } finally {
    loading.value = false;
  }
};
onMounted(load);
</script>
