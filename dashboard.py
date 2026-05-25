"""
Deokyoon's Monitoring — v10
섹션 재편 + 달력 위젯 + 히트맵 중립색 수정
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime, date, timedelta
import base64, calendar as cal_lib

st.set_page_config(page_title="Deokyoon's Monitoring",
                   page_icon="◈", layout="wide",
                   initial_sidebar_state="collapsed")

# ── 팔레트 ────────────────────────────────────────────────────
BG="#F5F0E5"; CARD="#FFFFFF"; C2="#FAF6EC"
BORD="#E5DDD0"; G="#EFE8D6"
TXT="#2A2620"; SUB="#5A5246"; MUT="#8C7F6E"
PUR_HI="#BAE6FD"; PUR_DK="#0369A1"   # 하늘색 하이라이트
B1="#DBEAFE"; B3="#60A5FA"; B4="#3B82F6"
B5="#2563EB"; B6="#1D4ED8"; B7="#1E40AF"; B8="#1E3A8A"
UP=B5; DN=B8

def up_dn(d): return UP if (d or 0)>=0 else DN

# ── CSS (종이 질감 배경) ──────────────────────────────────────
st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
@font-face{{font-family:'MaruBuri';
  src:url('https://cdn.jsdelivr.net/gh/wkdtjsgur100/maruburifonts@1.0/static/MaruBuri/MaruBuri-Regular.woff2') format('woff2');font-weight:400}}
@font-face{{font-family:'MaruBuri';
  src:url('https://cdn.jsdelivr.net/gh/wkdtjsgur100/maruburifonts@1.0/static/MaruBuri/MaruBuri-Bold.woff2') format('woff2');font-weight:700}}
html,body,[class*="css"]{{
  background-color:{BG}!important;
  background-image:
    radial-gradient(rgba(139,119,98,.042) 1px,transparent 1px),
    radial-gradient(rgba(139,119,98,.022) 1px,transparent 1px)!important;
  background-size:32px 32px,16px 16px!important;
  background-position:0 0,8px 8px!important;
  color:{TXT}!important;
  font-family:'MaruBuri','Gowun Batang',serif!important;
  letter-spacing:.015em!important;line-height:1.3!important}}
.block-container{{padding:0 2rem 3rem!important;max-width:100%!important;background:transparent!important}}
[data-testid="stAppViewContainer"]{{
  background-color:{BG}!important;
  background-image:radial-gradient(rgba(139,119,98,.042) 1px,transparent 1px),radial-gradient(rgba(139,119,98,.022) 1px,transparent 1px)!important;
  background-size:32px 32px,16px 16px!important;background-position:0 0,8px 8px!important}}
[data-testid="stHeader"]{{background:transparent!important;border-bottom:1px solid {BORD}!important;height:0}}
section[data-testid="stSidebar"]{{display:none}}
#MainMenu,footer,header{{visibility:hidden}}
p,span,div,label,th,td{{color:{TXT}!important;letter-spacing:.015em!important;line-height:1.3!important}}
.kpi-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;flex:1}}
</style>
""", unsafe_allow_html=True)

# ── 세션 상태 초기화 (캘린더) ────────────────────────────────
now = datetime.now()
if "cal_year"  not in st.session_state: st.session_state.cal_year  = now.year
if "cal_month" not in st.session_state: st.session_state.cal_month = now.month

# ── 데이터 로드 ──────────────────────────────────────────────
DATA_DIR  = Path(__file__).parent/"data"
ASSET_DIR = Path(__file__).parent/"assets"

@st.cache_data(ttl=3600)
def load(fn):
    f=DATA_DIR/fn
    if not f.exists(): return pd.DataFrame()
    df=pd.read_parquet(f)
    if "date" in df.columns: df["date"]=pd.to_datetime(df["date"])
    return df

fred=load("fred_indicators.parquet"); market=load("market_prices.parquet")
sentiment=load("sentiment.parquet");  ecos=load("ecos_latest.parquet")

def lat(df,ind):
    if df.empty: return None
    s=df[df["indicator"]==ind].sort_values("date")
    return s.iloc[-1] if not s.empty else None

def ser(df,ind,days=365):
    if df.empty: return pd.DataFrame()
    s=df[df["indicator"]==ind].copy()
    if days: s=s[s["date"]>=pd.Timestamp.now()-pd.Timedelta(days=days)]
    return s.sort_values("date")

def dlt(df,ind):
    s=ser(df,ind,15).sort_values("date")
    return (s.iloc[-1]["value"]-s.iloc[-2]["value"]) if len(s)>=2 else None

def pct_chg_1d(ind):
    s=ser(market,ind,10).sort_values("date")
    if len(s)<2: return 0.0
    try: return round((s.iloc[-1]["value"]/s.iloc[-2]["value"]-1)*100,2)
    except: return 0.0

def get_ecos_val(keyword):
    if ecos.empty or "KEYSTAT_NAME" not in ecos.columns: return None
    r=ecos[ecos["KEYSTAT_NAME"].str.contains(keyword,na=False)]
    if r.empty: return None
    try: return float(str(r.iloc[0]["DATA_VALUE"]).replace(",",""))
    except: return None

