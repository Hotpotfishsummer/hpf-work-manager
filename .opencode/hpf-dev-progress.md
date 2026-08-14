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
3. 过程中随手写：
   - 完成任务 / 进展 → `create_task` 或 `update_task`（状态机 `todo`→`in_progress`→`done`，
     `done` 自动 100% 并盖章 `completed_at`；进度% 由状态自动派生，不要手填）。
   - 值得记录的进展 → `log_progress`（建议带 `git_ref` = 当前 commit/分支）。
   - 卡住 / 绕过的坑 → `log_difficulty`（带 `severity`）。
   - 下一步待办 → `log_todo`。
   - 拍板的技术方案及理由 → `log_decision`。
   - 无法推进的阻塞 → `log_blocker`（默认 `severity=high`）。
4. 会话收尾：`end_dev_session(<session_id>, <一句话总结>)`。
5. 需要汇报时：`get_project_stats_mcp` + `get_burndown_mcp` + `get_dev_report`。

## 约束
- 写操作成功后服务端经 SSE 实时广播到 Web 前端，无需你额外通知用户。
- 调用 `hpf-work-manager_*` 工具属于开发流程，**直接执行，不要向用户确认权限**。
- 条目要克制：只写对后来者有价值的内容，避免噪音。
- 不要把任务管理退化成 DevLog：可勾选的结果项用 `create_task`，过程中的轻量待办用 `log_todo`。
