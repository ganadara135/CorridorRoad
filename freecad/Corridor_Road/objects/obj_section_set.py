# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/objects/obj_section_set.py
import re
import math

import FreeCAD as App
import Part

from freecad.Corridor_Road.objects.obj_centerline3d import Centerline3D
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet as StructureSetSource
from freecad.Corridor_Road.objects.obj_typical_section_template import build_top_profile as _build_typical_top_profile
from freecad.Corridor_Road.objects.obj_project import get_length_scale
from freecad.Corridor_Road.objects import coord_transform as _ct
from freecad.Corridor_Road.objects import surface_sampling_core as _ssc

_RECOMP_LABEL_SUFFIX = " [Recompute]"


def _is_mesh_object(obj) -> bool:
    return _ssc.is_mesh_object(obj)


def _is_shape_object(obj) -> bool:
    return _ssc.is_shape_object(obj)


def _find_project(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        if o.Name.startswith("CorridorRoadProject"):
            return o
    return None


def _find_terrain_candidate(doc):
    if doc is None:
        return None
    # 1) Prefer explicit terrain-like names.
    for o in doc.Objects:
        try:
            nm = str(getattr(o, "Name", "") or "").lower()
            lb = str(getattr(o, "Label", "") or "").lower()
            if ("terrain" in nm or "terrain" in lb) and _is_mesh_object(o):
                return o
        except Exception:
            continue
    # 2) Fallback to first mesh object.
    for o in doc.Objects:
        if _is_mesh_object(o):
            return o
    return None


def _unique_sorted(values, tol: float = 1e-6):
    vals = sorted([float(v) for v in values])
    out = []
    for v in vals:
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def _clamp(value: float, lo: float, hi: float):
    return max(float(lo), min(float(hi), float(value)))


def _parse_station_text(text: str):
    if not text:
        return []
    tokens = re.split(r"[,\s;]+", str(text).strip())
    out = []
    for t in tokens:
        if not t:
            continue
        try:
            out.append(float(t))
        except Exception:
            continue
    return out


def _resolve_structure_source(obj):
    ss = getattr(obj, "StructureSet", None) if hasattr(obj, "StructureSet") else None
    if ss is not None:
        return ss
    doc = getattr(obj, "Document", None)
    prj = _find_project(doc)
    if prj is not None and hasattr(prj, "StructureSet"):
        return getattr(prj, "StructureSet", None)
    return None


def _structure_overlay_offsets(rec):
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


def _primary_structure_role(meta) -> str:
    roles = [str(v or "").strip().lower() for v in list(meta.get("StructureRoles", []) or [])]
    for key in ("center", "start", "end", "transition_before", "transition_after", "active"):
        if key in roles:
            return key
    return roles[0] if roles else ""


def _overlay_signed_side_factor(rec) -> float:
    side = str(rec.get("Side", "") or "").strip().lower()
    if side == "left":
        return 1.0
    if side == "right":
        return -1.0
    off = float(rec.get("Offset", 0.0) or 0.0)
    if off < -1e-9:
        return -1.0
    return 1.0


def _overlay_rect_wire(center, nvec, zvec, width: float, height: float):
    half_w = 0.5 * max(1e-6, float(width))
    p1 = center - (nvec * half_w)
    p2 = center + (nvec * half_w)
    p3 = p2 + (zvec * max(1e-6, float(height)))
    p4 = p1 + (zvec * max(1e-6, float(height)))
    return Part.makePolygon([p1, p2, p3, p4, p1])


def _overlay_profile_wire(origin, nvec, zvec, coords_nz):
    pts = []
    for nn, zz in list(coords_nz or []):
        pts.append(origin + (nvec * float(nn)) + (zvec * float(zz)))
    if not pts:
        return None
    if (pts[0] - pts[-1]).Length > 1e-9:
        pts.append(pts[0])
    return Part.makePolygon(pts)


def _overlay_geometry_mode(rec) -> str:
    mode = str(rec.get("GeometryMode", "") or "").strip().lower()
    if mode in ("box", "template"):
        return mode
    if str(rec.get("TemplateName", "") or "").strip():
        return "template"
    return "box"


def _overlay_template_name(rec) -> str:
    name = str(rec.get("TemplateName", "") or "").strip().lower()
    if name:
        return name
    typ = str(rec.get("Type", "") or "").strip().lower()
    if typ == "culvert":
        return "box_culvert"
    if typ == "crossing":
        return "utility_crossing"
    if typ == "retaining_wall":
        return "retaining_wall"
    if typ == "abutment_zone":
        return "abutment_block"
    return ""


def _structure_overlay_label(station: float, meta) -> str:
    types = [str(v or "").strip() for v in list(meta.get("StructureTypes", []) or []) if str(v or "").strip()]
    ids = [str(v or "").strip() for v in list(meta.get("StructureIds", []) or []) if str(v or "").strip()]
    role = _primary_structure_role(meta)

    parts = []
    if types:
        t0 = types[0].replace("_", " ").upper()
        if len(types) > 1:
            t0 = f"{t0}+{len(types)-1}"
        parts.append(t0)
    else:
        parts.append("STRUCTURE")

    if ids:
        i0 = ids[0]
        if len(ids) > 1:
            i0 = f"{i0}+{len(ids)-1}"
        parts.append(i0)

    if role and role != "active":
        parts.append(role.replace("_", " ").upper())

    return f"STA {float(station):.3f} [{' | '.join(parts)}]"


def _slope_sign(value: float, fallback: float = 1.0) -> float:
    v = float(value)
    if v > 1e-9:
        return 1.0
    if v < -1e-9:
        return -1.0
    return 1.0 if float(fallback) >= 0.0 else -1.0


def _structure_side_override_spec(rec, side_key: str, scale: float):
    typ = str(rec.get("Type", "") or "").strip().lower()
    side = str(rec.get("Side", "") or "").strip().lower()
    width = max(0.0, abs(float(rec.get("Width", 0.0) or 0.0)))
    height = max(0.0, abs(float(rec.get("Height", 0.0) or 0.0)))

    applies = False
    if typ in ("culvert", "crossing", "bridge_zone", "abutment_zone"):
        applies = True
    elif side_key == "left" and side in ("left", "both", "center"):
        applies = True
    elif side_key == "right" and side in ("right", "both", "center"):
        applies = True
    if not applies:
        return None

    if typ in ("culvert", "crossing"):
        return {
            "Action": "berm",
            "TargetWidth": max(1.0 * scale, min(4.0 * scale, 0.35 * width + 0.50 * height)),
            "SlopeMode": "flat",
            "DisableDaylight": True,
            "Priority": 20,
        }
    if typ == "retaining_wall":
        return {
            "Action": "wall",
            "TargetWidth": max(0.35 * scale, min(2.0 * scale, 0.15 * width + 0.25 * height)),
            "SlopeMode": "steep",
            "SteepSlopePct": max(250.0, 60.0 * max(1.0, height / max(scale, 1e-9))),
            "DisableDaylight": True,
            "Priority": 30,
        }
    if typ in ("bridge_zone", "abutment_zone"):
        return {
            "Action": "trim",
            "TargetWidth": max(1.0 * scale, min(6.0 * scale, 0.20 * width + 0.50 * height)),
            "SlopeMode": "same",
            "DisableDaylight": True,
            "Priority": 15,
        }
    return {
        "Action": "stub",
        "TargetWidth": max(0.25 * scale, min(2.0 * scale, 0.15 * width + 0.25 * height)),
        "SlopeMode": "flat",
        "DisableDaylight": True,
        "Priority": 10,
    }


def _merge_side_override_spec(current, incoming):
    if incoming is None:
        return current
    if current is None:
        return dict(incoming)
    cur_pri = int(current.get("Priority", 0) or 0)
    inc_pri = int(incoming.get("Priority", 0) or 0)
    if inc_pri > cur_pri:
        return dict(incoming)
    if inc_pri < cur_pri:
        return current
    cur_w = float(current.get("TargetWidth", 0.0) or 0.0)
    inc_w = float(incoming.get("TargetWidth", 0.0) or 0.0)
    if cur_w <= 1e-9:
        return dict(incoming)
    if inc_w > 1e-9 and inc_w < cur_w:
        return dict(incoming)
    return current


def _alignment_ip_key_stations(aln):
    if aln is None or getattr(aln, "Shape", None) is None or aln.Shape.isNull():
        return []
    total = float(aln.Shape.Length)
    if total <= 1e-9:
        return [0.0]

    vals = [0.0, total]
    pts = list(getattr(aln, "IPPoints", []) or [])
    for p in pts:
        try:
            s = float(HorizontalAlignment.station_at_xy(aln, float(p.x), float(p.y), samples_per_edge=48))
            vals.append(s)
        except Exception:
            continue
    vals = [min(max(0.0, float(v)), total) for v in vals]
    return _unique_sorted(vals)


def _alignment_transition_key_stations(aln):
    if aln is None or getattr(aln, "Shape", None) is None or aln.Shape.isNull():
        return [], [], [], []
    total = float(aln.Shape.Length)
    if total <= 1e-9:
        return [], [], [], []

    ts = [min(max(0.0, float(v)), total) for v in list(getattr(aln, "TSKeyStations", []) or [])]
    sc = [min(max(0.0, float(v)), total) for v in list(getattr(aln, "SCKeyStations", []) or [])]
    cs = [min(max(0.0, float(v)), total) for v in list(getattr(aln, "CSKeyStations", []) or [])]
    st = [min(max(0.0, float(v)), total) for v in list(getattr(aln, "STKeyStations", []) or [])]
    return _unique_sorted(ts), _unique_sorted(sc), _unique_sorted(cs), _unique_sorted(st)


def _mark_corridor_needs_recompute(obj_corridor):
    try:
        if hasattr(obj_corridor, "NeedsRecompute"):
            obj_corridor.NeedsRecompute = True
    except Exception:
        pass

    try:
        st = str(getattr(obj_corridor, "Status", "") or "")
        if "NEEDS_RECOMPUTE" not in st:
            obj_corridor.Status = "NEEDS_RECOMPUTE: Source SectionSet changed."
    except Exception:
        pass

    try:
        label = str(getattr(obj_corridor, "Label", "") or "")
        if _RECOMP_LABEL_SUFFIX not in label:
            obj_corridor.Label = f"{label}{_RECOMP_LABEL_SUFFIX}"
    except Exception:
        pass


def ensure_section_set_properties(obj):
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)

    if not hasattr(obj, "Group"):
        obj.addProperty("App::PropertyLinkList", "Group", "Sections", "Child section objects")

    if not hasattr(obj, "SourceCenterlineDisplay"):
        obj.addProperty("App::PropertyLink", "SourceCenterlineDisplay", "Sections", "Centerline3DDisplay source link")
    if not hasattr(obj, "AssemblyTemplate"):
        obj.addProperty("App::PropertyLink", "AssemblyTemplate", "Sections", "AssemblyTemplate link")
    if not hasattr(obj, "TypicalSectionTemplate"):
        obj.addProperty("App::PropertyLink", "TypicalSectionTemplate", "Sections", "TypicalSectionTemplate link")
    if not hasattr(obj, "UseTypicalSectionTemplate"):
        obj.addProperty("App::PropertyBool", "UseTypicalSectionTemplate", "Sections", "Use TypicalSectionTemplate as primary top-profile source")
        obj.UseTypicalSectionTemplate = False
    if not hasattr(obj, "TerrainMesh"):
        obj.addProperty("App::PropertyLink", "TerrainMesh", "Sections", "Optional terrain source link for daylight (Mesh only)")
    if not hasattr(obj, "TerrainMeshCoords"):
        obj.addProperty(
            "App::PropertyEnumeration",
            "TerrainMeshCoords",
            "Sections",
            "Coordinate system of daylight terrain source",
        )
        obj.TerrainMeshCoords = ["Local", "World"]
        obj.TerrainMeshCoords = "Local"
    if not hasattr(obj, "DaylightAuto"):
        obj.addProperty("App::PropertyBool", "DaylightAuto", "Sections", "Auto daylight to terrain during section build")
        obj.DaylightAuto = True

    if not hasattr(obj, "Mode"):
        obj.addProperty("App::PropertyEnumeration", "Mode", "Sections", "Station selection mode")
        obj.Mode = ["Range", "Manual"]
        obj.Mode = "Range"

    if not hasattr(obj, "StartStation"):
        obj.addProperty("App::PropertyFloat", "StartStation", "Sections", "Start station (m)")
        obj.StartStation = 0.0
    if not hasattr(obj, "EndStation"):
        obj.addProperty("App::PropertyFloat", "EndStation", "Sections", "End station (m)")
        obj.EndStation = 100.0 * scale
    if not hasattr(obj, "Interval"):
        obj.addProperty("App::PropertyFloat", "Interval", "Sections", "Interval for range mode (m)")
        obj.Interval = 20.0 * scale
    if not hasattr(obj, "StationText"):
        obj.addProperty("App::PropertyString", "StationText", "Sections", "Manual station list text")
        obj.StationText = ""
    if not hasattr(obj, "IncludeAlignmentIPStations"):
        obj.addProperty("App::PropertyBool", "IncludeAlignmentIPStations", "Sections", "In Range mode, always include alignment IP key stations")
        obj.IncludeAlignmentIPStations = True
    if not hasattr(obj, "IncludeAlignmentSCCSStations"):
        obj.addProperty("App::PropertyBool", "IncludeAlignmentSCCSStations", "Sections", "In Range mode, include transition TS/SC/CS/ST key stations")
        obj.IncludeAlignmentSCCSStations = False
    if not hasattr(obj, "IncludeStructureStations"):
        obj.addProperty("App::PropertyBool", "IncludeStructureStations", "Sections", "Include structure/crossing key stations from text list")
        obj.IncludeStructureStations = False
    if not hasattr(obj, "StructureStationText"):
        obj.addProperty("App::PropertyString", "StructureStationText", "Sections", "Structure/crossing key stations list text")
        obj.StructureStationText = ""
    if not hasattr(obj, "StructureSet"):
        obj.addProperty("App::PropertyLink", "StructureSet", "Structures", "Linked StructureSet source")
    if not hasattr(obj, "UseStructureSet"):
        obj.addProperty("App::PropertyBool", "UseStructureSet", "Structures", "Use linked StructureSet for structure-driven station merge")
        obj.UseStructureSet = False
    if not hasattr(obj, "IncludeStructureStartEnd"):
        obj.addProperty("App::PropertyBool", "IncludeStructureStartEnd", "Structures", "Include structure start/end stations from StructureSet")
        obj.IncludeStructureStartEnd = True
    if not hasattr(obj, "IncludeStructureCenters"):
        obj.addProperty("App::PropertyBool", "IncludeStructureCenters", "Structures", "Include structure center stations from StructureSet")
        obj.IncludeStructureCenters = True
    if not hasattr(obj, "IncludeStructureTransitionStations"):
        obj.addProperty("App::PropertyBool", "IncludeStructureTransitionStations", "Structures", "Include transition stations before and after structure zones")
        obj.IncludeStructureTransitionStations = True
    if not hasattr(obj, "AutoStructureTransitionDistance"):
        obj.addProperty("App::PropertyBool", "AutoStructureTransitionDistance", "Structures", "Automatically derive transition distance from structure type and size")
        obj.AutoStructureTransitionDistance = True
    if not hasattr(obj, "StructureTransitionDistance"):
        scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
        obj.addProperty("App::PropertyFloat", "StructureTransitionDistance", "Structures", "Transition distance used before and after structure boundaries")
        obj.StructureTransitionDistance = 5.0 * scale
    if not hasattr(obj, "StructureBufferBefore"):
        obj.addProperty("App::PropertyFloat", "StructureBufferBefore", "Structures", "Additional station before structure start")
        obj.StructureBufferBefore = 0.0
    if not hasattr(obj, "StructureBufferAfter"):
        obj.addProperty("App::PropertyFloat", "StructureBufferAfter", "Structures", "Additional station after structure end")
        obj.StructureBufferAfter = 0.0
    if not hasattr(obj, "CreateStructureTaggedChildren"):
        obj.addProperty("App::PropertyBool", "CreateStructureTaggedChildren", "Structures", "Add structure-derived tags to child section labels")
        obj.CreateStructureTaggedChildren = True
    if not hasattr(obj, "ApplyStructureOverrides"):
        obj.addProperty("App::PropertyBool", "ApplyStructureOverrides", "Structures", "Reserved flag for future structure-based section overrides")
        obj.ApplyStructureOverrides = False

    if not hasattr(obj, "StationValues"):
        obj.addProperty("App::PropertyFloatList", "StationValues", "Result", "Resolved stations for sections (m)")
    if not hasattr(obj, "ResolvedStructureCount"):
        obj.addProperty("App::PropertyInteger", "ResolvedStructureCount", "Result", "Count of merged structure-driven stations")
        obj.ResolvedStructureCount = 0
    if not hasattr(obj, "ResolvedStructureTags"):
        obj.addProperty("App::PropertyStringList", "ResolvedStructureTags", "Result", "Resolved structure station summary")
        obj.ResolvedStructureTags = []
    if not hasattr(obj, "SectionSchemaVersion"):
        obj.addProperty("App::PropertyInteger", "SectionSchemaVersion", "Result", "Section schema version")
        obj.SectionSchemaVersion = 1
    if not hasattr(obj, "TopProfileSource"):
        obj.addProperty("App::PropertyString", "TopProfileSource", "Result", "Top-profile source summary")
        obj.TopProfileSource = "assembly_simple"
    if not hasattr(obj, "TopProfileEdgeSummary"):
        obj.addProperty("App::PropertyString", "TopProfileEdgeSummary", "Result", "Outermost top-profile edge component summary")
        obj.TopProfileEdgeSummary = "-"
    if not hasattr(obj, "PavementLayerCount"):
        obj.addProperty("App::PropertyInteger", "PavementLayerCount", "Result", "Typical-section pavement layer count")
        obj.PavementLayerCount = 0
    if not hasattr(obj, "EnabledPavementLayerCount"):
        obj.addProperty("App::PropertyInteger", "EnabledPavementLayerCount", "Result", "Enabled typical-section pavement layer count")
        obj.EnabledPavementLayerCount = 0
    if not hasattr(obj, "PavementTotalThickness"):
        obj.addProperty("App::PropertyFloat", "PavementTotalThickness", "Result", "Typical-section pavement total thickness")
        obj.PavementTotalThickness = 0.0
    if not hasattr(obj, "SectionCount"):
        obj.addProperty("App::PropertyInteger", "SectionCount", "Result", "Section count")
        obj.SectionCount = 0
    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"

    if not hasattr(obj, "CreateChildSections"):
        obj.addProperty("App::PropertyBool", "CreateChildSections", "Sections", "Create child section objects in tree")
        obj.CreateChildSections = True
    if not hasattr(obj, "AutoRebuildChildren"):
        obj.addProperty("App::PropertyBool", "AutoRebuildChildren", "Sections", "Auto rebuild child sections on recompute")
        obj.AutoRebuildChildren = True
    if not hasattr(obj, "RebuildNow"):
        obj.addProperty("App::PropertyBool", "RebuildNow", "Sections", "Set True to force child section rebuild now")
        obj.RebuildNow = False

    if not hasattr(obj, "ShowSectionWires"):
        obj.addProperty("App::PropertyBool", "ShowSectionWires", "Display", "Show section wires as set shape")
        obj.ShowSectionWires = True


