from pathlib import Path
from types import SimpleNamespace

import FreeCAD as App
import Part

from freecad.Corridor_Road.v1.common.diagnostics import DiagnosticMessage
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_BUILD_PARAMETRIC_OUTPUTS,
    CorridorRoadProject,
    ensure_project_tree,
)
import freecad.Corridor_Road.v1.commands.cmd_build_corridor as build_corridor_command
from freecad.Corridor_Road.v1.models.output.surface_output import (
    decide_intersection_surface_downstream_handoff,
    intersection_surface_replacement_blocker_kind,
)
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
    V1BuildCorridorTaskPanel,
    _hide_applied_section_set_review_shape,
    apply_v1_corridor_model,
    build_document_corridor_model,
    build_document_corridor_surface_model,
    corridor_applied_sections_review_summary,
    corridor_build_guided_review_steps,
    corridor_intersection_patch_prerequisite_result,
    corridor_intersection_patch_prerequisite_summary,
    corridor_build_review_outcome_matrix,
    corridor_region_boundary_rows,
    corridor_surface_transition_boundary_options,
    corridor_surface_transition_rows,
    corridor_build_review_rows,
    corridor_build_review_row_color,
    corridor_centerline_preview_style,
    corridor_drainage_flow_review_rows,
    corridor_drainage_flow_review_summary,
    corridor_intersection_contract_review_rows,
    corridor_intersection_contract_review_summary,
    corridor_intersection_drainage_review_rows,
    corridor_drainage_review_rows,
    corridor_drainage_review_summary,
    corridor_intersection_boundary_segment_result,
    corridor_intersection_patch_boundary_result,
    corridor_intersection_tie_in_edge_result,
    corridor_slope_face_issue_rows,
    document_has_v1_applied_sections,
    focus_adjacent_corridor_slope_face_issue,
    focus_corridor_build_guided_review_step,
    focus_corridor_drainage_flow_review,
    focus_corridor_drainage_review_row,
    focus_corridor_intersection_contract_review_row,
    focus_corridor_region_boundary_row,
    focus_corridor_slope_face_issue,
    preferred_corridor_build_review_row_index,
    set_all_corridor_build_preview_visibility,
    set_corridor_build_daylight_contact_marker_visibility,
    set_corridor_build_preview_visibility,
    show_corridor_build_review_object,
    show_corridor_slope_face_issue_marker,
    create_corridor_intersection_surface_preview,
    create_corridor_region_surface_previews,
    create_or_update_corridor_surface_transition_for_boundary,
    create_corridor_surface_transition_from_region_boundary,
    toggle_corridor_surface_transition_enabled,
    update_corridor_surface_transition_station_range,
)
from freecad.Corridor_Road.v1.models.result.tin_surface import TINSurface, TINTriangle, TINVertex
from freecad.Corridor_Road.v1.models.result.intersection_boundary_segment import IntersectionBoundarySegmentResult, IntersectionBoundarySegmentRow
from freecad.Corridor_Road.v1.services.mapping.tin_mesh_preview_mapper import tin_mesh_preview_style
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionSubassemblyRow,
    AppliedSectionFrame,
    AppliedSectionPoint,
    AppliedSectionSubassemblyLink,
    AppliedSectionSubassemblyPoint,
    AppliedSectionSubassemblyShape,
)
from freecad.Corridor_Road.v1.objects.obj_applied_section import create_or_update_v1_applied_section_set_object
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_corridor import find_v1_corridor_model
from freecad.Corridor_Road.v1.objects.obj_drainage import create_or_update_v1_drainage_model_object
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile
from freecad.Corridor_Road.v1.objects.obj_region import create_or_update_v1_region_model_object
from freecad.Corridor_Road.v1.objects.obj_intersection import create_or_update_v1_intersection_model_object
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing
from freecad.Corridor_Road.v1.objects.obj_structure import create_or_update_v1_structure_model_object
from freecad.Corridor_Road.v1.objects.obj_surface import find_v1_surface_model
from freecad.Corridor_Road.v1.objects.obj_surface_transition import (
    create_or_update_v1_surface_transition_model_object,
    find_v1_surface_transition_model,
    to_surface_transition_model,
)


from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.models.source.intersection_model import (
    IntersectionAnchorRow,
    IntersectionArmPolicyRow,
    IntersectionControlArea,
    IntersectionCornerRow,
    IntersectionCurbReturnPolicyRow,
    IntersectionDrainagePolicyRow,
    IntersectionEdgePolicyRow,
    IntersectionGradingPolicyRow,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
)
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageElementRow, DrainageFlowRoute, DrainageModel
from freecad.Corridor_Road.v1.models.source.structure_model import (
    StructureConnectionPoint,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from freecad.Corridor_Road.v1.models.source.surface_transition_model import SurfaceTransitionModel, SurfaceTransitionRange
from freecad.Corridor_Road.v1.services.evaluation.intersection_evaluation_service import IntersectionPatchPrerequisiteResult
from freecad.Corridor_Road.v1.models.result.intersection_patch_boundary import (
    IntersectionPatchBoundaryPointRow,
    IntersectionPatchBoundaryResult,
)
from freecad.Corridor_Road.v1.models.result.intersection_slope_face_loop import (
    IntersectionSlopeFaceLoopResult,
    IntersectionSlopeFaceLoopRow,
)
from freecad.Corridor_Road.v1.models.result.intersection_slope_face_boundary import (
    IntersectionSlopeFaceBoundaryResult,
    IntersectionSlopeFaceBoundaryRow,
)
from dataclasses import replace

_QAPP = None


def test_intersection_surface_downstream_handoff_decision_contract() -> None:
    review_only = decide_intersection_surface_downstream_handoff(
        gate_status="review_required",
        patch_ref="V1CorridorIntersectionSurfacePreview",
        zone_surface_ref="V1CorridorIntersectionSurfaceZoneSurfacePreview",
    )

    assert review_only.readiness == "review_only"
    assert review_only.selected_ref == "V1CorridorIntersectionSurfacePreview"
    assert review_only.selected_role == "transitional_patch_fallback"
    assert review_only.selection_reason == "replacement_gate_review_only"
    assert review_only.patch_selected is True
    assert review_only.zone_selected is False
    assert review_only.patch_handoff_preference == "fallback_review_required"
    assert review_only.zone_handoff_preference == "preferred_candidate_review_only"

    ready = decide_intersection_surface_downstream_handoff(
        gate_status="ready_to_replace",
        patch_ref="V1CorridorIntersectionSurfacePreview",
        zone_surface_ref="V1CorridorIntersectionSurfaceZoneSurfacePreview",
    )

    assert ready.readiness == "ready_to_replace"
    assert ready.selected_ref == "V1CorridorIntersectionSurfaceZoneSurfacePreview"
    assert ready.selected_role == "accepted_zone_surface"
    assert ready.selection_reason == "replacement_gate_ready_to_replace"
    assert ready.patch_selected is False
    assert ready.zone_selected is True
    assert ready.patch_handoff_preference == "fallback_until_replaced"
    assert ready.zone_handoff_preference == "preferred_ready_to_replace"

    blocked = decide_intersection_surface_downstream_handoff(
        gate_status="blocked",
        patch_ref="V1CorridorIntersectionSurfacePreview",
        zone_surface_ref="V1CorridorIntersectionSurfaceZoneSurfacePreview",
    )

    assert blocked.readiness == "blocked"
    assert blocked.selected_ref == "V1CorridorIntersectionSurfacePreview"
    assert blocked.selected_role == "transitional_patch_fallback"
    assert blocked.selection_reason == "replacement_gate_blocked"
    assert blocked.patch_selected is True
    assert blocked.zone_selected is False
    assert intersection_surface_replacement_blocker_kind(review_only.readiness, review_only.selected_role) == "intersection_replacement_gate_review_required"
    assert intersection_surface_replacement_blocker_kind(blocked.readiness, blocked.selected_role) == "intersection_replacement_gate_blocked"
    assert intersection_surface_replacement_blocker_kind(ready.readiness, ready.selected_role) == ""
    assert (
        intersection_surface_replacement_blocker_kind("ready_to_replace", "transitional_patch_fallback")
        == "intersection_replacement_ready_patch_fallback"
    )


def _group_names(group):
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(group, "Group", []) or [])}


def _group_name_list(group):
    return [str(getattr(child, "Name", "") or "") for child in list(getattr(group, "Group", []) or [])]


def _new_project_doc():
    doc = App.newDocument("V1BuildCorridorCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def _sample_sections() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:20", 20.0, "section:20"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
                diagnostic_rows=[
                    DiagnosticMessage(
                        "info",
                        "applied_section_overlap_clip",
                        "left side clipped",
                        "section_id=section:0;previous_section_id=section:-20;side=left;clipped_point_ids=slope:left:daylight;clipped_link_ids=slope:left:link;subassembly_refs=slope:left",
                    ),
                    DiagnosticMessage(
                        "warning",
                        "bench_daylight_fallback",
                        "fixed-width daylight fallback",
                        "subassembly_ref=slope:left;side=left;daylight_mode=terrain;daylight_status=fallback;terrain_hit=false;fallback_reason=no_existing_ground_tin",
                    ),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:20",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=20.0,
                frame=AppliedSectionFrame(station=20.0, x=20.0, y=0.0, z=11.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
        ],
    )


def _sample_sections_with_centerline_curve() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:curved",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:20", 20.0, "section:20"),
            AppliedSectionStationRow("station:40", 40.0, "section:40"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:20",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=20.0,
                frame=AppliedSectionFrame(station=20.0, x=20.0, y=4.0, z=11.0, tangent_direction_deg=10.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:40",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=40.0,
                frame=AppliedSectionFrame(station=40.0, x=40.0, y=0.0, z=12.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
        ],
    )


def _sample_sections_with_ditch_points() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:ditch",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:20", 20.0, "section:20"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("ditch:right-flow", 0.0, -5.2, 9.8, "ditch_surface", -5.2),
                    AppliedSectionPoint("ditch:right-edge", 0.0, -4.0, 10.0, "ditch_surface", -4.0),
                    AppliedSectionPoint("ditch:left-edge", 0.0, 5.0, 10.0, "ditch_surface", 5.0),
                    AppliedSectionPoint("ditch:left-flow", 0.0, 6.2, 9.8, "ditch_surface", 6.2),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:20",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=20.0,
                frame=AppliedSectionFrame(station=20.0, x=20.0, y=0.0, z=11.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("ditch:right-flow", 20.0, -5.2, 10.8, "ditch_surface", -5.2),
                    AppliedSectionPoint("ditch:right-edge", 20.0, -4.0, 11.0, "ditch_surface", -4.0),
                    AppliedSectionPoint("ditch:left-edge", 20.0, 5.0, 11.0, "ditch_surface", 5.0),
                    AppliedSectionPoint("ditch:left-flow", 20.0, 6.2, 10.8, "ditch_surface", 6.2),
                ],
            ),
        ],
    )


def _sample_sections_with_region_boundary() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:regions",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:20", 20.0, "section:20"),
            AppliedSectionStationRow("station:40", 40.0, "section:40"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                assembly_id="assembly:rural",
                region_id="region:rural",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
                point_rows=[
                    AppliedSectionPoint("fg:left", 0.0, 5.0, 10.0, "fg_surface", 5.0),
                    AppliedSectionPoint("fg:right", 0.0, -4.0, 10.0, "fg_surface", -4.0),
                    AppliedSectionPoint("ditch:right", 0.0, -5.5, 9.7, "ditch_surface", -5.5),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:20",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                assembly_id="assembly:rural",
                region_id="region:rural",
                station=20.0,
                frame=AppliedSectionFrame(station=20.0, x=20.0, y=0.0, z=11.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
                point_rows=[
                    AppliedSectionPoint("fg:left", 20.0, 5.0, 11.0, "fg_surface", 5.0),
                    AppliedSectionPoint("fg:right", 20.0, -4.0, 11.0, "fg_surface", -4.0),
                    AppliedSectionPoint("ditch:right", 20.0, -5.5, 10.7, "ditch_surface", -5.5),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:40",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                assembly_id="assembly:urban",
                region_id="region:urban",
                station=40.0,
                frame=AppliedSectionFrame(station=40.0, x=40.0, y=0.0, z=12.0, tangent_direction_deg=0.0),
                surface_left_width=7.0,
                surface_right_width=6.5,
                subgrade_depth=0.45,
                daylight_left_width=1.0,
                daylight_right_width=1.0,
                daylight_left_slope=-0.2,
                daylight_right_slope=-0.2,
                active_structure_ids=["structure:wall-01"],
                point_rows=[
                    AppliedSectionPoint("fg:left", 40.0, 7.0, 12.0, "fg_surface", 7.0),
                    AppliedSectionPoint("fg:right", 40.0, -6.5, 12.0, "fg_surface", -6.5),
                ],
            ),
        ],
    )


def _sample_region_model_with_source_ranges() -> RegionModel:
    return RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:test",
        alignment_id="alignment:main",
        region_rows=[
            RegionRow("region:rural", station_start=0.0, station_end=25.0, region_index=1, assembly_ref="assembly:rural"),
            RegionRow("region:urban", station_start=25.0, station_end=45.0, region_index=2, assembly_ref="assembly:urban"),
        ],
    )


def _sample_intersection_region_model(alignment_id: str, region_id: str) -> RegionModel:
    return RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id=f"regions:{alignment_id.split(':')[-1]}",
        alignment_id=alignment_id,
        region_rows=[
            RegionRow(
                region_id,
                station_start=0.0,
                station_end=20.0,
                region_index=1,
                assembly_ref="assembly:intersection-road",
                intersection_ref="intersection:t-01",
            )
        ],
    )


def _sample_intersection_applied_sections() -> AppliedSectionSet:
    primary_section = AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id="section:primary-10",
        corridor_id="corridor:main",
        alignment_id="alignment:primary",
        assembly_id="assembly:intersection-road",
        region_id="region:primary-intersection",
        station=10.0,
        active_superelevation_id="superelevation:main",
        superelevation_left_crossfall=-2.0,
        superelevation_right_crossfall=4.0,
        active_superelevation_transition_id="transition:primary-runoff",
        active_intersection_id="intersection:t-01",
        active_intersection_control_area_id="control-area:t-01:primary",
        active_intersection_leg_id="leg:primary",
        active_intersection_leg_role="primary_through",
        active_intersection_control_region_refs=["region:primary-intersection", "region:side-intersection"],
        point_rows=[
            AppliedSectionPoint("fg:left", 10.0, 5.0, 10.0, "fg_surface", 5.0),
            AppliedSectionPoint("fg:right", 10.0, -5.0, 10.0, "fg_surface", -5.0),
        ],
    )
    side_section = AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id="section:side-10",
        corridor_id="corridor:main",
        alignment_id="alignment:side",
        assembly_id="assembly:intersection-road",
        region_id="region:side-intersection",
        station=10.0,
        active_superelevation_id="superelevation:main",
        superelevation_left_crossfall=-3.0,
        superelevation_right_crossfall=3.0,
        active_superelevation_transition_id="transition:side-runoff",
        active_intersection_id="intersection:t-01",
        active_intersection_control_area_id="control-area:t-01:side",
        active_intersection_leg_id="leg:side",
        active_intersection_leg_role="side_road",
        active_intersection_control_region_refs=["region:primary-intersection", "region:side-intersection"],
        point_rows=[
            AppliedSectionPoint("fg:left", 10.0, 4.0, 12.0, "fg_surface", 4.0),
            AppliedSectionPoint("fg:right", 10.0, -4.0, 12.0, "fg_surface", -4.0),
        ],
    )
    primary_supplemental = replace(
        primary_section,
        applied_section_id="section:primary-4",
        station=4.0,
        point_rows=[
            AppliedSectionPoint("fg:left", 4.0, 5.0, 10.0, "fg_surface", 5.0),
            AppliedSectionPoint("fg:right", 4.0, -5.0, 10.0, "fg_surface", -5.0),
        ],
    )
    side_supplemental = replace(
        side_section,
        applied_section_id="section:side-4",
        station=4.0,
        point_rows=[
            AppliedSectionPoint("fg:left", 4.0, 4.0, 12.0, "fg_surface", 4.0),
            AppliedSectionPoint("fg:right", 4.0, -4.0, 12.0, "fg_surface", -4.0),
        ],
    )
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:intersection",
        corridor_id="corridor:main",
        alignment_id="alignment:primary",
        station_rows=[
            AppliedSectionStationRow("station:primary-10", 10.0, "section:primary-10"),
            AppliedSectionStationRow("station:side-10", 10.0, "section:side-10"),
            AppliedSectionStationRow("station:primary-4", 4.0, "section:primary-4", kind="intersection_supplemental"),
            AppliedSectionStationRow("station:side-4", 4.0, "section:side-4", kind="intersection_supplemental"),
        ],
        sections=[
            primary_supplemental,
            primary_section,
            side_supplemental,
            side_section,
        ],
    )


def _sample_intersection_applied_sections_with_tie_in_span() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:intersection-long",
        corridor_id="corridor:main",
        alignment_id="alignment:primary",
        station_rows=[
            AppliedSectionStationRow("station:primary-96", 96.0, "section:primary-96"),
            AppliedSectionStationRow("station:primary-144", 144.0, "section:primary-144"),
            AppliedSectionStationRow("station:side-96", 96.0, "section:side-96"),
            AppliedSectionStationRow("station:side-144", 144.0, "section:side-144"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:primary-96",
                corridor_id="corridor:main",
                alignment_id="alignment:primary",
                assembly_id="assembly:intersection-road",
                region_id="region:primary-intersection",
                station=96.0,
                active_superelevation_id="superelevation:main",
                superelevation_left_crossfall=-2.0,
                superelevation_right_crossfall=4.0,
                active_superelevation_transition_id="transition:primary-runoff",
                active_intersection_id="intersection:t-01",
                active_intersection_control_area_id="control-area:t-01:primary",
                active_intersection_leg_id="leg:primary",
                active_intersection_leg_role="primary_through",
                active_intersection_control_region_refs=["region:primary-intersection", "region:side-intersection"],
                point_rows=[
                    AppliedSectionPoint("fg:left", 96.0, 5.0, 10.0, "fg_surface", 5.0),
                    AppliedSectionPoint("fg:right", 96.0, -5.0, 10.0, "fg_surface", -5.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:primary-144",
                corridor_id="corridor:main",
                alignment_id="alignment:primary",
                assembly_id="assembly:intersection-road",
                region_id="region:primary-intersection",
                station=144.0,
                active_superelevation_id="superelevation:main",
                superelevation_left_crossfall=-2.0,
                superelevation_right_crossfall=4.0,
                active_superelevation_transition_id="transition:primary-runoff",
                active_intersection_id="intersection:t-01",
                active_intersection_control_area_id="control-area:t-01:primary",
                active_intersection_leg_id="leg:primary",
                active_intersection_leg_role="primary_through",
                active_intersection_control_region_refs=["region:primary-intersection", "region:side-intersection"],
                point_rows=[
                    AppliedSectionPoint("fg:left", 144.0, 5.0, 10.0, "fg_surface", 5.0),
                    AppliedSectionPoint("fg:right", 144.0, -5.0, 10.0, "fg_surface", -5.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-96",
                corridor_id="corridor:main",
                alignment_id="alignment:side",
                assembly_id="assembly:intersection-road",
                region_id="region:side-intersection",
                station=96.0,
                active_superelevation_id="superelevation:main",
                superelevation_left_crossfall=-3.0,
                superelevation_right_crossfall=3.0,
                active_superelevation_transition_id="transition:side-runoff",
                active_intersection_id="intersection:t-01",
                active_intersection_control_area_id="control-area:t-01:side",
                active_intersection_leg_id="leg:side",
                active_intersection_leg_role="side_road",
                active_intersection_control_region_refs=["region:primary-intersection", "region:side-intersection"],
                point_rows=[
                    AppliedSectionPoint("fg:left", 116.0, -24.0, 12.0, "fg_surface", 4.0),
                    AppliedSectionPoint("fg:right", 124.0, -24.0, 12.0, "fg_surface", -4.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-144",
                corridor_id="corridor:main",
                alignment_id="alignment:side",
                assembly_id="assembly:intersection-road",
                region_id="region:side-intersection",
                station=144.0,
                active_superelevation_id="superelevation:main",
                superelevation_left_crossfall=-3.0,
                superelevation_right_crossfall=3.0,
                active_superelevation_transition_id="transition:side-runoff",
                active_intersection_id="intersection:t-01",
                active_intersection_control_area_id="control-area:t-01:side",
                active_intersection_leg_id="leg:side",
                active_intersection_leg_role="side_road",
                active_intersection_control_region_refs=["region:primary-intersection", "region:side-intersection"],
                point_rows=[
                    AppliedSectionPoint("fg:left", 116.0, 24.0, 12.0, "fg_surface", 4.0),
                    AppliedSectionPoint("fg:right", 124.0, 24.0, 12.0, "fg_surface", -4.0),
                ],
            ),
        ],
    )


def _sample_intersection_model() -> IntersectionModel:
    return IntersectionModel(
        schema_version=1,
        project_id="proj-1",
        intersection_model_id="intersections:test",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:t-01",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:primary",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=["region:primary-intersection", "region:side-intersection"],
                grading_policy_ref="grading:intersection:t-01:default",
                policy_refs=[
                    "arm-policy:intersection:t-01:primary",
                    "arm-policy:intersection:t-01:side",
                    "edge-policy:intersection:t-01:primary:pavement",
                    "edge-policy:intersection:t-01:primary:daylight",
                    "edge-policy:intersection:t-01:side:pavement",
                    "edge-policy:intersection:t-01:side:daylight",
                    "curb-return:intersection:t-01:default",
                    "grading:intersection:t-01:default",
                    "drainage:intersection:t-01:default",
                ],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="leg:primary",
                        intersection_id="intersection:t-01",
                        leg_role="primary_through",
                        alignment_ref="alignment:primary",
                        profile_ref="profile:primary",
                        centerline3d_ref="centerline3d:primary",
                        region_ref="region:primary-intersection",
                        approach_station_start=0.0,
                        approach_station_end=20.0,
                        arm_policy_ref="arm-policy:intersection:t-01:primary",
                        edge_policy_refs=[
                            "edge-policy:intersection:t-01:primary:pavement",
                            "edge-policy:intersection:t-01:primary:daylight",
                        ],
                        grading_policy_ref="grading:intersection:t-01:default",
                    ),
                    IntersectionLegRow(
                        leg_id="leg:side",
                        intersection_id="intersection:t-01",
                        leg_role="side_road",
                        alignment_ref="alignment:side",
                        profile_ref="profile:side",
                        centerline3d_ref="centerline3d:side",
                        region_ref="region:side-intersection",
                        approach_station_start=0.0,
                        approach_station_end=20.0,
                        arm_policy_ref="arm-policy:intersection:t-01:side",
                        edge_policy_refs=[
                            "edge-policy:intersection:t-01:side:pavement",
                            "edge-policy:intersection:t-01:side:daylight",
                        ],
                        grading_policy_ref="grading:intersection:t-01:default",
                    ),
                ],
            )
        ],
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:intersection:t-01:main",
                intersection_id="intersection:t-01",
                source_method="manual",
                approval_status="locked",
                primary_alignment_ref="alignment:primary",
                primary_station=10.0,
                secondary_station_refs={"alignment:side": 10.0},
                tolerance=0.05,
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="control-area:t-01:primary",
                intersection_id="intersection:t-01",
                alignment_ref="alignment:primary",
                station_ranges=[(0.0, 20.0)],
                control_region_refs=["region:primary-intersection"],
                grading_policy_ref="grading:intersection:t-01:default",
            ),
            IntersectionControlArea(
                control_area_id="control-area:t-01:side",
                intersection_id="intersection:t-01",
                alignment_ref="alignment:side",
                station_ranges=[(0.0, 20.0)],
                control_region_refs=["region:side-intersection"],
                grading_policy_ref="grading:intersection:t-01:default",
            ),
        ],
        corner_rows=[
            IntersectionCornerRow(
                corner_id="corner:intersection:t-01:left",
                intersection_id="intersection:t-01",
                control_area_ref="control-area:t-01:primary",
                from_leg_ref="leg:primary",
                to_leg_ref="leg:side",
                side="left",
                quadrant="left",
                curb_return_policy_ref="curb-return:intersection:t-01:default",
                approval_status="locked",
            ),
            IntersectionCornerRow(
                corner_id="corner:intersection:t-01:right",
                intersection_id="intersection:t-01",
                control_area_ref="control-area:t-01:side",
                from_leg_ref="leg:side",
                to_leg_ref="leg:primary",
                side="right",
                quadrant="right",
                curb_return_policy_ref="curb-return:intersection:t-01:default",
                approval_status="locked",
            ),
        ],
        arm_policy_rows=[
            IntersectionArmPolicyRow("arm-policy:intersection:t-01:primary", "intersection:t-01", "leg:primary"),
            IntersectionArmPolicyRow("arm-policy:intersection:t-01:side", "intersection:t-01", "leg:side"),
        ],
        curb_return_policy_rows=[
            IntersectionCurbReturnPolicyRow(
                policy_id="curb-return:intersection:t-01:default",
                intersection_id="intersection:t-01",
                radius=12.0,
                approach_leg_refs=["leg:primary", "leg:side"],
                corner_refs=["corner:intersection:t-01:left", "corner:intersection:t-01:right"],
            )
        ],
        edge_policy_rows=[
            IntersectionEdgePolicyRow(
                "edge-policy:intersection:t-01:primary:pavement",
                "intersection:t-01",
                "leg:primary",
                edge_family_intent="lane",
                source_method="subassembly_derived",
                approval_status="locked",
                subassembly_kind="lane",
            ),
            IntersectionEdgePolicyRow(
                "edge-policy:intersection:t-01:primary:daylight",
                "intersection:t-01",
                "leg:primary",
                edge_role="daylight_hinge",
                edge_family_intent="side_slope",
                source_method="subassembly_derived",
                approval_status="locked",
                subassembly_kind="side_slope",
            ),
            IntersectionEdgePolicyRow(
                "edge-policy:intersection:t-01:side:pavement",
                "intersection:t-01",
                "leg:side",
                edge_family_intent="lane",
                source_method="subassembly_derived",
                approval_status="locked",
                subassembly_kind="lane",
            ),
            IntersectionEdgePolicyRow(
                "edge-policy:intersection:t-01:side:daylight",
                "intersection:t-01",
                "leg:side",
                edge_role="daylight_hinge",
                edge_family_intent="side_slope",
                source_method="subassembly_derived",
                approval_status="locked",
                subassembly_kind="side_slope",
            ),
        ],
        grading_policy_rows=[
            IntersectionGradingPolicyRow(
                policy_id="grading:intersection:t-01:default",
                intersection_id="intersection:t-01",
                mode="flatten_intersection",
                target_crossfall_percent=0.0,
                primary_alignment_ref="alignment:primary",
                secondary_alignment_refs=["alignment:side"],
            )
        ],
        drainage_policy_rows=[
            IntersectionDrainagePolicyRow(
                "drainage:intersection:t-01:default",
                "intersection:t-01",
                drainage_element_refs=["drainage:inlet-main"],
                flow_route_refs=["flow-route:main"],
                inlet_candidate_refs=["inlet-candidate:main"],
                low_point_refs=["low-point:central"],
                intent_status="accepted",
                approval_status="locked",
            ),
        ],
    )


def test_build_document_corridor_model_uses_applied_sections() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())

        result = build_document_corridor_model(doc, project=project)

        assert document_has_v1_applied_sections(doc) is True
        assert result.corridor_id == "corridor:main"
        assert result.applied_section_set_ref == "sections:main"
        assert [row.station for row in result.station_rows] == [0.0, 20.0]
    finally:
        App.closeDocument(doc.Name)


def test_build_document_corridor_surface_model_uses_corridor_and_applied_sections() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())
        corridor = build_document_corridor_model(doc, project=project)

        result = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor)

        assert result.corridor_id == "corridor:main"
        assert result.surface_model_id == "surface:main"
        assert [row.surface_kind for row in result.surface_rows] == [
            "design_surface",
            "subgrade_surface",
            "daylight_surface",
        ]
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_corridor_model_creates_result_object() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())
        progress_events = []

        obj = apply_v1_corridor_model(
            document=doc,
            project=project,
            progress_callback=lambda value, text: progress_events.append((value, text)),
        )

        assert obj == find_v1_corridor_model(doc)
        assert obj.V1ObjectType == "V1CorridorModel"
        assert obj.StationCount == 2
        assert list(obj.SurfaceBuildRefs) == ["surface:main"]
        surface_obj = find_v1_surface_model(doc)
        assert surface_obj is not None
        assert surface_obj.V1ObjectType == "V1SurfaceModel"
        assert surface_obj.SurfaceCount == 3
        preview = doc.getObject("V1CorridorDesignSurfacePreview")
        assert preview is not None
        assert preview.CRRecordKind == "v1_corridor_surface_preview"
        assert preview.SurfaceRole == "design"
        assert preview.SurfaceKind == "design_surface"
        assert preview.SurfaceModelId == "surface:main"
        assert preview.AppliedSectionSetRef == "sections:main"
        assert preview.PreviewStatus == "ready"
        assert int(preview.PreviewFacetCount) == 8
        assert "surface:main" in list(preview.SourceRefs)
        assert "sections:main" in list(preview.SourceRefs)
        assert int(preview.VertexCount) == 10
        assert int(preview.TriangleCount) == 8
        centerline = doc.getObject("V1CorridorCenterline3DPreview")
        assert centerline is None
        subgrade_preview = doc.getObject("V1CorridorSubgradeSurfacePreview")
        assert subgrade_preview is not None
        assert subgrade_preview.CRRecordKind == "v1_corridor_surface_preview"
        assert subgrade_preview.SurfaceRole == "subgrade"
        assert subgrade_preview.SurfaceKind == "subgrade_surface"
        assert subgrade_preview.PreviewStatus == "ready"
        assert subgrade_preview.AppliedSectionSetRef == "sections:main"
        assert int(subgrade_preview.VertexCount) == 10
        assert int(subgrade_preview.TriangleCount) == 8
        daylight_preview = doc.getObject("V1CorridorDaylightSurfacePreview")
        assert daylight_preview is not None
        assert daylight_preview.CRRecordKind == "v1_corridor_surface_preview"
        assert daylight_preview.SurfaceRole == "daylight"
        assert daylight_preview.SurfaceKind == "daylight_surface"
        assert daylight_preview.PreviewStatus == "ready"
        assert daylight_preview.AppliedSectionSetRef == "sections:main"
        assert int(daylight_preview.VertexCount) == 20
        assert int(daylight_preview.TriangleCount) == 16
        assert int(daylight_preview.EGIntersectionCount) == 0
        assert int(daylight_preview.EGTieInHitCount) == 0
        assert int(daylight_preview.SlopeFaceFallbackCount) == 10
        assert int(daylight_preview.SlopeFaceNoExistingGroundCount) == 10
        assert int(daylight_preview.SlopeFaceNoEGHitCount) == 0
        assert "fallbacks: 10" in daylight_preview.SlopeFaceDiagnosticSummary
        assert "no EG TIN: 10" in daylight_preview.SlopeFaceDiagnosticSummary
        assert "STA 0.000 L no EG TIN" in daylight_preview.SlopeFaceIssueStations
        assert "STA 20.000 R no EG TIN" in daylight_preview.SlopeFaceIssueStations
        assert len(list(daylight_preview.SlopeFaceIssueRows)) == 10
        issue_rows = corridor_slope_face_issue_rows(doc)
        assert issue_rows[0]["station_label"] == "STA 0.000"
        assert issue_rows[0]["side"] == "L"
        assert issue_rows[0]["reason"] == "no EG TIN"
        assert issue_rows[0]["marker_object"] == "ReviewIssueSlopeFaceIssue001L"
        assert issue_rows[-1]["station_label"] == "row 5"
        assert issue_rows[-1]["side"] == "R"
        fallback_markers = doc.getObject("ReviewIssueSlopeFaceFallbackMarkers")
        assert fallback_markers is not None
        assert fallback_markers.V1ObjectType == "ReviewIssue"
        assert fallback_markers.IssueKind == "slope_face_tie_in"
        assert int(fallback_markers.MarkerCount) == 10
        first_issue_marker = doc.getObject("ReviewIssueSlopeFaceIssue001L")
        assert first_issue_marker is not None
        assert first_issue_marker.V1ObjectType == "ReviewIssue"
        assert first_issue_marker.IssueStation == "STA 0.000"
        assert first_issue_marker.IssueSide == "L"
        assert first_issue_marker.IssueReason == "no EG TIN"
        assert int(first_issue_marker.MarkerCount) == 1
        shown_marker = show_corridor_slope_face_issue_marker(doc, 0)
        assert shown_marker.Name == "ReviewIssueSlopeFaceIssue001L"
        build_outputs = ensure_project_tree(project, include_references=False)[V1_TREE_BUILD_PARAMETRIC_OUTPUTS]
        build_output_names = _group_names(build_outputs)
        assert preview.Name in build_output_names
        assert subgrade_preview.Name in build_output_names
        assert daylight_preview.Name in build_output_names
        assert fallback_markers.Name in build_output_names
        assert first_issue_marker.Name in build_output_names
        assert progress_events[0] == (40, "Preparing project tree...")
        assert any(text == "Building corridor surfaces..." for _value, text in progress_events)
        assert progress_events[-1] == (94, "Recomputing document...")
    finally:
        App.closeDocument(doc.Name)


