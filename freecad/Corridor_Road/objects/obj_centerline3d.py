# CorridorRoad/objects/obj_centerline3d.py
import math

import FreeCAD as App
import Part

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_project import get_length_scale
from freecad.Corridor_Road.objects.obj_vertical_alignment import VerticalAlignment


def _unique_sorted(values, tol: float = 1e-6):
    vals = sorted([float(v) for v in values])
    out = []
    for v in vals:
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def _build_bundle_pairs(bundle_obj):
    st = list(getattr(bundle_obj, "Stations", []) or [])
    fg = list(getattr(bundle_obj, "ElevFG", []) or [])
    n = min(len(st), len(fg))
    if n < 1:
        return []

    pairs = [(float(st[i]), float(fg[i])) for i in range(n)]
    pairs.sort(key=lambda x: x[0])
    return pairs


def _interp_bundle_fg(bundle_obj, s: float):
    pairs = _build_bundle_pairs(bundle_obj)
    if not pairs:
        raise Exception("ProfileBundleFG source selected, but bundle has no valid Stations/ElevFG data.")

    if s <= pairs[0][0]:
        return float(pairs[0][1])
    if s >= pairs[-1][0]:
        return float(pairs[-1][1])

    for i in range(len(pairs) - 1):
        s0, z0 = pairs[i]
        s1, z1 = pairs[i + 1]
        if s0 <= s <= s1:
            if abs(s1 - s0) < 1e-12:
                return float(z0)
            t = (s - s0) / (s1 - s0)
            return float(z0 + t * (z1 - z0))

    return float(pairs[-1][1])


def ensure_centerline3d_properties(obj):
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)

    if not hasattr(obj, "Alignment"):
        obj.addProperty("App::PropertyLink", "Alignment", "Centerline3D", "HorizontalAlignment link")
    if not hasattr(obj, "Stationing"):
        obj.addProperty("App::PropertyLink", "Stationing", "Centerline3D", "Stationing link (optional)")
    if not hasattr(obj, "VerticalAlignment"):
        obj.addProperty("App::PropertyLink", "VerticalAlignment", "Centerline3D", "VerticalAlignment link (optional)")
    if not hasattr(obj, "ProfileBundle"):
        obj.addProperty("App::PropertyLink", "ProfileBundle", "Centerline3D", "ProfileBundle link (optional)")

    if not hasattr(obj, "UseStationing"):
        obj.addProperty("App::PropertyBool", "UseStationing", "Sampling", "Use Stationing.StationValues when available")
        obj.UseStationing = True

    if not hasattr(obj, "SamplingInterval"):
        obj.addProperty("App::PropertyFloat", "SamplingInterval", "Sampling", "Sampling interval (m) when Stationing is not used")
        obj.SamplingInterval = 5.0 * scale

    if not hasattr(obj, "ElevationSource"):
        obj.addProperty("App::PropertyEnumeration", "ElevationSource", "Sampling", "Elevation source mode")
        obj.ElevationSource = ["Auto", "VerticalAlignment", "ProfileBundleFG", "FlatZero"]
        obj.ElevationSource = "Auto"

    if not hasattr(obj, "StationValues"):
        obj.addProperty("App::PropertyFloatList", "StationValues", "Result", "Stations prepared by centerline engine (m)")
    if not hasattr(obj, "CenterlinePoints"):
        obj.addProperty("App::PropertyVectorList", "CenterlinePoints", "Result", "Prepared 3D points at StationValues")
    if not hasattr(obj, "TotalLength3D"):
        obj.addProperty("App::PropertyFloat", "TotalLength3D", "Result", "Approx. 3D length from prepared points")
        obj.TotalLength3D = 0.0

    if not hasattr(obj, "ResolvedElevationSource"):
        obj.addProperty("App::PropertyString", "ResolvedElevationSource", "Result", "Resolved elevation source used at runtime")
        obj.ResolvedElevationSource = "N/A"

    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"


