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
_WORKBENCH_BASE = getattr(Gui, "Workbench", object)


def corridorroad_workflow_command_groups():
    """Return the v1-oriented top-level command groups used by the workbench."""

    return {
        "project": [
            "CorridorRoad_ProjectSetup",
        ],
        "terrain": [
            "CorridorRoad_V1EditTIN",
        ],
        "alignment": [
            "CorridorRoad_V1EditAlignment",
        ],
        "station_profile": [
            "CorridorRoad_V1GenerateStations",
            "CorridorRoad_V1EditProfile",
            "CorridorRoad_ReviewPlanProfile",
        ],
        "assembly_region": [
            "CorridorRoad_V1EditAssembly",
            "CorridorRoad_V1EditStructures",
            "CorridorRoad_V1EditRegions",
        ],
        "drainage": [
            "CorridorRoad_V1EditDrainage",
            "CorridorRoad_V1DrainageReview",
        ],
        "corridor": [
            "CorridorRoad_V1AppliedSections",
            "CorridorRoad_GenerateCorridor",
        ],
        "review": [
            "CorridorRoad_ViewCrossSection",
            "CorridorRoad_GenerateCutFillCalc",
        ],
        "output": [
            "CorridorRoad_OutputsExchange",
            "CorridorRoad_V1StructureOutput",
        ],
        "ai": [
            "CorridorRoad_AIAssist",
        ],
        "watertight_solid": [
            "CorridorRoad_V1WatertightSolids",
        ],
    }


def corridorroad_workflow_toolbar_commands():
    """Return toolbar command ids in the intended workflow order."""

    groups = corridorroad_workflow_command_groups()
    return (
        groups["project"]
        + groups["terrain"]
        + groups["alignment"]
        + groups["station_profile"]
        + groups["assembly_region"]
        + groups["drainage"]
        + groups["corridor"]
        + groups["review"]
        + groups["output"]
        + groups["ai"]
        + groups["watertight_solid"]
    )


class CorridorRoadWorkbench(_WORKBENCH_BASE):
    MenuText = "CorridorRoad"
    ToolTip = "CorridorRoad Workbench for road corridor design, review, and outputs"
    Icon = _WB_ICON_PATH if os.path.isfile(_WB_ICON_PATH) else ""

    def Initialize(self):
        import freecad.Corridor_Road.commands.cmd_new_project  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_project_setup  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_edit_tin  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_create_alignment  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_alignment_editor  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_profile_editor  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_generate_stations  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_assembly_editor  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_structure_editor  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_drainage_editor  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_drainage_review  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_view_sections  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_review_plan_profile  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_earthwork_balance  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_structure_output  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_alignment  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_review_alignment  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_review_plan_profile  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_typical_section  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_regions  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_region_editor  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_view_cross_section  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_generate_corridor  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_generate_cut_fill_calc  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_outputs_exchange  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_ai_assist  # noqa: F401
        import freecad.Corridor_Road.v1.commands.cmd_watertight_solids  # noqa: F401

        groups = corridorroad_workflow_command_groups()
        project_commands = groups["project"]
        terrain_commands = groups["terrain"]
        alignment_commands = groups["alignment"]
        station_profile_commands = groups["station_profile"]
        assembly_region_commands = groups["assembly_region"]
        drainage_commands = groups["drainage"]
        corridor_commands = groups["corridor"]
        review_commands = groups["review"]
        output_commands = groups["output"]
        ai_commands = groups["ai"]
        watertight_solid_commands = groups["watertight_solid"]

        workflow_toolbar_commands = corridorroad_workflow_toolbar_commands()

        self.appendToolbar("CorridorRoad", list(workflow_toolbar_commands))

        self.appendMenu(["CorridorRoad", "Project"], list(project_commands))
        self.appendMenu(["CorridorRoad", "Survey & Surface"], list(terrain_commands))
        self.appendMenu(["CorridorRoad", "Alignment"], list(alignment_commands))
        self.appendMenu(["CorridorRoad", "Stations & Profile"], list(station_profile_commands))
        self.appendMenu(["CorridorRoad", "Assembly & Regions"], list(assembly_region_commands))
        self.appendMenu(["CorridorRoad", "Drainage"], list(drainage_commands))
        self.appendMenu(["CorridorRoad", "Corridor"], list(corridor_commands))
        self.appendMenu(["CorridorRoad", "Review"], list(review_commands))
        self.appendMenu(["CorridorRoad", "Outputs & Exchange"], list(output_commands))
        self.appendMenu(["CorridorRoad", "AI Assist"], list(ai_commands))
        self.appendMenu(["CorridorRoad", "Watertight Solids"], list(watertight_solid_commands))

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
    if not hasattr(Gui, "addWorkbench") or not hasattr(Gui, "Workbench"):
        return
    if getattr(Gui, "_corridorroad_wb_registered", False):
        return
    Gui.addWorkbench(CorridorRoadWorkbench())
    setattr(Gui, "_corridorroad_wb_registered", True)


register_workbench()
