"""
src/fetch_trending.py
한국 주식 트렌딩 수집 — 거래량 급증 · 등락률 상위/하위 · 뉴스 언급
결과: data/trending.json
GitHub Actions에서 매일 아침 실행
"""
import json, os, re, time
from pathlib import Path
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("⚠ pip install requests beautifulsoup4")
    raise SystemExit(0)

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
OUT  = DATA / "trending.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}

NAVER_ID     = os.environ.get("NAVER_CLIENT_ID", "").strip()
NAVER_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "").strip()

# ════════════════════════════════════════════════════════════════
# 네이버 금융 — 거래량 급증 / 등락률 상위·하위 스크래핑
# ════════════════════════════════════════════════════════════════
def parse_sise_table(url, limit=15):
    """네이버 금융 시세 테이블 파싱 (거래상위/상승/하락 공통)"""
    rows = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = "euc-kr"   # 네이버 금융은 euc-kr
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.select_one("table.type_2")
        if not table:
            return rows
        for tr in table.select("tr"):
            a = tr.select_one("a.tltle")
            if not a:
                continue
            tds = tr.select("td")
            if len(tds) < 6:
                continue
            name = a.get_text(strip=True)
            href = a.get("href", "")
            m = re.search(r"code=(\d+)", href)
            code = m.group(1) if m else ""
            try:
                price = tds[2].get_text(strip=True).replace(",", "")
                # 등락률: 보통 5번째 td (red/blue span)
                chg_txt = tds[4].get_text(strip=True).replace("%", "").replace(",", "")
                chg = float(chg_txt) if chg_txt and chg_txt not in ("-", "") else 0.0
                # 하락이면 음수 처리: class에 'nv'(파랑) 있으면 음수
                cls = tds[4].get("class", []) or (tds[4].find("span").get("class", []) if tds[4].find("span") else [])
                cls_str = " ".join(cls) if isinstance(cls, list) else str(cls)
                if "nv" in cls_str or "down" in cls_str:
                    chg = -abs(chg)
                vol = tds[5].get_text(strip=True).replace(",", "")
                rows.append({
                    "name": name, "code": code,
                    "price": int(price) if price.isdigit() else 0,
                    "change_pct": chg,
                    "volume": int(vol) if vol.isdigit() else 0,
                })
            except Exception:
                continue
            if len(rows) >= limit:
                break
    except Exception as e:
        print(f"  파싱 오류 {url}: {e}")
    return rows

def fetch_volume_surge(market=0, limit=12):
    """거래량 상위 — sosok=0(코스피) / 1(코스닥)"""
    url = f"https://finance.naver.com/sise/sise_quant.naver?sosok={market}"
    return parse_sise_table(url, limit)

def fetch_rising(market=0, limit=12):
    """상승률 상위"""
    url = f"https://finance.naver.com/sise/sise_rise.naver?sosok={market}"
    return parse_sise_table(url, limit)

def fetch_falling(market=0, limit=12):
    """하락률 상위"""
    url = f"https://finance.naver.com/sise/sise_fall.naver?sosok={market}"
    return parse_sise_table(url, limit)

# ════════════════════════════════════════════════════════════════
# yfinance — 거래량 배수 (당일 / 20일 평균)
# ════════════════════════════════════════════════════════════════
def compute_volume_ratio(stocks):
    """각 종목의 당일 거래량 / 20일 평균 거래량 배수 계산"""
    try:
        import yfinance as yf
    except ImportError:
        return stocks
    for s in stocks:
        code = s.get("code", "")
        if not code:
            continue
        ratio = None
        for suffix in (".KS", ".KQ"):
            try:
                hist = yf.Ticker(code + suffix).history(period="1mo")
                if hist.empty or "Volume" not in hist.columns:
                    continue
                vols = hist["Volume"].dropna()
                if len(vols) >= 6:
                    today_vol = float(vols.iloc[-1])
                    avg20 = float(vols.iloc[-21:-1].mean()) if len(vols) >= 21 else float(vols.iloc[:-1].mean())
                    if avg20 > 0:
                        ratio = round(today_vol / avg20, 1)
                        break
            except Exception:
                continue
        s["vol_ratio"] = ratio   # 평소 대비 배수 (None이면 계산 실패)
        time.sleep(0.08)
    return stocks

