"""Evaluated side-slope bench profile result contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...common.diagnostics import DiagnosticMessage


@dataclass(frozen=True)
class BenchProfileSegment:
    """One evaluated side-slope or bench segment."""

    kind: str
    width: float
    slope: float

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "width": self.width, "slope": self.slope}


@dataclass(frozen=True)
class SubassemblyBenchProfileResult:
    """Typed result contract for a side-slope bench profile evaluation."""

    segment_rows: tuple[BenchProfileSegment, ...] = field(default_factory=tuple)
    diagnostic_rows: tuple[DiagnosticMessage, ...] = field(default_factory=tuple)

    @property
    def status(self) -> str:
        if any(row.severity == "error" for row in self.diagnostic_rows):
            return "error"
        if any(row.severity == "warning" for row in self.diagnostic_rows):
            return "warning"
        return "ok"

    def to_dict_rows(self) -> list[dict[str, object]]:
        return [row.to_dict() for row in self.segment_rows]
