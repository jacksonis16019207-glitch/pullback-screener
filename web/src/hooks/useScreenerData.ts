import { useEffect, useState } from 'react'
import type { BuyCandidates, Watchlist } from '../types/screener'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; watchlist: Watchlist; buy: BuyCandidates }

async function fetchJson<T>(name: string): Promise<T> {
  const res = await fetch(`${import.meta.env.BASE_URL}data/${name}`)
  if (!res.ok) {
    throw new Error(`${name} を読み込めませんでした (${res.status})`)
  }
  return (await res.json()) as T
}

export function useScreenerData(): State {
  const [state, setState] = useState<State>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    Promise.all([
      fetchJson<Watchlist>('watchlist.json'),
      fetchJson<BuyCandidates>('buy_candidates.json'),
    ])
      .then(([watchlist, buy]) => {
        if (!cancelled) setState({ status: 'ready', watchlist, buy })
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
