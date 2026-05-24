"""
yfinance에서 주요 시장 가격을 가져와 Parquet으로 저장.
"""

import sys
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent))
from config import YFINANCE_TICKERS
from utils import merge_with_existing, sanity_check

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = DATA_DIR / "market_prices.parquet"


def fetch_ticker(name: str, ticker: str, period: str = "10y") -> pd.DataFrame:
    t = yf.Ticker(ticker)
    hist = t.history(period=period, auto_adjust=False)
    if hist.empty:
        raise ValueError("빈 데이터")
    df = hist[["Close"]].reset_index()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df["indicator"] = name
    df["ticker"] = ticker
    return df[["date", "indicator", "ticker", "value"]]


def main():
    print(f"[yfinance] 시작: {datetime.utcnow().isoformat()}Z")

    all_data = []
    all_warnings = []
    failed = []

    for name, (ticker, value_range) in YFINANCE_TICKERS.items():
        print(f"  - {name:10s} ({ticker:12s})...", end=" ")
        try:
            df = fetch_ticker(name, ticker)
            warnings = sanity_check(df, name=name, value_range=value_range, max_lag_days=5)
            for w in warnings:
                print(f"\n    ⚠ {w}", end="")
            all_warnings.extend(warnings)
            all_data.append(df)
            latest = df["date"].max().strftime("%Y-%m-%d")
            print(f"  OK ({len(df):,}건, 최근 {latest})")
            time.sleep(0.5)  # Yahoo 차단 방지
        except Exception as e:
            failed.append((name, str(e)))
            print(f"FAIL: {e}")

    if not all_data:
        print("\n[yfinance] 전체 실패. Yahoo 일시 차단 가능성. 내일 재시도.")
        return  # 워크플로 전체를 죽이지 않음

    new_df = pd.concat(all_data, ignore_index=True)
    merged = merge_with_existing(new_df, OUTPUT_FILE, key_cols=["date", "indicator"])

    print(f"\n[yfinance] 저장: {OUTPUT_FILE}")
    print(f"  전체 누적 행: {len(merged):,}")
    if failed:
        print(f"  실패 {len(failed)}개: {[f[0] for f in failed]}")
    if all_warnings:
        print(f"  경고 {len(all_warnings)}건")


if __name__ == "__main__":
    main()
