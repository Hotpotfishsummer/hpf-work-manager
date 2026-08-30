/**
 * Pagination utilities for handling paginated data.
 */

export interface PaginationParams {
  page: number
  pageSize: number
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
  hasNext: boolean
  hasPrev: boolean
}

/**
 * Calculate pagination metadata.
 */
export function paginate<T>(
  items: T[],
  params: PaginationParams
): PaginatedResult<T> {
  const { page, pageSize } = params
  const total = items.length
  const totalPages = Math.ceil(total / pageSize)
  const start = (page - 1) * pageSize
  const end = start + pageSize
  const paginatedItems = items.slice(start, end)

  return {
    items: paginatedItems,
    total,
    page,
    pageSize,
    totalPages,
    hasNext: page < totalPages,
    hasPrev: page > 1,
  }
}

/**
 * Generate page numbers for pagination UI.
 * Returns array of page numbers and ellipsis markers.
 */
export function getPageNumbers(
  currentPage: number,
  totalPages: number,
  maxVisible: number = 5
): (number | 'ellipsis')[] {
  if (totalPages <= maxVisible) {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
  }

  const half = Math.floor((maxVisible - 2) / 2) // Reserve 2 slots for first/last
  let start = Math.max(2, currentPage - half)
  let end = Math.min(totalPages - 1, start + maxVisible - 3) // -3 for first, last, and at least one ellipsis

  if (end - start + 1 < maxVisible - 2) {
    start = Math.max(2, end - maxVisible + 3)
  }

  const pages: (number | 'ellipsis')[] = [1]

  if (start > 2) {
    pages.push('ellipsis')
  }

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  if (end < totalPages - 1) {
    pages.push('ellipsis')
  }

  pages.push(totalPages)

  return pages
}