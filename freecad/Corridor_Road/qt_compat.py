"""Qt compatibility imports for FreeCAD workbench code.

Order of preference:
1) FreeCAD's compatibility shim (`PySide`)
2) Native Qt6 (`PySide6`)
3) Native Qt5 (`PySide2`)
"""

try:
    import PySide  # type: ignore

    QtCore = PySide.QtCore
    QtGui = PySide.QtGui
    # In some compatibility layers QtWidgets is merged into QtGui.
    QtWidgets = getattr(PySide, "QtWidgets", QtGui)
except Exception:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore
    except Exception:
        from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore

__all__ = ["QtCore", "QtGui", "QtWidgets"]
