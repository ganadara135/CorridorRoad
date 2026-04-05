# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.ui.task_cross_section_viewer import CrossSectionViewerTaskPanel


class CmdViewCrossSection:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Cross Section Viewer",
            "ToolTip": "Open a 2D viewer for SectionSet cross-sections",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = CrossSectionViewerTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_ViewCrossSection", CmdViewCrossSection())
