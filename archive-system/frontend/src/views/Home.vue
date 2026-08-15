<template>
  <div class="home">
    <!-- 加载骨架 -->
    <div v-if="stats.loading" class="skeleton-loading">
      <div class="stats-grid"><div v-for="i in 4" :key="i" class="skeleton skeleton--card"></div></div>
      <div class="home-grid"><div v-for="i in 4" :key="i" class="skeleton skeleton--card"></div></div>
    </div>
    <template v-else>
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon stat-icon--green">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
        </div>
        <div class="stat-label">馆藏档案总数</div>
        <div class="stat-value">{{ formatNum(stats.totalArchives) }}</div>
        <div class="stat-trend stat-trend--up">↑ 较上月 +3.2%</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--blue">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
        </div>
        <div class="stat-label">已数字化</div>
        <div class="stat-value">{{ formatNum(stats.digitized) }}</div>
        <div class="stat-trend stat-trend--up">↑ 覆盖率 {{ stats.digitizeRate }}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--purple">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        </div>
        <div class="stat-label">OCR 已处理</div>
        <div class="stat-value">{{ formatNum(stats.ocrProcessed) }}</div>
        <div class="stat-trend stat-trend--up">↑ 准确率 {{ stats.ocrAccuracy }}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--amber">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
        </div>
        <div class="stat-label">待开放审核</div>
        <div class="stat-value">{{ formatNum(stats.pendingReview) }}</div>
        <div class="stat-trend stat-trend--down">↓ 较上月 -8%</div>
      </div>
    </div>

    <!-- 快捷入口 -->
    <div class="home-grid">
      <router-link to="/search" class="quick-card">
        <div class="qc-icon qc-icon--green">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        </div>
        <div class="qc-info"><h3>智能检索</h3><p>关键词 · 语义 · 高级检索</p></div>
      </router-link>
      <router-link to="/review" class="quick-card">
        <div class="qc-icon qc-icon--purple">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
        </div>
        <div class="qc-info"><h3>AI 预审工作台</h3><p>敏感信息检测 · 风险评分</p></div>
      </router-link>
      <router-link to="/ocr" class="quick-card">
        <div class="qc-icon qc-icon--blue">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
        </div>
        <div class="qc-info"><h3>OCR 识别</h3><p>批量文字识别 · 质量报告</p></div>
      </router-link>
      <router-link to="/admin/sync" class="quick-card">
        <div class="qc-icon qc-icon--amber">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
        </div>
        <div class="qc-info"><h3>数据同步</h3><p>文件同步 · 数据库同步</p></div>
      </router-link>
    </div>

    <!-- 图表行 -->
    <div class="charts-row">
      <div class="chart-card">
        <h3>档案数字化进度</h3>
        <div ref="digitizeChartRef" class="chart-sm"></div>
      </div>
      <div class="chart-card">
        <h3>检索趋势（近7日）</h3>
        <div ref="trendChartRef" class="chart-sm"></div>
      </div>
    </div>

    <!-- OCR + 预审 -->
    <div class="home-cols">
      <div class="col-card">
        <h3>OCR任务处理概况</h3>
        <table class="mini-table">
          <thead><tr><th>任务名称</th><th>进度</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="t in ocrOverview" :key="t.name">
              <td class="ellipsis">{{ t.name }}</td>
              <td><div class="mini-bar"><div class="mini-bar-fill" :style="{width:t.pct+'%',background:t.status==='done'?'var(--c-success)':'var(--c-info)'}"></div><span class="mini-bar-num">{{ t.pct }}%</span></div></td>
              <td><span class="risk-tag" :class="'risk-tag--'+(t.status==='done'?'low':'mid')">{{ t.status==='done'?'已完成':'处理中' }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="col-card">
        <h3>AI预审任务进度</h3>
        <div class="timeline-list">
          <div v-for="(item, i) in reviewTimeline" :key="i" class="tl-item">
            <div class="tl-dot" :class="'tl--'+item.status"></div>
            <div class="tl-content">
              <div class="tl-title">{{ item.title }}</div>
              <div class="tl-meta">{{ item.desc }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 最近活动 -->
    <div class="recent-section">
      <h3>最近活动</h3>
      <div class="recent-list">
        <div v-for="(item, i) in recentActivities" :key="i" class="recent-item">
          <div class="recent-dot" :class="'recent-dot--' + item.type"></div>
          <div class="recent-content">
            <span class="recent-desc">{{ item.desc }}</span>
            <span class="recent-time">{{ item.time }}</span>
          </div>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, onUnmounted, nextTick } from 'vue'
import { searchApi, statsApi, logApi, reviewApi, ocrApi } from '@/api'
import * as echarts from 'echarts'

const digitizeChartRef = ref<HTMLElement>()
const trendChartRef = ref<HTMLElement>()
const charts: any[] = []

const stats = reactive({
  totalArchives: 0,
  digitized: 0,
  digitizeRate: 0,
  ocrProcessed: 0,
  ocrAccuracy: 0,
  pendingReview: 0,
  loading: true,
})

const recentActivities = ref<{type:string;desc:string;time:string}[]>([])
const ocrOverview = ref<{name:string;pct:number;status:string}[]>([])
const reviewTimeline = ref<{title:string;desc:string;status:string}[]>([])
const trendData = ref<number[]>([])

onMounted(async () => {
  // 并行加载首页数据
  try {
    const [facetsR, typeR, reviewR, ocrR, qualityR, timeR] = await Promise.allSettled([
      searchApi.facets(),
      statsApi.byType({}),
      reviewApi.listTasks({ page: 1, page_size: 5 }),
      ocrApi.listTasks({ page: 1, page_size: 5 }),
      ocrApi.qualityReport({}),
      statsApi.byTime({ granularity: 'day', days: 7 }),
    ])

    // 馆藏总数 = facets 各门类计数之和
    if (facetsR.status === 'fulfilled') {
      const cats = facetsR.value.data.categories || []
      stats.totalArchives = cats.reduce((s: number, c: any) => s + (c.count || 0), 0)
    }

    // 操作统计
    if (typeR.status === 'fulfilled') {
      const items = typeR.value.data.items || []
      stats.digitized = stats.totalArchives || items.reduce((s: number, i: any) => s + (i.count || 0), 0)
    }

    // 预审任务
    if (reviewR.status === 'fulfilled') {
      const tasks = reviewR.value.data.items || []
      const metrics = reviewR.value.data.metrics || {}
      stats.pendingReview = metrics.total_reviewed || tasks.reduce((s: number, t: any) => s + (t.completed_count || 0), 0)
      reviewTimeline.value = tasks.slice(0, 3).map((t: any) => ({
        title: t.task_name,
        desc: `${t.completed_count || 0}/${t.total_count || 0} 件${t.status === 'completed' ? ' 已完成' : ''}`,
        status: t.status === 'completed' ? 'done' : t.status === 'running' ? 'active' : 'pending',
      }))
    }

    // OCR 任务
    if (ocrR.status === 'fulfilled') {
      const ocrTasks = ocrR.value.data.items || []
      stats.ocrProcessed = ocrTasks.reduce((s: number, t: any) => s + (t.processed_pages || 0), 0)
      ocrOverview.value = ocrTasks.slice(0, 5).map((t: any) => ({
        name: t.task_name,
        pct: t.total_pages ? Math.round(t.processed_pages / t.total_pages * 100) : 0,
        status: t.status === 'completed' ? 'done' : 'processing',
      }))
    }

    // OCR 准确率来自质量报告；数字化覆盖率按实际数据计算
    if (qualityR.status === 'fulfilled') {
      stats.ocrAccuracy = Math.round((qualityR.value.data.overall_accuracy || 0) * 100)
    }
    stats.digitizeRate = stats.totalArchives ? Math.round(stats.digitized / stats.totalArchives * 100) : 0

    // 检索趋势来自 by-time 统计（近 7 日）
    if (timeR.status === 'fulfilled') {
      const items = timeR.value.data.items || []
      trendData.value = items.slice(-7).map((it: any) => it.search || 0)
    }
  } catch { /* keep defaults */ }
  stats.loading = false

  // 最近活动从日志获取
  try {
    const logs = await logApi.list({ page: 1, page_size: 5 })
    if (logs.data.items?.length) {
      recentActivities.value = logs.data.items.map((l: any) => ({
        type: l.operation_type || 'system',
        desc: l.description || l.operation_type,
        time: l.created_at?.substring(11, 19) || '',
      }))
    }
  } catch {
    recentActivities.value = []
  }

  await nextTick()
  // 数字化进度饼图
  if (digitizeChartRef.value) {
    const c = echarts.init(digitizeChartRef.value)
    charts.push(c)
    c.setOption({
      tooltip: { trigger: 'item' },
      series: [{ type: 'pie', radius: ['50%', '75%'], center: ['50%', '50%'], itemStyle: { borderRadius: 2, borderColor: '#fff', borderWidth: 2 }, label: { show: false },
        data: [{ value: stats.digitized, name: '已数字化' }, { value: stats.totalArchives - stats.digitized, name: '待数字化' }],
        color: ['#10B981', '#E2E8F0'] }]
    })
  }
  // 检索趋势柱状图
  if (trendChartRef.value) {
    const c = echarts.init(trendChartRef.value)
    charts.push(c)
    const days = ['6天前','5天前','4天前','3天前','前天','昨天','今天']
    c.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 10, right: 10, top: 10, bottom: 20 },
      xAxis: { type: 'category', data: days, axisLabel: { fontSize: 9, rotate: 30 }, axisTick: { show: false }, axisLine: { show: false } },
      yAxis: { type: 'value', axisLabel: { fontSize: 9 }, splitLine: { lineStyle: { color: '#F1F5F9' } } },
      series: [{ type: 'bar', data: trendData.value.length ? trendData.value : [0, 0, 0, 0, 0, 0, 0], barWidth: 12, itemStyle: { borderRadius: [4, 4, 0, 0], color: '#10B981' } }]
    })
  }
})

