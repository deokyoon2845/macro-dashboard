"""
CNN 공포탐욕지수 수집. 현재값만 제공되므로 매일 누적 저장.
"""

import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from utils import sanity_check

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
HISTORY_FILE = DATA_DIR / "sentiment.parquet"


def main():
    print(f"[Sentiment] 시작: {datetime.utcnow().isoformat()}Z")

    try:
        import fear_and_greed
        result = fear_and_greed.get()
        value = float(result.value)
        description = str(result.description)
        timestamp = pd.Timestamp(result.last_update)
        if timestamp.tz is not None:
            timestamp = timestamp.tz_localize(None)
    except Exception as e:
        print(f"  fear_and_greed 호출 실패: {e}")
        return  # 워크플로 죽이지 않음

    today_record = pd.DataFrame({
        "date":        [timestamp.normalize()],
        "indicator":   ["FEAR_GREED"],
        "value":       [value],
        "description": [description],
    })

    warnings = sanity_check(today_record, name="FEAR_GREED", value_range=(0.0, 100.0))
    for w in warnings:
        print(f"  ⚠ {w}")

    if HISTORY_FILE.exists():
        existing = pd.read_parquet(HISTORY_FILE)
        existing = existing[
            existing["date"].dt.date != today_record["date"].iloc[0].date()
        ]
        combined = pd.concat([existing, today_record], ignore_index=True)
    else:
        combined = today_record

    combined = combined.sort_values("date").reset_index(drop=True)
    combined.to_parquet(HISTORY_FILE, index=False)

    print(f"[Sentiment] 현재값: {value:.1f} ({description})")
    print(f"  누적 일수: {len(combined)}")


if __name__ == "__main__":
    main()
