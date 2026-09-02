# 02 · MCP 工具完整参考（35 个）

> 全部工具的签名、参数、返回值与示例。以服务端实际实现为准
> （源码：`backend/app/mcp_server.py`）。工具只操作**当前认证用户**的数据。

通用约定：
- **日期**参数一律为 ISO 格式字符串，如 `2026-08-13`；返回的日期同样为 ISO 字符串。
- **可选参数**不传即不更新（对 `update_*` 类工具而言）。
- 写操作成功后会自动 **SSE 广播**到前端，无需额外通知。
- 失败返回描述性错误（如"任务 42 不存在"）。

---

## 一、项目（5）

### 1. `list_projects` — 列出当前用户的所有项目
- 参数：`status`（可选，active/archived）、`offset`（默认 0）、`limit`（默认 50，上限 200）
- 返回：`Project[]`（按 created_at 倒序）

```json
[{"id":1,"name":"HPF 官网","description":"官网改版","status":"active",
  "start_date":"2026-08-01","end_date":"2026-09-30","created_at":"2026-08-12T09:00:00+00:00"}]
```

### 2. `get_project` — 获取单个项目详情
- 参数：`project_id: int`（必填）
- 返回：`Project`

### 3. `create_project` — 创建项目
- 参数：
  - `name: str`（必填，≤120 字符）
  - `description: str | None`
  - `start_date: str | None`（ISO 日期）
  - `end_date: str | None`
- 返回：`Project`（含新 id）

```text
create_project(name="HPF 官网", start_date="2026-08-01", end_date="2026-09-30")
```

### 4. `update_project` — 更新项目
- 参数：`project_id`（必填）+ 以下任选：
  - `name` / `description`
  - `status`：`active` / `archived`
  - `start_date` / `end_date`
- 返回：更新后的 `Project`

### 5. `delete_project` — 删除项目（级联删除其任务、里程碑、DevLog/会话）
- 参数：`project_id`（必填）
- 返回：`str`，如 `"项目 3 已删除"`
- ⚠️ 不可逆操作，请先确认。

---

## 二、里程碑（4）

`Milestone` 结构：`id, project_id, name, due_date, status, created_at`，`status ∈ active/done`。

### 6. `list_milestones` — 列出项目的所有里程碑
- 参数：`project_id: int`
- 返回：`Milestone[]`（按 due_date 升序）

### 7. `create_milestone` — 创建里程碑
- 参数：`project_id`（必填）、`name`（必填，≤120）、`due_date: str | None`
- 返回：`Milestone`

### 8. `update_milestone` — 更新里程碑
- 参数：`milestone_id`（必填）+ 任选 `name` / `due_date` / `status`（active/done）
- 返回：`Milestone`

### 9. `delete_milestone` — 删除里程碑
- 参数：`milestone_id`
- 返回：`str`
- 说明：其下任务**保留**，`milestone_id` 置空。

---

## 三、任务（8）

`Task` 结构：`id, project_id, milestone_id, name, description, status, priority, progress,
start_date, due_date, completed_at, estimated_hours, created_at`；另有派生字段
`overdue`（是否延期）与 `depends_on`（前置依赖任务 id 列表，后端查询不落库）。

### 10. `list_tasks` — 列出项目任务
- 参数：
  - `project_id: int`
  - `status: str | None`（`todo` / `in_progress` / `done`）
  - `overdue: bool | None`（`true`/`false` 均为 SQL 级过滤，分页语义稳定）
  - `search: str | None`（名称/描述 ILIKE 模糊匹配）
  - `offset: int = 0`、`limit: int = 200`（上限 500）
- 返回：`Task[]`（按 created_at 倒序）

```text
list_tasks(project_id=1, status="todo")
list_tasks(project_id=1, overdue=true)
```

### 11. `get_task` — 获取单个任务详情
- 参数：`task_id: int`
- 返回：`Task`

### 12. `create_task` — 创建任务
- 参数：
  - `project_id: int`、`name: str`（必填）
  - `description: str | None`
  - `milestone_id: int | None`
  - `priority: str = "medium"`（`low/medium/high`）
  - `status: str = "todo"`（`todo/in_progress/done`）
  - `progress: int = 0`（0-100）
  - `start_date` / `due_date: str | None`
  - `estimated_hours: int | None`（工时/小时，参与工时加权进度）
