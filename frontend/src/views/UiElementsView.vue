<template>
  <div class="ui-elements-page ui-elements-workbench">
    <aside class="ui-page-tree-panel unified-tree-panel">
      <div class="ui-panel-head unified-tree-head">
        <strong>页面结构</strong>
        <el-button size="small" type="primary" :disabled="!suiteFilter" @click="openPage()">新增</el-button>
      </div>
      <el-select v-model="suiteFilter" placeholder="套件" style="width: 100%" @change="onSuiteChange">
        <el-option v-for="suite in suites" :key="suite.id" :label="suite.name" :value="suite.id" />
      </el-select>
      <div class="ui-page-tree unified-tree-body">
        <button class="ui-page-node unified-tree-node" :class="{ active: !selectedPageId }" @click="selectPage(undefined)">
          <span class="unified-tree-name">全部页面</span>
        </button>
        <template v-for="page in rootPages" :key="page.id">
          <PageNode
            :page="page"
            :children-map="childrenMap"
            :selected-id="selectedPageId"
            @select="selectPage"
            @add-child="openPage(undefined, $event)"
            @edit="openPage"
            @remove="deletePage"
          />
        </template>
      </div>
    </aside>

    <section class="ui-elements-main">
      <header class="data-factory-head">
        <div>
          <div class="breadcrumb-lite">UI测试 / 定位元素</div>
          <h1>定位元素</h1>
          <p>维护页面树和元素定位表达式，供 UI 用例步骤复用。</p>
        </div>
        <div class="data-factory-actions">
          <el-input v-model="keyword" placeholder="搜索元素名称、选择器" clearable style="width: 280px" />
          <el-button @click="load">刷新</el-button>
          <el-button type="primary" :disabled="!suiteFilter" @click="openElement()">新增元素</el-button>
        </div>
      </header>

      <section class="data-factory-card">
        <el-table :data="filteredElements" v-loading="loading" stripe height="100%">
          <el-table-column prop="name" label="元素名称" min-width="180" />
          <el-table-column prop="suite_name" label="套件" min-width="150" />
          <el-table-column label="页面" min-width="150"><template #default="{ row }">{{ row.page_node_name || row.page || "-" }}</template></el-table-column>
          <el-table-column prop="locator_type" label="定位方式" width="110" />
          <el-table-column prop="selector" label="定位表达式" min-width="280" show-overflow-tooltip />
          <el-table-column prop="created_by_name" label="创建人" width="120" show-overflow-tooltip />
          <el-table-column prop="updated_by_name" label="最后修改人" width="130" show-overflow-tooltip />
          <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
          <el-table-column label="状态" width="90">
            <template #default="{ row }"><span class="badge" :class="row.is_active ? 'badge-success' : 'badge-warning'">{{ row.is_active ? "启用" : "停用" }}</span></template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openValidate(row)">验证</el-button>
              <el-button link type="primary" @click="openElement(row)">编辑</el-button>
              <el-button link class="danger-link" @click="deleteElement(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </section>

    <el-dialog v-model="pageDialog" :title="pageForm.id ? '编辑页面' : '新增页面'" width="520px">
      <el-form :model="pageForm" label-width="86px">
        <el-form-item label="页面名称" required><el-input v-model="pageForm.name" /></el-form-item>
        <el-form-item label="父级页面">
          <el-tree-select
            v-model="pageForm.parent"
            :data="pageTreeOptions"
            clearable
            check-strictly
            node-key="value"
            :props="{ label: 'label', children: 'children' }"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="页面路径"><el-input v-model="pageForm.path" placeholder="/login 或业务路径" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="pageForm.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="pageForm.is_active" active-text="启用" inactive-text="停用" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pageDialog = false">取消</el-button>
        <el-button type="primary" @click="savePage">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="elementDialog" :title="elementForm.id ? '编辑定位元素' : '新增定位元素'" width="560px">
      <el-form :model="elementForm" label-width="96px">
        <el-form-item label="所属套件" required>
          <el-select v-model="elementForm.suite" style="width: 100%" @change="elementForm.page_node = undefined">
            <el-option v-for="suite in suites" :key="suite.id" :label="suite.name" :value="suite.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属页面">
          <el-tree-select
            v-model="elementForm.page_node"
            :data="pageTreeOptions"
            clearable
            check-strictly
            node-key="value"
            :props="{ label: 'label', children: 'children' }"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="元素名称" required><el-input v-model="elementForm.name" /></el-form-item>
        <el-form-item label="定位方式">
          <el-select v-model="elementForm.locator_type" style="width: 100%">
            <el-option label="CSS" value="css" />
            <el-option label="Text" value="text" />
            <el-option label="Role" value="role" />
            <el-option label="XPath" value="xpath" />
            <el-option label="TestId" value="test_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="定位表达式" required><el-input v-model="elementForm.selector" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="elementForm.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="elementForm.is_active" active-text="启用" inactive-text="停用" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="elementDialog = false">取消</el-button>
        <el-button type="primary" @click="saveElement">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="validateDialog" title="定位器验证" width="720px">
      <div class="locator-check">
        <div class="locator-check-target">
          <strong>{{ validatingElement?.name }}</strong>
          <span>{{ validatingElement?.locator_type }} / {{ validatingElement?.selector }}</span>
        </div>
        <el-form label-width="92px">
          <el-form-item label="页面 URL" required>
            <el-input v-model="validateForm.url" placeholder="https://example.com/login" />
          </el-form-item>
          <el-form-item label="浏览器">
            <el-select v-model="validateForm.browser" style="width: 180px">
              <el-option label="Chromium" value="chromium" />
              <el-option label="Firefox" value="firefox" />
              <el-option label="WebKit" value="webkit" />
            </el-select>
          </el-form-item>
        </el-form>
        <section v-if="validateResult" class="locator-check-result">
          <div class="locator-check-summary">
            <span class="badge" :class="validateResult.passed ? 'badge-success' : 'badge-danger'">
              {{ validateResult.passed ? "PASS" : "FAIL" }}
            </span>
            <span>命中 {{ validateResult.match_count || 0 }} 个，可见 {{ validateResult.visible_count || 0 }} 个，耗时 {{ validateResult.duration_ms || 0 }}ms</span>
          </div>
          <p v-if="validateResult.error" class="locator-check-error">{{ validateResult.error }}</p>
          <p v-if="validateResult.sample_text" class="locator-check-text">{{ validateResult.sample_text }}</p>
          <img v-if="validateResult.screenshot" :src="validateResult.screenshot" alt="定位器验证截图" />
          <ul v-if="validateResult.suggestions?.length" class="locator-check-suggestions">
            <li v-for="item in validateResult.suggestions" :key="item">{{ item }}</li>
          </ul>
        </section>
      </div>
      <template #footer>
        <el-button @click="validateDialog = false">关闭</el-button>
        <el-button type="primary" :loading="validating" @click="validateElement">开始验证</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { Delete, Edit, Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, defineComponent, h, onMounted, reactive, ref, type Component, type VNode } from "vue";

