<template>
  <div class="records-page">
    <!-- 页头 -->
    <div class="page-head">
      <h2>预审记录</h2>
      <div style="display:flex;align-items:center;gap:12px">
        <span v-if="selectedIds.length" class="selected-badge">已选 {{ selectedIds.length }} 条</span>
        <button class="btn-export" @click="handleExport" :disabled="selectedIds.length === 0">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          导出 Excel
        </button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar">
      <select v-model="filters.risk_level" class="filter-select">
        <option value="">全部风险等级</option>
        <option value="高">高风险</option>
        <option value="中">中风险</option>
        <option value="低">低风险</option>
      </select>
      <select v-model="filters.suggestion" class="filter-select">
        <option value="">全部 AI 建议</option>
        <option value="建议开放">建议开放</option>
        <option value="建议人工重点关注">建议人工重点关注</option>
        <option value="建议延期开放或不予开放">建议延期开放或不予开放</option>
      </select>
      <input v-model.number="filters.year_from" type="number" placeholder="起始年度" class="filter-input filter-input--sm" />
      <span class="filter-sep">—</span>
      <input v-model.number="filters.year_to" type="number" placeholder="截止年度" class="filter-input filter-input--sm" />
      <button class="filter-btn" @click="fetchRecords">筛选</button>
    </div>

    <!-- 表格 -->
    <div class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th style="width:40px"><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
            <th>档案编号</th>
            <th>题名</th>
            <th style="width:70px">年度</th>
            <th style="width:100px">归口单位</th>
            <th style="width:160px">风险评分</th>
            <th style="width:70px">等级</th>
            <th style="width:120px">AI 建议</th>
            <th style="width:70px">置信度</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in records" :key="row.archive_id" @click="showDetail(row)" class="clickable">
            <td><input type="checkbox" :checked="selectedIds.includes(row.id)" @click.stop @change="toggleOne(row.id)" /></td>
            <td class="mono">{{ row.archive_id }}</td>
            <td class="title-cell">{{ row.title }}</td>
            <td>{{ row.year }}</td>
            <td>{{ row.department }}</td>
            <td>
              <div class="mini-bar">
                <div class="mini-bar-fill" :class="'mini-bar--' + riskLevelClass(row.risk_level)" :style="{ width: row.risk_score + '%' }"></div>
                <span class="mini-bar-num">{{ row.risk_score }}</span>
              </div>
            </td>
            <td><span class="risk-tag" :class="'risk-tag--' + riskLevelClass(row.risk_level)">{{ row.risk_level }}</span></td>
            <td>{{ row.suggestion }}</td>
            <td>{{ ((row.confidence || 0) * 100).toFixed(0) }}%</td>
          </tr>
        </tbody>
      </table>
      <div v-if="records.length === 0" class="table-empty">暂无预审记录</div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="selected" class="modal-overlay" @click.self="selected = null">
      <div class="modal-card">
        <div class="modal-head">
          <h3>预审详情</h3>
          <button class="modal-close" @click="selected = null">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div class="modal-body">
          <dl class="detail-grid">
            <div><dt>档案编号</dt><dd>{{ selected.archive_id }}</dd></div>
            <div><dt>题名</dt><dd>{{ selected.title }}</dd></div>
            <div><dt>归档年度</dt><dd>{{ selected.year }}</dd></div>
            <div><dt>归口单位</dt><dd>{{ selected.department }}</dd></div>
            <div><dt>风险评分</dt><dd class="text-accent font-semibold">{{ selected.risk_score }}</dd></div>
            <div><dt>风险等级</dt><dd>{{ selected.risk_level }}</dd></div>
            <div class="span-2"><dt>敏感信息</dt><dd>
              <span v-for="(s,i) in (selected.sensitive_items || [])" :key="i" class="tag-sm">{{ s.type }}</span>
              <span v-if="!selected.sensitive_items?.length" class="text-muted">无</span>
            </dd></div>
            <div class="span-2"><dt>AI 建议</dt><dd class="font-semibold">{{ selected.suggestion }}</dd></div>
            <div class="span-2"><dt>建议理由</dt><dd>{{ selected.reason }}</dd></div>
            <div><dt>置信度</dt><dd>{{ ((selected.confidence || 0) * 100).toFixed(0) }}%</dd></div>
            <div><dt>耗时</dt><dd>{{ selected.processing_time_ms || '—' }}ms</dd></div>
          </dl>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { reviewApi } from '@/api'
