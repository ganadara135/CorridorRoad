"""Intersection source editor command for Parametric Road v1."""

from __future__ import annotations

from math import ceil, hypot, pi

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is unavailable in plain Python.
    App = None
try:
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCADGui is unavailable in plain Python.
    Gui = None
try:
    import Part
except Exception:  # pragma: no cover - Part is unavailable in plain Python.
    Part = None

from freecad.Corridor_Road.qt_compat import QtWidgets

from ..models.source.intersection_model import (
    INTERSECTION_KIND_PRESETS,
    IntersectionAnchorRow,
    IntersectionArmPolicyRow,
    IntersectionControlArea,
    IntersectionCornerRow,
    IntersectionCurbReturnPolicyRow,
    IntersectionDrainagePolicyRow,
    IntersectionGradingPolicyRow,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
    IntersectionSlopeFacePolicyRow,
)
from ..objects.obj_alignment import to_alignment_model
from ..objects.obj_intersection import INTERSECTION_SOURCE_LABEL
from ..objects.obj_alignment import V1AlignmentObject, ViewProviderV1Alignment
from ..objects.obj_profile import create_sample_v1_profile
from ..objects.obj_region import create_or_update_v1_region_model_object, to_region_model
from ..objects.obj_stationing import create_v1_stationing
from ..models.source.region_model import RegionModel, RegionRow
from ..services.evaluation.intersection_alignment_detection_service import AlignmentIntersectionDetectionService  # noqa: F401 - re-exported to the Presets panel
from ...objects.obj_project import find_project
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree


INTERSECTION_COMMAND_ID = "CorridorRoad_V1EditIntersections"
INTERSECTION_SOURCE_MODES = ("Use Existing Alignments", "Create Starter Sources")
NEXT_INTERSECTION_WORKFLOW_TEXT = (
    "Workflow: Regions -> Intersections -> Structures -> Drainage -> Build Sections"
)
INTERSECTION_REVIEW_MAX_REGION_SPAN = 48.0


def list_v1_alignment_choices(document) -> list[tuple[str, str]]:
    """Return selectable v1 Alignment choices as ``(alignment_id, label)`` rows."""

    choices: list[tuple[str, str]] = []
    if document is None:
        return choices
    seen: set[str] = set()
    for obj in list(getattr(document, "Objects", []) or []):
        model = to_alignment_model(obj)
        if model is None:
            continue
        alignment_id = str(getattr(model, "alignment_id", "") or "").strip()
        if not alignment_id or alignment_id in seen:
            continue
        seen.add(alignment_id)
        label = str(getattr(model, "label", "") or getattr(obj, "Label", "") or alignment_id)
        choices.append((alignment_id, label))
    return choices


def alignment_model_by_ref(document, alignment_ref: str):
    """Return one AlignmentModel by v1 Alignment id."""

    target = str(alignment_ref or "").strip()
    if document is None or not target:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        model = to_alignment_model(obj)
        if model is not None and str(getattr(model, "alignment_id", "") or "") == target:
            return model
    return None


def validate_existing_alignment_selection(primary_alignment_ref: str, secondary_alignment_ref: str) -> list[str]:
    """Return validation errors for Existing Alignments mode."""

    primary = str(primary_alignment_ref or "").strip()
    secondary = str(secondary_alignment_ref or "").strip()
    errors: list[str] = []
    if not primary:
        errors.append("Primary Alignment is required.")
    if not secondary:
        errors.append("Secondary Alignment is required.")
    if primary and secondary and primary == secondary:
        errors.append("Primary and Secondary Alignment must be different.")
    return errors


def intersection_ref_for_kind(intersection_kind: str) -> str:
    """Return the first-slice Intersection ref used by starter control Regions."""

    kind = str(intersection_kind or "").strip() or "intersection"
    return f"intersection:starter-{kind}"


def list_intersection_control_region_choices(document, intersection_ref: str = "") -> list[dict[str, object]]:
    """Return Region rows that are already tagged as intersection control Regions."""

    target_ref = str(intersection_ref or "").strip()
    choices: list[dict[str, object]] = []
    if document is None:
        return choices
    for obj in list(getattr(document, "Objects", []) or []):
        region_model = to_region_model(obj)
        if region_model is None:
            continue
        model_id = str(getattr(region_model, "region_model_id", "") or "")
        alignment_id = str(getattr(region_model, "alignment_id", "") or "")
        for row in list(getattr(region_model, "region_rows", []) or []):
            row_intersection_ref = str(getattr(row, "intersection_ref", "") or "").strip()
            if not row_intersection_ref:
                continue
            if target_ref and row_intersection_ref != target_ref:
                continue
            region_id = str(getattr(row, "region_id", "") or "")
            choices.append(
                {
                    "control_region_ref": _control_region_ref(model_id, region_id),
                    "region_model_ref": model_id,
                    "region_id": region_id,
                    "alignment_ref": alignment_id,
                    "intersection_ref": row_intersection_ref,
                    "station_start": float(getattr(row, "station_start", 0.0) or 0.0),
                    "station_end": float(getattr(row, "station_end", 0.0) or 0.0),
                    "label": (
                        f"{region_id} | {alignment_id or '-'} | "
                        f"STA {float(getattr(row, 'station_start', 0.0) or 0.0):.3f}-"
                        f"{float(getattr(row, 'station_end', 0.0) or 0.0):.3f}"
                    ),
                }
            )
    return sorted(
        choices,
        key=lambda row: (
            str(row.get("alignment_ref", "")),
            float(row.get("station_start", 0.0)),
            str(row.get("region_id", "")),
        ),
    )