def test_corridor_surface_preview_contract_exposes_applied_section_diagnostics() -> None:
    doc, project = _new_project_doc()
    try:
        obj = doc.addObject("Part::Feature", "DiagnosticPreview")

        class _Corridor:
            corridor_id = "corridor:main"

        class _SurfaceModel:
            surface_model_id = "surface:main"

        class _PreviewResult:
            notes = "diagnostic preview"
            facet_count = 0

        build_corridor_command._attach_corridor_surface_preview_contract(
            obj,
            role="daylight",
            surface_kind="daylight_surface",
            surface_id="surface:daylight",
            corridor_model=_Corridor(),
            surface_model=_SurfaceModel(),
            applied_section_set=_sample_sections(),
            preview_result=_PreviewResult(),
        )

        assert int(obj.AppliedSectionDiagnosticCount) == 2
        assert int(obj.AppliedSectionOverlapClipCount) == 1
        assert int(obj.AppliedSectionDaylightFallbackCount) == 1
        assert "overlap_clip=1" in obj.AppliedSectionDiagnosticSummary
        assert "daylight_fallback=1" in obj.AppliedSectionDiagnosticSummary
        assert any("clipped_point_ids=slope:left:daylight" in row for row in list(obj.AppliedSectionDiagnosticRows))
        assert "clip_rows=1" in obj.AppliedSectionClipReviewSummary
        assert "subassemblies=slope:left" in obj.AppliedSectionClipReviewSummary
        assert list(obj.AppliedSectionClipReviewRows) == [
            "STA 0.000;section=section:0;previous=section:-20;side=left;subassemblies=slope:left;points=slope:left:daylight;links=slope:left:link"
        ]
        review_row = build_corridor_command._corridor_build_review_row(
            "daylight",
            "Slope Face Surface",
            "DiagnosticPreview",
            obj,
        )
        assert "applied sections: diagnostics=2" in review_row["notes"]
        assert "daylight_fallback=1" in review_row["notes"]
        assert "clipping: clip_rows=1" in review_row["notes"]
        assert "points=slope:left:daylight" in review_row["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_corridor_region_boundary_rows_report_region_ranges_and_diagnostics() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())

        rows = corridor_region_boundary_rows(doc)

        assert [row["region_id"] for row in rows] == ["region:rural", "region:urban"]
        assert rows[0]["station_start"] == 0.0
        assert rows[0]["station_end"] == 20.0
        assert rows[1]["station_start"] == 40.0
        assert rows[0]["assembly"] == "assembly:rural"
        assert rows[1]["assembly"] == "assembly:urban"
        assert rows[1]["structure"] == "structure:wall-01"
        assert rows[0]["boundary_status"] == "warn"
        assert "width" in rows[0]["diagnostics"]
        assert int(rows[0]["diagnostic_count"]) >= 3
    finally:
        App.closeDocument(doc.Name)


def test_corridor_region_boundary_rows_use_source_region_ranges_when_available() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_region_model_object(doc, project=project, region_model=_sample_region_model_with_source_ranges())
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())

        rows = corridor_region_boundary_rows(doc)
        options = corridor_surface_transition_boundary_options(doc, region_id="region:rural")

        assert [row["region_id"] for row in rows] == ["region:rural", "region:urban"]
        assert rows[0]["station_start"] == 0.0
        assert rows[0]["station_end"] == 25.0
        assert rows[1]["station_start"] == 25.0
        assert rows[1]["station_end"] == 45.0
        assert "20.000->25.000" in rows[0]["diagnostics"]
        assert "40.000->45.000" in rows[1]["diagnostics"]
        assert "STA 25.000" in [options[index]["label"].split(" | ")[0] for index in range(len(options))]

        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)
        create_corridor_region_surface_previews(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        urban = doc.getObject("V1CorridorRegionSurface_region_urban")
        assert urban is not None
        assert abs(float(urban.StationStart) - 25.0) < 1.0e-9
        assert abs(float(urban.StationEnd) - 45.0) < 1.0e-9
        assert int(urban.SectionCount) >= 3
        assert int(urban.SurfaceFaceCount) > 0
    finally:
        App.closeDocument(doc.Name)


def test_corridor_region_boundary_rows_use_station_context_resolver_for_domain_sources() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_region_model_object(doc, project=project, region_model=_sample_region_model_with_source_ranges())
        create_or_update_v1_structure_model_object(
            doc,
            project=project,
            structure_model=StructureModel(
                schema_version=1,
                project_id="proj-1",
                structure_model_id="structures:test",
                structure_rows=[
                    StructureRow(
                        structure_id="structure:culvert-01",
                        structure_kind="culvert",
                        structure_role="crossing",
                        placement=StructurePlacement(
                            placement_id="placement:culvert-01",
                            alignment_id="alignment:main",
                            station_start=25.0,
                            station_end=45.0,
                            region_ref="region:urban",
                        ),
                    )
                ],
            ),
        )
        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-1",
                drainage_model_id="drainage:test",
                element_rows=[
                    DrainageElementRow(
                        drainage_element_id="drainage:urban-left",
                        element_kind="ditch",
                        side="left",
                        region_ref="region:urban",
                        station_start=25.0,
                        station_end=45.0,
                    )
                ],
                flow_route_rows=[
                    DrainageFlowRoute(
                        flow_route_id="flow-route:urban-left",
                        from_element_ref="drainage:urban-left",
                        outlet_ref="drainage:outlet-main",
                    )
                ],
            ),
        )
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())

        rows = corridor_region_boundary_rows(doc)

        assert "structure:culvert-01" in rows[1]["structure"]
        assert "drainage:urban-left" in rows[1]["drainage"]
        assert "flow-route:urban-left" in rows[1]["drainage"]
    finally:
        App.closeDocument(doc.Name)


def test_corridor_intersection_patch_prerequisites_report_ready_context() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:primary", "region:primary-intersection"),
            object_name="V1RegionModelPrimary",
        )
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:side", "region:side-intersection"),
            object_name="V1RegionModelSide",
        )
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=_sample_intersection_model(),
        )
        create_or_update_v1_applied_section_set_object(
            doc,
            project=project,
            applied_section_set=_sample_intersection_applied_sections(),
        )

        result = corridor_intersection_patch_prerequisite_result(doc)
        summary = corridor_intersection_patch_prerequisite_summary(doc)
        steps = corridor_build_guided_review_steps(doc)
        intersection_step = [row for row in steps if row["step_id"] == "intersections"][0]

        assert result.status == "ready"
        assert result.intersection_id == "intersection:t-01"
        assert result.participating_alignment_count == 2
        assert result.control_region_count == 2
        assert result.applied_section_count == 4
        assert result.tie_in_edge_count == 4
        assert result.diagnostic_rows == ()
        assert summary["status"] == "ready"
        assert "patch prerequisites ready" in summary["notes"]
        assert "tie-in edges=4" in summary["notes"]
        assert "intersection supplemental sections=2" in summary["notes"]
        assert "alignment:primary=1" in summary["notes"]
        assert "alignment:side=1" in summary["notes"]
        assert intersection_step["status"] == "ready"
        assert "alignments=2" in intersection_step["notes"]
        assert "tie-in edges=4" in intersection_step["notes"]
        assert "intersection supplemental sections=2" in intersection_step["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_corridor_guided_review_reports_intersection_exclusion_clip_counts() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:primary", "region:primary-intersection"),
            object_name="V1RegionModelPrimary",
        )
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:side", "region:side-intersection"),
            object_name="V1RegionModelSide",
        )
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=_sample_intersection_model(),
        )
        create_or_update_v1_applied_section_set_object(
            doc,
            project=project,
            applied_section_set=_sample_intersection_applied_sections(),
        )
        design = doc.addObject("Part::Feature", "V1CorridorDesignSurfacePreview")
        daylight = doc.addObject("Part::Feature", "V1CorridorDaylightSurfacePreview")
        build_corridor_command._set_preview_property(design, "IntersectionExclusionClipStatus", "ready")
        build_corridor_command._set_preview_integer_property(design, "IntersectionExclusionClippedTriangleCount", 3)
        build_corridor_command._set_preview_integer_property(design, "IntersectionExclusionKeptTriangleCount", 7)
        build_corridor_command._set_preview_integer_property(design, "IntersectionExclusionExactCutCandidateCount", 1)
        build_corridor_command._set_preview_property(design, "IntersectionExclusionBoundaryStrategy", "structured_strip_curb_return_blend")
        build_corridor_command._set_preview_integer_property(design, "IntersectionExclusionPracticalBoundaryAligned", 1)
        build_corridor_command._set_preview_property(daylight, "IntersectionExclusionClipStatus", "ready")
        build_corridor_command._set_preview_integer_property(daylight, "IntersectionExclusionClippedTriangleCount", 2)
        build_corridor_command._set_preview_integer_property(daylight, "IntersectionExclusionKeptTriangleCount", 9)
        build_corridor_command._set_preview_property(daylight, "IntersectionExclusionBoundaryStrategy", "structured_strip_curb_return_blend")
        build_corridor_command._set_preview_integer_property(daylight, "IntersectionExclusionPracticalBoundaryAligned", 1)

        steps = corridor_build_guided_review_steps(doc)
        intersection_step = [row for row in steps if row["step_id"] == "intersections"][0]

        assert intersection_step["status"] == "ready"
        assert "Design exclusion ready: clipped=3, kept=7, exact-cut candidates=1, boundary=structured_strip_curb_return_blend, aligned=practical" in intersection_step["notes"]
        assert "Slope exclusion ready: clipped=2, kept=9, boundary=structured_strip_curb_return_blend, aligned=practical" in intersection_step["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_corridor_intersection_contract_review_rows_label_missing_source_path() -> None:
    doc, _project = _new_project_doc()
    try:
        rows = corridor_intersection_contract_review_rows(doc)
        summary = corridor_intersection_contract_review_summary(doc)

        assert len(rows) == 1
        assert rows[0]["status"] == "missing"
        assert rows[0]["source_status"] == "missing"
        assert rows[0]["output_path"] == "missing_source"
        assert "IntersectionModel is required" in rows[0]["notes"]
        assert "source status=missing=1" in summary["notes"]
        assert "output paths=missing_source=1" in summary["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_corridor_intersection_contract_review_rows_report_edge_zones_and_clipping() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=_sample_intersection_model(),
        )

        rows = corridor_intersection_contract_review_rows(doc)
        summary = corridor_intersection_contract_review_summary(doc)

        assert summary["status"] == "warning"
        assert summary["row_count"] == 25
        assert summary["source_warning_count"] == 0
        assert "topology=1" in summary["notes"]
        assert "edge_network=6" in summary["notes"]
        assert "surface_zone=7" in summary["notes"]
        assert "slope_face_loop=2" in summary["notes"]
        assert "corridor_clip=4" in summary["notes"]
        assert "drainage_hint=5" in summary["notes"]
        assert "output paths=contract_consumed=25" in summary["notes"]
        assert "source status=accepted=25" in summary["notes"]
        assert "source warnings=0" in summary["notes"]
        assert all(row["output_path"] == "contract_consumed" for row in rows)
        assert rows[0]["contract_family"] == "topology"
        assert rows[0]["status"] == "ready"
        assert rows[0]["source_status"] == "accepted"
        assert "lane connections=0" in rows[0]["notes"]

        edge_rows = [row for row in rows if row["contract_family"] == "edge_network"]
        assert len(edge_rows) == 6
        assert {row["role"] for row in edge_rows} == {"pavement_edge", "daylight_hinge", "curb_return_edge"}
        assert all(row["source_status"] == "accepted" for row in edge_rows)

        zone_rows = [row for row in rows if row["contract_family"] == "surface_zone"]
        assert len(zone_rows) == 7
        assert zone_rows[0]["status"] == "ready"
        assert all(row["source_status"] == "accepted" for row in zone_rows)
        assert "central_pavement" in {row["role"] for row in zone_rows}
        assert "exterior_slope_face" in {row["role"] for row in zone_rows}

        clip_rows = [row for row in rows if row["contract_family"] == "corridor_clip"]
        assert len(clip_rows) == 4
        assert {row["role"] for row in clip_rows} == {"design", "slope_face"}
        assert all(row["source_status"] == "accepted" for row in clip_rows)
        assert "control-area:t-01:primary" in clip_rows[0]["source_refs"]
        assert "intent=intersection_owned" in clip_rows[0]["notes"]
        assert "lineage=result_only" in clip_rows[0]["notes"]
        drainage_hint_rows = [row for row in rows if row["contract_family"] == "drainage_hint"]
        assert len(drainage_hint_rows) == 5
        assert {row["role"] for row in drainage_hint_rows} == {"low_point_candidate", "inlet_recommendation"}
        assert all(row["source_status"] == "accepted" for row in drainage_hint_rows)
        assert all("handoff=accepted_handoff" in row["notes"] for row in drainage_hint_rows)
    finally:
        App.closeDocument(doc.Name)


def test_corridor_intersection_contract_review_rows_expose_source_status_warnings() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=IntersectionModel(
                schema_version=1,
                project_id="proj-1",
                intersection_model_id="intersections:source-status",
                intersection_rows=[
                    IntersectionRow(
                        intersection_id="intersection:source-status",
                        intersection_kind="t_intersection",
                        primary_alignment_ref="alignment:primary",
                        secondary_alignment_refs=["alignment:side"],
                        control_region_refs=["region:primary-intersection"],
                        leg_rows=[
                            IntersectionLegRow(
                                leg_id="leg:primary",
                                intersection_id="intersection:source-status",
                                leg_role="primary_through",
                                alignment_ref="alignment:primary",
                                approach_station_start=0.0,
                                approach_station_end=20.0,
                                edge_policy_refs=["edge-policy:intersection:source-status:missing"],
                            )
                        ],
                    )
                ],
                control_area_rows=[
                    IntersectionControlArea(
                        control_area_id="control-area:source-status:primary",
                        intersection_id="intersection:source-status",
                        alignment_ref="alignment:primary",
                        station_ranges=[(0.0, 20.0)],
                        control_region_refs=["region:primary-intersection"],
                    )
                ],
            ),
        )

        rows = corridor_intersection_contract_review_rows(doc)
        summary = corridor_intersection_contract_review_summary(doc)
        warning_rows = [row for row in rows if row.get("source_status") == "warning"]

        assert summary["status"] == "warning"
        assert summary["source_warning_count"] > 0
        assert "source status=" in summary["notes"]
        assert "warning=" in summary["notes"]
        assert "source warnings=" in summary["notes"]
        assert warning_rows
        assert all(row["output_path"] == "contract_consumed" for row in warning_rows)
        assert any("source_leg_profile_ref_missing" in str(row.get("source_diagnostics", "")) for row in warning_rows)
        assert any("source_edge_policy_ref_unresolved" in str(row.get("source_diagnostics", "")) for row in warning_rows)
    finally:
        App.closeDocument(doc.Name)


def test_corridor_intersection_contract_review_rows_carry_slope_loop_source_lineage_warnings() -> None:
    doc, project = _new_project_doc()
    try:
        model = _sample_intersection_model()
        model.edge_policy_rows[1] = replace(
            model.edge_policy_rows[1],
            source_method="mesh_repaired",
            approval_status="auto_accepted",
        )
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=model,
        )

        rows = corridor_intersection_contract_review_rows(doc)
        summary = corridor_intersection_contract_review_summary(doc)
        slope_loop_warning_rows = [
            row
            for row in rows
            if row.get("contract_family") == "slope_face_loop" and row.get("source_status") == "warning"
        ]

        assert summary["source_warning_count"] > 0
        assert slope_loop_warning_rows
        assert all(row["output_path"] == "contract_consumed" for row in slope_loop_warning_rows)
        assert any("source_lineage=source_warning" in str(row.get("notes", "")) for row in slope_loop_warning_rows)
        assert any("surface_zone_status=warning" in str(row.get("notes", "")) for row in slope_loop_warning_rows)
        assert any("edge_network_status=warning" in str(row.get("notes", "")) for row in slope_loop_warning_rows)
        assert any("surface_zone_source_edge_diagnostic" in str(row.get("source_diagnostics", "")) for row in slope_loop_warning_rows)
    finally:
        App.closeDocument(doc.Name)


def test_focus_corridor_intersection_contract_review_row_creates_contract_highlight() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=_sample_intersection_model(),
        )
        preview = doc.addObject("Part::Feature", "V1IntersectionEdgeNetworkPreview")
        preview.Shape = Part.makeLine(App.Vector(0, 0, 0), App.Vector(10, 0, 0))
        rows = corridor_intersection_contract_review_rows(doc)
        edge_index = next(index for index, row in enumerate(rows) if row["contract_family"] == "edge_network")

        focused = focus_corridor_intersection_contract_review_row(doc, edge_index)

        assert focused.Name == "ReviewIntersectionContractHighlight"
        assert focused.CRRecordKind == "v1_intersection_contract_review_highlight"
        assert focused.ContractFamily == "edge_network"
        assert focused.ContractRowId == rows[edge_index]["row_id"]
        assert focused.HighlightedShapeCount >= 1
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_panel_populates_intersection_contract_table() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=_sample_intersection_model(),
        )

        panel = V1BuildCorridorTaskPanel(document=doc)

        assert panel._intersection_contract_table.rowCount() == 25
        assert panel._intersection_contract_table.columnCount() == 10
        assert panel._intersection_contract_table.item(0, 0).text() == "topology"
        assert panel._intersection_contract_table.item(0, 1).text() == "ready"
        assert panel._intersection_contract_table.item(0, 2).text() == "accepted"
        assert panel._intersection_contract_table.item(0, 3).text() == "contract_consumed"
    finally:
        App.closeDocument(doc.Name)


def test_corridor_guided_review_reports_intersection_patch_boundary_diagnostics() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:primary", "region:primary-intersection"),
            object_name="V1RegionModelPrimary",
        )
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:side", "region:side-intersection"),
            object_name="V1RegionModelSide",
        )
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=_sample_intersection_model(),
        )
        create_or_update_v1_applied_section_set_object(
            doc,
            project=project,
            applied_section_set=_sample_intersection_applied_sections(),
        )
        preview = doc.addObject("Part::Feature", "V1CorridorIntersectionSurfacePreview")
        build_corridor_command._set_preview_integer_property(preview, "IntersectionPatchBoundaryDiagnosticCount", 1)
        build_corridor_command._set_preview_integer_property(preview, "IntersectionPatchBoundaryHoleRingCount", 1)
        build_corridor_command._set_preview_string_list_property(
            preview,
            "IntersectionPatchBoundaryDiagnostics",
            ["intersection_patch_boundary_inner_ring_outside_outer: hole:1 is outside the outer ring."],
        )

        steps = corridor_build_guided_review_steps(doc)
        intersection_step = [row for row in steps if row["step_id"] == "intersections"][0]

        assert intersection_step["status"] == "warning"
        assert intersection_step["focus"] == "Intersection Patch Boundary diagnostics"
        assert intersection_step["output_path"] == "legacy_output"
        assert "patch boundary rings: holes=1, islands=0" in intersection_step["notes"]
        assert "intersection_patch_boundary_inner_ring_outside_outer" in intersection_step["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_corridor_guided_review_reports_intersection_surface_quality_diagnostics() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:primary", "region:primary-intersection"),
            object_name="V1RegionModelPrimary",
        )
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:side", "region:side-intersection"),
            object_name="V1RegionModelSide",
        )
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=_sample_intersection_model(),
        )
        create_or_update_v1_applied_section_set_object(
            doc,
            project=project,
            applied_section_set=_sample_intersection_applied_sections(),
        )
        preview = doc.addObject("Part::Feature", "V1CorridorIntersectionSurfacePreview")
        build_corridor_command._set_preview_property(preview, "PatchTriangulationMode", "fan_fallback")
        build_corridor_command._set_preview_float_property(preview, "PatchBoundaryBBoxAspectRatio", 12.5)
        build_corridor_command._set_preview_float_property(preview, "PatchTriangleMinQuality", 0.02)
        build_corridor_command._set_preview_integer_property(preview, "PatchTriangleSkinnyCount", 3)

        steps = corridor_build_guided_review_steps(doc)
        intersection_step = [row for row in steps if row["step_id"] == "intersections"][0]

        assert intersection_step["status"] == "warning"
        assert intersection_step["focus"] == "Intersection Surface diagnostics"
        assert "warning:patch triangulation=fan_fallback" in intersection_step["notes"]
        assert "warning:patch bbox ratio=12.500" in intersection_step["notes"]
        assert "warning:patch min triangle quality=0.020" in intersection_step["notes"]
        assert "warning:skinny triangles=3" in intersection_step["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_create_corridor_intersection_surface_preview_builds_patch_object() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:primary", "region:primary-intersection"),
            object_name="V1RegionModelPrimary",
        )
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:side", "region:side-intersection"),
            object_name="V1RegionModelSide",
        )
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=_sample_intersection_model(),
        )
        create_or_update_v1_applied_section_set_object(
            doc,
            project=project,
            applied_section_set=_sample_intersection_applied_sections_with_tie_in_span(),
        )
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        rows = corridor_build_review_rows(doc)
        intersection_row = [row for row in rows if row["role"] == "intersection"][0]
        assert [row for row in rows if row["role"] == "intersection_zone_surface"] == []
        replacement_readiness_row = [row for row in rows if row["role"] == "intersection_replacement_readiness"][0]
        guided_steps = corridor_build_guided_review_steps(doc)
        intersection_step = [row for row in guided_steps if row["step_id"] == "intersections"][0]

        assert preview is not None
        assert preview.Name == "V1CorridorIntersectionSurfacePreview"
        assert preview.SurfaceKind == "intersection_surface"
        assert preview.SurfaceRole == "intersection"
        assert preview.IntersectionId == "intersection:t-01"
        assert preview.IntersectionGradingPolicyRef == "grading:intersection:t-01:default"
        assert preview.IntersectionGradingMode == "flatten_intersection"
        assert float(preview.IntersectionGradingZDeltaMax) > 0.0
        assert int(preview.IntersectionSuperelevationSourceCount) == 1
        assert int(preview.IntersectionSuperelevationTransitionCount) == 2
        assert float(preview.IntersectionSuperelevationLeftMin) == -3.0
        assert float(preview.IntersectionSuperelevationLeftMax) == -2.0
        assert float(preview.IntersectionSuperelevationRightMin) == 3.0
        assert float(preview.IntersectionSuperelevationRightMax) == 4.0
        assert "sources=1" in preview.IntersectionSuperelevationContext
        assert int(preview.IntersectionTINLowPointCandidateCount) >= 1
        assert float(preview.IntersectionTINLowPointZ) > 0.0
        assert "boundary_to_low" in preview.IntersectionBoundaryToLowFlowHintSummary
        assert int(preview.ParticipatingAlignmentCount) == 2
        assert int(preview.ControlRegionCount) == 2
        assert int(preview.PatchBoundaryPointCount) >= 4
        assert int(preview.TriangleCount) > 0
        assert preview.PatchTriangulationMode == "structured_strip_curb_return_blend"
        assert preview.PatchSurfaceBoundaryStrategy == "structured_strip_curb_return_blend"
        assert int(preview.PatchStructuredStripCount) == 2
        assert int(preview.PatchCurbReturnSurfaceEdgeCount) == 2
        assert int(preview.PatchCurbReturnArcCount) == 2
        assert int(preview.PatchCurbReturnArcSampleCount) >= 11
        assert int(preview.PatchCurbReturnArcSegmentCount) >= 20
        assert int(preview.PatchEdgeBlendFaceCount) >= 20
        assert preview.PatchBoundaryRoleSummary == "pavement_tie_in=2; stem_tie_in=2; overlap_cut=1; curb_return=2"
        assert int(preview.PatchPavementTieInEdgeCount) == 2
        assert int(preview.PatchStemTieInEdgeCount) == 2
        assert int(preview.PatchOverlapCutEdgeCount) == 1
        assert int(preview.PatchCurbReturnEdgeCount) == 2
        assert preview.IntersectionImplementationMode == "legacy_patch_frozen"
        assert preview.IntersectionRedesignPath == "edge_network_first"
        assert preview.IntersectionOutputPath == "legacy_output"
        assert preview.ConsumedIntersectionTopologyResultId == "intersection-topology:intersection:t-01"
        assert preview.ConsumedIntersectionEdgeNetworkResultId == "intersection-edge-network:intersection:t-01"
        assert preview.ConsumedIntersectionSurfaceZoneResultId == "intersection-surface-zones:intersection:t-01"
        assert preview.IntersectionSurfaceZoneOutputId == "intersection-surface-zone-output:intersection-t-01"
        assert preview.IntersectionSurfaceZoneOutputStatus in {"ready", "warning"}
        assert preview.IntersectionSurfaceZoneOutputContractStatus == "accepted_surface_zone"
        assert preview.IntersectionSurfaceZoneOutputDigitalTwinHandoff == "accepted_zone_candidate"
        assert preview.IntersectionSurfaceZoneOutputSurfaceZoneResultRef == "intersection-surface-zones:intersection:t-01"
        assert preview.IntersectionSurfaceZoneOutputEdgeNetworkResultRef == "intersection-edge-network:intersection:t-01"
        assert int(preview.IntersectionSurfaceZoneOutputRowCount) >= 1
        assert list(preview.IntersectionSurfaceZoneOutputRowRefs)
        assert all(str(row).startswith("intersection-surface-zone-output:intersection-t-01:") for row in list(preview.IntersectionSurfaceZoneOutputRowRefs))
        assert all(str(row).endswith((":ready", ":warning")) for row in list(preview.IntersectionSurfaceZoneOutputRowStatuses))
        assert list(preview.IntersectionSurfaceZoneOutputRowLineage)
        assert any("legs=" in row and "alignments=" in row for row in list(preview.IntersectionSurfaceZoneOutputRowLineage))
        assert any("vertical_policy=" in row for row in list(preview.IntersectionSurfaceZoneOutputRowLineage))
        assert "contract=accepted_surface_zone" in preview.IntersectionSurfaceZoneOutputSummary
        assert "handoff=accepted_zone_candidate" in preview.IntersectionSurfaceZoneOutputSummary
        assert "legs=" in preview.IntersectionSurfaceZoneOutputSummary
        assert "alignments=" in preview.IntersectionSurfaceZoneOutputSummary
        assert preview.IntersectionSurfaceZoneOutputPreviewRef == ""
        zone_output_preview = doc.getObject("V1CorridorIntersectionSurfaceZoneOutputPreview")
        assert zone_output_preview is None
        assert preview.IntersectionSurfaceZoneSurfacePreviewRef == ""
        zone_surface_preview = doc.getObject("V1CorridorIntersectionSurfaceZoneSurfacePreview")
        assert zone_surface_preview is None
        assert preview.IntersectionSurfaceReplacementGateStatus == "blocked"
        assert preview.IntersectionSurfaceReplacementGateRecommendation == "build_accepted_zone_surface_before_replacing_patch"
        assert preview.IntersectionSurfaceReplacementZoneSurfaceRef == ""
        assert int(preview.IntersectionSurfaceComparisonPatchTriangleCount) == int(preview.TriangleCount)
        assert int(preview.IntersectionSurfaceComparisonZoneTriangleCount) == 0
        assert int(preview.IntersectionSurfaceComparisonZoneVertexCount) == 0
        assert int(preview.IntersectionSurfaceComparisonZoneOutputRowCount) == int(preview.IntersectionSurfaceZoneOutputRowCount)
        assert preview.IntersectionSurfaceReplacementReadinessStatus == "blocked"
        assert preview.IntersectionSurfaceReplacementHandoffRole == "transitional_patch"
        assert preview.IntersectionSurfaceReplacementHandoffPreference == "fallback_blocked_replacement"
        assert int(preview.IntersectionSurfaceDownstreamHandoffSelected) == 1
        assert preview.IntersectionSurfaceDownstreamHandoffSelectedRef == "V1CorridorIntersectionSurfacePreview"
        assert preview.IntersectionSurfaceDownstreamHandoffSelectedRole == "transitional_patch_fallback"
        assert preview.IntersectionSurfaceDownstreamHandoffSelectionReason == "replacement_gate_blocked"
        assert preview.IntersectionSurfaceReplacementBlockerKind == "intersection_replacement_gate_blocked"
        assert "replacement_blocker=intersection_replacement_gate_blocked" in preview.IntersectionSurfaceDownstreamHandoffSummary
        assert "gate=blocked" in preview.IntersectionSurfaceReplacementSummary
        assert "recommendation=build_accepted_zone_surface_before_replacing_patch" in preview.IntersectionSurfaceReplacementSummary
        assert "acceptance_evidence=1" in preview.IntersectionSurfaceReplacementSummary
        assert "error:intersection_surface_replacement_zone_surface_missing" in list(preview.IntersectionSurfaceReplacementDiagnostics)
        assert "info:intersection_surface_patch_is_transitional_normalized" in list(preview.IntersectionSurfaceReplacementDiagnostics)
        assert "info:intersection_surface_zone_output_is_accepted_candidate" in list(preview.IntersectionSurfaceReplacementDiagnostics)
        assert "error:required_evidence:accepted_zone_surface_preview_missing" in list(preview.IntersectionSurfaceReplacementAcceptanceDiagnostics)
        assert preview.ConsumedIntersectionGradingContextResultId == "intersection-grading-context:intersection:t-01"
        assert preview.ConsumedIntersectionDrainageHintResultId == "intersection-drainage-hints:intersection:t-01"
        assert preview.ConsumedIntersectionSlopeFaceLoopResultId == "intersection-slope-face-loops:intersection:t-01"
        assert preview.IntersectionSlopeFaceLoopPreviewRef == ""
        assert doc.getObject("V1CorridorIntersectionSlopeFaceLoopPreview") is None
        assert doc.getObject("V1CorridorIntersectionSlopeFaceBoundaryPreview") is None
        assert "topology=" in preview.ConsumedIntersectionContractSummary
        assert "edge_network=" in preview.ConsumedIntersectionContractSummary
        assert "surface_zone=" in preview.ConsumedIntersectionContractSummary
        assert "grading_context=" in preview.ConsumedIntersectionContractSummary
        assert "drainage_hint=" in preview.ConsumedIntersectionContractSummary
        assert "slope_face_loop=" in preview.ConsumedIntersectionContractSummary
        assert int(preview.ConsumedIntersectionContractCount) == 6
        assert preview.IntersectionSurfacePatchResultId == "intersection-surface-patch:intersection-t-01"
        assert preview.IntersectionSurfacePatchStatus == "warning"
        assert preview.IntersectionSurfacePatchOutputPath == "legacy_output"
        assert preview.IntersectionSurfacePatchOutputContractStatus == "transitional_normalized"
        assert preview.IntersectionSurfacePatchDigitalTwinHandoff == "review_required"
        assert preview.IntersectionSurfacePatchTransitionalReason == "legacy_patch_surface_output"
        assert preview.IntersectionSurfacePatchReplacementPath == "accepted_intersection_surface_zone_output"
        assert int(preview.IntersectionSurfacePatchBoundaryRowCount) == 1
        assert int(preview.IntersectionSurfacePatchTriangulationRowCount) == 1
        assert int(preview.IntersectionSurfacePatchQualityRowCount) == 1
        assert list(preview.IntersectionSurfacePatchBoundaryRowRefs) == ["intersection-surface-patch-boundary:intersection-t-01"]
        assert list(preview.IntersectionSurfacePatchTriangulationRowRefs) == ["intersection-surface-patch-triangulation:intersection-t-01"]
        assert list(preview.IntersectionSurfacePatchQualityRowRefs) == ["intersection-surface-patch-quality:intersection-t-01"]
        assert list(preview.IntersectionSurfacePatchBoundaryRowStatuses) == ["intersection-surface-patch-boundary:intersection-t-01:ready"]
        assert list(preview.IntersectionSurfacePatchTriangulationRowStatuses) == ["intersection-surface-patch-triangulation:intersection-t-01:ready"]
        assert list(preview.IntersectionSurfacePatchQualityRowStatuses) == ["intersection-surface-patch-quality:intersection-t-01:warning"]
        assert any("quality:intersection-surface-patch-quality:intersection-t-01:" in row for row in list(preview.IntersectionSurfacePatchRowDiagnostics))
        assert "boundary=ready" in preview.IntersectionSurfacePatchSummary
        assert "triangulation=structured_strip_curb_return_blend" in preview.IntersectionSurfacePatchSummary
        assert "quality=warning" in preview.IntersectionSurfacePatchSummary
        assert "points=" in preview.IntersectionSurfacePatchFootprintSummary
        assert "rings=" in preview.IntersectionSurfacePatchFootprintSummary
        assert "area=" in preview.IntersectionSurfacePatchFootprintSummary
        assert "bbox=" in preview.IntersectionSurfacePatchFootprintSummary
        assert "curb_return_edges=2" in preview.IntersectionSurfacePatchFootprintSummary
        assert "curb_return_arcs=2" in preview.IntersectionSurfacePatchFootprintSummary
        assert "tie_in_edges=4" in preview.IntersectionSurfacePatchFootprintSummary
        assert list(preview.IntersectionSurfacePatchConsumedContractRefs) == list(preview.ConsumedIntersectionContractRefs)
        assert preview.IntersectionLegacyPatchReviewVisibility == "metadata_only"
        assert int(preview.IntersectionLegacyPatchCompatibilityPropertyCount) >= 5
        legacy_patch_audit = list(preview.IntersectionLegacyPatchCompatibilityAudit)
        assert "property_only:PatchBoundaryPointCount->IntersectionSurfacePatchBoundaryRowCount:normalized_available" in legacy_patch_audit
        assert "property_only:PatchTriangulationMode->IntersectionSurfacePatchSummary:normalized_available" in legacy_patch_audit
        assert "property_only:PatchSurfaceBoundaryStrategy->IntersectionSurfacePatchSummary:normalized_available" in legacy_patch_audit
        assert "property_only:PatchBoundaryRoleSummary->IntersectionSurfacePatchBoundaryRowRefs:normalized_available" in legacy_patch_audit
        assert "review_visibility=metadata_only" in preview.IntersectionLegacyPatchCompatibilityAuditSummary
        assert "Frozen first-slice patch path" in preview.IntersectionImplementationStatus
        assert "legacy_patch_review=metadata_only" in preview.IntersectionReviewSummary
        assert "legacy_patch_audit=review_visibility=metadata_only" in preview.IntersectionReviewSummary
        assert "surface_patch=boundary=ready" in preview.IntersectionReviewSummary
        assert "boundary roles=pavement_tie_in=2; stem_tie_in=2; overlap_cut=1; curb_return=2" not in preview.IntersectionReviewSummary
        assert "surface boundary=structured_strip_curb_return_blend" not in preview.IntersectionReviewSummary
        assert "implementation=legacy_patch_frozen" in preview.IntersectionReviewSummary
        assert "next=edge_network_first" in preview.IntersectionReviewSummary
        assert "output_path=legacy_output" in preview.IntersectionReviewSummary
        assert "consumed_contracts=topology=" in preview.IntersectionReviewSummary
        assert "surface_patch_result=intersection-surface-patch:intersection-t-01" in preview.IntersectionReviewSummary
        assert "surface_patch_footprint=points=" in preview.IntersectionReviewSummary
        assert "curb_return_edges=2" in preview.IntersectionReviewSummary
        assert "tie_in_edges=4" in preview.IntersectionReviewSummary
        assert "surface_zone_output=status=" in preview.IntersectionReviewSummary
        assert "surface_zone_output_contract=accepted_surface_zone" in preview.IntersectionReviewSummary
        assert "surface_zone_output_handoff=accepted_zone_candidate" in preview.IntersectionReviewSummary
        assert "surface_replacement=gate=blocked" in preview.IntersectionReviewSummary
        assert "surface_replacement_gate=blocked" in preview.IntersectionReviewSummary
        assert "surface_patch_contract=transitional_normalized" in preview.IntersectionReviewSummary
        assert "surface_patch_handoff=review_required" in preview.IntersectionReviewSummary
        assert "surface_patch_transitional_reason=legacy_patch_surface_output" in preview.IntersectionReviewSummary
        assert "surface_patch_replacement=accepted_intersection_surface_zone_output" in preview.IntersectionReviewSummary
        assert "surface_patch_rows=boundary=ready, triangulation=ready, quality=warning" in preview.IntersectionReviewSummary
        assert "surface_patch_row_diagnostics=1" in preview.IntersectionReviewSummary
        assert float(preview.PatchBoundaryBBoxAspectRatio) >= 1.0
        assert float(preview.PatchTriangleMinQuality) > 0.0
        assert int(preview.PatchTriangleSkinnyCount) >= 0
        assert intersection_row["status"] == "warning"
        assert intersection_row["result"] == "Intersection Surface"
        assert intersection_row["output_path"] == "legacy_output"
        assert replacement_readiness_row["status"] == "error"
        assert replacement_readiness_row["result"] == "Intersection Replacement Readiness"
        assert replacement_readiness_row["object_name"] == "V1CorridorIntersectionSurfacePreview"
        assert replacement_readiness_row["output_path"] == "review_gate"
        assert replacement_readiness_row["triangle_or_point_count"] == 0
        assert "Replacement readiness=blocked" in replacement_readiness_row["notes"]
        assert "gate=blocked" in replacement_readiness_row["notes"]
        assert "recommendation=build_accepted_zone_surface_before_replacing_patch" in replacement_readiness_row["notes"]
        assert "acceptance_evidence=1" in replacement_readiness_row["notes"]
        assert "tie-in edges=4" in intersection_row["notes"]
        assert "grading policy=intersection:t-01:default" in intersection_row["notes"]
        assert "grading=flatten_intersection" in intersection_row["notes"]
        assert "target crossfall=0.000%" in intersection_row["notes"]
        assert "max z adjustment=" in intersection_row["notes"]
        assert "superelevation=sources=1" in intersection_row["notes"]
        assert "low-point candidates=" in intersection_row["notes"]
        assert "flow hint=boundary_to_low" in intersection_row["notes"]
        assert "tie-in status=ready" in intersection_row["notes"]
        assert "legacy_patch_review=metadata_only" in intersection_row["notes"]
        assert "legacy_patch_audit=review_visibility=metadata_only" in intersection_row["notes"]
        assert "patch boundary=ready" not in intersection_row["notes"]
        assert "surface boundary=structured_strip_curb_return_blend" not in intersection_row["notes"]
        assert "structured strips=2" not in intersection_row["notes"]
        assert "curb-return surface edges=2" not in intersection_row["notes"]
        assert "curb-return arcs=2" not in intersection_row["notes"]
        assert "implementation=legacy_patch_frozen" in intersection_row["notes"]
        assert "next=edge_network_first" in intersection_row["notes"]
        assert "output_path=legacy_output" in intersection_row["notes"]
        assert "consumed_contracts=topology=" in intersection_row["notes"]
        assert "surface_patch_result=intersection-surface-patch:intersection-t-01" in intersection_row["notes"]
        assert "boundary roles=pavement_tie_in=2; stem_tie_in=2; overlap_cut=1; curb_return=2" not in intersection_row["notes"]
        assert "surface_zone_output_contract=accepted_surface_zone" in intersection_row["notes"]
        assert "surface_zone_output_handoff=accepted_zone_candidate" in intersection_row["notes"]
        assert "surface_replacement_gate=blocked" in intersection_row["notes"]
        assert "surface_patch_contract=transitional_normalized" in intersection_row["notes"]
        assert "surface_patch_handoff=review_required" in intersection_row["notes"]
        assert "surface_patch_rows=boundary=ready, triangulation=ready, quality=warning" in intersection_row["notes"]
        assert "surface_patch_row_diagnostics=1" in intersection_row["notes"]
        assert "grading policy=intersection:t-01:default, mode=flatten_intersection" in intersection_step["notes"]
        assert "superelevation sources=1, transitions=2" in intersection_step["notes"]
        assert "surface_patch_contract=transitional_normalized" in intersection_step["notes"]
        assert "surface_patch_handoff=review_required" in intersection_step["notes"]
        assert "surface_patch_replacement=accepted_intersection_surface_zone_output" in intersection_step["notes"]
        assert "surface_zone_output_contract=accepted_surface_zone" in intersection_step["notes"]
        assert "surface_zone_output_handoff=accepted_zone_candidate" in intersection_step["notes"]
        assert "surface_replacement_gate=blocked" in intersection_step["notes"]
        assert "surface_patch_rows=boundary=ready, triangulation=ready, quality=warning" in intersection_step["notes"]
        assert "surface_patch_row_diagnostics=1" in intersection_step["notes"]
        assert "structured strips=2" not in intersection_step["notes"]
        assert "curb-return arcs=2" not in intersection_step["notes"]
        assert preferred_corridor_build_review_row_index(rows, preferred_role="intersection") is None
        guided_focus = focus_corridor_build_guided_review_step(doc, "intersections")
        assert guided_focus.Name == "V1CorridorIntersectionSurfacePreview"
        focused = show_corridor_build_review_object(doc, rows.index(intersection_row))
        assert focused.Name == "V1CorridorIntersectionSurfacePreview"
        shown = set_corridor_build_preview_visibility(doc, "intersection_zone_surface", True)
        assert shown is None
        assert doc.getObject("V1CorridorIntersectionCurbReturnSlopePreview") is None
    finally:
        App.closeDocument(doc.Name)


