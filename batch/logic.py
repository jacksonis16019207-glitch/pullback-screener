"""
判定ロジック（手順1〜8）。ネットワークには依存しない純粋な関数だけを置く。

入力のDataFrameは、日付昇順のindexで、High / Low / Close / Volume の列を持つこと。
"""

import contextlib
import json
from datetime import date, timedelta
from pathlib import Path

import jpholiday
import numpy as np
import pandas as pd


def load_config(path=None) -> dict:
    """設定ファイル（JSON）を読み込んで辞書として返す。

    Args:
        path: 設定ファイルのパス。指定しない場合は同階層の config.json を読み込む。

    Returns:
        読み込んだ設定辞書。
    """
    path = Path(path) if path else Path(__file__).parent / "config.json"
    return json.loads(path.read_text(encoding="utf-8"))


def add_sma(df: pd.DataFrame) -> pd.DataFrame:
    """日足データに25日移動平均線（sma25）および75日移動平均線（sma75）を追加する。

    Args:
        df: 終値列（Close）を含む日足データのDataFrame。

    Returns:
        sma25列およびsma75列が追加されたDataFrame。
    """
    out = df.copy()
    out["sma25"] = out["Close"].rolling(25).mean()
    out["sma75"] = out["Close"].rolling(75).mean()
    return out


def get_high_update_flags(df: pd.DataFrame) -> pd.Series:
    """
    SBI株アプリの「年初来高値」の定義に基づき、高値更新日を判定する。

    各日の高値が、基準期間内のそれ以前の最高値を上回る場合にTrue を返す。
    基準期間は以下のとおり。
    - 1〜3月: 前年1月1日以降
    - 4〜12月: 当年1月1日以降

    Args:
        df: 日付をインデックスとし、日ごとの高値を ``High`` 列に持つ DataFrame。

    Returns:
        各日が高値更新日かどうかを示す bool 型の Series。
        インデックスは入力 DataFrame のインデックスと一致する。
        高値更新日なら True、それ以外は False。
    """
    flags = pd.Series(False, index=df.index)
    dates = pd.DatetimeIndex(df.index)
    start_year = np.where(dates.month <= 3, dates.year - 1, dates.year)

    for year in np.unique(start_year):
        start = pd.Timestamp(int(year), 1, 1)
        seg = df.loc[start:]
        prior_max = seg["High"].expanding().max().shift(1)
        idx = df.index[start_year == year]
        flags.loc[idx] = (df.loc[idx, "High"] > prior_max.loc[idx]).to_numpy()
    return flags


def check_topix_trend(df: pd.DataFrame, cfg: dict) -> tuple[bool, dict]:
    """手順1: TOPIX連動データに基づき、市場全体の地合いが上昇トレンドかを判定する。

    終値＞25日線、25日線＞75日線、および75日線の傾きが基準値以上であることを確認する。

    Args:
        df: 日足データのDataFrame（High, Low, Close, Volume列）。
        cfg: TOPIX判定用の設定辞書（slope_lookback_days, slope_min_pct等）。

    Returns:
        判定結果（合格ならTrue）と判定詳細情報の辞書からなるタプル。
    """
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


def calculate_trend_slope_pct_per_day(close: pd.Series) -> float:
    """終値（対数）に直線を当てはめ、1日あたりの増減率（％）としてトレンドの傾きを計算する。

    期間内の全データ点を使用して回帰分析を行うため、始点・終点のみのブレに左右されない。

    Args:
        close: 終値の時系列データ（Series）。

    Returns:
        1日あたりの平均変化率（％）。
    """
    y = np.log(close.to_numpy(dtype=float))
    x = np.arange(len(y), dtype=float)
    slope = np.polyfit(x, y, 1)[0]
    return float((np.exp(slope) - 1) * 100)


