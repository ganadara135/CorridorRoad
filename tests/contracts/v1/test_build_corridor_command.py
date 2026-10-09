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
    corridor_drainage_review_rows,
    corridor_drainage_review_summary,
    corridor_slope_face_issue_rows,
    document_has_v1_applied_sections,
    focus_adjacent_corridor_slope_face_issue,
    focus_corridor_build_guided_review_step,
    focus_corridor_drainage_flow_review,
    focus_corridor_drainage_review_row,
    focus_corridor_region_boundary_row,
    focus_corridor_slope_face_issue,
    preferred_corridor_build_review_row_index,
    set_all_corridor_build_preview_visibility,
    set_corridor_build_daylight_contact_marker_visibility,
    set_corridor_build_preview_visibility,
    show_corridor_build_review_object,
    show_corridor_slope_face_issue_marker,
    create_corridor_region_surface_previews,
    create_or_update_corridor_surface_transition_for_boundary,
    create_corridor_surface_transition_from_region_boundary,
    toggle_corridor_surface_transition_enabled,
    update_corridor_surface_transition_station_range,
)
from freecad.Corridor_Road.v1.models.result.tin_surface import TINQualityRow, TINSurface, TINTriangle, TINVertex
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
from dataclasses import replace
from freecad.Corridor_Road.v1.services.builders import (
    suppress_daylight_triangles_above_intersection_surface,
    suppress_daylight_triangles_inside_intersection_slope_face_loop_footprint,
    suppress_daylight_triangles_inside_intersection_surface_footprint,
    trim_daylight_triangles_above_intersection_surface_by_intersection_lines,
)
from freecad.Corridor_Road.v1.services.builders.shared_breakline_tin_builder_service import (
    intersection_surface_tin_with_shared_breakline_constraint_edges,
    tin_surface_with_shared_breakline_constraint_edges,
    tin_surface_with_shared_breakline_metadata,
)
from freecad.Corridor_Road.v1.ui.presentation import (
    build_review_presentation,
    shared_breakline_audit_presentation,
)

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
        # one strip between the two stations; supplemental sampling no longer adds frames
        assert int(preview.PreviewFacetCount) == 2
        assert "surface:main" in list(preview.SourceRefs)
        assert "sections:main" in list(preview.SourceRefs)
        assert int(preview.VertexCount) == 4
        assert int(preview.TriangleCount) == 2
        centerline = doc.getObject("V1CorridorCenterline3DPreview")
        assert centerline is None
        subgrade_preview = doc.getObject("V1CorridorSubgradeSurfacePreview")
        assert subgrade_preview is not None
        assert subgrade_preview.CRRecordKind == "v1_corridor_surface_preview"
        assert subgrade_preview.SurfaceRole == "subgrade"
        assert subgrade_preview.SurfaceKind == "subgrade_surface"
        assert subgrade_preview.PreviewStatus == "ready"
        assert subgrade_preview.AppliedSectionSetRef == "sections:main"
        assert int(subgrade_preview.VertexCount) == 4
        assert int(subgrade_preview.TriangleCount) == 2
        daylight_preview = doc.getObject("V1CorridorDaylightSurfacePreview")
        assert daylight_preview is not None
        assert daylight_preview.CRRecordKind == "v1_corridor_surface_preview"
        assert daylight_preview.SurfaceRole == "daylight"
        assert daylight_preview.SurfaceKind == "daylight_surface"
        assert daylight_preview.PreviewStatus == "ready"
        assert daylight_preview.AppliedSectionSetRef == "sections:main"
        assert int(daylight_preview.VertexCount) == 8
        assert int(daylight_preview.TriangleCount) == 4
        assert int(daylight_preview.EGIntersectionCount) == 0
        assert int(daylight_preview.EGTieInHitCount) == 0
        assert int(daylight_preview.SlopeFaceFallbackCount) == 4
        assert int(daylight_preview.SlopeFaceNoExistingGroundCount) == 4
        assert int(daylight_preview.SlopeFaceNoEGHitCount) == 0
        assert "fallbacks: 4" in daylight_preview.SlopeFaceDiagnosticSummary
        assert "no EG TIN: 4" in daylight_preview.SlopeFaceDiagnosticSummary
        assert "STA 0.000 L no EG TIN" in daylight_preview.SlopeFaceIssueStations
        assert "STA 20.000 R no EG TIN" in daylight_preview.SlopeFaceIssueStations
        assert len(list(daylight_preview.SlopeFaceIssueRows)) == 4
        issue_rows = corridor_slope_face_issue_rows(doc)
        assert issue_rows[0]["station_label"] == "STA 0.000"
        assert issue_rows[0]["side"] == "L"
        assert issue_rows[0]["reason"] == "no EG TIN"
        assert issue_rows[0]["marker_object"] == "ReviewIssueSlopeFaceIssue001L"
        assert issue_rows[-1]["station_label"] == "STA 20.000"
        assert issue_rows[-1]["side"] == "R"
        # the aggregate marker is a ReviewDiagnostic; the per-issue markers stay ReviewIssue
        fallback_markers = doc.getObject("ReviewDiagnosticSlopeFaceFallbackMarkers")
        assert fallback_markers is not None
        assert fallback_markers.V1ObjectType == "ReviewDiagnostic"
        assert fallback_markers.IssueKind == "slope_face_tie_in_diagnostic"
        assert int(fallback_markers.MarkerCount) == 4
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
        assert progress_events[-1] == (94, "Finalizing document transaction...")
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
        review_row = build_review_presentation._corridor_build_review_row(
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
        # the panel fills each review tab on demand, the way opening it does
        panel._load_review_tab("intersections")

        # the tab shows the intersection kernel's rows; with no Applied Sections there is one
        # missing row saying so
        assert panel._intersection_contract_table.rowCount() == len(
            corridor_intersection_contract_review_rows(doc)
        )
        assert panel._intersection_contract_table.columnCount() == 10
        assert panel._intersection_contract_table.item(0, 0).text() == "intersection"
        assert panel._intersection_contract_table.item(0, 1).text() == "missing"
        assert panel._intersection_contract_table.item(0, 2).text() == "spec"
        assert panel._intersection_contract_table.item(0, 3).text() == "intersection_kernel"
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_panel_defers_inactive_review_tabs() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(
            doc,
            project=project,
            applied_section_set=_sample_sections_with_region_boundary(),
        )

        panel = V1BuildCorridorTaskPanel(document=doc)

        assert panel._loaded_review_tabs == {"guided"}
        assert panel._review_table.rowCount() == 0
        assert panel._intersection_contract_table.rowCount() == 0
        assert panel._drainage_table.rowCount() == 0

        panel._tabs.setCurrentIndex(1)

        assert "results" in panel._loaded_review_tabs
        assert panel._review_table.rowCount() > 0

        panel._tabs.setCurrentIndex(3)

        assert "intersections" in panel._loaded_review_tabs
        assert panel._intersection_contract_table.rowCount() > 0
    finally:
        App.closeDocument(doc.Name)


def test_intersection_slope_loop_suppression_skips_quality_rejected_reference_surface() -> None:
    daylight = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="slope_face_surface",
        vertex_rows=[
            TINVertex("d0", 0.0, 0.0, 10.0),
            TINVertex("d1", 10.0, 0.0, 10.0),
            TINVertex("d2", 0.0, 10.0, 9.0),
        ],
        triangle_rows=[
            TINTriangle("daylight:tri:1", "d0", "d1", "d2", quality_ref="side_slope_surface"),
        ],
    )
    rejected_reference = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:intersection-slope-face",
        surface_kind="intersection_slope_face_surface",
        boundary_refs=["loop:test:quality-rejected"],
        quality_rows=[
            TINQualityRow("q:ready", "ready_loop_count", 1, "count"),
            TINQualityRow("q:generated", "generated_loop_count", 0, "count"),
            TINQualityRow("q:skinny", "rejected_skinny_loop_count", 1, "count"),
        ],
    )

    suppressed = suppress_daylight_triangles_inside_intersection_slope_face_loop_footprint(
        daylight,
        rejected_reference,
    )

    assert [triangle.triangle_id for triangle in suppressed.triangle_rows] == ["daylight:tri:1"]
    assert build_corridor_command._tin_quality_text(suppressed, "intersection_slope_loop_suppress_status") == "skipped"
    assert build_corridor_command._tin_quality_float(suppressed, "intersection_slope_loop_suppress_suppressed_triangle_count") == 0
    assert build_corridor_command._tin_quality_float(suppressed, "intersection_slope_loop_suppress_reference_triangle_count") == 0
    assert build_corridor_command._tin_quality_float(suppressed, "intersection_slope_loop_suppress_kept_triangle_count") == 1
    assert list(getattr(suppressed, "void_refs", []) or []) == []


def test_intersection_slope_loop_suppression_uses_generated_ready_loop_footprint_only() -> None:
    daylight = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="slope_face_surface",
        vertex_rows=[
            TINVertex("inside-a", 1.0, 1.0, 10.0),
            TINVertex("inside-b", 2.0, 1.0, 10.0),
            TINVertex("inside-c", 1.0, 2.0, 10.0),
            TINVertex("outside-a", 20.0, 20.0, 10.0),
            TINVertex("outside-b", 21.0, 20.0, 10.0),
            TINVertex("outside-c", 20.0, 21.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("daylight:inside", "inside-a", "inside-b", "inside-c", quality_ref="side_slope_surface"),
            TINTriangle("daylight:outside", "outside-a", "outside-b", "outside-c", quality_ref="side_slope_surface"),
        ],
    )
    reference = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:intersection-slope-face",
        surface_kind="intersection_slope_face_surface",
        boundary_refs=["loop:test:generated"],
        vertex_rows=[
            TINVertex("r0", 0.0, 0.0, 10.0),
            TINVertex("r1", 5.0, 0.0, 10.0),
            TINVertex("r2", 0.0, 5.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("ref:tri:1", "r0", "r1", "r2", quality_ref="intersection_slope_face_loop"),
        ],
    )

    suppressed = suppress_daylight_triangles_inside_intersection_slope_face_loop_footprint(
        daylight,
        reference,
    )

    assert [triangle.triangle_id for triangle in suppressed.triangle_rows] == ["daylight:outside"]
    assert build_corridor_command._tin_quality_text(suppressed, "intersection_slope_loop_suppress_status") == "ready"
    assert build_corridor_command._tin_quality_float(suppressed, "intersection_slope_loop_suppress_ready_loop_count") == 1
    assert build_corridor_command._tin_quality_float(suppressed, "intersection_slope_loop_suppress_suppressed_triangle_count") == 1
    assert build_corridor_command._tin_quality_float(suppressed, "intersection_slope_loop_suppress_kept_triangle_count") == 1
    assert list(getattr(suppressed, "void_refs", []) or []) == ["surface:intersection-slope-face"]


