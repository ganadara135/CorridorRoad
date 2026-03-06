# CorridorRoad/objects/obj_centerline3d_display.py
import FreeCAD as App
import Part

from objects.obj_centerline3d import Centerline3D
from objects.obj_project import get_length_scale
from objects.obj_vertical_alignment import VerticalAlignment


def _unique_sorted(values, tol: float = 1e-6):
    vals = sorted([float(v) for v in values])
    out = []
    for v in vals:
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def _alignment_edge_boundaries(aln):
    if aln is None or aln.Shape is None or aln.Shape.isNull():
        return []

    vals = [0.0]
    acc = 0.0
    for e in list(aln.Shape.Edges):
        acc += float(e.Length)
        vals.append(float(acc))
    return vals


def _vertical_key_stations(va):
    if va is None:
        return []

    vals = []
    try:
        pvis, _grades, curves = VerticalAlignment._solve_curves(va)
        if pvis:
            vals.append(float(pvis[0][0]))
            vals.append(float(pvis[-1][0]))
        for c in curves:
            vals.append(float(c["bvc"]))
            vals.append(float(c["evc"]))
    except Exception:
        return []
    return vals


def ensure_centerline3d_display_properties(obj):
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)

    # Optional legacy link: if provided, display can read source data from engine object.
    if not hasattr(obj, "SourceCenterline"):
        obj.addProperty("App::PropertyLink", "SourceCenterline", "Display", "Centerline3D engine source")

    # Direct source mode (preferred): display can resolve geometry/elevation on its own.
    if not hasattr(obj, "Alignment"):
        obj.addProperty("App::PropertyLink", "Alignment", "Source", "HorizontalAlignment link")
    if not hasattr(obj, "Stationing"):
        obj.addProperty("App::PropertyLink", "Stationing", "Source", "Stationing link (optional)")
    if not hasattr(obj, "VerticalAlignment"):
        obj.addProperty("App::PropertyLink", "VerticalAlignment", "Source", "VerticalAlignment link (optional)")
    if not hasattr(obj, "ProfileBundle"):
        obj.addProperty("App::PropertyLink", "ProfileBundle", "Source", "ProfileBundle link (optional)")

    if not hasattr(obj, "UseStationing"):
        obj.addProperty("App::PropertyBool", "UseStationing", "Source", "Use Stationing.StationValues when available")
        obj.UseStationing = True

    if not hasattr(obj, "SamplingInterval"):
        obj.addProperty("App::PropertyFloat", "SamplingInterval", "Sampling", "Sampling interval (m) when Stationing is not used")
        obj.SamplingInterval = 5.0 * scale
    else:
        # Migrate older objects where SamplingInterval was under "Source"
        try:
            obj.setGroupOfProperty("SamplingInterval", "Sampling")
        except Exception:
            pass

    if not hasattr(obj, "ElevationSource"):
        obj.addProperty("App::PropertyEnumeration", "ElevationSource", "Source", "Elevation source mode")
        obj.ElevationSource = ["Auto", "VerticalAlignment", "ProfileBundleFG", "FlatZero"]
        obj.ElevationSource = "Auto"

    if not hasattr(obj, "ShowWire"):
        obj.addProperty("App::PropertyBool", "ShowWire", "Display", "Show 3D centerline wire")
        obj.ShowWire = True

    if not hasattr(obj, "MaxChordError"):
        obj.addProperty("App::PropertyFloat", "MaxChordError", "Sampling", "Maximum chord error for adaptive sampling (m)")
        obj.MaxChordError = 0.02 * scale

    if not hasattr(obj, "MinStep"):
        obj.addProperty("App::PropertyFloat", "MinStep", "Sampling", "Minimum station step for adaptive sampling (m)")
        obj.MinStep = 0.5 * scale

    if not hasattr(obj, "MaxStep"):
        obj.addProperty("App::PropertyFloat", "MaxStep", "Sampling", "Maximum station step for adaptive sampling (m)")
        obj.MaxStep = 10.0 * scale

    if not hasattr(obj, "UseKeyStations"):
        obj.addProperty("App::PropertyBool", "UseKeyStations", "Sampling", "Always include key stations (edge bounds, BVC/EVC)")
        obj.UseKeyStations = True

    if not hasattr(obj, "SampledStations"):
        obj.addProperty("App::PropertyFloatList", "SampledStations", "Result", "Adaptive sampled station values (m)")
    if not hasattr(obj, "SampledPoints"):
        obj.addProperty("App::PropertyVectorList", "SampledPoints", "Result", "Adaptive sampled 3D points")
    if not hasattr(obj, "SampleCount"):
        obj.addProperty("App::PropertyInteger", "SampleCount", "Result", "Sample point count")
        obj.SampleCount = 0

    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Display generation status")
        obj.Status = "Idle"
    if not hasattr(obj, "ResolvedElevationSource"):
        obj.addProperty("App::PropertyString", "ResolvedElevationSource", "Result", "Resolved elevation source used at runtime")
        obj.ResolvedElevationSource = "N/A"