import { platformApi, unwrapList } from "@/api/platform";

interface UiSuite { id: number; name: string }
interface UiPage {
  id: number;
  suite: number;
  parent?: number;
  name: string;
  path?: string;
  description?: string;
  sort_order?: number;
  is_active: boolean;
  element_count?: number;
}
interface UiElement {
  id: number;
  suite?: number;
  suite_name?: string;
  page?: string;
  page_node?: number;
  page_node_name?: string;
  name: string;
  locator_type: string;
  selector: string;
  description?: string;
  is_active: boolean;
}

const PageNode: Component = defineComponent({
  props: {
    page: { type: Object, required: true },
    childrenMap: { type: Object, required: true },
    selectedId: { type: Number, required: false },
  },
  emits: ["select", "add-child", "edit", "remove"],
  setup(props, { emit }) {
    const treeActionIcon = (icon: Component, title: string, onClick: () => void) =>
      h("button", { class: "unified-tree-action", title, onClick }, [h(icon)]);

    return (): VNode => {
      const page = props.page as UiPage;
      const children = ((props.childrenMap as Record<number, UiPage[]>)[page.id] || []);
      return h("div", { class: "ui-page-branch unified-tree-branch" }, [
        h("div", { class: ["ui-page-node", "unified-tree-node", { active: props.selectedId === page.id }] }, [
          h("button", { class: "ui-page-name unified-tree-name", onClick: () => emit("select", page.id) }, page.name),
          h("span", { class: "ui-page-actions unified-tree-actions" }, [
            treeActionIcon(Plus, "新增子页面", () => emit("add-child", page.id)),
            treeActionIcon(Edit, "编辑页面", () => emit("edit", page)),
            treeActionIcon(Delete, "删除页面", () => emit("remove", page)),
          ]),
        ]),
        children.length ? h("div", { class: "ui-page-children unified-tree-children" }, children.map((child): VNode =>
          h(PageNode, {
            page: child,
            childrenMap: props.childrenMap,
            selectedId: props.selectedId,
            onSelect: (id: number) => emit("select", id),
            onAddChild: (id: number) => emit("add-child", id),
            onEdit: (node: UiPage) => emit("edit", node),
            onRemove: (node: UiPage) => emit("remove", node),
          }),
        )) : null,
      ]);
    };
  },
});

