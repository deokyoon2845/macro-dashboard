"""
pages/6_일정.py — 경제 일정 & 매매 내역
FOMC 등 주요 일정 + 월간 캘린더 + 내 매매 내역
색상: 한국 증시 관례 (상승=빨강, 하락=파랑)
"""
import streamlit as st
import pandas as pd
import json
import base64
import sys
import calendar as calmod
from pathlib import Path
from datetime import datetime

# ════════════════════════════════════════════════════════════════
# 1. 초기 설정 및 경로
# ════════════════════════════════════════════════════════════════
st.set_page_config(page_title="일정 · 매매내역", page_icon="📅", layout="wide")

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from utils import render_sticky_nav
    render_sticky_nav()
except Exception:
    pass

DATA_DIR  = _ROOT / "data"
ASSET_DIR = _ROOT / "assets"

# ════════════════════════════════════════════════════════════════
# 2. 스타일 상수 및 폰트 설정
# ════════════════════════════════════════════════════════════════
BG = "#0A0D13"; CARD = "#111620"; C2 = "#161C28"; C3 = "#1C2438"
BORD = "#222A3A"; G = "#181F2C"; TXT = "#E4EAF6"; SUB = "#7A8CA4"; MUT = "#4A5668"
UP = "#E24B4A"      # 상승 빨강 (한국 증시 기준)
DN = "#388BFD"      # 하락 파랑 (한국 증시 기준)
B5 = "#388BFD"; B7 = "#1F6FEB"; ACC = "#388BFD"
GREYLINE = "#7A8CA4"

EV_STYLE = {
    "fomc":     ("#E24B4A", "🏛"),
    "cpi":      ("#F5A623", "📊"),   # 주황색은 일정 한정
    "bok":      ("#388BFD", "🇰🇷"),
    "earnings": ("#9C7BE0", "💵"),
    "custom":   ("#7A8CA4", "📌"),
}

