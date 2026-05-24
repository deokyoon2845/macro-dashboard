"""
Deokyoon's Monitoring — v6
빨간색=상승 / 파란색=하락 (한국 시장 관행)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Deokyoon's Monitoring",
                   page_icon="◈", layout="wide",
                   initial_sidebar_state="collapsed")

# ── 컬러 팔레트 ──────────────────────────────────────────────
BG   = "#0B0F1A"
CARD = "#131B2E"
C2   = "#0F1421"
BORD = "#1E2D4A"
UP   = "#DC2626"    # 빨간 = 상승
DN   = "#1D4ED8"    # 파란 = 하락
WT   = "#FFFFFF"    # 흰색 텍스트
MUT  = "#6B7280"    # 뮤트 텍스트
AMB  = "#F59E0B"
GOLD_C = "#F59E0B"
G    = "#141E30"    # 차트 그리드

# ── CSS ───────────────────────────────────────────────────────
st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
html,body,[class*="css"]{{background:{BG}!important;color:{WT}!important;
  font-family:'JetBrains Mono',monospace!important}}
.block-container{{padding:0 2rem 3rem!important;max-width:100%!important;background:{BG}!important}}
[data-testid="stAppViewContainer"]{{background:{BG}!important}}
[data-testid="stHeader"]{{background:{BG}!important;border-bottom:1px solid {BORD}!important}}
section[data-testid="stSidebar"]{{display:none}}
#MainMenu,footer,header{{visibility:hidden}}
p,span,div,label,th,td{{color:{WT}!important}}
</style>
""", unsafe_allow_html=True)

# ── 데이터 로드 ───────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"

@st.cache_data(ttl=3600)
def load(fn):
    f = DATA_DIR / fn
    if not f.exists(): return pd.DataFrame()
    df = pd.read_parquet(f)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df

fred=load("fred_indicators.parquet"); market=load("market_prices.parquet")
sentiment=load("sentiment.parquet");  ecos=load("ecos_latest.parquet")

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
    s = ser(df, ind, 15).sort_values("date")
    return (s.iloc[-1]["value"]-s.iloc[-2]["value"]) if len(s)>=2 else None

def pct_chg_1d(ind):
    s = ser(market, ind, 10).sort_values("date")
    if len(s)<2: return 0.0
    return round((s.iloc[-1]["value"]/s.iloc[-2]["value"]-1)*100, 2)

def get_ecos_val(keyword):
    if ecos.empty or "KEYSTAT_NAME" not in ecos.columns: return None
    r = ecos[ecos["KEYSTAT_NAME"].str.contains(keyword, na=False)]
    if r.empty: return None
    try: return float(str(r.iloc[0]["DATA_VALUE"]).replace(",",""))
    except: return None

# ── 지표 설명 ─────────────────────────────────────────────────
DESC = {
    "VIX":    "옵션 내재 변동성 | 25↑경계 · 30↑패닉 · 15↓안정",
    "FEAR_GREED":"0=극도공포 · 25=공포 · 50=중립 · 75=탐욕 · 100=극도탐욕",
    "SOX":    "美 반도체 대형주 지수 | 삼성·SK하이닉스 선행지표",
    "SPX":    "美 S&P500 | 글로벌 위험선호 기준점",
    "NASDAQ": "美 나스닥 | 기술·성장주 집중, 고금리에 민감",
    "KOSPI":  "한국 대형주 지수 | 외국인 수급에 고도 민감",
    "USDKRW": "원달러 환율 | 1,300↑주의 · 1,400↑위험 · 달러 강세=하락압력",
    "US_10Y": "美 10년 국채 | 전세계 자본비용 기준 | 4.5↑주식 밸류에이션 압박",
}

def up_dn(d):
    return UP if (d or 0) >= 0 else DN

# ── 스파크라인 SVG (그라디언트 fill) ──────────────────────────
def spark(df, ind, color=UP, days=90, w=80, h=30):
    s = ser(df, ind, days)
    vals = s["value"].dropna().tolist() if not s.empty else []
    if len(vals)<3: return "", "", ""
    mn,mx = min(vals),max(vals); mg=3
    if mn==mx:
        pts=[(round(i*w/(len(vals)-1),1),h/2) for i in range(len(vals))]
    else:
        pts=[(round(i*w/(len(vals)-1),1),
              round(h-mg-(v-mn)/(mx-mn)*(h-mg*2),1)) for i,v in enumerate(vals)]
    ld="M "+" L ".join(f"{x},{y}" for x,y in pts)
    fd=ld+f" L {pts[-1][0]},{h} L {pts[0][0]},{h} Z"
    gid=f"g{''.join(c for c in ind if c.isalpha())[:6]}"
    lx,ly=pts[-1]
    svg=(f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
         f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0%" stop-color="{color}" stop-opacity="0.25"/>'
         f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
         f'</linearGradient></defs>'
         f'<path d="{fd}" fill="url(#{gid})"/>'
         f'<path d="{ld}" fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
         f'<circle cx="{lx}" cy="{ly}" r="2.5" fill="{color}"/>'
         f'</svg>')
    start_dt = s["date"].iloc[0].strftime("%y.%m") if not s.empty else ""
    start_v  = f"{vals[0]:,.1f}" if vals else ""
    return svg, start_dt, start_v

# ── Plotly 기본 레이아웃 ──────────────────────────────────────
def BL(title="", h=262):
    return dict(
        paper_bgcolor=CARD, plot_bgcolor=BG,
        font=dict(family="JetBrains Mono",size=10,color=MUT),
        title=dict(text=title,font=dict(size=11,color="#8B9AB5"),x=0.01),
        height=h, margin=dict(l=8,r=8,t=32,b=8),
        legend=dict(orientation="h",y=1.08,x=0,font=dict(size=9,color="#8B9AB5"),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=C2,bordercolor=BORD,font=dict(family="JetBrains Mono",size=11)),
        xaxis=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT)),
        yaxis=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT)),
    )

