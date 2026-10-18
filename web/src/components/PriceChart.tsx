import type { StockChart } from '../types/screener'

type Props = {
  chart: StockChart
  buyLine?: number
}

// SVGの座標系。画面の幅に合わせて自動で拡大縮小される（viewBox）。
const W = 360
const PRICE_H = 150
const VOL_H = 36
const GAP = 8
const PAD = { left: 6, right: 46, top: 8, bottom: 16 }
const H = PAD.top + PRICE_H + GAP + VOL_H + PAD.bottom

// 値の並びを、1本の折れ線（SVGのpath）にする。null の日は線を切る。
function linePath(
  series: (number | null)[],
  x: (i: number) => number,
  y: (v: number) => number,
): string {
  let d = ''
  let pen = false
  series.forEach((v, i) => {
    if (v === null) {
      pen = false
      return
    }
    d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)} `
    pen = true
  })
  return d
}

function monthDay(date: string): string {
  return date.slice(5).replace('-', '/')
}

function yen(value: number): string {
  return value.toLocaleString('ja-JP', { maximumFractionDigits: 0 })
}

export function PriceChart({ chart, buyLine }: Props) {
  const n = chart.dates.length
  const prices = [...chart.close, ...chart.sma25, ...chart.sma75].filter(
    (v): v is number => v !== null,
  )
  if (n < 2 || prices.length === 0) {
    return <p className="empty">チャートのデータがありません。</p>
  }

  const all = buyLine === undefined ? prices : [...prices, buyLine]
  const lo = Math.min(...all)
  const hi = Math.max(...all)
  const span = hi - lo || 1
  const innerW = W - PAD.left - PAD.right

  const x = (i: number) => PAD.left + (i / (n - 1)) * innerW
  const y = (v: number) => PAD.top + (1 - (v - lo) / span) * PRICE_H

  const volTop = PAD.top + PRICE_H + GAP
  const maxVol = Math.max(...chart.volume, 1)
  const barW = Math.max((innerW / n) * 0.7, 0.5)
  const updates = new Set(chart.high_update_dates)

  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="日足6か月のチャート">
        <path className="chart__sma75" d={linePath(chart.sma75, x, y)} />
        <path className="chart__sma25" d={linePath(chart.sma25, x, y)} />
        <path className="chart__close" d={linePath(chart.close, x, y)} />

        {buyLine !== undefined && (
          <line
            className="chart__buyline"
            x1={PAD.left}
            x2={W - PAD.right}
            y1={y(buyLine)}
            y2={y(buyLine)}
          />
        )}

        {chart.dates.map((date, i) => {
          const v = chart.close[i]
          if (!updates.has(date) || v === null) return null
          return <circle key={date} className="chart__high" cx={x(i)} cy={y(v)} r={2.5} />
        })}

        <text className="chart__label" x={W - PAD.right + 4} y={PAD.top + 8}>
          {yen(hi)}
        </text>
        <text className="chart__label" x={W - PAD.right + 4} y={PAD.top + PRICE_H}>
          {yen(lo)}
        </text>

        {chart.volume.map((v, i) => {
          const h = (v / maxVol) * VOL_H
          return (
            <rect
              key={chart.dates[i]}
              className="chart__vol"
              x={x(i) - barW / 2}
              y={volTop + VOL_H - h}
              width={barW}
              height={h}
            />
          )
        })}

        <text className="chart__label" x={PAD.left} y={H - 3}>
          {monthDay(chart.dates[0])}
        </text>
        <text className="chart__label" x={W - PAD.right} y={H - 3} textAnchor="end">
          {monthDay(chart.dates[n - 1])}
        </text>
      </svg>

      <figcaption className="chart__legend">
        <span className="legend legend--close">終値</span>
        <span className="legend legend--sma25">25日線</span>
        <span className="legend legend--sma75">75日線</span>
        <span className="legend legend--high">高値更新日</span>
        {buyLine !== undefined && <span className="legend legend--buyline">買いライン</span>}
      </figcaption>
    </figure>
  )
}