def test_intersection_slope_loop_suppression_uses_intersection_slope_face_footprint() -> None:
    daylight = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:daylight",
        surface_kind="slope_face_surface",
        vertex_rows=[
            TINVertex("inside-a", 1.0, 1.0, 10.0),
            TINVertex("inside-b", 2.0, 1.0, 10.0),
            TINVertex("inside-c", 1.0, 2.0, 10.0),
            TINVertex("outside-a", 10.0, 10.0, 10.0),
            TINVertex("outside-b", 11.0, 10.0, 10.0),
            TINVertex("outside-c", 10.0, 11.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("daylight:inside-transition-cell", "inside-a", "inside-b", "inside-c", quality_ref="side_slope_surface"),
            TINTriangle("daylight:outside", "outside-a", "outside-b", "outside-c", quality_ref="side_slope_surface"),
        ],
    )
    reference = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:intersection-slope-face",
        surface_kind="intersection_slope_face_surface",
        boundary_refs=["intersection-slope-face-cell:test:curb-return"],
        vertex_rows=[
            TINVertex("r0", 0.0, 0.0, 10.0),
            TINVertex("r1", 5.0, 0.0, 10.0),
            TINVertex("r2", 0.0, 5.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle(
                "ref:curb-return-cell:1",
                "r0",
                "r1",
                "r2",
                triangle_kind="intersection_slope_face_curb_return_cell",
                quality_ref="intersection_slope_face_cell",
            ),
        ],
    )

    suppressed = suppress_daylight_triangles_inside_intersection_slope_face_loop_footprint(
        daylight,
        reference,
    )

    assert [triangle.triangle_id for triangle in suppressed.triangle_rows] == ["daylight:outside"]
    assert build_corridor_command._tin_quality_text(suppressed, "intersection_slope_loop_suppress_status") == "ready"
    assert build_corridor_command._tin_quality_float(suppressed, "intersection_slope_loop_suppress_suppressed_triangle_count") == 1
    assert list(getattr(suppressed, "void_refs", []) or []) == ["surface:intersection-slope-face"]


def _curb_return_variant_model(*, radius: float = 12.0) -> IntersectionModel:
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
                intersection_point_x=20.0,
                intersection_point_y=0.0,
            )
        ],
        curb_return_policy_rows=[
            IntersectionCurbReturnPolicyRow(
                policy_id="curb-return:intersection:t-01:default",
                intersection_id="intersection:t-01",
                radius=radius,
            )
        ],
    )


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

    clipped = suppress_daylight_triangles_above_intersection_surface(
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

    clipped = suppress_daylight_triangles_inside_intersection_surface_footprint(
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

    trimmed = trim_daylight_triangles_above_intersection_surface_by_intersection_lines(
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


def test_intersection_surface_tin_inserts_missing_shared_breakline_endpoint_vertices_with_source_refs() -> None:
    breakline_id = "shared-breakline:intersection:intersection:t-01:patch-to-slope-face"
    shared = build_corridor_command.SharedBreaklineResult(
        schema_version=1,
        project_id="proj-1",
        breakline_result_id="shared-breakline:intersection:intersection:t-01",
        domain_kind="intersection",
        domain_ref="intersection:t-01",
        status="ready",
        breakline_count=1,
        ready_count=1,
        breakline_rows=[
            build_corridor_command.SharedBreaklineRow(
                breakline_id=breakline_id,
                domain_kind="intersection",
                domain_ref="intersection:t-01",
                breakline_role="patch_to_slope_face",
                consumer_refs=("intersection_surface", "slope_face_surface"),
                point_refs=("p0", "p1"),
                source_status="ready",
            )
        ],
        point_rows=[
            build_corridor_command.SharedBreaklinePointRow(
                "p0",
                breakline_id,
                0,
                0.0,
                0.0,
                10.0,
                source_point_ref="intersection-boundary:patch-to-slope:start",
            ),
            build_corridor_command.SharedBreaklinePointRow(
                "p1",
                breakline_id,
                1,
                10.0,
                0.0,
                10.0,
                source_point_ref="intersection-boundary:patch-to-slope:end",
            ),
        ],
    )

    updated_vertices, updated_triangles, stats = intersection_surface_tin_with_shared_breakline_constraint_edges(
        vertices=[
            TINVertex("near-a", 0.0, 2.0, 10.0),
            TINVertex("near-b", 10.0, 2.0, 10.0),
            TINVertex("near-c", 5.0, 5.0, 10.0),
        ],
        triangles=[TINTriangle("base", "near-a", "near-b", "near-c")],
        shared_result=shared,
        surface_id="surface:intersection",
    )
    inserted = [
        vertex
        for vertex in updated_vertices
        if str(getattr(vertex, "vertex_id", "") or "").startswith("surface:intersection:shared-breakline-point:")
    ]

    assert stats["segment_count"] == 1
    assert stats["edge_count"] == 1
    assert stats["vertex_count"] == 3
    assert len(inserted) == 2
    assert {vertex.source_point_ref for vertex in inserted} == {
        "intersection-boundary:patch-to-slope:start",
        "intersection-boundary:patch-to-slope:end",
    }
    assert all(f"shared_breakline_ref={breakline_id}" in vertex.notes for vertex in inserted)
    assert any(triangle.quality_ref == "shared_breakline_constraint_edge" for triangle in updated_triangles)


def test_shared_breakline_constraint_edges_snap_generated_vertices_without_changing_source_points() -> None:
    breakline_id = "shared-breakline:intersection:intersection:t-01:patch-to-design"
    shared = build_corridor_command.SharedBreaklineResult(
        schema_version=1,
        project_id="proj-1",
        breakline_result_id="shared-breakline:intersection:intersection:t-01",
        domain_kind="intersection",
        domain_ref="intersection:t-01",
        status="ready",
        breakline_count=1,
        ready_count=1,
        breakline_rows=[
            build_corridor_command.SharedBreaklineRow(
                breakline_id=breakline_id,
                domain_kind="intersection",
                domain_ref="intersection:t-01",
                breakline_role="patch_to_design_pavement_tie_in",
                consumer_refs=("intersection_surface", "design_surface"),
                point_refs=("p0", "p1"),
                source_status="ready",
            )
        ],
        point_rows=[
            build_corridor_command.SharedBreaklinePointRow("p0", breakline_id, 0, 0.0, 0.0, 10.0, source_point_ref="source:start"),
            build_corridor_command.SharedBreaklinePointRow("p1", breakline_id, 1, 10.0, 0.0, 10.0, source_point_ref="source:end"),
        ],
    )
    original_source_points = [(point.x, point.y, point.z, point.source_point_ref) for point in shared.point_rows]
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:intersection",
        surface_kind="intersection_surface",
        vertex_rows=[
            TINVertex("near-start", 0.012, -0.006, 10.0),
            TINVertex("near-end", 9.991, 0.004, 10.0),
            TINVertex("support-a", 4.0, 3.0, 10.0),
            TINVertex("support-b", 6.0, -3.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("left", "near-start", "support-a", "support-b"),
            TINTriangle("right", "near-end", "support-b", "support-a"),
        ],
    )

    constrained = tin_surface_with_shared_breakline_constraint_edges(
        surface,
        shared,
        consumer_ref="intersection_surface",
    )
    constrained = tin_surface_with_shared_breakline_metadata(
        constrained,
        shared,
        consumer_ref="intersection_surface",
    )
    vertex_by_id = constrained.vertex_map()
    audit = build_corridor_command.shared_breakline_audit(shared, {"intersection_surface": constrained})

    assert (vertex_by_id["near-start"].x, vertex_by_id["near-start"].y, vertex_by_id["near-start"].z) == (0.0, 0.0, 10.0)
    assert (vertex_by_id["near-end"].x, vertex_by_id["near-end"].y, vertex_by_id["near-end"].z) == (10.0, 0.0, 10.0)
    assert "snapped_to_accepted_breakline" in vertex_by_id["near-start"].notes
    assert "snapped_to_accepted_breakline" in vertex_by_id["near-end"].notes
    assert [(point.x, point.y, point.z, point.source_point_ref) for point in shared.point_rows] == original_source_points
    assert build_corridor_command._tin_quality_float(constrained, "shared_breakline_constraint_snap_count") == 2
    assert build_corridor_command._tin_quality_float(constrained, "shared_breakline_constraint_vertex_count") == 1
    assert "snapped_result_vertex:near-start" in build_corridor_command._tin_quality_text(constrained, "shared_breakline_constraint_snap_diagnostics")
    assert audit["status"] == "ready"
    assert audit["geometry_mismatch_count"] == 0
    assert audit["mesh_mismatch_count"] == 0


def test_boundary_loop_constraint_edges_expose_role_summary_quality_row() -> None:
    arc_ref = "shared-breakline:intersection:cross-01:curb-return-arc"
    connector_ref = "shared-breakline:intersection:cross-01:patch-connector"
    shared = build_corridor_command.SharedBreaklineResult(
        schema_version=1,
        project_id="proj-1",
        breakline_result_id="shared-breakline:intersection:cross-01",
        domain_kind="intersection",
        domain_ref="cross-01",
        status="ready",
        breakline_count=2,
        ready_count=2,
        breakline_rows=[
            build_corridor_command.SharedBreaklineRow(
                breakline_id=arc_ref,
                domain_kind="intersection",
                domain_ref="cross-01",
                breakline_role="curb_return_to_intersection_slope_face",
                consumer_refs=("intersection_surface", "intersection_slope_face_surface"),
                point_refs=("arc:p0", "arc:p1"),
                source_contract_refs=(
                    "intersection-boundary-loops:cross-01",
                    "intersection-boundary-loop:cross-01:outer",
                    "intersection-boundary-envelope:cross-01:corner:01:arc:01",
                ),
                source_status="ready",
            ),
            build_corridor_command.SharedBreaklineRow(
                breakline_id=connector_ref,
                domain_kind="intersection",
                domain_ref="cross-01",
                breakline_role="patch_to_design_surface",
                consumer_refs=("intersection_surface", "design_surface", "intersection_slope_face_surface"),
                point_refs=("connector:p0", "connector:p1"),
                source_contract_refs=(
                    "intersection-boundary-loops:cross-01",
                    "intersection-boundary-loop:cross-01:outer",
                    "intersection-boundary-envelope:cross-01:corner-connector:02",
                ),
                source_status="ready",
            ),
        ],
        point_rows=[
            build_corridor_command.SharedBreaklinePointRow("arc:p0", arc_ref, 0, 0.0, 0.0, 10.0),
            build_corridor_command.SharedBreaklinePointRow("arc:p1", arc_ref, 1, 4.0, 0.0, 10.0),
            build_corridor_command.SharedBreaklinePointRow("connector:p0", connector_ref, 0, 4.0, 0.0, 10.0),
            build_corridor_command.SharedBreaklinePointRow("connector:p1", connector_ref, 1, 4.0, 3.0, 10.0),
        ],
    )
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:intersection",
        surface_kind="intersection_surface",
        vertex_rows=[
            TINVertex("v1", 0.0, 0.0, 10.0),
            TINVertex("v2", 4.0, 0.0, 10.0),
            TINVertex("v3", 4.0, 3.0, 10.0),
            TINVertex("v4", 0.0, 3.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("t1", "v1", "v2", "v3"),
            TINTriangle("t2", "v1", "v3", "v4"),
        ],
    )

    constrained = tin_surface_with_shared_breakline_constraint_edges(
        surface,
        shared,
        consumer_ref="intersection_surface",
    )

    assert build_corridor_command._tin_quality_float(constrained, "shared_breakline_boundary_loop_constraint_segment_count") == 2
    assert build_corridor_command._tin_quality_float(constrained, "shared_breakline_boundary_loop_constraint_edge_count") == 2
    role_summary = build_corridor_command._tin_quality_text(
        constrained,
        "shared_breakline_boundary_loop_constraint_role_summary",
    )
    assert "curb_return_to_intersection_slope_face=1" in role_summary
    assert "patch_to_design_surface=1" in role_summary


def test_shared_breakline_constraint_edges_apply_to_design_surface_mesh() -> None:
    breakline_id = "shared-breakline:corridor:corridor:main:lane_to_shoulder:1"
    shared = build_corridor_command.SharedBreaklineResult(
        schema_version=1,
        project_id="proj-1",
        breakline_result_id="shared-breakline:corridor:corridor:main",
        domain_kind="corridor",
        domain_ref="corridor:main",
        status="ready",
        breakline_count=1,
        ready_count=1,
        breakline_rows=[
            build_corridor_command.SharedBreaklineRow(
                breakline_id=breakline_id,
                domain_kind="corridor",
                domain_ref="corridor:main",
                breakline_role="lane_to_shoulder",
                consumer_refs=("design_surface",),
                point_refs=("p0", "p1"),
                source_status="ready",
            )
        ],
        point_rows=[
            build_corridor_command.SharedBreaklinePointRow("p0", breakline_id, 0, 0.0, 3.5, 10.0),
            build_corridor_command.SharedBreaklinePointRow("p1", breakline_id, 1, 20.0, 3.5, 10.0),
        ],
    )
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:design",
        surface_kind="design_surface",
        vertex_rows=[
            TINVertex("a", 0.0, 3.5, 10.0),
            TINVertex("b", 20.0, 3.5, 10.0),
            TINVertex("c", 8.0, 0.0, 10.0),
            TINVertex("d", 12.0, 7.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("left", "a", "c", "d"),
            TINTriangle("right", "b", "d", "c"),
        ],
    )

    constrained = tin_surface_with_shared_breakline_constraint_edges(
        surface,
        shared,
        consumer_ref="design_surface",
    )
    constrained = tin_surface_with_shared_breakline_metadata(
        constrained,
        shared,
        consumer_ref="design_surface",
    )
    audit = build_corridor_command.shared_breakline_audit(shared, {"design_surface": constrained})

    assert audit["status"] == "ready"
    assert audit["mesh_match_count"] == 1
    assert audit["mesh_mismatch_count"] == 0
    assert build_corridor_command._tin_quality_float(constrained, "shared_breakline_constraint_edge_count") == 1


def test_shared_breakline_constraint_edges_reuse_existing_coordinate_edge() -> None:
    breakline_id = "shared-breakline:corridor:corridor:main:side_slope_to_daylight:1"
    shared = build_corridor_command.SharedBreaklineResult(
        schema_version=1,
        project_id="proj-1",
        breakline_result_id="shared-breakline:corridor:corridor:main",
        domain_kind="corridor",
        domain_ref="corridor:main",
        status="ready",
        breakline_count=1,
        ready_count=1,
        breakline_rows=[
            build_corridor_command.SharedBreaklineRow(
                breakline_id=breakline_id,
                domain_kind="corridor",
                domain_ref="corridor:main",
                breakline_role="side_slope_to_daylight",
                consumer_refs=("slope_face_surface",),
                point_refs=("p0", "p1"),
                material_role="slope_face_surface",
                source_status="ready",
            )
        ],
        point_rows=[
            build_corridor_command.SharedBreaklinePointRow("p0", breakline_id, 0, 0.0, 8.0, 8.5),
            build_corridor_command.SharedBreaklinePointRow("p1", breakline_id, 1, 20.0, 8.0, 8.5),
        ],
    )
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:slope",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("edge-a", 0.0, 8.0, 8.5),
            TINVertex("edge-b", 20.0, 8.0, 8.5),
            TINVertex("inside", 10.0, 5.0, 9.5),
            TINVertex("duplicate-a", 0.0, 8.0, 8.5),
            TINVertex("duplicate-b", 20.0, 8.0, 8.5),
        ],
        triangle_rows=[
            TINTriangle("existing-coordinate-edge", "edge-a", "edge-b", "inside"),
        ],
    )

    constrained = tin_surface_with_shared_breakline_constraint_edges(
        surface,
        shared,
        consumer_ref="slope_face_surface",
    )
    constrained = tin_surface_with_shared_breakline_metadata(
        constrained,
        shared,
        consumer_ref="slope_face_surface",
    )
    audit = build_corridor_command.shared_breakline_audit(shared, {"slope_face_surface": constrained})

    assert audit["status"] == "ready"
    assert audit["mesh_match_count"] == 1
    assert audit["mesh_mismatch_count"] == 0
    assert build_corridor_command._tin_quality_float(constrained, "shared_breakline_constraint_edge_count") == 0
    assert len(constrained.triangle_rows) == 1


def test_shared_breakline_constraint_edges_reuse_existing_edge_chain() -> None:
    breakline_id = "shared-breakline:corridor:corridor:main:side_slope_to_daylight:chain"
    shared = build_corridor_command.SharedBreaklineResult(
        schema_version=1,
        project_id="proj-1",
        breakline_result_id="shared-breakline:corridor:corridor:main",
        domain_kind="corridor",
        domain_ref="corridor:main",
        status="ready",
        breakline_count=1,
        ready_count=1,
        breakline_rows=[
            build_corridor_command.SharedBreaklineRow(
                breakline_id=breakline_id,
                domain_kind="corridor",
                domain_ref="corridor:main",
                breakline_role="side_slope_to_daylight",
                consumer_refs=("slope_face_surface",),
                point_refs=("p0", "p1"),
                material_role="slope_face_surface",
                source_status="ready",
            )
        ],
        point_rows=[
            build_corridor_command.SharedBreaklinePointRow("p0", breakline_id, 0, 0.0, 8.0, 8.5),
            build_corridor_command.SharedBreaklinePointRow("p1", breakline_id, 1, 20.0, 8.0, 8.5),
        ],
    )
    surface = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="surface:slope-chain",
        surface_kind="daylight_surface",
        vertex_rows=[
            TINVertex("edge-a", 0.0, 8.0, 8.5),
            TINVertex("edge-mid", 10.0, 8.0, 8.5),
            TINVertex("edge-b", 20.0, 8.0, 8.5),
            TINVertex("inside-left", 5.0, 5.0, 9.5),
            TINVertex("inside-right", 15.0, 5.0, 9.5),
        ],
        triangle_rows=[
            TINTriangle("existing-chain-left", "edge-a", "edge-mid", "inside-left"),
            TINTriangle("existing-chain-right", "edge-mid", "edge-b", "inside-right"),
        ],
    )

    constrained = tin_surface_with_shared_breakline_constraint_edges(
        surface,
        shared,
        consumer_ref="slope_face_surface",
    )
    constrained = tin_surface_with_shared_breakline_metadata(
        constrained,
        shared,
        consumer_ref="slope_face_surface",
    )
    audit = build_corridor_command.shared_breakline_audit(shared, {"slope_face_surface": constrained})

    assert audit["status"] == "ready"
    assert audit["mesh_match_count"] == 1
    assert audit["mesh_mismatch_count"] == 0
    assert build_corridor_command._tin_quality_float(constrained, "shared_breakline_constraint_edge_count") == 0
    assert len(constrained.triangle_rows) == 2


