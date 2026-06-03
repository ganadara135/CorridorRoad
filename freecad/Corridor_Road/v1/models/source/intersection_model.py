"""Intersection source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


INTERSECTION_KIND_PRESETS: dict[str, dict[str, object]] = {
    "t_intersection": {
        "label": "T Intersection",
        "default_leg_roles": ("primary_before", "primary_after", "side_approach"),
        "minimum_alignment_count": 2,
    },
    "cross_intersection": {
        "label": "Cross Intersection",
        "default_leg_roles": ("primary_before", "primary_after", "secondary_before", "secondary_after"),
        "minimum_alignment_count": 2,
    },
    "y_intersection": {
        "label": "Y Intersection",
        "default_leg_roles": ("primary_approach", "left_branch", "right_branch"),
        "minimum_alignment_count": 2,
    },
}


@dataclass(frozen=True)
class IntersectionLegRow:
    """Minimal participating-leg row for one junction."""

    leg_id: str
    leg_role: str
    alignment_ref: str
    intersection_id: str = ""
    profile_ref: str = ""
    centerline3d_ref: str = ""
    region_ref: str = ""
    approach_station_start: float = 0.0
    approach_station_end: float = 0.0
    priority: int = 0
    notes: str = ""


@dataclass(frozen=True)
class IntersectionControlArea:
    """Minimal control-area row for one intersection."""

    control_area_id: str
    intersection_id: str
    alignment_ref: str = ""
    station_ranges: list[tuple[float, float]] = field(default_factory=list)
    influence_ranges: list[tuple[float, float]] = field(default_factory=list)
    control_region_refs: list[str] = field(default_factory=list)
    turn_lane_policy_ref: str = ""
    curb_return_policy_ref: str = ""
    grading_policy_ref: str = ""
    drainage_policy_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class IntersectionRow:
    """Minimal at-grade intersection definition row."""

    intersection_id: str
    intersection_kind: str
    intersection_index: int = 0
    primary_alignment_ref: str = ""
    secondary_alignment_refs: list[str] = field(default_factory=list)
    intersection_point_x: float = 0.0
    intersection_point_y: float = 0.0
    intersection_point_z: float = 0.0
    primary_station: float = 0.0
    secondary_station_refs: dict[str, float] = field(default_factory=dict)
    control_region_refs: list[str] = field(default_factory=list)
    leg_rows: list[IntersectionLegRow] = field(default_factory=list)
    control_area_ref: str = ""
    grading_policy_ref: str = ""
    drainage_ref: str = ""
    design_criteria_ref: str = ""
    source_mode: str = "use_existing_alignments"
    policy_refs: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def is_supported_kind(self) -> bool:
        """Return whether this row uses a first-slice supported intersection type."""

        return self.intersection_kind in INTERSECTION_KIND_PRESETS


@dataclass
class IntersectionModel(SourceModelBase):
    """Durable at-grade junction source contract."""

    intersection_model_id: str = ""
    intersection_rows: list[IntersectionRow] = field(default_factory=list)
    control_area_rows: list[IntersectionControlArea] = field(default_factory=list)


def intersection_preset_labels() -> list[str]:
    """Return user-facing labels for the first intersection type presets."""

    return [str(row["label"]) for row in INTERSECTION_KIND_PRESETS.values()]


def intersection_kind_from_label(label: str) -> str:
    """Resolve a user-facing preset label to an internal intersection kind."""

    normalized = str(label or "").strip().lower()
    for kind, preset in INTERSECTION_KIND_PRESETS.items():
        if normalized == str(preset.get("label", "") or "").strip().lower():
            return kind
    return ""


def intersection_row_from_kind(
    *,
    intersection_id: str,
    intersection_kind: str,
    primary_alignment_ref: str = "",
    secondary_alignment_refs: list[str] | None = None,
    control_region_refs: list[str] | None = None,
) -> IntersectionRow:
    """Create a first-slice intersection row from a supported kind preset."""

    kind = str(intersection_kind or "").strip()
    preset = INTERSECTION_KIND_PRESETS.get(kind)
    if preset is None:
        raise ValueError(f"Unsupported intersection kind: {intersection_kind}")

    secondaries = list(secondary_alignment_refs or [])
    roles = tuple(preset.get("default_leg_roles", ()) or ())
    leg_rows: list[IntersectionLegRow] = []
    for index, role in enumerate(roles):
        if str(role).startswith("primary"):
            alignment_ref = primary_alignment_ref
        else:
            alignment_ref = secondaries[0] if secondaries else ""
        leg_rows.append(
            IntersectionLegRow(
                leg_id=f"{intersection_id}:leg-{index + 1:02d}",
                intersection_id=intersection_id,
                leg_role=str(role),
                alignment_ref=alignment_ref,
                priority=index + 1,
            )
        )

    return IntersectionRow(
        intersection_id=intersection_id,
        intersection_kind=kind,
        primary_alignment_ref=primary_alignment_ref,
        secondary_alignment_refs=secondaries,
        control_region_refs=list(control_region_refs or []),
        leg_rows=leg_rows,
        control_area_ref=f"{intersection_id}:control-area",
    )
