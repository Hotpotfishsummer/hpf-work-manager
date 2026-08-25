# system-audit-optimization - Work Plan
## TL;DR (For humans)
**你将得到什么**：一份把 HPF Work Manager 从“能跑”拉到“可上生产”的完整优化交付 — 安全基线拉齐、线上循环与分页等正确性缺陷清零、健康检查与日志可观测性补齐、首屏与包体积显著下降、测试与 CI/CD 及备份版本链路闭环、文档与可访问性对齐，所有改动均有可执行验收与回滚路径。

**为何用此方案**：按“安全→正确性→可靠性→性能→工程化”分 5 波推进，风险递减且每波均可独立验证；单实例约束下优先内存限流/进程内优化，避免过早引入 Redis/K8s 等重依赖；分页与按需引入等变更均保持 API 向后兼容（新增 limit/offset 默认值），前端逐步接 paginated 接口，灰度友好。

**它不会做什么**：不做 RBAC 角色体系、团队共享/多租户、K8s 集群化、MCP 细粒度权限分级、工时加权进度 — 这些属新增能力范畴，已在 Scope OUT 显式排除，需另起计划。

**工作量/风险**：约 32 实现 todos + 4 最终验证 todos，5 波约 2-3 天工程量（单人）；最大风险为 SECRET_KEY fail-fast 与分页默认值对旧客户端的兼容影响，已通过“非 dev 才拒绝启动 + 默认 limit 50 向后兼容 + 文档与 CHANGELOG 同步更新”缓解；回滚均为单文件/单 compose 字段回退。

**我为你做的关键决策**：
- 我把此开放审计判为 **UNCLEAR**，采用最佳实践默认值而非追问；若你本想聚焦单域（如仅安全），门前一句话即可让我切到 CLEAR 单问分叉。
- 限流用 **slowapi 内存** + nginx `limit_req` 而非 Redis — 单实例足够，避免为限流引入新中间件。
- SECRET_KEY 非 dev 默认值直接 **fail-fast** 而非仅 warn — 安全最高优。
- 分页默认 50 max 100、ECharts/ElementPlus 按需引入、nginx gzip — 平衡兼容与体积收益。
- 日志用标准 `logging` 中间件 JSON 输出、CI 用 GitHub Actions、备份用 pg_dump sidecar — 零重依赖、单机 Compose 最简可靠。

## Scope
### IN
- 安全加固：SECRET_KEY fail-fast、登录/注册/keys/exchange/MCP 限流、MCP 枚举与跨项目校验对齐、输入 max_length/null 校验、CSV 公式注入防护、镜像/依赖 pin、安全头与 TLS 强制指引
- 正确性修复：401 循环、DevLog 过滤/分页、显式 null 与超长入参 422 化、跨项目 milestone 校验、Gantt UTC 时区、批量语义与时序侧信道缓解
- 可靠性与可观测性：/api/health DB 感知、compose healthcheck + depends_on: healthy、全局异常转换、结构化请求日志、SSE 可靠性（后台刷新、重连 affordance、丢弃策略显式化）
- 性能与分页：tasks/projects/milestones/dev_logs 分页、任务看板虚拟化/按需加载、ECharts/ElementPlus 按需、nginx gzip 与缓存头、frappe-gantt 差分刷新、ILike 搜索防抖与长度门槛
- 工程化与交付：pytest 化、前端 Vitest、GitHub Actions、pre-commit、版本/tag/CHANGELOG、备份 sidecar 与恢复演练、.dockerignore 清理、文档失真修复、a11y 与空错加载态补齐

### OUT
- RBAC 细粒度角色/团队共享/组织维度
- K8s 部署与多副本 Redis Pub/Sub 事件总线（仅保留单实例可扩展预留）
- MCP 工具级细粒度权限分级
- 工时加权进度、评论/附件/通知等新增产品能力

## Verification strategy
- **单元与集成**：后端 pytest（含 DB 隔离 fixture）、前端 Vitest（组件与 composables）；每波均有 happy+failure 双路径
- **契约与回归**：`alembic upgrade head --sql` 离线校验、`/api/health` DB 感知探活、`npm run build` 体积回归（dist chunk 大小断言）、`rg` 禁止回归扫描（如硬编码 SECRET_KEY、显式 null 入参）
- **手工 QA**：按 Final verification wave 的 F3 清单逐项走查（401 过期、分页翻页、SSE 批量事件、CSV 注入、深浅主题、a11y 快捷键）
- **证据路径**：每个 todo 的 QA 均声明证据文件/命令输出路径，禁止“口头通过”

## Execution strategy
- **5 波串行**，波内可并行：Wave 1 安全基线 → Wave 2 正确性 → Wave 3 可靠性/可观测性 → Wave 4 性能/分页 → Wave 5 工程化/文档/a11y
- **依赖矩阵**：Wave 2 依赖 Wave 1 的校验与限流中间件就位；Wave 4 的前端分页依赖 Wave 2/3 的后端分页与错误码归一；Wave 5 的 CI 依赖 Wave 1-4 的测试基建
- **分支与提交**：单分支 `system-audit-optimization`，每 todo 一 commit，message 含 `wave<N>-todo<M>` 前缀；失败单 commit 回滚即可
- **风险缓解**：所有破坏性改动（SECRET_KEY fail-fast、分页默认）均保持向后兼容或仅在非 dev 生效，并同步更新 `.env.example` 与 `docs/`