def lc(traces, title="", h=262, zero=False):
    fig=go.Figure()
    for df,nm,clr in traces:
        if isinstance(df,pd.DataFrame) and not df.empty:
            fig.add_trace(go.Scatter(x=df["date"],y=df["value"],name=nm,
                line=dict(color=clr,width=1.8),
                hovertemplate=f"<b>{nm}</b> %{{y:.2f}}<extra></extra>"))
    if zero: fig.add_hline(y=0,line_dash="dot",line_color="#243550",line_width=1)
    fig.update_layout(**BL(title,h))
    return fig

# ── 히트맵 (Treemap) 데이터 ──────────────────────────────────
US_STOCKS = {
    "AAPL":  ("Apple",       3100),
    "MSFT":  ("Microsoft",   2900),
    "NVDA":  ("NVIDIA",      2800),
    "AMZN":  ("Amazon",      2000),
    "GOOGL": ("Alphabet",    2100),
    "META":  ("Meta",        1400),
    "BRK_B": ("Berkshire",    950),
    "TSLA":  ("Tesla",        800),
    "LLY":   ("Eli Lilly",    850),
    "JPM":   ("JPMorgan",     750),
}

KR_STOCKS = {
    "KR_SAMSUNG":    ("삼성전자",     270),
    "KR_SKHYNIX":    ("SK하이닉스",  130),
    "KR_LGENSOL":    ("LG에너지솔루션", 70),
    "KR_SAMBIO":     ("삼성바이오",    60),
    "KR_HYUNDAI":    ("현대차",        55),
    "KR_KIA":        ("기아",          45),
    "KR_CELLTRION":  ("셀트리온",      40),
    "KR_POSCO":      ("POSCO홀딩스",   38),
    "KR_KB":         ("KB금융",        35),
    "KR_NAVER":      ("NAVER",         28),
    "KR_ECOPROBM":   ("에코프로비엠",  25),
    "KR_SAMSDI":     ("삼성SDI",       25),
    "KR_ECOPRO":     ("에코프로",      20),
    "KR_KAKAO":      ("카카오",        22),
    "KR_LGCHEM":     ("LG화학",        24),
    "KR_HYUNDAIMOB": ("현대모비스",    20),
    "KR_LGELEC":     ("LG전자",        20),
    "KR_SHINHAN":    ("신한지주",      18),
    "KR_SAMSUNG_C":  ("삼성물산",      22),
    "KR_HANA":       ("하나금융",      18),
}

def make_treemap(stocks, title="", unit=""):
    labels,parents,values,colors,cdata=[],[],[],[],[]
    for ind,(name,mcap) in stocks.items():
        chg = pct_chg_1d(ind)
        labels.append(name)
        parents.append("")
        values.append(mcap)
        colors.append(chg)
        sign="▲" if chg>=0 else "▼"
        cdata.append(f"{sign}{abs(chg):.2f}%")

    fig=go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        customdata=cdata,
        texttemplate="<b>%{label}</b><br>%{customdata}",
        textfont=dict(size=12, color=WT),
        marker=dict(
            colors=colors,
            colorscale=[
                [0.0, "#1D4ED8"],[0.35,"#3B82F6"],
                [0.45, C2],      [0.55, C2],
                [0.65, UP],      [1.0, "#7F1D1D"],
            ],
            cmid=0, cmin=-5, cmax=5, showscale=True,
            colorbar=dict(title="전일대비",ticksuffix="%",
                         thickness=12,len=0.5,
                         tickfont=dict(size=9,color=MUT),
                         titlefont=dict(size=9,color=MUT)),
        ),
        hovertemplate="<b>%{label}</b><br>전일대비: %{customdata}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title,font=dict(size=11,color="#8B9AB5"),x=0.01),
        paper_bgcolor=CARD, height=400, margin=dict(l=0,r=0,t=30,b=0))
    return fig

# ── 섹션 헤더 ─────────────────────────────────────────────────
def sh(num, name_ko, name_en=""):
    en_html = f'<span style="font-size:10px;color:{MUT};margin-left:6px">{name_en}</span>' if name_en else ""
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin:2.2rem 0 .9rem;font-family:'JetBrains Mono',monospace">
  <span style="font-family:'Syne',sans-serif;font-size:10px;font-weight:700;
    color:{BG};background:#3B82F6;padding:2px 8px;border-radius:5px;letter-spacing:.8px">{num}</span>
  <span style="font-size:13px;font-weight:600;color:{WT};letter-spacing:.5px">{name_ko}</span>
  {en_html}
  <div style="flex:1;height:1px;background:{BORD}"></div>
