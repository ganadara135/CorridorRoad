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
    drainage_pipe_table_rows,
    drainage_flowline_profile,
    drainage_review_run_rows,
    drainage_review_summary,
)

RUN = "ditch-run:ditch:left"
# a sag: falls to STA 40-60, then rises
SAG = [(0.0, 10.0), (20.0, 9.8), (40.0, 9.7), (60.0, 9.7), (80.0, 9.9), (100.0, 10.0)]


def _sections():
    return AppliedSectionSet(
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


def _output_model():
    return DrainageModel(
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


def _output():
    model = _output_model()
    result = DrainageEvaluationService().evaluate(model, _sections())
    return DrainageOutputMapper().map(model, result)


def test_the_output_carries_the_pipes_and_the_review_lists_them() -> None:
    output = _output()
    assert output.pipe_rows == [] and drainage_pipe_table_rows(output) == []
    assert "pipe(s)" not in drainage_review_summary(output)

    model = DrainageModel(
        schema_version=1,
        project_id="p",
        policy=DrainagePolicy(min_grade_percent=0.3, max_inlet_spacing_m=1000.0),
        ditch_run_rows=[DitchRun(RUN, "left", "ditch:left", 0.0, 100.0, alignment_ref="alignment:main")],
        point_rows=[
            DrainagePoint("inlet:1", "inlet", 20.0, side="left", ditch_run_ref=RUN),
            DrainagePoint("outfall:1", "outfall", 40.0, side="left", ditch_run_ref=RUN),
        ],
        link_rows=[DrainageLink("link:1", "inlet:1", "outfall:1", pipe_diameter_m=0.6)],
    )
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
    result = DrainageEvaluationService().evaluate(model, sections)
    piped = DrainageOutputMapper().map(model, result)
    (pipe,) = piped.pipe_rows
    assert (pipe.link_ref, pipe.from_ref, pipe.to_ref, pipe.diameter_m) == ("link:1", "inlet:1", "outfall:1", 0.6)
    assert (pipe.from_invert_z, pipe.to_invert_z) == (result.pipe_rows[0].from_z, result.pipe_rows[0].to_z)
    assert pipe.from_xyz == (20.0, 6.0, pipe.from_invert_z) and pipe.to_xyz[0] == 40.0
    assert pipe.volume_m3 == result.pipe_rows[0].volume_m3 > 0.0
    (row,) = drainage_pipe_table_rows(piped)
    assert (row["link_ref"], row["route"], row["diameter"]) == ("link:1", "inlet:1 -> outfall:1", "0.60")
    assert ", 1 pipe(s);" in drainage_review_summary(piped)


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


def test_the_editing_profile_draws_the_points_and_links_of_the_tables_on_the_stored_flowline() -> None:
    from freecad.Corridor_Road.v1.ui.presentation.drainage_review_presentation import (
        drainage_editing_profile,
        drainage_editing_run_refs,
        drainage_run_of_link,
    )

    model = _output_model()
    result = DrainageEvaluationService().evaluate(model, _sections())
    flowlines = result.flowline_rows
    assert drainage_editing_run_refs(flowlines) == [RUN]

    # edits not yet applied: an outfall at STA 60 and a piped link to it
    points = [
        DrainagePoint("inlet:1", "inlet", 20.0, ditch_run_ref=RUN),
        DrainagePoint("outfall:2", "outfall", 60.0, ditch_run_ref=RUN),
        DrainagePoint("outfall:9", "outfall", 500.0, ditch_run_ref=RUN),
        DrainagePoint("culvert:1", "culvert", 80.0),
    ]
    links = [
        DrainageLink("link:1", "inlet:1", "outfall:2", pipe_diameter_m=0.6),
        DrainageLink("link:2", "outfall:2", "outfall:9"),
        DrainageLink("link:3", "outfall:2", "culvert:1"),
    ]
    profile = drainage_editing_profile(flowlines, points, links, RUN, selected_link_id="link:1", selected_point_id="outfall:2")

    # a point past the flowline is not drawn, and a link needs both its points on the run
    assert [marker.label for marker in profile.markers] == ["inlet:1", "outfall:2", "culvert:1"]
    assert [marker.selected for marker in profile.markers] == [False, True, False]
    assert [link.link_id for link in profile.links] == ["link:1", "link:3"]
    piped = profile.links[0]
    assert (piped.from_station, piped.to_station, piped.pipe_diameter_m, piped.selected) == (20.0, 60.0, 0.6, True)
    # the marker sits on the stored flowline
    assert abs(profile.markers[0].z - 9.8) < 1.0e-9

    assert drainage_editing_profile(flowlines, points, links, "ditch-run:other") is None
    assert drainage_run_of_link(points, links, "link:1") == RUN
    # a culvert has no run of its own: the other end's run is drawn
    assert drainage_run_of_link(points, [DrainageLink("link:4", "culvert:1", "outfall:2")], "link:4") == RUN
    assert drainage_run_of_link(points, links, "link:missing") == ""
