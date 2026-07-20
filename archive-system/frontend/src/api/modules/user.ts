import { api } from './_base'

export const userApi = {
  list: (params: any) => api.get('/user/', { params }),
  create: (data: any) => api.post('/user/', data),
  get: (id: number) => api.get(`/user/${id}`),
  update: (id: number, data: any) => api.put(`/user/${id}`, data),
  resetPassword: (id: number, pass: string) => api.put(`/user/${id}/password`, null, { params: { new_password: pass } }),
  toggleStatus: (id: number, active: boolean) => api.put(`/user/${id}/status`, null, { params: { is_active: active } }),
  listOnline: () => api.get('/user/online'),
  listRoles: () => api.get('/user/roles'),
  createRole: (name: string, description: string) => api.post('/user/roles', null, { params: { name, description } }),
  updatePermissions: (roleId: number, perms: any) => api.put(`/user/roles/${roleId}/permissions`, perms),
}
