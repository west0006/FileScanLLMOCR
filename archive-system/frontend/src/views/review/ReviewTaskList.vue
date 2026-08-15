<template>
  <div class="page">
    <div class="page-head"><h2>预审任务</h2><button class="btn-primary" @click="showCreate=true">创建任务</button></div>
    <div class="process-banner"><IconSvg name="pin" size="14" /> 系统对每批审核任务自动完成 AI 智能预审，生成风险评分、敏感信息标注、开放建议。<strong>审核人员无需在系统中进行人工复核</strong>，可通过导出按钮获取预审数据。</div>
    <div class="card">
      <table class="data-table">
        <thead><tr><th>任务名称</th><th>批次</th><th>截止日期</th><th style="width:200px">进度</th><th>风险分布</th><th>通过率</th><th>高风险</th><th>状态</th><th style="width:200px">操作</th></tr></thead>
        <tbody>
          <tr v-for="t in tasks" :key="t.id">
            <td>{{ t.task_name }}</td><td>{{ t.batch_name }}</td>
            <td class="text-sm">{{ t.deadline?.substring(0,10) || '—' }}</td>
            <td><div class="mini-bar"><div class="mini-bar-fill mini-bar--low" :style="{width:(t.completed_count/t.total_count*100||0)+'%'}"></div><span class="mini-bar-num">{{ t.completed_count }}/{{ t.total_count }}</span></div><div v-if="t.status==='running' && t.speed" class="text-xs" style="color:var(--c-text-muted);margin-top:2px">{{ t.speed }} 件/分 · 约 {{ etaText(t) }} 剩余</div></td>
            <td><span class="text-xs"><span style="color:var(--c-danger)">高{{ t.risk_dist?.high||0 }}</span> / <span style="color:var(--c-warning)">中{{ t.risk_dist?.medium||0 }}</span> / <span style="color:var(--c-success)">低{{ t.risk_dist?.low||0 }}</span></span></td>
            <td class="text-sm">{{ passRate(t) }}</td>
            <td class="text-sm"><span style="color:var(--c-danger);font-weight:var(--fw-semibold)">{{ t.risk_dist?.high || 0 }}</span></td>
            <td><span class="risk-tag" :class="'risk-tag--'+statusClass(t.status)">{{ statusLabel(t.status) }}</span></td>
            <td>
              <button v-if="t.status==='pending'" class="btn-sm" @click="handleTaskAction(t, 'start')">启动</button>
              <button v-if="t.status==='running'" class="btn-sm" @click="handleTaskAction(t, 'pause')">暂停</button>
              <button v-if="t.status==='paused'" class="btn-sm" @click="handleTaskAction(t, 'resume')">恢复</button>
              <button v-if="t.status==='running'||t.status==='paused'" class="btn-sm" @click="handleTaskAction(t, 'mark_completed')">标记完成</button>
              <button v-if="t.status==='completed'||t.status==='cancelled'||t.status==='failed'" class="btn-sm" @click="handleTaskAction(t, 'view')">查看</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <el-pagination v-if="total > pageSize" class="pager" background layout="prev, pager, next, sizes" :total="total" :page-size="pageSize" :current-page="page" :page-sizes="[20,50,100]" @current-change="p=>{page=p;fetchTasks()}" @size-change="s=>{pageSize=s;fetchTasks()}" />

    <div class="export-row" v-if="canExport">
      <button class="btn-primary" @click="handleExport"><IconSvg name="chart" size="15" /> 导出AI预审结果表格</button>
      <button class="btn-sm" @click="handleExportArchive"><IconSvg name="pkg" size="15" /> 导出对应档案原文压缩包</button>
    </div>

    <div class="metrics-card" v-if="tasks.length">
      <h3><IconSvg name="chart" size="15" /> AI预审效率与质量</h3>
      <table class="data-table">
        <thead><tr><th>指标</th><th>数值</th></tr></thead>
        <tbody>
          <tr><td>平均单件预审耗时</td><td>{{ metrics.avg_processing_ms ? (metrics.avg_processing_ms / 1000).toFixed(1) + ' 秒/件' : '—' }}</td></tr>
          <tr><td>已完成审核数</td><td>{{ metrics.total_reviewed || 0 }} 件</td></tr>
          <tr><td>活跃任务数</td><td>{{ metrics.active_tasks || 0 }} 个</td></tr>
          <tr><td>总任务数</td><td>{{ metrics.total_tasks || 0 }} 个</td></tr>
        </tbody>
      </table>
    </div>

    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate=false"><div class="modal-card"><div class="modal-head"><h3>新建审核任务</h3><button class="modal-close" @click="showCreate=false"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div><div class="modal-body">
      <div class="form-group"><label>任务名称</label><input class="field-input" v-model="createForm.task_name" placeholder="如: 2025年行政档案批量预审" /></div>
      <div class="form-row"><div class="form-group" style="flex:1"><label>起始年度</label><select v-model="createForm.year_from" class="field-input"><option :value="undefined">不限</option><option v-for="y in yearOpts" :key="'rf'+y" :value="y">{{ y }}</option></select></div><div class="form-group" style="flex:1"><label>截止年度</label><select v-model="createForm.year_to" class="field-input"><option :value="undefined">不限</option><option v-for="y in yearOpts" :key="'rt'+y" :value="y">{{ y }}</option></select></div></div>
      <div class="form-row"><div class="form-group" style="flex:1"><label>档案门类</label><select v-model="createForm.category" class="field-input"><option value="">全部</option><option v-for="c in categories" :key="c" :value="c">{{ c }}</option></select></div><div class="form-group" style="flex:1"><label>归口单位</label><input class="field-input" v-model="createForm.department" placeholder="可选，如: 教务处" /></div></div>
      <div class="form-group"><label>批次名称</label><input class="field-input" v-model="createForm.batch_name" placeholder="如: 第一批开放审核" /></div>
      <label style="display:flex;align-items:center;gap:8px;font-size:var(--fs-sm);color:var(--c-text);cursor:pointer"><input type="checkbox" v-model="createForm.due_only" style="width:16px;height:16px" /><span>仅到期档案（满 25 年）</span></label>
      <div class="form-group"><label>截止日期</label><input class="field-input" type="date" v-model="createForm.deadline" /></div>
      <div class="scope-hint">📋 任务将对符合筛选条件的已 OCR 档案进行 AI 预审，结果可在「预审记录」页查看。</div>
      <div style="display:flex;gap:12px;justify-content:flex-end;margin-top:20px"><button class="btn-sm" @click="showCreate=false">取消</button><button class="btn-primary" @click="handleCreateTask">创建任务</button></div></div></div></div>

    <div v-if="showReport" class="modal-overlay" @click.self="showReport=false"><div class="modal-card" style="width:520px"><div class="modal-head"><h3>预审报告 — {{ reportTask?.task_name }}</h3><button class="modal-close" @click="showReport=false"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div><div class="modal-body">
      <dl class="detail-grid">
        <div><dt>批次</dt><dd>{{ reportTask?.batch_name || '—' }}</dd></div>
        <div><dt>状态</dt><dd><span class="risk-tag" :class="'risk-tag--'+statusClass(reportTask?.status)">{{ statusLabel(reportTask?.status) }}</span></dd></div>
        <div><dt>完成进度</dt><dd>{{ reportTask?.completed_count }}/{{ reportTask?.total_count }}</dd></div>
        <div><dt>通过率</dt><dd>{{ passRate(reportTask) }}</dd></div>
        <div><dt>截止日期</dt><dd>{{ reportTask?.deadline?.substring(0,10) || '—' }}</dd></div>
        <div><dt>创建时间</dt><dd>{{ reportTask?.created_at?.substring(0,19) || '—' }}</dd></div>
      </dl>
      <h4 style="margin:16px 0 8px;font-size:var(--fs-sm);font-weight:var(--fw-semibold)">风险分布</h4>
      <div class="risk-dist-row">
        <span style="color:var(--c-danger)">高风险 {{ reportRisk.high }}</span>
        <span style="color:var(--c-warning)">中风险 {{ reportRisk.medium }}</span>
        <span style="color:var(--c-success)">低风险 {{ reportRisk.low }}</span>
      </div>
      <div class="scope-hint">📊 完整预审明细可在「预审记录」页按任务筛选查看与导出。</div>
    </div></div></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { reviewApi } from '@/api'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const tasks = ref<any[]>([])
