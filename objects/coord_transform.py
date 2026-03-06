import math

import FreeCAD as App

from objects.obj_project import get_coordinate_setup
from objects import surface_sampling_core as _ssc


def world_to_local_params(doc_or_obj):
    c = get_coordinate_setup(doc_or_obj)
    th = math.radians(float(c.get("NorthRotationDeg", 0.0)))
    return {
        "cs": math.cos(th),
        "sn": math.sin(th),
        "e0": float(c.get("ProjectOriginE", 0.0)),
        "n0": float(c.get("ProjectOriginN", 0.0)),
        "z0": float(c.get("ProjectOriginZ", 0.0)),
        "lx": float(c.get("LocalOriginX", 0.0)),
        "ly": float(c.get("LocalOriginY", 0.0)),
        "lz": float(c.get("LocalOriginZ", 0.0)),
    }


def world_point_to_local(p_world, params):
    de = float(p_world.x) - float(params["e0"])
    dn = float(p_world.y) - float(params["n0"])
    x = float(params["lx"]) + float(params["cs"]) * de + float(params["sn"]) * dn
    y = float(params["ly"]) - float(params["sn"]) * de + float(params["cs"]) * dn
    z = float(params["lz"]) + (float(p_world.z) - float(params["z0"]))
    return App.Vector(x, y, z)


def triangle_bbox_xy(p0, p1, p2):
    return _ssc.triangle_bbox_xy(p0, p1, p2)


def triangles_world_to_local(triangles, doc_or_obj=None, params=None):
    if not triangles:
        return []
    tr = params if params is not None else world_to_local_params(doc_or_obj)
    out = []
    for tri in triangles:
        try:
            p0, p1, p2, _bb = tri
            q0 = world_point_to_local(p0, tr)
            q1 = world_point_to_local(p1, tr)
            q2 = world_point_to_local(p2, tr)
            bb = triangle_bbox_xy(q0, q1, q2)
            out.append((q0, q1, q2, bb))
        except Exception:
            continue
    return out


def triangles_bbox_xy(triangles):
    if not triangles:
        raise Exception("No triangles available for bounds.")
    xmin = None
    xmax = None
    ymin = None
    ymax = None
    for _p0, _p1, _p2, bb in triangles:
        bx0, bx1, by0, by1 = bb
        xmin = float(bx0) if xmin is None else min(float(xmin), float(bx0))
        xmax = float(bx1) if xmax is None else max(float(xmax), float(bx1))
        ymin = float(by0) if ymin is None else min(float(ymin), float(by0))
        ymax = float(by1) if ymax is None else max(float(ymax), float(by1))
    return float(xmin), float(xmax), float(ymin), float(ymax)
