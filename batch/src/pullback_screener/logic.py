"""
判定ロジック（手順1〜8）。ネットワークには依存しない純粋な関数だけを置く。

入力のDataFrameは、日付昇順のindexで、High / Low / Close / Volume の列を持つこと。
"""
import json
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .paths import CONFIG_PATH


def load_config(path=None) -> dict:
    path = Path(path) if path else CONFIG_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def add_sma(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["sma25"] = out["Close"].rolling(25).mean()
    out["sma75"] = out["Close"].rolling(75).mean()
    return out


def high_update_flags(df: pd.DataFrame) -> pd.Series:
    """
    SBI株アプリの「年初来高値」の定義で、各日が高値更新日かどうかを返す。
      1〜3月: 前年1月1日以降の高値を基準にする
      4〜12月: 当年1月1日以降の高値を基準にする
    その日の高値が、基準期間内のそれ以前の最高値を上回れば更新。
    """
    flags = pd.Series(False, index=df.index)
    start_year = np.where(df.index.month <= 3, df.index.year - 1, df.index.year)

    for year in np.unique(start_year):
        start = pd.Timestamp(int(year), 1, 1)
        seg = df.loc[start:]
        prior_max = seg["High"].expanding().max().shift(1)
        idx = df.index[start_year == year]
        flags.loc[idx] = (df.loc[idx, "High"] > prior_max.loc[idx]).to_numpy()
    return flags


def topix_ok(df: pd.DataFrame, cfg: dict) -> tuple[bool, dict]:
    """手順1: 終値＞25日線、25日線＞75日線、75日線が明確に下向きでない。"""
    look = cfg["slope_lookback_days"]
    if len(df) < 75 + look + 1:
        return False, {"reason": "データ不足"}
    d = add_sma(df)
    last = d.iloc[-1]
    prev75 = d["sma75"].iloc[-1 - look]
    slope = (last["sma75"] / prev75 - 1) * 100
    c1 = bool(last["Close"] > last["sma25"])
    c2 = bool(last["sma25"] > last["sma75"])
    c3 = bool(slope >= cfg["slope_min_pct"])
    return (c1 and c2 and c3), {
        "as_of": d.index[-1].strftime("%Y-%m-%d"),
        "close_gt_sma25": c1,
        "sma25_gt_sma75": c2,
        "sma75_slope_pct": round(float(slope), 2),
        "sma75_slope_ok": c3,
    }


def trend_slope_pct_per_day(close: pd.Series) -> float:
    """
    終値（対数）に直線を当てはめたときの傾きを、1日あたりの増減率（％）で返す。
    期間の全部の点を使うので、始点・終点の1日だけに左右されない。
    """
    y = np.log(close.to_numpy(dtype=float))
    x = np.arange(len(y), dtype=float)
    slope = np.polyfit(x, y, 1)[0]
    return float((np.exp(slope) - 1) * 100)


def screen_candidate(df: pd.DataFrame, cfg: dict) -> dict | None:
    """
    手順2・4・5（時価総額の確認は呼び出し側で行う）。
    押し目待ちリストに入れる銘柄なら情報を返し、対象外なら None。
    """
    s = cfg["screen"]
    t = cfg["trend"]
    n = t["lookback_days"]
    max_price = t["price_above_sma25_max_violation_days"]
    max_sma = t["sma25_above_sma75_max_violation_days"]
    # 許容日数が期間の日数以上なら「期間の制限なし」。最新日の条件だけを見る
    check_window = max_price < n or max_sma < n
    if len(df) < (75 + n if check_window else 76):
        return None

    d = add_sma(df)
    last = d.iloc[-1]
    ratio = 1 + s.get("close_below_sma25_tolerance_pct", 0.0) / 100
    # 最新日の条件: 終値＞25日線（許容幅つき）、25日線＞75日線
    if not (last["Close"] > last["sma25"] * ratio and last["sma25"] > last["sma75"]):
        return None

    # 日足6か月（約125営業日）での位置関係。違反した日数が許容を超えたら対象外
    win = d.iloc[-n:]
    v_price = int((win["Close"] <= win["sma25"] * ratio).sum())
    v_sma = int((win["sma25"] <= win["sma75"]).sum())
    if v_price > max_price or v_sma > max_sma:
        return None

    # 全体として上昇傾向か: 直近約6か月の終値（対数）の回帰直線の傾き（1日あたり％）
    slope = trend_slope_pct_per_day(d["Close"].iloc[-n:])
    if slope < t.get("min_slope_pct_per_day", 0.0):
        return None

    flags = high_update_flags(d)
    recent = flags.iloc[-s["high_update_lookback_days"] :]
    if not recent.any():
        return None
    last_update = recent[recent].index[-1]

    pct = d["Close"].pct_change() * 100
    surge = pct.iloc[-s["surge_lookback_days"] :]
    surge_dates = [x.strftime("%Y-%m-%d") for x in surge[surge >= s["surge_pct"]].index]

    return {
        "close": round(float(last["Close"]), 1),
        "sma25": round(float(last["sma25"]), 1),
        "sma75": round(float(last["sma75"]), 1),
        "last_high_update": last_update.strftime("%Y-%m-%d"),
        "trend_slope_pct_per_day": round(slope, 3),
        "trend_violations": {"price_below_sma25": v_price, "sma25_below_sma75": v_sma},
        "needs_news_check": len(surge_dates) > 0,
        "surge_dates": surge_dates,
    }


def buy_signal(df: pd.DataFrame, cfg: dict) -> dict | None:
    """
    手順7〜8。最新日が買い候補の成立日なら情報を返し、そうでなければ None。
      1. 直近の年初来高値の更新日より後に、終値が25日線の下限〜上限に入った日がある
      2. 更新日より後、終値が25日線の下限を一度も割っていない
      3. 最新日の終値＞前日の高値、かつ最新日の出来高＞前日の出来高
    買いラインは、最新日（シグナル日）の高値。
    """
    p = cfg["pullback"]
    if len(df) < 77:
        return None
    d = add_sma(df)
    flags = high_update_flags(d)
    if not flags.any():
        return None

    last_update = flags[flags].index[-1]
    after = d.loc[d.index > last_update]
    if len(after) < 2:  # 押し目の日とシグナル日の最低2日が必要
        return None

    ratio = (after["Close"] / after["sma25"] - 1) * 100
    if (ratio < p["lower_pct"]).any():
        return None

    pullback = ratio.iloc[:-1]
    if not ((pullback >= p["lower_pct"]) & (pullback <= p["upper_pct"])).any():
        return None

    today, prev = d.iloc[-1], d.iloc[-2]
    if not (today["Close"] > prev["High"] and today["Volume"] > prev["Volume"]):
        return None

    return {
        "signal_date": d.index[-1].strftime("%Y-%m-%d"),
        "buy_line": round(float(today["High"]), 1),
        "close": round(float(today["Close"]), 1),
        "volume": int(today["Volume"]),
        "prev_volume": int(prev["Volume"]),
        "last_high_update": last_update.strftime("%Y-%m-%d"),
        "pullback_min_pct": round(float(pullback.min()), 2),
    }


def _holidays(start: date, end: date) -> list[date]:
    """取引所の休場日（祝日＋年末年始）。jpholiday が入っていれば祝日も使う。"""
    days: set[date] = set()
    for y in range(start.year, end.year + 1):
        days.update([date(y, 1, 1), date(y, 1, 2), date(y, 1, 3), date(y, 12, 31)])
        try:
            import jpholiday

            days.update(d for d, _ in jpholiday.year_holidays(y))
        except ImportError:
            pass
    return sorted(days)


def business_days_between(start: date, end: date) -> int:
    """start の翌日から end まで（end を含む）の営業日数。end が start より前なら -1。"""
    if end < start:
        return -1
    return int(
        np.busday_count(
            start + timedelta(days=1),
            end + timedelta(days=1),
            holidays=_holidays(start, end),
        )
    )


def earnings_soon(base: date, earnings: date | None, within: int) -> bool | None:
    """
    手順10: base（基準日）から within 営業日以内に決算があれば True。
    決算日が分からないときは None（手入力が必要）。
    """
    if earnings is None:
        return None
    n = business_days_between(base, earnings)
    return 0 <= n <= within


def diagnose(df: pd.DataFrame, cfg: dict) -> dict:
    """1銘柄が押し目待ちの条件を満たすかを、条件ごとに説明する（確認用）。"""
    t, s = cfg["trend"], cfg["screen"]
    n = t["lookback_days"]
    d = add_sma(df)
    last = d.iloc[-1]
    win = d.iloc[-n:]
    below25 = win.index[win["Close"] <= win["sma25"]]
    below75 = win.index[win["sma25"] <= win["sma75"]]

    flags = high_update_flags(d)
    updates = flags[flags].index
    last_update = updates[-1] if len(updates) else None
    days_ago = None
    if last_update is not None:
        days_ago = int(len(d) - 1 - d.index.get_loc(last_update))

    pct = d["Close"].pct_change() * 100
    surge = pct.iloc[-s["surge_lookback_days"] :]

    def fmt(idx):
        return [x.strftime("%Y-%m-%d") for x in idx]

    return {
        "データ行数": len(d),
        "最新日": d.index[-1].strftime("%Y-%m-%d"),
        "終値/25日線/75日線": [round(float(last["Close"]), 1), round(float(last["sma25"]), 1), round(float(last["sma75"]), 1)],
        "最新日の条件(終値>25日線>75日線)": bool(last["Close"] > last["sma25"] > last["sma75"]),
        f"直近{n}営業日で終値<=25日線の日数": len(below25),
        "  その最初と最後の日": [fmt(below25[:1]), fmt(below25[-1:])],
        f"直近{n}営業日で25日線<=75日線の日数": len(below75),
        "  その最初と最後の日": [fmt(below75[:1]), fmt(below75[-1:])],
        "直近の年初来高値更新日": last_update.strftime("%Y-%m-%d") if last_update is not None else None,
        "  それは何営業日前か": days_ago,
        "  設定の期間内か": days_ago is not None and days_ago < s["high_update_lookback_days"],
        "直近の+5%以上の日": fmt(surge.index[surge >= s["surge_pct"]]),
    }


def read_jpx_earnings(path) -> dict[str, list[date]]:
    """
    JPXの決算発表予定日Excel（kessanMM_DDDD.xlsx）から、{銘柄コード: [予定日, ...]} を返す。
    先頭の数行は題名なので、「決算発表予定日」の見出し行を探し、その次の行から読む。
    列: 0=決算発表予定日, 1=コード
    """
    df = pd.read_excel(path, header=None, dtype=str)
    first = df.iloc[:, 0].astype(str)
    header = first[first.str.contains("決算発表予定日", na=False)]
    if header.empty:
        return {}
    body = df.iloc[header.index[0] + 1 :, :2].copy()
    body.columns = ["date", "code"]
    body["date"] = pd.to_datetime(body["date"], errors="coerce")
    body = body.dropna(subset=["date", "code"])

    result: dict[str, list[date]] = {}
    for d, code in zip(body["date"], body["code"]):
        key = unicodedata.normalize("NFKC", str(code)).strip()
        if key.endswith(".0"):  # 数値セルが 2678.0 と読まれた場合
            key = key[:-2]
        result.setdefault(key, []).append(d.date())
    return result


def next_date(dates: list[date], today: date) -> date | None:
    """today 以降で最も近い日付。なければ None。"""
    future = [d for d in dates if d >= today]
    return min(future) if future else None
