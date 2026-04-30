# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui
from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.misc.resources import icon_path


class CmdOutputsExchange:
    def GetResources(self):
        return {
            "Pixmap": icon_path("project_setup.svg"),
            "MenuText": "Outputs & Exchange",
            "ToolTip": "Open the outputs and exchange stage for deliverables and export actions",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        QtWidgets.QMessageBox.information(
            None,
            "Outputs & Exchange",
            "\n".join(
                [
                    "Outputs & Exchange stage",
                    "",
                    "This stage is part of the v1 workflow, but the dedicated output-review and export hub is not implemented yet.",
                    "",
                    "Planned primary actions:",
                    "- Review Outputs",
                    "- Structure Output Package",
                    "- Export DXF",
                    "- Export LandXML",
                    "- Export IFC",
                ]
            ),
        )


if hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_OutputsExchange", CmdOutputsExchange())