## Todos
- [ ] 1. backend/app/config.py: 以 Pydantic Field 约束实现 SECRET_KEY 非 dev fail-fast 并同步 .env 与 docs — 修复公开默认值可伪造
  - References: `backend/app/config.py:11-19` (SECRET_KEY 默认与 cors_origin_list), `docker-compose.yml:27` (`${SECRET_KEY:-change-me-in-production}`), `.env.example:13`, `docs/05-部署指南.md:121-130` (必改提示), `backend/app/core/security.py:25` (JWT 依赖 SECRET_KEY)
  - Acceptance: 非 `ENVIRONMENT=dev` 且 `SECRET_KEY` 为 `change-me-in-production` 或长度<32 时应用启动直接抛 `RuntimeError` 并退出；`ENVIRONMENT=dev` 允许默认值但日志 warning；`.env.example` 与 `docs/05` 同步更新说明
  - QA (happy): `ENVIRONMENT=production SECRET_KEY=change-me-in-production uvicorn app.main:app` 启动失败，日志含 `SECRET_KEY must be set`，`echo $? !=0`；设置 64 位随机串后启动成功，`/api/health` 200 — 证据：`backend/logs/startup-fail.log` 与 `startup-ok.log`
  - QA (failure): 不导入 `backend/app/config.py` 直接 `python -c "from app.config import settings; print(settings.secret_key)"` 仍能读取但启动路径已拦截 — 证据：`rg "change-me-in-production" backend/app` 仅剩 `config.py` 的校验分支与注释
  - Commit: `wave1-todo1: enforce SECRET_KEY fail-fast in non-dev`

- [ ] 2. backend 限流：slowapi 内存限流中间件 + 路由级限流（login/register/keys/exchange/mcp/events_ticket）— 封堵爆破与滥用
  - References: `backend/pyproject.toml:6-21` (新增 slowapi), `backend/app/main.py:42-56` (CORS 与 lifespan), `backend/app/routers/auth.py:18-56` (register/login), `backend/app/routers/keys.py:65` (exchange), `backend/app/mcp_server.py:46-71` (MCP), `backend/app/routers/events.py:22-29` (SSE ticket), `frontend/nginx.conf:1-52` (nginx limit_req 兜底)
  - Acceptance: `POST /api/auth/login` 6 次/分钟/IP 后返回 429 `Rate limit exceeded`，响应头含 `Retry-After`；MCP 与 ticket 端点独立桶；限流计数内存实现，单测验证；nginx 侧 `limit_req_zone` 与 `limit_req` 配置同步提交（即使后端限流已生效）
  - QA (happy): `for i in {1..6}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST /api/auth/login -H "Content-Type: application/json" -d '{"username":"x","password":"y"}'; done` 第 6 次 429 — 证据：`backend/logs/rate-limit-happy.log`
  - QA (failure): 并发 10 请求中 4 个 429 且不影响其它 IP（换 IP 头复测 200）— 证据：`pytest backend/tests/test_rate_limit.py -k test_per_ip_isolation -s`
  - Commit: `wave1-todo2: add slowapi rate limiting + nginx limit_req`

- [ ] 3. 输入校验对齐：为 Project/Task/DevLog/Milestone 的 description/name 补 max_length，禁止显式 null 写入非空字段，统一 422 响应
  - References: `backend/app/schemas/project.py:9-21` (description 无 max_length, ProjectUpdate.name 可 None), `backend/app/schemas/task.py:11-49` (description/status/priority 可 None), `backend/app/schemas/dev_log.py:46` (title 可 None), `backend/app/routers/projects.py:60-61` (setattr None), `backend/app/services/tasks.py:12-39` (apply_status_transition 接受 None), `backend/app/models/task.py:25`/`project.py:17` (DB 长度 1000/500)
  - Acceptance: `POST /api/projects` name=null 返回 422 而非 500；description 超长返回 422 `String too long (max 500/1000)`；`PATCH /api/tasks/{id}` status=null 返回 422；所有路径不再抛 IntegrityError 500
  - QA (happy): `curl -X POST /api/projects -d '{"name":null}'` 422；`python -c "print('a'*501)"` 构造超长 description 422 — 证据：`pytest backend/tests/test_validation.py -k test_null_and_max_length -s`
  - QA (failure): 用旧 payload `{"name": null}` 走 MCP `update_project` 同样 422（MCP 侧校验对齐，见 todo 4）— 证据：`pytest backend/tests/test_mcp_validation.py -k test_mcp_null_rejected -s`
  - Commit: `wave1-todo3: tighten schema max_length and reject explicit null`

