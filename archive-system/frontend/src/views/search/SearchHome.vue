<template>
  <div class="search-page">
    <!-- 左侧筛选栏 -->
    <aside class="search-sidebar" v-if="searched">
      <div class="filter-card">
        <div class="filter-title">档案门类</div>
        <div class="filter-tree">
          <div v-for="cat in categoryTree" :key="cat.key" class="ft-node" :class="{active:activeCat===cat.key}" @click="activeCat=cat.key">
            <span>{{ cat.label }}</span>
            <span class="ft-count">{{ cat.count }}</span>
          </div>
        </div>
      </div>
      <div class="filter-card">
        <div class="filter-title">归档年度</div>
        <div class="filter-tree">
          <div v-for="y in yearList" :key="y.year" class="ft-node" :class="{active:activeYear===y.year}" @click="activeYear=y.year">
            <span>{{ y.year }}年</span>
            <span class="ft-count">{{ y.count }}</span>
          </div>
        </div>
      </div>
      <button class="filter-reset" v-if="activeCat||activeYear" @click="activeCat='';activeYear=null;doSearch()">清除筛选</button>
    </aside>

    <!-- 右侧主区域 -->
    <div class="search-main">
    <!-- 搜索区 -->
    <div class="search-hero">
      <div class="search-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="['tab-btn', { active: searchMode === tab.key }]"
          @click="searchMode = tab.key"
        >{{ tab.label }}</button>
      </div>

      <!-- 关键词检索 -->
      <div v-if="searchMode === 'keyword'" class="search-input-row">
        <div class="search-box">
          <svg class="search-box-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          <input
            v-model="keyword"
            placeholder="输入关键词搜索档案..."
            class="search-input"
            @keyup.enter="doSearch"
          />
          <button class="search-btn" @click="doSearch">检索</button>
        </div>
      </div>

      <!-- 语义检索 -->
      <div v-else-if="searchMode === 'semantic'" class="search-input-row">
        <div class="search-box">
          <svg class="search-box-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V22l-4-2-4 2v-7.26A6.98 6.98 0 0 1 5 9a7 7 0 0 1 7-7z"/></svg>
          <input
            v-model="semanticQuery"
            placeholder="用自然语言描述查找内容，如：1996年招生工作相关文件..."
            class="search-input"
            @keyup.enter="doSearch"
          />
          <button class="search-btn search-btn--ai" @click="doSearch">AI 检索</button>
        </div>
      </div>

      <!-- 高级检索 -->
      <div v-else class="advanced-form">
        <div class="adv-row">
          <div class="adv-field">
            <label>关键词</label>
            <input v-model="advancedForm.keywords" placeholder="可选" class="adv-input" />
          </div>
          <div class="adv-field">
            <label>归档年度</label>
            <div class="adv-range">
              <input v-model.number="advancedForm.yearFrom" placeholder="起始" class="adv-input adv-input--sm" type="number" />
              <span class="adv-sep">—</span>
              <input v-model.number="advancedForm.yearTo" placeholder="截止" class="adv-input adv-input--sm" type="number" />
            </div>
          </div>
          <div class="adv-field">
            <label>档案门类</label>
            <select v-model="advancedForm.category" class="adv-select">
              <option value="">全部</option>
              <option value="文书档案">文书档案</option>
              <option value="教学档案">教学档案</option>
              <option value="科研档案">科研档案</option>
              <option value="人事档案">人事档案</option>
            </select>
          </div>
          <div class="adv-field">
            <label>归口单位</label>
            <input v-model="advancedForm.department" placeholder="可选" class="adv-input" />
          </div>
          <button class="search-btn" style="align-self:flex-end" @click="doSearch">高级检索</button>
        </div>
      </div>

      <!-- 检索范围 -->
      <div class="search-scope">
        <span class="scope-label">检索范围</span>
        <div class="scope-options">
          <button
            v-for="lvl in levels"
            :key="lvl.key"
            :class="['scope-btn', { active: searchLevel === lvl.key }]"
            @click="searchLevel = lvl.key"
          >{{ lvl.label }}</button>
        </div>
      </div>
    </div>

    <!-- 结果区 -->
    <div v-if="searched" class="results-area">
      <div class="results-toolbar">
        <div class="results-summary">
          <span class="results-count">{{ total }}</span>
          <span class="results-label">条结果</span>
          <span class="results-time">{{ queryTime }}ms</span>
        </div>
        <div class="results-actions">
          <select v-model="sortBy" class="sort-select">
            <option value="score">相关度排序</option>
            <option value="time_desc">时间倒序</option>
            <option value="time_asc">时间正序</option>
          </select>
          <button class="btn-export" @click="handleExport">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            导出
          </button>
        </div>
      </div>

      <div v-if="loading" class="results-loading">
        <div class="skeleton" v-for="i in 4" :key="i">
          <div class="skeleton-line skeleton-line--title"></div>
          <div class="skeleton-line"></div>
          <div class="skeleton-line skeleton-line--short"></div>
        </div>
      </div>

      <div v-else-if="results.length === 0" class="results-empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <p>未找到匹配的档案</p>
        <span>尝试调整关键词或检索条件</span>
      </div>

      <div v-else class="results-list">
        <div
          v-for="item in results"
          :key="item.archive_id"
          class="result-card"
          @click="goDetail(item.archive_id)"
        >
          <div class="result-card-body">
            <div class="result-card-top">
              <h3 class="result-title" v-html="highlightText(item.title)"></h3>
              <div class="result-badges">
                <span class="badge" :class="'badge--' + (item.risk_level || 'low')">{{ item.risk_level || '低' }}风险</span>
                <span class="badge badge--plain">{{ item.category || '文书档案' }}</span>
              </div>
            </div>
            <p class="result-summary">{{ item.summary || '暂无内容摘要...' }}</p>
            <div class="result-meta">
              <span class="meta-item">{{ item.archive_id }}</span>
              <span class="meta-sep">·</span>
              <span class="meta-item">{{ item.year }}</span>
              <span class="meta-sep">·</span>
              <span class="meta-item">{{ item.department }}</span>
              <span class="meta-score">{{ item.relevance || 85 }}% 匹配</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="total > pageSize" class="results-pager">
        <button class="pager-btn" :disabled="page <= 1" @click="page--; doSearch()">上一页</button>
        <span class="pager-info">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
        <button class="pager-btn" :disabled="page >= Math.ceil(total/pageSize)" @click="page++; doSearch()">下一页</button>
      </div>
    </div>
    </div><!-- /search-main -->
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { searchApi } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()

