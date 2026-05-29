"""Telegram 채널 최신 포스트 수집 (Telethon MTProto)"""
import json, os, asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
OUT  = DATA / "telegram_feed.json"

# ── 관심 채널 설정 ──────────────────────────────────────────
# 채널 username: t.me/채널명 에서 채널명 부분
CHANNELS = [
    "investingcom_kr",   # Investing.com 한국
    "maekyungsns",       # 매일경제
    # "채널username",    # 원하는 채널 추가
]

MAX_MESSAGES  = 10    # 채널당 최근 N개
MSG_CHAR_LIMIT = 500  # 포스트 최대 글자수
HOURS_BACK    = 24    # 최근 N시간 이내 포스트만

# ── 인증 정보 (GitHub Secrets로 관리) ───────────────────────
API_ID      = os.environ.get("TELEGRAM_API_ID", "")
API_HASH    = os.environ.get("TELEGRAM_API_HASH", "")
SESSION_STR = os.environ.get("TELEGRAM_SESSION", "")  # StringSession


async def fetch_channels():
    if not all([API_ID, API_HASH, SESSION_STR]):
        print("⚠ TELEGRAM_API_ID / API_HASH / SESSION 없음"); return None

    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except ImportError:
        print("⚠ telethon 미설치: pip install telethon"); return None

    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_BACK)
    results = {}

    async with TelegramClient(
        StringSession(SESSION_STR), int(API_ID), API_HASH
    ) as client:
        for channel_username in CHANNELS:
            print(f"\n📱 [{channel_username}]")
            try:
                entity = await client.get_entity(channel_username)
                posts = []
                async for msg in client.iter_messages(entity, limit=MAX_MESSAGES):
                    if not msg.text: continue
                    if msg.date.replace(tzinfo=timezone.utc) < cutoff: break
                    text = msg.text[:MSG_CHAR_LIMIT].replace("\n"," ").strip()
                    posts.append({
                        "id":   msg.id,
                        "text": text,
                        "date": msg.date.strftime("%Y-%m-%d %H:%M"),
                        "url":  f"https://t.me/{channel_username}/{msg.id}"
                    })
                    print(f"  ▸ {text[:50]}")
                results[channel_username] = posts
            except Exception as e:
                print(f"  ✗ {channel_username}: {e}")
                results[channel_username] = []

    return results


def main():
    results = asyncio.run(fetch_channels())
    if results is None: return

    output = {
        "updated":  datetime.now().strftime("%Y-%m-%d %H:%M"),
        "channels": results,
        "total":    sum(len(v) for v in results.values())
    }
    DATA.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Telegram 수집 완료: {output['total']}개 포스트")


if __name__ == "__main__": main()
