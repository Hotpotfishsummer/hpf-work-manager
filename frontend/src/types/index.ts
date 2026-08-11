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
  overdue_tasks: OverdueTask[]
}

export interface BurndownPoint {
  date: string
  ideal_remaining: number
  actual_remaining: number
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
