# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_generate_stations.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_station_generator import StationGeneratorTaskPanel


class CmdGenerateStations:
    def GetResources(self):
        return {
            "Pixmap": icon_path("stations.svg"),
            "MenuText": "Stations",
            "ToolTip": "Generate station ticks along the alignment",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = StationGeneratorTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_GenerateStations", CmdGenerateStations())
