"""
Macro Monitor — v2
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
:root {
  --bg:#070B0F; --s1:#0D1520; --s2:#111D2E;
  --b1:#1A2535; --b2:#243550;
  --t1:#D4DCE8; --t2:#8B98A8; --t3:#4E5F74;
  --cy:#00E5CC; --am:#F59E0B; --rd:#EF4444;
  --gn:#22C55E; --bl:#3B82F6; --pu:#8B5CF6; --or:#F97316;
}
*,*::before,*::after{box-sizing:border-box}
html,body,[class*="css"]{background:var(--bg)!important;color:var(--t1)!important;font-family:'JetBrains Mono',monospace!important}
.block-container{padding:1.5rem 2.5rem 3rem!important;max-width:100%!important}
section[data-testid="stSidebar"]{display:none}
#MainMenu,footer,header{visibility:hidden}

.db-hdr{display:flex;justify-content:space-between;align-items:flex-end;padding-bottom:1.1rem;border-bottom:1px solid var(--b1);margin-bottom:1.3rem}
.db-ttl{font-family:'Syne',sans-serif;font-size:1.55rem;font-weight:800;color:#fff;letter-spacing:-.025em}
.db-ttl em{color:var(--cy);font-style:normal}
.db-meta{font-size:.68rem;color:var(--t3);text-align:right;line-height:2;letter-spacing:.04em}

.rg-row{display:flex;align-items:center;gap:.7rem;margin-bottom:1.3rem}
.rg-lbl{font-size:.63rem;color:var(--t3);letter-spacing:.12em}
.rg-b{padding:.2rem .65rem;border-radius:3px;font-size:.66rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase}
.r-risk{background:rgba(239,68,68,.12);color:#EF4444;border:1px solid rgba(239,68,68,.3)}
.r-neu{background:rgba(245,158,11,.12);color:#F59E0B;border:1px solid rgba(245,158,11,.3)}
.r-on{background:rgba(0,229,204,.1);color:#00E5CC;border:1px solid rgba(0,229,204,.3)}
.rg-note{font-size:.67rem;color:var(--t3)}

.kg{display:grid;grid-template-columns:repeat(8,1fr);gap:.5rem;margin-bottom:1.5rem}
.kc{background:var(--s1);border:1px solid var(--b1);border-radius:8px;padding:.75rem .8rem .65rem;transition:border-color .15s;cursor:default}
.kc:hover{border-color:var(--b2)}
.kl{font-size:.58rem;color:var(--t3);letter-spacing:.1em;text-transform:uppercase;margin-bottom:.28rem}
.kv{font-size:1.1rem;font-weight:600;color:#fff;line-height:1.2}
.kd{font-size:.6rem;font-weight:500;margin-top:.15rem}
.up{color:var(--rd)} .dn{color:var(--cy)}
.iu{color:var(--cy)} .id{color:var(--rd)}
.nu{color:var(--t3)}

.fg-p{display:inline-block;padding:.1rem .45rem;border-radius:3px;font-size:.58rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin-top:.15rem}

.sh{display:flex;align-items:center;gap:.6rem;margin:1.9rem 0 .8rem}
.sh-id{font-family:'Syne',sans-serif;font-size:.6rem;font-weight:700;color:var(--bg);background:var(--cy);padding:.1rem .42rem;border-radius:3px;letter-spacing:.04em}
.sh-nm{font-family:'Syne',sans-serif;font-size:.8rem;font-weight:600;color:var(--t2);letter-spacing:.03em}
.sh-ln{flex:1;height:1px;background:var(--b1)}

.ew{background:var(--s1);border:1px solid var(--b1);border-radius:8px;overflow:hidden}
.et{width:100%;border-collapse:collapse;font-size:.7rem}
.et thead th{background:var(--s2);color:var(--t3);font-size:.6rem;letter-spacing:.1em;text-transform:uppercase;padding:.55rem .85rem;text-align:left;font-weight:500;border-bottom:1px solid var(--b1)}
.et tbody td{padding:.4rem .85rem;border-bottom:1px solid rgba(26,37,53,.55);color:var(--t1)}
.et tbody tr:last-child td{border-bottom:none}
.et tbody tr:hover td{background:rgba(17,29,46,.55)}
.ev{font-weight:600;color:#fff;text-align:right}
.eu{color:var(--t3);font-size:.6rem;text-align:right}
.ec{color:var(--t3);font-size:.6rem}

.db-ft{margin-top:2.5rem;padding-top:.85rem;border-top:1px solid var(--b1);font-size:.6rem;color:var(--t3);text-align:center;letter-spacing:.06em}
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

def sh(id_, name):
    st.markdown(f'<div class="sh"><span class="sh-id">{id_}</span>'
                f'<span class="sh-nm">{name}</span><div class="sh-ln"></div></div>',
                unsafe_allow_html=True)

def regime():
    v = lat(market,"VIX"); h = lat(fred,"HY_OAS")
    if v is None or h is None: return "neu","LOADING","데이터 수집 중"
    vv,hv = v["value"],h["value"]
    if vv>28 or hv>5.5:   return "risk","RISK-OFF",f"VIX {vv:.1f} · HY {hv:.2f}% — 위험 회피 국면"
    elif vv<16 and hv<3.5: return "on","RISK-ON", f"VIX {vv:.1f} · HY {hv:.2f}% — 위험 선호 국면"
    else:                  return "neu","NEUTRAL", f"VIX {vv:.1f} · HY {hv:.2f}% — 관망 국면"

rc,rt,rn = regime()

st.markdown(f"""
<div class="db-hdr">
  <div class="db-ttl">◈ MACRO <em>MONITOR</em></div>
  <div class="db-meta">{datetime.now().strftime("%Y-%m-%d")} &nbsp;·&nbsp; 매일 KST 07:00 자동 수집<br>FRED · yfinance · CNN · ECOS</div>
