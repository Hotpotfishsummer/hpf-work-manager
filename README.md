# HPF Work Manager

任务 / 项目管理与进度追踪 Web 应用。前后端分离架构，前端 Vue 3 + TypeScript，后端 Python FastAPI，全容器化部署（Docker Compose）。

UI 遵循 **Apple × Material Design 3 设计系统**（见根目录 [`DESIGN.md`](./DESIGN.md)，支持浅色/深色双主题）。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3.5 · Vite · TypeScript · Pinia · Vue Router · Element Plus · frappe-gantt (MIT) · ECharts 5 · Inter 字体 |
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · asyncpg · Alembic · PyJWT · passlib[bcrypt] |
| 数据库 | PostgreSQL 16 |
| 部署 | Docker Compose（frontend/nginx + backend/uvicorn + postgres） |

## 文档

完整项目文档见 [`docs/`](./docs) 目录：

| 文档 | 内容 |
|---|---|
| [01 · 架构设计](./docs/01-架构设计.md) | 技术选型、系统架构、目录结构、核心设计决策 |
| [02 · 数据模型](./docs/02-数据模型.md) | 八表结构、索引、级联策略、状态机、迁移管理 |
| [03 · API 参考](./docs/03-API参考.md) | 全部端点、认证、状态流转规则、错误码 |
| [04 · 前端指南](./docs/04-前端指南.md) | 前端架构、页面、组件、设计系统落地 |
| [05 · 部署指南](./docs/05-部署指南.md) | Docker 部署、环境变量、排障 |
| [06 · 开发指南](./docs/06-开发指南.md) | 环境搭建、测试、代码约定、扩展路线 |
| [07 · VS Code 调试](./docs/07-VSCode开发调试.md) | 一键启动、断点调试（前端/后端/全栈） |
| [08 · AI 接入指南](./docs/08-AI接入指南.md) | 让 AI 编码工具通过 MCP / API Key 自动更新进度，SSE 实时同步 |
| [09 · AI 技能包](./skills/hpf-work-manager/) | 对外分发的 MCP 使用技能（SKILL.md + 34 个工具参考 + AI 工作流），供其他机器的 AI 工具接入 |

## 核心功能

- **项目管理**：项目 CRUD、起止日期、归档、里程碑
- **任务管理**：任务 CRUD、状态流转（待办/进行中/已完成）、优先级、进度百分比、预估工时（预留）、批量更新、依赖关系
- **进度追踪**：
  - 项目进度 = 已完成任务数 / 总任务数（实时计算）
  - 甘特图（frappe-gantt，MD3 样式定制，延期任务标红）
  - 燃尽图（ECharts：期望线 + 实际线，基于 completed_at 推导，无快照表）
  - 延期预警（后端派生，前端三处高亮：概览/看板/甘特图）
- **认证**：注册/登录，JWT（7 天有效期，个人/小团队场景）
- **AI 工具接入**：
  - **API Key**：长期有效、可撤销的机器凭证（创建 `/api/keys`，换 JWT `/api/keys/exchange`）
  - **MCP Server**：AI 编码工具零适配接入（`{base}/mcp`，Streamable HTTP），34 个工具覆盖项目/里程碑/任务/依赖/统计/开发记录
  - **SSE 实时推送**：AI 更新后自动广播到前端，多工具/多机器进度实时一致（`/api/events/stream`）

## 目录结构

```
├── docker-compose.yml           # 生产编排
├── docker-compose.override.yml  # 开发编排（热更新）
├── .env.example                 # 环境变量模板
├── DESIGN.md                    # Apple×MD3 设计系统（UI 唯一设计源）
├── docs/                        # 项目文档（架构/数据模型/API/前端/部署/开发）
├── skills/hpf-work-manager/     # AI 接入技能包（SKILL.md + 工具参考，分发到其他机器）
├── scripts/e2e_check.py         # 端到端 API 验证（41 项断言）
├── frontend/                    # Vue 3 前端
└── backend/                     # FastAPI 后端
```

## 快速启动（Docker Compose）

```bash
# 1. 准备环境变量
cp .env.example .env
# 编辑 .env，务必修改 SECRET_KEY（生成方式见文件注释）

# 2. 生产模式：一键启动
docker compose up -d --build
# 访问 http://localhost:8080

# 3. 开发模式：源码挂载 + 热更新
docker compose -f docker-compose.yml -f docker-compose.override.yml up --build
# 前端 http://localhost:8080（vite dev server，代理 /api 到 backend）
# 后端 http://localhost:8000/docs（Swagger 文档）
```

首次启动后端容器会自动执行 `alembic upgrade head` 建表。停止：`docker compose down`（数据保存在 `pgdata` 卷中）。

## 本地开发（不使用 Docker）

```bash
# 后端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # 按需修改 DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 前端（新终端）
cd frontend
npm install
npm run dev            # http://localhost:8080，/api 自动代理到 :8000
```

## API 一览

| 模块 | 端点 |
|---|---|
| 认证 | `POST /api/auth/register` · `POST /api/auth/login` · `GET /api/auth/me` |
| API Key | `GET/POST /api/keys` · `DELETE /api/keys/{id}` · `POST /api/keys/exchange` |
| 项目 | `GET/POST /api/projects` · `GET/PUT/DELETE /api/projects/{id}` |
| 里程碑 | `GET/POST /api/projects/{pid}/milestones` · `PUT/DELETE /api/milestones/{id}` |
| 任务 | `GET/POST /api/projects/{pid}/tasks` · `GET/PUT/DELETE /api/tasks/{id}` · `POST /api/tasks/bulk` · `GET/POST/DELETE /api/tasks/{id}/dependencies` |
| 统计 | `GET /api/projects/{pid}/stats` · `.../burndown` · `.../gantt` |
| 实时推送 | `GET /api/events/stream?project_id={pid}`（SSE） |
| MCP | `{base}/mcp`（Streamable HTTP，AI 工具接入） |

完整交互式文档：启动后访问 `http://localhost:8000/docs`。

## 设计系统

UI 视觉规范由根目录 `DESIGN.md`（Apple × Material Design 3）约束，前端通过 `src/design/tokens.css` 落地为 `--md-*` CSS 变量，组件一律引用变量、禁止内联 hex。要点：

- **主色**：Apple Action Blue `#0066cc`（唯一行动色，深色主题 `#4ea0ff`）；**形状**：MD3 圆角阶梯（控件 `sm`/pill，卡片 `lg`，弹窗 `xl`）
- **字体**：系统字体栈（SF Pro Text / PingFang SC / Inter），400 正文 / 500 标签 / 600 标题
- **无卡片阴影**：深度来自 surface-container 色阶 + hairline 分隔线，仅悬浮 chrome 用阴影
- 状态色映射：done→success 绿 / 进行中→primary 蓝 / 待办→on-surface-variant 灰 / **延期→error 红**

## 说明与范围外

- 本仓库 `DESIGN.md` 仅为设计风格参考，不含任何第三方商标图形资产
- 当前范围不含：RBAC 权限、评论/附件/通知、工时加权进度（仅预留字段）、进度历史快照、K8s 部署
- AI 写操作当前为**完整 CRUD** 权限（无细粒度分级），请仅向可信工具发放 API Key
