<template>
  <div class="page">
    <div class="page-head"><h2>操作日志</h2><button class="btn-export" @click="handleExport"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>导出</button></div>
    <div class="log-toolbar">
      <div class="log-tabs">
        <button v-for="tab in logTabs" :key="tab.key" :class="['log-tab', {active:logTab===tab.key}]" @click="logTab=tab.key;fetchLogs()">
          {{ tab.label }} <span class="tab-badge">{{ tab.count }}</span>
        </button>
      </div>
      <div class="stats-card">
        <span><IconSvg name="chart" size="15" /> 今日操作 <strong>{{ logStats.total }}</strong></span>
        <span class="stats-sep">|</span>
        <span><IconSvg name="warn" size="14" /> 失败 <strong style="color:var(--c-danger)">{{ logStats.failed }}</strong></span>
        <span class="stats-sep">|</span>
        <span><IconSvg name="pkg" size="15" /> 保留 <strong>{{ logStats.retention }}</strong> 天</span>
      </div>
    </div>
    <div class="filter-bar">
      <input v-model="filters.username" placeholder="用户" class="filter-input" @keyup.enter="fetchLogs"/>
      <select v-model="filters.type" class="filter-select"><option value="">全部类型</option><option value="search">检索</option><option value="view">浏览</option><option value="download">下载</option><option value="admin">管理</option><option value="login">登录</option></select>
      <input v-model="filters.date_from" type="date" class="filter-input filter-input--date" title="开始日期" />
      <span class="filter-sep">—</span>
      <input v-model="filters.date_to" type="date" class="filter-input filter-input--date" title="结束日期" />
      <button class="filter-btn" @click="fetchLogs">查询</button>
      <button class="filter-btn-reset" @click="resetLogFilters">重置</button>
    </div>
    <div class="card">
      <table class="data-table">
        <thead><tr><th style="width:150px">操作时间</th><th style="width:80px">用户</th><th style="width:60px">类型</th><th>操作描述</th><th style="width:120px">操作对象</th><th style="width:110px">IP</th><th style="width:70px">结果</th></tr></thead>
        <tbody>
          <tr v-for="row in items" :key="row.id">
            <td class="text-sm">{{ row.created_at?.substring(0,19) }}</td>
            <td class="font-medium">{{ row.username }}</td>
            <td><span class="type-tag">{{ typeLabel(row.operation_type) }}</span></td>
            <td class="truncate" style="max-width:280px">{{ row.description }}</td>
            <td class="mono truncate" style="max-width:110px">{{ row.target_id || '—' }}</td>
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
const filters = ref({ username: '', type: '', date_from: '', date_to: '' })
const logTab = ref('all')
const logTabs = ref([
  { key: 'all', label: '全部', count: 0 },
  { key: 'login', label: '登录日志', count: 0 },
  { key: 'search', label: '检索日志', count: 0 },
  { key: 'review', label: '预审日志', count: 0 },
])
const logStats = ref({ total: 0, failed: 0, retention: 1095 })

onMounted(() => fetchLogs())

async function fetchLogs() {
  try {
    const params: any = { page: page.value, page_size: pageSize.value,
      user_account: filters.value.username || undefined,
      operation_type: logTab.value !== 'all' ? logTab.value : filters.value.type || undefined,
      date_from: filters.value.date_from || undefined,
      date_to: filters.value.date_to || undefined,
    }
    const res = await logApi.list(params)
    items.value = res.data.items || []
    total.value = res.data.total || 0
    // 更新统计卡和 tab 计数
    try {
      const [allR, loginR, searchR, reviewR, summary] = await Promise.all([
        logApi.list({ page:1, page_size:1 }),
        logApi.list({ page:1, page_size:1, operation_type:'login' }),
        logApi.list({ page:1, page_size:1, operation_type:'search' }),
        logApi.list({ page:1, page_size:1, operation_type:'review' }),
        logApi.auditSummary().catch(() => ({ data: { today_failed: 0 } })),
      ])
      logTabs.value[0].count = allR.data.total || 0
      logTabs.value[1].count = loginR.data.total || 0
      logTabs.value[2].count = searchR.data.total || 0
      logTabs.value[3].count = reviewR.data.total || 0
      logStats.value.total = allR.data.total || 0
      logStats.value.failed = summary.data.today_failed || 0
    } catch { /* ignore */ }
  } catch { /* ignore */ }
}

