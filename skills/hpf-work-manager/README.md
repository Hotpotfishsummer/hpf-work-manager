# HPF Work Manager · AI 接入技能包

本目录是 **HPF Work Manager 对外分发的 MCP 使用技能与外部 Agent 接入套件**，供**跨机器、跨终端的外部 AI 编码工具**（如 Claude Code、Cursor、Antigravity、Windsurf、Cline、dsh 等）接入并操作本服务（任务规划、双重认证审查、防假交付核销、开发记录追踪、进度看板实时同步）。

## 目录

```
skills/hpf-work-manager/
├── SKILL.md                         # 技能总入口（frontmatter + 速查 + 工作流与双重认证协议）
├── README.md                        # 本文件：分发与安装说明
└── references/
    ├── 01-连接与认证.md             # 外部 Agent 接入全景指南（多客户端导入配置、Tailscale/免鉴权模式、排障）
    ├── 02-MCP工具完整参考.md        # 全部 44 个工具：签名/参数/返回/示例（含 6 个新 AI 驱动工具）
    ├── 03-数据模型与状态机.md       # 实体字段、枚举、自动派生、级联与隔离
    ├── 04-DevLog开发记录协议.md     # 条目类型约束、会话生命周期、写作规范
    ├── 05-AI编码工作流.md           # 推荐 AI 会话流程与端到端场景
    └── 06-双重认证与外驱协同协议.md # 双模态协作、Cross-Audit 机制与凭证核销流水线
```

## 安装到外部 Agent 客户端

技能包是一个标准 skill 目录（目录名 = skill 名，内含 `SKILL.md`），可直接分发至目标 Agent 环境：

| 客户端环境 | 推荐放置/挂载位置 | 导入配置说明 |
|---|---|---|
| **Claude Code** | `~/.claude/skills/hpf-work-manager/` | 执行 `claude mcp add --transport http hpf-work-manager http://100.69.225.112:8088/mcp` |
| **Cursor IDE** | 项目根目录 `.cursor/mcp.json` 或 Settings GUI | URL 填入 `http://100.69.225.112:8088/mcp`，传输类型选 `sse` 或 `http` |
| **Antigravity** | `.gemini/antigravity/mcp/` 或全局 MCP 配置文件 | 配置 `http://100.69.225.112:8088/mcp` |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` | 配置 `serverUrl: "http://100.69.225.112:8088/mcp"` |
| **Cline / Roo Code** | `cline_mcp_settings.json` | 添加 MCP server 配置并开启核心工具自动批准 |
| **dsh (Manjaro)** | `/home/hotpotfish/dsh/dsh-home/skills/hpf-work-manager/` | 零配置直连本机 `http://127.0.0.1:8088/mcp` |

> 相对引用说明：`SKILL.md` 内用相对路径引用 `references/*`，请**保持整个目录一起复制**。

## 零门槛连接（Tailscale 专网免鉴权）

1. **MCP 端点**：
   - Tailscale 专网（推荐）：`http://100.69.225.112:8088/mcp`
   - 本机回环：`http://127.0.0.1:8088/mcp`
2. **鉴权说明**：
   - **内网免鉴权**：在 Tailscale 专网或 Localhost 访问时，外部 Agent **无需任何 Header**，服务端自动回退以 `admin` 身份放行。
   - **API Key 审计**：如需区分多个外部 Agent 审计日志，可在 Web 端「API Keys」页面生成密钥，配置在 `Authorization: Bearer <key>` 请求头中。

具体多客户端详细配置与排障示例见 `references/01-连接与认证.md`。

## 维护说明

- **工具清单是硬事实**：`references/02-MCP工具完整参考.md` 与源码 `backend/app/mcp_server.py` 一一对应（共 44 个工具）。
- 服务端新增/变更工具时，同步更新该文件与 `SKILL.md` 的速查表。
