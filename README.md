# pullback-screener

SBI証券アプリの押し目買い手法で、買うべき銘柄と買いラインを知るためのツール。
売買と売却の通知は、SBI株アプリで自分で行う。

## 構成

```
pullback-screener/
├─ batch/                       # Python: 押し目待ち・買い候補の判定
│  ├─ src/pullback_screener/    # コード本体（logic / common / screener / paths）
│  ├─ tests/                    # テスト（pytest）
│  ├─ config.json               # 判定の数値の設定
│  ├─ data/                     # 取得データの保存先（Git管理外）
│  └─ output/                   # 判定結果のJSON（Git管理外）
└─ web/                         # React + TypeScript + Vite: 画面
   ├─ public/data/              # 画面が読むJSON（Git管理外。batch/output からコピー）
   └─ src/
      ├─ components/            # 画面の部品
      ├─ hooks/                 # データ取得・保存の処理
      ├─ lib/                   # 計算・整形（画面に依存しない関数）
      └─ types/                 # JSONの型
```

## batch（batch/ フォルダで）

```
uv sync
uv run pytest
uv run pullback-screener weekly      # 金曜の引け後: 押し目待ちリストを作る
uv run pullback-screener daily       # 平日の引け後: 買い候補を判定する
uv run pullback-screener diagnose 2121 2004
```

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