const tabs = [
  { key: 'keyword', label: '关键词检索' },
  { key: 'semantic', label: '语义检索' },
  { key: 'advanced', label: '高级检索' },
]
const levels = [
  { key: 'all', label: '全部' },
  { key: 'project', label: '项目级' },
  { key: 'box', label: '案卷级' },
  { key: 'file', label: '卷内级' },
]

const searchMode = ref('keyword')
const searchLevel = ref('all')
const activeCat = ref('')
const activeYear = ref<number | null>(null)

const categoryTree = [
  { key: '行政档案', label: '行政档案', count: 45210 },
  { key: '教学档案', label: '教学档案', count: 23100 },
  { key: '党群档案', label: '党群档案', count: 18500 },
  { key: '科研档案', label: '科研档案', count: 12050 },
  { key: '人事档案', label: '人事档案', count: 9800 },
  { key: '财务档案', label: '财务档案', count: 7200 },
  { key: '基建档案', label: '基建档案', count: 3800 },
  { key: '声像档案', label: '声像档案', count: 2100 },
]
const yearList = [
  { year: 2025, count: 12300 }, { year: 2024, count: 11800 }, { year: 2023, count: 10500 },
  { year: 2022, count: 9800 }, { year: 2021, count: 9200 }, { year: 2020, count: 8900 },
  { year: 2010, count: 7500 }, { year: 2000, count: 6800 }, { year: 1990, count: 5200 },
  { year: 1980, count: 3400 }, { year: 1970, count: 2100 },
]
const keyword = ref('')
const semanticQuery = ref('')
const advancedForm = reactive({
  keywords: '', yearFrom: undefined as number | undefined, yearTo: undefined as number | undefined,
  category: '', department: '',
})

const searched = ref(false)
const loading = ref(false)
const results = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const sortBy = ref('score')
const queryTime = ref(0)

async function doSearch() {
  loading.value = true
  searched.value = true
  page.value = 1
  try {
    let res: any
    const common: any = {
      page: page.value, page_size: pageSize.value, level: searchLevel.value,
      category: activeCat.value || undefined, department: undefined,
    }
    if (activeYear.value) {
      common.year_from = activeYear.value
      common.year_to = activeYear.value
    }
    if (searchMode.value === 'semantic') {
      res = await searchApi.semantic({ query: semanticQuery.value, ...common })
    } else if (searchMode.value === 'advanced') {
      res = await searchApi.advanced({ ...advancedForm, category: advancedForm.category || activeCat.value || undefined, ...common })
    } else {
      res = await searchApi.keyword({ keywords: keyword.value, ...common })
    }
    results.value = res.data.results
    total.value = res.data.total
    queryTime.value = res.data.query_time_ms || 0
  } catch {
    results.value = []
    total.value = 0
    ElMessage.error('检索失败')
  } finally {
    loading.value = false
  }
}

// 筛选栏变化自动重新搜索
watch([activeCat, activeYear], () => { if (searched.value) doSearch() })

