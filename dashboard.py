"""
Deokyoon's Monitoring — v8
연베이지 테마 + 마루부리 + 보라 하이라이트
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime
import base64

st.set_page_config(page_title="Deokyoon's Monitoring",
                   page_icon="◈", layout="wide",
                   initial_sidebar_state="collapsed")

# ── 연베이지 + 블루 + 보라 팔레트 ─────────────────────────────
BG   = "#F5F0E5"   # 연베이지 (메인)
CARD = "#FFFFFF"   # 화이트 카드
C2   = "#FAF6EC"   # 오프화이트
BORD = "#E5DDD0"   # 따뜻한 보더
G    = "#EFE8D6"   # 차트 그리드

TXT  = "#2A2620"   # 다크 텍스트
SUB  = "#5A5246"   # 서브 텍스트
MUT  = "#8C7F6E"   # 뮤트 브라운

# 보라 (하이라이트)
PUR_HI = "#E0CCF5" # 파스텔 보라 (밑줄 하이라이트)
PUR_DK = "#7E22CE" # 진한 보라 (포인트)

# 블루 (데이터, 짙은 톤)
B1 = "#DBEAFE"
B3 = "#60A5FA"
B4 = "#3B82F6"
B5 = "#2563EB"
B6 = "#1D4ED8"
B7 = "#1E40AF"
B8 = "#1E3A8A"

UP = B5            # 상승 = blue-600
DN = B8            # 하락 = blue-900
AC = B6            # 액센트

def up_dn(d): return UP if (d or 0) >= 0 else DN

# ── CSS (마루부리 + 자간/행간) ────────────────────────────────
st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
@font-face {{
  font-family: 'MaruBuri';
  src: url('https://cdn.jsdelivr.net/gh/wkdtjsgur100/maruburifonts@1.0/static/MaruBuri/MaruBuri-Regular.woff2') format('woff2'),
       url('https://hangeul.pstatic.net/hangeul_static/webfont/maruburi/MaruBuri-Regular.woff') format('woff');
  font-weight: 400;
}}
@font-face {{
  font-family: 'MaruBuri';
  src: url('https://cdn.jsdelivr.net/gh/wkdtjsgur100/maruburifonts@1.0/static/MaruBuri/MaruBuri-Bold.woff2') format('woff2');
  font-weight: 700;
}}
html,body,[class*="css"]{{
  background:{BG}!important;color:{TXT}!important;
  font-family:'MaruBuri','Gowun Batang','Noto Serif KR',serif!important;
  letter-spacing:0.015em!important;line-height:1.3!important;
}}
.block-container{{padding:0 2rem 3rem!important;max-width:100%!important;background:{BG}!important}}
[data-testid="stAppViewContainer"]{{background:{BG}!important}}
[data-testid="stHeader"]{{background:{BG}!important;border-bottom:1px solid {BORD}!important;height:0}}
section[data-testid="stSidebar"]{{display:none}}
#MainMenu,footer,header{{visibility:hidden}}
p,span,div,label,th,td{{color:{TXT}!important;letter-spacing:0.015em!important;line-height:1.3!important}}
.kpi-grid {{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;flex:1}}
</style>
""", unsafe_allow_html=True)

# ── 데이터 로드 ───────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
ASSET_DIR = Path(__file__).parent / "assets"

@st.cache_data(ttl=3600)
def load(fn):
    f = DATA_DIR / fn
    if not f.exists(): return pd.DataFrame()
    df = pd.read_parquet(f)
    if "date" in df.columns: df["date"] = pd.to_datetime(df["date"])
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
    try: return round((s.iloc[-1]["value"]/s.iloc[-2]["value"]-1)*100,2)
    except: return 0.0

def get_ecos_val(keyword):
    if ecos.empty or "KEYSTAT_NAME" not in ecos.columns: return None
    r = ecos[ecos["KEYSTAT_NAME"].str.contains(keyword, na=False)]
    if r.empty: return None
    try: return float(str(r.iloc[0]["DATA_VALUE"]).replace(",",""))
    except: return None

# ── Y축 타이트 스케일링 헬퍼 ─────────────────────────────────
def yrange(*dfs, pad_pct=0.08):
    """차트에 데이터가 꽉 차도록 Y축 범위 계산"""
    vals=[]
    for df in dfs:
        if isinstance(df,pd.DataFrame) and not df.empty and "value" in df.columns:
            vals.extend(df["value"].dropna().tolist())
    if not vals: return None
    mn,mx=min(vals),max(vals)
    if mn==mx: return [mn-1, mx+1]
    pad=(mx-mn)*pad_pct
    return [mn-pad, mx+pad]

# ── 스파크라인 ───────────────────────────────────────────────
def spark(df, ind, color=B5, days=90, w=70, h=28):
    s = ser(df, ind, days)
    vals = s["value"].dropna().tolist() if not s.empty else []
    if len(vals)<3: return ""
    mn,mx=min(vals),max(vals); mg=3
    if mn==mx:
        pts=[(round(i*w/(len(vals)-1),1),h/2) for i in range(len(vals))]
    else:
        pts=[(round(i*w/(len(vals)-1),1),
              round(h-mg-(v-mn)/(mx-mn)*(h-mg*2),1)) for i,v in enumerate(vals)]
    ld="M "+" L ".join(f"{x},{y}" for x,y in pts)
    fd=ld+f" L {pts[-1][0]},{h} L {pts[0][0]},{h} Z"
    gid=f"g{''.join(c for c in ind if c.isalpha())[:6]}"
    lx,ly=pts[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity="0.25"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
            f'</linearGradient></defs>'
            f'<path d="{fd}" fill="url(#{gid})"/>'
            f'<path d="{ld}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{lx}" cy="{ly}" r="2" fill="{color}"/>'
            f'</svg>')

