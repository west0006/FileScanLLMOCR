<template>
  <div class="online-page">
    <div class="page-head">
      <h2>在线用户</h2>
      <span class="page-head-count">{{ users.length }} 人在线</span>
    </div>

    <div class="online-grid">
      <div v-for="u in users" :key="u.account" class="online-card">
        <div class="online-card-top">
          <div class="online-avatar" :class="'avatar--' + u.roleColor">{{ u.name[0] }}</div>
          <div class="online-status" :class="u.idle ? 'status--idle' : 'status--active'"></div>
        </div>
        <div class="online-info">
          <h4>{{ u.name }}</h4>
          <span class="online-role">{{ u.role }}</span>
          <span class="online-dept">{{ u.dept }}</span>
          <div class="online-meta">
            <span>@{{ u.account }}</span>
          </div>
        </div>
      </div>
      <div v-if="users.length === 0" class="empty-state">
        <p>暂无在线用户</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { userApi } from '@/api'

const users = ref<any[]>([])

function roleLabel(r: string): string {
  return { system_admin: '系统管理员', archive_admin: '档案管理员', reviewer: '审核员' }[r] || r
}

onMounted(async () => {
  try {
    const res = await userApi.listOnline?.() || await userApi.list({})
    users.value = (res.data.items || []).map((u: any) => ({
      name: u.name || u.username,
      account: u.username,
      role: roleLabel(u.role),
      dept: u.department || '',
      roleColor: u.role === 'system_admin' ? 'green' : u.role === 'archive_admin' ? 'purple' : 'amber',
      idle: !u.is_active,
    }))
  } catch {
    users.value = [
      { name: '管理员', account: 'admin', role: '系统管理员', dept: '档案馆', roleColor: 'green', idle: false },
    ]
  }
})
</script>

<style scoped>
.online-page { max-width: var(--page-max); margin: 0 auto; }
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
.online-details { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--c-border-light); }
.od-row { display: flex; justify-content: space-between; align-items: center; font-size: var(--fs-xs); color: var(--c-text-secondary); padding: 3px 0; }
.od-row span { color: var(--c-text-muted); }
.od-row code { font-family: 'SF Mono','Fira Code',monospace; font-size: 11px; color: var(--c-text); }
</style>
