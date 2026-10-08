"""Plan geometry of an intersection: corner fillets, leg mouths, the boundary, the hand-off spans.

Stages K1, K2, K3 and the planar part of K7 of `V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md`
section 5.6. Every edge is the real pavement edge of the evaluated road, the centreline offset by
the Applied Sections' half width at each station, so a curved or widening road is followed and
the fillets are tangent to the edges the corridor actually builds.

Leg frame: a leg looks outward from the anchor. Its left edge faces its counter-clockwise
neighbour. For an `ahead` leg that is the road's left side, for a `back` leg the road's right.
Elevations: a vertex on a pavement edge or across a mouth takes the finished grade of the road's
surface profile at that station (the Applied Sections, linear between two of them), so the boundary
is the corridor surface's own edge. Without a profile it takes the centreline finished grade.
"""

from __future__ import annotations

import math

from dataclasses import dataclass, field

from ....models.result.intersection_geometry import CornerGeometry, KernelDiagnostic, LegGeometry
from .constants import ARC_MAX_STEP_DEG, EDGE_SAMPLE_STEP_M, FILLET_SEARCH_LENGTH_M, MOUTH_CLEARANCE_M
from .resolve import ResolvedCorner, ResolvedIntersection, ResolvedLeg
from .road_context import STATION_TOLERANCE_M, RoadContext, left_normal, segment_intersection


@dataclass(frozen=True)
class BoundaryVertex:
    """One boundary vertex and what it lies on: a pavement `edge` (road, station, road side), a
    `mouth` cut (road, station) or a curb return `arc` (corner, position 0..1 along it)."""

    xyz: tuple[float, float, float]
    kind: str
    road_ref: str = ""
    station: float = 0.0
    road_side: str = ""
    corner_key: str = ""
    arc_ratio: float = 0.0
    # an `arc` vertex's circle centre (its side slope runs toward it); a `ring` vertex's ring
    # centre (its side slope runs away from it)
    center_xy: tuple[float, float] | None = None


@dataclass(frozen=True)
class FilletFrame:
    """A solved curb return, with the edge points it is tangent to."""

    corner_key: str
    center_xy: tuple[float, float]
    radius_m: float
    from_road: str
    from_station: float
    from_side: str
    to_road: str
    to_station: float
    to_side: str


@dataclass
class PlanarGeometry:
    legs: list[LegGeometry] = field(default_factory=list)
    corners: list[CornerGeometry] = field(default_factory=list)
    boundary_xyz: list[tuple[float, float, float]] = field(default_factory=list)
    boundary_vertices: list[BoundaryVertex] = field(default_factory=list)
    fillet_frames: dict[str, FilletFrame] = field(default_factory=dict)
    # leg id -> distance of its mouth from the anchor
    mouth_distance: dict[str, float] = field(default_factory=dict)
    # roundabout: the central island, clockwise, and the ring's tangent points of each corner
    holes_xyz: list[list[tuple[float, float, float]]] = field(default_factory=list)
    ring_tangents: dict[str, tuple[tuple[float, float], tuple[float, float]]] = field(default_factory=dict)
    boundary_area_m2: float = 0.0
    clip_spans: list[tuple[str, float, float]] = field(default_factory=list)
    supplemental_stations: list[tuple[str, float]] = field(default_factory=list)
    diagnostics: list[KernelDiagnostic] = field(default_factory=list)


@dataclass(frozen=True)
class _Fillet:
    center_xy: tuple[float, float]
    from_distance: float
    to_distance: float
    arc_xyz: tuple[tuple[float, float, float], ...]
    # per arc point: (kind, centre); empty for a plain fillet ("arc" about center_xy)
    point_tags: tuple[tuple[str, tuple[float, float]], ...] = ()
    # roundabout: where the from and to flares touch the ring
    ring_from_xy: tuple[float, float] | None = None
    ring_to_xy: tuple[float, float] | None = None


