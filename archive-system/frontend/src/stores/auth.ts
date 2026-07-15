import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const user = ref<any>(null)

  async function login(username: string, password: string) {
    const res = await authApi.login({ username, password })
    token.value = res.data.access_token
    user.value = res.data.user
    localStorage.setItem('access_token', token.value)
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

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('access_token')
  }

  return { token, user, login, fetchUser, logout }
})
