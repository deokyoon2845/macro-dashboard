"""5. 주요 이슈 현황 — DART 공시 · 거래량 이상 · 구글 트렌드"""
import streamlit as st
import pandas as pd
import requests
import os
from pathlib import Path
from datetime import datetime, timedelta

st.set_page_config(page_title="이슈", page_icon="🔥", layout="wide",
                   initial_sidebar_state="expanded")

# ── 홈 버튼 ──────────────────────────────────────────────────
with st.sidebar:
    st.page_link("Home.py", label="🏠  홈으로 돌아가기", use_container_width=True)
    st.markdown('<div style="height:1px;background:#222A3A;margin:6px 0"></div>',
                unsafe_allow_html=True)

# ── 색상 팔레트 ───────────────────────────────────────────────
BG="#0A0D13"; CARD="#111620"; C2="#161C28"; C3="#1C2438"
BORD="#222A3A"; G="#181F2C"; TXT="#E4EAF6"; SUB="#7A8CA4"; MUT="#4A5668"
PUR_HI="#4A82E4"; PUR_DK="#79C0FF"; ACC="#4A82E4"; GOLD="#F5A623"
UP="#2ECC71"; DN="#E74C3C"
B1="#CAE8FF"; B3="#79C0FF"; B4="#58A6FF"
B5="#388BFD"; B6="#2F81F7"; B7="#1F6FEB"; B8="#1158C7"

st.markdown(f"""<style>
html,body,[class*="css"]{{background-color:{BG}!important;color:{TXT}!important;
  font-family:'Inter','Gowun Batang',sans-serif!important}}
.block-container{{padding:1.5rem 2rem 3rem!important;background:transparent!important;max-width:100%!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
[data-testid="stSidebar"]{{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
#MainMenu,footer,header{{visibility:hidden}}
p,span,div,label{{color:{TXT}!important}}
.stButton>button{{background:{CARD}!important;color:{TXT}!important;
  border:1px solid {BORD}!important;border-radius:8px!important}}
.stTabs [data-baseweb="tab-list"]{{background:{CARD}!important;
  border-bottom:1px solid {BORD}!important;gap:0}}
.stTabs [data-baseweb="tab"]{{background:transparent!important;color:{SUB}!important;
  font-size:12px!important;padding:10px 18px!important;
  border-bottom:2px solid transparent!important}}
.stTabs [aria-selected="true"]{{color:{TXT}!important;border-bottom-color:{B5}!important}}
</style>""", unsafe_allow_html=True)

st.markdown(f"""
<div style="font-size:28px;font-weight:700;font-style:italic;margin-bottom:4px">
  <span style="background:rgba(74,130,228,.28);padding:2px 10px;border-radius:6px">
    🔥 주요 이슈
  </span>
</div>
<div style="font-size:11px;color:{MUT};margin-bottom:1.5rem">
  DART 공시 · 거래량 이상 감지 · 구글 트렌드
</div>
""", unsafe_allow_html=True)

# ── API KEY 로드 (모듈 최상단에 위치해야 함) ─────────────────
def get_secret(k, default=""):
    try:
        return st.secrets[k]
    except:
        return os.environ.get(k, default)

DART_KEY = get_secret("DART_API_KEY")  # ← DART_KEY로 통일

# ── 탭 구성 ──────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 DART 공시", "📊 거래량 이상", "🔍 구글 트렌드"])

# ── DART 공시 ─────────────────────────────────────────────────
with tab1:
    if not DART_KEY:
        st.markdown(f"""
<div style="background:{C2};border:1px solid {BORD};border-radius:8px;
  padding:12px;margin-bottom:1rem;font-size:10px;color:{MUT}">
  💡 <b>DART API KEY</b>가 필요합니다. Streamlit Secrets에
  <code>DART_API_KEY</code>를 추가해주세요.
  (<a href="https://opendart.fss.or.kr" target="_blank"
     style="color:{B5}">DART Open API 신청</a> — 무료)
</div>""", unsafe_allow_html=True)

    watchlist = st.text_input(
        "관심 종목 코드 (쉼표 구분)", "005930,000660,035420",
        help="DART 기업 코드 8자리. 삼성전자=00126380")

    if st.button("공시 조회"):
        if not DART_KEY:
            st.info("Streamlit Cloud Secrets에 DART_API_KEY를 추가하면 실시간 공시를 볼 수 있습니다.")
        else:
            try:
                today    = datetime.now().strftime("%Y%m%d")
                week_ago = (datetime.now()-timedelta(days=7)).strftime("%Y%m%d")
                params   = {"crtfc_key": DART_KEY, "bgn_de": week_ago,
                            "end_de": today, "pblntf_ty": "A",
                            "page_no": 1, "page_count": 50}
                res  = requests.get("https://opendart.fss.or.kr/api/list.json",
                                    params=params, timeout=10)
                data = res.json()
                if data.get("status") == "000":
                    df = pd.DataFrame(data.get("list", []))
                    if not df.empty:
                        cols = [c for c in ["rcept_dt","corp_name","report_nm","flr_nm"]
                                if c in df.columns]
                        st.dataframe(
                            df[cols].rename(columns={
                                "rcept_dt":"접수일","corp_name":"법인명",
                                "report_nm":"공시명","flr_nm":"제출인"}),
                            use_container_width=True, hide_index=True)
                    else:
                        st.info("최근 7일간 공시 없음")
                else:
                    st.warning(f"DART API 오류: {data.get('message','')}")
            except Exception as e:
                st.error(f"오류: {e}")

