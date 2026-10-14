"""
判定ロジックの動作確認（ネットワーク不要）。

    uv run batch/test_logic.py

作り物の株価データで、期待どおりに判定されるかを確かめる。
全部「OK」と出れば、ロジックの基本動作は正しい。
"""

from datetime import date
from typing import Any

import logic
import numpy as np
import pandas as pd

# テスト専用の固定設定（config.json を調整してもテスト結果が変わらないようにする）
CFG: dict[str, Any] = {
    "topix": {"ticker": "1306.T", "slope_lookback_days": 20, "slope_min_pct": -1.0},
    "screen": {
        "high_update_lookback_days": 20,
        "min_market_cap_oku": 1000,
        "surge_pct": 5.0,
        "surge_lookback_days": 5,
        "close_below_sma25_tolerance_pct": 0.0,
    },
    "trend": {
        "lookback_days": 125,
        "price_above_sma25_max_violation_days": 125,
        "sma25_above_sma75_max_violation_days": 125,
        "min_slope_pct_per_day": 0.0,
    },
    "pullback": {"lower_pct": -2.0, "upper_pct": 3.0},
    "earnings": {"skip_within_business_days": 5},
}


def make_df(closes, vols=None, start="2025-06-02") -> pd.DataFrame:
    """テスト用の日足株価DataFrameを生成する。

    Args:
        closes: 終値のリストまたは配列。
        vols: 出来高のリストまたは配列。省略時は1000.0で固定。
        start: 開始日（YYYY-MM-DD形式、デフォルト: "2025-06-02"）。

    Returns:
        High, Low, Close, Volume列を持つテスト用DataFrame。
    """
    idx = pd.bdate_range(start, periods=len(closes))
    c = np.array(closes, dtype=float)
    v = np.full(len(c), 1000.0) if vols is None else np.array(vols, dtype=float)
    return pd.DataFrame({"High": c * 1.01, "Low": c * 0.99, "Close": c, "Volume": v}, index=idx)


def check(name: str, cond: bool) -> None:
    """テスト条件を検証し、結果を表示する。不合格時は異常終了する。

    Args:
        name: テストケース名。
        cond: 検証する条件（Trueなら合格）。

    Raises:
        SystemExit: 条件がFalse（不合格）の場合。
    """
    print(("OK   " if cond else "NG   ") + name)
    if not cond:
        raise SystemExit(1)


UP = list(np.linspace(100, 300, 200))  # 上昇トレンド（最終日が年初来高値）


def test_high_update_sbi_definition() -> None:
    """SBI証券基準の年初来高値更新ロジック（1〜3月と4月以降の基準期間切り替え）をテストする。"""
    # 2025年に高値100を付けた後、2026年1月に95（更新ではない）と105（更新）
    df = pd.DataFrame(
        {
            "High": [100, 90, 95, 105],
            "Low": [90, 80, 85, 95],
            "Close": [95, 85, 90, 100],
            "Volume": [1000] * 4,
        },
        index=pd.to_datetime(["2025-06-02", "2025-12-26", "2026-01-05", "2026-01-06"]),
    )
    f = logic.get_high_update_flags(df)
    check("1〜3月は前年1月からの高値を基準にする（95は更新でない）", not f["2026-01-05"])
    check("1〜3月は前年の高値を超えれば更新（105は更新）", bool(f["2026-01-06"]))

    # 4月以降は当年1月からが基準（前年の高値100は無関係になる）
    df2 = pd.DataFrame(
        {
            "High": [100, 80, 85, 90],
            "Low": [90, 70, 75, 80],
            "Close": [95, 75, 80, 85],
            "Volume": [1000] * 4,
        },
        index=pd.to_datetime(["2025-06-02", "2026-01-05", "2026-03-31", "2026-04-01"]),
    )
    f2 = logic.get_high_update_flags(df2)
    check("4月以降は当年1月からが基準（前年の高値を無視）", bool(f2["2026-04-01"]))
    check("3月末はまだ前年が基準（更新でない）", not f2["2026-03-31"])


def test_topix() -> None:
    """TOPIXのトレンド判定ロジック（上昇・下降）をテストする。"""
    ok, _ = logic.check_topix_trend(make_df(UP), CFG["topix"])
    check("TOPIX: 上昇トレンドは○", ok)
    down = list(np.linspace(300, 100, 200))
    ok, _ = logic.check_topix_trend(make_df(down), CFG["topix"])
    check("TOPIX: 下降トレンドは×", not ok)


def test_screen_candidate() -> None:
    """押し目待ちスクリーニング条件（上昇トレンド、横ばい・下降除外、急騰日検知）をテストする。"""
    check(
        "押し目待ち: 高値更新直後の上昇トレンド銘柄は対象",
        logic.screen_candidate(make_df(UP), CFG) is not None,
    )
    flat = [200.0] * 200
    check(
        "押し目待ち: 高値更新のない横ばい銘柄は対象外",
        logic.screen_candidate(make_df(flat), CFG) is None,
    )
    down = list(np.linspace(300, 100, 200))
    check("押し目待ち: 下降トレンドは対象外", logic.screen_candidate(make_df(down), CFG) is None)

    surge = UP[:-1] + [UP[-2] * 1.08]
    c = logic.screen_candidate(make_df(surge), CFG)
    check(
        "押し目待ち: 直近5日に+5%以上の日があれば材料確認が必要",
        c is not None and c["needs_news_check"],
    )


