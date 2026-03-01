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

        if hasattr(obj, "Centerline3D") and obj.Centerline3D is not None:
            CorridorRoadProject.adopt(obj, obj.Centerline3D)
        if hasattr(obj, "Centerline3DDisplay") and obj.Centerline3DDisplay is not None:
            CorridorRoadProject.adopt(obj, obj.Centerline3DDisplay)
        if hasattr(obj, "AssemblyTemplate") and obj.AssemblyTemplate is not None:
            CorridorRoadProject.adopt(obj, obj.AssemblyTemplate)
        if hasattr(obj, "SectionSet") and obj.SectionSet is not None:
            CorridorRoadProject.adopt(obj, obj.SectionSet)
        if hasattr(obj, "CorridorLoft") and obj.CorridorLoft is not None:
            CorridorRoadProject.adopt(obj, obj.CorridorLoft)
        if hasattr(obj, "SurfaceComparison") and obj.SurfaceComparison is not None:
            CorridorRoadProject.adopt(obj, obj.SurfaceComparison)

        doc.recompute()


Gui.addCommand("CorridorRoad_NewProject", CmdNewProject())
