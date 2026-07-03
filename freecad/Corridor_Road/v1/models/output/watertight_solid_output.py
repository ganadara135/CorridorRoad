"""Watertight solid output contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class WatertightSolidOutputRow:
    """Normalized output row for one watertight solid target."""

    output_object_id: str
    target_id: str
    target_family: str
    scope_kind: str
    station_start: float
    station_end: float
    source_refs: list[str] = field(default_factory=list)
    generated_object_ref: str = ""
    validation_status: str = "not_checked"
    is_watertight: bool = False
    is_valid_solid: bool = False
    volume: float = 0.0
    face_count: int = 0
    edge_count: int = 0
    profile_count: int = 0
    diagnostic_refs: list[str] = field(default_factory=list)
    boundary_trace_rows: list[str] = field(default_factory=list)
    boundary_adjacency_rows: list[str] = field(default_factory=list)
    region_ref: str = ""
    assembly_ref: str = ""
    subassembly_ref: str = ""
    structure_ref: str = ""
    drainage_ref: str = ""
    flow_route_ref: str = ""
    material_ref: str = ""
    path_source: str = ""
    notes: str = ""


@dataclass(frozen=True)
class WatertightSolidSegmentRow:
    """Station segment metadata for one watertight solid output."""

    segment_id: str
    parent_output_object_id: str
    station_start: float
    station_end: float
    face_refs: list[str] = field(default_factory=list)
    profile_refs: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class WatertightSolidOutputDiagnosticRow:
    """Serializable diagnostic row for watertight solid output handoff."""

    diagnostic_id: str
    severity: str
    kind: str
    source_ref: str = ""
    message: str = ""
    notes: str = ""


@dataclass
class WatertightSolidOutput(OutputModelBase):
    """Normalized output payload for watertight solid results."""

    watertight_solid_output_id: str = ""
    corridor_id: str = ""
    solid_rows: list[WatertightSolidOutputRow] = field(default_factory=list)
    segment_rows: list[WatertightSolidSegmentRow] = field(default_factory=list)
    solid_diagnostic_rows: list[WatertightSolidOutputDiagnosticRow] = field(default_factory=list)
