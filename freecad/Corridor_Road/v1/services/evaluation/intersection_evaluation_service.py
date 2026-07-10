"""Intersection evaluation service for CorridorRoad v1."""

from __future__ import annotations

import math

from dataclasses import dataclass

from ...models.source.intersection_model import (
    IntersectionAnchorRow,
    IntersectionControlArea,
    IntersectionCornerRow,
    IntersectionCurbReturnPolicyRow,
    IntersectionEdgePolicyRow,
    IntersectionLaneConnectionRow,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
)
from ...models.result.intersection_edge_network import (
    IntersectionEdgeNetworkResult,
    IntersectionEdgeNetworkRow,
)
from ...models.result.intersection_boundary_loop import (
    IntersectionBoundaryLoopResult,
    IntersectionBoundaryLoopRow,
    IntersectionBoundarySegmentRow,
)
from ...models.result.intersection_grading_context import (
    IntersectionGradingContextResult,
    IntersectionGradingContextRow,
)
from ...models.result.intersection_corridor_clipping import (
    IntersectionCorridorClipResult,
    IntersectionCorridorClipRow,
)
from ...models.result.intersection_drainage_hint import (
    IntersectionDrainageHintResult,
    IntersectionDrainageHintRow,
)
from ...models.result.intersection_roundabout_approach_leg import (
    IntersectionRoundaboutApproachLegResult,
    IntersectionRoundaboutApproachLegRow,
)
from ...models.result.intersection_slope_face_loop import (
    IntersectionSlopeFaceLoopResult,
    IntersectionSlopeFaceLoopRow,
)
from ...models.result.intersection_surface_zone import (
    IntersectionSurfaceZoneResult,
    IntersectionSurfaceZoneRow,
)
from ...models.result.intersection_topology import (
    IntersectionTopologyAnchorRow,
    IntersectionTopologyCornerRow,
    IntersectionTopologyControlAreaRow,
    IntersectionTopologyLaneConnectionRow,
    IntersectionTopologyLegSpanRow,
    IntersectionTopologyResult,
)


_VALID_ANCHOR_SOURCE_METHODS = {"detected", "manual", "preset_default", "imported"}
_VALID_ANCHOR_APPROVAL_STATUSES = {"accepted", "locked", "draft", "missing"}
_VALID_LEG_SOURCE_METHODS = {"manual", "detected", "preset_default", "region_derived", "imported"}
_VALID_LEG_APPROVAL_STATUSES = {"accepted", "locked", "draft", "missing"}
_VALID_LEG_SPAN_SOURCES = {"explicit", "control_region", "preset_default", "detected", "imported"}
_VALID_CONTROL_AREA_SOURCE_METHODS = {"manual", "detected", "preset_default", "region_derived", "imported"}
_VALID_CONTROL_AREA_APPROVAL_STATUSES = {"accepted", "locked", "draft", "missing"}
_VALID_CONTROL_AREA_INTENT_STATUSES = {"intersection_owned", "region_derived", "preset_default"}
_VALID_CORNER_SOURCE_METHODS = {"manual", "detected", "preset_default", "imported"}
_VALID_CORNER_APPROVAL_STATUSES = {"accepted", "locked", "draft", "missing"}
_VALID_EDGE_POLICY_SOURCE_METHODS = {"manual", "detected", "preset_default", "subassembly", "subassembly_bridge", "subassembly_derived", "imported"}
_VALID_EDGE_POLICY_APPROVAL_STATUSES = {"accepted", "locked", "draft", "missing"}
_VALID_EDGE_FAMILY_INTENTS = {"lane", "shoulder", "gutter", "curb", "sidewalk", "ditch", "median", "side_slope", "pavement"}
_VALID_LANE_CONNECTION_SOURCE_METHODS = {"manual", "detected", "preset_default", "imported"}
_VALID_LANE_CONNECTION_APPROVAL_STATUSES = {"accepted", "locked", "draft", "missing"}
_VALID_LANE_CONNECTION_MOVEMENT_TYPES = {"through", "turn", "merge", "diverge", "terminate"}
_VALID_GRADING_POLICY_SOURCE_METHODS = {"manual", "detected", "preset_default", "imported"}
_VALID_GRADING_POLICY_APPROVAL_STATUSES = {"accepted", "locked", "draft", "missing"}
_VALID_GRADING_MODES = {"flatten_intersection", "keep_primary_crown", "blend_primary_side", "use_normal_superelevation", "roundabout_radial_crossfall"}
_VALID_GRADING_CROWN_BEHAVIORS = {"flatten", "preserve_primary_crown", "blend_primary_side_crowns", "normal_superelevation", "roundabout_radial"}
_VALID_GRADING_TIE_IN_RULES = {"blend_to_leg_profiles", "tie_to_primary_profile", "use_normal_profile", "radial_entry_exit_blend"}
_VALID_GRADING_CROSSFALL_TRANSITIONS = {"linear", "none", "normal_superelevation", "radial"}
_VALID_GRADING_LOW_POINT_STRATEGIES = {"review_low_points", "sag_low_point_review", "outside_gutter", "central_island", "none"}

_LEG_GRAPH_ROLE_ANGLE_DEG = {
    "primary_after": 0.0,
    "primary_before": 180.0,
    "primary_control": 0.0,
    "secondary_after": 90.0,
    "secondary_before": 270.0,
    "secondary_control": 90.0,
    "side_approach": 270.0,
    "skew_after": 60.0,
    "skew_before": 240.0,
    "urban_side_after": 90.0,
    "urban_side_before": 270.0,
    "sag_side_after": 90.0,
    "sag_side_before": 270.0,
    "primary_approach": 180.0,
    "left_branch": 120.0,
    "right_branch": 240.0,
}
_VALID_DRAINAGE_CAPTURE_MODES = {"review_low_points", "outside_gutter", "central_island", "curb_gutter_inlets", "sag_low_point_inlets"}
_VALID_DRAINAGE_INTENT_STATUSES = {"hint_only", "accepted", "source_owned", "draft", "missing"}
_VALID_DRAINAGE_SOURCE_METHODS = {"manual", "detected", "preset_default", "imported"}
_VALID_DRAINAGE_APPROVAL_STATUSES = {"accepted", "locked", "draft", "missing"}


@dataclass(frozen=True)
class IntersectionEvaluationResult:
    """Minimal resolved intersection context for a station."""

    station: float
    alignment_ref: str = ""
    active_intersection_id: str = ""
    active_control_area_id: str = ""
    active_leg_id: str = ""
    leg_role: str = ""
    control_region_refs: tuple[str, ...] = ()
    curb_return_policy_ref: str = ""
    turn_lane_policy_ref: str = ""
    grading_policy_ref: str = ""
    drainage_policy_ref: str = ""
    source_status: str = ""
    source_diagnostic_rows: tuple[str, ...] = ()
    diagnostic_rows: tuple[str, ...] = ()


@dataclass(frozen=True)
class IntersectionPatchPrerequisiteResult:
    """Readiness contract for a future intersection surface patch output."""

    status: str
    intersection_id: str = ""
    intersection_kind: str = ""
    alignment_refs: tuple[str, ...] = ()
    control_region_refs: tuple[str, ...] = ()
    control_area_refs: tuple[str, ...] = ()
    participating_alignment_count: int = 0
    control_region_count: int = 0
    applied_section_count: int = 0
    tie_in_edge_count: int = 0
    boundary_point_count: int = 0
    diagnostic_rows: tuple[str, ...] = ()


