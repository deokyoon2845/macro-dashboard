"""
Deokyoon's Monitoring — v5
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Deokyoon's Monitoring", page_icon="◈",
                   layout="wide", initial_sidebar_state="collapsed")

BG="#0B0F1A"; CARD="#131B2E"; CARD2="#0F1421"; BORD="#1E2D4A"
AC="#00D4AA"; RED="#EF4444"; AMB="#F59E0B"
BLU="#3B82F6"; PUR="#8B5CF6"; ORG="#F97316"; GRN="#22C55E"
TEXT="#E2E8F0"; MUT="#5C7090"

st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Pretendard:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
html,body,[class*="css"]{{background:{BG}!important;color:{TEXT}!important;font-family:'Pretendard','JetBrains Mono',sans-serif!important}}
.block-container{{padding:0 2rem 3rem!important;max-width:100%!important;background:{BG}!important}}
[data-testid="stAppViewContainer"]{{background:{BG}!important}}
[data-testid="stHeader"]{{background:{BG}!important;border-bottom:1px solid {BORD}!important}}
section[data-testid="stSidebar"]{{display:none}}
#MainMenu,footer,header{{visibility:hidden}}
div[data-testid="stVerticalBlock"]>div{{gap:0!important}}
.stPlotlyChart{{border-radius:12px;overflow:hidden}}
</style>
""", unsafe_allow_html=True)

DATA_DIR = Path(__file__).parent / "data"

@st.cache_data(ttl=3600)
def load(fn):
    f = DATA_DIR / fn
    if not f.exists(): return pd.DataFrame()
    df = pd.read_parquet(f)
    if "date" in df.columns: df["date"] = pd.to_datetime(df["date"])
    return df

fred=load("fred_indicators.parquet"); market=load("market_prices.parquet")
sentiment=load("sentiment.parquet"); ecos=load("ecos_latest.parquet")

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
    return (s.iloc[-1]["value"]-s.iloc[-2]["value"]) if len(s)>=2 else None

# ── 스파크라인 (그라디언트 fill 포함) ─────────────────────────
def spark(df, ind, color=AC, days=90, w=88, h=36):
    s = ser(df, ind, days)
    vals = s["value"].dropna().tolist() if not s.empty else []
    if len(vals) < 3: return ""
    mn,mx = min(vals),max(vals); mg=4
    if mn==mx:
        pts = [(round(i*w/(len(vals)-1),1), h/2) for i in range(len(vals))]
    else:
        pts = [(round(i*w/(len(vals)-1),1),
                round(h-mg-(v-mn)/(mx-mn)*(h-mg*2),1)) for i,v in enumerate(vals)]
    ld = "M "+" L ".join(f"{x},{y}" for x,y in pts)
    fd = ld+f" L {pts[-1][0]},{h} L {pts[0][0]},{h} Z"
    gid = f"g{''.join(c for c in ind if c.isalpha())[:5]}"
    lx,ly = pts[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity="0.3"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
            f'</linearGradient></defs>'
            f'<path d="{fd}" fill="url(#{gid})" stroke="none"/>'
            f'<path d="{ld}" fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{lx}" cy="{ly}" r="2.5" fill="{color}"/>'
            f'</svg>')

# ── Plotly 공통 레이아웃 ──────────────────────────────────────
G="#141E30"
def base_layout(title="", h=270):
    return dict(
        paper_bgcolor=CARD, plot_bgcolor=BG,
        font=dict(family="JetBrains Mono",size=10,color=MUT),
        title=dict(text=title,font=dict(size=11,color="#8B9AB5"),x=0.01,y=0.97),
        height=h, margin=dict(l=8,r=8,t=32,b=8),
        legend=dict(orientation="h",y=1.08,x=0,font=dict(size=9,color="#8B9AB5"),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=CARD2,bordercolor=BORD,font=dict(family="JetBrains Mono",size=11)),
        xaxis=dict(showgrid=True,gridcolor=G,gridwidth=1,zeroline=False,showline=False,tickfont=dict(size=9)),
        yaxis=dict(showgrid=True,gridcolor=G,gridwidth=1,zeroline=False,showline=False,tickfont=dict(size=9)),
    )

