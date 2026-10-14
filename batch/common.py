"""共通処理: 銘柄一覧の読み込み、日足の取得、時価総額の取得"""

import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf
from yfinance.exceptions import YFException

JPX_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xlsx"
DATA_DIR = Path(__file__).parent / "data"
LIST_PATH = DATA_DIR / "data_j.xlsx"
COLUMNS = ["High", "Low", "Close", "Volume"]


def load_prime_list() -> pd.DataFrame:
    """東証プライム（内国株式）の4文字コードの銘柄一覧を取得する。

    JPXのウェブサイトから上場銘柄一覧Excelをダウンロード・キャッシュし、
    東証プライム（内国株式）かつ4文字コードの銘柄を抽出して返す。

    Returns:
        東証プライム銘柄の情報（コード、銘柄名、33業種区分、ticker等）を含むDataFrame。
    """
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


def fetch_daily(
    tickers: list[str],
    period: str = "2y",
    batch_size: int = 100,
    sleep_sec: float = 1.0,
) -> dict[str, pd.DataFrame]:
    """指定した銘柄群の日足データ（High/Low/Close/Volume）をバッチ単位で取得する。

    Args:
        tickers: 取得対象のティッカーシンボル一覧（例: ["7203.T", "6758.T"]）。
        period: 取得期間（デフォルト: "2y"）。
        batch_size: 1回のリクエストで取得する銘柄数（デフォルト: 100）。
        sleep_sec: バッチリクエスト間の待機秒数（デフォルト: 1.0）。

    Returns:
        ティッカーシンボルをキー、日足データ（High, Low, Close, Volume）のDataFrameを値とする辞書。
    """
    result: dict[str, pd.DataFrame] = {}
    start = time.time()

    for i in range(0, len(tickers), batch_size):
        chunk = tickers[i : i + batch_size]
        try:
            df = yf.download(
                chunk,
                period=period,
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                threads=True,
                progress=False,
            )
        except (
            requests.RequestException,
            YFException,
            ValueError,
            RuntimeError,
        ) as e:
            print(f"  バッチ失敗 ({i}-{i + len(chunk)}): {e}")
            continue

        if df is None or not isinstance(df, pd.DataFrame):
            continue

        if not isinstance(df.columns, pd.MultiIndex):
            df = pd.concat({chunk[0]: df}, axis=1)

        for t in chunk:
            try:
                raw_sub = df[t]
            except KeyError:
                continue
            if not isinstance(raw_sub, pd.DataFrame):
                continue
            sub = raw_sub[COLUMNS].dropna(subset=["Close"])
            if not isinstance(sub, pd.DataFrame) or sub.empty:
                continue
            sub_copy = sub.copy()
            sub_copy.index = pd.DatetimeIndex(sub_copy.index).tz_localize(None)
            result[t] = sub_copy

        if len(tickers) > batch_size:
            done = min(i + batch_size, len(tickers))
            print(f"  日足取得 {done}/{len(tickers)} (経過 {time.time() - start:.0f}秒)")
            time.sleep(sleep_sec)

    return result


def get_market_cap(ticker: str) -> float | None:
    """指定した銘柄の時価総額（円）を取得する。

    Args:
        ticker: ティッカーシンボル（例: "7203.T"）。

    Returns:
        時価総額（円）。取得できなかった場合は None。
    """
    try:
        cap = yf.Ticker(ticker).fast_info["market_cap"]
        return float(cap) if cap else None
    except requests.RequestException, YFException, KeyError, TypeError, ValueError:
        return None


def get_earnings_date(ticker: str) -> date | None:
    """指定した銘柄の次の決算発表予定日を取得する。

    yfinanceのカレンダー情報を取得し、今日以降で直近の決算発表予定日を返す。

    Args:
        ticker: ティッカーシンボル（例: "7203.T"）。

    Returns:
        直近の決算発表予定日（date）。取得できなかった場合は None。
    """
    try:
        cal = yf.Ticker(ticker).calendar
        dates = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if dates is None or not isinstance(dates, (list, tuple, pd.Series, set)):
            return None
        today = date.today()
        normalized = [d.date() if isinstance(d, datetime) else d for d in dates]
        future = [d for d in normalized if d >= today]
        return min(future) if future else None
    except requests.RequestException, YFException, KeyError, TypeError, ValueError:
        return None
