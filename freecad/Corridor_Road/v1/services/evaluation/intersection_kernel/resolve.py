"""Resolve an `IntersectionSpec` against the evaluated roads (plan section 5.5).

Legs and corners are derived, never stored: a leg is a road on one side of the anchor, the legs
are ordered by bearing counter-clockwise, and a corner joins each leg to its successor. No role
name takes part. Each value the kernel uses records its origin.
"""

from __future__ import annotations

import math

from dataclasses import dataclass, field

from ....models.result.intersection_geometry import KernelDiagnostic, ResolvedValue
from ....models.source.intersection_spec import INTERSECTION_SPEC_KINDS, IntersectionSpec
from .constants import (
    ANCHOR_MEET_TOLERANCE_M,
    CROSS_CORNER_RADIUS_M,
    DEFAULT_GRADING_MODE,
    LEG_MIN_LENGTH_M,
    ROUNDABOUT_APRON_WIDTH_RATIO,
    ROUNDABOUT_CIRCULATORY_WIDTH_RATIO,
    ROUNDABOUT_ENTRY_RADIUS_RATIO,
    ROUNDABOUT_EXIT_RADIUS_RATIO,
    ROUNDABOUT_INSCRIBED_RADIUS_M,
    ROUNDABOUT_RING_CROSSFALL,
    T_CORNER_RADIUS_M,
)
from .road_context import RoadContext


@dataclass(frozen=True)
class ResolvedLeg:
    leg_id: str
    road_ref: str
    side: str
    bearing_rad: float
    length_m: float
    enabled: bool
    origin: str


@dataclass(frozen=True)
class ResolvedCorner:
    corner_key: str
    from_leg_id: str
    to_leg_id: str
    treatment: str
    radius_m: float
    treatment_origin: str
    radius_origin: str
    # treatment "ring" (roundabout): the from leg's flare and the to leg's flare onto the ring;
    # 0 is a square corner where the pavement edge meets the ring
    from_flare_radius_m: float = 0.0
    to_flare_radius_m: float = 0.0


@dataclass(frozen=True)
class ResolvedRing:
    """The circulatory roadway of a roundabout, about the anchor."""

    outer_edge_radius_m: float      # the paved outer edge: inscribed radius plus the outer apron
    island_radius_m: float          # the central island's edge
    island_z: float
    outer_edge_z: float
    circulation: str


@dataclass
class ResolvedIntersection:
    spec: IntersectionSpec
    anchor_xy: tuple[float, float] = (0.0, 0.0)
    anchor_station_by_road: dict[str, float] = field(default_factory=dict)
    legs: list[ResolvedLeg] = field(default_factory=list)
    corners: list[ResolvedCorner] = field(default_factory=list)
    grading_mode: str = DEFAULT_GRADING_MODE
    ring: ResolvedRing | None = None
    resolved_values: list[ResolvedValue] = field(default_factory=list)
    diagnostics: list[KernelDiagnostic] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(row.effect == "blocked" for row in self.diagnostics)

    def enabled_legs(self) -> list[ResolvedLeg]:
        return [leg for leg in self.legs if leg.enabled]

    def leg(self, leg_id: str) -> ResolvedLeg:
        return next(leg for leg in self.legs if leg.leg_id == leg_id)


def leg_id_for(road_ref: str, side: str) -> str:
    return f"{road_ref}:{side}"