</div>""", unsafe_allow_html=True)

# ── 레짐 계산 ─────────────────────────────────────────────────
def regime():
    v=lat(market,"VIX"); h=lat(fred,"HY_OAS")
    if v is None or h is None: return "neu","NEUTRAL","데이터 수집 중"
    vv,hv=v["value"],h["value"]
    if vv>28 or hv>5.5:    return "risk","RISK-OFF",f"VIX {vv:.1f} · HY {hv:.2f}% — 위험 회피 국면"
    elif vv<16 and hv<3.5: return "on","RISK-ON",  f"VIX {vv:.1f} · HY {hv:.2f}% — 위험 선호 국면"
    else:                  return "neu","NEUTRAL",  f"VIX {vv:.1f} · HY {hv:.2f}% — 관망 국면"
rc,rt,rn=regime()
RC={"risk":(UP,"rgba(220,38,38,.12)","rgba(220,38,38,.3)"),
    "on":  (DN,"rgba(29,78,216,.12)", "rgba(29,78,216,.3)"),
    "neu": (AMB,"rgba(245,158,11,.1)","rgba(245,158,11,.25)")}
rc_t,rc_bg,rc_bd=RC[rc]

# ═══════════════════════════════════════════════════════════
# == HEADER ==
# ═══════════════════════════════════════════════════════════
now=datetime.now()
st.markdown(f"""
<div style="background:{C2};border-bottom:1px solid {BORD};padding:13px 2rem;
  display:flex;justify-content:space-between;align-items:center;
  margin:0 -2rem 1.8rem;position:sticky;top:0;z-index:99">
  <div style="font-family:'Syne',sans-serif;font-size:18px;font-weight:800;color:{WT};letter-spacing:-.02em">
    <span style="color:{DN}">D</span>eokyoon's <span style="color:{DN}">Monitoring</span>
  </div>
  <div style="display:flex;align-items:center;gap:14px">
    <span style="background:{rc_bg};color:{rc_t};border:1px solid {rc_bd};
      padding:4px 12px;border-radius:20px;font-size:10px;font-weight:600;
      letter-spacing:1.2px;text-transform:uppercase">● {rt}</span>
    <span style="font-size:10px;color:{MUT}">{now.strftime("%Y-%m-%d  %H:%M")}</span>
  </div>
</div>
<div style="font-size:10px;color:{MUT};margin-bottom:1rem;font-family:'JetBrains Mono',monospace">
  {rn} &nbsp;·&nbsp; 빨간색=상승 · 파란색=하락
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# == KPI ROW ==
# ═══════════════════════════════════════════════════════════
KPI_SPECS=[
    ("VIX",    "VIX",    market, ".1f",   True),
    ("F&G",    "FEAR_GREED",sentiment,".0f",False),
    ("SOX",    "SOX",    market, ",.0f",  False),
    ("S&P500", "SPX",    market, ",.0f",  False),
    ("NASDAQ", "NASDAQ", market, ",.0f",  False),
    ("KOSPI",  "KOSPI",  market, ",.0f",  False),
    ("USD/KRW","USDKRW", market, ",.0f",  True),
    ("미국10Y","US_10Y", fred,   ".2f",   True),
]

def kcard_html(label, ind, df, fmt=".2f", inv=False):
    r=lat(df,ind)
    CS=(f"background:{CARD};border:1px solid {BORD};border-radius:10px;"
        f"padding:12px 13px 10px;font-family:'JetBrains Mono',monospace")
    desc=DESC.get(ind,"")
    desc_html=(f'<div style="font-size:8px;color:{MUT};margin-bottom:6px;line-height:1.3">{desc}</div>') if desc else ""
    if r is None:
        return f'<div style="{CS};border-left:3px solid {MUT}"><div style="font-size:9px;color:{MUT};letter-spacing:1.5px;text-transform:uppercase">{label}</div>{desc_html}<div style="font-size:20px;font-weight:700;color:{WT}">—</div></div>'
    val=r["value"]; d=dlt(df,ind); vs=format(val,fmt)
    clr=up_dn(d if not inv else (d*-1 if d else None))
    dh=""
    if d is not None:
        sign="▲" if d>0 else "▼"
        dh=(f'<div style="font-size:9px;font-weight:600;color:{clr};margin-top:2px">'
            f'{sign}{abs(d):.2f} <span style="color:{MUT};font-weight:400">(전일대비)</span></div>')
    spk_svg,spk_from,spk_v0=spark(df,ind,color=clr)
    spk_label=""
    if spk_from:
        spk_label=(f'<div style="display:flex;justify-content:space-between;'
                   f'font-size:8px;color:{MUT};margin-top:1px">'
                   f'<span>{spk_from} {spk_v0}</span><span>현재</span></div>')
    spk_block=(f'<div style="margin-top:8px;opacity:.75">{spk_svg}{spk_label}</div>') if spk_svg else ""
    return (f'<div style="{CS};border-left:3px solid {clr}">'
            f'<div style="font-size:9px;color:{MUT};letter-spacing:1.5px;text-transform:uppercase;margin-bottom:3px">{label}</div>'
            f'{desc_html}'
            f'<div style="font-size:20px;font-weight:700;color:{WT};line-height:1.1">{vs}</div>'
            f'{dh}{spk_block}</div>')

def fgcard_html():
    r=lat(sentiment,"FEAR_GREED")
    CS=(f"background:{CARD};border:1px solid {BORD};border-radius:10px;"
        f"padding:12px 13px 10px;font-family:'JetBrains Mono',monospace")
    desc=DESC.get("FEAR_GREED","")
    dh=(f'<div style="font-size:8px;color:{MUT};margin-bottom:6px;line-height:1.3">{desc}</div>')
    if r is None:
        return f'<div style="{CS};border-left:3px solid {MUT}"><div style="font-size:9px;color:{MUT};letter-spacing:1.5px;text-transform:uppercase">F&G</div>{dh}<div style="font-size:20px;font-weight:700;color:{WT}">—</div></div>'
    v=r["value"]
    if v<25:   c="F&G"
    elif v<45: c="F&G"
    else: c="F&G"
    if v<25:   fc=UP;    ft="극도의 공포"
    elif v<45: fc="#F97316"; ft="공포"
    elif v<55: fc=AMB;   ft="중립"
    elif v<75: fc="#84CC16"; ft="탐욕"
    else:      fc="#16A34A"; ft="극도의 탐욕"
    badge=(f'<span style="background:{fc}20;color:{fc};border:1px solid {fc}40;'
           f'padding:2px 7px;border-radius:10px;font-size:9px;font-weight:600">{ft}</span>')
    spk_svg,spk_from,spk_v0=spark(sentiment,"FEAR_GREED",color=fc)
    spk_label=""
    if spk_from:
        spk_label=(f'<div style="display:flex;justify-content:space-between;font-size:8px;color:{MUT};margin-top:1px">'
                   f'<span>{spk_from} {spk_v0}</span><span>현재</span></div>')
    spk_block=f'<div style="margin-top:8px;opacity:.75">{spk_svg}{spk_label}</div>' if spk_svg else ""
    return (f'<div style="{CS};border-left:3px solid {fc}">'
            f'<div style="font-size:9px;color:{MUT};letter-spacing:1.5px;text-transform:uppercase;margin-bottom:3px">F&G</div>'
            f'{dh}'
            f'<div style="font-size:20px;font-weight:700;color:{WT};line-height:1.1;margin-bottom:3px">{v:.0f}</div>'
            f'{badge}{spk_block}</div>')

