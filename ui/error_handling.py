"""Application log file and global handler for unexpected errors.

The packaged app runs without a console (``console=False`` in the PyInstaller
spec), so an uncaught exception would otherwise vanish. This module:

* writes a rotating log file (``garage_manager.log``) in the user data folder;
* installs ``sys.excepthook`` so any uncaught exception - including those raised
  inside Qt slots - is logged with its full traceback and shown to the user.

Qt is imported lazily so the logging part can be tested without a display.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE_NAME = "garage_manager.log"
_MAX_BYTES = 1_000_000
_BACKUP_COUNT = 5
_HANDLER_NAME = "garage_manager_file"

logger = logging.getLogger("garage_manager")

Translator = Callable[..., str]

_FALLBACK_TEXT = {
    "errors.unexpected_title": "Unexpected error",
    "errors.unexpected_body": (
        "Something went wrong and the last action may not have been saved.\n\n"
        "{error}\n\nDetails were written to:\n{log_path}"
    ),
}

_state: dict[str, object] = {"translator": None, "log_path": None, "showing": False}


def setup_logging(log_dir: Path, level: int = logging.INFO) -> Path:
    """Send log records to ``<log_dir>/garage_manager.log`` (rotating).

    Safe to call more than once: the file handler is only added once.
    Returns the log file path.
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / LOG_FILE_NAME

    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        if handler.get_name() == _HANDLER_NAME:
            root.removeHandler(handler)
            handler.close()

    handler = RotatingFileHandler(
        log_path, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    handler.set_name(_HANDLER_NAME)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    root.addHandler(handler)
    _state["log_path"] = log_path
    return log_path


def set_translator(translate: Translator | None) -> None:
    """Use the app's ``LanguageService.tr`` for error messages once it exists."""
    _state["translator"] = translate


def _tr(key: str, **kwargs: object) -> str:
    translate = _state["translator"]
    if callable(translate):
        text = translate(key, **kwargs)
        if text != key:
            return text
    return _FALLBACK_TEXT.get(key, key).format(**kwargs)


def handle_exception(exc_type, exc_value, exc_tb) -> None:
    """``sys.excepthook`` implementation: log, then tell the user."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
    _show_error_dialog(f"{exc_type.__name__}: {exc_value}")


def install_excepthook() -> None:
    sys.excepthook = handle_exception


def _show_error_dialog(error_text: str) -> None:
    # Avoid stacking dialogs if an error happens while one is being shown.
    if _state["showing"]:
        return
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except ImportError:
        return
    app = QApplication.instance()
    if app is None:
        return

    _state["showing"] = True
    try:
        QMessageBox.critical(
            app.activeWindow(),
            _tr("errors.unexpected_title"),
            _tr(
                "errors.unexpected_body",
                error=error_text,
                log_path=str(_state["log_path"] or LOG_FILE_NAME),
            ),
        )
    except Exception:  # never let the error handler itself crash the app
        logger.exception("Could not show the error dialog")
    finally:
        _state["showing"] = False
