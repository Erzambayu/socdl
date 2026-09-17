"""Tiny i18n layer. No external deps."""
from __future__ import annotations

from typing import Any

from .en import STRINGS as EN
from .id import STRINGS as ID

_TABLES: dict[str, dict[str, str]] = {"en": EN, "id": ID}
_CURRENT: str = "en"


def set_lang(lang: str) -> None:
    global _CURRENT
    lang = (lang or "en").lower()
    if lang not in _TABLES:
        lang = "en"
    _CURRENT = lang


def get_lang() -> str:
    return _CURRENT


def available_langs() -> list[str]:
    return list(_TABLES.keys())


def t(key: str, **kwargs: Any) -> str:
    """Translate `key` in current language, formatting with kwargs."""
    table = _TABLES.get(_CURRENT, EN)
    template = table.get(key) or EN.get(key) or key
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


__all__ = ["t", "set_lang", "get_lang", "available_langs"]
