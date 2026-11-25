import { describe, expect, it } from 'vitest'
import { TASK_CATEGORIES, categoryIcon, categoryLabel } from '@/utils/taskCategory'

describe('task category helpers', () => {
  it('与后端约定的 6 个分类一一对应', () => {
    expect(TASK_CATEGORIES.map((c) => c.value).sort()).toEqual(
      ['bugfix', 'devops', 'docs', 'feature', 'refactor', 'testing'],
    )
  })

  it('空值显示为未分类；未知值原样显示不丢信息', () => {
    expect(categoryLabel(null)).toBe('未分类')
    expect(categoryLabel(undefined)).toBe('未分类')
    expect(categoryLabel('testing')).toBe('测试')
    expect(categoryLabel('whatever')).toBe('whatever')
    expect(categoryIcon(null)).toBeTruthy()
    expect(categoryIcon('feature')).toBe('✨')
  })
})
