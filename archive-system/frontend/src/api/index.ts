import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截器 — 附加 JWT Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 — 统一错误处理
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api

// ===================== 各模块 API =====================

// 认证
export const authApi = {
  login: (data: { username: string; password: string }) => api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
}

// 检索
export const searchApi = {
  keyword: (data: any) => api.post('/search/keyword', data),
  semantic: (data: any) => api.post('/search/semantic', data),
  advanced: (data: any) => api.post('/search/advanced', data),
  history: (params: any) => api.get('/search/history', { params }),
  detail: (id: string) => api.get(`/search/archives/${id}`),
  ocrText: (id: string) => api.get(`/search/archives/${id}/ocr`),
  export: (data: any) => api.post('/search/export', data),
}

// OCR
export const ocrApi = {
  createTask: (data: any) => api.post('/ocr/tasks', data),
  listTasks: (params: any) => api.get('/ocr/tasks', { params }),
  getTask: (id: number) => api.get(`/ocr/tasks/${id}`),
  updateTask: (id: number, action: string) => api.put(`/ocr/tasks/${id}`, null, { params: { action } }),
  getResult: (archiveId: string) => api.get(`/ocr/results/${archiveId}`),
  qualityReport: (params: any) => api.get('/ocr/quality-report', { params }),
}

// AI 预审
export const reviewApi = {
  preview: (data: any) => api.post('/review/preview', data),
  createTask: (data: any) => api.post('/review/tasks', data),
  listTasks: (params: any) => api.get('/review/tasks', { params }),
  getTask: (id: number) => api.get(`/review/tasks/${id}`),
  updateTask: (id: number, action: string) => api.put(`/review/tasks/${id}`, null, { params: { action } }),
  listRecords: (params: any) => api.get('/review/records', { params }),
  getRecord: (id: number) => api.get(`/review/records/${id}`),
  export: (data: any) => api.post('/review/export', data),
}

// 用户管理
export const userApi = {
  list: (params: any) => api.get('/user/', { params }),
  create: (data: any) => api.post('/user/', data),
  get: (id: number) => api.get(`/user/${id}`),
  update: (id: number, data: any) => api.put(`/user/${id}`, data),
  resetPassword: (id: number, pass: string) => api.put(`/user/${id}/password`, null, { params: { new_password: pass } }),
  toggleStatus: (id: number, active: boolean) => api.put(`/user/${id}/status`, null, { params: { is_active: active } }),
  listOnline: () => api.get('/user/online'),
  listRoles: () => api.get('/user/roles'),
  updatePermissions: (roleId: number, perms: any) => api.put(`/user/roles/${roleId}/permissions`, perms),
}

// 数据同步
export const syncApi = {
  getConfigs: () => api.get('/sync/config'),
  setFileConfig: (data: any) => api.post('/sync/config/file', data),
  setDbConfig: (data: any) => api.post('/sync/config/database', data),
  triggerFile: (mode: string) => api.post('/sync/trigger/file', null, { params: { mode } }),
  triggerDb: (mode: string) => api.post('/sync/trigger/database', null, { params: { mode } }),
  getProgress: (id: number) => api.get(`/sync/progress/${id}`),
  history: (params: any) => api.get('/sync/history', { params }),
}

// 操作日志
export const logApi = {
  list: (params: any) => api.get('/log/', { params }),
  export: (data: any) => api.post('/log/export', data),
}

// 统计
export const statsApi = {
  byUser: (params: any) => api.get('/stats/by-user', { params }),
  byTime: (params: any) => api.get('/stats/by-time', { params }),
  byType: (params: any) => api.get('/stats/by-type', { params }),
}
