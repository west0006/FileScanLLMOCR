<template>
  <div class="app-shell" :class="{ collapsed: sidebarCollapsed }">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <!-- Logo -->
      <div class="sidebar-brand">
        <div class="brand-icon" @click="sidebarCollapsed = !sidebarCollapsed">
          <svg width="24" height="24" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="7" fill="#10B981"/>
            <path d="M7 10h14M7 15h14M7 20h10" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <transition name="fade-slide">
          <div v-if="!sidebarCollapsed" class="brand-text">
            <span class="brand-title">档案管理系统</span>
            <span class="brand-sub">中南财经政法大学</span>
          </div>
        </transition>
      </div>

      <!-- 导航 -->
      <nav class="sidebar-nav">
        <template v-for="section in navSections" :key="section.label">
          <div class="nav-section">
            <span v-if="!sidebarCollapsed" class="nav-label">{{ section.label }}</span>
            <router-link
              v-for="item in section.items"
              :key="item.to"
              :to="item.to"
              class="nav-item"
              active-class="nav-item--active"
              :exact="item.exact"
              :title="sidebarCollapsed ? item.label : ''"
            >
              <span class="nav-icon" v-html="item.icon"></span>
              <transition name="fade-slide">
                <span v-if="!sidebarCollapsed" class="nav-text">{{ item.label }}</span>
              </transition>
            </router-link>
          </div>
        </template>
      </nav>

      <!-- 折叠按钮 -->
      <div class="sidebar-collapse-wrap">
        <button class="collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed" :title="sidebarCollapsed ? '展开菜单' : '折叠菜单'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" :style="{transform: sidebarCollapsed ? 'rotate(180deg)' : ''}">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="collapse-hint">折叠菜单</span>
        </button>
      </div>

      <!-- 底部用户 -->
      <div class="sidebar-footer">
        <div class="user-mini">
          <div class="user-avatar">{{ auth.user?.username?.[0]?.toUpperCase() || '管' }}</div>
          <transition name="fade-slide">
            <div v-if="!sidebarCollapsed" class="user-info">
              <span class="user-name">{{ auth.user?.username || '管理员' }}</span>
              <span class="user-role">{{ userRoleLabel || '—' }}</span>
            </div>
          </transition>
        </div>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <span class="topbar-title">{{ pageTitle }}</span>
        </div>
        <div class="topbar-right">
          <button class="btn-logout" @click="handleLogout">退出</button>
        </div>
      </header>

      <main class="content">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ROLE_LABELS } from '@/constants'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const sidebarCollapsed = ref(false)

// 底部用户角色：按当前用户真实角色显示（回退为原始角色标识）
const userRoleLabel = computed(() => ROLE_LABELS[auth.user?.role] || auth.user?.role || '')

onMounted(() => { auth.fetchPermissions() })

const pageTitle = computed(() => route.meta.title as string || '')

interface NavItem { to: string; label: string; icon: string; module?: string; exact?: boolean }
interface NavSection { label: string; items: NavItem[] }

