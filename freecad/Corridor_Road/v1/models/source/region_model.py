"""Region source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import SourceModelBase


REGION_PRIMARY_KINDS = {
    "normal_road",
    "bridge",
    "culvert",
    "intersection",
    "ramp",
    "drainage",
    "transition",
    "structure_influence",
    "daylight_control",
    "temporary_candidate_region",
}

REGION_LEGACY_KIND_MAP = {
    "mainline_region": "normal_road",
    "transition_region": "transition",
    "structure_influence_region": "structure_influence",
    "daylight_control_region": "daylight_control",
}


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
    """Station-bounded region policy row.

    ``region_kind`` is retained as a compatibility alias for older v1 tests and
    early services. New code should use ``primary_kind``.
    """

    region_id: str
    station_start: float
    station_end: float
    primary_kind: str = "normal_road"
    applied_layers: list[str] = field(default_factory=list)
    region_index: int = 0
    assembly_ref: str = ""
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
    region_kind: str = ""
    policy_rows: list[RegionPolicyRow] = field(default_factory=list)

    def __post_init__(self) -> None:
        primary_kind = normalize_region_primary_kind(self.primary_kind or self.region_kind)
        object.__setattr__(self, "primary_kind", primary_kind)
        if not self.region_kind:
            object.__setattr__(self, "region_kind", primary_kind)
        object.__setattr__(self, "applied_layers", normalize_region_layers(self.applied_layers))
        object.__setattr__(self, "structure_refs", normalize_region_refs(self.structure_refs))
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


def normalize_region_primary_kind(value: str) -> str:
    """Return a supported primary kind, preserving unknown text as lower snake."""

    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    text = REGION_LEGACY_KIND_MAP.get(text, text)
    return text or "normal_road"


def normalize_region_layers(values: list[object] | tuple[object, ...] | str) -> list[str]:
    """Normalize applied layer names while preserving order."""

    if isinstance(values, str):
        raw_values = values.replace(";", ",").split(",")
    else:
        raw_values = list(values or [])
    output: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


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
