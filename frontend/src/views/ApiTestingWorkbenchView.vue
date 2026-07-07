<template>
  <div class="api-v2-shell">
    <aside class="api-v2-tree unified-tree-panel">
      <div class="tree-top unified-tree-head">
        <div class="api-work-title">
          <strong>接口管理</strong>
          <span>{{ apis.length }} 个接口</span>
        </div>
        <el-button size="small" type="primary" @click="openApiForm()">新增</el-button>
      </div>
      <div class="tree-filter">
        <el-input v-model="keyword" placeholder="搜索接口名称或路径" clearable />
      </div>
      <div class="tree-scroll unified-tree-body">
        <section v-for="platform in platformOptions" :key="platform.code" class="tree-platform">
          <button class="platform-title tree-branch-title unified-tree-node" @click="togglePlatform(platform.code)">
            <span v-if="platformHasChildren(platform.code)" class="tree-toggle" :class="{ expanded: isPlatformExpanded(platform.code) }">›</span>
            <span>{{ platform.name }}</span>
          </button>
          <template v-if="isPlatformExpanded(platform.code)">
            <template v-for="module in rootModulesForPlatform(platform.code)" :key="module.id">
              <button class="module-title tree-branch-title unified-tree-node" @click="toggleModule(module.id)">
                <span v-if="moduleHasChildren(platform.code, module.id)" class="tree-toggle" :class="{ expanded: isModuleExpanded(module.id) }">›</span>
                <span>{{ module.name }}</span>
              </button>
              <template v-if="isModuleExpanded(module.id)">
                <button
                  v-for="api in apisByModule(platform.code, module.id)"
                  :key="api.id"
                  class="api-node-v2 unified-tree-node"
                  :class="{ active: selectedApi?.id === api.id }"
                  @click="selectApi(api)"
                >
                  <span class="api-line">
                    <i class="method-tag" :class="api.method">{{ api.method }}</i>
                    <b>{{ api.name }}</b>
                    <em v-if="apiDebugBadge(api)" class="debug-state-badge" :class="apiDebugBadge(api)?.className">{{ apiDebugBadge(api)?.label }}</em>
                  </span>
                </button>
              </template>
            </template>
            <button
              v-for="api in apisWithoutModule(platform.code)"
              :key="api.id"
              class="api-node-v2 unified-tree-node"
              :class="{ active: selectedApi?.id === api.id }"
              @click="selectApi(api)"
            >
              <span class="api-line">
                <i class="method-tag" :class="api.method">{{ api.method }}</i>
                <b>{{ api.name }}</b>
                <em v-if="apiDebugBadge(api)" class="debug-state-badge" :class="apiDebugBadge(api)?.className">{{ apiDebugBadge(api)?.label }}</em>
              </span>
            </button>
          </template>
        </section>
      </div>
    </aside>

    <section v-if="selectedApi" class="api-v2-workbench">
      <header class="api-work-head">
        <div>
          <div class="api-title-row">
            <span class="method-tag" :class="selectedApi.method">{{ selectedApi.method }}</span>
            <el-input
              v-if="editingApiName"
              ref="apiNameInputRef"
              v-model="apiNameDraft"
              class="api-title-input"
              maxlength="20"
              show-word-limit
              @blur="saveApiNameIfChanged"
              @keyup.enter="blurApiNameInput"
              @keyup.esc="cancelApiNameEdit"
            />
            <button v-else class="api-title-name-button" type="button" title="点击编辑接口名称" @click="startApiNameEdit">
              <span>{{ selectedApi.name }}</span>
            </button>
            <el-dropdown trigger="click" popper-class="api-status-dropdown" :disabled="savingApiStatus" @command="saveApiStatus">
              <button class="api-status-button" type="button" title="点击编辑接口状态">
                <span class="badge" :class="statusBadgeClass(designForm.status)">{{ statusText(designForm.status) }}</span>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-for="item in apiStatusOptions" :key="item.value" :command="item.value">
                    <span class="badge" :class="statusBadgeClass(item.value)">{{ item.label }}</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div class="api-meta-row">
            <span class="api-meta-pill">{{ platformName(selectedApi.platform) }}</span>
            <span class="api-meta-pill">{{ moduleName(selectedApi.module) }}</span>
            <span class="api-path-pill"><b>路由</b><code>{{ selectedApi.path }}</code></span>
          </div>
          <div class="api-url-card">
            <span>当前环境 URL</span>
            <code>{{ resolvedRequestUrl }}</code>
          </div>
        </div>
        <div class="api-head-actions">
          <el-button @click="goCasePage">测试用例</el-button>
          <el-button type="primary" :loading="savingApi" @click="saveCurrentApi">保存</el-button>
          <el-button :loading="sending" @click="sendDebug">发送</el-button>
        </div>
      </header>

      <el-tabs v-model="activeTab" class="api-work-tabs">
        <el-tab-pane label="调试" name="debug">
          <div class="debug-grid-v2">
            <section class="v2-card">
              <div class="request-line-v2">
                <el-select v-model="debugForm.method" style="width: 110px">
                  <el-option v-for="item in methods" :key="item" :label="item" :value="item" />
                </el-select>
                <el-input v-model="debugForm.path" />
                <el-select v-model="debugForm.environment" placeholder="环境" clearable style="width: 160px">
                  <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
                </el-select>
              </div>
              <div class="resolved-url-box">
                <span>实际请求地址</span>
                <code>{{ resolvedRequestUrl }}</code>
              </div>
              <el-tabs v-model="debugReqTab" class="request-tabs">
                <el-tab-pane label="Params" name="params"><KeyValueEditor v-model="paramsRows" /></el-tab-pane>
                <el-tab-pane label="Headers" name="headers"><KeyValueEditor v-model="headerRows" /></el-tab-pane>
                <el-tab-pane label="Body" name="body">
                  <div class="body-editor-toolbar">
                    <el-button size="small" @click="formatBody">格式化</el-button>
                  </div>
                  <el-input v-model="bodyText" type="textarea" :rows="10" placeholder='{"name":"demo"}' />
                </el-tab-pane>
                <el-tab-pane label="Auth" name="auth">
                  <div class="inline-form">
                    <el-select v-model="authType"><el-option label="不使用认证" value="none" /><el-option label="Bearer 令牌" value="bearer" /></el-select>
                    <el-input v-model="authToken" placeholder="{{token}}" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="Tests" name="tests">
                  <div class="assertion-editor">
                    <div class="assertion-editor-head">
                      <strong>可视化断言</strong>
                      <el-button size="small" type="primary" @click="addAssertion">新增断言</el-button>
                    </div>
                    <div class="assertion-editor-table">
                      <div class="assertion-row assertion-row-head">
                        <span>断言类型</span>
                        <span>目标字段</span>
                        <span>操作符</span>
                        <span>期望值</span>
                        <span>操作</span>
                      </div>
                      <div v-for="(assertion, index) in assertionRows" :key="assertion.uid" class="assertion-row">
                        <el-select v-model="assertion.type" @change="normalizeAssertion(assertion)">
                          <el-option label="状态码" value="status_code" />
                          <el-option label="响应时间" value="response_time" />
                          <el-option label="响应 Header" value="header" />
                          <el-option label="JSONPath" value="json_path" />
                          <el-option label="Body 包含" value="body_contains" />
                        </el-select>
                        <el-input v-model="assertion.key" :disabled="!needsAssertionKey(assertion.type)" :placeholder="assertionKeyPlaceholder(assertion.type)" />
                        <el-select v-model="assertion.operator">
                          <el-option label="等于" value="eq" />
                          <el-option label="不等于" value="ne" />
                          <el-option label="包含" value="contains" />
                          <el-option label="存在" value="exists" />
                          <el-option label="小于" value="lt" />
                          <el-option label="大于" value="gt" />
                        </el-select>
                        <el-input v-model="assertion.expected" :disabled="assertion.operator === 'exists'" placeholder="期望值" />
                        <el-button link class="danger-link" @click="removeAssertion(index)">删除</el-button>
                      </div>
                    </div>
                    <el-empty v-if="!assertionRows.length" description="暂无断言，点击新增断言开始配置" />
                  </div>
                </el-tab-pane>
              </el-tabs>
            </section>
            <section class="v2-card response-card-v2">
              <div class="response-meta">
                <strong>响应结果</strong>
                <div class="response-meta-actions">
                  <el-button v-if="debugResult" size="small" plain :loading="savingApi" @click="saveDebugResponseExample">沉淀为响应示例</el-button>
                  <span v-if="debugResult" :class="responseStatusClass">{{ debugResult.response?.status_code }} · {{ debugResult.response?.elapsed_ms }}ms</span>
                </div>
              </div>
              <div class="diagnosis-card" :class="diagnosisSeverityClass">
                <div class="diagnosis-main">
                  <span class="diagnosis-icon">{{ diagnosisIconText }}</span>
                  <div>
                    <div class="diagnosis-title">
                      <strong>{{ diagnosisTitle }}</strong>
                      <span v-if="diagnosis.is_environment_issue" class="diagnosis-chip warning">疑似环境问题</span>
                      <span v-if="diagnosis.retry_suggested" class="diagnosis-chip info">建议重试</span>
                    </div>
                    <p>{{ diagnosisSummary }}</p>
                    <p class="diagnosis-advice">{{ diagnosisAdvice }}</p>
                  </div>
                </div>
                <div class="diagnosis-actions">
                  <el-button v-if="diagnosisActionTarget" size="small" type="primary" plain @click="locateDiagnosisTarget">{{ diagnosisActionText }}</el-button>
                  <el-button size="small" plain :disabled="!diagnosisVisible" @click="debugRespTab = 'diagnosis'">查看证据</el-button>
                </div>
              </div>
              <el-tabs v-model="debugRespTab" class="response-tabs">
                <el-tab-pane label="Body" name="body"><pre>{{ responseBodyText }}</pre></el-tab-pane>
                <el-tab-pane label="Headers" name="headers"><pre>{{ responseHeadersText }}</pre></el-tab-pane>
                <el-tab-pane label="诊断" name="diagnosis">
                  <el-empty v-if="!diagnosisVisible" description="当前响应暂无诊断信息" />
                  <div v-else class="diagnosis-evidence">
                    <div v-for="item in diagnosis.evidence || []" :key="item.key" class="diagnosis-evidence-row">
                      <span>{{ item.key }}</span>
                      <code>{{ item.value }}</code>
                    </div>
                  </div>
                </el-tab-pane>
                <el-tab-pane label="断言" name="assertions">
                  <div v-if="debugResult?.assertions?.length" class="assertion-list-v2">
                    <div v-for="item in debugResult.assertions" :key="item.name + item.type" :class="{ passed: item.passed }">
                      <b>{{ item.passed ? "PASS" : "FAIL" }}</b>
                      <span>{{ item.name }}</span>
                      <em>expected {{ item.expected }}, actual {{ item.actual }}</em>
                    </div>
                  </div>
                  <el-empty v-else description="发送请求后查看断言结果" />
                </el-tab-pane>
              </el-tabs>
            </section>
          </div>
        </el-tab-pane>

        <el-tab-pane label="文档" name="preview">
          <div class="api-doc-layout api-tab-scroll">
            <article class="api-doc-article">
              <section class="v2-card api-doc-hero">
                <div class="api-doc-title">
                  <span class="method-tag" :class="debugForm.method">{{ debugForm.method }}</span>
                  <h2>{{ designForm.name || selectedApi.name }}</h2>
                </div>
                <p>{{ designForm.description || "暂无接口描述，可在文档基础信息中补充业务用途、调用边界和注意事项。" }}</p>
                <div class="api-doc-meta">
                  <span>{{ platformName(selectedApi.platform) }} / {{ moduleName(selectedApi.module) }}</span>
                  <span>文档完整度 {{ docCompleteness.score }}%</span>
                  <span>维护人：{{ selectedApi.updated_by_name || selectedApi.created_by_name || "未记录" }}</span>
                  <span>更新：{{ selectedApi.updated_at || "未记录" }}</span>
                </div>
              </section>

              <section id="doc-basic" class="v2-card api-doc-section">
                <div class="doc-section-head">
                  <div>
                    <strong>基础信息</strong>
                  </div>
                  <span>可复制给开发/前端/测试评审</span>
                </div>
                <div class="doc-basic-grid">
                  <div><span>请求方式</span><b><i class="method-tag" :class="debugForm.method">{{ debugForm.method }}</i></b></div>
                  <div><span>请求路径</span><code>{{ debugForm.path || selectedApi.path }}</code></div>
                  <div><span>鉴权方式</span><b>{{ authType === "bearer" ? "Bearer Token" : "无" }}</b></div>
                  <div>
                    <span>接口状态</span>
                    <b>
                      <el-dropdown trigger="click" popper-class="api-status-dropdown" :disabled="savingApiStatus" @command="saveApiStatus">
                        <button class="api-status-button doc-status-button" type="button" title="点击编辑接口状态">
                          <em class="badge" :class="statusBadgeClass(designForm.status)">{{ statusText(designForm.status) }}</em>
                        </button>
                        <template #dropdown>
                          <el-dropdown-menu>
                            <el-dropdown-item v-for="item in apiStatusOptions" :key="item.value" :command="item.value">
                              <span class="badge" :class="statusBadgeClass(item.value)">{{ item.label }}</span>
                            </el-dropdown-item>
                          </el-dropdown-menu>
                        </template>
                      </el-dropdown>
                    </b>
                  </div>
                  <div class="full doc-editable-row" @click="startBusinessDescriptionEdit">
                    <span>业务说明</span>
                    <el-input
                      v-if="editingBusinessDescription"
                      v-model="designForm.description"
                      type="textarea"
                      :rows="4"
                      placeholder="补充接口业务用途、调用前置条件、关键边界和注意事项"
                      @click.stop
                    />
                    <p v-else>{{ designForm.description || "暂无业务说明，点击此区域补充" }}</p>
                  </div>
                </div>
              </section>

              <section id="doc-request" class="v2-card api-doc-section">
                <div class="doc-section-head">
                  <div>
                    <strong>请求说明</strong>
                  </div>
                  <el-button size="small" plain @click="copyCurlCommand">复制 Curl</el-button>
                </div>
                <div class="doc-sub-head">
                  <strong>Headers / Query Params</strong>
                  <span>敏感值已脱敏</span>
                </div>
                <div class="doc-table-wrap">
                  <table class="doc-data-table api-doc-param-table">
                    <thead><tr><th>位置</th><th>参数</th><th>类型</th><th>必填</th><th>示例</th><th>说明</th></tr></thead>
                    <tbody>
                      <tr v-for="row in requestDesignDocRows.filter((item) => item.scope !== 'Body')" :key="row.scope + row.key">
                        <td>{{ row.scope }}</td>
                        <td>{{ row.key }}</td>
                        <td>{{ row.type }}</td>
                        <td>{{ row.required }}</td>
                        <td>{{ row.value }}</td>
                        <td>{{ row.description || "暂无说明" }}</td>
                      </tr>
                    </tbody>
                  </table>
                  <el-empty v-if="!requestDesignDocRows.filter((item) => item.scope !== 'Body').length" description="暂无 Header / Query 参数" />
                </div>
                <div class="doc-code-title">
                  <strong>请求 Body</strong>
                  <span>JSON</span>
                </div>
                <pre class="api-doc-code full">{{ formattedBodyText }}</pre>
              </section>

              <section id="doc-response" class="v2-card api-doc-section">
                <div class="doc-section-head">
                  <div>
                    <strong>响应说明</strong>
                  </div>
                  <el-button size="small" plain :disabled="!debugResult" :loading="savingApi" @click="saveDebugResponseExample">从调试响应更新</el-button>
                </div>
                <div class="api-doc-response-grid">
                  <div>
                    <div class="doc-code-title">
                      <strong>成功响应</strong>
                      <span>{{ activeResponseStatusCode }} OK</span>
                    </div>
                    <pre class="api-doc-code">{{ responseExampleText }}</pre>
                  </div>
                  <div>
                    <div class="doc-code-title">
                      <strong>响应字段</strong>
                      <span>字段说明</span>
                    </div>
                    <div class="doc-table-wrap">
                      <table class="doc-data-table api-doc-field-table">
                        <thead><tr><th>字段</th><th>类型</th><th>说明</th></tr></thead>
                        <tbody>
                          <tr v-for="row in responseFieldRows" :key="row.key">
                            <td>{{ row.key }}</td>
                            <td>{{ row.type }}</td>
                            <td>{{ row.description || "暂无说明" }}</td>
                          </tr>
                        </tbody>
                      </table>
                      <el-empty v-if="!responseFieldRows.length" description="暂无响应字段" />
                    </div>
                  </div>
                </div>
              </section>
            </article>

            <aside class="api-doc-side">
              <section class="v2-card doc-side-card doc-action-card">
                <strong>文档操作</strong>
                <el-button size="small" type="primary" @click="copyApiDocMarkdown">复制 Markdown</el-button>
                <el-button size="small" plain @click="copyCurlCommand">复制 Curl</el-button>
                <el-button size="small" plain @click="activeTab = 'debug'">跳转调试</el-button>
              </section>
              <section class="v2-card doc-side-card">
                <strong>文档目录</strong>
                <a href="#doc-basic">基础信息</a>
                <a href="#doc-request">请求说明</a>
                <a href="#doc-response">响应说明</a>
                <a href="#doc-error">错误码说明</a>
              </section>
              <section class="v2-card doc-side-card">
                <strong>关联资产</strong>
                <div class="doc-side-row"><span>测试用例</span><b>{{ cases.length }}</b></div>
                <div class="doc-side-row"><span>Mock规则</span><b>{{ currentMockCount }} 个</b></div>
                <div class="doc-side-row"><span>最近调试</span><b>{{ latestDebugSummary.status }}</b></div>
                <div class="doc-side-row"><span>最近耗时</span><b>{{ latestDebugSummary.detail }}</b></div>
              </section>
              <section class="v2-card doc-side-card">
                <strong>Mock 地址</strong>
                <code :title="mocks[0] ? mockPublicPath(mocks[0]) : `/mock/${selectedApi.platform.toLowerCase() || 'api'}${debugForm.path || selectedApi.path}`">{{ mocks[0] ? mockPublicPath(mocks[0]) : `/mock/${selectedApi.platform.toLowerCase() || "api"}${debugForm.path || selectedApi.path}` }}</code>
                <el-button size="small" plain :disabled="!mocks[0]" @click="mocks[0] && copyMockUrl(mocks[0])">复制 Mock 地址</el-button>
              </section>
            </aside>
              </div>
        </el-tab-pane>

        <el-tab-pane label="测试用例" name="cases">
          <section class="v2-card">
            <div class="card-toolbar">
              <div>
                <strong>测试用例</strong>
                <span>当前接口下的功能测试场景</span>
              </div>
              <el-button type="primary" @click="openCaseForm()">新增用例</el-button>
            </div>
            <el-table :data="cases" v-loading="caseLoading" stripe>
              <el-table-column prop="name" label="用例名称" min-width="220" />
              <el-table-column prop="method" label="请求方式" width="110"><template #default="{ row }"><span class="method-tag" :class="row.method">{{ row.method }}</span></template></el-table-column>
              <el-table-column prop="priority" label="优先级" width="100" />
              <el-table-column label="状态" width="110"><template #default="{ row }"><span class="badge" :class="caseStatusClass(row.status)">{{ caseStatusText(row.status) }}</span></template></el-table-column>
              <el-table-column prop="created_by_name" label="创建人" width="120" show-overflow-tooltip />
              <el-table-column prop="updated_by_name" label="最后修改人" width="130" show-overflow-tooltip />
              <el-table-column label="操作" width="160" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="openCaseForm(row)">编辑</el-button>
                  <el-button link class="danger-link" @click="removeCase(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="Mock" name="mock">
          <section class="v2-card">
            <div class="card-toolbar">
              <div>
                <strong>Mock</strong>
                <span>维护当前接口的模拟响应</span>
              </div>
              <el-button type="primary" @click="openMockForm()">新增规则</el-button>
            </div>
            <el-table :data="mocks" v-loading="mockLoading" stripe>
              <el-table-column prop="name" label="规则名称" min-width="180" />
              <el-table-column prop="enabled" label="开关" width="90"><template #default="{ row }"><el-switch v-model="row.enabled" @change="toggleMock(row)" /></template></el-table-column>
              <el-table-column prop="status_code" label="状态码" width="100" />
              <el-table-column prop="delay_ms" label="延迟(ms)" width="110" />
              <el-table-column label="Mock 地址" min-width="280"><template #default="{ row }"><code>{{ mockPath(row) }}</code></template></el-table-column>
              <el-table-column label="操作" width="340" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="copyMockUrl(row)">复制地址</el-button>
                  <el-button link type="primary" @click="copyMockProxyUrl(row)">复制代理</el-button>
                  <el-button link type="primary" :loading="runningMockId === row.id" @click="runMock(row)">试运行</el-button>
                  <el-button link type="primary" @click="openMockForm(row)">编辑</el-button>
                  <el-button link class="danger-link" @click="removeMock(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </el-tab-pane>
      </el-tabs>
    </section>

    <section v-else class="api-v2-empty"><el-empty description="请选择左侧接口，或新增接口开始维护" /></section>

    <el-drawer v-model="apiDrawer" title="新增接口" size="560px">
      <el-form label-width="92px" :model="apiForm">
        <el-form-item label="接口名称" required><el-input v-model="apiForm.name" /></el-form-item>
        <el-form-item label="平台" required>
          <el-select v-model="apiForm.platform" style="width: 100%" @change="apiForm.module = undefined">
            <el-option v-for="item in platformOptions" :key="item.code" :label="item.name" :value="item.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="模块" required>
          <el-select v-model="apiForm.module" style="width: 100%">
            <el-option v-for="item in modulesForPlatform(apiForm.platform)" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="请求方式" required>
          <el-select v-model="apiForm.method" style="width: 100%"><el-option v-for="item in methods" :key="item" :label="item" :value="item" /></el-select>
        </el-form-item>
        <el-form-item label="请求路径" required>
          <div class="input-with-action">
            <el-input v-model="apiForm.path" placeholder="/api/orders" />
            <el-button @click="openCurlImport">解析 curl</el-button>
          </div>
        </el-form-item>
        <el-form-item label="状态"><el-select v-model="apiForm.status" style="width: 100%"><el-option label="开发中" value="developing" /><el-option label="已发布" value="released" /><el-option label="已废弃" value="deprecated" /></el-select></el-form-item>
        <el-form-item label="描述"><el-input v-model="apiForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="apiDrawer = false">取消</el-button><el-button type="primary" :loading="savingApi" @click="saveApi">保存</el-button></template>
    </el-drawer>

    <el-dialog v-model="curlDialog" title="解析 curl" width="680px">
      <el-input v-model="curlText" type="textarea" :rows="10" placeholder="粘贴 curl 命令，解析后会填充请求方式、路径、Headers、Query 和 Body" />
      <template #footer>
        <el-button @click="curlDialog = false">取消</el-button>
        <el-button type="primary" @click="applyCurlToApiForm">解析并填充</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="caseDialog" :title="editingCaseId ? '编辑用例' : '新增用例'" width="560px">
      <el-form label-width="92px" :model="caseForm">
        <el-form-item label="用例名称" required><el-input v-model="caseForm.name" /></el-form-item>
        <el-form-item label="优先级"><el-select v-model="caseForm.priority" style="width: 100%"><el-option label="P0" value="P0" /><el-option label="P1" value="P1" /><el-option label="P2" value="P2" /><el-option label="P3" value="P3" /></el-select></el-form-item>
        <el-form-item label="状态"><el-select v-model="caseForm.status" style="width: 100%"><el-option label="草稿" value="draft" /><el-option label="启用" value="active" /><el-option label="停用" value="inactive" /></el-select></el-form-item>
        <el-form-item label="描述"><el-input v-model="caseForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="caseDialog = false">取消</el-button><el-button type="primary" @click="saveCase">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="mockDialog" :title="editingMockId ? '编辑 Mock' : '新增 Mock'" width="620px">
      <el-form label-width="96px" :model="mockForm">
        <el-form-item label="规则名称" required><el-input v-model="mockForm.name" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="mockForm.enabled" /></el-form-item>
        <el-form-item label="状态码"><el-input-number v-model="mockForm.status_code" :min="100" :max="599" /></el-form-item>
        <el-form-item label="延迟"><el-input-number v-model="mockForm.delay_ms" :min="0" :max="60000" /> ms</el-form-item>
        <el-form-item label="响应 Headers"><el-input v-model="mockForm.responseHeadersText" type="textarea" :rows="4" placeholder='[{"enabled":true,"key":"X-Mock","value":"1"}]' /></el-form-item>
        <el-form-item label="响应 Body"><el-input v-model="mockForm.responseBodyText" type="textarea" :rows="8" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="mockDialog = false">取消</el-button><el-button type="primary" :loading="savingMock" @click="saveMock">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="mockRunDialog" title="Mock 试运行结果" width="720px">
      <div class="response-meta">
        <span v-if="mockRunResult" :class="Number(mockRunResult.status || 0) >= 400 ? 'status-error' : 'status-ok'">{{ mockRunResult.status }} · {{ mockRunResult.elapsed_ms }}ms</span>
      </div>
      <el-tabs v-model="mockRunTab">
        <el-tab-pane label="Body" name="body"><pre>{{ mockRunBodyText }}</pre></el-tab-pane>
        <el-tab-pane label="Headers" name="headers"><pre>{{ mockRunHeadersText }}</pre></el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, defineComponent, h, nextTick, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { platformApi, unwrapList } from "@/api/platform";