def resolve_intersection(spec: IntersectionSpec, context: RoadContext) -> ResolvedIntersection:
    resolved = ResolvedIntersection(spec=spec)
    diagnostics = resolved.diagnostics
    kind = str(spec.kind or "")
    if kind not in INTERSECTION_SPEC_KINDS:
        diagnostics.append(_blocked("intersection_kind_unknown", spec.intersection_id, f"kind {kind!r}; use one of {', '.join(INTERSECTION_SPEC_KINDS)}"))
        return resolved
    roads = [str(ref) for ref in spec.road_refs if str(ref)]
    if len(roads) < 2:
        diagnostics.append(_blocked("intersection_roads_missing", spec.intersection_id, "an intersection needs two Alignments in road_refs"))
        return resolved
    missing = [ref for ref in roads if ref not in set(context.road_refs())]
    if missing:
        for ref in missing:
            diagnostics.append(_blocked("road_not_evaluated", ref, "the Alignment has no usable centreline geometry"))
        return resolved

    if not _resolve_anchor(resolved, roads, context):
        return resolved
    _resolve_legs(resolved, roads, context)
    if resolved.blocked:
        return resolved
    if kind == "roundabout":
        _resolve_ring(resolved, context)
    else:
        _resolve_corners(resolved)
    resolved.grading_mode = spec.grading_mode or DEFAULT_GRADING_MODE
    resolved.resolved_values.append(
        ResolvedValue("grading_mode", spec.intersection_id, resolved.grading_mode, "spec" if spec.grading_mode else "constant")
    )
    return resolved


def _resolve_anchor(resolved: ResolvedIntersection, roads: list[str], context: RoadContext) -> bool:
    spec = resolved.spec
    primary = roads[0]
    manual = {str(ref): float(station) for ref, station in spec.anchor.station_by_road}
    if spec.anchor.method == "manual":
        if primary not in manual:
            resolved.diagnostics.append(_blocked("anchor_manual_station_missing", primary, "a manual anchor needs the primary road's station"))
            return False
        resolved.anchor_xy = context.point_xy(primary, manual[primary])
        origin = "spec"
    else:
        crossings = context.crossings(primary, roads[1])
        if not crossings:
            resolved.diagnostics.append(
                _blocked("anchor_no_crossing", f"{primary}|{roads[1]}", "the two Alignments do not cross in plan; set a manual anchor")
            )
            return False
        hint = spec.anchor.search_hint_xy
        crossing = min(crossings, key=lambda row: math.hypot(row.x - hint[0], row.y - hint[1])) if hint else crossings[0]
        if len(crossings) > 1 and hint is None:
            resolved.diagnostics.append(
                KernelDiagnostic("anchor_multiple_crossings", "warning", f"{primary}|{roads[1]}", None, "the first crossing is used; set search_hint_xy", "fallback")
            )
        resolved.anchor_xy = (crossing.x, crossing.y)
        manual = {primary: crossing.station_a, roads[1]: crossing.station_b, **{k: v for k, v in manual.items() if k not in {primary, roads[1]}}}
        origin = "derived:crossing"
    for ref in roads:
        if ref in manual:
            station = manual[ref]
        else:
            # a further road meets at its crossing with the primary road nearest to the anchor
            rows = context.crossings(primary, ref)
            if not rows:
                resolved.diagnostics.append(_blocked("anchor_no_crossing", f"{primary}|{ref}", "the road does not cross the primary road"))
                return False
            station = min(rows, key=lambda row: math.hypot(row.x - resolved.anchor_xy[0], row.y - resolved.anchor_xy[1])).station_b
        point = context.point_xy(ref, station)
        gap = math.hypot(point[0] - resolved.anchor_xy[0], point[1] - resolved.anchor_xy[1])
        if gap > ANCHOR_MEET_TOLERANCE_M:
            resolved.diagnostics.append(
                _blocked("anchor_roads_do_not_meet", ref, f"the road is {gap:.3f} m from the anchor at station {station:.3f}", station)
            )
            return False
        resolved.anchor_station_by_road[ref] = station
        resolved.resolved_values.append(ResolvedValue("anchor_station", ref, station, origin))
    return True


