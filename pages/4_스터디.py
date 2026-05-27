"""4. 스터디 — 거래 일지 + AI 회고 + 학습 노트"""
import streamlit as st
import pandas as pd
import json, uuid
from pathlib import Path
from datetime import datetime, date

st.set_page_config(page_title="스터디",page_icon="📚",layout="wide",
                   initial_sidebar_state="expanded")

BG="#0A0D13"; CARD="#111620"; C2="#161C28"; C3="#1C2438"; BORD="#222A3A"; G="#181F2C"
TXT="#E4EAF6"; SUB="#7A8CA4"; MUT="#4A5668"; ACC="#4A82E4"; UP="#2ECC71"; DN="#E74C3C"

st.markdown(f"""<style>
html,body,[class*="css"]{{background-color:{BG}!important;color:{TXT}!important;
  font-family:'MaruBuri','Gowun Batang',serif!important;letter-spacing:.015em!important}}
.block-container{{padding:1.5rem 2rem 3rem!important;max-width:100%!important;background:transparent!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
[data-testid="stSidebar"]{{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
#MainMenu,footer,header{{visibility:hidden}}
p,span,div,label{{color:{TXT}!important}}
.stButton>button{{background:{C2}!important;color:{TXT}!important;border:1px solid {BORD}!important;border-radius:8px!important}}
.stButton>button:hover{{border-color:{B5}!important;color:{B5}!important;background:{C2}!important}}
</style>""",unsafe_allow_html=True)

st.markdown(f"""
<div style="font-family:'MaruBuri',serif;font-size:28px;font-weight:700;font-style:italic;margin-bottom:4px">
  <span style="background:rgba(47,129,247,.28);padding:1px 8px;border-radius:5px">📚 스터디</span>
</div>
<div style="font-size:11px;color:{MUT};margin-bottom:1.5rem">거래 일지 · AI 회고 · 학습 노트</div>
""",unsafe_allow_html=True)

DATA=Path(__file__).parent.parent/"data"
JOURNAL_FILE=DATA/"trade_journal.json"; NOTES_FILE=DATA/"study_notes.json"
PORT_FILE=DATA/"portfolio.json"; PRICES_FILE=DATA/"portfolio_prices.parquet"

def load_json(p,d):
    if p.exists():
        with open(p,encoding="utf-8") as f: return json.load(f)
    return d

def save_json(p,data):
    p.parent.mkdir(exist_ok=True)
    with open(p,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)

@st.cache_data(ttl=600)
def load_prices():
    if PRICES_FILE.exists():
        df=pd.read_parquet(PRICES_FILE); df["date"]=pd.to_datetime(df["date"]); return df
    return pd.DataFrame()

def latest_price(ticker,prices):
    if prices.empty: return None
    sub=prices[prices["ticker"]==ticker].sort_values("date")
    return float(sub.iloc[-1]["close"]) if not sub.empty else None

tab_j,tab_n=st.tabs(["📝 거래 일지","📚 학습 노트"])

