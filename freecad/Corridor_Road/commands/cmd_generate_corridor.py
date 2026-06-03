# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_generate_corridor.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.corridor_compat import PREFERRED_COMMAND_ID
from freecad.Corridor_Road.misc.resources import icon_path


class CmdGenerateCorridor:
    def GetResources(self):
        return {
            "Pixmap": icon_path("corridor.svg"),
            "MenuText": "Build Parametric",
            "ToolTip": "Build parametric corridor results from the current section set",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
                run_v1_build_corridor_command,
            )

            run_v1_build_corridor_command()
        except Exception as exc:
            try:
                App.Console.PrintError(f"Build Parametric panel was not opened: {exc}\n")
            except Exception:
                pass


_CMD = CmdGenerateCorridor()

if hasattr(Gui, "addCommand"):
    Gui.addCommand(PREFERRED_COMMAND_ID, _CMD)
