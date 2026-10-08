"""Parametric Intersection spec for CorridorRoad v1.

The spec holds only design intent: which roads meet, how the anchor is found, and the values a
user changed. Legs, corners, edges and widths are not stored; the intersection kernel derives
them from the evaluated roads (`V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md` section 5.2).
Every length is in metres, in Project local coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass, field


INTERSECTION_SPEC_KINDS = ("t", "cross", "roundabout")
LEG_SIDES = ("ahead", "back")
CORNER_TREATMENTS = ("fillet", "none")


@dataclass(frozen=True)
class AnchorSpec:
    """How the intersection point is found on the participating roads."""

    method: str = "detected"
    # manual: the station of each road at the intersection point
    station_by_road: tuple[tuple[str, float], ...] = ()
    # detected: when two roads cross more than once, the crossing nearest to this point
    search_hint_xy: tuple[float, float] | None = None


@dataclass(frozen=True)
class LegOverride:
    """Opens or closes one derived leg: a road on one side of the anchor."""

    road_ref: str
    side: str
    enabled: bool = True
    # roundabout only: this approach's entry and exit flare radii
    entry_radius_m: float | None = None
    exit_radius_m: float | None = None


@dataclass(frozen=True)
class CornerOverride:
    """Changes one derived corner, keyed `"<from leg id>|<to leg id>"` in counter-clockwise order."""

    corner_key: str
    radius_m: float | None = None
    treatment: str | None = None


@dataclass(frozen=True)
class RoundaboutSpec:
    """Ring parameters of a roundabout."""

    inscribed_radius_m: float
    circulatory_width_m: float
    apron_width_m: float = 0.0
    entry_radius_m: float | None = None
    exit_radius_m: float | None = None
    circulation: str = "ccw"


@dataclass(frozen=True)
class IntersectionSpec:
    """Durable parametric intent of one at-grade intersection."""

    intersection_id: str
    kind: str
    # Alignment ids; the first one is the primary road
    road_refs: tuple[str, ...]
    anchor: AnchorSpec = field(default_factory=AnchorSpec)
    corner_radius_m: float | None = None
    grading_mode: str | None = None
    leg_overrides: tuple[LegOverride, ...] = ()
    corner_overrides: tuple[CornerOverride, ...] = ()
    roundabout: RoundaboutSpec | None = None
    schema_version: int = 1
