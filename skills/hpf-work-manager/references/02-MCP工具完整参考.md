# 02 · MCP 工具完整参考（28 个）

> 全部工具的签名、参数、返回值与示例。以服务端实际实现为准
> （源码：`backend/app/mcp_server.py`）。工具只操作**当前认证用户**的数据。
>
> 2026-11-25 由 44 个合并瘦身为 28 个：6 个 `log_*` 合一为 `log_dev_entry`；
> 依赖管理并入 `update_task` / `get_task`；4 个统计接口合一为 `get_project_stats(kind)`；
> `update/delete/resolve_dev_log` 合一为 `manage_dev_log(action)`；
> `delete_comment`、`brainstorm_ideas`、`sync_local_projects` 移出 MCP（REST/前端仍可用）。

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

## 三、任务（5）

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

### 11. `get_task` — 获取单个任务详情（含依赖富信息）
- 参数：`task_id: int`
- 返回：`Task` + `depends_on_detail`：
  `[{"task_id": 40, "name": "建表迁移", "status": "done", "progress": 100}, ...]`
- 用途：开工前判断前置任务是否已完成（`status != "done"` 即存在未完成前置）。

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

### 13. `update_task` — 更新任务（含状态机与依赖管理）
- 参数：`task_id`（必填）+ 上述任选字段，另加：
  - `add_depends_on: list[int] | None` — 添加前置依赖（前者依赖后者；重复添加自动跳过）
  - `remove_depends_on: list[int] | None` — 移除前置依赖（不存在的自动忽略）
- 返回：`Task`（`depends_on` 为最新依赖 id 列表）
- 状态机（自动）：
  - `status="done"` → `progress=100`、`completed_at` 盖章
  - `status` 改为非 `done` → `completed_at` 清空
  - `status="done"` 时 `progress` 写入被忽略（钳制 0-100）
- 依赖约束：不能依赖自身；**成环检测**——沿 depends_on 上游链可达 task_id 时拒绝（REST/MCP 一致）。

```text
update_task(task_id=42, status="done")
# => progress 自动变 100，completed_at 自动盖章

update_task(task_id=42, add_depends_on=[40, 41])     # 添加两个前置
update_task(task_id=42, remove_depends_on=[40])      # 移除一个前置
```

### 14. `delete_task` — 删除任务
- 参数：`task_id`
- 返回：`str`

---

## 四、统计（1）

### 15. `get_project_stats` — 项目统计（多合一）
- 参数：`project_id`、`kind: str = "overview"`
- 返回：`{"kind": kind, "data": ...}`，`data` 结构随 kind 而变：

**`kind="overview"`（默认）— 进度统计：**

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

**`kind="burndown"` — 燃尽图数据：**
`data` 为 `[{ "date": "2026-08-01", "ideal_remaining": 20, "actual_remaining": 18 }, ...]`。
区间为项目起止日期（缺省回退到今日）；期望线从总任务数线性降到 0，实际线基于 `completed_at` 按日推导。

**`kind="gantt"` — 甘特图数据：**

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

**`kind="devlog"` — 开发记录统计：**

```json
{
  "total": 25, "today_count": 5, "open_todos": 3, "open_difficulties": 2,
  "open_blockers": 1, "decisions": 6,
  "type_counts": {"progress": 8, "difficulty": 3, "todo": 4, "decision": 6,
                   "blocker": 1, "milestone": 0, "note": 3},
  "latest_activity": "2026-08-13T10:00:00+00:00"
}
```

---

## 五、开发记录 DevLog / 会话（7）

> 协议细节见 [`04-DevLog开发记录协议.md`](04-DevLog开发记录协议.md)。

`DevLog` 结构：`id, project_id, session_id, entry_type, status, severity, title, content,
related_task_ids, git_ref, author, created_at, updated_at, resolved_at`。

`DevSession` 结构：`id, project_id, title, started_at, ended_at, summary, author, created_at, log_count`。

