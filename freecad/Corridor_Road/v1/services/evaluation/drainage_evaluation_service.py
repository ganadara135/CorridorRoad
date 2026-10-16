"""Drainage evaluation: the flowline of each Ditch Run, checked against the Drainage Policy.

The flowline of a run is its ditch's `ditch_flowline` point (the lowest point of the ditch) at
every Applied Section the run covers; Applied Sections tag those points with the run id. From the
flowline come the grades, the low and high points and the flow direction. The run's inlets and
outfalls, and the culverts crossing its road, collect its water: a low point must have one near it
when the Policy requires it, and no stretch of ditch may run longer than the Policy's inlet
spacing without one. Where they are missing the evaluation suggests points; it never adds them.
Nothing here reads FreeCAD.

Units: stations, lengths and elevations in meters, grades in percent.
"""

from __future__ import annotations

import math

from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.drainage_result import (
    CHECK_ERROR,
    CHECK_INFO,
    CHECK_WARNING,
    FLOW_NONE,
    FLOW_TOWARD_END,
    FLOW_TOWARD_START,
    DitchRunFlowline,
    DrainageCheck,
    DrainageResult,
    DrainageSuggestion,
    FlowlineSegment,
    FlowlineStation,
)
from ...models.source.drainage_model import DitchRun, DrainageModel, DrainagePoint, ditch_run_covers

# Two sections closer than this are the same station (stations are stored rounded, and a
# supplemental section can land on a source station).
STATION_TOLERANCE_M = 1.0e-6
# An elevation change below this is no change: it is under the precision the section points carry,
# so it must not turn a flat flowline into a sequence of tiny low and high points.
ELEVATION_TOLERANCE_M = 1.0e-6


class DrainageEvaluationService:
    def evaluate(self, drainage_model: DrainageModel, applied_section_set: AppliedSectionSet | None) -> DrainageResult:
        policy = drainage_model.policy
        flowlines: list[DitchRunFlowline] = []
        checks: list[DrainageCheck] = []
        suggestions: list[DrainageSuggestion] = []
        sections = sorted(
            list(getattr(applied_section_set, "sections", []) or []),
            key=lambda section: float(getattr(section, "station", 0.0) or 0.0),
        )
        for run in [run for run in drainage_model.ditch_run_rows if run.enabled]:
            stations = _flowline_stations(run, sections)
            if len(stations) < 2:
                checks.append(
                    DrainageCheck(
                        f"flowline_missing:{run.ditch_run_id}",
                        "flowline_missing",
                        CHECK_ERROR,
                        run.ditch_run_id,
                        float(run.station_start),
                        float(run.station_end),
                        f"{run.ditch_run_id}: the Applied Sections give its ditch a flowline at {len(stations)} "
                        "station(s); two or more are needed. Rebuild Applied Sections, or check that the "
                        "run's ditch and stations match the Assembly and Regions.",
                    )
                )
                continue
            segments = _segments(stations)
            lows, highs = _low_and_high_points(stations, segments)
            flowlines.append(
                DitchRunFlowline(
                    run.ditch_run_id,
                    run.side,
                    run.subassembly_ref,
                    alignment_ref=run.alignment_ref,
                    station_rows=stations,
                    segment_rows=segments,
                    low_point_stations=lows,
                    high_point_stations=highs,
                )
            )
            checks.extend(_flat_grade_checks(run, segments, float(policy.min_grade_percent)))
            collectors, off_run = _collectors(run, drainage_model.point_rows, stations)
            checks.extend(off_run)
            low_checks, low_suggestions = _low_point_checks(run, stations, lows, collectors, policy.low_point_rule)
            checks.extend(low_checks)
            spacing_checks, spacing_suggestions = _spacing_checks(
                run,
                stations,
                highs,
                sorted([point.station for point in collectors] + [row.station for row in low_suggestions]),
                float(policy.max_inlet_spacing_m),
            )
            checks.extend(spacing_checks)
            suggestions.extend(_numbered(run, low_suggestions + spacing_suggestions))
        severities = {check.severity for check in checks}
        if not drainage_model.ditch_run_rows:
            status = "empty"
        elif CHECK_ERROR in severities:
            status = "error"
        elif CHECK_WARNING in severities:
            status = "warning"
        else:
            status = "ok"
        return DrainageResult(
            schema_version=1,
            project_id=drainage_model.project_id,
            drainage_model_ref=drainage_model.drainage_model_id,
            applied_section_set_ref=str(getattr(applied_section_set, "applied_section_set_id", "") or ""),
            min_grade_percent=float(policy.min_grade_percent),
            flowline_rows=flowlines,
            check_rows=checks,
            suggestion_rows=suggestions,
            status=status,
            source_refs=[drainage_model.drainage_model_id],
        )


