"""
DY Monitoring — Home v4
색상 버그픽스 · 계좌별 차트 · KPI 타이틀 우측 배치 · 레이아웃 재구성
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json, os, re, base64, html as html_lib, requests
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

DATA_DIR  = Path(__file__).parent / "data"
ASSET_DIR = Path(__file__).parent / "assets"

def load_custom_font():
    for ext, fmt in {".woff2":"woff2",".woff":"woff",".ttf":"truetype",".otf":"opentype"}.items():
        fps = sorted(ASSET_DIR.glob(f"*{ext}"))
        if not fps: continue
        fp = fps[0]
        try:
            with open(fp,"rb") as f: b64=base64.b64encode(f.read()).decode()
            return fp.stem, f"@font-face{{font-family:'{fp.stem}';src:url('data:font/{fmt};base64,{b64}') format('{fmt}');}}"
        except: continue
    return None, ""

CUSTOM_FONT, FONT_FACE_CSS = load_custom_font()
FF = f"'{CUSTOM_FONT}',sans-serif" if CUSTOM_FONT else "'Pretendard Variable','Inter',sans-serif"

# ── 색상 팔레트 ────────────────────────────────────────────────
BG   = "#07090F"; CARD = "#0D1117"; C2   = "#131924"; C3   = "#1A2233"
BORD = "#1E2433"; BORD2= "#2D3748"; TXT  = "#EAEEF2"; SUB  = "#8B949E"; MUT  = "#484F58"
UP   = "#E24B4A"   # 상승 = 빨강 (한국 관례)
DN   = "#388BFD"   # 하락 = 파랑 (한국 관례)
B5   = "#388BFD"; B3 = "#79C0FF"; GOLD = "#D4A017"

# 계좌별 색상
ACCT_COLORS = {
    "일반":     "#388BFD",  # 파랑
    "DC":       "#E24B4A",  # 빨강
    "연금저축": "#3FB950",  # 초록
}
ACCT_LABELS = {
    "일반":     "💳 일반",
    "DC":       "🏢 DC",
    "연금저축": "🏦 연금저축",
}

now = datetime.now()
BRIEF_KEY = "home_brief"

# ════════════════════════════════════════════════════════════════
# CSS — 핵심 수정: span/div에 color!important 제거 (인라인 색상 복원)
# ════════════════════════════════════════════════════════════════
st.markdown(
    FONT_FACE_CSS
    + '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.8/dist/web/variable/pretendardvariable.min.css">'
    + '<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">'
    + f"""<style>