def build_intersection_model_from_sources(
    *,
    intersection_kind: str,
    source_mode: str,
    primary_alignment_ref: str,
    secondary_alignment_ref: str,
    control_region_choices: list[dict[str, object]],
    detection_result=None,
    project_id: str = "corridorroad-v1",
) -> IntersectionModel:
    """Build a durable first-slice IntersectionModel from panel selections and Region refs."""

    kind = str(intersection_kind or "").strip()
    intersection_id = intersection_ref_for_kind(kind)
    control_refs = [str(row.get("control_region_ref", "") or "") for row in control_region_choices]
    control_refs = [ref for ref in control_refs if ref]
    primary_ref = str(primary_alignment_ref or "").strip()
    secondary_refs = _unique_text_values(
        [
            str(secondary_alignment_ref or "").strip(),
            *[
                str(row.get("alignment_ref", "") or "").strip()
                for row in list(control_region_choices or [])
                if str(row.get("alignment_ref", "") or "").strip()
                and str(row.get("alignment_ref", "") or "").strip() != primary_ref
            ],
        ]
    )
    primary_station = float(getattr(detection_result, "primary_station", 0.0) or 0.0) if detection_result is not None else 0.0
    secondary_station = float(getattr(detection_result, "secondary_station", 0.0) or 0.0) if detection_result is not None else 0.0
    x = float(getattr(detection_result, "x", 0.0) or 0.0) if detection_result is not None else 0.0
    y = float(getattr(detection_result, "y", 0.0) or 0.0) if detection_result is not None else 0.0
    anchor_row = IntersectionAnchorRow(
        anchor_id=f"anchor:{intersection_id}:main",
        intersection_id=intersection_id,
        source_method="detected" if detection_result is not None else "preset_default",
        approval_status="draft",
        primary_alignment_ref=primary_ref,
        primary_station=primary_station,
        secondary_station_refs={secondary_refs[0]: secondary_station} if secondary_refs else {},
        point_x=x,
        point_y=y,
        tolerance=0.0,
        diagnostic_rows=[] if detection_result is not None else ["anchor_source_defaulted"],
        notes="Intersection anchor source row created from panel inputs.",
        alignment_direction_refs={
            ref: (float(direction[0]), float(direction[1]))
            for ref, direction in (
                (primary_ref, tuple(getattr(detection_result, "primary_direction_xy", ()) or ())),
                (secondary_refs[0] if secondary_refs else "", tuple(getattr(detection_result, "secondary_direction_xy", ()) or ())),
            )
            if ref and len(direction) == 2
        },
    )
    control_area_rows = _control_area_rows_from_region_choices(intersection_id, control_region_choices)
    leg_rows = _leg_rows_from_region_choices(
        intersection_id,
        control_region_choices,
        intersection_kind=kind,
        primary_alignment_ref=primary_ref,
        secondary_alignment_refs=secondary_refs,
    )
    corner_rows = _default_corner_rows(intersection_id, kind, control_area_rows, leg_rows)
    arm_policy_rows = _default_arm_policy_rows(intersection_id, leg_rows)
    drainage_policy_row = _default_drainage_policy(intersection_id)
    row = IntersectionRow(
        intersection_id=intersection_id,
        intersection_kind=kind,
        intersection_index=1,
        primary_alignment_ref=primary_ref,
        secondary_alignment_refs=secondary_refs,
        intersection_point_x=x,
        intersection_point_y=y,
        primary_station=primary_station,
        secondary_station_refs={secondary_refs[0]: secondary_station} if secondary_refs else {},
        control_region_refs=control_refs,
        leg_rows=leg_rows,
        control_area_ref=f"{intersection_id}:control-area",
        grading_policy_ref=f"grading:{intersection_id}:default",
        policy_refs=[
            f"curb-return:{intersection_id}:default",
            f"grading:{intersection_id}:default",
            f"slope-face:{intersection_id}:default",
            drainage_policy_row.policy_id,
            *[row.policy_id for row in arm_policy_rows],
        ],
        source_mode=_source_mode_id(source_mode),
        notes="Created by Intersections panel control Region linking.",
    )
    return IntersectionModel(
        schema_version=1,
        project_id=project_id,
        label=INTERSECTION_SOURCE_LABEL,
        intersection_model_id="intersections:main",
        anchor_rows=[anchor_row],
        intersection_rows=[row],
        control_area_rows=control_area_rows,
        corner_rows=corner_rows,
        arm_policy_rows=arm_policy_rows,
        curb_return_policy_rows=[
            _default_curb_return_policy(
                intersection_id=intersection_id,
                intersection_kind=kind,
                leg_rows=leg_rows,
                corner_rows=corner_rows,
            )
        ],
        grading_policy_rows=[
            _default_grading_policy(
                intersection_id=intersection_id,
                primary_alignment_ref=primary_ref,
                secondary_alignment_refs=secondary_refs,
            )
        ],
        slope_face_policy_rows=[
            _default_slope_face_policy(intersection_id=intersection_id)
        ],
        drainage_policy_rows=[drainage_policy_row],
    )


