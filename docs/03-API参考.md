# 03 · API 参考

> Base URL：`/api` ｜ 认证：`Authorization: Bearer <token>` ｜ 交互式文档：`/docs`（Swagger UI）

## 1. 通用约定

- **请求/响应**：JSON（`Content-Type: application/json`）
- **日期**：请求传 `YYYY-MM-DD`；响应中 `created_at`/`completed_at` 为带时区的 ISO 8601（UTC）
- **错误格式**：`{"detail": "错误描述"}`，HTTP 状态码语义化
- **鉴权失败**：`401`，前端拦截器自动跳转登录页
- **校验失败**：`422`（Pydantic）或 `400`（业务校验）

### 状态枚举

| 枚举 | 值 |
|---|---|
| 项目状态 | `active` / `archived` |
| 里程碑状态 | `active` / `done` |
| 任务状态 | `todo` / `in_progress` / `done` |
| 任务优先级 | `low` / `medium` / `high` |

## 2. 认证

### POST /auth/register — 注册
```json
// 请求
{ "username": "alice", "email": "a@b.com", "password": "secret123" }
// 响应 201
{ "access_token": "<jwt>", "token_type": "bearer", "user": { "id": 1, "username": "alice", "email": "a@b.com", "created_at": "..." } }
```
- 用户名 2-50 字符、密码 ≥6 位、邮箱格式校验；用户名或邮箱重复 → `400`

### POST /auth/login — 登录
```json
{ "username": "alice", "password": "secret123" }   // 响应 200，同 register
```
- 凭据错误 → `401`

### GET /auth/me — 当前用户
```json
// 响应 200
{ "id": 1, "username": "alice", "email": "a@b.com", "created_at": "..." }
```

## 3. 项目

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /projects | 项目列表（按创建时间倒序） |
| POST | /projects | 创建项目 → 201 |
| GET | /projects/{id} | 详情（不存在/无权限 → 404） |
| PUT | /projects/{id} | 更新（支持部分字段） |
| DELETE | /projects/{id} | 删除（级联删任务/里程碑）→ 204 |

```json
// 项目对象
{ "id": 1, "name": "官网改版", "description": "2026 重构",
  "status": "active", "start_date": "2026-08-01", "end_date": "2026-09-30",
  "created_at": "..." }
```

## 4. 里程碑

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /projects/{pid}/milestones | 列表（due_date 升序，NULL 排后） |
| POST | /projects/{pid}/milestones | 创建 → 201 |
| PUT | /milestones/{id} | 更新 |
| DELETE | /milestones/{id} | 删除（任务保留，milestone_id 置空）→ 204 |

## 5. 任务

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /projects/{pid}/tasks | 列表；`?status=`、`?overdue=`、`?priority=`、`?milestone_id=`、`?search=`（名称/描述模糊）、`?sort=`（created_desc / due_asc / due_desc / priority_desc） |
| POST | /projects/{pid}/tasks | 创建 → 201 |
| GET | /tasks/{id} | 详情 |
| PUT | /tasks/{id} | 更新（含状态流转，见下） |
| DELETE | /tasks/{id} | 删除 → 204 |
| POST | /tasks/bulk | 批量更新：`{"ids": [...], "data": {...}}` → 204 |
| GET | /tasks/{id}/dependencies | 前置任务 id 列表 |
| POST | /tasks/{id}/dependencies | 添加依赖：`{"depends_on_task_id": n}` → 204 |
| DELETE | /tasks/{id}/dependencies | 移除依赖：`{"depends_on_task_id": n}` → 204 |

```json
// 任务对象（含派生字段 overdue）
{ "id": 1, "project_id": 1, "milestone_id": null,
  "name": "页面设计", "description": null, "status": "todo",
  "priority": "high", "progress": 40,
  "start_date": "2026-08-01", "due_date": "2026-08-10",
  "completed_at": null, "estimated_hours": null, "created_at": "...",
  "overdue": true }
```

### 状态流转规则（PUT / bulk 均适用）

| 请求中的 status | 服务端强制行为 |
|---|---|
| `done` | `progress = 100`，`completed_at = now()`（若为空） |
| 其他值（含回退） | `completed_at = null` |
| 仅改 progress 且非 done | 正常更新（收敛到 0-100） |

### 依赖约束

- 不能依赖自身 → `400`
- 重复依赖 → `400`
- 目标任务不存在/无权限 → `404`

## 6. 统计与进度追踪

### GET /overview — 全局仪表盘聚合（P1-1）
```json
{ "total_projects": 3, "active_projects": 2,
  "projects": [ { "project_id": 1, "name": "…", "status": "active", "progress": 33.3,
                   "total_tasks": 12, "done_tasks": 4, "overdue_count": 1 } ],
  "overdue_tasks": [ { "id": 3, "name": "…", "project_id": 1, "project_name": "…",
                        "due_date": "2026-08-09", "days_late": 2, "priority": "medium" } ],
  "recent_logs": [ { "id": 7, "project_id": 1, "project_name": "…", "entry_type": "progress",
                      "title": "…", "author": "…", "created_at": "…" } ],
  "active_sessions": [ { "id": 2, "project_id": 1, "project_name": "…", "title": "…",
                          "log_count": 4, "started_at": "…" } ],
  "today_completed": 3 }
```
- 单次聚合查询（统计头 / 项目进度卡片 / 逾期任务 / 近期 DevLog / 活跃会话 / 今日完成数），驱动 `/dashboard` 页

