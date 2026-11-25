/**
 * 跨浏览器与跨安全上下文的剪贴板复制工具。
 * 兼容 HTTP IP 访问环境（在非 HTTPS / 非 localhost 场景下 navigator.clipboard 为 undefined）。
 */
export async function copyText(text: string): Promise<boolean> {
  if (!text) return false

  // 1. 若处于安全上下文环境且支持，优先使用现代 Clipboard API
  if (typeof navigator !== 'undefined' && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch (err) {
      console.warn('navigator.clipboard.writeText 失败，尝试 fallback 方案:', err)
    }
  }

  // 2. 针对非安全上下文（如 http://100.69.225.112:8088）的 textarea + execCommand 降级方案
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'fixed'
    textarea.style.top = '-9999px'
    textarea.style.left = '-9999px'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    textarea.setSelectionRange(0, textarea.value.length)
    const success = document.execCommand('copy')
    document.body.removeChild(textarea)
    return success
  } catch (err) {
    console.error('execCommand copy 失败:', err)
    return false
  }
}
