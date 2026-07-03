"""Intersection source editor command for Parametric Road v1."""

from __future__ import annotations

from math import ceil, cos, hypot, pi, sin

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

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtWidgets

from ..models.source.intersection_model import (
    IntersectionAnchorRow,
    IntersectionArmPolicyRow,
    IntersectionControlArea,
    IntersectionCornerRow,
    IntersectionCurbReturnPolicyRow,
    IntersectionDrainagePolicyRow,
    IntersectionEdgePolicyRow,
    IntersectionGradingPolicyRow,
    IntersectionLaneConnectionRow,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
    intersection_kind_from_label,
    intersection_preset_labels,
)
from ..objects.obj_alignment import to_alignment_model
from ..objects.obj_alignment import V1AlignmentObject, ViewProviderV1Alignment
from ..objects.obj_profile import create_sample_v1_profile
from ..objects.obj_intersection import create_or_update_v1_intersection_model_object
from ..objects.obj_region import create_or_update_v1_region_model_object, to_region_model
from ..objects.obj_stationing import create_v1_stationing
from ..models.source.region_model import RegionModel, RegionRow
from ..services.evaluation.intersection_alignment_detection_service import AlignmentIntersectionDetectionService
from ..services.evaluation.intersection_evaluation_service import IntersectionEvaluationService
from ...objects.obj_project import find_project, route_to_v1_tree


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
    )
    control_area_rows = _control_area_rows_from_region_choices(intersection_id, control_region_choices)
    leg_rows = _leg_rows_from_region_choices(intersection_id, control_region_choices)
    corner_rows = _default_corner_rows(intersection_id, kind, control_area_rows, leg_rows)
    arm_policy_rows = _default_arm_policy_rows(intersection_id, leg_rows)
    edge_policy_rows = _default_edge_policy_rows(intersection_id, leg_rows)
    lane_connection_rows = _default_lane_connection_rows(intersection_id, kind, leg_rows)
    drainage_policy_row = _default_drainage_policy(intersection_id, edge_policy_rows)
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
            drainage_policy_row.policy_id,
            *[row.policy_id for row in arm_policy_rows],
            *[row.policy_id for row in edge_policy_rows],
        ],
        source_mode=_source_mode_id(source_mode),
        notes="Created by Intersections panel control Region linking.",
    )
    return IntersectionModel(
        schema_version=1,
        project_id=project_id,
        label="Intersections",
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
        edge_policy_rows=edge_policy_rows,
        lane_connection_rows=lane_connection_rows,
        drainage_policy_rows=[drainage_policy_row],
    )


def intersection_source_completeness_rows(
    intersection_model: IntersectionModel | None,
    *,
    alignment_errors: list[str] | tuple[str, ...] = (),
    control_region_count: int = 0,
) -> list[dict[str, object]]:
    """Return staged source-completeness rows for the Intersection panel."""

    rows: list[dict[str, object]] = []
    if intersection_model is None:
        participant_status = "warning" if control_region_count else "missing"
        participant_diagnostics = [str(item) for item in alignment_errors if str(item)]
        if not control_region_count:
            participant_diagnostics.append("source_control_regions_missing")
        return [
            _source_stage_row("Participants", participant_status, control_region_count, participant_diagnostics),
            _source_stage_row("Anchor", "missing", 0, ["source_anchor_rows_missing"]),
            _source_stage_row("Legs", "missing", 0, ["source_leg_rows_missing"]),
            _source_stage_row("Control Areas", "missing", 0, ["source_control_area_rows_missing"]),
            _source_stage_row("Corners", "missing", 0, ["source_corner_rows_missing"]),
            _source_stage_row("Edge Families", "missing", 0, ["source_edge_policy_rows_missing"]),
            _source_stage_row("Lane Connections", "missing", 0, ["source_lane_connection_rows_missing"]),
            _source_stage_row("Grading", "missing", 0, ["source_grading_policy_rows_missing"]),
            _source_stage_row("Drainage", "missing", 0, ["source_drainage_policy_rows_missing"]),
            _source_stage_row("Preview", "missing", 0, ["source_model_missing"]),
        ]

    service = IntersectionEvaluationService()
    topology = service.evaluate_topology(intersection_model)
    edge_network = service.evaluate_edge_network(intersection_model, topology)
    surface_zones = service.evaluate_surface_zones(intersection_model, edge_network)
    grading_context = service.evaluate_grading_context(intersection_model, surface_zones)
    drainage_hints = service.evaluate_drainage_hints(intersection_model, surface_zones, grading_context)

    intersection_rows = list(getattr(intersection_model, "intersection_rows", []) or [])
    first_intersection = intersection_rows[0] if intersection_rows else None
    participant_diagnostics = list(alignment_errors or [])
    if first_intersection is None:
        participant_diagnostics.append("source_intersection_row_missing")
    elif not str(getattr(first_intersection, "primary_alignment_ref", "") or ""):
        participant_diagnostics.append("source_primary_alignment_ref_missing")
    elif not list(getattr(first_intersection, "secondary_alignment_refs", []) or []):
        participant_diagnostics.append("source_secondary_alignment_refs_missing")
    if not control_region_count and first_intersection is not None:
        control_region_count = len(list(getattr(first_intersection, "control_region_refs", []) or []))
    if not control_region_count:
        participant_diagnostics.append("source_control_regions_missing")
    rows.append(
        _source_stage_row(
            "Participants",
            "warning" if participant_diagnostics else "accepted",
            len(intersection_rows),
            participant_diagnostics,
        )
    )
    rows.append(_result_stage_row("Anchor", list(getattr(topology, "anchor_rows", []) or []), missing="source_anchor_rows_missing"))
    rows.append(_result_stage_row("Legs", list(getattr(topology, "leg_span_rows", []) or []), missing="source_leg_rows_missing"))
    rows.append(_result_stage_row("Control Areas", list(getattr(topology, "control_area_rows", []) or []), missing="source_control_area_rows_missing"))
    rows.append(_source_stage_row_from_source_rows("Corners", list(getattr(intersection_model, "corner_rows", []) or []), "source_corner_rows_missing"))
    rows.append(_source_stage_row_from_source_rows("Edge Families", list(getattr(intersection_model, "edge_policy_rows", []) or []), "source_edge_policy_rows_missing"))
    rows.append(_result_stage_row("Lane Connections", list(getattr(topology, "lane_connection_rows", []) or []), missing="source_lane_connection_rows_missing"))
    rows.append(_result_stage_row("Grading", list(getattr(grading_context, "context_rows", []) or []), missing="source_grading_context_rows_missing"))
    rows.append(_result_stage_row("Drainage", list(getattr(drainage_hints, "hint_rows", []) or []), missing="source_drainage_hint_rows_missing"))
    preview_diagnostics = [
        *list(getattr(edge_network, "diagnostic_rows", []) or []),
        *list(getattr(surface_zones, "diagnostic_rows", []) or []),
    ]
    rows.append(
        _source_stage_row(
            "Preview",
            _stage_status_from_statuses([str(getattr(edge_network, "status", "") or ""), str(getattr(surface_zones, "status", "") or "")]),
            int(getattr(edge_network, "edge_count", 0) or 0) + int(getattr(surface_zones, "zone_count", 0) or 0),
            preview_diagnostics,
        )
    )
    return rows


def intersection_source_completeness_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    """Return compact staged source-completeness counts and next action text."""

    accepted_count = _stage_count(rows, "accepted")
    warning_count = _stage_count(rows, "warning")
    missing_count = _stage_count(rows, "missing")
    error_count = _stage_count(rows, "error")
    next_row = _first_source_stage_requiring_review(rows)
    if error_count:
        status = "error"
    elif missing_count:
        status = "missing"
    elif warning_count:
        status = "warning"
    else:
        status = "accepted"
    next_stage = str(next_row.get("stage", "") or "") if next_row else ""
    next_diagnostic = ""
    if next_row:
        diagnostics = list(next_row.get("diagnostics", []) or [])
        next_diagnostic = str(diagnostics[0]) if diagnostics else str(next_row.get("notes", "") or "")
    return {
        "status": status,
        "accepted_count": accepted_count,
        "warning_count": warning_count,
        "missing_count": missing_count,
        "error_count": error_count,
        "next_stage": next_stage,
        "next_diagnostic": next_diagnostic,
        "preview_ready": missing_count == 0 and error_count == 0,
        "apply_ready": missing_count == 0 and error_count == 0,
        "notes": _source_completeness_summary_notes(
            status=status,
            accepted_count=accepted_count,
            warning_count=warning_count,
            missing_count=missing_count,
            error_count=error_count,
            next_stage=next_stage,
            next_diagnostic=next_diagnostic,
        ),
    }