# The kinds the Intersection panel offers. INTERSECTION_KIND_PRESETS in the source
# model is the single list: IntersectionRow.is_supported_kind reads it, and topology
# warns with intersection_kind_not_first_slice_supported for anything outside it.
# Skewed, Urban Curb/Gutter, Drainage Sag and Y starters were retired on 2026-09-26;
# they had never been in this list, so they always carried that warning.
SUPPORTED_INTERSECTION_KINDS = tuple(INTERSECTION_KIND_PRESETS)


def starter_intersection_source_specs(intersection_kind: str) -> dict[str, object]:
    """Return starter source geometry specs for one supported intersection kind."""

    kind = str(intersection_kind or "").strip()
    if kind == "t_intersection":
        return {
            "kind": kind,
            "alignments": [
                {"role": "primary", "label": "Intersection Main Road", "points": [(-120.0, 0.0), (120.0, 0.0)]},
                {"role": "secondary", "label": "Intersection Side Road", "points": [(0.0, -100.0), (0.0, 0.0)]},
            ],
        }
    if kind == "cross_intersection":
        return {
            "kind": kind,
            "alignments": [
                {"role": "primary", "label": "Cross Main Road", "points": [(-120.0, 0.0), (120.0, 0.0)]},
                {"role": "secondary", "label": "Cross Road", "points": [(0.0, -120.0), (0.0, 120.0)]},
            ],
        }
    if kind == "roundabout":
        return {
            "kind": kind,
            "alignments": [
                {"role": "primary", "label": "Roundabout North-South Road", "points": [(0.0, -130.0), (0.0, 130.0)]},
                {"role": "secondary", "label": "Roundabout East-West Road", "points": [(-130.0, 0.0), (130.0, 0.0)]},
            ],
        }
    supported = ", ".join(SUPPORTED_INTERSECTION_KINDS)
    raise ValueError(
        f"Unsupported starter intersection kind: {intersection_kind}. Supported kinds: {supported}."
    )


def create_starter_intersection_sources(document, intersection_kind: str, *, project=None) -> list[str]:
    """Create editable starter source objects for one intersection type."""

    if App is None:
        raise RuntimeError("FreeCAD is required to create starter intersection sources.")
    doc = document or getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available.")
    prj = project or find_project(doc)
    specs = starter_intersection_source_specs(intersection_kind)
    created: list[str] = []
    assembly_ref, template_ref = _ensure_starter_assembly_for_intersections(doc, project=prj, created=created)
    for index, alignment_spec in enumerate(list(specs.get("alignments", []) or []), start=1):
        role = str(alignment_spec.get("role", "") or f"road-{index}")
        label = str(alignment_spec.get("label", "") or f"Intersection Road {index}")
        points = [(float(x), float(y)) for x, y in list(alignment_spec.get("points", []) or [])]
        alignment_id = _unique_alignment_id(doc, f"alignment:intersection-{role}")
        alignment = _create_alignment_source_from_points(
            doc,
            label=label,
            alignment_id=alignment_id,
            points=points,
            project=prj,
        )
        created.append(f"Alignment: {alignment.Label} | {alignment.AlignmentId}")
        profile = create_sample_v1_profile(
            doc,
            project=prj,
            alignment=alignment,
            label=f"{label} FG Profile",
            create_alignment_if_missing=False,
        )
        _update_profile_to_alignment_length(
            profile,
            _polyline_length(points),
            profile_style=str(specs.get("profile_style", "") or ""),
        )
        created.append(f"Profile: {profile.Label} | {profile.ProfileId}")
        stationing = create_v1_stationing(
            doc,
            project=prj,
            alignment=alignment,
            interval=20.0,
            label=f"{label} Stations",
        )
        created.append(f"Stations: {stationing.Label} | {stationing.StationingId}")
        region = create_or_update_v1_region_model_object(
            doc,
            project=prj,
            region_model=_starter_region_model_for_alignment(
                alignment_id=str(getattr(alignment, "AlignmentId", "") or ""),
                intersection_kind=intersection_kind,
                role=role,
                length=_polyline_length(points),
                project_id=_project_id(prj),
                assembly_ref=assembly_ref,
                template_ref=template_ref,
            ),
            object_name=f"V1IntersectionRegionModel_{_safe_name(role)}",
            label=f"{label} Regions",
        )
        created.append(f"Regions: {region.Label} | {region.RegionModelId}")
    try:
        doc.recompute()
    except Exception:
        pass
    centerline_status = _create_starter_centerline3d_preview(doc, project=prj)
    if centerline_status:
        created.append(centerline_status)
    return created