### 16. `start_dev_session` — 开始一次开发会话
- 参数：`project_id`（必填）、`title: str | None`
- 返回：`DevSession`（`ended_at=null`）
- 作用：后续 `log_dev_entry` 若未指定 session 会**自动归入最近的未结束会话**。

### 17. `end_dev_session` — 结束开发会话
- 参数：`session_id`（必填）、`summary: str | None`
- 返回：`DevSession`（`ended_at` 盖章、含 `log_count`）

### 18. `log_dev_entry` — 写入一条开发记录（六合一）
- 参数：
  - `project_id: int`、`entry_type: str`、`title: str`（必填）
  - `content: str | None`
  - `severity: str | None`（low/medium/high；**仅 difficulty / blocker 有效**，缺省 difficulty→medium、blocker→high）
  - `related_task_ids: list[int] | None`（必须属于本项目）
  - `git_ref: str | None`（commit 或分支名，溯源用）
- `entry_type` 取值与用途：
  - `progress` 开发进展（建议附 `git_ref`）
  - `difficulty` 遇到的难点
  - `todo` 下一步轻量待办（后续用 `manage_dev_log(action="resolve")` 关闭）
  - `decision` 技术决策及理由
  - `blocker` 阻塞项（同 todo 可 resolve）
  - `note` 通用备注
- 返回：`DevLog`

```text
log_dev_entry(project_id=1, entry_type="progress", title="完成 JWT 签发与校验", git_ref="a1b2c3d")
log_dev_entry(project_id=1, entry_type="difficulty", title="异步坑", severity="high")
```

### 19. `list_dev_logs` — 查询开发记录
- 参数：
  - `project_id`（必填）
  - `entry_type: str | None`（progress/difficulty/todo/decision/blocker/milestone/note）
  - `status: str | None`（open/done）
  - `since: str | None`（ISO 日期时间，`2026-08-12T00:00:00` 起）
  - `limit: int = 50`（上限 200）、`offset: int = 0`
- 返回：`DevLog[]`（按 created_at 倒序）

### 20. `get_project_state` — 项目状态聚合包（新会话恢复上下文）
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

### 21. `get_dev_report` — 生成阶段开发汇报
- 参数：`project_id`（必填）、`start: str | None`、`end: str | None`（ISO 日期，省略表示全部时间）
- 返回：`str`（Markdown 文本，按进展/里程碑/难点/阻塞/待办/决策/备注分组）

### 22. `manage_dev_log` — 维护一条记录（三合一）
- 参数：
  - `log_id: int`、`action: str`（必填）
  - `action="update"` 时可选：`title` / `content` / `severity` / `status` / `related_task_ids`
- `action` 取值：
  - `update` — 更新字段（仅更新传入字段；`related_task_ids` 必须属于本项目）
  - `resolve` — 标记完成（**仅 todo / blocker** 条目可用，其他类型报错）
  - `delete` — 删除该记录
- 返回：`{"ok": true, "log": DevLog}`（update/resolve）或 `{"ok": true, "deleted_log_id": n}`（delete）

---

## 六、任务评论（2）

`Comment` 结构：`id, task_id, author_id, author_username, content, created_at`。

### 23. `add_comment` — 为任务添加评论
- 参数：`task_id: int`、`content: str`（1-2000 字符）
- 返回：`Comment`
- 约束：任务必须属于当前用户；内容去除首尾空白后不能为空。

### 24. `list_comments` — 列出任务评论
- 参数：`task_id: int`、`offset: int = 0`、`limit: int = 100`（上限 500）
- 返回：`Comment[]`（按 created_at 升序）

> 删除评论已移出 MCP，走前端 UI 或 REST `DELETE /api/comments/{id}`。

---

## 七、AI Driver & 双重认证协同（4）

