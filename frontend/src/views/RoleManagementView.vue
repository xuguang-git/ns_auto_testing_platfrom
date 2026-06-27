<template>
  <div class="v11-page">
    <div class="v11-topbar">
      <div>
        <h2>角色管理</h2>
        <span>维护角色、页面入口和功能操作权限</span>
      </div>
      <el-button type="primary" @click="openCreate">新增角色</el-button>
    </div>
    <div class="v11-content">
      <div class="table-card">
        <el-table :data="roles" v-loading="loading" stripe>
          <el-table-column prop="name" label="角色名称" min-width="150" />
          <el-table-column prop="code" label="编码" width="150" />
          <el-table-column prop="user_count" label="用户数" width="90" />
          <el-table-column label="类型" width="100">
            <template #default="{ row }">
              <span class="badge" :class="row.is_builtin ? 'badge-primary' : 'badge-gray'">{{ row.is_builtin ? "预置" : "自定义" }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openEdit(row)">编辑权限</el-button>
              <el-button v-if="!row.is_builtin" link class="danger-link" @click="deleteRole(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog v-model="visible" :title="editingId ? '编辑角色' : '新增角色'" width="880px" class="role-permission-dialog">
      <el-form :model="form" label-width="92px">
        <div class="role-form-grid">
          <el-form-item label="角色名称" required>
            <el-input v-model="form.name" maxlength="32" show-word-limit />
          </el-form-item>
          <el-form-item label="角色编码" required>
            <el-input v-model="form.code" maxlength="32" :disabled="!!editingId && editingBuiltin" />
          </el-form-item>
        </div>
        <el-form-item label="说明">
          <el-input v-model="form.description" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="权限">
          <div class="permission-tree-panel">
            <div class="permission-tree-toolbar">
              <el-input
                v-model="permissionKeyword"
                clearable
                placeholder="搜索权限名称或编码"
                class="permission-tree-search"
                @input="filterPermissionTree"
              />
              <div class="permission-tree-summary">
                已选 <strong>{{ selectedPermissionCount }}</strong> 项
              </div>
            </div>
            <div class="permission-tree-tip">
              Tab 权限控制左侧一级分组，菜单权限控制页面入口，功能权限控制接口和按钮操作；三者独立勾选，只在树中展示归属关系。
            </div>
            <el-tree
              ref="permissionTreeRef"
              class="permission-tree"
              node-key="treeKey"
              show-checkbox
              check-strictly
              highlight-current
              :data="permissionTree"
              :props="permissionTreeProps"
              :default-expanded-keys="defaultExpandedKeys"
              :filter-node-method="filterPermissionNode"
              @check="syncCheckedPermissions"
            >
              <template #default="{ data }">
                <div class="permission-tree-node">
                  <span class="permission-node-title">{{ permissionNodeName(data) }}</span>
                  <span class="permission-node-code">{{ data.code }}</span>
                  <span class="permission-node-tag" :class="permissionNodeType(data)">
                    {{ permissionNodeTypeLabel(data) }}
                  </span>
                </div>
              </template>
            </el-tree>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRole">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, nextTick, onMounted, reactive, ref } from "vue";

import { accountApi } from "@/api/account";
import { unwrapList } from "@/api/platform";

interface PermissionNode {
  id: number;
  code: string;
  module: string;
  action: string;
  name: string;
  description?: string;
  type: "tab" | "menu" | "page" | "action";
  parent?: number | null;
  route_path?: string;
  is_visible?: boolean;
  sort_order?: number;
  treeKey?: string;
  children?: PermissionNode[];
}

const loading = ref(false);
const saving = ref(false);
const roles = ref<any[]>([]);
const permissions = ref<PermissionNode[]>([]);
const visible = ref(false);
const editingId = ref<number>();
const editingBuiltin = ref(false);
const permissionKeyword = ref("");
const permissionTreeRef = ref<any>();
const form = reactive({ name: "", code: "", description: "", permissions: [] as number[] });

const permissionTreeProps = {
  label: "name",
  children: "children",
};

const permissionTree = computed(() => buildPermissionTree(permissions.value));
const flatPermissionTree = computed(() => flattenPermissionTree(permissionTree.value));
const defaultExpandedKeys = computed(() => flatPermissionTree.value.filter((item) => permissionNodeType(item) !== "action").map((item) => item.treeKey));
const selectedPermissionCount = computed(() => form.permissions.length);

const load = async () => {
  loading.value = true;
  try {
    const [roleResp, permResp] = await Promise.all([accountApi.roles(), accountApi.permissions()]);
    roles.value = unwrapList(roleResp.data);
    permissions.value = unwrapList(permResp.data);
  } finally {
    loading.value = false;
  }
};

const openCreate = async () => {
  editingId.value = undefined;
  editingBuiltin.value = false;
  permissionKeyword.value = "";
  Object.assign(form, { name: "", code: "", description: "", permissions: [] });
  visible.value = true;
  await resetTreeCheckedKeys();
};

const openEdit = async (row: any) => {
  editingId.value = row.id;
  editingBuiltin.value = row.is_builtin;
  permissionKeyword.value = "";
  Object.assign(form, { name: row.name, code: row.code, description: row.description || "", permissions: row.permissions || [] });
  visible.value = true;
  await resetTreeCheckedKeys();
};

const saveRole = async () => {
  form.permissions = getCheckedPermissionIds();
  saving.value = true;
  try {
    if (editingId.value) await accountApi.updateRole(editingId.value, form);
    else await accountApi.createRole(form);
    ElMessage.success("角色已保存");
    visible.value = false;
    await load();
  } finally {
    saving.value = false;
  }
};

const deleteRole = async (row: any) => {
  await ElMessageBox.confirm(`确认删除角色 ${row.name}？`, "删除确认", { type: "warning" });
  await accountApi.deleteRole(row.id);
  await load();
};

const buildPermissionTree = (source: PermissionNode[]) => {
  const nodes = source
    .filter((item) => item.is_visible !== false)
    .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0) || a.code.localeCompare(b.code))
    .map((item, index) => ({ ...item, treeKey: permissionTreeKey(item, index), children: [] }));
  const nodeMap = new Map<string, PermissionNode>(nodes.map((node) => [node.treeKey, node]));
  const parentKeyMap = new Map<number, string>();
  const roots: PermissionNode[] = [];

  nodes.forEach((node) => {
    if (permissionNodeType(node) !== "action" && !parentKeyMap.has(node.id)) {
      parentKeyMap.set(node.id, node.treeKey);
    }
  });

  nodes.forEach((node) => {
    const parentKey = node.parent ? parentKeyMap.get(node.parent) : "";
    if (parentKey && nodeMap.has(parentKey)) {
      nodeMap.get(parentKey)?.children?.push(node);
      return;
    }
    if (permissionNodeType(node) === "action") return;
    roots.push(node);
  });
  return roots;
};