kcols=st.columns(8)
for col,(lbl,ind,df,fmt,inv) in zip(kcols,KPI_SPECS[:-1]):
    with col:
        st.markdown(kcard_html(lbl,ind,df,fmt,inv), unsafe_allow_html=True)
with kcols[7]:
    lbl,ind,df,fmt,inv=KPI_SPECS[-1]
    with kcols[7]:
        st.markdown(kcard_html(lbl,ind,df,fmt,inv), unsafe_allow_html=True)

# ── F&G를 두 번째 컬럼에 맞게 삽입 이미 했으므로 패스
# 실제로는 KPI_SPECS[1]이 FEAR_GREED라 fgcard_html 별도 사용:
# (아래처럼 개별 override)
with kcols[1]:
    st.markdown(fgcard_html(), unsafe_allow_html=True)

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# == 섹션 1: 시장 심리 ==
# ═══════════════════════════════════════════════════════════
sh("1","시장 심리","Market Sentiment")
c1,c2=st.columns(2)
with c1:
    vix_s=ser(market,"VIX"); hy_s=ser(fred,"HY_OAS")
    fig=go.Figure()
    if not vix_s.empty:
        fig.add_trace(go.Scatter(x=vix_s["date"],y=vix_s["value"],name="VIX",
            line=dict(color=UP,width=2),
            hovertemplate="<b>VIX</b> %{y:.1f}<extra></extra>"))
    if not hy_s.empty:
        fig.add_trace(go.Scatter(x=hy_s["date"],y=hy_s["value"],name="HY OAS %",
            line=dict(color=AMB,width=1.8),
            hovertemplate="<b>HY OAS</b> %{y:.2f}%<extra></extra>"))
    fig.add_hrect(y0=25,y1=100,fillcolor=f"rgba(220,38,38,0.04)",line_width=0)
    lay=BL("VIX · HY 신용스프레드 (25↑=경계)")
    lay["yaxis"]["autorange"]=True
    fig.update_layout(**lay)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fg_row=lat(sentiment,"FEAR_GREED")
    if fg_row is not None:
        fv=fg_row["value"]
        if fv<25:   fc,fl=UP,"극도의 공포"
        elif fv<45: fc,fl="#F97316","공포"
        elif fv<55: fc,fl=AMB,"중립"
        elif fv<75: fc,fl="#84CC16","탐욕"
        else:       fc,fl="#16A34A","극도의 탐욕"
        fig=go.Figure(go.Indicator(
            mode="gauge+number", value=fv,
            domain={"x":[0,1],"y":[0,1]},
            number={"font":{"size":44,"family":"JetBrains Mono","color":WT}},
            title={"text":f'{fl} · CNN Fear & Greed Index<br><span style="font-size:11px;color:{MUT}">0=극도공포 · 25=공포 · 50=중립 · 75=탐욕 · 100=극도탐욕</span>',
                   "font":{"size":13,"family":"Syne","color":fc}},
            gauge={"axis":{"range":[0,100],"tickwidth":0,"tickvals":[0,25,50,75,100],
                           "tickfont":{"size":9,"color":MUT}},
                   "bar":{"color":fc,"thickness":0.22},
                   "bgcolor":BG,"borderwidth":0,
                   "steps":[{"range":[0,25],"color":"rgba(220,38,38,0.15)"},
                             {"range":[25,45],"color":"rgba(249,115,22,0.12)"},
                             {"range":[45,55],"color":"rgba(245,158,11,0.12)"},
                             {"range":[55,75],"color":"rgba(132,204,22,0.12)"},
                             {"range":[75,100],"color":"rgba(22,163,74,0.15)"}],
                   "threshold":{"line":{"color":WT,"width":2},"thickness":0.7,"value":fv}}))
        fig.update_layout(paper_bgcolor=CARD,height=262,
                          margin=dict(l=30,r=30,t=20,b=20),
                          font=dict(family="JetBrains Mono",color=MUT))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("공포탐욕지수 데이터 수집 중")

# ═══════════════════════════════════════════════════════════
# == 섹션 2: 금리 & 통화정책 ==
# ═══════════════════════════════════════════════════════════
sh("2","금리 & 통화정책","Rates & Monetary Policy")
c1,c2=st.columns(2)