class IntersectionEvaluationService:
    """Resolve intersection control-area context from an intersection source model."""

    def evaluate_grading_context(
        self,
        intersection_model: IntersectionModel | None,
        surface_zone_result: IntersectionSurfaceZoneResult | None = None,
        *,
        intersection_id: str = "",
    ) -> IntersectionGradingContextResult:
        """Evaluate intersection grading/crossfall contracts from surface zones."""

        if intersection_model is None:
            return IntersectionGradingContextResult(
                schema_version=1,
                project_id="corridorroad-v1",
                status="error",
                diagnostic_rows=["error:intersection_model_missing"],
            )
        surface_zones = surface_zone_result or self.evaluate_surface_zones(intersection_model, intersection_id=intersection_id)
        diagnostics = list(getattr(surface_zones, "diagnostic_rows", []) or [])
        if str(getattr(surface_zones, "status", "") or "") == "error":
            return IntersectionGradingContextResult(
                schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
                project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
                grading_context_result_id=f"intersection-grading-context:{surface_zones.intersection_id or 'error'}",
                intersection_id=str(getattr(surface_zones, "intersection_id", "") or ""),
                intersection_kind=str(getattr(surface_zones, "intersection_kind", "") or ""),
                status="error",
                diagnostic_rows=diagnostics,
                source_refs=list(getattr(surface_zones, "source_refs", []) or []),
            )

        context_rows: list[IntersectionGradingContextRow] = []
        for index, zone in enumerate(list(getattr(surface_zones, "zone_rows", []) or []), start=1):
            policy_ref = str(getattr(zone, "vertical_policy_ref", "") or "")
            policy = _grading_policy_by_ref(intersection_model, policy_ref, surface_zones.intersection_id)
            row_diagnostics: list[str] = []
            if policy is None:
                row_diagnostics.append("warning:grading_policy_missing")
                diagnostics.append(f"warning:grading_policy_missing:{policy_ref or surface_zones.intersection_id}")
            mode = str(getattr(policy, "mode", "") or "use_normal_superelevation")
            source_method = str(getattr(policy, "source_method", "") or "manual")
            approval_status = str(getattr(policy, "approval_status", "") or "accepted")
            source_diagnostics: list[str] = []
            if policy is not None:
                for diagnostic in list(getattr(policy, "diagnostic_rows", []) or []):
                    text = str(diagnostic or "").strip()
                    if text:
                        source_diagnostics.append(text)
                if approval_status not in {"accepted", "locked"}:
                    source_diagnostics.append("source_grading_policy_approval_pending")
                if approval_status and approval_status not in _VALID_GRADING_POLICY_APPROVAL_STATUSES:
                    source_diagnostics.append("source_grading_policy_approval_status_unknown")
                if not source_method:
                    source_diagnostics.append("source_grading_policy_method_missing")
                elif source_method not in _VALID_GRADING_POLICY_SOURCE_METHODS:
                    source_diagnostics.append("source_grading_policy_method_unknown")
                if mode and mode not in _VALID_GRADING_MODES:
                    source_diagnostics.append("source_grading_policy_mode_unknown")
                if not str(getattr(policy, "crown_behavior", "") or "").strip():
                    source_diagnostics.append("source_grading_policy_crown_behavior_missing")
                elif str(getattr(policy, "crown_behavior", "") or "").strip() not in _VALID_GRADING_CROWN_BEHAVIORS:
                    source_diagnostics.append("source_grading_policy_crown_behavior_unknown")
                if not str(getattr(policy, "tie_in_rule", "") or "").strip():
                    source_diagnostics.append("source_grading_policy_tie_in_rule_missing")
                elif str(getattr(policy, "tie_in_rule", "") or "").strip() not in _VALID_GRADING_TIE_IN_RULES:
                    source_diagnostics.append("source_grading_policy_tie_in_rule_unknown")
                if not str(getattr(policy, "crossfall_transition", "") or "").strip():
                    source_diagnostics.append("source_grading_policy_crossfall_transition_missing")
                elif str(getattr(policy, "crossfall_transition", "") or "").strip() not in _VALID_GRADING_CROSSFALL_TRANSITIONS:
                    source_diagnostics.append("source_grading_policy_crossfall_transition_unknown")
                if not str(getattr(policy, "low_point_strategy", "") or "").strip():
                    source_diagnostics.append("source_grading_policy_low_point_strategy_missing")
                elif str(getattr(policy, "low_point_strategy", "") or "").strip() not in _VALID_GRADING_LOW_POINT_STRATEGIES:
                    source_diagnostics.append("source_grading_policy_low_point_strategy_unknown")
                for diagnostic in source_diagnostics:
                    diagnostics.append(f"warning:{diagnostic}:{str(getattr(policy, 'policy_id', '') or policy_ref)}")
            zone_role = str(getattr(zone, "design_zone_role", "") or getattr(zone, "zone_role", "") or "")
            crossfall_context = _intersection_crossfall_context(zone_role, mode)
            if crossfall_context == "intersection_override" and mode == "use_normal_superelevation":
                row_diagnostics.append("warning:intersection_zone_uses_normal_superelevation")
            row_diagnostics.extend(source_diagnostics)
            controlling_profile_ref = str(getattr(policy, "controlling_profile_ref", "") or "")
            profile_lineage_status = _grading_profile_lineage_status(controlling_profile_ref, policy)
            superelevation_source_ref = _grading_superelevation_source_ref(policy, crossfall_context)
            superelevation_source_status = _grading_superelevation_source_status(crossfall_context, superelevation_source_ref)
            fallback_status = _grading_fallback_status(policy, mode, source_diagnostics)
            vertical_handoff_status = _grading_vertical_handoff_status(
                crossfall_context,
                profile_lineage_status,
                fallback_status,
                source_diagnostics,
            )
            grading_source_status = _grading_source_status(source_diagnostics, vertical_handoff_status)
            context_rows.append(
                IntersectionGradingContextRow(
                    context_id=f"intersection-grading-context:{_id_token(surface_zones.intersection_id)}:{index:02d}",
                    intersection_id=surface_zones.intersection_id,
                    zone_ref=str(getattr(zone, "zone_id", "") or ""),
                    zone_role=zone_role,
                    surface_role=str(getattr(zone, "surface_role", "") or ""),
                    surface_priority=int(getattr(zone, "surface_priority", 0) or 0),
                    grading_policy_ref=policy_ref or str(getattr(policy, "policy_id", "") or ""),
                    source_grading_policy_ref=str(getattr(policy, "policy_id", "") or policy_ref or ""),
                    grading_mode=mode,
                    target_crossfall_percent=float(getattr(policy, "target_crossfall_percent", 0.0) or 0.0),
                    crossfall_context=crossfall_context,
                    controlling_profile_ref=controlling_profile_ref,
                    profile_lineage_status=profile_lineage_status,
                    profile_handoff_status=_grading_profile_handoff_status(profile_lineage_status, source_diagnostics),
                    superelevation_source_ref=superelevation_source_ref,
                    superelevation_source_status=superelevation_source_status,
                    superelevation_handoff_status=_grading_superelevation_handoff_status(superelevation_source_status),
                    vertical_handoff_status=vertical_handoff_status,
                    handoff_target=f"intersection-preview-stage:grading:{_id_token(str(getattr(zone, 'zone_id', '') or str(index)))}",
                    grading_source_scope="normal_superelevation" if crossfall_context == "normal_superelevation" else "intersection_policy",
                    fallback_status=fallback_status,
                    crown_behavior=str(getattr(policy, "crown_behavior", "") or ""),
                    tie_in_rule=str(getattr(policy, "tie_in_rule", "") or ""),
                    crossfall_transition=str(getattr(policy, "crossfall_transition", "") or ""),
                    low_point_strategy=str(getattr(policy, "low_point_strategy", "") or ""),
                    source_method=source_method,
                    approval_status=approval_status,
                    source_status=grading_source_status,
                    source_diagnostic_rows=tuple(source_diagnostics),
                    primary_alignment_ref=str(getattr(policy, "primary_alignment_ref", "") or ""),
                    secondary_alignment_refs=tuple(str(ref) for ref in list(getattr(policy, "secondary_alignment_refs", []) or []) if str(ref)),
                    alignment_refs=tuple(getattr(zone, "alignment_refs", ()) or ()),
                    control_area_refs=tuple(getattr(zone, "control_area_refs", ()) or ()),
                    status=grading_source_status if grading_source_status != "accepted" else ("warning" if row_diagnostics else "ready"),
                    diagnostic_rows=tuple(row_diagnostics),
                    notes=_grading_context_note(zone_role, mode, crossfall_context),
                )
            )

        if not context_rows:
            diagnostics.append("error:intersection_grading_context_rows_missing")
        status = _topology_status(diagnostics)
        return IntersectionGradingContextResult(
            schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
            project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
            label=f"Intersection Grading Context - {surface_zones.intersection_id}",
            grading_context_result_id=f"intersection-grading-context:{surface_zones.intersection_id or 'main'}",
            intersection_id=surface_zones.intersection_id,
            intersection_kind=surface_zones.intersection_kind,
            status=status,
            context_count=len(context_rows),
            intersection_override_count=len([row for row in context_rows if row.crossfall_context == "intersection_override"]),
            normal_superelevation_count=len([row for row in context_rows if row.crossfall_context == "normal_superelevation"]),
            warning_context_count=len([row for row in context_rows if row.status == "warning"]),
            diagnostic_rows=diagnostics,
            context_rows=context_rows,
            source_refs=list(getattr(surface_zones, "source_refs", []) or []),
        )

    def evaluate_drainage_hints(
        self,
        intersection_model: IntersectionModel | None,
        surface_zone_result: IntersectionSurfaceZoneResult | None = None,
        grading_context_result: IntersectionGradingContextResult | None = None,
        *,
        intersection_id: str = "",
    ) -> IntersectionDrainageHintResult:
        """Evaluate low-point and inlet recommendation hints from surface zones."""

        if intersection_model is None:
            return IntersectionDrainageHintResult(
                schema_version=1,
                project_id="corridorroad-v1",
                status="error",
                diagnostic_rows=["error:intersection_model_missing"],
            )
        surface_zones = surface_zone_result or self.evaluate_surface_zones(intersection_model, intersection_id=intersection_id)
        diagnostics = list(getattr(surface_zones, "diagnostic_rows", []) or [])
        if str(getattr(surface_zones, "status", "") or "") == "error":
            return IntersectionDrainageHintResult(
                schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
                project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
                drainage_hint_result_id=f"intersection-drainage-hints:{surface_zones.intersection_id or 'error'}",
                intersection_id=str(getattr(surface_zones, "intersection_id", "") or ""),
                intersection_kind=str(getattr(surface_zones, "intersection_kind", "") or ""),
                status="error",
                diagnostic_rows=diagnostics,
                source_refs=list(getattr(surface_zones, "source_refs", []) or []),
            )

        drainage_policy = _drainage_policy_for_intersection(
            intersection_model,
            str(getattr(surface_zones, "intersection_id", "") or intersection_id or ""),
        )
        drainage_policy_ref = str(getattr(drainage_policy, "policy_id", "") or "")
        drainage_mode = str(getattr(drainage_policy, "capture_mode", "") or "review_low_points")
        drainage_intent_status = str(getattr(drainage_policy, "intent_status", "") or "hint_only")
        drainage_source_method = str(getattr(drainage_policy, "source_method", "") or "manual")
        drainage_approval_status = str(getattr(drainage_policy, "approval_status", "") or "accepted")
        drainage_element_refs = tuple(str(ref) for ref in list(getattr(drainage_policy, "drainage_element_refs", []) or []) if str(ref))
        flow_route_refs = tuple(str(ref) for ref in list(getattr(drainage_policy, "flow_route_refs", []) or []) if str(ref))
        inlet_candidate_refs = tuple(str(ref) for ref in list(getattr(drainage_policy, "inlet_candidate_refs", []) or []) if str(ref))
        low_point_refs = tuple(str(ref) for ref in list(getattr(drainage_policy, "low_point_refs", []) or []) if str(ref))
        drainage_source_diagnostics = _drainage_policy_source_diagnostics(drainage_policy)
        for item in drainage_source_diagnostics:
            diagnostics.append(f"warning:{item}:{drainage_policy_ref or str(getattr(surface_zones, 'intersection_id', '') or '')}")
        if not drainage_policy_ref:
            diagnostics.append("warning:intersection_drainage_policy_missing")
            drainage_source_diagnostics = (*drainage_source_diagnostics, "source_drainage_policy_missing")
        drainage_handoff_status = _drainage_policy_handoff_status(
            drainage_intent_status,
            drainage_element_refs,
            flow_route_refs,
            drainage_source_diagnostics,
        )
        drainage_source_scope = _drainage_policy_source_scope(drainage_intent_status, drainage_handoff_status)
        accepted_drainage_ref = _accepted_drainage_ref(drainage_element_refs, flow_route_refs)
        drainage_review_status = _drainage_policy_review_status(drainage_handoff_status)
        drainage_source_lineage_status = _drainage_hint_source_lineage_status(
            drainage_intent_status,
            drainage_handoff_status,
            drainage_source_diagnostics,
        )
        drainage_source_status = _drainage_hint_source_status(
            drainage_handoff_status,
            drainage_source_diagnostics,
        )
        drainage_handoff_target = _drainage_hint_handoff_target(
            drainage_policy_ref,
            str(getattr(surface_zones, "intersection_id", "") or intersection_id or ""),
        )
        grading_context = grading_context_result or self.evaluate_grading_context(
            intersection_model,
            surface_zones,
            intersection_id=str(getattr(surface_zones, "intersection_id", "") or intersection_id or ""),
        )
        grading_context_by_zone = {
            str(getattr(row, "zone_ref", "") or ""): row
            for row in list(getattr(grading_context, "context_rows", []) or [])
            if str(getattr(row, "zone_ref", "") or "")
        }

        control_ranges = _control_area_station_ranges_by_id(
            intersection_model,
            str(getattr(surface_zones, "intersection_id", "") or intersection_id or ""),
        )
        hint_rows: list[IntersectionDrainageHintRow] = []
        zone_rows = list(getattr(surface_zones, "zone_rows", []) or [])
        for zone in zone_rows:
            design_role = str(getattr(zone, "design_zone_role", "") or "")
            zone_family = str(getattr(zone, "zone_family", "") or "")
            zone_ref = str(getattr(zone, "zone_id", "") or "")
            grading_row = grading_context_by_zone.get(zone_ref)
            if design_role in {"central_pavement", "roundabout_circulatory_lane"}:
                row_diagnostics = []
                if not drainage_policy_ref:
                    row_diagnostics.append("warning:low_point_hint_drainage_policy_missing")
                if drainage_mode in {"review_low_points", "outside_gutter", "central_island"}:
                    row_diagnostics.append("warning:low_point_requires_explicit_drainage_element_review")
                row_diagnostics.extend(f"warning:{item}" for item in drainage_source_diagnostics)
                hint_rows.append(
                    IntersectionDrainageHintRow(
                        hint_id=f"intersection-drainage-hint:{_id_token(surface_zones.intersection_id)}:low-point-{len(hint_rows) + 1:02d}",
                        intersection_id=surface_zones.intersection_id,
                        hint_kind="low_point_candidate",
                        zone_ref=zone_ref,
                        zone_role=design_role,
                        surface_role=str(getattr(zone, "surface_role", "") or ""),
                        recommended_element_kind="low_point_review",
                        drainage_policy_ref=drainage_policy_ref,
                        source_drainage_policy_ref=drainage_policy_ref,
                        drainage_mode=drainage_mode,
                        drainage_intent_status=drainage_intent_status,
                        drainage_source_method=drainage_source_method,
                        drainage_approval_status=drainage_approval_status,
                        drainage_element_refs=drainage_element_refs,
                        flow_route_refs=flow_route_refs,
                        inlet_candidate_refs=inlet_candidate_refs,
                        low_point_refs=low_point_refs,
                        drainage_handoff_status=drainage_handoff_status,
                        drainage_source_scope=drainage_source_scope,
                        accepted_drainage_ref=accepted_drainage_ref,
                        drainage_review_status=drainage_review_status,
                        source_lineage_status=drainage_source_lineage_status,
                        handoff_target=drainage_handoff_target,
                        grading_context_ref=str(getattr(grading_row, "context_id", "") or ""),
                        crossfall_context=str(getattr(grading_row, "crossfall_context", "") or ""),
                        control_area_refs=tuple(getattr(zone, "control_area_refs", ()) or ()),
                        source_edge_refs=tuple(getattr(zone, "source_edge_refs", ()) or ()),
                        boundary_edge_refs=tuple(getattr(zone, "boundary_edge_refs", ()) or ()),
                        station_ranges=_station_ranges_for_refs(control_ranges, getattr(zone, "control_area_refs", ()) or ()),
                        source_status=drainage_source_status,
                        source_diagnostic_rows=tuple(drainage_source_diagnostics),
                        status=drainage_source_status if drainage_source_status != "accepted" else ("warning" if row_diagnostics else "ready"),
                        diagnostic_rows=tuple(row_diagnostics),
                        notes=_drainage_hint_note("low_point_candidate", drainage_mode, design_role),
                    )
                )
            if design_role in {"curb_return_pavement", "roundabout_entry_exit_connector"} or zone_family == "slope":
                row_diagnostics = []
                if not drainage_policy_ref:
                    row_diagnostics.append("warning:inlet_recommendation_drainage_policy_missing")
                if not tuple(getattr(zone, "boundary_edge_refs", ()) or ()) and not tuple(getattr(zone, "source_edge_refs", ()) or ()):
                    row_diagnostics.append("warning:inlet_recommendation_boundary_edges_missing")
                if drainage_mode in {"outside_gutter", "central_island"}:
                    row_diagnostics.append("warning:inlet_candidate_requires_user_drainage_element")
                row_diagnostics.extend(f"warning:{item}" for item in drainage_source_diagnostics)
                hint_rows.append(
                    IntersectionDrainageHintRow(
                        hint_id=f"intersection-drainage-hint:{_id_token(surface_zones.intersection_id)}:inlet-{len(hint_rows) + 1:02d}",
                        intersection_id=surface_zones.intersection_id,
                        hint_kind="inlet_recommendation",
                        zone_ref=zone_ref,
                        zone_role=design_role or str(getattr(zone, "zone_role", "") or ""),
                        surface_role=str(getattr(zone, "surface_role", "") or ""),
                        recommended_element_kind="inlet",
                        drainage_policy_ref=drainage_policy_ref,
                        source_drainage_policy_ref=drainage_policy_ref,
                        drainage_mode=drainage_mode,
                        drainage_intent_status=drainage_intent_status,
                        drainage_source_method=drainage_source_method,
                        drainage_approval_status=drainage_approval_status,
                        drainage_element_refs=drainage_element_refs,
                        flow_route_refs=flow_route_refs,
                        inlet_candidate_refs=inlet_candidate_refs,
                        low_point_refs=low_point_refs,
                        drainage_handoff_status=drainage_handoff_status,
                        drainage_source_scope=drainage_source_scope,
                        accepted_drainage_ref=accepted_drainage_ref,
                        drainage_review_status=drainage_review_status,
                        source_lineage_status=drainage_source_lineage_status,
                        handoff_target=drainage_handoff_target,
                        grading_context_ref=str(getattr(grading_row, "context_id", "") or ""),
                        crossfall_context=str(getattr(grading_row, "crossfall_context", "") or ""),
                        control_area_refs=tuple(getattr(zone, "control_area_refs", ()) or ()),
                        source_edge_refs=tuple(getattr(zone, "source_edge_refs", ()) or ()),
                        boundary_edge_refs=tuple(getattr(zone, "boundary_edge_refs", ()) or ()),
                        station_ranges=_station_ranges_for_refs(control_ranges, getattr(zone, "control_area_refs", ()) or ()),
                        source_status=drainage_source_status,
                        source_diagnostic_rows=tuple(drainage_source_diagnostics),
                        status=drainage_source_status if drainage_source_status != "accepted" else ("warning" if row_diagnostics else "ready"),
                        diagnostic_rows=tuple(row_diagnostics),
                        notes=_drainage_hint_note("inlet_recommendation", drainage_mode, design_role or zone_family),
                    )
                )
        outlet_hints = _intersection_drainage_outlet_hint_rows(
            surface_zones,
            drainage_policy_ref=drainage_policy_ref,
            drainage_mode=drainage_mode,
            drainage_intent_status=drainage_intent_status,
            drainage_source_method=drainage_source_method,
            drainage_approval_status=drainage_approval_status,
            drainage_element_refs=drainage_element_refs,
            flow_route_refs=flow_route_refs,
            inlet_candidate_refs=inlet_candidate_refs,
            low_point_refs=low_point_refs,
            drainage_handoff_status=drainage_handoff_status,
            drainage_source_scope=drainage_source_scope,
            accepted_drainage_ref=accepted_drainage_ref,
            drainage_review_status=drainage_review_status,
            source_lineage_status=drainage_source_lineage_status,
            source_status=drainage_source_status,
            handoff_target=drainage_handoff_target,
            control_ranges=control_ranges,
            start_index=len(hint_rows) + 1,
        )
        hint_rows.extend(outlet_hints)

        if not hint_rows:
            diagnostics.append("warning:intersection_drainage_hint_rows_missing")
        if any(str(getattr(row, "status", "") or "") == "warning" for row in hint_rows):
            diagnostics.append("warning:intersection_drainage_hint_rows_require_review")
        status = _topology_status(diagnostics)
        missing_coverage_count = len(
            [
                row
                for row in hint_rows
                if any("requires_user_drainage_element" in item or "requires_explicit_drainage_element" in item for item in row.diagnostic_rows)
            ]
        )
        return IntersectionDrainageHintResult(
            schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
            project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
            label=f"Intersection Drainage Hints - {surface_zones.intersection_id}",
            drainage_hint_result_id=f"intersection-drainage-hints:{surface_zones.intersection_id or 'main'}",
            intersection_id=surface_zones.intersection_id,
            intersection_kind=surface_zones.intersection_kind,
            status=status,
            hint_row_count=len(hint_rows),
            low_point_hint_count=len([row for row in hint_rows if row.hint_kind == "low_point_candidate"]),
            inlet_recommendation_count=len([row for row in hint_rows if row.hint_kind == "inlet_recommendation"]),
            outlet_handoff_count=len([row for row in hint_rows if row.hint_kind == "outlet_handoff"]),
            missing_coverage_count=missing_coverage_count,
            accepted_handoff_count=len([row for row in hint_rows if row.drainage_handoff_status == "accepted_handoff"]),
            hint_only_count=len([row for row in hint_rows if row.drainage_handoff_status == "hint_only"]),
            review_required_count=len([row for row in hint_rows if row.drainage_review_status == "review_required"]),
            ready_hint_count=len([row for row in hint_rows if row.status == "ready"]),
            warning_hint_count=len([row for row in hint_rows if row.status == "warning"]),
            diagnostic_rows=diagnostics,
            hint_rows=hint_rows,
            source_refs=list(getattr(surface_zones, "source_refs", []) or []),
        )

    def evaluate_corridor_clipping(
        self,
        intersection_model: IntersectionModel | None,
        topology_result: IntersectionTopologyResult | None = None,
        surface_zone_result: IntersectionSurfaceZoneResult | None = None,
        *,
        intersection_id: str = "",
    ) -> IntersectionCorridorClipResult:
        """Evaluate ordinary-corridor clipping contracts from control areas."""

        if intersection_model is None:
            return IntersectionCorridorClipResult(
                schema_version=1,
                project_id="corridorroad-v1",
                status="error",
                diagnostic_rows=["error:intersection_model_missing"],
            )
        topology = topology_result or self.evaluate_topology(intersection_model, intersection_id=intersection_id)
        diagnostics = list(getattr(topology, "diagnostic_rows", []) or [])
        if str(getattr(topology, "status", "") or "") == "error":
            return IntersectionCorridorClipResult(
                schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
                project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
                clip_result_id=f"intersection-corridor-clipping:{topology.intersection_id or 'error'}",
                intersection_id=str(getattr(topology, "intersection_id", "") or ""),
                intersection_kind=str(getattr(topology, "intersection_kind", "") or ""),
                status="error",
                diagnostic_rows=diagnostics,
                source_refs=list(getattr(topology, "source_refs", []) or []),
            )

        surface_zones = surface_zone_result or self.evaluate_surface_zones(intersection_model, intersection_id=topology.intersection_id)
        zone_refs = tuple(str(row.zone_id) for row in list(getattr(surface_zones, "zone_rows", []) or []) if str(getattr(row, "zone_id", "") or ""))
        clip_rows: list[IntersectionCorridorClipRow] = []
        for index, control_area in enumerate(list(getattr(topology, "control_area_rows", []) or []), start=1):
            row_diagnostics = []
            if not control_area.station_ranges:
                row_diagnostics.append("warning:clip_control_area_station_range_missing")
                diagnostics.append(f"warning:clip_control_area_station_range_missing:{control_area.control_area_id}")
            if not control_area.control_region_refs:
                row_diagnostics.append("warning:clip_control_area_region_refs_missing")
                diagnostics.append(f"warning:clip_control_area_region_refs_missing:{control_area.control_area_id}")
            source_diagnostics = tuple(
                str(item)
                for item in [
                    *list(getattr(control_area, "source_diagnostic_rows", ()) or ()),
                    *row_diagnostics,
                ]
                if str(item)
            )
            for surface_role in ("design", "slope_face"):
                clip_rows.append(
                    IntersectionCorridorClipRow(
                        clip_id=(
                            f"intersection-clip:{_id_token(topology.intersection_id)}:"
                            f"{index:02d}:{_id_token(surface_role)}"
                        ),
                        intersection_id=topology.intersection_id,
                        control_area_ref=control_area.control_area_id,
                        alignment_ref=control_area.alignment_ref,
                        surface_role=surface_role,
                        station_ranges=control_area.station_ranges,
                        influence_ranges=control_area.influence_ranges,
                        control_region_refs=control_area.control_region_refs,
                        source_control_area_ref=str(getattr(control_area, "source_control_area_ref", "") or control_area.control_area_id),
                        control_area_intent_status=str(getattr(control_area, "intent_status", "") or "intersection_owned"),
                        control_area_source_method=str(getattr(control_area, "source_method", "") or "manual"),
                        control_area_approval_status=str(getattr(control_area, "approval_status", "") or "accepted"),
                        source_region_refs=tuple(getattr(control_area, "source_region_refs", ()) or ()),
                        result_region_refs=tuple(getattr(control_area, "result_region_refs", ()) or control_area.control_region_refs),
                        region_lineage_status=str(getattr(control_area, "region_lineage_status", "") or "result_only"),
                        protected_zone_refs=zone_refs,
                        source_status="warning" if source_diagnostics else "accepted",
                        source_diagnostic_rows=source_diagnostics,
                        status="warning" if row_diagnostics else "ready",
                        diagnostic_rows=tuple(row_diagnostics),
                        notes="Ordinary corridor surface must stop at the intersection control area before merge.",
                    )
                )

        if not clip_rows:
            diagnostics.append("error:intersection_corridor_clip_rows_missing")
        status = _topology_status(diagnostics)
        return IntersectionCorridorClipResult(
            schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
            project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
            label=f"Intersection Corridor Clipping - {topology.intersection_id}",
            clip_result_id=f"intersection-corridor-clipping:{topology.intersection_id or 'main'}",
            intersection_id=topology.intersection_id,
            intersection_kind=topology.intersection_kind,
            status=status,
            clip_row_count=len(clip_rows),
            design_clip_count=len([row for row in clip_rows if row.surface_role == "design"]),
            slope_clip_count=len([row for row in clip_rows if row.surface_role == "slope_face"]),
            ready_clip_count=len([row for row in clip_rows if row.status == "ready"]),
            warning_clip_count=len([row for row in clip_rows if row.status == "warning"]),
            diagnostic_rows=diagnostics,
            clip_rows=clip_rows,
            source_refs=list(getattr(topology, "source_refs", []) or []),
        )

    def evaluate_surface_zones(
        self,
        intersection_model: IntersectionModel | None,
        edge_network_result: IntersectionEdgeNetworkResult | None = None,
        *,
        intersection_id: str = "",
    ) -> IntersectionSurfaceZoneResult:
        """Evaluate surface-zone contracts from the intersection edge network."""

        if intersection_model is None:
            return IntersectionSurfaceZoneResult(
                schema_version=1,
                project_id="corridorroad-v1",
                status="error",
                diagnostic_rows=["error:intersection_model_missing"],
            )
        edge_network = edge_network_result or self.evaluate_edge_network(intersection_model, intersection_id=intersection_id)
        diagnostics = list(getattr(edge_network, "diagnostic_rows", []) or [])
        if str(getattr(edge_network, "status", "") or "") == "error":
            return IntersectionSurfaceZoneResult(
                schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
                project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
                surface_zone_result_id=f"intersection-surface-zones:{edge_network.intersection_id or 'error'}",
                intersection_id=str(getattr(edge_network, "intersection_id", "") or ""),
                intersection_kind=str(getattr(edge_network, "intersection_kind", "") or ""),
                status="error",
                diagnostic_rows=diagnostics,
                source_refs=list(getattr(edge_network, "source_refs", []) or []),
            )

        edge_rows = list(getattr(edge_network, "edge_rows", []) or [])
        pavement_edges = [row for row in edge_rows if str(getattr(row, "edge_role", "") or "") == "pavement_edge"]
        daylight_edges = [row for row in edge_rows if str(getattr(row, "edge_role", "") or "") == "daylight_hinge"]
        curb_edges = [row for row in edge_rows if str(getattr(row, "edge_family", "") or "") == "curb_return"]
        roundabout_edges = [row for row in edge_rows if str(getattr(row, "edge_family", "") or "") == "roundabout"]
        edge_by_id = {
            str(getattr(row, "edge_id", "") or ""): row
            for row in edge_rows
            if str(getattr(row, "edge_id", "") or "")
        }
        zone_rows: list[IntersectionSurfaceZoneRow] = []

        if len(_unique_text_values([row.alignment_ref for row in pavement_edges])) >= 2:
            source_edge_refs = tuple(str(row.edge_id) for row in pavement_edges)
            source_diagnostics = _surface_zone_source_diagnostics(source_edge_refs, edge_by_id)
            zone_rows.append(
                IntersectionSurfaceZoneRow(
                    zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:central-junction",
                    intersection_id=edge_network.intersection_id,
                    zone_role="central_junction",
                    zone_family="pavement",
                    design_zone_role="central_pavement",
                    surface_role="design",
                    source_edge_refs=source_edge_refs,
                    leg_refs=tuple(_unique_text_values([row.leg_ref for row in pavement_edges])),
                    alignment_refs=tuple(_unique_text_values([row.alignment_ref for row in pavement_edges])),
                    control_area_refs=tuple(_unique_text_values([row.control_area_ref for row in pavement_edges])),
                    vertical_policy_ref=_surface_zone_grading_policy_ref(intersection_model, edge_network.intersection_id),
                    surface_priority=_surface_priority("central_pavement"),
                    triangulation_method="pending_structured_zone",
                    source_status="warning" if source_diagnostics else "accepted",
                    source_diagnostic_rows=source_diagnostics,
                    status="candidate",
                    notes="Central junction zone contract only; no triangulation generated.",
                )
            )
        else:
            diagnostics.append("warning:surface_zone_central_junction_requires_two_pavement_alignments")

        for index, (leg_ref, edges) in enumerate(_edges_by_leg(pavement_edges).items(), start=1):
            design_zone_role = _design_zone_role_from_leg_edges(edges)
            source_edge_refs = tuple(str(row.edge_id) for row in edges)
            source_diagnostics = _surface_zone_source_diagnostics(source_edge_refs, edge_by_id)
            zone_rows.append(
                IntersectionSurfaceZoneRow(
                    zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:leg-pavement-{index:02d}",
                    intersection_id=edge_network.intersection_id,
                    zone_role="leg_pavement",
                    zone_family="pavement",
                    design_zone_role=design_zone_role,
                    surface_role="design",
                    source_edge_refs=source_edge_refs,
                    leg_refs=(leg_ref,),
                    alignment_refs=tuple(_unique_text_values([row.alignment_ref for row in edges])),
                    control_area_refs=tuple(_unique_text_values([row.control_area_ref for row in edges])),
                    vertical_policy_ref=_surface_zone_grading_policy_ref(intersection_model, edge_network.intersection_id),
                    surface_priority=_surface_priority(design_zone_role),
                    triangulation_method="pending_structured_strip",
                    source_status="warning" if source_diagnostics else "accepted",
                    source_diagnostic_rows=source_diagnostics,
                    status="candidate",
                    notes=f"{design_zone_role} contract only; no triangulation generated.",
                )
            )

        pavement_edges_by_leg = _edges_by_leg(pavement_edges)
        for index, edge in enumerate(curb_edges, start=1):
            curb_leg_refs = tuple(_unique_text_values(str(getattr(edge, "leg_ref", "") or "").split(",")))
            curb_context_edges = [context_edge for leg_ref in curb_leg_refs for context_edge in pavement_edges_by_leg.get(leg_ref, [])]
            source_edge_refs = (str(edge.edge_id),)
            source_diagnostics = _surface_zone_source_diagnostics(source_edge_refs, edge_by_id)
            zone_rows.append(
                IntersectionSurfaceZoneRow(
                    zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:curb-return-{index:02d}",
                    intersection_id=edge_network.intersection_id,
                    zone_role="curb_return",
                    zone_family="curb_return",
                    design_zone_role="curb_return_pavement",
                    surface_role="design",
                    source_edge_refs=source_edge_refs,
                    leg_refs=curb_leg_refs,
                    alignment_refs=tuple(_unique_text_values([row.alignment_ref for row in curb_context_edges])),
                    control_area_refs=tuple(_unique_text_values([row.control_area_ref for row in curb_context_edges])),
                    vertical_policy_ref=_surface_zone_grading_policy_ref(intersection_model, edge_network.intersection_id),
                    surface_priority=_surface_priority("curb_return_pavement"),
                    triangulation_method="pending_curb_return_fan",
                    source_status="warning" if source_diagnostics else "accepted",
                    source_diagnostic_rows=source_diagnostics,
                    status="candidate",
                    notes="curb_return_pavement contract only; no triangulation generated.",
                )
            )
        if not curb_edges:
            diagnostics.append("warning:surface_zone_curb_return_edges_missing")

        for index, edge in enumerate(daylight_edges, start=1):
            pavement_context_edges = pavement_edges_by_leg.get(str(getattr(edge, "leg_ref", "") or ""), [])
            curb_context_edges = _curb_edges_for_leg(edge, curb_edges)
            pavement_edge_refs = tuple(str(row.edge_id) for row in pavement_context_edges)
            curb_edge_refs = tuple(str(row.edge_id) for row in curb_context_edges)
            daylight_edge_ref = str(edge.edge_id)
            slope_diagnostics: list[str] = []
            if not pavement_edge_refs:
                slope_diagnostics.append("warning:slope_zone_matching_pavement_edge_missing")
                diagnostics.append(f"warning:slope_zone_matching_pavement_edge_missing:{edge.edge_id}")
            if not curb_edge_refs:
                slope_diagnostics.append("warning:slope_zone_curb_return_tie_edge_missing")
                diagnostics.append(f"warning:slope_zone_curb_return_tie_edge_missing:{edge.edge_id}")
            source_edge_refs = (daylight_edge_ref, *pavement_edge_refs, *curb_edge_refs)
            source_diagnostics = _surface_zone_source_diagnostics(source_edge_refs, edge_by_id)
            slope_zone_ready = not slope_diagnostics and not source_diagnostics
            boundary_audit_note = _slope_zone_boundary_audit_note(
                daylight_edge_ref=daylight_edge_ref,
                pavement_edge_refs=pavement_edge_refs,
                curb_edge_refs=curb_edge_refs,
                source_edge_refs=source_edge_refs,
            )
            zone_rows.append(
                IntersectionSurfaceZoneRow(
                    zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:slope-face-{index:02d}",
                    intersection_id=edge_network.intersection_id,
                    zone_role="exterior_slope_face",
                    zone_family="slope",
                    design_zone_role="exterior_slope_face",
                    surface_role="slope_face",
                    source_edge_refs=source_edge_refs,
                    boundary_edge_refs=source_edge_refs,
                    inner_edge_refs=pavement_edge_refs,
                    outer_edge_refs=(daylight_edge_ref,),
                    tie_edge_refs=curb_edge_refs,
                    leg_refs=(str(edge.leg_ref),),
                    alignment_refs=(str(edge.alignment_ref),) if str(edge.alignment_ref) else (),
                    control_area_refs=(str(edge.control_area_ref),) if str(edge.control_area_ref) else (),
                    surface_priority=_surface_priority("exterior_slope_face"),
                    triangulation_method="pending_daylight_zone",
                    surface_generation_role="surface_candidate" if slope_zone_ready else "diagnostic_only",
                    surface_generation_status="ready" if slope_zone_ready else "blocked",
                    source_status="warning" if source_diagnostics else "accepted",
                    source_diagnostic_rows=source_diagnostics,
                    status="ready" if slope_zone_ready else "warning",
                    diagnostic_rows=tuple([*slope_diagnostics, *source_diagnostics]),
                    notes=f"Slope-face zone boundary contract only; no triangulation generated. {boundary_audit_note}",
                )
            )
        if not daylight_edges:
            diagnostics.append("warning:surface_zone_daylight_edges_missing")

        zone_rows.extend(_roundabout_surface_zone_rows(intersection_model, edge_network, roundabout_edges))

        if not zone_rows:
            diagnostics.append("error:intersection_surface_zone_rows_missing")
        status = _topology_status(diagnostics)
        return IntersectionSurfaceZoneResult(
            schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
            project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
            label=f"Intersection Surface Zones - {edge_network.intersection_id}",
            surface_zone_result_id=f"intersection-surface-zones:{edge_network.intersection_id or 'main'}",
            intersection_id=edge_network.intersection_id,
            intersection_kind=edge_network.intersection_kind,
            status=status,
            zone_count=len(zone_rows),
            design_zone_count=len([row for row in zone_rows if row.surface_role == "design"]),
            pavement_zone_count=len([row for row in zone_rows if row.surface_role == "design"]),
            main_pavement_zone_count=len([row for row in zone_rows if row.design_zone_role == "main_pavement"]),
            side_pavement_zone_count=len([row for row in zone_rows if row.design_zone_role == "side_pavement"]),
            central_pavement_zone_count=len([row for row in zone_rows if row.design_zone_role == "central_pavement"]),
            curb_return_zone_count=len([row for row in zone_rows if row.zone_family == "curb_return"]),
            roundabout_zone_count=len([row for row in zone_rows if row.zone_family == "roundabout"]),
            slope_zone_count=len([row for row in zone_rows if row.zone_family == "slope"]),
            slope_zone_ready_count=len([row for row in zone_rows if row.zone_family == "slope" and row.status == "ready"]),
            slope_zone_warning_count=len([row for row in zone_rows if row.zone_family == "slope" and row.status == "warning"]),
            diagnostic_rows=diagnostics,
            zone_rows=zone_rows,
            source_refs=list(getattr(edge_network, "source_refs", []) or []),
        )

    def evaluate_boundary_loops(
        self,
        intersection_model: IntersectionModel | None,
        surface_zone_result: IntersectionSurfaceZoneResult | None = None,
        edge_network_result: IntersectionEdgeNetworkResult | None = None,
        slope_face_loop_result: IntersectionSlopeFaceLoopResult | None = None,
        applied_section_set=None,
        *,
        intersection_id: str = "",
    ) -> IntersectionBoundaryLoopResult:
        """Evaluate the authoritative outer boundary loop for an intersection."""

        if intersection_model is None:
            return IntersectionBoundaryLoopResult(
                schema_version=1,
                project_id="corridorroad-v1",
                status="error",
                diagnostic_rows=["error:intersection_model_missing"],
            )
        topology = self.evaluate_topology(intersection_model, intersection_id=intersection_id)
        edge_network = edge_network_result
        if edge_network is None:
            edge_network = self.evaluate_edge_network(intersection_model, topology, intersection_id=intersection_id)
        surface_zones = surface_zone_result or self.evaluate_surface_zones(
            intersection_model,
            edge_network,
            intersection_id=intersection_id,
        )
        diagnostics = list(getattr(surface_zones, "diagnostic_rows", []) or [])
        if str(getattr(topology, "intersection_kind", "") or "") == "roundabout":
            return _roundabout_boundary_loop_result(
                intersection_model,
                topology,
                surface_zones,
                edge_network,
                diagnostics=diagnostics,
            )
        edge_by_id = {
            str(getattr(edge, "edge_id", "") or ""): edge
            for edge in list(getattr(edge_network, "edge_rows", []) or [])
            if str(getattr(edge, "edge_id", "") or "")
        }
        candidate_edges: list[IntersectionEdgeNetworkRow] = []
        for zone in list(getattr(surface_zones, "zone_rows", []) or []):
            for edge_ref in tuple(getattr(zone, "boundary_edge_refs", ()) or ()):
                edge = edge_by_id.get(str(edge_ref or ""))
                if edge is not None:
                    candidate_edges.append(edge)
        if not candidate_edges:
            candidate_edges = list(getattr(edge_network, "edge_rows", []) or [])
            diagnostics.append("warning:intersection_boundary_loop_using_edge_network_fallback")
        candidate_edges, authoritative_edge_diagnostics = _intersection_boundary_authoritative_candidate_edges(
            candidate_edges
        )
        diagnostics.extend(authoritative_edge_diagnostics)

        candidate_points: list[tuple[tuple[float, float, float], str, tuple[str, ...]]] = []
        candidate_segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]] = []
        for edge in candidate_edges:
            edge_id = str(getattr(edge, "edge_id", "") or "")
            source_refs = tuple(
                value
                for value in (
                    edge_id,
                    str(getattr(edge, "source_policy_ref", "") or ""),
                    str(getattr(edge, "source_corner_ref", "") or ""),
                    str(getattr(edge, "leg_ref", "") or ""),
                    str(getattr(edge, "control_area_ref", "") or ""),
                )
                if value
            )
            start_point = _xyz_tuple_or_none(getattr(edge, "start_xyz", ()))
            end_point = _xyz_tuple_or_none(getattr(edge, "end_xyz", ()))
            edge_role = str(getattr(edge, "edge_role", "") or "")
            if (
                start_point is not None
                and end_point is not None
                and _intersection_boundary_key(start_point) != _intersection_boundary_key(end_point)
                and "internal" not in edge_role.lower()
            ):
                arc_points = _intersection_boundary_edge_arc_points(edge, start_point, end_point)
                if edge_role.lower() in {"curb_return", "curb_return_edge"} and len(arc_points) >= 3:
                    for arc_index, (arc_start, arc_end) in enumerate(zip(arc_points[:-1], arc_points[1:]), start=1):
                        if _intersection_boundary_key(arc_start) == _intersection_boundary_key(arc_end):
                            continue
                        candidate_segments.append(
                            (
                                arc_start,
                                arc_end,
                                f"{edge_id}:arc-segment:{arc_index:02d}",
                                "curb_return_arc_segment",
                                source_refs,
                            )
                        )
                    diagnostics.append(f"info:intersection_boundary_curb_return_arc_segments:{edge_id}:{max(0, len(arc_points) - 1)}")
                else:
                    candidate_segments.append((start_point, end_point, edge_id, edge_role, source_refs))
            for endpoint_role, xyz in (("start", getattr(edge, "start_xyz", ())), ("end", getattr(edge, "end_xyz", ()))):
                point = _xyz_tuple_or_none(xyz)
                if point is None:
                    diagnostics.append(f"warning:intersection_boundary_endpoint_missing:{edge_id}:{endpoint_role}")
                    continue
                candidate_points.append((point, f"{edge_id}:{endpoint_role}", source_refs))

        candidate_points = [
            row for row in candidate_points
            if not (
                abs(row[0][0]) <= 1.0e-9
                and abs(row[0][1]) <= 1.0e-9
                and abs(row[0][2]) <= 1.0e-9
            )
        ]
        loop_result = slope_face_loop_result
        if loop_result is None:
            loop_result = self.evaluate_slope_face_loops(intersection_model, surface_zones, edge_network, applied_section_set)
        slope_point_count, slope_segment_count = _intersection_boundary_slope_face_loop_candidate_counts(loop_result)
        if slope_point_count or slope_segment_count:
            diagnostics.append(
                "info:intersection_boundary_loop_slope_face_candidates_ignored:"
                f"points={slope_point_count};segments={slope_segment_count};"
                "reason=slope_face_loop_is_consumer_not_outer_boundary_source"
            )

        curb_envelope_points, curb_envelope_segments, curb_envelope_diagnostics = _intersection_boundary_construct_curb_return_envelope(
            topology
        )
        diagnostics.extend(curb_envelope_diagnostics)

        candidate_segments, excluded_segment_diagnostics = _intersection_boundary_filter_outer_candidate_segments(
            candidate_segments
        )
        diagnostics.extend(excluded_segment_diagnostics)
        diagnostics.extend(_intersection_boundary_candidate_graph_diagnostics(candidate_segments))

        using_curb_return_envelope = bool(curb_envelope_points)
        if using_curb_return_envelope:
            traced_points = curb_envelope_points
            traced_segments = curb_envelope_segments
        else:
            traced_points, traced_segments, trace_diagnostics = _intersection_boundary_construct_rectilinear_source_perimeter(
                candidate_segments
            )
            if not traced_points:
                fallback_points, fallback_segments, fallback_diagnostics = _intersection_boundary_trace_closed_segments(candidate_segments)
                traced_points, traced_segments = fallback_points, fallback_segments
                trace_diagnostics = [*trace_diagnostics, *fallback_diagnostics]
            diagnostics.extend(trace_diagnostics)
        hull_points = _intersection_boundary_convex_hull_xyz([point for point, _ref, _sources in candidate_points])
        using_fallback_hull = not traced_points
        intersection_kind = str(getattr(topology, "intersection_kind", "") or "")
        using_source_endpoint_hull = (
            using_fallback_hull
            and intersection_kind in {"y_intersection", "skewed_intersection"}
            and len(hull_points) >= 3
            and bool(candidate_points)
        )
        if using_fallback_hull and len(hull_points) >= 3 and not using_source_endpoint_hull:
            diagnostics.append("warning:intersection_boundary_convex_hull_fallback")
        loop_points = traced_points or hull_points
        loop_rows: list[IntersectionBoundaryLoopRow] = []
        segment_rows: list[IntersectionBoundarySegmentRow] = []
        if len(loop_points) < 3:
            diagnostics.append("error:intersection_boundary_loop_point_count_too_low")
        else:
            closed_points = list(loop_points)
            if not _points_closed_xy(closed_points):
                closed_points.append(closed_points[0])
            area_xy = abs(_intersection_boundary_area_xy(closed_points))
            bbox_xy = _intersection_boundary_bbox_xy(closed_points)
            loop_id = f"intersection-boundary-loop:{_id_token(str(getattr(edge_network, 'intersection_id', '') or 'main'))}:outer"
            source_refs = tuple(_unique_text_values([
                *[ref for _point, _pref, refs in candidate_points for ref in refs],
                *[ref for _first, _second, _seg_id, _role, refs in traced_segments for ref in refs],
            ]))
            consumer_roles = (
                "intersection_surface",
                "intersection_slope_face_surface",
                "design_surface",
                "slope_face_surface",
            )
            loop_diagnostics: list[str] = [
                "info:intersection_boundary_candidate_source=curb_return_envelope"
                if using_curb_return_envelope
                else "info:intersection_boundary_candidate_source=source_endpoint_hull"
                if using_source_endpoint_hull
                else "info:intersection_boundary_candidate_source=segment_graph"
                if not using_fallback_hull
                else "warning:intersection_boundary_convex_hull_fallback"
            ]
            if area_xy <= 1.0e-6:
                loop_diagnostics.append("error:intersection_boundary_loop_area_too_small")
                diagnostics.append(f"error:intersection_boundary_loop_area_too_small:{loop_id}")
            if _polyline_self_crosses_xy(closed_points):
                loop_diagnostics.append("error:intersection_boundary_loop_self_crossing")
                diagnostics.append(f"error:intersection_boundary_loop_self_crossing:{loop_id}")
            if using_fallback_hull and not using_source_endpoint_hull:
                loop_diagnostics.append("warning:intersection_boundary_loop_not_accepted_from_convex_hull")
            status = (
                "ready"
                if (not using_fallback_hull or using_source_endpoint_hull) and not any(item.startswith("error:") for item in loop_diagnostics)
                else "warning"
                if using_fallback_hull and not any(item.startswith("error:") for item in loop_diagnostics)
                else "error"
            )
            for index, (first, second) in enumerate(zip(closed_points, closed_points[1:]), start=1):
                traced_segment = traced_segments[index - 1] if index - 1 < len(traced_segments) else None
                role = (
                    _intersection_boundary_segment_role(first, second, closed_points)
                    if traced_segment is None
                    else _intersection_boundary_segment_role_from_edge_role(
                        traced_segment[3],
                        first,
                        second,
                        closed_points,
                        source_refs=traced_segment[4],
                    )
                )
                segment_id = f"{loop_id}:segment:{index:02d}"
                segment_rows.append(
                    IntersectionBoundarySegmentRow(
                        segment_id=segment_id,
                        intersection_id=str(getattr(edge_network, "intersection_id", "") or ""),
                        loop_ref=loop_id,
                        segment_role=role,
                        from_point_ref=f"{loop_id}:point:{index:02d}",
                        to_point_ref=f"{loop_id}:point:{(index % (len(closed_points) - 1)) + 1:02d}",
                        from_xyz=first,
                        to_xyz=second,
                        source_refs=source_refs if traced_segment is None else traced_segment[4],
                        expected_consumers=_intersection_boundary_expected_consumers(role),
                        shared_breakline_ref=f"shared-breakline:{_id_token(segment_id)}",
                        graph_edge_ref=f"intersection-shared-boundary-graph:{_id_token(segment_id)}",
                        diagnostics=("warning:convex_hull_fallback_segment",) if using_fallback_hull else (),
                        notes="Authoritative outer intersection boundary segment.",
                    )
                )
            loop_rows.append(
                IntersectionBoundaryLoopRow(
                    loop_id=loop_id,
                    intersection_id=str(getattr(edge_network, "intersection_id", "") or ""),
                    loop_role="outer_intersection_boundary",
                    status=status,
                    closed=_points_closed_xy(closed_points),
                    source_status="accepted" if status == "ready" else "fallback_warning" if status == "warning" else "warning",
                    point_count=max(0, len(closed_points) - 1),
                    segment_count=len(segment_rows),
                    area_xy=area_xy,
                    bbox_xy=bbox_xy,
                    source_refs=source_refs,
                    segment_refs=tuple(row.segment_id for row in segment_rows),
                    consumer_roles=consumer_roles,
                    loop_points_xyz=tuple(closed_points),
                    diagnostics=tuple(loop_diagnostics),
                    recommended_action=(
                        "Use this boundary loop as the intersection perimeter source for shared breaklines."
                        if status == "ready"
                        else "Repair Intersection control areas, edge network endpoints, and Applied Section boundary candidates before surface handoff."
                    ),
                    notes=(
                        "Authoritative cyan outer boundary loop candidate."
                        if status == "ready"
                        else "Diagnostic convex-hull fallback only; not accepted as authoritative perimeter."
                    ),
                )
            )

        ready_count = len([row for row in loop_rows if row.status == "ready"])
        error_count = len([row for row in loop_rows if row.status == "error"]) + len([row for row in diagnostics if str(row).startswith("error:")])
        warning_count = len([row for row in diagnostics if str(row).startswith("warning:")])
        status = "error" if error_count else ("warning" if warning_count else "ready")
        return IntersectionBoundaryLoopResult(
            schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
            project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
            label=f"Intersection Boundary Loops - {str(getattr(edge_network, 'intersection_id', '') or 'main')}",
            boundary_loop_result_id=f"intersection-boundary-loops:{str(getattr(edge_network, 'intersection_id', '') or 'main')}",
            intersection_id=str(getattr(edge_network, "intersection_id", "") or ""),
            intersection_kind=str(getattr(edge_network, "intersection_kind", "") or ""),
            status=status,
            loop_count=len(loop_rows),
            ready_count=ready_count,
            warning_count=warning_count,
            error_count=error_count,
            segment_count=len(segment_rows),
            diagnostic_rows=diagnostics,
            loop_rows=loop_rows,
            segment_rows=segment_rows,
            source_refs=list(getattr(surface_zones, "source_refs", []) or []),
        )

    def evaluate_slope_face_loops(
        self,
        intersection_model: IntersectionModel | None,
        surface_zone_result: IntersectionSurfaceZoneResult | None = None,
        edge_network_result: IntersectionEdgeNetworkResult | None = None,
        applied_section_set=None,
        *,
        intersection_id: str = "",
    ) -> IntersectionSlopeFaceLoopResult:
        """Evaluate source-traceable Slope Face loop candidates from surface zones."""

        if intersection_model is None:
            return IntersectionSlopeFaceLoopResult(
                schema_version=1,
                project_id="corridorroad-v1",
                status="error",
                diagnostic_rows=["error:intersection_model_missing"],
            )
        edge_network = edge_network_result
        if edge_network is None:
            topology = self.evaluate_topology(intersection_model, intersection_id=intersection_id)
            edge_network = self.evaluate_edge_network(intersection_model, topology, intersection_id=intersection_id)
        surface_zones = surface_zone_result or self.evaluate_surface_zones(intersection_model, edge_network, intersection_id=intersection_id)
        diagnostics = list(getattr(surface_zones, "diagnostic_rows", []) or [])
        edge_by_id = {
            str(getattr(edge, "edge_id", "") or ""): edge
            for edge in list(getattr(edge_network, "edge_rows", []) or [])
            if str(getattr(edge, "edge_id", "") or "")
        }
        if str(getattr(surface_zones, "status", "") or "") == "error":
            return IntersectionSlopeFaceLoopResult(
                schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
                project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
                loop_result_id=f"intersection-slope-face-loops:{surface_zones.intersection_id or 'error'}",
                intersection_id=str(getattr(surface_zones, "intersection_id", "") or ""),
                intersection_kind=str(getattr(surface_zones, "intersection_kind", "") or ""),
                status="error",
                diagnostic_rows=diagnostics,
                source_refs=list(getattr(surface_zones, "source_refs", []) or []),
            )

        loop_rows: list[IntersectionSlopeFaceLoopRow] = []
        slope_zones = [
            row for row in list(getattr(surface_zones, "zone_rows", []) or [])
            if str(getattr(row, "surface_role", "") or "") == "slope_face"
            or str(getattr(row, "zone_family", "") or "") == "slope"
        ]
        for index, zone in enumerate(slope_zones, start=1):
            loop_diagnostics = list(getattr(zone, "diagnostic_rows", ()) or ())
            source_edge_refs = tuple(str(value) for value in tuple(getattr(zone, "source_edge_refs", ()) or ()))
            source_surface_zone_refs = (str(getattr(zone, "zone_id", "") or ""),)
            zone_source_diagnostics = tuple(str(value) for value in tuple(getattr(zone, "source_diagnostic_rows", ()) or ()) if str(value))
            source_surface_zone_status = str(getattr(zone, "source_status", "") or ("warning" if zone_source_diagnostics else "accepted"))
            inner_edge_refs = tuple(str(value) for value in tuple(getattr(zone, "inner_edge_refs", ()) or ()))
            outer_edge_refs = tuple(str(value) for value in tuple(getattr(zone, "outer_edge_refs", ()) or ()))
            tie_edge_refs = tuple(str(value) for value in tuple(getattr(zone, "tie_edge_refs", ()) or ()))
            boundary_edge_refs = tuple(str(value) for value in tuple(getattr(zone, "boundary_edge_refs", ()) or ()))
            if not boundary_edge_refs:
                boundary_edge_refs = (*inner_edge_refs, *outer_edge_refs, *tie_edge_refs)
            source_applied_section_refs = _slope_face_loop_applied_section_refs(zone, applied_section_set)
            source_edge_network_status = _slope_face_loop_edge_network_status(source_edge_refs, edge_by_id)
            source_diagnostics = _unique_text_values(
                [
                    str(value)
                    for value in zone_source_diagnostics
                    if str(value)
                ]
                + list(_slope_face_loop_edge_source_diagnostics(source_edge_refs, edge_by_id))
            )
            source_lineage_status = _slope_face_loop_source_lineage_status(
                source_surface_zone_refs,
                source_edge_refs,
                source_surface_zone_status,
                source_edge_network_status,
                tuple(source_diagnostics),
            )
            if not inner_edge_refs:
                loop_diagnostics.append("warning:slope_face_loop_inner_edge_refs_missing")
                diagnostics.append(f"warning:slope_face_loop_inner_edge_refs_missing:{getattr(zone, 'zone_id', '')}")
            if not outer_edge_refs:
                loop_diagnostics.append("warning:slope_face_loop_outer_edge_refs_missing")
                diagnostics.append(f"warning:slope_face_loop_outer_edge_refs_missing:{getattr(zone, 'zone_id', '')}")
            if not tie_edge_refs:
                loop_diagnostics.append("warning:slope_face_loop_tie_edge_refs_missing")
                diagnostics.append(f"warning:slope_face_loop_tie_edge_refs_missing:{getattr(zone, 'zone_id', '')}")
            applied_boundary_edges, applied_boundary_refs, applied_boundary_diagnostics = _slope_face_loop_applied_section_boundary_edges(
                zone,
                applied_section_set,
            )
            edge_lookup = dict(edge_by_id)
            boundary_refs_for_graph = boundary_edge_refs
            applied_section_boundary_completion_used = False
            endpoint_graph = _slope_face_loop_endpoint_graph(boundary_refs_for_graph, edge_lookup)
            needs_boundary_completion = _slope_face_loop_graph_needs_boundary_completion(endpoint_graph)
            if needs_boundary_completion and applied_boundary_edges:
                for applied_edge in applied_boundary_edges:
                    edge_lookup[str(getattr(applied_edge, "edge_id", "") or "")] = applied_edge
                boundary_refs_for_graph = tuple(applied_boundary_refs)
                endpoint_graph = _slope_face_loop_endpoint_graph(boundary_refs_for_graph, edge_lookup)
                applied_section_boundary_completion_used = bool(
                    applied_boundary_refs
                    and not _slope_face_loop_graph_needs_boundary_completion(endpoint_graph)
                )
                if applied_section_boundary_completion_used:
                    boundary_edge_refs = boundary_refs_for_graph
                    source_applied_section_refs = tuple(
                        _unique_text_values(
                            [
                                *list(source_applied_section_refs),
                                *[
                                    item.strip()
                                    for edge in applied_boundary_edges
                                    for item in str(getattr(edge, "source_policy_ref", "") or "").split(",")
                                    if item.strip()
                                ],
                            ]
                        )
                    )
            for diagnostic in (applied_boundary_diagnostics if needs_boundary_completion else ()):
                if not str(diagnostic).startswith("info:") and diagnostic not in loop_diagnostics:
                    loop_diagnostics.append(diagnostic)
                diagnostics.append(f"{diagnostic}:{getattr(zone, 'zone_id', '')}")
            ordered_rings = _slope_face_loop_ordered_rings_from_graph(endpoint_graph)
            loop_points = (
                list(ordered_rings[0].get("points_xyz", ()) or ())
                if ordered_rings
                else _slope_face_loop_points_from_edges(boundary_refs_for_graph, edge_lookup)
            )
            missing_edge_refs = tuple(ref for ref in boundary_refs_for_graph if ref and ref not in edge_lookup)
            duplicate_edge_refs = _duplicate_text_values(boundary_edge_refs)
            dangling_endpoints = tuple(endpoint_graph.get("dangling_endpoint_rows", ()) or ())
            degenerate_edge_refs = tuple(str(ref) for ref in tuple(endpoint_graph.get("degenerate_edge_refs", ()) or ()) if str(ref))
            closed_xy = _points_closed_xy(loop_points)
            self_crossing = bool(closed_xy and _polyline_self_crosses_xy(loop_points))
            if missing_edge_refs:
                loop_diagnostics.append(
                    "error:slope_face_loop_boundary_edge_refs_unresolved:" + ",".join(missing_edge_refs)
                )
                diagnostics.append(
                    f"error:slope_face_loop_boundary_edge_refs_unresolved:{getattr(zone, 'zone_id', '')}:{','.join(missing_edge_refs)}"
                )
            if duplicate_edge_refs:
                loop_diagnostics.append(
                    "warning:slope_face_loop_duplicate_edge_refs:" + ",".join(duplicate_edge_refs)
                )
                diagnostics.append(
                    f"warning:slope_face_loop_duplicate_edge_refs:{getattr(zone, 'zone_id', '')}:{','.join(duplicate_edge_refs)}"
                )
            if degenerate_edge_refs:
                loop_diagnostics.append(
                    "warning:slope_face_loop_degenerate_edge_refs:" + ",".join(degenerate_edge_refs)
                )
                diagnostics.append(
                    f"warning:slope_face_loop_degenerate_edge_refs:{getattr(zone, 'zone_id', '')}:{','.join(degenerate_edge_refs)}"
                )
            for dangling in dangling_endpoints[:4]:
                dangling_edges = ",".join(str(value) for value in tuple(dangling.get("edge_refs", ()) or ()) if str(value))
                xyz = tuple(dangling.get("xyz", ()) or ())
                xyz_text = (
                    f"{float(xyz[0]):.3f},{float(xyz[1]):.3f},{float(xyz[2]):.3f}"
                    if len(xyz) >= 3
                    else ""
                )
                diagnostic = f"warning:slope_face_loop_dangling_endpoint:{dangling_edges}:xyz={xyz_text}"
                loop_diagnostics.append(diagnostic)
                diagnostics.append(f"{diagnostic}:{getattr(zone, 'zone_id', '')}")
            if len(loop_points) < 4:
                loop_diagnostics.append("warning:slope_face_loop_point_count_too_low")
                diagnostics.append(f"warning:slope_face_loop_point_count_too_low:{getattr(zone, 'zone_id', '')}:{len(loop_points)}")
            if loop_points and not closed_xy:
                loop_diagnostics.append("warning:slope_face_loop_open_xy")
                diagnostics.append(f"warning:slope_face_loop_open_xy:{getattr(zone, 'zone_id', '')}")
            if self_crossing:
                loop_diagnostics.append("error:slope_face_loop_self_crossing")
                diagnostics.append(f"error:slope_face_loop_self_crossing:{getattr(zone, 'zone_id', '')}")
            if not source_edge_refs:
                loop_diagnostics.append("warning:slope_face_loop_source_edge_refs_missing")
                diagnostics.append(f"warning:slope_face_loop_source_edge_refs_missing:{getattr(zone, 'zone_id', '')}")
            if len(ordered_rings) > 1 and not applied_section_boundary_completion_used:
                loop_diagnostics.append(f"warning:slope_face_loop_multiple_closed_rings:{len(ordered_rings)}")
                diagnostics.append(f"warning:slope_face_loop_multiple_closed_rings:{getattr(zone, 'zone_id', '')}:{len(ordered_rings)}")
            loop_note = "Slope Face loop candidate from surface-zone contract; no triangulation generated."
            if source_applied_section_refs:
                loop_note = (
                    f"{loop_note} applied_section_side_slope_refs="
                    f"{','.join(source_applied_section_refs)}"
                )
            if applied_section_boundary_completion_used:
                loop_note = f"{loop_note} applied_section_boundary_completion=used"
            loop_family = _slope_face_loop_family(zone)
            if applied_section_boundary_completion_used:
                loop_diagnostics = [
                    diagnostic for diagnostic in loop_diagnostics
                    if not _slope_face_loop_completion_supersedes_diagnostic(diagnostic)
                ]
                source_diagnostics = tuple(
                    diagnostic for diagnostic in tuple(source_diagnostics)
                    if not _slope_face_loop_completion_supersedes_diagnostic(diagnostic)
                )
                source_lineage_status = _slope_face_loop_source_lineage_status(
                    source_surface_zone_refs,
                    (*source_edge_refs, *boundary_refs_for_graph),
                    "accepted",
                    "accepted",
                    tuple(source_diagnostics),
                )
            status = "error" if any(str(item).startswith("error:") for item in loop_diagnostics) or source_lineage_status == "source_error" else (
                "ready" if not loop_diagnostics and source_lineage_status == "accepted" else "warning"
            )
            surface_generation_ready = (
                status == "ready"
                and (
                    applied_section_boundary_completion_used
                    or str(getattr(zone, "surface_generation_status", "") or "") == "ready"
                )
                and (
                    applied_section_boundary_completion_used
                    or str(getattr(zone, "surface_generation_role", "") or "") == "surface_candidate"
                )
            )
            surface_generation_role = "surface_candidate" if surface_generation_ready else "diagnostic_only"
            surface_generation_status = "ready" if surface_generation_ready else "blocked"
            loop_note = (
                f"{loop_note} surface_generation={surface_generation_role}:{surface_generation_status}"
            )
            loop_ring_rows = (
                ordered_rings
                if applied_section_boundary_completion_used and ordered_rings
                else [{"points_xyz": tuple(loop_points), "edge_refs": tuple(boundary_edge_refs)}]
            )
            for ring_index, ring in enumerate(loop_ring_rows, start=1):
                ring_points = list(ring.get("points_xyz", ()) or ())
                ring_edge_refs = tuple(str(ref) for ref in tuple(ring.get("edge_refs", ()) or ()) if str(ref))
                ring_closed_xy = _points_closed_xy(ring_points)
                ring_self_crossing = bool(ring_closed_xy and _polyline_self_crosses_xy(ring_points))
                ring_diagnostics = list(loop_diagnostics)
                if len(loop_ring_rows) > 1:
                    ring_diagnostics = [
                        diagnostic
                        for diagnostic in ring_diagnostics
                        if not str(diagnostic).startswith("warning:slope_face_loop_duplicate_edge_refs")
                    ]
                if len(ring_points) < 4 and "warning:slope_face_loop_point_count_too_low" not in ring_diagnostics:
                    ring_diagnostics.append("warning:slope_face_loop_point_count_too_low")
                if ring_points and not ring_closed_xy and "warning:slope_face_loop_open_xy" not in ring_diagnostics:
                    ring_diagnostics.append("warning:slope_face_loop_open_xy")
                if ring_self_crossing and "error:slope_face_loop_self_crossing" not in ring_diagnostics:
                    ring_diagnostics.append("error:slope_face_loop_self_crossing")
                ring_status = "error" if any(str(item).startswith("error:") for item in ring_diagnostics) or source_lineage_status == "source_error" else (
                    "ready" if not ring_diagnostics and source_lineage_status == "accepted" else "warning"
                )
                ring_surface_generation_ready = (
                    ring_status == "ready"
                    and (
                        applied_section_boundary_completion_used
                        or str(getattr(zone, "surface_generation_status", "") or "") == "ready"
                    )
                    and (
                        applied_section_boundary_completion_used
                        or str(getattr(zone, "surface_generation_role", "") or "") == "surface_candidate"
                    )
                )
                ring_surface_generation_role = "surface_candidate" if ring_surface_generation_ready else "diagnostic_only"
                ring_surface_generation_status = "ready" if ring_surface_generation_ready else "blocked"
                ring_loop_note = loop_note
                if len(loop_ring_rows) > 1:
                    ring_loop_note = f"{ring_loop_note} applied_section_boundary_ring={ring_index}/{len(loop_ring_rows)}"
                    if ring_surface_generation_role != surface_generation_role or ring_surface_generation_status != surface_generation_status:
                        ring_loop_note = ring_loop_note.replace(
                            f"surface_generation={surface_generation_role}:{surface_generation_status}",
                            f"surface_generation={ring_surface_generation_role}:{ring_surface_generation_status}",
                        )
                loop_id_suffix = f"{index:02d}" if len(loop_ring_rows) == 1 else f"{index:02d}-{ring_index:02d}"
                loop_rows.append(
                    IntersectionSlopeFaceLoopRow(
                        loop_id=f"intersection-slope-face-loop:{_id_token(surface_zones.intersection_id)}:{loop_id_suffix}",
                        intersection_id=str(getattr(surface_zones, "intersection_id", "") or ""),
                        loop_family=loop_family,
                        alignment_ref=str((tuple(getattr(zone, "alignment_refs", ()) or ("",))[0] if tuple(getattr(zone, "alignment_refs", ()) or ()) else "")),
                        leg_ref=str((tuple(getattr(zone, "leg_refs", ()) or ("",))[0] if tuple(getattr(zone, "leg_refs", ()) or ()) else "")),
                        side=_slope_face_loop_side(zone),
                        inner_edge_refs=inner_edge_refs,
                        outer_edge_refs=outer_edge_refs,
                        tie_edge_refs=tie_edge_refs,
                        boundary_edge_refs=ring_edge_refs or boundary_edge_refs,
                        loop_points_xyz=tuple(ring_points),
                        source_applied_section_refs=source_applied_section_refs,
                        source_edge_network_refs=source_edge_refs,
                        source_edge_network_status=source_edge_network_status,
                        source_surface_zone_refs=source_surface_zone_refs,
                        source_surface_zone_status=source_surface_zone_status,
                        source_status=_slope_face_loop_source_status(source_lineage_status),
                        source_diagnostic_rows=tuple(source_diagnostics),
                        source_lineage_status=source_lineage_status,
                        closed_xy=ring_closed_xy,
                        self_crossing=ring_self_crossing,
                        overlaps_intersection_surface=False,
                        point_count=len(ring_points),
                        surface_generation_role=ring_surface_generation_role,
                        surface_generation_status=ring_surface_generation_status,
                        status=ring_status,
                        diagnostics=tuple(ring_diagnostics),
                        notes=ring_loop_note,
                    )
                )
        if not slope_zones:
            diagnostics.append("warning:slope_face_loop_source_zones_missing")
        if not loop_rows:
            diagnostics.append("error:slope_face_loop_rows_missing")
        status = _topology_status(diagnostics)
        return IntersectionSlopeFaceLoopResult(
            schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
            project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
            label=f"Intersection Slope Face Loops - {surface_zones.intersection_id}",
            loop_result_id=f"intersection-slope-face-loops:{surface_zones.intersection_id or 'main'}",
            intersection_id=str(getattr(surface_zones, "intersection_id", "") or ""),
            intersection_kind=str(getattr(surface_zones, "intersection_kind", "") or ""),
            status=status,
            loop_count=len(loop_rows),
            ready_count=len([row for row in loop_rows if row.status == "ready"]),
            warning_count=len([row for row in loop_rows if row.status == "warning"]),
            error_count=len([row for row in loop_rows if row.status == "error"]),
            primary_outside_loop_count=len([row for row in loop_rows if row.loop_family == "primary_outside_loop"]),
            secondary_outside_loop_count=len([row for row in loop_rows if row.loop_family == "secondary_outside_loop"]),
            curb_return_loop_count=len([row for row in loop_rows if row.loop_family.startswith("curb_return")]),
            corner_gap_loop_count=len([row for row in loop_rows if row.loop_family == "corner_gap_loop"]),
            diagnostic_rows=diagnostics,
            loop_rows=loop_rows,
            source_refs=list(getattr(surface_zones, "source_refs", []) or []),
        )

    def evaluate_roundabout_approach_legs(
        self,
        intersection_model: IntersectionModel | None,
        topology_result: IntersectionTopologyResult | None = None,
        *,
        intersection_id: str = "",
    ) -> IntersectionRoundaboutApproachLegResult:
        """Evaluate four physical approach-leg contracts for roundabout builders."""

        if intersection_model is None:
            return IntersectionRoundaboutApproachLegResult(
                schema_version=1,
                project_id="corridorroad-v1",
                status="error",
                diagnostic_rows=["error:intersection_model_missing"],
            )
        topology = topology_result or self.evaluate_topology(intersection_model, intersection_id=intersection_id)
        diagnostics = list(getattr(topology, "diagnostic_rows", []) or [])
        intersection_kind = str(getattr(topology, "intersection_kind", "") or "")
        intersection_ref = str(getattr(topology, "intersection_id", "") or intersection_id or "")
        if intersection_kind != "roundabout":
            return IntersectionRoundaboutApproachLegResult(
                schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
                project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
                label=f"Roundabout Approach Legs - {intersection_ref or 'not-applicable'}",
                approach_leg_result_id=f"intersection-roundabout-approach-legs:{intersection_ref or 'not-applicable'}",
                intersection_id=intersection_ref,
                intersection_kind=intersection_kind,
                status="not_applicable",
                diagnostic_rows=[
                    *diagnostics,
                    f"info:roundabout_approach_leg_contract_not_applicable:{intersection_kind or 'unknown'}",
                ],
                source_refs=list(getattr(topology, "source_refs", []) or []),
            )
        if str(getattr(topology, "status", "") or "") == "error":
            return IntersectionRoundaboutApproachLegResult(
                schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
                project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
                label=f"Roundabout Approach Legs - {intersection_ref or 'error'}",
                approach_leg_result_id=f"intersection-roundabout-approach-legs:{intersection_ref or 'error'}",
                intersection_id=intersection_ref,
                intersection_kind=intersection_kind,
                status="error",
                diagnostic_rows=diagnostics,
                source_refs=list(getattr(topology, "source_refs", []) or []),
            )

        diagnostics.append("info:roundabout_approach_leg_contract_source=topology_leg_span_decomposition")
        rows = _roundabout_approach_leg_rows(intersection_model, topology, diagnostics=diagnostics)
        accepted_count = len([row for row in rows if row.status == "ready"])
        if not rows:
            diagnostics.append("error:roundabout_approach_leg_rows_missing")
        elif accepted_count < 4:
            diagnostics.append(f"warning:roundabout_approach_leg_count_below_four:{accepted_count}")
        alignment_count = len(_unique_text_values([str(getattr(row, "alignment_ref", "") or "") for row in rows]))
        status = "error" if any(str(item).startswith("error:roundabout_approach_leg") for item in diagnostics) else ("ready" if accepted_count >= 4 else "warning")
        return IntersectionRoundaboutApproachLegResult(
            schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
            project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
            label=f"Roundabout Approach Legs - {intersection_ref}",
            approach_leg_result_id=f"intersection-roundabout-approach-legs:{intersection_ref or 'main'}",
            intersection_id=intersection_ref,
            intersection_kind=intersection_kind,
            status=status,
            source_leg_count=len(list(getattr(topology, "leg_span_rows", []) or [])),
            approach_leg_count=len(rows),
            accepted_approach_leg_count=accepted_count,
            alignment_count=alignment_count,
            diagnostic_rows=diagnostics,
            approach_leg_rows=rows,
            source_refs=list(getattr(topology, "source_refs", []) or []),
        )

    def evaluate_edge_network(
        self,
        intersection_model: IntersectionModel | None,
        topology_result: IntersectionTopologyResult | None = None,
        *,
        intersection_id: str = "",
    ) -> IntersectionEdgeNetworkResult:
        """Evaluate deterministic edge rows from topology and source edge policies."""

        if intersection_model is None:
            return IntersectionEdgeNetworkResult(
                schema_version=1,
                project_id="corridorroad-v1",
                status="error",
                diagnostic_rows=["error:intersection_model_missing"],
            )
        topology = topology_result or self.evaluate_topology(intersection_model, intersection_id=intersection_id)
        diagnostics = list(getattr(topology, "diagnostic_rows", []) or [])
        if str(getattr(topology, "status", "") or "") == "error":
            return IntersectionEdgeNetworkResult(
                schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
                project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
                edge_network_result_id=f"intersection-edge-network:{topology.intersection_id or 'error'}",
                intersection_id=str(getattr(topology, "intersection_id", "") or ""),
                intersection_kind=str(getattr(topology, "intersection_kind", "") or ""),
                status="error",
                diagnostic_rows=diagnostics,
                source_refs=list(getattr(topology, "source_refs", []) or []),
            )

        edge_policy_by_id = {
            str(getattr(policy, "policy_id", "") or ""): policy
            for policy in list(getattr(intersection_model, "edge_policy_rows", []) or [])
            if str(getattr(policy, "policy_id", "") or "")
        }
        anchor_context = _intersection_edge_anchor_context(topology)
        edge_rows: list[IntersectionEdgeNetworkRow] = []
        for leg_index, leg_span in enumerate(list(getattr(topology, "leg_span_rows", []) or []), start=1):
            edge_refs = tuple(str(ref) for ref in list(getattr(leg_span, "edge_policy_refs", []) or []) if str(ref))
            if not edge_refs:
                diagnostics.append(f"warning:edge_network_leg_has_no_edge_policy_refs:{leg_span.leg_ref}")
            for edge_index, edge_ref in enumerate(edge_refs, start=1):
                policy = edge_policy_by_id.get(edge_ref)
                row_diagnostics: list[str] = []
                if policy is None:
                    row_diagnostics.append("source_edge_policy_ref_unresolved")
                    diagnostics.append(f"warning:edge_network_policy_ref_unresolved:{edge_ref}")
                policy_status = str(getattr(policy, "status", "") or "")
                if policy is not None and policy_status and policy_status != "active":
                    row_diagnostics.append(f"source_edge_policy_status:{policy_status}")
                    diagnostics.append(f"warning:source_edge_policy_status:{edge_ref}:{policy_status}")
                edge_family_intent = str(getattr(policy, "edge_family_intent", "") or "") if policy is not None else ""
                source_method = str(getattr(policy, "source_method", "") or "manual") if policy is not None else ""
                approval_status = str(getattr(policy, "approval_status", "") or "accepted") if policy is not None else ""
                subassembly_kind = str(getattr(policy, "subassembly_kind", "") or "") if policy is not None else ""
                if policy is not None:
                    source_policy_ref = str(getattr(policy, "source_policy_ref", "") or "")
                    for diagnostic in list(getattr(policy, "diagnostic_rows", []) or []):
                        text = str(diagnostic or "").strip()
                        if text:
                            row_diagnostics.append(text)
                    if not edge_family_intent:
                        row_diagnostics.append("source_edge_family_intent_missing")
                        diagnostics.append(f"warning:source_edge_family_intent_missing:{edge_ref}")
                    elif edge_family_intent not in _VALID_EDGE_FAMILY_INTENTS:
                        row_diagnostics.append("source_edge_family_intent_unknown")
                        diagnostics.append(f"warning:source_edge_family_intent_unknown:{edge_ref}:{edge_family_intent}")
                    if approval_status not in {"accepted", "locked"}:
                        row_diagnostics.append("source_edge_family_approval_pending")
                        diagnostics.append(f"warning:source_edge_family_approval_pending:{edge_ref}")
                    if approval_status and approval_status not in _VALID_EDGE_POLICY_APPROVAL_STATUSES:
                        row_diagnostics.append("source_edge_family_approval_status_unknown")
                        diagnostics.append(f"warning:source_edge_family_approval_status_unknown:{edge_ref}:{approval_status}")
                    if not source_method:
                        row_diagnostics.append("source_edge_family_method_missing")
                        diagnostics.append(f"warning:source_edge_family_method_missing:{edge_ref}")
                    elif source_method not in _VALID_EDGE_POLICY_SOURCE_METHODS:
                        row_diagnostics.append("source_edge_family_method_unknown")
                        diagnostics.append(f"warning:source_edge_family_method_unknown:{edge_ref}:{source_method}")
                    if source_method == "subassembly_bridge" and not source_policy_ref:
                        row_diagnostics.append("source_edge_family_source_policy_ref_missing")
                        diagnostics.append(f"error:source_edge_family_source_policy_ref_missing:{edge_ref}")
                    if source_method.startswith("subassembly") and not subassembly_kind:
                        row_diagnostics.append("source_edge_family_subassembly_kind_missing")
                        diagnostics.append(f"error:source_edge_family_subassembly_kind_missing:{edge_ref}")
                    if subassembly_kind and edge_family_intent and edge_family_intent in _VALID_EDGE_FAMILY_INTENTS and subassembly_kind != edge_family_intent:
                        row_diagnostics.append("source_edge_family_subassembly_kind_mismatch")
                        diagnostics.append(
                            f"error:source_edge_family_subassembly_kind_mismatch:{edge_ref}:{subassembly_kind}:{edge_family_intent}"
                        )
                edge_role = str(getattr(policy, "edge_role", "") or "")
                if not edge_role:
                    edge_role = _edge_role_from_policy_ref(edge_ref)
                side = str(getattr(policy, "side", "") or "both") if policy is not None else "both"
                edge_family_source_status = _edge_family_source_status(row_diagnostics)
                start_xyz, end_xyz = _intersection_leg_edge_endpoints(
                    leg_span,
                    edge_role=edge_role,
                    side=side,
                    policy=policy,
                    anchor_context=anchor_context,
                )
                endpoint_diagnostic = _edge_network_endpoint_diagnostic(
                    source_policy_ref=edge_ref,
                    leg_ref=str(getattr(leg_span, "leg_ref", "") or ""),
                    alignment_ref=str(getattr(leg_span, "alignment_ref", "") or ""),
                    control_area_ref=str(getattr(leg_span, "control_area_ref", "") or ""),
                    edge_family=_edge_family(edge_role),
                    station_start=float(getattr(leg_span, "station_start", 0.0) or 0.0),
                    station_end=float(getattr(leg_span, "station_end", 0.0) or 0.0),
                    start_xyz=start_xyz,
                    end_xyz=end_xyz,
                )
                if endpoint_diagnostic:
                    row_diagnostics.append(endpoint_diagnostic)
                    diagnostics.append(f"warning:{endpoint_diagnostic}")
                edge_rows.append(
                    IntersectionEdgeNetworkRow(
                        edge_id=_edge_network_row_id(topology.intersection_id, "leg", leg_index, edge_index, edge_role, side),
                        intersection_id=topology.intersection_id,
                        edge_role=edge_role,
                        edge_family=_edge_family(edge_role),
                        source_policy_ref=edge_ref,
                        leg_ref=leg_span.leg_ref,
                        leg_role=leg_span.leg_role,
                        alignment_ref=leg_span.alignment_ref,
                        control_area_ref=leg_span.control_area_ref,
                        side=side,
                        station_start=leg_span.station_start,
                        station_end=leg_span.station_end,
                        start_xyz=start_xyz,
                        end_xyz=end_xyz,
                        source_status=edge_family_source_status,
                        source_diagnostic_rows=tuple(row_diagnostics),
                        status=edge_family_source_status if edge_family_source_status != "accepted" else "ready",
                        notes="; ".join(row_diagnostics),
                    )
                )

        corner_by_id = _corner_rows_by_id(intersection_model, topology.intersection_id)
        leg_span_by_ref = {
            str(getattr(row, "leg_ref", "") or ""): row
            for row in list(getattr(topology, "leg_span_rows", []) or [])
            if str(getattr(row, "leg_ref", "") or "")
        }
        for policy_index, policy in enumerate(_curb_return_policies_for_intersection(intersection_model, topology.intersection_id), start=1):
            contact_station_refs = _curb_return_contact_station_refs(
                intersection_model,
                topology,
                policy,
            )
            corner_refs = [str(ref) for ref in list(getattr(policy, "corner_refs", []) or []) if str(ref)]
            curb_sources = _curb_return_corner_sources(policy, topology.intersection_kind, corner_by_id)
            if not corner_refs:
                diagnostics.append(f"warning:source_curb_return_corner_refs_missing:{getattr(policy, 'policy_id', '')}")
            for side_index, (side, corner_ref, corner) in enumerate(curb_sources, start=1):
                row_diagnostics: list[str] = []
                if float(getattr(policy, "radius", 0.0) or 0.0) <= 0.0:
                    row_diagnostics.append("source_curb_return_radius_missing")
                if not list(getattr(policy, "approach_leg_refs", []) or []):
                    row_diagnostics.append("source_curb_return_approach_leg_refs_missing")
                    diagnostics.append(f"warning:source_curb_return_approach_leg_refs_missing:{getattr(policy, 'policy_id', '')}")
                if not corner_ref:
                    row_diagnostics.append("source_curb_return_corner_ref_missing")
                elif corner is None:
                    row_diagnostics.append("source_curb_return_corner_ref_unresolved")
                    diagnostics.append(f"error:source_curb_return_corner_ref_unresolved:{getattr(policy, 'policy_id', '')}:{corner_ref}")
                else:
                    corner_status = str(getattr(corner, "approval_status", "") or "accepted")
                    corner_method = str(getattr(corner, "source_method", "") or "manual")
                    if corner_status not in {"accepted", "locked"}:
                        row_diagnostics.append("source_corner_approval_pending")
                        diagnostics.append(f"warning:source_corner_approval_pending:{corner_ref}")
                    if corner_status and corner_status not in _VALID_CORNER_APPROVAL_STATUSES:
                        row_diagnostics.append("source_corner_approval_status_unknown")
                        diagnostics.append(f"warning:source_corner_approval_status_unknown:{corner_ref}:{corner_status}")
                    if not corner_method:
                        row_diagnostics.append("source_corner_method_missing")
                        diagnostics.append(f"warning:source_corner_method_missing:{corner_ref}")
                    elif corner_method not in _VALID_CORNER_SOURCE_METHODS:
                        row_diagnostics.append("source_corner_method_unknown")
                        diagnostics.append(f"warning:source_corner_method_unknown:{corner_ref}:{corner_method}")
                    if not str(getattr(corner, "control_area_ref", "") or ""):
                        row_diagnostics.append("source_corner_control_area_ref_missing")
                        diagnostics.append(f"error:source_corner_control_area_ref_missing:{corner_ref}")
                    if not str(getattr(corner, "from_leg_ref", "") or ""):
                        row_diagnostics.append("source_corner_from_leg_ref_missing")
                        diagnostics.append(f"error:source_corner_from_leg_ref_missing:{corner_ref}")
                    if not str(getattr(corner, "to_leg_ref", "") or ""):
                        row_diagnostics.append("source_corner_to_leg_ref_missing")
                        diagnostics.append(f"error:source_corner_to_leg_ref_missing:{corner_ref}")
                    if not str(getattr(corner, "side", "") or getattr(corner, "quadrant", "") or ""):
                        row_diagnostics.append("source_corner_side_ref_missing")
                        diagnostics.append(f"error:source_corner_side_ref_missing:{corner_ref}")
                    corner_policy_ref = str(getattr(corner, "curb_return_policy_ref", "") or "")
                    policy_ref = str(getattr(policy, "policy_id", "") or "")
                    if not corner_policy_ref:
                        row_diagnostics.append("source_corner_curb_return_policy_ref_missing")
                        diagnostics.append(f"error:source_corner_curb_return_policy_ref_missing:{corner_ref}")
                    elif policy_ref and corner_policy_ref != policy_ref:
                        row_diagnostics.append("source_corner_curb_return_policy_ref_mismatch")
                        diagnostics.append(f"error:source_corner_curb_return_policy_ref_mismatch:{corner_ref}:{corner_policy_ref}:{policy_ref}")
                    for diagnostic in list(getattr(corner, "diagnostic_rows", []) or []):
                        text = str(diagnostic or "").strip()
                        if text:
                            row_diagnostics.append(text)
                corner_source_status = _corner_source_status(row_diagnostics)
                start_xyz, end_xyz = _intersection_curb_return_edge_endpoints(
                    corner=corner,
                    policy=policy,
                    leg_span_by_ref=leg_span_by_ref,
                    anchor_context=anchor_context,
                )
                arc_center_xyz = _xyz_tuple(anchor_context.get("anchor_xyz", (0.0, 0.0, 0.0)))
                arc_points_xyz = _intersection_curb_return_arc_points(
                    start_xyz,
                    end_xyz,
                    center_xyz=arc_center_xyz,
                    radius=float(getattr(policy, "radius", 0.0) or 0.0),
                )
                endpoint_diagnostic = _edge_network_endpoint_diagnostic(
                    source_policy_ref=str(getattr(policy, "policy_id", "") or ""),
                    leg_ref=",".join(str(ref) for ref in list(getattr(policy, "approach_leg_refs", []) or []) if str(ref)),
                    alignment_ref="",
                    control_area_ref=str(getattr(corner, "control_area_ref", "") or "") if corner is not None else "",
                    edge_family="curb_return",
                    station_start=0.0,
                    station_end=0.0,
                    start_xyz=start_xyz,
                    end_xyz=end_xyz,
                )
                if endpoint_diagnostic:
                    row_diagnostics.append(endpoint_diagnostic)
                    diagnostics.append(f"warning:{endpoint_diagnostic}")
                edge_rows.append(
                    IntersectionEdgeNetworkRow(
                        edge_id=_edge_network_row_id(topology.intersection_id, "curb-return", policy_index, side_index, "curb_return_edge", side),
                        intersection_id=topology.intersection_id,
                        edge_role="curb_return_edge",
                        edge_family="curb_return",
                        source_policy_ref=str(getattr(policy, "policy_id", "") or ""),
                        source_corner_ref=corner_ref,
                        leg_ref=",".join(str(ref) for ref in list(getattr(policy, "approach_leg_refs", []) or []) if str(ref)),
                        control_area_ref=str(getattr(corner, "control_area_ref", "") or "") if corner is not None else "",
                        side=side,
                        radius=float(getattr(policy, "radius", 0.0) or 0.0),
                        contact_station_refs=contact_station_refs,
                        start_xyz=start_xyz,
                        end_xyz=end_xyz,
                        arc_center_xyz=arc_center_xyz,
                        arc_points_xyz=arc_points_xyz,
                        source_status=corner_source_status,
                        source_diagnostic_rows=tuple(row_diagnostics),
                        status=corner_source_status if corner_source_status != "accepted" else "ready",
                        notes="; ".join(row_diagnostics),
                    )
                )
                if float(getattr(policy, "radius", 0.0) or 0.0) <= 0.0:
                    diagnostics.append(f"warning:curb_return_radius_missing:{getattr(policy, 'policy_id', '')}")

        if str(getattr(topology, "intersection_kind", "") or "") == "roundabout":
            edge_rows.extend(_roundabout_edge_network_rows(intersection_model, topology))
            diagnostics.append("warning:roundabout_edge_network_first_slice_source_only")

        if not edge_rows:
            diagnostics.append("error:intersection_edge_rows_missing")
        status = _topology_status(diagnostics)
        return IntersectionEdgeNetworkResult(
            schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
            project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
            label=f"Intersection Edge Network - {topology.intersection_id}",
            edge_network_result_id=f"intersection-edge-network:{topology.intersection_id or 'main'}",
            intersection_id=topology.intersection_id,
            intersection_kind=topology.intersection_kind,
            status=status,
            leg_edge_count=len([row for row in edge_rows if row.edge_family == "leg_edge"]),
            curb_return_edge_count=len([row for row in edge_rows if row.edge_family == "curb_return"]),
            daylight_edge_count=len([row for row in edge_rows if row.edge_role == "daylight_hinge"]),
            edge_count=len(edge_rows),
            diagnostic_rows=diagnostics,
            edge_rows=edge_rows,
            source_refs=list(getattr(topology, "source_refs", []) or []),
        )

    def evaluate_topology(
        self,
        intersection_model: IntersectionModel | None,
        *,
        intersection_id: str = "",
    ) -> IntersectionTopologyResult:
        """Evaluate source-level intersection topology before edge or surface generation."""

        if intersection_model is None:
            return IntersectionTopologyResult(
                schema_version=1,
                project_id="corridorroad-v1",
                status="error",
                diagnostic_rows=["error:intersection_model_missing"],
            )

        row = self._find_topology_intersection_row(intersection_model, intersection_id)
        if row is None:
            return IntersectionTopologyResult(
                schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
                project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
                topology_result_id="intersection-topology:missing",
                status="error",
                diagnostic_rows=["error:intersection_row_not_found"],
                source_refs=[str(getattr(intersection_model, "intersection_model_id", "") or "")],
            )

        diagnostics: list[str] = []
        leg_rows = list(getattr(row, "leg_rows", []) or [])
        source_refs = [str(getattr(intersection_model, "intersection_model_id", "") or "")]
        policy_refs = _unique_text_values(list(getattr(row, "policy_refs", []) or []))
        arm_policy_ids = {str(getattr(policy, "policy_id", "") or "") for policy in list(getattr(intersection_model, "arm_policy_rows", []) or [])}
        edge_policy_ids = {str(getattr(policy, "policy_id", "") or "") for policy in list(getattr(intersection_model, "edge_policy_rows", []) or [])}
        grading_policy_ids = {
            str(getattr(policy, "policy_id", "") or "")
            for policy in list(getattr(intersection_model, "grading_policy_rows", []) or [])
        }
        curb_return_policy_ids = {
            str(getattr(policy, "policy_id", "") or "")
            for policy in list(getattr(intersection_model, "curb_return_policy_rows", []) or [])
        }
        drainage_policy_ids = {
            str(getattr(policy, "policy_id", "") or "")
            for policy in list(getattr(intersection_model, "drainage_policy_rows", []) or [])
        }

        if not str(getattr(row, "intersection_kind", "") or ""):
            diagnostics.append("error:intersection_kind_missing")
        elif not row.is_supported_kind:
            diagnostics.append(f"warning:intersection_kind_not_first_slice_supported:{row.intersection_kind}")
        if not str(getattr(row, "primary_alignment_ref", "") or ""):
            diagnostics.append(f"error:source_intersection_primary_alignment_ref_missing:{row.intersection_id}")
        if not list(getattr(row, "secondary_alignment_refs", []) or []):
            diagnostics.append(f"error:source_intersection_secondary_alignment_refs_missing:{row.intersection_id}")
        if not list(getattr(row, "control_region_refs", []) or []):
            diagnostics.append(f"warning:source_intersection_control_region_refs_missing:{row.intersection_id}")
        if not curb_return_policy_ids:
            diagnostics.append(f"warning:source_intersection_curb_return_policy_rows_missing:{row.intersection_id}")
        if not grading_policy_ids:
            diagnostics.append(f"warning:source_intersection_grading_policy_rows_missing:{row.intersection_id}")
        if not drainage_policy_ids:
            diagnostics.append(f"warning:source_intersection_drainage_policy_rows_missing:{row.intersection_id}")

        if not leg_rows:
            diagnostics.append("error:intersection_leg_rows_missing")

        anchor_rows: list[IntersectionTopologyAnchorRow] = []
        for index, anchor in enumerate(self._anchor_rows_for_intersection(intersection_model, row.intersection_id), start=1):
            anchor_id = str(getattr(anchor, "anchor_id", "") or f"{row.intersection_id}:anchor:{index:02d}")
            source_method = str(getattr(anchor, "source_method", "") or "manual")
            approval_status = str(getattr(anchor, "approval_status", "") or "accepted")
            primary_alignment_ref = str(getattr(anchor, "primary_alignment_ref", "") or "")
            secondary_station_refs = tuple(
                (str(ref), float(station or 0.0))
                for ref, station in dict(getattr(anchor, "secondary_station_refs", {}) or {}).items()
                if str(ref)
            )
            anchor_diagnostics: list[str] = []
            for diagnostic in list(getattr(anchor, "diagnostic_rows", []) or []):
                text = str(diagnostic or "").strip()
                if text:
                    anchor_diagnostics.append(text)
                    diagnostics.append(f"warning:{text}:{anchor_id}")
            if approval_status not in {"accepted", "locked"}:
                anchor_diagnostics.append("source_anchor_approval_pending")
                diagnostics.append(f"warning:source_anchor_approval_pending:{anchor_id}:{approval_status or '-'}")
            if approval_status and approval_status not in _VALID_ANCHOR_APPROVAL_STATUSES:
                anchor_diagnostics.append("source_anchor_approval_status_unknown")
                diagnostics.append(f"warning:source_anchor_approval_status_unknown:{anchor_id}:{approval_status}")
            if not source_method:
                anchor_diagnostics.append("source_anchor_method_missing")
                diagnostics.append(f"warning:source_anchor_method_missing:{anchor_id}")
            elif source_method not in _VALID_ANCHOR_SOURCE_METHODS:
                anchor_diagnostics.append("source_anchor_method_unknown")
                diagnostics.append(f"warning:source_anchor_method_unknown:{anchor_id}:{source_method}")
            if not primary_alignment_ref:
                anchor_diagnostics.append("source_anchor_primary_alignment_ref_missing")
                diagnostics.append(f"error:source_anchor_primary_alignment_ref_missing:{anchor_id}")
            if primary_alignment_ref and primary_alignment_ref != str(getattr(row, "primary_alignment_ref", "") or ""):
                anchor_diagnostics.append("source_anchor_primary_alignment_ref_mismatch")
                diagnostics.append(f"warning:source_anchor_primary_alignment_ref_mismatch:{anchor_id}:{primary_alignment_ref}")
            if not secondary_station_refs and list(getattr(row, "secondary_alignment_refs", []) or []):
                anchor_diagnostics.append("source_anchor_secondary_station_refs_missing")
                diagnostics.append(f"warning:source_anchor_secondary_station_refs_missing:{anchor_id}")
            if float(getattr(anchor, "tolerance", 0.0) or 0.0) <= 0.0:
                anchor_diagnostics.append("source_anchor_tolerance_missing")
                diagnostics.append(f"warning:source_anchor_tolerance_missing:{anchor_id}")
            anchor_source_status = _anchor_source_status(anchor_diagnostics)
            anchor_rows.append(
                IntersectionTopologyAnchorRow(
                    anchor_result_id=f"{row.intersection_id}:anchor-result:{index:02d}",
                    source_anchor_ref=anchor_id,
                    intersection_id=str(getattr(anchor, "intersection_id", "") or row.intersection_id),
                    source_method=source_method,
                    approval_status=approval_status,
                    primary_alignment_ref=primary_alignment_ref,
                    primary_station=float(getattr(anchor, "primary_station", 0.0) or 0.0),
                    secondary_station_refs=secondary_station_refs,
                    station_lineage_status=_anchor_station_lineage_status(
                        primary_alignment_ref,
                        secondary_station_refs,
                        list(getattr(row, "secondary_alignment_refs", []) or []),
                        anchor_diagnostics,
                    ),
                    handoff_target=f"intersection-source-stage:anchor:{_id_token(anchor_id)}",
                    point_xyz=(
                        float(getattr(anchor, "point_x", 0.0) or 0.0),
                        float(getattr(anchor, "point_y", 0.0) or 0.0),
                        float(getattr(anchor, "point_z", 0.0) or 0.0),
                    ),
                    tolerance=float(getattr(anchor, "tolerance", 0.0) or 0.0),
                    source_status=anchor_source_status,
                    source_diagnostic_rows=tuple(anchor_diagnostics),
                    status=anchor_source_status if anchor_source_status != "accepted" else "ready",
                    notes="; ".join(anchor_diagnostics),
                )
            )
        if not anchor_rows:
            diagnostics.append(f"warning:source_intersection_anchor_rows_missing:{row.intersection_id}")

        leg_graph_rows, leg_graph_diagnostics, leg_graph_status = _topology_leg_graph_rows(leg_rows)
        diagnostics.extend(leg_graph_diagnostics)
        leg_graph_by_id = {
            str(getattr(leg, "leg_id", "") or ""): (order, angle_deg, angle_source)
            for leg, order, angle_deg, angle_source in leg_graph_rows
            if str(getattr(leg, "leg_id", "") or "")
        }
        leg_span_rows: list[IntersectionTopologyLegSpanRow] = []
        for index, leg in enumerate(leg_rows, start=1):
            leg_id = str(getattr(leg, "leg_id", "") or f"{row.intersection_id}:leg:{index:02d}")
            leg_graph_order, leg_graph_angle_deg, leg_graph_angle_source = leg_graph_by_id.get(
                leg_id,
                (index, 0.0, "source_order_fallback"),
            )
            alignment_ref = str(getattr(leg, "alignment_ref", "") or "")
            start = float(getattr(leg, "approach_station_start", 0.0) or 0.0)
            end = float(getattr(leg, "approach_station_end", 0.0) or 0.0)
            arm_policy_ref = str(getattr(leg, "arm_policy_ref", "") or "")
            edge_policy_refs = tuple(str(ref) for ref in list(getattr(leg, "edge_policy_refs", []) or []) if str(ref))
            grading_policy_ref = str(getattr(leg, "grading_policy_ref", "") or getattr(row, "grading_policy_ref", "") or "")
            source_method = str(getattr(leg, "source_method", "") or "manual")
            approval_status = str(getattr(leg, "approval_status", "") or "accepted")
            span_source = str(getattr(leg, "span_source", "") or "explicit")
            leg_diagnostics = []
            for diagnostic in list(getattr(leg, "diagnostic_rows", []) or []):
                diagnostic_text = str(diagnostic or "").strip()
                if diagnostic_text:
                    leg_diagnostics.append(diagnostic_text)
                    diagnostics.append(f"warning:{diagnostic_text}:{leg_id}")
            if approval_status not in {"accepted", "locked"}:
                leg_diagnostics.append("source_leg_approval_pending")
                diagnostics.append(f"warning:source_leg_approval_pending:{leg_id}:{approval_status or '-'}")
            if approval_status and approval_status not in _VALID_LEG_APPROVAL_STATUSES:
                leg_diagnostics.append("source_leg_approval_status_unknown")
                diagnostics.append(f"warning:source_leg_approval_status_unknown:{leg_id}:{approval_status}")
            if not source_method:
                leg_diagnostics.append("source_leg_method_missing")
                diagnostics.append(f"warning:source_leg_method_missing:{leg_id}")
            elif source_method not in _VALID_LEG_SOURCE_METHODS:
                leg_diagnostics.append("source_leg_method_unknown")
                diagnostics.append(f"warning:source_leg_method_unknown:{leg_id}:{source_method}")
            if not span_source:
                leg_diagnostics.append("source_leg_span_source_missing")
                diagnostics.append(f"warning:source_leg_span_source_missing:{leg_id}")
            elif span_source not in _VALID_LEG_SPAN_SOURCES:
                leg_diagnostics.append("source_leg_span_source_unknown")
                diagnostics.append(f"warning:source_leg_span_source_unknown:{leg_id}:{span_source}")
            elif span_source != "explicit":
                leg_diagnostics.append(f"source_leg_span_{span_source}")
                diagnostics.append(f"warning:source_leg_span_{span_source}:{leg_id}")
            if not alignment_ref:
                leg_diagnostics.append("missing_alignment")
                diagnostics.append(f"error:leg_missing_alignment_ref:{leg_id}")
            if not str(getattr(leg, "profile_ref", "") or ""):
                leg_diagnostics.append("source_leg_profile_ref_missing")
                diagnostics.append(f"warning:source_leg_profile_ref_missing:{leg_id}")
            if not str(getattr(leg, "centerline3d_ref", "") or ""):
                leg_diagnostics.append("source_leg_centerline3d_ref_missing")
                diagnostics.append(f"warning:source_leg_centerline3d_ref_missing:{leg_id}")
            if not str(getattr(leg, "region_ref", "") or ""):
                leg_diagnostics.append("source_leg_region_ref_missing")
                diagnostics.append(f"warning:source_leg_region_ref_missing:{leg_id}")
            if start == end:
                leg_diagnostics.append("zero_span")
                diagnostics.append(f"warning:leg_station_span_zero:{leg_id}")
            if arm_policy_ref and arm_policy_ref not in arm_policy_ids:
                leg_diagnostics.append("unresolved_arm_policy")
                diagnostics.append(f"warning:leg_arm_policy_ref_unresolved:{leg_id}:{arm_policy_ref}")
            if not arm_policy_ref:
                leg_diagnostics.append("missing_arm_policy")
                diagnostics.append(f"warning:leg_arm_policy_ref_missing:{leg_id}")
            for edge_ref in edge_policy_refs:
                if edge_ref not in edge_policy_ids:
                    leg_diagnostics.append("unresolved_edge_policy")
                    diagnostics.append(f"warning:leg_edge_policy_ref_unresolved:{leg_id}:{edge_ref}")
            if not edge_policy_refs:
                leg_diagnostics.append("missing_edge_policy")
                diagnostics.append(f"warning:leg_edge_policy_refs_missing:{leg_id}")
            if grading_policy_ref and grading_policy_ref not in grading_policy_ids:
                leg_diagnostics.append("unresolved_grading_policy")
                diagnostics.append(f"warning:leg_grading_policy_ref_unresolved:{leg_id}:{grading_policy_ref}")
            leg_source_status = _leg_source_status(leg_diagnostics)
            leg_span_rows.append(
                IntersectionTopologyLegSpanRow(
                    leg_span_id=f"{row.intersection_id}:leg-span:{index:02d}",
                    intersection_id=row.intersection_id,
                    leg_ref=leg_id,
                    leg_role=str(getattr(leg, "leg_role", "") or ""),
                    alignment_ref=alignment_ref,
                    region_ref=str(getattr(leg, "region_ref", "") or ""),
                    station_start=min(start, end),
                    station_end=max(start, end),
                    control_area_ref=_control_area_ref_for_alignment(intersection_model, row.intersection_id, alignment_ref),
                    arm_policy_ref=arm_policy_ref,
                    edge_policy_refs=edge_policy_refs,
                    grading_policy_ref=grading_policy_ref,
                    leg_graph_order=leg_graph_order,
                    leg_graph_angle_deg=leg_graph_angle_deg,
                    leg_graph_angle_source=leg_graph_angle_source,
                    applied_section_entry_ref="",
                    applied_section_exit_ref="",
                    applied_section_lineage_status="pending_applied_section_context",
                    source_method=source_method,
                    approval_status=approval_status,
                    span_source=span_source,
                    source_status=leg_source_status,
                    source_diagnostic_rows=tuple(leg_diagnostics),
                    status=leg_source_status if leg_source_status != "accepted" else "ready",
                    notes="; ".join(leg_diagnostics),
                )
            )

        corner_graph_rows, corner_graph_diagnostics, corner_graph_status = _topology_corner_graph_rows(
            intersection_model=intersection_model,
            intersection_id=row.intersection_id,
            intersection_kind=row.intersection_kind,
            leg_span_rows=leg_span_rows,
            anchor_rows=anchor_rows,
        )
        diagnostics.extend(corner_graph_diagnostics)

        control_area_rows: list[IntersectionTopologyControlAreaRow] = []
        for area in self._control_areas_for_intersection(intersection_model, row.intersection_id):
            station_ranges = _range_tuple(getattr(area, "station_ranges", []) or [])
            influence_ranges = _range_tuple(getattr(area, "influence_ranges", []) or [])
            control_region_refs = _unique_text_values(list(getattr(area, "control_region_refs", []) or []))
            source_region_refs = _unique_text_values(list(getattr(area, "source_region_refs", []) or []))
            source_method = str(getattr(area, "source_method", "") or "manual")
            approval_status = str(getattr(area, "approval_status", "") or "accepted")
            intent_status = str(getattr(area, "intent_status", "") or "intersection_owned")
            area_diagnostics = []
            for diagnostic in list(getattr(area, "diagnostic_rows", []) or []):
                text = str(diagnostic or "").strip()
                if text:
                    area_diagnostics.append(text)
                    diagnostics.append(f"warning:{text}:{area.control_area_id}")
            if not str(getattr(area, "alignment_ref", "") or ""):
                area_diagnostics.append("missing_alignment")
                diagnostics.append(f"error:control_area_missing_alignment_ref:{area.control_area_id}")
            if not station_ranges:
                area_diagnostics.append("missing_station_range")
                diagnostics.append(f"error:control_area_station_ranges_missing:{area.control_area_id}")
            if approval_status not in {"accepted", "locked"}:
                area_diagnostics.append("source_control_area_approval_pending")
                diagnostics.append(f"warning:source_control_area_approval_pending:{area.control_area_id}")
            if approval_status and approval_status not in _VALID_CONTROL_AREA_APPROVAL_STATUSES:
                area_diagnostics.append("source_control_area_approval_status_unknown")
                diagnostics.append(f"warning:source_control_area_approval_status_unknown:{area.control_area_id}:{approval_status}")
            if not source_method:
                area_diagnostics.append("source_control_area_method_missing")
                diagnostics.append(f"warning:source_control_area_method_missing:{area.control_area_id}")
            elif source_method not in _VALID_CONTROL_AREA_SOURCE_METHODS:
                area_diagnostics.append("source_control_area_method_unknown")
                diagnostics.append(f"warning:source_control_area_method_unknown:{area.control_area_id}:{source_method}")
            if not intent_status:
                area_diagnostics.append("source_control_area_intent_missing")
                diagnostics.append(f"warning:source_control_area_intent_missing:{area.control_area_id}")
            elif intent_status not in _VALID_CONTROL_AREA_INTENT_STATUSES:
                area_diagnostics.append("source_control_area_intent_unknown")
                diagnostics.append(f"warning:source_control_area_intent_unknown:{area.control_area_id}:{intent_status}")
            elif intent_status != "intersection_owned":
                area_diagnostics.append(f"source_control_area_intent_{intent_status}")
                diagnostics.append(f"warning:source_control_area_intent_{intent_status}:{area.control_area_id}")
            if not control_region_refs:
                area_diagnostics.append("source_control_area_region_refs_missing")
                diagnostics.append(f"warning:source_control_area_region_refs_missing:{area.control_area_id}")
            if intent_status == "region_derived" and not source_region_refs:
                area_diagnostics.append("source_control_area_source_region_refs_missing")
                diagnostics.append(f"warning:source_control_area_source_region_refs_missing:{area.control_area_id}")
            if source_region_refs and control_region_refs and set(source_region_refs) != set(control_region_refs):
                area_diagnostics.append("source_control_area_region_ref_mismatch")
                diagnostics.append(f"warning:source_control_area_region_ref_mismatch:{area.control_area_id}")
            curb_return_policy_ref = str(getattr(area, "curb_return_policy_ref", "") or "")
            grading_policy_ref = str(getattr(area, "grading_policy_ref", "") or "")
            drainage_policy_ref = str(getattr(area, "drainage_policy_ref", "") or "")
            if curb_return_policy_ref and curb_return_policy_ref not in curb_return_policy_ids:
                area_diagnostics.append("source_control_area_curb_return_policy_ref_unresolved")
                diagnostics.append(
                    f"warning:source_control_area_curb_return_policy_ref_unresolved:{area.control_area_id}:{curb_return_policy_ref}"
                )
            if grading_policy_ref and grading_policy_ref not in grading_policy_ids:
                area_diagnostics.append("source_control_area_grading_policy_ref_unresolved")
                diagnostics.append(
                    f"warning:source_control_area_grading_policy_ref_unresolved:{area.control_area_id}:{grading_policy_ref}"
                )
            if drainage_policy_ref and drainage_policy_ref not in drainage_policy_ids:
                area_diagnostics.append("source_control_area_drainage_policy_ref_unresolved")
                diagnostics.append(
                    f"warning:source_control_area_drainage_policy_ref_unresolved:{area.control_area_id}:{drainage_policy_ref}"
                )
            region_lineage_status = _control_area_region_lineage_status(
                intent_status,
                tuple(source_region_refs),
                tuple(control_region_refs),
            )
            clipping_boundary_ref = f"intersection-control-boundary:{_id_token(area.control_area_id)}"
            control_area_source_status = _control_area_source_status(area_diagnostics)
            control_area_rows.append(
                IntersectionTopologyControlAreaRow(
                    control_area_id=area.control_area_id,
                    intersection_id=area.intersection_id,
                    control_area_result_id=f"{row.intersection_id}:control-area-result:{len(control_area_rows) + 1:02d}",
                    source_control_area_ref=area.control_area_id,
                    alignment_ref=area.alignment_ref,
                    station_ranges=station_ranges,
                    influence_ranges=influence_ranges,
                    control_region_refs=tuple(control_region_refs),
                    result_region_refs=tuple(control_region_refs),
                    source_method=source_method,
                    approval_status=approval_status,
                    intent_status=intent_status,
                    source_region_refs=tuple(source_region_refs),
                    region_lineage_status=region_lineage_status,
                    clipping_boundary_ref=clipping_boundary_ref,
                    region_handoff_status=_control_area_region_handoff_status(region_lineage_status, area_diagnostics),
                    clipping_handoff_status=_control_area_clipping_handoff_status(clipping_boundary_ref, station_ranges, area_diagnostics),
                    handoff_target=f"intersection-source-stage:control_areas:{_id_token(area.control_area_id)}",
                    surface_zone_scope="intersection_control_area",
                    curb_return_policy_ref=curb_return_policy_ref,
                    grading_policy_ref=grading_policy_ref,
                    drainage_policy_ref=drainage_policy_ref,
                    source_status=control_area_source_status,
                    source_diagnostic_rows=tuple(area_diagnostics),
                    status=control_area_source_status if control_area_source_status != "accepted" else "ready",
                    notes="; ".join(area_diagnostics),
                )
            )
        if not control_area_rows:
            diagnostics.append("error:intersection_control_area_rows_missing")

        lane_connection_rows: list[IntersectionTopologyLaneConnectionRow] = []
        leg_ids = {str(getattr(leg, "leg_id", "") or "") for leg in leg_rows if str(getattr(leg, "leg_id", "") or "")}
        leg_span_by_id = {str(getattr(span, "leg_ref", "") or ""): span for span in leg_span_rows if str(getattr(span, "leg_ref", "") or "")}
        edge_policy_by_id = {
            str(getattr(policy, "policy_id", "") or ""): policy
            for policy in list(getattr(intersection_model, "edge_policy_rows", []) or [])
            if str(getattr(policy, "policy_id", "") or "")
        }
        for index, connection in enumerate(self._lane_connections_for_intersection(intersection_model, row.intersection_id), start=1):
            connection_id = str(getattr(connection, "connection_id", "") or f"{row.intersection_id}:lane-connection:{index:02d}")
            movement_type = str(getattr(connection, "movement_type", "") or "through")
            from_leg_ref = str(getattr(connection, "from_leg_ref", "") or "")
            to_leg_ref = str(getattr(connection, "to_leg_ref", "") or "")
            from_edge_policy_ref = str(getattr(connection, "from_edge_policy_ref", "") or "")
            to_edge_policy_ref = str(getattr(connection, "to_edge_policy_ref", "") or "")
            source_method = str(getattr(connection, "source_method", "") or "manual")
            approval_status = str(getattr(connection, "approval_status", "") or "accepted")
            connection_diagnostics: list[str] = []
            if movement_type not in _VALID_LANE_CONNECTION_MOVEMENT_TYPES:
                connection_diagnostics.append("source_lane_connection_movement_type_unknown")
                diagnostics.append(f"warning:source_lane_connection_movement_type_unknown:{connection_id}:{movement_type}")
            for diagnostic in list(getattr(connection, "diagnostic_rows", []) or []):
                text = str(diagnostic or "").strip()
                if text:
                    connection_diagnostics.append(text)
                    diagnostics.append(f"warning:{text}:{connection_id}")
            if approval_status not in {"accepted", "locked"}:
                connection_diagnostics.append("source_lane_connection_approval_pending")
                diagnostics.append(f"warning:source_lane_connection_approval_pending:{connection_id}")
            if approval_status and approval_status not in _VALID_LANE_CONNECTION_APPROVAL_STATUSES:
                connection_diagnostics.append("source_lane_connection_approval_status_unknown")
                diagnostics.append(f"warning:source_lane_connection_approval_status_unknown:{connection_id}:{approval_status}")
            if not source_method:
                connection_diagnostics.append("source_lane_connection_method_missing")
                diagnostics.append(f"warning:source_lane_connection_method_missing:{connection_id}")
            elif source_method not in _VALID_LANE_CONNECTION_SOURCE_METHODS:
                connection_diagnostics.append("source_lane_connection_method_unknown")
                diagnostics.append(f"warning:source_lane_connection_method_unknown:{connection_id}:{source_method}")
            if not from_leg_ref:
                connection_diagnostics.append("source_lane_connection_from_leg_missing")
                diagnostics.append(f"error:source_lane_connection_from_leg_missing:{connection_id}")
            elif from_leg_ref not in leg_ids:
                connection_diagnostics.append("source_lane_connection_from_leg_unresolved")
                diagnostics.append(f"error:source_lane_connection_from_leg_unresolved:{connection_id}:{from_leg_ref}")
            if not to_leg_ref:
                connection_diagnostics.append("source_lane_connection_to_leg_missing")
                diagnostics.append(f"error:source_lane_connection_to_leg_missing:{connection_id}")
            elif to_leg_ref not in leg_ids:
                connection_diagnostics.append("source_lane_connection_to_leg_unresolved")
                diagnostics.append(f"error:source_lane_connection_to_leg_unresolved:{connection_id}:{to_leg_ref}")
            if not from_edge_policy_ref:
                connection_diagnostics.append("source_lane_connection_from_edge_policy_missing")
                diagnostics.append(f"error:source_lane_connection_from_edge_policy_missing:{connection_id}")
            elif from_edge_policy_ref not in edge_policy_ids:
                connection_diagnostics.append("source_lane_connection_from_edge_policy_unresolved")
                diagnostics.append(f"error:source_lane_connection_from_edge_policy_unresolved:{connection_id}:{from_edge_policy_ref}")
            if not to_edge_policy_ref:
                connection_diagnostics.append("source_lane_connection_to_edge_policy_missing")
                diagnostics.append(f"error:source_lane_connection_to_edge_policy_missing:{connection_id}")
            elif to_edge_policy_ref not in edge_policy_ids:
                connection_diagnostics.append("source_lane_connection_to_edge_policy_unresolved")
                diagnostics.append(f"error:source_lane_connection_to_edge_policy_unresolved:{connection_id}:{to_edge_policy_ref}")
            from_leg_status = str(getattr(leg_span_by_id.get(from_leg_ref), "source_status", "") or "")
            to_leg_status = str(getattr(leg_span_by_id.get(to_leg_ref), "source_status", "") or "")
            if from_leg_status and from_leg_status != "accepted":
                connection_diagnostics.append(f"source_lane_connection_from_leg_status:{from_leg_status}")
            if to_leg_status and to_leg_status != "accepted":
                connection_diagnostics.append(f"source_lane_connection_to_leg_status:{to_leg_status}")
            from_edge_family, from_edge_status, from_edge_diagnostics = _lane_connection_edge_policy_lineage(
                edge_policy_by_id.get(from_edge_policy_ref),
                from_edge_policy_ref,
            )
            to_edge_family, to_edge_status, to_edge_diagnostics = _lane_connection_edge_policy_lineage(
                edge_policy_by_id.get(to_edge_policy_ref),
                to_edge_policy_ref,
            )
            connection_diagnostics.extend(f"from_edge:{item}" for item in from_edge_diagnostics)
            connection_diagnostics.extend(f"to_edge:{item}" for item in to_edge_diagnostics)
            connection_source_status = _lane_connection_source_status(connection_diagnostics)
            lane_connection_rows.append(
                IntersectionTopologyLaneConnectionRow(
                    connection_id=connection_id,
                    intersection_id=str(getattr(connection, "intersection_id", "") or row.intersection_id),
                    lane_connection_result_id=f"{row.intersection_id}:lane-connection-result:{index:02d}",
                    source_lane_connection_ref=connection_id,
                    movement_type=movement_type,
                    from_leg_ref=from_leg_ref,
                    to_leg_ref=to_leg_ref,
                    from_edge_policy_ref=from_edge_policy_ref,
                    to_edge_policy_ref=to_edge_policy_ref,
                    from_lane_index=int(getattr(connection, "from_lane_index", 1) or 1),
                    to_lane_index=int(getattr(connection, "to_lane_index", 1) or 1),
                    from_leg_source_status=from_leg_status,
                    to_leg_source_status=to_leg_status,
                    from_edge_family_intent=from_edge_family,
                    to_edge_family_intent=to_edge_family,
                    from_edge_source_status=from_edge_status,
                    to_edge_source_status=to_edge_status,
                    movement_lineage_status=_lane_connection_movement_lineage_status(connection_diagnostics),
                    leg_handoff_status=_lane_connection_leg_handoff_status(from_leg_ref, to_leg_ref, from_leg_status, to_leg_status),
                    edge_handoff_status=_lane_connection_edge_handoff_status(
                        from_edge_policy_ref,
                        to_edge_policy_ref,
                        from_edge_status,
                        to_edge_status,
                        from_edge_diagnostics,
                        to_edge_diagnostics,
                    ),
                    handoff_scope="lane_connection",
                    handoff_target=f"intersection-source-stage:lane_connections:{_id_token(connection_id)}",
                    source_method=source_method,
                    approval_status=approval_status,
                    source_status=connection_source_status,
                    source_diagnostic_rows=tuple(connection_diagnostics),
                    status=connection_source_status if connection_source_status != "accepted" else "ready",
                    notes="; ".join(connection_diagnostics),
                )
            )

        alignment_refs = _unique_text_values(
            [
                str(getattr(row, "primary_alignment_ref", "") or ""),
                *[str(ref) for ref in list(getattr(row, "secondary_alignment_refs", []) or [])],
                *[span.alignment_ref for span in leg_span_rows],
                *[area.alignment_ref for area in control_area_rows],
            ]
        )
        control_region_refs = _unique_text_values(
            [
                *[str(ref) for ref in list(getattr(row, "control_region_refs", []) or [])],
                *[ref for area in control_area_rows for ref in area.control_region_refs],
            ]
        )
        status = _topology_status(diagnostics)
        return IntersectionTopologyResult(
            schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
            project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
            label=f"Intersection Topology - {row.intersection_id}",
            topology_result_id=f"intersection-topology:{row.intersection_id}",
            intersection_id=row.intersection_id,
            intersection_kind=row.intersection_kind,
            status=status,
            participating_alignment_count=len(alignment_refs),
            control_region_count=len(control_region_refs),
            anchor_count=len(anchor_rows),
            leg_span_count=len(leg_span_rows),
            leg_graph_status=leg_graph_status,
            corner_graph_status=corner_graph_status,
            corner_count=len(corner_graph_rows),
            curb_return_arc_count=len([row for row in corner_graph_rows if int(getattr(row, "arc_point_count", 0) or 0) >= 3]),
            control_area_count=len(control_area_rows),
            lane_connection_count=len(lane_connection_rows),
            leg_graph_order_refs=[
                f"{int(getattr(span, 'leg_graph_order', 0) or 0)}:{str(getattr(span, 'leg_ref', '') or '')}"
                for span in leg_span_rows
            ],
            leg_graph_diagnostic_rows=leg_graph_diagnostics,
            corner_graph_order_refs=[
                f"{int(getattr(corner, 'corner_graph_order', 0) or 0)}:{str(getattr(corner, 'from_leg_ref', '') or '')}->{str(getattr(corner, 'to_leg_ref', '') or '')}"
                for corner in corner_graph_rows
            ],
            corner_graph_diagnostic_rows=corner_graph_diagnostics,
            policy_refs=policy_refs,
            diagnostic_rows=diagnostics,
            anchor_rows=anchor_rows,
            leg_span_rows=leg_span_rows,
            corner_rows=corner_graph_rows,
            control_area_rows=control_area_rows,
            lane_connection_rows=lane_connection_rows,
            source_refs=[ref for ref in source_refs if ref],
        )

    def resolve_station(
        self,
        intersection_model: IntersectionModel,
        station: float | None = None,
        *,
        alignment_ref: str = "",
    ) -> IntersectionEvaluationResult:
        """Resolve active intersection context by station and optional Alignment ref."""

        if station is None:
            raise ValueError("station is required.")

        control_area = self._find_active_control_area(
            intersection_model.control_area_rows,
            station,
            alignment_ref=alignment_ref,
        )
        if control_area is None:
            return IntersectionEvaluationResult(
                station=station,
                alignment_ref=alignment_ref,
                diagnostic_rows=(
                    "intersection_context_not_found_for_alignment_station"
                    if alignment_ref
                    else "intersection_context_not_found_for_station",
                ),
            )

        intersection_row = self._find_intersection_row(intersection_model, control_area.intersection_id)
        leg = self._find_active_leg(intersection_row, alignment_ref, station)
        source_diagnostics = _station_intersection_source_diagnostics(
            control_area,
            leg,
            alignment_ref=alignment_ref,
            anchor_rows=[
                row
                for row in list(getattr(intersection_model, "anchor_rows", []) or [])
                if str(getattr(row, "intersection_id", "") or "") == control_area.intersection_id
            ],
            edge_policy_rows=list(getattr(intersection_model, "edge_policy_rows", []) or []),
        )

        return IntersectionEvaluationResult(
            station=station,
            alignment_ref=alignment_ref,
            active_intersection_id=control_area.intersection_id,
            active_control_area_id=control_area.control_area_id,
            active_leg_id=leg.leg_id if leg is not None else "",
            leg_role=leg.leg_role if leg is not None else "",
            control_region_refs=tuple(control_area.control_region_refs),
            curb_return_policy_ref=control_area.curb_return_policy_ref,
            turn_lane_policy_ref=control_area.turn_lane_policy_ref,
            grading_policy_ref=control_area.grading_policy_ref,
            drainage_policy_ref=control_area.drainage_policy_ref,
            source_status="warning" if source_diagnostics else "accepted",
            source_diagnostic_rows=tuple(source_diagnostics),
            diagnostic_rows=() if leg is not None or not alignment_ref else ("intersection_leg_not_found_for_alignment_station",),
        )

    @staticmethod
    def _find_active_control_area(
        control_areas: list[IntersectionControlArea],
        station: float,
        *,
        alignment_ref: str = "",
    ) -> IntersectionControlArea | None:
        for row in control_areas:
            if alignment_ref and row.alignment_ref and row.alignment_ref != alignment_ref:
                continue
            for station_start, station_end in row.station_ranges:
                if station_start <= station <= station_end:
                    return row
            for station_start, station_end in row.influence_ranges:
                if station_start <= station <= station_end:
                    return row
        return None

    @staticmethod
    def _find_intersection_row(
        intersection_model: IntersectionModel,
        intersection_id: str,
    ) -> IntersectionRow | None:
        for row in intersection_model.intersection_rows:
            if row.intersection_id == intersection_id:
                return row
        return None

    @staticmethod
    def _find_active_leg(
        intersection_row: IntersectionRow | None,
        alignment_ref: str,
        station: float,
    ) -> IntersectionLegRow | None:
        if intersection_row is None:
            return None
        candidates: list[IntersectionLegRow] = []
        for leg in intersection_row.leg_rows:
            if alignment_ref and leg.alignment_ref and leg.alignment_ref != alignment_ref:
                continue
            if leg.approach_station_start or leg.approach_station_end:
                start = min(leg.approach_station_start, leg.approach_station_end)
                end = max(leg.approach_station_start, leg.approach_station_end)
                if not (start <= station <= end):
                    continue
            candidates.append(leg)
        if not candidates:
            return None
        return sorted(candidates, key=lambda row: (row.priority, row.leg_id))[0]

    @staticmethod
    def _find_topology_intersection_row(
        intersection_model: IntersectionModel,
        intersection_id: str = "",
    ) -> IntersectionRow | None:
        target = str(intersection_id or "").strip()
        rows = list(getattr(intersection_model, "intersection_rows", []) or [])
        if target:
            for row in rows:
                if str(getattr(row, "intersection_id", "") or "") == target:
                    return row
            return None
        return rows[0] if rows else None

    @staticmethod
    def _control_areas_for_intersection(
        intersection_model: IntersectionModel,
        intersection_id: str,
    ) -> list[IntersectionControlArea]:
        return [
            area
            for area in list(getattr(intersection_model, "control_area_rows", []) or [])
            if str(getattr(area, "intersection_id", "") or "") == str(intersection_id or "")
        ]

    @staticmethod
    def _anchor_rows_for_intersection(
        intersection_model: IntersectionModel,
        intersection_id: str,
    ) -> list[IntersectionAnchorRow]:
        return [
            row
            for row in list(getattr(intersection_model, "anchor_rows", []) or [])
            if str(getattr(row, "intersection_id", "") or "") == str(intersection_id or "")
        ]

    @staticmethod
    def _lane_connections_for_intersection(
        intersection_model: IntersectionModel,
        intersection_id: str,
    ) -> list[IntersectionLaneConnectionRow]:
        return [
            row
            for row in list(getattr(intersection_model, "lane_connection_rows", []) or [])
            if str(getattr(row, "intersection_id", "") or "") == str(intersection_id or "")
        ]


