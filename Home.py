"""
DY Monitoring — Home  (QLD 스타일 전면 리디자인)
순흑 배경 · 스크롤 티커 · 2열 히어로 · 미니멀 카드
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json, os, re, base64, html as html_lib
from pathlib import Path
from datetime import datetime
import sys

st.set_page_config(
    page_title="DY Monitoring", page_icon="◈",
    layout="wide", initial_sidebar_state="expanded"
)

# ── 스티키 네비 ──────────────────────────────────────────────
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    from utils import render_sticky_nav
    render_sticky_nav()
except Exception:
    pass

# ════════════════════════════════════════════════════════════════
# 경로
# ════════════════════════════════════════════════════════════════
DATA_DIR  = Path(__file__).parent / "data"
ASSET_DIR = Path(__file__).parent / "assets"

def load_custom_font():
    fmt_map = {".woff2":"woff2",".woff":"woff",".ttf":"truetype",".otf":"opentype"}
    for ext, fmt in fmt_map.items():
        fps = sorted(ASSET_DIR.glob(f"*{ext}"))
        if not fps: continue
        fp = fps[0]
        try:
            with open(fp,"rb") as f: b64=base64.b64encode(f.read()).decode()
            return fp.stem, (f"@font-face{{font-family:'{fp.stem}';"
                f"src:url('data:font/{fmt};base64,{b64}') format('{fmt}');}}")
        except: continue
    return None, ""

CUSTOM_FONT, FONT_FACE_CSS = load_custom_font()
FF = f"'{CUSTOM_FONT}',sans-serif" if CUSTOM_FONT else "'Pretendard Variable','Inter',sans-serif"

# ════════════════════════════════════════════════════════════════
# QLD 색상 팔레트
# ════════════════════════════════════════════════════════════════
BG    = "#07090F"   # 순흑 배경 (QLD 그대로)
CARD  = "#0D1117"   # 카드 배경
C2    = "#131924"   # 2단계 카드
C3    = "#1A2233"   # 호버
BORD  = "#1E2433"   # 기본 테두리
BORD2 = "#2D3748"   # 강조 테두리
TXT   = "#EAEEF2"   # 주 텍스트
SUB   = "#8B949E"   # 보조 텍스트
MUT   = "#484F58"   # 흐린 텍스트
UP    = "#E24B4A"   # 상승 = 빨강 (한국 관례)
DN    = "#388BFD"   # 하락 = 파랑 (한국 관례)
B5    = "#388BFD"   # 블루 액센트
B3    = "#79C0FF"   # 연블루
GOLD  = "#D4A017"   # 골드
PUR_DK = "#79C0FF"

# 계좌별
ACCT_COLORS = {"일반":"#388BFD","DC":"#79C0FF","연금저축":"#1F6FEB"}
ACCT_LABELS = {"일반":"💳 일반","DC":"🏢 DC","연금저축":"🏦 연금저축"}

now = datetime.now()
BRIEF_KEY = "home_brief"

# ════════════════════════════════════════════════════════════════
# 데이터 로드
# ════════════════════════════════════════════════════════════════
@st.cache_data(ttl=600)
def load_pq(fn):
    p = DATA_DIR / fn
    if not p.exists(): return pd.DataFrame()
    try:
        df = pd.read_parquet(p)
        if "date" in df.columns: df["date"] = pd.to_datetime(df["date"])
        return df
    except: return pd.DataFrame()

def load_json(fn, default=None):
    p = DATA_DIR / fn
    if not p.exists(): return default if default is not None else {}
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except: return default if default is not None else {}

def get_secret(k, default=""):
    try:    return st.secrets[k]
    except: return os.environ.get(k, default)

def safe(v): return html_lib.escape(str(v)) if v else ""

market    = load_pq("market_prices.parquet")
fred      = load_pq("fred_indicators.parquet")
portfolio = load_json("portfolio.json", [])
prices_df = load_pq("portfolio_prices.parquet")

# ════════════════════════════════════════════════════════════════
# CSS — QLD 스타일
# ════════════════════════════════════════════════════════════════
st.markdown(
    FONT_FACE_CSS +
    """<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.8/dist/web/variable/pretendardvariable.min.css">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">""" +
    f"""<style>
html,body,[class*="css"]{{
  background-color:{BG}!important;color:{TXT}!important;
  font-family:{FF}!important;letter-spacing:-.02em!important;
  font-size:14px!important;line-height:1.5!important}}
