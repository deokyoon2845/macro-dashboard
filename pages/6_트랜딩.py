"""
6_트렌딩.py — 오늘의 시장 통찰 (QLD 스타일 v2)
시장폭 · 섹터 자금흐름 · 내 포트 연관 · 거래량배수 · 등락률 · 뉴스 · AI브리핑
"""
import streamlit as st
import pandas as pd
import json, base64, os, re, sys
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="트렌딩", page_icon="🔥",
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

BG   = "#07090F"; CARD = "#0D1117"; C2   = "#131924"; C3   = "#1A2233"
BORD = "#1E2433"; BORD2= "#2D3748"; TXT  = "#EAEEF2"; SUB  = "#8B949E"; MUT  = "#484F58"
UP   = "#E24B4A"; DN = "#388BFD"
B5   = "#388BFD"; B3 = "#79C0FF"; GOLD = "#D4A017"; GREEN = "#3FB950"

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
label{{color:{TXT}!important}}
[data-testid="collapsedControl"]{{background:{CARD}!important;border:2px solid {B5}!important;border-left:none!important;border-radius:0 10px 10px 0!important;width:2.4rem!important;top:.8rem!important;box-shadow:4px 0 14px rgba(56,139,253,.35)!important}}
[data-testid="collapsedControl"]:hover{{background:{C2}!important}}
[data-testid="collapsedControl"] svg{{color:{B5}!important;fill:{B5}!important}}
.stButton>button{{background:transparent!important;color:{SUB}!important;border:1px solid {BORD}!important;border-radius:6px!important;font-family:{FF}!important;font-size:12px!important;font-weight:500!important;padding:5px 14px!important;box-shadow:none!important}}
.stButton>button:hover{{border-color:{B5}!important;color:{B5}!important;background:{C2}!important}}
.qld-divider{{height:1px;background:{BORD};margin:1.2rem 0}}
::-webkit-scrollbar{{width:3px;height:3px}}
::-webkit-scrollbar-thumb{{background:{BORD2};border-radius:2px}}
</style>""",
    unsafe_allow_html=True
)

def safe(v):
    import html as _h
    return _h.escape(str(v)) if v else ""

def load_json(fn, default):
    p = DATA / fn
    if not p.exists(): return default
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except: return default

def get_secret(k, default=""):
    try: return st.secrets[k]
    except: return os.environ.get(k, default)

# ════════════════════════════════════════════════════════════════
# 데이터 로드
# ════════════════════════════════════════════════════════════════
trending  = load_json("trending.json", {})
updated   = trending.get("updated", "")
portfolio = load_json("portfolio.json", [])
# 내 보유 섹터 집합
my_sectors = {p.get("sector","") for p in portfolio if isinstance(p,dict) and p.get("sector")}
my_names   = {p.get("name","")   for p in portfolio if isinstance(p,dict)}

# 실시간 보완
@st.cache_data(ttl=180)
def refresh_live(codes_tuple):
    import yfinance as yf
    out = {}
    for code in codes_tuple:
        if not code: continue
        for suffix in (".KS", ".KQ"):
            try:
                fi = yf.Ticker(code+suffix).fast_info
                cur  = fi.get("lastPrice") or fi.get("last_price")
                prev = fi.get("previousClose") or fi.get("previous_close")
                if cur and prev:
                    out[code]={"price":float(cur),"change_pct":(float(cur)/float(prev)-1)*100}
                    break
            except: continue
    return out

# ════════════════════════════════════════════════════════════════
# 헤더
# ════════════════════════════════════════════════════════════════
hc1, hc2 = st.columns([4,1])
with hc1:
    st.markdown(
        '<div style="padding:14px 0 6px">'
        + '<div style="font-size:11px;color:'+SUB+';text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px">오늘의 시장 통찰</div>'
        + '<div style="font-size:26px;font-weight:800;color:'+TXT+'">🔥 트렌딩</div>'
        + '</div>',
        unsafe_allow_html=True
    )
with hc2:
    live_on = st.toggle("실시간 보완", value=False, key="live_toggle",
                        help="yfinance로 현재가 재조회 (느려질 수 있음)")

if not trending or not trending.get("volume_surge"):
    st.markdown('<div style="background:#3D1418;border:1px solid #F85149;border-radius:8px;padding:10px 16px;margin-bottom:.8rem;font-size:12px;color:#F85149;font-weight:600">⚠ 트렌딩 데이터가 없습니다 — src/fetch_trending.py 실행 또는 GitHub Actions를 확인하세요</div>', unsafe_allow_html=True)
    st.stop()

st.markdown(
    '<div style="background:'+C2+';border:1px solid '+BORD+';border-radius:8px;padding:7px 16px;margin-bottom:1rem;font-size:11px;color:'+MUT+';font-family:JetBrains Mono,monospace">수집 기준: '+safe(updated)+' KST'+('  ·  🟢 실시간 보완 ON' if live_on else '')+'</div>',
    unsafe_allow_html=True
)

live_map = {}
if live_on:
    all_codes = tuple({s.get("code","") for s in
                       (trending.get("volume_surge",[])+trending.get("rising",[])+trending.get("falling",[]))
                       if s.get("code")})
    with st.spinner("실시간 가격 보완 중…"):
        live_map = refresh_live(all_codes)

def merged(stock):
    code = stock.get("code","")
    if code in live_map:
        return {**stock, "price":live_map[code]["price"], "change_pct":live_map[code]["change_pct"]}
    return stock

# ════════════════════════════════════════════════════════════════
# 1. 시장 폭 요약 (4순위) — 최상단 한 줄 통찰
# ════════════════════════════════════════════════════════════════
breadth = trending.get("breadth", {})
if breadth:
    regime   = breadth.get("regime","중립")
    up_n     = breadth.get("up_count",0)
    down_n   = breadth.get("down_count",0)
    vol_avg  = breadth.get("vol_avg_change",0)
    total_n  = up_n + down_n
    up_ratio = (up_n/total_n*100) if total_n>0 else 50
    reg_clr  = UP if "위험선호" in regime else (DN if "위험회피" in regime else SUB)
    st.markdown(
        '<div style="background:'+CARD+';border:1px solid '+BORD+';border-left:4px solid '+reg_clr+';border-radius:10px;padding:16px 20px;margin-bottom:1rem">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">'
        + '<div><div style="font-size:10px;color:'+MUT+';text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px">오늘 시장 레짐</div>'
        + '<div style="font-size:20px;font-weight:800;color:'+reg_clr+'">'+safe(regime)+'</div></div>'
        + '<div style="display:flex;gap:24px">'
        + '<div style="text-align:right"><div style="font-size:10px;color:'+MUT+'">상승 우세 종목</div><div style="font-size:18px;font-weight:700;color:'+UP+';font-family:JetBrains Mono,monospace">'+str(up_n)+'</div></div>'
        + '<div style="text-align:right"><div style="font-size:10px;color:'+MUT+'">하락 우세 종목</div><div style="font-size:18px;font-weight:700;color:'+DN+';font-family:JetBrains Mono,monospace">'+str(down_n)+'</div></div>'
        + '<div style="text-align:right"><div style="font-size:10px;color:'+MUT+'">거래량主 평균등락</div><div style="font-size:18px;font-weight:700;color:'+(UP if vol_avg>=0 else DN)+';font-family:JetBrains Mono,monospace">'+f'{vol_avg:+.2f}%'+'</div></div>'
        + '</div></div>'
        # 상승/하락 비율 바
        + '<div style="display:flex;height:5px;border-radius:3px;overflow:hidden;background:'+C2+';margin-top:12px">'
        + '<div style="width:'+f'{up_ratio:.0f}'+'%;background:'+UP+'"></div>'
        + '<div style="flex:1;background:'+DN+'"></div></div>'
        + '</div>',
        unsafe_allow_html=True
    )

# ════════════════════════════════════════════════════════════════
# 2. 섹터 자금 흐름 (1순위)
# ════════════════════════════════════════════════════════════════
st.markdown('<div style="font-size:11px;color:'+MUT+';text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">🌊 섹터 자금 흐름 <span style="color:'+MUT+';text-transform:none;letter-spacing:0">— 오늘 돈이 어디로 들어오고 나가는가</span></div>', unsafe_allow_html=True)

sector_flow = trending.get("sector_flow", [])
if sector_flow:
    max_score = max((abs(s.get("score",0)) for s in sector_flow), default=1) or 1
    rows = ""
    for s in sector_flow:
        sec   = s.get("sector","")
        score = s.get("score",0)
        up    = score >= 0
        clr   = UP if up else DN
        w     = min(abs(score)/max_score*100, 100)
        is_mine = sec in my_sectors
        mine_tag = ('<span style="background:'+GREEN+'22;color:'+GREEN+';font-size:8px;padding:1px 6px;border-radius:4px;margin-left:6px;font-weight:700">내 보유</span>') if is_mine else ""
        left_bar  = ('<div style="height:13px;width:'+f'{w}'+'%;background:'+DN+';border-radius:3px 0 0 3px"></div>') if not up else ""
        right_bar = ('<div style="height:13px;width:'+f'{w}'+'%;background:'+UP+';border-radius:0 3px 3px 0"></div>') if up else ""
        rows += (
            '<div style="display:flex;align-items:center;gap:12px;padding:6px 0;'+('background:'+GREEN+'08;border-radius:6px;' if is_mine else '')+'">'
            + '<div style="width:130px;flex-shrink:0;font-size:13px;font-weight:600;color:'+TXT+'">'+safe(sec)+mine_tag+'</div>'
            + '<div style="flex:1;display:flex;align-items:center;height:16px">'
            + '<div style="flex:1;display:flex;justify-content:flex-end">'+left_bar+'</div>'
            + '<div style="width:1px;height:16px;background:'+BORD+'"></div>'
            + '<div style="flex:1;display:flex;justify-content:flex-start">'+right_bar+'</div>'
            + '</div>'
            + '<div style="width:90px;flex-shrink:0;text-align:right;font-size:11px;color:'+MUT+';font-family:JetBrains Mono,monospace">↑'+str(s.get("up",0))+' ↓'+str(s.get("down",0))+'</div>'
            + '</div>'
        )
    st.markdown('<div style="background:'+CARD+';border:1px solid '+BORD+';border-radius:10px;padding:14px 18px">'+rows+'</div>', unsafe_allow_html=True)
else:
    st.markdown('<div style="color:'+MUT+';font-size:12px;padding:14px">섹터 데이터 없음</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 3. 내 포트폴리오 연관 신호 (2순위)
# ════════════════════════════════════════════════════════════════
all_trend = []
for key in ("volume_surge","rising","falling"):
    for s in trending.get(key, []):
        all_trend.append({**s, "_src":key})
# 내 섹터 or 내 종목과 겹치는 트렌딩
related = []
seen = set()
for s in all_trend:
    nm = s.get("name","")
    if nm in seen: continue
    seen.add(nm)
    sec = s.get("sector","")
    if sec in my_sectors or nm in my_names:
        related.append(merged(s))

if related:
    st.markdown('<div class="qld-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:'+GREEN+';text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">🎯 내 포트폴리오 연관 신호 <span style="color:'+MUT+';text-transform:none;letter-spacing:0">— 내 자산과 같은 섹터에서 움직임 포착</span></div>', unsafe_allow_html=True)
    cards = ""
    for s in related[:8]:
        pct = s.get("change_pct",0)
        clr = UP if pct>=0 else DN; sym = "▲" if pct>=0 else "▼"
        is_held = s.get("name","") in my_names
        held_tag = ('<span style="background:'+GREEN+'22;color:'+GREEN+';font-size:8px;padding:1px 5px;border-radius:3px;font-weight:700">보유중</span>') if is_held else ('<span style="background:'+B5+'22;color:'+B5+';font-size:8px;padding:1px 5px;border-radius:3px">'+safe(s.get("sector",""))+'</span>')
        cards += (
            '<div style="background:'+CARD+';border:1px solid '+(GREEN+'44' if is_held else BORD)+';border-radius:8px;padding:11px 13px">'
            + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">'
            + '<span style="font-size:12px;font-weight:600;color:'+TXT+';white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100px">'+safe(s.get("name",""))+'</span>'
            + held_tag + '</div>'
            + '<div style="display:flex;justify-content:space-between;align-items:baseline">'
            + '<span style="font-size:10px;color:'+SUB+';font-family:JetBrains Mono,monospace">'+f'{s.get("price",0):,}원'+'</span>'
            + '<span style="font-size:14px;font-weight:700;color:'+clr+';font-family:JetBrains Mono,monospace">'+sym+f'{abs(pct):.2f}%'+'</span>'
            + '</div></div>'
        )
    st.markdown('<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">'+cards+'</div>', unsafe_allow_html=True)

st.markdown('<div class="qld-divider"></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 4. 거래량 급증 (배수)
# ════════════════════════════════════════════════════════════════
st.markdown('<div style="font-size:11px;color:'+MUT+';text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">📊 거래량 급증 <span style="color:'+MUT+';text-transform:none;letter-spacing:0">— 평소 대비 거래량 배수</span></div>', unsafe_allow_html=True)
vol = [merged(s) for s in trending.get("volume_surge", [])]
if vol:
    cards = ""
    for s in vol[:12]:
        pct = s.get("change_pct",0)
        clr = UP if pct>=0 else DN; sym = "▲" if pct>=0 else "▼"
        ratio = s.get("vol_ratio")
        rbar = min((ratio or 0)/5*100, 100) if ratio else 0
        ratio_str = f'{ratio:.1f}배' if ratio else '—'
        ratio_clr = UP if (ratio and ratio>=3) else (GOLD if (ratio and ratio>=1.5) else SUB)
        cards += (
            '<div style="background:'+CARD+';border:1px solid '+BORD+';border-radius:8px;padding:11px 13px">'
            + '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px">'
            + '<span style="font-size:12px;font-weight:600;color:'+TXT+';white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100px">'+safe(s.get("name",""))+'</span>'
            + '<span style="font-size:11px;font-weight:700;font-family:JetBrains Mono,monospace;color:'+clr+'">'+sym+f'{abs(pct):.2f}%'+'</span>'
            + '</div>'
            + '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px">'
            + '<span style="font-size:10px;color:'+SUB+';font-family:JetBrains Mono,monospace">'+f'{s.get("price",0):,}원'+'</span>'
            + '<span style="font-size:13px;font-weight:800;font-family:JetBrains Mono,monospace;color:'+ratio_clr+'">'+ratio_str+'</span>'
            + '</div>'
            + '<div style="height:4px;background:'+C2+';border-radius:2px;overflow:hidden"><div style="height:100%;width:'+f'{rbar:.0f}'+'%;background:'+ratio_clr+'"></div></div>'
            + '<div style="font-size:9px;color:'+MUT+';font-family:JetBrains Mono,monospace;margin-top:3px">평소 대비 거래량</div>'
            + '</div>'
        )
    st.markdown('<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">'+cards+'</div>', unsafe_allow_html=True)

st.markdown('<div class="qld-divider"></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 5. 등락률 상위/하위
# ════════════════════════════════════════════════════════════════
def render_diverging(stocks, scale=None):
    if not stocks:
        st.markdown('<div style="color:'+MUT+';font-size:12px;padding:14px">데이터 없음</div>', unsafe_allow_html=True); return
    stocks=[merged(s) for s in stocks]
    if scale is None: scale=max(4.0, max(abs(s.get("change_pct",0)) for s in stocks))
    body=""
    for s in stocks:
        pct=s.get("change_pct",0); up=pct>=0; clr=UP if up else DN
        w=min(abs(pct)/scale*100,100); sym="▲" if up else "▼"
        lb=('<div style="height:11px;width:'+f'{w}'+'%;background:'+DN+';border-radius:3px 0 0 3px"></div>') if not up else ""
        rb=('<div style="height:11px;width:'+f'{w}'+'%;background:'+UP+';border-radius:0 3px 3px 0"></div>') if up else ""
        body+=('<div style="display:flex;align-items:center;gap:10px;padding:5px 0">'
            +'<div style="width:130px;flex-shrink:0;overflow:hidden"><div style="font-size:12px;font-weight:500;color:'+TXT+';white-space:nowrap;text-overflow:ellipsis;overflow:hidden">'+safe(s.get("name",""))+'</div>'
            +'<div style="font-size:9px;color:'+MUT+';font-family:JetBrains Mono,monospace">'+f'{s.get("price",0):,}'+'</div></div>'
            +'<div style="flex:1;display:flex;align-items:center;height:14px"><div style="flex:1;display:flex;justify-content:flex-end">'+lb+'</div><div style="width:1px;height:14px;background:'+BORD+'"></div><div style="flex:1;display:flex;justify-content:flex-start">'+rb+'</div></div>'
            +'<div style="width:56px;flex-shrink:0;text-align:right;font-size:12px;font-weight:700;font-family:JetBrains Mono,monospace;color:'+clr+'">'+sym+f'{abs(pct):.2f}%'+'</div></div>')
    st.markdown('<div style="background:'+CARD+';border:1px solid '+BORD+';border-radius:10px;padding:14px 16px">'+body+'</div>', unsafe_allow_html=True)

lc, rc = st.columns(2, gap="large")
with lc:
    st.markdown('<div style="font-size:11px;color:'+UP+';text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">▲ 상승률 상위</div>', unsafe_allow_html=True)
    render_diverging(trending.get("rising", [])[:10])
with rc:
    st.markdown('<div style="font-size:11px;color:'+DN+';text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">▼ 하락률 상위</div>', unsafe_allow_html=True)
    render_diverging(trending.get("falling", [])[:10])

st.markdown('<div class="qld-divider"></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 6. 뉴스 언급 + 불일치 신호 (3순위)
# ════════════════════════════════════════════════════════════════
st.markdown('<div style="font-size:11px;color:'+MUT+';text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">📰 뉴스 언급 많은 종목 <span style="color:'+MUT+';text-transform:none;letter-spacing:0">— 관심 집중 + 가격 불일치 포착</span></div>', unsafe_allow_html=True)

news_rank = trending.get("news_ranking", [])
# 거래량/등락 데이터와 종목명으로 조인 → 불일치 신호
trend_by_name = {}
for key in ("volume_surge","rising","falling"):
    for s in trending.get(key, []):
        trend_by_name[s.get("name","")] = merged(s)

if news_rank:
    max_cnt = max((n.get("news_count",0) for n in news_rank), default=1) or 1
    rows=""
    for i,n in enumerate(news_rank[:10]):
        nm=n.get("name",""); cnt=n.get("news_count",0)
        wbar=min(cnt/max_cnt*100,100)
        # 불일치 신호: 뉴스 많은데 주가 하락 / 거래량 터졌는데 뉴스 적음
        signal=""; t=trend_by_name.get(nm)
        if t:
            pct=t.get("change_pct",0); ratio=t.get("vol_ratio")
            if cnt>=max_cnt*0.5 and pct<-1:
                signal='<span style="background:'+DN+'22;color:'+DN+';font-size:8px;padding:1px 6px;border-radius:4px;font-weight:700">뉴스↑ 주가↓ 악재소화</span>'
            elif ratio and ratio>=3 and cnt<max_cnt*0.2:
                signal='<span style="background:'+GOLD+'22;color:'+GOLD+';font-size:8px;padding:1px 6px;border-radius:4px;font-weight:700">조용한 급등 주목</span>'
            elif cnt>=max_cnt*0.5 and pct>1:
                signal='<span style="background:'+UP+'22;color:'+UP+';font-size:8px;padding:1px 6px;border-radius:4px;font-weight:700">뉴스↑ 주가↑ 모멘텀</span>'
        rows+=('<div style="display:flex;align-items:center;gap:12px;padding:7px 0;border-bottom:1px solid '+BORD+'">'
            +'<span style="font-size:13px;font-weight:700;color:'+(GOLD if i<3 else MUT)+';font-family:JetBrains Mono,monospace;width:22px">'+str(i+1)+'</span>'
            +'<span style="font-size:13px;font-weight:600;color:'+TXT+';width:140px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+safe(nm)+'</span>'
            +signal
            +'<div style="flex:1;height:6px;background:'+C2+';border-radius:3px;overflow:hidden"><div style="height:100%;width:'+f'{wbar:.0f}'+'%;background:'+B5+'"></div></div>'
            +'<span style="font-size:12px;font-weight:700;color:'+B3+';font-family:JetBrains Mono,monospace;width:56px;text-align:right">'+f'{cnt:,}건'+'</span></div>'
            +'<div style="font-size:10px;color:'+MUT+';padding:0 0 6px 34px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+safe(n.get("latest_title",""))+'</div>')
    st.markdown('<div style="background:'+CARD+';border:1px solid '+BORD+';border-radius:10px;padding:14px 18px">'+rows+'</div>', unsafe_allow_html=True)
else:
    st.markdown('<div style="color:'+MUT+';font-size:12px;padding:14px">뉴스 데이터 없음 (NAVER API 키 확인)</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 7. AI 시장 브리핑 (5순위 — 수동 생성, Home 브리핑과 역할 분리)
# ════════════════════════════════════════════════════════════════
st.markdown('<div class="qld-divider"></div>', unsafe_allow_html=True)
ac1, ac2 = st.columns([5,1])
with ac1:
    st.markdown('<div style="font-size:11px;color:'+MUT+';text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">🤖 AI 시장 흐름 해석 <span style="color:'+MUT+';text-transform:none;letter-spacing:0">— 시장 전체 관점 (내 포트는 홈 브리핑 참고)</span></div>', unsafe_allow_html=True)
with ac2:
    gen_clicked = st.button("🔄 생성", key="trend_brief", use_container_width=True)

TBRIEF_KEY = "trend_brief_result"
if gen_clicked:
    api_key = get_secret("ANTHROPIC_API_KEY","")
    if not api_key or api_key.startswith("*"):
        st.warning("Streamlit Secrets에 ANTHROPIC_API_KEY를 등록하세요.")
    else:
        # 프롬프트 구성 — 시장 전체 관점
        nl = "\n"
        sec_lines = [f"  {s['sector']}: {'유입' if s.get('score',0)>=0 else '이탈'} (↑{s.get('up',0)} ↓{s.get('down',0)})"
                     for s in sector_flow[:6]]
        rise_lines = [f"  {s.get('name','')} {s.get('change_pct',0):+.1f}%" for s in trending.get("rising",[])[:5]]
        news_lines = [f"  {n.get('name','')} {n.get('news_count',0)}건" for n in news_rank[:5]]
        prompt = (
            f"한국 주식 시장의 오늘 흐름을 분석하세요. 개별 종목 추천이 아니라 시장 전체 관점입니다.\n\n"
            f"[시장 레짐] {breadth.get('regime','')}\n"
            f"상승우세 {breadth.get('up_count',0)}종목 / 하락우세 {breadth.get('down_count',0)}종목\n\n"
            f"[섹터 자금 흐름]\n{nl.join(sec_lines)}\n\n"
            f"[상승 주도주]\n{nl.join(rise_lines)}\n\n"
            f"[뉴스 집중]\n{nl.join(news_lines)}\n\n"
            f"다음 JSON만 반환:\n"
            f'{{"flow":"오늘 자금 흐름 핵심 2문장","rotation":"섹터 순환/쏠림 해석 1-2문장","watch":"내일 주목할 포인트 1문장"}}'
        )
        with st.spinner("Claude가 시장 흐름 분석 중…"):
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=api_key.strip())
                msg = client.messages.create(model="claude-haiku-4-5-20251001",
                    max_tokens=600, messages=[{"role":"user","content":prompt}])
                m = re.search(r'\{.*\}', msg.content[0].text.strip(), re.DOTALL)
                if m:
                    st.session_state[TBRIEF_KEY] = json.loads(m.group())
            except Exception as e:
                st.error(f"생성 오류: {e}")

tb = st.session_state.get(TBRIEF_KEY)
if tb:
    st.markdown(
        '<div style="background:'+CARD+';border:1px solid '+BORD+';border-radius:8px;padding:16px 18px">'
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">'
        + '<div style="background:'+C2+';border-radius:6px;padding:11px 13px"><div style="font-size:9px;color:'+MUT+';text-transform:uppercase;margin-bottom:5px">🌊 자금 흐름</div><div style="font-size:12px;color:'+TXT+';line-height:1.6">'+safe(tb.get("flow",""))+'</div></div>'
        + '<div style="background:'+C2+';border-radius:6px;padding:11px 13px"><div style="font-size:9px;color:'+MUT+';text-transform:uppercase;margin-bottom:5px">🔄 섹터 순환</div><div style="font-size:12px;color:'+TXT+';line-height:1.6">'+safe(tb.get("rotation",""))+'</div></div>'
        + '</div>'
        + '<div style="padding:10px 13px;background:'+B5+'12;border:1px solid '+B5+'33;border-radius:6px;font-size:12px;color:'+B3+';font-weight:500">👀 내일 주목: '+safe(tb.get("watch",""))+'</div>'
        + '</div>',
        unsafe_allow_html=True
    )
else:
    st.markdown('<div style="background:'+CARD+';border:1px solid '+BORD+';border-radius:8px;padding:20px;text-align:center;font-size:12px;color:'+MUT+'">🔄 생성 버튼을 누르면 오늘 시장 흐름을 AI가 해석합니다 (수동 · 비용 절약)</div>', unsafe_allow_html=True)

# 푸터
st.markdown(
    '<div style="margin-top:2rem;padding:10px 0;border-top:1px solid '+BORD+';font-size:10px;color:'+MUT+';font-family:JetBrains Mono,monospace;display:flex;justify-content:space-between">'
    + '<span>네이버 금융 · 네이버 뉴스 · yfinance(거래량배수) · 매일 KST 07:00</span>'
    + '<span>수집: '+safe(updated)+'</span>'
    + '</div>',
    unsafe_allow_html=True
)