- [ ] 4. MCP 校验与跨项目外键对齐：MCP update_* 工具补 Literal 枚举校验，create/update_task 校验 milestone 归属 project
  - References: `backend/app/mcp_server.py:208-445` (update_project/milestone/task 任意字符串), `backend/app/schemas/project.py:21`/`milestone.py:19`/`task.py:46-49` (Literal 枚举), `backend/app/routers/tasks.py:104,122-123` 与 `mcp_server.py:396,425-426` (milestone_id 未校验归属)
  - Acceptance: MCP `update_task status=bad` 返回 JSON-RPC `Invalid status` 错误而非入库；`create_task milestone_id` 指向他项目里程碑时返回 400 `Milestone does not belong to project`；REST 与 MCP 共用同一校验函数
  - QA (happy): `mcp call update_task status=done` 成功，`status=invalid` 失败 400 — 证据：`pytest backend/tests/test_mcp_validation.py -k test_mcp_enum_and_milestone -s`
  - QA (failure): 伪造跨项目 milestone_id 的 task 创建被拒，且 DB 中无孤儿关联 — 证据：`psql "SELECT count(*) FROM tasks WHERE milestone_id NOT IN (SELECT id FROM milestones WHERE project_id=tasks.project_id)"` 为 0
  - Commit: `wave1-todo4: align MCP validation and milestone ownership check`

- [ ] 5. CSV 公式注入防护与导出文件名净化
  - References: `frontend/src/views/TaskBoardView.vue:715-737` (csvEscape 仅处理引号/逗号)、`736` (文件名来自 project.name)
  - Acceptance: 导出 CSV 中以 `=+-@` 开头的单元格前缀 `'` (单引号) 或制表符，且 `"` 转义仍正确；文件名净化去除 `/\0` 与控制字符，长度截断 80
  - QA (happy): 创建任务名 `=SUM(A1:A2)` 导出后用 `cat export.csv | head` 可见 `'=SUM` 前缀；Excel 打开不触发公式 — 证据：`frontend/logs/csv-injection-happy.csv`
  - QA (failure): 任务名含 `"` 与换行仍正确转义，`rg "=SUM" frontend/src/views/TaskBoardView.vue` 不再命中未转义路径 — 证据：`npm run test -- csv-escape`
  - Commit: `wave1-todo5: neutralize CSV formula injection and sanitize filename`

- [ ] 6. 安全头、依赖与镜像 pin：nginx 加 CSP/HSTS/X-Frame 等、pin 基础镜像 digest、pyproject 依赖范围收敛、移除未使用依赖
  - References: `frontend/nginx.conf:1-52` (无安全头), `backend/Dockerfile:2,9` (`python:3.12-slim` 未 pin), `frontend/Dockerfile:2,10` (`node:22-alpine`, `nginx:alpine`), `docker-compose.yml:6` (`postgres:16-alpine`), `backend/pyproject.toml:7-21` (`>=` 范围), `frontend/package.json:25` (`sass-embedded` 无 .scss)
  - Acceptance: `curl -I https://...` 响应含 `Content-Security-Policy`、`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`Strict-Transport-Security`；`docker build` 使用 digest pin；`sass-embedded` 已移除且 `npm run build` 成功
  - QA (happy): `curl -s -D - http://localhost:8080 | grep -i "content-security-policy"` 命中；`rg "sass-embedded" frontend/package.json` 无命中 — 证据：`frontend/logs/security-headers.log`
  - QA (failure): 故意回退 nginx.conf 去掉 CSP 后 `pytest frontend/tests/test_security_headers.py -k test_csp_present` 失败 — 证据：CI 日志
  - Commit: `wave1-todo6: add security headers, pin images/deps, remove unused dep`

- [ ] 7. 修复 401 循环：axios 拦截器与 Pinia store 同步清 token，路由守卫不再回弹
  - References: `frontend/src/api/http.ts:50-59` (仅清 localStorage), `frontend/src/stores/auth.ts:28-29` (token ref 初始化), `frontend/src/router/index.ts:76-84` (guard 依赖 auth.token)
  - Acceptance: token 过期后任意 API 401，拦截器同步 `auth.token=null` 并 `router.push /login`，不再回跳 `/dashboard`；`auth.token` 与 localStorage 一致
  - QA (happy): 手动将 `hpf_token` 设为过期 JWT，访问 `/dashboard` 触发 401 后地址稳定在 `/login?redirect=...`，不再循环 — 证据：`frontend/logs/401-loop-happy.mp4` 或 Playwright trace
  - QA (failure): 连续 3 次 401 也不产生循环请求风暴（Network 面板仅 1 次重定向）— 证据：`npx playwright test tests/e2e/auth-redirect.spec.ts -s`
  - Commit: `wave2-todo7: fix 401 redirect loop by syncing Pinia token`

