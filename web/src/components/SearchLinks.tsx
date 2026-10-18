import { buildSearchGroups, kabutanNewsUrl } from '../lib/search'

type Props = {
  code: string
  name: string
  sector: string
  surgeDate: string | null
}

export function SearchLinks({ code, name, sector, surgeDate }: Props) {
  const groups = buildSearchGroups(name, sector, surgeDate)

  return (
    <div className="search">
      {groups.map((g) => (
        <div key={g.title} className="search__group">
          <p className="search__title">{g.title}</p>
          <div className="chips">
            {g.links.map((l) => (
              <a
                key={l.label}
                className="chip chip--link"
                href={l.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {l.label}
              </a>
            ))}
          </div>
        </div>
      ))}
      <div className="search__group">
        <p className="search__title">ニュースサイト</p>
        <div className="chips">
          <a
            className="chip chip--link"
            href={kabutanNewsUrl(code)}
            target="_blank"
            rel="noopener noreferrer"
          >
            株探のニュース
          </a>
        </div>
      </div>
    </div>
  )
}
