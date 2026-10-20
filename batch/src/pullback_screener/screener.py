"""
押し目買いスクリーナー本体（コマンドの入口）。

使い方（batch/ フォルダで）:
    uv run pullback-screener weekly               # 金曜の引け後: 押し目待ちリストを作る
    uv run pullback-screener daily                # 平日の引け後: 買い候補を判定する
    uv run pullback-screener run                  # 自動実行用: 直近の金曜時点のリスト＋今日の買い候補＋通知
    uv run pullback-screener diagnose 2121 2004   # 指定した銘柄が条件を満たすかを説明する
    uv run pullback-screener notify-test          # 通知のテスト送信（届かなければ終了コード1）

出力（batch/output/）:
    watchlist.json        押し目待ちリスト
    buy_candidates.json   買い候補リスト
"""
import json
import sys
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from . import common, logic, notify
from .paths import OUTPUT_DIR as OUT_DIR

JST = ZoneInfo("Asia/Tokyo")


def now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def save(name: str, data: dict, compact: bool = False) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    if compact:  # チャートのように数字が大きく並ぶファイルは、改行なしで小さくする
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    else:
        text = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")
    print(f"保存しました: {path}")


def fetch_topix(cfg: dict) -> pd.DataFrame:
    """TOPIX連動ETF(1306)の日足を取得する。"""
    ticker = cfg["topix"]["ticker"]
    data = common.fetch_daily([ticker], period="2y")
    if ticker not in data or len(data[ticker]) < 100:
        raise RuntimeError(f"TOPIX代用 ({ticker}) のデータを取得できませんでした")
    return data[ticker]


def topix_status(df: pd.DataFrame, cfg: dict, as_of: date | None = None) -> dict:
    """手順1。as_of 時点のTOPIXの地合いを判定する。"""
    ok, info = logic.topix_ok(logic.truncate(df, as_of), cfg["topix"])
    print(f"TOPIX判定 ({cfg['topix']['ticker']}): {'○' if ok else '×'} {info}")
    return {"ticker": cfg["topix"]["ticker"], "ok": ok, **info}


def build_watchlist(
    cfg: dict,
    topix_df: pd.DataFrame,
    prices: dict[str, pd.DataFrame],
    prime: pd.DataFrame,
    jpx: dict,
    as_of: date | None = None,
) -> dict:
    """押し目待ちリストを作る（手順1〜6）。as_of を指定すると、その日までのデータで判定する。"""
    topix = topix_status(topix_df, cfg, as_of)
    result = {"generated_at": now_text(), "topix": topix, "items": []}

    if not topix["ok"]:
        if cfg["topix"].get("block_watchlist", False):
            print("TOPIXが×のため、今週は新規の候補を出しません")
            return result
        print("TOPIXは×ですが、押し目待ちリストは作ります（買い候補は毎日の判定で見送ります）")

    cands = []
    for ticker, df in prices.items():
        c = logic.screen_candidate(logic.truncate(df, as_of), cfg)
        if c:
            c["ticker"] = ticker
            cands.append(c)
    print(f"価格条件を通過: {len(cands)} 銘柄。時価総額を確認します")

    meta = prime.set_index("ticker")
    min_cap = cfg["screen"]["min_market_cap_oku"] * 1e8
    passed, cap_failed = [], 0
    for c in cands:
        cap = common.get_market_cap(c["ticker"])
        if cap is None:
            cap_failed += 1
            continue
        if cap < min_cap:
            continue
        row = meta.loc[c["ticker"]]
        c.update(
            code=row["コード"],
            name=row["銘柄名"],
            sector=row.get("33業種区分", ""),
            market_cap_oku=round(cap / 1e8),
        )
        passed.append(c)

    # 年初来高値の更新日が新しい順に並べ、上位N件だけを対象にする
    limit = cfg["screen"].get("max_watchlist_size", 100)
    items = logic.sort_and_limit(passed, limit)
    for c in items:  # 決算日は対象の銘柄だけ調べる
        edate, source = common.find_earnings(c["code"], c["ticker"], jpx)
        c["earnings_date"] = edate.isoformat() if edate else None
        c["earnings_source"] = source

    result["total_before_limit"] = len(passed)
    result["items"] = items
    print(f"時価総額の条件を通過: {len(passed)} 銘柄 (時価総額の取得失敗 {cap_failed})")
    print(f"押し目待ちリスト: 高値更新日が新しい順に上位 {len(items)} 銘柄 (上限 {limit})")
    print(f"  うち材料ニュースの確認が必要: {sum(i['needs_news_check'] for i in items)} 銘柄")
    print(
        "  決算日の出所: "
        f"JPX {sum(i['earnings_source'] == 'JPX' for i in items)} / "
        f"yfinance予定 {sum(i['earnings_source'] == 'yfinance予定' for i in items)} / "
        f"取れなかった {sum(i['earnings_date'] is None for i in items)} 銘柄"
    )
    return result


