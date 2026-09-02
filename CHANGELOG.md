# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式，
版本号遵循语义化版本（SemVer）。

## [Unreleased]

### 夜间质量迭代 ✅
- **正确性**：批量任务更新后 SSE 事件发布缺失（缺 `await`）；并发读 stats 触发快照唯一约束 409（改原子 upsert）；MCP `list_tasks` overdue 分页语义不稳
- **性能**：SSE 长连接不再独占数据库连接池（认证会话提前释放，此前约 10 条连接即耗尽池）
- **安全**：uvicorn 开启 `--proxy-headers`，反代后 IP 级限流恢复按真实客户端 IP；新增账号维度登录慢速限流（5 分钟窗口 10 次失败即 429）
- **时区口径**：新增 `DISPLAY_TIMEZONE`（默认 Asia/Shanghai）——逾期判定、每日快照、燃尽分桶、今日完成数统一按用户日历日，修复 UTC+8 凌晨 0-8 点统计错位
- **前端**：路由参数变化四视图重载；看板批量操作入口恢复；搜索请求序号守卫；SSE 重连定时器泄漏；通知 store 竞态与水位口径
- **测试**：120 → 144 后端用例（跨用户隔离 10 项、里程碑 CRUD、统计端点家族、登录限流），前端 39 → 45

### P4 · 体验增强 ✅
#### P4-1 工时加权进度 ✅
- 任务支持 `estimated_hours`，统计新增 `weighted_progress`（工时加权完成度）；仪表盘卡片与详情页双口径展示

#### P4-2 移动端适配 ✅
- AppLayout 顶栏响应式压缩（≤900px 收品牌名/搜索文案，≤560px 收起搜索）；任务看板与详情页两栏布局折叠单栏

#### P4-3 每日进度快照 ✅
- 读取 stats 时按天沉淀快照（upsert，同日只更新不新增）；新增 `GET /projects/{id}/progress-history`；详情页新增进度趋势图（ProgressTrendChart）

#### P4-4 通知中心（SSE 全局流） ✅
- 后端事件总线新增全局主题（`subscribe_global`/`publish` 扇出到项目+全局双通道）
- `GET /events/stream` 支持省略 `project_id` 订阅全局流；服务端按用户所有权过滤，他人项目事件静默丢弃不泄露存在性
- 全局流认证改为端点内手动校验（Authorization 头优先、?ticket= 兜底）：绕开 slowapi 包装签名与 FastAPI 0.141 参数解析的冲突（此前无凭证请求被误判 422 而非 401）
- 前端 `stores/notifications.ts`：全局 SSE 单例连接（ticket 换取 + 指数退避重连最多 8 次）、50 条去重缓存、已读水位持久化 localStorage
- 前端 `NotificationBell.vue`：顶栏铃铛（未读角标 + 弹层列表 + 相对时间 + 点击跳转对应页面），≤560px 收起与移动端导航策略一致
- AppLayout 登录后自动连接、登出断开；新增 `tests/test_global_events.py`（总线扇出/所有权过滤/401 边界）

### P0 · 修复损坏与半成品功能（核心卖点真正可用）
- **SSE 实时同步修复**：新增 `POST /api/events/ticket`（JWT 换 30s 一次性 ticket），`/events/stream` 支持 `?ticket=` 认证；前端 `useProjectEvents` 改用 `addEventListener('project-update')` + 最大 8 次重试熔断，消除 401 无限重连
- **REST publish 补齐**：`routers/projects.py` / `milestones.py` / `tasks.py` 全部写操作补齐事件广播；`projects.py` 新增 `?status=` 过滤
- **项目编辑/归档/删除 UI**：`ProjectListView` 卡片加操作菜单（编辑/归档/删除）；`ProjectDetailView` hero 加编辑入口；归档筛选
- **里程碑编辑/完成标记**：详情页里程碑时间轴加编辑弹窗 + 「标记完成/取消完成」切换，删除已捕获 cancel rejection
- **小 bug 修复**：`dev_logs.py` no-op `resolved_at` 改 `utcnow()`；`http.ts` 422 array detail 正确渲染；所有 `el-date-picker` 加 `value-format="YYYY-MM-DD"`；Element Plus `zh-cn` locale；4 处 `ElMessageBox` cancel 加 try/catch；`ApiKeysView` 空状态/日期格式化/clipboard fallback/closable alert

