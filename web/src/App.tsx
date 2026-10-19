import { Navigate, Route, Routes } from 'react-router-dom'
import { useFunds } from './hooks/useFunds'
import { useManualEarnings } from './hooks/useManualEarnings'
import { useNewsSelections } from './hooks/useNewsSelections'
import { useScreenerData } from './hooks/useScreenerData'
import { ListPage } from './pages/ListPage'
import { ReviewPage } from './pages/ReviewPage'
import { StockDetailPage } from './pages/StockDetailPage'

export default function App() {
  const data = useScreenerData()
  const [funds, setFunds] = useFunds()
  const newsStore = useNewsSelections()
  const earningsStore = useManualEarnings()

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
  const nonTrading = new Set(watchlist.non_trading_days ?? [])
  const within = watchlist.earnings_skip_days ?? 5
  const common = { watchlist, buy, funds, newsStore, earningsStore }

  return (
    <main className="page">
      <Routes>
        <Route
          path="/"
          element={
            <ListPage
              tab="buy"
              {...common}
              onFundsChange={setFunds}
              nonTrading={nonTrading}
              within={within}
            />
          }
        />
        <Route
          path="/watch"
          element={
            <ListPage
              tab="watch"
              {...common}
              onFundsChange={setFunds}
              nonTrading={nonTrading}
              within={within}
            />
          }
        />
        <Route
          path="/review"
          element={<ReviewPage {...common} onFundsChange={setFunds} />}
        />
        <Route
          path="/stock/:code"
          element={<StockDetailPage {...common} nonTrading={nonTrading} within={within} />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </main>
  )
}
