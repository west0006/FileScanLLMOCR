/**
 * API 基类 — axios 实例 + 拦截器
 */
import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 30000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
    return config
  }
  // 无 token 时：只允许 auth/debug 端点通过，其余静默取消
  const path = config.url || ''
  if (path.includes('/auth/') || path.includes('/ocr/debug')) {
    return config
  }
  return Promise.reject({ __skip: true })
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error?.__skip) return Promise.reject(error)  // 静默取消
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export { api }
