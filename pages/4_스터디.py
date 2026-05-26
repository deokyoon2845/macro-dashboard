"""
4. 스터디 현황 — 리포트·메모 관리
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="스터디", page_icon="📚", layout="wide",
                   initial_sidebar_state="expanded")

BG="#F5F0E5"; CARD="#FFFFFF"; BORD="#E5DDD0"
TXT="#2A2620"; MUT="#8C7F6E"; PUR_HI="#BAE6FD"; B5="#2563EB"; PUR_DK="#0369A1"

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
    📚 스터디 현황
  </span>
</div>
<div style="font-size:11px;color:{MUT};margin-bottom:1.5rem">투자 아이디어 · 리포트 · 메모</div>
""", unsafe_allow_html=True)

NOTES_FILE = Path(__file__).parent.parent / "data" / "study_notes.json"

def load_notes():
    if NOTES_FILE.exists():
        with open(NOTES_FILE) as f: return json.load(f)
    return []

def save_notes(data):
    with open(NOTES_FILE,"w") as f: json.dump(data, f, ensure_ascii=False, indent=2)

notes = load_notes()

# ── 새 노트 작성 ─────────────────────────────────────────────
with st.expander("✏️ 새 노트 작성", expanded=not notes):
    n_title = st.text_input("제목")
    n_tags  = st.text_input("태그 (쉼표 구분)", placeholder="매크로, 금리, 미국")
    n_body  = st.text_area("내용 (마크다운 지원)", height=200)
    c1,c2 = st.columns([1,4])
    with c1:
        if st.button("저장", type="primary") and n_title:
            notes.insert(0, {
                "id": datetime.now().isoformat(),
                "title": n_title,
                "tags": [t.strip() for t in n_tags.split(",") if t.strip()],
                "body": n_body,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            save_notes(notes)
            st.success("저장 완료!"); st.rerun()

# ── 노트 목록 ─────────────────────────────────────────────────
if notes:
    all_tags = sorted(set(t for n in notes for t in n.get("tags",[])))
    filter_tag = st.selectbox("태그 필터", ["전체"]+all_tags, key="tag_filter")
    filtered = notes if filter_tag=="전체" else [n for n in notes if filter_tag in n.get("tags",[])]

    for note in filtered:
        with st.expander(f"📌 {note['title']}  —  {note['created']}"):
            tag_html = " ".join(
                f'<span style="background:#EFF6FF;color:{B5};border:1px solid {B5}40;'
                f'padding:1px 8px;border-radius:10px;font-size:9px;font-weight:600">{t}</span>'
                for t in note.get("tags",[]))
            st.markdown(tag_html, unsafe_allow_html=True)
            st.markdown(note.get("body",""))
            if st.button("🗑️ 삭제", key=f"del_{note['id']}"):
                notes.remove(note); save_notes(notes); st.rerun()
else:
    st.info("아직 노트가 없습니다. 위에서 새 노트를 작성해보세요.")
