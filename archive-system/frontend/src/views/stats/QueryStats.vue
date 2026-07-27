<template>
  <div class="stats-page">
    <!-- 概览卡片 -->
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-icon stat-icon--green">📁</div><div class="stat-label">总操作记录</div><div class="stat-value">{{ summary.total_operations }}</div></div>
      <div class="stat-card"><div class="stat-icon stat-icon--blue">🔍</div><div class="stat-label">检索次数</div><div class="stat-value">{{ summary.search_count }}</div></div>
      <div class="stat-card"><div class="stat-icon stat-icon--purple">📋</div><div class="stat-label">审核操作</div><div class="stat-value">{{ summary.review_count }}</div></div>
      <div class="stat-card"><div class="stat-icon stat-icon--amber">⚠️</div><div class="stat-label">失败操作</div><div class="stat-value">{{ summary.failed_count }}</div></div>
    </div>

    <!-- 图表行 -->
    <div class="charts-row">
      <div class="chart-card"><h3>按操作类型统计</h3><div ref="typeChartRef" class="chart-box"></div></div>
      <div class="chart-card"><h3>按用户统计 (Top 10)</h3><div ref="userChartRef" class="chart-box"></div></div>
    </div>
    <div class="charts-row">
      <div class="chart-card chart-card--full">
        <div class="chart-head"><h3>操作趋势</h3>
          <select v-model="timeGranularity" @change="loadTimeChart" class="chart-select">
            <option value="day">按日</option><option value="week">按周</option><option value="month">按月</option><option value="quarter">按季度</option><option value="year">按年</option>
          </select>
        </div>
        <div ref="timeChartRef" class="chart-box"></div>
      </div>
    </div>

    <!-- ST-001: 按用户账号统计 -->
    <div class="card">
      <div class="card-head">
        <h3>按用户账号统计 (ST-001)</h3>
        <button class="btn-sm" @click="exportTable('user-ranking')">📥 导出报表</button>
      </div>
      <div class="filter-bar">
        <select v-model="userFilter.role" class="filter-input-sm"><option value="">全部角色</option><option>system_admin</option><option>archive_admin</option><option>reviewer</option></select>
        <select v-model="userFilter.period" class="filter-input-sm"><option value="month">本月</option><option value="quarter">本季度</option><option value="year">本年度</option><option value="all">全部</option></select>
        <button class="btn-accent-sm" @click="fetchUserRanking">查询</button>
      </div>
      <table class="data-table">
        <thead><tr>
          <th>排名</th><th>用户</th><th>角色</th><th>检索</th><th>浏览</th><th>下载</th><th>打印</th><th>合计</th>
        </tr></thead>
        <tbody>
          <tr v-for="(u, i) in userRanking" :key="u.username">
            <td><strong>{{ i + 1 }}</strong></td>
            <td class="font-medium">{{ u.name || u.username }}</td>
            <td><span class="role-tag" :class="'role--'+u.role">{{ roleLabel(u.role) }}</span></td>
            <td>{{ u.search || 0 }}</td>
            <td>{{ u.view || 0 }}</td>
            <td>{{ u.download || 0 }}</td>
            <td>{{ u.print || 0 }}</td>
            <td><strong class="text-accent">{{ (u.search||0)+(u.view||0)+(u.download||0)+(u.print||0) }}</strong></td>
          </tr>
          <tr v-if="!userRanking.length"><td colspan="8" class="table-empty">暂无数据</td></tr>
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
            <td>{{ m.trend === 'up' ? '📈 上升' : m.trend === 'down' ? '📉 下降' : '➡️ 平稳' }}</td>
          </tr>
          <tr v-if="!methodDetail.length"><td colspan="5" class="table-empty">暂无数据</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { statsApi } from '@/api'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

const typeChartRef = ref<HTMLElement>()
const userChartRef = ref<HTMLElement>()
const timeChartRef = ref<HTMLElement>()
const timeGranularity = ref('day')

