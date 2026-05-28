"""
2. 가계부 — 수입·지출 추적
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="가계부", page_icon="💰", layout="wide",
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

st.markdown(f"""
<style>
html,body,[class*="css"]{{background-color:{BG}!important;color:{TXT}!important;
  font-family:'MaruBuri','Gowun Batang',serif!important;letter-spacing:.015em!important}}
.block-container{{padding:1.5rem 2rem 3rem!important;max-width:100%!important;background:transparent!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
[data-testid="stSidebar"]{{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
#MainMenu,footer,header{{visibility:hidden}}

/* ── 사이드바 접힘 토글 버튼 강조 ────────────────────────── */
[data-testid="collapsedControl"] {{
  background:{CARD} !important;
  border:2px solid {B5} !important;
  border-left:none !important;
  border-radius:0 10px 10px 0 !important;
  width:2.4rem !important;
  top:0.8rem !important;
  box-shadow:4px 0 14px rgba(56,139,253,.35) !important;
  transition:all .2s !important;
}}
[data-testid="collapsedControl"]:hover {{
  background:{C2} !important;
  box-shadow:4px 0 20px rgba(56,139,253,.5) !important;
}}
[data-testid="collapsedControl"] svg {{
  color:{B5} !important;
  fill:{B5} !important;
}}

.stButton>button{{background:{CARD}!important;color:{TXT}!important;border:1px solid {BORD}!important;border-radius:8px!important}}
</style>
""", unsafe_allow_html=True)

# ── 사이드바 플로팅 열기 버튼 ──────────────────────────────
st.markdown(f"""
<div id="sb-open-btn"
  style="position:fixed;top:10px;left:8px;z-index:99999;
    background:{CARD};border:2px solid {B5};border-radius:10px;
    padding:8px 12px;cursor:pointer;
    font-size:15px;font-weight:700;color:{B5};
    box-shadow:0 2px 12px rgba(56,139,253,.4);
    display:flex;align-items:center;gap:6px;
    opacity:0;pointer-events:none;transition:opacity .25s"
  onclick="document.querySelector('[data-testid=collapsedControl]')?.click()">
  ☰ 메뉴
</div>

<script>
(function() {{
  function syncBtn() {{
    const collapsed = document.querySelector('[data-testid="collapsedControl"]');
    const btn = document.getElementById('sb-open-btn');
    if (!btn) return;
    if (collapsed) {{
      btn.style.opacity = '1';
      btn.style.pointerEvents = 'auto';
    }} else {{
      btn.style.opacity = '0';
      btn.style.pointerEvents = 'none';
    }}
  }}
  const obs = new MutationObserver(syncBtn);
  obs.observe(document.body, {{childList:true, subtree:true}});
  setTimeout(syncBtn, 300);
}})();
</script>
""", unsafe_allow_html=True)


# ── 헤더 ─────────────────────────────────────────────────────
st.markdown(f"""
<div style="font-family:'MaruBuri',serif;font-size:28px;font-weight:700;color:{TXT};
  font-style:italic;margin-bottom:4px">
  <span style="background:linear-gradient(180deg,transparent 55%,{PUR_HI} 55%);padding:0 6px">
    💰 가계부
  </span>
</div>
<div style="font-size:11px;color:{MUT};margin-bottom:1.5rem">수입·지출 추적 · 카테고리별 분석</div>
""", unsafe_allow_html=True)

# ── 거래 내역 저장 경로 ──────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
LEDGER_FILE = DATA_DIR / "ledger.csv"

def load_ledger():
    if LEDGER_FILE.exists():
        return pd.read_csv(LEDGER_FILE)
    return pd.DataFrame(columns=["날짜","카테고리","금액","메모","유형"])

def save_ledger(df):
    df.to_csv(LEDGER_FILE, index=False)

ledger = load_ledger()

# ── 입력 섹션 ─────────────────────────────────────────────────
with st.expander("➕ 거래 내역 추가", expanded=ledger.empty):
    c1,c2,c3,c4 = st.columns([1.5,1.5,1.5,2])
    with c1: txn_date  = st.date_input("날짜", datetime.today())
    with c2:
        txn_type = st.selectbox("유형", ["지출","수입"])
        cat_options = (["식비","교통","주거","의류","의료","여가","교육","통신","기타"]
                       if txn_type=="지출" else ["급여","투자수익","기타수입"])
    with c3: txn_cat  = st.selectbox("카테고리", cat_options)
    with c4: txn_memo = st.text_input("메모", "")
    txn_amount = st.number_input("금액 (원)", min_value=0, step=1000)

    if st.button("추가하기", type="primary"):
        new_row = {"날짜": str(txn_date), "카테고리": txn_cat,
                   "금액": txn_amount if txn_type=="수입" else -txn_amount,
                   "메모": txn_memo, "유형": txn_type}
        ledger = pd.concat([ledger, pd.DataFrame([new_row])], ignore_index=True)
        save_ledger(ledger)
        st.success("추가 완료!"); st.rerun()

# ── CSV 업로드 ────────────────────────────────────────────────
with st.expander("📂 CSV 일괄 업로드"):
    uploaded = st.file_uploader("CSV 파일 (컬럼: 날짜,카테고리,금액,메모,유형)", type=["csv"])
    if uploaded:
        new_df = pd.read_csv(uploaded)
        ledger = pd.concat([ledger, new_df], ignore_index=True)
        save_ledger(ledger)
        st.success(f"{len(new_df)}건 추가됨"); st.rerun()
    st.caption("날짜: YYYY-MM-DD / 금액: 수입=양수, 지출=음수")

# ── 요약 대시보드 ─────────────────────────────────────────────
if not ledger.empty:
    ledger["날짜"] = pd.to_datetime(ledger["날짜"])
    ledger["금액"] = pd.to_numeric(ledger["금액"], errors="coerce").fillna(0)
    ledger["월"] = ledger["날짜"].dt.to_period("M").astype(str)

    now_m = datetime.now().strftime("%Y-%m")
    this_month = ledger[ledger["월"]==now_m]

    income = this_month[this_month["금액"]>0]["금액"].sum()
    expense = abs(this_month[this_month["금액"]<0]["금액"].sum())
    saving_rate = ((income-expense)/income*100) if income>0 else 0

    m1,m2,m3,m4 = st.columns(4)
    for col,(lbl,val,clr) in zip([m1,m2,m3,m4],[
        ("이번달 수입",f"{income:,.0f}원",GREEN),
        ("이번달 지출",f"{expense:,.0f}원",RED),
        ("순저축",f"{income-expense:,.0f}원",B5),
        ("저축률",f"{saving_rate:.1f}%",B5),
    ]):
        with col:
            st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:8px;padding:14px">
  <div style="font-size:10px;color:{MUT}">{lbl}</div>
  <div style="font-size:20px;font-weight:700;color:{clr}">{val}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    c1,c2 = st.columns(2)

    with c1:
        # 월별 트렌드
        monthly = ledger.groupby(["월","유형"])["금액"].sum().abs().reset_index()
        fig = go.Figure()
        for t,clr in [("수입",B5),("지출",RED)]:
            m = monthly[monthly["유형"]==t]
            if not m.empty:
                fig.add_trace(go.Bar(x=m["월"],y=m["금액"],name=t,marker_color=clr))
        fig.update_layout(paper_bgcolor=CARD,plot_bgcolor=CARD,height=280,
            title=dict(text="월별 수입·지출",font=dict(size=11,color=SUB),x=0.01),
            margin=dict(l=8,r=8,t=28,b=8),barmode="group",
            legend=dict(orientation="h",y=1.08,font=dict(size=9),bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # 카테고리 도넛
        cat_exp = this_month[this_month["금액"]<0].groupby("카테고리")["금액"].sum().abs()
        if not cat_exp.empty:
            fig = go.Figure(go.Pie(labels=cat_exp.index, values=cat_exp.values,
                hole=0.5, textinfo="label+percent"))
            fig.update_layout(paper_bgcolor=CARD,height=280,
                title=dict(text=f"{now_m} 지출 분류",font=dict(size=11,color=SUB),x=0.01),
                margin=dict(l=8,r=8,t=28,b=8),
                legend=dict(orientation="h",y=-0.1,font=dict(size=9)))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("**전체 거래 내역**")
    st.dataframe(ledger.sort_values("날짜",ascending=False).head(50),
                 use_container_width=True, hide_index=True)
else:
    st.info("아직 거래 내역이 없습니다. 위에서 추가하거나 CSV를 업로드해주세요.")
