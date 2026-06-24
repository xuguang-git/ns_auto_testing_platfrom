<template>
  <div class="database-page">
    <PageHeader title="数据库管理" description="维护测试数据源使用的数据库连接和只读查询数据源。" />

    <el-tabs v-model="activeTab" class="database-tabs">
      <el-tab-pane label="连接配置" name="connections">
        <section class="database-toolbar">
          <el-select v-model="connectionEnvFilter" clearable placeholder="环境" style="width: 180px">
            <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
          </el-select>
          <el-input v-model="connectionKeyword" clearable placeholder="搜索连接名称/主机/库名" style="width: 280px" />
          <el-button @click="load">刷新</el-button>
          <el-button type="primary" @click="openConnectionDialog()">新增连接</el-button>
        </section>

        <section class="database-card">
          <el-table :data="filteredConnections" v-loading="loading" stripe height="100%">
            <el-table-column prop="name" label="连接名称" min-width="150" />
            <el-table-column prop="environment_name" label="环境" min-width="120" />
            <el-table-column label="类型" width="110"><template #default="{ row }">{{ databaseTypeText(row.db_type) }}</template></el-table-column>
            <el-table-column prop="host" label="主机" min-width="180" show-overflow-tooltip />
            <el-table-column prop="port" label="端口" width="90" />
            <el-table-column prop="database_name" label="库名" min-width="130" show-overflow-tooltip />
            <el-table-column prop="username" label="账号" min-width="120" show-overflow-tooltip />
            <el-table-column label="密码" width="80"><template #default="{ row }">{{ row.has_password ? '已配置' : '未配置' }}</template></el-table-column>
            <el-table-column label="检测" width="100"><template #default="{ row }"><span class="badge" :class="checkBadge(row.last_check_status)">{{ checkStatusText(row.last_check_status) }}</span></template></el-table-column>
            <el-table-column label="状态" width="90"><template #default="{ row }"><span class="badge" :class="row.is_active ? 'badge-success' : 'badge-warning'">{{ row.is_active ? '启用' : '停用' }}</span></template></el-table-column>
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" :loading="checkingId === row.id" @click="checkConnection(row)">检测</el-button>
                <el-button link type="primary" @click="openConnectionDialog(row)">编辑</el-button>
                <el-button link class="danger-link" @click="removeConnection(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </el-tab-pane>

      <el-tab-pane label="查询数据源" name="sources">
        <section class="database-toolbar">
          <el-select v-model="sourceConnectionFilter" clearable placeholder="数据库连接" style="width: 220px">
            <el-option v-for="connection in connections" :key="connection.id" :label="connection.name" :value="connection.id" />
          </el-select>
          <el-input v-model="sourceKeyword" clearable placeholder="搜索数据源名称 / SQL" style="width: 300px" />
          <el-button @click="load">刷新</el-button>
          <el-button type="primary" @click="openSourceDialog()">新增数据源</el-button>
        </section>

        <section class="database-card">
          <el-table :data="filteredSources" v-loading="loading" stripe height="100%">
            <el-table-column prop="name" label="数据源名称" min-width="160" />
            <el-table-column prop="database_connection_name" label="连接" min-width="150" />
            <el-table-column prop="environment_name" label="环境" min-width="120" />
            <el-table-column label="SQL" min-width="320" show-overflow-tooltip><template #default="{ row }"><span class="inline-code">{{ row.sql }}</span></template></el-table-column>
            <el-table-column label="提取变量" min-width="180" show-overflow-tooltip><template #default="{ row }">{{ extractorText(row.extractors) }}</template></el-table-column>
            <el-table-column prop="run_count" label="运行次数" width="100" />
            <el-table-column label="状态" width="90"><template #default="{ row }"><span class="badge" :class="row.is_active ? 'badge-success' : 'badge-warning'">{{ row.is_active ? '启用' : '停用' }}</span></template></el-table-column>
            <el-table-column label="操作" width="250" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" :disabled="!row.is_active" :loading="runningSourceId === row.id" @click="runSource(row)">试运行</el-button>
                <el-button link type="primary" @click="openSourceDialog(row)">编辑</el-button>
                <el-button link class="danger-link" @click="removeSource(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="connectionDialog" :title="connectionForm.id ? '编辑数据库连接' : '新增数据库连接'" width="680px">
      <el-form :model="connectionForm" label-width="100px">
        <el-form-item label="连接名称" required><el-input v-model="connectionForm.name" /></el-form-item>
        <el-form-item label="环境" required><el-select v-model="connectionForm.environment" style="width: 100%"><el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" /></el-select></el-form-item>
        <el-form-item label="数据库类型" required><el-select v-model="connectionForm.db_type" style="width: 100%"><el-option label="MySQL" value="mysql" /><el-option label="PostgreSQL" value="postgresql" /></el-select></el-form-item>
        <el-form-item label="主机" required><el-input v-model="connectionForm.host" placeholder="127.0.0.1" /></el-form-item>
        <el-form-item label="端口" required><el-input-number v-model="connectionForm.port" :min="1" :max="65535" controls-position="right" /></el-form-item>
        <el-form-item label="库名" required><el-input v-model="connectionForm.database_name" /></el-form-item>
        <el-form-item label="账号" required><el-input v-model="connectionForm.username" /></el-form-item>
        <el-form-item label="密码" :required="!connectionForm.id"><el-input v-model="connectionForm.password" type="password" show-password :placeholder="connectionForm.id ? '留空则不修改密码' : '请输入数据库密码'" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="connectionForm.is_active" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="connectionForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="connectionDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveConnection">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="sourceDialog" :title="sourceForm.id ? '编辑查询数据源' : '新增查询数据源'" width="760px">
      <el-form :model="sourceForm" label-width="110px">
        <el-form-item label="数据源名称" required><el-input v-model="sourceForm.name" placeholder="查询订单号" /></el-form-item>
        <el-form-item label="数据库连接" required><el-select v-model="sourceForm.database_connection" filterable style="width: 100%" @change="syncSourceEnvironment"><el-option v-for="connection in activeConnections" :key="connection.id" :label="`${connection.name} / ${connection.environment_name}`" :value="connection.id" /></el-select></el-form-item>
        <el-form-item label="SQL" required><el-input v-model="sourceForm.sql" type="textarea" :rows="8" placeholder="SELECT id, order_no FROM orders WHERE user_id = '{{user_id}}'" /></el-form-item>
        <el-alert v-if="sqlWarning" :title="sqlWarning" type="warning" show-icon :closable="false" class="sql-alert" />
        <el-form-item label="提取规则"><div class="extractor-editor"><div class="extractor-row extractor-head"><span>变量名</span><span>列名</span><span>模式</span><span>行号</span><span></span></div><div v-for="(extractor, index) in sourceForm.extractors" :key="extractor.uid" class="extractor-row"><el-input v-model="extractor.name" placeholder="order_id" /><el-input v-model="extractor.column" placeholder="id" /><el-select v-model="extractor.mode"><el-option label="首行/指定行" value="first" /><el-option label="整列数组" value="column" /></el-select><el-input-number v-model="extractor.row" :min="0" :max="999" controls-position="right" /><el-button link class="danger-link" @click="removeExtractor(index)">删除</el-button></div><el-button size="small" @click="addExtractor">新增规则</el-button></div></el-form-item>
        <el-form-item label="启用"><el-switch v-model="sourceForm.is_active" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="sourceForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="sourceDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveSource">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="runDialog" title="查询数据源试运行" width="760px"><div v-if="runResult" class="source-run-result"><el-descriptions :column="3" border><el-descriptions-item label="行数">{{ runResult.row_count }}</el-descriptions-item><el-descriptions-item label="提取变量" :span="2">{{ Object.keys(runResult.variables || {}).length }}</el-descriptions-item></el-descriptions><h4>Variables</h4><pre>{{ JSON.stringify(runResult.variables || {}, null, 2) }}</pre><h4>Rows Preview</h4><pre>{{ JSON.stringify((runResult.rows || []).slice(0, 20), null, 2) }}</pre></div></el-dialog>

    <el-dialog v-model="runVariableDialog" title="试运行数据源" width="680px"><div class="run-variable-editor"><p class="muted-text">SQL 中可使用 &#123;&#123; variable_name &#125;&#125; 引用变量；场景执行时会自动使用前序步骤上下文变量。</p><div class="variable-row variable-head"><span>变量名</span><span>变量值</span><span></span></div><div v-for="(item, index) in runVariables" :key="item.uid" class="variable-row"><el-input v-model="item.key" placeholder="order_no" /><el-input v-model="item.value" placeholder="变量值" /><el-button link class="danger-link" @click="removeRunVariable(index)">删除</el-button></div><el-button size="small" @click="addRunVariable">新增变量</el-button></div><template #footer><el-button @click="runVariableDialog = false">取消</el-button><el-button type="primary" :loading="runningSourceId === pendingRunSource?.id" @click="confirmRunSource">运行</el-button></template></el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import { platformApi, unwrapList } from "@/api/platform";
