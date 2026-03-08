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


def world_point_to_local_cached(p_world, params, cache=None, max_cache_size: int = 500000):
    if cache is None:
        return world_point_to_local(p_world, params)
    key = (float(p_world.x), float(p_world.y), float(p_world.z))
    q = cache.get(key)
    if q is not None:
        return q
    q = world_point_to_local(p_world, params)
    try:
        if int(len(cache)) >= int(max_cache_size):
            cache.clear()
        cache[key] = q
    except Exception:
        pass
    return q


def triangle_bbox_xy(p0, p1, p2):
    return _ssc.triangle_bbox_xy(p0, p1, p2)


def triangles_world_to_local(triangles, doc_or_obj=None, params=None, point_cache=None):
    if not triangles:
        return []
    tr = params if params is not None else world_to_local_params(doc_or_obj)
    cache = point_cache if point_cache is not None else {}
    out = []
    for tri in triangles:
        try:
            p0, p1, p2, _bb = tri
            q0 = world_point_to_local_cached(p0, tr, cache=cache)
            q1 = world_point_to_local_cached(p1, tr, cache=cache)
            q2 = world_point_to_local_cached(p2, tr, cache=cache)
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


def world_xy_bounds_to_local(x0, x1, y0, y1, doc_or_obj=None, params=None):
    x0 = float(x0)
    x1 = float(x1)
    y0 = float(y0)
    y1 = float(y1)
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    tr = params if params is not None else world_to_local_params(doc_or_obj)
    corners = (
        App.Vector(x0, y0, 0.0),
        App.Vector(x0, y1, 0.0),
        App.Vector(x1, y0, 0.0),
        App.Vector(x1, y1, 0.0),
    )
    xs = []
    ys = []
    for p in corners:
        q = world_point_to_local(p, tr)
        xs.append(float(q.x))
        ys.append(float(q.y))
    return min(xs), max(xs), min(ys), max(ys)