### P1 · 核心体验补强 ✅
#### P1-1 全局仪表盘 ✅
- 后端 `GET /api/overview` 聚合接口（项目进度卡片 / 逾期汇总 / 近期 DevLog / 活跃会话 / 今日完成数），单次查询避免 N+1
- 前端 `DashboardView.vue` + 路由 `/dashboard`；AppLayout「进度」导航死链修复 → 指向 `/dashboard`

#### P1-2 任务看板增强 ✅
- 后端 `list_tasks` 新增 `priority` / `milestone_id` / `search`（ILIKE 模糊） / `sort`（created_desc / due_asc / due_desc / priority_desc）参数
- 前端搜索框 + 状态/优先级/逾期筛选表单 + 排序下拉（客户端派生，无需重新请求）
- 任务卡片多选框 + 批量操作弹窗（批量改状态/优先级/里程碑）
- 乐观更新（本地 patch + 失败回滚）；拖拽 done→todo 重置 progress
- `ElCheckbox` / `ElSwitch` / `ElSelect` 组件注册

#### P1-3 依赖关系编辑 UI ✅
- 任务卡片新增「依赖」按钮，卡片内以标签展示前置依赖任务名
- 依赖管理弹窗：候选任务搜索过滤 + 多选保存（`Promise.all` 增删差量）
- 已完成任务在候选列表中标注；乐观更新本地 `depends_on` 列表

#### P1-4 DevLog 页补强 ✅
- 新建/编辑 DevLog 弹窗（类型/标题/内容/状态/严重度/关联任务/git ref），状态与严重度字段按类型条件显示
- 列表分页：el-pagination + 差量去重加载
- 关联任务标签可点击跳转至任务看板
- 开发汇报弹窗：日期范围筛选重新生成 + 下载 `.md`
- 「标记完成」确认弹窗带条目标题，防误触

#### P1-5 全局设施 ✅
- AppLayout 接入 `GlobalSearch`，搜索按钮 + `⌘K`/`Ctrl+K` 快捷键聚焦
- 新增 404 页面（`NotFoundView`），未知路由不再静默重定向
- 路由 `afterEach` 设置 `document.title`（中文页面标题映射）
- DevLog 列表接入 `el-pagination`
- TaskBoard 新增任务清单 Markdown 导出（按状态分节 + 勾选框）

### P2 · 后端健壮性与安全加固 ✅
- **P2-1 MCP 补齐 `list_task_dependencies`**（34→35 个工具）：返回前置依赖 id/名称/状态/进度，AI 工具可判断任务可否开工；e2e 测试覆盖；skills 文档同步
- **P2-2 MCP list 工具分页与搜索对齐 REST**：`list_projects` +status 过滤与 offset/limit；`list_tasks` +search（ILIKE）与 SQL 级 overdue 过滤（与 `is_overdue` 派生口径一致）；`list_dev_logs` +offset；均带上限防全表拉取
- **P2-3 JWT sub 改 user id**：签发 `sub=user_id + username`，decode 兼容层使旧 token（sub=username）继续有效，下游零改动；SSE ticket 同步；typ 隔离保持
- **已在 0.2.0 覆盖的 P2 原始项**（审计确认）：登录/API Key 限流、注册 IntegrityError→409、MCP 枚举校验一致化、API Key 哈希存储、请求耗时日志

### P3 · 测试与运维 ✅
- **CI 全绿**（此前每次 push 均失败）：GitHub Actions 后端（ruff + pytest + alembic 离线迁移校验）与前端（vue-tsc + 生产构建 + 体积红线）全流程通过
- **ruff 规则固化**：pyproject 显式 select（E4/E7/E9/F/I/B/UP/RUF），排除 `alembic/versions` 生成代码；ignore B008（FastAPI 依赖注入惯用法）/ RUF001-003（中文全角标点误报）/ UP046（Pydantic 泛型不迁移 PEP 695）；autofix 97 处，models 8 文件补 `TYPE_CHECKING` 前向引用（F821 ×18），B904 raise-from ×4
- **两个真 bug 由 lint 抓出、测试回归覆盖**（`tests/test_overview.py`，/overview 此前零覆盖）：
  - `routers/tasks.py` list_tasks 的 search/sort 分支缺 `func/case` 导入，调用即 NameError→500（前端纯客户端过滤从未触发）；顺带修 `overdue` 过滤在分页之后执行的语义错误 → SQL 级
  - `services/stats.py` overview 卡片统计三元组解包错误，total>0 即 NameError（测试全靠空库短路）→ 正确解包
