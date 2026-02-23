# CorridorRoad/commands/cmd_create_alignment.py
import FreeCAD as App
import FreeCADGui as Gui

from objects.obj_alignment import HorizontalAlignment, ViewProviderHorizontalAlignment


class CmdCreateAlignment:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Create Alignment",
            "ToolTip": "Create a simple Horizontal Alignment (FeaturePython + Wire)",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            raise Exception("No active document.")

        obj = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
        HorizontalAlignment(obj)
        ViewProviderHorizontalAlignment(obj.ViewObject)

        obj.IPPoints = [
            App.Vector(0, 0, 0),
            App.Vector(50, 0, 0),
            App.Vector(80, 20, 0),
            App.Vector(120, 20, 0),
        ]
        obj.Label = "Alignment"

        obj.touch()
        doc.recompute()

        Gui.ActiveDocument.ActiveView.fitAll()


Gui.addCommand("CorridorRoad_CreateAlignment", CmdCreateAlignment())
