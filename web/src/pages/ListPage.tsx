import { useState } from 'react'
import { BuyCard } from '../components/BuyCard'
import { TopSection } from '../components/TopSection'
import { WatchCard } from '../components/WatchCard'
import type { EarningsStore } from '../hooks/useManualEarnings'
import type { NewsStore } from '../hooks/useNewsSelections'
import { todayIso } from '../lib/businessDays'
import { resolveEarnings } from '../lib/earnings'
import type { EarningsView } from '../lib/earnings'
import { buildViews } from '../lib/views'
import type { BuyCandidates, BuyItem, WatchItem, Watchlist } from '../types/screener'

type Props = {
  tab: 'buy' | 'watch'
  watchlist: Watchlist
  buy: BuyCandidates
  funds: number
  onFundsChange: (value: number) => void
  newsStore: NewsStore
  earningsStore: EarningsStore
  nonTrading: ReadonlySet<string>
  within: number
}

export function ListPage({
  tab,
  watchlist,
  buy,
  funds,
  onFundsChange,
  newsStore,
  earningsStore,
  nonTrading,
  within,
}: Props) {
  const [showExcluded, setShowExcluded] = useState(false)
  const views = buildViews(watchlist, buy, newsStore, (code) => earningsStore.get(code) !== null)
  const { watchByCode, newsOf } = views
  const today = todayIso()

  const earningsOfWatch = (w: WatchItem): EarningsView =>
    resolveEarnings(
      { date: w.earnings_date, source: w.earnings_source, soon: null },
      earningsStore.get(w.code),
      today,
      within,
      nonTrading,
    )
  const earningsOfBuy = (b: BuyItem): EarningsView =>
    resolveEarnings(
      { date: b.earnings_date, source: b.earnings_source, soon: b.earnings_soon },
      earningsStore.get(b.code),
      b.signal_date,
      within,
      nonTrading,
    )

  const renderBuy = (item: BuyItem) => {
    const w = watchByCode.get(item.code)
    return (
      <BuyCard
        key={item.ticker}
        item={item}
        funds={funds}
        needsNewsCheck={w?.needs_news_check ?? false}
        news={newsOf(w)}
        earnings={earningsOfBuy(item)}
      />
    )
  }
  const renderWatch = (item: WatchItem, dimmed = false) => (
    <WatchCard
      key={item.ticker}
      item={item}
      funds={funds}
      news={newsOf(item)}
      earnings={earningsOfWatch(item)}
      dimmed={dimmed}
    />
  )

  const excludedCount = tab === 'buy' ? views.buyExcluded.length : views.watchExcluded.length

  return (
    <>
      <TopSection
        topix={buy.topix}
        generatedAt={buy.generated_at}
        funds={funds}
        onFundsChange={onFundsChange}
        counts={{
          buy: views.buyVisible.length,
          watch: views.watchVisible.length,
          review: views.reviewCount,
        }}
      />

      {views.newsTodo.length > 0 && (
        <p className="notice">
          材料ニュースの選択が必要な銘柄が {views.newsTodo.length} 件あります。「要確認」から選択してください。
        </p>
      )}

      {tab === 'buy' ? (
        views.buyVisible.length === 0 ? (
          <p className="empty">今日の買い候補はありません。</p>
        ) : (
          views.buyVisible.map(renderBuy)
        )
      ) : (
        views.watchVisible.map((item) => renderWatch(item))
      )}

      {excludedCount > 0 && (
        <>
          <button type="button" className="link-button" onClick={() => setShowExcluded((v) => !v)}>
            {showExcluded
              ? '単発として除外した銘柄を隠す'
              : `単発として除外した銘柄を表示（${excludedCount}件）`}
          </button>
          {showExcluded &&
            (tab === 'buy'
              ? views.buyExcluded.map(renderBuy)
              : views.watchExcluded.map((item) => renderWatch(item, true)))}
        </>
      )}
    </>
  )
}
