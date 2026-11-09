"""Log file and global exception hook (ui/error_handling.py).

These tests do not need a display: without a running QApplication the hook only
logs, which is the part that matters for diagnosing problems.
"""

from __future__ import annotations

import logging
import sys

import pytest

from ui import error_handling


@pytest.fixture(autouse=True)
def _restore_logging_and_hook():
    saved_hook = sys.excepthook
    yield
    sys.excepthook = saved_hook
    root = logging.getLogger()
    for handler in list(root.handlers):
        if handler.get_name() == error_handling._HANDLER_NAME:
            root.removeHandler(handler)
            handler.close()
    error_handling.set_translator(None)


def _raise_and_capture(exc: BaseException):
    try:
        raise exc
    except BaseException:
        return sys.exc_info()


def test_setup_logging_writes_to_file(tmp_path):
    log_path = error_handling.setup_logging(tmp_path / "logs")
    logging.getLogger("garage_manager.test").info("hola log")
    assert log_path == tmp_path / "logs" / "garage_manager.log"
    assert "hola log" in log_path.read_text(encoding="utf-8")


def test_setup_logging_twice_does_not_duplicate_lines(tmp_path):
    error_handling.setup_logging(tmp_path)
    log_path = error_handling.setup_logging(tmp_path)
    logging.getLogger("garage_manager.test").info("una sola vez")
    assert log_path.read_text(encoding="utf-8").count("una sola vez") == 1


def test_uncaught_exception_is_logged_with_traceback(tmp_path):
    log_path = error_handling.setup_logging(tmp_path)
    error_handling.install_excepthook()
    assert sys.excepthook is error_handling.handle_exception

    sys.excepthook(*_raise_and_capture(ZeroDivisionError("division por cero")))

    text = log_path.read_text(encoding="utf-8")
    assert "Uncaught exception" in text
    assert "ZeroDivisionError: division por cero" in text
    assert "Traceback" in text


def test_keyboard_interrupt_goes_to_default_hook(tmp_path, monkeypatch):
    log_path = error_handling.setup_logging(tmp_path)
    called = []
    monkeypatch.setattr(sys, "__excepthook__", lambda *a: called.append(a[0]))

    error_handling.handle_exception(*_raise_and_capture(KeyboardInterrupt()))

    assert called == [KeyboardInterrupt]
    assert "Uncaught exception" not in log_path.read_text(encoding="utf-8")


def test_messages_use_translator_with_fallback():
    assert error_handling._tr("errors.unexpected_title") == "Unexpected error"

    error_handling.set_translator(
        lambda key, **kw: "Error inesperado" if key == "errors.unexpected_title" else key
    )
    assert error_handling._tr("errors.unexpected_title") == "Error inesperado"
    body = error_handling._tr("errors.unexpected_body", error="X", log_path="L")
    assert "X" in body and "L" in body  # missing translation -> English fallback