def lc(traces, title="", h=270, zero=False):
    fig = go.Figure()
    for df,nm,clr in traces:
        if df.empty: continue
        fig.add_trace(go.Scatter(x=df["date"],y=df["value"],name=nm,
            line=dict(color=clr,width=2),
            hovertemplate=f"<b>{nm}</b> %{{y:.2f}}<extra></extra>"))
    if zero: fig.add_hline(y=0,line_dash="dot",line_color="#243550",line_width=1)
    fig.update_layout(**base_layout(title,h))
    return fig

# ── 레짐 ─────────────────────────────────────────────────────
def regime():
    v=lat(market,"VIX"); h=lat(fred,"HY_OAS")
    if v is None or h is None: return "neu","NEUTRAL","데이터 수집 중"
    vv,hv = v["value"],h["value"]
    if vv>28 or hv>5.5:    return "risk","RISK-OFF",f"VIX {vv:.1f} · HY {hv:.2f}% — 위험 회피 국면"
    elif vv<16 and hv<3.5: return "on","RISK-ON",  f"VIX {vv:.1f} · HY {hv:.2f}% — 위험 선호 국면"
    else:                  return "neu","NEUTRAL",  f"VIX {vv:.1f} · HY {hv:.2f}% — 관망 국면"

rc,rt,rn = regime()
RC = {"risk":(RED,"rgba(239,68,68,.12)","rgba(239,68,68,.25)"),
      "on":  (AC, f"rgba(0,212,170,.1)",  f"rgba(0,212,170,.25)"),
      "neu": (AMB,"rgba(245,158,11,.1)", "rgba(245,158,11,.25)")}
rc_txt,rc_bg,rc_brd = RC[rc]

