"""Tests for Instagram session handling (socdl login / cookies import)."""
import json
import pickle
from unittest.mock import create_autospec

import instaloader
import pytest

from socdl.config import Config
from socdl.engines.instaloader_engine import (
    InstaloaderEngine,
    _parse_cookie_export,
    _username_from_cookies,
)

JSON_EXPORT = [
    {"domain": ".instagram.com", "name": "csrftoken", "value": "abc123"},
    {"domain": ".instagram.com", "name": "sessionid", "value": "69033%3AnXeL%3A3%3AAY"},
    {"domain": ".instagram.com", "name": "ds_user_id", "value": "69033657638"},
    {"domain": ".instagram.com", "name": "mid", "value": "ana2zQ"},
    {"domain": ".facebook.com", "name": "c_user", "value": "should-be-skipped"},
]

NETSCAPE = """# Netscape HTTP Cookie File
.instagram.com\tTRUE\t/\tTRUE\t1820724942\tcsrftoken\tfromtxt
.instagram.com\tTRUE\t/\tTRUE\t1820724942\tsessionid\tfromtxt-session
.instagram.com\tTRUE\t/\tTRUE\t1820724942\tds_user_id\t69033657638
.facebook.com\tTRUE\t/\tTRUE\t1820724942\tc_user\tskipme
"""


# --- cookie parsing ---------------------------------------------------------

def test_parse_json_export():
    pairs = dict(_parse_cookie_export(json.dumps(JSON_EXPORT)))
    assert pairs["csrftoken"] == "abc123"
    assert "sessionid" in pairs
    assert "c_user" not in pairs, "facebook cookies must be filtered out"


def test_parse_json_export_wrapped_in_object():
    pairs = dict(_parse_cookie_export(json.dumps({"cookies": JSON_EXPORT})))
    assert pairs["sessionid"].startswith("69033")


def test_parse_netscape_export():
    pairs = dict(_parse_cookie_export(NETSCAPE))
    assert pairs["csrftoken"] == "fromtxt"
    assert pairs["sessionid"] == "fromtxt-session"
    assert "c_user" not in pairs


def test_parse_garbage_returns_empty():
    assert _parse_cookie_export("") == []
    assert _parse_cookie_export("not json at all") == []
    assert _parse_cookie_export("[{bad json") == []


@pytest.mark.parametrize("domain", [
    "notinstagram.com", "instagram.com.example.org", "", None, 42,
])
def test_json_rejects_unrelated_or_missing_domains(domain):
    raw = json.dumps([{"domain": domain, "name": "sessionid", "value": "fake"}])
    assert _parse_cookie_export(raw) == []


@pytest.mark.parametrize("domain", ["instagram.com", ".instagram.com", "WWW.INSTAGRAM.COM"])
def test_both_formats_accept_instagram_domains(domain):
    raw = json.dumps([{"domain": domain, "name": "sessionid", "value": "fake"}])
    assert _parse_cookie_export(raw) == [("sessionid", "fake")]
    raw = f"{domain}\tTRUE\t/\tTRUE\t0\tsessionid\tfake"
    assert _parse_cookie_export(raw) == [("sessionid", "fake")]


@pytest.mark.parametrize("domain", ["notinstagram.com", "instagram.com.example.org"])
def test_netscape_rejects_lookalike_domains(domain):
    raw = f"#HttpOnly_{domain}\tTRUE\t/\tTRUE\t0\tsessionid\tfake"
    assert _parse_cookie_export(raw) == []


def test_import_netscape_httponly_cookie(tmp_path):
    source = tmp_path / "cookies.txt"
    source.write_text(
        "# Netscape HTTP Cookie File\n"
        "#HttpOnly_.instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\tfake-session\n"
        ".instagram.com\tTRUE\t/\tTRUE\t0\tcsrftoken\tfake-csrf\n",
        encoding="utf-8",
    )
    target = tmp_path / "out.session"
    ok, message = InstaloaderEngine.import_cookies(source, target)
    assert ok, message
    assert pickle.loads(target.read_bytes())["sessionid"] == "fake-session"


@pytest.mark.parametrize("username", ["example_user", ""])
def test_interactive_login_uses_real_api_signature(monkeypatch, tmp_path, username):
    loader = create_autospec(instaloader.Instaloader, instance=True)
    loader.save_session.return_value = {"sessionid": "fake-session"}
    monkeypatch.setattr(instaloader, "Instaloader", lambda **kwargs: loader)
    monkeypatch.setattr("builtins.input", lambda prompt: "example_user")
    target = tmp_path / "nested" / "out.session"
    ok, message = InstaloaderEngine.login(target, username)
    assert ok, message
    loader.interactive_login.assert_called_once_with("example_user")
    loader.login.assert_not_called()
    loader.close.assert_called_once()
    assert target.exists()


def test_failed_login_does_not_persist_or_expose_error(monkeypatch, tmp_path):
    loader = create_autospec(instaloader.Instaloader, instance=True)
    loader.interactive_login.side_effect = instaloader.exceptions.BadCredentialsException("fake-secret")
    monkeypatch.setattr(instaloader, "Instaloader", lambda **kwargs: loader)
    target = tmp_path / "out.session"
    ok, message = InstaloaderEngine.login(target, "example_user")
    assert not ok
    assert "fake-secret" not in message
    assert not target.exists()
    loader.save_session.assert_not_called()
    loader.close.assert_called_once()


