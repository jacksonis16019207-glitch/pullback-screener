// Python（batch/）が出力するJSONの形。項目名は batch/output/*.json と同じ。

export type Topix = {
  ticker: string
  ok: boolean
  as_of?: string
  close_gt_sma25?: boolean
  sma25_gt_sma75?: boolean
  sma75_slope_pct?: number
  sma75_slope_ok?: boolean
}

type StockBase = {
  ticker: string
  code: string
  name: string
  sector: string
  market_cap_oku: number
  close: number
  last_high_update: string
  earnings_date: string | null
  earnings_source: string | null
}

// 押し目待ちリスト（watchlist.json）の1銘柄
export type WatchItem = StockBase & {
  sma25: number
  sma75: number
  trend_slope_pct_per_day: number
  needs_news_check: boolean
  surge_dates: string[]
}

// 買い候補リスト（buy_candidates.json）の1銘柄
export type BuyItem = StockBase & {
  signal_date: string
  buy_line: number
  volume: number
  prev_volume: number
  pullback_min_pct: number
  earnings_soon: boolean | null // true=決算が近い, null=決算日不明
  topix_blocked: boolean
}

export type Watchlist = {
  generated_at: string
  topix: Topix
  total_before_limit?: number
  non_trading_days?: string[] // 平日なのに取引所が休みの日（営業日を数えるのに使う）
  earnings_skip_days?: number // 決算が何営業日以内なら見送りか
  items: WatchItem[]
}

export type BuyCandidates = {
  generated_at: string
  topix: Topix
  items: BuyItem[]
}

// charts.json（銘柄詳細画面のチャートと判定補助の数字）
export type ChartStats = {
  six_month_return_pct: number | null
  surge_count_20d: number
  surge_day: string | null
  days_since_surge: number | null
  pre_surge_20d_pct: number | null
  volume_ratio_after_surge: number | null
}

export type StockChart = {
  dates: string[]
  close: (number | null)[]
  sma25: (number | null)[]
  sma75: (number | null)[]
  volume: number[]
  high_update_dates: string[]
  stats: ChartStats
}

export type ChartsFile = {
  generated_at: string
  stocks: Record<string, StockChart>
}
