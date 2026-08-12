# 07 · VS Code 开发调试

> 仓库已内置 `.vscode/` 配置：`launch.json`（调试）、`tasks.json`（任务）、`settings.json`（项目设置）、`extensions.json`（推荐扩展）。

## 1. 首次准备

1. 安装推荐扩展：打开项目后右下角弹窗点击「Install」；或手动安装 `extensions.json` 中的：
   - **Vue.volar**（Vue 3 语言支持）、**ms-python.python** + **ms-python.debugpy**（Python 调试）
   - ms-python.black-formatter、esbenp.prettier-vscode（格式化）
   - ms-azuretools.vscode-docker（Docker 支持）
2. 创建后端虚拟环境并安装依赖（一次即可）：
   ```bash
   cd backend && python -m venv .venv && .venv/bin/pip install -e .
   ```
   > `settings.json` 已将 Python 解释器指向 `backend/.venv/bin/python`。
3. 前端安装依赖：
   ```bash
   cd frontend && npm install
   ```

## 2. 一键启动（Tasks）

`Cmd+Shift+P` → **Tasks: Run Task**，选择：

| 任务 | 作用 |
|---|---|
| **启动: 完整开发环境** | 依次：启动 PostgreSQL → 执行迁移 → 起 uvicorn(:8000, --reload) → 起 vite(:8080) |
| 启动: 后端开发环境 | 只起 DB + 迁移 + uvicorn |
| 启动: 前端开发环境 | 只起 vite dev server |
| frontend: 构建 (npm run build) | 默认构建任务（`Cmd+Shift+B`） |
| test: e2e 端到端验证 | 运行 33 项断言 |
| test: 全部 | 并行跑 构建 + e2e + 迁移验证 |

> 后台服务器任务（uvicorn/vite）会持续运行在专用终端面板（panel: dedicated），关闭终端即停止。

## 3. 调试（F5）

`launch.json` 提供 4 个调试配置 + 1 个组合：

| 配置 | 说明 |
|---|---|
| **Debug: FastAPI 后端 (:8000)** | Debugpy 启动 uvicorn（**无 --reload**，断点直命中）；`preLaunchTask` 先自动执行数据库迁移 |
| **Debug: 前端 (Chrome + Vite :8080)** | 启动 Vite（preLaunchTask）后打开 Chrome 调试 SPA，支持断点/源码映射 |
| **调试: 全栈 (后端 + 前端)** | `compounds` 组合：后端调试 + 前端调试同时运行 |
| Debug: e2e 端到端测试 | 断点调试 `scripts/e2e_check.py`（SQLite 临时库） |
| Debug: Python 当前文件 | 调试任意打开的 `.py` 文件 |

### 使用示例：调试后端接口

1. 在 `backend/app/routers/tasks.py` 行号左侧点击设置断点（如 `update_task`）
2. 运行配置 **Debug: FastAPI 后端 (:8000)**（F5）
3. 用 curl / Swagger（`http://localhost:8000/docs`）调用接口，命中断点后可在「变量/监视」面板查看状态

### 使用示例：调试前端页面

1. 运行组合 **调试: 全栈**，等 Vite 就绪后 Chrome 自动打开 `http://localhost:8080`
2. 在 `frontend/src/views/TaskBoardView.vue` 设置断点
3. 页面操作触发请求即命中断点；后端断点同样生效（跨前后端联调）

## 4. 环境变量说明

`launch.json` 中后端调试固定使用本地开发值：

| 变量 | 值 |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://hpf:hpf@localhost:5432/hpf_work`（与 docker compose 默认一致） |
| `SECRET_KEY` | 仅本地调试用的开发密钥 |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:8080` |

如需连其他环境，直接在 launch.json 的 `env` 中修改（不提交个人改动请勿改仓库文件，可用「launch.json 用户片段」或本地 `.env` 覆盖）。

## 5. 常见问题

**Q：preLaunchTask 提示找不到 "backend: 数据库迁移"？**
A：确保 `tasks.json` 与 `launch.json` 在同一 `.vscode/` 目录，且任务 label 完全一致（含空格与括号）。

**Q：Chrome 调试报 "Cannot connect to the target"？**
A：Vite 未就绪（background 匹配超时）。手动先跑「启动: 前端开发环境」，再单独运行 Chrome 调试配置（去掉 preLaunchTask 或等 Vite 输出 `Local:` 后重试）。

**Q：后端断点不停？**
A：确认运行的是 **Debug: FastAPI 后端**（非 tasks 的 --reload 版）；`justMyCode` 保持 true 只停业务代码。

**Q：uvicorn --reload 任务报模块找不到？**
A：`cwd` 必须是 `backend/`（任务已设置）；确保 `.venv` 已创建且安装了 `-e .`。

**Q：为什么 tasks 用 `.venv` 而不是系统 Python？**
A：项目依赖全部锁定在 `.venv`，避免污染系统环境；这也是 Docker 构建的同样隔离思路。
