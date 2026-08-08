"""Core download logic: resolve playlist, download video + thumbnail."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import requests
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
from yt_dlp.utils import sanitize_filename


def _network_opts() -> dict[str, Any]:
    """TLS fingerprint spoofing + mobile/TV clients — no browser cookies."""
    return {
        # 1. Giả lập TLS Fingerprint của Chrome (yêu cầu curl-cffi)
        # Python API cần ImpersonateTarget, không phải str thuần
        "impersonate": ImpersonateTarget.from_str("chrome"),
        # 2. Ép API Mobile/TV để tránh bộ lọc Web Bot của YouTube
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "tv", "web"],
            }
        },
        # Ngôn ngữ client — ảnh hưởng title localize khi flat-extract
        "http_headers": {
            "Accept-Language": "ja-JP,ja;q=1.0",
        },
        # Tránh cache cũ gây lỗi
        "rm_cachedir": True,
    }


def _best_title(info: dict, fallback_id: str) -> str:
    """Prefer original (untranslated) title when yt-dlp provides it."""
    return info.get("original_title") or info.get("title") or fallback_id


def _item_basename(item_data: dict) -> str:
    title = sanitize_filename(_best_title(item_data, item_data["id"]), restricted=False)
    return f"{item_data['position']:02d} {title}"


def resolve_playlist(
    url: str,
    from_index: int | None = None,
    to_index: int | None = None,
) -> list[dict]:
    """Stage 1: extract flat metadata and filter by from/to (1-based). Fast list load."""
    ydl_opts: dict[str, Any] = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        **_network_opts(),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        return []

    entries = info.get("entries")
    items: list[dict] = []

    if entries is None:
        vid = info["id"]
        items.append(
            {
                "id": vid,
                "url": info.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}",
                "title": _best_title(info, vid),
                "position": 1,
            }
        )
    else:
        pos = 0
        for entry in entries:
            if not entry:
                continue
            pos += 1
            vid = entry.get("id")
            if not vid:
                continue
            items.append(
                {
                    "id": vid,
                    "url": entry.get("url")
                    or entry.get("webpage_url")
                    or f"https://www.youtube.com/watch?v={vid}",
                    "title": _best_title(entry, vid),
                    "position": pos,
                }
            )

    if from_index is not None:
        items = [x for x in items if x["position"] >= from_index]
    if to_index is not None:
        items = [x for x in items if x["position"] <= to_index]
    return items


def fetch_full_metadata(url: str) -> dict:
    """
    Lazy full extract for one video URL (extract_flat=False).
    Prefer original_title over localized title. Call only at download time.
    """
    ydl_opts: dict[str, Any] = {
        "extract_flat": False,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        **_network_opts(),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ValueError(f"Không lấy được metadata: {url}")

    vid = info.get("id") or ""
    return {
        "id": vid,
        "url": info.get("webpage_url") or url,
        "title": _best_title(info, vid or url),
        "original_title": info.get("original_title"),
    }


def download_video(
    item_data: dict,
    resolution: int,
    save_dir: str,
    progress_hook: Callable | None = None,
) -> str:
    """Stage 2.1: download one video via yt_dlp."""
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    basename = _item_basename(item_data)
    outtmpl = str(Path(save_dir) / f"{basename}.%(ext)s")
    height = int(resolution)

    ydl_opts: dict[str, Any] = {
        "format": (
            f"bestvideo[ext=mp4][height<={height}]+bestaudio[ext=m4a]/"
            f"best[ext=mp4][height<={height}]/best"
        ),
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "nooverwrites": True,
        "retries": 3,
        "fragment_retries": 3,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        **_network_opts(),
    }
    if progress_hook is not None:
        ydl_opts["progress_hooks"] = [progress_hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([item_data["url"]])
    return basename


def download_thumbnail(video_id: str, save_dir: str, basename: str) -> str | None:
    """Stage 2.2: fetch thumbnail from YouTube CDN via requests."""
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    dest = Path(save_dir) / f"{basename}.jpg"
    if dest.exists():
        return str(dest)

    urls = [
        f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            # YouTube sometimes returns a tiny placeholder for missing maxres
            if len(resp.content) < 2000 and "maxresdefault" in url:
                continue
            dest.write_bytes(resp.content)
            return str(dest)
        except requests.RequestException:
            continue
    return None


def download_item(
    item_data: dict,
    resolution: int,
    save_dir: str,
    progress_hook: Callable | None = None,
    on_stage: Callable[[str], None] | None = None,
) -> dict:
    """
    Stage 2: enrich title via full extract, then download video + thumbnail.
    on_stage(status_text) is optional for UI status updates.
    Returns {"ok": bool, "basename": str, "thumb_error": str | None, "error": str | None}
    """
    def stage(msg: str) -> None:
        if on_stage:
            on_stage(msg)

    result = {"ok": False, "basename": "", "thumb_error": None, "error": None}
    try:
        # Lazy: full metadata only when downloading — keeps playlist load fast
        stage("Đang lấy tiêu đề gốc")
        meta = fetch_full_metadata(item_data["url"])
        enriched = {
            **item_data,
            "title": meta["title"],
            "original_title": meta.get("original_title"),
        }
        if meta.get("id"):
            enriched["id"] = meta["id"]
        if meta.get("url"):
            enriched["url"] = meta["url"]

        stage("Đang tải Video")
        basename = download_video(enriched, resolution, save_dir, progress_hook=progress_hook)
        result["basename"] = basename

        stage("Đang tải Thumb")
        thumb_path = download_thumbnail(enriched["id"], save_dir, basename)
        if thumb_path is None:
            result["thumb_error"] = "Không tải được thumbnail"

        stage("✅ Xong")
        result["ok"] = True
    except Exception as exc:  # noqa: BLE001 — surface any yt_dlp/network failure to UI
        result["error"] = str(exc)
        stage(f"❌ Lỗi: {exc}")
    return result
