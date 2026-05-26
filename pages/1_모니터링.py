"""
Deokyoon's Monitoring — v12  다크모드
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime, date, timedelta
import base64, calendar as cal_lib

st.set_page_config(page_title="DY Monitoring",
                   page_icon="◈", layout="wide",
                   initial_sidebar_state="collapsed")

# ── 다크 팔레트 ──────────────────────────────────────────────
BG    = "#0D1117"
CARD  = "#161B22"
C2    = "#1C2128"
BORD  = "#30363D"
G     = "#21262D"
TXT   = "#E6EDF3"
SUB   = "#8D96A0"
MUT   = "#6E7681"
PUR_HI = "#1F6FEB"
PUR_DK = "#58A6FF"
B1    = "#CAE8FF"
B3    = "#79C0FF"
B4    = "#58A6FF"
B5    = "#388BFD"
B6    = "#2F81F7"
B7    = "#1F6FEB"
B8    = "#1158C7"
UP    = "#3FB950"   # 상승 초록
DN    = "#F85149"   # 하락 빨강

def up_dn(d): return UP if (d or 0) >= 0 else DN

# ── CSS ──────────────────────────────────────────────────────
st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
@font-face{{font-family:'MaruBuri';src:url('https://cdn.jsdelivr.net/gh/wkdtjsgur100/maruburifonts@1.0/static/MaruBuri/MaruBuri-Regular.woff2') format('woff2');font-weight:400}}
@font-face{{font-family:'MaruBuri';src:url('https://cdn.jsdelivr.net/gh/wkdtjsgur100/maruburifonts@1.0/static/MaruBuri/MaruBuri-Bold.woff2') format('woff2');font-weight:700}}
html,body,[class*="css"]{{
  background-color:{BG}!important;
  color:{TXT}!important;
  font-family:'MaruBuri','Gowun Batang',serif!important;
  letter-spacing:.015em!important;
  line-height:1.3!important;
}}
.block-container{{padding:0 2rem 3rem!important;max-width:100%!important;background:transparent!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
[data-testid="stHeader"]{{background:transparent!important;height:0}}
section[data-testid="stSidebar"]{{display:none}}
#MainMenu,footer,header{{visibility:hidden}}
p,span,div,label,th,td{{color:{TXT}!important;letter-spacing:.015em!important}}
/* 버튼 */
.stButton>button{{
  background-color:{C2}!important;color:{TXT}!important;
  border:1px solid {BORD}!important;border-radius:8px!important;
  font-family:'MaruBuri',serif!important;padding:6px 16px!important;
  font-size:13px!important;box-shadow:none!important}}
.stButton>button:hover{{border-color:{B5}!important;color:{B5}!important;background:{C2}!important}}
.stButton>button:active,.stButton>button:focus{{border-color:{B5}!important;color:{B5}!important;background:{C2}!important;box-shadow:none!important}}
/* KPI 그리드 */
.kpi-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;flex:1}}
</style>
""", unsafe_allow_html=True)

# ── 세션 상태 ────────────────────────────────────────────────
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
    s=ser(df,ind,15)          # ser() 내부에서 이미 date 정렬됨
    if s.empty: return None   # 빈 경우 None 반환
    return (s.iloc[-1]["value"]-s.iloc[-2]["value"]) if len(s)>=2 else None

def pct_chg_1d(ind):
    s=ser(market,ind,10).sort_values("date")
    if len(s)<2: return 0.0
    try: return round((s.iloc[-1]["value"]/s.iloc[-2]["value"]-1)*100,2)
    except: return 0.0

def get_ecos_val(keyword):
    if ecos.empty or "KEYSTAT_NAME" not in ecos.columns: return None
    r=ecos[ecos["KEYSTAT_NAME"].str.contains(keyword,na=False,regex=False)]
    if r.empty and "(" in keyword:
        r=ecos[ecos["KEYSTAT_NAME"].str.contains(keyword.split("(")[0],na=False,regex=False)]
    if r.empty: return None
    try:
        raw=str(r.iloc[0]["DATA_VALUE"]).replace(",","").replace("%","").strip()
        return float(raw)
    except: return None

def yrange(*args,pad_pct=0.08):
    vals=[]
    for arg in args:
        if arg is None: continue
        try:
            if isinstance(arg,pd.DataFrame) and not arg.empty and "value" in arg.columns:
                vals.extend(arg["value"].dropna().tolist())
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
        return [mn-(mx-mn)*pad_pct, mx+(mx-mn)*pad_pct]
    except: return None

def ma(df,ind,window,days=None):
    total=(days or 365)+window*2
    s=ser(df,ind,total)           # ser() 내부에서 이미 정렬됨
    if s.empty: return pd.DataFrame()
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
            f'<stop offset="0%" stop-color="{color}" stop-opacity=".35"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity=".02"/>'
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

# ── 한국 기준금리 이력 (BOK 결정 이력 하드코딩) ──────────────
KOR_BASE_HISTORY=[
    (date(2020,3,16),0.75),(date(2020,5,28),0.50),
    (date(2021,8,26),0.75),(date(2021,11,25),1.00),
    (date(2022,1,14),1.25),(date(2022,4,14),1.50),
    (date(2022,5,26),1.75),(date(2022,7,13),2.25),
    (date(2022,8,25),2.50),(date(2022,10,12),3.00),
    (date(2022,11,24),3.25),(date(2023,1,13),3.50),
    (date(2024,8,22),3.25),(date(2024,10,16),3.00),
    (date(2024,11,28),2.75),(date(2025,2,25),2.75),
    (date(2025,5,29),2.50),
]

def kor_base_series(days=730):
    cutoff=pd.Timestamp.now()-pd.Timedelta(days=days)
    rows=[]
    for d,r in KOR_BASE_HISTORY:
        ts=pd.Timestamp(d)
        if ts>=cutoff-pd.Timedelta(days=30):
            rows.append({"date":ts,"value":r})
    if not rows:
        rows=[{"date":pd.Timestamp(KOR_BASE_HISTORY[-1][0]),"value":KOR_BASE_HISTORY[-1][1]}]
    rows.append({"date":pd.Timestamp.now(),"value":rows[-1]["value"]})
    df=pd.DataFrame(rows)
    return df[df["date"]>=cutoff]

