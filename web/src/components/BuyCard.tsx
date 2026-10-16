import { formatYen } from '../lib/format'
import { calcAffordability } from '../lib/shares'
import type { BuyItem } from '../types/screener'

type Props = {
  item: BuyItem
  funds: number
}

export function BuyCard({ item, funds }: Props) {
  const a = calcAffordability(funds, item.buy_line)
  const skip = item.topix_blocked || item.earnings_soon === true

  let affordText = '資金を入力してください'
  if (funds > 0) {
    if (a.lots > 0) affordText = `${a.lots}単元（S株なら${a.shares}株）`
    else if (a.shares > 0) affordText = `単元は買えません（S株なら${a.shares}株）`
    else affordText = '資金が足りません'
  }

  return (
    <article className={`card${skip ? ' card--skip' : ''}`}>
      <header className="card__head">
        <h3 className="card__title">
          {item.code} {item.name}
        </h3>
        <span className="card__sector">{item.sector}</span>
      </header>

      <p className="card__main">
        買いライン <strong>{formatYen(item.buy_line)}</strong> 超え
      </p>

      <ul className="badges">
        {item.topix_blocked && <li className="badge badge--warn">TOPIXが×のため見送り</li>}
        {item.earnings_soon === true && <li className="badge badge--warn">決算が近いため見送り</li>}
        {item.earnings_soon === null && <li className="badge badge--info">決算日不明</li>}
      </ul>

      <dl className="meta">
        <dt>買える数</dt>
        <dd>{affordText}</dd>
        <dt>1単元</dt>
        <dd>{formatYen(a.lotCost)}</dd>
        <dt>決算日</dt>
        <dd>{item.earnings_date ?? '不明'}</dd>
        <dt>時価総額</dt>
        <dd>{item.market_cap_oku.toLocaleString('ja-JP')}億円</dd>
      </dl>
    </article>
  )
}
