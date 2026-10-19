import { useState } from 'react'
import { parseManualEarnings } from '../lib/earnings'
import type { ManualEarnings } from '../lib/earnings'
import { loadJson, saveJson } from '../lib/storage'

const KEY = 'pullback.earnings.v1'

export type EarningsStore = {
  get: (code: string) => ManualEarnings | null
  set: (code: string, date: string) => void
  clear: (code: string) => void
}

// 手入力した決算日。この端末のブラウザにだけ保存する（サーバーには送らない）。
export function useManualEarnings(): EarningsStore {
  const [entries, setEntries] = useState<Record<string, ManualEarnings>>(() =>
    parseManualEarnings(loadJson(KEY)),
  )

  const persist = (next: Record<string, ManualEarnings>) => {
    setEntries(next)
    saveJson(KEY, { version: 1, entries: next })
  }

  return {
    get: (code) => entries[code] ?? null,
    set: (code, date) => {
      persist({ ...entries, [code]: { date, enteredAt: new Date().toISOString() } })
    },
    clear: (code) => {
      const next = { ...entries }
      delete next[code]
      persist(next)
    },
  }
}