def intersection_read_only_preview_rows(
    intersection_model: IntersectionModel | None,
    *,
    source_rows: list[dict[str, object]] | None = None,
    alignment_errors: list[str] | tuple[str, ...] = (),
    control_region_count: int = 0,
) -> list[dict[str, object]]:
    """Return read-only result preview stages without creating output geometry."""

    source_stage_rows = list(source_rows or [])
    if not source_stage_rows:
        source_stage_rows = intersection_source_completeness_rows(
            intersection_model,
            alignment_errors=alignment_errors,
            control_region_count=control_region_count,
        )
    source_summary = intersection_source_completeness_summary(source_stage_rows)
    rows = [
        _preview_stage_row(
            "Source Validation",
            source_summary["status"],
            len(source_stage_rows),
            "IntersectionModel source stages",
            [str(source_summary.get("next_diagnostic", "") or "")],
        )
    ]
    if intersection_model is None:
        rows.extend(
            [
                _preview_stage_row("Topology", "missing", 0, "IntersectionTopologyResult", ["source_model_missing"]),
                _preview_stage_row("Edge Network", "missing", 0, "IntersectionEdgeNetworkResult", ["source_model_missing"]),
                _preview_stage_row("Surface Zones", "missing", 0, "IntersectionSurfaceZoneResult", ["source_model_missing"]),
                _preview_stage_row("Grading", "missing", 0, "IntersectionGradingContextResult", ["source_model_missing"]),
                _preview_stage_row("Drainage", "missing", 0, "IntersectionDrainageHintResult", ["source_model_missing"]),
                _preview_stage_row("Slope Loops", "missing", 0, "IntersectionSlopeFaceLoopResult", ["source_model_missing"]),
            ]
        )
        return rows

    service = IntersectionEvaluationService()
    topology = service.evaluate_topology(intersection_model)
    edge_network = service.evaluate_edge_network(intersection_model, topology)
    surface_zones = service.evaluate_surface_zones(intersection_model, edge_network)
    grading_context = service.evaluate_grading_context(intersection_model, surface_zones)
    drainage_hints = service.evaluate_drainage_hints(intersection_model, surface_zones, grading_context)
    slope_loops = service.evaluate_slope_face_loops(intersection_model, surface_zones, edge_network)
    rows.extend(
        [
            _preview_stage_row(
                "Topology",
                getattr(topology, "status", ""),
                int(getattr(topology, "anchor_count", 0) or 0)
                + int(getattr(topology, "leg_span_count", 0) or 0)
                + int(getattr(topology, "control_area_count", 0) or 0)
                + int(getattr(topology, "lane_connection_count", 0) or 0),
                "IntersectionTopologyResult",
                list(getattr(topology, "diagnostic_rows", []) or []),
            ),
            _preview_stage_row(
                "Edge Network",
                getattr(edge_network, "status", ""),
                int(getattr(edge_network, "edge_count", 0) or 0),
                "IntersectionEdgeNetworkResult",
                list(getattr(edge_network, "diagnostic_rows", []) or []),
            ),
            _preview_stage_row(
                "Surface Zones",
                getattr(surface_zones, "status", ""),
                int(getattr(surface_zones, "zone_count", 0) or 0),
                "IntersectionSurfaceZoneResult",
                list(getattr(surface_zones, "diagnostic_rows", []) or []),
            ),
            _preview_stage_row(
                "Grading",
                getattr(grading_context, "status", ""),
                int(getattr(grading_context, "context_count", 0) or 0),
                "IntersectionGradingContextResult",
                [
                    *list(getattr(grading_context, "diagnostic_rows", []) or []),
                    *_result_rows_stage_metadata(list(getattr(grading_context, "context_rows", []) or [])),
                ],
            ),
            _preview_stage_row(
                "Drainage",
                getattr(drainage_hints, "status", ""),
                int(getattr(drainage_hints, "hint_row_count", 0) or 0),
                "IntersectionDrainageHintResult",
                [
                    *list(getattr(drainage_hints, "diagnostic_rows", []) or []),
                    *_result_rows_stage_metadata(list(getattr(drainage_hints, "hint_rows", []) or [])),
                ],
            ),
            _preview_stage_row(
                "Slope Loops",
                getattr(slope_loops, "status", ""),
                int(getattr(slope_loops, "loop_count", 0) or 0),
                "IntersectionSlopeFaceLoopResult",
                [
                    *list(getattr(slope_loops, "diagnostic_rows", []) or []),
                    *_result_rows_stage_metadata(list(getattr(slope_loops, "loop_rows", []) or [])),
                ],
            ),
        ]
    )
    return rows


def show_intersection_review_overlay(
    document,
    *,
    intersection_kind: str,
    primary_alignment_ref: str,
    secondary_alignment_ref: str,
    control_region_choices: list[dict[str, object]],
    detection_result=None,
    project=None,
):
    """Create or update the first-slice 3D review overlay for one intersection."""

    if document is None:
        raise RuntimeError("No active document is available.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Intersection review overlay.")

    alignment_by_ref = {
        str(ref): alignment_model_by_ref(document, str(ref))
        for ref in _unique_text_values(
            [
                primary_alignment_ref,
                secondary_alignment_ref,
                *[str(row.get("alignment_ref", "") or "") for row in control_region_choices],
            ]
        )
    }
    shapes: list[object] = []
    control_refs: list[str] = []
    for row in control_region_choices:
        alignment_ref = str(row.get("alignment_ref", "") or "")
        alignment = alignment_by_ref.get(alignment_ref)
        station_start, station_end = _intersection_review_region_station_span(
            row,
            detection_result=detection_result,
            primary_alignment_ref=primary_alignment_ref,
            secondary_alignment_ref=secondary_alignment_ref,
            max_span=INTERSECTION_REVIEW_MAX_REGION_SPAN,
        )
        points = _alignment_station_span_points(
            alignment,
            station_start,
            station_end,
        )
        if len(points) >= 2:
            for first, second in zip(points[:-1], points[1:]):
                shapes.append(Part.makeLine(first, second))
            control_refs.append(str(row.get("control_region_ref", "") or ""))

    point = _intersection_review_point(detection_result)
    if point is None and control_region_choices:
        first_row = control_region_choices[0]
        alignment = alignment_by_ref.get(str(first_row.get("alignment_ref", "") or ""))
        point = _alignment_point_at_station(alignment, float(first_row.get("station_start", 0.0) or 0.0))
    if point is not None:
        shapes.extend(_intersection_point_marker_shapes(point, radius=3.0))
        curb_return_shapes, curb_return_metadata = _curb_return_preview_shapes(
            point=point,
            intersection_kind=intersection_kind,
            primary_alignment=alignment_by_ref.get(str(primary_alignment_ref or "")),
            secondary_alignment=alignment_by_ref.get(str(secondary_alignment_ref or "")),
            detection_result=detection_result,
        )
        shapes.extend(curb_return_shapes)
    else:
        curb_return_metadata = {
            "policy_ref": "",
            "radius": 0.0,
            "arc_count": 0,
            "diagnostics": ["intersection_curb_return_policy_missing: intersection point is required."],
        }

    if not shapes:
        raise RuntimeError("No Intersection review geometry could be created.")

    obj = document.getObject("V1IntersectionReviewOverlay")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1IntersectionReviewOverlay")
    obj.Label = "Intersection Review Overlay"
    obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
    _set_preview_property(obj, "CRRecordKind", "v1_intersection_review_overlay")
    _set_preview_property(obj, "V1ObjectType", "V1IntersectionReviewOverlay")
    _set_preview_property(obj, "IntersectionKind", str(intersection_kind or ""))
    _set_preview_property(obj, "PrimaryAlignmentRef", str(primary_alignment_ref or ""))
    _set_preview_property(obj, "SecondaryAlignmentRef", str(secondary_alignment_ref or ""))
    _set_preview_string_list_property(obj, "ControlRegionRefs", _unique_text_values(control_refs))
    _set_preview_property(obj, "CurbReturnPolicyRef", str(curb_return_metadata.get("policy_ref", "") or ""))
    _set_preview_property(obj, "CurbReturnRadius", f"{float(curb_return_metadata.get('radius', 0.0) or 0.0):.3f}")
    _set_preview_integer_property(obj, "CurbReturnArcCount", int(curb_return_metadata.get("arc_count", 0) or 0))
    _set_preview_string_list_property(obj, "CurbReturnDiagnostics", list(curb_return_metadata.get("diagnostics", []) or []))
    _set_preview_integer_property(obj, "ShapePartCount", len(shapes))
    _style_intersection_review_overlay(obj, visible=True)
    try:
        prj = project or find_project(document)
        if prj is not None:
            route_to_v1_tree(prj, obj)
    except Exception:
        pass
    try:
        document.recompute()
    except Exception:
        pass
    return obj


