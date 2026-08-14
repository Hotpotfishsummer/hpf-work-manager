# HPF Work Manager · 自动进度同步指令

本仓库就是 HPF Work Manager 本身。项目配套一个运行中的 HPF Work Manager 服务，
通过 MCP server `hpf-work-manager`（地址 http://100.69.225.112:8088/mcp）对外提供
34 个工具，用于管理项目 / 里程碑 / 任务 / 依赖 / 统计，以及记录开发过程（DevLog / DevSession）。

**你在开发本应用时应自主、主动地通过该 MCP 维护开发进度，无需每次向用户确认或等待指令。**
这是正常开发流程的一部分，不是可选操作。

## 固定上下文
- 目标项目：**project_id = 1（「HPF Work Manager」）**，恒用此项目。
- 服务地址 `http://100.69.225.112:8088`，认证已由 opencode.json 的 MCP headers 携带，直接调用工具即可。

## 何时调用（自主判断）
只要进入一段有意义的开发工作（实现功能、修复缺陷、重构、配置/部署改动等），就按下面流程走；
不必等用户说"记录一下"。零散的小改动可合并到下一次会话里记录。

## 标准流程
1. 开始会话前：`get_project_state(1)` 恢复上下文（看未完成任务 / 活跃 DevSession）。
2. `start_dev_session(1, <本次主题，一句动宾短语>)` 开启本次开发会话。
3. **任务状态审计（必做）**：拉全量开放任务作为基线，合并去重 ——
   `list_tasks(1, status="todo")` + `list_tasks(1, status="in_progress")` + `list_tasks(1, overdue=true)`。
   对每一张开放任务逐一核验并据实更新：
   - `get_task(<任务id>)` 看清验收点；
   - 在仓库核验真实完成情况：grep / 读相关代码文件，并用 `git log` / `git diff` 找对应 commit；
   - 按实际完成度 `update_task(<任务id>, progress=N)`（部分完成填 1–99%；只有 `done` 时进度才强制 100%）；
   - 确证已合并 / 落地 → `update_task(<任务id>, status="done", git_ref=commit)`；
   - 仍 open / 停滞 → 保留 open，可 `log_todo` 提示；**绝不 `delete_task`**。
4. 过程中随手写（仅限"本次新做、且无对应旧任务"的工作）：
   - 确无对应旧任务的新工作 → `create_task`（状态机 `todo`→`in_progress`→`done`，`done` 自动 100% 并盖章 `completed_at`）。
   - 值得记录的进展 → `log_progress`（建议带 `git_ref` = 当前 commit/分支）。
   - 卡住 / 绕过的坑 → `log_difficulty`（带 `severity`）。
   - 下一步待办 → `log_todo`。
   - 拍板的技术方案及理由 → `log_decision`。
   - 无法推进的阻塞 → `log_blocker`（默认 `severity=high`）。
5. 会话收尾：`end_dev_session(<session_id>, <一句话总结>)`。
6. 需要汇报时：`get_project_stats_mcp` + `get_burndown_mcp` + `get_dev_report`。

## 约束
- 写操作成功后服务端经 SSE 实时广播到 Web 前端，无需你额外通知用户。
- 调用 `hpf-work-manager_*` 工具属于开发流程，**直接执行，不要向用户确认权限**。
- 条目要克制：只写对后来者有价值的内容，避免噪音。
- 不要把任务管理退化成 DevLog：可勾选的结果项用 `create_task`，过程中的轻量待办用 `log_todo`。
- 审计 / 对账只更新有证据（代码 + git commit）的任务；**状态变更必须有代码 + git 证据，绝不凭假设标 done**；
  **绝不 `delete_task`**（状态机不可逆，留痕优先）。
- `progress` 反映真实完成度（可部分 1–99%），不是非 0 即 100%。
