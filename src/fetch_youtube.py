"""YouTube 채널 최신 영상 자막 수집"""
import json, re, time
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
OUT  = DATA / "youtube_feed.json"

# ── 관심 채널 설정 ──────────────────────────────────────────
# 채널 ID 찾는 법: YouTube 채널 → 정보 탭 → "채널 ID 공유"
CHANNELS = {
    "삼프로TV":       "UCsJ6RoAZcbm4OBwMNsOznzA",
    "신과함께투자":   "CHANNEL_ID_HERE",
    "매일경제":       "CHANNEL_ID_HERE",
    # 원하는 채널 추가
}

MAX_VIDEOS_PER_CHANNEL = 3   # 채널당 최근 N개
TRANSCRIPT_LIMIT_CHARS = 2000  # 자막 최대 글자 수


def get_channel_latest(channel_id: str, max_results: int = 5):
    """채널 RSS로 최신 영상 목록 가져오기 (API 키 불필요)"""
    import requests
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200: return []
        from xml.etree import ElementTree as ET
        ns = {"atom":"http://www.w3.org/2005/Atom",
              "yt":"http://www.youtube.com/xml/schemas/2015",
              "media":"http://search.yahoo.com/mrss/"}
        root = ET.fromstring(res.content)
        videos = []
        for entry in root.findall("atom:entry", ns)[:max_results]:
            vid_id = entry.find("yt:videoId", ns)
            title  = entry.find("atom:title", ns)
            pub    = entry.find("atom:published", ns)
            if vid_id is None or title is None: continue
            videos.append({
                "video_id": vid_id.text,
                "title":    title.text or "",
                "url":      f"https://www.youtube.com/watch?v={vid_id.text}",
                "published": pub.text if pub is not None else "",
            })
        return videos
    except Exception as e:
        print(f"  ✗ {channel_id}: {e}"); return []


def get_transcript(video_id: str, limit: int = TRANSCRIPT_LIMIT_CHARS):
    """영상 자막 가져오기 (youtube-transcript-api)"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        # 한국어 우선, 없으면 영어
        for lang in (["ko"], ["ko-KR"], ["en"], None):
            try:
                segs = (YouTubeTranscriptApi.get_transcript(video_id, languages=lang)
                        if lang else
                        YouTubeTranscriptApi.get_transcript(video_id))
                text = " ".join(s["text"] for s in segs)
                text = re.sub(r'\s+', ' ', text).strip()
                return text[:limit]
            except: continue
    except Exception as e:
        print(f"  ✗ transcript {video_id}: {e}")
    return ""


def main():
    # 최근 48시간 이내 영상만 수집
    cutoff = datetime.utcnow() - timedelta(hours=48)
    results = {}

    for ch_name, ch_id in CHANNELS.items():
        print(f"\n📺 [{ch_name}]")
        videos = get_channel_latest(ch_id, MAX_VIDEOS_PER_CHANNEL)
        ch_data = []

        for v in videos:
            # 최신 영상인지 확인
            pub = v.get("published","")
            try:
                pub_dt = datetime.fromisoformat(pub.replace("Z","+00:00")).replace(tzinfo=None)
                if pub_dt < cutoff:
                    print(f"  ⏭ 오래된 영상: {v['title'][:30]}")
                    continue
            except: pass

            print(f"  ▸ {v['title'][:45]}")
            transcript = get_transcript(v["video_id"])
            if transcript:
                print(f"    ✓ 자막 {len(transcript)}자")
            ch_data.append({**v, "transcript": transcript})
            time.sleep(0.5)

        results[ch_name] = ch_data

    output = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "channels": results,
        "total": sum(len(v) for v in results.values())
    }
    DATA.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ YouTube 수집 완료: {output['total']}개 영상")


if __name__ == "__main__": main()
