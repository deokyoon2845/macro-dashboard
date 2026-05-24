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
