/**
 * 设计规范闸门：DESIGN.md（Material Design 3）的机器强制。
 *
 * 规则：组件层（src/design/tokens.css 以外）不得出现
 *  - 颜色字面量（hex / rgb() / rgba() / hsl()）
 *  - 非令牌的阴影、圆角、字号
 *  - >600 的字重（展示用粗体必须走 --md-weight-bold 令牌）
 *  - 分区用的细边框（整圈或左右描边）：层级请用表面色阶 / 间距 / 分隔线表达
 * 确需例外的行（如品牌 SVG 填充）在同行写 `design-audit: allow <原因>`。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const SRC = join(__dirname, '..', 'src')
const TOKEN_FILE = join(SRC, 'design', 'tokens.css')
const ALLOW = /design-audit:\s*allow/

type Rule = { name: string; re: RegExp; cssOnly?: boolean }

const RULES: Rule[] = [
  { name: 'hex 颜色', re: /#[0-9a-fA-F]{3,8}\b/ },
  { name: 'rgb/hsl 颜色', re: /\brgba?\(|\bhsla?\(/ },
  { name: '裸阴影', re: /box-shadow\s*:[^;]*\dpx/, cssOnly: true },
  { name: '裸圆角', re: /border-radius\s*:\s*(?!var\()[^;]*\dpx/, cssOnly: true },
  { name: '裸字号', re: /font-size\s*:\s*(?!var\()[^;]*\dpx/, cssOnly: true },
  { name: '分区细边框', re: /(?:^|[\s;])border(?:-(?:left|right))?\s*:\s*1px\s+(?:solid|dashed)\s+var\(--md-outline(?:-variant)?\)/, cssOnly: true },
  { name: '字重>600', re: /font-weight\s*:\s*(?!var\()(?:[7-9]00|bold|bolder)\b/, cssOnly: true },
]

/** 颜色字面量在 .vue 模板/脚本里也要查；纯 CSS 规则只查 <style> 与 .css。 */
function cssParts(file: string, text: string): { css: string; all: string }[] {
  if (file.endsWith('.css')) return [{ css: text, all: text }]
  if (!file.endsWith('.vue')) return [{ css: '', all: text }]
  const styles = [...text.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) => m[1])
  return styles.map((css) => ({ css, all: text }))
}

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (/\.(vue|css|ts)$/.test(name) && !name.endsWith('.d.ts')) out.push(p)
  }
  return out
}

describe('设计规范闸门（DESIGN.md）', () => {
  const files = walk(SRC).map((p) => relative(SRC, p)).sort()

  it('组件层无颜色字面量 / 裸阴影 / 裸圆角 / 裸字号 / 超标字重', () => {
    const report: string[] = []
    let total = 0
    for (const rel of files) {
      if (join(SRC, rel) === TOKEN_FILE) continue
      const text = readFileSync(join(SRC, rel), 'utf8')
      for (const { css, all } of cssParts(rel, text)) {
        const lines = (rel.endsWith('.vue') || rel.endsWith('.css') ? css : all).split('\n')
        const offset = rel.endsWith('.vue') ? all.slice(0, all.indexOf(css)).split('\n').length - 1 : 0
        lines.forEach((line, i) => {
          if (ALLOW.test(line)) return
          const code = line.replace(/\/\*.*?\*\//g, '').replace(/\/\/.*$/, '')
          for (const rule of RULES) {
            if (rule.cssOnly && !(rel.endsWith('.vue') || rel.endsWith('.css'))) continue
            if (rule.re.test(code)) {
              total++
              report.push(`  ${rel}:${i + offset + 1}  [${rule.name}]  ${line.trim().slice(0, 100)}`)
            }
          }
        })
      }
    }
    if (total) console.log(`\n设计规范违规 ${total} 处：\n${report.join('\n')}\n`)
    expect(total, `设计规范违规 ${total} 处（见上方报告）`).toBe(0)
  })

  it('tokens.css：深色主题补全了浅色主题的全部颜色令牌', () => {
    const css = readFileSync(TOKEN_FILE, 'utf8')
    const light = css.slice(0, css.indexOf("[data-theme='dark']"))
    const dark = css.slice(css.indexOf("[data-theme='dark']"))
    // 「字面色」= 值里直接写了 hex / rgb / hsl；引用了其它令牌的（如 color-mix）会自动随主题切换，不算
    const literalColor = /#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(/
    const colorTokens = (block: string) =>
      new Set(
        [...block.matchAll(/^\s*(--md-[\w-]+)\s*:\s*([^;]+);/gm)]
          .filter((m) => literalColor.test(m[2]))
          .map((m) => m[1]),
      )
    const l = colorTokens(light)
    const d = colorTokens(dark)
    const missing = [...l].filter((n) => !d.has(n))
    expect(missing, '这些颜色令牌缺少深色值').toEqual([])
  })

  it('组件引用的 --md-* 令牌都在 tokens.css 中有定义', () => {
    const defined = new Set([...readFileSync(TOKEN_FILE, 'utf8').matchAll(/(--md-[\w-]+)\s*:/g)].map((m) => m[1]))
    const unknown = new Set<string>()
    for (const rel of files) {
      if (join(SRC, rel) === TOKEN_FILE) continue
      const text = readFileSync(join(SRC, rel), 'utf8')
      for (const m of text.matchAll(/var\(\s*(--md-[\w-]+)/g)) {
        if (!defined.has(m[1])) unknown.add(`${rel} → ${m[1]}`)
      }
    }
    expect([...unknown].sort(), '引用了不存在的令牌').toEqual([])
  })
})
