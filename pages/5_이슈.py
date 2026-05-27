"""
5. 주요 이슈 현황 — DART 공시 · 거래량 이상 · 구글 트렌드
"""
import streamlit as st
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime, timedelta

st.set_page_config(page_title="이슈", page_icon="🔥", layout="wide",
                   initial_sidebar_state="expanded")

# ── 홈 버튼 ─────────────────────────────────────────────────
with st.sidebar:
    st.page_link("Home.py", label="🏠  홈으로 돌아가기", use_container_width=True)
    st.markdown(
        f'<div style="height:1px;background:#222A3A;margin:6px 0"></div>',
        unsafe_allow_html=True
    )

# ── 다크 팔레트 (전 페이지 공통) ───────────────────────────
BG    = "#0A0D13"; CARD  = "#111620"; C2    = "#161C28"
C3    = "#1C2438"; BORD  = "#222A3A"; G     = "#181F2C"
TXT   = "#E4EAF6"; SUB   = "#7A8CA4"; MUT   = "#4A5668"
# 구버전 호환 변수 (PUR_HI, PUR_DK)
PUR_HI = "#4A82E4"; PUR_DK = "#79C0FF"
ACC   = "#4A82E4"; GOLD  = "#F5A623"
UP    = "#2ECC71"; DN    = "#E74C3C"
B1    = "#CAE8FF"; B3    = "#79C0FF"; B4    = "#58A6FF"
B5    = "#388BFD"; B6    = "#2F81F7"; B7    = "#1F6FEB"; B8    = "#1158C7"

st.markdown(f"""<style>
html,body,[class*="css"]{{background-color:{BG}!important;color:{TXT}!important;
  font-family:'MaruBuri','Gowun Batang',serif!important;letter-spacing:.015em!important}}
.block-container{{padding:1.5rem 2rem 3rem!important;background:transparent!important;max-width:100%!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
[data-testid="stSidebar"]{{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
#MainMenu,footer,header{{visibility:hidden}}
.stButton>button{{background:{CARD}!important;color:{TXT}!important;border:1px solid {BORD}!important;border-radius:8px!important}}
</style>""", unsafe_allow_html=True)

