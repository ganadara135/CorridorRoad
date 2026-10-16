"""Ditch Run flowlines checked against the Drainage Policy (DR-2)."""

import pytest

from freecad.Corridor_Road.v1.models.result.applied_section import AppliedSection, AppliedSectionPoint
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet
from freecad.Corridor_Road.v1.models.source.drainage_model import DitchRun, DrainageModel, DrainagePolicy
from freecad.Corridor_Road.v1.services.evaluation.drainage_evaluation_service import DrainageEvaluationService

RUN = "ditch-run:left"


def _sections(flowline: list[tuple[float, float]], *, ref: str = RUN, offset: float = 6.0) -> AppliedSectionSet:
    """A straight road along x; the left ditch flowline at (station, offset, z)."""

    sections = []
    for station, z in flowline:
        sections.append(
            AppliedSection(
                schema_version=1,
                project_id="p",
                applied_section_id=f"section:{station:g}",
                alignment_id="alignment:main",
                station=station,
                point_rows=[
                    AppliedSectionPoint("ditch:edge", station, offset - 0.9, z + 0.45, "ditch_surface", offset - 0.9, "ditch:left", "left", ref),
                    AppliedSectionPoint("ditch:flowline:left:1", station, offset, z, "ditch_flowline", offset, "ditch:left", "left", ref),
                ],
            )
        )
    return AppliedSectionSet(schema_version=1, project_id="p", applied_section_set_id="applied:main", sections=sections)


def _model(*runs: DitchRun, min_grade: float = 0.3) -> DrainageModel:
    return DrainageModel(
        schema_version=1,
        project_id="p",
        policy=DrainagePolicy(min_grade_percent=min_grade),
        ditch_run_rows=list(runs) or [DitchRun(RUN, "left", "ditch:left", 0.0, 100.0, alignment_ref="alignment:main")],
    )


# a sag: falls 1 % and 0.5 %, a flat 20 m, then rises 1 % and 0.5 %
SAG = [(0.0, 10.0), (20.0, 9.8), (40.0, 9.7), (60.0, 9.7), (80.0, 9.9), (100.0, 10.0)]


def test_a_sag_gives_grades_flow_and_one_low_point() -> None:
    result = DrainageEvaluationService().evaluate(_model(), _sections(SAG))

    (flowline,) = result.flowline_rows
    assert [round(row.grade_percent, 6) for row in flowline.segment_rows] == [-1.0, -0.5, 0.0, 1.0, 0.5]
    assert [row.flow for row in flowline.segment_rows] == ["toward_end", "toward_end", "none", "toward_start", "toward_start"]
    assert [row.length_m for row in flowline.segment_rows] == pytest.approx([20.0] * 5)
    # the low point is the lowest station of the flat bottom; the flowline has no high point
    assert flowline.low_point_stations == [40.0]
    assert flowline.high_point_stations == []
    lows = [row for row in result.check_rows if row.kind == "low_point"]
    assert [(row.severity, row.station_start) for row in lows] == [("info", 40.0)]


def test_a_flowline_flatter_than_the_policy_minimum_is_a_warning() -> None:
    result = DrainageEvaluationService().evaluate(_model(min_grade=0.6), _sections(SAG))

    flats = [(row.station_start, row.station_end) for row in result.check_rows if row.kind == "flat_grade"]
    # 0.5 % and 0 % are under 0.6 %: STA 20-60 and STA 80-100
    assert flats == [(20.0, 60.0), (80.0, 100.0)]
    assert result.status == "warning"
    assert "0.00 %, under the 0.60 % minimum" in next(row.message for row in result.check_rows if row.kind == "flat_grade")


def test_a_flowline_falling_to_its_end_has_its_low_point_there() -> None:
    result = DrainageEvaluationService().evaluate(_model(), _sections([(0.0, 10.0), (50.0, 9.5), (100.0, 9.0)]))

    assert result.flowline_rows[0].low_point_stations == [100.0]
    assert result.status == "ok"


def test_a_hump_has_a_high_point_and_two_end_low_points() -> None:
    result = DrainageEvaluationService().evaluate(_model(), _sections([(0.0, 9.0), (50.0, 9.5), (100.0, 9.0)]))

    flowline = result.flowline_rows[0]
    assert flowline.high_point_stations == [50.0]
    assert flowline.low_point_stations == [0.0, 100.0]


def test_the_flowline_reads_only_its_own_run_and_span() -> None:
    other = _sections(SAG, ref="ditch-run:other")
    short = DitchRun(RUN, "left", "ditch:left", 20.0, 60.0, alignment_ref="alignment:main")
    sections = AppliedSectionSet(
        schema_version=1,
        project_id="p",
        applied_section_set_id="applied:main",
        sections=_sections(SAG).sections + other.sections,
    )

    result = DrainageEvaluationService().evaluate(_model(short), sections)

    assert [row.station for row in result.flowline_rows[0].station_rows] == [20.0, 40.0, 60.0]


def test_a_run_without_a_flowline_is_an_error_that_says_what_to_check() -> None:
    result = DrainageEvaluationService().evaluate(_model(), _sections(SAG, ref=""))

    assert result.flowline_rows == []
    (check,) = result.check_rows
    assert (check.kind, check.severity, check.ditch_run_ref) == ("flowline_missing", "error", RUN)
    assert "Rebuild Applied Sections" in check.message
    assert result.status == "error"


def test_a_switched_off_run_is_not_evaluated() -> None:
    off = DitchRun(RUN, "left", "ditch:left", 0.0, 100.0, enabled=False)

    result = DrainageEvaluationService().evaluate(_model(off), _sections(SAG))

    assert (result.flowline_rows, result.check_rows, result.status) == ([], [], "ok")
