<template>
  <div class="stats-page">
    <div v-if="hasError" class="error-banner"><IconSvg name="warn" size="14" /> {{ errorMsg }}</div>

    <!-- 概览卡片 -->
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-icon stat-icon--green"><IconSvg name="folder" size="14" /></div><div class="stat-label">总操作记录</div><div class="stat-value">{{ summary.total_operations }}</div></div>
      <div class="stat-card"><div class="stat-icon stat-icon--blue"><IconSvg name="search" size="14" /></div><div class="stat-label">检索次数</div><div class="stat-value">{{ summary.search_count }}</div></div>
      <div class="stat-card"><div class="stat-icon stat-icon--purple"><IconSvg name="clip" size="15" /></div><div class="stat-label">审核操作</div><div class="stat-value">{{ summary.review_count }}</div></div>
      <div class="stat-card"><div class="stat-icon stat-icon--amber"><IconSvg name="warn" size="14" /></div><div class="stat-label">失败操作</div><div class="stat-value">{{ summary.failed_count }}</div></div>
    </div>

    <!-- 图表行 -->
    <div class="charts-row">
      <div class="chart-card"><h3>按操作类型统计</h3><div ref="typeChartRef" class="chart-box"></div><div v-if="!typeHasData" class="chart-empty">暂无数据</div></div>
      <div class="chart-card"><h3>按用户统计 (Top 10)</h3><div ref="userChartRef" class="chart-box"></div><div v-if="!userHasData" class="chart-empty">暂无数据</div></div>
    </div>
    <div class="charts-row">
      <div class="chart-card chart-card--full">
        <div class="chart-head"><h3>操作趋势</h3>
          <select v-model="timeGranularity" @change="loadTimeChart" class="chart-select">
            <option value="day">按日</option><option value="week">按周</option><option value="month">按月</option><option value="quarter">按季度</option><option value="year">按年</option>
          </select>
        </div>
        <div ref="timeChartRef" class="chart-box"></div>
        <div v-if="!timeHasData" class="chart-empty">暂无数据</div>
      </div>
    </div>

    <!-- ST-001: 按用户账号统计 -->
    <div class="card">
      <div class="card-head">
        <h3>按用户账号统计 (ST-001)</h3>
        <button class="btn-sm" @click="showExportOptions = true"><IconSvg name="download" size="14" /> 导出报表</button>
      </div>
      <div class="filter-bar">
        <select v-model="userFilter.role" class="filter-input-sm"><option value="">全部角色</option><option>system_admin</option><option>archive_admin</option><option>reviewer</option></select>
        <select v-model="userFilter.period" class="filter-input-sm"><option value="month">本月</option><option value="quarter">本季度</option><option value="year">本年度</option><option value="all">全部</option></select>
        <button class="btn-accent-sm" @click="fetchUserRanking">查询</button>
      </div>
      <table class="data-table">
        <thead><tr>
          <th>排名</th><th>用户</th><th>角色</th><th>检索</th><th>条目浏览</th><th>文件浏览</th><th>下载</th><th>打印</th><th>合计</th>
        </tr></thead>
        <tbody>
          <tr v-for="(u, i) in userRanking" :key="u.username">
            <td><strong>{{ i + 1 }}</strong></td>
            <td class="font-medium">{{ u.name || u.username }}</td>
            <td><span class="role-tag" :class="'role--'+u.role">{{ roleLabel(u.role) }}</span></td>
            <td>{{ u.search || 0 }}</td>
            <td>{{ u.view_entry || 0 }}</td>
            <td>{{ u.view_file || 0 }}</td>
            <td>{{ u.download || 0 }}</td>
            <td>{{ u.print || 0 }}</td>
            <td><strong class="text-accent">{{ (u.search||0)+(u.view_entry||0)+(u.view_file||0)+(u.download||0)+(u.print||0) }}</strong></td>
          </tr>
          <tr v-if="!userRanking.length"><td colspan="9" class="table-empty">暂无数据</td></tr>
        </tbody>
      </table>
    </div>

    <!-- 利用方式明细统计 -->
    <div class="card">
      <div class="card-head"><h3>利用方式明细统计</h3></div>
      <table class="data-table">
        <thead><tr><th>利用方式</th><th>本月次数</th><th>本月占比</th><th>本年累计</th><th>趋势</th></tr></thead>
        <tbody>
          <tr v-for="m in methodDetail" :key="m.type">
            <td><strong>{{ typeLabel(m.type) }}</strong></td>
            <td>{{ m.month_count }}</td>
            <td><div class="pct-row"><div class="pct-bar"><div class="pct-fill" :style="{width:m.pct+'%'}"></div></div><span class="pct-num">{{ m.pct }}%</span></div></td>
            <td>{{ m.year_count }}</td>
            <td>{{ m.trend === 'up' ? '↑ 上升' : m.trend === 'down' ? '↓ 下降' : '→ 平稳' }}</td>
          </tr>
          <tr v-if="!methodDetail.length"><td colspan="5" class="table-empty">暂无数据</td></tr>
        </tbody>
      </table>
    </div>
    <!-- 导出选项弹窗 -->
    <div v-if="showExportOptions" class="modal-overlay" @click.self="showExportOptions=false">
      <div class="modal-card" style="width:400px">
        <div class="modal-head"><h3>自定义导出</h3><button class="modal-close" @click="showExportOptions=false"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
        <div class="modal-body">
          <div class="form-group"><label>文件格式</label>
            <select v-model="exportFormat" class="field-input"><option value="csv">CSV</option><option value="excel">Excel</option></select>
          </div>
          <div class="form-group"><label>导出字段</label>
            <label v-for="f in exportFields" :key="f.key" class="perm-item"><input type="checkbox" v-model="f.selected" /><span class="perm-label">{{ f.label }}</span></label>
          </div>
          <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
            <button class="btn-sm" @click="showExportOptions=false">取消</button>
            <button class="btn-primary" @click="doExportTable">导出</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { statsApi } from '@/api'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { ROLE_LABELS, OP_TYPE_LABELS } from '@/constants'

