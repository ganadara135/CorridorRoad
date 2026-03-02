# CorridorRoad/objects/obj_design_grading_surface.py
import FreeCAD as App
import Part

from objects.obj_section_set import SectionSet

_RECOMP_LABEL_SUFFIX = " [Recompute]"


def _is_finite(x: float) -> bool:
    try:
        import math

        return math.isfinite(float(x))
    except Exception:
        return False


def _dedupe_consecutive_points(points, tol: float = 1e-9):
    out = []
    for p in points:
        if not out:
            out.append(p)
            continue
        if (p - out[-1]).Length > tol:
            out.append(p)
    return out


def _mark_recompute_flag(obj, needed: bool):
    try:
        if hasattr(obj, "NeedsRecompute"):
            obj.NeedsRecompute = bool(needed)
    except Exception:
        pass

    try:
        label = str(getattr(obj, "Label", "") or "")
        if bool(needed):
            if _RECOMP_LABEL_SUFFIX not in label:
                obj.Label = f"{label}{_RECOMP_LABEL_SUFFIX}"
        else:
            if _RECOMP_LABEL_SUFFIX in label:
                obj.Label = label.replace(_RECOMP_LABEL_SUFFIX, "")
    except Exception:
        pass


def _mark_design_terrain_needs_recompute(obj_dep):
    try:
        if hasattr(obj_dep, "NeedsRecompute"):
            obj_dep.NeedsRecompute = True
    except Exception:
        pass
    try:
        st = str(getattr(obj_dep, "Status", "") or "")
        if "NEEDS_RECOMPUTE" not in st:
            obj_dep.Status = "NEEDS_RECOMPUTE: Source DesignGradingSurface changed."
    except Exception:
        pass
    try:
        label = str(getattr(obj_dep, "Label", "") or "")
        if _RECOMP_LABEL_SUFFIX not in label:
            obj_dep.Label = f"{label}{_RECOMP_LABEL_SUFFIX}"
    except Exception:
        pass


def ensure_design_grading_surface_properties(obj):
    if not hasattr(obj, "SourceSectionSet"):
        obj.addProperty("App::PropertyLink", "SourceSectionSet", "DesignSurface", "SectionSet source")

    if not hasattr(obj, "AutoUpdate"):
        obj.addProperty("App::PropertyBool", "AutoUpdate", "DesignSurface", "Auto update from source changes")
        obj.AutoUpdate = True

    if not hasattr(obj, "RebuildNow"):
        obj.addProperty("App::PropertyBool", "RebuildNow", "DesignSurface", "Set True to force rebuild now")
        obj.RebuildNow = False

    if not hasattr(obj, "NeedsRecompute"):
        obj.addProperty("App::PropertyBool", "NeedsRecompute", "Result", "Marked when source updates require recompute")
        obj.NeedsRecompute = False

    if not hasattr(obj, "SectionCount"):
        obj.addProperty("App::PropertyInteger", "SectionCount", "Result", "Used section count")
        obj.SectionCount = 0

    if not hasattr(obj, "PointCountPerSection"):
        obj.addProperty("App::PropertyInteger", "PointCountPerSection", "Result", "Point count per section")
        obj.PointCountPerSection = 0

    if not hasattr(obj, "FaceCount"):
        obj.addProperty("App::PropertyInteger", "FaceCount", "Result", "Generated face count")
        obj.FaceCount = 0

    if not hasattr(obj, "SchemaVersion"):
        obj.addProperty("App::PropertyInteger", "SchemaVersion", "Result", "Section schema version used")
        obj.SchemaVersion = 0

    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"


