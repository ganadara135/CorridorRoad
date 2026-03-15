import math

import FreeCAD as App

try:
    import Part
except Exception:
    Part = None

from freecad.Corridor_Road.objects.doc_query import find_first, find_project
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_centerline3d import Centerline3D


ALLOWED_TYPES = (
    "crossing",
    "culvert",
    "retaining_wall",
    "bridge_zone",
    "abutment_zone",
    "other",
)
ALLOWED_SIDES = ("left", "right", "center", "both")
ALLOWED_BEHAVIOR_MODES = ("tag_only", "section_overlay", "assembly_override")


def _empty_shape():
    if Part is None:
        return None
    try:
        return Part.Shape()
    except Exception:
        return None


def _safe_vec(v, fallback):
    try:
        if getattr(v, "Length", 0.0) > 1e-9:
            return v.normalize()
    except Exception:
        pass
    return App.Vector(fallback.x, fallback.y, fallback.z)


def _resolve_alignment(obj):
    doc = getattr(obj, "Document", None)
    prj = find_project(doc)
    if prj is not None:
        st = getattr(prj, "Stationing", None)
        if st is not None:
            aln = getattr(st, "Alignment", None)
            if aln is not None:
                return aln
        aln = getattr(prj, "Alignment", None)
        if aln is not None:
            return aln
    return find_first(doc, proxy_type="HorizontalAlignment", name_prefixes=("HorizontalAlignment",))


def _resolve_centerline_source(obj):
    doc = getattr(obj, "Document", None)
    prj = find_project(doc)
    if prj is not None:
        src = getattr(prj, "Centerline3DDisplay", None)
        if src is not None and getattr(src, "Alignment", None) is not None:
            return src
        src = getattr(prj, "Centerline3D", None)
        if src is not None and getattr(src, "Alignment", None) is not None:
            return src
    src = find_first(doc, proxy_type="Centerline3DDisplay", name_prefixes=("Centerline3DDisplay",))
    if src is not None and getattr(src, "Alignment", None) is not None:
        return src
    src = find_first(doc, proxy_type="Centerline3D", name_prefixes=("Centerline3D",))
    if src is not None and getattr(src, "Alignment", None) is not None:
        return src
    return None


def _resolve_station_point(obj, station: float, aln=None):
    src3d = _resolve_centerline_source(obj)
    if src3d is not None:
        try:
            return Centerline3D.point3d_at_station(src3d, float(station))
        except Exception:
            pass
    if aln is None:
        aln = _resolve_alignment(obj)
    if aln is not None:
        try:
            return HorizontalAlignment.point_at_station(aln, float(station))
        except Exception:
            pass
    return App.Vector(0.0, 0.0, 0.0)


def _station_for_record(rec):
    sc = float(rec.get("CenterStation", 0.0) or 0.0)
    s0 = float(rec.get("StartStation", 0.0) or 0.0)
    s1 = float(rec.get("EndStation", 0.0) or 0.0)
    if sc > 0.0:
        return sc
    if s1 > s0:
        return 0.5 * (s0 + s1)
    return s0


def _side_offsets(rec):
    side = str(rec.get("Side", "") or "").strip().lower()
    off = float(rec.get("Offset", 0.0) or 0.0)
    width = abs(float(rec.get("Width", 0.0) or 0.0))
    sep = max(abs(off), 0.5 * width, 0.5)
    if side == "left":
        return [off if abs(off) > 1e-9 else sep]
    if side == "right":
        return [off if abs(off) > 1e-9 else -sep]
    if side == "both":
        return [-sep, sep]
    return [off]


def _build_structure_solid(base_pt, tangent, normal, rec):
    if Part is None:
        return None
    length = abs(float(rec.get("EndStation", 0.0) or 0.0) - float(rec.get("StartStation", 0.0) or 0.0))
    width = abs(float(rec.get("Width", 0.0) or 0.0))
    height = abs(float(rec.get("Height", 0.0) or 0.0))
    rot = math.radians(float(rec.get("RotationDeg", 0.0) or 0.0))

    length = max(length, 1.0)
    width = max(width, 1.0)
    height = max(height, 1.0)

    t = _safe_vec(tangent, App.Vector(1, 0, 0))
    n = _safe_vec(normal, App.Vector(0, 1, 0))
    if abs(rot) > 1e-12:
        t0 = App.Vector(t.x, t.y, t.z)
        n0 = App.Vector(n.x, n.y, n.z)
        cs = math.cos(rot)
        sn = math.sin(rot)
        t = _safe_vec((t0 * cs) + (n0 * sn), App.Vector(1, 0, 0))
        n = _safe_vec((n0 * cs) - (t0 * sn), App.Vector(0, 1, 0))

    z0_raw = float(rec.get("BottomElevation", 0.0) or 0.0)
    cover = abs(float(rec.get("Cover", 0.0) or 0.0))
    z_ref = float(getattr(base_pt, "z", 0.0) or 0.0)
    if abs(z0_raw) > 1e-9:
        z0 = z0_raw
    elif cover > 1e-9:
        z0 = z_ref - cover - height
    else:
        z0 = z_ref
    half_l = 0.5 * length
    half_w = 0.5 * width
    base = App.Vector(float(base_pt.x), float(base_pt.y), z0)
    p1 = base - (t * half_l) - (n * half_w)
    p2 = base + (t * half_l) - (n * half_w)
    p3 = base + (t * half_l) + (n * half_w)
    p4 = base - (t * half_l) + (n * half_w)
    wire = Part.makePolygon([p1, p2, p3, p4, p1])
    face = Part.Face(wire)
    return face.extrude(App.Vector(0, 0, height))


