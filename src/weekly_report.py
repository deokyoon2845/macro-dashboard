"""주간 AI 리포트 — 매주 월요일 자동 생성"""
import json, os, re
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

try:
    from anthropic import Anthropic
except ImportError:
    raise SystemExit(0)

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
OUT_FILE = DATA / "weekly_report.json"
API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL    = "claude-haiku-4-5-20251001"


def load_pq(name):
    p = DATA / name
    if not p.exists(): return pd.DataFrame()
    df = pd.read_parquet(p)
    if "date" in df.columns: df["date"] = pd.to_datetime(df["date"])
    return df


def load_json(name, d=None):
    p = DATA / name
    if not p.exists(): return d or {}
    with open(p, encoding="utf-8") as f: return json.load(f)


def build_summary():
    prices    = load_pq("portfolio_prices.parquet")
    market    = load_pq("market_prices.parquet")
    portfolio = load_json("portfolio.json", [])

    today = datetime.now(); week_ago = today - timedelta(days=7)
    lines = []

    # ── 시장 주간 등락 ─────────────────────────────────────
    if not market.empty and "indicator" in market.columns:
        lines.append("【글로벌 시장】")
        for ind, lbl in [("SPX","S&P500"),("NASDAQ","NASDAQ"),
                         ("KOSPI","KOSPI"),("KOSDAQ","KOSDAQ"),("USDKRW","USD/KRW")]:
            sub = market[market["indicator"]==ind].sort_values("date").tail(8)
            if len(sub) < 2: continue
            v_end = float(sub.iloc[-1]["value"])
            v_start = float(sub.iloc[max(0, len(sub)-6)]["value"])
            pct = (v_end / v_start - 1) * 100 if v_start > 0 else 0
            lines.append(f"  {lbl}: {v_end:,.2f} ({pct:+.2f}%)")

    # ── 종목별 주간 성과 ───────────────────────────────────
    if not prices.empty and portfolio:
        lines.append("\n【종목별 주간 성과】")
        for it in portfolio:
            ticker = it.get("ticker","")
            sub = prices[prices["ticker"]==ticker].sort_values("date")
            w = sub[sub["date"] >= pd.Timestamp(week_ago)]
            if len(w) < 2: continue
            pct = (float(w.iloc[-1]["close"]) / float(w.iloc[0]["close"]) - 1) * 100
            symbol = "▲" if pct >= 0 else "▼"
            lines.append(f"  {it['name']} ({ticker}): {symbol}{abs(pct):.2f}%")

    # ── 포트폴리오 전체 주간 등락 (시가총액 가중) ──────────
    if not prices.empty and portfolio:
        fx_series = market[market["indicator"]=="USDKRW"].sort_values("date") \
            if not market.empty and "indicator" in market.columns else pd.DataFrame()
        def get_fx(d):
            if fx_series.empty: return 1380.0
            s = fx_series[fx_series["date"] <= pd.Timestamp(d)]
            return float(s.iloc[-1]["value"]) if not s.empty else 1380.0
        def pf_value(d):
            tv = 0
            for it in portfolio:
                qty = sum(l["qty"] for l in it.get("lots",[])
                          if pd.Timestamp(l["date"]) <= pd.Timestamp(d))
                if qty <= 0: continue
                ps = prices[(prices["ticker"]==it["ticker"]) &
                            (prices["date"] <= pd.Timestamp(d))].sort_values("date")
                if ps.empty: continue
                fxv = get_fx(d) if it.get("currency")=="USD" else 1
                tv += qty * float(ps.iloc[-1]["close"]) * fxv
            return tv
        try:
            v_now = pf_value(today); v_prev = pf_value(week_ago)
            if v_prev > 0:
                pct = (v_now / v_prev - 1) * 100
                lines.append(f"\n【포트폴리오 전체】")
                lines.append(f"  주간 수익률: {pct:+.2f}%")
                lines.append(f"  현재 평가금액: {v_now:,.0f}원")
        except: pass

    return "\n".join(lines) if lines else "(데이터 없음)"


def main():
    if not API_KEY: print("⚠ ANTHROPIC_API_KEY 없음"); return

    week_range = ((datetime.now()-timedelta(days=7)).strftime("%m/%d")
                  + " ~ " + datetime.now().strftime("%m/%d"))

    prompt = f"""한국 retail 투자자 주간 리포트입니다.

기간: {week_range}
{build_summary()}

다음 JSON 형식으로만 응답 (다른 텍스트 금지):
{{"headline":"이번 주 핵심 1줄 25자 이내","performance":"포트폴리오 성과 요약 2문장","market_context":"글로벌 시장 환경 1-2문장","best":"이번 주 가장 잘된 점 1문장","worst":"이번 주 아쉬운 점 1문장","lessons":"교훈 및 인사이트 1-2문장","next_week":"다음 주 주목 포인트 1-2문장","score":0~10,"grade":"S 또는 A 또는 B 또는 C 또는 D"}}"""

    client = Anthropic(api_key=API_KEY)
    print(f"📊 주간 리포트 생성 중 ({week_range})…")
    try:
        msg = client.messages.create(model=MODEL, max_tokens=700,
            messages=[{"role":"user","content":prompt}])
        text = msg.content[0].text.strip()
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if not m: print("✗ JSON 파싱 실패"); return
        result = json.loads(m.group())
        result.update({"generated_at":datetime.now().isoformat(),
                       "week_range":week_range})
        DATA.mkdir(exist_ok=True)
        with open(OUT_FILE,"w",encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ 등급 {result.get('grade','')} | {result.get('headline','')}")
    except Exception as e:
        print(f"✗ {e}")


if __name__ == "__main__":
    main()
