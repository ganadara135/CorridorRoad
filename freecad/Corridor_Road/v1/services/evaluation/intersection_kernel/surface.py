"""Stages K5 and K6: the intersection patch TIN and the side slope around it.

K5 triangulates the boundary of K3 with the crown lines of K4 as breaklines (constrained
Delaunay), so every boundary vertex keeps the corridor's height and the inside follows the crowns.

K6 runs a side slope strip along the boundary between two mouths. A vertex on a pavement edge takes
its road's side slope at that station: the daylight point of the road's surface profile, which is
the corridor's own side slope cut there, so the strip meets the corridor's side slope at the mouth
along the same line. A curb return vertex takes the side slope of the two roads it joins, blended
along the arc (width and fall), toward the fillet centre; where that width exceeds the distance to
the centre it stops at the centre.
"""

from __future__ import annotations

import math

from dataclasses import dataclass, field

from ....models.result.intersection_geometry import KernelDiagnostic
from .cdt import ConstraintRecoveryError, constrained_delaunay, triangle_quality
from .planar import BoundaryVertex, FilletFrame, PlanarGeometry
from .road_context import STATION_TOLERANCE_M, RoadContext, left_normal
from .vertical import CrownLine


# a triangle of quality below this is skinny; the threshold the current patch quality review uses
SKINNY_TRIANGLE_QUALITY = 0.08


@dataclass
class SurfaceGeometry:
    patch_vertices_xyz: list[tuple[float, float, float]] = field(default_factory=list)
    patch_triangles: list[tuple[int, int, int]] = field(default_factory=list)
    slope_vertices_xyz: list[tuple[float, float, float]] = field(default_factory=list)
    slope_triangles: list[tuple[int, int, int]] = field(default_factory=list)
    # (role, subject, points)
    breaklines: list[tuple[str, str, tuple[tuple[float, float, float], ...]]] = field(default_factory=list)
    quality_rows: list[tuple[str, float]] = field(default_factory=list)
    diagnostics: list[KernelDiagnostic] = field(default_factory=list)


def build_surfaces(planar: PlanarGeometry, crowns: list[CrownLine], context: RoadContext, intersection_id: str) -> SurfaceGeometry:
    out = SurfaceGeometry()
    _patch(planar, crowns, out, intersection_id)
    _side_slope(planar, context, out)
    return out


def _xy_key(point) -> tuple[int, int]:
    # micrometre grid: two vertices this close are one vertex (road_context.STATION_TOLERANCE_M)
    return (round(point[0] / STATION_TOLERANCE_M), round(point[1] / STATION_TOLERANCE_M))


def _patch(planar: PlanarGeometry, crowns: list[CrownLine], out: SurfaceGeometry, intersection_id: str) -> None:
    points = list(planar.boundary_xyz)
    index_by_key = {_xy_key(p): i for i, p in enumerate(points)}
    breaklines: list[tuple[int, int]] = []
    for crown in crowns:
        indices = []
        for point in crown.points_xyz:
            key = _xy_key(point)
            if key not in index_by_key:
                index_by_key[key] = len(points)
                points.append(point)
            indices.append(index_by_key[key])
        breaklines += [(a, b) for a, b in zip(indices, indices[1:]) if a != b]
        out.breaklines.append((crown.role, crown.leg_id, tuple(points[i] for i in indices)))
    out.breaklines.append(("boundary", intersection_id, tuple(planar.boundary_xyz) + (planar.boundary_xyz[0],)))
    holes: list[list[int]] = []
    for hole in planar.holes_xyz:
        indices = []
        for point in hole:
            key = _xy_key(point)
            if key not in index_by_key:
                index_by_key[key] = len(points)
                points.append(point)
            indices.append(index_by_key[key])
        holes.append(indices)
        out.breaklines.append(("island", intersection_id, tuple(hole) + (hole[0],)))
    xy = [(p[0], p[1]) for p in points]
    try:
        triangles = constrained_delaunay(xy, list(range(len(planar.boundary_xyz))), breaklines, holes)
    except ConstraintRecoveryError as exc:
        out.diagnostics.append(
            KernelDiagnostic("patch_breakline_not_recovered", "error", intersection_id, None, f"{exc}; a crown line crosses the boundary", "partial")
        )
        return
    area = sum(abs(_orient(xy[a], xy[b], xy[c])) * 0.5 for a, b, c in triangles)
    if abs(area - planar.boundary_area_m2) > max(1.0e-6 * planar.boundary_area_m2, 1.0e-6):
        out.diagnostics.append(
            KernelDiagnostic(
                "patch_area_mismatch", "error", intersection_id, None,
                f"the triangles cover {area:.6f} m2 of the {planar.boundary_area_m2:.6f} m2 boundary", "partial",
            )
        )
    out.patch_vertices_xyz = points
    out.patch_triangles = triangles
    qualities = [triangle_quality(xy[a], xy[b], xy[c]) for a, b, c in triangles]
    out.quality_rows += [
        ("patch_triangle_count", float(len(triangles))),
        ("patch_triangle_min_quality", min(qualities) if qualities else 0.0),
        ("patch_triangle_skinny_count", float(sum(1 for q in qualities if q < SKINNY_TRIANGLE_QUALITY))),
    ]


def _is_mouth_segment(a: BoundaryVertex, b: BoundaryVertex) -> bool:
    if not a.road_ref or a.road_ref != b.road_ref or abs(a.station - b.station) > STATION_TOLERANCE_M:
        return False
    return a.kind == "mouth" or b.kind == "mouth" or (a.kind == "edge" and b.kind == "edge" and a.road_side != b.road_side)