html,body{{background-color:{BG}!important;color:{TXT}!important;font-family:{FF}!important;letter-spacing:-.02em!important;font-size:14px!important}}
[class*="css"]{{background-color:{BG}!important;font-family:{FF}!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
[data-testid="stSidebar"]{{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
#MainMenu,footer,header{{visibility:hidden}}
.block-container{{padding:.8rem 1.8rem 3rem!important;max-width:100%!important;background:transparent!important}}
/* 주의: span,div에 color!important 없음 → 인라인 색상이 정상 작동 */
label{{color:{TXT}!important}}
.stButton>button{{background:transparent!important;color:{SUB}!important;border:1px solid {BORD}!important;border-radius:6px!important;font-family:{FF}!important;font-size:12px!important;font-weight:500!important;padding:5px 14px!important;box-shadow:none!important;transition:all .12s!important}}
.stButton>button:hover{{border-color:{B5}!important;color:{B5}!important;background:{C2}!important}}
[data-testid="stRadio"]>div{{gap:2px!important;flex-direction:row!important}}
[data-testid="stRadio"]>div>label{{background:transparent!important;color:{SUB}!important;border:1px solid {BORD}!important;border-radius:5px!important;padding:4px 11px!important;font-size:11px!important;font-family:{FF}!important;font-weight:500!important;cursor:pointer!important;transition:all .12s!important}}
[data-testid="stRadio"]>div>label[data-selected="true"]{{background:{C2}!important;color:{TXT}!important;border-color:{BORD2}!important}}
.js-plotly-plot{{border-radius:0!important}}
::-webkit-scrollbar{{width:3px;height:3px}}
::-webkit-scrollbar-track{{background:transparent}}
::-webkit-scrollbar-thumb{{background:{BORD2};border-radius:2px}}
/* 티커 */
.ticker-wrap{{overflow:hidden;background:{CARD};border-bottom:1px solid {BORD};padding:7px 0}}
.ticker-track{{display:flex;width:max-content;animation:ticker-run 60s linear infinite}}
.ticker-track:hover{{animation-play-state:paused}}
@keyframes ticker-run{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}
.ticker-item{{display:flex;align-items:center;gap:8px;padding:0 22px;border-right:1px solid {BORD};white-space:nowrap}}
.qld-divider{{height:1px;background:{BORD};margin:1.2rem 0}}
</style>""",
    unsafe_allow_html=True
)

# ════════════════════════════════════════════════════════════════
# 데이터 / 헬퍼
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


# ── 실시간 가격 조회 (개선 1) ─────────────────────────────────
@st.cache_data(ttl=180)  # 3분 캐시
def fetch_live_prices(tickers_tuple):
    """yfinance fast_info로 현재가 + 전일종가 일괄 수집"""
    import yfinance as yf
    out = {}
    for tk in tickers_tuple:
        try:
            fi = yf.Ticker(tk).fast_info
            cur  = fi.get("lastPrice") or fi.get("last_price")
            prev = fi.get("previousClose") or fi.get("previous_close")
            if cur:
                out[tk] = {"cur": float(cur),
                           "prev": float(prev) if prev else float(cur)}
        except Exception:
            continue
    return out

# ── 데이터 신선도 배너 (개선 3) ────────────────────────────────
def render_freshness_banner(prices_df_):
    if prices_df_.empty or "date" not in prices_df_.columns:
        st.markdown(
            '<div style="background:#3D1418;border:1px solid #F85149;border-radius:8px;'
            'padding:10px 16px;margin-bottom:.8rem;font-size:12px;color:#F85149;font-weight:600">'
            '⚠ 가격 데이터가 없습니다 — GitHub Actions 실행 여부를 확인하세요'
            '</div>', unsafe_allow_html=True)
        return
    last = prices_df_["date"].max()
    try:
        biz_days = max(0, len(pd.bdate_range(
            last.normalize(), pd.Timestamp.now().normalize())) - 1)
    except Exception:
        biz_days = 0
    if biz_days >= 2:
        st.markdown(
            '<div style="background:#3A2E10;border:1px solid #D4A017;border-radius:8px;'
            'padding:10px 16px;margin-bottom:.8rem;font-size:12px;color:#D4A017;font-weight:600">'
            f'⚠ 데이터가 <b>{biz_days}영업일</b> 지났습니다 (최종: {last:%Y-%m-%d}) '
            '— 수집이 멈췄을 수 있습니다. GitHub Actions를 확인하세요'
            '</div>', unsafe_allow_html=True)
    elif biz_days == 1:
        st.markdown(
            '<div style="background:#131924;border:1px solid #388BFD44;border-radius:8px;'
            'padding:8px 16px;margin-bottom:.8rem;font-size:11px;color:#8B949E">'
            f'ℹ 가격 기준: {last:%Y-%m-%d} (전 거래일 종가)</div>',
            unsafe_allow_html=True)

market    = load_pq("market_prices.parquet")
fred      = load_pq("fred_indicators.parquet")
portfolio = load_json("portfolio.json", [])
prices_df = load_pq("portfolio_prices.parquet")

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

def sparkline_svg(df, ind, color=B5, days=60, w=55, h=20):
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
    gid = "spk" + re.sub(r'\W','',ind)[:8]; lx, ly = pts[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="display:block;overflow:visible">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity=".22"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity=".02"/>'
            f'</linearGradient></defs>'
            f'<path d="{fd}" fill="url(#{gid})"/>'
            f'<path d="{ld}" fill="none" stroke="{color}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{lx}" cy="{ly}" r="2" fill="{color}"/></svg>')

# ── 포지션 계산 ──────────────────────────────────────────────
fx_row = lat(market, "USDKRW")
fx = float(fx_row["value"]) if fx_row is not None else 1380.0

@st.cache_data(ttl=300)
def get_positions():
    if not portfolio: return []
    # 실시간 가격 수집 (개선 1: parquet 없어도 동작, 있으면 폴백)
    all_tickers = tuple(sorted({
        it.get("ticker","") for it in portfolio
        if isinstance(it,dict) and it.get("ticker")
    }))
    live = fetch_live_prices(all_tickers) if all_tickers else {}
    out = []
    for it in portfolio:
        if not isinstance(it, dict): continue
        lots = [l for l in it.get("lots",[]) if isinstance(l,dict)]
        ticker = it.get("ticker","")
        if not lots or not ticker: continue
        qty  = sum(l.get("qty",0) for l in lots)
        cost = sum(l.get("qty",0)*l.get("price",0) for l in lots)
        if qty<=0: continue
        avg = cost/qty
        # 우선순위: 실시간 > parquet > skip
        if ticker in live:
            cur  = live[ticker]["cur"]
            prev = live[ticker]["prev"]
        elif not prices_df.empty:
            sub = prices_df[prices_df["ticker"]==ticker].sort_values("date")
            if sub.empty: continue
            cur  = float(sub.iloc[-1]["close"])
            prev = float(sub.iloc[-2]["close"]) if len(sub)>=2 else cur
        else:
            continue
        fxv = fx if it.get("currency")=="USD" else 1
        out.append({
            "name":      it.get("name",""),
            "ticker":    ticker,
            "account":   it.get("account","일반"),
            "currency":  it.get("currency","KRW"),
            "sector":    it.get("sector",""),
            "qty":       qty, "avg": avg, "cur": cur,
            "value_krw": cur*qty*fxv,
            "pnl_krw":   (cur-avg)*qty*fxv,
            "pnl_pct":   (cur/avg-1)*100 if avg>0 else 0,
            "daily_pct": (cur/prev-1)*100 if prev>0 else 0,
            "live":      ticker in live,  # 실시간 여부 표시
        })
    return sorted(out, key=lambda x: -x["value_krw"])

positions = get_positions()
tv   = sum(p["value_krw"] for p in positions)
tp   = sum(p["pnl_krw"]   for p in positions)
td   = sum(p["value_krw"]*p["daily_pct"]/100 for p in positions)
dpct = td/(tv-td)*100 if (tv-td)>0 else 0

# ════════════════════════════════════════════════════════════════
# 1. 티커 바 — 인라인 색상 정상 작동 (CSS 버그 수정 후)
# ════════════════════════════════════════════════════════════════
if positions:
    items_html = ""
    for p in positions:
        sym = "▲" if p["daily_pct"]>=0 else "▼"
        clr = UP if p["daily_pct"]>=0 else DN
        price_str = f"${p['cur']:,.2f}" if p["currency"]=="USD" else f"₩{p['cur']:,.0f}"
        items_html += (
            '<div class="ticker-item">'
            + '<span style="font-size:11px;font-weight:600;color:' + TXT + '">' + safe(p["name"]) + '</span>'
            + '<span style="font-size:11px;font-family:JetBrains Mono,monospace;color:' + TXT + '">' + price_str + '</span>'
            + '<span style="font-size:10px;font-family:JetBrains Mono,monospace;font-weight:700;color:' + clr + '">' + sym + f"{abs(p['daily_pct']):.2f}%" + '</span>'
            + '</div>'
        )
    st.markdown(
        '<div class="ticker-wrap"><div class="ticker-track">' + items_html*2 + '</div></div>',
        unsafe_allow_html=True
    )

# ════════════════════════════════════════════════════════════════
# 2-pre. 데이터 신선도 배너 (개선 3)
# ════════════════════════════════════════════════════════════════
render_freshness_banner(prices_df)

# ════════════════════════════════════════════════════════════════
# 2. DY Monitoring 타이틀 + KPI 미니차트 (동일 행)
# ════════════════════════════════════════════════════════════════
KPI_ITEMS = [
    ("S&P500","SPX",market,",.0f"),
    ("NASDAQ","NASDAQ",market,",.0f"),
    ("KOSPI","KOSPI",market,",.0f"),
    ("KOSDAQ","KOSDAQ",market,",.0f"),
    ("VIX","VIX",market,".1f"),
    ("USD/KRW","USDKRW",market,",.0f"),
    ("US 10Y","US_10Y",fred,".2f"),
]

# KPI 카드 HTML 사전 생성 (7개 → grid)
kpi_cards_html = '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:7px;align-items:start">'
for (lbl, ind, df_, fmt) in KPI_ITEMS:
    r = lat(df_, ind); d, p = dlt_info(df_, ind)
    spk = sparkline_svg(df_, ind, color=(UP if p>=0 else DN), days=60)
    sym = "▲" if p>=0 else "▼"
    clr = UP if p>=0 else DN
    val_str = format(r["value"], fmt) if r is not None else "—"
    chg_str = f"{sym}{abs(p):.2f}%" if r is not None else ""
    opacity = "1" if r is not None else "0.4"
    kpi_cards_html += (
        '<div style="background:' + CARD + ';border:1px solid ' + BORD + ';border-radius:7px;padding:10px 11px;opacity:' + opacity + '">'
        + '<div style="font-size:9px;color:' + SUB + ';text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">' + lbl + '</div>'
        + '<div style="font-size:16px;font-weight:700;font-family:JetBrains Mono,monospace;color:' + TXT + ';line-height:1;margin-bottom:4px">' + val_str + '</div>'
        + '<div style="font-size:10px;font-weight:700;font-family:JetBrains Mono,monospace;color:' + clr + '">' + chg_str + '</div>'
        + '<div style="margin-top:5px">' + spk + '</div>'
        + '</div>'
    )
kpi_cards_html += '</div>'

title_col, kpi_col = st.columns([3, 7])
with title_col:
    d_sym_t = "↑" if td>=0 else "↓"
    d_clr_t = UP if td>=0 else DN
    st.markdown(
        '<div style="padding:18px 0 14px">'
        + '<div style="font-size:26px;font-weight:800;font-style:italic;line-height:1.2;margin-bottom:5px">'
        + '<span style="background:rgba(56,139,253,.18);padding:2px 10px;border-radius:6px;color:' + TXT + '">DY Monitoring</span>'
        + '</div>'
        + '<div style="font-size:11px;color:' + MUT + ';font-family:JetBrains Mono,monospace;margin-bottom:10px">'
        + '한미 매크로 · 투자자산 · 이슈 · 매일 KST 07:00</div>'
        + '<div style="font-size:13px;font-weight:600;color:' + d_clr_t + ';font-family:JetBrains Mono,monospace">'
        + d_sym_t + f' 전일 {td:+,.0f}원 ({dpct:+.2f}%)'
        + '</div>'
        + '</div>',
        unsafe_allow_html=True
    )

with kpi_col:
    st.markdown('<div style="padding-top:18px">' + kpi_cards_html + '</div>', unsafe_allow_html=True)

st.markdown('<div class="qld-divider"></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 3. 오늘의 브리핑 (문자열 연결 방식 — HTML 버그 없음)
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
    prices   = load_pq("portfolio_prices.parquet")
    pf_data  = load_json("portfolio.json", [])
    news_raw = load_json("portfolio_news.json", {})
    nl = "\n"
    mkt_lines = []
    for ind, lbl in [("SPX","S&P500"),("NASDAQ","NASDAQ"),("KOSPI","KOSPI"),
                     ("KOSDAQ","KOSDAQ"),("VIX","VIX"),("USDKRW","USD/KRW"),("US_10Y","미국10Y금리")]:
        df_src = fred if ind=="US_10Y" else market
        r = lat(df_src, ind)
        if r is not None:
            _, p2 = dlt_info(df_src, ind)
            sym = "▲" if p2>=0 else "▼"
            mkt_lines.append(f"  {lbl}: {r['value']:,.2f} ({sym}{abs(p2):.2f}%)")
    hold_lines = []
    if isinstance(pf_data, list):
        for it in pf_data:
            if not isinstance(it,dict): continue
            lots = [l for l in it.get("lots",[]) if isinstance(l,dict)]
            ticker = it.get("ticker","")
            if not lots or not ticker: continue
            qty = sum(l.get("qty",0) for l in lots)
            cost= sum(l.get("qty",0)*l.get("price",0) for l in lots)
            if qty<=0: continue
            avg = cost/qty
            sub = prices[prices["ticker"]==ticker].sort_values("date") if not prices.empty else pd.DataFrame()
            if sub.empty: continue
            cur2 = float(sub.iloc[-1]["close"])
            prev2= float(sub.iloc[-2]["close"]) if len(sub)>=2 else cur2
            fxv  = fx if it.get("currency")=="USD" else 1
            val  = cur2*qty*fxv; dpct2=(cur2/prev2-1)*100 if prev2 else 0
            hold_lines.append(f"  {it.get('name','')}({it.get('sector','')}) 현재:{cur2:,.2f} 일간:{'▲' if dpct2>=0 else '▼'}{abs(dpct2):.2f}% 수익률:{(cur2/avg-1)*100:+.2f}% 평가:{val:,.0f}원")
    news_lines = []
    for cat in ("stocks","sectors"):
        for key, arts in news_raw.get(cat,{}).items():
            if isinstance(arts,list):
                for n in arts:
                    if isinstance(n,dict):
                        sc = n.get("score")
                        if sc is not None and (sc>=8 or sc<=2):
                            tag = "호재" if sc>=6 else "악재"
                            news_lines.append(f"  [{tag}{sc}] {key}: {n.get('ai_summary') or n.get('title','')[:55]}")
    return (
        f"한국 retail 투자자를 위한 실시간 투자 브리핑을 작성하세요.\n\n"
        f"[{now.strftime('%Y-%m-%d %H:%M')} 기준]\n\n"
        f"▣ 글로벌 시장 지표\n{nl.join(mkt_lines) or '  (데이터 없음)'}\n\n"
        f"▣ 보유 종목 현황\n{nl.join(hold_lines) or '  (데이터 없음)'}\n"
        f"  총평가:{tv:,.0f}원  누적손익:{tp:+,.0f}원\n\n"
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
        result["realtime"] = True
        return result
    except Exception as e:
        st.error(f"브리핑 생성 오류: {e}"); return None

brief = load_brief()
if BRIEF_KEY in st.session_state: brief = st.session_state[BRIEF_KEY]

bc1, bc2 = st.columns([5,1])
with bc1:
    st.markdown('<div style="font-size:11px;color:' + MUT + ';text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">오늘의 브리핑</div>', unsafe_allow_html=True)
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
    mood_map = {"positive": UP, "neutral": SUB, "cautious": B5}
    mc    = mood_map.get(brief.get("mood","neutral"), SUB)
    gen_t = safe(brief.get("generated_at",""))
    mood_ = safe(brief.get("mood","")).upper()
    hl    = safe(brief.get("headline",""))
    mkt_b = safe(brief.get("market",""))
    hold  = safe(brief.get("holdings",""))
    sect  = safe(brief.get("sectors",""))
    news_ = safe(brief.get("news",""))
    act   = safe(brief.get("action",""))
    rt_tag = '<span style="background:' + B5 + '22;color:' + B5 + ';padding:2px 8px;border-radius:4px;font-size:9px;font-weight:600;font-family:JetBrains Mono">실시간</span>' if brief.get("realtime") else ""
    st.markdown(
        '<div style="background:' + CARD + ';border:1px solid ' + BORD + ';border-radius:8px;padding:16px 18px">'
        + '<div style="margin-bottom:10px;overflow:hidden">'
        + '<span style="float:right;font-size:9px;color:' + MUT + ';font-family:JetBrains Mono,monospace">' + gen_t + '</span>'
        + '<div style="display:flex;align-items:center;gap:6px">'
        + '<span style="width:7px;height:7px;border-radius:50%;background:' + mc + ';display:inline-block;flex-shrink:0"></span>'
        + '<span style="font-size:11px;color:' + mc + ';font-weight:600;text-transform:uppercase">' + mood_ + '</span>'
        + rt_tag + '</div></div>'
        + '<div style="font-size:18px;font-weight:700;color:' + TXT + ';line-height:1.3;margin-bottom:12px">' + hl + '</div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;margin-bottom:10px">'
        + '<div style="background:' + C2 + ';border-radius:6px;padding:10px 12px"><div style="font-size:9px;color:' + MUT + ';text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px">📊 시장</div><div style="font-size:11px;color:' + TXT + ';line-height:1.6">' + mkt_b + '</div></div>'
        + '<div style="background:' + C2 + ';border-radius:6px;padding:10px 12px"><div style="font-size:9px;color:' + MUT + ';text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px">💼 종목</div><div style="font-size:11px;color:' + TXT + ';line-height:1.6">' + hold + '</div></div>'
        + '<div style="background:' + C2 + ';border-radius:6px;padding:10px 12px"><div style="font-size:9px;color:' + MUT + ';text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px">🏭 섹터</div><div style="font-size:11px;color:' + TXT + ';line-height:1.6">' + sect + '</div></div>'
        + '<div style="background:' + C2 + ';border-radius:6px;padding:10px 12px"><div style="font-size:9px;color:' + MUT + ';text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px">📰 뉴스</div><div style="font-size:11px;color:' + TXT + ';line-height:1.6">' + news_ + '</div></div>'
        + '</div>'
        + '<div style="padding:9px 12px;background:' + C2 + ';border-radius:6px;font-size:12px;color:' + TXT + ';font-weight:500">💬 ' + act + '</div>'
        + '</div>',
        unsafe_allow_html=True
    )
else:
    st.markdown('<div style="background:' + CARD + ';border:1px solid ' + BORD + ';border-radius:8px;padding:24px;text-align:center"><div style="font-size:13px;color:' + MUT + '">브리핑 없음 — 🔄 버튼으로 생성하거나 GitHub Actions를 실행하세요</div></div>', unsafe_allow_html=True)

st.markdown('<div class="qld-divider"></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 4. 총 평가금액 + 계좌별 차트 (2열 히어로)
# ════════════════════════════════════════════════════════════════
left, right = st.columns([4, 6], gap="large")

HOLD_COLORS = ["#388BFD","#79C0FF","#1F6FEB","#58A6FF","#2F81F7","#CAE8FF","#0D6EFD","#4A82E4","#9ECEFF","#1158C7"]

# ── 왼쪽: 총 평가금액 + 종목 목록 ────────────────────────────
with left:
    d_sym = "↑" if td>=0 else "↓"
    d_clr = UP if td>=0 else DN
    st.markdown(
        '<div style="font-size:11px;color:' + SUB + ';letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px">총 평가금액</div>'
        + '<div style="font-size:40px;font-weight:700;line-height:1;letter-spacing:-.03em;font-family:JetBrains Mono,monospace;color:' + TXT + ';margin-bottom:10px">'
        + f'{tv:,.0f}<span style="font-size:17px;color:' + SUB + ';margin-left:5px">원</span></div>'
        + '<div style="font-size:14px;font-weight:600;font-family:JetBrains Mono,monospace;color:' + d_clr + ';margin-bottom:18px">'
        + d_sym + f' 전일 {td:+,.0f}원 ({dpct:+.2f}%)</div>',
        unsafe_allow_html=True
    )

    # 계좌별 요약 배지
    acct_vals = {}
    for p in positions:
        acct_vals[p["account"]] = acct_vals.get(p["account"],0) + p["value_krw"]

    if acct_vals:
        badges_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">'
        for acct, val in sorted(acct_vals.items(), key=lambda x: -x[1]):
            clr = ACCT_COLORS.get(acct, B5)
            badges_html += (
                '<div style="background:' + clr + '18;border:1px solid ' + clr + '44;border-radius:6px;padding:6px 10px">'
                + '<div style="font-size:9px;color:' + clr + ';font-weight:600;margin-bottom:2px">' + ACCT_LABELS.get(acct,acct) + '</div>'
                + '<div style="font-size:13px;font-weight:700;font-family:JetBrains Mono,monospace;color:' + TXT + '">' + f'{val/1e6:.1f}M' + '</div>'
                + '</div>'
            )
        badges_html += '</div>'
        st.markdown(badges_html, unsafe_allow_html=True)

    # 레인보우 바
    if positions and tv > 0:
        segs = ""
        for i, p in enumerate(positions[:10]):
            w = p["value_krw"]/tv*100
            if w < 0.3: continue
            segs += f'<div style="width:{w:.2f}%;height:100%;background:{HOLD_COLORS[i%len(HOLD_COLORS)]}"></div>'
        st.markdown(
            '<div style="display:flex;height:5px;border-radius:3px;overflow:hidden;background:' + C2 + ';gap:1px;margin-bottom:14px">'
            + segs + '</div>',
            unsafe_allow_html=True
        )

    # 종목 목록 헤더
    st.markdown(
        '<div style="display:flex;padding:3px 0 5px;border-bottom:1px solid ' + BORD + ';gap:8px">'
        + '<span style="font-size:10px;color:' + MUT + ';flex:1">종목</span>'
        + '<span style="font-size:10px;color:' + MUT + ';min-width:38px;text-align:right">비중</span>'
        + '<span style="font-size:10px;color:' + MUT + ';min-width:58px;text-align:right">평가금액</span>'
        + '<span style="font-size:10px;color:' + MUT + ';min-width:50px;text-align:right">수익률</span>'
        + '</div>',
        unsafe_allow_html=True
    )
    for i, p in enumerate(positions[:8]):
        wt   = p["value_krw"]/tv*100 if tv>0 else 0
        pclr = UP if p["pnl_pct"]>=0 else DN
        sp   = "+" if p["pnl_pct"]>=0 else ""
        val_str = f"{p['value_krw']/1e8:.2f}억" if p["value_krw"]>=1e8 else f"{p['value_krw']/1e4:.0f}만"
        acct_clr = ACCT_COLORS.get(p["account"], B5)
        st.markdown(
            '<div style="display:flex;align-items:center;padding:5px 0;border-bottom:1px solid ' + BORD + ';gap:7px">'
            + '<div style="display:flex;align-items:center;gap:6px;flex:1;min-width:0">'
            + '<span style="width:7px;height:7px;border-radius:50%;background:' + HOLD_COLORS[i%len(HOLD_COLORS)] + ';flex-shrink:0"></span>'
            + '<span style="font-size:12px;font-weight:500;color:' + TXT + ';white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + safe(p["name"]) + '</span>'
            + '<span style="background:' + acct_clr + '22;color:' + acct_clr + ';font-size:8px;padding:1px 5px;border-radius:3px;flex-shrink:0;font-weight:600">' + p["account"] + '</span>'
            + '</div>'
            + '<span style="font-size:11px;color:' + SUB + ';min-width:38px;text-align:right;font-family:JetBrains Mono,monospace">' + f'{wt:.1f}%' + '</span>'
            + '<span style="font-size:11px;font-weight:600;color:' + TXT + ';min-width:58px;text-align:right;font-family:JetBrains Mono,monospace">' + val_str + '</span>'
            + '<span style="font-size:11px;font-weight:700;color:' + pclr + ';min-width:50px;text-align:right;font-family:JetBrains Mono,monospace">' + sp + f"{p['pnl_pct']:.2f}%" + '</span>'
            + '</div>',
            unsafe_allow_html=True
        )

    # 요약 하단
    tpct = tp/(tv-tp)*100 if (tv-tp)>0 else 0
    pclr_t = UP if tp>=0 else DN
    st.markdown(
        '<div style="display:flex;gap:18px;margin-top:12px;padding-top:12px;border-top:1px solid ' + BORD + '">'
        + '<div><div style="font-size:10px;color:' + MUT + '">누적 손익</div>'
        + '<div style="font-size:14px;font-weight:700;color:' + pclr_t + ';font-family:JetBrains Mono,monospace">' + f'{tp:+,.0f}원' + '</div>'
        + '<div style="font-size:10px;color:' + pclr_t + ';font-family:JetBrains Mono,monospace">' + f'{tpct:+.2f}%' + '</div></div>'
        + '<div><div style="font-size:10px;color:' + MUT + '">USD 환산</div>'
        + '<div style="font-size:14px;font-weight:700;color:' + TXT + ';font-family:JetBrains Mono,monospace">$' + f'{tv/fx:,.0f}' + '</div>'
        + '<div style="font-size:10px;color:' + MUT + ';font-family:JetBrains Mono,monospace">₩' + f'{fx:,.0f}' + '</div></div>'
        + '</div>',
        unsafe_allow_html=True
    )

# ── 오른쪽: 계좌별 잔고 추이 차트 ────────────────────────────
with right:

    @st.cache_data(ttl=600)
    def compute_account_history(_prices_df, _market_df, _portfolio):
        if _prices_df.empty or not _portfolio or not isinstance(_portfolio, list):
            return pd.DataFrame()
        all_dates = sorted(_prices_df["date"].dropna().unique())
        fx_df = pd.DataFrame()
        if not _market_df.empty and "indicator" in _market_df.columns:
            fx_df = (_market_df[_market_df["indicator"]=="USDKRW"][["date","value"]]
                     .rename(columns={"value":"fx"}).sort_values("date"))
        rows = []
        for d in all_dates:
            fx_now = 1380.0
            if not fx_df.empty:
                fs = fx_df[fx_df["date"]<=d]
                if not fs.empty: fx_now = float(fs.iloc[-1]["fx"])
            acct_vals = {}; total = 0
            for it in _portfolio:
                if not isinstance(it,dict): continue
                acct = it.get("account","일반"); ticker = it.get("ticker")
                if not ticker: continue
                try:
                    lots = [l for l in it.get("lots",[]) if isinstance(l,dict)
                            and pd.Timestamp(l.get("date","2000-01-01"))<=d]
                except: continue
                qty = sum(l.get("qty",0) for l in lots)
                if qty<=0: continue
                ps = _prices_df[(_prices_df["ticker"]==ticker)&(_prices_df["date"]<=d)].sort_values("date")
                if ps.empty: continue
                fxv = fx_now if it.get("currency","KRW")=="USD" else 1
                val = qty*float(ps.iloc[-1]["close"])*fxv
                acct_vals[acct] = acct_vals.get(acct,0)+val; total+=val
            if total>0:
                row={"date":d,"Total":total}; row.update(acct_vals); rows.append(row)
        return pd.DataFrame(rows)

    hist = compute_account_history(prices_df, market, portfolio)

    _, rng_col = st.columns([1,9])
    with rng_col:
        rng = st.radio("기간", ["1W","1M","3M","6M","1Y","ALL"],
                       horizontal=True, label_visibility="collapsed", key="hero_rng")

    rng_cutoffs = {"1W":7,"1M":30,"3M":90,"6M":180,"1Y":365}
    hist_f = (hist[hist["date"] >= pd.Timestamp.now()-pd.Timedelta(days=rng_cutoffs[rng])]
              if rng in rng_cutoffs and not hist.empty else hist)

    if not hist_f.empty and "Total" in hist_f.columns:
        acct_cols = [c for c in hist_f.columns if c not in ["date","Total"]]
        for c in acct_cols:
            hist_f[c] = hist_f[c].fillna(0)

        fig = go.Figure()

        # 계좌별 개별 라인 (색상 반영)
        for acct in acct_cols:
            clr = ACCT_COLORS.get(acct, B5)
            lbl = ACCT_LABELS.get(acct, acct)
            acct_data = hist_f[["date", acct]].dropna()
            if acct_data[acct].sum() == 0: continue
            fig.add_trace(go.Scatter(
                x=acct_data["date"], y=acct_data[acct]/1e6,
                name=lbl,
                mode="lines",
                line=dict(color=clr, width=1.8),
                hovertemplate="<b>" + lbl + "</b> %{y:,.1f}M원<extra></extra>"
            ))

        # 총합계 — 흰색 + 마커 + 면적
        fig.add_trace(go.Scatter(
            x=hist_f["date"], y=hist_f["Total"]/1e6,
            name="총합계",
            mode="lines+markers",
            line=dict(color="#CCCCDC", width=2.0),
            marker=dict(size=3.5, color=BG, line=dict(width=1.2, color="#CCCCDC")),
            fill="tozeroy",
            fillcolor="rgba(160,170,200,0.07)",
            hovertemplate="<b>총합계</b> %{y:,.1f}M원<extra></extra>"
        ))

        # 고점 / 저점 / MDD 어노테이션
        if len(hist_f) > 4:
            peak_i   = hist_f["Total"].idxmax()
            trough_i = hist_f["Total"].idxmin()
            cummax_s = hist_f["Total"].cummax()
            dd_s     = (hist_f["Total"] - cummax_s) / cummax_s
            mdd_i    = dd_s.idxmin()

            anno_list = [
                (peak_i,   "고점",    "#3FB950", "top center"),
                (trough_i, "저점",    "#F5A623", "bottom center"),
            ]
            if mdd_i != trough_i:
                anno_list.append((mdd_i, "MDD 저점", "#F85149", "bottom right"))

            for idx, label, acolor, pos in anno_list:
                if idx not in hist_f.index: continue
                fig.add_trace(go.Scatter(
                    x=[hist_f.loc[idx,"date"]],
                    y=[hist_f.loc[idx,"Total"]/1e6],
                    mode="markers+text",
                    marker=dict(size=10, color=acolor),
                    text=[label],
                    textposition=pos,
                    textfont=dict(size=9, color=acolor, family="JetBrains Mono"),
                    showlegend=False
                ))

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=360,
            margin=dict(l=0, r=10, t=34, b=0),
            title=dict(text="계좌별 평가금액 추이", font=dict(size=12, color=SUB, family=FF), x=0, xanchor="left"),
            legend=dict(orientation="h", y=1.06, x=0, font=dict(size=10,color=SUB,family=FF), bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",
            hoverlabel=dict(bgcolor=C2, bordercolor=BORD, font=dict(family="JetBrains Mono",size=10,color=TXT)),
            xaxis=dict(showgrid=False, zeroline=False, showline=False,
                tickfont=dict(size=9,color=MUT,family="JetBrains Mono"), tickformat="%m/%d"),
            yaxis=dict(showgrid=True, gridcolor=BORD, gridwidth=0.5, zeroline=False, showline=False,
                tickfont=dict(size=9,color=MUT,family="JetBrains Mono"), ticksuffix="M")
        )
        fig.update_xaxes(showspikes=True, spikecolor=BORD, spikethickness=1)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        # 차트 하단 스탯
        if len(hist_f)>=2:
            v_last  = float(hist_f["Total"].iloc[-1])
            v_first = float(hist_f["Total"].iloc[0])
            v_peak  = float(hist_f["Total"].max())
            mdd_pct = (float(hist_f["Total"].min())/v_peak-1)*100
            rng_ret = (v_last/v_first-1)*100
            stat_cols = st.columns(4)
            for col,(lbl,val,sub_,sc) in zip(stat_cols,[
                ("기간 수익", f"{rng_ret:+.2f}%",  rng, UP if rng_ret>=0 else DN),
                ("현재 평가", f"{v_last/1e6:.1f}M", "백만원", TXT),
                ("기간 최고", f"{v_peak/1e6:.1f}M", "백만원", TXT),
                ("MDD",       f"{mdd_pct:.2f}%",    "최대낙폭", DN),
            ]):
                with col:
                    st.markdown(
                        '<div style="background:' + CARD + ';border:1px solid ' + BORD + ';border-radius:7px;padding:9px 11px">'
                        + '<div style="font-size:9px;color:' + SUB + ';text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">' + lbl + '</div>'
                        + '<div style="font-size:14px;font-weight:700;color:' + sc + ';font-family:JetBrains Mono,monospace">' + val + '</div>'
                        + '<div style="font-size:9px;color:' + MUT + ';margin-top:1px">' + sub_ + '</div>'
                        + '</div>',
                        unsafe_allow_html=True
                    )
    else:
        st.markdown('<div style="background:' + CARD + ';border:1px solid ' + BORD + ';border-radius:8px;height:300px;display:flex;align-items:center;justify-content:center;font-size:13px;color:' + MUT + '">Actions 실행 후 차트가 표시됩니다</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 5. 주간 리포트
# ════════════════════════════════════════════════════════════════
weekly = load_json("weekly_report.json", None)
if weekly and isinstance(weekly, dict) and weekly.get("headline"):
    grade = weekly.get("grade","B")
    gc = {"S":UP,"A":B5,"B":B3,"C":SUB,"D":DN}.get(grade, SUB)
    st.markdown(
        '<div style="margin-top:1rem"></div>'
        + '<details style="background:' + CARD + ';border:1px solid ' + BORD + ';border-radius:8px;padding:14px 18px">'
        + '<summary style="font-size:12px;font-weight:600;color:' + TXT + ';list-style:none;display:flex;align-items:center;gap:8px;cursor:pointer">'
        + '📊 주간 리포트'
        + '<span style="background:' + gc + '22;color:' + gc + ';padding:2px 9px;border-radius:4px;font-size:10px;font-weight:700;font-family:JetBrains Mono,monospace">' + safe(grade) + '</span>'
        + '<span style="font-size:12px;color:' + TXT + '">' + safe(weekly.get("headline","")) + '</span>'
        + '<span style="font-size:9px;color:' + MUT + ';margin-left:auto;font-family:JetBrains Mono,monospace">' + safe(weekly.get("week_range","")) + ' · ' + safe(weekly.get("generated_at","")) + '</span>'
        + '</summary>'
        + '<div style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:8px">'
        + '<div style="background:' + C2 + ';border-radius:6px;padding:10px 13px"><div style="font-size:9px;color:' + MUT + ';margin-bottom:4px">성과</div><div style="font-size:11px;color:' + TXT + ';line-height:1.6">' + safe(weekly.get("performance","")) + '</div></div>'
        + '<div style="background:' + C2 + ';border-radius:6px;padding:10px 13px"><div style="font-size:9px;color:' + MUT + ';margin-bottom:4px">시장 환경</div><div style="font-size:11px;color:' + TXT + ';line-height:1.6">' + safe(weekly.get("market_context","")) + '</div></div>'
        + '<div style="background:' + C2 + ';border-radius:6px;padding:10px 13px"><div style="font-size:9px;color:' + MUT + ';margin-bottom:4px">교훈</div><div style="font-size:11px;color:' + TXT + ';line-height:1.6">' + safe(weekly.get("lessons","")) + '</div></div>'
        + '<div style="background:' + C2 + ';border-radius:6px;padding:10px 13px"><div style="font-size:9px;color:' + MUT + ';margin-bottom:4px">다음 주 주목</div><div style="font-size:11px;color:' + TXT + ';line-height:1.6">' + safe(weekly.get("next_week","")) + '</div></div>'
        + '</div></details>',
        unsafe_allow_html=True
    )

# ════════════════════════════════════════════════════════════════
# 6. 다가오는 일정
# ════════════════════════════════════════════════════════════════
_events_raw = load_json("events.json", {})
_events     = _events_raw.get("events",[]) if isinstance(_events_raw, dict) else []
_EV_COLORS  = {"fomc":UP,"cpi":GOLD,"bok":B5,"earnings":B3,"custom":SUB}
_EV_ICONS   = {"fomc":"🏛","cpi":"📊","bok":"🇰🇷","earnings":"💵","custom":"📌"}
_today      = now.date()
_upcoming   = []
for _e in _events:
    try: _d = datetime.strptime(_e["date"],"%Y-%m-%d").date()
    except: continue
    if _d >= _today: _upcoming.append((_d,_e))
_upcoming.sort(key=lambda x: x[0])
_upcoming = _upcoming[:5]

if _upcoming:
    st.markdown(
        '<div class="qld-divider"></div>'
        + '<div style="font-size:11px;color:' + MUT + ';text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">다가오는 일정</div>',
        unsafe_allow_html=True
    )
    ev_cols = st.columns(len(_upcoming))
    for ec,(_d,_e) in zip(ev_cols,_upcoming):
        _dday = (_d-_today).days
        _dl   = "D-DAY" if _dday==0 else f"D-{_dday}"
        _clr  = _EV_COLORS.get(_e.get("type","custom"), SUB)
        _icon = _EV_ICONS.get(_e.get("type","custom"), "📌")
        with ec:
            st.markdown(
                '<div style="background:' + CARD + ';border:1px solid ' + BORD + ';border-radius:8px;padding:12px 14px">'
                + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
                + '<span style="font-size:14px">' + _icon + '</span>'
                + '<span style="background:' + _clr + '22;color:' + _clr + ';padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;font-family:JetBrains Mono,monospace">' + _dl + '</span>'
                + '</div>'
                + '<div style="font-size:12px;font-weight:600;color:' + TXT + ';margin-bottom:3px">' + safe(_e.get("title","")) + '</div>'
                + '<div style="font-size:9px;color:' + MUT + ';font-family:JetBrains Mono,monospace">' + _d.strftime("%m/%d") + ' · ' + safe(_e.get("time","")) + '</div>'
                + '</div>',
                unsafe_allow_html=True
            )

# ════════════════════════════════════════════════════════════════
# 7. 푸터
# ════════════════════════════════════════════════════════════════
st.markdown(
    '<div style="margin-top:2rem;padding:10px 0;border-top:1px solid ' + BORD + ';font-size:10px;color:' + MUT + ';font-family:JetBrains Mono,monospace;display:flex;justify-content:space-between;align-items:center">'
    + '<span>FRED · yfinance · CNN F&amp;G · ECOS · 네이버 뉴스 · DART · 매일 KST 07:00 자동수집</span>'
    + '<span>' + now.strftime("%Y-%m-%d %H:%M") + ' KST</span>'
    + '</div>',
    unsafe_allow_html=True
)