### GET /search — 全局搜索（P1-5）
- `?q=<关键词>&project_id=<可选，限定项目>`；`q` 至少 2 字符
- 覆盖项目 / 任务 / 里程碑（ILIKE 模糊匹配），返回 `{ items: [ { type, id, name, description, project_id, project_name, status, due_date } ], total }`
- 前端入口：顶栏 GlobalSearch 组件（`⌘K` 聚焦）

### GET /projects/{pid}/stats — 进度汇总
```json
{ "total_tasks": 12, "done_tasks": 4, "in_progress_tasks": 3, "todo_tasks": 5,
  "progress": 33.3,
  "overdue_tasks": [
    { "id": 3, "name": "编写文档", "due_date": "2026-08-09", "days_late": 2, "priority": "medium" }
  ] }
```
- `progress` = done / total × 100（保留 1 位小数）
- `overdue_tasks` 按逾期天数降序

### GET /projects/{pid}/burndown — 燃尽图
```json
[ { "date": "2026-08-01", "ideal_remaining": 12, "actual_remaining": 12 },
  { "date": "2026-08-02", "ideal_remaining": 11, "actual_remaining": 10 },
  ... ]
```
- 区间 = 项目 start_date → end_date（缺省回退为今天）
- 期望线线性递减至 0；实际线按 `completed_at` 逐日累计
- 项目起止异常（start > end）→ `400`

### GET /projects/{pid}/gantt — 甘特图
```json
{ "tasks": [
    { "id": "1", "name": "页面设计", "start": "2026-08-01", "end": "2026-08-10",
      "progress": 40, "dependencies": "", "overdue": true, "status": "todo" },
    { "id": "2", "name": "前端开发", "start": "2026-08-11", "end": "2026-09-01",
      "progress": 0, "dependencies": "2:1", "overdue": false, "status": "in_progress" }
  ],
  "project_start": "2026-08-01", "project_end": "2026-09-30" }
```
- `dependencies` 为 frappe-gantt 格式：`"任务id:前置任务id,任务id:前置任务id"`

## 6.5 开发记录（DevLog / 会话）

> DevLog 记录开发**过程**（进度/难点/待办/决策/阻塞），与任务、里程碑互补。会话（Session）用于把一段连续开发内的记录归组，支持收口总结。

### POST /projects/{pid}/logs — 创建记录（需登录）
```json
// 请求 —— entry_type 必填；status 仅 todo/blocker；severity 仅 difficulty/blocker
{ "entry_type": "progress", "title": "完成登录模块", "content": "实现 JWT 签发与校验",
  "git_ref": "a1b2c3d", "related_task_ids": [42], "session_id": null }
// 响应 201
{ "id": 1, "project_id": 1, "session_id": 3, "entry_type": "progress", "status": "open",
  "severity": null, "title": "完成登录模块", "content": "...", "related_task_ids": [42],
  "git_ref": "a1b2c3d", "author": "alice", "created_at": "...", "updated_at": "...", "resolved_at": null }
```
- `entry_type` ∈ `progress`/`difficulty`/`todo`/`decision`/`blocker`/`milestone`/`note`
- `related_task_ids` 必须属于本项目，否则 `400`
- 不传 `session_id` 时，自动归入本项目最近未结束的会话

### GET /projects/{pid}/logs — 列表（需登录）
- 查询参数：`entry_type`、`status`、`since`（日期，含当日）、`limit`（≤200）、`offset`
- 按 `created_at` 倒序 → `200` 返回 `[DevLogOut]`

### GET /projects/{pid}/logs/stats — 统计（需登录）
```json
{ "total": 12, "today_count": 3, "open_todos": 2, "open_difficulties": 1, "open_blockers": 0,
  "decisions": 4, "type_counts": { "progress": 5, "difficulty": 2, "todo": 3, "decision": 4,
  "blocker": 0, "milestone": 1, "note": 0 }, "latest_activity": "2026-08-13T02:00:00+00:00" }
```

### POST /projects/{pid}/logs/report — 生成开发汇报（需登录）
```json
// 请求
{ "start": "2026-08-01", "end": "2026-08-13" }   // 均可省略，省略=全部时间
// 响应 200
{ "text": "# 开发汇报（全部时间）\n\n## 进展\n- **完成登录模块**\n..." }
```

### GET /logs/{id} — 单条记录（需登录）→ `200 [DevLogOut]`，无权限 `404`

### PUT /logs/{id} — 更新记录（需登录）
- 局部更新：仅更新传入字段（`exclude_unset`）；`related_task_ids` 变更会重新做项目归属校验
- 响应 `200 [DevLogOut]`

