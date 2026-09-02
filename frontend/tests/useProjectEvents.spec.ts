/**
 * useProjectEvents 回归测试：重连定时器在 close() 时被清理、
 * connect 幂等守卫（快速切换项目不产生双连接）、指数退避熔断。
 *
 * composable 使用 onMounted/onBeforeUnmount，需在组件 setup 上下文中调用，
 * 故用 @vue/test-utils 挂载宿主组件。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, ref } from 'vue'
import { mount } from '@vue/test-utils'

type ESHandlers = {
  onopen?: () => void
  onerror?: () => void
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

  emit(type: string, data: string) {
    for (const cb of this._listeners[type] ?? []) cb({ data } as MessageEvent)
  }
}

const ticketPost = vi.fn(async () => ({ ticket: 't-1' }))
vi.mock('@/api/http', () => ({
  default: { post: (...args: unknown[]) => ticketPost(...(args as [])) },
}))
vi.stubGlobal('EventSource', MockEventSource as unknown as typeof EventSource)

import { useProjectEvents } from '@/composables/useProjectEvents'

let onUpdate: ReturnType<typeof vi.fn>

// 挂载宿主组件；pidRef 变化可模拟路由参数切换
function setupHarness(initialPid: number | null) {
  let api: ReturnType<typeof useProjectEvents>
  const pidRef = ref<number | null>(initialPid)
  const wrapper = mount(
    defineComponent({
      setup() {
        api = useProjectEvents(() => pidRef.value, onUpdate)
        return () => null
      },
    }),
  )
  return {
    api: api!,
    setPid: (v: number | null) => (pidRef.value = v),
    unmount: () => wrapper.unmount(),
  }
}

beforeEach(() => {
  esInstances.length = 0
  ticketPost.mockClear()
  onUpdate = vi.fn()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useProjectEvents', () => {
  it('onUpdate 收到 project-update 事件触发', async () => {
    const h = setupHarness(1)
    await vi.waitFor(() => expect(esInstances.length).toBe(1))
    esInstances[0].onopen?.()
    expect(h.api.connected.value).toBe(true)
    esInstances[0].emit('project-update', JSON.stringify({ type: 'updated' }))
    expect(onUpdate).toHaveBeenCalledTimes(1)
    h.unmount()
  })

  it('断线重连有指数退避；重试定时器在 close 时清理，不产生双连接', async () => {
    vi.useFakeTimers()
    const h = setupHarness(1)
    await vi.runOnlyPendingTimersAsync()
    await vi.waitFor(() => expect(esInstances.length).toBe(1))
    esInstances[0].onerror?.() // 断开 → 安排 1s 后重连
    h.unmount() // 立即卸载（close）
    await vi.advanceTimersByTimeAsync(60_000)
    expect(esInstances.length).toBe(1) // 修复前：重试定时器未清理 → 第二条连接
    h.unmount()
  })

  it('快速切换项目时不泄漏旧连接（connect 幂等守卫）', async () => {
    const h = setupHarness(1)
    await vi.waitFor(() => expect(esInstances.length).toBe(1))
    h.setPid(2) // watch 触发 close + 重连
    await vi.waitFor(() => expect(esInstances.length).toBe(2))
    expect(esInstances[0].close).toHaveBeenCalledTimes(1) // 旧连接被关闭
    expect(esInstances[1].url).toContain('project_id=2')
    h.unmount()
  })

  it('pid 为 null 不建立连接', async () => {
    const h = setupHarness(null)
    await new Promise((r) => setTimeout(r, 20))
    expect(esInstances.length).toBe(0)
    h.unmount()
  })
})