# ════════════════════════════════════════════════════════════════
# 네이버 뉴스 API — 종목별 언급 건수
# ════════════════════════════════════════════════════════════════
def fetch_news_count(query):
    """최근 뉴스 검색 결과 총 건수 반환"""
    if not NAVER_ID or not NAVER_SECRET:
        return 0, ""
    try:
        url = "https://openapi.naver.com/v1/search/news.json"
        hdr = {"X-Naver-Client-Id": NAVER_ID,
               "X-Naver-Client-Secret": NAVER_SECRET}
        params = {"query": query, "display": 1, "sort": "date"}
        r = requests.get(url, headers=hdr, params=params, timeout=8)
        if r.status_code == 200:
            data = r.json()
            total = data.get("total", 0)
            items = data.get("items", [])
            latest = re.sub("<.*?>", "", items[0]["title"]) if items else ""
            return total, latest
    except Exception:
        pass
    return 0, ""

def build_news_ranking(stock_names, limit=10):
    """거래량/등락 상위 종목들의 뉴스 언급 건수 순위"""
    ranking = []
    seen = set()
    for name in stock_names:
        if name in seen:
            continue
        seen.add(name)
        cnt, latest = fetch_news_count(name)
        if cnt > 0:
            ranking.append({"name": name, "news_count": cnt, "latest_title": latest})
        time.sleep(0.12)  # API rate limit 여유
    ranking.sort(key=lambda x: -x["news_count"])
    return ranking[:limit]

# ════════════════════════════════════════════════════════════════
# 섹터 자금 흐름 집계 (1순위)
# ════════════════════════════════════════════════════════════════
# 네이버는 섹터 정보를 안 주므로, 종목명 키워드 기반 간이 분류 + watchlist 보강
SECTOR_KEYWORDS = {
    "반도체": ["반도체","하이닉스","SK하이","DB하이텍","한미반도체","원익","주성","에스에프에이","리노공업","ISC","HPSP","파크시스템스"],
    "방산": ["한화에어로","한화시스템","LIG넥스원","현대로템","한국항공","KAI","풍산","스페이스"],
    "2차전지": ["에코프로","엘앤에프","포스코퓨처엠","LG에너지","삼성SDI","SK이노","천보","나노신소재","코스모"],
    "로봇·AI": ["로보","로봇","레인보우","두산로보","휴머노이드","AI","뉴로메카","에스피지"],
    "바이오": ["바이오","제약","셀트리온","삼성바이오","유한양행","한미약품","녹십자","에이비엘","알테오젠","리가켐"],
    "증권·금융": ["증권","금융지주","은행","키움","미래에셋","삼성증권","NH투자","한국금융","카카오뱅크","KB"],
    "자동차": ["현대차","기아","모비스","현대위아","HL만도","에스엘"],
    "조선": ["중공업","조선","HD한국조선","삼성중공업","한화오션","HD현대"],
    "엔터·미디어": ["하이브","JYP","SM","와이지","에스엠","엔터","CJ ENM","스튜디오"],
    "원전·전력": ["일렉트릭","두산에너빌","한전","전력","원전","비에이치아이","우진"],
}

def classify_sector(name):
    for sector, kws in SECTOR_KEYWORDS.items():
        for kw in kws:
            if kw in name:
                return sector
    return "기타"

