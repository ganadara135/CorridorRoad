# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_alignment_editor import AlignmentEditorTaskPanel
from freecad.Corridor_Road.ui.task_profile_editor import ProfileEditorTaskPanel
from freecad.Corridor_Road.v1.commands.selection_context import (
    selected_alignment_profile_target,
)


def run_plan_profile_review_command(
    *,
    app_module=App,
    gui_module=Gui,
    run_v1_viewer=None,
    resolve_targets=None,
    open_existing_v0_alignment_editor=None,
    open_existing_v0_profile_editor=None,
):
    """Run the preferred plan/profile review path with a safe v0 fallback."""

    if run_v1_viewer is None:
        from freecad.Corridor_Road.v1.commands.cmd_review_plan_profile import (
            run_v1_plan_profile_preview_command,
        )

        run_v1_viewer = run_v1_plan_profile_preview_command

    if resolve_targets is None:
        def _resolve_targets():
            document = getattr(app_module, "ActiveDocument", None)
            return selected_alignment_profile_target(gui_module, document)

        resolve_targets = _resolve_targets

    if open_existing_v0_alignment_editor is None:
        def _open_existing_v0_alignment_editor():
            panel = AlignmentEditorTaskPanel()
            gui_module.Control.showDialog(panel)
            return panel

        open_existing_v0_alignment_editor = _open_existing_v0_alignment_editor

    if open_existing_v0_profile_editor is None:
        def _open_existing_v0_profile_editor():
            panel = ProfileEditorTaskPanel()
            gui_module.Control.showDialog(panel)
            return panel

        open_existing_v0_profile_editor = _open_existing_v0_profile_editor

    try:
        run_v1_viewer()
        return "v1"
    except Exception as exc:
        preferred_alignment, preferred_profile = resolve_targets()
        if preferred_profile is not None:
            app_module.Console.PrintWarning(
                "CorridorRoad v1 plan/profile viewer unavailable, "
                f"falling back to the existing v0 profile editor: {exc}\n"
            )
            open_existing_v0_profile_editor()
            return "v0_profile"

        app_module.Console.PrintWarning(
            "CorridorRoad v1 plan/profile viewer unavailable, "
            f"falling back to the existing v0 alignment editor: {exc}\n"
        )
        open_existing_v0_alignment_editor()
        return "v0_alignment"


class CmdReviewPlanProfile:
    def GetResources(self):
        return {
            "Pixmap": icon_path("plan_profile_review.svg"),
            "MenuText": "Review Plan/Profile",
            "ToolTip": "Review stationing and profile results for the current document",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        run_plan_profile_review_command()


if hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_ReviewPlanProfile", CmdReviewPlanProfile())