- **CI 环境自洽**：conftest 注入 `ENVIRONMENT=test` + 测试 SECRET_KEY，无 `.env` 环境（CI/新 clone）直接可跑 pytest；CI 安装 `.[test]` extras；setup-node 指定 `frontend/package-lock.json` 缓存路径
- **运维审计确认已完备**：backup sidecar（每日 pg_dump + gzip + 7 天保留）、restore.sh 交互式恢复、全服务 restart=unless-stopped、DB 感知 healthcheck

### 测试基建修复
- 修复全量 `pytest` 挂死：pytest-asyncio 1.4 函数级测试循环与会话级 MCP 会话管理器（anyio task group 绑定单循环、`run()` 仅允许一次）冲突 → `asyncio_default_fixture/test_loop_scope = "session"` 全套共享会话循环；移除废弃的 `event_loop` fixture
- MCP 工具执行错误以 200 + `result.isError` 返回而非 JSON-RPC error，修正 5 处断言；`test_unauthorized_mcp` 改用无凭证 client（MCP 认证层接受 JWT）
- 结果：**106 passed in ~21s**（修复前：全量跑永久挂起）

## [0.2.0] - 2026-08-26

### 安全加固
- `SECRET_KEY` 在非 dev 环境下 fail-fast：默认值或长度 <32 直接拒绝启动
- 登录 / 注册 / API Key 兑换 5/min/IP 限流，SSE 流 60/min/IP（slowapi + nginx limit_req 双层）
- MCP 工具补齐枚举校验（status/priority 白名单），与 REST 对齐；非法日期返回明确错误
- 任务关联跨项目里程碑被拒绝（REST 与 MCP 双侧校验归属）
- CSV 导出防公式注入（`=+-@` 前缀单元格加单引号）；导出文件名净化
- nginx 增加 CSP、X-Content-Type-Options、X-Frame-Options、HSTS、Referrer-Policy 安全头
- 基础镜像 digest 级 pin（python:3.12.6-slim-bookworm / node:22.11-alpine / nginx:1.27-alpine / postgres:16.6-alpine）
- 后端依赖从 `>=` 收敛为 `~=`，移除未使用的 sass-embedded

### 正确性修复
- 修复 token 过期后 401 无限重定向循环（拦截器同步清空 Pinia store）
- 全局异常处理器：IntegrityError→409、DataError/ValueError→422，不再泄露 500
- 注册并发冲突返回 409 而非 500
- 批量更新 ids 上限 100；批量更新 SSE 广播真实任务 id（此前恒为 0）
- 甘特图"今天"标记改用本地时区（此前 UTC 导致东八区凌晨日期错位）

### 可靠性与可观测性
- `/api/health` 升级为 DB 感知探活（SELECT 1 失败返回 503），接入 compose healthcheck
- backend / frontend 增加 healthcheck；frontend 等 backend healthy 后才启动
- 新增结构化 JSON 请求日志中间件（request_id、latency_ms、X-Request-ID）

### 性能
- ECharts 改按需引入（echarts/core），chunk 由 ~1.0MB 降至 ~0.5MB
- Inter 字体仅加载 latin 子集
- nginx 开启 gzip；静态资源 immutable 长缓存；index.html no-cache

### 工程化
- 后端测试 pytest 化（pytest-asyncio + httpx），新增 auth/pagination/errors/enums 用例
- 前端新增 Vitest（csv/auth/pagination 用例）
- GitHub Actions CI：ruff + pytest + alembic --sql + vue-tsc + build + bundle 体积门槛
- 新增 pg_dump 每日备份 sidecar（保留 7 天）与 scripts/restore.sh 一键恢复
- docker-compose 支持 image 标签（TAG 变量）；frontend/.dockerignore 补齐 node_modules/dist
- 文档失真修复（部署指南健康状态描述、依赖锁定说明等）

## [0.1.0] - 初始版本

- 项目 / 里程碑 / 任务 / 依赖管理，进度追踪（甘特图、燃尽图、延期预警）
- JWT 认证与 API Key（MCP Server 34 工具接入）、SSE 实时推送
- DevLog / DevSession 开发过程记录
