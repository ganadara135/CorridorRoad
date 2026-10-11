# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_generate_cut_fill_calc.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path


def run_earthwork_review_command(*, app_module=App, run_v1_viewer=None):
    """Open the v1 Earthwork review, reporting a failure instead of opening a v0 panel.

    The v0 panel this used to fall back to belongs to the retiring legacy objects
    (docsV1/V1_LEGACY_PROXY_MIGRATION_DESIGN.md, section 16).
    """

    if run_v1_viewer is None:
        from freecad.Corridor_Road.v1.commands.cmd_earthwork_balance import (
            run_v1_earthwork_balance_command,
        )

        run_v1_viewer = run_v1_earthwork_balance_command

    try:
        run_v1_viewer()
        return "v1"
    except Exception as exc:
        app_module.Console.PrintError(f"Earthwork review was not opened: {exc}" + "\n")
        return "error"


class CmdGenerateCutFillCalc:
    def GetResources(self):
        return {
            "Pixmap": icon_path("cut_fill.svg"),
            "MenuText": "Review Earthwork",
            "ToolTip": "Review cut/fill and earthwork results for the current document",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        run_earthwork_review_command()


if hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_GenerateCutFillCalc", CmdGenerateCutFillCalc())
