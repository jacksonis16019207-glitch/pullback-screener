import { Navigate, Route, Routes } from 'react-router-dom'
import { useFunds } from './hooks/useFunds'
import { useNewsSelections } from './hooks/useNewsSelections'
import { useScreenerData } from './hooks/useScreenerData'
import { ListPage } from './pages/ListPage'
import { StockDetailPage } from './pages/StockDetailPage'

export default function App() {
  const data = useScreenerData()
  const [funds, setFunds] = useFunds()
  const newsStore = useNewsSelections()

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
  const listProps = { watchlist, buy, funds, onFundsChange: setFunds, newsStore }

  return (
    <main className="page">
      <Routes>
        <Route path="/" element={<ListPage tab="buy" {...listProps} />} />
        <Route path="/watch" element={<ListPage tab="watch" {...listProps} />} />
        <Route
          path="/stock/:code"
          element={
            <StockDetailPage watchlist={watchlist} buy={buy} funds={funds} newsStore={newsStore} />
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </main>
  )
}
