"""
Macro Monitor — v3 (인라인 스타일 기반)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Macro Monitor", page_icon="◈",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
html,body,[class*="css"]{background:#070B0F!important;color:#D4DCE8!important;font-family:'JetBrains Mono',monospace!important}
.block-container{padding:1.5rem 2.5rem 3rem!important;max-width:100%!important}
section[data-testid="stSidebar"]{display:none}
#MainMenu,footer,header{visibility:hidden}
div[data-testid="stVerticalBlock"]>div{gap:0!important}
</style>
""", unsafe_allow_html=True)

DATA_DIR = Path(__file__).parent / "data"

@st.cache_data(ttl=3600)
def load(fn):
    f = DATA_DIR / fn
    if not f.exists(): return pd.DataFrame()
    df = pd.read_parquet(f)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df

fred      = load("fred_indicators.parquet")
market    = load("market_prices.parquet")
sentiment = load("sentiment.parquet")
ecos      = load("ecos_latest.parquet")

def lat(df, ind):
    if df.empty: return None
    s = df[df["indicator"]==ind].sort_values("date")
    return s.iloc[-1] if not s.empty else None

def ser(df, ind, days=365):
    if df.empty: return pd.DataFrame()
    s = df[df["indicator"]==ind].copy()
    if days: s = s[s["date"] >= pd.Timestamp.now()-pd.Timedelta(days=days)]
    return s.sort_values("date")

def dlt(df, ind):
    s = ser(df, ind, 15)
    return (s.iloc[-1]["value"] - s.iloc[-2]["value"]) if len(s) >= 2 else None

# ── 차트 상수 ─────────────────────────────────────────────────
P="#0D1520"; B="#070B0F"; G="#0F1923"
BASE = dict(
    paper_bgcolor=P, plot_bgcolor=B,
    font=dict(family="JetBrains Mono", size=10, color="#4E5F74"),
    margin=dict(l=6,r=6,t=30,b=6),
    legend=dict(orientation="h",y=1.1,x=0,font=dict(size=9,color="#6B7280"),bgcolor="rgba(0,0,0,0)"),
    hovermode="x unified",
    hoverlabel=dict(bgcolor="#111D2E",bordercolor="#243550",font=dict(family="JetBrains Mono",size=11)),
    xaxis=dict(showgrid=True,gridcolor=G,gridwidth=1,zeroline=False,showline=False,tickfont=dict(size=9)),
    yaxis=dict(showgrid=True,gridcolor=G,gridwidth=1,zeroline=False,showline=False,tickfont=dict(size=9)),
)

def lc(traces, title="", h=262, zero=False):
    fig = go.Figure()
    for df,nm,clr in traces:
        if df.empty: continue
        fig.add_trace(go.Scatter(x=df["date"],y=df["value"],name=nm,
            line=dict(color=clr,width=1.8),
            hovertemplate=f"<b>{nm}</b> %{{y:.2f}}<extra></extra>"))
    if zero: fig.add_hline(y=0,line_dash="dot",line_color="#243550",line_width=1)
    fig.update_layout(title=dict(text=title,font=dict(size=11,color="#6B7280"),x=0),height=h,**BASE)
    return fig

# ── 레짐 계산 ────────────────────────────────────────────────
def regime():
    v = lat(market,"VIX"); h = lat(fred,"HY_OAS")
    if v is None or h is None: return "neu","LOADING","데이터 수집 중"
    vv,hv = v["value"],h["value"]
    if vv>28 or hv>5.5:    return "risk","RISK-OFF",f"VIX {vv:.1f} · HY {hv:.2f}% — 위험 회피 국면"
    elif vv<16 and hv<3.5: return "on","RISK-ON",  f"VIX {vv:.1f} · HY {hv:.2f}% — 위험 선호 국면"
    else:                  return "neu","NEUTRAL",  f"VIX {vv:.1f} · HY {hv:.2f}% — 관망 국면"

rc,rt,rn = regime()

# ── 헤더 ─────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:flex-end;padding-bottom:16px;border-bottom:1px solid #1A2535;margin-bottom:18px">
  <div style="font-family:'Syne',sans-serif;font-size:24px;font-weight:800;color:#fff;letter-spacing:-.025em">
    ◈ MACRO <span style="color:#00E5CC">MONITOR</span>
  </div>
  <div style="font-size:10px;color:#4E5F74;text-align:right;line-height:2;letter-spacing:.04em">
    {datetime.now().strftime("%Y-%m-%d")} &nbsp;·&nbsp; 매일 KST 07:00 자동 수집<br>
    FRED &nbsp;·&nbsp; yfinance &nbsp;·&nbsp; CNN &nbsp;·&nbsp; ECOS
  </div>