def find_buy_candidates(
    cfg: dict,
    watch: dict,
    topix_df: pd.DataFrame,
    prices: dict[str, pd.DataFrame],
    jpx: dict,
) -> dict:
    """押し目待ちリストの銘柄から、今日の買い候補を判定する（手順7〜10）。"""
    topix = topix_status(topix_df, cfg)
    result = {"generated_at": now_text(), "topix": topix, "items": []}
    blocked = not topix["ok"]
    if blocked:
        print("TOPIXが×のため、新規買いは見送りです（条件を満たした銘柄には見送りの印をつけます）")

    items = watch["items"]
    if not items:
        print("押し目待ちリストが空です")
        return result

    # 全銘柄の中で最も新しい日付。この日にシグナルが出たものだけを買い候補にする
    # （データが古いまま止まっている銘柄の、過去のシグナルを混ぜないため）
    latest = max((df.index[-1] for df in prices.values()), default=None)

    found = []
    for it in items:
        df = prices.get(it["ticker"])
        if df is None:
            continue
        sig = logic.buy_signal(df, cfg)
        if sig and latest is not None and sig["signal_date"] == latest.strftime("%Y-%m-%d"):
            edate, source = common.find_earnings(it["code"], it["ticker"], jpx)
            soon = logic.earnings_soon(
                date.fromisoformat(sig["signal_date"]),
                edate,
                cfg["earnings"]["skip_within_business_days"],
            )
            found.append(
                {
                    "earnings_date": edate.isoformat() if edate else None,
                    "earnings_source": source,
                    "earnings_soon": soon,
                    "topix_blocked": blocked,
                    "ticker": it["ticker"],
                    "code": it["code"],
                    "name": it["name"],
                    "sector": it.get("sector", ""),
                    "market_cap_oku": it["market_cap_oku"],
                    **sig,
                }
            )

    result["items"] = found
    print(f"買い候補: {len(found)} 銘柄")
    for f in found:
        note = " ※決算が近いため見送り" if f["earnings_soon"] else ""
        note = " ※決算日不明" if f["earnings_soon"] is None else note
        note += " ※TOPIXが×のため見送り" if f["topix_blocked"] else ""
        print(f"  {f['code']} {f['name']}: 買いライン {f['buy_line']:,.1f}円{note}")
    return result


def weekly() -> None:
    cfg = logic.load_config()
    topix_df = fetch_topix(cfg)
    prime = common.load_prime_list()
    print(f"対象: 東証プライム {len(prime)} 銘柄")
    prices = common.fetch_daily(prime["ticker"].tolist())
    jpx = common.load_jpx_earnings()
    save("watchlist.json", build_watchlist(cfg, topix_df, prices, prime, jpx))


def daily() -> None:
    cfg = logic.load_config()
    watch_path = OUT_DIR / "watchlist.json"
    if not watch_path.exists():
        raise SystemExit("watchlist.json がありません。先に weekly を実行してください")
    watch = json.loads(watch_path.read_text(encoding="utf-8"))
    topix_df = fetch_topix(cfg)
    prices = common.fetch_daily([i["ticker"] for i in watch["items"]]) if watch["items"] else {}
    jpx = common.load_jpx_earnings()
    save("buy_candidates.json", find_buy_candidates(cfg, watch, topix_df, prices, jpx))


def wait_for_today_data(cfg: dict, now: datetime) -> None:
    """
    営業日の引け後なのに、TOPIXの日足に今日の分がまだ入っていないときは、入るまで待つ。
    （データの反映が遅れる日があるため。待っても入らなければ、そのまま先に進む）
    """
    if not logic.should_wait_for_data(now):
        return
    ticker = cfg["topix"]["ticker"]
    limit = cfg.get("run", {}).get("wait_for_data_minutes", 30)
    interval = cfg.get("run", {}).get("wait_interval_minutes", 5)
    waited = 0
    while True:
        data = common.fetch_daily([ticker], period="1mo")
        last = data[ticker].index[-1].date() if ticker in data else None
        if last == now.date():
            return
        if waited >= limit:
            print(f"{waited}分待ちましたが、TOPIXの日足に今日の分が入りませんでした")
            return
        print(f"TOPIXの日足に今日の分がまだありません。{interval}分待ちます（{waited}/{limit}分）")
        time.sleep(interval * 60)
        waited += interval


