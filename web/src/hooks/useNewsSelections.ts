import { useState } from 'react'
import { loadJson, saveJson } from '../lib/storage'
import { parseEntries, selectionKey } from '../lib/news'
import type { NewsSelection } from '../lib/news'

const KEY = 'pullback.news.v1'

export type NewsStore = {
  get: (code: string, surgeDate: string | null) => NewsSelection | null
  set: (code: string, surgeDate: string, selection: NewsSelection) => void
  clear: (code: string, surgeDate: string) => void
}

// 材料ニュースの選択。この端末のブラウザにだけ保存する（サーバーには送らない）。
export function useNewsSelections(): NewsStore {
  const [entries, setEntries] = useState<Record<string, NewsSelection>>(() =>
    parseEntries(loadJson(KEY)),
  )

  const persist = (next: Record<string, NewsSelection>) => {
    setEntries(next)
    saveJson(KEY, { version: 1, entries: next })
  }

  return {
    get: (code, surgeDate) =>
      surgeDate === null ? null : (entries[selectionKey(code, surgeDate)] ?? null),
    set: (code, surgeDate, selection) => {
      persist({ ...entries, [selectionKey(code, surgeDate)]: selection })
    },
    clear: (code, surgeDate) => {
      const next = { ...entries }
      delete next[selectionKey(code, surgeDate)]
      persist(next)
    },
  }
}