const loading = ref(false);
const suites = ref<UiSuite[]>([]);
const pages = ref<UiPage[]>([]);
const elements = ref<UiElement[]>([]);
const keyword = ref("");
const suiteFilter = ref<number>();
const selectedPageId = ref<number>();
const pageDialog = ref(false);
const elementDialog = ref(false);
const validateDialog = ref(false);
const validating = ref(false);
const validatingElement = ref<UiElement>();
const validateResult = ref<any>();
const pageForm = reactive({ id: undefined as number | undefined, suite: undefined as number | undefined, parent: undefined as number | undefined, name: "", path: "", description: "", is_active: true });
const elementForm = reactive({ id: undefined as number | undefined, suite: undefined as number | undefined, page_node: undefined as number | undefined, name: "", locator_type: "css", selector: "", description: "", is_active: true });
const validateForm = reactive({ url: "", browser: "chromium" });

const childrenMap = computed(() => pages.value.reduce<Record<number, UiPage[]>>((acc, page) => {
  if (page.parent) {
    if (!acc[page.parent]) acc[page.parent] = [];
    acc[page.parent].push(page);
  }
  return acc;
}, {}));
const rootPages = computed(() => pages.value.filter((page) => !page.parent));
const pageTreeOptions = computed(() => buildTreeOptions(rootPages.value));
const filteredElements = computed(() => elements.value.filter((item) => {
  const text = `${item.name} ${item.page_node_name || item.page || ""} ${item.selector}`.toLowerCase();
  return !keyword.value || text.includes(keyword.value.toLowerCase());
}));

const buildTreeOptions = (nodes: UiPage[]): any[] => nodes.map((page) => ({
  label: page.name,
  value: page.id,
  children: buildTreeOptions(childrenMap.value[page.id] || []),
}));

const load = async () => {
  loading.value = true;
  try {
    const { data } = await platformApi.uiSuites();
    suites.value = unwrapList<UiSuite>(data);
    if (!suiteFilter.value && suites.value.length) suiteFilter.value = suites.value[0].id;
    await Promise.all([loadPages(), loadElements()]);
  } finally {
    loading.value = false;
  }
};

const onSuiteChange = async () => {
  selectedPageId.value = undefined;
  await Promise.all([loadPages(), loadElements()]);
};

const loadPages = async () => {
  if (!suiteFilter.value) {
    pages.value = [];
    return;
  }
  const { data } = await platformApi.uiPages({ suite: suiteFilter.value });
  pages.value = unwrapList<UiPage>(data);
};

const loadElements = async () => {
  if (!suiteFilter.value) {
    elements.value = [];
    return;
  }
  const params: Record<string, unknown> = { suite: suiteFilter.value };
  if (selectedPageId.value) params.page_node = selectedPageId.value;
  const { data } = await platformApi.uiElements(params);
  elements.value = unwrapList<UiElement>(data);
};

