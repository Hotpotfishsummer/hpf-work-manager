// 从种子色按 Material Design 3 官方算法生成角色色，写入 src/design/tokens.css 的 <m3-generated-*> 标记之间。
// 用法：node scripts/gen-m3-tokens.mjs   （改种子色后重跑即可；非颜色令牌不受影响）
import { register } from 'node:module'
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

// 该库的 ESM 导入不带 .js 后缀，Node 默认不解析，补一个加载钩子（仅生成脚本使用）
register('./m3-ejs-loader.mjs', import.meta.url)
const M = await import('@material/material-color-utilities')

const hex = (argb) => '#' + (Number(argb) & 0xffffff).toString(16).padStart(6, '0')
const kebab = (s) => s.replace(/[A-Z]/g, (c) => '-' + c.toLowerCase())

const MAIN_ROLES = [
  'primary', 'onPrimary', 'primaryContainer', 'onPrimaryContainer', 'primaryDim',
  'secondary', 'onSecondary', 'secondaryContainer', 'onSecondaryContainer',
  'tertiary', 'onTertiary', 'tertiaryContainer', 'onTertiaryContainer',
  'error', 'onError', 'errorContainer', 'onErrorContainer',
  'surface', 'onSurface', 'surfaceVariant', 'onSurfaceVariant', 'outline', 'outlineVariant',
  'inverseSurface', 'inverseOnSurface', 'inversePrimary',
  'surfaceContainerLowest', 'surfaceContainerLow', 'surfaceContainer', 'surfaceContainerHigh',
  'surfaceContainerHighest', 'surfaceBright', 'surfaceDim',
]
const FAMILY_ROLES = [
  ['primary', (n) => `--md-${n}`],
  ['onPrimary', (n) => `--md-on-${n}`],
  ['primaryContainer', (n) => `--md-${n}-container`],
  ['onPrimaryContainer', (n) => `--md-on-${n}-container`],
]

/** 种子：主色沿用品牌蓝；成功 / 警告各成一族；accent 1–6 给分类标签与数据系列一个合法的彩色出口 */
const SEED_MAIN = '#0066cc'
const SEEDS = { success: '#1b8a3a', warning: '#c26a00' }
const ACCENTS = ['#0b8a8f', '#d9622b', '#7b5bd6', '#c94f8c', '#4c8a1f', '#a8861f']

const scheme = (seed, dark) => new M.SchemeTonalSpot(M.Hct.fromInt(M.argbFromHex(seed)), dark, 0)
const get = (s, name) => {
  const v = s[name]
  return hex(typeof v === 'function' ? v.call(s) : v)
}

const block = (dark) => {
  const L = []
  const main = scheme(SEED_MAIN, dark)
  for (const r of MAIN_ROLES) L.push(`  --md-${kebab(r)}: ${get(main, r)};`)
  for (const [name, seed] of Object.entries(SEEDS)) {
    const s = scheme(seed, dark)
    L.push('')
    L.push(`  /* ${name}：${name === 'success' ? '完成 / 健康' : '注意 / 待处理'}（文字用本色，浅底用 container） */`)
    for (const [r, name_] of FAMILY_ROLES) L.push(`  ${name_(name)}: ${get(s, r)};`)
  }
  L.push('')
  L.push('  /* accent 1–6：分类标签、数据系列的容器色 */')
  ACCENTS.forEach((seed, i) => {
    const s = scheme(seed, dark)
    L.push(`  --md-accent-${i + 1}: ${get(s, 'primary')};`)
    L.push(`  --md-accent-${i + 1}-container: ${get(s, 'primaryContainer')};`)
    L.push(`  --md-accent-${i + 1}-on-container: ${get(s, 'onPrimaryContainer')};`)
  })
  return L.join('\n') + '\n'
}

const file = fileURLToPath(new URL('../src/design/tokens.css', import.meta.url))
const css = readFileSync(file, 'utf8')
const swap = (text, tag, body) =>
  text.replace(new RegExp(`(/\\* <${tag}> \\*/\\n)[\\s\\S]*?(/\\* </${tag}> \\*/)`), `$1${body}$2`)
writeFileSync(file, swap(swap(css, 'm3-generated-light', block(false)), 'm3-generated-dark', block(true)))
console.log('已写入 M3 角色色 →', file)
