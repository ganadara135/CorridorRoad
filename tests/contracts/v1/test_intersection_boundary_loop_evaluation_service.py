from __future__ import annotations

import inspect
from types import SimpleNamespace

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.models.result import (
    IntersectionBoundaryLoopEvaluationChainResult,
)
from freecad.Corridor_Road.v1.services.evaluation import (
    IntersectionBoundaryLoopEvaluationRequest,
    IntersectionBoundaryLoopEvaluationService,
)


class _EvaluationService:
    def __init__(self, *, fail_stage=""):
        self.calls = []
        self.fail_stage = fail_stage
        self.topology = SimpleNamespace(result_id="topology:test")
        self.edges = SimpleNamespace(result_id="edges:test")
        self.zones = SimpleNamespace(result_id="zones:test")
        self.slope_loops = SimpleNamespace(result_id="slope-loops:test")
        self.boundary_loops = SimpleNamespace(result_id="boundary-loops:test")

    def _record(self, stage):
        self.calls.append(stage)
        if self.fail_stage == stage:
            raise ValueError(f"test failure at {stage}")

    def evaluate_topology(self, intersection_model):
        self._record("topology")
        assert intersection_model.model_id == "intersections:test"
        return self.topology

    def evaluate_edge_network(self, intersection_model, topology_result):
        self._record("edge_network")
        assert intersection_model.model_id == "intersections:test"
        assert topology_result is self.topology
        return self.edges

    def evaluate_surface_zones(self, intersection_model, edge_network_result):
        self._record("surface_zones")
        assert intersection_model.model_id == "intersections:test"
        assert edge_network_result is self.edges
        return self.zones

    def evaluate_slope_face_loops(
        self,
        intersection_model,
        surface_zone_result,
        edge_network_result,
        applied_section_set,
    ):
        self._record("slope_face_loops")
        assert intersection_model.model_id == "intersections:test"
        assert surface_zone_result is self.zones
        assert edge_network_result is self.edges
        assert applied_section_set.applied_section_set_id == "sections:test"
        return self.slope_loops

    def evaluate_boundary_loops(self, intersection_model, **kwargs):
        self._record("boundary_loops")
        assert intersection_model.model_id == "intersections:test"
        assert kwargs == {
            "surface_zone_result": self.zones,
            "edge_network_result": self.edges,
            "slope_face_loop_result": self.slope_loops,
            "applied_section_set": _APPLIED_SECTIONS,
            "intersection_id": "intersection:test",
        }
        return self.boundary_loops


_APPLIED_SECTIONS = SimpleNamespace(applied_section_set_id="sections:test")
_PREREQUISITE = SimpleNamespace(intersection_id="intersection:test")
_INTERSECTION_MODEL = SimpleNamespace(model_id="intersections:test")


def _request(*, intersection_model=_INTERSECTION_MODEL):
    return IntersectionBoundaryLoopEvaluationRequest(
        applied_section_set=_APPLIED_SECTIONS,
        prerequisite=_PREREQUISITE,
        intersection_model=intersection_model,
    )


def test_service_preserves_authoritative_evaluation_order_and_results() -> None:
    evaluator = _EvaluationService()

    result = IntersectionBoundaryLoopEvaluationService(
        evaluation_service=evaluator
    ).evaluate(_request())

    assert isinstance(result, IntersectionBoundaryLoopEvaluationChainResult)
    assert result.status == "ready"
    assert result.intersection_id == "intersection:test"
    assert result.completed_stages == (
        "topology",
        "edge_network",
        "surface_zones",
        "slope_face_loops",
        "boundary_loops",
    )
    assert evaluator.calls == list(result.completed_stages)
    assert result.topology_result is evaluator.topology
    assert result.edge_network_result is evaluator.edges
    assert result.surface_zone_result is evaluator.zones
    assert result.slope_face_loop_result is evaluator.slope_loops
    assert result.boundary_loop_result is evaluator.boundary_loops
    assert result.failed_stage == ""
    assert result.diagnostic_rows == ()


def test_service_reports_missing_model_without_running_evaluation() -> None:
    evaluator = _EvaluationService()

    result = IntersectionBoundaryLoopEvaluationService(
        evaluation_service=evaluator
    ).evaluate(_request(intersection_model=None))

    assert result.status == "missing"
    assert result.failed_stage == "input_validation"
    assert result.completed_stages == ()
    assert result.boundary_loop_result is None
    assert result.diagnostic_rows == ("intersection_boundary_loop_model_missing",)
    assert result.error_message == "Intersection model is required."
    assert evaluator.calls == []


def test_service_retains_partial_results_and_exact_failure_diagnostic() -> None:
    evaluator = _EvaluationService(fail_stage="surface_zones")

    result = IntersectionBoundaryLoopEvaluationService(
        evaluation_service=evaluator
    ).evaluate(_request())

    assert result.status == "error"
    assert result.failed_stage == "surface_zones"
    assert result.completed_stages == ("topology", "edge_network")
    assert result.topology_result is evaluator.topology
    assert result.edge_network_result is evaluator.edges
    assert result.surface_zone_result is None
    assert result.slope_face_loop_result is None
    assert result.boundary_loop_result is None
    assert result.diagnostic_rows == (
        "intersection_boundary_loop_evaluation_failed:test failure at surface_zones",
    )
    assert result.error_message == "test failure at surface_zones"


def test_context_adapter_extends_diagnostics_and_returns_boundary_result() -> None:
    evaluator = _EvaluationService()
    diagnostics = ["existing:diagnostic"]

    boundary_result = IntersectionBoundaryLoopEvaluationService(
        evaluation_service=evaluator
    ).evaluate_context(
        _APPLIED_SECTIONS,
        prerequisite=_PREREQUISITE,
        intersection_model=None,
        diagnostics=diagnostics,
    )

    assert boundary_result is None
    assert diagnostics == [
        "existing:diagnostic",
        "intersection_boundary_loop_model_missing",
    ]


def test_command_pipeline_uses_service_and_compatibility_wrapper_is_thin() -> None:
    pipeline_source = inspect.getsource(
        cmd_build_corridor._build_intersection_surface_patch_tin
    )
    wrapper_source = inspect.getsource(
        cmd_build_corridor._intersection_boundary_loop_result_for_shared_breaklines
    )

    assert (
        "IntersectionBoundaryLoopEvaluationService().evaluate_context"
        in pipeline_source
    )
    assert (
        "IntersectionBoundaryLoopEvaluationService().evaluate_context"
        in wrapper_source
    )
    assert "IntersectionEvaluationService()" not in wrapper_source
    assert "evaluate_topology(" not in wrapper_source
