# Apple × Material Design 3 — DESIGN.md

> Hybrid system for a data-dense task/progress manager.
> **Structure & density = Material 3; surfaces, type, borders, whitespace rhythm = Apple.**
> Every token has a light AND dark value. Theme is driven by `data-theme="light|dark"` on `<html>`.

## 1. Theme System

- Two schemes: **light** (`:root`, default) and **dark** (`[data-theme='dark']`).
- Selection follows `prefers-color-scheme` by default (`system`); a nav toggle overrides it;
  choice persisted in `localStorage` (`hpf_theme`) and applied pre-paint (no FOUC).
- Playwright/dev checks must verify BOTH schemes; a color change done in one mode only is a bug.
- No third "auto" value in the store — `system` resolves to light/dark at read time.

## 2. Color Roles (MD3)

All colors are roles. Never hardcode a hex in a `.vue` or `.ts` file unless it's genuinely
non-themeable (e.g. a brand SVG glyph) — and even then prefer a token.

| Role | Light | Dark | Use |
|---|---|---|---|
| `--md-primary` | #0066cc | #4ea0ff | Buttons/links/focus/active states, in_progress status |
| `--md-on-primary` | #ffffff | #00305f | Text/icon on primary |
| `--md-primary-container` | #cfe3ff | #004a8f | Tonal buttons, selected chips, inspects |
| `--md-on-primary-container` | #001b3c | #d2e5ff | Text on primary-container |
| `--md-surface` | #f8f9f9 | #141414 | Page canvas |
| `--md-on-surface` | #1a1b1f | #e4e2e6 | Primary text (≈ Apple ink #1d1d1f in light) |
| `--md-surface-container-lowest` | #ffffff | #0e0e0e | Highest surface (dialogs' content) |
| `--md-surface-container-low` | #f1f2f4 | #1c1c1e | Card body on canvas |
| `--md-surface-container` | #eaecf0 | #202022 | Nested grouping inside a card |
| `--md-surface-container-high` | #e4e6ea | #2a2a2d | Dialog body / elevated regions |
| `--md-surface-container-highest` | #dfe1e4 | #353537 | Chips, controls bottom layer |
| `--md-on-surface-variant` | #44474d | #c5c6ca | Secondary text, placeholders, icons |
| `--md-surface-variant` | #e0e2e8 | #434549 | Filled tags, chip fills |
| `--md-outline` | #73777f | #8f9297 | Emphasized outlines (focus ring) |
| `--md-outline-variant` | #c3c6cc | #434549 | Hairlines, card borders |
| `--md-error` | #ba1a1a | #ffb4ab | Overdue / destructive |
| `--md-on-error` | #ffffff | #690005 | Text on error |
| `--md-error-container` | #ffdad6 | #93000a | Error chip/tag fill |
| `--md-on-error-container` | #410002 | #ffdad6 | Text on error-container |
| `--md-success` | #2e7d32 | #a5d6a7 | done status |
| `--md-success-container` | #a9e6a8 | #17631f | Success tag fill |
| `--md-warning` | #8a5a00 | #f5c344 | Priority-high / warning |
| `--md-warning-container` | #ffdfa8 | #543d00 | Warning tag fill |
| `--md-ink` | #1d1d1f | #e4e2e6 | Apple near-black ink (headlines) |
| `--md-parchment` | #f5f5f7 | #1a1a1c | Apple off-white alternate band / footer |
| `--md-on-parchment` | #1d1d1f | #e4e2e6 | Text on parchment |

**Status mapping:** todo → `--md-on-surface-variant` · in_progress → `--md-primary` ·
done → `--md-success` · overdue → `--md-error`.

**Priority mapping:** high → `--md-warning`（唯一占用 warning 的语义）· medium / low → 中性
`--md-on-surface-variant`。error 红仅保留给逾期/破坏性操作，不用于优先级。

**Elevation:** flat chrome = surface-container-low + 1px outline-variant. Floating chrome
(dialogs/dropdowns) = surface-container-high + `--md-shadow-2`. Prefer color-elevation over
shadow; Apple never shadows cards.

## 3. Typography

Font stack: `system-ui, -apple-system, 'SF Pro Text', 'SF Pro Display', 'PingFang SC', 'Helvetica Neue', 'Inter', 'Segoe UI', Roboto, sans-serif`.