function highlightText(text: string) {
  if (!keyword.value || !text) return text
  return keyword.value.split(/\s+/).filter(Boolean).reduce((t, w) =>
    t.replace(new RegExp(w, 'gi'), m => `<mark class="search-highlight">${m}</mark>`), text)
}

function goDetail(id: string) { router.push(`/search/detail/${id}`) }
function handleExport() { ElMessage.info('导出任务已提交，请稍后下载') }
</script>

<style scoped>
.search-page { max-width: var(--page-max); margin: 0 auto; display: flex; gap: 20px; align-items: flex-start; }

/* ========== 左侧筛选栏 ========== */
.search-sidebar { width: 220px; flex-shrink: 0; }
.search-main { flex: 1; min-width: 0; }

.filter-card {
  background: var(--c-surface); border-radius: var(--r-md); border: 1px solid var(--c-border);
  padding: 14px; margin-bottom: 12px;
}
.filter-title {
  font-size: var(--fs-sm); font-weight: var(--fw-semibold); color: var(--c-text);
  margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid var(--c-border-light);
}
.filter-tree { display: flex; flex-direction: column; gap: 2px; }
.ft-node {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 10px; border-radius: var(--r-sm); cursor: pointer;
  font-size: var(--fs-sm); color: var(--c-text-secondary);
  transition: all var(--t-fast);
}
.ft-node:hover { background: var(--c-bg); color: var(--c-text); }
.ft-node.active { background: var(--c-accent-light); color: var(--c-accent); font-weight: var(--fw-medium); }
.ft-count {
  font-size: 11px; padding: 1px 6px; border-radius: var(--r-full);
  background: var(--c-bg); color: var(--c-text-muted);
}
.ft-node.active .ft-count { background: var(--c-accent); color: #fff; }

.filter-reset {
  display: block; width: 100%; padding: 6px; border: none; background: transparent;
  color: var(--c-accent); font-size: var(--fs-xs); cursor: pointer;
  border-radius: var(--r-sm); transition: background var(--t-fast);
}
.filter-reset:hover { background: var(--c-accent-light); }

/* ========== 搜索区 ========== */
.search-hero {
  background: var(--c-surface);
  border-radius: var(--r-lg);
  border: 1px solid var(--c-border);
  padding: 24px;
  margin-bottom: 24px;
}

.search-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  background: var(--c-bg);
  border-radius: var(--r-sm);
  padding: 3px;
  width: fit-content;
}
.tab-btn {
  padding: 6px 16px;
  border-radius: var(--r-sm);
  border: none;
  background: transparent;
  color: var(--c-text-secondary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-medium);
  cursor: pointer;
  transition: all var(--t-fast);
}
.tab-btn.active {
  background: var(--c-surface);
  color: var(--c-accent);
  box-shadow: var(--s-card);
}

.search-input-row { margin-bottom: 8px; }
.search-box {
  display: flex;
  align-items: center;
  background: var(--c-bg);
  border-radius: var(--r-md);
  border: 1px solid transparent;
  padding: 4px;
  transition: all var(--t-fast);
}
.search-box:focus-within {
  border-color: var(--c-accent);
  background: var(--c-surface);
  box-shadow: 0 0 0 3px var(--c-accent-light);
}
.search-box-icon {
  margin: 0 12px;
  color: var(--c-text-muted);
  flex-shrink: 0;
}
.search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 15px;
  color: var(--c-text);
  outline: none;
  padding: 10px 0;
  font-family: var(--font);
}
.search-input::placeholder { color: var(--c-text-muted); }
.search-btn {
  height: 40px;
  padding: 0 24px;
  border-radius: var(--r-sm);
  border: none;
  background: var(--c-accent);
  color: #fff;
  font-size: var(--fs-base);
  font-weight: var(--fw-semibold);
  cursor: pointer;
  transition: background var(--t-fast);
  white-space: nowrap;
}
.search-btn:hover { background: var(--c-accent-hover); }
.search-btn--ai {
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
}
.search-btn--ai:hover { background: linear-gradient(135deg, #4F46E5, #7C3AED); }

/* 高级检索 */
.adv-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-end;
}
.adv-field { display: flex; flex-direction: column; gap: 4px; }
.adv-field label {
  font-size: var(--fs-xs);
  font-weight: var(--fw-medium);
  color: var(--c-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.adv-input {
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-sm);
  font-size: var(--fs-base);
  color: var(--c-text);
  background: var(--c-surface);
  outline: none;
  font-family: var(--font);
  min-width: 140px;
}
.adv-input:focus { border-color: var(--c-accent); }
.adv-input--sm { width: 100px; min-width: 80px; }
.adv-select {
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-sm);
  font-size: var(--fs-base);
  color: var(--c-text);
  background: var(--c-surface);
  outline: none;
  cursor: pointer;
}
.adv-range { display: flex; align-items: center; gap: 6px; }
.adv-sep { color: var(--c-text-muted); }

/* 检索范围 */
.search-scope {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--c-border-light);
}
.scope-label {
  font-size: var(--fs-sm);
  color: var(--c-text-muted);
  font-weight: var(--fw-medium);
}
.scope-options { display: flex; gap: 4px; }
.scope-btn {
  padding: 4px 12px;
  border-radius: var(--r-full);
  border: 1px solid var(--c-border);
  background: transparent;
  color: var(--c-text-secondary);
  font-size: var(--fs-xs);
  cursor: pointer;
  transition: all var(--t-fast);
}
.scope-btn.active {
  background: var(--c-accent);
  color: #fff;
  border-color: var(--c-accent);
}