def test_intersection_slope_face_surface_preview_records_consumed_loop_contract() -> None:
    doc, project = _new_project_doc()
    try:
        loop_result = IntersectionSlopeFaceLoopResult(
            schema_version=1,
            project_id="proj-1",
            loop_result_id="intersection-slope-face-loops:test",
            intersection_id="intersection:test",
            status="warning",
            loop_count=2,
            ready_count=1,
            warning_count=1,
            loop_rows=[
                IntersectionSlopeFaceLoopRow(
                    loop_id="loop:test:outer",
                    intersection_id="intersection:test",
                    loop_family="primary_outside",
                    loop_points_xyz=((0.0, 0.0, 10.0), (5.0, 0.0, 10.0), (5.0, 4.0, 9.0), (0.0, 4.0, 9.0)),
                    source_edge_network_refs=("edge:test:1",),
                    source_surface_zone_refs=("zone:test:1",),
                    closed_xy=True,
                    point_count=4,
                    status="ready",
                ),
                IntersectionSlopeFaceLoopRow(
                    loop_id="loop:test:warning",
                    intersection_id="intersection:test",
                    loop_family="secondary_outside",
                    source_edge_network_refs=("edge:test:warning",),
                    source_surface_zone_refs=("zone:test:warning",),
                    source_edge_network_status="warning",
                    source_surface_zone_status="warning",
                    source_status="warning",
                    source_diagnostic_rows=("source_edge_network:edge:test:warning:source_edge_family_policy_ref_missing",),
                    source_lineage_status="source_warning",
                    point_count=0,
                    status="warning",
                ),
            ],
            source_refs=["intersection:test"],
        )

        slope_preview = build_corridor_command._create_corridor_intersection_slope_face_surface_preview(
            doc,
            loop_result,
            project=project,
        )

        assert slope_preview is not None
        assert slope_preview.ConsumedIntersectionSlopeFaceLoopResultId == "intersection-slope-face-loops:test"
        assert list(slope_preview.ConsumedIntersectionContractRefs) == ["intersection-slope-face-loops:test"]
        assert slope_preview.ConsumedIntersectionContractSummary == "slope_face_loop=warning rows=2"
        assert int(slope_preview.ConsumedIntersectionContractCount) == 1
        diagnostics = list(slope_preview.ConsumedIntersectionContractDiagnostics)
        assert "slope_face_loop:loop:test:warning:source_status=warning" in diagnostics
        assert "slope_face_loop:loop:test:warning:source_lineage=source_warning" in diagnostics
        assert "slope_face_loop:loop:test:warning:surface_zone_status=warning" in diagnostics
        assert "slope_face_loop:loop:test:warning:edge_network_status=warning" in diagnostics
        assert "slope_face_loop:loop:test:warning:source:source_edge_network:edge:test:warning:source_edge_family_policy_ref_missing" in diagnostics
        review_rows = corridor_build_review_rows(doc)
        slope_row = [row for row in review_rows if row["role"] == "intersection_slope"][0]
        assert slope_row["output_path"] == "contract_consumed"
        assert "consumed_contracts=slope_face_loop=warning rows=2" in str(slope_row["notes"])
        assert f"consumed_contract_diagnostics={len(diagnostics)}" in str(slope_row["notes"])
        assert (
            build_corridor_command._corridor_build_review_output_path(
                "intersection_slope",
                SimpleNamespace(
                    ReadyLoopCount=0,
                    SourceLoopRefs=[],
                    ConsumedIntersectionContractRefs=["intersection-slope-face-loops:test"],
                ),
            )
            == "contract_consumed"
        )
    finally:
        App.closeDocument(doc.Name)


def test_intersection_consumed_contract_metadata_preserves_row_source_diagnostics() -> None:
    doc, _project = _new_project_doc()
    try:
        preview = doc.addObject("Part::Feature", "V1IntersectionConsumedContractMetadataPreview")
        build_corridor_command._attach_intersection_contract_consumption_metadata(
            preview,
            edge_network_result=SimpleNamespace(
                edge_network_result_id="intersection-edge-network:test",
                status="warning",
                source_refs=["intersection:test"],
                diagnostic_rows=["warning:edge_network_result_warning"],
                edge_rows=[
                    SimpleNamespace(
                        edge_id="edge:test:warning",
                        source_status="warning",
                        source_diagnostic_rows=("source_edge_policy_ref_unresolved",),
                    )
                ],
            ),
            surface_zone_result=SimpleNamespace(
                surface_zone_result_id="intersection-surface-zones:test",
                status="warning",
                source_refs=["intersection:test"],
                diagnostic_rows=[],
                zone_rows=[
                    SimpleNamespace(
                        zone_id="zone:test:warning",
                        source_status="warning",
                        source_diagnostic_rows=("surface_zone_source_edge_diagnostic",),
                    )
                ],
            ),
            grading_context_result=SimpleNamespace(
                grading_context_result_id="intersection-grading-context:test",
                status="warning",
                source_refs=["intersection:test"],
                diagnostic_rows=[],
                context_rows=[
                    SimpleNamespace(
                        context_id="grading:test:warning",
                        source_status="warning",
                        source_diagnostic_rows=("source_grading_policy_mode_unknown",),
                    )
                ],
            ),
            drainage_hint_result=SimpleNamespace(
                drainage_hint_result_id="intersection-drainage-hints:test",
                status="warning",
                source_refs=["intersection:test"],
                diagnostic_rows=[],
                hint_rows=[
                    SimpleNamespace(
                        hint_id="drainage:test:error",
                        source_status="error",
                        source_diagnostic_rows=("source_drainage_element_refs_missing",),
                    )
                ],
            ),
            slope_loop_result=SimpleNamespace(
                loop_result_id="intersection-slope-face-loops:test",
                status="warning",
                source_refs=["intersection:test"],
                diagnostic_rows=[],
                loop_rows=[
                    SimpleNamespace(
                        loop_id="loop:test:warning",
                        source_status="warning",
                        source_lineage_status="source_warning",
                        source_surface_zone_status="warning",
                        source_edge_network_status="warning",
                        source_diagnostic_rows=("source_edge_network:edge:test:warning:source_edge_policy_ref_unresolved",),
                    )
                ],
            ),
        )

        diagnostics = list(preview.ConsumedIntersectionContractDiagnostics)

        assert preview.ConsumedIntersectionContractSummary == (
            "edge_network=warning rows=1; "
            "surface_zone=warning rows=1; "
            "grading_context=warning rows=1; "
            "drainage_hint=warning rows=1; "
            "slope_face_loop=warning rows=1"
        )
        assert "edge_network:warning:edge_network_result_warning" in diagnostics
        assert "edge_network:edge:test:warning:source_status=warning" in diagnostics
        assert "edge_network:edge:test:warning:source:source_edge_policy_ref_unresolved" in diagnostics
        assert "surface_zone:zone:test:warning:source:surface_zone_source_edge_diagnostic" in diagnostics
        assert "grading_context:grading:test:warning:source:source_grading_policy_mode_unknown" in diagnostics
        assert "drainage_hint:drainage:test:error:source_status=error" in diagnostics
        assert "drainage_hint:drainage:test:error:source:source_drainage_element_refs_missing" in diagnostics
        assert "slope_face_loop:loop:test:warning:source_lineage=source_warning" in diagnostics
        assert "slope_face_loop:loop:test:warning:edge_network_status=warning" in diagnostics
        assert "slope_face_loop:loop:test:warning:source:source_edge_network:edge:test:warning:source_edge_policy_ref_unresolved" in diagnostics
        assert int(preview.ConsumedIntersectionContractDiagnosticCount) == len(diagnostics)
    finally:
        App.closeDocument(doc.Name)


def test_intersection_slope_face_boundary_strips_are_suppressed_but_record_metadata() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
    )
    boundary_result = IntersectionSlopeFaceBoundaryResult(
        schema_version=1,
        project_id="proj-1",
        boundary_result_id="intersection-slope-face-boundary:test",
        intersection_id="intersection:test",
        status="ready",
        boundary_count=1,
        ready_count=1,
        boundary_rows=[
            IntersectionSlopeFaceBoundaryRow(
                boundary_id="slope-face-boundary:test:left",
                intersection_id="intersection:test",
                alignment_ref="alignment:test",
                side="left",
                inner_points_xyz=((0.0, 0.0, 10.0), (5.0, 0.0, 10.0)),
                outer_points_xyz=((0.0, 3.0, 9.0), (5.0, 3.0, 9.0)),
                source_applied_section_refs=("section:1", "section:2"),
                source_intersection_surface_ref="intersection-boundary:test:left",
                status="ready",
            )
        ],
    )

    augmented = build_corridor_command._augment_daylight_surface_with_slope_face_boundary_strips(
        surface,
        boundary_result,
    )

    assert build_corridor_command._tin_quality_text(augmented, "intersection_slope_face_boundary_result_id") == "intersection-slope-face-boundary:test"
    assert build_corridor_command._tin_quality_text(augmented, "intersection_slope_face_boundary_status") == "ready"
    assert build_corridor_command._tin_quality_float(augmented, "intersection_slope_face_boundary_count") == 1
    assert build_corridor_command._tin_quality_float(augmented, "intersection_slope_face_boundary_ready_count") == 1
    assert build_corridor_command._tin_quality_text(augmented, "intersection_slope_face_boundary_refs") == "slope-face-boundary:test:left"
    assert "boundary_result=intersection-slope-face-boundary:test" in build_corridor_command._tin_quality_text(
        augmented,
        "intersection_slope_face_boundary_summary",
    )
    assert build_corridor_command._tin_quality_float(augmented, "intersection_slope_face_boundary_strip_triangle_count") == 0
    assert build_corridor_command._tin_quality_text(augmented, "intersection_slope_face_boundary_strip_generation_mode") == "suppressed"
    assert build_corridor_command._tin_quality_text(augmented, "intersection_slope_face_boundary_strip_output_path") == "metadata_only"
    assert (
        build_corridor_command._tin_quality_text(augmented, "intersection_slope_face_boundary_strip_diagnostic")
        == "visible_boundary_strip_generation_suppressed"
    )
    review_note = build_corridor_command._intersection_slope_face_boundary_review_note(
        SimpleNamespace(
            IntersectionSlopeFaceBoundarySummary="boundary_result=intersection-slope-face-boundary:test; status=ready; ready=1/1; warnings=0; strip_generation=suppressed",
            IntersectionSlopeFaceBoundaryStripGenerationMode="suppressed",
            IntersectionSlopeFaceBoundaryStripOutputPath="metadata_only",
            IntersectionSlopeFaceBoundaryStripCount=0,
            IntersectionSlopeFaceBoundaryStripTriangleCount=0,
            IntersectionSlopeFaceBoundaryStripDiagnostic="visible_boundary_strip_generation_suppressed",
        )
    )
    assert "strip_generation=suppressed" in review_note
    assert "strip_output=metadata_only" in review_note
    assert "strip_diagnostic=visible_boundary_strip_generation_suppressed" in review_note
    guided_suffix = build_corridor_command._slope_face_boundary_guided_review_suffix(
        {"notes": f"Slope Face Surface ready | {review_note}"}
    )
    assert guided_suffix.startswith("boundary_review=intersection_slope_face_boundary_result")
    assert "slope_face_boundary=boundary_result=intersection-slope-face-boundary:test" in guided_suffix
    assert "strip_generation=suppressed" in guided_suffix


def test_intersection_patch_boundary_tin_vertices_preserve_elevation_source_notes() -> None:
    result = IntersectionPatchBoundaryResult(
        schema_version=1,
        project_id="proj-1",
        patch_boundary_result_id="intersection-patch-boundary:test",
        intersection_id="intersection:t-01",
        status="ready",
        boundary_point_count=1,
        point_rows=[
            IntersectionPatchBoundaryPointRow(
                boundary_point_id="patch-point:1",
                intersection_id="intersection:t-01",
                order_index=1,
                x=10.0,
                y=0.0,
                z=0.0,
                source_segment_ref="segment:1",
                source_kind="tie_in_edge",
            )
        ],
    )
    source_vertices = [
        TINVertex(
            "v:source",
            10.0,
            0.0,
            12.5,
            source_point_ref="section:10:fg:2",
            notes="alignment=alignment:primary; station=10.000; intersection_grading=flatten_intersection",
        )
    ]

    vertices = build_corridor_command._intersection_patch_boundary_tin_vertices(
        result,
        source_vertices=source_vertices,
    )

    assert len(vertices) == 1
    assert vertices[0].z == 12.5
    assert "elevation_source=section:10:fg:2" in vertices[0].notes
    assert "intersection_grading=flatten_intersection" in vertices[0].notes


def test_intersection_tie_in_single_section_uses_frame_tangent_direction() -> None:
    section = AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id="section:side-single",
        corridor_id="corridor:main",
        alignment_id="alignment:side",
        region_id="region:side-intersection",
        station=120.0,
        frame=AppliedSectionFrame(station=120.0, x=20.0, y=0.0, z=12.0, tangent_direction_deg=90.0),
        surface_left_width=4.0,
        surface_right_width=4.0,
        active_intersection_id="intersection:t-01",
        point_rows=[
            AppliedSectionPoint("fg:left", 16.0, 0.0, 12.0, "fg_surface", 4.0),
            AppliedSectionPoint("fg:right", 24.0, 0.0, 12.0, "fg_surface", -4.0),
        ],
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:single-side",
        corridor_id="corridor:main",
        sections=[section],
    )

    result = corridor_intersection_tie_in_edge_result(
        applied,
        prerequisite=IntersectionPatchPrerequisiteResult(
            status="ready",
            intersection_id="intersection:t-01",
            alignment_refs=("alignment:side",),
            control_region_refs=("region:side-intersection",),
        ),
    )

    assert result.edge_count == 2
    for edge in result.edge_rows:
        dx = float(edge.end_xyz[0]) - float(edge.start_xyz[0])
        dy = float(edge.end_xyz[1]) - float(edge.start_xyz[1])
        assert abs(dx) < 1.0e-6
        assert dy > 0.0
        assert edge.station_start < 120.0 < edge.station_end


def test_create_corridor_intersection_surface_preview_uses_center_sections_for_long_control_regions() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:primary", "region:primary-intersection"),
            object_name="V1RegionModelPrimary",
        )
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:side", "region:side-intersection"),
            object_name="V1RegionModelSide",
        )
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=IntersectionModel(
                schema_version=1,
                project_id="proj-1",
                intersection_model_id="intersections:test",
                intersection_rows=[
                    IntersectionRow(
                        intersection_id="intersection:t-01",
                        intersection_kind="t_intersection",
                        primary_alignment_ref="alignment:primary",
                        secondary_alignment_refs=["alignment:side"],
                        primary_station=120.0,
                        secondary_station_refs={"alignment:side": 120.0},
                        control_region_refs=["region:primary-intersection", "region:side-intersection"],
                    )
                ],
                control_area_rows=[
                    IntersectionControlArea(
                        control_area_id="control-area:t-01:primary",
                        intersection_id="intersection:t-01",
                        alignment_ref="alignment:primary",
                        station_ranges=[(96.0, 144.0)],
                        control_region_refs=["region:primary-intersection"],
                    ),
                    IntersectionControlArea(
                        control_area_id="control-area:t-01:side",
                        intersection_id="intersection:t-01",
                        alignment_ref="alignment:side",
                        station_ranges=[(96.0, 144.0)],
                        control_region_refs=["region:side-intersection"],
                    ),
                ],
            ),
        )
        sections = []
        station_rows = []
        for station in (96.0, 120.0, 144.0):
            station_rows.append(AppliedSectionStationRow(f"station:primary-{station:.0f}", station, f"section:primary-{station:.0f}"))
            sections.append(
                AppliedSection(
                    schema_version=1,
                    project_id="proj-1",
                    applied_section_id=f"section:primary-{station:.0f}",
                    corridor_id="corridor:main",
                    alignment_id="alignment:primary",
                    assembly_id="assembly:intersection-road",
                    region_id="region:primary-intersection",
                    station=station,
                    active_intersection_id="intersection:t-01",
                    point_rows=[
                        AppliedSectionPoint("fg:left", station, 5.0, 10.0, "fg_surface", 5.0),
                        AppliedSectionPoint("fg:right", station, -5.0, 10.0, "fg_surface", -5.0),
                    ],
                )
            )
            station_rows.append(AppliedSectionStationRow(f"station:side-{station:.0f}", station, f"section:side-{station:.0f}"))
            sections.append(
                AppliedSection(
                    schema_version=1,
                    project_id="proj-1",
                    applied_section_id=f"section:side-{station:.0f}",
                    corridor_id="corridor:main",
                    alignment_id="alignment:side",
                    assembly_id="assembly:intersection-road",
                    region_id="region:side-intersection",
                    station=station,
                    active_intersection_id="intersection:t-01",
                    point_rows=[
                        AppliedSectionPoint("fg:left", 116.0, station - 120.0, 12.0, "fg_surface", 4.0),
                        AppliedSectionPoint("fg:right", 124.0, station - 120.0, 12.0, "fg_surface", -4.0),
                    ],
                )
            )
        create_or_update_v1_applied_section_set_object(
            doc,
            project=project,
            applied_section_set=AppliedSectionSet(
                schema_version=1,
                project_id="proj-1",
                applied_section_set_id="sections:intersection-long",
                corridor_id="corridor:main",
                alignment_id="alignment:primary",
                station_rows=station_rows,
                sections=sections,
            ),
        )
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )

        assert preview is not None
        assert int(preview.PatchBoundaryPointCount) == int(preview.IntersectionPatchBoundaryOrderedPointCount)
        assert int(preview.TriangleCount) >= 4
        assert preview.PatchBoundarySource == "ordered_patch_boundary"
        assert int(preview.PatchDegenerateTriangleCount) == 0
        assert preview.PatchSurfaceBoundaryStrategy == "structured_strip_curb_return_blend"
        assert int(preview.PatchStructuredStripCount) >= 2
        assert int(preview.PatchCurbReturnSurfaceEdgeCount) >= 1
        assert float(preview.PatchBoundaryEdgeMaxLength) > 0.0
        assert int(preview.PatchBoundaryLongEdgeCount) >= 0
        assert float(preview.PatchBoundaryLongEdgeFactor) == 2.5
        assert float(preview.PatchBoundaryLongEdgeLimit) > 0.0
        assert float(preview.PatchBoundaryMaxEdgeLengthPolicy) == 0.0
        assert preview.PatchTriangulationMode == "structured_strip_curb_return_blend"
        assert float(preview.PatchBoundaryBBoxX) > 0.0
        assert float(preview.PatchBoundaryBBoxY) > 0.0
        assert float(preview.PatchBoundaryBBoxAspectRatio) >= 1.0
        assert float(preview.PatchTriangleMinQuality) > 0.0
        assert int(preview.PatchTriangleSkinnyCount) >= 0
        assert preview.Mesh.BoundBox.XLength >= 30.0
        assert preview.Mesh.BoundBox.YLength >= 25.0
        tie_in_preview = doc.getObject("V1CorridorIntersectionTieInEdgePreview")
        assert tie_in_preview is not None
        assert tie_in_preview.V1ObjectType == "V1CorridorIntersectionTieInEdgePreview"
        assert tie_in_preview.IntersectionId == "intersection:t-01"
        assert int(tie_in_preview.TieInEdgeCount) == 4
        assert int(tie_in_preview.DisplayedEdgeCount) == 4
        assert tie_in_preview.PreviewStatus == "ready"
        assert list(tie_in_preview.TieInEdgeDiagnostics) == []
        assert preview.TieInEdgePreviewRef == tie_in_preview.Name
        assert preview.IntersectionBoundaryMode == "curb_return_boundary"
        assert preview.IntersectionBoundaryStatus == "ready"
        assert int(preview.IntersectionBoundaryTieInSegmentCount) == 4
        assert int(preview.IntersectionBoundaryArcSegmentCount) == 2
        assert int(preview.IntersectionBoundaryDiagnosticCount) == 0
        assert preview.IntersectionPatchBoundaryStatus == "ready"
        assert preview.IntersectionPatchBoundaryClosed == "Yes"
        assert preview.IntersectionPatchBoundarySelfCrossing == "No"
        assert float(preview.IntersectionPatchBoundaryPolygonArea) > 0.0
        assert int(preview.IntersectionPatchBoundaryRingCount) == 1
        assert int(preview.IntersectionPatchBoundaryHoleRingCount) == 0
        assert int(preview.IntersectionPatchBoundaryIslandRingCount) == 0
        assert int(preview.IntersectionPatchBoundaryOrderedPointCount) >= 8
        assert int(preview.IntersectionPatchBoundarySourceSegmentCount) == 4
        assert int(preview.IntersectionPatchBoundaryDiagnosticCount) == 0
        boundary_preview = doc.getObject("V1CorridorIntersectionBoundarySegmentPreview")
        assert boundary_preview is not None
        assert boundary_preview.V1ObjectType == "V1CorridorIntersectionBoundarySegmentPreview"
        assert boundary_preview.IntersectionId == "intersection:t-01"
        assert int(boundary_preview.BoundarySegmentCount) == 6
        assert int(boundary_preview.DisplayedSegmentCount) == 6
        assert int(boundary_preview.ArcSegmentCount) == 2
        assert preview.IntersectionBoundaryPreviewRef == boundary_preview.Name
        exclusion_preview = doc.getObject("V1CorridorIntersectionExclusionZonePreview")
        assert exclusion_preview is not None
        assert exclusion_preview.V1ObjectType == "V1CorridorIntersectionExclusionZonePreview"
        assert exclusion_preview.IntersectionId == "intersection:t-01"
        assert exclusion_preview.ExclusionStatus == "ready"
        assert int(exclusion_preview.BoundaryPointCount) == int(preview.IntersectionPatchBoundaryOrderedPointCount)
        assert float(exclusion_preview.PolygonArea) > 0.0
        assert preview.IntersectionExclusionZoneRef == exclusion_preview.Name
        assert preview.IntersectionExclusionZoneStatus == "ready"
        assert int(preview.IntersectionExclusionZonePointCount) == int(exclusion_preview.BoundaryPointCount)
    finally:
        App.closeDocument(doc.Name)


