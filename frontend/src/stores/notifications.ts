/**
 * P4-4 通知中心：全局 SSE 单例连接 + 通知列表状态。
 *
 * - 登录后由 AppLayout 触发 connect()（不带 project_id，后端按所有权过滤全局广播）
 * - 事件只在前端内存中保留最近 50 条；已读水位 lastReadTs 持久化 localStorage
 * - 断线自动重连（指数退避，最多 8 次，之后可手动重连）
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
const unread = ref(0)

let es: EventSource | null = null
let retry = 0
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let started = false

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

function connect() {
  if (started || es) return
  started = true
  open()
}

function open() {
  const BASE = import.meta.env.VITE_API_BASE || '/api'
  // EventSource 无法携带 Authorization：先以 JWT 换 30s 短期 ticket
  import('@/api/http').then(async ({ default: http }) => {
    try {
      const { ticket } = await http.post<{ ticket: string }, { ticket: string }>('/events/ticket')
      es = new EventSource(`${BASE}/events/stream?ticket=${encodeURIComponent(ticket)}`)
      es.addEventListener('project-update', (ev) => handleEvent((ev as MessageEvent).data))
      es.onopen = () => {
        retry = 0
        connected.value = true
      }
      es.onerror = () => {
        connected.value = false
        es?.close()
        es = null
        if (retry >= MAX_RETRIES) return // 停止重试；用户可刷新页面恢复
        const delay = Math.min(1000 * 2 ** retry, 30000)
        retry += 1
        reconnectTimer = setTimeout(open, delay)
      }
    } catch {
      started = false
    }
  })
}

function disconnect() {
  started = false
  if (reconnectTimer) clearTimeout(reconnectTimer)
  es?.close()
  es = null
  connected.value = false
  items.value = []
  unread.value = 0
  lastReadTs.value = loadReadTs()
}

function markAllRead() {
  lastReadTs.value = Date.now()
  persistReadTs()
  recomputeUnread()
}

/** 实体/动作中文标签（通知渲染用） */
export const ENTITY_LABEL: Record<string, string> = {
  task: '任务',
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
  return { list, unread, connected, connect, disconnect, markAllRead }
}