def build_planar_geometry(resolved: ResolvedIntersection, context: RoadContext) -> PlanarGeometry:
    out = PlanarGeometry()
    enabled = resolved.enabled_legs()

    # K1
    fillets: dict[str, _Fillet] = {}
    for corner in resolved.corners:
        if corner.treatment == "ring":
            fillet = _ring_corner(resolved, context, corner, out.diagnostics)
        elif corner.treatment == "fillet":
            fillet = _corner_fillet(resolved, context, corner, out.diagnostics)
        else:
            continue
        if fillet is not None:
            fillets[corner.corner_key] = fillet

    # K2: a leg is handed back to the road beyond its outermost tangent point
    mouth_distance: dict[str, float] = {}
    for leg in enabled:
        distances = [fillets[c.corner_key].from_distance for c in resolved.corners if c.from_leg_id == leg.leg_id and c.corner_key in fillets]
        distances += [fillets[c.corner_key].to_distance for c in resolved.corners if c.to_leg_id == leg.leg_id and c.corner_key in fillets]
        if not distances:
            out.diagnostics.append(
                KernelDiagnostic("leg_mouth_without_corner", "error", leg.leg_id, None, "the leg has no solved curb return to end at", "blocked")
            )
            continue
        distance = max(distances) + MOUTH_CLEARANCE_M
        if distance > leg.length_m + STATION_TOLERANCE_M:
            out.diagnostics.append(
                KernelDiagnostic(
                    "leg_too_short_for_corner", "error", leg.leg_id, _station(resolved, leg, leg.length_m),
                    f"the curb return needs {distance:.3f} m of the leg, the road has {leg.length_m:.3f} m", "blocked",
                )
            )
            continue
        mouth_distance[leg.leg_id] = distance

    for leg in resolved.legs:
        distance = mouth_distance.get(leg.leg_id)
        if not leg.enabled or distance is None:
            out.legs.append(LegGeometry(leg.leg_id, leg.road_ref, leg.side, leg.bearing_rad, leg.enabled))
            continue
        station = _station(resolved, leg, distance)
        out.legs.append(
            LegGeometry(
                leg.leg_id, leg.road_ref, leg.side, leg.bearing_rad, True,
                mouth_station=station,
                mouth_left_xyz=_edge_xyz(context, leg.road_ref, station, "left"),
                mouth_right_xyz=_edge_xyz(context, leg.road_ref, station, "right"),
            )
        )

    for corner in resolved.corners:
        fillet = fillets.get(corner.corner_key)
        if fillet is None:
            out.corners.append(CornerGeometry(corner.corner_key, corner.from_leg_id, corner.to_leg_id, corner.treatment, corner.radius_m if corner.treatment == "fillet" else 0.0))
            continue
        out.corners.append(
            CornerGeometry(
                corner.corner_key, corner.from_leg_id, corner.to_leg_id, corner.treatment, corner.radius_m,
                center_xy=fillet.center_xy,
                from_tangent_station=_station(resolved, resolved.leg(corner.from_leg_id), fillet.from_distance),
                to_tangent_station=_station(resolved, resolved.leg(corner.to_leg_id), fillet.to_distance),
                arc_xyz=fillet.arc_xyz,
            )
        )

    if any(row.effect == "blocked" for row in out.diagnostics):
        return out

    out.mouth_distance = dict(mouth_distance)
    for corner in resolved.corners:
        fillet = fillets.get(corner.corner_key)
        if fillet is None:
            continue
        if fillet.ring_from_xy is not None:
            out.ring_tangents[corner.corner_key] = (fillet.ring_from_xy, fillet.ring_to_xy)
        a, b = resolved.leg(corner.from_leg_id), resolved.leg(corner.to_leg_id)
        out.fillet_frames[corner.corner_key] = FilletFrame(
            corner.corner_key, fillet.center_xy, corner.radius_m,
            a.road_ref, _station(resolved, a, fillet.from_distance), _road_side(a, "left"),
            b.road_ref, _station(resolved, b, fillet.to_distance), _road_side(b, "right"),
        )

    # K3
    vertices = _boundary(resolved, context, fillets, mouth_distance, out.diagnostics)
    boundary = [vertex.xyz for vertex in vertices]
    area = _signed_area(boundary)
    if len(boundary) < 3 or area <= 0.0:
        out.diagnostics.append(
            KernelDiagnostic("boundary_not_counter_clockwise", "error", resolved.spec.intersection_id, None, f"signed area {area:.3f} m2; check the leg order and the corner fillets", "blocked")
        )
        return out
    crossing = _first_self_crossing(boundary)
    if crossing is not None:
        out.diagnostics.append(
            KernelDiagnostic("boundary_self_crossing", "error", resolved.spec.intersection_id, None, f"boundary edges {crossing[0]} and {crossing[1]} cross; a radius may be too large for the legs", "blocked")
        )
        return out
    out.boundary_xyz = boundary
    out.boundary_vertices = vertices
    out.boundary_area_m2 = area
    if resolved.ring is not None:
        island = _circle(resolved.anchor_xy, resolved.ring.island_radius_m, resolved.ring.island_z, clockwise=True)
        if not all(_inside_xy(point, boundary) for point in island):
            out.diagnostics.append(
                KernelDiagnostic("roundabout_island_outside_boundary", "error", resolved.spec.intersection_id, None, "the central island does not lie inside the paved boundary", "blocked")
            )
            return out
        out.holes_xyz = [island]
        out.boundary_area_m2 = area + _signed_area(island)

    # K7, planar: the span of each road the intersection owns, and the stations it hands back at
    for road_ref, anchor_station in resolved.anchor_station_by_road.items():
        mouths = {leg.side: leg.mouth_station for leg in out.legs if leg.road_ref == road_ref and leg.mouth_station is not None}
        if not mouths:
            continue
        start = mouths.get("back", anchor_station)
        end = mouths.get("ahead", anchor_station)
        out.clip_spans.append((road_ref, min(start, end), max(start, end)))
        for side in ("back", "ahead"):
            if side in mouths:
                out.supplemental_stations.append((road_ref, mouths[side]))
    return out


