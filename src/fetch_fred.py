"""
FRED API에서 매크로 지표를 가져와 Parquet으로 저장.
config.py의 FRED_INDICATORS = {name: (series_id, value_range)} 형식에 맞게 수정.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import FRED_INDICATORS
from utils import merge_with_existing, sanity_check

API_KEY = os.environ.get("FRED_API_KEY")
if not API_KEY:
    raise ValueError("FRED_API_KEY 환경변수가 설정되지 않았습니다.")

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = DATA_DIR / "fred_indicators.parquet"


def fetch_series(series_id: str, start_date: str = "2015-01-01") -> pd.DataFrame:
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
    if df.empty:
        return df
    df = df[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().reset_index(drop=True)
    return df


def main():
    print(f"[FRED] 시작: {datetime.utcnow().isoformat()}Z")

    all_data = []
    all_warnings = []
    failed = []

    # ← 핵심 수정: (series_id, value_range) 튜플 언패킹
    for name, (series_id, value_range) in FRED_INDICATORS.items():
        print(f"  - {name:<22s} ({series_id:<15s})...", end=" ")
        try:
            df = fetch_series(series_id)
            if df.empty:
                print("EMPTY (데이터 없음)")
                continue

            df["indicator"] = name
            df["series_id"] = series_id

            warnings = sanity_check(
                df, name=name, value_range=value_range, max_lag_days=None
            )
            for w in warnings:
                print(f"\n    ⚠ {w}", end="")
            all_warnings.extend(warnings)

            all_data.append(df)
            latest = df["date"].max().strftime("%Y-%m-%d")
            print(f"  OK ({len(df):,}건, 최근 {latest})")

        except Exception as e:
            failed.append((name, str(e)))
            print(f"FAIL: {e}")

    if not all_data:
        raise RuntimeError("모든 FRED 시계열 수집 실패. API 키를 확인하세요.")

    new_df = pd.concat(all_data, ignore_index=True)
    new_df = new_df[["date", "indicator", "series_id", "value"]]

    merged = merge_with_existing(new_df, OUTPUT_FILE, key_cols=["date", "indicator"])

    print(f"\n[FRED] 저장: {OUTPUT_FILE}")
    print(f"  전체 누적 행: {len(merged):,}")
    if failed:
        print(f"  실패 {len(failed)}개: {[f[0] for f in failed]}")
    if all_warnings:
        print(f"  경고 {len(all_warnings)}건")


if __name__ == "__main__":
    main()
