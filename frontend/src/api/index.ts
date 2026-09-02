import http from './http'
import type {
  ApiKey,
  ApiKeyCreated,
  AuthResponse,
  BurndownPoint,
  DashboardOverview,
  DevLog,
  DevLogCreate,
  DevLogStats,
  DevLogUpdate,
  DevReport,
  DevSession,
  DevSessionCreate,
  GanttData,
  Milestone,
  MilestoneCreate,
  MilestoneUpdate,
  Project,
  ProjectCreate,
  ProjectStats,
  ProgressSnapshotPoint,
  ProjectUpdate,
  SearchResponse,
  SearchResultItem,
  Task,
  TaskBulkUpdate,
  TaskCreate,
  TaskUpdate,
  TaskComment,
  User,
} from '@/types'

/* ---- 认证 ---- */
export const authApi = {
  register: (data: { username: string; email: string; password: string }) =>
    http.post<AuthResponse, AuthResponse>('/auth/register', data),
  login: (data: { username: string; password: string }) =>
    http.post<AuthResponse, AuthResponse>('/auth/login', data),
  me: () => http.get<User, User>('/auth/me'),
}

/* ---- 项目 ---- */
export const projectApi = {
  list: (status?: 'active' | 'archived') =>
    http.get<Project[], Project[]>('/projects', status ? { params: { status } } : undefined),
  get: (id: number) => http.get<Project, Project>(`/projects/${id}`),
  create: (data: ProjectCreate) => http.post<Project, Project>('/projects', data),
  update: (id: number, data: ProjectUpdate) =>
    http.put<Project, Project>(`/projects/${id}`, data),
  remove: (id: number) => http.delete<null, null>(`/projects/${id}`),
}

/* ---- 里程碑 ---- */
export const milestoneApi = {
  list: (pid: number) => http.get<Milestone[], Milestone[]>(`/projects/${pid}/milestones`),
  create: (pid: number, data: MilestoneCreate) =>
    http.post<Milestone, Milestone>(`/projects/${pid}/milestones`, data),
  update: (id: number, data: MilestoneUpdate) =>
    http.put<Milestone, Milestone>(`/milestones/${id}`, data),
  remove: (id: number) => http.delete<null, null>(`/milestones/${id}`),
}

/* ---- 任务 ---- */
export const taskApi = {
  list: (pid: number, params?: { status?: string; overdue?: boolean; priority?: string; milestone_id?: number; search?: string; sort?: string }) =>
    http.get<Task[], Task[]>(`/projects/${pid}/tasks`, { params }),
  get: (id: number) => http.get<Task, Task>(`/tasks/${id}`),
  create: (pid: number, data: TaskCreate) =>
    http.post<Task, Task>(`/projects/${pid}/tasks`, data),
  update: (id: number, data: TaskUpdate) =>
    http.put<Task, Task>(`/tasks/${id}`, data),
  remove: (id: number) => http.delete<null, null>(`/tasks/${id}`),
  bulk: (data: TaskBulkUpdate) => http.post<null, null>('/tasks/bulk', data),
  // ---- 依赖关系 ----
  listDeps: (id: number) => http.get<number[], number[]>(`/tasks/${id}/dependencies`),
  addDep: (id: number, dependsOn: number) =>
    http.post<null, null>(`/tasks/${id}/dependencies`, { depends_on_task_id: dependsOn }),
  // 后端以请求体接收 depends_on_task_id（DELETE body），不能用 query 传
  removeDep: (id: number, dependsOn: number) =>
    http.request<null, null>({
      method: 'DELETE',
      url: `/tasks/${id}/dependencies`,
      data: { depends_on_task_id: dependsOn },
    }),
}

/* ---- 任务评论 ---- */
export const commentApi = {
  list: (taskId: number) => http.get<TaskComment[], TaskComment[]>(`/tasks/${taskId}/comments`),
  create: (taskId: number, content: string) =>
    http.post<TaskComment, TaskComment>(`/tasks/${taskId}/comments`, { content }),
  remove: (id: number) => http.delete<null, null>(`/comments/${id}`),
}

/* ---- 统计 / 进度 ---- */
export const statsApi = {
  project: (pid: number) => http.get<ProjectStats, ProjectStats>(`/projects/${pid}/stats`),
  burndown: (pid: number) =>
    http.get<BurndownPoint[], BurndownPoint[]>(`/projects/${pid}/burndown`),
  gantt: (pid: number) => http.get<GanttData, GanttData>(`/projects/${pid}/gantt`),
  overview: () => http.get<DashboardOverview, DashboardOverview>('/overview'),
  progressHistory: (pid: number, limit?: number) =>
    http.get<ProgressSnapshotPoint[], ProgressSnapshotPoint[]>(
      `/projects/${pid}/progress-history`,
      limit ? { params: { limit } } : undefined,
    ),
}

/* ---- API Key（AI 工具接入凭证） ---- */
export const keyApi = {
  list: () => http.get<ApiKey[], ApiKey[]>('/keys'),
  create: (data: { name: string }) =>
    http.post<ApiKeyCreated, ApiKeyCreated>('/keys', data),
  revoke: (id: number) => http.delete<null, null>(`/keys/${id}`),
}

/* ---- 开发记录 ---- */
export const devLogApi = {
  list: (
    pid: number,
    params?: { entry_type?: string; status?: string; since?: string; limit?: number; offset?: number },
  ) => http.get<DevLog[], DevLog[]>(`/projects/${pid}/logs`, { params }),
  create: (pid: number, data: DevLogCreate) =>
    http.post<DevLog, DevLog>(`/projects/${pid}/logs`, data),
  stats: (pid: number) =>
    http.get<DevLogStats, DevLogStats>(`/projects/${pid}/logs/stats`),
  report: (pid: number, start?: string | null, end?: string | null) =>
    http.post<DevReport, DevReport>(`/projects/${pid}/logs/report`, { start, end }),
  update: (id: number, data: DevLogUpdate) =>
    http.put<DevLog, DevLog>(`/logs/${id}`, data),
  resolve: (id: number) =>
    http.post<DevLog, DevLog>(`/logs/${id}/resolve`),
  remove: (id: number) => http.delete<null, null>(`/logs/${id}`),
}

/* ---- 搜索 ---- */
export const searchApi = {
  global: (q: string, projectId?: number) =>
    http.get<SearchResponse, SearchResponse>('/search', {
      params: { q, project_id: projectId },
    }),
}

/* ---- 开发会话 ---- */
export const devSessionApi = {
  list: (pid: number) =>
    http.get<DevSession[], DevSession[]>(`/projects/${pid}/sessions`),
  start: (pid: number, data: DevSessionCreate) =>
    http.post<DevSession, DevSession>(`/projects/${pid}/sessions`, data),
  end: (id: number, data: { summary?: string | null }) =>
    http.post<DevSession, DevSession>(`/sessions/${id}/end`, data),
}