import { formatBodyText } from "@/utils/bodyFormat";
import { parseCurl } from "@/utils/curl";

interface RowItem { enabled: boolean; key: string; value: string; description?: string }
interface AssertionRow { uid: number; type: string; key: string; operator: string; expected: string }
interface ApiDefinition {
  id: number; name: string; platform: string; module?: number; method: string; path: string; status: string; description?: string;
  headers?: RowItem[]; query_params?: RowItem[]; body?: unknown; body_type?: string; assertions?: unknown[]; auth_config?: Record<string, unknown>;
  body_schema?: unknown; response_example?: unknown; tags?: unknown[]; sort_order?: number; is_active?: boolean; test_case_count?: number; mock_count?: number;
  created_by_name?: string; updated_by_name?: string; created_at?: string; updated_at?: string;
}
interface ApiTestCase { id: number; api: number; name: string; method: string; status: string; priority: string; description?: string }
interface ApiMockRule {
  id: number;
  api: number;
  name: string;
  enabled: boolean;
  status_code: number;
  delay_ms: number;
  headers?: unknown;
  response_body: unknown;
  mock_path?: string;
  mock_public_path?: string;
  mock_proxy_path?: string;
  mock_public_proxy_path?: string;
}
interface MockRunResult { status: number; elapsed_ms: number; headers: Record<string, string>; body: unknown }
interface Diagnosis {
  failure_type?: string;
  failure_label?: string;
  failure_summary?: string;
  failure_advice?: string;
  is_environment_issue?: boolean;
  retry_suggested?: boolean;
  owner_hint?: string;
  severity?: string;
  evidence?: Array<{ key: string; value: unknown }>;
}
interface ApiDebugState { ok: boolean; label: string; className: string; failureType?: string }
interface DocRow { scope: string; key: string; value: string; description?: string; type?: string; required?: string; source?: string }

