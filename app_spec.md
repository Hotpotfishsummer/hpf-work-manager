# app_spec — MD3 设计语言贯彻（hpf-work-manager 前端）

## 1. 目标
`DESIGN.md`（Apple × MD3）是 UI 唯一设计源。现状：8 个新模块约 265 处硬编码色值（Ant 调色板）、
零深色覆盖 → 深色主题破相、出现第二主色与紫色状态色。目标：组件层**零硬编码颜色/阴影/圆角/字号/字重**，
全部走 `--md-*` 令牌，并有机器闸门防止回归。

## 2. 产物
- `frontend/src/design/tokens.css`：补齐缺失的语义令牌（深浅双值），`DESIGN.md` 同步
- `frontend/tests/design-tokens.spec.ts`：规范闸门（vitest，`npm test` 自动跑）
- 8 个违规文件完成令牌化；`docs/` 设计说明同步

## 3. 终止条件（Done = ）
- **End state**：分支 `feat/md3-design-consistency` 上，闸门测试全绿；DESIGN.md 与 tokens.css 一一对应。
- **Proof**：
  - `cd frontend && npx vitest run` → 全部通过（含 design-tokens.spec.ts）
  - `cd frontend && npm run build` → 退出码 0
  - `npx vue-tsc --noEmit -p tsconfig.app.json` → 0 error
  - 双主题截图（Playwright，浅/深各一组主要页面）人工目检无破相
- **Guardrails**：不改后端；不新增 npm 依赖；不动 `main` 分支、不 push、不重建容器/部署
  （合并与部署由用户裁决）；色值只能出现在 `src/design/tokens.css`；不改任何业务逻辑与交互。
- **Stop / Block**：需要改 DESIGN.md 既定角色语义（如新增第二种强调色）→ 停下标 blocked；
  vitest 既有用例回归且非本任务引起 → 记录并汇报。

## 4. 工作区
本目录是 `~/hpf-work-manager` 的 git worktree；`frontend/node_modules` 为指向主检出的软链（不提交）。


## 修订 2（2026-11-25）：从「令牌化」升级为「按 Material Design 3 重构」

用户反馈：上一轮只是把颜色换成令牌，页面仍然是「满屏细边框、全是同一种颜色」，不喜欢。
新的设计方向（用户原话要点）：扁平化；用色块和少数必要的强调线区分控件，不要大量边框；参考 m3.material.io 标准。

- **方法论来源**：`docs/design/m3-reference/`（material-design-3-ui skill 的参考规范，MIT）。
- **硬约束（新增）**：分区不得用细边框（闸门规则「分区细边框」）；层级用「表面色阶 > 间距 > 分隔线 > 卡片」的顺序表达；
  一组操作里只留一个实心按钮；顶层目的地不用页签承载。
- **范围扩大**：允许重构页面架构（导航形态、分区方式、组件选型），仍不改业务逻辑与数据接口。
- F010（间距令牌化）并入各页面的 M3 重排，不再单列。
