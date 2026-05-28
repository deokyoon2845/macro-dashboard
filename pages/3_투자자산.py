"""3. 투자자산 — QLD 스타일 리디자인"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime, date
import json, uuid
import numpy as np

st.set_page_config(page_title="투자자산", page_icon="📈", layout="wide",
                   initial_sidebar_state="expanded")

# ── 홈 버튼 ─────────────────────────────────────────────────
with st.sidebar:
    st.page_link("Home.py", label="🏠  홈으로 돌아가기", use_container_width=True)
    st.markdown(
        f'<div style="height:1px;background:#222A3A;margin:6px 0"></div>',
        unsafe_allow_html=True
    )

# ── 디자인 시스템 ─────────────────────────────────────────────
BG    = "#0A0D13"
CARD  = "#111620"
C2    = "#161C28"
C3    = "#1C2438"
BORD  = "#222A3A"
G     = "#181F2C"
TXT   = "#E4EAF6"
SUB   = "#7A8CA4"
MUT   = "#4A5668"
ACC   = "#4A82E4"
UP    = "#2ECC71"
DN    = "#E74C3C"
GOLD  = "#F5A623"

# 보유 종목 컬러 팔레트 (최대 12개)
HOLD_COLORS = ["#4A82E4","#FF6B6B","#4ECDC4","#F7DC6F","#BB8FCE","#58D68D",
               "#F0B27A","#7FB3D3","#82E0AA","#F1948A","#AED6F1","#FADBD8"]

st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Gowun+Batang:wght@400;700&display=swap" rel="stylesheet">
<style>
html,body,[class*="css"]{{
  background-color:{BG}!important;
  color:{TXT}!important;
  font-family:'Inter','Gowun Batang',sans-serif!important;
  letter-spacing:-.01em!important;
}}
.block-container{{padding:0 1.5rem 2rem!important;max-width:100%!important;background:transparent!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
[data-testid="stSidebar"]{{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
#MainMenu,footer,header{{visibility:hidden}}
p,span,div,label,th,td{{color:{TXT}!important;letter-spacing:-.01em!important}}
/* 버튼 */
.stButton>button{{
  background:{C2}!important;color:{TXT}!important;
  border:1px solid {BORD}!important;border-radius:6px!important;
  font-family:'Inter',sans-serif!important;font-size:12px!important;
  padding:5px 14px!important;font-weight:500!important;box-shadow:none!important}}
.stButton>button:hover{{background:{C3}!important;border-color:{ACC}!important;color:{ACC}!important}}
/* radio 버튼을 탭처럼 */
[data-testid="stRadio"]>div{{gap:2px!important;flex-direction:row!important}}
[data-testid="stRadio"]>div>label{{
  background:{C2}!important;color:{SUB}!important;border:1px solid {BORD}!important;
  border-radius:6px!important;padding:6px 14px!important;font-size:11px!important;
  font-family:'Inter',sans-serif!important;font-weight:500!important;cursor:pointer!important}}
[data-testid="stRadio"]>div>label[data-selected="true"]{{
  background:{ACC}!important;color:#FFFFFF!important;border-color:{ACC}!important}}
/* Plotly */
.js-plotly-plot{{border-radius:10px!important}}
/* tabs */
.stTabs [data-baseweb="tab-list"]{{background:{CARD}!important;border-bottom:1px solid {BORD}!important;gap:0}}
.stTabs [data-baseweb="tab"]{{background:transparent!important;color:{SUB}!important;
  font-family:'Inter',sans-serif!important;font-size:12px!important;font-weight:500!important;
  border-bottom:2px solid transparent!important;padding:10px 20px!important}}
.stTabs [aria-selected="true"]{{color:{TXT}!important;border-bottom-color:{ACC}!important}}
.stTabs [data-baseweb="tab-panel"]{{background:transparent!important;padding:0!important}}

/* ── 사이드바 접힘 토글 버튼 강조 ────────────────────────── */
[data-testid="collapsedControl"] {{
  background:{CARD} !important;
  border:2px solid {B5} !important;
  border-left:none !important;
  border-radius:0 10px 10px 0 !important;
  width:2.4rem !important;
  top:0.8rem !important;
  box-shadow:4px 0 14px rgba(56,139,253,.35) !important;
  transition:all .2s !important;
}}
[data-testid="collapsedControl"]:hover {{
  background:{C2} !important;
  box-shadow:4px 0 20px rgba(56,139,253,.5) !important;
}}
[data-testid="collapsedControl"] svg {{
  color:{B5} !important;
  fill:{B5} !important;
}}

</style>
""", unsafe_allow_html=True)


# ── 사이드바 플로팅 열기 버튼 ──────────────────────────────
st.markdown(f"""
<div id="sb-open-btn"
  style="position:fixed;top:10px;left:8px;z-index:99999;
    background:{CARD};border:2px solid {B5};border-radius:10px;
    padding:8px 12px;cursor:pointer;
    font-size:15px;font-weight:700;color:{B5};
    box-shadow:0 2px 12px rgba(56,139,253,.4);
    display:flex;align-items:center;gap:6px;
    opacity:0;pointer-events:none;transition:opacity .25s"
  onclick="document.querySelector('[data-testid=collapsedControl]')?.click()">
  ☰ 메뉴
</div>

<script>
(function() {{
  function syncBtn() {{
    const collapsed = document.querySelector('[data-testid="collapsedControl"]');
    const btn = document.getElementById('sb-open-btn');
    if (!btn) return;
    if (collapsed) {{
      btn.style.opacity = '1';
      btn.style.pointerEvents = 'auto';
    }} else {{
      btn.style.opacity = '0';
      btn.style.pointerEvents = 'none';
    }}
  }}
  const obs = new MutationObserver(syncBtn);
  obs.observe(document.body, {{childList:true, subtree:true}});
  setTimeout(syncBtn, 300);
}})();
</script>
""", unsafe_allow_html=True)


# ── 세션 상태 ────────────────────────────────────────────────
if "chart_range" not in st.session_state: st.session_state.chart_range = "3M"

DATA = Path(__file__).parent.parent / "data"
PORT_FILE   = DATA / "portfolio.json"
PRICE_FILE  = DATA / "portfolio_prices.parquet"
MARKET_FILE = DATA / "market_prices.parquet"
NEWS_FILE   = DATA / "portfolio_news.json"
DISC_FILE   = DATA / "portfolio_disclosures.json"

