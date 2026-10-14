"""
JPXが公開している決算発表予定日のExcelの構造を確認するスクリプト。

yfinanceで決算日が取れない銘柄（約3分の1）を、JPXの公式の予定日で補うための下調べ。

    uv run batch/check_jpx_earnings.py
"""

import re
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests

PAGE = "https://www.jpx.co.jp/listing/event-schedules/financial-announcement/index.html"
OUT_DIR = Path(__file__).parent / "data" / "earnings"


def main() -> None:
    """JPXウェブサイトから決算発表予定日Excelのリンクを取得・ダウンロードし、内容の構造を確認する。"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html = requests.get(PAGE, timeout=30).text
    hrefs = re.findall(r"href=[\"']([^\"']*kessan[^\"']*\.xlsx)[\"']", html)
    links = sorted({urljoin(PAGE, h) for h in hrefs})
    print(f"Excelのリンク: {len(links)} 件")
    for link in links:
        print(" ", link)

    for link in links:
        path = OUT_DIR / link.rsplit("/", 1)[-1]
        path.write_bytes(requests.get(link, timeout=60).content)
        print(f"\n===== {path.name} =====")
        xls = pd.ExcelFile(path)
        print("シート:", xls.sheet_names)
        df = pd.read_excel(path, header=None, nrows=8)
        print(f"先頭8行（{df.shape[1]}列）:")
        print(df.to_string())


if __name__ == "__main__":
    main()