/* ========== 结果区 ========== */
.results-area { animation: fadeIn 0.3s ease; }

@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.results-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.results-summary { display: flex; align-items: baseline; gap: 6px; }
.results-count {
  font-size: var(--fs-2xl);
  font-weight: var(--fw-bold);
  color: var(--c-accent);
}
.results-label { color: var(--c-text-secondary); font-size: var(--fs-base); }
.results-time { color: var(--c-text-muted); font-size: var(--fs-xs); margin-left: 8px; }
.results-actions { display: flex; gap: 8px; align-items: center; }
.sort-select {
  height: 32px;
  padding: 0 8px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-sm);
  font-size: var(--fs-sm);
  color: var(--c-text-secondary);
  background: var(--c-surface);
  outline: none;
  cursor: pointer;
}
.btn-export {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 14px;
  border-radius: var(--r-sm);
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text-secondary);
  font-size: var(--fs-sm);
  cursor: pointer;
  transition: all var(--t-fast);
}
.btn-export:hover { border-color: var(--c-accent); color: var(--c-accent); }

/* 卡片结果 */
.result-card {
  background: var(--c-surface);
  border-radius: var(--r-md);
  border: 1px solid var(--c-border);
  margin-bottom: 8px;
  cursor: pointer;
  transition: all var(--t-fast);
}
.result-card:hover {
  border-color: var(--c-accent);
  box-shadow: var(--s-card-hover);
  transform: translateY(-1px);
}
.result-card-body { padding: 16px 20px; }
.result-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}
.result-title {
  font-size: var(--fs-lg);
  font-weight: var(--fw-semibold);
  color: var(--c-text);
  margin: 0;
  line-height: var(--lh-tight);
  flex: 1;
}
.result-badges { display: flex; gap: 6px; flex-shrink: 0; }
.badge {
  padding: 2px 10px;
  border-radius: var(--r-full);
  font-size: 11px;
  font-weight: var(--fw-semibold);
  letter-spacing: 0.3px;
}
.badge--高 { background: #FEF2F2; color: var(--c-danger); }
.badge--中 { background: #FFFBEB; color: var(--c-warning); }
.badge--低 { background: #F0FDF4; color: var(--c-success); }
.badge--plain { background: var(--c-bg); color: var(--c-text-secondary); }

.result-summary {
  font-size: var(--fs-sm);
  color: var(--c-text-secondary);
  margin: 0 0 10px;
  line-height: var(--lh-normal);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-xs);
  color: var(--c-text-muted);
}
.meta-sep { margin: 0 4px; }
.meta-score {
  margin-left: auto;
  font-weight: var(--fw-semibold);
  color: var(--c-accent);
  background: var(--c-accent-light);
  padding: 2px 8px;
  border-radius: var(--r-full);
}

/* 分页 */
.results-pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
}
.pager-btn {
  height: 36px;
  padding: 0 20px;
  border-radius: var(--r-sm);
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text-secondary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-medium);
  cursor: pointer;
  transition: all var(--t-fast);
}
.pager-btn:hover:not(:disabled) { border-color: var(--c-accent); color: var(--c-accent); }
.pager-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.pager-info { font-size: var(--fs-sm); color: var(--c-text-muted); }

/* 加载骨架 */
.skeleton { padding: 16px 0; }
.skeleton-line {
  height: 12px;
  background: var(--c-border);
  border-radius: var(--r-full);
  margin-bottom: 8px;
  animation: pulse 1.5s ease infinite;
}
.skeleton-line--title { width: 60%; height: 16px; }
.skeleton-line--short { width: 40%; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* 空结果 */
.results-empty {
  text-align: center;
  padding: 64px 0;
  color: var(--c-text-muted);
}
.results-empty p { margin: 12px 0 4px; font-size: var(--fs-lg); font-weight: var(--fw-medium); }
.results-empty span { font-size: var(--fs-sm); }
</style>