# ── Plotly 기본 레이아웃 ─────────────────────────────────────
def BL(title="",h=270):
    return dict(
        paper_bgcolor=CARD,plot_bgcolor=CARD,
        font=dict(family="JetBrains Mono",size=10,color=SUB),
        title=dict(text=title,font=dict(size=11,color=SUB,family="MaruBuri,serif"),x=0.01),
        height=h,margin=dict(l=8,r=8,t=28,b=8),
        legend=dict(orientation="h",y=1.08,x=0,font=dict(size=9,color=SUB),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=C2,bordercolor=BORD,font=dict(family="JetBrains Mono",size=10,color=TXT)),
        xaxis=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT)),
        yaxis=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT)),
    )

def lc(traces,title="",h=270,zero=False):
    fig=go.Figure(); all_dfs=[]
    for df_,nm,clr in traces:
        if isinstance(df_,pd.DataFrame) and not df_.empty:
            fig.add_trace(go.Scatter(x=df_["date"],y=df_["value"],name=nm,
                line=dict(color=clr,width=2),
                hovertemplate=f"<b>{nm}</b> %{{y:.2f}}<extra></extra>"))
            all_dfs.append(df_)
    if zero: fig.add_hline(y=0,line_dash="dot",line_color=MUT,line_width=1)
    lay=BL(title,h); yr=yrange(*all_dfs)
    if yr: lay["yaxis"]["range"]=yr
    fig.update_layout(**lay)
    return fig

# ── 히트맵 (빨강-초록, 다크) ────────────────────────────────
HM_SCALE=[
    [0.00,"#67000D"],[0.25,"#A50F15"],[0.40,"#CB181D"],
    [0.47,"#1C2128"],[0.53,"#1C2128"],
    [0.60,"#00441B"],[0.75,"#238B45"],[1.00,"#41AB5D"],
]

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
            colors=colors,colorscale=HM_SCALE,
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
    v=lat(market,"VIX"); h_=lat(fred,"HY_OAS")
    if v is None or h_ is None: return "neu","NEUTRAL","—","데이터 수집 중"
    vv,hv=v["value"],h_["value"]
    if vv>28 or hv>5.5:
        return "risk","RISK-OFF",f"VIX {vv:.1f} · HY {hv:.2f}%","위험회피 — 현금·방어주·금 비중 확대"
    elif vv<16 and hv<3.5:
        return "on","RISK-ON",f"VIX {vv:.1f} · HY {hv:.2f}%","위험선호 — 성장주·고베타 유리"
    else:
        return "neu","NEUTRAL",f"VIX {vv:.1f} · HY {hv:.2f}%","관망 — 추가 확인 후 포지션 조정"

rc,rt,rn,reg_explain=regime()
RC={"risk":(DN,"rgba(248,81,73,.15)","rgba(248,81,73,.4)"),
    "on":  (UP,"rgba(63,185,80,.15)","rgba(63,185,80,.4)"),
    "neu": (SUB,C2,BORD)}
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
def kcard_html(label,ind,df_,fmt=".2f",inv=False):
    r=lat(df_,ind); d=dlt(df_,ind)
    clr=up_dn(d if not inv else ((-d) if d else None))
    desc=DESC.get(ind,"")
    desc_h=f'<div style="font-size:8px;color:{MUT};line-height:1.2;margin:1px 0 3px">{desc}</div>'
    CS=(f"background:{CARD};border:1px solid {BORD};border-left:3px solid {clr};"
        f"border-radius:8px;padding:8px 9px;font-family:'MaruBuri',serif;"
        f"display:flex;justify-content:space-between;gap:6px;align-items:stretch")
    if r is None:
        return (f'<div style="{CS.replace(clr,MUT)}">'
                f'<div style="flex:1"><div style="font-size:9px;color:{MUT};text-transform:uppercase">{label}</div>'
                f'{desc_h}<div style="font-size:15px;font-weight:700;color:{TXT}">—</div></div></div>')
    vs=format(r["value"],fmt); dh=""
    if d is not None:
        sym="▲" if d>0 else "▼"
        dh=(f'<div style="font-size:8px;font-weight:600;color:{clr};margin-top:1px">'
            f'{sym}{abs(d):.2f} <span style="color:{MUT};font-weight:400">전일</span></div>')
    spk=spark(df_,ind,color=clr,w=62,h=24)
    spkd=f'<div style="flex:0 0 auto;align-self:center;opacity:.75">{spk}</div>' if spk else ""
    return (f'<div style="{CS}">'
            f'<div style="flex:1;min-width:0">'
            f'<div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.05em">{label}</div>'
            f'{desc_h}'
            f'<div style="font-size:15px;font-weight:700;color:{TXT};line-height:1.1">{vs}</div>'
            f'{dh}</div>{spkd}</div>')

def fg_color_val(v):
    if v<25:   return DN,"극도공포"
    elif v<45: return "#F4A261","공포"
    elif v<55: return MUT,"중립"
    elif v<75: return "#52B788","탐욕"
    else:      return UP,"극도탐욕"

# ── 섹션 헤더 ─────────────────────────────────────────────────
def sh(num,name_ko,name_en=""):
    en=f'<span style="font-size:11px;color:{MUT};margin-left:10px;font-family:sans-serif">{name_en}</span>' if name_en else ""
    st.markdown(f"""
<div style="margin:2.2rem 0 1.1rem;font-family:'MaruBuri',serif">
  <span style="font-size:22px;font-weight:700;color:{TXT};line-height:1.3;
    background:rgba(47,129,247,.22);padding:2px 8px;border-radius:4px">
    {num}. {name_ko}
  </span>{en}
</div>""",unsafe_allow_html=True)

