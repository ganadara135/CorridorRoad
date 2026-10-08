"""Stage K4: the heights inside an intersection.

The boundary is not graded: every boundary vertex already has the finished grade of the corridor
surface it meets (stage K3). Only the inside is shaped, by one crown breakline per leg, from the
leg's mouth (the road's own crown there) to the anchor:

| grading mode | primary road crown | other crowns | anchor height |
| --- | --- | --- | --- |
| `blend_primary_side`, `keep_primary_crown`, `use_normal_superelevation` | its own profile | straight from the mouth crown to the anchor | primary profile at the anchor |
| `flatten_intersection` | straight from the mouth crown to the anchor | straight | mean of the mouth crowns |

The current pipeline's flatten and plane modes moved the boundary heights themselves, which tore
the patch away from the corridor at the mouths; here the modes only differ inside.
"""

from __future__ import annotations

import math

from dataclasses import dataclass

from ....models.result.intersection_geometry import KernelDiagnostic
from .planar import PlanarGeometry, leg_distances, station_on_leg
from .resolve import ResolvedIntersection
from .constants import ARC_MAX_STEP_DEG, EDGE_SAMPLE_STEP_M
from .road_context import RoadContext


PRIMARY_CROWN_MODES = {"blend_primary_side", "keep_primary_crown", "use_normal_superelevation"}
FLAT_MODES = {"flatten_intersection"}


@dataclass(frozen=True)
class CrownLine:
    leg_id: str
    road_ref: str
    # from the mouth to the anchor (to the ring's outer edge in a roundabout)
    points_xyz: tuple[tuple[float, float, float], ...]
    role: str = "crown"


def crown_lines(resolved: ResolvedIntersection, context: RoadContext, planar: PlanarGeometry, diagnostics: list[KernelDiagnostic]) -> list[CrownLine]:
    if resolved.ring is not None:
        return _roundabout_lines(resolved, context, planar)
    mode = resolved.grading_mode
    if mode not in PRIMARY_CROWN_MODES | FLAT_MODES:
        diagnostics.append(
            KernelDiagnostic(
                "grading_mode_unknown", "warning", resolved.spec.intersection_id, None,
                f"grading mode {mode!r} is not one of {sorted(PRIMARY_CROWN_MODES | FLAT_MODES)}; blend_primary_side is used", "fallback",
            )
        )
        mode = "blend_primary_side"
    primary = resolved.spec.road_refs[0]
    legs = [leg for leg in resolved.enabled_legs() if leg.leg_id in planar.mouth_distance]
    mouth_crown = {
        leg.leg_id: _crown_z(context, leg.road_ref, station_on_leg(resolved, leg, planar.mouth_distance[leg.leg_id]))
        for leg in legs
    }
    if mode in FLAT_MODES:
        anchor_z = sum(mouth_crown.values()) / max(len(mouth_crown), 1)
    else:
        anchor_z = _crown_z(context, primary, resolved.anchor_station_by_road[primary])
    lines: list[CrownLine] = []
    for leg in legs:
        mouth = planar.mouth_distance[leg.leg_id]
        points = []
        for distance in reversed(leg_distances(resolved, context, leg, 0.0, mouth)):
            station = station_on_leg(resolved, leg, distance)
            x, y = context.point_xy(leg.road_ref, station)
            if leg.road_ref == primary and mode in PRIMARY_CROWN_MODES:
                z = _crown_z(context, leg.road_ref, station)
            else:
                ratio = distance / mouth if mouth > 0.0 else 0.0
                z = anchor_z + (mouth_crown[leg.leg_id] - anchor_z) * ratio
            points.append((x, y, z))
        lines.append(CrownLine(leg.leg_id, leg.road_ref, tuple(points)))
    return lines


