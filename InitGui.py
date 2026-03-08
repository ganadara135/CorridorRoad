# CorridorRoad/InitGui.py
import os
import sys
import FreeCAD as App
import FreeCADGui as Gui

# ---- Resolve and add workbench root to sys.path (no __file__ usage) ----
# Prefer User Mod, fallback to System Mod
_user_wb = os.path.join(App.getUserAppDataDir(), "Mod", "CorridorRoad")
_sys_wb = os.path.join(App.getHomePath(), "Mod", "CorridorRoad")

WB_DIR = ""
if os.path.isdir(_user_wb):
    WB_DIR = _user_wb
elif os.path.isdir(_sys_wb):
    WB_DIR = _sys_wb

if WB_DIR and (WB_DIR not in sys.path):
    sys.path.insert(0, WB_DIR)


class CorridorRoadWorkbench(Gui.Workbench):
    MenuText = "CorridorRoad"
    ToolTip = "CorridorRoad Workbench (Alignment / Stations / Profiles)"
    Icon = os.path.join(WB_DIR, "resources", "icons", "corridorroad_workbench.svg") if WB_DIR else ""

    def Initialize(self):
        # Absolute imports (no leading dots)
        import commands.cmd_new_project  # noqa: F401
        import commands.cmd_project_setup  # noqa: F401
        import commands.cmd_create_alignment  # noqa: F401
        import commands.cmd_edit_alignment  # noqa: F401
        import commands.cmd_generate_stations  # noqa: F401
        import commands.cmd_edit_profiles  # noqa: F401
        import commands.cmd_edit_pvi  # noqa: F401
        import commands.cmd_generate_centerline3d  # noqa: F401
        import commands.cmd_generate_sections  # noqa: F401
        import commands.cmd_generate_corridor_loft  # noqa: F401
        import commands.cmd_generate_design_grading_surface  # noqa: F401
        import commands.cmd_generate_design_terrain  # noqa: F401
        import commands.cmd_generate_cut_fill_calc  # noqa: F401

        self.appendToolbar("CorridorRoad", [
            "CorridorRoad_NewProject",
            "CorridorRoad_ProjectSetup",
            "CorridorRoad_CreateAlignment",
            "CorridorRoad_EditAlignment",
            "CorridorRoad_GenerateStations",
            "CorridorRoad_EditProfiles",
            "CorridorRoad_EditPVI",
            "CorridorRoad_GenerateCenterline3D",
            "CorridorRoad_GenerateSections",
            "CorridorRoad_GenerateCorridorLoft",
            "CorridorRoad_GenerateDesignGradingSurface",
            "CorridorRoad_GenerateDesignTerrain",
            "CorridorRoad_GenerateCutFillCalc",
        ])

        self.appendMenu("CorridorRoad", [
            "CorridorRoad_NewProject",
            "CorridorRoad_ProjectSetup",
            "CorridorRoad_CreateAlignment",
            "CorridorRoad_EditAlignment",
            "CorridorRoad_GenerateStations",
            "CorridorRoad_EditProfiles",
            "CorridorRoad_EditPVI",
            "CorridorRoad_GenerateCenterline3D",
            "CorridorRoad_GenerateSections",
            "CorridorRoad_GenerateCorridorLoft",
            "CorridorRoad_GenerateDesignGradingSurface",
            "CorridorRoad_GenerateDesignTerrain",
            "CorridorRoad_GenerateCutFillCalc",
        ])

    def ContextMenu(self, recipient):
        try:
            sel = list(Gui.Selection.getSelection() or [])
        except Exception:
            sel = []
        has_project = any(str(getattr(o, "Name", "") or "").startswith("CorridorRoadProject") for o in sel)
        if has_project:
            self.appendContextMenu("CorridorRoad Project", ["CorridorRoad_ProjectSetup"])

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            return
        try:
            from objects.obj_project import CorridorRoadProject, ensure_project_properties, ensure_project_tree
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


Gui.addWorkbench(CorridorRoadWorkbench())