function typeLabel(t: string) { return OP_TYPE_LABELS[t] || t }
function resetLogFilters() { filters.value = { username: '', type: '', date_from: '', date_to: '' }; fetchLogs() }
function handleExport() {
  const params: any = {}
  if (filters.value.username) params.user_account = filters.value.username
  if (filters.value.type) params.operation_type = filters.value.type
  if (filters.value.date_from) params.date_from = filters.value.date_from
  if (filters.value.date_to) params.date_to = filters.value.date_to
  if (logTab.value !== 'all') params.operation_type = logTab.value
  logApi.export(params).then((res: any) => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = '操作日志.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  }).catch(() => ElMessage.error('导出失败'))
}
</script>

<style scoped>
.page{max-width:var(--page-max);margin:0 auto}.page-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}.page-head h2{font-size:var(--fs-xl);font-weight:var(--fw-semibold);margin:0}.btn-export{display:flex;align-items:center;gap:6px;height:36px;padding:0 18px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-sm);font-weight:var(--fw-medium);cursor:pointer}.btn-export:hover{border-color:var(--c-accent);color:var(--c-accent)}.log-toolbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;gap:12px}.log-tabs{display:flex;gap:4px}.log-tab{padding:5px 14px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-sm);cursor:pointer;transition:all var(--t-fast);display:flex;align-items:center;gap:6px}.log-tab.active{background:var(--c-accent);color:#fff;border-color:var(--c-accent)}.log-tab:hover:not(.active){border-color:var(--c-accent);color:var(--c-accent)}.tab-badge{padding:0 6px;border-radius:var(--r-full);font-size:10px;background:var(--c-bg);font-weight:var(--fw-bold)}.log-tab.active .tab-badge{background:rgba(255,255,255,0.2)}.stats-card{display:flex;align-items:center;gap:8px;font-size:var(--fs-sm);color:var(--c-text-secondary);white-space:nowrap}.stats-sep{color:var(--c-border)}.filter-bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:16px;padding:12px 16px;background:var(--c-surface);border-radius:var(--r-md);border:1px solid var(--c-border)}.filter-input{height:36px;padding:0 10px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-sm);background:var(--c-bg);outline:none;font-family:var(--font)}.filter-select{height:36px;padding:0 12px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-sm);background:var(--c-bg);outline:none;cursor:pointer}.filter-btn{height:36px;padding:0 20px;border-radius:var(--r-sm);border:none;background:var(--c-accent);color:#fff;font-size:var(--fs-sm);font-weight:var(--fw-medium);cursor:pointer;margin-left:auto}.filter-btn:hover{background:var(--c-accent-hover)}.filter-btn-reset{height:36px;padding:0 16px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-sm);cursor:pointer}.filter-btn-reset:hover{border-color:var(--c-text-muted);color:var(--c-text)}
.filter-input--date{width:130px}.filter-sep{font-size:var(--fs-sm);color:var(--c-text-muted)}.card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);overflow:hidden;overflow-x:auto}.data-table{width:100%;border-collapse:collapse}.data-table th{padding:12px 16px;text-align:left;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);text-transform:uppercase;letter-spacing:0.5px;background:var(--c-bg);border-bottom:1px solid var(--c-border)}.data-table td{padding:12px 16px;font-size:var(--fs-sm);color:var(--c-text);border-bottom:1px solid var(--c-border-light)}.mono{font-family:'SF Mono','Fira Code',monospace;font-size:11px;color:var(--c-text-secondary)}.risk-tag{padding:2px 10px;border-radius:var(--r-full);font-size:11px;font-weight:var(--fw-bold)}.risk-tag--low{background:#F0FDF4;color:var(--c-success)}.risk-tag--high{background:#FEF2F2;color:var(--c-danger)}.type-tag{padding:1px 8px;border-radius:var(--r-full);font-size:11px;background:var(--c-bg);color:var(--c-text-secondary)}.table-empty{padding:48px;text-align:center;color:var(--c-text-muted)}.text-sm{font-size:var(--fs-xs);color:var(--c-text-secondary)}.font-medium{font-weight:var(--fw-medium)}.truncate{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pager{margin-top:16px;display:flex;justify-content:center}
</style>
