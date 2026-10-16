"""Result freshness: is a stored result still built from the current inputs?

Each result stage records, when it is built, one content fingerprint per input it consumed
(`input key -> fingerprint`). Freshness compares that record with the fingerprints of the inputs
as they are now. A stage is also stale when a stage it consumes is stale, because rebuilding the
upstream stage will change what this one reads. These rules read no document and write nothing.
"""

from __future__ import annotations

from dataclasses import dataclass


STATIONING = "stationing"
CENTERLINE3D = "centerline3d"
APPLIED_SECTIONS = "applied_sections"
BUILD_PARAMETRIC = "build_parametric"
# Workflow order. The 3D Centerline stage is its review object; Applied Sections evaluate their own
# centerline, so both consume Stations directly (GR-4 makes the 3D Centerline their shared input).
RESULT_STAGES = (STATIONING, CENTERLINE3D, APPLIED_SECTIONS, BUILD_PARAMETRIC)
STAGE_LABELS = {
    STATIONING: "Stations",
    CENTERLINE3D: "3D Centerline",
    APPLIED_SECTIONS: "Applied Sections",
    BUILD_PARAMETRIC: "Build Parametric",
}
# The stage each stage consumes directly.
UPSTREAM_STAGE = {CENTERLINE3D: STATIONING, APPLIED_SECTIONS: STATIONING, BUILD_PARAMETRIC: APPLIED_SECTIONS}

CURRENT = "current"
STALE = "stale"
MISSING = "missing"
# A result built before inputs were recorded cannot be compared; Rebuild Downstream rebuilds it.
NOT_RECORDED = "not recorded"


@dataclass(frozen=True)
class StageFreshness:
    """Freshness of one stage. `changed_inputs` names the input keys that differ from the record,
    including those of a stale upstream stage."""

    stage: str
    status: str
    object_names: tuple[str, ...] = ()
    changed_inputs: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return STAGE_LABELS.get(self.stage, self.stage)


def changed_input_keys(recorded: dict[str, str] | None, current: dict[str, str]) -> tuple[str, ...]:
    """Input keys whose fingerprint differs, or that were added or removed since the record."""

    if recorded is None:
        return (NOT_RECORDED,)
    keys = sorted(set(recorded) | set(current))
    return tuple(key for key in keys if recorded.get(key) != current.get(key))


def stage_freshness(
    stage: str,
    *,
    object_names: tuple[str, ...],
    recorded: dict[str, str] | None,
    current: dict[str, str],
    upstream: StageFreshness | None = None,
) -> StageFreshness:
    """Freshness of one stage result from its record, its current inputs and its upstream stage."""

    if not object_names:
        return StageFreshness(stage=stage, status=MISSING)
    changed = list(changed_input_keys(recorded, current))
    if upstream is not None and upstream.status == STALE:
        changed.extend(key for key in upstream.changed_inputs if key not in changed)
    return StageFreshness(
        stage=stage,
        status=STALE if changed else CURRENT,
        object_names=tuple(object_names),
        changed_inputs=tuple(changed),
    )


def merge_stage_rows(stage: str, rows: list[StageFreshness]) -> StageFreshness:
    """One row for a stage held by several objects, such as one Stationing per road."""

    present = [row for row in rows if row.status != MISSING]
    if not present:
        return StageFreshness(stage=stage, status=MISSING)
    changed: list[str] = []
    for row in present:
        changed.extend(key for key in row.changed_inputs if key not in changed)
    return StageFreshness(
        stage=stage,
        status=STALE if any(row.status == STALE for row in present) else CURRENT,
        object_names=tuple(name for row in present for name in row.object_names),
        changed_inputs=tuple(changed),
    )


def stale_stages(rows: list[StageFreshness]) -> tuple[str, ...]:
    return tuple(row.stage for row in rows if row.status == STALE)


def freshness_text(rows: list[StageFreshness]) -> str:
    """One line per stage, for the panels' summaries."""

    lines = []
    for row in rows:
        if row.status == STALE:
            lines.append(f"{row.label}: stale ({', '.join(row.changed_inputs)})")
        else:
            lines.append(f"{row.label}: {row.status}")
    if stale_stages(rows):
        lines.append("Run Rebuild Downstream to rebuild the stale results.")
    return "\n".join(lines)


__all__ = [
    "APPLIED_SECTIONS",
    "BUILD_PARAMETRIC",
    "CENTERLINE3D",
    "CURRENT",
    "MISSING",
    "NOT_RECORDED",
    "RESULT_STAGES",
    "STAGE_LABELS",
    "STALE",
    "STATIONING",
    "StageFreshness",
    "UPSTREAM_STAGE",
    "changed_input_keys",
    "freshness_text",
    "merge_stage_rows",
    "stage_freshness",
    "stale_stages",
]
