import { Link } from 'react-router-dom'
import { EarningsInput } from '../components/EarningsInput'
import { TopSection } from '../components/TopSection'
import type { EarningsStore } from '../hooks/useManualEarnings'
import type { NewsStore } from '../hooks/useNewsSelections'
import { latestSurgeDate } from '../lib/news'
import { buildViews } from '../lib/views'
import type { BuyCandidates, WatchItem, Watchlist } from '../types/screener'

type Props = {
  watchlist: Watchlist
  buy: BuyCandidates
  funds: number
  onFundsChange: (value: number) => void
  newsStore: NewsStore
  earningsStore: EarningsStore
}

export function ReviewPage({
  watchlist,
  buy,
  funds,
  onFundsChange,
  newsStore,
  earningsStore,
}: Props) {
  const views = buildViews(watchlist, buy, newsStore, (code) => earningsStore.get(code) !== null)
  const buyCodes = new Set(buy.items.map((i) => i.code))

  const header = (item: WatchItem) => (
    <header className="card__head">
      <h3 className="card__title">
        <Link to={`/stock/${item.code}`} className="card__link">
          {item.code} {item.name}
        </Link>
      </h3>
      {buyCodes.has(item.code) && <span className="badge badge--ok">買い候補</span>}
    </header>
  )

  const earningsRow = (item: WatchItem) => (
    <article key={item.ticker} className="card">
      {header(item)}
      <EarningsInput
        value={earningsStore.get(item.code)?.date ?? null}
        onSave={(date) => earningsStore.set(item.code, date)}
        onClear={() => earningsStore.clear(item.code)}
      />
    </article>
  )

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

      {views.reviewCount === 0 && <p className="empty">確認が必要な銘柄はありません。</p>}

      {views.newsTodo.length > 0 && (
        <section className="section">
          <h2 className="section__title">材料ニュースの選択が必要（{views.newsTodo.length}件）</h2>
          <p className="news__hint">
            直近5営業日に+5%以上の急騰があった銘柄です。材料を調べて、単発か継続かを選んでください。
          </p>
          {views.newsTodo.map((item) => (
            <article key={item.ticker} className="card">
              {header(item)}
              <p className="card__main">急騰日: {latestSurgeDate(item) ?? '—'}</p>
              <Link to={`/stock/${item.code}`} className="chip chip--link">
                調べて選択する
              </Link>
            </article>
          ))}
        </section>
      )}

      {views.earningsTodo.length > 0 && (
        <section className="section">
          <h2 className="section__title">決算日が不明（{views.earningsTodo.length}件）</h2>
          <p className="news__hint">
            SBI株アプリなどで決算発表予定日を調べて、入力してください。入力すると、5営業日以内の銘柄には「見送り」の印がつきます。
          </p>
          {views.earningsTodo.map(earningsRow)}
        </section>
      )}

      {views.earningsManual.length > 0 && (
        <section className="section">
          <h2 className="section__title">決算日を手入力した銘柄（{views.earningsManual.length}件）</h2>
          {views.earningsManual.map(earningsRow)}
        </section>
      )}
    </>
  )
}
