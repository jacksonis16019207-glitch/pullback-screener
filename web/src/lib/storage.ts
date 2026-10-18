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

// JSON の読み書き。壊れた値や使えない環境では null を返す（中身の形の確認は呼び出し側で行う）。
export function loadJson(key: string): unknown {
  try {
    const raw = localStorage.getItem(key)
    return raw === null ? null : JSON.parse(raw)
  } catch {
    return null
  }
}

export function saveJson(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // 保存できなくても、画面の動作は続ける
  }
}
