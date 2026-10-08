import pytest

from socdl.platforms import detect_platform


@pytest.mark.parametrize("url, platform, kind", [
    ("https://playmogo.com/d/yj2iqz70pnsx", "doodstream", "video"),
    ("https://playmogo.com/e/yj2iqz70pnsx", "doodstream", "video"),
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

    ("https://www.facebook.com/reel/1044635761456156",        "facebook", "reel"),
    ("https://www.facebook.com/watch/?v=1044635761456156",    "facebook", "video"),
    ("https://www.facebook.com/watch?v=1044635761456156",     "facebook", "video"),
    ("https://www.facebook.com/user/videos/1234567890/",      "facebook", "video"),
    ("https://www.facebook.com/user/video/1234567890",        "facebook", "video"),
    ("https://www.facebook.com/share/r/ABCdef123/",           "facebook", "video"),
    ("https://www.facebook.com/user/posts/123456789",         "facebook", "post"),
    ("https://www.facebook.com/groups/12345/posts/67890",     "facebook", "post"),
    ("https://www.facebook.com/photo?fbid=123&set=a.456",     "facebook", "photo"),
    ("https://www.facebook.com/photo.php?fbid=123456",        "facebook", "photo"),
    ("https://www.facebook.com/permalink.php?story_fbid=99&id=1", "facebook", "post"),
    ("https://fb.watch/abcdef123/",                           "facebook", "video"),
    ("https://web.facebook.com/reel/1044635761456156",        "facebook", "reel"),

    ("https://example.com/whatever", "unknown", "media"),
])
def test_detection(url, platform, kind):
    det = detect_platform(url)
    assert det.platform == platform, det
    assert det.kind == kind, det


@pytest.mark.parametrize("url, target", [
    ("https://www.facebook.com/reel/1044635761456156", "1044635761456156"),
    ("https://www.facebook.com/user/videos/1234567890/", "1234567890"),
    ("https://www.facebook.com/photo?fbid=123&set=a.456", "123"),
    ("https://fb.watch/abcdef123/", "abcdef123"),
])
def test_facebook_target_extracted(url, target):
    assert detect_platform(url).target == target


def test_facebook_engine_chain_is_ytdlp_only():
    from socdl.router import engine_chain

    det = detect_platform("https://www.facebook.com/reel/1044635761456156")
    assert engine_chain(det) == ["yt-dlp"]


def test_doodstream_engine_chain():
    from socdl.router import engine_chain

    det = detect_platform("https://playmogo.com/d/yj2iqz70pnsx")
    assert det.target == "yj2iqz70pnsx"
    assert det.folder_name == "DoodStream"
    assert engine_chain(det) == ["doodstream"]


@pytest.mark.parametrize("url", [
    "https://playmogo.com.evil.test/d/yj2iqz70pnsx",
    "https://evil.test/?next=playmogo.com/d/yj2iqz70pnsx",
])
def test_doodstream_lookalikes_not_detected(url):
    assert detect_platform(url).platform != "doodstream"


def test_reserved_ig_paths_are_not_profiles():
    for path in ["explore", "reels", "stories", "accounts", "direct"]:
        det = detect_platform(f"https://www.instagram.com/{path}/")
        assert not (det.platform == "instagram" and det.kind == "profile"), path


@pytest.mark.parametrize("url, target", [
    ("https://www.instagram.com/p/DdrPU-QEwTm", "DdrPU-QEwTm"),
    ("https://www.instagram.com/p/Ddq5pJPE0El", "Ddq5pJPE0El"),
    ("https://www.instagram.com/reel/DdrPU-QEwTm/", "DdrPU-QEwTm"),
    ("https://www.instagram.com/tv/DdrPU-QEwTm/", "DdrPU-QEwTm"),
])
def test_instagram_shortcode_case_is_preserved(url, target):
    """Instagram shortcodes are case-sensitive; detection must not lowercase them.

    Regression: matching patterns against a lowercased URL made every post and
    reel 404, because instaloader looked up e.g. "ddrpu-qewtm" instead of
    "DdrPU-QEwTm".
    """
    assert detect_platform(url).target == target


def test_reserved_ig_path_check_is_case_insensitive():
    det = detect_platform("https://www.instagram.com/Explore/")
    assert not (det.platform == "instagram" and det.kind == "profile"), det