def compute_sector_flow(rising, falling):
    """섹터별 순자금 흐름 점수 = 상승 종목수 - 하락 종목수 (등락률 가중)"""
    flow = {}
    for s in rising:
        sec = classify_sector(s.get("name",""))
        flow.setdefault(sec, {"up":0,"down":0,"score":0.0,"stocks":[]})
        flow[sec]["up"] += 1
        flow[sec]["score"] += abs(s.get("change_pct",0))
        flow[sec]["stocks"].append({"name":s.get("name",""),"pct":s.get("change_pct",0)})
    for s in falling:
        sec = classify_sector(s.get("name",""))
        flow.setdefault(sec, {"up":0,"down":0,"score":0.0,"stocks":[]})
        flow[sec]["down"] += 1
        flow[sec]["score"] -= abs(s.get("change_pct",0))
        flow[sec]["stocks"].append({"name":s.get("name",""),"pct":s.get("change_pct",0)})
    # 기타는 제외하고 정렬
    out = [{"sector":k, **v} for k,v in flow.items() if k != "기타"]
    out.sort(key=lambda x: -x["score"])
    return out

def compute_breadth(rising, falling, volume):
    """시장 폭(Market Breadth) 한 줄 요약 (4순위)"""
    up_n   = len(rising)
    down_n = len(falling)
    avg_chg = 0.0
    all_chg = [s.get("change_pct",0) for s in (rising+falling)]
    if all_chg:
        avg_chg = sum(all_chg)/len(all_chg)
    # 거래량 급증 종목 평균 등락률 — 자금이 상승/하락 어디로?
    vol_chg = [s.get("change_pct",0) for s in volume]
    vol_avg = sum(vol_chg)/len(vol_chg) if vol_chg else 0.0
    if vol_avg > 1.0:
        regime = "위험선호 (자금 유입 우세)"
    elif vol_avg < -1.0:
        regime = "위험회피 (자금 이탈 우세)"
    else:
        regime = "중립 (혼조세)"
    return {"up_count":up_n, "down_count":down_n,
            "avg_change":round(avg_chg,2), "vol_avg_change":round(vol_avg,2),
            "regime":regime}

# ════════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════════
def main():
    print("📊 트렌딩 수집 시작…")
    result = {"updated": datetime.now().strftime("%Y-%m-%d %H:%M")}

    # 거래량 급증 (코스피+코스닥 합쳐서 상위)
    vol_kospi  = fetch_volume_surge(0, 10)
    vol_kosdaq = fetch_volume_surge(1, 8)
    volume = sorted(vol_kospi + vol_kosdaq, key=lambda x: -x["volume"])[:15]
    # 평소 대비 거래량 배수 계산 후, 배수 기준 재정렬
    volume = compute_volume_ratio(volume)
    volume = sorted(volume, key=lambda x: -(x.get("vol_ratio") or 0))[:12]
    result["volume_surge"] = volume
    print(f"  거래량 급증: {len(volume)}건 (배수 계산 완료)")

    # 등락률
    rising  = fetch_rising(0, 8) + fetch_rising(1, 6)
    falling = fetch_falling(0, 8) + fetch_falling(1, 6)
    result["rising"]  = sorted(rising,  key=lambda x: -x["change_pct"])[:12]
    result["falling"] = sorted(falling, key=lambda x: x["change_pct"])[:12]
    print(f"  상승률: {len(result['rising'])}건, 하락률: {len(result['falling'])}건")

    # 뉴스 언급 — 위 종목들 대상
    candidates = [s["name"] for s in (volume + result["rising"] + result["falling"])]
    result["news_ranking"] = build_news_ranking(candidates, 10)
    print(f"  뉴스 언급 순위: {len(result['news_ranking'])}건")

    # 섹터 자금 흐름 (1순위)
    result["sector_flow"] = compute_sector_flow(result["rising"], result["falling"])
    print(f"  섹터 흐름: {len(result['sector_flow'])}개 섹터")

    # 시장 폭 (4순위)
    result["breadth"] = compute_breadth(result["rising"], result["falling"], volume)
    print(f"  시장 레짐: {result['breadth']['regime']}")

    # 종목별 섹터 태그 부착 (2순위 — 페이지에서 내 포트와 매칭)
    for key in ("volume_surge","rising","falling"):
        for s in result.get(key, []):
            s["sector"] = classify_sector(s.get("name",""))

    DATA.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 저장 완료: {OUT}")

if __name__ == "__main__":
    main()