</div>
""", unsafe_allow_html=True)

# ── 레짐 배지 ────────────────────────────────────────────────
RG = {
    "risk": ("rgba(239,68,68,.12)","#EF4444","rgba(239,68,68,.3)"),
    "on":   ("rgba(0,229,204,.1)", "#00E5CC","rgba(0,229,204,.3)"),
    "neu":  ("rgba(245,158,11,.12)","#F59E0B","rgba(245,158,11,.3)"),
}
bg_c,txt_c,brd_c = RG[rc]
st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;font-family:'JetBrains Mono',monospace">
  <span style="font-size:10px;color:#4E5F74;letter-spacing:2px">REGIME</span>
  <span style="background:{bg_c};color:{txt_c};border:1px solid {brd_c};padding:3px 10px;border-radius:3px;font-size:10px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase">● {rt}</span>
  <span style="font-size:10px;color:#4E5F74">{rn}</span>
</div>
""", unsafe_allow_html=True)

# ── KPI 카드 (st.columns 사용) ───────────────────────────────
CS = "background:#0D1520;border:1px solid #1A2535;border-radius:8px;padding:11px 13px 10px;font-family:'JetBrains Mono',monospace"
LS = "font-size:9px;color:#4E5F74;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:5px"
VS = "font-size:17px;font-weight:600;color:#fff;line-height:1.2;margin-bottom:3px"
DS = "font-size:9px;font-weight:500"

def kcard(label, ind, df, fmt=".2f", inv=False):
    r = lat(df, ind)
    if r is None:
        return f'<div style="{CS}"><div style="{LS}">{label}</div><div style="{VS}">—</div></div>'
    val = r["value"]; d = dlt(df, ind); vs = format(val, fmt)
    if d is not None:
        clr = ("#00E5CC" if d>0 else "#EF4444") if inv else ("#EF4444" if d>0 else "#00E5CC")
        dh = f'<div style="{DS};color:{clr}">{"+" if d>0 else ""}{d:.2f}</div>'
    else:
        dh = f'<div style="{DS};color:#4E5F74">—</div>'
    return f'<div style="{CS}"><div style="{LS}">{label}</div><div style="{VS}">{vs}</div>{dh}</div>'

def fgcard():
    r = lat(sentiment, "FEAR_GREED")
    if r is None:
        return f'<div style="{CS}"><div style="{LS}">공포탐욕</div><div style="{VS}">—</div></div>'
    v = r["value"]
    if v<25:   c,t="#EF4444","극도 공포"
    elif v<45: c,t="#F97316","공포"
    elif v<55: c,t="#EAB308","중립"
    elif v<75: c,t="#84CC16","탐욕"
    else:      c,t="#22C55E","극도 탐욕"
    badge = f'<span style="background:{c}20;color:{c};border:1px solid {c}40;padding:1px 6px;border-radius:3px;font-size:9px;font-weight:600;letter-spacing:1px;text-transform:uppercase">{v:.0f} · {t}</span>'
    return f'<div style="{CS}"><div style="{LS}">공포탐욕</div><div style="{VS}">{v:.0f}</div>{badge}</div>'

kpi_specs = [
    ("VIX",     "VIX",    market, ".1f",  True),
    ("SOX",     "SOX",    market, ",.0f", False),
    ("S&P 500", "SPX",    market, ",.0f", False),
    ("KOSPI",   "KOSPI",  market, ",.0f", False),
    ("USD/KRW", "USDKRW", market, ",.0f", True),
    ("US 10Y",  "US_10Y", fred,   ".2f",  True),
    ("HY OAS",  "HY_OAS", fred,   ".2f",  True),
]

kcols = st.columns(8)
for col,(lbl,ind,df,fmt,inv) in zip(kcols, kpi_specs):
    with col:
        st.markdown(kcard(lbl,ind,df,fmt,inv), unsafe_allow_html=True)
with kcols[7]:
    st.markdown(fgcard(), unsafe_allow_html=True)

# ── 섹션 헤더 헬퍼 ──────────────────────────────────────────
def sh(id_, name):
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin:28px 0 12px;font-family:'JetBrains Mono',monospace">
  <span style="font-family:'Syne',sans-serif;font-size:9px;font-weight:700;color:#070B0F;background:#00E5CC;padding:1px 6px;border-radius:3px;letter-spacing:.8px">{id_}</span>
  <span style="font-family:'Syne',sans-serif;font-size:12px;font-weight:600;color:#8B98A8;letter-spacing:1px">{name}</span>
  <div style="flex:1;height:1px;background:#1A2535"></div>
