"""Context review output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class ContextReviewRow:
    """Minimal review-context row for ramp, junction, or drainage state."""

    row_id: str
    kind: str
    label: str
    value: float | str
    source_ref: str = ""
    notes: str = ""


@dataclass
class ContextReviewOutput(OutputModelBase):
    """Normalized review-context payload."""

    context_review_output_id: str = ""
    alignment_id: str = ""
    station: float = 0.0
    ramp_rows: list[ContextReviewRow] = field(default_factory=list)
    intersection_rows: list[ContextReviewRow] = field(default_factory=list)
    drainage_rows: list[ContextReviewRow] = field(default_factory=list)
