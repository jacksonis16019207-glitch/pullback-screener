"""
データ取得の検証スクリプト（ステップ2）

目的: 東証プライム全銘柄の日足が yfinance で安定して取れるか、
      何分かかるかを確認する。

使い方（リポジトリ直下で）:
    python batch/check_data.py 100    # まず100銘柄だけ試す
    python batch/check_data.py        # 全銘柄
"""

import sys
import time
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

JPX_URL = (
    "https://www.jpx.co.jp/markets/statistics-equities/misc/"
    "tvdivq0000001vg2-att/data_j.xlsx"
)
DATA_DIR = Path(__file__).parent / "data"
LIST_PATH = DATA_DIR / "data_j.xlsx"

BATCH_SIZE = 100  # 1回のリクエストで取る銘柄数
SLEEP_SEC = 1.0  # バッチ間の待ち時間（制限対策）
MIN_ROWS = 200  # 1年分としてこの行数以上あればOKとみなす


def load_prime_list() -> pd.DataFrame:
    """JPXの上場銘柄一覧から東証プライムを抽出する。"""
    DATA_DIR.mkdir(exist_ok=True)
    if not LIST_PATH.exists():
        print("JPXの銘柄一覧をダウンロード中...")
        res = requests.get(JPX_URL, timeout=30)
        res.raise_for_status()
        LIST_PATH.write_bytes(res.content)

    df = pd.read_excel(LIST_PATH, dtype={"コード": str})
    prime = df[df["市場・商品区分"] == "プライム（内国株式）"].copy()
    prime = prime[prime["コード"].str.len() == 4].copy()
    prime["ticker"] = prime["コード"] + ".T"
    return prime


def fetch_batch(tickers: list[str]) -> pd.DataFrame:
    df = yf.download(
        tickers,
        period="1y",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False,
    )
    # 1銘柄だけのときは列が階層構造にならないので揃える
    if not isinstance(df.columns, pd.MultiIndex):
        df = pd.concat({tickers[0]: df}, axis=1)
    return df


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    prime = load_prime_list()
    tickers = prime["ticker"].tolist()
    print(f"東証プライム: {len(tickers)} 銘柄")
    if limit:
        tickers = tickers[:limit]
        print(f"テストのため先頭 {limit} 銘柄のみ取得します")

    ok, ng = [], []
    start = time.time()

    for i in range(0, len(tickers), BATCH_SIZE):
        chunk = tickers[i : i + BATCH_SIZE]
        try:
            df = fetch_batch(chunk)
        except Exception as e:  # noqa: BLE001
            print(f"  バッチ失敗 ({i}-{i + len(chunk)}): {e}")
            ng.extend(chunk)
            continue

        for t in chunk:
            try:
                sub = df[t].dropna(how="all")
            except KeyError:
                ng.append(t)
                continue
            (ok if len(sub) >= MIN_ROWS else ng).append(t)

        done = min(i + BATCH_SIZE, len(tickers))
        print(f"  {done}/{len(tickers)} 完了 (経過 {time.time() - start:.0f}秒)")
        time.sleep(SLEEP_SEC)

    elapsed = time.time() - start
    print()
    print("===== 結果 =====")
    print(f"所要時間: {elapsed / 60:.1f} 分")
    print(f"取得OK : {len(ok)} 銘柄")
    print(f"取得NG : {len(ng)} 銘柄")
    if ng:
        print("NGの例(先頭20):", ng[:20])


if __name__ == "__main__":
    main()
