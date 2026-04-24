"""Shared result-model base classes for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...common.coordinates import CoordinateContext
from ...common.diagnostics import DiagnosticMessage
from ...common.units import UnitContext


@dataclass
class ResultModelBase:
    """Common base for rebuildable engineering result models."""

    schema_version: int
    project_id: str
    label: str = ""
    unit_context: UnitContext = field(default_factory=UnitContext)
    coordinate_context: CoordinateContext = field(default_factory=CoordinateContext)
    source_refs: list[str] = field(default_factory=list)
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)

