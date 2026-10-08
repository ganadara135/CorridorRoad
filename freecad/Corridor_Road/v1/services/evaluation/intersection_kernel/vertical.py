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

from dataclasses import dataclass

from ....models.result.intersection_geometry import KernelDiagnostic
from .planar import PlanarGeometry, leg_distances, station_on_leg
from .resolve import ResolvedIntersection
from .road_context import RoadContext


PRIMARY_CROWN_MODES = {"blend_primary_side", "keep_primary_crown", "use_normal_superelevation"}
FLAT_MODES = {"flatten_intersection"}


@dataclass(frozen=True)
class CrownLine:
    leg_id: str
    road_ref: str
    # from the mouth to the anchor
    points_xyz: tuple[tuple[float, float, float], ...]


def crown_lines(resolved: ResolvedIntersection, context: RoadContext, planar: PlanarGeometry, diagnostics: list[KernelDiagnostic]) -> list[CrownLine]:
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


def _crown_z(context: RoadContext, road_ref: str, station: float) -> float:
    profile = context.surface_profile(road_ref, station)
    if profile is not None:
        value = profile.center_z()
        if value is not None:
            return float(value)
    value = context.finished_grade_z(road_ref, station)
    return float(value) if value is not None else 0.0
