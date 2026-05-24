"""
모니터링 지표 설정.
여기서 지표를 추가/삭제하면 수집 스크립트가 자동으로 반영합니다.
"""

# FRED (미국 세인트루이스 연준) 데이터
FRED_INDICATORS = {
    "US_10Y":         "DGS10",         # 미국 10년 국채금리
    "T10Y2Y_SPREAD":  "T10Y2Y",        # 10년-2년 스프레드
    "HY_OAS":         "BAMLH0A0HYM2",  # 하이일드 신용 스프레드
    "VIX_FRED":       "VIXCLS",        # VIX (백업용)
    "DXY_BROAD":      "DTWEXBGS",      # 달러 인덱스 (백업용)
    "FFR_UPPER":      "DFEDTARU",      # 미국 연방기준금리 상단
    "US_CORE_CPI":    "CPILFESL",      # 미국 코어 CPI (월간)
    "US_NFP":         "PAYEMS",        # 미국 비농업 고용 (월간)
}
# yfinance 티커
# 형식: 우리 이름 -> (ticker, sanity check 값 범위)
YFINANCE_TICKERS = {
    "VIX":    ("^VIX",     (5.0,   100.0)),     # 변동성 지수
    "SOX":    ("^SOX",     (500.0, 8000.0)),    # 필라델피아 반도체
    "DXY":    ("DX-Y.NYB", (80.0,  130.0)),     # 달러 인덱스
    "USDKRW": ("KRW=X",    (900.0, 2000.0)),    # 원달러 환율
    "KOSPI":  ("^KS11",    (1000.0,5000.0)),    # KOSPI
    "SPX":    ("^GSPC",    (1000.0,10000.0)),   # S&P 500
}

# 헬스체크 기준 (check_health.py가 사용)
HEALTH_CHECKS = {
    "fred_indicators.parquet": {"max_lag_days": 10, "min_rows": 1000},
    "market_prices.parquet":   {"max_lag_days": 5,  "min_rows": 1000},
    "kospi_flows.parquet":     {"max_lag_days": 5,  "min_rows": 100},
    "sentiment.parquet":       {"max_lag_days": 3,  "min_rows": 1},
    "ecos_latest.parquet":     {"max_lag_days": 5,  "min_rows": 50},
}
