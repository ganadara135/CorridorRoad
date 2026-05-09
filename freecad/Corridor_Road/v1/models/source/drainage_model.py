"""Drainage source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


@dataclass(frozen=True)
class DrainagePolicySet:
    """Minimal drainage policy row."""

    policy_set_id: str
    flow_intent: str
    min_grade_rule: float | str = ""
    low_point_rule: str = ""
    collection_rule: str = ""
    discharge_rule: str = ""
    earthwork_priority: str = ""


@dataclass(frozen=True)
class DrainageFlowRoute:
    """Minimal drainage flow route row."""

    flow_route_id: str
    from_element_ref: str = ""
    to_element_ref: str = ""
    outlet_ref: str = ""
    direction: str = ""
    risk_level: str = ""
    notes: str = ""


@dataclass(frozen=True)
class DrainageElementRow:
    """Minimal drainage element row."""

    drainage_element_id: str
    element_kind: str
    alignment_ref: str = ""
    ramp_ref: str = ""
    intersection_ref: str = ""
    structure_ref: str = ""
    side: str = ""
    region_ref: str = ""
    assembly_component_ref: str = ""
    station_start: float = 0.0
    station_end: float = 0.0
    policy_set_ref: str = ""


@dataclass
class DrainageModel(SourceModelBase):
    """Durable drainage source contract."""

    drainage_model_id: str = ""
    element_rows: list[DrainageElementRow] = field(default_factory=list)
    policy_rows: list[DrainagePolicySet] = field(default_factory=list)
    flow_route_rows: list[DrainageFlowRoute] = field(default_factory=list)
