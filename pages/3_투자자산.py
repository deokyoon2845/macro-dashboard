"""
3. 투자자산 현황
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import json

st.set_page_config(page_title="투자자산", page_icon="📈", layout="wide",
                   initial_sidebar_state="expanded")

BG="#F5F0E5"; CARD="#FFFFFF"; C2="#FAF6EC"; BORD="#E5DDD0"
TXT="#2A2620"; SUB="#5A5246"; MUT="#8C7F6E"; PUR_HI="#BAE6FD"
B5="#2563EB"; B6="#1D4ED8"; B8="#1E3A8A"
GREEN="#059669"; RED="#DC2626"

st.markdown(f"""<style>
html,body,[class*="css"]{{background-color:{BG}!important;color:{TXT}!important;
  font-family:'MaruBuri','Gowun Batang',serif!important;letter-spacing:.015em!important}}
.block-container{{padding:1.5rem 2rem 3rem!important;background:transparent!important;max-width:100%!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
[data-testid="stSidebar"]{{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
#MainMenu,footer,header{{visibility:hidden}}
.stButton>button{{background:{CARD}!important;color:{TXT}!important;border:1px solid {BORD}!important;border-radius:8px!important}}
</style>""", unsafe_allow_html=True)

st.markdown(f"""
<div style="font-family:'MaruBuri',serif;font-size:28px;font-weight:700;
  font-style:italic;margin-bottom:4px">
  <span style="background:linear-gradient(180deg,transparent 55%,{PUR_HI} 55%);padding:0 6px">
    📈 투자자산 현황
  </span>
</div>
<div style="font-size:11px;color:{MUT};margin-bottom:1.5rem">보유 종목 평가손익 · 자산 배분</div>
""", unsafe_allow_html=True)

DATA_DIR  = Path(__file__).parent.parent / "data"
PORT_FILE = DATA_DIR / "portfolio.json"
market = pd.DataFrame()
try:
    mf = DATA_DIR / "market_prices.parquet"
    if mf.exists():
        market = pd.read_parquet(mf)
        market["date"] = pd.to_datetime(market["date"])
except: pass

def load_portfolio():
    if PORT_FILE.exists():
        with open(PORT_FILE) as f: return json.load(f)
    return []

def save_portfolio(data):
    with open(PORT_FILE,"w") as f: json.dump(data, f, ensure_ascii=False)

def get_price(ind):
    if market.empty: return None
    s = market[market["indicator"]==ind].sort_values("date")
    return s.iloc[-1]["value"] if not s.empty else None

portfolio = load_portfolio()

# ── 종목 추가 ─────────────────────────────────────────────────
with st.expander("➕ 종목 추가"):
    c1,c2,c3,c4 = st.columns(4)
    with c1: p_name   = st.text_input("종목명", placeholder="삼성전자")
    with c2: p_ticker = st.text_input("티커 (config 내)", placeholder="KR_SAMSUNG")
    with c3: p_qty    = st.number_input("수량", min_value=0.0, step=1.0)
    with c4: p_cost   = st.number_input("평균 매수가", min_value=0.0, step=100.0)
    p_currency = st.selectbox("통화", ["KRW","USD"])
    if st.button("추가", type="primary") and p_name:
        portfolio.append({"name":p_name,"ticker":p_ticker,"qty":p_qty,
                          "cost":p_cost,"currency":p_currency})
        save_portfolio(portfolio)
        st.success("추가 완료!"); st.rerun()

# ── 포트폴리오 요약 ───────────────────────────────────────────
if portfolio:
    rows = []
    for item in portfolio:
        current = get_price(item["ticker"])
        if current:
            total_cost = item["qty"] * item["cost"]
            total_val  = item["qty"] * current
            pnl  = total_val - total_cost
            pnl_pct = (pnl / total_cost * 100) if total_cost > 0 else 0
        else:
            total_cost = item["qty"] * item["cost"]
            total_val = total_cost; pnl = 0; pnl_pct = 0; current = None
        rows.append({
            "종목": item["name"], "티커": item["ticker"],
            "수량": item["qty"], "평균가": f"{item['cost']:,.0f}",
            "현재가": f"{current:,.0f}" if current else "N/A",
            "평가금액": f"{total_val:,.0f}",
            "손익": f"{pnl:+,.0f}",
            "손익률": f"{pnl_pct:+.2f}%",
            "_val": total_val, "_pnl_pct": pnl_pct,
        })

    df_port = pd.DataFrame(rows)
    total_value = sum(r["_val"] for r in rows)

    m1,m2,m3 = st.columns(3)
    for col,(lbl,val,clr) in zip([m1,m2,m3],[
        ("총 평가금액", f"{total_value:,.0f}원", B5),
        ("총 평가손익", f"{sum(r['_val']-r['수량']*float(str(r['평균가']).replace(',','')) for r in rows if r['현재가'] != 'N/A'):+,.0f}원" if rows else "—", GREEN),
        ("보유 종목 수", f"{len(portfolio)}개", B5),
    ]):
        with col:
            st.markdown(f"""<div style="background:{CARD};border:1px solid {BORD};
              border-radius:8px;padding:14px">
              <div style="font-size:10px;color:{MUT}">{lbl}</div>
              <div style="font-size:20px;font-weight:700;color:{clr}">{val}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    c1,c2 = st.columns([1.5,1])
    with c1:
        display_cols = ["종목","수량","평균가","현재가","평가금액","손익","손익률"]
        st.dataframe(df_port[display_cols], use_container_width=True, hide_index=True)

    with c2:
        # 자산 배분 도넛
        labels = [r["종목"] for r in rows]
        values = [r["_val"] for r in rows]
        if any(v>0 for v in values):
            fig = go.Figure(go.Pie(labels=labels,values=values,hole=0.5,
                textinfo="label+percent",textfont_size=10))
            fig.update_layout(paper_bgcolor=CARD,height=300,
                title=dict(text="자산 배분",font=dict(size=11,color=SUB),x=0.01),
                margin=dict(l=8,r=8,t=28,b=8),
                legend=dict(orientation="h",y=-0.15,font=dict(size=9)))
            st.plotly_chart(fig, use_container_width=True)

    if st.button("🗑️ 선택 삭제 (마지막 항목)") and portfolio:
        portfolio.pop(); save_portfolio(portfolio); st.rerun()
else:
    st.info("보유 종목을 추가해주세요. 티커는 config.py의 YFINANCE_TICKERS 키명을 사용하세요.")
    st.caption("예: 삼성전자 → KR_SAMSUNG / Apple → AAPL / KOSPI → KOSPI")
