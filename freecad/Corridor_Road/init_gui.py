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
    ToolTip = "CorridorRoad Workbench (Alignment / Stations / Profiles)"
    Icon = _WB_ICON_PATH if os.path.isfile(_WB_ICON_PATH) else ""

    def Initialize(self):
        import freecad.Corridor_Road.commands.cmd_new_project  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_project_setup  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_import_pointcloud_dem  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_create_alignment  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_alignment  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_generate_stations  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_profiles  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_pvi  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_generate_centerline3d  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_typical_section  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_structures  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_edit_regions  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_generate_sections  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_view_cross_section  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_generate_corridor_loft  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_generate_design_grading_surface  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_generate_design_terrain  # noqa: F401
        import freecad.Corridor_Road.commands.cmd_generate_cut_fill_calc  # noqa: F401

        self.appendToolbar(
            "CorridorRoad",
            [
                "CorridorRoad_NewProject",
                "CorridorRoad_ProjectSetup",
                "CorridorRoad_ImportPointCloudDEM",
                "CorridorRoad_EditAlignment",
                "CorridorRoad_GenerateStations",
                "CorridorRoad_EditProfiles",
                "CorridorRoad_EditPVI",
                "CorridorRoad_GenerateCenterline3D",
                "CorridorRoad_EditTypicalSection",
                "CorridorRoad_EditStructures",
                "CorridorRoad_EditRegions",
                "CorridorRoad_GenerateSections",
                "CorridorRoad_ViewCrossSection",
                "CorridorRoad_GenerateCorridor",
                "CorridorRoad_GenerateDesignGradingSurface",
                "CorridorRoad_GenerateDesignTerrain",
                "CorridorRoad_GenerateCutFillCalc",
            ],
        )

        self.appendMenu(
            "CorridorRoad",
            [
                "CorridorRoad_NewProject",
                "CorridorRoad_ProjectSetup",
                "CorridorRoad_ImportPointCloudDEM",
                "CorridorRoad_EditAlignment",
                "CorridorRoad_GenerateStations",
                "CorridorRoad_EditProfiles",
                "CorridorRoad_EditPVI",
                "CorridorRoad_GenerateCenterline3D",
                "CorridorRoad_EditTypicalSection",
                "CorridorRoad_EditStructures",
                "CorridorRoad_EditRegions",
                "CorridorRoad_GenerateSections",
                "CorridorRoad_ViewCrossSection",
                "CorridorRoad_GenerateCorridor",
                "CorridorRoad_GenerateDesignGradingSurface",
                "CorridorRoad_GenerateDesignTerrain",
                "CorridorRoad_GenerateCutFillCalc",
            ],
        )

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
