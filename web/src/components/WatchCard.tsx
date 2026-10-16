import { formatPercent, formatYen } from '../lib/format'
import { calcAffordability } from '../lib/shares'
import type { WatchItem } from '../types/screener'

type Props = {
  item: WatchItem
  funds: number
}

export function WatchCard({ item, funds }: Props) {
  const a = calcAffordability(funds, item.close)
  const distance = (item.close / item.sma25 - 1) * 100

  let affordText = '資金を入力してください'
  if (funds > 0) {
    if (a.lots > 0) affordText = `${a.lots}単元（S株なら${a.shares}株）`
    else if (a.shares > 0) affordText = `S株なら${a.shares}株`
    else affordText = '資金が足りません'
  }

  return (
    <article className="card">
      <header className="card__head">
        <h3 className="card__title">
          {item.code} {item.name}
        </h3>
        <span className="card__sector">{item.sector}</span>
      </header>

      <p className="card__main">
        現在値 <strong>{formatYen(item.close)}</strong>（25日線から {formatPercent(distance)}）
      </p>

      <ul className="badges">
        {item.needs_news_check && <li className="badge badge--warn">材料ニュースの確認が必要</li>}
        {item.earnings_date === null && <li className="badge badge--info">決算日不明</li>}
      </ul>

      <dl className="meta">
        <dt>高値更新日</dt>
        <dd>{item.last_high_update}</dd>
        <dt>買える数</dt>
        <dd>{affordText}</dd>
        <dt>決算日</dt>
        <dd>{item.earnings_date ?? '不明'}</dd>
        <dt>時価総額</dt>
        <dd>{item.market_cap_oku.toLocaleString('ja-JP')}億円</dd>
      </dl>
    </article>
  )
}
