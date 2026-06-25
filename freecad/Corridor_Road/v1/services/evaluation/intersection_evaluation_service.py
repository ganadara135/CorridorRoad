"""Intersection evaluation service for CorridorRoad v1."""

from __future__ import annotations

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
            if design_role in {"central_pavement", "roundabout_circulatory_pavement"}:
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
            if design_role in {"curb_return_pavement", "roundabout_entry_exit_pavement"} or zone_family == "slope":
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
                    source_status="warning" if source_diagnostics else "accepted",
                    source_diagnostic_rows=source_diagnostics,
                    status="ready" if not slope_diagnostics and not source_diagnostics else "warning",
                    diagnostic_rows=tuple([*slope_diagnostics, *source_diagnostics]),
                    notes="Slope-face zone boundary contract only; no triangulation generated.",
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

    def evaluate_slope_face_loops(
        self,
        intersection_model: IntersectionModel | None,
        surface_zone_result: IntersectionSurfaceZoneResult | None = None,
        edge_network_result: IntersectionEdgeNetworkResult | None = None,
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
            loop_points = _slope_face_loop_points_from_edges(boundary_edge_refs, edge_by_id)
            missing_edge_refs = tuple(ref for ref in boundary_edge_refs if ref and ref not in edge_by_id)
            duplicate_edge_refs = _duplicate_text_values(boundary_edge_refs)
            closed_xy = _points_closed_xy(loop_points)
            self_crossing = _polyline_self_crosses_xy(loop_points)
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
            loop_family = _slope_face_loop_family(zone)
            status = "error" if any(str(item).startswith("error:") for item in loop_diagnostics) or source_lineage_status == "source_error" else (
                "ready" if not loop_diagnostics and source_lineage_status == "accepted" else "warning"
            )
            loop_rows.append(
                IntersectionSlopeFaceLoopRow(
                    loop_id=f"intersection-slope-face-loop:{_id_token(surface_zones.intersection_id)}:{index:02d}",
                    intersection_id=str(getattr(surface_zones, "intersection_id", "") or ""),
                    loop_family=loop_family,
                    alignment_ref=str((tuple(getattr(zone, "alignment_refs", ()) or ("",))[0] if tuple(getattr(zone, "alignment_refs", ()) or ()) else "")),
                    leg_ref=str((tuple(getattr(zone, "leg_refs", ()) or ("",))[0] if tuple(getattr(zone, "leg_refs", ()) or ()) else "")),
                    side=_slope_face_loop_side(zone),
                    inner_edge_refs=inner_edge_refs,
                    outer_edge_refs=outer_edge_refs,
                    tie_edge_refs=tie_edge_refs,
                    boundary_edge_refs=boundary_edge_refs,
                    loop_points_xyz=tuple(loop_points),
                    source_edge_network_refs=source_edge_refs,
                    source_edge_network_status=source_edge_network_status,
                    source_surface_zone_refs=source_surface_zone_refs,
                    source_surface_zone_status=source_surface_zone_status,
                    source_status=_slope_face_loop_source_status(source_lineage_status),
                    source_diagnostic_rows=tuple(source_diagnostics),
                    source_lineage_status=source_lineage_status,
                    closed_xy=closed_xy,
                    self_crossing=self_crossing,
                    overlaps_intersection_surface=False,
                    point_count=len(loop_points),
                    status=status,
                    diagnostics=tuple(loop_diagnostics),
                    notes="Slope Face loop candidate from surface-zone contract; no triangulation generated.",
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
                        source_status=edge_family_source_status,
                        source_diagnostic_rows=tuple(row_diagnostics),
                        status=edge_family_source_status if edge_family_source_status != "accepted" else "ready",
                        notes="; ".join(row_diagnostics),
                    )
                )

        corner_by_id = _corner_rows_by_id(intersection_model, topology.intersection_id)
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
                edge_rows.append(
                    IntersectionEdgeNetworkRow(
                        edge_id=_edge_network_row_id(topology.intersection_id, "curb-return", policy_index, side_index, "curb_return_edge", side),
                        intersection_id=topology.intersection_id,
                        edge_role="curb_return_edge",
                        edge_family="curb_return",
                        source_policy_ref=str(getattr(policy, "policy_id", "") or ""),
                        source_corner_ref=corner_ref,
                        leg_ref=",".join(str(ref) for ref in list(getattr(policy, "approach_leg_refs", []) or []) if str(ref)),
                        side=side,
                        radius=float(getattr(policy, "radius", 0.0) or 0.0),
                        contact_station_refs=contact_station_refs,
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

        leg_span_rows: list[IntersectionTopologyLegSpanRow] = []
        for index, leg in enumerate(leg_rows, start=1):
            leg_id = str(getattr(leg, "leg_id", "") or f"{row.intersection_id}:leg:{index:02d}")
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
                    source_method=source_method,
                    approval_status=approval_status,
                    span_source=span_source,
                    source_status=leg_source_status,
                    source_diagnostic_rows=tuple(leg_diagnostics),
                    status=leg_source_status if leg_source_status != "accepted" else "ready",
                    notes="; ".join(leg_diagnostics),
                )
            )

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
            control_area_count=len(control_area_rows),
            lane_connection_count=len(lane_connection_rows),
            policy_refs=policy_refs,
            diagnostic_rows=diagnostics,
            anchor_rows=anchor_rows,
            leg_span_rows=leg_span_rows,
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


def _roundabout_edge_network_rows(
    intersection_model: IntersectionModel,
    topology_result: IntersectionTopologyResult,
) -> list[IntersectionEdgeNetworkRow]:
    """Return first-slice roundabout edge-family rows for source/topology review."""

    row = IntersectionEvaluationService._find_topology_intersection_row(
        intersection_model,
        str(getattr(topology_result, "intersection_id", "") or ""),
    )
    if row is None:
        return []
    policies = _curb_return_policies_for_intersection(intersection_model, topology_result.intersection_id)
    policy = policies[0] if policies else None
    policy_ref = str(getattr(policy, "policy_id", "") or f"roundabout-policy:{topology_result.intersection_id}:default")
    radius = float(getattr(policy, "radius", 0.0) or 18.0)
    if radius <= 0.0:
        radius = 18.0
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
            radius=radius * 0.5,
            contact_station_refs=contact_station_refs,
            status="candidate",
            notes="roundabout_first_slice_central_island_edge",
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
            status="candidate",
            notes="roundabout_first_slice_circulatory_edge",
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
                status="candidate",
                notes="roundabout_first_slice_entry_exit_edge",
            )
        )
    return rows


