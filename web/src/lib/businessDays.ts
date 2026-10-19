// 営業日の数え方。Python側の logic.business_days_between と同じ考え方。
// 休場日（祝日・年末年始）は、バッチが watchlist.json の non_trading_days に入れて渡す。

// "2026-10-15" に n 日足した日付
export function addDays(iso: string, n: number): string {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

function isWeekday(iso: string): boolean {
  const day = new Date(`${iso}T00:00:00Z`).getUTCDay()
  return day !== 0 && day !== 6
}

// この端末の「今日」（YYYY-MM-DD）
export function todayIso(): string {
  const d = new Date()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}

// start の翌日から end まで（end を含む）の営業日数。end が start より前なら -1。
export function businessDaysBetween(
  start: string,
  end: string,
  nonTrading: ReadonlySet<string>,
): number {
  if (end < start) return -1
  let count = 0
  for (let d = addDays(start, 1); d <= end; d = addDays(d, 1)) {
    if (isWeekday(d) && !nonTrading.has(d)) count += 1
  }
  return count
}

// base から within 営業日以内に決算があれば true。決算日が分からなければ null。
export function earningsSoon(
  base: string,
  earnings: string | null,
  within: number,
  nonTrading: ReadonlySet<string>,
): boolean | null {
  if (earnings === null) return null
  const n = businessDaysBetween(base, earnings, nonTrading)
  return n >= 0 && n <= within
}
