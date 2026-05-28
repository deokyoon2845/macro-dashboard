"""
DY Monitoring — Home
실시간 브리핑 · KPI 스파크라인 · 보유 종목 차트 · 24시간 표기
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json, os, re, base64
from pathlib import Path
from datetime import datetime
 
st.set_page_config(
    page_title="DY Monitoring", page_icon="◈",
    layout="wide", initial_sidebar_state="expanded"
)
 
# ════════════════════════════════════════════════════════════════
# 경로
# ════════════════════════════════════════════════════════════════
DATA_DIR  = Path(__file__).parent / "data"
ASSET_DIR = Path(__file__).parent / "assets"
 
# ════════════════════════════════════════════════════════════════
# 커스텀 폰트 자동 로드 (assets/ 폴더의 .woff2/.woff/.ttf/.otf)
# ════════════════════════════════════════════════════════════════
def load_custom_font():
    fmt_map = {".woff2":"woff2", ".woff":"woff", ".ttf":"truetype", ".otf":"opentype"}
    for ext, fmt in fmt_map.items():
        fps = sorted(ASSET_DIR.glob(f"*{ext}"))
        if not fps:
            continue
        fp = fps[0]
        try:
            with open(fp, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            name = fp.stem
            css  = (f"@font-face{{font-family:'{name}';"
                    f"src:url('data:font/{fmt};base64,{b64}') format('{fmt}');}}")
            return name, css
        except:
            continue
    return None, ""
 
CUSTOM_FONT, FONT_FACE_CSS = load_custom_font()
FF = f"'{CUSTOM_FONT}',sans-serif" if CUSTOM_FONT else "'Inter','Gowun Batang',sans-serif"
 
# ════════════════════════════════════════════════════════════════
# 색상 팔레트  (KPI 강조색 BLUE 단일)
# ════════════════════════════════════════════════════════════════
BG   = "#0A0D13"; CARD = "#111620"; C2   = "#161C28"; C3   = "#1C2438"
BORD = "#222A3A"; G    = "#181F2C"; TXT  = "#E4EAF6"; SUB  = "#7A8CA4"; MUT  = "#4A5668"
BLUE = "#388BFD"   # KPI 단일 강조색 (UP/DN 대신)
B5   = "#388BFD";  B6   = "#2F81F7"; B7   = "#1F6FEB"
PUR_DK = "#79C0FF"; GOLD = "#F5A623"
UP = "#2ECC71";    DN   = "#E74C3C"
 
now = datetime.now()
 
# ════════════════════════════════════════════════════════════════
# 데이터 로드
# ════════════════════════════════════════════════════════════════
@st.cache_data(ttl=600)
def load_pq(fn):
    p = DATA_DIR / fn
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df
 
def load_json(fn, default=None):
    p = DATA_DIR / fn
    if not p.exists():
        return default or {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)
 
def get_secret(k, default=""):
    try:    return st.secrets[k]
    except: return os.environ.get(k, default)
 
# ════════════════════════════════════════════════════════════════
# CSS — 커스텀 폰트 + 다크 테마
# ════════════════════════════════════════════════════════════════
st.markdown(f"""
{FONT_FACE_CSS}
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Gowun+Batang:wght@400;700&display=swap" rel="stylesheet">
<style>
html,body,[class*="css"]{{
  background-color:{BG}!important; color:{TXT}!important;
  font-family:{FF}!important; letter-spacing:-.01em!important}}
