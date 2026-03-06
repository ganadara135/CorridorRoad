# CorridorRoad/objects/obj_corridor_loft.py
import math

import FreeCAD as App
import Part

from objects.obj_section_set import SectionSet
from objects.obj_project import get_length_scale

_RECOMP_LABEL_SUFFIX = " [Recompute]"


def _is_finite(x: float) -> bool:
    return math.isfinite(float(x))


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


def ensure_corridor_loft_properties(obj):
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)

    # Hard-remove legacy thickness properties.
    for legacy_prop in ("PavementThickness", "SolidThickness", "ResolvedPavementThickness"):
        try:
            if hasattr(obj, legacy_prop):
                obj.removeProperty(legacy_prop)
        except Exception:
            pass

    if not hasattr(obj, "SourceSectionSet"):
        obj.addProperty("App::PropertyLink", "SourceSectionSet", "Corridor", "SectionSet source")

    if not hasattr(obj, "OutputType"):
        obj.addProperty("App::PropertyEnumeration", "OutputType", "Corridor", "Output type")
    # Solid-only policy.
    try:
        obj.OutputType = ["Solid"]
        obj.OutputType = "Solid"
    except Exception:
        pass

    if not hasattr(obj, "HeightLeft"):
        obj.addProperty("App::PropertyFloat", "HeightLeft", "Corridor", "Fallback left depth (m, downward)")
        obj.HeightLeft = 0.30

    if not hasattr(obj, "HeightRight"):
        obj.addProperty("App::PropertyFloat", "HeightRight", "Corridor", "Fallback right depth (m, downward)")
        obj.HeightRight = 0.30

    if not hasattr(obj, "UseRuled"):
        obj.addProperty("App::PropertyBool", "UseRuled", "Corridor", "Use ruled loft")
        obj.UseRuled = False

    if not hasattr(obj, "MinSectionSpacing"):
        obj.addProperty("App::PropertyFloat", "MinSectionSpacing", "Corridor", "Minimum station spacing for loft input (m)")
        obj.MinSectionSpacing = 0.50 * scale

    if not hasattr(obj, "AutoUpdate"):
        obj.addProperty("App::PropertyBool", "AutoUpdate", "Corridor", "Auto update from source changes")
        obj.AutoUpdate = True

    if not hasattr(obj, "RebuildNow"):
        obj.addProperty("App::PropertyBool", "RebuildNow", "Corridor", "Set True to force rebuild now")
        obj.RebuildNow = False

    if not hasattr(obj, "SectionCount"):
        obj.addProperty("App::PropertyInteger", "SectionCount", "Result", "Used section count")
        obj.SectionCount = 0

    if not hasattr(obj, "PointCountPerSection"):
        obj.addProperty("App::PropertyInteger", "PointCountPerSection", "Result", "Point count per section")
        obj.PointCountPerSection = 0

    if not hasattr(obj, "SchemaVersion"):
        obj.addProperty("App::PropertyInteger", "SchemaVersion", "Result", "Section schema version used")
        obj.SchemaVersion = 0

    if not hasattr(obj, "FailedRanges"):
        obj.addProperty("App::PropertyStringList", "FailedRanges", "Result", "Failed ranges during segmented fallback")
        obj.FailedRanges = []

    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"

    if not hasattr(obj, "NeedsRecompute"):
        obj.addProperty("App::PropertyBool", "NeedsRecompute", "Result", "Marked when source updates require recompute")
        obj.NeedsRecompute = False

    if not hasattr(obj, "ResolvedHeightLeft"):
        obj.addProperty("App::PropertyFloat", "ResolvedHeightLeft", "Result", "Resolved left depth used for solid")
        obj.ResolvedHeightLeft = 0.0

    if not hasattr(obj, "ResolvedHeightRight"):
        obj.addProperty("App::PropertyFloat", "ResolvedHeightRight", "Result", "Resolved right depth used for solid")
        obj.ResolvedHeightRight = 0.0

    try:
        if hasattr(obj, "OutputType"):
            obj.setEditorMode("OutputType", 2)
    except Exception:
        pass


