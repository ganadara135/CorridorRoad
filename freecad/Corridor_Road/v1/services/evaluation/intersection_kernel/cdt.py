"""Constrained Delaunay triangulation of a simple polygon with interior breaklines (stage K5).

Bowyer-Watson inserts the points; every constraint edge (the polygon's own edges and the
breaklines) is then recovered by diagonal flips (Sloan 1993); triangles outside the polygon are
dropped; and the remaining unconstrained edges are flipped back to Delaunay. The breaklines must
lie inside the polygon and may meet only at shared points. Everything is in plan XY; heights ride
along by index. Deterministic: points and edges are visited in a fixed order.
"""

from __future__ import annotations

import math


# orientation and in-circle tests treat values this close to zero as zero; the inputs are in
# metres with points at least millimetres apart, so 1e-12 m2 is far below any real area
_EPS = 1.0e-12
# a Delaunay flip must beat the in-circle test by this much, so co-circular points (a regular
# grid of edge samples) do not flip back and forth on rounding noise
_FLIP_EPS = 1.0e-10


class ConstraintRecoveryError(RuntimeError):
    """A constraint edge could not be recovered by flips (it crosses another constraint)."""


def constrained_delaunay(
    points: list[tuple[float, float]],
    polygon: list[int],
    breaklines: list[tuple[int, int]],
) -> list[tuple[int, int, int]]:
    """Return counter-clockwise triangles (point indices) covering the polygon.

    `polygon` lists the boundary point indices counter-clockwise; `breaklines` are extra edges
    between point indices inside it.
    """

    count = len(points)
    # work on coordinates centred and scaled to about 1, so the fixed tolerances are relative and
    # world coordinates of hundreds of kilometres lose no precision in the in-circle test
    points = _normalized(points)
    triangles = _bowyer_watson(points)
    constraints = {_key(polygon[i], polygon[(i + 1) % len(polygon)]) for i in range(len(polygon))}
    constraints |= {_key(a, b) for a, b in breaklines if a != b}
    all_points = list(points) + _super_points(points)
    for a, b in sorted(constraints):
        triangles = _recover(all_points, triangles, a, b, constraints)
    boundary = [points[index] for index in polygon]
    triangles = [
        tri for tri in triangles
        if max(tri) < count and _inside(_centroid(points, tri), boundary)
    ]
    return _delaunay_flips(points, triangles, constraints)