def _create_starter_centerline3d_preview(document, *, project=None) -> str:
    try:
        from .cmd_centerline3d import build_document_centerline3d_result, show_v1_centerline3d_preview_object

        result = build_document_centerline3d_result(document)
        obj = show_v1_centerline3d_preview_object(
            document,
            result=result,
            project=project,
            show_station_markers=False,
            display_mode="smooth_curve",
        )
        alignment_count = len(
            {
                str(getattr(row, "source_alignment_ref", "") or "")
                for row in list(getattr(result, "point_rows", ()) or ())
                if str(getattr(row, "source_alignment_ref", "") or "")
            }
        )
        return (
            f"3D Centerline: {str(getattr(obj, 'Label', '') or getattr(obj, 'Name', '') or '3D Centerline')} "
            f"| {str(getattr(result, 'centerline3d_result_id', '') or 'centerline3d:main')} "
            f"| alignments={alignment_count} | points={int(getattr(result, 'point_count', 0) or 0)}"
        )
    except Exception as exc:
        return f"3D Centerline: not generated | {exc}"


def _populate_alignment_combo(combo, choices: list[tuple[str, str]]) -> None:
    combo.clear()
    combo.addItem("", "")
    for alignment_id, label in choices:
        combo.addItem(f"{label} | {alignment_id}", alignment_id)


def _combo_data_or_text(combo) -> str:
    try:
        data = combo.currentData()
        if data:
            return str(data)
    except Exception:
        pass
    text = str(combo.currentText() or "").strip()
    if "|" in text:
        text = text.rsplit("|", 1)[-1].strip()
    return text


def _format_detection_lines(result) -> list[str]:
    if result is None:
        return []
    return [
        f"- Status: {result.status}",
        f"- XY: {result.x:.3f}, {result.y:.3f}",
        f"- Primary STA: {result.primary_station:.3f}",
        f"- Secondary STA: {result.secondary_station:.3f}",
        f"- Distance: {result.distance:.3f}",
        f"- Notes: {result.notes}",
    ]


def _control_region_ref(region_model_ref: str, region_id: str) -> str:
    model_ref = str(region_model_ref or "").strip()
    row_ref = str(region_id or "").strip()
    if model_ref and row_ref:
        return f"{model_ref}/{row_ref}"
    return row_ref or model_ref


def _control_area_rows_from_region_choices(
    intersection_id: str,
    control_region_choices: list[dict[str, object]],
) -> list[IntersectionControlArea]:
    by_alignment: dict[str, list[dict[str, object]]] = {}
    for row in control_region_choices:
        alignment_ref = str(row.get("alignment_ref", "") or "")
        by_alignment.setdefault(alignment_ref, []).append(row)
    rows: list[IntersectionControlArea] = []
    for index, (alignment_ref, region_rows) in enumerate(sorted(by_alignment.items()), start=1):
        rows.append(
            IntersectionControlArea(
                control_area_id=f"{intersection_id}:control-area:{index:02d}",
                intersection_id=intersection_id,
                alignment_ref=alignment_ref,
                station_ranges=[
                    (
                        float(row.get("station_start", 0.0) or 0.0),
                        float(row.get("station_end", 0.0) or 0.0),
                    )
                    for row in region_rows
                ],
                influence_ranges=[
                    (
                        float(row.get("station_start", 0.0) or 0.0),
                        float(row.get("station_end", 0.0) or 0.0),
                    )
                    for row in region_rows
                ],
                control_region_refs=[str(row.get("control_region_ref", "") or "") for row in region_rows],
                source_method="region_derived",
                approval_status="draft",
                intent_status="region_derived",
                source_region_refs=[str(row.get("control_region_ref", "") or "") for row in region_rows],
                grading_policy_ref=f"grading:{intersection_id}:default",
                diagnostic_rows=["control_area_region_derived", "control_area_approval_pending"],
                notes="Linked from Region rows tagged with intersection_ref.",
            )
        )
    return rows