.block-container{{
  padding:.8rem 1.8rem 3rem!important;max-width:100%!important;
  background:transparent!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
[data-testid="stSidebar"]{{
  background-color:{CARD}!important;
  border-right:1px solid {BORD}!important}}
#MainMenu,footer,header{{visibility:hidden}}
p,span,div,label{{color:{TXT}!important}}
/* 버튼 */
.stButton>button{{
  background:transparent!important;color:{SUB}!important;
  border:1px solid {BORD}!important;border-radius:6px!important;
  font-family:{FF}!important;font-size:12px!important;font-weight:500!important;
  padding:5px 14px!important;box-shadow:none!important;transition:all .12s!important}}
.stButton>button:hover{{
  border-color:{B5}!important;color:{B5}!important;background:{C2}!important}}
/* 라디오 버튼 → 기간 선택 pill */
[data-testid="stRadio"]>div{{gap:2px!important;flex-direction:row!important}}
[data-testid="stRadio"]>div>label{{
  background:transparent!important;color:{SUB}!important;
  border:1px solid {BORD}!important;border-radius:5px!important;
  padding:4px 12px!important;font-size:11px!important;
  font-family:{FF}!important;font-weight:500!important;cursor:pointer!important;
  transition:all .12s!important}}
[data-testid="stRadio"]>div>label[data-selected="true"]{{
  background:{C2}!important;color:{TXT}!important;border-color:{BORD2}!important}}
/* Plotly 차트 */
.js-plotly-plot{{border-radius:0!important}}
/* 스크롤바 */
::-webkit-scrollbar{{width:3px;height:3px}}
::-webkit-scrollbar-track{{background:transparent}}
::-webkit-scrollbar-thumb{{background:{BORD2};border-radius:2px}}
/* ══ 티커 바 ══ */
.ticker-wrap{{
  overflow:hidden;background:{CARD};
  border-bottom:1px solid {BORD};
  padding:8px 0;margin-bottom:1.2rem}}
.ticker-track{{
  display:flex;gap:0;width:max-content;
  animation:ticker-run 50s linear infinite}}
.ticker-track:hover{{animation-play-state:paused}}
@keyframes ticker-run{{
  0%{{transform:translateX(0)}}
  100%{{transform:translateX(-50%)}}}}
.ticker-item{{
  display:flex;align-items:center;gap:8px;
  padding:0 24px;border-right:1px solid {BORD};white-space:nowrap}}
.ticker-name{{font-size:11px;font-weight:600;color:{TXT}}}
.ticker-price{{font-size:11px;font-family:'JetBrains Mono',monospace;color:{TXT}}}
.ticker-chg{{font-size:10px;font-family:'JetBrains Mono',monospace;font-weight:600}}
/* ══ 섹션 구분선 ══ */
.qld-divider{{height:1px;background:{BORD};margin:1.4rem 0}}
/* ══ 히어로 숫자 ══ */
.hero-amount{{
  font-size:42px;font-weight:700;line-height:1;
  letter-spacing:-.03em;font-family:'JetBrains Mono',monospace;color:{TXT}}}
.hero-label{{font-size:11px;color:{SUB};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}}
/* ══ KPI 카드 ══ */
.kpi-card{{
  background:{CARD};border:1px solid {BORD};
  border-radius:8px;padding:14px 16px}}
.kpi-label{{font-size:10px;color:{SUB};text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}}
.kpi-val{{font-size:20px;font-weight:700;font-family:'JetBrains Mono',monospace;color:{TXT};line-height:1;margin-bottom:5px}}
.kpi-chg{{font-size:11px;font-weight:600;font-family:'JetBrains Mono',monospace}}
/* ══ 홀딩 행 ══ */
.holding-row{{
  display:flex;align-items:center;justify-content:space-between;
  padding:7px 0;border-bottom:1px solid {BORD}}}
</style>""",
    unsafe_allow_html=True
)

# ════════════════════════════════════════════════════════════════
# 헬퍼
# ════════════════════════════════════════════════════════════════
def lat(df, ind):
    if df.empty or "indicator" not in df.columns: return None
    s = df[df["indicator"]==ind].sort_values("date")
    return s.iloc[-1] if not s.empty else None

def ser_h(df, ind, days=90):
    if df.empty or "indicator" not in df.columns: return pd.DataFrame()
    s = df[df["indicator"]==ind].copy()
    if days: s = s[s["date"] >= pd.Timestamp.now()-pd.Timedelta(days=days)]
    return s.sort_values("date")

def dlt_info(df, ind):
    s = ser_h(df, ind, 10)
    if s.empty or len(s)<2: return 0.0, 0.0
    prev, cur = float(s.iloc[-2]["value"]), float(s.iloc[-1]["value"])
    d = cur - prev
    return d, (d/prev*100) if prev else 0.0

def sparkline_svg(df, ind, color=B5, days=60, w=80, h=28):
    s = ser_h(df, ind, days)
    vals = s["value"].dropna().tolist() if not s.empty else []
    if len(vals) < 3: return ""
    mn, mx = min(vals), max(vals); mg=2
    if mn == mx:
        pts = [(round(i*w/(len(vals)-1),1), h/2) for i in range(len(vals))]
    else:
        pts = [(round(i*w/(len(vals)-1),1),
                round(h-mg-(v-mn)/(mx-mn)*(h-mg*2),1)) for i,v in enumerate(vals)]
    ld = "M " + " L ".join(f"{x},{y}" for x,y in pts)
    fd = ld + f" L {pts[-1][0]},{h} L {pts[0][0]},{h} Z"
    gid = "spk" + re.sub(r'\W','',ind)[:8]
    lx, ly = pts[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="display:block">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity=".25"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity=".02"/>'
            f'</linearGradient></defs>'
            f'<path d="{fd}" fill="url(#{gid})"/>'
            f'<path d="{ld}" fill="none" stroke="{color}" stroke-width="1.4"'
            f' stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{lx}" cy="{ly}" r="2" fill="{color}"/></svg>')

# ════════════════════════════════════════════════════════════════
# 포트폴리오 포지션 계산
# ════════════════════════════════════════════════════════════════
fx_row = lat(market, "USDKRW")
fx = float(fx_row["value"]) if fx_row is not None else 1380.0

@st.cache_data(ttl=300)
def get_positions():
    if not portfolio or prices_df.empty: return []
    out = []
    for it in portfolio:
        if not isinstance(it, dict): continue
        lots = [l for l in it.get("lots",[]) if isinstance(l,dict)]
        ticker = it.get("ticker","")
        if not lots or not ticker: continue
        qty   = sum(l.get("qty",0) for l in lots)
        cost  = sum(l.get("qty",0)*l.get("price",0) for l in lots)
        if qty <= 0: continue
        avg = cost/qty
        sub = prices_df[prices_df["ticker"]==ticker].sort_values("date")
        if sub.empty: continue
        cur  = float(sub.iloc[-1]["close"])
        prev = float(sub.iloc[-2]["close"]) if len(sub)>=2 else cur
        fxv  = fx if it.get("currency")=="USD" else 1
        val  = cur*qty*fxv
        out.append({
            "name":     it.get("name",""),
            "ticker":   ticker,
            "account":  it.get("account","일반"),
            "currency": it.get("currency","KRW"),
            "sector":   it.get("sector",""),
            "qty":      qty,
            "avg":      avg,
            "cur":      cur,
            "value_krw": val,
            "pnl_krw":  (cur-avg)*qty*fxv,
            "pnl_pct":  (cur/avg-1)*100 if avg>0 else 0,
            "daily_pct":(cur/prev-1)*100 if prev>0 else 0,
        })
    return sorted(out, key=lambda x: -x["value_krw"])

positions = get_positions()
tv  = sum(p["value_krw"] for p in positions)
tp  = sum(p["pnl_krw"]   for p in positions)
td  = sum(p["value_krw"]*p["daily_pct"]/100 for p in positions)
dpct = td/(tv-td)*100 if (tv-td)>0 else 0

# ════════════════════════════════════════════════════════════════
# 1. 티커 바 (자동 스크롤)
# ════════════════════════════════════════════════════════════════
if positions:
    items_html = ""
    for p in positions:
        sym   = "▲" if p["daily_pct"]>=0 else "▼"
        clr   = UP if p["daily_pct"]>=0 else DN
        price_str = (f"${p['cur']:,.2f}" if p["currency"]=="USD"
                     else f"₩{p['cur']:,.0f}")
        items_html += (
            f'<div class="ticker-item">'
            f'<span class="ticker-name">{safe(p["name"])}</span>'
            f'<span class="ticker-price">{price_str}</span>'
            f'<span class="ticker-chg" style="color:{clr}">'
            f'{sym}{abs(p["daily_pct"]):.2f}%</span>'
            f'</div>'
        )
    # 무한 루프를 위해 2배 복제
    st.markdown(
        f'<div class="ticker-wrap">'
        f'<div class="ticker-track">{items_html}{items_html}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

# ════════════════════════════════════════════════════════════════
# 2. 히어로 — 좌(자산 요약) : 우(잔고 추이 차트)
# ════════════════════════════════════════════════════════════════
left, right = st.columns([4, 6], gap="large")

# ── 왼쪽: 총 평가금액 + 구성 ─────────────────────────────────
with left:
    # 총 평가금액
    d_sym   = "↑" if td>=0 else "↓"
    d_clr   = UP if td>=0 else DN
    st.markdown(f"""
<div class="hero-label">총 평가금액</div>
<div class="hero-amount">{tv:,.0f}<span style="font-size:18px;color:{SUB};margin-left:6px">원</span></div>
<div style="display:flex;align-items:center;gap:8px;margin-top:10px;margin-bottom:20px">
  <span style="font-size:14px;color:{d_clr};font-weight:600;font-family:'JetBrains Mono',monospace">
    {d_sym} 전일 {td:+,.0f}원 ({dpct:+.2f}%)
  </span>
</div>""", unsafe_allow_html=True)

    # 레인보우 비중 바
    if positions and tv > 0:
        COLORS = ["#388BFD","#79C0FF","#1F6FEB","#58A6FF",
                  "#2F81F7","#CAE8FF","#0D6EFD","#4A82E4","#9ECEFF","#1158C7"]
        segs = ""
        for i, p in enumerate(positions[:10]):
            w = p["value_krw"]/tv*100
            if w < 0.3: continue
            segs += (f'<div style="width:{w:.2f}%;height:100%;'
                     f'background:{COLORS[i%len(COLORS)]}"></div>')
        st.markdown(f"""
<div style="display:flex;height:5px;border-radius:3px;overflow:hidden;background:{C2};gap:1px;margin-bottom:16px">
  {segs}
</div>""", unsafe_allow_html=True)

    # 종목 목록
    st.markdown(f"""
<div style="display:flex;padding:4px 0 6px;border-bottom:1px solid {BORD};gap:8px">
  <span style="font-size:10px;color:{MUT};flex:1">종목</span>
  <span style="font-size:10px;color:{MUT};min-width:56px;text-align:right">비중</span>
  <span style="font-size:10px;color:{MUT};min-width:64px;text-align:right">평가금액</span>
  <span style="font-size:10px;color:{MUT};min-width:52px;text-align:right">수익률</span>
</div>""", unsafe_allow_html=True)

    for i, p in enumerate(positions[:8]):
        wt   = p["value_krw"]/tv*100 if tv>0 else 0
        pclr = UP if p["pnl_pct"]>=0 else DN
        sp   = "+" if p["pnl_pct"]>=0 else ""
        val_str = (f"{p['value_krw']/1e8:.2f}억"
                   if p["value_krw"]>=1e8 else f"{p['value_krw']/1e4:.0f}만")
        dot_clr = COLORS[i%len(COLORS)]
        st.markdown(f"""
<div style="display:flex;align-items:center;padding:6px 0;border-bottom:1px solid {BORD};gap:8px">
  <div style="display:flex;align-items:center;gap:7px;flex:1;min-width:0">
    <span style="width:7px;height:7px;border-radius:50%;background:{dot_clr};flex-shrink:0"></span>
    <span style="font-size:12px;font-weight:500;color:{TXT};
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{safe(p['name'])}</span>
  </div>
  <span style="font-size:11px;color:{SUB};min-width:56px;text-align:right;
    font-family:'JetBrains Mono',monospace">{wt:.1f}%</span>
  <span style="font-size:11px;font-weight:600;color:{TXT};min-width:64px;text-align:right;
    font-family:'JetBrains Mono',monospace">{val_str}</span>
  <span style="font-size:11px;font-weight:700;color:{pclr};min-width:52px;text-align:right;
    font-family:'JetBrains Mono',monospace">{sp}{p['pnl_pct']:.2f}%</span>
</div>""", unsafe_allow_html=True)

    # 요약 통계
    tpct = tp/(tv-tp)*100 if (tv-tp)>0 else 0
    pclr_total = UP if tp>=0 else DN
    st.markdown(f"""
<div style="display:flex;gap:16px;margin-top:14px;padding-top:14px;border-top:1px solid {BORD}">
  <div>
    <div style="font-size:10px;color:{MUT}">누적 손익</div>
    <div style="font-size:15px;font-weight:700;color:{pclr_total};
      font-family:'JetBrains Mono',monospace">{tp:+,.0f}원</div>
    <div style="font-size:10px;color:{pclr_total};font-family:'JetBrains Mono',monospace">
      {tpct:+.2f}%</div>
  </div>
  <div>
    <div style="font-size:10px;color:{MUT}">USD 환산</div>
    <div style="font-size:15px;font-weight:700;color:{TXT};
      font-family:'JetBrains Mono',monospace">${tv/fx:,.0f}</div>
    <div style="font-size:10px;color:{MUT};font-family:'JetBrains Mono',monospace">
      ₩{fx:,.0f}</div>
  </div>
  <div>
    <div style="font-size:10px;color:{MUT}">보유 종목</div>
    <div style="font-size:15px;font-weight:700;color:{TXT};
      font-family:'JetBrains Mono',monospace">{len(positions)}개</div>
    <div style="font-size:10px;color:{MUT}">종목 · {len({p['account'] for p in positions})}개 계좌</div>
  </div>
</div>""", unsafe_allow_html=True)

# ── 오른쪽: 잔고 추이 차트 ───────────────────────────────────
with right:
    # 기간 선택
    rng = st.radio("기간", ["1W","1M","3M","6M","1Y","ALL"],
                   horizontal=True, label_visibility="collapsed", key="hero_rng")

    # 계좌별 히스토리 계산
    @st.cache_data(ttl=600)
    def compute_account_history():
        if prices_df.empty or not portfolio or not isinstance(portfolio, list):
            return pd.DataFrame()
        all_dates = sorted(prices_df["date"].dropna().unique())
        fx_df = pd.DataFrame()
        if not market.empty and "indicator" in market.columns:
            fx_df = (market[market["indicator"]=="USDKRW"][["date","value"]]
                     .rename(columns={"value":"fx"}).sort_values("date"))
        rows = []
        for d in all_dates:
            fx_now = 1380.0
            if not fx_df.empty:
                fs = fx_df[fx_df["date"]<=d]
                if not fs.empty: fx_now = float(fs.iloc[-1]["fx"])
            acct_vals = {}; total = 0
            for it in portfolio:
                if not isinstance(it, dict): continue
                acct = it.get("account","일반"); ticker = it.get("ticker")
                if not ticker: continue
                lots = [l for l in it.get("lots",[]) if isinstance(l,dict)
                        and pd.Timestamp(l.get("date","2000-01-01"))<=d]
                qty = sum(l.get("qty",0) for l in lots)
                if qty<=0: continue
                ps = prices_df[(prices_df["ticker"]==ticker)&(prices_df["date"]<=d)].sort_values("date")
                if ps.empty: continue
                fxv = fx_now if it.get("currency","KRW")=="USD" else 1
                val = qty*float(ps.iloc[-1]["close"])*fxv
                acct_vals[acct] = acct_vals.get(acct,0)+val; total+=val
            if total>0:
                row={"date":d,"Total":total}; row.update(acct_vals); rows.append(row)
        return pd.DataFrame(rows)

    hist = compute_account_history()

    # 기간 필터
    cutoffs = {"1W":7,"1M":30,"3M":90,"6M":180,"1Y":365}
    if rng in cutoffs and not hist.empty:
        hist = hist[hist["date"] >= pd.Timestamp.now()-pd.Timedelta(days=cutoffs[rng])]

    if not hist.empty:
        acct_cols = [c for c in hist.columns if c not in ["date","Total"]]
        fig = go.Figure()

        # 계좌별 누적 영역
        for acct in acct_cols:
            clr = ACCT_COLORS.get(acct, B5)
            fig.add_trace(go.Scatter(
                x=hist["date"], y=hist[acct]/1e6,
                name=ACCT_LABELS.get(acct, acct),
                mode="lines", stackgroup="one",
                line=dict(width=1.2, color=clr),
                hovertemplate=(f"<b>{ACCT_LABELS.get(acct,acct)}</b>"
                               f" %{{y:,.1f}}M<extra></extra>")))

        # 최고점 레퍼런스
        if "Total" in hist.columns:
            peak = hist["Total"].max()
            if peak > 0:
                fig.add_hline(y=peak/1e6, line_dash="dot",
                    line_color=MUT, line_width=0.8)

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=340,
            margin=dict(l=0, r=0, t=4, b=0),
            legend=dict(orientation="h", y=1.06, x=0,
                font=dict(size=10,color=SUB,family=FF),
                bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",
            hoverlabel=dict(bgcolor=C2, bordercolor=BORD,
                font=dict(family="JetBrains Mono",size=10,color=TXT)),
            xaxis=dict(showgrid=False, zeroline=False, showline=False,
                tickfont=dict(size=9,color=MUT,family="JetBrains Mono"),
                tickformat="%m/%d"),
            yaxis=dict(showgrid=True, gridcolor=BORD, gridwidth=0.5,
                zeroline=False, showline=False,
                tickfont=dict(size=9,color=MUT,family="JetBrains Mono"),
                ticksuffix="M", side="right"))
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar":False})

        # 차트 하단 스탯
        if "Total" in hist.columns and len(hist)>=2:
            v_last  = float(hist["Total"].iloc[-1])
            v_first = float(hist["Total"].iloc[0])
            v_peak  = float(hist["Total"].max())
            v_min   = float(hist["Total"].min())
            mdd     = (v_min/v_peak-1)*100
            rng_ret = (v_last/v_first-1)*100
            st_cols = st.columns(4)
            for col,(lbl,val,sub_) in zip(st_cols,[
                ("기간 수익", f"{rng_ret:+.2f}%", rng),
                ("현재 평가", f"{v_last/1e8:.2f}억", "원"),
                ("기간 최고", f"{v_peak/1e8:.2f}억", "원"),
                ("MDD",       f"{mdd:.2f}%",  "최대낙폭"),
            ]):
                clr2 = (UP if rng_ret>=0 else DN) if lbl=="기간 수익" else TXT
                with col:
                    st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:7px;padding:10px 12px">
  <div style="font-size:9px;color:{SUB};text-transform:uppercase;
    letter-spacing:.06em;margin-bottom:4px">{lbl}</div>
  <div style="font-size:15px;font-weight:700;color:{clr2};
    font-family:'JetBrains Mono',monospace">{val}</div>
  <div style="font-size:9px;color:{MUT};margin-top:2px">{sub_}</div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:8px;
  height:300px;display:flex;align-items:center;justify-content:center;
  font-size:13px;color:{MUT}">Actions 실행 후 차트가 표시됩니다</div>""",
            unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 3. 구분선
# ════════════════════════════════════════════════════════════════
st.markdown(f'<div class="qld-divider"></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 4. 글로벌 KPI 7개
# ════════════════════════════════════════════════════════════════
st.markdown(f'<div style="font-size:11px;color:{MUT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">글로벌 시장</div>', unsafe_allow_html=True)

KPI_ITEMS = [
    ("S&P500","SPX",market,",.0f"),
    ("NASDAQ","NASDAQ",market,",.0f"),
    ("KOSPI","KOSPI",market,",.0f"),
    ("KOSDAQ","KOSDAQ",market,",.0f"),
    ("VIX","VIX",market,".1f"),
    ("USD/KRW","USDKRW",market,",.0f"),
    ("US 10Y","US_10Y",fred,".2f"),
]
kpi_cols = st.columns(7)
for col,(lbl,ind,df_,fmt) in zip(kpi_cols, KPI_ITEMS):
    r = lat(df_, ind); d, p = dlt_info(df_, ind)
    spk = sparkline_svg(df_, ind,
                        color=(UP if p>=0 else DN), days=60)
    sym = "▲" if p>=0 else "▼"
    clr = UP if p>=0 else DN
    with col:
        if r is not None:
            st.markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">{lbl}</div>
  <div class="kpi-val">{format(r["value"],fmt)}</div>
  <div class="kpi-chg" style="color:{clr}">{sym}{abs(p):.2f}%</div>
  <div style="margin-top:6px">{spk}</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
<div class="kpi-card" style="opacity:.4">
  <div class="kpi-label">{lbl}</div>
  <div class="kpi-val" style="color:{MUT}">—</div>
</div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 5. 구분선
# ════════════════════════════════════════════════════════════════
st.markdown(f'<div class="qld-divider"></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 6. 오늘의 브리핑
# ════════════════════════════════════════════════════════════════
BRIEF_FILE = DATA_DIR / "daily_briefing.json"

def load_brief():
    if BRIEF_FILE.exists():
        try:
            with open(BRIEF_FILE, encoding="utf-8") as f: return json.load(f)
        except: return None
    return None

def save_brief(data):
    DATA_DIR.mkdir(exist_ok=True)
    with open(BRIEF_FILE,"w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def build_prompt():
    prices    = load_pq("portfolio_prices.parquet")
    pf_data   = load_json("portfolio.json", [])
    news_data = load_json("portfolio_news.json", {})
    nl = "\n"
    mkt_lines = []
    for ind, lbl in [("SPX","S&P500"),("NASDAQ","NASDAQ"),("KOSPI","KOSPI"),
                     ("KOSDAQ","KOSDAQ"),("VIX","VIX"),("USDKRW","USD/KRW"),
                     ("US_10Y","미국10Y금리")]:
        df_src = fred if ind == "US_10Y" else market
        r = lat(df_src, ind)
        if r is not None:
            _, p = dlt_info(df_src, ind)
            sym = "▲" if p>=0 else "▼"
            mkt_lines.append(f"  {lbl}: {r['value']:,.2f} ({sym}{abs(p):.2f}%)")
    hold_lines = []
    if isinstance(pf_data, list):
        for it in pf_data:
            if not isinstance(it, dict): continue
            lots = [l for l in it.get("lots",[]) if isinstance(l,dict)]
            ticker = it.get("ticker","")
            if not lots or not ticker: continue
            qty = sum(l.get("qty",0) for l in lots)
            cost= sum(l.get("qty",0)*l.get("price",0) for l in lots)
            if qty<=0: continue
            avg = cost/qty
            sub = prices[prices["ticker"]==ticker].sort_values("date") if not prices.empty else pd.DataFrame()
            if sub.empty: continue
            cur = float(sub.iloc[-1]["close"])
            prev= float(sub.iloc[-2]["close"]) if len(sub)>=2 else cur
            fxv = fx if it.get("currency")=="USD" else 1
            val = cur*qty*fxv; pnl=(cur-avg)*qty*fxv
            dpct=(cur/prev-1)*100 if prev else 0
            sym = "▲" if dpct>=0 else "▼"
            hold_lines.append(
                f"  {it.get('name','')}({it.get('sector','')}) "
                f"현재:{cur:,.2f} 일간:{sym}{abs(dpct):.2f}% "
                f"수익률:{(cur/avg-1)*100:+.2f}% 평가:{val:,.0f}원")
    news_lines = []
    for cat in ("stocks","sectors"):
        for key, arts in news_data.get(cat,{}).items():
            if isinstance(arts, list):
                for n in arts:
                    if isinstance(n,dict):
                        sc = n.get("score")
                        if sc is not None and (sc>=8 or sc<=2):
                            tag="호재" if sc>=6 else "악재"
                            news_lines.append(
                                f"  [{tag}{sc}] {key}: "
                                f"{n.get('ai_summary') or n.get('title','')[:55]}")
    return (
        f"한국 retail 투자자를 위한 실시간 투자 브리핑을 작성하세요.\n\n"
        f"[{now.strftime('%Y-%m-%d %H:%M')} 기준]\n\n"
        f"▣ 글로벌 시장 지표\n{nl.join(mkt_lines) or '  (데이터 없음)'}\n\n"
        f"▣ 보유 종목 현황\n{nl.join(hold_lines) or '  (데이터 없음)'}\n"
        f"  총평가:{tv:,.0f}원  누적손익:{tp:+,.0f}원\n\n"
        f"▣ AI 점수 주요 뉴스\n{nl.join(news_lines[:8]) or '  (뉴스 없음)'}\n\n"
        f"다음 JSON만 반환 (다른 텍스트 금지):\n"
        f'{{"headline":"오늘 핵심 1줄(25자이내)",'
        f'"market":"시장 분석 2-3문장","holdings":"보유 종목 분석 2-3문장",'
        f'"sectors":"보유 섹터 흐름 1-2문장","news":"주목 뉴스 영향 1-2문장",'
        f'"action":"투자 액션 코멘트 1문장",'
        f'"mood":"positive 또는 neutral 또는 cautious"}}'
    )

def gen_brief_realtime(api_key):
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key.strip())
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=900,
            messages=[{"role":"user","content":build_prompt()}])
        text = msg.content[0].text.strip()
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if not m: return None
        result = json.loads(m.group())
        result["generated_at"] = now.strftime("%Y-%m-%d %H:%M")
        result["realtime"] = True
        return result
    except Exception as e:
        st.error(f"브리핑 생성 오류: {e}"); return None

brief = load_brief()
if BRIEF_KEY in st.session_state: brief = st.session_state[BRIEF_KEY]

# 브리핑 헤더
bc1, bc2 = st.columns([5,1])
with bc1:
    st.markdown(f'<div style="font-size:11px;color:{MUT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">오늘의 브리핑</div>',
                unsafe_allow_html=True)
with bc2:
    if st.button("🔄 생성", key="brief_refresh", use_container_width=True):
        api_key = get_secret("ANTHROPIC_API_KEY")
        if not api_key or api_key.startswith("*"):
            st.warning("Streamlit Secrets에 ANTHROPIC_API_KEY를 등록하세요.")
        else:
            with st.spinner("Claude가 브리핑 생성 중…"):
                nb = gen_brief_realtime(api_key)
                if nb:
                    st.session_state[BRIEF_KEY] = nb
                    save_brief(nb); brief = nb; st.rerun()

if brief:
    mood_map = {
        "positive": UP,
        "neutral":  SUB,
        "cautious": B5,
    }
    mc      = mood_map.get(brief.get("mood","neutral"), SUB)
    gen_t   = safe(brief.get("generated_at",""))
    rt_tag  = (f'<span style="background:{B5}22;color:{B5};padding:2px 8px;'
               f'border-radius:4px;font-size:9px;font-weight:600;'
               f'font-family:JetBrains Mono">실시간</span>'
               ) if brief.get("realtime") else ""

    st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:8px;padding:18px 20px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
    <div>
      <div style="font-size:18px;font-weight:700;color:{TXT};line-height:1.3;margin-bottom:6px">
        {safe(brief.get("headline",""))}
      </div>
      <div style="display:flex;align-items:center;gap:6px">
        <span style="width:6px;height:6px;border-radius:50%;background:{mc};display:inline-block"></span>
        <span style="font-size:11px;color:{mc};font-weight:600;text-transform:uppercase">
          {safe(brief.get("mood",""))}
        </span>
        {rt_tag}
      </div>
    </div>
    <span style="font-size:9px;color:{MUT};font-family:'JetBrains Mono',monospace;
      flex-shrink:0;margin-left:12px">{gen_t}</span>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;margin-bottom:12px">
    <div style="background:{C2};border-radius:6px;padding:10px 12px">
      <div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px">📊 시장</div>
      <div style="font-size:11px;color:{TXT};line-height:1.6">{safe(brief.get("market",""))}</div>
    </div>
    <div style="background:{C2};border-radius:6px;padding:10px 12px">
      <div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px">💼 종목</div>
      <div style="font-size:11px;color:{TXT};line-height:1.6">{safe(brief.get("holdings",""))}</div>
    </div>
    <div style="background:{C2};border-radius:6px;padding:10px 12px">
      <div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px">🏭 섹터</div>
      <div style="font-size:11px;color:{TXT};line-height:1.6">{safe(brief.get("sectors",""))}</div>
    </div>
    <div style="background:{C2};border-radius:6px;padding:10px 12px">
      <div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px">📰 뉴스</div>
      <div style="font-size:11px;color:{TXT};line-height:1.6">{safe(brief.get("news",""))}</div>
    </div>
  </div>
  <div style="padding:10px 12px;background:{C2};border-radius:6px;
    font-size:12px;color:{TXT};font-weight:500">
    💬 {safe(brief.get("action",""))}
  </div>
</div>""", unsafe_allow_html=True)
else:
    st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:8px;
  padding:28px;text-align:center">
  <div style="font-size:13px;color:{MUT}">
    브리핑 없음 — 🔄 버튼으로 생성하거나 GitHub Actions를 실행하세요
  </div>
</div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 7. 주간 리포트 (접이식)
# ════════════════════════════════════════════════════════════════
weekly = load_json("weekly_report.json", None)
if weekly and isinstance(weekly, dict) and weekly.get("headline"):
    grade    = weekly.get("grade","B")
    gc_map   = {"S":UP,"A":B5,"B":B3,"C":SUB,"D":DN}
    gc       = gc_map.get(grade, SUB)
    st.markdown(f"""
<div style="margin-top:1rem"></div>
<details style="background:{CARD};border:1px solid {BORD};border-radius:8px;padding:14px 18px">
  <summary style="font-size:12px;font-weight:600;color:{TXT};list-style:none;
    display:flex;align-items:center;gap:8px;cursor:pointer">
    📊 주간 리포트
    <span style="background:{gc}22;color:{gc};padding:2px 9px;border-radius:4px;
      font-size:10px;font-weight:700;font-family:'JetBrains Mono',monospace">{safe(grade)}</span>
    <span style="font-size:12px;color:{TXT}">{safe(weekly.get("headline",""))}</span>
    <span style="font-size:9px;color:{MUT};margin-left:auto;font-family:'JetBrains Mono',monospace">
      {safe(weekly.get("week_range",""))} · {safe(weekly.get("generated_at",""))}
    </span>
  </summary>
  <div style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:8px">
    <div style="background:{C2};border-radius:6px;padding:10px 13px">
      <div style="font-size:9px;color:{MUT};margin-bottom:4px">성과</div>
      <div style="font-size:11px;color:{TXT};line-height:1.6">{safe(weekly.get("performance",""))}</div>
    </div>
    <div style="background:{C2};border-radius:6px;padding:10px 13px">
      <div style="font-size:9px;color:{MUT};margin-bottom:4px">시장 환경</div>
      <div style="font-size:11px;color:{TXT};line-height:1.6">{safe(weekly.get("market_context",""))}</div>
    </div>
    <div style="background:{C2};border-radius:6px;padding:10px 13px">
      <div style="font-size:9px;color:{MUT};margin-bottom:4px">교훈</div>
      <div style="font-size:11px;color:{TXT};line-height:1.6">{safe(weekly.get("lessons",""))}</div>
    </div>
    <div style="background:{C2};border-radius:6px;padding:10px 13px">
      <div style="font-size:9px;color:{MUT};margin-bottom:4px">다음 주 주목</div>
      <div style="font-size:11px;color:{TXT};line-height:1.6">{safe(weekly.get("next_week",""))}</div>
    </div>
  </div>
</details>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 8. 다가오는 일정
# ════════════════════════════════════════════════════════════════
_events_raw = load_json("events.json", {})
_events     = _events_raw.get("events",[]) if isinstance(_events_raw, dict) else []
_EV_COLORS  = {"fomc":UP,"cpi":GOLD,"bok":B5,"earnings":B3,"custom":SUB}
_EV_ICONS   = {"fomc":"🏛","cpi":"📊","bok":"🇰🇷","earnings":"💵","custom":"📌"}
_today      = now.date()

_upcoming = []
for _e in _events:
    try: _d = datetime.strptime(_e["date"],"%Y-%m-%d").date()
    except: continue
    if _d >= _today: _upcoming.append((_d,_e))
_upcoming.sort(key=lambda x: x[0])
_upcoming = _upcoming[:5]

if _upcoming:
    st.markdown(
        f'<div class="qld-divider"></div>'
        f'<div style="font-size:11px;color:{MUT};text-transform:uppercase;'
        f'letter-spacing:.08em;margin-bottom:10px">다가오는 일정</div>',
        unsafe_allow_html=True)
    ev_cols = st.columns(len(_upcoming))
    for ec,(_d,_e) in zip(ev_cols,_upcoming):
        _dday = (_d - _today).days
        _dl   = "D-DAY" if _dday==0 else f"D-{_dday}"
        _clr  = _EV_COLORS.get(_e.get("type","custom"), SUB)
        _icon = _EV_ICONS.get(_e.get("type","custom"), "📌")
        with ec:
            st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:8px;padding:12px 14px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
    <span style="font-size:14px">{_icon}</span>
    <span style="background:{_clr}22;color:{_clr};padding:2px 8px;
      border-radius:4px;font-size:10px;font-weight:700;
      font-family:'JetBrains Mono',monospace">{_dl}</span>
  </div>
  <div style="font-size:12px;font-weight:600;color:{TXT};margin-bottom:3px">
    {safe(_e.get("title",""))}</div>
  <div style="font-size:9px;color:{MUT};font-family:'JetBrains Mono',monospace">
    {_d.strftime("%m/%d")} · {safe(_e.get("time",""))}</div>
</div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 9. 푸터
# ════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="margin-top:2.4rem;padding:10px 0;border-top:1px solid {BORD};
  font-size:10px;color:{MUT};font-family:'JetBrains Mono',monospace;
  display:flex;justify-content:space-between;align-items:center">
  <span>FRED · yfinance · CNN F&amp;G · ECOS · 네이버 뉴스 · DART · 매일 KST 07:00 자동수집</span>
  <span>{now.strftime("%Y-%m-%d %H:%M")} KST</span>
</div>
""", unsafe_allow_html=True)