SECTORS=["반도체","방산","증권·금융","우주항공","로봇·자동화","2차전지","바이오",
         "IT·소프트웨어","엔터·미디어","자동차","화학","철강·소재","건설","유틸리티","소비재", "미용", "에너지","기타"]
MARKETS=["KOSPI","KOSDAQ","NYSE","NASDAQ","기타"]

# ── 데이터 함수 ──────────────────────────────────────────────
def load_portfolio():
    if PORT_FILE.exists():
        with open(PORT_FILE, encoding="utf-8") as f: return json.load(f)
    return []

def save_portfolio(data):
    DATA.mkdir(exist_ok=True)
    with open(PORT_FILE,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)

@st.cache_data(ttl=600)
def load_prices():
    if PRICE_FILE.exists():
        df=pd.read_parquet(PRICE_FILE); df["date"]=pd.to_datetime(df["date"]); return df
    return pd.DataFrame()

@st.cache_data(ttl=600)
def load_market():
    if MARKET_FILE.exists():
        df=pd.read_parquet(MARKET_FILE); df["date"]=pd.to_datetime(df["date"]); return df
    return pd.DataFrame()

def load_news():
    if NEWS_FILE.exists():
        with open(NEWS_FILE,encoding="utf-8") as f: return json.load(f)
    return {"updated":"","stocks":{},"sectors":{}}

def load_disc():
    if DISC_FILE.exists():
        with open(DISC_FILE,encoding="utf-8") as f: return json.load(f)
    return {"updated":"","disclosures":{}}

def get_usdkrw(mdf):
    if mdf.empty or "indicator" not in mdf.columns: return 1380.0
    s=mdf[mdf["indicator"]=="USDKRW"].sort_values("date")
    return float(s.iloc[-1]["value"]) if not s.empty else 1380.0

def get_px(ticker, prices):
    if prices.empty: return None, None
    sub=prices[prices["ticker"]==ticker].sort_values("date")
    if sub.empty: return None, None
    return float(sub.iloc[-1]["close"]), (float(sub.iloc[-2]["close"]) if len(sub)>=2 else None)

def compute_pos(item, prices, usdkrw):
    lots=item.get("lots",[]); ticker=item.get("ticker","")
    if not lots or not ticker: return None
    qty=sum(l["qty"] for l in lots); cost=sum(l["qty"]*l["price"] for l in lots)
    avg=cost/qty if qty>0 else 0
    cur, prev=get_px(ticker,prices)
    is_usd=item.get("currency","KRW")=="USD"; fx=usdkrw if is_usd else 1
    if cur is None:
        return {"name":item["name"],"ticker":ticker,"sector":item.get("sector","기타"),
                "market":item.get("market","기타"),"currency":item.get("currency","KRW"),
                "qty":qty,"avg_cost":avg,"current":None,"value_krw":0,
                "cost_krw":cost*fx,"pnl_krw":0,"pnl_pct":0,"daily_pct":0,"daily_pnl_krw":0,
                "id":item.get("id",""),"lots":lots}
    val=cur*qty*fx; pnl=(cur-avg)*qty*fx; pnl_pct=(cur/avg-1)*100 if avg>0 else 0
    daily_pct=(cur/prev-1)*100 if prev and prev>0 else 0
    daily_pnl=(cur-prev)*qty*fx if prev else 0
    return {"name":item["name"],"ticker":ticker,"sector":item.get("sector","기타"),
            "market":item.get("market","기타"),"currency":item.get("currency","KRW"),
            "qty":qty,"avg_cost":avg,"current":cur,"value_krw":val,
            "cost_krw":cost*fx,"pnl_krw":pnl,"pnl_pct":pnl_pct,
            "daily_pct":daily_pct,"daily_pnl_krw":daily_pnl,
            "id":item.get("id",""),"lots":lots}

def compute_daily_pf(portfolio, prices, mdf):
    if prices.empty or not portfolio: return pd.DataFrame()
    all_dates=sorted(prices["date"].dropna().unique())
    fx_df=pd.DataFrame()
    if not mdf.empty and "indicator" in mdf.columns:
        fxs=mdf[mdf["indicator"]=="USDKRW"][["date","value"]].copy()
        if not fxs.empty: fx_df=fxs.rename(columns={"value":"fx"})
    rows=[]
    for d in all_dates:
        tv=0; tc=0; any_pos=False
        fx_now=1380.0
        if not fx_df.empty:
            fs=fx_df[fx_df["date"]<=d].sort_values("date")
            if not fs.empty: fx_now=float(fs.iloc[-1]["fx"])
        for it in portfolio:
            qty=0; cost=0
            for lot in it.get("lots",[]):
                if pd.Timestamp(lot["date"])<=d: qty+=lot["qty"]; cost+=lot["qty"]*lot["price"]
            if qty<=0: continue; any_pos=True
            ps=prices[(prices["ticker"]==it["ticker"])&(prices["date"]<=d)].sort_values("date")
            if ps.empty: continue
            fxv=fx_now if it.get("currency","KRW")=="USD" else 1
            tv+=qty*float(ps.iloc[-1]["close"])*fxv; tc+=cost*fxv
        if any_pos: rows.append({"date":d,"value":tv,"cost":tc,"pnl_pct":(tv/tc-1)*100 if tc>0 else 0})
    return pd.DataFrame(rows)

def filter_hist(hist_df, rng):
    if hist_df.empty: return hist_df
    cutoffs={"1W":7,"1M":30,"3M":90,"6M":180,"1Y":365,"YTD":None,"ALL":None}
    days=cutoffs.get(rng)
    if days: return hist_df[hist_df["date"]>=pd.Timestamp.now()-pd.Timedelta(days=days)]
    if rng=="YTD": return hist_df[hist_df["date"]>=pd.Timestamp(datetime.now().year,1,1)]
    return hist_df

# ── 데이터 로드 ──────────────────────────────────────────────
portfolio=load_portfolio(); prices=load_prices(); mdf=load_market()
usdkrw=get_usdkrw(mdf)
positions=[compute_pos(p,prices,usdkrw) for p in portfolio]
positions=[p for p in positions if p]
df=pd.DataFrame(positions) if positions else pd.DataFrame()
hist_df=compute_daily_pf(portfolio,prices,mdf)

# ══════════════════════════════════════════════════════════════
# 페이지 헤더 + 관리 버튼
# ══════════════════════════════════════════════════════════════
h1,h2=st.columns([4,1])
with h1:
    st.markdown(f"""
<div style="padding:20px 0 12px">
  <div style="font-size:13px;color:{SUB};font-weight:500;letter-spacing:.05em;text-transform:uppercase;margin-bottom:4px">포트폴리오</div>
  <div style="font-size:26px;font-weight:700;color:{TXT}">투자자산 현황</div>
</div>""",unsafe_allow_html=True)
with h2:
    with st.expander("⚙️ 종목 관리"):
        manage_mode=st.selectbox("작업",["신규 종목 등록","매수 기록 추가","종목 삭제"],key="mgmt",label_visibility="collapsed")

        if manage_mode=="신규 종목 등록":
            with st.form("nf",clear_on_submit=True):
                n_name=st.text_input("종목명*"); n_ticker=st.text_input("티커*",placeholder="005930.KS")
                n_currency=st.selectbox("통화",["KRW","USD"])
                c1,c2=st.columns(2)
                with c1: n_sector=st.selectbox("섹터",SECTORS)
                with c2: n_market=st.selectbox("시장",MARKETS)
                c3,c4,c5=st.columns(3)
                with c3: n_date=st.date_input("첫 매수일",date.today())
                with c4: n_qty=st.number_input("수량",min_value=0.0,step=1.0)
                with c5: n_price=st.number_input("매수가",min_value=0.0,step=100.0)
                if st.form_submit_button("등록",type="primary"):
                    if n_name and n_ticker:
                        new={"id":str(uuid.uuid4())[:8],"name":n_name,"ticker":n_ticker,
                             "sector":n_sector,"market":n_market,"currency":n_currency,"lots":[]}
                        if n_qty>0 and n_price>0: new["lots"].append({"date":str(n_date),"qty":n_qty,"price":n_price})
                        portfolio.append(new); save_portfolio(portfolio)
                        st.cache_data.clear(); st.success("등록!"); st.rerun()

        elif manage_mode=="매수 기록 추가" and portfolio:
            with st.form("af",clear_on_submit=True):
                opts={f"{p['name']}":p["id"] for p in portfolio}
                sel=st.selectbox("종목",list(opts.keys()))
                c1,c2,c3=st.columns(3)
                with c1: a_date=st.date_input("매수일",date.today())
                with c2: a_qty=st.number_input("수량",min_value=0.0,step=1.0)
                with c3: a_price=st.number_input("매수가",min_value=0.0,step=100.0)
                if st.form_submit_button("추가",type="primary") and a_qty>0 and a_price>0:
                    tid=opts[sel]
                    for p in portfolio:
                        if p["id"]==tid: p.setdefault("lots",[]).append({"date":str(a_date),"qty":a_qty,"price":a_price}); break
                    save_portfolio(portfolio); st.cache_data.clear(); st.success("추가!"); st.rerun()

        elif manage_mode=="종목 삭제" and portfolio:
            to_del=st.selectbox("삭제할 종목",["선택..."]+[p["name"] for p in portfolio],key="del_sel")
            if to_del!="선택..." and st.button("삭제",key="del_btn"):
                portfolio=[p for p in portfolio if p["name"]!=to_del]
                save_portfolio(portfolio); st.cache_data.clear(); st.rerun()

# ══════════════════════════════════════════════════════════════
# 보유 종목 티커 바
# ══════════════════════════════════════════════════════════════
if positions:
    ticker_items=""
    for i,pos in enumerate(sorted(positions,key=lambda x:x["value_krw"],reverse=True)[:8]):
        clr=HOLD_COLORS[i%len(HOLD_COLORS)]
        pct=pos["daily_pct"]; pclr=UP if pct>=0 else DN; sign="+" if pct>=0 else ""
        val_str=f"{pos['value_krw']/1e8:.2f}억" if pos["value_krw"]>=1e8 else f"{pos['value_krw']/1e4:.0f}만"
        ticker_items+=f"""
<div style="display:flex;flex-direction:column;gap:3px;padding:10px 16px;
  background:{CARD};border:1px solid {BORD};border-radius:8px;min-width:160px;flex-shrink:0">
  <div style="display:flex;align-items:center;gap:6px">
    <span style="width:8px;height:8px;border-radius:50%;background:{clr};flex-shrink:0"></span>
    <span style="font-size:11px;font-weight:600;color:{TXT};overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:120px">{pos['name']}</span>
  </div>
  <div style="display:flex;align-items:baseline;justify-content:space-between">
    <span style="font-size:13px;font-weight:700;color:{TXT};font-family:'JetBrains Mono',monospace">{val_str}</span>
    <span style="font-size:11px;font-weight:600;color:{pclr};font-family:'JetBrains Mono',monospace">{sign}{pct:.2f}%</span>
  </div>
</div>"""
    st.markdown(f"""
<div style="display:flex;gap:8px;overflow-x:auto;padding:4px 0 12px;scrollbar-width:thin;
  scrollbar-color:{BORD} transparent">
  {ticker_items}
</div>""",unsafe_allow_html=True)

# 데이터 없을 때
if df.empty or not positions:
    st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;
  padding:60px;text-align:center;margin-top:20px">
  <div style="font-size:40px;margin-bottom:16px">📊</div>
  <div style="font-size:18px;font-weight:600;color:{TXT};margin-bottom:8px">보유 종목 없음</div>
  <div style="font-size:13px;color:{SUB}">우측 상단 ⚙️ 종목 관리에서 종목을 추가해주세요</div>
