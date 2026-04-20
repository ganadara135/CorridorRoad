# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import Part


def dedupe_consecutive_points(points, tol: float = 1e-9):
    out = []
    for point in list(points or []):
        if not out or (point - out[-1]).Length > tol:
            out.append(point)
    return out


def wire_points(wire):
    edges = list(getattr(wire, "Edges", []) or [])
    if not edges:
        return []
    pts = [edges[0].valueAt(edges[0].FirstParameter)]
    for edge in edges:
        pts.append(edge.valueAt(edge.LastParameter))
    return dedupe_consecutive_points(pts)


def make_tri_face(p0, p1, p2, tol: float = 1e-9):
    if ((p1 - p0).Length <= tol) or ((p2 - p1).Length <= tol) or ((p2 - p0).Length <= tol):
        return None
    try:
        wire = Part.makePolygon([p0, p1, p2, p0])
        face = Part.Face(wire)
        if face is None or face.isNull():
            return None
        return face
    except Exception:
        return None


def add_mesh_triangle(mesh_out, p0, p1, p2, area_tol: float = 1e-12):
    try:
        if (p1 - p0).Length <= area_tol or (p2 - p0).Length <= area_tol:
            return 0
        normal = (p1 - p0).cross(p2 - p0)
        if normal.Length <= area_tol:
            return 0
        mesh_out.addFacet(p0, p1, p2)
        return 1
    except Exception:
        return 0


def build_mesh_from_point_lists(point_lists):
    import Mesh

    mesh_out = Mesh.Mesh()
    quad_count = 0
    tri_count = 0
    rows = list(point_lists or [])
    for idx in range(len(rows) - 1):
        a = list(rows[idx] or [])
        b = list(rows[idx + 1] or [])
        for j in range(len(a) - 1):
            p00 = a[j]
            p01 = a[j + 1]
            p10 = b[j]
            p11 = b[j + 1]
            tri_count += add_mesh_triangle(mesh_out, p00, p01, p11)
            tri_count += add_mesh_triangle(mesh_out, p00, p11, p10)
            quad_count += 1
    return mesh_out, int(quad_count), int(tri_count)


def resample_wire_points(wire, count: int):
    target = max(2, int(count or 0))
    try:
        pts = list(wire.discretize(Number=target) or [])
        if len(pts) == target:
            return [App.Vector(float(p.x), float(p.y), float(p.z)) for p in pts]
    except Exception:
        pass
    pts = wire_points(wire)
    if len(pts) == target:
        return list(pts)
    return list(pts)


def _polyline_params(points):
    pts = [App.Vector(float(p.x), float(p.y), float(p.z)) for p in list(points or [])]
    if len(pts) < 2:
        return []
    lengths = [0.0]
    total = 0.0
    for idx in range(1, len(pts)):
        total += float((pts[idx] - pts[idx - 1]).Length)
        lengths.append(total)
    if total <= 1e-12:
        denom = max(1, len(pts) - 1)
        return [float(idx) / float(denom) for idx in range(len(pts))]
    return [float(val) / float(total) for val in lengths]


def _resample_polyline_at_params(points, params):
    pts = [App.Vector(float(p.x), float(p.y), float(p.z)) for p in list(points or [])]
    if len(pts) < 2:
        return list(pts)
    base_params = _polyline_params(pts)
    if len(base_params) != len(pts):
        return list(pts)

    out = []
    seg = 0
    last_seg = max(0, len(pts) - 2)
    for raw_t in list(params or []):
        t = max(0.0, min(1.0, float(raw_t)))
        while seg < last_seg and t > base_params[seg + 1] + 1e-12:
            seg += 1
        t0 = float(base_params[seg])
        t1 = float(base_params[seg + 1])
        p0 = pts[seg]
        p1 = pts[seg + 1]
        if t1 <= t0 + 1e-12:
            out.append(App.Vector(float(p0.x), float(p0.y), float(p0.z)))
            continue
        alpha = (t - t0) / (t1 - t0)
        out.append(
            App.Vector(
                float(p0.x) + ((float(p1.x) - float(p0.x)) * alpha),
                float(p0.y) + ((float(p1.y) - float(p0.y)) * alpha),
                float(p0.z) + ((float(p1.z) - float(p0.z)) * alpha),
            )
        )
    return dedupe_consecutive_points(out)


def _merge_polyline_params(points_a, points_b):
    params = [0.0, 1.0]
    params.extend(_polyline_params(points_a))
    params.extend(_polyline_params(points_b))
    merged = []
    for raw in sorted(float(v) for v in list(params or [])):
        val = max(0.0, min(1.0, raw))
        if not merged or abs(val - merged[-1]) > 1e-9:
            merged.append(val)
    return merged


def harmonize_pair_points(wire0, wire1, pts0, pts1, point_count_hint: int = 0):
    a = list(pts0 or [])
    b = list(pts1 or [])
    if len(a) >= 2 and len(a) == len(b):
        return a, b
    merged_params = _merge_polyline_params(a, b)
    if len(merged_params) >= 2:
        a2 = _resample_polyline_at_params(a, merged_params)
        b2 = _resample_polyline_at_params(b, merged_params)
        if len(a2) >= 2 and len(a2) == len(b2):
            return a2, b2
    target = int(point_count_hint or 0)
    if target < 2:
        target = max(len(a), len(b), 2)
    a2 = resample_wire_points(wire0, target)
    b2 = resample_wire_points(wire1, target)
    if len(a2) >= 2 and len(a2) == len(b2):
        return a2, b2
    raise Exception(f"Section pair point-count mismatch ({len(a)} vs {len(b)})")


def build_part_pair_surface(wire0, wire1, pts0=None, pts1=None, point_count_hint: int = 0):
    pts0 = list(pts0 or wire_points(wire0))
    pts1 = list(pts1 or wire_points(wire1))
    if len(pts0) < 2 or len(pts1) < 2:
        raise Exception("Section pair has insufficient points.")
    pts0, pts1 = harmonize_pair_points(wire0, wire1, pts0, pts1, point_count_hint=point_count_hint)

    faces = []
    for j in range(len(pts0) - 1):
        p00 = pts0[j]
        p01 = pts0[j + 1]
        p10 = pts1[j]
        p11 = pts1[j + 1]
        for tri in ((p00, p01, p11), (p00, p11, p10)):
            face = make_tri_face(*tri)
            if face is not None:
                faces.append(face)

    if faces:
        return Part.Compound(faces)

    raise Exception("Section pair surface produced no valid strip faces.")


def build_part_strip_surface(wires, point_lists=None, point_count_hint: int = 0):
    pair_shapes = []
    wires = list(wires or [])
    if len(wires) < 2:
        raise Exception("Need at least 2 sections for strip surface.")
    point_lists = list(point_lists or [])
    use_point_lists = len(point_lists) == len(wires)
    for idx in range(len(wires) - 1):
        pts0 = point_lists[idx] if use_point_lists else None
        pts1 = point_lists[idx + 1] if use_point_lists else None
        pair_shapes.append(
            build_part_pair_surface(
                wires[idx],
                wires[idx + 1],
                pts0=pts0,
                pts1=pts1,
                point_count_hint=point_count_hint,
            )
        )
    if not pair_shapes:
        raise Exception("Section strip surface produced no faces.")
    return pair_shapes[0] if len(pair_shapes) == 1 else Part.Compound(pair_shapes)