def _station(resolved: ResolvedIntersection, leg: ResolvedLeg, distance: float) -> float:
    anchor = resolved.anchor_station_by_road[leg.road_ref]
    return anchor + distance if leg.side == "ahead" else anchor - distance


def _road_side(leg: ResolvedLeg, leg_side: str) -> str:
    """The road side ("left" / "right") of a leg's outward-looking left or right edge."""

    if leg.side == "ahead":
        return leg_side
    return "right" if leg_side == "left" else "left"


def _edge_xy(context: RoadContext, road_ref: str, station: float, road_side: str, extra: float = 0.0) -> tuple[float, float] | None:
    width = context.pavement_half_width(road_ref, station, road_side)
    if width is None:
        return None
    x, y = context.point_xy(road_ref, station)
    normal = left_normal(context.tangent_xy(road_ref, station))
    sign = 1.0 if road_side == "left" else -1.0
    offset = sign * (width + extra)
    return x + normal[0] * offset, y + normal[1] * offset


def _edge_xyz(context: RoadContext, road_ref: str, station: float, road_side: str) -> tuple[float, float, float] | None:
    xy = _edge_xy(context, road_ref, station, road_side)
    if xy is None:
        return None
    return xy[0], xy[1], _grade(context, road_ref, station, road_side)


def _grade(context: RoadContext, road_ref: str, station: float, road_side: str = "") -> float:
    if road_side:
        profile = context.surface_profile(road_ref, station)
        if profile is not None and profile.fg:
            return float(profile.edge(road_side)[1])
    value = context.finished_grade_z(road_ref, station)
    return float(value) if value is not None else 0.0


def _leg_distances(resolved: ResolvedIntersection, context: RoadContext, leg: ResolvedLeg, start: float, end: float) -> list[float]:
    """Distances from the anchor along a leg: both ends, the road's vertices, and a regular step."""

    values = {start, end}
    steps = int(math.floor((end - start) / EDGE_SAMPLE_STEP_M))
    values.update(start + EDGE_SAMPLE_STEP_M * index for index in range(1, steps + 1))
    anchor = resolved.anchor_station_by_road[leg.road_ref]
    for station in context.vertex_stations(leg.road_ref, _station(resolved, leg, start), _station(resolved, leg, end)):
        values.add(abs(station - anchor))
    return sorted(value for value in values if start - STATION_TOLERANCE_M <= value <= end + STATION_TOLERANCE_M)