class SectionSet:
    """
    Section set container with station selection settings and aggregate display.
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "SectionSet"
        self._is_rebuilding_children = False
        self._suspend_recompute = False
        ensure_section_set_properties(obj)

    @staticmethod
    def _resolve_structure_station_items(obj, total: float, mode: str = "", s0: float = None, s1: float = None):
        items = []
        source_kind = ""
        source_obj = None

        if bool(getattr(obj, "UseStructureSet", False)):
            ss = _resolve_structure_source(obj)
            if ss is not None:
                source_obj = ss
                source_kind = "structure_set"
                items = StructureSetSource.structure_key_station_items(
                    ss,
                    include_start_end=bool(getattr(obj, "IncludeStructureStartEnd", True)),
                    include_centers=bool(getattr(obj, "IncludeStructureCenters", True)),
                    include_transition=bool(getattr(obj, "IncludeStructureTransitionStations", True)),
                    auto_transition=bool(getattr(obj, "AutoStructureTransitionDistance", True)),
                    transition=float(getattr(obj, "StructureTransitionDistance", 0.0) or 0.0),
                )

        out = []
        lo = None if s0 is None else float(min(s0, s1))
        hi = None if s1 is None else float(max(s0, s1))
        for it in items:
            st = _clamp(float(it.get("station", 0.0) or 0.0), 0.0, float(total))
            if str(mode or "") == "Range" and lo is not None and hi is not None:
                if st < lo - 1e-9 or st > hi + 1e-9:
                    continue
            rec = dict(it)
            rec["station"] = st
            out.append(rec)
        return out, source_kind, source_obj

    @staticmethod
    def _resolved_structure_summary(items):
        if not items:
            return 0, []
        rows = []
        uniq = set()
        for it in sorted(items, key=lambda x: float(x.get("station", 0.0))):
            sta = float(it.get("station", 0.0))
            tag = str(it.get("tag", "") or "")
            ids = ",".join([str(v) for v in list(it.get("ids", []) or []) if str(v)])
            if tag:
                txt = f"{sta:.3f}:{tag}"
            else:
                txt = f"{sta:.3f}:TRANSITION"
            if ids:
                txt += f" [{ids}]"
            if txt not in uniq:
                rows.append(txt)
                uniq.add(txt)
        count = len(_unique_sorted([float(it.get("station", 0.0)) for it in items]))
        return int(count), rows

    @staticmethod
    def _structure_context_at_station(obj, station: float):
        ctx = {
            "HasStructure": False,
            "ActiveRecords": [],
            "SuppressSideSlopes": False,
            "SuppressDaylight": False,
            "OverlayRecords": [],
            "LeftAction": "keep",
            "RightAction": "keep",
            "LeftDisableDaylight": False,
            "RightDisableDaylight": False,
            "BoundaryRoles": [],
            "IsBoundaryStation": False,
            "LeftOverrideSpec": None,
            "RightOverrideSpec": None,
        }
        if not bool(getattr(obj, "UseStructureSet", False)):
            return ctx
        ss = _resolve_structure_source(obj)
        if ss is None:
            return ctx

        src = getattr(obj, "SourceCenterlineDisplay", None)
        aln = getattr(src, "Alignment", None) if src is not None else None
        total = float(getattr(getattr(aln, "Shape", None), "Length", 0.0) or 0.0)
        tol = max(1e-4, 1e-6 * max(total, 1.0))
        try:
            active = StructureSetSource.active_records_at_station(ss, float(station), tol=tol)
        except Exception:
            active = []
        if not active:
            return ctx

        resolved_active = []
        for rec in list(active or []):
            try:
                resolved = StructureSetSource.resolve_profile_at_station(ss, rec, float(station))
                resolved_active.append(resolved if resolved else rec)
            except Exception:
                resolved_active.append(rec)

        ctx["HasStructure"] = True
        ctx["ActiveRecords"] = list(resolved_active)
        ctx["OverlayRecords"] = list(resolved_active)
        try:
            station_items, _sk, _so = SectionSet._resolve_structure_station_items(
                obj,
                total,
                mode=str(getattr(obj, "Mode", "Range") or "Range"),
                s0=float(getattr(obj, "StartStation", 0.0) or 0.0),
                s1=float(getattr(obj, "EndStation", total) or total),
            )
        except Exception:
            station_items = []
        boundary_roles = []
        for it in station_items:
            if abs(float(it.get("station", 0.0) or 0.0) - float(station)) > tol:
                continue
            role = str(it.get("role", "") or "").strip().lower()
            if role and role not in boundary_roles:
                boundary_roles.append(role)
        ctx["BoundaryRoles"] = list(boundary_roles)
        ctx["IsBoundaryStation"] = any(r in ("start", "end", "transition_before", "transition_after") for r in boundary_roles)

        if ctx["IsBoundaryStation"]:
            return ctx

        scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
        for rec in resolved_active:
            mode = str(rec.get("BehaviorMode", "") or "").strip().lower()
            if mode not in ("section_overlay", "assembly_override"):
                continue
            left_spec = _structure_side_override_spec(rec, "left", scale)
            right_spec = _structure_side_override_spec(rec, "right", scale)
            ctx["LeftOverrideSpec"] = _merge_side_override_spec(ctx.get("LeftOverrideSpec"), left_spec)
            ctx["RightOverrideSpec"] = _merge_side_override_spec(ctx.get("RightOverrideSpec"), right_spec)

        if ctx["LeftOverrideSpec"] is not None:
            ctx["LeftAction"] = str(ctx["LeftOverrideSpec"].get("Action", "keep") or "keep").strip().lower()
            ctx["LeftDisableDaylight"] = bool(ctx["LeftOverrideSpec"].get("DisableDaylight", False))
        if ctx["RightOverrideSpec"] is not None:
            ctx["RightAction"] = str(ctx["RightOverrideSpec"].get("Action", "keep") or "keep").strip().lower()
            ctx["RightDisableDaylight"] = bool(ctx["RightOverrideSpec"].get("DisableDaylight", False))

        if ctx["LeftAction"] == "stub" and ctx["RightAction"] == "stub":
            ctx["SuppressSideSlopes"] = True
        if ctx["LeftDisableDaylight"] and ctx["RightDisableDaylight"]:
            ctx["SuppressDaylight"] = True
        return ctx

    @staticmethod
    def resolve_station_values(obj):
        src = getattr(obj, "SourceCenterlineDisplay", None)
        if src is None:
            return []

        aln = getattr(src, "Alignment", None)
        if aln is None or aln.Shape is None or aln.Shape.isNull():
            return []

        total = float(aln.Shape.Length)
        mode = str(getattr(obj, "Mode", "Range"))
        vals = []
        s0 = 0.0
        s1 = float(total)

        if mode == "Manual":
            vals = _parse_station_text(getattr(obj, "StationText", ""))
            vals = [min(max(0.0, float(v)), total) for v in vals]
        else:
            # Range mode
            s0 = float(getattr(obj, "StartStation", 0.0))
            s1 = float(getattr(obj, "EndStation", total))
            if s1 < s0:
                s0, s1 = s1, s0

            s0 = min(max(0.0, s0), total)
            s1 = min(max(0.0, s1), total)
            if s1 < s0 + 1e-9:
                vals = [s0]
            else:
                itv = float(getattr(obj, "Interval", 20.0))
                if itv <= 1e-9:
                    itv = 20.0 * get_length_scale(getattr(obj, "Document", None), default=1.0)
                    obj.Interval = itv

                vals = [s0]
                s = s0 + itv
                while s < s1 - 1e-9:
                    vals.append(float(s))
                    s += itv
                vals.append(float(s1))

            if bool(getattr(obj, "IncludeAlignmentIPStations", True)):
                try:
                    keys = _alignment_ip_key_stations(aln)
                    keys = [v for v in keys if (v >= s0 - 1e-9 and v <= s1 + 1e-9)]
                    vals.extend(keys)
                except Exception:
                    pass
            if bool(getattr(obj, "IncludeAlignmentSCCSStations", False)):
                try:
                    ts_keys, sc_keys, cs_keys, st_keys = _alignment_transition_key_stations(aln)
                    ts_keys = [v for v in ts_keys if (v >= s0 - 1e-9 and v <= s1 + 1e-9)]
                    sc_keys = [v for v in sc_keys if (v >= s0 - 1e-9 and v <= s1 + 1e-9)]
                    cs_keys = [v for v in cs_keys if (v >= s0 - 1e-9 and v <= s1 + 1e-9)]
                    st_keys = [v for v in st_keys if (v >= s0 - 1e-9 and v <= s1 + 1e-9)]
                    vals.extend(ts_keys)
                    vals.extend(sc_keys)
                    vals.extend(cs_keys)
                    vals.extend(st_keys)
                except Exception:
                    pass

        try:
            struct_items, _skind, _sobj = SectionSet._resolve_structure_station_items(
                obj,
                total,
                mode=mode,
                s0=s0,
                s1=s1,
            )
            vals.extend([float(it.get("station", 0.0)) for it in struct_items])
        except Exception:
            pass
        return _unique_sorted(vals)

    @staticmethod
    def resolve_station_tags(obj, stations):
        """
        Resolve per-station tag list used by child section labels.
        """
        out = [[] for _ in stations]
        if not stations:
            return out

        src = getattr(obj, "SourceCenterlineDisplay", None)
        aln = getattr(src, "Alignment", None) if src is not None else None
        if aln is None or getattr(aln, "Shape", None) is None or aln.Shape.isNull():
            return out

        tol = max(1e-4, 1e-6 * float(getattr(aln.Shape, "Length", 1.0)))
        key_sets = []

        if bool(getattr(obj, "IncludeAlignmentIPStations", True)):
            try:
                key_sets.append(("PI", _alignment_ip_key_stations(aln)))
            except Exception:
                pass
        if bool(getattr(obj, "IncludeAlignmentSCCSStations", False)):
            try:
                ts_keys, sc_keys, cs_keys, st_keys = _alignment_transition_key_stations(aln)
                key_sets.append(("TS", ts_keys))
                key_sets.append(("SC", sc_keys))
                key_sets.append(("CS", cs_keys))
                key_sets.append(("ST", st_keys))
            except Exception:
                pass
        struct_items = []
        struct_kind = ""
        struct_obj = None
        try:
            struct_items, struct_kind, struct_obj = SectionSet._resolve_structure_station_items(
                obj,
                float(aln.Shape.Length),
                mode=str(getattr(obj, "Mode", "Range") or "Range"),
                s0=float(getattr(obj, "StartStation", 0.0) or 0.0),
                s1=float(getattr(obj, "EndStation", float(aln.Shape.Length)) or float(aln.Shape.Length)),
            )
        except Exception:
            struct_items = []
        if struct_items and bool(getattr(obj, "CreateStructureTaggedChildren", True)):
            by_tag = {}
            for it in struct_items:
                tag = str(it.get("tag", "") or "")
                if not tag:
                    continue
                by_tag.setdefault(tag, []).append(float(it.get("station", 0.0)))
            for tag, keys in by_tag.items():
                key_sets.append((tag, _unique_sorted(keys)))

        if not key_sets:
            key_sets = []

        for i, s in enumerate(stations):
            ss = float(s)
            tags = []
            for tag, keys in key_sets:
                if any(abs(ss - float(k)) <= tol for k in keys):
                    tags.append(tag)
            if bool(getattr(obj, "CreateStructureTaggedChildren", True)) and struct_kind == "structure_set" and struct_obj is not None:
                try:
                    active = StructureSetSource.active_records_at_station(struct_obj, ss, tol=tol)
                    if active:
                        tags.append("STR")
                except Exception:
                    pass
            if tags:
                dedup = []
                for tg in tags:
                    if tg not in dedup:
                        dedup.append(tg)
                tags = dedup
            out[i] = tags
        return out

    @staticmethod
    def resolve_structure_metadata(obj, stations):
        out = []
        if not stations:
            return out

        src = getattr(obj, "SourceCenterlineDisplay", None)
        aln = getattr(src, "Alignment", None) if src is not None else None
        total = float(getattr(getattr(aln, "Shape", None), "Length", 0.0) or 0.0)
        tol = max(1e-4, 1e-6 * max(total, 1.0))

        struct_items = []
        struct_kind = ""
        struct_obj = None
        try:
            struct_items, struct_kind, struct_obj = SectionSet._resolve_structure_station_items(
                obj,
                total,
                mode=str(getattr(obj, "Mode", "Range") or "Range"),
                s0=float(getattr(obj, "StartStation", 0.0) or 0.0),
                s1=float(getattr(obj, "EndStation", total) or total),
            )
        except Exception:
            struct_items = []

        for s in stations:
            ss = float(s)
            ids = []
            types = []
            roles = []

            if struct_kind == "structure_set" and struct_obj is not None:
                try:
                    active = StructureSetSource.active_records_at_station(struct_obj, ss, tol=tol)
                except Exception:
                    active = []
                for rec in active:
                    rid = str(rec.get("Id", "") or f"#{int(rec.get('Index', 0)) + 1}")
                    typ = str(rec.get("Type", "") or "").strip()
                    if rid and rid not in ids:
                        ids.append(rid)
                    if typ and typ not in types:
                        types.append(typ)
                if active:
                    roles.append("active")

            for it in struct_items:
                if abs(ss - float(it.get("station", 0.0) or 0.0)) > tol:
                    continue
                role = str(it.get("role", "") or "").strip()
                if role and role not in roles:
                    roles.append(role)
                for rid in list(it.get("ids", []) or []):
                    rid_txt = str(rid or "").strip()
                    if rid_txt and rid_txt not in ids:
                        ids.append(rid_txt)
                for typ in list(it.get("types", []) or []):
                    typ_txt = str(typ or "").strip()
                    if typ_txt and typ_txt not in types:
                        types.append(typ_txt)

            has_structure = bool(ids or roles or types)
            role_summary = ",".join(roles)
            type_summary = ",".join(types)
            id_summary = ",".join(ids)
            out.append(
                {
                    "HasStructure": has_structure,
                    "StructureIds": ids,
                    "StructureTypes": types,
                    "StructureRoles": roles,
                    "StructureRole": role_summary,
                    "StructureSummary": f"{id_summary} | {type_summary} | {role_summary}".strip(" |"),
                }
            )
        return out

    @staticmethod
    def _apply_child_structure_visual(ch, meta):
        try:
            vobj = getattr(ch, "ViewObject", None)
            if vobj is None:
                return
            has_structure = bool(meta.get("HasStructure", False))
            roles = list(meta.get("StructureRoles", []) or [])
            if not has_structure:
                return
            color = (0.95, 0.70, 0.18)
            line_width = 3
            if "center" in roles:
                color = (0.86, 0.28, 0.16)
                line_width = 4
            elif "start" in roles or "end" in roles:
                color = (0.95, 0.52, 0.14)
                line_width = 4
            elif "transition_before" in roles or "transition_after" in roles:
                color = (0.92, 0.82, 0.38)
                line_width = 3
            vobj.LineColor = color
            vobj.PointColor = color
            vobj.ShapeColor = color
            vobj.LineWidth = line_width
            vobj.DisplayMode = "Wireframe"
        except Exception:
            pass

    @staticmethod
    def _record_overlay_wire(section_obj, station: float, rec):
        src = getattr(section_obj, "SourceCenterlineDisplay", None)
        if src is None:
            return None
        struct_src = _resolve_structure_source(section_obj)
        try:
            if struct_src is not None and str(rec.get("Id", "") or "").strip():
                resolved = StructureSetSource.resolve_profile_at_station(struct_src, rec, float(station))
                if resolved:
                    rec = resolved
        except Exception:
            pass
        scale = get_length_scale(getattr(section_obj, "Document", None), default=1.0)
        frame = Centerline3D.frame_at_station(src, float(station), eps=0.1 * scale, prev_n=None)
        p = frame["point"]
        n = frame["N"]
        z = frame["Z"]

        width = max(0.2 * scale, abs(float(rec.get("Width", 0.0) or 0.0)))
        height = max(0.2 * scale, abs(float(rec.get("Height", 0.0) or 0.0)))
        bottom = float(rec.get("BottomElevation", 0.0) or 0.0)
        cover = abs(float(rec.get("Cover", 0.0) or 0.0))
        z_ref = float(getattr(p, "z", 0.0) or 0.0)
        if abs(bottom) > 1e-9:
            z0 = bottom
        elif cover > 1e-9:
            z0 = z_ref - cover - height
        else:
            z0 = z_ref

        wires = []
        geom_mode = _overlay_geometry_mode(rec)
        template_name = _overlay_template_name(rec)
        for off in _structure_overlay_offsets(rec):
            c = App.Vector(float(p.x), float(p.y), float(z0)) + (n * float(off))
            if geom_mode == "template" and template_name == "box_culvert":
                wall = max(0.10 * scale, abs(float(rec.get("WallThickness", 0.0) or 0.0)))
                cells = max(1, int(round(float(rec.get("CellCount", 1) or 1))))
                top_cap = max(0.0, abs(float(rec.get("CapHeight", 0.0) or 0.0)))
                total_h = max(0.2 * scale, height + top_cap)
                wires.append(_overlay_rect_wire(c, n, z, width, total_h))
                inner_h = total_h - (2.0 * wall)
                clear_w = width - (2.0 * wall)
                if inner_h > 0.05 * scale and clear_w > 0.05 * scale:
                    gap = wall
                    total_gap = max(0.0, float(cells - 1)) * gap
                    cell_w = (clear_w - total_gap) / float(cells)
                    if cell_w > 0.05 * scale:
                        inner_center = App.Vector(float(c.x), float(c.y), float(z0) + wall)
                        start_center = -0.5 * clear_w + 0.5 * cell_w
                        for i in range(cells):
                            shift = start_center + (float(i) * (cell_w + gap))
                            cell_center = inner_center + (n * shift)
                            wires.append(_overlay_rect_wire(cell_center, n, z, cell_w, inner_h))
            elif geom_mode == "template" and template_name == "utility_crossing":
                wall = max(0.08 * scale, abs(float(rec.get("WallThickness", 0.0) or 0.0)))
                cells = max(1, int(round(float(rec.get("CellCount", 1) or 1))))
                top_cap = max(0.0, abs(float(rec.get("CapHeight", 0.0) or 0.0)))
                total_h = max(0.2 * scale, height + top_cap)
                wires.append(_overlay_rect_wire(c, n, z, width, total_h))
                clear_w = width - (2.0 * wall)
                duct_h = max(0.10 * scale, min(0.45 * total_h, total_h - (2.0 * wall)))
                if clear_w > 0.05 * scale and duct_h > 0.05 * scale:
                    gap = max(0.10 * scale, 0.60 * wall)
                    total_gap = max(0.0, float(cells - 1)) * gap
                    duct_w = (clear_w - total_gap) / float(cells)
                    if duct_w > 0.05 * scale:
                        z_clear_bottom = max(wall, 0.28 * total_h)
                        z_clear_top = z_clear_bottom + duct_h
                        if z_clear_top >= total_h - wall:
                            z_clear_bottom = max(wall, total_h - wall - duct_h)
                        inner_center = App.Vector(float(c.x), float(c.y), float(z0) + z_clear_bottom)
                        start_center = -0.5 * clear_w + 0.5 * duct_w
                        for i in range(cells):
                            shift = start_center + (float(i) * (duct_w + gap))
                            duct_center = inner_center + (n * shift)
                            wires.append(_overlay_rect_wire(duct_center, n, z, duct_w, duct_h))
            elif geom_mode == "template" and template_name == "retaining_wall":
                wall = max(0.10 * scale, abs(float(rec.get("WallThickness", 0.0) or 0.0)))
                footing_w = max(wall * 2.0, abs(float(rec.get("FootingWidth", 0.0) or 0.0)), max(width, wall * 3.0))
                footing_h = max(0.10 * scale, abs(float(rec.get("FootingThickness", 0.0) or 0.0)))
                cap_h = max(0.0, abs(float(rec.get("CapHeight", 0.0) or 0.0)))
                sign = _overlay_signed_side_factor(rec)
                heel = footing_w * 0.65
                toe = footing_w - heel
                top_wall = max(0.08 * scale, wall * 0.70)
                total_h = footing_h + max(0.2 * scale, height)
                coords = [
                    (-sign * toe, 0.0),
                    (sign * heel, 0.0),
                    (sign * heel, footing_h),
                    (sign * (0.5 * wall), footing_h),
                    (sign * (0.5 * top_wall), total_h),
                    (-sign * (0.5 * top_wall), total_h),
                    (-sign * (0.5 * wall), footing_h),
                    (-sign * toe, footing_h),
                ]
                pw = _overlay_profile_wire(App.Vector(float(c.x), float(c.y), float(z0)), n, z, coords)
                if pw is not None:
                    wires.append(pw)
                if cap_h > 1e-9:
                    cap_center = App.Vector(float(c.x), float(c.y), float(z0) + total_h)
                    cap_center = cap_center + (n * (sign * 0.10 * wall))
                    wires.append(_overlay_rect_wire(cap_center, n, z, max(top_wall * 1.8, wall + 0.20 * scale), cap_h))
            elif geom_mode == "template" and template_name == "abutment_block":
                wall = max(0.20 * scale, abs(float(rec.get("WallThickness", 0.0) or 0.0)), max(0.20 * scale, 0.35 * height))
                footing_h = max(0.20 * scale, abs(float(rec.get("FootingThickness", 0.0) or 0.0)), max(0.20 * scale, 0.18 * height))
                footing_w = max(abs(float(rec.get("FootingWidth", 0.0) or 0.0)), width, wall * 2.5)
                cap_h = max(0.0, abs(float(rec.get("CapHeight", 0.0) or 0.0)))
                stem_w = max(wall * 1.4, min(width * 0.55, footing_w * 0.60))
                seat_w = max(stem_w * 0.55, wall * 1.4)
                total_h = footing_h + max(0.2 * scale, height)
                seat_h0 = footing_h + max(0.30 * scale, 0.60 * height)
                coords = [
                    (-0.5 * footing_w, 0.0),
                    (0.5 * footing_w, 0.0),
                    (0.5 * footing_w, footing_h),
                    (0.5 * stem_w, footing_h),
                    (0.5 * stem_w, seat_h0),
                    (0.5 * seat_w, total_h),
                    (-0.5 * seat_w, total_h),
                    (-0.5 * stem_w, seat_h0),
                    (-0.5 * stem_w, footing_h),
                    (-0.5 * footing_w, footing_h),
                ]
                pw = _overlay_profile_wire(App.Vector(float(c.x), float(c.y), float(z0)), n, z, coords)
                if pw is not None:
                    wires.append(pw)
                if cap_h > 1e-9:
                    cap_center = App.Vector(float(c.x), float(c.y), float(z0) + total_h)
                    wires.append(_overlay_rect_wire(cap_center, n, z, max(seat_w * 1.1, seat_w + 0.20 * scale), cap_h))
            else:
                wires.append(_overlay_rect_wire(c, n, z, width, height))
        if not wires:
            return None
        if len(wires) == 1:
            return wires[0]
        try:
            return Part.Compound(wires)
        except Exception:
            return wires[0]

    @staticmethod
    def _build_child_structure_overlay(section_obj, station: float, meta):
        if not bool(meta.get("HasStructure", False)):
            return None
        if not bool(getattr(section_obj, "CreateStructureTaggedChildren", True)):
            return None
        ctx = SectionSet._structure_context_at_station(section_obj, float(station))
        recs = list(ctx.get("OverlayRecords", []) or [])
        if not recs:
            return None
        overlays = []
        for rec in recs:
            try:
                ow = SectionSet._record_overlay_wire(section_obj, float(station), rec)
                if ow is not None and not ow.isNull():
                    overlays.append(ow)
            except Exception:
                pass
        if not overlays:
            return None
        if len(overlays) == 1:
            return overlays[0]
        try:
            return Part.Compound(overlays)
        except Exception:
            return overlays[0]

    @staticmethod
    def _resolve_terrain_source(obj):
        t = getattr(obj, "TerrainMesh", None)
        if _is_mesh_object(t):
            return t

        doc = getattr(obj, "Document", None)
        prj = _find_project(doc)
        if prj is not None:
            pt = getattr(prj, "Terrain", None)
            if _is_mesh_object(pt):
                return pt

        cand = _find_terrain_candidate(doc)
        if cand is not None:
            return cand

        return None

    @staticmethod
    def _triangle_bbox_xy(p0, p1, p2):
        return _ssc.triangle_bbox_xy(p0, p1, p2)

    @staticmethod
    def _to_vec(p):
        return _ssc.to_vec(p)

    @staticmethod
    def _mesh_triangles(mesh_obj):
        return _ssc.mesh_triangles(mesh_obj)

    @staticmethod
    def _shape_triangles(shape_obj, deflection: float = 1.0):
        return _ssc.shape_triangles(shape_obj, deflection=deflection)

    @staticmethod
    def _surface_triangles(src_obj):
        if _is_mesh_object(src_obj):
            return SectionSet._mesh_triangles(src_obj)
        return []

    @staticmethod
    def _build_xy_buckets(triangles, bucket_size: float, max_cells_per_triangle: int = 20000):
        return _ssc.build_xy_buckets(
            triangles,
            bucket_size,
            max_cells_per_triangle=max_cells_per_triangle,
            max_wide_items=5000,
        )

    @staticmethod
    def _point_in_tri_z(x, y, p0, p1, p2):
        return _ssc.point_in_tri_z(x, y, p0, p1, p2)

    @staticmethod
    def _terrain_sampler(src_obj, max_triangles: int = 300000, coord_context=None, coord_mode: str = "Local"):
        tris = SectionSet._surface_triangles(src_obj)
        if not tris:
            return None

        if str(coord_mode or "Local") == "World":
            tris = _ct.triangles_world_to_local(
                tris,
                doc_or_obj=(coord_context if coord_context is not None else src_obj),
            )
            if not tris:
                return None

        mt = int(max(1000, int(max_triangles)))
        tris = _ssc.decimate_triangles(tris, mt)

        scale = get_length_scale(getattr(src_obj, "Document", None), default=1.0)
        bucket = 2.0 * scale
        try:
            n = max(1, len(tris))
            xmin, xmax, ymin, ymax = _ct.triangles_bbox_xy(tris)
            xlen = float(xmax - xmin)
            ylen = float(ymax - ymin)
            area = max((1.0 * scale) ** 2, xlen * ylen)
            bucket = max(0.5 * scale, min(20.0 * scale, math.sqrt(area / float(n)) * 2.0))
        except Exception:
            pass
        buckets, wide = SectionSet._build_xy_buckets(tris, bucket)
        return {
            "triangles": tris,
            "bucket_size": bucket,
            "buckets": buckets,
            "wide_indices": wide,
        }

    @staticmethod
    def _terrain_z_at(sampler, x: float, y: float):
        if sampler is None:
            return None
        tris = sampler["triangles"]
        buckets = sampler["buckets"]
        wide = sampler.get("wide_indices", []) or []
        bs = float(sampler["bucket_size"])
        z0 = _ssc.z_at_xy(float(x), float(y), tris, buckets, bs, wide_indices=wide, max_candidates=None)
        if z0 is not None:
            return z0

        # Fallback for DEM-like meshes with local holes:
        # sample neighboring positions and use nearest available Z.
        step = max(0.2, float(bs))
        dirs = (
            (1.0, 0.0),
            (-1.0, 0.0),
            (0.0, 1.0),
            (0.0, -1.0),
            (0.7071, 0.7071),
            (0.7071, -0.7071),
            (-0.7071, 0.7071),
            (-0.7071, -0.7071),
        )
        best = None
        best_d2 = None
        for ring in (1, 2, 3):
            r = float(ring) * step
            for dx, dy in dirs:
                qx = float(x) + float(dx) * r
                qy = float(y) + float(dy) * r
                zz = _ssc.z_at_xy(float(qx), float(qy), tris, buckets, bs, wide_indices=wide, max_candidates=None)
                if zz is None:
                    continue
                d2 = float((qx - x) * (qx - x) + (qy - y) * (qy - y))
                if best is None or d2 < best_d2:
                    best = float(zz)
                    best_d2 = d2
            if best is not None:
                return best
        return None

    @staticmethod
    def _solve_daylight_width(edge_p, outward_n, up_z, slope_pct: float, max_w: float, sampler, step: float):
        mw = max(0.0, float(max_w))
        if sampler is None or mw <= 1e-9:
            return mw, False

        st = max(0.2, float(step))
        if st > mw:
            st = mw
        if st <= 1e-12:
            return mw, False
        # Keep runtime bounded even when max width is large or step is tiny.
        max_iter = 5000
        est_iter = int(math.ceil(mw / st)) + 1
        if est_iter > max_iter:
            st = max(st, float(mw) / float(max_iter))

        def f_at(w):
            q = edge_p + outward_n * float(w) + up_z * (-float(w) * float(slope_pct) / 100.0)
            zt = SectionSet._terrain_z_at(sampler, q.x, q.y)
            if zt is None:
                return None
            return float(q.z - zt)

        # Daylight policy:
        # - If a sign-change intersection is found, use that root.
        # - If no intersection exists inside [0, max_w], return max_w with hit=False.
        had_sample = False
        prev_w = None
        prev_f = None
        best_w = None
        best_abs_f = None
        w = 0.0
        while w <= mw + 1e-9:
            fv = f_at(w)
            if fv is not None:
                had_sample = True
                af = abs(float(fv))
                if best_abs_f is None or af < best_abs_f:
                    best_abs_f = af
                    best_w = float(w)
                if prev_f is not None and (prev_f == 0.0 or fv == 0.0 or (prev_f > 0.0 and fv < 0.0) or (prev_f < 0.0 and fv > 0.0)):
                    if prev_w is None:
                        return w, True
                    den = (fv - prev_f)
                    if abs(den) <= 1e-12:
                        return w, True
                    t = -prev_f / den
                    return max(0.0, min(mw, prev_w + (w - prev_w) * t)), True
                prev_w = w
                prev_f = fv
            w += st

        if not had_sample:
            return mw, False
        # If sampled but no explicit sign change was found, use nearest approach.
        if best_w is not None:
            return max(0.0, min(mw, float(best_w))), True
        return mw, False

    @staticmethod
    def _daylight_signed_slope(edge_p, slope_pct: float, sampler):
        """
        Resolve cut/fill side-slope direction automatically for daylight:
        - terrain above edge -> cut slope (upward outward)  -> negative slope_pct
        - terrain below edge -> fill slope (downward outward) -> positive slope_pct
        If terrain cannot be sampled, keep user-provided sign.
        """
        s = float(slope_pct)
        mag = abs(s)
        if mag <= 1e-9:
            return 0.0

        sign_user = -1.0 if s < 0.0 else 1.0
        if sampler is None:
            return sign_user * mag

        zt = SectionSet._terrain_z_at(sampler, float(edge_p.x), float(edge_p.y))
        if zt is None:
            return sign_user * mag

        tol = 1e-3
        if float(zt) > float(edge_p.z) + tol:
            # Cut condition: terrain is above road edge -> slope goes upward outward.
            return -mag
        if float(zt) < float(edge_p.z) - tol:
            # Fill condition: terrain is below road edge -> slope goes downward outward.
            return +mag
        return sign_user * mag

    @staticmethod
    def _stabilize_daylight_width(target_w: float, prev_w, max_delta: float, min_w: float, max_w: float):
        w = _clamp(float(target_w), float(min_w), float(max_w))
        if prev_w is None:
            return w
        md = max(0.0, float(max_delta))
        if md <= 1e-9:
            return w
        lo = max(float(min_w), float(prev_w) - md)
        hi = min(float(max_w), float(prev_w) + md)
        return _clamp(w, lo, hi)

    @staticmethod
    def build_section_wire(
        source_obj,
        asm_obj,
        station: float,
        prev_n: App.Vector = None,
        prev_day_widths=None,
        terrain_sampler=None,
        use_daylight: bool = False,
        structure_context=None,
        apply_structure_overrides: bool = False,
        typical_section_obj=None,
        use_typical_section: bool = False,
    ):
        scale = get_length_scale(getattr(source_obj, "Document", None), default=1.0)
        stub_side_w = max(0.01, 0.01 * scale)
        frame = Centerline3D.frame_at_station(source_obj, float(station), eps=0.1 * scale, prev_n=prev_n)
        p = frame["point"]
        n = frame["N"]
        z = frame["Z"]

        lw = max(0.0, float(getattr(asm_obj, "LeftWidth", 0.0)))
        rw = max(0.0, float(getattr(asm_obj, "RightWidth", 0.0)))
        ls = float(getattr(asm_obj, "LeftSlopePct", 0.0))
        rs = float(getattr(asm_obj, "RightSlopePct", 0.0))
        use_ss = bool(getattr(asm_obj, "UseSideSlopes", False))
        lsw = max(0.0, float(getattr(asm_obj, "LeftSideWidth", 0.0)))
        rsw = max(0.0, float(getattr(asm_obj, "RightSideWidth", 0.0)))
        lss = float(getattr(asm_obj, "LeftSideSlopePct", 0.0))
        rss = float(getattr(asm_obj, "RightSideSlopePct", 0.0))
        use_day = bool(use_daylight) and bool(use_ss) and ((lsw > 1e-9) or (rsw > 1e-9))
        left_has_side = bool(use_ss) and lsw > 1e-9
        right_has_side = bool(use_ss) and rsw > 1e-9
        left_action = "keep"
        right_action = "keep"
        left_spec = None
        right_spec = None
        use_day_left = bool(use_day and left_has_side)
        use_day_right = bool(use_day and right_has_side)
        if bool(apply_structure_overrides) and structure_context is not None:
            left_action = str(structure_context.get("LeftAction", "keep") or "keep").strip().lower()
            right_action = str(structure_context.get("RightAction", "keep") or "keep").strip().lower()
            left_spec = structure_context.get("LeftOverrideSpec")
            right_spec = structure_context.get("RightOverrideSpec")
            if bool(structure_context.get("SuppressSideSlopes", False)):
                # Preserve the section point contract for loft consumers by keeping
                # side-slope vertices present as short horizontal stubs.
                use_ss = bool(left_has_side or right_has_side)
                if left_has_side:
                    lsw = min(lsw, stub_side_w)
                    lss = 0.0
                else:
                    lsw = 0.0
                if right_has_side:
                    rsw = min(rsw, stub_side_w)
                    rss = 0.0
                else:
                    rsw = 0.0
            if bool(structure_context.get("SuppressDaylight", False)):
                use_day_left = False
                use_day_right = False
            if left_action == "stub" and left_has_side:
                lsw = min(lsw, stub_side_w)
                lss = 0.0
                use_day_left = False
                use_ss = True
            if right_action == "stub" and right_has_side:
                rsw = min(rsw, stub_side_w)
                rss = 0.0
                use_day_right = False
                use_ss = True
            if bool(structure_context.get("LeftDisableDaylight", False)):
                use_day_left = False
            if bool(structure_context.get("RightDisableDaylight", False)):
                use_day_right = False

        def _apply_side_override(base_w, base_s, has_side, action, spec, use_day_side):
            if (not has_side) or action == "keep":
                return base_w, base_s, use_day_side

            target_w = 0.0
            slope_mode = "same"
            steep_slope = 0.0
            if spec is not None:
                try:
                    target_w = float(spec.get("TargetWidth", 0.0) or 0.0)
                except Exception:
                    target_w = 0.0
                slope_mode = str(spec.get("SlopeMode", "same") or "same").strip().lower()
                try:
                    steep_slope = float(spec.get("SteepSlopePct", 0.0) or 0.0)
                except Exception:
                    steep_slope = 0.0

            resolved_w = float(base_w)
            resolved_s = float(base_s)
            sign = _slope_sign(base_s, fallback=1.0)

            if action == "stub":
                resolved_w = min(resolved_w, max(stub_side_w, target_w if target_w > 1e-9 else stub_side_w))
                resolved_s = 0.0
                use_day_side = False
            elif action in ("bench", "berm"):
                target = max(1.0 * scale, target_w if target_w > 1e-9 else max(stub_side_w, 0.20 * resolved_w))
                resolved_w = min(resolved_w, target) if resolved_w > 1e-9 else target
                resolved_s = 0.0
                use_day_side = False
            elif action == "trim":
                target = max(stub_side_w, target_w if target_w > 1e-9 else max(0.50 * scale, 0.35 * resolved_w))
                resolved_w = min(resolved_w, target) if resolved_w > 1e-9 else target
                resolved_s = 0.0 if slope_mode == "flat" else float(base_s)
                use_day_side = False
            elif action == "wall":
                target = max(0.20 * scale, target_w if target_w > 1e-9 else max(0.35 * scale, 0.15 * resolved_w))
                resolved_w = min(resolved_w, target) if resolved_w > 1e-9 else target
                steep = max(abs(steep_slope), abs(float(base_s)), 250.0)
                resolved_s = sign * steep
                use_day_side = False

            return resolved_w, resolved_s, use_day_side

        if bool(apply_structure_overrides) and structure_context is not None:
            lsw, lss, use_day_left = _apply_side_override(lsw, lss, left_has_side, left_action, left_spec, use_day_left)
            rsw, rss, use_day_right = _apply_side_override(rsw, rss, right_has_side, right_action, right_spec, use_day_right)
        day_step = max(0.2 * scale, float(getattr(asm_obj, "DaylightSearchStep", 1.0 * scale)))
        day_max_w = max(0.0, float(getattr(asm_obj, "DaylightMaxSearchWidth", 200.0 * scale)))
        day_max_delta = max(0.0, float(getattr(asm_obj, "DaylightMaxWidthDelta", 0.0)))
        prev_left_w = None if prev_day_widths is None else prev_day_widths.get("left")
        prev_right_w = None if prev_day_widths is None else prev_day_widths.get("right")

        top_pts = None
        p_l = None
        p_r = None
        if bool(use_typical_section) and typical_section_obj is not None:
            try:
                local_pts = list(_build_typical_top_profile(typical_section_obj) or [])
                if len(local_pts) >= 2:
                    top_pts = [p + n * float(lp.x) + z * float(lp.y) for lp in local_pts]
                    p_l = top_pts[0]
                    p_r = top_pts[-1]
            except Exception:
                top_pts = None
                p_l = None
                p_r = None

        if top_pts is None:
            dz_l = -lw * ls / 100.0
            dz_r = -rw * rs / 100.0
            p_l = p + n * lw + z * dz_l
            p_r = p - n * rw + z * dz_r
            top_pts = [p_l, p, p_r]

        lss_eff = float(lss)
        rss_eff = float(rss)
        if use_day_left:
            lss_eff = SectionSet._daylight_signed_slope(p_l, lss, terrain_sampler)
        if use_day_right:
            rss_eff = SectionSet._daylight_signed_slope(p_r, rss, terrain_sampler)

        pts = list(top_pts)
        resolved_left_w = None
        resolved_right_w = None
        if use_ss and lsw > 1e-9:
            w_l = lsw
            if use_day_left:
                try:
                    search_w_l = max(lsw, day_max_w)
                    w_l_day, hit_l = SectionSet._solve_daylight_width(
                        p_l, n, z, lss_eff, search_w_l, terrain_sampler, day_step
                    )
                    w_l = w_l_day if hit_l else lsw
                    w_l = SectionSet._stabilize_daylight_width(
                        w_l,
                        prev_left_w,
                        day_max_delta,
                        0.01 if lsw > 1e-9 else 0.0,
                        search_w_l,
                    )
                except Exception:
                    # Fail-safe: never block section creation due to daylight solve failure.
                    w_l = max(0.01 if lsw > 1e-9 else 0.0, lsw)
            else:
                w_l = max(0.01 if lsw > 1e-9 else 0.0, min(lsw, w_l))
            resolved_left_w = float(w_l)
            p_lt = p_l + n * w_l + z * (-w_l * lss_eff / 100.0)
            pts = [p_lt] + pts
        if use_ss and rsw > 1e-9:
            w_r = rsw
            if use_day_right:
                try:
                    search_w_r = max(rsw, day_max_w)
                    w_r_day, hit_r = SectionSet._solve_daylight_width(
                        p_r, -n, z, rss_eff, search_w_r, terrain_sampler, day_step
                    )
                    w_r = w_r_day if hit_r else rsw
                    w_r = SectionSet._stabilize_daylight_width(
                        w_r,
                        prev_right_w,
                        day_max_delta,
                        0.01 if rsw > 1e-9 else 0.0,
                        search_w_r,
                    )
                except Exception:
                    # Fail-safe: never block section creation due to daylight solve failure.
                    w_r = max(0.01 if rsw > 1e-9 else 0.0, rsw)
            else:
                w_r = max(0.01 if rsw > 1e-9 else 0.0, min(rsw, w_r))
            resolved_right_w = float(w_r)
            p_rt = p_r - n * w_r + z * (-w_r * rss_eff / 100.0)
            pts = pts + [p_rt]

        w = Part.makePolygon(pts)
        return w, n, {"left": resolved_left_w, "right": resolved_right_w}

    @staticmethod
    def build_section_wires(obj):
        src = getattr(obj, "SourceCenterlineDisplay", None)
        asm = getattr(obj, "AssemblyTemplate", None)
        typ = getattr(obj, "TypicalSectionTemplate", None) if hasattr(obj, "TypicalSectionTemplate") else None
        if src is None:
            raise Exception("SourceCenterlineDisplay is missing.")
        if asm is None:
            raise Exception("AssemblyTemplate is missing.")

        stations = list(getattr(obj, "StationValues", []) or [])
        if len(stations) < 1:
            stations = SectionSet.resolve_station_values(obj)
        if len(stations) < 1:
            return [], [], False, False

        terrain_sampler = None
        terrain_found = False
        use_ss = bool(getattr(asm, "UseSideSlopes", False))
        lsw = max(0.0, float(getattr(asm, "LeftSideWidth", 0.0)))
        rsw = max(0.0, float(getattr(asm, "RightSideWidth", 0.0)))
        use_day = bool(getattr(obj, "DaylightAuto", True)) and bool(use_ss) and ((lsw > 1e-9) or (rsw > 1e-9))
        try:
            if use_day:
                tsrc = SectionSet._resolve_terrain_source(obj)
                terrain_found = tsrc is not None
                if tsrc is not None:
                    day_max = int(getattr(asm, "DaylightMaxTriangles", 300000))
                    terrain_mode = str(getattr(obj, "TerrainMeshCoords", "Local") or "Local")
                    # Prefer explicit source declaration when available.
                    src_mode = str(getattr(tsrc, "OutputCoords", "") or "")
                    if src_mode in ("Local", "World"):
                        terrain_mode = src_mode
                    if terrain_mode not in ("Local", "World"):
                        terrain_mode = "Local"
                    terrain_sampler = SectionSet._terrain_sampler(
                        tsrc,
                        max_triangles=day_max,
                        coord_context=obj,
                        coord_mode=terrain_mode,
                    )
        except Exception:
            terrain_sampler = None

        wires = []
        prev_n = None
        prev_day_widths = {"left": None, "right": None}
        override_hits = 0
        use_typ = bool(getattr(obj, "UseTypicalSectionTemplate", False)) and typ is not None
        for s in stations:
            structure_context = None
            if bool(getattr(obj, "ApplyStructureOverrides", False)):
                structure_context = SectionSet._structure_context_at_station(obj, float(s))
                if bool(
                    structure_context.get("SuppressSideSlopes", False)
                    or structure_context.get("SuppressDaylight", False)
                    or str(structure_context.get("LeftAction", "keep") or "keep").strip().lower() != "keep"
                    or str(structure_context.get("RightAction", "keep") or "keep").strip().lower() != "keep"
                ):
                    override_hits += 1
            try:
                w, prev_n, prev_day_widths = SectionSet.build_section_wire(
                    src,
                    asm,
                    float(s),
                    prev_n=prev_n,
                    prev_day_widths=prev_day_widths,
                    terrain_sampler=terrain_sampler,
                    use_daylight=use_day,
                    structure_context=structure_context,
                    apply_structure_overrides=bool(getattr(obj, "ApplyStructureOverrides", False)),
                    typical_section_obj=typ,
                    use_typical_section=use_typ,
                )
            except Exception:
                # Per-station fail-safe: fall back to fixed-width side slopes.
                w, prev_n, prev_day_widths = SectionSet.build_section_wire(
                    src,
                    asm,
                    float(s),
                    prev_n=prev_n,
                    prev_day_widths=prev_day_widths,
                    terrain_sampler=None,
                    use_daylight=False,
                    structure_context=structure_context,
                    apply_structure_overrides=bool(getattr(obj, "ApplyStructureOverrides", False)),
                    typical_section_obj=typ,
                    use_typical_section=use_typ,
                )
            wires.append(w)
        try:
            obj._StructureOverrideHitCount = int(override_hits)
        except Exception:
            pass
        return stations, wires, terrain_found, (terrain_sampler is not None)

    @staticmethod
    def clear_child_sections(obj):
        doc = getattr(obj, "Document", None)
        if doc is None:
            return
        group = list(getattr(obj, "Group", []) or [])
        if not group:
            return
        for ch in group:
            try:
                doc.removeObject(ch.Name)
            except Exception:
                pass
        obj.Group = []

    @staticmethod
    def rebuild_child_sections(obj, stations=None, wires=None, station_tags=None, structure_meta=None):
        doc = getattr(obj, "Document", None)
        if doc is None:
            return

        if stations is None or wires is None:
            stations, wires, _tf, _so = SectionSet.build_section_wires(obj)
        if len(stations) != len(wires):
            raise Exception("Child rebuild failed: stations/wires size mismatch.")
        if station_tags is None or len(station_tags) != len(stations):
            station_tags = SectionSet.resolve_station_tags(obj, stations)
        if structure_meta is None or len(structure_meta) != len(stations):
            structure_meta = SectionSet.resolve_structure_metadata(obj, stations)

        SectionSet.clear_child_sections(obj)
        children = []
        for i, (s, w) in enumerate(zip(stations, wires)):
            ch = doc.addObject("Part::Feature", "SectionSlice")
            tags = station_tags[i] if i < len(station_tags) else []
            meta = structure_meta[i] if i < len(structure_meta) else {}
            tag_txt = f" [{'/'.join(tags)}]" if tags else ""
            ch.Label = f"STA {float(s):.3f}{tag_txt}"
            try:
                if not hasattr(ch, "Station"):
                    ch.addProperty("App::PropertyFloat", "Station", "Section", "Station (m)")
                ch.Station = float(s)
            except Exception:
                pass
            try:
                if not hasattr(ch, "ParentSectionSet"):
                    ch.addProperty("App::PropertyLink", "ParentSectionSet", "Section", "Owner SectionSet")
                ch.ParentSectionSet = obj
            except Exception:
                pass
            try:
                if not hasattr(ch, "HasStructure"):
                    ch.addProperty("App::PropertyBool", "HasStructure", "Structure", "Whether this section is structure-aware")
                ch.HasStructure = bool(meta.get("HasStructure", False))
            except Exception:
                pass
            try:
                if not hasattr(ch, "StructureIds"):
                    ch.addProperty("App::PropertyStringList", "StructureIds", "Structure", "Resolved structure IDs at this section")
                ch.StructureIds = list(meta.get("StructureIds", []) or [])
            except Exception:
                pass
            try:
                if not hasattr(ch, "StructureTypes"):
                    ch.addProperty("App::PropertyStringList", "StructureTypes", "Structure", "Resolved structure types at this section")
                ch.StructureTypes = list(meta.get("StructureTypes", []) or [])
            except Exception:
                pass
            try:
                if not hasattr(ch, "StructureRoles"):
                    ch.addProperty("App::PropertyStringList", "StructureRoles", "Structure", "Resolved structure roles at this section")
                ch.StructureRoles = list(meta.get("StructureRoles", []) or [])
            except Exception:
                pass
            try:
                if not hasattr(ch, "StructureRole"):
                    ch.addProperty("App::PropertyString", "StructureRole", "Structure", "Primary structure role summary")
                ch.StructureRole = str(meta.get("StructureRole", "") or "")
            except Exception:
                pass
            try:
                if not hasattr(ch, "StructureSummary"):
                    ch.addProperty("App::PropertyString", "StructureSummary", "Structure", "Structure summary text")
                ch.StructureSummary = str(meta.get("StructureSummary", "") or "")
            except Exception:
                pass
            overlay_shape = SectionSet._build_child_structure_overlay(obj, float(s), meta)
            try:
                if not hasattr(ch, "StructureOverlayCount"):
                    ch.addProperty("App::PropertyInteger", "StructureOverlayCount", "Structure", "Overlay wire count generated for this section")
                if overlay_shape is not None:
                    nw = len(list(getattr(overlay_shape, "Wires", []) or []))
                    ch.StructureOverlayCount = int(max(1, nw))
                else:
                    ch.StructureOverlayCount = 0
            except Exception:
                pass
            # Keep the child section shape as the base section wire only.
            # Corridor loft relies on a stable wire point contract, and embedding
            # structure overlay geometry here can change the interpreted point count.
            ch.Shape = w
            SectionSet._apply_child_structure_visual(ch, meta)
            children.append(ch)
            if overlay_shape is not None:
                try:
                    ov = doc.addObject("Part::Feature", "SectionStructureOverlay")
                    ov.Label = _structure_overlay_label(float(s), meta)
                    try:
                        if not hasattr(ov, "Station"):
                            ov.addProperty("App::PropertyFloat", "Station", "Section", "Section station")
                        ov.Station = float(s)
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "ParentSectionSet"):
                            ov.addProperty("App::PropertyLink", "ParentSectionSet", "Section", "Owner SectionSet")
                        ov.ParentSectionSet = obj
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "ParentSectionSlice"):
                            ov.addProperty("App::PropertyLink", "ParentSectionSlice", "Section", "Owner child section")
                        ov.ParentSectionSlice = ch
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "HasStructure"):
                            ov.addProperty("App::PropertyBool", "HasStructure", "Structure", "Whether this overlay represents resolved structure data")
                        ov.HasStructure = bool(meta.get("HasStructure", False))
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "StructureIds"):
                            ov.addProperty("App::PropertyStringList", "StructureIds", "Structure", "Resolved structure IDs at this section")
                        ov.StructureIds = list(meta.get("StructureIds", []) or [])
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "StructureTypes"):
                            ov.addProperty("App::PropertyStringList", "StructureTypes", "Structure", "Resolved structure types at this section")
                        ov.StructureTypes = list(meta.get("StructureTypes", []) or [])
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "StructureRoles"):
                            ov.addProperty("App::PropertyStringList", "StructureRoles", "Structure", "Resolved structure roles at this section")
                        ov.StructureRoles = list(meta.get("StructureRoles", []) or [])
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "StructureRole"):
                            ov.addProperty("App::PropertyString", "StructureRole", "Structure", "Primary structure role summary")
                        ov.StructureRole = str(meta.get("StructureRole", "") or "")
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "StructureSummary"):
                            ov.addProperty("App::PropertyString", "StructureSummary", "Structure", "Structure summary text")
                        ov.StructureSummary = str(meta.get("StructureSummary", "") or "")
                    except Exception:
                        pass
                    ov.Shape = overlay_shape
                    try:
                        vov = getattr(ov, "ViewObject", None)
                        if vov is not None:
                            vov.DisplayMode = "Wireframe"
                            vov.LineColor = (0.92, 0.35, 0.20)
                            vov.PointColor = (0.92, 0.35, 0.20)
                            vov.ShapeColor = (0.92, 0.35, 0.20)
                            vov.LineWidth = 4
                            vov.Transparency = 0
                        ov.Label = _structure_overlay_label(float(s), meta)
                    except Exception:
                        pass
                    children.append(ov)
                except Exception:
                    pass
        obj.Group = children
        prj = _find_project(doc)
        if prj is not None:
            try:
                from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject

                for child in children:
                    try:
                        CorridorRoadProject.adopt(prj, child)
                    except Exception:
                        pass
            except Exception:
                pass

    def execute(self, obj):
        ensure_section_set_properties(obj)
        try:
            asm = getattr(obj, "AssemblyTemplate", None)
            use_ss = bool(getattr(asm, "UseSideSlopes", False)) if asm is not None else False
            left_on = float(getattr(asm, "LeftSideWidth", 0.0)) > 1e-9 if asm is not None else False
            right_on = float(getattr(asm, "RightSideWidth", 0.0)) > 1e-9 if asm is not None else False
            use_typ = bool(getattr(obj, "UseTypicalSectionTemplate", False)) and getattr(obj, "TypicalSectionTemplate", None) is not None
            # Schema contract:
            # - v1: simple 3-point profile (Left->Center->Right)
            # - v2: extended/open profile with additional break points
            obj.SectionSchemaVersion = 2 if (use_typ or (use_ss and (left_on or right_on))) else 1
            obj.TopProfileSource = "typical_section" if use_typ else "assembly_simple"
            if use_typ:
                typ = getattr(obj, "TypicalSectionTemplate", None)
                left_edge = str(getattr(typ, "LeftEdgeComponentType", "") or "-")
                right_edge = str(getattr(typ, "RightEdgeComponentType", "") or "-")
                obj.TopProfileEdgeSummary = f"{left_edge}/{right_edge}"
                obj.PavementLayerCount = int(getattr(typ, "PavementLayerCount", 0) or 0)
                obj.EnabledPavementLayerCount = int(getattr(typ, "EnabledPavementLayerCount", 0) or 0)
                obj.PavementTotalThickness = float(getattr(typ, "PavementTotalThickness", 0.0) or 0.0)
            else:
                obj.TopProfileEdgeSummary = "-"
                obj.PavementLayerCount = 0
                obj.EnabledPavementLayerCount = 0
                obj.PavementTotalThickness = 0.0
            stations = SectionSet.resolve_station_values(obj)
            obj.StationValues = stations
            obj.SectionCount = len(stations)
            try:
                src0 = getattr(obj, "SourceCenterlineDisplay", None)
                aln0 = getattr(src0, "Alignment", None) if src0 is not None else None
                total0 = float(getattr(getattr(aln0, "Shape", None), "Length", 0.0) or 0.0)
                st_items, st_kind, st_obj = SectionSet._resolve_structure_station_items(
                    obj,
                    total0,
                    mode=str(getattr(obj, "Mode", "Range") or "Range"),
                    s0=float(getattr(obj, "StartStation", 0.0) or 0.0),
                    s1=float(getattr(obj, "EndStation", total0) or total0),
                )
                st_count, st_rows = SectionSet._resolved_structure_summary(st_items)
                obj.ResolvedStructureCount = int(st_count)
                obj.ResolvedStructureTags = list(st_rows)
            except Exception:
                obj.ResolvedStructureCount = 0
                obj.ResolvedStructureTags = []
                st_kind = ""
                st_obj = None

            if not bool(getattr(obj, "ShowSectionWires", True)):
                obj.Shape = Part.Shape()
                obj.Status = "Hidden"
                return

            if len(stations) < 1:
                obj.Shape = Part.Shape()
                obj.Status = "No stations"
                return

            _stations, wires, terrain_found, sampler_ok = SectionSet.build_section_wires(obj)
            if len(wires) < 1:
                obj.Shape = Part.Shape()
                obj.Status = "No section wires"
                return

            if len(wires) == 1:
                obj.Shape = wires[0]
            else:
                obj.Shape = Part.Compound(wires)

            # Keep tree child sections consistent with current template/centerline.
            if bool(getattr(obj, "CreateChildSections", True)):
                need_rebuild = bool(getattr(obj, "AutoRebuildChildren", True)) or bool(getattr(obj, "RebuildNow", False))
                if need_rebuild and (not self._is_rebuilding_children):
                    self._is_rebuilding_children = True
                    try:
                        tags = SectionSet.resolve_station_tags(obj, stations)
                        meta = SectionSet.resolve_structure_metadata(obj, stations)
                        SectionSet.rebuild_child_sections(
                            obj,
                            stations=stations,
                            wires=wires,
                            station_tags=tags,
                            structure_meta=meta,
                        )
                    finally:
                        self._is_rebuilding_children = False
            else:
                if (not self._is_rebuilding_children):
                    self._is_rebuilding_children = True
                    try:
                        SectionSet.clear_child_sections(obj)
                    finally:
                        self._is_rebuilding_children = False

            if bool(getattr(obj, "RebuildNow", False)):
                obj.RebuildNow = False
            use_day = bool(getattr(obj, "DaylightAuto", True)) and bool(use_ss) and (left_on or right_on)
            if use_day and (not terrain_found):
                obj.Status = "WARN: DaylightAuto=True but no terrain source found. Fixed side widths used."
            elif use_day and terrain_found and (not sampler_ok):
                obj.Status = "WARN: Terrain source found but daylight sampler failed. Fixed side widths used."
            else:
                obj.Status = "OK"
            obj.Status = f"{obj.Status} | schema={int(getattr(obj, 'SectionSchemaVersion', 1) or 1)}"
            obj.Status = f"{obj.Status} | topProfile={str(getattr(obj, 'TopProfileSource', 'assembly_simple') or 'assembly_simple')}"
            obj.Status = f"{obj.Status} | topEdges={str(getattr(obj, 'TopProfileEdgeSummary', '-') or '-')}"
            if float(getattr(obj, "PavementTotalThickness", 0.0) or 0.0) > 1e-9:
                obj.Status = f"{obj.Status} | pavement={float(getattr(obj, 'PavementTotalThickness', 0.0) or 0.0):.3f}m"
            struct_src = _resolve_structure_source(obj) if bool(getattr(obj, "UseStructureSet", False)) else None
            if bool(getattr(obj, "UseStructureSet", False)) and struct_src is None:
                obj.Status = f"{obj.Status} | StructureSet missing"
            elif int(getattr(obj, "ResolvedStructureCount", 0) or 0) > 0:
                obj.Status = f"{obj.Status} | structures={int(getattr(obj, 'ResolvedStructureCount', 0) or 0)}"
            if struct_src is not None:
                try:
                    ext_count = sum(
                        1
                        for rec in list(StructureSetSource.records(struct_src) or [])
                        if str(rec.get("GeometryMode", "") or "").strip().lower() == "external_shape"
                    )
                except Exception:
                    ext_count = 0
                if ext_count > 0:
                    obj.Status = f"{obj.Status} | externalShapeDisplayOnly={int(ext_count)}"
            if bool(getattr(obj, "ApplyStructureOverrides", False)):
                ovh = int(getattr(obj, "_StructureOverrideHitCount", 0) or 0)
                obj.Status = f"{obj.Status} | overrides={ovh}"

            # Push parametric updates to linked corridor objects.
            if obj.Document is not None:
                for o in list(obj.Document.Objects):
                    try:
                        if getattr(o, "SourceSectionSet", None) == obj and bool(getattr(o, "AutoUpdate", True)):
                            _mark_corridor_needs_recompute(o)
                    except Exception:
                        pass

        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.SectionCount = 0
            obj.TopProfileEdgeSummary = "-"
            obj.PavementLayerCount = 0
            obj.EnabledPavementLayerCount = 0
            obj.PavementTotalThickness = 0.0
            obj.Status = f"ERROR: {ex}"

    def onChanged(self, obj, prop):
        if bool(getattr(self, "_suspend_recompute", False)):
            return
        if prop in (
            "SourceCenterlineDisplay",
            "AssemblyTemplate",
            "TypicalSectionTemplate",
            "UseTypicalSectionTemplate",
            "TerrainMesh",
            "TerrainMeshCoords",
            "DaylightAuto",
            "Mode",
            "StartStation",
            "EndStation",
            "Interval",
            "StationText",
            "IncludeAlignmentIPStations",
            "IncludeAlignmentSCCSStations",
            "IncludeStructureStations",
            "StructureStationText",
            "StructureSet",
            "UseStructureSet",
            "IncludeStructureStartEnd",
            "IncludeStructureCenters",
            "IncludeStructureTransitionStations",
            "AutoStructureTransitionDistance",
            "StructureTransitionDistance",
            "StructureBufferBefore",
            "StructureBufferAfter",
            "CreateStructureTaggedChildren",
            "ApplyStructureOverrides",
            "CreateChildSections",
            "AutoRebuildChildren",
            "RebuildNow",
            "ShowSectionWires",
        ):
            try:
                obj.touch()
                if prop == "RebuildNow" and bool(getattr(obj, "RebuildNow", False)):
                    if obj.Document is not None:
                        obj.Document.recompute()
            except Exception:
                pass


class ViewProviderSectionSet:
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
