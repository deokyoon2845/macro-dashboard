"""
PyKRX에서 KOSPI 외국인 순매수 데이터 가져오기.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
from pykrx import stock

sys.path.insert(0, str(Path(__file__).parent))
from utils import merge_with_existing, sanity_check

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = DATA_DIR / "kospi_flows.parquet"


def main():
    print(f"[PyKRX] 시작: {datetime.utcnow().isoformat()}Z")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 3)
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    print(f"  기간: {start_str} ~ {end_str}")

    try:
        df = stock.get_market_trading_value_by_date(start_str, end_str, "KOSPI")
    except Exception as e:
        raise RuntimeError(f"PyKRX 조회 실패: {e}")

    df = df.reset_index()

    if "외국인" not in df.columns:
        raise RuntimeError(f"외국인 컬럼 없음. 실제 컬럼들: {list(df.columns)}")

    result = df[["날짜", "외국인"]].copy()
    result.columns = ["date", "value"]
    result["date"] = pd.to_datetime(result["date"])
    result["indicator"] = "KOSPI_FOREIGN_NET"
    result = result[["date", "indicator", "value"]]

    warnings = sanity_check(result, name="KOSPI_FOREIGN_NET", max_lag_days=5)
    for w in warnings:
        print(f"  ⚠ {w}")

    merged = merge_with_existing(result, OUTPUT_FILE, key_cols=["date", "indicator"])

    print(f"[PyKRX] 저장: {OUTPUT_FILE}")
    print(f"  전체 누적 행: {len(merged):,}")
    print(f"  최근 날짜: {result['date'].max().strftime('%Y-%m-%d')}")
    print(f"  최근 5거래일 외국인 순매수 (원):")
    print(result.tail().to_string(index=False))


if __name__ == "__main__":
    main()
