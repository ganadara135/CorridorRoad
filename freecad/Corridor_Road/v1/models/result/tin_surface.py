"""TIN surface result model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class TINVertex:
    """One vertex in a normalized TIN surface."""

    vertex_id: str
    x: float
    y: float
    z: float
    source_point_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class TINTriangle:
    """One triangular face in a normalized TIN surface."""

    triangle_id: str
    v1: str
    v2: str
    v3: str
    triangle_kind: str = "primary_triangle"
    quality_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class TINQualityRow:
    """Minimal quality row attached to a TIN surface."""

    quality_id: str
    kind: str
    value: float | str
    unit: str = ""
    notes: str = ""


@dataclass(frozen=True)
class TINProvenanceRow:
    """Minimal provenance row attached to a TIN surface."""

    provenance_id: str
    source_kind: str
    source_ref: str
    notes: str = ""


@dataclass
class TINSurface(ResultModelBase):
    """Rebuildable TIN surface result contract."""

    surface_id: str = ""
    surface_kind: str = "existing_ground_tin"
    vertex_rows: list[TINVertex] = field(default_factory=list)
    triangle_rows: list[TINTriangle] = field(default_factory=list)
    boundary_refs: list[str] = field(default_factory=list)
    void_refs: list[str] = field(default_factory=list)
    quality_rows: list[TINQualityRow] = field(default_factory=list)
    provenance_rows: list[TINProvenanceRow] = field(default_factory=list)

    def vertex_map(self) -> dict[str, TINVertex]:
        """Return vertices keyed by stable vertex id."""

        return {row.vertex_id: row for row in self.vertex_rows}
