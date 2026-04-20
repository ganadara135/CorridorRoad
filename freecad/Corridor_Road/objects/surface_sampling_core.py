# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import math

import FreeCAD as App


def is_mesh_object(obj) -> bool:
    try:
        return hasattr(obj, "Mesh") and obj.Mesh is not None and int(obj.Mesh.CountFacets) > 0
    except Exception:
        return False


def is_shape_object(obj) -> bool:
    try:
        return hasattr(obj, "Shape") and obj.Shape is not None and (not obj.Shape.isNull())
    except Exception:
        return False


def to_vec(p):
    try:
        return App.Vector(float(p.x), float(p.y), float(p.z))
    except Exception:
        pass
    try:
        return App.Vector(float(p[0]), float(p[1]), float(p[2]))
    except Exception:
        pass
    raise Exception("Invalid point format.")


def triangle_bbox_xy(p0, p1, p2):
    return (
        min(p0.x, p1.x, p2.x),
        max(p0.x, p1.x, p2.x),
        min(p0.y, p1.y, p2.y),
        max(p0.y, p1.y, p2.y),
    )


def mesh_triangles(mesh_obj):
    mesh = getattr(mesh_obj, "Mesh", None)
    if mesh is None:
        return []

    triangles = []
    topo = None
    try:
        topo = mesh.Topology
        if callable(topo):
            topo = topo()
    except Exception:
        topo = None

    if topo is not None and len(topo) == 2:
        pts, faces = topo
        for f in faces:
            try:
                i0, i1, i2 = int(f[0]), int(f[1]), int(f[2])
                p0, p1, p2 = to_vec(pts[i0]), to_vec(pts[i1]), to_vec(pts[i2])
                if (p1 - p0).Length <= 1e-12 or (p2 - p0).Length <= 1e-12:
                    continue
                triangles.append((p0, p1, p2, triangle_bbox_xy(p0, p1, p2)))
            except Exception:
                continue
    else:
        for fc in list(getattr(mesh, "Facets", []) or []):
            try:
                pts = list(getattr(fc, "Points", []) or [])
                if len(pts) != 3:
                    continue
                p0, p1, p2 = to_vec(pts[0]), to_vec(pts[1]), to_vec(pts[2])
                if (p1 - p0).Length <= 1e-12 or (p2 - p0).Length <= 1e-12:
                    continue
                triangles.append((p0, p1, p2, triangle_bbox_xy(p0, p1, p2)))
            except Exception:
                continue
    return triangles


def shape_triangles(shape_obj, deflection: float = 1.0):
    shp = getattr(shape_obj, "Shape", None)
    if shp is None or shp.isNull():
        return []
    triangles = []
    try:
        pts, tri_idx = shp.tessellate(max(0.01, float(deflection)))
    except Exception:
        return []
    for t in tri_idx:
        try:
            i0, i1, i2 = int(t[0]), int(t[1]), int(t[2])
            p0, p1, p2 = to_vec(pts[i0]), to_vec(pts[i1]), to_vec(pts[i2])
            if (p1 - p0).Length <= 1e-12 or (p2 - p0).Length <= 1e-12:
                continue
            triangles.append((p0, p1, p2, triangle_bbox_xy(p0, p1, p2)))
        except Exception:
            continue
    return triangles


def build_xy_buckets(triangles, bucket_size: float, max_cells_per_triangle: int = 20000, max_wide_items: int = 5000):
    if bucket_size <= 1e-9:
        bucket_size = 1.0
    buckets = {}
    wide = []
    for idx, tri in enumerate(triangles):
        bb = tri[3]
        ix0 = int(math.floor(bb[0] / bucket_size))
        ix1 = int(math.floor(bb[1] / bucket_size))
        iy0 = int(math.floor(bb[2] / bucket_size))
        iy1 = int(math.floor(bb[3] / bucket_size))
        nx = int(max(0, ix1 - ix0 + 1))
        ny = int(max(0, iy1 - iy0 + 1))
        if int(nx * ny) > int(max(1, max_cells_per_triangle)):
            wide.append(idx)
            continue
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                buckets.setdefault((ix, iy), []).append(idx)

    if len(wide) > int(max(1, max_wide_items)):
        stride = int(math.ceil(float(len(wide)) / float(max(1, max_wide_items))))
        wide = wide[::max(1, stride)]
    return buckets, wide


def point_in_tri_z(x, y, p0, p1, p2):
    x0, y0 = p0.x, p0.y
    x1, y1 = p1.x, p1.y
    x2, y2 = p2.x, p2.y
    den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if abs(den) <= 1e-14:
        return None
    w0 = ((y1 - y2) * (x - x2) + (x2 - x1) * (y - y2)) / den
    w1 = ((y2 - y0) * (x - x2) + (x0 - x2) * (y - y2)) / den
    w2 = 1.0 - w0 - w1
    tol = 1e-9
    if w0 < -tol or w1 < -tol or w2 < -tol:
        return None
    return float(w0 * p0.z + w1 * p1.z + w2 * p2.z)


def z_at_xy(x, y, triangles, buckets, bucket_size, wide_indices=None, max_candidates=None):
    ix = int(math.floor(float(x) / bucket_size))
    iy = int(math.floor(float(y) / bucket_size))
    cand = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cand.extend(buckets.get((ix + dx, iy + dy), []))
    if wide_indices:
        cand.extend(wide_indices)
    if max_candidates is not None and int(max_candidates) > 0 and len(cand) > int(max_candidates):
        stride = int(max(2, math.ceil(float(len(cand)) / float(max_candidates))))
        cand = cand[::stride]
    if not cand:
        return None

    z_best = None
    seen = set()
    for idx in cand:
        if idx in seen:
            continue
        seen.add(idx)
        p0, p1, p2, bb = triangles[idx]
        if x < bb[0] - 1e-9 or x > bb[1] + 1e-9 or y < bb[2] - 1e-9 or y > bb[3] + 1e-9:
            continue
        z = point_in_tri_z(x, y, p0, p1, p2)
        if z is None:
            continue
        if z_best is None or z > z_best:
            z_best = z
    return z_best


def decimate_triangles(triangles, max_count: int):
    n = int(len(triangles))
    if n <= 0:
        return triangles
    m = int(max_count)
    if m <= 0 or n <= m:
        return triangles
    stride = int(max(2, math.ceil(float(n) / float(m))))
    return triangles[::stride]


def iter_grid_centers(xmin, xmax, ymin, ymax, step):
    if step <= 1e-9:
        step = 1.0
    x = xmin + 0.5 * step
    while x <= xmax - 0.5 * step + 1e-9:
        y = ymin + 0.5 * step
        while y <= ymax - 0.5 * step + 1e-9:
            yield x, y
            y += step
        x += step
