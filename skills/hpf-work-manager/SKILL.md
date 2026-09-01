---
name: hpf-work-manager-mcp
description: >
  通过 HPF Work Manager 的 MCP Server 接口，让 AI 编码工具在其他机器上读写任务/项目管理数据：
  管理项目、里程碑、任务、任务依赖，读取进度/燃尽/甘特统计，并记录 DevLog 开发过程（进展/难点/待办/决策/阻塞/备注）与会话。
  当用户要求连接或调用 HPF 工作管理器、更新任务状态/进度、创建或查询项目/任务/里程碑、记录开发过程或开发汇报、查看看板/燃尽/甘特数据时使用本技能。
  不触发场景：仅讨论通用前后端代码、目标不是 HPF Work Manager 服务的其他 MCP 服务、或只是解释概念而不连接本服务。
---

# HPF Work Manager · MCP 使用技能

HPF Work Manager 是一个**任务 / 项目管理与进度追踪服务**。它对外暴露一个 **MCP Server**（Streamable HTTP），
共 **35 个工具**，覆盖：项目、里程碑、任务、任务依赖、进度统计，以及 DevLog 开发记录与开发会话。
AI 编码工具可在编码过程中自动维护任务状态、记录开发过程，并实时同步到 Web 前端。

本技能用于**让其他机器上的 AI 工具接入并操作该服务**（不是本仓库的二次开发指南）。

---

## 1. 快速接入（30 秒）

前置条件只有两样：

| 需要 | 获取方式 |
|---|---|
| MCP 端点地址 | `https://<你的域名>/mcp`（与 Web 前端同源，nginx 已反代） |
| API Key | 登录 Web 前端 → 「API Keys」→ 新建（形如 `hpf_ab12cd_<64位hex>`，**仅显示一次**） |

然后按你的工具配置一个 HTTP MCP server：

- **Claude Code**（`.mcp.json`）：
  ```json
  {
    "mcpServers": {
      "hpf-work-manager": {
        "type": "http",
        "url": "https://<你的域名>/mcp",
        "headers": { "Authorization": "Bearer hpf_ab12cd_<你的API Key>" }
      }
    }
  }
  ```
- **Cursor**：Settings → MCP Servers → Add；Type=`HTTP`，URL=`https://<你的域名>/mcp`，Header=`Authorization: Bearer hpf_ab12cd_<你的API Key>`。
- 认证头同样支持 **JWT**（`Bearer <jwt>`），二选一。

详细步骤、端点说明、安全注意事项见 [`references/01-连接与认证.md`](references/01-连接与认证.md)。

---

## 2. 工具速查（35 个）

> 完整签名、参数、返回值与示例见 [`references/02-MCP工具完整参考.md`](references/02-MCP工具完整参考.md)。

### 项目（5）
| 工具 | 作用 |
|---|---|
| `list_projects` | 列出当前用户所有项目 |
| `get_project` | 单项目详情 |
| `create_project` | 创建项目 |
| `update_project` | 更新项目（名称/描述/状态/起止日期） |
| `delete_project` | 删除项目（级联删除任务与里程碑） |

### 里程碑（4）
| 工具 | 作用 |
|---|---|
| `list_milestones` | 列出项目里程碑（按 due_date 升序） |
| `create_milestone` | 创建里程碑 |
| `update_milestone` | 更新里程碑 |
| `delete_milestone` | 删除里程碑（其下任务保留） |

### 任务（8）
| 工具 | 作用 |
|---|---|
| `list_tasks` | 列出项目任务（可按 `status`/`overdue` 过滤） |
| `get_task` | 单任务详情 |
| `create_task` | 创建任务 |
| `update_task` | 更新任务（含状态机） |
| `delete_task` | 删除任务 |
| `add_task_dependency` | 添加任务依赖（前者依赖后者） |
| `remove_task_dependency` | 移除任务依赖 |
| `list_task_dependencies` | 列出任务前置依赖（含名称/状态，判断可否开工） |

### 统计（3）
| 工具 | 作用 |
|---|---|
| `get_project_stats_mcp` | 项目进度统计（总数/完成/进行中/待办/进度%/延期列表） |
| `get_burndown_mcp` | 燃尽图数据（期望线 + 实际线） |
| `get_gantt_mcp` | 甘特图数据（任务 + 依赖） |

### 开发记录 DevLog（15）
| 工具 | 作用 |
|---|---|
| `start_dev_session` / `end_dev_session` | 开发会话开始 / 收口 |
| `log_progress` / `log_difficulty` / `log_todo` / `log_decision` / `log_blocker` / `log_note` | 写入开发记录 |
| `list_dev_logs` | 查询记录（按 `entry_type`/`status`/`since` 过滤） |
| `get_dev_log_stats_mcp` | 记录统计（今日/难点/待办/阻塞/决策） |
| `get_project_state` | 上下文聚合包（新会话恢复用） |
| `get_dev_report` | 生成阶段开发汇报（Markdown） |
| `update_dev_log` / `delete_dev_log` / `resolve_dev_log` | 记录维护（`resolve` 仅 todo/blocker） |

