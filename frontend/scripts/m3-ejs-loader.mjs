// 该库的 ESM 导入不带 .js 后缀，Node 默认不解析；这里补上（仅生成脚本使用，不进构建产物）。
import { existsSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
export const resolve = async (spec, ctx, next) => {
  if (spec.startsWith('.') || spec.startsWith('/')) {
    const base = ctx.parentURL ? new URL(spec, ctx.parentURL) : pathToFileURL(spec)
    for (const cand of [base.href, base.href + '.js', base.href.replace(/\/?$/, '/index.js')]) {
      if (existsSync(fileURLToPath(cand))) return { url: cand, shortCircuit: true }
    }
  }
  return next(spec, ctx)
}
