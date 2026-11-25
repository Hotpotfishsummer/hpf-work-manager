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
共 **28 个工具**，覆盖：AI 驱动与双重认证协同、项目、里程碑、任务、任务依赖、任务评论、进度统计，以及 DevLog 开发记录与开发会话。
AI 编码工具可在编码过程中自动维护任务状态、记录开发过程，并实时同步到 Web 前端。

本技能用于**让其他机器上的外部 AI Agent 接入并操作该服务**（不是本仓库的二次开发指南）。

---

## 1. 快速接入（30 秒）

连接端点与认证方式：

| 环境 | MCP 端点 URL | 认证要求 |
|---|---|---|
| **Tailscale 局域专网 (推荐)** | `http://100.69.225.112:8088/mcp` | **免鉴权**（自动以 admin 身份执行）或可选带 API Key |
| **服务器宿主本地** | `http://127.0.0.1:8088/mcp` | **免鉴权**（自动以 admin 身份执行） |
| **公网域名 / 反向代理** | `https://<你的域名>/mcp` | 携带 Header `Authorization: Bearer <API Key>` |

各主流客户端配置极简范例：

- **Claude Code 一键命令**：
  ```bash
  claude mcp add --transport http hpf-work-manager http://100.69.225.112:8088/mcp
  ```
- **Cursor IDE**：
  项目根目录 `.cursor/mcp.json`：
  ```json
  {
    "mcpServers": {
      "hpf-work-manager": { "url": "http://100.69.225.112:8088/mcp" }
    }
  }
  ```
- **Windsurf**：在 `~/.codeium/windsurf/mcp_config.json` 中配置 `"serverUrl": "http://100.69.225.112:8088/mcp"`。
- **Cline / Roo Code**：在 `cline_mcp_settings.json` 中填入该 URL 即可。

详细多客户端步骤、端点说明与排障见 [`references/01-连接与认证.md`](references/01-连接与认证.md)。

---

## 2. 工具速查（28 个，2026-11-25 由 44 个合并瘦身）

> 完整签名、参数、返回值与示例见 [`references/02-MCP工具完整参考.md`](references/02-MCP工具完整参考.md)。
> 双重认证协同机制与外驱规范详见 [`references/06-双重认证与外驱协同协议.md`](references/06-双重认证与外驱协同协议.md)。

### AI Driver & 双重认证协同（4）
| 工具 | 作用 |
|---|---|
| `get_manager_status` | 查询管理器算力配额与 Agent 驱动模式（双重认证 DUAL_CERTIFIED vs 外部单驱 EXTERNAL_DRIVEN）及行动指南 |
| `get_next_steps` | 获取指定项目的下一步落地建议（内部有额度时模型推演，额度耗尽时自动降级为代码库启发式规则推演） |
| `propose_task_plan` | 【双重认证核心】提交多项任务规划提案；由内部架构师交叉审查（防幻觉与劣质规划）或规则护栏校验，可选直接写入看板 |
| `verify_and_complete_task` | 【双重认证核销】交付完成任务；必须提供真实 git commit hash 与验收测试凭证，自动完成并写入关联 DevLog |

> 原 `brainstorm_ideas` / `sync_local_projects` 已移出 MCP，走前端 UI 或 REST（`/api/ideator/brainstorm`、`/api/ideator/sync-projects`）。

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

### 任务（5）
| 工具 | 作用 |
|---|---|
| `list_tasks` | 列出项目任务（可按 `status`/`overdue`/`search` 过滤） |
| `get_task` | 单任务详情（含 `depends_on` id 列表与 `depends_on_detail` 名称/状态/进度，判断可否开工） |
| `create_task` | 创建任务 |
| `update_task` | 更新任务（含状态机；**依赖管理并入**：`add_depends_on` / `remove_depends_on` 传前置任务 id 列表） |
| `delete_task` | 删除任务 |

### 统计（1）
| 工具 | 作用 |
|---|---|
| `get_project_stats` | 项目统计，`kind` 取值：`overview`（进度/延期，默认）/ `burndown`（燃尽）/ `gantt`（甘特）/ `devlog`（记录统计）；返回 `{"kind", "data"}` |

### 任务评论（2）
| 工具 | 作用 |
|---|---|
| `add_comment` | 为任务添加评论（1-2000 字符） |
| `list_comments` | 列出任务评论（升序，分页）。删除评论走前端 UI / REST |

