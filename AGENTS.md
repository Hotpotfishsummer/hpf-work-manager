# AGENTS.md — AI 编码代理项目约定

本文件供在此仓库工作的 AI 编码代理（Claude Code / Cursor / opencode 等）遵循。人类开发者同样适用。

## 开发完成后的部署对齐（必做）

**功能开发推送到 `main` 后，必须同步部署到生产服务器，保持线上版本与仓库对齐。**

标准流程（备份 → 拉取 → 重建 → 验证）见 [`docs/06-开发指南.md`](docs/06-开发指南.md) 第 7 节与 [`docs/05-部署指南.md`](docs/05-部署指南.md) 第 6 节。服务器地址等环境信息维护在本地 `.workbuddy/DEPLOY.md`（已 gitignore）。

流程摘要：

```bash
# 1. 备份数据库（更新前必做）
# 2. git pull --ff-only
# 3. docker compose -f docker-compose.yml up -d --build   # -f 必须显式
# 4. 验证：容器 healthy + /api/health + alembic 迁移日志
```

## 开发纪律

1. **测试先行验证**：后端改动跑 `pytest`（`backend/tests/`），前端改动跑 `npx vitest run` + `npm run build`；相关测试不过不提交
2. **状态对账**：任务状态变更必须有代码 + git 证据（通过 MCP `update_task` 据实更新，绝不凭假设标 done）
3. **DevLog 记录**：开发会话用 MCP 工具记录（`start_dev_session` → `log_*` → `end_dev_session`），见 `skills/hpf-work-manager/`
4. **公开仓库纪律**：本仓库是 PUBLIC 的——服务器 IP、密码、API Key 等只写本地 `.workbuddy/`，严禁提交
5. **文档同步**：新增/变更 MCP 工具时同步更新 `skills/hpf-work-manager/references/02-MCP工具完整参考.md` 与 `SKILL.md` 速查表（工具清单与 `backend/app/mcp_server.py` 一一对应）；涉及部署流程变更时同步 `docs/06-开发指南.md` 第 7 节

## 快速参考

| 事项 | 位置 |
|---|---|
| 架构 / API / 数据模型 | `docs/01` / `docs/03` / `docs/02` |
| 部署与更新 | `docs/05-部署指南.md`、`docs/06-开发指南.md` 第 7 节 |
| 生产环境信息（本地） | `.workbuddy/DEPLOY.md` |
| MCP 接入技能包 | `skills/hpf-work-manager/` |
| 设计规范 | `DESIGN.md`（Material Design 3，分层靠色阶与间距、分区不描边，禁内联 hex） |

<!-- agent-harness:begin -->
## agent-harness 契约（本 worktree 分支 `feat/md3-design-consistency`）

事实来源三件套：`app_spec.md` / `feature_list.json` / `progress.md`（本文件只是入口）。

- **开工前必读**：`progress.md` → `feature_list.json`（未通过项）→ `git log --oneline -20`。
- 只允许改 feature 的 `passes` / `notes` / `blocked`；`description` 与 `steps` **永不改**。
- `passes: true` 之前必须有**实际跑过的** evidence（命令输出 / 测试结果 / 截图路径）。
- `blocked: true` 或以 `⚠️ 待用户裁决` 开头的 feature：不要动；汇报里单独列「需要你裁决的 N 项」。
- **用户没说开工就不要开工。** 只有 3 类问题必须立刻问：改系统级配置 / 删数据 / 花钱。
- 每个 feature 完成 = 1 个 commit，`feat(F005): xxx`，写 why 不写 what。
- 收尾前跑 `bash init.sh && bash check.sh`，两个都绿才算收口。
- **本分支不合并、不 push、不重建容器**：合并与部署由用户裁决。
- 规范闸门：`cd frontend && npx vitest run tests/design-tokens.spec.ts`；色值只准出现在 `src/design/tokens.css`。
<!-- agent-harness:end -->