def _corner_fillet(resolved: ResolvedIntersection, context: RoadContext, corner: ResolvedCorner, diagnostics: list[KernelDiagnostic]) -> _Fillet | None:
    """K1: the fillet of radius R tangent to the from leg's left edge and the to leg's right edge.

    Its centre is R beyond both edges, so it is the first crossing, outward from the anchor, of the
    two edges offset by R. Each tangent point is the edge point at the station of the centre.
    """

    radius = float(corner.radius_m)
    if radius <= 0.0:
        diagnostics.append(KernelDiagnostic("corner_radius_not_positive", "error", corner.corner_key, None, "give the corner a positive radius", "blocked"))
        return None
    a, b = resolved.leg(corner.from_leg_id), resolved.leg(corner.to_leg_id)
    side_a, side_b = _road_side(a, "left"), _road_side(b, "right")
    curves = []
    for leg, side in ((a, side_a), (b, side_b)):
        distances = _leg_distances(resolved, context, leg, 0.0, min(leg.length_m, FILLET_SEARCH_LENGTH_M))
        points = []
        for distance in distances:
            xy = _edge_xy(context, leg.road_ref, _station(resolved, leg, distance), side, radius)
            if xy is None:
                diagnostics.append(
                    KernelDiagnostic(
                        "pavement_edge_owner_missing", "error", leg.road_ref, _station(resolved, leg, distance),
                        "the road has no Applied Section pavement width here; generate Applied Sections for it", "blocked",
                    )
                )
                return None
            points.append(xy)
        curves.append((distances, points))
    (dist_a, pts_a), (dist_b, pts_b) = curves
    best = None
    for i in range(len(pts_a) - 1):
        for j in range(len(pts_b) - 1):
            hit = segment_intersection(pts_a[i], pts_a[i + 1], pts_b[j], pts_b[j + 1])
            if hit is None:
                continue
            t, u = hit
            d_a = dist_a[i] + (dist_a[i + 1] - dist_a[i]) * t
            d_b = dist_b[j] + (dist_b[j + 1] - dist_b[j]) * u
            if best is None or d_a + d_b < best[0] + best[1]:
                center = (pts_a[i][0] + (pts_a[i + 1][0] - pts_a[i][0]) * t, pts_a[i][1] + (pts_a[i + 1][1] - pts_a[i][1]) * t)
                best = (d_a, d_b, center)
        if best is not None:
            break
    if best is None:
        diagnostics.append(
            KernelDiagnostic(
                "corner_fillet_no_solution", "error", corner.corner_key, None,
                f"no circle of radius {radius:.3f} m touches both pavement edges in front of the anchor; reduce the radius", "blocked",
            )
        )
        return None
    d_a, d_b, center = best
    start = _edge_xyz(context, a.road_ref, _station(resolved, a, d_a), side_a)
    end = _edge_xyz(context, b.road_ref, _station(resolved, b, d_b), side_b)
    return _Fillet(center, d_a, d_b, _arc(center, start, end))


def _arc(center, start, end) -> tuple[tuple[float, float, float], ...]:
    a0 = math.atan2(start[1] - center[1], start[0] - center[0])
    a1 = math.atan2(end[1] - center[1], end[0] - center[0])
    delta = (a1 - a0 + math.pi) % math.tau - math.pi
    r0 = math.hypot(start[0] - center[0], start[1] - center[1])
    r1 = math.hypot(end[0] - center[0], end[1] - center[1])
    # the 1e-9 keeps a sweep of exactly n steps (a right angle is 18) from becoming n + 1 by round-off,
    # which would make a turned copy of the same corner a different polygon
    count = max(2, int(math.ceil(abs(math.degrees(delta)) / ARC_MAX_STEP_DEG - 1.0e-9)))
    points = [start]
    for index in range(1, count):
        ratio = index / count
        angle = a0 + delta * ratio
        radius = r0 + (r1 - r0) * ratio
        points.append((center[0] + math.cos(angle) * radius, center[1] + math.sin(angle) * radius, start[2] + (end[2] - start[2]) * ratio))
    points.append(end)
    return tuple(points)