.block-container{{padding:1.2rem 2rem 3rem!important;max-width:100%!important;background:transparent!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
[data-testid="stSidebar"]{{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
#MainMenu,footer,header{{visibility:hidden}}
p,span,div,label{{color:{TXT}!important}}
.stButton>button{{
  background:{C2}!important; color:{TXT}!important;
  border:1px solid {BORD}!important; border-radius:8px!important;
  font-family:{FF}!important; font-size:12px!important; font-weight:500!important;
  padding:6px 16px!important; box-shadow:none!important; transition:all .15s!important}}
.stButton>button:hover{{border-color:{B5}!important; color:{B5}!important; background:{C3}!important}}
</style>
""", unsafe_allow_html=True)
 
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
    p = (d/prev*100) if prev else 0.0
    return d, p
 
def sparkline(df, ind, color=BLUE, days=60, w=72, h=26):
    s = ser_h(df, ind, days)
    vals = s["value"].dropna().tolist() if not s.empty else []
    if len(vals) < 3: return ""
    mn, mx = min(vals), max(vals); mg = 2
    if mn == mx:
        pts = [(round(i*w/(len(vals)-1), 1), h/2) for i in range(len(vals))]
    else:
        pts = [(round(i*w/(len(vals)-1), 1),
                round(h-mg-(v-mn)/(mx-mn)*(h-mg*2), 1)) for i, v in enumerate(vals)]
    ld = "M " + " L ".join(f"{x},{y}" for x, y in pts)
    fd = ld + f" L {pts[-1][0]},{h} L {pts[0][0]},{h} Z"
    gid = "g" + re.sub(r'\W','', ind)[:8]
    lx, ly = pts[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="display:block">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity=".3"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity=".02"/>'
            f'</linearGradient></defs>'
            f'<path d="{fd}" fill="url(#{gid})"/>'
            f'<path d="{ld}" fill="none" stroke="{color}" stroke-width="1.5"'
            f' stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{lx}" cy="{ly}" r="2.2" fill="{color}"/></svg>')
 
# ════════════════════════════════════════════════════════════════
# 헤더
# ════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="padding:18px 0 14px;border-bottom:1px solid {BORD};margin-bottom:1.2rem">
  <div style="font-size:28px;font-weight:800;font-style:italic;line-height:1.2;margin-bottom:4px">
    <span style="background:rgba(56,139,253,.22);padding:2px 10px;border-radius:6px">
      DY Monitoring
    </span>
  </div>
  <div style="font-size:11px;color:{MUT};font-family:'JetBrains Mono',monospace">
    한미 매크로 · 투자자산 · 가계부 · 이슈 종합 대시보드
    &nbsp;·&nbsp; 매일 KST 07:00 자동수집
  </div>
</div>
""", unsafe_allow_html=True)
 
# ════════════════════════════════════════════════════════════════
# KPI 7개 — 파란색 통일 + 미니 스파크차트
# ════════════════════════════════════════════════════════════════
KPI_ITEMS = [
    ("S&P500",  "SPX",     market, ",.0f"),
    ("NASDAQ",  "NASDAQ",  market, ",.0f"),
    ("KOSPI",   "KOSPI",   market, ",.0f"),
    ("KOSDAQ",  "KOSDAQ",  market, ",.0f"),
    ("VIX",     "VIX",     market, ".1f"),
    ("USD/KRW", "USDKRW",  market, ",.0f"),
    ("US 10Y",  "US_10Y",  fred,   ".2f"),
]
 
kpi_cols = st.columns(7)
for col, (lbl, ind, df_, fmt) in zip(kpi_cols, KPI_ITEMS):
    r = lat(df_, ind); d, p = dlt_info(df_, ind)
    spk = sparkline(df_, ind, color=BLUE)
    with col:
        if r is not None:
            vs  = format(r["value"], fmt)
            sym = "▲" if p >= 0 else "▼"
            st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-left:3px solid {BLUE};
  border-radius:8px;padding:10px 12px 8px">
  <div style="font-size:9px;color:{MUT};text-transform:uppercase;
    letter-spacing:.06em;margin-bottom:3px">{lbl}</div>
  <div style="font-size:17px;font-weight:700;color:{TXT};
    font-family:'JetBrains Mono',monospace;line-height:1.1">{vs}</div>
  <div style="font-size:9px;color:{BLUE};font-weight:600;margin:3px 0;
    font-family:'JetBrains Mono',monospace">{sym}{abs(p):.2f}%</div>
  <div style="margin-top:4px">{spk}</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-left:3px solid {BORD};
  border-radius:8px;padding:10px 12px 8px;opacity:.5">
  <div style="font-size:9px;color:{MUT};text-transform:uppercase;
    letter-spacing:.06em;margin-bottom:3px">{lbl}</div>
  <div style="font-size:17px;font-weight:700;color:{MUT}">—</div>
</div>""", unsafe_allow_html=True)
 
st.markdown(f'<div style="height:.8rem"></div>', unsafe_allow_html=True)
 
# ════════════════════════════════════════════════════════════════
# 브리핑 — 저장된 JSON + 실시간 새로고침 버튼
# ════════════════════════════════════════════════════════════════
BRIEF_FILE = DATA_DIR / "daily_briefing.json"
 
def load_brief():
    if BRIEF_FILE.exists():
        with open(BRIEF_FILE, encoding="utf-8") as f:
            return json.load(f)
    return None
 
def save_brief(data):
    DATA_DIR.mkdir(exist_ok=True)
    with open(BRIEF_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
 
def build_prompt():
    """현재 데이터를 기반으로 상세 브리핑 프롬프트 생성"""
    prices    = load_pq("portfolio_prices.parquet")
    portfolio = load_json("portfolio.json", [])
    news_data = load_json("portfolio_news.json", {})
 
    # 시장 지표
    mkt_lines = []
    for ind, lbl in [("SPX","S&P500"),("NASDAQ","NASDAQ"),("KOSPI","KOSPI"),
                     ("KOSDAQ","KOSDAQ"),("VIX","VIX"),("USDKRW","USD/KRW"),("US_10Y","미국10Y금리")]:
        r = lat(market if "10Y" not in ind and ind not in ("FFR",) else fred, ind)
        if r:
            _, p = dlt_info(market if ind not in ("US_10Y","HY_OAS") else fred, ind)
            sym = "▲" if p>=0 else "▼"
            mkt_lines.append(f"  {lbl}: {r['value']:,.2f} ({sym}{abs(p):.2f}%)")
 
    # 보유 종목
    fx_row = lat(market, "USDKRW"); fx = float(fx_row["value"]) if fx_row else 1380
    hold_lines = []; tv = 0; tp = 0
    for it in portfolio:
        lots = it.get("lots", []); ticker = it.get("ticker", "")
        if not lots or not ticker: continue
        qty  = sum(l["qty"]         for l in lots)
        cost = sum(l["qty"]*l["price"] for l in lots)
        avg  = cost/qty if qty>0 else 0
        sub  = prices[prices["ticker"]==ticker].sort_values("date") if not prices.empty else pd.DataFrame()
        if sub.empty: continue
        cur  = float(sub.iloc[-1]["close"])
        prev = float(sub.iloc[-2]["close"]) if len(sub)>=2 else cur
        fxv  = fx if it.get("currency")=="USD" else 1
        val  = cur*qty*fxv; pnl=(cur-avg)*qty*fxv; dpct=(cur/prev-1)*100 if prev else 0
        tv  += val; tp += pnl
        sym  = "▲" if dpct>=0 else "▼"
        hold_lines.append(f"  {it['name']}({it.get('sector','')}) "
                          f"현재:{cur:,.2f} 일간:{sym}{abs(dpct):.2f}% "
                          f"수익률:{(cur/avg-1)*100:+.2f}% 평가:{val:,.0f}원")
    pf_sum = (f"  포트폴리오 총평가:{tv:,.0f}원  누적손익:{tp:+,.0f}원 "
              f"({tp/(tv-tp)*100:+.2f}%)") if tv>0 else "  (보유 종목 데이터 없음)"
 
    # 주요 뉴스 (점수 8↑ 또는 2↓)
    news_lines = []
    for cat in ("stocks","sectors"):
        for key, arts in news_data.get(cat,{}).items():
            for n in arts:
                sc = n.get("score")
                if sc is not None and (sc>=8 or sc<=2):
                    tag = "호재" if sc>=6 else "악재"
                    news_lines.append(f"  [{tag}{sc}] {key}: "
                                      f"{n.get('ai_summary') or n.get('title','')[:55]}")
    news_str = "\n".join(news_lines[:8]) if news_lines else "  (뉴스 없음)"
 
    today = now.strftime("%Y-%m-%d %H:%M")
    return f"""한국 retail 투자자를 위한 실시간 투자 브리핑을 작성하세요.
 
[{today} 기준]
 
▣ 글로벌 시장 지표
{chr(10).join(mkt_lines) or "  (데이터 없음)"}
 
▣ 보유 종목 현황
{chr(10).join(hold_lines) or "  (데이터 없음)"}
{pf_sum}
 
▣ AI 점수 주요 뉴스
{news_str}
 
다음 JSON만 반환 (다른 텍스트 금지):
{{"headline":"오늘 핵심 1줄(25자이내)",
  "market":"시장 분석 — 지수·등락률·원인 구체적으로 2-3문장",
  "holdings":"보유 종목 분석 — 상승/하락 종목과 이유 2-3문장",
  "sectors":"보유 섹터(반도체·방산·증권 등) 흐름 1-2문장",
  "news":"주목 뉴스 및 영향 1-2문장",
  "action":"투자 액션 코멘트 1문장(관망/매수/비중조절 등)",
  "mood":"positive 또는 neutral 또는 cautious"}}"""
 
def gen_brief_realtime(api_key):
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key.strip())
        prompt = build_prompt()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=900,
            messages=[{"role":"user","content":prompt}])
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
 
# 브리핑 표시
brief = load_brief()
BRIEF_KEY = "home_brief"
if BRIEF_KEY in st.session_state:
    brief = st.session_state[BRIEF_KEY]
 
# 브리핑 UI
bc1, bc2 = st.columns([5,1])
with bc1:
    st.markdown(f"""
<div style="font-size:16px;font-weight:700;color:{TXT};margin-bottom:.5rem">
  📡 오늘의 브리핑
</div>""", unsafe_allow_html=True)
with bc2:
    if st.button("🔄 지금 생성", key="brief_refresh", use_container_width=True):
        api_key = get_secret("ANTHROPIC_API_KEY")
        if not api_key or api_key.startswith("*"):
            st.warning("Streamlit Secrets에 ANTHROPIC_API_KEY를 등록하세요.")
        else:
            with st.spinner("Claude가 브리핑 생성 중…"):
                new_brief = gen_brief_realtime(api_key)
                if new_brief:
                    st.session_state[BRIEF_KEY] = new_brief
                    save_brief(new_brief)
                    brief = new_brief
                    st.rerun()
 
if brief:
    mood_style = {
        "positive": (B5,  "rgba(56,139,253,.15)"),
        "neutral":  (SUB, C2),
        "cautious": (B7,  "rgba(31,111,235,.15)"),
    }
    mc, mbg = mood_style.get(brief.get("mood","neutral"), (SUB,C2))
    gen_t   = brief.get("generated_at","")
    is_rt   = brief.get("realtime", False)
    rt_badge = (f'<span style="background:rgba(56,139,253,.2);color:{B5};'
                f'padding:2px 8px;border-radius:10px;font-size:9px;'
                f'font-weight:600;font-family:JetBrains Mono">실시간</span>') if is_rt else ""
 
    st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-left:4px solid {mc};
  border-radius:10px;padding:18px 22px;margin-bottom:1rem">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <div style="display:flex;align-items:center;gap:8px">
      <span style="background:{mbg};color:{mc};padding:3px 10px;border-radius:10px;
        font-size:9px;font-weight:700;font-family:'JetBrains Mono',monospace">
        {brief.get('mood','').upper()}
      </span>
      {rt_badge}
    </div>
    <span style="font-size:9px;color:{MUT};font-family:'JetBrains Mono',monospace">
      {gen_t} 생성
    </span>
  </div>
  <div style="font-size:19px;font-weight:700;color:{TXT};margin-bottom:12px;line-height:1.3">
    {brief.get('headline','')}
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">
    <div style="background:{C2};border-radius:7px;padding:11px 14px">
      <div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px">📊 시장</div>
      <div style="font-size:12px;color:{TXT};line-height:1.6">{brief.get('market','')}</div>
    </div>
    <div style="background:{C2};border-radius:7px;padding:11px 14px">
      <div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px">💼 보유 종목</div>
      <div style="font-size:12px;color:{TXT};line-height:1.6">{brief.get('holdings','')}</div>
    </div>
    <div style="background:{C2};border-radius:7px;padding:11px 14px">
      <div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px">🏭 섹터</div>
      <div style="font-size:12px;color:{TXT};line-height:1.6">{brief.get('sectors','')}</div>
    </div>
    <div style="background:{C2};border-radius:7px;padding:11px 14px">
      <div style="font-size:9px;color:{MUT};text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px">📰 뉴스</div>
      <div style="font-size:12px;color:{TXT};line-height:1.6">{brief.get('news','')}</div>
    </div>
  </div>
  <div style="background:rgba(56,139,253,.08);border:1px solid rgba(56,139,253,.2);
    border-radius:7px;padding:11px 14px;font-size:12px;color:{BLUE};font-weight:600">
    💬 {brief.get('action','')}
  </div>
</div>""", unsafe_allow_html=True)
else:
    st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;
  padding:30px;text-align:center;margin-bottom:1rem">
  <div style="font-size:14px;color:{SUB}">브리핑 없음 — 우측 상단 🔄 버튼으로 생성하거나 Actions를 실행하세요</div>
</div>""", unsafe_allow_html=True)
 
# ════════════════════════════════════════════════════════════════
# 보유 종목 차트
# ════════════════════════════════════════════════════════════════
portfolio = load_json("portfolio.json", [])
prices_df = load_pq("portfolio_prices.parquet")
 
@st.cache_data(ttl=300)
def fetch_intraday_yf(ticker, currency):
    """yfinance로 실시간 가격 데이터 (US: 1d/5m, KR: 5d/1d)"""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        if currency == "USD":
            hist = t.history(period="1d", interval="5m")
        else:
            hist = t.history(period="7d", interval="1h")
        if hist.empty:
            return pd.DataFrame()
        hist.index = pd.to_datetime(hist.index)
        return hist.reset_index()[["Datetime","Close"]].rename(
            columns={"Datetime":"date","Close":"close"})
    except:
        return pd.DataFrame()
 
def get_price_series(item):
    """종목 가격 시계열 반환 (yfinance 우선 → parquet 폴백)"""
    ticker   = item.get("ticker","")
    currency = item.get("currency","KRW")
    # yfinance 시도
    df = fetch_intraday_yf(ticker, currency)
    if not df.empty:
        df["source"] = "realtime"
        return df
    # parquet 폴백 (최근 30일 일별)
    if not prices_df.empty:
        sub = prices_df[prices_df["ticker"]==ticker].sort_values("date").tail(30).copy()
        if not sub.empty:
            sub["source"] = "daily"
            return sub[["date","close"]].rename(columns={"date":"date","close":"close"})
    return pd.DataFrame()
 
if portfolio:
    st.markdown(f"""
<div style="font-size:16px;font-weight:700;color:{TXT};margin-bottom:.6rem">
  📈 보유 종목 현황
</div>""", unsafe_allow_html=True)
 
    fx_row = lat(market,"USDKRW"); fx = float(fx_row["value"]) if fx_row else 1380
    items_with_lots = [p for p in portfolio if p.get("lots")]
    ncols = min(3, len(items_with_lots))
    if ncols > 0:
        chart_cols = st.columns(ncols)
        for i, item in enumerate(items_with_lots):
            col = chart_cols[i % ncols]
            ticker   = item.get("ticker","")
            currency = item.get("currency","KRW")
            name     = item.get("name","")
            lots     = item.get("lots",[])
            qty      = sum(l["qty"]           for l in lots)
            cost     = sum(l["qty"]*l["price"] for l in lots)
            avg      = cost/qty if qty>0 else 0
            fxv      = fx if currency=="USD" else 1
 
            df_p = get_price_series(item)
            source = ""
            cur_price = None
            if not df_p.empty:
                cur_price = float(df_p["close"].iloc[-1])
                source    = df_p.get("source", pd.Series(["daily"])).iloc[-1] if "source" in df_p.columns else "daily"
 
            daily_pct  = 0.0
            if not df_p.empty and len(df_p) >= 2:
                prev = float(df_p["close"].iloc[-2])
                daily_pct = (cur_price/prev-1)*100 if prev and cur_price else 0.0
 
            pnl_pct = (cur_price/avg-1)*100 if (avg>0 and cur_price) else 0.0
            val_krw = cur_price*qty*fxv if cur_price else 0
 
            clr_daily = UP if daily_pct>=0 else DN
            clr_pnl   = UP if pnl_pct>=0   else DN
            src_label = "실시간" if source=="realtime" else "일별"
            now_str   = now.strftime("%H:%M")
 
            with col:
                with st.container():
                    # 종목 헤더
                    st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;padding:12px 14px 0;margin-bottom:-1px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
    <div>
      <div style="font-size:13px;font-weight:700;color:{TXT}">{name}</div>
      <div style="font-size:9px;color:{MUT};font-family:'JetBrains Mono',monospace">{ticker}</div>
    </div>
    <div style="text-align:right">
      <div style="font-size:14px;font-weight:700;color:{TXT};font-family:'JetBrains Mono',monospace">
        {f"{cur_price:,.2f}" if cur_price else "—"}
        <span style="font-size:9px;color:{MUT}">{currency}</span>
      </div>
      <div style="font-size:9px;color:{clr_daily};font-weight:600;font-family:'JetBrains Mono',monospace">
        {"▲" if daily_pct>=0 else "▼"}{abs(daily_pct):.2f}% 일간
      </div>
    </div>
  </div>
  <div style="display:flex;gap:12px;margin-bottom:6px;font-size:10px;font-family:'JetBrains Mono',monospace">
    <span style="color:{MUT}">수량 <b style="color:{TXT}">{qty:,.0f}</b></span>
    <span style="color:{MUT}">평단 <b style="color:{TXT}">{avg:,.2f}</b></span>
    <span style="color:{clr_pnl}">수익률 <b>{"▲" if pnl_pct>=0 else "▼"}{abs(pnl_pct):.2f}%</b></span>
    <span style="color:{MUT}">평가 <b style="color:{TXT}">{val_krw/1e6:.1f}백만</b>원</span>
  </div>
</div>""", unsafe_allow_html=True)
 
                    # 차트
                    if not df_p.empty and len(df_p) >= 3:
                        x_col = "date"
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=df_p[x_col], y=df_p["close"],
                            line=dict(color=BLUE, width=2),
                            fill="tozeroy",
                            fillcolor="rgba(56,139,253,.08)",
                            hovertemplate=f"<b>{name}</b> %{{y:,.2f}}<extra></extra>"))
                        if avg > 0:
                            fig.add_hline(y=avg, line_dash="dot", line_color=GOLD, line_width=1,
                                annotation_text=f"평단 {avg:,.2f}",
                                annotation_font_color=GOLD, annotation_font_size=9)
                        yr = [df_p["close"].min()*0.99, df_p["close"].max()*1.01]
                        fig.update_layout(
                            paper_bgcolor=CARD, plot_bgcolor=CARD,
                            height=180, margin=dict(l=0,r=0,t=0,b=0),
                            showlegend=False,
                            hovermode="x unified",
                            hoverlabel=dict(bgcolor=C2,bordercolor=BORD,
                                font=dict(family="JetBrains Mono",size=10,color=TXT)),
                            xaxis=dict(showgrid=False, zeroline=False, showline=False,
                                tickfont=dict(size=8,color=MUT), showticklabels=True),
                            yaxis=dict(showgrid=True, gridcolor=G, zeroline=False,
                                showline=False, tickfont=dict(size=8,color=MUT),
                                range=yr, side="right"))
                        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
                    else:
                        st.markdown(f"""
<div style="background:{C2};border-radius:0 0 10px 10px;height:100px;
  display:flex;align-items:center;justify-content:center;
  font-size:10px;color:{MUT}">가격 데이터 수집 후 표시됩니다</div>""",
                            unsafe_allow_html=True)
 
                    # 타임스탬프
                    st.markdown(f"""
<div style="background:{C2};border-radius:0 0 10px 10px;padding:5px 14px;
  font-size:9px;color:{MUT};font-family:'JetBrains Mono',monospace;
  border:1px solid {BORD};border-top:none">
  {src_label} · {now.strftime("%Y-%m-%d %H:%M")} 기준
</div>""", unsafe_allow_html=True)
 
            # 행 구분 (3개마다)
            if (i+1) % ncols == 0 and (i+1) < len(items_with_lots):
                st.markdown(f'<div style="height:.6rem"></div>', unsafe_allow_html=True)
                chart_cols = st.columns(ncols)
 
