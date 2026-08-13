<template>
  <div class="page">
    <!-- 页头 -->
    <div class="page-head">
      <h2>OCR 识别任务</h2>
      <div style="display:flex;gap:8px;align-items:center">
        <span class="engine-badge" :class="'engine--' + engineInfo.mode">{{ engineInfo.label }}</span>
        <button class="btn-sm" @click="fetchEngineInfo">刷新</button>
        <button class="btn-primary" @click="showCreate=true">创建任务</button>
      </div>
    </div>

    <!-- 质量概览 -->
    <div class="quality-bar" v-if="quality.total">
      <span><IconSvg name="chart" size="15" /> 已处理 {{ quality.total }} 件 | 平均准确率 {{ (quality.overall_accuracy*100).toFixed(1) }}%</span>
      <span v-if="quality.low_confidence_count" style="color:var(--c-warning)"> | <IconSvg name="warn" size="14" /> 低置信度 {{ quality.low_confidence_count }} 件</span>
      <span v-if="quality.failed_count" style="color:var(--c-danger)"> | <IconSvg name="warn" size="12" /> 失败 {{ quality.failed_count }} 件</span>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar" style="margin-bottom:12px">
      <select v-model="statusFilter" class="filter-select" @change="fetchTasks()"><option value="">全部状态</option><option value="pending">待处理</option><option value="running">处理中</option><option value="paused">已暂停</option><option value="completed">已完成</option><option value="failed">失败</option><option value="cancelled">已取消</option></select>
      <button class="btn-sm" @click="statusFilter='';fetchTasks()">重置</button>
    </div>

    <!-- 任务表格 -->
    <div class="card">
      <table class="data-table">
        <thead><tr>
          <th>#</th><th>任务名称</th><th style="width:180px">进度</th>
          <th style="width:70px">失败</th><th style="width:60px">优先级</th><th style="width:70px">状态</th>
          <th style="width:140px">时间</th><th style="width:170px">操作</th>
        </tr></thead>
        <tbody>
          <tr v-for="t in tasks" :key="t.id">
            <td class="mono">#{{ t.id }}</td>
            <td>{{ t.task_name }}</td>
            <td>
              <div class="mini-bar">
                <div class="mini-bar-fill" :class="'mini-bar--'+barClass(t.status)" :style="{width:(t.processed_pages/t.total_pages*100||0)+'%'}"></div>
                <span class="mini-bar-num">{{ t.processed_pages }}/{{ t.total_pages }} ({{ t.total_pages ? Math.round(t.processed_pages/t.total_pages*100) : 0 }}%)</span>
              </div>
            </td>
            <td><span style="color:var(--c-danger)">{{ t.failed_pages || 0 }}</span></td>
            <td>
              <select v-model="t.priority" class="pri-select" @change="setPriority(t)">
                <option :value="0">普通</option>
                <option :value="1">高</option>
                <option :value="2">紧急</option>
              </select>
            </td>
            <td><span class="risk-tag" :class="'risk-tag--'+barClass(t.status)">{{ statusLabel(t.status) }}</span></td>
            <td class="text-sm">{{ t.created_at?.substring(0,10) }}</td>
            <td>
              <button class="btn-sm" @click="openDetail(t)">详情</button>
              <button v-if="t.status==='pending'" class="btn-sm" style="margin-left:4px" @click="handleAction(t,'start')">启动</button>
              <button v-if="t.status==='running'" class="btn-sm" style="margin-left:4px" @click="handleAction(t,'pause')">暂停</button>
              <button v-if="t.status==='paused'" class="btn-sm" style="margin-left:4px" @click="handleAction(t,'resume')">恢复</button>
              <button v-if="t.status==='running'||t.status==='pending'||t.status==='paused'" class="btn-sm" style="margin-left:4px" @click="handleAction(t,'cancel')">取消</button>
            </td>
          </tr>
          <tr v-if="tasks.length===0"><td colspan="7" class="table-empty">暂无 OCR 任务，点击右上角「创建任务」开始</td></tr>
        </tbody>
      </table>
    </div>
    <el-pagination v-if="total > pageSize" class="pager" background layout="prev, pager, next, sizes" :total="total" :page-size="pageSize" :current-page="page" :page-sizes="[20,50,100]" @current-change="p=>{page=p;fetchTasks()}" @size-change="s=>{pageSize=s;fetchTasks()}" />

    <!-- 创建任务弹窗 -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate=false">
      <div class="modal-card">
        <div class="modal-head"><h3>创建 OCR 任务</h3><button class="modal-close" @click="showCreate=false"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
        <div class="modal-body">
          <div class="form-group"><label>任务名称 *</label><input class="field-input" v-model="cf.task_name" placeholder="如: 1996年行政档案批量OCR" /></div>
          <div class="form-row">
            <div class="form-group" style="flex:1"><label>起始年度</label><input class="field-input" v-model.number="cf.year_from" type="number" placeholder="如 1996" /></div>
            <div class="form-group" style="flex:1"><label>截止年度</label><input class="field-input" v-model.number="cf.year_to" type="number" placeholder="如 2000" /></div>
          </div>
          <div class="form-row">
            <div class="form-group" style="flex:1"><label>档案门类</label><select class="field-input" v-model="cf.category"><option value="">全部</option><option>行政档案</option><option>党群档案</option><option>教学档案</option><option>科研档案</option><option>人事档案</option><option>财务档案</option></select></div>
            <div class="form-group" style="flex:1"><label>优先级</label><select class="field-input" v-model.number="cf.priority"><option :value="0">普通</option><option :value="1">高</option><option :value="2">紧急</option></select></div>
          </div>
          <div class="ocr-hint">🔒 OCR 处理采用本地部署的 NLP 推理，数据不上云</div>
          <div style="display:flex;gap:12px;justify-content:flex-end;margin-top:20px">
            <button class="btn-sm" @click="showCreate=false">取消</button>
            <button class="btn-primary" @click="handleCreateTask">提交任务</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="showDetail" class="modal-overlay" @click.self="showDetail=false">
      <div class="modal-card" style="width:560px">
        <div class="modal-head"><h3>任务详情 — {{ detailTask?.task_name }}</h3><button class="modal-close" @click="showDetail=false"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
        <div class="modal-body">
          <dl class="detail-grid">
            <div><dt>任务编号</dt><dd>#{{ detailTask?.id }}</dd></div>
            <div><dt>状态</dt><dd><span class="risk-tag" :class="'risk-tag--'+barClass(detailTask?.status)">{{ statusLabel(detailTask?.status) }}</span></dd></div>
            <div><dt>总页数</dt><dd>{{ detailTask?.total_pages || '—' }}</dd></div>
            <div><dt>已处理</dt><dd>{{ detailTask?.processed_pages || 0 }}</dd></div>
            <div><dt>失败数</dt><dd style="color:var(--c-danger)">{{ detailTask?.failed_pages || 0 }}</dd></div>
            <div><dt>剩余</dt><dd>{{ (detailTask?.total_pages || 0) - (detailTask?.processed_pages || 0) }}</dd></div>
            <div><dt>优先级</dt><dd>{{ priLabel(detailTask?.priority) }}</dd></div>
            <div><dt>创建时间</dt><dd>{{ detailTask?.created_at?.substring(0,19) }}</dd></div>
            <div class="span-2"><dt>筛选条件</dt><dd class="text-sm text-muted">{{ detailTask?.filter_criteria ? JSON.stringify(detailTask.filter_criteria) : '无' }}</dd></div>
          </dl>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ocrApi } from '@/api'