def build_charts(items: list[dict], prices: dict[str, pd.DataFrame], cfg: dict) -> dict:
    """押し目待ちリストの各銘柄について、銘柄詳細画面用のチャートと判定補助の数字を作る。"""
    stocks = {}
    for it in items:
        df = prices.get(it["ticker"])
        if df is None:
            continue
        stocks[it["code"]] = {**logic.chart_data(df), "stats": logic.news_check_stats(df, cfg)}
    return {"generated_at": now_text(), "stocks": stocks}


def run() -> None:
    """
    自動実行用。状態を持ち越さずに、毎回すべてを作り直す。
      押し目待ちリスト: 直近の金曜（その日が休場なら直前の営業日）までのデータで作る
      買い候補: 今日までのデータで、そのリストの銘柄を判定する
    """
    cfg = logic.load_config()
    now = datetime.now(JST)
    today = now.date()
    as_of = logic.last_friday(today)
    print(f"今日: {today} / 押し目待ちリストの基準日: {as_of}")

    wait_for_today_data(cfg, now)
    topix_df = fetch_topix(cfg)
    prime = common.load_prime_list()
    prices = common.fetch_daily(prime["ticker"].tolist())
    jpx = common.load_jpx_earnings()

    watch = build_watchlist(cfg, topix_df, prices, prime, jpx, as_of=as_of)
    buy = find_buy_candidates(cfg, watch, topix_df, prices, jpx)
    # 画面で、手入力した決算日から「5営業日以内か」を数えるための情報
    watch["non_trading_days"] = logic.non_trading_weekdays(today - timedelta(days=14))
    watch["earnings_skip_days"] = cfg["earnings"]["skip_within_business_days"]
    save("watchlist.json", watch)
    save("buy_candidates.json", buy)
    save("charts.json", build_charts(watch["items"], prices, cfg), compact=True)

    trading_today = buy["topix"].get("as_of") == today.isoformat()
    if not trading_today:
        print("今日は休場日か、今日の日足がまだないため、通知は送りません")
        if logic.should_wait_for_data(now):  # 営業日の引け後なのに日足がない: 気づけるよう知らせる
            notify.send(
                "日足が取得できませんでした",
                "営業日の引け後ですが、今日の日足が反映されていないため、通知を見送りました。"
                "あとで画面を確認してください。",
            )
    for title, message in notify.build_notifications(
        watch, buy, is_friday=today.weekday() == 4, trading_today=trading_today
    ):
        notify.send(title, message)


def diagnose(codes: list[str]) -> None:
    """指定した銘柄コードについて、押し目待ちの条件ごとの結果を表示する（確認用）。"""
    cfg = logic.load_config()
    tickers = [c + ".T" for c in codes]
    prices = common.fetch_daily(tickers)
    for code, ticker in zip(codes, tickers):
        print(f"\n===== {code} =====")
        df = prices.get(ticker)
        if df is None:
            print("日足を取得できませんでした")
            continue
        for key, value in logic.diagnose(df, cfg).items():
            print(f"{key}: {value}")
        cap = common.get_market_cap(ticker)
        print(f"時価総額: {round(cap / 1e8):,}億円" if cap else "時価総額: 取得失敗")
        print(f"押し目待ちの判定: {'対象' if logic.screen_candidate(df, cfg) else '対象外'}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "weekly":
        weekly()
    elif mode == "daily":
        daily()
    elif mode == "run":
        run()
    elif mode == "diagnose" and len(sys.argv) > 2:
        diagnose(sys.argv[2:])
    elif mode == "notify-test":
        sent = notify.send(
            "通知のテスト",
            "押し目スクリーナーからのテスト通知です。この通知が届けば、設定は正しく動いています。",
        )
        raise SystemExit(0 if sent else 1)
    else:
        print("使い方: uv run pullback-screener weekly | daily | run | diagnose 銘柄コード... | notify-test")
