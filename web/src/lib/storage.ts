// localStorage の読み書き。使えない環境でもアプリが止まらないように try/catch で包む。

export function loadNumber(key: string, fallback: number): number {
  try {
    const raw = localStorage.getItem(key)
    const n = raw === null ? Number.NaN : Number(raw)
    return Number.isFinite(n) ? n : fallback
  } catch {
    return fallback
  }
}

export function saveNumber(key: string, value: number): void {
  try {
    localStorage.setItem(key, String(value))
  } catch {
    // 保存できなくても、画面の動作は続ける
  }
}
