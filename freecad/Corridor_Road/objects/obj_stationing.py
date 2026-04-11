# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/objects/obj_stationing.py
import Part

from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment


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
        obj.addProperty("App::PropertyInteger", "LengthSchemaVersion", "Stations", "Stationing scalar length storage schema")
        obj.LengthSchemaVersion = 2

    @staticmethod
    def _migrate_length_schema(obj):
        if obj is None or not hasattr(obj, "LengthSchemaVersion"):
            return
        try:
            schema = int(getattr(obj, "LengthSchemaVersion", 0) or 0)
        except Exception:
            schema = 0
        if schema >= 2:
            return
        obj.LengthSchemaVersion = 2

    def execute(self, obj):
        self._migrate_length_schema(obj)
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

        total = float(getattr(aln, "TotalLength", 0.0) or 0.0)
        if total <= 1.0e-9:
            total = _units.meters_from_model_length(getattr(obj, "Document", None), float(getattr(aln.Shape, "Length", 0.0) or 0.0))

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
        half = _units.model_length_from_meters(getattr(obj, "Document", None), tick_len * 0.5)

        for s_val, p in zip(stations, points):
            n = HorizontalAlignment.normal_at_station(aln, s_val)

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