def _boundary(resolved, context, fillets, mouth_distance, diagnostics) -> list[BoundaryVertex]:
    """K3: walk the legs counter-clockwise, out along each right edge, across the mouth, back along
    the left edge, then round the corner to the next leg. A `none` corner adds nothing: the two
    edge pieces meet at the anchor station on the same edge line. The mouth is crossed through
    every finished grade point of the road's cut there, so the patch meets the corridor surface
    point for point."""

    enabled = resolved.enabled_legs()
    corners = {corner.from_leg_id: corner for corner in resolved.corners}
    incoming = {corner.to_leg_id: corner for corner in resolved.corners}
    vertices: list[BoundaryVertex] = []
    for leg in enabled:
        before, after = incoming.get(leg.leg_id), corners.get(leg.leg_id)
        inner_right = fillets[before.corner_key].to_distance if before is not None and before.corner_key in fillets else 0.0
        inner_left = fillets[after.corner_key].from_distance if after is not None and after.corner_key in fillets else 0.0
        mouth = mouth_distance[leg.leg_id]
        right_side, left_side = _road_side(leg, "right"), _road_side(leg, "left")
        for distance in _leg_distances(resolved, context, leg, inner_right, mouth):
            station = _station(resolved, leg, distance)
            _append(vertices, _edge_xyz(context, leg.road_ref, station, right_side), "edge", leg.road_ref, station, right_side)
        for vertex in _mouth_cut(context, leg, _station(resolved, leg, mouth), diagnostics):
            _append(vertices, vertex.xyz, vertex.kind, vertex.road_ref, vertex.station, vertex.road_side)
        for distance in reversed(_leg_distances(resolved, context, leg, inner_left, mouth)):
            station = _station(resolved, leg, distance)
            _append(vertices, _edge_xyz(context, leg.road_ref, station, left_side), "edge", leg.road_ref, station, left_side)
        if after is not None and after.corner_key in fillets:
            fillet = fillets[after.corner_key]
            arc = fillet.arc_xyz
            ratios = _cumulative_ratios(arc)
            for index in range(1, len(arc) - 1):
                kind, center = fillet.point_tags[index] if fillet.point_tags else ("arc", fillet.center_xy)
                _append(vertices, arc[index], kind, corner_key=after.corner_key, arc_ratio=ratios[index], center_xy=center)
    if len(vertices) > 1 and _same_xy(vertices[0].xyz, vertices[-1].xyz):
        vertices.pop()
    return vertices


def _mouth_cut(context, leg: ResolvedLeg, station: float, diagnostics) -> list[BoundaryVertex]:
    """The finished grade points strictly between the two pavement edges at a leg's mouth, from the
    leg's right edge to its left edge."""

    profile = context.surface_profile(leg.road_ref, station)
    if profile is None or len(profile.fg) < 3:
        return []
    if not profile.exact:
        diagnostics.append(
            KernelDiagnostic(
                "mouth_section_points_do_not_pair", "warning", leg.leg_id, station,
                "the Applied Sections either side of the mouth have different points; the nearer one is used", "fallback",
            )
        )
    interior = list(profile.fg[1:-1])
    if leg.side == "back":
        interior.reverse()
    x, y = context.point_xy(leg.road_ref, station)
    normal = left_normal(context.tangent_xy(leg.road_ref, station))
    return [
        BoundaryVertex((x + normal[0] * offset, y + normal[1] * offset, z), "mouth", leg.road_ref, station)
        for offset, z in interior
    ]


def _append(vertices: list, xyz, kind: str, road_ref: str = "", station: float = 0.0, road_side: str = "", *, corner_key: str = "", arc_ratio: float = 0.0, center_xy=None) -> None:
    if xyz is None or (vertices and _same_xy(vertices[-1].xyz, xyz)):
        return
    vertices.append(BoundaryVertex(tuple(xyz), kind, road_ref, station, road_side, corner_key, arc_ratio, center_xy))


