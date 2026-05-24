"""
Macro Monitor — 한미 매크로 모니터링 대시보드
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="Macro Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 스타일 ───────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main-title {
    font-size: 1.7rem; font-weight: 700; color: #FAFAFA;
    margin-bottom: 0.1rem;
}
.main-sub {
    font-size: 0.82rem; color: #6B7280; margin-bottom: 1.8rem;
}
.section-label {
    font-size: 0.72rem; font-weight: 600; color: #6B7280;
    text-transform: uppercase; letter-spacing: 0.1em;
    margin: 1.8rem 0 0.7rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #1F2937;
}
div[data-testid="stMetric"] {
    background: #111827;
    border: 1px solid #1F2937;
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
}
div[data-testid="stMetricValue"] > div {
    font-size: 1.35rem !important;
    font-weight: 600 !important;
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── 상수 ─────────────────────────────────────────────────────
DATA_DIR   = Path(__file__).parent / "data"
BG         = "#0D1117"
CHART_BG   = "#111827"
GRID       = "#1F2937"
COLORS     = {
    "blue":   "#3B82F6",
    "green":  "#10B981",
    "red":    "#EF4444",
    "amber":  "#F59E0B",
    "purple": "#8B5CF6",
    "teal":   "#14B8A6",
    "orange": "#F97316",
    "gray":   "#6B7280",
}

# ── 데이터 로드 ───────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load(filename):
    f = DATA_DIR / filename
    if not f.exists():
        return pd.DataFrame()
    df = pd.read_parquet(f)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df

fred      = load("fred_indicators.parquet")
market    = load("market_prices.parquet")
sentiment = load("sentiment.parquet")
ecos      = load("ecos_latest.parquet")

def get_latest(df, indicator):
    if df.empty: return None
    sub = df[df["indicator"] == indicator].sort_values("date")
    return sub.iloc[-1] if not sub.empty else None

def get_series(df, indicator, days=365):
    if df.empty: return pd.DataFrame()
    sub = df[df["indicator"] == indicator].copy()
    if days:
        sub = sub[sub["date"] >= pd.Timestamp.now() - pd.Timedelta(days=days)]
    return sub.sort_values("date")

def line_chart(traces, title="", height=270, zero_line=False):
    """traces: [(df, name, color), ...]"""
    fig = go.Figure()
    for df, name, color in traces:
        if df.empty: continue
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["value"], name=name,
            line=dict(color=color, width=2),
            hovertemplate=f"<b>{name}</b><br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}<extra></extra>",
        ))
    if zero_line:
        fig.add_hline(y=0, line_dash="dot", line_color="#374151", line_width=1)
    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color="#9CA3AF"), x=0),
        template="plotly_dark", paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        height=height, margin=dict(l=8, r=8, t=36, b=8),
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=10),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False),
        hovermode="x unified",
    )
    return fig

# ── 헤더 ─────────────────────────────────────────────────────
st.markdown('<div class="main-title">📊 Macro Monitor</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="main-sub">한미 매크로 모니터링 · 업데이트: {datetime.now().strftime("%Y-%m-%d")}'
    f' · 매일 KST 07:00 자동 수집</div>',
    unsafe_allow_html=True,
)

# ── KPI 메트릭 ────────────────────────────────────────────────
st.markdown('<div class="section-label">핵심 지표 현재값</div>', unsafe_allow_html=True)

kpi_list = [
    ("VIX",           "📉 VIX",         market,    False, ".1f"),
    ("FEAR_GREED",    "😨 공포탐욕",     sentiment, False, ".0f"),
    ("HY_OAS",        "💳 HY스프레드",  fred,      False, ".2f"),
    ("US_10Y",        "🏦 미국10Y(%)",  fred,      False, ".2f"),
    ("T10Y2Y_SPREAD", "📐 2Y-10Y",     fred,      True,  ".2f"),
    ("DXY",           "💵 DXY",         market,    False, ".1f"),
    ("USDKRW",        "🇰🇷 USD/KRW",  market,    False, ",.0f"),
    ("SOX",           "🔵 SOX",         market,    False, ",.0f"),
]

cols = st.columns(8)
for col, (ind, label, df, inverse, fmt) in zip(cols, kpi_list):
    row = get_latest(df, ind)
    with col:
        if row is not None:
            val = row["value"]
            series = get_series(df, ind, days=10)
            delta = None
            if len(series) >= 2:
                prev = series.iloc[-2]["value"]
                delta = f"{val - prev:+.2f}"
            st.metric(
                label=label,
                value=format(val, fmt),
                delta=delta,
                delta_color="inverse" if inverse else "normal",
            )
        else:
            st.metric(label=label, value="—")

# ── Section A: 위험·심리 ──────────────────────────────────────
st.markdown('<div class="section-label">A · 글로벌 위험 & 심리</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)

with c1:
    vix = get_series(market, "VIX")
    hy  = get_series(fred,   "HY_OAS")
    fig = line_chart([
        (vix, "VIX",           COLORS["red"]),
        (hy,  "HY OAS (%)",    COLORS["amber"]),
    ], "VIX · HY 신용스프레드")
    fig.add_hrect(y0=25, y1=100, fillcolor="rgba(239,68,68,0.04)", line_width=0)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fg = get_series(sentiment, "FEAR_GREED")
    sp = get_series(fred,      "T10Y2Y_SPREAD")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if not fg.empty:
        fig.add_trace(go.Scatter(
            x=fg["date"], y=fg["value"], name="공포탐욕지수",
            line=dict(color=COLORS["blue"], width=2),
            hovertemplate="<b>공포탐욕</b> %{y:.0f}<extra></extra>",
        ), secondary_y=False)
        fig.add_hrect(y0=0,  y1=25,  fillcolor="rgba(239,68,68,0.06)",  line_width=0)
        fig.add_hrect(y0=75, y1=100, fillcolor="rgba(16,185,129,0.06)", line_width=0)
    if not sp.empty:
        fig.add_trace(go.Scatter(
            x=sp["date"], y=sp["value"], name="2Y-10Y (%)",
            line=dict(color=COLORS["amber"], width=1.5, dash="dot"),
            hovertemplate="<b>스프레드</b> %{y:.2f}%<extra></extra>",
        ), secondary_y=True)
    fig.add_hline(y=0, line_dash="dot", line_color="#374151", line_width=1, secondary_y=True)
    fig.update_layout(
        title=dict(text="공포탐욕지수 · 금리 스프레드", font=dict(size=12, color="#9CA3AF"), x=0),
        template="plotly_dark", paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        height=270, margin=dict(l=8, r=8, t=36, b=8),
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=10),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=True, gridcolor=GRID),
        hovermode="x unified",
    )
    fig.update_yaxes(showgrid=True, gridcolor=GRID, secondary_y=False)
    fig.update_yaxes(showgrid=False, secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

# ── Section B: 금리·달러 ──────────────────────────────────────
st.markdown('<div class="section-label">B · 미국 금리 & 달러</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)

with c1:
    us10 = get_series(fred,   "US_10Y")
    sp   = get_series(fred,   "T10Y2Y_SPREAD")
    fig  = line_chart([
        (us10, "미국 10Y 금리 (%)", COLORS["blue"]),
        (sp,   "2Y-10Y 스프레드",  COLORS["amber"]),
    ], "미국 금리", zero_line=True)
    fig.add_hrect(y0=4.5, y1=10, fillcolor="rgba(245,158,11,0.04)", line_width=0)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    dxy = get_series(market, "DXY")
    fig = line_chart([(dxy, "DXY 달러 인덱스", COLORS["purple"])], "DXY 달러 인덱스")
    st.plotly_chart(fig, use_container_width=True)

# ── Section C: 한국 시장 ──────────────────────────────────────
st.markdown('<div class="section-label">C · 한국 시장</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)

with c1:
    krw = get_series(market, "USDKRW")
    fig = line_chart([(krw, "USD/KRW", COLORS["orange"])], "원달러 환율")
    fig.add_hrect(y0=1400, y1=2500, fillcolor="rgba(239,68,68,0.04)", line_width=0)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    ksp = get_series(market, "KOSPI")
    fig = line_chart([(ksp, "KOSPI", COLORS["teal"])], "KOSPI")
    st.plotly_chart(fig, use_container_width=True)

# ── Section D: 글로벌 모멘텀 ─────────────────────────────────
st.markdown('<div class="section-label">D · 글로벌 주식 모멘텀</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)

with c1:
    sox = get_series(market, "SOX")
    fig = line_chart([(sox, "SOX 반도체지수", COLORS["blue"])], "필라델피아 반도체 (SOX)")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    spx = get_series(market, "SPX")
    fig = line_chart([(spx, "S&P 500", COLORS["purple"])], "S&P 500")
    st.plotly_chart(fig, use_container_width=True)

# ── Section E: 미국 월간 매크로 ──────────────────────────────
st.markdown('<div class="section-label">E · 미국 월간 매크로</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)

with c1:
    cpi = get_series(fred, "US_CORE_CPI", days=365 * 6)
    if not cpi.empty:
        cpi = cpi.copy()
        cpi["yoy"] = cpi["value"].pct_change(12) * 100
        cpi_yoy = cpi.dropna(subset=["yoy"])[["date", "yoy"]].rename(columns={"yoy": "value"})
        fig = line_chart([(cpi_yoy, "Core CPI YoY (%)", COLORS["orange"])], "미국 Core CPI YoY")
        fig.add_hline(y=2.0, line_dash="dot", line_color="#374151", line_width=1.5,
                      annotation_text="목표 2%", annotation_font_color="#6B7280",
                      annotation_position="bottom right")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Core CPI 데이터 로딩 중")

with c2:
    nfp = get_series(fred, "US_NFP", days=365 * 5)
    if not nfp.empty:
        nfp = nfp.copy()
        nfp["mom"] = nfp["value"].diff()
        nfp_mom = nfp.dropna(subset=["mom"])
        bar_colors = [COLORS["green"] if v >= 0 else COLORS["red"] for v in nfp_mom["mom"]]
        fig = go.Figure(go.Bar(
            x=nfp_mom["date"], y=nfp_mom["mom"],
            marker_color=bar_colors,
            hovertemplate="<b>NFP MoM</b><br>%{x|%Y-%m}<br>%{y:,.0f}천명<extra></extra>",
        ))
        fig.update_layout(
            title=dict(text="비농업 고용 월간 변화 (천명)", font=dict(size=12, color="#9CA3AF"), x=0),
            template="plotly_dark", paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
            height=270, margin=dict(l=8, r=8, t=36, b=8),
            xaxis=dict(showgrid=True, gridcolor=GRID),
            yaxis=dict(showgrid=True, gridcolor=GRID),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("NFP 데이터 로딩 중")

# ── Section F: 한국 매크로 (ECOS) ────────────────────────────
st.markdown('<div class="section-label">F · 한국 매크로 (한국은행 ECOS)</div>', unsafe_allow_html=True)

if ecos.empty:
    st.info("ECOS 데이터 없음")
else:
    preview = [c for c in ["CLASS_NAME", "KEYSTAT_NAME", "DATA_VALUE", "UNIT_NAME", "CYCLE"]
               if c in ecos.columns]
    if preview:
        disp = ecos[preview].copy()
        disp.columns = ["분류", "지표명", "현재값", "단위", "주기"][:len(preview)]
        st.dataframe(disp, use_container_width=True, height=380, hide_index=True)

# ── 푸터 ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#374151;font-size:0.72rem;">'
    'FRED · yfinance · CNN Fear & Greed · ECOS · 매일 KST 07:00 자동 수집</p>',
    unsafe_allow_html=True,
)