</div>""",unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════
# 메인 레이아웃 — 좌(자산) : 우(차트) = 4:6
# ══════════════════════════════════════════════════════════════
df_p=df[df["current"].notna()]
tv=df_p["value_krw"].sum(); tc=df_p["cost_krw"].sum()
tp=df_p["pnl_krw"].sum(); tpct=(tp/tc*100) if tc>0 else 0
td=df_p["daily_pnl_krw"].sum(); dpct=(td/(tv-td)*100) if (tv-td)>0 else 0
tv_usd=tv/usdkrw

left,right=st.columns([4,6],gap="medium")

# ── 왼쪽 패널 ─────────────────────────────────────────────────
with left:
    # 총 평가금액 카드
    pnl_bg="rgba(46,204,113,.12)" if td>=0 else "rgba(231,76,60,.12)"
    pnl_clr=UP if td>=0 else DN
    sign="▲" if td>=0 else "▼"
    st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;padding:24px;margin-bottom:10px">
  <div style="font-size:12px;color:{SUB};font-weight:500;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px">총 평가금액</div>
  <div style="font-size:36px;font-weight:800;color:{TXT};font-family:'JetBrains Mono',monospace;line-height:1;margin-bottom:12px">
    {tv:,.0f}
    <span style="font-size:14px;font-weight:500;color:{SUB}">원</span>
  </div>
  <div style="display:flex;gap:8px;align-items:center">
    <span style="background:{pnl_bg};color:{pnl_clr};padding:4px 10px;border-radius:20px;
      font-size:12px;font-weight:600;font-family:'JetBrains Mono',monospace">
      {sign} 전일 {td:+,.0f}원 ({dpct:+.2f}%)
    </span>
  </div>
  <div style="margin-top:10px;font-size:11px;color:{SUB};font-family:'JetBrains Mono',monospace">
    ≈ ${tv_usd:,.0f} · 환율 {usdkrw:,.0f}
  </div>
</div>""",unsafe_allow_html=True)

    # 자산 구성 레인보우 바
    df_sorted_val=df_p.sort_values("value_krw",ascending=False)
    segments=""
    for i,((_,row),clr) in enumerate(zip(df_sorted_val.iterrows(), HOLD_COLORS)):
        w=row["value_krw"]/tv*100
        if w<0.5: continue
        segments+=f'<div style="width:{w:.2f}%;background:{clr};height:100%;border-radius:{"4px 0 0 4px" if i==0 else ""}"></div>'

    st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;padding:20px;margin-bottom:10px">
  <div style="font-size:11px;color:{SUB};font-weight:500;text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px">자산 구성</div>
  <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;background:{C2};margin-bottom:14px;gap:1px">
    {segments}
  </div>
  <div style="display:flex;flex-direction:column;gap:0">""",unsafe_allow_html=True)

    holding_rows=""
    for i,((_,row),clr) in enumerate(zip(df_sorted_val.iterrows(), HOLD_COLORS)):
        w=row["value_krw"]/tv*100
        pclr=UP if row["pnl_pct"]>=0 else DN
        sign_p="+" if row["pnl_pct"]>=0 else ""
        holding_rows+=f"""
<div style="display:flex;align-items:center;justify-content:space-between;
  padding:7px 0;border-bottom:1px solid {BORD};gap:8px" class="holding-row">
  <div style="display:flex;align-items:center;gap:8px;flex:1;min-width:0">
    <span style="width:8px;height:8px;border-radius:50%;background:{clr};flex-shrink:0"></span>
    <span style="font-size:12px;color:{TXT};font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{row['name']}</span>
  </div>
  <div style="display:flex;align-items:center;gap:12px;flex-shrink:0">
    <span style="font-size:11px;color:{SUB};min-width:36px;text-align:right">{w:.1f}%</span>
    <span style="font-size:12px;font-weight:600;color:{TXT};font-family:'JetBrains Mono',monospace;min-width:70px;text-align:right">{row['value_krw']:,.0f}</span>
    <span style="font-size:11px;font-weight:600;color:{pclr};font-family:'JetBrains Mono',monospace;min-width:56px;text-align:right">{sign_p}{row['pnl_pct']:.2f}%</span>
  </div>
</div>"""

    st.markdown(f"""
  <div style="display:flex;align-items:center;padding:4px 0 8px;gap:8px">
    <span style="font-size:10px;color:{MUT};flex:1">종목</span>
    <span style="font-size:10px;color:{MUT};min-width:36px;text-align:right">비중</span>
    <span style="font-size:10px;color:{MUT};min-width:70px;text-align:right">평가금액</span>
    <span style="font-size:10px;color:{MUT};min-width:56px;text-align:right">수익률</span>
  </div>
  {holding_rows}
</div></div>""",unsafe_allow_html=True)

# ── 오른쪽 패널 ───────────────────────────────────────────────
with right:
    # 기간 선택 버튼
    rng_col1, rng_col2 = st.columns([1,5])
    with rng_col2:
        rng=st.radio("기간",["1W","1M","3M","6M","1Y","YTD","ALL"],
                     horizontal=True,label_visibility="collapsed",key="rng")
        if rng != st.session_state.chart_range:
            st.session_state.chart_range = rng

    # 차트
    filtered=filter_hist(hist_df, st.session_state.chart_range)

    if not filtered.empty:
        # USD/KRW 시리즈 가져오기
        fx_series=pd.DataFrame()
        if not mdf.empty and "indicator" in mdf.columns:
            fxs=mdf[mdf["indicator"]=="USDKRW"][["date","value"]].copy()
            if not fxs.empty:
                fx_series=fxs[fxs["date"]>=filtered.iloc[0]["date"]].sort_values("date")

        fig=make_subplots(specs=[[{"secondary_y":True}]])

        # 포트폴리오 가치 - 영역 차트
        fig.add_trace(go.Scatter(
            x=filtered["date"],y=filtered["value"],name="포트폴리오",
            line=dict(color=ACC,width=2),
            fill="tonexty",
            fillcolor="rgba(74,130,228,.12)",
            hovertemplate="<b>포트폴리오</b> %{y:,.0f}원<extra></extra>"),secondary_y=False)

        # 0선 (fill base)
        fig.add_trace(go.Scatter(
            x=filtered["date"],y=[filtered["value"].min()*0.998]*len(filtered),
            line=dict(width=0),showlegend=False,hoverinfo="skip"),secondary_y=False)

        # 매입원가 점선
        if not filtered.empty:
            cost_last=filtered.iloc[-1]["cost"] if "cost" in filtered.columns else 0
            if cost_last>0:
                fig.add_hline(y=cost_last,line_dash="dash",line_color=GOLD,line_width=1,
                    annotation_text=f"매입 {cost_last/1e8:.2f}억",
                    annotation_font_color=GOLD,annotation_font_size=9)

        # 환율 (보조축)
        if not fx_series.empty:
            fig.add_trace(go.Scatter(
                x=fx_series["date"],y=fx_series["value"],name="환율",
                line=dict(color="#9B59B6",width=1.5,dash="dot"),
                hovertemplate="<b>USD/KRW</b> %{y:,.0f}<extra></extra>"),secondary_y=True)

        # 레이아웃
        fig.update_layout(
            paper_bgcolor=CARD, plot_bgcolor=CARD,
            height=340, margin=dict(l=8,r=8,t=8,b=8),
            legend=dict(orientation="h",y=1.05,x=0,font=dict(size=10,color=SUB),bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",
            hoverlabel=dict(bgcolor=C3,bordercolor=BORD,font=dict(family="JetBrains Mono",size=11,color=TXT)),
            xaxis=dict(showgrid=False,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT),tickcolor=BORD),
            yaxis=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT),
                       tickformat=",.0f",side="right"),
            yaxis2=dict(showgrid=False,zeroline=False,showline=False,tickfont=dict(size=9,color="#9B59B6"),
                        side="left"),
        )
        fig.update_yaxes(secondary_y=False,ticksuffix="원")
        st.plotly_chart(fig,use_container_width=True)

        # 차트 하단 메트릭 스트립
        if not filtered.empty:
            max_v=filtered["value"].max(); min_v=filtered["value"].min()
            first_v=filtered.iloc[0]["value"]; last_v=filtered.iloc[-1]["value"]
            max_d=filtered.loc[filtered["value"].idxmax(),"date"].strftime("%m/%d")
            min_d=filtered.loc[filtered["value"].idxmin(),"date"].strftime("%m/%d")
            mdd_pct=(min_v/max_v-1)*100
            chg_pct=(last_v/first_v-1)*100
            metrics=[
                ("최고점",f"{max_v/1e8:.3f}억원",max_d,ACC),
                ("최저점",f"{min_v/1e8:.3f}억원",min_d,DN),
                ("기간 수익",f"{chg_pct:+.2f}%",f"기간내",UP if chg_pct>=0 else DN),
                ("MDD",f"{mdd_pct:.2f}%","최대낙폭",DN),
                ("현재/최고",f"{last_v/max_v*100:.2f}%","",SUB),
            ]
            m_cols=st.columns(5)
            for col,(lbl,val,sub_,clr) in zip(m_cols,metrics):
                with col:
                    st.markdown(f"""
