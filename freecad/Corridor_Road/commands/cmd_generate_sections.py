# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_generate_sections.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_section_generator import SectionGeneratorTaskPanel


class CmdGenerateSections:
    def GetResources(self):
        return {
            "Pixmap": icon_path("sections.svg"),
            "MenuText": "Generate Sections",
            "ToolTip": "Generate section results from the current alignment, stations, and section rules",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = SectionGeneratorTaskPanel()
        Gui.Control.showDialog(panel)


if hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_GenerateSections", CmdGenerateSections())
