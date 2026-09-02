"""Typed result contracts for deterministic incremental stage rebuilds."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class IncrementalStageRecord:
    """Accepted metadata for one rebuildable engineering result stage."""

    schema_version: int = 1
    stage_name: str = ""
    service_version: str = ""
    input_fingerprint: str = ""
    result_fingerprint: str = ""
    consumed_source_refs: tuple[str, ...] = ()
    consumed_result_refs: tuple[str, ...] = ()
    accepted: bool = False
    duration_ms: float = 0.0
    changed_stages: tuple[str, ...] = ()
    stale_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class IncrementalBuildDecision:
    """Decision made before a stage builder mutates accepted output."""

    stage_name: str
    input_fingerprint: str
    rebuild_required: bool
    reuse_previous: bool
    stale_reasons: tuple[str, ...] = ()
    changed_stages: tuple[str, ...] = ()


@dataclass(frozen=True)
class IncrementalBuildExecution:
    """Successful stage execution or reuse outcome."""

    result: object
    record: IncrementalStageRecord
    decision: IncrementalBuildDecision
    diagnostics: tuple[str, ...] = field(default_factory=tuple)


__all__ = ["IncrementalBuildDecision", "IncrementalBuildExecution", "IncrementalStageRecord"]
