# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_cross_section_viewer import CrossSectionViewerTaskPanel


def run_cross_section_review_command(
    *,
    app_module=App,
    gui_module=Gui,
    run_v1_viewer=None,
    open_existing_v0_viewer=None,
):
    """Run the preferred cross-section review path with a safe v0 fallback."""

    if run_v1_viewer is None:
        from freecad.Corridor_Road.v1.commands.cmd_view_sections import (
            run_v1_section_view_command,
        )

        run_v1_viewer = run_v1_section_view_command

    if open_existing_v0_viewer is None:
        def _open_existing_v0_viewer():
            panel = CrossSectionViewerTaskPanel()
            gui_module.Control.showDialog(panel)
            return panel

        open_existing_v0_viewer = _open_existing_v0_viewer

    try:
        run_v1_viewer()
        return "v1"
    except Exception as exc:
        app_module.Console.PrintWarning(
            "CorridorRoad v1 cross-section viewer unavailable, "
            f"falling back to the existing v0 viewer: {exc}\n"
        )
        open_existing_v0_viewer()
        return "v0"


class CmdViewCrossSection:
    def GetResources(self):
        return {
            "Pixmap": icon_path("view_cross_section.svg"),
            "MenuText": "Review Cross Sections",
            "ToolTip": "Review cross-section results for the current corridor document",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        run_cross_section_review_command()


if hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_ViewCrossSection", CmdViewCrossSection())