with c1:
    fig=go.Figure()
    rate_map=[("US_3Y","美 3년",DN),("US_10Y","美 10년","#93C5FD"),("US_30Y","美 30년","#BFDBFE")]
    for ind,nm,clr in rate_map:
        s=ser(fred,ind)
        if not s.empty:
            fig.add_trace(go.Scatter(x=s["date"],y=s["value"],name=nm,
                line=dict(color=clr,width=1.8),
                hovertemplate=f"<b>{nm}</b> %{{y:.2f}}%<extra></extra>"))
    # 한국 금리 (ECOS 스냅샷 → 수평선)
    kor_base=get_ecos_val("한국은행 기준금리")
    kor_3y=get_ecos_val("국고채수익률(3년)")
    if kor_base:
        fig.add_hline(y=kor_base,line_dash="dot",line_color=UP,line_width=1.5,
                     annotation_text=f"한국 기준금리 {kor_base:.2f}%",
                     annotation_font_color=UP,annotation_position="right")
    if kor_3y:
        fig.add_hline(y=kor_3y,line_dash="dot",line_color="#FCA5A5",line_width=1.5,
                     annotation_text=f"한국 국고채 3년 {kor_3y:.2f}%",
                     annotation_font_color="#FCA5A5",annotation_position="right")
    lay=BL("美 3Y / 10Y / 30Y 국채금리  +  한국 기준금리",262)
    lay["yaxis"]["autorange"]=True
    fig.update_layout(**lay)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    sp_s=ser(fred,"T10Y2Y")
    ffr_s=ser(fred,"FFR")
    fig=go.Figure()
    if not sp_s.empty:
        fig.add_trace(go.Scatter(x=sp_s["date"],y=sp_s["value"],name="2Y-10Y 스프레드",
            line=dict(color=AMB,width=2),
            hovertemplate="<b>2Y-10Y</b> %{y:.2f}%<extra></extra>"))
    if not ffr_s.empty:
        fig.add_trace(go.Scatter(x=ffr_s["date"],y=ffr_s["value"],name="연방기준금리",
            line=dict(color=DN,width=2),
            hovertemplate="<b>FFR</b> %{y:.2f}%<extra></extra>"))
    fig.add_hline(y=0,line_dash="dot",line_color="#374151",line_width=1)
    lay=BL("2Y-10Y 스프레드 (마이너스=침체 신호)  ·  연방기준금리",262)
    lay["yaxis"]["autorange"]=True
    fig.update_layout(**lay)
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# == 섹션 3: 환율 & 달러 ==
# ═══════════════════════════════════════════════════════════
sh("3","환율 & 달러","FX & Dollar")

def norm_ser(df, ind, days=365):
    s=ser(df,ind,days)
    if len(s)<2: return s
    base=s.iloc[0]["value"]
    out=s.copy(); out["value"]=(out["value"]/base-1)*100
    return out

dxy_n=norm_ser(market,"DXY")
krw_n=norm_ser(market,"USDKRW")
jpy_n=norm_ser(market,"USDJPY")

fig=go.Figure()
for s,nm,clr in [(dxy_n,"DXY (달러 강도)","#93C5FD"),
                  (krw_n,"USD/KRW (원화 약세↑)",UP),
                  (jpy_n,"USD/JPY (엔화 약세↑)","#FCA5A5")]:
    if not s.empty:
        fig.add_trace(go.Scatter(x=s["date"],y=s["value"],name=nm,
            line=dict(width=1.8),
            hovertemplate=f"<b>{nm}</b> %{{y:+.2f}}%<extra></extra>"))
