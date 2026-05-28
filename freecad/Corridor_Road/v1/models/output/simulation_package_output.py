"""Simulation package output contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class SimulationPackageSolidRow:
    """One built watertight solid included in a simulation hand-off package."""

    output_ref: str
    target_families: list[str] = field(default_factory=list)
    structure_refs: list[str] = field(default_factory=list)
    drainage_refs: list[str] = field(default_factory=list)
    flow_route_refs: list[str] = field(default_factory=list)
    volume: float = 0.0
    shape_valid: bool = False


@dataclass
class SimulationPackageOutput(OutputModelBase):
    """First-slice simulation package manifest."""

    simulation_package_output_id: str = "simulation-package:watertight-solids"
    package_status: str = "blocked"
    simulation_ready: bool = False
    simulation_qa_output_ref: str = ""
    terrain_status: str = "missing"
    terrain_ref: str = ""
    terrain_bound_box: tuple[float, float, float, float, float, float] | None = None
    drainage_readiness_status: str = "missing"
    drainage_source_status: str = "missing"
    drainage_flow_route_count: int = 0
    drainage_capture_only_route_count: int = 0
    drainage_pipe_candidate_count: int = 0
    drainage_unresolved_port_route_count: int = 0
    drainage_missing_element_route_count: int = 0
    drainage_lined_ditch_target_count: int = 0
    drainage_pipe_segment_target_count: int = 0
    drainage_pipeline_network_target_count: int = 0
    drainage_structure_body_target_count: int = 0
    drainage_built_output_count: int = 0
    drainage_network_fuse_status: str = "not_available"
    output_count: int = 0
    total_volume: float = 0.0
    target_families: list[str] = field(default_factory=list)
    missing_contexts: list[str] = field(default_factory=list)
    diagnostic_kinds: list[str] = field(default_factory=list)
    solid_rows: list[SimulationPackageSolidRow] = field(default_factory=list)
