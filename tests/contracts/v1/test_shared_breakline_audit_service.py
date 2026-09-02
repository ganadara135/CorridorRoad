from __future__ import annotations

from types import SimpleNamespace

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.models.result import (
    SharedBreaklineAdjacencyResult,
    SharedBreaklineAuditResult,
)
from freecad.Corridor_Road.v1.services.evaluation import SharedBreaklineAuditService
from freecad.Corridor_Road.v1.ui.presentation import (
    SharedBreaklineAuditPresentationMapper,
)


def _point(point_id: str, x: float, y: float, z: float = 0.0):
    return SimpleNamespace(point_id=point_id, x=x, y=y, z=z)


def _breakline(
    breakline_id: str,
    point_refs: tuple[str, ...],
    consumer_refs: tuple[str, ...] = ("design_surface",),
):
    return SimpleNamespace(
        breakline_id=breakline_id,
        point_refs=point_refs,
        consumer_refs=consumer_refs,
    )


def _shared_result(*breaklines):
    return SimpleNamespace(
        shared_breakline_result_id="shared:test",
        point_rows=[_point("p1", 0.0, 0.0), _point("p2", 10.0, 0.0)],
        breakline_rows=list(breaklines),
        breakline_count=len(breaklines),
        error_count=0,
    )


def test_missing_shared_breakline_returns_typed_missing_results() -> None:
    service = SharedBreaklineAuditService()

    adjacency = service.adjacency(None)
    audit = service.audit(None)

    assert isinstance(adjacency, SharedBreaklineAdjacencyResult)
    assert adjacency.status == "missing"
    assert adjacency.notes == "shared_breakline_result_missing"
    assert isinstance(audit, SharedBreaklineAuditResult)
    assert audit.status == "missing"
    assert audit.solid_readiness_status == "missing"
    assert audit.to_legacy_dict()["notes"] == "shared_breakline_result_missing"


def test_adjacency_reports_open_ends_for_one_breakline() -> None:
    shared = _shared_result(_breakline("breakline:1", ("p1", "p2")))

    result = SharedBreaklineAuditService().adjacency(shared)

    assert result.status == "warning"
    assert result.node_count == 2
    assert result.edge_count == 1
    assert result.open_end_count == 2
    assert result.duplicate_edge_count == 0
    assert result.notes == "open_end_count=2"


def test_adjacency_reports_duplicate_and_reversed_edges() -> None:
    shared = _shared_result(
        _breakline("breakline:1", ("p1", "p2")),
        _breakline("breakline:2", ("p2", "p1")),
    )

    result = SharedBreaklineAuditService().adjacency(shared)

    assert result.status == "warning"
    assert result.duplicate_edge_count == 1
    assert result.reversed_edge_count == 1
    assert "duplicate_edge:breakline:2:breakline:1" in result.notes
    assert "reversed_edge:breakline:2:breakline:1" in result.notes


def test_audit_reports_missing_consumer_boundary_reference() -> None:
    shared = _shared_result(_breakline("breakline:1", ("p1", "p2")))
    surface = SimpleNamespace(boundary_refs=[], triangle_rows=[])

    result = SharedBreaklineAuditService().audit(
        shared,
        {"design_surface": surface},
    )

    assert result.status == "warning"
    assert result.missing_consumer_count == 1
    assert result.geometry_match_count == 0
    assert result.notes == "missing_consumer:design_surface:breakline:1"
    assert result.source_result_ref == "shared:test"
    assert result.consumer_refs == ("design_surface",)


def test_audit_accepts_matching_mesh_edge_and_preserves_solid_warning() -> None:
    shared = _shared_result(_breakline("breakline:1", ("p1", "p2")))
    surface = SimpleNamespace(
        boundary_refs=["breakline:1"],
        quality_rows=[],
        vertex_rows=[
            SimpleNamespace(vertex_id="v1", x=0.0, y=0.0, z=0.0),
            SimpleNamespace(vertex_id="v2", x=10.0, y=0.0, z=0.0),
            SimpleNamespace(vertex_id="v3", x=0.0, y=5.0, z=0.0),
        ],
        triangle_rows=[SimpleNamespace(v1="v1", v2="v2", v3="v3")],
    )

    result = SharedBreaklineAuditService().audit(
        shared,
        {"design_surface": surface},
    )

    assert result.status == "ready"
    assert result.geometry_match_count == 1
    assert result.mesh_match_count == 1
    assert result.geometry_mismatch_count == 0
    assert result.mesh_mismatch_count == 0
    assert result.solid_readiness_status == "warning"
    assert result.solid_open_end_count == 2


def test_command_compatibility_wrappers_match_typed_service_mappings() -> None:
    shared = _shared_result(_breakline("breakline:1", ("p1", "p2")))
    surfaces = {"design_surface": SimpleNamespace(boundary_refs=[], triangle_rows=[])}
    service = SharedBreaklineAuditService()

    assert cmd_build_corridor.shared_breakline_adjacency_graph(
        shared
    ) == service.adjacency(shared).to_legacy_dict()
    assert cmd_build_corridor.shared_breakline_audit(
        shared,
        surfaces,
    ) == service.audit(shared, surfaces).to_legacy_dict()


def test_presentation_mapper_accepts_typed_and_legacy_results_equally() -> None:
    result = SharedBreaklineAuditResult(
        status="warning",
        missing_consumer_count=1,
        mismatch_count=2,
        geometry_match_count=3,
        geometry_mismatch_count=4,
        mesh_match_count=5,
        mesh_mismatch_count=6,
        reversed_edge_count=7,
        solid_readiness_status="warning",
        solid_open_end_count=8,
        solid_duplicate_edge_count=9,
        solid_reversed_edge_count=10,
        solid_non_manifold_node_count=11,
        solid_readiness_notes="open graph",
        notes="first; second",
    )
    mapper = SharedBreaklineAuditPresentationMapper()

    typed = mapper.map(result)
    legacy = mapper.map(result.to_legacy_dict())

    assert typed == legacy
    assert typed.summary == (
        "audit=warning geometry=3/7 mesh=5/11 missing=1 mismatch=2 reversed=7"
    )
    assert typed.note_rows == ("first", "second")
    assert cmd_build_corridor._shared_breakline_audit_summary(result) == typed.summary


def test_command_no_longer_contains_inactive_legacy_audit_implementations() -> None:
    assert not hasattr(
        cmd_build_corridor,
        "_legacy_shared_breakline_adjacency_graph",
    )
    assert not hasattr(cmd_build_corridor, "_legacy_shared_breakline_audit")
    assert not hasattr(
        cmd_build_corridor,
        "_surface_shared_breakline_constraint_matches",
    )
    assert not hasattr(
        cmd_build_corridor,
        "_surface_boundary_edge_matches_shared_breakline",
    )