- [ ] 8. DevLog 过滤与分页一致性：服务端统一按 entry_type/status 过滤，首载即带参，分页基于过滤后游标
  - References: `frontend/src/views/DevLogView.vue:265-270` (filteredLogs 客户端过滤), `281-291` (loadLogs 仅 offset>0 带 entry_type), `308` (initial load 不带 entry_type), `frontend/src/api/index.ts:107-111` (devLogApi 参数)
  - Acceptance: 切换 `entry_type/status` 立即 `offset=0` 重载，服务端返回已过滤结果；“加载更多”基于服务端 `hasMore`，不再出现“有更多但无可见新增”
  - QA (happy): 造 30 条 DevLog (10 blocker)，过滤 `blocker` 首屏即 10 条且 `hasMore=false` — 证据：`pytest backend/tests/test_dev_logs.py -k test_filter_pagination -s` + 前端 `npm run test -- devlog-filter`
  - QA (failure): 旧逻辑下切换过滤后首屏 20 条内无匹配的场景现已正确重载 — 证据：Playwright `devlog-filter.spec.ts` 截图对比
  - Commit: `wave2-todo8: fix DevLog filter/pagination consistency`

- [ ] 9. 全局异常归一：IntegrityError/DataError→4xx、ValueError→422，MCP 侧同语义 JSON-RPC 错误
  - References: `backend/app/main.py:42-56` (无 exception_handlers), `backend/app/routers/auth.py:20-28` (register 竞态 500), `backend/app/services/dependencies.py:60-61` (依赖竞态), `backend/app/mcp_server.py:390-392,434-436` (date.fromisoformat 裸调)
  - Acceptance: 任意显式 null/超长/重复键不再 500，均 4xx 且 message 含字段名；MCP 侧非法 date 返回 `Invalid date format` 而非通用 JSON-RPC error
  - QA (happy): `curl -X POST /api/projects -d '{"name":null}'` 422；并发 duplicate register 其中之一 409 — 证据：`pytest backend/tests/test_error_handlers.py -s`
  - QA (failure): 故意抛 `IntegrityError` 的分支被 handler 捕获，日志含 `exc_info` 且不泄露堆栈给客户端 — 证据：`rg "add_exception_handler" backend/app/main.py`
  - Commit: `wave2-todo9: add global exception handlers and normalize 4xx`

- [ ] 10. 跨项目 milestone 校验（REST 侧）与批量语义修正：bulk ids 上限、SSE entity_id 去 0
  - References: `backend/app/routers/tasks.py:104,122-123,159` (milestone 未校验、bulk entity_id=0、ids 无上限), `backend/app/schemas/task.py:54` (bulk ids)
  - Acceptance: `POST /api/tasks` 与 `PATCH /api/tasks/{id}` 校验 `milestone.project_id == task.project_id` 否则 400；`POST /api/tasks/bulk` ids 长度上限 100，超限 422；SSE `entity_id` 为实际任务 id 列表或逐条事件，不再为 0
  - QA (happy): 跨项目 milestone 创建 400；bulk 101 ids 422；SSE 订阅后批量更新可收到逐条 `entity_id` — 证据：`pytest backend/tests/test_tasks_bulk.py -s` + `curl -N /api/events/stream` 日志
  - QA (failure): 已存在的跨项目脏数据被迁移脚本或校验拦截后 `SELECT` 归零 — 证据：SQL 0 行报告
  - Commit: `wave2-todo10: enforce milestone ownership and fix bulk/SSE semantics`

- [ ] 11. Gantt 时区与批量/进度静默失败修复：本地日期、bulk/进度失败显式提示、时序枚举防抖
  - References: `frontend/src/components/GanttChart.vue:43` (UTC today), `frontend/src/views/GanttView.vue:63-76` (onDateChange/onProgressChange 无 catch), `frontend/src/views/TaskBoardView.vue:594-602` (quickSetDebounced 静默 catch), `666-680` (bulkRemove 吞错)
  - Acceptance: Gantt today 按本地时区；Gantt 拖拽失败回滚并 toast；看板进度/批量失败 toast 且不误报成功
  - QA (happy): UTC+8 00:30 创建任务 Gantt today 仍为当天；断网拖拽后 UI 回滚 — 证据：`npx playwright test gantt-timezone.spec.ts`
  - QA (failure): 模拟 API 500 时 `quickSetDebounced` 抛错路径被捕获并提示，非静默 — 证据：`npm run test -- gantt-error`
  - Commit: `wave2-todo11: fix Gantt timezone and silent failure paths`

- [ ] 12. 健康检查 DB 感知化：/api/health 探 DB，compose 为 backend/frontend 加 healthcheck 与 depends_on: healthy
  - References: `backend/app/main.py:72-74` (health 仅 ok), `docker-compose.yml:14-18` (仅 postgres healthcheck), `47-48` (frontend depends_on 无 condition), `frontend/nginx.conf:9-29` (proxy), `docs/05-部署指南.md:179,186-188` (healthy 断言)
  - Acceptance: `/api/health` 执行 `SELECT 1`，DB 不可用时 503；`docker compose ps` 三服务均 `healthy`；frontend 仅在 backend healthy 后启动
  - QA (happy): `docker compose up -d && curl -f http://localhost:8080/api/health` 200；`docker compose exec postgres pg_ctl stop && curl -f /api/health` 503 — 证据：`docker compose ps` 截图 + `logs/health-happy.log`
  - QA (failure): 故意 kill backend 后 frontend health 转 `unhealthy` 且 compose 重启策略生效 — 证据：`docker inspect` 状态
  - Commit: `wave3-todo12: make /api/health DB-aware and add compose healthchecks`