</div>""", unsafe_allow_html=True)

# ── A
sh("A","글로벌 위험 & 심리")
c1,c2 = st.columns(2)
with c1:
    fig = lc([(ser(market,"VIX"),"VIX","#EF4444"),(ser(fred,"HY_OAS"),"HY OAS %","#F59E0B")],
             "VIX · HY 신용스프레드")
    fig.add_hrect(y0=25,y1=100,fillcolor="rgba(239,68,68,0.03)",line_width=0)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    fg_s=ser(sentiment,"FEAR_GREED"); sp_s=ser(fred,"T10Y2Y_SPREAD")
    fig = make_subplots(specs=[[{"secondary_y":True}]])
    AX = dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9))
    if not fg_s.empty:
        fig.add_trace(go.Scatter(x=fg_s["date"],y=fg_s["value"],name="공포탐욕",
            line=dict(color="#3B82F6",width=1.8),
            hovertemplate="<b>공포탐욕</b> %{y:.0f}<extra></extra>"),secondary_y=False)
        fig.add_hrect(y0=0,y1=25,fillcolor="rgba(239,68,68,0.04)",line_width=0)
        fig.add_hrect(y0=75,y1=100,fillcolor="rgba(34,197,94,0.04)",line_width=0)
    if not sp_s.empty:
        fig.add_trace(go.Scatter(x=sp_s["date"],y=sp_s["value"],name="2Y-10Y %",
            line=dict(color="#F59E0B",width=1.5,dash="dot"),
            hovertemplate="<b>스프레드</b> %{y:.2f}%<extra></extra>"),secondary_y=True)
    fig.add_hline(y=0,line_dash="dot",line_color="#243550",line_width=1,secondary_y=True)
    fig.update_layout(
        title=dict(text="공포탐욕지수 · 금리 스프레드",font=dict(size=11,color="#6B7280"),x=0),
        height=262, paper_bgcolor=P, plot_bgcolor=B,
        font=dict(family="JetBrains Mono",size=10,color="#4E5F74"),
        margin=dict(l=6,r=6,t=30,b=6),
        legend=dict(orientation="h",y=1.1,x=0,font=dict(size=9,color="#6B7280"),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified", xaxis=AX)
    fig.update_yaxes(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9),secondary_y=False)
    fig.update_yaxes(showgrid=False,zeroline=False,showline=False,tickfont=dict(size=9,color="#F59E0B"),secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

# ── B
sh("B","미국 금리 & 달러")
c1,c2 = st.columns(2)
with c1:
    fig = lc([(ser(fred,"US_10Y"),"US 10Y %","#3B82F6"),(ser(fred,"T10Y2Y_SPREAD"),"2Y-10Y %","#F59E0B")],
             "미국 국채금리",zero=True)
    fig.add_hrect(y0=4.5,y1=10,fillcolor="rgba(245,158,11,0.03)",line_width=0)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    st.plotly_chart(lc([(ser(market,"DXY"),"DXY","#8B5CF6")],"DXY 달러 인덱스"), use_container_width=True)

# ── C
sh("C","한국 시장")
c1,c2 = st.columns(2)
with c1:
    fig = lc([(ser(market,"USDKRW"),"USD/KRW","#F97316")],"원달러 환율")
    fig.add_hrect(y0=1400,y1=2500,fillcolor="rgba(239,68,68,0.03)",line_width=0)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    st.plotly_chart(lc([(ser(market,"KOSPI"),"KOSPI","#00E5CC")],"KOSPI"), use_container_width=True)

# ── D
sh("D","글로벌 주식 모멘텀")
c1,c2 = st.columns(2)
with c1:
    st.plotly_chart(lc([(ser(market,"SOX"),"SOX 반도체","#3B82F6")],"필라델피아 반도체 (SOX)"), use_container_width=True)
with c2:
    st.plotly_chart(lc([(ser(market,"SPX"),"S&P 500","#8B5CF6")],"S&P 500"), use_container_width=True)

# ── E
sh("E","미국 월간 매크로")
c1,c2 = st.columns(2)
with c1:
    cpi = ser(fred,"US_CORE_CPI",days=365*6)
    if not cpi.empty:
        cpi = cpi.copy()
        cpi["yoy"] = cpi["value"].pct_change(12)*100
        cy = cpi.dropna(subset=["yoy"])[["date","yoy"]].rename(columns={"yoy":"value"})
        fig = lc([(cy,"Core CPI YoY %","#F97316")],"미국 Core CPI YoY")
        fig.add_hline(y=2.0,line_dash="dot",line_color="#243550",line_width=1.5,
                      annotation_text="2% 목표",annotation_font_color="#4E5F74",
                      annotation_position="bottom right")
        st.plotly_chart(fig, use_container_width=True)
with c2:
    nfp = ser(fred,"US_NFP",days=365*5)
    if not nfp.empty:
        nfp = nfp.copy(); nfp["mom"] = nfp["value"].diff()
        nm = nfp.dropna(subset=["mom"])
        fig = go.Figure(go.Bar(x=nm["date"],y=nm["mom"],
            marker_color=["#22C55E" if v>=0 else "#EF4444" for v in nm["mom"]],
            hovertemplate="<b>NFP MoM</b> %{y:,.0f}천명<extra></extra>"))
        nl = {k:v for k,v in BASE.items() if k!="legend"}
        fig.update_layout(title=dict(text="비농업 고용 MoM (천명)",font=dict(size=11,color="#6B7280"),x=0),
                          height=262,showlegend=False,**nl)
        st.plotly_chart(fig, use_container_width=True)

# ── F
sh("F","한국 매크로 · ECOS")
if ecos.empty:
    st.info("ECOS 데이터 없음")
else:
    cols_list = [c for c in ["CLASS_NAME","KEYSTAT_NAME","DATA_VALUE","UNIT_NAME","CYCLE"] if c in ecos.columns]
    if cols_list:
        rows = ""
        for _,r in ecos[cols_list].iterrows():
            rows += (f'<tr>'
                     f'<td style="padding:.4rem .85rem;font-size:10px;color:#4E5F74;border-bottom:1px solid rgba(26,37,53,.5)">{r.get("CLASS_NAME","")}</td>'
                     f'<td style="padding:.4rem .85rem;font-size:11px;color:#D4DCE8;border-bottom:1px solid rgba(26,37,53,.5)">{r.get("KEYSTAT_NAME","")}</td>'
                     f'<td style="padding:.4rem .85rem;font-size:11px;font-weight:600;color:#fff;text-align:right;border-bottom:1px solid rgba(26,37,53,.5)">{r.get("DATA_VALUE","")}</td>'
                     f'<td style="padding:.4rem .85rem;font-size:10px;color:#4E5F74;text-align:right;border-bottom:1px solid rgba(26,37,53,.5)">{r.get("UNIT_NAME","")}</td>'
                     f'<td style="padding:.4rem .85rem;font-size:10px;color:#4E5F74;text-align:right;border-bottom:1px solid rgba(26,37,53,.5)">{r.get("CYCLE","")}</td>'
                     f'</tr>')
        st.markdown(f"""
