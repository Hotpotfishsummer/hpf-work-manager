import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'cockpit',
          component: () => import('@/views/CockpitView.vue'),
        },
        {
          path: 'ideas',
          name: 'idea-lab',
          component: () => import('@/views/IdeaLabView.vue'),
        },
        {
          path: 'quota',
          name: 'quota',
          component: () => import('@/views/QuotaView.vue'),
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
    document.title = '未找到 · HarnessPilot'
  } else {
    const base = 'HarnessPilot · AI Agent Cockpit'
    const names: Record<string, string> = {
      cockpit: '任务看板',
      'idea-lab': '灵感工坊 & Next Steps',
      quota: '5h 算力调度雷达',
      projects: '项目管理',
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

export default router
