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
    { path: '/:pathMatch(.*)*', redirect: '/projects' },
  ],
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
