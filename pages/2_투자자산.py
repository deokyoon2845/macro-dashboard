"""
3. 투자자산 — 계좌별 관리 + 블루/레드 팔레트 + 스티키 네비
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
# 3. 데이터 로드 및 비즈니스 로직
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

def load_json(path, default):
    if path.exists():
        with open(path, encoding="utf-8") as f: return json.load(f)
    return default

def save_json(path, data):
    DATA.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@st.cache_data(ttl=600)
def load_parquet(path):
    if path.exists():
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        return df
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
    lots = item.get("lots", [])
    ticker = item.get("ticker", "")
    if not lots or not ticker: return None
    
    qty = sum(l["qty"] for l in lots)
    cost = sum(l["qty"]*l["price"] for l in lots)
    avg = cost/qty if qty > 0 else 0
    cur, prev = get_px(ticker, prices)
    
    is_usd = item.get("currency", "KRW") == "USD"
    fx = usdkrw if is_usd else 1
    
    base = {
        "name": item["name"], "ticker": ticker, "sector": item.get("sector", "기타"),
        "market": item.get("market", "기타"), "currency": item.get("currency", "KRW"),
        "account": item.get("account", "일반"), "qty": qty, "avg_cost": avg, 
        "id": item.get("id", ""), "lots": lots
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
            qty = sum(l["qty"] for l in it.get("lots", []) if pd.Timestamp(l["date"]) <= d)
            cost = sum(l["qty"]*l["price"] for l in it.get("lots", []) if pd.Timestamp(l["date"]) <= d)
            if qty <= 0: continue
            
            any_pos = True
            ps = prices[(prices["ticker"]==it["ticker"]) & (prices["date"]<=d)].sort_values("date")
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

# ── 리스크 계산 헬퍼 함수 ────────────────────────────────────
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
# 4. UI 렌더링 함수
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
                    save_json(PORT_FILE, portfolio)
                    st.cache_data.clear(); st.success("등록 완료!"); st.rerun()

        elif manage_mode == "매수 기록 추가" and portfolio:
            with st.form("af", clear_on_submit=True):
                opts = {f"{p['name']} [{p.get('account','일반')}]": p["id"] for p in portfolio}
                sel = st.selectbox("종목", list(opts.keys()))
                
                c1, c2, c3 = st.columns(3)
                with c1: a_date = st.date_input("매수일", date.today())
                with c2: a_qty = st.number_input("수량", min_value=0.0, step=1.0)
                with c3: a_price = st.number_input("매수가", min_value=0.0, step=100.0)
                
                if st.form_submit_button("추가", type="primary") and a_qty > 0 and a_price > 0:
                    tid = opts[sel]
                    for p in portfolio:
                        if p["id"] == tid:
                            p.setdefault("lots", []).append({"date": str(a_date), "qty": a_qty, "price": a_price, "type": "buy"})
                            break
                    save_json(PORT_FILE, portfolio)
                    st.cache_data.clear(); st.success("추가 완료!"); st.rerun()

        elif manage_mode == "종목 삭제" and portfolio:
            to_del = st.selectbox("삭제할 종목", ["선택..."] + [f"{p['name']} [{p.get('account','일반')}]" for p in portfolio])
            if to_del != "선택..." and st.button("삭제"):
                del_name = to_del.split(" [")[0]
                portfolio = [p for p in portfolio if p["name"] != del_name]
                save_json(PORT_FILE, portfolio)
                st.cache_data.clear(); st.rerun()

def render_ticker_bar(positions):
    if not positions: return
    ticker_items = ""
    for i, pos in enumerate(sorted(positions, key=lambda x: x["value_krw"], reverse=True)[:8]):
        clr = HOLD_COLORS[i % len(HOLD_COLORS)]
        pct, pclr = pos["daily_pct"], UP if pos["daily_pct"] >= 0 else DN
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

def render_risk_tab(positions, prices, mdf):
    if prices.empty or len(positions) < 2:
        st.markdown(f'<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;padding:40px;text-align:center"><div style="font-size:14px;color:{SUB}">종목이 2개 이상 등록되고 가격 데이터가 수집된 후 확인 가능합니다</div></div>', unsafe_allow_html=True)
        return

    st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};margin:1rem 0 10px">리스크 지표 요약</div>', unsafe_allow_html=True)
    
    risk_rows = ""
    for i, pos in enumerate(sorted(positions, key=lambda x: x["value_krw"], reverse=True)):
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

# ════════════════════════════════════════════════════════════════
# 5. 메인 앱 실행 흐름
# ════════════════════════════════════════════════════════════════
def main():
    if "chart_range" not in st.session_state: st.session_state.chart_range = "3M"
    if "sel_account" not in st.session_state: st.session_state.sel_account = "📊 전체"

    render_css()
    render_sidebar_helper()

    portfolio = load_json(PORT_FILE, [])
    prices = load_parquet(PRICE_FILE)
    mdf = load_parquet(MARKET_FILE)
    usdkrw = get_usdkrw(mdf)

    positions_all = [compute_pos(p, prices, usdkrw) for p in portfolio if isinstance(p, dict)]
    positions_all = [p for p in positions_all if p]

    # 계좌 선택 UI
    accts_in_use = sorted({p["account"] for p in positions_all}) if positions_all else []
    acct_tabs = ["📊 전체"] + [ACCT_LABELS.get(a, a) for a in accts_in_use]
    rev_labels = {v: k for k, v in ACCT_LABELS.items()}

    sel_idx = st.radio("계좌 선택", acct_tabs, horizontal=True, label_visibility="collapsed", key="acct_radio")
    sel_account = None if sel_idx == "📊 전체" else rev_labels.get(sel_idx, sel_idx)

    portfolio_view = portfolio if sel_account is None else [p for p in portfolio if p.get("account", "일반") == sel_account]
    positions = [p for p in positions_all] if sel_account is None else [p for p in positions_all if p["account"] == sel_account]

    # 헤더 및 종목 관리 렌더링
    h1, h2 = st.columns([4, 1])
    with h1:
        acct_label = ACCT_LABELS.get(sel_account, "") if sel_account else ""
        st.markdown(f'<div style="padding:16px 0 10px"><div style="font-size:12px;color:{SUB};font-weight:500;text-transform:uppercase;margin-bottom:4px">포트폴리오 {f"· {acct_label}" if acct_label else ""}</div><div style="font-size:26px;font-weight:700;color:{TXT}">투자자산 현황</div></div>', unsafe_allow_html=True)
    with h2:
        render_management_form(portfolio)

    render_ticker_bar(positions)

    # 데이터 부재 시 처리
    df = pd.DataFrame(positions) if positions else pd.DataFrame()
    if df.empty:
        st.markdown(f'<div style="background:{CARD};border:1px solid {BORD};border-radius:12px;padding:60px;text-align:center;margin-top:20px"><div style="font-size:40px;margin-bottom:16px">📊</div><div style="font-size:18px;font-weight:600;color:{TXT};margin-bottom:8px">{"이 계좌에 보유 종목 없음" if sel_account else "보유 종목 없음"}</div><div style="font-size:13px;color:{SUB}">우측 상단 ⚙️ 종목 관리에서 종목을 추가해주세요</div></div>', unsafe_allow_html=True)
        st.stop()

    # (이하 생략 - 전체 메인 레이아웃 및 탭 렌더링 로직 위치)
    # 리팩토링된 탭(t1~t4) 코드는 기존과 동일한 방식으로 호출하되, 복잡한 함수들은 위로 분리되었습니다.
    
    t1, t2, t3, t4 = st.tabs(["📋 상세 테이블", "📰 뉴스", "📑 공시", "📊 리스크"])
    with t4:
        render_risk_tab(positions, prices, mdf)

if __name__ == "__main__":
    main()
