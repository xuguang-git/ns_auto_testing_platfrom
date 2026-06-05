# NS 自动化测试平台

当前仓库是 NS 自动化测试平台开发工程，已推进到 v1.1。平台目标是支撑接口资产维护、测试计划编排、执行中心触发、执行记录与报告查看的自动化测试闭环。

## 技术栈

- 后端：Python、Django、Django REST Framework
- 前端：Vue 3、Vite、TypeScript、Pinia、Vue Router、Element Plus
- 调度与队列：Celery、Redis、django-celery-beat
- 数据库：MySQL

## 目录结构

```text
backend/
  apps/
    projects/      项目、平台、环境、环境变量
    api_testing/   接口模块、接口定义、测试集、场景、步骤
    test_runs/     测试计划、执行记录、步骤结果
    ui_testing/    UI 自动化预留模型
    scheduling/    定时调度预留模型
  config/          Django 配置、路由、Celery 入口
frontend/
  src/
    api/           Axios 封装与平台 API
    layouts/       管理台布局与 v1.1 侧边栏
    router/        前端路由
    stores/        Pinia 状态
    styles/        全局样式与设计系统适配
    views/         业务页面入口
```

## 本地启动

启动 Redis 兼容服务（Windows 本机已解包到 D 盘时）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-redis.ps1
```

后端：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:18080
```

Celery Worker：

```powershell
cd backend
celery -A config worker --pool=solo --loglevel=info
```

或使用项目脚本后台启动：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-celery-worker.ps1
```

Celery Beat：

```bash
cd backend
.venv\Scripts\activate
celery -A config beat -l info
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## v1.1 功能范围

- 平台维护：新增、编辑、删除平台，支持启用状态、排序、模块数和接口数展示。
- 模块管理：按平台维护接口模块，支持目录树筛选、模块 CRUD、级联删除确认。
- 接口管理：原“测试用例”更名为“接口管理”，用于维护接口定义、方法、路径、状态、标签和请求配置。
- 测试计划：新增计划列表与详情页，支持计划 CRUD、克隆、关联平台、模块和接口。
- 执行中心：支持从测试计划页跳转并自动选中计划，保留执行配置、触发执行、轮询结果、日志和步骤详情展示。
- 环境管理：维护环境、Base URL、平台变量和敏感变量。
- 测试报告：展示执行摘要、步骤结果，并支持 HTML 报告导出。
- 侧边栏导航：重构为“平台管理 / 接口自动化 / UI 自动化 / 配置管理”分组；UI 自动化入口预留到 v1.2。

## 已提供的 API

- `GET/POST /api/v1/platforms/`
- `GET/PATCH/DELETE /api/v1/platforms/{id}/`
- `GET/POST /api/v1/projects/`
- `GET/POST /api/v1/environments/`
- `GET/POST /api/v1/environment-variables/`
- `GET/POST /api/v1/api-modules/`
- `GET/PATCH/DELETE /api/v1/api-modules/{id}/`
- `GET/POST /api/v1/api-definitions/`
- `POST /api/v1/api-definitions/debug/`
- `GET/POST /api/v1/api-suites/`
- `GET/POST /api/v1/api-scenarios/`
- `GET/POST /api/v1/api-steps/`
- `GET/POST /api/v1/api-cases/`
- `GET/POST /api/v1/ui-suites/`
- `GET/POST /api/v1/ui-cases/`
- `GET/POST /api/v1/test-plans/`
- `GET/PATCH/DELETE /api/v1/test-plans/{id}/`
- `POST /api/v1/test-plans/{id}/run/`
- `GET /api/v1/test-runs/`
- `GET /api/v1/test-runs/{id}/html-report/`

## 当前实现说明

- v1.1 已新增数据库迁移，首次拉取后需要执行 `python manage.py migrate`。
- 平台管理已由数据库模型承载，但部分旧接口字段仍保留 `ERP/WMS/PDA/CLIENT` 兼容值。
- 测试计划已支持 `platform_ref`、`module_ids`、`api_ids`，前端可维护计划与接口关联。
- 执行器当前主要沿用 v1.0 的 `api_suites/api_scenarios/api_steps` 执行逻辑；`api_ids` 已作为计划编排数据保存，但尚未完全驱动执行器生成步骤。

## 后续迭代建议

1. 执行器 v1.1 闭环完善：让 `test_plans.api_ids` 直接生成执行步骤，打通“测试计划 -> 接口列表 -> 执行记录 -> 报告”的真实链路。
2. 平台与模块数据迁移：提供初始化脚本，将旧的 `ERP/WMS/PDA/CLIENT` 硬编码平台和旧模块数据迁移到 `Platform` 与新版 `ApiModule`。
3. 接口管理升级：增加平台/模块联动筛选、批量导入、批量移动模块、启停状态批量操作和接口复制。
4. 测试计划规则增强：补充计划状态流转、计划失效标记、模块变更时自动重算接口列表、删除平台/模块后的计划处理策略。
5. 执行中心增强：支持运行时覆盖并发数、超时、失败策略、重试次数、优先级筛选，并将这些参数传入后端执行任务。
6. 报告增强：展示请求、响应、断言、提取器、变量上下文、失败原因定位、趋势统计和平台/模块维度汇总。
7. 定时调度落地：基于测试计划创建 Cron/Webhook 任务，支持启停、执行历史、失败通知和重试策略。
8. 权限与审计：补充用户角色、平台/项目级权限、操作审计日志和删除审批能力。
9. UI 自动化 v1.2：明确 Playwright/Selenium 方案，设计用例库、录制回放、截图/视频报告和执行器资源隔离。
10. 工程质量：补充后端单元测试、前端组件测试、API 契约测试，并优化 Vite 大 chunk 拆包。
