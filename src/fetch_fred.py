"""
FRED API에서 매크로 지표를 가져와 Parquet 파일로 저장.
GitHub Actions가 매일 실행한다.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import FRED_INDICATORS

API_KEY = os.environ.get("FRED_API_KEY")
if not API_KEY:
    raise ValueError("FRED_API_KEY 환경변수가 설정되지 않았습니다.")

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = DATA_DIR / "fred_indicators.parquet"


def fetch_series(series_id: str, start_date: str = "2015-01-01") -> pd.DataFrame:
    """FRED API에서 단일 시계열 가져오기."""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json",
        "observation_start": start_date,
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    observations = response.json().get("observations", [])
    df = pd.DataFrame(observations)
    df = df[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().reset_index(drop=True)
    return df


def main():
    print(f"[FRED] 수집 시작: {datetime.utcnow().isoformat()}Z")

    all_data = []
    failed = []

    for name, series_id in FRED_INDICATORS.items():
        print(f"  - {name:20s} ({series_id:15s})...", end=" ")
        try:
            df = fetch_series(series_id)
            df["indicator"] = name
            df["series_id"] = series_id
            all_data.append(df)
            latest = df["date"].max().strftime("%Y-%m-%d")
            print(f"OK ({len(df):,}건, 최근 {latest})")
        except Exception as e:
            failed.append((name, str(e)))
            print(f"FAIL: {e}")

    if not all_data:
        raise RuntimeError("모든 시계열 수집 실패. API 키나 네트워크를 확인하세요.")

    combined = pd.concat(all_data, ignore_index=True)
    combined = combined[["date", "indicator", "series_id", "value"]]
    combined.to_parquet(OUTPUT_FILE, index=False)

    print(f"\n[FRED] 저장 완료: {OUTPUT_FILE}")
    print(f"  전체 행 수: {len(combined):,}")
    if failed:
        print(f"  실패 지표 {len(failed)}개: {[f[0] for f in failed]}")


if __name__ == "__main__":
    main()
