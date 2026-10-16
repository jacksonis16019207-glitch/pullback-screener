export function formatYen(value: number): string {
  return `${value.toLocaleString('ja-JP', { maximumFractionDigits: 1 })}円`
}

export function formatPercent(value: number): string {
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('ja-JP')
}
