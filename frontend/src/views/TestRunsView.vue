<template>
  <div class="test-runner-v11">
    <aside class="exec-sidebar">
      <div class="exec-header">
        <h3>执行配置</h3>
      </div>
      <div class="exec-body">
        <div class="plan-source-box">
          <div class="psb-label">执行来源 <span>v1.1</span></div>
          <el-radio-group v-model="sourceMode" class="exec-radio-group">
            <el-radio value="plan">测试计划</el-radio>
            <el-radio value="manual">手动选择</el-radio>
          </el-radio-group>
          <el-select v-model="selectedPlan" placeholder="请选择计划" class="exec-control" :disabled="sourceMode !== 'plan'" @change="applyPlanConfig">
            <el-option v-for="plan in plans" :key="plan.id" :label="plan.name" :value="plan.id" />
          </el-select>
        </div>

        <section class="exec-section">
          <span class="exec-label">执行平台</span>
          <el-select v-model="selectedPlatform" placeholder="选择平台" class="exec-control" @change="onPlatformChange">
            <el-option v-for="platform in platforms" :key="platform.id" :label="platform.name" :value="platform.id" />
          </el-select>
        </section>

        <section class="exec-section">
          <span class="exec-label">执行模块</span>
          <div class="module-check-list">
            <el-checkbox-group v-model="selectedModules">
              <el-checkbox v-for="module in availableModules" :key="module.id" :value="module.id">{{ module.name }} ({{ module.api_count || 0 }})</el-checkbox>
            </el-checkbox-group>
            <div v-if="!availableModules.length" class="module-empty">先选择计划或平台</div>
          </div>
        </section>

        <section class="exec-section">
          <span class="exec-label">执行环境</span>
          <el-select v-model="selectedEnvironment" placeholder="选择环境" class="exec-control">
            <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
          </el-select>
        </section>

        <section class="exec-section">
          <span class="exec-label">并发数 <b>{{ concurrency }}</b></span>
          <el-slider v-model="concurrency" :min="1" :max="10" />
        </section>

        <section class="exec-section">
          <el-checkbox v-model="retryEnabled">失败重试</el-checkbox>
          <el-select v-model="retryCount" class="exec-control retry-select" :disabled="!retryEnabled">
            <el-option :value="1" label="重试1次" />
            <el-option :value="2" label="重试2次" />
            <el-option :value="3" label="重试3次" />
          </el-select>
        </section>

        <button v-if="!running" class="exec-start" :disabled="!selectedPlan" @click="runSelectedPlan">开始执行</button>
        <button v-else class="exec-stop" @click="stopPolling">停止刷新</button>
      </div>
    </aside>

    <section class="runner-v11-main">
      <div class="runner-topbar">
        <div>
          <h2>执行中心</h2>
          <span>{{ runInfo }}</span>
        </div>
        <el-button @click="$router.push('/test-plans')">管理计划</el-button>
      </div>

      <div v-if="!selectedRun" class="run-empty-v11">
        <div class="empty-play">▶</div>
        <p>选择计划并配置参数后，点击“开始执行”</p>
        <el-button type="primary" :disabled="!plans.length" @click="quickLoadPlan">快速加载第一个计划</el-button>
      </div>

      <div v-else class="runner-content-v11">
        <section class="progress-card-v11">
          <div class="progress-card-head">
            <div>
              <h3>{{ activePlan?.name || planName(selectedRun.plan) }}</h3>
              <p>执行 #{{ selectedRun.id }} · {{ statusText(selectedRun.status) }} · {{ selectedRun.duration_ms || 0 }}ms</p>
            </div>
            <span class="pc-status" :class="statusClass(selectedRun.status)">
              <i v-if="selectedRun.status === 'running'" class="dot-running"></i>{{ statusText(selectedRun.status) }}
            </span>
          </div>
          <el-progress :percentage="progressPercent" :stroke-width="10" />
          <div class="pc-stats">
            <span>总数 <b>{{ total }}</b></span>
            <span>通过 <b class="success">{{ passed }}</b></span>
            <span>失败 <b class="danger">{{ failed }}</b></span>
            <span>跳过 <b>{{ skipped }}</b></span>
          </div>
        </section>

        <section class="result-card-v11">
          <div class="result-head">
            <h3>执行结果</h3>
            <el-link :href="`/api/v1/test-runs/${selectedRun.id}/html-report/`" target="_blank">导出 HTML</el-link>
          </div>
          <el-table :data="selectedRun.steps || []" stripe>
            <el-table-column prop="sort_order" label="#" width="60" />
            <el-table-column prop="scenario_name" label="场景" min-width="150" show-overflow-tooltip />
            <el-table-column prop="step_name" label="步骤" min-width="180" show-overflow-tooltip />
            <el-table-column label="状态" width="100">
              <template #default="{ row }"><span class="step-status" :class="statusClass(row.status)">{{ statusText(row.status) }}</span></template>
            </el-table-column>
            <el-table-column prop="duration_ms" label="耗时" width="100">
              <template #default="{ row }">{{ row.duration_ms || 0 }}ms</template>
            </el-table-column>
            <el-table-column prop="error_message" label="错误" min-width="220" show-overflow-tooltip />
          </el-table>
        </section>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { platformApi, unwrapList } from "@/api/platform";