def _leg_rows_from_region_choices(
    intersection_id: str,
    control_region_choices: list[dict[str, object]],
    *,
    intersection_kind: str = "",
    primary_alignment_ref: str = "",
    secondary_alignment_refs: list[str] | None = None,
) -> list[IntersectionLegRow]:
    expanded_rows = _expanded_leg_source_rows_for_intersection_kind(
        intersection_id,
        control_region_choices,
        intersection_kind=intersection_kind,
        primary_alignment_ref=primary_alignment_ref,
        secondary_alignment_refs=secondary_alignment_refs or [],
    )
    if expanded_rows:
        return expanded_rows
    rows: list[IntersectionLegRow] = []
    for index, row in enumerate(control_region_choices, start=1):
        rows.append(_intersection_leg_row_from_region_choice(intersection_id, row, index, _leg_role_from_region_id(str(row.get("region_id", "") or ""), index)))
    return rows


def _expanded_leg_source_rows_for_intersection_kind(
    intersection_id: str,
    control_region_choices: list[dict[str, object]],
    *,
    intersection_kind: str = "",
    primary_alignment_ref: str = "",
    secondary_alignment_refs: list[str] | None = None,
) -> list[IntersectionLegRow]:
    """Return approach-direction legs for intersection kinds where one Region spans two approaches."""

    kind = str(intersection_kind or "").strip()
    if kind != "cross_intersection":
        return []
    primary_ref = str(primary_alignment_ref or "").strip()
    secondary_refs = [str(ref or "").strip() for ref in list(secondary_alignment_refs or []) if str(ref or "").strip()]
    primary_row = _control_region_choice_for_alignment(control_region_choices, primary_ref)
    secondary_ref = secondary_refs[0] if secondary_refs else ""
    secondary_row = _control_region_choice_for_alignment(control_region_choices, secondary_ref)
    if primary_row is None or secondary_row is None:
        return []
    specs = [
        (primary_row, "primary_after"),
        (secondary_row, "secondary_after"),
        (primary_row, "primary_before"),
        (secondary_row, "secondary_before"),
    ]
    return [
        _intersection_leg_row_from_region_choice(intersection_id, row, index, role)
        for index, (row, role) in enumerate(specs, start=1)
    ]


def _control_region_choice_for_alignment(control_region_choices: list[dict[str, object]], alignment_ref: str):
    target = str(alignment_ref or "").strip()
    if not target:
        return None
    for row in list(control_region_choices or []):
        if str(row.get("alignment_ref", "") or "").strip() == target:
            return row
    return None


def _intersection_leg_row_from_region_choice(
    intersection_id: str,
    row: dict[str, object],
    index: int,
    leg_role: str,
) -> IntersectionLegRow:
    start = float(row.get("station_start", 0.0) or 0.0)
    end = float(row.get("station_end", 0.0) or 0.0)
    alignment_ref = str(row.get("alignment_ref", "") or "")
    return IntersectionLegRow(
        leg_id=f"{intersection_id}:leg:{index:02d}",
        intersection_id=intersection_id,
        leg_role=str(leg_role or f"control_region_{index:02d}"),
        alignment_ref=alignment_ref,
        region_ref=str(row.get("control_region_ref", "") or ""),
        approach_station_start=min(start, end),
        approach_station_end=max(start, end),
        source_method="region_derived",
        approval_status="draft",
        span_source="control_region",
        arm_policy_ref=f"arm-policy:{intersection_id}:leg:{index:02d}",
        grading_policy_ref=f"grading:{intersection_id}:default",
        priority=index,
        diagnostic_rows=["leg_source_region_derived", "leg_approval_pending"],
        notes="Linked from intersection control Region.",
    )


def _default_arm_policy_rows(intersection_id: str, leg_rows: list[IntersectionLegRow]) -> list[IntersectionArmPolicyRow]:
    rows: list[IntersectionArmPolicyRow] = []
    for index, leg in enumerate(list(leg_rows or []), start=1):
        leg_ref = str(getattr(leg, "leg_id", "") or "")
        role = str(getattr(leg, "leg_role", "") or "")
        rows.append(
            IntersectionArmPolicyRow(
                policy_id=str(getattr(leg, "arm_policy_ref", "") or f"arm-policy:{intersection_id}:leg:{index:02d}"),
                intersection_id=intersection_id,
                leg_ref=leg_ref,
                arm_role=role,
                design_speed_kph=40.0 if "primary" in role else 30.0,
                design_vehicle_ref="design-vehicle:passenger-car",
                lane_count=2,
                lane_width=3.5,
                shoulder_width=1.0,
                approval_status="draft",
                diagnostic_rows=["arm_policy_source_defaulted", "arm_policy_approval_pending"],
                notes="Default intersection arm policy for future edge-network evaluation.",
            )
        )
    return rows


