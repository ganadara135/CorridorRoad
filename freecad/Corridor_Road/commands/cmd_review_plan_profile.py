# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path


def run_plan_profile_review_command(*, app_module=App, run_v1_viewer=None):
    """Open the v1 Plan/Profile review, reporting a failure instead of opening a v0 editor.

    The v0 alignment and profile editors this used to fall back to create legacy proxy objects,
    which are retiring (docsV1/V1_LEGACY_PROXY_MIGRATION_DESIGN.md, decision 4).
    """

    if run_v1_viewer is None:
        from freecad.Corridor_Road.v1.commands.cmd_review_plan_profile import (
            run_v1_plan_profile_preview_command,
        )

        run_v1_viewer = run_v1_plan_profile_preview_command

    try:
        run_v1_viewer()
        return "v1"
    except Exception as exc:
        app_module.Console.PrintError(f"Plan/Profile review was not opened: {exc}\n")
        return "error"


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
