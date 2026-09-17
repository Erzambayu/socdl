"""Platform & content-type detection from URLs."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Detected:
    platform: str            # instagram | tiktok | youtube | twitter | reddit | facebook | unknown
    kind: str = "media"      # post | reel | story | profile | video | photo | playlist | media
    target: Optional[str] = None
    label: str = ""

    @property
    def folder_name(self) -> str:
        return {
            "instagram": "Instagram",
            "tiktok":    "TikTok",
            "youtube":   "YouTube",
            "twitter":   "Twitter",
            "reddit":    "Reddit",
            "facebook":  "Facebook",
        }.get(self.platform, "Other")


PATTERNS = [
    ("instagram", "reel",       r"instagram\.com/(?:reel|reels)/([A-Za-z0-9_-]+)"),
    ("instagram", "reel",       r"instagram\.com/tv/([A-Za-z0-9_-]+)"),
    ("instagram", "story",      r"instagram\.com/stories/([A-Za-z0-9_.]+)/(\d+)"),
    ("instagram", "profile",    r"instagram\.com/stories/([A-Za-z0-9_.]+)/?$"),
    ("instagram", "post",       r"instagram\.com/(?:p)/([A-Za-z0-9_-]+)"),
    ("instagram", "profile",    r"instagram\.com/([A-Za-z0-9_.]+)/?$"),

    ("tiktok",    "photo",      r"tiktok\.com/@[^/]+/photo/(\d+)"),
    ("tiktok",    "video",      r"tiktok\.com/@[^/]+/video/(\d+)"),
    ("tiktok",    "video",      r"(?:vm|vt)\.tiktok\.com/([A-Za-z0-9]+)"),
    ("tiktok",    "profile",    r"tiktok\.com/@([A-Za-z0-9._]+)/?$"),

    ("youtube",   "playlist",   r"youtube\.com/playlist\?list=([A-Za-z0-9_-]+)"),
    ("youtube",   "video",      r"youtube\.com/shorts/([A-Za-z0-9_-]+)"),
    ("youtube",   "video",      r"youtube\.com/watch\?v=([A-Za-z0-9_-]+)"),
    ("youtube",   "video",      r"youtu\.be/([A-Za-z0-9_-]+)"),
    ("youtube",   "video",      r"youtube\.com/embed/([A-Za-z0-9_-]+)"),

    ("twitter",   "post",       r"(?:twitter|x)\.com/[^/]+/status/(\d+)"),
    ("twitter",   "profile",    r"(?:twitter|x)\.com/([A-Za-z0-9_]+)/?$"),

    ("reddit",    "post",       r"reddit\.com/r/[^/]+/comments/([A-Za-z0-9]+)"),
    ("reddit",    "post",       r"redd\.it/([A-Za-z0-9]+)"),

    ("facebook",  "video",      r"(?:facebook|fb)\.com/(?:watch|reel|video)/?\??v?=?(\d+)?"),
    ("facebook",  "post",       r"(?:facebook|fb)\.com/[^/]+/posts/([0-9A-Za-z]+)"),
]


LABELS = {
    ("instagram", "post"):    "Instagram post",
    ("instagram", "reel"):    "Instagram reel",
    ("instagram", "story"):   "Instagram story",
    ("instagram", "profile"): "Instagram profile",
    ("tiktok",    "video"):   "TikTok video",
    ("tiktok",    "photo"):   "TikTok photo",
    ("tiktok",    "profile"): "TikTok profile",
    ("youtube",   "video"):   "YouTube video",
    ("youtube",   "playlist"):"YouTube playlist",
    ("twitter",   "post"):    "Twitter/X post",
    ("twitter",   "profile"): "Twitter/X profile",
    ("reddit",    "post"):    "Reddit post",
    ("facebook",  "video"):   "Facebook video",
    ("facebook",  "post"):    "Facebook post",
}

RESERVED_IG = {"explore", "reels", "stories", "accounts", "p", "tv", "direct", "developer"}


def detect_platform(url: str) -> Detected:
    u = url.strip().split("#")[0]
    u_low = u.lower()

    for platform, kind, pat in PATTERNS:
        m = re.search(pat, u_low, re.IGNORECASE)
        if not m:
            continue
        target = m.group(1) if m.groups() else None

        if platform == "instagram" and kind == "profile" and target in RESERVED_IG:
            continue

        label = LABELS.get((platform, kind), f"{platform} {kind}")
        return Detected(platform=platform, kind=kind, target=target, label=label)

    if "instagram." in u_low or "instagr.am" in u_low:
        return Detected("instagram", "post", None, "Instagram")
    if "tiktok." in u_low:
        return Detected("tiktok", "video", None, "TikTok")
    if "youtube." in u_low or "youtu.be" in u_low:
        return Detected("youtube", "video", None, "YouTube")

    return Detected("unknown", "media", None, "Unknown")


__all__ = ["Detected", "detect_platform"]
