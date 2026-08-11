import http from './http'
import type {
  AuthResponse,
  BurndownPoint,
  GanttData,
  Milestone,
  MilestoneCreate,
  MilestoneUpdate,
  Project,
  ProjectCreate,
  ProjectStats,
  ProjectUpdate,
  Task,
  TaskBulkUpdate,
  TaskCreate,
  TaskUpdate,
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
  list: () => http.get<Project[], Project[]>('/projects'),
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
  list: (pid: number, params?: { status?: string; overdue?: boolean }) =>
    http.get<Task[], Task[]>(`/projects/${pid}/tasks`, { params }),
  get: (id: number) => http.get<Task, Task>(`/tasks/${id}`),
  create: (pid: number, data: TaskCreate) =>
    http.post<Task, Task>(`/projects/${pid}/tasks`, data),
  update: (id: number, data: TaskUpdate) =>
    http.put<Task, Task>(`/tasks/${id}`, data),
  remove: (id: number) => http.delete<null, null>(`/tasks/${id}`),
  bulk: (data: TaskBulkUpdate) => http.post<null, null>('/tasks/bulk', data),
}

/* ---- 统计 / 进度 ---- */
export const statsApi = {
  project: (pid: number) => http.get<ProjectStats, ProjectStats>(`/projects/${pid}/stats`),
  burndown: (pid: number) =>
    http.get<BurndownPoint[], BurndownPoint[]>(`/projects/${pid}/burndown`),
  gantt: (pid: number) => http.get<GanttData, GanttData>(`/projects/${pid}/gantt`),
}