def _flowline_stations(run: DitchRun, sections: list) -> list[FlowlineStation]:
    rows: list[FlowlineStation] = []
    for section in sections:
        station = float(getattr(section, "station", 0.0) or 0.0)
        if not ditch_run_covers(run, station, alignment_ref=str(getattr(section, "alignment_id", "") or "")):
            continue
        points = [
            point
            for point in list(getattr(section, "point_rows", []) or [])
            if point.point_role == "ditch_flowline" and point.drainage_ref == run.ditch_run_id
        ]
        if not points:
            continue
        low = min(points, key=lambda point: float(point.z))
        if rows and abs(rows[-1].station - station) <= STATION_TOLERANCE_M:
            continue
        rows.append(FlowlineStation(station, float(low.x), float(low.y), float(low.z), str(section.applied_section_id)))
    return rows


def _segments(stations: list[FlowlineStation]) -> list[FlowlineSegment]:
    segments: list[FlowlineSegment] = []
    for first, second in zip(stations, stations[1:]):
        # Plan length along the flowline: in a curve it differs from the station difference.
        length = math.hypot(second.x - first.x, second.y - first.y)
        rise = second.z - first.z
        grade = 0.0 if length <= 0.0 or abs(rise) <= ELEVATION_TOLERANCE_M else rise / length * 100.0
        flow = FLOW_TOWARD_START if grade > 0.0 else FLOW_TOWARD_END if grade < 0.0 else FLOW_NONE
        segments.append(FlowlineSegment(first.station, second.station, length, grade, flow))
    return segments


def _low_and_high_points(stations: list[FlowlineStation], segments: list[FlowlineSegment]) -> tuple[list[float], list[float]]:
    """Where the flowline turns from falling to rising (low) and from rising to falling (high).

    A flat stretch between the two belongs to the turn; its lowest (highest) station is reported.
    A flowline that falls toward one of its ends has a low point there.
    """

    lows: list[float] = []
    highs: list[float] = []
    turning = [(index, 1 if segment.grade_percent > 0.0 else -1) for index, segment in enumerate(segments) if segment.grade_percent != 0.0]
    if not turning:
        return lows, highs
    if turning[0][1] > 0:
        lows.append(stations[0].station)
    for (previous_index, previous_sign), (index, sign) in zip(turning, turning[1:]):
        if previous_sign == sign:
            continue
        # stations[previous_index + 1] .. stations[index] are the turn, flat stretches included
        between = stations[previous_index + 1 : index + 1]
        pick = min if previous_sign < 0 else max
        turn = pick(between, key=lambda row: row.z)
        (lows if previous_sign < 0 else highs).append(turn.station)
    if turning[-1][1] < 0:
        lows.append(stations[-1].station)
    return lows, highs


def _collectors(run: DitchRun, points: list[DrainagePoint], stations: list[FlowlineStation]):
    """The run's inlets and outfalls, and the culverts crossing its road, inside its flowline.

    A point of the run outside the flowline's stations collects nothing; it is reported.
    """

    start, end = stations[0].station, stations[-1].station
    collectors: list[DrainagePoint] = []
    off_run: list[DrainageCheck] = []
    for point in points:
        own = point.ditch_run_ref == run.ditch_run_id
        crossing = (
            point.kind == "culvert"
            and not point.ditch_run_ref
            and (not point.alignment_ref or not run.alignment_ref or point.alignment_ref == run.alignment_ref)
        )
        if not (own or crossing):
            continue
        if start - STATION_TOLERANCE_M <= point.station <= end + STATION_TOLERANCE_M:
            collectors.append(point)
        elif own:
            off_run.append(
                DrainageCheck(
                    f"point_off_run:{point.point_id}",
                    "point_off_run",
                    CHECK_WARNING,
                    run.ditch_run_id,
                    point.station,
                    point.station,
                    f"{point.point_id}: STA {point.station:.3f} is outside {run.ditch_run_id} "
                    f"(STA {start:.3f} to {end:.3f}), so it collects nothing.",
                )
            )
    return collectors, off_run


def _low_point_checks(run: DitchRun, stations, lows: list[float], collectors: list[DrainagePoint], rule: str):
    """A low point needs a collector within one section spacing of it, unless it may pond."""

    checks: list[DrainageCheck] = []
    suggestions: list[DrainageSuggestion] = []
    values = [row.station for row in stations]
    for index, low in enumerate(lows, start=1):
        position = min(range(len(values)), key=lambda at: abs(values[at] - low))
        neighbours = [abs(values[at] - low) for at in (position - 1, position + 1) if 0 <= at < len(values)]
        reach = max(neighbours) if neighbours else 0.0
        near = [point for point in collectors if abs(point.station - low) <= reach + STATION_TOLERANCE_M]
        if near:
            names = ", ".join(point.point_id for point in near)
            checks.append(_info(run, f"low_point:{run.ditch_run_id}:{index}", low, f"{run.ditch_run_id}: low point at STA {low:.3f}, collected by {names}."))
            continue
        if rule != "require_inlet":
            checks.append(_info(run, f"low_point:{run.ditch_run_id}:{index}", low, f"{run.ditch_run_id}: low point at STA {low:.3f}; water ponds here, as the Policy allows."))
            continue
        # water leaves the run at an end it falls toward: that is an outfall, elsewhere an inlet
        kind = "outfall" if position in (0, len(values) - 1) else "inlet"
        checks.append(
            DrainageCheck(
                f"low_point_uncollected:{run.ditch_run_id}:{index}",
                "low_point_uncollected",
                CHECK_WARNING,
                run.ditch_run_id,
                low,
                low,
                f"{run.ditch_run_id}: low point at STA {low:.3f} has no inlet or outfall within {reach:.1f} m.",
            )
        )
        suggestions.append(
            DrainageSuggestion("", kind, run.ditch_run_id, low, "low_point", f"Add an {kind} at the low point STA {low:.3f}.")
        )
    return checks, suggestions


