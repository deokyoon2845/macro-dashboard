"""
Deokyoon's Monitoring — v7
파스텔 블루 테마 | 모든 빨간색 제거
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

# ── 파스텔 블루 팔레트 ───────────────────────────────────────
BG   = "#070B14"
CARD = "#0E1523"
C2   = "#090E1B"
BORD = "#1A2B4A"
G    = "#0C1830"

B1 = "#BAE6FD"   # sky-200  (가장 밝음)
B2 = "#7DD3FC"   # sky-300
B3 = "#60A5FA"   # blue-400 ← 메인 포인트
B4 = "#3B82F6"   # blue-500
B5 = "#2563EB"   # blue-600
B6 = "#1D4ED8"   # blue-700
B7 = "#1E40AF"   # blue-800

IND = "#818CF8"  # indigo-400
SLT = "#94A3B8"  # slate-400
WT  = "#E0E7FF"  # 블루틴트 화이트
MUT = "#64748B"  # muted slate

UP = B3          # 상승 = 파스텔 블루
DN = B6          # 하락 = 진한 블루

def up_dn(d): return UP if (d or 0) >= 0 else DN

# ── CSS (자간·행간 축소) ──────────────────────────────────────
st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
html,body,[class*="css"]{{
  background:{BG}!important;color:{WT}!important;
  font-family:'JetBrains Mono',monospace!important;
  letter-spacing:0.015em!important;
  line-height:1.3!important;
}}
.block-container{{padding:0 2rem 3rem!important;max-width:100%!important;background:{BG}!important}}
[data-testid="stAppViewContainer"]{{background:{BG}!important}}
[data-testid="stHeader"]{{background:{BG}!important;border-bottom:1px solid {BORD}!important}}
section[data-testid="stSidebar"]{{display:none}}
#MainMenu,footer,header{{visibility:hidden}}
p,span,div,label,th,td{{color:{WT}!important;letter-spacing:0.015em!important;line-height:1.3!important}}
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
    try: return round((s.iloc[-1]["value"]/s.iloc[-2]["value"]-1)*100, 2)
    except: return 0.0

def get_ecos_val(keyword):
    if ecos.empty or "KEYSTAT_NAME" not in ecos.columns: return None
    r = ecos[ecos["KEYSTAT_NAME"].str.contains(keyword, na=False)]
    if r.empty: return None
    try: return float(str(r.iloc[0]["DATA_VALUE"]).replace(",",""))
    except: return None

def no_data(label="데이터 수집 중"):
    st.markdown(
        f'<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;'
        f'padding:14px;font-size:10px;color:{MUT};height:262px;display:flex;'
        f'align-items:center;justify-content:center;text-align:center;">'
        f'{label}<br><span style="font-size:9px">GitHub Actions 실행 후 표시</span></div>',
        unsafe_allow_html=True)

# ── 지표 설명 ─────────────────────────────────────────────────
DESC = {
    "VIX":          "옵션 내재 변동성 | 15↓안정 · 25↑경계 · 30↑패닉",
    "FEAR_GREED":   "0=극도공포 · 25=공포 · 50=중립 · 75=탐욕 · 100=극도탐욕",
    "SOX":          "美 반도체 | 삼성·SK하이닉스 선행지표",
    "SPX":          "S&P500 | 글로벌 위험선호 기준",
    "NASDAQ":       "나스닥 | 기술·성장주, 고금리에 민감",
    "KOSPI":        "한국 대형주 | 외국인 수급 민감",
    "USDKRW":       "원달러 | 1,300↑주의 · 1,400↑위험",
    "US_10Y":       "美 10년 | 전세계 자본비용 기준 | 4.5↑주의",
}

# ── 스파크라인 SVG ────────────────────────────────────────────
def spark(df, ind, color=B3, days=90, w=80, h=30):
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
         f'<stop offset="0%" stop-color="{color}" stop-opacity="0.2"/>'
         f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
         f'</linearGradient></defs>'
         f'<path d="{fd}" fill="url(#{gid})"/>'
         f'<path d="{ld}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
         f'<circle cx="{lx}" cy="{ly}" r="2" fill="{color}"/>'
         f'</svg>')
    start_dt = s["date"].iloc[0].strftime("%y.%m") if not s.empty else ""
    start_v  = f"{vals[0]:,.1f}"
    return svg, start_dt, start_v

# ── Plotly 기본 레이아웃 ──────────────────────────────────────
def BL(title="", h=262):
    return dict(
        paper_bgcolor=CARD, plot_bgcolor=BG,
        font=dict(family="JetBrains Mono",size=10,color=MUT),
        title=dict(text=title,font=dict(size=10,color=SLT),x=0.01),
        height=h, margin=dict(l=8,r=8,t=28,b=8),
        legend=dict(orientation="h",y=1.06,x=0,font=dict(size=9,color=SLT),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=C2,bordercolor=BORD,font=dict(family="JetBrains Mono",size=10)),
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
    lay=BL(title,h); lay["yaxis"]["autorange"]=True
    fig.update_layout(**lay)
    return fig

# ── 히트맵 (Treemap) ─────────────────────────────────────────
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
    "KR_SAMSUNG":    ("삼성전자",   270),
    "KR_SKHYNIX":    ("SK하이닉스",130),
    "KR_LGENSOL":    ("LG에너지",   70),
    "KR_SAMBIO":     ("삼성바이오", 60),
    "KR_HYUNDAI":    ("현대차",     55),
    "KR_KIA":        ("기아",       45),
    "KR_CELLTRION":  ("셀트리온",   40),
    "KR_POSCO":      ("POSCO",      38),
    "KR_KB":         ("KB금융",     35),
    "KR_NAVER":      ("NAVER",      28),
    "KR_ECOPROBM":   ("에코프로비엠",25),
    "KR_SAMSDI":     ("삼성SDI",    25),
    "KR_ECOPRO":     ("에코프로",   20),
    "KR_KAKAO":      ("카카오",     22),
    "KR_LGCHEM":     ("LG화학",     24),
    "KR_HYUNDAIMOB": ("현대모비스", 20),
    "KR_LGELEC":     ("LG전자",     20),
    "KR_SHINHAN":    ("신한지주",   18),
    "KR_SAMSUNG_C":  ("삼성물산",   22),
    "KR_HANA":       ("하나금융",   18),
}

def make_treemap(stocks, title=""):
    labels,parents,values,colors,cdata=[],[],[],[],[]
    for ind,(name,mcap) in stocks.items():
        chg=pct_chg_1d(ind)
        labels.append(name); parents.append("")
        values.append(mcap); colors.append(chg)
        sign="▲" if chg>=0 else "▼"
        cdata.append(f"{sign}{abs(chg):.2f}%")
    fig=go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        customdata=cdata,
        texttemplate="<b>%{label}</b><br>%{customdata}",
        textfont=dict(size=11, color=WT),
        marker=dict(
            colors=colors,
            colorscale=[
                [0.0,  "#0C2461"],
                [0.35, B6],
                [0.47, C2],
                [0.53, C2],
                [0.65, B3],
                [1.0,  B1],
            ],
            cmid=0, cmin=-5, cmax=5,
            showscale=True,
            colorbar=dict(
                thickness=10, len=0.5,
                ticksuffix="%",
                tickfont=dict(size=9, color=MUT),
                title=dict(text="등락", font=dict(size=9, color=MUT)),
            ),
        ),
        hovertemplate="<b>%{label}</b> | 전일대비: %{customdata}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=10, color=SLT), x=0.01),
        paper_bgcolor=CARD, height=380,
        margin=dict(l=0, r=0, t=28, b=0))
    return fig

# ── 섹션 헤더 ─────────────────────────────────────────────────
def sh(num, name_ko, name_en=""):
    en_html = f'<span style="font-size:9px;color:{MUT}">{name_en}</span>' if name_en else ""
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin:1.8rem 0 .8rem;letter-spacing:0.015em">
  <span style="font-family:'Syne',sans-serif;font-size:9px;font-weight:700;
    color:{BG};background:{B5};padding:2px 7px;border-radius:4px">{num}</span>
  <span style="font-size:12px;font-weight:600;color:{WT}">{name_ko}</span>
  {en_html}
  <div style="flex:1;height:1px;background:{BORD}"></div>
</div>""", unsafe_allow_html=True)

