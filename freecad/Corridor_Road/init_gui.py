# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import os

import FreeCAD as App
import FreeCADGui as Gui

from . import ensure_package_on_sys_path, install_virtual_path_mappings
from .misc.resources import icon_path


ensure_package_on_sys_path()
install_virtual_path_mappings(eager=True)

_WB_ICON_PATH = icon_path("corridorroad_workbench.svg")


class CorridorRoadWorkbench(Gui.Workbench):
    MenuText = "CorridorRoad"
    ToolTip = "CorridorRoad Workbench for road corridor design, review, and outputs"
    Icon = _WB_ICON_PATH if os.path.isfile(_WB_ICON_PATH) else ""

    def Initialize(self):
        import freecad.Corridor_Road.commands.cmd_new_project  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_project_setup  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_import_pointcloud_tin  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_create_alignment  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_create_alignment  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_alignment_editor  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_create_profile  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_profile_editor  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_generate_stations  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_alignment  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_review_alignment  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_profiles  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_pvi  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_review_plan_profile  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_typical_section  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_structures  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_regions  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_view_cross_section  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_generate_corridor  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_generate_cut_fill_calc  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_outputs_exchange  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_ai_assist  # noqa: F401

        project_commands = [
            "CorridorRoad_NewProject",
            "CorridorRoad_ProjectSetup",
        ]
        terrain_commands = [
            "CorridorRoad_ImportPointCloudTIN",
        ]
        alignment_commands = [
            "CorridorRoad_V1EditAlignment",
        ]
        station_profile_commands = [
            "CorridorRoad_V1CreateProfile",
            "CorridorRoad_V1EditProfile",
            "CorridorRoad_V1GenerateStations",
            "CorridorRoad_EditProfiles",
            "CorridorRoad_EditPVI",
            "CorridorRoad_ReviewPlanProfile",
        ]
        assembly_region_commands = [
            "CorridorRoad_EditTypicalSection",
            "CorridorRoad_EditRegions",
            "CorridorRoad_EditStructures",
        ]
        corridor_commands = [
            "CorridorRoad_GenerateCorridor",
        ]
        review_commands = [
            "CorridorRoad_ViewCrossSection",
            "CorridorRoad_GenerateCutFillCalc",
        ]
        output_commands = [
            "CorridorRoad_OutputsExchange",
        ]
        ai_commands = [
            "CorridorRoad_AIAssist",
        ]

        workflow_toolbar_commands = (
            project_commands
            + terrain_commands
            + alignment_commands
            + station_profile_commands
            + assembly_region_commands
            + corridor_commands
            + review_commands
            + output_commands
            + ai_commands
        )

        self.appendToolbar("CorridorRoad", list(workflow_toolbar_commands))

        self.appendMenu(["CorridorRoad", "Project"], list(project_commands))
        self.appendMenu(["CorridorRoad", "Survey & Surface"], list(terrain_commands))
        self.appendMenu(["CorridorRoad", "Alignment"], list(alignment_commands))
        self.appendMenu(["CorridorRoad", "Stations & Profile"], list(station_profile_commands))
        self.appendMenu(["CorridorRoad", "Assembly & Regions"], list(assembly_region_commands))
        self.appendMenu(["CorridorRoad", "Corridor"], list(corridor_commands))
        self.appendMenu(["CorridorRoad", "Review"], list(review_commands))
        self.appendMenu(["CorridorRoad", "Outputs & Exchange"], list(output_commands))
        self.appendMenu(["CorridorRoad", "AI Assist"], list(ai_commands))

    def ContextMenu(self, recipient):
        try:
            sel = list(Gui.Selection.getSelection() or [])
        except Exception:
            sel = []
        has_project = any(
            str(getattr(o, "Name", "") or "").startswith("CorridorRoadProject") for o in sel
        )
        if has_project:
            self.appendContextMenu("CorridorRoad Project", ["CorridorRoad_ProjectSetup"])

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            return
        try:
            from freecad.Corridor_Road.objects.obj_project import (
                CorridorRoadProject,
                ensure_project_properties,
                ensure_project_tree,
            )
        except Exception:
            return
        touched = False
        for o in list(getattr(doc, "Objects", []) or []):
            if not str(getattr(o, "Name", "") or "").startswith("CorridorRoadProject"):
                continue
            try:
                ensure_project_properties(o)
                ensure_project_tree(o, include_references=False)
                CorridorRoadProject.auto_link(doc, o)
                o.touch()
                touched = True
            except Exception:
                pass
        if touched:
            try:
                doc.recompute()
            except Exception:
                pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


def register_workbench():
    if getattr(Gui, "_corridorroad_wb_registered", False):
        return
    Gui.addWorkbench(CorridorRoadWorkbench())
    setattr(Gui, "_corridorroad_wb_registered", True)


register_workbench()