def _control_area_ref_for_alignment(
    intersection_model: IntersectionModel,
    intersection_id: str,
    alignment_ref: str,
) -> str:
    for area in list(getattr(intersection_model, "control_area_rows", []) or []):
        if str(getattr(area, "intersection_id", "") or "") != str(intersection_id or ""):
            continue
        if str(getattr(area, "alignment_ref", "") or "") == str(alignment_ref or ""):
            return str(getattr(area, "control_area_id", "") or "")
    return ""


def _topology_leg_graph_rows(leg_rows: list[IntersectionLegRow]) -> tuple[list[tuple[IntersectionLegRow, int, float, str]], list[str], str]:
    graph_rows: list[tuple[IntersectionLegRow, int, float, str]] = []
    diagnostics: list[str] = []
    role_angles_used = False
    fallback_used = False
    seen_angles: dict[float, list[str]] = {}
    leg_count = len(list(leg_rows or []))
    for index, leg in enumerate(list(leg_rows or []), start=1):
        leg_id = str(getattr(leg, "leg_id", "") or f"leg:{index:02d}")
        role = str(getattr(leg, "leg_role", "") or "")
        if role in _LEG_GRAPH_ROLE_ANGLE_DEG:
            angle_deg = float(_LEG_GRAPH_ROLE_ANGLE_DEG[role])
            angle_source = "role_preset"
            role_angles_used = True
        else:
            angle_deg = (360.0 * float(index - 1) / float(max(leg_count, 1))) % 360.0
            angle_source = "index_even_spacing_fallback"
            fallback_used = True
            diagnostics.append(f"warning:intersection_leg_graph_angle_fallback:{leg_id}:{role or '-'}")
        normalized_angle = angle_deg % 360.0
        seen_angles.setdefault(round(normalized_angle, 6), []).append(leg_id)
        graph_rows.append((leg, index, normalized_angle, angle_source))
    for angle, refs in seen_angles.items():
        if len(refs) > 1:
            diagnostics.append(f"warning:intersection_leg_graph_duplicate_angle:{angle:.3f}:{','.join(refs)}")
    graph_rows.sort(
        key=lambda item: (
            item[2],
            int(getattr(item[0], "priority", 0) or 0),
            str(getattr(item[0], "leg_id", "") or ""),
        )
    )
    ordered: list[tuple[IntersectionLegRow, int, float, str]] = []
    for order, (leg, _source_index, angle_deg, angle_source) in enumerate(graph_rows, start=1):
        ordered.append((leg, order, angle_deg, angle_source))
    if not ordered:
        status = "error"
    elif fallback_used:
        status = "warning"
    elif role_angles_used:
        status = "ready"
    else:
        status = "warning"
    if ordered:
        diagnostics.append(
            "info:intersection_leg_graph_order:"
            + ",".join(
                f"{order}:{str(getattr(leg, 'leg_id', '') or '')}@{angle_deg:.1f}"
                for leg, order, angle_deg, _angle_source in ordered
            )
        )
    return ordered, _unique_text_values(diagnostics), status


