import type { NewsSelection } from '../lib/news'

type Props = {
  needsCheck: boolean
  selection: NewsSelection | null
}

export function NewsBadge({ needsCheck, selection }: Props) {
  if (selection?.verdict === 'oneoff') return <li className="badge badge--info">単発として除外</li>
  if (selection?.verdict === 'continuing') {
    return <li className="badge badge--ok">材料確認済み（継続）</li>
  }
  if (needsCheck) return <li className="badge badge--warn">材料ニュースの選択が必要</li>
  return null
}
