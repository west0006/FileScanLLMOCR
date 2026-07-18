<template>
  <teleport to="body">
    <div v-if="visible" class="app-modal-overlay" @click.self="closeOnOverlay && emit('close')">
      <div class="app-modal" :style="{ width }">
        <div class="app-modal-head">
          <h3>{{ title }}</h3>
          <button class="app-modal-close" @click="emit('close')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div class="app-modal-body"><slot /></div>
        <div v-if="$slots.footer" class="app-modal-footer"><slot name="footer" /></div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
defineProps<{ visible: boolean; title: string; width?: string; closeOnOverlay?: boolean }>()
defineProps({ visible: Boolean, title: String, width: { type: String, default: '520px' }, closeOnOverlay: { type: Boolean, default: true } })
const emit = defineEmits(['close'])
</script>

<style scoped>
.app-modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;z-index:100;backdrop-filter:blur(4px)}
.app-modal{background:var(--c-surface);border-radius:var(--r-lg);box-shadow:var(--s-dropdown);max-height:80vh;overflow-y:auto}
.app-modal-head{display:flex;align-items:center;justify-content:space-between;padding:18px 22px;border-bottom:1px solid var(--c-border-light)}
.app-modal-head h3{margin:0;font-size:var(--fs-lg);font-weight:var(--fw-semibold)}
.app-modal-close{width:32px;height:32px;border-radius:var(--r-sm);border:none;background:transparent;cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--c-text-muted)}.app-modal-close:hover{background:var(--c-bg)}
.app-modal-body{padding:22px}
.app-modal-footer{padding:14px 22px;border-top:1px solid var(--c-border-light);display:flex;justify-content:flex-end;gap:8px}
</style>
