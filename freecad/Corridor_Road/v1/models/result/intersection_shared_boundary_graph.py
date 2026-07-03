"""Canonical intersection shared-boundary graph result contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionSharedBoundaryNodeRow:
    """One canonical node used by shared intersection boundary edges."""

    node_id: str
    intersection_id: str
    node_role: str
    x: float
    y: float
    z: float
    source_refs: tuple[str, ...] = ()
    source_status: str = "accepted"
    diagnostics: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class IntersectionSharedBoundaryEdgeRow:
    """One canonical boundary edge consumed by adjacent intersection surfaces."""

    edge_id: str
    intersection_id: str
    edge_role: str
    from_node_ref: str
    to_node_ref: str
    point_refs: tuple[str, ...] = ()
    consumer_refs: tuple[str, ...] = ()
    left_owner: str = ""
    right_owner: str = ""
    source_refs: tuple[str, ...] = ()
    source_status: str = "accepted"
    diagnostics: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class IntersectionSharedBoundaryCellRow:
    """One graph-closed ownership cell around an intersection."""

    cell_id: str
    intersection_id: str
    cell_role: str
    boundary_edge_refs: tuple[str, ...] = ()
    loop_points_xyz: tuple[tuple[float, float, float], ...] = ()
    owner_surface_ref: str = ""
    adjacent_surface_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    closed: bool = False
    self_crossing: bool = False
    status: str = "candidate"
    diagnostics: tuple[str, ...] = ()
    notes: str = ""


@dataclass
class IntersectionSharedBoundaryGraphResult(ResultModelBase):
    """Canonical shared-boundary topology for intersection surface consumers."""

    graph_result_id: str = "intersection-shared-boundary-graph:main"
    intersection_id: str = ""
    intersection_kind: str = ""
    status: str = "not_evaluated"
    node_count: int = 0
    edge_count: int = 0
    cell_count: int = 0
    ready_edge_count: int = 0
    ready_cell_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    duplicate_edge_count: int = 0
    missing_consumer_count: int = 0
    not_snapped_count: int = 0
    graph_open_cell_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    node_rows: list[IntersectionSharedBoundaryNodeRow] = field(default_factory=list)
    edge_rows: list[IntersectionSharedBoundaryEdgeRow] = field(default_factory=list)
    cell_rows: list[IntersectionSharedBoundaryCellRow] = field(default_factory=list)
