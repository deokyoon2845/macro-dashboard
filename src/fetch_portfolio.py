"""보유 종목 일일 가격 수집 — portfolio.json → portfolio_prices.parquet"""
import json, time
import yfinance as yf
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT/"data"
PORT_FILE = DATA/"portfolio.json"
OUT_FILE  = DATA/"portfolio_prices.parquet"

def load_portfolio():
    if not PORT_FILE.exists(): return []
    with open(PORT_FILE, encoding="utf-8") as f: return json.load(f)

def fetch_one(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="30d", auto_adjust=False)
        if hist.empty: return []
        currency = t.info.get("currency","USD")
        return [{"ticker":ticker,"date":pd.Timestamp(i.date()),
                 "close":float(r["Close"]),"currency":currency}
                for i, r in hist.iterrows()]
    except Exception as e:
        print(f"  ✗ {ticker}: {e}"); return []

def main():
    items = load_portfolio()
    if not items: print("portfolio.json 비어있음."); return
    tickers = sorted(set(it["ticker"] for it in items if isinstance(it, dict) and it.get("ticker")))
    print(f"수집: {len(tickers)}개 티커")
    df_old = pd.DataFrame()
    if OUT_FILE.exists():
        df_old = pd.read_parquet(OUT_FILE)
        df_old["date"] = pd.to_datetime(df_old["date"])
    all_rows = []
    for tk in tickers:
        rows = fetch_one(tk)
        if rows: all_rows.extend(rows); print(f"  ✓ {tk}: {len(rows)}일")
        time.sleep(0.5)
    if not all_rows: return
    df_new = pd.DataFrame(all_rows)
    df = pd.concat([df_old, df_new], ignore_index=True) if not df_old.empty else df_new
    df = df.drop_duplicates(subset=["date","ticker"], keep="last").sort_values(["ticker","date"])
    DATA.mkdir(exist_ok=True)
    df.to_parquet(OUT_FILE, index=False)
    print(f"✅ 저장: {len(df)} rows")

if __name__ == "__main__": main()
