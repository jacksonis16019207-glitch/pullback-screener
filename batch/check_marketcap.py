"""
時価総額の取得検証スクリプト（ステップ2の続き）

目的: yfinance で時価総額が取れるか、1銘柄あたり何秒かかるかを確認する。
      本番では、価格条件で絞った後の少数の銘柄にだけ使う想定。

使い方（リポジトリ直下で）:
    uv run batch/check_marketcap.py        # 先頭30銘柄
    uv run batch/check_marketcap.py 100    # 先頭100銘柄
"""

import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

LIST_PATH = Path(__file__).parent / "data" / "data_j.xlsx"
THRESHOLD = 100_000_000_000  # 1000億円


def load_prime_list() -> pd.DataFrame:
    df = pd.read_excel(LIST_PATH, dtype={"コード": str})
    prime = df[df["市場・商品区分"] == "プライム（内国株式）"].copy()
    prime = prime[prime["コード"].str.len() == 4].copy()
    prime["ticker"] = prime["コード"] + ".T"
    return prime


def get_market_cap(ticker: str):
    """時価総額（円）を返す。取れなければ None。"""
    try:
        cap = yf.Ticker(ticker).fast_info["market_cap"]
        return float(cap) if cap else None
    except Exception:  # noqa: BLE001
        return None


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    prime = load_prime_list().head(n)

    rows = []
    start = time.time()
    for _, r in prime.iterrows():
        t0 = time.time()
        cap = get_market_cap(r["ticker"])
        rows.append((r["ticker"], r["銘柄名"], cap, time.time() - t0))

    elapsed = time.time() - start
    ok = [x for x in rows if x[2] is not None]
    ng = [x for x in rows if x[2] is None]
    big = [x for x in ok if x[2] >= THRESHOLD]

    print("===== サンプル（先頭5件）=====")
    for t, name, cap, sec in rows[:5]:
        cap_text = f"{cap / 1e8:,.0f}億円" if cap else "取得失敗"
        print(f"{t} {name}: {cap_text} ({sec:.2f}秒)")

    print()
    print("===== 結果 =====")
    print(f"対象 {len(rows)} 銘柄 / 所要時間 {elapsed:.1f} 秒")
    print(f"1銘柄あたり平均 {elapsed / len(rows):.2f} 秒")
    print(f"取得OK {len(ok)} / NG {len(ng)}")
    print(f"1000億円以上 {len(big)} 銘柄")
    if ng:
        print("NGの例:", [x[0] for x in ng[:10]])


if __name__ == "__main__":
    main()