class Centerline3D:
    """
    Compute 3D centerline data by integrating:
      - Horizontal XY from HorizontalAlignment.point_at_station
      - Vertical Z from VerticalAlignment or ProfileBundle FG

    This object is an engine/data container.
    Display geometry should be built by Centerline3DDisplay.
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "Centerline3D"
        ensure_centerline3d_properties(obj)

    @staticmethod
    def _build_station_list(obj, total_len: float):
        values = [0.0, float(total_len)]

        use_stationing = bool(getattr(obj, "UseStationing", True))
        st_obj = getattr(obj, "Stationing", None)
        if use_stationing and st_obj is not None and hasattr(st_obj, "StationValues"):
            st_vals = [float(s) for s in (st_obj.StationValues or [])]
            values.extend(st_vals)
            values = [min(max(0.0, s), float(total_len)) for s in values]
            return _unique_sorted(values)

        interval = float(getattr(obj, "SamplingInterval", 5.0))
        if not math.isfinite(interval) or interval <= 1e-6:
            interval = 5.0 * get_length_scale(getattr(obj, "Document", None), default=1.0)
            obj.SamplingInterval = interval

        s = 0.0
        while s < total_len:
            values.append(float(s))
            s += interval

        values.append(float(total_len))
        return _unique_sorted(values)

    @staticmethod
    def _resolve_z_provider(obj):
        mode = str(getattr(obj, "ElevationSource", "Auto"))
        va = getattr(obj, "VerticalAlignment", None)
        bundle = getattr(obj, "ProfileBundle", None)

        if mode == "VerticalAlignment":
            if va is None:
                raise Exception("ElevationSource=VerticalAlignment but VerticalAlignment link is empty.")
            return "VerticalAlignment", lambda s: float(VerticalAlignment.elevation_at_station(va, float(s)))

        if mode == "ProfileBundleFG":
            if bundle is None:
                raise Exception("ElevationSource=ProfileBundleFG but ProfileBundle link is empty.")
            return "ProfileBundleFG", lambda s: float(_interp_bundle_fg(bundle, float(s)))

        if mode == "FlatZero":
            return "FlatZero", lambda _s: 0.0

        # Auto
        if va is not None:
            return "VerticalAlignment", lambda s: float(VerticalAlignment.elevation_at_station(va, float(s)))
        if bundle is not None and _build_bundle_pairs(bundle):
            return "ProfileBundleFG", lambda s: float(_interp_bundle_fg(bundle, float(s)))
        return "FlatZero", lambda _s: 0.0

    @staticmethod
    def point3d_at_station(obj, s: float, z_provider=None) -> App.Vector:
        aln = getattr(obj, "Alignment", None)
        if aln is None or aln.Shape is None or aln.Shape.isNull():
            raise Exception("Centerline3D.Alignment is missing or empty.")

        if z_provider is None:
            _, z_provider = Centerline3D._resolve_z_provider(obj)

        total = float(aln.Shape.Length)
        ss = float(s)
        if ss < 0.0:
            ss = 0.0
        if ss > total:
            ss = total

        p_xy = HorizontalAlignment.point_at_station(aln, ss)
        z = float(z_provider(ss))
        return App.Vector(float(p_xy.x), float(p_xy.y), z)

    @staticmethod
    def tangent3d_at_station(obj, s: float, eps: float = 0.1, z_provider=None) -> App.Vector:
        """
        3D tangent from central difference on resolved 3D centerline.
        """
        aln = getattr(obj, "Alignment", None)
        if aln is None or aln.Shape is None or aln.Shape.isNull():
            raise Exception("Centerline3D.Alignment is missing or empty.")

        total = float(aln.Shape.Length)
        if total <= 1e-9:
            return App.Vector(1.0, 0.0, 0.0)

        e = float(eps)
        if e <= 1e-6:
            e = 0.1
        if e > 0.25 * total:
            e = max(1e-3, 0.25 * total)

        s0 = max(0.0, float(s) - e)
        s1 = min(total, float(s) + e)
        if s1 <= s0 + 1e-9:
            s0 = max(0.0, float(s) - 0.5 * e)
            s1 = min(total, float(s) + 0.5 * e)

        p0 = Centerline3D.point3d_at_station(obj, s0, z_provider=z_provider)
        p1 = Centerline3D.point3d_at_station(obj, s1, z_provider=z_provider)
        t = p1 - p0
        if t.Length <= 1e-12:
            return App.Vector(1.0, 0.0, 0.0)
        return t.normalize()

    @staticmethod
    def frame_at_station(obj, s: float, eps: float = 0.1, prev_n: App.Vector = None, z_provider=None):
        """
        Standard section frame (T-N-Z):
          - T: tangent at station (3D)
          - Z: global up (0,0,1)
          - N: left normal, N = normalize(Z x T), with flip-stabilization via prev_n
        """
        p = Centerline3D.point3d_at_station(obj, float(s), z_provider=z_provider)
        t = Centerline3D.tangent3d_at_station(obj, float(s), eps=eps, z_provider=z_provider)
        z = App.Vector(0.0, 0.0, 1.0)
        n = z.cross(t)

        if n.Length <= 1e-12:
            if prev_n is not None and getattr(prev_n, "Length", 0.0) > 1e-12:
                n = prev_n
            else:
                n = App.Vector(0.0, 1.0, 0.0)
        else:
            n = n.normalize()

        # Keep left/right orientation continuity to reduce sudden flips.
        if prev_n is not None and getattr(prev_n, "Length", 0.0) > 1e-12:
            pn = prev_n.normalize()
            if float(n.dot(pn)) < 0.0:
                n = n * -1.0

        return {
            "point": p,
            "T": t,
            "N": n,
            "Z": z,
        }

    def execute(self, obj):
        ensure_centerline3d_properties(obj)
        try:
            aln = getattr(obj, "Alignment", None)
            if aln is None or aln.Shape is None or aln.Shape.isNull():
                obj.Shape = Part.Shape()
                obj.StationValues = []
                obj.CenterlinePoints = []
                obj.TotalLength3D = 0.0
                obj.ResolvedElevationSource = "N/A"
                obj.Status = "Missing Alignment"
                return

            total = float(aln.Shape.Length)
            if total <= 1e-9:
                obj.Shape = Part.Shape()
                obj.StationValues = []
                obj.CenterlinePoints = []
                obj.TotalLength3D = 0.0
                obj.ResolvedElevationSource = "N/A"
                obj.Status = "Alignment length is zero"
                return

            stations = self._build_station_list(obj, total)
            if len(stations) < 2:
                obj.Shape = Part.Shape()
                obj.StationValues = stations
                obj.CenterlinePoints = []
                obj.TotalLength3D = 0.0
                obj.ResolvedElevationSource = "N/A"
                obj.Status = "Insufficient stations"
                return

            source_name, z_provider = self._resolve_z_provider(obj)
            points = []
            for s in stations:
                points.append(Centerline3D.point3d_at_station(obj, float(s), z_provider=z_provider))

            if len(points) < 2:
                obj.Shape = Part.Shape()
                obj.StationValues = stations
                obj.CenterlinePoints = points
                obj.TotalLength3D = 0.0
                obj.ResolvedElevationSource = source_name
                obj.Status = "Insufficient sampled points"
                return

            # Engine object does not render centerline geometry.
            # Display is handled by Centerline3DDisplay.
            obj.Shape = Part.Shape()
            obj.StationValues = stations
            obj.CenterlinePoints = points
            total3d = 0.0
            for i in range(len(points) - 1):
                total3d += float((points[i + 1] - points[i]).Length)
            obj.TotalLength3D = float(total3d)
            obj.ResolvedElevationSource = source_name
            obj.Status = "OK"

        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.StationValues = []
            obj.CenterlinePoints = []
            obj.TotalLength3D = 0.0
            obj.ResolvedElevationSource = "N/A"
            obj.Status = f"ERROR: {ex}"

    def onChanged(self, obj, prop):
        if prop in (
            "Alignment",
            "Stationing",
            "VerticalAlignment",
            "ProfileBundle",
            "UseStationing",
            "SamplingInterval",
            "ElevationSource",
        ):
            try:
                obj.touch()
                if obj.Document is not None:
                    # Legacy compatibility: refresh display objects linked to this engine.
                    for o in list(obj.Document.Objects):
                        try:
                            if getattr(o, "SourceCenterline", None) == obj:
                                o.touch()
                        except Exception:
                            pass
            except Exception:
                pass


class ViewProviderCenterline3D:
    def __init__(self, vobj):
        vobj.Proxy = self
        self.Object = None

    def attach(self, vobj):
        self.Object = vobj.Object
        try:
            # Engine object is data-only, keep it hidden by default.
            vobj.Visibility = False
            vobj.DisplayMode = "Wireframe"
            vobj.LineWidth = 1
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
