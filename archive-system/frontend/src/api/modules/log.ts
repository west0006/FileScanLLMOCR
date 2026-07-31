import { api } from './_base'

export const logApi = {
  list: (params: any) => api.get('/log/', { params }),
  loginLogs: (params: any) => api.get('/log/login', { params }),
  auditSummary: () => api.get('/log/audit/summary'),
  export: (data: any) => api.post('/log/export', data, { responseType: 'blob' }),
}
