"""Shared output-model base classes for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...common.coordinates import CoordinateContext
from ...common.diagnostics import DiagnosticMessage
from ...common.units import UnitContext


@dataclass
class OutputModelBase:
    """Common base for normalized output payloads."""

    schema_version: int
    project_id: str
    label: str = ""
    unit_context: UnitContext = field(default_factory=UnitContext)
    coordinate_context: CoordinateContext = field(default_factory=CoordinateContext)
    selection_scope: dict[str, object] = field(default_factory=dict)
    source_refs: list[str] = field(default_factory=list)
    result_refs: list[str] = field(default_factory=list)
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)

