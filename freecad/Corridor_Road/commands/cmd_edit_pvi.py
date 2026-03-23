# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_edit_pvi.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.ui.task_pvi_editor import PviEditorTaskPanel


class CmdEditPVI:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Edit PVI (FG)",
            "ToolTip": "Edit Vertical Alignment PVI and generate FG on stations (linear grade)",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = PviEditorTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_EditPVI", CmdEditPVI())
