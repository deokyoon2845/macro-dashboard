"""
2. 투자자산 — 계좌별 관리 + 블루/레드 팔레트 + 스티키 네비
포트폴리오 대시보드, 계좌별 성과, 뉴스/공시 및 리스크 지표 트래킹
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime, date
import json, uuid, base64, sys

# ════════════════════════════════════════════════════════════════
# 1. 초기 설정 및 환경 구성
# ════════════════════════════════════════════════════════════════
st.set_page_config(page_title="투자자산", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    from utils import render_sticky_nav
    render_sticky_nav()
except Exception:
    pass

DATA = _ROOT / "data"
ASSET_DIR = _ROOT / "assets"

PORT_FILE   = DATA / "portfolio.json"
PRICE_FILE  = DATA / "portfolio_prices.parquet"
MARKET_FILE = DATA / "market_prices.parquet"
NEWS_FILE   = DATA / "portfolio_news.json"
DISC_FILE   = DATA / "portfolio_disclosures.json"

# ════════════════════════════════════════════════════════════════
# 2. 디자인 시스템 및 상수
# ════════════════════════════════════════════════════════════════
BG = "#0A0D13"; CARD = "#111620"; C2 = "#161C28"; C3 = "#1C2438"
BORD = "#222A3A"; G = "#181F2C"; TXT = "#E4EAF6"; SUB = "#7A8CA4"; MUT = "#4A5668"
ACC = "#388BFD"; UP = "#E24B4A"; DN = "#388BFD" # 한국 증시 관례 (상승=빨강, 하락=파랑)
B3 = "#79C0FF"; B5 = "#388BFD"; B6 = "#2F81F7"; B7 = "#1F6FEB"

HOLD_COLORS = ["#388BFD","#79C0FF","#1F6FEB","#58A6FF","#CAE8FF","#2F81F7",
               "#4A82E4","#9ECEFF","#1158C7","#56D3FF","#0D6EFD","#B0D9FF"]

ACCT_COLORS = {"일반":"#388BFD", "DC":"#79C0FF", "연금저축":"#1F6FEB"}
ACCT_LABELS = {"일반":"💳 일반 종합매매", "DC":"🏢 퇴직연금 DC", "연금저축":"🏦 연금저축펀드"}
ALL_ACCOUNTS = ["일반", "DC", "연금저축"]

SECTORS = ["반도체","방산","증권·금융","우주항공","로봇·자동화","2차전지","바이오",
           "IT·소프트웨어","엔터·미디어","자동차","화학","철강·소재","건설","유틸리티","소비재","미용","에너지","기타"]
MARKETS = ["KOSPI","KOSDAQ","NYSE","NASDAQ","기타"]

# ════════════════════════════════════════════════════════════════
# 3. 데이터 로드 및 안전 장치가 강화된 비즈니스 로직
# ════════════════════════════════════════════════════════════════
def load_custom_font():
    fmt_map = {".woff2":"woff2",".woff":"woff",".ttf":"truetype",".otf":"opentype"}
    for ext, fmt in fmt_map.items():
        fps = sorted(ASSET_DIR.glob(f"*{ext}"))
        if not fps: continue
        fp = fps[0]
        try:
            with open(fp,"rb") as f: b64=base64.b64encode(f.read()).decode()
            return fp.stem, f"@font-face{{font-family:'{fp.stem}';src:url('data:font/{fmt};base64,{b64}') format('{fmt}');}}"
        except Exception: continue
    return None, ""

CUSTOM_FONT, FONT_FACE_CSS = load_custom_font()
FF = f"'{CUSTOM_FONT}',sans-serif" if CUSTOM_FONT else "'Inter','Gowun Batang',sans-serif"

def load_portfolio():
    if PORT_FILE.exists():
        try:
            with open(PORT_FILE, encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_portfolio(data):
    DATA.mkdir(exist_ok=True)
    with open(PORT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path, default):
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f: return json.load(f)
        except Exception: return default
    return default

@st.cache_data(ttl=600)
def load_parquet(path):
    if path.exists():
        try:
            df = pd.read_parquet(path)
            if not df.empty and "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            return df
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def get_usdkrw(mdf):
    if mdf.empty or "indicator" not in mdf.columns: return 1380.0
    s = mdf[mdf["indicator"]=="USDKRW"].sort_values("date")
    return float(s.iloc[-1]["value"]) if not s.empty else 1380.0

def get_px(ticker, prices):
    if prices.empty: return None, None
    sub = prices[prices["ticker"]==ticker].sort_values("date")
    if sub.empty: return None, None
    return float(sub.iloc[-1]["close"]), (float(sub.iloc[-2]["close"]) if len(sub)>=2 else None)

def compute_pos(item, prices, usdkrw):
    if not isinstance(item, dict): return None
    lots = item.get("lots", [])
    ticker = item.get("ticker", "")
    if not lots or not ticker: return None
    
    valid_lots = [l for l in lots if isinstance(l, dict)]
    if not valid_lots: return None

    qty = sum(l.get("qty", 0) for l in valid_lots)
    cost = sum(l.get("qty", 0) * l.get("price", 0) for l in valid_lots)
    avg = cost / qty if qty > 0 else 0
    cur, prev = get_px(ticker, prices)
    
    is_usd = item.get("currency", "KRW") == "USD"
    fx = usdkrw if is_usd else 1
    
    base = {
        "name": item.get("name", "미지정"), "ticker": ticker, "sector": item.get("sector", "기타"),
        "market": item.get("market", "기타"), "currency": item.get("currency", "KRW"),
        "account": item.get("account", "일반"), "qty": qty, "avg_cost": avg, 
        "id": item.get("id", ""), "lots": valid_lots
    }
    
    if cur is None:
        return {**base, "current": None, "value_krw": 0, "cost_krw": cost*fx,
                "pnl_krw": 0, "pnl_pct": 0, "daily_pct": 0, "daily_pnl_krw": 0}
        
    val = cur * qty * fx
    pnl = (cur - avg) * qty * fx
    pnl_pct = (cur / avg - 1) * 100 if avg > 0 else 0
    daily_pct = (cur / prev - 1) * 100 if prev and prev > 0 else 0
    daily_pnl = (cur - prev) * qty * fx if prev else 0
    
    return {**base, "current": cur, "value_krw": val, "cost_krw": cost*fx,
            "pnl_krw": pnl, "pnl_pct": pnl_pct, "daily_pct": daily_pct, "daily_pnl_krw": daily_pnl}

def compute_daily_pf(pf_list, prices, mdf):
    if prices.empty or not pf_list: return pd.DataFrame()
    all_dates = sorted(prices["date"].dropna().unique())
    fx_df = pd.DataFrame()
    
    if not mdf.empty and "indicator" in mdf.columns:
        fxs = mdf[mdf["indicator"]=="USDKRW"][["date","value"]].copy()
        if not fxs.empty: fx_df = fxs.rename(columns={"value":"fx"})
        
    rows = []
    for d in all_dates:
        tv, tc, any_pos = 0, 0, False
        fx_now = float(fx_df[fx_df["date"]<=d].sort_values("date").iloc[-1]["fx"]) if not fx_df.empty and not fx_df[fx_df["date"]<=d].empty else 1380.0
        
        for it in pf_list:
            if not isinstance(it, dict): continue
            lots = it.get("lots", [])
            qty = sum(l.get("qty", 0) for l in lots if isinstance(l, dict) and pd.Timestamp(l.get("date")) <= d)
            cost = sum(l.get("qty", 0) * l.get("price", 0) for l in lots if isinstance(l, dict) and pd.Timestamp(l.get("date")) <= d)
            if qty <= 0: continue
            
            any_pos = True
            ps = prices[(prices["ticker"]==it.get("ticker")) & (prices["date"]<=d)].sort_values("date")
            if ps.empty: continue
            
            fxv = fx_now if it.get("currency", "KRW") == "USD" else 1
            tv += qty * float(ps.iloc[-1]["close"]) * fxv
            tc += cost * fxv
            
        if any_pos:
            rows.append({"date": d, "value": tv, "cost": tc, "pnl_pct": (tv/tc-1)*100 if tc > 0 else 0})
            
    return pd.DataFrame(rows)

def filter_hist(hist_df, rng):
    if hist_df.empty: return hist_df
    cutoffs = {"1W":7, "1M":30, "3M":90, "6M":180, "1Y":365, "YTD":None, "ALL":None}
    days = cutoffs.get(rng)
    if days: return hist_df[hist_df["date"] >= pd.Timestamp.now() - pd.Timedelta(days=days)]
    if rng == "YTD": return hist_df[hist_df["date"] >= pd.Timestamp(datetime.now().year, 1, 1)]
    return hist_df

# ── 리스크 계산 통계 함수 ────────────────────────────────────
def get_ret(ticker, prices, days=None):
    sub = prices[prices["ticker"]==ticker].sort_values("date")
    if days: sub = sub.tail(days+1)
    return sub["close"].pct_change().dropna()

def calc_beta(ticker, is_usd, prices, mdf, days=90):
    stock_ret = get_ret(ticker, prices, days)
    if len(stock_ret) < 20: return None
    bench_ind = "SPX" if is_usd else "KOSPI"
    if mdf.empty or "indicator" not in mdf.columns: return None
    bench = mdf[mdf["indicator"]==bench_ind].sort_values("date")
    if bench.empty: return None
    
    bench_ret = bench.set_index("date")["value"].pct_change().dropna()
    common = stock_ret.index.intersection(bench_ret.index)
    if len(common) < 20: return None
    
    s = stock_ret[common].values
    b = bench_ret[common].values
    var_b = np.var(b)
    return round(float(np.cov(s,b)[0,1]/var_b), 2) if var_b != 0 else None

def calc_vol(ticker, prices, days=60):
    ret = get_ret(ticker, prices, days)
    return round(float(ret.std()*np.sqrt(252)*100), 2) if len(ret) >= 10 else None

def calc_mdd(ticker, prices):
    sub = prices[prices["ticker"]==ticker].sort_values("date")["close"]
    if len(sub) < 5: return None
    dd = (sub - sub.cummax()) / sub.cummax() * 100
    return round(float(dd.min()), 2)

def calc_sharpe(ticker, prices, rf=3.5, days=90):
    ret = get_ret(ticker, prices, days)
    if len(ret) < 20: return None
    ann = float(ret.mean() * 252 * 100)
    vol = float(ret.std() * np.sqrt(252) * 100)
    return round((ann - rf) / vol, 2) if vol > 0 else None

def get_badge_html(v, thresholds, fmt, reverse=False):
    if v is None: return f'<span style="color:{MUT}">—</span>'
    lo, hi = thresholds
    clr = (UP if v < lo else (SUB if v < hi else DN)) if reverse else (DN if v < lo else (SUB if v < hi else UP))
    return f'<span style="color:{clr};font-weight:700;font-family:JetBrains Mono,monospace">{fmt.format(v)}</span>'

# ════════════════════════════════════════════════════════════════
# 4. UI 및 렌더링 컴포넌트 함수
# ════════════════════════════════════════════════════════════════
def render_css():
    st.markdown(
        FONT_FACE_CSS +
        """<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Gowun+Batang:wght@400;700&display=swap" rel="stylesheet">""" +
        f"""<style>
        html,body,[class*="css"] {{background-color:{BG}!important;color:{TXT}!important;font-family:{FF}!important;letter-spacing:-.01em!important}}
        .block-container {{padding:0 1.5rem 2rem!important;max-width:100%!important;background:transparent!important}}
        [data-testid="stAppViewContainer"] {{background-color:{BG}!important}}
        [data-testid="stSidebar"] {{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
        #MainMenu,footer,header {{visibility:hidden}}
        p,span,div,label,th,td {{color:{TXT}!important;letter-spacing:-.01em!important}}
        .stButton>button {{background:{C2}!important;color:{TXT}!important;border:1px solid {BORD}!important;border-radius:6px!important;font-family:{FF}!important;font-size:12px!important;padding:5px 14px!important;font-weight:500!important;box-shadow:none!important}}
        .stButton>button:hover {{background:{C3}!important;border-color:{B5}!important;color:{B5}!important}}
        [data-testid="stRadio"]>div {{gap:2px!important;flex-direction:row!important}}
        [data-testid="stRadio"]>div>label {{background:{C2}!important;color:{SUB}!important;border:1px solid {BORD}!important;border-radius:6px!important;padding:6px 14px!important;font-size:11px!important;font-family:{FF}!important;font-weight:500!important;cursor:pointer!important}}
        [data-testid="stRadio"]>div>label[data-selected="true"] {{background:{B5}!important;color:#FFFFFF!important;border-color:{B5}!important}}
        .js-plotly-plot {{border-radius:10px!important}}
        .stTabs [data-baseweb="tab-list"] {{background:{CARD}!important;border-bottom:1px solid {BORD}!important;gap:0}}
        .stTabs [data-baseweb="tab"] {{background:transparent!important;color:{SUB}!important;font-family:{FF}!important;font-size:12px!important;font-weight:500!important;border-bottom:2px solid transparent!important;padding:10px 20px!important}}
        .stTabs [aria-selected="true"] {{color:{TXT}!important;border-bottom-color:{B5}!important}}
        .stTabs [data-baseweb="tab-panel"] {{background:transparent!important;padding:0!important}}
        </style>""", unsafe_allow_html=True)

