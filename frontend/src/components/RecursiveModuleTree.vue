<template>
  <div class="recursive-module-tree">
    <template v-for="module in nodes" :key="module.id">
      <div
        class="recursive-module-node unified-tree-node"
        :class="{ active: selectedModuleId === module.id }"
        :style="{ paddingLeft: `${12 + depth * 20}px` }"
        role="button"
        tabindex="0"
        @click="selectModule(module.id)"
        @keydown.enter="selectModule(module.id)"
      >
        <button v-if="childrenOf(module.id).length" class="tree-toggle-btn" type="button" @click.stop="toggle(module.id)">
          <span class="tree-toggle" :class="{ expanded: isExpanded(module.id) }">›</span>
        </button>
        <span v-else class="tree-toggle-placeholder" />
        <span class="tree-node-name" :title="pathLabel(module.id)">{{ module.name }}</span>
        <em v-if="countLabel(module)">{{ countLabel(module) }}</em>
      </div>
      <template v-if="isExpanded(module.id)">
        <button
          v-for="api in apiItemsFor(module.id)"
          :key="api.id"
          class="recursive-api-node unified-tree-node"
          :class="{ active: selectedApiId === api.id }"
          :style="{ paddingLeft: `${32 + depth * 20}px` }"
          type="button"
          @click="emit('select-api', api)"
        >
          <span class="method-tag" :class="api.method">{{ api.method }}</span><span class="tree-node-name">{{ api.name }}</span>
        </button>
        <RecursiveModuleTree
          v-if="childrenOf(module.id).length"
          :nodes="childrenOf(module.id)"
          :all-modules="allModules"
          :selected-module-id="selectedModuleId"
          :selected-api-id="selectedApiId"
          :depth="depth + 1"
          :api-items="apiItems"
          :count-label="countLabel"
          @select-module="emit('select-module', $event)"
          @select-api="emit('select-api', $event)"
        />
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { modulePathLabel, type ModuleTreeItem } from "@/utils/moduleTree";

defineOptions({ name: "RecursiveModuleTree" });

const props = withDefaults(defineProps<{
  nodes: ModuleTreeItem[];
  allModules: ModuleTreeItem[];
  selectedModuleId?: number;
  selectedApiId?: number;
  depth?: number;
  apiItems?: Array<{ id: number; module?: number; name: string; method: string }>;
  countLabel?: (module: ModuleTreeItem) => string | number | undefined;
}>(), { depth: 1, apiItems: () => [], countLabel: () => undefined });

const emit = defineEmits<{
  "select-module": [id: number];
  "select-api": [api: { id: number; module?: number; name: string; method: string }];
}>();

const expandedIds = ref<number[]>(props.nodes.map((item) => item.id));
const childrenOf = (parentId: number) => props.allModules.filter((item) => item.parent === parentId);
const apiItemsFor = (moduleId: number) => props.apiItems.filter((item) => item.module === moduleId);
const isExpanded = (id: number) => expandedIds.value.includes(id);
const toggle = (id: number) => {
  expandedIds.value = isExpanded(id) ? expandedIds.value.filter((item) => item !== id) : [...expandedIds.value, id];
};
const selectModule = (id: number) => {
  emit("select-module", id);
};
const pathLabel = (id: number) => modulePathLabel(props.allModules, id, "");
</script>

<style scoped>
.recursive-module-node,.recursive-api-node{display:flex;align-items:center;gap:7px;min-height:34px;border-radius:6px;color:#334155;cursor:pointer}
.recursive-module-node:hover,.recursive-module-node.active,.recursive-api-node:hover,.recursive-api-node.active{background:#eef2ff;color:#4f46e5}
.tree-toggle-btn{width:20px;height:24px;padding:0;border:0;background:transparent;color:#64748b}.tree-toggle-placeholder{width:20px;flex:0 0 20px}
.tree-node-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.recursive-module-node em{margin-left:auto;padding-right:10px;color:#64748b;font-size:12px;font-style:normal}
.recursive-api-node{width:100%;border:0;background:transparent;text-align:left;padding-right:8px}.method-tag{font-size:10px;font-style:normal}.method-tag.GET{color:#047857}.method-tag.POST{color:#1d4ed8}.method-tag.PUT,.method-tag.PATCH{color:#a16207}.method-tag.DELETE{color:#b91c1c}
</style>