# ── 상단 네비 바 ──────────────────────────────────────────────
now = datetime.now()
st.markdown(f"""
<div style="background:{CARD2};border-bottom:1px solid {BORD};padding:14px 2rem;
  display:flex;justify-content:space-between;align-items:center;
  margin:0 -2rem 1.8rem;position:sticky;top:0;z-index:99">
  <div style="display:flex;align-items:center;gap:12px">
    <span style="font-family:'Syne',sans-serif;font-size:18px;font-weight:800;color:{TEXT};letter-spacing:-.02em">
      <span style="color:{AC}">D</span>eokyoon's&nbsp;<span style="color:{AC}">Monitoring</span>
    </span>
    <span style="width:1px;height:16px;background:{BORD};display:inline-block;margin:0 4px"></span>
    <span style="font-size:10px;color:{MUT};letter-spacing:.04em">한미 매크로 모니터링</span>
  </div>
  <div style="display:flex;align-items:center;gap:16px">
    <span style="background:{rc_bg};color:{rc_txt};border:1px solid {rc_brd};
      padding:4px 12px;border-radius:20px;font-size:10px;font-weight:600;letter-spacing:1.2px;
      text-transform:uppercase;font-family:'JetBrains Mono',monospace">● {rt}</span>
    <span style="font-size:10px;color:{MUT};font-family:'JetBrains Mono',monospace">
      {now.strftime("%Y-%m-%d &nbsp;·&nbsp; %H:%M")} KST
    </span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── KPI 메트릭 카드 ───────────────────────────────────────────
def kcard(label, ind, df, fmt=".2f", inv=False, color=AC):
    r = lat(df, ind)
    CS = (f"background:{CARD};border:1px solid {BORD};border-radius:12px;"
          f"padding:14px 16px 12px;font-family:'JetBrains Mono',monospace;"
          f"border-left:3px solid {color}")
    if r is None:
        return (f'<div style="{CS}">'
                f'<div style="font-size:9px;color:{MUT};letter-spacing:1.5px;'
                f'text-transform:uppercase;margin-bottom:6px">{label}</div>'
                f'<div style="font-size:20px;font-weight:700;color:{TEXT}">—</div></div>')
    val=r["value"]; d=dlt(df,ind); vs=format(val,fmt)
    if d is not None:
        clr=(AC if d>0 else RED) if inv else (RED if d>0 else AC)
        sym="▲" if d>0 else "▼"
        dh=(f'<div style="font-size:10px;font-weight:600;color:{clr};margin-top:3px">'
            f'{sym} {abs(d):.2f}</div>')
    else:
        dh=f'<div style="font-size:10px;color:{MUT};margin-top:3px">—</div>'
    spk=spark(df,ind,color=color)
    spkh=(f'<div style="margin-top:10px;opacity:.75">{spk}</div>') if spk else ""
    return (f'<div style="{CS}">'
            f'<div style="font-size:9px;color:{MUT};letter-spacing:1.5px;text-transform:uppercase;margin-bottom:5px">{label}</div>'
            f'<div style="font-size:20px;font-weight:700;color:{TEXT};line-height:1.1">{vs}</div>'
            f'{dh}{spkh}</div>')

def fgcard():
    r = lat(sentiment,"FEAR_GREED")
    CS = (f"background:{CARD};border:1px solid {BORD};border-radius:12px;"
          f"padding:14px 16px 12px;font-family:'JetBrains Mono',monospace")
    if r is None:
        return (f'<div style="{CS};border-left:3px solid {MUT}">'
                f'<div style="font-size:9px;color:{MUT};letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px">공포탐욕</div>'
                f'<div style="font-size:20px;font-weight:700;color:{TEXT}">—</div></div>')
    v=r["value"]
    if v<25:   c,t=RED,"극도의 공포"
    elif v<45: c,t=ORG,"공포"
    elif v<55: c,t=AMB,"중립"
    elif v<75: c,t="#84CC16","탐욕"
    else:      c,t=GRN,"극도의 탐욕"
    badge=(f'<span style="background:{c}20;color:{c};border:1px solid {c}40;'
           f'padding:2px 7px;border-radius:10px;font-size:9px;font-weight:600;'
           f'letter-spacing:.5px">{t}</span>')
    spk=spark(sentiment,"FEAR_GREED",color=c)
    spkh=f'<div style="margin-top:10px;opacity:.75">{spk}</div>' if spk else ""
    return (f'<div style="{CS};border-left:3px solid {c}">'
            f'<div style="font-size:9px;color:{MUT};letter-spacing:1.5px;text-transform:uppercase;margin-bottom:5px">공포탐욕</div>'
            f'<div style="font-size:20px;font-weight:700;color:{TEXT};line-height:1.1;margin-bottom:3px">{v:.0f}</div>'
            f'{badge}{spkh}</div>')

kpi_specs = [
    ("VIX",     "VIX",    market, ".1f",  True,  RED),
    ("SOX",     "SOX",    market, ",.0f", False, BLU),
    ("S&P 500", "SPX",    market, ",.0f", False, PUR),
    ("KOSPI",   "KOSPI",  market, ",.0f", False, AC),
    ("USD/KRW", "USDKRW", market, ",.0f", True,  ORG),
    ("US 10Y",  "US_10Y", fred,   ".2f",  True,  BLU),
    ("HY OAS",  "HY_OAS", fred,   ".2f",  True,  AMB),
]

kcols = st.columns(8)
for col,(lbl,ind,df,fmt,inv,c) in zip(kcols, kpi_specs):
    with col:
        st.markdown(kcard(lbl,ind,df,fmt,inv,c), unsafe_allow_html=True)
with kcols[7]:
    st.markdown(fgcard(), unsafe_allow_html=True)

st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

# ── 섹션 헤더 헬퍼 ──────────────────────────────────────────
def sh(id_, name, sub=""):
    sub_html = f'<span style="font-size:10px;color:{MUT};margin-left:8px">{sub}</span>' if sub else ""
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin:2rem 0 .9rem;font-family:'Pretendard',sans-serif">
  <span style="font-family:'Syne',sans-serif;font-size:10px;font-weight:700;
    color:{BG};background:{AC};padding:2px 8px;border-radius:5px;letter-spacing:.8px">{id_}</span>
  <span style="font-size:13px;font-weight:600;color:{TEXT};letter-spacing:.5px">{name}</span>
  {sub_html}
  <div style="flex:1;height:1px;background:{BORD}"></div>
</div>""", unsafe_allow_html=True)

