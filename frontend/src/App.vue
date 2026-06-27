<template>
  <RouterView v-slot="{ Component }">
    <div v-if="pageError" v-mojibake class="app-error-state">
      <h1>页面加载失败</h1>
      <p>{{ pageError }}</p>
      <div>
        <button type="button" @click="reloadPage">刷新</button>
        <button type="button" @click="goHome">返回首页</button>
      </div>
    </div>
    <component :is="Component" v-else-if="Component" />
    <div v-else class="app-route-loading">页面加载中...</div>
  </RouterView>
</template>

<script setup lang="ts">
import { onErrorCaptured, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const pageError = ref("");

const isExpectedInteractionError = (error: unknown) => {
  const value = error as any;
  const message = error instanceof Error ? error.message : String(error || "");
  if (["cancel", "close"].includes(message)) return true;
  if (value?.name === "CanceledError" || value?.code === "ERR_CANCELED") return true;
  if (value?.isAxiosError || value?.response || value?.businessCode) return true;
  return false;
};

onErrorCaptured((error) => {
  // 用户取消弹窗、关闭弹窗、接口业务失败都属于可预期交互，不应触发整页失败态。
  if (isExpectedInteractionError(error)) return false;
  pageError.value = error instanceof Error ? error.message : "页面运行异常";
  return false;
});

router.afterEach(() => {
  pageError.value = "";
});

const reloadPage = () => {
  window.location.reload();
};

const goHome = async () => {
  await router.push("/dashboard");
};
</script>

