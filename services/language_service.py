"""Loads UI string mappings from JSON locale files and notifies widgets on change."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, QLocale, Signal


class LanguageService(QObject):
    """Flat key → message maps per locale, loaded from ``locale/<code>.json``."""

    language_changed = Signal(str)

    def __init__(self, locale_code: str = "en", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._root = Path(__file__).resolve().parent.parent / "locale"
        self._by_locale: dict[str, dict[str, str]] = {}
        self._load_file("en")
        self._load_file("es")
        self._locale_code = locale_code if locale_code in self._by_locale else "en"
        self._strings = dict(self._by_locale.get(self._locale_code, {}))

    def _load_file(self, code: str) -> None:
        path = self._root / f"{code}.json"
        if not path.is_file():
            self._by_locale[code] = {}
            return
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            self._by_locale[code] = {}
            return
        flat: dict[str, str] = {}
        for k, v in data.items():
            if isinstance(k, str) and isinstance(v, str):
                flat[k] = v
        self._by_locale[code] = flat

    def locale_code(self) -> str:
        return self._locale_code

    def qlocale(self) -> QLocale:
        if self._locale_code == "es":
            return QLocale(QLocale.Language.Spanish, QLocale.Country.Argentina)
        return QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)

    def tr(self, key: str, **kwargs: object) -> str:
        text = self._strings.get(key)
        if text is None:
            text = self._by_locale.get("en", {}).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        return text

    def set_locale(self, code: str) -> None:
        if code not in self._by_locale or not self._by_locale[code]:
            code = "en"
        if code == self._locale_code:
            return
        self._locale_code = code
        self._strings = dict(self._by_locale.get(code, {}))
        self.language_changed.emit(code)