def _default_drainage_policy(intersection_id: str) -> IntersectionDrainagePolicyRow:
    return IntersectionDrainagePolicyRow(
        policy_id=f"drainage-policy:{intersection_id}:default",
        intersection_id=intersection_id,
        capture_mode="review_low_points",
        low_point_tolerance=0.05,
        intent_status="hint_only",
        source_method="preset_default",
        approval_status="draft",
        diagnostic_rows=["drainage_policy_hint_only", "drainage_policy_approval_pending"],
        notes="Default intersection drainage handoff policy for low-point review.",
    )


def _leg_role_from_region_id(region_id: str, index: int) -> str:
    text = str(region_id or "").lower()
    if "primary_approach" in text:
        return "primary_approach"
    if "left_branch" in text:
        return "left_branch"
    if "right_branch" in text:
        return "right_branch"
    if "primary" in text:
        return "primary_control"
    if "secondary" in text or "side" in text:
        return "secondary_control"
    return f"control_region_{index:02d}"


def _source_mode_id(source_mode: str) -> str:
    text = str(source_mode or "").strip().lower()
    if "starter" in text:
        return "create_starter_sources"
    return "use_existing_alignments"


def _default_corner_rows(
    intersection_id: str,
    intersection_kind: str,
    control_area_rows: list[IntersectionControlArea],
    leg_rows: list[IntersectionLegRow],
) -> list[IntersectionCornerRow]:
    leg_ids = [
        str(getattr(row, "leg_id", "") or "")
        for row in list(leg_rows or [])
        if str(getattr(row, "leg_id", "") or "")
    ]
    if len(leg_ids) < 2:
        return []
    kind = str(intersection_kind or "").strip()
    corner_labels = _default_corner_labels(kind)
    control_area_ref = str(getattr(control_area_rows[0], "control_area_id", "") or "") if control_area_rows else ""
    rows: list[IntersectionCornerRow] = []
    for index, label in enumerate(corner_labels, start=1):
        from_leg_ref = leg_ids[(index - 1) % len(leg_ids)]
        to_leg_ref = leg_ids[index % len(leg_ids)]
        rows.append(
            IntersectionCornerRow(
                corner_id=f"corner:{intersection_id}:{label}",
                intersection_id=intersection_id,
                control_area_ref=control_area_ref,
                from_leg_ref=from_leg_ref,
                to_leg_ref=to_leg_ref,
                side=label,
                quadrant=label,
                curb_return_policy_ref=f"curb-return:{intersection_id}:default",
                source_method="preset_default",
                approval_status="draft",
                diagnostic_rows=["corner_source_defaulted", "corner_approval_pending"],
                notes="Default corner source row for first-slice curb-return review.",
            )
        )
    return rows


def _default_corner_labels(intersection_kind: str) -> tuple[str, ...]:
    kind = str(intersection_kind or "").strip()
    if kind == "cross_intersection":
        return ("quadrant_01", "quadrant_02", "quadrant_03", "quadrant_04")
    return ("left", "right")


def _default_curb_return_policy(
    *,
    intersection_id: str,
    intersection_kind: str,
    leg_rows: list[IntersectionLegRow],
    corner_rows: list[IntersectionCornerRow] | None = None,
) -> IntersectionCurbReturnPolicyRow:
    kind = str(intersection_kind or "").strip()
    radius = 12.0
    if kind == "cross_intersection":
        radius = 10.0
    return IntersectionCurbReturnPolicyRow(
        policy_id=f"curb-return:{intersection_id}:default",
        intersection_id=intersection_id,
        radius=radius,
        side="all",
        edge_role="pavement_edge",
        approach_leg_refs=[
            str(getattr(row, "leg_id", "") or "")
            for row in list(leg_rows or [])
            if str(getattr(row, "leg_id", "") or "")
        ],
        corner_refs=[
            str(getattr(row, "corner_id", "") or "")
            for row in list(corner_rows or [])
            if str(getattr(row, "corner_id", "") or "")
        ],
        approval_status="draft",
        diagnostic_rows=["curb_return_source_defaulted", "curb_return_approval_pending"],
        notes="Default first-slice curb return radius for 3D review preview.",
    )


