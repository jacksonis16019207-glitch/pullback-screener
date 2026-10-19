// 材料ニュースの選択（単発／継続）に関する型と、判断の目安。
import { isRecord } from './guards'

export type NewsType =
  | 'earnings'
  | 'upgrade'
  | 'tob'
  | 'order'
  | 'alliance'
  | 'drug'
  | 'policy'
  | 'none'

export type NewsVerdict = 'oneoff' | 'continuing'

export type NewsSelection = {
  type: NewsType | null
  verdict: NewsVerdict | null // null = まだ判断していない
  decidedAt: string
}

export type NewsTypeInfo = {
  value: NewsType
  label: string
  lean: NewsVerdict | null // 材料の種類から決まる目安。決められないものは null
  hint: string
}

export const NEWS_TYPES: NewsTypeInfo[] = [
  {
    value: 'earnings',
    label: '決算',
    lean: null,
    hint: '発表翌日に飛んで終わりやすい。急騰前から数週間じわじわ上がっていたら継続、飛んだ1日だけなら単発。',
  },
  {
    value: 'upgrade',
    label: '上方修正',
    lean: null,
    hint: '決算と同様。急騰前から上昇が続いていれば継続、1日だけなら単発。',
  },
  {
    value: 'tob',
    label: 'TOB',
    lean: 'oneoff',
    hint: 'TOB価格に張り付いて値動きが固定される。常に単発（除外）。',
  },
  {
    value: 'order',
    label: '大型受注',
    lean: null,
    hint: '発表日に集中しやすく、単発寄り。受注後も数日上昇が続くなら継続。',
  },
  {
    value: 'alliance',
    label: '提携',
    lean: null,
    hint: '思惑で一時的に上がりやすく、単発寄り。事業の中核に関わり、上昇が続くなら継続。',
  },
  {
    value: 'drug',
    label: '新薬',
    lean: 'oneoff',
    hint: '承認・治験結果の一発材料。単発寄り。',
  },
  {
    value: 'policy',
    label: '政策材料',
    lean: 'continuing',
    hint: '業種全体に波及して数日〜数週間続く。同業他社も上がっていれば継続寄り。',
  },
  {
    value: 'none',
    label: 'ニュースなし',
    lean: 'continuing',
    hint: '地合い・需給で上がっている。継続。',
  },
]

export const VERDICT_LABEL: Record<NewsVerdict, string> = {
  oneoff: '単発（除外する）',
  continuing: '継続（残す）',
}

// 判断のための3つの質問（元の手順5の考え方）
export const QUESTIONS: string[] = [
  '急騰（+5%以上）は1日だけで、前後は小動きですか？ → はいなら単発寄り',
  '急騰の前から、数週間じわじわ上がっていましたか？ → はいなら継続寄り',
  '急騰のあとも、高値圏で出来高が続いていますか？ → はいなら継続寄り',
]

const TYPE_VALUES: string[] = NEWS_TYPES.map((t) => t.value)
const VERDICT_VALUES: string[] = ['oneoff', 'continuing']

// 選択は急騰日ごとのもの。古い選択は、一定の日数がたったら捨てる。
export const KEEP_DAYS = 45

export function selectionKey(code: string, surgeDate: string): string {
  return `${code}:${surgeDate}`
}

// 直近5営業日の中で、最も新しい急騰日（なければ null）
export function latestSurgeDate(item: { surge_dates: string[] }): string | null {
  return item.surge_dates.length > 0 ? item.surge_dates[item.surge_dates.length - 1] : null
}

// localStorage から読んだ値を、安全な形に直す。形が違うもの・古いものは捨てる。
export function parseEntries(raw: unknown, now: number = Date.now()): Record<string, NewsSelection> {
  const result: Record<string, NewsSelection> = {}
  if (!isRecord(raw) || !isRecord(raw.entries)) return result

  for (const [key, value] of Object.entries(raw.entries)) {
    if (!isRecord(value)) continue
    const { type, verdict, decidedAt } = value
    if (typeof decidedAt !== 'string') continue
    const decided = Date.parse(decidedAt)
    if (Number.isNaN(decided) || now - decided > KEEP_DAYS * 86_400_000) continue

    const typeOk = type === null || (typeof type === 'string' && TYPE_VALUES.includes(type))
    const verdictOk =
      verdict === null || (typeof verdict === 'string' && VERDICT_VALUES.includes(verdict))
    if (!typeOk || !verdictOk) continue

    result[key] = {
      type: type as NewsType | null,
      verdict: verdict as NewsVerdict | null,
      decidedAt,
    }
  }
  return result
}
