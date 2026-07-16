<template>
  <div class="api-directory-branch">
    <template v-for="module in nodes" :key="module.id">
      <div class="directory-module-row" :style="rowStyle">
        <button class="directory-toggle" type="button" :disabled="!childrenOf(module.id).length && !apisOf(module.id).length" @click="toggle(module.id)">
          <span v-if="childrenOf(module.id).length || apisOf(module.id).length" class="tree-toggle" :class="{ expanded: isExpanded(module.id) }">›</span>
        </button>
        <button class="directory-node-button" :class="{ active: selectedModuleId === module.id }" type="button" :title="pathLabel(module.id)" @click="emit('select-module', module.id)">
          <span class="tree-node-name">{{ module.name }}</span>
          <em>{{ countLabel(module) }}</em>
        </button>
      </div>
      <template v-if="isExpanded(module.id)">
        <button
          v-for="api in apisOf(module.id)"
          :key="api.id"
          class="directory-api-row"
          :class="{ active: selectedApiId === api.id }"
          :style="apiRowStyle"
          type="button"
          @click="emit('select-api', api)"
        >
          <i class="method-tag" :class="api.method">{{ api.method }}</i>
          <span class="tree-node-name">{{ api.name }}</span>
        </button>
        <ApiDirectoryBranch
          v-if="childrenOf(module.id).length"
          :nodes="childrenOf(module.id)"
          :all-modules="allModules"
          :apis="apis"
          :selected-module-id="selectedModuleId"
          :selected-api-id="selectedApiId"
          :level="level + 1"
          :count-label="countLabel"
          @select-module="emit('select-module', $event)"
          @select-api="emit('select-api', $event)"
        />
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import { modulePathLabel, type ModuleTreeItem } from "@/utils/moduleTree";

defineOptions({ name: "ApiDirectoryBranch" });

const props = withDefaults(defineProps<{
  nodes: ModuleTreeItem[];
  allModules: ModuleTreeItem[];
  apis?: Array<{ id: number; module?: number; name: string; method: string }>;
  selectedModuleId?: number;
  selectedApiId?: number;
  level?: number;
  countLabel: (module: ModuleTreeItem) => string | number;
}>(), { apis: () => [], level: 1 });

const emit = defineEmits<{
  "select-module": [id: number];
  "select-api": [api: { id: number; module?: number; name: string; method: string }];
}>();

const expandedIds = ref<number[]>(props.nodes.map((item) => item.id));
const childrenOf = (parentId: number) => props.allModules.filter((item) => item.parent === parentId);
const apisOf = (moduleId: number) => props.apis.filter((item) => item.module === moduleId);
const isExpanded = (id: number) => expandedIds.value.includes(id);
const toggle = (id: number) => {
  expandedIds.value = isExpanded(id) ? expandedIds.value.filter((item) => item !== id) : [...expandedIds.value, id];
};
const rowStyle = computed(() => ({ "--directory-indent": `${22 + (props.level - 1) * 22}px` }));
const apiRowStyle = computed(() => ({ "--directory-api-indent": `${44 + (props.level - 1) * 22}px` }));
const pathLabel = (id: number) => modulePathLabel(props.allModules, id, "");
</script>

<style scoped>
.directory-module-row{position:relative;display:grid;grid-template-columns:18px minmax(0,1fr);align-items:center;margin:3px 0 3px var(--directory-indent);width:calc(100% - var(--directory-indent));min-height:36px}
.directory-module-row::before{content:"";position:absolute;top:-5px;bottom:-5px;left:-10px;width:1px;background:var(--gray-200)}
.directory-toggle{width:18px;height:36px;padding:0;border:0;background:transparent;color:var(--gray-500);cursor:pointer}.directory-toggle:disabled{cursor:default}
.directory-node-button{width:100%;min-width:0;min-height:36px;display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:8px;padding:7px 10px;border:0;border-radius:var(--radius-lg);background:transparent;color:var(--gray-800);font-size:14px;font-weight:650;line-height:1.35;text-align:left;cursor:pointer}
.directory-node-button:hover,.directory-node-button.active{background:var(--brand-lighter);color:var(--brand)}
.tree-node-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.directory-node-button em{min-width:auto;padding:0 4px;color:var(--gray-500);font-size:12px;font-style:normal;font-weight:700}.directory-node-button.active em{color:var(--brand)}
.directory-api-row{position:relative;width:calc(100% - var(--directory-api-indent));min-height:34px;display:flex;align-items:center;gap:8px;margin:2px 0 3px var(--directory-api-indent);padding:6px 9px;border:0;border-radius:6px;background:transparent;color:var(--gray-800);font-size:14px;font-weight:650;line-height:1.35;text-align:left;cursor:pointer}.directory-api-row::before{content:"";position:absolute;top:-5px;bottom:-5px;left:-10px;width:1px;background:var(--gray-200)}
.directory-api-row:hover{background:var(--gray-50)}.directory-api-row.active{color:var(--brand)}
.method-tag{flex:0 0 52px;min-width:48px;padding:0 8px;font-size:11px}
</style>
