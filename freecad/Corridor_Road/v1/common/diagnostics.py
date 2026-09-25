"""Diagnostics helpers for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiagnosticMessage:
    """Minimal diagnostic payload used by v1 placeholders."""

    severity: str
    kind: str
    message: str
    notes: str = ""
