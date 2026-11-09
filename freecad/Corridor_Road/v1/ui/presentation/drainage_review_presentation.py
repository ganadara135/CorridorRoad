"""Drainage Review rows from the Drainage output contract.

Turns a `DrainageOutput` into what the Drainage Review panel shows: one line per Ditch Run, the
flowline profile of a run with its points and flagged stretches, and the checks table. Pure: no
FreeCAD, no Qt, no engineering rule; the checks are the evaluation's.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models.output.drainage_output import DrainageOutput

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
# Checks that flag a stretch of the flowline; the profile draws them over the line.
STRETCH_CHECK_KINDS = frozenset({"flat_grade", "inlet_spacing"})


@dataclass(frozen=True)
class ProfileMarker:
    station: float
    z: float
    kind: str
    label: str
    selected: bool = False


@dataclass(frozen=True)
class ProfileLink:
    """A link drawn between two points of the run; a diameter above 0 makes it a pipe."""

    link_id: str
    from_station: float
    from_z: float
    to_station: float
    to_z: float
    pipe_diameter_m: float = 0.0
    selected: bool = False


@dataclass(frozen=True)
class FlowlineProfile:
    ditch_run_ref: str
    points: tuple[tuple[float, float], ...] = ()
    markers: tuple[ProfileMarker, ...] = ()
    low_points: tuple[tuple[float, float], ...] = ()
    high_points: tuple[tuple[float, float], ...] = ()
    # (station_start, station_end, severity) of the stretches a check flags
    flagged: tuple[tuple[float, float, str], ...] = ()
    links: tuple[ProfileLink, ...] = ()
    lines: list[str] = field(default_factory=list)


def drainage_review_run_rows(output: DrainageOutput) -> list[dict[str, object]]:
    """One row per Ditch Run with a flowline: its span, length, grades and check counts."""

    rows = []
    for flowline in output.flowline_rows:
        checks = [row for row in output.check_rows if row.ditch_run_ref == flowline.ditch_run_ref]
        rows.append(
            {
                "ditch_run_ref": flowline.ditch_run_ref,
                "label": (
                    f"{flowline.ditch_run_ref} ({flowline.side}) STA {flowline.station_start:.3f}-{flowline.station_end:.3f}, "
                    f"{flowline.length_m:.1f} m, grade {flowline.min_grade_percent:.2f} to {flowline.max_grade_percent:.2f} %"
                ),
                "errors": sum(1 for row in checks if row.severity == "error"),
                "warnings": sum(1 for row in checks if row.severity == "warning"),
            }
        )
    return rows


def drainage_flowline_profile(output: DrainageOutput, ditch_run_ref: str) -> FlowlineProfile | None:
    flowline = next((row for row in output.flowline_rows if row.ditch_run_ref == ditch_run_ref), None)
    if flowline is None:
        return None
    profile = list(flowline.profile)
    markers = tuple(
        ProfileMarker(point.station, point.z, point.kind, point.point_ref)
        for point in output.point_rows
        if point.z is not None and (point.ditch_run_ref == ditch_run_ref or (point.kind == "culvert" and not point.ditch_run_ref))
        and flowline.station_start <= point.station <= flowline.station_end
    )
    flagged = tuple(
        (row.station_start, row.station_end, row.severity)
        for row in output.check_rows
        if row.ditch_run_ref == ditch_run_ref and row.kind in STRETCH_CHECK_KINDS
    )
    return FlowlineProfile(
        ditch_run_ref=ditch_run_ref,
        points=tuple(profile),
        markers=markers,
        low_points=tuple((station, _z_at(profile, station)) for station in flowline.low_point_stations),
        high_points=tuple((station, _z_at(profile, station)) for station in flowline.high_point_stations),
        flagged=flagged,
    )


def drainage_editing_run_refs(flowlines) -> list[str]:
    """The Ditch Runs the stored result has a flowline for, in the result's order."""

    return [str(row.ditch_run_ref) for row in flowlines or []]


