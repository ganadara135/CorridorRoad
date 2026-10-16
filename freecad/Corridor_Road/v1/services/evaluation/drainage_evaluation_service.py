"""Drainage evaluation: the flowline of each Ditch Run, checked against the Drainage Policy.

The flowline of a run is its ditch's `ditch_flowline` point (the lowest point of the ditch) at
every Applied Section the run covers; Applied Sections tag those points with the run id. From the
flowline come the grades, the low and high points and the flow direction. Nothing is authored
here and nothing reads FreeCAD.

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
    FlowlineSegment,
    FlowlineStation,
)
from ...models.source.drainage_model import DitchRun, DrainageModel, ditch_run_covers

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
            checks.extend(
                DrainageCheck(
                    f"low_point:{run.ditch_run_id}:{index}",
                    "low_point",
                    CHECK_INFO,
                    run.ditch_run_id,
                    station,
                    station,
                    f"{run.ditch_run_id}: low point at STA {station:.3f}; water collects here.",
                )
                for index, station in enumerate(lows, start=1)
            )
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
