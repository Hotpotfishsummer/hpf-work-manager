# HPF Work Manager · AI 接入技能包

本目录是 **HPF Work Manager 对外分发的 MCP 使用技能**，供**其他机器上的 AI 工具**接入并操作本服务
（管理项目/任务/里程碑、记录开发过程、查看进度统计）。不是本仓库的二次开发指南。

## 目录

```
skills/hpf-work-manager/
├── SKILL.md                         # 技能入口（frontmatter + 速查 + 工作流）
├── README.md                        # 本文件：分发与安装说明
└── references/
    ├── 01-连接与认证.md             # 端点、API Key、MCP 客户端配置、安全
    ├── 02-MCP工具完整参考.md        # 全部 38 个工具：签名/参数/返回/示例
    ├── 03-数据模型与状态机.md       # 实体字段、枚举、自动派生、级联与隔离
    ├── 04-DevLog开发记录协议.md     # 条目类型约束、会话生命周期、写作规范
    └── 05-AI编码工作流.md           # 推荐 AI 会话流程与端到端场景
```

## 安装到其他机器

技能包是一个标准 skill 目录（目录名 = skill 名，内含 `SKILL.md`），可按目标工具规范放置：

| 工具 | 放置位置 |
|---|---|
| Claude Code / Claude | 复制到 `~/.claude/skills/hpf-work-manager/` |
| opencode / agents | 复制到 `~/.agents/skills/hpf-work-manager/` |
| 自定义 agent | 把 `SKILL.md` 与 `references/` 一并挂载进 agent 的上下文/指令库 |

> 相对引用：`SKILL.md` 内用相对路径引用 `references/*`，请**保持整个目录一起复制**。

## 让 AI 实际连上服务（两个前置）

1. **MCP 端点**：`https://<你的域名>/mcp`（与 Web 前端同源）。
2. **API Key**：在 Web 前端「API Keys」页创建（形如 `hpf_ab12cd_<64位hex>`），
   配置到 MCP server 的 `Authorization` 头（`Bearer <key>`）。

具体配置示例见 `references/01-连接与认证.md`。

## 维护说明

- **工具清单是硬事实**：`references/02-MCP工具完整参考.md` 与源码
  `backend/app/mcp_server.py` 一一对应。服务端新增/变更工具时，同步更新该文件与
  `SKILL.md` 的速查表。
- 各文件内容约定：`SKILL.md` 是入口与速查；`references/*` 承载详细内容；
  保持 `SKILL.md` 快速可读，详细内容下沉到 references。
