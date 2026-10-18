import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { BuyCard } from '../components/BuyCard'
import { FundsInput } from '../components/FundsInput'
import { WatchCard } from '../components/WatchCard'
import type { NewsStore } from '../hooks/useNewsSelections'
import { formatDateTime } from '../lib/format'
import { latestSurgeDate } from '../lib/news'
import type { NewsSelection } from '../lib/news'
import type { BuyCandidates, WatchItem, Watchlist } from '../types/screener'

type Props = {
  tab: 'buy' | 'watch'
  watchlist: Watchlist
  buy: BuyCandidates
  funds: number
  onFundsChange: (value: number) => void
  newsStore: NewsStore
}

function tabClass({ isActive }: { isActive: boolean }): string {
  return `tab${isActive ? ' tab--active' : ''}`
}

export function ListPage({ tab, watchlist, buy, funds, onFundsChange, newsStore }: Props) {
  const [showExcluded, setShowExcluded] = useState(false)
  const topix = buy.topix

  const watchByCode = new Map(watchlist.items.map((i) => [i.code, i]))
  const newsOf = (w: WatchItem | undefined): NewsSelection | null =>
    w ? newsStore.get(w.code, latestSurgeDate(w)) : null
  const isExcluded = (w: WatchItem | undefined): boolean => newsOf(w)?.verdict === 'oneoff'

  // 「単発」と判断した銘柄は、リストから外す（下のボタンで表示できる）
  const watchVisible = watchlist.items.filter((i) => !isExcluded(i))
  const watchExcluded = watchlist.items.filter((i) => isExcluded(i))
  const buyVisible = buy.items.filter((i) => !isExcluded(watchByCode.get(i.code)))
  const buyExcluded = buy.items.filter((i) => isExcluded(watchByCode.get(i.code)))
  const unselected = watchVisible.filter(
    (i) => i.needs_news_check && newsOf(i)?.verdict == null,
  ).length

  const excludedCount = tab === 'buy' ? buyExcluded.length : watchExcluded.length

  return (
    <>
      <h1 className="title">押し目スクリーナー</h1>

      <p className={`topix ${topix.ok ? 'topix--ok' : 'topix--ng'}`}>
        TOPIX判定: {topix.ok ? '○（新規買いOK）' : '×（新規買いは見送り）'}
      </p>
      <p className="updated">更新: {formatDateTime(buy.generated_at)}</p>

      <FundsInput value={funds} onChange={onFundsChange} />

      <nav className="tabs">
        <NavLink to="/" end className={tabClass}>
          買い候補 {buyVisible.length}
        </NavLink>
        <NavLink to="/watch" className={tabClass}>
          押し目待ち {watchVisible.length}
        </NavLink>
      </nav>

      {unselected > 0 && (
        <p className="notice">
          材料ニュースの選択が必要な銘柄が {unselected} 件あります。銘柄をタップして、材料を調べて選択してください。
        </p>
      )}

      {tab === 'buy' ? (
        buyVisible.length === 0 ? (
          <p className="empty">今日の買い候補はありません。</p>
        ) : (
          buyVisible.map((item) => {
            const w = watchByCode.get(item.code)
            return (
              <BuyCard
                key={item.ticker}
                item={item}
                funds={funds}
                needsNewsCheck={w?.needs_news_check ?? false}
                news={newsOf(w)}
              />
            )
          })
        )
      ) : (
        watchVisible.map((item) => (
          <WatchCard key={item.ticker} item={item} funds={funds} news={newsOf(item)} />
        ))
      )}

      {excludedCount > 0 && (
        <>
          <button type="button" className="link-button" onClick={() => setShowExcluded((v) => !v)}>
            {showExcluded ? '単発として除外した銘柄を隠す' : `単発として除外した銘柄を表示（${excludedCount}件）`}
          </button>
          {showExcluded &&
            (tab === 'buy'
              ? buyExcluded.map((item) => (
                  <BuyCard
                    key={item.ticker}
                    item={item}
                    funds={funds}
                    needsNewsCheck={watchByCode.get(item.code)?.needs_news_check ?? false}
                    news={newsOf(watchByCode.get(item.code))}
                  />
                ))
              : watchExcluded.map((item) => (
                  <WatchCard
                    key={item.ticker}
                    item={item}
                    funds={funds}
                    news={newsOf(item)}
                    dimmed
                  />
                )))}
        </>
      )}
    </>
  )
}
