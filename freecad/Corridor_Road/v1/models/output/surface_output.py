"""Surface output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class SurfaceRowOutput:
    """Minimal surface family row for surface output."""

    surface_row_id: str
    surface_id: str
    surface_kind: str
    tin_ref: str
    status: str = "ready"
    parent_surface_ref: str = ""


@dataclass(frozen=True)
class SurfaceBoundaryRow:
    """Minimal boundary row for surface output."""

    boundary_row_id: str
    surface_ref: str
    boundary_kind: str
    vertex_refs: list[str] = field(default_factory=list)
    closed: bool = True


@dataclass(frozen=True)
class SurfaceComparisonOutputRow:
    """Minimal comparison row for surface output."""

    comparison_row_id: str
    comparison_id: str
    comparison_kind: str
    base_surface_ref: str
    compare_surface_ref: str
    result_surface_ref: str = ""


@dataclass(frozen=True)
class SurfaceSummaryRow:
    """Minimal summary row for surface output."""

    summary_id: str
    kind: str
    label: str
    value: float | str
    unit: str = ""


@dataclass
class SurfaceOutput(OutputModelBase):
    """Normalized surface output payload."""

    surface_output_id: str = ""
    corridor_id: str = ""
    surface_rows: list[SurfaceRowOutput] = field(default_factory=list)
    boundary_rows: list[SurfaceBoundaryRow] = field(default_factory=list)
    comparison_rows: list[SurfaceComparisonOutputRow] = field(default_factory=list)
    summary_rows: list[SurfaceSummaryRow] = field(default_factory=list)