const typeChartRef = ref<HTMLElement>()
const userChartRef = ref<HTMLElement>()
const timeChartRef = ref<HTMLElement>()
const timeGranularity = ref('day')
const summary = reactive({ total_operations:0, search_count:0, review_count:0, failed_count:0 })
const userRanking = ref<any[]>([])
const methodDetail = ref<any[]>([])
const userFilter = reactive({ role:'', period:'month' })
const hasError = ref(false)
const errorMsg = ref('')
const typeHasData = ref(true)
const userHasData = ref(true)
const timeHasData = ref(true)

function roleLabel(r: string) { return ROLE_LABELS[r] || r }
function typeLabel(t: string) { return OP_TYPE_LABELS[t] || t }
function userTotal(u: any) { return (u.search||0)+(u.view_entry||0)+(u.view_file||0)+(u.download||0)+(u.print||0) }

onMounted(async () => {
  try {
    const [tr, ur] = await Promise.all([statsApi.byType({}), statsApi.byUser({top_n:10})])
    const typeData = tr.data.items || []
    const userData = ur.data.items || []
    summary.total_operations = typeData.reduce((s:number,i:any)=>s+(i.count||0),0)
    summary.search_count = typeData.find((i:any)=>i.type==='search')?.count||0
    summary.review_count = typeData.find((i:any)=>i.type==='review')?.count||0
    summary.failed_count = (tr.data.failed || tr.data.items?.find((i:any)=>i.type==='failure')?.count) || 0
    typeHasData.value = typeData.length > 0
    userHasData.value = userData.length > 0
    await nextTick()
    loadTimeChart()
    if(typeChartRef.value){_initChart(typeChartRef, {tooltip:{trigger:'item'},legend:{bottom:0},series:[{type:'pie',radius:['45%','75%'],center:['50%','45%'],itemStyle:{borderRadius:4,borderColor:'#fff',borderWidth:2},label:{show:false},data:typeData.map((t:any)=>({name:typeLabel(t.type),value:t.count})),color:['#10B981','#6366F1','#8B5CF6','#06B6D4','#F59E0B','#94A3B8']}]})}
    if(userChartRef.value){_initChart(userChartRef, {tooltip:{trigger:'axis'},grid:{left:10,right:20,top:10,bottom:0,containLabel:true},xAxis:{type:'value',axisLine:{show:false},axisTick:{show:false},splitLine:{lineStyle:{color:'#F1F5F9'}}},yAxis:{type:'category',data:userData.map((u:any)=>u.username||u.name).reverse(),axisLine:{show:false},axisTick:{show:false}},series:[{type:'bar',data:userData.map((u:any)=>userTotal(u)).reverse(),barWidth:14,itemStyle:{borderRadius:[0,6,6,0],color:'#10B981'},emphasis:{itemStyle:{color:'#059669'}}}]})}
    fetchUserRanking()
  } catch {
    hasError.value = true
    errorMsg.value = '统计接口请求失败，请检查后端服务是否正常。页面显示均为0，不代表真实数据。'
  }
})

