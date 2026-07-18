<template>
  <div class="page-head">
    <h2>{{ title }}</h2>
    <slot name="actions" />
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string }>()
defineProps({ title: String })
</script>

<style scoped>
.page-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}
.page-head h2{font-size:var(--fs-xl);font-weight:var(--fw-semibold);margin:0}
</style>
