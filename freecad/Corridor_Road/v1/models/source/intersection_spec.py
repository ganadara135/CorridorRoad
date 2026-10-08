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


def intersection_spec_to_dict(spec: IntersectionSpec) -> dict[str, object]:
    """Plain JSON-ready data of a spec (schema version 1)."""

    return {
        "schema_version": spec.schema_version,
        "intersection_id": spec.intersection_id,
        "kind": spec.kind,
        "road_refs": list(spec.road_refs),
        "anchor": {
            "method": spec.anchor.method,
            "station_by_road": [[ref, float(station)] for ref, station in spec.anchor.station_by_road],
            "search_hint_xy": list(spec.anchor.search_hint_xy) if spec.anchor.search_hint_xy is not None else None,
        },
        "corner_radius_m": spec.corner_radius_m,
        "grading_mode": spec.grading_mode,
        "leg_overrides": [
            {"road_ref": row.road_ref, "side": row.side, "enabled": bool(row.enabled), "entry_radius_m": row.entry_radius_m, "exit_radius_m": row.exit_radius_m}
            for row in spec.leg_overrides
        ],
        "corner_overrides": [
            {"corner_key": row.corner_key, "radius_m": row.radius_m, "treatment": row.treatment}
            for row in spec.corner_overrides
        ],
        "roundabout": None if spec.roundabout is None else {
            "inscribed_radius_m": spec.roundabout.inscribed_radius_m,
            "circulatory_width_m": spec.roundabout.circulatory_width_m,
            "apron_width_m": spec.roundabout.apron_width_m,
            "entry_radius_m": spec.roundabout.entry_radius_m,
            "exit_radius_m": spec.roundabout.exit_radius_m,
            "circulation": spec.roundabout.circulation,
        },
    }


def intersection_spec_from_dict(data: dict) -> IntersectionSpec:
    """The spec of `intersection_spec_to_dict`; missing optional entries take their defaults."""

    anchor = dict(data.get("anchor") or {})
    hint = anchor.get("search_hint_xy")
    ring = data.get("roundabout")
    return IntersectionSpec(
        intersection_id=str(data.get("intersection_id", "") or ""),
        kind=str(data.get("kind", "") or ""),
        road_refs=tuple(str(ref) for ref in list(data.get("road_refs") or [])),
        anchor=AnchorSpec(
            method=str(anchor.get("method", "detected") or "detected"),
            station_by_road=tuple((str(ref), float(station)) for ref, station in list(anchor.get("station_by_road") or [])),
            search_hint_xy=(float(hint[0]), float(hint[1])) if hint else None,
        ),
        corner_radius_m=_optional_float(data.get("corner_radius_m")),
        grading_mode=str(data["grading_mode"]) if data.get("grading_mode") else None,
        leg_overrides=tuple(
            LegOverride(
                str(row.get("road_ref", "")),
                str(row.get("side", "")),
                bool(row.get("enabled", True)),
                _optional_float(row.get("entry_radius_m")),
                _optional_float(row.get("exit_radius_m")),
            )
            for row in list(data.get("leg_overrides") or [])
        ),
        corner_overrides=tuple(
            CornerOverride(str(row.get("corner_key", "")), _optional_float(row.get("radius_m")), row.get("treatment") or None)
            for row in list(data.get("corner_overrides") or [])
        ),
        roundabout=None if not ring else RoundaboutSpec(
            float(ring.get("inscribed_radius_m", 0.0) or 0.0),
            float(ring.get("circulatory_width_m", 0.0) or 0.0),
            float(ring.get("apron_width_m", 0.0) or 0.0),
            _optional_float(ring.get("entry_radius_m")),
            _optional_float(ring.get("exit_radius_m")),
            str(ring.get("circulation", "ccw") or "ccw"),
        ),
        schema_version=int(data.get("schema_version", 1) or 1),
    )


def _optional_float(value) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