def yrange(*args,pad_pct=0.08):
    vals=[]
    for arg in args:
        if arg is None: continue
        try:
            if isinstance(arg,pd.DataFrame) and not arg.empty and "value" in arg.columns:
                col=arg["value"]
                if isinstance(col,pd.Series): vals.extend(col.dropna().tolist())
            elif isinstance(arg,pd.Series) and not arg.empty:
                vals.extend(arg.dropna().tolist())
        except: pass
    if not vals: return None
    mn,mx=min(vals),max(vals)
    if mn==mx: return [mn-1,mx+1]
    pad=(mx-mn)*pad_pct
    return [mn-pad,mx+pad]

def srange(series,pad_pct=0.08):
    try:
        vals=series.dropna().tolist()
        if not vals: return None
        mn,mx=min(vals),max(vals)
        if mn==mx: return [mn-1,mx+1]
        pad=(mx-mn)*pad_pct
        return [mn-pad,mx+pad]
    except: return None

def ma(df,ind,window,days=None):
    total=(days or 365)+window*2
    s=ser(df,ind,total).sort_values("date")
    if len(s)<window: return pd.DataFrame()
    s=s.copy(); s["value"]=s["value"].rolling(window).mean()
    if days: s=s[s["date"]>=pd.Timestamp.now()-pd.Timedelta(days=days)]
    return s.dropna()

def spark(df,ind,color=B5,days=90,w=70,h=28):
    s=ser(df,ind,days)
    vals=s["value"].dropna().tolist() if not s.empty else []
    if len(vals)<3: return ""
    mn,mx=min(vals),max(vals); mg=3
    if mn==mx:
        pts=[(round(i*w/(len(vals)-1),1),h/2) for i in range(len(vals))]
    else:
        pts=[(round(i*w/(len(vals)-1),1),round(h-mg-(v-mn)/(mx-mn)*(h-mg*2),1)) for i,v in enumerate(vals)]
    ld="M "+" L ".join(f"{x},{y}" for x,y in pts)
    fd=ld+f" L {pts[-1][0]},{h} L {pts[0][0]},{h} Z"
    gid=f"g{''.join(c for c in ind if c.isalpha())[:6]}"
    lx,ly=pts[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity=".25"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
            f'</linearGradient></defs>'
            f'<path d="{fd}" fill="url(#{gid})"/>'
            f'<path d="{ld}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{lx}" cy="{ly}" r="2" fill="{color}"/></svg>')

def get_bull_html():
    bp=ASSET_DIR/"bull.png"
    if bp.exists():
        try:
            with open(bp,"rb") as f: b64=base64.b64encode(f.read()).decode()
            return f'<img src="data:image/png;base64,{b64}" style="width:100%;height:100%;object-fit:cover;border-radius:8px;display:block">'
        except: pass
    return f'<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:56px">🐂</div>'

# ── Plotly 기본 레이아웃 ─────────────────────────────────────
def BL(title="",h=270):
    return dict(
        paper_bgcolor=CARD,plot_bgcolor=CARD,
        font=dict(family="JetBrains Mono",size=10,color=SUB),
        title=dict(text=title,font=dict(size=11,color=SUB,family="MaruBuri,serif"),x=0.01),
        height=h,margin=dict(l=8,r=8,t=28,b=8),
        legend=dict(orientation="h",y=1.08,x=0,font=dict(size=9,color=SUB),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=CARD,bordercolor=BORD,font=dict(family="JetBrains Mono",size=10,color=TXT)),
        xaxis=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT)),
        yaxis=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT)),
    )

def lc(traces,title="",h=270,zero=False):
    fig=go.Figure(); all_dfs=[]
    for df,nm,clr in traces:
        if isinstance(df,pd.DataFrame) and not df.empty:
            fig.add_trace(go.Scatter(x=df["date"],y=df["value"],name=nm,
                line=dict(color=clr,width=2),
                hovertemplate=f"<b>{nm}</b> %{{y:.2f}}<extra></extra>"))
            all_dfs.append(df)
    if zero: fig.add_hline(y=0,line_dash="dot",line_color=MUT,line_width=1)
    lay=BL(title,h); yr=yrange(*all_dfs)
    if yr: lay["yaxis"]["range"]=yr
    fig.update_layout(**lay)
    return fig

