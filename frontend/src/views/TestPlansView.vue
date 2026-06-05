<template>
  <div class="plan-layout">
    <aside class="plan-panel">
      <div class="plan-toolbar">
        <el-input v-model="keyword" placeholder="搜索计划..." clearable />
        <el-button type="primary" @click="openCreate">新建</el-button>
      </div>
      <div class="plan-list">
        <button v-for="plan in filteredPlans" :key="plan.id" class="plan-item" :class="{ active: selectedPlan?.id === plan.id }" @click="selectedPlan = plan">
          <div class="plan-name">{{ plan.name }}</div>
          <div class="plan-meta">
            <span class="pt pt-erp">{{ plan.platform_name || platformName(plan.platform_ref) || "平台" }}</span>
            <span>{{ plan.module_count || 0 }} 个模块</span>
            <span>{{ plan.api_count || 0 }} 条接口</span>
            <span class="badge" :class="statusBadge(plan.status)">{{ statusText(plan.status) }}</span>
          </div>
        </button>
        <div v-if="!filteredPlans.length && !loading" class="plan-empty">暂无测试计划</div>
      </div>
    </aside>

    <section class="plan-detail">
      <template v-if="selectedPlan">
        <div class="v11-topbar">
          <div>
            <h2>{{ selectedPlan.name }}</h2>
            <span>{{ selectedPlan.description || "暂无描述" }}</span>
          </div>
          <div class="v11-actions">
            <el-button @click="openEdit(selectedPlan)">编辑计划</el-button>
            <el-button @click="clonePlan(selectedPlan)">克隆</el-button>
            <el-button class="danger-link" @click="deletePlan(selectedPlan)">删除</el-button>
            <el-button type="primary" @click="$router.push({ path: '/test-runs', query: { plan: selectedPlan.id } })">去执行</el-button>
          </div>
        </div>
        <div class="v11-content">
          <div class="info-card">
            <h3>基本信息</h3>
            <div class="info-row"><span>计划名称</span><strong>{{ selectedPlan.name }}</strong></div>
            <div class="info-row"><span>执行平台</span><strong>{{ selectedPlan.platform_name || platformName(selectedPlan.platform_ref) || "-" }}</strong></div>
            <div class="info-row"><span>状态</span><strong>{{ statusText(selectedPlan.status) }}</strong></div>
            <div class="info-row"><span>创建人</span><strong>{{ selectedPlan.created_by_name || "-" }}</strong></div>
            <div class="info-row"><span>最后修改人</span><strong>{{ selectedPlan.updated_by_name || "-" }}</strong></div>
            <div class="info-row"><span>模块数量</span><strong>{{ selectedPlan.module_count || 0 }}</strong></div>
            <div class="info-row"><span>接口数量</span><strong>{{ selectedPlan.api_count || 0 }}</strong></div>
          </div>
          <div class="info-card">
            <h3>关联接口</h3>
            <el-table :data="selectedApis" stripe>
              <el-table-column prop="name" label="接口名称" min-width="160" />
              <el-table-column label="方法" width="90"><template #default="{ row }"><span class="method-tag" :class="row.method">{{ row.method }}</span></template></el-table-column>
              <el-table-column prop="path" label="请求路径" min-width="240" show-overflow-tooltip />
            </el-table>
          </div>
        </div>
      </template>
      <el-empty v-else description="选择左侧测试计划查看详情" />
    </section>

    <el-dialog v-model="formVisible" :title="editingId ? '编辑测试计划' : '新建测试计划'" width="680px">
      <el-form :model="form" label-width="92px">
        <el-form-item label="计划名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="执行平台" required>
          <el-select v-model="form.platform_ref" style="width: 100%" @change="onPlatformChange">
            <el-option v-for="platform in platforms" :key="platform.id" :label="platform.name" :value="platform.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联模块" required>
          <el-checkbox-group v-model="form.module_ids" class="check-list" @change="syncApisByModules">
            <el-checkbox v-for="module in availableModules" :key="module.id" :value="module.id">{{ module.name }} ({{ module.api_count || 0 }}条接口)</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="关联接口" required>
          <el-checkbox-group v-model="form.api_ids" class="check-list">
            <el-checkbox v-for="api in availableApis" :key="api.id" :value="api.id">{{ api.name }} - {{ api.method }} {{ api.path }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePlan">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";

const loading = ref(false);
const saving = ref(false);
const keyword = ref("");
const formVisible = ref(false);
const editingId = ref<number>();
const plans = ref<any[]>([]);
const platforms = ref<any[]>([]);
const modules = ref<any[]>([]);
const apis = ref<any[]>([]);
const selectedPlan = ref<any>();
const form = reactive({ name: "", description: "", platform_ref: undefined as number | undefined, module_ids: [] as number[], api_ids: [] as number[], status: "pending", plan_type: "api", is_active: true });

const filteredPlans = computed(() => plans.value.filter((item) => !keyword.value || item.name.toLowerCase().includes(keyword.value.toLowerCase())));
const availableModules = computed(() => modules.value.filter((item) => !form.platform_ref || item.managed_platform === form.platform_ref));
const availableApis = computed(() => apis.value.filter((item) => !form.module_ids.length || form.module_ids.includes(item.module)));
const selectedApis = computed(() => apis.value.filter((item) => (selectedPlan.value?.api_ids || []).includes(item.id)));

const platformName = (id: number) => platforms.value.find((item) => item.id === id)?.name;
const statusText = (status: string) => ({ pending: "待执行", running: "执行中", completed: "已完成" }[status] || status);
const statusBadge = (status: string) => (status === "completed" ? "badge-success" : status === "running" ? "badge-primary" : "badge-warning");

const load = async () => {
  loading.value = true;
  try {
    const [planResp, platformResp, moduleResp, apiResp] = await Promise.all([
      platformApi.testPlans(),
      platformApi.platforms(),
      platformApi.apiModules(),
      platformApi.apiDefinitions(),
    ]);
    plans.value = unwrapList(planResp.data);
    platforms.value = unwrapList(platformResp.data);
    modules.value = unwrapList(moduleResp.data);
    apis.value = unwrapList(apiResp.data);
    selectedPlan.value = selectedPlan.value ? plans.value.find((item) => item.id === selectedPlan.value.id) : plans.value[0];
  } finally {
    loading.value = false;
  }
};

const resetForm = () => {
  editingId.value = undefined;
  Object.assign(form, { name: "", description: "", platform_ref: platforms.value[0]?.id, module_ids: [], api_ids: [], status: "pending", plan_type: "api", is_active: true });
};
const openCreate = () => {
  resetForm();
  formVisible.value = true;
};
const openEdit = (plan: any) => {
  editingId.value = plan.id;
  Object.assign(form, { name: plan.name, description: plan.description || "", platform_ref: plan.platform_ref, module_ids: plan.module_ids || [], api_ids: plan.api_ids || [], status: plan.status || "pending", plan_type: plan.plan_type || "api", is_active: plan.is_active });
  formVisible.value = true;
};
const onPlatformChange = () => {
  form.module_ids = [];
  form.api_ids = [];
};
const syncApisByModules = () => {
  form.api_ids = availableApis.value.map((item) => item.id);
};
const savePlan = async () => {
  if (!form.name.trim() || !form.platform_ref || !form.module_ids.length || !form.api_ids.length) {
    ElMessage.warning("计划名称、平台、模块和接口均必填");
    return;
  }
  saving.value = true;
  try {
    if (editingId.value) await platformApi.updateTestPlan(editingId.value, form);
    else await platformApi.createTestPlan(form);
    ElMessage.success("测试计划已保存");
    formVisible.value = false;
    await load();
  } finally {
    saving.value = false;
  }
};
const clonePlan = (plan: any) => {
  openEdit(plan);
  editingId.value = undefined;
  form.name = `${plan.name} 副本`;
};
const deletePlan = async (plan: any) => {
  await ElMessageBox.confirm(`确认删除测试计划「${plan.name}」？历史执行记录不会删除。`, "删除确认", { type: "warning" });
  await platformApi.deleteTestPlan(plan.id);
  ElMessage.success("测试计划已删除");
  selectedPlan.value = undefined;
  await load();
};

onMounted(load);
</script>
