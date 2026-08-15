/**
 * API 基类 — axios 实例 + 拦截器
 */
import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 30000 })

// 会话失效统一处理：清除本地 token 并回到登录页
function clearSessionAndRedirect() {
  localStorage.removeItem('access_token')
  window.location.href = '/login'
}

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
    // 登录失败（密码错误也是 401）不触发跳转，避免把登录页用户原地踢回登录页、丢失错误提示
    if (error.response?.status === 401 && !String(error.config?.url || '').includes('/auth/login')) {
      clearSessionAndRedirect()
    }
    // 账户停用：Token 仍有效但请求被拒 → 清除本地会话并回到登录页
    // 仅处理「停用」类 403，权限不足等其他 403 保持原样，避免误伤
    if (error.response?.status === 403 && String(error.response.data?.detail || '').includes('停用')) {
      clearSessionAndRedirect()
    }
    return Promise.reject(error)
  }
)

export { api }
