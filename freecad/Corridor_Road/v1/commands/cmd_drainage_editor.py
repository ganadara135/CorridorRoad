"""Drainage editor entry command for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtWidgets


class CmdV1DrainageEditor:
    def GetResources(self):
        return {
            "Pixmap": icon_path("drainage.svg"),
            "MenuText": "Drainage",
            "ToolTip": "Create and edit v1 drainage design intent",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        QtWidgets.QMessageBox.information(
            None,
            "Drainage",
            "\n".join(
                [
                    "Drainage Editor",
                    "",
                    "현재 작업중입니다.",
                    "",
                    "예정 작업:",
                    "- Drainage 요소 생성/편집",
                    "- Region 과 Drainage 요소 연결",
                    "- Ditch, flowline, culvert, inlet, outlet, discharge 검토",
                    "- Drainage diagnostics 및 output row 생성",
                ]
            ),
        )


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditDrainage", CmdV1DrainageEditor())
