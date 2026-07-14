"""Typed shared-breakline audit results for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SharedBreaklineAdjacencyResult:
    """Solid-readiness topology summary for shared-breakline edges."""

    status: str
    node_count: int = 0
    edge_count: int = 0
    open_end_count: int = 0
    duplicate_edge_count: int = 0
    reversed_edge_count: int = 0
    non_manifold_node_count: int = 0
    notes: str = ""

    def to_legacy_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "open_end_count": self.open_end_count,
            "duplicate_edge_count": self.duplicate_edge_count,
            "reversed_edge_count": self.reversed_edge_count,
            "non_manifold_node_count": self.non_manifold_node_count,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SharedBreaklineAuditResult:
    """Normalized consumer, geometry, mesh, and solid-readiness audit result."""

    status: str
    missing_consumer_count: int = 0
    mismatch_count: int = 0
    geometry_match_count: int = 0
    geometry_mismatch_count: int = 0
    mesh_match_count: int = 0
    mesh_mismatch_count: int = 0
    reversed_edge_count: int = 0
    solid_readiness_status: str = ""
    solid_open_end_count: int = 0
    solid_duplicate_edge_count: int = 0
    solid_reversed_edge_count: int = 0
    solid_non_manifold_node_count: int = 0
    solid_readiness_notes: str = ""
    notes: str = ""
    source_result_ref: str = ""
    consumer_refs: tuple[str, ...] = ()

    def to_legacy_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "missing_consumer_count": self.missing_consumer_count,
            "mismatch_count": self.mismatch_count,
            "geometry_match_count": self.geometry_match_count,
            "geometry_mismatch_count": self.geometry_mismatch_count,
            "mesh_match_count": self.mesh_match_count,
            "mesh_mismatch_count": self.mesh_mismatch_count,
            "reversed_edge_count": self.reversed_edge_count,
            "solid_readiness_status": self.solid_readiness_status,
            "solid_open_end_count": self.solid_open_end_count,
            "solid_duplicate_edge_count": self.solid_duplicate_edge_count,
            "solid_reversed_edge_count": self.solid_reversed_edge_count,
            "solid_non_manifold_node_count": self.solid_non_manifold_node_count,
            "solid_readiness_notes": self.solid_readiness_notes,
            "notes": self.notes,
        }