- [ ] 13. 结构化日志与请求日志中间件：JSON 日志、请求 ID、错误堆栈脱敏
  - References: `backend/app` 全目录 `rg "import logging"` 零命中, `backend/app/main.py:42-56` (无日志), `backend/app/routers/auth.py:50-51` (401 静默)
  - Acceptance: 每个请求日志含 `request_id`、`method`、`path`、`status`、`latency_ms`；5xx 自动 `exc_info`；日志 JSON 输出到 stdout，可被 docker json-file 收集；uvicorn access_log 关闭由中间件接管
  - QA (happy): `curl /api/projects/1/tasks` 后 `docker compose logs backend | jq .request_id` 有值 — 证据：`backend/logs/request-json.log`
  - QA (failure): 触发 500 的分支日志含堆栈但响应体不泄露堆栈 — 证据：`pytest backend/tests/test_logging.py -k test_no_stack_leak -s`
  - Commit: `wave3-todo13: add structured request logging middleware`

- [ ] 14. 统一错误码与审计：401/409/422 message 规范、last_used_at 在 API Key 直接鉴权时也更新
  - References: `backend/app/deps.py:44-57`/`mcp_auth.py:32-49` (直接 API Key 鉴权不更新 last_used_at), `backend/app/routers/keys.py:86` (仅 exchange 更新), `backend/app/routers/auth.py:20-28` (register 竞态)
  - Acceptance: 任意 API Key 成功鉴权均更新 `last_used_at` (1 分钟节流防抖可选)；register 并发 duplicate 返回 409 `Username already exists`；错误体 `{detail, code}` 结构统一
  - QA (happy): API Key 调 `/api/projects` 后 `SELECT last_used_at` 已更新 — 证据：`pytest backend/tests/test_api_keys.py -k test_last_used_updated -s`
  - QA (failure): 并发 register 10 次仅 1 成功其余 409 — 证据：`pytest backend/tests/test_auth_race.py -s`
  - Commit: `wave3-todo14: normalize error codes and update api_key last_used_at`

- [ ] 15. SSE 可靠性：后台静默刷新、重连 affordance、丢弃策略显式化与文档化
  - References: `frontend/src/composables/useProjectEvents.ts:14,38-46` (MAX_RETRIES=8 后永久中断), `frontend/src/components/LiveIndicator.vue:8-16` (无重连按钮/aria-live), `frontend/src/views/ProjectDetailView.vue:248-271`/`TaskBoardView.vue:493-498`/`DevLogView:449-456`/`GanttView:79-86` (每次全量 + v-loading 闪烁), `backend/app/core/events.py:43-52` (队列满丢最旧)
  - Acceptance: SSE 触发的 `scheduleReload` 走静默刷新（`loading=false`）；达最大重试后 LiveIndicator 显示“连接中断·重试”按钮可手动重连；后端队列丢弃策略在 `docs/01-架构设计.md` 显式文档
  - QA (happy): 人为 kill SSE 后重连按钮出现，点击后恢复；AI 批量 20 次事件仅触发 1-2 次 reload（400ms debounce）且无全屏遮罩 — 证据：`npx playwright test sse-reliability.spec.ts`
  - QA (failure): 队列满时日志 `dropped oldest event` 计数递增 — 证据：`backend/logs/sse-drop.log`
  - Commit: `wave3-todo15: make SSE silent, reconnectable, and document drop policy`

- [ ] 16. 后端分页：为 tasks/projects/milestones/dev_logs/session 加 limit/offset 与 total，默认 50 max 100
  - References: `backend/app/routers/tasks.py:49-82` (无分页), `projects.py:27-37`, `milestones.py:26-36`, `dev_logs.py:64-88,226-249` (仅 dev_logs 有 limit 无 total), `services/stats.py:42-51` (overdue 无 limit), `frontend/src/api/index.ts:63-73,107-111` (前端未暴露分页)
  - Acceptance: `GET /api/projects/{pid}/tasks?limit=50&offset=0` 返回 `{items, total, limit, offset}`，默认 50 上限 100；overdue 列表同样分页；所有列表 `total` 准确；旧客户端不传参仍 200（默认分页）
  - QA (happy): `curl "/api/projects/1/tasks?limit=2"` 返回 2 条且 total 正确；`limit=200` 被钳制为 100 — 证据：`pytest backend/tests/test_pagination.py -s`
  - QA (failure): `limit=0` 与 `offset=-1` 返回 422 — 证据：同上
  - Commit: `wave4-todo16: add paginated list with total for tasks/projects/milestones`

- [ ] 17. 前端分页与虚拟化：任务看板/项目列表/DevLog 接分页，后端 total 驱动分页器，超长列表虚拟滚动
  - References: `frontend/src/views/TaskBoardView.vue:108-169,469-475` (全量渲染), `ProjectListView.vue:31,145-152`, `DevLogView.vue:99-101,265-270` (load-more), `frontend/src/api/index.ts:63-73` (未暴露 limit/offset)
  - Acceptance: 任务看板按分页加载，滚动或分页器翻页；单页 >100 时虚拟滚动；DevLog 废弃客户端过滤的“加载更多”，改为服务端分页 + 过滤；空/错/加载三态完整
  - QA (happy): 造 200 任务，首屏仅渲染 50 DOM 节点，翻页后请求 `offset=50` — 证据：`npx playwright test pagination.spec.ts` + DOM 节点计数
  - QA (failure): 断网翻页显示错误态与重试按钮，不卡死 — 证据：Playwright 离线用例截图
  - Commit: `wave4-todo17: wire frontend pagination and virtual scroll`

