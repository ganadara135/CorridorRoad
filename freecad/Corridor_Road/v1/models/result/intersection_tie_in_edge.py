"""Intersection tie-in edge result contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionTieInEdgeRow:
    """One road edge candidate that an intersection patch can connect to."""

    tie_in_edge_id: str
    intersection_id: str
    alignment_ref: str
    region_ref: str = ""
    side: str = ""
    edge_role: str = "pavement_edge"
    station_start: float = 0.0
    station_end: float = 0.0
    section_start_ref: str = ""
    section_end_ref: str = ""
    start_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    end_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    status: str = "candidate"
    notes: str = ""


@dataclass
class IntersectionTieInEdgeResult(ResultModelBase):
    """Rebuildable result contract for intersection patch tie-in edge candidates."""

    tie_in_edge_result_id: str = "intersection-tie-in-edges:build-parametric"
    intersection_id: str = ""
    boundary_mode: str = "tie_in_edges"
    status: str = "not_evaluated"
    edge_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    edge_rows: list[IntersectionTieInEdgeRow] = field(default_factory=list)
