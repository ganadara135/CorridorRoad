"""Diagnostics helpers for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiagnosticMessage:
    """Minimal diagnostic payload used by v1 placeholders."""

    severity: str
    kind: str
    message: str
    notes: str = ""


@dataclass
class DiagnosticBag:
    """Mutable collection used while building or validating v1 models."""

    rows: list[DiagnosticMessage] = field(default_factory=list)

    def add(
        self,
        *,
        severity: str,
        kind: str,
        message: str,
        notes: str = "",
    ) -> None:
        self.rows.append(
            DiagnosticMessage(
                severity=severity,
                kind=kind,
                message=message,
                notes=notes,
            )
        )
