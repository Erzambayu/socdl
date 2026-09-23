"""Tests for the release changelog extractor."""
import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "changelog_for_version.py"


def _load():
    spec = importlib.util.spec_from_file_location("changelog_for_version", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


SAMPLE = """# Changelog

Intro line.

## [0.2.0] — 2026-02-01

### Added
- shiny new thing

## [0.1.5] — 2026-01-01

### Fixed
- some bug

## [0.1.0]

- first
"""


@pytest.fixture(scope="module")
def mod():
    return _load()


def test_extract_middle_section(mod):
    body = mod.extract(SAMPLE, "0.2.0")
    assert "shiny new thing" in body
    assert "some bug" not in body


def test_extract_last_section(mod):
    body = mod.extract(SAMPLE, "0.1.5")
    assert "some bug" in body
    assert "first" not in body


def test_extract_strips_v_prefix(mod):
    assert mod.extract(SAMPLE, "v0.1.5") == mod.extract(SAMPLE, "0.1.5")


def test_extract_missing_returns_none(mod):
    assert mod.extract(SAMPLE, "9.9.9") is None


def test_main_prints_section(tmp_path, capsys, mod):
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text(SAMPLE, encoding="utf-8")
    code = mod.main(["0.1.5", "--file", str(cl)])
    out = capsys.readouterr().out
    assert code == 0
    assert "v0.1.5" in out
    assert "some bug" in out


def test_main_missing_version_exits_1(tmp_path, capsys, mod):
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text(SAMPLE, encoding="utf-8")
    code = mod.main(["9.9.9", "--file", str(cl)])
    assert code == 1
    assert "no changelog section" in capsys.readouterr().err
