"""Drainage pipeline result model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class DrainagePipelineSegment:
    """Physical pipe/channel segment resolved from Drainage Flow Routes."""

    pipeline_segment_id: str
    flow_route_ref: str
    from_element_ref: str = ""
    to_element_ref: str = ""
    from_connection_point_ref: str = ""
    to_connection_point_ref: str = ""
    station_start: float = 0.0
    station_end: float = 0.0
    from_offset: float = 0.0
    to_offset: float = 0.0
    invert_start: float | None = None
    invert_end: float | None = None
    diameter: float = 0.0
    shape_kind: str = ""
    status: str = "ready"
    notes: str = ""


@dataclass
class DrainagePipelineResult(ResultModelBase):
    """Evaluated Drainage pipeline result family."""

    drainage_pipeline_result_id: str = ""
    drainage_model_id: str = ""
    structure_model_id: str = ""
    segment_rows: list[DrainagePipelineSegment] = field(default_factory=list)