st.markdown(f"""
<div style="font-family:'MaruBuri',serif;font-size:28px;font-weight:700;font-style:italic;margin-bottom:4px">
  <span style="background:linear-gradient(180deg,transparent 55%,{PUR_HI} 55%);padding:0 6px">
    🔥 주요 이슈
  </span>
</div>
<div style="font-size:11px;color:{MUT};margin-bottom:1.5rem">DART 공시 · 거래량 이상 감지 · 구글 트렌드</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📋 DART 공시", "📊 거래량 이상", "🔍 구글 트렌드"])

# ── DART 공시 ─────────────────────────────────────────────────
with tab1:
    def get_secret(k, default=""):
    try: return st.secrets[k]
    except: return os.environ.get(k, default)

DART_KEY = get_secret("DART_API_KEY")

    st.markdown(f"""
<div style="background:{C2};border:1px solid {BORD};border-radius:8px;padding:12px;margin-bottom:1rem;font-size:10px;color:{MUT}">
  💡 <b>DART API KEY</b>가 필요합니다. Streamlit Secrets에 <code>DART_API_KEY</code>를 추가해주세요.
  (<a href="https://opendart.fss.or.kr" target="_blank">DART Open API 신청</a> — 무료)
</div>""", unsafe_allow_html=True)

    watchlist = st.text_input("관심 종목 코드 (쉼표 구분)", "005930,000660,035420",
                               help="DART 기업 코드 8자리. 삼성전자=00126380")

    if st.button("공시 조회") and DART_API:
        try:
            today = datetime.now().strftime("%Y%m%d")
            week_ago = (datetime.now()-timedelta(days=7)).strftime("%Y%m%d")
            url = f"https://opendart.fss.or.kr/api/list.json"
            params = {"crtfc_key": DART_API, "bgn_de": week_ago,
                      "end_de": today, "pblntf_ty": "A", "page_no": 1, "page_count": 50}
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            if data.get("status") == "000":
                df = pd.DataFrame(data.get("list",[]))
                if not df.empty:
                    st.dataframe(df[["rcept_dt","corp_name","report_nm","flr_nm"]].rename(
                        columns={"rcept_dt":"접수일","corp_name":"법인명",
                                 "report_nm":"공시명","flr_nm":"제출인"}),
                        use_container_width=True, hide_index=True)
                else:
                    st.info("최근 7일간 공시 없음")
            else:
                st.warning(f"DART API 오류: {data.get('message','')}")
        except Exception as e:
            st.error(f"오류: {e}")
    elif not DART_API:
        st.info("Streamlit Cloud Secrets에 DART_API_KEY를 추가하면 실시간 공시를 볼 수 있습니다.")

# ── 거래량 이상 감지 ──────────────────────────────────────────
with tab2:
    st.subheader("거래량 이상 감지 (yfinance 수집 데이터 기반)")
    DATA_DIR = Path(__file__).parent.parent / "data"
    try:
        mdf = pd.read_parquet(DATA_DIR/"market_prices.parquet")
        mdf["date"] = pd.to_datetime(mdf["date"])
        
        # 간단한 거래량 이상 감지 예시 (가격 변동 기반)
        today_data = mdf[mdf["date"] >= datetime.now()-timedelta(days=5)]
        anomalies = []
        for ind in today_data["indicator"].unique():
            s = mdf[mdf["indicator"]==ind].sort_values("date").tail(10)
            if len(s) >= 5:
                recent_chg = abs((s.iloc[-1]["value"]/s.iloc[-5]["value"]-1)*100)
                if recent_chg > 5:
                    anomalies.append({"지표": ind,
                                       "5일 변화": f"{recent_chg:+.2f}%",
                                       "최근값": f"{s.iloc[-1]['value']:,.2f}"})
        
        if anomalies:
            df_anomaly = pd.DataFrame(anomalies)
            st.dataframe(df_anomaly, use_container_width=True, hide_index=True)
        else:
            st.success("최근 5일간 5% 이상 급변 지표 없음")
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")

# ── 구글 트렌드 ───────────────────────────────────────────────
with tab3:
    st.subheader("구글 트렌드 검색량 비교")
    keywords = st.text_input("검색어 (쉼표 구분, 최대 5개)", "삼성전자,SK하이닉스,금리,달러,코스피")
    timeframe = st.selectbox("기간", ["now 7-d","today 1-m","today 3-m","today 12-m"],
                              format_func=lambda x: {"now 7-d":"최근 7일","today 1-m":"1개월","today 3-m":"3개월","today 12-m":"12개월"}[x])

    if st.button("트렌드 조회"):
        try:
            from pytrends.request import TrendReq
            import plotly.graph_objects as go
            pytrends = TrendReq(hl="ko-KR", tz=540)
            kw_list = [k.strip() for k in keywords.split(",")][:5]
            pytrends.build_payload(kw_list, cat=0, timeframe=timeframe, geo="KR")
            df = pytrends.interest_over_time()
            if not df.empty:
                fig = go.Figure()
                for kw in kw_list:
                    if kw in df.columns:
                        fig.add_trace(go.Scatter(x=df.index, y=df[kw], name=kw, mode="lines"))
                fig.update_layout(paper_bgcolor=CARD, plot_bgcolor=CARD, height=350,
                    title=dict(text="구글 트렌드 (한국)", font=dict(size=11), x=0.01),
                    legend=dict(orientation="h", y=1.08), hovermode="x unified",
                    yaxis_title="상대 검색량", margin=dict(l=8,r=8,t=32,b=8))
                st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.warning("pytrends 패키지가 필요합니다. requirements.txt에 pytrends 추가 후 재배포하세요.")
        except Exception as e:
            st.error(f"오류: {e}")
