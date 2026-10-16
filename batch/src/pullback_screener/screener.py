"""
押し目買いスクリーナー本体（コマンドの入口）。

使い方（batch/ フォルダで）:
    uv run pullback-screener weekly               # 金曜の引け後: 押し目待ちリストを作る
    uv run pullback-screener daily                # 平日の引け後: 買い候補を判定する
    uv run pullback-screener diagnose 2121 2004   # 指定した銘柄が条件を満たすかを説明する

出力（batch/output/）:
    watchlist.json        押し目待ちリスト
    buy_candidates.json   買い候補リスト
"""
import json
import sys
from datetime import date, datetime

from . import common, logic
from .paths import OUTPUT_DIR as OUT_DIR


def now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def save(name: str, data: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"保存しました: {path}")


def check_topix(cfg: dict) -> dict:
    """手順1。TOPIX連動ETF(1306)の日足でTOPIXの地合いを判定する。"""
    ticker = cfg["topix"]["ticker"]
    data = common.fetch_daily([ticker], period="2y")
    if ticker not in data or len(data[ticker]) < 100:
        raise RuntimeError(f"TOPIX代用 ({ticker}) のデータを取得できませんでした")
    ok, info = logic.topix_ok(data[ticker], cfg["topix"])
    print(f"TOPIX判定 ({ticker}): {'○' if ok else '×'} {info}")
    return {"ticker": ticker, "ok": ok, **info}


def weekly() -> None:
    cfg = logic.load_config()
    topix = check_topix(cfg)
    result = {"generated_at": now_text(), "topix": topix, "items": []}

    if not topix["ok"]:
        if cfg["topix"].get("block_watchlist", False):
            print("TOPIXが×のため、今週は新規の候補を出しません")
            save("watchlist.json", result)
            return
        print("TOPIXは×ですが、押し目待ちリストは作ります（買い候補は毎日の判定で見送ります）")

    prime = common.load_prime_list()
    print(f"対象: 東証プライム {len(prime)} 銘柄")
    prices = common.fetch_daily(prime["ticker"].tolist())

    cands = []
    for ticker, df in prices.items():
        c = logic.screen_candidate(df, cfg)
        if c:
            c["ticker"] = ticker
            cands.append(c)
    print(f"価格条件を通過: {len(cands)} 銘柄。時価総額を確認します")

    jpx = common.load_jpx_earnings()
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
    save("watchlist.json", result)


def daily() -> None:
    cfg = logic.load_config()
    watch_path = OUT_DIR / "watchlist.json"
    if not watch_path.exists():
        raise SystemExit("watchlist.json がありません。先に weekly を実行してください")
    watch = json.loads(watch_path.read_text(encoding="utf-8"))
    items = watch["items"]

    topix = check_topix(cfg)
    result = {"generated_at": now_text(), "topix": topix, "items": []}
    blocked = not topix["ok"]
    if blocked:
        print("TOPIXが×のため、新規買いは見送りです（条件を満たした銘柄には見送りの印をつけます）")

    if not items:
        print("押し目待ちリストが空です")
        save("buy_candidates.json", result)
        return

    prices = common.fetch_daily([i["ticker"] for i in items])
    jpx = common.load_jpx_earnings()
    found = []
    for it in items:
        df = prices.get(it["ticker"])
        if df is None:
            continue
        sig = logic.buy_signal(df, cfg)
        if sig:
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
    save("buy_candidates.json", result)


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
    elif mode == "diagnose" and len(sys.argv) > 2:
        diagnose(sys.argv[2:])
    else:
        print("使い方: uv run pullback-screener weekly | daily | diagnose 銘柄コード...")
