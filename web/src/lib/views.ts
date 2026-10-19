// 一覧・要確認画面で使う、リストの振り分け（単発として除外／要確認）。
import type { BuyCandidates, BuyItem, WatchItem, Watchlist } from '../types/screener'
import { latestSurgeDate } from './news'
import type { NewsSelection } from './news'

type NewsGetter = {
  get: (code: string, surgeDate: string | null) => NewsSelection | null
}

export type Views = {
  watchByCode: Map<string, WatchItem>
  newsOf: (w: WatchItem | undefined) => NewsSelection | null
  watchVisible: WatchItem[]
  watchExcluded: WatchItem[]
  buyVisible: BuyItem[]
  buyExcluded: BuyItem[]
  newsTodo: WatchItem[] // 材料ニュースの選択が必要
  earningsTodo: WatchItem[] // 決算日が不明（手入力もまだ）
  earningsManual: WatchItem[] // 決算日を手入力した
  reviewCount: number
}

export function buildViews(
  watchlist: Watchlist,
  buy: BuyCandidates,
  newsStore: NewsGetter,
  hasManualEarnings: (code: string) => boolean,
): Views {
  const watchByCode = new Map(watchlist.items.map((i) => [i.code, i] as const))
  const newsOf = (w: WatchItem | undefined): NewsSelection | null =>
    w ? newsStore.get(w.code, latestSurgeDate(w)) : null
  const isExcluded = (w: WatchItem | undefined): boolean => newsOf(w)?.verdict === 'oneoff'

  const watchVisible = watchlist.items.filter((i) => !isExcluded(i))
  const watchExcluded = watchlist.items.filter((i) => isExcluded(i))
  const buyVisible = buy.items.filter((i) => !isExcluded(watchByCode.get(i.code)))
  const buyExcluded = buy.items.filter((i) => isExcluded(watchByCode.get(i.code)))

  // 要確認は、買い候補になっている銘柄を先に並べる
  const buyCodes = new Set(buy.items.map((i) => i.code))
  const buyFirst = (a: WatchItem, b: WatchItem): number =>
    Number(buyCodes.has(b.code)) - Number(buyCodes.has(a.code))

  const newsTodo = watchVisible
    .filter((i) => i.needs_news_check && (newsOf(i)?.verdict ?? null) === null)
    .sort(buyFirst)
  const earningsTodo = watchVisible
    .filter((i) => i.earnings_date === null && !hasManualEarnings(i.code))
    .sort(buyFirst)
  const earningsManual = watchVisible.filter(
    (i) => i.earnings_date === null && hasManualEarnings(i.code),
  )

  const reviewCount = new Set([...newsTodo, ...earningsTodo].map((i) => i.code)).size

  return {
    watchByCode,
    newsOf,
    watchVisible,
    watchExcluded,
    buyVisible,
    buyExcluded,
    newsTodo,
    earningsTodo,
    earningsManual,
    reviewCount,
  }
}