### 25. `get_manager_status` — 查询管理器状态与驱动模式
- 参数：无
- 返回：
  ```json
  {
    "ok": true,
    "driver_mode": "DUAL_CERTIFIED", // 或 "EXTERNAL_DRIVEN"
    "mode_description": "双重认证协同模式 (Dual-Agent Consensus Active)",
    "has_internal_tokens": true,
    "quota": {
      "remaining_percent": 85,
      "weekly_remaining_percent": 92,
      "minutes_left": 142,
      "reset_time_str": "21:30:00",
      "is_night_shift": false,
      "suggestion": "5h额度状态良好（剩余 85%）"
    },
    "guidelines": "内部 MiniMax 算力充足。外部 Agent 在此模式下提交的规划提案将经过内部架构师模型的交叉校验...",
    "active_workspace": "/workspace/projects"
  }
  ```
- 用途：外部 Agent 在发起任务规划前探活，判断当前是双重认证还是单驱降级。

### 26. `get_next_steps` — 获取项目高价值落地推演建议
- 参数：`project_name: str`（代码库目录名）
- 返回：`TaskItem[]`（包含 title, category, priority, description, estimated_hours, reason, certified_by）
- 机制：内部算力充沛时由 MiniMax 架构师推演；算力耗尽时自动降级为代码库结构启发式规则推演（零 Token，永远可用）。

### 27. `propose_task_plan` — 外部规划提案与双重认证审查
- 参数：
  - `project_name: str`（目标项目名）
  - `tasks: list[dict]`（提案任务列表，含 title, description, category, priority, estimated_hours 等）
  - `agent_role_or_id: str = "external_agent"`（外部 Agent 代号）
  - `rationale: str = ""`（提案动机理由）
  - `auto_create: bool = false`（审查通过后是否直接建档落入项目看板）
- 返回：
  ```json
  {
    "ok": true,
    "driver_mode": "DUAL_CERTIFIED",
    "audit_status": "APPROVED", // 或 MODIFIED / REJECTED
    "audit_summary": "已通过内部模型双重认证审核，消除 1 处冗余并完善测试断言标准。",
    "certified_tasks": [...],
    "created_task_ids": [101, 102],
    "project_name": "my-app"
  }
  ```

### 28. `verify_and_complete_task` — 任务交付核销与证据绑定
- 参数：
  - `task_id: int`（任务编号）
  - `git_ref: str`（真实 Git Commit Hash 或分支）
  - `verification_evidence: str`（测试执行结果、覆盖率或核心代码变更片段，≥5字符）
  - `summary: str = ""`（完成总结）
- 返回：
  ```json
  {
    "ok": true,
    "task_id": 42,
    "task_name": "实现搜索接口",
    "status": "done",
    "dev_log_id": 89,
    "git_ref": "4a9fbf0",
    "certified": true,
    "message": "任务「实现搜索接口」已完成双重认证归档，并生成关联 DevLog 凭证！"
  }
  ```
- 约束：杜绝虚标 done；必须带 git 证据，自动落成 `entry_type="progress"` DevLog 并广播 SSE。

> 原 MCP 工具 `brainstorm_ideas` / `sync_local_projects` 已移出 MCP，
> 走前端 UI 或 REST：`POST /api/ideator/brainstorm`、`POST /api/ideator/sync-projects`。

---

## 附：REST API（非 MCP 脚本场景）

MCP 工具与 REST 端点共享业务逻辑。REST 需要 JWT（`/api/keys/exchange` 换得），完整端点见仓库 `docs/03-API参考.md`。关键区别：

- REST 提供 MCP 没有的：批量更新 `POST /api/tasks/bulk`、任务依赖查询 `GET /api/tasks/{id}/dependencies`、评论删除 `DELETE /api/comments/{id}`、创意孵化与本地项目同步（`/api/ideator/*`）、分页 `offset/limit`、通知水位 `GET/PUT /api/notifications/watermark`。
- SSE 订阅：`GET /api/events/stream?project_id={pid}`。