let rankSeq = 0  // 请求序号，防快速连点查询时旧响应覆盖新数据

async function fetchUserRanking() {
  const seq = ++rankSeq
  try {
    const res = await statsApi.byUser({top_n:20,role:userFilter.role||undefined,period:userFilter.period})
    if (seq !== rankSeq) return
    const ranking = (res.data.items||[]).map((u:any)=>({...u,name:u.name||u.username,role:u.role||'reviewer'}))
    userRanking.value = ranking
    const types = ['search','view_entry','view_file','download','print']
    const total = ranking.reduce((s: number, u: any)=>{types.forEach(t=>{u[t]=u[t]||0}); return s+userTotal(u)},0)
    // 当月数据
    methodDetail.value = types.map(t=>{
      const month = ranking.reduce((s: number, u: any)=>s+(u[t]||0),0)
      return {type:t, month_count:month, pct:total?+(month/total*100).toFixed(1):0, year_count:0, trend:'flat'}
    })
    // 异步获取本年累计（by-user period=year）
    statsApi.byUser({top_n:20,period:'year',role:userFilter.role||undefined}).then(yr => {
      if (seq !== rankSeq) return  // 旧请求的异步回调丢弃
      const yrRanking = yr.data.items || []
      methodDetail.value = types.map(t => {
        const month = ranking.reduce((s: number, u: any)=>s+(u[t]||0),0)
        const year = yrRanking.reduce((s: number, u: any)=>s+(u[t]||0),0)
        const pct = total ? +(month/total*100).toFixed(1) : 0
        const trend = year > 0 && month > year/12*1.1 ? 'up' : month < year/12*0.9 ? 'down' : 'flat'
        return {type:t, month_count:month, pct, year_count:year, trend}
      })
    }).catch(() => {})
    hasError.value = false
  } catch {
    if (seq !== rankSeq) return
    userRanking.value = []
    methodDetail.value = []
    hasError.value = true
    errorMsg.value = '统计接口请求失败，请检查后端服务是否正常。'
  }
}

const TREND_COLORS: Record<string, string> = { search: '#10B981', view_entry: '#6366F1', view_file: '#8B5CF6', download: '#F59E0B', print: '#06B6D4' }
const TREND_NAMES: Record<string, string> = { search: '检索', view_entry: '条目浏览', view_file: '文件浏览', download: '下载', print: '打印' }

let timeSeq = 0  // 请求序号，防快速切换粒度时旧响应覆盖新数据

