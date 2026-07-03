"""Intersection surface patch result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionSurfacePatchBoundaryRow:
    """Normalized boundary contract for one intersection surface patch."""

    boundary_id: str
    intersection_id: str
    boundary_source: str = ""
    boundary_mode: str = ""
    patch_boundary_result_ref: str = ""
    point_count: int = 0
    source_segment_count: int = 0
    ring_count: int = 0
    hole_ring_count: int = 0
    island_ring_count: int = 0
    closed: bool = False
    self_crossing: bool = False
    polygon_area: float = 0.0
    bbox_x: float = 0.0
    bbox_y: float = 0.0
    bbox_aspect_ratio: float = 0.0
    status: str = "candidate"
    diagnostic_rows: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class IntersectionSurfacePatchTriangulationRow:
    """Normalized triangulation contract for one intersection surface patch."""

    triangulation_id: str
    intersection_id: str
    triangulation_method: str = ""
    boundary_strategy: str = ""
    triangle_count: int = 0
    degenerate_triangle_count: int = 0
    structured_strip_count: int = 0
    curb_return_surface_edge_count: int = 0
    curb_return_arc_count: int = 0
    curb_return_arc_sample_count: int = 0
    curb_return_arc_segment_count: int = 0
    edge_blend_face_count: int = 0
    boundary_role_summary: str = ""
    pavement_tie_in_edge_count: int = 0
    stem_tie_in_edge_count: int = 0
    overlap_cut_edge_count: int = 0
    curb_return_edge_count: int = 0
    status: str = "candidate"
    diagnostic_rows: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class IntersectionSurfacePatchQualityRow:
    """Normalized quality contract for one intersection surface patch."""

    quality_id: str
    intersection_id: str
    min_triangle_quality: float = 0.0
    skinny_triangle_count: int = 0
    max_boundary_edge_length: float = 0.0
    long_boundary_edge_count: int = 0
    long_boundary_edge_factor: float = 0.0
    long_boundary_edge_limit: float = 0.0
    max_boundary_edge_length_policy: float = 0.0
    status: str = "candidate"
    diagnostic_rows: tuple[str, ...] = ()
    notes: str = ""


@dataclass
class IntersectionSurfacePatchResult(ResultModelBase):
    """Output contract for a generated intersection surface patch."""

    surface_patch_result_id: str = "intersection-surface-patch:build-parametric"
    intersection_id: str = ""
    status: str = "not_evaluated"
    output_path: str = "legacy_output"
    output_contract_status: str = "transitional_normalized"
    digital_twin_handoff: str = "review_required"
    transitional_reason: str = "legacy_patch_surface_output"
    replacement_path: str = "accepted_intersection_surface_zone_output"
    patch_surface_ref: str = ""
    patch_boundary_result_ref: str = ""
    consumed_contract_refs: list[str] = field(default_factory=list)
    diagnostic_rows: list[str] = field(default_factory=list)
    boundary_rows: list[IntersectionSurfacePatchBoundaryRow] = field(default_factory=list)
    triangulation_rows: list[IntersectionSurfacePatchTriangulationRow] = field(default_factory=list)
    quality_rows: list[IntersectionSurfacePatchQualityRow] = field(default_factory=list)
