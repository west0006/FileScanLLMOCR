import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const user = ref<any>(null)
  const permissions = ref<Record<string, boolean>>({})

  function can(module: string): boolean {
    return permissions.value?.all === true || !!permissions.value?.[module]
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
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    permissions.value = {}
    localStorage.removeItem('access_token')
  }

  return { token, user, permissions, can, login, fetchUser, fetchPermissions, logout }
})
