"""일일 AI 브리핑 — 모든 데이터를 종합하여 Claude가 요약"""
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
OUT_FILE = DATA/"daily_briefing.json"
API_KEY = os.environ.get("ANTHROPIC_API_KEY","")
MODEL = "claude-haiku-4-5-20251001"

def load_pq(name):
    p=DATA/name
    if not p.exists(): return pd.DataFrame()
    df=pd.read_parquet(p)
    if "date" in df.columns: df["date"]=pd.to_datetime(df["date"])
    return df

def load_json(name, d):
    p=DATA/name
    if not p.exists(): return d
    with open(p, encoding="utf-8") as f: return json.load(f)

def latest(df, ind):
    if df.empty or "indicator" not in df.columns: return None
    s=df[df["indicator"]==ind].sort_values("date")
    return float(s.iloc[-1]["value"]) if not s.empty else None

def pct_chg(df, ind):
    if df.empty or "indicator" not in df.columns: return 0,0
    s=df[df["indicator"]==ind].sort_values("date").tail(2)
    if len(s)<2: return 0,0
    return s.iloc[1]["value"], (s.iloc[1]["value"]/s.iloc[0]["value"]-1)*100

def build_market():
    m=load_pq("market_prices.parquet"); f=load_pq("fred_indicators.parquet"); s=load_pq("sentiment.parquet")
    lines=[]
    for ind,lbl in [("SPX","S&P500"),("NASDAQ","NASDAQ"),("KOSPI","KOSPI"),("KOSDAQ","KOSDAQ")]:
        v,p=pct_chg(m,ind)
        if v: lines.append(f"  {lbl}: {v:,.0f} ({p:+.2f}%)")
    for ind,lbl in [("VIX","VIX"),("USDKRW","USD/KRW")]:
        v=latest(m,ind)
        if v: lines.append(f"  {lbl}: {v:,.0f}" if lbl=="USD/KRW" else f"  {lbl}: {v:.1f}")
    v=latest(f,"US_10Y"); fg=latest(s,"FEAR_GREED")
    if v: lines.append(f"  US10Y: {v:.2f}%")
    if fg: lines.append(f"  F&G: {fg:.0f}")
    return "\n".join(lines) or "(데이터 없음)"

def build_portfolio():
    items=load_json("portfolio.json",[])
    prices=load_pq("portfolio_prices.parquet"); market=load_pq("market_prices.parquet")
    if not items or prices.empty: return "(보유 종목 없음)"
    fx=latest(market,"USDKRW") or 1380
    positions=[]
    for it in items:
        lots=it.get("lots",[]); ticker=it.get("ticker","")
        if not lots: continue
        qty=sum(l["qty"] for l in lots); cost=sum(l["qty"]*l["price"] for l in lots)
        avg=cost/qty if qty>0 else 0
        sub=prices[prices["ticker"]==ticker].sort_values("date")
        if sub.empty: continue
        cur=float(sub.iloc[-1]["close"]); prev=float(sub.iloc[-2]["close"]) if len(sub)>=2 else cur
        fxv=fx if it.get("currency")=="USD" else 1
        positions.append({"name":it["name"],"value":cur*qty*fxv,
                          "pnl_krw":(cur-avg)*qty*fxv,"daily_pct":(cur/prev-1)*100 if prev>0 else 0})
    if not positions: return "(가격 데이터 없음)"
    tv=sum(p["value"] for p in positions); tp=sum(p["pnl_krw"] for p in positions)
    tpct=tp/(tv-tp)*100 if (tv-tp)>0 else 0
    up=sorted(positions,key=lambda x:x["daily_pct"],reverse=True)[:3]
    dn=sorted(positions,key=lambda x:x["daily_pct"])[:3]
    return (f"  총평가: {tv:,.0f}원\n  누적손익: {tp:+,.0f}원 ({tpct:+.2f}%)\n"
            f"  상승: {', '.join(f'{p[\"name\"]}({p[\"daily_pct\"]:+.2f}%)' for p in up if p['daily_pct']>0)}\n"
            f"  하락: {', '.join(f'{p[\"name\"]}({p[\"daily_pct\"]:+.2f}%)' for p in dn if p['daily_pct']<0)}")

def build_news():
    news=load_json("portfolio_news.json",{})
    lines=[]
    for cat in ("stocks","sectors"):
        for key,articles in news.get(cat,{}).items():
            for n in articles:
                sc=n.get("score")
                if sc is not None and (sc>=8 or sc<=2):
                    tag="호재" if sc>=6 else "악재"
                    lines.append(f"  [{tag} {sc}] {key}: {n.get('ai_summary') or n.get('title','')[:60]}")
    lines.sort(key=lambda x:("악재" in x,x),reverse=True)
    return "\n".join(lines[:6]) or "(주요 뉴스 없음)"

def main():
    if not API_KEY: print("⚠ ANTHROPIC_API_KEY 없음"); return
    today_str=datetime.now().strftime("%Y년 %m월 %d일")
    prompt=f"""한국 retail 투자자를 위한 시장 브리핑을 작성하세요.

[{today_str} 데이터]
▣ 시장\n{build_market()}
▣ 포트폴리오\n{build_portfolio()}
▣ 주요 뉴스 (AI 점수 8+ 호재 / 2- 악재)\n{build_news()}

다음 JSON 형식으로만 응답:
{{"headline":"오늘 핵심 1줄 (20자 이내)","market":"시장 요약 1-2문장","portfolio":"포트폴리오 핵심 1-2문장","watch":"주의/관심 사항 1-2문장","comment":"액션 코멘트 (관망/리밸런싱/공격적/방어적 포함)","mood":"positive 또는 neutral 또는 cautious"}}"""
    client=Anthropic(api_key=API_KEY)
    print("🤖 브리핑 생성 중…")
    msg=client.messages.create(model=MODEL,max_tokens=700,messages=[{"role":"user","content":prompt}])
    text=msg.content[0].text.strip()
    m=re.search(r'\{.*\}',text,re.DOTALL)
    if not m: print("✗ JSON 파싱 실패"); return
    result=json.loads(m.group())
    result.update({"generated_at":datetime.now().isoformat(),"date_label":today_str})
    DATA.mkdir(exist_ok=True)
    with open(OUT_FILE,"w",encoding="utf-8") as f: json.dump(result,f,ensure_ascii=False,indent=2)
    print(f"✅ {result.get('headline','')}\n   💬 {result.get('comment','')}")

if __name__ == "__main__": main()
