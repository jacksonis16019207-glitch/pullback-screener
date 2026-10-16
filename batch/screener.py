"""
押し目買いスクリーナー本体。

使い方（リポジトリ直下で）:
    uv run batch/screener.py weekly   # 金曜の引け後: 押し目待ちリストを作る
    uv run batch/screener.py daily    # 平日の引け後: 買い候補を判定する
    uv run batch/screener.py diagnose 2121 2004   # 指定した銘柄が条件を満たすかを説明する
    uv run batch/screener.py explain 2121   # 1銘柄の判定を条件ごとに説明する

出力（batch/output/）:
    watchlist.json        押し目待ちリスト
    buy_candidates.json   買い候補リスト
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

import common
import logic

OUT_DIR = Path(__file__).parent / "output"


def get_now_text() -> str:
    """現在時刻をISO 8601形式の文字列（秒単位）で取得する。

    Returns:
        タイムゾーン付きのISO 8601形式現在日時文字列。
    """
    return datetime.now().astimezone().isoformat(timespec="seconds")


def save(name: str, data: dict) -> None:
    """データをJSONファイルとして出力ディレクトリに保存する。

    Args:
        name: 保存するファイル名（例: "watchlist.json"）。
        data: 保存する辞書データ。
    """
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"保存しました: {path}")


def check_topix(cfg: dict) -> dict:
    """手順1: TOPIX連動ETFの日足データを取得し、地合いの上昇トレンド判定を行う。

    Args:
        cfg: 設定辞書。

    Returns:
        TOPIXの判定結果および詳細情報を含む辞書。

    Raises:
        RuntimeError: TOPIX連動ETFのデータ取得に失敗した場合。
    """
    ticker = cfg["topix"]["ticker"]
    data = common.fetch_daily([ticker], period="2y")
    if ticker not in data or len(data[ticker]) < 100:
        raise RuntimeError(f"TOPIX代用 ({ticker}) のデータを取得できませんでした")
    ok, info = logic.check_topix_trend(data[ticker], cfg["topix"])
    print(f"TOPIX判定 ({ticker}): {'○' if ok else '×'} {info}")
    return {"ticker": ticker, "ok": ok, **info}


def run_weekly() -> None:
    """週次処理（金曜引け後用）: 東証プライム全銘柄をスクリーニングし、
    押し目待ちリストを作成・保存する。
    """
    cfg = logic.load_config()
    topix = check_topix(cfg)
    result = {"generated_at": get_now_text(), "topix": topix, "items": []}

    if not topix["ok"]:
        print("TOPIXが×のため、今週は新規の候補を出しません")
        save("watchlist.json", result)
        return

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
    items, cap_failed = [], 0
    for c in cands:
        cap = common.get_market_cap(c["ticker"])
        if cap is None:
            cap_failed += 1
            continue
        if cap < min_cap:
            continue
        row = meta.loc[c["ticker"]]
        edate, source = common.find_earnings(row["コード"], c["ticker"], jpx)
        c.update(
            earnings_date=edate.isoformat() if edate else None,
            code=row["コード"],
            name=row["銘柄名"],
            sector=row.get("33業種区分", ""),
            market_cap_oku=round(cap / 1e8),
        )
        items.append(c)

    items.sort(key=lambda x: x["code"])
    result["items"] = items
    print(f"押し目待ちリスト: {len(items)} 銘柄 (時価総額の取得失敗 {cap_failed})")
    print(f"  うち材料ニュースの確認が必要: {sum(i['needs_news_check'] for i in items)} 銘柄")
    print(
        "  決算日の出所: "
        f"JPX {sum(i['earnings_source'] == 'JPX' for i in items)} / "
        f"yfinance予定 {sum(i['earnings_source'] == 'yfinance予定' for i in items)} / "
        f"取れなかった {sum(i['earnings_date'] is None for i in items)} 銘柄"
    )
    save("watchlist.json", result)


def run_daily() -> None:
    """日次処理（平日引け後用）: 押し目待ちリストから当日の買いシグナル成立銘柄を抽出し、保存する。

    Raises:
        SystemExit: 押し目待ちリスト（watchlist.json）が存在しない場合。
    """
    cfg = logic.load_config()
    watch_path = OUT_DIR / "watchlist.json"
    if not watch_path.exists():
        raise SystemExit("watchlist.json がありません。先に weekly を実行してください")
    watch = json.loads(watch_path.read_text(encoding="utf-8"))
    items = watch["items"]

    topix = check_topix(cfg)
    result = {"generated_at": get_now_text(), "topix": topix, "items": []}

    if not topix["ok"]:
        print("TOPIXが×のため、新規買いは見送りです")
        save("buy_candidates.json", result)
        return
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
        sig = logic.check_buy_signal(df, cfg)
        if sig:
            edate, source = common.find_earnings(it["code"], it["ticker"], jpx)
            soon = logic.has_earnings_within_business_days(
                date.fromisoformat(sig["signal_date"]),
                edate,
                cfg["earnings"]["skip_within_business_days"],
            )
            found.append(
                {
                    "earnings_date": edate.isoformat() if edate else None,
                    "earnings_source": source,
                    "earnings_soon": soon,
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
        print(f"  {f['code']} {f['name']}: 買いライン {f['buy_line']:,.1f}円{note}")
    save("buy_candidates.json", result)


def explain(code: str) -> None:
    """指定した銘柄コードについて、スクリーニング条件の合否理由や詳細診断結果を表示する。

    Args:
        code: 銘柄コード（例: "2121"）。

    Raises:
        SystemExit: 銘柄データの取得に失敗した場合。
    """
    cfg = logic.load_config()
    ticker = f"{code}.T"
    data = common.fetch_daily([ticker])
    if ticker not in data:
        raise SystemExit(f"{ticker} のデータを取得できませんでした")
    print(f"===== {ticker} =====")
    for key, value in logic.diagnose(data[ticker], cfg).items():
        print(f"{key}: {value}")
    cap = common.get_market_cap(ticker)
    print(f"時価総額: {round(cap / 1e8):,}億円" if cap else "時価総額: 取得失敗")
    print(f"押し目待ちの判定: {'対象' if logic.screen_candidate(data[ticker], cfg) else '対象外'}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "weekly":
        run_weekly()
    elif mode == "daily":
        run_daily()
    elif mode == "explain" and len(sys.argv) > 2:
        explain(sys.argv[2])
    else:
        print("使い方: uv run batch/screener.py weekly | daily | explain <銘柄コード>")