def test_corridor_general_shared_breakline_splits_slope_face_when_boundary_slot_changes() -> None:
    def section(section_id: str, station: float, x: float, outer_role: str, outer_offset: float) -> AppliedSection:
        return AppliedSection(
            schema_version=1,
            project_id="proj-1",
            applied_section_id=section_id,
            corridor_id="corridor:main",
            alignment_id="alignment:main",
            region_id="region:ordinary",
            station=station,
            frame=AppliedSectionFrame(station=station, x=x, y=0.0, z=10.0),
            point_rows=[
                AppliedSectionPoint(f"{section_id}:left:hinge", x, 4.5, 9.90, "side_slope_surface", 4.5, side="left"),
                AppliedSectionPoint(f"{section_id}:left:outer", x, outer_offset, 8.75, outer_role, outer_offset, side="left"),
            ],
        )

    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:slope-slot-change",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        sections=[
            section("section:0", 0.0, 0.0, "daylight_marker", 8.0),
            section("section:10", 10.0, 10.0, "side_slope_surface", 16.0),
            section("section:20", 20.0, 20.0, "daylight_marker", 8.0),
        ],
    )

    shared = build_corridor_command.corridor_general_shared_breakline_result(applied)
    slope_rows = [row for row in shared.breakline_rows if row.material_role == "slope_face_surface"]

    assert [row.breakline_role for row in slope_rows] == ["shoulder_to_side_slope"]
    assert len(slope_rows[0].point_refs) == 3
    assert all("side_slope_internal_breakline" != row.breakline_role for row in slope_rows)
    assert all("side_slope_to_daylight" != row.breakline_role for row in slope_rows)


def test_corridor_general_shared_breakline_metadata_drives_design_and_slope_audit() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:ordinary",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                region_id="region:ordinary",
                station=0.0,
                subassembly_point_rows=[
                    AppliedSectionSubassemblyPoint("lane:center", "lane", "centerline", 0.0, 0.0, 10.0),
                    AppliedSectionSubassemblyPoint("lane:edge", "lane", "lane_edge", 0.0, 3.5, 9.9),
                ],
                subassembly_link_rows=[
                    AppliedSectionSubassemblyLink("lane:fg", "lane", "lane:center", "lane:edge", "lane_fg", surface_role="design_surface")
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:10",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                region_id="region:ordinary",
                station=10.0,
                subassembly_point_rows=[
                    AppliedSectionSubassemblyPoint("lane:center", "lane", "centerline", 10.0, 0.0, 10.0),
                    AppliedSectionSubassemblyPoint("lane:edge", "lane", "lane_edge", 10.0, 3.5, 9.9),
                ],
                subassembly_link_rows=[
                    AppliedSectionSubassemblyLink("lane:fg", "lane", "lane:center", "lane:edge", "lane_fg", surface_role="design_surface")
                ],
            ),
        ],
    )
    shared = build_corridor_command.corridor_general_shared_breakline_result(applied)
    surface = tin_surface_with_shared_breakline_metadata(
        TINSurface(
            schema_version=1,
            project_id="proj-1",
            surface_id="surface:design",
            vertex_rows=[
                TINVertex("center0", 0.0, 0.0, 10.0),
                TINVertex("center1", 10.0, 0.0, 10.0),
                TINVertex("edge0", 0.0, 3.5, 9.9),
                TINVertex("edge1", 10.0, 3.5, 9.9),
                TINVertex("mid", 5.0, 1.75, 9.95),
            ],
            triangle_rows=[
                TINTriangle("t1", "center0", "center1", "mid"),
                TINTriangle("t2", "edge0", "mid", "edge1"),
            ],
        ),
        shared,
        consumer_ref="design_surface",
    )

    audit = build_corridor_command.shared_breakline_audit(shared, {"design_surface": surface})

    assert audit["status"] == "ready"
    assert audit["geometry_match_count"] == 2
    assert audit["geometry_mismatch_count"] == 0
    assert audit["mesh_match_count"] == 2
    assert audit["mesh_mismatch_count"] == 0
    assert build_corridor_command._tin_quality_text(surface, "shared_breakline_consumed_count") == "2"
    assert "shared-breakline:corridor:corridor:main" in build_corridor_command._tin_quality_text(
        surface,
        "shared_breakline_constraint_segment_rows",
    )


