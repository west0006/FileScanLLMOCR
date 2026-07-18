import { api } from './_base'

export const statsApi = {
  byUser: (params: any) => api.get('/stats/by-user', { params }),
  byTime: (params: any) => api.get('/stats/by-time', { params }),
  byType: (params: any) => api.get('/stats/by-type', { params }),
}