- [ ] 18. 包体积：ECharts 按需、ElementPlus 按需、字体子集化、移除 sass-embedded
  - References: `frontend/src/components/BurndownChart.vue:7` (`import * as echarts`), `frontend/src/main.ts:3,5,20` (全量 ElementPlus), `frontend/src/main.ts:6-8` (全量 Inter 含非 latin), `frontend/package.json:25` (sass-embedded 无 .scss), `frontend/dist` (echarts 1.0MB, element-plus 928KB+382KB)
  - Acceptance: `BurndownChart` 改 `echarts/core` + `LineChart`；`main.ts` 切 `unplugin-vue-components/auto-import`；`@fontsource/inter/latin-*.css` 子集；`sass-embedded` 移除；`npm run build` 成功且 `dist` 总体积下降 ≥50%
  - QA (happy): `du -sh frontend/dist` 对比基线下降，`rg "import \* as echarts"` 0 命中 — 证据：`frontend/logs/bundle-before-after.log`
  - QA (failure): 回退到全量引入后体积回归测试失败 — 证据：CI `bundle-size` job
  - Commit: `wave4-todo18: tree-shake echarts/element-plus, subset fonts, remove sass-embedded`

- [ ] 19. nginx 性能与缓存：gzip/brotli、/assets immutable、index.html no-cache、client_max_body_size
  - References: `frontend/nginx.conf:1-52` (无 gzip, /assets 仅 7d 无 immutable, index.html 可缓存, 无 client_max_body_size), `frontend/vite.config.ts:23-33` (manualChunks 已有)
  - Acceptance: `gzip on` 且 `gzip_types` 含 JS/CSS/JSON/SVG；`location /assets/` 加 `immutable`；`location = /index.html` 加 `Cache-Control: no-cache`；`client_max_body_size 2m`
  - QA (happy): `curl -H "Accept-Encoding: gzip" -I http://localhost:8080/assets/index-*.js | grep content-encoding` 命中 gzip；`curl -I http://localhost:8080/index.html | grep no-cache` 命中 — 证据：`frontend/logs/nginx-cache-headers.log`
  - QA (failure): 去掉 gzip 后 `curl` 无 `content-encoding`，CI 失败 — 证据：`pytest frontend/tests/test_nginx.py`
  - Commit: `wave4-todo19: enable gzip and fix cache headers`

- [ ] 20. 搜索与 Gantt 性能：搜索最小长度 2、ILIKE 防抖 300ms、Gantt 差分刷新、依赖 cycle 检查批量化
  - References: `backend/app/routers/search.py:17,20,29,45,61` (q 1 字符 + 前导通配), `frontend/src/components/GanttChart.vue:120-127` (deep watch 全量 refresh), `backend/app/services/dependencies.py:23-29` (逐节点查询), `frontend/src/components/GlobalSearch.vue:19-23,42-46` (50ms DOM hack 无防抖)
  - Acceptance: `q.length<2` 返回 422；搜索防抖 300ms；Gantt 仅当 task id/dates 变更才 `refresh`；`add_dependency` 的 cycle 检查改为单次递归 CTE/批量查询而非 N 次单查
  - QA (happy): 输入 1 字符不发请求；Gantt 20 任务 SSE 批量更新仅 1 次 DOM 重绘 — 证据：`npx playwright test search-gantt-perf.spec.ts`
  - QA (failure): `q=ab` 仍 200 且结果正确；`q=a` 422 — 证据：`pytest backend/tests/test_search.py -k test_min_length -s`
  - Commit: `wave4-todo20: tune search/gantt perf and batch cycle check`

- [ ] 21. 后端测试 pytest 化：引入 pytest/pytest-asyncio/httpx，迁移 3 套脚本为可发现用例，补齐 auth/CRUD/分页/错误路径覆盖
  - References: `backend/pyproject.toml:6-21` (无 pytest), `backend/tests/test_integration.py:54,120-121`/`test_mcp_e2e.py:23,108-109`/`test_dev_logs.py:23,260-261` (__main__ 脚本), `backend/app/main.py:42-56`
  - Acceptance: `pytest -q` 可发现并通过 ≥30 用例，含 `test_auth_register_login`, `test_pagination_total`, `test_mcp_enum_rejected`, `test_error_4xx`；CI 可直接 `pytest`
  - QA (happy): `pytest backend/tests -q` 30+ passed，覆盖率 `pytest --cov=app` ≥60% — 证据：`backend/logs/pytest-happy.log`
  - QA (failure): 故意 break 一个校验后对应用例失败 — 证据：CI 日志
  - Commit: `wave5-todo21: convert backend tests to pytest and expand coverage`