def chart_col(fig):
    st.markdown(f'<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;overflow:hidden;padding:4px">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── A: 위험·심리 ──────────────────────────────────────────────
sh("A","글로벌 위험 & 심리","Risk Sentiment")
c1,c2 = st.columns(2)
with c1:
    fig = lc([(ser(market,"VIX"),"VIX",RED),(ser(fred,"HY_OAS"),"HY OAS %",AMB)],
             "VIX · HY 신용스프레드")
    fig.add_hrect(y0=25,y1=100,fillcolor="rgba(239,68,68,0.04)",line_width=0)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    fg_row = lat(sentiment,"FEAR_GREED")
    if fg_row is not None:
        fv=fg_row["value"]
        if fv<25:   fc="#EF4444"; fl="극도의 공포"
        elif fv<45: fc="#F97316"; fl="공포"
        elif fv<55: fc="#EAB308"; fl="중립"
        elif fv<75: fc="#84CC16"; fl="탐욕"
        else:       fc="#22C55E"; fl="극도의 탐욕"
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=fv,
            domain={"x":[0,1],"y":[0,1]},
            number={"font":{"size":44,"family":"JetBrains Mono","color":fc}},
            title={"text":fl,"font":{"size":14,"family":"Syne","color":fc}},
            gauge={
                "axis":{"range":[0,100],"tickwidth":0,
                        "tickvals":[0,25,50,75,100],"tickfont":{"size":9,"color":MUT}},
                "bar":{"color":fc,"thickness":0.22},
                "bgcolor":BG,"borderwidth":0,
                "steps":[{"range":[0,25],  "color":"rgba(239,68,68,0.15)"},
                         {"range":[25,45], "color":"rgba(249,115,22,0.12)"},
                         {"range":[45,55], "color":"rgba(234,179,8,0.12)"},
                         {"range":[55,75], "color":"rgba(132,204,22,0.12)"},
                         {"range":[75,100],"color":"rgba(34,197,94,0.15)"}],
                "threshold":{"line":{"color":"#fff","width":2},"thickness":0.7,"value":fv},
            }))
        fig.update_layout(paper_bgcolor=CARD,height=270,
                          margin=dict(l=30,r=30,t=20,b=20),
                          font=dict(family="JetBrains Mono",color=MUT))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("공포탐욕지수 데이터 수집 중")

# ── B: 금리·달러 ─────────────────────────────────────────────
sh("B","미국 금리 & 달러","Interest Rate · Dollar")
c1,c2 = st.columns(2)
with c1:
    fig = lc([(ser(fred,"US_10Y"),"US 10Y %",BLU),
              (ser(fred,"T10Y2Y_SPREAD"),"2Y-10Y 스프레드",AMB)],
             "미국 국채금리 · 스프레드",zero=True)
    fig.add_hrect(y0=4.5,y1=10,fillcolor="rgba(245,158,11,0.03)",line_width=0)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    st.plotly_chart(lc([(ser(market,"DXY"),"DXY",PUR)],"DXY 달러 인덱스"),
                    use_container_width=True)

# ── C: 한국 시장 ─────────────────────────────────────────────
sh("C","한국 시장","Korean Market")
c1,c2 = st.columns(2)
with c1:
    fig = lc([(ser(market,"USDKRW"),"USD/KRW",ORG)],"원달러 환율")
    fig.add_hrect(y0=1400,y1=2500,fillcolor="rgba(239,68,68,0.03)",line_width=0)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    st.plotly_chart(lc([(ser(market,"KOSPI"),"KOSPI",AC)],"KOSPI"),
                    use_container_width=True)

# ── D: 글로벌 모멘텀 ─────────────────────────────────────────
sh("D","글로벌 주식 모멘텀","Global Equity Momentum")
c1,c2 = st.columns(2)
with c1:
    st.plotly_chart(lc([(ser(market,"SOX"),"SOX 반도체",BLU)],
                       "필라델피아 반도체 (SOX)"), use_container_width=True)
with c2:
    st.plotly_chart(lc([(ser(market,"SPX"),"S&P 500",PUR)],"S&P 500"),
                    use_container_width=True)