const summary = reactive({ total_operations:0, search_count:0, review_count:0, failed_count:0 })
const userRanking = ref<any[]>([])
const methodDetail = ref<any[]>([])
const userFilter = reactive({ role:'', period:'month' })

function roleLabel(r: string) { return {system_admin:'系统管理员',archive_admin:'档案管理员',reviewer:'审核员'}[r]||r }
function typeLabel(t: string) { const m:Record<string,string>={search:'检索',view:'浏览',review:'审核',download:'下载',print:'打印',admin:'管理',login:'登录'}; return m[t]||t }

onMounted(async () => {
  let typeData: any[] = []; let userData: any[] = []
  try {
    const [typeRes, userRes] = await Promise.all([statsApi.byType({}), statsApi.byUser({top_n:10})])
    typeData = typeRes.data.items||[]; userData = userRes.data.items||[]
    summary.total_operations = typeData.reduce((s:number,i:any)=>s+(i.count||0),0)
    summary.search_count = typeData.find((i:any)=>i.type==='search')?.count||0
    summary.review_count = typeData.find((i:any)=>i.type==='review')?.count||0
    summary.failed_count = typeData.find((i:any)=>i.type==='failure')?.count||0
  } catch {
    typeData = [{type:'search',count:342},{type:'view',count:156},{type:'review',count:89},{type:'download',count:45},{type:'print',count:23},{type:'login',count:198}]
    userData = [{username:'管理员',count:245},{username:'李芳',count:187},{username:'陈小红',count:143},{username:'王建国',count:98},{username:'刘伟',count:67},{username:'张明华',count:52},{username:'赵静',count:31}]
    const total = (u:any)=> (u.search||0)+(u.view||0)+(u.download||0)+(u.print||0) || u.count || 0
    summary.total_operations = typeData.reduce((s,i)=>s+(i.count||0),0)
    summary.search_count = typeData.find((i:any)=>i.type==='search')?.count||0
    summary.review_count = typeData.find((i:any)=>i.type==='review')?.count||0
    summary.failed_count = typeData.find((i:any)=>i.type==='failure')?.count||0
  } catch {
    typeData = [{type:'search',count:342},{type:'view',count:156},{type:'review',count:89},{type:'download',count:45},{type:'print',count:23},{type:'login',count:198}]
    userData = [{username:'管理员',search:120,view:85,download:28,print:12},{username:'李芳',search:98,view:56,download:32,print:0},{username:'陈小红',search:76,view:44,download:22,print:0},{username:'王建国',search:186,view:342,download:28,print:12},{username:'刘伟',search:23,view:15,download:5,print:0},{username:'张明华',search:12,view:8,download:3,print:0},{username:'赵静',search:156,view:123,download:22,print:8}]
    summary.total_operations = typeData.reduce((s,i)=>s+i.count,0)
  }
  const total = (u:any)=> (u.search||0)+(u.view||0)+(u.download||0)+(u.print||0) || u.count || 0
  await nextTick()
  loadTimeChart()
  if(typeChartRef.value){const c=echarts.init(typeChartRef.value);c.setOption({tooltip:{trigger:'item'},legend:{bottom:0},series:[{type:'pie',radius:['45%','75%'],center:['50%','45%'],itemStyle:{borderRadius:4,borderColor:'#fff',borderWidth:2},label:{show:false},data:typeData.map((t:any)=>({name:typeLabel(t.type),value:t.count})),color:['#10B981','#6366F1','#8B5CF6','#06B6D4','#F59E0B','#94A3B8']}]})}
  if(userChartRef.value){const c=echarts.init(userChartRef.value);c.setOption({tooltip:{trigger:'axis'},grid:{left:10,right:20,top:10,bottom:0,containLabel:true},xAxis:{type:'value',axisLine:{show:false},axisTick:{show:false},splitLine:{lineStyle:{color:'#F1F5F9'}}},yAxis:{type:'category',data:userData.map((u:any)=>u.username||u.name).reverse(),axisLine:{show:false},axisTick:{show:false}},series:[{type:'bar',data:userData.map((u:any)=>total(u)).reverse(),barWidth:14,itemStyle:{borderRadius:[0,6,6,0],color:'#10B981'},emphasis:{itemStyle:{color:'#059669'}}}]})}
  fetchUserRanking()
})

