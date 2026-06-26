"""Simulation package manifest builder for Watertight Solid outputs."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models.output.simulation_package_output import (
    SimulationPackageOutput,
    SimulationPackageSolidRow,
)
from ...models.output.simulation_qa_output import SimulationQaOutput
from ...models.output.surface_output import intersection_surface_replacement_blocker_kind
from .watertight_simulation_qa_service import (
    WatertightSimulationQaSolidInput,
    resolve_intersection_trim_handoff_status,
)


@dataclass(frozen=True)
class WatertightSimulationPackageBuildRequest:
    """Input bundle for building a first-slice simulation package manifest."""

    project_id: str = "corridorroad-v1"
    package_output_id: str = "simulation-package:watertight-solids"
    simulation_qa_output: SimulationQaOutput | None = None
    output_refs: list[str] = field(default_factory=list)
    solid_inputs: list[WatertightSimulationQaSolidInput] = field(default_factory=list)
    terrain_ref: str = ""
    terrain_bound_box: tuple[float, float, float, float, float, float] | None = None
    drainage_readiness: dict[str, object] = field(default_factory=dict)
    intersection_trim: dict[str, object] = field(default_factory=dict)
    intersection_handoff: dict[str, object] = field(default_factory=dict)


class WatertightSimulationPackageService:
    """Build a simulation hand-off manifest from QA and built solid outputs."""

    def build(self, request: WatertightSimulationPackageBuildRequest) -> SimulationPackageOutput:
        qa = getattr(request, "simulation_qa_output", None) or SimulationQaOutput(
            schema_version=1,
            project_id=str(getattr(request, "project_id", "") or "corridorroad-v1"),
        )
        solids = [
            SimulationPackageSolidRow(
                output_ref=str(getattr(row, "output_ref", "") or ""),
                target_families=_unique_refs(getattr(row, "target_families", []) or []),
                subassembly_refs=_split_refs(getattr(row, "subassembly_refs", []) or []),
                structure_refs=_split_refs(getattr(row, "structure_refs", []) or []),
                drainage_refs=[],
                flow_route_refs=_split_refs(getattr(row, "flow_route_refs", []) or []),
                material_refs=_split_refs(getattr(row, "material_refs", []) or []),
                source_refs=_split_refs(getattr(row, "source_refs", []) or []),
                volume=sum(max(float(value or 0.0), 0.0) for value in list(getattr(row, "volumes", []) or [])),
                shape_valid=bool(getattr(row, "shape_valid", False)),
            )
            for row in list(getattr(request, "solid_inputs", []) or [])
            if str(getattr(row, "output_ref", "") or "")
        ]
        family_refs = _unique_refs(family for row in solids for family in row.target_families)
        diagnostic_kinds = _unique_refs(
            str(getattr(row, "kind", "") or "")
            for row in list(getattr(qa, "diagnostic_rows", []) or [])
            if str(getattr(row, "kind", "") or "")
        )
        qa_ref = str(getattr(qa, "simulation_qa_output_id", "") or "simulation-qa:watertight-solids")
        intersection_handoff = dict(getattr(request, "intersection_handoff", {}) or {})
        intersection_final_quality_status = _drainage_text(intersection_handoff, "final_quality_status", "not_available")
        intersection_handoff_status = _drainage_text(intersection_handoff, "digital_twin_handoff", "not_available")
        shared_breakline_audit_status = _drainage_text(intersection_handoff, "shared_breakline_audit_status", "")
        shared_breakline_geometry_mismatch_count = _drainage_int(intersection_handoff, "shared_breakline_geometry_mismatch_count")
        shared_breakline_mesh_mismatch_count = _drainage_int(intersection_handoff, "shared_breakline_mesh_mismatch_count")
        shared_breakline_missing_consumer_count = _drainage_int(intersection_handoff, "shared_breakline_missing_consumer_count")
        shared_breakline_reversed_edge_count = _drainage_int(intersection_handoff, "shared_breakline_reversed_edge_count")
        shared_breakline_blocks_final_handoff = (
            shared_breakline_audit_status in {"error", "blocked", "warning"}
            or shared_breakline_geometry_mismatch_count > 0
            or shared_breakline_mesh_mismatch_count > 0
            or shared_breakline_missing_consumer_count > 0
            or shared_breakline_reversed_edge_count > 0
        )
        intersection_blocks_final_handoff = (
            intersection_final_quality_status == "blocked"
            or intersection_handoff_status == "review_required"
            or shared_breakline_blocks_final_handoff
        )
        replacement_blocker_kind = ""
        if intersection_blocks_final_handoff:
            diagnostic_kinds = _unique_refs([*diagnostic_kinds, "intersection_final_handoff_blocked"])
            if shared_breakline_blocks_final_handoff:
                diagnostic_kinds = _unique_refs([*diagnostic_kinds, "intersection_shared_breakline_audit_blocked"])
            replacement_readiness = _drainage_text(intersection_handoff, "replacement_readiness_status", "")
            replacement_selected_role = _drainage_text(intersection_handoff, "downstream_selected_role", "")
            replacement_blocker_kind = intersection_surface_replacement_blocker_kind(
                replacement_readiness,
                replacement_selected_role,
            )
            if replacement_blocker_kind:
                diagnostic_kinds = _unique_refs([*diagnostic_kinds, replacement_blocker_kind])
        package_ready = bool(getattr(qa, "simulation_ready", False)) and not intersection_blocks_final_handoff
        output_refs = _unique_refs(getattr(request, "output_refs", []) or [])
        drainage = dict(getattr(request, "drainage_readiness", {}) or {})
        intersection_trim = dict(getattr(request, "intersection_trim", {}) or {})
        intersection_trim_handoff_status = resolve_intersection_trim_handoff_status(
            status=_drainage_text(intersection_trim, "status", "not_available"),
            fuse_status=_drainage_text(intersection_trim, "fuse_status", "not_available"),
            ready_pair_count=_drainage_int(intersection_trim, "ready_pair_count"),
            blocked_pair_count=_drainage_int(intersection_trim, "blocked_pair_count"),
        )
        return SimulationPackageOutput(
            schema_version=1,
            project_id=str(getattr(request, "project_id", "") or getattr(qa, "project_id", "") or "corridorroad-v1"),
            simulation_package_output_id=str(getattr(request, "package_output_id", "") or "simulation-package:watertight-solids"),
            label="Simulation Package",
            selection_scope={"scope_kind": "simulation_package", "source": "watertight_solids"},
            source_refs=_unique_refs([
                qa_ref,
                *output_refs,
                *[ref for solid in solids for ref in solid.subassembly_refs],
                *[ref for solid in solids for ref in solid.material_refs],
                *[ref for solid in solids for ref in solid.source_refs],
            ]),
            result_refs=diagnostic_kinds,
            package_status="ready" if package_ready else "blocked",
            simulation_ready=package_ready,
            simulation_qa_output_ref=qa_ref,
            terrain_status=str(getattr(qa, "terrain_status", "") or "missing"),
            terrain_ref=str(getattr(request, "terrain_ref", "") or ""),
            terrain_bound_box=getattr(request, "terrain_bound_box", None),
            drainage_readiness_status=_drainage_text(drainage, "readiness_status", "missing"),
            drainage_source_status=_drainage_text(drainage, "source_status", "missing"),
            drainage_flow_route_count=_drainage_int(drainage, "flow_route_count"),
            drainage_capture_only_route_count=_drainage_int(drainage, "capture_only_route_count"),
            drainage_pipe_candidate_count=_drainage_int(drainage, "pipe_candidate_count"),
            drainage_unresolved_port_route_count=_drainage_int(drainage, "unresolved_port_route_count"),
            drainage_missing_element_route_count=_drainage_int(drainage, "missing_element_route_count"),
            drainage_lined_ditch_target_count=_drainage_int(drainage, "lined_ditch_target_count"),
            drainage_pipe_segment_target_count=_drainage_int(drainage, "pipe_segment_target_count"),
            drainage_pipeline_network_target_count=_drainage_int(drainage, "pipeline_network_target_count"),
            drainage_structure_body_target_count=_drainage_int(drainage, "structure_body_target_count"),
            drainage_built_output_count=_drainage_int(drainage, "built_drainage_output_count"),
            drainage_network_fuse_status=_drainage_text(drainage, "network_fuse_status", "not_available"),
            intersection_trim_status=_drainage_text(intersection_trim, "status", "not_available"),
            intersection_trim_result_ref=_drainage_text(intersection_trim, "result_ref", ""),
            intersection_trim_boundary_pair_count=_drainage_int(intersection_trim, "boundary_pair_count"),
            intersection_trim_ready_pair_count=_drainage_int(intersection_trim, "ready_pair_count"),
            intersection_trim_blocked_pair_count=_drainage_int(intersection_trim, "blocked_pair_count"),
            intersection_trim_pair_rows=[
                dict(row)
                for row in list(intersection_trim.get("pair_rows", []) or [])
                if isinstance(row, dict)
            ],
            intersection_trim_fuse_status=_drainage_text(intersection_trim, "fuse_status", "not_available"),
            intersection_trim_handoff_status=intersection_trim_handoff_status,
            intersection_trim_fuse_candidate_ref=_drainage_text(intersection_trim, "fuse_candidate_ref", ""),
            intersection_trim_fuse_source_count=_drainage_int(intersection_trim, "fuse_source_count"),
            intersection_trim_fuse_face_count=_drainage_int(intersection_trim, "fuse_face_count"),
            intersection_trim_fuse_open_edge_count=_drainage_int(intersection_trim, "fuse_open_edge_count"),
            intersection_trim_fuse_source_refs=[
                str(ref)
                for ref in list(intersection_trim.get("fuse_source_refs", []) or [])
                if str(ref)
            ],
            intersection_trim_handoff_chain_refs=[
                str(ref)
                for ref in list(intersection_trim.get("handoff_chain_refs", []) or [])
                if str(ref)
            ],
            intersection_trim_handoff_stage_statuses=[
                str(value)
                for value in list(intersection_trim.get("handoff_stage_statuses", []) or [])
                if str(value)
            ],
            intersection_handoff_readiness_status=_drainage_text(intersection_handoff, "readiness_status", "not_available"),
            intersection_handoff_final_quality_status=intersection_final_quality_status,
            intersection_handoff_status=intersection_handoff_status,
            intersection_handoff_target_count=_drainage_int(intersection_handoff, "target_count"),
            intersection_handoff_patch_target_count=_drainage_int(intersection_handoff, "patch_target_count"),
            intersection_handoff_accepted_zone_target_count=_drainage_int(intersection_handoff, "accepted_zone_target_count"),
            intersection_handoff_replacement_gate_status=_drainage_text(intersection_handoff, "replacement_gate_status", ""),
            intersection_handoff_replacement_readiness_status=_drainage_text(intersection_handoff, "replacement_readiness_status", ""),
            intersection_handoff_replacement_handoff_preference=_drainage_text(intersection_handoff, "replacement_handoff_preference", ""),
            intersection_handoff_downstream_selected_role=_drainage_text(intersection_handoff, "downstream_selected_role", ""),
            intersection_handoff_legacy_patch_review_visibility=_drainage_text(intersection_handoff, "legacy_patch_review_visibility", ""),
            intersection_handoff_legacy_patch_compatibility_audit_summary=_drainage_text(intersection_handoff, "legacy_patch_compatibility_audit_summary", ""),
            intersection_handoff_replacement_blocker_kind=replacement_blocker_kind,
            intersection_handoff_shared_breakline_audit_status=shared_breakline_audit_status,
            intersection_handoff_shared_breakline_geometry_mismatch_count=shared_breakline_geometry_mismatch_count,
            intersection_handoff_shared_breakline_mesh_mismatch_count=shared_breakline_mesh_mismatch_count,
            intersection_handoff_shared_breakline_missing_consumer_count=shared_breakline_missing_consumer_count,
            intersection_handoff_shared_breakline_reversed_edge_count=shared_breakline_reversed_edge_count,
            output_count=len(solids),
            total_volume=sum(float(getattr(row, "volume", 0.0) or 0.0) for row in solids),
            target_families=family_refs,
            missing_contexts=[str(value) for value in list(getattr(qa, "missing_contexts", []) or []) if str(value)],
            diagnostic_kinds=diagnostic_kinds,
            solid_rows=solids,
        )


def _unique_refs(values) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        refs.append(text)
    return refs


def _split_refs(values) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        for part in str(value or "").replace("|", ",").split(","):
            text = part.strip()
            if not text or text in seen:
                continue
            seen.add(text)
            refs.append(text)
    return refs


def _drainage_text(values: dict[str, object], key: str, default: str = "") -> str:
    return str(values.get(key, default) or default)


def _drainage_int(values: dict[str, object], key: str) -> int:
    try:
        return int(values.get(key, 0) or 0)
    except Exception:
        return 0