def render_sidebar_helper():
    _s = f"position:fixed;top:10px;left:8px;z-index:99999;background:{CARD};border:2px solid {B5};border-radius:10px;padding:8px 13px;cursor:pointer;font-size:14px;font-weight:700;color:{B5};box-shadow:0 2px 12px rgba(56,139,253,.4);display:flex;align-items:center;gap:5px;opacity:0;pointer-events:none;transition:opacity .2s"
    _oc = "document.querySelector('[data-testid=collapsedControl]')?.click()"
    _js = "(function(){function r(){var c=document.querySelector('[data-testid=\"collapsedControl\"]');var b=document.getElementById('pf-sb-btn');if(!b)return;b.style.opacity=c?'1':'0';b.style.pointerEvents=c?'auto':'none';}new MutationObserver(r).observe(document.body,{childList:true,subtree:true});setTimeout(r,400);})();"
    st.markdown(f'<div id="pf-sb-btn" style="{_s}" onclick="{_oc}">☰ 메뉴</div><script>{_js}</script>', unsafe_allow_html=True)

def render_management_form(portfolio):
    with st.expander("⚙️ 종목 관리"):
        manage_mode = st.selectbox("작업", ["신규 종목 등록", "매수 기록 추가", "종목 삭제"], label_visibility="collapsed")

        if manage_mode == "신규 종목 등록":
            with st.form("nf", clear_on_submit=True):
                n_name = st.text_input("종목명*")
                n_ticker = st.text_input("티커*", placeholder="005930.KS")
                n_acct = st.selectbox("계좌", ALL_ACCOUNTS)
                n_currency = st.selectbox("통화", ["KRW", "USD"])
                
                c1, c2 = st.columns(2)
                with c1: n_sector = st.selectbox("섹터", SECTORS)
                with c2: n_market = st.selectbox("시장", MARKETS)
                
                c3, c4, c5 = st.columns(3)
                with c3: n_date = st.date_input("첫 매수일", date.today())
                with c4: n_qty = st.number_input("수량", min_value=0.0, step=1.0)
                with c5: n_price = st.number_input("매수가", min_value=0.0, step=100.0)
                
                if st.form_submit_button("등록", type="primary") and n_name and n_ticker:
                    new = {"id": str(uuid.uuid4())[:8], "name": n_name, "ticker": n_ticker, "sector": n_sector, "market": n_market, "currency": n_currency, "account": n_acct, "lots": []}
                    if n_qty > 0 and n_price > 0:
                        new["lots"].append({"date": str(n_date), "qty": n_qty, "price": n_price, "type": "buy"})
                    portfolio.append(new)
                    save_portfolio(portfolio)
                    st.cache_data.clear(); st.success("등록 완료!"); st.rerun()

        elif manage_mode == "매수 기록 추가" and portfolio:
            with st.form("af", clear_on_submit=True):
                opts = {f"{p['name']} [{p.get('account','일반')}]": p["id"] for p in portfolio if isinstance(p, dict)}
                if opts:
                    sel = st.selectbox("종목", list(opts.keys()))
                    c1, c2, c3 = st.columns(3)
                    with c1: a_date = st.date_input("매수일", date.today())
                    with c2: a_qty = st.number_input("수량", min_value=0.0, step=1.0)
                    with c3: a_price = st.number_input("매수가", min_value=0.0, step=100.0)
                    
                    if st.form_submit_button("추가", type="primary") and a_qty > 0 and a_price > 0:
                        tid = opts[sel]
                        for p in portfolio:
                            if isinstance(p, dict) and p["id"] == tid:
                                p.setdefault("lots", []).append({"date": str(a_date), "qty": a_qty, "price": a_price, "type": "buy"})
                                break
                        save_portfolio(portfolio)
                        st.cache_data.clear(); st.success("추가 완료!"); st.rerun()

        elif manage_mode == "종목 삭제" and portfolio:
            to_del = st.selectbox("삭제할 종목", ["선택..."] + [f"{p['name']} [{p.get('account','일반')}]" for p in portfolio if isinstance(p, dict)])
            if to_del != "선택..." and st.button("삭제"):
                del_name = to_del.split(" [")[0]
                portfolio = [p for p in portfolio if isinstance(p, dict) and p["name"] != del_name]
                save_portfolio(portfolio)
                st.cache_data.clear(); st.rerun()

