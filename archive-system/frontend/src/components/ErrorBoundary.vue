<template>
  <div class="error-boundary" v-if="hasError">
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
      <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
    <h3>页面加载异常</h3>
    <p>{{ error?.message || '未知错误' }}</p>
    <button @click="reset" class="retry-btn">重新加载</button>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'

const hasError = ref(false)
const error = ref<Error | null>(null)

onErrorCaptured((err) => {
  hasError.value = true
  error.value = err
  return false
})

function reset() { hasError.value = false; error.value = null }
</script>

<style scoped>
.error-boundary {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 80px 20px; text-align: center; color: var(--c-text-muted);
}
.error-boundary h3 { font-size: var(--fs-xl); color: var(--c-text); margin: 16px 0 4px; }
.error-boundary p { font-size: var(--fs-sm); margin: 0 0 20px; max-width: 400px; word-break: break-all; }
.retry-btn {
  padding: 8px 24px; border-radius: var(--r-sm); border: 1px solid var(--c-border);
  background: var(--c-surface); color: var(--c-text-secondary); font-size: var(--fs-sm);
  cursor: pointer; transition: all var(--t-fast);
}
.retry-btn:hover { border-color: var(--c-accent); color: var(--c-accent); }
</style>
