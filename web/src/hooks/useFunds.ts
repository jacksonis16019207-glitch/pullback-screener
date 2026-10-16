import { useState } from 'react'
import { loadNumber, saveNumber } from '../lib/storage'

const KEY = 'pullback.funds'

// 投資資金。この端末のブラウザにだけ保存する（サーバーには送らない）。
export function useFunds(): [number, (value: number) => void] {
  const [funds, setFunds] = useState<number>(() => loadNumber(KEY, 0))

  const update = (value: number) => {
    setFunds(value)
    saveNumber(KEY, value)
  }

  return [funds, update]
}