def render_ticker_bar(positions):
    if not positions: return
    ticker_items = ""
    for i, pos in enumerate(sorted(positions, key=lambda x: x.get("value_krw", 0), reverse=True)[:8]):
        clr = HOLD_COLORS[i % len(HOLD_COLORS)]
        pct, pclr = pos.get("daily_pct", 0), UP if pos.get("daily_pct", 0) >= 0 else DN
        sign = "+" if pct >= 0 else ""
        val_str = f"{pos['value_krw']/1e8:.2f}억" if pos["value_krw"] >= 1e8 else f"{pos['value_krw']/1e4:.0f}만"
        
        ticker_items += f"""
        <div style="display:flex;flex-direction:column;gap:3px;padding:10px 16px;background:{CARD};border:1px solid {BORD};border-radius:8px;min-width:160px;flex-shrink:0">
            <div style="display:flex;align-items:center;gap:6px">
                <span style="width:8px;height:8px;border-radius:50%;background:{clr};flex-shrink:0"></span>
                <span style="font-size:11px;font-weight:600;color:{TXT};overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:120px">{pos['name']}</span>
            </div>
            <div style="display:flex;align-items:baseline;justify-content:space-between">
                <span style="font-size:13px;font-weight:700;color:{TXT};font-family:'JetBrains Mono',monospace">{val_str}</span>
                <span style="font-size:11px;font-weight:600;color:{pclr};font-family:'JetBrains Mono',monospace">{sign}{pct:.2f}%</span>
            </div>
        </div>"""
        
    st.markdown(f'<div style="display:flex;gap:8px;overflow-x:auto;padding:4px 0 12px;scrollbar-width:thin;scrollbar-color:{BORD} transparent">{ticker_items}</div>', unsafe_allow_html=True)

