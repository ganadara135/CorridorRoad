"""Resolved region context result models for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RegionContextReviewItem:
    """Small viewer-facing row derived from a resolved Region context."""

    row_id: str
    kind: str
    label: str
    value: str
    source_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class RegionContextSummary:
    """Station-specific Region handoff contract for downstream services."""

    station: float
    region_id: str = ""
    primary_kind: str = ""
    applied_layers: list[str] = field(default_factory=list)
    assembly_ref: str = ""
    template_ref: str = ""
    policy_set_ref: str = ""
    superelevation_ref: str = ""
    structure_ref: str = ""
    structure_refs: list[str] = field(default_factory=list)
    drainage_refs: list[str] = field(default_factory=list)
    ramp_ref: str = ""
    intersection_ref: str = ""
    override_refs: list[str] = field(default_factory=list)
    overlap_region_ids: list[str] = field(default_factory=list)
    diagnostic_kinds: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def summary_text(self) -> str:
        """Human-readable one-line summary for reviewers."""

        if not self.region_id:
            return f"STA {self.station:.3f}: no active region"
        layers = ",".join(self.applied_layers) if self.applied_layers else "none"
        refs = []
        if self.assembly_ref:
            refs.append(f"assembly={self.assembly_ref}")
        structure_ref = self.structure_ref or (self.structure_refs[0] if self.structure_refs else "")
        if structure_ref:
            refs.append(f"structure={structure_ref}")
        if self.drainage_refs:
            refs.append(f"drainage={','.join(self.drainage_refs)}")
        ref_text = f" | {'; '.join(refs)}" if refs else ""
        return f"STA {self.station:.3f}: {self.primary_kind} [{layers}]{ref_text}"

    def to_review_items(self) -> list[RegionContextReviewItem]:
        """Return stable viewer rows without exposing UI state."""

        source_ref = self.region_id
        return [
            RegionContextReviewItem(
                row_id="region:primary_kind",
                kind="region",
                label="Primary Kind",
                value=self.primary_kind,
                source_ref=source_ref,
            ),
            RegionContextReviewItem(
                row_id="region:layers",
                kind="region",
                label="Applied Layers",
                value=", ".join(self.applied_layers),
                source_ref=source_ref,
            ),
            RegionContextReviewItem(
                row_id="region:assembly",
                kind="assembly",
                label="Assembly",
                value=self.assembly_ref,
                source_ref=source_ref,
            ),
            RegionContextReviewItem(
                row_id="region:structures",
                kind="structure",
                label="Structure",
                value=self.structure_ref or (self.structure_refs[0] if self.structure_refs else ""),
                source_ref=source_ref,
            ),
            RegionContextReviewItem(
                row_id="region:drainage",
                kind="drainage",
                label="Drainage",
                value=", ".join(self.drainage_refs),
                source_ref=source_ref,
            ),
            RegionContextReviewItem(
                row_id="region:overlaps",
                kind="diagnostic",
                label="Overlaps",
                value=", ".join(self.overlap_region_ids),
                source_ref=source_ref,
            ),
        ]
