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
    ToolTip = "CorridorRoad Workbench (Sample Alignment / Stations / ProfileEG)"
    Icon = ""

    def Initialize(self):
        # Absolute imports (no leading dots)
        import commands.cmd_new_project  # noqa: F401
        import commands.cmd_create_alignment  # noqa: F401
        import commands.cmd_generate_stations  # noqa: F401
        import commands.cmd_sample_eg_profile  # noqa: F401
        import commands.cmd_edit_profiles  # noqa: F401
        import commands.cmd_edit_pvi  # noqa: F401

        self.appendToolbar("CorridorRoad", [
            "CorridorRoad_NewProject",
            "CorridorRoad_CreateAlignment",
            "CorridorRoad_GenerateStations",
            "CorridorRoad_SampleEGProfile",
            "CorridorRoad_EditProfiles",
            "CorridorRoad_EditPVI",
        ])

        self.appendMenu("CorridorRoad", [
            "CorridorRoad_NewProject",
            "CorridorRoad_CreateAlignment",
            "CorridorRoad_GenerateStations",
            "CorridorRoad_SampleEGProfile",
            "CorridorRoad_EditProfiles",
            "CorridorRoad_EditPVI",
        ])

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(CorridorRoadWorkbench())
