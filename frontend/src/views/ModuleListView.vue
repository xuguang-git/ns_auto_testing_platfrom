<template>
  <div class="module-v11">
    <aside class="module-tree unified-tree-panel">
      <div class="tree-toolbar unified-tree-head">
        <strong>平台目录</strong>
        <el-button size="small" type="primary" @click="openCreate">新增</el-button>
      </div>
      <button class="tree-node unified-tree-node" :class="{ active: !selectedPlatform && !selectedModule }" @click="selectAll">全部平台</button>
      <section v-for="platform in platforms" :key="platform.id">
        <button class="tree-node platform unified-tree-node" :class="{ active: selectedPlatform === platform.id && !selectedModule }" @click="selectPlatform(platform.id)">
          <span class="tree-node-main">
            <span v-if="platformHasChildren(platform)" class="tree-toggle-btn" role="button" tabindex="0" @click.stop="togglePlatform(platform.id)" @keydown.enter.stop="togglePlatform(platform.id)">
              <span class="tree-toggle" :class="{ expanded: isPlatformExpanded(platform.id) }">›</span>
            </span>
            <span>{{ platform.name }}</span>
          </span>
          <em>{{ modulesByPlatform(platform).length }}</em>
        </button>
        <ApiDirectoryBranch
          v-if="isPlatformExpanded(platform.id)"
          :nodes="rootModulesByPlatform(platform)"
          :all-modules="modulesByPlatform(platform)"
          :selected-module-id="selectedModule"
          :count-label="moduleCountLabel"
          @select-module="selectModule($event, platform.id)"
        />
      </section>
    </aside>

    <section class="module-main">
      <div class="v11-topbar">
        <div>
          <h2>{{ breadcrumb }}</h2>
          <span>维护平台下的接口模块分类</span>
        </div>
        <el-button type="primary" @click="openCreate">+ 新增模块</el-button>
      </div>
      <div class="v11-content">
        <div class="table-card">
          <el-table :data="filteredModules" v-loading="loading" stripe>
            <el-table-column prop="name" label="模块名称" min-width="160" />
            <el-table-column prop="code" label="编码" width="130"><template #default="{ row }"><code class="inline-code">{{ row.code || "-" }}</code></template></el-table-column>
            <el-table-column label="平台" width="120"><template #default="{ row }">{{ platformName(row) }}</template></el-table-column>
            <el-table-column prop="api_count" label="接口数" width="100" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }"><span class="badge" :class="row.is_active ? 'badge-success' : 'badge-gray'">{{ row.is_active ? "启用" : "停用" }}</span></template>
            </el-table-column>
            <el-table-column prop="created_by_name" label="创建人" width="120" show-overflow-tooltip />
            <el-table-column prop="updated_by_name" label="最后修改人" width="130" show-overflow-tooltip />
            <el-table-column prop="sort_order" label="排序" width="90" />
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
                <el-button link class="danger-link" @click="openDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </section>

    <el-dialog v-model="formVisible" :title="editingId ? '编辑模块' : '新增模块'" width="540px">
      <el-form :model="form" label-width="92px">
        <el-form-item label="所属平台" required>
          <el-select v-model="form.managed_platform" style="width: 100%" @change="syncLegacyPlatform">
            <el-option v-for="item in platforms" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="模块名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="模块编码" required><el-input v-model="form.code" /></el-form-item>
        <el-form-item label="上级模块">
          <el-tree-select v-model="form.parent" :data="parentModuleOptions" clearable check-strictly node-key="value" :props="{ label: 'label', children: 'children', disabled: 'disabled' }" style="width: 100%" />
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort_order" :min="0" :max="999" /></el-form-item>
        <el-form-item label="启用状态"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveModule">保存</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";
import ApiDirectoryBranch from "@/components/ApiDirectoryBranch.vue";
import { buildModuleTreeOptions, modulePathNames } from "@/utils/moduleTree";

const loading = ref(false);
const saving = ref(false);
const formVisible = ref(false);
const platforms = ref<any[]>([]);
const modules = ref<any[]>([]);
const selectedPlatform = ref<number>();
const selectedModule = ref<number>();
const expandedPlatforms = ref<number[]>([]);
const expandedModules = ref<number[]>([]);
const editingId = ref<number>();
const form = reactive({ managed_platform: undefined as number | undefined, platform: "ERP", parent: undefined as number | undefined, name: "", code: "", description: "", sort_order: 0, is_active: true });

const filteredModules = computed(() => modules.value.filter((item) => (!selectedPlatform.value || item.managed_platform === selectedPlatform.value) && (!selectedModule.value || item.id === selectedModule.value)));
const breadcrumb = computed(() => {
  if (selectedModule.value) {
    const module = modules.value.find((item) => item.id === selectedModule.value);
    return `${platformName(module)} / ${module?.name || ""}`;
  }
  if (selectedPlatform.value) return platforms.value.find((item) => item.id === selectedPlatform.value)?.name || "平台";
  return "全部平台";
});

