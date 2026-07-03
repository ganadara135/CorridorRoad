"""Simulation QA output contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class SimulationQaFamilyRow:
    """Coverage summary for one simulation solid family."""

    family: str
    status: str
    output_count: int = 0
    total_volume: float = 0.0
    notes: str = ""


@dataclass(frozen=True)
class SimulationQaDiagnosticRow:
    """Diagnostic row for simulation-readiness review."""

    diagnostic_id: str
    severity: str
    kind: str
    source_ref: str = ""
    message: str = ""
    notes: str = ""


@dataclass
class SimulationQaOutput(OutputModelBase):
    """First-slice simulation-readiness QA summary."""

    simulation_qa_output_id: str = "simulation-qa:watertight-solids"
    output_count: int = 0
    road_body_status: str = "missing"
    terrain_status: str = "missing"
    drainage_status: str = "missing"
    structure_status: str = "missing"
    solid_validity_status: str = "check"
    geometry_contact_status: str = "not_checked"
    terrain_domain_status: str = "not_checked"
    port_connection_status: str = "not_checked"
    intersection_trim_status: str = "not_available"
    intersection_trim_fuse_status: str = "not_available"
    intersection_trim_handoff_status: str = "not_available"
    intersection_handoff_final_quality_status: str = "not_available"
    intersection_handoff_status: str = "not_available"
    intersection_replacement_readiness_status: str = ""
    intersection_replacement_blocker_kind: str = ""
    simulation_ready: bool = False
    invalid_output_count: int = 0
    zero_volume_output_count: int = 0
    contact_issue_count: int = 0
    terrain_issue_count: int = 0
    port_issue_count: int = 0
    intersection_trim_ready_pair_count: int = 0
    intersection_trim_blocked_pair_count: int = 0
    intersection_trim_max_gap: float = 0.0
    total_volume: float = 0.0
    missing_contexts: list[str] = field(default_factory=list)
    family_rows: list[SimulationQaFamilyRow] = field(default_factory=list)
    diagnostic_rows: list[SimulationQaDiagnosticRow] = field(default_factory=list)
