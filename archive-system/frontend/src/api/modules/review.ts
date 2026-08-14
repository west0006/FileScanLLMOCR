import { api } from './_base'

export const reviewApi = {
  preview: (data: any) => api.post('/review/preview', data),
  createTask: (data: any) => api.post('/review/tasks', data),
  listTasks: (params: any) => api.get('/review/tasks', { params }),
  getTask: (id: number) => api.get(`/review/tasks/${id}`),
  updateTask: (id: number, action: string) => api.put(`/review/tasks/${id}`, null, { params: { action } }),
  listRecords: (params: any) => api.get('/review/records', { params }),
  getRecord: (id: number) => api.get(`/review/records/${id}`),
  export: (data: any) => api.post('/review/export', data, { responseType: 'blob' }),
  exportArchive: (archiveIds: string[]) => api.post('/review/export-archive', { archive_ids: archiveIds }, { responseType: 'blob' }),
}