def news_card_new(news, accent=B5):
    title = news.get("title", ""); url = news.get("url", "#")
    body = news.get("ai_summary") or news.get("summary", "")
    source = (news.get("source") or "")[:25]; pub = news.get("pub_date", "")
    score = news.get("score"); tags = news.get("tags", [])
    try: ds = datetime.fromisoformat(pub.replace("Z", "+00:00").split("+")[0]).strftime("%m-%d")
    except: ds = pub[:5] if pub else ""
    badge = ""
    if score is not None:
        if score >= 7: bf, bb = "호재", "rgba(226,75,74,.2)"
        elif score <= 3: bf, bb = "악재", "rgba(56,139,253,.2)"
        else: bf, bb = "중립", "rgba(56,139,253,.15)"
        bclr = UP if score >= 7 else (DN if score <= 3 else B5)
        badge = f'<span style="background:{bb};color:{bclr};padding:2px 7px;border-radius:12px;font-size:9px;font-weight:600;font-family:JetBrains Mono">{bf} {score}</span>'
    tag_html = "".join(f'<span style="background:{C3};color:{SUB};padding:1px 6px;border-radius:4px;font-size:9px;font-family:JetBrains Mono">#{t}</span>' for t in tags[:2]) if tags else ""
    return f"""<a href="{url}" target="_blank" style="text-decoration:none">
    <div style="background:{CARD};border:1px solid {BORD};border-left:3px solid {accent};border-radius:8px;padding:14px;height:190px;display:flex;flex-direction:column">
      <div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:8px">
        <div style="font-size:12px;font-weight:600;color:{TXT};line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;flex:1">{title}</div>
        {badge}
      </div>
      <div style="font-size:11px;color:{SUB};line-height:1.5;flex:1;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical">{body}</div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;padding-top:8px;border-top:1px solid {BORD}">
        <div style="display:flex;gap:4px">{tag_html}</div>
        <div style="display:flex;gap:8px;font-size:9px;color:{MUT};font-family:JetBrains Mono"><span>{source}</span><span>{ds}</span></div>
      </div>
    </div></a>"""

def disc_card_new(d):
    title = d.get("title", ""); url = d.get("url", "#"); filer = d.get("filer", "")
    dt = d.get("date", "")
    if len(dt) == 8: dt = f"{dt[4:6]}-{dt[6:8]}"
    return f"""<a href="{url}" target="_blank" style="text-decoration:none">
    <div style="background:{CARD};border:1px solid {BORD};border-left:3px solid {B7};border-radius:8px;padding:14px;min-height:90px;display:flex;flex-direction:column;justify-content:space-between">
      <div style="font-size:12px;font-weight:600;color:{TXT};line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical">{title}</div>
      <div style="display:flex;justify-content:space-between;margin-top:10px;padding-top:8px;border-top:1px solid {BORD};font-size:9px;color:{MUT};font-family:JetBrains Mono"><span>{filer}</span><span>{dt}</span></div>
    </div></a>"""

