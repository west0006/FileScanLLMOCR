<template>
  <div class="page">
    <div class="page-head"><h2>角色权限</h2></div>
    <div class="card">
      <table class="data-table">
        <thead><tr><th>角色名称</th><th>描述</th><th style="width:80px">用户数</th><th style="width:120px">操作</th></tr></thead>
        <tbody>
          <tr v-for="r in roles" :key="r.id">
            <td class="font-medium">{{ r.name }}</td><td>{{ r.description }}</td><td>{{ r.user_count }}</td>
            <td><button class="btn-sm" @click="editRole(r)">权限配置</button></td>
          </tr>
          <tr v-if="roles.length === 0"><td colspan="4" class="table-empty">暂无角色数据</td></tr>
        </tbody>
      </table>
    </div>

    <!-- 权限配置弹窗 -->
    <AppModal :visible="showPerm" :title="'权限配置 - ' + editingRole?.name" @close="showPerm=false" width="480px">
      <div class="perm-grid">
        <label v-for="p in permModules" :key="p.key" class="perm-item">
          <input type="checkbox" v-model="permForm[p.key]" />
          <span class="perm-label">{{ p.label }}</span>
          <span class="perm-desc">{{ p.desc }}</span>
        </label>
      </div>
      <template #footer>
        <button class="btn-sm" @click="showPerm=false">取消</button>
        <button class="btn-primary" @click="savePerm">保存</button>
      </template>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { userApi } from '@/api'
import { ElMessage } from 'element-plus'
import AppModal from '@/components/AppModal.vue'

const roles = ref<any[]>([])
const showPerm = ref(false)
const editingRole = ref<any>(null)
const permForm = reactive<Record<string, boolean>>({})

const permModules = [
  { key: 'search', label: '智能检索', desc: '关键词/语义/高级检索' },
  { key: 'ocr', label: 'OCR识别', desc: '创建任务、查看结果' },
  { key: 'review', label: 'AI预审', desc: '审核工作台、任务管理' },
  { key: 'sync', label: '数据同步', desc: '同步配置与监控' },
  { key: 'user', label: '用户管理', desc: '用户增删改查' },
  { key: 'log', label: '操作日志', desc: '日志查询与审计' },
  { key: 'stats', label: '查询统计', desc: '利用统计分析' },
]

function roleLabel(name: string) {
  return { system_admin: '系统管理员', archive_admin: '档案管理员', reviewer: '审核员' }[name] || name
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

function editRole(r: any) {
  editingRole.value = r
  const perms = r.permissions || {}
  permModules.forEach(p => { permForm[p.key] = perms.all || !!perms[p.key] })
  showPerm.value = true
}

async function savePerm() {
  if (!editingRole.value) return
  try {
    const perms: Record<string, boolean> = {}
    permModules.forEach(p => { perms[p.key] = permForm[p.key] })
    await userApi.updatePermissions(editingRole.value.id, perms)
    ElMessage.success('权限已保存')
    showPerm.value = false
  } catch { ElMessage.error('保存失败') }
}
</script>

<style scoped>
.page{max-width:var(--page-max);margin:0 auto}.page-head{margin-bottom:20px}.page-head h2{font-size:var(--fs-xl);font-weight:var(--fw-semibold);margin:0}.card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);overflow:hidden}.data-table{width:100%;border-collapse:collapse}.data-table th{padding:12px 16px;text-align:left;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);text-transform:uppercase;letter-spacing:0.5px;background:var(--c-bg);border-bottom:1px solid var(--c-border)}.data-table td{padding:12px 16px;font-size:var(--fs-sm);color:var(--c-text);border-bottom:1px solid var(--c-border-light)}.btn-sm{height:30px;padding:0 14px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-xs);cursor:pointer}.btn-sm:hover{border-color:var(--c-accent);color:var(--c-accent)}.btn-primary{height:32px;padding:0 20px;border-radius:var(--r-sm);border:none;background:var(--c-accent);color:#fff;font-size:var(--fs-sm);cursor:pointer}.btn-primary:hover{background:var(--c-accent-hover)}.font-medium{font-weight:var(--fw-medium)}.table-empty{padding:48px;text-align:center;color:var(--c-text-muted)}
.perm-grid{display:flex;flex-direction:column;gap:10px}.perm-item{display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--c-bg);border-radius:var(--r-sm);cursor:pointer;transition:background var(--t-fast)}.perm-item:hover{background:var(--c-border-light)}.perm-item input[type=checkbox]{width:18px;height:18px;accent-color:var(--c-accent);cursor:pointer}.perm-label{font-size:var(--fs-sm);font-weight:var(--fw-medium);color:var(--c-text);min-width:80px}.perm-desc{font-size:var(--fs-xs);color:var(--c-text-muted)}
</style>
