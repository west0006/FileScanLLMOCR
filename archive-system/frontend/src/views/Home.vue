<template>
  <div class="home">
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
        <div class="qc-info">
          <h3>智能检索</h3>
          <p>关键词 · 语义 · 高级检索</p>
        </div>
      </router-link>
      <router-link to="/review" class="quick-card">
        <div class="qc-icon qc-icon--purple">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
        </div>
        <div class="qc-info">
          <h3>AI 预审工作台</h3>
          <p>敏感信息检测 · 风险评分</p>
        </div>
      </router-link>
      <router-link to="/review/tasks" class="quick-card">
        <div class="qc-icon qc-icon--amber">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/></svg>
        </div>
        <div class="qc-info">
          <h3>预审任务</h3>
          <p>批量审核 · 进度跟踪</p>
        </div>
      </router-link>
      <router-link to="/ocr" class="quick-card">
        <div class="qc-icon qc-icon--blue">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
        </div>
        <div class="qc-info">
          <h3>OCR 识别</h3>
          <p>批量文字识别 · 质量报告</p>
        </div>
      </router-link>
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
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { statsApi, logApi } from '@/api'

const stats = reactive({
  totalArchives: 125830,
  digitized: 89456,
  digitizeRate: 71.1,
  ocrProcessed: 67234,
  ocrAccuracy: 94.6,
  pendingReview: 2341,
})

const recentActivities = ref([
  { type: 'search', desc: '用户"管理员"检索了关键词"招生 1996"', time: '2 分钟前' },
  { type: 'review', desc: 'AI 预审任务 REV-2026-001 完成 560 件', time: '15 分钟前' },
  { type: 'ocr', desc: 'OCR 任务"历史档案补录"处理完成 2400 页', time: '1 小时前' },
  { type: 'system', desc: '文件增量同步完成，新增 125 个文件', time: '2 小时前' },
  { type: 'login', desc: '用户"审核员李芳"登录系统', time: '3 小时前' },
])

onMounted(async () => {
  try {
    const [userRes, typeRes] = await Promise.all([
      statsApi.byUser({}),
      statsApi.byType({}),
    ])
    const total = userRes.data.items?.reduce((s: number, i: any) => s + (i.count || 0), 0) || 0
    if (total > 0) {
      stats.totalArchives = total
    }
  } catch {
    // 后端不可用时保持静态数据
  }
  try {
    const logs = await logApi.list({ page: 1, page_size: 5 })
    if (logs.data.items?.length) {
      recentActivities.value = logs.data.items.map((l: any) => ({
        type: l.operation_type || 'system',
        desc: l.description || l.operation_type,
        time: l.created_at?.substring(11, 19) || '',
      }))
    }
  } catch { /* ignore */ }
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
</style>
