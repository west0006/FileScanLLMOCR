<template>
  <div class="filter-bar"><slot /></div>
</template>

<style scoped>
.filter-bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:16px;padding:10px 16px;background:var(--c-surface);border-radius:var(--r-md);border:1px solid var(--c-border)}
</style>