<div style="background:{C2};border:1px solid {BORD};border-radius:8px;padding:12px 14px">
  <div style="font-size:10px;color:{SUB};font-weight:500;margin-bottom:4px">{lbl}</div>
  <div style="font-size:15px;font-weight:700;color:{clr};font-family:'JetBrains Mono',monospace;line-height:1.2">{val}</div>
  <div style="font-size:9px;color:{MUT};margin-top:3px">{sub_}</div>
</div>""",unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;
  padding:40px;text-align:center;height:340px;display:flex;align-items:center;justify-content:center">
  <div style="color:{SUB};font-size:13px">Actions 실행 후 차트가 표시됩니다</div>
</div>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 하단 KPI 스트립
# ══════════════════════════════════════════════════════════════
st.markdown(f'<div style="height:4px"></div>',unsafe_allow_html=True)

kpi_strip_items=[
    ("누적 평가손익",f"{tp:+,.0f}원",f"{tpct:+.2f}%",UP if tp>=0 else DN),
    ("매입 원가",f"{tc:,.0f}원","투자 원금",SUB),
    ("전일 평가손익",f"{td:+,.0f}원",f"{dpct:+.2f}%",UP if td>=0 else DN),
    ("USD/KRW",f"{usdkrw:,.0f}","현재 환율",SUB),
    ("USD 환산",f"${tv_usd:,.0f}","포트폴리오",SUB),
]
ks_cols=st.columns(5)
for col,(lbl,val,sub_,clr) in zip(ks_cols,kpi_strip_items):
    with col:
        st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;padding:16px 18px">
  <div style="font-size:10px;color:{SUB};font-weight:500;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">{lbl}</div>
  <div style="font-size:20px;font-weight:800;color:{TXT};font-family:'JetBrains Mono',monospace;line-height:1;margin-bottom:4px">{val}</div>
  <div style="font-size:11px;color:{clr};font-weight:600">{sub_}</div>
</div>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 탭: 상세 테이블 / 뉴스 / 공시
# ══════════════════════════════════════════════════════════════
st.markdown(f'<div style="height:8px"></div>',unsafe_allow_html=True)
t1, t2, t3, t4 = st.tabs(["📋 상세 테이블", "📰 뉴스", "📑 공시", "📊 리스크"])


with t1:
    df_sorted=df.sort_values("value_krw",ascending=False)
    def fmt_row(r,i):
        clr=HOLD_COLORS[i%len(HOLD_COLORS)]
        pclr=UP if r["pnl_pct"]>=0 else DN; dclr=UP if r["daily_pct"]>=0 else DN
        cv=f"{r['current']:,.2f}" if r["current"] else "—"
        wt=(r["value_krw"]/tv*100) if tv>0 else 0
        sp="▲" if r["pnl_pct"]>=0 else "▼"; sd="▲" if r["daily_pct"]>=0 else "▼"
        return f"""<tr style="border-bottom:1px solid {BORD}">
<td style="padding:.7rem 1rem">
  <div style="display:flex;align-items:center;gap:8px">
    <span style="width:8px;height:8px;border-radius:50%;background:{clr};flex-shrink:0"></span>
    <div>
      <div style="font-size:12px;font-weight:600;color:{TXT}">{r['name']}</div>
      <div style="font-size:10px;color:{SUB};font-family:'JetBrains Mono',monospace">{r['ticker']}</div>
    </div>
  </div>
</td>
<td style="padding:.7rem 1rem;text-align:right;font-family:'JetBrains Mono',monospace;font-size:12px;color:{TXT}">{r['qty']:,.0f}</td>
<td style="padding:.7rem 1rem;text-align:right;font-family:'JetBrains Mono',monospace;font-size:12px;color:{TXT}">{r['avg_cost']:,.2f}</td>
<td style="padding:.7rem 1rem;text-align:right">
  <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:{TXT}">{cv}</div>
  <div style="font-size:10px;color:{dclr};font-weight:600">{sd}{abs(r['daily_pct']):.2f}%</div>
</td>
<td style="padding:.7rem 1rem;text-align:right">
  <div style="font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;color:{TXT}">{r['value_krw']:,.0f}</div>
  <div style="font-size:10px;color:{SUB}">{wt:.1f}%</div>
</td>
<td style="padding:.7rem 1rem;text-align:right">
  <div style="font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;color:{pclr}">{r['pnl_krw']:+,.0f}</div>
  <div style="font-size:10px;color:{pclr}">{sp}{abs(r['pnl_pct']):.2f}%</div>
