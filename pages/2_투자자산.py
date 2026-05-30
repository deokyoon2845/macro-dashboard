"""
3_투자자산.py — QLD 스타일 v2
수정: 사이드바 토글 CSS · 색상 버그픽스 · 계좌별 차트 · QLD 팔레트
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime, date
import json, uuid, base64, sys, requests

# ════════════════════════════════════════════════════════════════
# 초기 설정
# ════════════════════════════════════════════════════════════════
st.set_page_config(page_title="투자자산", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    from utils import render_sticky_nav
    render_sticky_nav()
except Exception:
    pass

DATA      = _ROOT / "data"
ASSET_DIR = _ROOT / "assets"
PORT_FILE   = DATA / "portfolio.json"
PRICE_FILE  = DATA / "portfolio_prices.parquet"
MARKET_FILE = DATA / "market_prices.parquet"
NEWS_FILE   = DATA / "portfolio_news.json"
DISC_FILE   = DATA / "portfolio_disclosures.json"

# ════════════════════════════════════════════════════════════════
# 색상 팔레트 (QLD + 한국 관례)
# ════════════════════════════════════════════════════════════════
BG   = "#07090F"; CARD = "#0D1117"; C2   = "#131924"; C3   = "#1A2233"
BORD = "#1E2433"; BORD2= "#2D3748"; TXT  = "#EAEEF2"; SUB  = "#8B949E"; MUT  = "#484F58"
UP   = "#E24B4A"   # 상승 = 빨강 (한국 관례)
DN   = "#388BFD"   # 하락 = 파랑 (한국 관례)
B3   = "#79C0FF"; B5 = "#388BFD"; B6 = "#2F81F7"; B7 = "#1F6FEB"

HOLD_COLORS = ["#388BFD","#79C0FF","#1F6FEB","#58A6FF","#2F81F7","#CAE8FF",
               "#4A82E4","#9ECEFF","#1158C7","#56D3FF","#0D6EFD","#B0D9FF"]

# 계좌 색상 (수정됨: DC=빨강, 연금저축=초록)
ACCT_COLORS = {"일반":"#388BFD", "DC":"#E24B4A", "연금저축":"#3FB950"}
ACCT_LABELS = {"일반":"💳 일반", "DC":"🏢 DC", "연금저축":"🏦 연금저축"}
ALL_ACCOUNTS = ["일반","DC","연금저축"]

SECTORS = ["반도체","방산","증권·금융","우주항공","로봇·자동화","2차전지","바이오",
           "IT·소프트웨어","엔터·미디어","자동차","화학","철강·소재","건설","유틸리티",
           "소비재","미용","에너지","기타"]
MARKETS = ["KOSPI","KOSDAQ","NYSE","NASDAQ","기타"]

# ════════════════════════════════════════════════════════════════
# 커스텀 폰트
# ════════════════════════════════════════════════════════════════
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

# ════════════════════════════════════════════════════════════════
# CSS — 핵심 수정 3가지:
# 1. span,div에 color!important 없음 → 인라인 색상 작동
# 2. collapsedControl CSS → 사이드바 접었다 펼 수 있음
# 3. QLD 팔레트 적용
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
/* span/div에 color!important 없음 → 인라인 색상이 정상 작동 */
label{{color:{TXT}!important}}
/* ★ 사이드바 토글 버튼 — 접은 후에도 보임 (핵심 수정) */
[data-testid="collapsedControl"]{{background:{CARD}!important;border:2px solid {B5}!important;border-left:none!important;border-radius:0 10px 10px 0!important;width:2.4rem!important;top:.8rem!important;box-shadow:4px 0 14px rgba(56,139,253,.35)!important;transition:all .2s!important}}
[data-testid="collapsedControl"]:hover{{background:{C2}!important;box-shadow:4px 0 20px rgba(56,139,253,.5)!important}}
[data-testid="collapsedControl"] svg{{color:{B5}!important;fill:{B5}!important}}
.stButton>button{{background:transparent!important;color:{SUB}!important;border:1px solid {BORD}!important;border-radius:6px!important;font-family:{FF}!important;font-size:12px!important;font-weight:500!important;padding:5px 14px!important;box-shadow:none!important;transition:all .12s!important}}
.stButton>button:hover{{border-color:{B5}!important;color:{B5}!important;background:{C2}!important}}
[data-testid="stRadio"]>div{{gap:2px!important;flex-direction:row!important}}
[data-testid="stRadio"]>div>label{{background:transparent!important;color:{SUB}!important;border:1px solid {BORD}!important;border-radius:5px!important;padding:5px 12px!important;font-size:11px!important;font-family:{FF}!important;font-weight:500!important;cursor:pointer!important;transition:all .12s!important}}
[data-testid="stRadio"]>div>label[data-selected="true"]{{background:{C2}!important;color:{TXT}!important;border-color:{BORD2}!important}}
.js-plotly-plot{{border-radius:0!important}}
.stTabs [data-baseweb="tab-list"]{{background:{CARD}!important;border-bottom:1px solid {BORD}!important;gap:0}}
.stTabs [data-baseweb="tab"]{{background:transparent!important;color:{SUB}!important;font-family:{FF}!important;font-size:12px!important;font-weight:500!important;border-bottom:2px solid transparent!important;padding:10px 20px!important}}
.stTabs [aria-selected="true"]{{color:{TXT}!important;border-bottom-color:{B5}!important}}
.stTabs [data-baseweb="tab-panel"]{{background:transparent!important;padding:0!important}}
::-webkit-scrollbar{{width:3px;height:3px}}
::-webkit-scrollbar-track{{background:transparent}}
::-webkit-scrollbar-thumb{{background:{BORD2};border-radius:2px}}
</style>""",
    unsafe_allow_html=True
)

# ════════════════════════════════════════════════════════════════
# 데이터 함수
# ════════════════════════════════════════════════════════════════
def load_portfolio():
    if PORT_FILE.exists():
        try:
            with open(PORT_FILE, encoding="utf-8") as f:
                d = json.load(f)
                return d if isinstance(d, list) else []
        except: return []
    return []

def get_secret(k, default=""):
    try:    return st.secrets[k]
    except: return __import__("os").environ.get(k, default)

