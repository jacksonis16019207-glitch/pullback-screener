type Props = {
  value: string | null
  onSave: (date: string) => void
  onClear: () => void
}

// 決算発表予定日の入力（日付の選択）。選ぶとすぐ保存される。
export function EarningsInput({ value, onSave, onClear }: Props) {
  return (
    <div className="earnings-input">
      <input
        className="funds__input earnings-input__date"
        type="date"
        aria-label="決算発表予定日"
        value={value ?? ''}
        onChange={(e) => {
          const v = e.target.value
          if (v === '') onClear()
          else onSave(v)
        }}
      />
      {value !== null && (
        <button type="button" className="link-button" onClick={onClear}>
          取り消す
        </button>
      )}
    </div>
  )
}
