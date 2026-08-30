import { describe, it, expect } from 'vitest'
import { csvEscape, generateCsv } from '@/utils/csv'

describe('csvEscape', () => {
  it('returns empty string for null', () => {
    expect(csvEscape(null)).toBe('')
  })

  it('returns empty string for undefined', () => {
    expect(csvEscape(undefined)).toBe('')
  })

  it('escapes formula injection with = prefix', () => {
    expect(csvEscape('=SUM(A1:A10)')).toBe("'=SUM(A1:A10)")
  })

  it('escapes formula injection with + prefix', () => {
    expect(csvEscape('+123')).toBe("'+123")
  })

  it('escapes formula injection with - prefix', () => {
    expect(csvEscape('-123')).toBe("'-123")
  })

  it('escapes formula injection with @ prefix', () => {
    expect(csvEscape('@SUM(A1:A10)')).toBe("'@SUM(A1:A10)")
  })

  it('escapes tab character', () => {
    expect(csvEscape('hello\tworld')).toBe("'hello\tworld")
  })

  it('escapes carriage return', () => {
    expect(csvEscape('hello\rworld')).toBe("'hello\rworld")
  })

  it('escapes newline', () => {
    expect(csvEscape('hello\nworld')).toBe("'hello\nworld")
  })

  it('escapes double quotes by doubling', () => {
    expect(csvEscape('hello "world"')).toBe('"hello ""world"""')
  })

  it('wraps in quotes when containing comma', () => {
    expect(csvEscape('hello,world')).toBe('"hello,world"')
  })

  it('wraps in quotes when containing semicolon', () => {
    expect(csvEscape('hello;world')).toBe('"hello;world"')
  })

  it('does not modify safe strings', () => {
    expect(csvEscape('hello world')).toBe('hello world')
    expect(csvEscape('123')).toBe('123')
    expect(csvEscape('hello-world')).toBe('hello-world')
  })

  it('handles numbers', () => {
    expect(csvEscape(123)).toBe('123')
    expect(csvEscape(45.67)).toBe('45.67')
  })

  it('handles boolean', () => {
    expect(csvEscape(true)).toBe('true')
    expect(csvEscape(false)).toBe('false')
  })
})

describe('generateCsv', () => {
  it('generates CSV with headers and rows', () => {
    const headers = ['Name', 'Value']
    const rows = [['Task 1', 100], ['Task 2', 200]]
    const result = generateCsv(headers, rows)
    expect(result).toBe('Name,Value\nTask 1,100\nTask 2,200')
  })

  it('escapes formula injection in rows', () => {
    const headers = ['Formula']
    const rows = [['=SUM(A1:A10)'], ['+123']]
    const result = generateCsv(headers, rows)
    expect(result).toBe("Formula\n'=SUM(A1:A10)\n'+123")
  })

  it('escapes commas in values', () => {
    const headers = ['Description']
    const rows = [['Task, with comma']]
    const result = generateCsv(headers, rows)
    expect(result).toBe('Description\n"Task, with comma"')
  })

  it('handles empty rows', () => {
    const headers = ['A', 'B']
    const rows: unknown[][] = []
    const result = generateCsv(headers, rows)
    expect(result).toBe('A,B')
  })
})