def _roundabout_surface_zone_rows(
    intersection_model: IntersectionModel,
    edge_network: IntersectionEdgeNetworkResult,
    roundabout_edges: list[IntersectionEdgeNetworkRow],
) -> list[IntersectionSurfaceZoneRow]:
    """Return first-slice roundabout surface-zone contracts from roundabout edge rows."""

    if not roundabout_edges:
        return []
    grading_ref = _surface_zone_grading_policy_ref(intersection_model, edge_network.intersection_id)
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
                zone_role="roundabout_circulatory_roadway",
                zone_family="roundabout",
                design_zone_role="roundabout_circulatory_pavement",
                surface_role="design",
                source_edge_refs=source_edge_refs,
                boundary_edge_refs=source_edge_refs,
                inner_edge_refs=tuple(str(row.edge_id) for row in central_edges),
                outer_edge_refs=tuple(str(row.edge_id) for row in circulatory_edges),
                leg_refs=tuple(_unique_text_values([row.leg_ref for row in [*central_edges, *circulatory_edges]])),
                alignment_refs=tuple(_unique_text_values([row.alignment_ref for row in [*central_edges, *circulatory_edges]])),
                vertical_policy_ref=grading_ref,
                surface_priority=_surface_priority("roundabout_circulatory_pavement"),
                triangulation_method="pending_roundabout_ring_zone",
                source_status="warning" if source_diagnostics else "accepted",
                source_diagnostic_rows=source_diagnostics,
                status="candidate",
                notes="Roundabout circulatory roadway source-zone contract only; no triangulation generated.",
            )
        )
    for index, edge in enumerate(entry_edges, start=1):
        source_edge_refs = (str(edge.edge_id),)
        source_diagnostics = _surface_zone_source_diagnostics(source_edge_refs, edge_by_id)
        zone_rows.append(
            IntersectionSurfaceZoneRow(
                zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:roundabout-entry-exit-{index:02d}",
                intersection_id=edge_network.intersection_id,
                zone_role="roundabout_entry_exit",
                zone_family="roundabout",
                design_zone_role="roundabout_entry_exit_pavement",
                surface_role="design",
                source_edge_refs=source_edge_refs,
                boundary_edge_refs=source_edge_refs,
                tie_edge_refs=tuple(str(row.edge_id) for row in circulatory_edges),
                leg_refs=(str(edge.leg_ref),) if str(edge.leg_ref) else (),
                alignment_refs=(str(edge.alignment_ref),) if str(edge.alignment_ref) else (),
                control_area_refs=(str(edge.control_area_ref),) if str(edge.control_area_ref) else (),
                vertical_policy_ref=grading_ref,
                surface_priority=_surface_priority("roundabout_entry_exit_pavement"),
                triangulation_method="pending_roundabout_entry_exit_zone",
                source_status="warning" if source_diagnostics else "accepted",
                source_diagnostic_rows=source_diagnostics,
                status="candidate",
                notes="Roundabout entry/exit source-zone contract only; no triangulation generated.",
            )
        )
    return zone_rows


def _surface_priority(design_zone_role: str) -> int:
    role = str(design_zone_role or "").strip()
    priorities = {
        "central_pavement": 100,
        "roundabout_central_island": 98,
        "roundabout_circulatory_pavement": 96,
        "curb_return_pavement": 90,
        "roundabout_entry_exit_pavement": 88,
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
        "roundabout_circulatory_pavement",
        "roundabout_entry_exit_pavement",
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
        if str(getattr(row, "design_zone_role", "") or "") in {"central_pavement", "roundabout_circulatory_pavement"}
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
    if not leg_ref:
        return []
    output: list[IntersectionEdgeNetworkRow] = []
    for curb_edge in curb_edges:
        leg_refs = _unique_text_values(str(getattr(curb_edge, "leg_ref", "") or "").split(","))
        if leg_ref in leg_refs:
            output.append(curb_edge)
    return output


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
