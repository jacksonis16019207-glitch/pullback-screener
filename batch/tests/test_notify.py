"""通知の文面づくりの確認（ネットワーク不要）。"""
from pullback_screener import notify


def buy_item(code: str, name: str, line: float, soon, blocked: bool = False) -> dict:
    return {
        "code": code,
        "name": name,
        "buy_line": line,
        "earnings_soon": soon,
        "topix_blocked": blocked,
    }


WATCH = {"items": [{"needs_news_check": True}, {"needs_news_check": False}]}


def test_fmt_price() -> None:
    assert notify.fmt_price(3173.0) == "3,173"
    assert notify.fmt_price(2247.5) == "2,247.5"
    assert notify.fmt_price(42250.0) == "42,250"


def test_holiday_sends_nothing() -> None:
    buy = {"items": [buy_item("9934", "因幡電機産業", 3173.0, False)]}
    assert notify.build_notifications(WATCH, buy, is_friday=True, trading_today=False) == []


def test_friday_watchlist_notification() -> None:
    got = notify.build_notifications(WATCH, {"items": []}, is_friday=True, trading_today=True)
    assert len(got) == 1
    title, message = got[0]
    assert "押し目待ち" in title
    assert "2銘柄" in message
    assert "材料ニュース" in message and "1件" in message


def test_weekday_has_no_watchlist_notification() -> None:
    got = notify.build_notifications(WATCH, {"items": []}, is_friday=False, trading_today=True)
    assert got == []


def test_buy_notification_excludes_skipped_items() -> None:
    buy = {
        "items": [
            buy_item("9934", "因幡電機産業", 3173.0, False),
            buy_item("2737", "トーメンデバイス", 42250.0, None),  # 決算日不明は含める（注記つき）
            buy_item("1111", "決算が近い銘柄", 1000.0, True),  # 除く
            buy_item("2222", "TOPIX×の日", 2000.0, False, blocked=True),  # 除く
        ]
    }
    got = notify.build_notifications(WATCH, buy, is_friday=False, trading_today=True)
    assert len(got) == 1
    title, message = got[0]
    assert "2銘柄" in title
    assert "9934 因幡電機産業: 3,173円超え" in message
    assert "2737 トーメンデバイス: 42,250円超え（決算日不明）" in message
    assert "決算が近い銘柄" not in message and "TOPIX×の日" not in message
    assert "SBI株アプリ" in message


def test_buy_notification_truncates_long_list() -> None:
    buy = {"items": [buy_item(str(1000 + i), f"銘柄{i}", 1000.0, False) for i in range(7)]}
    got = notify.build_notifications(WATCH, buy, is_friday=False, trading_today=True)
    assert "ほか2銘柄" in got[0][1]