def test_corridor_general_shared_breakline_audit_reports_zero_mismatch_for_straight_and_curved_roads() -> None:
    def section(section_id: str, station: float, x: float, y_shift: float = 0.0) -> AppliedSection:
        return AppliedSection(
            schema_version=1,
            project_id="proj-1",
            applied_section_id=section_id,
            corridor_id="corridor:main",
            alignment_id="alignment:main",
            region_id="region:ordinary",
            station=station,
            frame=AppliedSectionFrame(station=station, x=x, y=y_shift, z=10.0),
            point_rows=[
                AppliedSectionPoint("slope:left:hinge", x, y_shift + 4.5, 9.90, "side_slope_surface", 4.5, side="left"),
                AppliedSectionPoint("slope:left:daylight", x, y_shift + 8.0, 8.75, "daylight_marker", 8.0, side="left"),
            ],
            subassembly_rows=[
                AppliedSectionSubassemblyRow("lane:left", "lane", side="left"),
                AppliedSectionSubassemblyRow("slope:left", "side_slope", side="left"),
            ],
            subassembly_point_rows=[
                AppliedSectionSubassemblyPoint("lane:left:center", "lane:left", "centerline", x, y_shift + 0.0, 10.0, lateral_offset=0.0, side="left"),
                AppliedSectionSubassemblyPoint("lane:left:edge", "lane:left", "lane_edge", x, y_shift + 3.5, 9.93, lateral_offset=3.5, side="left"),
                AppliedSectionSubassemblyPoint("slope:left:hinge", "slope:left", "hinge", x, y_shift + 4.5, 9.90, lateral_offset=4.5, side="left"),
                AppliedSectionSubassemblyPoint("slope:left:daylight", "slope:left", "daylight", x, y_shift + 8.0, 8.75, lateral_offset=8.0, side="left"),
            ],
            subassembly_link_rows=[
                AppliedSectionSubassemblyLink(
                    "lane:left:fg",
                    "lane:left",
                    "lane:left:center",
                    "lane:left:edge",
                    "lane_fg",
                    surface_role="design_surface",
                ),
                AppliedSectionSubassemblyLink(
                    "slope:left:face",
                    "slope:left",
                    "slope:left:hinge",
                    "slope:left:daylight",
                    "slope_face",
                    surface_role="slope_face_surface",
                ),
            ],
        )

    def audit_case(case_id: str, y_values: list[float]) -> tuple[dict[str, object], object, object]:
        sections = [
            section(f"section:{index}", station=float(index * 10), x=float(index * 10), y_shift=float(y_shift))
            for index, y_shift in enumerate(y_values)
        ]
        applied = AppliedSectionSet(
            schema_version=1,
            project_id="proj-1",
            applied_section_set_id=f"sections:{case_id}",
            corridor_id="corridor:main",
            alignment_id="alignment:main",
            sections=sections,
        )
        shared = build_corridor_command.corridor_general_shared_breakline_result(applied)
        design_surface = tin_surface_with_shared_breakline_metadata(
            tin_surface_with_shared_breakline_constraint_edges(
                TINSurface(schema_version=1, project_id="proj-1", surface_id=f"surface:{case_id}:design"),
                shared,
                consumer_ref="design_surface",
            ),
            shared,
            consumer_ref="design_surface",
        )
        slope_surface = tin_surface_with_shared_breakline_metadata(
            tin_surface_with_shared_breakline_constraint_edges(
                TINSurface(schema_version=1, project_id="proj-1", surface_id=f"surface:{case_id}:slope"),
                shared,
                consumer_ref="slope_face_surface",
            ),
            shared,
            consumer_ref="slope_face_surface",
        )
        audit = build_corridor_command.shared_breakline_audit(
            shared,
            {
                "design_surface": design_surface,
                "slope_face_surface": slope_surface,
            },
        )
        return audit, design_surface, slope_surface

    for case_id, y_values in {
        "straight": [0.0, 0.0, 0.0],
        "curved": [0.0, 2.0, 5.0],
    }.items():
        audit, design_surface, slope_surface = audit_case(case_id, y_values)
        assert audit["status"] == "ready"
        assert audit["missing_consumer_count"] == 0
        assert audit["geometry_mismatch_count"] == 0
        assert audit["mesh_mismatch_count"] == 0
        assert audit["geometry_match_count"] == 4
        assert audit["mesh_match_count"] == 4
        assert build_corridor_command._tin_quality_text(design_surface, "shared_breakline_consumed_count") == "2"
        assert build_corridor_command._tin_quality_text(slope_surface, "shared_breakline_consumed_count") == "2"
        assert build_corridor_command._tin_quality_text(design_surface, "shared_breakline_constraint_edge_count") == "4"
        assert build_corridor_command._tin_quality_text(slope_surface, "shared_breakline_constraint_edge_count") == "4"


def test_corridor_region_transition_shared_breakline_audit_consumes_design_and_slope_constraints() -> None:
    def section(section_id: str, region_id: str, station: float, x: float) -> AppliedSection:
        return AppliedSection(
            schema_version=1,
            project_id="proj-1",
            applied_section_id=section_id,
            corridor_id="corridor:main",
            alignment_id="alignment:main",
            region_id=region_id,
            station=station,
            subassembly_point_rows=[
                AppliedSectionSubassemblyPoint("lane:center", "lane", "centerline", x, 0.0, 10.0, lateral_offset=0.0),
                AppliedSectionSubassemblyPoint("lane:edge", "lane", "lane_edge", x, 3.5, 9.9, lateral_offset=3.5),
                AppliedSectionSubassemblyPoint("slope:hinge", "slope", "hinge", x, 5.0, 9.8, lateral_offset=5.0),
                AppliedSectionSubassemblyPoint("slope:daylight", "slope", "daylight", x, 8.0, 9.0, lateral_offset=8.0),
            ],
            subassembly_link_rows=[
                AppliedSectionSubassemblyLink("lane:fg", "lane", "lane:center", "lane:edge", "lane_fg", surface_role="design_surface"),
                AppliedSectionSubassemblyLink("slope:fg", "slope", "slope:hinge", "slope:daylight", "slope_fg", surface_role="slope_face_surface"),
            ],
        )

    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:region-audit",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        sections=[
            section("section:a:0", "region:a", 0.0, 0.0),
            section("section:a:10", "region:a", 10.0, 10.0),
            section("section:b:20", "region:b", 20.0, 20.0),
            section("section:b:30", "region:b", 30.0, 30.0),
        ],
    )
    shared = build_corridor_command.corridor_region_transition_shared_breakline_result(applied)
    design_surface = tin_surface_with_shared_breakline_metadata(
        tin_surface_with_shared_breakline_constraint_edges(
            TINSurface(schema_version=1, project_id="proj-1", surface_id="surface:region:design"),
            shared,
            consumer_ref="design_surface",
        ),
        shared,
        consumer_ref="design_surface",
    )
    slope_surface = tin_surface_with_shared_breakline_metadata(
        tin_surface_with_shared_breakline_constraint_edges(
            TINSurface(schema_version=1, project_id="proj-1", surface_id="surface:region:slope"),
            shared,
            consumer_ref="slope_face_surface",
        ),
        shared,
        consumer_ref="slope_face_surface",
    )

    audit = build_corridor_command.shared_breakline_audit(
        shared,
        {
            "design_surface": design_surface,
            "slope_face_surface": slope_surface,
        },
    )

    assert shared.breakline_count == 8
    assert build_corridor_command._tin_quality_text(design_surface, "shared_breakline_consumed_count") == "4"
    assert build_corridor_command._tin_quality_text(slope_surface, "shared_breakline_consumed_count") == "4"
    assert audit["status"] == "ready"
    assert audit["geometry_match_count"] == 8
    assert audit["geometry_mismatch_count"] == 0
    assert audit["mesh_match_count"] == 8
    assert audit["mesh_mismatch_count"] == 0
    assert audit["missing_consumer_count"] == 0


def test_shared_breakline_audit_metadata_is_visible_in_review_note() -> None:
    doc, _project = _new_project_doc()
    try:
        obj = doc.addObject("Part::Feature", "SharedBreaklineAuditPreview")
        shared = SimpleNamespace(
            breakline_result_id="shared-breakline:test",
            status="ready",
            breakline_count=2,
            ready_count=2,
            warning_count=0,
            error_count=0,
            diagnostic_rows=[],
            breakline_rows=[
                SimpleNamespace(breakline_id="shared-breakline:test:a", breakline_role="patch_to_design", source_status="ready"),
                SimpleNamespace(breakline_id="shared-breakline:test:b", breakline_role="patch_to_slope_face", source_status="ready"),
            ],
            point_rows=[
                SimpleNamespace(breakline_ref="shared-breakline:test:a", sequence=0, x=0.0, y=0.0, z=10.0),
                SimpleNamespace(breakline_ref="shared-breakline:test:a", sequence=1, x=10.0, y=0.0, z=10.0),
                SimpleNamespace(breakline_ref="shared-breakline:test:b", sequence=0, x=0.0, y=5.0, z=10.0),
                SimpleNamespace(breakline_ref="shared-breakline:test:b", sequence=1, x=10.0, y=5.0, z=10.0),
            ],
        )
        audit = {
            "status": "warning",
            "missing_consumer_count": 1,
            "mismatch_count": 0,
            "geometry_match_count": 1,
            "geometry_mismatch_count": 1,
            "mesh_match_count": 1,
            "mesh_mismatch_count": 1,
            "reversed_edge_count": 0,
            "solid_readiness_status": "warning",
            "solid_open_end_count": 2,
            "solid_duplicate_edge_count": 1,
            "solid_reversed_edge_count": 1,
            "solid_non_manifold_node_count": 0,
            "solid_readiness_notes": "open_end_count=2; duplicate_edge=edge:a",
            "notes": "geometry_mismatch:slope_face_surface:shared-breakline:test:b",
        }

        build_corridor_command._attach_shared_breakline_preview_metadata(obj, shared, audit=audit)
        note = build_review_presentation._shared_breakline_review_note(obj)

        assert obj.SharedBreaklineAuditStatus == "warning"
        assert int(obj.SharedBreaklineGeometryMatchCount) == 1
        assert int(obj.SharedBreaklineGeometryMismatchCount) == 1
        assert int(obj.SharedBreaklineMeshMatchCount) == 1
        assert int(obj.SharedBreaklineMeshMismatchCount) == 1
        assert int(obj.SharedBreaklineMissingConsumerCount) == 1
        assert obj.SharedBreaklineSolidReadinessStatus == "warning"
        assert int(obj.SharedBreaklineSolidOpenEndCount) == 2
        assert int(obj.SharedBreaklineSolidDuplicateEdgeCount) == 1
        assert int(obj.SharedBreaklineSolidReversedEdgeCount) == 1
        assert obj.SharedBreaklineSolidReadinessNotes == "open_end_count=2; duplicate_edge=edge:a"
        assert obj.SharedBreaklineAuditSummary == "audit=warning geometry=1/2 mesh=1/2 missing=1 mismatch=0 reversed=0"
        assert list(obj.SharedBreaklineAuditNotes) == ["geometry_mismatch:slope_face_surface:shared-breakline:test:b"]
        assert len(list(obj.SharedBreaklineSegmentRows)) == 2
        assert len(list(obj.SharedBreaklineSolidBoundaryTraceRows)) == 2
        assert "shared-breakline:test:a|patch_to_design|ready|0|0|0|10|10|0|10|patch_to_design" in list(obj.SharedBreaklineSegmentRows)
        assert list(obj.SharedBreaklineSolidBoundaryTraceRows)[0].startswith("shared-breakline:test:a|patch_to_design")
        assert "shared_breakline=ready consumed=2/2 warnings=0 errors=0" in note
        assert "audit=warning geometry=1/2 mesh=1/2 missing=1 mismatch=0 reversed=0" in note
        assert "solid_readiness=warning open=2 duplicate=1 reversed=1 non_manifold=0" in note
    finally:
        App.closeDocument(doc.Name)