async function loadTimeChart() {
  if(!timeChartRef.value) return
  const seq = ++timeSeq
  let timeData:any[]=[]
  try{const res=await statsApi.byTime({granularity:timeGranularity.value,days:timeGranularity.value==='year'?365:timeGranularity.value==='quarter'?90:30});timeData=res.data.items||[]}catch{timeData=[]}
  if (seq !== timeSeq) return
  timeHasData.value = timeData.length > 0
  const types = ['search','view_entry','view_file','download','print']
  _initChart(timeChartRef, {
    tooltip:{trigger:'axis'},
    legend:{bottom:0, data: types.map(t => TREND_NAMES[t]), textStyle:{fontSize:10}},
    grid:{left:40,right:20,top:10,bottom:35},
    xAxis:{type:'category',data:timeData.map((i:any)=>i.period),axisLabel:{rotate:timeGranularity.value==='day'?45:0,fontSize:10}},
    yAxis:{type:'value',minInterval:1},
    series: types.map(t => ({
      name: TREND_NAMES[t],
      type:'line',
      data:timeData.map((i:any)=>i[t]||0),
      smooth:true, symbol:'circle', symbolSize:4,
      lineStyle:{color:TREND_COLORS[t],width:2},
      itemStyle:{color:TREND_COLORS[t]},
    }))
  })
}

const _charts: any[] = []
function _initChart(ref: any, option: any) {
  if (!ref || !ref.value) return
  const c = echarts.init(ref.value)
  c.setOption(option)
  _charts.push(c)
  return c
}
function _resizeCharts() { _charts.forEach(c => { try { c.resize() } catch {} }) }
onUnmounted(() => { _charts.forEach(c => { try { c.dispose() } catch {} }) })
onMounted(() => { window.addEventListener('resize', _resizeCharts) })
onUnmounted(() => { window.removeEventListener('resize', _resizeCharts) })

const showExportOptions = ref(false)
const exportFormat = ref('csv')
const exportFields = reactive([
  { key: 'name', label: '用户名', selected: true },
  { key: 'role', label: '角色', selected: true },
  { key: 'search', label: '检索次数', selected: true },
  { key: 'view_entry', label: '条目浏览', selected: true },
  { key: 'view_file', label: '文件浏览', selected: true },
  { key: 'download', label: '下载次数', selected: true },
  { key: 'print', label: '打印次数', selected: true },
])

function doExportTable() {
  const fields = exportFields.filter(f => f.selected)
  if (!fields.length) { ElMessage.warning('至少选择一个字段'); return }
  const rows = userRanking.value
  if (!rows.length) { ElMessage.warning('暂无数据可导出'); return }
  const headers = fields.map(f => f.label)
  const keys = fields.map(f => f.key)
  const dataRows = rows.map(r => keys.map(k => {
    return k === 'name' ? (r.name || r.username) : k === 'role' ? roleLabel(r.role) : (r[k] || 0)
  }))

  if (exportFormat.value === 'excel') {
    // 使用 xlsx 库生成真实 Excel
    import('xlsx').then((XLSX) => {
      const ws = XLSX.utils.aoa_to_sheet([headers, ...dataRows])
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, '统计报表')
      XLSX.writeFile(wb, `统计报表_${new Date().toISOString().slice(0,10)}.xlsx`)
      ElMessage.success(`导出成功 (${fields.length} 个字段, ${rows.length} 条)`)
      showExportOptions.value = false
    }).catch(() => ElMessage.error('Excel 导出失败'))
    return
  }

  // CSV
  const csv = [
    headers.join(','),
    ...dataRows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(','))
  ].join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `统计报表_${new Date().toISOString().slice(0,10)}.csv`; a.click()
  window.URL.revokeObjectURL(url)
  ElMessage.success(`导出成功 (${fields.length} 个字段, ${rows.length} 条)`)
  showExportOptions.value = false
}

