"""Structure source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase

# Culverts and the structures around them (inlet, outlet, headwall, manhole, junction box) are
# modelled in Drainage since 2026-11-08: a pipe is a Drainage link and a culvert point's barrel is
# the pipe of its link. A Structure of these kinds is no longer supported; documents saved before
# lose such rows when the Structure is next applied.
REMOVED_DRAINAGE_STRUCTURE_KINDS = frozenset({"culvert", "inlet", "outlet", "headwall", "manhole", "junction_box"})
REMOVED_DRAINAGE_NATIVE_TYPES = frozenset({"box_culvert", "pipe_culvert", "inlet", "outlet", "headwall"})


def is_removed_drainage_structure(row) -> bool:
    """True for a Structure row of a kind or native type that now belongs to Drainage."""

    kind = str(getattr(row, "structure_kind", "") or "").strip().lower()
    native_type = str(getattr(row, "native_type", "") or "").strip().lower()
    return kind in REMOVED_DRAINAGE_STRUCTURE_KINDS or native_type in REMOVED_DRAINAGE_NATIVE_TYPES


@dataclass(frozen=True)
class StructurePlacement:
    """Minimal station-aware structure placement."""

    placement_id: str
    alignment_id: str
    station_start: float
    station_end: float
    offset: float = 0.0
    elevation_reference: str = ""
    orientation_mode: str = "alignment"
    region_ref: str = ""


@dataclass(frozen=True)
class StructureRow:
    """Minimal corridor-related structure row."""

    structure_id: str
    structure_kind: str
    structure_role: str
    placement: StructurePlacement
    geometry_spec_ref: str = ""
    geometry_ref: str = ""
    reference_mode: str = "native"
    geometry_source_mode: str = "native"
    native_type: str = ""


@dataclass(frozen=True)
class StructureGeometrySpec:
    """Normalized source dimensions for one v1 structure geometry spec."""

    geometry_spec_id: str
    structure_ref: str
    shape_kind: str = ""
    width: float = 0.0
    height: float = 0.0
    length_mode: str = "station_range"
    skew_angle_deg: float = 0.0
    vertical_position_mode: str = "profile_frame"
    base_elevation: float | None = None
    top_elevation: float | None = None
    material: str = ""
    style_role: str = ""
    notes: str = ""


@dataclass(frozen=True)
class BridgeGeometrySpec:
    """Bridge-specific source dimensions linked to a common geometry spec."""

    geometry_spec_ref: str
    deck_width: float = 0.0
    deck_thickness: float = 0.0
    girder_depth: float = 0.0
    barrier_height: float = 0.0
    clearance_height: float = 0.0
    abutment_start_offset: float = 0.0
    abutment_end_offset: float = 0.0
    pier_station_refs: list[str] = field(default_factory=list)
    approach_slab_length: float = 0.0
    bearing_elevation_mode: str = ""


@dataclass(frozen=True)
class RetainingWallGeometrySpec:
    """Retaining-wall-specific body and side source dimensions."""

    geometry_spec_ref: str
    wall_height: float = 0.0
    wall_thickness: float = 0.0
    footing_width: float = 0.0
    footing_thickness: float = 0.0
    retained_side: str = ""
    top_elevation_mode: str = ""
    bottom_elevation_mode: str = ""
    batter_slope: float = 0.0
    coping_height: float = 0.0
    drainage_layer_ref: str = ""


@dataclass
class StructureModel(SourceModelBase):
    """Durable structure source contract."""

    structure_model_id: str = ""
    alignment_id: str = ""
    structure_rows: list[StructureRow] = field(default_factory=list)
    geometry_spec_rows: list[StructureGeometrySpec] = field(default_factory=list)
    bridge_geometry_spec_rows: list[BridgeGeometrySpec] = field(default_factory=list)
    retaining_wall_geometry_spec_rows: list[RetainingWallGeometrySpec] = field(default_factory=list)
