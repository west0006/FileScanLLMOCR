<template>
  <div class="not-found">
    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.2">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
    <h1>404</h1>
    <p>页面不存在</p>
    <router-link to="/home" class="back-link">返回首页</router-link>
  </div>
</template>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
  color: var(--c-text-muted);
}

.not-found h1 {
  font-size: 56px;
  font-weight: var(--fw-bold);
  color: var(--c-text);
  margin: 16px 0 4px;
}

.not-found p {
  font-size: var(--fs-lg);
  margin: 0 0 24px;
}

.back-link {
  padding: 8px 24px;
  border-radius: var(--r-sm);
  background: var(--c-accent);
  color: #fff;
  text-decoration: none;
  font-size: var(--fs-sm);
  font-weight: var(--fw-medium);
  transition: background var(--t-fast);
}

.back-link:hover {
  background: var(--c-accent-hover);
  opacity: 1;
}
</style>
