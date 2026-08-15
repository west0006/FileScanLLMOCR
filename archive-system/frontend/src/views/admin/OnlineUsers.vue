<template>
  <div class="online-page">
    <div class="stats-grid-sm">
      <div class="stat-card" :class="{active:statFilter==='all'}" @click="statFilter='all'"><div class="stat-icon stat-icon--green">●</div><div class="stat-label">当前在线</div><div class="stat-value">{{ users.length }}</div></div>
      <div class="stat-card" :class="{active:statFilter==='admin'}" @click="statFilter='admin'"><div class="stat-icon stat-icon--amber">👤</div><div class="stat-label">管理员在线</div><div class="stat-value">{{ adminCount }}</div></div>
      <div class="stat-card" :class="{active:statFilter==='reviewer'}" @click="statFilter='reviewer'"><div class="stat-icon stat-icon--purple"><IconSvg name="clip" size="15" /></div><div class="stat-label">审核员在线</div><div class="stat-value">{{ reviewerCount }}</div></div>
      <div class="stat-card stat-card--refresh" @click="loadUsers"><div class="stat-icon stat-icon--blue"><IconSvg name="refresh" size="15" /></div><div class="stat-label">手动刷新 · 30秒自动</div><div class="stat-value" style="font-size:14px"><IconSvg name="refresh" size="15" /> 刷新</div></div>
    </div>
    <div class="page-head">
      <h2>在线用户</h2>
      <span class="page-head-count">{{ filteredUsers.length }} 人在线</span>
    </div>

    <div class="online-grid">
      <div v-for="u in filteredUsers" :key="u.account" class="online-card" :class="{ 'online-card--self': u.isSelf }" @click="selectedUser = u">
        <div class="online-card-top">
          <div class="online-avatar" :class="'avatar--' + u.roleColor">{{ u.name[0] }}</div>
          <div class="online-status" :class="u.idle ? 'status--idle' : 'status--active'"></div>
        </div>
        <div class="online-info">
          <h4>
            {{ u.name }}
            <span v-if="u.isSelf" class="self-tag">当前管理员</span>
          </h4>
          <span class="online-role">{{ u.role }}</span>
          <span class="online-dept">{{ u.dept }}</span>
          <div class="online-meta">
            <span>@{{ u.account }}</span>
            <span class="meta-sep">·</span>
            <span>{{ u.sessionDuration }}</span>
          </div>
          <div class="online-details">
            <div class="od-row"><span>位置</span><span>{{ u.location || '档案馆办公区' }}</span></div>
            <div class="od-row"><span>当前操作</span><span>{{ u.currentPage || '在线用户页面' }}</span></div>
          </div>
        </div>
      </div>
      <div v-if="filteredUsers.length === 0" class="empty-state">
        <p>{{ statFilter !== 'all' ? '该角色暂无在线用户' : '暂无在线用户' }}</p>
      </div>
    </div>

    <!-- 用户详情弹窗 -->
    <AppModal :visible="!!selectedUser" :title="'用户详情 — ' + (selectedUser?.name || '')" @close="selectedUser = null" width="420px">
      <div v-if="selectedUser" class="detail-grid">
        <div><dt>用户名</dt><dd>@{{ selectedUser.account }}</dd></div>
        <div><dt>姓名</dt><dd>{{ selectedUser.name }}</dd></div>
        <div><dt>角色</dt><dd>{{ selectedUser.role }}</dd></div>
        <div><dt>部门</dt><dd>{{ selectedUser.dept || '—' }}</dd></div>
        <div><dt>会话时长</dt><dd>{{ selectedUser.sessionDuration }}</dd></div>
        <div><dt>位置</dt><dd>{{ selectedUser.location || '档案馆办公区' }}</dd></div>
        <div class="span-2"><dt>当前操作</dt><dd>{{ selectedUser.currentPage || '在线用户页面' }}</dd></div>
      </div>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { userApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { ROLE_LABELS } from '@/constants'
import AppModal from '@/components/AppModal.vue'

const auth = useAuthStore()
const users = ref<any[]>([])
const statFilter = ref('all')
const selectedUser = ref<any>(null)
let _timer: any = null

const adminCount = computed(() => users.value.filter(u => u.role?.includes('管理员')).length)
const reviewerCount = computed(() => users.value.filter(u => u.role === '审核员').length)

const filteredUsers = computed(() => {
  if (statFilter.value === 'all') return users.value
  if (statFilter.value === 'admin') return users.value.filter(u => u.role?.includes('管理员'))
  if (statFilter.value === 'reviewer') return users.value.filter(u => u.role === '审核员')
  return users.value
})

function roleLabel(r: string): string {
  return ROLE_LABELS[r] || r
}

function loadUsers() {
  userApi.listOnline?.().then(res => {
    const now = Date.now()
    users.value = (res.data.items || []).map((u: any) => {
      const sessionMs = now - (u.last_login_at ? new Date(u.last_login_at).getTime() : now)
      const mins = Math.floor(sessionMs / 60000)
      return {
        name: u.name || u.username,
        account: u.username,
        role: roleLabel(u.role),
        dept: u.department || '',
        roleColor: u.role === 'system_admin' ? 'green' : u.role === 'archive_admin' ? 'purple' : 'amber',
        idle: !u.is_active,
        isSelf: u.username === auth.user?.username,
        sessionDuration: mins < 60 ? `${mins} 分钟` : `${Math.floor(mins / 60)} 小时 ${mins % 60} 分钟`,
        location: '档案馆办公区',
        currentPage: '在线用户页面',
      }
    })
  }).catch(() => {
    if (users.value.length === 0) {
      users.value = [
        { name: '管理员', account: 'admin', role: '系统管理员', dept: '档案馆', roleColor: 'green', idle: false, isSelf: true, sessionDuration: '2 分钟', location: '档案馆办公区', currentPage: '在线用户页面' },
      ]
    }
  })
}

onMounted(() => { loadUsers(); _timer = setInterval(loadUsers, 30000) })
onUnmounted(() => { clearInterval(_timer) })
</script>

<style scoped>
.online-page { max-width: var(--page-max); margin: 0 auto; }
.stats-grid-sm{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
.stats-grid-sm .stat-card{padding:14px}.stats-grid-sm .stat-value{font-size:22px}
.page-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 24px; }
.page-head h2 { font-size: var(--fs-xl); font-weight: var(--fw-semibold); margin: 0; }
.page-head-count { font-size: var(--fs-base); color: var(--c-accent); font-weight: var(--fw-semibold); }

.online-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px;
}
.online-card {
  background: var(--c-surface); border-radius: var(--r-lg);
  border: 1px solid var(--c-border); padding: 20px;
  transition: all var(--t-fast);
}
.online-card:hover { box-shadow: var(--s-card-hover); }
.online-card-top { position: relative; margin-bottom: 12px; display: flex; align-items: center; }
.online-avatar {
  width: 44px; height: 44px; border-radius: var(--r-md);
  display: flex; align-items: center; justify-content: center;
  font-size: var(--fs-lg); font-weight: var(--fw-semibold); color: #fff;
}
.avatar--green { background: var(--c-accent); }
.avatar--purple { background: var(--c-purple); }
.avatar--amber { background: var(--c-warning); }
.online-status {
  position: absolute; bottom: 0; left: 34px;
  width: 12px; height: 12px; border-radius: 50%;
  border: 2px solid var(--c-surface);
}
.status--active { background: var(--c-success); }
.status--idle { background: var(--c-text-muted); }

