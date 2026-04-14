# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_alignment_editor import AlignmentEditorTaskPanel


class CmdEditAlignment:
    def GetResources(self):
        return {
            "Pixmap": icon_path("alignment.svg"),
            "MenuText": "Alignment",
            "ToolTip": "Edit alignment geometry and criteria",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = AlignmentEditorTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_EditAlignment", CmdEditAlignment())