class DesignGradingSurface:
    """
    Design grading surface (road + side slopes) generated from SectionSet wires.
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "DesignGradingSurface"
        ensure_design_grading_surface_properties(obj)

    @staticmethod
    def _wire_points(wire):
        edges = list(getattr(wire, "Edges", []) or [])
        if not edges:
            return []
        pts = [edges[0].valueAt(edges[0].FirstParameter)]
        for e in edges:
            pts.append(e.valueAt(e.LastParameter))
        return _dedupe_consecutive_points(pts)

    @staticmethod
    def _validate_and_points(stations, wires):
        if len(stations) < 2 or len(wires) < 2:
            raise Exception("Need at least 2 sections to build design surface.")
        if len(stations) != len(wires):
            raise Exception("Stations/wires size mismatch.")

        st = [float(s) for s in stations]
        for i, s in enumerate(st):
            if not _is_finite(s):
                raise Exception(f"Station[{i}] is not finite.")
            if i >= 1 and s <= st[i - 1] + 1e-9:
                raise Exception("Station values must be strictly increasing.")

        pt_lists = []
        ref_n = None
        for i, w in enumerate(wires):
            pts = DesignGradingSurface._wire_points(w)
            if len(pts) < 2:
                raise Exception(f"Section[{i}] has insufficient points.")
            if ref_n is None:
                ref_n = len(pts)
            elif len(pts) != ref_n:
                raise Exception(
                    f"Section point count mismatch at index {i}: {len(pts)} != {ref_n}. "
                    "Design surface stopped by section contract."
                )
            pt_lists.append(pts)

        # Orientation continuity guard (same policy as corridor loft):
        # reverse section point order if left/right axis flips.
        out = []
        prev_axis = None
        for i, pts in enumerate(pt_lists):
            axis = pts[0] - pts[-1]
            if axis.Length <= 1e-12:
                raise Exception(f"Section[{i}] left/right axis is degenerate.")
            if prev_axis is not None and float(axis.dot(prev_axis)) < 0.0:
                pts = list(reversed(pts))
                axis = pts[0] - pts[-1]
            prev_axis = axis
            out.append(pts)

        return out, int(ref_n or 0)

    @staticmethod
    def _build_ruled_faces(pt_lists):
        faces = []
        for i in range(len(pt_lists) - 1):
            a = pt_lists[i]
            b = pt_lists[i + 1]
            for j in range(len(a) - 1):
                e0 = Part.makeLine(a[j], a[j + 1])
                e1 = Part.makeLine(b[j], b[j + 1])
                try:
                    f = Part.makeRuledSurface(e0, e1)
                    if f is not None and (not f.isNull()):
                        faces.append(f)
                except Exception:
                    # Keep generation robust even with local degeneracy.
                    continue
        return faces

    def execute(self, obj):
        ensure_design_grading_surface_properties(obj)
        try:
            src = getattr(obj, "SourceSectionSet", None)
            if src is None:
                obj.Shape = Part.Shape()
                obj.SectionCount = 0
                obj.PointCountPerSection = 0
                obj.FaceCount = 0
                obj.SchemaVersion = 0
                obj.Status = "Missing SourceSectionSet"
                _mark_recompute_flag(obj, False)
                return

            stations, wires, _tf, _so = SectionSet.build_section_wires(src)
            pts, pt_count = DesignGradingSurface._validate_and_points(stations, wires)
            faces = DesignGradingSurface._build_ruled_faces(pts)
            if not faces:
                raise Exception("No valid ruled faces were generated.")

            obj.Shape = Part.Compound(faces)
            obj.SectionCount = int(len(stations))
            obj.PointCountPerSection = int(pt_count)
            obj.FaceCount = int(len(faces))
            obj.SchemaVersion = int(getattr(src, "SectionSchemaVersion", 0))
            obj.Status = "OK (Surface)"
            _mark_recompute_flag(obj, False)

            # Push updates to linked DesignTerrain objects as pending recompute.
            if obj.Document is not None:
                for o in list(obj.Document.Objects):
                    try:
                        if getattr(o, "SourceDesignSurface", None) == obj and bool(getattr(o, "AutoUpdate", True)):
                            _mark_design_terrain_needs_recompute(o)
                    except Exception:
                        pass

            if bool(getattr(obj, "RebuildNow", False)):
                obj.RebuildNow = False

        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.SectionCount = 0
            obj.PointCountPerSection = 0
            obj.FaceCount = 0
            obj.SchemaVersion = 0
            obj.Status = f"ERROR: {ex}"
            _mark_recompute_flag(obj, False)

    def onChanged(self, obj, prop):
        if prop in (
            "SourceSectionSet",
            "AutoUpdate",
            "RebuildNow",
        ):
            try:
                if prop == "RebuildNow":
                    if not bool(getattr(obj, "RebuildNow", False)):
                        return
                elif not bool(getattr(obj, "AutoUpdate", True)):
                    try:
                        obj.Status = "NEEDS_RECOMPUTE: source/parameters changed"
                    except Exception:
                        pass
                    return

                obj.touch()
                if obj.Document is not None:
                    obj.Document.recompute()
            except Exception:
                pass


class ViewProviderDesignGradingSurface:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Shaded"
            vobj.Transparency = 20
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
        return ["Wireframe", "Flat Lines", "Shaded"]

    def getDefaultDisplayMode(self):
        return "Shaded"

    def setDisplayMode(self, mode):
        return mode