def _default_grading_policy(
    *,
    intersection_id: str,
    primary_alignment_ref: str,
    secondary_alignment_refs: list[str],
) -> IntersectionGradingPolicyRow:
    return IntersectionGradingPolicyRow(
        policy_id=f"grading:{intersection_id}:default",
        intersection_id=intersection_id,
        mode="flatten_intersection",
        target_crossfall_percent=0.0,
        primary_alignment_ref=primary_alignment_ref,
        secondary_alignment_refs=list(secondary_alignment_refs or []),
        crown_behavior="flatten",
        tie_in_rule="blend_to_leg_profiles",
        crossfall_transition="linear",
        low_point_strategy="review_low_points",
        source_method="preset_default",
        approval_status="draft",
        diagnostic_rows=["grading_policy_source_defaulted", "grading_policy_approval_pending"],
        notes="Default first-slice intersection grading policy. Overrides normal superelevation inside the control area.",
    )


def _default_slope_face_policy(*, intersection_id: str) -> IntersectionSlopeFacePolicyRow:
    return IntersectionSlopeFacePolicyRow(
        policy_id=f"slope-face:{intersection_id}:default",
        intersection_id=intersection_id,
        policy_name="Default Intersection Slope Face Policy",
        tie_slope_overlap_m=0.5,
        slope_face_width_offset_m=0.0,
        blend_angle_deg=0.0,
        max_panel_extension_m=3.0,
        min_panel_width_m=0.25,
        enabled=True,
        diagnostic_level="normal",
        source_method="preset_default",
        approval_status="draft",
        diagnostic_rows=["slope_face_policy_source_defaulted", "slope_face_policy_approval_pending"],
        notes="Default source policy for dedicated Intersection Slope Face panel reach.",
    )


def _curb_return_arc_sample_count(radius: float) -> int:
    arc_length = max(float(radius), 0.0) * (pi / 2.0)
    segment_count = int(ceil(arc_length / 2.0)) if arc_length > 0.0 else 4
    segment_count = max(4, min(segment_count, 48))
    return segment_count + 1


def _set_preview_property(obj, name: str, value: str) -> None:
    if obj is None:
        return
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyString", name, "Review", name)
        setattr(obj, name, str(value))
    except Exception:
        pass


def _set_preview_string_list_property(obj, name: str, values: list[str]) -> None:
    if obj is None:
        return
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyStringList", name, "Review", name)
        setattr(obj, name, [str(value) for value in list(values or [])])
    except Exception:
        pass


def _set_preview_integer_property(obj, name: str, value: int) -> None:
    if obj is None:
        return
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyInteger", name, "Review", name)
        setattr(obj, name, int(value))
    except Exception:
        pass