</div>
<div class="rg-row">
  <span class="rg-lbl">REGIME</span>
  <span class="rg-b r-{rc}">● {rt}</span>
  <span class="rg-note">{rn}</span>
</div>
""", unsafe_allow_html=True)

def kc(label, ind, df, fmt=".2f", inv=False, badge=None):
    r = lat(df, ind)
    if r is None:
        return f'<div class="kc"><div class="kl">{label}</div><div class="kv">—</div></div>'
    val = r["value"]; d = dlt(df, ind)
    vs = format(val, fmt)
    if badge:
        dh = badge
    elif d is not None:
        cls = ("iu" if d>0 else "id") if inv else ("up" if d>0 else "dn")
        dh = f'<div class="kd {cls}">{"+" if d>0 else ""}{d:.2f}</div>'
    else:
        dh = '<div class="kd nu">—</div>'
    return f'<div class="kc"><div class="kl">{label}</div><div class="kv">{vs}</div>{dh}</div>'

def fg_pill(v):
    if v<25:   c,t="#EF4444","극도 공포"
    elif v<45: c,t="#F97316","공포"
    elif v<55: c,t="#EAB308","중립"
    elif v<75: c,t="#84CC16","탐욕"
    else:      c,t="#22C55E","극도 탐욕"
    return f'<div class="fg-p" style="background:{c}18;color:{c};border:1px solid {c}40">{v:.0f} · {t}</div>'

fg_r = lat(sentiment,"FEAR_GREED")
fg_b = fg_pill(fg_r["value"]) if fg_r else '<div class="kd nu">—</div>'
fg_v = f'{fg_r["value"]:.0f}' if fg_r else "—"

st.markdown(f"""
<div class="kg">
  {kc("VIX","VIX",market,".1f",inv=True)}
  {kc("SOX","SOX",market,",.0f")}
  {kc("S&P 500","SPX",market,",.0f")}
  {kc("KOSPI","KOSPI",market,",.0f")}
  {kc("USD / KRW","USDKRW",market,",.0f",inv=True)}
  {kc("US 10Y","US_10Y",fred,".2f",inv=True)}
  {kc("HY OAS","HY_OAS",fred,".2f",inv=True)}
  <div class="kc">
    <div class="kl">공포탐욕</div>
    <div class="kv">{fg_v}</div>
    {fg_b}
  </div>