</td>
</tr>"""
    rows_html="".join(fmt_row(r,i) for i,(_,r) in enumerate(df_sorted.iterrows()))
    TH=f"padding:.6rem 1rem;text-align:left;font-size:10px;color:{MUT};font-weight:500;border-bottom:1px solid {BORD};text-transform:uppercase;letter-spacing:.04em"
    st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;overflow:hidden;margin-top:8px">
<table style="width:100%;border-collapse:collapse">
<thead><tr style="background:{C2}">
  <th style="{TH}">종목</th>
  <th style="{TH};text-align:right">수량</th>
  <th style="{TH};text-align:right">평균단가</th>
  <th style="{TH};text-align:right">현재가 · 일간</th>
  <th style="{TH};text-align:right">평가금액 (비중)</th>
  <th style="{TH};text-align:right">평가손익</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table></div>""",unsafe_allow_html=True)

# 뉴스 + 공시 탭
def news_card_new(news, accent=ACC):
    title=news.get("title",""); url=news.get("url","#")
    body=news.get("ai_summary") or news.get("summary","")
    source=(news.get("source") or "")[:25]; pub=news.get("pub_date","")
    score=news.get("score"); tags=news.get("tags",[])
    try:
        ds=datetime.fromisoformat(pub.replace("Z","+00:00").split("+")[0]).strftime("%m-%d")
    except: ds=pub[:5] if pub else ""
    badge=""
    if score is not None:
        if score>=7:   bf,bb="호재",f"rgba(46,204,113,.2)"
        elif score<=3: bf,bb="악재",f"rgba(231,76,60,.2)"
        else:           bf,bb="중립",f"rgba(74,130,228,.15)"
        bclr=UP if score>=7 else (DN if score<=3 else ACC)
        badge=f'<span style="background:{bb};color:{bclr};padding:2px 7px;border-radius:12px;font-size:9px;font-weight:600;font-family:JetBrains Mono">{bf} {score}</span>'
    tag_html=("".join(f'<span style="background:{C3};color:{SUB};padding:1px 6px;border-radius:4px;font-size:9px;font-family:JetBrains Mono">#{t}</span>' for t in tags[:2])) if tags else ""
    return f"""<a href="{url}" target="_blank" style="text-decoration:none">
<div style="background:{CARD};border:1px solid {BORD};border-left:3px solid {accent};border-radius:8px;padding:14px;height:190px;display:flex;flex-direction:column;transition:background .15s">
  <div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:8px">
    <div style="font-size:12px;font-weight:600;color:{TXT};line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;flex:1">{title}</div>
    {badge}
  </div>
  <div style="font-size:11px;color:{SUB};line-height:1.5;flex:1;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical">{body}</div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;padding-top:8px;border-top:1px solid {BORD}">
    <div style="display:flex;gap:4px">{tag_html}</div>
    <div style="display:flex;gap:8px;font-size:9px;color:{MUT};font-family:JetBrains Mono">
      <span>{source}</span><span>{ds}</span>
    </div>
  </div>
</div></a>"""

def disc_card_new(d):
    title=d.get("title",""); url=d.get("url","#"); filer=d.get("filer","")
    dt=d.get("date","")
    if len(dt)==8: dt=f"{dt[4:6]}-{dt[6:8]}"
    return f"""<a href="{url}" target="_blank" style="text-decoration:none">
<div style="background:{CARD};border:1px solid {BORD};border-left:3px solid #9B59B6;border-radius:8px;padding:14px;min-height:90px;display:flex;flex-direction:column;justify-content:space-between">
  <div style="font-size:12px;font-weight:600;color:{TXT};line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical">{title}</div>
  <div style="display:flex;justify-content:space-between;margin-top:10px;padding-top:8px;border-top:1px solid {BORD};font-size:9px;color:{MUT};font-family:JetBrains Mono">
    <span>{filer}</span><span>{dt}</span>
  </div>
</div></a>"""

with t2:
    news_data=load_news(); stocks=news_data.get("stocks",{})
    ordered=[(r["name"],stocks[r["name"]]) for _,r in df_sorted.iterrows() if r["name"] in stocks and stocks[r["name"]]]
    if not ordered: st.markdown(f'<div style="color:{SUB};font-size:13px;padding:20px">종목 뉴스 미수집. 내일 KST 07:00 자동수집됩니다.</div>',unsafe_allow_html=True)
    else:
        for i,(name,articles) in enumerate(ordered):
            clr=HOLD_COLORS[i%len(HOLD_COLORS)]
            scores=[a.get("score") for a in articles if a.get("score") is not None]
            avg_s=sum(scores)/len(scores) if scores else None
            tone=""
            if avg_s is not None:
                tc2=UP if avg_s>=6.5 else (DN if avg_s<=3.5 else SUB)
                tone=f'<span style="background:rgba(74,130,228,.15);color:{tc2};padding:2px 8px;border-radius:12px;font-size:9px;font-weight:600;margin-left:8px">평균 {avg_s:.1f}</span>'
            st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;padding:10px 0 8px">
  <span style="width:8px;height:8px;border-radius:50%;background:{clr}"></span>
  <span style="font-size:13px;font-weight:700;color:{TXT}">{name}</span>{tone}
</div>""",unsafe_allow_html=True)
            cols=st.columns(3)
            for col,news in zip(cols,articles[:3]):
                with col: st.markdown(news_card_new(news,accent=clr),unsafe_allow_html=True)

with t3:
    disc_data=load_disc(); discs=disc_data.get("disclosures",{})
    if not discs: st.markdown(f'<div style="color:{SUB};font-size:13px;padding:20px">DART_API_KEY 등록 후 공시가 자동수집됩니다.</div>',unsafe_allow_html=True)
    else:
        ordered_d=[(r["name"],discs[r["name"]]) for _,r in df_sorted.iterrows() if r["name"] in discs and discs[r["name"]]]
        if not ordered_d: st.markdown(f'<div style="color:{SUB};font-size:13px;padding:20px">최근 14일 공시 없음.</div>',unsafe_allow_html=True)
        else:
            for i,(name,items_) in enumerate(ordered_d):
                clr=HOLD_COLORS[i%len(HOLD_COLORS)]
                st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;padding:10px 0 8px">
  <span style="width:8px;height:8px;border-radius:50%;background:{clr}"></span>
  <span style="font-size:13px;font-weight:700;color:{TXT}">{name}</span>
  <span style="font-size:10px;color:{MUT}">{len(items_)}건</span>
</div>""",unsafe_allow_html=True)
                cols=st.columns(3)
                for j,d_ in enumerate(items_[:6]):
                    with cols[j%3]: st.markdown(disc_card_new(d_),unsafe_allow_html=True)