def render_risk_tab(positions, prices, mdf):
    if prices.empty or len(positions) < 2:
        st.markdown(f'<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;padding:40px;text-align:center"><div style="font-size:14px;color:{SUB}">종목이 2개 이상 등록되고 가격 데이터가 수집된 후 확인 가능합니다</div></div>', unsafe_allow_html=True)
        return

    st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};margin:1rem 0 10px">리스크 지표 요약</div>', unsafe_allow_html=True)
    
    risk_rows = ""
    for i, pos in enumerate(sorted(positions, key=lambda x: x.get("value_krw", 0), reverse=True)):
        clr = HOLD_COLORS[i % len(HOLD_COLORS)]
        t = pos["ticker"]
        is_usd = pos["currency"] == "USD"
        
        beta = calc_beta(t, is_usd, prices, mdf)
        vol = calc_vol(t, prices)
        mdd_v = calc_mdd(t, prices)
        sh = calc_sharpe(t, prices)
        
        b_html = get_badge_html(beta, (0.8, 1.3), "{:.2f}")
        v_html = get_badge_html(vol, (20, 35), "{:.1f}%", reverse=True)
        m_html = f'<span style="color:{DN};font-weight:700;font-family:JetBrains Mono">{mdd_v:.1f}%</span>' if mdd_v else f'<span style="color:{MUT}">—</span>'
        sh_html = get_badge_html(sh, (0, 1), "{:.2f}")
        
        risk_rows += f"""
        <tr style="border-bottom:1px solid {BORD}">
            <td style="padding:.7rem 1rem">
                <div style="display:flex;align-items:center;gap:8px">
                    <span style="width:8px;height:8px;border-radius:50%;background:{clr};flex-shrink:0"></span>
                    <div>
                        <div style="font-size:12px;font-weight:600;color:{TXT}">{pos['name']}</div>
                        <div style="font-size:9px;color:{MUT};font-family:'JetBrains Mono',monospace">{t}</div>
                    </div>
                </div>
            </td>
            <td style="padding:.7rem 1rem;text-align:center">{b_html}</td>
            <td style="padding:.7rem 1rem;text-align:center">{v_html}</td>
            <td style="padding:.7rem 1rem;text-align:center">{m_html}</td>
            <td style="padding:.7rem 1rem;text-align:center">{sh_html}</td>
        </tr>"""

    TH_S = f"padding:.6rem 1rem;font-size:10px;color:{MUT};font-weight:500;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid {BORD};text-align:center"
    st.markdown(f"""
    <div style="background:{CARD};border:1px solid {BORD};border-radius:12px;overflow:hidden">
        <table style="width:100%;border-collapse:collapse">
            <thead>
                <tr style="background:{C2}">
                    <th style="{TH_S};text-align:left">종목</th>
                    <th style="{TH_S}">베타<br><span style="font-size:8px;color:{MUT};font-weight:400">90일</span></th>
                    <th style="{TH_S}">변동성<br><span style="font-size:8px;color:{MUT};font-weight:400">60일·연환산</span></th>
                    <th style="{TH_S}">MDD<br><span style="font-size:8px;color:{MUT};font-weight:400">최대낙폭</span></th>
                    <th style="{TH_S}">샤프비율<br><span style="font-size:8px;color:{MUT};font-weight:400">90일</span></th>
                </tr>
            </thead>
            <tbody>{risk_rows}</tbody>
        </table>
    </div>
    <div style="background:{C2};border:1px solid {BORD};border-radius:8px;padding:10px 14px;font-size:10px;color:{SUB};margin-top:8px;display:flex;gap:16px;flex-wrap:wrap">
        <span>📊 <b style="color:{TXT}">베타</b> &lt;0.8 방어 · 0.8~1.3 중립 · &gt;1.3 공격</span>
        <span>📉 <b style="color:{TXT}">변동성</b> &lt;20% 안정 · 20~35% 보통 · &gt;35% 고위험</span>
        <span>⭐ <b style="color:{TXT}">샤프</b> &lt;0 손실 · 0~1 보통 · &gt;1 우수</span>
    </div><div style="height:1.5rem"></div>""", unsafe_allow_html=True)

    # ── 상관관계 매트릭스 ─────────────────────────────────
    st.markdown('<div style="font-size:14px;font-weight:600;color:{SUB};margin-bottom:10px">상관관계 매트릭스</div>', unsafe_allow_html=True)
    all_tickers = [p["ticker"] for p in positions]
    names_map = {p["ticker"]: p["name"] for p in positions}
    
    pivot = prices[prices["ticker"].isin(all_tickers)].pivot_table(index="date", columns="ticker", values="close")
    ret_mat = pivot.pct_change().dropna()

    if len(ret_mat.columns) >= 2 and len(ret_mat) >= 10:
        corr = ret_mat.corr()
        corr.columns = [names_map.get(t, t) for t in corr.columns]
        corr.index = [names_map.get(t, t) for t in corr.index]
        
        fig_c = go.Figure(go.Heatmap(
            z=corr.values, x=list(corr.columns), y=list(corr.index),
            colorscale=[[0, "#1F6FEB"], [0.5, CARD], [1, "#E24B4A"]],
            zmin=-1, zmax=1,
            text=[[f"{v:.2f}" for v in row] for row in corr.values],
            texttemplate="%{text}",
            textfont={"size": 11, "color": TXT, "family": "JetBrains Mono"},
            colorbar=dict(thickness=10, tickfont=dict(color=MUT, size=9), bgcolor="rgba(0,0,0,0)")
        ))
        fig_c.update_layout(
            paper_bgcolor=CARD, plot_bgcolor=CARD, height=max(280, len(corr)*60), margin=dict(l=8, r=60, t=8, b=8),
            font=dict(family="JetBrains Mono", size=10, color=MUT),
            xaxis=dict(tickfont=dict(size=10, color=TXT), tickangle=-30), yaxis=dict(tickfont=dict(size=10, color=TXT))
        )
        st.plotly_chart(fig_c, use_container_width=True)

    # ── 롤링 변동성 추이 ─────────────────────────────────
    st.markdown('<div style="font-size:14px;font-weight:600;color:{SUB};margin-bottom:10px">롤링 변동성 추이 (30일 연환산)</div>', unsafe_allow_html=True)
    fig_v = go.Figure()
    for i, pos in enumerate(positions):
        sub = prices[prices["ticker"]==pos["ticker"]].sort_values("date").copy()
        if len(sub) < 35: continue
        sub["ret"] = sub["close"].pct_change()
        sub["vol"] = sub["ret"].rolling(30).std() * np.sqrt(252) * 100
        sub = sub.dropna(subset=["vol"])
        if sub.empty: continue
        fig_v.add_trace(go.Scatter(x=sub["date"], y=sub["vol"], name=pos["name"], line=dict(color=HOLD_COLORS[i%len(HOLD_COLORS)], width=2)))
        
    fig_v.add_hline(y=20, line_dash="dash", line_color=SUB, line_width=1, annotation_text="20% 경계", annotation_font_color=SUB, annotation_font_size=9)
    fig_v.update_layout(paper_bgcolor=CARD, plot_bgcolor=CARD, height=260, margin=dict(l=8, r=8, t=8, b=8), legend=dict(orientation="h", y=1.1, x=0, font=dict(size=10, color=SUB)), hovermode="x unified", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor=G, ticksuffix="%"))
    st.plotly_chart(fig_v, use_container_width=True)

