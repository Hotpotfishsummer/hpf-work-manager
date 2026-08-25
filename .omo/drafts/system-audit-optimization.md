# system-audit-optimization - Draft

## Meta
- slug: system-audit-optimization
- intent: unclear
- review_required: true
- classification: Architecture
- status: approved
- created: 2026-08-25
- approved_at: 2026-08-25
- plan_path: .omo/plans/system-audit-optimization.md
- pending-action: review .omo/plans/system-audit-optimization.md

## Request
> 找一下系统存在的问题等,提出一个优化改进的完整计划

用户要求对 HPF Work Manager 做全系统审计，找出存在问题并提出完整优化改进计划。未指定聚焦方向，需覆盖后端/前端/部署/测试/文档/安全/可观测性/可扩展性。

## Intent Verdict
Intent: **UNCLEAR**, review required — 请求为开放式全量审计，无明确改造终态，需以研究定最佳实践默认值并自动走双重高精度审查。

> 本次按 UNCLEAR 路径处理：不追问用户，采用已验证的最佳实践默认值推进，全部假设在 TL;DR 中明示供门前否决。

## Exploration Summary (已完成三路并行审计)

### 后端 (backend/app) — 33 项
- **HIGH**: SECRET_KEY 默认为 `change-me-in-production` (config.py:12, compose:27)；无限流 (auth/login, register, keys/exchange, /mcp)；MCP 工具绕过 REST 枚举校验导致脏数据；跨项目 milestone_id 未校验
- **MED**: JWT 以 username 为 sub 且不校验用户仍存在；description 无 max_length 导致 500；显式 null 写非空字段 500；cycle 检查 N 次查询；ILIKE 前导通配全表扫描
- **LOW/INFO**: bcrypt 72 字节截断；login 时序侧信道；register 并发 500；Swagger tokenUrl 与 JSON 登录不一致；无分页 (tasks/projects/milestones)；pool 5+5 单 worker；SSE ticket 内存无界；零日志；测试为脚本非 pytest

### 前端 (frontend/src) — 30+ 项
- **BUG**: 401 循环 (http.ts:50-59 + router:76-84，Pinia token 未清)；DevLog 过滤/分页不一致 (DevLogView:308/281-291，首载忽略 entry_type，状态过滤客户端化)
- **PERF**: 任务看板无分页/虚拟化 (api/index:63-73)；SSE 每次全量 3-5 请求+全屏 loading 闪烁；ECharts 全量 1MB、ElementPlus 全量 928KB+382KB；frappe-gantt deep watch 全重绘；nginx 无 gzip
- **SEC**: CSV 公式注入 (TaskBoardView:715-737)；JWT 存 localStorage + 无 CSP/安全头
- **A11Y**: LiveIndicator 无 aria-live；DnD 仅鼠标；Gantt 不可键盘操作
- **其他**: 主题 light ramp 塌陷；批量删除吞错却报成功；进度同步静默失败；字体全量子集；sass-embedded 未使用

### 部署/测试/文档/可观测性 — 30+ 项
- **部署**: 仅 postgres 有 healthcheck；/api/health 不查 DB；单实例+单 worker+进程内事件总线不可水平扩展；override 自动合并导致 dev 配置上生产；无资源限制；镜像/依赖浮动；frontend/.dockerignore 缺 node_modules/dist
- **CI/CD**: 零 CI；测试非 pytest 不可发现；前端零测试；无覆盖率
- **可观测性**: 后端零 logging；无 metrics/tracing；health 不可用作 readiness
- **文档**: docs/03 缺 /overview /search；docs/05:179 healthy 断言失真；docs/06:12 "依赖锁定" 失真；env 模板三处漂移
- **安全/产品**: 开放注册无校验；API Key 全 CRUD 无分级；HMAC 复用 SECRET_KEY；无自动备份（仅 docs 手动 cron）；无版本/Release 流程

## Components Ledger (1-6 独立成败组件)
1. **安全加固** — SECRET_KEY fail-fast、限流、输入校验对齐、CSV 注入、依赖/镜像 pin、安全头/TLS 强制
2. **可靠性与可观测性** — 健康检查 DB 感知、结构化日志/请求日志、错误码归一化、SSE 可靠性
3. **性能与分页** — 任务/项目/里程碑分页 + 虚拟化、ECharts/ElementPlus 按需引入、nginx gzip、Gantt 差分刷新
4. **正确性修复** — 401 循环、DevLog 过滤分页、null/超长 422、跨项目外键校验、时区/批量语义
5. **工程化与 CI/CD** — pytest 化、前端 Vitest、GitHub Actions、pre-commit、版本/CHANGELOG、备份自动化
6. **可用性与可访问性** — a11y (aria-live/键盘 DnD/Gantt)、空/错/加载态、主题 ramp、字体子集化