def test_username_from_cookies_prefers_ds_user_id():
    assert _username_from_cookies([("ds_user_id", "42"), ("sessionid", "x")]) == "42"


def test_username_fallback():
    assert _username_from_cookies([("sessionid", "x")]) == "socdl"


# --- session path resolution ------------------------------------------------

def test_default_session_path_under_data_dir():
    p = InstaloaderEngine.default_session_path()
    assert p.name == "instagram.session"
    assert p.parent.exists(), "data dir should be created on demand"


def test_session_path_none_when_no_file(tmp_path):
    cfg = Config(instagram_login="")
    cfg_missing = Config(instagram_login=str(tmp_path / "nope.session"))
    # configured path that does not exist -> still returned (caller checks .exists)
    assert InstaloaderEngine.session_path_for(cfg_missing) == tmp_path / "nope.session"
    # empty config + no default file -> None (anonymous)
    default = InstaloaderEngine.default_session_path()
    if not default.exists():
        assert InstaloaderEngine.session_path_for(cfg) is None


def test_config_path_wins(tmp_path):
    cfg = Config(instagram_login=str(tmp_path / "custom.session"))
    assert InstaloaderEngine.session_path_for(cfg) == tmp_path / "custom.session"


# --- import_cookies ---------------------------------------------------------

def test_import_cookies_builds_pickle(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(json.dumps(JSON_EXPORT), encoding="utf-8")
    session_file = tmp_path / "out.session"

    ok_flag, msg = InstaloaderEngine.import_cookies(cookie_file, session_file)
    assert ok_flag, msg
    assert session_file.exists()
    data = pickle.loads(session_file.read_bytes())
    assert data["csrftoken"] == "abc123"
    assert data["sessionid"].startswith("69033")


def test_import_cookies_rejects_logged_out_export(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(
        json.dumps([{"domain": ".instagram.com", "name": "csrftoken", "value": "x"}]),
        encoding="utf-8",
    )
    ok_flag, msg = InstaloaderEngine.import_cookies(cookie_file, tmp_path / "o.session")
    assert not ok_flag
    assert "sessionid" in msg


def test_import_cookies_missing_file(tmp_path):
    ok_flag, msg = InstaloaderEngine.import_cookies(tmp_path / "nope.json", tmp_path / "o")
    assert not ok_flag
    assert "not found" in msg


def test_import_cookies_empty_file(tmp_path):
    f = tmp_path / "c.json"
    f.write_text("", encoding="utf-8")
    ok_flag, msg = InstaloaderEngine.import_cookies(f, tmp_path / "o.session")
    assert not ok_flag
    assert "no Instagram cookies" in msg


# --- apply_session ----------------------------------------------------------

def test_apply_session_loads_pickle(tmp_path):
    session_file = tmp_path / "s.session"
    session_file.write_bytes(
        pickle.dumps({"csrftoken": "tok", "sessionid": "sid", "ds_user_id": "42"})
    )
    cfg = Config(instagram_login=str(session_file))

    class FakeLoader:
        def __init__(self):
            self.loaded = None

        def load_session(self, username, data):
            self.loaded = (username, data)

    loader = FakeLoader()
    assert InstaloaderEngine.apply_session(loader, cfg) is True
    username, data = loader.loaded
    assert username == "42"
    assert data["csrftoken"] == "tok"


def test_apply_session_returns_false_when_absent(tmp_path):
    cfg = Config(instagram_login=str(tmp_path / "missing.session"))

    class FakeLoader:
        def load_session(self, username, data):
            raise AssertionError("should not be called")

    assert InstaloaderEngine.apply_session(FakeLoader(), cfg) is False


def test_apply_session_survives_corrupt_file(tmp_path):
    bad = tmp_path / "bad.session"
    bad.write_bytes(b"not a pickle")
    cfg = Config(instagram_login=str(bad))

    class FakeLoader:
        def load_session(self, username, data):
            raise AssertionError("should not be called")

    assert InstaloaderEngine.apply_session(FakeLoader(), cfg) is False


def test_error_messages_never_leak_cookie_values(tmp_path):
    """A rejected import must not echo the cookie values back to the user."""
    secret = "SUPER_SECRET_SESSION_VALUE"
    cookie_file = tmp_path / "cookies.json"
    # Missing 'sessionid' -> rejected, and the secret must not be in the message.
    cookie_file.write_text(
        json.dumps([{"domain": ".instagram.com", "name": "csrftoken", "value": secret}]),
        encoding="utf-8",
    )
    ok_flag, msg = InstaloaderEngine.import_cookies(cookie_file, tmp_path / "o.session")
    assert not ok_flag
    assert secret not in msg


def test_success_message_reports_count_not_values(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(json.dumps(JSON_EXPORT), encoding="utf-8")
    ok_flag, msg = InstaloaderEngine.import_cookies(cookie_file, tmp_path / "o.session")
    assert ok_flag
    for cookie in JSON_EXPORT:
        assert str(cookie["value"]) not in msg, "must not echo cookie values"