const allNavSections: NavSection[] = [
  {
    label: '档案服务',
    items: [
      { to: '/', label: '首页', icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>', exact: true },
      { to: '/search', label: '智能检索', icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>', module: 'search' },
      { to: '/ocr', label: 'OCR 识别', icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>', module: 'ocr' },
    ]
  },
  {
    label: '开放预审',
    items: [
      { to: '/review', label: '预审工作台', icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>', module: 'review' },
      { to: '/review/tasks', label: '预审任务', icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>', module: 'review' },
      { to: '/review/records', label: '预审记录', icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>', module: 'review' },
    ]
  },
  {
    label: '系统管理',
    items: [
      { to: '/admin/users', label: '用户管理', icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>', module: 'user' },
      { to: '/admin/online', label: '在线用户', icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3" fill="currentColor"/></svg>', module: 'user' },
      { to: '/admin/roles', label: '角色权限', icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>', module: 'user' },
      { to: '/admin/sync', label: '数据同步', icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>', module: 'sync' },
    ]
  },
  {
    label: '监控',
    items: [
      { to: '/log', label: '操作日志', icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>', module: 'log' },
      { to: '/stats', label: '查询统计', icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>', module: 'stats' },
    ]
  },
]

// 按权限过滤菜单
const navSections = computed(() => {
  if (!auth.permissions || Object.keys(auth.permissions).length === 0) {
    return allNavSections // 尚未加载权限时显示全部（避免闪烁）
  }
  return allNavSections
    .map(section => ({
      ...section,
      items: section.items.filter(item => !item.module || auth.can(item.module)),
    }))
    .filter(section => section.items.length > 0)
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-shell {
  display: flex; height: 100vh; background: var(--c-bg);
  --sidebar-actual: var(--sidebar-w);
}
.app-shell.collapsed { --sidebar-actual: var(--sidebar-collapsed); }

/* ==================== 侧边栏 ==================== */
.sidebar {
  width: var(--sidebar-actual);
  background: var(--c-surface);
  border-right: 1px solid var(--c-border);
  display: flex; flex-direction: column; flex-shrink: 0;
  transition: width 0.2s cubic-bezier(0.4, 0, 0.2, 1); overflow: hidden;
  position: relative;
}

.sidebar-brand {
  display: flex; align-items: center; gap: 10px;
  padding: 18px 16px; border-bottom: 1px solid var(--c-border-light);
  min-height: 64px;
}
.brand-icon {
  flex-shrink: 0; cursor: pointer;
  transition: transform var(--t-fast);
}
.brand-icon:hover { transform: scale(1.05); }
.brand-text { display: flex; flex-direction: column; min-width: 0; white-space: nowrap; }
.brand-title { font-size: var(--fs-base); font-weight: var(--fw-semibold); color: var(--c-text); line-height: 1.3; }
.brand-sub { font-size: 11px; color: var(--c-text-muted); }

/* 折叠按钮区域 */
.sidebar-collapse-wrap {
  padding: 8px 14px;
  border-top: 1px solid var(--c-border-light);
}
.collapse-btn {
  width: 100%;
  height: 34px; padding: 0 12px;
  border-radius: var(--r-sm);
  border: 1px solid var(--c-border); background: var(--c-bg);
  cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;
  color: var(--c-text-secondary); transition: all var(--t-fast);
  white-space: nowrap;
}
.collapse-btn:hover {
  color: var(--c-accent); border-color: var(--c-accent);
  background: var(--c-accent-light);
}
.collapse-btn svg { transition: transform 0.2s ease; flex-shrink: 0; opacity: 0.6; }
.collapse-btn:hover svg { opacity: 1; }
.collapse-hint {
  font-size: var(--fs-sm); font-weight: var(--fw-medium);
  color: var(--c-text-muted);
}
.collapse-btn:hover .collapse-hint { color: var(--c-accent); }

/* 导航 */
.sidebar-nav { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 8px 0; }
.nav-section { padding: 4px 0; }
.nav-label {
  display: block; padding: 8px 16px 4px;
  font-size: 10px; font-weight: var(--fw-semibold);
  text-transform: uppercase; letter-spacing: 0.8px;
  color: var(--c-text-muted); white-space: nowrap;
}
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 14px; margin: 1px 12px;
  border-radius: var(--r-sm); font-size: var(--fs-sm);
  font-weight: var(--fw-medium); color: var(--c-text-secondary);
  text-decoration: none; transition: all var(--t-fast);
  white-space: nowrap;
}
.nav-item:hover { background: var(--c-bg); color: var(--c-text); }
.nav-item--active { background: var(--c-accent-light) !important; color: var(--c-accent) !important; }
.nav-icon { display: flex; align-items: center; justify-content: center; width: 20px; height: 20px; flex-shrink: 0; opacity: 0.55; transition: opacity var(--t-fast); }
.nav-item--active .nav-icon { opacity: 1; }
.nav-item:hover .nav-icon { opacity: 0.8; }

/* 底部 */
.sidebar-footer { padding: 10px 14px; border-top: 1px solid var(--c-border-light); }
.user-mini { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.user-avatar {
  width: 30px; height: 30px; border-radius: var(--r-sm);
  background: var(--c-accent); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: var(--fw-semibold); flex-shrink: 0;
}
.user-info { display: flex; flex-direction: column; min-width: 0; }
.user-name { font-size: var(--fs-sm); font-weight: var(--fw-medium); color: var(--c-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-role { font-size: 11px; color: var(--c-text-muted); }

/* ==================== 主区域 ==================== */
.main-area {
  flex: 1; display: flex; flex-direction: column; min-width: 0;
  margin-left: 0;
}

.topbar {
  height: var(--header-h); background: var(--c-surface);
  border-bottom: 1px solid var(--c-border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; flex-shrink: 0;
}
.topbar-title { font-size: var(--fs-lg); font-weight: var(--fw-semibold); color: var(--c-text); }
.btn-logout {
  height: 32px; padding: 0 16px; border-radius: var(--r-sm);
  border: 1px solid var(--c-border); background: var(--c-surface);
  color: var(--c-text-secondary); font-size: var(--fs-sm);
  font-weight: var(--fw-medium); cursor: pointer; transition: all var(--t-fast);
}
.btn-logout:hover { border-color: var(--c-danger); color: var(--c-danger); }

.content {
  flex: 1; overflow-y: auto; padding: var(--page-px, 32px);
}

/* 移动端：侧边栏自动折叠 */
@media (max-width: 768px) {
  .app-shell { --sidebar-actual: var(--sidebar-collapsed); }
  .content { padding: 16px; }
  .topbar { padding: 0 16px; }
}

/* ==================== 过渡类 ==================== */

/* 页面切换 — 快、跟手 */
.page-enter-active,
.page-leave-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.page-enter-from { opacity: 0; transform: translateY(4px); }
.page-leave-to { opacity: 0; transform: translateY(-2px); }

/* 侧边栏文字渐变 */
.fade-slide-enter-active,
.fade-slide-leave-active { transition: opacity 0.1s ease, max-width 0.1s ease; }
.fade-slide-enter-from,
.fade-slide-leave-to { opacity: 0; }
</style>
