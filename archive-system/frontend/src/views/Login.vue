<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <div class="brand-icon">
          <svg width="32" height="32" viewBox="0 0 28 28" fill="none"><rect width="28" height="28" rx="8" fill="#10B981"/><path d="M7 9h14M7 14h10M7 19h6" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>
        </div>
        <h1>档案智能查询与开放审核系统</h1>
        <p>中南财经政法大学</p>
      </div>
      <div class="login-form">
        <div class="field-group">
          <label>用户名</label>
          <input v-model="form.username" class="field-input" placeholder="请输入用户名" />
        </div>
        <div class="field-group">
          <label>密码</label>
          <input v-model="form.password" type="password" class="field-input" placeholder="请输入密码" @keyup.enter="handleLogin" />
        </div>
        <button class="login-btn" :disabled="loading" @click="handleLogin">
          {{ loading ? '登录中...' : '登 录' }}
        </button>
      </div>
      <p class="login-hint">开发环境默认: admin / 任意密码</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'Admin@123456' })

async function handleLogin() {
  loading.value = true
  try { await auth.login(form.username, form.password); router.push('/') }
  catch { /* mock 模式忽略错误 */ router.push('/') }
  finally { loading.value = false }
}
</script>

<style scoped>
.login-page {
  display: flex; align-items: center; justify-content: center;
  height: 100vh; background: var(--c-bg);
}
.login-card {
  width: 400px; padding: 40px;
  background: var(--c-surface); border-radius: var(--r-xl);
  border: 1px solid var(--c-border); box-shadow: var(--s-card);
}
.login-brand { text-align: center; margin-bottom: 32px; }
.login-brand h1 { font-size: var(--fs-xl); font-weight: var(--fw-bold); color: var(--c-text); margin: 16px 0 4px; }
.login-brand p { font-size: var(--fs-sm); color: var(--c-text-muted); margin: 0; }
.login-form { display: flex; flex-direction: column; gap: 16px; }
.field-group { display: flex; flex-direction: column; gap: 6px; }
.field-group label { font-size: var(--fs-sm); font-weight: var(--fw-medium); color: var(--c-text-secondary); }
.field-input {
  height: 44px; padding: 0 14px; border: 1px solid var(--c-border);
  border-radius: var(--r-sm); font-size: var(--fs-base); color: var(--c-text);
  background: var(--c-bg); outline: none; font-family: var(--font);
}
.field-input:focus { border-color: var(--c-accent); box-shadow: 0 0 0 2px var(--c-accent-light); }
.login-btn {
  height: 44px; border-radius: var(--r-sm); border: none;
  background: var(--c-accent); color: #fff; font-size: var(--fs-base);
  font-weight: var(--fw-semibold); cursor: pointer; margin-top: 8px;
}
.login-btn:hover:not(:disabled) { background: var(--c-accent-hover); }
.login-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.login-hint { text-align: center; margin-top: 24px; font-size: var(--fs-xs); color: var(--c-text-muted); }
</style>