def no_data(label=""):
    st.markdown(
        f'<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;'
        f'padding:14px;font-size:10px;color:{MUT};height:262px;display:flex;'
        f'align-items:center;justify-content:center;text-align:center">'
        f'{label}<br><span style="font-size:9px">Actions 실행 후 표시</span></div>',
        unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 상단 고정 KPI (position:fixed — 완벽 고정)
# ══════════════════════════════════════════════════════════════
KPI_SPECS=[
    ("S&P500", "SPX",   market,",.0f",False),
    ("NASDAQ", "NASDAQ",market,",.0f",False),
    ("KOSPI",  "KOSPI", market,",.0f",False),
    ("KOSDAQ", "KOSDAQ",market,",.0f",False),
    ("VIX",    "VIX",   market,".1f", True),
    ("USD/KRW","USDKRW",market,",.0f",True),
    ("US 10Y", "US_10Y",fred,  ".2f", True),
]
kpi_html="".join(kcard_html(l,i,d,f,iv) for l,i,d,f,iv in KPI_SPECS)

st.markdown(f"""
<div id="kpi-fixed" style="
  position:fixed;top:0;left:0;right:0;z-index:99999;
  background:{BG};
  padding:12px 2rem 10px;
  border-bottom:1px solid {BORD}">

  <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:10px">
    <div>
      <div style="font-family:'MaruBuri',serif;font-size:24px;font-weight:700;
        color:{TXT};font-style:italic;line-height:1.2">
        <span style="background:rgba(47,129,247,.28);padding:1px 8px;border-radius:5px">
          Deokyoon's Monitoring
        </span>
      </div>
      <div style="font-size:10px;color:{MUT};margin-top:3px">{now.strftime("%Y-%m-%d %H:%M")} KST · 전일 종가 기준</div>
    </div>
    <div style="text-align:right">
      <div style="background:{rc_bg};color:{rc_t};border:1px solid {rc_bd};
        padding:4px 14px;border-radius:14px;font-size:10px;font-weight:600;
        display:inline-block;font-family:'JetBrains Mono',monospace">● {rt}</div>
      <div style="font-size:9.5px;color:{SUB};margin-top:3px;font-family:'MaruBuri',serif">{reg_explain}</div>
      <div style="font-size:8.5px;color:{MUT};margin-top:1px">{rn}</div>
    </div>
  </div>

  <div style="display:flex;gap:12px;align-items:stretch;min-height:120px">
    <div style="flex:0 0 128px;background:{CARD};border:1px solid {BORD};
      border-radius:10px;overflow:hidden">{get_bull_html()}</div>
    <div class="kpi-grid">{kpi_html}</div>
  </div>
</div>
<div style="height:240px"></div>
""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 1. 시장 심리
# ══════════════════════════════════════════════════════════════
sh("1","시장 심리","Market Sentiment")
c1,c2,c3=st.columns([1.1,0.9,0.9])

with c1:
    vix_s=ser(market,"VIX"); hy_s=ser(fred,"HY_OAS")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    if not vix_s.empty:
        fig.add_trace(go.Scatter(x=vix_s["date"],y=vix_s["value"],name="VIX (좌)",
            line=dict(color=UP,width=2),hovertemplate="<b>VIX</b> %{y:.1f}<extra></extra>"),secondary_y=False)
    if not hy_s.empty:
        fig.add_trace(go.Scatter(x=hy_s["date"],y=hy_s["value"],name="HY OAS % (우)",
            line=dict(color=B4,width=1.8,dash="dot"),hovertemplate="<b>HY OAS</b> %{y:.2f}%<extra></extra>"),secondary_y=True)
    lay=BL("VIX (주축) · HY 신용스프레드 (보조축)",270)
    fig.update_layout(**lay)
    fig.update_yaxes(range=yrange(vix_s),secondary_y=False,gridcolor=G,tickfont=dict(size=9,color=MUT))
    fig.update_yaxes(range=yrange(hy_s),secondary_y=True,showgrid=False,tickfont=dict(size=9,color=B4))
    st.plotly_chart(fig,use_container_width=True)

with c2:
    sp_s=ser(fred,"T10Y2Y_SPREAD")
    if not sp_s.empty:
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=sp_s["date"],y=sp_s["value"],name="2Y-10Y 스프레드",
            line=dict(color=B5,width=2),hovertemplate="<b>스프레드</b> %{y:.2f}%<extra></extra>"))
        fig.add_hline(y=0,line_dash="dot",line_color=MUT,line_width=1.5,
                      annotation_text="장단기 역전 기준",annotation_font_color=MUT,
                      annotation_position="bottom right")
        lay=BL("2Y-10Y 스프레드 — 음수=경기침체 신호",270)
        yr=yrange(sp_s)
        if yr: lay["yaxis"]["range"]=yr
        fig.update_layout(**lay); st.plotly_chart(fig,use_container_width=True)
    else: no_data("T10Y2Y_SPREAD")

with c3:
    fg_row=lat(sentiment,"FEAR_GREED")
    if fg_row is not None:
        fv=fg_row["value"]; fc,fl=fg_color_val(fv)
        fig=go.Figure(go.Indicator(
            mode="gauge+number",value=fv,domain={"x":[0,1],"y":[0,1]},
            number={"font":{"size":38,"family":"MaruBuri","color":TXT}},
            title={"text":f'CNN F&G  ·  {fl}',"font":{"size":11,"color":fc}},
            gauge={
                "axis":{"range":[0,100],"tickwidth":0,
                    "tickvals":[0,25,50,75,100],
                    "ticktext":["극공포","공포","중립","탐욕","극탐욕"],
                    "tickfont":{"size":8,"color":MUT}},
                "bar":{"color":fc,"thickness":0.2},
                "bgcolor":C2,"borderwidth":0,
                "steps":[
                    {"range":[0,25],"color":"rgba(248,81,73,.18)"},
                    {"range":[25,45],"color":"rgba(244,162,97,.12)"},
                    {"range":[45,55],"color":"rgba(110,118,129,.12)"},
                    {"range":[55,75],"color":"rgba(82,183,136,.12)"},
                    {"range":[75,100],"color":"rgba(63,185,80,.18)"},
                ],
                "threshold":{"line":{"color":TXT,"width":2},"thickness":0.7,"value":fv},
            }))
        fig.update_layout(paper_bgcolor=CARD,height=270,margin=dict(l=20,r=20,t=46,b=15))
        st.plotly_chart(fig,use_container_width=True)
    else: no_data("F&G 수집 중")

# ══════════════════════════════════════════════════════════════
# 2. 금리 & 통화정책
#    좌: 한국 (기준금리 step + 국고채 수평선)
#    우: 미국 (FFR step + 국채 3Y/10Y/30Y)
# ══════════════════════════════════════════════════════════════
sh("2","금리 & 통화정책","Rates & Monetary Policy")
c1,c2=st.columns(2)

with c1:
    fig=go.Figure()
    kor_df=kor_base_series(days=730)
    if not kor_df.empty:
        fig.add_trace(go.Scatter(x=kor_df["date"],y=kor_df["value"],name="한국 기준금리",
            line=dict(color=UP,width=2.5,shape="hv"),
            hovertemplate="<b>한국 기준금리</b> %{y:.2f}%<extra></extra>"))
    kor_3y=get_ecos_val("국고채수익률(3년)") or get_ecos_val("국고채(3년)")
    kor_5y=get_ecos_val("국고채수익률(5년)") or get_ecos_val("국고채(5년)")
    for val,lbl,clr in [(kor_3y,"국고채 3Y",B5),(kor_5y,"국고채 5Y",B7)]:
        if val:
            fig.add_hline(y=val,line_dash="dot",line_color=clr,line_width=1.8)
            fig.add_annotation(x=0.02,xref="paper",y=val,yref="y",
                text=f"{lbl} {val:.2f}%",showarrow=False,xanchor="left",yanchor="bottom",
                font=dict(color=clr,size=9,family="JetBrains Mono"),bgcolor=CARD,borderpad=2)
    lay=BL("한국 금리 — 기준금리 · 국고채 3Y/5Y",270)
    all_v=list(kor_df["value"].tolist() if not kor_df.empty else [])
    for v in [kor_3y,kor_5y]:
        if v: all_v.append(v)
    if all_v:
        mn,mx=min(all_v),max(all_v); pad=(mx-mn)*0.15 or 0.3
        lay["yaxis"]["range"]=[mn-pad,mx+pad]
    fig.update_layout(**lay); st.plotly_chart(fig,use_container_width=True)

with c2:
    fig=go.Figure()
    ffr_s=ser(fred,"FFR_UPPER")
    if not ffr_s.empty:
        fig.add_trace(go.Scatter(x=ffr_s["date"],y=ffr_s["value"],name="美 연방기준금리",
            line=dict(color=UP,width=2.5,shape="hv"),
            hovertemplate="<b>美 FFR</b> %{y:.2f}%<extra></extra>"))
    rate_s=[]
    for ind,nm,clr in [("US_3Y","美3년",B5),("US_10Y","美10년",B6),("US_30Y","美30년",B7)]:
        s=ser(fred,ind)
        if not s.empty:
            fig.add_trace(go.Scatter(x=s["date"],y=s["value"],name=nm,
                line=dict(color=clr,width=1.6),hovertemplate=f"<b>{nm}</b> %{{y:.2f}}%<extra></extra>"))
            rate_s.append(s)
    lay=BL("美 금리 — 연방기준금리 · 국채 3Y/10Y/30Y",270)
    yr=yrange(ffr_s,*rate_s)
    if yr: lay["yaxis"]["range"]=yr
    fig.update_layout(**lay); st.plotly_chart(fig,use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 3. 환율 & 달러
# ══════════════════════════════════════════════════════════════
sh("3","환율 & 달러","FX & Dollar")
def norm_ser(df_,ind,days=365):
    s=ser(df_,ind,days)
    if len(s)<2: return pd.DataFrame()
    base=s.iloc[0]["value"]
    out=s.copy(); out["value"]=(out["value"]/base-1)*100
    return out

dxy_n=norm_ser(market,"DXY"); krw_n=norm_ser(market,"USDKRW"); jpy_n=norm_ser(market,"USDJPY")
fig=go.Figure(); all_s=[]
for s_,nm,clr in [(dxy_n,"DXY",B7),(krw_n,"USD/KRW",B5),(jpy_n,"USD/JPY",B3)]:
    if not s_.empty:
        fig.add_trace(go.Scatter(x=s_["date"],y=s_["value"],name=nm,line=dict(width=2),
            hovertemplate=f"<b>{nm}</b> %{{y:+.2f}}%<extra></extra>"))
        all_s.append(s_)
fig.add_hline(y=0,line_dash="dot",line_color=MUT,line_width=1)
if fig.data:
    lay=BL("DXY · USD/KRW · USD/JPY 상대 변화 (1년 전=0)",290)
    yr=yrange(*all_s)
    if yr: lay["yaxis"]["range"]=yr
    lay["yaxis"]["title_text"]="기준대비 (%)"
    fig.update_layout(**lay); st.plotly_chart(fig,use_container_width=True)
else: no_data("환율 데이터")

# ══════════════════════════════════════════════════════════════
# 4. 미국 증시 — 좌: S&P500+MA  /  우: NASDAQ+MA
# ══════════════════════════════════════════════════════════════
sh("4","미국 증시","US Market")
AX=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT))
c1,c2=st.columns(2)

with c1:
    spx=ser(market,"SPX",days=400); spx50=ma(market,"SPX",50,days=400); spx200=ma(market,"SPX",200,days=400)
    fig=go.Figure()
    if not spx.empty:
        fig.add_trace(go.Scatter(x=spx["date"],y=spx["value"],name="S&P500",
            line=dict(color=B5,width=2),fill="tozeroy",fillcolor="rgba(47,129,247,.07)",
            hovertemplate="<b>S&P500</b> %{y:,.0f}<extra></extra>"))
    if not spx50.empty:
        fig.add_trace(go.Scatter(x=spx50["date"],y=spx50["value"],name="MA50",
            line=dict(color=UP,width=1.2,dash="dot")))
    if not spx200.empty:
        fig.add_trace(go.Scatter(x=spx200["date"],y=spx200["value"],name="MA200",
            line=dict(color=MUT,width=1.2,dash="dash")))
    lay=BL("S&P500 + MA50/MA200",270)
    yr=yrange(spx);
    if yr: lay["yaxis"]["range"]=yr
    fig.update_layout(**lay,xaxis=AX); st.plotly_chart(fig,use_container_width=True)

with c2:
    nas=ser(market,"NASDAQ",days=400); nas50=ma(market,"NASDAQ",50,days=400); nas200=ma(market,"NASDAQ",200,days=400)
    fig=go.Figure()
    if not nas.empty:
        fig.add_trace(go.Scatter(x=nas["date"],y=nas["value"],name="NASDAQ",
            line=dict(color=B4,width=2),fill="tozeroy",fillcolor="rgba(88,166,255,.07)",
            hovertemplate="<b>NASDAQ</b> %{y:,.0f}<extra></extra>"))
    if not nas50.empty:
        fig.add_trace(go.Scatter(x=nas50["date"],y=nas50["value"],name="MA50",
            line=dict(color=UP,width=1.2,dash="dot")))
    if not nas200.empty:
        fig.add_trace(go.Scatter(x=nas200["date"],y=nas200["value"],name="MA200",
            line=dict(color=MUT,width=1.2,dash="dash")))
    lay=BL("NASDAQ + MA50/MA200",270)
    yr=yrange(nas)
    if yr: lay["yaxis"]["range"]=yr
    fig.update_layout(**lay,xaxis=AX); st.plotly_chart(fig,use_container_width=True)

US_STOCKS={
    "AAPL":("Apple",3100),"MSFT":("Microsoft",2900),"NVDA":("NVIDIA",2800),
    "AMZN":("Amazon",2000),"GOOGL":("Alphabet",2100),"META":("Meta",1400),
    "BRK_B":("Berkshire",950),"TSLA":("Tesla",800),"LLY":("Eli Lilly",850),
    "JPM":("JPMorgan",750),"AVGO":("Broadcom",780),"V":("Visa",580),
    "UNH":("UnitedHealth",540),"XOM":("ExxonMobil",510),"MA":("Mastercard",470),
    "NFLX":("Netflix",460),"ORCL":("Oracle",430),"PG":("P&G",410),
    "COST":("Costco",400),"HD":("Home Depot",380),"ABBV":("AbbVie",360),
    "WMT":("Walmart",760),"BAC":("BofA",340),"CRM":("Salesforce",320),
    "AMD":("AMD",300),"KO":("Coca-Cola",290),"PEP":("PepsiCo",280),
    "MRK":("Merck",270),"TMO":("ThermoFisher",260),"ADBE":("Adobe",250),
    "ACN":("Accenture",240),"MCD":("McDonald's",230),"TXN":("TI",220),
    "CSCO":("Cisco",210),"IBM":("IBM",200),"GE":("GE",195),
    "CAT":("Caterpillar",190),"NOW":("ServiceNow",185),"INTU":("Intuit",180),
    "RTX":("RTX",175),"AMGN":("Amgen",170),"GS":("Goldman",165),
    "AMAT":("AppMaterials",160),"MU":("Micron",155),"BSX":("Boston Sci",150),
    "AXP":("Amex",145),"BLK":("BlackRock",140),"ETN":("Eaton",135),
    "LMT":("Lockheed",130),"DE":("Deere",125),"SCHW":("Schwab",120),
    "SBUX":("Starbucks",115),"NEE":("NextEra",110),"ADI":("AnalogDev",105),
    "GILD":("Gilead",100),"REGN":("Regeneron",98),"ISRG":("Intuitive",96),
    "HON":("Honeywell",94),"PLD":("Prologis",92),"SYK":("Stryker",90),
    "UBER":("Uber",88),"LRCX":("LamResearch",86),"CB":("Chubb",84),
    "CI":("Cigna",82),"MDT":("Medtronic",80),"CVS":("CVS",78),
    "KLAC":("KLA Corp",76),"MDLZ":("Mondelez",74),"CME":("CME",72),
    "ADP":("ADP",70),"SO":("Southern Co",68),"DUK":("Duke Energy",66),
    "PH":("Parker",62),"WM":("Waste Mgmt",60),"ICE":("ICE",58),
    "SHW":("Sherwin",56),"MMC":("Marsh",54),"ITW":("IllinoisTool",52),
    "TGT":("Target",50),"USB":("US Bancorp",48),"AON":("Aon",46),
    "MCO":("Moody's",44),"MCK":("McKesson",42),"COF":("Capital One",40),
    "FCX":("Freeport",38),"EOG":("EOG",36),"PSA":("Public Storage",34),
    "DLR":("Digital Realty",32),"SPG":("Simon Property",30),"NXPI":("NXP Semi",29),
    "SLB":("SLB",28),"PNC":("PNC",27),"OKE":("ONEOK",25),
    "NEM":("Newmont",24),"EMR":("Emerson",23),"ECL":("Ecolab",22),
    "HUM":("Humana",21),"EL":("Estee Lauder",20),
}
st.plotly_chart(make_treemap(US_STOCKS,"미국 시총 TOP 100 히트맵",h=600),use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 5. 한국 증시 — 좌: KOSPI+MA  /  우: KOSDAQ+MA
# ══════════════════════════════════════════════════════════════
sh("5","한국 증시","Korean Market")
c1,c2=st.columns(2)

with c1:
    ksp=ser(market,"KOSPI",days=400); ksp50=ma(market,"KOSPI",50,days=400); ksp200=ma(market,"KOSPI",200,days=400)
    fig=go.Figure()
    if not ksp.empty:
        fig.add_trace(go.Scatter(x=ksp["date"],y=ksp["value"],name="KOSPI",
            line=dict(color=B5,width=2),fill="tozeroy",fillcolor="rgba(47,129,247,.07)",
            hovertemplate="<b>KOSPI</b> %{y:,.0f}<extra></extra>"))
    if not ksp50.empty:
        fig.add_trace(go.Scatter(x=ksp50["date"],y=ksp50["value"],name="MA50",line=dict(color=UP,width=1.2,dash="dot")))
    if not ksp200.empty:
        fig.add_trace(go.Scatter(x=ksp200["date"],y=ksp200["value"],name="MA200",line=dict(color=MUT,width=1.2,dash="dash")))
    lay=BL("KOSPI + MA50/MA200",270)
    yr=yrange(ksp)
    if yr: lay["yaxis"]["range"]=yr
    fig.update_layout(**lay,xaxis=AX); st.plotly_chart(fig,use_container_width=True)

with c2:
    ksq=ser(market,"KOSDAQ",days=400); ksq50=ma(market,"KOSDAQ",50,days=400); ksq200=ma(market,"KOSDAQ",200,days=400)
    fig=go.Figure()
    if not ksq.empty:
        fig.add_trace(go.Scatter(x=ksq["date"],y=ksq["value"],name="KOSDAQ",
            line=dict(color=B4,width=2),fill="tozeroy",fillcolor="rgba(88,166,255,.07)",
            hovertemplate="<b>KOSDAQ</b> %{y:,.0f}<extra></extra>"))
    if not ksq50.empty:
        fig.add_trace(go.Scatter(x=ksq50["date"],y=ksq50["value"],name="MA50",line=dict(color=UP,width=1.2,dash="dot")))
    if not ksq200.empty:
        fig.add_trace(go.Scatter(x=ksq200["date"],y=ksq200["value"],name="MA200",line=dict(color=MUT,width=1.2,dash="dash")))
    lay=BL("KOSDAQ + MA50/MA200",270)
    yr=yrange(ksq)
    if yr: lay["yaxis"]["range"]=yr
    fig.update_layout(**lay,xaxis=AX); st.plotly_chart(fig,use_container_width=True)

KR_STOCKS={
    "KR_SAMSUNG":("삼성전자",270),"KR_SKHYNIX":("SK하이닉스",130),
    "KR_LGENSOL":("LG에너지",70),"KR_SAMBIO":("삼성바이오",60),
    "KR_HYUNDAI":("현대차",55),"KR_KIA":("기아",45),
    "KR_CELLTRION":("셀트리온",40),"KR_POSCO":("POSCO",38),
    "KR_KB":("KB금융",35),"KR_NAVER":("NAVER",28),
    "KR_ECOPROBM":("에코프로비엠",25),"KR_SAMSDI":("삼성SDI",25),
    "KR_ECOPRO":("에코프로",20),"KR_KAKAO":("카카오",22),
    "KR_LGCHEM":("LG화학",24),"KR_HYUNDAIMOB":("현대모비스",20),
    "KR_LGELEC":("LG전자",20),"KR_SHINHAN":("신한지주",18),
    "KR_SAMSUNG_C":("삼성물산",22),"KR_HANA":("하나금융",18),
    "KR_HANWHAERO":("한화에어로",17),"KR_SEMCO":("삼성전기",16),
    "KR_SAMSLIFE":("삼성생명",15),"KR_SAMSFIRE":("삼성화재",14),
    "KR_SK":("SK",13),"KR_LGINNO":("LG이노텍",12),
    "KR_PFUTURE":("포스코퓨처엠",11),"KR_HDHEAVY":("HD현대중공업",10),
    "KR_DOOSAN":("두산에너빌",9),"KR_IBK":("기업은행",9),
    "KR_WOORI":("우리금융",9),"KR_COWELL":("코웨이",8),
    "KR_HSTEEL":("현대제철",8),"KR_GREYCOREA":("고려아연",25),
    "KR_KEPCO":("한국전력",8),"KR_HMM":("HMM",7),
    "KR_HYBE":("HYBE",10),"KR_KAKAOBK":("카카오뱅크",15),
    "KR_KTNG":("KT&G",13),"KR_HGLOVIS":("현대글로비스",10),
    "KR_SOIL":("S-Oil",9),"KR_LG":("LG",12),
    "KR_KT":("KT",9),"KR_SKT":("SK텔레콤",12),
    "KR_KRAFTON":("크래프톤",15),"KR_SKSQUARE":("SK스퀘어",10),
    "KR_SKINN":("SK이노베이션",9),"KR_HLBI":("에이치엘비",18),
    "KR_KAKAOG":("카카오게임즈",8),"KR_PARLABS":("펄어비스",7),
    "KR_ECOSON":("에코프로에이치엔",6),"KR_CTZPHARM":("셀트리온제약",8),
}
st.plotly_chart(make_treemap(KR_STOCKS,"한국 시총 TOP 60 히트맵 (KOSPI+KOSDAQ)",h=600),use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 6. 글로벌 증시
# ══════════════════════════════════════════════════════════════
sh("6","글로벌 증시","Global Equity")
c1,c2,c3,c4=st.columns(4)
for col,ind,title in [(c1,"NIKKEI","닛케이 (일본)"),(c2,"SHANGHAI","상해 (중국)"),
                       (c3,"HSI","항셍 (홍콩)"),(c4,"NIFTY","니프티 (인도)")]:
    with col:
        s=ser(market,ind); r=lat(market,ind)
        if not s.empty and r is not None:
            chg=pct_chg_1d(ind); clr=UP if chg>=0 else DN
            fig=go.Figure(go.Scatter(x=s["date"],y=s["value"],line=dict(color=clr,width=2),
                fill="tozeroy",fillcolor=f"rgba({'63,185,80' if chg>=0 else '248,81,73'},.07)",
                hovertemplate="%{y:,.0f}<extra></extra>"))
            sign="▲" if chg>=0 else "▼"
            lay=BL(f"{title}\n{r['value']:,.0f}  {sign}{abs(chg):.2f}%",240)
            yr=yrange(s)
            if yr: lay["yaxis"]["range"]=yr
            fig.update_layout(**lay); st.plotly_chart(fig,use_container_width=True)
        else:
            st.markdown(f'<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;'
                        f'padding:12px;font-size:9px;color:{MUT};height:240px;display:flex;'
                        f'align-items:center;justify-content:center;text-align:center">'
                        f'{title}<br>Actions 후 표시</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 7. 원자재 & 암호화폐
# ══════════════════════════════════════════════════════════════
sh("7","원자재 & 암호화폐","Commodities & Crypto")
def dual_chart(s1,s2,n1,n2,c1_,c2_,title):
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    if not s1.empty:
        fig.add_trace(go.Scatter(x=s1["date"],y=s1["value"],name=n1,
            line=dict(color=c1_,width=2),hovertemplate=f"<b>{n1}</b> %{{y:,.2f}}<extra></extra>"),secondary_y=False)
    if not s2.empty:
        fig.add_trace(go.Scatter(x=s2["date"],y=s2["value"],name=n2,
            line=dict(color=c2_,width=1.8),hovertemplate=f"<b>{n2}</b> %{{y:,.2f}}<extra></extra>"),secondary_y=True)
    lay=BL(title,270); fig.update_layout(**lay)
    fig.update_yaxes(range=yrange(s1),secondary_y=False,gridcolor=G,tickfont=dict(size=9,color=MUT))
    fig.update_yaxes(range=yrange(s2),secondary_y=True,showgrid=False,tickfont=dict(size=9,color=c2_))
    return fig

c1,c2,c3=st.columns(3)
with c1:
    g_s=ser(market,"GOLD"); sv_s=ser(market,"SILVER")
    if not g_s.empty or not sv_s.empty: st.plotly_chart(dual_chart(g_s,sv_s,"금($)","은($)",B5,MUT,"금·은"),use_container_width=True)
    else: no_data("금·은")
with c2:
    oil_s=ser(market,"OIL"); cu_s=ser(market,"COPPER")
    if not oil_s.empty or not cu_s.empty: st.plotly_chart(dual_chart(oil_s,cu_s,"WTI($)","구리($)",B6,PUR_DK,"WTI·구리"),use_container_width=True)
    else: no_data("원유·구리")
with c3:
    btc_s=ser(market,"BTC"); eth_s=ser(market,"ETH")
    if not btc_s.empty or not eth_s.empty: st.plotly_chart(dual_chart(btc_s,eth_s,"BTC($)","ETH($)",B5,B3,"Bitcoin·Ethereum"),use_container_width=True)
    else: no_data("BTC·ETH")

# ══════════════════════════════════════════════════════════════
# 8. 유동성
# ══════════════════════════════════════════════════════════════
sh("8","유동성","Liquidity")
c1,c2=st.columns(2)
with c1:
    fed_s=ser(fred,"FED_ASSETS",days=365*5)
    if not fed_s.empty: st.plotly_chart(lc([(fed_s,"연준 자산",B5)],"연준 자산 (QE↑ / QT↓)"),use_container_width=True)
    else: no_data("연준 자산")
with c2:
    m2_s=ser(fred,"M2_US",days=365*5)
    if not m2_s.empty: st.plotly_chart(lc([(m2_s,"美 M2",B6)],"美 M2 통화량"),use_container_width=True)
    else: no_data("美 M2")

# ══════════════════════════════════════════════════════════════
# 9. 미국 매크로
# ══════════════════════════════════════════════════════════════
sh("9","미국 매크로","US Macro")
c1,c2=st.columns(2)
with c1:
    cpi=ser(fred,"US_CORE_CPI",days=365*6); pce=ser(fred,"US_CORE_PCE",days=365*6)
    fig=go.Figure(); yoy_dfs=[]
    for s_,nm,clr,dash in [(cpi,"Core CPI YoY",B5,"solid"),(pce,"Core PCE YoY",PUR_DK,"dot")]:
        if not s_.empty:
            ss=s_.copy(); ss["yoy"]=ss["value"].pct_change(12)*100
            sy=ss.dropna(subset=["yoy"])[["date","yoy"]].rename(columns={"yoy":"value"})
            if not sy.empty:
                fig.add_trace(go.Scatter(x=sy["date"],y=sy["value"],name=nm,
                    line=dict(color=clr,width=2,dash=dash),
                    hovertemplate=f"<b>{nm}</b> %{{y:.2f}}%<extra></extra>"))
                yoy_dfs.append(sy)
    if fig.data:
        fig.add_hline(y=2.0,line_dash="dot",line_color=MUT,line_width=1.5,
                      annotation_text="Fed 목표 2%",annotation_font_color=MUT)
        lay=BL("Core CPI · Core PCE YoY",270)
        yr=yrange(*yoy_dfs)
        if yr: yr=[min(yr[0],1.5),max(yr[1],3.5)]; lay["yaxis"]["range"]=yr
        fig.update_layout(**lay); st.plotly_chart(fig,use_container_width=True)
    else: no_data("CPI·PCE")
with c2:
    nfp=ser(fred,"US_NFP",days=365*4); ic=ser(fred,"US_INIT_CLAIMS",days=365*4)
    if not nfp.empty:
        nfp=nfp.copy(); nfp["mom"]=nfp["value"].diff(); nm_=nfp.dropna(subset=["mom"])
        fig=make_subplots(specs=[[{"secondary_y":True}]])
        fig.add_trace(go.Bar(x=nm_["date"],y=nm_["mom"],name="NFP MoM 천명 (좌)",
            marker_color=[UP if v>=0 else DN for v in nm_["mom"]],
            hovertemplate="<b>NFP MoM</b> %{y:,.0f}천명<extra></extra>"),secondary_y=False)
        if not ic.empty:
            fig.add_trace(go.Scatter(x=ic["date"],y=ic["value"],name="신규 실업급여 (우)",
                line=dict(color=B4,width=1.8,dash="dot"),
                hovertemplate="<b>신규 실업급여</b> %{y:,.0f}명<extra></extra>"),secondary_y=True)
        lay=BL("비농업 고용 MoM + 신규 실업급여",270)
        fig.update_layout(showlegend=True,**lay)
        if yr_:=srange(nm_["mom"]): fig.update_yaxes(range=yr_,secondary_y=False)
        if not ic.empty: fig.update_yaxes(range=yrange(ic),secondary_y=True,showgrid=False,tickfont=dict(size=9,color=B4))
        st.plotly_chart(fig,use_container_width=True)
    else: no_data("NFP")

# ══════════════════════════════════════════════════════════════
# 10. 한국 매크로 & 경제 캘린더
# ══════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="margin:2.2rem 0 1.1rem;font-family:'MaruBuri',serif">
  <span style="font-size:22px;font-weight:700;color:{TXT};line-height:1.3;
    background:rgba(47,129,247,.22);padding:2px 8px;border-radius:4px">
    10. 한국 매크로 & 경제 캘린더
  </span>
</div>""",unsafe_allow_html=True)

col_ecos,col_cal=st.columns([1,1.5])
with col_ecos:
    st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};margin-bottom:8px">한국 매크로 · ECOS TOP 10</div>',unsafe_allow_html=True)
    ECOS_TOP=["한국은행 기준금리","국고채수익률","원/달러","KOSPI","수출","경상수지","M2","소비자물가","실업률","GDP"]
    ECOS_DESC={"한국은행 기준금리":"통화정책 기준","국고채수익률":"시중 자금비용","원/달러":"달러강세=수출기업 수혜",
               "KOSPI":"한국 대형주 종합","수출":"한국 최강 선행지표","경상수지":"흑자=원화 강세",
               "M2":"유동성 지표","소비자물가":"한은 금리결정 핵심","실업률":"낮을수록 양호","GDP":"분기 성장률"}
    if not ecos.empty and "KEYSTAT_NAME" in ecos.columns:
        mask=ecos["KEYSTAT_NAME"].apply(lambda x: any(k in str(x) for k in ECOS_TOP))
        top=ecos[mask].copy()
        if not top.empty:
            cl=[c for c in ["CLASS_NAME","KEYSTAT_NAME","DATA_VALUE","UNIT_NAME"] if c in top.columns]
            rows=""
            for _,r in top[cl].head(10).iterrows():
                kn=str(r.get("KEYSTAT_NAME",""))
                dt=next((v for k,v in ECOS_DESC.items() if k in kn),"")
                dc=f'<div style="font-size:9px;color:{MUT};margin-top:1px">{dt}</div>' if dt else ""
                rows+=(f'<tr style="border-bottom:1px solid {BORD}">'
                       f'<td style="padding:.35rem .7rem;font-size:9px;color:{MUT}">{r.get("CLASS_NAME","")}</td>'
                       f'<td style="padding:.35rem .7rem"><div style="font-size:11px;color:{TXT}">{kn}</div>{dc}</td>'
                       f'<td style="padding:.35rem .7rem;font-size:12px;font-weight:700;text-align:right;font-family:JetBrains Mono;color:{TXT}">{r.get("DATA_VALUE","")}</td>'
                       f'<td style="padding:.35rem .7rem;font-size:9px;color:{MUT};text-align:right">{r.get("UNIT_NAME","")}</td>'
                       f'</tr>')
            TH=f"padding:.45rem .7rem;text-align:left;font-size:9px;color:{MUT};font-weight:500;border-bottom:1px solid {BORD}"
            st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;overflow:hidden">
