/* ---- 与后端 Pydantic schema 对齐的 TS 类型 ---- */

export type ProjectStatus = 'active' | 'archived'
export type TaskStatus = 'todo' | 'in_progress' | 'done'
export type TaskPriority = 'low' | 'medium' | 'high'

export interface User {
  id: number
  username: string
  email: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Project {
  id: number
  name: string
  description: string | null
  status: ProjectStatus
  start_date: string | null
  end_date: string | null
  created_at: string
}

export interface ProjectCreate {
  name: string
  description?: string | null
  start_date?: string | null
  end_date?: string | null
}

export interface ProjectUpdate {
  name?: string
  description?: string | null
  status?: ProjectStatus
  start_date?: string | null
  end_date?: string | null
}

export interface Milestone {
  id: number
  project_id: number
  name: string
  due_date: string | null
  status: string
  created_at: string
}

export interface MilestoneCreate {
  name: string
  due_date?: string | null
}

export interface MilestoneUpdate {
  name?: string
  due_date?: string | null
  status?: string
}

export interface Task {
  id: number
  project_id: number
  milestone_id: number | null
  name: string
  description: string | null
  status: TaskStatus
  priority: TaskPriority
  progress: number
  start_date: string | null
  due_date: string | null
  completed_at: string | null
  estimated_hours: number | null
  created_at: string
  overdue: boolean
}

export interface TaskCreate {
  name: string
  description?: string | null
  milestone_id?: number | null
  priority?: TaskPriority
  status?: TaskStatus
  progress?: number
  start_date?: string | null
  due_date?: string | null
  estimated_hours?: number | null
}

export interface TaskUpdate {
  name?: string
  description?: string | null
  milestone_id?: number | null
  priority?: TaskPriority
  status?: TaskStatus
  progress?: number
  start_date?: string | null
  due_date?: string | null
  estimated_hours?: number | null
}

export interface TaskBulkUpdate {
  ids: number[]
  data: TaskUpdate
}

export interface OverdueTask {
  id: number
  name: string
  due_date: string | null
  days_late: number
  priority: TaskPriority
}

export interface ProjectStats {
  total_tasks: number
  done_tasks: number
  in_progress_tasks: number
  todo_tasks: number
  progress: number
  weighted_progress: number
  estimated_hours_total: number | null
  overdue_tasks: OverdueTask[]
}

export interface ProgressSnapshotPoint {
  date: string
  total_tasks: number
  done_tasks: number
  progress: number
  weighted_progress: number
}

export interface BurndownPoint {
  date: string
  ideal_remaining: number
  actual_remaining: number
}

export interface DashboardOverview {
  total_projects: number
  active_projects: number
  projects: DashboardProjectCard[]
  overdue_tasks: DashboardOverdueItem[]
  recent_logs: DashboardRecentLog[]
  active_sessions: DashboardSession[]
  today_completed: number
}

export interface DashboardProjectCard {
  project_id: number
  name: string
  status: ProjectStatus
  progress: number
  weighted_progress: number
  total_tasks: number
  done_tasks: number
  overdue_count: number
}

export interface DashboardOverdueItem {
  id: number
  name: string
  project_id: number
  project_name: string | null
  due_date: string | null
  days_late: number
  priority: TaskPriority
}

export interface DashboardRecentLog {
  id: number
  project_id: number
  project_name: string | null
  entry_type: DevLogType
  title: string | null
  author: string | null
  created_at: string
}

export interface DashboardSession {
  id: number
  project_id: number
  project_name: string | null
  title: string | null
  log_count: number
  started_at: string
}

export interface GanttDependency {
  task_id: number
  depends_on_task_id: number
}

export interface GanttTask {
  id: string
  name: string
  start: string
  end: string
  progress: number
  dependencies: string
  overdue: boolean
  status: TaskStatus
}

export interface GanttData {
  tasks: GanttTask[]
  project_start: string
  project_end: string
}

export interface ApiKey {
  id: number
  name: string
  prefix: string
  created_at: string
  last_used_at: string | null
  revoked_at: string | null
}

export interface ApiKeyCreated {
  id: number
  name: string
  key: string
  prefix: string
}

/* ---- 开发记录（DevLog / DevSession） ---- */

export type DevLogType =
  | 'progress'
  | 'difficulty'
  | 'todo'
  | 'decision'
  | 'blocker'
  | 'milestone'
  | 'note'

export interface DevLog {
  id: number
  project_id: number
  session_id: number | null
  entry_type: DevLogType
  status: string
  severity: string | null
  title: string
  content: string | null
  related_task_ids: number[]
  git_ref: string | null
  author: string
  created_at: string
  updated_at: string
  resolved_at: string | null
}

export interface DevLogCreate {
  entry_type?: DevLogType
  status?: string
  severity?: string | null
  title: string
  content?: string | null
  related_task_ids?: number[] | null
  git_ref?: string | null
  session_id?: number | null
}

export interface DevLogUpdate {
  entry_type?: DevLogType
  status?: string
  severity?: string | null
  title?: string
  content?: string | null
  related_task_ids?: number[] | null
  git_ref?: string | null
}

export interface DevLogStats {
  total: number
  today_count: number
  open_todos: number
  open_difficulties: number
  open_blockers: number
  decisions: number
  type_counts: Record<DevLogType, number>
  latest_activity: string | null
}

export interface DevSession {
  id: number
  project_id: number
  title: string | null
  started_at: string
  ended_at: string | null
  summary: string | null
  author: string
  created_at: string
  log_count: number
}

export interface DevSessionCreate {
  title?: string | null
}

export interface DevReport {
  text: string
}

/* ---- 搜索 ---- */

export interface SearchResultItem {
  type: 'project' | 'task' | 'milestone'
  id: number
  name: string
  description: string | null
  project_id: number | null
  project_name: string | null
  status: string | null
  due_date: string | null
}

export interface SearchResponse {
  items: SearchResultItem[]
  total: number
}