def test_corridor_intersection_tie_in_edge_result_extracts_alignment_side_edges() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:intersection-long",
        corridor_id="corridor:main",
        alignment_id="alignment:primary",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:primary-96",
                corridor_id="corridor:main",
                alignment_id="alignment:primary",
                region_id="region:primary-intersection",
                station=96.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 96.0, 5.0, 10.0, "fg_surface", 5.0),
                    AppliedSectionPoint("fg:right", 96.0, -5.0, 10.0, "fg_surface", -5.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:primary-144",
                corridor_id="corridor:main",
                alignment_id="alignment:primary",
                region_id="region:primary-intersection",
                station=144.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 144.0, 5.0, 10.0, "fg_surface", 5.0),
                    AppliedSectionPoint("fg:right", 144.0, -5.0, 10.0, "fg_surface", -5.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-96",
                corridor_id="corridor:main",
                alignment_id="alignment:side",
                region_id="region:side-intersection",
                station=96.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 116.0, -24.0, 12.0, "fg_surface", 4.0),
                    AppliedSectionPoint("fg:right", 124.0, -24.0, 12.0, "fg_surface", -4.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-144",
                corridor_id="corridor:main",
                alignment_id="alignment:side",
                region_id="region:side-intersection",
                station=144.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 116.0, 24.0, 12.0, "fg_surface", 4.0),
                    AppliedSectionPoint("fg:right", 124.0, 24.0, 12.0, "fg_surface", -4.0),
                ],
            ),
        ],
    )
    prerequisite = IntersectionPatchPrerequisiteResult(
        status="ready",
        intersection_id="intersection:t-01",
        alignment_refs=("alignment:primary", "alignment:side"),
        control_region_refs=("region:primary-intersection", "region:side-intersection"),
    )
    intersection_model = IntersectionModel(
        schema_version=1,
        project_id="proj-1",
        intersection_model_id="intersections:test",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:t-01",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:primary",
                secondary_alignment_refs=["alignment:side"],
                primary_station=120.0,
                secondary_station_refs={"alignment:side": 120.0},
            )
        ],
    )

    result = corridor_intersection_tie_in_edge_result(
        applied,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
    )

    assert result.status == "ready"
    assert result.edge_count == 4
    assert {row.alignment_ref for row in result.edge_rows} == {"alignment:primary", "alignment:side"}
    assert {row.side for row in result.edge_rows} == {"left", "right"}
    assert all(row.station_start == 96.0 for row in result.edge_rows)
    assert all(row.station_end == 144.0 for row in result.edge_rows)
    assert {
        (row.alignment_ref, row.side, row.start_xyz, row.end_xyz)
        for row in result.edge_rows
    } == {
        ("alignment:primary", "left", (96.0, 5.0, 10.0), (144.0, 5.0, 10.0)),
        ("alignment:primary", "right", (96.0, -5.0, 10.0), (144.0, -5.0, 10.0)),
        ("alignment:side", "left", (116.0, -24.0, 12.0), (116.0, 24.0, 12.0)),
        ("alignment:side", "right", (124.0, -24.0, 12.0), (124.0, 24.0, 12.0)),
    }
    assert result.diagnostic_rows == []


def test_corridor_intersection_tie_in_edge_result_spans_across_exact_target_section() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:intersection-exact-target",
        corridor_id="corridor:main",
        alignment_id="alignment:primary",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id=f"section:primary-{station:.0f}",
                corridor_id="corridor:main",
                alignment_id="alignment:primary",
                region_id="region:primary-intersection",
                station=station,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", station, 5.0, 10.0, "fg_surface", 5.0),
                    AppliedSectionPoint("fg:right", station, -5.0, 10.0, "fg_surface", -5.0),
                ],
            )
            for station in (100.0, 120.0, 140.0)
        ],
    )
    prerequisite = IntersectionPatchPrerequisiteResult(
        status="ready",
        intersection_id="intersection:t-01",
        alignment_refs=("alignment:primary",),
        control_region_refs=("region:primary-intersection",),
    )
    intersection_model = IntersectionModel(
        schema_version=1,
        project_id="proj-1",
        intersection_model_id="intersections:test",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:t-01",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:primary",
                primary_station=120.0,
            )
        ],
    )

    result = corridor_intersection_tie_in_edge_result(
        applied,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
    )

    assert result.status == "ready"
    assert all(row.station_start == 100.0 for row in result.edge_rows)
    assert all(row.station_end == 140.0 for row in result.edge_rows)


def test_corridor_intersection_boundary_segment_result_promotes_tie_in_and_curb_return_arcs() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:intersection-long",
        corridor_id="corridor:main",
        alignment_id="alignment:primary",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:primary-96",
                corridor_id="corridor:main",
                alignment_id="alignment:primary",
                region_id="region:primary-intersection",
                station=96.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 96.0, 5.0, 10.0, "fg_surface", 5.0),
                    AppliedSectionPoint("fg:right", 96.0, -5.0, 10.0, "fg_surface", -5.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:primary-144",
                corridor_id="corridor:main",
                alignment_id="alignment:primary",
                region_id="region:primary-intersection",
                station=144.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 144.0, 5.0, 10.0, "fg_surface", 5.0),
                    AppliedSectionPoint("fg:right", 144.0, -5.0, 10.0, "fg_surface", -5.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-96",
                corridor_id="corridor:main",
                alignment_id="alignment:side",
                region_id="region:side-intersection",
                station=96.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 116.0, -24.0, 12.0, "fg_surface", 4.0),
                    AppliedSectionPoint("fg:right", 124.0, -24.0, 12.0, "fg_surface", -4.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-144",
                corridor_id="corridor:main",
                alignment_id="alignment:side",
                region_id="region:side-intersection",
                station=144.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 116.0, 24.0, 12.0, "fg_surface", 4.0),
                    AppliedSectionPoint("fg:right", 124.0, 24.0, 12.0, "fg_surface", -4.0),
                ],
            ),
        ],
    )
    prerequisite = IntersectionPatchPrerequisiteResult(
        status="ready",
        intersection_id="intersection:t-01",
        alignment_refs=("alignment:primary", "alignment:side"),
        control_region_refs=("region:primary-intersection", "region:side-intersection"),
    )
    intersection_model = IntersectionModel(
        schema_version=1,
        project_id="proj-1",
        intersection_model_id="intersections:test",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:t-01",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:primary",
                secondary_alignment_refs=["alignment:side"],
                intersection_point_x=120.0,
                intersection_point_y=0.0,
                primary_station=120.0,
                secondary_station_refs={"alignment:side": 120.0},
            )
        ],
        curb_return_policy_rows=[
            IntersectionCurbReturnPolicyRow(
                policy_id="curb-return:intersection:t-01:default",
                intersection_id="intersection:t-01",
                radius=12.0,
            )
        ],
    )
    tie_in_result = corridor_intersection_tie_in_edge_result(
        applied,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
    )

    result = corridor_intersection_boundary_segment_result(tie_in_result, intersection_model=intersection_model)

    assert result.status == "ready"
    assert result.tie_in_segment_count == 4
    assert result.arc_segment_count == 2
    assert result.segment_count == 6
    assert {row.segment_kind for row in result.segment_rows} == {"tie_in", "arc"}
    arc_rows = [row for row in result.segment_rows if row.segment_kind == "arc"]
    assert all(row.radius == 12.0 for row in arc_rows)
    assert all(len(row.chord_points_xyz) == 11 for row in arc_rows)
    assert all("arc_samples=11" in row.notes for row in arc_rows)
    assert result.diagnostic_rows == []


def test_intersection_practical_exclusion_polygon_uses_curb_return_blend_boundary() -> None:
    boundary_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        label="boundary",
        intersection_id="intersection:t-01",
        status="ready",
        segment_count=6,
        segment_rows=[
            IntersectionBoundarySegmentRow("edge:primary:left", "intersection:t-01", "tie_in", alignment_ref="alignment:primary", side="left", start_xyz=(0.0, 5.0, 0.0), end_xyz=(40.0, 5.0, 0.0)),
            IntersectionBoundarySegmentRow("edge:primary:right", "intersection:t-01", "tie_in", alignment_ref="alignment:primary", side="right", start_xyz=(0.0, -5.0, 0.0), end_xyz=(40.0, -5.0, 0.0)),
            IntersectionBoundarySegmentRow("edge:side:left", "intersection:t-01", "tie_in", alignment_ref="alignment:side", side="left", start_xyz=(16.0, -24.0, 0.0), end_xyz=(16.0, 0.0, 0.0)),
            IntersectionBoundarySegmentRow("edge:side:right", "intersection:t-01", "tie_in", alignment_ref="alignment:side", side="right", start_xyz=(24.0, -24.0, 0.0), end_xyz=(24.0, 0.0, 0.0)),
            IntersectionBoundarySegmentRow(
                "arc:right",
                "intersection:t-01",
                "arc",
                segment_role="curb_return",
                center_xyz=(20.0, 0.0, 0.0),
                chord_points_xyz=((32.0, 0.0, 0.0), (30.0, -6.0, 0.0), (24.0, -10.0, 0.0), (20.0, -12.0, 0.0)),
            ),
            IntersectionBoundarySegmentRow(
                "arc:left",
                "intersection:t-01",
                "arc",
                segment_role="curb_return",
                center_xyz=(20.0, 0.0, 0.0),
                chord_points_xyz=((8.0, 0.0, 0.0), (10.0, -6.0, 0.0), (16.0, -10.0, 0.0), (20.0, -12.0, 0.0)),
            ),
        ],
    )
    intersection_model = IntersectionModel(
        schema_version=1,
        project_id="proj-1",
        intersection_model_id="intersections:test",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:t-01",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:primary",
                secondary_alignment_refs=["alignment:side"],
            )
        ],
    )

    exclusion = build_corridor_command._intersection_practical_exclusion_polygon_from_boundary_segments(
        boundary_result,
        intersection_model=intersection_model,
    )

    assert exclusion is not None
    assert exclusion["boundary_source"] == "practical_intersection_surface_boundary"
    assert exclusion["boundary_strategy"] == "structured_strip_curb_return_blend"
    assert exclusion["practical_boundary_aligned"] is True
    assert exclusion["edge_blend_face_count"] > 0
    assert len(exclusion["points"]) >= 4
    assert float(exclusion["area"]) > 0.0


def test_corridor_intersection_patch_boundary_result_orders_boundary_segment_points() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:intersection-long",
        corridor_id="corridor:main",
        alignment_id="alignment:primary",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:primary-96",
                corridor_id="corridor:main",
                alignment_id="alignment:primary",
                region_id="region:primary-intersection",
                station=96.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 96.0, 5.0, 10.0, "fg_surface", 5.0),
                    AppliedSectionPoint("fg:right", 96.0, -5.0, 10.0, "fg_surface", -5.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:primary-144",
                corridor_id="corridor:main",
                alignment_id="alignment:primary",
                region_id="region:primary-intersection",
                station=144.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 144.0, 5.0, 10.0, "fg_surface", 5.0),
                    AppliedSectionPoint("fg:right", 144.0, -5.0, 10.0, "fg_surface", -5.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-96",
                corridor_id="corridor:main",
                alignment_id="alignment:side",
                region_id="region:side-intersection",
                station=96.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 116.0, -24.0, 12.0, "fg_surface", 4.0),
                    AppliedSectionPoint("fg:right", 124.0, -24.0, 12.0, "fg_surface", -4.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-144",
                corridor_id="corridor:main",
                alignment_id="alignment:side",
                region_id="region:side-intersection",
                station=144.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 116.0, 24.0, 12.0, "fg_surface", 4.0),
                    AppliedSectionPoint("fg:right", 124.0, 24.0, 12.0, "fg_surface", -4.0),
                ],
            ),
        ],
    )
    prerequisite = IntersectionPatchPrerequisiteResult(
        status="ready",
        intersection_id="intersection:t-01",
        alignment_refs=("alignment:primary", "alignment:side"),
        control_region_refs=("region:primary-intersection", "region:side-intersection"),
    )
    intersection_model = IntersectionModel(
        schema_version=1,
        project_id="proj-1",
        intersection_model_id="intersections:test",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:t-01",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:primary",
                secondary_alignment_refs=["alignment:side"],
                intersection_point_x=120.0,
                intersection_point_y=0.0,
                primary_station=120.0,
                secondary_station_refs={"alignment:side": 120.0},
            )
        ],
        curb_return_policy_rows=[
            IntersectionCurbReturnPolicyRow(
                policy_id="curb-return:intersection:t-01:default",
                intersection_id="intersection:t-01",
                radius=12.0,
            )
        ],
    )
    tie_in_result = corridor_intersection_tie_in_edge_result(
        applied,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
    )
    segment_result = corridor_intersection_boundary_segment_result(tie_in_result, intersection_model=intersection_model)

    result = corridor_intersection_patch_boundary_result(segment_result)

    assert result.status == "ready"
    assert result.boundary_mode == "tie_in_strip_union"
    assert result.closed is True
    assert result.source_segment_count == 4
    assert result.boundary_point_count >= 8
    assert result.self_crossing is False
    assert [row.order_index for row in result.point_rows] == list(range(1, result.boundary_point_count + 1))
    assert result.diagnostic_rows == []


def test_corridor_intersection_patch_boundary_result_preserves_hole_rings() -> None:
    segment_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        label="boundary with hole",
        intersection_id="intersection:t-01",
        status="ready",
        segment_count=5,
        segment_rows=[
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:outer-1",
                intersection_id="intersection:t-01",
                segment_kind="tie_in",
                segment_role="outer",
                start_xyz=(0.0, 0.0, 0.0),
                end_xyz=(20.0, 0.0, 0.0),
            ),
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:outer-2",
                intersection_id="intersection:t-01",
                segment_kind="tie_in",
                segment_role="outer",
                start_xyz=(20.0, 0.0, 0.0),
                end_xyz=(20.0, 20.0, 0.0),
            ),
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:outer-3",
                intersection_id="intersection:t-01",
                segment_kind="tie_in",
                segment_role="outer",
                start_xyz=(20.0, 20.0, 0.0),
                end_xyz=(0.0, 20.0, 0.0),
            ),
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:outer-4",
                intersection_id="intersection:t-01",
                segment_kind="tie_in",
                segment_role="outer",
                start_xyz=(0.0, 20.0, 0.0),
                end_xyz=(0.0, 0.0, 0.0),
            ),
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:hole-1",
                intersection_id="intersection:t-01",
                segment_kind="control_edge",
                segment_role="hole",
                chord_points_xyz=((8.0, 8.0, 0.0), (12.0, 8.0, 0.0), (12.0, 12.0, 0.0), (8.0, 12.0, 0.0)),
            ),
        ],
    )

    result = corridor_intersection_patch_boundary_result(segment_result)

    assert result.status == "ready"
    assert result.closed is True
    assert result.boundary_point_count == 8
    assert result.ring_count == 2
    assert result.outer_ring_count == 1
    assert result.hole_ring_count == 1
    assert result.island_ring_count == 0
    assert len([row for row in result.point_rows if row.ring_role == "outer"]) == 4
    assert len([row for row in result.point_rows if row.ring_role == "hole"]) == 4
    assert not any("holes_not_supported" in row for row in result.diagnostic_rows)
    assert result.polygon_area == 384.0


def test_intersection_exclusion_polygon_from_sources_includes_boundary_hole_rings() -> None:
    segment_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        label="boundary with hole",
        intersection_id="intersection:t-01",
        status="ready",
        segment_count=5,
        segment_rows=[
            IntersectionBoundarySegmentRow("boundary:outer-1", "intersection:t-01", "tie_in", segment_role="outer", start_xyz=(0.0, 0.0, 0.0), end_xyz=(20.0, 0.0, 0.0)),
            IntersectionBoundarySegmentRow("boundary:outer-2", "intersection:t-01", "tie_in", segment_role="outer", start_xyz=(20.0, 0.0, 0.0), end_xyz=(20.0, 20.0, 0.0)),
            IntersectionBoundarySegmentRow("boundary:outer-3", "intersection:t-01", "tie_in", segment_role="outer", start_xyz=(20.0, 20.0, 0.0), end_xyz=(0.0, 20.0, 0.0)),
            IntersectionBoundarySegmentRow("boundary:outer-4", "intersection:t-01", "tie_in", segment_role="outer", start_xyz=(0.0, 20.0, 0.0), end_xyz=(0.0, 0.0, 0.0)),
            IntersectionBoundarySegmentRow(
                "boundary:hole-1",
                "intersection:t-01",
                "control_edge",
                segment_role="hole",
                chord_points_xyz=((8.0, 8.0, 0.0), (12.0, 8.0, 0.0), (12.0, 12.0, 0.0), (8.0, 12.0, 0.0)),
            ),
        ],
    )
    result = corridor_intersection_patch_boundary_result(segment_result)

    holes = build_corridor_command._intersection_exclusion_rings_from_points(result, "hole")
    islands = build_corridor_command._intersection_exclusion_rings_from_points(result, "island")

    assert len(holes) == 1
    assert len(holes[0]) == 4
    assert islands == []


def test_corridor_intersection_patch_boundary_result_flags_hole_outside_outer_ring() -> None:
    segment_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        label="boundary with outside hole",
        intersection_id="intersection:t-01",
        status="ready",
        segment_count=5,
        segment_rows=[
            IntersectionBoundarySegmentRow("boundary:outer-1", "intersection:t-01", "tie_in", segment_role="outer", start_xyz=(0.0, 0.0, 0.0), end_xyz=(20.0, 0.0, 0.0)),
            IntersectionBoundarySegmentRow("boundary:outer-2", "intersection:t-01", "tie_in", segment_role="outer", start_xyz=(20.0, 0.0, 0.0), end_xyz=(20.0, 20.0, 0.0)),
            IntersectionBoundarySegmentRow("boundary:outer-3", "intersection:t-01", "tie_in", segment_role="outer", start_xyz=(20.0, 20.0, 0.0), end_xyz=(0.0, 20.0, 0.0)),
            IntersectionBoundarySegmentRow("boundary:outer-4", "intersection:t-01", "tie_in", segment_role="outer", start_xyz=(0.0, 20.0, 0.0), end_xyz=(0.0, 0.0, 0.0)),
            IntersectionBoundarySegmentRow(
                "boundary:hole-1",
                "intersection:t-01",
                "control_edge",
                segment_role="hole",
                chord_points_xyz=((30.0, 30.0, 0.0), (34.0, 30.0, 0.0), (34.0, 34.0, 0.0), (30.0, 34.0, 0.0)),
            ),
        ],
    )

    result = corridor_intersection_patch_boundary_result(segment_result)

    assert result.status == "warning"
    assert result.closed is False
    assert result.hole_ring_count == 1
    assert any("intersection_patch_boundary_inner_ring_outside_outer" in row for row in result.diagnostic_rows)


def test_corridor_intersection_patch_boundary_result_rejects_zero_area_polygon() -> None:
    segment_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        label="collinear boundary",
        intersection_id="intersection:t-01",
        status="ready",
        segment_count=3,
        segment_rows=[
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:1",
                intersection_id="intersection:t-01",
                segment_kind="tie_in",
                start_xyz=(0.0, 0.0, 0.0),
                end_xyz=(10.0, 0.0, 0.0),
            ),
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:2",
                intersection_id="intersection:t-01",
                segment_kind="tie_in",
                start_xyz=(10.0, 0.0, 0.0),
                end_xyz=(20.0, 0.0, 0.0),
            ),
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:3",
                intersection_id="intersection:t-01",
                segment_kind="tie_in",
                start_xyz=(20.0, 0.0, 0.0),
                end_xyz=(0.0, 0.0, 0.0),
            ),
        ],
    )

    result = corridor_intersection_patch_boundary_result(segment_result)

    assert result.status == "warning"
    assert result.closed is False
    assert result.polygon_area == 0.0
    assert any("intersection_patch_boundary_zero_area" in row for row in result.diagnostic_rows)


def test_intersection_ordered_polygon_triangulation_uses_long_edge_policy() -> None:
    vertices = [
        TINVertex("v1", 0.0, 0.0, 0.0),
        TINVertex("v2", 20.0, 0.0, 0.0),
        TINVertex("v3", 20.0, 4.0, 0.0),
        TINVertex("v4", 0.0, 4.0, 0.0),
    ]
    center = TINVertex("v:center", 10.0, 2.0, 0.0)

    default_result = build_corridor_command._intersection_patch_ordered_polygon_triangulation(
        vertices,
        center,
        intersection_id="intersection:t-01",
    )
    strict_result = build_corridor_command._intersection_patch_ordered_polygon_triangulation(
        vertices,
        center,
        intersection_id="intersection:t-01",
        policy={"max_boundary_edge_length": 10.0, "long_edge_factor": 2.5},
    )

    assert default_result["long_edge_count"] == 0
    assert len(default_result["triangles"]) == 2
    assert {triangle.quality_ref for triangle in default_result["triangles"]} == {"ordered_polygon"}
    assert strict_result["long_edge_count"] == 2
    assert strict_result["long_edge_limit"] == 10.0
    assert strict_result["max_boundary_edge_length_policy"] == 10.0


def test_intersection_exclusion_clips_tin_triangles_by_centroid() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:test",
        surface_kind="design_surface",
        vertex_rows=[
            TINVertex("v1", 0.0, 0.0, 0.0),
            TINVertex("v2", 10.0, 0.0, 0.0),
            TINVertex("v3", 0.0, 10.0, 0.0),
            TINVertex("v4", 10.0, 10.0, 0.0),
        ],
        triangle_rows=[
            TINTriangle("t1", "v1", "v2", "v3"),
            TINTriangle("t2", "v2", "v4", "v3"),
        ],
    )
    original_provider = build_corridor_command._intersection_exclusion_polygon_from_sources
    build_corridor_command._intersection_exclusion_polygon_from_sources = lambda *args, **kwargs: {
        "intersection_id": "intersection:t-01",
        "status": "ready",
        "points": [(-1.0, -1.0), (8.0, -1.0), (-1.0, 8.0)],
        "area": 40.5,
    }
    try:
        clipped = build_corridor_command._clip_tin_surface_by_intersection_exclusion(
            surface,
            None,
            surface_role="design",
        )
    finally:
        build_corridor_command._intersection_exclusion_polygon_from_sources = original_provider

    assert len(clipped.triangle_rows) == 3
    assert [row.quality_ref for row in clipped.triangle_rows[:2]] == [
        "intersection_exclusion_exact_cut",
        "intersection_exclusion_exact_cut",
    ]
    assert clipped.triangle_rows[-1].triangle_id == "t2"
    assert "intersection:t-01" in clipped.void_refs
    assert build_corridor_command._tin_quality_text(clipped, "intersection_exclusion_boundary_source") == "patch_boundary"
    assert build_corridor_command._tin_quality_text(clipped, "intersection_exclusion_boundary_strategy") == "ordered_patch_boundary"
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_practical_boundary_aligned") == 0
    assert build_corridor_command._tin_quality_text(clipped, "intersection_exclusion_clip_method") == "exact_convex_polygon"
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_clipped_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_kept_triangle_count") == 3
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_candidate_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_generated_triangle_count") == 2
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_recommended") == 0


def test_intersection_exclusion_clips_tin_triangles_crossing_polygon_edges() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:test",
        surface_kind="design_surface",
        vertex_rows=[
            TINVertex("v1", -2.0, 1.0, 0.0),
            TINVertex("v2", 8.0, 1.0, 0.0),
            TINVertex("v3", 3.0, 8.0, 0.0),
            TINVertex("v4", 20.0, 20.0, 0.0),
            TINVertex("v5", 25.0, 20.0, 0.0),
            TINVertex("v6", 20.0, 25.0, 0.0),
        ],
        triangle_rows=[
            TINTriangle("t-crossing", "v1", "v2", "v3"),
            TINTriangle("t-outside", "v4", "v5", "v6"),
        ],
    )
    original_provider = build_corridor_command._intersection_exclusion_polygon_from_sources
    build_corridor_command._intersection_exclusion_polygon_from_sources = lambda *args, **kwargs: {
        "intersection_id": "intersection:t-01",
        "status": "ready",
        "points": [(0.0, 0.0), (2.0, 0.0), (0.0, 2.0)],
        "area": 2.0,
    }
    try:
        clipped = build_corridor_command._clip_tin_surface_by_intersection_exclusion(
            surface,
            None,
            surface_role="design",
        )
    finally:
        build_corridor_command._intersection_exclusion_polygon_from_sources = original_provider

    assert len(clipped.triangle_rows) == 5
    assert [row.quality_ref for row in clipped.triangle_rows[:4]] == [
        "intersection_exclusion_exact_cut",
        "intersection_exclusion_exact_cut",
        "intersection_exclusion_exact_cut",
        "intersection_exclusion_exact_cut",
    ]
    assert clipped.triangle_rows[-1].triangle_id == "t-outside"
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_clipped_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_kept_triangle_count") == 5
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_boundary_crossing_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_candidate_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_generated_triangle_count") == 4


def test_intersection_exclusion_hard_suppresses_daylight_triangles_without_fragments() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("v1", -2.0, 1.0, 0.0),
            TINVertex("v2", 8.0, 1.0, 0.0),
            TINVertex("v3", 3.0, 8.0, 0.0),
            TINVertex("v4", 20.0, 20.0, 0.0),
            TINVertex("v5", 25.0, 20.0, 0.0),
            TINVertex("v6", 20.0, 25.0, 0.0),
        ],
        triangle_rows=[
            TINTriangle("t-crossing", "v1", "v2", "v3"),
            TINTriangle("t-outside", "v4", "v5", "v6"),
        ],
    )
    original_provider = build_corridor_command._intersection_exclusion_polygon_from_sources
    build_corridor_command._intersection_exclusion_polygon_from_sources = lambda *args, **kwargs: {
        "intersection_id": "intersection:t-01",
        "status": "ready",
        "points": [(0.0, 0.0), (2.0, 0.0), (0.0, 2.0)],
        "area": 2.0,
        "boundary_source": "practical_intersection_surface_boundary",
        "boundary_strategy": "structured_strip_curb_return_blend",
        "practical_boundary_aligned": True,
    }
    try:
        clipped = build_corridor_command._clip_tin_surface_by_intersection_exclusion(
            surface,
            None,
            surface_role="daylight",
        )
    finally:
        build_corridor_command._intersection_exclusion_polygon_from_sources = original_provider

    assert len(clipped.triangle_rows) == 1
    assert clipped.triangle_rows[0].triangle_id == "t-outside"
    assert build_corridor_command._tin_quality_text(clipped, "intersection_exclusion_clip_method") == "hard_suppress_intersection"
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_clipped_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_kept_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_candidate_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_recommended") == 0
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_generated_triangle_count") == 0
    assert build_corridor_command._tin_quality_text(clipped, "intersection_exclusion_boundary_strategy") == "structured_strip_curb_return_blend"
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_practical_boundary_aligned") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_daylight_protection_offset") >= 4.0


def test_intersection_height_clip_suppresses_only_daylight_triangles_above_intersection_surface() -> None:
    intersection_surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:intersection",
        surface_kind="intersection_surface",
        vertex_rows=[
            TINVertex("i1", 0.0, 0.0, 10.0),
            TINVertex("i2", 10.0, 0.0, 10.0),
            TINVertex("i3", 0.0, 10.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("it1", "i1", "i2", "i3"),
        ],
    )
    daylight_surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("a1", 1.0, 1.0, 10.2),
            TINVertex("a2", 2.0, 1.0, 10.2),
            TINVertex("a3", 1.0, 2.0, 10.2),
            TINVertex("b1", 3.0, 1.0, 9.8),
            TINVertex("b2", 4.0, 1.0, 9.8),
            TINVertex("b3", 3.0, 2.0, 9.8),
            TINVertex("c1", 20.0, 20.0, 20.0),
            TINVertex("c2", 21.0, 20.0, 20.0),
            TINVertex("c3", 20.0, 21.0, 20.0),
        ],
        triangle_rows=[
            TINTriangle("above", "a1", "a2", "a3"),
            TINTriangle("below", "b1", "b2", "b3"),
            TINTriangle("outside", "c1", "c2", "c3"),
        ],
    )

    clipped = build_corridor_command._suppress_daylight_triangles_above_intersection_surface(
        daylight_surface,
        intersection_surface,
        tolerance=0.05,
    )

    assert [row.triangle_id for row in clipped.triangle_rows] == ["below", "outside"]
    assert "surface:intersection" in clipped.void_refs
    assert build_corridor_command._tin_quality_text(clipped, "intersection_height_clip_status") == "ready"
    assert build_corridor_command._tin_quality_float(clipped, "intersection_height_clip_tested_triangle_count") == 2
    assert build_corridor_command._tin_quality_float(clipped, "intersection_height_clip_suppressed_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_height_clip_kept_triangle_count") == 2


def test_intersection_footprint_suppresses_daylight_triangles_inside_intersection_surface_even_when_lower() -> None:
    intersection_surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:intersection",
        surface_kind="intersection_surface",
        vertex_rows=[
            TINVertex("i1", 0.0, 0.0, 10.0),
            TINVertex("i2", 10.0, 0.0, 10.0),
            TINVertex("i3", 0.0, 10.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("it1", "i1", "i2", "i3"),
        ],
    )
    daylight_surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("inside1", 1.0, 1.0, 8.0),
            TINVertex("inside2", 2.0, 1.0, 8.0),
            TINVertex("inside3", 1.0, 2.0, 8.0),
            TINVertex("outside1", 20.0, 20.0, 8.0),
            TINVertex("outside2", 21.0, 20.0, 8.0),
            TINVertex("outside3", 20.0, 21.0, 8.0),
        ],
        triangle_rows=[
            TINTriangle("inside-footprint", "inside1", "inside2", "inside3"),
            TINTriangle("outside-footprint", "outside1", "outside2", "outside3"),
        ],
    )

    clipped = build_corridor_command._suppress_daylight_triangles_inside_intersection_surface_footprint(
        daylight_surface,
        intersection_surface,
    )

    assert [row.triangle_id for row in clipped.triangle_rows] == ["outside-footprint"]
    assert "surface:intersection" in clipped.void_refs
    assert build_corridor_command._tin_quality_text(clipped, "intersection_footprint_suppress_status") == "ready"
    assert build_corridor_command._tin_quality_text(clipped, "intersection_footprint_suppress_method") == "sample_xy_footprint"
    assert build_corridor_command._tin_quality_float(clipped, "intersection_footprint_suppress_tested_triangle_count") == 2
    assert build_corridor_command._tin_quality_float(clipped, "intersection_footprint_suppress_suppressed_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_footprint_suppress_kept_triangle_count") == 1


def test_intersection_slope_face_overlap_edges_mark_only_xy_overlap_triangles() -> None:
    intersection_surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:intersection",
        surface_kind="intersection_surface",
        vertex_rows=[
            TINVertex("i1", 0.0, 0.0, 10.0),
            TINVertex("i2", 10.0, 0.0, 10.0),
            TINVertex("i3", 0.0, 10.0, 10.0),
        ],
        triangle_rows=[TINTriangle("it1", "i1", "i2", "i3")],
    )
    daylight_surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("a1", 1.0, 1.0, 9.0),
            TINVertex("a2", 3.0, 1.0, 11.0),
            TINVertex("a3", 1.0, 3.0, 11.0),
            TINVertex("b1", 20.0, 20.0, 9.5),
            TINVertex("b2", 21.0, 20.0, 9.5),
            TINVertex("b3", 20.0, 21.0, 9.5),
        ],
        triangle_rows=[
            TINTriangle("overlap", "a1", "a2", "a3"),
            TINTriangle("outside", "b1", "b2", "b3"),
        ],
    )

    segments, triangle_count = build_corridor_command._intersection_slope_face_overlap_edge_segments(
        daylight_surface,
        intersection_surface,
        z_offset=0.08,
    )

    assert triangle_count == 1
    assert len(segments) == 1
    start, end = segments[0]
    assert {round(start[2], 3), round(end[2], 3)} == {10.08}
    assert {
        (round(start[0], 3), round(start[1], 3)),
        (round(end[0], 3), round(end[1], 3)),
    } == {(2.0, 1.0), (1.0, 2.0)}