def screen_candidate(df: pd.DataFrame, cfg: dict) -> dict | None:
    """手順2・4・5: 押し目待ちリストの選定条件を満たすかを判定する。

    最新日の移動平均線の位置関係、期間内の維持状況、トレンドの傾き、
    年初来高値更新の有無、急騰日（材料確認要否）のチェックを行う。
    （時価総額の確認は呼び出し側で行う）

    Args:
        df: 対象銘柄の日足データDataFrame。
        cfg: スクリーニング設定辞書。

    Returns:
        条件を満たす場合は銘柄の判定情報辞書、対象外の場合は None。
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
    slope = calculate_trend_slope_pct_per_day(d["Close"].iloc[-n:])
    if slope < t.get("min_slope_pct_per_day", 0.0):
        return None

    flags = get_high_update_flags(d)
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


def check_buy_signal(df: pd.DataFrame, cfg: dict) -> dict | None:
    """手順7〜8: 最新日が押し目買いシグナルの成立日かを判定する。

    以下の条件をすべて満たす場合にシグナル成立とする:
      1. 直近の年初来高値の更新日より後に、終値が25日線の下限〜上限に入った日（押し目）がある
      2. 高値更新日より後、終値が25日線の下限を一度も割っていない
      3. 最新日の終値＞前日の高値、かつ最新日の出来高＞前日の出来高

    Args:
        df: 対象銘柄の日足データDataFrame。
        cfg: スクリーニング設定辞書（pullback下限・上限比率等）。

    Returns:
        シグナル成立時は買いラインやシグナル日を含む情報辞書、不成立時は None。
    """
    p = cfg["pullback"]
    if len(df) < 77:
        return None
    d = add_sma(df)
    flags = get_high_update_flags(d)
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


def _get_holidays(start: date, end: date) -> list[date]:
    """
    指定した期間の 年末年始、祝日を取得する。

    Args:
        start: 開始日
        end: 終了日

    Returns:
        年末年始 + 祝日の集合 (日付の昇順)
    """
    days: set[date] = set()
    for y in range(start.year, end.year + 1):
        days.update([date(y, 1, 1), date(y, 1, 2), date(y, 1, 3), date(y, 12, 31)])
        with contextlib.suppress(ImportError):
            days.update(d for d, _ in jpholiday.year_holidays(y))
    return sorted(days)


def calculate_business_days(start: date, end: date) -> int:
    """
    指定した期間の営業日数を計算する。

    Args:
        start: 開始日
        end: 終了日

    Returns:
        営業日数。end が start より前なら -1。
    """
    if end < start:
        return -1
    return int(
        np.busday_count(
            start + timedelta(days=1),
            end + timedelta(days=1),
            holidays=_get_holidays(start, end),
        )
    )


def has_earnings_within_business_days(
    base: date, earnings: date | None, within: int
) -> bool | None:
    """
    指定した営業日以内に決算日があるかどうか判定する。

    Args:
        base: 基準日
        earnings: 決算日
        within: 営業日数

    Returns:
        基準日 から within 営業日以内に決算日があれば True。
        決算日が分からないときは None（手入力が必要）。
    """
    if earnings is None:
        return None
    n = calculate_business_days(base, earnings)
    return 0 <= n <= within


def diagnose(df: pd.DataFrame, cfg: dict) -> dict:
    """1銘柄が押し目待ちの条件を満たすかを、条件ごとに詳細診断する（確認・デバッグ用）。

    Args:
        df: 対象銘柄の日足データDataFrame。
        cfg: スクリーニング設定辞書。

    Returns:
        各判定条件の充足状況や詳細情報を含む辞書。
    """
    t, s = cfg["trend"], cfg["screen"]
    n = t["lookback_days"]
    d = add_sma(df)
    last = d.iloc[-1]
    win = d.iloc[-n:]
    below25 = win.index[win["Close"] <= win["sma25"]]
    below75 = win.index[win["sma25"] <= win["sma75"]]

    flags = get_high_update_flags(d)
    updates = flags[flags].index
    last_update = updates[-1] if len(updates) else None
    days_ago = None
    if last_update is not None:
        loc = d.index.get_loc(last_update)
        if isinstance(loc, int):
            loc_idx = loc
        elif isinstance(loc, slice):
            loc_idx = loc.start or 0
        else:
            loc_idx = int(np.where(loc)[0][0])
        days_ago = int(len(d) - 1 - loc_idx)

    pct = d["Close"].pct_change() * 100
    surge = pct.iloc[-s["surge_lookback_days"] :]

    def format_dates(idx):
        return [x.strftime("%Y-%m-%d") for x in idx]

    return {
        "データ行数": len(d),
        "最新日": d.index[-1].strftime("%Y-%m-%d"),
        "終値/25日線/75日線": [
            round(float(last["Close"]), 1),
            round(float(last["sma25"]), 1),
            round(float(last["sma75"]), 1),
        ],
        "最新日の条件(終値>25日線>75日線)": bool(last["Close"] > last["sma25"] > last["sma75"]),
        f"直近{n}営業日で終値<=25日線の日数": len(below25),
        "  終値<=25日線の最初と最後の日": [format_dates(below25[:1]), format_dates(below25[-1:])],
        f"直近{n}営業日で25日線<=75日線の日数": len(below75),
        "  25日線<=75日線の最初と最後の日": [format_dates(below75[:1]), format_dates(below75[-1:])],
        "直近の年初来高値更新日": last_update.strftime("%Y-%m-%d")
        if last_update is not None
        else None,
        "  それは何営業日前か": days_ago,
        "  設定の期間内か": days_ago is not None and days_ago < s["high_update_lookback_days"],
        "直近の+5%以上の日": format_dates(surge.index[surge >= s["surge_pct"]]),
    }