const KeyValueEditor = defineComponent({
  props: { modelValue: { type: Array, required: true } },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const update = (index: number, key: keyof RowItem, value: string | boolean) => {
      const rows = [...(props.modelValue as RowItem[])];
      rows[index] = { ...rows[index], [key]: value };
      emit("update:modelValue", rows);
    };
    const remove = (index: number) => {
      const rows = [...(props.modelValue as RowItem[])];
      rows.splice(index, 1);
      emit("update:modelValue", rows);
    };
    const add = () => emit("update:modelValue", [...(props.modelValue as RowItem[]), { enabled: true, key: "", value: "", description: "" }]);
    return () => h("div", { class: "kv-editor" }, [
      h("table", { class: "kv-table" }, [
        h("thead", [h("tr", [h("th", ""), h("th", "Key"), h("th", "Value"), h("th", "Description"), h("th", "")])]),
        h("tbody", (props.modelValue as RowItem[]).map((row, index) => h("tr", { key: index }, [
          h("td", [h("input", { type: "checkbox", checked: row.enabled !== false, onChange: (e: Event) => update(index, "enabled", (e.target as HTMLInputElement).checked) })]),
          h("td", [h("input", { value: row.key, onInput: (e: Event) => update(index, "key", (e.target as HTMLInputElement).value) })]),
          h("td", [h("input", { value: row.value, onInput: (e: Event) => update(index, "value", (e.target as HTMLInputElement).value) })]),
          h("td", [h("input", { value: row.description, onInput: (e: Event) => update(index, "description", (e.target as HTMLInputElement).value) })]),
          h("td", [h("button", { class: "kv-remove-row", type: "button", title: "删除字段", onClick: () => remove(index) }, "-")]),
        ]))),
      ]),
      h("button", { class: "add-row", type: "button", onClick: add }, "+ 新增字段"),
    ]);
  },
});