def _topology_corner_graph_rows(
    *,
    intersection_model: IntersectionModel,
    intersection_id: str,
    intersection_kind: str,
    leg_span_rows: list[IntersectionTopologyLegSpanRow],
    anchor_rows: list[IntersectionTopologyAnchorRow],
) -> tuple[list[IntersectionTopologyCornerRow], list[str], str]:
    diagnostics: list[str] = []
    ordered_spans = sorted(
        [span for span in list(leg_span_rows or []) if str(getattr(span, "leg_ref", "") or "")],
        key=lambda span: (
            int(getattr(span, "leg_graph_order", 0) or 0),
            str(getattr(span, "leg_ref", "") or ""),
        ),
    )
    if len(ordered_spans) < 2:
        return [], ["error:intersection_corner_graph_leg_count_insufficient"], "error"
    source_corners = [
        row
        for row in list(getattr(intersection_model, "corner_rows", []) or [])
        if str(getattr(row, "intersection_id", "") or "") == str(intersection_id or "")
    ]
    source_by_pair: dict[tuple[str, str], IntersectionCornerRow] = {}
    for corner in source_corners:
        from_ref = str(getattr(corner, "from_leg_ref", "") or "")
        to_ref = str(getattr(corner, "to_leg_ref", "") or "")
        if from_ref and to_ref:
            source_by_pair[(from_ref, to_ref)] = corner
    policies = _curb_return_policies_for_intersection(intersection_model, intersection_id)
    policy_by_ref = {str(getattr(policy, "policy_id", "") or ""): policy for policy in policies if str(getattr(policy, "policy_id", "") or "")}
    default_policy = policies[0] if policies else None
    leg_span_by_ref = {str(getattr(span, "leg_ref", "") or ""): span for span in ordered_spans}
    anchor = anchor_rows[0] if anchor_rows else None
    anchor_context = {
        "anchor_xyz": tuple(getattr(anchor, "point_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)),
        "primary_alignment": str(getattr(anchor, "primary_alignment_ref", "") or ""),
    }
    rows: list[IntersectionTopologyCornerRow] = []
    for index, from_span in enumerate(ordered_spans, start=1):
        to_span = ordered_spans[index % len(ordered_spans)]
        from_ref = str(getattr(from_span, "leg_ref", "") or "")
        to_ref = str(getattr(to_span, "leg_ref", "") or "")
        corner = source_by_pair.get((from_ref, to_ref))
        reversed_source = False
        if corner is None and (to_ref, from_ref) in source_by_pair:
            corner = source_by_pair[(to_ref, from_ref)]
            reversed_source = True
        row_diagnostics: list[str] = []
        source_corner_ref = str(getattr(corner, "corner_id", "") or "") if corner is not None else ""
        if corner is None:
            row_diagnostics.append("candidate_missing_source_corner")
            diagnostics.append(f"warning:intersection_corner_graph_candidate_missing_source:{from_ref}:{to_ref}")
        elif reversed_source:
            row_diagnostics.append("source_corner_direction_reversed")
            diagnostics.append(f"warning:intersection_corner_graph_source_direction_reversed:{source_corner_ref}")
        policy_ref = str(getattr(corner, "curb_return_policy_ref", "") or "") if corner is not None else ""
        policy = policy_by_ref.get(policy_ref) if policy_ref else default_policy
        if policy is None:
            row_diagnostics.append("curb_return_policy_missing")
            diagnostics.append(f"error:intersection_corner_graph_curb_return_policy_missing:{from_ref}:{to_ref}")
        elif not policy_ref:
            policy_ref = str(getattr(policy, "policy_id", "") or "")
            row_diagnostics.append("curb_return_policy_defaulted")
            diagnostics.append(f"warning:intersection_corner_graph_curb_return_policy_defaulted:{from_ref}:{to_ref}:{policy_ref}")
        radius = float(getattr(policy, "radius", 0.0) or 0.0) if policy is not None else 0.0
        if radius <= 0.0:
            row_diagnostics.append("curb_return_radius_missing")
            diagnostics.append(f"error:intersection_corner_graph_curb_return_radius_missing:{from_ref}:{to_ref}")
        working_corner = corner or IntersectionCornerRow(
            corner_id=f"{intersection_id}:corner-candidate-{index:02d}",
            intersection_id=intersection_id,
            from_leg_ref=from_ref,
            to_leg_ref=to_ref,
            side=f"corner_{index:02d}",
            quadrant=f"quadrant_{index:02d}",
            curb_return_policy_ref=policy_ref,
            source_method="leg_graph_candidate",
            approval_status="draft",
        )
        start_xyz, end_xyz = _intersection_curb_return_edge_endpoints(
            corner=working_corner,
            policy=policy,
            leg_span_by_ref=leg_span_by_ref,
            anchor_context=anchor_context,
        )
        arc_points = _intersection_curb_return_arc_points(
            start_xyz,
            end_xyz,
            center_xyz=_xyz_tuple(anchor_context.get("anchor_xyz", (0.0, 0.0, 0.0))),
            radius=radius,
        )
        if len(arc_points) < 3:
            row_diagnostics.append("curb_return_arc_points_missing")
            diagnostics.append(f"error:intersection_corner_graph_arc_points_missing:{from_ref}:{to_ref}")
        source_status = _corner_source_status(row_diagnostics)
        if any(
            str(item) in {"curb_return_policy_missing", "curb_return_radius_missing", "curb_return_arc_points_missing"}
            for item in row_diagnostics
        ):
            source_status = "error"
        rows.append(
            IntersectionTopologyCornerRow(
                corner_result_id=f"{intersection_id}:corner-result:{index:02d}",
                intersection_id=intersection_id,
                corner_graph_order=index,
                source_corner_ref=source_corner_ref,
                from_leg_ref=from_ref,
                to_leg_ref=to_ref,
                side=str(getattr(working_corner, "side", "") or ""),
                quadrant=str(getattr(working_corner, "quadrant", "") or ""),
                curb_return_policy_ref=policy_ref,
                radius=radius,
                start_xyz=start_xyz,
                end_xyz=end_xyz,
                arc_points_xyz=tuple(arc_points),
                arc_point_count=len(arc_points),
                source_method=str(getattr(working_corner, "source_method", "") or ""),
                approval_status=str(getattr(working_corner, "approval_status", "") or ""),
                source_status=source_status,
                source_diagnostic_rows=tuple(row_diagnostics),
                status=source_status if source_status != "accepted" else "ready",
                notes="; ".join(row_diagnostics),
            )
        )
    if any(str(getattr(row, "status", "") or "") == "error" for row in rows):
        status = "error"
    elif any(str(getattr(row, "status", "") or "") == "warning" for row in rows):
        status = "warning"
    else:
        status = "ready"
    diagnostics.append(
        "info:intersection_corner_graph_order:"
        + ",".join(
            f"{row.corner_graph_order}:{row.from_leg_ref}->{row.to_leg_ref}"
            for row in rows
        )
    )
    if str(intersection_kind or "") == "cross_intersection" and len(rows) != 4:
        diagnostics.append(f"error:cross_intersection_corner_count:{len(rows)}")
        status = "error"
    return rows, _unique_text_values(diagnostics), status


def _xyz_tuple_or_none(value) -> tuple[float, float, float] | None:
    try:
        if len(value) < 3:
            return None
        return (float(value[0]), float(value[1]), float(value[2]))
    except Exception:
        return None


def _intersection_boundary_key(point: tuple[float, float, float]) -> tuple[float, float]:
    return (round(float(point[0]), 6), round(float(point[1]), 6))


def _intersection_boundary_construct_curb_return_envelope(
    topology: IntersectionTopologyResult | None,
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    list[str],
]:
    """Build an authoritative boundary-loop candidate from ordered curb-return arcs."""

    diagnostics: list[str] = []
    if topology is None:
        return [], [], diagnostics
    intersection_id = str(getattr(topology, "intersection_id", "") or "main")
    corners = [
        row
        for row in sorted(
            list(getattr(topology, "corner_rows", []) or []),
            key=lambda item: int(getattr(item, "corner_graph_order", 0) or 0),
        )
        if len(tuple(getattr(row, "arc_points_xyz", ()) or ())) >= 2
    ]
    if len(corners) < 3:
        diagnostics.append(
            "info:intersection_boundary_curb_return_envelope_skipped:"
            f"corner_arcs={len(corners)};reason=corner_arc_count_too_low"
        )
        return [], [], diagnostics

    candidate_results = []
    for first_reversed in (False, True):
        ordered_arcs: list[tuple[IntersectionTopologyCornerRow, list[tuple[float, float, float]]]] = []
        for index, corner in enumerate(corners):
            arc_points = [_xyz_tuple(point) for point in tuple(getattr(corner, "arc_points_xyz", ()) or ())]
            if len(arc_points) < 2:
                continue
            if index == 0:
                if first_reversed:
                    arc_points = list(reversed(arc_points))
            else:
                previous_end = ordered_arcs[-1][1][-1]
                if _distance_xy(previous_end, arc_points[-1]) < _distance_xy(previous_end, arc_points[0]):
                    arc_points = list(reversed(arc_points))
            ordered_arcs.append((corner, arc_points))
        points, segments, connector_count = _intersection_boundary_join_ordered_corner_arcs(
            ordered_arcs,
            intersection_id=intersection_id,
        )
        if len(points) < 4:
            continue
        area = abs(_intersection_boundary_area_xy(points))
        self_crossing = _polyline_self_crosses_xy(points)
        connector_length = sum(
            _distance_xy(first, second)
            for first, second, _sid, role, _refs in segments
            if role == "curb_return_envelope_connector"
        )
        candidate_results.append((self_crossing, connector_length, -area, points, segments, connector_count))

    if not candidate_results:
        diagnostics.append("warning:intersection_boundary_curb_return_envelope_unavailable")
        return [], [], diagnostics
    candidate_results.sort(key=lambda item: (item[0], item[1], item[2]))
    self_crossing, _connector_length, negative_area, points, segments, connector_count = candidate_results[0]
    area = abs(float(negative_area))
    if area <= 1.0e-6:
        diagnostics.append("warning:intersection_boundary_curb_return_envelope_area_too_small")
        return [], [], diagnostics
    if self_crossing:
        diagnostics.append("warning:intersection_boundary_curb_return_envelope_self_crossing")
        return [], [], diagnostics
    diagnostics.append(
        "info:intersection_boundary_curb_return_envelope_ready:"
        f"corners={len(corners)};points={max(0, len(points) - 1)};connectors={connector_count}"
    )
    if connector_count:
        diagnostics.append(f"info:intersection_boundary_curb_return_envelope_connectors:{connector_count}")
    return points, segments, diagnostics


def _intersection_boundary_join_ordered_corner_arcs(
    ordered_arcs: list[tuple[IntersectionTopologyCornerRow, list[tuple[float, float, float]]]],
    *,
    intersection_id: str,
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    int,
]:
    points: list[tuple[float, float, float]] = []
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]] = []
    connector_count = 0
    for corner_index, (corner, arc_points) in enumerate(ordered_arcs, start=1):
        source_refs = tuple(
            value
            for value in (
                str(getattr(corner, "corner_result_id", "") or ""),
                str(getattr(corner, "source_corner_ref", "") or ""),
                str(getattr(corner, "curb_return_policy_ref", "") or ""),
                str(getattr(corner, "from_leg_ref", "") or ""),
                str(getattr(corner, "to_leg_ref", "") or ""),
            )
            if value
        )
        if points and _intersection_boundary_key(points[-1]) != _intersection_boundary_key(arc_points[0]):
            connector_count += 1
            connector_id = (
                f"intersection-boundary-envelope:{_id_token(intersection_id)}:"
                f"corner-connector:{corner_index:02d}"
            )
            segments.append((points[-1], arc_points[0], connector_id, "curb_return_envelope_connector", source_refs))
        if not points:
            points.append(arc_points[0])
        elif _intersection_boundary_key(points[-1]) != _intersection_boundary_key(arc_points[0]):
            points.append(arc_points[0])
        for arc_index, (first, second) in enumerate(zip(arc_points[:-1], arc_points[1:]), start=1):
            if _intersection_boundary_key(first) == _intersection_boundary_key(second):
                continue
            if _intersection_boundary_key(points[-1]) != _intersection_boundary_key(first):
                points.append(first)
            points.append(second)
            segment_id = (
                f"intersection-boundary-envelope:{_id_token(intersection_id)}:"
                f"corner:{corner_index:02d}:arc:{arc_index:02d}"
            )
            segments.append((first, second, segment_id, "curb_return_envelope_arc", source_refs))
    if points and _intersection_boundary_key(points[0]) != _intersection_boundary_key(points[-1]):
        connector_count += 1
        connector_id = f"intersection-boundary-envelope:{_id_token(intersection_id)}:corner-connector:close"
        last_refs = segments[-1][4] if segments else ()
        segments.append((points[-1], points[0], connector_id, "curb_return_envelope_connector", last_refs))
        points.append(points[0])
    return points, segments, connector_count


def _distance_xy(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return math.hypot(float(second[0]) - float(first[0]), float(second[1]) - float(first[1]))


def _intersection_boundary_authoritative_candidate_edges(
    edges: list[IntersectionEdgeNetworkRow],
) -> tuple[list[IntersectionEdgeNetworkRow], list[str]]:
    output: list[IntersectionEdgeNetworkRow] = []
    excluded: dict[str, int] = {}
    for edge in list(edges or []):
        reason = _intersection_boundary_edge_authority_exclusion_reason(edge)
        if reason:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        output.append(edge)
    diagnostics = [
        f"warning:intersection_boundary_candidate_edges_excluded:{reason}:{count}"
        for reason, count in sorted(excluded.items())
    ]
    if edges and not output:
        diagnostics.append("error:intersection_boundary_authoritative_source_edges_missing")
    return output, diagnostics


def _intersection_boundary_edge_authority_exclusion_reason(edge: IntersectionEdgeNetworkRow) -> str:
    source_status = str(getattr(edge, "source_status", "") or "accepted")
    status = str(getattr(edge, "status", "") or "ready")
    if source_status not in {"accepted", "ready", "locked"}:
        return f"source_status_{_id_token(source_status)}"
    if status not in {"accepted", "ready", "locked"}:
        return f"status_{_id_token(status)}"
    diagnostics = " ".join(
        str(value or "")
        for value in tuple(getattr(edge, "source_diagnostic_rows", ()) or ())
    ).lower()
    for token, reason in (
        ("defaulted", "defaulted_source"),
        ("approval_pending", "approval_pending"),
        ("review_required", "review_required"),
        ("method_unknown", "method_unknown"),
        ("method_missing", "method_missing"),
        ("source_policy_ref_missing", "source_policy_ref_missing"),
        ("fallback", "fallback_source"),
        ("diagnostic", "diagnostic_source"),
        ("preview", "preview_source"),
        ("highlight", "highlight_source"),
    ):
        if token in diagnostics:
            return reason
    return ""


def _intersection_boundary_slope_face_loop_candidate_counts(
    slope_face_loop_result,
) -> tuple[int, int]:
    point_count = 0
    segment_count = 0
    for loop in list(getattr(slope_face_loop_result, "loop_rows", []) or []):
        if str(getattr(loop, "status", "") or "") != "ready":
            continue
        if not bool(getattr(loop, "closed_xy", False)):
            continue
        loop_id = str(getattr(loop, "loop_id", "") or "")
        points: list[tuple[float, float, float]] = []
        for point in list(getattr(loop, "loop_points_xyz", ()) or ()):
            xyz = _xyz_tuple_or_none(point)
            if xyz is not None:
                points.append(xyz)
        if len(points) < 4 or not _points_closed_xy(points):
            continue
        point_count += len(points)
        for start, end in zip(points, points[1:]):
            if _intersection_boundary_key(start) == _intersection_boundary_key(end):
                continue
            segment_count += 1
    return point_count, segment_count


def _intersection_boundary_trace_closed_segments(
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    list[str],
]:
    diagnostics: list[str] = []
    clean_segments = [
        row for row in list(segments or [])
        if _intersection_boundary_key(row[0]) != _intersection_boundary_key(row[1])
    ]
    if not clean_segments:
        return [], [], ["warning:intersection_boundary_graph_segments_missing"]

    closed_loop_groups = _intersection_boundary_trace_source_loop_groups(clean_segments)
    if len(closed_loop_groups) > 1:
        area_text = ",".join(f"{abs(_intersection_boundary_area_xy(points)):.3f}" for points, _rows in closed_loop_groups[:8])
        diagnostics.append(
            f"warning:intersection_boundary_multiple_closed_components:{len(closed_loop_groups)};areas={area_text}"
        )
        return [], [], diagnostics
    if len(closed_loop_groups) == 1:
        points, rows = closed_loop_groups[0]
        diagnostics.append("info:intersection_boundary_single_source_loop_component")
        return points, rows, diagnostics

    components = _intersection_boundary_segment_components(clean_segments)
    closed_components: list[
        tuple[
            list[tuple[float, float, float]],
            list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
        ]
    ] = []
    component_diagnostics: list[str] = []
    for component in components:
        points, rows, row_diagnostics = _intersection_boundary_trace_single_closed_component(component)
        if points and rows:
            closed_components.append((points, rows))
        else:
            component_diagnostics.extend(row_diagnostics)
    if len(closed_components) > 1:
        area_text = ",".join(f"{abs(_intersection_boundary_area_xy(points)):.3f}" for points, _rows in closed_components[:8])
        diagnostics.append(
            f"warning:intersection_boundary_multiple_closed_components:{len(closed_components)};areas={area_text}"
        )
        return [], [], diagnostics
    if len(closed_components) == 1:
        if component_diagnostics:
            diagnostics.append(f"info:intersection_boundary_ignored_open_components:{len(component_diagnostics)}")
        return closed_components[0][0], closed_components[0][1], diagnostics

    diagnostics.extend(component_diagnostics[:8])
    if diagnostics:
        return [], [], diagnostics
    return [], [], ["warning:intersection_boundary_graph_segments_missing"]


def _intersection_boundary_filter_outer_candidate_segments(
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
) -> tuple[
    list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    list[str],
]:
    """Remove candidate edges that are explicitly not authoritative outer perimeter."""

    output: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]] = []
    excluded: dict[str, int] = {}
    for row in list(segments or []):
        reason = _intersection_boundary_candidate_segment_exclusion_reason(row)
        if reason:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        output.append(row)
    diagnostics = [
        f"info:intersection_boundary_candidate_segments_excluded:{reason}:{count}"
        for reason, count in sorted(excluded.items())
    ]
    return output, diagnostics


