"""보유 종목 + 산업 뉴스 수집 — 네이버 API + 구글 뉴스 RSS"""
import json, os, re, time, requests
from pathlib import Path
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, quote
from xml.etree import ElementTree as ET

ROOT = Path(__file__).parent.parent
DATA = ROOT/"data"
PORT_FILE = DATA/"portfolio.json"
OUT_FILE  = DATA/"portfolio_news.json"

NAVER_ID  = os.environ.get("NAVER_CLIENT_ID","")
NAVER_SEC = os.environ.get("NAVER_CLIENT_SECRET","")
NAVER_URL = "https://openapi.naver.com/v1/search/news.json"

SECTOR_KEYWORDS = {
    "반도체":["반도체 업황","반도체 시장"],     "방산":["방위산업","방산 수주"],
    "증권·금융":["증권업","금융지주"],          "우주항공":["우주항공","우주개발"],
    "로봇·자동화":["로봇 산업","산업자동화"],   "2차전지":["2차전지","배터리 시장"],
    "바이오":["바이오 시장","제약바이오"],       "IT·소프트웨어":["IT 업계","소프트웨어"],
    "엔터·미디어":["엔터테인먼트","미디어"],    "자동차":["자동차 산업","전기차"],
    "화학":["화학 업황"],                       "철강·소재":["철강 시황"],
}

def clean_html(t):
    if not t: return ""
    t = re.sub(r'<[^>]+>','',t)
    for a,b in [('&quot;','"'),('&amp;','&'),('&lt;','<'),('&gt;','>'),('&nbsp;',' ')]:
        t = t.replace(a,b)
    return t.strip()

def parse_date(s):
    try: return parsedate_to_datetime(s).isoformat()
    except: return s or ""

def naver_search(query, display=8):
    if not NAVER_ID: return []
    try:
        res = requests.get(NAVER_URL,
            headers={"X-Naver-Client-Id":NAVER_ID,"X-Naver-Client-Secret":NAVER_SEC},
            params={"query":query,"display":display,"sort":"date"}, timeout=10)
        if res.status_code != 200: return []
        return [{"title":clean_html(it.get("title","")),
                 "url":it.get("originallink") or it.get("link",""),
                 "summary":clean_html(it.get("description",""))[:200],
                 "source":urlparse(it.get("originallink") or "").netloc.replace("www.",""),
                 "pub_date":parse_date(it.get("pubDate",""))} for it in res.json().get("items",[])]
    except Exception as e: print(f"  ✗ {query}: {e}"); return []

def google_rss(query, lang="en"):
    try:
        q = quote(query)
        url = (f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko" if lang=="ko"
               else f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en")
        res = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        if res.status_code != 200: return []
        items = []
        for it in ET.fromstring(res.content).findall(".//item")[:8]:
            t=it.find("title"); l=it.find("link"); pd_=it.find("pubDate"); d=it.find("description")
            if t is None or l is None: continue
            items.append({"title":clean_html(t.text or ""),"url":l.text or "",
                          "summary":clean_html(d.text or "")[:200] if d is not None else "",
                          "source":"Google News","pub_date":parse_date(pd_.text) if pd_ else ""})
        return items
    except Exception as e: print(f"  ✗ google {query}: {e}"); return []

def dedup(lst, limit=3):
    seen_url, seen_title, result = set(), set(), []
    for n in lst:
        url_k = n.get("url","").split("?")[0].rstrip("/")
        ttl_k = re.sub(r'\s+','',n.get("title",""))[:25]
        if url_k in seen_url or ttl_k in seen_title: continue
        seen_url.add(url_k); seen_title.add(ttl_k); result.append(n)
        if len(result)>=limit: break
    return result

def main():
    if not PORT_FILE.exists(): print("portfolio.json 없음."); return
    with open(PORT_FILE, encoding="utf-8") as f: items = json.load(f)
    if not items: return
    print(f"📰 뉴스 수집 — {len(items)}개 종목")
    stock_news = {}; seen_sectors = set()
    for it in items:
        if not isinstance(it, dict): 
        continue # 딕셔너리가 아니면 건너뜀
        if it.get("currency","KRW") != "KRW": continue
        if not name: continue
        if sector and sector!="기타": seen_sectors.add(sector)
        print(f"  [{name}]")
        pool = naver_search(name, display=6)
        if currency=="USD" and ticker: pool += google_rss(ticker, lang="en")
        stock_news[name] = dedup(pool, limit=3)
        time.sleep(0.3)
    print(f"\n🏭 산업 뉴스 — {len(seen_sectors)}개")
    sector_news = {}
    for sec in seen_sectors:
        pool = []
        for kw in SECTOR_KEYWORDS.get(sec,[sec]):
            pool += naver_search(kw, display=4); time.sleep(0.3)
        sector_news[sec] = dedup(pool, limit=3)
        print(f"  [{sec}] {len(sector_news[sec])}건")
    output = {"updated":datetime.now().isoformat(),"stocks":stock_news,"sectors":sector_news}
    DATA.mkdir(exist_ok=True)
    with open(OUT_FILE,"w",encoding="utf-8") as f: json.dump(output,f,ensure_ascii=False,indent=2)
    print(f"✅ 완료 — 종목 {sum(len(v) for v in stock_news.values())}건 · 산업 {sum(len(v) for v in sector_news.values())}건")

if __name__ == "__main__": main()