### 开发记录 DevLog（7）
| 工具 | 作用 |
|---|---|
| `start_dev_session` / `end_dev_session` | 开发会话开始 / 收口 |
| `log_dev_entry` | 写入开发记录，`entry_type` ∈ progress/difficulty/todo/decision/blocker/note；`severity` 仅 difficulty（默认 medium）/blocker（默认 high） |
| `list_dev_logs` | 查询记录（按 `entry_type`/`status`/`since` 过滤） |
| `get_project_state` | 上下文聚合包（新会话恢复用） |
| `get_dev_report` | 生成阶段开发汇报（Markdown） |
| `manage_dev_log` | 记录维护，`action` ∈ `update` / `resolve`（仅 todo/blocker）/ `delete` |

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
1. start_dev_session(project_id, title)   → 后续 log_dev_entry 自动归入
2. 过程中随手写 log_dev_entry(entry_type=progress/difficulty/todo/decision/blocker/note, ...)
3. 结束时 end_dev_session(session_id, summary)
4. 新会话先 get_project_state(project_id) 恢复上下文
```

条目约束：
- `entry_type` ∈ `progress / difficulty / todo / decision / blocker / milestone / note`
- `severity`（low/medium/high）仅用于 `difficulty` / `blocker`
- `status`（open/done）仅用于 `todo` / `blocker`；`manage_dev_log(action="resolve")` 仅对这两类生效
- `related_task_ids` 必须是**本项目内**的任务，否则拒绝
- `git_ref` 填 commit 或分支名，仅作溯源引用（系统不解析 git）

### 3.3 数据隔离与权限
- 所有工具只操作**当前认证用户**自己的数据（`owner_id` 隔离），访问他人数据会报错"不存在"。
- 所有写操作都是**完整 CRUD** 权限；只向可信工具发放 API Key。
- 每次写操作成功后，服务会通过 **SSE** 实时广播给 Web 前端，无需 AI 手动通知。

### 3.4 错误返回
工具失败时返回一条描述性错误（如"任务 42 不存在""related_task_ids 中存在不属于该项目的任务"）。
收到错误先自查：ID 是否正确、枚举是否合法、依赖/关联是否属于本项目。

### 3.5 双重认证协同与防劣质规划约定（重要）
- **开工前感知模式**：会话启动时先调用 `get_manager_status`。
  - `driver_mode="DUAL_CERTIFIED"`：说明内部 MiniMax 算力充足。新规划批量提交建议走 `propose_task_plan`，让内部架构师模型交叉审核（消除低端模型幻觉与不合理安排）。
  - `driver_mode="EXTERNAL_DRIVEN"`：说明内部额度耗尽，已降级为确定性规则护栏模式。外部 Agent 承担完整规划职责，须明确工时与验收标准。
- **任务完成必须提供核验凭证**：
  严禁未核验代码凭假设标 done。推荐使用 `verify_and_complete_task` 工具，必须提供真实的 `git_ref`（commit hash）与 `verification_evidence`（测试结果/改动凭证），管理器将自动完成任务并生成关联的 DevLog 交付记录。

---

## 3.6 排障：挂载着却看不到 `mcp__work_manager__*` 工具（头号根因）

**现象**：dsh 侧 `mcp-work-manager` 条目明明在配置里，但工具列表里没有
`mcp__work_manager__*`；`list_mcp_resources` 报 `server is disconnected`。

**根因**：服务重部署期间连接中断，mcp-client 的 `reconnect.maxAttempts` 耗尽后
**永久放弃**（日志 `giving up after N consecutive failed reconnect attempts — tools unregistered`）。
默认 10 次只覆盖 ≈2.5 分钟，**扛不住一次重部署**。

**诊断顺序**：

```bash
docker inspect -f '{{.State.StartedAt}}' hpf-work-manager-frontend-1   # 看重部署时刻
# 与 dsh 进程启动时刻比对；若重部署晚于 dsh 启动 → 就是这个坑
```

**修**：改 `reconnect.maxAttempts`（或把该 MCP 条目重启一次）→ 重启 dsh。

**另一个相邻坑**：MCP 端点 `http://100.69.225.112:8088/mcp/` —— **结尾斜杠必须留**，
否则 nginx 307 重定向，客户端可能跟不过去。

---

## 4. 推荐工作流（详见 references/05）

**新项目**：`create_project` → `create_milestone` → 批量 `create_task`（建依赖）→ 开发中更新状态。

**日常编码**：
```
get_manager_status                                  # 探活：确认当前驱动模式与算力余量
list_projects → get_project_state(project_id)      # 恢复上下文
start_dev_session(project_id, title)                # 记录本次会话
list_tasks(status="todo"/"in_progress") + list_tasks(overdue=true)  # 拉全量开放任务
... 对每张开放任务：get_task → 在仓库核验(代码+git) → 据实 update_task(progress)
... 本次完成工作 → verify_and_complete_task(task_id, git_ref, verification_evidence)
... 新规划推演/批量提案 → propose_task_plan / get_next_steps
... 随手写 → log_dev_entry(entry_type=...)
end_dev_session(session_id, summary)                # 收口
get_dev_report(project_id)                          # 出阶段汇报
```

> 开发中对**所有开放任务（todo / in_progress / 逾期）**都要做状态审计：先 `list_tasks` 拉全量，
> 再逐一 `get_task` 并在仓库核验真实完成情况（读相关代码 + `git log`/`git diff` 找对应 commit），
> **据实更新 `progress`（部分完成填 1–99%），确证已合并/落地走 `verify_and_complete_task` 盖章归档**。
> 状态变更必须有代码 + git 证据，绝不凭假设标 done，也绝不 `delete_task`。

**汇报**：`get_project_stats(kind="overview")`（进度）+ `get_project_stats(kind="burndown")`（趋势）+ `get_dev_report`（过程）。

完整场景示例见 [`references/05-AI编码工作流.md`](references/05-AI编码工作流.md)。

---

## 5. 详细文档索引

| 文档 | 内容 |
|---|---|
| [`01-连接与认证`](references/01-连接与认证.md) | 端点、API Key、MCP 客户端配置、安全与防重绑定 |
| [`02-MCP工具完整参考`](references/02-MCP工具完整参考.md) | 全部 28 个工具：签名/参数/枚举/返回/示例 |
| [`03-数据模型与状态机`](references/03-数据模型与状态机.md) | 实体字段、枚举、自动派生、级联与隔离 |
| [`04-DevLog开发记录协议`](references/04-DevLog开发记录协议.md) | 条目类型约束、会话生命周期、写作规范 |
| [`05-AI编码工作流`](references/05-AI编码工作流.md) | 推荐 AI 使用流程与端到端场景 |
| [`06-双重认证与外驱协同协议`](references/06-双重认证与外驱协同协议.md) | 双重认证、外驱降级安全护栏、提案审查与核销协议 |