# ── 황소 이미지 ──────────────────────────────────────────────
def get_bull_html():
    bp = ASSET_DIR / "bull.png"
    if bp.exists():
        try:
            with open(bp,"rb") as f: b64=base64.b64encode(f.read()).decode()
            return (f'<div style="background:{CARD};border:1px solid {BORD};'
                    f'border-radius:10px;padding:6px;display:flex;align-items:center;justify-content:center;height:100%">'
                    f'<img src="data:image/png;base64,{b64}" '
                    f'style="height:108px;width:auto;border-radius:6px;display:block"></div>')
        except: pass
    return (f'<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;'
            f'height:128px;display:flex;align-items:center;justify-content:center;'
            f'flex-direction:column;font-size:11px;color:{MUT}">'
            f'<div style="font-size:48px">🐂</div>'
            f'<div>assets/bull.png</div></div>')

# ── 지표 설명 ─────────────────────────────────────────────────
DESC = {
    "VIX":    "옵션 변동성 · 15↓안정",
    "SOX":    "美 반도체 · 한국선행",
    "SPX":    "S&P500 · 위험선호",
    "NASDAQ": "나스닥 · 고금리민감",
    "KOSPI":  "韓 대형주 · 외국인민감",
    "USDKRW": "원달러 · 1,300↑주의",
    "US_10Y": "美 10년 · 자본비용",
}

# ── Plotly 기본 레이아웃 (라이트 테마) ────────────────────────
def BL(title="", h=270):
    return dict(
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(family="JetBrains Mono",size=10,color=SUB),
        title=dict(text=title,font=dict(size=11,color=SUB,family="MaruBuri,serif"),x=0.01),
        height=h, margin=dict(l=8,r=8,t=28,b=8),
        legend=dict(orientation="h",y=1.08,x=0,font=dict(size=9,color=SUB),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=CARD,bordercolor=BORD,
                        font=dict(family="JetBrains Mono",size=10,color=TXT)),
        xaxis=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT)),
        yaxis=dict(showgrid=True,gridcolor=G,zeroline=False,showline=False,tickfont=dict(size=9,color=MUT)),
    )

def lc(traces, title="", h=270, zero=False):
    fig=go.Figure()
    all_dfs=[]
    for df,nm,clr in traces:
        if isinstance(df,pd.DataFrame) and not df.empty:
            fig.add_trace(go.Scatter(x=df["date"],y=df["value"],name=nm,
                line=dict(color=clr,width=2),
                hovertemplate=f"<b>{nm}</b> %{{y:.2f}}<extra></extra>"))
            all_dfs.append(df)
    if zero: fig.add_hline(y=0,line_dash="dot",line_color=MUT,line_width=1)
    lay=BL(title,h)
    yr=yrange(*all_dfs)
    if yr: lay["yaxis"]["range"]=yr
    fig.update_layout(**lay)
    return fig

# ── 레짐 ──────────────────────────────────────────────────────
def regime():
    v=lat(market,"VIX"); h=lat(fred,"HY_OAS")
    if v is None or h is None: return "neu","NEUTRAL","데이터 수집 중","—"
    vv,hv=v["value"],h["value"]
    if vv>28 or hv>5.5:
        return "risk","RISK-OFF",f"VIX {vv:.1f} · HY {hv:.2f}%","위험회피 국면 — 현금 비중 확대, 방어주·금"
    elif vv<16 and hv<3.5:
        return "on","RISK-ON",f"VIX {vv:.1f} · HY {hv:.2f}%","위험선호 국면 — 성장주·고베타 종목 유리"
    else:
        return "neu","NEUTRAL",f"VIX {vv:.1f} · HY {hv:.2f}%","관망 국면 — 큰 베팅보다 분할매수·관찰 중심"
rc,rt,rn,reg_explain=regime()
RC={"risk":(B6,"#FEF2F2","#FECACA"),
    "on":  (B4,"#EFF6FF","#BFDBFE"),
    "neu": (SUB,"#FAFAF0","#E5DDD0")}
rc_t,rc_bg,rc_bd=RC[rc]

# ══════════════════════════════════════════════════════════════
# 상단 고정 헤더 (Title + Bull + KPI bar)
# ══════════════════════════════════════════════════════════════
now=datetime.now()

# KPI 카드 HTML
def kcard_html(label, ind, df, fmt=".2f", inv=False):
    r=lat(df,ind); d=dlt(df,ind)
    clr=up_dn(d if not inv else ((-d) if d else None))
    desc=DESC.get(ind,"")
    desc_h=f'<div style="font-size:8px;color:{MUT};line-height:1.2;margin:1px 0 3px">{desc}</div>'
    CS=(f"background:{CARD};border:1px solid {BORD};border-left:3px solid {clr};"
        f"border-radius:8px;padding:8px 9px;font-family:'MaruBuri',serif;"
        f"display:flex;justify-content:space-between;gap:6px;align-items:stretch;height:100%")
    if r is None:
        return (f'<div style="{CS.replace(clr,MUT,1)}">'
                f'<div style="flex:1"><div style="font-size:9px;color:{MUT};text-transform:uppercase">{label}</div>'
                f'{desc_h}<div style="font-size:16px;font-weight:700">—</div></div></div>')
    vs=format(r["value"],fmt)
    dh=""
    if d is not None:
        sym="▲" if d>0 else "▼"
        dh=(f'<div style="font-size:8.5px;font-weight:600;color:{clr};margin-top:1px;line-height:1.2">'
            f'{sym}{abs(d):.2f} <span style="color:{MUT};font-weight:400">전일</span></div>')
    spk=spark(df,ind,color=clr,w=64,h=24)
    spk_div=f'<div style="flex:0 0 auto;align-self:center;opacity:.65">{spk}</div>' if spk else ""
    return (f'<div style="{CS}">'
            f'<div style="flex:1;min-width:0">'
            f'<div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.05em">{label}</div>'
            f'{desc_h}'
            f'<div style="font-size:16px;font-weight:700;color:{TXT};line-height:1.1">{vs}</div>'
            f'{dh}'
            f'</div>'
            f'{spk_div}'
            f'</div>')