def _resolve_legs(resolved: ResolvedIntersection, roads: list[str], context: RoadContext) -> None:
    spec = resolved.spec
    legs: list[ResolvedLeg] = []
    for ref in roads:
        station = resolved.anchor_station_by_road[ref]
        low, high = context.station_range(ref)
        tangent = context.tangent_xy(ref, station)
        for side, length, sign in (("ahead", high - station, 1.0), ("back", station - low, -1.0)):
            if length <= LEG_MIN_LENGTH_M:
                continue
            bearing = math.atan2(sign * tangent[1], sign * tangent[0]) % math.tau
            legs.append(ResolvedLeg(leg_id_for(ref, side), ref, side, bearing, length, True, "derived:road_extent"))

    # D3: a T whose side road crosses the primary road closes the side road's shorter side
    if spec.kind == "t" and len(roads) >= 2:
        side_legs = [leg for leg in legs if leg.road_ref == roads[1]]
        if len(side_legs) == 2:
            shorter = min(side_legs, key=lambda leg: leg.length_m)
            legs = [_with_enabled(leg, False, "derived:t_rule") if leg is shorter else leg for leg in legs]

    overrides = {(row.road_ref, row.side): row for row in spec.leg_overrides}
    for key, override in overrides.items():
        index = next((i for i, leg in enumerate(legs) if (leg.road_ref, leg.side) == key), None)
        if index is None:
            resolved.diagnostics.append(
                KernelDiagnostic("leg_override_unmatched", "warning", leg_id_for(*key), None, "no leg exists on that side of the anchor", "none")
            )
            continue
        legs[index] = _with_enabled(legs[index], bool(override.enabled), "override")

    legs.sort(key=lambda leg: leg.bearing_rad)
    resolved.legs = legs
    for leg in legs:
        resolved.resolved_values.append(ResolvedValue("leg_enabled", leg.leg_id, leg.enabled, leg.origin))
    enabled = resolved.enabled_legs()
    expected = {"t": 3, "cross": 4}.get(spec.kind)
    if len(enabled) < 2:
        resolved.diagnostics.append(_blocked("intersection_leg_count", spec.intersection_id, f"{len(enabled)} legs; an intersection needs at least 2"))
    elif expected is not None and len(enabled) != expected:
        resolved.diagnostics.append(
            KernelDiagnostic(
                "intersection_leg_count",
                "warning",
                spec.intersection_id,
                None,
                f"a {spec.kind} has {expected} legs, the roads give {len(enabled)}; check the anchor and the road extents",
                "partial",
            )
        )


def _resolve_corners(resolved: ResolvedIntersection) -> None:
    spec = resolved.spec
    enabled = resolved.enabled_legs()
    if len(enabled) < 2:
        return
    overrides = {row.corner_key: row for row in spec.corner_overrides}
    default_radius = CROSS_CORNER_RADIUS_M if spec.kind == "cross" else T_CORNER_RADIUS_M
    corners: list[ResolvedCorner] = []
    for index, leg in enumerate(enabled):
        successor = enabled[(index + 1) % len(enabled)]
        key = f"{leg.leg_id}|{successor.leg_id}"
        # two legs of the same road: its edge runs straight through, there is no corner to round
        treatment, treatment_origin = ("none", "derived:same_road") if leg.road_ref == successor.road_ref else ("fillet", "derived:two_roads")
        if spec.corner_radius_m:
            radius, radius_origin = float(spec.corner_radius_m), "spec"
        else:
            radius, radius_origin = default_radius, "constant"
        override = overrides.get(key)
        if override is not None:
            if override.treatment:
                treatment, treatment_origin = str(override.treatment), "override"
            if override.radius_m:
                radius, radius_origin = float(override.radius_m), "override"
        corners.append(ResolvedCorner(key, leg.leg_id, successor.leg_id, treatment, radius, treatment_origin, radius_origin))
        resolved.resolved_values.append(ResolvedValue("corner_treatment", key, treatment, treatment_origin))
        if treatment == "fillet":
            resolved.resolved_values.append(ResolvedValue("corner_radius_m", key, radius, radius_origin))
    for key in sorted(set(overrides) - {row.corner_key for row in corners}):
        resolved.diagnostics.append(
            KernelDiagnostic("corner_override_unmatched", "warning", key, None, "no such pair of neighbouring legs", "none")
        )
    resolved.corners = corners


