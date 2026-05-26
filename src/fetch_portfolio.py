"""
보유 종목 가격 자동 수집 — portfolio.json 읽어서 yfinance로 일일 종가 저장
"""
import json
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime
import time

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
PORT_FILE = DATA / "portfolio.json"
OUT_FILE = DATA / "portfolio_prices.parquet"

def load_portfolio():
    if not PORT_FILE.exists():
        print("portfolio.json 없음. 수집할 종목 없음.")
        return []
    with open(PORT_FILE, encoding="utf-8") as f:
        return json.load(f)

def fetch_one(ticker):
    """yfinance에서 최근 30일 종가 가져오기"""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="30d", auto_adjust=False)
        if hist.empty:
            print(f"  ✗ {ticker}: 데이터 없음")
            return []
        currency = t.info.get("currency", "USD")
        rows = []
        for idx, row in hist.iterrows():
            rows.append({
                "ticker": ticker,
                "date": pd.Timestamp(idx.date()),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
                "currency": currency,
            })
        return rows
    except Exception as e:
        print(f"  ✗ {ticker}: {e}")
        return []

def main():
    items = load_portfolio()
    if not items:
        return

    tickers = sorted(set(item["ticker"] for item in items if item.get("ticker")))
    print(f"수집 대상: {len(tickers)}개 티커")

    # 기존 데이터 로드
    if OUT_FILE.exists():
        df_old = pd.read_parquet(OUT_FILE)
        df_old["date"] = pd.to_datetime(df_old["date"])
    else:
        df_old = pd.DataFrame()

    all_new = []
    for tk in tickers:
        rows = fetch_one(tk)
        if rows:
            all_new.extend(rows)
            print(f"  ✓ {tk}: {len(rows)}일치, 최근가 {rows[-1]['close']:.2f} {rows[-1]['currency']}")
        time.sleep(0.5)  # yfinance rate limit

    if not all_new:
        print("새로 수집된 데이터 없음.")
        return

    df_new = pd.DataFrame(all_new)

    # 머지 (date+ticker 기준 중복 제거)
    if not df_old.empty:
        df = pd.concat([df_old, df_new], ignore_index=True)
        df = df.drop_duplicates(subset=["date", "ticker"], keep="last")
    else:
        df = df_new

    df = df.sort_values(["ticker", "date"])
    DATA.mkdir(exist_ok=True)
    df.to_parquet(OUT_FILE, index=False)
    print(f"저장 완료: {OUT_FILE} ({len(df)} rows)")

if __name__ == "__main__":
    main()
