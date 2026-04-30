"""Structure solid output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class StructureExportDiagnosticRow:
    """Output/export readiness diagnostic for one structure solid row."""

    diagnostic_id: str
    severity: str
    kind: str
    structure_id: str
    geometry_spec_id: str
    output_object_id: str
    message: str
    notes: str = ""


@dataclass(frozen=True)
class StructureSolidSegmentRow:
    """Output-only segment geometry row for one structure solid station span."""

    segment_id: str
    parent_output_object_id: str
    structure_id: str
    geometry_spec_id: str
    segment_index: int
    station_start: float
    station_end: float
    start_x: float
    start_y: float
    start_z: float
    end_x: float
    end_y: float
    end_z: float
    start_tangent_direction_deg: float = 0.0
    end_tangent_direction_deg: float = 0.0
    path_source: str = ""
    width: float = 0.0
    height: float = 0.0
    length: float = 0.0
    volume: float = 0.0
    region_ref: str = ""
    assembly_ref: str = ""
    structure_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class StructureSolidOutputRow:
    """Normalized corridor structure solid or envelope output row."""

    output_object_id: str
    structure_id: str
    geometry_spec_id: str
    solid_kind: str
    station_start: float
    station_end: float
    path_source: str = ""
    material: str = ""
    width: float = 0.0
    height: float = 0.0
    length: float = 0.0
    volume: float = 0.0
    placement_x: float = 0.0
    placement_y: float = 0.0
    placement_z: float = 0.0
    tangent_direction_deg: float = 0.0
    start_x: float = 0.0
    start_y: float = 0.0
    start_z: float = 0.0
    end_x: float = 0.0
    end_y: float = 0.0
    end_z: float = 0.0
    start_tangent_direction_deg: float = 0.0
    end_tangent_direction_deg: float = 0.0
    region_ref: str = ""
    assembly_ref: str = ""
    structure_ref: str = ""
    source_ref: str = ""
    notes: str = ""


@dataclass
class StructureSolidOutput(OutputModelBase):
    """Normalized structure solid output payload derived from StructureModel."""

    structure_solid_output_id: str = ""
    corridor_id: str = ""
    structure_model_id: str = ""
    applied_section_set_ref: str = ""
    solid_rows: list[StructureSolidOutputRow] = field(default_factory=list)
    solid_segment_rows: list[StructureSolidSegmentRow] = field(default_factory=list)
    diagnostic_rows: list[StructureExportDiagnosticRow] = field(default_factory=list)
