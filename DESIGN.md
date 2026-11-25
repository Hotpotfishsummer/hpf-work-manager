# Material Design 3 — DESIGN.md

本文件是前端 UI 的**唯一设计源**。它描述「界面应该是什么样、为什么」，落地位置：

| 层 | 位置 | 说明 |
|---|---|---|
| 令牌 | `frontend/src/design/tokens.css` | 所有颜色 / 字阶 / 形状 / 高度 / 状态层 / 动效 / 间距 |
| 控件 | `frontend/src/design/element-plus.css`、`global.css` | Element Plus 与 `.md-*` 语义类 |
| 规范闸门 | `frontend/tests/design-tokens.spec.ts` | `npm test` 自动跑，违规即失败 |
| 方法论参考 | `docs/design/m3-reference/` | [material-design-3-ui](https://github.com/skydashnet/material-design-3-ui-skill)（MIT）的参考规范 |
| 页面改造规范 | `docs/design/M3-页面改造规范.md` | 改页面时的操作手册 |

更高优先级的外部依据：<https://m3.material.io/>。

## 0. 一句话

**扁平、克制、靠色块与间距分层级。** 边框只留给少数必要的控件；阴影只给浮在内容之上的东西；
主色要稀缺；颜色一定成对出现（容器色 + 该容器上的文字色）。

## 1. 分层怎么表达（按顺序选）

1. **间距与标题**：把相关内容归为一组，不套框。
2. **表面色阶**：需要「一块整体」时才升一档表面色（填充式卡片）。
3. **分隔线**：`outline-variant`，只在行与行之间。
4. **阴影**：只给弹层、菜单、对话框等浮层。

分区、工具条、卡片**不描边**（闸门规则「分区细边框」会拦）。允许描边的只有：
未选中的筛选芯片、描边按钮、输入框底部状态线、表格行分隔线、甘特网格线、卡片左侧的状态强调条。

## 2. 颜色

角色色由官方算法从种子色生成（`node frontend/scripts/gen-m3-tokens.mjs`），深浅两套自动成对。
要换主色，只改脚本里的 `SEED_MAIN` 后重跑。

### 表面

| 令牌 | 浅色 | 深色 | 用在哪 |
|---|---|---|---|
| `--md-surface` | tone 98 | tone 6 | 页面底、顶栏 |
| `--md-surface-container-low` | 96 | 10 | 大面积容器 |
| `--md-surface-container` | 94 | 12 | 导航栏底、表头、卡内分块 |
| `--md-surface-container-high` | 92 | 17 | 浮层、卡内分块、中性芯片 |
| `--md-surface-container-highest` | 90 | 22 | 填充式卡片、输入框底 |

卡内再分块用 `surface-container-high` / `-container`，不要卡片套卡片。

### 强调族

| 族 | 本色 / 其上文字 | 容器色 / 其上文字 | 用在哪 |
|---|---|---|---|
| primary | `--md-primary` / `--md-on-primary` | `--md-primary-container` / `-on-…` | 当前区域最重要的那一个操作；进行中；选中 |
| secondary | `--md-secondary` | `--md-secondary-container` | 次要操作（tonal）、导航选中指示器、辅助标签 |
| tertiary | `--md-tertiary` | `--md-tertiary-container` | 需要第三种强调时 |
| success | `--md-success` | `--md-success-container` | 完成、健康 |
| warning | `--md-warning` | `--md-warning-container` | 注意、待处理、中优先级 |
| error | `--md-error` | `--md-error-container` | 延期、失败、高优先级、破坏性操作 |
| accent 1–6 | `--md-accent-N` | `--md-accent-N-container` / `-on-container` | 任务分类、数据系列 |

规则：

- **主色稀缺**：同一屏里实心主按钮通常只有一个。
- 状态 / 优先级 / 分类 / 选中，用「容器色 + 容器上的文字色」；实心（本色）只给需要立刻注意的少数地方。
- 文字色只用 `on-surface`（正文）、`on-surface-variant`（次要）、`outline`（占位 / 禁用）。
- 不靠颜色单独表达状态：芯片里保留文字或图标。

状态芯片统一用 `global.css` 的 `.md-chip--<tone>`：
`primary` `secondary` `tertiary` `success` `warning` `error` `neutral` `accent-1..6`，实心为 `solid-primary` / `solid-error`。

任务分类固定映射：新功能→1，排错修复→2，重构→3，测试→4，文档→5，运维部署→6，未分类→`neutral`。

### 状态层

悬停 8% / 焦点 10% / 按下 10%（主色 12%）/ 拖拽 16%，颜色取组件自身的「其上文字色」。
全局类 `.md-state` 已封装；自己写时用 `color-mix(in srgb, <on 色> 8%, transparent)`。

## 3. 字阶（M3 type scale）

| 用途 | 令牌 |
|---|---|
| 页面标题 | `--md-type-headline-sm`（24 / 32，400） |
| 顶栏标题 | `--md-type-title-lg`（22 / 28，400） |
| 分区标题、卡片标题 | `--md-type-title-md`（16 / 24，500） |
| 小标题 | `--md-type-title-sm`（14 / 20，500） |
| 正文 | `--md-type-body-md`（14 / 20） |
| 次要说明 | `--md-type-body-sm`（12 / 16） |
| 按钮、芯片 | `--md-type-label-lg`（14 / 20，500） |
| 紧凑芯片 | `--md-type-label-md`（12 / 16，500） |
| 展示数字 | `--md-type-display-sm` 及以上 |

标题字重 ≤500；600 只用于紧凑表格头，700 只用于展示数字。

## 4. 形状、间距、高度

- 形状：extra-small 4 / small 8 / medium 12 / large 16 / extra-large 28 / full。
  卡片 12、芯片 8、按钮 full、输入框 4、对话框 28。**不要把所有东西都做成药丸形**。
- 间距 4px 基准：`--md-space-1..8`（4/8/12/16/24/32/48/64）。分区间 24，卡片内 16。
- 高度：`--md-elevation-0..5`。卡片无阴影；浮层用 2；对话框用 3。
- 点击区 ≥40×40（图标按钮 `.md-icon-btn`）。

## 5. 控件选型

| 场景 | 用什么 |
|---|---|
| 区域主操作 | 实心按钮（`el-button type="primary"`） |
| 次要操作 | tonal（`el-button plain` → secondary-container） |
| 低强调 / 行内 | 文字按钮（`el-button text` / `.md-btn--text`） |
| 筛选 | `.md-chip--filter`，选中 `.is-selected` |
| 只读状态 | `.md-chip--<tone>` |
| 顶层导航 | 导航栏（宽屏 ≥840）/ 底部导航栏（窄屏）——不用页签承载不相关的目的地 |
| 同级视图切换 | `el-tabs`（secondary-container 指示器药丸） |
| 输入 | 填充式（无边框，底部状态线） |
| 提示 / 建议 | `.md-callout--<tone>` |

## 6. 动效

短 100–200ms、中 250–400ms，标准缓动 `cubic-bezier(0.2, 0, 0, 1)`；尊重 `prefers-reduced-motion`。
动效只用来解释状态变化，不做装饰。

## 7. 反模式（闸门与评审都会拦）

- 给分区 / 工具条 / 卡片描边；卡片套卡片；到处加阴影。
- 一屏多个实心主按钮；主色用在大面积正文或无关容器上。
- 用颜色而不配文字表达状态；出现第二套蓝、紫色状态色。
- 顶层目的地放在页签里；芯片当按钮或主导航用。
- 把所有控件都做成药丸形；只用「大圆角 + 淡彩 + 阴影」冒充 Material。
- 在组件里写死颜色 / 阴影 / 圆角 / 字号；>600 的标题字重。
- 混入 Material 2 的规则（下划线页签、描边输入框、悬浮阴影卡片）。

## 8. 闸门

`cd frontend && npx vitest run tests/design-tokens.spec.ts`。失败时逐行列出：颜色字面量、裸阴影 / 圆角 / 字号、
超标字重、分区细边框、引用了不存在的令牌、字面色缺少深色值。
确需例外，在同一行写 `design-audit: allow <原因>`。