def test_shared_breakline_adjacency_graph_reports_solid_loop_readiness() -> None:
    shared = build_corridor_command.SharedBreaklineResult(
        schema_version=1,
        project_id="proj-1",
        breakline_result_id="shared-breakline:closed",
        domain_kind="corridor",
        domain_ref="corridor:main",
        status="ready",
        breakline_count=4,
        breakline_rows=[
            build_corridor_command.SharedBreaklineRow("edge:a", "corridor", "corridor:main", "solid_boundary", point_refs=("p1", "p2")),
            build_corridor_command.SharedBreaklineRow("edge:b", "corridor", "corridor:main", "solid_boundary", point_refs=("p2", "p3")),
            build_corridor_command.SharedBreaklineRow("edge:c", "corridor", "corridor:main", "solid_boundary", point_refs=("p3", "p4")),
            build_corridor_command.SharedBreaklineRow("edge:d", "corridor", "corridor:main", "solid_boundary", point_refs=("p4", "p1")),
        ],
        point_rows=[
            build_corridor_command.SharedBreaklinePointRow("p1", "edge:a", 0, 0.0, 0.0, 0.0),
            build_corridor_command.SharedBreaklinePointRow("p2", "edge:a", 1, 10.0, 0.0, 0.0),
            build_corridor_command.SharedBreaklinePointRow("p3", "edge:b", 1, 10.0, 10.0, 0.0),
            build_corridor_command.SharedBreaklinePointRow("p4", "edge:c", 1, 0.0, 10.0, 0.0),
        ],
    )

    graph = build_corridor_command.shared_breakline_adjacency_graph(shared)

    assert graph["status"] == "ready"
    assert graph["node_count"] == 4
    assert graph["edge_count"] == 4
    assert graph["open_end_count"] == 0
    assert graph["duplicate_edge_count"] == 0
    assert graph["reversed_edge_count"] == 0
    assert graph["non_manifold_node_count"] == 0
    assert graph["notes"] == "shared_breakline_adjacency=closed"


def test_shared_breakline_adjacency_graph_reports_open_duplicate_reversed_and_non_manifold_edges() -> None:
    shared = build_corridor_command.SharedBreaklineResult(
        schema_version=1,
        project_id="proj-1",
        breakline_result_id="shared-breakline:issues",
        domain_kind="corridor",
        domain_ref="corridor:main",
        status="warning",
        breakline_count=4,
        breakline_rows=[
            build_corridor_command.SharedBreaklineRow("edge:a", "corridor", "corridor:main", "solid_boundary", point_refs=("p1", "p2")),
            build_corridor_command.SharedBreaklineRow("edge:a-reversed", "corridor", "corridor:main", "solid_boundary", point_refs=("p2", "p1")),
            build_corridor_command.SharedBreaklineRow("edge:branch-1", "corridor", "corridor:main", "solid_boundary", point_refs=("p1", "p3")),
            build_corridor_command.SharedBreaklineRow("edge:branch-2", "corridor", "corridor:main", "solid_boundary", point_refs=("p1", "p4")),
        ],
        point_rows=[
            build_corridor_command.SharedBreaklinePointRow("p1", "edge:a", 0, 0.0, 0.0, 0.0),
            build_corridor_command.SharedBreaklinePointRow("p2", "edge:a", 1, 10.0, 0.0, 0.0),
            build_corridor_command.SharedBreaklinePointRow("p3", "edge:branch-1", 1, 0.0, 10.0, 0.0),
            build_corridor_command.SharedBreaklinePointRow("p4", "edge:branch-2", 1, -10.0, 0.0, 0.0),
        ],
    )

    graph = build_corridor_command.shared_breakline_adjacency_graph(shared)

    assert graph["status"] == "warning"
    assert graph["edge_count"] == 4
    assert graph["open_end_count"] == 2
    assert graph["duplicate_edge_count"] == 1
    assert graph["reversed_edge_count"] == 1
    assert graph["non_manifold_node_count"] == 1
    assert "duplicate_edge:edge:a-reversed:edge:a" in graph["notes"]
    assert "reversed_edge:edge:a-reversed:edge:a" in graph["notes"]
    assert "open_end_count=2" in graph["notes"]
    assert "non_manifold_node_count=1" in graph["notes"]


def test_shared_breakline_solid_boundary_trace_rows_preserve_source_lineage() -> None:
    shared = build_corridor_command.SharedBreaklineResult(
        schema_version=1,
        project_id="proj-1",
        breakline_result_id="shared-breakline:trace",
        domain_kind="intersection",
        domain_ref="intersection:t-01",
        status="ready",
        breakline_count=1,
        breakline_rows=[
            build_corridor_command.SharedBreaklineRow(
                "shared-breakline:trace:control-entry",
                "intersection_control_area",
                "control-area:t-01:main",
                "control_area_entry",
                source_contract_refs=("section:entry", "control-area:t-01:main", "region:main-intersection"),
                consumer_refs=("intersection_surface", "design_surface"),
                point_refs=("p1", "p2"),
                station_start=10.0,
                station_end=10.0,
                alignment_ref="alignment:main",
                material_role="design_surface",
                source_status="ready",
                handoff_target="intersection_control_area",
            )
        ],
        point_rows=[
            build_corridor_command.SharedBreaklinePointRow("p1", "shared-breakline:trace:control-entry", 0, 10.0, 0.0, 10.0),
            build_corridor_command.SharedBreaklinePointRow("p2", "shared-breakline:trace:control-entry", 1, 10.0, 5.0, 10.0),
        ],
    )

    rows = build_corridor_command.shared_breakline_solid_boundary_trace_rows(shared)

    assert rows == [
        "shared-breakline:trace:control-entry|control_area_entry|intersection_control_area|control-area:t-01:main|alignment:main|10.000000|10.000000|design_surface|ready|section:entry,control-area:t-01:main,region:main-intersection|intersection_surface,design_surface|intersection_control_area"
    ]
    assert build_corridor_command.shared_breakline_solid_boundary_trace_rows(shared, ["missing"]) == []
    assert build_corridor_command.shared_breakline_solid_boundary_trace_rows(shared, ["shared-breakline:trace:control-entry"]) == rows


def test_shared_breakline_highlight_uses_preview_segment_rows() -> None:
    doc, _project = _new_project_doc()
    try:
        source = doc.addObject("Part::Feature", "V1CorridorDaylightSurfacePreview")
        source.Label = "Corridor Slope Face Surface"
        source.Shape = Part.makeBox(12.0, 12.0, 2.0, App.Vector(-1.0, -1.0, 9.0))
        build_corridor_command._set_preview_property(source, "SharedBreaklineResultId", "shared-breakline:test")
        build_corridor_command._set_preview_property(source, "SharedBreaklineAuditStatus", "warning")
        build_corridor_command._set_preview_string_list_property(
            source,
            "SharedBreaklineSegmentRows",
            [
                "shared-breakline:test:a|patch_to_slope_face|ready|0|0|0|10|10|0|10|side_slope|intersection_surface",
                "shared-breakline:test:b|curb_return_to_shoulder|ready|0|0|5|10|10|5|10|shoulder|design_surface",
                "shared-breakline:test:c|lane_to_shoulder|ready|0|20|0|10|30|0|10|shoulder|design_surface",
                "shared-breakline:test:d|side_slope_to_daylight|ready|0|20|5|10|30|5|10|side_slope|slope_face_surface",
                "shared-breakline:test:e|corridor_gutter_handoff|ready|0|20|10|10|30|10|10|drainage_surface|drainage_surface",
                "shared-breakline:test:f|curb_return_to_slope_face|ready|0|100|100|10|110|100|10|curb_return|intersection_surface",
                "shared-breakline:test:g|legacy_untagged|ready|0|1|1|10|2|1|10|curb_return",
            ],
        )

        highlight = build_corridor_command.show_shared_breakline_highlight(doc, source)
        shoulder = build_corridor_command.show_shared_breakline_highlight(doc, source, material_filter="shoulder")

        assert highlight.Name == "ReviewSharedBreaklineHighlight"
        assert highlight.CRRecordKind == "v1_shared_breakline_highlight"
        assert highlight.V1ObjectType == "ReviewDiagnostic"
        assert int(shoulder.SharedBreaklineSegmentCount) == 2
        assert shoulder.SharedBreaklineMaterialFilter == "shoulder"
        assert shoulder.SharedBreaklineHighlightColor == "0.650,1.000,0.350"
        assert list(shoulder.SharedBreaklineRefs) == ["shared-breakline:test:b", "shared-breakline:test:c"]
        slope_role = build_corridor_command.show_shared_breakline_highlight(doc, source, role_filter="patch_to_slope_face")
        assert int(slope_role.SharedBreaklineSegmentCount) == 1
        assert slope_role.SharedBreaklineRoleFilter == "patch_to_slope_face"
        assert slope_role.SharedBreaklineHighlightColor == "0.050,0.950,0.250"
        assert list(slope_role.SharedBreaklineRefs) == ["shared-breakline:test:a"]
        lane_shoulder = build_corridor_command.show_shared_breakline_highlight(doc, source, role_filter="lane_to_shoulder")
        assert int(lane_shoulder.SharedBreaklineSegmentCount) == 1
        assert lane_shoulder.SharedBreaklineRoleFilter == "lane_to_shoulder"
        assert lane_shoulder.SharedBreaklineHighlightColor == "0.650,1.000,0.350"
        assert list(lane_shoulder.SharedBreaklineRefs) == ["shared-breakline:test:c"]
        daylight = build_corridor_command.show_shared_breakline_highlight(doc, source, role_filter="side_slope_to_daylight")
        assert int(daylight.SharedBreaklineSegmentCount) == 1
        assert daylight.SharedBreaklineHighlightColor == "0.050,0.950,0.250"
        gutter = build_corridor_command.show_shared_breakline_highlight(doc, source, role_filter="corridor_gutter_handoff")
        assert int(gutter.SharedBreaklineSegmentCount) == 1
        assert gutter.SharedBreaklineHighlightColor == "0.100,0.550,1.000"
        clipped = build_corridor_command.show_shared_breakline_highlight(
            doc,
            source,
            consumer_filter="intersection_surface",
            clip_to_source_bounds=True,
        )
        assert clipped.SharedBreaklineConsumerFilter == "intersection_surface"
        assert clipped.SharedBreaklineClipToSourceBounds == "Yes"
        assert int(clipped.SharedBreaklineSegmentCount) == 1
        assert list(clipped.SharedBreaklineRefs) == ["shared-breakline:test:a"]
        assert build_corridor_command._shared_breakline_summary_keys("pavement=4, shoulder=4") == ["pavement", "shoulder"]
        assert build_corridor_command._shared_breakline_highlight_color(material_filter="pavement") == (1.00, 0.88, 0.05)
        assert build_corridor_command._shared_breakline_highlight_color(role_filter="lane_to_lane") == (1.00, 0.88, 0.05)
        assert build_corridor_command._shared_breakline_highlight_color(role_filter="lane_to_shoulder") == (0.65, 1.00, 0.35)
        assert build_corridor_command._shared_breakline_highlight_color(role_filter="side_slope_to_daylight") == (0.05, 0.95, 0.25)
        assert build_corridor_command._shared_breakline_highlight_color(role_filter="curb_return_to_shoulder") == (1.00, 0.52, 0.05)
        assert build_corridor_command._shared_breakline_highlight_color(role_filter="corridor_gutter_handoff") == (0.10, 0.55, 1.00)
        assert build_corridor_command._shared_breakline_highlight_color(material_filter="drainage_surface") == (0.10, 0.55, 1.00)
    finally:
        App.closeDocument(doc.Name)


