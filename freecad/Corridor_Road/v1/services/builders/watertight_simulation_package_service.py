"""Simulation package manifest builder for Watertight Solid outputs."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models.output.simulation_package_output import (
    SimulationPackageOutput,
    SimulationPackageSolidRow,
)
from ...models.output.simulation_qa_output import SimulationQaOutput
from .watertight_simulation_qa_service import WatertightSimulationQaSolidInput


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
                structure_refs=_split_refs(getattr(row, "structure_refs", []) or []),
                drainage_refs=[],
                flow_route_refs=_split_refs(getattr(row, "flow_route_refs", []) or []),
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
        package_ready = bool(getattr(qa, "simulation_ready", False))
        output_refs = _unique_refs(getattr(request, "output_refs", []) or [])
        drainage = dict(getattr(request, "drainage_readiness", {}) or {})
        return SimulationPackageOutput(
            schema_version=1,
            project_id=str(getattr(request, "project_id", "") or getattr(qa, "project_id", "") or "corridorroad-v1"),
            simulation_package_output_id=str(getattr(request, "package_output_id", "") or "simulation-package:watertight-solids"),
            label="Simulation Package",
            selection_scope={"scope_kind": "simulation_package", "source": "watertight_solids"},
            source_refs=_unique_refs([qa_ref, *output_refs]),
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
