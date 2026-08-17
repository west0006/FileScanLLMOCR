<template>
  <div class="change-pwd-page">
    <div class="cp-card">
      <h2>修改密码</h2>
      <p class="cp-sub">修改成功后需重新登录</p>
      <div class="form-group">
        <label>原密码</label>
        <input v-model="form.old_password" type="password" class="field-input" placeholder="请输入原密码"
          @keyup.enter="submit" />
      </div>
      <div class="form-group">
        <label>新密码</label>
        <input v-model="form.new_password" type="password" class="field-input" placeholder="不少于12位，含大小写/数字/特殊字符" />
      </div>
      <div class="form-group">
        <label>确认新密码</label>
        <input v-model="confirmPwd" type="password" class="field-input" placeholder="再次输入新密码" @keyup.enter="submit" />
      </div>
      <button class="btn-primary" :disabled="submitting" @click="submit">{{ submitting ? '提交中...' : '确认修改' }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { userApi } from '@/api'
import { ElMessage } from 'element-plus'
import { passwordComplexityError } from '@/constants'

const router = useRouter()
const form = reactive({ old_password: '', new_password: '' })
const confirmPwd = ref('')
const submitting = ref(false)

async function submit() {
  if (!form.old_password) { ElMessage.warning('请输入原密码'); return }
  const err = passwordComplexityError(form.new_password)
  if (err) { ElMessage.warning(err); return }
  if (form.new_password !== confirmPwd.value) { ElMessage.warning('两次输入的新密码不一致'); return }
  submitting.value = true
  try {
    const res = await userApi.changePassword(form.old_password, form.new_password)
    if (res.data && res.data.error) { ElMessage.error(res.data.error); return }
    ElMessage.success('密码修改成功，请重新登录')
    localStorage.removeItem('access_token')
    router.push('/login')
  } catch { ElMessage.error('修改失败，请确认原密码正确') } finally { submitting.value = false }
}
</script>

<style scoped>
.change-pwd-page {
  max-width: 480px;
  margin: 0 auto;
  padding-top: 40px;
}

.cp-card {
  background: var(--c-surface);
  border-radius: var(--r-lg);
  border: 1px solid var(--c-border);
  padding: 32px;
}

.cp-card h2 {
  font-size: var(--fs-xl);
  font-weight: var(--fw-semibold);
  margin: 0 0 4px;
}

.cp-sub {
  font-size: var(--fs-sm);
  color: var(--c-text-muted);
  margin: 0 0 24px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: var(--fs-sm);
  font-weight: var(--fw-medium);
  color: var(--c-text-secondary);
  margin-bottom: 6px;
}

.field-input {
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-sm);
  font-size: var(--fs-base);
  background: var(--c-bg);
  outline: none;
  font-family: var(--font);
  width: 100%;
}

.field-input:focus {
  border-color: var(--c-accent);
}

.btn-primary {
  height: 40px;
  padding: 0 20px;
  border-radius: var(--r-sm);
  border: none;
  background: var(--c-accent);
  color: #fff;
  font-size: var(--fs-base);
  font-weight: var(--fw-semibold);
  cursor: pointer;
  width: 100%;
}

.btn-primary:hover:not(:disabled) {
  background: var(--c-accent-hover);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