def _cumulative_ratios(points) -> list[float]:
    lengths = [0.0]
    for a, b in zip(points, points[1:]):
        lengths.append(lengths[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = lengths[-1] or 1.0
    return [value / total for value in lengths]


def _circle(center, radius: float, z: float, *, clockwise: bool = False) -> list[tuple[float, float, float]]:
    count = max(8, int(math.ceil(360.0 / ARC_MAX_STEP_DEG - 1.0e-9)))
    sign = -1.0 if clockwise else 1.0
    return [
        (center[0] + radius * math.cos(sign * math.tau * k / count), center[1] + radius * math.sin(sign * math.tau * k / count), z)
        for k in range(count)
    ]


def _inside_xy(point, polygon) -> bool:
    x, y = point[0], point[1]
    inside = False
    for index, a in enumerate(polygon):
        b = polygon[(index + 1) % len(polygon)]
        if (a[1] > y) != (b[1] > y) and a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]) > x:
            inside = not inside
    return inside


def _ring_flare(resolved, context, leg: ResolvedLeg, leg_side: str, radius: float, diagnostics, subject: str):
    """One approach's flare onto the ring: the circle of `radius` tangent to the leg's pavement edge
    on `leg_side` and outside tangent to the ring's outer edge. Returns (distance of the edge
    tangent point from the anchor, its station, the flare centre or None, the ring tangent point).
    A radius of 0 is a square corner: where the pavement edge meets the ring."""

    ring = resolved.ring
    center = resolved.anchor_xy
    side = _road_side(leg, leg_side)
    target = ring.outer_edge_radius_m + radius
    distances = _leg_distances(resolved, context, leg, 0.0, min(leg.length_m, FILLET_SEARCH_LENGTH_M))
    previous = None
    for distance in distances:
        xy = _edge_xy(context, leg.road_ref, _station(resolved, leg, distance), side, radius)
        if xy is None:
            diagnostics.append(
                KernelDiagnostic("pavement_edge_owner_missing", "error", leg.road_ref, _station(resolved, leg, distance),
                                 "the road has no Applied Section pavement width here; generate Applied Sections for it", "blocked")
            )
            return None
        reach = math.hypot(xy[0] - center[0], xy[1] - center[1])
        if previous is None and reach >= target:
            diagnostics.append(
                KernelDiagnostic("roundabout_approach_wider_than_ring", "error", leg.leg_id, None,
                                 "the approach's pavement edge already lies outside the ring at the centre; enlarge the ring", "blocked")
            )
            return None
        if previous is not None and reach >= target:
            d0, xy0, r0 = previous
            # solve |xy0 + (xy - xy0) t - c| = target on the segment
            dx, dy = xy[0] - xy0[0], xy[1] - xy0[1]
            fx, fy = xy0[0] - center[0], xy0[1] - center[1]
            a = dx * dx + dy * dy
            b = 2.0 * (fx * dx + fy * dy)
            c = fx * fx + fy * fy - target * target
            root = math.sqrt(max(b * b - 4.0 * a * c, 0.0))
            t = (-b + root) / (2.0 * a) if a > 0.0 else 0.0
            t = min(max(t, 0.0), 1.0)
            hit = (xy0[0] + dx * t, xy0[1] + dy * t)
            found = d0 + (distance - d0) * t
            station = _station(resolved, leg, found)
            scale = ring.outer_edge_radius_m / target
            ring_point = (center[0] + (hit[0] - center[0]) * scale, center[1] + (hit[1] - center[1]) * scale)
            return found, station, (hit if radius > 0.0 else None), ring_point
        previous = (distance, xy, reach)
    diagnostics.append(
        KernelDiagnostic("roundabout_flare_no_solution", "error", subject, None,
                         f"the {leg.leg_id} flare of radius {radius:.3f} m does not reach the ring within the leg", "blocked")
    )
    return None


