"""
3. 투자자산 — 평가손익 자동 집계 + 자산배분 분석
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime, date
import json, uuid

st.set_page_config(page_title="투자자산", page_icon="📈", layout="wide",
                   initial_sidebar_state="expanded")

# ── 팔레트 ───────────────────────────────────────────────────
BG="#F5F0E5"; CARD="#FFFFFF"; C2="#FAF6EC"; BORD="#E5DDD0"; G="#EFE8D6"
TXT="#2A2620"; SUB="#5A5246"; MUT="#8C7F6E"; PUR_HI="#BAE6FD"; PUR_DK="#0369A1"
B1="#DBEAFE"; B3="#60A5FA"; B4="#3B82F6"; B5="#2563EB"; B6="#1D4ED8"; B8="#1E3A8A"
UP=B5; DN=B8

st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
@font-face{{font-family:'MaruBuri';src:url('https://cdn.jsdelivr.net/gh/wkdtjsgur100/maruburifonts@1.0/static/MaruBuri/MaruBuri-Regular.woff2') format('woff2')}}
html,body,[class*="css"]{{background-color:{BG}!important;color:{TXT}!important;
  font-family:'MaruBuri','Gowun Batang',serif!important;letter-spacing:.015em!important;line-height:1.3!important}}
.block-container{{padding:1.5rem 2rem 3rem!important;max-width:100%!important;background:transparent!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
[data-testid="stSidebar"]{{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
#MainMenu,footer,header{{visibility:hidden}}
.stButton>button{{background:{CARD}!important;color:{TXT}!important;border:1px solid {BORD}!important;
  border-radius:8px!important;font-family:'MaruBuri',serif!important}}
.stButton>button:hover{{border-color:{B5}!important;color:{B5}!important}}
.stTextInput>div>div>input,.stNumberInput>div>div>input,.stDateInput>div>div>input,.stSelectbox>div>div>div{{
  background:{CARD}!important;color:{TXT}!important;border:1px solid {BORD}!important;font-family:'JetBrains Mono',monospace!important}}
</style>
""", unsafe_allow_html=True)

# ── 데이터 경로 ──────────────────────────────────────────────
DATA = Path(__file__).parent.parent / "data"
PORT_FILE   = DATA / "portfolio.json"
PRICE_FILE  = DATA / "portfolio_prices.parquet"
MARKET_FILE = DATA / "market_prices.parquet"

def load_portfolio():
    if PORT_FILE.exists():
        with open(PORT_FILE, encoding="utf-8") as f: return json.load(f)
    return []

