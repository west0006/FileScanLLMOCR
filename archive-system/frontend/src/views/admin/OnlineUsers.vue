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
          <div class="online-details">
            <div class="od-row"><span>IP</span><code>{{ u.ip }}</code></div>
            <div class="od-row"><span>登录时间</span>{{ u.loginTime }}</div>
            <div class="od-row"><span>会话时长</span>{{ u.session }}</div>
            <div class="od-row"><span>当前页面</span>{{ u.activity }}</div>
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
import { ref } from 'vue'

const users = ref([
  { name:'张明华', account:'zhangmh', role:'系统管理员', dept:'信息管理部', ip:'10.20.1.100', loginTime:'2026-07-02 09:15', session:'2小时18分', activity:'首页', roleColor:'green', idle:false },
  { name:'李芳', account:'lifang', role:'审核员', dept:'档案馆', ip:'10.20.1.156', loginTime:'2026-07-02 08:40', session:'2小时53分', activity:'预审记录', roleColor:'purple', idle:false },
  { name:'陈小红', account:'chenxh', role:'审核员', dept:'收集指导室', ip:'10.20.1.142', loginTime:'2026-07-02 07:30', session:'4小时03分', activity:'AI预审工作台', roleColor:'purple', idle:false },
  { name:'王建国', account:'wangjg', role:'查档人员', dept:'查询利用室', ip:'10.20.1.88', loginTime:'2026-07-02 06:50', session:'4小时43分', activity:'—', roleColor:'amber', idle:true },
])
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
