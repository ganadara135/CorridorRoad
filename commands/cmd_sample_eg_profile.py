# CorridorRoad/commands/cmd_sample_eg_profile.py
import FreeCAD as App
import FreeCADGui as Gui

from objects.obj_profile_eg import ProfileEG, ViewProviderProfileEG
from objects.obj_project import CorridorRoadProject


def _find_project(doc):
    for o in doc.Objects:
        if o.Name.startswith("CorridorRoadProject"):
            return o

    return None


def _find_stationing(doc):
    for o in doc.Objects:
        if o.Name.startswith("Stationing"):
            return o

    return None


class CmdSampleEGProfile:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Sample EG Profile",
            "ToolTip": "Create Existing Ground Profile (skeleton) from stations",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            raise Exception("No active document.")

        st = _find_stationing(doc)
        if st is None:
            raise Exception("No Stationing found. Generate Stations first.")

        prof = doc.addObject("Part::FeaturePython", "ProfileEG")
        ProfileEG(prof)
        ViewProviderProfileEG(prof.ViewObject)
        prof.Stationing = st
        prof.BaseElevation = 100.0
        prof.UseDummySurface = True
        prof.Label = "EG Profile"

        prj = _find_project(doc)
        if prj is not None:
            prj.ProfileEG = prof
            CorridorRoadProject.adopt(prj, prof)

            if prj.Stationing is None:
                prj.Stationing = st
                CorridorRoadProject.adopt(prj, st)

        doc.recompute()
        
        Gui.ActiveDocument.ActiveView.fitAll()


Gui.addCommand("CorridorRoad_SampleEGProfile", CmdSampleEGProfile())
