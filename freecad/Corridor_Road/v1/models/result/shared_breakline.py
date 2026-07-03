"""Shared boundary breakline result contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class SharedBreaklinePointRow:
    """One ordered point on a shared boundary breakline."""

    point_id: str
    breakline_ref: str
    sequence: int
    x: float
    y: float
    z: float
    station: float = 0.0
    offset: float = 0.0
    source_point_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class SharedBreaklineRow:
    """One shared contact edge consumed by two or more result/output objects."""

    breakline_id: str
    domain_kind: str
    domain_ref: str
    breakline_role: str
    source_contract_refs: tuple[str, ...] = ()
    consumer_refs: tuple[str, ...] = ()
    from_output_role: str = ""
    to_output_role: str = ""
    point_refs: tuple[str, ...] = ()
    station_start: float = 0.0
    station_end: float = 0.0
    alignment_ref: str = ""
    side: str = ""
    material_role: str = ""
    source_status: str = "candidate"
    diagnostic_rows: tuple[str, ...] = ()
    handoff_target: str = ""
    notes: str = ""


@dataclass
class SharedBreaklineResult(ResultModelBase):
    """Common result contract for boundary-sharing outputs."""

    breakline_result_id: str = "shared-breakline:main"
    domain_kind: str = ""
    domain_ref: str = ""
    status: str = "not_evaluated"
    breakline_count: int = 0
    ready_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    breakline_rows: list[SharedBreaklineRow] = field(default_factory=list)
    point_rows: list[SharedBreaklinePointRow] = field(default_factory=list)