# ════════════════════════════════════════════════════════════════
# 주간 리포트 (있을 경우)
# ════════════════════════════════════════════════════════════════
weekly = load_json("weekly_report.json", None)
if weekly and isinstance(weekly, dict) and weekly.get("headline"):
    grade = weekly.get("grade","B")
    grade_color = {
        "S":UP, "A":B5, "B":BLUE, "C":SUB, "D":DN
    }.get(grade, SUB)
    st.markdown(f"""
<div style="height:.6rem"></div>
<details style="background:{CARD};border:1px solid {BORD};border-radius:10px;
  padding:14px 18px;cursor:pointer">
  <summary style="font-size:13px;font-weight:700;color:{TXT};list-style:none;
    display:flex;align-items:center;gap:8px">
    📊 주간 리포트
    <span style="background:rgba(56,139,253,.15);color:{grade_color};
      padding:2px 9px;border-radius:10px;font-size:10px;font-weight:700">
      {grade}
    </span>
    <span style="font-size:12px;color:{TXT};font-weight:600">{weekly.get('headline','')}</span>
    <span style="font-size:9px;color:{MUT};margin-left:auto;font-family:'JetBrains Mono',monospace">
      {weekly.get('week_range','')} · {weekly.get('generated_at','')} 생성
    </span>
  </summary>
  <div style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:8px">
    <div style="background:{C2};border-radius:7px;padding:10px 13px">
      <div style="font-size:9px;color:{MUT};margin-bottom:4px">성과</div>
      <div style="font-size:11px;color:{TXT};line-height:1.6">{weekly.get('performance','')}</div>
    </div>
    <div style="background:{C2};border-radius:7px;padding:10px 13px">
      <div style="font-size:9px;color:{MUT};margin-bottom:4px">시장 환경</div>
      <div style="font-size:11px;color:{TXT};line-height:1.6">{weekly.get('market_context','')}</div>
    </div>
    <div style="background:{C2};border-radius:7px;padding:10px 13px">
      <div style="font-size:9px;color:{MUT};margin-bottom:4px">교훈</div>
      <div style="font-size:11px;color:{TXT};line-height:1.6">{weekly.get('lessons','')}</div>
    </div>
    <div style="background:{C2};border-radius:7px;padding:10px 13px">
      <div style="font-size:9px;color:{MUT};margin-bottom:4px">다음 주 주목</div>
      <div style="font-size:11px;color:{TXT};line-height:1.6">{weekly.get('next_week','')}</div>
    </div>
  </div>
</details>""", unsafe_allow_html=True)
 
# ════════════════════════════════════════════════════════════════
# 푸터 (네비게이션 카드 제거 — 사이드바 메뉴 활용)
# ════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="margin-top:2rem;padding:10px 16px;background:{C2};border:1px solid {BORD};
  border-radius:8px;font-size:10px;color:{MUT};font-family:'JetBrains Mono',monospace;
  display:flex;justify-content:space-between;align-items:center">
  <span>📅 매일 KST 07:00 자동수집 · FRED · yfinance · CNN F&amp;G · ECOS · 네이버 뉴스 · DART</span>
  <span>{now.strftime("%Y-%m-%d %H:%M")} KST</span>
</div>
""", unsafe_allow_html=True)
