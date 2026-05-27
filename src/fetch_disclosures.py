"""DART 공시 자동 수집 — 보유 한국 종목 최근 14일"""
import json, os, re, io, zipfile, requests
from pathlib import Path
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

ROOT = Path(__file__).parent.parent
DATA = ROOT/"data"
PORT_FILE = DATA/"portfolio.json"
CORP_FILE = DATA/"dart_corp_codes.json"
OUT_FILE  = DATA/"portfolio_disclosures.json"
DART_KEY  = os.environ.get("DART_API_KEY","")

def fetch_corp_map():
    print("DART corp_code 다운로드…")
    try:
        res = requests.get("https://opendart.fss.or.kr/api/corpCode.xml",
            params={"crtfc_key":DART_KEY}, timeout=30)
        zf = zipfile.ZipFile(io.BytesIO(res.content))
        root = ET.fromstring(zf.read(zf.namelist()[0]))
        m = {}
        for item in root.findall("list"):
            sc=(item.findtext("stock_code") or "").strip()
            cc=(item.findtext("corp_code") or "").strip()
            nm=(item.findtext("corp_name") or "").strip()
            if sc and cc: m[sc]={"corp_code":cc,"name":nm}
        print(f"  ✓ {len(m)}개 매핑"); return m
    except Exception as e: print(f"  ✗ {e}"); return None

def load_corp_map():
    if CORP_FILE.exists():
        try:
            with open(CORP_FILE, encoding="utf-8") as f: data=json.load(f)
            if (datetime.now()-datetime.fromisoformat(data.get("updated","2000-01-01"))).days < 7:
                return data.get("mapping",{})
        except: pass
    m = fetch_corp_map()
    if m:
        DATA.mkdir(exist_ok=True)
        with open(CORP_FILE,"w",encoding="utf-8") as f:
            json.dump({"updated":datetime.now().isoformat(),"mapping":m},f,ensure_ascii=False)
        return m
    return {}

def ticker_to_code(ticker):
    m = re.match(r'^(\d{6})\.(KS|KQ)$', ticker or "")
    return m.group(1) if m else None

def fetch_disc(corp_code, days=14):
    try:
        bgn=(datetime.now()-timedelta(days=days)).strftime("%Y%m%d")
        end=datetime.now().strftime("%Y%m%d")
        res = requests.get("https://opendart.fss.or.kr/api/list.json",
            params={"crtfc_key":DART_KEY,"corp_code":corp_code,
                    "bgn_de":bgn,"end_de":end,"page_count":10,"page_no":1}, timeout=10)
        if res.status_code != 200: return []
        data = res.json()
        if data.get("status") != "000": return []
        return [{"title":d.get("report_nm",""),"filer":d.get("flr_nm",""),
                 "date":d.get("rcept_dt",""),
                 "url":f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={d.get('rcept_no','')}"}
                for d in data.get("list",[])]
    except Exception as e: print(f"  ✗ {corp_code}: {e}"); return []

def main():
    if not DART_KEY: print("⚠ DART_API_KEY 없음"); return
    if not PORT_FILE.exists(): return
    with open(PORT_FILE, encoding="utf-8") as f: items=json.load(f)
    corp_map = load_corp_map()
    if not corp_map: return
    print("\n📑 공시 수집")
    results = {}
    for it in items:
        if it.get("currency","KRW") != "KRW": continue
        sc = ticker_to_code(it.get("ticker",""))
        if not sc: continue
        info = corp_map.get(sc)
        if not info: continue
        disc = fetch_disc(info["corp_code"], days=14)
        results[it["name"]] = disc[:5]
        print(f"  [{it['name']}] {len(disc)}건")
    output = {"updated":datetime.now().isoformat(),"disclosures":results}
    DATA.mkdir(exist_ok=True)
    with open(OUT_FILE,"w",encoding="utf-8") as f: json.dump(output,f,ensure_ascii=False,indent=2)
    print(f"✅ 완료 — {sum(len(v) for v in results.values())}건")

if __name__ == "__main__": main()