fig.add_hline(y=0,line_dash="dot",line_color="#374151",line_width=1)
lay=BL("DXY · USD/KRW · USD/JPY 상대 변화율 (1년 전=0 기준, 위로 갈수록 달러 강세)",280)
lay["yaxis"]["title_text"]="기준 대비 (%)"
lay["yaxis"]["autorange"]=True
fig.update_layout(**lay)
st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# == 섹션 4: 유동성 ==
# ═══════════════════════════════════════════════════════════
sh("4","유동성","Liquidity")
c1,c2=st.columns(2)
with c1:
    fed_s=ser(fred,"FED_ASSETS",days=365*5)
    fig=lc([(fed_s,"연준 자산 (억달러)",DN)],
           "연준 자산 (Fed Balance Sheet) — 증가=양적완화, 감소=양적긴축")
    if not fed_s.empty:
        fig.update_layout(yaxis_autorange=True)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    m2_s=ser(fred,"M2_US",days=365*5)
    fig=lc([(m2_s,"美 M2 (억달러)",UP)],
           "미국 M2 통화량 — 증가=유동성 확대=자산 가격 상승 압력")
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# == 섹션 5: 미국 증시 ==
# ═══════════════════════════════════════════════════════════
sh("5","미국 증시","US Market")
c1,c2=st.columns(2)
with c1:
    spx_s=ser(market,"SPX"); nas_s=ser(market,"NASDAQ")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    AX=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT))
    if not spx_s.empty:
        fig.add_trace(go.Scatter(x=spx_s["date"],y=spx_s["value"],name="S&P500",
            line=dict(color=DN,width=2),
            hovertemplate="<b>S&P500</b> %{y:,.0f}<extra></extra>"),secondary_y=False)
    if not nas_s.empty:
        fig.add_trace(go.Scatter(x=nas_s["date"],y=nas_s["value"],name="NASDAQ",
            line=dict(color=UP,width=2),
            hovertemplate="<b>NASDAQ</b> %{y:,.0f}<extra></extra>"),secondary_y=True)
    fig.update_layout(
        title=dict(text="S&P500 · NASDAQ",font=dict(size=11,color="#8B9AB5"),x=0.01),
        height=262,paper_bgcolor=CARD,plot_bgcolor=BG,
        font=dict(family="JetBrains Mono",size=10,color=MUT),
        margin=dict(l=8,r=8,t=32,b=8),
        legend=dict(orientation="h",y=1.08,x=0,font=dict(size=9,color="#8B9AB5"),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",xaxis=AX)
    fig.update_yaxes(showgrid=True,gridcolor=G,zeroline=False,showline=False,
                     autorange=True,tickfont=dict(size=9,color=MUT),secondary_y=False)
    fig.update_yaxes(showgrid=False,zeroline=False,showline=False,
                     autorange=True,tickfont=dict(size=9,color=MUT),secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    sox_s=ser(market,"SOX")
    fig=lc([(sox_s,"SOX 반도체 지수",DN)],"필라델피아 반도체 (SOX) — 한국 반도체 선행지표")
    fig.update_layout(yaxis_autorange=True)
    st.plotly_chart(fig, use_container_width=True)

# US 히트맵
st.plotly_chart(make_treemap(US_STOCKS,"미국 시가총액 TOP 10 히트맵 (시가총액: $10억 기준, 색상: 전일대비 등락)"),
                use_container_width=True)

# ═══════════════════════════════════════════════════════════
# == 섹션 6: 한국 증시 ==
# ═══════════════════════════════════════════════════════════
sh("6","한국 증시","Korean Market")
c1,c2=st.columns(2)
with c1:
    ksp_s=ser(market,"KOSPI"); ksq_s=ser(market,"KOSDAQ")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    AX2=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT))
    if not ksp_s.empty:
        fig.add_trace(go.Scatter(x=ksp_s["date"],y=ksp_s["value"],name="KOSPI",
            line=dict(color=DN,width=2),
            hovertemplate="<b>KOSPI</b> %{y:,.0f}<extra></extra>"),secondary_y=False)
    if not ksq_s.empty:
        fig.add_trace(go.Scatter(x=ksq_s["date"],y=ksq_s["value"],name="KOSDAQ",
            line=dict(color=UP,width=2,dash="dot"),
            hovertemplate="<b>KOSDAQ</b> %{y:,.0f}<extra></extra>"),secondary_y=True)
    fig.update_layout(
        title=dict(text="KOSPI (좌축) · KOSDAQ (우축 보조)",font=dict(size=11,color="#8B9AB5"),x=0.01),
        height=262,paper_bgcolor=CARD,plot_bgcolor=BG,
        font=dict(family="JetBrains Mono",size=10,color=MUT),
        margin=dict(l=8,r=8,t=32,b=8),
        legend=dict(orientation="h",y=1.08,x=0,font=dict(size=9,color="#8B9AB5"),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",xaxis=AX2)
    fig.update_yaxes(showgrid=True,gridcolor=G,zeroline=False,autorange=True,
                     tickfont=dict(size=9,color=MUT),secondary_y=False)
    fig.update_yaxes(showgrid=False,zeroline=False,autorange=True,
                     tickfont=dict(size=9,color=MUT),secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    # 외국인 순매수 (kospi_flows.parquet)
    flows=load("kospi_flows.parquet")
    if not flows.empty and "indicator" in flows.columns:
        fs=flows[flows["indicator"]=="KOSPI_FOREIGN_NET"].sort_values("date")
        fs=fs[fs["date"]>=pd.Timestamp.now()-pd.Timedelta(days=365)]
        if not fs.empty:
            bar_c=[UP if v>=0 else DN for v in fs["value"]]
            nl={k:v for k,v in BL("외국인 KOSPI 순매수 (원)").items() if k!="legend"}
            fig=go.Figure(go.Bar(x=fs["date"],y=fs["value"],marker_color=bar_c,
                hovertemplate="<b>외국인 순매수</b> %{y:,.0f}원<extra></extra>"))
            fig.update_layout(showlegend=False,yaxis_autorange=True,**nl)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("외국인 수급 데이터 누적 중")
    else:
        st.info("외국인 수급: PyKRX IP 차단으로 수집 불가 (KRX는 해외 IP 제한)")

# 한국 히트맵
st.plotly_chart(make_treemap(KR_STOCKS,"한국 시가총액 TOP 20 히트맵 (KOSPI+KOSDAQ 혼합, 시가총액: 조원 기준, 색상: 전일대비 등락)"),
                use_container_width=True)

# ═══════════════════════════════════════════════════════════
# == 섹션 7: 글로벌 증시 ==
# ═══════════════════════════════════════════════════════════
sh("7","글로벌 증시","Global Equity")
c1,c2,c3,c4=st.columns(4)
global_map=[
    (c1,"NIKKEI","닛케이 225 (일본)"),
    (c2,"SHANGHAI","상해종합 (중국)"),
    (c3,"HSI","항셍 (홍콩)"),
    (c4,"NIFTY","니프티50 (인도)"),
]
for col,ind,title in global_map:
    with col:
        s=ser(market,ind)
        r=lat(market,ind)
        if not s.empty and r is not None:
            chg=pct_chg_1d(ind)
            clr=UP if chg>=0 else DN
            fig=go.Figure(go.Scatter(x=s["date"],y=s["value"],
                line=dict(color=clr,width=2),
                hovertemplate="%{y:,.0f}<extra></extra>"))
            fig.update_layout(**BL(f"{title}<br><span style='font-size:9px'>{r['value']:,.0f} {'▲' if chg>=0 else '▼'}{abs(chg):.2f}%</span>",240))
            fig.update_layout(yaxis_autorange=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(f'<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;padding:14px;font-size:10px;color:{MUT};height:240px;display:flex;align-items:center;justify-content:center">{title}<br>데이터 수집 중</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# == 섹션 8: 원자재 & 암호화폐 ==
# ═══════════════════════════════════════════════════════════
sh("8","원자재 & 암호화폐","Commodities & Crypto")
c1,c2,c3=st.columns(3)
with c1:
    g_s=ser(market,"GOLD"); sv_s=ser(market,"SILVER")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    AX3=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT))
    if not g_s.empty:
        fig.add_trace(go.Scatter(x=g_s["date"],y=g_s["value"],name="금 ($/oz)",
            line=dict(color=GOLD_C,width=2),
            hovertemplate="<b>금</b> $%{y:,.0f}<extra></extra>"),secondary_y=False)
    if not sv_s.empty:
        fig.add_trace(go.Scatter(x=sv_s["date"],y=sv_s["value"],name="은 ($/oz)",
            line=dict(color="#9CA3AF",width=1.8),
            hovertemplate="<b>은</b> $%{y:.2f}<extra></extra>"),secondary_y=True)
    fig.update_layout(title=dict(text="금 · 은",font=dict(size=11,color="#8B9AB5"),x=0.01),
        height=262,paper_bgcolor=CARD,plot_bgcolor=BG,font=dict(family="JetBrains Mono",size=10,color=MUT),
        margin=dict(l=8,r=8,t=32,b=8),legend=dict(orientation="h",y=1.08,x=0,font=dict(size=9),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",xaxis=AX3)
    fig.update_yaxes(autorange=True,showgrid=True,gridcolor=G,zeroline=False,tickfont=dict(size=9,color=MUT),secondary_y=False)
    fig.update_yaxes(autorange=True,showgrid=False,zeroline=False,tickfont=dict(size=9,color=MUT),secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    oil_s=ser(market,"OIL"); cu_s=ser(market,"COPPER")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    if not oil_s.empty:
        fig.add_trace(go.Scatter(x=oil_s["date"],y=oil_s["value"],name="WTI 원유 ($/배럴)",
            line=dict(color="#6B7280",width=2),
            hovertemplate="<b>WTI</b> $%{y:.1f}<extra></extra>"),secondary_y=False)
    if not cu_s.empty:
        fig.add_trace(go.Scatter(x=cu_s["date"],y=cu_s["value"],name="구리 ($/lb)",
            line=dict(color="#F97316",width=1.8),
            hovertemplate="<b>구리</b> $%{y:.3f}<extra></extra>"),secondary_y=True)
    fig.update_layout(title=dict(text="WTI 원유 · 구리 (경기 선행지표)",font=dict(size=11,color="#8B9AB5"),x=0.01),
        height=262,paper_bgcolor=CARD,plot_bgcolor=BG,font=dict(family="JetBrains Mono",size=10,color=MUT),
        margin=dict(l=8,r=8,t=32,b=8),legend=dict(orientation="h",y=1.08,x=0,font=dict(size=9),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",xaxis=AX3)
    fig.update_yaxes(autorange=True,showgrid=True,gridcolor=G,zeroline=False,tickfont=dict(size=9,color=MUT),secondary_y=False)
    fig.update_yaxes(autorange=True,showgrid=False,zeroline=False,tickfont=dict(size=9,color=MUT),secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

with c3:
    btc_s=ser(market,"BTC"); eth_s=ser(market,"ETH")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    if not btc_s.empty:
        fig.add_trace(go.Scatter(x=btc_s["date"],y=btc_s["value"],name="BTC ($)",
            line=dict(color="#F7931A",width=2),
            hovertemplate="<b>BTC</b> $%{y:,.0f}<extra></extra>"),secondary_y=False)
    if not eth_s.empty:
        fig.add_trace(go.Scatter(x=eth_s["date"],y=eth_s["value"],name="ETH ($)",
            line=dict(color="#627EEA",width=1.8),
            hovertemplate="<b>ETH</b> $%{y:,.0f}<extra></extra>"),secondary_y=True)
    fig.update_layout(title=dict(text="Bitcoin · Ethereum",font=dict(size=11,color="#8B9AB5"),x=0.01),
        height=262,paper_bgcolor=CARD,plot_bgcolor=BG,font=dict(family="JetBrains Mono",size=10,color=MUT),
        margin=dict(l=8,r=8,t=32,b=8),legend=dict(orientation="h",y=1.08,x=0,font=dict(size=9),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",xaxis=AX3)
    fig.update_yaxes(autorange=True,showgrid=True,gridcolor=G,zeroline=False,tickfont=dict(size=9,color=MUT),secondary_y=False)
    fig.update_yaxes(autorange=True,showgrid=False,zeroline=False,tickfont=dict(size=9,color=MUT),secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# == 섹션 9: 미국 매크로 ==
# ═══════════════════════════════════════════════════════════
sh("9","미국 매크로","US Macro")
c1,c2=st.columns(2)
with c1:
    cpi=ser(fred,"US_CORE_CPI",days=365*6)
    pce=ser(fred,"US_CORE_PCE",days=365*6)
    fig=go.Figure()
    if not cpi.empty:
        cc=cpi.copy(); cc["yoy"]=cc["value"].pct_change(12)*100
        cy=cc.dropna(subset=["yoy"])[["date","yoy"]].rename(columns={"yoy":"value"})
        if not cy.empty:
            fig.add_trace(go.Scatter(x=cy["date"],y=cy["value"],name="Core CPI YoY %",
                line=dict(color=UP,width=2),hovertemplate="<b>Core CPI</b> %{y:.2f}%<extra></extra>"))
    if not pce.empty:
        pp=pce.copy(); pp["yoy"]=pp["value"].pct_change(12)*100
        py=pp.dropna(subset=["yoy"])[["date","yoy"]].rename(columns={"yoy":"value"})
        if not py.empty:
            fig.add_trace(go.Scatter(x=py["date"],y=py["value"],name="Core PCE YoY %",
                line=dict(color=DN,width=1.8,dash="dot"),
                hovertemplate="<b>Core PCE</b> %{y:.2f}%<extra></extra>"))
    fig.add_hline(y=2.0,line_dash="dot",line_color="#374151",line_width=1.5,
                  annotation_text="Fed 목표 2%",annotation_font_color=MUT,annotation_position="bottom right")
    lay=BL("Core CPI · Core PCE YoY (Fed 인플레 목표 2%)"); lay["yaxis"]["autorange"]=True
    fig.update_layout(**lay)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    nfp=ser(fred,"US_NFP",days=365*5)
    if not nfp.empty:
        nfp=nfp.copy(); nfp["mom"]=nfp["value"].diff()
        nm=nfp.dropna(subset=["mom"])
        nl={k:v for k,v in BL("비농업 고용 MoM (천명) — 매월 첫 금요일 발표").items() if k!="legend"}
        fig=go.Figure(go.Bar(x=nm["date"],y=nm["mom"],
            marker_color=[UP if v>=0 else DN for v in nm["mom"]],
            hovertemplate="<b>NFP MoM</b> %{y:,.0f}천명<extra></extra>"))
        fig.update_layout(showlegend=False,yaxis_autorange=True,**nl)
        st.plotly_chart(fig, use_container_width=True)

c3,c4=st.columns(2)
with c3:
    ic_s=ser(fred,"US_INIT_CLAIMS",days=365*3)
    fig=lc([(ic_s,"신규 실업급여 청구 (명)",UP)],
           "Initial Jobless Claims (주간) — 노동시장 가장 빠른 지표, 20만↑주의")
    fig.update_layout(yaxis_autorange=True)
    st.plotly_chart(fig, use_container_width=True)

with c4:
    rt_s=ser(fred,"US_RETAIL",days=365*5)
    if not rt_s.empty:
        rt_s=rt_s.copy(); rt_s["mom"]=rt_s["value"].pct_change()*100
        rm=rt_s.dropna(subset=["mom"])
        nl2={k:v for k,v in BL("소매판매 MoM % (미국 소비 강도 — GDP 70%)").items() if k!="legend"}
        fig=go.Figure(go.Bar(x=rm["date"],y=rm["mom"],
            marker_color=[UP if v>=0 else DN for v in rm["mom"]],
            hovertemplate="<b>소매판매 MoM</b> %{y:.2f}%<extra></extra>"))
        fig.update_layout(showlegend=False,yaxis_autorange=True,**nl2)
        st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# == 섹션 10: 한국 매크로 ==
# ═══════════════════════════════════════════════════════════
sh("10","한국 매크로 · ECOS TOP 10","Korean Macro")

ECOS_TOP_KEYWORDS=[
    "한국은행 기준금리",
    "국고채수익률(3년)",
    "국고채수익률(5년)",
    "원/달러",
    "KOSPI",
    "수출",
    "경상수지",
    "M2",
    "소비자물가",
    "실업률",
]

ECOS_DESC={
    "한국은행 기준금리": "한국 통화정책 기준. 올리면 대출·채권 금리 상승",
    "국고채수익률(3년)": "한국 3년 국채. 시중 금리 기준점",
    "국고채수익률(5년)": "한국 5년 국채. 중기 자금비용 기준",
    "원/달러":           "원달러 환율. 달러 강세 시 한국 수출기업 수혜",
    "KOSPI":             "한국 주식시장 대형주 종합지수",
    "수출":              "한국 수출 (한국 경제의 가장 강력한 선행지표)",
    "경상수지":          "무역·서비스 흑자. 원화 강세 요인",
    "M2":                "광의통화. 증가=시중 유동성 확대=자산가격 상승 압력",
    "소비자물가":         "한국 CPI. 한국은행 금리 결정의 핵심 지표",
    "실업률":             "취업자 비중. 낮을수록 경기 양호",
}

if not ecos.empty and "KEYSTAT_NAME" in ecos.columns:
    # TOP 10 필터링
    mask = ecos["KEYSTAT_NAME"].apply(
        lambda x: any(k in str(x) for k in ECOS_TOP_KEYWORDS)
    )
    top10 = ecos[mask].copy()

    if not top10.empty:
        cl=[c for c in ["CLASS_NAME","KEYSTAT_NAME","DATA_VALUE","UNIT_NAME","CYCLE"] if c in top10.columns]
        rows=""
        for _,r in top10[cl].head(10).iterrows():
            kn=str(r.get("KEYSTAT_NAME",""))
            desc_txt=next((v for k,v in ECOS_DESC.items() if k in kn),"")
            desc_cell=(f'<div style="font-size:9px;color:{MUT};margin-top:2px">{desc_txt}</div>') if desc_txt else ""
            rows+=(f'<tr style="border-bottom:1px solid rgba(30,45,74,.6)">'
                   f'<td style="padding:.45rem 1rem;font-size:10px;color:{MUT}">{r.get("CLASS_NAME","")}</td>'
                   f'<td style="padding:.45rem 1rem"><div style="font-size:11px;color:{WT}">{kn}</div>{desc_cell}</td>'
                   f'<td style="padding:.45rem 1rem;font-size:13px;font-weight:700;color:{WT};text-align:right">{r.get("DATA_VALUE","")}</td>'
                   f'<td style="padding:.45rem 1rem;font-size:10px;color:{MUT};text-align:right">{r.get("UNIT_NAME","")}</td>'
                   f'<td style="padding:.45rem 1rem;font-size:10px;color:{MUT};text-align:right">{r.get("CYCLE","")}</td>'
                   f'</tr>')
        TH=f"padding:.65rem 1rem;text-align:left;font-size:9px;color:{MUT};letter-spacing:1.5px;text-transform:uppercase;font-weight:500;border-bottom:1px solid {BORD}"
        st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;overflow:hidden;font-family:'JetBrains Mono',monospace">
<table style="width:100%;border-collapse:collapse">
  <thead><tr style="background:{C2}">
    <th style="{TH};width:15%">분류</th>
    <th style="{TH};width:38%">지표명 · 의미</th>
    <th style="{TH};width:15%;text-align:right">현재값</th>
    <th style="{TH};width:10%;text-align:right">단위</th>
    <th style="{TH};width:8%;text-align:right">주기</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table></div>""", unsafe_allow_html=True)
    else:
        st.info("ECOS 데이터 필터링 중")
else:
    st.info("ECOS 데이터 없음")

# ═══════════════════════════════════════════════════════════
# == 푸터 ==
# ═══════════════════════════════════════════════════════════
st.markdown(f"""
<div style="margin-top:3rem;padding-top:1rem;border-top:1px solid {BORD};
  font-size:10px;color:{MUT};text-align:center;letter-spacing:1px;
  font-family:'JetBrains Mono',monospace">
  FRED · yfinance · CNN Fear&Greed · 한국은행 ECOS
  &nbsp;·&nbsp; 매일 KST 07:00 자동 수집 &nbsp;·&nbsp; 전일 종가 기준
</div>
""", unsafe_allow_html=True)
