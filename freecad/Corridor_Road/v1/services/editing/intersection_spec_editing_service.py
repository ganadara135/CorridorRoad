"""Editing the parametric intersection spec from a form (plan phase R7b).

Widget-free: the Intersection panel fills an `IntersectionSpecForm` from its widgets and back, and
this module turns the form into a spec, says what is wrong with it, and words the kernel's check of
it. A value of 0 in a radius or width field means "not set": the kernel then uses its own default
and says so in the check (origin `constant`).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from ...models.source.intersection_spec import (
    INTERSECTION_SPEC_KINDS,
    AnchorSpec,
    IntersectionSpec,
    LegOverride,
    RoundaboutSpec,
)


SPEC_GRADING_MODES = ("", "blend_primary_side", "keep_primary_crown", "use_normal_superelevation", "flatten_intersection")
SPEC_ANCHOR_METHODS = ("detected", "manual")
SPEC_CIRCULATIONS = ("ccw", "cw")


@dataclass
class LegFormRow:
    road_ref: str
    side: str
    enabled: bool = True
    entry_radius_m: float = 0.0
    exit_radius_m: float = 0.0


@dataclass
class IntersectionSpecForm:
    intersection_id: str = ""
    kind: str = "t"
    primary_road: str = ""
    secondary_road: str = ""
    anchor_method: str = "detected"
    primary_station: float = 0.0
    secondary_station: float = 0.0
    corner_radius_m: float = 0.0
    grading_mode: str = ""
    inscribed_radius_m: float = 0.0
    circulatory_width_m: float = 0.0
    apron_width_m: float = 0.0
    entry_radius_m: float = 0.0
    exit_radius_m: float = 0.0
    circulation: str = "ccw"
    leg_rows: list[LegFormRow] = field(default_factory=list)


def form_from_spec(spec: IntersectionSpec) -> IntersectionSpecForm:
    roads = list(spec.road_refs) + ["", ""]
    stations = dict(spec.anchor.station_by_road)
    ring = spec.roundabout
    return IntersectionSpecForm(
        intersection_id=spec.intersection_id,
        kind=spec.kind,
        primary_road=roads[0],
        secondary_road=roads[1],
        anchor_method=spec.anchor.method,
        primary_station=float(stations.get(roads[0], 0.0)),
        secondary_station=float(stations.get(roads[1], 0.0)),
        corner_radius_m=float(spec.corner_radius_m or 0.0),
        grading_mode=spec.grading_mode or "",
        inscribed_radius_m=float(ring.inscribed_radius_m) if ring else 0.0,
        circulatory_width_m=float(ring.circulatory_width_m) if ring else 0.0,
        apron_width_m=float(ring.apron_width_m) if ring else 0.0,
        entry_radius_m=float(ring.entry_radius_m or 0.0) if ring else 0.0,
        exit_radius_m=float(ring.exit_radius_m or 0.0) if ring else 0.0,
        circulation=ring.circulation if ring else "ccw",
        leg_rows=[
            LegFormRow(row.road_ref, row.side, bool(row.enabled), float(row.entry_radius_m or 0.0), float(row.exit_radius_m or 0.0))
            for row in spec.leg_overrides
        ],
    )


def spec_from_form(form: IntersectionSpecForm, *, base: IntersectionSpec | None = None) -> tuple[IntersectionSpec | None, list[str]]:
    """The spec the form describes, or None and what is wrong with the form.

    `base` is the spec the form was loaded from: what the form does not show (corner overrides,
    the anchor search hint) is kept from it.
    """

    errors: list[str] = []
    kind = str(form.kind or "")
    if kind not in INTERSECTION_SPEC_KINDS:
        errors.append(f"Kind must be one of {', '.join(INTERSECTION_SPEC_KINDS)}.")
    primary, secondary = str(form.primary_road or ""), str(form.secondary_road or "")
    if not primary or not secondary:
        errors.append("Choose the primary and the secondary road.")
    elif primary == secondary:
        errors.append("The primary and the secondary road must be different Alignments.")
    if form.anchor_method not in SPEC_ANCHOR_METHODS:
        errors.append(f"Anchor must be one of {', '.join(SPEC_ANCHOR_METHODS)}.")
    if form.grading_mode not in SPEC_GRADING_MODES:
        errors.append(f"Unknown grading mode {form.grading_mode!r}.")
    for name in ("corner_radius_m", "inscribed_radius_m", "circulatory_width_m", "apron_width_m", "entry_radius_m", "exit_radius_m"):
        if float(getattr(form, name)) < 0.0:
            errors.append(f"{name} cannot be negative.")
    ring = None
    if kind == "roundabout":
        if form.inscribed_radius_m <= 0.0 or form.circulatory_width_m <= 0.0:
            errors.append("A roundabout needs a positive inscribed radius and circulatory width.")
        elif form.circulatory_width_m >= form.inscribed_radius_m:
            errors.append("The circulatory width must be less than the inscribed radius, or there is no central island.")
        if form.circulation not in SPEC_CIRCULATIONS:
            errors.append("Circulation must be ccw or cw.")
        ring = RoundaboutSpec(
            float(form.inscribed_radius_m),
            float(form.circulatory_width_m),
            float(form.apron_width_m),
            float(form.entry_radius_m) or None,
            float(form.exit_radius_m) or None,
            form.circulation,
        )
    for row in form.leg_rows:
        if row.side not in ("ahead", "back"):
            errors.append(f"Leg side must be ahead or back, not {row.side!r}.")
        if row.entry_radius_m < 0.0 or row.exit_radius_m < 0.0:
            errors.append(f"Leg {row.road_ref}:{row.side} has a negative radius.")
    if errors:
        return None, errors
    stations = ()
    if form.anchor_method == "manual":
        stations = ((primary, float(form.primary_station)), (secondary, float(form.secondary_station)))
    anchor = AnchorSpec(form.anchor_method, stations, base.anchor.search_hint_xy if base is not None else None)
    overrides = tuple(
        LegOverride(row.road_ref, row.side, bool(row.enabled), float(row.entry_radius_m) or None, float(row.exit_radius_m) or None)
        for row in form.leg_rows
        # a row that changes nothing is not stored: the leg is derived anyway
        if not row.enabled or row.entry_radius_m > 0.0 or row.exit_radius_m > 0.0
    )
    spec = IntersectionSpec(
        intersection_id=str(form.intersection_id or (base.intersection_id if base is not None else "")) or "intersection:main",
        kind=kind,
        road_refs=(primary, secondary),
        anchor=anchor,
        corner_radius_m=float(form.corner_radius_m) or None,
        grading_mode=form.grading_mode or None,
        leg_overrides=overrides,
        roundabout=ring,
    )
    if base is not None:
        spec = replace(spec, corner_overrides=base.corner_overrides)
    return spec, []


def leg_rows_for_result(result, form: IntersectionSpecForm) -> list[LegFormRow]:
    """One editable row per leg the kernel derived, carrying the form's override where it has one."""

    known = {(row.road_ref, row.side): row for row in form.leg_rows}
    rows = []
    for leg in list(getattr(result, "legs", ()) or ()):
        current = known.get((leg.road_ref, leg.side))
        rows.append(current or LegFormRow(leg.road_ref, leg.side, bool(leg.enabled)))
    return rows


def spec_check_lines(result) -> list[str]:
    """The kernel's verdict on a spec, for the panel: status, legs, corners, every value with
    where it came from, and the diagnostics."""

    if result is None:
        return ["No intersection to check."]
    lines = [f"Kernel status: {result.status}"]
    for leg in result.legs:
        mouth = "-" if leg.mouth_station is None else f"{leg.mouth_station:.3f}"
        lines.append(f"  leg {leg.leg_id}: {'open' if leg.enabled else 'closed'}, mouth station {mouth}")
    for corner in result.corners:
        lines.append(f"  corner {corner.corner_key}: {corner.treatment}" + (f", R {corner.radius_m:.3f} m" if corner.radius_m else ""))
    for value in result.resolved_values:
        shown = f"{value.value:.3f}" if isinstance(value.value, float) else str(value.value)
        lines.append(f"  {value.name} [{value.subject}] = {shown} ({value.origin})")
    for name, value in result.quality_rows:
        lines.append(f"  {name} = {value:.4g}")
    if result.diagnostics:
        lines.append("Diagnostics:")
        lines.extend(f"  {row.severity} {row.code} [{row.subject}]: {row.inspect}" for row in result.diagnostics)
    return lines
