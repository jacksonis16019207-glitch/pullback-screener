import { Link } from 'react-router-dom'
import { earningsText } from '../lib/earnings'
import type { EarningsView } from '../lib/earnings'
import { formatYen } from '../lib/format'
import type { NewsSelection } from '../lib/news'
import { calcAffordability } from '../lib/shares'
import type { BuyItem } from '../types/screener'
import { NewsBadge } from './NewsBadge'

type Props = {
  item: BuyItem
  funds: number
  needsNewsCheck: boolean
  news: NewsSelection | null
  earnings: EarningsView
}

export function BuyCard({ item, funds, needsNewsCheck, news, earnings }: Props) {
  const a = calcAffordability(funds, item.buy_line)
  const skip = item.topix_blocked || earnings.soon === true

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
          <Link to={`/stock/${item.code}`} className="card__link">
            {item.code} {item.name}
          </Link>
        </h3>
        <span className="card__sector">{item.sector}</span>
      </header>

      <p className="card__main">
        買いライン <strong>{formatYen(item.buy_line)}</strong> 超え
      </p>

      <ul className="badges">
        {item.topix_blocked && <li className="badge badge--warn">TOPIXが×のため見送り</li>}
        {earnings.soon === true && <li className="badge badge--warn">決算が近いため見送り</li>}
        {earnings.date === null && <li className="badge badge--info">決算日不明</li>}
        <NewsBadge needsCheck={needsNewsCheck} selection={news} />
      </ul>

      <dl className="meta">
        <dt>買える数</dt>
        <dd>{affordText}</dd>
        <dt>1単元</dt>
        <dd>{formatYen(a.lotCost)}</dd>
        <dt>決算日</dt>
        <dd>{earningsText(earnings)}</dd>
        <dt>時価総額</dt>
        <dd>{item.market_cap_oku.toLocaleString('ja-JP')}億円</dd>
      </dl>
    </article>
  )
}
