# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_cross_section_editor import CrossSectionEditorTaskPanel


class CmdEditCrossSection:
    def GetResources(self):
        return {
            "Pixmap": icon_path("view_cross_section.svg"),
            "MenuText": "Advanced Cross Section Editor",
            "ToolTip": "Open the advanced cross-section editing utility",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = CrossSectionEditorTaskPanel()
        Gui.Control.showDialog(panel)


if hasattr(Gui, "addCommand"):
    Gui.addCommand("CorridorRoad_EditCrossSection", CmdEditCrossSection())
