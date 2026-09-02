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
| 设计规范 | `DESIGN.md`（BMW 风格 token，禁内联 hex） |