const methods = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const apiStatusOptions = [
  { label: "开发中", value: "developing" },
  { label: "已发布", value: "released" },
  { label: "已废弃", value: "deprecated" },
];
const mockCacheTtlMs = 30_000;
const enabledRows = (rows: RowItem[]) => rows.filter((row) => row.enabled !== false);
const route = useRoute();
const router = useRouter();
const keyword = ref("");
const activeTab = ref("debug");
const debugReqTab = ref("params");
const debugRespTab = ref("body");
const loading = ref(false);
const sending = ref(false);
const savingApi = ref(false);
const savingApiName = ref(false);
const savingApiStatus = ref(false);
const savingMock = ref(false);
const editingApiName = ref(false);
const editingBusinessDescription = ref(false);
const apiNameDraft = ref("");
const apiNameInputRef = ref();
const caseLoading = ref(false);
const mockLoading = ref(false);
const apiDrawer = ref(false);
const caseDialog = ref(false);
const mockDialog = ref(false);
const mockRunDialog = ref(false);
const mockRunTab = ref("body");
const runningMockId = ref<number>();
const curlDialog = ref(false);
const curlText = ref("");
const editingCaseId = ref<number>();
const editingMockId = ref<number>();
const apis = ref<ApiDefinition[]>([]);
const platforms = ref<any[]>([]);
const modules = ref<any[]>([]);
const environments = ref<any[]>([]);
const cases = ref<ApiTestCase[]>([]);
const mocks = ref<ApiMockRule[]>([]);
const mockCache = reactive<Record<number, { data: ApiMockRule[]; loadedAt: number }>>({});
const selectedApi = ref<ApiDefinition>();
const debugResult = ref<any>();
const apiDebugStates = reactive<Record<number, ApiDebugState>>({});
const expandedPlatforms = ref<string[]>([]);
const expandedModules = ref<number[]>([]);
const paramsRows = ref<RowItem[]>([]);
const headerRows = ref<RowItem[]>([]);
const bodyText = ref("{}");
const assertionRows = ref<AssertionRow[]>([]);
const authType = ref("none");
const authToken = ref("");
const debugForm = reactive({ method: "GET", path: "", environment: undefined as number | undefined });
const apiForm = reactive({ name: "", platform: "", module: undefined as number | undefined, method: "GET", path: "", status: "developing", description: "" });
const apiRequestForm = reactive({ headers: [] as RowItem[], query_params: [] as RowItem[], body: {} as unknown, body_type: "none" });
const designForm = reactive({ name: "", path: "", status: "developing", description: "" });
const caseForm = reactive({ name: "", priority: "P1", status: "draft", description: "" });
const mockForm = reactive({ name: "默认 Mock", enabled: false, status_code: 200, delay_ms: 0, responseHeadersText: "[]", responseBodyText: "{}" });
const mockRunResult = ref<MockRunResult>();

