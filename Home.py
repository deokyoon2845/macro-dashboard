"""
Deokyoon's Monitoring — Home
"""
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys, base64

st.set_page_config(page_title="Deokyoon's Monitoring", page_icon="◈",
                   layout="wide", initial_sidebar_state="expanded")

# ── 색상 팔레트 (중복 정의 — pages와 독립적) ─────────────────
BG="#F5F0E5"; CARD="#FFFFFF"; C2="#FAF6EC"
BORD="#E5DDD0"; TXT="#2A2620"; SUB="#5A5246"; MUT="#8C7F6E"
PUR_HI="#BAE6FD"; PUR_DK="#0369A1"
B3="#60A5FA"; B4="#3B82F6"; B5="#2563EB"; B6="#1D4ED8"; B8="#1E3A8A"
UP=B5; DN=B8

st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
@font-face{{font-family:'MaruBuri';src:url('https://cdn.jsdelivr.net/gh/wkdtjsgur100/maruburifonts@1.0/static/MaruBuri/MaruBuri-Regular.woff2') format('woff2')}}
html,body,[class*="css"]{{background-color:{BG}!important;
  background-image:radial-gradient(rgba(139,119,98,.042) 1px,transparent 1px),radial-gradient(rgba(139,119,98,.022) 1px,transparent 1px)!important;
  background-size:32px 32px,16px 16px!important;background-position:0 0,8px 8px!important;
  color:{TXT}!important;font-family:'MaruBuri','Gowun Batang',serif!important;
  letter-spacing:.015em!important;line-height:1.3!important}}
.block-container{{padding:1.5rem 2rem 3rem!important;max-width:100%!important;background:transparent!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important;
  background-image:radial-gradient(rgba(139,119,98,.042) 1px,transparent 1px),radial-gradient(rgba(139,119,98,.022) 1px,transparent 1px)!important;
  background-size:32px 32px,16px 16px!important;background-position:0 0,8px 8px!important}}
