import math
import os

import FreeCAD as App

try:
    import Part
except Exception:
    Part = None

from freecad.Corridor_Road.objects.doc_query import find_first, find_project
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_centerline3d import Centerline3D
from freecad.Corridor_Road.objects.obj_project import get_length_scale


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
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
    src3d = _resolve_centerline_source(obj)
    if src3d is not None:
        try:
            frame = Centerline3D.frame_at_station(src3d, float(station), eps=0.1 * scale, prev_n=prev_n)
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


def _record_transition_distance(obj, rec, auto_transition: bool = True, transition: float = 0.0):
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
    width = max(0.0, abs(float(rec.get("Width", 0.0) or 0.0)))
    height = max(0.0, abs(float(rec.get("Height", 0.0) or 0.0)))
    typ = str(rec.get("Type", "") or "").strip().lower()

    if not bool(auto_transition):
        return max(0.0, float(transition))

    if typ in ("culvert", "crossing"):
        return max(5.0 * scale, 0.75 * width, 1.50 * height)
    if typ == "retaining_wall":
        return max(3.0 * scale, 0.50 * width, 1.00 * height)
    if typ in ("bridge_zone", "abutment_zone"):
        return max(10.0 * scale, 0.50 * width, 1.00 * height)
    return max(5.0 * scale, 0.50 * width, 1.00 * height)


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


def _make_profile_wire(origin, nvec, zvec, coords_nz):
    pts = []
    for nn, zz in list(coords_nz or []):
        pts.append(origin + (nvec * float(nn)) + (zvec * float(zz)))
    if not pts:
        return None
    if (pts[0] - pts[-1]).Length > 1e-9:
        pts.append(pts[0])
    return Part.makePolygon(pts)


def _build_box_culvert_template(base_pt, t, n, rec, length: float, width: float, height: float, z0: float):
    wall = max(0.10, abs(float(rec.get("WallThickness", 0.0) or 0.0)))
    cells = max(1, int(round(float(rec.get("CellCount", 1) or 1))))
    top_cap = max(0.0, abs(float(rec.get("CapHeight", 0.0) or 0.0)))
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


def _build_utility_crossing_template(base_pt, t, n, rec, length: float, width: float, height: float, z0: float):
    wall = max(0.08, abs(float(rec.get("WallThickness", 0.0) or 0.0)))
    cells = max(1, int(round(float(rec.get("CellCount", 1) or 1))))
    top_cap = max(0.0, abs(float(rec.get("CapHeight", 0.0) or 0.0)))
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


def _build_retaining_wall_template(base_pt, t, n, rec, length: float, width: float, height: float, z0: float):
    wall = max(0.10, abs(float(rec.get("WallThickness", 0.0) or 0.0)), max(0.10, 0.60 * width))
    footing_w = max(wall * 2.5, abs(float(rec.get("FootingWidth", 0.0) or 0.0)), max(width * 2.0, wall * 4.0))
    footing_h = max(0.10, abs(float(rec.get("FootingThickness", 0.0) or 0.0)))
    cap_h = max(0.0, abs(float(rec.get("CapHeight", 0.0) or 0.0)))
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


def _build_abutment_block_template(base_pt, t, n, rec, length: float, width: float, height: float, z0: float):
    wall = max(0.20, abs(float(rec.get("WallThickness", 0.0) or 0.0)), max(0.20, 0.35 * height))
    footing_h = max(0.20, abs(float(rec.get("FootingThickness", 0.0) or 0.0)), max(0.20, 0.18 * height))
    footing_w = max(abs(float(rec.get("FootingWidth", 0.0) or 0.0)), width, wall * 2.5)
    cap_h = max(0.0, abs(float(rec.get("CapHeight", 0.0) or 0.0)))

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
    geom_mode = _default_geometry_mode(rec, fallback="box")
    template_name = _default_template_name(rec)

    if geom_mode == "external_shape":
        solid = _build_external_shape_geometry(base_pt, t, n, rec, z0)
        if _shape_is_displayable(solid):
            return solid

    if geom_mode == "template":
        if template_name == "box_culvert":
            solid = _build_box_culvert_template(base_pt, t, n, rec, length, width, height, z0)
            if _usable_solid(solid):
                return solid
        elif template_name == "utility_crossing":
            solid = _build_utility_crossing_template(base_pt, t, n, rec, length, width, height, z0)
            if _usable_solid(solid):
                return solid
        elif template_name == "retaining_wall":
            solid = _build_retaining_wall_template(base_pt, t, n, rec, length, width, height, z0)
            if _usable_solid(solid):
                return solid
        elif template_name == "abutment_block":
            solid = _build_abutment_block_template(base_pt, t, n, rec, length, width, height, z0)
            if _usable_solid(solid):
                return solid

    return _build_box_geometry(base_pt, t, n, length, width, height, z0)


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


