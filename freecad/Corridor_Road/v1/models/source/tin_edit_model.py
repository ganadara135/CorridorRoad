"""TIN edit source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...common.diagnostics import DiagnosticMessage
from .base import SourceModelBase


@dataclass(frozen=True)
class TINEditOperation:
    """One replayable edit operation applied to a TIN surface."""

    operation_id: str
    operation_kind: str
    target_surface_id: str = ""
    enabled: bool = True
    parameters: dict[str, Any] = field(default_factory=dict)
    source_ref: str = ""
    created_at: str = ""
    notes: str = ""
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)


@dataclass
class TINEditSet(SourceModelBase):
    """Durable ordered collection of TIN edit operations."""

    edit_set_id: str = ""
    target_surface_id: str = ""
    operation_rows: list[TINEditOperation] = field(default_factory=list)
