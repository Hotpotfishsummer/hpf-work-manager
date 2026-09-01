import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/AppLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/projects' },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
{
          path: '/',
          component: AppLayout,
          children: [
            {
              path: '',
              redirect: 'projects',
            },
            {
              path: 'dashboard',
              name: 'dashboard',
              component: () => import('@/views/DashboardView.vue'),
            },
            {
              path: 'projects',
              name: 'projects',
              component: () => import('@/views/ProjectListView.vue'),
            },
        {
          path: 'projects/:id',
          name: 'project-detail',
          component: () => import('@/views/ProjectDetailView.vue'),
          props: true,
        },
        {
          path: 'projects/:id/tasks',
          name: 'project-tasks',
          component: () => import('@/views/TaskBoardView.vue'),
          props: true,
        },
        {
          path: 'projects/:id/gantt',
          name: 'project-gantt',
          component: () => import('@/views/GanttView.vue'),
          props: true,
        },
        {
          path: 'projects/:id/logs',
          name: 'project-logs',
          component: () => import('@/views/DevLogView.vue'),
          props: true,
        },
        {
          path: 'keys',
          name: 'api-keys',
          component: () => import('@/views/ApiKeysView.vue'),
        },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue') },
  ],
})

// 设置 document.title
router.afterEach((to) => {
  if (to.name === 'not-found') {
    document.title = '未找到 · HPF Work Manager'
  } else {
    const base = 'HPF Work Manager'
    const names: Record<string, string> = {
      login: '登录',
      projects: '项目',
      dashboard: '进度总览',
      'project-detail': '项目概览',
      'project-tasks': '任务看板',
      'project-gantt': '甘特图',
      'project-logs': '开发记录',
      'api-keys': 'API Keys',
    }
    const name = names[to.name as string] ?? ''
    document.title = name ? `${name} · ${base}` : base
  }
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && auth.token) {
    return { path: '/projects' }
  }
})

export default router