onUnmounted(() => {
  charts.forEach(c => { try { c.dispose() } catch {} })
})

function formatNum(n: number): string {
  return n.toLocaleString('zh-CN')
}
</script>

<style scoped>
.home { max-width: var(--page-max); margin: 0 auto; }

/* 快捷入口 */
.home-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;
}
.quick-card {
  background: var(--c-surface); border-radius: var(--r-lg);
  border: 1px solid var(--c-border); padding: 20px;
  display: flex; align-items: center; gap: 14px;
  text-decoration: none; cursor: pointer;
  transition: all var(--t-fast);
}
.quick-card:hover { box-shadow: var(--s-card-hover); transform: translateY(-2px); }
.qc-icon {
  width: 48px; height: 48px; border-radius: var(--r-md);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.qc-icon--green { background: var(--c-accent-light); color: var(--c-accent); }
.qc-icon--purple { background: #F3E8FF; color: var(--c-purple); }
.qc-icon--amber { background: #FEF3C7; color: var(--c-warning); }
.qc-icon--blue { background: #E0F2FE; color: var(--c-info); }
.qc-info h3 { font-size: var(--fs-base); font-weight: var(--fw-semibold); color: var(--c-text); margin: 0 0 2px; }
.qc-info p { font-size: var(--fs-xs); color: var(--c-text-muted); margin: 0; }

/* 最近活动 */
.recent-section {
  background: var(--c-surface); border-radius: var(--r-lg);
  border: 1px solid var(--c-border); padding: 20px;
}
.recent-section h3 {
  font-size: var(--fs-base); font-weight: var(--fw-semibold);
  color: var(--c-text); margin: 0 0 16px; padding-bottom: 12px;
  border-bottom: 1px solid var(--c-border-light);
}
.recent-item { display: flex; gap: 12px; padding: 10px 0; align-items: flex-start; }
.recent-item + .recent-item { border-top: 1px solid var(--c-border-light); }
.recent-dot {
  width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; flex-shrink: 0;
}
.recent-dot--search { background: var(--c-accent); }
.recent-dot--review { background: var(--c-purple); }
.recent-dot--ocr { background: var(--c-info); }
.recent-dot--system { background: var(--c-warning); }
.recent-dot--login { background: var(--c-text-muted); }
.recent-content { display: flex; flex-direction: column; }
.recent-desc { font-size: var(--fs-sm); color: var(--c-text); }
.recent-time { font-size: var(--fs-xs); color: var(--c-text-muted); margin-top: 2px; }

@media (max-width:900px){.home-grid{grid-template-columns:repeat(2,1fr)}}
@media (max-width:500px){.home-grid{grid-template-columns:1fr}}

/* 图表 */
.charts-row{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px}
.chart-card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);padding:16px}
.chart-card h3{font-size:var(--fs-sm);font-weight:var(--fw-semibold);margin:0 0 12px}
.chart-sm{height:180px}

/* OCR+预审 双栏 */
.home-cols{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px}
.col-card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);padding:16px}
.col-card h3{font-size:var(--fs-sm);font-weight:var(--fw-semibold);margin:0 0 12px;padding-bottom:8px;border-bottom:1px solid var(--c-border-light)}
.mini-table{width:100%;border-collapse:collapse}
.mini-table th{padding:6px 10px;text-align:left;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted)}
.mini-table td{padding:6px 10px;font-size:var(--fs-xs);color:var(--c-text);border-bottom:1px solid var(--c-border-light)}
.ellipsis{max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* 时间线 */
.timeline-list{display:flex;flex-direction:column;gap:8px}
.tl-item{display:flex;gap:10px;align-items:flex-start}
.tl-dot{width:8px;height:8px;border-radius:50%;margin-top:4px;flex-shrink:0}
.tl--done{background:var(--c-success)}.tl--pending{background:var(--c-warning)}.tl--active{background:var(--c-info)}
.tl-title{font-size:var(--fs-xs);font-weight:var(--fw-medium);color:var(--c-text)}
.tl-meta{font-size:11px;color:var(--c-text-muted);margin-top:2px}

.risk-tag{padding:2px 8px;border-radius:var(--r-full);font-size:10px;font-weight:var(--fw-bold)}.risk-tag--low{background:#F0FDF4;color:var(--c-success)}.risk-tag--mid{background:#FFFBEB;color:var(--c-warning)}
</style>