# ── 거래 일지 ─────────────────────────────────────────────────
with tab_j:
    journal=load_json(JOURNAL_FILE,[]); portfolio=load_json(PORT_FILE,[]); prices=load_prices()
    mode=st.radio("작업",["📋 일지 목록","➕ 새 일지 작성"],horizontal=True,label_visibility="collapsed",key="jmode")

    if mode=="➕ 새 일지 작성":
        if not portfolio: st.warning("먼저 투자자산 페이지에서 종목을 등록해주세요.")
        else:
            with st.form("jform",clear_on_submit=True):
                c1,c2=st.columns(2)
                with c1:
                    jt_lbl=st.selectbox("유형",["매수 (buy)","매도 (sell)"])
                    jt="buy" if "buy" in jt_lbl else "sell"
                    opts={f"{p['name']} ({p['ticker']})":p for p in portfolio}
                    sel=st.selectbox("종목",list(opts.keys())); jstk=opts[sel]
                with c2:
                    jdate=st.date_input("거래일",date.today())
                    ca,cb=st.columns(2)
                    with ca: jqty=st.number_input("수량",min_value=0.0,step=1.0)
                    with cb: jprice=st.number_input("거래가",min_value=0.0,step=100.0)
                jthesis=st.text_area("거래 사유 / 투자 아이디어",height=120,
                    placeholder="예: HBM4 점유율 확대 기대, P/E 15배로 역사적 저평가…")
                c3,c4,c5=st.columns(3)
                with c3: jth=st.number_input("목표 상승률 (%)",0,200,20,5)
                with c4: jtl=st.number_input("손절 하락률 (%)",0,50,10,1)
                with c5: jpm=st.number_input("예상 보유 (개월)",1,60,6,1)
                if st.form_submit_button("일지 저장",type="primary"):
                    if jqty<=0 or jprice<=0: st.error("수량과 가격은 0보다 커야 합니다.")
                    elif not jthesis.strip(): st.error("거래 사유는 필수입니다.")
                    else:
                        entry={"id":str(uuid.uuid4())[:8],"created":datetime.combine(jdate,datetime.now().time()).isoformat(),
                               "type":jt,"ticker":jstk["ticker"],"stock_name":jstk["name"],
                               "sector":jstk.get("sector",""),"currency":jstk.get("currency","KRW"),
                               "qty":jqty,"price":jprice,"thesis":jthesis,
                               "target_pct_high":jth,"target_pct_low":-jtl,"period_months":jpm,"ai_reviews":[]}
                        journal.append(entry); save_json(JOURNAL_FILE,journal)
                        st.success("저장 완료!"); st.rerun()
    else:
        if not journal: st.info("아직 거래 일지가 없습니다.")
        else:
            f1,f2=st.columns(2)
            with f1: ft=st.selectbox("유형",["전체","매수","매도"],key="ft")
            with f2: fr=st.selectbox("회고",["전체","회고 있음","미회고"],key="fr")
            for entry in sorted(journal,key=lambda x:x.get("created",""),reverse=True):
                if ft=="매수" and entry["type"]!="buy": continue
                if ft=="매도" and entry["type"]!="sell": continue
                has_r=bool(entry.get("ai_reviews"))
                if fr=="회고 있음" and not has_r: continue
                if fr=="미회고" and has_r: continue
                cur=latest_price(entry["ticker"],prices)
                pct=(cur/entry["price"]-1)*100 if cur and entry["price"]>0 else None
                tlbl="🔵 매수" if entry["type"]=="buy" else "🟡 매도"
                ps=f" · {pct:+.2f}%" if pct is not None else ""
                rs=f" · 회고 {len(entry.get('ai_reviews',[]))}건" if has_r else ""
                with st.expander(f"{tlbl}  {entry['stock_name']}  ({entry['created'][:10]}){ps}{rs}"):
                    cc1,cc2=st.columns([2,1])
                    with cc1:
                        st.markdown(f"""**거래 정보**
- 거래가: `{entry['price']:,.0f}` {entry.get('currency','KRW')}  |  수량: `{entry['qty']:,.0f}`주
- 목표: +{entry.get('target_pct_high',0)}% / {entry.get('target_pct_low',0)}%  |  예상: {entry.get('period_months',0)}개월

**거래 사유**
{entry.get('thesis','(미입력)')}""")
                    with cc2:
                        if cur:
                            pnl=(cur-entry["price"])*entry["qty"]
                            pclr=UP if pnl>=0 else DN
                            st.markdown(f"""
<div style="background:{C2};border:1px solid {BORD};border-radius:8px;padding:12px">
  <div style="font-size:10px;color:{MUT}">현재가</div>
  <div style="font-size:18px;font-weight:700;color:{TXT};font-family:'JetBrains Mono',monospace;margin:3px 0">{cur:,.2f}</div>
  <div style="font-size:10px;color:{MUT}">평가손익</div>
  <div style="font-size:14px;font-weight:700;color:{pclr};font-family:'JetBrains Mono',monospace">{pnl:+,.0f}</div>
</div>""",unsafe_allow_html=True)
                    reviews=entry.get("ai_reviews",[])
                    if reviews:
                        st.markdown("---"); st.markdown(f"<div style='font-size:13px;font-weight:700;color:{TXT};margin-bottom:8px'>🤖 AI 회고</div>",unsafe_allow_html=True)
                        for rv in sorted(reviews,key=lambda r:r.get("days_passed",0)):
                            v=rv.get("verdict","판단보류")
                            vmap={"정답":(B5,"rgba(56,139,253,.2)"),"오답":(B8,"rgba(17,88,199,.2)"),"판단보류":(MUT,C2)}
                            vfg,vbg=vmap.get(v,(MUT,C2))
                            st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-left:3px solid {vfg};border-radius:8px;padding:12px 14px;margin-bottom:10px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
    <span style="font-size:10px;color:{MUT};font-family:'JetBrains Mono',monospace">{rv.get('days_passed',0)}일 경과 · {rv.get('change_pct',0):+.2f}%</span>
    <span style="background:{vbg};color:{vfg};padding:2px 9px;border-radius:9px;font-size:9px;font-weight:700">{v}</span>
  </div>
  <div style="font-size:12px;color:{TXT};font-weight:600;margin-bottom:6px">{rv.get('summary','')}</div>
  <div style="font-size:11px;color:{SUB};line-height:1.6;margin-bottom:3px">📌 사유 검증: {rv.get('thesis_check','')}</div>
  <div style="font-size:11px;color:{SUB};line-height:1.6">💡 교훈: {rv.get('lesson','')}</div>