def _unique_text_values(values: list[object]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _create_alignment_source_from_points(document, *, label: str, alignment_id: str, points: list[tuple[float, float]], project=None):
    try:
        obj = document.addObject("Part::FeaturePython", "V1Alignment")
    except Exception:
        obj = document.addObject("App::FeaturePython", "V1Alignment")
    V1AlignmentObject(obj)
    try:
        ViewProviderV1Alignment(obj.ViewObject)
    except Exception:
        pass
    length = _polyline_length(points)
    obj.Label = label
    obj.ProjectId = _project_id(project)
    obj.AlignmentId = alignment_id
    obj.AlignmentKind = "road_centerline"
    obj.ElementIds = [f"{alignment_id}:starter:1"]
    obj.ElementKinds = ["tangent" if len(points) == 2 else "sampled_curve"]
    obj.StationStarts = [0.0]
    obj.StationEnds = [length]
    obj.ElementLengths = [length]
    obj.XValueRows = [",".join(f"{x:.3f}" for x, _y in points)]
    obj.YValueRows = [",".join(f"{y:.3f}" for _x, y in points)]
    obj.TotalLength = length
    obj.CriteriaStatus = "starter"
    obj.CriteriaMessages = ["Created by Intersections starter source workflow."]
    try:
        obj.touch()
    except Exception:
        pass
    if project is not None:
        try:
            route_object_to_project_tree(project, obj)
        except Exception:
            pass
    return obj


def _unique_alignment_id(document, base_alignment_id: str) -> str:
    base = str(base_alignment_id or "alignment:intersection").strip() or "alignment:intersection"
    existing = {
        str(getattr(model, "alignment_id", "") or "")
        for model in (to_alignment_model(obj) for obj in list(getattr(document, "Objects", []) or []))
        if model is not None
    }
    if base not in existing:
        return base
    index = 2
    while f"{base}-{index}" in existing:
        index += 1
    return f"{base}-{index}"


def _update_profile_to_alignment_length(profile, length: float, *, profile_style: str = "") -> None:
    style = str(profile_style or "").strip()
    profile.ControlPointIds = [
        f"{profile.ProfileId}:pvi:1",
        f"{profile.ProfileId}:pvi:2",
        f"{profile.ProfileId}:pvi:3",
    ]
    profile.ControlStations = [0.0, max(float(length) * 0.5, 0.0), max(float(length), 0.0)]
    if style == "sag_low_point":
        profile.ControlElevations = [60.8, 59.6, 60.7]
        profile.ControlKinds = ["grade_break", "sag_low_point", "grade_break"]
    else:
        profile.ControlElevations = [60.0, 60.8, 60.2]
        profile.ControlKinds = ["grade_break", "pvi", "grade_break"]
    profile.VerticalCurveIds = [f"{profile.ProfileId}:curve:1"]
    profile.VerticalCurveKinds = ["parabolic_vertical_curve"]
    mid = max(float(length) * 0.5, 0.0)
    curve_half = min(15.0, max(float(length) * 0.15, 0.0))
    profile.VerticalCurveStationStarts = [max(mid - curve_half, 0.0)]
    profile.VerticalCurveStationEnds = [min(mid + curve_half, max(float(length), 0.0))]
    profile.VerticalCurveLengths = [max(profile.VerticalCurveStationEnds[0] - profile.VerticalCurveStationStarts[0], 0.0)]
    profile.VerticalCurveParameters = [-0.02]
    try:
        profile.touch()
    except Exception:
        pass


def _starter_region_model_for_alignment(
    *,
    alignment_id: str,
    intersection_kind: str,
    role: str,
    length: float,
    project_id: str,
    assembly_ref: str = "",
    template_ref: str = "",
) -> RegionModel:
    control_start = max(float(length) * 0.4, 0.0)
    control_end = min(float(length) * 0.6, float(length))
    if role == "secondary" and intersection_kind == "t_intersection":
        control_start = max(float(length) * 0.65, 0.0)
        control_end = float(length)
    rows: list[RegionRow] = []
    if control_start > 1.0e-9:
        rows.append(
            RegionRow(
                region_id=f"region:{role}-approach",
                region_index=len(rows) + 1,
                station_start=0.0,
                station_end=control_start,
                assembly_ref=assembly_ref,
                template_ref=template_ref,
                priority=10,
                notes="Starter normal approach Region created by Intersections.",
            )
        )
    if control_end > control_start + 1.0e-9:
        rows.append(
            RegionRow(
                region_id=f"region:{role}-intersection",
                region_index=len(rows) + 1,
                station_start=control_start,
                station_end=control_end,
                assembly_ref=assembly_ref,
                template_ref=template_ref,
                priority=80,
                intersection_ref=f"intersection:starter-{intersection_kind}",
                notes="Starter intersection control Region created by Intersections.",
            )
        )
    if float(length) > control_end + 1.0e-9:
        rows.append(
            RegionRow(
                region_id=f"region:{role}-departure",
                region_index=len(rows) + 1,
                station_start=control_end,
                station_end=float(length),
                assembly_ref=assembly_ref,
                template_ref=template_ref,
                priority=10,
                notes="Starter normal departure Region created by Intersections.",
            )
        )
    return RegionModel(
        schema_version=1,
        project_id=project_id,
        region_model_id=f"regions:intersection-{role}",
        alignment_id=alignment_id,
        label=f"Intersection {role.title()} Regions",
        region_rows=rows,
    )


def _ensure_starter_assembly_for_intersections(document, *, project=None, created: list[str] | None = None) -> tuple[str, str]:
    """Ensure starter intersection sources have an Assembly/Subassembly source for Build Sections."""

    try:
        from ..objects.obj_subassembly_assembly import (
            find_v1_assembly_subassembly_model,
            to_assembly_subassembly_model,
        )

        existing_subassembly_obj = find_v1_assembly_subassembly_model(document)
        existing_subassembly_model = (
            to_assembly_subassembly_model(existing_subassembly_obj)
            if existing_subassembly_obj is not None
            else None
        )
        if existing_subassembly_model is not None:
            assembly_id = str(getattr(existing_subassembly_model, "assembly_id", "") or "").strip()
            template_id = str(getattr(existing_subassembly_model, "active_template_id", "") or "").strip()
            if assembly_id:
                return assembly_id, template_id
    except Exception:
        pass
    try:
        from .cmd_subassembly_editor import (
            apply_v1_assembly_subassembly_model,
            assembly_subassembly_preset_model_from_document,
        )

        model = assembly_subassembly_preset_model_from_document("Basic Road", document=document, project=project)
        obj = apply_v1_assembly_subassembly_model(
            document=document,
            project=project,
            assembly_model=model,
            object_name="V1IntersectionStarterAssemblySubassembly",
        )
        if created is not None:
            created.append(f"Assembly / Subassembly: {getattr(obj, 'Label', '') or getattr(obj, 'Name', '')} | {model.assembly_id}")
        return str(getattr(model, "assembly_id", "") or ""), str(getattr(model, "active_template_id", "") or "")
    except Exception:
        return "", ""


def _polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(points, points[1:]))


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value or "source")).strip("_") or "source"


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass
