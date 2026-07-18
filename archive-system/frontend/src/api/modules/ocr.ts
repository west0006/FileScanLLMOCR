import { api } from './_base'

export const ocrApi = {
  createTask: (data: any) => api.post('/ocr/tasks', data),
  listTasks: (params: any) => api.get('/ocr/tasks', { params }),
  getTask: (id: number) => api.get(`/ocr/tasks/${id}`),
  updateTask: (id: number, action: string) => api.put(`/ocr/tasks/${id}`, null, { params: { action } }),
  getResult: (archiveId: string) => api.get(`/ocr/results/${archiveId}`),
  qualityReport: (params: any) => api.get('/ocr/quality-report', { params }),
}