# ── 레짐 계산 ─────────────────────────────────────────────────
def regime():
    v=lat(market,"VIX"); h=lat(fred,"HY_OAS")
    if v is None or h is None: return "neu","NEUTRAL","데이터 수집 중"
    vv,hv=v["value"],h["value"]
    if vv>28 or hv>5.5:    return "risk","RISK-OFF",f"VIX {vv:.1f} · HY {hv:.2f}% — 위험 회피"
    elif vv<16 and hv<3.5: return "on","RISK-ON",  f"VIX {vv:.1f} · HY {hv:.2f}% — 위험 선호"
    else:                  return "neu","NEUTRAL",  f"VIX {vv:.1f} · HY {hv:.2f}% — 관망"
rc,rt,rn=regime()
RC={"risk":(B3,"rgba(96,165,250,.12)","rgba(96,165,250,.3)"),
    "on":  (B1,"rgba(186,230,253,.1)","rgba(186,230,253,.25)"),
    "neu": (SLT,"rgba(148,163,184,.1)","rgba(148,163,184,.25)")}
rc_t,rc_bg,rc_bd=RC[rc]

# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
now=datetime.now()
st.markdown(f"""
<div style="background:{C2};border-bottom:1px solid {BORD};padding:12px 2rem;
  display:flex;justify-content:space-between;align-items:center;
  margin:0 -2rem 1.5rem;position:sticky;top:0;z-index:99;letter-spacing:0.015em">
  <div style="font-family:'Syne',sans-serif;font-size:17px;font-weight:800;color:{WT}">
    <span style="color:{B3}">D</span>eokyoon's <span style="color:{B3}">Monitoring</span>
  </div>
  <div style="display:flex;align-items:center;gap:12px">
    <span style="background:{rc_bg};color:{rc_t};border:1px solid {rc_bd};
      padding:3px 10px;border-radius:14px;font-size:9px;font-weight:600;
      letter-spacing:0.05em;text-transform:uppercase">● {rt}</span>
    <span style="font-size:9px;color:{MUT}">{now.strftime("%Y-%m-%d %H:%M")}</span>
  </div>
</div>
<div style="font-size:9px;color:{MUT};margin-bottom:.8rem;letter-spacing:0.015em">
  {rn} &nbsp;·&nbsp; 파란색 계열 = 상승 → 밝음 / 하락 → 진함
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# KPI ROW (F&G 중복 제거)
# ══════════════════════════════════════════════════════════════
KPI_SPECS = [
    ("VIX",    "VIX",    market, ".1f",  True,  False),
    ("F&G",    None,     None,   None,   None,  True),   # fgcard placeholder
    ("SOX",    "SOX",    market, ",.0f", False, False),
    ("S&P500", "SPX",    market, ",.0f", False, False),
    ("NASDAQ", "NASDAQ", market, ",.0f", False, False),
    ("KOSPI",  "KOSPI",  market, ",.0f", False, False),
    ("USD/KRW","USDKRW", market, ",.0f", True,  False),
    ("미국10Y","US_10Y", fred,   ".2f",  True,  False),
]

def fg_color_val(v):
    if v<25:   return "#1E40AF","극도공포"
    elif v<45: return "#2563EB","공포"
    elif v<55: return "#475569","중립"
    elif v<75: return B3,       "탐욕"
    else:      return B1,       "극도탐욕"

def fgcard_html():
    r=lat(sentiment,"FEAR_GREED")
    CS=(f"background:{CARD};border:1px solid {BORD};border-radius:10px;"
        f"padding:12px 13px 10px;font-family:'JetBrains Mono',monospace;"
        f"letter-spacing:0.015em;line-height:1.3")
    desc_=f'<div style="font-size:8px;color:{MUT};margin-bottom:5px;line-height:1.3">{DESC["FEAR_GREED"]}</div>'
    if r is None:
        return f'<div style="{CS};border-left:3px solid {MUT}"><div style="font-size:9px;color:{MUT};text-transform:uppercase">F&G</div>{desc_}<div style="font-size:19px;font-weight:700;color:{WT}">—</div></div>'
    v=r["value"]; fc,ft=fg_color_val(v)
    badge=(f'<span style="background:{fc}25;color:{fc};border:1px solid {fc}40;'
           f'padding:1px 6px;border-radius:8px;font-size:8px;font-weight:600">{ft}</span>')
    spk_svg,spk_from,spk_v0=spark(sentiment,"FEAR_GREED",color=fc)
    spk_block=f'<div style="margin-top:7px;opacity:.7">{spk_svg}<div style="display:flex;justify-content:space-between;font-size:7px;color:{MUT};margin-top:1px"><span>{spk_from} {spk_v0}</span><span>현재</span></div></div>' if spk_svg else ""
    return (f'<div style="{CS};border-left:3px solid {fc}">'
            f'<div style="font-size:9px;color:{MUT};text-transform:uppercase;margin-bottom:2px;letter-spacing:0.05em">F&G</div>'
            f'{desc_}'
            f'<div style="font-size:19px;font-weight:700;color:{WT};line-height:1.1;margin-bottom:2px">{v:.0f}</div>'
            f'{badge}{spk_block}</div>')

def kcard_html(label, ind, df, fmt=".2f", inv=False):
    r=lat(df,ind)
    d=dlt(df,ind)
    clr=up_dn(d if not inv else ((-d) if d else None))
    CS=(f"background:{CARD};border:1px solid {BORD};border-radius:10px;"
        f"padding:12px 13px 10px;font-family:'JetBrains Mono',monospace;"
        f"border-left:3px solid {clr};letter-spacing:0.015em;line-height:1.3")
    desc_=""
    if ind in DESC:
        desc_=f'<div style="font-size:8px;color:{MUT};margin-bottom:5px;line-height:1.3">{DESC[ind]}</div>'
    if r is None:
        return (f'<div style="{CS}">'
                f'<div style="font-size:9px;color:{MUT};text-transform:uppercase;margin-bottom:2px;letter-spacing:0.05em">{label}</div>'
                f'{desc_}<div style="font-size:19px;font-weight:700;color:{WT}">—</div></div>')
    val=r["value"]; vs=format(val,fmt)
    dh=""
    if d is not None:
        sign="▲" if d>0 else "▼"
        dh=(f'<div style="font-size:9px;font-weight:600;color:{clr};margin-top:2px;line-height:1.3">'
            f'{sign}{abs(d):.2f} <span style="color:{MUT};font-weight:400;font-size:8px">(전일대비)</span></div>')
    spk_svg,spk_from,spk_v0=spark(df,ind,color=clr)
    spk_block=""
    if spk_svg:
        spk_block=(f'<div style="margin-top:7px;opacity:.7">{spk_svg}'
                   f'<div style="display:flex;justify-content:space-between;font-size:7px;color:{MUT};margin-top:1px">'
                   f'<span>{spk_from} {spk_v0}</span><span>현재</span></div></div>')
    return (f'<div style="{CS}">'
            f'<div style="font-size:9px;color:{MUT};text-transform:uppercase;margin-bottom:2px;letter-spacing:0.05em">{label}</div>'
            f'{desc_}'
            f'<div style="font-size:19px;font-weight:700;color:{WT};line-height:1.1">{vs}</div>'
            f'{dh}{spk_block}</div>')

# KPI 렌더링 (중복 없이)
kcols = st.columns(8)
for i, col in enumerate(kcols):
    lbl,ind,df,fmt,inv,is_fg = KPI_SPECS[i]
    with col:
        if is_fg:
            st.markdown(fgcard_html(), unsafe_allow_html=True)
        else:
            st.markdown(kcard_html(lbl,ind,df,fmt,inv), unsafe_allow_html=True)

st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 섹션 1: 시장 심리
# ══════════════════════════════════════════════════════════════
sh("1","시장 심리","Market Sentiment")
c1,c2=st.columns(2)
with c1:
    # VIX (주축) + HY OAS (보조축)
    vix_s=ser(market,"VIX"); hy_s=ser(fred,"HY_OAS")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    AX=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT))
    if not vix_s.empty:
        fig.add_trace(go.Scatter(x=vix_s["date"],y=vix_s["value"],name="VIX (좌)",
            line=dict(color=B3,width=2),
            hovertemplate="<b>VIX</b> %{y:.1f}<extra></extra>"),secondary_y=False)
        fig.add_hrect(y0=25,y1=100,fillcolor=f"rgba(96,165,250,0.05)",
                      line_width=0,secondary_y=False)
    if not hy_s.empty:
        fig.add_trace(go.Scatter(x=hy_s["date"],y=hy_s["value"],name="HY OAS % (우)",
            line=dict(color=IND,width=1.8,dash="dot"),
            hovertemplate="<b>HY OAS</b> %{y:.2f}%<extra></extra>"),secondary_y=True)
    fig.update_layout(
        title=dict(text="VIX (주축) · HY 신용스프레드 (우보조축)",font=dict(size=10,color=SLT),x=0.01),
        height=262,paper_bgcolor=CARD,plot_bgcolor=BG,
        font=dict(family="JetBrains Mono",size=10,color=MUT),
        margin=dict(l=8,r=8,t=28,b=8),
        legend=dict(orientation="h",y=1.06,x=0,font=dict(size=9,color=SLT),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",xaxis=AX)
    fig.update_yaxes(showgrid=True,gridcolor=G,zeroline=False,autorange=True,
                     tickfont=dict(size=9,color=MUT),secondary_y=False)
    fig.update_yaxes(showgrid=False,zeroline=False,autorange=True,
                     tickfont=dict(size=9,color=IND),
                     title_text="HY OAS %",title_font=dict(size=9,color=IND),
                     secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fg_row=lat(sentiment,"FEAR_GREED")
    if fg_row is not None:
        fv=fg_row["value"]; fc,fl=fg_color_val(fv)
        fig=go.Figure(go.Indicator(
            mode="gauge+number", value=fv,
            domain={"x":[0,1],"y":[0,1]},
            number={"font":{"size":42,"family":"JetBrains Mono","color":WT}},
            title={"text":f'{fl} · CNN Fear & Greed<br><span style="font-size:9px;color:{MUT}">0=극도공포 · 25=공포 · 50=중립 · 75=탐욕 · 100=극도탐욕</span>',
                   "font":{"size":12,"family":"Syne","color":fc}},
            gauge={
                "axis":{"range":[0,100],"tickwidth":0,"tickvals":[0,25,50,75,100],
                        "tickfont":{"size":8,"color":MUT}},
                "bar":{"color":fc,"thickness":0.2},
                "bgcolor":BG,"borderwidth":0,
                "steps":[
                    {"range":[0,25],"color":"rgba(30,64,175,0.2)"},
                    {"range":[25,45],"color":"rgba(37,99,235,0.15)"},
                    {"range":[45,55],"color":"rgba(71,85,105,0.15)"},
                    {"range":[55,75],"color":"rgba(96,165,250,0.15)"},
                    {"range":[75,100],"color":"rgba(186,230,253,0.2)"},
                ],
                "threshold":{"line":{"color":WT,"width":2},"thickness":0.7,"value":fv},
            }))
        fig.update_layout(paper_bgcolor=CARD,height=262,
                          margin=dict(l=30,r=30,t=20,b=20),
                          font=dict(family="JetBrains Mono",color=MUT))
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data("공포탐욕지수 수집 중")

# ══════════════════════════════════════════════════════════════
# 섹션 2: 금리 & 통화정책
# ══════════════════════════════════════════════════════════════
sh("2","금리 & 통화정책","Rates & Monetary Policy")
c1,c2=st.columns(2)
with c1:
    fig=go.Figure()
    existing_rates=[]
    # 기존 데이터 (T10Y2Y_SPREAD, FFR_UPPER 이름 사용)
    us10=ser(fred,"US_10Y")
    if not us10.empty:
        fig.add_trace(go.Scatter(x=us10["date"],y=us10["value"],name="美 10년",
            line=dict(color=B3,width=2),hovertemplate="<b>美10Y</b> %{y:.2f}%<extra></extra>"))
        existing_rates.append("10Y")
    # 신규 (GitHub Actions 후 표시)
    us3=ser(fred,"US_3Y")
    if not us3.empty:
        fig.add_trace(go.Scatter(x=us3["date"],y=us3["value"],name="美 3년",
            line=dict(color=B2,width=1.8),hovertemplate="<b>美3Y</b> %{y:.2f}%<extra></extra>"))
    us30=ser(fred,"US_30Y")
    if not us30.empty:
        fig.add_trace(go.Scatter(x=us30["date"],y=us30["value"],name="美 30년",
            line=dict(color=B5,width=1.8),hovertemplate="<b>美30Y</b> %{y:.2f}%<extra></extra>"))
    # 한국 기준금리 (ECOS 스냅샷 → 수평선)
    kor_base=get_ecos_val("한국은행 기준금리")
    kor_3y=get_ecos_val("국고채수익률(3년)")
    if kor_base:
        fig.add_hline(y=kor_base,line_dash="dot",line_color=IND,line_width=1.5,
                     annotation_text=f"한국 기준금리 {kor_base:.2f}%",
                     annotation_font_color=IND,annotation_position="right")
    if kor_3y:
        fig.add_hline(y=kor_3y,line_dash="dash",line_color=SLT,line_width=1.2,
                     annotation_text=f"한국 국고채3Y {kor_3y:.2f}%",
                     annotation_font_color=SLT,annotation_position="right")
    lay=BL("미국 국채 3Y/10Y/30Y + 한국 기준금리·국고채",262)
    lay["yaxis"]["autorange"]=True
    if fig.data:
        fig.update_layout(**lay)
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data("금리 데이터 수집 중\n(Actions 실행 후 표시)")

with c2:
    sp_s=ser(fred,"T10Y2Y_SPREAD")  # ← 기존 이름 사용
    ffr_s=ser(fred,"FFR_UPPER")     # ← 기존 이름 사용
    fig=go.Figure()
    if not sp_s.empty:
        fig.add_trace(go.Scatter(x=sp_s["date"],y=sp_s["value"],name="2Y-10Y 스프레드",
            line=dict(color=B3,width=2),hovertemplate="<b>스프레드</b> %{y:.2f}%<extra></extra>"))
    if not ffr_s.empty:
        fig.add_trace(go.Scatter(x=ffr_s["date"],y=ffr_s["value"],name="연방기준금리",
            line=dict(color=IND,width=1.8),hovertemplate="<b>FFR</b> %{y:.2f}%<extra></extra>"))
    fig.add_hline(y=0,line_dash="dot",line_color="#374151",line_width=1)
    lay=BL("2Y-10Y 스프레드 (마이너스=침체신호) · 연방기준금리",262)
    lay["yaxis"]["autorange"]=True
    if fig.data:
        fig.update_layout(**lay)
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data("스프레드·기준금리 데이터 없음")

# ══════════════════════════════════════════════════════════════
# 섹션 3: 환율 & 달러
# ══════════════════════════════════════════════════════════════
sh("3","환율 & 달러","FX & Dollar")

def norm_ser(df, ind, days=365):
    s=ser(df,ind,days)
    if len(s)<2: return pd.DataFrame()
    base=s.iloc[0]["value"]
    out=s.copy(); out["value"]=(out["value"]/base-1)*100
    return out

dxy_n=norm_ser(market,"DXY")
krw_n=norm_ser(market,"USDKRW")
jpy_n=norm_ser(market,"USDJPY")  # 신규 - Actions 후 표시

fig=go.Figure()
for s,nm,clr in [(dxy_n,"DXY (달러강도)",B5),(krw_n,"USD/KRW (원화약세↑)",B3),(jpy_n,"USD/JPY (엔화약세↑)",B1)]:
    if not s.empty:
        fig.add_trace(go.Scatter(x=s["date"],y=s["value"],name=nm,
            line=dict(width=1.8),
            hovertemplate=f"<b>{nm}</b> %{{y:+.2f}}%<extra></extra>"))
fig.add_hline(y=0,line_dash="dot",line_color="#374151",line_width=1)
lay=BL("DXY · USD/KRW · USD/JPY 상대 변화율 (1년 전=0, 위=달러강세)",280)
lay["yaxis"]["autorange"]=True
lay["yaxis"]["title_text"]="기준대비 (%)"
if fig.data:
    fig.update_layout(**lay)
    st.plotly_chart(fig, use_container_width=True)
else:
    no_data("환율 데이터 없음")

# ══════════════════════════════════════════════════════════════
# 섹션 4: 유동성
# ══════════════════════════════════════════════════════════════
sh("4","유동성","Liquidity")
c1,c2=st.columns(2)
with c1:
    fed_s=ser(fred,"FED_ASSETS",days=365*5)
    if not fed_s.empty:
        fig=lc([(fed_s,"연준 자산 ($억)",B4)],"연준 자산 (증가=QE, 감소=QT)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data("연준 자산 (FED_ASSETS)\nGitHub Actions 실행 후 표시")
with c2:
    m2_s=ser(fred,"M2_US",days=365*5)
    if not m2_s.empty:
        fig=lc([(m2_s,"美 M2 ($억)",B3)],"미국 M2 통화량 (증가=유동성↑=자산가격 상승압력)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data("美 M2 (M2_US)\nGitHub Actions 실행 후 표시")

# ══════════════════════════════════════════════════════════════
# 섹션 5: 미국 증시
# ══════════════════════════════════════════════════════════════
sh("5","미국 증시","US Market")
c1,c2=st.columns(2)
with c1:
    spx_s=ser(market,"SPX"); nas_s=ser(market,"NASDAQ")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    AX2=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT))
    if not spx_s.empty:
        fig.add_trace(go.Scatter(x=spx_s["date"],y=spx_s["value"],name="S&P500 (좌)",
            line=dict(color=B3,width=2),
            hovertemplate="<b>S&P500</b> %{y:,.0f}<extra></extra>"),secondary_y=False)
    if not nas_s.empty:
        fig.add_trace(go.Scatter(x=nas_s["date"],y=nas_s["value"],name="NASDAQ (우)",
            line=dict(color=B1,width=2),
            hovertemplate="<b>NASDAQ</b> %{y:,.0f}<extra></extra>"),secondary_y=True)
    fig.update_layout(
        title=dict(text="S&P500 · NASDAQ (보조축)" + (" | NASDAQ: 데이터 수집 중" if nas_s.empty else ""),
                   font=dict(size=10,color=SLT),x=0.01),
        height=262,paper_bgcolor=CARD,plot_bgcolor=BG,
        font=dict(family="JetBrains Mono",size=10,color=MUT),
        margin=dict(l=8,r=8,t=28,b=8),
        legend=dict(orientation="h",y=1.06,x=0,font=dict(size=9,color=SLT),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",xaxis=AX2)
    fig.update_yaxes(autorange=True,showgrid=True,gridcolor=G,zeroline=False,
                     tickfont=dict(size=9,color=MUT),secondary_y=False)
    fig.update_yaxes(autorange=True,showgrid=False,zeroline=False,
                     tickfont=dict(size=9,color=MUT),secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    sox_s=ser(market,"SOX")
    if not sox_s.empty:
        st.plotly_chart(lc([(sox_s,"SOX 반도체",B4)],"SOX 반도체 — 한국 반도체 선행"),
                        use_container_width=True)
    else:
        no_data("SOX")

st.plotly_chart(make_treemap(US_STOCKS,"미국 시총 TOP 10 히트맵 (시총 $10억 · 색상=전일 등락)"),
                use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 섹션 6: 한국 증시
# ══════════════════════════════════════════════════════════════
sh("6","한국 증시","Korean Market")
c1,c2=st.columns(2)
with c1:
    ksp_s=ser(market,"KOSPI"); ksq_s=ser(market,"KOSDAQ")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    AX3=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT))
    if not ksp_s.empty:
        fig.add_trace(go.Scatter(x=ksp_s["date"],y=ksp_s["value"],name="KOSPI (좌)",
            line=dict(color=B3,width=2),
            hovertemplate="<b>KOSPI</b> %{y:,.0f}<extra></extra>"),secondary_y=False)
    if not ksq_s.empty:
        fig.add_trace(go.Scatter(x=ksq_s["date"],y=ksq_s["value"],name="KOSDAQ (우)",
            line=dict(color=B1,width=1.8,dash="dot"),
            hovertemplate="<b>KOSDAQ</b> %{y:,.0f}<extra></extra>"),secondary_y=True)
    fig.update_layout(
        title=dict(text="KOSPI (좌) · KOSDAQ (우보조축)" + (" | KOSDAQ: 수집 중" if ksq_s.empty else ""),
                   font=dict(size=10,color=SLT),x=0.01),
        height=262,paper_bgcolor=CARD,plot_bgcolor=BG,
        font=dict(family="JetBrains Mono",size=10,color=MUT),
        margin=dict(l=8,r=8,t=28,b=8),
        legend=dict(orientation="h",y=1.06,x=0,font=dict(size=9,color=SLT),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",xaxis=AX3)
    fig.update_yaxes(autorange=True,showgrid=True,gridcolor=G,zeroline=False,
                     tickfont=dict(size=9,color=MUT),secondary_y=False)
    fig.update_yaxes(autorange=True,showgrid=False,zeroline=False,
                     tickfont=dict(size=9,color=MUT),secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    flows=load("kospi_flows.parquet")
    if not flows.empty and "indicator" in flows.columns:
        fs=flows[flows["indicator"]=="KOSPI_FOREIGN_NET"].sort_values("date")
        fs=fs[fs["date"]>=pd.Timestamp.now()-pd.Timedelta(days=365)]
        if not fs.empty:
            nl={k:v for k,v in BL("외국인 KOSPI 순매수 (원)").items() if k!="legend"}
            fig=go.Figure(go.Bar(x=fs["date"],y=fs["value"],
                marker_color=[UP if v>=0 else DN for v in fs["value"]],
                hovertemplate="<b>외국인 순매수</b> %{y:,.0f}원<extra></extra>"))
            fig.update_layout(showlegend=False,yaxis_autorange=True,**nl)
            st.plotly_chart(fig, use_container_width=True)
        else:
            no_data("외국인 수급")
    else:
        no_data("외국인 수급 (PyKRX → 해외 IP 차단)")

st.plotly_chart(make_treemap(KR_STOCKS,"한국 시총 TOP 20 히트맵 (KOSPI+KOSDAQ · 시총 조원 · 색상=전일 등락)"),
                use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 섹션 7: 글로벌 증시
# ══════════════════════════════════════════════════════════════
sh("7","글로벌 증시","Global Equity")
c1,c2,c3,c4=st.columns(4)
global_map=[(c1,"NIKKEI","닛케이 (일본)"),(c2,"SHANGHAI","상해 (중국)"),
            (c3,"HSI","항셍 (홍콩)"),(c4,"NIFTY","니프티 (인도)")]
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
            sign="▲" if chg>=0 else "▼"
            lay=BL(f"{title}\n{r['value']:,.0f}  {sign}{abs(chg):.2f}%",240)
            lay["yaxis"]["autorange"]=True
            fig.update_layout(**lay)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(
                f'<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;'
                f'padding:12px;font-size:9px;color:{MUT};height:240px;display:flex;'
                f'align-items:center;justify-content:center;text-align:center">'
                f'{title}<br>Actions 실행 후 표시</div>',
                unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 섹션 8: 원자재 & 암호화폐
# ══════════════════════════════════════════════════════════════
sh("8","원자재 & 암호화폐","Commodities & Crypto")
c1,c2,c3=st.columns(3)
with c1:
    g_s=ser(market,"GOLD"); sv_s=ser(market,"SILVER")
    if not g_s.empty or not sv_s.empty:
        fig=make_subplots(specs=[[{"secondary_y":True}]])
        AXC=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT))
        if not g_s.empty:
            fig.add_trace(go.Scatter(x=g_s["date"],y=g_s["value"],name="금 (좌,$)",
                line=dict(color=B2,width=2),hovertemplate="<b>금</b> $%{y:,.0f}<extra></extra>"),secondary_y=False)
        if not sv_s.empty:
            fig.add_trace(go.Scatter(x=sv_s["date"],y=sv_s["value"],name="은 (우,$)",
                line=dict(color=SLT,width=1.8),hovertemplate="<b>은</b> $%{y:.2f}<extra></extra>"),secondary_y=True)
        fig.update_layout(title=dict(text="금·은",font=dict(size=10,color=SLT),x=0.01),
            height=262,paper_bgcolor=CARD,plot_bgcolor=BG,
            font=dict(family="JetBrains Mono",size=10,color=MUT),
            margin=dict(l=8,r=8,t=28,b=8),
            legend=dict(orientation="h",y=1.06,x=0,font=dict(size=9),bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",xaxis=AXC)
        fig.update_yaxes(autorange=True,showgrid=True,gridcolor=G,zeroline=False,tickfont=dict(size=9,color=MUT),secondary_y=False)
        fig.update_yaxes(autorange=True,showgrid=False,zeroline=False,tickfont=dict(size=9,color=MUT),secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data("금·은 (Actions 실행 후)")

with c2:
    oil_s=ser(market,"OIL"); cu_s=ser(market,"COPPER")
    if not oil_s.empty or not cu_s.empty:
        fig=make_subplots(specs=[[{"secondary_y":True}]])
        if not oil_s.empty:
            fig.add_trace(go.Scatter(x=oil_s["date"],y=oil_s["value"],name="WTI (좌,$)",
                line=dict(color=B4,width=2),hovertemplate="<b>WTI</b> $%{y:.1f}<extra></extra>"),secondary_y=False)
        if not cu_s.empty:
            fig.add_trace(go.Scatter(x=cu_s["date"],y=cu_s["value"],name="구리 (우,$)",
                line=dict(color=IND,width=1.8),hovertemplate="<b>구리</b> $%{y:.3f}<extra></extra>"),secondary_y=True)
        fig.update_layout(title=dict(text="WTI 원유 · 구리 (경기선행)",font=dict(size=10,color=SLT),x=0.01),
            height=262,paper_bgcolor=CARD,plot_bgcolor=BG,
            font=dict(family="JetBrains Mono",size=10,color=MUT),
            margin=dict(l=8,r=8,t=28,b=8),
            legend=dict(orientation="h",y=1.06,x=0,font=dict(size=9),bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",xaxis=AXC)
        fig.update_yaxes(autorange=True,showgrid=True,gridcolor=G,zeroline=False,tickfont=dict(size=9,color=MUT),secondary_y=False)
        fig.update_yaxes(autorange=True,showgrid=False,zeroline=False,tickfont=dict(size=9,color=MUT),secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data("원유·구리 (Actions 실행 후)")

with c3:
    btc_s=ser(market,"BTC"); eth_s=ser(market,"ETH")
    if not btc_s.empty or not eth_s.empty:
        fig=make_subplots(specs=[[{"secondary_y":True}]])
        if not btc_s.empty:
            fig.add_trace(go.Scatter(x=btc_s["date"],y=btc_s["value"],name="BTC (좌,$)",
                line=dict(color=B3,width=2),hovertemplate="<b>BTC</b> $%{y:,.0f}<extra></extra>"),secondary_y=False)
        if not eth_s.empty:
            fig.add_trace(go.Scatter(x=eth_s["date"],y=eth_s["value"],name="ETH (우,$)",
                line=dict(color=IND,width=1.8),hovertemplate="<b>ETH</b> $%{y:,.0f}<extra></extra>"),secondary_y=True)
        fig.update_layout(title=dict(text="Bitcoin · Ethereum",font=dict(size=10,color=SLT),x=0.01),
            height=262,paper_bgcolor=CARD,plot_bgcolor=BG,
            font=dict(family="JetBrains Mono",size=10,color=MUT),
            margin=dict(l=8,r=8,t=28,b=8),
            legend=dict(orientation="h",y=1.06,x=0,font=dict(size=9),bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",xaxis=AXC)
        fig.update_yaxes(autorange=True,showgrid=True,gridcolor=G,zeroline=False,tickfont=dict(size=9,color=MUT),secondary_y=False)
        fig.update_yaxes(autorange=True,showgrid=False,zeroline=False,tickfont=dict(size=9,color=MUT),secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data("BTC·ETH (Actions 실행 후)")

# ══════════════════════════════════════════════════════════════
# 섹션 9: 미국 매크로
# ══════════════════════════════════════════════════════════════
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
            fig.add_trace(go.Scatter(x=cy["date"],y=cy["value"],name="Core CPI YoY",
                line=dict(color=B3,width=2),hovertemplate="<b>Core CPI</b> %{y:.2f}%<extra></extra>"))
    if not pce.empty:
        pp=pce.copy(); pp["yoy"]=pp["value"].pct_change(12)*100
        py=pp.dropna(subset=["yoy"])[["date","yoy"]].rename(columns={"yoy":"value"})
        if not py.empty:
            fig.add_trace(go.Scatter(x=py["date"],y=py["value"],name="Core PCE YoY",
                line=dict(color=IND,width=1.8,dash="dot"),
                hovertemplate="<b>Core PCE</b> %{y:.2f}%<extra></extra>"))
    if fig.data:
        fig.add_hline(y=2.0,line_dash="dot",line_color="#374151",line_width=1.5,
                      annotation_text="Fed 목표 2%",annotation_font_color=MUT,
                      annotation_position="bottom right")
        lay=BL("Core CPI · Core PCE YoY (Fed 인플레 목표 2%)",262)
        lay["yaxis"]["autorange"]=True; fig.update_layout(**lay)
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data("CPI·PCE (기존 데이터 확인 중)")

with c2:
    nfp=ser(fred,"US_NFP",days=365*5)
    if not nfp.empty:
        nfp=nfp.copy(); nfp["mom"]=nfp["value"].diff()
        nm=nfp.dropna(subset=["mom"])
        nl={k:v for k,v in BL("비농업 고용 MoM (천명) — 매월 첫 금요일",262).items() if k!="legend"}
        fig=go.Figure(go.Bar(x=nm["date"],y=nm["mom"],
            marker_color=[UP if v>=0 else DN for v in nm["mom"]],
            hovertemplate="<b>NFP MoM</b> %{y:,.0f}천명<extra></extra>"))
        fig.update_layout(showlegend=False,yaxis_autorange=True,**nl)
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data("NFP")

c3,c4=st.columns(2)
with c3:
    ic_s=ser(fred,"US_INIT_CLAIMS",days=365*3)
    if not ic_s.empty:
        fig=lc([(ic_s,"신규 실업급여 청구",B4)],"Initial Jobless Claims (주간) — 20만↑주의")
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data("신규 실업급여 청구 (Actions 실행 후)")

with c4:
    rt_s=ser(fred,"US_RETAIL",days=365*5)
    if not rt_s.empty:
        rt_s=rt_s.copy(); rt_s["mom"]=rt_s["value"].pct_change()*100
        rm=rt_s.dropna(subset=["mom"])
        nl2={k:v for k,v in BL("소매판매 MoM % — GDP의 70%",262).items() if k!="legend"}
        fig=go.Figure(go.Bar(x=rm["date"],y=rm["mom"],
            marker_color=[UP if v>=0 else DN for v in rm["mom"]],
            hovertemplate="<b>소매판매 MoM</b> %{y:.2f}%<extra></extra>"))
        fig.update_layout(showlegend=False,yaxis_autorange=True,**nl2)
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data("소매판매 (Actions 실행 후)")

# ══════════════════════════════════════════════════════════════
# 섹션 10: 한국 매크로 · ECOS
# ══════════════════════════════════════════════════════════════
sh("10","한국 매크로 · ECOS TOP 10","Korean Macro")
ECOS_TOP_KEYWORDS=["한국은행 기준금리","국고채수익률","원/달러","KOSPI","수출","경상수지","M2","소비자물가","실업률","GDP"]
ECOS_DESC={
    "한국은행 기준금리":"한국 통화정책 기준. 인상=대출금리·채권금리 상승",
    "국고채수익률":"시중 자금비용 기준. 기준금리와 격차=시장 기대 반영",
    "원/달러":"원달러 환율. 달러 강세=수출기업 수혜, 수입물가 상승",
    "KOSPI":"한국 대형주 종합지수",
    "수출":"한국 경제의 최강 선행지표. YoY 전환=경기 방향 전환",
    "경상수지":"무역+서비스 흑자. 흑자=원화 강세 요인",
    "M2":"광의통화. 증가=유동성↑=자산가격 상승 압력",
    "소비자물가":"한국 CPI. 한은 금리 결정 핵심 지표",
    "실업률":"낮을수록 경기 양호. 3%대=건전",
    "GDP":"분기 경제성장률. 한국 경기의 최종 성적표",
}

if not ecos.empty and "KEYSTAT_NAME" in ecos.columns:
    mask=ecos["KEYSTAT_NAME"].apply(lambda x: any(k in str(x) for k in ECOS_TOP_KEYWORDS))
    top10=ecos[mask].copy()
    if not top10.empty:
        cl=[c for c in ["CLASS_NAME","KEYSTAT_NAME","DATA_VALUE","UNIT_NAME","CYCLE"] if c in top10.columns]
        rows=""
        for _,r in top10[cl].head(10).iterrows():
            kn=str(r.get("KEYSTAT_NAME",""))
            desc_txt=next((v for k,v in ECOS_DESC.items() if k in kn),"")
            dc=f'<div style="font-size:8px;color:{MUT};line-height:1.3;margin-top:2px">{desc_txt}</div>' if desc_txt else ""
            rows+=(f'<tr style="border-bottom:1px solid rgba(26,43,74,.6)">'
                   f'<td style="padding:.35rem .9rem;font-size:9px;color:{MUT}">{r.get("CLASS_NAME","")}</td>'
                   f'<td style="padding:.35rem .9rem"><div style="font-size:10px;color:{WT}">{kn}</div>{dc}</td>'
                   f'<td style="padding:.35rem .9rem;font-size:12px;font-weight:700;color:{WT};text-align:right">{r.get("DATA_VALUE","")}</td>'
                   f'<td style="padding:.35rem .9rem;font-size:9px;color:{MUT};text-align:right">{r.get("UNIT_NAME","")}</td>'
                   f'<td style="padding:.35rem .9rem;font-size:9px;color:{MUT};text-align:right">{r.get("CYCLE","")}</td>'
                   f'</tr>')
        TH=f"padding:.5rem .9rem;text-align:left;font-size:8px;color:{MUT};letter-spacing:0.05em;text-transform:uppercase;font-weight:500;border-bottom:1px solid {BORD}"
        st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;overflow:hidden;font-family:'JetBrains Mono',monospace;letter-spacing:0.015em">
<table style="width:100%;border-collapse:collapse">
  <thead><tr style="background:{C2}">
    <th style="{TH};width:15%">분류</th>
    <th style="{TH};width:38%">지표명 · 의미</th>
    <th style="{TH};width:15%;text-align:right">현재값</th>
    <th style="{TH};width:10%;text-align:right">단위</th>
    <th style="{TH};width:7%;text-align:right">주기</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table></div>""", unsafe_allow_html=True)
    else:
        st.info("ECOS 필터링 중")
else:
    st.info("ECOS 데이터 없음")

# ── 푸터 ─────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:2.5rem;padding-top:.8rem;border-top:1px solid {BORD};
  font-size:9px;color:{MUT};text-align:center;letter-spacing:0.015em;
  font-family:'JetBrains Mono',monospace;line-height:1.5">
  FRED · yfinance · CNN Fear&Greed · 한국은행 ECOS · 매일 KST 07:00 자동 수집 · 전일 종가 기준
</div>
""", unsafe_allow_html=True)