# ── E: 미국 월간 매크로 ──────────────────────────────────────
sh("E","미국 월간 매크로","US Monthly Macro")
c1,c2 = st.columns(2)
with c1:
    cpi = ser(fred,"US_CORE_CPI",days=365*6)
    if not cpi.empty:
        cpi=cpi.copy(); cpi["yoy"]=cpi["value"].pct_change(12)*100
        cy=cpi.dropna(subset=["yoy"])[["date","yoy"]].rename(columns={"yoy":"value"})
        fig=lc([(cy,"Core CPI YoY %",ORG)],"미국 Core CPI YoY")
        fig.add_hline(y=2.0,line_dash="dot",line_color="#243550",line_width=1.5,
                      annotation_text="2% 목표",annotation_font_color=MUT,
                      annotation_position="bottom right")
        st.plotly_chart(fig, use_container_width=True)
with c2:
    nfp=ser(fred,"US_NFP",days=365*5)
    if not nfp.empty:
        nfp=nfp.copy(); nfp["mom"]=nfp["value"].diff()
        nm=nfp.dropna(subset=["mom"])
        bl=base_layout("비농업 고용 MoM (천명)",270)
        bl.pop("legend",None)
        fig=go.Figure(go.Bar(x=nm["date"],y=nm["mom"],
            marker_color=[GRN if v>=0 else RED for v in nm["mom"]],
            hovertemplate="<b>NFP MoM</b> %{y:,.0f}천명<extra></extra>"))
        fig.update_layout(showlegend=False,**bl)
        st.plotly_chart(fig, use_container_width=True)

# ── F: ECOS ──────────────────────────────────────────────────
sh("F","한국 매크로 · ECOS","Bank of Korea Statistics")
if ecos.empty:
    st.info("ECOS 데이터 없음")
else:
    cl=[c for c in ["CLASS_NAME","KEYSTAT_NAME","DATA_VALUE","UNIT_NAME","CYCLE"] if c in ecos.columns]
    if cl:
        rows=""
        for _,r in ecos[cl].iterrows():
            rows+=(f'<tr style="border-bottom:1px solid rgba(30,45,74,.6)">'
                   f'<td style="padding:.45rem 1rem;font-size:10px;color:{MUT}">{r.get("CLASS_NAME","")}</td>'
                   f'<td style="padding:.45rem 1rem;font-size:11px;color:{TEXT}">{r.get("KEYSTAT_NAME","")}</td>'
                   f'<td style="padding:.45rem 1rem;font-size:12px;font-weight:700;color:#fff;text-align:right">{r.get("DATA_VALUE","")}</td>'
                   f'<td style="padding:.45rem 1rem;font-size:10px;color:{MUT};text-align:right">{r.get("UNIT_NAME","")}</td>'
                   f'<td style="padding:.45rem 1rem;font-size:10px;color:{MUT};text-align:right">{r.get("CYCLE","")}</td>'
                   f'</tr>')
        th_s = f"padding:.65rem 1rem;text-align:left;font-size:9px;color:{MUT};letter-spacing:1.5px;text-transform:uppercase;font-weight:500;border-bottom:1px solid {BORD}"
        st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;overflow:hidden;font-family:'JetBrains Mono',monospace">
<table style="width:100%;border-collapse:collapse">
  <thead><tr style="background:{CARD2}">
    <th style="{th_s};width:18%">분류</th>
    <th style="{th_s};width:42%">지표명</th>
    <th style="{th_s};width:15%;text-align:right">현재값</th>
    <th style="{th_s};width:12%;text-align:right">단위</th>
    <th style="{th_s};width:8%;text-align:right">주기</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table></div>""", unsafe_allow_html=True)

# ── 푸터 ─────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:3rem;padding-top:1rem;border-top:1px solid {BORD};
  font-size:10px;color:{MUT};text-align:center;letter-spacing:1px;
  font-family:'JetBrains Mono',monospace">
  FRED &nbsp;·&nbsp; yfinance &nbsp;·&nbsp; CNN Fear &amp; Greed &nbsp;·&nbsp; 한국은행 ECOS
  &nbsp;·&nbsp; 매일 KST 07:00 자동 수집
</div>
""", unsafe_allow_html=True)