---

## 3. 核心约定（务必遵守）

### 3.1 任务状态机（自动派生，无需手动维护）
- `status="done"` → 自动 `progress=100` 并盖章 `completed_at`。
- `status` 改为非 `done` → 自动清空 `completed_at`。
- `status="done"` 时 `progress` 写入被忽略。
- **延期（overdue）是派生字段**：`status!=done` 且 `due_date < 今天`。前端三处高亮、统计接口都会给出。

枚举值：
- `status`：`todo` / `in_progress` / `done`
- `priority`：`low` / `medium` / `high`
- 项目/里程碑 `status`：`active` / `archived`（里程碑为 `active` / `done`）

### 3.2 DevLog 协议（过程叙事）
DevLog 记录"开发过程"，任务/里程碑管"结果"。写记录前先开会话：

```
1. start_dev_session(project_id, title)   → 后续 log_* 自动归入
2. 过程中随手写 log_progress / log_difficulty / log_todo / log_decision / log_blocker / log_note
3. 结束时 end_dev_session(session_id, summary)
4. 新会话先 get_project_state(project_id) 恢复上下文
```

条目约束：
- `entry_type` ∈ `progress / difficulty / todo / decision / blocker / milestone / note`
- `severity`（low/medium/high）仅用于 `difficulty` / `blocker`
- `status`（open/done）仅用于 `todo` / `blocker`；`resolve_dev_log` 仅对这两类生效
- `related_task_ids` 必须是**本项目内**的任务，否则拒绝
- `git_ref` 填 commit 或分支名，仅作溯源引用（系统不解析 git）

### 3.3 数据隔离与权限
- 所有工具只操作**当前认证用户**自己的数据（`owner_id` 隔离），访问他人数据会报错"不存在"。
- 所有写操作都是**完整 CRUD** 权限；只向可信工具发放 API Key。
- 每次写操作成功后，服务会通过 **SSE** 实时广播给 Web 前端，无需 AI 手动通知。

### 3.4 错误返回
工具失败时返回一条描述性错误（如"任务 42 不存在""related_task_ids 中存在不属于该项目的任务"）。
收到错误先自查：ID 是否正确、枚举是否合法、依赖/关联是否属于本项目。

---

## 4. 推荐工作流（详见 references/05）

**新项目**：`create_project` → `create_milestone` → 批量 `create_task`（建依赖）→ 开发中更新状态。

**日常编码**：
```
list_projects → get_project_state(project_id)      # 恢复上下文
start_dev_session(project_id, title)                # 记录本次会话
list_tasks(status="todo"/"in_progress") + list_tasks(overdue=true)  # 拉全量开放任务
... 对每张开放任务：get_task → 在仓库核验(代码+git) → 据实 update_task(progress) / 确证完成标 done
... 本次新做且无对应旧任务的工作 → create_task
... 随手写 → log_progress / log_difficulty / log_todo ...
end_dev_session(session_id, summary)                # 收口
get_dev_report(project_id)                          # 出阶段汇报
```

> 开发中对**所有开放任务（todo / in_progress / 逾期）**都要做状态审计：先 `list_tasks` 拉全量，
> 再逐一 `get_task` 并在仓库核验真实完成情况（读相关代码 + `git log`/`git diff` 找对应 commit），
> **据实更新 `progress`（部分完成填 1–99%），确证已合并/落地才 `update_task(status="done", git_ref=commit)`**。
> 状态变更必须有代码 + git 证据，绝不凭假设标 done，也绝不 `delete_task`。

**汇报**：`get_project_stats_mcp`（进度）+ `get_burndown_mcp`（趋势）+ `get_dev_report`（过程）。

完整场景示例见 [`references/05-AI编码工作流.md`](references/05-AI编码工作流.md)。

---

## 5. 详细文档索引

| 文档 | 内容 |
|---|---|
| [`01-连接与认证`](references/01-连接与认证.md) | 端点、API Key、MCP 客户端配置、安全与防重绑定 |
| [`02-MCP工具完整参考`](references/02-MCP工具完整参考.md) | 全部 34 个工具：签名/参数/枚举/返回/示例 |
| [`03-数据模型与状态机`](references/03-数据模型与状态机.md) | 实体字段、枚举、自动派生、级联与隔离 |
| [`04-DevLog开发记录协议`](references/04-DevLog开发记录协议.md) | 条目类型约束、会话生命周期、写作规范 |
| [`05-AI编码工作流`](references/05-AI编码工作流.md) | 推荐 AI 使用流程与端到端场景 |