def _ring_corner(resolved, context, corner: ResolvedCorner, diagnostics) -> _Fillet | None:
    """A roundabout corner: the from leg's flare onto the ring, the ring's outer edge counter-
    clockwise, and the to leg's flare off it."""

    ring = resolved.ring
    if ring is None:
        return None
    a, b = resolved.leg(corner.from_leg_id), resolved.leg(corner.to_leg_id)
    first = _ring_flare(resolved, context, a, "left", corner.from_flare_radius_m, diagnostics, corner.corner_key)
    second = _ring_flare(resolved, context, b, "right", corner.to_flare_radius_m, diagnostics, corner.corner_key)
    if first is None or second is None:
        return None
    center = resolved.anchor_xy
    z_ring = ring.outer_edge_z
    start = _edge_xyz(context, a.road_ref, first[1], _road_side(a, "left"))
    end = _edge_xyz(context, b.road_ref, second[1], _road_side(b, "right"))
    tangent_a = (first[3][0], first[3][1], z_ring)
    tangent_b = (second[3][0], second[3][1], z_ring)
    angle_a = math.atan2(tangent_a[1] - center[1], tangent_a[0] - center[0])
    angle_b = math.atan2(tangent_b[1] - center[1], tangent_b[0] - center[0])
    sweep = (angle_b - angle_a) % math.tau
    gap = (math.atan2(math.sin(b.bearing_rad - a.bearing_rad), math.cos(b.bearing_rad - a.bearing_rad))) % math.tau
    if sweep <= 1.0e-9 or sweep >= gap:
        diagnostics.append(
            KernelDiagnostic("roundabout_flares_overlap", "error", corner.corner_key, None,
                             "the two flares meet the ring past each other; reduce their radii", "blocked")
        )
        return None
    points: list[tuple[float, float, float]] = []
    tags: list[tuple[str, tuple[float, float]]] = []
    if first[2] is not None:
        for point in _arc(first[2], start, tangent_a):
            points.append(point)
            tags.append(("arc", first[2]))
    else:
        points.append(start)
        tags.append(("ring", center))
    count = max(2, int(math.ceil(math.degrees(sweep) / ARC_MAX_STEP_DEG - 1.0e-9)))
    radius = ring.outer_edge_radius_m
    for k in range(1, count):
        angle = angle_a + sweep * k / count
        points.append((center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle), z_ring))
        tags.append(("ring", center))
    if second[2] is not None:
        for point in _arc(second[2], tangent_b, end):
            points.append(point)
            tags.append(("arc", second[2]))
    else:
        points.append(end)
        tags.append(("ring", center))
    # one point per position: the flare arcs repeat their ring tangent points
    merged_points, merged_tags = [], []
    for point, tag in zip(points, tags):
        if merged_points and _same_xy(merged_points[-1], point):
            continue
        merged_points.append(point)
        merged_tags.append(tag)
    return _Fillet(center, first[0], second[0], tuple(merged_points), tuple(merged_tags), first[3], second[3])


def _same_xy(a, b) -> bool:
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= STATION_TOLERANCE_M


def _signed_area(points) -> float:
    area = 0.0
    for index, point in enumerate(points):
        nxt = points[(index + 1) % len(points)]
        area += point[0] * nxt[1] - nxt[0] * point[1]
    return area * 0.5


def _first_self_crossing(points) -> tuple[int, int] | None:
    count = len(points)
    for i in range(count):
        p0, p1 = points[i], points[(i + 1) % count]
        for j in range(i + 2, count):
            if i == 0 and j == count - 1:
                continue
            q0, q1 = points[j], points[(j + 1) % count]
            hit = segment_intersection(p0, p1, q0, q1)
            if hit is None:
                continue
            t, u = hit
            # touching at a shared vertex of neighbouring edges is not a crossing
            if (t <= 1.0e-9 or t >= 1.0 - 1.0e-9) and (u <= 1.0e-9 or u >= 1.0 - 1.0e-9):
                continue
            return i, j
    return None


# public names for the later kernel stages
leg_distances = _leg_distances
station_on_leg = _station
road_side_of_leg = _road_side