def test_intersection_slope_trim_removes_intersecting_daylight_triangle_above_intersection_surface() -> None:
    intersection_surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:intersection",
        surface_kind="intersection_surface",
        vertex_rows=[
            TINVertex("i1", 0.0, 0.0, 10.0),
            TINVertex("i2", 10.0, 0.0, 10.0),
            TINVertex("i3", 0.0, 10.0, 10.0),
        ],
        triangle_rows=[TINTriangle("it1", "i1", "i2", "i3")],
    )
    daylight_surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("a1", 1.0, 1.0, 9.0),
            TINVertex("a2", 3.0, 1.0, 11.0),
            TINVertex("a3", 1.0, 3.0, 11.0),
            TINVertex("b1", 20.0, 20.0, 9.5),
            TINVertex("b2", 21.0, 20.0, 9.5),
            TINVertex("b3", 20.0, 21.0, 9.5),
        ],
        triangle_rows=[
            TINTriangle("intersecting-above", "a1", "a2", "a3"),
            TINTriangle("outside", "b1", "b2", "b3"),
        ],
    )

    trimmed = build_corridor_command._trim_daylight_triangles_above_intersection_surface_by_intersection_lines(
        daylight_surface,
        intersection_surface,
        tolerance=0.05,
    )

    assert [row.triangle_id for row in trimmed.triangle_rows] == ["outside"]
    assert build_corridor_command._tin_quality_text(trimmed, "intersection_slope_trim_status") == "ready"
    assert build_corridor_command._tin_quality_text(trimmed, "intersection_slope_trim_method") == "coarse_remove_intersecting_above_triangles"
    assert build_corridor_command._tin_quality_float(trimmed, "intersection_slope_trim_intersecting_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(trimmed, "intersection_slope_trim_removed_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(trimmed, "intersection_slope_trim_kept_triangle_count") == 1


def test_intersection_side_slope_strip_fills_boundary_gap_from_applied_sections() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("b1", 0.0, 1.0, 10.0),
            TINVertex("b2", 10.0, 1.0, 10.0),
            TINVertex("b3", 0.0, 2.0, 10.0),
            TINVertex("b4", 10.0, 2.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("existing-a", "b1", "b2", "b4"),
            TINTriangle("existing-b", "b1", "b4", "b3"),
        ],
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                alignment_id="alignment:main",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=2.0,
                daylight_left_width=2.0,
                daylight_left_slope=-0.25,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:10",
                alignment_id="alignment:main",
                station=10.0,
                frame=AppliedSectionFrame(station=10.0, x=10.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=2.0,
                daylight_left_width=2.0,
                daylight_left_slope=-0.25,
            ),
        ],
    )

    augmented = build_corridor_command._augment_daylight_surface_with_applied_section_side_slope_strips(
        surface,
        applied,
    )

    strip_triangles = [
        triangle for triangle in augmented.triangle_rows
        if triangle.triangle_kind == "intersection_side_slope_strip"
    ]
    assert len(strip_triangles) == 2
    assert build_corridor_command._tin_quality_text(augmented, "intersection_side_slope_strip_status") == "ready"
    assert build_corridor_command._tin_quality_float(augmented, "intersection_side_slope_strip_count") == 1
    assert build_corridor_command._tin_quality_float(augmented, "intersection_side_slope_strip_triangle_count") == 2
    assert build_corridor_command._tin_quality_text(augmented, "intersection_side_slope_strip_output_path") == "applied_section_side_slope_edges"


def test_intersection_side_slope_strip_does_not_duplicate_existing_surface() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("i1", 0.0, 2.0, 10.0),
            TINVertex("i2", 10.0, 2.0, 10.0),
            TINVertex("o1", 0.0, 4.0, 9.5),
            TINVertex("o2", 10.0, 4.0, 9.5),
        ],
        triangle_rows=[
            TINTriangle("existing-a", "i1", "i2", "o2"),
            TINTriangle("existing-b", "i1", "o2", "o1"),
        ],
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                alignment_id="alignment:main",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=2.0,
                daylight_left_width=2.0,
                daylight_left_slope=-0.25,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:10",
                alignment_id="alignment:main",
                station=10.0,
                frame=AppliedSectionFrame(station=10.0, x=10.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=2.0,
                daylight_left_width=2.0,
                daylight_left_slope=-0.25,
            ),
        ],
    )

    augmented = build_corridor_command._augment_daylight_surface_with_applied_section_side_slope_strips(
        surface,
        applied,
    )

    assert len(augmented.triangle_rows) == 2
    assert build_corridor_command._tin_quality_text(augmented, "intersection_side_slope_strip_status") == "not_needed"
    assert build_corridor_command._tin_quality_float(augmented, "intersection_side_slope_strip_count") == 0
    assert build_corridor_command._tin_quality_float(augmented, "intersection_side_slope_strip_skipped_existing_count") == 1


def test_intersection_side_slope_restore_uses_preclip_reference_without_filling_patch() -> None:
    current = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("u1", 0.0, 4.0, 10.0),
            TINVertex("u2", 10.0, 4.0, 10.0),
            TINVertex("u3", 0.0, 6.0, 9.5),
            TINVertex("u4", 10.0, 6.0, 9.5),
            TINVertex("p1", 0.0, 0.0, 10.0),
            TINVertex("p2", 10.0, 0.0, 10.0),
            TINVertex("p3", 0.0, 2.0, 9.5),
            TINVertex("p4", 10.0, 2.0, 9.5),
        ],
        triangle_rows=[],
    )
    reference = replace(
        current,
        triangle_rows=[
            TINTriangle("upper-a", "u1", "u2", "u4", triangle_kind="corridor_daylight_bench_strip"),
            TINTriangle("upper-b", "u1", "u4", "u3", triangle_kind="corridor_daylight_bench_strip"),
            TINTriangle("patch-a", "p1", "p2", "p4", triangle_kind="corridor_daylight_bench_strip"),
        ],
    )
    intersection = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:intersection",
        surface_kind="intersection_surface",
        vertex_rows=[
            TINVertex("i1", -1.0, -1.0, 10.0),
            TINVertex("i2", 11.0, -1.0, 10.0),
            TINVertex("i3", 11.0, 3.0, 10.0),
            TINVertex("i4", -1.0, 3.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("intersection-a", "i1", "i2", "i3"),
            TINTriangle("intersection-b", "i1", "i3", "i4"),
        ],
    )

    restored = build_corridor_command._restore_daylight_surface_side_slope_strips_from_reference(
        current,
        reference,
        intersection_tin_surface=intersection,
    )

    restored_ids = {triangle.triangle_id for triangle in restored.triangle_rows}
    assert restored_ids == {"upper-a", "upper-b"}
    assert all(triangle.quality_ref == "intersection_side_slope_strip" for triangle in restored.triangle_rows)
    assert build_corridor_command._tin_quality_text(restored, "intersection_side_slope_reference_restore_status") == "ready"
    assert build_corridor_command._tin_quality_float(restored, "intersection_side_slope_reference_restore_triangle_count") == 2
    assert build_corridor_command._tin_quality_float(restored, "intersection_side_slope_reference_restore_skipped_intersection_count") == 1
    assert build_corridor_command._tin_quality_text(restored, "intersection_side_slope_reference_restore_output_path") == "preclip_side_slope_tin"


def test_intersection_exclusion_suppresses_daylight_triangles_near_junction_gap() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight-gap",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("v1", 2.8, 0.2, 0.0),
            TINVertex("v2", 3.8, 0.2, 0.0),
            TINVertex("v3", 2.8, 1.2, 0.0),
            TINVertex("v4", 8.0, 8.0, 0.0),
            TINVertex("v5", 9.0, 8.0, 0.0),
            TINVertex("v6", 8.0, 9.0, 0.0),
        ],
        triangle_rows=[
            TINTriangle("t-near-gap", "v1", "v2", "v3"),
            TINTriangle("t-outside", "v4", "v5", "v6"),
        ],
    )
    original_provider = build_corridor_command._intersection_exclusion_polygon_from_sources
    build_corridor_command._intersection_exclusion_polygon_from_sources = lambda *args, **kwargs: {
        "intersection_id": "intersection:t-01",
        "status": "ready",
        "points": [(0.0, 0.0), (2.0, 0.0), (0.0, 2.0)],
        "area": 2.0,
        "boundary_source": "practical_intersection_surface_boundary",
        "boundary_strategy": "structured_strip_curb_return_blend",
        "practical_boundary_aligned": True,
    }
    try:
        clipped = build_corridor_command._clip_tin_surface_by_intersection_exclusion(
            surface,
            None,
            surface_role="daylight",
        )
    finally:
        build_corridor_command._intersection_exclusion_polygon_from_sources = original_provider

    assert len(clipped.triangle_rows) == 1
    assert clipped.triangle_rows[0].triangle_id == "t-outside"
    assert build_corridor_command._tin_quality_text(clipped, "intersection_exclusion_clip_method") == "hard_suppress_intersection"
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_clipped_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_daylight_protection_offset") >= 4.0


def test_intersection_exclusion_suppresses_daylight_triangles_intruding_into_pavement_strip() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight-pavement-strip",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("v1", 11.0, 2.0, 0.0),
            TINVertex("v2", 13.0, 2.0, 0.0),
            TINVertex("v3", 11.0, 4.0, 0.0),
            TINVertex("v4", 80.0, 80.0, 0.0),
            TINVertex("v5", 81.0, 80.0, 0.0),
            TINVertex("v6", 80.0, 81.0, 0.0),
        ],
        triangle_rows=[
            TINTriangle("t-in-pavement-strip", "v1", "v2", "v3"),
            TINTriangle("t-outside", "v4", "v5", "v6"),
        ],
    )
    original_provider = build_corridor_command._intersection_exclusion_polygon_from_sources
    build_corridor_command._intersection_exclusion_polygon_from_sources = lambda *args, **kwargs: {
        "intersection_id": "intersection:t-01",
        "status": "ready",
        "points": [(0.0, 0.0), (2.0, 0.0), (0.0, 2.0)],
        "area": 2.0,
        "boundary_source": "practical_intersection_surface_boundary",
        "boundary_strategy": "structured_strip_curb_return_blend",
        "practical_boundary_aligned": True,
        "pavement_strip_polygons": [[(10.0, 0.0), (20.0, 0.0), (20.0, 10.0), (10.0, 10.0)]],
    }
    try:
        clipped = build_corridor_command._clip_tin_surface_by_intersection_exclusion(
            surface,
            None,
            surface_role="daylight",
        )
    finally:
        build_corridor_command._intersection_exclusion_polygon_from_sources = original_provider

    assert len(clipped.triangle_rows) == 1
    assert clipped.triangle_rows[0].triangle_id == "t-outside"
    assert build_corridor_command._tin_quality_text(clipped, "intersection_exclusion_clip_method") == "hard_suppress_intersection"
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_clipped_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_control_section_clipped_triangle_count") == 1


def test_intersection_exclusion_suppresses_daylight_triangles_from_intersection_control_sections() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        sections=[
            AppliedSection(schema_version=1, project_id="proj-1", applied_section_id="section:0", station=0.0, frame=AppliedSectionFrame(station=0.0)),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:1",
                station=10.0,
                frame=AppliedSectionFrame(station=10.0),
                region_id="region:primary-intersection",
                active_intersection_id="intersection:t-01",
                active_intersection_control_region_refs=["region:primary-intersection", "region:side-intersection"],
            ),
            AppliedSection(schema_version=1, project_id="proj-1", applied_section_id="section:2", station=20.0, frame=AppliedSectionFrame(station=20.0)),
        ],
    )
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight-control",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("group:primary:v1:left:r0:p0", 2.8, 0.2, 0.0),
            TINVertex("group:primary:v1:left:r0:p1", 3.8, 0.2, 0.0),
            TINVertex("group:primary:v1:left:r1:p0", 2.8, 1.2, 0.0),
            TINVertex("group:primary:v2:left:r0:p0", 200.0, 200.0, 0.0),
            TINVertex("group:primary:v2:left:r0:p1", 201.0, 200.0, 0.0),
            TINVertex("group:primary:v2:left:r1:p0", 200.0, 201.0, 0.0),
        ],
        triangle_rows=[
            TINTriangle(
                "group:primary:span:1:left:r0:p0:a",
                "group:primary:v1:left:r0:p0",
                "group:primary:v1:left:r0:p1",
                "group:primary:v1:left:r1:p0",
            ),
            TINTriangle(
                "group:primary:span:2:left:r0:p0:a",
                "group:primary:v2:left:r0:p0",
                "group:primary:v2:left:r0:p1",
                "group:primary:v2:left:r1:p0",
            ),
        ],
    )
    original_provider = build_corridor_command._intersection_exclusion_polygon_from_sources
    build_corridor_command._intersection_exclusion_polygon_from_sources = lambda *args, **kwargs: {
        "intersection_id": "intersection:t-01",
        "status": "ready",
        "points": [(0.0, 0.0), (2.0, 0.0), (0.0, 2.0)],
        "area": 2.0,
        "boundary_source": "practical_intersection_surface_boundary",
        "boundary_strategy": "structured_strip_curb_return_blend",
        "practical_boundary_aligned": True,
    }
    try:
        clipped = build_corridor_command._clip_tin_surface_by_intersection_exclusion(
            surface,
            None,
            applied_section_set=applied,
            surface_role="daylight",
        )
    finally:
        build_corridor_command._intersection_exclusion_polygon_from_sources = original_provider

    assert [row.triangle_id for row in clipped.triangle_rows] == ["group:primary:span:2:left:r0:p0:a"]
    assert build_corridor_command._tin_quality_text(clipped, "intersection_exclusion_clip_method") == "hard_suppress_intersection"
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_clipped_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_control_section_clipped_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_candidate_count") == 0


def test_intersection_exclusion_uses_region_source_sections_for_region_daylight_surfaces() -> None:
    full_applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:full",
        sections=[
            AppliedSection(schema_version=1, project_id="proj-1", applied_section_id="full:0", station=0.0, frame=AppliedSectionFrame(station=0.0)),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="full:1",
                station=10.0,
                frame=AppliedSectionFrame(station=10.0),
                active_intersection_id="intersection:t-01",
            ),
            AppliedSection(schema_version=1, project_id="proj-1", applied_section_id="full:2", station=20.0, frame=AppliedSectionFrame(station=20.0)),
        ],
    )
    region_subset = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:region",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="region:0",
                station=10.0,
                frame=AppliedSectionFrame(station=10.0),
                active_intersection_id="intersection:t-01",
            ),
            AppliedSection(schema_version=1, project_id="proj-1", applied_section_id="region:1", station=20.0, frame=AppliedSectionFrame(station=20.0)),
        ],
    )
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:region-daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("v0:left:r0:p0", 2.8, 0.2, 0.0),
            TINVertex("v0:left:r0:p1", 3.8, 0.2, 0.0),
            TINVertex("v0:left:r1:p0", 2.8, 1.2, 0.0),
            TINVertex("v1:left:r0:p0", 200.0, 200.0, 0.0),
            TINVertex("v1:left:r0:p1", 201.0, 200.0, 0.0),
            TINVertex("v1:left:r1:p0", 200.0, 201.0, 0.0),
        ],
        triangle_rows=[
            TINTriangle("span:0:left:r0:p0:a", "v0:left:r0:p0", "v0:left:r0:p1", "v0:left:r1:p0"),
            TINTriangle("span:1:left:r0:p0:a", "v1:left:r0:p0", "v1:left:r0:p1", "v1:left:r1:p0"),
        ],
    )
    original_provider = build_corridor_command._intersection_exclusion_polygon_from_sources
    build_corridor_command._intersection_exclusion_polygon_from_sources = lambda *args, **kwargs: {
        "intersection_id": "intersection:t-01",
        "status": "ready",
        "points": [(0.0, 0.0), (2.0, 0.0), (0.0, 2.0)],
        "area": 2.0,
        "boundary_source": "practical_intersection_surface_boundary",
        "boundary_strategy": "structured_strip_curb_return_blend",
        "practical_boundary_aligned": True,
    }
    try:
        clipped = build_corridor_command._clip_tin_surface_by_intersection_exclusion(
            surface,
            None,
            applied_section_set=full_applied,
            source_applied_section_set=region_subset,
            surface_role="daylight",
        )
    finally:
        build_corridor_command._intersection_exclusion_polygon_from_sources = original_provider

    assert [row.triangle_id for row in clipped.triangle_rows] == ["span:1:left:r0:p0:a"]
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_control_section_clipped_triangle_count") == 1


def test_region_design_and_subgrade_surfaces_use_intersection_exclusion() -> None:
    assert build_corridor_command._region_surface_role_uses_intersection_exclusion("design") is True
    assert build_corridor_command._region_surface_role_uses_intersection_exclusion("subgrade") is True
    assert build_corridor_command._region_surface_role_uses_intersection_exclusion("daylight") is True
    assert build_corridor_command._region_surface_role_uses_intersection_exclusion("drainage") is False


def test_slope_face_issue_rows_ignore_vertices_removed_from_clipped_triangles() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight-clipped",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("v0:left:outer", 0.0, 0.0, 0.0, notes="fallback:no_eg_hit_in_search_width"),
            TINVertex("v0:left:inner", 0.0, 1.0, 0.0),
            TINVertex("v1:right:outer", 10.0, 0.0, 0.0, notes="fallback:no_eg_hit_in_search_width"),
            TINVertex("v1:right:inner", 10.0, 1.0, 0.0),
            TINVertex("v1:center", 10.0, 0.5, 0.0),
        ],
        triangle_rows=[
            TINTriangle("t-kept", "v1:right:outer", "v1:right:inner", "v1:center"),
        ],
    )

    rows = build_corridor_command._slope_face_issue_station_rows(surface)

    assert [row["marker_object"] for row in rows] == ["ReviewIssueSlopeFaceIssue002R"]


def test_intersection_tie_in_generated_section_projects_to_nearest_alignment_span() -> None:
    first = AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id="section:side-100",
        corridor_id="corridor:main",
        alignment_id="alignment:side",
        region_id="region:side-intersection",
        station=100.0,
        frame=AppliedSectionFrame(station=100.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
        surface_left_width=5.0,
        surface_right_width=5.0,
        daylight_left_width=3.0,
        daylight_right_width=3.0,
        daylight_left_slope=-0.5,
        daylight_right_slope=-0.5,
        point_rows=[
            AppliedSectionPoint("fg:left:100", 0.0, 5.0, 10.0, "fg_surface", 5.0),
            AppliedSectionPoint("fg:right:100", 0.0, -5.0, 10.0, "fg_surface", -5.0),
        ],
    )
    second = AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id="section:side-120",
        corridor_id="corridor:main",
        alignment_id="alignment:side",
        region_id="region:side-intersection",
        station=120.0,
        frame=AppliedSectionFrame(station=120.0, x=20.0, y=0.0, z=12.0, tangent_direction_deg=0.0),
        surface_left_width=5.0,
        surface_right_width=5.0,
        daylight_left_width=3.0,
        daylight_right_width=3.0,
        daylight_left_slope=-0.5,
        daylight_right_slope=-0.5,
        point_rows=[
            AppliedSectionPoint("fg:left:120", 20.0, 5.0, 12.0, "fg_surface", 5.0),
            AppliedSectionPoint("fg:right:120", 20.0, -5.0, 12.0, "fg_surface", -5.0),
        ],
    )

    generated = build_corridor_command._intersection_tie_in_generated_section_for_point(
        (10.0, 2.5, 0.0),
        {"alignment:side": [first, second]},
        intersection_id="intersection:t-01",
        source_index=3,
    )

    assert generated is not None
    assert generated.applied_section_id == "section:intersection-tie-in:intersection_t_01:alignment_side:3"
    assert generated.alignment_id == "alignment:side"
    assert generated.region_id == "region:side-intersection"
    assert generated.station == 110.0
    assert generated.frame.x == 10.0
    assert generated.frame.z == 11.0
    assert generated.active_intersection_id == "intersection:t-01"
    assert generated.active_intersection_leg_role == "tie_in_generated"
    assert any("generated_intersection_tie_in_section" in row for row in generated.intersection_diagnostic_rows)


def test_intersection_curb_return_boundary_adds_slope_band_without_caps_or_bridges() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[],
        triangle_rows=[],
    )
    boundary_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        intersection_id="intersection:t-01",
        status="ready",
        segment_rows=[
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:curb-return:1",
                intersection_id="intersection:t-01",
                segment_kind="arc",
                segment_role="curb_return",
                center_xyz=(0.0, 0.0, 10.0),
                chord_points_xyz=((3.0, 0.0, 10.0), (2.121, 2.121, 10.0), (0.0, 3.0, 10.0)),
            )
        ],
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:1",
                daylight_left_width=3.5,
                daylight_left_slope=0.25,
            )
        ],
    )

    augmented = build_corridor_command._augment_daylight_surface_with_curb_return_boundary_bands(
        surface,
        boundary_result,
        applied_section_set=applied,
    )

    assert len(augmented.vertex_rows) == 6
    assert len(augmented.triangle_rows) == 4
    assert build_corridor_command._tin_quality_float(augmented, "intersection_curb_return_slope_band_edge_count") == 2
    assert build_corridor_command._tin_quality_float(augmented, "intersection_curb_return_slope_band_triangle_count") == 4
    assert build_corridor_command._tin_quality_float(augmented, "intersection_curb_return_slope_band_width") == 3.5
    assert all(row.quality_ref == "intersection_curb_return_slope_band" for row in augmented.triangle_rows)
    assert not any("cap" in row.quality_ref or "bridge" in row.quality_ref for row in augmented.triangle_rows)
    vertex_map = augmented.vertex_map()
    for triangle in augmented.triangle_rows:
        assert build_corridor_command._xy_triangle_area(
            vertex_map[triangle.v1],
            vertex_map[triangle.v2],
            vertex_map[triangle.v3],
        ) >= 0.0


def test_intersection_curb_return_slope_band_connects_to_side_applied_section_edge() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("existing:side:inner", -1.0, 3.0, 10.0),
            TINVertex("existing:side:outer", -1.0, 6.5, 9.125),
            TINVertex("existing:side:tail", -5.0, 4.5, 9.5),
        ],
        triangle_rows=[
            TINTriangle("existing:side:slope", "existing:side:inner", "existing:side:outer", "existing:side:tail"),
        ],
    )
    boundary_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        intersection_id="intersection:t-01",
        status="ready",
        segment_rows=[
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:curb-return:1",
                intersection_id="intersection:t-01",
                segment_kind="arc",
                segment_role="curb_return",
                center_xyz=(0.0, 0.0, 10.0),
                chord_points_xyz=((3.0, 0.0, 10.0), (2.121, 2.121, 10.0), (0.0, 3.0, 10.0)),
            )
        ],
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-contact",
                alignment_id="alignment:side",
                station=100.0,
                active_intersection_id="intersection:t-01",
                active_intersection_leg_role="side_road",
                frame=AppliedSectionFrame(station=100.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=3.0,
                surface_right_width=3.0,
                daylight_left_width=3.5,
                daylight_right_width=0.0,
                daylight_left_slope=-0.25,
            )
        ],
    )

    augmented = build_corridor_command._augment_daylight_surface_with_curb_return_boundary_bands(
        surface,
        boundary_result,
        applied_section_set=applied,
    )

    assert build_corridor_command._tin_quality_float(augmented, "intersection_curb_return_slope_band_triangle_count") == 4
    assert build_corridor_command._tin_quality_float(augmented, "intersection_slope_tie_in_edge_count") >= 1
    assert build_corridor_command._tin_quality_float(augmented, "intersection_slope_tie_in_triangle_count") >= 2
    assert build_corridor_command._tin_quality_float(augmented, "intersection_side_slope_extension_edge_count") >= 2
    assert build_corridor_command._tin_quality_float(augmented, "intersection_side_slope_extension_triangle_count") >= 4
    assert len([row for row in augmented.triangle_rows if row.quality_ref == "intersection_slope_tie_in"]) >= 2
    assert len([row for row in augmented.triangle_rows if row.quality_ref == "intersection_side_slope_extension"]) >= 4
    assert any("section:side-contact" in row.notes for row in augmented.triangle_rows if row.quality_ref == "intersection_slope_tie_in")


def test_intersection_slope_tie_in_is_not_preblocked_by_pavement_strip() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[],
        triangle_rows=[],
    )
    boundary_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        intersection_id="intersection:t-01",
        status="ready",
        segment_rows=[
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:curb-return:1",
                intersection_id="intersection:t-01",
                segment_kind="arc",
                segment_role="curb_return",
                center_xyz=(0.0, 0.0, 10.0),
                chord_points_xyz=((3.0, 0.0, 10.0), (2.121, 2.121, 10.0), (0.0, 3.0, 10.0)),
            ),
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:pavement:a",
                intersection_id="intersection:t-01",
                segment_kind="tie_in",
                segment_role="pavement_edge",
                alignment_ref="alignment:primary",
                start_xyz=(-2.0, -1.0, 10.0),
                end_xyz=(5.0, -1.0, 10.0),
            ),
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:pavement:b",
                intersection_id="intersection:t-01",
                segment_kind="tie_in",
                segment_role="pavement_edge",
                alignment_ref="alignment:primary",
                start_xyz=(-2.0, 7.0, 10.0),
                end_xyz=(5.0, 7.0, 10.0),
            ),
        ],
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-contact",
                alignment_id="alignment:side",
                station=100.0,
                active_intersection_id="intersection:t-01",
                active_intersection_leg_role="side_road",
                frame=AppliedSectionFrame(station=100.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=3.0,
                daylight_left_width=3.5,
                daylight_left_slope=-0.25,
            )
        ],
    )

    augmented = build_corridor_command._augment_daylight_surface_with_curb_return_boundary_bands(
        surface,
        boundary_result,
        applied_section_set=applied,
    )

    assert build_corridor_command._tin_quality_float(augmented, "intersection_slope_tie_in_edge_count") >= 1
    assert any(
        "section:side-contact" in row.notes
        for row in augmented.triangle_rows
        if row.quality_ref == "intersection_slope_tie_in"
    )


def test_intersection_pavement_tie_in_edge_adds_straight_slope_band() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("existing:primary:inner", -5.0, 5.0, 9.25),
            TINVertex("existing:primary:outer", 5.0, 5.0, 9.25),
            TINVertex("existing:primary:tail", 0.0, 8.0, 8.5),
        ],
        triangle_rows=[
            TINTriangle("existing:primary:slope", "existing:primary:inner", "existing:primary:outer", "existing:primary:tail"),
        ],
    )
    boundary_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        intersection_id="intersection:t-01",
        status="ready",
        segment_rows=[
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:pavement:primary:left",
                intersection_id="intersection:t-01",
                segment_kind="tie_in",
                segment_role="pavement_edge",
                alignment_ref="alignment:primary",
                side="left",
                start_xyz=(-5.0, 2.0, 10.0),
                end_xyz=(5.0, 2.0, 10.0),
            )
        ],
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:primary",
                daylight_left_width=3.0,
                daylight_left_slope=0.25,
            )
        ],
    )

    augmented = build_corridor_command._augment_daylight_surface_with_curb_return_boundary_bands(
        surface,
        boundary_result,
        applied_section_set=applied,
    )

    assert build_corridor_command._tin_quality_float(augmented, "intersection_pavement_tie_in_slope_band_edge_count") == 1
    assert build_corridor_command._tin_quality_float(augmented, "intersection_pavement_tie_in_slope_band_triangle_count") == 2
    assert len([row for row in augmented.triangle_rows if row.quality_ref == "intersection_pavement_tie_in_slope_band"]) == 2
    assert build_corridor_command._tin_quality_float(augmented, "intersection_side_slope_extension_edge_count") >= 1
    assert any(
        "existing Primary Slope Face boundary" in row.notes
        for row in augmented.triangle_rows
        if row.quality_ref == "intersection_side_slope_extension"
    )
    assert any(
        "endpoint cap" in row.notes
        for row in augmented.triangle_rows
        if row.quality_ref == "intersection_side_slope_extension"
    )


def test_intersection_slope_gap_closure_fills_nearby_open_slope_edges() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("tie:start", 0.0, 0.0, 10.0),
            TINVertex("tie:end", 2.0, 0.0, 10.0),
            TINVertex("tie:tail", 1.0, -1.0, 9.5),
            TINVertex("slope:start", 0.0, 1.0, 9.75),
            TINVertex("slope:end", 2.0, 1.0, 9.75),
            TINVertex("slope:tail", 1.0, 2.0, 9.25),
        ],
        triangle_rows=[
            TINTriangle(
                "triangle:tie",
                "tie:start",
                "tie:end",
                "tie:tail",
                triangle_kind="daylight_surface",
                quality_ref="intersection_slope_tie_in",
            ),
            TINTriangle(
                "triangle:slope",
                "slope:end",
                "slope:start",
                "slope:tail",
                triangle_kind="daylight_surface",
                quality_ref="",
            ),
        ],
    )
    boundary_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        intersection_id="intersection:t-01",
        status="ready",
        segment_rows=[
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:curb-return:center",
                intersection_id="intersection:t-01",
                segment_kind="arc",
                segment_role="curb_return",
                center_xyz=(1.0, 0.5, 10.0),
                chord_points_xyz=((0.0, 0.0, 10.0), (2.0, 0.0, 10.0)),
            )
        ],
    )

    result = build_corridor_command._intersection_slope_gap_closure_triangles(
        surface,
        boundary_result=boundary_result,
        band_width=3.0,
    )

    assert result["edge_pair_count"] == 1
    assert result["triangle_count"] == 2
    assert len(result["triangles"]) == 2
    assert {row.quality_ref for row in result["triangles"]} == {"intersection_slope_gap_closure"}
    assert float(result["max_gap_distance"]) == 1.0


def test_intersection_slope_corner_closure_fills_curb_return_endpoint_gap() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("curb:end", 0.0, 0.0, 10.0),
            TINVertex("curb:outer", 0.0, 2.0, 9.5),
            TINVertex("curb:next", 1.0, 0.0, 10.0),
            TINVertex("slope:corner", 1.2, 1.2, 9.4),
            TINVertex("slope:outer", 2.0, 2.0, 9.0),
            TINVertex("slope:tail", 2.4, 0.8, 9.0),
        ],
        triangle_rows=[
            TINTriangle(
                "triangle:curb",
                "curb:end",
                "curb:next",
                "curb:outer",
                triangle_kind="daylight_surface",
                quality_ref="intersection_curb_return_slope_band",
            ),
            TINTriangle(
                "triangle:slope",
                "slope:corner",
                "slope:outer",
                "slope:tail",
                triangle_kind="daylight_surface",
                quality_ref="",
            ),
        ],
    )
    boundary_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        intersection_id="intersection:t-01",
        status="ready",
        segment_rows=[
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:curb-return:1",
                intersection_id="intersection:t-01",
                segment_kind="arc",
                segment_role="curb_return",
                center_xyz=(0.0, 2.0, 10.0),
                chord_points_xyz=((0.0, 0.0, 10.0), (1.0, 0.0, 10.0)),
            )
        ],
    )

    result = build_corridor_command._intersection_slope_gap_closure_triangles(
        surface,
        boundary_result=boundary_result,
        band_width=3.0,
    )

    corner_rows = [
        row for row in result["triangles"]
        if row.quality_ref == "intersection_slope_corner_closure"
    ]
    assert result["corner_triangle_count"] >= 1
    assert corner_rows
    assert any(row.v1 == "curb:end" or row.v2 == "curb:end" or row.v3 == "curb:end" for row in corner_rows)


def test_slope_face_generation_boundary_segments_use_only_open_tin_edges() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("v1", 0.0, 0.0, 10.0),
            TINVertex("v2", 2.0, 0.0, 10.0),
            TINVertex("v3", 2.0, 2.0, 10.0),
            TINVertex("v4", 0.0, 2.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("t1", "v1", "v2", "v3", triangle_kind="daylight_surface"),
            TINTriangle("t2", "v1", "v3", "v4", triangle_kind="daylight_surface"),
        ],
    )

    segments = build_corridor_command._slope_face_generation_boundary_segments(surface, z_offset=0.25)

    assert len(segments) == 4
    segment_xy = {
        (
            (round(start[0], 3), round(start[1], 3)),
            (round(end[0], 3), round(end[1], 3)),
        )
        for start, end in segments
    }
    flattened = {frozenset(pair) for pair in segment_xy}
    assert frozenset({(0.0, 0.0), (2.0, 2.0)}) not in flattened
    assert all(round(start[2], 3) == 10.25 and round(end[2], 3) == 10.25 for start, end in segments)


def test_intersection_curb_return_slope_band_keeps_both_side_tie_ins_when_nearest_band_edge_conflicts() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[],
        triangle_rows=[],
    )
    boundary_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        intersection_id="intersection:t-01",
        status="ready",
        segment_rows=[
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:curb-return:1",
                intersection_id="intersection:t-01",
                segment_kind="arc",
                segment_role="curb_return",
                center_xyz=(0.0, 0.0, 10.0),
                chord_points_xyz=((3.0, 0.0, 10.0), (2.121, 2.121, 10.0), (0.0, 3.0, 10.0)),
            )
        ],
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-contact",
                alignment_id="alignment:side",
                station=100.0,
                active_intersection_id="intersection:t-01",
                active_intersection_leg_role="side_road",
                frame=AppliedSectionFrame(station=100.0, x=2.121, y=2.121, z=10.0, tangent_direction_deg=45.0),
                surface_left_width=0.1,
                surface_right_width=0.1,
                daylight_left_width=0.2,
                daylight_right_width=0.2,
                daylight_left_slope=-0.25,
                daylight_right_slope=-0.25,
            )
        ],
    )

    augmented = build_corridor_command._augment_daylight_surface_with_curb_return_boundary_bands(
        surface,
        boundary_result,
        applied_section_set=applied,
    )

    assert build_corridor_command._tin_quality_float(augmented, "intersection_slope_tie_in_edge_count") >= 2
    assert build_corridor_command._tin_quality_float(augmented, "intersection_slope_tie_in_triangle_count") >= 4
    tie_in_notes = [
        row.notes
        for row in augmented.triangle_rows
        if row.quality_ref == "intersection_slope_tie_in"
    ]
    assert any("side=left" in notes for notes in tie_in_notes)
    assert any("side=right" in notes for notes in tie_in_notes)