import { ElMessage } from 'element-plus'

const records = ref<any[]>([])
const selected = ref<any>(null)
const selectedIds = ref<number[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const allSelected = computed(() => records.value.length > 0 && records.value.every(r => selectedIds.value.includes(r.id)))

function toggleAll() {
  if (allSelected.value) { selectedIds.value = [] }
  else { selectedIds.value = records.value.map(r => r.id) }
}
function toggleOne(id: number) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

const filters = ref({
  risk_level: '', suggestion: '', year_from: undefined as number | undefined, year_to: undefined as number | undefined,
})

onMounted(() => fetchRecords())

function riskLevelClass(lvl: string) {
  return { '高': 'high', '中': 'mid', '低': 'low' }[lvl] || 'low'
}
async function fetchRecords() {
  try {
    const res = await reviewApi.listRecords({
      page: page.value, page_size: pageSize.value,
      risk_level: filters.value.risk_level || undefined,
      suggestion: filters.value.suggestion || undefined,
      year_from: filters.value.year_from, year_to: filters.value.year_to,
    })
    records.value = res.data.items || []
    total.value = res.data.total || 0
  } catch { /* ignore */ }
}
async function showDetail(row: any) {
  try {
    const res = await reviewApi.getRecord(row.id)
    selected.value = res.data
  } catch {
    selected.value = row
  }
}
async function handleExport() {
  try {
    const ids = selectedIds.value.length ? selectedIds.value : []
    const res = await reviewApi.export({ archive_ids: ids })
    ElMessage.success(`导出成功: ${res.data.file} (${res.data.count} 条)`)
    selectedIds.value = []
  } catch { ElMessage.error('导出失败') }
}
</script>

<style scoped>
.records-page { max-width: var(--page-max); margin: 0 auto; }
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-head h2 { font-size: var(--fs-xl); font-weight: var(--fw-semibold); margin: 0; }

.btn-export {
  display: flex; align-items: center; gap: 6px;
  height: 36px; padding: 0 18px; border-radius: var(--r-sm);
  border: 1px solid var(--c-border); background: var(--c-surface);
  color: var(--c-text-secondary); font-size: var(--fs-sm); font-weight: var(--fw-medium); cursor: pointer;
  transition: all var(--t-fast);
}
.btn-export:hover { border-color: var(--c-accent); color: var(--c-accent); }
.btn-export:disabled { opacity: 0.4; cursor: not-allowed; }
.selected-badge {
  padding: 2px 12px; border-radius: var(--r-full); font-size: var(--fs-xs);
  background: var(--c-accent-light); color: var(--c-accent); font-weight: var(--fw-semibold);
}

/* 筛选 */
.filter-bar {
  display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
  margin-bottom: 16px; padding: 12px 16px;
  background: var(--c-surface); border-radius: var(--r-md);
  border: 1px solid var(--c-border);
}
.filter-select {
  height: 36px; padding: 0 12px; border: 1px solid var(--c-border);
  border-radius: var(--r-sm); font-size: var(--fs-sm); color: var(--c-text);
  background: var(--c-bg); outline: none; cursor: pointer;
}
.filter-input {
  height: 36px; padding: 0 10px; border: 1px solid var(--c-border);
  border-radius: var(--r-sm); font-size: var(--fs-sm); background: var(--c-bg); outline: none;
  font-family: var(--font);
}
.filter-input--sm { width: 100px; }
.filter-sep { color: var(--c-text-muted); font-size: var(--fs-sm); }
.filter-btn {
  height: 36px; padding: 0 20px; border-radius: var(--r-sm); border: none;
  background: var(--c-accent); color: #fff; font-size: var(--fs-sm);
  font-weight: var(--fw-medium); cursor: pointer; margin-left: auto;
}
.filter-btn:hover { background: var(--c-accent-hover); }

/* 表格 */
.table-card {
  background: var(--c-surface); border-radius: var(--r-lg);
  border: 1px solid var(--c-border); overflow: hidden;
}
.data-table {
  width: 100%; border-collapse: collapse;
}
.data-table th {
  padding: 12px 16px; text-align: left; font-size: var(--fs-xs);
  font-weight: var(--fw-semibold); color: var(--c-text-muted);
  text-transform: uppercase; letter-spacing: 0.5px;
  background: var(--c-bg); border-bottom: 1px solid var(--c-border);
}
.data-table td {
  padding: 12px 16px; font-size: var(--fs-sm); color: var(--c-text);
  border-bottom: 1px solid var(--c-border-light);
}
.data-table tr.clickable { cursor: pointer; transition: background var(--t-fast); }
.data-table tbody tr:hover { background: #F8F9FC; }
.mono { font-family: 'SF Mono', 'Fira Code', monospace; font-size: var(--fs-xs); color: var(--c-text-secondary); }
.title-cell { max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.mini-bar { display: flex; align-items: center; gap: 8px; }
.mini-bar-fill { height: 6px; border-radius: var(--r-full); min-width: 2px; }
.mini-bar--low  { background: var(--c-success); }
.mini-bar--mid  { background: var(--c-warning); }
.mini-bar--high { background: var(--c-danger); }
.mini-bar-num { font-size: var(--fs-xs); font-weight: var(--fw-semibold); color: var(--c-text-secondary); width: 24px; }

.risk-tag {
  padding: 2px 10px; border-radius: var(--r-full);
  font-size: 11px; font-weight: var(--fw-bold); letter-spacing: 0.3px;
}
.risk-tag--low  { background: #F0FDF4; color: var(--c-success); }
.risk-tag--mid  { background: #FFFBEB; color: var(--c-warning); }
.risk-tag--high { background: #FEF2F2; color: var(--c-danger); }

.table-empty { padding: 48px; text-align: center; color: var(--c-text-muted); }

/* 弹窗 */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.3);
  display: flex; align-items: center; justify-content: center; z-index: 100;
  backdrop-filter: blur(4px);
}
.modal-card {
  width: 600px; max-height: 80vh; overflow-y: auto;
  background: var(--c-surface); border-radius: var(--r-lg);
  box-shadow: var(--s-dropdown);
}
.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px; border-bottom: 1px solid var(--c-border-light);
}
.modal-head h3 { margin: 0; font-size: var(--fs-lg); }
.modal-close {
  width: 32px; height: 32px; border-radius: var(--r-sm); border: none;
  background: transparent; cursor: pointer; display: flex; align-items: center; justify-content: center;
  color: var(--c-text-muted); transition: all var(--t-fast);
}
.modal-close:hover { background: var(--c-bg); color: var(--c-text); }
.modal-body { padding: 24px; }
.detail-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px 24px; margin: 0;
}
.detail-grid dt { font-size: var(--fs-xs); color: var(--c-text-muted); font-weight: var(--fw-medium); margin-bottom: 2px; }
.detail-grid dd { font-size: var(--fs-sm); color: var(--c-text); margin: 0; }
.span-2 { grid-column: span 2; }
.tag-sm {
  display: inline-block; padding: 2px 8px; border-radius: var(--r-full);
  background: #FEF2F2; color: var(--c-danger); font-size: 11px; font-weight: var(--fw-medium); margin: 2px;
}
</style>
