import { api } from './_base'

export const syncApi = {
  getConfigs: () => api.get('/sync/config'),
  setFileConfig: (data: any) => api.post('/sync/config/file', data),
  setDbConfig: (data: any) => api.post('/sync/config/database', data),
  triggerFile: (mode: string) => api.post('/sync/trigger/file', null, { params: { mode } }),
  triggerDb: (mode: string) => api.post('/sync/trigger/database', null, { params: { mode } }),
  getProgress: (id: number) => api.get(`/sync/progress/${id}`),
  history: (params: any) => api.get('/sync/history', { params }),
}
