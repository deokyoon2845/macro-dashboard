"""
DY Monitoring — Home  (계좌별 잔고 추이 차트 적용 + 버그픽스 + 스티키 네비)
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

# ── 유틸 임포트 (sticky nav) ──────────────────────────────────
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    from utils import render_sticky_nav
    render_sticky_nav()
except Exception:
    pass

# ════════════════════════════════════════════════════════════════
# 경로 및 기본 설정
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
            name = fp.stem
            css  = (f"@font-face{{font-family:'{name}';"
                    f"src:url('data:font/{fmt};base64,{b64}') format('{fmt}');}}")
            return name, css
        except: continue
    return None, ""

CUSTOM_FONT, FONT_FACE_CSS = load_custom_font()
FF = f"'{CUSTOM_FONT}',sans-serif" if CUSTOM_FONT else "'Inter','Gowun Batang',sans-serif"

# ════════════════════════════════════════════════════════════════
# 색상
# ════════════════════════════════════════════════════════════════
BG   = "#0A0D13"; CARD = "#111620"; C2   = "#161C28"; C3   = "#1C2438"
BORD = "#222A3A"; G    = "#181F2C"; TXT  = "#E4EAF6"; SUB  = "#7A8CA4"; MUT  = "#4A5668"
BLUE = "#388BFD"; B5   = "#388BFD"; B6   = "#2F81F7"; B7   = "#1F6FEB"
PUR_DK = "#79C0FF"; GOLD = "#F5A623"
UP = "#2ECC71"; DN = "#E74C3C"

# 계좌별 색상 및 라벨 정의
ACCT_COLORS = {"일반":"#388BFD", "DC":"#79C0FF", "연금저축":"#1F6FEB"}
ACCT_LABELS = {"일반":"💳 일반 종합매매", "DC":"🏢 퇴직연금 DC", "연금저축":"🏦 연금저축펀드"}

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
    except Exception: return pd.DataFrame()

def load_json(fn, default=None):
    p = DATA_DIR / fn
    if not p.exists(): return default or {}
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except Exception: return default or {}

def get_secret(k, default=""):
    try:    return st.secrets[k]
    except: return os.environ.get(k, default)

def safe(v):
    return html_lib.escape(str(v)) if v else ""

# ════════════════════════════════════════════════════════════════
# CSS
# ════════════════════════════════════════════════════════════════
st.markdown(
    FONT_FACE_CSS +
    """<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Gowun+Batang:wght@400;700&display=swap" rel="stylesheet">""" +
    f"""<style>
    html,body,[class*="css"]{{background-color:{BG}!important;color:{TXT}!important;font-family:{FF}!important;letter-spacing:-.01em!important}}
    .block-container{{padding:1.2rem 2rem 3rem!important;max-width:100%!important;background:transparent!important}}
    [data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
    [data-testid="stSidebar"]{{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
    #MainMenu,footer,header{{visibility:hidden}}
    p,span,div,label{{color:{TXT}!important}}
    .stButton>button{{background:{C2}!important;color:{TXT}!important;border:1px solid {BORD}!important;border-radius:8px!important;font-family:{FF}!important;font-size:12px!important;font-weight:500!important;padding:6px 16px!important;box-shadow:none!important;transition:all .15s!important}}
    .stButton>button:hover{{border-color:{B5}!important;color:{B5}!important;background:{C3}!important}}
    </style>""",
    unsafe_allow_html=True
)

# ════════════════════════════════════════════════════════════════
# 헬퍼 함수
# ════════════════════════════════════════════════════════════════
market = load_pq("market_prices.parquet")
fred   = load_pq("fred_indicators.parquet")

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

