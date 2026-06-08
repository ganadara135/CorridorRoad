"""Intersection edge-network result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionEdgeNetworkRow:
    """One deterministic intersection edge row before surface-zone generation."""

    edge_id: str
    intersection_id: str
    edge_role: str
    edge_family: str = "leg_edge"
    source_policy_ref: str = ""
    leg_ref: str = ""
    leg_role: str = ""
    alignment_ref: str = ""
    control_area_ref: str = ""
    side: str = ""
    station_start: float = 0.0
    station_end: float = 0.0
    radius: float = 0.0
    contact_station_refs: dict[str, tuple[float, ...]] = field(default_factory=dict)
    start_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    end_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    status: str = "candidate"
    notes: str = ""


@dataclass
class IntersectionEdgeNetworkResult(ResultModelBase):
    """Source-driven edge-network handoff before intersection surface zones."""

    edge_network_result_id: str = "intersection-edge-network:main"
    intersection_id: str = ""
    intersection_kind: str = ""
    status: str = "not_evaluated"
    leg_edge_count: int = 0
    curb_return_edge_count: int = 0
    daylight_edge_count: int = 0
    edge_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    edge_rows: list[IntersectionEdgeNetworkRow] = field(default_factory=list)