def test_shared_breakline_audit_panel_rows_and_summary_are_user_readable() -> None:
    doc, _project = _new_project_doc()
    try:
        intersection = doc.addObject("Part::Feature", "V1CorridorIntersectionSurfacePreview")
        intersection.Label = "Intersection Surface"
        build_corridor_command._set_preview_property(intersection, "SharedBreaklineResultId", "shared-breakline:test")
        build_corridor_command._set_preview_property(intersection, "SharedBreaklineStatus", "ready")
        build_corridor_command._set_preview_integer_property(intersection, "SharedBreaklineCount", 2)
        build_corridor_command._set_preview_integer_property(intersection, "SharedBreaklineConsumedCount", 2)
        build_corridor_command._set_preview_property(intersection, "SharedBreaklineAuditStatus", "ready")
        build_corridor_command._set_preview_integer_property(intersection, "SharedBreaklineGeometryMatchCount", 2)
        build_corridor_command._set_preview_integer_property(intersection, "SharedBreaklineGeometryMismatchCount", 0)
        build_corridor_command._set_preview_integer_property(intersection, "SharedBreaklineMeshMatchCount", 2)
        build_corridor_command._set_preview_integer_property(intersection, "SharedBreaklineMeshMismatchCount", 0)
        build_corridor_command._set_preview_property(intersection, "SharedBreaklineMaterialSummary", "curb_return=2, shoulder=1")
        build_corridor_command._set_preview_property(intersection, "SharedBreaklineRoleSummary", "curb_return_outer=2, patch_to_shoulder=1")
        build_corridor_command._set_preview_property(intersection, "SharedBreaklineSolidReadinessStatus", "ready")
        build_corridor_command._set_preview_property(intersection, "SharedBreaklineAuditSummary", "audit=ready geometry=2/2 mesh=2/2 missing=0 mismatch=0 reversed=0")
        slope = doc.addObject("Part::Feature", "V1CorridorDaylightSurfacePreview")
        slope.Label = "Corridor Slope Face Surface"
        build_corridor_command._set_preview_property(slope, "SharedBreaklineResultId", "shared-breakline:test")
        build_corridor_command._set_preview_property(slope, "SharedBreaklineStatus", "ready")
        build_corridor_command._set_preview_integer_property(slope, "SharedBreaklineCount", 2)
        build_corridor_command._set_preview_integer_property(slope, "SharedBreaklineConsumedCount", 1)
        build_corridor_command._set_preview_property(slope, "SharedBreaklineAuditStatus", "warning")
        build_corridor_command._set_preview_integer_property(slope, "SharedBreaklineGeometryMatchCount", 0)
        build_corridor_command._set_preview_integer_property(slope, "SharedBreaklineGeometryMismatchCount", 1)
        build_corridor_command._set_preview_integer_property(slope, "SharedBreaklineMeshMatchCount", 0)
        build_corridor_command._set_preview_integer_property(slope, "SharedBreaklineMeshMismatchCount", 1)
        build_corridor_command._set_preview_property(slope, "SharedBreaklineMaterialSummary", "side_slope=1")
        build_corridor_command._set_preview_property(slope, "SharedBreaklineRoleSummary", "patch_to_slope_face=1")
        build_corridor_command._set_preview_property(slope, "SharedBreaklineSolidReadinessStatus", "warning")
        build_corridor_command._set_preview_integer_property(slope, "SharedBreaklineSolidOpenEndCount", 2)
        build_corridor_command._set_preview_integer_property(slope, "SharedBreaklineSolidDuplicateEdgeCount", 1)
        build_corridor_command._set_preview_integer_property(slope, "SharedBreaklineSolidNonManifoldNodeCount", 1)
        build_corridor_command._set_preview_string_list_property(slope, "SharedBreaklineAuditNotes", ["geometry_mismatch:slope_face_surface:shared-breakline:test"])
        intersection_slope = doc.addObject("Part::Feature", "V1CorridorIntersectionSlopeFaceSurfacePreview")
        intersection_slope.Label = "Intersection Slope Face Surface"
        build_corridor_command._set_preview_property(intersection_slope, "SharedBreaklineResultId", "shared-breakline:test")
        build_corridor_command._set_preview_property(intersection_slope, "SharedBreaklineStatus", "ready")
        build_corridor_command._set_preview_integer_property(intersection_slope, "SharedBreaklineCount", 3)
        build_corridor_command._set_preview_integer_property(intersection_slope, "SharedBreaklineConsumedCount", 3)
        build_corridor_command._set_preview_property(intersection_slope, "SharedBreaklineAuditStatus", "ready")
        build_corridor_command._set_preview_integer_property(intersection_slope, "SharedBreaklineGeometryMatchCount", 3)
        build_corridor_command._set_preview_integer_property(intersection_slope, "SharedBreaklineMeshMatchCount", 3)
        build_corridor_command._set_preview_property(intersection_slope, "SharedBreaklineRoleSummary", "patch_to_intersection_slope_face=1, main_side_slope_face_tie=2")
        build_corridor_command._set_preview_integer_property(intersection_slope, "IntersectionSlopeFaceCellCount", 3)
        build_corridor_command._set_preview_integer_property(intersection_slope, "IntersectionSlopeFaceCellReadyCount", 2)
        build_corridor_command._set_preview_integer_property(intersection_slope, "IntersectionSlopeFaceCellOpenCount", 1)
        build_corridor_command._set_preview_integer_property(intersection_slope, "IntersectionSlopeFaceCellMissingEdgeCount", 1)
        build_corridor_command._set_preview_integer_property(intersection_slope, "IntersectionSlopeFaceCellTriangleCount", 8)
        build_corridor_command._set_preview_string_list_property(
            intersection_slope,
            "IntersectionSlopeFaceCellAuditRows",
            [
                "cell:upper|upper_left_transition_cell|ready|0|0|5|patch-to-intersection-slope-face:1,intersection-slope-face-to-design-surface:1|",
                "cell:tie|main_to_side_left_tie_cell|warning|1|1|3|main-side-slope-face-tie:1|intersection_slope_face_cell_edge_missing:curb_return",
            ],
        )

        rows = build_corridor_command.corridor_shared_breakline_audit_rows(doc)
        display_rows = build_corridor_command.shared_breakline_audit_display_rows(rows)
        internal_display_rows = build_corridor_command.shared_breakline_audit_display_rows(rows, include_internal=True)
        summary = build_corridor_command.corridor_shared_breakline_audit_summary(doc)

        assert [row["surface"] for row in rows] == ["Intersection Surface", "Slope Face Surface", "Intersection Slope Face Surface"]
        assert [row["row_kind"] for row in display_rows] == ["surface", "surface", "surface"]
        assert [row["row_kind"] for row in internal_display_rows[:2]] == ["surface", "role"]
        assert internal_display_rows[1]["surface"] == "  Role: curb_return_outer"
        assert internal_display_rows[1]["breakline_role_filter"] == "curb_return_outer"
        assert internal_display_rows[1]["role_summary"] == "curb_return_outer=2"
        assert any(row.get("breakline_role_filter") == "patch_to_shoulder" for row in internal_display_rows)
        assert any(row.get("breakline_role_filter") == "patch_to_slope_face" for row in internal_display_rows)
        assert rows[0]["status"] == "ready"
        assert rows[0]["recommended_action"] == "No action needed"
        assert rows[0]["material_summary"] == "curb_return=2, shoulder=1"
        assert rows[0]["role_summary"] == "curb_return_outer=2, patch_to_shoulder=1"
        assert rows[0]["solid_readiness_status"] == "ready"
        assert rows[1]["status"] == "warning"
        assert rows[1]["geometry_mismatch_count"] == 1
        assert rows[1]["mesh_mismatch_count"] == 1
        assert rows[1]["material_summary"] == "side_slope=1"
        assert rows[1]["role_summary"] == "patch_to_slope_face=1"
        assert rows[1]["solid_readiness_status"] == "warning"
        assert rows[1]["solid_open_end_count"] == 2
        assert rows[1]["solid_duplicate_edge_count"] == 1
        assert rows[1]["solid_non_manifold_node_count"] == 1
        assert rows[1]["recommended_action"] == "Rebuild constrained surface mesh"
        assert "geometry_mismatch:slope_face_surface" in rows[1]["notes"]
        assert rows[2]["status"] == "warning"
        assert rows[2]["cell_count"] == 3
        assert rows[2]["cell_open_count"] == 1
        assert rows[2]["cell_missing_edge_count"] == 1
        assert rows[2]["recommended_action"] == "Review Intersection Slope Face cells, then rebuild"
        assert "cell_audit=count=3" in rows[2]["notes"]
        assert any(row.get("row_kind") == "cell" and row.get("surface") == "  Cell Audit: Intersection Slope Face" for row in internal_display_rows)
        cell_detail_rows = [row for row in internal_display_rows if row.get("row_kind") == "cell_detail"]
        assert len(cell_detail_rows) == 2
        assert cell_detail_rows[1]["status"] == "warning"
        assert cell_detail_rows[1]["surface"] == "    Cell: main_to_side_left_tie_cell"
        assert "main-side-slope-face-tie:1" in cell_detail_rows[1]["role_summary"]
        assert "intersection_slope_face_cell_edge_missing:curb_return" in cell_detail_rows[1]["notes"]
        assert summary["status"] == "warning"
        assert summary["title"] == "Shared breakline issues found: 2 surface(s)"
        assert "geometry_mismatch=1" in summary["notes"]
        assert "mesh_mismatch=1" in summary["notes"]
        assert "reversed=0" in summary["notes"]
        assert "cell_open=1" in summary["notes"]
        assert "cell_missing_edge=1" in summary["notes"]
        assert "status_warning=2" in summary["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_shared_breakline_audit_summary_explains_status_only_warning() -> None:
    doc, _project = _new_project_doc()
    try:
        for object_name, label in (
            ("V1CorridorDesignSurfacePreview", "Design Surface"),
            ("V1CorridorDaylightSurfacePreview", "Slope Face Surface"),
        ):
            preview = doc.addObject("Part::Feature", object_name)
            preview.Label = label
            build_corridor_command._set_preview_property(preview, "SharedBreaklineResultId", "shared-breakline:test")
            build_corridor_command._set_preview_property(preview, "SharedBreaklineStatus", "ready")
            build_corridor_command._set_preview_integer_property(preview, "SharedBreaklineCount", 1)
            build_corridor_command._set_preview_integer_property(preview, "SharedBreaklineConsumedCount", 1)
            build_corridor_command._set_preview_property(preview, "SharedBreaklineAuditStatus", "warning")
            build_corridor_command._set_preview_integer_property(preview, "SharedBreaklineGeometryMatchCount", 1)
            build_corridor_command._set_preview_integer_property(preview, "SharedBreaklineGeometryMismatchCount", 0)
            build_corridor_command._set_preview_integer_property(preview, "SharedBreaklineMeshMatchCount", 1)
            build_corridor_command._set_preview_integer_property(preview, "SharedBreaklineMeshMismatchCount", 0)

        rows = build_corridor_command.corridor_shared_breakline_audit_rows(doc)
        summary = build_corridor_command.corridor_shared_breakline_audit_summary(doc)

        assert [row["status"] for row in rows] == ["ready", "ready"]
        assert summary["status"] == "ready"
        assert summary["title"] == "No shared breakline issues"
        assert "2 audited surface(s)" in summary["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_shared_breakline_recommended_action_uses_breakline_role_notes() -> None:
    assert shared_breakline_audit_presentation._shared_breakline_recommended_action(
        geometry_mismatch_count=1,
        mesh_mismatch_count=1,
        missing_consumer_count=0,
        mismatch_count=0,
        reversed_edge_count=0,
        notes="mesh_drift:slope_face_surface:shared-breakline:intersection:intersection:t:patch-to-slope-face:1",
    ) == "Rebuild Intersection and Slope Face constraints"
    assert shared_breakline_audit_presentation._shared_breakline_recommended_action(
        geometry_mismatch_count=1,
        mesh_mismatch_count=1,
        missing_consumer_count=0,
        mismatch_count=0,
        reversed_edge_count=0,
        notes="mesh_drift:slope_face_surface:shared-breakline:intersection:intersection:t:curb-return-to-slope-face:1:start",
    ) == "Rebuild Intersection and Slope Face constraints"
    assert shared_breakline_audit_presentation._shared_breakline_recommended_action(
        geometry_mismatch_count=1,
        mesh_mismatch_count=1,
        missing_consumer_count=0,
        mismatch_count=0,
        reversed_edge_count=0,
        notes="mesh_drift:design_surface:shared-breakline:intersection:intersection:t:curb-return-to-shoulder:1:start",
    ) == "Rebuild Intersection and Design constraints"
    assert shared_breakline_audit_presentation._shared_breakline_recommended_action(
        geometry_mismatch_count=1,
        mesh_mismatch_count=1,
        missing_consumer_count=0,
        mismatch_count=0,
        reversed_edge_count=0,
        notes="mesh_drift:design_surface:shared-breakline:intersection:intersection:t:patch-to-shoulder:1",
    ) == "Rebuild Intersection and Design constraints"
    assert shared_breakline_audit_presentation._shared_breakline_recommended_action(
        geometry_mismatch_count=1,
        mesh_mismatch_count=1,
        missing_consumer_count=0,
        mismatch_count=0,
        reversed_edge_count=0,
        notes="mesh_drift:slope_face_surface:shared-breakline:intersection:intersection:t:shoulder-to-slope-face:1",
    ) == "Rebuild Applied Sections, then constrained surfaces"
    assert shared_breakline_audit_presentation._shared_breakline_recommended_action(
        geometry_mismatch_count=1,
        mesh_mismatch_count=1,
        missing_consumer_count=0,
        mismatch_count=0,
        reversed_edge_count=0,
        notes="mesh_drift:drainage_surface:shared-breakline:corridor:corridor:main:corridor-gutter-handoff:1",
    ) == "Review Drainage source, then rebuild Applied Sections"
    assert shared_breakline_audit_presentation._shared_breakline_recommended_action(
        geometry_mismatch_count=1,
        mesh_mismatch_count=1,
        missing_consumer_count=0,
        mismatch_count=0,
        reversed_edge_count=0,
        notes="mesh_drift:drainage_surface:shared-breakline:intersection:intersection:t:intersection-gutter-handoff:1",
    ) == "Review Intersection Drainage source, then rebuild Intersection"
    assert shared_breakline_audit_presentation._shared_breakline_recommended_action(
        geometry_mismatch_count=1,
        mesh_mismatch_count=1,
        missing_consumer_count=0,
        mismatch_count=0,
        reversed_edge_count=0,
        notes="mesh_drift:design_surface:shared-breakline:region-transition:corridor:main:region_start_boundary:3:design_surface",
    ) == "Review Region spans, then Build Parametric"
    assert shared_breakline_audit_presentation._shared_breakline_recommended_action(
        geometry_mismatch_count=1,
        mesh_mismatch_count=1,
        missing_consumer_count=0,
        mismatch_count=0,
        reversed_edge_count=0,
        notes="mesh_drift:design_surface:shared-breakline:region-transition:corridor:main:assembly_change_boundary:5:design_surface",
    ) == "Review Region spans, then Build Parametric"
    assert shared_breakline_audit_presentation._shared_breakline_recommended_action(
        geometry_mismatch_count=1,
        mesh_mismatch_count=1,
        missing_consumer_count=0,
        mismatch_count=0,
        reversed_edge_count=0,
        notes="mesh_drift:design_surface:shared-breakline:intersection:intersection:t:control_area_entry:1:control-main:design_surface",
    ) == "Review Intersection control areas and Region spans, then Build Parametric"
    assert shared_breakline_audit_presentation._shared_breakline_recommended_action(
        geometry_mismatch_count=1,
        mesh_mismatch_count=1,
        missing_consumer_count=0,
        mismatch_count=0,
        reversed_edge_count=0,
        notes="mesh_drift:design_surface:shared-breakline:corridor:corridor:main:lane_to_shoulder:6",
    ) == "Rebuild Applied Sections, then constrained surfaces"


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
        # the panel fills each review tab on demand, the way opening it does
        panel._load_review_tab("regions")

        assert panel._region_table.rowCount() == 2
        # Alignment leads the row, then the region id, and Boundary is the tenth column
        assert panel._region_table.item(0, 0).text() == "main"
        assert panel._region_table.item(0, 1).text() == "region:rural"
        assert panel._region_table.item(1, 1).text() == "region:urban"
        assert panel._region_table.item(0, 9).text() == "warn"
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_panel_creates_surface_transition_from_selected_region() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_region_boundary())
        panel = V1BuildCorridorTaskPanel(document=doc)
        # the panel fills each review tab on demand, the way opening it does
        panel._load_review_tab("regions")

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
        # the panel fills each review tab on demand, the way opening it does
        panel._load_review_tab("regions")

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


def test_build_corridor_panel_delegates_supplemental_sampling_to_applied_sections() -> None:
    """Build Parametric does not own supplemental density and offers no toggle.

    Supplemental sampling ownership moved to the Applied Sections stage; see
    docsV1/V1_APPLIED_SECTION_SUPPLEMENTAL_SAMPLING_REDESIGN_PLAN.md. Build
    Parametric consumes the resulting section rows and must not ask the surface
    service to invent samples of its own. This replaces an earlier expectation
    that the panel carried a checked "Supplemental Sampling" checkbox.
    """

    _ensure_qapp()
    doc, _project = _new_project_doc()
    try:
        panel = V1BuildCorridorTaskPanel(document=doc)
        checks = panel.form.findChildren(QtWidgets.QCheckBox)
        assert not [check for check in checks if check.text() == "Supplemental Sampling"]

        label_texts = [label.text() for label in panel.form.findChildren(QtWidgets.QLabel)]
        assert any(
            "supplemental density is configured in Applied Sections" in text
            for text in label_texts
        )
        assert any(text.startswith("Applied Sections:") for text in label_texts)

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

        build_review_roles = [
            "centerline",
            "design",
            "intersection",
            "subgrade",
            "daylight",
            "intersection_slope",
            "intersection_tie_slope",
            "drainage",
        ]
        missing_rows = corridor_build_review_rows(doc)
        assert [row["role"] for row in missing_rows] == build_review_roles
        assert {row["status"] for row in missing_rows} == {"missing"}
        assert "2 STA" in str(missing_rows[0]["applied_section_summary"])
        assert missing_rows[0]["applied_section_diagnostics"] == "2 diagnostic(s)"

        apply_v1_corridor_model(document=doc, project=project)
        rows = corridor_build_review_rows(doc)

        rows_by_role = {str(row["role"]): row for row in rows}
        assert [row["role"] for row in rows] == build_review_roles
        # the applied sections carry an overlap clip and a daylight fallback, so the
        # surfaces that read them are warnings rather than ready
        assert [row["status"] for row in rows] == [
            "missing",
            "warning",
            "missing",
            "warning",
            "warning",
            "missing",
            "missing",
            "missing",
        ]
        assert rows_by_role["centerline"]["triangle_or_point_count"] == ""
        assert rows_by_role["design"]["vertex_count"] == 4
        assert rows_by_role["design"]["triangle_or_point_count"] == 2
        assert "2 STA" in str(rows_by_role["design"]["applied_section_summary"])
        assert rows_by_role["design"]["applied_section_diagnostics"] == "2 diagnostic(s)"
        assert "fallbacks: 4" in str(rows_by_role["daylight"]["notes"])
        assert "no EG TIN: 4" in str(rows_by_role["daylight"]["notes"])
        assert "STA 0.000 L no EG TIN" in str(rows_by_role["daylight"]["notes"])
        assert "STA 20.000 R no EG TIN" in str(rows_by_role["daylight"]["notes"])
        assert "no drainage_surface row exists" in str(rows_by_role["drainage"]["notes"])
        # no surface reaches ready here, so no row is preferred for review
        assert preferred_corridor_build_review_row_index(rows) is None

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

        # the daylight contact markers are review diagnostics
        marker = doc.getObject("ReviewDiagnosticSlopeFaceIntersectionMarkers")
        assert marker is None
        assert created == []
        assert set_corridor_build_daylight_contact_marker_visibility(doc, True) is None

        created = build_corridor_command._create_slope_face_diagnostic_markers(
            document=doc,
            project=project,
            surface=surface,
            show_daylight_contact_markers=True,
        )

        marker = doc.getObject("ReviewDiagnosticSlopeFaceIntersectionMarkers")
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
        drainage_row = next(row for row in rows if row["role"] == "drainage")
        assert drainage_row["status"] == "missing"
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
    transitional = tin_mesh_preview_style("intersection_transitional_patch")
    accepted = tin_mesh_preview_style("intersection_accepted_candidate")
    base = tin_mesh_preview_style("unknown")

    assert design["shape_color"] == (1.00, 0.56, 0.12)
    assert subgrade["transparency"] > design["transparency"]
    assert daylight["shape_color"] != design["shape_color"]
    assert drainage["line_width"] > daylight["line_width"]
    assert transitional["transparency"] > accepted["transparency"]
    assert transitional["shape_color"] != accepted["shape_color"]
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
                FakeObject("V1CorridorIntersectionSlopeFaceSurfacePreview"),
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
    # every object in the document is toggled exactly once
    assert changed == len(doc.Objects)
    assert doc.getObject("V1CorridorRegionSurface_region_rural").ViewObject.Visibility is False
    assert all(
        obj.ViewObject.Visibility is True
        for obj in doc.Objects
        if obj.Name != "V1CorridorRegionSurface_region_rural"
    )


def test_intersection_slope_visibility_note_explains_absent_preview() -> None:
    class FakeView:
        def __init__(self):
            self.Visibility = False

    class FakeObject:
        def __init__(self, name):
            self.Name = name
            self.Label = name
            self.ViewObject = FakeView()

    class FakeDocument:
        def __init__(self):
            intersection = FakeObject("V1CorridorIntersectionSurfacePreview")
            self.Objects = [intersection]

        def getObject(self, name):
            for obj in self.Objects:
                if obj.Name == name:
                    return obj
            return None

    doc = FakeDocument()

    assert build_corridor_command.set_corridor_build_preview_visibility(doc, "intersection_slope", True) is None
    note = build_corridor_command.corridor_build_preview_visibility_note(doc, "intersection_slope")
    assert "unavailable" in note
    assert "Preview object is absent" in note

    rows = build_corridor_command.corridor_build_review_rows(doc)
    slope_row = [row for row in rows if row["role"] == "intersection_slope"][0]
    assert slope_row["status"] == "missing"

    slope_preview = FakeObject("V1CorridorIntersectionSlopeFaceSurfacePreview")
    doc.Objects.append(slope_preview)
    toggled = build_corridor_command.set_corridor_build_preview_visibility(doc, "intersection_slope", True)
    assert toggled is slope_preview
    assert slope_preview.ViewObject.Visibility is True
    assert "Show or hide" in build_corridor_command.corridor_build_preview_visibility_note(doc, "intersection_slope")


def test_corridor_build_visibility_group_toggles_common_review_layers() -> None:
    class FakeView:
        def __init__(self):
            self.Visibility = False

    class FakeObject:
        def __init__(self, name):
            self.Name = name
            self.ViewObject = FakeView()

    class FakeDocument:
        def __init__(self):
            self.Objects = [
                FakeObject("V1CorridorDesignSurfacePreview"),
                FakeObject("V1CorridorSubgradeSurfacePreview"),
                FakeObject("V1CorridorDrainageSurfacePreview"),
                FakeObject("V1CorridorIntersectionSurfacePreview"),
                FakeObject("V1CorridorIntersectionSlopeFaceSurfacePreview"),
                FakeObject("V1CorridorDaylightSurfacePreview"),
                FakeObject("ReviewSharedBreaklineHighlight"),
                FakeObject("ReviewIssueSlopeFaceIssue001L"),
                FakeObject("ReviewIssueDrainageFlowRoutes"),
            ]

        def getObject(self, name):
            for obj in self.Objects:
                if obj.Name == name:
                    return obj
            return None

    doc = FakeDocument()

    assert [row["group_id"] for row in build_corridor_command.corridor_build_visibility_groups()] == [
        "design",
        "intersection",
        "slope_face",
        "breaklines",
        "diagnostics",
    ]
    assert build_corridor_command.set_corridor_build_visibility_group(doc, "design", True) == 3
    assert doc.getObject("V1CorridorDesignSurfacePreview").ViewObject.Visibility is True
    assert doc.getObject("V1CorridorSubgradeSurfacePreview").ViewObject.Visibility is True
    assert doc.getObject("V1CorridorDrainageSurfacePreview").ViewObject.Visibility is True
    assert doc.getObject("V1CorridorIntersectionSurfacePreview").ViewObject.Visibility is False
    assert build_corridor_command.corridor_build_visibility_group_visible(doc, "design") is True

    assert build_corridor_command.set_corridor_build_visibility_group(doc, "slope_face", True) == 2
    assert doc.getObject("V1CorridorDaylightSurfacePreview").ViewObject.Visibility is True
    assert doc.getObject("V1CorridorIntersectionSlopeFaceSurfacePreview").ViewObject.Visibility is True
    assert build_corridor_command.set_corridor_build_visibility_group(doc, "breaklines", True) == 1
    assert doc.getObject("ReviewSharedBreaklineHighlight").ViewObject.Visibility is True
    assert build_corridor_command.set_corridor_build_visibility_group(doc, "diagnostics", True) >= 2
    assert doc.getObject("ReviewIssueSlopeFaceIssue001L").ViewObject.Visibility is True
    assert doc.getObject("ReviewIssueDrainageFlowRoutes").ViewObject.Visibility is True

    build_corridor_command.set_corridor_build_visibility_group(doc, "diagnostics", False)

    assert doc.getObject("ReviewIssueSlopeFaceIssue001L").ViewObject.Visibility is False
    assert doc.getObject("ReviewIssueDrainageFlowRoutes").ViewObject.Visibility is False


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
                FakeObject("V1CorridorIntersectionSlopeFaceSurfacePreview"),
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
    assert steps[3]["title"] == "5. Side Slope"
    assert steps[4]["title"] == "6. Drainage Surface"
    assert steps[5]["title"] == "7. Drainage Flow"
    assert steps[3]["status"] == "warning"
    assert steps[3]["focus"] == "Intersection and Corridor Slope Face Surfaces"

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
    assert focused.Name == "V1CorridorIntersectionSlopeFaceSurfacePreview"
    assert doc.getObject("V1CorridorDaylightSurfacePreview").ViewObject.Visibility is True
    assert doc.getObject("V1CorridorIntersectionSlopeFaceSurfacePreview").ViewObject.Visibility is True
    assert doc.getObject("V1CorridorRegionSurface_region_rural").ViewObject.Visibility is False
    assert doc.getObject("ReviewIssueSlopeFaceIssue001L").ViewObject.Visibility is False

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
        assert int(drainage_preview.PreviewFacetCount) == 4
        assert "surface:main" in list(drainage_preview.SourceRefs)
        assert "sections:ditch" in list(drainage_preview.SourceRefs)
        assert int(drainage_preview.VertexCount) == 8
        assert int(drainage_preview.TriangleCount) == 4
        build_outputs = ensure_project_tree(project, include_references=False)[V1_TREE_BUILD_PARAMETRIC_OUTPUTS]
        assert drainage_preview.Name in _group_names(build_outputs)
        rows = corridor_build_review_rows(doc)
        rows_by_role = {str(row["role"]): row for row in rows}
        assert rows_by_role["daylight"]["status"] == "error"
        assert "Slope Face Surface preview was not created" in str(rows_by_role["daylight"]["notes"])
        # the sections carry ditch points but declare no drainage surface role, so the
        # surface is built through the inferred fallback and the row says so
        assert rows_by_role["drainage"]["status"] == "warning"
        assert rows_by_role["drainage"]["output_path"] == "inferred_fallback"
        assert "surface role contract=missing; expected=drainage_surface" in str(
            rows_by_role["drainage"]["notes"]
        )
        assert rows_by_role["drainage"]["vertex_count"] == 8
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
        # The shared Centerline3D result is still the source (PreviewSource and
        # ConsumedCenterlineSourceMode stay centerline3d_source_geometry); only its
        # display curve follows the B-spline default set by fad9e6f.
        assert centerline.DisplayCurveKind == "bspline_display_bspline_smoothed"
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
        row = build_review_presentation._corridor_build_review_row(
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
        row = build_review_presentation._corridor_build_review_row(
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


def test_subassembly_kind_review_lane_uses_section_surface_strips_without_shape_polygons() -> None:
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
        assert obj.SourceMode == "applied_section_link_rows"
        assert obj.DisplayMode == "section_surface_strips"
        assert int(obj.SectionCount) == 4
        assert int(obj.ContinuityScopeCount) == 2
        assert int(obj.LinkCount) == 4
        assert int(obj.ShapeCount) == 0
        assert int(obj.SurfacePatchCount) == 4
    finally:
        App.closeDocument(doc.Name)


def test_subassembly_kind_review_shoulder_uses_section_surface_strips_without_shape_polygons() -> None:
    doc, project = _new_project_doc()
    try:
        def shoulder_section(section_id: str, alignment_id: str, station: float, x: float, y: float, tangent: float) -> AppliedSection:
            left_x = x
            left_y = y + 1.5
            if tangent == 90.0:
                left_x = x - 1.5
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
                        subassembly_id="shoulder:left",
                        kind="shoulder",
                        source_template_id="template:basic-road",
                        source_instance_ref="shoulder:left",
                        side="left",
                        width=1.5,
                    )
                ],
                subassembly_point_rows=[
                    AppliedSectionSubassemblyPoint(
                        "shoulder:left:start",
                        "shoulder:left",
                        "fg_surface",
                        x,
                        y,
                        10.0,
                        lateral_offset=0.0,
                        side="left",
                    ),
                    AppliedSectionSubassemblyPoint(
                        "shoulder:left:end",
                        "shoulder:left",
                        "fg_surface",
                        left_x,
                        left_y,
                        9.97,
                        lateral_offset=1.5,
                        side="left",
                    ),
                ],
                subassembly_link_rows=[
                    AppliedSectionSubassemblyLink(
                        "shoulder:left:fg",
                        "shoulder:left",
                        "shoulder:left:start",
                        "shoulder:left:end",
                        "shoulder_fg",
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
                shoulder_section("section:primary:0", "alignment:primary", 0.0, 0.0, 0.0, 0.0),
                shoulder_section("section:secondary:0", "alignment:secondary", 0.0, 50.0, 0.0, 90.0),
                shoulder_section("section:primary:20", "alignment:primary", 20.0, 20.0, 0.0, 0.0),
                shoulder_section("section:secondary:20", "alignment:secondary", 20.0, 50.0, 20.0, 90.0),
            ],
        )
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=applied)

        obj = build_corridor_command._create_subassembly_kind_review_highlight(
            document=doc,
            project=project,
            kind="shoulder",
            visible=False,
        )

        assert obj is not None
        assert obj.SourceMode == "applied_section_link_rows"
        assert obj.DisplayMode == "section_surface_strips"
        assert int(obj.SectionCount) == 4
        assert int(obj.ContinuityScopeCount) == 2
        assert int(obj.LinkCount) == 4
        assert int(obj.ShapeCount) == 0
        assert int(obj.SurfacePatchCount) == 4
    finally:
        App.closeDocument(doc.Name)


