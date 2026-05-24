"""
Macro Monitor — v4 (스파크라인 + F&G 게이지 + 다크모드)
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
.block-container{padding:1.5rem 2.5rem 3rem!important;max-width:100%!important;background:#070B0F!important}
section[data-testid="stSidebar"]{display:none}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stAppViewContainer"]{background:#070B0F!important}
[data-testid="stHeader"]{background:#070B0F!important}
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

# ── 스파크라인 SVG ────────────────────────────────────────────
def spark(df, ind, color="#00E5CC", days=90, w=64, h=26):
    s = ser(df, ind, days)
    vals = s["value"].dropna().tolist() if not s.empty else []
    if len(vals) < 3: return ""
    mn, mx = min(vals), max(vals)
    if mn == mx:
        pts = [(i * w / (len(vals)-1), h/2) for i in range(len(vals))]
    else:
        pts = [(i * w / (len(vals)-1), h - (v-mn)/(mx-mn)*h) for i,v in enumerate(vals)]
    d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x,y in pts)
    last_x, last_y = pts[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.4" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity=".8"/>'
            f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2" fill="{color}"/>'
            f'</svg>')

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

# ── 레짐 ─────────────────────────────────────────────────────
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

# ── KPI 카드 ─────────────────────────────────────────────────
CS = "background:#0D1520;border:1px solid #1A2535;border-radius:8px;padding:11px 12px 10px;font-family:'JetBrains Mono',monospace"
LS = "font-size:9px;color:#4E5F74;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:5px"
VS = "font-size:18px;font-weight:600;color:#fff;line-height:1.2;margin-bottom:3px"
DS = "font-size:9px;font-weight:500"

def kcard(label, ind, df, fmt=".2f", inv=False, spk_color="#00E5CC"):
    r = lat(df, ind)
    if r is None:
        return f'<div style="{CS}"><div style="{LS}">{label}</div><div style="{VS}">—</div></div>'
    val = r["value"]; d = dlt(df, ind); vs = format(val, fmt)
    if d is not None:
        clr = ("#00E5CC" if d>0 else "#EF4444") if inv else ("#EF4444" if d>0 else "#00E5CC")
        dh = f'<div style="{DS};color:{clr}">{"+" if d>0 else ""}{d:.2f}</div>'
    else:
        dh = f'<div style="{DS};color:#4E5F74">—</div>'
    spk_html = spark(df, ind, color=spk_color)
    spk_div = f'<div style="opacity:.55;margin-top:2px">{spk_html}</div>' if spk_html else ""
    return f'''<div style="{CS}">
        <div style="{LS}">{label}</div>
        <div style="display:flex;justify-content:space-between;align-items:flex-end">
            <div>
                <div style="{VS}">{vs}</div>
                {dh}
            </div>
            {spk_div}
        </div>
    </div>'''

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
    badge = f'<span style="background:{c}20;color:{c};border:1px solid {c}40;padding:1px 5px;border-radius:3px;font-size:8px;font-weight:600;letter-spacing:1px;text-transform:uppercase">{t}</span>'
    spk_html = spark(sentiment, "FEAR_GREED", color=c)
    spk_div = f'<div style="opacity:.55;margin-top:2px">{spk_html}</div>' if spk_html else ""
    return f'''<div style="{CS}">
        <div style="{LS}">공포탐욕</div>
        <div style="display:flex;justify-content:space-between;align-items:flex-end">
            <div>
                <div style="{VS}">{v:.0f}</div>
                {badge}
            </div>
            {spk_div}
        </div>
    </div>'''

kpi_specs = [
    ("VIX",     "VIX",    market, ".1f",  True,  "#EF4444"),
    ("SOX",     "SOX",    market, ",.0f", False, "#3B82F6"),
    ("S&P 500", "SPX",    market, ",.0f", False, "#8B5CF6"),
    ("KOSPI",   "KOSPI",  market, ",.0f", False, "#00E5CC"),
    ("USD/KRW", "USDKRW", market, ",.0f", True,  "#F97316"),
    ("US 10Y",  "US_10Y", fred,   ".2f",  True,  "#3B82F6"),
    ("HY OAS",  "HY_OAS", fred,   ".2f",  True,  "#F59E0B"),
]

kcols = st.columns(8)
for col,(lbl,ind,df,fmt,inv,spk_c) in zip(kcols, kpi_specs):
    with col:
        st.markdown(kcard(lbl,ind,df,fmt,inv,spk_c), unsafe_allow_html=True)
with kcols[7]:
    st.markdown(fgcard(), unsafe_allow_html=True)

def sh(id_, name):
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin:28px 0 12px;font-family:'JetBrains Mono',monospace">
  <span style="font-family:'Syne',sans-serif;font-size:9px;font-weight:700;color:#070B0F;background:#00E5CC;padding:1px 6px;border-radius:3px;letter-spacing:.8px">{id_}</span>
  <span style="font-family:'Syne',sans-serif;font-size:12px;font-weight:600;color:#8B98A8;letter-spacing:1px">{name}</span>
  <div style="flex:1;height:1px;background:#1A2535"></div>
</div>""", unsafe_allow_html=True)

