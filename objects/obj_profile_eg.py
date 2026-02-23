# CorridorRoad/objects/obj_profile_eg.py
import FreeCAD as App
import Part
import math


class ProfileEG:
    """
    Profile polyline in "profile space": (X=station, Y=elevation, Z=0)
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "ProfileEG"

        obj.addProperty("App::PropertyLink", "Stationing", "Profile", "Link to Stationing object")
        obj.addProperty("App::PropertyLink", "Terrain", "Profile", "Link to Terrain (future)")

        obj.addProperty("App::PropertyFloatList", "Stations", "Profile", "Station values (m)")
        obj.addProperty("App::PropertyFloatList", "Elevations", "Profile", "EG elevations (m)")

        obj.addProperty("App::PropertyFloat", "BaseElevation", "Profile", "Base elevation offset (m)")
        obj.BaseElevation = 100.0

        obj.addProperty("App::PropertyBool", "UseDummySurface", "Profile", "Use dummy elevation (for now)")
        obj.UseDummySurface = True

    def execute(self, obj):
        st = obj.Stationing
        if st is None or not st.StationValues:
            obj.Shape = Part.Shape()
            obj.Stations = []
            obj.Elevations = []

            return

        stations = list(st.StationValues)
        base = float(obj.BaseElevation)

        elevs = []
        for s in stations:
            if obj.UseDummySurface:
                z = base + 5.0 * math.sin(s / 30.0) + 2.0 * math.cos(s / 12.0)

            else:
                z = base

            elevs.append(float(z))

        obj.Stations = stations
        obj.Elevations = elevs

        pts = [App.Vector(float(s), float(z), 0.0) for s, z in zip(stations, elevs)]
        if len(pts) < 2:
            obj.Shape = Part.Shape()

            return

        obj.Shape = Part.makePolygon(pts)


class ViewProviderProfileEG:
    def __init__(self, vobj):
        vobj.Proxy = self
        self.Object = None

    def attach(self, vobj):
        self.Object = vobj.Object

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
