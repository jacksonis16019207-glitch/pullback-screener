# pullback-screener

SBI証券アプリの押し目買い手法で、買うべき銘柄と買いラインを知るためのツール。
売買と売却の通知は、SBI株アプリで自分で行う。

## 構成

```
pullback-screener/
├─ batch/                  # Python: 押し目待ち・買い候補の判定
│  ├─ src/pullback_screener/   # コード本体
│  │  ├─ logic.py              # 判定ロジック（ネットワーク不要）
│  │  ├─ common.py             # 銘柄一覧・日足・時価総額・決算日の取得
│  │  ├─ screener.py           # コマンドの入口（weekly / daily / diagnose）
│  │  └─ paths.py              # ファイルの置き場所
│  ├─ tests/                   # テスト
│  ├─ config.json              # 判定の数値の設定
│  ├─ data/                    # 取得データの保存先（Git管理外）
│  └─ output/                  # 判定結果のJSON（Git管理外）
└─ web/                    # React: 画面（これから作成）
```

## 使い方（batch/ フォルダで）

```
uv sync                              # 初回のみ: 環境づくり
uv run pytest                        # テスト
uv run pullback-screener weekly      # 金曜の引け後: 押し目待ちリストを作る
uv run pullback-screener daily       # 平日の引け後: 買い候補を判定する
uv run pullback-screener run         # 自動実行用: 直近の金曜時点のリスト＋今日の買い候補を作り、通知する
uv run pullback-screener diagnose 2121 2004   # 指定銘柄の判定内容を表示
```

判定の数値（押し目の幅、傾きの下限など）は `batch/config.json` で変える。

### 通知（ntfy）

環境変数 `NTFY_TOPIC` を設定したときだけ、`run` がプッシュ通知を送る（未設定なら送らない）。
`APP_URL` を設定すると、通知をタップしたときにそのURLを開く。
トピック名は他人に知られると通知を読まれるので、長くランダムな文字列にして、リポジトリには書かない。
