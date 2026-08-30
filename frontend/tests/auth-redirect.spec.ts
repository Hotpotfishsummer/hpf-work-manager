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

    const error = {
      response: {
        status: 401,
        data: { detail: 'Unauthorized' },
      },
    }

    await expect(responseErrorInterceptor!(error)).rejects.toEqual(error)
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('hpf_token')
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('hpf_user')
    expect(window.location.href).toBe('/login')
  })

  it('does not redirect if already on login page', async () => {
    window.location.pathname = '/login'
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
    expect(window.location.href).toBe('http://localhost:8080')
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