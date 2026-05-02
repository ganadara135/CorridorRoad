# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_generate_cut_fill_calc.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_cut_fill_calc import CutFillCalcTaskPanel


def run_earthwork_review_command(
    *,
    app_module=App,
    gui_module=Gui,
    run_v1_viewer=None,
    open_existing_v0_panel=None,
):
    """Run the preferred earthwork review path with a safe v0 fallback."""

    if run_v1_viewer is None:
        from freecad.Corridor_Road.v1.commands.cmd_earthwork_balance import (
            run_v1_earthwork_balance_command,
        )

        run_v1_viewer = run_v1_earthwork_balance_command

    if open_existing_v0_panel is None:
        def _open_existing_v0_panel():
            panel = CutFillCalcTaskPanel()
            gui_module.Control.showDialog(panel)
            return panel

        open_existing_v0_panel = _open_existing_v0_panel

    try:
        run_v1_viewer()
        return "v1"
    except Exception as exc:
        app_module.Console.PrintWarning(
            "CorridorRoad v1 earthwork viewer unavailable, "
            f"falling back to the existing v0 panel: {exc}\n"
        )
        open_existing_v0_panel()
        return "v0"


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
