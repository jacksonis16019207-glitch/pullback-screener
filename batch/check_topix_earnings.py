"""
^TOPX と決算日がyfinanceで取れるかの確認スクリプト。

    uv run batch/check_topix_earnings.py
"""

import requests
import yfinance as yf
from yfinance.exceptions import YFException


def check_topix() -> None:
    """TOPIX指数および連動ETFの日足データ取得可否を確認する。"""
    print("===== TOPIX =====")
    for ticker in ("^TOPX", "1306.T"):
        try:
            df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=False)
            if df is None or df.empty:
                print(f"{ticker}: データなし")
            else:
                print(f"{ticker}: {len(df)}行, 最新日 {df.index[-1].date()}")
        except (
            requests.RequestException,
            YFException,
            ValueError,
            RuntimeError,
        ) as e:
            print(f"{ticker}: 失敗 {e}")


def check_earnings() -> None:
    """主要銘柄の決算発表予定日データがyfinanceから取得可能かを確認する。"""
    print()
    print("===== 決算日 =====")
    for ticker in ("7203.T", "6758.T", "9984.T", "8035.T", "4063.T"):
        print(f"--- {ticker} ---")
        tk = yf.Ticker(ticker)
        try:
            print("calendar:", tk.calendar)
        except (
            requests.RequestException,
            YFException,
            KeyError,
            TypeError,
            ValueError,
        ) as e:
            print("calendar 失敗:", e)
        try:
            print("earnings_dates:")
            print(tk.get_earnings_dates(limit=4))
        except (
            requests.RequestException,
            YFException,
            KeyError,
            TypeError,
            ValueError,
        ) as e:
            print("earnings_dates 失敗:", e)


if __name__ == "__main__":
    check_topix()
    check_earnings()