def drainage_editing_profile(
    flowlines,
    points,
    links,
    ditch_run_ref: str,
    *,
    selected_link_id: str = "",
    selected_point_id: str = "",
) -> FlowlineProfile | None:
    """One run's flowline with the points and links as the editor's tables hold them now.

    The flowline is the stored result's; the points and links are the unapplied edits, so the
    drawing follows the tables. A point sits on the flowline at its station. A link is drawn only
    when both its points are on this run.
    """

    flowline = next((row for row in flowlines or [] if row.ditch_run_ref == ditch_run_ref), None)
    if flowline is None or len(flowline.station_rows) < 2:
        return None
    profile = [(float(row.station), float(row.z)) for row in flowline.station_rows]
    first, last = profile[0][0], profile[-1][0]
    on_run = {
        point.point_id: point
        for point in points or []
        if first - 1.0e-6 <= point.station <= last + 1.0e-6
        and (point.ditch_run_ref == ditch_run_ref or (point.kind == "culvert" and not point.ditch_run_ref))
    }
    markers = tuple(
        ProfileMarker(point.station, _z_at(profile, point.station), point.kind, point.point_id, point.point_id == selected_point_id)
        for point in on_run.values()
    )
    drawn = []
    for link in links or []:
        start, end = on_run.get(link.from_ref), on_run.get(link.to_ref)
        if start is None or end is None:
            continue
        drawn.append(
            ProfileLink(
                link.link_id,
                start.station,
                _z_at(profile, start.station),
                end.station,
                _z_at(profile, end.station),
                float(link.pipe_diameter_m),
                link.link_id == selected_link_id,
            )
        )
    return FlowlineProfile(
        ditch_run_ref=ditch_run_ref,
        points=tuple(profile),
        markers=markers,
        low_points=tuple((station, _z_at(profile, station)) for station in flowline.low_point_stations),
        high_points=tuple((station, _z_at(profile, station)) for station in flowline.high_point_stations),
        links=tuple(drawn),
    )


def drainage_run_of_link(points, links, link_id: str) -> str:
    """The Ditch Run a link is drawn on: its from-point's run, else its to-point's (a culvert has none)."""

    link = next((row for row in links or [] if row.link_id == link_id), None)
    if link is None:
        return ""
    by_id = {point.point_id: point for point in points or []}
    for ref in (link.from_ref, link.to_ref):
        point = by_id.get(ref)
        if point is not None and point.ditch_run_ref:
            return str(point.ditch_run_ref)
    return ""


def drainage_check_table_rows(output: DrainageOutput, ditch_run_ref: str = "") -> list[dict[str, object]]:
    """The checks, errors first then by station; with a run, its checks and the run-less ones."""

    rows = [
        row
        for row in output.check_rows
        if not ditch_run_ref or row.ditch_run_ref in {ditch_run_ref, ""}
    ]
    rows.sort(key=lambda row: (SEVERITY_ORDER.get(row.severity, 3), row.station_start, row.check_ref))
    return [
        {
            "check_ref": row.check_ref,
            "severity": row.severity,
            "kind": row.kind,
            "ditch_run_ref": row.ditch_run_ref,
            "stations": f"{row.station_start:.3f}" if abs(row.station_end - row.station_start) < 1.0e-9 else f"{row.station_start:.3f}-{row.station_end:.3f}",
            "message": row.message,
        }
        for row in rows
    ]


def drainage_pipe_table_rows(output: DrainageOutput) -> list[dict[str, object]]:
    """The pipes by link, each with its diameter, length, inverts, grade and barrel volume."""

    return [
        {
            "link_ref": row.link_ref,
            "route": f"{row.from_ref} -> {row.to_ref}",
            "diameter": f"{row.diameter_m:.2f}",
            "length": f"{row.length_m:.1f}",
            "inverts": f"{row.from_invert_z:.2f} -> {row.to_invert_z:.2f}",
            "grade": f"{row.grade_percent:.2f}",
            "volume": f"{row.volume_m3:.2f}",
        }
        for row in sorted(output.pipe_rows, key=lambda pipe: pipe.link_ref)
    ]


def drainage_review_summary(output: DrainageOutput | None) -> str:
    if output is None:
        return "No Drainage result. Add Ditch Runs in the Drainage panel, then Apply or run Rebuild Downstream."
    counts = {severity: sum(1 for row in output.check_rows if row.severity == severity) for severity in SEVERITY_ORDER}
    pipes = f", {len(output.pipe_rows)} pipe(s)" if output.pipe_rows else ""
    return (
        f"Drainage: {output.status}; {len(output.flowline_rows)} flowline(s), {len(output.point_rows)} point(s), "
        f"{len(output.link_rows)} link(s){pipes}; {counts['error']} error(s), {counts['warning']} warning(s). "
        f"Policy: minimum grade {output.min_grade_percent:.2f} %, inlet spacing {output.max_inlet_spacing_m:.1f} m."
    )


def _z_at(profile: list[tuple[float, float]], station: float) -> float:
    for (first_station, first_z), (second_station, second_z) in zip(profile, profile[1:]):
        if first_station <= station <= second_station:
            span = second_station - first_station
            ratio = 0.0 if span <= 0.0 else (station - first_station) / span
            return first_z + (second_z - first_z) * ratio
    return profile[-1][1] if profile else 0.0


__all__ = [
    "FlowlineProfile",
    "ProfileLink",
    "ProfileMarker",
    "drainage_editing_profile",
    "drainage_editing_run_refs",
    "drainage_run_of_link",
    "drainage_check_table_rows",
    "drainage_flowline_profile",
    "drainage_pipe_table_rows",
    "drainage_review_run_rows",
    "drainage_review_summary",
]
