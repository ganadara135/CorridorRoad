"""Intersection evaluation service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.source.intersection_model import (
    IntersectionControlArea,
    IntersectionCurbReturnPolicyRow,
    IntersectionEdgePolicyRow,
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
    IntersectionTopologyControlAreaRow,
    IntersectionTopologyLegSpanRow,
    IntersectionTopologyResult,
)


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
            zone_role = str(getattr(zone, "design_zone_role", "") or getattr(zone, "zone_role", "") or "")
            crossfall_context = _intersection_crossfall_context(zone_role, mode)
            if crossfall_context == "intersection_override" and mode == "use_normal_superelevation":
                row_diagnostics.append("warning:intersection_zone_uses_normal_superelevation")
            context_rows.append(
                IntersectionGradingContextRow(
                    context_id=f"intersection-grading-context:{_id_token(surface_zones.intersection_id)}:{index:02d}",
                    intersection_id=surface_zones.intersection_id,
                    zone_ref=str(getattr(zone, "zone_id", "") or ""),
                    zone_role=zone_role,
                    surface_role=str(getattr(zone, "surface_role", "") or ""),
                    surface_priority=int(getattr(zone, "surface_priority", 0) or 0),
                    grading_policy_ref=policy_ref or str(getattr(policy, "policy_id", "") or ""),
                    grading_mode=mode,
                    target_crossfall_percent=float(getattr(policy, "target_crossfall_percent", 0.0) or 0.0),
                    crossfall_context=crossfall_context,
                    primary_alignment_ref=str(getattr(policy, "primary_alignment_ref", "") or ""),
                    secondary_alignment_refs=tuple(str(ref) for ref in list(getattr(policy, "secondary_alignment_refs", []) or []) if str(ref)),
                    alignment_refs=tuple(getattr(zone, "alignment_refs", ()) or ()),
                    control_area_refs=tuple(getattr(zone, "control_area_refs", ()) or ()),
                    status="warning" if row_diagnostics else "ready",
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
        if not drainage_policy_ref:
            diagnostics.append("warning:intersection_drainage_policy_missing")
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
                        drainage_mode=drainage_mode,
                        grading_context_ref=str(getattr(grading_row, "context_id", "") or ""),
                        crossfall_context=str(getattr(grading_row, "crossfall_context", "") or ""),
                        control_area_refs=tuple(getattr(zone, "control_area_refs", ()) or ()),
                        source_edge_refs=tuple(getattr(zone, "source_edge_refs", ()) or ()),
                        boundary_edge_refs=tuple(getattr(zone, "boundary_edge_refs", ()) or ()),
                        station_ranges=_station_ranges_for_refs(control_ranges, getattr(zone, "control_area_refs", ()) or ()),
                        status="warning" if row_diagnostics else "ready",
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
                        drainage_mode=drainage_mode,
                        grading_context_ref=str(getattr(grading_row, "context_id", "") or ""),
                        crossfall_context=str(getattr(grading_row, "crossfall_context", "") or ""),
                        control_area_refs=tuple(getattr(zone, "control_area_refs", ()) or ()),
                        source_edge_refs=tuple(getattr(zone, "source_edge_refs", ()) or ()),
                        boundary_edge_refs=tuple(getattr(zone, "boundary_edge_refs", ()) or ()),
                        station_ranges=_station_ranges_for_refs(control_ranges, getattr(zone, "control_area_refs", ()) or ()),
                        status="warning" if row_diagnostics else "ready",
                        diagnostic_rows=tuple(row_diagnostics),
                        notes=_drainage_hint_note("inlet_recommendation", drainage_mode, design_role or zone_family),
                    )
                )
        outlet_hints = _intersection_drainage_outlet_hint_rows(
            surface_zones,
            drainage_policy_ref=drainage_policy_ref,
            drainage_mode=drainage_mode,
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
                        protected_zone_refs=zone_refs,
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
        zone_rows: list[IntersectionSurfaceZoneRow] = []

        if len(_unique_text_values([row.alignment_ref for row in pavement_edges])) >= 2:
            zone_rows.append(
                IntersectionSurfaceZoneRow(
                    zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:central-junction",
                    intersection_id=edge_network.intersection_id,
                    zone_role="central_junction",
                    zone_family="pavement",
                    design_zone_role="central_pavement",
                    surface_role="design",
                    source_edge_refs=tuple(str(row.edge_id) for row in pavement_edges),
                    leg_refs=tuple(_unique_text_values([row.leg_ref for row in pavement_edges])),
                    alignment_refs=tuple(_unique_text_values([row.alignment_ref for row in pavement_edges])),
                    control_area_refs=tuple(_unique_text_values([row.control_area_ref for row in pavement_edges])),
                    vertical_policy_ref=_surface_zone_grading_policy_ref(intersection_model, edge_network.intersection_id),
                    surface_priority=_surface_priority("central_pavement"),
                    triangulation_method="pending_structured_zone",
                    status="candidate",
                    notes="Central junction zone contract only; no triangulation generated.",
                )
            )
        else:
            diagnostics.append("warning:surface_zone_central_junction_requires_two_pavement_alignments")

        for index, (leg_ref, edges) in enumerate(_edges_by_leg(pavement_edges).items(), start=1):
            design_zone_role = _design_zone_role_from_leg_edges(edges)
            zone_rows.append(
                IntersectionSurfaceZoneRow(
                    zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:leg-pavement-{index:02d}",
                    intersection_id=edge_network.intersection_id,
                    zone_role="leg_pavement",
                    zone_family="pavement",
                    design_zone_role=design_zone_role,
                    surface_role="design",
                    source_edge_refs=tuple(str(row.edge_id) for row in edges),
                    leg_refs=(leg_ref,),
                    alignment_refs=tuple(_unique_text_values([row.alignment_ref for row in edges])),
                    control_area_refs=tuple(_unique_text_values([row.control_area_ref for row in edges])),
                    vertical_policy_ref=_surface_zone_grading_policy_ref(intersection_model, edge_network.intersection_id),
                    surface_priority=_surface_priority(design_zone_role),
                    triangulation_method="pending_structured_strip",
                    status="candidate",
                    notes=f"{design_zone_role} contract only; no triangulation generated.",
                )
            )

        pavement_edges_by_leg = _edges_by_leg(pavement_edges)
        for index, edge in enumerate(curb_edges, start=1):
            curb_leg_refs = tuple(_unique_text_values(str(getattr(edge, "leg_ref", "") or "").split(",")))
            curb_context_edges = [context_edge for leg_ref in curb_leg_refs for context_edge in pavement_edges_by_leg.get(leg_ref, [])]
            zone_rows.append(
                IntersectionSurfaceZoneRow(
                    zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:curb-return-{index:02d}",
                    intersection_id=edge_network.intersection_id,
                    zone_role="curb_return",
                    zone_family="curb_return",
                    design_zone_role="curb_return_pavement",
                    surface_role="design",
                    source_edge_refs=(str(edge.edge_id),),
                    leg_refs=curb_leg_refs,
                    alignment_refs=tuple(_unique_text_values([row.alignment_ref for row in curb_context_edges])),
                    control_area_refs=tuple(_unique_text_values([row.control_area_ref for row in curb_context_edges])),
                    vertical_policy_ref=_surface_zone_grading_policy_ref(intersection_model, edge_network.intersection_id),
                    surface_priority=_surface_priority("curb_return_pavement"),
                    triangulation_method="pending_curb_return_fan",
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
            zone_rows.append(
                IntersectionSurfaceZoneRow(
                    zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:slope-face-{index:02d}",
                    intersection_id=edge_network.intersection_id,
                    zone_role="exterior_slope_face",
                    zone_family="slope",
                    design_zone_role="exterior_slope_face",
                    surface_role="slope_face",
                    source_edge_refs=(daylight_edge_ref, *pavement_edge_refs, *curb_edge_refs),
                    boundary_edge_refs=(daylight_edge_ref, *pavement_edge_refs, *curb_edge_refs),
                    inner_edge_refs=pavement_edge_refs,
                    outer_edge_refs=(daylight_edge_ref,),
                    tie_edge_refs=curb_edge_refs,
                    leg_refs=(str(edge.leg_ref),),
                    alignment_refs=(str(edge.alignment_ref),) if str(edge.alignment_ref) else (),
                    control_area_refs=(str(edge.control_area_ref),) if str(edge.control_area_ref) else (),
                    surface_priority=_surface_priority("exterior_slope_face"),
                    triangulation_method="pending_daylight_zone",
                    status="ready" if not slope_diagnostics else "warning",
                    diagnostic_rows=tuple(slope_diagnostics),
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
            inner_edge_refs = tuple(str(value) for value in tuple(getattr(zone, "inner_edge_refs", ()) or ()))
            outer_edge_refs = tuple(str(value) for value in tuple(getattr(zone, "outer_edge_refs", ()) or ()))
            tie_edge_refs = tuple(str(value) for value in tuple(getattr(zone, "tie_edge_refs", ()) or ()))
            boundary_edge_refs = tuple(str(value) for value in tuple(getattr(zone, "boundary_edge_refs", ()) or ()))
            if not boundary_edge_refs:
                boundary_edge_refs = (*inner_edge_refs, *outer_edge_refs, *tie_edge_refs)
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
            if not tuple(getattr(zone, "source_edge_refs", ()) or ()):
                loop_diagnostics.append("warning:slope_face_loop_source_edge_refs_missing")
                diagnostics.append(f"warning:slope_face_loop_source_edge_refs_missing:{getattr(zone, 'zone_id', '')}")
            loop_family = _slope_face_loop_family(zone)
            status = "error" if any(str(item).startswith("error:") for item in loop_diagnostics) else ("ready" if not loop_diagnostics else "warning")
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
                    source_edge_network_refs=tuple(str(value) for value in tuple(getattr(zone, "source_edge_refs", ()) or ())),
                    source_surface_zone_refs=(str(getattr(zone, "zone_id", "") or ""),),
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
                if policy is None:
                    diagnostics.append(f"warning:edge_network_policy_ref_unresolved:{edge_ref}")
                edge_role = str(getattr(policy, "edge_role", "") or "")
                if not edge_role:
                    edge_role = _edge_role_from_policy_ref(edge_ref)
                side = str(getattr(policy, "side", "") or "both") if policy is not None else "both"
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
                        status="warning" if policy is None else "ready",
                        notes="unresolved_edge_policy" if policy is None else "",
                    )
                )

        for policy_index, policy in enumerate(_curb_return_policies_for_intersection(intersection_model, topology.intersection_id), start=1):
            contact_station_refs = _curb_return_contact_station_refs(
                intersection_model,
                topology,
                policy,
            )
            for side_index, side in enumerate(_curb_return_sides(policy, topology.intersection_kind), start=1):
                edge_rows.append(
                    IntersectionEdgeNetworkRow(
                        edge_id=_edge_network_row_id(topology.intersection_id, "curb-return", policy_index, side_index, "curb_return_edge", side),
                        intersection_id=topology.intersection_id,
                        edge_role="curb_return_edge",
                        edge_family="curb_return",
                        source_policy_ref=str(getattr(policy, "policy_id", "") or ""),
                        leg_ref=",".join(str(ref) for ref in list(getattr(policy, "approach_leg_refs", []) or []) if str(ref)),
                        side=side,
                        radius=float(getattr(policy, "radius", 0.0) or 0.0),
                        contact_station_refs=contact_station_refs,
                        status="ready" if float(getattr(policy, "radius", 0.0) or 0.0) > 0.0 else "warning",
                        notes="" if float(getattr(policy, "radius", 0.0) or 0.0) > 0.0 else "curb_return_radius_missing",
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

        if not str(getattr(row, "intersection_kind", "") or ""):
            diagnostics.append("error:intersection_kind_missing")
        elif not row.is_supported_kind:
            diagnostics.append(f"warning:intersection_kind_not_first_slice_supported:{row.intersection_kind}")

        if not leg_rows:
            diagnostics.append("error:intersection_leg_rows_missing")

        leg_span_rows: list[IntersectionTopologyLegSpanRow] = []
        for index, leg in enumerate(leg_rows, start=1):
            leg_id = str(getattr(leg, "leg_id", "") or f"{row.intersection_id}:leg:{index:02d}")
            alignment_ref = str(getattr(leg, "alignment_ref", "") or "")
            start = float(getattr(leg, "approach_station_start", 0.0) or 0.0)
            end = float(getattr(leg, "approach_station_end", 0.0) or 0.0)
            arm_policy_ref = str(getattr(leg, "arm_policy_ref", "") or "")
            edge_policy_refs = tuple(str(ref) for ref in list(getattr(leg, "edge_policy_refs", []) or []) if str(ref))
            grading_policy_ref = str(getattr(leg, "grading_policy_ref", "") or getattr(row, "grading_policy_ref", "") or "")
            leg_diagnostics = []
            if not alignment_ref:
                leg_diagnostics.append("missing_alignment")
                diagnostics.append(f"error:leg_missing_alignment_ref:{leg_id}")
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
                    status="warning" if leg_diagnostics else "ready",
                    notes="; ".join(leg_diagnostics),
                )
            )

        control_area_rows: list[IntersectionTopologyControlAreaRow] = []
        for area in self._control_areas_for_intersection(intersection_model, row.intersection_id):
            station_ranges = _range_tuple(getattr(area, "station_ranges", []) or [])
            influence_ranges = _range_tuple(getattr(area, "influence_ranges", []) or [])
            area_diagnostics = []
            if not str(getattr(area, "alignment_ref", "") or ""):
                area_diagnostics.append("missing_alignment")
                diagnostics.append(f"error:control_area_missing_alignment_ref:{area.control_area_id}")
            if not station_ranges:
                area_diagnostics.append("missing_station_range")
                diagnostics.append(f"error:control_area_station_ranges_missing:{area.control_area_id}")
            control_area_rows.append(
                IntersectionTopologyControlAreaRow(
                    control_area_id=area.control_area_id,
                    intersection_id=area.intersection_id,
                    alignment_ref=area.alignment_ref,
                    station_ranges=station_ranges,
                    influence_ranges=influence_ranges,
                    control_region_refs=tuple(str(ref) for ref in list(area.control_region_refs or []) if str(ref)),
                    curb_return_policy_ref=area.curb_return_policy_ref,
                    grading_policy_ref=area.grading_policy_ref,
                    drainage_policy_ref=area.drainage_policy_ref,
                    status="warning" if area_diagnostics else "ready",
                    notes="; ".join(area_diagnostics),
                )
            )
        if not control_area_rows:
            diagnostics.append("error:intersection_control_area_rows_missing")

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
            leg_span_count=len(leg_span_rows),
            control_area_count=len(control_area_rows),
            policy_refs=policy_refs,
            diagnostic_rows=diagnostics,
            leg_span_rows=leg_span_rows,
            control_area_rows=control_area_rows,
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


def _topology_status(diagnostics: list[str]) -> str:
    if any(str(row).startswith("error:") for row in diagnostics):
        return "error"
    if diagnostics:
        return "warning"
    return "ready"


def _curb_return_policies_for_intersection(
    intersection_model: IntersectionModel,
    intersection_id: str,
) -> list[IntersectionCurbReturnPolicyRow]:
    return [
        policy
        for policy in list(getattr(intersection_model, "curb_return_policy_rows", []) or [])
        if str(getattr(policy, "intersection_id", "") or "") == str(intersection_id or "")
    ]


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
    zone_rows: list[IntersectionSurfaceZoneRow] = []
    central_edges = [row for row in roundabout_edges if str(getattr(row, "edge_role", "") or "") == "central_island_edge"]
    circulatory_edges = [row for row in roundabout_edges if str(getattr(row, "edge_role", "") or "") == "circulatory_outer_edge"]
    entry_edges = [row for row in roundabout_edges if str(getattr(row, "edge_role", "") or "") == "entry_exit_edge"]
    if central_edges:
        zone_rows.append(
            IntersectionSurfaceZoneRow(
                zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:roundabout-central-island",
                intersection_id=edge_network.intersection_id,
                zone_role="roundabout_central_island",
                zone_family="roundabout",
                design_zone_role="roundabout_central_island",
                surface_role="design",
                source_edge_refs=tuple(str(row.edge_id) for row in central_edges),
                boundary_edge_refs=tuple(str(row.edge_id) for row in central_edges),
                inner_edge_refs=tuple(str(row.edge_id) for row in central_edges),
                leg_refs=tuple(_unique_text_values([row.leg_ref for row in central_edges])),
                alignment_refs=tuple(_unique_text_values([row.alignment_ref for row in central_edges])),
                vertical_policy_ref=grading_ref,
                surface_priority=_surface_priority("roundabout_central_island"),
                triangulation_method="pending_roundabout_island_zone",
                status="candidate",
                notes="Roundabout central island source-zone contract only; no triangulation generated.",
            )
        )
    if circulatory_edges:
        zone_rows.append(
            IntersectionSurfaceZoneRow(
                zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:roundabout-circulatory",
                intersection_id=edge_network.intersection_id,
                zone_role="roundabout_circulatory_roadway",
                zone_family="roundabout",
                design_zone_role="roundabout_circulatory_pavement",
                surface_role="design",
                source_edge_refs=tuple(str(row.edge_id) for row in [*central_edges, *circulatory_edges]),
                boundary_edge_refs=tuple(str(row.edge_id) for row in [*central_edges, *circulatory_edges]),
                inner_edge_refs=tuple(str(row.edge_id) for row in central_edges),
                outer_edge_refs=tuple(str(row.edge_id) for row in circulatory_edges),
                leg_refs=tuple(_unique_text_values([row.leg_ref for row in [*central_edges, *circulatory_edges]])),
                alignment_refs=tuple(_unique_text_values([row.alignment_ref for row in [*central_edges, *circulatory_edges]])),
                vertical_policy_ref=grading_ref,
                surface_priority=_surface_priority("roundabout_circulatory_pavement"),
                triangulation_method="pending_roundabout_ring_zone",
                status="candidate",
                notes="Roundabout circulatory roadway source-zone contract only; no triangulation generated.",
            )
        )
    for index, edge in enumerate(entry_edges, start=1):
        zone_rows.append(
            IntersectionSurfaceZoneRow(
                zone_id=f"intersection-zone:{_id_token(edge_network.intersection_id)}:roundabout-entry-exit-{index:02d}",
                intersection_id=edge_network.intersection_id,
                zone_role="roundabout_entry_exit",
                zone_family="roundabout",
                design_zone_role="roundabout_entry_exit_pavement",
                surface_role="design",
                source_edge_refs=(str(edge.edge_id),),
                boundary_edge_refs=(str(edge.edge_id),),
                tie_edge_refs=tuple(str(row.edge_id) for row in circulatory_edges),
                leg_refs=(str(edge.leg_ref),) if str(edge.leg_ref) else (),
                alignment_refs=(str(edge.alignment_ref),) if str(edge.alignment_ref) else (),
                control_area_refs=(str(edge.control_area_ref),) if str(edge.control_area_ref) else (),
                vertical_policy_ref=grading_ref,
                surface_priority=_surface_priority("roundabout_entry_exit_pavement"),
                triangulation_method="pending_roundabout_entry_exit_zone",
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
                drainage_mode=mode,
                control_area_refs=control_area_refs,
                source_edge_refs=tuple(getattr(zone, "source_edge_refs", ()) or ()),
                boundary_edge_refs=tuple(getattr(zone, "boundary_edge_refs", ()) or ()),
                station_ranges=_station_ranges_for_refs(control_ranges, control_area_refs),
                status="warning",
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
