# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import math
import os

import FreeCAD as App

try:
    import Part
except Exception:
    Part = None

from freecad.Corridor_Road.corridor_compat import CORRIDOR_PROXY_TYPE
from freecad.Corridor_Road.objects.doc_query import find_first, find_project
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_centerline3d import Centerline3D
from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.section_strip_builder import (
    make_tri_face as _shared_make_tri_face,
    wire_points as _shared_wire_points,
)


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
ALLOWED_CORRIDOR_MODES = ("", "none", "split_only", "skip_zone", "notch", "boolean_cut")
ALLOWED_GEOMETRY_MODES = ("", "box", "template", "external_shape")
ALLOWED_TEMPLATE_NAMES = ("", "box_culvert", "utility_crossing", "retaining_wall", "abutment_block")
ALLOWED_PLACEMENT_MODES = ("", "center_on_station", "start_on_station")

_EXTERNAL_SHAPE_CACHE = {}
_EXTERNAL_SHAPE_PROXY_CACHE = {}
_PROFILE_LINEAR_FIELDS = (
    "Offset",
    "Width",
    "Height",
    "BottomElevation",
    "Cover",
    "WallThickness",
    "FootingWidth",
    "FootingThickness",
    "CapHeight",
)
_PROFILE_STEP_FIELDS = ("CellCount",)
_RECOMP_LABEL_SUFFIX = " [Recompute]"
_STRUCTURE_LENGTH_SCHEMA_TARGET = 1
_STRUCTURE_LINEAR_RECORD_PROPS = (
    "StartStations",
    "EndStations",
    "CenterStations",
    "Offsets",
    "Widths",
    "Heights",
    "BottomElevations",
    "Covers",
    "WallThicknesses",
    "FootingWidths",
    "FootingThicknesses",
    "CapHeights",
    "CorridorMargins",
)
_STRUCTURE_LINEAR_PROFILE_PROPS = (
    "ProfileStations",
    "ProfileOffsets",
    "ProfileWidths",
    "ProfileHeights",
    "ProfileBottomElevations",
    "ProfileCovers",
    "ProfileWallThicknesses",
    "ProfileFootingWidths",
    "ProfileFootingThicknesses",
    "ProfileCapHeights",
)


def _split_external_shape_source(path: str):
    raw = str(path or "").strip()
    if not raw:
        return "", ""
    if "#" in raw:
        src, obj_name = raw.rsplit("#", 1)
        return os.path.abspath(os.path.expanduser(str(src).strip())), str(obj_name or "").strip()
    return os.path.abspath(os.path.expanduser(raw)), ""


def _empty_shape():
    if Part is None:
        return None
    try:
        return Part.Shape()
    except Exception:
        return None


def _usable_solid(shape, min_volume: float = 1e-9):
    if shape is None:
        return False
    try:
        if shape.isNull():
            return False
    except Exception:
        return False
    try:
        if len(list(getattr(shape, "Solids", []) or [])) > 0:
            return True
    except Exception:
        pass
    try:
        return float(getattr(shape, "Volume", 0.0) or 0.0) > float(min_volume)
    except Exception:
        return False


def _safe_vec(v, fallback):
    try:
        if getattr(v, "Length", 0.0) > 1e-9:
            return v.normalize()
    except Exception:
        pass
    return App.Vector(fallback.x, fallback.y, fallback.z)


def _mark_dependency_needs_recompute(obj_dep, status_text: str):
    proxy_type = str(getattr(getattr(obj_dep, "Proxy", None), "Type", "") or "")
    hide_user_stale_state = proxy_type == CORRIDOR_PROXY_TYPE
    try:
        if hasattr(obj_dep, "NeedsRecompute"):
            obj_dep.NeedsRecompute = True
    except Exception:
        pass
    if not hide_user_stale_state:
        try:
            st = str(getattr(obj_dep, "Status", "") or "")
            if "NEEDS_RECOMPUTE" not in st:
                obj_dep.Status = str(status_text or "NEEDS_RECOMPUTE")
        except Exception:
            pass
        try:
            label = str(getattr(obj_dep, "Label", "") or "")
            if _RECOMP_LABEL_SUFFIX not in label:
                obj_dep.Label = f"{label}{_RECOMP_LABEL_SUFFIX}"
        except Exception:
            pass
    try:
        obj_dep.touch()
    except Exception:
        pass


def _structure_source_matches(section_obj, structure_obj) -> bool:
    try:
        if not bool(getattr(section_obj, "UseStructureSet", False)):
            return False
    except Exception:
        return False

    try:
        from freecad.Corridor_Road.objects.obj_section_set import _resolve_structure_source

        return _resolve_structure_source(section_obj) == structure_obj
    except Exception:
        pass

    try:
        if getattr(section_obj, "StructureSet", None) == structure_obj:
            return True
    except Exception:
        pass

    try:
        prj = find_project(getattr(section_obj, "Document", None))
        if prj is not None and getattr(prj, "StructureSet", None) == structure_obj:
            return True
    except Exception:
        pass
    return False


def _mark_dependents_from_structure_set(structure_obj):
    doc = getattr(structure_obj, "Document", None)
    if doc is None:
        return

    dependent_sections = []
    for o in list(getattr(doc, "Objects", []) or []):
        try:
            proxy_type = str(getattr(getattr(o, "Proxy", None), "Type", "") or "")
            if proxy_type != "SectionSet":
                continue
            if not _structure_source_matches(o, structure_obj):
                continue
            _mark_dependency_needs_recompute(o, "NEEDS_RECOMPUTE: Source StructureSet changed.")
            dependent_sections.append(o)
        except Exception:
            continue

    for sec in dependent_sections:
        for o in list(getattr(doc, "Objects", []) or []):
            try:
                proxy_type = str(getattr(getattr(o, "Proxy", None), "Type", "") or "")
                if getattr(o, "SourceSectionSet", None) == sec:
                    if proxy_type == CORRIDOR_PROXY_TYPE:
                        _mark_dependency_needs_recompute(o, "NEEDS_RECOMPUTE: Source SectionSet changed.")
                        for dep in list(getattr(doc, "Objects", []) or []):
                            try:
                                dep_type = str(getattr(getattr(dep, "Proxy", None), "Type", "") or "")
                                if dep_type == "CutFillCalc" and getattr(dep, "SourceCorridor", None) == o:
                                    _mark_dependency_needs_recompute(dep, "NEEDS_RECOMPUTE: Source corridor changed.")
                            except Exception:
                                continue
                    elif proxy_type == "DesignGradingSurface":
                        _mark_dependency_needs_recompute(o, "NEEDS_RECOMPUTE: Source SectionSet changed.")
                        for dep in list(getattr(doc, "Objects", []) or []):
                            try:
                                dep_type = str(getattr(getattr(dep, "Proxy", None), "Type", "") or "")
                                if dep_type == "DesignTerrain" and getattr(dep, "SourceDesignSurface", None) == o:
                                    _mark_dependency_needs_recompute(dep, "NEEDS_RECOMPUTE: Source DesignGradingSurface changed.")
                            except Exception:
                                continue
            except Exception:
                continue


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


def _resolve_station_frame(obj, station: float, aln=None, prev_n=None):
    frame_eps = _units.model_length_from_meters(getattr(obj, "Document", None), 0.1)
    src3d = _resolve_centerline_source(obj)
    if src3d is not None:
        try:
            frame = Centerline3D.frame_at_station(src3d, float(station), eps=frame_eps, prev_n=prev_n)
            if frame is not None:
                return {
                    "point": frame.get("point", App.Vector(0.0, 0.0, 0.0)),
                    "T": _safe_vec(frame.get("T", App.Vector(1.0, 0.0, 0.0)), App.Vector(1.0, 0.0, 0.0)),
                    "N": _safe_vec(frame.get("N", App.Vector(0.0, 1.0, 0.0)), App.Vector(0.0, 1.0, 0.0)),
                    "Z": _safe_vec(frame.get("Z", App.Vector(0.0, 0.0, 1.0)), App.Vector(0.0, 0.0, 1.0)),
                    "source": "centerline3d",
                }
        except Exception:
            pass

    if aln is None:
        aln = _resolve_alignment(obj)
    if aln is not None:
        try:
            p = HorizontalAlignment.point_at_station(aln, float(station))
            t = _safe_vec(HorizontalAlignment.tangent_at_station(aln, float(station)), App.Vector(1.0, 0.0, 0.0))
            n = _safe_vec(HorizontalAlignment.normal_at_station(aln, float(station)), App.Vector(0.0, 1.0, 0.0))
            z = App.Vector(0.0, 0.0, 1.0)
            return {
                "point": p,
                "T": t,
                "N": n,
                "Z": z,
                "source": "alignment",
            }
        except Exception:
            pass

    return {
        "point": App.Vector(0.0, 0.0, 0.0),
        "T": App.Vector(1.0, 0.0, 0.0),
        "N": App.Vector(0.0, 1.0, 0.0),
        "Z": App.Vector(0.0, 0.0, 1.0),
        "source": "fallback",
    }


def _station_for_record(rec):
    sc = float(rec.get("CenterStation", 0.0) or 0.0)
    s0 = float(rec.get("StartStation", 0.0) or 0.0)
    s1 = float(rec.get("EndStation", 0.0) or 0.0)
    if sc > 0.0:
        return sc
    if s1 > s0:
        return 0.5 * (s0 + s1)
    return s0


def _side_offsets(rec, doc_or_obj=None):
    side = str(rec.get("Side", "") or "").strip().lower()
    off = _model_length(doc_or_obj, float(rec.get("Offset", 0.0) or 0.0))
    width = abs(_model_length(doc_or_obj, float(rec.get("Width", 0.0) or 0.0)))
    sep = max(abs(off), 0.5 * width, _model_length(doc_or_obj, 0.5))
    if side == "left":
        return [off if abs(off) > 1e-9 else sep]
    if side == "right":
        return [off if abs(off) > 1e-9 else -sep]
    if side == "both":
        return [-sep, sep]
    return [off]


