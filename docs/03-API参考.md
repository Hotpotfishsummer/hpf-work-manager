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
| GET | /projects/{pid}/tasks | 列表；`?status=`、`?overdue=true` 过滤 |
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

## 7. 错误码速查

| 状态码 | 场景 |
|---|---|
| 400 | 重复注册、重复/自依赖、项目起止日期异常、业务校验 |
| 401 | 未登录 / token 失效 / 凭据错误 |
| 404 | 资源不存在或无权限（统一 404 防探测） |
| 422 | 请求体字段校验失败（枚举/长度/范围） |
| 204 | 删除/批量操作成功（无响应体） |