def _safe_str_list(values):
    return [str(v or "") for v in list(values or [])]


def _safe_float_list(values):
    out = []
    for v in list(values or []):
        try:
            x = float(v)
        except Exception:
            x = 0.0
        if not math.isfinite(x):
            x = 0.0
        out.append(float(x))
    return out


def _unique_sorted_floats(values, tol: float = 1e-6):
    vals = sorted([float(v) for v in list(values or [])])
    out = []
    for v in vals:
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def ensure_structure_set_properties(obj):
    if not hasattr(obj, "StructureIds"):
        obj.addProperty("App::PropertyStringList", "StructureIds", "Structures", "Structure identifiers")
        obj.StructureIds = []
    if not hasattr(obj, "StructureTypes"):
        obj.addProperty("App::PropertyStringList", "StructureTypes", "Structures", "Structure type list")
        obj.StructureTypes = []
    if not hasattr(obj, "StartStations"):
        obj.addProperty("App::PropertyFloatList", "StartStations", "Structures", "Structure start stations")
        obj.StartStations = []
    if not hasattr(obj, "EndStations"):
        obj.addProperty("App::PropertyFloatList", "EndStations", "Structures", "Structure end stations")
        obj.EndStations = []
    if not hasattr(obj, "CenterStations"):
        obj.addProperty("App::PropertyFloatList", "CenterStations", "Structures", "Structure center stations")
        obj.CenterStations = []
    if not hasattr(obj, "Sides"):
        obj.addProperty("App::PropertyStringList", "Sides", "Structures", "Structure side list")
        obj.Sides = []
    if not hasattr(obj, "Offsets"):
        obj.addProperty("App::PropertyFloatList", "Offsets", "Structures", "Structure offsets")
        obj.Offsets = []
    if not hasattr(obj, "Widths"):
        obj.addProperty("App::PropertyFloatList", "Widths", "Structures", "Structure widths")
        obj.Widths = []
    if not hasattr(obj, "Heights"):
        obj.addProperty("App::PropertyFloatList", "Heights", "Structures", "Structure heights")
        obj.Heights = []
    if not hasattr(obj, "BottomElevations"):
        obj.addProperty("App::PropertyFloatList", "BottomElevations", "Structures", "Structure bottom elevations")
        obj.BottomElevations = []
    if not hasattr(obj, "Covers"):
        obj.addProperty("App::PropertyFloatList", "Covers", "Structures", "Structure covers")
        obj.Covers = []
    if not hasattr(obj, "RotationsDeg"):
        obj.addProperty("App::PropertyFloatList", "RotationsDeg", "Structures", "Structure rotation angles")
        obj.RotationsDeg = []
    if not hasattr(obj, "BehaviorModes"):
        obj.addProperty("App::PropertyStringList", "BehaviorModes", "Structures", "Structure behavior modes")
        obj.BehaviorModes = []
    if not hasattr(obj, "Notes"):
        obj.addProperty("App::PropertyStringList", "Notes", "Structures", "Structure notes")
        obj.Notes = []
    if not hasattr(obj, "StructureCount"):
        obj.addProperty("App::PropertyInteger", "StructureCount", "Result", "Structure record count")
        obj.StructureCount = 0
    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"