def _record_transition_distance(obj, rec, auto_transition: bool = True, transition: float = 0.0):
    default_transition = 5.0
    retaining_wall_transition = 3.0
    bridge_transition = 10.0
    width = max(0.0, abs(float(rec.get("Width", 0.0) or 0.0)))
    height = max(0.0, abs(float(rec.get("Height", 0.0) or 0.0)))
    typ = str(rec.get("Type", "") or "").strip().lower()

    if not bool(auto_transition):
        return max(0.0, float(transition))

    if typ in ("culvert", "crossing"):
        return max(default_transition, 0.75 * width, 1.50 * height)
    if typ == "retaining_wall":
        return max(retaining_wall_transition, 0.50 * width, 1.00 * height)
    if typ in ("bridge_zone", "abutment_zone"):
        return max(bridge_transition, 0.50 * width, 1.00 * height)
    return max(default_transition, 0.50 * width, 1.00 * height)


def _default_corridor_mode(rec, fallback: str = "split_only"):
    typ = str(rec.get("Type", "") or "").strip().lower()
    mode = str(rec.get("CorridorMode", "") or "").strip().lower()
    if mode in ALLOWED_CORRIDOR_MODES:
        return mode or str(fallback or "split_only").strip().lower()
    if typ in ("culvert", "crossing", "bridge_zone", "abutment_zone"):
        return "skip_zone"
    if typ == "retaining_wall":
        return "split_only"
    return "none"


def _default_geometry_mode(rec, fallback: str = "box"):
    mode = str(rec.get("GeometryMode", "") or "").strip().lower()
    if mode in ALLOWED_GEOMETRY_MODES:
        return mode or str(fallback or "box").strip().lower()
    name = str(rec.get("TemplateName", "") or "").strip().lower()
    if name:
        return "template"
    return "box"


def _default_template_name(rec):
    name = str(rec.get("TemplateName", "") or "").strip().lower()
    if name in ALLOWED_TEMPLATE_NAMES:
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


def _signed_side_factor(rec):
    side = str(rec.get("Side", "") or "").strip().lower()
    if side == "left":
        return 1.0
    if side == "right":
        return -1.0
    off = float(rec.get("Offset", 0.0) or 0.0)
    if off < -1e-9:
        return -1.0
    return 1.0


def _face_from_rect(base, t, n, length: float, width: float):
    half_l = 0.5 * max(1e-6, float(length))
    half_w = 0.5 * max(1e-6, float(width))
    p1 = base - (t * half_l) - (n * half_w)
    p2 = base + (t * half_l) - (n * half_w)
    p3 = base + (t * half_l) + (n * half_w)
    p4 = base - (t * half_l) + (n * half_w)
    return Part.Face(Part.makePolygon([p1, p2, p3, p4, p1]))


def _build_box_geometry(base_pt, t, n, length: float, width: float, height: float, z0: float):
    base = App.Vector(float(base_pt.x), float(base_pt.y), float(z0))
    face = _face_from_rect(base, t, n, length, width)
    return face.extrude(App.Vector(0, 0, max(1e-6, float(height))))


def _resolved_bottom_z(base_pt, rec, height: float, doc_or_obj=None):
    z0_raw = _model_length(doc_or_obj, float(rec.get("BottomElevation", 0.0) or 0.0))
    cover = abs(_model_length(doc_or_obj, float(rec.get("Cover", 0.0) or 0.0)))
    z_ref = float(getattr(base_pt, "z", 0.0) or 0.0)
    if abs(z0_raw) > 1e-9:
        return z0_raw
    if cover > 1e-9:
        return z_ref - cover - float(height)
    return z_ref


def _make_profile_wire(origin, nvec, zvec, coords_nz):
    pts = []
    for nn, zz in list(coords_nz or []):
        pts.append(origin + (nvec * float(nn)) + (zvec * float(zz)))
    if not pts:
        return None
    if (pts[0] - pts[-1]).Length > 1e-9:
        pts.append(pts[0])
    return Part.makePolygon(pts)


