// 材料ニュースを調べるための、検索リンクを作る。

export type SearchLink = { label: string; url: string }
export type SearchGroup = { title: string; links: SearchLink[] }

function google(query: string): string {
  return `https://www.google.com/search?q=${encodeURIComponent(query)}`
}

// "2026-10-15" → "10月15日"
function monthDay(date: string): string {
  const [, m, d] = date.split('-')
  return `${Number(m)}月${Number(d)}日`
}

export function kabutanNewsUrl(code: string): string {
  return `https://kabutan.jp/stock/news?code=${encodeURIComponent(code)}`
}

export function buildSearchGroups(
  name: string,
  sector: string,
  surgeDate: string | null,
): SearchGroup[] {
  const reason: SearchLink[] = [
    { label: '急騰の理由', url: google(`${name} 株価 急騰 理由`) },
    { label: '適時開示', url: google(`${name} 適時開示`) },
  ]
  if (surgeDate !== null) {
    const md = monthDay(surgeDate)
    reason.push({ label: `${md}のニュース`, url: google(`${name} ${md}`) })
  }

  return [
    { title: '原因を探す', links: reason },
    {
      title: '材料の種類別',
      links: [
        { label: '決算', url: google(`${name} 決算 上振れ`) },
        { label: '上方修正', url: google(`${name} 上方修正`) },
        { label: 'TOB', url: google(`${name} TOB 公開買付け`) },
        { label: '受注', url: google(`${name} 受注`) },
        { label: '提携', url: google(`${name} 提携`) },
        { label: '承認・治験', url: google(`${name} 承認 治験`) },
        { label: '政策', url: google(`${sector} 政策 関連銘柄`) },
      ],
    },
    {
      title: '単発か継続かを見る',
      links: [
        { label: '目標株価の引き上げ', url: google(`${name} 目標株価 引き上げ`) },
        { label: '格上げ', url: google(`${name} 格上げ`) },
        { label: '株価の続伸', url: google(`${name} 株価 続伸`) },
        { label: '同業の動き', url: google(`${sector} 株価 上昇`) },
      ],
    },
  ]
}
