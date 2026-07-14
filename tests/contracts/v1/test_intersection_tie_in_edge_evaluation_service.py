from __future__ import annotations

import inspect
from types import SimpleNamespace

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.models.result.intersection_tie_in_edge import (
    IntersectionTieInEdgeResult,
)
from freecad.Corridor_Road.v1.services.evaluation import (
    IntersectionTieInEdgeEvaluationRequest,
    IntersectionTieInEdgeEvaluationService,
)


def _point(point_id, x, y, z, offset):
    return SimpleNamespace(
        point_id=point_id,
        point_role="fg_surface",
        x=x,
        y=y,
        z=z,
        lateral_offset=offset,
    )


def _section(alignment_id, station, left_xyz, right_xyz, *, frame=None):
    return SimpleNamespace(
        applied_section_id=f"section:{alignment_id}:{station:.0f}",
        alignment_id=alignment_id,
        region_id=f"region:{alignment_id}",
        station=station,
        active_intersection_id="intersection:test",
        frame=frame,
        surface_left_width=5.0,
        surface_right_width=5.0,
        point_rows=(
            _point("fg:left", *left_xyz, 5.0),
            _point("fg:right", *right_xyz, -5.0),
        ),
    )


def _request(sections, alignment_refs, *, intersection_model=None):
    applied = SimpleNamespace(
        project_id="project:test",
        sections=tuple(sections),
        station_rows=(),
    )
    prerequisite = SimpleNamespace(
        intersection_id="intersection:test",
        alignment_refs=tuple(alignment_refs),
        control_region_refs=tuple(f"region:{value}" for value in alignment_refs),
    )
    return IntersectionTieInEdgeEvaluationRequest(
        applied_section_set=applied,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
    )


def test_service_builds_deterministic_primary_and_secondary_side_edges() -> None:
    sections = (
        _section("primary", 96.0, (96.0, 5.0, 10.0), (96.0, -5.0, 10.0)),
        _section("primary", 144.0, (144.0, 5.0, 10.0), (144.0, -5.0, 10.0)),
        _section("side", 96.0, (116.0, -24.0, 12.0), (124.0, -24.0, 12.0)),
        _section("side", 144.0, (116.0, 24.0, 12.0), (124.0, 24.0, 12.0)),
    )
    model = SimpleNamespace(
        intersection_rows=(
            SimpleNamespace(
                intersection_id="intersection:test",
                primary_alignment_ref="primary",
                primary_station=120.0,
                secondary_station_refs={"side": 120.0},
            ),
        ),
        control_area_rows=(),
    )

    result = IntersectionTieInEdgeEvaluationService().evaluate(
        _request(sections, ("primary", "side"), intersection_model=model)
    )

    assert isinstance(result, IntersectionTieInEdgeResult)
    assert result.status == "ready"
    assert result.edge_count == 4
    assert result.diagnostic_rows == []
    assert [row.tie_in_edge_id for row in result.edge_rows] == [
        "tie-in:intersection:test:primary:left",
        "tie-in:intersection:test:primary:right",
        "tie-in:intersection:test:side:left",
        "tie-in:intersection:test:side:right",
    ]
    assert all(row.station_start == 96.0 for row in result.edge_rows)
    assert all(row.station_end == 144.0 for row in result.edge_rows)
    assert result.edge_rows[2].start_xyz == (116.0, -24.0, 12.0)
    assert result.edge_rows[2].end_xyz == (116.0, 24.0, 12.0)


def test_service_spans_sections_on_both_sides_of_exact_target_station() -> None:
    sections = tuple(
        _section(
            "primary",
            station,
            (station, 5.0, 10.0),
            (station, -5.0, 10.0),
        )
        for station in (100.0, 120.0, 140.0)
    )
    model = SimpleNamespace(
        intersection_rows=(
            SimpleNamespace(
                intersection_id="intersection:test",
                primary_alignment_ref="primary",
                primary_station=120.0,
                secondary_station_refs={},
            ),
        ),
        control_area_rows=(),
    )

    result = IntersectionTieInEdgeEvaluationService().evaluate(
        _request(sections, ("primary",), intersection_model=model)
    )

    assert result.status == "ready"
    assert all(row.station_start == 100.0 for row in result.edge_rows)
    assert all(row.station_end == 140.0 for row in result.edge_rows)
    assert all(row.notes == "target_station=120.000" for row in result.edge_rows)


def test_service_marks_single_section_synthetic_edges_without_blocking_result() -> None:
    frame = SimpleNamespace(station=50.0, tangent_direction_deg=90.0)
    section = _section(
        "primary",
        50.0,
        (10.0, 5.0, 7.0),
        (10.0, -5.0, 7.0),
        frame=frame,
    )

    result = IntersectionTieInEdgeEvaluationService().evaluate(
        _request((section,), ("primary",))
    )

    assert result.status == "ready"
    assert result.edge_count == 2
    assert all(row.status == "single_section_candidate" for row in result.edge_rows)
    assert all(row.station_start == 42.5 for row in result.edge_rows)
    assert all(row.station_end == 57.5 for row in result.edge_rows)
    assert result.edge_rows[0].start_xyz == (10.0, -2.5, 7.0)
    assert result.edge_rows[0].end_xyz == (10.0, 12.5, 7.0)
    assert all(
        row.startswith(
            "warning:intersection_tie_in_edge_single_section_candidate:"
        )
        for row in result.diagnostic_rows
    )


def test_service_reports_missing_expected_alignment_and_incomplete_count() -> None:
    result = IntersectionTieInEdgeEvaluationService().evaluate(
        _request((), ("primary",))
    )

    assert result.status == "missing"
    assert result.edge_count == 0
    assert result.edge_rows == []
    assert result.diagnostic_rows == [
        "intersection_tie_in_edge_missing: no Applied Sections for primary.",
        "intersection_tie_in_edge_incomplete: expected 2 left/right edge "
        "candidate(s), found 0.",
    ]


def test_command_wrapper_and_preparation_pipeline_use_typed_service() -> None:
    wrapper_source = inspect.getsource(
        cmd_build_corridor.corridor_intersection_tie_in_edge_result
    )
    pipeline_source = inspect.getsource(
        cmd_build_corridor._build_intersection_surface_patch_tin
    )

    assert "IntersectionTieInEdgeEvaluationService().evaluate(" in wrapper_source
    assert "IntersectionTieInEdgeEvaluationRequest(" in wrapper_source
    assert "IntersectionTieInEdgeRow(" not in wrapper_source
    assert (
        "IntersectionTieInEdgeEvaluationService().evaluate_context"
        in pipeline_source
    )