## Open Assumptions Ledger (采用的最佳实践默认值)

| 假设 | 默认值 | 依据 | 可逆性 |
|---|---|---|---|
| 限流实现 | 后端用 slowapi (内存) + nginx limit_req 兜底，登录/注册/keys/exchange 5/min/IP，MCP 60/min/IP | 零额外中间件，个人/小团队足够，可后换 Redis | 可逆 |
| SECRET_KEY 策略 | 非 dev 环境下默认值直接拒绝启动 (fail-fast)，并在 docs/.env.example 标注必改 | 最高安全优先级，防误部署 | 可逆 (改回 warn) |
| 分页默认值 | tasks/projects/milestones 默认 limit 50 max 100，tasks 支持 cursor/offset 二选一由后端定 | 前端已有 PAGE_SIZE 20 惯例，50 平衡首屏与请求数 | 可逆 |
| ECharts/ElementPlus | ECharts 切 echarts/core 按需，ElementPlus 切 unplugin-vue-components 按需 | 官方推荐，体积 -70% | 可逆 |
| 日志方案 | backend 用 structlog/标准 logging + 中间件请求日志，JSON 输出，uvicorn --access-log 关闭改中间件 | 零侵入，可对接任意收集器 | 可逆 |
| CI 平台 | GitHub Actions (test + alembic --sql + build) | 仓库已在 GitHub 语义下，无需自建 | 可逆 (可换 GitLab) |
| 备份 | 新增 pg_dump sidecar cron 容器，每日 02:00 保留 7 天，恢复文档化 | 单机 Compose 最简可靠方案 | 可逆 |
| 版本 | git tag + image 标签 + CHANGELOG.md，compose 加 image: 字段 | 可回滚，符合现有无发布现状 | 可逆 |
| 可访问性优先级 | 先修 LiveIndicator aria-live + 键盘可操作替代 DnD，再补 Gantt 键盘 | 影响面递减 | 可逆 |

> 最高杠杆假设自检：限流选内存而非 Redis — 是否过度设计？结论：内存足够单实例，避免引入 Redis 复杂度；多实例时再切 Redis，与事件总线扩展同节奏，属合理分层。

## Scope
- **IN**: 上述 6 组件对应的全部问题修复与优化；含迁移、测试、文档、回滚
- **OUT**: RBAC 细粒度角色、团队共享、K8s 部署、MCP 权限分级、工时加权进度 — 均属新增能力，非本次“问题修复/优化”范畴，需另起计划

## Approach (拟规划的执行形态)
分 5 波，每波 5-8 todos，依赖矩阵串行/并行交错；全程 TDD/测试后置明确标注；每 todo 含 References/Acceptance/QA/Commit；收口为 F1-F4 四重最终验证波；双重高精度审查 (momus + oracle) 自动执行。

## Approval Gate
- status: awaiting-approval
- next: 用户显式认可后，执行 scaffold 生成 `.omo/plans/system-audit-optimization.md` 并 APPEND 完整 Todos，随后自动进入双重审查
- 提示：若你有更具体的优化倾向（如“先只做安全”或“不限流”），直接说，我会切到 CLEAR 路径单问分叉

## Review Request State
```json
{
  "transition": "replace",
  "phase": "review_requested",
  "applies_when": ["intent=unclear_and_nontrivial"],
  "atomic": true,
  "review_required": true,
  "plan_path": ".omo/plans/system-audit-optimization.md",
  "plan_sha256": null,
  "review_round_id": null,
  "pending_action_policy": { "review_required": "write and review .omo/plans/system-audit-optimization.md", "otherwise": "write .omo/plans/system-audit-optimization.md" },
  "pending-action": "write and review .omo/plans/system-audit-optimization.md",
  "review": {
    "momus": { "status": "pending", "workspace_root": null, "runtime_home": null, "target": ".omo/plans/system-audit-optimization.md", "round_id": null, "plan_sha256": null, "launch_id": null, "session": null, "result": null },
    "independent": { "status": "pending", "workspace_root": null, "runtime_home": null, "target": ".omo/plans/system-audit-optimization.md", "round_id": null, "plan_sha256": null, "launch_id": null, "session": null, "result": null }
  }
}
```