- [ ] 22. 前端测试与 pre-commit：Vitest + Testing Library，补 401/分页/CSV/a11y 用例，加 pre-commit (ruff/eslint/stylelint)
  - References: `frontend/package.json:6-10` (无 test 脚本), `frontend/src/api/http.ts:50-59`, `TaskBoardView.vue:715-737`, `LiveIndicator.vue:8-16`
  - Acceptance: `npm run test` 可跑 Vitest，含 `auth-redirect.spec`, `csv-escape.spec`, `pagination.spec`；`pre-commit install` 后提交自动跑 `ruff`/`eslint`/`tsc --noEmit`
  - QA (happy): `npm run test -- --run` ≥10 用例通过 — 证据：`frontend/logs/vitest-happy.log`
  - QA (failure): 提交含 `any` 的 TS 文件被 pre-commit 拦截 — 证据：`pre-commit run --all-files` 日志
  - Commit: `wave5-todo22: add frontend Vitest and pre-commit`

- [ ] 23. GitHub Actions CI：lint + tsc + pytest + alembic --sql + build + bundle 体积门槛
  - References: 无 `.github/` 目录, `docs/06-开发指南.md:60-63` (手动 alembic --sql), `frontend/package.json:6-10`, `backend/pyproject.toml:6-21`
  - Acceptance: `.github/workflows/ci.yml` 在 push/PR 触发：`ruff check`、`vue-tsc --noEmit`、`pytest`、`alembic upgrade head --sql`、`npm run build`、`bundle size` 检查；任一失败阻断合并
  - QA (happy): 推送分支后 Actions 全部 green — 证据：Actions run 链接与 `gh run view`
  - QA (failure): 故意提交 `secret_key` 默认值绕过后 CI 失败 — 证据：失败 run 日志
  - Commit: `wave5-todo23: add GitHub Actions CI`

- [ ] 24. 备份与恢复：pg_dump sidecar cron 容器 + 保留 7 天 + 恢复演练文档化
  - References: `docker-compose.yml:54-55` (pgdata 仅卷), `docs/05-部署指南.md:399-424` (手动 cron 硬编码 hpf/hpf_work)
  - Acceptance: `docker-compose.yml` 新增 `backup` 服务，每日 02:00 `pg_dump` 到 `./backups/` 保留 7 天；`docs/05` 更新为 `docker compose exec backup` 流程，变量来自 `.env`；提供一键恢复脚本 `scripts/restore.sh`
  - QA (happy): `docker compose up -d backup && ls backups/` 含当日 dump；`scripts/restore.sh backups/latest.sql.gz` 恢复后 `SELECT count(*) FROM projects` 一致 — 证据：`backups/restore-happy.log`
  - QA (failure): 磁盘满时 backup 失败告警（exit code 非 0 且日志含 `No space`）— 证据：`docker compose logs backup`
  - Commit: `wave5-todo24: add pg_dump sidecar backup and restore script`

- [ ] 25. 版本与发布：git tag + image 标签 + CHANGELOG.md，compose 加 image 字段，docs 去“Release 压缩包”失真
  - References: `backend/pyproject.toml:3`/`backend/app/main.py:45`/`frontend/package.json:4` (0.1.0 硬编码三处), `docker-compose.yml:23,45` (无 image), `docs/05-部署指南.md:102-104,347` (Release 压缩包), `git tag -l` 空
  - Acceptance: `CHANGELOG.md` 建立；`docker-compose.yml` 加 `image: hpf-work-manager-backend:${TAG}` 等；`git tag v0.2.0` 可触发 `docker buildx build --tag`；docs 更新为 tag 发布流程
  - QA (happy): `git tag v0.2.0 && docker compose build && docker images | grep hpf` 含 tag — 证据：`git tag --list` + `docker images`
  - QA (failure): 未打 tag 时 `scripts/release.sh` 拒绝发布 — 证据：脚本 exit code
  - Commit: `wave5-todo25: add versioning, image tags, and CHANGELOG`

- [ ] 26. 依赖与构建卫生：pin 基础镜像 digest、收敛 pyproject 版本范围、补 .dockerignore、去 drift 的 env 模板
  - References: `backend/Dockerfile:2,9`, `frontend/Dockerfile:2,10`, `docker-compose.yml:6`, `backend/pyproject.toml:7-21`, `frontend/.dockerignore` (缺 node_modules/dist), `.env.example:13,15` vs `backend/.env.example:4` vs `config.py:15` 三处漂移
  - Acceptance: 基础镜像改为 `python:3.12-slim@sha256:...` 等 digest；`pyproject.toml` 依赖改为 `~=` 收敛；`frontend/.dockerignore` 补 `node_modules`/`dist`；三处 env 模板一致且与 `config.py` 默认一致
  - QA (happy): `docker compose build --no-cache` 成功；`rg "node_modules" frontend/.dockerignore` 命中；`diff .env.example backend/.env.example` 仅注释差异 — 证据：`frontend/logs/dockerignore-check.log`
  - QA (failure): 回退 digest 后 `hadolint` 告警 — 证据：CI hadolint job
  - Commit: `wave5-todo26: pin images/deps and fix dockerignore/env drift`