def _normalized(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    scale = max(max(xs) - min(xs), max(ys) - min(ys), 1.0e-9)
    return [((x - cx) / scale, (y - cy) / scale) for x, y in points]


def triangle_quality(a, b, c) -> float:
    """0..1, 1 for an equilateral triangle: 4 sqrt(3) area / sum of squared edge lengths."""

    lengths = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (b[0] - c[0]) ** 2 + (b[1] - c[1]) ** 2 + (c[0] - a[0]) ** 2 + (c[1] - a[1]) ** 2
    if lengths <= _EPS:
        return 0.0
    return 4.0 * math.sqrt(3.0) * abs(_orient(a, b, c)) * 0.5 / lengths


def _key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _orient(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _incircle(a, b, c, d) -> float:
    adx, ady = a[0] - d[0], a[1] - d[1]
    bdx, bdy = b[0] - d[0], b[1] - d[1]
    cdx, cdy = c[0] - d[0], c[1] - d[1]
    return (
        (adx * adx + ady * ady) * (bdx * cdy - cdx * bdy)
        - (bdx * bdx + bdy * bdy) * (adx * cdy - cdx * ady)
        + (cdx * cdx + cdy * cdy) * (adx * bdy - bdx * ady)
    )


def _super_points(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0) * 20.0
    return [(cx - 2.0 * span, cy - span), (cx + 2.0 * span, cy - span), (cx, cy + 2.0 * span)]


def _bowyer_watson(points) -> list[tuple[int, int, int]]:
    count = len(points)
    all_points = list(points) + _super_points(points)
    triangles = [(count, count + 1, count + 2)]
    for index in range(count):
        p = all_points[index]
        bad = [tri for tri in triangles if _incircle(*(all_points[v] for v in tri), p) > _EPS]
        edges: dict[tuple[int, int], int] = {}
        directed: dict[tuple[int, int], tuple[int, int]] = {}
        for a, b, c in bad:
            for u, v in ((a, b), (b, c), (c, a)):
                k = _key(u, v)
                edges[k] = edges.get(k, 0) + 1
                directed[k] = (u, v)
        bad_set = set(bad)
        triangles = [tri for tri in triangles if tri not in bad_set]
        for k in sorted(edges):
            if edges[k] == 1:
                u, v = directed[k]
                triangles.append((u, v, index))
    return triangles


def _edge_owners(triangles):
    owners: dict[tuple[int, int], list[int]] = {}
    for position, (a, b, c) in enumerate(triangles):
        for u, v in ((a, b), (b, c), (c, a)):
            owners.setdefault(_key(u, v), []).append(position)
    return owners


def _crosses(p, q, a, b) -> bool:
    """True when the open segments pq and ab cross at one interior point."""

    d1, d2 = _orient(a, b, p), _orient(a, b, q)
    d3, d4 = _orient(p, q, a), _orient(p, q, b)
    return ((d1 > _EPS and d2 < -_EPS) or (d1 < -_EPS and d2 > _EPS)) and ((d3 > _EPS and d4 < -_EPS) or (d3 < -_EPS and d4 > _EPS))


def _flip(triangles, owners, key):
    first, second = owners[key]
    u, v = key
    t1, t2 = triangles[first], triangles[second]
    p = next(x for x in t1 if x not in key)
    q = next(x for x in t2 if x not in key)
    return first, second, u, v, p, q


def _recover(points, triangles, a, b, constraints):
    owners = _edge_owners(triangles)
    if (a, b) in owners or (b, a) in owners or _key(a, b) in owners:
        return triangles
    pa, pb = points[a], points[b]
    queue = [
        key for key in sorted(owners)
        if a not in key and b not in key and _crosses(points[key[0]], points[key[1]], pa, pb)
    ]
    guard = 0
    while queue:
        guard += 1
        if guard > 50 * (len(triangles) + 10):
            raise ConstraintRecoveryError(f"constraint {a}-{b} could not be recovered")
        key = queue.pop(0)
        owners = _edge_owners(triangles)
        if key not in owners or len(owners[key]) != 2:
            continue
        if key in constraints:
            raise ConstraintRecoveryError(f"constraint {a}-{b} crosses constraint {key[0]}-{key[1]}")
        first, second, u, v, p, q = _flip(triangles, owners, key)
        # the quadrilateral u p v q must be strictly convex for the diagonal p q to replace u v
        pu, pv, pp, pq = points[u], points[v], points[p], points[q]
        if not _crosses(pp, pq, pu, pv):
            queue.append(key)
            continue
        new1, new2 = _ccw(points, (p, q, u)), _ccw(points, (q, p, v))
        triangles[first], triangles[second] = new1, new2
        new_key = _key(p, q)
        if a not in new_key and b not in new_key and _crosses(pp, pq, pa, pb):
            queue.append(new_key)
    return triangles


def _ccw(points, tri):
    a, b, c = tri
    return (a, b, c) if _orient(points[a], points[b], points[c]) > 0.0 else (a, c, b)


def _delaunay_flips(points, triangles, constraints):
    triangles = [_ccw(points, tri) for tri in triangles]
    for _ in range(len(triangles) * len(triangles) + 1):
        owners = _edge_owners(triangles)
        flipped = False
        for key in sorted(owners):
            if key in constraints or len(owners[key]) != 2:
                continue
            first, second, u, v, p, q = _flip(triangles, owners, key)
            t1 = triangles[first]
            if _incircle(*(points[x] for x in t1), points[q]) <= _FLIP_EPS:
                continue
            if not _crosses(points[p], points[q], points[u], points[v]):
                continue
            triangles[first], triangles[second] = _ccw(points, (p, q, u)), _ccw(points, (q, p, v))
            flipped = True
            break
        if not flipped:
            break
    return triangles


def _centroid(points, tri):
    return (sum(points[v][0] for v in tri) / 3.0, sum(points[v][1] for v in tri) / 3.0)


def _inside(point, polygon) -> bool:
    x, y = point
    inside = False
    for index, a in enumerate(polygon):
        b = polygon[(index + 1) % len(polygon)]
        if (a[1] > y) != (b[1] > y):
            cross = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if cross > x:
                inside = not inside
    return inside
