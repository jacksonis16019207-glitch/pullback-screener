"""通知の文面づくりと、ntfy（無料のプッシュ通知）での送信。"""
import os


def fmt_price(value: float) -> str:
    """3173.0 → '3,173'、2247.5 → '2,247.5'"""
    return f"{value:,.1f}".removesuffix(".0")


def build_notifications(
    watch: dict, buy: dict, is_friday: bool, trading_today: bool
) -> list[tuple[str, str]]:
    """
    送る通知を [(タイトル, 本文), ...] で返す。
      - 金曜: 押し目待ちリストの更新（材料ニュースの確認が必要な銘柄があれば同じ通知に含める）
      - 平日: 買い候補（TOPIXが×・決算が近い銘柄は除く）。SBI株アプリでの通知設定を促す
    休場日（今日の日足がない日）は何も送らない。
    """
    if not trading_today:
        return []

    notifications: list[tuple[str, str]] = []

    if is_friday:
        items = watch["items"]
        need = sum(1 for i in items if i.get("needs_news_check"))
        message = f"押し目待ちリストを更新しました（{len(items)}銘柄）。"
        if need:
            message += f"\n材料ニュースの確認が必要な銘柄が{need}件あります。選択をお願いします。"
        notifications.append(("押し目待ちリストを更新", message))

    actionable = [
        i
        for i in buy["items"]
        if not i.get("topix_blocked") and i.get("earnings_soon") is not True
    ]
    if actionable:
        lines = []
        for i in actionable[:5]:
            note = "（決算日不明）" if i.get("earnings_soon") is None else ""
            lines.append(f"{i['code']} {i['name']}: {fmt_price(i['buy_line'])}円超え{note}")
        if len(actionable) > 5:
            lines.append(f"ほか{len(actionable) - 5}銘柄")
        lines.append("SBI株アプリで、買いラインの通知を設定してください。")
        notifications.append((f"買い候補 {len(actionable)}銘柄", "\n".join(lines)))

    return notifications


def send(title: str, message: str) -> None:
    """ntfyに送る。NTFY_TOPIC（環境変数）が未設定なら何もしない。"""
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("NTFY_TOPIC が未設定のため、通知は送りません")
        return

    import requests

    body = {"topic": topic, "title": title, "message": message}
    click = os.environ.get("APP_URL")
    if click:
        body["click"] = click
    try:
        res = requests.post("https://ntfy.sh/", json=body, timeout=30)
        res.raise_for_status()
        print(f"通知を送りました: {title}")
    except Exception as e:  # noqa: BLE001
        print(f"通知を送れませんでした: {e}")
