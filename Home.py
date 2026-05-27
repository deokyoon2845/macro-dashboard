"""Deokyoon's Monitoring — Home (일일 AI 브리핑 포함)"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Deokyoon's Monitoring", page_icon="◈",
                   layout="wide", initial_sidebar_state="expanded")

BG="#0A0D13"; CARD="#111620"; C2="#161C28"; C3="#1C2438"; BORD="#222A3A"; G="#181F2C"
TXT="#E4EAF6"; SUB="#7A8CA4"; MUT="#4A5668"; ACC="#4A82E4"; UP="#2ECC71"; DN="#E74C3C"

st.markdown(f"""
<style>
html,body,[class*="css"]{{background-color:{BG}!important;color:{TXT}!important;
  font-family:'MaruBuri','Gowun Batang',serif!important;letter-spacing:.015em!important}}
.block-container{{padding:1.5rem 2rem 3rem!important;max-width:100%!important;background:transparent!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
[data-testid="stSidebar"]{{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
#MainMenu,footer,header{{visibility:hidden}}
p,span,div,label{{color:{TXT}!important}}
</style>
""", unsafe_allow_html=True)

DATA_DIR = Path(__file__).parent/"data"

@st.cache_data(ttl=600)
def load_pq(fn):
    p=DATA_DIR/fn
    if not p.exists(): return pd.DataFrame()
    df=pd.read_parquet(p)
    if "date" in df.columns: df["date"]=pd.to_datetime(df["date"])
    return df

market=load_pq("market_prices.parquet"); fred=load_pq("fred_indicators.parquet")

def latest(df,ind):
    if df.empty or "indicator" not in df.columns: return None
    s=df[df["indicator"]==ind].sort_values("date")
    return s.iloc[-1] if not s.empty else None

def dlt(df,ind):
    if df.empty or "indicator" not in df.columns: return None
    s=df[df["indicator"]==ind].sort_values("date").tail(2)
    return (s.iloc[-1]["value"]-s.iloc[-2]["value"]) if len(s)>=2 else None

# ── 일일 AI 브리핑 ────────────────────────────────────────────
BRIEF_FILE = DATA_DIR/"daily_briefing.json"
brief = None
if BRIEF_FILE.exists():
    with open(BRIEF_FILE, encoding="utf-8") as f:
        brief = json.load(f)

st.markdown(f"""
<div style="font-family:'MaruBuri',serif;font-size:32px;font-weight:700;font-style:italic;margin-bottom:4px">
  <span style="background:rgba(47,129,247,.28);padding:2px 10px;border-radius:6px">
    Deokyoon's Monitoring
  </span>
</div>
<div style="font-size:11px;color:{MUT};margin-bottom:1.5rem">
  한미 매크로 · 투자자산 · 가계부 · 이슈 종합 대시보드
</div>
""", unsafe_allow_html=True)

if brief:
    mood_map={"positive":(B5,"rgba(56,139,253,.15)"),"neutral":(SUB,C2),"cautious":(B8,"rgba(17,88,199,.15)")}
    mc,mbg=mood_map.get(brief.get("mood","neutral"),(SUB,C2))
    try: gen_t=datetime.fromisoformat(brief.get("generated_at","")).strftime("%m-%d %H:%M")
    except: gen_t=""
    st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-left:4px solid {mc};
  border-radius:10px;padding:18px 22px;margin-bottom:1.5rem">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <div>
      <span style="font-size:10px;color:{MUT};text-transform:uppercase;letter-spacing:.1em;font-family:'JetBrains Mono',monospace">오늘의 브리핑</span>
      <span style="background:{mbg};color:{mc};padding:2px 10px;border-radius:10px;font-size:9px;font-weight:600;margin-left:8px;font-family:'JetBrains Mono',monospace">{brief.get('mood','').upper()}</span>
    </div>
    <span style="font-size:9px;color:{MUT};font-family:'JetBrains Mono',monospace">{gen_t} 생성</span>
  </div>
  <div style="font-size:20px;font-weight:700;color:{TXT};margin-bottom:12px">{brief.get('headline','')}</div>
  <div style="font-size:12px;color:{TXT};line-height:1.7;margin-bottom:4px"><b style="color:{SUB}">📊 시장 ·</b> {brief.get('market','')}</div>
  <div style="font-size:12px;color:{TXT};line-height:1.7;margin-bottom:4px"><b style="color:{SUB}">💼 포트폴리오 ·</b> {brief.get('portfolio','')}</div>
  <div style="font-size:12px;color:{TXT};line-height:1.7;margin-bottom:12px"><b style="color:{SUB}">👀 주의 ·</b> {brief.get('watch','')}</div>
  <div style="background:{C2};border-radius:6px;padding:10px 14px;font-size:12px;color:{mc};font-weight:600">
    💬 {brief.get('comment','')}
  </div>
</div>""", unsafe_allow_html=True)

# ── KPI ──────────────────────────────────────────────────────
st.markdown(f'<div style="height:1px;background:{BORD};margin:.5rem 0 1.2rem"></div>',unsafe_allow_html=True)
KPI_ITEMS=[("S&P500","SPX",market,",.0f"),("NASDAQ","NASDAQ",market,",.0f"),
           ("KOSPI","KOSPI",market,",.0f"),("KOSDAQ","KOSDAQ",market,",.0f"),
           ("VIX","VIX",market,".1f"),("USD/KRW","USDKRW",market,",.0f"),("미국10Y","US_10Y",fred,".2f")]
cols=st.columns(7)
for col,(lbl,ind,df_,fmt) in zip(cols,KPI_ITEMS):
    r=latest(df_,ind); d=dlt(df_,ind)
    with col:
        if r is not None:
            clr=UP if (d or 0)>=0 else DN
            st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-left:3px solid {clr};
  border-radius:8px;padding:10px 12px">
  <div style="font-size:9px;color:{MUT};text-transform:uppercase">{lbl}</div>
  <div style="font-size:18px;font-weight:700;color:{TXT};margin:3px 0;font-family:'JetBrains Mono',monospace">{format(r['value'],fmt)}</div>
  <div style="font-size:9px;color:{clr};font-weight:600">{'▲' if (d or 0)>=0 else '▼'}{abs(d):.2f}</div>
</div>""",unsafe_allow_html=True)

# ── 네비게이션 카드 ─────────────────────────────────────────
st.markdown(f'<div style="height:1px;background:{BORD};margin:1.2rem 0 1.5rem"></div>',unsafe_allow_html=True)
pages_info=[
    ("pages/1_모니터링.py","📊 모니터링","매크로 지표 · 금리 · 환율 · 증시 · 원자재",B5),
    ("pages/2_가계부.py","💰 가계부","수입·지출 추적 · 카테고리 분석 · 저축률","#059669"),
    ("pages/3_투자자산.py","📈 투자자산","평가손익 · 뉴스 · DART 공시 · 수익률 추이","#D97706"),
    ("pages/4_스터디.py","📚 스터디","거래 일지 · AI 회고 · 학습 노트","#58A6FF"),
    ("pages/5_이슈.py","🔥 이슈","DART 공시 · 구글 트렌드 · 거래량 이상","#F85149"),
]
nav_cols=st.columns(5)
for col,(path,label,desc,clr) in zip(nav_cols,pages_info):
    with col:
        st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-top:3px solid {clr};
  border-radius:10px;padding:14px;height:110px;display:flex;flex-direction:column;justify-content:space-between;margin-bottom:8px">
  <div>
    <div style="font-size:16px;font-weight:700;color:{TXT};margin-bottom:4px">{label}</div>
    <div style="font-size:10px;color:{MUT};line-height:1.4">{desc}</div>
  </div>
</div>""",unsafe_allow_html=True)
        st.page_link(path,label="바로가기 →",use_container_width=True)

st.markdown(f"""
<div style="margin-top:2rem;padding:10px 14px;background:{C2};border:1px solid {BORD};
  border-radius:8px;font-size:10px;color:{MUT};font-family:'JetBrains Mono',monospace">
  📅 매일 KST 07:00 자동수집 · FRED · yfinance · CNN F&G · ECOS · 네이버 뉴스 · DART
</div>
""",unsafe_allow_html=True)
