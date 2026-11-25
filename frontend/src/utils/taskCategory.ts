/* 任务分类：与后端 TASK_CATEGORIES 一一对应（顺序即下拉里的展示顺序） */
export const TASK_CATEGORIES = [
  { value: 'feature', label: '新功能', icon: '✨' },
  { value: 'bugfix', label: '排错修复', icon: '🐛' },
  { value: 'refactor', label: '重构', icon: '🛠️' },
  { value: 'testing', label: '测试', icon: '🧪' },
  { value: 'docs', label: '文档', icon: '📄' },
  { value: 'devops', label: '运维部署', icon: '🚀' },
] as const

export type TaskCategory = (typeof TASK_CATEGORIES)[number]['value']

export const UNCATALOGUED = 'none'

export function categoryLabel(category: string | null | undefined): string {
  if (!category) return '未分类'
  return TASK_CATEGORIES.find((c) => c.value === category)?.label ?? category
}

export function categoryIcon(category: string | null | undefined): string {
  if (!category) return '📎'
  return TASK_CATEGORIES.find((c) => c.value === category)?.icon ?? '📎'
}
