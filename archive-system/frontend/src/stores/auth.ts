import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const user = ref<any>(null)
  const permissions = ref<Record<string, any>>({})
  const permissionsLoaded = ref(false)

  function can(module: string, action?: string): boolean {
    const p = permissions.value
    if (!p) return false
    if (p.all === true) return true
    const mp = p[module]
    if (mp === undefined) return false
    // 向后兼容: bool 格式
    if (typeof mp === 'boolean') return mp
    // 新格式: {view: true, download: false}
    if (action && typeof mp === 'object') return !!mp[action]
    // 未指定操作 → 有任一权限
    if (typeof mp === 'object') return Object.values(mp).some(Boolean)
    return false
  }

  async function login(username: string, password: string) {
    const res = await authApi.login({ username, password })
    token.value = res.data.access_token
    user.value = res.data.user
    localStorage.setItem('access_token', token.value)
    await fetchPermissions()
    return res.data
  }

  async function fetchUser() {
    try {
      const res = await authApi.me()
      user.value = res.data
    } catch {
      logout()
    }
  }

  async function fetchPermissions() {
    try {
      const res = await authApi.permissions()
      permissions.value = res.data.permissions || {}
    } catch {
      permissions.value = {}
    } finally {
      permissionsLoaded.value = true
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    permissions.value = {}
    localStorage.removeItem('access_token')
  }

  return { token, user, permissions, permissionsLoaded, can, login, fetchUser, fetchPermissions, logout }
})