def _roundabout_lines(resolved: ResolvedIntersection, context: RoadContext, planar: PlanarGeometry) -> list[CrownLine]:
    """A roundabout is graded by its ring, whatever the grading mode: the circulatory roadway falls
    from the central island's edge (the primary profile at the anchor) to the ring's outer edge at
    `ROUNDABOUT_RING_CROSSFALL`. Each approach crown runs straight from its mouth to where the road
    crosses the ring's outer edge, and the outer edge itself is a breakline across each approach's
    throat, so the ring keeps its crossfall all the way round."""

    ring = resolved.ring
    center = resolved.anchor_xy
    radius = ring.outer_edge_radius_m
    lines: list[CrownLine] = []
    crown_end_by_leg: dict[str, tuple[float, float, float]] = {}
    for leg in resolved.enabled_legs():
        if leg.leg_id not in planar.mouth_distance:
            continue
        mouth = planar.mouth_distance[leg.leg_id]
        distances = leg_distances(resolved, context, leg, 0.0, mouth)
        reach = _ring_crossing(resolved, context, leg, distances, center, radius)
        mouth_z = _crown_z(context, leg.road_ref, station_on_leg(resolved, leg, mouth))
        points = []
        # samples within half a step of the ring crossing would make a sliver against it
        kept = [d for d in distances if d > reach + EDGE_SAMPLE_STEP_M * 0.5 or d == mouth]
        for distance in reversed(kept + [reach]):
            station = station_on_leg(resolved, leg, distance)
            x, y = context.point_xy(leg.road_ref, station)
            if distance <= reach:
                # the crossing point on the ring's outer edge, exactly on its circle
                scale = radius / max(math.hypot(x - center[0], y - center[1]), 1.0e-12)
                x, y = center[0] + (x - center[0]) * scale, center[1] + (y - center[1]) * scale
            ratio = (distance - reach) / (mouth - reach) if mouth > reach else 0.0
            points.append((x, y, ring.outer_edge_z + (mouth_z - ring.outer_edge_z) * ratio))
        crown_end_by_leg[leg.leg_id] = points[-1]
        lines.append(CrownLine(leg.leg_id, leg.road_ref, tuple(points)))
    for leg in resolved.enabled_legs():
        incoming = next((c for c in resolved.corners if c.to_leg_id == leg.leg_id), None)
        outgoing = next((c for c in resolved.corners if c.from_leg_id == leg.leg_id), None)
        if incoming is None or outgoing is None or incoming.corner_key not in planar.ring_tangents or outgoing.corner_key not in planar.ring_tangents:
            continue
        start = planar.ring_tangents[incoming.corner_key][1]
        end = planar.ring_tangents[outgoing.corner_key][0]
        lines.append(CrownLine(leg.leg_id, leg.road_ref, _throat(center, radius, ring.outer_edge_z, start, end, crown_end_by_leg.get(leg.leg_id)), "ring_throat"))
    return lines


def _ring_crossing(resolved, context, leg, distances, center, radius) -> float:
    previous = None
    for distance in distances:
        x, y = context.point_xy(leg.road_ref, station_on_leg(resolved, leg, distance))
        reach = math.hypot(x - center[0], y - center[1])
        if reach >= radius:
            if previous is None:
                return distance
            d0, r0 = previous
            return d0 + (distance - d0) * (radius - r0) / (reach - r0) if reach > r0 else distance
        previous = (distance, reach)
    return distances[-1]


def _throat(center, radius, z, start, end, crown_end) -> tuple[tuple[float, float, float], ...]:
    """The ring's outer edge from one flare's tangent point counter-clockwise to the next, through
    the approach crown's end point, so the crown and the edge share that vertex. Each side of the
    crown end is sampled evenly, so no sliver is left beside it."""

    def angle_of(point) -> float:
        return math.atan2(point[1] - center[1], point[0] - center[0])

    def piece(first, last, sweep) -> list[tuple[float, float, float]]:
        count = max(1, int(math.ceil(math.degrees(sweep) / ARC_MAX_STEP_DEG - 1.0e-9)))
        a0 = angle_of(first)
        return [(center[0] + radius * math.cos(a0 + sweep * k / count), center[1] + radius * math.sin(a0 + sweep * k / count), z) for k in range(1, count)]

    start_xyz, end_xyz = (start[0], start[1], z), (end[0], end[1], z)
    total = (angle_of(end) - angle_of(start)) % math.tau
    if crown_end is None:
        return (start_xyz, *piece(start, end, total), end_xyz)
    to_crown = (angle_of(crown_end) - angle_of(start)) % math.tau
    return (start_xyz, *piece(start, crown_end, to_crown), crown_end, *piece(crown_end, end, total - to_crown), end_xyz)


def _crown_z(context: RoadContext, road_ref: str, station: float) -> float:
    profile = context.surface_profile(road_ref, station)
    if profile is not None:
        value = profile.center_z()
        if value is not None:
            return float(value)
    value = context.finished_grade_z(road_ref, station)
    return float(value) if value is not None else 0.0