const modulesByPlatform = (platform: any) => modules.value.filter((item) => item.managed_platform === platform.id || item.platform === platform.code?.toUpperCase());
const rootModulesByPlatform = (platform: any) => modulesByPlatform(platform).filter((item) => !item.parent);
const childModules = (parentId: number) => modules.value.filter((item) => item.parent === parentId);
const parentModuleOptions = computed(() => {
  const options = buildModuleTreeOptions(modules.value, platformCodeForId(form.managed_platform));
  return disableLeafParents(editingId.value ? removeCurrentSubtree(options, editingId.value) : options);
});
const platformHasChildren = (platform: any) => rootModulesByPlatform(platform).length > 0;
const moduleHasChildren = (moduleId: number) => childModules(moduleId).length > 0;
const isPlatformExpanded = (platformId: number) => expandedPlatforms.value.includes(platformId);
const isModuleExpanded = (moduleId: number) => expandedModules.value.includes(moduleId);
const togglePlatform = (platformId: number) => {
  expandedPlatforms.value = isPlatformExpanded(platformId) ? expandedPlatforms.value.filter((item) => item !== platformId) : [...expandedPlatforms.value, platformId];
};
const toggleModule = (moduleId: number) => {
  expandedModules.value = isModuleExpanded(moduleId) ? expandedModules.value.filter((item) => item !== moduleId) : [...expandedModules.value, moduleId];
};
const platformName = (module: any) => platforms.value.find((item) => item.id === module?.managed_platform || item.code?.toUpperCase() === module?.platform)?.name || module?.platform || "-";
const platformCodeForId = (id?: number) => platformCode(platforms.value.find((item) => item.id === id));
const platformCode = (platform: any) => platform?.code?.toUpperCase?.() || platform?.code || "";
const removeCurrentSubtree = (nodes: any[], currentId: number): any[] => nodes.filter((node) => node.value !== currentId).map((node) => ({ ...node, children: removeCurrentSubtree(node.children || [], currentId) }));
const disableLeafParents = (nodes: any[]): any[] => nodes.map((node) => ({
  ...node,
  disabled: modulePathNames(modules.value, node.value).length >= 3,
  children: disableLeafParents(node.children || []),
}));
const moduleCountLabel = (module: any) => `${module.api_count || 0} 接口`;
const syncLegacyPlatform = () => {
  const platform = platforms.value.find((item) => item.id === form.managed_platform);
  form.platform = platform?.code?.toUpperCase() || "ERP";
};

const load = async () => {
  loading.value = true;
  try {
    const [platformData, moduleData] = await Promise.all([platformApi.cachedPlatforms(), platformApi.cachedApiModules()]);
    platforms.value = unwrapList(platformData as any);
    modules.value = unwrapList(moduleData as any);
    expandedPlatforms.value = platforms.value.filter(platformHasChildren).map((item) => item.id);
    expandedModules.value = modules.value.filter((item) => moduleHasChildren(item.id)).map((item) => item.id);
  } finally {
    loading.value = false;
  }
};

const selectAll = () => {
  selectedPlatform.value = undefined;
  selectedModule.value = undefined;
};
const selectPlatform = (id: number) => {
  selectedPlatform.value = id;
  selectedModule.value = undefined;
};
const selectModule = (id: number, platformId: number) => {
  selectedPlatform.value = platformId;
  selectedModule.value = id;
};

const openCreate = () => {
  if (selectedModule.value && modulePathNames(modules.value, selectedModule.value).length >= 3) {
    ElMessage.warning("第三级模块不能新增下级模块");
    return;
  }
  editingId.value = undefined;
  Object.assign(form, { managed_platform: selectedPlatform.value || platforms.value[0]?.id, platform: "ERP", parent: selectedModule.value, name: "", code: "", description: "", sort_order: modules.value.length + 1, is_active: true });
  syncLegacyPlatform();
  formVisible.value = true;
};
const openEdit = (row: any) => {
  editingId.value = row.id;
  Object.assign(form, { managed_platform: row.managed_platform, platform: row.platform, parent: row.parent, name: row.name, code: row.code || "", description: row.description || "", sort_order: row.sort_order || 0, is_active: row.is_active });
  formVisible.value = true;
};
const saveModule = async () => {
  if (!form.managed_platform || !form.name.trim() || !form.code.trim()) {
    ElMessage.warning("平台和模块名称必填");
    return;
  }
  syncLegacyPlatform();
  saving.value = true;
  try {
    if (editingId.value) await platformApi.updateApiModule(editingId.value, form);
    else await platformApi.createApiModule(form);
    ElMessage.success("模块已保存");
    formVisible.value = false;
    await load();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.parent?.[0] || error?.response?.data?.detail || "保存模块失败");
  } finally {
    saving.value = false;
  }
};
const openDelete = async (row: any) => {
  await ElMessageBox.confirm(`确认删除模块「${row.name}」？`, "删除确认", { type: "warning" });
  await platformApi.deleteApiModule(row.id);
  ElMessage.success("模块已删除");
  selectedModule.value = undefined;
  await load();
};

onMounted(load);
</script>