def test_subassembly_kind_review_strips_skip_intersection_owned_sections() -> None:
    doc, project = _new_project_doc()
    try:
        def lane_section(section_id: str, station: float, *, intersection_owned: bool = False) -> AppliedSection:
            return AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id=section_id,
                corridor_id="corridor:main",
                alignment_id="alignment:primary",
                profile_id="profile:primary",
                assembly_id="assembly:road",
                station=station,
                template_id="template:basic-road",
                region_id="region:primary-intersection" if intersection_owned else "region:ordinary",
                frame=AppliedSectionFrame(station=station, x=station, y=0.0, z=10.0, tangent_direction_deg=0.0),
                active_intersection_id="intersection:test" if intersection_owned else "",
                active_intersection_control_area_id="control-area:test" if intersection_owned else "",
                active_intersection_control_region_refs=["region:primary-intersection"] if intersection_owned else [],
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
                        station,
                        0.0,
                        10.0,
                        lateral_offset=0.0,
                        side="left",
                    ),
                    AppliedSectionSubassemblyPoint(
                        "lane:left:end",
                        "lane:left",
                        "fg_surface",
                        station,
                        3.5,
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
            applied_section_set_id="sections:intersection-filter",
            corridor_id="corridor:main",
            alignment_id="alignment:primary",
            station_rows=[
                AppliedSectionStationRow("row:0", 0.0, "section:0"),
                AppliedSectionStationRow("row:10", 10.0, "section:10"),
                AppliedSectionStationRow("row:20", 20.0, "section:20"),
                AppliedSectionStationRow("row:30", 30.0, "section:30"),
                AppliedSectionStationRow("row:40", 40.0, "section:40"),
            ],
            sections=[
                lane_section("section:0", 0.0),
                lane_section("section:10", 10.0),
                lane_section("section:20", 20.0, intersection_owned=True),
                lane_section("section:30", 30.0),
                lane_section("section:40", 40.0),
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
        assert obj.DisplayMode == "section_surface_strips"
        assert int(obj.SectionCount) == 4
        assert int(obj.LinkCount) == 4
        assert int(obj.SurfacePatchCount) == 4
        assert int(obj.SkippedIntersectionSectionCount) == 1
    finally:
        App.closeDocument(doc.Name)


def test_side_slope_compatibility_focus_uses_accepted_slope_face_surface() -> None:
    doc, _project = _new_project_doc()
    try:
        slope_preview = doc.addObject("Part::Feature", "V1CorridorDaylightSurfacePreview")
        slope_preview.Label = "Slope Face Surface - corridor:main"
        build_corridor_command._set_preview_integer_property(slope_preview, "VertexCount", 4)
        build_corridor_command._set_preview_integer_property(slope_preview, "TriangleCount", 2)

        focused = build_corridor_command.focus_corridor_subassembly_kind_review(doc, "side_slope")

        assert focused is slope_preview
    finally:
        App.closeDocument(doc.Name)


def test_side_slope_guided_review_prioritizes_intersection_result_and_removes_stale_marker() -> None:
    doc, _project = _new_project_doc()
    try:
        daylight = doc.addObject("Part::Feature", "V1CorridorDaylightSurfacePreview")
        intersection = doc.addObject("Part::Feature", "V1CorridorIntersectionSlopeFaceSurfacePreview")
        stale_marker = doc.addObject("Part::Feature", "ReviewIssueSubassemblyKind_side_slope")
        stale_marker_name = stale_marker.Name
        for obj in (daylight, intersection):
            build_corridor_command._set_preview_integer_property(obj, "VertexCount", 4)
            build_corridor_command._set_preview_integer_property(obj, "TriangleCount", 2)

        focused = focus_corridor_build_guided_review_step(doc, "slope_issues")

        assert focused is intersection
        assert doc.getObject(stale_marker_name) is None
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
        row = build_review_presentation._corridor_build_review_row(
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
        row = build_review_presentation._corridor_build_review_row(
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
