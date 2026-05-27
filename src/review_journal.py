"""거래 일지 AI 자동 회고 — 7/30/90/180일 경과 시"""
import json, os, re
from pathlib import Path
from datetime import datetime
import pandas as pd

try:
    from anthropic import Anthropic
except ImportError:
    raise SystemExit(0)

ROOT = Path(__file__).parent.parent
DATA = ROOT/"data"
JOURNAL_FILE = DATA/"trade_journal.json"
PRICES_FILE  = DATA/"portfolio_prices.parquet"
API_KEY = os.environ.get("ANTHROPIC_API_KEY","")
MODEL   = "claude-haiku-4-5-20251001"
THRESHOLDS = [7, 30, 90, 180]

def latest_price(prices, ticker):
    if prices.empty: return None
    sub=prices[prices["ticker"]==ticker].sort_values("date")
    return float(sub.iloc[-1]["close"]) if not sub.empty else None

def review_one(client, entry, cur, pct):
    prompt=(f"매수 일지 회고 요청.\n"
            f"종목: {entry['stock_name']} | 매수가: {entry['price']:,} | 수량: {entry['qty']}\n"
            f"매수 사유: {entry.get('thesis','')}\n"
            f"목표: 상승 {entry.get('target_pct_high',0)}% / 손절 {entry.get('target_pct_low',0)}%\n"
            f"현재: {cur:,.2f} ({pct:+.2f}%) | 경과: {(datetime.now()-datetime.fromisoformat(entry['created'])).days}일\n\n"
            "다음 JSON으로만 응답:\n"
            '{"summary":"현황 1줄 (40자)","thesis_check":"사유 검증 1-2문장","lesson":"교훈 1-2문장","verdict":"정답 또는 오답 또는 판단보류"}')
    try:
        msg=client.messages.create(model=MODEL,max_tokens=400,messages=[{"role":"user","content":prompt}])
        text=msg.content[0].text.strip()
        m=re.search(r'\{.*\}',text,re.DOTALL)
        return json.loads(m.group()) if m else None
    except Exception as e: print(f"  ✗ {e}"); return None

def main():
    if not API_KEY: return
    if not JOURNAL_FILE.exists(): return
    with open(JOURNAL_FILE, encoding="utf-8") as f: entries=json.load(f)
    if not entries: return
    prices=pd.read_parquet(PRICES_FILE) if PRICES_FILE.exists() else pd.DataFrame()
    if not prices.empty: prices["date"]=pd.to_datetime(prices["date"])
    client=Anthropic(api_key=API_KEY); now=datetime.now(); added=0
    for entry in entries:
        if entry.get("type")!="buy": continue
        days_passed=(now-datetime.fromisoformat(entry["created"])).days
        existing=[r.get("days_passed",0) for r in entry.get("ai_reviews",[])]
        for th in THRESHOLDS:
            if days_passed>=th and not any(th-3<=e<=th+30 for e in existing):
                cur=latest_price(prices,entry["ticker"])
                if not cur: continue
                pct=(cur/entry["price"]-1)*100
                print(f"  📝 {entry['stock_name']} ({th}일 회고)")
                rv=review_one(client,entry,cur,pct)
                if rv:
                    rv.update({"days_passed":days_passed,"reviewed_at":now.isoformat(),
                               "current_price":cur,"change_pct":pct})
                    entry.setdefault("ai_reviews",[]).append(rv); added+=1
                break
    if added:
        with open(JOURNAL_FILE,"w",encoding="utf-8") as f:
            json.dump(entries,f,ensure_ascii=False,indent=2)
        print(f"✅ {added}건 회고 추가")

if __name__ == "__main__": main()
