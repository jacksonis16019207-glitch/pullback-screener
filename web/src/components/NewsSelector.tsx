import { NEWS_TYPES, VERDICT_LABEL } from '../lib/news'
import type { NewsSelection, NewsTypeInfo, NewsVerdict } from '../lib/news'

type Props = {
  selection: NewsSelection | null
  onChange: (selection: NewsSelection) => void
  onClear: () => void
}

const VERDICTS: NewsVerdict[] = ['oneoff', 'continuing']

export function NewsSelector({ selection, onChange, onClear }: Props) {
  const selectedType = NEWS_TYPES.find((t) => t.value === selection?.type)

  const pickType = (t: NewsTypeInfo) => {
    // 種類から目安が決まるものは、判断も自動で入れる（あとから変えられる）
    onChange({
      type: t.value,
      verdict: t.lean ?? selection?.verdict ?? null,
      decidedAt: new Date().toISOString(),
    })
  }

  const pickVerdict = (verdict: NewsVerdict) => {
    onChange({
      type: selection?.type ?? null,
      verdict,
      decidedAt: new Date().toISOString(),
    })
  }

  return (
    <div className="news">
      <p className="news__label">材料の種類</p>
      <div className="chips" role="radiogroup" aria-label="材料の種類">
        {NEWS_TYPES.map((t) => (
          <button
            key={t.value}
            type="button"
            role="radio"
            aria-checked={selection?.type === t.value}
            className={`chip${selection?.type === t.value ? ' chip--on' : ''}`}
            onClick={() => pickType(t)}
          >
            {t.label}
          </button>
        ))}
      </div>
      {selectedType && <p className="news__hint">{selectedType.hint}</p>}

      <p className="news__label">判断</p>
      <div className="chips" role="radiogroup" aria-label="単発か継続か">
        {VERDICTS.map((v) => (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={selection?.verdict === v}
            className={`chip${selection?.verdict === v ? ' chip--on' : ''}`}
            onClick={() => pickVerdict(v)}
          >
            {VERDICT_LABEL[v]}
          </button>
        ))}
      </div>

      {selection && (
        <button type="button" className="link-button" onClick={onClear}>
          選択を取り消す
        </button>
      )}
    </div>
  )
}
