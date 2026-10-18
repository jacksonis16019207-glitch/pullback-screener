"""
判定ロジックの動作確認（ネットワーク不要）。

    cd batch
    uv run pytest

作り物の株価データで、期待どおりに判定されるかを確かめる。
"""
import json
import tempfile
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from pullback_screener import logic

# テスト専用の固定設定（config.json を調整してもテスト結果が変わらないようにする）
CFG = {
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
    idx = pd.bdate_range(start, periods=len(closes))
    c = np.array(closes, dtype=float)
    v = np.full(len(c), 1000.0) if vols is None else np.array(vols, dtype=float)
    return pd.DataFrame(
        {"High": c * 1.01, "Low": c * 0.99, "Close": c, "Volume": v}, index=idx
    )


def check(name: str, cond: bool) -> None:
    assert cond, name


UP = list(np.linspace(100, 300, 200))  # 上昇トレンド（最終日が年初来高値）


def test_high_update_sbi_definition() -> None:
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
    f = logic.high_update_flags(df)
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
    f2 = logic.high_update_flags(df2)
    check("4月以降は当年1月からが基準（前年の高値を無視）", bool(f2["2026-04-01"]))
    check("3月末はまだ前年が基準（更新でない）", not f2["2026-03-31"])


def test_topix() -> None:
    ok, _ = logic.topix_ok(make_df(UP), CFG["topix"])
    check("TOPIX: 上昇トレンドは○", ok)
    down = list(np.linspace(300, 100, 200))
    ok, _ = logic.topix_ok(make_df(down), CFG["topix"])
    check("TOPIX: 下降トレンドは×", not ok)


def test_screen_candidate() -> None:
    check("押し目待ち: 高値更新直後の上昇トレンド銘柄は対象", logic.screen_candidate(make_df(UP), CFG) is not None)
    flat = [200.0] * 200
    check("押し目待ち: 高値更新のない横ばい銘柄は対象外", logic.screen_candidate(make_df(flat), CFG) is None)
    down = list(np.linspace(300, 100, 200))
    check("押し目待ち: 下降トレンドは対象外", logic.screen_candidate(make_df(down), CFG) is None)

    surge = UP[:-1] + [UP[-2] * 1.08]
    c = logic.screen_candidate(make_df(surge), CFG)
    check("押し目待ち: 直近5日に+5%以上の日があれば材料確認が必要", c is not None and c["needs_news_check"])


def test_trend_over_period() -> None:
    import copy

    strict = copy.deepcopy(CFG)
    strict["trend"]["price_above_sma25_max_violation_days"] = 0
    strict["trend"]["sma25_above_sma75_max_violation_days"] = 0

    dip = list(UP)
    for i in range(-60, -55):  # 6か月の途中で5日だけ25日線を割る
        dip[i] = dip[i] * 0.85
    df = make_df(dip)
    check("トレンド: 既定では期間の制限なし（最新日の条件のみ）", logic.screen_candidate(df, CFG) is not None)
    check("トレンド: 許容0日にすると、途中で25日線を割った銘柄は対象外", logic.screen_candidate(df, strict) is None)

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
    check("押し目待ち: 許容幅-2%なら押し目の最中も対象", logic.screen_candidate(pulled, tol) is not None)


def test_slope() -> None:
    import copy

    growth = [100 * 1.01**i for i in range(200)]  # 毎日+1%
    c = logic.screen_candidate(make_df(growth), CFG)
    check("傾き: 毎日+1%の銘柄は約+1%/日と計算される", c is not None and abs(c["trend_slope_pct_per_day"] - 1.0) < 0.01)

    steep = copy.deepcopy(CFG)
    steep["trend"]["min_slope_pct_per_day"] = 5.0
    check("傾き: 下限を超えない銘柄は対象外", logic.screen_candidate(make_df(growth), steep) is None)

    # 6か月前の1日だけ安値に落ちている銘柄でも、傾きは全体の動きで判断される
    dent = list(UP)
    dent[-125] = 50.0
    check("傾き: 始点だけが極端でも、全体が上昇なら対象", logic.screen_candidate(make_df(dent), CFG) is not None)


def test_jpx_earnings_file() -> None:
    rows = [
        ["９月に四半期末又は期末を迎えた決算発表予定会社の一覧"] + [None] * 10,
        ["List of companies scheduled to announce earnings ..."] + [None] * 10,
        ["2026年10月8日 現在"] + [None] * 10,
        ["As of 2026/10/8"] + [None] * 10,
        ["決算発表予定日\nScheduled Dates for Earnings Announcements", "コード\nCode", "会社名"] + [None] * 8,
        [pd.Timestamp("2026-10-05"), 2753, "あみやき亭"] + [None] * 8,
        [pd.Timestamp("2026-10-15"), 6866, "日置電機"] + [None] * 8,
        [pd.Timestamp("2026-11-05"), "471A", "新規上場の例"] + [None] * 8,
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "kessan09_test.xlsx"
        pd.DataFrame(rows).to_excel(path, header=False, index=False)
        got = logic.read_jpx_earnings(path)
    check("JPX決算日: 見出しの次の行から読み込む", got.get("6866") == [date(2026, 10, 15)])
    check("JPX決算日: 英字入りのコードも読める", got.get("471A") == [date(2026, 11, 5)])
    check("JPX決算日: 題名の行は含めない", len(got) == 3)
    check("次の決算日: 今日以降で最も近い日", logic.next_date([date(2026, 10, 5), date(2026, 10, 15)], date(2026, 10, 14)) == date(2026, 10, 15))
    check("次の決算日: 過去だけなら None", logic.next_date([date(2026, 10, 5)], date(2026, 10, 14)) is None)


def test_buy_signal() -> None:
    pull = [296, 292, 288, 286, 286]
    ok = make_df(UP + pull + [300], [1000] * 200 + [800] * 5 + [1500])
    check("買い候補: 押し目→終値が前日高値超え＋出来高増で成立", logic.buy_signal(ok, CFG) is not None)

    low_vol = make_df(UP + pull + [300], [1000] * 200 + [800] * 5 + [700])
    check("買い候補: 出来高が増えていなければ不成立", logic.buy_signal(low_vol, CFG) is None)

    no_break = make_df(UP + pull + [287], [1000] * 200 + [800] * 5 + [1500])
    check("買い候補: 終値が前日高値を超えなければ不成立", logic.buy_signal(no_break, CFG) is None)

    deep = [296, 280, 270, 270, 275]
    broke = make_df(UP + deep + [300], [1000] * 200 + [800] * 5 + [1500])
    check("買い候補: 25日線を大きく割った銘柄は不成立", logic.buy_signal(broke, CFG) is None)

    shallow = [300, 301, 302, 303, 304]
    no_pull = make_df(UP + shallow + [310], [1000] * 200 + [800] * 5 + [1500])
    check("買い候補: 25日線付近まで押していなければ不成立", logic.buy_signal(no_pull, CFG) is None)

    sig = logic.buy_signal(ok, CFG)
    check("買いラインはシグナル日の高値", sig is not None and sig["buy_line"] == round(300 * 1.01, 1))


def test_earnings_soon() -> None:
    base = date(2026, 10, 13)  # 火曜
    check("決算: 5営業日後ちょうどは見送り", logic.earnings_soon(base, date(2026, 10, 20), 5) is True)
    check("決算: 6営業日後は見送りでない", logic.earnings_soon(base, date(2026, 10, 21), 5) is False)
    check("決算: 過去の日付は見送りでない", logic.earnings_soon(base, date(2026, 10, 1), 5) is False)
    check("決算: 日付不明は None（手入力が必要）", logic.earnings_soon(base, None, 5) is None)
    check(
        "決算: 年末年始の休場日を営業日に数えない",
        logic.earnings_soon(date(2026, 12, 28), date(2027, 1, 6), 5) is True,
    )


def test_sort_and_limit() -> None:
    items = [
        {"code": "A", "last_high_update": "2026-10-01", "market_cap_oku": 5000},
        {"code": "B", "last_high_update": "2026-10-15", "market_cap_oku": 1200},
        {"code": "C", "last_high_update": "2026-10-15", "market_cap_oku": 9000},
        {"code": "D", "last_high_update": "2026-10-10", "market_cap_oku": 3000},
    ]
    got = logic.sort_and_limit(items, 3)
    check("上限: 指定した件数で打ち切る", len(got) == 3)
    check("並び順: 更新日が新しい順、同じ日は時価総額が大きい順", [x["code"] for x in got] == ["C", "B", "D"])
    check("上限: 件数が足りないときはそのまま返す", len(logic.sort_and_limit(items, 100)) == 4)


def test_truncate_and_last_friday() -> None:
    df = make_df(UP)
    cut = logic.truncate(df, df.index[100].date())
    check("基準日: その日までの日足だけになる", cut.index[-1] == df.index[100] and len(cut) == 101)
    check("基準日: None ならそのまま", len(logic.truncate(df, None)) == len(df))

    check("金曜: 水曜なら直前の金曜", logic.last_friday(date(2026, 10, 14)) == date(2026, 10, 9))
    check("金曜: 金曜ならその日", logic.last_friday(date(2026, 10, 16)) == date(2026, 10, 16))
    check("金曜: 土曜なら前日の金曜", logic.last_friday(date(2026, 10, 17)) == date(2026, 10, 16))
    check("金曜: 月曜なら先週の金曜", logic.last_friday(date(2026, 10, 12)) == date(2026, 10, 9))


def test_should_wait_for_data() -> None:
    check("待つ: 営業日の引け後は待つ", logic.should_wait_for_data(datetime(2026, 10, 14, 16, 30)) is True)
    check("待つ: 15:30ちょうどから待つ", logic.should_wait_for_data(datetime(2026, 10, 14, 15, 30)) is True)
    check("待つ: 引け前は待たない", logic.should_wait_for_data(datetime(2026, 10, 14, 10, 0)) is False)
    check("待つ: 土曜は待たない", logic.should_wait_for_data(datetime(2026, 10, 17, 16, 30)) is False)
    check("待つ: 年末の休場日は待たない", logic.should_wait_for_data(datetime(2026, 12, 31, 16, 30)) is False)
    check("営業日: 平日は営業日", logic.is_business_day(date(2026, 10, 14)) is True)
    check("営業日: 日曜は営業日でない", logic.is_business_day(date(2026, 10, 18)) is False)


def test_chart_data() -> None:
    cd = logic.chart_data(make_df(UP))
    n = len(cd["dates"])
    check("チャート: 直近125営業日", n == 125)
    check("チャート: 各系列の長さがそろう", all(len(cd[k]) == n for k in ("close", "sma25", "sma75", "volume")))
    check("チャート: 最終日が高値更新日", cd["high_update_dates"][-1] == cd["dates"][-1])
    check("チャート: JSONに書き出せる（NaNなし）", len(json.dumps(cd, allow_nan=False)) > 0)

    short = logic.chart_data(make_df(UP[:90]))  # 75日線がまだない日はnullになる
    check("チャート: 75日線が未計算の日は null", short["sma75"][0] is None)
    check("チャート: nullがあってもJSONに書き出せる", len(json.dumps(short, allow_nan=False)) > 0)


def test_news_check_stats() -> None:
    calm = logic.news_check_stats(make_df(UP), CFG)
    check("判定補助: 急騰がなければ急騰日は None", calm["surge_day"] is None and calm["surge_count_20d"] == 0)

    surge = UP[:-1] + [UP[-2] * 1.08]
    vols = [1000] * 199 + [3000]
    st = logic.news_check_stats(make_df(surge, vols), CFG)
    check("判定補助: 直近の+5%以上の日を拾う", st["surge_count_20d"] == 1 and st["days_since_surge"] == 0)
    check("判定補助: 急騰前20日は上昇している", st["pre_surge_20d_pct"] is not None and st["pre_surge_20d_pct"] > 0)
    check("判定補助: 急騰日の出来高は急騰前の3倍", st["volume_ratio_after_surge"] == 3.0)