# ── A: 위험·심리 ──────────────────────────────────────────────
sh("A","글로벌 위험 & 심리")
c1,c2 = st.columns(2)
with c1:
    fig = lc([(ser(market,"VIX"),"VIX","#EF4444"),(ser(fred,"HY_OAS"),"HY OAS %","#F59E0B")],
             "VIX · HY 신용스프레드")
    fig.add_hrect(y0=25,y1=100,fillcolor="rgba(239,68,68,0.03)",line_width=0)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    # F&G 게이지 — 데이터 포인트 수 무관하게 항상 현재값 표시
    fg_row = lat(sentiment, "FEAR_GREED")
    if fg_row is not None:
        fv = fg_row["value"]
        if fv<25:   fc,fl="#EF4444","극도의 공포"
        elif fv<45: fc,fl="#F97316","공포"
        elif fv<55: fc,fl="#EAB308","중립"
        elif fv<75: fc,fl="#84CC16","탐욕"
        else:       fc,fl="#22C55E","극도의 탐욕"

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=fv,
            domain={"x":[0,1],"y":[0,1]},
            number={"font":{"size":42,"family":"JetBrains Mono","color":fc}},
            title={"text":fl,"font":{"size":13,"family":"Syne","color":fc}},
            gauge={
                "axis":{"range":[0,100],"tickwidth":0,"tickvals":[0,25,50,75,100],
                        "tickfont":{"size":9,"color":"#4E5F74"}},
                "bar":{"color":fc,"thickness":0.22},
                "bgcolor":"#0D1520","borderwidth":0,
                "steps":[
                    {"range":[0,25],  "color":"rgba(239,68,68,0.15)"},
                    {"range":[25,45], "color":"rgba(249,115,22,0.12)"},
                    {"range":[45,55], "color":"rgba(234,179,8,0.12)"},
                    {"range":[55,75], "color":"rgba(132,204,22,0.12)"},
                    {"range":[75,100],"color":"rgba(34,197,94,0.15)"},
                ],
                "threshold":{"line":{"color":"#fff","width":2},"thickness":0.7,"value":fv},
            },
        ))
        fig.update_layout(paper_bgcolor="#0D1520",height=262,
                          margin=dict(l=30,r=30,t=20,b=20),
                          font=dict(family="JetBrains Mono",color="#4E5F74"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("공포탐욕지수 데이터 수집 중")

# ── B: 금리·달러 ─────────────────────────────────────────────
sh("B","미국 금리 & 달러")
c1,c2 = st.columns(2)
with c1:
    fig = lc([(ser(fred,"US_10Y"),"US 10Y %","#3B82F6"),
              (ser(fred,"T10Y2Y_SPREAD"),"2Y-10Y 스프레드","#F59E0B")],
             "미국 국채금리 · 스프레드",zero=True)
    fig.add_hrect(y0=4.5,y1=10,fillcolor="rgba(245,158,11,0.03)",line_width=0)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    st.plotly_chart(lc([(ser(market,"DXY"),"DXY","#8B5CF6")],"DXY 달러 인덱스"),
                    use_container_width=True)

# ── C: 한국 시장 ─────────────────────────────────────────────
sh("C","한국 시장")
c1,c2 = st.columns(2)
with c1:
    fig = lc([(ser(market,"USDKRW"),"USD/KRW","#F97316")],"원달러 환율")
    fig.add_hrect(y0=1400,y1=2500,fillcolor="rgba(239,68,68,0.03)",line_width=0)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    st.plotly_chart(lc([(ser(market,"KOSPI"),"KOSPI","#00E5CC")],"KOSPI"),
                    use_container_width=True)

# ── D: 글로벌 모멘텀 ─────────────────────────────────────────
sh("D","글로벌 주식 모멘텀")
c1,c2 = st.columns(2)
with c1:
    st.plotly_chart(lc([(ser(market,"SOX"),"SOX 반도체","#3B82F6")],
                       "필라델피아 반도체 (SOX)"), use_container_width=True)
with c2:
    st.plotly_chart(lc([(ser(market,"SPX"),"S&P 500","#8B5CF6")],"S&P 500"),
                    use_container_width=True)

# ── E: 미국 월간 매크로 ──────────────────────────────────────
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
        nl = {k:v for k,v in BASE.items() if k!="legend"}
        fig = go.Figure(go.Bar(x=nm["date"],y=nm["mom"],
            marker_color=["#22C55E" if v>=0 else "#EF4444" for v in nm["mom"]],
            hovertemplate="<b>NFP MoM</b> %{y:,.0f}천명<extra></extra>"))
        fig.update_layout(title=dict(text="비농업 고용 MoM (천명)",
                          font=dict(size=11,color="#6B7280"),x=0),
                          height=262,showlegend=False,**nl)
        st.plotly_chart(fig, use_container_width=True)

# ── F: ECOS ──────────────────────────────────────────────────
sh("F","한국 매크로 · ECOS")
if ecos.empty:
    st.info("ECOS 데이터 없음")
else:
    cols_list=[c for c in ["CLASS_NAME","KEYSTAT_NAME","DATA_VALUE","UNIT_NAME","CYCLE"] if c in ecos.columns]
    if cols_list:
        rows=""
        for _,r in ecos[cols_list].iterrows():
            rows+=(f'<tr>'
                   f'<td style="padding:.4rem .85rem;font-size:10px;color:#4E5F74;border-bottom:1px solid rgba(26,37,53,.5)">{r.get("CLASS_NAME","")}</td>'
                   f'<td style="padding:.4rem .85rem;font-size:11px;color:#D4DCE8;border-bottom:1px solid rgba(26,37,53,.5)">{r.get("KEYSTAT_NAME","")}</td>'
                   f'<td style="padding:.4rem .85rem;font-size:11px;font-weight:600;color:#fff;text-align:right;border-bottom:1px solid rgba(26,37,53,.5)">{r.get("DATA_VALUE","")}</td>'
                   f'<td style="padding:.4rem .85rem;font-size:10px;color:#4E5F74;text-align:right;border-bottom:1px solid rgba(26,37,53,.5)">{r.get("UNIT_NAME","")}</td>'
                   f'<td style="padding:.4rem .85rem;font-size:10px;color:#4E5F74;text-align:right;border-bottom:1px solid rgba(26,37,53,.5)">{r.get("CYCLE","")}</td>'
                   f'</tr>')
        st.markdown(f"""
<div style="background:#0D1520;border:1px solid #1A2535;border-radius:8px;overflow:hidden;font-family:'JetBrains Mono',monospace">
<table style="width:100%;border-collapse:collapse">
  <thead><tr style="background:#111D2E">
    <th style="padding:.55rem .85rem;text-align:left;font-size:9px;color:#4E5F74;letter-spacing:1.5px;text-transform:uppercase;font-weight:500;border-bottom:1px solid #1A2535;width:18%">분류</th>
    <th style="padding:.55rem .85rem;text-align:left;font-size:9px;color:#4E5F74;letter-spacing:1.5px;text-transform:uppercase;font-weight:500;border-bottom:1px solid #1A2535;width:42%">지표명</th>
    <th style="padding:.55rem .85rem;text-align:right;font-size:9px;color:#4E5F74;letter-spacing:1.5px;text-transform:uppercase;font-weight:500;border-bottom:1px solid #1A2535;width:15%">현재값</th>
    <th style="padding:.55rem .85rem;text-align:right;font-size:9px;color:#4E5F74;letter-spacing:1.5px;text-transform:uppercase;font-weight:500;border-bottom:1px solid #1A2535;width:12%">단위</th>
    <th style="padding:.55rem .85rem;text-align:right;font-size:9px;color:#4E5F74;letter-spacing:1.5px;text-transform:uppercase;font-weight:500;border-bottom:1px solid #1A2535;width:8%">주기</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table></div>""", unsafe_allow_html=True)

st.markdown("""
<div style="margin-top:2.5rem;padding-top:.85rem;border-top:1px solid #1A2535;font-size:10px;color:#4E5F74;text-align:center;letter-spacing:1px;font-family:'JetBrains Mono',monospace">
  FRED &nbsp;·&nbsp; yfinance &nbsp;·&nbsp; CNN Fear &amp; Greed &nbsp;·&nbsp; 한국은행 ECOS &nbsp;·&nbsp; 매일 KST 07:00 자동 수집
</div>
""", unsafe_allow_html=True)