def _outer_profile_coords_nz(rec, doc_or_obj=None):
    width = abs(_model_length(doc_or_obj, float(rec.get("Width", 0.0) or 0.0)))
    height = abs(_model_length(doc_or_obj, float(rec.get("Height", 0.0) or 0.0)))
    wall = max(_model_length(doc_or_obj, 0.10), abs(_model_length(doc_or_obj, float(rec.get("WallThickness", 0.0) or 0.0))))
    footing_w = max(abs(_model_length(doc_or_obj, float(rec.get("FootingWidth", 0.0) or 0.0))), width, wall * 2.5)
    footing_h = max(_model_length(doc_or_obj, 0.10), abs(_model_length(doc_or_obj, float(rec.get("FootingThickness", 0.0) or 0.0))))
    cap_h = max(0.0, abs(_model_length(doc_or_obj, float(rec.get("CapHeight", 0.0) or 0.0))))
    geom_mode = _default_geometry_mode(rec, fallback="box")
    template_name = _default_template_name(rec)

    if geom_mode == "template" and template_name == "retaining_wall":
        sign = _signed_side_factor(rec)
        wall = max(0.10, wall, max(0.10, 0.60 * width))
        footing_w = max(wall * 2.5, footing_w, max(width * 2.0, wall * 4.0))
        heel = footing_w * 0.65
        toe = footing_w - heel
        top_wall = max(0.08, wall * 0.70)
        total_h = footing_h + max(0.10, height)
        return [
            (-sign * toe, 0.0),
            (sign * heel, 0.0),
            (sign * heel, footing_h),
            (sign * (0.5 * wall), footing_h),
            (sign * (0.5 * top_wall), total_h),
            (-sign * (0.5 * top_wall), total_h),
            (-sign * (0.5 * wall), footing_h),
            (-sign * toe, footing_h),
        ]

    if geom_mode == "template" and template_name == "abutment_block":
        wall = max(0.20, wall, max(0.20, 0.35 * height))
        footing_h = max(0.20, footing_h, max(0.20, 0.18 * height))
        footing_w = max(footing_w, wall * 2.5)
        stem_w = max(wall * 1.4, min(width * 0.55, footing_w * 0.60))
        seat_w = max(stem_w * 0.55, wall * 1.4)
        total_h = footing_h + max(0.20, height)
        seat_h0 = footing_h + max(0.30, 0.60 * height)
        return [
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

    total_h = max(1e-6, height + cap_h)
    half_w = 0.5 * max(1e-6, width)
    return [
        (-half_w, 0.0),
        (half_w, 0.0),
        (half_w, total_h),
        (-half_w, total_h),
    ]


def _section_wire_for_profile_record(base_pt, normal, zvec, rec, doc_or_obj=None):
    coords = _outer_profile_coords_nz(rec, doc_or_obj=doc_or_obj)
    height = abs(_model_length(doc_or_obj, float(rec.get("Height", 0.0) or 0.0)))
    z0 = _resolved_bottom_z(base_pt, rec, height, doc_or_obj=doc_or_obj)
    origin = App.Vector(float(base_pt.x), float(base_pt.y), float(z0))
    return _make_profile_wire(origin, normal, zvec, coords)


def _wire_loop_points(wire):
    pts = [App.Vector(float(p.x), float(p.y), float(p.z)) for p in list(_shared_wire_points(wire) or [])]
    if len(pts) >= 2 and (pts[0] - pts[-1]).Length <= 1e-9:
        pts = pts[:-1]
    return pts


def _face_from_loop_points(points):
    pts = [App.Vector(float(p.x), float(p.y), float(p.z)) for p in list(points or [])]
    if len(pts) < 3:
        return None
    if (pts[0] - pts[-1]).Length > 1e-9:
        pts.append(pts[0])
    try:
        face = Part.Face(Part.makePolygon(pts))
        if face is None or face.isNull():
            return None
        return face
    except Exception:
        return None


def _build_profile_pair_solid(wire0, wire1):
    if Part is None:
        return None

    pts0 = _wire_loop_points(wire0)
    pts1 = _wire_loop_points(wire1)
    if len(pts0) < 3 or len(pts1) < 3:
        raise Exception("Profile pair has insufficient closed-loop points.")
    if len(pts0) != len(pts1):
        raise Exception(f"Profile pair point-count mismatch ({len(pts0)} vs {len(pts1)})")

    faces = []
    cap0 = _face_from_loop_points(pts0)
    cap1 = _face_from_loop_points(list(reversed(pts1)))
    if cap0 is None or cap1 is None:
        raise Exception("Profile pair cap face construction failed.")
    faces.extend([cap0, cap1])

    count = len(pts0)
    for idx in range(count):
        p00 = pts0[idx]
        p01 = pts0[(idx + 1) % count]
        p10 = pts1[idx]
        p11 = pts1[(idx + 1) % count]

        try:
            quad = Part.Face(Part.makePolygon([p00, p01, p11, p10, p00]))
            if quad is not None and not quad.isNull():
                faces.append(quad)
                continue
        except Exception:
            pass

        tri0 = _shared_make_tri_face(p00, p01, p11)
        tri1 = _shared_make_tri_face(p00, p11, p10)
        if tri0 is not None:
            faces.append(tri0)
        if tri1 is not None:
            faces.append(tri1)

    if len(faces) < 4:
        raise Exception("Profile pair shell produced insufficient faces.")

    shell = None
    make_shell = getattr(Part, "makeShell", None)
    if callable(make_shell):
        try:
            shell = make_shell(faces)
        except Exception:
            shell = None
    if shell is None:
        try:
            shell = Part.Shell(faces)
        except Exception as ex:
            raise Exception(f"Profile pair shell construction failed: {ex}")
    if shell is None or shell.isNull():
        raise Exception("Profile pair shell construction returned null.")

    make_solid = getattr(Part, "makeSolid", None)
    if callable(make_solid):
        try:
            solid = make_solid(shell)
            if _usable_solid(solid):
                return solid
        except Exception:
            pass
    try:
        solid = Part.Solid(shell)
        if _usable_solid(solid):
            return solid
    except Exception:
        pass
    raise Exception("Profile pair solid construction produced no usable solid.")


def _build_box_culvert_template(base_pt, t, n, rec, length: float, width: float, height: float, z0: float, doc_or_obj=None):
    wall = max(_model_length(doc_or_obj, 0.10), abs(_model_length(doc_or_obj, float(rec.get("WallThickness", 0.0) or 0.0))))
    cells = max(1, int(round(float(rec.get("CellCount", 1) or 1))))
    top_cap = max(0.0, abs(_model_length(doc_or_obj, float(rec.get("CapHeight", 0.0) or 0.0))))
    outer = _build_box_geometry(base_pt, t, n, length, width, height + top_cap, z0)
    if outer is None or outer.isNull():
        return outer

    inner_height = max(0.10, float(height + top_cap) - (2.0 * wall))
    if width <= (2.0 * wall + 0.10):
        return outer

    clear_width = max(0.10, float(width) - (2.0 * wall))
    cell_gap = wall
    total_gap = max(0.0, float(cells - 1)) * cell_gap
    cell_width = (clear_width - total_gap) / float(cells)
    if cell_width <= 0.05:
        return outer

    cutters = []
    center_base = App.Vector(float(base_pt.x), float(base_pt.y), float(z0) + wall)
    start_center = -0.5 * clear_width + 0.5 * cell_width
    for i in range(cells):
        center_shift = start_center + (float(i) * (cell_width + cell_gap))
        cell_center = center_base + (n * center_shift)
        cut = _build_box_geometry(cell_center, t, n, max(0.01, length - 0.02), cell_width, inner_height, float(cell_center.z))
        if cut is not None and not cut.isNull():
            cutters.append(cut)

    out = outer
    for cut in cutters:
        try:
            out = out.cut(cut)
        except Exception:
            return outer
    if not _usable_solid(out):
        return outer
    return out


def _build_utility_crossing_template(base_pt, t, n, rec, length: float, width: float, height: float, z0: float, doc_or_obj=None):
    wall = max(_model_length(doc_or_obj, 0.08), abs(_model_length(doc_or_obj, float(rec.get("WallThickness", 0.0) or 0.0))))
    cells = max(1, int(round(float(rec.get("CellCount", 1) or 1))))
    top_cap = max(0.0, abs(_model_length(doc_or_obj, float(rec.get("CapHeight", 0.0) or 0.0))))
    outer = _build_box_geometry(base_pt, t, n, length, width, height + top_cap, z0)
    if outer is None or outer.isNull():
        return outer

    total_h = float(height + top_cap)
    clear_w = max(0.10, float(width) - (2.0 * wall))
    duct_h = max(0.10, min(0.45 * total_h, total_h - (2.0 * wall)))
    if clear_w <= 0.10 or duct_h <= 0.05:
        return outer

    gap = max(0.10, 0.60 * wall)
    total_gap = max(0.0, float(cells - 1)) * gap
    duct_w = (clear_w - total_gap) / float(cells)
    if duct_w <= 0.05:
        return outer

    z_clear_bottom = max(wall, 0.28 * total_h)
    z_clear_top = z_clear_bottom + duct_h
    if z_clear_top >= total_h - wall:
        z_clear_bottom = max(wall, total_h - wall - duct_h)
    center_base = App.Vector(float(base_pt.x), float(base_pt.y), float(z0) + z_clear_bottom)
    start_center = -0.5 * clear_w + 0.5 * duct_w

    out = outer
    for i in range(cells):
        center_shift = start_center + (float(i) * (duct_w + gap))
        duct_center = center_base + (n * center_shift)
        cut = _build_box_geometry(
            duct_center,
            t,
            n,
            max(0.01, length - 0.02),
            duct_w,
            duct_h,
            float(duct_center.z),
        )
        if cut is None or cut.isNull():
            continue
        try:
            out = out.cut(cut)
        except Exception:
            return outer
    if not _usable_solid(out):
        return outer
    return out


def _build_retaining_wall_template(base_pt, t, n, rec, length: float, width: float, height: float, z0: float, doc_or_obj=None):
    wall = max(
        _model_length(doc_or_obj, 0.10),
        abs(_model_length(doc_or_obj, float(rec.get("WallThickness", 0.0) or 0.0))),
        max(_model_length(doc_or_obj, 0.10), 0.60 * width),
    )
    footing_w = max(wall * 2.5, abs(_model_length(doc_or_obj, float(rec.get("FootingWidth", 0.0) or 0.0))), max(width * 2.0, wall * 4.0))
    footing_h = max(_model_length(doc_or_obj, 0.10), abs(_model_length(doc_or_obj, float(rec.get("FootingThickness", 0.0) or 0.0))))
    cap_h = max(0.0, abs(_model_length(doc_or_obj, float(rec.get("CapHeight", 0.0) or 0.0))))
    sign = _signed_side_factor(rec)

    heel = footing_w * 0.65
    toe = footing_w - heel
    top_wall = max(0.08, wall * 0.70)
    cap_w = max(top_wall * 1.8, wall + 0.20)
    total_h = footing_h + max(0.10, height)

    # Positive local-N points to the retained side for left walls and flips for right walls.
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
    center_origin = App.Vector(float(base_pt.x), float(base_pt.y), float(z0))
    origin = center_origin - (t * (0.5 * max(1e-6, float(length))))
    wire = _make_profile_wire(origin, n, App.Vector(0, 0, 1), coords)
    if wire is None:
        return None
    try:
        face = Part.Face(wire)
        wall_solid = face.extrude(t * max(1e-6, float(length)))
    except Exception:
        return _build_box_geometry(base_pt, t, n, length, footing_w, total_h, z0)

    solids = [wall_solid]
    if cap_h > 1e-6:
        cap_center = center_origin + (App.Vector(0, 0, total_h))
        cap_center = cap_center + (n * (sign * 0.10 * wall))
        cap = _build_box_geometry(cap_center, t, n, length, cap_w, cap_h, float(cap_center.z))
        if cap is not None and not cap.isNull():
            solids.append(cap)
    if len(solids) == 1:
        return solids[0] if _usable_solid(solids[0]) else _build_box_geometry(base_pt, t, n, length, footing_w, total_h, z0)
    try:
        out = Part.makeCompound(solids)
        if _usable_solid(out):
            return out
    except Exception:
        pass
    return _build_box_geometry(base_pt, t, n, length, footing_w, total_h, z0)


def _build_abutment_block_template(base_pt, t, n, rec, length: float, width: float, height: float, z0: float, doc_or_obj=None):
    wall = max(
        _model_length(doc_or_obj, 0.20),
        abs(_model_length(doc_or_obj, float(rec.get("WallThickness", 0.0) or 0.0))),
        max(_model_length(doc_or_obj, 0.20), 0.35 * height),
    )
    footing_h = max(
        _model_length(doc_or_obj, 0.20),
        abs(_model_length(doc_or_obj, float(rec.get("FootingThickness", 0.0) or 0.0))),
        max(_model_length(doc_or_obj, 0.20), 0.18 * height),
    )
    footing_w = max(abs(_model_length(doc_or_obj, float(rec.get("FootingWidth", 0.0) or 0.0))), width, wall * 2.5)
    cap_h = max(0.0, abs(_model_length(doc_or_obj, float(rec.get("CapHeight", 0.0) or 0.0))))

    stem_w = max(wall * 1.4, min(width * 0.55, footing_w * 0.60))
    seat_w = max(stem_w * 0.55, wall * 1.4)
    total_h = footing_h + max(0.20, height)
    seat_h0 = footing_h + max(0.30, 0.60 * height)

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
    center_origin = App.Vector(float(base_pt.x), float(base_pt.y), float(z0))
    origin = center_origin - (t * (0.5 * max(1e-6, float(length))))
    wire = _make_profile_wire(origin, n, App.Vector(0, 0, 1), coords)
    if wire is None:
        return None
    try:
        face = Part.Face(wire)
        solid = face.extrude(t * max(1e-6, float(length)))
    except Exception:
        return _build_box_geometry(base_pt, t, n, length, footing_w, total_h, z0)

    solids = [solid]
    if cap_h > 1e-6:
        cap_center = center_origin + App.Vector(0.0, 0.0, total_h)
        cap = _build_box_geometry(cap_center, t, n, length, max(seat_w * 1.1, seat_w + 0.20), cap_h, float(cap_center.z))
        if cap is not None and not cap.isNull():
            solids.append(cap)
    if len(solids) == 1:
        return solids[0] if _usable_solid(solids[0]) else _build_box_geometry(base_pt, t, n, length, footing_w, total_h, z0)
    try:
        out = Part.makeCompound(solids)
        if _usable_solid(out):
            return out
    except Exception:
        pass
    return _build_box_geometry(base_pt, t, n, length, footing_w, total_h, z0)


def _build_structure_solid(base_pt, tangent, normal, rec, doc_or_obj=None):
    if Part is None:
        return None
    length = abs(_model_length(doc_or_obj, float(rec.get("EndStation", 0.0) or 0.0) - float(rec.get("StartStation", 0.0) or 0.0)))
    width = abs(_model_length(doc_or_obj, float(rec.get("Width", 0.0) or 0.0)))
    height = abs(_model_length(doc_or_obj, float(rec.get("Height", 0.0) or 0.0)))
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

    z0 = _resolved_bottom_z(base_pt, rec, height, doc_or_obj=doc_or_obj)
    geom_mode = _default_geometry_mode(rec, fallback="box")
    template_name = _default_template_name(rec)

    if geom_mode == "external_shape":
        solid = _build_external_shape_geometry(base_pt, t, n, rec, z0)
        if _shape_is_displayable(solid):
            return solid

    if geom_mode == "template":
        if template_name == "box_culvert":
            solid = _build_box_culvert_template(base_pt, t, n, rec, length, width, height, z0, doc_or_obj=doc_or_obj)
            if _usable_solid(solid):
                return solid
        elif template_name == "utility_crossing":
            solid = _build_utility_crossing_template(base_pt, t, n, rec, length, width, height, z0, doc_or_obj=doc_or_obj)
            if _usable_solid(solid):
                return solid
        elif template_name == "retaining_wall":
            solid = _build_retaining_wall_template(base_pt, t, n, rec, length, width, height, z0, doc_or_obj=doc_or_obj)
            if _usable_solid(solid):
                return solid
        elif template_name == "abutment_block":
            solid = _build_abutment_block_template(base_pt, t, n, rec, length, width, height, z0, doc_or_obj=doc_or_obj)
            if _usable_solid(solid):
                return solid

    return _build_box_geometry(base_pt, t, n, length, width, height, z0)


def _build_profile_segment_solids(obj, aln, rec, prev_n=None):
    rid = _structure_ref_id(rec.get("Id", ""))
    if not rid:
        return [], prev_n
    geom_mode = _default_geometry_mode(rec, fallback="box")
    if geom_mode == "external_shape":
        return [], prev_n

    pts = StructureSet.profile_points(obj, rid)
    if len(pts) < 2:
        return [], prev_n

    s0 = float(rec.get("StartStation", 0.0) or 0.0)
    s1 = float(rec.get("EndStation", 0.0) or 0.0)
    if s1 < s0:
        s0, s1 = s1, s0
    sample_recs = StructureSet.resolve_profile_span(obj, rec, s0, s1)
    if len(sample_recs) < 2:
        return [], prev_n

    frames = []
    local_prev_n = prev_n
    for rr in sample_recs:
        ss = float(rr.get("ResolvedProfileStation", 0.0) or 0.0)
        frame = _resolve_station_frame(obj, ss, aln=aln, prev_n=local_prev_n)
        frames.append((rr, frame))
        local_prev_n = frame["N"]

    if len(frames) < 2:
        return [], local_prev_n

    solids = []
    branch_count = max(1, len(_side_offsets(sample_recs[0], obj)))
    for branch_idx in range(branch_count):
        wires = []
        fallback_needed = False
        for rr, frame in frames:
            offs = _side_offsets(rr, obj)
            off = float(offs[min(branch_idx, len(offs) - 1)] if offs else 0.0)
            wire = _section_wire_for_profile_record(frame["point"] + (frame["N"] * off), frame["N"], frame["Z"], rr, doc_or_obj=obj)
            if wire is None:
                fallback_needed = True
                break
            wires.append(wire)

        if not fallback_needed and len(wires) >= 2 and Part is not None:
            for i in range(len(wires) - 1):
                try:
                    solid = _build_profile_pair_solid(wires[i], wires[i + 1])
                    if _usable_solid(solid):
                        solids.append(solid)
                        continue
                except Exception:
                    pass
                fallback_needed = True
                break

        if fallback_needed:
            for i in range(len(sample_recs) - 1):
                a = sample_recs[i]
                b = sample_recs[i + 1]
                ss0 = float(a.get("ResolvedProfileStation", s0) or s0)
                ss1 = float(b.get("ResolvedProfileStation", s1) or s1)
                if ss1 <= ss0 + 1e-9:
                    continue
                sm = 0.5 * (ss0 + ss1)
                seg_rec = StructureSet.resolve_profile_at_station(obj, rec, sm)
                if not seg_rec:
                    continue
                seg_rec["StartStation"] = float(ss0)
                seg_rec["EndStation"] = float(ss1)
                seg_rec["CenterStation"] = float(sm)
                frame = _resolve_station_frame(obj, sm, aln=aln, prev_n=local_prev_n)
                p = frame["point"]
                t = frame["T"]
                n = frame["N"]
                local_prev_n = n
                offs = _side_offsets(seg_rec, obj)
                off = float(offs[min(branch_idx, len(offs) - 1)] if offs else 0.0)
                solid = _build_structure_solid(p + (n * off), t, n, seg_rec, doc_or_obj=obj)
                if solid is not None and not solid.isNull():
                    solids.append(solid)
    return solids, local_prev_n


def _safe_str_list(values):
    return [str(v or "") for v in list(values or [])]


def _safe_float(value, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        out = float(default)
    if not math.isfinite(out):
        out = float(default)
    return float(out)


def _safe_float_list(values):
    out = []
    for v in list(values or []):
        out.append(_safe_float(v, default=0.0))
    return out


def _safe_bool_text_list(values):
    out = []
    for v in list(values or []):
        txt = str(v or "").strip().lower()
        if txt in ("1", "true", "yes", "y", "on"):
            out.append("true")
        elif txt in ("0", "false", "no", "n", "off"):
            out.append("false")
        else:
            out.append("")
    return out


def _safe_int_list(values):
    out = []
    for v in list(values or []):
        try:
            x = int(round(float(v)))
        except Exception:
            x = 0
        out.append(int(x))
    return out


def _convert_float_list(values, converter):
    out = []
    for value in list(values or []):
        try:
            out.append(float(converter(value)))
        except Exception:
            out.append(0.0)
    return out


def _float_list_meters_from_internal(doc_or_obj, values):
    return _convert_float_list(values, lambda v: _units.meters_from_internal_length(doc_or_obj, float(v or 0.0)))


def _model_length(doc_or_obj, meters: float) -> float:
    return _units.model_length_from_meters(doc_or_obj, float(meters or 0.0))


def _unique_sorted_floats(values, tol: float = 1e-6):
    vals = sorted([float(v) for v in list(values or [])])
    out = []
    for v in vals:
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def _lerp(a: float, b: float, t: float):
    tt = max(0.0, min(1.0, float(t)))
    return float(a) + ((float(b) - float(a)) * tt)


def _profile_row_defaults():
    return {
        "StructureId": "",
        "Station": 0.0,
        "Offset": 0.0,
        "Width": 0.0,
        "Height": 0.0,
        "BottomElevation": 0.0,
        "Cover": 0.0,
        "WallThickness": 0.0,
        "FootingWidth": 0.0,
        "FootingThickness": 0.0,
        "CapHeight": 0.0,
        "CellCount": 0,
    }


def _structure_ref_id(structure_ref):
    if isinstance(structure_ref, dict):
        return str(structure_ref.get("Id", "") or "").strip()
    return str(structure_ref or "").strip()


def _normalize_profile_points(points, tol: float = 1e-6):
    rows = [dict(_profile_row_defaults(), **dict(p or {})) for p in list(points or [])]
    rows.sort(key=lambda r: float(r.get("Station", 0.0) or 0.0))
    out = []
    for row in rows:
        if out and abs(float(row.get("Station", 0.0) or 0.0) - float(out[-1].get("Station", 0.0) or 0.0)) <= tol:
            out[-1] = row
        else:
            out.append(row)
    return out


def _resolve_profile_interpolated_value(points, station: float, key: str, base_value):
    pts = list(points or [])
    if not pts:
        return base_value
    ss = float(station)
    if len(pts) == 1:
        return pts[0].get(key, base_value)
    if ss <= float(pts[0].get("Station", 0.0) or 0.0):
        return pts[0].get(key, base_value)
    if ss >= float(pts[-1].get("Station", 0.0) or 0.0):
        return pts[-1].get(key, base_value)
    for i in range(len(pts) - 1):
        p0 = pts[i]
        p1 = pts[i + 1]
        s0 = float(p0.get("Station", 0.0) or 0.0)
        s1 = float(p1.get("Station", 0.0) or 0.0)
        if ss < s0 or ss > s1:
            continue
        if abs(s1 - s0) <= 1e-9:
            return p1.get(key, p0.get(key, base_value))
        if key in _PROFILE_LINEAR_FIELDS:
            return _lerp(p0.get(key, base_value), p1.get(key, base_value), (ss - s0) / (s1 - s0))
        if key in _PROFILE_STEP_FIELDS:
            return p0.get(key, base_value)
        return p0.get(key, base_value)
    return pts[-1].get(key, base_value)


def _resolved_shape_source_kind(path: str) -> str:
    p, _obj = _split_external_shape_source(path)
    p = str(p or "").strip().lower()
    if not p:
        return ""
    if p.endswith(".step") or p.endswith(".stp"):
        return "step"
    if p.endswith(".brep") or p.endswith(".brp"):
        return "brep"
    if p.endswith(".fcstd"):
        return "fcstd_link"
    return "invalid"


def _shape_is_displayable(shape):
    if shape is None:
        return False
    try:
        return not shape.isNull()
    except Exception:
        return False


def _load_external_shape(path: str):
    if Part is None:
        return None, "missing_part"
    src, obj_name = _split_external_shape_source(path)
    kind = _resolved_shape_source_kind(src)
    if not src:
        return None, "missing"
    if not os.path.isfile(src):
        return None, "not_found"
    if kind not in ("step", "brep", "fcstd_link"):
        return None, kind or "invalid"
    key = str(src).lower() if kind != "fcstd_link" else f"{str(src).lower()}#{str(obj_name).lower()}"
    cached = _EXTERNAL_SHAPE_CACHE.get(key)
    if cached is not None:
        try:
            return cached.copy(), kind
        except Exception:
            _EXTERNAL_SHAPE_CACHE.pop(key, None)
    if kind == "fcstd_link":
        if not obj_name:
            return None, "fcstd_missing_object"
        doc_ref = None
        opened_here = False
        try:
            for d in list(getattr(App, "listDocuments", lambda: {})().values()):
                try:
                    if os.path.abspath(str(getattr(d, "FileName", "") or "")) == src:
                        doc_ref = d
                        break
                except Exception:
                    continue
            if doc_ref is None:
                try:
                    doc_ref = App.openDocument(src, True)
                except Exception:
                    try:
                        doc_ref = App.openDocument(src, hidden=True)
                    except Exception:
                        doc_ref = App.openDocument(src)
                opened_here = doc_ref is not None
            if doc_ref is None:
                return None, "load_failed"
            src_obj = None
            try:
                src_obj = doc_ref.getObject(str(obj_name))
            except Exception:
                src_obj = None
            if src_obj is None:
                for candidate in list(getattr(doc_ref, "Objects", []) or []):
                    if str(getattr(candidate, "Label", "") or "").strip() == str(obj_name):
                        src_obj = candidate
                        break
            if src_obj is None:
                return None, "fcstd_object_not_found"
            shp = getattr(src_obj, "Shape", None)
            if not _shape_is_displayable(shp):
                return None, "fcstd_missing_shape"
            try:
                shp = shp.copy()
            except Exception:
                pass
            _EXTERNAL_SHAPE_CACHE[key] = shp
            try:
                return shp.copy(), kind
            except Exception:
                return shp, kind
        except Exception:
            return None, "load_failed"
        finally:
            if opened_here and doc_ref is not None:
                try:
                    App.closeDocument(str(doc_ref.Name))
                except Exception:
                    pass
    try:
        shp = Part.read(src)
        if not _shape_is_displayable(shp):
            return None, "invalid_shape"
        _EXTERNAL_SHAPE_CACHE[key] = shp
        try:
            return shp.copy(), kind
        except Exception:
            return shp, kind
    except Exception:
        return None, "load_failed"


def _bool_from_text(v, default: bool = False) -> bool:
    txt = str(v or "").strip().lower()
    if txt in ("1", "true", "yes", "y", "on"):
        return True
    if txt in ("0", "false", "no", "n", "off"):
        return False
    return bool(default)


def _scaled_shape(shape, scale_factor: float):
    if not _shape_is_displayable(shape):
        return None
    sf = float(scale_factor or 1.0)
    if abs(sf - 1.0) <= 1e-12:
        try:
            return shape.copy()
        except Exception:
            return shape
    try:
        m = App.Matrix()
        m.A11 = sf
        m.A22 = sf
        m.A33 = sf
        m.A44 = 1.0
        return shape.transformGeometry(m)
    except Exception:
        return None


def _external_shape_ref_point(shape, placement_mode: str, use_source_base_as_bottom: bool):
    bb = getattr(shape, "BoundBox", None)
    if bb is None:
        return App.Vector(0.0, 0.0, 0.0)
    mode = str(placement_mode or "").strip().lower()
    if mode == "start_on_station":
        x_ref = float(bb.XMin)
    else:
        x_ref = 0.5 * (float(bb.XMin) + float(bb.XMax))
    y_ref = 0.5 * (float(bb.YMin) + float(bb.YMax))
    z_ref = float(bb.ZMin) if bool(use_source_base_as_bottom) else 0.0
    return App.Vector(x_ref, y_ref, z_ref)


def _external_shape_matrix(origin, t, n, zvec, ref_local):
    m = App.Matrix()
    m.A11 = float(t.x)
    m.A21 = float(t.y)
    m.A31 = float(t.z)
    m.A12 = float(n.x)
    m.A22 = float(n.y)
    m.A32 = float(n.z)
    m.A13 = float(zvec.x)
    m.A23 = float(zvec.y)
    m.A33 = float(zvec.z)
    tr = App.Vector(float(origin.x), float(origin.y), float(origin.z)) - (
        (t * float(ref_local.x)) + (n * float(ref_local.y)) + (zvec * float(ref_local.z))
    )
    m.A14 = float(tr.x)
    m.A24 = float(tr.y)
    m.A34 = float(tr.z)
    m.A44 = 1.0
    return m


def _build_external_shape_geometry(base_pt, t, n, rec, z0: float):
    src_shape, _status = _load_external_shape(str(rec.get("ShapeSourcePath", "") or "").strip())
    if not _shape_is_displayable(src_shape):
        return None
    shp = _scaled_shape(src_shape, float(rec.get("ScaleFactor", 1.0) or 1.0))
    if not _shape_is_displayable(shp):
        return None
    ref_local = _external_shape_ref_point(
        shp,
        placement_mode=str(rec.get("PlacementMode", "") or ""),
        use_source_base_as_bottom=_bool_from_text(rec.get("UseSourceBaseAsBottom", ""), default=True),
    )
    origin = App.Vector(float(base_pt.x), float(base_pt.y), float(z0))
    zvec = App.Vector(0.0, 0.0, 1.0)
    try:
        return shp.transformGeometry(_external_shape_matrix(origin, t, n, zvec, ref_local))
    except Exception:
        return None


def _external_shape_proxy_key(path: str, scale_factor: float):
    src, obj_name = _split_external_shape_source(path)
    kind = _resolved_shape_source_kind(src)
    key = str(src).lower()
    if kind == "fcstd_link":
        key = f"{key}#{str(obj_name).lower()}"
    return f"{key}|{float(scale_factor or 1.0):.9g}"


def _external_shape_bbox_proxy(rec, doc_or_obj=None):
    geom_mode = str(rec.get("GeometryMode", "") or "").strip().lower()
    if geom_mode != "external_shape":
        return None, ""
    path = str(rec.get("ShapeSourcePath", "") or "").strip()
    if not path:
        return None, "missing"
    scale_factor = _safe_float(rec.get("ScaleFactor", 1.0), default=1.0)
    cache_key = _external_shape_proxy_key(path, scale_factor)
    cached = _EXTERNAL_SHAPE_PROXY_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached), str(cached.get("SourceMode", "external_shape_bbox") or "external_shape_bbox")

    shp, status = _load_external_shape(path)
    if not _shape_is_displayable(shp):
        return None, str(status or "missing")
    shp = _scaled_shape(shp, scale_factor)
    if not _shape_is_displayable(shp):
        return None, "scale_failed"
    bb = getattr(shp, "BoundBox", None)
    if bb is None:
        return None, "bbox_missing"

    width = max(0.0, _units.meters_from_model_length(doc_or_obj, float(getattr(bb, "YLength", 0.0) or 0.0)))
    height = max(0.0, _units.meters_from_model_length(doc_or_obj, float(getattr(bb, "ZLength", 0.0) or 0.0)))
    length = max(0.0, _units.meters_from_model_length(doc_or_obj, float(getattr(bb, "XLength", 0.0) or 0.0)))
    if width <= 1e-9 or height <= 1e-9:
        return None, "bbox_flat"

    proxy = {
        "Width": float(width),
        "Height": float(height),
        "Length": float(length),
        "SourceMode": "external_shape_bbox",
        "ShapeSourceKind": str(status or ""),
    }
    _EXTERNAL_SHAPE_PROXY_CACHE[cache_key] = dict(proxy)
    return dict(proxy), "external_shape_bbox"


def _apply_external_shape_earthwork_proxy(rec, prefer_proxy: bool, doc_or_obj=None):
    out = dict(rec or {})
    proxy, status = _external_shape_bbox_proxy(out, doc_or_obj=doc_or_obj)
    if proxy is None:
        if str(out.get("GeometryMode", "") or "").strip().lower() == "external_shape":
            out["ResolvedEarthworkProxyMode"] = "-"
            out["ResolvedEarthworkProxyStatus"] = str(status or "unavailable")
        return out

    out["ResolvedEarthworkProxyMode"] = str(proxy.get("SourceMode", "external_shape_bbox") or "external_shape_bbox")
    out["ResolvedEarthworkProxyStatus"] = str(status or "external_shape_bbox")
    out["ResolvedEarthworkProxyWidth"] = float(proxy.get("Width", 0.0) or 0.0)
    out["ResolvedEarthworkProxyHeight"] = float(proxy.get("Height", 0.0) or 0.0)
    out["ResolvedEarthworkProxyLength"] = float(proxy.get("Length", 0.0) or 0.0)

    cur_width = abs(float(out.get("Width", 0.0) or 0.0))
    cur_height = abs(float(out.get("Height", 0.0) or 0.0))
    if bool(prefer_proxy) or cur_width <= 1e-9:
        out["Width"] = float(proxy.get("Width", 0.0) or 0.0)
    if bool(prefer_proxy) or cur_height <= 1e-9:
        out["Height"] = float(proxy.get("Height", 0.0) or 0.0)
    return out


def ensure_structure_set_properties(obj):
    had_linear_props = any(
        hasattr(obj, prop)
        for prop in (_STRUCTURE_LINEAR_RECORD_PROPS + _STRUCTURE_LINEAR_PROFILE_PROPS)
    )
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
    if not hasattr(obj, "GeometryModes"):
        obj.addProperty("App::PropertyStringList", "GeometryModes", "Structures", "Structure geometry modes")
        obj.GeometryModes = []
    if not hasattr(obj, "TemplateNames"):
        obj.addProperty("App::PropertyStringList", "TemplateNames", "Structures", "Structure template names")
        obj.TemplateNames = []
    if not hasattr(obj, "ShapeSourcePaths"):
        obj.addProperty("App::PropertyStringList", "ShapeSourcePaths", "Structures", "External shape source paths")
        obj.ShapeSourcePaths = []
    if not hasattr(obj, "ScaleFactors"):
        obj.addProperty("App::PropertyFloatList", "ScaleFactors", "Structures", "External shape scale factors")
        obj.ScaleFactors = []
    if not hasattr(obj, "PlacementModes"):
        obj.addProperty("App::PropertyStringList", "PlacementModes", "Structures", "External shape placement modes")
        obj.PlacementModes = []
    if not hasattr(obj, "UseSourceBaseAsBottoms"):
        obj.addProperty("App::PropertyStringList", "UseSourceBaseAsBottoms", "Structures", "Whether the external source base should align to z0")
        obj.UseSourceBaseAsBottoms = []
    if not hasattr(obj, "WallThicknesses"):
        obj.addProperty("App::PropertyFloatList", "WallThicknesses", "Structures", "Template wall thickness values")
        obj.WallThicknesses = []
    if not hasattr(obj, "FootingWidths"):
        obj.addProperty("App::PropertyFloatList", "FootingWidths", "Structures", "Template footing widths")
        obj.FootingWidths = []
    if not hasattr(obj, "FootingThicknesses"):
        obj.addProperty("App::PropertyFloatList", "FootingThicknesses", "Structures", "Template footing thicknesses")
        obj.FootingThicknesses = []
    if not hasattr(obj, "CapHeights"):
        obj.addProperty("App::PropertyFloatList", "CapHeights", "Structures", "Template cap heights")
        obj.CapHeights = []
    if not hasattr(obj, "CellCounts"):
        obj.addProperty("App::PropertyFloatList", "CellCounts", "Structures", "Template cell counts")
        obj.CellCounts = []
    if not hasattr(obj, "CorridorModes"):
        obj.addProperty("App::PropertyStringList", "CorridorModes", "Structures", "Corridor consumption modes")
        obj.CorridorModes = []
    if not hasattr(obj, "CorridorMargins"):
        obj.addProperty("App::PropertyFloatList", "CorridorMargins", "Structures", "Additional structure corridor margins")
        obj.CorridorMargins = []
    if not hasattr(obj, "Notes"):
        obj.addProperty("App::PropertyStringList", "Notes", "Structures", "Structure notes")
        obj.Notes = []
    if not hasattr(obj, "ProfileStructureIds"):
        obj.addProperty("App::PropertyStringList", "ProfileStructureIds", "StructureProfiles", "Structure-profile parent IDs")
        obj.ProfileStructureIds = []
    if not hasattr(obj, "ProfileStations"):
        obj.addProperty("App::PropertyFloatList", "ProfileStations", "StructureProfiles", "Structure-profile stations")
        obj.ProfileStations = []
    if not hasattr(obj, "ProfileOffsets"):
        obj.addProperty("App::PropertyFloatList", "ProfileOffsets", "StructureProfiles", "Structure-profile offsets")
        obj.ProfileOffsets = []
    if not hasattr(obj, "ProfileWidths"):
        obj.addProperty("App::PropertyFloatList", "ProfileWidths", "StructureProfiles", "Structure-profile widths")
        obj.ProfileWidths = []
    if not hasattr(obj, "ProfileHeights"):
        obj.addProperty("App::PropertyFloatList", "ProfileHeights", "StructureProfiles", "Structure-profile heights")
        obj.ProfileHeights = []
    if not hasattr(obj, "ProfileBottomElevations"):
        obj.addProperty("App::PropertyFloatList", "ProfileBottomElevations", "StructureProfiles", "Structure-profile bottom elevations")
        obj.ProfileBottomElevations = []
    if not hasattr(obj, "ProfileCovers"):
        obj.addProperty("App::PropertyFloatList", "ProfileCovers", "StructureProfiles", "Structure-profile covers")
        obj.ProfileCovers = []
    if not hasattr(obj, "ProfileWallThicknesses"):
        obj.addProperty("App::PropertyFloatList", "ProfileWallThicknesses", "StructureProfiles", "Structure-profile wall thicknesses")
        obj.ProfileWallThicknesses = []
    if not hasattr(obj, "ProfileFootingWidths"):
        obj.addProperty("App::PropertyFloatList", "ProfileFootingWidths", "StructureProfiles", "Structure-profile footing widths")
        obj.ProfileFootingWidths = []
    if not hasattr(obj, "ProfileFootingThicknesses"):
        obj.addProperty("App::PropertyFloatList", "ProfileFootingThicknesses", "StructureProfiles", "Structure-profile footing thicknesses")
        obj.ProfileFootingThicknesses = []
    if not hasattr(obj, "ProfileCapHeights"):
        obj.addProperty("App::PropertyFloatList", "ProfileCapHeights", "StructureProfiles", "Structure-profile cap heights")
        obj.ProfileCapHeights = []
    if not hasattr(obj, "ProfileCellCounts"):
        obj.addProperty("App::PropertyIntegerList", "ProfileCellCounts", "StructureProfiles", "Structure-profile cell counts")
        obj.ProfileCellCounts = []
    if not hasattr(obj, "StructureCount"):
        obj.addProperty("App::PropertyInteger", "StructureCount", "Result", "Structure record count")
        obj.StructureCount = 0
    if not hasattr(obj, "StructureProfileCount"):
        obj.addProperty("App::PropertyInteger", "StructureProfileCount", "Result", "Structure profile point count")
        obj.StructureProfileCount = 0
    if not hasattr(obj, "ResolvedShapeSourceKinds"):
        obj.addProperty("App::PropertyStringList", "ResolvedShapeSourceKinds", "Result", "Resolved external shape source kinds")
        obj.ResolvedShapeSourceKinds = []
    if not hasattr(obj, "ResolvedShapeStatusNotes"):
        obj.addProperty("App::PropertyStringList", "ResolvedShapeStatusNotes", "Result", "Resolved external shape load and fallback notes")
        obj.ResolvedShapeStatusNotes = []
    if not hasattr(obj, "ResolvedEarthworkProxyIds"):
        obj.addProperty("App::PropertyStringList", "ResolvedEarthworkProxyIds", "Result", "Structure ids using indirect external-shape earthwork proxy")
        obj.ResolvedEarthworkProxyIds = []
    if not hasattr(obj, "ResolvedEarthworkProxyNotes"):
        obj.addProperty("App::PropertyStringList", "ResolvedEarthworkProxyNotes", "Result", "Resolved external-shape earthwork proxy diagnostics")
        obj.ResolvedEarthworkProxyNotes = []
    if not hasattr(obj, "ResolvedEarthworkProxyCount"):
        obj.addProperty("App::PropertyInteger", "ResolvedEarthworkProxyCount", "Result", "Resolved count of indirect external-shape earthwork proxies")
        obj.ResolvedEarthworkProxyCount = 0
    if not hasattr(obj, "ResolvedFrameSources"):
        obj.addProperty("App::PropertyStringList", "ResolvedFrameSources", "Result", "Resolved frame sources for structure display placement")
        obj.ResolvedFrameSources = []
    if not hasattr(obj, "ResolvedFrameStatusNotes"):
        obj.addProperty("App::PropertyStringList", "ResolvedFrameStatusNotes", "Result", "Resolved frame source diagnostics for structure display placement")
        obj.ResolvedFrameStatusNotes = []
    if not hasattr(obj, "LengthSchemaVersion"):
        obj.addProperty("App::PropertyInteger", "LengthSchemaVersion", "Result", "Length storage schema version")
        obj.LengthSchemaVersion = 0
    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"

    schema = int(getattr(obj, "LengthSchemaVersion", 0) or 0)
    if schema < _STRUCTURE_LENGTH_SCHEMA_TARGET:
        if had_linear_props:
            for prop in _STRUCTURE_LINEAR_RECORD_PROPS + _STRUCTURE_LINEAR_PROFILE_PROPS:
                try:
                    setattr(
                        obj,
                        prop,
                        _float_list_meters_from_internal(getattr(obj, "Document", None), list(getattr(obj, prop, []) or [])),
                    )
                except Exception:
                    pass
        obj.LengthSchemaVersion = _STRUCTURE_LENGTH_SCHEMA_TARGET


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
        obj.StructureProfileCount = int(len(StructureSet.profile_points(obj)))
        obj.ResolvedShapeSourceKinds = [_resolved_shape_source_kind(rec.get("ShapeSourcePath", "")) for rec in recs]
        obj.ResolvedShapeStatusNotes = []
        obj.ResolvedEarthworkProxyIds = []
        obj.ResolvedEarthworkProxyNotes = []
        obj.ResolvedEarthworkProxyCount = 0
        obj.ResolvedFrameSources = []
        obj.ResolvedFrameStatusNotes = []
        aln = _resolve_alignment(obj)
        shape_notes = []
        shape_status_notes = []
        earthwork_proxy_ids = []
        earthwork_proxy_notes = []
        frame_sources = []
        frame_status_notes = []
        shp = _empty_shape()
        if Part is not None and hasattr(obj, "Shape") and aln is not None and getattr(aln, "Shape", None):
            total = float(getattr(aln.Shape, "Length", 0.0) or 0.0)
            solids = []
            prev_n = None
            centerline_hits = 0
            alignment_hits = 0
            fallback_hits = 0
            profile_driven_hits = 0
            for rec in recs:
                try:
                    rid = str(rec.get("Id", "") or f"#{int(rec.get('Index', 0)) + 1}")
                    sta = max(0.0, min(total, float(_station_for_record(rec))))
                    frame = _resolve_station_frame(obj, sta, aln=aln, prev_n=prev_n)
                    p = frame["point"]
                    t = frame["T"]
                    n = frame["N"]
                    prev_n = n
                    src = str(frame.get("source", "") or "")
                    frame_sources.append(src)
                    if src == "centerline3d":
                        centerline_hits += 1
                    elif src == "alignment":
                        alignment_hits += 1
                        frame_status_notes.append(f"{rid}: frame source=alignment")
                    else:
                        fallback_hits += 1
                        frame_status_notes.append(f"{rid}: frame source={src or 'fallback'}")
                    if str(rec.get("GeometryMode", "") or "").strip().lower() == "external_shape":
                        _shp_check, ext_status = _load_external_shape(rec.get("ShapeSourcePath", ""))
                        if ext_status not in ("step", "brep", "fcstd_link"):
                            note = f"{rid}: external_shape source={ext_status} -> box fallback"
                            shape_notes.append(note)
                            shape_status_notes.append(note)
                        proxy, proxy_status = _external_shape_bbox_proxy(rec, doc_or_obj=obj)
                        if proxy is not None:
                            earthwork_proxy_ids.append(rid)
                            earthwork_proxy_notes.append(
                                f"{rid}: external_shape bbox proxy width={float(proxy.get('Width', 0.0) or 0.0):.3f} height={float(proxy.get('Height', 0.0) or 0.0):.3f}"
                            )
                        else:
                            earthwork_proxy_notes.append(
                                f"{rid}: external_shape earthwork proxy unavailable ({proxy_status or 'missing'}); fallback to Type/Width/Height"
                            )
                    seg_solids, prev_n = _build_profile_segment_solids(obj, aln, rec, prev_n=prev_n)
                    if seg_solids:
                        profile_driven_hits += 1
                        solids.extend(seg_solids)
                    else:
                        for off in _side_offsets(rec, obj):
                            solid = _build_structure_solid(p + (n * float(off)), t, n, rec, doc_or_obj=obj)
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
            if recs:
                if centerline_hits > 0:
                    shape_notes.append(f"3D frame source: centerline3d={centerline_hits}")
                if alignment_hits > 0:
                    shape_notes.append(f"3D frame source: alignment={alignment_hits}")
                if fallback_hits > 0:
                    shape_notes.append(f"3D frame source: fallback={fallback_hits}")
                if profile_driven_hits > 0:
                    shape_notes.append(f"3D station-profile records: {profile_driven_hits}")
        elif recs:
            shape_notes.append("3D display requires a HorizontalAlignment")

        if shp is not None and hasattr(obj, "Shape"):
            obj.Shape = shp
        obj.ResolvedShapeStatusNotes = list(shape_status_notes or [])
        obj.ResolvedEarthworkProxyIds = list(earthwork_proxy_ids or [])
        obj.ResolvedEarthworkProxyNotes = list(earthwork_proxy_notes or [])
        obj.ResolvedEarthworkProxyCount = int(len(list(earthwork_proxy_ids or [])))
        obj.ResolvedFrameSources = list(frame_sources or [])
        obj.ResolvedFrameStatusNotes = list(frame_status_notes or [])

        note_count = len(issues) + len(shape_notes)
        external_shape_count = sum(1 for rec in recs if str(rec.get("GeometryMode", "") or "").strip().lower() == "external_shape")
        if note_count == 0:
            obj.Status = f"OK: {len(recs)} records"
        else:
            status = f"WARN: {len(recs)} records, {note_count} issue(s)"
            if shape_status_notes:
                status = f"{status} | externalShapeFallbacks={len(shape_status_notes)}"
            if frame_status_notes:
                status = f"{status} | frameFallbacks={len(frame_status_notes)}"
            obj.Status = status
        proxy_count = int(len(list(earthwork_proxy_ids or [])))
        display_only_count = max(0, int(external_shape_count) - int(proxy_count))
        if proxy_count > 0:
            obj.Status = f"{obj.Status} | externalShapeProxy={int(proxy_count)}"
        if display_only_count > 0:
            obj.Status = f"{obj.Status} | externalShapeDisplayOnly={int(display_only_count)}"
        if int(getattr(obj, "StructureProfileCount", 0) or 0) > 0:
            obj.Status = f"{obj.Status} | profilePoints={int(getattr(obj, 'StructureProfileCount', 0) or 0)}"

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
            "GeometryModes",
            "TemplateNames",
            "ShapeSourcePaths",
            "ScaleFactors",
            "PlacementModes",
            "UseSourceBaseAsBottoms",
            "WallThicknesses",
            "FootingWidths",
            "FootingThicknesses",
            "CapHeights",
            "CellCounts",
            "CorridorModes",
            "CorridorMargins",
            "Notes",
            "ProfileStructureIds",
            "ProfileStations",
            "ProfileOffsets",
            "ProfileWidths",
            "ProfileHeights",
            "ProfileBottomElevations",
            "ProfileCovers",
            "ProfileWallThicknesses",
            "ProfileFootingWidths",
            "ProfileFootingThicknesses",
            "ProfileCapHeights",
            "ProfileCellCounts",
        ):
            try:
                obj.touch()
                _mark_dependents_from_structure_set(obj)
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
            len(list(getattr(obj, "GeometryModes", []) or [])),
            len(list(getattr(obj, "TemplateNames", []) or [])),
            len(list(getattr(obj, "ShapeSourcePaths", []) or [])),
            len(list(getattr(obj, "ScaleFactors", []) or [])),
            len(list(getattr(obj, "PlacementModes", []) or [])),
            len(list(getattr(obj, "UseSourceBaseAsBottoms", []) or [])),
            len(list(getattr(obj, "WallThicknesses", []) or [])),
            len(list(getattr(obj, "FootingWidths", []) or [])),
            len(list(getattr(obj, "FootingThicknesses", []) or [])),
            len(list(getattr(obj, "CapHeights", []) or [])),
            len(list(getattr(obj, "CellCounts", []) or [])),
            len(list(getattr(obj, "CorridorModes", []) or [])),
            len(list(getattr(obj, "CorridorMargins", []) or [])),
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
        geometry_modes = _safe_str_list(getattr(obj, "GeometryModes", []))
        template_names = _safe_str_list(getattr(obj, "TemplateNames", []))
        shape_source_paths = _safe_str_list(getattr(obj, "ShapeSourcePaths", []))
        scale_factors = _safe_float_list(getattr(obj, "ScaleFactors", []))
        placement_modes = _safe_str_list(getattr(obj, "PlacementModes", []))
        use_source_base_as_bottoms = _safe_bool_text_list(getattr(obj, "UseSourceBaseAsBottoms", []))
        wall_thicknesses = _safe_float_list(getattr(obj, "WallThicknesses", []))
        footing_widths = _safe_float_list(getattr(obj, "FootingWidths", []))
        footing_thicknesses = _safe_float_list(getattr(obj, "FootingThicknesses", []))
        cap_heights = _safe_float_list(getattr(obj, "CapHeights", []))
        cell_counts = _safe_float_list(getattr(obj, "CellCounts", []))
        corridor_modes = _safe_str_list(getattr(obj, "CorridorModes", []))
        corridor_margins = _safe_float_list(getattr(obj, "CorridorMargins", []))
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
                    "GeometryMode": geometry_modes[i] if i < len(geometry_modes) else "",
                    "TemplateName": template_names[i] if i < len(template_names) else "",
                    "ShapeSourcePath": shape_source_paths[i] if i < len(shape_source_paths) else "",
                    "ScaleFactor": scale_factors[i] if i < len(scale_factors) else 1.0,
                    "PlacementMode": placement_modes[i] if i < len(placement_modes) else "",
                    "UseSourceBaseAsBottom": use_source_base_as_bottoms[i] if i < len(use_source_base_as_bottoms) else "",
                    "WallThickness": wall_thicknesses[i] if i < len(wall_thicknesses) else 0.0,
                    "FootingWidth": footing_widths[i] if i < len(footing_widths) else 0.0,
                    "FootingThickness": footing_thicknesses[i] if i < len(footing_thicknesses) else 0.0,
                    "CapHeight": cap_heights[i] if i < len(cap_heights) else 0.0,
                    "CellCount": cell_counts[i] if i < len(cell_counts) else 0.0,
                    "CorridorMode": corridor_modes[i] if i < len(corridor_modes) else "",
                    "CorridorMargin": corridor_margins[i] if i < len(corridor_margins) else 0.0,
                    "Notes": notes[i] if i < len(notes) else "",
                }
            )
        return recs

    @staticmethod
    def raw_profile_points(obj, structure_id: str = ""):
        ensure_structure_set_properties(obj)
        ids = _safe_str_list(getattr(obj, "ProfileStructureIds", []))
        stations = _safe_float_list(getattr(obj, "ProfileStations", []))
        offsets = _safe_float_list(getattr(obj, "ProfileOffsets", []))
        widths = _safe_float_list(getattr(obj, "ProfileWidths", []))
        heights = _safe_float_list(getattr(obj, "ProfileHeights", []))
        bottoms = _safe_float_list(getattr(obj, "ProfileBottomElevations", []))
        covers = _safe_float_list(getattr(obj, "ProfileCovers", []))
        wall_thicknesses = _safe_float_list(getattr(obj, "ProfileWallThicknesses", []))
        footing_widths = _safe_float_list(getattr(obj, "ProfileFootingWidths", []))
        footing_thicknesses = _safe_float_list(getattr(obj, "ProfileFootingThicknesses", []))
        cap_heights = _safe_float_list(getattr(obj, "ProfileCapHeights", []))
        cell_counts = _safe_int_list(getattr(obj, "ProfileCellCounts", []))
        n = max(
            len(ids),
            len(stations),
            len(offsets),
            len(widths),
            len(heights),
            len(bottoms),
            len(covers),
            len(wall_thicknesses),
            len(footing_widths),
            len(footing_thicknesses),
            len(cap_heights),
            len(cell_counts),
            0,
        )
        wanted = _structure_ref_id(structure_id)
        pts = []
        for i in range(n):
            row = {
                "Index": int(i),
                "StructureId": ids[i] if i < len(ids) else "",
                "Station": stations[i] if i < len(stations) else 0.0,
                "Offset": offsets[i] if i < len(offsets) else 0.0,
                "Width": widths[i] if i < len(widths) else 0.0,
                "Height": heights[i] if i < len(heights) else 0.0,
                "BottomElevation": bottoms[i] if i < len(bottoms) else 0.0,
                "Cover": covers[i] if i < len(covers) else 0.0,
                "WallThickness": wall_thicknesses[i] if i < len(wall_thicknesses) else 0.0,
                "FootingWidth": footing_widths[i] if i < len(footing_widths) else 0.0,
                "FootingThickness": footing_thicknesses[i] if i < len(footing_thicknesses) else 0.0,
                "CapHeight": cap_heights[i] if i < len(cap_heights) else 0.0,
                "CellCount": cell_counts[i] if i < len(cell_counts) else 0,
            }
            sid = _structure_ref_id(row.get("StructureId", ""))
            if wanted and sid != wanted:
                continue
            pts.append(row)
        return pts

    @staticmethod
    def profile_points(obj, structure_id: str = ""):
        return _normalize_profile_points(StructureSet.raw_profile_points(obj, structure_id=structure_id))

    @staticmethod
    def profile_points_by_structure(obj):
        grouped = {}
        for row in StructureSet.profile_points(obj):
            sid = _structure_ref_id(row.get("StructureId", ""))
            if not sid:
                continue
            grouped.setdefault(sid, []).append(row)
        return {sid: _normalize_profile_points(rows) for sid, rows in grouped.items()}

    @staticmethod
    def resolve_profile_at_station(obj, structure_ref, station: float):
        rec = None
        wanted = _structure_ref_id(structure_ref)
        if isinstance(structure_ref, dict):
            rec = dict(structure_ref)
            if not wanted:
                wanted = _structure_ref_id(rec.get("Id", ""))
        if rec is None and wanted:
            for row in StructureSet.records(obj):
                if _structure_ref_id(row.get("Id", "")) == wanted:
                    rec = dict(row)
                    break
        if rec is None:
            return {}

        pts = StructureSet.profile_points(obj, wanted)
        resolved = dict(rec)
        resolved["ResolvedProfileStructureId"] = wanted
        resolved["ResolvedProfileStation"] = float(station)
        resolved["ResolvedProfilePointCount"] = int(len(pts))
        resolved["ResolvedProfileMode"] = "base_row"
        if not pts:
            return _apply_external_shape_earthwork_proxy(resolved, prefer_proxy=True, doc_or_obj=obj)

        for key in _PROFILE_LINEAR_FIELDS + _PROFILE_STEP_FIELDS:
            resolved[key] = _resolve_profile_interpolated_value(pts, station, key, rec.get(key, _profile_row_defaults().get(key)))
        resolved["ResolvedProfileMode"] = "station_profile"
        return _apply_external_shape_earthwork_proxy(resolved, prefer_proxy=False, doc_or_obj=obj)

    @staticmethod
    def resolve_profile_span(obj, structure_ref, station_from: float, station_to: float):
        rec = None
        wanted = _structure_ref_id(structure_ref)
        if isinstance(structure_ref, dict):
            rec = dict(structure_ref)
            if not wanted:
                wanted = _structure_ref_id(rec.get("Id", ""))
        if rec is None and wanted:
            for row in StructureSet.records(obj):
                if _structure_ref_id(row.get("Id", "")) == wanted:
                    rec = dict(row)
                    break
        if rec is None:
            return []

        s0 = float(station_from)
        s1 = float(station_to)
        if s1 < s0:
            s0, s1 = s1, s0
        pts = StructureSet.profile_points(obj, wanted)
        sample_stations = [s0, s1]
        for row in pts:
            ss = float(row.get("Station", 0.0) or 0.0)
            if ss > s0 + 1e-9 and ss < s1 - 1e-9:
                sample_stations.append(ss)
        return [StructureSet.resolve_profile_at_station(obj, rec, ss) for ss in _unique_sorted_floats(sample_stations)]

    @staticmethod
    def validate(obj):
        issues = []
        recs = StructureSet.records(obj)
        valid_ids = {_structure_ref_id(rec.get("Id", "")) for rec in recs if _structure_ref_id(rec.get("Id", ""))}
        tol = 1e-6
        for rec in recs:
            rid = str(rec.get("Id", "") or f"#{int(rec['Index']) + 1}")
            typ = str(rec.get("Type", "") or "").strip().lower()
            side = str(rec.get("Side", "") or "").strip().lower()
            mode = str(rec.get("BehaviorMode", "") or "").strip().lower()
            geom_mode = str(rec.get("GeometryMode", "") or "").strip().lower()
            template_name = str(rec.get("TemplateName", "") or "").strip().lower()
            shape_source_path = str(rec.get("ShapeSourcePath", "") or "").strip()
            scale_factor = float(rec.get("ScaleFactor", 1.0) or 1.0)
            placement_mode = str(rec.get("PlacementMode", "") or "").strip().lower()
            cor_mode = str(rec.get("CorridorMode", "") or "").strip().lower()
            s0 = float(rec.get("StartStation", 0.0) or 0.0)
            s1 = float(rec.get("EndStation", 0.0) or 0.0)
            sc = float(rec.get("CenterStation", 0.0) or 0.0)
            w = float(rec.get("Width", 0.0) or 0.0)
            h = float(rec.get("Height", 0.0) or 0.0)
            wt = float(rec.get("WallThickness", 0.0) or 0.0)
            fw = float(rec.get("FootingWidth", 0.0) or 0.0)
            ft = float(rec.get("FootingThickness", 0.0) or 0.0)
            ch = float(rec.get("CapHeight", 0.0) or 0.0)
            cc = float(rec.get("CellCount", 0.0) or 0.0)
            cm = float(rec.get("CorridorMargin", 0.0) or 0.0)

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
            if geom_mode and geom_mode not in ALLOWED_GEOMETRY_MODES:
                issues.append(f"{rid}: unknown geometry mode '{geom_mode}'")
            if template_name and template_name not in ALLOWED_TEMPLATE_NAMES:
                issues.append(f"{rid}: unknown template name '{template_name}'")
            if placement_mode and placement_mode not in ALLOWED_PLACEMENT_MODES:
                issues.append(f"{rid}: unknown placement mode '{placement_mode}'")
            if cor_mode and cor_mode not in ALLOWED_CORRIDOR_MODES:
                issues.append(f"{rid}: unknown corridor mode '{cor_mode}'")

            if s1 < s0:
                issues.append(f"{rid}: end station is smaller than start station")
            if sc > 0.0 and s1 > s0 and (sc < s0 or sc > s1):
                issues.append(f"{rid}: center station is outside start/end range")
            if w < 0.0:
                issues.append(f"{rid}: width is negative")
            if h < 0.0:
                issues.append(f"{rid}: height is negative")
            if wt < 0.0:
                issues.append(f"{rid}: wall thickness is negative")
            if fw < 0.0:
                issues.append(f"{rid}: footing width is negative")
            if ft < 0.0:
                issues.append(f"{rid}: footing thickness is negative")
            if ch < 0.0:
                issues.append(f"{rid}: cap height is negative")
            if cc < 0.0:
                issues.append(f"{rid}: cell count is negative")
            if cm < 0.0:
                issues.append(f"{rid}: corridor margin is negative")
            if scale_factor <= 0.0:
                issues.append(f"{rid}: scale factor must be greater than zero")
            has_start_end = abs(s0) > tol or abs(s1) > tol or abs(s1 - s0) > tol
            has_center = abs(sc) > tol
            if geom_mode == "template":
                if not template_name:
                    issues.append(f"{rid}: template geometry mode requires TemplateName")
                if template_name in ("box_culvert", "utility_crossing") and cc < 1.0:
                    issues.append(f"{rid}: {template_name} requires CellCount >= 1")
            if geom_mode == "external_shape":
                if not shape_source_path:
                    issues.append(f"{rid}: external_shape geometry mode requires ShapeSourcePath")
                kind = _resolved_shape_source_kind(shape_source_path)
                if shape_source_path and kind == "invalid":
                    issues.append(f"{rid}: unsupported external shape source '{shape_source_path}'")
                if kind == "fcstd_link" and "#" not in shape_source_path:
                    issues.append(f"{rid}: fcstd external shape requires ShapeSourcePath in the form 'path.FCStd#ObjectName'")
                issues.append(f"{rid}: external_shape may drive an indirect bbox-based earthwork proxy; direct solid consumption is still unsupported")
                if cor_mode in ("notch", "boolean_cut"):
                    issues.append(f"{rid}: {cor_mode} does not yet consume the imported external solid directly; current runtime can only use bbox proxy or Type/Width/Height")
            if cor_mode == "notch" and typ not in ("culvert", "crossing"):
                if typ == "retaining_wall":
                    issues.append(f"{rid}: retaining_wall should use split_only rather than notch")
                elif typ in ("bridge_zone", "abutment_zone"):
                    issues.append(f"{rid}: {typ} should prefer skip_zone rather than notch")
                else:
                    issues.append(f"{rid}: notch first sprint supports culvert/crossing only")
            if cor_mode == "boolean_cut":
                issues.append(f"{rid}: boolean_cut remains later opt-in scope; keep notch/skip_zone as the current stable corridor modes")
            if cor_mode in ("skip_zone", "notch", "boolean_cut"):
                if not has_start_end and not has_center:
                    issues.append(f"{rid}: corridor mode '{cor_mode}' has no usable station span")
                elif abs(s1 - s0) <= tol and cm <= tol:
                    issues.append(f"{rid}: corridor mode '{cor_mode}' is point-like; add CorridorMargin or explicit Start/End span")
        grouped = {}
        raw_points = StructureSet.raw_profile_points(obj)
        for row in raw_points:
            sid = _structure_ref_id(row.get("StructureId", ""))
            grouped.setdefault(sid, []).append(row)
        for sid, rows in grouped.items():
            if not sid:
                issues.append("StructureProfile: StructureId is empty")
                continue
            if sid not in valid_ids:
                issues.append(f"{sid}: structure profile references unknown structure id")
            if len(rows) < 2:
                issues.append(f"{sid}: structure profile needs at least 2 station points")
            prev_station = None
            seen_station = set()
            for row in sorted(rows, key=lambda r: float(r.get("Station", 0.0) or 0.0)):
                ss = float(row.get("Station", 0.0) or 0.0)
                key_station = round(ss, 9)
                if prev_station is not None and ss < prev_station - 1e-9:
                    issues.append(f"{sid}: structure profile stations must be sorted ascending")
                if key_station in seen_station:
                    issues.append(f"{sid}: duplicate structure profile station {ss:.3f}")
                seen_station.add(key_station)
                prev_station = ss
                for name in _PROFILE_LINEAR_FIELDS:
                    vv = float(row.get(name, 0.0) or 0.0)
                    if name in ("Width", "Height", "WallThickness", "FootingWidth", "FootingThickness", "CapHeight") and vv < 0.0:
                        issues.append(f"{sid}: structure profile {name} is negative at station {ss:.3f}")
                if int(row.get("CellCount", 0) or 0) < 0:
                    issues.append(f"{sid}: structure profile CellCount is negative at station {ss:.3f}")
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
    def structure_key_station_items(
        obj,
        include_start_end: bool = True,
        include_centers: bool = True,
        include_transition: bool = False,
        auto_transition: bool = True,
        transition: float = 0.0,
    ):
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
            if include_transition:
                tt = _record_transition_distance(obj, rec, auto_transition=auto_transition, transition=transition)
                if tt > 1e-9:
                    _add(s0 - tt, "", "transition_before")
                    _add(s1 + tt, "", "transition_after")
        return items

    @staticmethod
    def structure_key_stations(
        obj,
        include_start_end: bool = True,
        include_centers: bool = True,
        include_transition: bool = False,
        auto_transition: bool = True,
        transition: float = 0.0,
    ):
        items = StructureSet.structure_key_station_items(
            obj,
            include_start_end=include_start_end,
            include_centers=include_centers,
            include_transition=include_transition,
            auto_transition=auto_transition,
            transition=transition,
        )
        return _unique_sorted_floats([it.get("station", 0.0) for it in items])

    @staticmethod
    def corridor_zone_records(obj, fallback_mode: str = "split_only"):
        out = []
        tol = 1e-6
        for rec in StructureSet.records(obj):
            s0 = _safe_float(rec.get("StartStation", 0.0), default=0.0)
            s1 = _safe_float(rec.get("EndStation", 0.0), default=0.0)
            sc = _safe_float(rec.get("CenterStation", 0.0), default=0.0)
            station_source = "start_end"
            warnings = []
            has_start_end = abs(s0) > tol or abs(s1) > tol or abs(s1 - s0) > tol
            has_center = abs(sc) > tol
            if not has_start_end and has_center:
                s0 = sc
                s1 = sc
                station_source = "center_fallback"
                warnings.append("used CenterStation because Start/EndStation were empty")
            if s1 < s0:
                s0, s1 = s1, s0
                warnings.append("swapped StartStation/EndStation order")
            mode = _default_corridor_mode(rec, fallback=fallback_mode)
            corridor_margin = max(0.0, _safe_float(rec.get("CorridorMargin", 0.0), default=0.0))
            if not has_start_end and not has_center and mode not in ("", "none"):
                station_source = "missing"
                warnings.append("no usable station span; corridor logic falls back to 0.000")
            if has_center and (sc < (s0 - tol) or sc > (s1 + tol)):
                warnings.append("CenterStation lies outside the resolved corridor span")
            if mode == "skip_zone" and abs(s1 - s0) <= tol and corridor_margin <= tol:
                warnings.append("zero-length skip_zone span without CorridorMargin")
            row = dict(rec)
            row["ResolvedCorridorMode"] = mode
            row["ResolvedStartStation"] = float(s0)
            row["ResolvedEndStation"] = float(s1)
            row["ResolvedCorridorMargin"] = corridor_margin
            row["ResolvedStationSource"] = station_source
            row["ResolvedCorridorWarnings"] = list(warnings)
            out.append(row)
        return out


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