<div style="background:#0D1520;border:1px solid #1A2535;border-radius:8px;overflow:hidden;font-family:'JetBrains Mono',monospace">
<table style="width:100%;border-collapse:collapse">
  <thead>
    <tr style="background:#111D2E">
      <th style="padding:.55rem .85rem;text-align:left;font-size:9px;color:#4E5F74;letter-spacing:1.5px;text-transform:uppercase;font-weight:500;border-bottom:1px solid #1A2535;width:18%">분류</th>
      <th style="padding:.55rem .85rem;text-align:left;font-size:9px;color:#4E5F74;letter-spacing:1.5px;text-transform:uppercase;font-weight:500;border-bottom:1px solid #1A2535;width:42%">지표명</th>
      <th style="padding:.55rem .85rem;text-align:right;font-size:9px;color:#4E5F74;letter-spacing:1.5px;text-transform:uppercase;font-weight:500;border-bottom:1px solid #1A2535;width:15%">현재값</th>
      <th style="padding:.55rem .85rem;text-align:right;font-size:9px;color:#4E5F74;letter-spacing:1.5px;text-transform:uppercase;font-weight:500;border-bottom:1px solid #1A2535;width:12%">단위</th>
      <th style="padding:.55rem .85rem;text-align:right;font-size:9px;color:#4E5F74;letter-spacing:1.5px;text-transform:uppercase;font-weight:500;border-bottom:1px solid #1A2535;width:8%">주기</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
</div>""", unsafe_allow_html=True)

# ── 푸터
st.markdown("""
<div style="margin-top:2.5rem;padding-top:.85rem;border-top:1px solid #1A2535;font-size:10px;color:#4E5F74;text-align:center;letter-spacing:1px;font-family:'JetBrains Mono',monospace">
  FRED &nbsp;·&nbsp; yfinance &nbsp;·&nbsp; CNN Fear &amp; Greed &nbsp;·&nbsp; 한국은행 ECOS &nbsp;·&nbsp; 매일 KST 07:00 자동 수집
</div>
""", unsafe_allow_html=True)
