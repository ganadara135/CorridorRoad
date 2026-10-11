# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.


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
