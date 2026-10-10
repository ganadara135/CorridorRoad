# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path


class CmdProjectSetup:
    def GetResources(self):
        return {
            "Pixmap": icon_path("project_setup.svg"),
            "MenuText": "New/Project Setup",
            "ToolTip": "Create or configure a CorridorRoad project, CRS, origin, rotation, and datum",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        # Stable command id; the panel and its rules are v1 (v1/commands/cmd_project_setup.py).
        from freecad.Corridor_Road.v1.commands.cmd_project_setup import run_v1_project_setup_command

        run_v1_project_setup_command(App.ActiveDocument)


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_ProjectSetup", CmdProjectSetup())