const platformCode = (item: any) => item.code?.toUpperCase?.() || item.code || "";
const platformOptions = computed(() => platforms.value.map((item) => ({ ...item, code: platformCode(item) })));
const filteredApis = computed(() => apis.value.filter((item) => !keyword.value || `${item.name} ${item.path}`.toLowerCase().includes(keyword.value.toLowerCase())));
const modulePlatformCode = (module: any) => module.platform || platformCode(platforms.value.find((item) => item.id === module.managed_platform));
const modulesForPlatform = (code: string) => modules.value.filter((item) => modulePlatformCode(item) === code);
const rootModulesForPlatform = (code: string) => modulesForPlatform(code).filter((item) => !item.parent);
const apisByModule = (platform: string, moduleId: number) => filteredApis.value.filter((item) => item.platform === platform && item.module === moduleId);
const apisWithoutModule = (platform: string) => filteredApis.value.filter((item) => item.platform === platform && !item.module);
const childModules = (parentId: number) => modules.value.filter((item) => item.parent === parentId);
const platformHasChildren = (platform: string) => rootModulesForPlatform(platform).length > 0 || apisWithoutModule(platform).length > 0;
const moduleHasChildren = (platform: string, moduleId: number) => childModules(moduleId).length > 0 || apisByModule(platform, moduleId).length > 0;
const isPlatformExpanded = (platform: string) => expandedPlatforms.value.includes(platform);
const isModuleExpanded = (moduleId: number) => expandedModules.value.includes(moduleId);
const togglePlatform = (platform: string) => {
  if (!platformHasChildren(platform)) return;
  expandedPlatforms.value = isPlatformExpanded(platform) ? expandedPlatforms.value.filter((item) => item !== platform) : [...expandedPlatforms.value, platform];
};
const toggleModule = (moduleId: number) => {
  expandedModules.value = isModuleExpanded(moduleId) ? expandedModules.value.filter((item) => item !== moduleId) : [...expandedModules.value, moduleId];
};
const platformName = (code: string) => platformOptions.value.find((item) => item.code === code)?.name || code;
const moduleName = (id?: number) => modules.value.find((item) => item.id === id)?.name || "未分配";
const responseBodyText = computed(() => {
  if (debugResult.value?.response?.body !== undefined) return JSON.stringify(debugResult.value.response.body, null, 2);
  if (debugResult.value?.error) {
    return JSON.stringify(
      {
        error: debugResult.value.error,
        error_detail: debugResult.value.error_detail,
        logs: debugResult.value.logs || [],
      },
      null,
      2,
    );
  }
  return "{}";
});
const responseHeadersText = computed(() => JSON.stringify(debugResult.value?.response?.headers ?? {}, null, 2));
const responseStatusClass = computed(() => (debugResult.value?.ok === false || Number(debugResult.value?.response?.status_code || 0) >= 400 ? "status-error" : "status-ok"));
const diagnosis = computed<Diagnosis>(() => debugResult.value?.diagnosis || {});
const diagnosisVisible = computed(() => Boolean(diagnosis.value.failure_type));
const diagnosisSeverityClass = computed(() => {
  if (!debugResult.value) return "diagnosis-idle";
  if (!diagnosisVisible.value) return "diagnosis-success";
  return `diagnosis-${diagnosis.value.severity || "warning"}`;
});
const diagnosisIconText = computed(() => {
  if (!debugResult.value) return "i";
  return diagnosisVisible.value ? "!" : "✓";
});
const diagnosisTitle = computed(() => {
  if (!debugResult.value) return "调试归因";
  return diagnosis.value.failure_label || "暂无失败归因";
});
const diagnosisSummary = computed(() => {
  if (!debugResult.value) return "发送请求后，平台会在这里展示失败类型、环境风险、建议动作和脱敏诊断证据。";
  return diagnosis.value.failure_summary || "本次请求未命中失败归因规则。";
});
const diagnosisAdvice = computed(() => {
  if (!debugResult.value) return "接口管理是归因主入口，失败后可直接定位到 Auth、Headers、断言或环境前置操作。";
  return diagnosis.value.failure_advice || "如需沉淀为用例，可继续在当前接口工作台维护断言和测试用例。";
});
const diagnosisActionTarget = computed(() => {
  const failureType = diagnosis.value.failure_type;
  if (["auth_error", "pre_request_error"].includes(failureType || "")) return "auth";
  if (failureType === "case_config_error") return "params";
  if (failureType === "assertion_failed") return "tests";
  if (failureType === "request_blocked") return "environment";
  return "";
});
const diagnosisActionText = computed(() => {
  const target = diagnosisActionTarget.value;
  if (target === "auth") return "定位 Auth 配置";
  if (target === "params") return "检查请求配置";
  if (target === "tests") return "定位断言配置";
  if (target === "environment") return "查看环境控制";
  return "";
});
const mockRunBodyText = computed(() => JSON.stringify(mockRunResult.value?.body ?? {}, null, 2));
const mockRunHeadersText = computed(() => JSON.stringify(mockRunResult.value?.headers ?? {}, null, 2));
const currentEnvironment = computed(() => environments.value.find((item) => item.id === debugForm.environment));
const currentPlatformBaseUrl = computed(() => {
  if (!selectedApi.value) return "";
  const urls = currentEnvironment.value?.platform_base_urls || {};
  return urls[selectedApi.value.platform] || urls[selectedApi.value.platform.toLowerCase?.()] || currentEnvironment.value?.base_url || "";
});
const resolvedRequestUrl = computed(() => {
  const path = debugForm.path || selectedApi.value?.path || "";
  if (!path) return currentPlatformBaseUrl.value || "未配置环境地址";
  if (/^https?:\/\//i.test(path)) return path;
  if (!currentPlatformBaseUrl.value) return path;
  return `${currentPlatformBaseUrl.value.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
});
const sensitiveKeyPattern = /(authorization|cookie|token|secret|password|passwd|apikey|api-key)/i;
const maskSensitiveValue = (key: string, value: unknown) => {
  const text = value === undefined || value === null ? "" : String(value);
  if (!sensitiveKeyPattern.test(key)) return text;
  if (!text) return "";
  return text.length <= 6 ? "******" : `${text.slice(0, 3)}******${text.slice(-2)}`;
};
const stringifyDocValue = (value: unknown) => {
  if (value === undefined || value === null) return "";
  if (typeof value === "string") return value;
  try { return JSON.stringify(value); } catch { return String(value); }
};
const currentBody = computed(() => {
  try { return parseJson(bodyText.value, {}); } catch { return {}; }
});
const bodyFieldRows = computed<DocRow[]>(() => {
  const rows: DocRow[] = [];
  const walk = (value: unknown, prefix: string) => {
    if (rows.length >= 20) return;
    if (!value || typeof value !== "object") return;
    Object.entries(value as Record<string, unknown>).forEach(([key, item]) => {
      const path = prefix ? `${prefix}.${key}` : key;
      const isArray = Array.isArray(item);
      const type = isArray ? "array" : item === null ? "null" : typeof item;
      rows.push({ scope: "Body", key: path, value: stringifyDocValue(isArray ? item[0] : item), type });
      if (item && typeof item === "object" && !isArray) walk(item, path);
    });
  };
  walk(currentBody.value, "");
  return rows;
});
const requestDocRows = computed<DocRow[]>(() => {
  const rows: DocRow[] = [];
  enabledRows(paramsRows.value).filter((row) => row.key).forEach((row) => rows.push({ scope: "Query", key: row.key, value: row.value, description: row.description }));
  enabledRows(headerRows.value).filter((row) => row.key).forEach((row) => rows.push({ scope: "Header", key: row.key, value: maskSensitiveValue(row.key, row.value), description: row.description }));
  bodyFieldRows.value.forEach((row) => rows.push({ ...row, description: row.description || "Body 字段" }));
  return rows;
});
const inferDocValueType = (row: DocRow) => {
  if (row.type) return row.type;
  if (row.scope === "Header") return "string";
  const value = row.value;
  if (value === "") return "string";
  if (["true", "false"].includes(value)) return "boolean";
  if (!Number.isNaN(Number(value))) return "number";
  if (/^\[.*\]$/.test(value)) return "array";
  if (/^\{.*\}$/.test(value)) return "object";
  return "string";
};
const inferDocRequired = (row: DocRow) => {
  if (row.required) return row.required;
  if (row.scope === "Header" && /^(authorization|content-type)$/i.test(row.key)) return "是";
  if (row.scope === "Body") return "是";
  return "否";
};
const requestDesignDocRows = computed<DocRow[]>(() =>
  requestDocRows.value.map((row) => ({
    ...row,
    type: inferDocValueType(row),
    required: inferDocRequired(row),
    source: row.source || (row.scope === "Body" ? "body" : "debug"),
  })),
);
const normalizedResponseExample = computed<Record<string, any>>(() => {
  const source = selectedApi.value?.response_example;
  return source && typeof source === "object" && !Array.isArray(source) ? source as Record<string, any> : {};
});
const activeResponseExample = computed(() => {
  const stored = normalizedResponseExample.value.latest || normalizedResponseExample.value.success || normalizedResponseExample.value;
  if (stored && Object.keys(stored).length) return stored;
  return {};
});
const activeResponseStatusCode = computed(() => Number(activeResponseExample.value?.status_code || 200));
const activeResponseBody = computed(() => {
  const example = activeResponseExample.value;
  if (!example || !Object.keys(example).length) return {};
  return example.body !== undefined ? example.body : example;
});
const responseExampleText = computed(() => JSON.stringify(activeResponseBody.value, null, 2));
const responseFieldRows = computed<DocRow[]>(() => {
  const rows: DocRow[] = [];
  const source = activeResponseBody.value;
  const walk = (value: unknown, prefix: string) => {
    if (rows.length >= 16 || !value || typeof value !== "object") return;
    Object.entries(value as Record<string, unknown>).forEach(([key, item]) => {
      if (rows.length >= 16) return;
      const path = prefix ? `${prefix}.${key}` : key;
      const isArray = Array.isArray(item);
      const type = isArray ? "array" : item === null ? "null" : typeof item;
      rows.push({ scope: "Response", key: path, value: stringifyDocValue(isArray ? item[0] : item), type, description: "暂无说明" });
      if (item && typeof item === "object" && !isArray) walk(item, path);
    });
  };
  walk(source, "");
  return rows;
});
const formattedBodyText = computed(() => {
  try { return JSON.stringify(currentBody.value, null, 2); } catch { return bodyText.value || "{}"; }
});
const docCompleteness = computed(() => {
  const items = [
    { key: "name", label: "接口名称", done: Boolean(designForm.name.trim()) },
    { key: "path", label: "请求路径", done: Boolean((debugForm.path || "").trim()) },
    { key: "desc", label: "接口描述", done: Boolean(designForm.description.trim()) },
    { key: "request", label: "请求参数", done: requestDocRows.value.length > 0 },
    { key: "response", label: "响应示例", done: Object.keys(activeResponseExample.value).length > 0 },
    { key: "assertion", label: "断言规则", done: assertionRows.value.length > 0 },
  ];
  const score = Math.round((items.filter((item) => item.done).length / items.length) * 100);
  return { score, items };
});
const latestDebugSummary = computed(() => {
  if (!debugResult.value) return { status: "未调试", detail: "当前页面暂无调试结果" };
  const status = debugResult.value.ok === false || Number(debugResult.value.response?.status_code || 0) >= 400 ? "失败" : "通过";
  return { status, detail: `${debugResult.value.response?.status_code || "-"} · ${debugResult.value.response?.elapsed_ms || 0}ms` };
});
const currentMockCount = computed(() => {
  if (!selectedApi.value) return 0;
  return mockCache[selectedApi.value.id]?.data.length ?? selectedApi.value.mock_count ?? mocks.value.length;
});

function parseJson(text: string, fallback: unknown) {
  if (!text.trim()) return fallback;
  try { return JSON.parse(text); } catch { throw new Error("JSON 格式不正确"); }
}
const copyText = async (text: string, message: string) => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
  } else {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
  }
  ElMessage.success(message);
};
const formatBody = () => {
  bodyText.value = formatBodyText(bodyText.value);
  ElMessage.success("Body 已格式化");
};
const createAssertion = (input?: any): AssertionRow => ({
  uid: Date.now() + Math.floor(Math.random() * 10000),
  type: input?.type || "status_code",
  key: input?.key || input?.path || "",
  operator: input?.operator || input?.op || "eq",
  expected: input?.expected === undefined || input?.expected === null ? "" : String(input.expected),
});
const normalizeAssertion = (assertion: AssertionRow) => {
  if (!needsAssertionKey(assertion.type)) assertion.key = "";
  if (assertion.type === "body_contains") assertion.operator = "contains";
  if (assertion.type === "response_time" && !["lt", "gt", "eq", "ne"].includes(assertion.operator)) assertion.operator = "lt";
};
const needsAssertionKey = (type: string) => ["header", "json_path"].includes(type);
const assertionKeyPlaceholder = (type: string) => {
  if (type === "header") return "例如 Content-Type";
  if (type === "json_path") return "例如 $.data.id";
  return "无需填写";
};
const addAssertion = () => assertionRows.value.push(createAssertion());
const removeAssertion = (index: number) => assertionRows.value.splice(index, 1);
const buildAssertions = () =>
  assertionRows.value.map((item) => ({
    name: assertionName(item),
    type: item.type,
    operator: item.operator,
    expected: item.operator === "exists" ? "" : item.expected,
    ...(item.type === "header" ? { key: item.key } : {}),
    ...(item.type === "json_path" ? { path: item.key } : {}),
  }));
const assertionName = (item: AssertionRow) => {
  const label = { status_code: "状态码", response_time: "响应时间", header: "Header", json_path: "JSONPath", body_contains: "Body 包含" }[item.type] || item.type;
  return item.key ? `${label} ${item.key}` : label;
};
const statusText = (status: string) => ({ developing: "开发中", released: "已发布", deprecated: "已废弃" }[status] || status);
const statusBadgeClass = (status: string) => (status === "released" ? "badge-success" : status === "deprecated" ? "badge-danger" : "badge-warning");
const caseStatusText = (status: string) => ({ draft: "草稿", active: "启用", inactive: "停用" }[status] || status);
const caseStatusClass = (status: string) => (status === "active" ? "badge-success" : status === "inactive" ? "badge-danger" : "badge-warning");
const buildCurlCommand = () => {
  const command = [`curl -X ${debugForm.method}`, `"${resolvedRequestUrl.value}"`];
  enabledRows(headerRows.value)
    .filter((row) => row.key)
    .forEach((row) => command.push(`-H "${row.key}: ${maskSensitiveValue(row.key, row.value)}"`));
  if (!["GET", "HEAD"].includes(debugForm.method) && bodyText.value.trim() && bodyText.value.trim() !== "{}") {
    command.push(`--data '${formattedBodyText.value.replace(/'/g, "'\\''")}'`);
  }
  return command.join(" \\\n  ");
};
const buildApiDocMarkdown = () => {
  const requestTable = requestDocRows.value.length
    ? requestDocRows.value.map((row) => `| ${row.scope} | ${row.key} | ${row.value || "-"} | ${row.description || "-"} |`).join("\n")
    : "| - | - | - | - |";
  return [
    `# ${designForm.name || selectedApi.value?.name || "未命名接口"}`,
    "",
    `- 请求方式：${debugForm.method}`,
    `- 请求路径：${debugForm.path || selectedApi.value?.path || ""}`,
    `- 所属模块：${selectedApi.value ? `${platformName(selectedApi.value.platform)} / ${moduleName(selectedApi.value.module)}` : ""}`,
    `- 状态：${statusText(designForm.status)}`,
    "",
    designForm.description || "暂无接口描述。",
    "",
    "## 请求参数",
    "",
    "| 位置 | 字段 | 示例值 | 说明 |",
    "| --- | --- | --- | --- |",
    requestTable,
    "",
    "## 请求 Body",
    "",
    "```json",
    formattedBodyText.value,
    "```",
    "",
    "## 响应示例",
    "",
    "```json",
    responseExampleText.value,
    "```",
  ].join("\n");
};
const copyApiDocMarkdown = () => copyText(buildApiDocMarkdown(), "Markdown 文档已复制");
const copyCurlCommand = () => copyText(buildCurlCommand(), "cURL 已复制");
const apiDebugBadge = (api: ApiDefinition) => apiDebugStates[api.id];
const updateApiDebugState = (apiId: number, result: any) => {
  const itemDiagnosis: Diagnosis = result?.diagnosis || {};
  const statusCode = Number(result?.response?.status_code || 0);
  const ok = Boolean(result?.ok) && statusCode < 400 && !itemDiagnosis.failure_type;
  apiDebugStates[apiId] = ok
    ? { ok: true, label: "最近通过", className: "passed" }
    : {
        ok: false,
        label: itemDiagnosis.failure_label || result?.error_type || "最近失败",
        className: itemDiagnosis.is_environment_issue ? "warning" : "failed",
        failureType: itemDiagnosis.failure_type,
      };
};
const locateDiagnosisTarget = () => {
  const target = diagnosisActionTarget.value;
  if (target === "auth") {
    debugReqTab.value = "auth";
    ElMessage.info("已定位到 Auth 配置，请检查认证方式和 Token 引用");
  } else if (target === "params") {
    debugReqTab.value = "params";
    ElMessage.info("已定位到请求配置，请检查 URL、Params、Headers 和 Body");
  } else if (target === "tests") {
    debugReqTab.value = "tests";
    ElMessage.info("已定位到断言配置，请对比实际响应和预期值");
  } else if (target === "environment") {
    ElMessage.info("请在环境管理中检查当前环境的请求控制配置");
  }
};

