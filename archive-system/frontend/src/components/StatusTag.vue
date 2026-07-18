<template>
  <div class="status-tag" :class="`st-${type}`"><slot /></div>
</template>

<script setup lang="ts">
defineProps<{ type?: 'success' | 'warning' | 'danger' | 'info' | 'plain' }>()
defineProps({ type: { type: String, default: 'plain' } })
</script>

<style scoped>
.status-tag{padding:2px 10px;border-radius:var(--r-full);font-size:11px;font-weight:var(--fw-bold);letter-spacing:.3px;display:inline-block}
.st-success{background:#F0FDF4;color:var(--c-success)}.st-warning{background:#FFFBEB;color:var(--c-warning)}.st-danger{background:#FEF2F2;color:var(--c-danger)}.st-info{background:#E0F2FE;color:var(--c-info)}.st-plain{background:var(--c-bg);color:var(--c-text-secondary)}
</style>
