import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import http from '@/api/http'

interface ProjectEvent {
  type: string
  entity: string
  entity_id: number
  project_id: number
  ts: string
}

const MAX_RETRIES = 8

/**
 * 订阅项目变更的 SSE 事件流，收到项目相关变更时触发 onUpdate 回调。
 *
 * EventSource 无法携带 Authorization 头，故先以 JWT 换取短期 ticket
 * （POST /events/ticket），再以 ?ticket= 形式建立连接；后端在 401 时
 * 不会无限重连（达到 MAX_RETRIES 后熔断，由调用方展示断线提示）。
 */
export function useProjectEvents(projectId: () => number | null, onUpdate: () => void) {
  let es: EventSource | null = null
  let retry = 0
  let manualClosed = false
  const connected = ref(false)
  const reconnectable = ref(false)

  const BASE = import.meta.env.VITE_API_BASE || '/api'

  async function connect() {
    const pid = projectId()
    if (pid == null || manualClosed) return

    // 先换取短期 ticket，失败则按退避重连（token 失效时由拦截器转登录，不再死循环）
    let ticket = ''
    try {
      const res = await http.post<{ ticket: string }, { ticket: string }>('/events/ticket')
      ticket = res.ticket
    } catch {
      connected.value = false
      if (!manualClosed && retry < MAX_RETRIES) {
        const delay = Math.min(1000 * 2 ** retry, 30000)
        retry += 1
        setTimeout(connect, delay)
      } else {
        reconnectable.value = true
      }
      return
    }

    try {
      es = new EventSource(
        `${BASE}/events/stream?project_id=${pid}&ticket=${encodeURIComponent(ticket)}`,
      )
      es.onopen = () => {
        retry = 0
        reconnectable.value = false
        connected.value = true
      }
      // 仅命名事件 project-update 会触发刷新（后端按事件名推送，onmessage 收不到）
      es.addEventListener('project-update', (e: MessageEvent) => onUpdate())
      es.onerror = () => {
        connected.value = false
        es?.close()
        es = null
        if (manualClosed) return
        if (retry >= MAX_RETRIES) {
          reconnectable.value = true
          return
        }
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
    reconnectable.value = false
  }

  function reconnect() {
    if (projectId() == null) return
    manualClosed = false
    retry = 0
    reconnectable.value = false
    setTimeout(connect, 0)
  }

  onMounted(connect)
  onBeforeUnmount(close)

  watch(projectId, (pid, old) => {
    if (pid === old) return
    close()
    manualClosed = false
    setTimeout(connect, 0)
  })

  return { connected, reconnectable, reconnect }
}