kpi_specs=[
    ("VIX",     "VIX",    market, ".1f",   True),
    ("SOX",     "SOX",    market, ",.0f",  False),
    ("S&P500",  "SPX",    market, ",.0f",  False),
    ("NASDAQ",  "NASDAQ", market, ",.0f",  False),
    ("KOSPI",   "KOSPI",  market, ",.0f",  False),
    ("USD/KRW", "USDKRW", market, ",.0f",  True),
    ("US 10Y",  "US_10Y", fred,   ".2f",   True),
]
kpi_html="".join(kcard_html(l,i,d,f,iv) for l,i,d,f,iv in kpi_specs)

header_html=f"""
<div style="position:sticky;top:0;background:{BG};z-index:100;padding:14px 0 10px;
  border-bottom:1px solid {BORD};margin:0 -2rem 1.4rem;padding-left:2rem;padding-right:2rem">

  <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:12px">
    <div>
      <div style="font-family:'MaruBuri',serif;font-size:24px;font-weight:700;color:{TXT};line-height:1.2">
        Deokyoon's <span style="background:linear-gradient(180deg,transparent 55%,{PUR_HI} 55%);padding:0 3px">Monitoring</span>
      </div>
      <div style="font-size:10px;color:{MUT};margin-top:3px">{now.strftime("%Y-%m-%d %H:%M")} KST · 전일 종가 기준</div>
    </div>
    <div style="text-align:right">
      <div style="background:{rc_bg};color:{rc_t};border:1px solid {rc_bd};
        padding:4px 12px;border-radius:14px;font-size:10px;font-weight:600;
        display:inline-block;font-family:'JetBrains Mono',monospace">● {rt}</div>
      <div style="font-size:9.5px;color:{SUB};margin-top:4px;font-family:'MaruBuri',serif">{reg_explain}</div>
      <div style="font-size:8.5px;color:{MUT};margin-top:1px">{rn}</div>
    </div>
  </div>

  <div style="display:flex;gap:12px;align-items:stretch">
    <div style="flex:0 0 138px">{get_bull_html()}</div>
    <div class="kpi-grid">{kpi_html}</div>
  </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# ── 섹션 헤더 (보라 하이라이트) ──────────────────────────────
def sh(num, name_ko, name_en=""):
    en=f'<span style="font-size:11px;color:{MUT};margin-left:10px;font-family:sans-serif">{name_en}</span>' if name_en else ""
    st.markdown(f"""
<div style="margin:2.2rem 0 1.1rem;font-family:'MaruBuri',serif">
  <span style="font-size:22px;font-weight:700;color:{TXT};line-height:1.3;
    background:linear-gradient(180deg,transparent 55%,{PUR_HI} 55%);padding:0 4px">
    {num}. {name_ko}
  </span>{en}
