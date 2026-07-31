<template>
  <div class="page">
    <div class="page-head"><h2>操作日志</h2><button class="btn-export" @click="handleExport"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>导出</button></div>
    <div class="log-tabs">
      <button v-for="tab in logTabs" :key="tab.key" :class="['log-tab', {active:logTab===tab.key}]" @click="logTab=tab.key;fetchLogs()">
        {{ tab.label }} <span class="tab-badge">{{ tab.count }}</span>
      </button>
    </div>
    <div class="stats-card">
      <span>📊 今日操作 <strong>{{ logStats.total }}</strong> 条</span>
      <span>|</span>
      <span>❌ 失败 <strong style="color:var(--c-danger)">{{ logStats.failed }}</strong> 条</span>
      <span>|</span>
      <span>📦 日志保留 <strong>{{ logStats.retention }}</strong> 天</span>
    </div>
    <div class="filter-bar">
      <input v-model="filters.username" placeholder="用户" class="filter-input" @keyup.enter="fetchLogs"/>
      <select v-model="filters.type" class="filter-select"><option value="">全部类型</option><option value="search">检索</option><option value="view">浏览</option><option value="download">下载</option><option value="admin">管理</option><option value="login">登录</option></select>
      <button class="filter-btn" @click="fetchLogs">查询</button>
      <button class="filter-btn-reset" @click="resetLogFilters">重置</button>
    </div>
    <div class="card">
      <table class="data-table">
        <thead><tr><th style="width:150px">操作时间</th><th style="width:80px">用户</th><th style="width:60px">类型</th><th style="width:60px">模块</th><th>操作描述</th><th style="width:110px">IP</th><th style="width:70px">结果</th></tr></thead>
        <tbody>
          <tr v-for="row in items" :key="row.id">
            <td class="text-sm">{{ row.created_at?.substring(0,19) }}</td>
            <td class="font-medium">{{ row.username }}</td>
            <td><span class="type-tag">{{ typeLabel(row.operation_type) }}</span></td>
            <td>{{ row.module }}</td>
            <td class="truncate" style="max-width:300px">{{ row.description }}</td>
            <td class="mono">{{ row.ip_address }}</td>
            <td><span class="risk-tag" :class="row.result==='success'?'risk-tag--low':'risk-tag--high'">{{ row.result==='success'?'成功':'失败' }}</span></td>
          </tr>
          <tr v-if="items.length===0"><td colspan="7" class="table-empty">暂无日志</td></tr>
        </tbody>
      </table>
    </div>
    <el-pagination v-if="total > pageSize" class="pager" background layout="prev, pager, next, sizes" :total="total" :page-size="pageSize" :current-page="page" :page-sizes="[20,50,100]" @current-change="p=>{page=p;fetchLogs()}" @size-change="s=>{pageSize=s;fetchLogs()}" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { logApi } from '@/api'
import { ElMessage } from 'element-plus'
import { OP_TYPE_LABELS } from '@/constants'

const items = ref<any[]>([])
const page = ref(1); const pageSize = ref(20); const total = ref(0)
const filters = ref({ username: '', type: '' })
const logTab = ref('all')
const logTabs = ref([
  { key: 'all', label: '全部', count: 0 },
  { key: 'login', label: '登录日志', count: 0 },
  { key: 'search', label: '检索日志', count: 0 },
  { key: 'review', label: '预审日志', count: 0 },
])
const logStats = ref({ total: 0, failed: 0, retention: 180 })

onMounted(() => fetchLogs())

async function fetchLogs() {
  try {
    const params: any = { page: page.value, page_size: pageSize.value,
      user_account: filters.value.username || undefined,
      operation_type: logTab.value !== 'all' ? logTab.value : filters.value.type || undefined,
    }
    const res = await logApi.list(params)
    items.value = res.data.items || []
    total.value = res.data.total || 0
    // 更新 tab 计数（仅全部 tab 时）
    if (logTab.value === 'all' && !filters.value.username && !filters.value.type) {
      const [allR, loginR, searchR, reviewR] = await Promise.all([
        logApi.list({ page:1, page_size:1 }),
        logApi.list({ page:1, page_size:1, operation_type:'login' }),
        logApi.list({ page:1, page_size:1, operation_type:'search' }),
        logApi.list({ page:1, page_size:1, operation_type:'review' }),
      ])
      logTabs.value[0].count = allR.data.total || 0
      logTabs.value[1].count = loginR.data.total || 0
      logTabs.value[2].count = searchR.data.total || 0
      logTabs.value[3].count = reviewR.data.total || 0
    }
    // 更新统计卡
    logStats.value.total = allR.data.total || 0
    try { const summary = await logApi.auditSummary(); logStats.value.failed = summary.data.failed_operations || 0 } catch { logStats.value.failed = 0 }
  } catch { /* ignore */ }
}