import PageHeader from "@/components/PageHeader.vue";

interface ExtractorForm { uid: number; name: string; column: string; mode: string; row: number }
interface RunVariableForm { uid: number; key: string; value: string }

const activeTab = ref("connections");
const loading = ref(false);
const saving = ref(false);
const checkingId = ref<number>();
const runningSourceId = ref<number>();
const environments = ref<any[]>([]);
const connections = ref<any[]>([]);
const sources = ref<any[]>([]);
const connectionKeyword = ref("");
const connectionEnvFilter = ref<number>();
const sourceKeyword = ref("");
const sourceConnectionFilter = ref<number>();
const connectionDialog = ref(false);
const sourceDialog = ref(false);
const runDialog = ref(false);
const runVariableDialog = ref(false);
const runResult = ref<any>();
const pendingRunSource = ref<any>();
const runVariables = ref<RunVariableForm[]>([]);

const connectionForm = reactive({ id: undefined as number | undefined, name: "", environment: undefined as number | undefined, db_type: "postgresql", host: "", port: 5432, database_name: "", username: "", password: "", description: "", is_active: true });
const sourceForm = reactive({ id: undefined as number | undefined, name: "", environment: undefined as number | undefined, database_connection: undefined as number | undefined, sql: "", extractors: [] as ExtractorForm[], description: "", is_active: true });

