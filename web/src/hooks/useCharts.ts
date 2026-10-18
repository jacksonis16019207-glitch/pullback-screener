import { useEffect, useState } from 'react'
import type { ChartsFile } from '../types/screener'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; charts: ChartsFile }

// charts.json は大きいので、銘柄詳細を開いたときに初めて読み込み、以降は使い回す。
let cache: Promise<ChartsFile> | null = null

function loadCharts(): Promise<ChartsFile> {
  if (cache === null) {
    const request = fetch(`${import.meta.env.BASE_URL}data/charts.json`).then((res) => {
      if (!res.ok) throw new Error(`charts.json を読み込めませんでした (${res.status})`)
      return res.json() as Promise<ChartsFile>
    })
    cache = request
    request.catch(() => {
      cache = null // 失敗したときは、次に開いたときにやり直せるようにする
    })
  }
  return cache
}

export function useCharts(): State {
  const [state, setState] = useState<State>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    loadCharts()
      .then((charts) => {
        if (!cancelled) setState({ status: 'ready', charts })
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setState({ status: 'error', message: e instanceof Error ? e.message : String(e) })
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  return state
}