</div>""",unsafe_allow_html=True)
                    ac1,ac2=st.columns([1,5])
                    with ac1:
                        if st.button("🗑️ 삭제",key=f"dj_{entry['id']}"):
                            journal=[x for x in journal if x["id"]!=entry["id"]]
                            save_json(JOURNAL_FILE,journal); st.rerun()
                    with ac2: st.caption("💡 거래 후 7/30/90/180일 경과 시 매일 KST 07:00 AI 회고 자동 생성됩니다.")

# ── 학습 노트 ─────────────────────────────────────────────────
with tab_n:
    notes=load_json(NOTES_FILE,[])
    with st.expander("✏️ 새 노트 작성",expanded=not notes):
        nt=st.text_input("제목",key="nt"); ntg=st.text_input("태그 (쉼표 구분)",key="ntg")
        nb=st.text_area("내용 (마크다운)",height=200,key="nb")
        if st.button("저장",type="primary",key="nsave") and nt:
            notes.insert(0,{"id":datetime.now().isoformat(),"title":nt,
                "tags":[t.strip() for t in ntg.split(",") if t.strip()],
                "body":nb,"created":datetime.now().strftime("%Y-%m-%d %H:%M")})
            save_json(NOTES_FILE,notes); st.success("저장 완료!"); st.rerun()
    if notes:
        all_tags=sorted(set(t for n in notes for t in n.get("tags",[])))
        ftag=st.selectbox("태그 필터",["전체"]+all_tags,key="ntag")
        filtered=notes if ftag=="전체" else [n for n in notes if ftag in n.get("tags",[])]
        for note in filtered:
            with st.expander(f"📌 {note['title']}  —  {note['created']}"):
                th="".join(f'<span style="background:rgba(56,139,253,.2);color:{B5};border-radius:3px;font-size:9px;padding:1px 8px;margin-right:4px">{t}</span>' for t in note.get("tags",[]))
                st.markdown(th,unsafe_allow_html=True); st.markdown(note.get("body",""))
                if st.button("🗑️ 삭제",key=f"dn_{note['id']}"):
                    notes.remove(note); save_json(NOTES_FILE,notes); st.rerun()
