import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const THEME_KEY = 'hpf_theme'
type ThemeMode = 'system' | 'light' | 'dark'
type ThemeScheme = 'light' | 'dark'

const media = window.matchMedia('(prefers-color-scheme: dark)')

function readMode(): ThemeMode {
  const raw = localStorage.getItem(THEME_KEY)
  return raw === 'light' || raw === 'dark' || raw === 'system' ? raw : 'system'
}

function resolveScheme(mode: ThemeMode): ThemeScheme {
  if (mode === 'system') return media.matches ? 'dark' : 'light'
  return mode
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>(readMode())
  const scheme = ref<ThemeScheme>(resolveScheme(mode.value))

  const isDark = computed(() => scheme.value === 'dark')

  function apply(s: ThemeScheme) {
    scheme.value = s
    document.documentElement.setAttribute('data-theme', s)
  }

  function setMode(m: ThemeMode) {
    mode.value = m
    localStorage.setItem(THEME_KEY, m)
    apply(resolveScheme(m))
  }

  function toggle() {
    setMode(scheme.value === 'dark' ? 'light' : 'dark')
  }

  media.addEventListener('change', () => {
    // system 模式下跟随系统实时切换
    if (mode.value === 'system') apply(media.matches ? 'dark' : 'light')
  })

  return { mode, scheme, isDark, setMode, toggle, apply }
})