const load = async () => {
  loading.value = true;
  try {
    const [apiResp, platformData, moduleData, envData] = await Promise.all([platformApi.apiDefinitions(), platformApi.cachedPlatforms(), platformApi.cachedApiModules(), platformApi.cachedEnvironments()]);
    apis.value = unwrapList<ApiDefinition>(apiResp.data);
    platforms.value = unwrapList(platformData as any);
    modules.value = unwrapList(moduleData as any);
    environments.value = unwrapList(envData as any);
    expandedPlatforms.value = platformOptions.value.filter((item) => platformHasChildren(item.code)).map((item) => item.code);
    expandedModules.value = modules.value.filter((item) => moduleHasChildren(modulePlatformCode(item), item.id)).map((item) => item.id);
    debugForm.environment = environments.value.find((item) => item.is_default)?.id || environments.value[0]?.id;
    const queryApi = Number(route.query.apiId);
    const next = apis.value.find((item) => item.id === queryApi) || apis.value[0];
    if (route.query.tab === "debug") activeTab.value = "debug";
    if (next) await selectApi(next);
  } catch (error: any) {
    ElMessage.error(error?.message || "接口管理页面加载失败，请稍后重试");
  } finally {
    loading.value = false;
  }
};
const loadCases = async () => {
  if (!selectedApi.value) return;
  caseLoading.value = true;
  try {
    const { data } = await platformApi.apiTestCases({ api: selectedApi.value.id });
    cases.value = unwrapList<ApiTestCase>(data);
  } catch (error: any) {
    cases.value = [];
    ElMessage.error(error?.message || "测试用例加载失败");
  } finally {
    caseLoading.value = false;
  }
};
const syncMocksFromCache = (apiId: number) => {
  const cached = mockCache[apiId];
  mocks.value = cached ? [...cached.data] : [];
};
const invalidateMockCache = (apiId?: number) => {
  if (apiId) delete mockCache[apiId];
};
const loadMocks = async (options: { force?: boolean } = {}) => {
  if (!selectedApi.value) return;
  const apiId = selectedApi.value.id;
  const cached = mockCache[apiId];
  if (!options.force && cached && Date.now() - cached.loadedAt < mockCacheTtlMs) {
    mocks.value = [...cached.data];
    return;
  }
  mockLoading.value = true;
  try {
    const { data } = await platformApi.apiMockRules({ api: apiId });
    if (selectedApi.value?.id !== apiId) return;
    const rows = unwrapList<ApiMockRule>(data);
    mockCache[apiId] = { data: rows, loadedAt: Date.now() };
    mocks.value = [...rows];
  } catch (error: any) {
    if (selectedApi.value?.id === apiId) mocks.value = [];
    ElMessage.error(error?.message || "Mock 规则加载失败");
  } finally {
    if (selectedApi.value?.id === apiId) mockLoading.value = false;
  }
};
const selectApi = async (api: ApiDefinition) => {
  editingApiName.value = false;
  editingBusinessDescription.value = false;
  apiNameDraft.value = api.name || "";
  selectedApi.value = api;
  debugResult.value = undefined;
  mockLoading.value = false;
  syncMocksFromCache(api.id);
  debugForm.method = api.method;
  debugForm.path = api.path;
  paramsRows.value = api.query_params?.length ? api.query_params : [{ enabled: true, key: "", value: "", description: "" }];
  headerRows.value = api.headers?.length ? api.headers : [{ enabled: true, key: "Content-Type", value: "application/json", description: "" }];
  bodyText.value = JSON.stringify(api.body || {}, null, 2);
  assertionRows.value = (api.assertions?.length ? api.assertions : [{ type: "status_code", operator: "eq", expected: 200 }]).map(createAssertion);
  authType.value = String(api.auth_config?.type || "none");
  authToken.value = String(api.auth_config?.token || "");
  Object.assign(designForm, { name: api.name, path: api.path, status: api.status, description: api.description || "" });
  await router.replace({ path: "/api-testing/apis", query: { apiId: api.id } });
  await loadCases();
  if (activeTab.value === "mock") await loadMocks();
};
const goCasePage = () => {
  if (!selectedApi.value) return;
  router.push({ path: "/api-testing/cases", query: { apiId: selectedApi.value.id } });
};
const startApiNameEdit = async () => {
  if (!selectedApi.value) return;
  apiNameDraft.value = selectedApi.value.name || "";
  editingApiName.value = true;
  await nextTick();
  apiNameInputRef.value?.focus?.();
};
const blurApiNameInput = () => {
  apiNameInputRef.value?.blur?.();
};
const cancelApiNameEdit = () => {
  editingApiName.value = false;
  apiNameDraft.value = selectedApi.value?.name || "";
};
const startBusinessDescriptionEdit = () => {
  editingBusinessDescription.value = true;
};
const applySavedApi = (api: ApiDefinition) => {
  selectedApi.value = api;
  Object.assign(designForm, { name: api.name, path: api.path, status: api.status, description: api.description || "" });
  debugForm.method = api.method;
  debugForm.path = api.path;
  const index = apis.value.findIndex((item) => item.id === api.id);
  if (index >= 0) apis.value[index] = api;
};
const saveApiNameIfChanged = async () => {
  if (!selectedApi.value || savingApiName.value) return;
  const nextName = apiNameDraft.value.trim();
  if (!nextName) {
    ElMessage.warning("接口名称必填");
    apiNameDraft.value = selectedApi.value.name || "";
    editingApiName.value = false;
    return;
  }
  if (nextName.length > 20) {
    ElMessage.warning("接口名称不能超过20个字");
    return;
  }
  if (nextName === selectedApi.value.name) {
    editingApiName.value = false;
    return;
  }
  const payload = buildCurrentApiPayload();
  if (!payload) return;
  savingApiName.value = true;
  try {
    const { data } = await platformApi.updateApiDefinition(selectedApi.value.id, { ...payload, name: nextName });
    ElMessage.success("接口名称已保存");
    applySavedApi(data);
    editingApiName.value = false;
  } finally {
    savingApiName.value = false;
  }
};
const saveApiStatus = async (nextStatus: string) => {
  if (!selectedApi.value || savingApiStatus.value) return;
  const previousStatus = selectedApi.value.status;
  if (nextStatus === previousStatus) return;
  const payload = buildCurrentApiPayload();
  if (!payload) return;
  savingApiStatus.value = true;
  try {
    const { data } = await platformApi.updateApiDefinition(selectedApi.value.id, { ...payload, status: nextStatus });
    ElMessage.success("接口状态已更新");
    applySavedApi(data);
  } catch (error: any) {
    designForm.status = previousStatus;
    ElMessage.error(error?.message || "接口状态更新失败");
  } finally {
    savingApiStatus.value = false;
  }
};
const openApiForm = () => {
  Object.assign(apiForm, {
    name: "",
    platform: platformOptions.value[0]?.code || "ERP",
    module: undefined,
    method: "GET",
    path: "",
    status: "developing",
    description: "",
  });
  Object.assign(apiRequestForm, {
    headers: [],
    query_params: [],
    body: {},
    body_type: "none",
  });
  apiDrawer.value = true;
};
const openCurlImport = () => {
  curlText.value = "";
  curlDialog.value = true;
};
const applyCurlToApiForm = () => {
  try {
    const parsed = parseCurl(curlText.value);
    apiForm.method = parsed.method;
    apiForm.path = parsed.path;
    if (!apiForm.name) apiForm.name = `${parsed.method} ${parsed.path.split("?")[0]}`;
    apiRequestForm.headers = parsed.headers;
    apiRequestForm.query_params = parsed.query_params;
    apiRequestForm.body = parsed.body;
    apiRequestForm.body_type = parsed.bodyText && parsed.bodyText !== "{}" ? "json" : "none";
    curlDialog.value = false;
    ElMessage.success("curl 已解析");
  } catch (error: any) {
    ElMessage.error(error?.message || "curl 解析失败");
  }
};
const normalizePath = (value: string) => {
  const trimmed = value.trim();
  if (!trimmed) return "";
  try {
    const url = new URL(trimmed);
    return `${url.pathname}${url.search || ""}`;
  } catch {
    return trimmed;
  }
};
const saveApi = async () => {
  if (!apiForm.name.trim() || !apiForm.path.trim() || !apiForm.platform || !apiForm.module) {
    ElMessage.warning("接口名称、平台、模块和请求路径必填");
    return;
  }
  savingApi.value = true;
  try {
    const nextPath = normalizePath(apiForm.path);
    const { data: existingResp } = await platformApi.apiDefinitions({
      platform: apiForm.platform,
      method: apiForm.method,
      search: nextPath,
    });
    const duplicated = unwrapList<ApiDefinition>(existingResp).find(
      (item) =>
        item.platform === apiForm.platform &&
        item.method === apiForm.method &&
        normalizePath(item.path) === nextPath,
    );
    if (duplicated) {
      ElMessage.warning(`接口已存在：${duplicated.name}`);
      return;
    }
    const payload = { ...apiForm, path: nextPath, ...apiRequestForm, is_active: true };
    const { data } = await platformApi.createApiDefinition(payload);
    ElMessage.success("接口已保存");
    apiDrawer.value = false;
    await load();
    selectApi(data);
  } finally {
    savingApi.value = false;
  }
};
// 当前接口保存以主页面的设计区和调试区为准，避免弹窗状态与页面状态割裂。
const buildCurrentApiPayload = () => {
  if (!selectedApi.value) return undefined;
  const nextPath = normalizePath(debugForm.path || designForm.path);
  return {
    name: designForm.name.trim(),
    platform: selectedApi.value.platform,
    module: selectedApi.value.module,
    method: debugForm.method,
    path: nextPath,
    status: designForm.status,
    description: designForm.description,
    tags: selectedApi.value.tags || [],
    headers: headerRows.value,
    query_params: paramsRows.value,
    body_type: (bodyText.value.trim() && bodyText.value.trim() !== "{}") ? "json" : "none",
    body: parseJson(bodyText.value, {}),
    body_schema: selectedApi.value.body_schema || {},
    auth_config: { type: authType.value, token: authToken.value },
    assertions: buildAssertions(),
    response_example: selectedApi.value.response_example || {},
    sort_order: selectedApi.value.sort_order || 0,
    is_active: selectedApi.value.is_active !== false,
  };
};
const buildResponseExamplePayload = () => {
  const response = debugResult.value?.response;
  if (!response) return undefined;
  const item = {
    status_code: response.status_code,
    elapsed_ms: response.elapsed_ms,
    headers: response.headers || {},
    body: response.body,
    saved_at: new Date().toISOString(),
    source: "debug",
  };
  const previous = normalizedResponseExample.value;
  const errors = Array.isArray(previous.errors) ? previous.errors : [];
  if (Number(response.status_code || 0) >= 400 || debugResult.value?.ok === false) {
    return { ...previous, latest: item, errors: [item, ...errors].slice(0, 5) };
  }
  return { ...previous, latest: item, success: item };
};
const saveDebugResponseExample = async () => {
  if (!selectedApi.value) return;
  const responseExample = buildResponseExamplePayload();
  if (!responseExample) {
    ElMessage.warning("请先执行调试，获取响应结果后再沉淀示例");
    return;
  }
  const payload = buildCurrentApiPayload();
  if (!payload) return;
  savingApi.value = true;
  try {
    const { data } = await platformApi.updateApiDefinition(selectedApi.value.id, { ...payload, response_example: responseExample });
    selectedApi.value = data;
    const index = apis.value.findIndex((item) => item.id === data.id);
    if (index >= 0) apis.value[index] = data;
    ElMessage.success("响应示例已沉淀到文档");
  } catch (error: any) {
    ElMessage.error(error?.message || "响应示例保存失败");
  } finally {
    savingApi.value = false;
  }
};
const saveCurrentApi = async () => {
  if (!selectedApi.value) return;
  const payload = buildCurrentApiPayload();
  if (!payload) return;
  if (!payload.name || !payload.path) {
    ElMessage.warning("接口名称和请求路径必填");
    return;
  }
  savingApi.value = true;
  try {
    const { data } = await platformApi.updateApiDefinition(selectedApi.value.id, payload);
    ElMessage.success("接口已保存");
    applySavedApi(data);
    editingBusinessDescription.value = false;
  } finally {
    savingApi.value = false;
  }
};
const sendDebug = async () => {
  if (!selectedApi.value) return;
  sending.value = true;
  try {
    const { data } = await platformApi.debugApi({
      method: debugForm.method,
      path: debugForm.path,
      platform: selectedApi.value.platform,
      module: selectedApi.value.module,
      environment: debugForm.environment,
      query_params: enabledRows(paramsRows.value),
      headers: enabledRows(headerRows.value),
      body: parseJson(bodyText.value, {}),
      auth_config: { type: authType.value, token: authToken.value },
      assertions: buildAssertions(),
    });
    debugResult.value = data;
    updateApiDebugState(selectedApi.value.id, data);
    debugRespTab.value = "body";
  } catch (error: any) {
    const data = error?.response?.data;
    if (data && typeof data === "object" && data.ok === false) {
      debugResult.value = data;
      updateApiDebugState(selectedApi.value.id, data);
      debugRespTab.value = "body";
      ElMessage.warning(data.error || error?.message || "请求执行失败");
      return;
    }
    ElMessage.error(error?.message || "请求失败");
  } finally {
    sending.value = false;
  }
};
const openCaseForm = (row?: ApiTestCase) => {
  editingCaseId.value = row?.id;
  Object.assign(caseForm, { name: row?.name || "", priority: row?.priority || "P1", status: row?.status || "draft", description: row?.description || "" });
  caseDialog.value = true;
};
const saveCase = async () => {
  if (!selectedApi.value || !caseForm.name.trim()) return;
  const payload = { ...caseForm, api: selectedApi.value.id, is_active: caseForm.status !== "inactive" };
  if (editingCaseId.value) await platformApi.updateApiTestCase(editingCaseId.value, payload);
  else await platformApi.createApiTestCase(payload);
  ElMessage.success("用例已保存");
  caseDialog.value = false;
  await loadCases();
};
const removeCase = async (row: ApiTestCase) => {
  await ElMessageBox.confirm(`确认删除用例“${row.name}”？`, "删除确认", { type: "warning" });
  await platformApi.deleteApiTestCase(row.id);
  await loadCases();
};
const mockPath = (row: ApiMockRule) => row.mock_path || `/mock/api/${row.api}/${row.id}/`;
const mockPublicPath = (row: ApiMockRule) => row.mock_public_path || mockPath(row);
const mockProxyPath = (row: ApiMockRule) => row.mock_proxy_path || mockPath(row);
const mockPublicProxyPath = (row: ApiMockRule) => row.mock_public_proxy_path || mockProxyPath(row);
const mockUrl = (row: ApiMockRule) => `${window.location.origin}${mockPublicPath(row)}`;
const mockProxyUrl = (row: ApiMockRule) => `${window.location.origin}${mockPublicProxyPath(row)}`;
const copyMockUrl = async (row: ApiMockRule) => {
  await navigator.clipboard.writeText(mockUrl(row));
  ElMessage.success("Mock 地址已复制");
};
const copyMockProxyUrl = async (row: ApiMockRule) => {
  await navigator.clipboard.writeText(mockProxyUrl(row));
  ElMessage.success("Mock 代理地址已复制");
};
const runMock = async (row: ApiMockRule) => {
  runningMockId.value = row.id;
  const started = performance.now();
  try {
    const response = await fetch(mockPath(row), {
      method: selectedApi.value?.method || "GET",
      headers: { "Content-Type": "application/json" },
      body: ["GET", "HEAD"].includes(selectedApi.value?.method || "GET") ? undefined : "{}",
    });
    const contentType = response.headers.get("content-type") || "";
    const text = await response.text();
    let body: unknown = text;
    if (contentType.includes("application/json") && text) {
      try { body = JSON.parse(text); } catch { body = text; }
    }
    mockRunResult.value = {
      status: response.status,
      elapsed_ms: Math.round(performance.now() - started),
      headers: Object.fromEntries(response.headers.entries()),
      body,
    };
    mockRunTab.value = "body";
    mockRunDialog.value = true;
  } catch (error: any) {
    ElMessage.error(error?.message || "Mock 试运行失败");
  } finally {
    runningMockId.value = undefined;
  }
};
const openMockForm = (row?: ApiMockRule) => {
  editingMockId.value = row?.id;
  Object.assign(mockForm, {
    name: row?.name || "默认 Mock",
    enabled: row?.enabled || false,
    status_code: row?.status_code || 200,
    delay_ms: row?.delay_ms || 0,
    responseHeadersText: JSON.stringify(row?.headers || [], null, 2),
    responseBodyText: JSON.stringify(row?.response_body || {}, null, 2),
  });
  mockDialog.value = true;
};
const saveMock = async () => {
  if (!selectedApi.value) return;
  if (!mockForm.name.trim()) {
    ElMessage.warning("请填写 Mock 规则名称");
    return;
  }
  let responseBody: unknown;
  let responseHeaders: unknown;
  try {
    responseHeaders = parseJson(mockForm.responseHeadersText, []);
    responseBody = parseJson(mockForm.responseBodyText, {});
  } catch (error: any) {
    ElMessage.warning(error?.message || "Mock JSON 格式不正确");
    return;
  }
  savingMock.value = true;
  try {
    const payload = {
      api: selectedApi.value.id,
      name: mockForm.name.trim(),
      enabled: mockForm.enabled,
      status_code: mockForm.status_code,
      delay_ms: mockForm.delay_ms,
      headers: responseHeaders,
      response_body: responseBody,
    };
    if (editingMockId.value) await platformApi.updateApiMockRule(editingMockId.value, payload);
    else await platformApi.createApiMockRule(payload);
    ElMessage.success("Mock 规则已保存");
    mockDialog.value = false;
    invalidateMockCache(selectedApi.value.id);
    await loadMocks({ force: true });
  } catch (error: any) {
    ElMessage.error(error?.message || "Mock 规则保存失败");
  } finally {
    savingMock.value = false;
  }
};
const toggleMock = async (row: ApiMockRule) => {
  try {
    await platformApi.updateApiMockRule(row.id, { enabled: row.enabled });
    if (selectedApi.value) {
      mockCache[selectedApi.value.id] = { data: [...mocks.value], loadedAt: Date.now() };
    }
  } catch (error: any) {
    row.enabled = !row.enabled;
    ElMessage.error(error?.message || "Mock 规则状态更新失败");
  }
};
const removeMock = async (row: ApiMockRule) => {
  await ElMessageBox.confirm(`确认删除 Mock“${row.name}”？`, "删除确认", { type: "warning" });
  await platformApi.deleteApiMockRule(row.id);
  invalidateMockCache(selectedApi.value?.id);
  await loadMocks({ force: true });
};