def test_intersection_curb_return_slope_band_allows_multiple_sections_on_same_side() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[],
        triangle_rows=[],
    )
    boundary_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        intersection_id="intersection:t-01",
        status="ready",
        segment_rows=[
            IntersectionBoundarySegmentRow(
                boundary_segment_id="boundary:curb-return:1",
                intersection_id="intersection:t-01",
                segment_kind="arc",
                segment_role="curb_return",
                center_xyz=(0.0, 0.0, 10.0),
                chord_points_xyz=((3.0, 0.0, 10.0), (2.121, 2.121, 10.0), (0.0, 3.0, 10.0)),
            )
        ],
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-left-a",
                alignment_id="alignment:side",
                station=96.0,
                active_intersection_id="intersection:t-01",
                active_intersection_leg_role="side_road",
                frame=AppliedSectionFrame(station=96.0, x=3.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=0.1,
                daylight_left_width=0.2,
                daylight_left_slope=-0.25,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-left-b",
                alignment_id="alignment:side",
                station=144.0,
                active_intersection_id="intersection:t-01",
                active_intersection_leg_role="side_road",
                frame=AppliedSectionFrame(station=144.0, x=0.0, y=3.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=0.1,
                daylight_left_width=0.2,
                daylight_left_slope=-0.25,
            ),
        ],
    )

    augmented = build_corridor_command._augment_daylight_surface_with_curb_return_boundary_bands(
        surface,
        boundary_result,
        applied_section_set=applied,
    )

    assert build_corridor_command._tin_quality_float(augmented, "intersection_slope_tie_in_edge_count") >= 2
    tie_in_notes = [
        row.notes
        for row in augmented.triangle_rows
        if row.quality_ref == "intersection_slope_tie_in"
    ]
    assert any("section:side-left-a" in notes for notes in tie_in_notes)
    assert any("section:side-left-b" in notes for notes in tie_in_notes)


def test_intersection_side_tie_in_can_use_multiple_band_edges_for_one_section_side() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-left",
                alignment_id="alignment:side",
                station=100.0,
                active_intersection_id="intersection:t-01",
                active_intersection_leg_role="side_road",
                frame=AppliedSectionFrame(station=100.0, x=2.0, y=2.0, z=10.0, tangent_direction_deg=45.0),
                surface_left_width=0.1,
                daylight_left_width=0.2,
                daylight_left_slope=-0.25,
            )
        ],
    )
    boundary_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        intersection_id="intersection:t-01",
        status="ready",
    )
    band_edges = [
        (
            TINVertex(f"band:{index}:inner", float(index), float(index), 10.0),
            TINVertex(f"band:{index}:outer", float(index) + 0.2, float(index) + 0.2, 9.95),
        )
        for index in range(1, 5)
    ]

    edges = build_corridor_command._intersection_side_applied_section_slope_tie_in_edges(
        applied,
        boundary_result=boundary_result,
        band_radial_edges=band_edges,
        band_width=0.2,
        band_slope=0.25,
    )

    left_edges = [edge for edge in edges if edge["section_id"] == "section:side-left" and edge["side_label"] == "left"]
    assert len(left_edges) == 3


def test_intersection_curb_return_slope_tie_in_includes_primary_alignment_sections() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:primary-through",
                alignment_id="alignment:primary",
                station=100.0,
                active_intersection_id="intersection:t-01",
                active_intersection_leg_role="primary_through",
                frame=AppliedSectionFrame(station=100.0, x=2.0, y=2.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=0.1,
                daylight_left_width=0.2,
                daylight_left_slope=-0.25,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-road",
                alignment_id="alignment:side",
                station=100.0,
                active_intersection_id="intersection:t-01",
                active_intersection_leg_role="side_road",
                frame=AppliedSectionFrame(station=100.0, x=2.0, y=2.0, z=10.0, tangent_direction_deg=90.0),
                surface_left_width=0.1,
                daylight_left_width=0.2,
                daylight_left_slope=-0.25,
            ),
        ],
    )
    boundary_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        intersection_id="intersection:t-01",
        status="ready",
    )
    band_edges = [
        (
            TINVertex(f"band:{index}:inner", float(index), float(index), 10.0),
            TINVertex(f"band:{index}:outer", float(index) + 0.2, float(index) + 0.2, 9.95),
        )
        for index in range(1, 4)
    ]

    edges = build_corridor_command._intersection_side_applied_section_slope_tie_in_edges(
        applied,
        boundary_result=boundary_result,
        band_radial_edges=band_edges,
        band_width=0.2,
        band_slope=0.25,
    )

    assert any(edge["section_id"] == "section:primary-through" for edge in edges)
    assert any(edge["section_id"] == "section:side-road" for edge in edges)


def test_intersection_curb_return_slope_tie_in_uses_wider_primary_through_search() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:primary-opposite",
                alignment_id="alignment:primary",
                station=100.0,
                active_intersection_id="intersection:t-01",
                active_intersection_leg_role="primary_through",
                frame=AppliedSectionFrame(station=100.0, x=18.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=0.1,
                daylight_left_width=0.2,
                daylight_left_slope=-0.25,
            )
        ],
    )
    boundary_result = IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="proj-1",
        intersection_id="intersection:t-01",
        status="ready",
    )
    band_edges = [
        (
            TINVertex("band:inner", 4.75, 0.0, 10.0),
            TINVertex("band:outer", 8.25, 0.0, 9.125),
        )
    ]

    edges = build_corridor_command._intersection_side_applied_section_slope_tie_in_edges(
        applied,
        boundary_result=boundary_result,
        band_radial_edges=band_edges,
        band_width=3.5,
        band_slope=0.25,
    )

    assert any(edge["section_id"] == "section:primary-opposite" for edge in edges)
    assert any("role=primary_through" in str(edge.get("notes", "")) for edge in edges)


def test_intersection_side_slope_extension_can_reuse_existing_internal_slope_face_edge() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("existing:shared:a", 0.0, 0.0, 10.0),
            TINVertex("existing:shared:b", 0.0, 2.0, 9.5),
            TINVertex("existing:tail:left", -3.0, 1.0, 9.0),
            TINVertex("existing:tail:right", 3.0, 1.0, 9.0),
        ],
        triangle_rows=[
            TINTriangle("existing:left", "existing:shared:a", "existing:shared:b", "existing:tail:left"),
            TINTriangle("existing:right", "existing:shared:b", "existing:shared:a", "existing:tail:right"),
        ],
    )
    side_inner = TINVertex("side:inner", 0.0, 0.2, 10.0)
    side_outer = TINVertex("side:outer", 0.0, 1.8, 9.5)

    edges = build_corridor_command._near_existing_daylight_boundary_edges_to_side_edge(
        surface,
        side_inner,
        side_outer,
        max_distance=2.0,
        max_edges=1,
    )

    assert len(edges) == 1
    edge_ids = {
        str(getattr(edges[0][0], "vertex_id", "") or ""),
        str(getattr(edges[0][1], "vertex_id", "") or ""),
    }
    assert edge_ids == {"existing:shared:a", "existing:shared:b"}


def test_curb_return_arc_daylight_protection_detects_near_corridor_slope_triangle() -> None:
    arc = [[(0.0, 0.0), (2.0, 1.0), (4.0, 0.0)]]
    near_triangle = [(1.0, 2.0), (2.0, 2.5), (3.0, 2.0)]
    far_triangle = [(20.0, 20.0), (21.0, 20.0), (20.0, 21.0)]

    assert build_corridor_command._xy_triangle_near_curb_return_arc_protection(
        near_triangle,
        arc,
        max_distance=2.0,
    )
    assert not build_corridor_command._xy_triangle_near_curb_return_arc_protection(
        far_triangle,
        arc,
        max_distance=2.0,
    )


def test_intersection_exclusion_exact_cuts_non_convex_polygon_by_triangulation() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:test",
        surface_kind="design_surface",
        vertex_rows=[
            TINVertex("v1", -1.0, -1.0, 0.0),
            TINVertex("v2", 7.0, -1.0, 0.0),
            TINVertex("v3", -1.0, 7.0, 0.0),
            TINVertex("v4", 7.0, 7.0, 0.0),
        ],
        triangle_rows=[
            TINTriangle("t1", "v1", "v2", "v3"),
            TINTriangle("t2", "v2", "v4", "v3"),
        ],
    )
    original_provider = build_corridor_command._intersection_exclusion_polygon_from_sources
    build_corridor_command._intersection_exclusion_polygon_from_sources = lambda *args, **kwargs: {
        "intersection_id": "intersection:t-01",
        "status": "ready",
        "points": [(0.0, 0.0), (5.0, 0.0), (5.0, 2.0), (2.0, 2.0), (2.0, 5.0), (0.0, 5.0)],
        "area": 16.0,
    }
    try:
        clipped = build_corridor_command._clip_tin_surface_by_intersection_exclusion(
            surface,
            None,
            surface_role="design",
        )
    finally:
        build_corridor_command._intersection_exclusion_polygon_from_sources = original_provider

    assert build_corridor_command._tin_quality_text(clipped, "intersection_exclusion_clip_method") == "exact_triangulated_polygon"
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_supported") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_part_count") == 4
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_clipped_triangle_count") == 2
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_candidate_count") == 2
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_generated_triangle_count") > 0
    assert any(row.quality_ref == "intersection_exclusion_exact_cut" for row in clipped.triangle_rows)


def test_intersection_exclusion_exact_cut_preserves_hole_ring_fragments() -> None:
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:test",
        surface_kind="design_surface",
        vertex_rows=[
            TINVertex("v1", -1.0, -1.0, 0.0),
            TINVertex("v2", 7.0, -1.0, 0.0),
            TINVertex("v3", -1.0, 7.0, 0.0),
        ],
        triangle_rows=[TINTriangle("t1", "v1", "v2", "v3")],
    )
    original_provider = build_corridor_command._intersection_exclusion_polygon_from_sources
    build_corridor_command._intersection_exclusion_polygon_from_sources = lambda *args, **kwargs: {
        "intersection_id": "intersection:t-01",
        "status": "ready",
        "points": [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)],
        "holes": [[(2.0, 2.0), (3.0, 2.0), (3.0, 3.0), (2.0, 3.0)]],
        "islands": [],
        "area": 24.0,
    }
    try:
        clipped = build_corridor_command._clip_tin_surface_by_intersection_exclusion(
            surface,
            None,
            surface_role="design",
        )
    finally:
        build_corridor_command._intersection_exclusion_polygon_from_sources = original_provider

    assert build_corridor_command._tin_quality_text(clipped, "intersection_exclusion_clip_method") == "exact_multiring_polygon"
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_supported") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_part_count") == 2
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_hole_ring_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_island_ring_count") == 0
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_clipped_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(clipped, "intersection_exclusion_exact_cut_generated_triangle_count") > 0
    assert any(row.quality_ref == "intersection_exclusion_exact_cut" for row in clipped.triangle_rows)


def test_intersection_grading_policy_modes_have_distinct_z_behavior() -> None:
    vertices = [
        TINVertex("v:primary:left", 0.0, -5.0, 10.0, notes="alignment=alignment:primary"),
        TINVertex("v:primary:right", 0.0, 5.0, 12.0, notes="alignment=alignment:primary"),
        TINVertex("v:side:left", 5.0, 0.0, 20.0, notes="alignment=alignment:side"),
        TINVertex("v:side:right", -5.0, 0.0, 22.0, notes="alignment=alignment:side"),
    ]
    flattened = build_corridor_command._apply_intersection_grading_policy(
        vertices,
        IntersectionGradingPolicyRow("grading:flat", "intersection:t-01", mode="flatten_intersection", primary_alignment_ref="alignment:primary"),
    )
    preserved = build_corridor_command._apply_intersection_grading_policy(
        vertices,
        IntersectionGradingPolicyRow("grading:crown", "intersection:t-01", mode="keep_primary_crown", primary_alignment_ref="alignment:primary"),
    )
    blended = build_corridor_command._apply_intersection_grading_policy(
        vertices,
        IntersectionGradingPolicyRow("grading:blend", "intersection:t-01", mode="blend_primary_side", primary_alignment_ref="alignment:primary"),
    )

    assert [round(vertex.z, 6) for vertex in flattened] == [16.0, 16.0, 16.0, 16.0]
    assert [vertex.z for vertex in preserved] == [vertex.z for vertex in vertices]
    assert [round(vertex.z, 6) for vertex in blended] == [15.0, 17.0, 15.0, 17.0]
    assert "blend_basis=primary_side_plane" in blended[0].notes
    assert "blend_basis=primary_side_plane" in blended[2].notes


def test_intersection_patch_boundary_vertices_use_grading_plane_elevation() -> None:
    source_vertices = [
        TINVertex("v:primary:left", 0.0, -5.0, 10.0, notes="alignment=alignment:primary"),
        TINVertex("v:primary:right", 0.0, 5.0, 12.0, notes="alignment=alignment:primary"),
        TINVertex("v:side:left", 5.0, 0.0, 20.0, notes="alignment=alignment:side"),
        TINVertex("v:side:right", -5.0, 0.0, 22.0, notes="alignment=alignment:side"),
    ]
    plane = build_corridor_command._intersection_grading_plane_for_policy(
        source_vertices,
        IntersectionGradingPolicyRow("grading:blend", "intersection:t-01", mode="blend_primary_side", primary_alignment_ref="alignment:primary"),
    )
    patch_boundary = IntersectionPatchBoundaryResult(
        schema_version=1,
        project_id="proj-1",
        intersection_id="intersection:t-01",
        status="ready",
        point_rows=[
            IntersectionPatchBoundaryPointRow("boundary:p1", "intersection:t-01", 1, x=2.5, y=0.0, z=0.0),
        ],
    )

    vertices = build_corridor_command._intersection_patch_boundary_tin_vertices(
        patch_boundary,
        source_vertices=source_vertices,
        grading_plane=plane,
        grading_mode="blend_primary_side",
    )

    assert len(vertices) == 1
    assert round(vertices[0].z, 6) == 15.5
    assert "blend_basis=primary_side_plane" in vertices[0].notes


def test_corridor_intersection_boundary_segment_result_warns_when_curb_return_radius_is_large() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:intersection-long",
        corridor_id="corridor:main",
        alignment_id="alignment:primary",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:primary-96",
                corridor_id="corridor:main",
                alignment_id="alignment:primary",
                region_id="region:primary-intersection",
                station=96.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 96.0, 5.0, 10.0, "fg_surface", 5.0),
                    AppliedSectionPoint("fg:right", 96.0, -5.0, 10.0, "fg_surface", -5.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:primary-144",
                corridor_id="corridor:main",
                alignment_id="alignment:primary",
                region_id="region:primary-intersection",
                station=144.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 144.0, 5.0, 10.0, "fg_surface", 5.0),
                    AppliedSectionPoint("fg:right", 144.0, -5.0, 10.0, "fg_surface", -5.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-96",
                corridor_id="corridor:main",
                alignment_id="alignment:side",
                region_id="region:side-intersection",
                station=96.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 116.0, -24.0, 12.0, "fg_surface", 4.0),
                    AppliedSectionPoint("fg:right", 124.0, -24.0, 12.0, "fg_surface", -4.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:side-144",
                corridor_id="corridor:main",
                alignment_id="alignment:side",
                region_id="region:side-intersection",
                station=144.0,
                active_intersection_id="intersection:t-01",
                point_rows=[
                    AppliedSectionPoint("fg:left", 116.0, 24.0, 12.0, "fg_surface", 4.0),
                    AppliedSectionPoint("fg:right", 124.0, 24.0, 12.0, "fg_surface", -4.0),
                ],
            ),
        ],
    )
    prerequisite = IntersectionPatchPrerequisiteResult(
        status="ready",
        intersection_id="intersection:t-01",
        alignment_refs=("alignment:primary", "alignment:side"),
        control_region_refs=("region:primary-intersection", "region:side-intersection"),
    )
    intersection_model = IntersectionModel(
        schema_version=1,
        project_id="proj-1",
        intersection_model_id="intersections:test",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:t-01",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:primary",
                secondary_alignment_refs=["alignment:side"],
                intersection_point_x=120.0,
                intersection_point_y=0.0,
                primary_station=120.0,
                secondary_station_refs={"alignment:side": 120.0},
            )
        ],
        curb_return_policy_rows=[
            IntersectionCurbReturnPolicyRow(
                policy_id="curb-return:intersection:t-01:large",
                intersection_id="intersection:t-01",
                radius=80.0,
            )
        ],
    )
    tie_in_result = corridor_intersection_tie_in_edge_result(
        applied,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
    )

    result = corridor_intersection_boundary_segment_result(tie_in_result, intersection_model=intersection_model)

    assert result.status == "ready"
    assert result.arc_segment_count == 2
    assert any("warning:intersection_curb_return_radius_large" in row for row in result.diagnostic_rows)


def test_corridor_intersection_drainage_review_reports_missing_control_region_coverage() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:primary", "region:primary-intersection"),
            object_name="V1RegionModelPrimary",
        )
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:side", "region:side-intersection"),
            object_name="V1RegionModelSide",
        )
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=_sample_intersection_model(),
        )
        create_or_update_v1_applied_section_set_object(
            doc,
            project=project,
            applied_section_set=_sample_intersection_applied_sections(),
        )

        rows = corridor_intersection_drainage_review_rows(doc)
        summary = corridor_drainage_review_summary(doc)
        all_rows = corridor_drainage_review_rows(doc)
        marker_row_index = next(
            index for index, row in enumerate(all_rows)
            if row.get("review_kind") == "intersection_drainage"
        )
        marker = focus_corridor_drainage_review_row(doc, marker_row_index)

        assert len(rows) == 1
        assert rows[0]["review_kind"] == "intersection_drainage"
        assert rows[0]["context_label"] == "Intersection Drainage"
        assert rows[0]["intersection_id"] == "intersection:t-01"
        assert rows[0]["status"] == "missing"
        assert rows[0]["marker_kind"] == "suggested_inlet"
        assert "no Drainage Element coverage" in rows[0]["notes"]
        assert summary["status"] == "missing"
        assert "intersection" in summary["notes"]
        assert marker.V1ObjectType == "ReviewIssue"
        assert marker.IssueKind == "intersection_suggested_inlet"
        assert marker.DisplayMode == "suggested_inlet_marker"
        assert marker.SuggestedInletReviewOnly == "Yes"
        assert marker.IntersectionId == "intersection:t-01"
        assert int(marker.MarkerCount) == 1
    finally:
        App.closeDocument(doc.Name)


def test_corridor_intersection_drainage_review_accepts_control_region_element_coverage() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:primary", "region:primary-intersection"),
            object_name="V1RegionModelPrimary",
        )
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:side", "region:side-intersection"),
            object_name="V1RegionModelSide",
        )
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=_sample_intersection_model(),
        )
        create_or_update_v1_applied_section_set_object(
            doc,
            project=project,
            applied_section_set=_sample_intersection_applied_sections_with_tie_in_span(),
        )
        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-1",
                drainage_model_id="drainage:intersection",
                element_rows=[
                    DrainageElementRow(
                        drainage_element_id="drainage:intersection-inlet-01",
                        element_kind="inlet",
                        intersection_ref="intersection:t-01",
                        region_ref="region:primary-intersection",
                        station_start=96.0,
                        station_end=144.0,
                    )
                ],
            ),
        )
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        rows = corridor_intersection_drainage_review_rows(doc)
        preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )

        assert len(rows) == 1
        assert rows[0]["status"] == "ready"
        assert rows[0]["context"] == "intersection_drainage"
        assert rows[0]["drainage_element_refs"] == "drainage:intersection-inlet-01"
        assert preview is not None
        assert preview.IntersectionDrainageCoverageStatus == "ready"
        assert preview.IntersectionDrainageElementRefs == ["drainage:intersection-inlet-01"]
    finally:
        App.closeDocument(doc.Name)


def test_corridor_intersection_drainage_review_warns_when_element_misses_low_point_station() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:primary", "region:primary-intersection"),
            object_name="V1RegionModelPrimary",
        )
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=_sample_intersection_region_model("alignment:side", "region:side-intersection"),
            object_name="V1RegionModelSide",
        )
        create_or_update_v1_intersection_model_object(
            doc,
            project=project,
            intersection_model=_sample_intersection_model(),
        )
        create_or_update_v1_applied_section_set_object(
            doc,
            project=project,
            applied_section_set=_sample_intersection_applied_sections_with_tie_in_span(),
        )
        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-1",
                drainage_model_id="drainage:intersection",
                element_rows=[
                    DrainageElementRow(
                        drainage_element_id="drainage:intersection-inlet-outside-low-point",
                        element_kind="inlet",
                        intersection_ref="intersection:t-01",
                        region_ref="region:primary-intersection",
                        station_start=80.0,
                        station_end=90.0,
                    )
                ],
            ),
        )
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        rows = corridor_intersection_drainage_review_rows(doc)
        preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )

        assert len(rows) == 1
        assert rows[0]["status"] == "warn"
        assert rows[0]["drainage_element_refs"] == ""
        assert rows[0]["drainage_candidate_refs"] == "drainage:intersection-inlet-outside-low-point"
        assert "none cover the low-point station" in rows[0]["notes"]
        assert "intersection_low_point_station_uncovered" in rows[0]["diagnostics"]
        assert preview is not None
        assert preview.IntersectionDrainageCoverageStatus == "warn"
        assert list(preview.IntersectionDrainageElementRefs) == []
        assert list(preview.IntersectionDrainageCandidateRefs) == ["drainage:intersection-inlet-outside-low-point"]
        assert any("intersection_low_point_station_uncovered" in value for value in list(preview.IntersectionDrainageDiagnostics))
    finally:
        App.closeDocument(doc.Name)


def test_corridor_intersection_patch_prerequisites_report_missing_sources() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())

        result = corridor_intersection_patch_prerequisite_result(doc)
        summary = corridor_intersection_patch_prerequisite_summary(doc)

        assert result.status == "missing"
        assert "IntersectionModel is required" in result.diagnostic_rows[0]
        assert summary["status"] == "missing"
        assert "Intersection Surface Patch prerequisites are missing" in summary["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_focus_corridor_region_boundary_row_selects_built_region_surface_object() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)
        created = create_corridor_region_surface_previews(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )

        marker = focus_corridor_region_boundary_row(doc, 0)

        assert [obj.Name for obj in created] == [
            "V1CorridorRegionSurface_region_rural",
            "V1CorridorRegionSurface_region_rural_subgrade",
            "V1CorridorRegionSurface_region_rural_daylight",
            "V1CorridorRegionSurface_region_urban",
            "V1CorridorRegionSurface_region_urban_subgrade",
            "V1CorridorRegionSurface_region_urban_daylight",
        ]
        assert marker.Name == "V1CorridorRegionSurface_region_rural"
        assert marker.V1ObjectType == "V1CorridorRegionSurface"
        assert marker.CRRecordKind == "v1_corridor_region_surface_preview"
        assert marker.RegionRef == "region:rural"
        assert abs(float(marker.StationStart) - 0.0) < 1.0e-9
        assert abs(float(marker.StationEnd) - 20.0) < 1.0e-9
        assert marker.BoundaryStatus == "warn"
        assert int(marker.SurfaceFaceCount) == int(marker.TriangleCount)
        assert int(marker.SectionCount) == 2
        assert abs(float(marker.DisplayZOffset) - 0.25) < 1.0e-9
        assert doc.getObject("V1RegionDisplay_region_rural") is None

        second_marker = focus_corridor_region_boundary_row(doc, 1)

        assert second_marker.Name == "V1CorridorRegionSurface_region_urban"
        assert second_marker.RegionRef == "region:urban"
        assert int(second_marker.SectionCount) >= 2
        assert int(second_marker.SurfaceFaceCount) >= 2
        assert doc.getObject("V1CorridorRegionSurface_region_urban_daylight") is not None
        assert doc.getObject("V1CorridorRegionStructure_region_urban") is None
    finally:
        App.closeDocument(doc.Name)


def test_region_boundary_rows_report_generated_object_family_completeness() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)
        create_corridor_region_surface_previews(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )

        missing_rows = corridor_region_boundary_rows(doc)

        assert missing_rows[1]["region_object_status"] == "missing"
        assert "structure" in missing_rows[1]["region_object_diagnostics"]
        assert "V1CorridorRegionStructure_region_urban" not in list(missing_rows[1]["missing_region_object_names"])

        structure_obj = doc.addObject("Part::Feature", "V1StructurePreview_structure_wall_01")
        structure_obj.Label = "Structure - wall-01"
        structure_obj.addProperty("App::PropertyString", "CRRecordKind", "V1").CRRecordKind = "v1_structure_row_preview"
        structure_obj.addProperty("App::PropertyString", "StructureRef", "V1").StructureRef = "structure:wall-01"

        focused_names: list[str] = []
        previous_select = build_corridor_command._select_and_fit_objects
        try:
            build_corridor_command._select_and_fit_objects = lambda objects: focused_names.extend([obj.Name for obj in objects])
            focused = focus_corridor_region_boundary_row(doc, 1)
        finally:
            build_corridor_command._select_and_fit_objects = previous_select

        ready_rows = corridor_region_boundary_rows(doc)

        assert focused.Name == "V1CorridorRegionSurface_region_urban"
        assert "V1StructurePreview_structure_wall_01" in focused_names
        assert "V1CorridorRegionStructure_region_urban" not in focused_names
        assert ready_rows[1]["region_object_status"] == "ready"
        assert ready_rows[1]["region_object_count"] >= 4
    finally:
        App.closeDocument(doc.Name)


def test_region_boundary_focus_uses_structure_preview_contract_not_placeholder_name() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)
        create_corridor_region_surface_previews(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        structure_obj = doc.addObject("Part::Feature", "CustomStructurePreviewWall01")
        structure_obj.Label = "Structure - wall-01"
        structure_obj.addProperty("App::PropertyString", "CRRecordKind", "V1").CRRecordKind = "v1_structure_row_preview"
        structure_obj.addProperty("App::PropertyString", "StructureRef", "V1").StructureRef = "structure:wall-01"

        focused_names: list[str] = []
        previous_select = build_corridor_command._select_and_fit_objects
        try:
            build_corridor_command._select_and_fit_objects = lambda objects: focused_names.extend([obj.Name for obj in objects])
            focused = focus_corridor_region_boundary_row(doc, 1)
        finally:
            build_corridor_command._select_and_fit_objects = previous_select

        ready_rows = corridor_region_boundary_rows(doc)

        assert focused.Name == "V1CorridorRegionSurface_region_urban"
        assert "CustomStructurePreviewWall01" in focused_names
        assert "V1StructurePreview_structure_wall_01" not in ready_rows[1]["missing_region_object_names"]
        assert "CustomStructurePreviewWall01" in ready_rows[1]["region_object_names"]
        assert ready_rows[1]["region_object_status"] == "ready"
    finally:
        App.closeDocument(doc.Name)


def test_create_corridor_surface_transition_from_region_boundary_persists_source_intent() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())

        obj = create_corridor_surface_transition_from_region_boundary(doc, 0, sample_interval=1.0)
        rows = corridor_surface_transition_rows(doc)
        options = corridor_surface_transition_boundary_options(doc, region_id="region:rural")
        model = to_surface_transition_model(find_v1_surface_transition_model(doc))

        assert obj.V1ObjectType == "V1SurfaceTransitionModel"
        assert len(rows) == 1
        assert rows[0]["from_region_ref"] == "region:rural"
        assert rows[0]["to_region_ref"] == "region:urban"
        assert "FG L" in rows[0]["from_surface"]
        assert "FG L" in rows[0]["to_surface"]
        assert rows[0]["station_start"] == 15.0
        assert rows[0]["station_end"] == 25.0
        assert rows[0]["boundary_station"] == 20.0
        assert rows[0]["sample_interval"] == 1.0
        assert rows[0]["sample_count"] == 11
        assert rows[0]["status"] == "active"
        assert len(options) == 2
        assert options[1]["transition_exists"] is True
        assert options[1]["sample_interval"] == 1.0
        assert model is not None
        assert model.transition_ranges[0].sample_interval == 1.0
        assert model.transition_ranges[0].source_ref == "build-corridor:region-boundary"

        toggle_corridor_surface_transition_enabled(doc, 0)
        rows = corridor_surface_transition_rows(doc)

        assert rows[0]["enabled"] is False
        assert rows[0]["status"] == "disabled"
    finally:
        App.closeDocument(doc.Name)


def test_create_or_update_corridor_surface_transition_for_boundary_updates_only_selected_spacing() -> None:
    doc, project = _new_project_doc()
    try:
        applied = _sample_sections_with_region_boundary()
        extra = AppliedSection(
            schema_version=1,
            project_id="proj-1",
            applied_section_id="section:60",
            corridor_id="corridor:main",
            alignment_id="alignment:main",
            assembly_id="assembly:urban",
            region_id="region:suburban",
            station=60.0,
            frame=AppliedSectionFrame(station=60.0, x=60.0, y=0.0, z=13.0, tangent_direction_deg=0.0),
            surface_left_width=8.0,
            surface_right_width=6.0,
            point_rows=[
                AppliedSectionPoint("fg:left", 60.0, 8.0, 13.0, "fg_surface", 8.0),
                AppliedSectionPoint("fg:right", 60.0, -6.0, 13.0, "fg_surface", -6.0),
            ],
        )
        applied.sections.append(extra)
        applied.station_rows.append(AppliedSectionStationRow("station:60", 60.0, "section:60"))
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=applied)

        create_or_update_corridor_surface_transition_for_boundary(doc, 1, sample_interval=1.0, region_id="region:rural")
        create_or_update_corridor_surface_transition_for_boundary(doc, 0, sample_interval=5.0, region_id="region:urban")
        create_or_update_corridor_surface_transition_for_boundary(doc, 1, sample_interval=2.5, region_id="region:rural")

        model = to_surface_transition_model(find_v1_surface_transition_model(doc))
        assert model is not None
        intervals = {row.transition_id: row.sample_interval for row in model.transition_ranges}
        assert intervals["surface-transition:region:rural->region:urban@20.000"] == 2.5
        assert intervals["surface-transition:region:urban->region:suburban@40.000"] == 5.0
        rows = {row["transition_id"]: row for row in corridor_surface_transition_rows(doc)}
        assert rows["surface-transition:region:rural->region:urban@20.000"]["sample_count"] == 5
        assert rows["surface-transition:region:urban->region:suburban@40.000"]["sample_count"] == 3
    finally:
        App.closeDocument(doc.Name)


def test_update_corridor_surface_transition_station_range_persists_source_intent() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())
        create_corridor_surface_transition_from_region_boundary(doc, 0)

        update_corridor_surface_transition_station_range(doc, 0, station_start=18.0, station_end=32.0)
        rows = corridor_surface_transition_rows(doc)
        model = to_surface_transition_model(find_v1_surface_transition_model(doc))

        assert rows[0]["station_start"] == 18.0
        assert rows[0]["station_end"] == 32.0
        assert model is not None
        assert model.transition_ranges[0].station_start == 18.0
        assert model.transition_ranges[0].station_end == 32.0
    finally:
        App.closeDocument(doc.Name)


def test_build_document_corridor_surface_model_reads_saved_surface_transitions() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())
        create_corridor_surface_transition_from_region_boundary(doc, 0)

        surface_model = build_document_corridor_surface_model(doc, project=project)
        design_spans = [row for row in surface_model.span_rows if row.surface_ref == "corridor:main:design"]

        assert "surface-transitions:main" in surface_model.source_refs
        assert any(row.transition_ref for row in design_spans)
        assert any(row.continuity_status == "transition_applied" for row in design_spans)
    finally:
        App.closeDocument(doc.Name)


def test_surface_transition_sample_count_uses_ceiling_for_partial_spacing() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())

        create_or_update_corridor_surface_transition_for_boundary(doc, 1, sample_interval=4.0, region_id="region:rural")
        rows = corridor_surface_transition_rows(doc)

        assert rows[0]["sample_interval"] == 4.0
        assert rows[0]["sample_count"] == 4
    finally:
        App.closeDocument(doc.Name)


def test_build_parametric_rebuild_reflects_surface_transition_spacing_update() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())

        create_or_update_corridor_surface_transition_for_boundary(doc, 1, sample_interval=5.0, region_id="region:rural")
        apply_v1_corridor_model(document=doc, project=project, supplemental_sampling_enabled=False)
        coarse_preview = doc.getObject("V1CorridorDesignSurfacePreview")
        assert coarse_preview is not None
        coarse_vertices = int(coarse_preview.VertexCount)

        create_or_update_corridor_surface_transition_for_boundary(doc, 1, sample_interval=1.0, region_id="region:rural")
        apply_v1_corridor_model(document=doc, project=project, supplemental_sampling_enabled=False)
        dense_preview = doc.getObject("V1CorridorDesignSurfacePreview")
        marker = doc.getObject("V1SurfaceTransitionSpanMarkers")

        assert dense_preview is not None
        assert int(dense_preview.VertexCount) > coarse_vertices
        assert marker is not None
        assert int(marker.TransitionSpanCount) >= 1
        assert any(text.endswith("|1.000") for text in list(marker.TransitionSampleIntervals))
        assert any(text.endswith("|11") for text in list(marker.TransitionSampleCounts))
    finally:
        App.closeDocument(doc.Name)


