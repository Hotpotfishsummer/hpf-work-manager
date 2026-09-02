/**
 * P4-4 通知中心：全局 SSE 单例连接 + 通知列表状态。
 *
 * - 登录后由 AppLayout 触发 connect()（不带 project_id，后端按所有权过滤全局广播）
 * - 事件只在前端内存中保留最近 50 条；已读水位 lastReadTs 持久化 localStorage
 * - 断线自动重连（指数退避，最多 8 次），之后 reconnectable=true，可手动 reconnect()
 * - generation 计数防竞态：disconnect() 后仍在途的动态 import/ticket 请求不会建连
 * - 已读水位取服务器事件时间戳（而非本地 Date.now()），避免客户端时钟偏移误判
 */
import { computed, ref } from 'vue'

export interface NotificationItem {
  id: string // project_id-entity-entity_id-ts 组合去重键
  type: string // created / updated / deleted
  entity: string // task / project / milestone / log / session
  entity_id: number
  project_id: number
  ts: string
}

const MAX_ITEMS = 50
const MAX_RETRIES = 8
const LS_KEY = 'hpf_notify_read_ts'

const items = ref<NotificationItem[]>([])
const connected = ref(false)
const reconnectable = ref(false)
const unread = ref(0)

let es: EventSource | null = null
let retry = 0
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let started = false
let generation = 0 // disconnect/重连时递增，使在途异步流程失效

function loadReadTs(): number {
  const v = Number(localStorage.getItem(LS_KEY) ?? '0')
  return Number.isFinite(v) ? v : 0
}
const lastReadTs = ref(loadReadTs())

function persistReadTs() {
  localStorage.setItem(LS_KEY, String(lastReadTs.value))
}

function recomputeUnread() {
  unread.value = items.value.filter((n) => new Date(n.ts).getTime() > lastReadTs.value).length
}

function handleEvent(raw: string) {
  try {
    const e = JSON.parse(raw) as Omit<NotificationItem, 'id'>
    const id = `${e.project_id}-${e.entity}-${e.entity_id}-${e.ts}`
    if (items.value.some((n) => n.id === id)) return
    items.value = [{ id, ...e }, ...items.value].slice(0, MAX_ITEMS)
    recomputeUnread()
  } catch {
    // 非 JSON 心跳/脏数据忽略
  }
}

/** 登录后从服务端拉取已读水位（localStorage 仅作离线兜底） */
async function syncWatermarkFromServer(myGen: number) {
  try {
    const { default: http } = await import('@/api/http')
    const res = await http.get<{ last_read_at: string | null }, { last_read_at: string | null }>(
      '/notifications/watermark',
    )
    if (myGen !== generation) return
    if (res.last_read_at) {
      const t = new Date(res.last_read_at).getTime()
      if (Number.isFinite(t) && t > lastReadTs.value) {
        lastReadTs.value = t
        persistReadTs()
        recomputeUnread()
      }
    }
  } catch {
    // 拉取失败：沿用 localStorage 兜底
  }
}

/** markAllRead 后把水位推送到服务端（fire-and-forget，失败静默） */
function pushWatermarkToServer() {
  if (!Number.isFinite(lastReadTs.value) || lastReadTs.value <= 0) return
  const iso = new Date(lastReadTs.value).toISOString()
  import('@/api/http')
    .then(({ default: http }) =>
      http
        .put<{ last_read_at: string }, unknown>('/notifications/watermark', {
          last_read_at: iso,
        })
        .catch(() => {}),
    )
    .catch(() => {})
}

function connect() {
  if (started || es) return
  started = true
  open()
}

function scheduleReconnect() {
  if (retry >= MAX_RETRIES) {
    reconnectable.value = true
    return
  }
  const delay = Math.min(1000 * 2 ** retry, 30000)
  retry += 1
  const myGen = generation
  reconnectTimer = setTimeout(() => {
    if (myGen === generation) open()
  }, delay)
}

function open() {
  const myGen = generation
  const BASE = import.meta.env.VITE_API_BASE || '/api'
  // EventSource 无法携带 Authorization：先以 JWT 换 30s 短期 ticket
  import('@/api/http')
    .then(async ({ default: http }) => {
      if (myGen !== generation) return // 已 disconnect/换代：放弃建连
      try {
        const { ticket } = await http.post<{ ticket: string }, { ticket: string }>('/events/ticket')
        if (myGen !== generation) return
        es = new EventSource(`${BASE}/events/stream?ticket=${encodeURIComponent(ticket)}`)
        es.addEventListener('project-update', (ev) => handleEvent((ev as MessageEvent).data))
        es.onopen = () => {
          retry = 0
          reconnectable.value = false
          connected.value = true
          void syncWatermarkFromServer(myGen)
        }
        es.onerror = () => {
          connected.value = false
          es?.close()
          es = null
          scheduleReconnect()
        }
      } catch {
        connected.value = false
        scheduleReconnect()
      }
    })
    .catch(() => {
      // 动态 import 本身失败：按断线处理走退避重连
      if (myGen === generation && started) scheduleReconnect()
    })
}

function disconnect() {
  generation += 1
  started = false
  if (reconnectTimer) clearTimeout(reconnectTimer)
  es?.close()
  es = null
  connected.value = false
  reconnectable.value = false
  items.value = []
  unread.value = 0
  lastReadTs.value = loadReadTs()
}

/** 手动重连（重试熔断后由 UI 触发；重置退避计数） */
function reconnect() {
  if (es) return // 已连接，无需重连
  retry = 0
  reconnectable.value = false
  started = true
  open()
}

function markAllRead() {
  // 用服务器事件时间戳推进水位：客户端 Date.now() 与服务器时钟偏移会误判未读数。
  // 列表为空时保持原水位（没有新事件可读）。
  const times = items.value.map((n) => new Date(n.ts).getTime()).filter((t) => Number.isFinite(t))
  if (times.length) {
    lastReadTs.value = Math.max(lastReadTs.value, ...times)
    persistReadTs()
  }
  recomputeUnread()
  pushWatermarkToServer()
}

/** 实体/动作中文标签（通知渲染用） */
export const ENTITY_LABEL: Record<string, string> = {
  task: '任务',
  comment: '评论',
  project: '项目',
  milestone: '里程碑',
  log: '开发记录',
  session: '会话',
}
export const TYPE_LABEL: Record<string, string> = {
  created: '新建',
  updated: '更新',
  deleted: '删除',
}

export function useNotifications() {
  const list = computed(() => items.value)
  return { list, unread, connected, reconnectable, lastReadTs, connect, disconnect, reconnect, markAllRead }
}
