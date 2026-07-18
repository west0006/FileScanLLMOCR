import { api } from './_base'

export const searchApi = {
  keyword: (data: any) => api.post('/search/keyword', data),
  semantic: (data: any) => api.post('/search/semantic', data),
  advanced: (data: any) => api.post('/search/advanced', data),
  history: (params: any) => api.get('/search/history', { params }),
  detail: (id: string) => api.get(`/search/archives/${id}`),
  ocrText: (id: string) => api.get(`/search/archives/${id}/ocr`),
  export: (data: any) => api.post('/search/export', data),
}
