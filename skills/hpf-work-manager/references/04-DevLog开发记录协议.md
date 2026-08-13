# 04 · DevLog 开发记录协议

DevLog（开发记录）是系统的**过程叙事**：任务/里程碑记录"结果"，DevLog 记录"过程"
（为什么这么做、卡在哪、下一步）。系统与 git 是一体两面 —— git 记录"代码状态"，
DevLog 记录"开发过程"，DevLog 只存 `git_ref` 引用（commit/分支名），**不解析 git**。

## 1. 条目类型 `entry_type`

| 类型 | 何时写 | 字段约束 |
|---|---|---|
| `progress` | 完成一件值得记录的事 | `git_ref` 建议填 commit |
| `difficulty` | 卡住 / 绕过的坑 | 可用 `severity` |
| `todo` | 下一步要做的事（比任务轻量） | 可用 `status`（open/done）、`git_ref` |
| `decision` | 拍板的技术方案及理由 | — |
| `blocker` | 无法推进的阻塞项 | 可用 `severity`、`status`（open/done） |
| `milestone` | 里程碑达成 | — |
| `note` | 通用备注 | — |

## 2. 字段组合约束（服务端强制）

| 字段 | 取值 | 适用范围 |
|---|---|---|
| `severity` | `low` / `medium` / `high` | **仅** `difficulty` / `blocker` |
| `status` | `open` / `done` | **仅** `todo` / `blocker` |
| `related_task_ids` | 本项目内任务 id 数组 | 任一越权 → 整条拒绝 |
| `git_ref` | commit/分支名，≤100 | 所有类型（溯源用） |

- `status="done"` 时自动盖章 `resolved_at`；改回 `open` 则清空。
- 修改 `entry_type` 时服务端会自动校正：非 todo/blocker 强制 `status=open`；
  非 difficulty/blocker 清空 `severity`。
- `resolve_dev_log` 仅对 `todo` / `blocker` 生效，其他类型报错。

## 3. 会话生命周期（DevSession）

一次 AI 编码会话 = 一个 `DevSession`：

```
start_dev_session(project_id, title)   # 会话开始，ended_at=null
        │
        ▼
log_* 写入（未指定 session 时自动归入最近的未结束会话）
        │
        ▼
end_dev_session(session_id, summary)   # 收口：盖章 ended_at + 写入总结
```

- `start_dev_session` 返回的 `DevSession.id` 可用于后续 `log_*(..., session_id=?)`
  显式归入；不传则自动归入最近的未结束会话。
- 一个项目可同时存在多个未结束会话；`get_project_state` 会返回最近的一个作为
  `active_session`。

## 4. 每次会话建议遵循的流程

```
1. 开始会话：start_dev_session(project_id, title)
2. 过程中随手写：
   - 完成一件值得记录的事 → log_progress（附 git_ref）
   - 卡住 / 绕过的坑       → log_difficulty（附 severity）
   - 下一步要做的事       → log_todo
   - 拍板的技术方案及理由 → log_decision
   - 无法推进的阻塞项     → log_blocker（默认 severity=high）
3. 结束时收口：end_dev_session(session_id, summary)
4. 新会话开始前，先 get_project_state(project_id) 恢复上下文
```

## 5. 完整示例：一次会话的写法

```
start_dev_session(project_id=1, title="实现登录模块")
# => { "id": 3, "project_id": 1, "title": "实现登录模块", "ended_at": null, ... }

log_progress(project_id=1, title="完成 JWT 签发与校验", git_ref="a1b2c3d")
log_difficulty(project_id=1, title="异步客户端挂起", severity="high",
               content="httpx 未用 async with 导致连接泄漏")
log_todo(project_id=1, title="补充登录接口的单元测试")
log_decision(project_id=1, title="选用 SQLAlchemy 2.0 异步",
             content="与现有 FastAPI 生态一致，避免双 ORM")
log_blocker(project_id=1, title="等待依赖方提供测试环境", severity="high")

end_dev_session(session_id=3, summary="完成认证流程与 12 个单测")
```

## 6. 写作规范（给 AI 的约束）

- `title` 用一句动宾短语概括，≤200 字符；`content` 补充上下文/原因/数据。
- `git_ref` 建议每次 `log_progress` 都带上当前 commit/分支名，便于溯源。
- 不要用 DevLog 替代任务管理：需要追踪可勾选的结果项 → `create_task`；
  记录过程中的轻量待办 → `log_todo`。
- 记录要克制：值得被后来者看到的才写，避免噪音。
- 汇报口径：`get_dev_report` 按 progress→milestone→difficulty→blocker→todo→decision→note
  顺序分组生成 Markdown，AI 与人共用同一份报告。

## 7. 常见错误

| 错误 | 原因 | 处理 |
|---|---|---|
| `related_task_ids 中存在不属于该项目的任务` | 关联了本项目外的任务 | 核对任务 id |
| `仅 todo / blocker 条目可标记完成` | 对 progress 等调用 `resolve_dev_log` | 改用 `update_dev_log(status=...)` 或换条目 |
| `severity 仅可用于 difficulty / blocker` | 给 progress/todo 传了 severity | 去掉 severity |
| `status 仅可用于 todo / blocker` | 给 progress 等传 status | 去掉 status |