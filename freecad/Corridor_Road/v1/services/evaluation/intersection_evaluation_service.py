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
from ...models.result.intersection_corridor_clipping import (
    IntersectionCorridorClipResult,
    IntersectionCorridorClipRow,
)
from ...models.result.intersection_drainage_hint import (
    IntersectionDrainageHintResult,
    IntersectionDrainageHintRow,
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

    def evaluate_drainage_hints(
        self,
        intersection_model: IntersectionModel | None,
        surface_zone_result: IntersectionSurfaceZoneResult | None = None,
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
        if not drainage_policy_ref:
            diagnostics.append("warning:intersection_drainage_policy_missing")

        control_ranges = _control_area_station_ranges_by_id(
            intersection_model,
            str(getattr(surface_zones, "intersection_id", "") or intersection_id or ""),
        )
        hint_rows: list[IntersectionDrainageHintRow] = []
        zone_rows = list(getattr(surface_zones, "zone_rows", []) or [])
        for zone in zone_rows:
            design_role = str(getattr(zone, "design_zone_role", "") or "")
            zone_family = str(getattr(zone, "zone_family", "") or "")
            if design_role == "central_pavement":
                row_diagnostics = []
                if not drainage_policy_ref:
                    row_diagnostics.append("warning:low_point_hint_drainage_policy_missing")
                hint_rows.append(
                    IntersectionDrainageHintRow(
                        hint_id=f"intersection-drainage-hint:{_id_token(surface_zones.intersection_id)}:low-point-{len(hint_rows) + 1:02d}",
                        intersection_id=surface_zones.intersection_id,
                        hint_kind="low_point_candidate",
                        zone_ref=str(getattr(zone, "zone_id", "") or ""),
                        zone_role=design_role,
                        surface_role=str(getattr(zone, "surface_role", "") or ""),
                        recommended_element_kind="low_point_review",
                        drainage_policy_ref=drainage_policy_ref,
                        control_area_refs=tuple(getattr(zone, "control_area_refs", ()) or ()),
                        source_edge_refs=tuple(getattr(zone, "source_edge_refs", ()) or ()),
                        boundary_edge_refs=tuple(getattr(zone, "boundary_edge_refs", ()) or ()),
                        station_ranges=_station_ranges_for_refs(control_ranges, getattr(zone, "control_area_refs", ()) or ()),
                        status="warning" if row_diagnostics else "ready",
                        diagnostic_rows=tuple(row_diagnostics),
                        notes="Review central junction zone for the intersection low point before inlet placement.",
                    )
                )
            if design_role == "curb_return_pavement" or zone_family == "slope":
                row_diagnostics = []
                if not drainage_policy_ref:
                    row_diagnostics.append("warning:inlet_recommendation_drainage_policy_missing")
                if not tuple(getattr(zone, "boundary_edge_refs", ()) or ()) and not tuple(getattr(zone, "source_edge_refs", ()) or ()):
                    row_diagnostics.append("warning:inlet_recommendation_boundary_edges_missing")
                hint_rows.append(
                    IntersectionDrainageHintRow(
                        hint_id=f"intersection-drainage-hint:{_id_token(surface_zones.intersection_id)}:inlet-{len(hint_rows) + 1:02d}",
                        intersection_id=surface_zones.intersection_id,
                        hint_kind="inlet_recommendation",
                        zone_ref=str(getattr(zone, "zone_id", "") or ""),
                        zone_role=design_role or str(getattr(zone, "zone_role", "") or ""),
                        surface_role=str(getattr(zone, "surface_role", "") or ""),
                        recommended_element_kind="inlet",
                        drainage_policy_ref=drainage_policy_ref,
                        control_area_refs=tuple(getattr(zone, "control_area_refs", ()) or ()),
                        source_edge_refs=tuple(getattr(zone, "source_edge_refs", ()) or ()),
                        boundary_edge_refs=tuple(getattr(zone, "boundary_edge_refs", ()) or ()),
                        station_ranges=_station_ranges_for_refs(control_ranges, getattr(zone, "control_area_refs", ()) or ()),
                        status="warning" if row_diagnostics else "ready",
                        diagnostic_rows=tuple(row_diagnostics),
                        notes="Recommended inlet review near curb-return/slope-zone transition; create Drainage Elements explicitly before build.",
                    )
                )

        if not hint_rows:
            diagnostics.append("warning:intersection_drainage_hint_rows_missing")
        status = _topology_status(diagnostics)
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
                    triangulation_method="pending_daylight_zone",
                    status="ready" if not slope_diagnostics else "warning",
                    diagnostic_rows=tuple(slope_diagnostics),
                    notes="Slope-face zone boundary contract only; no triangulation generated.",
                )
            )
        if not daylight_edges:
            diagnostics.append("warning:surface_zone_daylight_edges_missing")

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
            slope_zone_count=len([row for row in zone_rows if row.zone_family == "slope"]),
            slope_zone_ready_count=len([row for row in zone_rows if row.zone_family == "slope" and row.status == "ready"]),
            slope_zone_warning_count=len([row for row in zone_rows if row.zone_family == "slope" and row.status == "warning"]),
            diagnostic_rows=diagnostics,
            zone_rows=zone_rows,
            source_refs=list(getattr(edge_network, "source_refs", []) or []),
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
                        status="ready" if float(getattr(policy, "radius", 0.0) or 0.0) > 0.0 else "warning",
                        notes="" if float(getattr(policy, "radius", 0.0) or 0.0) > 0.0 else "curb_return_radius_missing",
                    )
                )
                if float(getattr(policy, "radius", 0.0) or 0.0) <= 0.0:
                    diagnostics.append(f"warning:curb_return_radius_missing:{getattr(policy, 'policy_id', '')}")

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
