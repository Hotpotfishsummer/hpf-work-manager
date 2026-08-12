import { watch } from 'vue'
import { useThemeStore } from '@/stores/theme'

/** 读取当前生效的 CSS 变量值（ECharts 等需要真实色值的场景使用）。 */
export function cssVar(name: string, fallback = ''): string {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return raw || fallback
}

export const chartColors = {
  get primary() {
    return cssVar('--md-primary')
  },
  get onSurface() {
    return cssVar('--md-on-surface')
  },
  get onSurfaceVariant() {
    return cssVar('--md-on-surface-variant')
  },
  get outlineVariant() {
    return cssVar('--md-outline-variant')
  },
  get outline() {
    return cssVar('--md-outline')
  },
  get surface() {
    return cssVar('--md-surface')
  },
  get surfaceContainerLow() {
    return cssVar('--md-surface-container-low')
  },
  get success() {
    return cssVar('--md-success')
  },
  get error() {
    return cssVar('--md-error')
  },
}

/** 主题切换时触发回调（ECharts 组件用它重绘）。 */
export function onThemeChange(cb: () => void) {
  const theme = useThemeStore()
  watch(
    () => theme.scheme,
    () => {
      // 等 CSS 变量已切换后再读
      requestAnimationFrame(cb)
    }
  )
}