class CorridorLoft:
    """
    Corridor loft from SectionSet (Solid-only).
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "CorridorLoft"
        ensure_corridor_loft_properties(obj)

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
    def _make_wire(points):
        return Part.makePolygon(points)

    @staticmethod
    def _validate_and_normalize(stations, wires, schema_version: int):
        if len(stations) < 2 or len(wires) < 2:
            raise Exception("Need at least 2 sections for loft.")
        if len(stations) != len(wires):
            raise Exception("Stations/wires size mismatch.")

        st = [float(s) for s in stations]
        for i, s in enumerate(st):
            if not _is_finite(s):
                raise Exception(f"Station[{i}] is not finite.")
            if i >= 1 and s <= st[i - 1] + 1e-9:
                raise Exception("Station values must be strictly increasing.")

        pt_lists = []
        for i, w in enumerate(wires):
            pts = CorridorLoft._wire_points(w)
            if len(pts) < 2:
                raise Exception(f"Section[{i}] has insufficient points.")
            for j, p in enumerate(pts):
                if not (_is_finite(p.x) and _is_finite(p.y) and _is_finite(p.z)):
                    raise Exception(f"Section[{i}] point[{j}] is not finite.")
            for j in range(len(pts) - 1):
                if (pts[j + 1] - pts[j]).Length <= 1e-12:
                    raise Exception(f"Section[{i}] has duplicate critical points.")
            pt_lists.append(pts)

        ref_n = len(pt_lists[0])
        for i, pts in enumerate(pt_lists):
            if len(pts) != ref_n:
                raise Exception(
                    f"Section point count mismatch at index {i}: {len(pts)} != {ref_n}. "
                    "Loft stopped by section contract."
                )

        if int(schema_version) == 1 and ref_n != 3:
            raise Exception(
                f"SchemaVersion=1 requires 3 points (Left->Center->Right), but got {ref_n}."
            )

        # SectionSet.build_section_wires already stabilizes N-direction with prev_n.
        # Keep source point order as-is; additional auto-flip here can mis-detect
        # normal heading rotation as a true left/right inversion.
        out_wires = []
        for i, pts in enumerate(pt_lists):
            axis = pts[0] - pts[-1]
            if axis.Length <= 1e-12:
                raise Exception(f"Section[{i}] left/right axis is degenerate.")
            out_wires.append(CorridorLoft._make_wire(pts))

        return out_wires, ref_n

    @staticmethod
    def _filter_close_sections(stations, wires, min_spacing: float):
        if len(stations) != len(wires):
            raise Exception("Stations/wires size mismatch.")
        if len(stations) <= 2:
            return list(stations), list(wires), 0

        dmin = max(0.0, float(min_spacing))
        if dmin <= 1e-9:
            return list(stations), list(wires), 0

        out_st = [float(stations[0])]
        out_wr = [wires[0]]
        dropped = 0

        for i in range(1, len(stations)):
            s = float(stations[i])
            if (s - float(out_st[-1])) < dmin:
                dropped += 1
                continue
            out_st.append(s)
            out_wr.append(wires[i])

        # Keep at least 2 sections for loft contract.
        if len(out_st) < 2 and len(stations) >= 2:
            return [float(stations[0]), float(stations[-1])], [wires[0], wires[-1]], max(0, len(stations) - 2)
        return out_st, out_wr, dropped

    @staticmethod
    def _valid_heights(h_left: float, h_right: float):
        if not (_is_finite(h_left) and _is_finite(h_right)):
            return False
        if h_left < -1e-9 or h_right < -1e-9:
            return False
        return max(float(h_left), float(h_right)) > 1e-6

    @staticmethod
    def _make_closed_profiles_for_solid(open_wires, h_left: float, h_right: float):
        hl = float(h_left)
        hr = float(h_right)
        if not CorridorLoft._valid_heights(hl, hr):
            raise Exception("HeightLeft/HeightRight must be finite, non-negative, and at least one > 0.")

        closed = []
        for i, w in enumerate(open_wires):
            up = CorridorLoft._wire_points(w)
            if len(up) < 2:
                raise Exception(f"Section[{i}] has insufficient points for solid profile.")

            n = len(up)
            dn = []
            for j, p in enumerate(up):
                alpha = float(j) / float(n - 1) if n > 1 else 0.5
                h = (1.0 - alpha) * hl + alpha * hr
                dn.append(App.Vector(p.x, p.y, p.z - h))

            poly = list(up) + list(reversed(dn))
            poly.append(poly[0])
            closed.append(Part.makePolygon(poly))
        return closed

    @staticmethod
    def _resolve_heights(obj, src):
        asm = getattr(src, "AssemblyTemplate", None) if src is not None else None
        if asm is not None:
            try:
                hl = float(getattr(asm, "HeightLeft"))
                hr = float(getattr(asm, "HeightRight"))
                if CorridorLoft._valid_heights(hl, hr):
                    return hl, hr, "AssemblyTemplate.HeightLeft/HeightRight"
            except Exception:
                pass

        try:
            hl = float(getattr(obj, "HeightLeft"))
            hr = float(getattr(obj, "HeightRight"))
            if CorridorLoft._valid_heights(hl, hr):
                return hl, hr, "CorridorLoft.HeightLeft/HeightRight"
        except Exception:
            pass

        raise Exception("Valid HeightLeft/HeightRight are required for Solid output.")

    @staticmethod
    def _loft(wires, ruled: bool, solid: bool = True):
        return Part.makeLoft(wires, bool(solid), bool(ruled), False)

    @staticmethod
    def _loft_adaptive(wires, stations, ruled: bool, solid: bool = True):
        parts = []
        failed = []

        def _run(i0: int, i1: int):
            try:
                seg = CorridorLoft._loft(wires[i0 : i1 + 1], ruled=ruled, solid=solid)
                parts.append((i0, seg))
            except Exception as ex:
                if (i1 - i0) <= 1:
                    failed.append(f"{float(stations[i0]):.3f}-{float(stations[i1]):.3f}: {ex}")
                    return
                mid = (i0 + i1) // 2
                if mid <= i0 or mid >= i1:
                    failed.append(f"{float(stations[i0]):.3f}-{float(stations[i1]):.3f}: {ex}")
                    return
                _run(i0, mid)
                _run(mid, i1)

        _run(0, len(wires) - 1)

        if not parts:
            raise Exception("Adaptive segmented loft failed for all ranges.")

        parts.sort(key=lambda it: int(it[0]))
        shapes = [it[1] for it in parts]
        shape = shapes[0] if len(shapes) == 1 else Part.Compound(shapes)
        return shape, failed

    def execute(self, obj):
        ensure_corridor_loft_properties(obj)
        try:
            src = getattr(obj, "SourceSectionSet", None)
            if src is None:
                obj.Shape = Part.Shape()
                obj.SectionCount = 0
                obj.PointCountPerSection = 0
                obj.SchemaVersion = 0
                obj.FailedRanges = []
                obj.ResolvedHeightLeft = 0.0
                obj.ResolvedHeightRight = 0.0
                obj.Status = "Missing SourceSectionSet"
                _mark_recompute_flag(obj, False)
                return

            stations, wires, _tf, _so = SectionSet.build_section_wires(src)
            min_spacing = max(0.0, float(getattr(obj, "MinSectionSpacing", 0.0)))
            stations, wires, dropped = CorridorLoft._filter_close_sections(stations, wires, min_spacing)
            schema = int(getattr(src, "SectionSchemaVersion", 1))

            norm_wires, pt_count = CorridorLoft._validate_and_normalize(stations, wires, schema)
            ruled = bool(getattr(obj, "UseRuled", False))
            h_left, h_right, height_source = CorridorLoft._resolve_heights(obj, src)
            loft_wires = CorridorLoft._make_closed_profiles_for_solid(norm_wires, h_left, h_right)

            failed_ranges = []
            try:
                shape = CorridorLoft._loft(loft_wires, ruled=ruled, solid=True)
                status = (
                    "OK (Solid) "
                    f"hL={float(h_left):.3f}m hR={float(h_right):.3f}m from {height_source} | "
                    f"minSpacing={float(min_spacing):.3f} used={len(stations)} dropped={int(dropped)}"
                )
            except Exception as ex:
                shape, failed_ranges = CorridorLoft._loft_adaptive(
                    loft_wires, stations, ruled=ruled, solid=True
                )
                status = (
                    "WARN (Solid): full loft failed, adaptive fallback used "
                    f"({len(failed_ranges)} failed ranges): {ex} | "
                    f"hL={float(h_left):.3f}m hR={float(h_right):.3f}m from {height_source} | "
                    f"minSpacing={float(min_spacing):.3f} used={len(stations)} dropped={int(dropped)}"
                )

            obj.Shape = shape
            obj.SectionCount = len(stations)
            obj.PointCountPerSection = int(pt_count)
            obj.SchemaVersion = int(schema)
            obj.FailedRanges = list(failed_ranges)
            obj.ResolvedHeightLeft = float(h_left)
            obj.ResolvedHeightRight = float(h_right)
            obj.Status = status
            _mark_recompute_flag(obj, False)

            if bool(getattr(obj, "RebuildNow", False)):
                obj.RebuildNow = False

        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.SectionCount = 0
            obj.PointCountPerSection = 0
            obj.SchemaVersion = 0
            obj.FailedRanges = []
            obj.ResolvedHeightLeft = 0.0
            obj.ResolvedHeightRight = 0.0
            obj.Status = f"ERROR: {ex}"
            _mark_recompute_flag(obj, False)

    def onChanged(self, obj, prop):
        if prop in (
            "SourceSectionSet",
            "OutputType",
            "HeightLeft",
            "HeightRight",
            "UseRuled",
            "MinSectionSpacing",
            "AutoUpdate",
            "RebuildNow",
        ):
            try:
                obj.touch()
                # Avoid forced recompute on every property-editor keystroke.
                # FreeCAD will recompute on confirmed edit; only force when user
                # explicitly requests rebuild.
                if prop == "RebuildNow" and bool(getattr(obj, "RebuildNow", False)):
                    if obj.Document is not None:
                        obj.Document.recompute()
            except Exception:
                pass


class ViewProviderCorridorLoft:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Flat Lines"
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
        return ["Wireframe", "Flat Lines", "Shaded"]

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def setDisplayMode(self, mode):
        return mode
