<template>
  <div class="page">
    <div class="page-head"><h2>数据同步</h2></div>

    <!-- Tab 切换 -->
    <div class="sync-tabs">
      <button :class="['sync-tab', { active: tab === 'file' }]" @click="tab = 'file'">文件同步</button>
      <button :class="['sync-tab', { active: tab === 'db' }]" @click="tab = 'db'">数据库同步</button>
      <button :class="['sync-tab', { active: tab === 'history' }]" @click="tab = 'history'">同步历史</button>
    </div>

    <!-- 文件同步配置 -->
    <div class="card" v-if="tab === 'file'">
      <div class="card-body">
        <div class="form-group">
          <label>共享目录路径</label>
          <input class="field-input" v-model="fileConfig.share_path" placeholder="如: /mnt/archive_share 或 \\\\192.168.1.10\\archives" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>同步频率</label>
            <select class="field-input" v-model="fileConfig.sync_frequency" style="width:200px">
              <option value="daily">每天</option>
              <option value="weekly">每周</option>
              <option value="monthly">每月</option>
            </select>
          </div>
          <div class="form-group">
            <label>同步方式</label>
            <select class="field-input" v-model="fileConfig.sync_mode" style="width:200px">
              <option value="incremental">增量</option>
              <option value="full">全量</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>同步窗口开始</label>
            <input class="field-input" v-model="fileConfig.sync_window_start" style="width:120px" placeholder="02:00" />
          </div>
          <div class="form-group">
            <label>同步窗口结束</label>
            <input class="field-input" v-model="fileConfig.sync_window_end" style="width:120px" placeholder="06:00" />
          </div>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px">
          <button class="btn-primary" @click="saveFileConfig">保存配置</button>
          <button class="btn-sm" @click="triggerFileSync" :disabled="syncing">
            {{ syncing === 'file' ? '同步中...' : '手动同步' }}
          </button>
        </div>
        <div v-if="fileMsg" class="sync-msg" :class="fileMsg.type">{{ fileMsg.text }}</div>
      </div>
    </div>

    <!-- 数据库同步配置 -->
    <div class="card" v-else-if="tab === 'db'">
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label>主机地址</label>
            <input class="field-input" v-model="dbConfig.host" placeholder="10.0.0.1" />
          </div>
          <div class="form-group">
            <label>端口</label>
            <input class="field-input" v-model.number="dbConfig.port" style="width:100px" type="number" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>数据库名</label>
            <input class="field-input" v-model="dbConfig.database" />
          </div>
          <div class="form-group">
            <label>只读账号</label>
            <input class="field-input" v-model="dbConfig.username" />
          </div>
        </div>
        <div class="form-group">
          <label>密码</label>
          <input class="field-input" v-model="dbConfig.password" type="password" style="max-width:300px" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>同步频率</label>
            <select class="field-input" v-model="dbConfig.sync_frequency" style="width:200px">
              <option value="daily">每天</option>
              <option value="weekly">每周</option>
              <option value="monthly">每月</option>
            </select>
          </div>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px">
          <button class="btn-primary" @click="saveDbConfig">保存配置</button>
          <button class="btn-sm" @click="triggerDbSync" :disabled="syncing === 'db'">
            {{ syncing === 'db' ? '同步中...' : '手动同步' }}
          </button>
        </div>
        <div v-if="dbMsg" class="sync-msg" :class="dbMsg.type">{{ dbMsg.text }}</div>
      </div>
    </div>

    <!-- 同步历史 -->
    <div class="card" v-else>
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th><th>开始时间</th><th>类型</th><th>方式</th>
            <th>新增</th><th>更新</th><th>失败</th><th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="h in history" :key="h.id">
            <td class="mono">#{{ h.id }}</td>
            <td>{{ h.started_at?.substring(0, 19) }}</td>
            <td>{{ h.sync_type === 'file' ? '文件同步' : '数据库同步' }}</td>
            <td>{{ h.sync_mode === 'incremental' ? '增量' : '全量' }}</td>
            <td>{{ h.new_files || 0 }}</td>
            <td>{{ h.updated_files || 0 }}</td>
            <td>{{ h.failed_count || 0 }}</td>
            <td><span class="risk-tag" :class="'risk-tag--' + (h.status === 'completed' ? 'low' : h.status === 'failed' ? 'high' : 'mid')">{{ statusLabel(h.status) }}</span></td>
          </tr>
          <tr v-if="history.length === 0">
            <td colspan="8" class="table-empty">暂无同步记录</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { syncApi } from '@/api'
import { ElMessage } from 'element-plus'

const tab = ref('file')
const syncing = ref<string | null>(null)
const fileMsg = ref<{ type: string; text: string } | null>(null)
const dbMsg = ref<{ type: string; text: string } | null>(null)
const history = ref<any[]>([])

const fileConfig = reactive({
  share_path: '',
  sync_frequency: 'daily',
  sync_mode: 'incremental',
  sync_window_start: '02:00',
  sync_window_end: '06:00',
})

const dbConfig = reactive({
  host: '',
  port: 3306,
  database: '',
  username: '',
  password: '',
  sync_frequency: 'daily',
})

onMounted(() => { loadConfig(); fetchHistory() })

async function loadConfig() {
  try {
    const res = await syncApi.getConfigs()
    const cfg = res.data
    if (cfg.file_sync) Object.assign(fileConfig, cfg.file_sync)
    if (cfg.database_sync) Object.assign(dbConfig, cfg.database_sync)
  } catch { /* keep defaults */ }
}