class StructureSet:
    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "StructureSet"
        ensure_structure_set_properties(obj)

    def execute(self, obj):
        ensure_structure_set_properties(obj)
        recs = self.records(obj)
        issues = self.validate(obj)
        obj.StructureCount = int(len(recs))
        aln = _resolve_alignment(obj)
        shape_notes = []
        shp = _empty_shape()
        if Part is not None and hasattr(obj, "Shape") and aln is not None and getattr(aln, "Shape", None):
            total = float(getattr(aln.Shape, "Length", 0.0) or 0.0)
            solids = []
            for rec in recs:
                try:
                    sta = max(0.0, min(total, float(_station_for_record(rec))))
                    p = _resolve_station_point(obj, sta, aln=aln)
                    t = HorizontalAlignment.tangent_at_station(aln, sta)
                    n = HorizontalAlignment.normal_at_station(aln, sta)
                    for off in _side_offsets(rec):
                        solid = _build_structure_solid(p + (n * float(off)), t, n, rec)
                        if solid is not None and not solid.isNull():
                            solids.append(solid)
                except Exception:
                    rid = str(rec.get("Id", "") or f"#{int(rec.get('Index', 0)) + 1}")
                    shape_notes.append(f"{rid}: display shape skipped")
            if solids:
                try:
                    shp = Part.makeCompound(solids)
                except Exception:
                    shp = _empty_shape()
            elif recs:
                shape_notes.append("No display solids generated")
        elif recs:
            shape_notes.append("3D display requires a HorizontalAlignment")

        if shp is not None and hasattr(obj, "Shape"):
            obj.Shape = shp

        note_count = len(issues) + len(shape_notes)
        if note_count == 0:
            obj.Status = f"OK: {len(recs)} records"
        else:
            obj.Status = f"WARN: {len(recs)} records, {note_count} issue(s)"

    def onChanged(self, obj, prop):
        if prop in (
            "StructureIds",
            "StructureTypes",
            "StartStations",
            "EndStations",
            "CenterStations",
            "Sides",
            "Offsets",
            "Widths",
            "Heights",
            "BottomElevations",
            "Covers",
            "RotationsDeg",
            "BehaviorModes",
            "Notes",
        ):
            try:
                obj.touch()
            except Exception:
                pass

    @staticmethod
    def _record_count(obj):
        return max(
            len(list(getattr(obj, "StructureIds", []) or [])),
            len(list(getattr(obj, "StructureTypes", []) or [])),
            len(list(getattr(obj, "StartStations", []) or [])),
            len(list(getattr(obj, "EndStations", []) or [])),
            len(list(getattr(obj, "CenterStations", []) or [])),
            len(list(getattr(obj, "Sides", []) or [])),
            len(list(getattr(obj, "Offsets", []) or [])),
            len(list(getattr(obj, "Widths", []) or [])),
            len(list(getattr(obj, "Heights", []) or [])),
            len(list(getattr(obj, "BottomElevations", []) or [])),
            len(list(getattr(obj, "Covers", []) or [])),
            len(list(getattr(obj, "RotationsDeg", []) or [])),
            len(list(getattr(obj, "BehaviorModes", []) or [])),
            len(list(getattr(obj, "Notes", []) or [])),
            0,
        )

    @staticmethod
    def records(obj):
        ensure_structure_set_properties(obj)
        ids = _safe_str_list(getattr(obj, "StructureIds", []))
        types = _safe_str_list(getattr(obj, "StructureTypes", []))
        starts = _safe_float_list(getattr(obj, "StartStations", []))
        ends = _safe_float_list(getattr(obj, "EndStations", []))
        centers = _safe_float_list(getattr(obj, "CenterStations", []))
        sides = _safe_str_list(getattr(obj, "Sides", []))
        offsets = _safe_float_list(getattr(obj, "Offsets", []))
        widths = _safe_float_list(getattr(obj, "Widths", []))
        heights = _safe_float_list(getattr(obj, "Heights", []))
        bottoms = _safe_float_list(getattr(obj, "BottomElevations", []))
        covers = _safe_float_list(getattr(obj, "Covers", []))
        rotations = _safe_float_list(getattr(obj, "RotationsDeg", []))
        behaviors = _safe_str_list(getattr(obj, "BehaviorModes", []))
        notes = _safe_str_list(getattr(obj, "Notes", []))

        n = StructureSet._record_count(obj)
        recs = []
        for i in range(n):
            recs.append(
                {
                    "Index": int(i),
                    "Id": ids[i] if i < len(ids) else "",
                    "Type": types[i] if i < len(types) else "",
                    "StartStation": starts[i] if i < len(starts) else 0.0,
                    "EndStation": ends[i] if i < len(ends) else 0.0,
                    "CenterStation": centers[i] if i < len(centers) else 0.0,
                    "Side": sides[i] if i < len(sides) else "",
                    "Offset": offsets[i] if i < len(offsets) else 0.0,
                    "Width": widths[i] if i < len(widths) else 0.0,
                    "Height": heights[i] if i < len(heights) else 0.0,
                    "BottomElevation": bottoms[i] if i < len(bottoms) else 0.0,
                    "Cover": covers[i] if i < len(covers) else 0.0,
                    "RotationDeg": rotations[i] if i < len(rotations) else 0.0,
                    "BehaviorMode": behaviors[i] if i < len(behaviors) else "",
                    "Notes": notes[i] if i < len(notes) else "",
                }
            )
        return recs

    @staticmethod
    def validate(obj):
        issues = []
        for rec in StructureSet.records(obj):
            rid = str(rec.get("Id", "") or f"#{int(rec['Index']) + 1}")
            typ = str(rec.get("Type", "") or "").strip().lower()
            side = str(rec.get("Side", "") or "").strip().lower()
            mode = str(rec.get("BehaviorMode", "") or "").strip().lower()
            s0 = float(rec.get("StartStation", 0.0) or 0.0)
            s1 = float(rec.get("EndStation", 0.0) or 0.0)
            sc = float(rec.get("CenterStation", 0.0) or 0.0)
            w = float(rec.get("Width", 0.0) or 0.0)
            h = float(rec.get("Height", 0.0) or 0.0)

            if not typ:
                issues.append(f"{rid}: type is empty")
            elif typ not in ALLOWED_TYPES:
                issues.append(f"{rid}: unknown type '{typ}'")

            if not side:
                issues.append(f"{rid}: side is empty")
            elif side not in ALLOWED_SIDES:
                issues.append(f"{rid}: unknown side '{side}'")

            if mode and mode not in ALLOWED_BEHAVIOR_MODES:
                issues.append(f"{rid}: unknown behavior mode '{mode}'")

            if s1 < s0:
                issues.append(f"{rid}: end station is smaller than start station")
            if sc > 0.0 and s1 > s0 and (sc < s0 or sc > s1):
                issues.append(f"{rid}: center station is outside start/end range")
            if w < 0.0:
                issues.append(f"{rid}: width is negative")
            if h < 0.0:
                issues.append(f"{rid}: height is negative")
        return issues

    @staticmethod
    def active_records_at_station(obj, s: float, tol: float = 1e-6):
        ss = float(s)
        tt = max(1e-9, float(tol))
        out = []
        for rec in StructureSet.records(obj):
            s0 = float(rec.get("StartStation", 0.0) or 0.0)
            s1 = float(rec.get("EndStation", 0.0) or 0.0)
            sc = float(rec.get("CenterStation", 0.0) or 0.0)
            if s1 < s0:
                s0, s1 = s1, s0

            active = False
            if s1 > s0 + tt:
                active = (ss >= s0 - tt) and (ss <= s1 + tt)
            else:
                active = abs(ss - s0) <= tt

            if (not active) and abs(sc) > tt:
                active = abs(ss - sc) <= tt

            if active:
                out.append(rec)
        return out

    @staticmethod
    def structure_key_station_items(obj, include_start_end: bool = True, include_centers: bool = True, before: float = 0.0, after: float = 0.0):
        bt = max(0.0, float(before))
        at = max(0.0, float(after))
        items = []
        for rec in StructureSet.records(obj):
            rid = str(rec.get("Id", "") or f"#{int(rec.get('Index', 0)) + 1}")
            typ = str(rec.get("Type", "") or "").strip()
            s0 = float(rec.get("StartStation", 0.0) or 0.0)
            s1 = float(rec.get("EndStation", 0.0) or 0.0)
            sc = float(rec.get("CenterStation", 0.0) or 0.0)
            if s1 < s0:
                s0, s1 = s1, s0

            def _add(station, tag=None, role=None):
                items.append(
                    {
                        "station": float(station),
                        "tag": (str(tag) if tag else ""),
                        "role": str(role or ""),
                        "ids": [rid],
                        "types": [typ] if typ else [],
                    }
                )

            if include_start_end:
                _add(s0, "STR_START", "start")
                if abs(s1 - s0) > 1e-9:
                    _add(s1, "STR_END", "end")
            if include_centers:
                if abs(sc) > 1e-9 or (abs(s0) <= 1e-9 and abs(s1) <= 1e-9):
                    _add(sc, "STR_CENTER", "center")
            if bt > 1e-9:
                _add(s0 - bt, "", "buffer_before")
            if at > 1e-9:
                _add(s1 + at, "", "buffer_after")
        return items

    @staticmethod
    def structure_key_stations(obj, include_start_end: bool = True, include_centers: bool = True, before: float = 0.0, after: float = 0.0):
        items = StructureSet.structure_key_station_items(
            obj,
            include_start_end=include_start_end,
            include_centers=include_centers,
            before=before,
            after=after,
        )
        return _unique_sorted_floats([it.get("station", 0.0) for it in items])


class ViewProviderStructureSet:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Flat Lines"
            vobj.ShapeColor = (0.80, 0.56, 0.22)
            vobj.LineColor = (0.55, 0.32, 0.05)
            vobj.Transparency = 35
        except Exception:
            pass

    def getIcon(self):
        return ""

    def getDisplayModes(self, vobj):
        return ["Flat Lines", "Shaded", "Wireframe"]

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def setDisplayMode(self, mode):
        return str(mode)

    def updateData(self, obj, prop):
        return

    def onChanged(self, vobj, prop):
        return
