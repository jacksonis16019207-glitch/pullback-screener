// 決算日。バッチが取れなかった銘柄は、手入力した日付で補う。
import { addDays, earningsSoon, todayIso } from './businessDays'
import { isRecord } from './guards'

export type ManualEarnings = {
  date: string // 決算発表予定日（YYYY-MM-DD）
  enteredAt: string
}

// 画面に出す決算日の情報
export type EarningsView = {
  date: string | null
  sourceLabel: string | null
  soon: boolean | null // true=決算が近い, null=決算日不明
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/
export const KEEP_PAST_DAYS = 30 // 決算日から30日たった入力は捨てる

// localStorage から読んだ値を、安全な形に直す。形が違うもの・古いものは捨てる。
export function parseManualEarnings(
  raw: unknown,
  today: string = todayIso(),
): Record<string, ManualEarnings> {
  const result: Record<string, ManualEarnings> = {}
  if (!isRecord(raw) || !isRecord(raw.entries)) return result

  const oldest = addDays(today, -KEEP_PAST_DAYS)
  for (const [code, value] of Object.entries(raw.entries)) {
    if (!isRecord(value)) continue
    const { date, enteredAt } = value
    if (typeof date !== 'string' || !DATE_RE.test(date) || Number.isNaN(Date.parse(date))) continue
    if (typeof enteredAt !== 'string' || date < oldest) continue
    result[code] = { date, enteredAt }
  }
  return result
}

// バッチの決算日があればそれを使い、なければ手入力の日付を使う。
export function resolveEarnings(
  batch: { date: string | null; source: string | null; soon: boolean | null },
  manual: ManualEarnings | null,
  baseDate: string,
  within: number,
  nonTrading: ReadonlySet<string>,
): EarningsView {
  if (batch.date !== null) {
    return { date: batch.date, sourceLabel: batch.source, soon: batch.soon }
  }
  if (manual !== null) {
    return {
      date: manual.date,
      sourceLabel: '手入力',
      soon: earningsSoon(baseDate, manual.date, within, nonTrading),
    }
  }
  return { date: null, sourceLabel: null, soon: null }
}

export function earningsText(e: EarningsView): string {
  if (e.date === null) return '不明'
  return e.sourceLabel ? `${e.date}（${e.sourceLabel}）` : e.date
}
