# CorridorRoad/objects/obj_stationing.py
import FreeCAD as App
import Part

from objects.obj_alignment import HorizontalAlignment


class Stationing:
    """
    Generates tick marks along alignment as Shape (Compound of lines)
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "Stationing"

        obj.addProperty("App::PropertyLink", "Alignment", "Stations", "Link to HorizontalAlignment")
        obj.addProperty("App::PropertyFloat", "Interval", "Stations", "Station interval (m)")
        obj.Interval = 20.0

        obj.addProperty("App::PropertyFloat", "TickLength", "Stations", "Tick length (m)")
        obj.TickLength = 2.0

        obj.addProperty("App::PropertyBool", "ShowTicks", "Stations", "Show tick marks as shape")
        obj.ShowTicks = True

        obj.addProperty("App::PropertyFloatList", "StationValues", "Stations", "Computed stations (m)")
        obj.addProperty("App::PropertyVectorList", "StationPoints", "Stations", "Computed points (XYZ)")

    def execute(self, obj):
        aln = obj.Alignment
        if aln is None or aln.Shape is None or aln.Shape.isNull():
            obj.Shape = Part.Shape()
            obj.StationValues = []
            obj.StationPoints = []

            return

        interval = float(obj.Interval)
        if interval <= 0:
            interval = 20.0
            obj.Interval = interval

        total = float(aln.Shape.Length)

        stations = []
        points = []

        s = 0.0
        while s < total:
            stations.append(s)
            points.append(HorizontalAlignment.point_at_station(aln, s))
            s += interval

        stations.append(total)
        points.append(HorizontalAlignment.point_at_station(aln, total))

        obj.StationValues = stations
        obj.StationPoints = points

        if not obj.ShowTicks:
            obj.Shape = Part.Shape()

            return

        tick_len = float(obj.TickLength)
        if tick_len <= 0:
            tick_len = 2.0
            obj.TickLength = tick_len

        tick_edges = []
        half = tick_len * 0.5

        for s_val, p in zip(stations, points):
            t = HorizontalAlignment.tangent_at_station(aln, s_val)
            n = App.Vector(-t.y, t.x, 0)
            if n.Length < 1e-9:
                n = App.Vector(0, 1, 0)

            else:
                n = n.normalize()

            a = p - n * half
            b = p + n * half
            tick_edges.append(Part.makeLine(a, b))

        obj.Shape = Part.Compound(tick_edges)


class ViewProviderStationing:
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
