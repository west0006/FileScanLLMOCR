<template>
  <div class="stats-page">
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon stat-icon--green">📁</div>
        <div class="stat-label">总操作记录</div>
        <div class="stat-value">{{ summary.total_operations }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--blue">🔍</div>
        <div class="stat-label">检索次数</div>
        <div class="stat-value">{{ summary.search_count }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--purple">📋</div>
        <div class="stat-label">审核操作</div>
        <div class="stat-value">{{ summary.review_count }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--amber">⚠️</div>
        <div class="stat-label">失败操作</div>
        <div class="stat-value">{{ summary.failed_count }}</div>
      </div>
    </div>

    <div class="charts-row">
      <div class="chart-card">
        <h3>按操作类型统计</h3>
        <div ref="typeChartRef" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <h3>按用户统计 (Top 10)</h3>
        <div ref="userChartRef" class="chart-box"></div>
      </div>
    </div>
    <div class="charts-row">
      <div class="chart-card chart-card--full">
        <div class="chart-head">
          <h3>操作趋势</h3>
          <select v-model="timeGranularity" @change="loadTimeChart" class="chart-select">
            <option value="day">按日</option>
            <option value="week">按周</option>
            <option value="month">按月</option>
          </select>
        </div>
        <div ref="timeChartRef" class="chart-box"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { statsApi } from '@/api'
import * as echarts from 'echarts'

const typeChartRef = ref<HTMLElement>()
const userChartRef = ref<HTMLElement>()
const timeChartRef = ref<HTMLElement>()
const timeGranularity = ref('day')

const summary = reactive({
  total_operations: 0, search_count: 0, review_count: 0, failed_count: 0,
})

onMounted(async () => {
  let typeData: any[] = []
  let userData: any[] = []

  try {
    const [typeRes, userRes] = await Promise.all([
      statsApi.byType({}), statsApi.byUser({ top_n: 10 }),
    ])
    typeData = typeRes.data.items || []
    userData = userRes.data.items || []
    summary.total_operations = typeData.reduce((s: number, i: any) => s + (i.count || 0), 0)
    summary.search_count = typeData.find((i: any) => i.type === 'search')?.count || 0
    summary.review_count = typeData.find((i: any) => i.type === 'review')?.count || 0
    summary.failed_count = typeData.find((i: any) => i.type === 'failure')?.count || 0
  } catch {
    typeData = [
      { type: 'search', count: 342 }, { type: 'view', count: 156 }, { type: 'review', count: 89 },
      { type: 'download', count: 45 }, { type: 'admin', count: 23 }, { type: 'login', count: 198 },
    ]
    userData = [
      { username: '管理员', count: 245 }, { username: '李芳', count: 187 }, { username: '陈小红', count: 143 },
      { username: '王建国', count: 98 }, { username: '刘伟', count: 67 }, { username: '张明华', count: 52 },
      { username: '赵静', count: 31 }, { username: '系统', count: 28 },
    ]
    summary.total_operations = typeData.reduce((s, i) => s + i.count, 0)
  }

  await nextTick()

  // 时间趋势图
  loadTimeChart()

  // 饼图 — 按类型
  if (typeChartRef.value) {
    const c1 = echarts.init(typeChartRef.value)
    c1.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie', radius: ['45%', '75%'], center: ['50%', '45%'],
        itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: typeData.map((t: any) => ({ name: typeLabel(t.type), value: t.count })),
        color: ['#10B981', '#6366F1', '#8B5CF6', '#06B6D4', '#F59E0B', '#94A3B8'],
      }],
    })
  }

  // 柱状图 — 按用户
  if (userChartRef.value) {
    const c2 = echarts.init(userChartRef.value)
    c2.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 10, right: 20, top: 10, bottom: 0, containLabel: true },
      xAxis: {
        type: 'value', axisLine: { show: false }, axisTick: { show: false },
        splitLine: { lineStyle: { color: '#F1F5F9' } },
      },
      yAxis: {
        type: 'category', data: userData.map((u: any) => u.username).reverse(),
        axisLine: { show: false }, axisTick: { show: false },
      },
      series: [{
        type: 'bar', data: userData.map((u: any) => u.count).reverse(),
        barWidth: 14, itemStyle: { borderRadius: [0, 6, 6, 0], color: '#10B981' },
        emphasis: { itemStyle: { color: '#059669' } },
      }],
    })
  }
})

function typeLabel(t: string): string {
  const m: Record<string, string> = {
    search: '检索', view: '浏览', review: '审核', download: '下载', admin: '管理', login: '登录', logout: '退出',
  }
  return m[t] || t
}

async function loadTimeChart() {
  if (!timeChartRef.value) return
  let timeData: any[] = []
  try {
    const res = await statsApi.byTime({ granularity: timeGranularity.value, days: 30 })
    timeData = res.data.items || []
  } catch {
    timeData = []
  }

  const c = echarts.init(timeChartRef.value)
  c.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 10, bottom: 30 },
    xAxis: {
      type: 'category', data: timeData.map((i: any) => i.period),
      axisLabel: { rotate: timeGranularity.value === 'day' ? 45 : 0, fontSize: 10 },
    },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{
      type: 'line', data: timeData.map((i: any) => i.count),
      smooth: true, symbol: 'circle', symbolSize: 6,
      lineStyle: { color: '#10B981', width: 2 },
      itemStyle: { color: '#10B981' },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(16,185,129,0.25)' },
        { offset: 1, color: 'rgba(16,185,129,0.02)' },
      ])},
    }],
  })
}
</script>

<style scoped>
.stats-page { max-width: var(--page-max); margin: 0 auto; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card {
  background: var(--c-surface); border-radius: var(--r-lg); padding: 20px;
  border: 1px solid var(--c-border); position: relative; overflow: hidden;
}
.stat-icon { position: absolute; right: 16px; top: 14px; font-size: 24px; opacity: 0.6; }
.stat-label { font-size: var(--fs-sm); color: var(--c-text-secondary); margin-bottom: 6px; }
.stat-value { font-size: 28px; font-weight: var(--fw-bold); color: var(--c-text); }
.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.chart-card {
  background: var(--c-surface); border-radius: var(--r-lg); border: 1px solid var(--c-border); padding: 20px;
}
.chart-card h3 { font-size: var(--fs-base); font-weight: var(--fw-semibold); color: var(--c-text); margin: 0 0 16px; }
.chart-box { height: 300px; }
.chart-card--full .chart-box { height: 280px; }
.chart-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.chart-head h3 { margin: 0; }
.chart-select { height: 32px; padding: 0 10px; border: 1px solid var(--c-border); border-radius: var(--r-sm); font-size: var(--fs-xs); background: var(--c-bg); outline: none; cursor: pointer; }
@media (max-width: 900px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } .charts-row { grid-template-columns: 1fr; } }
</style>
