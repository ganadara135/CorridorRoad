# CorridorRoad/commands/cmd_new_project.py
import FreeCAD as App
import FreeCADGui as Gui

from objects.obj_project import CorridorRoadProject


class CmdNewProject:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "New Project",
            "ToolTip": "Create a CorridorRoad project container object",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            raise Exception("No active document.")

        obj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(obj)
        obj.Label = "CorridorRoad Project"

        # Try auto-link and adopt existing objects
        CorridorRoadProject.auto_link(doc, obj)

        if obj.Alignment is not None:
            CorridorRoadProject.adopt(obj, obj.Alignment)

        if obj.Stationing is not None:
            CorridorRoadProject.adopt(obj, obj.Stationing)

        if obj.ProfileEG is not None:
            CorridorRoadProject.adopt(obj, obj.ProfileEG)

        doc.recompute()


Gui.addCommand("CorridorRoad_NewProject", CmdNewProject())