const metrics = ref<any>({})
const showCreate = ref(false)
const yearOpts = Array.from({ length: 56 }, (_, i) => 1970 + i)
const categories = ['行政档案', '党群档案', '教学档案', '科研档案', '人事档案', '财务档案', '基建档案', '声像档案']
const createForm = ref({ task_name: '', batch_name: '', year_from: undefined as number | undefined, year_to: undefined as number | undefined, category: '', department: '', due_only: false, deadline: '' })
const page = ref(1); const pageSize = ref(20); const total = ref(0)
// 导出按钮门控：仅有 review.export 权限的用户可见（与 ReviewRecordList 一致）
const canExport = computed(() => auth.can('all') || auth.can('review', 'export'))

onMounted(fetchTasks)
async function fetchTasks() {
  try {
    const res = await reviewApi.listTasks({ page: page.value, page_size: pageSize.value })
    tasks.value = res.data.items || []
    total.value = res.data.total || 0
    metrics.value = res.data.metrics || {}
  } catch { /* keep empty */ }
}
async function handleCreateTask() {
  if (!createForm.value.task_name) { ElMessage.warning('请输入任务名称'); return }
  try {
    await reviewApi.createTask({ task_name: createForm.value.task_name, batch_name: createForm.value.batch_name || undefined, year_from: createForm.value.year_from, year_to: createForm.value.year_to, category: createForm.value.category || undefined, department: createForm.value.department || undefined, due_only: createForm.value.due_only, deadline: createForm.value.deadline || undefined })
    ElMessage.success('任务已创建')
    showCreate.value = false
    createForm.value = { task_name: '', batch_name: '', year_from: undefined, year_to: undefined, category: '', department: '', due_only: false, deadline: '' }
    fetchTasks()
  } catch { ElMessage.error('创建失败') }
}
function statusClass(s: string) { return { pending:'low', running:'mid', completed:'low', failed:'high' }[s]||'low' }
function statusLabel(s: string) { return { pending:'待启动', running:'处理中', paused:'已暂停', completed:'已完成', failed:'失败', cancelled:'已取消' }[s]||s }
// 预审通过率 = 低风险（建议开放）数 / 总完成数
function passRate(t: any) {
  const h = t.risk_dist?.high || 0
  const m = t.risk_dist?.medium || 0
  const l = t.risk_dist?.low || 0
  const total = h + m + l
  return total > 0 ? Math.round(l / total * 100) + '%' : '—'
}
// 预计剩余时间人性化展示
function etaText(t: any) {
  const s = t.eta_seconds
  if (s == null) return '—'
  if (s < 60) return `${s} 秒`
  if (s < 3600) return `${Math.round(s / 60)} 分钟`
  return `${(s / 3600).toFixed(1)} 小时`
}
async function handleExport() {
  try {
    const res = await reviewApi.export({})
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `AI预审结果_${new Date().toISOString().slice(0, 10)}.xlsx`
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch { ElMessage.error('导出失败，请确认已连接后端服务') }
}
function handleExportArchive() { ElMessage.info('请前往「预审记录」页选择档案后导出原文压缩包') }
// 预审报告（RV-008 已完成任务查看报告）
const showReport = ref(false)
const reportTask = ref<any>(null)
const reportRisk = computed(() => {
  const d = reportTask.value?.risk_distribution || reportTask.value?.risk_dist || {}
  return {
    high: d.high ?? d['高'] ?? 0,
    medium: d.medium ?? d['中'] ?? 0,
    low: d.low ?? d['低'] ?? 0,
  }
})
async function openReport(t: any) {
  reportTask.value = t
  showReport.value = true
  try {
    const res = await reviewApi.getTask(t.id)
    reportTask.value = { ...t, ...res.data }
  } catch { /* 使用列表已有数据 */ }
}
async function handleTaskAction(t: any, action: string) {
  if (action === 'view') {
    openReport(t)
    return
  }
  try {
    await reviewApi.updateTask(t.id, action)
    const msg: Record<string, string> = {
      start: '任务已启动', pause: '任务已暂停', resume: '任务已恢复',
      cancel: '任务已取消', mark_completed: '任务已标记完成',
    }
    ElMessage.success(msg[action] || '操作成功')
    fetchTasks()
  } catch { ElMessage.error('操作失败') }
}
</script>

<style scoped>
.page { max-width: var(--page-max); margin: 0 auto; }
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-head h2 { font-size: var(--fs-xl); font-weight: var(--fw-semibold); margin: 0; }
.btn-primary {
  height: 36px; padding: 0 20px; border-radius: var(--r-sm); border: none;
  background: var(--c-accent); color: #fff; font-size: var(--fs-sm); font-weight: var(--fw-semibold); cursor: pointer;
}
.btn-primary:hover { background: var(--c-accent-hover); }
.btn-sm {
  height: 30px; padding: 0 14px; border-radius: var(--r-sm); border: 1px solid var(--c-border);
  background: var(--c-surface); color: var(--c-text-secondary); font-size: var(--fs-xs); cursor: pointer;
}
.btn-sm:hover { border-color: var(--c-accent); color: var(--c-accent); }
.card { background: var(--c-surface); border-radius: var(--r-lg); border:1px solid var(--c-border); overflow:hidden; }
.data-table { width:100%; border-collapse:collapse; }
.data-table th { padding:12px 16px; text-align:left; font-size:var(--fs-xs); font-weight:var(--fw-semibold); color:var(--c-text-muted); text-transform:uppercase; letter-spacing:0.5px; background:var(--c-bg); border-bottom:1px solid var(--c-border); }
.data-table td { padding:12px 16px; font-size:var(--fs-sm); color:var(--c-text); border-bottom:1px solid var(--c-border-light); }
.mini-bar{display:flex;align-items:center;gap:8px}.mini-bar-fill{height:6px;border-radius:var(--r-full);min-width:2px}.mini-bar--low{background:var(--c-success)}.mini-bar--mid{background:var(--c-warning)}.mini-bar--high{background:var(--c-danger)}.mini-bar-num{font-size:var(--fs-xs);color:var(--c-text-secondary)}
.risk-tag{padding:2px 10px;border-radius:var(--r-full);font-size:11px;font-weight:var(--fw-bold)}.risk-tag--low{background:#F0FDF4;color:var(--c-success)}.risk-tag--mid{background:#FFFBEB;color:var(--c-warning)}.risk-tag--high{background:#FEF2F2;color:var(--c-danger)}
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;z-index:100;backdrop-filter:blur(4px)}.modal-card{width:480px;background:var(--c-surface);border-radius:var(--r-lg);box-shadow:var(--s-dropdown)}.modal-head{display:flex;align-items:center;justify-content:space-between;padding:20px 24px;border-bottom:1px solid var(--c-border-light)}.modal-head h3{margin:0;font-size:var(--fs-lg)}.modal-close{width:32px;height:32px;border-radius:var(--r-sm);border:none;background:transparent;cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--c-text-muted)}.modal-close:hover{background:var(--c-bg)}.modal-body{padding:24px}
.form-group{margin-bottom:16px}.form-group label{display:block;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px}.field-input{height:40px;padding:0 12px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-base);background:var(--c-bg);outline:none;font-family:var(--font);width:100%}.field-input:focus{border-color:var(--c-accent)}
.pager{margin-top:16px;display:flex;justify-content:center}
.process-banner{padding:12px 16px;margin-bottom:16px;background:linear-gradient(90deg,#EFF6FF,#F0F7FF);border-left:4px solid var(--c-accent);border-radius:var(--r-sm);font-size:var(--fs-sm);color:var(--c-text-secondary);line-height:1.6}
.export-row{display:flex;gap:8px;margin-top:16px}
.metrics-card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);padding:20px;margin-top:16px}
.metrics-card h3{font-size:var(--fs-base);font-weight:var(--fw-semibold);margin:0 0 12px}
.form-row{display:flex;gap:12px}.scope-hint{padding:8px 12px;margin-top:8px;background:#FFFBEB;border-radius:var(--r-sm);font-size:var(--fs-xs);color:#92400E;line-height:1.6}
.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px 20px;margin:0}.detail-grid dt{font-size:var(--fs-xs);color:var(--c-text-muted);margin-bottom:2px}.detail-grid dd{font-size:var(--fs-sm);color:var(--c-text);margin:0;font-weight:var(--fw-medium)}
.risk-dist-row{display:flex;gap:16px;padding:12px 14px;background:var(--c-bg);border-radius:var(--r-sm);font-size:var(--fs-sm)}
</style>