- [ ] 27. 文档与设计系统对齐：补 docs/03 的 /overview /search、修 healthy/依赖锁定等失真、同步 DESIGN.md 变更
  - References: `docs/03-API参考.md` (缺 /overview `routers/overview.py:24` 与 /search `search.py:13`), `docs/05-部署指南.md:179`/`06:12`/`06:130`/`01:3`, `frontend/src/design/element-plus.css:9-13` (light ramp 塌陷), `frontend/src/components/AppLayout.vue:87-89` (backdrop-filter 无 fallback)
  - Acceptance: `docs/03` 补两端点；`05:179` 改为“仅 postgres healthy，backend/frontend 新增 healthcheck 后为 healthy”；`06:12` 改为“依赖范围见 pyproject，pin 见 Dockerfile”；`element-plus.css` light ramp 恢复 3/5/7/8/9 阶梯；AppLayout 加 `@supports` 回退
  - QA (happy): `rg "/api/overview|/api/search" docs/03-API参考.md` 命中；`rg "backdrop-filter" frontend/src/components/AppLayout.vue` 含 `@supports` — 证据：`docs/logs/docs-fix-check.log`
  - QA (failure): 缺失端点的旧 docs 导致 `pytest backend/tests/test_docs_coverage.py` 失败 — 证据：CI
  - Commit: `wave5-todo27: fix docs staleness and design system alignment`

- [ ] 28. 可访问性与空错加载态：LiveIndicator aria-live、任务看板键盘替代 DnD、Gantt 键盘可达、全局空/错/加载态统一
  - References: `frontend/src/components/LiveIndicator.vue:8-16` (无 role/status), `frontend/src/views/TaskBoardView.vue:116-120,684-709` (DnD 仅鼠标), `frontend/src/components/GanttChart.vue:67-81` (SVG 不可键盘), `frontend/src/views/DashboardView.vue:56`/`ProjectListView.vue:31`/`GanttView.vue:49-61` (空/错态不区分)
  - Acceptance: LiveIndicator 含 `role="status" aria-live="polite"`；任务卡片支持 `Enter/Space` 打开抽屉且“移动到列”下拉可键盘操作；Gantt bar 可 `tab` 聚焦并 `Enter` 编辑；所有列表页区分“空数据”与“加载失败可重试”
  - QA (happy): 键盘全程走查：Tab 到任务卡片 Enter 打开抽屉，LiveIndicator 断连时读屏播报 — 证据：`npx playwright test a11y.spec.ts` + 录屏
  - QA (failure): 去掉 aria-live 后 `axe-core` 告警 — 证据：`npx playwright test --grep a11y` 失败日志
  - Commit: `wave5-todo28: improve a11y and empty/error/loading states`

## Final verification wave
- [ ] F1. 计划合规审计 — 校验本计划 28 实现 todos + 4 验证 todos 均满足列零 Markdown 行、References/Acceptance/QA/Commit 四件套、依赖矩阵一致、Scope OUT 未越界
- [ ] F2. 代码质量审查 — 跑 `ruff check`、`vue-tsc --noEmit`、`eslint`、`hadolint`，确认无新增 any/unwrap/panic、CSS 变量全走 --md-*、无硬编码 hex
- [ ] F3. 真机手工 QA — 按 Verification strategy 走查：401 过期重登、分页翻页、SSE 20 事件批量、CSV 注入、深浅主题切换、键盘 a11y、/api/health 503、备份恢复演练
- [ ] F4. 范围保真 — `git diff --stat` 仅触及 IN 范围文件，OUT 能力（RBAC/K8s/MCP 分级/工时加权）零新增代码，CHANGELOG 与 docs 同步更新

## Commit strategy
- 分支：`system-audit-optimization`，每 todo 一 commit，前缀 `wave<N>-todo<M>: <subject>`，关联 `Refs: #<issue>` 可选
- 合并前 squash 可选，但保留每波 tag：`wave1-security`、`wave2-correctness`、`wave3-reliability`、`wave4-perf`、`wave5-engineering`
- 回滚：单 commit `git revert <sha>` 即可；破坏性改动（SECRET_KEY、分页）均有 feature flag/环境开关兜底

## Success criteria
- 安全：默认 SECRET_KEY 已 fail-fast、限流 429 可复现、安全头齐全、CSV 注入已防护、依赖/镜像已 pin
- 正确性：401 不再循环、DevLog 过滤分页一致、所有显式 null/超长 422、跨项目外键 400、Gantt 本地日期正确
- 可靠性：`/api/health` DB 感知且 compose 三服务 healthy、日志 JSON 可查询、SSE 静默重连可用
- 性能：任务列表分页 + 虚拟化生效、dist 体积 -50%、nginx gzip 生效、Gantt/搜索防抖生效
- 工程化：`pytest -q` ≥30 用例通过、`npm run test -- --run` ≥10 用例通过、CI 全绿、备份 sidecar 每日产出、CHANGELOG 与 tag 流程闭环、docs 失真清零、a11y 走查通过