def sparkline(df, ind, color=BLUE, days=60, w=72, h=26):
    s = ser_h(df, ind, days)
    vals = s["value"].dropna().tolist() if not s.empty else []
    if len(vals) < 3: return ""
    mn, mx = min(vals), max(vals); mg = 2
    if mn == mx:
        pts = [(round(i*w/(len(vals)-1),1), h/2) for i in range(len(vals))]
    else:
        pts = [(round(i*w/(len(vals)-1),1), round(h-mg-(v-mn)/(mx-mn)*(h-mg*2),1)) for i,v in enumerate(vals)]
    ld = "M " + " L ".join(f"{x},{y}" for x,y in pts)
    fd = ld + f" L {pts[-1][0]},{h} L {pts[0][0]},{h} Z"
    gid = "g" + re.sub(r'\W','',ind)[:8]
    lx, ly = pts[-1]
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="display:block"><defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{color}" stop-opacity=".3"/><stop offset="100%" stop-color="{color}" stop-opacity=".02"/></linearGradient></defs><path d="{fd}" fill="url(#{gid})"/><path d="{ld}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="{lx}" cy="{ly}" r="2.2" fill="{color}"/></svg>'

# ════════════════════════════════════════════════════════════════
# 헤더
# ════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="padding:14px 0 12px;border-bottom:1px solid {BORD};margin-bottom:1rem">
  <div style="font-size:26px;font-weight:800;font-style:italic;line-height:1.2;margin-bottom:3px">
    <span style="background:rgba(56,139,253,.22);padding:2px 10px;border-radius:6px">DY Monitoring</span>
  </div>
  <div style="font-size:11px;color:{MUT};font-family:'JetBrains Mono',monospace">
    한미 매크로 · 투자자산 · 일정 · 이슈 종합 대시보드 &nbsp;·&nbsp; 매일 KST 07:00 자동수집
  </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# KPI 7개
# ════════════════════════════════════════════════════════════════
KPI_ITEMS = [
    ("S&P500","SPX",market,",.0f"),("NASDAQ","NASDAQ",market,",.0f"),
    ("KOSPI","KOSPI",market,",.0f"),("KOSDAQ","KOSDAQ",market,",.0f"),
    ("VIX","VIX",market,".1f"),("USD/KRW","USDKRW",market,",.0f"),
    ("US 10Y","US_10Y",fred,".2f"),
]
kpi_cols = st.columns(7)
for col,(lbl,ind,df_,fmt) in zip(kpi_cols, KPI_ITEMS):
    r = lat(df_, ind); d, p = dlt_info(df_, ind)
    spk = sparkline(df_, ind, color=BLUE)
    sym = "▲" if p >= 0 else "▼"
    with col:
        if r is not None:
            st.markdown(f"""
            <div style="background:{CARD};border:1px solid {BORD};border-left:3px solid {BLUE};border-radius:8px;padding:10px 12px 8px">
              <div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px">{lbl}</div>
              <div style="font-size:17px;font-weight:700;color:{TXT};font-family:'JetBrains Mono',monospace;line-height:1.1">{format(r["value"],fmt)}</div>
              <div style="font-size:9px;color:{BLUE};font-weight:600;margin:3px 0;font-family:'JetBrains Mono',monospace">{sym}{abs(p):.2f}%</div>
              <div style="margin-top:4px">{spk}</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="background:{CARD};border:1px solid {BORD};border-left:3px solid {BORD};border-radius:8px;padding:10px 12px 8px;opacity:.5"><div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px">{lbl}</div><div style="font-size:17px;font-weight:700;color:{MUT}">—</div></div>', unsafe_allow_html=True)

st.markdown('<div style="height:.8rem"></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 브리핑 생성 관련 로직
# ════════════════════════════════════════════════════════════════
BRIEF_FILE = DATA_DIR / "daily_briefing.json"

def load_brief():
    if BRIEF_FILE.exists():
        try:
            with open(BRIEF_FILE, encoding="utf-8") as f: return json.load(f)
        except Exception: return None
    return None

def save_brief(data):
    DATA_DIR.mkdir(exist_ok=True)
    with open(BRIEF_FILE,"w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def build_prompt():
    prices    = load_pq("portfolio_prices.parquet")
    portfolio = load_json("portfolio.json", [])
    news_data = load_json("portfolio_news.json", {})
    nl = "\n"

    # 시장 지표
    mkt_lines = []
    for ind, lbl in [("SPX","S&P500"),("NASDAQ","NASDAQ"),("KOSPI","KOSPI"),("KOSDAQ","KOSDAQ"),("VIX","VIX"),("USDKRW","USD/KRW"),("US_10Y","미국10Y금리")]:
        df_src = fred if ind == "US_10Y" else market
        r = lat(df_src, ind)
        if r is not None:
            _, p = dlt_info(df_src, ind)
            sym = "▲" if p>=0 else "▼"
            mkt_lines.append(f"  {lbl}: {r['value']:,.2f} ({sym}{abs(p):.2f}%)")

    # 보유 종목 수익률 계산 (방어코드 추가)
    fx_row = lat(market, "USDKRW")
    fx = float(fx_row["value"]) if fx_row is not None else 1380.0
    hold_lines = []; tv = 0.0; tp = 0.0
    
    if isinstance(portfolio, list):
        for it in portfolio:
            if not isinstance(it, dict): continue
            lots = [l for l in it.get("lots", []) if isinstance(l, dict)]
            ticker = it.get("ticker", "")
            if not lots or not ticker: continue
            
            qty  = sum(l.get("qty", 0) for l in lots)
            cost = sum(l.get("qty", 0) * l.get("price", 0) for l in lots)
            if qty <= 0: continue
            avg  = cost/qty
            
            sub = prices[prices["ticker"]==ticker].sort_values("date") if not prices.empty else pd.DataFrame()
            if sub.empty: continue
            
            cur  = float(sub.iloc[-1]["close"])
            prev = float(sub.iloc[-2]["close"]) if len(sub)>=2 else cur
            fxv  = fx if it.get("currency")=="USD" else 1
            val  = cur*qty*fxv; pnl=(cur-avg)*qty*fxv
            dpct = (cur/prev-1)*100 if prev else 0
            tv  += val; tp += pnl
            sym  = "▲" if dpct>=0 else "▼"
            hold_lines.append(f"  {it.get('name','')}({it.get('sector','')}) 현재:{cur:,.2f} 일간:{sym}{abs(dpct):.2f}% 수익률:{(cur/avg-1)*100:+.2f}% 평가:{val:,.0f}원")

    pf_sum = f"  총평가:{tv:,.0f}원  누적손익:{tp:+,.0f}원 ({tp/(tv-tp)*100:+.2f}%)" if tv>0 else "  (데이터 없음)"

    # 뉴스
    news_lines = []
    for cat in ("stocks","sectors"):
        for key, arts in news_data.get(cat,{}).items():
            if isinstance(arts, list):
                for n in arts:
                    if isinstance(n, dict):
                        sc = n.get("score")
                        if sc is not None and (sc>=8 or sc<=2):
                            tag = "호재" if sc>=6 else "악재"
                            news_lines.append(f"  [{tag}{sc}] {key}: {n.get('ai_summary') or n.get('title','')[:55]}")

    return (
        f"한국 retail 투자자를 위한 실시간 투자 브리핑을 작성하세요.\n\n"
        f"[{now.strftime('%Y-%m-%d %H:%M')} 기준]\n\n"
        f"▣ 글로벌 시장 지표\n{nl.join(mkt_lines) or '  (데이터 없음)'}\n\n"
        f"▣ 보유 종목 현황\n{nl.join(hold_lines) or '  (데이터 없음)'}\n{pf_sum}\n\n"
        f"▣ AI 점수 주요 뉴스\n{nl.join(news_lines[:8]) or '  (뉴스 없음)'}\n\n"
        f"다음 JSON만 반환 (다른 텍스트 금지):\n"
        f'{{"headline":"오늘 핵심 1줄(25자이내)","market":"시장 분석 2-3문장","holdings":"보유 종목 분석 2-3문장","sectors":"보유 섹터 흐름 1-2문장","news":"주목 뉴스 영향 1-2문장","action":"투자 액션 코멘트 1문장","mood":"positive 또는 neutral 또는 cautious"}}'
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
        result["realtime"]     = True
        return result
    except Exception as e:
        st.error(f"브리핑 생성 오류: {e}")
        return None

# ════════════════════════════════════════════════════════════════
# 브리핑 UI
# ════════════════════════════════════════════════════════════════
brief = load_brief()
if BRIEF_KEY in st.session_state: brief = st.session_state[BRIEF_KEY]

bc1, bc2 = st.columns([5,1])
with bc1: st.markdown(f'<div style="font-size:16px;font-weight:700;color:{TXT};margin-bottom:.5rem">📡 오늘의 브리핑</div>', unsafe_allow_html=True)
with bc2:
    if st.button("🔄 지금 생성", key="brief_refresh", use_container_width=True):
        api_key = get_secret("ANTHROPIC_API_KEY")
        if not api_key or api_key.startswith("*"):
            st.warning("Streamlit Secrets에 ANTHROPIC_API_KEY를 등록하세요.")
        else:
            with st.spinner("Claude가 브리핑 생성 중…"):
                nb
