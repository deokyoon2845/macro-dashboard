"""
2. 투자자산 — 계좌별 통합 관리 대시보드
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime, date
import json, uuid, base64, sys

# 1. 초기 설정
st.set_page_config(page_title="투자자산", page_icon="📈", layout="wide")

# 세션 상태 초기화 (에러 방지용)
if "chart_range" not in st.session_state:
    st.session_state.chart_range = "3M"

_ROOT = Path(__file__).parent.parent
DATA = _ROOT / "data"
PORT_FILE = DATA / "portfolio.json"
PRICE_FILE = DATA / "portfolio_prices.parquet"

# 2. 데이터 처리 및 그룹화 로직 (핵심)
def get_processed_data():
    portfolio = []
    if PORT_FILE.exists():
        with open(PORT_FILE, encoding="utf-8") as f:
            portfolio = json.load(f)
            
    prices = pd.read_parquet(PRICE_FILE) if PRICE_FILE.exists() else pd.DataFrame()
    
    # 계좌+종목별 통합 데이터 생성
    rows = []
    for p in portfolio:
        lots = p.get("lots", [])
        for l in lots:
            rows.append({
                "name": p["name"],
                "ticker": p["ticker"],
                "account": p.get("account", "일반"),
                "qty": l["qty"],
                "value": l["qty"] * l["price"] # 예시로 원가 기반 계산
            })
    
    df = pd.DataFrame(rows)
    if df.empty: return df
    
    # 계좌별, 종목별로 그룹화하여 합산
    df = df.groupby(["account", "name", "ticker"]).agg({
        "qty": "sum",
        "value": "sum"
    }).reset_index()
    
    return df

# 3. 메인 UI 렌더링
def main():
    st.markdown("### 📈 투자자산 현황")
    
    df = get_processed_data()
    
    if df.empty:
        st.warning("등록된 종목이 없습니다.")
        return

    # 계좌 선택 필터
    accts = ["📊 전체"] + list(df["account"].unique())
    sel = st.radio("계좌 선택", accts, horizontal=True)
    
    # 데이터 필터링
    view_df = df if sel == "📊 전체" else df[df["account"] == sel]
    
    # 깔끔한 테이블 렌더링 (중복 방지)
    st.markdown("""
    <style>
    .asset-row { display: flex; justify-content: space-between; padding: 12px; border-bottom: 1px solid #222A3A; }
    .asset-name { font-weight: 600; color: #E4EAF6; }
    .asset-val { font-family: 'JetBrains Mono'; color: #388BFD; }
    </style>
    """, unsafe_allow_html=True)
    
    for _, row in view_df.iterrows():
        st.markdown(f"""
        <div class="asset-row">
            <div class="asset-name">{row['name']} <small style="color:#7A8CA4">({row['account']})</small></div>
            <div class="asset-val">{row['value']:,.0f} 원</div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