watch(activeTab, (tab) => {
  if (tab === "cases") loadCases();
  if (tab === "mock") loadMocks();
});
onMounted(load);
</script>

<style scoped>
.debug-state-badge {
  display: inline-flex;
  align-items: center;
  max-width: 72px;
  height: 18px;
  margin-left: auto;
  padding: 0 6px;
  border-radius: 999px;
  font-size: 11px;
  font-style: normal;
  font-weight: 600;
  line-height: 18px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.debug-state-badge.passed {
  color: var(--el-color-success);
  background: var(--el-color-success-light-9);
}
.debug-state-badge.warning {
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-9);
}
.debug-state-badge.failed {
  color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
}
.diagnosis-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin: 12px 0;
  padding: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
}
.diagnosis-warning {
  border-color: var(--el-color-warning-light-5);
  background: var(--el-color-warning-light-9);
}
.diagnosis-error {
  border-color: var(--el-color-danger-light-5);
  background: var(--el-color-danger-light-9);
}
.diagnosis-info {
  border-color: var(--el-color-primary-light-5);
  background: var(--el-color-primary-light-9);
}
.diagnosis-idle {
  border-color: var(--el-color-primary-light-7);
  background: var(--el-color-primary-light-9);
}
.diagnosis-success {
  border-color: var(--el-color-success-light-6);
  background: var(--el-color-success-light-9);
}
.diagnosis-main {
  display: flex;
  align-items: flex-start;
  min-width: 0;
  gap: 10px;
}
.diagnosis-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: #fff;
  background: var(--el-color-warning);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  font-weight: 700;
}
.diagnosis-error .diagnosis-icon {
  background: var(--el-color-danger);
}
.diagnosis-info .diagnosis-icon {
  background: var(--el-color-primary);
}
.diagnosis-idle .diagnosis-icon {
  background: var(--el-color-primary);
}
.diagnosis-success .diagnosis-icon {
  background: var(--el-color-success);
}
.diagnosis-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.diagnosis-title strong {
  color: var(--el-text-color-primary);
}
.diagnosis-card p {
  margin: 5px 0 0;
  color: var(--el-text-color-regular);
  line-height: 1.55;
}
.diagnosis-advice {
  color: var(--el-text-color-secondary) !important;
}
.diagnosis-chip {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.diagnosis-chip.warning {
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-8);
}
.diagnosis-chip.info {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-8);
}
.diagnosis-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.diagnosis-evidence {
  display: grid;
  gap: 8px;
}
.diagnosis-evidence-row {
  display: grid;
  grid-template-columns: 140px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 8px 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}
.diagnosis-evidence-row span {
  color: var(--el-text-color-secondary);
  font-weight: 600;
}
.diagnosis-evidence-row code {
  color: var(--el-text-color-primary);
  white-space: pre-wrap;
  word-break: break-all;
}
@media (max-width: 1100px) {
  .diagnosis-card {
    flex-direction: column;
  }
  .diagnosis-actions {
    justify-content: flex-start;
  }
}
</style>
