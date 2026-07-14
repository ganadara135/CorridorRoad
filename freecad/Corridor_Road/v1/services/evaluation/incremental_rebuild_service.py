"""Fingerprint and rebuild decisions for v1 engineering result stages."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from time import perf_counter
from typing import Callable, Mapping

from ...models.persistence import fingerprint_for
from ...models.result.incremental_rebuild import (
    IncrementalBuildDecision,
    IncrementalBuildExecution,
    IncrementalStageRecord,
)


PRESENTATION_ONLY_FIELDS = frozenset(
    {
        "display_mode",
        "line_color",
        "line_width",
        "point_color",
        "shape_color",
        "style",
        "style_role",
        "transparency",
        "visibility",
        "visible",
    }
)


class IncrementalRebuildService:
    """Decide reuse before building and commit metadata only after success."""

    def __init__(self, *, clock: Callable[[], float] = perf_counter) -> None:
        self._clock = clock

    def engineering_fingerprint(
        self,
        value: object,
        *,
        ignored_fields: frozenset[str] = PRESENTATION_ONLY_FIELDS,
    ) -> str:
        return fingerprint_for(_engineering_value(value, ignored_fields=ignored_fields))

    def decide(
        self,
        *,
        stage_name: str,
        service_version: str,
        engineering_input: object,
        previous_record: IncrementalStageRecord | None = None,
        dependency_changed_stages: tuple[str, ...] = (),
    ) -> IncrementalBuildDecision:
        stage = str(stage_name or "").strip()
        if not stage:
            raise ValueError("stage_name is required.")
        input_fingerprint = self.engineering_fingerprint(engineering_input)
        reasons: list[str] = []
        if previous_record is None:
            reasons.append("no_previous_accepted_result")
        elif not previous_record.accepted:
            reasons.append("previous_result_not_accepted")
        else:
            if previous_record.stage_name != stage:
                reasons.append("stage_name_changed")
            if previous_record.service_version != str(service_version or ""):
                reasons.append("service_version_changed")
            if previous_record.input_fingerprint != input_fingerprint:
                reasons.append("engineering_input_changed")
        changed = _unique_text(dependency_changed_stages)
        if changed:
            reasons.append("dependency_result_changed")
        rebuild = bool(reasons)
        return IncrementalBuildDecision(
            stage_name=stage,
            input_fingerprint=input_fingerprint,
            rebuild_required=rebuild,
            reuse_previous=not rebuild,
            stale_reasons=tuple(reasons),
            changed_stages=changed,
        )

    def execute(
        self,
        *,
        decision: IncrementalBuildDecision,
        service_version: str,
        builder: Callable[[], object],
        previous_result: object | None = None,
        previous_record: IncrementalStageRecord | None = None,
        consumed_source_refs: tuple[str, ...] = (),
        consumed_result_refs: tuple[str, ...] = (),
    ) -> IncrementalBuildExecution:
        if decision.reuse_previous:
            if previous_record is None or previous_result is None:
                raise ValueError("Reuse requires both the previous accepted result and its record.")
            return IncrementalBuildExecution(
                result=previous_result,
                record=previous_record,
                decision=decision,
                diagnostics=("accepted_result_reused",),
            )

        started = self._clock()
        result = builder()
        duration_ms = max(0.0, (self._clock() - started) * 1000.0)
        record = IncrementalStageRecord(
            stage_name=decision.stage_name,
            service_version=str(service_version or ""),
            input_fingerprint=decision.input_fingerprint,
            result_fingerprint=self.engineering_fingerprint(result),
            consumed_source_refs=_unique_text(consumed_source_refs),
            consumed_result_refs=_unique_text(consumed_result_refs),
            accepted=True,
            duration_ms=duration_ms,
            changed_stages=decision.changed_stages + (decision.stage_name,),
            stale_reasons=decision.stale_reasons,
        )
        return IncrementalBuildExecution(result=result, record=record, decision=decision)


def _engineering_value(value: object, *, ignored_fields: frozenset[str]) -> object:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Mapping):
        return {
            str(key): _engineering_value(item, ignored_fields=ignored_fields)
            for key, item in value.items()
            if str(key).lower() not in ignored_fields
        }
    if isinstance(value, (list, tuple)):
        return [_engineering_value(item, ignored_fields=ignored_fields) for item in value]
    return value


def _unique_text(values) -> tuple[str, ...]:
    result: list[str] = []
    for value in values or ():
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return tuple(result)


__all__ = ["IncrementalRebuildService", "PRESENTATION_ONLY_FIELDS"]