def _runs(vertices: list[BoundaryVertex]) -> list[list[BoundaryVertex]]:
    """Split the closed boundary at its mouths into the runs a side slope follows."""

    count = len(vertices)
    cuts = [i for i in range(count) if _is_mouth_segment(vertices[i], vertices[(i + 1) % count])]
    if not cuts:
        return [vertices + vertices[:1]]
    runs = []
    for position, cut in enumerate(cuts):
        end = cuts[(position + 1) % len(cuts)]
        run, index = [], (cut + 1) % count
        while True:
            vertex = vertices[index]
            if vertex.kind != "mouth":
                run.append(vertex)
            if index == end:
                break
            index = (index + 1) % count
        if len(run) >= 2:
            runs.append(run)
    return runs


def _side_slope(planar: PlanarGeometry, context: RoadContext, out: SurfaceGeometry) -> None:
    missing = 0
    collapsed = 0
    for run in _runs(planar.boundary_vertices):
        pairs = []
        for vertex in run:
            outer, was_collapsed = _outer_point(vertex, planar.fillet_frames, context)
            collapsed += int(was_collapsed)
            if outer is None:
                missing += 1
                pairs.append(None)
            else:
                pairs.append((vertex.xyz, outer))
        out.breaklines.append(("slope_toe", f"{run[0].road_ref or run[0].corner_key}", tuple(p[1] for p in pairs if p)))
        for first, second in zip(pairs, pairs[1:]):
            if first is None or second is None:
                continue
            _add_quad(out, first[0], second[0], second[1], first[1])
    if missing:
        out.diagnostics.append(
            KernelDiagnostic(
                "side_slope_daylight_missing", "warning", "", None,
                f"{missing} boundary vertices have no Applied Section daylight point on their side; the strip is open there", "partial",
            )
        )
    if collapsed:
        out.diagnostics.append(
            KernelDiagnostic(
                "corner_side_slope_wider_than_radius", "warning", "", None,
                f"{collapsed} curb return side slope points stop at the fillet centre; the side slope is wider than the radius", "partial",
            )
        )
    xy = [(p[0], p[1]) for p in out.slope_vertices_xyz]
    qualities = [triangle_quality(xy[a], xy[b], xy[c]) for a, b, c in out.slope_triangles]
    out.quality_rows += [
        ("slope_triangle_count", float(len(out.slope_triangles))),
        ("slope_triangle_min_quality", min(qualities) if qualities else 0.0),
        ("slope_triangle_skinny_count", float(sum(1 for q in qualities if q < SKINNY_TRIANGLE_QUALITY))),
        ("slope_vertex_without_daylight_count", float(missing)),
        ("slope_arc_vertex_count", float(sum(1 for v in planar.boundary_vertices if v.kind == "arc"))),
    ]


def _side_slope_at(context: RoadContext, road_ref: str, station: float, side: str):
    """(width, fall) of the side slope at a road edge, and the daylight point, from the profile."""

    profile = context.surface_profile(road_ref, station)
    if profile is None or not profile.fg:
        return None
    daylight = profile.daylight(side)
    if daylight is None:
        return None
    edge = profile.edge(side)
    return abs(daylight[0] - edge[0]), daylight[1] - edge[1], daylight


def _outer_point(vertex: BoundaryVertex, frames: dict[str, FilletFrame], context: RoadContext):
    if vertex.kind == "edge":
        slope = _side_slope_at(context, vertex.road_ref, vertex.station, vertex.road_side)
        if slope is None:
            return None, False
        offset, z = slope[2]
        x, y = context.point_xy(vertex.road_ref, vertex.station)
        normal = left_normal(context.tangent_xy(vertex.road_ref, vertex.station))
        return (x + normal[0] * offset, y + normal[1] * offset, z), False
    if vertex.kind in {"arc", "ring"}:
        frame = frames.get(vertex.corner_key)
        if frame is None:
            return None, False
        a = _side_slope_at(context, frame.from_road, frame.from_station, frame.from_side)
        b = _side_slope_at(context, frame.to_road, frame.to_station, frame.to_side)
        if a is None or b is None:
            return None, False
        ratio = vertex.arc_ratio
        width = a[0] + (b[0] - a[0]) * ratio
        fall = a[1] + (b[1] - a[1]) * ratio
        center = vertex.center_xy or frame.center_xy
        dx, dy = center[0] - vertex.xyz[0], center[1] - vertex.xyz[1]
        distance = math.hypot(dx, dy)
        if distance <= 1.0e-12:
            return None, False
        if vertex.kind == "ring":
            # outside the ring the slope runs away from the roundabout centre, with nothing to meet
            return (vertex.xyz[0] - dx / distance * width, vertex.xyz[1] - dy / distance * width, vertex.xyz[2] + fall), False
        reach = min(width, distance)
        return (vertex.xyz[0] + dx / distance * reach, vertex.xyz[1] + dy / distance * reach, vertex.xyz[2] + fall), width > distance
    return None, False


def _add_quad(out: SurfaceGeometry, i0, i1, o1, o0) -> None:
    """Two triangles for the strip cell i0 i1 o1 o0, split along its shorter diagonal."""

    base = len(out.slope_vertices_xyz)
    out.slope_vertices_xyz += [i0, i1, o1, o0]
    a, b, c, d = base, base + 1, base + 2, base + 3
    pts = out.slope_vertices_xyz
    if math.dist(pts[a][:2], pts[c][:2]) <= math.dist(pts[b][:2], pts[d][:2]):
        candidates = [(a, b, c), (a, c, d)]
    else:
        candidates = [(a, b, d), (b, c, d)]
    for tri in candidates:
        signed = _orient(pts[tri[0]], pts[tri[1]], pts[tri[2]])
        if abs(signed) <= 1.0e-12:
            continue
        out.slope_triangles.append(tri if signed > 0.0 else (tri[0], tri[2], tri[1]))


def _orient(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