import { ElMessage } from 'element-plus'

const tasks = ref<any[]>([])
const showCreate = ref(false)
const showDetail = ref(false)
const detailTask = ref<any>(null)
const page = ref(1); const pageSize = ref(20); const total = ref(0)
const cf = reactive({ task_name: '', category: '', year_from: undefined as number|undefined, year_to: undefined as number|undefined, priority: 0 })
const engineInfo = ref({ mode: 'mock', label: 'Mock 模式' })
const quality = ref<any>({})
const statusFilter = ref('')

onMounted(() => { fetchTasks(); fetchEngineInfo(); fetchQuality() })

async function fetchTasks() {
  try { const res = await ocrApi.listTasks({ page:page.value, page_size:pageSize.value, status: statusFilter.value||undefined }); tasks.value = res.data.items || []; total.value = res.data.total || 0 } catch { /* */ }
}
async function fetchEngineInfo() {
  try { const res = await ocrApi.listTasks({ page:1, page_size:1 }) /* use models endpoint */; 
    const m = await (await fetch('/api/ocr/models', {headers:{Authorization:'Bearer '+localStorage.getItem('access_token')}})).json()
    engineInfo.value = { mode: m.mode||'mock', label: m.gpu ? 'PaddleOCR GPU' : m.available ? 'PaddleOCR CPU' : 'Mock 模式' }
  } catch { engineInfo.value = { mode:'mock', label:'Mock 模式' } }
}
async function fetchQuality() {
  try { const res = await ocrApi.qualityReport({}); quality.value = res.data } catch { /* */ }
}
async function handleCreateTask() {
  if (!cf.task_name) { ElMessage.warning('请输入任务名称'); return }
  // 长度校验
  if (cf.task_name.length > 50) { ElMessage.warning('任务名称不能超过50个字符'); return }
  // 特殊字符校验
  if (/[\\/:*?"<>|]/.test(cf.task_name)) { ElMessage.warning('任务名称包含非法字符：\\ / : * ? " < > |'); return }
  try {
    const res = await ocrApi.createTask({ task_name: cf.task_name, category: cf.category||undefined, year_from: cf.year_from, year_to: cf.year_to, priority: cf.priority })
    if (res.data && res.data.error) { ElMessage.error(res.data.error); return }
    ElMessage.success('任务已创建')
    showCreate.value = false
    cf.task_name = ''; cf.category = ''; cf.year_from = undefined; cf.year_to = undefined; cf.priority = 0
    fetchTasks()
  } catch { ElMessage.error('创建失败') }
}
function barClass(s: string) { return { pending:'low',running:'mid',paused:'mid',completed:'low',failed:'high',cancelled:'high' }[s]||'low' }
function statusLabel(s: string) { return { pending:'待处理',running:'处理中',paused:'已暂停',completed:'已完成',failed:'失败',cancelled:'已取消' }[s]||s }
function priLabel(p: number) { return {0:'普通',1:'高',2:'紧急'}[p]||'普通' }
async function openDetail(t: any) {
  try {
    const res = await ocrApi.getTask(t.id)
    detailTask.value = res.data
  } catch { detailTask.value = t }
  showDetail.value = true
}
async function setPriority(t: any) {
  try {
    await ocrApi.updateTask(t.id, 'set_priority', t.priority)
    ElMessage.success('优先级已调整')
  } catch { ElMessage.error('调整失败') }
}
async function handleAction(t: any, action: string) {
  try {
    await ocrApi.updateTask(t.id, action)
    ElMessage.success({ start:'已启动',pause:'已暂停',resume:'已恢复',cancel:'已取消' }[action]||'操作成功')
    fetchTasks()
  } catch { ElMessage.error('操作失败') }
}
</script>

<style scoped>
.page{max-width:var(--page-max);margin:0 auto}.page-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.page-head h2{font-size:var(--fs-xl);font-weight:var(--fw-semibold);margin:0}
.engine-badge{padding:2px 10px;border-radius:var(--r-full);font-size:11px;font-weight:var(--fw-bold)}.engine--mock{background:#FEF3C7;color:var(--c-warning)}.engine--real{background:#D1FAE5;color:var(--c-accent)}
.quality-bar{padding:8px 14px;margin-bottom:12px;background:var(--c-surface);border-radius:var(--r-md);border:1px solid var(--c-border);font-size:var(--fs-sm);color:var(--c-text-secondary);display:flex;gap:8px;flex-wrap:wrap}
.btn-primary{height:36px;padding:0 20px;border-radius:var(--r-sm);border:none;background:var(--c-accent);color:#fff;font-size:var(--fs-sm);font-weight:var(--fw-semibold);cursor:pointer}.btn-primary:hover{background:var(--c-accent-hover)}
.btn-sm{height:30px;padding:0 14px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-xs);cursor:pointer}.btn-sm:hover{border-color:var(--c-accent);color:var(--c-accent)}
.card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);overflow:hidden}
.data-table{width:100%;border-collapse:collapse}
.data-table th{padding:12px 16px;text-align:left;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);text-transform:uppercase;letter-spacing:0.5px;background:var(--c-bg);border-bottom:1px solid var(--c-border)}
.data-table td{padding:12px 16px;font-size:var(--fs-sm);color:var(--c-text);border-bottom:1px solid var(--c-border-light)}
.mono{font-family:'SF Mono','Fira Code',monospace;font-size:var(--fs-xs);color:var(--c-text-secondary)}
.text-sm{font-size:var(--fs-xs);color:var(--c-text-secondary)}.text-muted{color:var(--c-text-muted)}
.table-empty{padding:48px;text-align:center;color:var(--c-text-muted)}
.mini-bar{display:flex;align-items:center;gap:8px}.mini-bar-fill{height:6px;border-radius:var(--r-full);min-width:2px}.mini-bar--low{background:var(--c-success)}.mini-bar--mid{background:var(--c-warning)}.mini-bar--high{background:var(--c-danger)}.mini-bar-num{font-size:var(--fs-xs);color:var(--c-text-secondary)}
.risk-tag{padding:2px 10px;border-radius:var(--r-full);font-size:11px;font-weight:var(--fw-bold)}.risk-tag--low{background:#F0FDF4;color:var(--c-success)}.risk-tag--mid{background:#FFFBEB;color:var(--c-warning)}.risk-tag--high{background:#FEF2F2;color:var(--c-danger)}
.priority-tag{padding:1px 8px;border-radius:var(--r-full);font-size:11px}.pri--0{background:var(--c-bg);color:var(--c-text-secondary)}.pri--1{background:#FFFBEB;color:var(--c-warning)}.pri--2{background:#FEF2F2;color:var(--c-danger)}
.pri-select{height:28px;padding:0 4px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-xs);background:var(--c-bg);cursor:pointer}
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;z-index:100;backdrop-filter:blur(4px)}.modal-card{width:480px;background:var(--c-surface);border-radius:var(--r-lg);box-shadow:var(--s-dropdown);max-height:80vh;overflow-y:auto}.modal-head{display:flex;align-items:center;justify-content:space-between;padding:20px 24px;border-bottom:1px solid var(--c-border-light)}.modal-head h3{margin:0;font-size:var(--fs-lg)}.modal-close{width:32px;height:32px;border-radius:var(--r-sm);border:none;background:transparent;cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--c-text-muted)}.modal-close:hover{background:var(--c-bg)}.modal-body{padding:24px}
.form-group{margin-bottom:16px}.form-group label{display:block;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px}.field-input{height:40px;padding:0 12px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-base);background:var(--c-bg);outline:none;font-family:var(--font);width:100%}.field-input:focus{border-color:var(--c-accent)}.form-row{display:flex;gap:12px}
.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px 24px;margin:0}.detail-grid dt{font-size:var(--fs-xs);color:var(--c-text-muted);margin-bottom:2px}.detail-grid dd{font-size:var(--fs-sm);color:var(--c-text);margin:0;font-weight:var(--fw-medium)}.span-2{grid-column:span 2}
.pager{margin-top:16px;display:flex;justify-content:center}
.ocr-hint{padding:8px 12px;margin-top:12px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:var(--r-sm);font-size:var(--fs-xs);color:#92400E}
.filter-bar{display:flex;gap:8px;align-items:center;padding:8px 14px;background:var(--c-surface);border-radius:var(--r-md);border:1px solid var(--c-border)}
.filter-select{height:32px;padding:0 10px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-xs);background:var(--c-bg);outline:none;cursor:pointer}
</style>
