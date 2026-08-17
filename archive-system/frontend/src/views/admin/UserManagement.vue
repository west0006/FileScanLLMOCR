<template>
  <div class="page">
    <div class="page-head">
      <h2>用户管理 <span class="user-count">共 {{ total }} 人</span></h2>
      <div style="display:flex;gap:8px;align-items:center">
        <span v-if="selectedIds.length" class="selected-badge">已选 {{ selectedIds.length }} 人</span>
        <button v-if="selectedIds.length" class="btn-sm" @click="batchStatus(true)">批量启用</button>
        <button v-if="selectedIds.length" class="btn-sm" @click="batchStatus(false)">批量停用</button>
        <button class="btn-primary" @click="openCreate">新建用户</button>
      </div>
    </div>
    <div class="filter-bar">
      <select v-model="roleFilter" class="filter-select">
        <option value="">全部角色</option>
        <option value="system_admin">系统管理员</option>
        <option value="archive_admin">档案馆员</option>
        <option value="reviewer">审核员</option>
      </select>
      <select v-model="statusFilter" class="filter-select">
        <option value="">全部状态</option>
        <option value="1">正常</option>
        <option value="0">停用</option>
      </select>
      <input v-model="searchKeyword" placeholder="搜索用户名/姓名" class="filter-input" @keyup.enter="fetchUsers()" />
      <button class="btn-accent-sm" @click="fetchUsers()">查询</button>
    </div>
    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th style="width:36px"><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
            <th>姓名</th>
            <th>用户名</th>
            <th>所属部门</th>
            <th>角色</th>
            <th>最后登录</th>
            <th style="width:80px">状态</th>
            <th style="width:210px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td><input type="checkbox" :checked="selectedIds.includes(u.id)" @change="toggleSelect(u.id)" /></td>
            <td><span class="online-dot" :class="u.is_active ? 'dot--on' : 'dot--off'"></span>{{ u.name }}</td>
            <td class="mono">{{ u.username }}</td>
            <td>{{ u.department || '—' }}</td>
            <td>{{ roleLabel(u.role) }}</td>
            <td class="text-sm">{{ u.last_login_at?.substring(0, 19) || u.created_at?.substring(0, 19) || '—' }}</td>
            <td><span class="risk-tag" :class="u.is_active ? 'risk-tag--low' : 'risk-tag--high'">{{ u.is_active ? '正常' :
              '停用'
                }}</span></td>
            <td>
              <button class="btn-sm" @click="openEdit(u)">编辑</button>
              <button class="btn-sm" style="margin-left:4px" @click="openResetPwd(u)">密码</button>
              <button class="btn-sm" style="margin-left:4px" @click="toggleUser(u)">{{ u.is_active ? '停用' : '启用'
              }}</button>
            </td>
          </tr>
          <tr v-if="users.length === 0">
            <td colspan="8" style="text-align:center;padding:40px;color:var(--c-text-muted)">暂无用户</td>
          </tr>
        </tbody>
      </table>
    </div>
    <el-pagination v-if="total > pageSize" class="pager" background layout="prev, pager, next, sizes" :total="total"
      :page-size="pageSize" :current-page="page" :page-sizes="[20, 50, 100]"
      @current-change="(p: number) => { page = p; fetchUsers() }"
      @size-change="(s: number) => { pageSize = s; fetchUsers() }" />

    <!-- 新建弹窗 -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal-card">
        <div class="modal-head">
          <h3>新建用户</h3><button class="modal-close" @click="showCreate = false"><svg width="18" height="18"
              viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg></button>
        </div>
        <div class="modal-body">
          <div class="form-group"><label>用户名</label><input v-model="form.username" class="field-input"
              placeholder="3-50字符" /></div>
          <div class="form-group"><label>姓名</label><input v-model="form.name" class="field-input" /></div>
          <div class="form-group"><label>所属部门</label><input v-model="form.department" class="field-input"
              placeholder="如: 档案馆" /></div>
          <div class="form-group"><label>角色</label><select v-model="form.role" class="field-input">
              <option value="reviewer">审核员</option>
              <option value="archive_admin">档案馆员</option>
              <option value="system_admin">系统管理员</option>
            </select></div>
          <div class="form-group"><label>初始密码</label><input v-model="form.password" class="field-input" type="password"
              placeholder="不少于12个字符" /></div>
          <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
          <div style="display:flex;gap:12px;justify-content:flex-end;margin-top:20px">
            <button class="btn-sm" @click="showCreate = false">取消</button>
            <button class="btn-primary" :disabled="creating" @click="doCreate">{{ creating ? '创建中...' : '确定' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <div v-if="showEdit" class="modal-overlay" @click.self="showEdit = false">
      <div class="modal-card">
        <div class="modal-head">
          <h3>编辑用户</h3><button class="modal-close" @click="showEdit = false"><svg width="18" height="18"
              viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg></button>
        </div>
        <div class="modal-body">
          <div class="form-group"><label>姓名</label><input v-model="editForm.name" class="field-input" /></div>
          <div class="form-group"><label>部门</label><input v-model="editForm.department" class="field-input" /></div>
          <div class="form-group"><label>角色</label><select v-model="editForm.role" class="field-input">
              <option value="reviewer">审核员</option>
              <option value="archive_admin">档案馆员</option>
              <option value="system_admin">系统管理员</option>
            </select></div>
          <div style="display:flex;gap:12px;justify-content:flex-end;margin-top:20px">
            <button class="btn-sm" @click="showEdit = false">取消</button>
            <button class="btn-primary" @click="doEdit">保存</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 重置密码弹窗 -->
    <div v-if="showResetPwd" class="modal-overlay" @click.self="showResetPwd = false">
      <div class="modal-card">
        <div class="modal-head">
          <h3>重置密码 — {{ resetTarget?.username }}</h3><button class="modal-close" @click="showResetPwd = false"><svg
              width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg></button>
        </div>
        <div class="modal-body">
          <div class="form-group"><label>新密码（不少于12个字符）</label><input v-model="resetPwd" class="field-input"
              type="password" /></div>
          <div style="display:flex;gap:12px;justify-content:flex-end;margin-top:20px">
            <button class="btn-sm" @click="showResetPwd = false">取消</button>
            <button class="btn-primary" @click="doResetPassword">重置</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { userApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { passwordComplexityError } from '@/constants'

const users = ref<any[]>([])
const showCreate = ref(false)
let fetchSeq = 0  // 请求序号，防快速切换筛选/翻页时旧响应覆盖新数据
const creating = ref(false)
const errorMsg = ref('')
const page = ref(1); const pageSize = ref(20); const total = ref(0)
const roleFilter = ref(''); const statusFilter = ref(''); const searchKeyword = ref('')
const selectedIds = ref<number[]>([])

const form = reactive({ username: '', name: '', department: '', role: 'reviewer', password: '' })

// Edit
const showEdit = ref(false)
const editForm = reactive({ id: 0, name: '', department: '', role: '' })
function openEdit(u: any) {
  editForm.id = u.id; editForm.name = u.name; editForm.department = u.department || ''; editForm.role = u.role
  showEdit.value = true
}
async function doEdit() {
  try {
    await userApi.update(editForm.id, { name: editForm.name, department: editForm.department, role: editForm.role })
    ElMessage.success('已保存')
    showEdit.value = false
    fetchUsers()
  } catch { ElMessage.error('保存失败') }
}

// Reset password
const showResetPwd = ref(false)
const resetTarget = ref<any>(null)
const resetPwd = ref('')
function openResetPwd(u: any) { resetTarget.value = u; resetPwd.value = ''; showResetPwd.value = true }
async function doResetPassword() {
  const pwdErr = passwordComplexityError(resetPwd.value || '')
  if (pwdErr) { ElMessage.warning(pwdErr); return }
  try {
    const res = await userApi.resetPassword(resetTarget.value.id, resetPwd.value)
    if (res.data && res.data.error) { ElMessage.error(res.data.error); return }
    ElMessage.success('密码已重置')
    showResetPwd.value = false
  } catch { ElMessage.error('重置失败') }
}

function roleLabel(r: string) { return { system_admin: '系统管理员', archive_admin: '档案馆员', reviewer: '审核员' }[r] || r }

onMounted(() => fetchUsers())

async function fetchUsers() {
  const seq = ++fetchSeq
  try {
    const res = await userApi.list({
      page: page.value, page_size: pageSize.value,
      role: roleFilter.value || undefined,
      is_active: statusFilter.value ? statusFilter.value === '1' : undefined,
      keyword: searchKeyword.value || undefined,
    })
    if (seq !== fetchSeq) return
    users.value = res.data.items || []
    total.value = res.data.total || 0
  } catch { /* ignore */ }
}

function openCreate() { form.username = ''; form.name = ''; form.department = ''; form.role = 'reviewer'; form.password = ''; errorMsg.value = ''; showCreate.value = true }

async function doCreate() {
  if (!form.username || !form.name || !form.password) { errorMsg.value = '请填写所有字段'; return }
  const pwdErr = passwordComplexityError(form.password)
  if (pwdErr) { errorMsg.value = pwdErr; return }
  creating.value = true; errorMsg.value = ''
  try {
    const res = await userApi.create({ username: form.username, name: form.name, role: form.role, password: form.password, department: form.department })
    if (res.data && res.data.error) { errorMsg.value = res.data.error; return }
    ElMessage.success(`用户 ${form.username} 已创建`)
    showCreate.value = false
    fetchUsers()
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail || e?.response?.data?.error || '创建失败'
  } finally { creating.value = false }
}

async function toggleUser(u: any) {
  try {
    await ElMessageBox.confirm(
      `确认${u.is_active ? '停用' : '启用'}用户「${u.name || u.username}」？`,
      '操作确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await userApi.toggleStatus(u.id, !u.is_active)
    u.is_active = !u.is_active
    ElMessage.success(u.is_active ? '已启用' : '已停用')
  } catch (e: any) {
    if (e !== 'cancel' && e?.action !== 'cancel') ElMessage.error('操作失败')
  }
}

// 批量选择与批量启用/停用（UM-004）
const allSelected = computed(() => users.value.length > 0 && users.value.every(u => selectedIds.value.includes(u.id)))
function toggleSelect(id: number) {
  const i = selectedIds.value.indexOf(id)
  if (i >= 0) selectedIds.value.splice(i, 1)
  else selectedIds.value.push(id)
}
function toggleAll() {
  if (allSelected.value) selectedIds.value = []
  else selectedIds.value = users.value.map(u => u.id)
}
async function batchStatus(active: boolean) {
  try {
    await ElMessageBox.confirm(
      `确认批量${active ? '启用' : '停用'} ${selectedIds.value.length} 个用户？`,
      '批量操作确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await userApi.batchStatus(selectedIds.value, active)
    ElMessage.success(`已批量${active ? '启用' : '停用'}`)
    selectedIds.value = []
    fetchUsers()
  } catch (e: any) {
    if (e !== 'cancel' && e?.action !== 'cancel') ElMessage.error('操作失败')
  }
}
</script>

<style scoped>
.page {
  max-width: var(--page-max);
  margin: 0 auto
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px
}

.page-head h2 {
  font-size: var(--fs-xl);
  font-weight: var(--fw-semibold);
  margin: 0
}

.btn-primary {
  height: 36px;
  padding: 0 20px;
  border-radius: var(--r-sm);
  border: none;
  background: var(--c-accent);
  color: #fff;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  cursor: pointer
}

.btn-primary:hover {
  background: var(--c-accent-hover);
  opacity: 1
}

.btn-primary:disabled {
  opacity: .6;
  cursor: not-allowed
}

.card {
  background: var(--c-surface);
  border-radius: var(--r-lg);
  border: 1px solid var(--c-border);
  overflow: hidden
}

.data-table {
  width: 100%;
  border-collapse: collapse
}

.data-table th {
  padding: 12px 16px;
  text-align: left;
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  color: var(--c-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--c-bg);
  border-bottom: 1px solid var(--c-border)
}

.data-table td {
  padding: 12px 16px;
  font-size: var(--fs-sm);
  color: var(--c-text);
  border-bottom: 1px solid var(--c-border-light)
}

.mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: var(--fs-xs)
}

.btn-sm {
  height: 30px;
  padding: 0 14px;
  border-radius: var(--r-sm);
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text-secondary);
  font-size: var(--fs-xs);
  cursor: pointer
}

.btn-sm:hover {
  border-color: var(--c-accent);
  color: var(--c-accent)
}

.risk-tag {
  padding: 2px 10px;
  border-radius: var(--r-full);
  font-size: 11px;
  font-weight: var(--fw-bold)
}

.risk-tag--low {
  background: #F0FDF4;
  color: var(--c-success)
}

.risk-tag--high {
  background: #FEF2F2;
  color: var(--c-danger)
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  backdrop-filter: blur(4px)
}

.modal-card {
  width: 480px;
  background: var(--c-surface);
  border-radius: var(--r-lg);
  box-shadow: var(--s-dropdown)
}

.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--c-border-light)
}

.modal-head h3 {
  margin: 0;
  font-size: var(--fs-lg)
}

.modal-close {
  width: 32px;
  height: 32px;
  border-radius: var(--r-sm);
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-text-muted)
}

