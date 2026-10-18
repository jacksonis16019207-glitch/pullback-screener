# pullback-screener

SBI証券アプリの押し目買い手法で、買うべき銘柄と買いラインを知るためのツール。
売買と売却の通知は、SBI株アプリで自分で行う。

## 構成

```
pullback-screener/
├─ .github/workflows/           # 定期実行と画面の公開（GitHub Actions）
├─ batch/                       # Python: 押し目待ち・買い候補の判定
│  ├─ src/pullback_screener/    # コード本体（logic / common / screener / notify / paths）
│  ├─ tests/                    # テスト（pytest）
│  ├─ config.json               # 判定の数値の設定
│  ├─ data/                     # 取得データの保存先（Git管理外）
│  └─ output/                   # 判定結果のJSON（Git管理外）
│     ├─ watchlist.json         #   押し目待ちリスト
│     ├─ buy_candidates.json    #   買い候補リスト
│     └─ charts.json            #   銘柄詳細画面のチャートと判定補助の数字
└─ web/                         # React + TypeScript + Vite: 画面
   ├─ public/data/              # 画面が読むJSON（Git管理外。batch/output からコピー）
   └─ src/
      ├─ pages/                 # 画面（一覧、銘柄詳細）
      ├─ components/            # 画面の部品
      ├─ hooks/                 # データ取得・保存の処理
      ├─ lib/                   # 計算・整形（画面に依存しない関数）
      └─ types/                 # JSONの型
```

## batch（batch/ フォルダで）

```
uv sync
uv run pytest
uv run pullback-screener run         # 自動実行用: 直近の金曜時点のリスト＋今日の買い候補を作り、通知する
uv run pullback-screener weekly      # 金曜の引け後: 押し目待ちリストを作る
uv run pullback-screener daily       # 平日の引け後: 買い候補を判定する
uv run pullback-screener diagnose 2121 2004
```

判定の数値（押し目の幅、傾きの下限など）は `batch/config.json` で変える。

### 通知（ntfy）

環境変数 `NTFY_TOPIC` を設定したときだけ、`run` がプッシュ通知を送る（未設定なら送らない）。
`APP_URL` を設定すると、通知をタップしたときにそのURLを開く。
トピック名は他人に知られると通知を読まれるので、長くランダムな文字列にして、リポジトリには書かない。

## web（web/ フォルダで）

```
npm install
npm run dev        # 開発サーバー（http://localhost:5173）
npm run build      # 型チェックと本番用ビルド
```

画面に表示するJSONは、リポジトリ直下で次のコマンドでコピーする（PowerShell）。

```
Copy-Item batch\output\*.json web\public\data\
```
