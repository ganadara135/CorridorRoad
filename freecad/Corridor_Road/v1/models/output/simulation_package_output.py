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
    output_count: int = 0
    total_volume: float = 0.0
    target_families: list[str] = field(default_factory=list)
    missing_contexts: list[str] = field(default_factory=list)
    diagnostic_kinds: list[str] = field(default_factory=list)
    solid_rows: list[SimulationPackageSolidRow] = field(default_factory=list)
