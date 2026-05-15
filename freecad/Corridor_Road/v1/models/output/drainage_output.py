"""Drainage review output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class DrainageElementOutputRow:
    """Minimal drainage output row."""

    row_id: str
    kind: str
    station_start: float
    station_end: float
    label: str = ""
    source_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class DrainageSummaryRow:
    """Minimal drainage summary row."""

    summary_id: str
    kind: str
    label: str
    value: float | str
    unit: str = ""


@dataclass(frozen=True)
class DrainagePipelineSegmentOutputRow:
    """Normalized output row for a resolved Drainage pipeline segment."""

    pipeline_segment_id: str
    flow_route_ref: str
    station_start: float
    station_end: float
    from_element_ref: str = ""
    to_element_ref: str = ""
    from_connection_point_ref: str = ""
    to_connection_point_ref: str = ""
    from_offset: float = 0.0
    to_offset: float = 0.0
    invert_start: float | None = None
    invert_end: float | None = None
    diameter: float = 0.0
    shape_kind: str = ""
    status: str = "ready"
    notes: str = ""


@dataclass(frozen=True)
class DrainagePipelineGeometryOutputRow:
    """Output geometry row derived from a resolved Drainage pipeline segment."""

    geometry_row_id: str
    pipeline_segment_id: str
    flow_route_ref: str
    geometry_kind: str = "centerline_polyline"
    coordinate_mode: str = "station_offset_fallback"
    centerline_points: list[tuple[float, float, float]] = field(default_factory=list)
    diameter: float = 0.0
    shape_kind: str = ""
    status: str = "ready"
    notes: str = ""


@dataclass(frozen=True)
class DrainagePipelineSolidOutputRow:
    """Output metadata row for a first-slice Drainage pipeline pipe solid."""

    solid_row_id: str
    pipeline_segment_id: str
    flow_route_ref: str
    solid_kind: str = "pipe_solid_candidate"
    station_start: float = 0.0
    station_end: float = 0.0
    length: float = 0.0
    diameter: float = 0.0
    volume: float = 0.0
    cap_count: int = 0
    is_capped: bool = False
    coordinate_mode: str = "station_offset_fallback"
    geometry_row_ref: str = ""
    status: str = "ready"
    notes: str = ""


@dataclass(frozen=True)
class DrainagePipelineNetworkOutputRow:
    """Output metadata row for a grouped Drainage pipeline network candidate."""

    network_row_id: str
    network_id: str
    pipeline_segment_refs: list[str] = field(default_factory=list)
    flow_route_refs: list[str] = field(default_factory=list)
    solid_row_refs: list[str] = field(default_factory=list)
    segment_count: int = 0
    junction_count: int = 0
    length: float = 0.0
    volume: float = 0.0
    coordinate_mode: str = "station_offset_fallback"
    validation_status: str = "ready"
    notes: str = ""


@dataclass(frozen=True)
class DrainagePipelineJunctionOutputRow:
    """Output row for a Drainage pipeline network endpoint junction."""

    junction_row_id: str
    network_ref: str
    junction_kind: str = "terminal"
    degree: int = 1
    point: tuple[float, float, float] = (0.0, 0.0, 0.0)
    pipeline_segment_refs: list[str] = field(default_factory=list)
    flow_route_refs: list[str] = field(default_factory=list)
    coordinate_mode: str = "station_offset_fallback"
    status: str = "ready"
    notes: str = ""


@dataclass
class DrainageOutput(OutputModelBase):
    """Normalized drainage review payload."""

    drainage_output_id: str = ""
    alignment_id: str = ""
    drainage_model_id: str = ""
    element_rows: list[DrainageElementOutputRow] = field(default_factory=list)
    pipeline_segment_rows: list[DrainagePipelineSegmentOutputRow] = field(default_factory=list)
    pipeline_geometry_rows: list[DrainagePipelineGeometryOutputRow] = field(default_factory=list)
    pipeline_solid_rows: list[DrainagePipelineSolidOutputRow] = field(default_factory=list)
    pipeline_network_rows: list[DrainagePipelineNetworkOutputRow] = field(default_factory=list)
    pipeline_junction_rows: list[DrainagePipelineJunctionOutputRow] = field(default_factory=list)
    summary_rows: list[DrainageSummaryRow] = field(default_factory=list)