### POST /logs/{id}/resolve — 标记完成（需登录）
- 仅 `todo` / `blocker` 条目可用，否则 `400`；置 `status=done` 并盖章 `resolved_at` → `200 [DevLogOut]`

### DELETE /logs/{id} — 删除记录（需登录）→ `204`

### POST /projects/{pid}/sessions — 开始会话（需登录）
```json
// 请求
{ "title": "实现登录模块" }
// 响应 201 —— log_count 为已归入该会话的记录数
{ "id": 3, "project_id": 1, "title": "实现登录模块", "started_at": "...", "ended_at": null,
  "summary": null, "author": "alice", "created_at": "...", "log_count": 0 }
```

### POST /sessions/{id}/end — 结束会话（需登录）
```json
// 请求
{ "summary": "完成认证流程与 12 个单测" }
// 响应 200
{ "id": 3, "project_id": 1, "title": "...", "started_at": "...", "ended_at": "...",
  "summary": "完成认证流程与 12 个单测", "author": "alice", "created_at": "...", "log_count": 7 }
```

### GET /projects/{pid}/sessions — 会话列表（需登录）
- 按 `started_at` 倒序，`ended_at=null` 表示进行中 → `200 [DevSessionOut]`

## 7. 错误码速查

| 状态码 | 场景 |
|---|---|
| 400 | 重复注册、重复/自依赖、项目起止日期异常、业务校验（含 related_task_ids 越权、resolve 非 todo/blocker） |
| 401 | 未登录 / token 失效 / 凭据错误 / API Key 无效 |
| 404 | 资源不存在或无权限（统一 404 防探测） |
| 422 | 请求体字段校验失败（枚举/长度/范围） |
| 204 | 删除/批量操作成功（无响应体） |

## 8. API Key（AI 工具接入）

> AI 工具使用长期有效的 API Key，避免 7 天 JWT 过期。Key 只在创建时返回一次，落库仅存哈希；可随时撤销。

### POST /keys — 创建（需登录）
```json
// 请求
{ "name": "Claude Code" }
// 响应 201 —— key 仅此一次返回
{ "id": 1, "name": "Claude Code", "key": "hpf_a1b2c3_<64位十六进制>", "prefix": "a1b2c3" }
```

### GET /keys — 列表（需登录）
```json
[ { "id": 1, "name": "Claude Code", "prefix": "a1b2c3", "created_at": "...", "last_used_at": null, "revoked_at": null } ]
```

### DELETE /keys/{id} — 撤销（需登录）
- 撤销后该 Key 立即失效，无法恢复 → `204`

### POST /keys/exchange — 用 API Key 换 JWT
```json
// 请求
{ "key": "hpf_a1b2c3_<...>" }
// 响应 200 —— 返回短期 JWT，可调用既有 /api 接口
{ "access_token": "<jwt>" }
```
- 供不方便直接跑 MCP 的脚本/工具使用；失败 → `401`

> **两种使用方式**：① 通过 MCP Server（推荐，见 `08-AI接入指南.md`）；② 通过 `/keys/exchange` 换 JWT 后调 REST。

## 9. SSE 实时推送（进度同步）

### POST /events/ticket — 换取 SSE 短期 ticket（需登录）
- EventSource 无法携带 Authorization 头，先以 JWT 换取 30s 一次性 ticket，再以 `?ticket=` 传入流端点，避免长期令牌进入 URL。
- 响应：`{ "ticket": "<jwt-typ=sse>" }`；限流 60/min/IP。

### GET /events/stream?project_id={pid} — 项目变更事件流（需登录）
- 认证优先级：`Authorization: Bearer <JWT>` 头 > `?ticket=` 短期 ticket；两者皆无 → `401`。
- `project_id` 可省略：省略则订阅**全局流**（P4-4 通知中心），服务端按当前用户拥有的项目过滤——他人项目的事件静默丢弃，不泄露其存在。
- 长连接，`text/event-stream`。任一写操作（项目/里程碑/任务/依赖/DevLog/会话）后推送 `project-update` 事件。
- 事件格式（`data` 字段为 JSON）：
```json
{ "type": "updated", "entity": "task", "entity_id": 42, "project_id": 1, "ts": "2026-08-12T05:41:00+00:00" }
```
- `entity` ∈ `project`/`milestone`/`task`/`log`/`session`；`type` ∈ `created`/`updated`/`deleted`
- 每 25s 发送 `ping` 心跳保活；前端可据此自动刷新受影响项目。
- 注意：此端点未挂 slowapi 限流装饰器（与 EventSourceResponse 的签名解析冲突会误判 422），长连接天然低频，由 nginx `limit_req` 兜底。

## 10. MCP Server（AI 工具）

- 端点：`{base}/mcp`（Streamable HTTP 传输，兼容 SSE）
- 认证：`Authorization: Bearer <API Key 或 JWT>`
- 工具清单与用法见 `08-AI接入指南.md`