- 返回：`Task`
- 状态机：`status="done"` 时自动 `progress=100` + `completed_at=now`。

```text
create_task(project_id=1, name="实现登录模块", milestone_id=2, priority="high",
            due_date="2026-08-20", estimated_hours=8)
```

### 13. `update_task` — 更新任务（含状态机）
- 参数：`task_id`（必填）+ 上述任选字段
- 返回：`Task`
- 状态机（自动）：
  - `status="done"` → `progress=100`、`completed_at` 盖章
  - `status` 改为非 `done` → `completed_at` 清空
  - `status="done"` 时 `progress` 写入被忽略（钳制 0-100）

```text
update_task(task_id=42, status="done")
# => progress 自动变 100，completed_at 自动盖章
```

### 14. `delete_task` — 删除任务
- 参数：`task_id`
- 返回：`str`

### 15. `add_task_dependency` — 添加任务依赖（task 依赖 depends_on）
- 参数：`task_id: int`、`depends_on_task_id: int`
- 返回：`str`，如 `"任务 42 已依赖任务 40"`
- 约束：不能依赖自身；重复添加报错；**成环检测**——沿 depends_on 上游链可达 task_id 时拒绝（REST/MCP 一致）。

### 16. `remove_task_dependency` — 移除任务依赖
- 参数：`task_id: int`、`depends_on_task_id: int`
- 返回：`str`
- 约束：依赖不存在报错。

### 17. `list_task_dependencies` — 列出任务的前置依赖
- 参数：`task_id: int`
- 返回：`list[dict]`，每项含 `task_id` / `depends_on_task_id` / `name` / `status` / `progress`
- 用途：开工前判断前置任务是否已完成（`status != "done"` 即存在未完成前置）。

---

## 四、统计（3）

### 18. `get_project_stats_mcp` — 项目进度统计
- 参数：`project_id`
- 返回：

```json
{
  "total_tasks": 20, "done_tasks": 8, "in_progress_tasks": 4, "todo_tasks": 8,
  "progress": 40.0, "weighted_progress": 46.2,
  "overdue_tasks": [
    {"id": 12, "name": "首页轮播", "due_date": "2026-08-10", "days_late": 3, "priority": "high"}
  ]
}
```

- `progress` = 已完成任务数 / 总任务数 × 100（1 位小数）。
- `weighted_progress` = 工时加权完成度（按 `estimated_hours` 加权；未填工时的任务按 1 计），双口径之一。
- `overdue_tasks` 按延期天数倒序；无延期返回空数组。

### 19. `get_burndown_mcp` — 燃尽图数据
- 参数：`project_id`
- 返回：`[{ "date": "2026-08-01", "ideal_remaining": 20, "actual_remaining": 18 }, ...]`
- 区间为项目起止日期（缺省回退到今日）；期望线从总任务数线性降到 0，实际线基于 `completed_at` 按日推导。

### 20. `get_gantt_mcp` — 甘特图数据
- 参数：`project_id`
- 返回：

```json
{
  "project_start": "2026-08-01", "project_end": "2026-09-30",
  "tasks": [
    {"id": "1", "name": "登录模块", "start": "2026-08-01", "end": "2026-08-10",
     "progress": 100, "dependencies": "1:2,1:3", "overdue": false, "status": "done"}
  ]
}
```

- `dependencies` 为逗号分隔的 `"任务id:依赖任务id"` 串，可为空字符串。

---

## 五、开发记录 DevLog / 会话（15）

> 协议细节见 [`04-DevLog开发记录协议.md`](04-DevLog开发记录协议.md)。

`DevLog` 结构：`id, project_id, session_id, entry_type, status, severity, title, content,
related_task_ids, git_ref, author, created_at, updated_at, resolved_at`。

`DevSession` 结构：`id, project_id, title, started_at, ended_at, summary, author, created_at, log_count`。

### 21. `start_dev_session` — 开始一次开发会话
- 参数：`project_id`（必填）、`title: str | None`
- 返回：`DevSession`（`ended_at=null`）
- 作用：后续 `log_*` 若未指定 session 会**自动归入最近的未结束会话**。

### 22. `end_dev_session` — 结束开发会话
- 参数：`session_id`（必填）、`summary: str | None`
- 返回：`DevSession`（`ended_at` 盖章、含 `log_count`）

