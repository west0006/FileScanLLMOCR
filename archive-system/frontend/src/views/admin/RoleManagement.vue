<template>
  <div class="page">
    <div class="page-head"><h2>角色权限</h2><button class="btn-primary" @click="showCreateRole = true">创建角色</button></div>
    <div class="card">
      <table class="data-table">
        <thead><tr><th>角色名称</th><th>描述</th><th style="width:80px">用户数</th><th style="width:120px">操作</th></tr></thead>
        <tbody>
          <tr v-for="r in roles" :key="r.id">
            <td class="font-medium">{{ r.name }}</td><td>{{ r.description }}</td><td>{{ r.user_count }}</td>
            <td>
              <button class="btn-sm" @click="editRole(r)">权限配置</button>
              <button class="btn-sm btn-sm--danger" style="margin-left:4px" @click="deleteRole(r)" :disabled="r.user_count > 0" :title="r.user_count > 0 ? '该角色下有用户，无法删除' : '删除角色'">删除</button>
            </td>
          </tr>
          <tr v-if="roles.length === 0"><td colspan="4" class="table-empty">暂无角色数据</td></tr>
        </tbody>
      </table>
    </div>
    <el-pagination v-if="total > pageSize" class="pager" background layout="prev, pager, next" :total="total" :page-size="pageSize" :current-page="page" @current-change="p=>{page=p;fetchRoles()}" />

    <!-- 权限配置弹窗 -->
    <AppModal :visible="showPerm" :title="'权限配置 - ' + editingRole?.name" @close="showPerm=false" width="480px">
      <div class="perm-grid">
        <label class="perm-item perm-item--all">
          <input type="checkbox" :checked="permAllSelected" @change="togglePermAll" />
          <span class="perm-label">全选 / 清空</span>
        </label>
        <template v-for="p in permModules" :key="p.key">
          <!-- 无子操作的模块：单 checkbox -->
          <label v-if="!p.actions.length" class="perm-item">
            <input type="checkbox" v-model="permForm[p.key]" />
            <span class="perm-label">{{ p.label }}</span>
            <span class="perm-desc">{{ p.desc }}</span>
          </label>
          <!-- 有子操作的模块：模块名 + 子 checkbox -->
          <div v-else class="perm-group">
            <div class="perm-group-label">{{ p.label }} — {{ p.desc }}</div>
            <label v-for="a in p.actions" :key="p.key+'-'+a" class="perm-item perm-item--sub">
              <input type="checkbox" v-model="permForm[p.key][a]" />
              <span class="perm-label perm-label--sub">{{ actionLabel(a) }}</span>
            </label>
          </div>
        </template>
        <div class="perm-group" style="margin-top:8px">
          <div class="perm-group-label">数据权限（案卷级 / 卷内级）</div>
          <label class="perm-item perm-item--sub">
            <input type="checkbox" v-model="dataPermForm.box.entry_view" />
            <span class="perm-label perm-label--sub">案卷级 — 条目浏览</span>
          </label>
          <label class="perm-item perm-item--sub">
            <input type="checkbox" v-model="dataPermForm.file.entry_view" />
            <span class="perm-label perm-label--sub">卷内级 — 条目浏览</span>
          </label>
          <label class="perm-item perm-item--sub">
            <input type="checkbox" v-model="dataPermForm.file.view" />
            <span class="perm-label perm-label--sub">卷内级 — 文件浏览</span>
          </label>
          <label class="perm-item perm-item--sub">
            <input type="checkbox" v-model="dataPermForm.file.download" />
            <span class="perm-label perm-label--sub">卷内级 — 文件下载</span>
          </label>
          <label class="perm-item perm-item--sub">
            <input type="checkbox" v-model="dataPermForm.file.print" />
            <span class="perm-label perm-label--sub">卷内级 — 文件打印</span>
          </label>
        </div>
      </div>
      <template #footer>
        <button class="btn-sm" @click="showPerm=false">取消</button>
        <button class="btn-primary" @click="savePerm">保存</button>
      </template>
    </AppModal>

    <!-- 创建角色弹窗 -->
    <AppModal :visible="showCreateRole" title="创建角色" @close="showCreateRole=false; roleForm.name=''; roleForm.desc=''" width="400px">
      <div class="form-group"><label>角色标识</label><input v-model="roleForm.name" class="field-input" placeholder="英文标识, 如: dept_admin" /></div>
      <div class="form-group"><label>角色描述</label><input v-model="roleForm.desc" class="field-input" placeholder="如: 部门管理员" /></div>
      <template #footer>
        <button class="btn-sm" @click="showCreateRole=false">取消</button>
        <button class="btn-primary" @click="createRole">创建</button>
      </template>
    </AppModal>

    <!-- 密码安全策略 -->
    <div class="security-card">
      <h3><IconSvg name="lock" size="15" /> 密码安全策略</h3>
      <div class="sec-grid">
        <div class="sec-item">最小长度 <strong>12 位</strong></div>
        <div class="sec-item">复杂度 <strong>大小写+数字+符号</strong></div>
        <div class="sec-item">有效期 <strong>30 天</strong></div>
        <div class="sec-item">锁定策略 <strong>5 次失败 / 15 分钟</strong></div>
        <div class="sec-item">会话超时 <strong>30 分钟</strong></div>
        <div class="sec-item">传输加密 <strong>HTTPS / TLS 1.3</strong></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { userApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppModal from '@/components/AppModal.vue'

const roles = ref<any[]>([])
const page = ref(1); const pageSize = ref(10); const total = ref(0)
const showPerm = ref(false)
const showCreateRole = ref(false)
const editingRole = ref<any>(null)
const permForm = reactive<Record<string, any>>({})
const dataPermForm = reactive({ box: { entry_view: true }, file: { entry_view: true, view: true, download: true, print: true } })
const roleForm = reactive({ name: '', desc: '' })

const permModules = [
  { key: 'search', label: '智能检索', desc: '关键词/语义/高级检索', actions: ['view', 'download', 'print'] },
  { key: 'ocr', label: 'OCR识别', desc: '创建任务、查看结果', actions: [] },
  { key: 'review', label: 'AI预审', desc: '审核工作台、任务管理', actions: ['view', 'export'] },
  { key: 'sync', label: '数据同步', desc: '同步配置与监控', actions: [] },
  { key: 'user', label: '用户管理', desc: '用户增删改查', actions: [] },
  { key: 'log', label: '操作日志', desc: '日志查询与审计', actions: [] },
  { key: 'stats', label: '查询统计', desc: '利用统计分析', actions: [] },
]

function actionLabel(a: string): string {
  return { view: '浏览', download: '下载', print: '打印', export: '导出' }[a] || a
}

function roleLabel(name: string) {
  return { system_admin: '系统管理员', archive_admin: '档案管理员', reviewer: '审核员', searcher: '查档人员' }[name] || name
}

onMounted(fetchRoles)

async function fetchRoles() {
  try {
    const res = await userApi.listRoles()
    roles.value = (res.data.items || []).map((r: any) => ({ ...r, name: roleLabel(r.name) }))
  } catch {
    roles.value = [
      { id: 1, name: '系统管理员', description: '全部权限', user_count: 1, permissions: { all: true } },
      { id: 2, name: '档案管理员', description: '档案管理与检索', user_count: 2 },
      { id: 3, name: '审核员', description: '开放审核', user_count: 5 },
    ]
  }
}

const permAllSelected = computed(() => permModules.every(p => {
  const v = permForm[p.key]
  if (typeof v === 'boolean') return v
  if (typeof v === 'object') return Object.values(v).some(Boolean)
  return false
}))
function togglePermAll() {
  const val = !permAllSelected.value
  permModules.forEach(p => {
    if (p.actions.length) {
      const obj: Record<string, boolean> = {}
      p.actions.forEach(a => obj[a] = val)
      permForm[p.key] = obj
    } else {
      permForm[p.key] = val
    }
  })
}

function editRole(r: any) {
  editingRole.value = r
  const perms = r.permissions || {}
  permModules.forEach(p => {
    const v = perms[p.key]
    if (p.actions.length) {
      // 有子操作的模块：初始化为嵌套对象
      const obj: Record<string, boolean> = {}
      p.actions.forEach(a => {
        obj[a] = perms.all ? true : (typeof v === 'object' ? !!v[a] : !!v)
      })
      permForm[p.key] = obj
    } else {
      // 无子操作：bool
      permForm[p.key] = perms.all ? true : (typeof v === 'boolean' ? v : (typeof v === 'object' ? Object.values(v).some(Boolean) : false))
    }
  })
  // 回填数据权限（未配置则默认全选）
  const dp = r.data_permissions || {}
  dataPermForm.box.entry_view = dp.box?.entry_view ?? true
  dataPermForm.file.entry_view = dp.file?.entry_view ?? true
  dataPermForm.file.view = dp.file?.view ?? true
  dataPermForm.file.download = dp.file?.download ?? true
  dataPermForm.file.print = dp.file?.print ?? true
  showPerm.value = true
}

async function savePerm() {
  if (!editingRole.value) return
  try {
    const perms: Record<string, any> = {}
    permModules.forEach(p => { perms[p.key] = permForm[p.key] })
    const dataPerms = { box: { ...dataPermForm.box }, file: { ...dataPermForm.file } }
    const res: any = await userApi.updatePermissions(editingRole.value.id, perms, dataPerms)
    if (res.data && res.data.error) { ElMessage.error(res.data.error); return }
    ElMessage.success('权限已保存')
    showPerm.value = false
    fetchRoles()
  } catch { ElMessage.error('保存失败') }
}

async function deleteRole(r: any) {
  try {
    await ElMessageBox.confirm(`确认删除角色「${r.name}」？`, '删除确认', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
    const res: any = await userApi.deleteRole(r.id)
    if (res.data && res.data.error) { ElMessage.error(res.data.error); return }
    ElMessage.success('角色已删除')
    fetchRoles()
  } catch (e: any) {
    if (e !== 'cancel' && e?.action !== 'cancel') ElMessage.error('删除失败')
  }
}

async function createRole() {
  if (!roleForm.name) { ElMessage.warning('请输入角色标识'); return }
  try {
    const res: any = await userApi.createRole(roleForm.name, roleForm.desc)
    if (res.data && res.data.error) { ElMessage.error(res.data.error); return }
    ElMessage.success('角色已创建')
    showCreateRole.value = false
    roleForm.name = ''; roleForm.desc = ''
    fetchRoles()
  } catch { ElMessage.error('创建失败') }
}
</script>

<style scoped>
.page{max-width:var(--page-max);margin:0 auto}.page-head{margin-bottom:20px}.page-head h2{font-size:var(--fs-xl);font-weight:var(--fw-semibold);margin:0}.card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);overflow:hidden}.data-table{width:100%;border-collapse:collapse}.data-table th{padding:12px 16px;text-align:left;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);text-transform:uppercase;letter-spacing:0.5px;background:var(--c-bg);border-bottom:1px solid var(--c-border)}.data-table td{padding:12px 16px;font-size:var(--fs-sm);color:var(--c-text);border-bottom:1px solid var(--c-border-light)}.btn-sm{height:30px;padding:0 14px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-xs);cursor:pointer}.btn-sm:hover{border-color:var(--c-accent);color:var(--c-accent)}.btn-primary{height:32px;padding:0 20px;border-radius:var(--r-sm);border:none;background:var(--c-accent);color:#fff;font-size:var(--fs-sm);cursor:pointer}.btn-primary:hover{background:var(--c-accent-hover)}.font-medium{font-weight:var(--fw-medium)}.table-empty{padding:48px;text-align:center;color:var(--c-text-muted)}
.perm-grid{display:flex;flex-direction:column;gap:10px}.perm-item{display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--c-bg);border-radius:var(--r-sm);cursor:pointer;transition:background var(--t-fast)}.perm-item:hover{background:var(--c-border-light)}.perm-item input[type=checkbox]{width:18px;height:18px;accent-color:var(--c-accent);cursor:pointer}.perm-label{font-size:var(--fs-sm);font-weight:var(--fw-medium);color:var(--c-text);min-width:80px}.perm-desc{font-size:var(--fs-xs);color:var(--c-text-muted)}
.perm-group{margin-bottom:4px;padding:8px 10px;background:var(--c-bg);border-radius:var(--r-sm)}
.perm-group-label{font-size:var(--fs-sm);font-weight:var(--fw-semibold);color:var(--c-text);margin-bottom:4px}
.perm-item--sub{padding-left:20px;margin-left:0}.perm-item--sub .perm-label{font-size:var(--fs-xs)}
.pager{margin-top:16px;display:flex;justify-content:center}
.security-card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);padding:20px;margin-top:16px}
.security-card h3{font-size:var(--fs-base);font-weight:var(--fw-semibold);margin:0 0 12px}
.sec-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.sec-item{padding:8px 12px;background:var(--c-bg);border-radius:var(--r-sm);font-size:var(--fs-xs);color:var(--c-text-secondary)}
</style>