.modal-close:hover {
  background: var(--c-bg)
}

.modal-body {
  padding: 24px
}

.form-group {
  margin-bottom: 16px
}

.form-group label {
  display: block;
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  color: var(--c-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px
}

.field-input {
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-sm);
  font-size: var(--fs-base);
  background: var(--c-bg);
  outline: none;
  font-family: var(--font);
  width: 100%
}

.field-input:focus {
  border-color: var(--c-accent)
}

.error-msg {
  padding: 8px 12px;
  background: #FEF2F2;
  color: var(--c-danger);
  border-radius: var(--r-sm);
  font-size: var(--fs-sm)
}

.pager {
  margin-top: 16px;
  display: flex;
  justify-content: center
}

.user-count {
  font-size: var(--fs-base);
  font-weight: var(--fw-normal);
  color: var(--c-text-muted)
}

.filter-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 14px;
  margin-bottom: 16px;
  background: var(--c-surface);
  border-radius: var(--r-md);
  border: 1px solid var(--c-border)
}

.filter-select {
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-sm);
  font-size: var(--fs-xs);
  background: var(--c-bg);
  outline: none;
  cursor: pointer
}

.filter-input {
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-sm);
  font-size: var(--fs-xs);
  background: var(--c-bg);
  outline: none;
  width: 160px
}

.btn-accent-sm {
  height: 32px;
  padding: 0 14px;
  border-radius: var(--r-sm);
  border: none;
  background: var(--c-accent);
  color: #fff;
  font-size: var(--fs-xs);
  cursor: pointer
}

.btn-accent-sm:hover {
  background: var(--c-accent-hover)
}

.online-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle
}

.dot--on {
  background: var(--c-success)
}

.dot--off {
  background: var(--c-text-muted)
}

.text-sm {
  font-size: var(--fs-xs);
  color: var(--c-text-secondary)
}

.selected-badge {
  padding: 2px 12px;
  border-radius: var(--r-full);
  font-size: var(--fs-xs);
  background: var(--c-accent-light);
  color: var(--c-accent);
  font-weight: var(--fw-semibold)
}
</style>
