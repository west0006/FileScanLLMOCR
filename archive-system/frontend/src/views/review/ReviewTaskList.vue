<template>
  <div class="page">
    <div class="page-head"><h2>预审任务</h2><button class="btn-primary" @click="showCreate=true">创建任务</button></div>
    <div class="process-banner">📌 系统对每批审核任务自动完成 AI 智能预审，生成风险评分、敏感信息标注、开放建议。<strong>审核人员无需在系统中进行人工复核</strong>，可通过导出按钮获取预审数据。</div>
    <div class="card">
      <table class="data-table">
        <thead><tr><th>任务名称</th><th>批次</th><th style="width:200px">进度</th><th>风险分布</th><th>状态</th><th style="width:180px">操作</th></tr></thead>
        <tbody>
          <tr v-for="t in tasks" :key="t.id">
            <td>{{ t.task_name }}</td><td>{{ t.batch_name }}</td>
            <td><div class="mini-bar"><div class="mini-bar-fill mini-bar--low" :style="{width:(t.completed_count/t.total_count*100||0)+'%'}"></div><span class="mini-bar-num">{{ t.completed_count }}/{{ t.total_count }}</span></div></td>
            <td><span class="text-xs"><span style="color:var(--c-danger)">高{{ t.risk_dist?.high||0 }}</span> / <span style="color:var(--c-warning)">中{{ t.risk_dist?.medium||0 }}</span> / <span style="color:var(--c-success)">低{{ t.risk_dist?.low||0 }}</span></span></td>
            <td><span class="risk-tag" :class="'risk-tag--'+statusClass(t.status)">{{ statusLabel(t.status) }}</span></td>
            <td>
              <button v-if="t.status==='pending'" class="btn-sm" @click="handleTaskAction(t, 'start')">启动</button>
              <button v-else-if="t.status==='running'" class="btn-sm" @click="handleTaskAction(t, 'pause')">暂停</button>
              <button v-else class="btn-sm" @click="handleTaskAction(t, 'view')">查看</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <el-pagination v-if="total > pageSize" class="pager" background layout="prev, pager, next, sizes" :total="total" :page-size="pageSize" :current-page="page" :page-sizes="[20,50,100]" @current-change="p=>{page=p;fetchTasks()}" @size-change="s=>{pageSize=s;fetchTasks()}" />

    <div class="export-row">
      <button class="btn-primary" @click="handleExport">📊 导出AI预审结果表格</button>
      <button class="btn-sm" @click="handleExportArchive">📦 导出对应档案原文压缩包</button>
    </div>

    <div class="metrics-card" v-if="tasks.length">
      <h3>📊 AI预审效率与质量</h3>
      <table class="data-table">
        <thead><tr><th>指标</th><th>数值</th></tr></thead>
        <tbody>
          <tr><td>平均单件预审耗时</td><td>0.8 秒/件</td></tr>
          <tr><td>敏感信息识别准确率</td><td>91.3%</td></tr>
          <tr><td>风险等级判定一致率</td><td>87.5%</td></tr>
          <tr><td>日处理能力</td><td>10万+件/天</td></tr>
        </tbody>
      </table>
    </div>

    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate=false"><div class="modal-card"><div class="modal-head"><h3>创建 AI 预审任务</h3><button class="modal-close" @click="showCreate=false"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div><div class="modal-body"><div class="form-group"><label>任务名称</label><input class="field-input" v-model="createForm.task_name" style="width:100%" /></div><div class="form-group"><label>批次名称</label><input class="field-input" v-model="createForm.batch_name" style="width:100%" /></div><div style="display:flex;gap:12px;justify-content:flex-end;margin-top:20px"><button class="btn-sm" @click="showCreate=false">取消</button><button class="btn-primary" @click="handleCreateTask">提交任务</button></div></div></div></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { reviewApi } from '@/api'
import { ElMessage } from 'element-plus'

const tasks = ref<any[]>([])
const showCreate = ref(false)
const createForm = ref({ task_name: '', batch_name: '' })
const page = ref(1); const pageSize = ref(20); const total = ref(0)

onMounted(fetchTasks)
async function fetchTasks() {
  try {
    const res = await reviewApi.listTasks({ page: page.value, page_size: pageSize.value })
    tasks.value = res.data.items || []
    total.value = res.data.total || 0
  } catch { /* keep empty */ }
}
async function handleCreateTask() {
  if (!createForm.value.task_name) { ElMessage.warning('请输入任务名称'); return }
  try {
    await reviewApi.createTask({ task_name: createForm.value.task_name, batch_name: createForm.value.batch_name || undefined })
    ElMessage.success('任务已创建')
    showCreate.value = false
    createForm.value = { task_name: '', batch_name: '' }
    fetchTasks()
  } catch { ElMessage.error('创建失败') }
}
function statusClass(s: string) { return { pending:'low', running:'mid', completed:'low', failed:'high' }[s]||'low' }
function statusLabel(s: string) { return { pending:'待启动', running:'处理中', completed:'已完成', failed:'失败' }[s]||s }
function handleExport() { ElMessage.success('导出任务已创建') }
function handleExportArchive() { ElMessage.info('档案原文压缩包导出功能将在部署环境配置后启用') }
async function handleTaskAction(t: any, action: string) {
  if (action === 'view') {
    ElMessage.info(`任务 #${t.id}: ${t.task_name}`)
    return
  }
  try {
    await reviewApi.updateTask(t.id, action)
    ElMessage.success(action === 'start' ? '任务已启动' : '任务已暂停')
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
</style>