Weights: **400 body / 500 labels / 600 titles / 700 品牌与展示点缀**. Body 14px, minimum 12px.

| Token | Size/Weight | Leading | Tracking | Use |
|---|---|---|---|---|
| `--md-text-display` | 28/600 | 1.2 | -0.374px | Page titles |
| `--md-text-title-lg` | 20/600 | 1.3 | -0.36px | Card titles, dialog titles |
| `--md-text-title-md` | 16/600 | 1.4 | -0.31px | In-card subheads |
| `--md-text-title-sm` | 14/600 | 1.43 | -0.224px | List item titles, nav links |
| `--md-text-body-lg` | 16/400 | 1.5 | -0.31px | Description paragraphs |
| `--md-text-body` | 14/400 | 1.5 | -0.224px | Default UI / table / forms |
| `--md-text-body-sm` | 12/400 | 1.5 | -0.12px | Metadata, timestamps |
| `--md-text-label` | 14/500 | 1.2 | -0.224px | Buttons, inputs labels |
| `--md-text-label-sm` | 12/500 | 1.3 | -0.12px | Table header, chips |
| `--md-text-caption` | 11/500 | 1.4 | 0 | Overline/eyebrow |

Negative tracking ≥14px (Apple tight), 0 at/or below 12px.

## 4. Shapes & Spacing

- Radius: `--md-radius-xs` 4 (tags) · `sm` 8 (inputs) · `md` 12 (small cards) · `lg` 16 (cards) · `xl` 28 (dialogs) · `pill` 9999 (buttons, chips, progress).
- Spacing: 4px base → `--md-space-xxs 4` · `xs 8` · `sm 12` · `md 16` · `lg 24` · `xl 32` · `xxl 48` · `section 80`.
- Density: tables/boards/chips = MD3 compact (32–40px rows, 8–12px card padding). Page headers
  & sections = Apple generous (24–48px around headers).

## 5. Components

- **Button primary:** pill, `primary` bg/`on-primary` text, 40px tall, hover = `--md-primary-hover` overlay, focus = 2px primary ring, active = `scale(.98)`.
- **Button tonal** (secondary action): pill, `primary-container`/`on-primary-container`.
- **Button outlined/text:** outline-variant border or transparent; `primary` text.
- **Input:** outlined — transparent bg, 1px `outline-variant` (hover `outline`), focus 2px `primary`, height 40px, radius `sm`.
- **Card:** `surface-container-low` + 1px `outline-variant` + radius `lg` + padding `md`/`lg`. Elevated card = pure `surface` + `shadow-1`.
- **Table:** header `label-sm`/`on-surface-variant` on `surface`; row hover `surface-container-low`; separator 1px `outline-variant`.
- **Chip/Tag/Progress:** chips pill on `surface-container-highest`; tags `xs` on `surface-variant`; linear progress pill on `surface-container-highest` track.
- **Nav:** top-app-bar 56px, `surface` @ 72% + blur(20px) saturate(180%) 1px outline-variant bottom; active link `on-surface` + 2px primary underline, inactive `on-surface-variant`.
- **Dialog:** `surface-container-high`, radius `xl`, `shadow-2`.

## 6. Motion

- Standard: `200ms cubic-bezier(0.2,0,0,1)`. Emphasized: `300ms cubic-bezier(0.05,0.7,0.1,1)`. Press: `scale(.98)`, 100ms.
- Theme switch: instant attribute swap (no transition that delays); chart components re-render.
- Respect `prefers-reduced-motion`.

## 7. Anti-patterns (Do Not)

- No hardcoded hex in components; charts must read computed token values & re-render on theme change.
- No second accent color; no violet/magenta status colors.
- Don't use weight 700 for body/content — reserve it for brand & display accents only (hierarchy tops at 600).
- Don't uppercase body text or use 1.5px letter-spacing links like the BMW "LEARN MORE" style.
- Don't use `radius-none` (0px) rectangles; controls are `sm`/pill, cards `lg`.
- Don't shadow cards/rows — raise via surface-container ladder.
- Don't ship a light-only palette: every surface/status/outline token has a dark variant.
- Don't use pure black (#000) for text or surfaces; use ink/surface tokens.