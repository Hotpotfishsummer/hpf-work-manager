import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

interface ProjectEvent {
  type: string
  entity: string
  entity_id: number
  project_id: number
  ts: string
}

const MAX_RETRIES = 8

// Global singleton state for SSE connection
let globalEs: EventSource | null = null
let globalRetry = 0
let globalManualClosed = false
const globalConnected = ref(false)
const globalIsReconnectable = ref(false)
let globalProjectId: number | null = null
const subscribers = new Set<() => void>()

function notifySubscribers() {
  subscribers.forEach((cb) => cb())
}

function globalConnect(pid: number) {
  if (globalManualClosed) return
  const BASE = import.meta.env.VITE_API_BASE || '/api'
  try {
    globalEs = new EventSource(`${BASE}/events/stream?project_id=${pid}`)
    globalEs.onopen = () => {
      globalRetry = 0
      globalIsReconnectable.value = false
      globalConnected.value = true
      notifySubscribers()
    }
    globalEs.onmessage = () => {
      notifySubscribers()
    }
    globalEs.onerror = () => {
      globalConnected.value = false
      globalEs?.close()
      if (globalManualClosed) return
      if (globalRetry >= MAX_RETRIES) {
        globalIsReconnectable.value = true
        notifySubscribers()
        return
      }
      const delay = Math.min(1000 * 2 ** globalRetry, 30000)
      globalRetry += 1
      setTimeout(() => globalConnect(globalProjectId!), delay)
    }
  } catch {
    // 环境不支持 EventSource 时静默降级
  }
}

function globalClose() {
  globalManualClosed = true
  globalEs?.close()
  globalEs = null
  globalConnected.value = false
  globalIsReconnectable.value = false
  globalProjectId = null
  notifySubscribers()
}

function globalReconnect() {
  globalRetry = 0
  globalIsReconnectable.value = false
  globalManualClosed = false
  if (globalProjectId != null) {
    globalConnect(globalProjectId)
  }
}

function globalSetProject(pid: number | null) {
  if (pid === globalProjectId) return
  globalClose()
  globalManualClosed = false
  globalProjectId = pid
  if (pid != null) {
    setTimeout(() => globalConnect(pid), 0)
  }
}

/**
 * 全局项目事件订阅：基于路由自动识别 project_id，单例 SSE 连接。
 * 供 AppLayout 的 LiveIndicator 与各视图复用，避免重复连接。
 */
export function useGlobalProjectEvents() {
  const route = useRoute()

  // 从路由提取 project_id
  const projectId = computed(() => {
    const id = route.params.id
    return id ? Number(id) : null
  })

  // 订阅更新回调
  function subscribe(onUpdate: () => void) {
    subscribers.add(onUpdate)
    return () => subscribers.delete(onUpdate)
  }

  // 响应路由变化
  watch(projectId, (pid) => {
    globalSetProject(pid)
  }, { immediate: true })

  onBeforeUnmount(() => {
    // 不在这里关闭全局连接，由路由变化触发
  })

  return {
    connected: globalConnected,
    isReconnectable: globalIsReconnectable,
    reconnect: globalReconnect,
    subscribe,
  }
}