def _resolve_ring(resolved: ResolvedIntersection, context: RoadContext) -> None:
    """A roundabout: the ring about the anchor, and between each pair of neighbouring approaches a
    corner that runs from the first approach's flare round the ring to the second's.

    Circulating counter-clockwise (right-hand traffic) a driver enters on the approach's left
    side, looking outward, and leaves on its right; clockwise swaps them.
    """

    spec = resolved.spec
    ring_spec = spec.roundabout
    subject = spec.intersection_id
    if ring_spec is not None and ring_spec.inscribed_radius_m > 0.0:
        inscribed, inscribed_origin = float(ring_spec.inscribed_radius_m), "spec"
    else:
        inscribed, inscribed_origin = ROUNDABOUT_INSCRIBED_RADIUS_M, "constant"
    if ring_spec is not None and ring_spec.circulatory_width_m > 0.0:
        width, width_origin = float(ring_spec.circulatory_width_m), "spec"
    else:
        width, width_origin = inscribed * ROUNDABOUT_CIRCULATORY_WIDTH_RATIO, "constant"
    if ring_spec is not None:
        apron, apron_origin = max(float(ring_spec.apron_width_m), 0.0), "spec"
    else:
        apron, apron_origin = width * ROUNDABOUT_APRON_WIDTH_RATIO, "constant"
    circulation = (ring_spec.circulation if ring_spec is not None else "ccw") or "ccw"
    island = inscribed - width
    if island <= 0.0:
        resolved.diagnostics.append(_blocked("roundabout_island_not_positive", subject, f"circulatory width {width:.3f} m fills the {inscribed:.3f} m ring"))
        return
    primary = spec.road_refs[0]
    island_z = context.finished_grade_z(primary, resolved.anchor_station_by_road[primary])
    island_z = float(island_z) if island_z is not None else 0.0
    outer = inscribed + apron
    resolved.ring = ResolvedRing(outer, island, island_z, island_z - ROUNDABOUT_RING_CROSSFALL * (outer - island), circulation)
    resolved.resolved_values += [
        ResolvedValue("roundabout_inscribed_radius_m", subject, inscribed, inscribed_origin),
        ResolvedValue("roundabout_circulatory_width_m", subject, width, width_origin),
        ResolvedValue("roundabout_apron_width_m", subject, apron, apron_origin),
        ResolvedValue("roundabout_circulation", subject, circulation, "spec" if ring_spec is not None else "constant"),
    ]

    overrides = {(row.road_ref, row.side): row for row in spec.leg_overrides}

    def flare(leg: ResolvedLeg, entry: bool) -> tuple[float, str]:
        override = overrides.get((leg.road_ref, leg.side))
        value = getattr(override, "entry_radius_m" if entry else "exit_radius_m", None) if override is not None else None
        if value is not None:
            return max(float(value), 0.0), "override"
        value = getattr(ring_spec, "entry_radius_m" if entry else "exit_radius_m", None) if ring_spec is not None else None
        if value is not None:
            return max(float(value), 0.0), "spec"
        return outer * (ROUNDABOUT_ENTRY_RADIUS_RATIO if entry else ROUNDABOUT_EXIT_RADIUS_RATIO), "constant"

    counter_clockwise = circulation != "cw"
    enabled = resolved.enabled_legs()
    for index, leg in enumerate(enabled):
        successor = enabled[(index + 1) % len(enabled)]
        key = f"{leg.leg_id}|{successor.leg_id}"
        # the from leg's left side and the to leg's right side face this corner
        from_radius, from_origin = flare(leg, counter_clockwise)
        to_radius, to_origin = flare(successor, not counter_clockwise)
        resolved.corners.append(ResolvedCorner(key, leg.leg_id, successor.leg_id, "ring", 0.0, "derived:roundabout", "-", from_radius, to_radius))
        resolved.resolved_values.append(ResolvedValue("corner_treatment", key, "ring", "derived:roundabout"))
        resolved.resolved_values.append(ResolvedValue("flare_radius_m", f"{key}:from", from_radius, from_origin))
        resolved.resolved_values.append(ResolvedValue("flare_radius_m", f"{key}:to", to_radius, to_origin))


def _with_enabled(leg: ResolvedLeg, enabled: bool, origin: str) -> ResolvedLeg:
    return ResolvedLeg(leg.leg_id, leg.road_ref, leg.side, leg.bearing_rad, leg.length_m, enabled, origin)


def _blocked(code: str, subject: str, inspect: str, station: float | None = None) -> KernelDiagnostic:
    return KernelDiagnostic(code, "error", subject, station, inspect, "blocked")
