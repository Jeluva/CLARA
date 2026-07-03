"""YouTube channel resolution and transcript scraping.

No API key required: channel listing goes through `yt-dlp` (flat extraction of
the channel's /videos tab), and transcripts go through `youtube-transcript-api`
(direct call to YouTube's caption endpoint). Both run locally, no Google Cloud
key needed.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("clara.youtube")


class ChannelNotFoundError(Exception):
    """The given URL/handle does not resolve to a YouTube channel."""


def _channel_videos_url(url_or_handle: str) -> str:
    text = url_or_handle.strip()
    if text.startswith("http://") or text.startswith("https://"):
        url = text.rstrip("/")
        return url if url.endswith("/videos") else f"{url}/videos"
    handle = text if text.startswith("@") else f"@{text}"
    return f"https://www.youtube.com/{handle}/videos"


def resolve_channel(url_or_handle: str) -> dict:
    """Resolve a channel URL/@handle to its canonical channel_id + name."""
    import yt_dlp

    opts = {"extract_flat": True, "playlist_items": "1", "quiet": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(_channel_videos_url(url_or_handle), download=False)
    except Exception as exc:
        raise ChannelNotFoundError(f"No se pudo resolver el canal: {exc}") from exc

    channel_id = info.get("channel_id")
    if not channel_id:
        raise ChannelNotFoundError(f"'{url_or_handle}' no parece ser un canal de YouTube válido")

    return {
        "channel_id": channel_id,
        "handle": info.get("uploader_id") or info.get("channel") or url_or_handle,
        "display_name": info.get("channel") or info.get("uploader") or url_or_handle,
    }


def list_latest_videos(channel_id: str, limit: int = 5) -> list[dict]:
    """Latest `limit` uploads for a channel, with title + upload date."""
    import yt_dlp

    channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
    flat_opts = {
        "extract_flat": True,
        "playlist_items": f"1-{limit}",
        "quiet": True,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(flat_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
    except Exception as exc:
        logger.warning("failed to list videos for channel %s: %s", channel_id, exc)
        return []

    entries = info.get("entries") or []
    videos: list[dict] = []
    meta_opts = {"quiet": True, "skip_download": True}
    with yt_dlp.YoutubeDL(meta_opts) as ydl:
        for entry in entries[:limit]:
            video_id = entry.get("id")
            if not video_id:
                continue
            upload_date = None
            try:
                meta = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}",
                    download=False,
                    process=False,
                )
                upload_date = meta.get("upload_date")
            except Exception as exc:
                logger.debug("failed to fetch upload date for %s: %s", video_id, exc)
            videos.append({
                "video_id": video_id,
                "title": entry.get("title") or "",
                "upload_date": upload_date,  # YYYYMMDD or None
            })
    return videos


_TRANSCRIPT_MAX_CHARS = 6000


def fetch_transcript(video_id: str) -> str | None:
    """Full transcript text for a video, preferring Spanish then English.

    Returns None if no transcript is available (disabled captions, etc.).
    """
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
    )

    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(["es", "es-419", "en"])
        except NoTranscriptFound:
            transcript = next(iter(transcript_list))
        fetched = transcript.fetch()
        text = " ".join(s.text for s in fetched.snippets).strip()
        return text[:_TRANSCRIPT_MAX_CHARS] if text else None
    except (TranscriptsDisabled, VideoUnavailable, NoTranscriptFound):
        return None
    except Exception as exc:
        logger.warning("transcript fetch failed for %s: %s", video_id, exc)
        return None
