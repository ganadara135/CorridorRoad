# CorridorRoad/commands/cmd_generate_design_terrain.py
import FreeCAD as App
import FreeCADGui as Gui

from ui.task_design_terrain import DesignTerrainTaskPanel


class CmdGenerateDesignTerrain:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Design Terrain",
            "ToolTip": "Create/update composite design terrain from DesignGradingSurface and Existing Terrain",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = DesignTerrainTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_GenerateDesignTerrain", CmdGenerateDesignTerrain())
