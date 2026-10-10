"""TIN edit source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...common.diagnostics import DiagnosticMessage


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
