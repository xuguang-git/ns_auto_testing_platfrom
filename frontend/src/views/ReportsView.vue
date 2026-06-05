<template>
  <div class="report-layout">
    <aside class="report-list-panel">
      <div class="report-list-header">
        <strong>报告列表</strong>
        <span>共 {{ runs.length }} 份</span>
      </div>
      <el-input v-model="keyword" placeholder="搜索报告编号" clearable class="report-search" />
      <button v-for="run in filteredRuns" :key="run.id" class="report-item" :class="{ active: selectedRun?.id === run.id }" @click="selectedRun = run">
        <div class="report-item-head">
          <strong>#{{ run.id }}</strong>
          <span>{{ run.status }}</span>
        </div>
        <div class="report-item-time">{{ run.created_at }}</div>
        <el-progress :percentage="run.summary?.pass_rate || 0" :show-text="false" />
        <div class="report-item-stats">通过 {{ run.summary?.passed || 0 }} / 失败 {{ run.summary?.failed || 0 }} / 总数 {{ run.summary?.total || 0 }}</div>
      </button>
    </aside>

    <section class="report-detail" v-if="selectedRun">
      <div class="report-header-card">
        <div>
          <h2>执行报告 #{{ selectedRun.id }}</h2>
          <p>状态：{{ selectedRun.status }} · 触发方式：{{ selectedRun.trigger_type }} · 耗时：{{ selectedRun.duration_ms || 0 }}ms</p>
        </div>
        <div class="pass-circle">{{ selectedRun.summary?.pass_rate || 0 }}%</div>
      </div>
      <div class="stats-row">
        <div><strong>{{ selectedRun.summary?.total || 0 }}</strong><span>总数</span></div>
        <div><strong>{{ selectedRun.summary?.passed || 0 }}</strong><span>通过</span></div>
        <div><strong>{{ selectedRun.summary?.failed || 0 }}</strong><span>失败</span></div>
        <div><strong>{{ selectedRun.summary?.skipped || 0 }}</strong><span>跳过</span></div>
      </div>
      <el-card shadow="never" style="margin-top: 14px">
        <template #header>
          <div class="card-header">
            <span>步骤详情</span>
            <el-link :href="`/api/v1/test-runs/${selectedRun.id}/html-report/`" target="_blank">导出 HTML</el-link>
          </div>
        </template>
        <el-table :data="selectedRun.steps || []" stripe>
          <el-table-column prop="sort_order" label="#" width="70" />
          <el-table-column prop="scenario_name" label="场景" />
          <el-table-column prop="step_name" label="步骤" />
          <el-table-column prop="status" label="状态" width="110" />
          <el-table-column prop="duration_ms" label="耗时(ms)" width="120" />
          <el-table-column prop="error_message" label="错误" />
        </el-table>
      </el-card>
    </section>
    <el-empty v-else description="暂无报告" style="flex: 1" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";

const loading = ref(false);
const keyword = ref("");
const runs = ref<any[]>([]);
const selectedRun = ref<any>();

const filteredRuns = computed(() => runs.value.filter((run) => !keyword.value || String(run.id).includes(keyword.value)));

onMounted(async () => {
  loading.value = true;
  try {
    const { data } = await platformApi.testRuns();
    runs.value = unwrapList(data);
    selectedRun.value = runs.value[0];
  } finally {
    loading.value = false;
  }
});
</script>