def set_intersection_review_overlay_visible(document, visible: bool):
    """Set the Intersection review overlay visibility."""

    obj = document.getObject("V1IntersectionReviewOverlay") if document is not None else None
    if obj is None:
        return None
    try:
        obj.ViewObject.Visibility = bool(visible)
    except Exception:
        pass
    return obj


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
    if kind == "skewed_intersection":
        return {
            "kind": kind,
            "alignments": [
                {"role": "primary", "label": "Skew Main Road", "points": [(-130.0, 0.0), (130.0, 0.0)]},
                {"role": "secondary_skew", "label": "Skew Crossing Road", "points": [(-70.0, -120.0), (70.0, 120.0)]},
            ],
        }
    if kind == "urban_curb_gutter_intersection":
        return {
            "kind": kind,
            "alignments": [
                {"role": "primary", "label": "Urban Main Street", "points": [(-120.0, 0.0), (120.0, 0.0)]},
                {"role": "secondary", "label": "Urban Side Street", "points": [(0.0, -110.0), (0.0, 110.0)]},
            ],
        }
    if kind == "drainage_sag_intersection":
        return {
            "kind": kind,
            "profile_style": "sag_low_point",
            "alignments": [
                {"role": "primary", "label": "Sag Main Road", "points": [(-120.0, 0.0), (120.0, 0.0)]},
                {"role": "secondary", "label": "Sag Side Road", "points": [(0.0, -110.0), (0.0, 110.0)]},
            ],
        }
    if kind == "y_intersection":
        return {
            "kind": kind,
            "alignments": [
                {"role": "primary_approach", "label": "Y Main Approach", "points": [(0.0, -120.0), (0.0, 0.0)]},
                {"role": "left_branch", "label": "Y Left Branch Road", "points": [(0.0, 0.0), (-90.0, 90.0)]},
                {"role": "right_branch", "label": "Y Right Branch Road", "points": [(0.0, 0.0), (90.0, 90.0)]},
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
    raise ValueError(f"Unsupported starter intersection kind: {intersection_kind}")


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


def run_v1_intersection_editor_command():
    """Open the v1 Intersection source editor shell."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    panel = V1IntersectionEditorTaskPanel(document=App.ActiveDocument)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return panel


class V1IntersectionEditorTaskPanel:
    """First-slice Intersection source editor shell."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self._alignment_choices = list_v1_alignment_choices(self.document)
        self.form = self._build_ui()
        self._last_detection = None
        self._last_created_sources: list[str] = []
        self._last_applied_intersection = ""
        self._last_overlay = ""
        self._last_source_stage_rows: list[dict[str, object]] = []
        self._last_preview_stage_rows: list[dict[str, object]] = []
        self._update_status()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return True

    def reject(self):
        if Gui is not None:
            try:
                Gui.Control.closeDialog()
            except Exception:
                pass
        return True

    def selected_intersection_kind(self) -> str:
        """Return the internal intersection kind selected in the panel."""

        return intersection_kind_from_label(str(self._type_combo.currentText() or ""))

    def selected_source_mode(self) -> str:
        """Return the selected source mode label."""

        return str(self._source_mode_combo.currentText() or INTERSECTION_SOURCE_MODES[0])

    def selected_primary_alignment_ref(self) -> str:
        """Return the selected primary Alignment ref."""

        return _combo_data_or_text(self._primary_alignment_combo)

    def selected_secondary_alignment_ref(self) -> str:
        """Return the selected secondary Alignment ref."""

        return _combo_data_or_text(self._secondary_alignment_combo)

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("Parametric Road v1 - Intersections")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Intersections")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        note = QtWidgets.QLabel(
            "Define at-grade junction source intent. Select the intersection type first; "
            "use Auto Detect, link control Regions, then review the junction overlay before Build Sections."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        workflow = QtWidgets.QLabel(NEXT_INTERSECTION_WORKFLOW_TEXT)
        workflow.setWordWrap(True)
        try:
            workflow.setStyleSheet("color: #78f0a0;")
        except Exception:
            pass
        layout.addWidget(workflow)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Intersection Type:"))
        self._type_combo = QtWidgets.QComboBox()
        self._type_combo.addItems(intersection_preset_labels())
        self._type_combo.currentIndexChanged.connect(self._update_status)
        preset_row.addWidget(self._type_combo)
        self._preset_button = QtWidgets.QPushButton("Preset Data")
        self._preset_button.clicked.connect(self._load_preset_data)
        preset_row.addWidget(self._preset_button)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)

        source_row = QtWidgets.QHBoxLayout()
        source_row.addWidget(QtWidgets.QLabel("Source Mode:"))
        self._source_mode_combo = QtWidgets.QComboBox()
        self._source_mode_combo.addItems(INTERSECTION_SOURCE_MODES)
        self._source_mode_combo.currentIndexChanged.connect(self._on_source_mode_changed)
        source_row.addWidget(self._source_mode_combo)
        self._create_sources_button = QtWidgets.QPushButton("Create Starter Sources")
        self._create_sources_button.clicked.connect(self._create_starter_sources)
        source_row.addWidget(self._create_sources_button)
        source_row.addStretch(1)
        layout.addLayout(source_row)

        self._alignment_note = QtWidgets.QLabel(
            "Existing Alignments mode will use selected primary and secondary Alignment sources. "
            "Starter Sources mode creates editable Alignment, Profile, Station, Region, and Assembly / Subassembly sources."
        )
        self._alignment_note.setWordWrap(True)
        layout.addWidget(self._alignment_note)

        primary_alignment_row = QtWidgets.QHBoxLayout()
        primary_alignment_row.addWidget(QtWidgets.QLabel("Primary Alignment:"))
        self._primary_alignment_combo = QtWidgets.QComboBox()
        _populate_alignment_combo(self._primary_alignment_combo, self._alignment_choices)
        self._primary_alignment_combo.currentIndexChanged.connect(self._update_status)
        primary_alignment_row.addWidget(self._primary_alignment_combo, 1)
        layout.addLayout(primary_alignment_row)

        secondary_alignment_row = QtWidgets.QHBoxLayout()
        secondary_alignment_row.addWidget(QtWidgets.QLabel("Secondary Alignment:"))
        self._secondary_alignment_combo = QtWidgets.QComboBox()
        _populate_alignment_combo(self._secondary_alignment_combo, self._alignment_choices)
        if len(self._alignment_choices) > 1:
            self._secondary_alignment_combo.setCurrentIndex(1)
        self._secondary_alignment_combo.currentIndexChanged.connect(self._update_status)
        secondary_alignment_row.addWidget(self._secondary_alignment_combo, 1)
        layout.addLayout(secondary_alignment_row)

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setMinimumHeight(130)
        layout.addWidget(self._status, 1)

        self._source_stage_table = QtWidgets.QTableWidget(0, 6)
        self._source_stage_table.setHorizontalHeaderLabels(["Stage", "Status", "Approval", "Count", "Target", "Diagnostics"])
        self._source_stage_table.setMinimumHeight(150)
        try:
            self._source_stage_table.horizontalHeader().setStretchLastSection(True)
            self._source_stage_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self._source_stage_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        except Exception:
            pass
        layout.addWidget(self._source_stage_table, 1)

        self._preview_stage_table = QtWidgets.QTableWidget(0, 5)
        self._preview_stage_table.setHorizontalHeaderLabels(["Preview", "Status", "Count", "Contract", "Diagnostics"])
        self._preview_stage_table.setMinimumHeight(120)
        try:
            self._preview_stage_table.horizontalHeader().setStretchLastSection(True)
            self._preview_stage_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self._preview_stage_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        except Exception:
            pass
        layout.addWidget(self._preview_stage_table, 1)

        action_row = QtWidgets.QHBoxLayout()
        auto_detect_button = QtWidgets.QPushButton("Auto Detect")
        auto_detect_button.clicked.connect(self._auto_detect_intersection)
        action_row.addWidget(auto_detect_button)
        preview_button = QtWidgets.QPushButton("Preview Selection")
        preview_button.clicked.connect(self._show_review_overlay)
        action_row.addWidget(preview_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        overlay_action_row = QtWidgets.QHBoxLayout()
        hide_button = QtWidgets.QPushButton("Hide Overlay")
        hide_button.clicked.connect(self._hide_review_overlay)
        overlay_action_row.addWidget(hide_button)
        focus_button = QtWidgets.QPushButton("Focus Overlay")
        focus_button.clicked.connect(self._focus_review_overlay)
        overlay_action_row.addWidget(focus_button)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(self._apply_intersection_model)
        overlay_action_row.addWidget(apply_button)
        overlay_action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        overlay_action_row.addWidget(close_button)
        layout.addLayout(overlay_action_row)
        self._update_source_mode_controls()
        return widget

    def _load_preset_data(self) -> None:
        self._update_status(prefix="Preset Data loaded for panel draft only.")

    def _on_source_mode_changed(self) -> None:
        self._update_source_mode_controls()
        self._update_status()

    def _update_source_mode_controls(self) -> None:
        show_create = self.selected_source_mode() == "Create Starter Sources"
        try:
            self._create_sources_button.setVisible(show_create)
        except Exception:
            pass

    def _auto_detect_intersection(self) -> None:
        errors = validate_existing_alignment_selection(
            self.selected_primary_alignment_ref(),
            self.selected_secondary_alignment_ref(),
        )
        if errors:
            self._last_detection = None
            self._update_status(prefix="Auto Detect blocked by Alignment selection errors.")
            return
        primary = alignment_model_by_ref(self.document, self.selected_primary_alignment_ref())
        secondary = alignment_model_by_ref(self.document, self.selected_secondary_alignment_ref())
        if primary is None or secondary is None:
            self._last_detection = None
            self._update_status(prefix="Auto Detect failed: selected Alignment source could not be loaded.")
            return
        self._last_detection = AlignmentIntersectionDetectionService().detect(primary, secondary)
        self._update_status(prefix="Auto Detect completed.")

    def _create_starter_sources(self) -> None:
        if self.selected_source_mode() != "Create Starter Sources":
            self._update_status(prefix="Switch Source Mode to Create Starter Sources before creating source drafts.")
            return
        try:
            self._last_created_sources = create_starter_intersection_sources(
                self.document,
                self.selected_intersection_kind(),
            )
            self._alignment_choices = list_v1_alignment_choices(self.document)
            _populate_alignment_combo(self._primary_alignment_combo, self._alignment_choices)
            _populate_alignment_combo(self._secondary_alignment_combo, self._alignment_choices)
            if len(self._alignment_choices) > 1:
                self._secondary_alignment_combo.setCurrentIndex(1)
            self._update_status(prefix="Starter Sources created, including Assembly / Subassembly source.")
        except Exception as exc:
            self._last_created_sources = []
            self._update_status(prefix=f"Starter Sources were not created: {exc}")

    def _apply_intersection_model(self) -> None:
        kind = self.selected_intersection_kind()
        primary_ref = self.selected_primary_alignment_ref()
        secondary_ref = self.selected_secondary_alignment_ref()
        errors = validate_existing_alignment_selection(primary_ref, secondary_ref)
        if errors:
            self._last_applied_intersection = ""
            message = "Intersection was not applied because Alignment selection has errors.\n" + "\n".join(f"- {error}" for error in errors)
            self._update_status(prefix="Apply blocked by Alignment selection errors.")
            _show_message(self.form, "Intersections", message)
            return
        control_regions = list_intersection_control_region_choices(self.document, intersection_ref_for_kind(kind))
        if not control_regions:
            self._last_applied_intersection = ""
            message = "Intersection was not applied.\nNo intersection-tagged control Regions were found."
            self._update_status(prefix="Apply blocked: no intersection-tagged control Regions were found.")
            _show_message(self.form, "Intersections", message)
            return
        try:
            model = build_intersection_model_from_sources(
                intersection_kind=kind,
                source_mode=self.selected_source_mode(),
                primary_alignment_ref=primary_ref,
                secondary_alignment_ref=secondary_ref,
                control_region_choices=control_regions,
                detection_result=self._last_detection,
                project_id=_project_id(find_project(self.document)),
            )
            obj = create_or_update_v1_intersection_model_object(
                self.document,
                intersection_model=model,
                project=find_project(self.document),
                label="Intersections",
            )
            try:
                self.document.recompute()
            except Exception:
                pass
            self._last_applied_intersection = f"{obj.Label} | {obj.IntersectionModelId}"
            self._update_status(prefix="IntersectionModel applied.")
            _show_message(
                self.form,
                "Intersections",
                (
                    "Intersection has been applied.\n"
                    f"Object: {obj.Label}\n"
                    f"IntersectionModel: {obj.IntersectionModelId}\n"
                    f"Control Regions: {len(control_regions)}"
                ),
            )
        except Exception as exc:
            self._last_applied_intersection = ""
            self._update_status(prefix=f"Apply failed: {exc}")
            _show_message(self.form, "Intersections", f"Intersection was not applied.\n{exc}")

    def _show_review_overlay(self) -> None:
        kind = self.selected_intersection_kind()
        control_regions = list_intersection_control_region_choices(self.document, intersection_ref_for_kind(kind))
        if not control_regions:
            self._last_overlay = ""
            self._update_status(prefix="Preview blocked: no intersection-tagged control Regions were found.")
            return
        try:
            obj = show_intersection_review_overlay(
                self.document,
                intersection_kind=kind,
                primary_alignment_ref=self.selected_primary_alignment_ref(),
                secondary_alignment_ref=self.selected_secondary_alignment_ref(),
                control_region_choices=control_regions,
                detection_result=self._last_detection,
                project=find_project(self.document),
            )
            self._last_overlay = f"{obj.Label} | {obj.Name}"
            if Gui is not None:
                try:
                    Gui.Selection.clearSelection()
                    Gui.Selection.addSelection(obj)
                except Exception:
                    pass
            self._update_status(prefix="Intersection review overlay shown.")
        except Exception as exc:
            self._last_overlay = ""
            self._update_status(prefix=f"Preview failed: {exc}")

    def _hide_review_overlay(self) -> None:
        obj = set_intersection_review_overlay_visible(self.document, False)
        self._update_status(prefix="Intersection review overlay hidden." if obj is not None else "No Intersection review overlay exists.")

    def _focus_review_overlay(self) -> None:
        obj = set_intersection_review_overlay_visible(self.document, True)
        if obj is None:
            self._update_status(prefix="No Intersection review overlay exists.")
            return
        if Gui is not None:
            try:
                Gui.Selection.clearSelection()
                Gui.Selection.addSelection(obj)
                Gui.SendMsgToActiveView("ViewSelection")
            except Exception:
                pass
        self._last_overlay = f"{obj.Label} | {obj.Name}"
        self._update_status(prefix="Intersection review overlay focused.")

    def _update_status(self, *args, prefix: str = "") -> None:
        del args
        kind = self.selected_intersection_kind() if hasattr(self, "_type_combo") else ""
        label = str(self._type_combo.currentText() or "") if hasattr(self, "_type_combo") else ""
        source_mode = self.selected_source_mode() if hasattr(self, "_source_mode_combo") else ""
        primary_ref = self.selected_primary_alignment_ref() if hasattr(self, "_primary_alignment_combo") else ""
        secondary_ref = self.selected_secondary_alignment_ref() if hasattr(self, "_secondary_alignment_combo") else ""
        alignment_errors = (
            validate_existing_alignment_selection(primary_ref, secondary_ref)
            if source_mode == "Use Existing Alignments"
            else []
        )
        detection_lines = _format_detection_lines(self._last_detection) if hasattr(self, "_last_detection") else []
        created_lines = list(getattr(self, "_last_created_sources", []) or [])
        intersection_ref = intersection_ref_for_kind(kind)
        control_regions = list_intersection_control_region_choices(self.document, intersection_ref)
        source_stage_rows = self._source_completeness_rows(control_regions, alignment_errors)
        self._last_source_stage_rows = list(source_stage_rows)
        source_summary = intersection_source_completeness_summary(source_stage_rows)
        self._update_source_stage_table(source_stage_rows)
        preview_stage_rows = self._preview_sequence_rows(control_regions, alignment_errors, source_stage_rows)
        self._last_preview_stage_rows = list(preview_stage_rows)
        self._update_preview_stage_table(preview_stage_rows)
        applied_line = str(getattr(self, "_last_applied_intersection", "") or "")
        overlay_line = str(getattr(self, "_last_overlay", "") or "")
        lines = []
        if prefix:
            lines.append(prefix)
            lines.append("")
        lines.extend(
            [
                "Intersections shell is ready.",
                f"Selected Type: {label} ({kind or 'unresolved'})",
                f"Source Mode: {source_mode}",
                f"Primary Alignment: {primary_ref or '-'}",
                f"Secondary Alignment: {secondary_ref or '-'}",
                "",
                f"Source Summary: {source_summary['status']} | accepted={source_summary['accepted_count']}, "
                f"warnings={source_summary['warning_count']}, missing={source_summary['missing_count']}, errors={source_summary['error_count']}",
                f"Next Source Stage: {source_summary['next_stage'] or 'None'}",
                f"Next Source Diagnostic: {source_summary['next_diagnostic'] or '-'}",
                f"Preview Ready: {'yes' if source_summary['preview_ready'] else 'no'}",
                f"Apply Ready: {'yes' if source_summary['apply_ready'] else 'no'}",
                "",
                f"Validation: {'ok' if not alignment_errors else 'error'}",
                *[f"- {error}" for error in alignment_errors],
                "",
                "Auto Detect:",
                *(detection_lines or ["- Not run."]),
                "",
                f"Control Regions ({intersection_ref}):",
                *(
                    [
                        f"- {row.get('label', '-')}"
                        for row in control_regions
                    ]
                    if control_regions
                    else ["- No linked control Regions found."]
                ),
                "",
                "Source Completeness:",
                *[
                    (
                        f"- {row['stage']}: {row['status']} / {row.get('approval_state', '-')}"
                        f" ({row['count']})"
                    )
                    for row in source_stage_rows
                ],
                "",
                "Read-only Preview Sequence:",
                *[
                    (
                        f"- {row['stage']}: {row['status']} ({row['count']})"
                        f" | {row.get('contract', '-')}"
                    )
                    for row in preview_stage_rows
                ],
                "",
                "Starter Sources:",
                *([f"- {line}" for line in created_lines] if created_lines else ["- Not created."]),
                "",
                "Applied IntersectionModel:",
                f"- {applied_line or 'Not applied.'}",
                "",
                "3D Review Overlay:",
                f"- {overlay_line or 'Not shown.'}",
                "",
                "Next planned actions:",
                "- review the 3D overlay for point, legs, and control spans",
                "- rebuild Sections so intersection context can be carried downstream",
                "- check Build Parametric diagnostics for intersection-controlled Regions",
            ]
        )
        self._status.setPlainText("\n".join(lines))

    def _source_completeness_rows(self, control_regions: list[dict[str, object]], alignment_errors: list[str]) -> list[dict[str, object]]:
        model = None
        if not alignment_errors and control_regions:
            try:
                model = build_intersection_model_from_sources(
                    intersection_kind=self.selected_intersection_kind(),
                    source_mode=self.selected_source_mode(),
                    primary_alignment_ref=self.selected_primary_alignment_ref(),
                    secondary_alignment_ref=self.selected_secondary_alignment_ref(),
                    control_region_choices=control_regions,
                    detection_result=getattr(self, "_last_detection", None),
                    project_id=_project_id(find_project(self.document)),
                )
            except Exception:
                model = None
        return intersection_source_completeness_rows(
            model,
            alignment_errors=alignment_errors,
            control_region_count=len(control_regions),
        )

    def _preview_sequence_rows(
        self,
        control_regions: list[dict[str, object]],
        alignment_errors: list[str],
        source_stage_rows: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        model = None
        if not alignment_errors and control_regions:
            try:
                model = build_intersection_model_from_sources(
                    intersection_kind=self.selected_intersection_kind(),
                    source_mode=self.selected_source_mode(),
                    primary_alignment_ref=self.selected_primary_alignment_ref(),
                    secondary_alignment_ref=self.selected_secondary_alignment_ref(),
                    control_region_choices=control_regions,
                    detection_result=getattr(self, "_last_detection", None),
                    project_id=_project_id(find_project(self.document)),
                )
            except Exception:
                model = None
        return intersection_read_only_preview_rows(
            model,
            source_rows=source_stage_rows,
            alignment_errors=alignment_errors,
            control_region_count=len(control_regions),
        )

    def _update_source_stage_table(self, rows: list[dict[str, object]]) -> None:
        table = getattr(self, "_source_stage_table", None)
        if table is None:
            return
        try:
            table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                diagnostics = "; ".join(list(row.get("diagnostics", []) or []))
                values = [
                    str(row.get("stage", "") or ""),
                    str(row.get("status", "") or ""),
                    str(row.get("approval_state", "") or ""),
                    str(int(row.get("count", 0) or 0)),
                    str(row.get("handoff_target", "") or ""),
                    diagnostics,
                ]
                for column, value in enumerate(values):
                    table.setItem(row_index, column, QtWidgets.QTableWidgetItem(value))
            table.resizeColumnsToContents()
        except Exception:
            pass

    def _update_preview_stage_table(self, rows: list[dict[str, object]]) -> None:
        table = getattr(self, "_preview_stage_table", None)
        if table is None:
            return
        try:
            table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                diagnostics = "; ".join(list(row.get("diagnostics", []) or []))
                values = [
                    str(row.get("stage", "") or ""),
                    str(row.get("status", "") or ""),
                    str(int(row.get("count", 0) or 0)),
                    str(row.get("contract", "") or ""),
                    diagnostics,
                ]
                for column, value in enumerate(values):
                    table.setItem(row_index, column, QtWidgets.QTableWidgetItem(value))
            table.resizeColumnsToContents()
        except Exception:
            pass

    def focus_source_stage(self, target: str) -> bool:
        rows = getattr(self, "_last_source_stage_rows", []) or []
        table = getattr(self, "_source_stage_table", None)
        for index, row in enumerate(rows):
            if not _source_stage_row_matches(row, target):
                continue
            self._update_status(prefix=f"Focused source stage: {row.get('stage', '')}")
            table = getattr(self, "_source_stage_table", None)
            if table is not None:
                try:
                    table.selectRow(index)
                    table.scrollToItem(table.item(index, 0))
                except Exception:
                    pass
            return True
        self._update_status(prefix=f"Source stage was not found: {target}")
        return False


class CmdV1IntersectionEditor:
    """Open the v1 Intersection source editor shell."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("intersections.svg"),
            "MenuText": "Intersections",
            "ToolTip": "Define v1 at-grade intersection type, source mode, and junction source intent",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_intersection_editor_command()


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


def _source_stage_row(
    stage: str,
    status: str,
    count: int,
    diagnostics: list[str] | tuple[str, ...],
    *,
    approval_states: list[str] | tuple[str, ...] = (),
    source_methods: list[str] | tuple[str, ...] = (),
) -> dict[str, object]:
    clean_diagnostics = _unique_text_values([str(item) for item in list(diagnostics or []) if str(item)])
    stage_id = _source_stage_id(stage)
    approval_state = _source_stage_approval_state(approval_states, status)
    clean_source_methods = _unique_text_values([str(item) for item in list(source_methods or []) if str(item)])
    return {
        "stage_id": stage_id,
        "stage": str(stage or ""),
        "status": str(status or "accepted"),
        "approval_state": approval_state,
        "source_methods": clean_source_methods,
        "count": int(count or 0),
        "diagnostics": clean_diagnostics,
        "handoff_target": f"intersection-source-stage:{stage_id}",
        "notes": "; ".join(clean_diagnostics),
    }


def _preview_stage_row(
    stage: str,
    status: str,
    count: int,
    contract: str,
    diagnostics: list[str] | tuple[str, ...],
) -> dict[str, object]:
    clean_diagnostics = _unique_text_values([str(item) for item in list(diagnostics or []) if str(item)])
    stage_id = _source_stage_id(stage)
    return {
        "stage_id": stage_id,
        "stage": str(stage or ""),
        "status": _preview_stage_status(status, clean_diagnostics),
        "count": int(count or 0),
        "contract": str(contract or ""),
        "diagnostics": clean_diagnostics,
        "handoff_target": f"intersection-preview-stage:{stage_id}",
        "notes": "; ".join(clean_diagnostics),
    }


def _preview_stage_status(status: str, diagnostics: list[str] | tuple[str, ...]) -> str:
    raw_status = str(status or "").strip()
    clean_diagnostics = [str(item) for item in list(diagnostics or []) if str(item)]
    if raw_status in {"error", "missing"}:
        return raw_status
    if any(item.startswith("error:") for item in clean_diagnostics):
        return "error"
    if raw_status in {"warning", "warn"}:
        return "warning"
    if any(item.startswith("warning:") for item in clean_diagnostics):
        return "warning"
    if raw_status in {"", "not_evaluated"}:
        return "missing"
    return "accepted"


def _result_stage_row(stage: str, rows: list[object], *, missing: str) -> dict[str, object]:
    if not rows:
        return _source_stage_row(stage, "missing", 0, [missing])
    diagnostics: list[str] = []
    statuses: list[str] = []
    approval_states: list[str] = []
    source_methods: list[str] = []
    for row in rows:
        statuses.append(str(getattr(row, "source_status", "") or getattr(row, "status", "") or "accepted"))
        approval_states.append(_source_stage_row_approval_status(row))
        source_methods.append(_source_stage_row_source_method(row))
        diagnostics.extend(str(item) for item in list(getattr(row, "source_diagnostic_rows", ()) or ()) if str(item))
        diagnostics.extend(str(item) for item in list(getattr(row, "diagnostic_rows", ()) or ()) if str(item))
        diagnostics.extend(_result_row_stage_metadata(row))
    return _source_stage_row(
        stage,
        _stage_status_from_statuses(statuses),
        len(rows),
        diagnostics,
        approval_states=approval_states,
        source_methods=source_methods,
    )


def _result_rows_stage_metadata(rows: list[object]) -> list[str]:
    diagnostics: list[str] = []
    for row in list(rows or []):
        diagnostics.extend(_result_row_stage_metadata(row))
    return diagnostics


def _result_row_stage_metadata(row: object) -> list[str]:
    diagnostics: list[str] = []
    handoff_target = str(getattr(row, "handoff_target", "") or "").strip()
    if handoff_target:
        diagnostics.append(f"handoff_target:{handoff_target}")
    source_lineage_status = str(getattr(row, "source_lineage_status", "") or "").strip()
    if source_lineage_status:
        diagnostics.append(f"source_lineage_status:{source_lineage_status}")
    return diagnostics


def _source_stage_row_approval_status(row: object) -> str:
    for attr_name in ("approval_status", "drainage_approval_status", "control_area_approval_status"):
        approval_status = str(getattr(row, attr_name, "") or "").strip()
        if approval_status:
            return approval_status
    return "accepted"


def _source_stage_row_source_method(row: object) -> str:
    for attr_name in ("source_method", "drainage_source_method", "control_area_source_method"):
        source_method = str(getattr(row, attr_name, "") or "").strip()
        if source_method:
            return source_method
    return ""


def _source_stage_row_from_source_rows(stage: str, rows: list[object], missing: str) -> dict[str, object]:
    if not rows:
        return _source_stage_row(stage, "missing", 0, [missing])
    diagnostics: list[str] = []
    statuses: list[str] = []
    approval_states: list[str] = []
    source_methods: list[str] = []
    for row in rows:
        approval_status = str(getattr(row, "approval_status", "") or "accepted")
        approval_states.append(approval_status)
        source_methods.append(str(getattr(row, "source_method", "") or ""))
        statuses.append("accepted" if approval_status in {"accepted", "locked"} else "warning")
        diagnostics.extend(str(item) for item in list(getattr(row, "diagnostic_rows", []) or []) if str(item))
        if approval_status not in {"accepted", "locked"}:
            diagnostics.append(f"source_approval_pending:{approval_status}")
    return _source_stage_row(
        stage,
        _stage_status_from_statuses(statuses),
        len(rows),
        diagnostics,
        approval_states=approval_states,
        source_methods=source_methods,
    )


def _stage_status_from_statuses(statuses: list[str]) -> str:
    clean = [str(status or "").strip() for status in statuses if str(status or "").strip()]
    if not clean:
        return "missing"
    if any(status == "error" or status == "missing" for status in clean):
        return "missing" if any(status == "missing" for status in clean) else "error"
    if any(status in {"warning", "warn", "candidate", "draft"} for status in clean):
        return "warning"
    return "accepted"


def _source_stage_id(stage: str) -> str:
    return str(stage or "").strip().lower().replace(" ", "_").replace("-", "_")


def _source_stage_approval_state(approval_states: list[str] | tuple[str, ...], status: str) -> str:
    states = _unique_text_values([str(item) for item in list(approval_states or []) if str(item)])
    if not states:
        return "missing" if str(status or "") == "missing" else "accepted"
    if any(state == "draft" for state in states):
        return "draft"
    if any(state not in {"accepted", "locked"} for state in states):
        return "review"
    if states and all(state == "locked" for state in states):
        return "locked"
    return "accepted"


def _source_stage_row_matches(row: dict[str, object], target: str) -> bool:
    wanted = str(target or "").strip()
    if not wanted:
        return False
    return wanted in {
        str(row.get("stage_id", "") or ""),
        str(row.get("stage", "") or ""),
        str(row.get("handoff_target", "") or ""),
    }


def _stage_count(rows: list[dict[str, object]], status: str) -> int:
    return len([row for row in list(rows or []) if str(row.get("status", "") or "") == str(status or "")])


def _first_source_stage_requiring_review(rows: list[dict[str, object]]) -> dict[str, object] | None:
    for wanted_status in ("error", "missing", "warning"):
        for row in list(rows or []):
            if str(row.get("status", "") or "") == wanted_status:
                return row
    return None


def _source_completeness_summary_notes(
    *,
    status: str,
    accepted_count: int,
    warning_count: int,
    missing_count: int,
    error_count: int,
    next_stage: str,
    next_diagnostic: str,
) -> str:
    base = (
        f"accepted={accepted_count}, warning={warning_count}, "
        f"missing={missing_count}, error={error_count}"
    )
    if str(status or "") == "accepted":
        return f"All source stages are accepted ({base})."
    if next_stage:
        return f"Review {next_stage}: {next_diagnostic or 'source stage requires attention'} ({base})."
    return f"Source stages require review ({base})."


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
) -> list[IntersectionLegRow]:
    rows: list[IntersectionLegRow] = []
    for index, row in enumerate(control_region_choices, start=1):
        start = float(row.get("station_start", 0.0) or 0.0)
        end = float(row.get("station_end", 0.0) or 0.0)
        region_id = str(row.get("region_id", "") or "")
        alignment_ref = str(row.get("alignment_ref", "") or "")
        rows.append(
            IntersectionLegRow(
                leg_id=f"{intersection_id}:leg:{index:02d}",
                intersection_id=intersection_id,
                leg_role=_leg_role_from_region_id(region_id, index),
                alignment_ref=alignment_ref,
                region_ref=str(row.get("control_region_ref", "") or ""),
                approach_station_start=min(start, end),
                approach_station_end=max(start, end),
                source_method="region_derived",
                approval_status="draft",
                span_source="control_region",
                arm_policy_ref=f"arm-policy:{intersection_id}:leg:{index:02d}",
                edge_policy_refs=[
                    f"edge-policy:{intersection_id}:leg:{index:02d}:pavement",
                    f"edge-policy:{intersection_id}:leg:{index:02d}:daylight",
                ],
                grading_policy_ref=f"grading:{intersection_id}:default",
                priority=index,
                diagnostic_rows=["leg_source_region_derived", "leg_approval_pending"],
                notes="Linked from intersection control Region.",
            )
        )
    return rows


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
                notes="Default intersection arm policy for future edge-network evaluation.",
            )
        )
    return rows


def _default_edge_policy_rows(intersection_id: str, leg_rows: list[IntersectionLegRow]) -> list[IntersectionEdgePolicyRow]:
    rows: list[IntersectionEdgePolicyRow] = []
    for index, leg in enumerate(list(leg_rows or []), start=1):
        leg_ref = str(getattr(leg, "leg_id", "") or "")
        edge_refs = [str(ref) for ref in list(getattr(leg, "edge_policy_refs", []) or []) if str(ref)]
        pavement_ref = edge_refs[0] if edge_refs else f"edge-policy:{intersection_id}:leg:{index:02d}:pavement"
        daylight_ref = edge_refs[1] if len(edge_refs) > 1 else f"edge-policy:{intersection_id}:leg:{index:02d}:daylight"
        rows.extend(
            [
                IntersectionEdgePolicyRow(
                    policy_id=pavement_ref,
                    intersection_id=intersection_id,
                    leg_ref=leg_ref,
                    edge_role="pavement_edge",
                    side="both",
                    offset_rule="lane_width_from_arm_policy",
                    elevation_rule="from_grading_policy",
                    source_policy_ref=str(getattr(leg, "arm_policy_ref", "") or ""),
                    edge_family_intent="lane",
                    source_method="subassembly_default",
                    approval_status="draft",
                    subassembly_kind="lane",
                    diagnostic_rows=["edge_family_subassembly_defaulted", "edge_family_approval_pending"],
                    notes="Pavement edge source policy for future intersection edge network.",
                ),
                IntersectionEdgePolicyRow(
                    policy_id=daylight_ref,
                    intersection_id=intersection_id,
                    leg_ref=leg_ref,
                    edge_role="daylight_hinge",
                    side="both",
                    offset_rule="assembly_daylight",
                    elevation_rule="from_surface_zone",
                    source_policy_ref=str(getattr(leg, "arm_policy_ref", "") or ""),
                    edge_family_intent="side_slope",
                    source_method="subassembly_default",
                    approval_status="draft",
                    subassembly_kind="side_slope",
                    diagnostic_rows=["edge_family_subassembly_defaulted", "edge_family_approval_pending"],
                    notes="Daylight hinge source policy for future intersection slope face zones.",
                ),
            ]
        )
    return rows


def _default_lane_connection_rows(
    intersection_id: str,
    intersection_kind: str,
    leg_rows: list[IntersectionLegRow],
) -> list[IntersectionLaneConnectionRow]:
    legs = [row for row in list(leg_rows or []) if str(getattr(row, "leg_id", "") or "")]
    if len(legs) < 2:
        return []
    rows: list[IntersectionLaneConnectionRow] = []
    for index, from_leg in enumerate(legs, start=1):
        to_leg = legs[index % len(legs)]
        from_leg_ref = str(getattr(from_leg, "leg_id", "") or "")
        to_leg_ref = str(getattr(to_leg, "leg_id", "") or "")
        movement_type = _default_lane_movement_type(intersection_kind, from_leg, to_leg, index)
        rows.append(
            IntersectionLaneConnectionRow(
                connection_id=f"lane-connection:{intersection_id}:{index:02d}",
                intersection_id=intersection_id,
                movement_type=movement_type,
                from_leg_ref=from_leg_ref,
                to_leg_ref=to_leg_ref,
                from_edge_policy_ref=_first_edge_policy_ref(from_leg),
                to_edge_policy_ref=_first_edge_policy_ref(to_leg),
                from_lane_index=1,
                to_lane_index=1,
                source_method="preset_default",
                approval_status="draft",
                diagnostic_rows=["lane_connection_source_defaulted", "lane_connection_approval_pending"],
                notes="Default first-slice lane connection source row for topology review.",
            )
        )
    return rows


def _default_lane_movement_type(
    intersection_kind: str,
    from_leg: IntersectionLegRow,
    to_leg: IntersectionLegRow,
    index: int,
) -> str:
    from_role = str(getattr(from_leg, "leg_role", "") or "").lower()
    to_role = str(getattr(to_leg, "leg_role", "") or "").lower()
    if "before" in from_role and "after" in to_role:
        return "through"
    if "after" in from_role and "before" in to_role:
        return "through"
    if str(intersection_kind or "") == "y_intersection":
        return "diverge" if index == 1 else "merge"
    return "turn"


def _first_edge_policy_ref(leg: IntersectionLegRow) -> str:
    refs = [str(ref) for ref in list(getattr(leg, "edge_policy_refs", []) or []) if str(ref)]
    return refs[0] if refs else ""


def _default_drainage_policy(
    intersection_id: str,
    edge_policy_rows: list[IntersectionEdgePolicyRow],
) -> IntersectionDrainagePolicyRow:
    gutter_refs = [
        str(getattr(row, "policy_id", "") or "")
        for row in list(edge_policy_rows or [])
        if str(getattr(row, "edge_role", "") or "") in {"gutter_edge", "pavement_edge"}
    ]
    return IntersectionDrainagePolicyRow(
        policy_id=f"drainage-policy:{intersection_id}:default",
        intersection_id=intersection_id,
        capture_mode="review_low_points",
        low_point_tolerance=0.05,
        gutter_edge_refs=[ref for ref in gutter_refs if ref],
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
    if kind == "urban_curb_gutter_intersection":
        return ("urban_quadrant_01", "urban_quadrant_02", "urban_quadrant_03", "urban_quadrant_04")
    if kind == "drainage_sag_intersection":
        return ("sag_quadrant_01", "sag_quadrant_02", "sag_quadrant_03", "sag_quadrant_04")
    if kind == "skewed_intersection":
        return ("skew_quadrant_01", "skew_quadrant_02", "skew_quadrant_03", "skew_quadrant_04")
    if kind == "y_intersection":
        return ("left_branch", "right_branch")
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
    elif kind == "skewed_intersection":
        radius = 11.0
    elif kind == "urban_curb_gutter_intersection":
        radius = 8.0
    elif kind == "drainage_sag_intersection":
        radius = 9.0
    elif kind == "y_intersection":
        radius = 15.0
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


def _intersection_review_point(detection_result):
    if detection_result is None or App is None:
        return None
    try:
        return App.Vector(
            float(getattr(detection_result, "x", 0.0) or 0.0),
            float(getattr(detection_result, "y", 0.0) or 0.0),
            0.0,
        )
    except Exception:
        return None


def _intersection_review_region_station_span(
    row: dict[str, object],
    *,
    detection_result=None,
    primary_alignment_ref: str = "",
    secondary_alignment_ref: str = "",
    max_span: float = INTERSECTION_REVIEW_MAX_REGION_SPAN,
) -> tuple[float, float]:
    start = float(row.get("station_start", 0.0) or 0.0)
    end = float(row.get("station_end", 0.0) or 0.0)
    low = min(start, end)
    high = max(start, end)
    span = high - low
    limit = max(float(max_span or 0.0), 1.0)
    if span <= limit:
        return (start, end)

    center = _intersection_review_station_for_alignment(
        str(row.get("alignment_ref", "") or ""),
        detection_result=detection_result,
        primary_alignment_ref=primary_alignment_ref,
        secondary_alignment_ref=secondary_alignment_ref,
        fallback=(low + high) * 0.5,
    )
    center = min(max(float(center), low), high)
    half = limit * 0.5
    clipped_low = max(low, center - half)
    clipped_high = min(high, center + half)
    if clipped_high - clipped_low < min(limit, span) - 1.0e-9:
        if clipped_low <= low + 1.0e-9:
            clipped_high = min(high, clipped_low + limit)
        elif clipped_high >= high - 1.0e-9:
            clipped_low = max(low, clipped_high - limit)
    return (clipped_low, clipped_high) if start <= end else (clipped_high, clipped_low)


def _intersection_review_station_for_alignment(
    alignment_ref: str,
    *,
    detection_result=None,
    primary_alignment_ref: str = "",
    secondary_alignment_ref: str = "",
    fallback: float = 0.0,
) -> float:
    if detection_result is None:
        return float(fallback)
    text = str(alignment_ref or "")
    if text and text == str(primary_alignment_ref or ""):
        return float(getattr(detection_result, "primary_station", fallback) or fallback)
    if text and text == str(secondary_alignment_ref or ""):
        return float(getattr(detection_result, "secondary_station", fallback) or fallback)
    return float(fallback)


def _intersection_point_marker_shapes(point, *, radius: float) -> list[object]:
    if App is None or Part is None or point is None:
        return []
    shapes: list[object] = []
    try:
        shapes.append(Part.makeSphere(max(float(radius) * 0.55, 0.5), point))
    except Exception:
        pass
    axes = (
        (App.Vector(radius, 0.0, 0.0), App.Vector(-radius, 0.0, 0.0)),
        (App.Vector(0.0, radius, 0.0), App.Vector(0.0, -radius, 0.0)),
        (App.Vector(0.0, 0.0, radius), App.Vector(0.0, 0.0, -radius)),
    )
    for positive, negative in axes:
        try:
            shapes.append(Part.makeLine(point + negative, point + positive))
        except Exception:
            pass
    return shapes


def _curb_return_preview_shapes(
    *,
    point,
    intersection_kind: str,
    radius: float | None = None,
    policy_ref: str = "",
    primary_alignment,
    secondary_alignment,
    detection_result=None,
) -> tuple[list[object], dict[str, object]]:
    if App is None or Part is None or point is None:
        return [], {
            "policy_ref": "",
            "radius": 0.0,
            "arc_count": 0,
            "diagnostics": ["intersection_curb_return_policy_missing: FreeCAD Part context and intersection point are required."],
        }
    kind = str(intersection_kind or "").strip() or "t_intersection"
    radius_value = _positive_radius_or_default(radius, kind)
    primary_station = float(getattr(detection_result, "primary_station", 0.0) or 0.0) if detection_result is not None else 0.0
    secondary_station = float(getattr(detection_result, "secondary_station", 0.0) or 0.0) if detection_result is not None else 0.0
    primary_dir = _alignment_tangent_at_station(primary_alignment, primary_station) or App.Vector(1.0, 0.0, 0.0)
    secondary_dir = _alignment_tangent_at_station(secondary_alignment, secondary_station) or App.Vector(0.0, 1.0, 0.0)
    primary_dir = _unit_vector(primary_dir) or App.Vector(1.0, 0.0, 0.0)
    secondary_dir = _unit_vector(secondary_dir) or App.Vector(0.0, 1.0, 0.0)
    quadrants = {
        "cross_intersection": ((1.0, 1.0), (1.0, -1.0), (-1.0, 1.0), (-1.0, -1.0)),
        "skewed_intersection": ((1.0, 1.0), (1.0, -1.0), (-1.0, 1.0), (-1.0, -1.0)),
        "urban_curb_gutter_intersection": ((1.0, 1.0), (1.0, -1.0), (-1.0, 1.0), (-1.0, -1.0)),
        "drainage_sag_intersection": ((1.0, 1.0), (1.0, -1.0), (-1.0, 1.0), (-1.0, -1.0)),
        "t_intersection": ((1.0, -1.0), (-1.0, -1.0)),
        "y_intersection": ((1.0, 1.0), (-1.0, 1.0)),
    }.get(kind, ((1.0, 1.0), (-1.0, 1.0)))
    shapes: list[object] = []
    diagnostics: list[str] = []
    sample_count = _curb_return_arc_sample_count(radius_value)
    for index, (primary_sign, secondary_sign) in enumerate(quadrants, start=1):
        arc_points = []
        denominator = max(sample_count - 1, 1)
        for step in range(sample_count):
            theta = (pi / 2.0) * (step / denominator)
            vector = _scaled_vector(primary_dir, primary_sign * radius_value * cos(theta)) + _scaled_vector(
                secondary_dir,
                secondary_sign * radius_value * sin(theta),
            )
            arc_points.append(point + vector)
        try:
            shapes.append(Part.makePolygon(arc_points))
        except Exception as exc:
            diagnostics.append(f"intersection_curb_return_radius_invalid: arc {index} could not be created: {exc}")
    if not shapes and not diagnostics:
        diagnostics.append("intersection_curb_return_policy_missing: no curb return arc could be created.")
    return shapes, {
        "policy_ref": str(policy_ref or f"curb-return:starter-{kind}:default"),
        "radius": radius_value,
        "arc_count": len(shapes),
        "diagnostics": diagnostics,
    }


def _positive_radius_or_default(radius: float | None, kind: str) -> float:
    try:
        value = float(radius)
    except Exception:
        value = 0.0
    if value > 0.0:
        return value
    if kind == "cross_intersection":
        return 10.0
    if kind == "skewed_intersection":
        return 11.0
    if kind == "urban_curb_gutter_intersection":
        return 8.0
    if kind == "drainage_sag_intersection":
        return 9.0
    if kind == "y_intersection":
        return 15.0
    return 12.0


def _intersection_model_curb_return_radius(intersection_model) -> float:
    for row in list(getattr(intersection_model, "curb_return_policy_rows", []) or []):
        try:
            value = float(getattr(row, "radius", 0.0) or 0.0)
        except Exception:
            continue
        if value > 0.0:
            return value
    kind = ""
    rows = list(getattr(intersection_model, "intersection_rows", []) or [])
    if rows:
        kind = str(getattr(rows[0], "intersection_kind", "") or "")
    return _positive_radius_or_default(None, kind)


def _intersection_model_curb_return_policy_ref(intersection_model) -> str:
    for row in list(getattr(intersection_model, "curb_return_policy_rows", []) or []):
        policy_ref = str(getattr(row, "policy_id", "") or "").strip()
        if policy_ref:
            return policy_ref
    return ""


def _intersection_model_design_vehicles(intersection_model) -> list[str]:
    return _unique_text_values(
        [
            str(getattr(row, "design_vehicle_ref", "") or "").strip()
            for row in list(getattr(intersection_model, "arm_policy_rows", []) or [])
        ]
    )


def _intersection_model_grading_modes(intersection_model) -> list[str]:
    return _unique_text_values(
        [
            str(getattr(row, "mode", "") or "").strip()
            for row in list(getattr(intersection_model, "grading_policy_rows", []) or [])
        ]
    )


def _intersection_model_drainage_modes(intersection_model) -> list[str]:
    return _unique_text_values(
        [
            str(getattr(row, "capture_mode", "") or "").strip()
            for row in list(getattr(intersection_model, "drainage_policy_rows", []) or [])
        ]
    )


def _intersection_model_control_area_ranges(intersection_model) -> list[str]:
    output = []
    for row in list(getattr(intersection_model, "control_area_rows", []) or []):
        alignment_ref = str(getattr(row, "alignment_ref", "") or "").strip()
        for start, end in list(getattr(row, "station_ranges", []) or []):
            try:
                output.append(f"{alignment_ref or '-'} | STA {float(start):.3f}-{float(end):.3f}")
            except Exception:
                continue
    return _unique_text_values(output)


def _curb_return_arc_sample_count(radius: float) -> int:
    arc_length = max(float(radius), 0.0) * (pi / 2.0)
    segment_count = int(ceil(arc_length / 2.0)) if arc_length > 0.0 else 4
    segment_count = max(4, min(segment_count, 48))
    return segment_count + 1


def _alignment_station_span_points(alignment_model, station_start: float, station_end: float) -> list[object]:
    if alignment_model is None or App is None:
        return []
    start = min(float(station_start), float(station_end))
    end = max(float(station_start), float(station_end))
    samples = [start, end]
    if end > start:
        step = max((end - start) / 6.0, 1.0)
        value = start + step
        while value < end - 1.0e-9:
            samples.append(value)
            value += step
    samples = sorted(set(round(value, 6) for value in samples))
    return [point for point in (_alignment_point_at_station(alignment_model, station) for station in samples) if point is not None]


def _alignment_point_at_station(alignment_model, station: float):
    if alignment_model is None or App is None:
        return None
    target = float(station)
    for element in list(getattr(alignment_model, "geometry_sequence", []) or []):
        start = float(getattr(element, "station_start", 0.0) or 0.0)
        end = float(getattr(element, "station_end", start) or start)
        if target < min(start, end) - 1.0e-6 or target > max(start, end) + 1.0e-6:
            continue
        points = _alignment_element_points(element)
        if len(points) < 2:
            continue
        length = max(float(getattr(element, "length", 0.0) or 0.0), abs(end - start))
        local = 0.0 if length <= 1.0e-9 else max(0.0, min(length, target - start))
        return _point_on_polyline(points, local)
    points = []
    for element in list(getattr(alignment_model, "geometry_sequence", []) or []):
        points.extend(_alignment_element_points(element))
    if not points:
        return None
    return points[0] if target <= 0.0 else points[-1]


def _alignment_element_points(element) -> list[object]:
    payload = dict(getattr(element, "geometry_payload", {}) or {})
    x_values = list(payload.get("x_values", []) or [])
    y_values = list(payload.get("y_values", []) or [])
    points = []
    for x, y in zip(x_values, y_values):
        try:
            points.append(App.Vector(float(x), float(y), 0.0))
        except Exception:
            continue
    return points


def _point_on_polyline(points: list[object], distance: float):
    if not points:
        return None
    remaining = max(float(distance), 0.0)
    for first, second in zip(points[:-1], points[1:]):
        segment = second - first
        length = float(getattr(segment, "Length", 0.0) or 0.0)
        if length <= 1.0e-9:
            continue
        if remaining <= length:
            return first + segment.multiply(remaining / length)
        remaining -= length
    return points[-1]


def _alignment_tangent_at_station(alignment_model, station: float):
    if alignment_model is None or App is None:
        return None
    before = _alignment_point_at_station(alignment_model, float(station) - 1.0)
    after = _alignment_point_at_station(alignment_model, float(station) + 1.0)
    if before is None or after is None:
        points = []
        for element in list(getattr(alignment_model, "geometry_sequence", []) or []):
            points.extend(_alignment_element_points(element))
        if len(points) >= 2:
            before = points[0]
            after = points[-1]
    if before is None or after is None:
        return None
    vector = after - before
    return vector if float(getattr(vector, "Length", 0.0) or 0.0) > 1.0e-9 else None


def _unit_vector(vector):
    if vector is None:
        return None
    length = float(getattr(vector, "Length", 0.0) or 0.0)
    if length <= 1.0e-9:
        return None
    return vector.multiply(1.0 / length)


def _scaled_vector(vector, scale: float):
    if App is None or vector is None:
        return None
    return App.Vector(
        float(getattr(vector, "x", 0.0) or 0.0) * float(scale),
        float(getattr(vector, "y", 0.0) or 0.0) * float(scale),
        float(getattr(vector, "z", 0.0) or 0.0) * float(scale),
    )


def _style_intersection_review_overlay(obj, *, visible: bool) -> None:
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = bool(visible)
            vobj.ShapeColor = (1.0, 0.72, 0.05)
            vobj.LineColor = (1.0, 0.72, 0.05)
            vobj.PointColor = (1.0, 0.72, 0.05)
            vobj.LineWidth = 7.0
            vobj.PointSize = 8.0
            vobj.Transparency = 0
    except Exception:
        pass


def _intersection_model_point(intersection_model):
    if App is None or intersection_model is None:
        return None
    rows = list(getattr(intersection_model, "intersection_rows", []) or [])
    if not rows:
        return None
    row = rows[0]
    try:
        return App.Vector(
            float(getattr(row, "intersection_point_x", 0.0) or 0.0),
            float(getattr(row, "intersection_point_y", 0.0) or 0.0),
            float(getattr(row, "intersection_point_z", 0.0) or 0.0),
        )
    except Exception:
        return None


def _intersection_model_primary_secondary_refs(intersection_model) -> tuple[str, str]:
    rows = list(getattr(intersection_model, "intersection_rows", []) or [])
    if not rows:
        return "", ""
    row = rows[0]
    secondaries = list(getattr(row, "secondary_alignment_refs", []) or [])
    return str(getattr(row, "primary_alignment_ref", "") or ""), str(secondaries[0] if secondaries else "")


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
            route_to_v1_tree(project, obj)
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
