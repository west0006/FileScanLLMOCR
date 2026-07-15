<template>
  <div class="page">
    <div class="page-head"><h2>查询利用统计</h2></div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">1,234</div><div class="stat-label">总检索次数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">567</div><div class="stat-label">浏览条目数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">89</div><div class="stat-label">下载次数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">12</div><div class="stat-label">活跃用户</div>
      </div>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="chart-placeholder">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        <p>趋势图表区域</p><span>ECharts 柱状/折线图</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page{max-width:var(--page-max);margin:0 auto}.page-head{margin-bottom:20px}.page-head h2{font-size:var(--fs-xl);font-weight:var(--fw-semibold);margin:0}.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.stat-card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);padding:20px;text-align:center}.stat-value{font-size:var(--fs-3xl);font-weight:var(--fw-bold);color:var(--c-accent)}.stat-label{font-size:var(--fs-sm);color:var(--c-text-muted);margin-top:4px}.card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);overflow:hidden}.chart-placeholder{display:flex;flex-direction:column;align-items:center;justify-content:center;height:320px;color:var(--c-text-muted);gap:8px}.chart-placeholder p{font-size:var(--fs-lg);margin:0}.chart-placeholder span{font-size:var(--fs-sm)}
</style>
