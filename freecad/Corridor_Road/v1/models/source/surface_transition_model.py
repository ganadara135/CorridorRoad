"""Surface transition source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


SURFACE_TRANSITION_MODES = {
    "interpolate_matching_roles",
    "interpolate_width",
    "manual_required",
}

SURFACE_TRANSITION_SURFACE_KINDS = {
    "design_surface",
    "subgrade_surface",
    "daylight_surface",
}

SURFACE_TRANSITION_APPROVAL_STATUSES = {
    "draft",
    "active",
    "approved",
    "disabled",
}


@dataclass(frozen=True)
class SurfaceTransitionDiagnosticRow:
    """Validation diagnostic row for SurfaceTransition workflows."""

    diagnostic_id: str
    severity: str
    kind: str
    source_ref: str = ""
    message: str = ""
    notes: str = ""


@dataclass(frozen=True)
class SurfaceTransitionRange:
    """Station-bounded user intent for applying transition surface treatment."""

    transition_id: str
    station_start: float
    station_end: float
    from_region_ref: str = ""
    to_region_ref: str = ""
    target_surface_kinds: list[str] = field(default_factory=list)
    transition_mode: str = "interpolate_matching_roles"
    sample_interval: float = 5.0
    enabled: bool = True
    approval_status: str = "draft"
    source_ref: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "transition_mode", normalize_surface_transition_mode(self.transition_mode))
        object.__setattr__(self, "approval_status", normalize_surface_transition_approval_status(self.approval_status))
        object.__setattr__(self, "target_surface_kinds", normalize_surface_transition_surface_kinds(self.target_surface_kinds))
        object.__setattr__(self, "enabled", bool(self.enabled))


@dataclass
class SurfaceTransitionModel(SourceModelBase):
    """Durable source contract for Region-boundary transition surface intent."""

    transition_model_id: str = ""
    corridor_ref: str = ""
    transition_ranges: list[SurfaceTransitionRange] = field(default_factory=list)
    diagnostic_rows: list[SurfaceTransitionDiagnosticRow] = field(default_factory=list)


def normalize_surface_transition_mode(value: str) -> str:
    """Return a supported transition mode, defaulting to matching-role interpolation."""

    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return text if text in SURFACE_TRANSITION_MODES else "interpolate_matching_roles"


def normalize_surface_transition_approval_status(value: str) -> str:
    """Return a supported transition approval status."""

    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return text if text in SURFACE_TRANSITION_APPROVAL_STATUSES else "draft"


def normalize_surface_transition_surface_kinds(values: list[object] | tuple[object, ...] | str) -> list[str]:
    """Normalize target surface kind rows while preserving user order."""

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
        if text in SURFACE_TRANSITION_SURFACE_KINDS:
            output.append(text)
    if output:
        return output
    return ["design_surface", "subgrade_surface", "daylight_surface"]
