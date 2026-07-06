"""Run YouTube transcript ingestion from a residential IP and push results
to the deployed backend.

Why this exists: YouTube blanket-blocks requests from cloud-provider IPs
(Render, AWS, etc.), so the ingestion running *on* the server always comes up
empty. This script does the same scraping (yt-dlp + youtube-transcript-api)
but from wherever you run it — your own PC, on your ISP's residential IP,
which YouTube doesn't block — and POSTs the results to
POST /api/transcripts/ingest-external.

Usage (from backend/, with the venv active):
    CLARA_BACKEND_URL=https://clara-l955.onrender.com \
    CLARA_INGEST_SECRET=<same value as INGEST_SECRET on Render> \
    python scripts/fetch_transcripts_local.py

Run it manually whenever you want fresh transcripts, or schedule it locally
(cron / Windows Task Scheduler) — there's no server-side dependency beyond
the one endpoint call.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime
from urllib.parse import parse_qs, urlparse

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ingestion import youtube  # noqa: E402

_VIDEOS_PER_CHANNEL = 5


def _video_id_from_url(url: str) -> str | None:
    qs = parse_qs(urlparse(url).query)
    return (qs.get("v") or [None])[0]


def _parse_upload_date(raw: str | None) -> str:
    if not raw:
        return date.today().isoformat()
    try:
        return datetime.strptime(raw, "%Y%m%d").date().isoformat()
    except ValueError:
        return date.today().isoformat()


def main() -> None:
    backend_url = os.environ.get("CLARA_BACKEND_URL")
    secret = os.environ.get("CLARA_INGEST_SECRET")
    if not backend_url or not secret:
        print(
            "Set CLARA_BACKEND_URL and CLARA_INGEST_SECRET env vars first.",
            file=sys.stderr,
        )
        sys.exit(1)

    channels = httpx.get(f"{backend_url}/api/youtube/channels", timeout=20).json()
    channels = [c for c in channels if c["active"]]
    if not channels:
        print("No hay canales activos en el backend.")
        return

    existing = httpx.get(f"{backend_url}/api/transcripts", timeout=20).json()
    seen_ids = {
        vid for t in existing if (vid := _video_id_from_url(t["url"])) is not None
    }

    items = []
    for channel in channels:
        name = channel["display_name"] or channel["handle"]
        print(f"Canal: {name}")
        try:
            videos = youtube.list_latest_videos(
                channel["channel_id"], limit=_VIDEOS_PER_CHANNEL
            )
        except youtube.ChannelFetchError as exc:
            print(f"  fallo al listar videos: {exc}")
            continue

        for video in videos:
            video_id = video["video_id"]
            if video_id in seen_ids:
                continue
            try:
                transcript = youtube.fetch_transcript(video_id)
            except youtube.ChannelFetchError as exc:
                print(f"  {video_id}: {exc}")
                continue
            if not transcript:
                print(f"  {video_id}: sin transcript (captions deshabilitados)")
                continue

            items.append({
                "video_id": video_id,
                "channel": name,
                "title": video["title"],
                "transcript": transcript,
                "published_at": _parse_upload_date(video.get("upload_date")),
            })
            print(f"  {video_id}: transcript OK ({len(transcript)} chars)")

    if not items:
        print("Nada nuevo para subir.")
        return

    resp = httpx.post(
        f"{backend_url}/api/transcripts/ingest-external",
        json=items,
        headers={"X-Ingest-Secret": secret},
        timeout=60,
    )
    resp.raise_for_status()
    print(resp.json()["message"])


if __name__ == "__main__":
    main()
