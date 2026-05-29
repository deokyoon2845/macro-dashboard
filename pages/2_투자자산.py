"""
2. 투자자산 — 계좌별 관리 + 블루/레드 팔레트 + 스티키 네비
포트폴리오 대시보드, 계좌별 성과, 뉴스/공시 및 리스크 지표 트래킹
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
st.set_page_config(page_title="투자자산", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# 세션 상태 초기화 (에러 방지)
if "chart_range" not in st.session_state:
    st.session_state.chart_range = "3M"

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from utils import render_sticky_nav
    render_sticky_nav()
except Exception:
    pass

DATA = _ROOT / "data"
ASSET_DIR = _ROOT / "assets"
PORT_FILE = DATA / "portfolio.json"
PRICE_FILE = DATA / "portfolio_prices.parquet"
MARKET_FILE = DATA / "market_prices.parquet"
NEWS_FILE = DATA / "portfolio_news.json"
DISC_FILE = DATA / "portfolio_disclosures.json"

# 디자인 상수
BG, CARD, C2, C3 = "#0A0D13", "#111620", "#161C28", "#1C2438"
BORD, G, TXT, SUB, MUT = "#222A3A", "#181F2C", "#E4EAF6", "#7A8CA4", "#4A5668"
B5, UP, DN = "#388BFD", "#E24B4A", "#388BFD"
HOLD_COLORS = ["#388BFD","#79C0FF","#1F6FEB","#58A6FF","#CAE8FF","#2F81F7","#4A82E4","#9ECEFF","#1158C7","#56D3FF","#0D6EFD","#B0D9FF"]

# 데이터 로드 함수들
def load_portfolio():
    if PORT_FILE.exists():
        try:
            with open(PORT_FILE, encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_portfolio(data):
    DATA.mkdir(exist_ok=True)
    with open(PORT_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

@st.cache_data(ttl=600)
def load_parquet(path):
    if path.exists():
        try:
            df = pd.read_parquet(path)
            if "date" in df.columns: df["date"] = pd.to_datetime(df["date"])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

# 로직 함수 (생략... 기존 함수 그대로 유지)
def compute_pos(item, prices, usdkrw):
    # (생략된 기존 함수 내용 사용)
    return {} 

# 메인 실행 함수
def main():
    portfolio = load_portfolio()
    prices = load_parquet(PRICE_FILE)
    
    # 1. 데이터프레임 처리 (오류 발생지점 수정)
    df = pd.DataFrame(portfolio) if portfolio else pd.DataFrame()
    
    if not df.empty:
        # 합산 및 계산 로직
        df = df.groupby(["name", "ticker"]).agg({
            "qty": "sum",
            "value_krw": "sum",
            "cost_krw": "sum"
        }).reset_index()
        
        # 수익률 및 데이터 정렬
        df = df.sort_values("value_krw", ascending=False)
    
    # 총액 계산
    tv = df["value_krw"].sum() if not df.empty else 0
    
    # 2. 루프 렌더링
    holding_rows = ""
    for i, row in df.iterrows():
        # HTML 렌더링 로직
        holding_rows += f"<div>{row['name']}</div>"
        
    st.markdown(holding_rows, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