# ── 히트맵 ───────────────────────────────────────────────────
def make_treemap(stocks,title="",h=580):
    labels,parents,values,colors,cdata=[],[],[],[],[]
    for ind,(name,mcap) in stocks.items():
        chg=pct_chg_1d(ind)
        labels.append(name); parents.append(""); values.append(mcap); colors.append(chg)
        sign="▲" if chg>=0 else "▼"; cdata.append(f"{sign}{abs(chg):.2f}%")
    fig=go.Figure(go.Treemap(
        labels=labels,parents=parents,values=values,customdata=cdata,
        texttemplate="<b>%{label}</b><br>%{customdata}",
        textfont=dict(size=10,color="#FFFFFF",family="MaruBuri"),
        tiling=dict(packing="squarify",squarifyratio=1),
        marker=dict(
            colors=colors,
            # 중립(0%) = 따뜻한 회갈색으로 → 배경과 구분
            colorscale=[[0.0,B8],[0.35,B6],[0.47,"#B0A49A"],[0.53,"#B0A49A"],[0.65,B4],[1.0,B1]],
            cmid=0,cmin=-5,cmax=5,showscale=True,
            colorbar=dict(thickness=10,len=0.4,ticksuffix="%",
                tickfont=dict(size=9,color=MUT),
                title=dict(text="등락",font=dict(size=9,color=MUT))),
        ),
        hovertemplate="<b>%{label}</b> | 전일대비: %{customdata}<extra></extra>",
    ))
    fig.update_layout(title=dict(text=title,font=dict(size=11,color=SUB,family="MaruBuri"),x=0.01),
        paper_bgcolor=CARD,height=h,margin=dict(l=0,r=0,t=30,b=0))
    return fig

# ── 레짐 ──────────────────────────────────────────────────────
def regime():
    v=lat(market,"VIX"); h=lat(fred,"HY_OAS")
    if v is None or h is None: return "neu","NEUTRAL","—","데이터 수집 중"
    vv,hv=v["value"],h["value"]
    if vv>28 or hv>5.5:
        return "risk","RISK-OFF",f"VIX {vv:.1f} · HY {hv:.2f}%","위험회피 — 현금·방어주·금 비중 확대"
    elif vv<16 and hv<3.5:
        return "on","RISK-ON",f"VIX {vv:.1f} · HY {hv:.2f}%","위험선호 — 성장주·고베타 유리"
    else:
        return "neu","NEUTRAL",f"VIX {vv:.1f} · HY {hv:.2f}%","관망 — 추가 확인 후 포지션 조정"

rc,rt,rn,reg_explain=regime()
RC={"risk":(B6,"#FEF2F2","#FECACA"),"on":(B4,"#EFF6FF","#BFDBFE"),"neu":(SUB,"#FAFAF0","#E5DDD0")}
rc_t,rc_bg,rc_bd=RC[rc]

DESC={
    "SPX":    "S&P500 · 위험선호 기준",
    "NASDAQ": "나스닥 · 고금리 민감",
    "KOSPI":  "韓 대형주 · 외국인 민감",
    "KOSDAQ": "코스닥 · 성장·기술주",
    "VIX":    "옵션 변동성 · 25↑경계",
    "USDKRW": "원달러 · 1,300↑주의",
    "US_10Y": "美 10년 · 자본비용",
}

# ── KPI 카드 ─────────────────────────────────────────────────
def kcard_html(label,ind,df,fmt=".2f",inv=False):
    r=lat(df,ind); d=dlt(df,ind)
    clr=up_dn(d if not inv else ((-d) if d else None))
    desc=DESC.get(ind,"")
    desc_h=f'<div style="font-size:8px;color:{MUT};line-height:1.2;margin:1px 0 3px">{desc}</div>'
    CS=(f"background:{CARD};border:1px solid {BORD};border-left:3px solid {clr};"
        f"border-radius:8px;padding:8px 9px;font-family:'MaruBuri',serif;"
        f"display:flex;justify-content:space-between;gap:6px;align-items:stretch")
    if r is None:
        return (f'<div style="{CS.replace(clr,MUT)}">'
                f'<div style="flex:1"><div style="font-size:9px;color:{MUT};text-transform:uppercase">{label}</div>'
                f'{desc_h}<div style="font-size:15px;font-weight:700">—</div></div></div>')
    vs=format(r["value"],fmt); dh=""
    if d is not None:
        sym="▲" if d>0 else "▼"
        dh=(f'<div style="font-size:8px;font-weight:600;color:{clr};margin-top:1px">'
            f'{sym}{abs(d):.2f} <span style="color:{MUT};font-weight:400">전일</span></div>')
    spk=spark(df,ind,color=clr,w=62,h=24)
    spkd=f'<div style="flex:0 0 auto;align-self:center;opacity:.65">{spk}</div>' if spk else ""
    return (f'<div style="{CS}">'
            f'<div style="flex:1;min-width:0">'
            f'<div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.05em">{label}</div>'
            f'{desc_h}'
            f'<div style="font-size:15px;font-weight:700;color:{TXT};line-height:1.1">{vs}</div>'
            f'{dh}</div>{spkd}</div>')

def fg_color_val(v):
    if v<25:   return B8,"극도공포"
    elif v<45: return B6,"공포"
    elif v<55: return SUB,"중립"
    elif v<75: return B4,"탐욕"
    else:      return B3,"극도탐욕"

def fgcard_html():
    r=lat(sentiment,"FEAR_GREED")
    CS=(f"background:{CARD};border:1px solid {BORD};border-radius:8px;"
        f"padding:8px 9px;font-family:'MaruBuri',serif;"
        f"display:flex;justify-content:space-between;gap:6px;align-items:stretch")
    if r is None:
        return f'<div style="{CS};border-left:3px solid {MUT}"><div style="flex:1"><div sty
