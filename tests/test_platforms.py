import pytest

from socdl.platforms import detect_platform


@pytest.mark.parametrize("url, platform, kind", [
    ("https://www.instagram.com/p/DbHFIQxE5LC/?img_index=1", "instagram", "post"),
    ("https://www.instagram.com/reel/ABC123/",               "instagram", "reel"),
    ("https://www.instagram.com/reels/ABC123/",              "instagram", "reel"),
    ("https://www.instagram.com/tv/ABC123/",                 "instagram", "reel"),
    ("https://www.instagram.com/username/",                  "instagram", "profile"),
    ("https://www.instagram.com/stories/username/",          "instagram", "profile"),
    ("https://www.instagram.com/stories/username/1234567890","instagram", "story"),

    ("https://www.tiktok.com/@user/video/1234567890",        "tiktok", "video"),
    ("https://www.tiktok.com/@user/photo/1234567890",        "tiktok", "photo"),
    ("https://vt.tiktok.com/ZSFyj9U8V/",                     "tiktok", "video"),
    ("https://vm.tiktok.com/ZSFyj9U8V/",                     "tiktok", "video"),
    ("https://www.tiktok.com/@user",                         "tiktok", "profile"),

    ("https://youtu.be/dQw4w9WgXcQ",                         "youtube", "video"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ",          "youtube", "video"),
    ("https://www.youtube.com/shorts/aqz-KE-bpKQ",           "youtube", "video"),
    ("https://www.youtube.com/playlist?list=PLxxxxxx",       "youtube", "playlist"),

    ("https://twitter.com/user/status/1234567890",           "twitter", "post"),
    ("https://x.com/user/status/1234567890",                 "twitter", "post"),
    ("https://x.com/user",                                    "twitter", "profile"),

    ("https://www.reddit.com/r/aww/comments/abc123/cute_cat/", "reddit", "post"),

    ("https://example.com/whatever", "unknown", "media"),
])
def test_detection(url, platform, kind):
    det = detect_platform(url)
    assert det.platform == platform, det
    assert det.kind == kind, det


def test_reserved_ig_paths_are_not_profiles():
    for path in ["explore", "reels", "stories", "accounts", "direct"]:
        det = detect_platform(f"https://www.instagram.com/{path}/")
        assert not (det.platform == "instagram" and det.kind == "profile"), path