### 23. `log_progress` — 记录一次开发进展
- 参数：`project_id`、`title`（必填）、`content`、`related_task_ids`、`git_ref`
- 返回：`DevLog`

```text
log_progress(project_id=1, title="完成 JWT 签发与校验", git_ref="a1b2c3d")
```

### 24. `log_difficulty` — 记录难点
- 参数：`project_id`、`title`（必填）、`content`、`severity="medium"`（low/medium/high）、`related_task_ids`
- 返回：`DevLog`

### 25. `log_todo` — 记录下一步待办（开发过程 TODO，比任务轻量）
- 参数：`project_id`、`title`（必填）、`content`、`related_task_ids`、`git_ref`
- 返回：`DevLog`

### 26. `log_decision` — 记录技术决策及理由
- 参数：`project_id`、`title`（必填）、`content`、`related_task_ids`
- 返回：`DevLog`

### 27. `log_blocker` — 记录阻塞项
- 参数：`project_id`、`title`（必填）、`content`、`severity="high"`（low/medium/high）
- 返回：`DevLog`

### 28. `log_note` — 记录通用备注
- 参数：`project_id`、`title`（必填）、`content`
- 返回：`DevLog`

### 29. `list_dev_logs` — 查询开发记录
- 参数：
  - `project_id`（必填）
  - `entry_type: str | None`（progress/difficulty/todo/decision/blocker/milestone/note）
  - `status: str | None`（open/done）
  - `since: str | None`（ISO 日期时间，`2026-08-12T00:00:00` 起）
  - `limit: int = 50`（上限 200）、`offset: int = 0`
- 返回：`DevLog[]`（按 created_at 倒序）

### 30. `get_dev_log_stats_mcp` — 开发记录统计
- 参数：`project_id`
- 返回：

```json
{
  "total": 25, "today_count": 5, "open_todos": 3, "open_difficulties": 2,
  "open_blockers": 1, "decisions": 6,
  "type_counts": {"progress": 8, "difficulty": 3, "todo": 4, "decision": 6,
                   "blocker": 1, "milestone": 0, "note": 3},
  "latest_activity": "2026-08-13T10:00:00+00:00"
}
```

### 31. `get_project_state` — 项目状态聚合包（新会话恢复上下文）
- 参数：`project_id`
- 返回：

```json
{
  "project": {"id": 1, "name": "HPF 官网", "status": "active", "description": "..."},
  "open_todos": [DevLog...],
  "active_difficulties": [DevLog...],
  "open_blockers": [DevLog...],
  "recent_progress": [DevLog...],
  "recent_decisions": [DevLog...],
  "active_session": {"id": 3, "project_id": 1, "title": "登录模块", "started_at": "...",
                     "ended_at": null, "summary": null, "author": "alice",
                     "created_at": "...", "log_count": 0}
}
```

- **新会话开始前先调它**，一次拉全上下文。

### 32. `get_dev_report` — 生成阶段开发汇报
- 参数：`project_id`（必填）、`start: str | None`、`end: str | None`（ISO 日期，省略表示全部时间）
- 返回：`str`（Markdown 文本，按进展/里程碑/难点/阻塞/待办/决策/备注分组）

### 33. `update_dev_log` — 更新一条记录
- 参数：`log_id`（必填）+ 任选 `title` / `content` / `severity` / `status` / `related_task_ids`
- 返回：`DevLog`
- 注意：`related_task_ids` 必须属于本项目；修改 `entry_type` 时服务端会强制校正
  status/severity 组合约束。

### 34. `delete_dev_log` — 删除一条记录
- 参数：`log_id`
- 返回：`str`

### 35. `resolve_dev_log` — 将记录标记为完成
- 参数：`log_id`
- 返回：`DevLog`（`status="done"`、`resolved_at` 盖章）
- 约束：**仅 `todo` / `blocker`** 条目可用，其他类型报错。

---

## 附：REST API（非 MCP 脚本场景）

MCP 工具与 REST 端点共享业务逻辑。REST 需要 JWT（`/api/keys/exchange` 换得），完整端点见仓库 `docs/03-API参考.md`。关键区别：

- REST 提供 MCP 没有的：批量更新 `POST /api/tasks/bulk`、任务依赖查询 `GET /api/tasks/{id}/dependencies`、分页 `offset/limit`。
- SSE 订阅：`GET /api/events/stream?project_id={pid}`。
