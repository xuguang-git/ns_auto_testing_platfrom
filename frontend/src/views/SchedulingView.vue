<template>
  <div>
    <PageHeader title="调度计划" description="第一版预留定时调度入口，后续接入 Celery Beat、Webhook 和通知。" />
    <el-card shadow="never">
      <el-empty description="调度能力将在后续版本实现，当前已预留后端模型和菜单入口。" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import PageHeader from "@/components/PageHeader.vue";
</script>
