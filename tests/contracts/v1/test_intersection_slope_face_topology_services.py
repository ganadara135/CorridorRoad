from __future__ import annotations

from freecad.Corridor_Road.v1.models.result.shared_breakline import (
    SharedBreaklinePointRow,
    SharedBreaklineResult,
    SharedBreaklineRow,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_shared_boundary_graph_evaluation_service import (
    IntersectionSharedBoundaryGraphEvaluationRequest,
    IntersectionSharedBoundaryGraphEvaluationService,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_slope_face_cell_evaluation_service import (
    IntersectionSlopeFaceCellEvaluationRequest,
    IntersectionSlopeFaceCellEvaluationService,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_evaluation_service import (
    IntersectionPatchPrerequisiteResult,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_tie_slope_evaluation_service import (
    IntersectionTieSlopeEvaluationRequest,
    IntersectionTieSlopeEvaluationService,
)


def _shared_breaklines() -> SharedBreaklineResult:
    coordinates = {
        "p0": (0.0, 0.0, 0.0),
        "p1": (2.0, 0.0, 0.0),
        "p2": (2.0, 1.0, 0.0),
        "p3": (0.0, 1.0, 0.0),
    }
    points = [
        SharedBreaklinePointRow(
            point_id=point_id,
            breakline_ref="",
            sequence=index,
            x=xyz[0],
            y=xyz[1],
            z=xyz[2],
        )
        for index, (point_id, xyz) in enumerate(coordinates.items())
    ]
    rows = [
        SharedBreaklineRow(
            breakline_id="patch",
            domain_kind="intersection",
            domain_ref="intersection:test",
            breakline_role="patch_to_intersection_slope_face",
            source_contract_refs=("boundary-loop:patch",),
            point_refs=("p0", "p1"),
            consumer_refs=("intersection_surface", "intersection_slope_face_surface"),
            alignment_ref="alignment:main",
            side="left",
            source_status="ready",
        ),
        SharedBreaklineRow(
            breakline_id="outer",
            domain_kind="intersection",
            domain_ref="intersection:test",
            breakline_role="intersection_slope_face_to_corridor_slope_face",
            source_contract_refs=("applied-section:slope",),
            point_refs=("p3", "p2"),
            consumer_refs=("intersection_slope_face_surface", "slope_face_surface"),
            alignment_ref="alignment:main",
            side="left",
            source_status="ready",
        ),
        SharedBreaklineRow(
            breakline_id="design",
            domain_kind="intersection",
            domain_ref="intersection:test",
            breakline_role="intersection_slope_face_to_design_surface",
            source_contract_refs=("applied-section:design",),
            point_refs=("p1", "p2", "p3", "p0"),
            consumer_refs=("intersection_slope_face_surface", "design_surface"),
            alignment_ref="alignment:main",
            side="left",
            source_status="ready",
        ),
    ]
    return SharedBreaklineResult(
        schema_version=1,
        project_id="project:test",
        domain_kind="intersection",
        domain_ref="intersection:test",
        status="ready",
        breakline_count=len(rows),
        ready_count=len(rows),
        breakline_rows=rows,
        point_rows=points,
    )


def test_slope_face_cell_service_returns_typed_missing_result() -> None:
    result = IntersectionSlopeFaceCellEvaluationService().evaluate(
        IntersectionSlopeFaceCellEvaluationRequest(None, "intersection:test")
    )

    assert result.status == "missing"
    assert result.intersection_id == "intersection:test"
    assert result.diagnostic_rows == ["shared_breakline_result_missing"]


def test_slope_face_cell_service_builds_source_owned_cell() -> None:
    result = IntersectionSlopeFaceCellEvaluationService().evaluate(
        IntersectionSlopeFaceCellEvaluationRequest(
            _shared_breaklines(),
            "intersection:test",
        )
    )

    assert result.cell_count == 3
    assert all(
        row.source_intersection_refs
        == (
            "boundary-loop:patch",
            "applied-section:slope",
            "applied-section:design",
        )
        for row in result.cell_rows
    )
    assert all(
        row.source_shared_breakline_refs == ("patch", "outer", "design")
        for row in result.cell_rows
    )
    assert all(
        row.consumer_surface_ref == "intersection_slope_face_surface"
        for row in result.cell_rows
    )


def test_shared_boundary_graph_service_uses_cell_result_contract() -> None:
    result = IntersectionSharedBoundaryGraphEvaluationService().evaluate(
        IntersectionSharedBoundaryGraphEvaluationRequest(
            _shared_breaklines(),
            "intersection:test",
        )
    )

    assert result.intersection_id == "intersection:test"
    assert result.node_count >= 4
    assert result.edge_count >= 3
    assert all(
        row.source_refs
        for row in result.edge_rows
        if row.edge_role != "cell_closure_internal_seam"
    )


def test_tie_slope_service_returns_typed_missing_result() -> None:
    prerequisite = IntersectionPatchPrerequisiteResult(
        status="ready",
        intersection_id="intersection:test",
    )

    result = IntersectionTieSlopeEvaluationService().evaluate(
        IntersectionTieSlopeEvaluationRequest(None, prerequisite)
    )

    assert result.status == "missing"
    assert result.intersection_id == "intersection:test"
    assert result.diagnostic_rows == [
        "intersection_tie_slope_missing: Applied Sections are required."
    ]


def test_tie_slope_service_keeps_roundabout_out_of_generic_path() -> None:
    prerequisite = IntersectionPatchPrerequisiteResult(
        status="ready",
        intersection_id="intersection:roundabout",
        intersection_kind="roundabout",
    )
    applied_section_set = type(
        "AppliedSectionSetStub",
        (),
        {"project_id": "project:test"},
    )()

    result = IntersectionTieSlopeEvaluationService().evaluate(
        IntersectionTieSlopeEvaluationRequest(
            applied_section_set,
            prerequisite,
        )
    )

    assert result.status == "missing"
    assert "info:roundabout_generic_intersection_tie_slope_disabled" in (
        result.diagnostic_rows
    )
