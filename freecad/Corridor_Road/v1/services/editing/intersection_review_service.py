"""UI-independent review of Intersection source rows before they can build geometry.

An Intersection preset writes its rows as `draft`, with each leg's `profile_ref`
and `centerline3d_ref` empty, and nothing downstream fills them. Until they are
reviewed the junction evaluates against an incomplete source, so the review is a
real authoring step rather than a formality.

Like the rest of `services/editing`, nothing here reads a FreeCAD document or
builds a widget. A caller that can read the document resolves the refs and passes
them in, and persistence stays an explicit command step afterwards.

A row is accepted only when every field it needs is present. Inventing a ref that
names nothing would make the source look reviewed while leaving the same gap, so
an incomplete row keeps its draft status and says what it still needs.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ...models.source.intersection_model import IntersectionModel


LEG_REQUIRED_FIELDS = ("alignment_ref", "profile_ref", "centerline3d_ref")
ANCHOR_DEFAULT_TOLERANCE = 0.01

# Accepting a row resolves the markers that say nobody has reviewed it, and only
# those. A preset leaves two families behind: review state, `leg_approval_pending`,
# `control_area_approval_pending`, `preset_anchor_review_required`, and provenance,
# `leg_source_region_derived`, `control_area_region_derived`. Review state stops
# being true once a user accepts the row; provenance stays true forever, and it is
# what the edge-authority filter and the audit trail read afterwards. The T
# slope-face smoke clears `diagnostic_rows` outright, which drops provenance too.
REVIEW_STATE_DIAGNOSTIC_TOKENS = ("approval_pending", "review_required")


@dataclass(frozen=True)
class IntersectionReviewRow:
    """One source row a user must review, and what it still lacks."""

    kind: str
    row_id: str
    intersection_id: str
    approval_status: str
    missing_fields: tuple[str, ...] = ()
    notes: str = ""

    @property
    def reviewed(self) -> bool:
        return self.approval_status == "accepted" and not self.missing_fields


@dataclass(frozen=True)
class PreparedIntersectionReview:
    """Non-mutating result at the review Apply boundary."""

    model: IntersectionModel
    accepted_row_ids: tuple[str, ...] = ()
    incomplete_row_ids: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return not any(row.startswith("error|") for row in self.diagnostics)


@dataclass(frozen=True)
class IntersectionPresetDefaultRow:
    """One value the preset decided, where it landed, and whether it can be reviewed."""

    label: str
    value: str
    carrier: str
    review_state: str
    reviewable: bool = True
    notes: str = ""


def intersection_preset_default_rows(model: IntersectionModel | None) -> list[IntersectionPresetDefaultRow]:
    """Return the preset-decided values as a checklist, with the review state of each.

    The panel already shows what the combos and spins will send. This reports the
    other half: what ended up in the document and which row family carries it, so the
    review step has a checklist rather than a note.

    Two of the five carry no review state at all. `IntersectionCurbReturnPolicyRow`
    and `IntersectionArmPolicyRow` are the only two of the eleven row families without
    `approval_status` or `diagnostic_rows`, and the curb return radius and the design
    vehicle land on exactly those. They are reported as not reviewable rather than
    quietly shown as reviewed.
    """

    if model is None:
        return []
    rows: list[IntersectionPresetDefaultRow] = []

    arm_rows = list(getattr(model, "arm_policy_rows", []) or [])
    vehicles = sorted({_text(getattr(row, "design_vehicle_ref", "")) for row in arm_rows} - {""})
    rows.append(
        IntersectionPresetDefaultRow(
            label="Design vehicle",
            value=", ".join(vehicles) or "(not set)",
            carrier="arm_policy_rows",
            review_state="no review state on this row family",
            reviewable=False,
            notes="IntersectionArmPolicyRow has no approval_status or diagnostic_rows.",
        )
    )

    curb_rows = list(getattr(model, "curb_return_policy_rows", []) or [])
    radii = sorted({_float(getattr(row, "radius", 0.0)) for row in curb_rows} - {0.0})
    rows.append(
        IntersectionPresetDefaultRow(
            label="Curb return radius",
            value=", ".join("%.3f m" % value for value in radii) or "(not set)",
            carrier="curb_return_policy_rows",
            review_state="no review state on this row family",
            reviewable=False,
            notes="IntersectionCurbReturnPolicyRow has no approval_status or diagnostic_rows.",
        )
    )

    area_rows = list(getattr(model, "control_area_rows", []) or [])
    spans = []
    for row in area_rows:
        for start, end in list(getattr(row, "station_ranges", []) or []):
            spans.append(abs(_float(end) - _float(start)))
    rows.append(
        IntersectionPresetDefaultRow(
            label="Control length",
            value=", ".join("%.3f m" % span for span in spans) or "(no station ranges)",
            carrier="control_area_rows",
            review_state=_family_review_state(area_rows),
        )
    )

    grading_rows = list(getattr(model, "grading_policy_rows", []) or [])
    rows.append(
        IntersectionPresetDefaultRow(
            label="Grading policy",
            value=", ".join(
                sorted({_text(getattr(row, "crown_behavior", "")) for row in grading_rows} - {""})
            )
            or "(not set)",
            carrier="grading_policy_rows",
            review_state=_family_review_state(grading_rows),
        )
    )

    drainage_rows = list(getattr(model, "drainage_policy_rows", []) or [])
    rows.append(
        IntersectionPresetDefaultRow(
            label="Drainage mode",
            value=", ".join(
                sorted({_text(getattr(row, "capture_mode", "")) for row in drainage_rows} - {""})
            )
            or "(not set)",
            carrier="drainage_policy_rows",
            review_state=_family_review_state(drainage_rows),
        )
    )
    return rows


def _family_review_state(rows) -> str:
    """Summarise the review state of a row family that carries one."""

    rows = list(rows or [])
    if not rows:
        return "no rows"
    pending = [
        row
        for row in rows
        if _text(getattr(row, "approval_status", "")) != "accepted"
        or any(
            token in str(value).lower()
            for value in list(getattr(row, "diagnostic_rows", []) or [])
            for token in REVIEW_STATE_DIAGNOSTIC_TOKENS
        )
    ]
    if not pending:
        return "reviewed"
    return "review required (%d of %d row(s))" % (len(pending), len(rows))


def intersection_review_rows(model: IntersectionModel | None) -> list[IntersectionReviewRow]:
    """Return every leg, anchor and control area row with its review state."""

    if model is None:
        return []
    rows: list[IntersectionReviewRow] = []
    for intersection in list(getattr(model, "intersection_rows", []) or []):
        intersection_id = _text(getattr(intersection, "intersection_id", ""))
        for leg in list(getattr(intersection, "leg_rows", []) or []):
            missing = tuple(name for name in LEG_REQUIRED_FIELDS if not _text(getattr(leg, name, "")))
            rows.append(
                IntersectionReviewRow(
                    kind="leg",
                    row_id=_text(getattr(leg, "leg_id", "")),
                    intersection_id=intersection_id,
                    approval_status=_text(getattr(leg, "approval_status", "")),
                    missing_fields=missing,
                    notes=_text(getattr(leg, "leg_role", "")),
                )
            )
    for anchor in list(getattr(model, "anchor_rows", []) or []):
        missing = () if _float(getattr(anchor, "tolerance", 0.0)) > 0.0 else ("tolerance",)
        rows.append(
            IntersectionReviewRow(
                kind="anchor",
                row_id=_text(getattr(anchor, "anchor_id", "")),
                intersection_id=_text(getattr(anchor, "intersection_id", "")),
                approval_status=_text(getattr(anchor, "approval_status", "")),
                missing_fields=missing,
                notes=_text(getattr(anchor, "source_method", "")),
            )
        )
    for area in list(getattr(model, "control_area_rows", []) or []):
        missing = () if list(getattr(area, "station_ranges", []) or []) else ("station_ranges",)
        rows.append(
            IntersectionReviewRow(
                kind="control_area",
                row_id=_text(getattr(area, "control_area_id", "")),
                intersection_id=_text(getattr(area, "intersection_id", "")),
                approval_status=_text(getattr(area, "approval_status", "")),
                missing_fields=missing,
                notes=_text(getattr(area, "intent_status", "")),
            )
        )
    return rows


def apply_intersection_review(
    model: IntersectionModel | None,
    *,
    leg_refs: dict[str, dict[str, str]] | None = None,
    anchor_tolerance: float | None = None,
) -> PreparedIntersectionReview:
    """Accept the rows that are complete, filling leg refs the caller resolved.

    `leg_refs` maps a leg id to the refs found in the document, for example
    ``{"intersection:t:leg:01": {"profile_ref": "profile:V1Profile",
    "centerline3d_ref": "centerline3d:multiple"}}``. A ref already on the row is
    kept; the caller's value only fills a blank.
    """

    if model is None:
        return PreparedIntersectionReview(
            model=IntersectionModel(schema_version=1, project_id=""),
            diagnostics=("error|intersection_review_model_missing",),
        )

    refs = dict(leg_refs or {})
    accepted: list[str] = []
    incomplete: list[str] = []
    diagnostics: list[str] = []

    intersection_rows = []
    for intersection in list(getattr(model, "intersection_rows", []) or []):
        legs = []
        for leg in list(getattr(intersection, "leg_rows", []) or []):
            leg_id = _text(getattr(leg, "leg_id", ""))
            supplied = dict(refs.get(leg_id, {}) or {})
            profile_ref = _text(getattr(leg, "profile_ref", "")) or _text(supplied.get("profile_ref", ""))
            centerline_ref = _text(getattr(leg, "centerline3d_ref", "")) or _text(supplied.get("centerline3d_ref", ""))
            candidate = replace(leg, profile_ref=profile_ref, centerline3d_ref=centerline_ref)
            missing = tuple(name for name in LEG_REQUIRED_FIELDS if not _text(getattr(candidate, name, "")))
            if missing:
                incomplete.append(leg_id)
                diagnostics.append("warning|leg_review_incomplete:%s:%s" % (leg_id, ",".join(missing)))
                legs.append(candidate)
                continue
            accepted.append(leg_id)
            legs.append(
                replace(
                    candidate,
                    approval_status="accepted",
                    span_source="explicit",
                    diagnostic_rows=_resolved_review_diagnostics(candidate),
                )
            )
        intersection_rows.append(replace(intersection, leg_rows=legs))

    anchor_rows = []
    for anchor in list(getattr(model, "anchor_rows", []) or []):
        anchor_id = _text(getattr(anchor, "anchor_id", ""))
        tolerance = _float(getattr(anchor, "tolerance", 0.0))
        if tolerance <= 0.0:
            tolerance = _float(anchor_tolerance) if anchor_tolerance is not None else ANCHOR_DEFAULT_TOLERANCE
        accepted.append(anchor_id)
        anchor_rows.append(
            replace(
                anchor,
                approval_status="accepted",
                tolerance=tolerance,
                diagnostic_rows=_resolved_review_diagnostics(anchor),
            )
        )

    control_area_rows = []
    for area in list(getattr(model, "control_area_rows", []) or []):
        area_id = _text(getattr(area, "control_area_id", ""))
        if not list(getattr(area, "station_ranges", []) or []):
            incomplete.append(area_id)
            diagnostics.append("warning|control_area_review_incomplete:%s:station_ranges" % area_id)
            control_area_rows.append(area)
            continue
        accepted.append(area_id)
        control_area_rows.append(
            replace(
                area,
                approval_status="accepted",
                intent_status="intersection_owned",
                diagnostic_rows=_resolved_review_diagnostics(area),
            )
        )

    reviewed = replace(
        model,
        intersection_rows=intersection_rows,
        anchor_rows=anchor_rows,
        control_area_rows=control_area_rows,
    )
    return PreparedIntersectionReview(
        model=reviewed,
        accepted_row_ids=tuple(accepted),
        incomplete_row_ids=tuple(incomplete),
        diagnostics=tuple(diagnostics),
    )


def intersection_review_summary(rows: list[IntersectionReviewRow]) -> str:
    """Return a one-line count for a panel header."""

    total = len(rows)
    if not total:
        return "No Intersection source rows to review."
    reviewed = sum(1 for row in rows if row.reviewed)
    blocked = sum(1 for row in rows if row.missing_fields)
    return "%d of %d row(s) reviewed; %d still missing source fields." % (reviewed, total, blocked)


def _resolved_review_diagnostics(row) -> list[str]:
    """Return the row's diagnostics without the markers acceptance resolves."""

    return [
        str(value)
        for value in list(getattr(row, "diagnostic_rows", []) or [])
        if not any(token in str(value).lower() for token in REVIEW_STATE_DIAGNOSTIC_TOKENS)
    ]


def _text(value) -> str:
    return str(value or "").strip()


def _float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