def _intersection_boundary_candidate_segment_exclusion_reason(
    segment: tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]],
) -> str:
    _start, _end, edge_id, edge_role, refs = segment
    tokens = " ".join([str(edge_id or ""), str(edge_role or ""), *[str(ref or "") for ref in refs]]).lower()
    for token, reason in (
        ("internal", "internal"),
        ("shortcut", "shortcut"),
        ("diagonal", "diagonal"),
        ("seam", "internal_seam"),
        ("preview", "preview"),
        ("highlight", "highlight"),
        ("diagnostic", "diagnostic"),
    ):
        if token in tokens:
            return reason
    return ""


def _intersection_boundary_candidate_graph_diagnostics(
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
) -> list[str]:
    clean_segments = [
        row for row in list(segments or [])
        if _intersection_boundary_key(row[0]) != _intersection_boundary_key(row[1])
    ]
    if not clean_segments:
        return ["warning:intersection_boundary_candidate_graph_empty"]
    node_degree: dict[tuple[float, float], int] = {}
    for start, end, _edge_id, _edge_role, _refs in clean_segments:
        start_key = _intersection_boundary_key(start)
        end_key = _intersection_boundary_key(end)
        node_degree[start_key] = node_degree.get(start_key, 0) + 1
        node_degree[end_key] = node_degree.get(end_key, 0) + 1
    components = _intersection_boundary_segment_components(clean_segments)
    degree_one = sorted(key for key, degree in node_degree.items() if degree == 1)
    degree_many = sorted(key for key, degree in node_degree.items() if degree > 2)
    diagnostics = [
        "info:intersection_boundary_candidate_graph:"
        f"segments={len(clean_segments)};nodes={len(node_degree)};components={len(components)};"
        f"degree1={len(degree_one)};degree_gt2={len(degree_many)}"
    ]
    if degree_one:
        diagnostics.append(
            "warning:intersection_boundary_candidate_graph_open_nodes:"
            + ",".join(_intersection_boundary_key_note(key) for key in degree_one[:8])
        )
    if degree_many:
        diagnostics.append(
            "warning:intersection_boundary_candidate_graph_branch_nodes:"
            + ",".join(f"{_intersection_boundary_key_note(key)}={node_degree[key]}" for key in degree_many[:8])
        )
    if len(components) > 1:
        diagnostics.append(
            "warning:intersection_boundary_candidate_graph_components:"
            + ",".join(str(len(component)) for component in components[:8])
        )
    return diagnostics


def _intersection_boundary_key_note(key: tuple[float, float]) -> str:
    return f"{float(key[0]):.3f}:{float(key[1]):.3f}"


def _intersection_boundary_construct_rectilinear_source_perimeter(
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    list[str],
]:
    clean_segments = [
        row for row in list(segments or [])
        if _intersection_boundary_key(row[0]) != _intersection_boundary_key(row[1])
    ]
    axis_aligned = _intersection_boundary_segments_axis_alignment_status(clean_segments)
    if axis_aligned is None:
        return [], [], []
    if not axis_aligned:
        polygon_points, polygon_rows, polygon_diagnostics = _intersection_boundary_construct_leg_frame_source_perimeter(
            clean_segments
        )
        if polygon_points:
            return polygon_points, polygon_rows, [
                "info:intersection_boundary_rectilinear_source_perimeter_skipped:non_axis_aligned_edges",
                *polygon_diagnostics,
            ]
        return [], [], [
            "warning:intersection_boundary_rectilinear_source_perimeter_skipped:non_axis_aligned_edges",
            *polygon_diagnostics,
        ]
    grouped_points: dict[str, list[tuple[float, float, float]]] = {}
    grouped_refs: dict[str, set[str]] = {}
    curb_index = 0
    for start, end, edge_id, edge_role, refs in clean_segments:
        role = str(edge_role or "").lower()
        if role in {"pavement_edge", "daylight_hinge"}:
            group_id = _intersection_boundary_leg_group_id(edge_id, refs)
            if not group_id:
                continue
        elif role in {"curb_return", "curb_return_edge", "curb_return_arc_segment"}:
            group_id = _intersection_boundary_curb_group_id(edge_id)
            if not group_id:
                curb_index += 1
                group_id = f"curb-return:{curb_index}"
        else:
            continue
        grouped_points.setdefault(group_id, []).extend([start, end])
        grouped_refs.setdefault(group_id, set()).update(str(ref or "") for ref in refs if str(ref or ""))

    rectangles: list[tuple[float, float, float, float, str, tuple[str, ...]]] = []
    for group_id, points in grouped_points.items():
        unique_keys = {_intersection_boundary_key(point) for point in points}
        if len(unique_keys) < 2:
            continue
        xmin = min(point[0] for point in points)
        xmax = max(point[0] for point in points)
        ymin = min(point[1] for point in points)
        ymax = max(point[1] for point in points)
        if xmax - xmin <= 1.0e-6 or ymax - ymin <= 1.0e-6:
            continue
        refs = tuple(sorted(grouped_refs.get(group_id, set())))
        rectangles.append((xmin, ymin, xmax, ymax, group_id, refs))
    if len(rectangles) < 2:
        return [], [], []

    xs = sorted({value for xmin, _ymin, xmax, _ymax, _group_id, _refs in rectangles for value in (xmin, xmax)})
    ys = sorted({value for _xmin, ymin, _xmax, ymax, _group_id, _refs in rectangles for value in (ymin, ymax)})
    if len(xs) < 2 or len(ys) < 2:
        return [], [], []

    occupied: set[tuple[int, int]] = set()
    cell_refs: dict[tuple[int, int], set[str]] = {}
    for ix in range(len(xs) - 1):
        for iy in range(len(ys) - 1):
            cx = (xs[ix] + xs[ix + 1]) * 0.5
            cy = (ys[iy] + ys[iy + 1]) * 0.5
            refs: set[str] = set()
            for xmin, ymin, xmax, ymax, _group_id, row_refs in rectangles:
                if xmin - 1.0e-9 <= cx <= xmax + 1.0e-9 and ymin - 1.0e-9 <= cy <= ymax + 1.0e-9:
                    refs.update(row_refs)
            if refs:
                key = (ix, iy)
                occupied.add(key)
                cell_refs[key] = refs
    if not occupied:
        return [], [], []

    raw_edges: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]] = []
    for ix, iy in sorted(occupied):
        refs = tuple(sorted(cell_refs.get((ix, iy), set())))
        edge_specs = (
            ((ix - 1, iy), (xs[ix], ys[iy]), (xs[ix], ys[iy + 1]), "west"),
            ((ix + 1, iy), (xs[ix + 1], ys[iy + 1]), (xs[ix + 1], ys[iy]), "east"),
            ((ix, iy - 1), (xs[ix + 1], ys[iy]), (xs[ix], ys[iy]), "south"),
            ((ix, iy + 1), (xs[ix], ys[iy + 1]), (xs[ix + 1], ys[iy + 1]), "north"),
        )
        for neighbor, start_xy, end_xy, side in edge_specs:
            if neighbor in occupied:
                continue
            side_refs = _intersection_boundary_rectilinear_side_owner_refs(
                rectangles,
                start_xy=(float(start_xy[0]), float(start_xy[1])),
                end_xy=(float(end_xy[0]), float(end_xy[1])),
                side=side,
                fallback_refs=refs,
            )
            edge_index = len(raw_edges) + 1
            raw_edges.append(
                (
                    (float(start_xy[0]), float(start_xy[1]), 0.0),
                    (float(end_xy[0]), float(end_xy[1]), 0.0),
                    f"intersection-source-perimeter:{edge_index:02d}:{side}",
                    "source_rectilinear_outer_perimeter",
                    side_refs,
                )
            )

    components = _intersection_boundary_segment_components(raw_edges)
    closed_components: list[
        tuple[
            list[tuple[float, float, float]],
            list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
        ]
    ] = []
    for component in components:
        points, rows, _diagnostics = _intersection_boundary_trace_single_closed_component(component)
        if points and rows:
            closed_components.append((points, rows))
    if len(closed_components) != 1:
        return [], [], [f"warning:intersection_boundary_source_perimeter_component_count:{len(closed_components)}"]

    points, rows = closed_components[0]
    points, rows, arc_diagnostics = _intersection_boundary_replace_rectilinear_curb_spans_with_arcs(points, rows, clean_segments)
    return points, rows, [
        "info:intersection_boundary_candidate_source=rectilinear_edge_network_envelope",
        f"info:intersection_boundary_source_perimeter_rectangles:{len(rectangles)}",
        *arc_diagnostics,
    ]


def _intersection_boundary_construct_leg_frame_source_perimeter(
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    list[str],
]:
    leg_groups: dict[str, dict[str, object]] = {}
    for start, end, edge_id, edge_role, refs in list(segments or []):
        role = str(edge_role or "").lower()
        if role not in {"pavement_edge", "daylight_hinge"}:
            continue
        group_id = _intersection_boundary_leg_group_id(edge_id, refs)
        if not group_id:
            continue
        row = leg_groups.setdefault(group_id, {"refs": set()})
        row["pavement" if role == "pavement_edge" else "daylight"] = (start, end)
        refs_set = row.setdefault("refs", set())
        if isinstance(refs_set, set):
            refs_set.update(str(ref or "") for ref in refs if str(ref or ""))

    polygons: list[tuple[list[tuple[float, float, float]], tuple[str, ...]]] = []
    for row in leg_groups.values():
        pavement = row.get("pavement")
        daylight = row.get("daylight")
        if not pavement or not daylight:
            continue
        pav_start, pav_end = pavement
        day_start, day_end = daylight
        points = [pav_start, pav_end, day_end, day_start, pav_start]
        if abs(_intersection_boundary_area_xy(points)) <= 1.0e-6:
            continue
        if _intersection_boundary_area_xy(points) < 0.0:
            points = list(reversed(points))
        refs = tuple(sorted(value for value in row.get("refs", set()) if str(value or "")))
        polygons.append((points, refs))
    if len(polygons) < 2:
        return [], [], ["warning:intersection_boundary_leg_frame_polygon_count_too_low"]

    split_edges: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]] = []
    for polygon_index, (polygon, refs) in enumerate(polygons, start=1):
        for edge_index, (start, end) in enumerate(zip(polygon[:-1], polygon[1:]), start=1):
            split_params = [0.0, 1.0]
            for other_polygon, _other_refs in polygons:
                if other_polygon is polygon:
                    continue
                for other_start, other_end in zip(other_polygon[:-1], other_polygon[1:]):
                    intersection = _intersection_boundary_segment_intersection_point(start, end, other_start, other_end)
                    if intersection is None:
                        continue
                    ratio = _intersection_boundary_segment_ratio(intersection, start, end)
                    if -1.0e-9 <= ratio <= 1.0 + 1.0e-9:
                        split_params.append(max(0.0, min(1.0, ratio)))
            ordered_params = _unique_sorted_float_values(split_params)
            for first_t, second_t in zip(ordered_params[:-1], ordered_params[1:]):
                if second_t - first_t <= 1.0e-9:
                    continue
                first = _interpolate_xyz(start, end, first_t)
                second = _interpolate_xyz(start, end, second_t)
                midpoint = _interpolate_xyz(first, second, 0.5)
                if any(
                    _intersection_boundary_point_strictly_inside_polygon(midpoint, other_polygon)
                    for other_polygon, _other_refs in polygons
                    if other_polygon is not polygon
                ):
                    continue
                split_edges.append(
                    (
                        first,
                        second,
                        f"intersection-leg-frame-source-perimeter:{polygon_index:02d}:{edge_index:02d}:{len(split_edges) + 1:02d}",
                        "source_leg_frame_outer_perimeter",
                        refs,
                    )
                )
    components = _intersection_boundary_segment_components(split_edges)
    closed_components: list[
        tuple[
            list[tuple[float, float, float]],
            list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
        ]
    ] = []
    for component in components:
        points, rows, _diagnostics = _intersection_boundary_trace_single_closed_component(component)
        if points and rows:
            closed_components.append((points, rows))
    if len(closed_components) != 1:
        return [], [], [f"warning:intersection_boundary_leg_frame_component_count:{len(closed_components)}"]
    points, rows = closed_components[0]
    return points, rows, [
        "info:intersection_boundary_candidate_source=leg_frame_source_polygon_envelope",
        f"info:intersection_boundary_leg_frame_polygon_count:{len(polygons)}",
    ]


def _intersection_boundary_replace_rectilinear_curb_spans_with_arcs(
    points: list[tuple[float, float, float]],
    rows: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    source_segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    list[str],
]:
    diagnostics: list[str] = []
    original_bbox = _intersection_boundary_bbox_xy(points)
    arc_groups: dict[str, list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]]] = {}
    for segment in source_segments:
        _start, _end, edge_id, edge_role, _refs = segment
        if str(edge_role or "").lower() != "curb_return_arc_segment":
            continue
        arc_groups.setdefault(_intersection_boundary_curb_group_id(edge_id), []).append(segment)
    if not arc_groups:
        return points, rows, diagnostics

    current_rows = list(rows)
    for group_id, arc_rows in arc_groups.items():
        ordered_arc_rows = sorted(arc_rows, key=lambda row: str(row[2]))
        if len(ordered_arc_rows) < 2:
            continue
        arc_start = ordered_arc_rows[0][0]
        arc_end = ordered_arc_rows[-1][1]
        span_candidates = _intersection_boundary_curb_span_candidates(current_rows, group_id, arc_start, arc_end)
        if span_candidates:
            best_mixed, best_count, negative_curb_ref_count, _start_index, reverse_arc_candidate, _curb_ref_count = min(span_candidates)
            diagnostics.append(
                f"info:intersection_boundary_curb_arc_span_candidates:{group_id}:"
                f"candidates={len(span_candidates)};best_mixed_rows={best_mixed};"
                f"best_span_rows={best_count};best_curb_rows={abs(negative_curb_ref_count)};"
                f"reverse={1 if reverse_arc_candidate else 0}"
            )
        replace_range = _intersection_boundary_curb_span_row_range(current_rows, group_id, arc_start, arc_end)
        if replace_range is None:
            diagnostics.append(f"warning:intersection_boundary_curb_arc_span_not_matched:{group_id}")
            continue
        start_index, count, reverse_arc, mixed_owner_count = replace_range
        if mixed_owner_count:
            bridge_note = _intersection_boundary_curb_span_bridge_note(
                current_rows,
                group_id,
                arc_start,
                arc_end,
            )
            if bridge_note:
                diagnostics.append(bridge_note)
            promotion_block_note = _intersection_boundary_curb_bridge_promotion_block_note(
                current_rows,
                group_id,
                start_index,
                count,
                original_bbox,
            )
            if promotion_block_note:
                diagnostics.append(promotion_block_note)
            diagnostics.append(
                f"warning:intersection_boundary_curb_arc_pure_span_missing:{group_id}:"
                f"best_mixed_rows={mixed_owner_count};span_rows={count}"
            )
            diagnostics.append(
                f"warning:intersection_boundary_curb_arc_span_mixed_ownership:{group_id}:"
                f"mixed_rows={mixed_owner_count};span_rows={count}"
            )
            continue
        replacement = [
            (end, start, edge_id, role, refs) if reverse_arc else (start, end, edge_id, role, refs)
            for start, end, edge_id, role, refs in (reversed(ordered_arc_rows) if reverse_arc else ordered_arc_rows)
        ]
        if start_index + count <= len(current_rows):
            current_rows = current_rows[:start_index] + replacement + current_rows[start_index + count:]
        else:
            rotated = current_rows[start_index:] + current_rows[:start_index]
            current_rows = replacement + rotated[count:]
        diagnostics.append(f"info:intersection_boundary_rectilinear_curb_span_replaced_by_arc:{group_id}:{len(replacement)}")

    if not current_rows:
        return points, rows, diagnostics
    rebuilt_points = [current_rows[0][0]]
    for row in current_rows:
        rebuilt_points.append(row[1])
    if not _points_closed_xy(rebuilt_points):
        diagnostics.append("warning:intersection_boundary_curb_arc_replacement_open_loop")
        return points, rows, diagnostics
    rebuilt_bbox = _intersection_boundary_bbox_xy(rebuilt_points)
    if any(abs(float(first) - float(second)) > 1.0e-6 for first, second in zip(original_bbox, rebuilt_bbox)):
        diagnostics.append(
            "warning:intersection_boundary_curb_arc_replacement_bbox_changed:"
            f"original={_intersection_boundary_bbox_note(original_bbox)};"
            f"replacement={_intersection_boundary_bbox_note(rebuilt_bbox)}"
        )
        return points, rows, diagnostics
    if _polyline_self_crosses_xy(rebuilt_points):
        diagnostics.append("warning:intersection_boundary_curb_arc_replacement_self_crossing_rejected")
        return points, rows, diagnostics
    return rebuilt_points, current_rows, diagnostics


def _intersection_boundary_rectilinear_side_owner_refs(
    rectangles: list[tuple[float, float, float, float, str, tuple[str, ...]]],
    *,
    start_xy: tuple[float, float],
    end_xy: tuple[float, float],
    side: str,
    fallback_refs: tuple[str, ...],
) -> tuple[str, ...]:
    """Return refs for rectangles that actually own a rectilinear outer side."""

    axis = str(side or "").lower()
    x1, y1 = float(start_xy[0]), float(start_xy[1])
    x2, y2 = float(end_xy[0]), float(end_xy[1])
    segment_xmin = min(x1, x2)
    segment_xmax = max(x1, x2)
    segment_ymin = min(y1, y2)
    segment_ymax = max(y1, y2)
    owner_refs: set[str] = set()
    for xmin, ymin, xmax, ymax, _group_id, refs in rectangles:
        if axis in {"west", "east"}:
            side_x = xmin if axis == "west" else xmax
            if abs(side_x - x1) > 1.0e-6 or abs(side_x - x2) > 1.0e-6:
                continue
            if segment_ymin < ymin - 1.0e-6 or segment_ymax > ymax + 1.0e-6:
                continue
        elif axis in {"south", "north"}:
            side_y = ymin if axis == "south" else ymax
            if abs(side_y - y1) > 1.0e-6 or abs(side_y - y2) > 1.0e-6:
                continue
            if segment_xmin < xmin - 1.0e-6 or segment_xmax > xmax + 1.0e-6:
                continue
        else:
            continue
        owner_refs.update(str(ref or "") for ref in refs if str(ref or ""))
        owner_refs.add(_intersection_boundary_rectilinear_owner_ref(_group_id, axis))
    if owner_refs:
        return tuple(sorted(owner_refs))
    return tuple(sorted(str(ref or "") for ref in fallback_refs if str(ref or "")))


def _intersection_boundary_bbox_note(bbox: tuple[float, float, float, float]) -> str:
    return ",".join(f"{float(value):.3f}" for value in bbox)


def _intersection_boundary_rectilinear_owner_ref(group_id: str, side: str) -> str:
    group = str(group_id or "unknown").strip() or "unknown"
    axis = str(side or "unknown").strip() or "unknown"
    return f"intersection-boundary-owner:{group}:{axis}"


def _intersection_boundary_refs_match_group(refs: tuple[str, ...], group_id: str) -> bool:
    group = str(group_id or "").strip()
    if not group:
        return False
    for ref in tuple(str(value or "") for value in tuple(refs or ())):
        if ref == group:
            return True
        if ref.startswith(f"intersection-boundary-owner:{group}:"):
            return True
    return False


def _intersection_boundary_curb_span_row_range(
    rows: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    group_id: str,
    arc_start: tuple[float, float, float],
    arc_end: tuple[float, float, float],
) -> tuple[int, int, bool, int] | None:
    candidates = _intersection_boundary_curb_span_candidates(rows, group_id, arc_start, arc_end)
    if candidates:
        mixed_owner_count, count, _negative_curb_ref_count, start_index, reverse_arc, _curb_ref_count = min(candidates)
        return (start_index, count, reverse_arc, mixed_owner_count)
    return None


def _intersection_boundary_curb_span_candidates(
    rows: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    group_id: str,
    arc_start: tuple[float, float, float],
    arc_end: tuple[float, float, float],
) -> list[tuple[int, int, int, int, bool, int]]:
    if not rows:
        return []
    n = len(rows)
    candidates: list[tuple[int, int, int, int, bool, int]] = []
    for reverse_arc, first, last in ((False, arc_start, arc_end), (True, arc_end, arc_start)):
        for start_index in range(n):
            if not _same_xy(rows[start_index][0], first):
                continue
            index = start_index
            count = 0
            curb_ref_count = 0
            mixed_owner_count = 0
            while count < n:
                row = rows[index % n]
                if _intersection_boundary_refs_match_group(row[4], group_id):
                    curb_ref_count += 1
                else:
                    mixed_owner_count += 1
                count += 1
                if _same_xy(row[1], last):
                    candidates.append((mixed_owner_count, count, -curb_ref_count, start_index, reverse_arc, curb_ref_count))
                    break
                index += 1
    return candidates


def _intersection_boundary_curb_span_bridge_note(
    rows: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    group_id: str,
    arc_start: tuple[float, float, float],
    arc_end: tuple[float, float, float],
) -> str:
    curb_rows = [row for row in list(rows or []) if _intersection_boundary_refs_match_group(row[4], group_id)]
    if not curb_rows:
        return ""
    points = [arc_start, arc_end]
    for start, end, _edge_id, _role, _refs in curb_rows:
        points.extend([start, end])
    xmin = min(float(point[0]) for point in points)
    xmax = max(float(point[0]) for point in points)
    ymin = min(float(point[1]) for point in points)
    ymax = max(float(point[1]) for point in points)
    bbox_points = [
        (xmin, ymin, 0.0),
        (xmax, ymin, 0.0),
        (xmax, ymax, 0.0),
        (xmin, ymax, 0.0),
        (xmin, ymin, 0.0),
    ]
    start_index = _intersection_boundary_matching_point_index(bbox_points[:-1], arc_start)
    end_index = _intersection_boundary_matching_point_index(bbox_points[:-1], arc_end)
    if start_index < 0 or end_index < 0:
        return ""
    paths: list[list[tuple[float, float, float]]] = []
    path = [bbox_points[start_index]]
    index = start_index
    while index != end_index:
        index = (index + 1) % 4
        path.append(bbox_points[index])
    paths.append(path)
    path = [bbox_points[start_index]]
    index = start_index
    while index != end_index:
        index = (index - 1) % 4
        path.append(bbox_points[index])
    paths.append(path)

    best_missing_count = 10**9
    best_segment_count = 0
    best_missing: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    for candidate_path in paths:
        missing: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
        segment_count = 0
        for start, end in zip(candidate_path[:-1], candidate_path[1:]):
            if _same_xy(start, end):
                continue
            segment_count += 1
            missing.extend(_intersection_boundary_missing_curb_owned_subsegments(curb_rows, start, end))
        if len(missing) < best_missing_count:
            best_missing_count = len(missing)
            best_segment_count = segment_count
            best_missing = missing
    if best_missing_count <= 0:
        return ""
    sample = ",".join(
        f"{_intersection_boundary_key_note(_intersection_boundary_key(start))}->{_intersection_boundary_key_note(_intersection_boundary_key(end))}"
        for start, end in best_missing[:4]
    )
    return (
        f"warning:intersection_boundary_curb_arc_bridge_required:{group_id}:"
        f"missing_segments={best_missing_count};candidate_segments={best_segment_count};"
        f"sample={sample}"
    )


def _intersection_boundary_matching_point_index(
    points: list[tuple[float, float, float]],
    target: tuple[float, float, float],
) -> int:
    for index, point in enumerate(points):
        if _same_xy(point, target):
            return index
    return -1


def _intersection_boundary_has_curb_owned_segment(
    rows: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> bool:
    for row_start, row_end, _edge_id, _role, _refs in rows:
        if (_same_xy(row_start, start) and _same_xy(row_end, end)) or (
            _same_xy(row_start, end) and _same_xy(row_end, start)
        ):
            return True
    return False


def _intersection_boundary_missing_curb_owned_subsegments(
    rows: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    if _same_xy(start, end):
        return []
    dx = abs(float(end[0]) - float(start[0]))
    dy = abs(float(end[1]) - float(start[1]))
    if dx > 1.0e-6 and dy > 1.0e-6:
        return [] if _intersection_boundary_has_curb_owned_segment(rows, start, end) else [(start, end)]
    covered: list[tuple[float, float]] = []
    for row_start, row_end, _edge_id, _role, _refs in rows:
        if dx <= 1.0e-6:
            if abs(float(row_start[0]) - float(start[0])) > 1.0e-6 or abs(float(row_end[0]) - float(start[0])) > 1.0e-6:
                continue
            first = (float(row_start[1]) - float(start[1])) / ((float(end[1]) - float(start[1])) or 1.0e-18)
            second = (float(row_end[1]) - float(start[1])) / ((float(end[1]) - float(start[1])) or 1.0e-18)
        else:
            if abs(float(row_start[1]) - float(start[1])) > 1.0e-6 or abs(float(row_end[1]) - float(start[1])) > 1.0e-6:
                continue
            first = (float(row_start[0]) - float(start[0])) / ((float(end[0]) - float(start[0])) or 1.0e-18)
            second = (float(row_end[0]) - float(start[0])) / ((float(end[0]) - float(start[0])) or 1.0e-18)
        low = max(0.0, min(1.0, min(first, second)))
        high = max(0.0, min(1.0, max(first, second)))
        if high - low > 1.0e-9:
            covered.append((low, high))
    if not covered:
        return [(start, end)]
    covered.sort()
    merged: list[tuple[float, float]] = []
    for low, high in covered:
        if not merged or low > merged[-1][1] + 1.0e-9:
            merged.append((low, high))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
    missing: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    cursor = 0.0
    for low, high in merged:
        if low - cursor > 1.0e-9:
            missing.append((_interpolate_xyz(start, end, cursor), _interpolate_xyz(start, end, low)))
        cursor = max(cursor, high)
    if 1.0 - cursor > 1.0e-9:
        missing.append((_interpolate_xyz(start, end, cursor), end))
    return missing


def _intersection_boundary_curb_bridge_promotion_block_note(
    rows: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    group_id: str,
    start_index: int,
    count: int,
    bbox: tuple[float, float, float, float],
) -> str:
    if not rows or count <= 0:
        return ""
    xmin, ymin, xmax, ymax = bbox
    bbox_owner_hits: list[str] = []
    for offset in range(count):
        row = rows[(start_index + offset) % len(rows)]
        start, end, edge_id, _role, refs = row
        if _intersection_boundary_refs_match_group(refs, group_id):
            continue
        hit_axes: list[str] = []
        for point in (start, end):
            if abs(float(point[0]) - float(xmin)) <= 1.0e-6:
                hit_axes.append("xmin")
            if abs(float(point[0]) - float(xmax)) <= 1.0e-6:
                hit_axes.append("xmax")
            if abs(float(point[1]) - float(ymin)) <= 1.0e-6:
                hit_axes.append("ymin")
            if abs(float(point[1]) - float(ymax)) <= 1.0e-6:
                hit_axes.append("ymax")
        if hit_axes:
            bbox_owner_hits.append(f"{edge_id}:{','.join(_unique_text_values(hit_axes))}")
    if not bbox_owner_hits:
        return ""
    return (
        f"warning:intersection_boundary_curb_arc_bridge_promotion_blocked:{group_id}:"
        "mixed_span_contains_outer_bbox_edges="
        + ",".join(bbox_owner_hits[:4])
    )


def _intersection_boundary_segments_axis_alignment_status(
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
) -> bool | None:
    checked = 0
    for start, end, _edge_id, edge_role, _refs in list(segments or []):
        role = str(edge_role or "").lower()
        if role not in {"pavement_edge", "daylight_hinge"}:
            continue
        checked += 1
        dx = abs(float(end[0]) - float(start[0]))
        dy = abs(float(end[1]) - float(start[1]))
        if dx > 1.0e-6 and dy > 1.0e-6:
            return False
    return None if checked <= 0 else True


def _intersection_boundary_edge_arc_points(
    edge,
    start_point: tuple[float, float, float],
    end_point: tuple[float, float, float],
) -> tuple[tuple[float, float, float], ...]:
    raw_points = tuple(getattr(edge, "arc_points_xyz", ()) or ())
    points = [_xyz_tuple_or_none(point) for point in raw_points]
    normalized = [point for point in points if point is not None]
    if len(normalized) < 3:
        return ()
    normalized[0] = start_point
    normalized[-1] = end_point
    return tuple(normalized)


def _intersection_boundary_curb_group_id(edge_id: str) -> str:
    text = str(edge_id or "")
    if ":arc-segment:" in text:
        return text.rsplit(":arc-segment:", 1)[0]
    return text


def _intersection_boundary_segment_intersection_point(
    first_start: tuple[float, float, float],
    first_end: tuple[float, float, float],
    second_start: tuple[float, float, float],
    second_end: tuple[float, float, float],
    tolerance: float = 1.0e-9,
) -> tuple[float, float, float] | None:
    x1, y1 = float(first_start[0]), float(first_start[1])
    x2, y2 = float(first_end[0]), float(first_end[1])
    x3, y3 = float(second_start[0]), float(second_start[1])
    x4, y4 = float(second_end[0]), float(second_end[1])
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denominator) <= tolerance:
        return None
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator
    point = (float(px), float(py), 0.0)
    if (
        min(x1, x2) - tolerance <= px <= max(x1, x2) + tolerance
        and min(y1, y2) - tolerance <= py <= max(y1, y2) + tolerance
        and min(x3, x4) - tolerance <= px <= max(x3, x4) + tolerance
        and min(y3, y4) - tolerance <= py <= max(y3, y4) + tolerance
    ):
        return point
    return None


def _intersection_boundary_segment_ratio(
    point: tuple[float, float, float],
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> float:
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    denominator = dx * dx + dy * dy
    if denominator <= 1.0e-18:
        return 0.0
    return ((float(point[0]) - float(start[0])) * dx + (float(point[1]) - float(start[1])) * dy) / denominator


def _interpolate_xyz(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    ratio: float,
) -> tuple[float, float, float]:
    t = float(ratio)
    return (
        float(start[0]) + (float(end[0]) - float(start[0])) * t,
        float(start[1]) + (float(end[1]) - float(start[1])) * t,
        float(start[2]) + (float(end[2]) - float(start[2])) * t,
    )


def _unique_sorted_float_values(values: list[float], tolerance: float = 1.0e-9) -> list[float]:
    ordered: list[float] = []
    for value in sorted(float(item) for item in values):
        if not ordered or abs(value - ordered[-1]) > tolerance:
            ordered.append(value)
    return ordered


def _intersection_boundary_point_strictly_inside_polygon(
    point: tuple[float, float, float],
    polygon: list[tuple[float, float, float]],
    tolerance: float = 1.0e-9,
) -> bool:
    x = float(point[0])
    y = float(point[1])
    inside = False
    for start, end in zip(polygon[:-1], polygon[1:]):
        if _intersection_boundary_point_on_segment_xy(point, start, end, tolerance=tolerance):
            return False
        x1, y1 = float(start[0]), float(start[1])
        x2, y2 = float(end[0]), float(end[1])
        if (y1 > y) != (y2 > y):
            x_cross = (x2 - x1) * (y - y1) / ((y2 - y1) or 1.0e-18) + x1
            if x < x_cross:
                inside = not inside
    return inside


def _intersection_boundary_point_on_segment_xy(
    point: tuple[float, float, float],
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    tolerance: float = 1.0e-9,
) -> bool:
    cross = (float(point[0]) - float(start[0])) * (float(end[1]) - float(start[1])) - (
        float(point[1]) - float(start[1])
    ) * (float(end[0]) - float(start[0]))
    if abs(cross) > tolerance:
        return False
    return (
        min(float(start[0]), float(end[0])) - tolerance <= float(point[0]) <= max(float(start[0]), float(end[0])) + tolerance
        and min(float(start[1]), float(end[1])) - tolerance <= float(point[1]) <= max(float(start[1]), float(end[1])) + tolerance
    )


def _intersection_boundary_leg_group_id(edge_id: str, refs: tuple[str, ...]) -> str:
    for value in list(refs or ()):
        text = str(value or "").strip()
        if text.startswith("leg:"):
            return text
    parts = str(edge_id or "").split(":")
    for part in parts:
        if part.startswith("leg-") or part.startswith("leg_"):
            return part
    return ""


def _intersection_boundary_trace_source_loop_groups(
    clean_segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
) -> list[
    tuple[
        list[tuple[float, float, float]],
        list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    ]
]:
    grouped: dict[str, list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]]] = {}
    for row in clean_segments:
        _start, _end, edge_id, edge_role, _refs = row
        if edge_role != "intersection_slope_face_loop_boundary" or ":segment:" not in edge_id:
            continue
        group_id = edge_id.rsplit(":segment:", 1)[0]
        grouped.setdefault(group_id, []).append(row)

    closed_groups: list[
        tuple[
            list[tuple[float, float, float]],
            list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
        ]
    ] = []
    for rows in grouped.values():
        points, ordered_rows, _diagnostics = _intersection_boundary_trace_single_closed_component(rows)
        if points and ordered_rows:
            closed_groups.append((points, ordered_rows))
    return closed_groups


def _intersection_boundary_segment_components(
    clean_segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
) -> list[list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]]]:
    node_to_segments: dict[tuple[float, float], list[int]] = {}
    segment_nodes: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for index, (start, end, _edge_id, _role, _refs) in enumerate(clean_segments):
        start_key = _intersection_boundary_key(start)
        end_key = _intersection_boundary_key(end)
        segment_nodes.append((start_key, end_key))
        node_to_segments.setdefault(start_key, []).append(index)
        node_to_segments.setdefault(end_key, []).append(index)

    components: list[list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]]] = []
    remaining = set(range(len(clean_segments)))
    while remaining:
        root = next(iter(remaining))
        stack = [root]
        indexes: set[int] = set()
        remaining.remove(root)
        while stack:
            segment_index = stack.pop()
            indexes.add(segment_index)
            for node_key in segment_nodes[segment_index]:
                for neighbor_index in node_to_segments.get(node_key, []):
                    if neighbor_index in remaining:
                        remaining.remove(neighbor_index)
                        stack.append(neighbor_index)
        components.append([clean_segments[index] for index in sorted(indexes)])
    return components


def _intersection_boundary_trace_single_closed_component(
    clean_segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]],
    list[str],
]:
    diagnostics: list[str] = []
    adjacency: dict[tuple[float, float], list[int]] = {}
    point_by_key: dict[tuple[float, float], tuple[float, float, float]] = {}
    for index, (start, end, _edge_id, _role, _refs) in enumerate(clean_segments):
        start_key = _intersection_boundary_key(start)
        end_key = _intersection_boundary_key(end)
        point_by_key.setdefault(start_key, start)
        point_by_key.setdefault(end_key, end)
        adjacency.setdefault(start_key, []).append(index)
        adjacency.setdefault(end_key, []).append(index)
    invalid_degrees = {key: len(values) for key, values in adjacency.items() if len(values) != 2}
    if invalid_degrees:
        sample = ",".join(f"{key[0]:.3f}:{key[1]:.3f}={degree}" for key, degree in list(invalid_degrees.items())[:8])
        diagnostics.append(f"warning:intersection_boundary_graph_degree_invalid:{sample}")
        return [], [], diagnostics

    start_key = min(adjacency.keys())
    ordered_keys = [start_key]
    ordered_segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, tuple[str, ...]]] = []
    used: set[int] = set()
    current_key = start_key
    previous_segment = -1
    while True:
        next_segment = None
        for segment_index in adjacency.get(current_key, []):
            if segment_index == previous_segment or segment_index in used:
                continue
            next_segment = segment_index
            break
        if next_segment is None:
            break
        used.add(next_segment)
        start, end, edge_id, edge_role, refs = clean_segments[next_segment]
        start_key_for_segment = _intersection_boundary_key(start)
        end_key_for_segment = _intersection_boundary_key(end)
        if start_key_for_segment == current_key:
            next_key = end_key_for_segment
            ordered_segments.append((start, end, edge_id, edge_role, refs))
        else:
            next_key = start_key_for_segment
            ordered_segments.append((end, start, edge_id, edge_role, refs))
        if next_key == start_key:
            ordered_keys.append(next_key)
            break
        ordered_keys.append(next_key)
        previous_segment = next_segment
        current_key = next_key
        if len(ordered_segments) > len(clean_segments):
            diagnostics.append("warning:intersection_boundary_graph_trace_overrun")
            return [], [], diagnostics
    if len(used) != len(clean_segments) or ordered_keys[-1] != start_key:
        diagnostics.append(
            f"warning:intersection_boundary_graph_chain_unclosed:used={len(used)}/{len(clean_segments)}"
        )
        return [], [], diagnostics
    ordered_points = [point_by_key[key] for key in ordered_keys]
    if len(ordered_points) >= 3 and _intersection_boundary_area_xy(ordered_points) < 0.0:
        ordered_points = list(reversed(ordered_points))
        ordered_segments = [(end, start, edge_id, edge_role, refs) for start, end, edge_id, edge_role, refs in reversed(ordered_segments)]
    return ordered_points, ordered_segments, diagnostics


def _intersection_boundary_convex_hull_xyz(points: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    point_by_key: dict[tuple[float, float], tuple[float, float, float]] = {}
    for point in points:
        point_by_key.setdefault(_intersection_boundary_key(point), point)
    ordered = sorted(point_by_key.items(), key=lambda item: (item[0][0], item[0][1]))
    if len(ordered) <= 1:
        return [point for _key, point in ordered]

    def cross(origin, first, second) -> float:
        return (first[0] - origin[0]) * (second[1] - origin[1]) - (first[1] - origin[1]) * (second[0] - origin[0])

    lower: list[tuple[float, float]] = []
    for key, _point in ordered:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], key) <= 0.0:
            lower.pop()
        lower.append(key)
    upper: list[tuple[float, float]] = []
    for key, _point in reversed(ordered):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], key) <= 0.0:
            upper.pop()
        upper.append(key)
    hull_keys = lower[:-1] + upper[:-1]
    hull = [point_by_key[key] for key in hull_keys if key in point_by_key]
    if len(hull) >= 3 and _intersection_boundary_area_xy(hull) < 0.0:
        hull.reverse()
    return hull


def _intersection_boundary_area_xy(points: list[tuple[float, float, float]]) -> float:
    area = 0.0
    if len(points) < 3:
        return 0.0
    for current, nxt in zip(points, points[1:] + [points[0]]):
        area += float(current[0]) * float(nxt[1])
        area -= float(nxt[0]) * float(current[1])
    return area * 0.5


def _intersection_boundary_bbox_xy(points: list[tuple[float, float, float]]) -> tuple[float, float, float, float]:
    if not points:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _intersection_boundary_segment_role(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    loop_points: list[tuple[float, float, float]],
) -> str:
    bbox = _intersection_boundary_bbox_xy(loop_points)
    x_mid = (bbox[0] + bbox[2]) * 0.5
    y_mid = (bbox[1] + bbox[3]) * 0.5
    dx = abs(float(second[0]) - float(first[0]))
    dy = abs(float(second[1]) - float(first[1]))
    segment_mid_x = (float(first[0]) + float(second[0])) * 0.5
    segment_mid_y = (float(first[1]) + float(second[1])) * 0.5
    if dx >= dy and segment_mid_y >= y_mid:
        return "patch_to_design_surface"
    if dx >= dy and segment_mid_y < y_mid:
        return "curb_return_to_intersection_slope_face"
    if segment_mid_x < x_mid:
        return "intersection_slope_face_to_corridor_slope_face"
    return "main_road_tie"


def _intersection_boundary_segment_role_from_edge_role(
    edge_role: str,
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    loop_points: list[tuple[float, float, float]],
    *,
    source_refs: tuple[str, ...] = (),
) -> str:
    role = str(edge_role or "").lower()
    if _intersection_boundary_is_side_road_tie_segment(first, second, loop_points, source_refs):
        return "side_road_tie"
    if "slope_face_loop" in role:
        return "intersection_slope_face_to_corridor_slope_face"
    if "curb" in role:
        return "curb_return_to_intersection_slope_face"
    if "daylight" in role or "slope" in role:
        return "intersection_slope_face_to_corridor_slope_face"
    if "pavement" in role or "lane" in role:
        return "patch_to_design_surface"
    return _intersection_boundary_segment_role(first, second, loop_points)


def _intersection_boundary_is_side_road_tie_segment(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    loop_points: list[tuple[float, float, float]],
    source_refs: tuple[str, ...],
) -> bool:
    refs = tuple(str(value or "").lower() for value in tuple(source_refs or ()))
    if not refs:
        return False
    if not any("leg:02" in ref or "leg-02" in ref or "intersection-secondary" in ref for ref in refs):
        return False
    if any("curb-return" in ref or "corner:" in ref for ref in refs):
        return False
    bbox = _intersection_boundary_bbox_xy(loop_points)
    dx = abs(float(second[0]) - float(first[0]))
    dy = abs(float(second[1]) - float(first[1]))
    if dx < dy:
        return False
    segment_mid_y = (float(first[1]) + float(second[1])) * 0.5
    y_span = max(1.0e-9, float(bbox[3]) - float(bbox[1]))
    near_side_road_end = abs(segment_mid_y - float(bbox[1])) <= max(1.0e-6, y_span * 0.05)
    return near_side_road_end


def _intersection_boundary_expected_consumers(segment_role: str) -> tuple[str, ...]:
    if segment_role == "patch_to_design_surface":
        return ("intersection_surface", "design_surface", "intersection_slope_face_surface")
    if segment_role == "curb_return_to_intersection_slope_face":
        return ("intersection_surface", "intersection_slope_face_surface")
    if segment_role == "intersection_slope_face_to_corridor_slope_face":
        return ("intersection_slope_face_surface", "slope_face_surface")
    if segment_role in {"main_road_tie", "side_road_tie"}:
        return ("intersection_surface", "design_surface", "intersection_slope_face_surface")
    return ("intersection_surface",)


def _range_tuple(value: object) -> tuple[tuple[float, float], ...]:
    ranges: list[tuple[float, float]] = []
    if not isinstance(value, list):
        return ()
    for item in value:
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            ranges.append((float(item[0]), float(item[1])))
    return tuple(ranges)


def _unique_text_values(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in output:
            output.append(text)
    return output


def _control_area_region_lineage_status(
    intent_status: str,
    source_region_refs: tuple[str, ...],
    result_region_refs: tuple[str, ...],
) -> str:
    intent = str(intent_status or "").strip()
    source_refs = {str(ref) for ref in source_region_refs if str(ref)}
    result_refs = {str(ref) for ref in result_region_refs if str(ref)}
    if intent == "region_derived" and not source_refs:
        return "source_region_missing"
    if source_refs and result_refs and source_refs != result_refs:
        return "region_ref_mismatch"
    if source_refs and source_refs == result_refs:
        return "matched"
    if result_refs:
        return "result_only"
    return "missing"


def _control_area_region_handoff_status(region_lineage_status: str, source_diagnostics: list[str]) -> str:
    if str(region_lineage_status or "") in {"matched", "result_only"} and not source_diagnostics:
        return "accepted"
    if str(region_lineage_status or "") in {"matched", "result_only"}:
        return "review_required"
    if str(region_lineage_status or "") in {"source_region_missing", "region_ref_mismatch", "missing"}:
        return "incomplete"
    return "review_required"


def _control_area_clipping_handoff_status(
    clipping_boundary_ref: str,
    station_ranges: tuple[tuple[float, float], ...],
    source_diagnostics: list[str],
) -> str:
    if not str(clipping_boundary_ref or ""):
        return "missing"
    if not station_ranges:
        return "missing"
    if source_diagnostics:
        return "review_required"
    return "accepted"


def _anchor_station_lineage_status(
    primary_alignment_ref: str,
    secondary_station_refs: tuple[tuple[str, float], ...],
    expected_secondary_alignment_refs: list[object] | tuple[object, ...],
    source_diagnostics: list[str],
) -> str:
    if any(str(item).startswith("source_anchor_primary_alignment_ref_missing") for item in source_diagnostics):
        return "primary_missing"
    if any(str(item).startswith("source_anchor_primary_alignment_ref_mismatch") for item in source_diagnostics):
        return "primary_mismatch"
    if not str(primary_alignment_ref or "").strip():
        return "primary_missing"
    expected_secondary = tuple(str(ref) for ref in list(expected_secondary_alignment_refs or []) if str(ref))
    actual_secondary = tuple(str(ref) for ref, _station in tuple(secondary_station_refs or ()) if str(ref))
    if expected_secondary and not actual_secondary:
        return "secondary_missing"
    if expected_secondary and set(expected_secondary) != set(actual_secondary):
        return "secondary_partial"
    if source_diagnostics:
        return "source_warning"
    return "accepted"


def _anchor_source_status(source_diagnostics: list[str]) -> str:
    if any(
        str(item).startswith("source_anchor_primary_alignment_ref_missing")
        for item in list(source_diagnostics or [])
    ):
        return "error"
    if source_diagnostics:
        return "warning"
    return "accepted"


def _leg_source_status(source_diagnostics: list[str]) -> str:
    if any(str(item) == "missing_alignment" for item in list(source_diagnostics or [])):
        return "error"
    if source_diagnostics:
        return "warning"
    return "accepted"


def _control_area_source_status(source_diagnostics: list[str]) -> str:
    if any(
        str(item) in {"missing_alignment", "missing_station_range"}
        for item in list(source_diagnostics or [])
    ):
        return "error"
    if source_diagnostics:
        return "warning"
    return "accepted"


def _corner_source_status(source_diagnostics: list[str]) -> str:
    blocking = {
        "source_curb_return_corner_ref_missing",
        "source_curb_return_corner_ref_unresolved",
        "source_corner_control_area_ref_missing",
        "source_corner_from_leg_ref_missing",
        "source_corner_to_leg_ref_missing",
        "source_corner_side_ref_missing",
        "source_corner_curb_return_policy_ref_missing",
        "source_corner_curb_return_policy_ref_mismatch",
    }
    if any(str(item) in blocking for item in list(source_diagnostics or [])):
        return "error"
    if source_diagnostics:
        return "warning"
    return "accepted"


def _edge_family_source_status(source_diagnostics: list[str]) -> str:
    blocking = {
        "source_edge_family_source_policy_ref_missing",
        "source_edge_family_subassembly_kind_missing",
        "source_edge_family_subassembly_kind_mismatch",
    }
    if any(str(item) in blocking for item in list(source_diagnostics or [])):
        return "error"
    if source_diagnostics:
        return "warning"
    return "accepted"


def _lane_connection_edge_policy_lineage(
    policy: IntersectionEdgePolicyRow | None,
    policy_ref: str,
) -> tuple[str, str, tuple[str, ...]]:
    if not str(policy_ref or ""):
        return "", "", ()
    if policy is None:
        return "", "missing", ("source_edge_policy_ref_unresolved",)
    diagnostics: list[str] = []
    edge_family_intent = str(getattr(policy, "edge_family_intent", "") or "")
    source_method = str(getattr(policy, "source_method", "") or "manual")
    approval_status = str(getattr(policy, "approval_status", "") or "accepted")
    subassembly_kind = str(getattr(policy, "subassembly_kind", "") or "")
    source_policy_ref = str(getattr(policy, "source_policy_ref", "") or "")
    for diagnostic in list(getattr(policy, "diagnostic_rows", []) or []):
        text = str(diagnostic or "").strip()
        if text:
            diagnostics.append(text)
    if not edge_family_intent:
        diagnostics.append("source_edge_family_intent_missing")
    elif edge_family_intent not in _VALID_EDGE_FAMILY_INTENTS:
        diagnostics.append("source_edge_family_intent_unknown")
    if approval_status not in {"accepted", "locked"}:
        diagnostics.append("source_edge_family_approval_pending")
    if approval_status and approval_status not in _VALID_EDGE_POLICY_APPROVAL_STATUSES:
        diagnostics.append("source_edge_family_approval_status_unknown")
    if not source_method:
        diagnostics.append("source_edge_family_method_missing")
    elif source_method not in _VALID_EDGE_POLICY_SOURCE_METHODS:
        diagnostics.append("source_edge_family_method_unknown")
    if source_method == "subassembly_bridge" and not source_policy_ref:
        diagnostics.append("source_edge_family_source_policy_ref_missing")
    if source_method.startswith("subassembly") and not subassembly_kind:
        diagnostics.append("source_edge_family_subassembly_kind_missing")
    if subassembly_kind and edge_family_intent and edge_family_intent in _VALID_EDGE_FAMILY_INTENTS and subassembly_kind != edge_family_intent:
        diagnostics.append("source_edge_family_subassembly_kind_mismatch")
    return edge_family_intent, _edge_family_source_status(diagnostics), tuple(diagnostics)


def _lane_connection_movement_lineage_status(diagnostics: list[str]) -> str:
    if any("missing" in item or "unresolved" in item for item in diagnostics):
        return "incomplete"
    if diagnostics:
        return "warning"
    return "connected"


def _lane_connection_source_status(source_diagnostics: list[str]) -> str:
    blocking_exact = {
        "source_lane_connection_from_leg_missing",
        "source_lane_connection_from_leg_unresolved",
        "source_lane_connection_to_leg_missing",
        "source_lane_connection_to_leg_unresolved",
        "source_lane_connection_from_edge_policy_missing",
        "source_lane_connection_from_edge_policy_unresolved",
        "source_lane_connection_to_edge_policy_missing",
        "source_lane_connection_to_edge_policy_unresolved",
    }
    diagnostics = [str(item) for item in list(source_diagnostics or [])]
    if any(item in blocking_exact for item in diagnostics):
        return "error"
    if any(item in {"source_lane_connection_from_leg_status:error", "source_lane_connection_to_leg_status:error"} for item in diagnostics):
        return "error"
    if any(item.startswith("from_edge:") and _edge_family_source_status((item.removeprefix("from_edge:"),)) == "error" for item in diagnostics):
        return "error"
    if any(item.startswith("to_edge:") and _edge_family_source_status((item.removeprefix("to_edge:"),)) == "error" for item in diagnostics):
        return "error"
    if diagnostics:
        return "warning"
    return "accepted"


def _lane_connection_leg_handoff_status(
    from_leg_ref: str,
    to_leg_ref: str,
    from_leg_status: str,
    to_leg_status: str,
) -> str:
    if not str(from_leg_ref or "") or not str(to_leg_ref or ""):
        return "missing"
    statuses = {str(from_leg_status or "accepted"), str(to_leg_status or "accepted")}
    if "error" in statuses:
        return "incomplete"
    if any(status not in {"", "accepted"} for status in statuses):
        return "review_required"
    return "accepted"


def _lane_connection_edge_handoff_status(
    from_edge_policy_ref: str,
    to_edge_policy_ref: str,
    from_edge_status: str,
    to_edge_status: str,
    from_edge_diagnostics: tuple[str, ...],
    to_edge_diagnostics: tuple[str, ...],
) -> str:
    if not str(from_edge_policy_ref or "") or not str(to_edge_policy_ref or ""):
        return "missing"
    statuses = {str(from_edge_status or "accepted"), str(to_edge_status or "accepted")}
    if "error" in statuses or "missing" in statuses or any("unresolved" in item for item in (*from_edge_diagnostics, *to_edge_diagnostics)):
        return "incomplete"
    if any(status not in {"", "accepted"} for status in statuses) or from_edge_diagnostics or to_edge_diagnostics:
        return "review_required"
    return "accepted"


def _grading_profile_lineage_status(controlling_profile_ref: str, policy: object | None) -> str:
    if policy is None:
        return "policy_missing"
    if str(controlling_profile_ref or "").strip():
        return "explicit"
    return "missing"


def _grading_profile_handoff_status(profile_lineage_status: str, source_diagnostics: list[str]) -> str:
    lineage = str(profile_lineage_status or "")
    if lineage == "policy_missing":
        return "blocked"
    if lineage == "missing":
        return "blocked"
    if source_diagnostics:
        return "review_required"
    return "accepted"


def _grading_superelevation_source_ref(policy: object | None, crossfall_context: str) -> str:
    if policy is None:
        return ""
    for attr in ("superelevation_ref", "superelevation_source_ref"):
        text = str(getattr(policy, attr, "") or "").strip()
        if text:
            return text
    return ""


def _grading_superelevation_source_status(crossfall_context: str, superelevation_source_ref: str) -> str:
    if crossfall_context == "normal_superelevation":
        return "referenced" if str(superelevation_source_ref or "").strip() else "normal_superelevation_context"
    return "intersection_policy_override"


def _grading_superelevation_handoff_status(superelevation_source_status: str) -> str:
    status = str(superelevation_source_status or "")
    if status == "referenced":
        return "accepted"
    if status == "normal_superelevation_context":
        return "inherited"
    if status == "intersection_policy_override":
        return "overridden"
    return "not_used"


def _grading_fallback_status(policy: object | None, mode: str, source_diagnostics: list[str]) -> str:
    if policy is None:
        return "policy_missing"
    if str(getattr(policy, "source_method", "") or "") in {"preset_default", "region_derived"}:
        return "defaulted"
    if source_diagnostics:
        return "source_warning"
    if str(mode or "") == "use_normal_superelevation":
        return "normal_superelevation"
    return "none"


def _grading_vertical_handoff_status(
    crossfall_context: str,
    profile_lineage_status: str,
    fallback_status: str,
    source_diagnostics: list[str],
) -> str:
    if fallback_status == "policy_missing":
        return "blocked"
    if source_diagnostics:
        return "warning"
    if crossfall_context == "intersection_override" and profile_lineage_status == "missing":
        return "blocked"
    return "ready"


def _grading_source_status(source_diagnostics: list[str], vertical_handoff_status: str) -> str:
    if str(vertical_handoff_status or "") == "blocked":
        return "error"
    if source_diagnostics:
        return "warning"
    return "accepted"


def _station_intersection_source_diagnostics(
    control_area: IntersectionControlArea,
    leg: IntersectionLegRow | None,
    *,
    alignment_ref: str,
    anchor_rows: list[IntersectionAnchorRow] | tuple[IntersectionAnchorRow, ...] = (),
    edge_policy_rows: list[IntersectionEdgePolicyRow] | tuple[IntersectionEdgePolicyRow, ...] = (),
) -> list[str]:
    diagnostics: list[str] = []
    anchors = list(anchor_rows or [])
    if not anchors:
        diagnostics.append("source_anchor_rows_missing")
    else:
        for anchor in anchors:
            approval_status = str(getattr(anchor, "approval_status", "") or "accepted")
            source_method = str(getattr(anchor, "source_method", "") or "manual")
            for diagnostic in list(getattr(anchor, "diagnostic_rows", []) or []):
                text = str(diagnostic or "").strip()
                if text:
                    diagnostics.append(text)
            if approval_status not in {"accepted", "locked"}:
                diagnostics.append("source_anchor_approval_pending")
            if approval_status and approval_status not in _VALID_ANCHOR_APPROVAL_STATUSES:
                diagnostics.append("source_anchor_approval_status_unknown")
            if not source_method:
                diagnostics.append("source_anchor_method_missing")
            elif source_method not in _VALID_ANCHOR_SOURCE_METHODS:
                diagnostics.append("source_anchor_method_unknown")
    if leg is None:
        diagnostics.append("source_leg_ref_missing_for_alignment" if alignment_ref else "source_leg_ref_missing")
    else:
        approval_status = str(getattr(leg, "approval_status", "") or "accepted")
        source_method = str(getattr(leg, "source_method", "") or "manual")
        span_source = str(getattr(leg, "span_source", "") or "explicit")
        for diagnostic in list(getattr(leg, "diagnostic_rows", []) or []):
            text = str(diagnostic or "").strip()
            if text:
                diagnostics.append(text)
        if approval_status not in {"accepted", "locked"}:
            diagnostics.append("source_leg_approval_pending")
        if approval_status and approval_status not in _VALID_LEG_APPROVAL_STATUSES:
            diagnostics.append("source_leg_approval_status_unknown")
        if not source_method:
            diagnostics.append("source_leg_method_missing")
        elif source_method not in _VALID_LEG_SOURCE_METHODS:
            diagnostics.append("source_leg_method_unknown")
        if not span_source:
            diagnostics.append("source_leg_span_source_missing")
        elif span_source not in _VALID_LEG_SPAN_SOURCES:
            diagnostics.append("source_leg_span_source_unknown")
        elif span_source != "explicit":
            diagnostics.append(f"source_leg_span_{span_source}")
        if not str(getattr(leg, "profile_ref", "") or "").strip():
            diagnostics.append("source_leg_profile_ref_missing")
        if not str(getattr(leg, "centerline3d_ref", "") or "").strip():
            diagnostics.append("source_leg_centerline3d_ref_missing")
        if not str(getattr(leg, "region_ref", "") or "").strip():
            diagnostics.append("source_leg_region_ref_missing")
        if not list(getattr(leg, "edge_policy_refs", []) or []):
            diagnostics.append("source_leg_edge_policy_refs_missing")
        else:
            edge_policy_by_id = {
                str(getattr(policy, "policy_id", "") or ""): policy
                for policy in list(edge_policy_rows or [])
                if str(getattr(policy, "policy_id", "") or "")
            }
            for edge_policy_ref in list(getattr(leg, "edge_policy_refs", []) or []):
                policy = edge_policy_by_id.get(str(edge_policy_ref or ""))
                if policy is None:
                    diagnostics.append("source_edge_policy_ref_unresolved")
                    continue
                approval_status = str(getattr(policy, "approval_status", "") or "accepted")
                source_method = str(getattr(policy, "source_method", "") or "manual")
                for diagnostic in list(getattr(policy, "diagnostic_rows", []) or []):
                    text = str(diagnostic or "").strip()
                    if text:
                        diagnostics.append(text)
                if approval_status not in {"accepted", "locked"}:
                    diagnostics.append("source_edge_policy_approval_pending")
                if not source_method:
                    diagnostics.append("source_edge_policy_method_missing")
    control_area_approval_status = str(getattr(control_area, "approval_status", "") or "accepted")
    control_area_source_method = str(getattr(control_area, "source_method", "") or "manual")
    control_area_intent_status = str(getattr(control_area, "intent_status", "") or "intersection_owned")
    control_region_refs = _unique_text_values(list(getattr(control_area, "control_region_refs", []) or []))
    source_region_refs = _unique_text_values(list(getattr(control_area, "source_region_refs", []) or []))
    for diagnostic in list(getattr(control_area, "diagnostic_rows", []) or []):
        text = str(diagnostic or "").strip()
        if text:
            diagnostics.append(text)
    if control_area_approval_status not in {"accepted", "locked"}:
        diagnostics.append("source_control_area_approval_pending")
    if control_area_approval_status and control_area_approval_status not in _VALID_CONTROL_AREA_APPROVAL_STATUSES:
        diagnostics.append("source_control_area_approval_status_unknown")
    if not control_area_source_method:
        diagnostics.append("source_control_area_method_missing")
    elif control_area_source_method not in _VALID_CONTROL_AREA_SOURCE_METHODS:
        diagnostics.append("source_control_area_method_unknown")
    if not control_area_intent_status:
        diagnostics.append("source_control_area_intent_missing")
    elif control_area_intent_status not in _VALID_CONTROL_AREA_INTENT_STATUSES:
        diagnostics.append("source_control_area_intent_unknown")
    elif control_area_intent_status != "intersection_owned":
        diagnostics.append(f"source_control_area_intent_{control_area_intent_status}")
    if control_area_intent_status == "region_derived" and not source_region_refs:
        diagnostics.append("source_control_area_source_region_refs_missing")
    if source_region_refs and control_region_refs and set(source_region_refs) != set(control_region_refs):
        diagnostics.append("source_control_area_region_ref_mismatch")
    if not list(getattr(control_area, "control_region_refs", []) or []):
        diagnostics.append("source_control_region_refs_missing")
    if not str(getattr(control_area, "curb_return_policy_ref", "") or "").strip():
        diagnostics.append("source_curb_return_policy_ref_missing")
    if not str(getattr(control_area, "grading_policy_ref", "") or "").strip():
        diagnostics.append("source_grading_policy_ref_missing")
    if not str(getattr(control_area, "drainage_policy_ref", "") or "").strip():
        diagnostics.append("source_drainage_policy_ref_missing")
    return diagnostics


def _topology_status(diagnostics: list[str]) -> str:
    if any(str(row).startswith("error:") for row in diagnostics):
        return "error"
    if diagnostics:
        return "warning"
    return "ready"


def _edge_network_endpoint_diagnostic(
    *,
    source_policy_ref: str,
    leg_ref: str,
    alignment_ref: str,
    control_area_ref: str,
    edge_family: str,
    station_start: float,
    station_end: float,
    start_xyz: tuple[float, float, float],
    end_xyz: tuple[float, float, float],
) -> str:
    start = _xyz_tuple(start_xyz)
    end = _xyz_tuple(end_xyz)
    if not _same_xy(start, end):
        return ""
    return (
        "edge_network_endpoint_degenerate:"
        f"policy={source_policy_ref or 'missing'};"
        f"leg={leg_ref or 'missing'};"
        f"alignment={alignment_ref or 'missing'};"
        f"control_area={control_area_ref or 'missing'};"
        f"edge_family={edge_family or 'missing'};"
        f"station={float(station_start):.3f}-{float(station_end):.3f};"
        f"start={start[0]:.3f},{start[1]:.3f},{start[2]:.3f};"
        f"end={end[0]:.3f},{end[1]:.3f},{end[2]:.3f}"
    )


def _intersection_edge_anchor_context(topology_result: IntersectionTopologyResult) -> dict[str, object]:
    anchors = list(getattr(topology_result, "anchor_rows", []) or [])
    anchor = anchors[0] if anchors else None
    anchor_xyz = _xyz_tuple(getattr(anchor, "point_xyz", (0.0, 0.0, 0.0))) if anchor is not None else (0.0, 0.0, 0.0)
    station_by_alignment: dict[str, float] = {}
    primary_alignment = str(getattr(anchor, "primary_alignment_ref", "") or "") if anchor is not None else ""
    if primary_alignment:
        station_by_alignment[primary_alignment] = float(getattr(anchor, "primary_station", 0.0) or 0.0)
    for alignment_ref, station in tuple(getattr(anchor, "secondary_station_refs", ()) or ()):
        key = str(alignment_ref or "")
        if key:
            station_by_alignment[key] = float(station or 0.0)
    return {
        "anchor_xyz": anchor_xyz,
        "primary_alignment": primary_alignment,
        "station_by_alignment": station_by_alignment,
    }


def _intersection_leg_edge_endpoints(
    leg_span,
    *,
    edge_role: str,
    side: str,
    policy,
    anchor_context: dict[str, object],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    anchor = _xyz_tuple(anchor_context.get("anchor_xyz", (0.0, 0.0, 0.0)))
    alignment_ref = str(getattr(leg_span, "alignment_ref", "") or "")
    station_by_alignment = dict(anchor_context.get("station_by_alignment", {}) or {})
    center_station = float(
        station_by_alignment.get(
            alignment_ref,
            (float(getattr(leg_span, "station_start", 0.0) or 0.0) + float(getattr(leg_span, "station_end", 0.0) or 0.0)) * 0.5,
        )
    )
    station_start = float(getattr(leg_span, "station_start", 0.0) or 0.0)
    station_end = float(getattr(leg_span, "station_end", 0.0) or 0.0)
    start_delta = station_start - center_station
    end_delta = station_end - center_station
    axis = _intersection_alignment_axis(alignment_ref, str(anchor_context.get("primary_alignment", "") or ""), str(getattr(leg_span, "leg_role", "") or ""))
    normal = (-axis[1], axis[0])
    offset = _intersection_edge_lateral_offset(edge_role, side, policy)
    start = (
        anchor[0] + axis[0] * start_delta + normal[0] * offset,
        anchor[1] + axis[1] * start_delta + normal[1] * offset,
        anchor[2],
    )
    end = (
        anchor[0] + axis[0] * end_delta + normal[0] * offset,
        anchor[1] + axis[1] * end_delta + normal[1] * offset,
        anchor[2],
    )
    return start, end


def _intersection_alignment_axis(alignment_ref: str, primary_alignment_ref: str, leg_role: str) -> tuple[float, float]:
    role = str(leg_role or "").lower()
    if role == "primary_after":
        return (1.0, 0.0)
    if role == "primary_before":
        return (-1.0, 0.0)
    if role == "secondary_after":
        return (0.0, 1.0)
    if role == "secondary_before":
        return (0.0, -1.0)
    if str(alignment_ref or "") and str(alignment_ref or "") == str(primary_alignment_ref or ""):
        return (1.0, 0.0)
    if "primary" in role:
        return (1.0, 0.0)
    return (0.0, 1.0)


def _intersection_edge_lateral_offset(edge_role: str, side: str, policy) -> float:
    explicit = float(getattr(policy, "offset_value", 0.0) or 0.0) if policy is not None else 0.0
    if abs(explicit) > 1.0e-9:
        return explicit
    role = str(edge_role or "").lower()
    base = 9.0 if "daylight" in role or "slope" in role else 4.5 if "pavement" in role or "lane" in role else 6.0
    side_text = str(side or "").lower()
    if side_text in {"left", "inside"}:
        return base
    if side_text in {"right", "outside"}:
        return -base
    return base


def _intersection_curb_return_edge_endpoints(
    *,
    corner,
    policy,
    leg_span_by_ref: dict[str, object],
    anchor_context: dict[str, object],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    anchor = _xyz_tuple(anchor_context.get("anchor_xyz", (0.0, 0.0, 0.0)))
    if corner is None:
        return anchor, anchor
    from_leg = leg_span_by_ref.get(str(getattr(corner, "from_leg_ref", "") or ""))
    to_leg = leg_span_by_ref.get(str(getattr(corner, "to_leg_ref", "") or ""))
    if from_leg is None or to_leg is None:
        return anchor, anchor
    radius = max(float(getattr(policy, "radius", 0.0) or 0.0), 0.0)
    offset = radius if radius > 0.0 else 6.0
    from_axis = _intersection_alignment_axis(
        str(getattr(from_leg, "alignment_ref", "") or ""),
        str(anchor_context.get("primary_alignment", "") or ""),
        str(getattr(from_leg, "leg_role", "") or ""),
    )
    to_axis = _intersection_alignment_axis(
        str(getattr(to_leg, "alignment_ref", "") or ""),
        str(anchor_context.get("primary_alignment", "") or ""),
        str(getattr(to_leg, "leg_role", "") or ""),
    )
    start = (anchor[0] + from_axis[0] * offset, anchor[1] + from_axis[1] * offset, anchor[2])
    end = (anchor[0] + to_axis[0] * offset, anchor[1] + to_axis[1] * offset, anchor[2])
    side = str(getattr(corner, "side", "") or getattr(corner, "quadrant", "") or "").lower()
    if side in {"left"}:
        start = (anchor[0] - from_axis[0] * offset, anchor[1] - from_axis[1] * offset, anchor[2])
    if side in {"right"}:
        end = (anchor[0] - to_axis[0] * offset, anchor[1] - to_axis[1] * offset, anchor[2])
    return start, end


def _intersection_curb_return_arc_points(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    *,
    center_xyz: tuple[float, float, float],
    radius: float,
    sample_count: int = 9,
) -> tuple[tuple[float, float, float], ...]:
    radius_value = float(radius or 0.0)
    if radius_value <= 1.0e-9:
        return ()
    center = _xyz_tuple(center_xyz)
    start_radius = math.hypot(float(start[0]) - center[0], float(start[1]) - center[1])
    end_radius = math.hypot(float(end[0]) - center[0], float(end[1]) - center[1])
    if start_radius <= 1.0e-9 or end_radius <= 1.0e-9:
        return ()
    start_angle = math.atan2(float(start[1]) - center[1], float(start[0]) - center[0])
    end_angle = math.atan2(float(end[1]) - center[1], float(end[0]) - center[0])
    delta = end_angle - start_angle
    while delta > math.pi:
        delta -= math.tau
    while delta < -math.pi:
        delta += math.tau
    count = max(3, int(sample_count or 0))
    points: list[tuple[float, float, float]] = []
    for index in range(count):
        ratio = index / float(count - 1)
        angle = start_angle + delta * ratio
        local_radius = start_radius + (end_radius - start_radius) * ratio
        points.append(
            (
                center[0] + math.cos(angle) * local_radius,
                center[1] + math.sin(angle) * local_radius,
                float(start[2]) + (float(end[2]) - float(start[2])) * ratio,
            )
        )
    points[0] = start
    points[-1] = end
    return tuple(points)


def _surface_zone_source_diagnostics(
    source_edge_refs: tuple[str, ...],
    edge_by_id: dict[str, IntersectionEdgeNetworkRow],
) -> tuple[str, ...]:
    diagnostics: list[str] = []
    for edge_ref in source_edge_refs:
        edge = edge_by_id.get(str(edge_ref or ""))
        if edge is None:
            diagnostics.append(f"warning:surface_zone_source_edge_ref_unresolved:{edge_ref}")
            continue
        edge_status = str(getattr(edge, "source_status", "") or "")
        if edge_status and edge_status != "accepted":
            diagnostics.append(f"warning:surface_zone_consumes_{edge_status}_edge:{edge_ref}")
        for item in tuple(getattr(edge, "source_diagnostic_rows", ()) or ()):
            diagnostics.append(f"warning:surface_zone_source_edge_diagnostic:{edge_ref}:{item}")
    return tuple(_unique_text_values(diagnostics))


def _curb_return_policies_for_intersection(
    intersection_model: IntersectionModel,
    intersection_id: str,
) -> list[IntersectionCurbReturnPolicyRow]:
    return [
        policy
        for policy in list(getattr(intersection_model, "curb_return_policy_rows", []) or [])
        if str(getattr(policy, "intersection_id", "") or "") == str(intersection_id or "")
    ]


def _corner_rows_by_id(
    intersection_model: IntersectionModel,
    intersection_id: str,
) -> dict[str, IntersectionCornerRow]:
    return {
        str(getattr(row, "corner_id", "") or ""): row
        for row in list(getattr(intersection_model, "corner_rows", []) or [])
        if str(getattr(row, "intersection_id", "") or "") == str(intersection_id or "")
        and str(getattr(row, "corner_id", "") or "")
    }


def _curb_return_corner_sources(
    policy: IntersectionCurbReturnPolicyRow,
    intersection_kind: str,
    corner_by_id: dict[str, IntersectionCornerRow],
) -> tuple[tuple[str, str, IntersectionCornerRow | None], ...]:
    corner_refs = [str(ref) for ref in list(getattr(policy, "corner_refs", []) or []) if str(ref)]
    if not corner_refs:
        return tuple((side, "", None) for side in _curb_return_sides(policy, intersection_kind))
    output: list[tuple[str, str, IntersectionCornerRow | None]] = []
    for ref in corner_refs:
        corner = corner_by_id.get(ref)
        side = str(getattr(corner, "side", "") or getattr(corner, "quadrant", "") or ref).strip() if corner is not None else ref
        output.append((side, ref, corner))
    return tuple(output)


def _curb_return_sides(policy: IntersectionCurbReturnPolicyRow, intersection_kind: str) -> tuple[str, ...]:
    side = str(getattr(policy, "side", "") or "all").strip().lower()
    if side and side not in {"all", "both"}:
        return (side,)
    kind = str(intersection_kind or "").strip()
    if kind == "cross_intersection":
        return ("quadrant_01", "quadrant_02", "quadrant_03", "quadrant_04")
    if kind == "y_intersection":
        return ("left_branch", "right_branch")
    return ("left", "right")


def _edge_role_from_policy_ref(policy_ref: str) -> str:
    text = str(policy_ref or "").lower()
    if "daylight" in text:
        return "daylight_hinge"
    if "shoulder" in text:
        return "shoulder_edge"
    if "lane" in text:
        return "lane_edge"
    if "gutter" in text:
        return "gutter_edge"
    if "curb" in text:
        return "curb_return_edge"
    return "pavement_edge"


def _edge_family(edge_role: str) -> str:
    role = str(edge_role or "")
    if role == "curb_return_edge":
        return "curb_return"
    return "leg_edge"


def _curb_return_contact_station_refs(
    intersection_model: IntersectionModel,
    topology_result: IntersectionTopologyResult,
    policy: IntersectionCurbReturnPolicyRow,
) -> dict[str, tuple[float, ...]]:
    """Return alignment-scoped curb-return control/contact stations for Applied Sections handoff."""

    row = IntersectionEvaluationService._find_topology_intersection_row(
        intersection_model,
        str(getattr(topology_result, "intersection_id", "") or ""),
    )
    if row is None:
        return {}
    radius = max(float(getattr(policy, "radius", 0.0) or 0.0), 0.0)
    if radius <= 0.0:
        return {}
    output: dict[str, tuple[float, ...]] = {}
    span_by_alignment = {
        str(getattr(span, "alignment_ref", "") or ""): span
        for span in list(getattr(topology_result, "leg_span_rows", []) or [])
        if str(getattr(span, "alignment_ref", "") or "")
    }
    alignment_centers: dict[str, float] = {}
    primary_ref = str(getattr(row, "primary_alignment_ref", "") or "").strip()
    if primary_ref:
        alignment_centers[primary_ref] = float(getattr(row, "primary_station", 0.0) or 0.0)
    for alignment_ref, station in dict(getattr(row, "secondary_station_refs", {}) or {}).items():
        if str(alignment_ref or "").strip():
            alignment_centers[str(alignment_ref)] = float(station or 0.0)

    leg_refs = {
        str(ref)
        for ref in list(getattr(policy, "approach_leg_refs", []) or [])
        if str(ref)
    }
    for span in list(getattr(topology_result, "leg_span_rows", []) or []):
        if leg_refs and str(getattr(span, "leg_ref", "") or "") not in leg_refs:
            continue
        alignment_ref = str(getattr(span, "alignment_ref", "") or "").strip()
        if not alignment_ref:
            continue
        center = alignment_centers.get(alignment_ref)
        if center is None:
            center = (float(getattr(span, "station_start", 0.0) or 0.0) + float(getattr(span, "station_end", 0.0) or 0.0)) * 0.5
        start = max(float(getattr(span, "station_start", 0.0) or 0.0), center - radius)
        end = min(float(getattr(span, "station_end", 0.0) or 0.0), center + radius)
        mid_left = center - radius * 0.5
        mid_right = center + radius * 0.5
        stations = [start, mid_left, center, mid_right, end]
        if alignment_ref in output:
            stations = [*output[alignment_ref], *stations]
        output[alignment_ref] = tuple(_unique_float_values(stations))

    for alignment_ref, center in alignment_centers.items():
        if alignment_ref in output:
            continue
        span = span_by_alignment.get(alignment_ref)
        if span is not None:
            start = max(float(getattr(span, "station_start", 0.0) or 0.0), center - radius)
            end = min(float(getattr(span, "station_end", 0.0) or 0.0), center + radius)
        else:
            start = center - radius
            end = center + radius
        output[alignment_ref] = tuple(_unique_float_values([start, center - radius * 0.5, center, center + radius * 0.5, end]))
    return output


def _roundabout_approach_leg_rows(
    intersection_model: IntersectionModel,
    topology_result: IntersectionTopologyResult,
    *,
    diagnostics: list[str],
) -> list[IntersectionRoundaboutApproachLegRow]:
    """Split roundabout source leg spans into physical approach directions."""

    intersection_id = str(getattr(topology_result, "intersection_id", "") or "")
    center = _roundabout_center_xyz(intersection_model, topology_result)
    rows: list[IntersectionRoundaboutApproachLegRow] = []
    role_counts: dict[str, int] = {}
    shared_roles = (
        "roundabout_approach_clip_to_design_surface",
        "roundabout_entry_exit_connector_to_circulatory_surface",
        "roundabout_subgrade_to_corridor_subgrade",
        "roundabout_slope_face_to_corridor_slope_face",
    )
    for span_index, span in enumerate(list(getattr(topology_result, "leg_span_rows", []) or []), start=1):
        leg_role = str(getattr(span, "leg_role", "") or f"leg_{span_index}")
        base_role = _roundabout_approach_base_role(leg_role, span_index)
        role_counts[base_role] = role_counts.get(base_role, 0) + 1
        if role_counts[base_role] > 1:
            base_role = f"{base_role}_{role_counts[base_role]}"
        station_start = float(getattr(span, "station_start", 0.0) or 0.0)
        station_end = float(getattr(span, "station_end", 0.0) or 0.0)
        station_min = min(station_start, station_end)
        station_max = max(station_start, station_end)
        base_angle = float(getattr(span, "leg_graph_angle_deg", 0.0) or 0.0)
        source_diagnostics = list(getattr(span, "source_diagnostic_rows", ()) or ())
        geometry_diagnostics: list[str] = []
        if not str(getattr(span, "alignment_ref", "") or ""):
            geometry_diagnostics.append("error:roundabout_approach_leg_alignment_ref_missing")
        if abs(station_max - station_min) <= 1.0e-9:
            geometry_diagnostics.append("error:roundabout_approach_leg_station_span_degenerate")
        for endpoint_suffix, handoff_station, direction_sign, direction_angle in (
            ("start", station_min, -1, base_angle + 180.0),
            ("end", station_max, 1, base_angle),
        ):
            approach_role = f"{base_role}_{endpoint_suffix}"
            direction_angle = float(direction_angle) % 360.0
            direction_rad = math.radians(direction_angle)
            direction_vector = (math.cos(direction_rad), math.sin(direction_rad))
            row_diagnostics = [*source_diagnostics, *geometry_diagnostics]
            for diagnostic in geometry_diagnostics:
                diagnostics.append(f"{diagnostic}:{approach_role}")
            status = "error" if geometry_diagnostics else "ready"
            rows.append(
                IntersectionRoundaboutApproachLegRow(
                    approach_leg_id=(
                        f"intersection-roundabout-approach-leg:"
                        f"{_id_token(intersection_id or 'main')}:{_id_token(approach_role)}"
                    ),
                    intersection_id=intersection_id,
                    approach_role=approach_role,
                    approach_index=len(rows) + 1,
                    source_leg_ref=str(getattr(span, "leg_ref", "") or ""),
                    source_leg_role=leg_role,
                    alignment_ref=str(getattr(span, "alignment_ref", "") or ""),
                    control_area_ref=str(getattr(span, "control_area_ref", "") or ""),
                    station_start=station_min,
                    station_end=station_max,
                    handoff_station=handoff_station,
                    inner_station=handoff_station,
                    outer_station=station_max if endpoint_suffix == "start" else station_min,
                    direction_sign=direction_sign,
                    direction_angle_deg=direction_angle,
                    direction_vector_xy=direction_vector,
                    approach_center_xyz=center,
                    roundabout_center_xyz=center,
                    shared_breakline_roles=shared_roles,
                    source_status="warning" if source_diagnostics else "accepted",
                    source_diagnostic_rows=tuple(row_diagnostics),
                    status=status,
                    notes=(
                        "physical_roundabout_approach_leg_from_topology_span; "
                        f"source_leg={str(getattr(span, 'leg_ref', '') or '')}; "
                        f"endpoint={endpoint_suffix}; "
                        f"handoff_sta={handoff_station:.3f}"
                    ),
                )
            )
    if len(rows) != 4:
        diagnostics.append(f"warning:roundabout_approach_leg_expected_four_rows:actual={len(rows)}")
    return rows


def _roundabout_approach_base_role(leg_role: str, span_index: int) -> str:
    text = str(leg_role or "").strip().lower().replace("-", "_")
    if "primary" in text:
        return "primary"
    if "secondary" in text:
        return "secondary"
    if text:
        return _id_token(text).replace("-", "_")
    return f"leg_{int(span_index or 0):02d}"


def _roundabout_edge_network_rows(
    intersection_model: IntersectionModel,
    topology_result: IntersectionTopologyResult,
) -> list[IntersectionEdgeNetworkRow]:
    """Return roundabout edge-family rows for source/topology review."""

    row = IntersectionEvaluationService._find_topology_intersection_row(
        intersection_model,
        str(getattr(topology_result, "intersection_id", "") or ""),
    )
    if row is None:
        return []
    policies = _curb_return_policies_for_intersection(intersection_model, topology_result.intersection_id)
    policy = policies[0] if policies else None
    policy_ref = str(getattr(policy, "policy_id", "") or f"roundabout-policy:{topology_result.intersection_id}:default")
    roundabout_policy = _roundabout_source_policy_values(intersection_model, topology_result.intersection_id)
    radius = float(roundabout_policy.get("circulatory_outer_radius", 0.0) or getattr(policy, "radius", 0.0) or 18.0)
    if radius <= 0.0:
        radius = 18.0
    central_radius = float(roundabout_policy.get("central_island_radius", 0.0) or radius * 0.5)
    if central_radius <= 0.0:
        central_radius = radius * 0.5
    connector_length = float(roundabout_policy.get("approach_connector_length", 0.0) or max(radius * 1.25, 12.0))
    apron_width = float(roundabout_policy.get("outer_apron_width", 0.0) or 0.0)
    policy_diagnostics = _roundabout_source_policy_diagnostics(roundabout_policy)
    contact_station_refs = _curb_return_contact_station_refs(
        intersection_model,
        topology_result,
        policy
        or IntersectionCurbReturnPolicyRow(
            policy_id=policy_ref,
            intersection_id=topology_result.intersection_id,
            radius=radius,
        ),
    )
    alignment_refs = _unique_text_values(
        [
            str(getattr(row, "primary_alignment_ref", "") or ""),
            *[str(ref) for ref in list(getattr(row, "secondary_alignment_refs", []) or [])],
            *[str(getattr(span, "alignment_ref", "") or "") for span in list(getattr(topology_result, "leg_span_rows", []) or [])],
        ]
    )
    leg_refs = _unique_text_values(
        [str(getattr(span, "leg_ref", "") or "") for span in list(getattr(topology_result, "leg_span_rows", []) or [])]
    )
    rows = [
        IntersectionEdgeNetworkRow(
            edge_id=_edge_network_row_id(topology_result.intersection_id, "roundabout", 1, 1, "central_island_edge", "inside"),
            intersection_id=topology_result.intersection_id,
            edge_role="central_island_edge",
            edge_family="roundabout",
            source_policy_ref=policy_ref,
            leg_ref=",".join(leg_refs),
            alignment_ref=",".join(alignment_refs),
            side="inside",
            radius=central_radius,
            contact_station_refs=contact_station_refs,
            source_status="warning" if policy_diagnostics else "accepted",
            source_diagnostic_rows=policy_diagnostics,
            status="accepted" if not policy_diagnostics else "candidate",
            notes=(
                "roundabout_source_policy_central_island_edge; "
                f"central_island_radius={central_radius:.3f}m; "
                f"circulatory_outer_radius={radius:.3f}m"
            ),
        ),
        IntersectionEdgeNetworkRow(
            edge_id=_edge_network_row_id(topology_result.intersection_id, "roundabout", 1, 2, "circulatory_outer_edge", "outside"),
            intersection_id=topology_result.intersection_id,
            edge_role="circulatory_outer_edge",
            edge_family="roundabout",
            source_policy_ref=policy_ref,
            leg_ref=",".join(leg_refs),
            alignment_ref=",".join(alignment_refs),
            side="outside",
            radius=radius,
            contact_station_refs=contact_station_refs,
            source_status="warning" if policy_diagnostics else "accepted",
            source_diagnostic_rows=policy_diagnostics,
            status="accepted" if not policy_diagnostics else "candidate",
            notes=(
                "roundabout_source_policy_circulatory_edge; "
                f"central_island_radius={central_radius:.3f}m; "
                f"circulatory_outer_radius={radius:.3f}m; "
                f"outer_apron_width={apron_width:.3f}m"
            ),
        ),
    ]
    for index, span in enumerate(list(getattr(topology_result, "leg_span_rows", []) or []), start=1):
        rows.append(
            IntersectionEdgeNetworkRow(
                edge_id=_edge_network_row_id(topology_result.intersection_id, "roundabout-entry", 1, index, "entry_exit_edge", f"leg-{index:02d}"),
                intersection_id=topology_result.intersection_id,
                edge_role="entry_exit_edge",
                edge_family="roundabout",
                source_policy_ref=policy_ref,
                leg_ref=str(getattr(span, "leg_ref", "") or ""),
                leg_role=str(getattr(span, "leg_role", "") or ""),
                alignment_ref=str(getattr(span, "alignment_ref", "") or ""),
                control_area_ref=str(getattr(span, "control_area_ref", "") or ""),
                side=f"leg-{index:02d}",
                station_start=float(getattr(span, "station_start", 0.0) or 0.0),
                station_end=float(getattr(span, "station_end", 0.0) or 0.0),
                radius=radius,
                contact_station_refs={
                    str(getattr(span, "alignment_ref", "") or ""): contact_station_refs.get(
                        str(getattr(span, "alignment_ref", "") or ""),
                        (),
                    )
                },
                source_status="warning" if policy_diagnostics else "accepted",
                source_diagnostic_rows=policy_diagnostics,
                status="accepted" if not policy_diagnostics else "candidate",
                notes=(
                    "roundabout_source_policy_entry_exit_edge; "
                    f"approach_connector_length={connector_length:.3f}m"
                ),
            )
        )
    return rows


def _roundabout_source_policy_values(
    intersection_model: IntersectionModel,
    intersection_id: str,
) -> dict[str, float]:
    values: dict[str, float] = {}
    for row in list(getattr(intersection_model, "edge_policy_rows", []) or []):
        if str(getattr(row, "intersection_id", "") or "") != str(intersection_id or ""):
            continue
        if str(getattr(row, "edge_family_intent", "") or "") != "roundabout":
            continue
        rule = str(getattr(row, "offset_rule", "") or "").strip()
        value = float(getattr(row, "offset_value", 0.0) or 0.0)
        if rule == "roundabout_central_island_radius":
            values["central_island_radius"] = value
        elif rule == "roundabout_circulatory_outer_radius":
            values["circulatory_outer_radius"] = value
        elif rule == "roundabout_outer_apron_width":
            values["outer_apron_width"] = value
        elif rule == "roundabout_slope_face_width":
            values["slope_face_width"] = value
        elif rule == "roundabout_approach_connector_length":
            values["approach_connector_length"] = value
        elif rule == "roundabout_subgrade_depth":
            values["subgrade_depth"] = value
    return values


def _roundabout_source_policy_diagnostics(values: dict[str, float]) -> tuple[str, ...]:
    diagnostics: list[str] = []
    required = (
        "central_island_radius",
        "circulatory_outer_radius",
        "approach_connector_length",
    )
    for key in required:
        if float(values.get(key, 0.0) or 0.0) <= 0.0:
            diagnostics.append(f"roundabout_source_policy_missing:{key}")
    if (
        float(values.get("central_island_radius", 0.0) or 0.0) > 0.0
        and float(values.get("circulatory_outer_radius", 0.0) or 0.0) > 0.0
        and float(values.get("central_island_radius", 0.0) or 0.0)
        >= float(values.get("circulatory_outer_radius", 0.0) or 0.0)
    ):
        diagnostics.append("roundabout_source_policy_invalid:central_island_exceeds_outer_radius")
    return tuple(diagnostics)


def _roundabout_boundary_loop_result(
    intersection_model: IntersectionModel,
    topology_result: IntersectionTopologyResult,
    surface_zones: IntersectionSurfaceZoneResult,
    edge_network: IntersectionEdgeNetworkResult,
    *,
    diagnostics: list[str],
) -> IntersectionBoundaryLoopResult:
    intersection_id = str(getattr(topology_result, "intersection_id", "") or "")
    policy_values = _roundabout_source_policy_values(intersection_model, intersection_id)
    policy_diagnostics = list(_roundabout_source_policy_diagnostics(policy_values))
    center = _roundabout_center_xyz(intersection_model, topology_result)
    outer_radius = float(policy_values.get("circulatory_outer_radius", 0.0) or 0.0)
    central_radius = float(policy_values.get("central_island_radius", 0.0) or 0.0)
    if outer_radius <= 0.0:
        outer_radius = _roundabout_edge_radius(edge_network, "circulatory_outer_edge") or 18.0
        policy_diagnostics.append("roundabout_boundary_loop_outer_radius_fallback")
    if central_radius <= 0.0:
        central_radius = _roundabout_edge_radius(edge_network, "central_island_edge") or outer_radius * 0.45
        policy_diagnostics.append("roundabout_boundary_loop_central_radius_fallback")
    apron_width = max(float(policy_values.get("outer_apron_width", 0.0) or 0.0), 0.0)
    ownership_radius = max(outer_radius + apron_width, outer_radius)
    loop_rows: list[IntersectionBoundaryLoopRow] = []
    segment_rows: list[IntersectionBoundarySegmentRow] = []
    loop_specs = [
        (
            "central-island",
            "roundabout_central_island_boundary",
            central_radius,
            _roundabout_circle_points(center, central_radius, segment_count=32),
            (),
            "roundabout_source_policy",
        ),
        (
            "circulatory-outer",
            "roundabout_circulatory_outer_boundary",
            outer_radius,
            _roundabout_circle_points(center, outer_radius, segment_count=32),
            (),
            "roundabout_source_policy",
        ),
        (
            "outer-ownership",
            "roundabout_outer_ownership_boundary",
            ownership_radius,
            _roundabout_circle_points(center, ownership_radius, segment_count=32),
            (),
            "roundabout_source_policy",
        ),
    ]
    connector_length = float(policy_values.get("approach_connector_length", 0.0) or max(outer_radius * 1.25, 12.0))
    connector_width = max(outer_radius - central_radius, 1.0)
    clip_depth = max(min(connector_width * 0.25, 3.0), 0.75)
    approach_legs = IntersectionEvaluationService().evaluate_roundabout_approach_legs(
        intersection_model,
        topology_result,
    )
    approach_leg_rows = list(getattr(approach_legs, "approach_leg_rows", []) or [])
    if approach_leg_rows:
        diagnostics.append(
            "info:roundabout_boundary_loop_source=roundabout_approach_leg_contract:"
            f"{len(approach_leg_rows)}"
        )
    else:
        diagnostics.append("warning:roundabout_boundary_loop_approach_leg_rows_missing")
    for connector_index, approach_leg in enumerate(approach_leg_rows, start=1):
        angle = float(getattr(approach_leg, "direction_angle_deg", 0.0) or 0.0)
        approach_role = str(getattr(approach_leg, "approach_role", "") or f"approach-{connector_index:02d}")
        direction_suffix = _id_token(approach_role)
        approach_source_refs = (
            str(getattr(approach_legs, "approach_leg_result_id", "") or ""),
            str(getattr(approach_leg, "approach_leg_id", "") or ""),
        )
        connector_points = _roundabout_entry_exit_connector_points(
            center,
            outer_radius=outer_radius,
            connector_length=connector_length,
            connector_width=connector_width,
            angle_deg=angle,
        )
        loop_specs.append(
            (
                f"entry-exit-{connector_index:02d}-{direction_suffix}",
                "roundabout_entry_exit_connector_boundary",
                0.0,
                connector_points,
                approach_source_refs,
                "roundabout_approach_leg_contract",
            )
        )
        clip_points = _roundabout_cross_boundary_loop_points(
            center,
            radius=outer_radius + connector_length,
            boundary_width=connector_width,
            boundary_depth=clip_depth,
            angle_deg=angle,
        )
        for boundary_suffix, boundary_role in (
            ("approach-clip", "roundabout_approach_clip_boundary"),
            ("subgrade-clip", "roundabout_subgrade_clip_boundary"),
            ("slope-handoff", "roundabout_slope_handoff_boundary"),
        ):
            loop_specs.append(
                (
                    f"{boundary_suffix}-{connector_index:02d}-{direction_suffix}",
                    boundary_role,
                    0.0,
                    clip_points,
                    approach_source_refs,
                    "roundabout_approach_leg_contract",
                )
            )
    radial_loop_roles = {
        "roundabout_central_island_boundary",
        "roundabout_circulatory_outer_boundary",
        "roundabout_outer_ownership_boundary",
    }
    rectangular_loop_roles = {
        "roundabout_entry_exit_connector_boundary",
        "roundabout_approach_clip_boundary",
        "roundabout_subgrade_clip_boundary",
        "roundabout_slope_handoff_boundary",
    }
    for loop_index, (suffix, role, radius, points, spec_source_refs, source_label) in enumerate(loop_specs, start=1):
        loop_id = f"intersection-boundary-loop:{_id_token(intersection_id or 'main')}:roundabout:{suffix}"
        loop_diagnostics = [
            f"info:intersection_boundary_candidate_source={source_label}",
            *policy_diagnostics,
        ]
        if spec_source_refs:
            loop_diagnostics.append("info:roundabout_boundary_loop_approach_leg_source_refs")
        closed_points = [*points, points[0]] if points else []
        if role in radial_loop_roles and radius <= 0.0:
            loop_diagnostics.append(f"error:roundabout_boundary_loop_radius_invalid:{suffix}")
        if role in rectangular_loop_roles and not points:
            loop_diagnostics.append(f"error:roundabout_rectangular_loop_points_missing:{suffix}")
        if role in radial_loop_roles and len(points) < 8:
            loop_diagnostics.append(f"error:roundabout_boundary_loop_point_count_too_low:{suffix}")
        if role in rectangular_loop_roles and len(points) < 4:
            loop_diagnostics.append(f"error:roundabout_rectangular_loop_point_count_too_low:{suffix}")
        area_xy = abs(_intersection_boundary_area_xy(closed_points)) if closed_points else 0.0
        if area_xy <= 1.0e-6:
            loop_diagnostics.append(f"error:roundabout_boundary_loop_area_too_small:{suffix}")
        source_refs = tuple(
            _unique_text_values(
                [
                    str(getattr(surface_zones, "surface_zone_result_id", "") or ""),
                    str(getattr(edge_network, "edge_network_result_id", "") or ""),
                    *[str(ref) for ref in tuple(spec_source_refs or ()) if str(ref)],
                    *[
                        str(getattr(edge, "edge_id", "") or "")
                        for edge in list(getattr(edge_network, "edge_rows", []) or [])
                        if str(getattr(edge, "edge_family", "") or "") == "roundabout"
                    ],
                ]
            )
        )
        status = "error" if any(item.startswith("error:") for item in loop_diagnostics) else "ready"
        loop_segment_ids: list[str] = []
        for segment_index, (first, second) in enumerate(zip(closed_points[:-1], closed_points[1:]), start=1):
            segment_id = f"{loop_id}:segment:{segment_index:02d}"
            loop_segment_ids.append(segment_id)
            segment_rows.append(
                IntersectionBoundarySegmentRow(
                    segment_id=segment_id,
                    intersection_id=intersection_id,
                    loop_ref=loop_id,
                    segment_role=role,
                    from_point_ref=f"{loop_id}:point:{segment_index:02d}",
                    to_point_ref=f"{loop_id}:point:{(segment_index % len(points)) + 1:02d}",
                    from_xyz=first,
                    to_xyz=second,
                    source_refs=source_refs,
                    expected_consumers=_roundabout_boundary_expected_consumers(role),
                    shared_breakline_ref=f"shared-breakline:{_id_token(segment_id)}",
                    graph_edge_ref=f"intersection-shared-boundary-graph:{_id_token(segment_id)}",
                    diagnostics=tuple(item for item in loop_diagnostics if item.startswith("error:")),
                    notes="Roundabout source-policy boundary segment.",
                )
            )
        loop_rows.append(
            IntersectionBoundaryLoopRow(
                loop_id=loop_id,
                intersection_id=intersection_id,
                loop_role=role,
                status=status,
                closed=_points_closed_xy(closed_points),
                source_status="accepted" if not policy_diagnostics else "warning",
                point_count=len(points),
                segment_count=len(loop_segment_ids),
                area_xy=area_xy,
                bbox_xy=_intersection_boundary_bbox_xy(closed_points) if closed_points else (0.0, 0.0, 0.0, 0.0),
                source_refs=source_refs,
                segment_refs=tuple(loop_segment_ids),
                consumer_roles=_roundabout_boundary_expected_consumers(role),
                loop_points_xyz=tuple(closed_points),
                diagnostics=tuple(loop_diagnostics),
                recommended_action=(
                    "Use this roundabout boundary loop as a source for circulatory surface and shared breaklines."
                    if status == "ready"
                    else "Repair explicit roundabout source policy values before surface handoff."
                ),
                notes=f"Roundabout {suffix} boundary from explicit source policy.",
            )
        )
    diagnostics = [
        *list(diagnostics or []),
        "info:roundabout_boundary_loop_source=explicit_roundabout_policy",
        *[f"warning:{item}" for item in policy_diagnostics if not item.startswith("roundabout_source_policy_missing")],
        *[f"error:{item}" for item in policy_diagnostics if item.startswith("roundabout_source_policy_missing")],
    ]
    error_count = len([row for row in loop_rows if row.status == "error"]) + len([row for row in diagnostics if str(row).startswith("error:")])
    warning_count = len([row for row in diagnostics if str(row).startswith("warning:")])
    ready_count = len([row for row in loop_rows if row.status == "ready"])
    status = "error" if error_count else ("warning" if warning_count else "ready")
    return IntersectionBoundaryLoopResult(
        schema_version=int(getattr(intersection_model, "schema_version", 1) or 1),
        project_id=str(getattr(intersection_model, "project_id", "") or "corridorroad-v1"),
        label=f"Roundabout Boundary Loops - {intersection_id or 'main'}",
        boundary_loop_result_id=f"intersection-boundary-loops:{intersection_id or 'main'}",
        intersection_id=intersection_id,
        intersection_kind="roundabout",
        status=status,
        loop_count=len(loop_rows),
        ready_count=ready_count,
        warning_count=warning_count,
        error_count=error_count,
        segment_count=len(segment_rows),
        diagnostic_rows=diagnostics,
        loop_rows=loop_rows,
        segment_rows=segment_rows,
        source_refs=list(getattr(surface_zones, "source_refs", []) or []),
    )


def _roundabout_center_xyz(
    intersection_model: IntersectionModel,
    topology_result: IntersectionTopologyResult,
) -> tuple[float, float, float]:
    intersection_id = str(getattr(topology_result, "intersection_id", "") or "")
    for row in list(getattr(intersection_model, "intersection_rows", []) or []):
        if str(getattr(row, "intersection_id", "") or "") == intersection_id:
            return (
                float(getattr(row, "intersection_point_x", 0.0) or 0.0),
                float(getattr(row, "intersection_point_y", 0.0) or 0.0),
                float(getattr(row, "intersection_point_z", 0.0) or 0.0),
            )
    return (0.0, 0.0, 0.0)


def _roundabout_edge_radius(
    edge_network: IntersectionEdgeNetworkResult,
    edge_role: str,
) -> float:
    role = str(edge_role or "")
    for row in list(getattr(edge_network, "edge_rows", []) or []):
        if str(getattr(row, "edge_family", "") or "") != "roundabout":
            continue
        if str(getattr(row, "edge_role", "") or "") != role:
            continue
        radius = float(getattr(row, "radius", 0.0) or 0.0)
        if radius > 0.0:
            return radius
    return 0.0


def _roundabout_circle_points(
    center: tuple[float, float, float],
    radius: float,
    *,
    segment_count: int,
) -> list[tuple[float, float, float]]:
    radius_value = float(radius or 0.0)
    count = max(int(segment_count or 0), 8)
    if radius_value <= 0.0:
        return []
    cx, cy, cz = _xyz_tuple(center)
    return [
        (
            cx + math.cos((2.0 * math.pi * index) / count) * radius_value,
            cy + math.sin((2.0 * math.pi * index) / count) * radius_value,
            cz,
        )
        for index in range(count)
    ]


def _roundabout_entry_exit_connector_points(
    center: tuple[float, float, float],
    *,
    outer_radius: float,
    connector_length: float,
    connector_width: float,
    angle_deg: float,
) -> list[tuple[float, float, float]]:
    radius = float(outer_radius or 0.0)
    length = float(connector_length or 0.0)
    width = float(connector_width or 0.0)
    if radius <= 0.0 or length <= 0.0 or width <= 0.0:
        return []
    cx, cy, cz = _xyz_tuple(center)
    angle = math.radians(float(angle_deg or 0.0))
    ux = math.cos(angle)
    uy = math.sin(angle)
    px = -uy
    py = ux
    half_width = width * 0.5
    inner = radius
    outer = radius + length
    return [
        (cx + ux * inner + px * half_width, cy + uy * inner + py * half_width, cz),
        (cx + ux * outer + px * half_width, cy + uy * outer + py * half_width, cz),
        (cx + ux * outer - px * half_width, cy + uy * outer - py * half_width, cz),
        (cx + ux * inner - px * half_width, cy + uy * inner - py * half_width, cz),
    ]


def _roundabout_cross_boundary_loop_points(
    center: tuple[float, float, float],
    *,
    radius: float,
    boundary_width: float,
    boundary_depth: float,
    angle_deg: float,
) -> list[tuple[float, float, float]]:
    radius_value = float(radius or 0.0)
    width = float(boundary_width or 0.0)
    depth = max(float(boundary_depth or 0.0), 0.25)
    if radius_value <= 0.0 or width <= 0.0:
        return []
    cx, cy, cz = _xyz_tuple(center)
    angle = math.radians(float(angle_deg or 0.0))
    ux = math.cos(angle)
    uy = math.sin(angle)
    px = -uy
    py = ux
    half_width = width * 0.5
    inner = max(radius_value - depth * 0.5, 0.0)
    outer = radius_value + depth * 0.5
    return [
        (cx + ux * inner + px * half_width, cy + uy * inner + py * half_width, cz),
        (cx + ux * outer + px * half_width, cy + uy * outer + py * half_width, cz),
        (cx + ux * outer - px * half_width, cy + uy * outer - py * half_width, cz),
        (cx + ux * inner - px * half_width, cy + uy * inner - py * half_width, cz),
    ]


def _roundabout_boundary_expected_consumers(role: str) -> tuple[str, ...]:
    text = str(role or "")
    if text == "roundabout_central_island_boundary":
        return ("intersection_surface", "roundabout_central_island", "roundabout_circulatory_surface")
    if text == "roundabout_circulatory_outer_boundary":
        return (
            "intersection_surface",
            "roundabout_circulatory_surface",
            "roundabout_apron_surface",
        )
    if text == "roundabout_entry_exit_connector_boundary":
        return (
            "roundabout_entry_exit_connector",
            "design_surface",
            "roundabout_circulatory_surface",
        )
    if text == "roundabout_outer_ownership_boundary":
        return (
            "roundabout_apron_surface",
            "roundabout_slope_face_surface",
        )
    if text == "roundabout_approach_clip_boundary":
        return (
            "design_surface",
            "roundabout_entry_exit_connector",
        )
    if text == "roundabout_subgrade_clip_boundary":
        return (
            "subgrade_surface",
            "roundabout_subgrade_surface",
        )
    if text == "roundabout_slope_handoff_boundary":
        return (
            "slope_face_surface",
            "roundabout_slope_face_surface",
        )
    return ("roundabout_surface",)


def _roundabout_surface_zone_rows(
    intersection_model: IntersectionModel,
    edge_network: IntersectionEdgeNetworkResult,
    roundabout_edges: list[IntersectionEdgeNetworkRow],
) -> list[IntersectionSurfaceZoneRow]:
    """Return dedicated roundabout surface-zone contracts from source policy rows."""

    if not roundabout_edges:
        return []
    grading_ref = _surface_zone_grading_policy_ref(intersection_model, edge_network.intersection_id)
    policy_values = _roundabout_source_policy_values(intersection_model, edge_network.intersection_id)
    apron_width = float(policy_values.get("outer_apron_width", 0.0) or 0.0)
    edge_by_id = {
        str(getattr(row, "edge_id", "") or ""): row
        for row in list(getattr(edge_network, "edge_rows", []) or [])
        if str(getattr(row, "edge_id", "") or "")
    }
    zone_rows: list[IntersectionSurfaceZoneRow] = []
    central_edges = [row for row in roundabout_edges if str(getattr(row, "edge_role", "") or "") == "central_island_edge"]
    circulatory_edges = [row for row in roundabout_edges if str(getattr(row, "edge_role", "") or "") == "circulatory_outer_edge"]
    entry_edges = [row for row in roundabout_edges if str(getattr(row, "edge_role", "") or "") == "entry_exit_edge"]
    if central_edges:
        source_edge_refs = tuple(str(row.edge_id) for row in central_edges)
        source_diagnostics = _surface_zone_source_diagnostics(source_edge_refs, edge_by_id)
        zone_rows.append(
            IntersectionSurfaceZoneRow(
                zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:roundabout-central-island",
                intersection_id=edge_network.intersection_id,
                zone_role="roundabout_central_island",
                zone_family="roundabout",
                design_zone_role="roundabout_central_island",
                surface_role="design",
                source_edge_refs=source_edge_refs,
                boundary_edge_refs=source_edge_refs,
                inner_edge_refs=source_edge_refs,
                leg_refs=tuple(_unique_text_values([row.leg_ref for row in central_edges])),
                alignment_refs=tuple(_unique_text_values([row.alignment_ref for row in central_edges])),
                vertical_policy_ref=grading_ref,
                surface_priority=_surface_priority("roundabout_central_island"),
                triangulation_method="pending_roundabout_island_zone",
                source_status="warning" if source_diagnostics else "accepted",
                source_diagnostic_rows=source_diagnostics,
                status="candidate",
                notes="Roundabout central island source-zone contract only; no triangulation generated.",
            )
        )
    if circulatory_edges:
        source_edge_refs = tuple(str(row.edge_id) for row in [*central_edges, *circulatory_edges])
        source_diagnostics = _surface_zone_source_diagnostics(source_edge_refs, edge_by_id)
        zone_rows.append(
            IntersectionSurfaceZoneRow(
                zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:roundabout-circulatory",
                intersection_id=edge_network.intersection_id,
                zone_role="roundabout_circulatory_lane",
                zone_family="roundabout",
                design_zone_role="roundabout_circulatory_lane",
                surface_role="design",
                source_edge_refs=source_edge_refs,
                boundary_edge_refs=source_edge_refs,
                inner_edge_refs=tuple(str(row.edge_id) for row in central_edges),
                outer_edge_refs=tuple(str(row.edge_id) for row in circulatory_edges),
                leg_refs=tuple(_unique_text_values([row.leg_ref for row in [*central_edges, *circulatory_edges]])),
                alignment_refs=tuple(_unique_text_values([row.alignment_ref for row in [*central_edges, *circulatory_edges]])),
                vertical_policy_ref=grading_ref,
                surface_priority=_surface_priority("roundabout_circulatory_lane"),
                triangulation_method="pending_roundabout_ring_zone",
                source_status="warning" if source_diagnostics else "accepted",
                source_diagnostic_rows=source_diagnostics,
                status="candidate",
                notes="Roundabout circulatory roadway source-zone contract only; no triangulation generated.",
            )
        )
        apron_diagnostics = tuple(
            item
            for item in (
                *source_diagnostics,
                "warning:roundabout_truck_apron_width_policy_missing" if apron_width <= 0.0 else "",
            )
            if item
        )
        zone_rows.append(
            IntersectionSurfaceZoneRow(
                zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:roundabout-truck-apron",
                intersection_id=edge_network.intersection_id,
                zone_role="roundabout_truck_apron",
                zone_family="roundabout",
                design_zone_role="roundabout_truck_apron",
                surface_role="design",
                source_edge_refs=tuple(str(row.edge_id) for row in circulatory_edges),
                boundary_edge_refs=tuple(str(row.edge_id) for row in circulatory_edges),
                inner_edge_refs=tuple(str(row.edge_id) for row in circulatory_edges),
                leg_refs=tuple(_unique_text_values([row.leg_ref for row in circulatory_edges])),
                alignment_refs=tuple(_unique_text_values([row.alignment_ref for row in circulatory_edges])),
                vertical_policy_ref=grading_ref,
                surface_priority=_surface_priority("roundabout_truck_apron"),
                triangulation_method="pending_roundabout_apron_zone",
                source_status="warning" if apron_diagnostics else "accepted",
                source_diagnostic_rows=apron_diagnostics,
                status="warning" if apron_diagnostics else "candidate",
                diagnostic_rows=apron_diagnostics,
                notes="Roundabout truck-apron source-zone contract from outer-apron policy; no triangulation generated.",
            )
        )
        shoulder_diagnostics = tuple(
            item
            for item in (
                *source_diagnostics,
                "warning:roundabout_outer_shoulder_policy_missing",
            )
            if item
        )
        zone_rows.append(
            IntersectionSurfaceZoneRow(
                zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:roundabout-outer-shoulder",
                intersection_id=edge_network.intersection_id,
                zone_role="roundabout_outer_shoulder",
                zone_family="roundabout",
                design_zone_role="roundabout_outer_shoulder",
                surface_role="design",
                source_edge_refs=tuple(str(row.edge_id) for row in circulatory_edges),
                boundary_edge_refs=tuple(str(row.edge_id) for row in circulatory_edges),
                inner_edge_refs=tuple(str(row.edge_id) for row in circulatory_edges),
                leg_refs=tuple(_unique_text_values([row.leg_ref for row in circulatory_edges])),
                alignment_refs=tuple(_unique_text_values([row.alignment_ref for row in circulatory_edges])),
                vertical_policy_ref=grading_ref,
                surface_priority=_surface_priority("roundabout_outer_shoulder"),
                triangulation_method="pending_roundabout_outer_shoulder_zone",
                surface_generation_role="diagnostic_only",
                surface_generation_status="blocked",
                source_status="warning",
                source_diagnostic_rows=shoulder_diagnostics,
                status="warning",
                diagnostic_rows=shoulder_diagnostics,
                notes="Roundabout outer-shoulder source-zone contract is waiting for an explicit shoulder-width policy.",
            )
        )
    for index, edge in enumerate(entry_edges, start=1):
        source_edge_refs = (str(edge.edge_id),)
        source_diagnostics = _surface_zone_source_diagnostics(source_edge_refs, edge_by_id)
        zone_rows.append(
            IntersectionSurfaceZoneRow(
                zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:roundabout-entry-exit-{index:02d}",
                intersection_id=edge_network.intersection_id,
                zone_role="roundabout_entry_exit_connector",
                zone_family="roundabout",
                design_zone_role="roundabout_entry_exit_connector",
                surface_role="design",
                source_edge_refs=source_edge_refs,
                boundary_edge_refs=source_edge_refs,
                tie_edge_refs=tuple(str(row.edge_id) for row in circulatory_edges),
                leg_refs=(str(edge.leg_ref),) if str(edge.leg_ref) else (),
                alignment_refs=(str(edge.alignment_ref),) if str(edge.alignment_ref) else (),
                control_area_refs=(str(edge.control_area_ref),) if str(edge.control_area_ref) else (),
                vertical_policy_ref=grading_ref,
                surface_priority=_surface_priority("roundabout_entry_exit_connector"),
                triangulation_method="pending_roundabout_entry_exit_zone",
                surface_generation_role="diagnostic_only",
                surface_generation_status="blocked",
                source_status="warning" if source_diagnostics else "accepted",
                source_diagnostic_rows=source_diagnostics,
                status="warning",
                diagnostic_rows=tuple([*source_diagnostics, "info:roundabout_entry_exit_connector_surface_generation_deferred"]),
                notes="Roundabout entry/exit connector source-zone contract only; production surface generation is deferred to connector geometry phase.",
            )
        )
    return zone_rows


def _surface_priority(design_zone_role: str) -> int:
    role = str(design_zone_role or "").strip()
    priorities = {
        "central_pavement": 100,
        "roundabout_central_island": 98,
        "roundabout_circulatory_lane": 96,
        "roundabout_truck_apron": 94,
        "roundabout_outer_shoulder": 92,
        "curb_return_pavement": 90,
        "roundabout_entry_exit_connector": 88,
        "main_pavement": 70,
        "side_pavement": 70,
        "leg_pavement": 70,
        "exterior_slope_face": 40,
    }
    return priorities.get(role, 50)


def _slope_face_loop_family(zone: IntersectionSurfaceZoneRow) -> str:
    leg_text = " ".join(
        [
            " ".join(str(value or "") for value in tuple(getattr(zone, "leg_refs", ()) or ())),
            " ".join(str(value or "") for value in tuple(getattr(zone, "alignment_refs", ()) or ())),
            str(getattr(zone, "zone_id", "") or ""),
            str(getattr(zone, "notes", "") or ""),
        ]
    ).lower()
    if "secondary" in leg_text or "side" in leg_text:
        return "secondary_outside_loop"
    if "primary" in leg_text or "main" in leg_text:
        return "primary_outside_loop"
    if tuple(getattr(zone, "tie_edge_refs", ()) or ()):
        return "curb_return_loop"
    return "corner_gap_loop"


def _slope_face_loop_side(zone: IntersectionSurfaceZoneRow) -> str:
    text = " ".join(
        [
            str(getattr(zone, "zone_id", "") or ""),
            str(getattr(zone, "notes", "") or ""),
            " ".join(str(value or "") for value in tuple(getattr(zone, "boundary_edge_refs", ()) or ())),
        ]
    ).lower()
    if "left" in text:
        return "left"
    if "right" in text:
        return "right"
    return ""


def _slope_face_loop_source_lineage_status(
    source_surface_zone_refs: tuple[str, ...],
    source_edge_refs: tuple[str, ...],
    source_surface_zone_status: str,
    source_edge_network_status: str,
    source_diagnostics: tuple[str, ...],
) -> str:
    if not tuple(ref for ref in source_surface_zone_refs if str(ref)):
        return "source_surface_zone_missing"
    if not tuple(ref for ref in source_edge_refs if str(ref)):
        return "source_edge_refs_missing"
    if str(source_surface_zone_status or "") == "error" or str(source_edge_network_status or "") == "error":
        return "source_error"
    if str(source_surface_zone_status or "") not in {"", "accepted"}:
        return "source_warning"
    if str(source_edge_network_status or "") not in {"", "accepted"}:
        return "source_warning"
    if source_diagnostics:
        return "source_warning"
    return "accepted"


def _slope_face_loop_source_status(source_lineage_status: str) -> str:
    if str(source_lineage_status or "") == "source_error":
        return "error"
    if str(source_lineage_status or "") != "accepted":
        return "warning"
    return "accepted"


def _slope_face_loop_edge_network_status(
    source_edge_refs: tuple[str, ...],
    edge_by_id: dict[str, IntersectionEdgeNetworkRow],
) -> str:
    refs = tuple(str(ref) for ref in source_edge_refs if str(ref))
    if not refs:
        return "missing"
    statuses: list[str] = []
    for ref in refs:
        edge = edge_by_id.get(ref)
        if edge is None:
            statuses.append("error")
            continue
        statuses.append(str(getattr(edge, "source_status", "") or "accepted"))
        row_status = str(getattr(edge, "status", "") or "")
        if row_status == "error":
            statuses.append("error")
        elif row_status == "warning":
            statuses.append("warning")
    if any(status == "error" for status in statuses):
        return "error"
    if any(status not in {"", "accepted", "ready", "candidate"} for status in statuses):
        return "warning"
    return "accepted"


def _slope_face_loop_edge_source_diagnostics(
    source_edge_refs: tuple[str, ...],
    edge_by_id: dict[str, IntersectionEdgeNetworkRow],
) -> tuple[str, ...]:
    diagnostics: list[str] = []
    for ref in tuple(str(ref) for ref in source_edge_refs if str(ref)):
        edge = edge_by_id.get(ref)
        if edge is None:
            diagnostics.append(f"source_edge_network_ref_unresolved:{ref}")
            continue
        for diagnostic in tuple(getattr(edge, "source_diagnostic_rows", ()) or ()):
            text = str(diagnostic or "").strip()
            if text:
                diagnostics.append(f"source_edge_network:{ref}:{text}")
    return tuple(_unique_text_values(diagnostics))


def _slope_face_loop_applied_section_refs(zone, applied_section_set) -> tuple[str, ...]:
    if zone is None or applied_section_set is None:
        return ()
    intersection_id = str(getattr(zone, "intersection_id", "") or "")
    alignment_refs = {str(ref or "") for ref in tuple(getattr(zone, "alignment_refs", ()) or ()) if str(ref or "")}
    control_area_refs = {str(ref or "") for ref in tuple(getattr(zone, "control_area_refs", ()) or ()) if str(ref or "")}
    leg_refs = {str(ref or "") for ref in tuple(getattr(zone, "leg_refs", ()) or ()) if str(ref or "")}
    refs: list[str] = []
    for section in list(getattr(applied_section_set, "sections", []) or []):
        section_id = str(getattr(section, "applied_section_id", "") or "")
        if not section_id:
            continue
        if not _applied_section_has_side_slope_boundary(section):
            continue
        section_intersection = str(getattr(section, "active_intersection_id", "") or "")
        section_alignment = str(getattr(section, "alignment_id", "") or "")
        section_control_area = str(getattr(section, "active_intersection_control_area_id", "") or "")
        section_leg = str(getattr(section, "active_intersection_leg_id", "") or "")
        if intersection_id and section_intersection == intersection_id:
            refs.append(section_id)
            continue
        if control_area_refs and section_control_area in control_area_refs:
            refs.append(section_id)
            continue
        if leg_refs and section_leg in leg_refs:
            refs.append(section_id)
            continue
        if alignment_refs and section_alignment in alignment_refs and not section_intersection:
            refs.append(section_id)
    return tuple(_unique_text_values(refs))


def _applied_section_has_side_slope_boundary(section) -> bool:
    for link in list(getattr(section, "subassembly_link_rows", []) or []):
        if str(getattr(link, "surface_role", "") or "") in {"side_slope_surface", "slope_face_surface"}:
            return True
    for point in list(getattr(section, "point_rows", []) or []):
        if str(getattr(point, "point_role", "") or "") in {"side_slope_surface", "bench_surface", "daylight_marker"}:
            return True
    for point in list(getattr(section, "subassembly_point_rows", []) or []):
        if str(getattr(point, "point_code", "") or "") in {"side_slope_surface", "bench_surface", "daylight_marker"}:
            return True
    return False


def _slope_face_loop_applied_section_boundary_edges(zone, applied_section_set) -> tuple[list[IntersectionEdgeNetworkRow], tuple[str, ...], tuple[str, ...]]:
    """Return evaluated Applied Section side-slope boundary segments for one slope zone."""

    if zone is None or applied_section_set is None:
        return ([], (), ())
    intersection_id = str(getattr(zone, "intersection_id", "") or "")
    alignment_refs = {str(ref or "") for ref in tuple(getattr(zone, "alignment_refs", ()) or ()) if str(ref or "")}
    control_area_refs = {str(ref or "") for ref in tuple(getattr(zone, "control_area_refs", ()) or ()) if str(ref or "")}
    leg_refs = {str(ref or "") for ref in tuple(getattr(zone, "leg_refs", ()) or ()) if str(ref or "")}
    zone_id = str(getattr(zone, "zone_id", "") or "zone")
    strip_groups: dict[tuple[str, str, str, str], list[dict[str, object]]] = {}
    diagnostics: list[str] = []
    for section in sorted(
        list(getattr(applied_section_set, "sections", []) or []),
        key=lambda item: (
            str(getattr(item, "alignment_id", "") or ""),
            float(getattr(item, "station", 0.0) or 0.0),
            str(getattr(item, "applied_section_id", "") or ""),
        ),
    ):
        if not _slope_face_loop_section_matches_zone(
            section,
            intersection_id=intersection_id,
            alignment_refs=alignment_refs,
            control_area_refs=control_area_refs,
            leg_refs=leg_refs,
        ):
            continue
        section_id = str(getattr(section, "applied_section_id", "") or "")
        point_by_ref = _applied_section_point_lookup(section)
        for link_index, link in enumerate(list(getattr(section, "subassembly_link_rows", []) or []), start=1):
            surface_role = str(getattr(link, "surface_role", "") or "").strip()
            if surface_role not in {"side_slope_surface", "slope_face_surface"}:
                continue
            side = _applied_section_side_slope_link_side(link)
            start_ref = str(getattr(link, "start_point_ref", "") or "").strip()
            end_ref = str(getattr(link, "end_point_ref", "") or "").strip()
            start = point_by_ref.get(start_ref)
            end = point_by_ref.get(end_ref)
            if start is None or end is None:
                diagnostics.append(
                    "warning:applied_section_side_slope_boundary_point_ref_unresolved:"
                    f"{section_id}:{getattr(link, 'link_id', '')}:{start_ref}->{end_ref}"
                )
                continue
            if _same_xy(start, end):
                diagnostics.append(
                    "warning:applied_section_side_slope_boundary_degenerate:"
                    f"{section_id}:{getattr(link, 'link_id', '')}"
                )
                continue
            group_key = (
                str(getattr(section, "alignment_id", "") or ""),
                str(getattr(section, "active_intersection_control_area_id", "") or ""),
                str(getattr(section, "active_intersection_leg_id", "") or ""),
                side,
            )
            strip_groups.setdefault(group_key, []).append(
                {
                    "section_id": section_id,
                    "station": float(getattr(section, "station", 0.0) or 0.0),
                    "link_id": str(getattr(link, "link_id", "") or f"link:{link_index}"),
                    "surface_role": surface_role,
                    "start": start,
                    "end": end,
                }
            )
    edges: list[IntersectionEdgeNetworkRow] = []
    refs: list[str] = []
    valid_group_count = 0
    for best_group_key, best_records in _ordered_applied_section_side_slope_strip_groups(strip_groups):
        ordered = sorted(
            best_records,
            key=lambda item: (
                float(item.get("station", 0.0) or 0.0),
                str(item.get("section_id", "") or ""),
                str(item.get("link_id", "") or ""),
            ),
        )
        strip_points: list[tuple[float, float, float]] = []
        strip_points.extend(_unique_adjacent_points([_xyz_tuple(record.get("start", (0.0, 0.0, 0.0))) for record in ordered]))
        strip_points.extend(_unique_adjacent_points([_xyz_tuple(record.get("end", (0.0, 0.0, 0.0))) for record in reversed(ordered)]))
        if strip_points and not _same_xy(strip_points[0], strip_points[-1]):
            strip_points.append(strip_points[0])
        if len(strip_points) >= 4 and _points_closed_xy(strip_points):
            source_sections = ",".join(
                _unique_text_values([str(record.get("section_id", "") or "") for record in ordered if str(record.get("section_id", "") or "")])
            )
            valid_group_count += 1
            for segment_index, (start, end) in enumerate(zip(strip_points[:-1], strip_points[1:]), start=1):
                if _same_xy(start, end):
                    continue
                edge_id = (
                    f"applied-section-boundary:{_id_token(zone_id)}:"
                    f"{_id_token('|'.join(best_group_key))}:{segment_index:02d}"
                )
                refs.append(edge_id)
                edges.append(
                    IntersectionEdgeNetworkRow(
                        edge_id=edge_id,
                        intersection_id=intersection_id,
                        edge_role="applied_section_side_slope_boundary",
                        edge_family="applied_section_boundary",
                        source_policy_ref=source_sections,
                        leg_ref=best_group_key[2],
                        alignment_ref=best_group_key[0],
                        control_area_ref=best_group_key[1],
                        side=best_group_key[3],
                        station_start=float(ordered[0].get("station", 0.0) or 0.0),
                        station_end=float(ordered[-1].get("station", 0.0) or 0.0),
                        start_xyz=start,
                        end_xyz=end,
                        source_status="accepted",
                        status="ready",
                        notes=(
                            "Applied Section side-slope longitudinal strip boundary candidate; "
                            f"sections={source_sections}"
                        ),
                    )
                )
        else:
            diagnostics.append(f"warning:applied_section_side_slope_boundary_strip_open_or_too_short:{'|'.join(best_group_key)}")
    if strip_groups and not edges:
        diagnostics.append("warning:applied_section_side_slope_boundary_strip_edges_missing")
    if len(strip_groups) > 1 and edges:
        diagnostics.append(f"info:applied_section_side_slope_boundary_groups_used:{valid_group_count}/{len(strip_groups)}")
    if not strip_groups:
        diagnostics.append("warning:applied_section_side_slope_boundary_candidates_missing")
    return (edges, tuple(_unique_text_values(refs)), tuple(_unique_text_values(diagnostics)))


def _applied_section_side_slope_link_side(link) -> str:
    text = " ".join(
        [
            str(getattr(link, "side", "") or ""),
            str(getattr(link, "link_id", "") or ""),
            str(getattr(link, "start_point_ref", "") or ""),
            str(getattr(link, "end_point_ref", "") or ""),
        ]
    ).lower()
    if "left" in text:
        return "left"
    if "right" in text:
        return "right"
    return ""


def _best_applied_section_side_slope_strip_group(
    strip_groups: dict[tuple[str, str, str, str], list[dict[str, object]]],
) -> tuple[tuple[str, str, str, str], list[dict[str, object]]]:
    if not strip_groups:
        return (("", "", "", ""), [])
    return max(
        sorted(strip_groups.items(), key=lambda item: item[0]),
        key=lambda item: (
            len(item[1]),
            len({float(record.get("station", 0.0) or 0.0) for record in item[1]}),
        ),
    )


def _ordered_applied_section_side_slope_strip_groups(
    strip_groups: dict[tuple[str, str, str, str], list[dict[str, object]]],
) -> list[tuple[tuple[str, str, str, str], list[dict[str, object]]]]:
    if not strip_groups:
        return []
    return sorted(
        strip_groups.items(),
        key=lambda item: (
            str(item[0][0]),
            str(item[0][1]),
            str(item[0][2]),
            str(item[0][3]),
        ),
    )


def _unique_adjacent_points(points: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    result: list[tuple[float, float, float]] = []
    for point in points:
        if not result or not _same_xy(result[-1], point):
            result.append(point)
    return result


def _slope_face_loop_section_matches_zone(
    section,
    *,
    intersection_id: str,
    alignment_refs: set[str],
    control_area_refs: set[str],
    leg_refs: set[str],
) -> bool:
    section_intersection = str(getattr(section, "active_intersection_id", "") or "")
    section_alignment = str(getattr(section, "alignment_id", "") or "")
    section_control_area = str(getattr(section, "active_intersection_control_area_id", "") or "")
    section_leg = str(getattr(section, "active_intersection_leg_id", "") or "")
    if intersection_id and section_intersection and section_intersection != intersection_id:
        return False
    if control_area_refs and section_control_area in control_area_refs:
        return True
    if leg_refs and section_leg in leg_refs:
        return True
    if alignment_refs and section_alignment in alignment_refs:
        return True
    return bool(intersection_id and section_intersection == intersection_id)


def _applied_section_point_lookup(section) -> dict[str, tuple[float, float, float]]:
    points: dict[str, tuple[float, float, float]] = {}
    for point in list(getattr(section, "point_rows", []) or []):
        point_id = str(getattr(point, "point_id", "") or "").strip()
        if point_id:
            points[point_id] = (
                float(getattr(point, "x", 0.0) or 0.0),
                float(getattr(point, "y", 0.0) or 0.0),
                float(getattr(point, "z", 0.0) or 0.0),
            )
    for point in list(getattr(section, "subassembly_point_rows", []) or []):
        xyz = (
            float(getattr(point, "x", 0.0) or 0.0),
            float(getattr(point, "y", 0.0) or 0.0),
            float(getattr(point, "z", 0.0) or 0.0),
        )
        for ref in (
            str(getattr(point, "point_id", "") or "").strip(),
            str(getattr(point, "point_code", "") or "").strip(),
        ):
            if ref:
                points[ref] = xyz
    return points


def _slope_face_loop_graph_needs_boundary_completion(graph: dict[str, object]) -> bool:
    if not graph:
        return True
    if tuple(graph.get("unresolved_edge_refs", ()) or ()):
        return True
    if tuple(graph.get("degenerate_edge_refs", ()) or ()):
        return True
    if tuple(graph.get("dangling_node_keys", ()) or ()):
        return True
    if not _slope_face_loop_ordered_rings_from_graph(graph):
        return True
    return False


def _slope_face_loop_completion_supersedes_diagnostic(diagnostic: object) -> bool:
    text = str(diagnostic or "")
    return any(
        token in text
        for token in (
            "slope_face_loop_boundary_edge_refs_unresolved",
            "slope_face_loop_degenerate_edge_refs",
            "slope_face_loop_dangling_endpoint",
            "slope_face_loop_point_count_too_low",
            "slope_face_loop_open_xy",
            "source_edge_network:",
            "surface_zone_source_edge_diagnostic",
            "applied_section_side_slope_boundary_degenerate",
            "applied_section_side_slope_boundary_group_selected",
        )
    )


def _slope_face_loop_points_from_edges(
    edge_refs: tuple[str, ...],
    edge_by_id: dict[str, IntersectionEdgeNetworkRow],
) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    for edge_ref in edge_refs:
        edge = edge_by_id.get(str(edge_ref or ""))
        if edge is None:
            continue
        start = _xyz_tuple(getattr(edge, "start_xyz", (0.0, 0.0, 0.0)))
        end = _xyz_tuple(getattr(edge, "end_xyz", (0.0, 0.0, 0.0)))
        if not points or not _same_xy(points[-1], start):
            points.append(start)
        if not _same_xy(points[-1], end):
            points.append(end)
    return points


def _slope_face_loop_endpoint_graph(
    edge_refs: tuple[str, ...],
    edge_by_id: dict[str, IntersectionEdgeNetworkRow],
    *,
    tolerance: float = 1.0e-6,
) -> dict[str, object]:
    """Convert slope-face boundary refs into endpoint graph data."""

    nodes: dict[str, tuple[float, float, float]] = {}
    adjacency: dict[str, list[str]] = {}
    segments: list[dict[str, object]] = []
    unresolved: list[str] = []
    degenerate: list[str] = []
    for edge_ref in tuple(str(ref or "") for ref in edge_refs if str(ref or "")):
        edge = edge_by_id.get(edge_ref)
        if edge is None:
            unresolved.append(edge_ref)
            continue
        start = _xyz_tuple(getattr(edge, "start_xyz", (0.0, 0.0, 0.0)))
        end = _xyz_tuple(getattr(edge, "end_xyz", (0.0, 0.0, 0.0)))
        start_key = _slope_face_loop_endpoint_key(start, tolerance=tolerance)
        end_key = _slope_face_loop_endpoint_key(end, tolerance=tolerance)
        nodes.setdefault(start_key, start)
        nodes.setdefault(end_key, end)
        if start_key == end_key:
            degenerate.append(edge_ref)
            continue
        adjacency.setdefault(start_key, []).append(end_key)
        adjacency.setdefault(end_key, []).append(start_key)
        segments.append(
            {
                "edge_ref": edge_ref,
                "start_key": start_key,
                "end_key": end_key,
                "start_xyz": start,
                "end_xyz": end,
            }
        )
    dangling = sorted(key for key, values in adjacency.items() if len(_unique_text_values(values)) == 1)
    branch = sorted(key for key, values in adjacency.items() if len(_unique_text_values(values)) > 2)
    segment_refs_by_node: dict[str, list[str]] = {}
    for segment in segments:
        edge_ref = str(segment.get("edge_ref", "") or "")
        for key in (str(segment.get("start_key", "") or ""), str(segment.get("end_key", "") or "")):
            if key and edge_ref:
                segment_refs_by_node.setdefault(key, []).append(edge_ref)
    return {
        "nodes": nodes,
        "adjacency": {key: _unique_text_values(values) for key, values in adjacency.items()},
        "segments": segments,
        "unresolved_edge_refs": tuple(_unique_text_values(unresolved)),
        "degenerate_edge_refs": tuple(_unique_text_values(degenerate)),
        "dangling_node_keys": tuple(dangling),
        "dangling_endpoint_rows": tuple(
            {
                "node_key": key,
                "xyz": nodes.get(key, (0.0, 0.0, 0.0)),
                "edge_refs": tuple(_unique_text_values(segment_refs_by_node.get(key, []))),
            }
            for key in dangling
        ),
        "branch_node_keys": tuple(branch),
    }


def _slope_face_loop_ordered_rings_from_graph(graph: dict[str, object]) -> list[dict[str, object]]:
    """Order graph segments into deterministic closed rings."""

    segments = list(graph.get("segments", []) or [])
    nodes = dict(graph.get("nodes", {}) or {})
    segment_by_ref = {
        str(segment.get("edge_ref", "") or ""): segment
        for segment in segments
        if str(segment.get("edge_ref", "") or "")
    }
    segment_refs_by_node: dict[str, list[str]] = {}
    for segment_ref, segment in segment_by_ref.items():
        start_key = str(segment.get("start_key", "") or "")
        end_key = str(segment.get("end_key", "") or "")
        if start_key:
            segment_refs_by_node.setdefault(start_key, []).append(segment_ref)
        if end_key:
            segment_refs_by_node.setdefault(end_key, []).append(segment_ref)
    for key, refs in list(segment_refs_by_node.items()):
        segment_refs_by_node[key] = sorted(_unique_text_values(refs))

    visited: set[str] = set()
    rings: list[dict[str, object]] = []
    for start_ref in sorted(segment_by_ref):
        if start_ref in visited:
            continue
        first_segment = segment_by_ref[start_ref]
        start_key = str(first_segment.get("start_key", "") or "")
        end_key = str(first_segment.get("end_key", "") or "")
        if not start_key or not end_key:
            continue
        edge_refs = [start_ref]
        point_keys = [start_key, end_key]
        visited.add(start_ref)
        previous_key = start_key
        current_key = end_key
        closed = current_key == start_key
        while not closed:
            candidates = [
                ref
                for ref in segment_refs_by_node.get(current_key, [])
                if ref not in visited
            ]
            if not candidates:
                break
            next_ref = candidates[0]
            next_segment = segment_by_ref[next_ref]
            next_start = str(next_segment.get("start_key", "") or "")
            next_end = str(next_segment.get("end_key", "") or "")
            next_key = next_end if next_start == current_key else next_start
            if not next_key or next_key == previous_key:
                break
            edge_refs.append(next_ref)
            point_keys.append(next_key)
            visited.add(next_ref)
            previous_key, current_key = current_key, next_key
            closed = current_key == start_key
            if len(edge_refs) > len(segment_by_ref):
                break
        if closed and len(point_keys) >= 4:
            point_keys = _slope_face_loop_canonical_ring_point_keys(point_keys)
            rings.append(
                {
                    "edge_refs": tuple(edge_refs),
                    "point_keys": tuple(point_keys),
                    "points_xyz": tuple(nodes[key] for key in point_keys if key in nodes),
                }
            )
    return rings


def _slope_face_loop_canonical_ring_point_keys(point_keys: list[str]) -> list[str]:
    if len(point_keys) < 2:
        return list(point_keys)
    keys = list(point_keys)
    if keys[0] == keys[-1]:
        keys = keys[:-1]
    if not keys:
        return []

    def rotate(values: list[str], start_index: int) -> list[str]:
        return values[start_index:] + values[:start_index]

    min_key = min(keys)
    start_indices = [index for index, key in enumerate(keys) if key == min_key]
    candidates: list[list[str]] = []
    reversed_keys = list(reversed(keys))
    for index in start_indices:
        candidates.append(rotate(keys, index))
    for index, key in enumerate(reversed_keys):
        if key == min_key:
            candidates.append(rotate(reversed_keys, index))
    canonical = min(candidates)
    return canonical + [canonical[0]]


def _slope_face_loop_endpoint_key(point: tuple[float, float, float], *, tolerance: float = 1.0e-6) -> str:
    scale = 1.0 / max(float(tolerance or 0.0), 1.0e-9)
    x = int(round(float(point[0]) * scale))
    y = int(round(float(point[1]) * scale))
    z = int(round(float(point[2]) * scale))
    return f"{x}:{y}:{z}"


def _xyz_tuple(value) -> tuple[float, float, float]:
    try:
        seq = tuple(value or ())
    except Exception:
        seq = ()
    x = float(seq[0]) if len(seq) > 0 else 0.0
    y = float(seq[1]) if len(seq) > 1 else 0.0
    z = float(seq[2]) if len(seq) > 2 else 0.0
    return (x, y, z)


def _same_xy(a: tuple[float, float, float], b: tuple[float, float, float], tolerance: float = 1.0e-6) -> bool:
    return abs(float(a[0]) - float(b[0])) <= tolerance and abs(float(a[1]) - float(b[1])) <= tolerance


def _points_closed_xy(points: list[tuple[float, float, float]], tolerance: float = 1.0e-6) -> bool:
    if len(points) < 4:
        return False
    return _same_xy(points[0], points[-1], tolerance)


def _polyline_self_crosses_xy(points: list[tuple[float, float, float]], tolerance: float = 1.0e-9) -> bool:
    if len(points) < 5:
        return False
    segments = list(zip(points[:-1], points[1:]))
    for i, first in enumerate(segments):
        for j, second in enumerate(segments):
            if j <= i + 1:
                continue
            if i == 0 and j == len(segments) - 1:
                continue
            if _segments_intersect_xy(first[0], first[1], second[0], second[1], tolerance):
                return True
    return False


def _segments_intersect_xy(a1, a2, b1, b2, tolerance: float = 1.0e-9) -> bool:
    def orient(p, q, r):
        return (float(q[0]) - float(p[0])) * (float(r[1]) - float(p[1])) - (float(q[1]) - float(p[1])) * (float(r[0]) - float(p[0]))

    def on_segment(p, q, r):
        return (
            min(float(p[0]), float(r[0])) - tolerance <= float(q[0]) <= max(float(p[0]), float(r[0])) + tolerance
            and min(float(p[1]), float(r[1])) - tolerance <= float(q[1]) <= max(float(p[1]), float(r[1])) + tolerance
        )

    o1 = orient(a1, a2, b1)
    o2 = orient(a1, a2, b2)
    o3 = orient(b1, b2, a1)
    o4 = orient(b1, b2, a2)
    if abs(o1) <= tolerance and on_segment(a1, b1, a2):
        return True
    if abs(o2) <= tolerance and on_segment(a1, b2, a2):
        return True
    if abs(o3) <= tolerance and on_segment(b1, a1, b2):
        return True
    if abs(o4) <= tolerance and on_segment(b1, a2, b2):
        return True
    return (o1 > tolerance) != (o2 > tolerance) and (o3 > tolerance) != (o4 > tolerance)


def _duplicate_text_values(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        if text in seen and text not in duplicates:
            duplicates.append(text)
        seen.add(text)
    return tuple(duplicates)


def _grading_policy_by_ref(intersection_model: IntersectionModel, policy_ref: str, intersection_id: str):
    rows = list(getattr(intersection_model, "grading_policy_rows", []) or [])
    wanted = str(policy_ref or "").strip()
    for row in rows:
        if wanted and str(getattr(row, "policy_id", "") or "") == wanted:
            return row
    for row in rows:
        if str(getattr(row, "intersection_id", "") or "") == str(intersection_id or ""):
            return row
    return rows[0] if rows else None


def _intersection_crossfall_context(zone_role: str, grading_mode: str) -> str:
    role = str(zone_role or "").strip()
    mode = str(grading_mode or "").strip()
    if role == "exterior_slope_face":
        return "normal_superelevation"
    if role in {
        "central_pavement",
        "curb_return_pavement",
        "roundabout_central_island",
        "roundabout_circulatory_lane",
        "roundabout_truck_apron",
        "roundabout_outer_shoulder",
        "roundabout_entry_exit_connector",
    }:
        return "intersection_override" if mode != "use_normal_superelevation" else "normal_superelevation"
    if mode in {"flatten_intersection", "blend_primary_side", "keep_primary_crown", "roundabout_radial_crossfall"}:
        return "intersection_override"
    return "normal_superelevation"


def _grading_context_note(zone_role: str, grading_mode: str, crossfall_context: str) -> str:
    role = str(zone_role or "").strip()
    mode = str(grading_mode or "").strip()
    context = str(crossfall_context or "").strip()
    if context == "normal_superelevation":
        return "Normal Superelevation/Assembly crossfall remains the governing context outside the intersection override."
    if mode == "flatten_intersection":
        return f"{role} uses a flattened intersection grading override."
    if mode == "blend_primary_side":
        return f"{role} blends primary and secondary approach grading inside the control area."
    if mode == "keep_primary_crown":
        return f"{role} preserves the primary alignment crown through the intersection control area."
    if mode == "roundabout_radial_crossfall":
        return f"{role} uses roundabout radial crossfall intent; final ring grading remains a later geometry step."
    return f"{role} uses intersection grading override mode {mode or 'unknown'}."


def _drainage_hint_note(hint_kind: str, drainage_mode: str, zone_role: str) -> str:
    mode = str(drainage_mode or "review_low_points").strip()
    role = str(zone_role or "").strip()
    if str(hint_kind or "") == "outlet_handoff":
        return f"Drainage mode {mode} requires explicit outlet/outfall review after intersection grading is accepted."
    if str(hint_kind or "") == "low_point_candidate":
        if mode == "outside_gutter":
            return f"Review {role} as an outside-gutter low-point search zone before inlet placement."
        if mode == "central_island":
            return f"Review {role} for central-island drainage; confirm whether runoff drains inward or outward."
        return f"Review {role} for intersection low-point candidates before inlet placement."
    if mode == "outside_gutter":
        return f"Recommended inlet review near {role}; outside-gutter drainage needs explicit Drainage Elements."
    if mode == "central_island":
        return f"Recommended inlet/drain review near {role}; central-island drainage needs explicit collection and outlet design."
    return f"Recommended inlet review near {role}; create Drainage Elements explicitly before build."


def _intersection_drainage_outlet_hint_rows(
    surface_zones: IntersectionSurfaceZoneResult,
    *,
    drainage_policy_ref: str,
    drainage_mode: str,
    drainage_intent_status: str,
    drainage_source_method: str,
    drainage_approval_status: str,
    drainage_element_refs: tuple[str, ...],
    flow_route_refs: tuple[str, ...],
    inlet_candidate_refs: tuple[str, ...],
    low_point_refs: tuple[str, ...],
    drainage_handoff_status: str,
    drainage_source_scope: str,
    accepted_drainage_ref: str,
    drainage_review_status: str,
    source_lineage_status: str,
    source_status: str,
    handoff_target: str,
    control_ranges: dict[str, tuple[tuple[float, float], ...]],
    start_index: int,
) -> list[IntersectionDrainageHintRow]:
    mode = str(drainage_mode or "review_low_points").strip()
    if mode not in {"outside_gutter", "central_island"}:
        return []
    candidate_zones = [
        row
        for row in list(getattr(surface_zones, "zone_rows", []) or [])
        if str(getattr(row, "design_zone_role", "") or "") in {"central_pavement", "roundabout_circulatory_lane"}
    ]
    if not candidate_zones:
        return []
    output: list[IntersectionDrainageHintRow] = []
    for index, zone in enumerate(candidate_zones, start=start_index):
        control_area_refs = tuple(getattr(zone, "control_area_refs", ()) or ())
        output.append(
            IntersectionDrainageHintRow(
                hint_id=f"intersection-drainage-hint:{_id_token(surface_zones.intersection_id)}:outlet-{index:02d}",
                intersection_id=surface_zones.intersection_id,
                hint_kind="outlet_handoff",
                zone_ref=str(getattr(zone, "zone_id", "") or ""),
                zone_role=str(getattr(zone, "design_zone_role", "") or getattr(zone, "zone_role", "") or ""),
                surface_role=str(getattr(zone, "surface_role", "") or ""),
                recommended_element_kind="outlet_review",
                drainage_policy_ref=drainage_policy_ref,
                source_drainage_policy_ref=drainage_policy_ref,
                drainage_mode=mode,
                drainage_intent_status=drainage_intent_status,
                drainage_source_method=drainage_source_method,
                drainage_approval_status=drainage_approval_status,
                drainage_element_refs=drainage_element_refs,
                flow_route_refs=flow_route_refs,
                inlet_candidate_refs=inlet_candidate_refs,
                low_point_refs=low_point_refs,
                drainage_handoff_status=drainage_handoff_status,
                drainage_source_scope=drainage_source_scope,
                accepted_drainage_ref=accepted_drainage_ref,
                drainage_review_status=drainage_review_status,
                source_lineage_status=source_lineage_status,
                handoff_target=handoff_target,
                control_area_refs=control_area_refs,
                source_edge_refs=tuple(getattr(zone, "source_edge_refs", ()) or ()),
                boundary_edge_refs=tuple(getattr(zone, "boundary_edge_refs", ()) or ()),
                station_ranges=_station_ranges_for_refs(control_ranges, control_area_refs),
                source_status=source_status,
                source_diagnostic_rows=tuple(
                    item
                    for item in (
                        "source_drainage_element_refs_missing" if drainage_handoff_status == "accepted_source_incomplete" and not drainage_element_refs else "",
                        "source_drainage_flow_route_refs_missing" if drainage_handoff_status == "accepted_source_incomplete" and not flow_route_refs else "",
                    )
                    if item
                ),
                status=source_status if str(source_status or "") == "error" else "warning",
                diagnostic_rows=("warning:outlet_handoff_requires_user_drainage_element",),
                notes=_drainage_hint_note("outlet_handoff", mode, str(getattr(zone, "design_zone_role", "") or "")),
            )
        )
    return output


def _unique_float_values(values: list[float], *, tolerance: float = 1.0e-6) -> list[float]:
    output: list[float] = []
    for value in sorted(float(v) for v in list(values or [])):
        if output and abs(output[-1] - value) <= tolerance:
            continue
        output.append(value)
    return output


def _edge_network_row_id(
    intersection_id: str,
    family: str,
    family_index: int,
    edge_index: int,
    edge_role: str,
    side: str,
) -> str:
    return (
        f"intersection-edge:{_id_token(intersection_id)}:"
        f"{_id_token(family)}-{int(family_index):02d}:"
        f"{_id_token(edge_role)}-{_id_token(side)}-{int(edge_index):02d}"
    )


def _edges_by_leg(edge_rows: list[IntersectionEdgeNetworkRow]) -> dict[str, list[IntersectionEdgeNetworkRow]]:
    output: dict[str, list[IntersectionEdgeNetworkRow]] = {}
    for row in edge_rows:
        leg_ref = str(getattr(row, "leg_ref", "") or "")
        if not leg_ref:
            continue
        output.setdefault(leg_ref, []).append(row)
    return output


def _design_zone_role_from_leg_edges(edge_rows: list[IntersectionEdgeNetworkRow]) -> str:
    roles = _unique_text_values([str(getattr(row, "leg_role", "") or "") for row in edge_rows])
    if any(role.startswith("primary") or role.startswith("main") for role in roles):
        return "main_pavement"
    if roles:
        return "side_pavement"
    return "leg_pavement"


def _curb_edges_for_leg(
    leg_edge: IntersectionEdgeNetworkRow,
    curb_edges: list[IntersectionEdgeNetworkRow],
) -> list[IntersectionEdgeNetworkRow]:
    leg_ref = str(getattr(leg_edge, "leg_ref", "") or "")
    control_area_ref = str(getattr(leg_edge, "control_area_ref", "") or "")
    output: list[IntersectionEdgeNetworkRow] = []
    for curb_edge in curb_edges:
        leg_refs = _unique_text_values(str(getattr(curb_edge, "leg_ref", "") or "").split(","))
        if leg_ref and leg_ref in leg_refs:
            output.append(curb_edge)
    if output:
        return output
    if not control_area_ref:
        return []
    for curb_edge in curb_edges:
        if str(getattr(curb_edge, "source_status", "") or "accepted") not in {"accepted", "ready"}:
            continue
        if str(getattr(curb_edge, "status", "") or "ready") not in {"accepted", "ready"}:
            continue
        if str(getattr(curb_edge, "control_area_ref", "") or "") == control_area_ref:
            output.append(curb_edge)
    return output


def _slope_zone_boundary_audit_note(
    *,
    daylight_edge_ref: str,
    pavement_edge_refs: tuple[str, ...],
    curb_edge_refs: tuple[str, ...],
    source_edge_refs: tuple[str, ...],
) -> str:
    inner_refs = tuple(str(ref or "") for ref in pavement_edge_refs if str(ref or ""))
    outer_refs = tuple([str(daylight_edge_ref or "")] if str(daylight_edge_ref or "") else ())
    tie_refs = tuple(str(ref or "") for ref in curb_edge_refs if str(ref or ""))
    boundary_refs = tuple(str(ref or "") for ref in source_edge_refs if str(ref or ""))
    missing: list[str] = []
    if not inner_refs:
        missing.append("inner")
    if not outer_refs:
        missing.append("outer")
    if not tie_refs:
        missing.append("tie")
    parts = [
        f"slope_zone_boundary_audit=inner:{len(inner_refs)} outer:{len(outer_refs)} tie:{len(tie_refs)} boundary:{len(boundary_refs)}",
        "inner_refs=" + ",".join(inner_refs) if inner_refs else "inner_refs=missing",
        "outer_refs=" + ",".join(outer_refs) if outer_refs else "outer_refs=missing",
        "tie_refs=" + ",".join(tie_refs) if tie_refs else "tie_refs=missing",
    ]
    if missing:
        parts.append("missing=" + ",".join(missing))
    return "; ".join(parts)


def _surface_zone_grading_policy_ref(intersection_model: IntersectionModel, intersection_id: str) -> str:
    for row in list(getattr(intersection_model, "intersection_rows", []) or []):
        if str(getattr(row, "intersection_id", "") or "") == str(intersection_id or ""):
            return str(getattr(row, "grading_policy_ref", "") or "")
    return ""


def _drainage_policy_for_intersection(intersection_model: IntersectionModel, intersection_id: str):
    for policy in list(getattr(intersection_model, "drainage_policy_rows", []) or []):
        if str(getattr(policy, "intersection_id", "") or "") == str(intersection_id or ""):
            return policy
    return None


def _drainage_policy_source_diagnostics(policy) -> tuple[str, ...]:
    if policy is None:
        return ()
    diagnostics: list[str] = []
    for diagnostic in list(getattr(policy, "diagnostic_rows", []) or []):
        text = str(diagnostic or "").strip()
        if text:
            diagnostics.append(text)
    intent_status = str(getattr(policy, "intent_status", "") or "hint_only")
    capture_mode = str(getattr(policy, "capture_mode", "") or "review_low_points")
    source_method = str(getattr(policy, "source_method", "") or "manual")
    approval_status = str(getattr(policy, "approval_status", "") or "accepted")
    drainage_element_refs = [str(ref) for ref in list(getattr(policy, "drainage_element_refs", []) or []) if str(ref)]
    flow_route_refs = [str(ref) for ref in list(getattr(policy, "flow_route_refs", []) or []) if str(ref)]
    if capture_mode and capture_mode not in _VALID_DRAINAGE_CAPTURE_MODES:
        diagnostics.append("source_drainage_policy_capture_mode_unknown")
    if intent_status and intent_status not in _VALID_DRAINAGE_INTENT_STATUSES:
        diagnostics.append("source_drainage_policy_intent_status_unknown")
    if intent_status == "hint_only":
        diagnostics.append("source_drainage_policy_hint_only")
    if approval_status not in {"accepted", "locked"}:
        diagnostics.append("source_drainage_policy_approval_pending")
    if approval_status and approval_status not in _VALID_DRAINAGE_APPROVAL_STATUSES:
        diagnostics.append("source_drainage_policy_approval_status_unknown")
    if not source_method:
        diagnostics.append("source_drainage_policy_method_missing")
    elif source_method not in _VALID_DRAINAGE_SOURCE_METHODS:
        diagnostics.append("source_drainage_policy_method_unknown")
    if intent_status in {"accepted", "source_owned"} and not drainage_element_refs:
        diagnostics.append("source_drainage_element_refs_missing")
    if intent_status in {"accepted", "source_owned"} and not flow_route_refs:
        diagnostics.append("source_drainage_flow_route_refs_missing")
    return tuple(_unique_text_values(diagnostics))


def _drainage_policy_handoff_status(
    intent_status: str,
    drainage_element_refs: tuple[str, ...],
    flow_route_refs: tuple[str, ...],
    source_diagnostics: tuple[str, ...],
) -> str:
    intent = str(intent_status or "").strip()
    if intent == "hint_only":
        return "hint_only"
    if intent in {"accepted", "source_owned"} and drainage_element_refs and flow_route_refs and not source_diagnostics:
        return "accepted_handoff"
    if intent in {"accepted", "source_owned"}:
        return "accepted_source_incomplete"
    return "review_required"


def _drainage_policy_source_scope(intent_status: str, handoff_status: str) -> str:
    if handoff_status == "accepted_handoff":
        return "source_owned"
    if str(intent_status or "") == "hint_only":
        return "hint"
    return "review"


def _accepted_drainage_ref(drainage_element_refs: tuple[str, ...], flow_route_refs: tuple[str, ...]) -> str:
    if drainage_element_refs:
        return drainage_element_refs[0]
    if flow_route_refs:
        return flow_route_refs[0]
    return ""


def _drainage_policy_review_status(handoff_status: str) -> str:
    return "accepted" if str(handoff_status or "") == "accepted_handoff" else "review_required"


def _drainage_hint_source_lineage_status(
    intent_status: str,
    handoff_status: str,
    source_diagnostics: tuple[str, ...],
) -> str:
    if str(handoff_status or "") == "accepted_handoff":
        return "accepted_source"
    if str(handoff_status or "") == "accepted_source_incomplete":
        return "source_incomplete"
    if str(intent_status or "") == "hint_only":
        return "hint_only"
    if source_diagnostics:
        return "source_warning"
    return "review_required"


def _drainage_hint_source_status(
    handoff_status: str,
    source_diagnostics: tuple[str, ...],
) -> str:
    if str(handoff_status or "") == "accepted_source_incomplete":
        return "error"
    if source_diagnostics:
        return "warning"
    return "accepted"


def _drainage_hint_handoff_target(policy_ref: str, intersection_id: str) -> str:
    return f"intersection-source-stage:drainage:{_id_token(policy_ref or intersection_id or 'main')}"


def _control_area_station_ranges_by_id(
    intersection_model: IntersectionModel,
    intersection_id: str,
) -> dict[str, tuple[tuple[float, float], ...]]:
    output: dict[str, tuple[tuple[float, float], ...]] = {}
    for area in list(getattr(intersection_model, "control_area_rows", []) or []):
        if str(getattr(area, "intersection_id", "") or "") != str(intersection_id or ""):
            continue
        area_id = str(getattr(area, "control_area_id", "") or "")
        if not area_id:
            continue
        output[area_id] = tuple(
            (float(start or 0.0), float(end or 0.0))
            for start, end in list(getattr(area, "station_ranges", []) or [])
        )
    return output


def _station_ranges_for_refs(
    ranges_by_control_area: dict[str, tuple[tuple[float, float], ...]],
    control_area_refs,
) -> tuple[tuple[float, float], ...]:
    output: list[tuple[float, float]] = []
    for ref in list(control_area_refs or []):
        for start, end in list(ranges_by_control_area.get(str(ref or ""), ()) or ()):
            pair = (float(start), float(end))
            if pair not in output:
                output.append(pair)
    return tuple(output)


def _id_token(value: object) -> str:
    text = str(value or "").strip()
    output = []
    for char in text:
        output.append(char if char.isalnum() else "-")
    token = "".join(output).strip("-").lower()
    return token or "none"
