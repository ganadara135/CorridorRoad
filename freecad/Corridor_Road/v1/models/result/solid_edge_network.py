"""Solid edge-network result contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


SOLID_FACE_KINDS = {
    "top",
    "bottom",
    "left_side",
    "right_side",
    "start_cap",
    "end_cap",
    "transition",
}


@dataclass(frozen=True)
class SolidTopologyEdgeRow:
    """Canonical topology edge used by generated solid faces."""

    edge_id: str
    start_node_id: str
    end_node_id: str
    edge_kind: str = "profile"
    station_start: float = 0.0
    station_end: float = 0.0
    usage_count: int = 0
    face_refs: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SolidFaceRow:
    """Topology-first face row for watertight shell validation."""

    face_id: str
    target_id: str
    face_kind: str
    node_ids: list[str] = field(default_factory=list)
    edge_ids: list[str] = field(default_factory=list)
    station_start: float = 0.0
    station_end: float = 0.0
    source_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        kind = str(self.face_kind or "").strip().lower()
        object.__setattr__(self, "face_kind", kind if kind in SOLID_FACE_KINDS else "transition")


@dataclass
class SolidEdgeNetwork(ResultModelBase):
    """Validated topology network generated from closed solid profiles."""

    edge_network_id: str = ""
    target_ref: str = ""
    profile_set_ref: str = ""
    station_start: float = 0.0
    station_end: float = 0.0
    validation_status: str = "not_checked"
    is_shell_closed: bool = False
    face_count: int = 0
    edge_count: int = 0
    profile_count: int = 0
    edge_rows: list[SolidTopologyEdgeRow] = field(default_factory=list)
    face_rows: list[SolidFaceRow] = field(default_factory=list)
