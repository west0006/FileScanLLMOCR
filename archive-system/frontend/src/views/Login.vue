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
        <div class="field-group">
          <label>验证码</label>
          <div class="captcha-row">
            <input v-model="captchaInput" class="field-input captcha-input" placeholder="请输入验证码" maxlength="4" @keyup.enter="handleLogin" />
            <div class="captcha-box" @click="genCaptcha">{{ captchaText }}</div>
          </div>
        </div>
        <div class="role-row">
          <button v-for="r in roles" :key="r.key" :class="['role-btn', {active:selectedRole===r.key}]" @click="selectedRole=r.key">{{ r.label }}</button>
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
import { ElMessage } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'Admin@123456' })
const captchaInput = ref('')
const captchaText = ref('')
const selectedRole = ref('reviewer')
const roles = [
  { key: 'system_admin', label: '系统管理员' },
  { key: 'archive_admin', label: '预审管理员' },
  { key: 'reviewer', label: '查档人员' },
]

function genCaptcha() {
  const a = Math.floor(Math.random() * 20) + 1
  const b = Math.floor(Math.random() * 20) + 1
  captchaText.value = `${a} + ${b} = ?`
  captchaInput.value = '' // 留空让用户填，点验证码图片可刷新
}
genCaptcha()

async function handleLogin() {
  // 验证码校验（留空则跳过）
  if (captchaInput.value) {
    const expected = captchaText.value.replace(' = ?', '').split(' + ').reduce((s:number,n:string)=>s+parseInt(n),0).toString()
    if (captchaInput.value !== expected) { genCaptcha(); return }
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.push('/')
  } catch (e: any) {
    // 生产模式：密码错误/账户锁定/密码过期等均带 detail 说明；开发模式登录失败同样提示
    const detail = e?.response?.data?.detail
    if (detail) ElMessage.error(detail)
    else ElMessage.error('登录失败，请检查用户名和密码')
  } finally { loading.value = false }
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
/* 验证码 */
.captcha-row { display: flex; gap: 10px; }
.captcha-input { flex: 1; }
.captcha-box { width: 110px; height: 44px; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #EFF6FF, #F0F7FF); border: 1px solid var(--c-border); border-radius: var(--r-sm); font-size: 14px; font-weight: var(--fw-bold); color: var(--c-accent); cursor: pointer; user-select: none; letter-spacing: 1px; }
/* 角色 */
.role-row { display: flex; gap: 4px; }
.role-btn { flex: 1; height: 36px; border-radius: var(--r-sm); border: 1px solid var(--c-border); background: var(--c-surface); color: var(--c-text-secondary); font-size: var(--fs-sm); cursor: pointer; transition: all var(--t-fast); }
.role-btn.active { background: var(--c-accent); color: #fff; border-color: var(--c-accent); }
.role-btn:hover:not(.active) { border-color: var(--c-accent); color: var(--c-accent); }
</style>