def test_corridor_surface_transition_rows_include_generation_diagnostics() -> None:
    doc, project = _new_project_doc()
    try:
        applied = AppliedSectionSet(
            schema_version=1,
            project_id="proj-1",
            applied_section_set_id="sections:transition-diag",
            corridor_id="corridor:main",
            alignment_id="alignment:main",
            station_rows=[
                AppliedSectionStationRow("station:10", 10.0, "section:10"),
                AppliedSectionStationRow("station:20", 20.0, "section:20"),
            ],
            sections=[
                AppliedSection(
                    schema_version=1,
                    project_id="proj-1",
                    applied_section_id="section:10",
                    corridor_id="corridor:main",
                    region_id="region:a",
                    frame=AppliedSectionFrame(station=10.0, x=10.0, z=10.0),
                    point_rows=[
                        AppliedSectionPoint("fg:left", 10.0, 4.0, 10.0, "fg_surface", 4.0),
                        AppliedSectionPoint("fg:right", 10.0, -4.0, 10.0, "fg_surface", -4.0),
                    ],
                ),
                AppliedSection(
                    schema_version=1,
                    project_id="proj-1",
                    applied_section_id="section:20",
                    corridor_id="corridor:main",
                    region_id="region:b",
                    frame=AppliedSectionFrame(station=20.0, x=20.0, z=11.0),
                    point_rows=[
                        AppliedSectionPoint("fg:center", 20.0, 0.0, 11.0, "fg_surface", 0.0),
                    ],
                ),
            ],
        )
        transition_model = SurfaceTransitionModel(
            schema_version=1,
            project_id="proj-1",
            transition_model_id="surface-transitions:diag",
            corridor_ref="corridor:main",
            transition_ranges=[
                SurfaceTransitionRange(
                    "transition:diag",
                    12.0,
                    18.0,
                    from_region_ref="region:a",
                    to_region_ref="region:b",
                    target_surface_kinds=["design_surface"],
                    transition_mode="interpolate_matching_roles",
                    sample_interval=3.0,
                    approval_status="active",
                )
            ],
        )
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=applied)
        create_or_update_v1_surface_transition_model_object(doc, project=project, transition_model=transition_model)

        rows = corridor_surface_transition_rows(doc)

        assert rows[0]["status"] == "warn"
        assert "surface_transition_role_skipped" in rows[0]["diagnostics"]
        assert rows[0]["generation_diagnostic_count"] > 0
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_corridor_model_creates_surface_transition_span_markers() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())
        create_corridor_surface_transition_from_region_boundary(doc, 0)

        apply_v1_corridor_model(document=doc, project=project, supplemental_sampling_enabled=False)

        marker = doc.getObject("V1SurfaceTransitionSpanMarkers")
        assert marker is not None
        assert marker.V1ObjectType == "ReviewIssue"
        assert marker.IssueKind == "surface_transition_span"
        assert int(marker.MarkerCount) >= 1
        assert list(marker.TransitionRefs)
        assert int(marker.TransitionSpanCount) == len(list(marker.TransitionRefs))
        assert list(marker.TransitionStations)
        assert list(marker.TransitionSampleIntervals)
        assert list(marker.TransitionSampleCounts)
    finally:
        App.closeDocument(doc.Name)


def test_build_parametric_rebuild_updates_stable_tree_objects_without_duplicates() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_ditch_points())

        apply_v1_corridor_model(document=doc, project=project, supplemental_sampling_enabled=False)
        first_names = {
            name
            for name in (
                "V1CorridorDesignSurfacePreview",
                "V1CorridorSubgradeSurfacePreview",
                "V1CorridorDaylightSurfacePreview",
                "V1CorridorDrainageSurfacePreview",
                "ReviewIssueSlopeFaceFallbackMarkers",
            )
            if doc.getObject(name) is not None
        }
        first_object_ids = {name: id(doc.getObject(name)) for name in first_names}

        apply_v1_corridor_model(document=doc, project=project, supplemental_sampling_enabled=False)

        build_outputs = ensure_project_tree(project, include_references=False)[V1_TREE_BUILD_PARAMETRIC_OUTPUTS]
        build_output_names = _group_name_list(build_outputs)

        for name in first_names:
            assert doc.getObject(name) is not None
            assert id(doc.getObject(name)) == first_object_ids[name]
            assert build_output_names.count(name) == 1
        for name in first_names:
            assert len([obj for obj in doc.Objects if str(getattr(obj, "Name", "") or "") == name]) == 1
    finally:
        App.closeDocument(doc.Name)


def test_region_surface_preview_rebuild_removes_stale_region_objects() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())
        apply_v1_corridor_model(document=doc, project=project, supplemental_sampling_enabled=False)

        assert doc.getObject("V1CorridorRegionSurface_region_rural") is not None
        assert doc.getObject("V1CorridorRegionSurface_region_urban") is not None

        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())
        apply_v1_corridor_model(document=doc, project=project, supplemental_sampling_enabled=False)

        build_outputs = ensure_project_tree(project, include_references=False)[V1_TREE_BUILD_PARAMETRIC_OUTPUTS]
        build_output_names = _group_names(build_outputs)

        assert doc.getObject("V1CorridorRegionSurface_region_rural") is None
        assert doc.getObject("V1CorridorRegionSurface_region_rural_subgrade") is None
        assert doc.getObject("V1CorridorRegionSurface_region_rural_daylight") is None
        assert doc.getObject("V1CorridorRegionSurface_region_urban") is None
        assert not any(name.startswith("V1CorridorRegionSurface_region_") for name in build_output_names)
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_panel_shows_progress_bar() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc()
    try:
        panel = V1BuildCorridorTaskPanel(document=doc)
        progress_bars = panel.form.findChildren(QtWidgets.QProgressBar)

        assert len(progress_bars) == 1
        assert progress_bars[0].value() == 0
        assert progress_bars[0].format() == "Ready"
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_panel_has_region_boundaries_table() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())
        panel = V1BuildCorridorTaskPanel(document=doc)

        assert panel._region_table.rowCount() == 2
        assert panel._region_table.item(0, 0).text() == "region:rural"
        assert panel._region_table.item(1, 0).text() == "region:urban"
        assert panel._region_table.item(0, 7).text() == "warn"
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_panel_creates_surface_transition_from_selected_region() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())
        panel = V1BuildCorridorTaskPanel(document=doc)

        assert hasattr(panel, "_surface_transition_table")
        assert panel._surface_transition_table.rowCount() == 0

        assert panel._surface_transition_boundary_combo.count() == 2
        assert "STA 0.000" in panel._surface_transition_boundary_combo.itemText(0)
        assert "STA 20.000" in panel._surface_transition_boundary_combo.itemText(1)
        panel._region_table.selectRow(1)
        assert panel._surface_transition_boundary_combo.count() == 1
        assert "STA 40.000" in panel._surface_transition_boundary_combo.itemText(0)
        panel._region_table.selectRow(0)
        panel._surface_transition_boundary_combo.setCurrentIndex(1)
        panel._surface_transition_spacing_combo.setCurrentIndex(0)
        panel._create_transition_from_selected_boundary_option()

        assert panel._surface_transition_table.rowCount() == 1
        assert panel._surface_transition_table.item(0, 2).text() == "20.000"
        assert panel._surface_transition_table.item(0, 3).text() == "1.000"
        assert panel._surface_transition_table.item(0, 4).text() == "11"
        assert panel._surface_transition_table.item(0, 5).text() == "region:rural"
        assert panel._surface_transition_table.item(0, 6).text() == "region:urban"
        assert "FG L" in panel._surface_transition_table.item(0, 7).text()
        assert "FG L" in panel._surface_transition_table.item(0, 8).text()
        assert panel._surface_transition_table.item(0, 11).text() == "active"
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_panel_updates_selected_surface_transition_spacing() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())
        create_corridor_surface_transition_from_region_boundary(doc, 0)
        panel = V1BuildCorridorTaskPanel(document=doc)

        panel._surface_transition_boundary_combo.setCurrentIndex(1)
        panel._surface_transition_spacing_combo.setCurrentIndex(3)
        panel._surface_transition_spacing_spin.setValue(4.0)
        panel._create_transition_from_selected_boundary_option()

        model = to_surface_transition_model(find_v1_surface_transition_model(doc))
        assert model is not None
        assert model.transition_ranges[0].station_start == 15.0
        assert model.transition_ranges[0].station_end == 25.0
        assert model.transition_ranges[0].sample_interval == 4.0
        assert panel._surface_transition_table.item(0, 2).text() == "20.000"
        assert panel._surface_transition_table.item(0, 3).text() == "4.000"
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_panel_expands_display_areas_with_task_width() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc()
    try:
        panel = V1BuildCorridorTaskPanel(document=doc)

        assert panel.form.minimumWidth() <= 420
        assert panel.form.maximumWidth() > 560
        assert panel.form.sizePolicy().horizontalPolicy() == QtWidgets.QSizePolicy.Expanding
        assert panel._summary.sizePolicy().horizontalPolicy() == QtWidgets.QSizePolicy.Expanding
        assert panel._guided_table.minimumWidth() == 0
        assert panel._guided_table.maximumWidth() > 560
        assert panel._guided_table.sizePolicy().horizontalPolicy() == QtWidgets.QSizePolicy.Expanding
        assert panel._review_table.minimumWidth() == 0
        assert panel._review_table.sizePolicy().horizontalPolicy() == QtWidgets.QSizePolicy.Expanding
        assert panel._slope_issue_table.minimumWidth() == 0
        assert panel._slope_issue_table.sizePolicy().horizontalPolicy() == QtWidgets.QSizePolicy.Expanding
        assert panel._drainage_table.minimumWidth() == 0
        assert panel._drainage_table.sizePolicy().horizontalPolicy() == QtWidgets.QSizePolicy.Expanding
        assert panel._surface_transition_table.minimumWidth() == 0
        assert panel._surface_transition_table.sizePolicy().horizontalPolicy() == QtWidgets.QSizePolicy.Expanding
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_hides_applied_section_set_review_shape() -> None:
    doc, project = _new_project_doc()
    try:
        applied = create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())
        if getattr(applied, "ViewObject", None) is None:
            return
        applied.ViewObject.Visibility = True

        assert _hide_applied_section_set_review_shape(doc) is True
        assert applied.ViewObject.Visibility is False
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_panel_has_daylight_contact_marker_checkbox() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc()
    try:
        panel = V1BuildCorridorTaskPanel(document=doc)
        checks = panel.form.findChildren(QtWidgets.QCheckBox)
        contact_checks = [check for check in checks if check.text() == "Daylight Contact Markers"]

        assert len(contact_checks) == 1
        assert contact_checks[0].isChecked() is False
        assert panel._show_daylight_contact_markers() is False
        contact_checks[0].setChecked(True)
        assert panel._show_daylight_contact_markers() is True
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_panel_has_supplemental_sampling_checked_by_default() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc()
    try:
        panel = V1BuildCorridorTaskPanel(document=doc)
        checks = panel.form.findChildren(QtWidgets.QCheckBox)
        sampling_checks = [check for check in checks if check.text() == "Supplemental Sampling"]

        assert len(sampling_checks) == 1
        assert sampling_checks[0].isChecked() is True
        assert panel._use_supplemental_sampling() is True
        sampling_checks[0].setChecked(False)
        assert panel._use_supplemental_sampling() is False
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_corridor_model_can_disable_supplemental_sampling() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())

        apply_v1_corridor_model(document=doc, project=project, supplemental_sampling_enabled=False)

        preview = doc.getObject("V1CorridorDesignSurfacePreview")
        daylight_preview = doc.getObject("V1CorridorDaylightSurfacePreview")
        assert preview is not None
        assert daylight_preview is not None
        assert int(preview.VertexCount) == 4
        assert int(preview.TriangleCount) == 2
        assert int(daylight_preview.VertexCount) == 8
        assert int(daylight_preview.TriangleCount) == 4
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_corridor_model_does_not_resample_when_applied_sections_have_supplemental_rows() -> None:
    doc, project = _new_project_doc()
    try:
        applied = _sample_sections_with_centerline_curve()
        applied.station_rows[1] = AppliedSectionStationRow("station:20", 20.0, "section:20", kind="curve_supplemental")
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=applied)

        apply_v1_corridor_model(document=doc, project=project, supplemental_sampling_enabled=True)

        preview = doc.getObject("V1CorridorDesignSurfacePreview")
        assert preview is not None
        assert int(preview.VertexCount) == 6
        assert int(preview.ConsumedSourceSectionCount) == 2
        assert int(preview.ConsumedSupplementalSectionCount) == 1
        assert int(preview.SupplementalCompatibilityFallbackActive) == 0
        assert preview.SupplementalCompatibilityPolicy == "applied_sections_only"
    finally:
        App.closeDocument(doc.Name)


def test_corridor_build_review_rows_summarize_preview_outputs() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())

        missing_rows = corridor_build_review_rows(doc)
        assert [row["status"] for row in missing_rows] == ["missing", "missing", "missing", "missing", "missing"]
        assert "2 STA" in str(missing_rows[0]["applied_section_summary"])
        assert missing_rows[0]["applied_section_diagnostics"] == "ok"

        apply_v1_corridor_model(document=doc, project=project)
        rows = corridor_build_review_rows(doc)

        assert [row["role"] for row in rows] == ["centerline", "design", "subgrade", "daylight", "drainage"]
        assert [row["status"] for row in rows] == ["missing", "ready", "ready", "ready", "missing"]
        assert rows[0]["triangle_or_point_count"] == ""
        assert rows[1]["vertex_count"] == 10
        assert rows[1]["triangle_or_point_count"] == 8
        assert "2 STA" in str(rows[1]["applied_section_summary"])
        assert rows[1]["applied_section_diagnostics"] == "ok"
        assert "fallbacks: 10" in str(rows[3]["notes"])
        assert "no EG TIN: 10" in str(rows[3]["notes"])
        assert "STA 0.000 L no EG TIN" in str(rows[3]["notes"])
        assert "STA 20.000 R no EG TIN" in str(rows[3]["notes"])
        assert "no drainage_surface row exists" in str(rows[4]["notes"])
        assert preferred_corridor_build_review_row_index(rows) == 1

        shown = show_corridor_build_review_object(doc, 1)
        assert shown.Name == "V1CorridorDesignSurfacePreview"
    finally:
        App.closeDocument(doc.Name)


def test_corridor_build_review_outcome_matrix_is_deterministic() -> None:
    rows = corridor_build_review_outcome_matrix()

    assert [row["status"] for row in rows] == ["ready", "warning", "missing", "empty", "error"]
    assert all(row["meaning"] for row in rows)


def test_corridor_build_review_rows_preserve_warning_diagnostics() -> None:
    doc, project = _new_project_doc()
    try:
        build_corridor_command._record_corridor_build_preview_diagnostic(
            doc,
            role="design",
            surface_kind="design_surface",
            status="warning",
            notes="Design Surface preview needs review before downstream use.",
            project=project,
        )

        rows = corridor_build_review_rows(doc)

        assert rows[1]["role"] == "design"
        assert rows[1]["status"] == "warning"
        assert "needs review" in str(rows[1]["notes"])
        tree = ensure_project_tree(project, include_references=False)
        diagnostic = doc.getObject("V1CorridorDesignSurfacePreviewDiagnostic")
        assert diagnostic is not None
        assert diagnostic.Name in _group_names(tree[V1_TREE_BUILD_PARAMETRIC_OUTPUTS])
    finally:
        App.closeDocument(doc.Name)


def test_corridor_applied_sections_review_summary_tracks_source_context() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_ditch_points())

        summary = corridor_applied_sections_review_summary(doc)

        assert summary["status"] == "ok"
        assert summary["station_count"] == 2
        assert summary["diagnostic_count"] == 0
        assert summary["ditch_point_count"] == 8
        assert summary["slope_face_count"] == 0
        assert summary["structure_count"] == 0
        assert "2 STA" in summary["summary"]
        assert "structures:0" in summary["summary"]
        assert "ditch_pts:8" in summary["summary"]
    finally:
        App.closeDocument(doc.Name)


def test_corridor_applied_sections_review_summary_tracks_singular_structure_owner() -> None:
    doc, project = _new_project_doc()
    try:
        applied = AppliedSectionSet(
            schema_version=1,
            project_id="proj-1",
            applied_section_set_id="sections:structure",
            corridor_id="corridor:main",
            alignment_id="alignment:main",
            station_rows=[AppliedSectionStationRow("station:10", 10.0, "section:10")],
            sections=[
                AppliedSection(
                    schema_version=1,
                    project_id="proj-1",
                    applied_section_id="section:10",
                    corridor_id="corridor:main",
                    station=10.0,
                    active_structure_ids=["structure:bridge-01", "structure:wall-ignored"],
                    subassembly_rows=[
                        AppliedSectionSubassemblyRow(
                            subassembly_id="lane-1",
                            kind="lane",
                            structure_ids=["structure:bridge-01"],
                        )
                    ],
                )
            ],
        )
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=applied)

        summary = corridor_applied_sections_review_summary(doc)

        assert summary["structure_count"] == 1
        assert summary["structure_refs"] == ["structure:bridge-01"]
        assert "structures:1" in summary["summary"]
    finally:
        App.closeDocument(doc.Name)


def test_corridor_drainage_review_rows_track_ditch_surface_points() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_ditch_points())

        rows = corridor_drainage_review_rows(doc)
        summary = corridor_drainage_review_summary(doc)

        assert [row["status"] for row in rows] == ["ready", "ready"]
        assert rows[0]["context_label"] == "Roadside Drainage"
        assert rows[0]["station"] == 0.0
        assert rows[0]["ditch_point_count"] == 4
        assert rows[0]["left_count"] == 2
        assert rows[0]["right_count"] == 2
        assert rows[0]["marker_object"] == "ReviewIssueDrainageStation001"
        assert rows[0]["x"] == "0.000000"
        assert rows[0]["y"] == "0.500000"
        assert rows[0]["z"] == "9.900000"
        assert summary["status"] == "ready"
        assert summary["ditch_point_count"] == 8
        assert summary["missing_count"] == 0
        marker = focus_corridor_drainage_review_row(doc, 0)
        assert marker.Name == "ReviewIssueDrainageStation001"
        assert marker.V1ObjectType == "ReviewIssue"
        assert marker.IssueKind == "drainage_diagnostic"
        assert marker.IssueStation == "0.000"
        assert marker.IssueStatus == "ready"
        assert marker.DisplayMode == "drainage_highlight"
        assert int(marker.MarkerCount) == 4
    finally:
        App.closeDocument(doc.Name)


def test_slope_face_markers_include_daylight_contact_vertices() -> None:
    doc, project = _new_project_doc()
    try:
        surface = TINSurface(
            schema_version=1,
            project_id="proj-1",
            surface_id="surface:daylight",
            surface_kind="daylight_surface",
            vertex_rows=[
                TINVertex("v0:right:r0:p0", 0.0, -4.0, 10.0, notes="terminal_edge"),
                TINVertex("v0:right:r0:p1", 0.0, -8.0, 12.0, notes="daylight_marker"),
                TINVertex("v1:right:r0:p1", 10.0, -8.5, 12.2, notes="daylight_marker"),
            ],
        )

        created = build_corridor_command._create_slope_face_diagnostic_markers(
            document=doc,
            project=project,
            surface=surface,
            show_daylight_contact_markers=False,
        )

        marker = doc.getObject("ReviewIssueSlopeFaceIntersectionMarkers")
        assert marker is None
        assert created == []
        assert set_corridor_build_daylight_contact_marker_visibility(doc, True) is None

        created = build_corridor_command._create_slope_face_diagnostic_markers(
            document=doc,
            project=project,
            surface=surface,
            show_daylight_contact_markers=True,
        )

        marker = doc.getObject("ReviewIssueSlopeFaceIntersectionMarkers")
        assert marker is not None
        assert marker.Label == "Slope Face Daylight / EG Intersections"
        assert int(marker.MarkerCount) == 2
        assert marker in created
        shown = set_corridor_build_daylight_contact_marker_visibility(doc, True)
        assert shown == marker
    finally:
        App.closeDocument(doc.Name)


def test_daylight_contact_marker_visibility_helper_targets_daylight_marker_objects() -> None:
    class FakeView:
        def __init__(self):
            self.Visibility = False

    class FakeObject:
        def __init__(self, name):
            self.Name = name
            self.ViewObject = FakeView()

    class FakeDocument:
        def __init__(self):
            self.contact = FakeObject("ReviewIssueSlopeFaceIntersectionMarkers")
            self.sampled = FakeObject("ReviewIssueSlopeFaceSampledEdgeMarkers")
            self.fallback = FakeObject("ReviewIssueSlopeFaceFallbackMarkers")

        def getObject(self, name):
            if name == self.contact.Name:
                return self.contact
            if name == self.sampled.Name:
                return self.sampled
            if name == self.fallback.Name:
                return self.fallback
            return None

    doc = FakeDocument()

    shown = set_corridor_build_daylight_contact_marker_visibility(doc, True)

    assert shown == doc.contact
    assert doc.contact.ViewObject.Visibility is True
    assert doc.sampled.ViewObject.Visibility is True
    assert doc.fallback.ViewObject.Visibility is True


def test_corridor_drainage_review_rows_explain_missing_ditch_points() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())

        rows = corridor_drainage_review_rows(doc)
        summary = corridor_drainage_review_summary(doc)
        steps = corridor_build_guided_review_steps(doc)

        assert [row["status"] for row in rows] == ["missing", "missing"]
        assert "No ditch_surface" in str(rows[0]["notes"])
        assert summary["status"] == "missing"
        assert summary["missing_count"] == 2
        drainage_step = next(step for step in steps if step["step_id"] == "drainage")
        assert drainage_step["status"] == "missing"
        assert "without ditch_surface" in str(drainage_step["notes"])
    finally:
        App.closeDocument(doc.Name)


def test_corridor_drainage_review_rows_report_source_side_subassembly_mismatch() -> None:
    doc, project = _new_project_doc()
    try:
        applied = AppliedSectionSet(
            schema_version=1,
            project_id="proj-1",
            applied_section_set_id="sections:drainage-mismatch",
            corridor_id="corridor:main",
            alignment_id="alignment:main",
            station_rows=[AppliedSectionStationRow("station:0", 0.0, "section:0")],
            sections=[
                AppliedSection(
                    schema_version=1,
                    project_id="proj-1",
                    applied_section_id="section:0",
                    corridor_id="corridor:main",
                    alignment_id="alignment:main",
                    station=0.0,
                    region_id="region:road",
                    frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0),
                    point_rows=[
                        AppliedSectionPoint(
                            "ditch:left-flow",
                            0.0,
                            6.0,
                            9.8,
                            "ditch_surface",
                            6.0,
                            subassembly_ref="ditch:left",
                            side="left",
                            drainage_ref="drainage:left",
                        ),
                        AppliedSectionPoint(
                            "ditch:left-edge",
                            0.0,
                            5.0,
                            10.0,
                            "ditch_surface",
                            5.0,
                            subassembly_ref="ditch:left",
                            side="left",
                            drainage_ref="drainage:left",
                        ),
                    ],
                )
            ],
        )
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=applied)
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=RegionModel(
                schema_version=1,
                project_id="proj-1",
                region_model_id="regions:main",
                region_rows=[RegionRow("region:road", 0.0, 20.0)],
            ),
        )
        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-1",
                drainage_model_id="drainage:main",
                element_rows=[
                    DrainageElementRow(
                        "drainage:right",
                        "ditch",
                        side="right",
                        region_ref="region:road",
                        subassembly_ref="ditch:right",
                        station_start=0.0,
                        station_end=20.0,
                    )
                ],
            ),
        )

        rows = corridor_drainage_review_rows(doc)
        summary = corridor_drainage_review_summary(doc)

        assert rows[0]["status"] == "missing"
        assert "missing_side=right" in str(rows[0]["notes"])
        assert "drainage_ref=drainage:right" in str(rows[0]["notes"])
        assert summary["status"] == "missing"
    finally:
        App.closeDocument(doc.Name)


def test_corridor_drainage_review_rows_report_source_tag_mismatch() -> None:
    doc, project = _new_project_doc()
    try:
        applied = _sample_sections_with_ditch_points()
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=applied)
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=RegionModel(
                schema_version=1,
                project_id="proj-1",
                region_model_id="regions:main",
                region_rows=[RegionRow("region:road", 0.0, 20.0)],
            ),
        )
        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-1",
                drainage_model_id="drainage:main",
                element_rows=[
                    DrainageElementRow(
                        "drainage:right",
                        "ditch",
                        side="right",
                        region_ref="region:road",
                        subassembly_ref="ditch:right",
                        station_start=0.0,
                        station_end=20.0,
                    )
                ],
            ),
        )

        rows = corridor_drainage_review_rows(doc)

        assert rows[0]["status"] == "warn"
        assert "missing_drainage_ref=drainage:right" in str(rows[0]["notes"])
        assert "subassembly_mismatch=ditch:right" in str(rows[0]["notes"])
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_corridor_model_records_drainage_surface_diagnostic_without_ditch_points() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())

        apply_v1_corridor_model(document=doc, project=project)

        preview = doc.getObject("V1CorridorDrainageSurfacePreview")
        diagnostic = doc.getObject("V1CorridorDrainageSurfacePreviewDiagnostic")
        rows = corridor_build_review_rows(doc)

        assert preview is None
        assert diagnostic is not None
        assert diagnostic.CRRecordKind == "v1_corridor_surface_preview_diagnostic"
        assert diagnostic.SurfaceRole == "drainage"
        assert diagnostic.PreviewStatus == "missing"
        assert "ditch_surface" in diagnostic.PreviewDiagnostic
        assert rows[4]["role"] == "drainage"
        assert rows[4]["status"] == "missing"
    finally:
        App.closeDocument(doc.Name)


def test_corridor_guided_review_adds_drainage_flow_context_and_highlight() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_ditch_points())
        create_or_update_v1_structure_model_object(
            doc,
            project=project,
            structure_model=StructureModel(
                schema_version=1,
                project_id="proj-1",
                structure_model_id="structures:test",
                structure_rows=[
                    StructureRow(
                        structure_id="structure:culvert-01",
                        structure_kind="culvert",
                        structure_role="crossing",
                        placement=StructurePlacement(
                            placement_id="placement:culvert-01",
                            alignment_id="alignment:main",
                            station_start=8.0,
                            station_end=12.0,
                        ),
                    )
                ],
            ),
        )
        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-1",
                drainage_model_id="drainage:test",
                element_rows=[
                    DrainageElementRow(
                        drainage_element_id="drainage:side-ditch-right",
                        element_kind="ditch",
                        side="right",
                        station_start=0.0,
                        station_end=20.0,
                    ),
                    DrainageElementRow(
                        drainage_element_id="drainage:culvert-01",
                        element_kind="culvert",
                        structure_ref="structure:culvert-01",
                        station_start=8.0,
                        station_end=12.0,
                    ),
                ],
                flow_route_rows=[
                    DrainageFlowRoute(
                        flow_route_id="flow-route:flowId-01",
                        from_element_ref="drainage:side-ditch-right",
                        to_element_ref="drainage:culvert-01",
                        outlet_ref="structure:culvert-01",
                    )
                ],
            ),
        )

        rows = corridor_drainage_flow_review_rows(doc)
        summary = corridor_drainage_flow_review_summary(doc)
        steps = corridor_build_guided_review_steps(doc)
        focused = focus_corridor_build_guided_review_step(doc, "drainage_flow")

        assert rows[0]["status"] == "ready"
        assert rows[0]["flow_route_id"] == "flow-route:flowId-01"
        assert rows[0]["structure_refs"] == "structure:culvert-01"
        assert rows[0]["highlight_mode"] == "station_span"
        assert summary["status"] == "ready"
        assert "culvert-01" in str(summary["notes"])
        drainage_flow_step = [step for step in steps if step["step_id"] == "drainage_flow"][0]
        assert drainage_flow_step["focus"] == "flowId-01"
        assert focused.Name == "ReviewIssueDrainageFlowRoutes"
        assert focused.DisplayMode == "drainage_flow_station_span"
        assert focused.FlowRouteRefs == ["flow-route:flowId-01"]
        assert focused.StructureRefs == ["structure:culvert-01"]
        assert int(focused.PipeSegmentCount) == 0
        assert int(focused.StationSpanCount) >= 1
        assert focus_corridor_drainage_flow_review(doc).Name == "ReviewIssueDrainageFlowRoutes"
    finally:
        App.closeDocument(doc.Name)


def test_intersection_preset_drainage_does_not_create_drainage_flow_highlight() -> None:
    doc, project = _new_project_doc()
    try:
        stale = doc.addObject("Part::Feature", "ReviewIssueDrainageFlowRoutes")
        stale.Label = "Drainage Flow Highlight"
        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-1",
                drainage_model_id="drainage:intersection-preset-t-intersection",
                element_rows=[
                    DrainageElementRow(
                        drainage_element_id="drainage:intersection-low-point-t-intersection",
                        element_kind="low_point_hint",
                    ),
                    DrainageElementRow(
                        drainage_element_id="drainage:intersection-outlet-hint-t-intersection",
                        element_kind="outlet_hint",
                    ),
                ],
                flow_route_rows=[
                    DrainageFlowRoute(
                        flow_route_id="flow-route:intersection-t-intersection-01",
                        from_element_ref="drainage:intersection-low-point-t-intersection",
                        to_element_ref="drainage:intersection-outlet-hint-t-intersection",
                        outlet_ref="drainage:intersection-outlet-hint-t-intersection",
                    )
                ],
                source_refs=["intersection:t-01"],
            ),
            object_name="V1IntersectionPresetDrainage",
            label="Intersection Preset Drainage",
        )

        rows = corridor_drainage_flow_review_rows(doc)
        summary = corridor_drainage_flow_review_summary(doc)

        assert doc.getObject("ReviewIssueDrainageFlowRoutes") is None
        assert rows[0]["status"] == "missing"
        assert rows[0]["flow_route_id"] == ""
        assert "Intersection preset drainage" in rows[0]["notes"]
        assert summary["status"] == "missing"
        try:
            focus_corridor_drainage_flow_review(doc)
        except RuntimeError as exc:
            assert "No Drainage Flow Route rows" in str(exc)
        else:
            raise AssertionError("Intersection preset drainage should not create a Drainage Flow highlight.")
    finally:
        App.closeDocument(doc.Name)


