/** Format a numeric value to at most `decimals` decimal places, trimming trailing zeros. Returns '' for null/undefined. */
export function fmtNum(v: unknown, decimals = 2): string {
  if (v == null || v === '') return ''
  const n = Number(v)
  if (isNaN(n)) return String(v)
  return parseFloat(n.toFixed(decimals)).toString()
}

/** Convert "2024-01-15" or "2024-01-15T..." to "15/01/2024". Returns the original string if unrecognised. */
export function fmtDate(v: unknown): string {
  if (!v) return ''
  const s = String(v)
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return s
  return `${m[3]}/${m[2]}/${m[1]}`
}
