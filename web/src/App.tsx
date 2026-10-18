import { Navigate, Route, Routes } from 'react-router-dom'
import { useFunds } from './hooks/useFunds'
import { useScreenerData } from './hooks/useScreenerData'
import { ListPage } from './pages/ListPage'
import { StockDetailPage } from './pages/StockDetailPage'

export default function App() {
  const data = useScreenerData()
  const [funds, setFunds] = useFunds()

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

  return (
    <main className="page">
      <Routes>
        <Route
          path="/"
          element={<ListPage tab="buy" watchlist={watchlist} buy={buy} funds={funds} onFundsChange={setFunds} />}
        />
        <Route
          path="/watch"
          element={<ListPage tab="watch" watchlist={watchlist} buy={buy} funds={funds} onFundsChange={setFunds} />}
        />
        <Route
          path="/stock/:code"
          element={<StockDetailPage watchlist={watchlist} buy={buy} funds={funds} />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </main>
  )
}
