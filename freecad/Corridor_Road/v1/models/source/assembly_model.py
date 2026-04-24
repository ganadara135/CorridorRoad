"""Assembly source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


@dataclass(frozen=True)
class TemplateComponent:
    """Minimal reusable section component definition."""

    component_id: str
    kind: str
    parameters: dict[str, object] = field(default_factory=dict)
    enabled: bool = True


@dataclass(frozen=True)
class SectionTemplate:
    """Minimal section template definition."""

    template_id: str
    template_kind: str
    component_rows: list[TemplateComponent] = field(default_factory=list)


@dataclass
class AssemblyModel(SourceModelBase):
    """Durable assembly and section-template source contract."""

    assembly_id: str = ""
    template_rows: list[SectionTemplate] = field(default_factory=list)
