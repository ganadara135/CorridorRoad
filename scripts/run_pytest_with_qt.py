"""Run pytest with a deterministic Qt application for local FreeCAD validation."""

from __future__ import annotations

import sys

import pytest


def _configure_qt_test_runtime():
    """Create QApplication and replace modal message boxes for unattended tests."""

    try:
        from freecad.Corridor_Road.qt_compat import QtWidgets
    except Exception:
        return None

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    message_box = QtWidgets.QMessageBox
    ok_value = getattr(message_box, "Ok", 0)
    yes_value = getattr(message_box, "Yes", ok_value)
    message_box.information = staticmethod(lambda *args, **kwargs: ok_value)
    message_box.warning = staticmethod(lambda *args, **kwargs: ok_value)
    message_box.critical = staticmethod(lambda *args, **kwargs: ok_value)
    message_box.question = staticmethod(lambda *args, **kwargs: yes_value)
    return app


def main(argv: list[str] | None = None) -> int:
    app = _configure_qt_test_runtime()
    exit_code = int(pytest.main(list(argv if argv is not None else sys.argv[1:])))
    if app is not None:
        try:
            app.processEvents()
        except Exception:
            pass
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