</div>""", unsafe_allow_html=True)

def no_data(label="데이터 수집 중"):
    st.markdown(
        f'<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;'
        f'padding:14px;font-size:10px;color:{MUT};height:262px;display:flex;'
        f'align-items:center;justify-content:center;text-align:center">'
        f'{label}<br><span style="font-size:9px">Actions 실행 후 표시</span></div>',
        unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 1. 시장 심리
# ══════════════════════════════════════════════════════════════
sh("1","시장 심리","Market Sentiment")
c1,c2=st.columns(2)
with c1:
    vix_s=ser(market,"VIX"); hy_s=ser(fred,"HY_OAS")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    if not vix_s.empty:
        fig.add_trace(go.Scatter(x=vix_s["date"],y=vix_s["value"],name="VIX (좌)",
            line=dict(color=B5,width=2),
            hovertemplate="<b>VIX</b> %{y:.1f}<extra></extra>"),secondary_y=False)
    if not hy_s.empty:
        fig.add_trace(go.Scatter(x=hy_s["date"],y=hy_s["value"],name="HY OAS % (우)",
            line=dict(color=PUR_DK,width=1.8,dash="dot"),
            hovertemplate="<b>HY OAS</b> %{y:.2f}%<extra></extra>"),secondary_y=True)
    lay=BL("VIX (주축) · HY 신용스프레드 (보조축)",270)
    fig.update_layout(**lay)
    fig.update_yaxes(range=yrange(vix_s),secondary_y=False,gridcolor=G,tickfont=dict(size=9,color=MUT))
    fig.update_yaxes(range=yrange(hy_s),secondary_y=True,showgrid=False,tickfont=dict(size=9,color=PUR_DK))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fg_row=lat(sentiment,"FEAR_GREED")
    if fg_row is not None:
        fv=fg_row["value"]
        if fv<25:   fc,fl=B8,"극도공포"
        elif fv<45: fc,fl=B6,"공포"
        elif fv<55: fc,fl=SUB,"중립"
        elif fv<75: fc,fl=B4,"탐욕"
        else:       fc,fl=B3,"극도탐욕"
        fig=go.Figure(go.Indicator(
            mode="gauge+number",value=fv,
            domain={"x":[0,1],"y":[0,1]},
            number={"font":{"size":42,"family":"MaruBuri","color":TXT}},
            title={"text":f'{fl} · CNN Fear & Greed<br><span style="font-size:9px;color:{MUT}">0=극도공포 · 25=공포 · 50=중립 · 75=탐욕 · 100=극도탐욕</span>',
                   "font":{"size":12,"color":fc}},
            gauge={"axis":{"range":[0,100],"tickwidth":0,
                           "tickvals":[0,25,50,75,100],"tickfont":{"size":8,"color":MUT}},
                   "bar":{"color":fc,"thickness":0.2},
                   "bgcolor":C2,"borderwidth":0,
                   "steps":[{"range":[0,25],"color":"rgba(30,58,138,0.12)"},
                             {"range":[25,45],"color":"rgba(29,78,216,0.1)"},
                             {"range":[45,55],"color":"rgba(90,82,70,0.08)"},
                             {"range":[55,75],"color":"rgba(59,130,246,0.1)"},
                             {"range":[75,100],"color":"rgba(96,165,250,0.12)"}],
                   "threshold":{"line":{"color":TXT,"width":2},"thickness":0.7,"value":fv}}))
        fig.update_layout(paper_bgcolor=CARD,height=270,margin=dict(l=30,r=30,t=20,b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data("F&G 수집 중")

# ══════════════════════════════════════════════════════════════
# 2. 금리 & 통화정책
# ══════════════════════════════════════════════════════════════
sh("2","금리 & 통화정책","Rates & Monetary Policy")
c1,c2=st.columns(2)
with c1:
    fig=go.Figure(); rate_series=[]
    for ind,nm,clr in [("US_3Y","美3년",B3),("US_10Y","美10년",B5),("US_30Y","美30년",B7)]:
        s=ser(fred,ind)
        if not s.empty:
            fig.add_trace(go.Scatter(x=s["date"],y=s["value"],name=nm,line=dict(color=clr,width=2),
                hovertemplate=f"<b>{nm}</b> %{{y:.2f}}%<extra></extra>"))
            rate_series.append(s)
    kor_base=get_ecos_val("한국은행 기준금리")
    kor_3y=get_ecos_val("국고채수익률(3년)")
    if kor_base:
        fig.add_hline(y=kor_base,line_dash="dot",line_color=PUR_DK,line_width=1.5,
                     annotation_text=f"한국 기준금리 {kor_base:.2f}%",
                     annotation_font_color=PUR_DK,annotation_position="right")
    if kor_3y:
        fig.add_hline(y=kor_3y,line_dash="dash",line_color=MUT,line_width=1.2,
                     annotation_text=f"한국 국고채3Y {kor_3y:.2f}%",
                     annotation_font_color=MUT,annotation_position="right")
    if fig.data:
        lay=BL("美 3Y · 10Y · 30Y + 한국 기준금리",270)
        if rate_series:
            extras=[kor_base,kor_3y]
            vals=[v for v in extras if v is not None]
            yr=yrange(*rate_series)
            if yr and vals:
                yr=[min(yr[0],min(vals)-0.3), max(yr[1],max(vals)+0.3)]
            if yr: lay["yaxis"]["range"]=yr
        fig.update_layout(**lay)
        st.plotly_chart(fig, use_container_width=True)
    else: no_data("금리 데이터")

with c2:
    sp=ser(fred,"T10Y2Y_SPREAD"); ffr=ser(fred,"FFR_UPPER")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    if not sp.empty:
        fig.add_trace(go.Scatter(x=sp["date"],y=sp["value"],name="2Y-10Y (좌)",
            line=dict(color=B5,width=2),
            hovertemplate="<b>스프레드</b> %{y:.2f}%<extra></extra>"),secondary_y=False)
        fig.add_hline(y=0,line_dash="dot",line_color=MUT,line_width=1,secondary_y=False)
    if not ffr.empty:
        fig.add_trace(go.Scatter(x=ffr["date"],y=ffr["value"],name="기준금리 (우)",
            line=dict(color=PUR_DK,width=1.8),
            hovertemplate="<b>FFR</b> %{y:.2f}%<extra></extra>"),secondary_y=True)
    lay=BL("2Y-10Y 스프레드 (-=침체신호) · 美 연방기준금리",270)
    fig.update_layout(**lay)
    fig.update_yaxes(range=yrange(sp),secondary_y=False,gridcolor=G,tickfont=dict(size=9,color=MUT))
    fig.update_yaxes(range=yrange(ffr),secondary_y=True,showgrid=False,tickfont=dict(size=9,color=PUR_DK))
    if fig.data: st.plotly_chart(fig, use_container_width=True)
    else: no_data("스프레드")

# ══════════════════════════════════════════════════════════════
# 3. 환율 & 달러
# ══════════════════════════════════════════════════════════════
sh("3","환율 & 달러","FX & Dollar")
def norm_ser(df, ind, days=365):
    s=ser(df,ind,days)
    if len(s)<2: return pd.DataFrame()
    base=s.iloc[0]["value"]
    out=s.copy(); out["value"]=(out["value"]/base-1)*100
    return out
dxy_n=norm_ser(market,"DXY"); krw_n=norm_ser(market,"USDKRW"); jpy_n=norm_ser(market,"USDJPY")
fig=go.Figure(); all_s=[]
for s,nm,clr in [(dxy_n,"DXY (달러강도)",B7),(krw_n,"USD/KRW (원화약세↑)",B5),(jpy_n,"USD/JPY (엔화약세↑)",B3)]:
    if not s.empty:
        fig.add_trace(go.Scatter(x=s["date"],y=s["value"],name=nm,line=dict(width=2),
            hovertemplate=f"<b>{nm}</b> %{{y:+.2f}}%<extra></extra>"))
        all_s.append(s)
fig.add_hline(y=0,line_dash="dot",line_color=MUT,line_width=1)
if fig.data:
    lay=BL("DXY · USD/KRW · USD/JPY 상대 변화 (1년 전=0, 위=달러강세)",290)
    yr=yrange(*all_s)
    if yr: lay["yaxis"]["range"]=yr
    lay["yaxis"]["title_text"]="기준대비 (%)"
    fig.update_layout(**lay)
    st.plotly_chart(fig, use_container_width=True)
else: no_data("환율 데이터")

# ══════════════════════════════════════════════════════════════
# 4. 유동성
# ══════════════════════════════════════════════════════════════
sh("4","유동성","Liquidity")
c1,c2=st.columns(2)
with c1:
    fed_s=ser(fred,"FED_ASSETS",days=365*5)
    if not fed_s.empty:
        st.plotly_chart(lc([(fed_s,"연준 자산",B5)],"연준 자산 (QE↑ / QT↓)"),use_container_width=True)
    else: no_data("연준 자산 (FED_ASSETS)")
with c2:
    m2_s=ser(fred,"M2_US",days=365*5)
    if not m2_s.empty:
        st.plotly_chart(lc([(m2_s,"美 M2",B6)],"美 M2 통화량 (증가=자산가격 상승압력)"),use_container_width=True)
    else: no_data("美 M2 (M2_US)")

# ══════════════════════════════════════════════════════════════
# 5. 미국 증시
# ══════════════════════════════════════════════════════════════
sh("5","미국 증시","US Market")
c1,c2=st.columns(2)
with c1:
    spx=ser(market,"SPX"); nas=ser(market,"NASDAQ")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    if not spx.empty:
        fig.add_trace(go.Scatter(x=spx["date"],y=spx["value"],name="S&P500 (좌)",
            line=dict(color=B5,width=2),
            hovertemplate="<b>S&P500</b> %{y:,.0f}<extra></extra>"),secondary_y=False)
    if not nas.empty:
        fig.add_trace(go.Scatter(x=nas["date"],y=nas["value"],name="NASDAQ (우)",
            line=dict(color=PUR_DK,width=2),
            hovertemplate="<b>NASDAQ</b> %{y:,.0f}<extra></extra>"),secondary_y=True)
    lay=BL("S&P500 · NASDAQ",270)
    fig.update_layout(**lay)
    fig.update_yaxes(range=yrange(spx),secondary_y=False,gridcolor=G,tickfont=dict(size=9,color=MUT))
    fig.update_yaxes(range=yrange(nas),secondary_y=True,showgrid=False,tickfont=dict(size=9,color=PUR_DK))
    st.plotly_chart(fig, use_container_width=True)
with c2:
    sox=ser(market,"SOX")
    if not sox.empty:
        st.plotly_chart(lc([(sox,"SOX 반도체",B4)],"필라델피아 반도체 (SOX) — 한국 반도체 선행"),
                        use_container_width=True)
    else: no_data("SOX")

# ── 美 히트맵 (TOP 30, squarify) ─────────────────────────────
US_STOCKS={
    "AAPL":("Apple",3100),"MSFT":("Microsoft",2900),"NVDA":("NVIDIA",2800),
    "AMZN":("Amazon",2000),"GOOGL":("Alphabet",2100),"META":("Meta",1400),
    "BRK_B":("Berkshire",950),"TSLA":("Tesla",800),"LLY":("Eli Lilly",850),
    "JPM":("JPMorgan",750),
}
def make_treemap(stocks, title=""):
    labels,parents,values,colors,cdata=[],[],[],[],[]
    for ind,(name,mcap) in stocks.items():
        chg=pct_chg_1d(ind)
        labels.append(name); parents.append(""); values.append(mcap); colors.append(chg)
        sign="▲" if chg>=0 else "▼"
        cdata.append(f"{sign}{abs(chg):.2f}%")
    fig=go.Figure(go.Treemap(
        labels=labels,parents=parents,values=values,customdata=cdata,
        texttemplate="<b>%{label}</b><br>%{customdata}",
        textfont=dict(size=11,color="#FFFFFF",family="MaruBuri"),
        tiling=dict(packing="squarify",squarifyratio=1),
        marker=dict(
            colors=colors,
            colorscale=[[0.0,B8],[0.35,B6],[0.47,"#E5DDD0"],[0.53,"#E5DDD0"],[0.65,B4],[1.0,B3]],
            cmid=0,cmin=-5,cmax=5,showscale=True,
            colorbar=dict(thickness=10,len=0.5,ticksuffix="%",
                tickfont=dict(size=9,color=MUT),
                title=dict(text="등락",font=dict(size=9,color=MUT))),
        ),
        hovertemplate="<b>%{label}</b><br>전일대비: %{customdata}<extra></extra>",
    ))
    fig.update_layout(title=dict(text=title,font=dict(size=11,color=SUB,family="MaruBuri"),x=0.01),
        paper_bgcolor=CARD,height=420,margin=dict(l=0,r=0,t=30,b=0))
    return fig

st.plotly_chart(make_treemap(US_STOCKS,"미국 시총 TOP 10 히트맵 (TOP 100 확장은 다음 단계)"),
                use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 6. 한국 증시
# ══════════════════════════════════════════════════════════════
sh("6","한국 증시","Korean Market")
c1,c2=st.columns(2)
with c1:
    ksp=ser(market,"KOSPI"); ksq=ser(market,"KOSDAQ")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    if not ksp.empty:
        fig.add_trace(go.Scatter(x=ksp["date"],y=ksp["value"],name="KOSPI (좌)",
            line=dict(color=B5,width=2),
            hovertemplate="<b>KOSPI</b> %{y:,.0f}<extra></extra>"),secondary_y=False)
    if not ksq.empty:
        fig.add_trace(go.Scatter(x=ksq["date"],y=ksq["value"],name="KOSDAQ (우)",
            line=dict(color=PUR_DK,width=1.8,dash="dot"),
            hovertemplate="<b>KOSDAQ</b> %{y:,.0f}<extra></extra>"),secondary_y=True)
    lay=BL("KOSPI · KOSDAQ (보조축)",270)
    fig.update_layout(**lay)
    fig.update_yaxes(range=yrange(ksp),secondary_y=False,gridcolor=G,tickfont=dict(size=9,color=MUT))
    fig.update_yaxes(range=yrange(ksq),secondary_y=True,showgrid=False,tickfont=dict(size=9,color=PUR_DK))
    st.plotly_chart(fig, use_container_width=True)
with c2:
    # 외국인 + 기관 수급 (둘 다 PyKRX 데이터 필요 — 미수집 시 안내)
    flows=load("kospi_flows.parquet")
    has_data=False
    if not flows.empty and "indicator" in flows.columns:
        fo=flows[flows["indicator"]=="KOSPI_FOREIGN_NET"].sort_values("date")
        ins=flows[flows["indicator"]=="KOSPI_INSTITUTION_NET"].sort_values("date")
        cutoff=pd.Timestamp.now()-pd.Timedelta(days=365)
        fo=fo[fo["date"]>=cutoff]; ins=ins[ins["date"]>=cutoff]
        if not fo.empty:
            has_data=True
            fig=make_subplots(specs=[[{"secondary_y":True}]])
            fig.add_trace(go.Bar(x=fo["date"],y=fo["value"],name="외국인 (좌)",
                marker_color=[UP if v>=0 else DN for v in fo["value"]],
                hovertemplate="<b>외국인</b> %{y:,.0f}원<extra></extra>"),secondary_y=False)
            if not ins.empty:
                fig.add_trace(go.Scatter(x=ins["date"],y=ins["value"],name="기관 (우)",
                    line=dict(color=PUR_DK,width=1.5),
                    hovertemplate="<b>기관</b> %{y:,.0f}원<extra></extra>"),secondary_y=True)
            lay=BL("외국인 + 기관 순매수 (원)",270)
            fig.update_layout(showlegend=True,**lay)
            fig.update_yaxes(range=yrange(fo),secondary_y=False)
            fig.update_yaxes(range=yrange(ins),secondary_y=True,showgrid=False,tickfont=dict(color=PUR_DK))
            st.plotly_chart(fig, use_container_width=True)
    if not has_data:
        no_data("외국인·기관 수급\nPyKRX 해외IP 차단으로 미수집")

# 신용잔고 · 고객예탁금 (PyKRX/KOFIA 데이터, 미수집 안내)
st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;padding:14px;
  font-size:11px;color:{SUB};margin:1rem 0;font-family:'MaruBuri',serif">
  <b>신용잔고 · 고객예탁금</b> — KRX/KOFIA 데이터 (PyKRX 의존). GitHub Actions 해외IP 차단으로 자동 수집 불가.
  <span style="color:{MUT}">→ 로컬 PC에서 수집 → 수동 커밋 방식만 가능. 별도 스크립트 필요시 요청.</span>
</div>""", unsafe_allow_html=True)