const filteredConnections = computed(() => connections.value.filter((item) => {
  const text = `${item.name} ${item.host} ${item.database_name}`.toLowerCase();
  return (!connectionKeyword.value || text.includes(connectionKeyword.value.toLowerCase())) && (!connectionEnvFilter.value || item.environment === connectionEnvFilter.value);
}));
const filteredSources = computed(() => sources.value.filter((item) => {
  const text = `${item.name} ${item.sql}`.toLowerCase();
  return (!sourceKeyword.value || text.includes(sourceKeyword.value.toLowerCase())) && (!sourceConnectionFilter.value || item.database_connection === sourceConnectionFilter.value);
}));
const activeConnections = computed(() => connections.value.filter((item) => item.is_active));
const sqlWarning = computed(() => {
  const sql = sourceForm.sql.trim();
  if (!sql) return "";
  const normalized = sql.replace(/;+\s*$/, "");
  if (!/^(select|with)\b/i.test(normalized)) return "第一版仅允许 SELECT 查询，新增、修改、删除、DDL、存储过程都会在执行前拦截。";
  if (/(;.*\S|--|#|\/\*)/.test(sql)) return "暂不允许多语句和 SQL 注释。";
  if (/\b(insert|update|delete|drop|alter|truncate|create|replace|merge|grant|revoke|call|exec|execute|load|outfile|dumpfile|set|use|lock|unlock)\b/i.test(normalized)) return "检测到非只读关键字，后端会拒绝执行。";
  return "";
});

const checkStatusText = (status: string) => ({ success: "成功", failed: "失败", unchecked: "未检测" }[status] || "未检测");
const checkBadge = (status: string) => status === "success" ? "badge-success" : status === "failed" ? "badge-danger" : "badge-warning";
const databaseTypeText = (type: string) => ({ mysql: "MySQL", postgresql: "PostgreSQL" }[type] || type || "-");
const extractorText = (extractors: any[] = []) => extractors.map((item) => `${item.name}<-${item.column || item.path}`).join(", ") || "-";

const load = async () => {
  loading.value = true;
  try {
    const [envResp, connectionResp, sourceResp] = await Promise.all([platformApi.environments(), platformApi.databaseConnections(), platformApi.testDataSources()]);
    environments.value = unwrapList(envResp.data);
    connections.value = unwrapList(connectionResp.data);
    sources.value = unwrapList(sourceResp.data);
  } finally {
    loading.value = false;
  }
};

const openConnectionDialog = (row?: any) => {
  Object.assign(connectionForm, { id: row?.id, name: row?.name || "", environment: row?.environment || environments.value[0]?.id, db_type: row?.db_type || "postgresql", host: row?.host || "", port: Number(row?.port || (row?.db_type === "mysql" ? 3306 : 5432)), database_name: row?.database_name || "", username: row?.username || "", password: "", description: row?.description || "", is_active: row?.is_active ?? true });
  connectionDialog.value = true;
};

const saveConnection = async () => {
  if (!connectionForm.name.trim() || !connectionForm.environment || !connectionForm.host.trim() || !connectionForm.database_name.trim() || !connectionForm.username.trim() || (!connectionForm.id && !connectionForm.password.trim())) {
    ElMessage.warning("请填写连接名称、环境、主机、库名、账号和密码");
    return;
  }
  saving.value = true;
  try {
    const payload: Record<string, unknown> = { name: connectionForm.name.trim(), environment: connectionForm.environment, db_type: connectionForm.db_type, host: connectionForm.host.trim(), port: connectionForm.port, database_name: connectionForm.database_name.trim(), username: connectionForm.username.trim(), description: connectionForm.description, is_active: connectionForm.is_active };
    if (connectionForm.password.trim()) payload.password = connectionForm.password.trim();
    if (connectionForm.id) await platformApi.updateDatabaseConnection(connectionForm.id, payload);
    else await platformApi.createDatabaseConnection(payload);
    ElMessage.success("数据库连接已保存");
    connectionDialog.value = false;
    await load();
  } finally {
    saving.value = false;
  }
};

const checkConnection = async (row: any) => {
  checkingId.value = row.id;
  try {
    const { data } = await platformApi.checkDatabaseConnection(row.id);
    ElMessage[data.ok ? "success" : "warning"](data.message || (data.ok ? "连接成功" : "连接失败"));
    await load();
  } finally {
    checkingId.value = undefined;
  }
};

const removeConnection = async (row: any) => {
  await ElMessageBox.confirm(`确认删除数据库连接「${row.name}」？`, "删除确认", { type: "warning" });
  await platformApi.deleteDatabaseConnection(row.id);
  ElMessage.success("数据库连接已删除");
  await load();
};

const syncSourceEnvironment = () => { sourceForm.environment = connections.value.find((item) => item.id === sourceForm.database_connection)?.environment; };
const addExtractor = () => sourceForm.extractors.push({ uid: Date.now() + Math.floor(Math.random() * 10000), name: "", column: "", mode: "first", row: 0 });
const removeExtractor = (index: number) => sourceForm.extractors.splice(index, 1);
const addRunVariable = () => runVariables.value.push({ uid: Date.now() + Math.floor(Math.random() * 10000), key: "", value: "" });
const removeRunVariable = (index: number) => runVariables.value.splice(index, 1);

const openSourceDialog = (row?: any) => {
  Object.assign(sourceForm, { id: row?.id, name: row?.name || "", environment: row?.environment || undefined, database_connection: row?.database_connection || activeConnections.value[0]?.id, sql: row?.sql || "", extractors: (row?.extractors?.length ? row.extractors : [{ name: "", column: "", mode: "first", row: 0 }]).map((item: any) => ({ uid: Date.now() + Math.floor(Math.random() * 10000), name: item.name || "", column: item.column || item.path || "", mode: item.mode || "first", row: Number(item.row || 0) })), description: row?.description || "", is_active: row?.is_active ?? true });
  syncSourceEnvironment();
  sourceDialog.value = true;
};
const buildExtractors = () => sourceForm.extractors.filter((item) => item.name.trim() && item.column.trim()).map((item) => ({ name: item.name.trim(), column: item.column.trim(), mode: item.mode, row: item.row || 0 }));

const saveSource = async () => {
  if (!sourceForm.name.trim() || !sourceForm.database_connection || !sourceForm.sql.trim()) { ElMessage.warning("请填写数据源名称、数据库连接和 SQL"); return; }
  if (sqlWarning.value) { ElMessage.warning(sqlWarning.value); return; }
  saving.value = true;
  try {
    syncSourceEnvironment();
    const payload = { name: sourceForm.name.trim(), environment: sourceForm.environment, database_connection: sourceForm.database_connection, source_type: "database_query", sql: sourceForm.sql, extractors: buildExtractors(), description: sourceForm.description, is_active: sourceForm.is_active };
    if (sourceForm.id) await platformApi.updateTestDataSource(sourceForm.id, payload);
    else await platformApi.createTestDataSource(payload);
    ElMessage.success("查询数据源已保存");
    sourceDialog.value = false;
    await load();
  } finally { saving.value = false; }
};

const removeSource = async (row: any) => { await ElMessageBox.confirm(`确认删除查询数据源「${row.name}」？`, "删除确认", { type: "warning" }); await platformApi.deleteTestDataSource(row.id); ElMessage.success("查询数据源已删除"); await load(); };
const extractSqlVariables = (sql: string) => { const names: string[] = []; const pattern = /{{\s*([a-zA-Z0-9_.-]+)\s*}}/g; let match: RegExpExecArray | null; while ((match = pattern.exec(sql || ""))) { if (!names.includes(match[1])) names.push(match[1]); } return names; };
const runSource = async (row: any) => { pendingRunSource.value = row; runVariables.value = extractSqlVariables(row.sql).map((key) => ({ uid: Date.now() + Math.floor(Math.random() * 10000), key, value: "" })); if (!runVariables.value.length) addRunVariable(); runVariableDialog.value = true; };
const buildRunVariables = () => runVariables.value.reduce((result, item) => { const key = item.key.trim(); if (key) result[key] = item.value; return result; }, {} as Record<string, string>);
const confirmRunSource = async () => { const row = pendingRunSource.value; if (!row) return; runningSourceId.value = row.id; try { const { data } = await platformApi.runTestDataSource(row.id, { variables: buildRunVariables() }); runResult.value = data.result; runVariableDialog.value = false; runDialog.value = true; await load(); } catch { } finally { runningSourceId.value = undefined; } };

onMounted(load);
</script>
