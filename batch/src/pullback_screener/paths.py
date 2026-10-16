"""ファイルの置き場所をここにまとめる。"""
from pathlib import Path

BATCH_DIR = Path(__file__).resolve().parents[2]  # batch/
CONFIG_PATH = BATCH_DIR / "config.json"          # 判定の設定値
DATA_DIR = BATCH_DIR / "data"                    # ダウンロードしたデータの保存先（Git管理外）
OUTPUT_DIR = BATCH_DIR / "output"                # 判定結果の出力先（Git管理外）