def test_trend_over_period() -> None:
    """期間中の移動平均線乖離許容日数および25日線割れ許容幅の判定ロジックをテストする。"""
    import copy

    strict = copy.deepcopy(CFG)
    strict["trend"]["price_above_sma25_max_violation_days"] = 0
    strict["trend"]["sma25_above_sma75_max_violation_days"] = 0

    dip = list(UP)
    for i in range(-60, -55):  # 6か月の途中で5日だけ25日線を割る
        dip[i] = dip[i] * 0.85
    df = make_df(dip)
    check(
        "トレンド: 既定では期間の制限なし（最新日の条件のみ）",
        logic.screen_candidate(df, CFG) is not None,
    )
    check(
        "トレンド: 許容0日にすると、途中で25日線を割った銘柄は対象外",
        logic.screen_candidate(df, strict) is None,
    )

    loose = copy.deepcopy(strict)
    loose["trend"]["price_above_sma25_max_violation_days"] = 10
    loose["trend"]["sma25_above_sma75_max_violation_days"] = 10
    check("トレンド: 許容日数を増やせば対象になる", logic.screen_candidate(df, loose) is not None)

    flat_then_up = [200.0] * 120 + list(np.linspace(200, 300, 80))
    check(
        "トレンド: 許容0日だと、25日線＜75日線の日がある銘柄は対象外",
        logic.screen_candidate(make_df(flat_then_up), strict) is None,
    )

    pulled = make_df(UP + [296, 292, 288, 286, 286])  # 高値更新後、25日線を約1.5%割り込んだ状態
    check("押し目待ち: 許容幅0なら25日線割れは対象外", logic.screen_candidate(pulled, CFG) is None)
    tol = copy.deepcopy(CFG)
    tol["screen"]["close_below_sma25_tolerance_pct"] = -2.0
    check(
        "押し目待ち: 許容幅-2%なら押し目の最中も対象",
        logic.screen_candidate(pulled, tol) is not None,
    )


def test_slope() -> None:
    """トレンドの傾き（回帰直線の1日あたり変化率％）の計算ロジックをテストする。"""
    import copy

    growth = [100 * 1.01**i for i in range(200)]  # 毎日+1%
    c = logic.screen_candidate(make_df(growth), CFG)
    check(
        "傾き: 毎日+1%の銘柄は約+1%/日と計算される",
        c is not None and abs(c["trend_slope_pct_per_day"] - 1.0) < 0.01,
    )

    steep = copy.deepcopy(CFG)
    steep["trend"]["min_slope_pct_per_day"] = 5.0
    check(
        "傾き: 下限を超えない銘柄は対象外", logic.screen_candidate(make_df(growth), steep) is None
    )

    # 6か月前の1日だけ安値に落ちている銘柄でも、傾きは全体の動きで判断される
    dent = list(UP)
    dent[-125] = 50.0
    check(
        "傾き: 始点だけが極端でも、全体が上昇なら対象",
        logic.screen_candidate(make_df(dent), CFG) is not None,
    )


def test_buy_signal() -> None:
    """押し目買いシグナル判定（押し目深度、前日高値超え、出来高増など）をテストする。"""
    pull = [296, 292, 288, 286, 286]
    ok = make_df(UP + pull + [300], [1000] * 200 + [800] * 5 + [1500])
    check(
        "買い候補: 押し目→終値が前日高値超え＋出来高増で成立",
        logic.check_buy_signal(ok, CFG) is not None,
    )

    low_vol = make_df(UP + pull + [300], [1000] * 200 + [800] * 5 + [700])
    check("買い候補: 出来高が増えていなければ不成立", logic.check_buy_signal(low_vol, CFG) is None)

    no_break = make_df(UP + pull + [287], [1000] * 200 + [800] * 5 + [1500])
    check(
        "買い候補: 終値が前日高値を超えなければ不成立",
        logic.check_buy_signal(no_break, CFG) is None,
    )

    deep = [296, 280, 270, 270, 275]
    broke = make_df(UP + deep + [300], [1000] * 200 + [800] * 5 + [1500])
    check("買い候補: 25日線を大きく割った銘柄は不成立", logic.check_buy_signal(broke, CFG) is None)

    shallow = [300, 301, 302, 303, 304]
    no_pull = make_df(UP + shallow + [310], [1000] * 200 + [800] * 5 + [1500])
    check(
        "買い候補: 25日線付近まで押していなければ不成立",
        logic.check_buy_signal(no_pull, CFG) is None,
    )

    sig = logic.check_buy_signal(ok, CFG)
    check(
        "買いラインはシグナル日の高値", sig is not None and sig["buy_line"] == round(300 * 1.01, 1)
    )


def test_has_earnings_within_business_days() -> None:
    """決算発表予定日が指定営業日以内にあるかの判定ロジックをテストする。"""
    base = date(2026, 10, 13)  # 火曜
    check(
        "決算: 5営業日後ちょうどは見送り",
        logic.has_earnings_within_business_days(base, date(2026, 10, 20), 5) is True,
    )
    check(
        "決算: 6営業日後は見送りでない",
        logic.has_earnings_within_business_days(base, date(2026, 10, 21), 5) is False,
    )
    check(
        "決算: 過去の日付は見送りでない",
        logic.has_earnings_within_business_days(base, date(2026, 10, 1), 5) is False,
    )
    check(
        "決算: 日付不明は None（手入力が必要）",
        logic.has_earnings_within_business_days(base, None, 5) is None,
    )
    check(
        "決算: 年末年始の休場日を営業日に数えない",
        logic.has_earnings_within_business_days(date(2026, 12, 28), date(2027, 1, 6), 5) is True,
    )


if __name__ == "__main__":
    test_has_earnings_within_business_days()
    test_high_update_sbi_definition()
    test_topix()
    test_screen_candidate()
    test_trend_over_period()
    test_slope()
    test_buy_signal()
    print("\nすべてOKでした")