<table style="width:100%;border-collapse:collapse">
  <thead><tr style="background:{C2}">
    <th style="{TH}">분류</th><th style="{TH}">지표</th>
    <th style="{TH};text-align:right">현재값</th><th style="{TH};text-align:right">단위</th>
  </tr></thead><tbody>{rows}</tbody>
</table></div>""",unsafe_allow_html=True)

with col_cal:
    st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};margin-bottom:4px">경제 캘린더</div>',unsafe_allow_html=True)
    nav1,nav2,nav3=st.columns([1,3,1])
    with nav1:
        if st.button("◀ 이전달",key="cal_prev"):
            if st.session_state.cal_month==1: st.session_state.cal_month=12; st.session_state.cal_year-=1
            else: st.session_state.cal_month-=1
            st.rerun()
    with nav2:
        mo=["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"]
        st.markdown(f'<div style="text-align:center;font-size:15px;font-weight:700;color:{TXT};padding:6px 0">{st.session_state.cal_year}년 {mo[st.session_state.cal_month-1]}</div>',unsafe_allow_html=True)
    with nav3:
        if st.button("다음달 ▶",key="cal_next"):
            if st.session_state.cal_month==12: st.session_state.cal_month=1; st.session_state.cal_year+=1
            else: st.session_state.cal_month+=1
            st.rerun()

    CAL_EVENTS={
        date(2026,5,29):[("bok","한국 금통위")],
        date(2026,6,5): [("econ","美 NFP (5월)")],
        date(2026,6,9): [("fomc","FOMC 금리결정")],
        date(2026,6,11):[("econ","美 CPI (5월)")],
        date(2026,6,28):[("bok","한국 금통위")],
        date(2026,7,2): [("econ","美 NFP (6월)")],
        date(2026,7,10):[("bok","한국 금통위")],
        date(2026,7,15):[("econ","美 CPI (6월)")],
        date(2026,7,22):[("earn","META 실적")],
        date(2026,7,23):[("earn","GOOGL 실적")],
        date(2026,7,28):[("fomc","FOMC 금리결정"),("earn","MSFT 실적")],
        date(2026,7,29):[("earn","AAPL 실적")],
        date(2026,8,1): [("earn","AMZN 실적")],
        date(2026,8,7): [("econ","美 NFP (7월)")],
        date(2026,8,12):[("econ","美 CPI (7월)")],
        date(2026,8,27):[("earn","NVDA 실적"),("bok","한국 금통위")],
        date(2026,9,4): [("econ","美 NFP (8월)")],
        date(2026,9,9): [("econ","美 CPI (8월)")],
        date(2026,9,15):[("fomc","FOMC 금리결정")],
        date(2026,10,2):[("econ","美 NFP (9월)")],
        date(2026,10,14):[("econ","美 CPI (9월)")],
        date(2026,10,16):[("bok","한국 금통위")],
        date(2026,10,27):[("fomc","FOMC 금리결정")],
        date(2026,11,6):[("econ","美 NFP (10월)")],
        date(2026,11,10):[("econ","美 CPI (10월)")],
        date(2026,11,27):[("bok","한국 금통위")],
        date(2026,12,4):[("econ","美 NFP (11월)")],
        date(2026,12,8):[("fomc","FOMC 금리결정")],
        date(2026,12,9):[("econ","美 CPI (11월)")],
    }
    TC={
        "fomc":(B5,"rgba(47,129,247,.2)"),
        "bok": (PUR_DK,"rgba(88,166,255,.2)"),
        "econ":(UP,"rgba(63,185,80,.2)"),
        "earn":("#F4A261","rgba(244,162,97,.2)"),
    }

    def build_calendar(year,month,events):
        cal_lib.setfirstweekday(0)
        weeks=cal_lib.monthcalendar(year,month); today=date.today()
        day_hd=""
        for dn,dc2 in [("월",TXT),("화",TXT),("수",TXT),("목",TXT),("금",TXT),("토",B4),("일",DN)]:
            day_hd+=f'<div style="text-align:center;font-size:10px;font-weight:600;color:{dc2};padding:5px 0">{dn}</div>'
        cells=""
        for wk in weeks:
            for day in wk:
                if day==0:
                    cells+=f'<div style="background:{BG};border-radius:6px;min-height:72px"></div>'
                else:
                    d=date(year,month,day); is_today=(d==today); is_past=(d<today)
                    evs=events.get(d,[])
                    ev_html=""
                    for ev_type,ev_name in evs[:2]:
                        ec,eb=TC.get(ev_type,(MUT,C2))
                        ev_short=ev_name[:10]+("…" if len(ev_name)>10 else "")
                        ev_html+=(f'<div style="background:{eb};color:{ec};border-radius:3px;'
                                  f'font-size:8px;padding:1px 4px;margin-top:2px;overflow:hidden;'
                                  f'white-space:nowrap;font-family:JetBrains Mono,monospace">{ev_short}</div>')
                    if len(evs)>2:
                        ev_html+=f'<div style="font-size:8px;color:{MUT}">+{len(evs)-2}</div>'
                    if is_today: bg_d=B5; brd=f"2px solid {B5}"; day_c="#FFFFFF"
                    elif is_past: bg_d=BG; brd=f"1px solid {BORD}"; day_c=MUT
                    else: bg_d=CARD; brd=f"1px solid {BORD}"; day_c=TXT
                    cells+=(f'<div style="background:{bg_d};border:{brd};border-radius:6px;'
                             f'padding:5px;min-height:72px;overflow:hidden">'
                             f'<div style="font-size:12px;font-weight:{"700" if is_today else "400"};color:{day_c}">{day}</div>'
                             f'{ev_html}</div>')
        legend=""
        for lbl,et in [("FOMC","fomc"),("금통위","bok"),("경제지표","econ"),("실적","earn")]:
            ec,eb=TC[et]
            legend+=f'<span style="background:{eb};color:{ec};border-radius:3px;font-size:9px;padding:2px 7px;margin-right:6px;font-family:JetBrains Mono,monospace">{lbl}</span>'
        return f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;padding:12px">
  <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:3px;margin-bottom:3px">{day_hd}</div>
  <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:3px">{cells}</div>
  <div style="margin-top:10px;padding-top:8px;border-top:1px solid {BORD}">{legend}</div>
</div>"""

    st.markdown(build_calendar(st.session_state.cal_year,st.session_state.cal_month,CAL_EVENTS),unsafe_allow_html=True)

# ── 푸터 ─────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:3rem;padding-top:1rem;border-top:1px solid {BORD};
  font-size:10px;color:{MUT};text-align:center;font-family:'MaruBuri',serif">
  FRED · yfinance · CNN Fear&amp;Greed · 한국은행 ECOS · 매일 KST 07:00 자동수집 · 전일 종가 기준
</div>
""",unsafe_allow_html=True)
