import { useState } from 'react'
import { BuyCard } from './components/BuyCard'
import { FundsInput } from './components/FundsInput'
import { WatchCard } from './components/WatchCard'
import { useFunds } from './hooks/useFunds'
import { useScreenerData } from './hooks/useScreenerData'
import { formatDateTime } from './lib/format'

type Tab = 'buy' | 'watch'

export default function App() {
  const data = useScreenerData()
  const [funds, setFunds] = useFunds()
  const [tab, setTab] = useState<Tab>('buy')

  if (data.status === 'loading') {
    return <main className="page"><p>読み込み中...</p></main>
  }
  if (data.status === 'error') {
    return (
      <main className="page">
        <p className="error">{data.message}</p>
        <p>web/public/data/ に watchlist.json と buy_candidates.json を置いてください。</p>
      </main>
    )
  }

  const { watchlist, buy } = data
  const topix = buy.topix

  return (
    <main className="page">
      <h1 className="title">押し目スクリーナー</h1>

      <p className={`topix ${topix.ok ? 'topix--ok' : 'topix--ng'}`}>
        TOPIX判定: {topix.ok ? '○（新規買いOK）' : '×（新規買いは見送り）'}
      </p>
      <p className="updated">更新: {formatDateTime(buy.generated_at)}</p>

      <FundsInput value={funds} onChange={setFunds} />

      <nav className="tabs">
        <button className={`tab${tab === 'buy' ? ' tab--active' : ''}`} onClick={() => setTab('buy')}>
          買い候補 {buy.items.length}
        </button>
        <button className={`tab${tab === 'watch' ? ' tab--active' : ''}`} onClick={() => setTab('watch')}>
          押し目待ち {watchlist.items.length}
        </button>
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
    </main>
  )
}