# ════════════════════════════════════════════════════════════════
# 5. 메인 앱 실행 흐름
# ════════════════════════════════════════════════════════════════
def main():
    render_css()
    render_sidebar_helper()

    portfolio = load_portfolio()
    if not isinstance(portfolio, list):
        portfolio = []

    prices = load_parquet(PRICE_FILE)
    mdf = load_parquet(MARKET_FILE)
    usdkrw = get_usdkrw(mdf)

    # 모든 리스트 항목 내부 딕셔너리 검증용 이중 방어 필터링
    positions_all = [compute_pos(p, prices, usdkrw) for p in portfolio if isinstance(p, dict)]
    positions_all = [p for p in positions_all if p is not None]

    accts_in_use = sorted({p["account"] for p in positions_all}) if positions_all else []
    acct_tabs = ["📊 전체"] + [ACCT_LABELS.get(a, a) for a in accts_in_use]
    rev_labels = {v: k for k, v in ACCT_LABELS.items()}

    sel_idx = st.radio("계좌 선택", acct_tabs, horizontal=True, label_visibility="collapsed", key="acct_radio")
    sel_account = None if sel_idx == "📊 전체" else rev_labels.get(sel_idx, sel_idx)

    portfolio_view = portfolio if sel_account is None else [p for p in portfolio if isinstance(p, dict) and p.get("account", "일반") == sel_account]
    positions = [p for p in positions_all] if sel_account is None else [p for p in positions_all if p["account"] == sel_account]

    # 상단 요약 카드 (전체보기 전용)
    if sel_account is None and accts_in_use:
        acct_cols = st.columns(len(accts_in_use))
        for col, acct in zip(acct_cols, accts_in_use):
            clr = ACCT_COLORS.get(acct, B5)
            holds = [p for p in positions_all if p["account"] == acct]
            a_val = sum(p["value_krw"] for p in holds)
            a_pnl = sum(p["pnl_krw"] for p in holds)
            a_pct = (a_pnl / sum(p["cost_krw"] for p in holds) * 100) if sum(p.get("cost_krw", 0) for p in holds) > 0 else 0
            pclr = UP if a_pnl >= 0 else DN
            sym = "▲" if a_pnl >= 0 else "▼"
            with col:
                st.markdown(f"""
                <div style="background:{CARD};border:1px solid {BORD};border-top:3px solid {clr};border-radius:9px;padding:13px 15px;margin-bottom:10px">
                  <div style="font-size:10px;color:{SUB};margin-bottom:4px">{ACCT_LABELS.get(acct,acct)}</div>
                  <div style="font-size:20px;font-weight:800;color:{TXT};font-family:'JetBrains Mono',monospace">{a_val/1e6:.1f}<span style="font-size:11px;color:{MUT}">백만원</span></div>
                  <div style="font-size:10px;color:{pclr};font-weight:600;font-family:'JetBrains Mono',monospace;margin-top:3px">{sym}{abs(a_pnl):,.0f}원 ({a_pct:+.2f}%)</div>
                  <div style="font-size:10px;color:{MUT};margin-top:2px">{len(holds)}개 종목</div>
                </div>""", unsafe_allow_html=True)

    h1, h2 = st.columns([4, 1])
    with h1:
        acct_label = ACCT_LABELS.get(sel_account, "") if sel_account else ""
        st.markdown(f'<div style="padding:16px 0 10px"><div style="font-size:12px;color:{SUB};font-weight:500;text-transform:uppercase;margin-bottom:4px">포트폴리오 {f"· {acct_label}" if acct_label else ""}</div><div style="font-size:26px;font-weight:700;color:{TXT}">투자자산 현황</div></div>', unsafe_allow_html=True)
    with h2:
        render_management_form(portfolio)

    render_ticker_bar(positions)

    df = pd.DataFrame(positions) if positions else pd.DataFrame()
    if df.empty:
        st.markdown(f'<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;padding:60px;text-align:center;margin-top:20px"><div style="font-size:40px;margin-bottom:16px">📊</div><div style="font-size:18px;font-weight:600;color:{TXT};margin-bottom:8px">{"이 계좌에 보유 종목 없음" if sel_account else "보유 종목 없음"}</div><div style="font-size:13px;color:{SUB}">우측 상단 ⚙️ 종목 관리에서 종목을 추가해주세요</div></div>', unsafe_allow_html=True)
        st.stop()

    # KPI 지표 정밀 계산
    df_p = df[df["current"].notna()] if "current" in df.columns else pd.DataFrame()
    if not df_p.empty:
        tv = df_p["value_krw"].sum()
        tc_v = df_p["cost_krw"].sum()
        tp = df_p["pnl_krw"].sum()
        tpct = (tp / tc_v * 100) if tc_v > 0 else 0
        td = df_p["daily_pnl_krw"].sum()
        dpct = (td / (tv - td) * 100) if (tv - td) > 0 else 0
        tv_usd = tv / usdkrw
    else:
        tv, tc_v, tp, tpct, td, dpct, tv_usd = 0, 0, 0, 0, 0, 0, 0

    hist_df = compute_daily_pf(portfolio_view, prices, mdf)

    # ── 대시보드 메인 레이아웃 (좌:우 = 4:6) ───────────────────────────
    left, right = st.columns([4, 6], gap="medium")
    
    with left:
        pnl_bg = "rgba(226,75,74,.12)" if td >= 0 else "rgba(56,139,253,.12)"
        pnl_clr = UP if td >= 0 else DN
        sign = "▲" if td >= 0 else "▼"
        st.markdown(f"""
        <div style="background:{CARD};border:1px solid {BORD};border-radius:12px;padding:24px;margin-bottom:10px">
          <div style="font-size:12px;color:{SUB};font-weight:500;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px">총 평가금액</div>
          <div style="font-size:36px;font-weight:800;color:{TXT};font-family:'JetBrains Mono',monospace;line-height:1;margin-bottom:12px">{tv:,.0f}<span style="font-size:14px;font-weight:500;color:{SUB}">원</span></div>
          <div style="display:flex;gap:8px;align-items:center"><span style="background:{pnl_bg};color:{pnl_clr};padding:4px 10px;border-radius:20px;font-size:12px;font-weight:600;font-family:'JetBrains Mono',monospace">{sign} 전일 {td:+,.0f}원 ({dpct:+.2f}%)</span></div>
          <div style="margin-top:10px;font-size:11px;color:{SUB};font-family:'JetBrains Mono',monospace">≈ ${tv_usd:,.0f} · 환율 {usdkrw:,.0f}</div>
        </div>""", unsafe_allow_html=True)

        df_sorted_val = df_p.sort_values("value_krw", ascending=False) if not df_p.empty else pd.DataFrame()
        segments = ""
        holding_rows = ""
        
        if not df_sorted_val.empty:
            for i, ((_, row), clr) in enumerate(zip(df_sorted_val.iterrows(), HOLD_COLORS)):
                w = row["value_krw"] / tv * 100 if tv > 0 else 0
                if w >= 0.5:
                    rr = "4px 0 0 4px" if i == 0 else ""
                    segments += f'<div style="width:{w:.2f}%;background:{clr};height:100%;{"border-radius:"+rr+";" if rr else ""}"></div>'
                
                pclr = UP if row["pnl_pct"] >= 0 else DN
                sp = "+" if row["pnl_pct"] >= 0 else ""
                holding_rows += f"""
                <div style="display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid {BORD};gap:8px">
                  <div style="display:flex;align-items:center;gap:8px;flex:1;min-width:0">
                    <span style="width:8px;height:8px;border-radius:50%;background:{clr};flex-shrink:0"></span>
                    <span style="font-size:12px;color:{TXT};font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{row['name']}</span>
                  </div>
                  <div style="display:flex;align-items:center;gap:12px;flex-shrink:0">
                    <span style="font-size:11px;color:{SUB};min-width:36px;text-align:right">{w:.1f}%</span>
                    <span style="font-size:12px;font-weight:600;color:{TXT};font-family:'JetBrains Mono',monospace;min-width:70px;text-align:right">{row['value_krw']:,.0f}</span>
                    <span style="font-size:11px;font-weight:600;color:{pclr};font-family:'JetBrains Mono',monospace;min-width:56px;text-align:right">{sp}{row['pnl_pct']:.2f}%</span>
                  </div>
                </div>"""

        st.markdown(f"""
        <div style="background:{CARD};border:1px solid {BORD};border-radius:12px;padding:20px;margin-bottom:10px">
          <div style="font-size:11px;color:{SUB};font-weight:500;text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px">자산 구성</div>
          <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;background:{C2};margin-bottom:14px;gap:1px">{segments}</div>
          <div style="display:flex;align-items:center;padding:4px 0 8px;gap:8px">
            <span style="font-size:10px;color:{MUT};flex:1">종목</span>
            <span style="font-size:10px;color:{MUT};min-width:36px;text-align:right">비중</span>
            <span style="font-size:10px;color:{MUT};min-width:70px;text-align:right">평가금액</span>
            <span style="font-size:10px;color:{MUT};min-width:56px;text-align:right">수익률</span>
          </div>
          {holding_rows}
        </div>""", unsafe_allow_html=True)

    with right:
        _, rng_col = st.columns([1, 5])
        with rng_col:
            rng = st.radio("기간", ["1W", "1M", "3M", "6M", "1Y", "YTD", "ALL"], horizontal=True, label_visibility="collapsed", key="rng")
            if rng != st.session_state.chart_range:
                st.session_state.chart_range = rng

        filtered = filter_hist(hist_df, st.session_state.chart_range)
        if not filtered.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=filtered["date"], y=filtered["value"], name="포트폴리오", line=dict(color=B5, width=2), fill="tonexty", fillcolor="rgba(56,139,253,.12)"), secondary_y=False)
            
            if "cost" in filtered.columns:
                cost_last = filtered.iloc[-1]["cost"]
                if cost_last > 0:
                    fig.add_hline(y=cost_last, line_dash="dash", line_color=SUB, line_width=1, annotation_text=f"매입 {cost_last/1e8:.2f}억", annotation_font_color=SUB)

            fig.update_layout(paper_bgcolor=CARD, plot_bgcolor=CARD, height=340, margin=dict(l=8, r=8, t=8, b=8), hovermode="x unified", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor=G, side="right"))
            st.plotly_chart(fig, use_container_width=True)

            max_v, min_v = filtered["value"].max(), filtered["value"].min()
            chg_pct = (filtered.iloc[-1]["value"] / filtered.iloc[0]["value"] - 1) * 100
            
            m_cols = st.columns(3)
            metrics = [("최고점", f"{max_v/1e8:.2f}억", B5), ("최저점", f"{min_v/1e8:.2f}억", DN), ("기간 성과", f"{chg_pct:+.2f}%", UP if chg_pct >= 0 else DN)]
            for col, (lbl, val, clr) in zip(m_cols, metrics):
                with col:
                    st.markdown(f'<div style="background:{C2};border:1px solid {BORD};border-radius:8px;padding:12px 14px"><div style="font-size:10px;color:{SUB}">{lbl}</div><div style="font-size:15px;font-weight:700;color:{clr};font-family:JetBrains Mono">{val}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;padding:40px;text-align:center;height:340px;display:flex;align-items:center;justify-content:center"><div style="color:{SUB};font-size:13px">수집된 히스토리 데이터가 없습니다.</div></div>', unsafe_allow_html=True)

    # 계좌별 평가금액 추이 차트 (전체 선택 시)
    if sel_account is None and accts_in_use and not prices.empty:
        st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};margin:1.2rem 0 .5rem">💼 계좌별 평가금액 추이</div>', unsafe_allow_html=True)
        fig_bal = go.Figure()
        for acct in accts_in_use:
            pf_acct = [p for p in portfolio if isinstance(p, dict) and p.get("account", "일반") == acct]
            if not pf_acct: continue
            h = compute_daily_pf(pf_acct, prices, mdf)
            if h.empty: continue
            fig_bal.add_trace(go.Scatter(x=h["date"], y=h["value"]/1e6, name=ACCT_LABELS.get(acct, acct), mode="lines", stackgroup="one", line=dict(width=1.5, color=ACCT_COLORS.get(acct, B5))))
        fig_bal.update_layout(paper_bgcolor=CARD, plot_bgcolor=CARD, height=240, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor=G, side="right"))
        st.plotly_chart(fig_bal, use_container_width=True, config={"displayModeBar": False})

    # 하단 KPI 스트립
    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
    kpi_items = [
        ("누적 평가손익", f"{tp:+,.0f}원", f"{tpct:+.2f}%", UP if tp>=0 else DN),
        ("매입 원가", f"{tc_v:,.0f}원", "투자 원금", SUB),
        ("전일 평가손익", f"{td:+,.0f}원", f"{dpct:+.2f}%", UP if td>=0 else DN),
        ("USD/KRW 환율", f"{usdkrw:,.1f}원", "현재 환율", SUB),
        ("USD 환산 자산", f"${tv_usd:,.0f}", "포트폴리오 총액", SUB)
    ]
    ks_cols = st.columns(5)
    for col, (lbl, val, sub_, clr) in zip(ks_cols, kpi_items):
        with col:
            st.markdown(f"""
            <div style="background:{CARD};border:1px solid {BORD};border-radius:10px;padding:16px 18px">
              <div style="font-size:10px;color:{SUB};text-transform:uppercase;margin-bottom:6px">{lbl}</div>
              <div style="font-size:20px;font-weight:800;color:{TXT};font-family:'JetBrains Mono',monospace;line-height:1;margin-bottom:4px">{val}</div>
              <div style="font-size:11px;color:{clr};font-weight:600">{sub_}</div>
            </div>""", unsafe_allow_html=True)

    # ── 하단 탭 섹션 (상세 테이블, 뉴스, 공시, 리스크) ───────────────────────
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["📋 상세 테이블", "📰 뉴스", "📑 공시", "📊 리스크"])

    with t1:
        df_sorted = df.sort_values("value_krw", ascending=False) if not df.empty else pd.DataFrame()
        rows_html = ""
        for i, (_, r) in enumerate(df_sorted.iterrows()):
            clr = HOLD_COLORS[i % len(HOLD_COLORS)]
            pclr = UP if r["pnl_pct"] >= 0 else DN
            dclr = UP if r["daily_pct"] >= 0 else DN
            cv = f"{r['current']:,.2f}" if r["current"] else "—"
            wt = (r["value_krw"] / tv * 100) if tv > 0 else 0
            a_clr = ACCT_COLORS.get(r.get("account", "일반"), B5)
            
            rows_html += f"""
            <tr style="border-bottom:1px solid {BORD}">
                <td style="padding:.7rem 1rem">
                    <div style="display:flex;align-items:center;gap:8px">
                        <span style="width:8px;height:8px;border-radius:50%;background:{clr};flex-shrink:0"></span>
                        <div><div style="font-size:12px;font-weight:600;color:{TXT}">{r['name']}</div><div style="font-size:9px;color:{MUT};font-family:'JetBrains Mono'">{r['ticker']}</div></div>
                    </div>
                </td>
                <td style="padding:.7rem 1rem;text-align:center"><span style="background:{a_clr}22;color:{a_clr};padding:2px 7px;border-radius:5px;font-size:9px;font-weight:700">{r.get('account','일반')}</span></td>
                <td style="padding:.7rem 1rem;text-align:right;font-family:'JetBrains Mono';font-size:12px">{r['qty']:,.0f}</td>
                <td style="padding:.7rem 1rem;text-align:right;font-family:'JetBrains Mono';font-size:12px">{r['avg_cost']:,.2f}</td>
                <td style="padding:.7rem 1rem;text-align:right"><div style="font-family:'JetBrains Mono';font-size:12px">{cv}</div><div style="font-size:10px;color:{dclr};font-weight:600">{r['daily_pct']:+.2f}%</div></td>
                <td style="padding:.7rem 1rem;text-align:right"><div style="font-family:'JetBrains Mono';font-size:13px;font-weight:700">{r['value_krw']:,.0f}</div><div style="font-size:10px;color:{SUB}">{wt:.1f}%</div></td>
                <td style="padding:.7rem 1rem;text-align:right"><div style="font-family:'JetBrains Mono';font-size:13px;font-weight:700;color:{pclr}">{r['pnl_krw']:+,.0f}</div><div style="font-size:10px;color:{pclr}">{r['pnl_pct']:+.2f}%</div></td>
            </tr>"""

        TH = f"padding:.6rem 1rem;text-align:left;font-size:10px;color:{MUT};font-weight:500;border-bottom:1px solid {BORD};text-transform:uppercase"
        st.markdown(f"""
        <div style="background:{CARD};border:1px solid {BORD};border-radius:12px;overflow:hidden;margin-top:8px">
        <table style="width:100%;border-collapse:collapse">
            <thead><tr style="background:{C2}">
                <th style="{TH}">종목</th><th style="{TH};text-align:center">계좌</th><th style="{TH};text-align:right">수량</th><th style="{TH};text-align:right">평균단가</th><th style="{TH};text-align:right">현재가·일간</th><th style="{TH};text-align:right">평가금액(비중)</th><th style="{TH};text-align:right">평가손익</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table></div>""", unsafe_allow_html=True)

    with t2:
        news_data = load_json(NEWS_FILE, {})
        stocks_news = news_data.get("stocks", {})
        ordered = [(r["name"], stocks_news[r["name"]]) for _, r in df_sorted.iterrows() if isinstance(stocks_news, dict) and r["name"] in stocks_news and stocks_news[r["name"]]]
        if not ordered:
            st.markdown(f'<div style="color:{SUB};font-size:13px;padding:20px">수집된 종목 뉴스가 없습니다.</div>', unsafe_allow_html=True)
        else:
            for i, (name, articles) in enumerate(ordered):
                clr = HOLD_COLORS[i % len(HOLD_COLORS)]
                st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:10px 0 8px"><span style="width:8px;height:8px;border-radius:50%;background:{clr}"></span><span style="font-size:13px;font-weight:700;color:{TXT}">{name}</span></div>', unsafe_allow_html=True)
                cols = st.columns(3)
                for col, news in zip(cols, articles[:3]):
                    with col: st.markdown(news_card_new(news, accent=clr), unsafe_allow_html=True)

    with t3:
        disc_data = load_json(DISC_FILE, {})
        discs = disc_data.get("disclosures", {})
        ordered_d = [(r["name"], discs[r["name"]]) for _, r in df_sorted.iterrows() if isinstance(discs, dict) and r["name"] in discs and discs[r["name"]]]
        if not ordered_d:
            st.markdown(f'<div style="color:{SUB};font-size:13px;padding:20px">최근 14일간 공시 내역이 없습니다.</div>', unsafe_allow_html=True)
        else:
            for i, (name, items_) in enumerate(ordered_d):
                clr = HOLD_COLORS[i % len(HOLD_COLORS)]
                st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:10px 0 8px"><span style="width:8px;height:8px;border-radius:50%;background:{clr}"></span><span style="font-size:13px;font-weight:700;color:{TXT}">{name}</span><span style="font-size:10px;color:{MUT}">{len(items_)}건</span></div>', unsafe_allow_html=True)
                cols = st.columns(3)
                for j, d_ in enumerate(items_[:6]):
                    with cols[j % 3]: st.markdown(disc_card_new(d_), unsafe_allow_html=True)

    with t4:
        render_risk_tab(positions, prices, mdf)

    st.markdown(f'<div style="margin-top:2rem;padding:10px 14px;background:{CARD};border:1px solid {BORD};border-radius:8px;font-size:10px;color:{MUT};font-family:\'JetBrains Mono\'">가격 갱신: {prices["date"].max().strftime("%Y-%m-%d") if not prices.empty else "—"} · USD/KRW: {usdkrw:,.1f}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
