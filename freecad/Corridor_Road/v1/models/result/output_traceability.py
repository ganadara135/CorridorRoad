"""Typed validation result for normalized output ownership."""

from __future__ import annotations

from dataclasses import dataclass

from ...common.diagnostics import DiagnosticMessage


@dataclass(frozen=True)
class OutputTraceabilityResult:
    """Read-only audit of one output contract's source and result owners."""

    schema_version: int = 1
    output_type: str = ""
    output_ref: str = ""
    owner_requirement: str = "source_or_result"
    source_refs: tuple[str, ...] = ()
    result_refs: tuple[str, ...] = ()
    status: str = "error"
    diagnostic_rows: tuple[DiagnosticMessage, ...] = ()


__all__ = ["OutputTraceabilityResult"]