# ── 거래량 이상 감지 ──────────────────────────────────────────
with tab2:
    st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};'
                f'margin-bottom:12px">거래량 이상 감지 (yfinance 수집 데이터)</div>',
                unsafe_allow_html=True)
    DATA_DIR = Path(__file__).parent.parent / "data"
    try:
        mdf = pd.read_parquet(DATA_DIR / "market_prices.parquet")
        mdf["date"] = pd.to_datetime(mdf["date"])
        anomalies = []
        for ind in mdf["indicator"].unique():
            s = mdf[mdf["indicator"]==ind].sort_values("date").tail(10)
            if len(s) >= 5:
                v_last = s.iloc[-1]["value"]; v_prev = s.iloc[-5]["value"]
                if v_prev and v_prev != 0:
                    chg = (v_last/v_prev - 1) * 100
                    if abs(chg) > 5:
                        anomalies.append({
                            "지표": ind,
                            "5일 변화": f"{chg:+.2f}%",
                            "최근값": f"{v_last:,.2f}",
                            "방향": "▲ 급등" if chg > 0 else "▼ 급락"
                        })
        if anomalies:
            anomalies.sort(key=lambda x: abs(float(x["5일 변화"].replace("%",""))), reverse=True)
            st.dataframe(pd.DataFrame(anomalies), use_container_width=True, hide_index=True)
        else:
            st.success("✅ 최근 5일간 5% 이상 급변 지표 없음")
    except FileNotFoundError:
        st.info("데이터 없음 — GitHub Actions 실행 후 확인 가능합니다.")
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")

# ── 구글 트렌드 ───────────────────────────────────────────────
with tab3:
    st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};'
                f'margin-bottom:12px">구글 트렌드 검색량 비교</div>',
                unsafe_allow_html=True)
    keywords  = st.text_input("검색어 (쉼표 구분, 최대 5개)",
                               "삼성전자,SK하이닉스,금리,달러,코스피")
    timeframe = st.selectbox("기간",
        ["now 7-d","today 1-m","today 3-m","today 12-m"],
        format_func=lambda x: {
            "now 7-d":"최근 7일","today 1-m":"1개월",
            "today 3-m":"3개월","today 12-m":"12개월"}[x])

    if st.button("트렌드 조회"):
        try:
            from pytrends.request import TrendReq
            import plotly.graph_objects as go
            pytrends = TrendReq(hl="ko-KR", tz=540)
            kw_list  = [k.strip() for k in keywords.split(",")][:5]
            pytrends.build_payload(kw_list, cat=0, timeframe=timeframe, geo="KR")
            df = pytrends.interest_over_time()
            if not df.empty:
                fig = go.Figure()
                colors = [B5, "#2ECC71", "#F5A623", "#E74C3C", "#79C0FF"]
                for i, kw in enumerate(kw_list):
                    if kw in df.columns:
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df[kw], name=kw, mode="lines",
                            line=dict(color=colors[i%len(colors)], width=2)))
                fig.update_layout(
                    paper_bgcolor=CARD, plot_bgcolor=CARD, height=380,
                    title=dict(text="구글 트렌드 (한국 기준)",
                               font=dict(size=11, color=SUB), x=0.01),
                    legend=dict(orientation="h", y=1.08, font=dict(size=10, color=SUB),
                                bgcolor="rgba(0,0,0,0)"),
                    hovermode="x unified",
                    yaxis=dict(title="상대 검색량", showgrid=True,
                               gridcolor=G, tickfont=dict(size=9, color=MUT)),
                    xaxis=dict(showgrid=False, tickfont=dict(size=9, color=MUT)),
                    margin=dict(l=8,r=8,t=32,b=8))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("검색 결과 없음")
        except ImportError:
            st.warning("pytrends 패키지가 필요합니다. requirements.txt에 추가 후 재배포하세요.")
        except Exception as e:
            st.error(f"트렌드 조회 오류: {e}")
