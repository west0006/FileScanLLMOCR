<template>
  <div class="empty-state">
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
    <p>{{ message }}</p>
    <span v-if="hint">{{ hint }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ message?: string; hint?: string }>()
defineProps({ message: { type: String, default: '暂无数据' }, hint: String })
</script>

<style scoped>
.empty-state{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:64px 20px;color:var(--c-text-muted);gap:6px}
.empty-state p{font-size:var(--fs-base);margin:0}.empty-state span{font-size:var(--fs-sm)}
</style>
