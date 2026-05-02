# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui
from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.misc.resources import icon_path


class CmdAIAssist:
    def GetResources(self):
        return {
            "Pixmap": icon_path("corridorroad_workbench.svg"),
            "MenuText": "AI Assist",
            "ToolTip": "Open the AI-assisted design stage for recommendations and alternative comparison",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        QtWidgets.QMessageBox.information(
            None,
            "AI Assist",
            "\n".join(
                [
                    "AI Assist stage",
                    "",
                    "This stage is part of the v1 workflow, but the dedicated AI assist UI is not implemented yet.",
                    "",
                    "Planned primary actions:",
                    "- Generate recommendations",
                    "- Compare alternatives",
                    "- Review AI explanations",
                    "- Accept an approved candidate",
                ]
            ),
        )


if hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_AIAssist", CmdAIAssist())