async function fetchHistory() {
  try {
    const res = await syncApi.history({ page: 1, page_size: 50 })
    history.value = res.data.items || []
  } catch { /* keep empty */ }
}

async function saveFileConfig() {
  try {
    await syncApi.setFileConfig(fileConfig)
    fileMsg.value = { type: 'success', text: '文件同步配置已保存' }
    setTimeout(() => fileMsg.value = null, 3000)
  } catch {
    fileMsg.value = { type: 'error', text: '保存失败' }
  }
}

async function saveDbConfig() {
  try {
    await syncApi.setDbConfig(dbConfig)
    dbMsg.value = { type: 'success', text: '数据库同步配置已保存' }
    setTimeout(() => dbMsg.value = null, 3000)
  } catch {
    dbMsg.value = { type: 'error', text: '保存失败' }
  }
}

async function triggerFileSync() {
  syncing.value = 'file'
  fileMsg.value = { type: 'info', text: '文件同步任务已提交...' }
  try {
    const res = await syncApi.triggerFile(fileConfig.sync_mode)
    fileMsg.value = { type: 'success', text: `同步已启动 (ID: #${res.data.sync_id})` }
    ElMessage.success('文件同步已启动')
    setTimeout(() => { fileMsg.value = null; fetchHistory() }, 3000)
  } catch {
    fileMsg.value = { type: 'error', text: '启动失败' }
  } finally {
    syncing.value = null
  }
}

async function triggerDbSync() {
  syncing.value = 'db'
  dbMsg.value = { type: 'info', text: '数据库同步任务已提交...' }
  try {
    const res = await syncApi.triggerDb('incremental')
    dbMsg.value = { type: 'success', text: `同步已启动 (ID: #${res.data.sync_id})` }
    ElMessage.success('数据库同步已启动')
    setTimeout(() => { dbMsg.value = null; fetchHistory() }, 3000)
  } catch {
    dbMsg.value = { type: 'error', text: '启动失败' }
  } finally {
    syncing.value = null
  }
}

function statusLabel(s: string) {
  return { pending: '等待中', running: '执行中', completed: '已完成', failed: '失败', queued: '已排队' }[s] || s
}
</script>

<style scoped>
.page { max-width: var(--page-max); margin: 0 auto; }
.page-head { margin-bottom: 20px; }
.page-head h2 { font-size: var(--fs-xl); font-weight: var(--fw-semibold); margin: 0; }
.sync-tabs {
  display: flex; gap: 4px; margin-bottom: 16px;
  background: var(--c-surface); border-radius: var(--r-md); padding: 3px;
  width: fit-content; border: 1px solid var(--c-border);
}
.sync-tab {
  padding: 6px 16px; border-radius: var(--r-sm); border: none;
  background: transparent; color: var(--c-text-secondary);
  font-size: var(--fs-sm); font-weight: var(--fw-medium); cursor: pointer;
  transition: all var(--t-fast);
}
.sync-tab.active { background: var(--c-accent); color: #fff; }
.card {
  background: var(--c-surface); border-radius: var(--r-lg);
  border: 1px solid var(--c-border); overflow: hidden;
}
.card-body { padding: 20px; }
.form-group { margin-bottom: 16px; }
.form-group label {
  display: block; font-size: var(--fs-xs); font-weight: var(--fw-semibold);
  color: var(--c-text-muted); text-transform: uppercase;
  letter-spacing: 0.5px; margin-bottom: 6px;
}
.form-row { display: flex; gap: 16px; }
.field-input {
  height: 40px; padding: 0 12px; border: 1px solid var(--c-border);
  border-radius: var(--r-sm); font-size: var(--fs-base);
  background: var(--c-bg); outline: none; font-family: var(--font);
  width: 100%; max-width: 400px;
}
.field-input:focus { border-color: var(--c-accent); }
.btn-primary {
  height: 36px; padding: 0 20px; border-radius: var(--r-sm); border: none;
  background: var(--c-accent); color: #fff; font-size: var(--fs-sm);
  font-weight: var(--fw-semibold); cursor: pointer;
}
.btn-primary:hover { background: var(--c-accent-hover); }
.btn-sm {
  height: 36px; padding: 0 16px; border-radius: var(--r-sm);
  border: 1px solid var(--c-border); background: var(--c-surface);
  color: var(--c-text-secondary); font-size: var(--fs-sm); cursor: pointer;
}
.btn-sm:hover { border-color: var(--c-accent); color: var(--c-accent); }
.btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
.sync-msg { margin-top: 12px; padding: 8px 12px; border-radius: var(--r-sm); font-size: var(--fs-sm); }
.sync-msg.success { background: #F0FDF4; color: var(--c-success); }
.sync-msg.error { background: #FEF2F2; color: var(--c-danger); }
.sync-msg.info { background: #EFF6FF; color: var(--c-info); }
.data-table { width: 100%; border-collapse: collapse; }
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
.mono { font-family: 'SF Mono', 'Fira Code', monospace; font-size: var(--fs-xs); color: var(--c-text-secondary); }
.table-empty { padding: 48px; text-align: center; color: var(--c-text-muted); }
.risk-tag { padding: 2px 10px; border-radius: var(--r-full); font-size: 11px; font-weight: var(--fw-bold); }
.risk-tag--low { background: #F0FDF4; color: var(--c-success); }
.risk-tag--mid { background: #FFFBEB; color: var(--c-warning); }
.risk-tag--high { background: #FEF2F2; color: var(--c-danger); }
</style>
