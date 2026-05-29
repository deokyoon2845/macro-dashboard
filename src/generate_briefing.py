"""
src/generate_briefing.py
일일 AI 브리핑 생성 — 시장·포트폴리오·뉴스·YouTube·Telegram 종합
결과: data/daily_briefing.json
"""
import json, os, re
from pathlib import Path
from datetime import datetime
import pandas as pd

try:
    from anthropic import Anthropic
except ImportError:
    print("⚠ anthropic 미설치: pip install anthropic")
    raise SystemExit(0)

# ════════════════════════════════════════════════════════════════
# 경로 / 설정
# ════════════════════════════════════════════════════════════════
ROOT     = Path(__file__).parent.parent
DATA     = ROOT / "data"
OUT_FILE = DATA / "daily_briefing.json"

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
MODEL   = "claude-haiku-4-5-20251001"

# ════════════════════════════════════════════════════════════════
# 공통 로더
# ════════════════════════════════════════════════════════════════
def load_pq(name):
    p = DATA / name
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df

def load_json(name, default=None):
    p = DATA / name
    if not p.exists():
        return default if default is not None else {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

# ════════════════════════════════════════════════════════════════
# 헬퍼
# ════════════════════════════════════════════════════════════════
def latest_val(df, ind):
    """지표의 최신값 반환 (float | None)"""
    if df.empty or "indicator" not in df.columns:
        return None
    s = df[df["indicator"] == ind].sort_values("date")
    return float(s.iloc[-1]["value"]) if not s.empty else None

def pct_chg(df, ind, n=2):
    """전일 대비 등락률 (float %)"""
    if df.empty or "indicator" not in df.columns:
        return 0.0
    s = df[df["indicator"] == ind].sort_values("date").tail(n)
    if len(s) < 2:
        return 0.0
    v0, v1 = float(s.iloc[-2]["value"]), float(s.iloc[-1]["value"])
    return (v1 / v0 - 1) * 100 if v0 else 0.0

# ════════════════════════════════════════════════════════════════
# 1. 시장 지표 섹션
# ════════════════════════════════════════════════════════════════
def build_market():
    market    = load_pq("market_prices.parquet")
    fred      = load_pq("fred_indicators.parquet")
    sentiment = load_pq("sentiment.parquet")
    lines     = []

    for ind, lbl in [
        ("SPX",    "S&P500"),
        ("NASDAQ", "NASDAQ"),
        ("KOSPI",  "KOSPI"),
        ("KOSDAQ", "KOSDAQ"),
    ]:
        v  = latest_val(market, ind)
        p  = pct_chg(market, ind)
        if v is not None:
            sym = "▲" if p >= 0 else "▼"
            lines.append(f"  {lbl}: {v:,.0f} ({sym}{abs(p):.2f}%)")

    for ind, lbl, fmt in [
        ("VIX",    "VIX",      ".1f"),
        ("USDKRW", "USD/KRW",  ",.0f"),
    ]:
        v = latest_val(market, ind)
        if v is not None:
            lines.append(f"  {lbl}: {format(v, fmt)}")

    v = latest_val(fred, "US_10Y")
    if v is not None:
        lines.append(f"  미국 10Y금리: {v:.2f}%")

    fg = latest_val(sentiment, "FEAR_GREED")
    if fg is not None:
        tone = "탐욕" if fg >= 70 else ("공포" if fg <= 30 else "중립")
        lines.append(f"  F&G 지수: {fg:.0f} ({tone})")

    return "\n".join(lines) if lines else "  (데이터 없음)"

# ════════════════════════════════════════════════════════════════
# 2. 포트폴리오 섹션
# ════════════════════════════════════════════════════════════════
def build_portfolio():
    items   = load_json("portfolio.json", [])
    prices  = load_pq("portfolio_prices.parquet")
    market  = load_pq("market_prices.parquet")

    if not items or prices.empty:
        return "  (보유 종목 데이터 없음)"

    fx = latest_val(market, "USDKRW") or 1380.0

    positions = []
    tv = 0.0
    tp = 0.0
    for it in items:
        lots   = it.get("lots", [])
        ticker = it.get("ticker", "")
        if not lots or not ticker:
            continue
        qty   = sum(l["qty"]             for l in lots)
        cost  = sum(l["qty"] * l["price"] for l in lots)
        avg   = cost / qty if qty > 0 else 0
        sub   = prices[prices["ticker"] == ticker].sort_values("date")
        if sub.empty:
            continue
        cur   = float(sub.iloc[-1]["close"])
        prev  = float(sub.iloc[-2]["close"]) if len(sub) >= 2 else cur
        fxv   = fx if it.get("currency") == "USD" else 1
        val   = cur * qty * fxv
        pnl   = (cur - avg) * qty * fxv
        dpct  = (cur / prev - 1) * 100 if prev > 0 else 0.0
        tv   += val
        tp   += pnl
        # 계좌 정보 포함
        acct  = it.get("account", "일반")
        positions.append({
            "name":     it["name"],
            "account":  acct,
            "sector":   it.get("sector", ""),
            "value":    val,
            "pnl_krw":  pnl,
            "pnl_pct":  (cur / avg - 1) * 100 if avg > 0 else 0.0,
            "daily_pct": dpct,
        })

    if not positions:
        return "  (가격 데이터 없음)"

    tpct = tp / (tv - tp) * 100 if (tv - tp) > 0 else 0.0

    # 일간 상승 TOP 3
    up_str = ", ".join(
        f"{p['name']}({p['daily_pct']:+.2f}%)"
        for p in sorted(positions, key=lambda x: x["daily_pct"], reverse=True)[:3]
        if p["daily_pct"] > 0
    )
    # 일간 하락 TOP 3
    dn_str = ", ".join(
        f"{p['name']}({p['daily_pct']:+.2f}%)"
        for p in sorted(positions, key=lambda x: x["daily_pct"])[:3]
        if p["daily_pct"] < 0
    )

    nl = "\n"
    lines = [
        f"  총평가금액: {tv:,.0f}원",
        f"  누적손익:   {tp:+,.0f}원 ({tpct:+.2f}%)",
        f"  일간 상승: {up_str or '없음'}",
        f"  일간 하락: {dn_str or '없음'}",
    ]

    # 계좌별 요약
    acct_vals = {}
    for p in positions:
        acct_vals[p["account"]] = acct_vals.get(p["account"], 0) + p["value"]
    if len(acct_vals) > 1:
        acct_line = "  계좌별: " + " | ".join(
            f"{a} {v/1e6:.1f}M원"
            for a, v in sorted(acct_vals.items(), key=lambda x: -x[1])
        )
        lines.append(acct_line)

    return nl.join(lines)

# ════════════════════════════════════════════════════════════════
# 3. AI 점수 뉴스 섹션
# ════════════════════════════════════════════════════════════════
def build_news():
    news_data = load_json("portfolio_news.json", {})
    lines     = []

    for cat in ("stocks", "sectors"):
        for key, articles in news_data.get(cat, {}).items():
            for n in articles:
                sc = n.get("score")
                if sc is not None and (sc >= 8 or sc <= 2):
                    tag     = "호재" if sc >= 6 else "악재"
                    summary = n.get("ai_summary") or n.get("title", "")[:60]
                    lines.append(f"  [{tag} {sc}] {key}: {summary}")

    # 호재 먼저, 악재 나중
    lines.sort(key=lambda x: ("악재" in x, x))
    return "\n".join(lines[:8]) if lines else "  (주요 뉴스 없음)"

# ════════════════════════════════════════════════════════════════
# 4. YouTube 피드 섹션
# ════════════════════════════════════════════════════════════════
def build_youtube():
    yt_data = load_json("youtube_feed.json", {})
    lines   = []

    for ch, videos in yt_data.get("channels", {}).items():
        for v in videos[:2]:
            transcript = v.get("transcript", "")
            if not transcript:
                continue
            snippet = transcript[:200].replace("\n", " ")
            lines.append(f"  [{ch}] {v.get('title', '')[:40]}: {snippet}…")

    return "\n".join(lines[:6]) if lines else ""   # 없으면 빈 문자열 → 섹션 자체 생략

# ════════════════════════════════════════════════════════════════
# 5. Telegram 피드 섹션
# ════════════════════════════════════════════════════════════════
def build_telegram():
    tg_data = load_json("telegram_feed.json", {})
    lines   = []

    for ch, posts in tg_data.get("channels", {}).items():
        for p in posts[:3]:
            text = p.get("text", "")[:150].replace("\n", " ")
            if text:
                lines.append(f"  [@{ch}] {text}")

    return "\n".join(lines[:6]) if lines else ""   # 없으면 빈 문자열 → 섹션 자체 생략

# ════════════════════════════════════════════════════════════════
# 6. 프롬프트 빌더
# ════════════════════════════════════════════════════════════════
def build_prompt():
    today_str = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")

    market_sec    = build_market()
    portfolio_sec = build_portfolio()
    news_sec      = build_news()
    yt_sec        = build_youtube()
    tg_sec        = build_telegram()

    # YouTube / Telegram 섹션은 데이터 있을 때만 포함
    extra_sections = ""
    if yt_sec:
        extra_sections += f"\n▣ YouTube 주요 채널 최신 영상\n{yt_sec}\n"
    if tg_sec:
        extra_sections += f"\n▣ Telegram 채널 최신 포스트\n{tg_sec}\n"

    return (
        f"한국 retail 투자자를 위한 오늘의 투자 브리핑을 작성하세요.\n\n"
        f"[{today_str} 기준]\n\n"
        f"▣ 글로벌 시장 지표\n{market_sec}\n\n"
        f"▣ 보유 포트폴리오 현황\n{portfolio_sec}\n\n"
        f"▣ AI 점수 주요 뉴스 (8↑호재 / 2↓악재)\n{news_sec}\n"
        f"{extra_sections}\n"
        f"다음 JSON만 반환 (다른 텍스트 일절 금지):\n"
        f'{{"headline":"오늘 핵심 1줄 (25자 이내)",'
        f'"market":"시장 분석 — 지수·등락률·원인 구체적으로 2-3문장",'
        f'"holdings":"보유 종목 분석 — 상승/하락 종목과 이유 2-3문장",'
        f'"sectors":"보유 섹터(반도체·방산·증권 등) 흐름 1-2문장",'
        f'"news":"주목 뉴스 및 영향 1-2문장",'
        f'"action":"투자 액션 코멘트 1문장 (관망/매수/비중조절 등)",'
        f'"mood":"positive 또는 neutral 또는 cautious"}}'
    )

# ════════════════════════════════════════════════════════════════
# 7. 메인
# ════════════════════════════════════════════════════════════════
def main():
    # API 키 검증
    if not API_KEY:
        print("⚠ ANTHROPIC_API_KEY 환경변수가 없습니다."); return
    if API_KEY.startswith("*") or len(API_KEY) < 20:
        print("⚠ ANTHROPIC_API_KEY가 올바르지 않습니다 — GitHub Secrets를 확인하세요."); return

    prompt = build_prompt()
    print(f"🤖 브리핑 생성 중… (모델: {MODEL})")

    try:
        client = Anthropic(api_key=API_KEY)
        msg    = client.messages.create(
            model=MODEL, max_tokens=900,
            messages=[{"role": "user", "content": prompt}]
        )
        text = msg.content[0].text.strip()

        # JSON 추출
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if not m:
            print(f"✗ JSON 파싱 실패 — 원문:\n{text[:300]}"); return

        result = json.loads(m.group())

        # 필수 키 보완
        result.setdefault("headline",  "브리핑 생성 완료")
        result.setdefault("market",    "")
        result.setdefault("holdings",  "")
        result.setdefault("sectors",   "")
        result.setdefault("news",      "")
        result.setdefault("action",    "")
        result.setdefault("mood",      "neutral")

        result["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        result["realtime"]     = False   # Actions에서 생성 = 실시간 아님

        # 저장
        DATA.mkdir(exist_ok=True)
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        mood_label = {"positive":"✅ 긍정","neutral":"➡ 중립","cautious":"⚠ 주의"}\
                     .get(result["mood"], "")
        print(f"✅ 완료 {mood_label}")
        print(f"   헤드라인: {result['headline']}")
        print(f"   액션: {result['action']}")

    except Exception as e:
        print(f"✗ 오류: {e}")
        raise


if __name__ == "__main__":
    main()
