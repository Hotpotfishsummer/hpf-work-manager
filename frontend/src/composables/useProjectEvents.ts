import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

interface ProjectEvent {
  type: string
  entity: string
  entity_id: number
  project_id: number
  ts: string
}

/**
 * 订阅项目变更的 SSE 事件流，收到项目相关变更时触发 onUpdate 回调。
 * 自动处理断线重连（指数退避），组件卸载时关闭连接。
 */
export function useProjectEvents(projectId: () => number | null, onUpdate: () => void) {
  let es: EventSource | null = null
  let retry = 0
  let manualClosed = false
  const connected = ref(false)

  const BASE = import.meta.env.VITE_API_BASE || '/api'

  function connect() {
    const pid = projectId()
    if (pid == null || manualClosed) return
    try {
      es = new EventSource(`${BASE}/events/stream?project_id=${pid}`)
      es.onopen = () => {
        retry = 0
        connected.value = true
      }
      es.onmessage = (e) => onUpdate()
      es.onerror = () => {
        connected.value = false
        es?.close()
        if (manualClosed) return
        const delay = Math.min(1000 * 2 ** retry, 30000)
        retry += 1
        setTimeout(connect, delay)
      }
    } catch {
      // 环境不支持 EventSource 时静默降级（无实时刷新）
    }
  }

  function close() {
    manualClosed = true
    es?.close()
    es = null
    connected.value = false
  }

  onMounted(connect)
  onBeforeUnmount(close)

  watch(projectId, (pid, old) => {
    if (pid === old) return
    close()
    manualClosed = false
    setTimeout(connect, 0)
  })

  return { connected }
}