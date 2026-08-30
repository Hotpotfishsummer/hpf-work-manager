import { describe, it, expect } from 'vitest'
import { paginate, getPageNumbers, type PaginationParams } from '@/utils/pagination'

describe('paginate', () => {
  const items = Array.from({ length: 25 }, (_, i) => ({ id: i + 1, name: `Item ${i + 1}` }))

  it('returns first page with correct items', () => {
    const params: PaginationParams = { page: 1, pageSize: 10 }
    const result = paginate(items, params)

    expect(result.items).toHaveLength(10)
    expect(result.items[0].id).toBe(1)
    expect(result.items[9].id).toBe(10)
    expect(result.page).toBe(1)
    expect(result.pageSize).toBe(10)
    expect(result.total).toBe(25)
    expect(result.totalPages).toBe(3)
    expect(result.hasNext).toBe(true)
    expect(result.hasPrev).toBe(false)
  })

  it('returns second page with correct items', () => {
    const params: PaginationParams = { page: 2, pageSize: 10 }
    const result = paginate(items, params)

    expect(result.items).toHaveLength(10)
    expect(result.items[0].id).toBe(11)
    expect(result.items[9].id).toBe(20)
    expect(result.page).toBe(2)
    expect(result.hasNext).toBe(true)
    expect(result.hasPrev).toBe(true)
  })

  it('returns last page with remaining items', () => {
    const params: PaginationParams = { page: 3, pageSize: 10 }
    const result = paginate(items, params)

    expect(result.items).toHaveLength(5)
    expect(result.items[0].id).toBe(21)
    expect(result.items[4].id).toBe(25)
    expect(result.page).toBe(3)
    expect(result.hasNext).toBe(false)
    expect(result.hasPrev).toBe(true)
  })

  it('handles page size larger than total items', () => {
    const params: PaginationParams = { page: 1, pageSize: 50 }
    const result = paginate(items, params)

    expect(result.items).toHaveLength(25)
    expect(result.totalPages).toBe(1)
    expect(result.hasNext).toBe(false)
    expect(result.hasPrev).toBe(false)
  })

  it('handles empty array', () => {
    const params: PaginationParams = { page: 1, pageSize: 10 }
    const result = paginate([], params)

    expect(result.items).toHaveLength(0)
    expect(result.total).toBe(0)
    expect(result.totalPages).toBe(0)
    expect(result.hasNext).toBe(false)
    expect(result.hasPrev).toBe(false)
  })

  it('handles page beyond total pages', () => {
    const params: PaginationParams = { page: 5, pageSize: 10 }
    const result = paginate(items, params)

    expect(result.items).toHaveLength(0)
    expect(result.page).toBe(5)
    expect(result.hasNext).toBe(false)
    expect(result.hasPrev).toBe(true)
  })
})

describe('getPageNumbers', () => {
  it('returns all pages when total <= maxVisible', () => {
    expect(getPageNumbers(1, 3)).toEqual([1, 2, 3])
    expect(getPageNumbers(2, 5, 5)).toEqual([1, 2, 3, 4, 5])
  })

  it('shows first pages with ellipsis when near start', () => {
    expect(getPageNumbers(1, 10)).toEqual([1, 2, 3, 4, 'ellipsis', 10])
    expect(getPageNumbers(2, 10)).toEqual([1, 2, 3, 4, 'ellipsis', 10])
    expect(getPageNumbers(3, 10)).toEqual([1, 2, 3, 4, 'ellipsis', 10])
  })

  it('shows middle pages with ellipsis on both sides', () => {
    expect(getPageNumbers(5, 10)).toEqual([1, 'ellipsis', 4, 5, 6, 'ellipsis', 10])
    expect(getPageNumbers(6, 10)).toEqual([1, 'ellipsis', 5, 6, 7, 'ellipsis', 10])
  })

  it('shows last pages with ellipsis when near end', () => {
    expect(getPageNumbers(8, 10)).toEqual([1, 'ellipsis', 7, 8, 9, 10])
    expect(getPageNumbers(9, 10)).toEqual([1, 'ellipsis', 7, 8, 9, 10])
    expect(getPageNumbers(10, 10)).toEqual([1, 'ellipsis', 7, 8, 9, 10])
  })

  it('handles single page', () => {
    expect(getPageNumbers(1, 1)).toEqual([1])
  })

  it('handles two pages', () => {
    expect(getPageNumbers(1, 2)).toEqual([1, 2])
    expect(getPageNumbers(2, 2)).toEqual([1, 2])
  })

  it('respects custom maxVisible', () => {
    expect(getPageNumbers(5, 20, 7)).toEqual([1, 'ellipsis', 3, 4, 5, 6, 7, 'ellipsis', 20])
    expect(getPageNumbers(1, 20, 3)).toEqual([1, 2, 'ellipsis', 20])
  })
})