"""Region source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import SourceModelBase


@dataclass(frozen=True)
class RegionDiagnosticRow:
    """Validation or resolution diagnostic row for Region workflows."""

    diagnostic_id: str
    severity: str
    kind: str
    source_ref: str = ""
    message: str = ""
    notes: str = ""


@dataclass(frozen=True)
class RegionPolicyRow:
    """Minimal region policy row."""

    policy_id: str
    component_scope: str
    parameter: str
    value: float | str
    unit: str = ""
    policy_kind: str = "parameter_override"


@dataclass(frozen=True)
class RegionTransition:
    """Minimal region transition row."""

    transition_id: str
    from_region_id: str
    to_region_id: str
    station_start: float
    station_end: float
    transition_kind: str = "linear_blend"


@dataclass(frozen=True)
class RegionPolicySet:
    """Named region-level policy bundle."""

    policy_set_id: str
    template_ref: str = ""
    assembly_ref: str = ""
    component_policy_rows: list[RegionPolicyRow] = field(default_factory=list)
    daylight_policy: dict[str, Any] = field(default_factory=dict)
    drainage_policy: dict[str, Any] = field(default_factory=dict)
    structure_policy: dict[str, Any] = field(default_factory=dict)
    ramp_policy: dict[str, Any] = field(default_factory=dict)
    intersection_policy: dict[str, Any] = field(default_factory=dict)
    earthwork_policy: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True)
class RegionRow:
    """Station-bounded region policy row."""

    region_id: str
    station_start: float
    station_end: float
    region_index: int = 0
    assembly_ref: str = ""
    structure_ref: str = ""
    structure_refs: list[str] = field(default_factory=list)
    drainage_refs: list[str] = field(default_factory=list)
    ramp_ref: str = ""
    intersection_ref: str = ""
    policy_set_ref: str = ""
    template_ref: str = ""
    superelevation_ref: str = ""
    override_refs: list[str] = field(default_factory=list)
    priority: int = 0
    source_ref: str = ""
    notes: str = ""
    policy_rows: list[RegionPolicyRow] = field(default_factory=list)

    def __post_init__(self) -> None:
        structure_ref = str(self.structure_ref or "").strip()
        structure_refs = normalize_region_refs(self.structure_refs)
        if structure_ref and structure_ref not in structure_refs:
            structure_refs = [structure_ref] + structure_refs
        if not structure_ref and structure_refs:
            structure_ref = structure_refs[0]
        object.__setattr__(self, "structure_ref", structure_ref)
        object.__setattr__(self, "structure_refs", structure_refs)
        object.__setattr__(self, "drainage_refs", normalize_region_refs(self.drainage_refs))
        object.__setattr__(self, "override_refs", normalize_region_refs(self.override_refs))


@dataclass
class RegionModel(SourceModelBase):
    """Durable region source contract."""

    region_model_id: str = ""
    alignment_id: str = ""
    region_rows: list[RegionRow] = field(default_factory=list)
    policy_sets: list[RegionPolicySet] = field(default_factory=list)
    transition_rows: list[RegionTransition] = field(default_factory=list)
    constraint_rows: list[dict[str, Any]] = field(default_factory=list)
    diagnostic_rows: list[RegionDiagnosticRow] = field(default_factory=list)


def normalize_region_refs(values: list[object] | tuple[object, ...] | str) -> list[str]:
    """Normalize a list-like region reference field."""

    if isinstance(values, str):
        raw_values = values.replace(";", ",").split(",")
    else:
        raw_values = list(values or [])
    output: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output