def load_custom_font():
    fmt_map = {".woff2": "woff2", ".woff": "woff", ".ttf": "truetype", ".otf": "opentype"}
    for ext, fmt in fmt_map.items():
        fps = sorted(ASSET_DIR.glob(f"*{ext}"))
        if not fps: continue
        fp = fps[0]
        try:
            with open(fp, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            css = f"@font-face{{font-family:'{fp.stem}';src:url('data:font/{fmt};base64,{b64}') format('{fmt}');}}"
            return fp.stem, css
        except Exception:
            continue
    return None, ""

CUSTOM_FONT, FONT_FACE_CSS = load_custom_font()
FF = f"'{CUSTOM_FONT}',sans-serif" if CUSTOM_FONT else "'Inter','Gowun Batang',sans-serif"

# ════════════════════════════════════════════════════════════════
# 3. 데이터 로드 및 전처리
# ════════════════════════════════════════════════════════════════
def load_json(fn, default=None):
    p = DATA_DIR / fn
    if not p.exists(): return default if default is not None else {}
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except Exception:
        return default if default is not None else {}

def get_events():
    events_raw = load_json("events.json", {}).get("events", [])
    parsed = []
    for e in events_raw:
        try:
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
            parsed.append({**e, "_date": d})
        except Exception:
            continue
    return sorted(parsed, key=lambda x: x["_date"])

def get_trades():
    portfolio = load_json("portfolio.json", [])
    parsed = []
    for pos in portfolio:
        for lot in pos.get("lots", []):
            try:
                d = datetime.strptime(lot["date"], "%Y-%m-%d").date()
                parsed.append({
                    "date": d,
                    "name": pos.get("name", ""),
                    "ticker": pos.get("ticker", ""),
                    "account": pos.get("account", "일반"),
                    "sector": pos.get("sector", ""),
                    "type": lot.get("type", "buy"),
                    "qty": lot.get("qty", 0),
                    "price": lot.get("price", 0),
                    "currency": pos.get("currency", "KRW"),
                    "amount": lot.get("qty", 0) * lot.get("price", 0),
                })
            except Exception:
                continue
    return sorted(parsed, key=lambda x: x["date"], reverse=True)

# ════════════════════════════════════════════════════════════════
# 4. UI 렌더링 함수
# ════════════════════════════════════════════════════════════════
def render_css():
    st.markdown(
        FONT_FACE_CSS +
        """<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800"""
        """&family=JetBrains+Mono:wght@400;500;600&family=Gowun+Batang:wght@400;700&display=swap" rel="stylesheet">""" +
        f"""<style>
        html, body, [class*="css"] {{background-color: {BG} !important; color: {TXT} !important; font-family: {FF} !important; letter-spacing: -.01em !important;}}
        .block-container {{padding: 1.2rem 2rem 3rem !important; max-width: 100% !important;}}
        [data-testid="stAppViewContainer"] {{background-color: {BG} !important;}}
        [data-testid="stSidebar"] {{background-color: {CARD} !important; border-right: 1px solid {BORD} !important;}}
        #MainMenu, footer, header {{visibility: hidden;}}
        p, span, div, label {{color: {TXT} !important;}}
        .stButton>button {{background: {C2} !important; color: {TXT} !important; border: 1px solid {BORD} !important; border-radius: 8px !important; font-family: {FF} !important; font-size: 12px !important; font-weight: 500 !important; padding: 5px 14px !important; box-shadow: none !important;}}
        .stButton>button:hover {{border-color: {B5} !important; color: {B5} !important;}}
        [data-testid="collapsedControl"] {{background: {CARD} !important; border: 2px solid {B5} !important; border-left: none !important; border-radius: 0 10px 10px 0 !important; width: 2.5rem !important; top: .8rem !important; box-shadow: 4px 0 16px rgba(56,139,253,.4) !important;}}
        [data-testid="collapsedControl"] svg {{color: {B5} !important; fill: {B5} !important;}}
        </style>""", unsafe_allow_html=True)

def render_header(now):
    st.markdown(f"""
    <div style="padding:14px 0 12px;border-bottom:1px solid {BORD};margin-bottom:1.2rem">
        <div style="font-size:24px;font-weight:800;font-style:italic;line-height:1.2">
            <span style="background:rgba(56,139,253,.22);padding:2px 10px;border-radius:6px">📅 일정 · 매매내역</span>
        </div>
        <div style="font-size:11px;color:{MUT};font-family:'JetBrains Mono',monospace;margin-top:5px">
            FOMC · 경제지표 · 내 거래 기록 &nbsp;·&nbsp; {now.strftime("%Y-%m-%d %H:%M")} 기준
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_upcoming_events(events, today):
    st.markdown('<div style="font-size:16px;font-weight:700;margin-bottom:.6rem">⏰ 다가오는 일정</div>', unsafe_allow_html=True)
    
    upcoming = [e for e in events if e["_date"] >= today][:6]
    if not upcoming:
        st.info("예정된 일정이 없습니다. data/events.json에 추가하세요.")
        return

    cols = st.columns(min(3, len(upcoming)))
    for i, e in enumerate(upcoming):
        clr, icon = EV_STYLE.get(e.get("type", "custom"), EV_STYLE["custom"])
        dday = (e["_date"] - today).days
        dlabel = "D-DAY" if dday == 0 else f"D-{dday}"
        note_html = f'<div style="font-size:10px;color:{SUB};margin-top:4px">💡 {e["note"]}</div>' if e.get('note') else ''
        
        with cols[i % len(cols)]:
            st.markdown(f"""
            <div style="background:{CARD};border:1px solid {BORD};border-left:3px solid {clr};border-radius:9px;padding:13px 15px;margin-bottom:10px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                    <span style="font-size:18px">{icon}</span>
                    <span style="background:{clr}22;color:{clr};padding:2px 10px;border-radius:10px;font-size:11px;font-weight:700;font-family:'JetBrains Mono',monospace">{dlabel}</span>
                </div>
                <div style="font-size:13px;font-weight:700;color:{TXT};margin-bottom:3px">{e['title']}</div>
                <div style="font-size:10px;color:{MUT};font-family:'JetBrains Mono',monospace">
                    {e['_date'].strftime("%Y-%m-%d (%a)")} · {e.get('time','')}
                </div>
                {note_html}
            </div>""", unsafe_allow_html=True)

def render_calendar(events, trades, today):
    st.markdown('<div style="font-size:16px;font-weight:700;margin:1.4rem 0 .6rem">🗓 월간 캘린더</div>', unsafe_allow_html=True)

    nav1, nav2, nav3, _ = st.columns([1, 1, 2, 6])
    with nav1:
        if st.button("◀ 이전", use_container_width=True):
            st.session_state.ev_month -= 1
            if st.session_state.ev_month < 1:
                st.session_state.ev_month = 12
                st.session_state.ev_year -= 1
            st.rerun()
    with nav2:
        if st.button("다음 ▶", use_container_width=True):
            st.session_state.ev_month += 1
            if st.session_state.ev_month > 12:
                st.session_state.ev_month = 1
                st.session_state.ev_year += 1
            st.rerun()
    with nav3:
        st.markdown(f"""
        <div style="font-size:18px;font-weight:800;padding-top:4px;font-family:'JetBrains Mono',monospace">
            {st.session_state.ev_year}년 {st.session_state.ev_month}월
        </div>""", unsafe_allow_html=True)

    yr, mo = st.session_state.ev_year, st.session_state.ev_month

    # 데이터 매핑
    ev_by_day, tr_by_day = {}, {}
    for e in events:
        if e["_date"].year == yr and e["_date"].month == mo:
            ev_by_day.setdefault(e["_date"].day, []).append(e)
    for t in trades:
        if t["date"].year == yr and t["date"].month == mo:
            tr_by_day.setdefault(t["date"].day, []).append(t)

    cal = calmod.Calendar(firstweekday=6)  # 일요일 시작
    weeks = cal.monthdayscalendar(yr, mo)
    dows = ["일", "월", "화", "수", "목", "금", "토"]

    head = "".join(f'<div style="text-align:center;font-size:11px;font-weight:600;padding:6px 0;color:{"#E24B4A" if i==0 else "#388BFD" if i==6 else SUB}">{d}</div>' for i, d in enumerate(dows))
    
    cells = ""
    for week in weeks:
        for i, day in enumerate(week):
            if day == 0:
                cells += f'<div style="background:{BG};border:1px solid {BORD};min-height:78px;border-radius:6px"></div>'
                continue
            
            is_today = (yr == today.year and mo == today.month and day == today.day)
            dcol = "#E24B4A" if i == 0 else "#388BFD" if i == 6 else TXT
            
            chips = ""
            for e in ev_by_day.get(day, [])[:2]:
                clr, _ic = EV_STYLE.get(e.get("type", "custom"), EV_STYLE["custom"])
                chips += f'<div style="background:{clr}22;color:{clr};font-size:8px;padding:1px 4px;border-radius:3px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{e["title"][:9]}</div>'
            
            trs = tr_by_day.get(day, [])
            if trs:
                buys = sum(1 for t in trs if t["type"] == "buy")
                sells = sum(1 for t in trs if t["type"] == "sell")
                tg = ""
                if buys:  tg += f'<span style="color:{UP}">매수{buys}</span> '
                if sells: tg += f'<span style="color:{DN}">매도{sells}</span>'
                chips += f'<div style="font-size:8px;margin-top:2px;font-family:JetBrains Mono">{tg}</div>'

            border = f"2px solid {B5}" if is_today else f"1px solid {BORD}"
            bgc = C2 if is_today else CARD
            cells += f'<div style="background:{bgc};border:{border};min-height:78px;border-radius:6px;padding:4px 5px"><div style="font-size:11px;font-weight:700;color:{dcol};font-family:JetBrains Mono">{day}</div>{chips}</div>'

    st.markdown(f"""
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin-bottom:4px">{head}</div>
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px">{cells}</div>
    """, unsafe_allow_html=True)

def render_trade_history(trades):
    st.markdown('<div style="font-size:16px;font-weight:700;margin:1.6rem 0 .6rem">💼 매매 내역</div>', unsafe_allow_html=True)

    accounts = ["전체"] + sorted({t["account"] for t in trades})
    sel_acc = st.radio("계좌 필터", accounts, horizontal=True, label_visibility="collapsed")

    filt = trades if sel_acc == "전체" else [t for t in trades if t["account"] == sel_acc]

    if not filt:
        st.info("매매 내역이 없습니다. portfolio.json의 lots에 거래가 기록되면 표시됩니다.")
        return

    # 요약 카드
    buy_amt = sum(t["amount"] for t in filt if t["type"] == "buy")
    sell_amt = sum(t["amount"] for t in filt if t["type"] == "sell")
    n_buy = sum(1 for t in filt if t["type"] == "buy")
    n_sell = sum(1 for t in filt if t["type"] == "sell")
    
    cols = st.columns(3)
    summary_data = [
        (f"매수 {n_buy}건", f"{buy_amt:,.0f}", UP),
        (f"매도 {n_sell}건", f"{sell_amt:,.0f}", DN),
        ("총 거래", f"{len(filt)}건", SUB)
    ]
    
    for c, (lbl, val, clr) in zip(cols, summary_data):
        with c:
            st.markdown(f"""
            <div style="background:{CARD};border:1px solid {BORD};border-radius:8px;padding:10px 14px">
                <div style="font-size:10px;color:{MUT}">{lbl}</div>
                <div style="font-size:18px;font-weight:700;color:{clr};font-family:JetBrains Mono">{val}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)

    # 테이블 렌더링
    rows = ""
    for t in filt[:60]:
        tclr = UP if t["type"] == "buy" else DN
        tlbl = "매수" if t["type"] == "buy" else "매도"
        cur = t["currency"]
        rows += f"""
        <tr style="border-bottom:1px solid {BORD}">
            <td style="padding:8px 10px;font-size:11px;color:{SUB};font-family:JetBrains Mono">{t['date'].strftime("%Y-%m-%d")}</td>
            <td style="padding:8px 10px;font-size:12px;font-weight:600">{t['name']}</td>
            <td style="padding:8px 10px;font-size:10px;color:{MUT}">{t['account']}</td>
            <td style="padding:8px 10px"><span style="background:{tclr}22;color:{tclr};padding:2px 8px;border-radius:5px;font-size:10px;font-weight:700">{tlbl}</span></td>
            <td style="padding:8px 10px;font-size:11px;text-align:right;font-family:JetBrains Mono">{t['qty']:,.0f}</td>
            <td style="padding:8px 10px;font-size:11px;text-align:right;font-family:JetBrains Mono">{t['price']:,.2f}</td>
            <td style="padding:8px 10px;font-size:11px;text-align:right;font-weight:600;font-family:JetBrains Mono">{t['amount']:,.0f} {cur}</td>
        </tr>"""

    st.markdown(f"""
    <div style="background:{CARD};border:1px solid {BORD};border-radius:9px;overflow:hidden">
        <table style="width:100%;border-collapse:collapse">
            <thead>
                <tr style="background:{C2}">
                    <th style="padding:9px 10px;font-size:10px;color:{MUT};text-align:left">날짜</th>
                    <th style="padding:9px 10px;font-size:10px;color:{MUT};text-align:left">종목</th>
                    <th style="padding:9px 10px;font-size:10px;color:{MUT};text-align:left">계좌</th>
                    <th style="padding:9px 10px;font-size:10px;color:{MUT};text-align:left">구분</th>
                    <th style="padding:9px 10px;font-size:10px;color:{MUT};text-align:right">수량</th>
                    <th style="padding:9px 10px;font-size:10px;color:{MUT};text-align:right">단가</th>
                    <th style="padding:9px 10px;font-size:10px;color:{MUT};text-align:right">금액</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>""", unsafe_allow_html=True)
    
    if len(filt) > 60:
        st.caption(f"최근 60건 표시 (전체 {len(filt)}건)")

# ════════════════════════════════════════════════════════════════
# 5. 메인 실행 블록
# ════════════════════════════════════════════════════════════════
def main():
    now = datetime.now()
    today = now.date()

    if "ev_year" not in st.session_state: st.session_state.ev_year = now.year
    if "ev_month" not in st.session_state: st.session_state.ev_month = now.month

    # 스타일 적용
    render_css()
    
    # 데이터 로드
    events = get_events()
    trades = get_trades()

    # 화면 구성
    render_header(now)
    render_upcoming_events(events, today)
    render_calendar(events, trades, today)
    render_trade_history(trades)

if __name__ == "__main__":
    main()
