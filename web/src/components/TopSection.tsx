import { NavLink } from 'react-router-dom'
import { formatDateTime } from '../lib/format'
import type { Topix } from '../types/screener'
import { FundsInput } from './FundsInput'

type Props = {
  topix: Topix
  generatedAt: string
  funds: number
  onFundsChange: (value: number) => void
  counts: { buy: number; watch: number; review: number }
}

function tabClass({ isActive }: { isActive: boolean }): string {
  return `tab${isActive ? ' tab--active' : ''}`
}

// 一覧と要確認の画面で共通の、上の部分（タイトル・TOPIX・資金・タブ）
export function TopSection({ topix, generatedAt, funds, onFundsChange, counts }: Props) {
  return (
    <>
      <h1 className="title">押し目スクリーナー</h1>

      <p className={`topix ${topix.ok ? 'topix--ok' : 'topix--ng'}`}>
        TOPIX判定: {topix.ok ? '○（新規買いOK）' : '×（新規買いは見送り）'}
      </p>
      <p className="updated">更新: {formatDateTime(generatedAt)}</p>

      <FundsInput value={funds} onChange={onFundsChange} />

      <nav className="tabs">
        <NavLink to="/" end className={tabClass}>
          買い候補 {counts.buy}
        </NavLink>
        <NavLink to="/watch" className={tabClass}>
          押し目待ち {counts.watch}
        </NavLink>
        <NavLink to="/review" className={tabClass}>
          要確認 {counts.review}
        </NavLink>
      </nav>
    </>
  )
}