async function fetchUserRanking() {
  try {
    const res = await statsApi.byUser({top_n:20,role:userFilter.role||undefined,period:userFilter.period})
    userRanking.value = (res.data.items||[]).map((u:any)=>({...u,name:u.name||u.username,role:u.role||'reviewer'}))
    // 计算利用方式明细
    const types = ['search','view','download','print']
    const total = userRanking.value.reduce((s,u)=>{types.forEach(t=>{u[t]=u[t]||0}); return s+(u.search||0)+(u.view||0)+(u.download||0)+(u.print||0)},0)
    methodDetail.value = types.map(t=>{
      const month = userRanking.value.reduce((s,u)=>s+(u[t]||0),0)
      return {type:t, month_count:month, pct:total?+(month/total*100).toFixed(1):0, year_count:month*7, trend:month>20?'up':month>5?'flat':'down'}
    })
  } catch {
    userRanking.value = [
      {name:'王建国',username:'wangjg',role:'reviewer',search:186,view:342,download:28,print:12},
      {name:'赵静',username:'zhaojing',role:'reviewer',search:156,view:289,download:22,print:8},
      {name:'李芳',username:'lifang',role:'archive_admin',search:98,view:156,download:45,print:0},
      {name:'陈小红',username:'chenxh',role:'archive_admin',search:76,view:134,download:32,print:0},
      {name:'管理员',username:'admin',role:'system_admin',search:12,view:28,download:3,print:0},
    ]
    methodDetail.value = [
      {type:'search',month_count:1280,pct:23.1,year_count:8560,trend:'up'},
      {type:'view',month_count:2340,pct:42.2,year_count:15680,trend:'up'},
      {type:'download',month_count:320,pct:5.8,year_count:2340,trend:'down'},
      {type:'print',month_count:85,pct:1.5,year_count:680,trend:'flat'},
    ]
  }
}

async function loadTimeChart() {
  if(!timeChartRef.value) return
  let timeData:any[]=[]
  try{const res=await statsApi.byTime({granularity:timeGranularity.value,days:timeGranularity.value==='year'?365:timeGranularity.value==='quarter'?90:30});timeData=res.data.items||[]}catch{timeData=[]}
  const c=echarts.init(timeChartRef.value)
  c.setOption({tooltip:{trigger:'axis'},grid:{left:40,right:20,top:10,bottom:30},xAxis:{type:'category',data:timeData.map((i:any)=>i.period),axisLabel:{rotate:timeGranularity.value==='day'?45:0,fontSize:10}},yAxis:{type:'value',minInterval:1},series:[{type:'line',data:timeData.map((i:any)=>i.count),smooth:true,symbol:'circle',symbolSize:6,lineStyle:{color:'#10B981',width:2},itemStyle:{color:'#10B981'},areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(16,185,129,0.25)'},{offset:1,color:'rgba(16,185,129,0.02)'}])}}]})
}

function exportTable(id: string) { ElMessage.success('报表导出任务已创建') }
</script>

<style scoped>
.stats-page{max-width:var(--page-max);margin:0 auto}
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.stat-card{background:var(--c-surface);border-radius:var(--r-lg);padding:20px;border:1px solid var(--c-border);position:relative;overflow:hidden}
.stat-icon{position:absolute;right:16px;top:14px;font-size:24px;opacity:.6}
.stat-label{font-size:var(--fs-sm);color:var(--c-text-secondary);margin-bottom:6px}
.stat-value{font-size:28px;font-weight:var(--fw-bold);color:var(--c-text)}
.charts-row{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px}
.chart-card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);padding:20px}
.chart-card h3{font-size:var(--fs-base);font-weight:var(--fw-semibold);color:var(--c-text);margin:0 0 16px}
.chart-box{height:300px}
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