</div>
""", unsafe_allow_html=True)

# ── A
sh("A","글로벌 위험 & 심리")
c1,c2 = st.columns(2)
with c1:
    fig = lc([(ser(market,"VIX"),"VIX","#EF4444"),(ser(fred,"HY_OAS"),"HY OAS %","#F59E0B")],
             "VIX · HY 신용스프레드")
    fig.add_hrect(y0=25,y1=100,fillcolor="rgba(239,68,68,0.03)",line_width=0)
    st.plotly_chart(fig,use_container_width=True)
with c2:
    fg_s = ser(sentiment,"FEAR_GREED"); sp_s = ser(fred,"T10Y2Y_SPREAD")
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
    fig.update_layout(title=dict(text="공포탐욕지수 · 금리 스프레드",font=dict(size=11,color="#6B7280"),x=0),
        height=262,paper_bgcolor=P,plot_bgcolor=B,
        font=dict(family="JetBrains Mono",size=10,color="#4E5F74"),
        margin=dict(l=6,r=6,t=30,b=6),
        legend=dict(orientation="h",y=1.1,x=0,font=dict(size=9,color="#6B7280"),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",hoverlabel=dict(bgcolor="#111D2E",bordercolor="#243550",font=dict(family="JetBrains Mono",size=11)),
        xaxis=AX)
    fig.update_yaxes(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9),secondary_y=False)
    fig.update_yaxes(showgrid=False,zeroline=False,showline=False,tickfont=dict(size=9,color="#F59E0B"),secondary_y=True)
    st.plotly_chart(fig,use_container_width=True)

# ── B
sh("B","미국 금리 & 달러")
c1,c2 = st.columns(2)
with c1:
    fig = lc([(ser(fred,"US_10Y"),"US 10Y %","#3B82F6"),(ser(fred,"T10Y2Y_SPREAD"),"2Y-10Y %","#F59E0B")],
             "미국 국채금리",zero=True)
    fig.add_hrect(y0=4.5,y1=10,fillcolor="rgba(245,158,11,0.03)",line_width=0)
    st.plotly_chart(fig,use_container_width=True)
with c2:
    st.plotly_chart(lc([(ser(market,"DXY"),"DXY","#8B5CF6")],"DXY 달러 인덱스"),use_container_width=True)

# ── C
sh("C","한국 시장")
c1,c2 = st.columns(2)
with c1:
    fig = lc([(ser(market,"USDKRW"),"USD/KRW","#F97316")],"원달러 환율")
    fig.add_hrect(y0=1400,y1=2500,fillcolor="rgba(239,68,68,0.03)",line_width=0)
    st.plotly_chart(fig,use_container_width=True)
with c2:
    st.plotly_chart(lc([(ser(market,"KOSPI"),"KOSPI","#00E5CC")],"KOSPI"),use_container_width=True)

# ── D
sh("D","글로벌 주식 모멘텀")
c1,c2 = st.columns(2)
with c1:
    st.plotly_chart(lc([(ser(market,"SOX"),"SOX 반도체","#3B82F6")],"필라델피아 반도체 (SOX)"),use_container_width=True)
with c2:
    st.plotly_chart(lc([(ser(market,"SPX"),"S&P 500","#8B5CF6")],"S&P 500"),use_container_width=True)

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
                      annotation_text="2% 목표",annotation_font_color="#4E5F74",annotation_position="bottom right")
        st.plotly_chart(fig,use_container_width=True)
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
        st.plotly_chart(fig,use_container_width=True)

# ── F
sh("F","한국 매크로 · ECOS")
if ecos.empty:
    st.info("ECOS 데이터 없음")
else:
    cols = [c for c in ["CLASS_NAME","KEYSTAT_NAME","DATA_VALUE","UNIT_NAME","CYCLE"] if c in ecos.columns]
    if cols:
        rows = ""
        for _,r in ecos[cols].iterrows():
            rows += (f'<tr><td class="ec">{r.get("CLASS_NAME","")}</td>'
                     f'<td>{r.get("KEYSTAT_NAME","")}</td>'
                     f'<td class="ev">{r.get("DATA_VALUE","")}</td>'
                     f'<td class="eu">{r.get("UNIT_NAME","")}</td>'
                     f'<td class="ec" style="text-align:right">{r.get("CYCLE","")}</td></tr>')
        st.markdown(f"""
<div class="ew"><table class="et">
  <thead><tr>
    <th style="width:18%">분류</th><th style="width:42%">지표명</th>
    <th style="width:15%;text-align:right">현재값</th>
    <th style="width:12%;text-align:right">단위</th>
    <th style="width:8%;text-align:right">주기</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table></div>""", unsafe_allow_html=True)

st.markdown("""
<div class="db-ft">FRED &nbsp;·&nbsp; yfinance &nbsp;·&nbsp; CNN Fear & Greed &nbsp;·&nbsp; 한국은행 ECOS &nbsp;·&nbsp; 매일 KST 07:00 자동 수집</div>
""", unsafe_allow_html=True)
