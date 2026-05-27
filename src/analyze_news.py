"""뉴스 AI 분석 — Claude Haiku로 한 줄 요약 + 감성 점수"""
import json, os, re, time, hashlib
from pathlib import Path
from datetime import datetime

try:
    from anthropic import Anthropic
except ImportError:
    print("⚠ anthropic 미설치"); raise SystemExit(0)

ROOT = Path(__file__).parent.parent
DATA = ROOT/"data"
NEWS_FILE  = DATA/"portfolio_news.json"
CACHE_FILE = DATA/"news_analysis_cache.json"
API_KEY = os.environ.get("ANTHROPIC_API_KEY","")
MODEL   = "claude-haiku-4-5-20251001"

def url_hash(u): return hashlib.md5(u.encode()).hexdigest()[:12]

def load_json(p, d):
    if p.exists():
        with open(p, encoding="utf-8") as f: return json.load(f)
    return d

def save_json(p, data):
    p.parent.mkdir(exist_ok=True)
    with open(p,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)

def analyze_one(client, title, summary, context=""):
    ctx = f"종목/섹터: {context}\n" if context else ""
    prompt = (f"{ctx}뉴스 제목: {title}\n내용: {summary[:280]}\n\n"
              "다음 JSON 형식으로만 응답 (다른 텍스트 금지):\n"
              '{"summary":"50자 이내 한국어 요약","score":0~10 정수(5=중립,10=극호재,0=극악재),"tags":["키워드1","키워드2"]}')
    try:
        msg = client.messages.create(model=MODEL, max_tokens=250,
            messages=[{"role":"user","content":prompt}])
        text = msg.content[0].text.strip()
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if not m: return None
        r = json.loads(m.group())
        if "summary" not in r or "score" not in r: return None
        r["score"] = max(0, min(10, int(r.get("score",5))))
        r["tags"] = (r.get("tags") or [])[:3]
        r["summary"] = str(r["summary"])[:80]
        return r
    except Exception as e: print(f"    ✗ {title[:30]}: {e}"); return None

def main():
    if not API_KEY: print("⚠ ANTHROPIC_API_KEY 없음"); return
    if not NEWS_FILE.exists(): print("portfolio_news.json 없음"); return
    news_data = load_json(NEWS_FILE, {}); cache = load_json(CACHE_FILE, {})
    client = Anthropic(api_key=API_KEY)
    targets = [(cat,key,idx,n) for cat in ("stocks","sectors")
               for key,articles in news_data.get(cat,{}).items()
               for idx,n in enumerate(articles)]
    print(f"🤖 AI 분석 — {len(targets)}건")
    new_cnt = cache_cnt = 0
    for cat,key,idx,n in targets:
        h = url_hash(n.get("url") or n.get("title",""))
        if h in cache:
            for fld in ("ai_summary","score","tags"):
                if fld in cache[h]: news_data[cat][key][idx][fld]=cache[h][fld]
            cache_cnt += 1; continue
        r = analyze_one(client, n.get("title",""), n.get("summary",""), context=key)
        if r:
            news_data[cat][key][idx].update({"ai_summary":r["summary"],"score":r["score"],"tags":r["tags"]})
            cache[h] = {**r,"analyzed_at":datetime.now().isoformat()}
            new_cnt += 1; print(f"  ✓ [{key}] {n['title'][:30]} → {r['score']}")
        time.sleep(0.3)
    news_data["analyzed_at"] = datetime.now().isoformat()
    save_json(NEWS_FILE, news_data); save_json(CACHE_FILE, cache)
    print(f"✅ 완료 — 신규 {new_cnt}건 · 캐시 {cache_cnt}건")

if __name__ == "__main__": main()