def _unique_sorted_floats(values, tol: float = 1e-6):
    vals = sorted([float(v) for v in list(values or [])])
    out = []
    for v in vals:
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


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
    if not hasattr(obj, "StructureCount"):
        obj.addProperty("App::PropertyInteger", "StructureCount", "Result", "Structure record count")
        obj.StructureCount = 0
    if not hasattr(obj, "ResolvedShapeSourceKinds"):
        obj.addProperty("App::PropertyStringList", "ResolvedShapeSourceKinds", "Result", "Resolved external shape source kinds")
        obj.ResolvedShapeSourceKinds = []
    if not hasattr(obj, "ResolvedShapeStatusNotes"):
        obj.addProperty("App::PropertyStringList", "ResolvedShapeStatusNotes", "Result", "Resolved external shape load and fallback notes")
        obj.ResolvedShapeStatusNotes = []
    if not hasattr(obj, "ResolvedFrameSources"):
        obj.addProperty("App::PropertyStringList", "ResolvedFrameSources", "Result", "Resolved frame sources for structure display placement")
        obj.ResolvedFrameSources = []
    if not hasattr(obj, "ResolvedFrameStatusNotes"):
        obj.addProperty("App::PropertyStringList", "ResolvedFrameStatusNotes", "Result", "Resolved frame source diagnostics for structure display placement")
        obj.ResolvedFrameStatusNotes = []
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
        obj.ResolvedShapeSourceKinds = [_resolved_shape_source_kind(rec.get("ShapeSourcePath", "")) for rec in recs]
        obj.ResolvedShapeStatusNotes = []
        obj.ResolvedFrameSources = []
        obj.ResolvedFrameStatusNotes = []
        aln = _resolve_alignment(obj)
        shape_notes = []
        shape_status_notes = []
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
            if recs:
                if centerline_hits > 0:
                    shape_notes.append(f"3D frame source: centerline3d={centerline_hits}")
                if alignment_hits > 0:
                    shape_notes.append(f"3D frame source: alignment={alignment_hits}")
                if fallback_hits > 0:
                    shape_notes.append(f"3D frame source: fallback={fallback_hits}")
        elif recs:
            shape_notes.append("3D display requires a HorizontalAlignment")

        if shp is not None and hasattr(obj, "Shape"):
            obj.Shape = shp
        obj.ResolvedShapeStatusNotes = list(shape_status_notes or [])
        obj.ResolvedFrameSources = list(frame_sources or [])
        obj.ResolvedFrameStatusNotes = list(frame_status_notes or [])

        note_count = len(issues) + len(shape_notes)
        if note_count == 0:
            obj.Status = f"OK: {len(recs)} records"
        else:
            status = f"WARN: {len(recs)} records, {note_count} issue(s)"
            if shape_status_notes:
                status = f"{status} | externalShapeFallbacks={len(shape_status_notes)}"
            if frame_status_notes:
                status = f"{status} | frameFallbacks={len(frame_status_notes)}"
            obj.Status = status

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
    def validate(obj):
        issues = []
        for rec in StructureSet.records(obj):
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
        for rec in StructureSet.records(obj):
            s0 = float(rec.get("StartStation", 0.0) or 0.0)
            s1 = float(rec.get("EndStation", 0.0) or 0.0)
            if s1 < s0:
                s0, s1 = s1, s0
            mode = _default_corridor_mode(rec, fallback=fallback_mode)
            row = dict(rec)
            row["ResolvedCorridorMode"] = mode
            row["ResolvedStartStation"] = float(s0)
            row["ResolvedEndStation"] = float(s1)
            row["ResolvedCorridorMargin"] = max(0.0, float(rec.get("CorridorMargin", 0.0) or 0.0))
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
