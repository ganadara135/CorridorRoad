"""The Drainage output and the Drainage Review rows built from it (DR-5)."""

from freecad.Corridor_Road.v1.models.result.applied_section import AppliedSection, AppliedSectionPoint
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet
from freecad.Corridor_Road.v1.models.source.drainage_model import (
    DitchRun,
    DrainageLink,
    DrainageModel,
    DrainagePoint,
    DrainagePolicy,
)
from freecad.Corridor_Road.v1.services.evaluation.drainage_evaluation_service import DrainageEvaluationService
from freecad.Corridor_Road.v1.services.evaluation.output_traceability_service import OutputTraceabilityService
from freecad.Corridor_Road.v1.services.mapping.drainage_output_mapper import DrainageOutputMapper
from freecad.Corridor_Road.v1.ui.presentation.drainage_review_presentation import (
    drainage_check_table_rows,
    drainage_flowline_profile,
    drainage_review_run_rows,
    drainage_review_summary,
)

RUN = "ditch-run:ditch:left"
# a sag: falls to STA 40-60, then rises
SAG = [(0.0, 10.0), (20.0, 9.8), (40.0, 9.7), (60.0, 9.7), (80.0, 9.9), (100.0, 10.0)]


def _output():
    sections = AppliedSectionSet(
        schema_version=1,
        project_id="p",
        applied_section_set_id="applied:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="p",
                applied_section_id=f"section:{station:g}",
                alignment_id="alignment:main",
                station=station,
                point_rows=[AppliedSectionPoint("flow", station, 6.0, z, "ditch_flowline", 6.0, "ditch:left", "left", RUN)],
            )
            for station, z in SAG
        ],
    )
    model = DrainageModel(
        schema_version=1,
        project_id="p",
        policy=DrainagePolicy(min_grade_percent=0.3, max_inlet_spacing_m=1000.0),
        ditch_run_rows=[DitchRun(RUN, "left", "ditch:left", 0.0, 100.0, alignment_ref="alignment:main")],
        point_rows=[
            DrainagePoint("inlet:1", "inlet", 20.0, side="left", ditch_run_ref=RUN),
            DrainagePoint("outfall:1", "outfall", 40.0, side="left", ditch_run_ref=RUN),
        ],
        link_rows=[DrainageLink("link:1", "inlet:1", "outfall:1")],
    )
    result = DrainageEvaluationService().evaluate(model, sections)
    return DrainageOutputMapper().map(model, result)


def test_the_output_carries_flowlines_points_links_and_checks_with_their_owners() -> None:
    output = _output()

    (flowline,) = output.flowline_rows
    assert (flowline.station_start, flowline.station_end, round(flowline.length_m, 6)) == (0.0, 100.0, 100.0)
    assert (round(flowline.min_grade_percent, 6), round(flowline.max_grade_percent, 6)) == (-1.0, 1.0)
    assert flowline.low_point_stations == (40.0,)
    assert [(row.point_ref, round(row.z, 6)) for row in output.point_rows] == [("inlet:1", 9.8), ("outfall:1", 9.7)]
    assert [(row.link_ref, round(row.grade_percent, 6)) for row in output.link_rows] == [("link:1", -0.5)]
    assert output.source_refs == ["drainage:main"]
    assert output.result_refs == ["drainage-result:main", "applied:main"]
    assert OutputTraceabilityService().validate_supported_output(output).status == "ready"


def test_the_profile_marks_points_low_points_and_flagged_stretches() -> None:
    output = _output()

    profile = drainage_flowline_profile(output, RUN)

    assert profile.points[0] == (0.0, 10.0) and len(profile.points) == 6
    assert [(marker.label, marker.kind) for marker in profile.markers] == [("inlet:1", "inlet"), ("outfall:1", "outfall")]
    assert profile.low_points == ((40.0, 9.7),)
    # the flat bottom STA 40-60 is under the 0.3 % minimum
    assert profile.flagged == ((40.0, 60.0, "warning"),)
    assert drainage_flowline_profile(output, "ditch-run:none") is None


def test_the_check_table_lists_warnings_before_info_and_the_runs_have_counts() -> None:
    output = _output()

    rows = drainage_check_table_rows(output, RUN)

    severities = [row["severity"] for row in rows]
    assert severities == sorted(severities, key=["error", "warning", "info"].index)
    assert rows[0]["kind"] == "flat_grade" and rows[0]["stations"] == "40.000-60.000"
    assert any(row["kind"] == "low_point" and row["stations"] == "40.000" for row in rows)
    (run,) = drainage_review_run_rows(output)
    assert (run["ditch_run_ref"], run["errors"], run["warnings"]) == (RUN, 0, 1)
    assert "1 flowline(s), 2 point(s), 1 link(s); 0 error(s), 1 warning(s)" in drainage_review_summary(output)
    assert "No Drainage result" in drainage_review_summary(None)