const resetTreeCheckedKeys = async () => {
  await nextTick();
  permissionTreeRef.value?.setCheckedKeys(flatPermissionTree.value.filter((item) => form.permissions.includes(item.id)).map((item) => item.treeKey));
  filterPermissionTree();
};

const getCheckedPermissionIds = (): number[] => {
  const checkedNodes = (permissionTreeRef.value?.getCheckedNodes(false, false) || []) as PermissionNode[];
  return [...new Set(checkedNodes.map((item: PermissionNode) => item.id))];
};

const syncCheckedPermissions = () => {
  form.permissions = getCheckedPermissionIds();
};

const filterPermissionTree = () => {
  permissionTreeRef.value?.filter(permissionKeyword.value);
};

const filterPermissionNode = (keyword: string, data: PermissionNode) => {
  if (!keyword) return true;
  const value = keyword.trim().toLowerCase();
  return matchesPermissionNode(data, value);
};

const matchesPermissionNode = (node: PermissionNode, keyword: string): boolean => {
  return permissionNodeName(node).toLowerCase().includes(keyword) ||
    node.name.toLowerCase().includes(keyword) ||
    node.code.toLowerCase().includes(keyword) ||
    Boolean(node.children?.some((child) => matchesPermissionNode(child, keyword)));
};

const permissionNodeType = (node: PermissionNode) => {
  if (node.type === "page") return node.parent ? "menu" : "tab";
  return node.type;
};

const permissionTreeKey = (node: PermissionNode, index: number) => `${node.parent || "root"}:${node.id}:${index}`;

const flattenPermissionTree = (nodes: PermissionNode[]): PermissionNode[] => nodes.flatMap((node) => [node, ...flattenPermissionTree(node.children || [])]);

const permissionNodeTypeLabel = (node: PermissionNode) => {
  const type = permissionNodeType(node);
  if (type === "tab") return "Tab";
  if (type === "menu") return "菜单";
  return "功能";
};

const permissionNodeName = (node: PermissionNode) => {
  return node.name;
};

onMounted(load);
</script>
