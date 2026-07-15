<template>
  <div class="page">
    <div class="page-head"><h2>操作日志</h2><button class="btn-export"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>导出</button></div>
    <div class="filter-bar">
      <input placeholder="用户" class="filter-input" />
      <select class="filter-select"><option value="">全部类型</option><option>检索</option><option>浏览</option><option>下载</option><option>管理</option></select>
      <input type="date" class="filter-input" /> <span class="filter-sep">—</span> <input type="date" class="filter-input" />
      <button class="filter-btn">查询</button>
    </div>
    <div class="card">
      <table class="data-table">
        <thead><tr><th style="width:160px">操作时间</th><th style="width:100px">用户</th><th style="width:80px">类型</th><th style="width:80px">模块</th><th>操作描述</th><th style="width:120px">IP</th><th style="width:60px">结果</th></tr></thead>
        <tbody><tr><td colspan="7" class="table-empty">暂无日志记录</td></tr></tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.page{max-width:var(--page-max);margin:0 auto}.page-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}.page-head h2{font-size:var(--fs-xl);font-weight:var(--fw-semibold);margin:0}.btn-export{display:flex;align-items:center;gap:6px;height:36px;padding:0 18px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-sm);font-weight:var(--fw-medium);cursor:pointer}.btn-export:hover{border-color:var(--c-accent);color:var(--c-accent)}.filter-bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:16px;padding:12px 16px;background:var(--c-surface);border-radius:var(--r-md);border:1px solid var(--c-border)}.filter-input{height:36px;padding:0 10px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-sm);background:var(--c-bg);outline:none;font-family:var(--font)}.filter-select{height:36px;padding:0 12px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-sm);background:var(--c-bg);outline:none;cursor:pointer}.filter-sep{color:var(--c-text-muted)}.filter-btn{height:36px;padding:0 20px;border-radius:var(--r-sm);border:none;background:var(--c-accent);color:#fff;font-size:var(--fs-sm);font-weight:var(--fw-medium);cursor:pointer;margin-left:auto}.filter-btn:hover{background:var(--c-accent-hover)}.card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);overflow:hidden}.data-table{width:100%;border-collapse:collapse}.data-table th{padding:12px 16px;text-align:left;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);text-transform:uppercase;letter-spacing:0.5px;background:var(--c-bg);border-bottom:1px solid var(--c-border)}.table-empty{padding:48px;text-align:center;color:var(--c-text-muted)}
</style>
