"""The QApplication shared by the tests that build Qt widgets."""

from freecad.Corridor_Road.qt_compat import QtWidgets

_QAPP = None


def ensure_qapp():
    """Return the running QApplication, creating one if needed.

    Qt aborts the process if a widget is built with no QApplication, so a test file that
    builds panels calls this to also run alone. The module-level reference keeps the
    application from being garbage collected while widgets still exist.
    """
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP
