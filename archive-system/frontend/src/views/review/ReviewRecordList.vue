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

    <div class="process-banner">📌 以下为AI预审完成的档案记录。可按风险等级、AI建议、年度范围进行筛选。<strong>建议优先查看高风险档案</strong>，通过导出功能批量获取预审结果表格。</div>

    <!-- 视图切换 -->
    <div class="view-toggle">
      <button :class="['toggle-btn', { active: reviewView === 'item' }]" @click="reviewView = 'item'">📄 按件展示</button>
      <button :class="['toggle-btn', { active: reviewView === 'volume' }]" @click="reviewView = 'volume'">📁 按卷展示</button>
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
        <option value="建议部分开放（脱敏后）">建议部分开放（脱敏后）</option>
        <option value="建议延期开放">建议延期开放</option>
        <option value="建议不开放">建议不开放</option>
      </select>
      <input v-model.number="filters.year_from" type="number" placeholder="起始年度" class="filter-input filter-input--sm" />
      <span class="filter-sep">—</span>
      <input v-model.number="filters.year_to" type="number" placeholder="截止年度" class="filter-input filter-input--sm" />
      <button class="filter-btn" @click="fetchRecords">筛选</button>
      <button class="filter-btn-reset" @click="resetFilters">重置</button>
    </div>

    <!-- 按件展示 — 按部门分组 -->
    <template v-if="reviewView === 'item'">
      <div class="table-card" v-for="group in groupedRecords" :key="group.dept">
        <div class="dept-header">
          <span class="dept-name">{{ group.dept || '未分类' }}</span>
          <span class="dept-count">{{ group.items.length }} 件</span>
        </div>
        <table class="data-table">
          <thead><tr>
            <th style="width:36px"><input type="checkbox" :checked="group.allSelected" @change="toggleGroup(group)" /></th>
            <th>档案编号</th><th>题名</th><th style="width:100px">所属案卷</th>
            <th style="width:60px">年度</th><th style="width:140px">风险评分</th>
            <th style="width:60px">等级</th><th style="width:120px">AI 建议</th>
            <th style="width:100px">预审时间</th>
            <th style="width:60px">置信度</th>
          </tr></thead>
          <tbody>
            <tr v-for="row in group.items" :key="row.id" @click="showDetail(row)" class="clickable">
              <td><input type="checkbox" :checked="selectedIds.includes(row.id)" @click.stop @change="toggleOne(row.id)" /></td>
              <td class="mono">{{ row.archive_id }}</td>
              <td class="title-cell">{{ row.title }}</td>
              <td class="text-sm">{{ row.volume_id || '—' }}</td>
              <td>{{ row.year }}</td>
              <td><div class="mini-bar"><div class="mini-bar-fill" :class="'mini-bar--'+riskLevelClass(row.risk_level)" :style="{width:row.risk_score+'%'}"></div><span class="mini-bar-num">{{ row.risk_score }}</span></div></td>
              <td><span class="risk-tag" :class="'risk-tag--'+riskLevelClass(row.risk_level)">{{ row.risk_level }}</span></td>
              <td>{{ row.suggestion }}</td>
              <td class="text-sm">{{ row.created_at?.substring(0,10) }}</td>
              <td>{{ ((row.confidence||0)*100).toFixed(0) }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- 按卷展示 -->
    <div class="table-card" v-if="reviewView === 'volume'">
      <table class="data-table">
        <thead><tr>
          <th>案卷编号</th><th>案卷题名</th><th style="width:70px">年度</th>
          <th style="width:80px">件数</th><th style="width:80px">最高风险</th>
          <th style="width:140px">卷级建议</th>
        </tr></thead>
        <tbody>
          <tr v-for="v in volumeRecords" :key="v.archive_id">
            <td class="mono">{{ v.archive_id }}</td>
            <td class="title-cell">{{ v.title }}</td>
            <td>{{ v.year }}</td>
            <td>{{ v.item_count || '-' }}</td>
            <td><span class="risk-tag" :class="'risk-tag--'+riskLevelClass(v.max_risk)">{{ v.max_risk || '-' }}</span></td>
            <td>{{ v.suggestion || '-' }}</td>
          </tr>
          <tr v-if="!volumeRecords.length"><td colspan="6" class="table-empty">暂无案卷数据</td></tr>
        </tbody>
      </table>
    </div>

    <el-pagination v-if="total > pageSize" class="pager" background layout="prev, pager, next, sizes" :total="total" :page-size="pageSize" :current-page="page" :page-sizes="[20,50,100]" @current-change="p=>{page=p;fetchRecords()}" @size-change="s=>{pageSize=s;fetchRecords()}" />

    <div class="export-cards">
      <div class="export-card">
        <h4>📊 导出AI预审结果表格</h4>
        <p>Excel格式，含档案编号、题名、风险评分、敏感类型、AI建议、预审时间等字段。</p>
      </div>
      <div class="export-card">
        <h4>📦 导出档案原文压缩包</h4>
        <p>ZIP格式，含原始扫描件(TIFF/PDF)、对应的OCR识别文本、结构化元数据(XML/JSON)。</p>
      </div>
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
const reviewView = ref('item')
const volumeRecords = ref<any[]>([])

// 按部门分组
const groupedRecords = computed(() => {
  const groups: Record<string, any[]> = {}
  for (const r of records.value) {
    const dept = r.department || '未分类'
    if (!groups[dept]) groups[dept] = []
    groups[dept].push(r)
  }
  return Object.entries(groups).map(([dept, items]) => ({
    dept,
    items,
    allSelected: items.length > 0 && items.every((i:any) => selectedIds.value.includes(i.id)),
  }))
})

function toggleGroup(group: any) {
  const ids = group.items.map((i:any) => i.id)
  if (group.allSelected) { selectedIds.value = selectedIds.value.filter((id:number) => !ids.includes(id)) }
  else { ids.forEach((id:number) => { if (!selectedIds.value.includes(id)) selectedIds.value.push(id) }) }
}
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
function resetFilters() {
  filters.value = { risk_level: '', suggestion: '', year_from: undefined, year_to: undefined }
  fetchRecords()
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
    // 按卷聚合（卷级建议：任一件建议不开放则整卷建议不开放）
    const volMap: Record<string, any> = {}
    for (const r of records.value) {
      const vid = r.volume_id || r.archive_id?.split('-').slice(0,2).join('-') || r.archive_id
      if (!volMap[vid]) volMap[vid] = { archive_id: vid, title: r.volume_title || r.title, year: r.year, item_count: 0, max_risk: '低', suggestion: '建议开放', items: [] }
      volMap[vid].item_count++
      volMap[vid].items.push(r)
      if (r.risk_level === '高' || (r.risk_score||0) > (volMap[vid]._maxScore||0)) { volMap[vid]._maxScore = r.risk_score||0; volMap[vid].max_risk = r.risk_level }
      // 卷级建议传播：任一件不开放/延期开放 → 整卷提升建议级别
      const s = r.suggestion || ''
      if (s.includes('不开放')) volMap[vid].suggestion = '建议不开放'
      else if (s.includes('延期') && !volMap[vid].suggestion.includes('不开放')) volMap[vid].suggestion = '建议延期开放'
      else if (s.includes('脱敏') && volMap[vid].suggestion === '建议开放') volMap[vid].suggestion = '建议部分开放（脱敏后）'
    }
    volumeRecords.value = Object.values(volMap)
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

/* 视图切换 */
.view-toggle { display: flex; gap: 4px; margin-bottom: 12px; }
.toggle-btn {
  padding: 6px 16px; border-radius: var(--r-sm); border: 1px solid var(--c-border);
  background: var(--c-surface); color: var(--c-text-secondary); font-size: var(--fs-sm);
  cursor: pointer; transition: all var(--t-fast);
}
.toggle-btn.active { background: var(--c-accent); color: #fff; border-color: var(--c-accent); }
.toggle-btn:hover:not(.active) { border-color: var(--c-accent); color: var(--c-accent); }

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
.filter-btn-reset {
  height: 36px; padding: 0 16px; border-radius: var(--r-sm); border: 1px solid var(--c-border);
  background: var(--c-surface); color: var(--c-text-secondary); font-size: var(--fs-sm); cursor: pointer;
}
.filter-btn-reset:hover { border-color: var(--c-text-muted); color: var(--c-text); }

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
.pager{margin-top:16px;display:flex;justify-content:center}
.process-banner{padding:12px 16px;margin-bottom:16px;background:linear-gradient(90deg,#EFF6FF,#F0F7FF);border-left:4px solid var(--c-accent);border-radius:var(--r-sm);font-size:var(--fs-sm);color:var(--c-text-secondary);line-height:1.6}
.export-cards{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px}
.export-card{background:var(--c-bg);border-radius:var(--r-md);padding:14px 16px;border:1px solid var(--c-border)}
.export-card h4{font-size:var(--fs-sm);font-weight:var(--fw-semibold);margin:0 0 4px}
.export-card p{font-size:var(--fs-xs);color:var(--c-text-muted);margin:0;line-height:1.5}
/* 部门分组 */
.dept-header{padding:10px 16px;background:linear-gradient(90deg,var(--c-bg),var(--c-surface));border-bottom:1px solid var(--c-border);display:flex;align-items:center;justify-content:space-between}
.dept-name{font-size:var(--fs-sm);font-weight:var(--fw-semibold);color:var(--c-text)}
.dept-count{font-size:var(--fs-xs);color:var(--c-text-muted);background:var(--c-bg);padding:1px 8px;border-radius:var(--r-full)}
.tag-sm {
  display: inline-block; padding: 2px 8px; border-radius: var(--r-full);
  background: #FEF2F2; color: var(--c-danger); font-size: 11px; font-weight: var(--fw-medium); margin: 2px;
}
</style>