.online-info h4 { font-size: var(--fs-base); font-weight: var(--fw-semibold); color: var(--c-text); margin: 0 0 2px; }
.online-role { font-size: var(--fs-xs); color: var(--c-accent); margin-right: 8px; }
.online-dept { font-size: var(--fs-xs); color: var(--c-text-muted); }
.online-details { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--c-border-light); }
.od-row { display: flex; justify-content: space-between; align-items: center; font-size: var(--fs-xs); color: var(--c-text-secondary); padding: 2px 0; }
.od-row span:first-child { color: var(--c-text-muted); }
.meta-sep { color: var(--c-border); margin: 0 2px; }
.online-meta { font-size: var(--fs-xs); color: var(--c-text-muted); margin-top: 2px; }
.self-tag { font-size: 10px; padding: 1px 6px; border-radius: var(--r-full); background: var(--c-accent-light); color: var(--c-accent); font-weight: var(--fw-medium); margin-left: 6px; vertical-align: middle; }
.online-card--self { border-color: var(--c-accent); background: var(--c-accent-light); }
.online-card { cursor: pointer; }
.stats-grid-sm .stat-card { cursor: pointer; }
.stats-grid-sm .stat-card.active { border-color: var(--c-accent); background: var(--c-accent-light); }
.stats-grid-sm .stat-card--refresh { cursor: pointer; }
.stats-grid-sm .stat-card--refresh:hover { border-color: var(--c-accent); }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 20px; margin: 0; }
.detail-grid dt { font-size: var(--fs-xs); color: var(--c-text-muted); font-weight: var(--fw-medium); margin-bottom: 2px; }
.detail-grid dd { font-size: var(--fs-sm); color: var(--c-text); margin: 0; font-weight: var(--fw-medium); }
.span-2 { grid-column: span 2; }
</style>
