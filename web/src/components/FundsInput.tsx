type Props = {
  value: number
  onChange: (value: number) => void
}

export function FundsInput({ value, onChange }: Props) {
  return (
    <label className="funds">
      <span className="funds__label">投資資金（円）</span>
      <input
        className="funds__input"
        type="number"
        inputMode="numeric"
        min={0}
        step={10000}
        placeholder="例: 500000"
        value={value === 0 ? '' : value}
        onChange={(e) => {
          const n = Number(e.target.value)
          onChange(Number.isFinite(n) && n > 0 ? n : 0)
        }}
      />
    </label>
  )
}
