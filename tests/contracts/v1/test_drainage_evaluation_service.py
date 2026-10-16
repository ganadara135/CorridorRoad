"""Ditch Run flowlines checked against the Drainage Policy (DR-2), with its points (DR-3)."""

import pytest

from freecad.Corridor_Road.v1.models.result.applied_section import AppliedSection, AppliedSectionPoint
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet
from freecad.Corridor_Road.v1.models.source.drainage_model import DitchRun, DrainageModel, DrainagePoint, DrainagePolicy
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


def _model(
    *runs: DitchRun,
    min_grade: float = 0.3,
    spacing: float = 60.0,
    rule: str = "require_inlet",
    points: list[DrainagePoint] | None = None,
) -> DrainageModel:
    return DrainageModel(
        schema_version=1,
        project_id="p",
        policy=DrainagePolicy(min_grade_percent=min_grade, max_inlet_spacing_m=spacing, low_point_rule=rule),
        ditch_run_rows=list(runs) or [DitchRun(RUN, "left", "ditch:left", 0.0, 400.0, alignment_ref="alignment:main")],
        point_rows=list(points or []),
    )


def _kinds(result) -> list[str]:
    return [row.kind for row in result.check_rows]


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
    # no inlet there yet: a warning and one suggested inlet; 0-40 and 40-100 stay within 60 m
    lows = [row for row in result.check_rows if row.kind == "low_point_uncollected"]
    assert [(row.severity, row.station_start) for row in lows] == [("warning", 40.0)]
    assert [(row.kind, row.station, row.reason) for row in result.suggestion_rows] == [("inlet", 40.0, "low_point")]


def test_the_suggested_inlet_collects_the_low_point() -> None:
    inlet = DrainagePoint("inlet:1", "inlet", 40.0, ditch_run_ref=RUN)

    result = DrainageEvaluationService().evaluate(_model(points=[inlet]), _sections(SAG))

    assert "low_point_uncollected" not in _kinds(result)
    assert result.suggestion_rows == []
    assert "collected by inlet:1" in next(row.message for row in result.check_rows if row.kind == "low_point")


def test_a_culvert_crossing_the_road_collects_a_nearby_low_point() -> None:
    culvert = DrainagePoint("culvert:1", "culvert", 50.0, alignment_ref="alignment:main")

    result = DrainageEvaluationService().evaluate(_model(points=[culvert]), _sections(SAG))

    assert "low_point_uncollected" not in _kinds(result)


def test_a_low_point_may_pond_when_the_policy_allows_it() -> None:
    result = DrainageEvaluationService().evaluate(_model(rule="allow_ponding", spacing=1000.0), _sections(SAG))

    assert "low_point_uncollected" not in _kinds(result)
    assert result.suggestion_rows == []
    assert "ponds here" in next(row.message for row in result.check_rows if row.kind == "low_point")


def test_a_long_stretch_gets_inlets_at_equal_spacing() -> None:
    # falls 1 % over 300 m to an outfall at its end
    falling = [(float(station), 10.0 - station / 100.0) for station in range(0, 301, 20)]
    outfall = DrainagePoint("outfall:1", "outfall", 300.0, ditch_run_ref=RUN)

    result = DrainageEvaluationService().evaluate(_model(points=[outfall]), _sections(falling))

    (spacing,) = [row for row in result.check_rows if row.kind == "inlet_spacing"]
    assert (spacing.station_start, spacing.station_end) == (0.0, 300.0)
    assert [(row.kind, row.station) for row in result.suggestion_rows] == [
        ("inlet", 60.0),
        ("inlet", 120.0),
        ("inlet", 180.0),
        ("inlet", 240.0),
    ]
    assert len({row.suggestion_id for row in result.suggestion_rows}) == 4


def test_applying_the_spacing_suggestions_clears_the_check() -> None:
    falling = [(float(station), 10.0 - station / 100.0) for station in range(0, 301, 20)]
    points = [DrainagePoint("outfall:1", "outfall", 300.0, ditch_run_ref=RUN)] + [
        DrainagePoint(f"inlet:{n}", "inlet", station, ditch_run_ref=RUN) for n, station in enumerate((60.0, 120.0, 180.0, 240.0), 1)
    ]

    result = DrainageEvaluationService().evaluate(_model(points=points), _sections(falling))

    assert result.status == "ok"
    assert result.suggestion_rows == []


def test_a_point_outside_its_run_collects_nothing_and_says_so() -> None:
    stray = DrainagePoint("inlet:far", "inlet", 450.0, ditch_run_ref=RUN)

    result = DrainageEvaluationService().evaluate(_model(points=[stray]), _sections(SAG))

    assert "outside ditch-run:left" in next(row.message for row in result.check_rows if row.kind == "point_off_run")
    assert "low_point_uncollected" in _kinds(result)


def test_a_flowline_flatter_than_the_policy_minimum_is_a_warning() -> None:
    result = DrainageEvaluationService().evaluate(_model(min_grade=0.6, rule="allow_ponding"), _sections(SAG))

    flats = [(row.station_start, row.station_end) for row in result.check_rows if row.kind == "flat_grade"]
    # 0.5 % and 0 % are under 0.6 %: STA 20-60 and STA 80-100
    assert flats == [(20.0, 60.0), (80.0, 100.0)]
    assert result.status == "warning"
    assert "0.00 %, under the 0.60 % minimum" in next(row.message for row in result.check_rows if row.kind == "flat_grade")


def test_a_flowline_falling_to_its_end_has_its_low_point_there() -> None:
    result = DrainageEvaluationService().evaluate(_model(spacing=1000.0), _sections([(0.0, 10.0), (50.0, 9.5), (100.0, 9.0)]))

    assert result.flowline_rows[0].low_point_stations == [100.0]
    # water leaves the run at its end: an outfall
    assert [(row.kind, row.station) for row in result.suggestion_rows] == [("outfall", 100.0)]


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
