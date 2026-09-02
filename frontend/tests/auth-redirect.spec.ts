import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'

// Mock axios before importing http
vi.mock('axios', () => {
  const mockInterceptors = {
    request: { use: vi.fn() },
    response: { use: vi.fn() },
  }
  const mockCreate = vi.fn(() => ({
    interceptors: mockInterceptors,
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }))
  return {
    default: {
      create: mockCreate,
      isAxiosError: vi.fn(),
    },
    create: mockCreate,
    isAxiosError: vi.fn(),
  }
})

// Mock element-plus
vi.mock('element-plus', () => ({
  ElMessage: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}))

// Mock router（拦截器 401 时动态 import('@/router') 跳转登录页）
vi.mock('@/router', () => ({
  default: {
    currentRoute: { value: { path: '/projects/1', fullPath: '/projects/1' } },
    push: vi.fn(),
  },
}))

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock window.location
const originalLocation = window.location
beforeEach(() => {
  delete (window as unknown as { location: Location }).location
  window.location = { ...originalLocation, href: 'http://localhost:8080', pathname: '/projects/1' } as Location
})

afterEach(() => {
  window.location = originalLocation
  vi.clearAllMocks()
})

describe('http interceptor 401 handling', () => {
  let http: ReturnType<typeof axios.create>
  let responseInterceptor: (res: unknown) => unknown
  let responseErrorInterceptor: (error: unknown) => Promise<unknown>

  beforeEach(async () => {
    vi.resetModules()
    // 拦截器动态 import('@/stores/auth') 使用 Pinia，测试需先激活
    const { createPinia, setActivePinia } = await import('pinia')
    setActivePinia(createPinia())
    const { default: httpModule } = await import('@/api/http')
    http = httpModule.default

    // Get the interceptors that were registered
    const createMock = vi.mocked(axios.create)
    const instance = createMock.mock.results[0]?.value
    if (instance?.interceptors?.response?.use) {
      const calls = instance.interceptors.response.use.mock.calls
      if (calls.length > 0) {
        responseInterceptor = calls[0][0]
        responseErrorInterceptor = calls[0][1]
      }
    }
  })

  it('registers response interceptor', () => {
    expect(responseErrorInterceptor).toBeDefined()
  })

  it('removes token and redirects on 401', async () => {
    localStorageMock.getItem.mockReturnValue('test-token')
    const { useAuthStore } = await import('@/stores/auth')
    const authStore = useAuthStore()
    authStore.token = 'test-token'

    const error = {
      response: {
        status: 401,
        data: { detail: 'Unauthorized' },
      },
    }

    await expect(responseErrorInterceptor!(error)).rejects.toEqual(error)
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('hpf_token')
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('hpf_user')
    // 拦截器经 vue-router 跳转登录页（携带 redirect query）
    const { push } = (await import('@/router')).default as unknown as { push: ReturnType<typeof vi.fn> }
    expect(push).toHaveBeenCalledWith({ path: '/login', query: { redirect: '/projects/1' } })
  })

  it('does not redirect if already on login page', async () => {
    // 路由 mock 需指向 /login 以验证「已在该页则不重复跳转」分支
    const routerModule = (await import('@/router')) as unknown as {
      default: { currentRoute: { value: { path: string } }; push: ReturnType<typeof vi.fn> }
    }
    routerModule.default.currentRoute.value.path = '/login'
    localStorageMock.getItem.mockReturnValue('test-token')

    const error = {
      response: {
        status: 401,
        data: { detail: 'Unauthorized' },
      },
    }

    await expect(responseErrorInterceptor!(error)).rejects.toEqual(error)
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('hpf_token')
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('hpf_user')
    expect(routerModule.default.push).not.toHaveBeenCalled()
  })

  it('shows error message for non-401 errors', async () => {
    const { ElMessage } = await import('element-plus')
    const error = {
      response: {
        status: 500,
        data: { detail: 'Internal Server Error' },
      },
    }

    await expect(responseErrorInterceptor!(error)).rejects.toEqual(error)
    expect(ElMessage.error).toHaveBeenCalledWith('Internal Server Error')
  })

  it('shows generic error when no detail provided', async () => {
    const { ElMessage } = await import('element-plus')
    const error = {
      response: {
        status: 500,
        data: {},
      },
    }

    await expect(responseErrorInterceptor!(error)).rejects.toEqual(error)
    expect(ElMessage.error).toHaveBeenCalledWith('请求失败，请稍后重试')
  })

  it('attaches Authorization header when token exists', async () => {
    localStorageMock.getItem.mockReturnValue('test-jwt-token')

    const { default: httpModule } = await import('@/api/http')
    const httpInstance = httpModule.default

    // Get the request interceptor
    const createMock = vi.mocked(axios.create)
    const instance = createMock.mock.results[0]?.value
    const requestInterceptor = instance?.interceptors?.request?.use?.mock?.calls?.[0]?.[0]

    if (requestInterceptor) {
      const config = { headers: {} }
      const result = requestInterceptor(config)
      expect(result.headers.Authorization).toBe('Bearer test-jwt-token')
    }
  })

  it('does not attach Authorization header when no token', async () => {
    localStorageMock.getItem.mockReturnValue(null)

    const { default: httpModule } = await import('@/api/http')
    const httpInstance = httpModule.default

    const createMock = vi.mocked(axios.create)
    const instance = createMock.mock.results[0]?.value
    const requestInterceptor = instance?.interceptors?.request?.use?.mock?.calls?.[0]?.[0]

    if (requestInterceptor) {
      const config = { headers: {} }
      const result = requestInterceptor(config)
      expect(result.headers.Authorization).toBeUndefined()
    }
  })
})