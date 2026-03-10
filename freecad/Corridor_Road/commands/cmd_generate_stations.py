# CorridorRoad/commands/cmd_generate_stations.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.ui.task_station_generator import StationGeneratorTaskPanel


class CmdGenerateStations:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Stations",
            "ToolTip": "Create Stationing object and generate station ticks along alignment",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = StationGeneratorTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_GenerateStations", CmdGenerateStations())
