import { NavLink } from 'react-router-dom'
import { BuyCard } from '../components/BuyCard'
import { FundsInput } from '../components/FundsInput'
import { WatchCard } from '../components/WatchCard'
import { formatDateTime } from '../lib/format'
import type { BuyCandidates, Watchlist } from '../types/screener'

type Props = {
  tab: 'buy' | 'watch'
  watchlist: Watchlist
  buy: BuyCandidates
  funds: number
  onFundsChange: (value: number) => void
}

function tabClass({ isActive }: { isActive: boolean }): string {
  return `tab${isActive ? ' tab--active' : ''}`
}

export function ListPage({ tab, watchlist, buy, funds, onFundsChange }: Props) {
  const topix = buy.topix

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
          買い候補 {buy.items.length}
        </NavLink>
        <NavLink to="/watch" className={tabClass}>
          押し目待ち {watchlist.items.length}
        </NavLink>
      </nav>

      {tab === 'buy' ? (
        buy.items.length === 0 ? (
          <p className="empty">今日の買い候補はありません。</p>
        ) : (
          buy.items.map((item) => <BuyCard key={item.ticker} item={item} funds={funds} />)
        )
      ) : (
        watchlist.items.map((item) => <WatchCard key={item.ticker} item={item} funds={funds} />)
      )}
    </>
  )
}