# ── 개선 2: GitHub API 저장 (앱에서 직접 portfolio.json 쓰기) ─
def save_portfolio(data):
    """GitHub API 우선 저장 → 실패 시 로컬 폴백"""
    # ① GitHub API 저장 시도
    token = get_secret("GITHUB_TOKEN", "")
    repo  = get_secret("GITHUB_REPO", "deokyoon2845/macro-dashboard")
    if token and not token.startswith("*"):
        try:
            path = "data/portfolio.json"
            url  = f"https://api.github.com/repos/{repo}/contents/{path}"
            hdr  = {"Authorization": f"token {token}",
                    "Accept": "application/vnd.github+json"}
            r = requests.get(url, headers=hdr, timeout=8)
            sha = r.json().get("sha") if r.status_code == 200 else None
            body = json.dumps(data, ensure_ascii=False, indent=2)
            payload = {
                "message": f"[앱] 포트폴리오 업데이트 {__import__('datetime').datetime.now():%Y-%m-%d %H:%M}",
                "content": __import__("base64").b64encode(body.encode()).decode(),
            }
            if sha: payload["sha"] = sha
            r2 = requests.put(url, headers=hdr, json=payload, timeout=10)
            if r2.status_code in (200, 201):
                return  # ✅ GitHub 저장 성공 → 로컬 불필요
            else:
                st.warning(f"GitHub 저장 실패 ({r2.status_code}) — 로컬 저장으로 대체합니다")
        except Exception as e:
            st.warning(f"GitHub 저장 오류: {e} — 로컬 저장으로 대체합니다")
    # ② 로컬 폴백 (Streamlit Cloud에선 재시작 시 초기화됨, 주의)
    DATA.mkdir(exist_ok=True)
    with open(PORT_FILE,"w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path, default):
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f: return json.load(f)
        except: return default
    return default

@st.cache_data(ttl=600)
def load_parquet(path_str):
    p = Path(path_str)
    if not p.exists(): return pd.DataFrame()
    try:
        df = pd.read_parquet(p)
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        return df
    except: return pd.DataFrame()

def get_usdkrw(mdf):
    if mdf.empty or "indicator" not in mdf.columns: return 1380.0
    s = mdf[mdf["indicator"]=="USDKRW"].sort_values("date")
    return float(s.iloc[-1]["value"]) if not s.empty else 1380.0

def get_px(ticker, prices):
    if prices.empty: return None, None
    sub = prices[prices["ticker"]==ticker].sort_values("date")
    if sub.empty: return None, None
    return float(sub.iloc[-1]["close"]), (float(sub.iloc[-2]["close"]) if len(sub)>=2 else None)

def compute_pos(item, prices, usdkrw, live=None):
    """live: fetch_live_prices() 결과 dict (없으면 parquet 사용)"""
    if not isinstance(item, dict): return None
    lots = [l for l in item.get("lots",[]) if isinstance(l,dict)]
    ticker = item.get("ticker","")
    if not lots or not ticker: return None
    qty  = sum(l.get("qty",0) for l in lots)
    cost = sum(l.get("qty",0)*l.get("price",0) for l in lots)
    avg  = cost/qty if qty>0 else 0
    is_usd = item.get("currency","KRW")=="USD"; fx = usdkrw if is_usd else 1
    base = {"name":item.get("name",""), "ticker":ticker, "sector":item.get("sector","기타"),
            "market":item.get("market","기타"), "currency":item.get("currency","KRW"),
            "account":item.get("account","일반"), "qty":qty, "avg_cost":avg,
            "id":item.get("id",""), "lots":lots}
    # 실시간 우선 → parquet 폴백
    if live and ticker in live:
        cur  = live[ticker]["cur"]
        prev = live[ticker]["prev"]
        is_live = True
    else:
        cur, prev = get_px(ticker, prices)
        is_live = False
    if cur is None:
        return {**base,"current":None,"value_krw":0,"cost_krw":cost*fx,
                "pnl_krw":0,"pnl_pct":0,"daily_pct":0,"daily_pnl_krw":0,"is_live":False}
    val=cur*qty*fx; pnl=(cur-avg)*qty*fx
    return {**base,"current":cur,"value_krw":val,"cost_krw":cost*fx,"pnl_krw":pnl,
            "pnl_pct":(cur/avg-1)*100 if avg>0 else 0,
            "daily_pct":(cur/prev-1)*100 if prev and prev>0 else 0,
            "daily_pnl_krw":(cur-prev)*qty*fx if prev else 0,
            "is_live":is_live}

# ── 개선 1: 실시간 가격 (3분 캐시) ─────────────────────────────
@st.cache_data(ttl=180)
def fetch_live_prices(tickers_tuple):
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

@st.cache_data(ttl=600)
def compute_account_history(_prices_df, _market_df, _portfolio_json):
    """계좌별 + 총합계 일별 잔고 계산 (Home.py 동일 방식)"""
    portfolio = json.loads(_portfolio_json)
    if _prices_df.empty or not portfolio: return pd.DataFrame()
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
        for it in portfolio:
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

# ── 리스크 계산 ──────────────────────────────────────────────
def get_ret(ticker, prices, days=None):
    sub = prices[prices["ticker"]==ticker].sort_values("date")
    if days: sub = sub.tail(days+1)
    return sub["close"].pct_change().dropna()

def calc_beta(ticker, is_usd, prices, mdf, days=90):
    sr = get_ret(ticker, prices, days)
    if len(sr)<20: return None
    bind = "SPX" if is_usd else "KOSPI"
    if mdf.empty or "indicator" not in mdf.columns: return None
    bench = mdf[mdf["indicator"]==bind].sort_values("date")
    if bench.empty: return None
    br = bench.set_index("date")["value"].pct_change().dropna()
    common = sr.index.intersection(br.index)
    if len(common)<20: return None
    s=sr[common].values; b=br[common].values; vb=np.var(b)
    return round(float(np.cov(s,b)[0,1]/vb),2) if vb!=0 else None

def calc_vol(ticker, prices, days=60):
    r = get_ret(ticker, prices, days)
    return round(float(r.std()*np.sqrt(252)*100),2) if len(r)>=10 else None

def calc_mdd(ticker, prices):
    sub = prices[prices["ticker"]==ticker].sort_values("date")["close"]
    if len(sub)<5: return None
    dd = (sub-sub.cummax())/sub.cummax()*100
    return round(float(dd.min()),2)

def calc_sharpe(ticker, prices, rf=3.5, days=90):
    r = get_ret(ticker, prices, days)
    if len(r)<20: return None
    ann=float(r.mean()*252*100); vol=float(r.std()*np.sqrt(252)*100)
    return round((ann-rf)/vol,2) if vol>0 else None

def badge_html(v, thresholds, fmt, reverse=False):
    if v is None: return '<span style="color:' + MUT + '">—</span>'
    lo,hi=thresholds
    clr=(UP if v<lo else (SUB if v<hi else DN)) if reverse else (DN if v<lo else (SUB if v<hi else UP))
    return '<span style="color:' + clr + ';font-weight:700;font-family:JetBrains Mono,monospace">' + fmt.format(v) + '</span>'

# ════════════════════════════════════════════════════════════════
# 카드/뉴스 렌더 함수
# ════════════════════════════════════════════════════════════════
def news_card(news, accent=B5):
    title = news.get("title",""); url = news.get("url","#")
    body  = news.get("ai_summary") or news.get("summary","")
    src   = (news.get("source") or "")[:25]; pub = news.get("pub_date","")
    score = news.get("score"); tags = news.get("tags",[])
    try: ds=datetime.fromisoformat(pub.replace("Z","+00:00").split("+")[0]).strftime("%m-%d")
    except: ds=pub[:5] if pub else ""
    badge=""
    if score is not None:
        if score>=7: bf,bb="호재","rgba(226,75,74,.2)"
        elif score<=3: bf,bb="악재","rgba(56,139,253,.2)"
        else: bf,bb="중립","rgba(56,139,253,.15)"
        bclr=UP if score>=7 else (DN if score<=3 else B5)
        badge='<span style="background:'+bb+';color:'+bclr+';padding:2px 7px;border-radius:12px;font-size:9px;font-weight:600;font-family:JetBrains Mono">'+bf+' '+str(score)+'</span>'
    tag_html=''.join('<span style="background:'+C3+';color:'+SUB+';padding:1px 6px;border-radius:4px;font-size:9px;font-family:JetBrains Mono">#'+t+'</span>' for t in tags[:2]) if tags else ""
    return ('<a href="'+url+'" target="_blank" style="text-decoration:none">'
            '<div style="background:'+CARD+';border:1px solid '+BORD+';border-left:3px solid '+accent+';border-radius:8px;padding:14px;height:190px;display:flex;flex-direction:column">'
            '<div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:8px">'
            '<div style="font-size:12px;font-weight:600;color:'+TXT+';line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;flex:1">'+title+'</div>'
            +badge+'</div>'
            '<div style="font-size:11px;color:'+SUB+';line-height:1.5;flex:1;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical">'+body+'</div>'
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;padding-top:8px;border-top:1px solid '+BORD+'">'
            '<div style="display:flex;gap:4px">'+tag_html+'</div>'
            '<div style="display:flex;gap:8px;font-size:9px;color:'+MUT+';font-family:JetBrains Mono"><span>'+src+'</span><span>'+ds+'</span></div>'
            '</div></div></a>')

def disc_card(d):
    title=d.get("title",""); url=d.get("url","#"); filer=d.get("filer","")
    dt=d.get("date","")
    if len(dt)==8: dt=f"{dt[4:6]}-{dt[6:8]}"
    return ('<a href="'+url+'" target="_blank" style="text-decoration:none">'
            '<div style="background:'+CARD+';border:1px solid '+BORD+';border-left:3px solid '+B7+';border-radius:8px;padding:14px;min-height:90px;display:flex;flex-direction:column;justify-content:space-between">'
            '<div style="font-size:12px;font-weight:600;color:'+TXT+';line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical">'+title+'</div>'
            '<div style="display:flex;justify-content:space-between;margin-top:10px;padding-top:8px;border-top:1px solid '+BORD+';font-size:9px;color:'+MUT+';font-family:JetBrains Mono"><span>'+filer+'</span><span>'+dt+'</span></div>'
            '</div></a>')

# ════════════════════════════════════════════════════════════════
# 메인 앱
# ════════════════════════════════════════════════════════════════
def render_freshness_banner(prices_df_, live_count=0):
    """데이터 최신성 경고 배너 (개선 3)"""
    if prices_df_.empty and live_count == 0:
        st.markdown(
            '<div style="background:#3D1418;border:1px solid #F85149;border-radius:8px;'
            'padding:10px 16px;margin-bottom:.8rem;font-size:12px;color:#F85149;font-weight:600">'
            '⚠ 가격 데이터가 없습니다 — GitHub Actions 실행을 확인하세요</div>',
            unsafe_allow_html=True)
        return
    if live_count > 0:
        st.markdown(
            '<div style="background:#0D1F12;border:1px solid #3FB95044;border-radius:8px;'
            'padding:7px 16px;margin-bottom:.8rem;font-size:11px;color:#3FB950">'
            f'🟢 실시간 가격 적용 중 ({live_count}개 종목 · 3분 갱신)</div>',
            unsafe_allow_html=True)
        return
    if prices_df_.empty or "date" not in prices_df_.columns: return
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
            '— GitHub Actions 수집을 확인하세요</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="background:#131924;border:1px solid #388BFD33;border-radius:8px;'
            'padding:7px 16px;margin-bottom:.8rem;font-size:11px;color:#8B949E">'
            f'ℹ 가격 기준: {last:%Y-%m-%d} (전 거래일 종가)</div>',
            unsafe_allow_html=True)


