import sys
print("ECOS 스크립트 시작", flush=True)

"""
한국은행 ECOS API에서 100대 주요 통계를 매일 수집·누적 저장.
KeyStatisticList: 한국 기준금리, 시장금리, 환율, 가계신용 등 한 번에 수신.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from utils import sanity_check

API_KEY = os.environ.get("ECOS_API_KEY")
if not API_KEY:
    raise ValueError("ECOS_API_KEY 환경변수가 설정되지 않았습니다.")

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
LATEST_FILE  = DATA_DIR / "ecos_latest.parquet"   # 가장 최신 스냅샷 (항상 덮어쓰기)
HISTORY_FILE = DATA_DIR / "ecos_history.parquet"  # 매일 누적


def fetch_key_statistics() -> pd.DataFrame:
    """ECOS 100대 통계 한 번에 조회."""
    url = f"https://ecos.bok.or.kr/api/KeyStatisticList/{API_KEY}/json/kr/1/100"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()

    if "RESULT" in data:
        raise RuntimeError(f"ECOS API 에러: {data['RESULT']}")
    if "KeyStatisticList" not in data:
        raise RuntimeError(f"예상치 못한 응답 구조: {str(data)[:300]}")

    rows = data["KeyStatisticList"].get("row", [])
    if not rows:
        raise RuntimeError("ECOS 응답에 데이터 없음")

    return pd.DataFrame(rows)


def main():
    print(f"[ECOS] 시작: {datetime.utcnow().isoformat()}Z")

    df = fetch_key_statistics()
    print(f"  {len(df)}개 항목 수신")
    print(f"  컬럼들: {list(df.columns)}")

    # 수집 시각 기록
    fetched_at = pd.Timestamp.utcnow().tz_localize(None).normalize()
    df["fetched_date"] = fetched_at

    # 최신 스냅샷 저장 (항상 덮어쓰기)
    df.to_parquet(LATEST_FILE, index=False)

    # 누적 히스토리: 같은 날 중복 제거 후 추가
    if HISTORY_FILE.exists():
        try:
            existing = pd.read_parquet(HISTORY_FILE)
            existing = existing[
                pd.to_datetime(existing["fetched_date"]).dt.normalize() != fetched_at
            ]
            combined = pd.concat([existing, df], ignore_index=True)
        except Exception as e:
            print(f"  기존 히스토리 읽기 실패, 새로 시작: {e}")
            combined = df
    else:
        combined = df

    combined.to_parquet(HISTORY_FILE, index=False)
    print(f"  누적 히스토리: {len(combined):,}건 ({len(combined) // max(len(df), 1)}일치)")

    # 주요 항목 미리보기
    preview_cols = [c for c in ["CLASS_NAME", "KEYSTAT_NAME", "DATA_VALUE", "UNIT_NAME"]
                    if c in df.columns]
    if preview_cols:
        print("\n=== 주요 항목 미리보기 ===")
        with pd.option_context("display.max_rows", 30, "display.max_colwidth", 35, "display.width", 180):
            print(df[preview_cols].head(30).to_string(index=False))

    # 수출/무역 관련 항목 자동 탐지
    if "KEYSTAT_NAME" in df.columns:
        export_rows = df[df["KEYSTAT_NAME"].str.contains("수출|무역|수입", na=False)]
        if len(export_rows) > 0:
            print(f"\n=== 수출·무역 관련 항목 {len(export_rows)}개 ===")
            print(export_rows[preview_cols].to_string(index=False))
        else:
            print("\n수출·무역 항목이 100대 통계에 없음 → 다음 단계에서 별도 시계열 추가")

    # sanity check
    warnings = sanity_check(df, name="ECOS_KEYSTAT", max_lag_days=None)
    for w in warnings:
        print(f"  ⚠ {w}")

    if len(df) < 50:
        print(f"  ⚠ 항목 수가 너무 적음 ({len(df)}개). API 키 또는 응답 확인 필요.")


if __name__ == "__main__":
    main()
