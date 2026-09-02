/**
 * notifications store 测试：去重、50 条截断、已读水位推进、
 * generation 竞态（disconnect 后在途 import 不建连）、重连退避熔断与手动重连。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// ---- EventSource mock ----
type ESHandlers = {
  onopen?: () => void
  onerror?: () => void
  listeners: Record<string, ((ev: MessageEvent) => void)[]>
}

const esInstances: (ESHandlers & { close: ReturnType<typeof vi.fn>; url: string })[] = []

class MockEventSource {
  url: string
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  private _listeners: Record<string, ((ev: MessageEvent) => void)[]> = {}
  close = vi.fn(() => {})

  constructor(url: string) {
    this.url = url
    esInstances.push(this as unknown as (typeof esInstances)[number])
  }

  addEventListener(type: string, cb: (ev: MessageEvent) => void) {
    ;(this._listeners[type] ??= []).push(cb)
  }

  get listeners(): Record<string, ((ev: MessageEvent) => void)[]> {
    return this._listeners
  }

  emit(type: string, data: string) {
    for (const cb of this._listeners[type] ?? []) cb({ data } as MessageEvent)
  }
}

// ---- localStorage / 动态 import mock ----
const store: Record<string, string> = {}
const localStorageMock = {
  getItem: vi.fn((k: string) => store[k] ?? null),
  setItem: vi.fn((k: string, v: string) => {
    store[k] = v
  }),
  removeItem: vi.fn((k: string) => delete store[k]),
  clear: vi.fn(),
}
vi.stubGlobal('localStorage', localStorageMock)

const ticketPost = vi.fn(async () => ({ ticket: 't-1' }))
vi.mock('@/api/http', () => ({ default: { post: (...args: unknown[]) => ticketPost(...(args as [])) } }))
vi.stubGlobal('EventSource', MockEventSource as unknown as typeof EventSource)

import { useNotifications } from '@/stores/notifications'

const EVENT = 'project-update'

function lastEs() {
  return esInstances[esInstances.length - 1]
}

beforeEach(() => {
  vi.resetModules()
  esInstances.length = 0
  ticketPost.mockClear()
  for (const k of Object.keys(store)) delete store[k]
})

afterEach(() => {
  vi.useRealTimers()
})

async function setup() {
  // resetModules 后需重新导入以获得全新单例状态
  const mod = await import('@/stores/notifications')
  const api = mod.useNotifications()
  return { mod, api }
}

describe('notifications store', () => {
  it('接收事件并按 id 去重', async () => {
    const { api } = await setup()
    api.connect()
    await vi.waitFor(() => expect(esInstances.length).toBe(1))
    const es = lastEs()
    es.onopen?.()
    es.emit(EVENT, JSON.stringify({ type: 'created', entity: 'task', entity_id: 1, project_id: 1, ts: '2026-09-03T00:00:00Z' }))
    es.emit(EVENT, JSON.stringify({ type: 'created', entity: 'task', entity_id: 1, project_id: 1, ts: '2026-09-03T00:00:00Z' }))
    expect(api.list.value).toHaveLength(1)
    expect(api.unread.value).toBe(1)
  })

  it('列表截断到最近 50 条', async () => {
    const { api } = await setup()
    api.connect()
    await vi.waitFor(() => expect(esInstances.length).toBe(1))
    const es = lastEs()
    es.onopen?.()
    for (let i = 0; i < 60; i++) {
      es.emit(
        EVENT,
        JSON.stringify({ type: 'created', entity: 'task', entity_id: i, project_id: 1, ts: `2026-09-03T00:00:${String(i % 60).padStart(2, '0')}Z` }),
      )
    }
    expect(api.list.value).toHaveLength(50)
  })

  it('markAllRead 推进水位并持久化（服务器时间戳口径）', async () => {
    const { api } = await setup()
    api.connect()
    await vi.waitFor(() => expect(esInstances.length).toBe(1))
    const es = lastEs()
    es.onopen?.()
    es.emit(EVENT, JSON.stringify({ type: 'updated', entity: 'task', entity_id: 2, project_id: 1, ts: '2026-09-03T00:05:00Z' }))
    api.markAllRead()
    expect(api.unread.value).toBe(0)
    expect(localStorageMock.setItem).toHaveBeenCalledWith('hpf_notify_read_ts', expect.any(String))
    // 同一时间戳的事件重放不产生新未读
    es.emit(EVENT, JSON.stringify({ type: 'updated', entity: 'task', entity_id: 2, project_id: 1, ts: '2026-09-03T00:05:00Z' }))
    expect(api.unread.value).toBe(0)
  })

  it('disconnect 后在途异步流程不建连（generation 竞态）', async () => {
    const { api } = await setup()
    // 让 ticket 请求挂起，直到我们手动放行
    let release!: () => void
    const gate = new Promise<void>((r) => (release = r))
    ticketPost.mockImplementationOnce(async () => {
      await gate
      return { ticket: 't-slow' }
    })
    api.connect()
    api.disconnect() // import/ticket 未完成时登出
    release()
    await new Promise((r) => setTimeout(r, 0))
    // generation 已换代：ticket 请求被拦截、EventSource 从未创建
    expect(ticketPost).not.toHaveBeenCalled()
    expect(esInstances.length).toBe(0)
  })

  it('断线按指数退避重连，超过 8 次熔断为 reconnectable', async () => {
    vi.useFakeTimers()
    const { api } = await setup()
    api.connect()
    // 初次连接 + 最多 8 次退避重试 = 共 9 次 ticket 尝试
    for (let i = 0; i < 9; i++) {
      await vi.runOnlyPendingTimersAsync()
      await vi.waitFor(() => expect(ticketPost.mock.calls.length).toBe(i + 1))
      expect(api.reconnectable.value).toBe(false)
      lastEs().onerror?.()
      await vi.advanceTimersByTimeAsync(31_000)
    }
    expect(api.reconnectable.value).toBe(true) // 第 9 次 onerror 后熔断
    expect(ticketPost.mock.calls.length).toBe(9)
    // 手动重连恢复（重置计数）
    api.reconnect()
    await vi.waitFor(() => expect(ticketPost.mock.calls.length).toBe(10))
    expect(api.reconnectable.value).toBe(false)
  })

  it('disconnect 清空列表与未读并断开连接', async () => {
    const { api } = await setup()
    api.connect()
    await vi.waitFor(() => expect(esInstances.length).toBe(1))
    const es = lastEs()
    es.onopen?.()
    es.emit(EVENT, JSON.stringify({ type: 'created', entity: 'task', entity_id: 9, project_id: 1, ts: '2026-09-03T00:00:00Z' }))
    expect(api.unread.value).toBe(1)
    api.disconnect()
    expect(api.list.value).toHaveLength(0)
    expect(api.unread.value).toBe(0)
    expect(api.connected.value).toBe(false)
    expect(es.close).toHaveBeenCalled()
  })
})
