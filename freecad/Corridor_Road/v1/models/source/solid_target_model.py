"""Watertight solid target source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


SOLID_TARGET_FAMILIES = {
    "road_body_envelope",
    "region_body",
    "pavement_layer_body",
    "subbase_body",
    "shoulder_body",
    "lined_ditch_body",
    "structure_body",
}

SOLID_TARGET_SCOPE_KINDS = {
    "whole_corridor",
    "region",
    "station_range",
    "assembly_component",
    "structure",
    "drainage",
}

SOLID_TARGET_READINESS_STATUSES = {
    "available",
    "blocked",
    "planned",
}


@dataclass(frozen=True)
class SolidTargetDiagnosticRow:
    """Diagnostic row for watertight solid target discovery and readiness."""

    diagnostic_id: str
    severity: str
    kind: str
    source_ref: str = ""
    message: str = ""
    notes: str = ""


@dataclass(frozen=True)
class SolidTargetRow:
    """Source-level intent row for one watertight solid target."""

    target_id: str
    target_family: str
    scope_kind: str
    station_start: float = 0.0
    station_end: float = 0.0
    region_ref: str = ""
    assembly_ref: str = ""
    component_ref: str = ""
    structure_ref: str = ""
    drainage_ref: str = ""
    enabled: bool = False
    priority: int = 10
    material_ref: str = ""
    readiness_status: str = "planned"
    source_refs: list[str] = field(default_factory=list)
    diagnostic_refs: list[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_family", normalize_solid_target_family(self.target_family))
        object.__setattr__(self, "scope_kind", normalize_solid_target_scope_kind(self.scope_kind))
        object.__setattr__(self, "readiness_status", normalize_solid_target_readiness_status(self.readiness_status))
        object.__setattr__(self, "enabled", bool(self.enabled))
        object.__setattr__(self, "source_refs", _normalize_refs(self.source_refs))
        object.__setattr__(self, "diagnostic_refs", _normalize_refs(self.diagnostic_refs))


@dataclass
class SolidTargetModel(SourceModelBase):
    """Durable target contract for topology-first watertight solid generation."""

    solid_target_model_id: str = ""
    corridor_ref: str = ""
    target_rows: list[SolidTargetRow] = field(default_factory=list)
    target_diagnostic_rows: list[SolidTargetDiagnosticRow] = field(default_factory=list)


def normalize_solid_target_family(value: str) -> str:
    """Return a supported solid target family, defaulting to road envelope."""

    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return text if text in SOLID_TARGET_FAMILIES else "road_body_envelope"


def normalize_solid_target_scope_kind(value: str) -> str:
    """Return a supported target scope kind."""

    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return text if text in SOLID_TARGET_SCOPE_KINDS else "whole_corridor"


def normalize_solid_target_readiness_status(value: str) -> str:
    """Return a supported target readiness status."""

    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return text if text in SOLID_TARGET_READINESS_STATUSES else "planned"


def _normalize_refs(values: list[object] | tuple[object, ...] | str) -> list[str]:
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
