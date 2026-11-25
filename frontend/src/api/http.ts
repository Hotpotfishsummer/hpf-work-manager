import axios, { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 120000,
})

// 请求拦截：附加缺省 JWT 占位
http.interceptors.request.use((config) => {
  config.headers.Authorization = 'Bearer tailnet-mode-token'
  return config
})

// 响应拦截：统一错误提示（免鉴权模式不强制重定向到登录页）
http.interceptors.response.use(
  (res) => res.data,
  async (error: AxiosError<{ detail?: string | Array<{ loc: string[]; msg: string; type: string }> }>) => {
    const detail = error.response?.data?.detail
    let message: string
    if (Array.isArray(detail)) {
      message = detail.map((d) => d.msg).join('；') || '请求参数有误'
    } else if (typeof detail === 'string') {
      message = detail
    } else {
      message = '请求失败，请稍后重试'
    }
    // 忽略部分 404 / 401 弹窗干扰
    if (error.response?.status !== 401) {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

export default http
