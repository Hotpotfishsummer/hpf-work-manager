/**
 * CSV escaping utilities to prevent formula injection attacks.
 * See: https://owasp.org/www-community/attacks/CSV_Injection
 */

/**
 * Escape a value for safe CSV output.
 * Prepends a single quote to values starting with =, +, -, @, or tab/carriage return
 * to prevent formula injection in spreadsheet applications.
 */
export function csvEscape(value: unknown): string {
  if (value === null || value === undefined) {
    return ''
  }
  const str = String(value)
  // Check for formula injection prefixes
  if (/^[\=\+\-\@]/.test(str) || str.includes('\t') || str.includes('\r') || str.includes('\n')) {
    return `'${str}`
  }
  // Escape double quotes by doubling them
  if (str.includes('"')) {
    return `"${str.replace(/"/g, '""')}"`
  }
  // Wrap in quotes if contains comma, semicolon, or double quote
  if (/[,";]/.test(str)) {
    return `"${str}"`
  }
  return str
}

/**
 * Generate CSV content from headers and rows.
 */
export function generateCsv(headers: string[], rows: unknown[][]): string {
  const headerLine = headers.map(csvEscape).join(',')
  const rowLines = rows.map((row) => row.map(csvEscape).join(','))
  return [headerLine, ...rowLines].join('\n')
}