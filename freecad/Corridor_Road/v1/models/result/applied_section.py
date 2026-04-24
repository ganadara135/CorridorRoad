"""Applied section result model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class AppliedSectionPoint:
    """Minimal point row inside an applied section."""

    point_id: str
    x: float
    y: float
    z: float
    point_role: str = "section_point"


@dataclass(frozen=True)
class AppliedSectionComponentRow:
    """Minimal semantic component row inside an applied section."""

    component_id: str
    kind: str
    source_template_id: str = ""
    region_id: str = ""
    override_ids: list[str] = field(default_factory=list)
    structure_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AppliedSectionQuantityFragment:
    """Minimal quantity fragment attached to one applied section."""

    fragment_id: str
    quantity_kind: str
    value: float
    unit: str
    component_id: str = ""


@dataclass
class AppliedSection(ResultModelBase):
    """Station-specific resolved section result."""

    applied_section_id: str = ""
    corridor_id: str = ""
    alignment_id: str = ""
    profile_id: str = ""
    station: float = 0.0
    template_id: str = ""
    region_id: str = ""
    point_rows: list[AppliedSectionPoint] = field(default_factory=list)
    component_rows: list[AppliedSectionComponentRow] = field(default_factory=list)
    quantity_rows: list[AppliedSectionQuantityFragment] = field(default_factory=list)