KR_STOCKS={
    "KR_SAMSUNG":("삼성전자",270),"KR_SKHYNIX":("SK하이닉스",130),
    "KR_LGENSOL":("LG에너지",70),"KR_SAMBIO":("삼성바이오",60),
    "KR_HYUNDAI":("현대차",55),"KR_KIA":("기아",45),"KR_CELLTRION":("셀트리온",40),
    "KR_POSCO":("POSCO",38),"KR_KB":("KB금융",35),"KR_NAVER":("NAVER",28),
    "KR_ECOPROBM":("에코프로비엠",25),"KR_SAMSDI":("삼성SDI",25),
    "KR_ECOPRO":("에코프로",20),"KR_KAKAO":("카카오",22),"KR_LGCHEM":("LG화학",24),
    "KR_HYUNDAIMOB":("현대모비스",20),"KR_LGELEC":("LG전자",20),
    "KR_SHINHAN":("신한지주",18),"KR_SAMSUNG_C":("삼성물산",22),"KR_HANA":("하나금융",18),
}
st.plotly_chart(make_treemap(KR_STOCKS,"한국 시총 TOP 20 히트맵 (TOP 100 확장은 다음 단계)"),
                use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 7. 글로벌 증시
# ══════════════════════════════════════════════════════════════
sh("7","글로벌 증시","Global Equity")
c1,c2,c3,c4=st.columns(4)
for col,ind,title in [(c1,"NIKKEI","닛케이 (일본)"),(c2,"SHANGHAI","상해 (중국)"),
                       (c3,"HSI","항셍 (홍콩)"),(c4,"NIFTY","니프티 (인도)")]:
    with col:
        s=ser(market,ind); r=lat(market,ind)
        if not s.empty and r is not None:
            chg=pct_chg_1d(ind); clr=UP if chg>=0 else DN
            fig=go.Figure(go.Scatter(x=s["date"],y=s["value"],line=dict(color=clr,width=2),
                hovertemplate="%{y:,.0f}<extra></extra>"))
            sign="▲" if chg>=0 else "▼"
            lay=BL(f"{title}<br>{r['value']:,.0f}  {sign}{abs(chg):.2f}%",240)
            yr=yrange(s)
            if yr: lay["yaxis"]["range"]=yr
            fig.update_layout(**lay)
            st.plotly_chart(fig, use_container_width=True)
        else: no_data(title)

# ══════════════════════════════════════════════════════════════
# 8. 원자재 & 암호화폐
# ══════════════════════════════════════════════════════════════
sh("8","원자재 & 암호화폐","Commodities & Crypto")
def dual_chart(s1,s2,n1,n2,c1_,c2_,title):
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    if not s1.empty:
        fig.add_trace(go.Scatter(x=s1["date"],y=s1["value"],name=n1,line=dict(color=c1_,width=2),
            hovertemplate=f"<b>{n1}</b> %{{y:,.2f}}<extra></extra>"),secondary_y=False)
    if not s2.empty:
        fig.add_trace(go.Scatter(x=s2["date"],y=s2["value"],name=n2,line=dict(color=c2_,width=1.8),
            hovertemplate=f"<b>{n2}</b> %{{y:,.2f}}<extra></extra>"),secondary_y=True)
    lay=BL(title,270); fig.update_layout(**lay)
    fig.update_yaxes(range=yrange(s1),secondary_y=False,gridcolor=G,tickfont=dict(size=9,color=MUT))
    fig.update_yaxes(range=yrange(s2),secondary_y=True,showgrid=False,tickfont=dict(size=9,color=c2_))
    return fig

c1,c2,c3=st.columns(3)
with c1:
    g_s=ser(market,"GOLD"); sv_s=ser(market,"SILVER")
    if not g_s.empty or not sv_s.empty:
        st.plotly_chart(dual_chart(g_s,sv_s,"금($)","은($)",B5,MUT,"금·은"),use_container_width=True)
    else: no_data("금·은")
with c2:
    oil_s=ser(market,"OIL"); cu_s=ser(market,"COPPER")
    if not oil_s.empty or not cu_s.empty:
        st.plotly_chart(dual_chart(oil_s,cu_s,"WTI($)","구리($)",B6,PUR_DK,"WTI 원유·구리 (경기선행)"),
                        use_container_width=True)
    else: no_data("원유·구리")
with c3:
    btc_s=ser(market,"BTC"); eth_s=ser(market,"ETH")
    if not btc_s.empty or not eth_s.empty:
        st.plotly_chart(dual_chart(btc_s,eth_s,"BTC($)","ETH($)",B5,PUR_DK,"Bitcoin · Ethereum"),
                        use_container_width=True)
    else: no_data("BTC·ETH")

# ══════════════════════════════════════════════════════════════
# 9. 미국 매크로
# ══════════════════════════════════════════════════════════════
sh("9","미국 매크로","US Macro")
c1,c2=st.columns(2)
with c1:
    cpi=ser(fred,"US_CORE_CPI",days=365*6); pce=ser(fred,"US_CORE_PCE",days=365*6)
    fig=go.Figure(); yoy_dfs=[]
    for s,nm,clr,dash in [(cpi,"Core CPI YoY",B5,"solid"),(pce,"Core PCE YoY",PUR_DK,"dot")]:
        if not s.empty:
            ss=s.copy(); ss["yoy"]=ss["value"].pct_change(12)*100
            sy=ss.dropna(subset=["yoy"])[["date","yoy"]].rename(columns={"yoy":"value"})
            if not sy.empty:
                fig.add_trace(go.Scatter(x=sy["date"],y=sy["value"],name=nm,
                    line=dict(color=clr,width=2,dash=dash),
                    hovertemplate=f"<b>{nm}</b> %{{y:.2f}}%<extra></extra>"))
                yoy_dfs.append(sy)
    if fig.data:
        fig.add_hline(y=2.0,line_dash="dot",line_color=MUT,line_width=1.5,
                      annotation_text="Fed 목표 2%",annotation_font_color=MUT)
        lay=BL("Core CPI · Core PCE YoY (Fed 목표 2%)",270)
        yr=yrange(*yoy_dfs)
        if yr: 
            yr=[min(yr[0],1.5),max(yr[1],3.5)]
            lay["yaxis"]["range"]=yr
        fig.update_layout(**lay)
        st.plotly_chart(fig, use_container_width=True)
    else: no_data("CPI·PCE")
with c2:
    nfp=ser(fred,"US_NFP",days=365*5)
    if not nfp.empty:
        nfp=nfp.copy(); nfp["mom"]=nfp["value"].diff(); nm_=nfp.dropna(subset=["mom"])
        nl={k:v for k,v in BL("비농업 고용 MoM (천명)",270).items() if k!="legend"}
        fig=go.Figure(go.Bar(x=nm_["date"],y=nm_["mom"],
            marker_color=[UP if v>=0 else DN for v in nm_["mom"]],
            hovertemplate="<b>NFP MoM</b> %{y:,.0f}천명<extra></extra>"))
        yr=yrange(nm_.rename(columns={"mom":"value"}))
        fig.update_layout(showlegend=False,**nl)
        if yr: fig.update_yaxes(range=yr)
        st.plotly_chart(fig, use_container_width=True)
    else: no_data("NFP")
c3,c4=st.columns(2)
with c3:
    ic=ser(fred,"US_INIT_CLAIMS",days=365*3)
    if not ic.empty:
        st.plotly_chart(lc([(ic,"신규 실업급여",B5)],"Initial Jobless Claims (주간) — 20만↑주의"),
                        use_container_width=True)
    else: no_data("신규 실업급여")
with c4:
    rt=ser(fred,"US_RETAIL",days=365*5)
    if not rt.empty:
        rt=rt.copy(); rt["mom"]=rt["value"].pct_change()*100; rm=rt.dropna(subset=["mom"])
        nl2={k:v for k,v in BL("소매판매 MoM % — GDP의 70%",270).items() if k!="legend"}
        fig=go.Figure(go.Bar(x=rm["date"],y=rm["mom"],
            marker_color=[UP if v>=0 else DN for v in rm["mom"]],
            hovertemplate="<b>소매판매 MoM</b> %{y:.2f}%<extra></extra>"))
        yr=yrange(rm.rename(columns={"mom":"value"}))
        fig.update_layout(showlegend=False,**nl2)
        if yr: fig.update_yaxes(range=yr)
        st.plotly_chart(fig, use_container_width=True)
    else: no_data("소매판매")

# ══════════════════════════════════════════════════════════════
# 10. 한국 매크로 · ECOS
# ══════════════════════════════════════════════════════════════
sh("10","한국 매크로 · ECOS TOP 10","Korean Macro")
ECOS_TOP=["한국은행 기준금리","국고채수익률","원/달러","KOSPI","수출","경상수지","M2","소비자물가","실업률","GDP"]
ECOS_DESC={
    "한국은행 기준금리":"한국 통화정책 기준. 인상=대출·채권금리 상승",
    "국고채수익률":"시중 자금비용 기준",
    "원/달러":"환율. 달러 강세=수출기업 수혜, 수입물가 상승",
    "KOSPI":"한국 대형주 종합지수",
    "수출":"한국 경제 최강 선행지표",
    "경상수지":"무역·서비스 흑자. 흑자=원화 강세",
    "M2":"광의통화. 증가=유동성↑=자산가격 상승",
    "소비자물가":"한국 CPI. 한은 금리 결정 핵심",
    "실업률":"낮을수록 경기 양호",
    "GDP":"분기 경제성장률",
}
if not ecos.empty and "KEYSTAT_NAME" in ecos.columns:
    mask=ecos["KEYSTAT_NAME"].apply(lambda x: any(k in str(x) for k in ECOS_TOP))
    top=ecos[mask].copy()
    if not top.empty:
        cl=[c for c in ["CLASS_NAME","KEYSTAT_NAME","DATA_VALUE","UNIT_NAME","CYCLE"] if c in top.columns]
        rows=""
        for _,r in top[cl].head(10).iterrows():
            kn=str(r.get("KEYSTAT_NAME",""))
            dt=next((v for k,v in ECOS_DESC.items() if k in kn),"")
            dc=f'<div style="font-size:9px;color:{MUT};margin-top:2px;font-family:sans-serif">{dt}</div>' if dt else ""
            rows+=(f'<tr style="border-bottom:1px solid {BORD}">'
                   f'<td style="padding:.45rem 1rem;font-size:9px;color:{MUT};font-family:sans-serif">{r.get("CLASS_NAME","")}</td>'
                   f'<td style="padding:.45rem 1rem"><div style="font-size:11px;color:{TXT}">{kn}</div>{dc}</td>'
                   f'<td style="padding:.45rem 1rem;font-size:13px;font-weight:700;color:{TXT};text-align:right;font-family:JetBrains Mono,monospace">{r.get("DATA_VALUE","")}</td>'
                   f'<td style="padding:.45rem 1rem;font-size:9px;color:{MUT};text-align:right">{r.get("UNIT_NAME","")}</td>'
                   f'<td style="padding:.45rem 1rem;font-size:9px;color:{MUT};text-align:right">{r.get("CYCLE","")}</td>'
                   f'</tr>')
        TH=f"padding:.55rem 1rem;text-align:left;font-size:9px;color:{MUT};letter-spacing:.05em;text-transform:uppercase;font-weight:500;border-bottom:1px solid {BORD};font-family:sans-serif"
        st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;overflow:hidden">
<table style="width:100%;border-collapse:collapse">
  <thead><tr style="background:{C2}">
    <th style="{TH};width:15%">분류</th><th style="{TH};width:38%">지표 · 의미</th>
    <th style="{TH};width:15%;text-align:right">현재값</th>
    <th style="{TH};width:10%;text-align:right">단위</th>
    <th style="{TH};width:7%;text-align:right">주기</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table></div>""", unsafe_allow_html=True)

# ── 푸터 ─────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:3rem;padding-top:1rem;border-top:1px solid {BORD};
  font-size:10px;color:{MUT};text-align:center;font-family:'MaruBuri',serif">
  FRED · yfinance · CNN Fear&Greed · 한국은행 ECOS · 매일 KST 07:00 자동수집
</div>
""", unsafe_allow_html=True)