def save_portfolio(data):
    DATA.mkdir(exist_ok=True)
    with open(PORT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@st.cache_data(ttl=600)
def load_prices():
    if PRICE_FILE.exists():
        df = pd.read_parquet(PRICE_FILE)
        df["date"] = pd.to_datetime(df["date"])
        return df
    return pd.DataFrame()

@st.cache_data(ttl=600)
def get_usdkrw():
    if MARKET_FILE.exists():
        df = pd.read_parquet(MARKET_FILE)
        df["date"] = pd.to_datetime(df["date"])
        s = df[df["indicator"]=="USDKRW"].sort_values("date")
        if not s.empty: return float(s.iloc[-1]["value"])
    return 1380.0

def get_latest_price(ticker, prices_df):
    if prices_df.empty: return None, None, None
    sub = prices_df[prices_df["ticker"]==ticker].sort_values("date")
    if sub.empty: return None, None, None
    last = sub.iloc[-1]
    prev = sub.iloc[-2] if len(sub)>=2 else last
    return float(last["close"]), float(prev["close"]), pd.Timestamp(last["date"])

def compute_position(item, prices_df, usdkrw):
    lots = item.get("lots", [])
    if not lots: return None
    total_qty  = sum(l["qty"] for l in lots)
    total_cost = sum(l["qty"]*l["price"] for l in lots)
    avg_cost   = total_cost/total_qty if total_qty>0 else 0
    if total_qty <= 0: return None

    current, prev, price_date = get_latest_price(item["ticker"], prices_df)
    is_usd = item.get("currency","KRW")=="USD"
    fx = usdkrw if is_usd else 1

    if current is None:
        return {**{"name":item["name"],"ticker":item["ticker"],
                   "sector":item.get("sector","기타"),
                   "market":item.get("market","기타"),
                   "currency":item.get("currency","KRW"),
                   "qty":total_qty,"avg_cost":avg_cost,"current":None,
                   "price_date":None,
                   "value_local":0,"value_krw":0,"cost_krw":total_cost*fx,
                   "pnl_local":0,"pnl_krw":0,"pnl_pct":0,
                   "daily_pnl_krw":0,"daily_pct":0,"id":item.get("id",""),
                   "lots":lots,"notes":item.get("notes","")}}

    value_local = current*total_qty
    pnl_local   = (current-avg_cost)*total_qty
    pnl_pct     = (current/avg_cost-1)*100 if avg_cost>0 else 0
    daily_pct   = (current/prev-1)*100 if prev>0 else 0
    daily_pnl_l = (current-prev)*total_qty if prev else 0

    return {
        "name":item["name"],"ticker":item["ticker"],
        "sector":item.get("sector","기타"),
        "market":item.get("market","기타"),
        "currency":item.get("currency","KRW"),
        "qty":total_qty,"avg_cost":avg_cost,"current":current,
        "price_date":price_date,
        "value_local":value_local,"value_krw":value_local*fx,
        "cost_krw":total_cost*fx,
        "pnl_local":pnl_local,"pnl_krw":pnl_local*fx,
        "pnl_pct":pnl_pct,
        "daily_pnl_krw":daily_pnl_l*fx,"daily_pct":daily_pct,
        "id":item.get("id",""),"lots":lots,"notes":item.get("notes",""),
    }

# ── 헤더 ─────────────────────────────────────────────────────
st.markdown(f"""
<div style="font-family:'MaruBuri',serif;font-size:28px;font-weight:700;
  font-style:italic;margin-bottom:4px">
  <span style="background:linear-gradient(180deg,transparent 55%,{PUR_HI} 55%);padding:0 6px">
    📈 투자자산 현황
  </span>
</div>
<div style="font-size:11px;color:{MUT};margin-bottom:1.5rem">
  보유 종목 평가손익 · 자산 배분 · 일간 수익률 (매일 KST 07:00 자동 업데이트)
</div>
""", unsafe_allow_html=True)

# ── 데이터 로드 ──────────────────────────────────────────────
portfolio = load_portfolio()
prices    = load_prices()
usdkrw    = get_usdkrw()

# ══════════════════════════════════════════════════════════════
# 종목 추가 / 매수 기록 추가
# ══════════════════════════════════════════════════════════════
SECTORS = ["반도체","방산","증권·금융","우주항공","로봇·자동화","2차전지","바이오",
           "IT·소프트웨어","엔터·미디어","자동차","화학","철강·소재","건설","유틸리티",
           "소비재","에너지","기타"]
MARKETS = ["KOSPI","KOSDAQ","NYSE","NASDAQ","기타"]

mode = st.radio("작업 선택", ["📝 매수 기록 추가","➕ 신규 종목 등록","🗑️ 종목 관리"],
                 horizontal=True, label_visibility="collapsed")

if mode == "➕ 신규 종목 등록":
    with st.form("new_stock_form", clear_on_submit=True):
        st.markdown(f'<div style="font-size:13px;font-weight:600;color:{SUB};margin-bottom:6px">신규 종목 등록</div>',unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        with c1: n_name   = st.text_input("종목명*", placeholder="삼성전자")
        with c2: n_ticker = st.text_input("yfinance 티커*", placeholder="005930.KS")
        with c3: n_currency = st.selectbox("통화*", ["KRW","USD"])
        c4,c5,c6 = st.columns(3)
        with c4: n_sector = st.selectbox("섹터", SECTORS)
        with c5: n_market = st.selectbox("시장", MARKETS)
        with c6: n_notes  = st.text_input("메모", "")
        st.caption("💡 티커 예시: 한국 코스피=`005930.KS`, 코스닥=`247540.KQ`, 미국=`AAPL` (점 대신 하이픈 사용: `BRK-B`)")

        st.markdown(f'<div style="font-size:12px;color:{SUB};margin-top:8px">초기 매수 기록 (선택)</div>',unsafe_allow_html=True)
        c7,c8,c9 = st.columns(3)
        with c7: n_lot_date  = st.date_input("매수일", date.today())
        with c8: n_lot_qty   = st.number_input("수량", min_value=0.0, step=1.0)
        with c9: n_lot_price = st.number_input("매수가", min_value=0.0, step=100.0)

        submitted = st.form_submit_button("등록", type="primary")
        if submitted:
            if not n_name or not n_ticker:
                st.error("종목명과 티커는 필수입니다.")
            else:
                portfolio = load_portfolio()
                # 중복 체크
                if any(p.get("ticker")==n_ticker for p in portfolio):
                    st.warning(f"이미 등록된 티커: {n_ticker}")
                else:
                    new_item = {
                        "id": str(uuid.uuid4())[:8],
                        "name": n_name, "ticker": n_ticker,
                        "sector": n_sector, "market": n_market,
                        "currency": n_currency, "notes": n_notes,
                        "lots": []
                    }
                    if n_lot_qty > 0 and n_lot_price > 0:
                        new_item["lots"].append({
                            "date": str(n_lot_date),
                            "qty": n_lot_qty,
                            "price": n_lot_price,
                        })
                    portfolio.append(new_item)
                    save_portfolio(portfolio)
                    st.cache_data.clear()
                    st.success(f"{n_name} 등록 완료! 내일 07:00에 자동수집됩니다.")
                    st.rerun()

elif mode == "📝 매수 기록 추가":
    if not portfolio:
        st.info("먼저 신규 종목을 등록해주세요.")
    else:
        with st.form("add_lot_form", clear_on_submit=True):
            opts = {f"{p['name']} ({p['ticker']})": p["id"] for p in portfolio}
            sel = st.selectbox("종목 선택", list(opts.keys()))
            c1,c2,c3 = st.columns(3)
            with c1: a_date  = st.date_input("매수일", date.today())
            with c2: a_qty   = st.number_input("수량*", min_value=0.0, step=1.0)
            with c3: a_price = st.number_input("매수가*", min_value=0.0, step=100.0)
            if st.form_submit_button("매수 기록 추가", type="primary"):
                if a_qty <= 0 or a_price <= 0:
                    st.error("수량과 매수가는 0보다 커야 합니다.")
                else:
                    target_id = opts[sel]
                    for p in portfolio:
                        if p.get("id") == target_id:
                            p.setdefault("lots", []).append({
                                "date": str(a_date), "qty": a_qty, "price": a_price})
                            break
                    save_portfolio(portfolio)
                    st.cache_data.clear()
                    st.success("매수 기록 추가됨"); st.rerun()

elif mode == "🗑️ 종목 관리":
    if not portfolio:
        st.info("등록된 종목이 없습니다.")
    else:
        for p in portfolio:
            lots = p.get("lots", [])
            total_qty = sum(l["qty"] for l in lots)
            with st.expander(f"📌 {p['name']} ({p['ticker']}) · {len(lots)}개 매수기록 · 총 {total_qty:.0f}주"):
                if lots:
                    lot_df = pd.DataFrame(lots)
                    lot_df["금액"] = lot_df["qty"] * lot_df["price"]
                    lot_df.columns = ["매수일","수량","매수가","총액"]
                    st.dataframe(lot_df, use_container_width=True, hide_index=True)
                c1,c2 = st.columns([1,5])
                with c1:
                    if st.button("🗑️ 종목 삭제", key=f"del_{p['id']}"):
                        portfolio = [x for x in portfolio if x.get("id") != p["id"]]
                        save_portfolio(portfolio)
                        st.cache_data.clear()
                        st.rerun()

st.markdown(f'<div style="height:1px;background:{BORD};margin:1.5rem 0"></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 평가손익 집계
# ══════════════════════════════════════════════════════════════
positions = [compute_position(p, prices, usdkrw) for p in portfolio]
positions = [pos for pos in positions if pos]

if not positions:
    st.info("📊 보유 종목을 등록하고 매수 기록을 추가해주세요.")
    st.stop()

df = pd.DataFrame(positions)
has_price = df["current"].notna()
df_priced = df[has_price]
df_nopric = df[~has_price]

total_value = df_priced["value_krw"].sum()
total_cost  = df_priced["cost_krw"].sum()
total_pnl   = df_priced["pnl_krw"].sum()
total_pct   = (total_pnl/total_cost*100) if total_cost>0 else 0
total_daily = df_priced["daily_pnl_krw"].sum()
daily_pct   = (total_daily/(total_value-total_daily)*100) if (total_value-total_daily)>0 else 0

# ── KPI 카드 ─────────────────────────────────────────────────
kpi_items = [
    ("총 평가금액", f"{total_value:,.0f}원", B5, ""),
    ("총 평가손익", f"{total_pnl:+,.0f}원", UP if total_pnl>=0 else DN,
                    f"{total_pct:+.2f}%"),
    ("일간 변동",   f"{total_daily:+,.0f}원", UP if total_daily>=0 else DN,
                    f"{daily_pct:+.2f}%"),
    ("총 매수원가", f"{total_cost:,.0f}원", MUT,
                    f"USD/KRW {usdkrw:,.0f}"),
]
cols = st.columns(4)
for col,(lbl,val,clr,sub) in zip(cols, kpi_items):
    with col:
        sub_html = f'<div style="font-size:10px;color:{clr};font-weight:600;margin-top:2px">{sub}</div>' if sub else ""
        st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-left:3px solid {clr};
  border-radius:8px;padding:14px">
  <div style="font-size:10px;color:{MUT};text-transform:uppercase;letter-spacing:.05em">{lbl}</div>
  <div style="font-size:22px;font-weight:700;color:{TXT};line-height:1.2;margin-top:3px;font-family:'JetBrains Mono',monospace">{val}</div>
  {sub_html}
</div>""", unsafe_allow_html=True)

# 가격 없는 종목 경고
if not df_nopric.empty:
    no_p = ", ".join(df_nopric["ticker"].tolist())
    st.warning(f"⚠️ 가격 데이터가 아직 수집되지 않은 종목: {no_p} (내일 07:00 자동수집 후 표시)")

st.markdown(f'<div style="height:1.5rem"></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 자산 배분 차트
# ══════════════════════════════════════════════════════════════
def donut(df_, group_col, title, palette):
    g = df_.groupby(group_col)["value_krw"].sum().sort_values(ascending=False)
    if g.empty: return None
    fig = go.Figure(go.Pie(
        labels=g.index, values=g.values, hole=0.55,
        textinfo="label+percent", textfont=dict(size=10, family="MaruBuri"),
        marker=dict(colors=palette[:len(g)], line=dict(color=CARD, width=1.5)),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f}원 (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=11,color=SUB,family="MaruBuri"), x=0.01),
        paper_bgcolor=CARD, height=280, margin=dict(l=8,r=8,t=30,b=8),
        showlegend=False,
        annotations=[dict(text=f"{g.sum()/1e8:.1f}억", x=0.5, y=0.5,
                          font=dict(size=14,color=TXT,family="JetBrains Mono"), showarrow=False)],
    )
    return fig

BLUE_PAL = [B5,B4,B3,B6,B7,B8,B1,PUR_DK,"#7DD3FC","#38BDF8","#0EA5E9","#0284C7"]

st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};margin-bottom:8px;font-family:\'MaruBuri\',serif">자산 배분</div>',unsafe_allow_html=True)
c1,c2,c3,c4 = st.columns(4)
with c1:
    fig = donut(df_priced, "name", "종목별", BLUE_PAL)
    if fig: st.plotly_chart(fig, use_container_width=True)
with c2:
    fig = donut(df_priced, "sector", "섹터별", BLUE_PAL)
    if fig: st.plotly_chart(fig, use_container_width=True)
with c3:
    fig = donut(df_priced, "market", "시장별", BLUE_PAL)
    if fig: st.plotly_chart(fig, use_container_width=True)
with c4:
    fig = donut(df_priced, "currency", "통화별", [B5, PUR_DK])
    if fig: st.plotly_chart(fig, use_container_width=True)

st.markdown(f'<div style="height:1.5rem"></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 일간 변동 톱 (상승·하락)
# ══════════════════════════════════════════════════════════════
st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};margin-bottom:8px;font-family:\'MaruBuri\',serif">일간 변동</div>',unsafe_allow_html=True)
c1,c2 = st.columns(2)
with c1:
    top_up = df_priced.nlargest(5, "daily_pct")
    if not top_up.empty:
        fig = go.Figure(go.Bar(
            x=top_up["daily_pct"], y=top_up["name"], orientation="h",
            marker_color=B5,
            text=[f"+{p:.2f}%" for p in top_up["daily_pct"]],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>%{x:+.2f}%<extra></extra>",
        ))
        fig.update_layout(title=dict(text="📈 일간 상승 TOP 5",font=dict(size=11,color=SUB),x=0.01),
            paper_bgcolor=CARD, plot_bgcolor=CARD, height=230,
            margin=dict(l=8,r=40,t=30,b=8),
            xaxis=dict(showgrid=True,gridcolor=G,tickformat="+.1f",ticksuffix="%",tickfont=dict(size=9)),
            yaxis=dict(autorange="reversed",tickfont=dict(size=10,family="MaruBuri")))
        st.plotly_chart(fig, use_container_width=True)

with c2:
    top_dn = df_priced.nsmallest(5, "daily_pct")
    if not top_dn.empty and (top_dn["daily_pct"]<0).any():
        fig = go.Figure(go.Bar(
            x=top_dn["daily_pct"], y=top_dn["name"], orientation="h",
            marker_color=DN,
            text=[f"{p:.2f}%" for p in top_dn["daily_pct"]],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>%{x:+.2f}%<extra></extra>",
        ))
        fig.update_layout(title=dict(text="📉 일간 하락 TOP 5",font=dict(size=11,color=SUB),x=0.01),
            paper_bgcolor=CARD, plot_bgcolor=CARD, height=230,
            margin=dict(l=8,r=40,t=30,b=8),
            xaxis=dict(showgrid=True,gridcolor=G,tickformat="+.1f",ticksuffix="%",tickfont=dict(size=9)),
            yaxis=dict(autorange="reversed",tickfont=dict(size=10,family="MaruBuri")))
        st.plotly_chart(fig, use_container_width=True)

st.markdown(f'<div style="height:1.5rem"></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 보유 종목 상세 표
# ══════════════════════════════════════════════════════════════
st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};margin-bottom:8px;font-family:\'MaruBuri\',serif">보유 종목 상세</div>',unsafe_allow_html=True)

def fmt_row(r):
    """HTML 표 한 행 생성"""
    pnl_clr = UP if r["pnl_krw"]>=0 else DN
    daily_clr = UP if r["daily_pct"]>=0 else DN
    sign_p = "▲" if r["pnl_pct"]>=0 else "▼"
    sign_d = "▲" if r["daily_pct"]>=0 else "▼"
    weight = (r["value_krw"]/total_value*100) if total_value>0 else 0
    cur_str = f"{r['current']:,.2f}" if r["current"] else "—"
    cur_unit = r["currency"]
    return f"""
<tr style="border-bottom:1px solid {BORD}">
  <td style="padding:.6rem .8rem">
    <div style="font-size:12px;font-weight:600">{r['name']}</div>
    <div style="font-size:9px;color:{MUT};font-family:'JetBrains Mono',monospace">{r['ticker']}</div>
  </td>
  <td style="padding:.6rem .8rem;font-size:10px;color:{MUT}">{r['sector']}<br><span style="font-size:9px">{r['market']}</span></td>
  <td style="padding:.6rem .8rem;text-align:right;font-family:'JetBrains Mono',monospace;font-size:11px">{r['qty']:,.0f}주</td>
  <td style="padding:.6rem .8rem;text-align:right;font-family:'JetBrains Mono',monospace;font-size:11px">{r['avg_cost']:,.2f}<br><span style="font-size:9px;color:{MUT}">{cur_unit}</span></td>
  <td style="padding:.6rem .8rem;text-align:right;font-family:'JetBrains Mono',monospace;font-size:11px">{cur_str}<br><span style="font-size:9px;color:{daily_clr};font-weight:600">{sign_d}{abs(r['daily_pct']):.2f}%</span></td>
  <td style="padding:.6rem .8rem;text-align:right;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700">{r['value_krw']:,.0f}원<br><span style="font-size:9px;color:{MUT}">({weight:.1f}%)</span></td>
  <td style="padding:.6rem .8rem;text-align:right;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;color:{pnl_clr}">{r['pnl_krw']:+,.0f}원<br><span style="font-size:9px">{sign_p}{abs(r['pnl_pct']):.2f}%</span></td>
</tr>"""

df_sorted = df.sort_values("value_krw", ascending=False)
rows_html = "".join(fmt_row(r) for _,r in df_sorted.iterrows())
TH=f"padding:.5rem .8rem;text-align:left;font-size:9px;color:{MUT};letter-spacing:.05em;text-transform:uppercase;font-weight:500;border-bottom:1px solid {BORD};background:{C2}"

st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;overflow:hidden">
<table style="width:100%;border-collapse:collapse">
  <thead><tr>
    <th style="{TH}">종목</th>
    <th style="{TH}">섹터·시장</th>
    <th style="{TH};text-align:right">수량</th>
    <th style="{TH};text-align:right">평균단가</th>
    <th style="{TH};text-align:right">현재가 · 일간</th>
    <th style="{TH};text-align:right">평가금액 (비중)</th>
    <th style="{TH};text-align:right">평가손익</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table></div>
""", unsafe_allow_html=True)

# ── 푸터 ─────────────────────────────────────────────────────
last_update = ""
if not prices.empty:
    last_update = prices["date"].max().strftime("%Y-%m-%d")
st.markdown(f"""
<div style="margin-top:2rem;padding:10px 14px;background:{C2};border:1px solid {BORD};
  border-radius:8px;font-size:10px;color:{MUT};font-family:'JetBrains Mono',monospace">
  📅 가격 데이터 최종 업데이트: {last_update or "—"}  ·  USD/KRW: {usdkrw:,.0f}  ·  매일 KST 07:00 자동수집
</div>
""", unsafe_allow_html=True)