def test_drainage_flow_focus_connects_structure_connection_points_as_pipe_segments() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())
        create_or_update_v1_structure_model_object(
            doc,
            project=project,
            structure_model=StructureModel(
                schema_version=1,
                project_id="proj-1",
                structure_model_id="structures:main",
                structure_rows=[
                    StructureRow(
                        structure_id="structure:inlet-01",
                        structure_kind="utility",
                        structure_role="reference",
                        placement=StructurePlacement(
                            "placement:inlet-01",
                            "alignment:main",
                            station_start=2.0,
                            station_end=2.0,
                        ),
                    ),
                    StructureRow(
                        structure_id="structure:culvert-01",
                        structure_kind="culvert",
                        structure_role="clearance_control",
                        placement=StructurePlacement(
                            "placement:culvert-01",
                            "alignment:main",
                            station_start=10.0,
                            station_end=12.0,
                        ),
                    ),
                    StructureRow(
                        structure_id="structure:outlet-01",
                        structure_kind="utility",
                        structure_role="reference",
                        placement=StructurePlacement(
                            "placement:outlet-01",
                            "alignment:main",
                            station_start=18.0,
                            station_end=18.0,
                        ),
                    ),
                ],
                connection_point_rows=[
                    StructureConnectionPoint(
                        connection_point_id="connection:inlet-01:pipe-out",
                        structure_ref="structure:inlet-01",
                        point_role="pipe_out",
                        station=2.0,
                        offset=-4.0,
                        diameter=0.6,
                    ),
                    StructureConnectionPoint(
                        connection_point_id="connection:culvert-01:upstream",
                        structure_ref="structure:culvert-01",
                        point_role="upstream",
                        station=10.0,
                        offset=-1.0,
                        width=3.0,
                        height=2.0,
                    ),
                    StructureConnectionPoint(
                        connection_point_id="connection:outlet-01:pipe-in",
                        structure_ref="structure:outlet-01",
                        point_role="pipe_in",
                        station=18.0,
                        offset=-5.0,
                        diameter=0.8,
                    ),
                ],
            ),
        )
        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-1",
                drainage_model_id="drainage:test",
                element_rows=[
                    DrainageElementRow(
                        drainage_element_id="drainage:inlet-01",
                        element_kind="inlet",
                        structure_ref="structure:inlet-01",
                        connection_point_ref="connection:inlet-01:pipe-out",
                    ),
                    DrainageElementRow(
                        drainage_element_id="drainage:culvert-01",
                        element_kind="culvert_reference",
                        structure_ref="structure:culvert-01",
                        connection_point_ref="connection:culvert-01:upstream",
                    ),
                    DrainageElementRow(
                        drainage_element_id="drainage:outlet-01",
                        element_kind="outfall_reference",
                        structure_ref="structure:outlet-01",
                        connection_point_ref="connection:outlet-01:pipe-in",
                    ),
                ],
                flow_route_rows=[
                    DrainageFlowRoute(
                        flow_route_id="flow-route:pipe-network-01",
                        from_element_ref="drainage:inlet-01",
                        to_element_ref="drainage:culvert-01",
                        outlet_ref="drainage:outlet-01",
                    )
                ],
            ),
        )

        focused = focus_corridor_drainage_flow_review(doc)
        rows = corridor_drainage_flow_review_rows(doc)

        assert focused.Name == "ReviewIssueDrainageFlowRoutes"
        assert focused.DisplayMode == "drainage_flow_pipe_segments"
        assert int(focused.MarkerCount) == 2
        assert int(focused.PipeSegmentCount) == 2
        assert int(focused.StationSpanCount) == 0
        assert rows[0]["highlight_mode"] == "connection_point_pipe"
        assert focused.ConnectionPointRefs == [
            "connection:inlet-01:pipe-out",
            "connection:culvert-01:upstream",
            "connection:outlet-01:pipe-in",
        ]
        assert focused.StructureRefs == [
            "structure:inlet-01",
            "structure:culvert-01",
            "structure:outlet-01",
        ]
    finally:
        App.closeDocument(doc.Name)


def test_preferred_corridor_build_review_row_index_prefers_ready_design_surface() -> None:
    rows = [
        {"role": "centerline", "status": "ready"},
        {"role": "design", "status": "ready"},
        {"role": "subgrade", "status": "ready"},
    ]

    assert preferred_corridor_build_review_row_index(rows) == 1
    assert preferred_corridor_build_review_row_index(rows, preferred_role="subgrade") == 2
    assert preferred_corridor_build_review_row_index([{"role": "design", "status": "missing"}]) is None


def test_corridor_build_review_row_colors_are_dark_theme_readable() -> None:
    assert corridor_build_review_row_color("ready") == (220, 245, 224)
    assert corridor_build_review_row_color("warning") == (255, 241, 205)
    assert corridor_build_review_row_color("missing") == (238, 238, 238)
    assert corridor_build_review_row_color("empty") == (255, 241, 205)
    assert corridor_build_review_row_color("error") == (255, 210, 210)
    assert corridor_build_review_row_color("unknown") is None


def test_corridor_preview_styles_are_role_specific() -> None:
    design = tin_mesh_preview_style("design")
    subgrade = tin_mesh_preview_style("subgrade")
    daylight = tin_mesh_preview_style("daylight")
    drainage = tin_mesh_preview_style("drainage")
    base = tin_mesh_preview_style("unknown")

    assert design["shape_color"] == (1.00, 0.56, 0.12)
    assert subgrade["transparency"] > design["transparency"]
    assert daylight["shape_color"] != design["shape_color"]
    assert drainage["line_width"] > daylight["line_width"]
    assert base == tin_mesh_preview_style("base")
    assert corridor_centerline_preview_style()["line_width"] == 5.0


def test_corridor_preview_visibility_helpers_target_roles_and_markers() -> None:
    class FakeView:
        def __init__(self):
            self.Visibility = True

    class FakeObject:
        def __init__(self, name):
            self.Name = name
            self.ViewObject = FakeView()

    class FakeDocument:
        def __init__(self):
            self.Objects = [
                FakeObject("V1CorridorCenterline3DPreview"),
                FakeObject("V1CorridorDesignSurfacePreview"),
                FakeObject("V1CorridorIntersectionSurfacePreview"),
                FakeObject("V1CorridorIntersectionTieInEdgePreview"),
                FakeObject("V1CorridorIntersectionBoundarySegmentPreview"),
                FakeObject("V1CorridorIntersectionExclusionZonePreview"),
                FakeObject("V1CorridorSubgradeSurfacePreview"),
                FakeObject("V1CorridorDaylightSurfacePreview"),
                FakeObject("V1CorridorRegionSurface_region_rural"),
                FakeObject("ReviewIssueSlopeFaceIssue001L"),
                FakeObject("ReviewIssueDrainageStation001"),
            ]

        def getObject(self, name):
            for obj in self.Objects:
                if obj.Name == name:
                    return obj
            return None

    doc = FakeDocument()

    design = set_corridor_build_preview_visibility(doc, "design", False)
    assert design.Name == "V1CorridorDesignSurfacePreview"
    assert design.ViewObject.Visibility is False
    assert set_corridor_build_preview_visibility(doc, "drainage", False) is None

    changed = set_all_corridor_build_preview_visibility(doc, True, include_issue_markers=True)
    assert changed == 11
    assert doc.getObject("V1CorridorRegionSurface_region_rural").ViewObject.Visibility is False
    assert all(
        obj.ViewObject.Visibility is True
        for obj in doc.Objects
        if obj.Name != "V1CorridorRegionSurface_region_rural"
    )


def test_corridor_guided_review_steps_and_focus_isolate_layers() -> None:
    class FakeView:
        def __init__(self):
            self.Visibility = True

    class FakeObject:
        def __init__(self, name):
            self.Name = name
            self.Label = name
            self.VertexCount = 4
            self.TriangleCount = 2
            self.PointCount = 2
            self.DisplayCurveKind = "line"
            self.ViewObject = FakeView()

    class FakeDocument:
        def __init__(self):
            self.Objects = [
                FakeObject("V1CorridorCenterline3DPreview"),
                FakeObject("V1CorridorDesignSurfacePreview"),
                FakeObject("V1CorridorIntersectionSurfacePreview"),
                FakeObject("V1CorridorIntersectionTieInEdgePreview"),
                FakeObject("V1CorridorIntersectionBoundarySegmentPreview"),
                FakeObject("V1CorridorIntersectionExclusionZonePreview"),
                FakeObject("V1CorridorSubgradeSurfacePreview"),
                FakeObject("V1CorridorDaylightSurfacePreview"),
                FakeObject("V1CorridorRegionSurface_region_rural"),
                FakeObject("ReviewIssueSlopeFaceIssue001L"),
                FakeObject("ReviewIssueSlopeFaceIssue002R"),
            ]
            daylight = self.getObject("V1CorridorDaylightSurfacePreview")
            daylight.SlopeFaceIssueRows = [
                "station_label=STA 0.000;station_index=0;side=L;reason=no EG TIN;status=fallback:no_existing_ground_tin;marker_object=ReviewIssueSlopeFaceIssue001L",
                "station_label=STA 20.000;station_index=1;side=R;reason=no EG TIN;status=fallback:no_existing_ground_tin;marker_object=ReviewIssueSlopeFaceIssue002R",
            ]
            for obj in self.Objects:
                if obj.Name.startswith("V1Corridor"):
                    obj.CRRecordKind = "v1_corridor_surface_preview"
                if obj.Name == "V1CorridorCenterline3DPreview":
                    obj.CRRecordKind = "v1_corridor_centerline_preview"

        def getObject(self, name):
            for obj in self.Objects:
                if obj.Name == name:
                    return obj
            return None

    doc = FakeDocument()

    steps = corridor_build_guided_review_steps(doc)
    assert [step["step_id"] for step in steps] == ["centerline", "design", "intersections", "slope_issues", "drainage", "drainage_flow"]
    assert "supplemental_sections" not in {step["step_id"] for step in steps}
    assert steps[4]["title"] == "6. Drainage Surface"
    assert steps[5]["title"] == "7. Drainage Flow"
    assert steps[3]["status"] == "warning"
    assert steps[3]["focus"] == "First fallback issue marker"

    focused = focus_corridor_build_guided_review_step(doc, "design")
    assert focused.Name == "V1CorridorDesignSurfacePreview"
    assert doc.getObject("V1CorridorCenterline3DPreview").ViewObject.Visibility is True
    assert doc.getObject("V1CorridorDesignSurfacePreview").ViewObject.Visibility is True
    assert doc.getObject("V1CorridorIntersectionSurfacePreview").ViewObject.Visibility is False
    assert doc.getObject("V1CorridorDaylightSurfacePreview").ViewObject.Visibility is False

    focused = focus_corridor_build_guided_review_step(doc, "intersections")
    assert focused.Name == "V1CorridorIntersectionSurfacePreview"
    assert doc.getObject("V1CorridorCenterline3DPreview").ViewObject.Visibility is False
    assert doc.getObject("V1CorridorDesignSurfacePreview").ViewObject.Visibility is False
    assert doc.getObject("V1CorridorIntersectionSurfacePreview").ViewObject.Visibility is True
    assert doc.getObject("V1CorridorIntersectionTieInEdgePreview").ViewObject.Visibility is False
    assert doc.getObject("V1CorridorIntersectionBoundarySegmentPreview").ViewObject.Visibility is False
    assert doc.getObject("V1CorridorIntersectionExclusionZonePreview").ViewObject.Visibility is False
    assert doc.getObject("V1CorridorDaylightSurfacePreview").ViewObject.Visibility is False

    focused = focus_corridor_build_guided_review_step(doc, "slope_issues")
    assert focused.Name == "ReviewIssueSlopeFaceIssue001L"
    assert doc.getObject("V1CorridorDaylightSurfacePreview").ViewObject.Visibility is True
    assert doc.getObject("V1CorridorRegionSurface_region_rural").ViewObject.Visibility is False
    assert doc.getObject("ReviewIssueSlopeFaceIssue001L").ViewObject.Visibility is True

    focused = focus_corridor_slope_face_issue(doc, 1)
    assert focused.Name == "ReviewIssueSlopeFaceIssue002R"
    assert doc.getObject("V1CorridorDesignSurfacePreview").ViewObject.Visibility is False
    assert doc.getObject("V1CorridorDaylightSurfacePreview").ViewObject.Visibility is True

    index, focused = focus_adjacent_corridor_slope_face_issue(doc, current_index=1, direction=1)
    assert index == 0
    assert focused.Name == "ReviewIssueSlopeFaceIssue001L"

    index, focused = focus_adjacent_corridor_slope_face_issue(doc, current_index=0, direction=-1)
    assert index == 1
    assert focused.Name == "ReviewIssueSlopeFaceIssue002R"


def test_apply_v1_corridor_model_creates_drainage_surface_when_ditch_points_exist() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_ditch_points())

        apply_v1_corridor_model(document=doc, project=project)

        surface_obj = find_v1_surface_model(doc)
        assert surface_obj is not None
        assert list(surface_obj.SurfaceKinds) == [
            "design_surface",
            "subgrade_surface",
            "daylight_surface",
            "drainage_surface",
        ]
        drainage_preview = doc.getObject("V1CorridorDrainageSurfacePreview")
        assert drainage_preview is not None
        assert drainage_preview.CRRecordKind == "v1_corridor_surface_preview"
        assert drainage_preview.SurfaceRole == "drainage"
        assert drainage_preview.SurfaceKind == "drainage_surface"
        assert drainage_preview.SurfaceModelId == "surface:main"
        assert drainage_preview.AppliedSectionSetRef == "sections:ditch"
        assert drainage_preview.PreviewStatus == "ready"
        assert int(drainage_preview.PreviewFacetCount) == 16
        assert "surface:main" in list(drainage_preview.SourceRefs)
        assert "sections:ditch" in list(drainage_preview.SourceRefs)
        assert int(drainage_preview.VertexCount) == 20
        assert int(drainage_preview.TriangleCount) == 16
        build_outputs = ensure_project_tree(project, include_references=False)[V1_TREE_BUILD_PARAMETRIC_OUTPUTS]
        assert drainage_preview.Name in _group_names(build_outputs)
        rows = corridor_build_review_rows(doc)
        assert rows[3]["status"] == "error"
        assert "Slope Face Surface preview was not created" in str(rows[3]["notes"])
        assert rows[4]["status"] == "ready"
        assert rows[4]["vertex_count"] == 20
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_corridor_model_does_not_create_centerline_preview_from_applied_section_frames() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_centerline_curve())

        apply_v1_corridor_model(document=doc, project=project)

        centerline = doc.getObject("V1CorridorCenterline3DPreview")
        assert centerline is None
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_corridor_model_prefers_shared_centerline3d_result_preview() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())

        apply_v1_corridor_model(document=doc, project=project)

        centerline = doc.getObject("V1CorridorCenterline3DPreview")
        assert centerline is not None
        assert centerline.PreviewSource == "centerline3d_source_geometry"
        assert centerline.Centerline3DResultId == "centerline3d:main"
        assert centerline.DisplayCurveKind == "source_geometry"
        assert centerline.ConsumedAppliedSectionSetId == "sections:main"
        assert centerline.ConsumedCenterline3DResultId == "centerline3d:main"
        assert centerline.ConsumedCenterlineSourceMode == "centerline3d_source_geometry"
        assert int(centerline.ConsumedSourceSectionCount) == 2
        assert int(centerline.ConsumedSupplementalSectionCount) == 0
        assert int(centerline.ConsumedTotalSectionCount) == 2
        assert int(centerline.CenterlineConsumerFallbackActive) == 0
        assert int(centerline.SupplementalCompatibilityFallbackActive) == 0
        assert "source_mode=centerline3d_source_geometry" in centerline.BuildCorridorConsumerSummary
        assert centerline.WatertightSolidReadinessStatus == "ready"
        assert int(centerline.WatertightSolidAvailableTargetCount) >= 1
        assert int(centerline.WatertightSolidBlockedTargetCount) == 0
        assert "status=ready" in centerline.WatertightSolidReadinessSummary
        assert "road_body_envelope:available=1" in list(centerline.WatertightSolidTargetFamilyCounts)
        assert int(centerline.WatertightSolidEnvelopeTargetCount) >= 1
        assert int(centerline.WatertightSolidPhysicalBodyTargetCount) >= 0
        assert int(centerline.WatertightSolidSurfaceLikeTargetCount) >= 0
        assert centerline.WatertightSolidPhysicalBodyReadinessStatus == "blocked"
        assert "closed Subassembly shape/material contracts" in centerline.WatertightSolidPhysicalBodyReadinessReason
        assert centerline.WatertightSolidDigitalTwinReadinessStatus == "blocked"
        assert "digital_twin_readiness=blocked" in centerline.WatertightSolidDigitalTwinReadinessSummary
        assert "overall=ready" in centerline.WatertightSolidDigitalTwinReadinessSummary
        assert "physical_body=blocked" in centerline.WatertightSolidDigitalTwinReadinessSummary
        assert "envelope:available=1" in list(centerline.WatertightSolidTargetClassCounts)
        assert "physical_body_targets=" in centerline.WatertightSolidReadinessSummary
        assert "physical_body_readiness=blocked" in centerline.WatertightSolidReadinessSummary
        assert "surface_like_targets=" in centerline.WatertightSolidReadinessSummary
        assert int(centerline.WatertightSolidStationSpanCount) >= 1
        assert any(
            str(row).startswith("solid-target:road-body-envelope|road_body_envelope|whole_corridor|")
            for row in list(centerline.WatertightSolidTargetStationSpans)
        )
        assert "station_spans=" in centerline.WatertightSolidReadinessSummary
        assert "region_refs=" in centerline.WatertightSolidReadinessSummary
        assert "material_refs=" in centerline.WatertightSolidReadinessSummary
        assert int(centerline.PointCount) > 2
        rows = corridor_build_review_rows(doc)
        centerline_row = [row for row in rows if row["role"] == "centerline"][0]
        assert centerline_row["status"] == "warning"
        assert "source=centerline3d_source_geometry" in centerline_row["notes"]
        assert "watertight solid readiness=ready" in centerline_row["notes"]
        assert "digital_twin_readiness=blocked" in centerline_row["notes"]
        assert "physical_body_targets=" in centerline_row["notes"]
        assert "physical_body_readiness=blocked" in centerline_row["notes"]
        assert "warning:physical-body watertight readiness=blocked" in centerline_row["notes"]
        assert "station_spans=" in centerline_row["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_corridor_surface_previews_disclose_consumed_result_contracts() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())

        apply_v1_corridor_model(document=doc, project=project)

        preview_names = [
            "V1CorridorDesignSurfacePreview",
            "V1CorridorSubgradeSurfacePreview",
            "V1CorridorDaylightSurfacePreview",
        ]
        for name in preview_names:
            preview = doc.getObject(name)
            assert preview is not None
            assert preview.ConsumedAppliedSectionSetId == "sections:main"
            assert int(preview.ConsumedSourceSectionCount) == 2
            assert int(preview.ConsumedSupplementalSectionCount) == 0
            assert int(preview.ConsumedTotalSectionCount) == 2
            assert int(preview.SupplementalCompatibilityFallbackActive) == 0
            assert "applied=sections:main" in preview.BuildCorridorConsumerSummary
            assert preview.WatertightSolidReadinessStatus == "ready"
            assert int(preview.WatertightSolidAvailableTargetCount) >= 1
            assert "status=ready" in preview.WatertightSolidReadinessSummary
            assert int(preview.WatertightSolidEnvelopeTargetCount) >= 1
            assert "physical_body_targets=" in preview.WatertightSolidReadinessSummary
            assert "physical_body_readiness=" in preview.WatertightSolidReadinessSummary
            assert int(preview.WatertightSolidStationSpanCount) >= 1
            assert "station_spans=" in preview.WatertightSolidReadinessSummary
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solid_readiness_reports_missing_prerequisites() -> None:
    doc, project = _new_project_doc()
    try:
        obj = doc.addObject("App::FeaturePython", "WatertightMissingPrerequisitesProbe")

        build_corridor_command._set_watertight_solid_readiness_properties(
            obj,
            document=doc,
            applied_section_set=None,
            corridor_model=None,
        )

        assert obj.WatertightSolidReadinessStatus == "blocked"
        assert int(obj.WatertightSolidMissingPrerequisiteCount) >= 1
        assert any("missing_applied_sections" in str(row) for row in list(obj.WatertightSolidMissingPrerequisiteRows))
        assert any("missing_corridor_model" in str(row) for row in list(obj.WatertightSolidMissingPrerequisiteRows))
        assert any(
            str(row).startswith("solid-target:road-body-envelope|road_body_envelope|whole_corridor|")
            for row in list(obj.WatertightSolidBlockedTargetRows)
        )
        assert "missing_prerequisites=" in obj.WatertightSolidReadinessSummary
        assert "blocked_targets=" in obj.WatertightSolidReadinessSummary
        assert obj.WatertightSolidDigitalTwinReadinessStatus == "blocked"
        assert "overall=blocked" in obj.WatertightSolidDigitalTwinReadinessSummary
        assert "physical_body=blocked" in obj.WatertightSolidDigitalTwinReadinessSummary
        build_corridor_command._set_preview_property(obj, "SurfaceKind", "design_surface")
        build_corridor_command._set_preview_integer_property(obj, "VertexCount", 4)
        build_corridor_command._set_preview_integer_property(obj, "TriangleCount", 2)
        row = build_corridor_command._corridor_build_review_row(
            "design",
            "Design Surface",
            "WatertightMissingPrerequisitesProbe",
            obj,
        )
        assert row["status"] == "warning"
        assert "watertight solid readiness=blocked" in row["notes"]
        assert "missing_prerequisites=" in row["notes"]
        assert "warning:watertight solid readiness=blocked" in row["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_disclosure_requires_applied_sections_rebuild_for_potential_supplemental_rows() -> None:
    doc, project = _new_project_doc()
    try:
        applied = _sample_sections_with_centerline_curve()
        obj = doc.addObject("App::FeaturePython", "CompatibilityFallbackProbe")

        build_corridor_command._set_corridor_consumer_disclosure_properties(
            obj,
            document=doc,
            applied_section_set=applied,
            corridor_model=None,
            centerline_source_mode="centerline3d_source_geometry",
            centerline_result_id="centerline3d:test",
            supplemental_sampling_max_spacing=5.0,
            supplemental_sampling_tangent_delta_deg=1.0,
            supplemental_sampling_chord_deviation=0.05,
        )

        assert int(obj.ConsumedSourceSectionCount) == 3
        assert int(obj.ConsumedSupplementalSectionCount) == 0
        assert int(obj.SupplementalCompatibilityFallbackActive) == 0
        assert obj.SupplementalCompatibilityPolicy == "rebuild_applied_sections_required"
        assert "no longer creates hidden supplemental frames" in obj.SupplementalCompatibilityReason
        assert int(obj.PotentialSupplementalFrameCount) > 0
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_disclosure_reports_consumed_applied_section_result_roles() -> None:
    doc, project = _new_project_doc()
    try:
        applied = AppliedSectionSet(
            schema_version=1,
            project_id="proj-1",
            applied_section_set_id="sections:roles",
            corridor_id="corridor:main",
            alignment_id="alignment:main",
            station_rows=[AppliedSectionStationRow("station:0", 0.0, "section:0")],
            sections=[
                AppliedSection(
                    schema_version=1,
                    project_id="proj-1",
                    applied_section_id="section:0",
                    corridor_id="corridor:main",
                    alignment_id="alignment:main",
                    station=0.0,
                    region_id="region:ordinary",
                    active_intersection_control_region_refs=["region:intersection-control"],
                    frame=AppliedSectionFrame(station=0.0),
                    subassembly_point_rows=[
                        AppliedSectionSubassemblyPoint("lane:left:start", "lane:left", "fg_surface", 0.0, 0.0, 0.0),
                        AppliedSectionSubassemblyPoint("lane:left:end", "lane:left", "fg_surface", 0.0, 3.5, -0.07),
                    ],
                    subassembly_link_rows=[
                        AppliedSectionSubassemblyLink(
                            "lane:left:fg",
                            "lane:left",
                            "lane:left:start",
                            "lane:left:end",
                            "lane_fg",
                            surface_role="design_surface",
                        )
                    ],
                    subassembly_shape_rows=[
                        AppliedSectionSubassemblyShape(
                            "lane:left:shape",
                            "lane:left",
                            point_refs=["lane:left:start", "lane:left:end", "lane:left:bottom"],
                            shape_code="lane_body",
                            solid_family="pavement_layer",
                        )
                    ],
                )
            ],
        )
        obj = doc.addObject("App::FeaturePython", "RoleCountProbe")

        build_corridor_command._set_corridor_consumer_disclosure_properties(
            obj,
            document=doc,
            applied_section_set=applied,
            corridor_model=None,
            centerline_source_mode="centerline3d_source_geometry",
            centerline_result_id="centerline3d:test",
        )

        assert int(obj.ConsumedSubassemblyLinkCount) == 1
        assert int(obj.ConsumedSubassemblyPointCount) == 2
        assert int(obj.ConsumedSubassemblyShapeCount) == 1
        assert list(obj.ConsumedSurfaceRoleCounts) == ["design_surface=1"]
        assert list(obj.ConsumedPointRoleCounts) == ["fg_surface=2"]
        assert list(obj.ConsumedShapeFamilyCounts) == ["pavement_layer=1"]
        assert int(obj.ConsumedRegionCount) == 2
        assert list(obj.ConsumedRegionRefs) == ["region:intersection-control", "region:ordinary"]
        assert int(obj.ConsumedIntersectionControlRegionCount) == 1
        assert list(obj.ConsumedIntersectionControlRegionRefs) == ["region:intersection-control"]
        assert int(obj.ResultContractCompatibilityFallbackActive) == 0
        assert "link rows are available" in obj.ResultContractCompatibilityReason
        assert "links=1" in obj.BuildCorridorConsumerSummary
        assert "surface_roles=design_surface:1" in obj.BuildCorridorConsumerSummary
        assert "shapes=1" in obj.BuildCorridorConsumerSummary
        assert "regions=2" in obj.BuildCorridorConsumerSummary
        assert "intersection_control_regions=1" in obj.BuildCorridorConsumerSummary
        assert "result_contract_fallback=0" in obj.BuildCorridorConsumerSummary

        build_corridor_command._attach_corridor_surface_role_contract_review_properties(obj, "design")
        assert obj.ResultContractExpectedSurfaceRoleStatus == "ready"
        assert list(obj.ResultContractExpectedSurfaceRoles) == ["design_surface"]
        assert list(obj.ResultContractMatchedSurfaceRoles) == ["design_surface=1"]

        build_corridor_command._set_preview_property(obj, "SurfaceKind", "design_surface")
        build_corridor_command._set_preview_integer_property(obj, "VertexCount", 4)
        build_corridor_command._set_preview_integer_property(obj, "TriangleCount", 2)
        row = build_corridor_command._corridor_build_review_row(
            "design",
            "Design Surface",
            "RoleCountProbe",
            obj,
        )
        assert "region contract: regions=2" in row["notes"]
        assert "refs=region:intersection-control,region:ordinary" in row["notes"]
        assert "intersection_control_regions=1" in row["notes"]
        assert "control_refs=region:intersection-control" in row["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_subassembly_kind_review_does_not_stitch_across_alignment_scopes() -> None:
    doc, project = _new_project_doc()
    try:
        def lane_section(section_id: str, alignment_id: str, station: float, x: float, y: float, tangent: float) -> AppliedSection:
            left_x = x
            left_y = y + 3.5
            if tangent == 90.0:
                left_x = x - 3.5
                left_y = y
            return AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id=section_id,
                corridor_id="corridor:main",
                alignment_id=alignment_id,
                profile_id=f"profile:{alignment_id}",
                assembly_id="assembly:intersection-starter",
                station=station,
                template_id="template:basic-road",
                region_id=f"region:{alignment_id}",
                frame=AppliedSectionFrame(station=station, x=x, y=y, z=10.0, tangent_direction_deg=tangent),
                subassembly_rows=[
                    AppliedSectionSubassemblyRow(
                        subassembly_id="lane:left",
                        kind="lane",
                        source_template_id="template:basic-road",
                        source_instance_ref="lane:left",
                        side="left",
                        width=3.5,
                    )
                ],
                subassembly_point_rows=[
                    AppliedSectionSubassemblyPoint(
                        "lane:left:start",
                        "lane:left",
                        "fg_surface",
                        x,
                        y,
                        10.0,
                        lateral_offset=0.0,
                        side="left",
                    ),
                    AppliedSectionSubassemblyPoint(
                        "lane:left:end",
                        "lane:left",
                        "fg_surface",
                        left_x,
                        left_y,
                        9.93,
                        lateral_offset=3.5,
                        side="left",
                    ),
                ],
                subassembly_link_rows=[
                    AppliedSectionSubassemblyLink(
                        "lane:left:fg",
                        "lane:left",
                        "lane:left:start",
                        "lane:left:end",
                        "lane_fg",
                        surface_role="design_surface",
                    )
                ],
            )

        applied = AppliedSectionSet(
            schema_version=1,
            project_id="proj-1",
            applied_section_set_id="sections:interleaved-alignments",
            corridor_id="corridor:main",
            alignment_id="alignment:primary",
            station_rows=[
                AppliedSectionStationRow("row:primary:0", 0.0, "section:primary:0"),
                AppliedSectionStationRow("row:secondary:0", 0.0, "section:secondary:0"),
                AppliedSectionStationRow("row:primary:20", 20.0, "section:primary:20"),
                AppliedSectionStationRow("row:secondary:20", 20.0, "section:secondary:20"),
            ],
            sections=[
                lane_section("section:primary:0", "alignment:primary", 0.0, 0.0, 0.0, 0.0),
                lane_section("section:secondary:0", "alignment:secondary", 0.0, 50.0, 0.0, 90.0),
                lane_section("section:primary:20", "alignment:primary", 20.0, 20.0, 0.0, 0.0),
                lane_section("section:secondary:20", "alignment:secondary", 20.0, 50.0, 20.0, 90.0),
            ],
        )
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=applied)

        obj = build_corridor_command._create_subassembly_kind_review_highlight(
            document=doc,
            project=project,
            kind="lane",
            visible=False,
        )

        assert obj is not None
        assert int(obj.SectionCount) == 4
        assert int(obj.ContinuityScopeCount) == 2
        assert int(obj.SurfacePatchCount) == 4
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_review_warns_when_expected_surface_role_is_missing() -> None:
    doc, project = _new_project_doc()
    try:
        obj = doc.addObject("App::FeaturePython", "MissingSurfaceRoleProbe")
        build_corridor_command._set_preview_string_list_property(obj, "ConsumedSurfaceRoleCounts", ["drainage_surface=1"])
        build_corridor_command._attach_corridor_surface_role_contract_review_properties(obj, "design")
        build_corridor_command._set_preview_property(obj, "SurfaceKind", "design_surface")
        build_corridor_command._set_preview_integer_property(obj, "VertexCount", 4)
        build_corridor_command._set_preview_integer_property(obj, "TriangleCount", 2)

        assert obj.ResultContractExpectedSurfaceRoleStatus == "missing"
        assert list(obj.ResultContractExpectedSurfaceRoles) == ["design_surface"]
        assert list(obj.ResultContractMatchedSurfaceRoles) == []
        row = build_corridor_command._corridor_build_review_row(
            "design",
            "Design Surface",
            "MissingSurfaceRoleProbe",
            obj,
        )
        assert row["status"] == "warning"
        assert "surface role contract=missing" in row["notes"]
        assert "consumed=drainage_surface=1" in row["notes"]
        assert "warning:expected surface role missing=design_surface" in row["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_review_warns_when_consumed_result_contract_links_are_missing() -> None:
    doc, project = _new_project_doc()
    try:
        obj = doc.addObject("App::FeaturePython", "MissingResultContractProbe")
        build_corridor_command._set_corridor_consumer_disclosure_properties(
            obj,
            document=doc,
            applied_section_set=_sample_sections(),
            corridor_model=None,
            centerline_source_mode="centerline3d_source_geometry",
            centerline_result_id="centerline3d:test",
        )
        build_corridor_command._set_preview_property(obj, "SurfaceKind", "design_surface")
        build_corridor_command._set_preview_integer_property(obj, "VertexCount", 4)
        build_corridor_command._set_preview_integer_property(obj, "TriangleCount", 2)

        assert int(obj.ResultContractCompatibilityFallbackActive) == 1
        assert "legacy width/point result fields" in obj.ResultContractCompatibilityReason
        row = build_corridor_command._corridor_build_review_row(
            "design",
            "Design Surface",
            "MissingResultContractProbe",
            obj,
        )
        assert row["status"] == "warning"
        assert "warning:result contract fallback active" in row["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_command_does_not_reverse_read_preview_shapes_as_source() -> None:
    source = Path(build_corridor_command.__file__).read_text(encoding="utf-8")

    forbidden_getattr_patterns = [
        'getattr(obj, "Shape",',
        "getattr(obj, 'Shape',",
        'getattr(preview_obj, "Shape",',
        "getattr(preview_obj, 'Shape',",
    ]
    for pattern in forbidden_getattr_patterns:
        assert pattern not in source

    for line in source.splitlines():
        text = line.strip()
        if ".Shape" not in text:
            continue
        if ".ShapeColor" in text:
            continue
        if ".Shape =" in text:
            continue
        if "part_module.Shape()" in text:
            continue
        assert False, text


def test_corridor_build_review_warns_when_centerline_consumer_uses_fallback() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())

        apply_v1_corridor_model(document=doc, project=project)

        centerline = doc.getObject("V1CorridorCenterline3DPreview")
        assert centerline is not None
        build_corridor_command._set_preview_property(centerline, "ConsumedCenterlineSourceMode", "centerline3d_result_fallback")
        build_corridor_command._set_preview_integer_property(centerline, "CenterlineConsumerFallbackActive", 1)

        rows = corridor_build_review_rows(doc)
        centerline_row = next(row for row in rows if row["role"] == "centerline")

        assert centerline_row["status"] == "warning"
        assert centerline_row["output_path"] == "inferred_fallback"
        assert "warning:centerline source fallback=centerline3d_result_fallback" in str(centerline_row["notes"])
        assert "expected=centerline3d_source_geometry" in str(centerline_row["notes"])
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 build corridor command contract tests completed.")
