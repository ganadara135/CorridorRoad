"""UI-independent construction of an intersection control Region row for an existing road.

A starter preset authors its own Region model, so its control Region is part of a
set it wrote itself. A real route already has a Region model that the user wrote,
and `Use Existing Alignments` needs an intersection-tagged Region on it without
editing what the user authored. The row built here is an overlay: it covers the
station span around the detected crossing, carries `intersection_ref`, and takes
a priority above every existing row, so `RegionResolutionService` makes it the
active row there and leaves every other row exactly as it was.

The overlay copies the Assembly, Template, Superelevation and policy-set refs of
the row that was active at the crossing, so the section a station resolves to
does not change except that it is now tagged as an intersection control area.

Nothing here reads or writes a FreeCAD document. A caller that can find the
Region model passes it in and persists the result as an explicit step.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ...models.source.region_model import RegionModel, RegionRow
from ..evaluation.region_resolution_service import RegionResolutionService

# Starter control Regions use 80 against 10 for the approach rows. An overlay must
# beat every row it covers, so it is the larger of this and the highest priority + 10.
CONTROL_REGION_BASE_PRIORITY = 80
_STATION_TOLERANCE = 1.0e-6


@dataclass(frozen=True)
class ControlRegionOverlay:
    """The Region model with one control Region row added, and what that row is."""

    model: RegionModel
    row: RegionRow
    base_region_id: str = ""


def build_control_region_overlay(
    region_model: RegionModel | None,
    *,
    station: float,
    control_length: float,
    intersection_ref: str,
    role: str,
    kind: str,
) -> ControlRegionOverlay:
    """Return `region_model` with an intersection-tagged overlay row centred on `station`.

    Raises `ValueError` naming what is wrong when no honest row can be built: no
    Region rows to inherit from, a station outside the span the Regions cover, or a
    control length that leaves no span. A row invented over stations no Region
    covers would claim an Assembly nobody chose.
    """

    rows = list(getattr(region_model, "region_rows", []) or [])
    if region_model is None or not rows:
        raise ValueError("The Alignment has no Region rows to place an intersection control Region on.")
    length = float(control_length or 0.0)
    if length <= _STATION_TOLERANCE:
        raise ValueError("Control length must be greater than zero.")
    span_start = min(float(row.station_start) for row in rows)
    span_end = max(float(row.station_end) for row in rows)
    center = float(station)
    if center < span_start - _STATION_TOLERANCE or center > span_end + _STATION_TOLERANCE:
        raise ValueError(
            "The detected crossing station %.3f is outside the Regions of %s (STA %.3f-%.3f)."
            % (center, str(getattr(region_model, "alignment_id", "") or "the Alignment"), span_start, span_end)
        )
    start = max(span_start, center - length / 2.0)
    end = min(span_end, center + length / 2.0)
    if end - start <= _STATION_TOLERANCE:
        raise ValueError("The control Region around STA %.3f would be empty." % center)

    resolution = RegionResolutionService().resolve_station(region_model, min(max(center, span_start), span_end))
    base = next((row for row in rows if row.region_id == resolution.active_region_id), None)
    taken = {str(row.region_id) for row in rows}
    region_id = _unique_region_id("region:intersection-%s-%s" % (_token(role), _token(kind)), taken)
    priority = max(CONTROL_REGION_BASE_PRIORITY, max(int(row.priority or 0) for row in rows) + 10)
    overlay = RegionRow(
        region_id=region_id,
        region_index=max(int(row.region_index or 0) for row in rows) + 1,
        station_start=start,
        station_end=end,
        assembly_ref=str(getattr(base, "assembly_ref", "") or ""),
        template_ref=str(getattr(base, "template_ref", "") or ""),
        superelevation_ref=str(getattr(base, "superelevation_ref", "") or ""),
        policy_set_ref=str(getattr(base, "policy_set_ref", "") or ""),
        intersection_ref=str(intersection_ref or ""),
        priority=priority,
        notes=(
            "Intersection control Region overlay created by Intersections; "
            "it inherits the refs of %s and leaves that row unchanged."
            % (str(getattr(base, "region_id", "") or "no covering row"))
        ),
    )
    return ControlRegionOverlay(
        model=replace(region_model, region_rows=[*rows, overlay]),
        row=overlay,
        base_region_id=str(getattr(base, "region_id", "") or ""),
    )


def _unique_region_id(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    index = 2
    while "%s-%02d" % (base, index) in taken:
        index += 1
    return "%s-%02d" % (base, index)


def _token(value: str) -> str:
    text = "".join(ch if ch.isalnum() else "-" for ch in str(value or "").strip().lower())
    return "-".join(part for part in text.split("-") if part) or "x"