def _spacing_checks(run: DitchRun, stations, highs: list[float], collector_stations: list[float], max_spacing: float):
    """No stretch of the flowline between collectors, high points and run ends may exceed the
    maximum inlet spacing; inlets split a longer stretch into equal parts."""

    checks: list[DrainageCheck] = []
    suggestions: list[DrainageSuggestion] = []
    if max_spacing <= 0.0:
        return checks, suggestions
    values = [row.station for row in stations]
    lengths = [0.0]
    for first, second in zip(stations, stations[1:]):
        lengths.append(lengths[-1] + math.hypot(second.x - first.x, second.y - first.y))
    marks = sorted({values[0], values[-1], *highs, *[s for s in collector_stations if values[0] <= s <= values[-1]]})
    for start, end in zip(marks, marks[1:]):
        length = _length_at(values, lengths, end) - _length_at(values, lengths, start)
        if length <= max_spacing + STATION_TOLERANCE_M:
            continue
        checks.append(
            DrainageCheck(
                f"inlet_spacing:{run.ditch_run_id}:{len(checks) + 1}",
                "inlet_spacing",
                CHECK_WARNING,
                run.ditch_run_id,
                start,
                end,
                f"{run.ditch_run_id}: STA {start:.3f} to {end:.3f} runs {length:.1f} m without an inlet; "
                f"the maximum spacing is {max_spacing:.1f} m.",
            )
        )
        parts = math.ceil(length / max_spacing - STATION_TOLERANCE_M)
        base = _length_at(values, lengths, start)
        for part in range(1, parts):
            station = round(_station_at(values, lengths, base + length * part / parts), 3)
            suggestions.append(
                DrainageSuggestion("", "inlet", run.ditch_run_id, station, "spacing", f"Add an inlet at STA {station:.3f} to keep the spacing under {max_spacing:.1f} m.")
            )
    return checks, suggestions


def _length_at(values: list[float], lengths: list[float], station: float) -> float:
    """Flowline length from the run's first station to `station`, linear between stations."""

    for index in range(1, len(values)):
        if station <= values[index] + STATION_TOLERANCE_M:
            span = values[index] - values[index - 1]
            ratio = 0.0 if span <= 0.0 else (station - values[index - 1]) / span
            return lengths[index - 1] + (lengths[index] - lengths[index - 1]) * min(max(ratio, 0.0), 1.0)
    return lengths[-1]


def _station_at(values: list[float], lengths: list[float], length: float) -> float:
    for index in range(1, len(values)):
        if length <= lengths[index] + STATION_TOLERANCE_M:
            span = lengths[index] - lengths[index - 1]
            ratio = 0.0 if span <= 0.0 else (length - lengths[index - 1]) / span
            return values[index - 1] + (values[index] - values[index - 1]) * min(max(ratio, 0.0), 1.0)
    return values[-1]


def _numbered(run: DitchRun, rows: list[DrainageSuggestion]) -> list[DrainageSuggestion]:
    ordered = sorted(rows, key=lambda row: row.station)
    return [
        DrainageSuggestion(f"suggestion:{run.ditch_run_id}:{index}", row.kind, row.ditch_run_ref, row.station, row.reason, row.message)
        for index, row in enumerate(ordered, start=1)
    ]


def _info(run: DitchRun, check_id: str, station: float, message: str) -> DrainageCheck:
    return DrainageCheck(check_id, "low_point", CHECK_INFO, run.ditch_run_id, station, station, message)


def _flat_grade_checks(run: DitchRun, segments: list[FlowlineSegment], min_grade_percent: float) -> list[DrainageCheck]:
    checks: list[DrainageCheck] = []
    stretch: list[FlowlineSegment] = []
    for segment in segments + [None]:
        if segment is not None and abs(segment.grade_percent) < min_grade_percent:
            stretch.append(segment)
            continue
        if stretch:
            flattest = min(abs(row.grade_percent) for row in stretch)
            start, end = stretch[0].station_start, stretch[-1].station_end
            checks.append(
                DrainageCheck(
                    f"flat_grade:{run.ditch_run_id}:{len(checks) + 1}",
                    "flat_grade",
                    CHECK_WARNING,
                    run.ditch_run_id,
                    start,
                    end,
                    f"{run.ditch_run_id}: STA {start:.3f} to {end:.3f}: the flowline grade falls to "
                    f"{flattest:.2f} %, under the {min_grade_percent:.2f} % minimum.",
                )
            )
            stretch = []
    return checks


__all__ = ["DrainageEvaluationService", "ELEVATION_TOLERANCE_M", "STATION_TOLERANCE_M"]
