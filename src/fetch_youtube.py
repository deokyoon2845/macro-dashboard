"""
src/fetch_youtube.py
유튜브 채널 최신 영상 자막 수집 → data/youtube_feed.json
"""
import json
from pathlib import Path
from datetime import datetime, timedelta

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    import requests
except ImportError:
    print("pip install youtube-transcript-api requests")
    raise SystemExit(0)

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

def get_recent_video_ids(channel_id, max_results=3):
    """RSS 피드로 최신 영상 ID 가져오기 (API 키 불필요)"""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        r = requests.get(url, timeout=10)
        ids = []
        for line in r.text.split("\n"):
            if "yt:videoId" in line:
                vid = line.strip().replace("<yt:videoId>","").replace("</yt:videoId>","")
                ids.append(vid)
                if len(ids) >= max_results: break
        return ids
    except Exception as e:
        print(f"  RSS 오류: {e}")
        return []

def get_transcript(video_id, lang=["ko","en"]):
    """자막 가져오기"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=lang)
        text = " ".join(t["text"] for t in transcript)
        return text[:2000]  # 앞 2000자만
    except Exception as e:
        print(f"  자막 오류 {video_id}: {e}")
        return ""

def main():
    channels_file = DATA / "youtube_channels.json"
    if not channels_file.exists():
        print("⚠ data/youtube_channels.json 없음 — 파일을 만들어주세요")
        return

    channels = json.loads(channels_file.read_text(encoding="utf-8"))
    result = {"updated": datetime.now().strftime("%Y-%m-%d %H:%M"), "channels": {}}

    for ch in channels:
        name = ch["name"]
        cid  = ch["channel_id"]
        print(f"수집 중: {name}")
        videos = []
        for vid_id in get_recent_video_ids(cid, max_results=2):
            transcript = get_transcript(vid_id)
            if not transcript: continue
            videos.append({
                "video_id":  vid_id,
                "url":       f"https://youtube.com/watch?v={vid_id}",
                "transcript": transcript
            })
            print(f"  ✅ {vid_id} ({len(transcript)}자)")
        result["channels"][name] = videos

    out = DATA / "youtube_feed.json"
    DATA.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 저장 완료: {out}")

if __name__ == "__main__":
    main()