const route = useRoute();
const sourceMode = ref<"plan" | "manual">("plan");
const plans = ref<any[]>([]);
const runs = ref<any[]>([]);
const platforms = ref<any[]>([]);
const modules = ref<any[]>([]);
const environments = ref<any[]>([]);
const selectedPlan = ref<number>();
const selectedPlatform = ref<number>();
const selectedModules = ref<number[]>([]);
const selectedEnvironment = ref<number>();
const selectedRun = ref<any>();
const concurrency = ref(3);
const retryEnabled = ref(true);
const retryCount = ref(1);
const running = ref(false);
const pollTimer = ref<number>();

const activePlan = computed(() => plans.value.find((item) => item.id === selectedPlan.value));
const availableModules = computed(() => modules.value.filter((item) => !selectedPlatform.value || item.managed_platform === selectedPlatform.value));
const summary = computed(() => selectedRun.value?.summary || {});
const total = computed(() => summary.value.total || selectedRun.value?.steps?.length || 0);
const passed = computed(() => summary.value.passed || countStepStatus("passed"));
const failed = computed(() => summary.value.failed || countStepStatus("failed"));
const skipped = computed(() => summary.value.skipped || countStepStatus("skipped"));
const done = computed(() => passed.value + failed.value + skipped.value);
const progressPercent = computed(() => (total.value ? Math.round((done.value / total.value) * 100) : 0));
const runInfo = computed(() => (activePlan.value ? `${activePlan.value.name} · ${availableModules.value.length} 个模块` : "尚未选择执行计划"));

const countStepStatus = (status: string) => (selectedRun.value?.steps || []).filter((step: any) => step.status === status).length;
const statusText = (status: string) => ({ pending: "待执行", running: "执行中", completed: "完成", failed: "失败", passed: "通过", skipped: "跳过" }[status] || status || "未知");
const statusClass = (status: string) => (status === "completed" || status === "passed" ? "success" : status === "failed" ? "danger" : status === "running" || status === "pending" ? "warning" : "muted");
const planName = (id: number) => plans.value.find((plan) => plan.id === id)?.name || `计划 ${id}`;

const applyPlanConfig = () => {
  if (!activePlan.value) return;
  selectedPlatform.value = activePlan.value.platform_ref || selectedPlatform.value;
  selectedModules.value = activePlan.value.module_ids || [];
  selectedEnvironment.value = activePlan.value.environment || selectedEnvironment.value;
  concurrency.value = activePlan.value.concurrency || concurrency.value;
  retryCount.value = activePlan.value.retry_count || retryCount.value;
};
const onPlatformChange = () => {
  selectedModules.value = availableModules.value.map((item) => item.id);
};
const quickLoadPlan = () => {
  selectedPlan.value = plans.value[0]?.id;
  applyPlanConfig();
};

const load = async () => {
  const [plansResp, runsResp, envResp, platformResp, moduleResp] = await Promise.all([
    platformApi.testPlans(),
    platformApi.testRuns(),
    platformApi.environments(),
    platformApi.platforms(),
    platformApi.apiModules(),
  ]);
  plans.value = unwrapList(plansResp.data);
  runs.value = unwrapList(runsResp.data);
  environments.value = unwrapList(envResp.data);
  platforms.value = unwrapList(platformResp.data);
  modules.value = unwrapList(moduleResp.data);
  const queryPlan = Number(route.query.plan);
  selectedPlan.value = plans.value.find((item) => item.id === queryPlan)?.id || selectedPlan.value || plans.value[0]?.id;
  selectedEnvironment.value ||= environments.value[0]?.id;
  selectedRun.value = runs.value.find((run) => run.id === selectedRun.value?.id) || undefined;
  applyPlanConfig();
};

const pollLatestRun = () => {
  stopPolling();
  running.value = true;
  pollTimer.value = window.setInterval(async () => {
    const { data } = await platformApi.testRuns();
    runs.value = unwrapList(data);
    selectedRun.value = runs.value.find((run) => run.id === selectedRun.value?.id) || selectedRun.value;
    if (selectedRun.value && !["pending", "running"].includes(selectedRun.value.status)) stopPolling();
  }, 3000);
};
const stopPolling = () => {
  running.value = false;
  if (pollTimer.value) {
    window.clearInterval(pollTimer.value);
    pollTimer.value = undefined;
  }
};
const runSelectedPlan = async () => {
  if (!selectedPlan.value) return;
  const { data } = await platformApi.runPlan(selectedPlan.value, selectedEnvironment.value);
  selectedRun.value = data;
  runs.value = [data, ...runs.value.filter((run) => run.id !== data.id)];
  if (data.detail) {
    ElMessage.warning(data.detail);
  } else {
    ElMessage.success("执行任务已触发");
    pollLatestRun();
  }
};

watch(activePlan, applyPlanConfig);
onMounted(load);
onBeforeUnmount(stopPolling);
</script>