const selectPage = async (id?: number) => {
  selectedPageId.value = id;
  await loadElements();
};

const openPage = (row?: UiPage, parentId?: number) => {
  Object.assign(pageForm, {
    id: row?.id,
    suite: row?.suite || suiteFilter.value,
    parent: row?.parent || parentId,
    name: row?.name || "",
    path: row?.path || "",
    description: row?.description || "",
    is_active: row?.is_active ?? true,
  });
  pageDialog.value = true;
};

const savePage = async () => {
  if (!pageForm.suite || !pageForm.name.trim()) {
    ElMessage.warning("套件和页面名称不能为空");
    return;
  }
  if (pageForm.id && pageForm.parent === pageForm.id) {
    ElMessage.warning("父级页面不能选择自身");
    return;
  }
  const payload = {
    suite: pageForm.suite,
    parent: pageForm.parent,
    name: pageForm.name.trim(),
    path: pageForm.path,
    description: pageForm.description,
    is_active: pageForm.is_active,
  };
  if (pageForm.id) await platformApi.updateUiPage(pageForm.id, payload);
  else await platformApi.createUiPage(payload);
  ElMessage.success("页面已保存");
  pageDialog.value = false;
  await loadPages();
};

const deletePage = async (row: UiPage) => {
  await ElMessageBox.confirm(`确认删除页面「${row.name}」？其子页面会一并删除，元素将失去页面归属。`, "删除确认", { type: "warning" });
  await platformApi.deleteUiPage(row.id);
  if (selectedPageId.value === row.id) selectedPageId.value = undefined;
  ElMessage.success("页面已删除");
  await Promise.all([loadPages(), loadElements()]);
};

const openElement = (row?: UiElement) => {
  Object.assign(elementForm, {
    id: row?.id,
    suite: row?.suite || suiteFilter.value,
    page_node: row?.page_node || selectedPageId.value,
    name: row?.name || "",
    locator_type: row?.locator_type || "css",
    selector: row?.selector || "",
    description: row?.description || "",
    is_active: row?.is_active ?? true,
  });
  elementDialog.value = true;
};

const openValidate = (row: UiElement) => {
  validatingElement.value = row;
  validateForm.url = pages.value.find((page) => page.id === row.page_node)?.path || "";
  validateForm.browser = "chromium";
  validateResult.value = undefined;
  validateDialog.value = true;
};

const validateElement = async () => {
  if (!validatingElement.value || !validateForm.url.trim()) {
    ElMessage.warning("请填写页面 URL");
    return;
  }
  validating.value = true;
  try {
    const { data } = await platformApi.validateUiElement(validatingElement.value.id, {
      url: validateForm.url.trim(),
      browser: validateForm.browser,
      headless: true,
      timeout_ms: 30000,
    });
    validateResult.value = data;
    if (data.passed) ElMessage.success("定位器验证通过");
    else ElMessage.warning("定位器未命中可见元素");
  } finally {
    validating.value = false;
  }
};

const saveElement = async () => {
  if (!elementForm.suite || !elementForm.name.trim() || !elementForm.selector.trim()) {
    ElMessage.warning("套件、元素名称和定位表达式不能为空");
    return;
  }
  const payload = {
    suite: elementForm.suite,
    page_node: elementForm.page_node,
    page: pages.value.find((page) => page.id === elementForm.page_node)?.name || "",
    name: elementForm.name.trim(),
    locator_type: elementForm.locator_type,
    selector: elementForm.selector.trim(),
    description: elementForm.description,
    is_active: elementForm.is_active,
  };
  if (elementForm.id) await platformApi.updateUiElement(elementForm.id, payload);
  else await platformApi.createUiElement(payload);
  ElMessage.success("定位元素已保存");
  elementDialog.value = false;
  await loadElements();
};

const deleteElement = async (row: UiElement) => {
  await ElMessageBox.confirm(`确认删除定位元素「${row.name}」？`, "删除确认", { type: "warning" });
  await platformApi.deleteUiElement(row.id);
  ElMessage.success("定位元素已删除");
  await loadElements();
};

onMounted(load);
</script>