function exportTable(id: string) {
  try {
    // 导出当前排名表数据为 CSV
    const rows = userRanking.value
    if (!rows.length) { ElMessage.warning('暂无数据可导出'); return }
    const headers = ['排名','用户','角色','检索','浏览','下载','打印','合计']
    const csv = [
      headers.join(','),
      ...rows.map((r, i) => [
        i + 1,
        `"${r.name || r.username}"`,
        `"${roleLabel(r.role)}"`,
        r.search || 0, r.view || 0, r.download || 0, r.print || 0,
        (r.search||0)+(r.view||0)+(r.download||0)+(r.print||0),
      ].join(','))
    ].join('\n')
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `统计报表_${new Date().toISOString().slice(0,10)}.csv`; a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch { ElMessage.error('导出失败') }
}
</script>

<style scoped>
.stats-page{max-width:var(--page-max);margin:0 auto}
.error-banner{padding:12px 18px;margin-bottom:16px;background:#FEF2F2;border:1px solid #FECACA;border-radius:var(--r-md);color:var(--c-danger);font-size:var(--fs-sm);font-weight:var(--fw-medium)}
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.stat-card{background:var(--c-surface);border-radius:var(--r-lg);padding:20px;border:1px solid var(--c-border);position:relative;overflow:hidden}
.stat-icon{position:absolute;right:16px;top:14px;font-size:24px;opacity:.6}
.stat-label{font-size:var(--fs-sm);color:var(--c-text-secondary);margin-bottom:6px}
.stat-value{font-size:28px;font-weight:var(--fw-bold);color:var(--c-text)}
.charts-row{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px}
.chart-card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);padding:20px}
.chart-card h3{font-size:var(--fs-base);font-weight:var(--fw-semibold);color:var(--c-text);margin:0 0 16px}
.chart-box{height:300px}
.chart-empty{height:200px;display:flex;align-items:center;justify-content:center;color:var(--c-text-muted);font-size:var(--fs-sm)}
.chart-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
.chart-head h3{margin:0}
.chart-select{height:32px;padding:0 10px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-xs);background:var(--c-bg);outline:none;cursor:pointer}

.card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);overflow:hidden;margin-bottom:24px}
.card-head{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--c-border-light)}
.card-head h3{font-size:var(--fs-base);font-weight:var(--fw-semibold);margin:0}
.btn-sm{height:30px;padding:0 14px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-xs);cursor:pointer}.btn-sm:hover{border-color:var(--c-accent);color:var(--c-accent)}
.btn-accent-sm{height:30px;padding:0 14px;border-radius:var(--r-sm);border:none;background:var(--c-accent);color:#fff;font-size:var(--fs-xs);cursor:pointer}.btn-accent-sm:hover{background:var(--c-accent-hover)}

.filter-bar{display:flex;gap:8px;align-items:center;padding:12px 20px;border-bottom:1px solid var(--c-border-light)}
.filter-input-sm{height:32px;padding:0 10px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-xs);background:var(--c-bg);outline:none;cursor:pointer}

.data-table{width:100%;border-collapse:collapse}
.data-table th{padding:10px 16px;text-align:left;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);background:var(--c-bg);border-bottom:1px solid var(--c-border)}
.data-table td{padding:10px 16px;font-size:var(--fs-sm);color:var(--c-text);border-bottom:1px solid var(--c-border-light)}
.table-empty{padding:32px;text-align:center;color:var(--c-text-muted)}

.role-tag{padding:1px 8px;border-radius:var(--r-full);font-size:11px}.role--system_admin{background:#F3E8FF;color:var(--c-purple)}.role--archive_admin{background:#E0F2FE;color:var(--c-info)}.role--reviewer{background:var(--c-bg);color:var(--c-text-secondary)}

.pct-row{display:flex;align-items:center;gap:8px}.pct-bar{width:80px;height:6px;background:var(--c-border);border-radius:var(--r-full);overflow:hidden}.pct-fill{height:100%;border-radius:var(--r-full);background:var(--c-info)}.pct-num{font-size:var(--fs-xs);color:var(--c-text-secondary)}

.font-medium{font-weight:var(--fw-medium)}.text-accent{color:var(--c-accent)}
@media(max-width:900px){.stats-grid{grid-template-columns:repeat(2,1fr)}.charts-row{grid-template-columns:1fr}}
</style>
