"""Surface result model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class SurfaceRow:
    """Minimal engineering surface row."""

    surface_id: str
    surface_kind: str
    tin_ref: str
    status: str = "ready"
    parent_surface_ref: str = ""


@dataclass(frozen=True)
class SurfaceBuildRelation:
    """Minimal provenance relationship for a derived surface."""

    build_relation_id: str
    surface_ref: str
    relation_kind: str
    input_refs: list[str] = field(default_factory=list)
    operation_summary: str = ""


@dataclass(frozen=True)
class SurfaceComparisonRow:
    """Minimal surface comparison row."""

    comparison_id: str
    base_surface_ref: str
    compare_surface_ref: str
    comparison_kind: str
    result_surface_ref: str = ""


@dataclass(frozen=True)
class SurfaceSpanRow:
    """Station span metadata for a derived surface family."""

    span_id: str
    surface_ref: str
    station_start: float
    station_end: float
    from_region_ref: str = ""
    to_region_ref: str = ""
    span_kind: str = "same_region"
    transition_ref: str = ""
    continuity_status: str = "ok"
    diagnostic_refs: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class SurfaceModel(ResultModelBase):
    """Grouped engineering surface result family."""

    surface_model_id: str = ""
    corridor_id: str = ""
    surface_rows: list[SurfaceRow] = field(default_factory=list)
    build_relation_rows: list[SurfaceBuildRelation] = field(default_factory=list)
    comparison_rows: list[SurfaceComparisonRow] = field(default_factory=list)
    span_rows: list[SurfaceSpanRow] = field(default_factory=list)