function typeLabel(t: string) { return OP_TYPE_LABELS[t] || t }
function resetLogFilters() { filters.value = { username: '', type: '' }; fetchLogs() }
function handleExport() {
  try {
    const filters: any = {}
    if (filters.value.username) filters.user_account = filters.value.username
    if (filters.value.type) filters.operation_type = filters.value.type
    if (logTab.value !== 'all') filters.operation_type = logTab.value
    logApi.export(filters).then((res: any) => {
      const a = document.createElement('a')
      a.href = `/api/log/export?format=excel`
      a.download = res.data?.file || '操作日志.xlsx'
      a.click()
      ElMessage.success(`导出成功: ${res.data?.count || '?'} 条`)
    }).catch(() => ElMessage.error('导出失败'))
  } catch { ElMessage.error('导出失败') }
}
</script>

<style scoped>
.page{max-width:var(--page-max);margin:0 auto}.page-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}.page-head h2{font-size:var(--fs-xl);font-weight:var(--fw-semibold);margin:0}.btn-export{display:flex;align-items:center;gap:6px;height:36px;padding:0 18px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-sm);font-weight:var(--fw-medium);cursor:pointer}.btn-export:hover{border-color:var(--c-accent);color:var(--c-accent)}.log-tabs{display:flex;gap:4px;margin-bottom:12px}.log-tab{padding:5px 14px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-sm);cursor:pointer;transition:all var(--t-fast);display:flex;align-items:center;gap:6px}.log-tab.active{background:var(--c-accent);color:#fff;border-color:var(--c-accent)}.log-tab:hover:not(.active){border-color:var(--c-accent);color:var(--c-accent)}.tab-badge{padding:0 6px;border-radius:var(--r-full);font-size:10px;background:var(--c-bg);font-weight:var(--fw-bold)}.log-tab.active .tab-badge{background:rgba(255,255,255,0.2)}.filter-bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:16px;padding:12px 16px;background:var(--c-surface);border-radius:var(--r-md);border:1px solid var(--c-border)}.filter-input{height:36px;padding:0 10px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-sm);background:var(--c-bg);outline:none;font-family:var(--font)}.filter-select{height:36px;padding:0 12px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-sm);background:var(--c-bg);outline:none;cursor:pointer}.filter-btn{height:36px;padding:0 20px;border-radius:var(--r-sm);border:none;background:var(--c-accent);color:#fff;font-size:var(--fs-sm);font-weight:var(--fw-medium);cursor:pointer;margin-left:auto}.filter-btn:hover{background:var(--c-accent-hover)}.filter-btn-reset{height:36px;padding:0 16px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-sm);cursor:pointer}.filter-btn-reset:hover{border-color:var(--c-text-muted);color:var(--c-text)}.card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);overflow:hidden}.data-table{width:100%;border-collapse:collapse}.data-table th{padding:12px 16px;text-align:left;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);text-transform:uppercase;letter-spacing:0.5px;background:var(--c-bg);border-bottom:1px solid var(--c-border)}.data-table td{padding:12px 16px;font-size:var(--fs-sm);color:var(--c-text);border-bottom:1px solid var(--c-border-light)}.mono{font-family:'SF Mono','Fira Code',monospace;font-size:11px;color:var(--c-text-secondary)}.risk-tag{padding:2px 10px;border-radius:var(--r-full);font-size:11px;font-weight:var(--fw-bold)}.risk-tag--low{background:#F0FDF4;color:var(--c-success)}.risk-tag--high{background:#FEF2F2;color:var(--c-danger)}.type-tag{padding:1px 8px;border-radius:var(--r-full);font-size:11px;background:var(--c-bg);color:var(--c-text-secondary)}.table-empty{padding:48px;text-align:center;color:var(--c-text-muted)}.text-sm{font-size:var(--fs-xs);color:var(--c-text-secondary)}.font-medium{font-weight:var(--fw-medium)}.truncate{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pager{margin-top:16px;display:flex;justify-content:center}
.stats-card{padding:10px 14px;margin-bottom:12px;background:var(--c-surface);border-radius:var(--r-md);border:1px solid var(--c-border);font-size:var(--fs-sm);color:var(--c-text-secondary);display:flex;gap:12px}
</style>