# 푸터
st.markdown(f"""
<div style="margin-top:2rem;padding:10px 14px;background:{CARD};border:1px solid {BORD};
  border-radius:8px;font-size:10px;color:{MUT};font-family:'JetBrains Mono',monospace">
  가격 최종: {prices["date"].max().strftime("%Y-%m-%d") if not prices.empty else "—"}
  · USD/KRW: {usdkrw:,.0f}  · 매일 KST 07:00 자동수집
</div>""",unsafe_allow_html=True)

with t4:
    if prices.empty or len(positions) < 2:
        st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;
  padding:40px;text-align:center">
  <div style="font-size:14px;color:{SUB}">
    종목이 2개 이상 등록되고 가격 데이터가 수집된 후 확인 가능합니다
  </div>
</div>""", unsafe_allow_html=True)
    else:
        # ── 헬퍼 함수 ─────────────────────────────────────────
        def get_ret(ticker, days=None):
            sub = prices[prices["ticker"]==ticker].sort_values("date")
            if days: sub = sub.tail(days+1)
            return sub["close"].pct_change().dropna()

        def calc_beta(ticker, is_usd, days=90):
            stock_ret = get_ret(ticker, days)
            if len(stock_ret) < 20: return None
            bench_ind = "SPX" if is_usd else "KOSPI"
            if mdf.empty or "indicator" not in mdf.columns: return None
            bench = mdf[mdf["indicator"]==bench_ind].sort_values("date")
            if bench.empty: return None
            bench_ret = bench.set_index("date")["value"].pct_change().dropna()
            common = stock_ret.index.intersection(bench_ret.index)
            if len(common) < 20: return None
            s = stock_ret[common].values; b = bench_ret[common].values
            var_b = np.var(b)
            if var_b == 0: return None
            return round(float(np.cov(s, b)[0,1] / var_b), 2)

        def calc_vol(ticker, days=60):
            ret = get_ret(ticker, days)
            if len(ret) < 10: return None
            return round(float(ret.std() * np.sqrt(252) * 100), 2)

        def calc_mdd(ticker):
            sub = prices[prices["ticker"]==ticker].sort_values("date")["close"]
            if len(sub) < 5: return None
            dd = (sub - sub.cummax()) / sub.cummax() * 100
            return round(float(dd.min()), 2)

        def calc_sharpe(ticker, rf=3.5, days=90):
            ret = get_ret(ticker, days)
            if len(ret) < 20: return None
            ann = float(ret.mean() * 252 * 100)
            vol = float(ret.std() * np.sqrt(252) * 100)
            return round((ann - rf) / vol, 2) if vol > 0 else None

        # ── 리스크 지표 테이블 ────────────────────────────────
        st.markdown(f"""
<div style="font-size:14px;font-weight:600;color:{SUB};
  margin:1rem 0 10px;font-family:'Inter',sans-serif">리스크 지표 요약</div>
""", unsafe_allow_html=True)

        def badge(v, thresholds, fmt, reverse=False):
            if v is None: return f'<span style="color:{MUT}">—</span>'
            lo, hi = thresholds
            if reverse:
                clr = UP if v < lo else (GOLD if v < hi else DN)
            else:
                clr = DN if v < lo else (GOLD if v < hi else UP)
            return f'<span style="color:{clr};font-weight:700;font-family:JetBrains Mono,monospace">{fmt.format(v)}</span>'

        risk_rows = ""
        for i, pos in enumerate(sorted(positions, key=lambda x:x["value_krw"], reverse=True)):
            clr = HOLD_COLORS[i % len(HOLD_COLORS)]
            t = pos["ticker"]; is_usd = pos["currency"] == "USD"
            beta = calc_beta(t, is_usd)
            vol  = calc_vol(t)
            mdd  = calc_mdd(t)
            sh   = calc_sharpe(t)
            b_html  = badge(beta, (0.8, 1.3), "{:.2f}", reverse=False) if beta else f'<span style="color:{MUT}">—</span>'
            v_html  = badge(vol,  (20, 35), "{:.1f}%", reverse=True)   if vol  else f'<span style="color:{MUT}">—</span>'
            mdd_html= f'<span style="color:{DN};font-weight:700;font-family:JetBrains Mono,monospace">{mdd:.1f}%</span>' if mdd else f'<span style="color:{MUT}">—</span>'
            sh_html = badge(sh, (0, 1), "{:.2f}")                       if sh   else f'<span style="color:{MUT}">—</span>'
            risk_rows += f"""<tr style="border-bottom:1px solid {BORD}">
  <td style="padding:.7rem 1rem">
    <div style="display:flex;align-items:center;gap:8px">
      <span style="width:8px;height:8px;border-radius:50%;background:{clr};flex-shrink:0"></span>
      <div>
        <div style="font-size:12px;font-weight:600;color:{TXT}">{pos['name']}</div>
        <div style="font-size:9px;color:{MUT};font-family:'JetBrains Mono',monospace">{t}</div>
      </div>
    </div>
  </td>
  <td style="padding:.7rem 1rem;text-align:center">{b_html}</td>
  <td style="padding:.7rem 1rem;text-align:center">{v_html}</td>
  <td style="padding:.7rem 1rem;text-align:center">{mdd_html}</td>
  <td style="padding:.7rem 1rem;text-align:center">{sh_html}</td>
