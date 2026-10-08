"""Intersection geometry result produced by the parametric intersection kernel.

One result per intersection replaces the chain of topology, edge network, zone, loop and patch
boundary results (`V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md` section 5.7). It is rebuilt from
its inputs; `input_fingerprint` tells a consumer whether it is stale. Lengths are metres in
Project local coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KernelDiagnostic:
    """A typed kernel diagnostic: what failed, where, what to inspect, and the effect."""

    code: str
    severity: str
    subject: str = ""
    station: float | None = None
    inspect: str = ""
    effect: str = "none"

    def as_text(self) -> str:
        station = "" if self.station is None else f"{self.station:.3f}"
        return f"{self.severity}:{self.code}|{self.subject}|{station}|{self.effect}|{self.inspect}"


@dataclass(frozen=True)
class ResolvedValue:
    """One value the kernel used, with where it came from: spec, override, constant or derived:<rule>."""

    name: str
    subject: str
    value: object
    origin: str


@dataclass(frozen=True)
class LegGeometry:
    """One leg: a road on one side of the anchor, and where the intersection hands it back."""

    leg_id: str
    road_ref: str
    side: str
    bearing_rad: float
    enabled: bool
    mouth_station: float | None = None
    mouth_left_xyz: tuple[float, float, float] | None = None
    mouth_right_xyz: tuple[float, float, float] | None = None


@dataclass(frozen=True)
class CornerGeometry:
    """The corner between a leg and its counter-clockwise successor."""

    corner_key: str
    from_leg_id: str
    to_leg_id: str
    treatment: str
    radius_m: float = 0.0
    center_xy: tuple[float, float] | None = None
    from_tangent_station: float | None = None
    to_tangent_station: float | None = None
    arc_xyz: tuple[tuple[float, float, float], ...] = ()


@dataclass(frozen=True)
class IntersectionGeometryResult:
    """The evaluated plan geometry of one intersection."""

    schema_version: int
    intersection_id: str
    kind: str
    input_fingerprint: str
    status: str
    anchor_xy: tuple[float, float] = (0.0, 0.0)
    anchor_station_by_road: tuple[tuple[str, float], ...] = ()
    legs: tuple[LegGeometry, ...] = ()
    corners: tuple[CornerGeometry, ...] = ()
    # closed counter-clockwise polygon; the first point is not repeated at the end
    boundary_xyz: tuple[tuple[float, float, float], ...] = ()
    boundary_area_m2: float = 0.0
    # (road ref, station start, station end) the intersection owns on that road
    clip_spans: tuple[tuple[str, float, float], ...] = ()
    supplemental_stations: tuple[tuple[str, float], ...] = ()
    resolved_values: tuple[ResolvedValue, ...] = ()
    diagnostics: tuple[KernelDiagnostic, ...] = ()
    # K5: the patch TIN inside the boundary (counter-clockwise index triples)
    patch_vertices_xyz: tuple[tuple[float, float, float], ...] = ()
    patch_triangles: tuple[tuple[int, int, int], ...] = ()
    # K6: the side slope strips from the boundary to daylight
    slope_vertices_xyz: tuple[tuple[float, float, float], ...] = ()
    slope_triangles: tuple[tuple[int, int, int], ...] = ()
    # (role, subject, points): crown lines, the boundary, the slope toe lines
    breaklines: tuple[tuple[str, str, tuple[tuple[float, float, float], ...]], ...] = ()
    # (name, value): triangle counts and qualities of the patch and the slope
    quality_rows: tuple[tuple[str, float], ...] = ()
