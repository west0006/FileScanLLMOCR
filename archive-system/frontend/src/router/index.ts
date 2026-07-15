import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { title: '登录', guest: true },
    },
    {
      path: '/',
      component: () => import('@/layout/MainLayout.vue'),
      redirect: '/home',
      children: [
        {
          path: 'home',
          name: 'Home',
          component: () => import('@/views/Home.vue'),
          meta: { title: '首页' },
        },
        {
          path: 'search',
          name: 'Search',
          component: () => import('@/views/search/SearchHome.vue'),
          meta: { title: '智能检索' },
        },
        {
          path: 'search/detail/:id',
          name: 'ArchiveDetail',
          component: () => import('@/views/search/ArchiveDetail.vue'),
          meta: { title: '档案详情' },
        },
        {
          path: 'ocr',
          name: 'OcrTasks',
          component: () => import('@/views/ocr/OcrTaskList.vue'),
          meta: { title: 'OCR 识别' },
        },
        {
          path: 'review',
          name: 'ReviewWorkbench',
          component: () => import('@/views/review/ReviewWorkbench.vue'),
          meta: { title: 'AI 预审工作台' },
        },
        {
          path: 'review/tasks',
          name: 'ReviewTasks',
          component: () => import('@/views/review/ReviewTaskList.vue'),
          meta: { title: '预审任务管理' },
        },
        {
          path: 'review/records',
          name: 'ReviewRecords',
          component: () => import('@/views/review/ReviewRecordList.vue'),
          meta: { title: '预审记录' },
        },
        {
          path: 'admin/users',
          name: 'UserManagement',
          component: () => import('@/views/admin/UserManagement.vue'),
          meta: { title: '用户管理' },
        },
        {
          path: 'admin/roles',
          name: 'RoleManagement',
          component: () => import('@/views/admin/RoleManagement.vue'),
          meta: { title: '角色权限' },
        },
        {
          path: 'admin/online',
          name: 'OnlineUsers',
          component: () => import('@/views/admin/OnlineUsers.vue'),
          meta: { title: '在线用户' },
        },
        {
          path: 'admin/sync',
          name: 'SyncManagement',
          component: () => import('@/views/admin/SyncManagement.vue'),
          meta: { title: '数据同步' },
        },
        {
          path: 'log',
          name: 'OperationLogs',
          component: () => import('@/views/log/OperationLogs.vue'),
          meta: { title: '操作日志' },
        },
        {
          path: 'stats',
          name: 'QueryStats',
          component: () => import('@/views/stats/QueryStats.vue'),
          meta: { title: '查询统计' },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/NotFound.vue'),
      meta: { title: '404' },
    },
  ],
})

// 路由守卫：未登录用户重定向到登录页
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.guest) {
    // 登录页：已登录用户直接进首页
    if (token) return next('/home')
    return next()
  }
  // 内页：未登录 → 登录页
  if (!token) return next('/login')
  next()
})

export default router
