# CorridorRoad/objects/obj_profile_bundle.py
import FreeCAD as App
import Part


class ProfileBundle:
    """
    Stores station-based profiles (data):
      - Stations[]
      - ElevEG[]
      - ElevFG[]
      - ElevDelta = FG - EG

    Visualization policy (refactored):
      - EG wire is drawn here (optional)
      - FG wire is drawn by VerticalAlignment object (analytic edges)
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "ProfileBundle"

        obj.addProperty("App::PropertyLink", "Stationing", "Profiles", "Stationing object link")
        obj.addProperty("App::PropertyLink", "VerticalAlignment", "Profiles", "VerticalAlignment object link")

        obj.addProperty("App::PropertyFloatList", "Stations", "Profiles", "Stations (m)")
        obj.addProperty("App::PropertyFloatList", "ElevEG", "Profiles", "Existing Ground elevations (m)")
        obj.addProperty("App::PropertyFloatList", "ElevFG", "Profiles", "Finished Grade elevations (m)")
        obj.addProperty("App::PropertyFloatList", "ElevDelta", "Profiles", "Delta elevations (FG - EG) (m)")

        obj.addProperty("App::PropertyBool", "ShowEGWire", "Display", "Show EG wire")
        obj.ShowEGWire = True

        obj.addProperty("App::PropertyFloat", "WireZOffset", "Display", "Z offset for EG wire")
        obj.WireZOffset = 0.0

        obj.addProperty("App::PropertyBool", "FGIsManual", "Profiles", "If True, FG was edited manually (not from VerticalAlignment)")
        obj.FGIsManual = False

    def execute(self, obj):
        st = list(obj.Stations or [])
        eg = list(obj.ElevEG or [])
        fg = list(obj.ElevFG or [])

        n = min(len(st), len(eg), len(fg))
        if n < 2:
            obj.Shape = Part.Shape()
            obj.ElevDelta = []

            return

        st = st[:n]
        eg = eg[:n]
        fg = fg[:n]

        obj.ElevDelta = [(float(fg[i]) - float(eg[i])) for i in range(n)]

        shapes = []

        if obj.ShowEGWire:
            zoff = float(obj.WireZOffset)
            pts_eg = [App.Vector(float(st[i]), float(eg[i]), zoff) for i in range(n)]
            shapes.append(Part.makePolygon(pts_eg))

        if not shapes:
            obj.Shape = Part.Shape()

            return

        if len(shapes) == 1:
            obj.Shape = shapes[0]

            return

        obj.Shape = Part.Compound(shapes)


class ViewProviderProfileBundle:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Wireframe"
            vobj.LineWidth = 2
        except Exception:
            pass

    def getIcon(self):
        return ""

    def updateData(self, obj, prop):
        return

    def onChanged(self, vobj, prop):
        return

    def getDisplayModes(self, vobj):
        return ["Wireframe", "Flat Lines"]

    def getDefaultDisplayMode(self):
        return "Wireframe"

    def setDisplayMode(self, mode):
        return mode