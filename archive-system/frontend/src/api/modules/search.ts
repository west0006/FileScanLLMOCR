import { api } from './_base'

export const searchApi = {
  keyword: (data: any) => api.post('/search/keyword', data),
  semantic: (data: any) => api.post('/search/semantic', data),
  advanced: (data: any) => api.post('/search/advanced', data),
  history: (params: any) => api.get('/search/history', { params }),
  detail: (id: string) => api.get(`/search/archives/${id}`),
  ocrText: (id: string) => api.get(`/search/archives/${id}/ocr`),
  image: (id: string, page?: number) => api.get(`/search/archives/${id}/image`, { params: { page } }),
  download: (id: string, page?: number) => api.get(`/search/archives/${id}/download`, { params: { page }, responseType: 'blob' }),
  related: (id: string) => api.get(`/search/archives/${id}/related`),
  export: (data: any) => api.post('/search/export', data),
  facets: () => api.get('/search/facets'),
}