def main():
    if "chart_range" not in st.session_state:
        st.session_state.chart_range = "3M"

    portfolio = load_portfolio()
    if not isinstance(portfolio, list): portfolio = []
    prices = load_parquet(str(PRICE_FILE))
    mdf    = load_parquet(str(MARKET_FILE))
    usdkrw = get_usdkrw(mdf)

    # 개선 1: 실시간 가격 일괄 수집
    _all_tickers = tuple(sorted({
        p.get("ticker","") for p in portfolio
        if isinstance(p,dict) and p.get("ticker")
    }))
    _live = fetch_live_prices(_all_tickers) if _all_tickers else {}
    _live_count = len(_live)

    positions_all = [compute_pos(p,prices,usdkrw,_live) for p in portfolio if isinstance(p,dict)]
    positions_all = [p for p in positions_all if p]

    # 계좌 선택
    accts_in_use = sorted({p["account"] for p in positions_all}) if positions_all else []
    acct_tabs    = ["📊 전체"] + [ACCT_LABELS.get(a,a) for a in accts_in_use]
    rev_labels   = {v:k for k,v in ACCT_LABELS.items()}

    # 개선 3: 데이터 신선도 배너
    render_freshness_banner(prices, _live_count)

    sel_idx     = st.radio("계좌 선택", acct_tabs, horizontal=True,
                            label_visibility="collapsed", key="acct_radio")
    sel_account = None if sel_idx=="📊 전체" else rev_labels.get(sel_idx, sel_idx)

    portfolio_view = portfolio if sel_account is None else [p for p in portfolio if isinstance(p,dict) and p.get("account","일반")==sel_account]
    positions      = positions_all if sel_account is None else [p for p in positions_all if p["account"]==sel_account]

    # 계좌 요약 카드 (전체 선택 시)
    if sel_account is None and accts_in_use:
        acct_cols = st.columns(len(accts_in_use))
        for col, acct in zip(acct_cols, accts_in_use):
            clr   = ACCT_COLORS.get(acct, B5)
            holds = [p for p in positions_all if p["account"]==acct]
            a_val = sum(p["value_krw"] for p in holds)
            a_pnl = sum(p["pnl_krw"]   for p in holds)
            a_tc  = sum(p.get("cost_krw",0) for p in holds)
            a_pct = (a_pnl/a_tc*100) if a_tc>0 else 0
            pclr  = UP if a_pnl>=0 else DN
            sym   = "▲" if a_pnl>=0 else "▼"
            with col:
                st.markdown(
                    '<div style="background:'+CARD+';border:1px solid '+BORD+';border-top:3px solid '+clr+';border-radius:9px;padding:12px 14px;margin-bottom:10px">'
                    +'<div style="font-size:10px;color:'+SUB+';margin-bottom:4px">'+ACCT_LABELS.get(acct,acct)+'</div>'
                    +'<div style="font-size:18px;font-weight:800;color:'+TXT+';font-family:JetBrains Mono,monospace">'+f'{a_val/1e6:.1f}'+'<span style="font-size:10px;color:'+MUT+'">M원</span></div>'
                    +'<div style="font-size:10px;color:'+pclr+';font-weight:600;font-family:JetBrains Mono,monospace;margin-top:3px">'+sym+f'{abs(a_pnl):,.0f}원 ({a_pct:+.2f}%)'+'</div>'
                    +'<div style="font-size:10px;color:'+MUT+';margin-top:2px">'+str(len(holds))+'개 종목</div>'
                    +'</div>',
                    unsafe_allow_html=True
                )

    # 헤더 + 관리
    h1,h2 = st.columns([4,1])
    with h1:
        acct_label = ACCT_LABELS.get(sel_account,"") if sel_account else ""
        st.markdown(
            '<div style="padding:14px 0 10px">'
            +'<div style="font-size:11px;color:'+SUB+';font-weight:500;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px">포트폴리오'+(f' · {acct_label}' if acct_label else '')+'</div>'
            +'<div style="font-size:26px;font-weight:700;color:'+TXT+'">투자자산 현황</div>'
            +'</div>',
            unsafe_allow_html=True
        )
    with h2:
        with st.expander("⚙️ 종목 관리"):
            manage_mode = st.selectbox("작업",
                ["신규 종목 등록","매수 기록 추가","종목 삭제"],
                key="mgmt", label_visibility="collapsed")
            if manage_mode=="신규 종목 등록":
                with st.form("nf",clear_on_submit=True):
                    n_name   = st.text_input("종목명*")
                    n_ticker = st.text_input("티커*",placeholder="005930.KS")
                    n_acct   = st.selectbox("계좌",ALL_ACCOUNTS)
                    n_curr   = st.selectbox("통화",["KRW","USD"])
                    c1,c2=st.columns(2)
                    with c1: n_sector=st.selectbox("섹터",SECTORS)
                    with c2: n_market=st.selectbox("시장",MARKETS)
                    c3,c4,c5=st.columns(3)
                    with c3: n_date=st.date_input("첫 매수일",date.today())
                    with c4: n_qty=st.number_input("수량",min_value=0.0,step=1.0)
                    with c5: n_price=st.number_input("매수가",min_value=0.0,step=100.0)
                    if st.form_submit_button("등록",type="primary") and n_name and n_ticker:
                        new={"id":str(uuid.uuid4())[:8],"name":n_name,"ticker":n_ticker,
                             "sector":n_sector,"market":n_market,"currency":n_curr,
                             "account":n_acct,"lots":[]}
                        if n_qty>0 and n_price>0:
                            new["lots"].append({"date":str(n_date),"qty":n_qty,"price":n_price,"type":"buy"})
                        portfolio.append(new); save_portfolio(portfolio)
                        st.cache_data.clear(); st.success("등록 완료!"); st.rerun()
            elif manage_mode=="매수 기록 추가" and portfolio:
                with st.form("af",clear_on_submit=True):
                    opts={f"{p['name']} [{p.get('account','일반')}]":p["id"] for p in portfolio if isinstance(p,dict)}
                    if opts:
                        sel=st.selectbox("종목",list(opts.keys()))
                        c1,c2,c3=st.columns(3)
                        with c1: a_date=st.date_input("매수일",date.today())
                        with c2: a_qty=st.number_input("수량",min_value=0.0,step=1.0)
                        with c3: a_price=st.number_input("매수가",min_value=0.0,step=100.0)
                        if st.form_submit_button("추가",type="primary") and a_qty>0 and a_price>0:
                            tid=opts[sel]
                            for p in portfolio:
                                if isinstance(p,dict) and p["id"]==tid:
                                    p.setdefault("lots",[]).append({"date":str(a_date),"qty":a_qty,"price":a_price,"type":"buy"}); break
                            save_portfolio(portfolio)
                            st.cache_data.clear(); st.success("추가 완료!"); st.rerun()
            elif manage_mode=="종목 삭제" and portfolio:
                to_del=st.selectbox("삭제할 종목",["선택..."]+[f"{p['name']} [{p.get('account','일반')}]" for p in portfolio if isinstance(p,dict)])
                if to_del!="선택..." and st.button("삭제"):
                    del_name=to_del.split(" [")[0]
                    portfolio=[p for p in portfolio if isinstance(p,dict) and p["name"]!=del_name]
                    save_portfolio(portfolio); st.cache_data.clear(); st.rerun()

    # 티커 바
    if positions:
        items_html=""
        for i,pos in enumerate(sorted(positions,key=lambda x:x.get("value_krw",0),reverse=True)[:8]):
            clr=HOLD_COLORS[i%len(HOLD_COLORS)]
            pct=pos.get("daily_pct",0); pclr=UP if pct>=0 else DN; sym="▲" if pct>=0 else "▼"
            val_str=f"{pos['value_krw']/1e8:.2f}억" if pos["value_krw"]>=1e8 else f"{pos['value_krw']/1e4:.0f}만"
            items_html+=(
                '<div style="display:flex;flex-direction:column;gap:3px;padding:9px 14px;background:'+CARD+';border:1px solid '+BORD+';border-radius:7px;min-width:150px;flex-shrink:0">'
                +'<div style="display:flex;align-items:center;gap:6px">'
                +'<span style="width:7px;height:7px;border-radius:50%;background:'+clr+';flex-shrink:0"></span>'
                +'<span style="font-size:11px;font-weight:600;color:'+TXT+';overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:110px">'+pos['name']+'</span>'
                +'</div>'
                +'<div style="display:flex;align-items:baseline;justify-content:space-between">'
                +'<span style="font-size:13px;font-weight:700;color:'+TXT+';font-family:JetBrains Mono,monospace">'+val_str+'</span>'
                +'<span style="font-size:11px;font-weight:700;color:'+pclr+';font-family:JetBrains Mono,monospace">'+sym+f'{abs(pct):.2f}%'+'</span>'
                +'</div></div>'
            )
        st.markdown(
            '<div style="display:flex;gap:7px;overflow-x:auto;padding:4px 0 12px;scrollbar-width:thin;scrollbar-color:'+BORD+' transparent">'
            +items_html+'</div>',
            unsafe_allow_html=True
        )

    df = pd.DataFrame(positions) if positions else pd.DataFrame()
    if df.empty:
        st.markdown(
            '<div style="background:'+CARD+';border:1px solid '+BORD+';border-radius:12px;padding:60px;text-align:center;margin-top:20px">'
            +'<div style="font-size:40px;margin-bottom:16px">📊</div>'
            +'<div style="font-size:18px;font-weight:600;color:'+TXT+';margin-bottom:8px">'+('이 계좌에 보유 종목 없음' if sel_account else '보유 종목 없음')+'</div>'
            +'<div style="font-size:13px;color:'+SUB+'">⚙️ 종목 관리에서 종목을 추가해주세요</div>'
            +'</div>',
            unsafe_allow_html=True
        )
        st.stop()

    # KPI 계산
    df_p  = df[df["current"].notna()] if "current" in df.columns else pd.DataFrame()
    if not df_p.empty:
        tv=df_p["value_krw"].sum(); tc_v=df_p["cost_krw"].sum()
        tp=df_p["pnl_krw"].sum(); tpct=(tp/tc_v*100) if tc_v>0 else 0
        td=df_p["daily_pnl_krw"].sum(); dpct=(td/(tv-td)*100) if (tv-td)>0 else 0
        tv_usd=tv/usdkrw
    else:
        tv=tc_v=tp=tpct=td=dpct=tv_usd=0

    # ════ 메인 레이아웃 좌:우 = 4:6 ═══════════════════════════
    left, right = st.columns([4,6], gap="large")

    # ── 왼쪽: 총 평가금액 + 구성 ─────────────────────────────
    with left:
        pclr_d = UP if td>=0 else DN; sym_d = "↑" if td>=0 else "↓"
        st.markdown(
            '<div style="font-size:11px;color:'+SUB+';letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px">총 평가금액</div>'
            +'<div style="font-size:38px;font-weight:700;line-height:1;letter-spacing:-.03em;font-family:JetBrains Mono,monospace;color:'+TXT+';margin-bottom:10px">'
            +f'{tv:,.0f}<span style="font-size:16px;color:'+SUB+';margin-left:5px">원</span></div>'
            +'<div style="font-size:13px;font-weight:600;font-family:JetBrains Mono,monospace;color:'+pclr_d+';margin-bottom:16px">'
            +sym_d+f' 전일 {td:+,.0f}원 ({dpct:+.2f}%)</div>',
            unsafe_allow_html=True
        )

        # 계좌별 배지
        if positions:
            acct_vals={}
            for p in positions:
                acct_vals[p["account"]]=acct_vals.get(p["account"],0)+p["value_krw"]
            badges=""
            for acct,val in sorted(acct_vals.items(),key=lambda x:-x[1]):
                clr=ACCT_COLORS.get(acct,B5)
                badges+=('<div style="background:'+clr+'18;border:1px solid '+clr+'44;border-radius:6px;padding:5px 10px">'
                         +'<div style="font-size:9px;color:'+clr+';font-weight:600;margin-bottom:2px">'+ACCT_LABELS.get(acct,acct)+'</div>'
                         +'<div style="font-size:12px;font-weight:700;font-family:JetBrains Mono,monospace;color:'+TXT+'">'+f'{val/1e6:.1f}M'+'</div></div>')
            st.markdown('<div style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:12px">'+badges+'</div>', unsafe_allow_html=True)

        # 레인보우 바
        df_sorted_val = df_p.sort_values("value_krw",ascending=False) if not df_p.empty else pd.DataFrame()
        if not df_sorted_val.empty and tv>0:
            segs=""
            for i,((_,row),clr) in enumerate(zip(df_sorted_val.iterrows(),HOLD_COLORS)):
                w=row["value_krw"]/tv*100
                if w>=0.5: segs+=f'<div style="width:{w:.2f}%;height:100%;background:{clr}"></div>'
            st.markdown('<div style="display:flex;height:5px;border-radius:3px;overflow:hidden;background:'+C2+';gap:1px;margin-bottom:12px">'+segs+'</div>', unsafe_allow_html=True)

        # 종목 목록 헤더
        st.markdown(
            '<div style="display:flex;padding:3px 0 5px;border-bottom:1px solid '+BORD+';gap:8px">'
            +'<span style="font-size:10px;color:'+MUT+';flex:1">종목</span>'
            +'<span style="font-size:10px;color:'+MUT+';min-width:36px;text-align:right">비중</span>'
            +'<span style="font-size:10px;color:'+MUT+';min-width:64px;text-align:right">평가금액</span>'
            +'<span style="font-size:10px;color:'+MUT+';min-width:52px;text-align:right">수익률</span>'
            +'</div>',
            unsafe_allow_html=True
        )
        for i,((_,row),clr) in enumerate(zip(df_sorted_val.iterrows(),HOLD_COLORS)):
            w=row["value_krw"]/tv*100 if tv>0 else 0
            pclr=UP if row["pnl_pct"]>=0 else DN
            sp="+" if row["pnl_pct"]>=0 else ""
            acct_clr=ACCT_COLORS.get(row.get("account","일반"),B5)
            st.markdown(
                '<div style="display:flex;align-items:center;padding:5px 0;border-bottom:1px solid '+BORD+';gap:7px">'
                +'<div style="display:flex;align-items:center;gap:6px;flex:1;min-width:0">'
                +'<span style="width:7px;height:7px;border-radius:50%;background:'+clr+';flex-shrink:0"></span>'
                +'<span style="font-size:12px;font-weight:500;color:'+TXT+';white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+str(row["name"])+'</span>'
                +'<span style="background:'+acct_clr+'22;color:'+acct_clr+';font-size:8px;padding:1px 5px;border-radius:3px;flex-shrink:0;font-weight:600">'+str(row.get("account","일반"))+'</span>'
                +'</div>'
                +'<span style="font-size:11px;color:'+SUB+';min-width:36px;text-align:right;font-family:JetBrains Mono,monospace">'+f'{w:.1f}%'+'</span>'
                +'<span style="font-size:11px;font-weight:600;color:'+TXT+';min-width:64px;text-align:right;font-family:JetBrains Mono,monospace">'+f"{row['value_krw']:,.0f}"+'</span>'
                +'<span style="font-size:11px;font-weight:700;color:'+pclr+';min-width:52px;text-align:right;font-family:JetBrains Mono,monospace">'+sp+f"{row['pnl_pct']:.2f}%"+'</span>'
                +'</div>',
                unsafe_allow_html=True
            )

        # 요약
        pclr_t=UP if tp>=0 else DN
        st.markdown(
            '<div style="display:flex;gap:18px;margin-top:12px;padding-top:12px;border-top:1px solid '+BORD+'">'
            +'<div><div style="font-size:10px;color:'+MUT+'">누적 손익</div>'
            +'<div style="font-size:14px;font-weight:700;color:'+pclr_t+';font-family:JetBrains Mono,monospace">'+f'{tp:+,.0f}원'+'</div>'
            +'<div style="font-size:10px;color:'+pclr_t+';font-family:JetBrains Mono,monospace">'+f'{tpct:+.2f}%'+'</div></div>'
            +'<div><div style="font-size:10px;color:'+MUT+'">USD 환산</div>'
            +'<div style="font-size:14px;font-weight:700;color:'+TXT+';font-family:JetBrains Mono,monospace">$'+f'{tv_usd:,.0f}'+'</div>'
            +'<div style="font-size:10px;color:'+MUT+';font-family:JetBrains Mono,monospace">₩'+f'{usdkrw:,.0f}'+'</div></div>'
            +'</div>',
            unsafe_allow_html=True
        )

    # ── 오른쪽: 계좌별 차트 (Home.py 동일 방식) ──────────────
    with right:
        _, rng_col = st.columns([1,9])
        with rng_col:
            rng = st.radio("기간",["1W","1M","3M","6M","1Y","ALL"],
                           horizontal=True, label_visibility="collapsed", key="rng")

        # 계좌별 히스토리 계산
        portfolio_json = json.dumps(portfolio_view, ensure_ascii=False)
        hist = compute_account_history(prices, mdf, portfolio_json)

        rng_cutoffs={"1W":7,"1M":30,"3M":90,"6M":180,"1Y":365}
        hist_f=(hist[hist["date"]>=pd.Timestamp.now()-pd.Timedelta(days=rng_cutoffs[rng])]
                if rng in rng_cutoffs and not hist.empty else hist)

        if not hist_f.empty and "Total" in hist_f.columns:
            acct_cols_chart=[c for c in hist_f.columns if c not in ["date","Total"]]
            for c in acct_cols_chart:
                hist_f[c]=hist_f[c].fillna(0)

            fig = go.Figure()

            # 계좌별 개별 라인
            for acct in acct_cols_chart:
                clr=ACCT_COLORS.get(acct,B5)
                lbl=ACCT_LABELS.get(acct,acct)
                d_=hist_f[["date",acct]].dropna()
                if d_[acct].sum()==0: continue
                fig.add_trace(go.Scatter(
                    x=d_["date"],y=d_[acct]/1e6,name=lbl,mode="lines",
                    line=dict(color=clr,width=1.8),
                    hovertemplate="<b>"+lbl+"</b> %{y:,.1f}M원<extra></extra>"))

            # 총합계 — 흰색 + 마커 + 면적
            fig.add_trace(go.Scatter(
                x=hist_f["date"],y=hist_f["Total"]/1e6,name="총합계",
                mode="lines+markers",
                line=dict(color="#CCCCDC",width=2),
                marker=dict(size=3.5,color=BG,line=dict(width=1.2,color="#CCCCDC")),
                fill="tozeroy",fillcolor="rgba(160,170,200,0.07)",
                hovertemplate="<b>총합계</b> %{y:,.1f}M원<extra></extra>"))

            # 고점/저점/MDD 어노테이션
            if len(hist_f)>4:
                peak_i   = hist_f["Total"].idxmax()
                trough_i = hist_f["Total"].idxmin()
                cummax_s = hist_f["Total"].cummax()
                dd_s     = (hist_f["Total"]-cummax_s)/cummax_s
                mdd_i    = dd_s.idxmin()
                anno_list=[(peak_i,"고점","#3FB950","top center"),
                           (trough_i,"저점","#F5A623","bottom center")]
                if mdd_i!=trough_i: anno_list.append((mdd_i,"MDD 저점","#F85149","bottom right"))
                for idx,label,acolor,pos in anno_list:
                    if idx not in hist_f.index: continue
                    fig.add_trace(go.Scatter(
                        x=[hist_f.loc[idx,"date"]],y=[hist_f.loc[idx,"Total"]/1e6],
                        mode="markers+text",marker=dict(size=10,color=acolor),
                        text=[label],textposition=pos,
                        textfont=dict(size=9,color=acolor,family="JetBrains Mono"),
                        showlegend=False))

            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                height=360,margin=dict(l=0,r=10,t=34,b=0),
                title=dict(text="계좌별 평가금액 추이",
                    font=dict(size=12,color=SUB,family=FF),x=0,xanchor="left"),
                legend=dict(orientation="h",y=1.06,x=0,
                    font=dict(size=10,color=SUB,family=FF),bgcolor="rgba(0,0,0,0)"),
                hovermode="x unified",
                hoverlabel=dict(bgcolor=C2,bordercolor=BORD,
                    font=dict(family="JetBrains Mono",size=10,color=TXT)),
                xaxis=dict(showgrid=False,zeroline=False,showline=False,
                    tickfont=dict(size=9,color=MUT,family="JetBrains Mono"),tickformat="%m/%d"),
                yaxis=dict(showgrid=True,gridcolor=BORD,gridwidth=0.5,
                    zeroline=False,showline=False,
                    tickfont=dict(size=9,color=MUT,family="JetBrains Mono"),ticksuffix="M")
            )
            fig.update_xaxes(showspikes=True,spikecolor=BORD,spikethickness=1)
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

            # 스탯 행
            if len(hist_f)>=2:
                v_last=float(hist_f["Total"].iloc[-1]); v_first=float(hist_f["Total"].iloc[0])
                v_peak=float(hist_f["Total"].max()); v_min=float(hist_f["Total"].min())
                mdd_pct=(v_min/v_peak-1)*100; rng_ret=(v_last/v_first-1)*100
                stat_c=st.columns(4)
                for col,(lbl,val,sc) in zip(stat_c,[
                    ("기간 수익",f"{rng_ret:+.2f}%",UP if rng_ret>=0 else DN),
                    ("현재 평가",f"{v_last/1e6:.1f}M",TXT),
                    ("기간 최고",f"{v_peak/1e6:.1f}M",TXT),
                    ("MDD",f"{mdd_pct:.2f}%",DN),
                ]):
                    with col:
                        st.markdown(
                            '<div style="background:'+CARD+';border:1px solid '+BORD+';border-radius:7px;padding:9px 11px">'
                            +'<div style="font-size:9px;color:'+SUB+';text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">'+lbl+'</div>'
                            +'<div style="font-size:14px;font-weight:700;color:'+sc+';font-family:JetBrains Mono,monospace">'+val+'</div>'
                            +'</div>',
                            unsafe_allow_html=True
                        )
        else:
            st.markdown('<div style="background:'+CARD+';border:1px solid '+BORD+';border-radius:8px;height:300px;display:flex;align-items:center;justify-content:center;font-size:13px;color:'+MUT+'">수집된 히스토리 데이터가 없습니다</div>', unsafe_allow_html=True)

    # ── 하단 KPI 스트립 ───────────────────────────────────────
    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
    kpi_items=[
        ("누적 평가손익",f"{tp:+,.0f}원",f"{tpct:+.2f}%",UP if tp>=0 else DN),
        ("매입 원가",f"{tc_v:,.0f}원","투자 원금",SUB),
        ("전일 평가손익",f"{td:+,.0f}원",f"{dpct:+.2f}%",UP if td>=0 else DN),
        ("USD/KRW",f"{usdkrw:,.1f}","현재 환율",SUB),
        ("USD 환산",f"${tv_usd:,.0f}","포트폴리오",SUB),
    ]
    ks_cols=st.columns(5)
    for col,(lbl,val,sub_,clr) in zip(ks_cols,kpi_items):
        with col:
            st.markdown(
                '<div style="background:'+CARD+';border:1px solid '+BORD+';border-radius:9px;padding:14px 16px">'
                +'<div style="font-size:10px;color:'+SUB+';text-transform:uppercase;letter-spacing:.04em;margin-bottom:5px">'+lbl+'</div>'
                +'<div style="font-size:18px;font-weight:800;color:'+TXT+';font-family:JetBrains Mono,monospace;line-height:1;margin-bottom:3px">'+val+'</div>'
                +'<div style="font-size:11px;color:'+clr+';font-weight:600">'+sub_+'</div>'
                +'</div>',
                unsafe_allow_html=True
            )

    # ── 탭 ───────────────────────────────────────────────────
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    t1,t2,t3,t4 = st.tabs(["📋 상세 테이블","📰 뉴스","📑 공시","📊 리스크"])

    with t1:
        df_sorted=df.sort_values("value_krw",ascending=False) if not df.empty else pd.DataFrame()
        rows_html=""
        TH=f"padding:.6rem 1rem;text-align:left;font-size:10px;color:{MUT};font-weight:500;border-bottom:1px solid {BORD};text-transform:uppercase;letter-spacing:.04em"
        for i,(_,r) in enumerate(df_sorted.iterrows()):
            clr=HOLD_COLORS[i%len(HOLD_COLORS)]
            pclr=UP if r["pnl_pct"]>=0 else DN
            dclr=UP if r["daily_pct"]>=0 else DN
            cv=f"{r['current']:,.2f}" if r["current"] else "—"
            wt=(r["value_krw"]/tv*100) if tv>0 else 0
            a_clr=ACCT_COLORS.get(r.get("account","일반"),B5)
            rows_html+=(
                '<tr style="border-bottom:1px solid '+BORD+'">'
                +'<td style="padding:.7rem 1rem"><div style="display:flex;align-items:center;gap:8px">'
                +'<span style="width:8px;height:8px;border-radius:50%;background:'+clr+';flex-shrink:0"></span>'
                +'<div><div style="font-size:12px;font-weight:600;color:'+TXT+'">'+str(r['name'])+'</div>'
                +'<div style="font-size:9px;color:'+MUT+';font-family:JetBrains Mono,monospace">'+str(r['ticker'])+'</div></div></div></td>'
                +'<td style="padding:.7rem 1rem;text-align:center"><span style="background:'+a_clr+'22;color:'+a_clr+';padding:2px 7px;border-radius:5px;font-size:9px;font-weight:700">'+str(r.get('account','일반'))+'</span></td>'
                +'<td style="padding:.7rem 1rem;text-align:right;font-family:JetBrains Mono,monospace;font-size:12px;color:'+TXT+'">'+f"{r['qty']:,.0f}"+'</td>'
                +'<td style="padding:.7rem 1rem;text-align:right;font-family:JetBrains Mono,monospace;font-size:12px;color:'+TXT+'">'+f"{r['avg_cost']:,.2f}"+'</td>'
                +'<td style="padding:.7rem 1rem;text-align:right"><div style="font-family:JetBrains Mono,monospace;font-size:12px;color:'+TXT+'">'+cv+'</div>'
                +'<div style="font-size:10px;color:'+dclr+';font-weight:600">'+f"{r['daily_pct']:+.2f}%"+'</div></td>'
                +'<td style="padding:.7rem 1rem;text-align:right"><div style="font-family:JetBrains Mono,monospace;font-size:13px;font-weight:700;color:'+TXT+'">'+f"{r['value_krw']:,.0f}"+'</div>'
                +'<div style="font-size:10px;color:'+SUB+'">'+f"{wt:.1f}%"+'</div></td>'
                +'<td style="padding:.7rem 1rem;text-align:right"><div style="font-family:JetBrains Mono,monospace;font-size:13px;font-weight:700;color:'+pclr+'">'+f"{r['pnl_krw']:+,.0f}"+'</div>'
                +'<div style="font-size:10px;color:'+pclr+'">'+f"{r['pnl_pct']:+.2f}%"+'</div></td>'
                +'</tr>'
            )
        st.markdown(
            '<div style="background:'+CARD+';border:1px solid '+BORD+';border-radius:12px;overflow:hidden;margin-top:8px">'
            +'<table style="width:100%;border-collapse:collapse">'
            +'<thead><tr style="background:'+C2+'">'
            +'<th style="'+TH+'">종목</th><th style="'+TH+';text-align:center">계좌</th>'
            +'<th style="'+TH+';text-align:right">수량</th><th style="'+TH+';text-align:right">평균단가</th>'
            +'<th style="'+TH+';text-align:right">현재가·일간</th><th style="'+TH+';text-align:right">평가금액(비중)</th>'
            +'<th style="'+TH+';text-align:right">평가손익</th>'
            +'</tr></thead><tbody>'+rows_html+'</tbody></table></div>',
            unsafe_allow_html=True
        )

    with t2:
        news_data=load_json(NEWS_FILE,{}); stocks_news=news_data.get("stocks",{})
        ordered=[(r["name"],stocks_news[r["name"]]) for _,r in df_sorted.iterrows()
                 if isinstance(stocks_news,dict) and r["name"] in stocks_news and stocks_news[r["name"]]]
        if not ordered:
            st.markdown('<div style="color:'+SUB+';font-size:13px;padding:20px">수집된 종목 뉴스가 없습니다.</div>', unsafe_allow_html=True)
        else:
            for i,(name,articles) in enumerate(ordered):
                clr=HOLD_COLORS[i%len(HOLD_COLORS)]
                st.markdown('<div style="display:flex;align-items:center;gap:8px;padding:10px 0 8px"><span style="width:8px;height:8px;border-radius:50%;background:'+clr+'"></span><span style="font-size:13px;font-weight:700;color:'+TXT+'">'+name+'</span></div>', unsafe_allow_html=True)
                cols=st.columns(3)
                for col,n in zip(cols,articles[:3]):
                    with col: st.markdown(news_card(n,accent=clr),unsafe_allow_html=True)

    with t3:
        disc_data=load_json(DISC_FILE,{}); discs=disc_data.get("disclosures",{})
        ordered_d=[(r["name"],discs[r["name"]]) for _,r in df_sorted.iterrows()
                   if isinstance(discs,dict) and r["name"] in discs and discs[r["name"]]]
        if not ordered_d:
            st.markdown('<div style="color:'+SUB+';font-size:13px;padding:20px">최근 14일간 공시 내역이 없습니다.</div>', unsafe_allow_html=True)
        else:
            for i,(name,items_) in enumerate(ordered_d):
                clr=HOLD_COLORS[i%len(HOLD_COLORS)]
                st.markdown('<div style="display:flex;align-items:center;gap:8px;padding:10px 0 8px"><span style="width:8px;height:8px;border-radius:50%;background:'+clr+'"></span><span style="font-size:13px;font-weight:700;color:'+TXT+'">'+name+'</span><span style="font-size:10px;color:'+MUT+'">'+str(len(items_))+'건</span></div>', unsafe_allow_html=True)
                cols=st.columns(3)
                for j,d_ in enumerate(items_[:6]):
                    with cols[j%3]: st.markdown(disc_card(d_),unsafe_allow_html=True)

    with t4:
        if prices.empty or len(positions)<2:
            st.markdown('<div style="background:'+CARD+';border:1px solid '+BORD+';border-radius:12px;padding:40px;text-align:center"><div style="font-size:14px;color:'+SUB+'">종목이 2개 이상 등록되고 가격 데이터가 수집된 후 확인 가능합니다</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:14px;font-weight:600;color:'+SUB+';margin:1rem 0 10px">리스크 지표 요약</div>', unsafe_allow_html=True)
            risk_rows=""
            for i,pos in enumerate(sorted(positions,key=lambda x:x.get("value_krw",0),reverse=True)):
                clr=HOLD_COLORS[i%len(HOLD_COLORS)]; t_=pos["ticker"]; is_usd=pos["currency"]=="USD"
                beta=calc_beta(t_,is_usd,prices,mdf); vol=calc_vol(t_,prices)
                mdd_v=calc_mdd(t_,prices); sh=calc_sharpe(t_,prices)
                b_html=badge_html(beta,(0.8,1.3),"{:.2f}")
                v_html=badge_html(vol,(20,35),"{:.1f}%",reverse=True)
                m_html=('<span style="color:'+DN+';font-weight:700;font-family:JetBrains Mono">'+f'{mdd_v:.1f}%'+'</span>' if mdd_v else '<span style="color:'+MUT+'">—</span>')
                sh_html=badge_html(sh,(0,1),"{:.2f}")
                TH_S=f"padding:.6rem 1rem;font-size:10px;color:{MUT};font-weight:500;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid {BORD};text-align:center"
                risk_rows+=('<tr style="border-bottom:1px solid '+BORD+'">'
                    +'<td style="padding:.7rem 1rem"><div style="display:flex;align-items:center;gap:8px">'
                    +'<span style="width:8px;height:8px;border-radius:50%;background:'+clr+';flex-shrink:0"></span>'
                    +'<div><div style="font-size:12px;font-weight:600;color:'+TXT+'">'+pos['name']+'</div>'
                    +'<div style="font-size:9px;color:'+MUT+';font-family:JetBrains Mono,monospace">'+t_+'</div></div></div></td>'
                    +'<td style="padding:.7rem 1rem;text-align:center">'+b_html+'</td>'
                    +'<td style="padding:.7rem 1rem;text-align:center">'+v_html+'</td>'
                    +'<td style="padding:.7rem 1rem;text-align:center">'+m_html+'</td>'
                    +'<td style="padding:.7rem 1rem;text-align:center">'+sh_html+'</td>'
                    +'</tr>')
            TH_S=f"padding:.6rem 1rem;font-size:10px;color:{MUT};font-weight:500;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid {BORD};text-align:center"
            st.markdown(
                '<div style="background:'+CARD+';border:1px solid '+BORD+';border-radius:12px;overflow:hidden">'
                +'<table style="width:100%;border-collapse:collapse">'
                +'<thead><tr style="background:'+C2+'">'
                +'<th style="'+TH_S+';text-align:left">종목</th>'
                +'<th style="'+TH_S+'">베타<br><span style="font-size:8px;font-weight:400">90일</span></th>'
                +'<th style="'+TH_S+'">변동성<br><span style="font-size:8px;font-weight:400">60일·연환산</span></th>'
                +'<th style="'+TH_S+'">MDD<br><span style="font-size:8px;font-weight:400">최대낙폭</span></th>'
                +'<th style="'+TH_S+'">샤프비율<br><span style="font-size:8px;font-weight:400">90일</span></th>'
                +'</tr></thead><tbody>'+risk_rows+'</tbody></table></div>',
                unsafe_allow_html=True
            )
            st.markdown('<div style="background:'+C2+';border:1px solid '+BORD+';border-radius:8px;padding:10px 14px;font-size:10px;color:'+SUB+';margin-top:8px;display:flex;gap:16px;flex-wrap:wrap">'
                +'<span>📊 <b style="color:'+TXT+'">베타</b> &lt;0.8 방어 · 0.8~1.3 중립 · &gt;1.3 공격</span>'
                +'<span>📉 <b style="color:'+TXT+'">변동성</b> &lt;20% 안정 · 20~35% 보통 · &gt;35% 고위험</span>'
                +'<span>⭐ <b style="color:'+TXT+'">샤프</b> &lt;0 손실 · 0~1 보통 · &gt;1 우수</span>'
                +'</div>', unsafe_allow_html=True)

            # 상관관계 매트릭스
            st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:14px;font-weight:600;color:'+SUB+';margin-bottom:10px">상관관계 매트릭스</div>', unsafe_allow_html=True)
            all_tickers=[p["ticker"] for p in positions]; names_map={p["ticker"]:p["name"] for p in positions}
            pivot=prices[prices["ticker"].isin(all_tickers)].pivot_table(index="date",columns="ticker",values="close")
            ret_mat=pivot.pct_change().dropna()
            if len(ret_mat.columns)>=2 and len(ret_mat)>=10:
                corr=ret_mat.corr()
                corr.columns=[names_map.get(t,t) for t in corr.columns]
                corr.index=[names_map.get(t,t) for t in corr.index]
                fig_c=go.Figure(go.Heatmap(z=corr.values,x=list(corr.columns),y=list(corr.index),
                    colorscale=[[0,"#1F6FEB"],[0.5,CARD],[1,"#E24B4A"]],zmin=-1,zmax=1,
                    text=[[f"{v:.2f}" for v in row] for row in corr.values],texttemplate="%{text}",
                    textfont={"size":11,"color":TXT,"family":"JetBrains Mono"},
                    colorbar=dict(thickness=10,tickfont=dict(color=MUT,size=9),bgcolor="rgba(0,0,0,0)")))
                fig_c.update_layout(paper_bgcolor=CARD,plot_bgcolor=CARD,height=max(280,len(corr)*60),
                    margin=dict(l=8,r=60,t=8,b=8),font=dict(family="JetBrains Mono",size=10,color=MUT),
                    xaxis=dict(tickfont=dict(size=10,color=TXT),tickangle=-30),yaxis=dict(tickfont=dict(size=10,color=TXT)))
                st.plotly_chart(fig_c,use_container_width=True)

            # 롤링 변동성
            st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:14px;font-weight:600;color:'+SUB+';margin-bottom:10px">롤링 변동성 추이 (30일 연환산)</div>', unsafe_allow_html=True)
            fig_v=go.Figure()
            for i,pos in enumerate(positions):
                sub=prices[prices["ticker"]==pos["ticker"]].sort_values("date").copy()
                if len(sub)<35: continue
                sub["ret"]=sub["close"].pct_change(); sub["vol"]=sub["ret"].rolling(30).std()*np.sqrt(252)*100
                sub=sub.dropna(subset=["vol"])
                if sub.empty: continue
                fig_v.add_trace(go.Scatter(x=sub["date"],y=sub["vol"],name=pos["name"],line=dict(color=HOLD_COLORS[i%len(HOLD_COLORS)],width=2)))
            fig_v.add_hline(y=20,line_dash="dash",line_color=SUB,line_width=1,annotation_text="20% 경계",annotation_font_color=SUB,annotation_font_size=9)
            fig_v.update_layout(paper_bgcolor=CARD,plot_bgcolor=CARD,height=260,margin=dict(l=8,r=8,t=8,b=8),
                legend=dict(orientation="h",y=1.1,x=0,font=dict(size=10,color=SUB),bgcolor="rgba(0,0,0,0)"),
                hovermode="x unified",xaxis=dict(showgrid=False,tickfont=dict(size=9,color=MUT)),
                yaxis=dict(showgrid=True,gridcolor=BORD,ticksuffix="%",tickfont=dict(size=9,color=MUT)))
            st.plotly_chart(fig_v,use_container_width=True)

    st.markdown(
        '<div style="margin-top:2rem;padding:10px 0;border-top:1px solid '+BORD+';font-size:10px;color:'+MUT+';font-family:JetBrains Mono,monospace;display:flex;justify-content:space-between">'
        +'<span>가격 갱신: '+(prices["date"].max().strftime("%Y-%m-%d") if not prices.empty else "—")+'  ·  USD/KRW: '+f'{usdkrw:,.1f}'+'</span>'
        +'<span>'+now_str+'</span></div>',
        unsafe_allow_html=True
    )

now_str = datetime.now().strftime("%Y-%m-%d %H:%M") + " KST"
main()
