import { Link, useParams } from 'react-router-dom'
import { NewsBadge } from '../components/NewsBadge'
import { NewsGuide } from '../components/NewsGuide'
import { NewsSelector } from '../components/NewsSelector'
import { PriceChart } from '../components/PriceChart'
import { SearchLinks } from '../components/SearchLinks'
import { useCharts } from '../hooks/useCharts'
import type { NewsStore } from '../hooks/useNewsSelections'
import { formatPercent, formatYen } from '../lib/format'
import { latestSurgeDate } from '../lib/news'
import { calcAffordability } from '../lib/shares'
import type { BuyCandidates, StockChart, Watchlist } from '../types/screener'

type Props = {
  watchlist: Watchlist
  buy: BuyCandidates
  funds: number
  newsStore: NewsStore
}

function surgeText(chart: StockChart): string {
  const { surge_day, days_since_surge } = chart.stats
  if (surge_day === null) return '直近5営業日にはなし'
  return `${surge_day}（${days_since_surge ?? 0}営業日前）`
}

export function StockDetailPage({ watchlist, buy, funds, newsStore }: Props) {
  const { code } = useParams<{ code: string }>()
  const charts = useCharts()

  const watchItem = watchlist.items.find((i) => i.code === code)
  const buyItem = buy.items.find((i) => i.code === code)

  if (!watchItem) {
    return (
      <>
        <Link to="/" className="back">← 戻る</Link>
        <p className="empty">この銘柄は、現在のリストにありません。</p>
      </>
    )
  }

  const price = buyItem?.buy_line ?? watchItem.close
  const a = calcAffordability(funds, price)
  const chart: StockChart | undefined =
    charts.status === 'ready' ? charts.charts.stocks[watchItem.code] : undefined
  const surgeDate = latestSurgeDate(watchItem)
  const news = newsStore.get(watchItem.code, surgeDate)
  const earningsLabel = watchItem.earnings_date ?? '不明'
  const earningsSource = watchItem.earnings_source ? `（${watchItem.earnings_source}）` : ''

  return (
    <>
      <Link to={buyItem ? '/' : '/watch'} className="back">← 戻る</Link>

      <header className="card__head">
        <h1 className="title">
          {watchItem.code} {watchItem.name}
        </h1>
        <span className="card__sector">{watchItem.sector}</span>
      </header>

      <ul className="badges">
        {buyItem && <li className="badge badge--ok">買い候補</li>}
        <NewsBadge needsCheck={watchItem.needs_news_check} selection={news} />
        {watchItem.earnings_date === null && <li className="badge badge--info">決算日不明</li>}
      </ul>

      <section className="section">
        <dl className="meta">
          {buyItem && (
            <>
              <dt>買いライン</dt>
              <dd>{formatYen(buyItem.buy_line)} 超え</dd>
            </>
          )}
          <dt>現在値</dt>
          <dd>{formatYen(watchItem.close)}</dd>
          <dt>買える数</dt>
          <dd>
            {funds > 0
              ? a.lots > 0
                ? `${a.lots}単元（S株なら${a.shares}株）`
                : `S株なら${a.shares}株`
              : '資金を入力してください'}
          </dd>
          <dt>高値更新日</dt>
          <dd>{watchItem.last_high_update}</dd>
          <dt>決算日</dt>
          <dd>
            {earningsLabel}
            {earningsSource}
          </dd>
          <dt>時価総額</dt>
          <dd>{watchItem.market_cap_oku.toLocaleString('ja-JP')}億円</dd>
        </dl>
      </section>

      <section className="section">
        <h2 className="section__title">日足6か月</h2>
        {charts.status === 'loading' && <p className="empty">チャートを読み込み中...</p>}
        {charts.status === 'error' && <p className="error">{charts.message}</p>}
        {charts.status === 'ready' && !chart && <p className="empty">この銘柄のチャートがありません。</p>}
        {chart && <PriceChart chart={chart} buyLine={buyItem?.buy_line} />}
      </section>

      {chart && (
        <section className="section">
          <h2 className="section__title">判定の目安</h2>
          <dl className="meta">
            <dt>6か月の傾き</dt>
            <dd>{watchItem.trend_slope_pct_per_day.toFixed(2)}%/日</dd>
            <dt>6か月の騰落率</dt>
            <dd>
              {chart.stats.six_month_return_pct === null ? '—' : formatPercent(chart.stats.six_month_return_pct)}
            </dd>
            <dt>+5%以上の日（直近20営業日）</dt>
            <dd>{chart.stats.surge_count_20d}日</dd>
            <dt>直近の急騰日</dt>
            <dd>{surgeText(chart)}</dd>
            <dt>急騰前20日の上昇率</dt>
            <dd>
              {chart.stats.pre_surge_20d_pct === null ? '—' : formatPercent(chart.stats.pre_surge_20d_pct)}
            </dd>
            <dt>急騰後の出来高（急騰前20日平均比）</dt>
            <dd>
              {chart.stats.volume_ratio_after_surge === null
                ? '—'
                : `${chart.stats.volume_ratio_after_surge.toFixed(2)}倍`}
            </dd>
          </dl>
        </section>
      )}

      <section className="section">
        <h2 className="section__title">材料ニュースを調べる</h2>
        <SearchLinks
          code={watchItem.code}
          name={watchItem.name}
          sector={watchItem.sector}
          surgeDate={surgeDate}
        />
      </section>

      {watchItem.needs_news_check && surgeDate !== null && (
        <section className="section">
          <h2 className="section__title">材料ニュースの選択</h2>
          <p className="news__hint">
            急騰日: {surgeDate}。調べた結果を選んでください。「単発」を選ぶと、一覧から外れます。
          </p>
          <NewsSelector
            selection={news}
            onChange={(s) => newsStore.set(watchItem.code, surgeDate, s)}
            onClear={() => newsStore.clear(watchItem.code, surgeDate)}
          />
          <NewsGuide />
        </section>
      )}
    </>
  )
}