class Centerline3DDisplay:
    """
    Display-only object for Centerline3D.
    Uses adaptive sampling to represent curved 3D geometry.
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "Centerline3DDisplay"
        ensure_centerline3d_display_properties(obj)

    @staticmethod
    def _safe_sampling_params(obj):
        scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
        max_err = float(getattr(obj, "MaxChordError", 0.02 * scale))
        if max_err < 1e-6 * scale:
            max_err = 1e-6 * scale
            obj.MaxChordError = max_err

        min_step = float(getattr(obj, "MinStep", 0.5 * scale))
        if min_step < 1e-3 * scale:
            min_step = 1e-3 * scale
            obj.MinStep = min_step

        max_step = float(getattr(obj, "MaxStep", 10.0 * scale))
        if max_step < min_step:
            max_step = min_step
            obj.MaxStep = max_step

        return max_err, min_step, max_step

    @staticmethod
    def _base_station_seeds(src_obj, total_len: float):
        vals = [0.0, float(total_len)]

        # Include engine prepared stations.
        vals.extend(list(getattr(src_obj, "StationValues", []) or []))

        # Include geometry boundaries and vertical keys for stable joins.
        if bool(getattr(src_obj, "UseStationing", True)):
            st_obj = getattr(src_obj, "Stationing", None)
            if st_obj is not None and hasattr(st_obj, "StationValues"):
                vals.extend(list(st_obj.StationValues or []))

        aln = getattr(src_obj, "Alignment", None)
        if aln is not None:
            vals.extend(_alignment_edge_boundaries(aln))

        vals.extend(_vertical_key_stations(getattr(src_obj, "VerticalAlignment", None)))

        vals = [min(max(0.0, float(v)), float(total_len)) for v in vals]
        return _unique_sorted(vals)

    @staticmethod
    def _midpoint_dev(src_obj, z_provider, s0: float, s1: float):
        p0 = Centerline3D.point3d_at_station(src_obj, float(s0), z_provider=z_provider)
        p1 = Centerline3D.point3d_at_station(src_obj, float(s1), z_provider=z_provider)
        sm = 0.5 * (float(s0) + float(s1))
        pm = Centerline3D.point3d_at_station(src_obj, float(sm), z_provider=z_provider)

        chord_mid = p0 + (p1 - p0) * 0.5
        return float((pm - chord_mid).Length), float(sm)

    @staticmethod
    def _append_adaptive(src_obj, z_provider, out_stations, s0: float, s1: float, max_err: float, min_step: float, max_step: float, depth: int):
        ds = float(s1 - s0)
        if ds <= min_step + 1e-9:
            out_stations.append(float(s1))
            return

        need_split = False
        if ds > max_step + 1e-9:
            need_split = True
            sm = 0.5 * (float(s0) + float(s1))
        else:
            dev, sm = Centerline3DDisplay._midpoint_dev(src_obj, z_provider, s0, s1)
            if dev > max_err:
                need_split = True

        if need_split and depth < 32:
            Centerline3DDisplay._append_adaptive(src_obj, z_provider, out_stations, s0, sm, max_err, min_step, max_step, depth + 1)
            Centerline3DDisplay._append_adaptive(src_obj, z_provider, out_stations, sm, s1, max_err, min_step, max_step, depth + 1)
            return

        out_stations.append(float(s1))

    def execute(self, obj):
        ensure_centerline3d_display_properties(obj)
        try:
            if not bool(getattr(obj, "ShowWire", True)):
                obj.Shape = Part.Shape()
                obj.SampledStations = []
                obj.SampledPoints = []
                obj.SampleCount = 0
                obj.Status = "Hidden"
                return

            src = getattr(obj, "SourceCenterline", None)
            if src is None:
                # Preferred mode: display uses its own source links/sampling properties.
                src = obj

            aln = getattr(src, "Alignment", None)
            if aln is None or aln.Shape is None or aln.Shape.isNull():
                obj.Shape = Part.Shape()
                obj.SampledStations = []
                obj.SampledPoints = []
                obj.SampleCount = 0
                obj.Status = "Source alignment is missing"
                obj.ResolvedElevationSource = "N/A"
                return

            total = float(aln.Shape.Length)
            if total <= 1e-9:
                obj.Shape = Part.Shape()
                obj.SampledStations = []
                obj.SampledPoints = []
                obj.SampleCount = 0
                obj.Status = "Source alignment length is zero"
                obj.ResolvedElevationSource = "N/A"
                return

            source_name, z_provider = Centerline3D._resolve_z_provider(src)
            max_err, min_step, max_step = Centerline3DDisplay._safe_sampling_params(obj)

            if bool(getattr(obj, "UseKeyStations", True)):
                seeds = Centerline3DDisplay._base_station_seeds(src, total)
            else:
                seeds = [0.0, float(total)]

            if len(seeds) < 2:
                seeds = [0.0, float(total)]

            sampled = [float(seeds[0])]
            for i in range(len(seeds) - 1):
                s0 = float(seeds[i])
                s1 = float(seeds[i + 1])
                if s1 <= s0 + 1e-9:
                    continue
                Centerline3DDisplay._append_adaptive(
                    src, z_provider, sampled, s0, s1,
                    max_err=max_err, min_step=min_step, max_step=max_step, depth=0
                )

            sampled = _unique_sorted(sampled)
            points = [Centerline3D.point3d_at_station(src, s, z_provider=z_provider) for s in sampled]
            if len(points) < 2:
                obj.Shape = Part.Shape()
                obj.SampledStations = sampled
                obj.SampledPoints = points
                obj.SampleCount = len(points)
                obj.Status = "Insufficient sampled points"
                obj.ResolvedElevationSource = source_name
                return

            obj.Shape = Part.makePolygon(points)
            obj.SampledStations = sampled
            obj.SampledPoints = points
            obj.SampleCount = len(points)
            obj.Status = "OK"
            obj.ResolvedElevationSource = source_name

        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.SampledStations = []
            obj.SampledPoints = []
            obj.SampleCount = 0
            obj.Status = f"ERROR: {ex}"
            obj.ResolvedElevationSource = "N/A"

    def onChanged(self, obj, prop):
        if prop in (
            "SourceCenterline",
            "Alignment",
            "Stationing",
            "VerticalAlignment",
            "ProfileBundle",
            "UseStationing",
            "SamplingInterval",
            "ElevationSource",
            "ShowWire",
            "MaxChordError",
            "MinStep",
            "MaxStep",
            "UseKeyStations",
        ):
            try:
                obj.touch()
                try:
                    import FreeCADGui as Gui
                    Gui.updateGui()
                except Exception:
                    pass
            except Exception:
                pass


class ViewProviderCenterline3DDisplay:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Wireframe"
            vobj.LineWidth = 3
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