</tr>"""

        TH_S = f"padding:.6rem 1rem;font-size:10px;color:{MUT};font-weight:500;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid {BORD};text-align:center"
        st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;overflow:hidden">
  <table style="width:100%;border-collapse:collapse">
    <thead><tr style="background:{C2}">
      <th style="{TH_S};text-align:left">종목</th>
      <th style="{TH_S}">베타<br><span style="font-size:8px;color:{MUT};font-weight:400">90일·시장대비</span></th>
      <th style="{TH_S}">변동성<br><span style="font-size:8px;color:{MUT};font-weight:400">60일·연환산</span></th>
      <th style="{TH_S}">MDD<br><span style="font-size:8px;color:{MUT};font-weight:400">최대낙폭</span></th>
      <th style="{TH_S}">샤프비율<br><span style="font-size:8px;color:{MUT};font-weight:400">90일·RF 3.5%</span></th>
    </tr></thead>
    <tbody>{risk_rows}</tbody>
  </table>
</div>""", unsafe_allow_html=True)

        st.markdown(f"""
<div style="background:{C2};border:1px solid {BORD};border-radius:8px;
  padding:10px 14px;font-size:10px;color:{SUB};margin-top:8px;display:flex;gap:16px;flex-wrap:wrap">
  <span>📊 <b style="color:{TXT}">베타</b> &lt;0.8 방어 · 0.8~1.3 중립 · &gt;1.3 공격</span>
  <span>📉 <b style="color:{TXT}">변동성</b> &lt;20% 안정 · 20~35% 보통 · &gt;35% 고위험</span>
  <span>⭐ <b style="color:{TXT}">샤프</b> &lt;0 손실 · 0~1 보통 · &gt;1 우수</span>
</div>""", unsafe_allow_html=True)

        st.markdown(f'<div style="height:1.5rem"></div>', unsafe_allow_html=True)

        # ── 상관관계 매트릭스 ────────────────────────────────
        st.markdown(f"""
<div style="font-size:14px;font-weight:600;color:{SUB};
  margin-bottom:10px;font-family:'Inter',sans-serif">상관관계 매트릭스</div>
""", unsafe_allow_html=True)

        all_tickers = [p["ticker"] for p in positions]
        names_map   = {p["ticker"]: p["name"] for p in positions}
        pivot = prices[prices["ticker"].isin(all_tickers)]\
            .pivot_table(index="date", columns="ticker", values="close")
        ret_mat = pivot.pct_change().dropna()

        if len(ret_mat.columns) >= 2 and len(ret_mat) >= 10:
            corr = ret_mat.corr()
            corr.columns = [names_map.get(t, t) for t in corr.columns]
            corr.index   = [names_map.get(t, t) for t in corr.index]

            fig_c = go.Figure(go.Heatmap(
                z=corr.values, x=list(corr.columns), y=list(corr.index),
                colorscale=[[0,"#E74C3C"],[0.5,CARD],[1,"#2ECC71"]],
                zmin=-1, zmax=1,
                text=[[f"{v:.2f}" for v in row] for row in corr.values],
                texttemplate="%{text}",
                textfont={"size":11,"color":TXT,"family":"JetBrains Mono"},
                hovertemplate="<b>%{y} × %{x}</b><br>%{z:.3f}<extra></extra>",
                colorbar=dict(thickness=10,tickfont=dict(color=MUT,size=9),
                              bgcolor="rgba(0,0,0,0)")
            ))
            fig_c.update_layout(
                paper_bgcolor=CARD, plot_bgcolor=CARD,
                height=max(280, len(corr)*60),
                margin=dict(l=8,r=60,t=8,b=8),
                font=dict(family="JetBrains Mono",size=10,color=MUT),
                xaxis=dict(tickfont=dict(size=10,color=TXT),tickangle=-30),
                yaxis=dict(tickfont=dict(size=10,color=TXT))
            )
            st.plotly_chart(fig_c, use_container_width=True)

            # 최고/최저 상관 인사이트
            arr = corr.values.copy(); np.fill_diagonal(arr, np.nan)
            if not np.all(np.isnan(arr)):
                hi_i = np.unravel_index(np.nanargmax(arr), arr.shape)
                lo_i = np.unravel_index(np.nanargmin(arr), arr.shape)
                cols_list = list(corr.columns)
                st.markdown(f"""
<div style="background:{C2};border:1px solid {BORD};border-radius:8px;
  padding:10px 14px;font-size:11px;color:{SUB};margin-top:8px;display:flex;gap:16px;flex-wrap:wrap">
  <span>🔗 <b style="color:{TXT}">최고 상관:</b> {cols_list[hi_i[0]]} × {cols_list[hi_i[1]]}
    <span style="color:{DN};font-weight:700"> {arr[hi_i]:.2f}</span>
    → 같은 방향으로 움직임
  </span>
  <span>🔀 <b style="color:{TXT}">최저 상관:</b> {cols_list[lo_i[0]]} × {cols_list[lo_i[1]]}
    <span style="color:{UP};font-weight:700"> {arr[lo_i]:.2f}</span>
    → 분산 효과 우수
  </span>
</div>""", unsafe_allow_html=True)

        st.markdown(f'<div style="height:1.5rem"></div>', unsafe_allow_html=True)

        # ── 롤링 변동성 추이 ─────────────────────────────────
        st.markdown(f"""
<div style="font-size:14px;font-weight:600;color:{SUB};
  margin-bottom:10px;font-family:'Inter',sans-serif">롤링 변동성 추이 (30일 연환산)</div>
""", unsafe_allow_html=True)

        fig_v = go.Figure()
        for i, pos in enumerate(positions):
            sub = prices[prices["ticker"]==pos["ticker"]].sort_values("date").copy()
            if len(sub) < 35: continue
            sub["ret"] = sub["close"].pct_change()
            sub["vol"] = sub["ret"].rolling(30).std() * np.sqrt(252) * 100
            sub = sub.dropna(subset=["vol"])
            if sub.empty: continue
            fig_v.add_trace(go.Scatter(
                x=sub["date"], y=sub["vol"], name=pos["name"],
                line=dict(color=HOLD_COLORS[i%len(HOLD_COLORS)], width=2),
                hovertemplate=f"<b>{pos['name']}</b> %{{y:.1f}}%<extra></extra>"))

        fig_v.add_hline(y=20, line_dash="dash", line_color=GOLD, line_width=1,
            annotation_text="20% 경계", annotation_font_color=GOLD, annotation_font_size=9)
        fig_v.update_layout(
            paper_bgcolor=CARD, plot_bgcolor=CARD, height=260,
            margin=dict(l=8,r=8,t=8,b=8),
            legend=dict(orientation="h",y=1.1,x=0,font=dict(size=10,color=SUB),bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",
            xaxis=dict(showgrid=False, tickfont=dict(size=9,color=MUT)),
            yaxis=dict(showgrid=True, gridcolor=G, ticksuffix="%", tickfont=dict(size=9,color=MUT)))
        st.plotly_chart(fig_v, use_container_width=True)
