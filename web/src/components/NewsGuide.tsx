import { Fragment } from 'react'
import { NEWS_TYPES, QUESTIONS } from '../lib/news'

export function NewsGuide() {
  return (
    <details className="guide">
      <summary>判断の目安</summary>
      <ol className="guide__list">
        {QUESTIONS.map((q) => (
          <li key={q}>{q}</li>
        ))}
      </ol>
      <p className="guide__note">
        迷ったら「単発」を選びます。候補を1つ失うだけで、損失を避けられるためです。
      </p>
      <dl className="meta">
        {NEWS_TYPES.map((t) => (
          <Fragment key={t.value}>
            <dt>{t.label}</dt>
            <dd>{t.hint}</dd>
          </Fragment>
        ))}
      </dl>
    </details>
  )
}