#MainMenu,footer,header{{visibility:hidden}}
p,span,div,label{{color:{TXT}!important}}
/* 사이드바 커스텀 */
[data-testid="stSidebar"]{{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
[data-testid="stSidebarNavItems"] a{{font-family:'MaruBuri',serif!important;font-size:14px!important;color:{TXT}!important}}
[data-testid="stSidebarNavItems"] a:hover{{color:{B5}!important}}
</style>
""", unsafe_allow_html=True)

# ── 데이터 로드 ──────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"

@st.cache_data(ttl=3600)
def load(fn):
    f = DATA_DIR / fn
    if not f.exists(): return pd.DataFrame()
    df = pd.read_parquet(f)
    if "date" in df.columns: df["date"] = pd.to_datetime(df["date"])
    return df

market = load("market_prices.parquet")
fred   = load("fred_indicators.parquet")
sentiment = load("sentiment.parquet")

def lat(df, ind):
    if df.empty: return None
    s = df[df["indicator"]==ind].sort_values("date")
    return s.iloc[-1] if not s.empty else None

def dlt(df, ind):
    if df.empty: return None
    s = df[df["indicator"]==ind].sort_values("date").tail(10)
    return (s.iloc[-1]["value"]-s.iloc[-2]["value"]) if len(s)>=2 else None

now = datetime.now()

# ── 헤더 ─────────────────────────────────────────────────────
col_logo, col_info = st.columns([2,1])
with col_logo:
    st.markdown(f"""
<div style="font-family:'MaruBuri',serif;font-size:36px;font-weight:700;color:{TXT};
  font-style:italic;margin-bottom:6px">
  <span style="background:linear-gradient(180deg,transparent 50%,{PUR_HI} 50%);padding:0 8px">
    Deokyoon's Monitoring
  </span>
</div>
<div style="font-size:11px;color:{MUT};margin-bottom:1.5rem">
  한미 매크로 · 투자자산 · 가계부 · 이슈 종합 대시보드
</div>
""", unsafe_allow_html=True)

with col_info:
    v = lat(market,"VIX"); h = lat(fred,"HY_OAS")
    if v is not None and h is not None:
        vv,hv = v["value"],h["value"]
        if vv>28 or hv>5.5:   rt,rc_bg,rc_t = "RISK-OFF","#FEF2F2",B6
        elif vv<16 and hv<3.5: rt,rc_bg,rc_t = "RISK-ON","#EFF6FF",B4
        else:                   rt,rc_bg,rc_t = "NEUTRAL","#FAFAF0",SUB
        st.markdown(f"""
<div style="text-align:right;margin-top:8px">
  <span style="background:{rc_bg};color:{rc_t};border:1px solid {rc_t}40;
    padding:5px 16px;border-radius:16px;font-size:11px;font-weight:600;
    font-family:'JetBrains Mono',monospace">● {rt}</span>
  <div style="font-size:10px;color:{MUT};margin-top:6px">
    VIX {vv:.1f} · HY {hv:.2f}%<br>{now.strftime("%Y-%m-%d %H:%M")} KST
  </div>
</div>""", unsafe_allow_html=True)

# ── 빠른 KPI ─────────────────────────────────────────────────
st.markdown(f'<div style="height:1px;background:{BORD};margin:.5rem 0 1.2rem"></div>', unsafe_allow_html=True)
kpi_items = [
    ("S&P500","SPX",market,",.0f"),("NASDAQ","NASDAQ",market,",.0f"),
    ("KOSPI","KOSPI",market,",.0f"),("KOSDAQ","KOSDAQ",market,",.0f"),
    ("VIX","VIX",market,".1f"),("USD/KRW","USDKRW",market,",.0f"),
    ("미국10Y","US_10Y",fred,".2f"),
]
cols = st.columns(7)
for col,(lbl,ind,df,fmt) in zip(cols,kpi_items):
    r=lat(df,ind); d=dlt(df,ind)
    with col:
        if r is not None:
            clr = UP if (d or 0)>=0 else DN
            sign="▲" if (d or 0)>=0 else "▼"
            delta_str=f"{sign}{abs(d):.2f}" if d else "—"
            st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-left:3px solid {clr};
  border-radius:8px;padding:10px 12px;text-align:left">
  <div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.05em">{lbl}</div>
  <div style="font-size:18px;font-weight:700;color:{TXT};line-height:1.1;margin:3px 0">{format(r['value'],fmt)}</div>
  <div style="font-size:9px;color:{clr};font-weight:600">{delta_str} <span style="color:{MUT};font-weight:400">전일</span></div>
</div>""", unsafe_allow_html=True)

st.markdown(f'<div style="height:1px;background:{BORD};margin:1.2rem 0 1.5rem"></div>', unsafe_allow_html=True)

# ── 페이지 네비게이션 카드 ────────────────────────────────────
st.markdown(f'<div style="font-size:16px;font-weight:700;color:{TXT};margin-bottom:1rem">빠른 이동</div>', unsafe_allow_html=True)

pages_info = [
    ("pages/1_모니터링.py","📊 모니터링","한미 매크로 지표 · 환율 · 금리 · 증시 · 원자재",B5),
    ("pages/2_가계부.py",  "💰 가계부",  "수입·지출 추적 · 카테고리별 분석 · 저축률",    "#059669"),
    ("pages/3_투자자산.py","📈 투자자산","보유 종목 평가손익 · 자산 배분 · 수익률 비교",   "#D97706"),
    ("pages/4_스터디.py",  "📚 스터디",  "리포트 저장 · 태그 · 투자 아이디어 메모",       PUR_DK),
    ("pages/5_이슈.py",    "🔥 이슈",    "DART 공시 · 거래량 폭증 · 뉴스 · 구글 트렌드",  "#DC2626"),
]

nav_cols = st.columns(5)
for col,(path,label,desc,clr) in zip(nav_cols,pages_info):
    with col:
        st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-top:3px solid {clr};
  border-radius:10px;padding:16px;height:120px;display:flex;flex-direction:column;justify-content:space-between">
  <div>
    <div style="font-size:16px;font-weight:700;color:{TXT};margin-bottom:6px">{label}</div>
    <div style="font-size:10px;color:{MUT};line-height:1.4">{desc}</div>
  </div>
</div>""", unsafe_allow_html=True)
        st.page_link(path, label=f"바로가기 →", use_container_width=True)

# ── 마지막 업데이트 정보 ──────────────────────────────────────
st.markdown(f"""
<div style="margin-top:2rem;padding:12px 16px;background:{C2};border:1px solid {BORD};
  border-radius:8px;font-size:10px;color:{MUT};font-family:'JetBrains Mono',monospace">
  📅 마지막 데이터 수집: 매일 KST 07:00 자동 (GitHub Actions)<br>
  📦 데이터 소스: FRED · yfinance · CNN Fear&Greed · 한국은행 ECOS
</div>
""", unsafe_allow_html=True)
