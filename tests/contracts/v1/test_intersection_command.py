from dataclasses import replace

import FreeCAD as App
from types import SimpleNamespace

from freecad.Corridor_Road.init_gui import corridorroad_workflow_command_groups, corridorroad_workflow_toolbar_commands
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, V1_TREE_INTERSECTIONS, ensure_project_tree, find_project
from freecad.Corridor_Road.v1.commands.cmd_intersection_editor import (
    INTERSECTION_COMMAND_ID,
    INTERSECTION_SOURCE_MODES,
    NEXT_INTERSECTION_WORKFLOW_TEXT,
    V1IntersectionEditorTaskPanel,
    alignment_model_by_ref,
    create_starter_intersection_sources,
    intersection_read_only_preview_rows,
    intersection_source_completeness_rows,
    intersection_source_completeness_summary,
    show_intersection_review_overlay,
    starter_intersection_source_specs,
    list_v1_alignment_choices,
    validate_existing_alignment_selection,
    INTERSECTION_REVIEW_MAX_REGION_SPAN,
    _starter_region_model_for_alignment,
    _unique_alignment_id,
)
from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import (
    CmdV1IntersectionPresets,
    INTERSECTION_PRESETS_COMMAND_ID,
    PRESET_SOURCE_MODES,
    build_existing_alignment_intersection_model,
    build_preset_source_intersection_model,
    create_intersection_from_existing_alignments,
    create_intersection_preset_sources,
    intersection_preset_kind_from_label,
    intersection_preset_labels,
    _route_intersection_preset_objects,
)
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    apply_v1_applied_section_set,
    build_document_applied_section_set,
    hide_applied_sections_preview_objects,
    show_all_applied_sections_preview_object,
)
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
    apply_v1_corridor_model,
    build_document_corridor_model,
    build_document_corridor_surface_model,
    corridor_intersection_contract_review_rows,
    corridor_intersection_patch_prerequisite_result,
    corridor_intersection_shared_breakline_result,
    corridor_build_review_rows,
    corridor_shared_breakline_audit_rows,
    corridor_build_visibility_groups,
    create_corridor_daylight_surface_preview,
    create_corridor_design_surface_preview,
    create_corridor_intersection_surface_preview,
    create_corridor_subgrade_surface_preview,
    focus_corridor_intersection_contract_review_row,
    focus_corridor_build_guided_review_step,
    set_corridor_build_visibility_group,
    shared_breakline_audit_display_rows,
    _breakline_audit_surface_row_focuses_source_only,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_drainage import to_drainage_model
from freecad.Corridor_Road.v1.objects.obj_intersection import find_v1_intersection_model, to_intersection_model
from freecad.Corridor_Road.v1.objects.obj_profile import to_profile_model
from freecad.Corridor_Road.v1.objects.obj_region import to_region_model
from freecad.Corridor_Road.v1.objects.obj_subassembly_assembly import (
    find_v1_assembly_subassembly_model,
    to_assembly_subassembly_model,
)
from freecad.Corridor_Road.v1.objects.obj_superelevation import to_superelevation_model
from freecad.Corridor_Road.v1.models.source.intersection_model import (
    IntersectionAnchorRow,
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
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_evaluation_service import IntersectionEvaluationService

_QAPP = None


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def test_intersection_command_is_between_regions_and_structures() -> None:
    commands = corridorroad_workflow_command_groups()["assembly_region"]
    toolbar = corridorroad_workflow_toolbar_commands()

    assert INTERSECTION_COMMAND_ID not in commands
    assert INTERSECTION_COMMAND_ID not in toolbar
    assert INTERSECTION_PRESETS_COMMAND_ID in commands
    assert commands.index("CorridorRoad_V1EditRegions") < commands.index(INTERSECTION_PRESETS_COMMAND_ID)
    assert commands.index(INTERSECTION_PRESETS_COMMAND_ID) < commands.index("CorridorRoad_V1EditStructures")
    assert INTERSECTION_PRESETS_COMMAND_ID in toolbar
    assert toolbar.index("CorridorRoad_V1EditRegions") < toolbar.index(INTERSECTION_PRESETS_COMMAND_ID)
    assert toolbar.index(INTERSECTION_PRESETS_COMMAND_ID) < toolbar.index("CorridorRoad_V1EditStructures")


def test_intersection_presets_command_resources_are_specific() -> None:
    resources = CmdV1IntersectionPresets().GetResources()

    assert resources["MenuText"] == "Intersection"
    assert "preset" in resources["ToolTip"].lower()
    assert str(resources["Pixmap"]).replace("\\", "/").endswith("intersections.svg")


def test_intersection_panel_constants_expose_first_slice_modes() -> None:
    assert INTERSECTION_SOURCE_MODES == ("Use Existing Alignments", "Create Starter Sources")
    assert NEXT_INTERSECTION_WORKFLOW_TEXT.endswith("Build Sections")


def test_intersection_starter_source_specs_cover_first_slice_types() -> None:
    expected_roles = {
        "t_intersection": {"primary", "secondary"},
        "cross_intersection": {"primary", "secondary"},
        "roundabout": {"primary", "secondary"},
    }
    for kind, roles in expected_roles.items():
        spec = starter_intersection_source_specs(kind)
        alignments = list(spec["alignments"])

        assert spec["kind"] == kind
        assert len(alignments) == len(roles)
        assert {row["role"] for row in alignments} == roles
        assert all(len(row["points"]) >= 2 for row in alignments)


def test_intersection_source_completeness_rows_cover_staged_workflow() -> None:
    rows = intersection_source_completeness_rows(None, alignment_errors=["Primary Alignment is required."], control_region_count=0)
    summary = intersection_source_completeness_summary(rows)

    assert [row["stage"] for row in rows] == [
        "Participants",
        "Anchor",
        "Legs",
        "Control Areas",
        "Corners",
        "Edge Families",
        "Lane Connections",
        "Grading",
        "Drainage",
        "Preview",
    ]
    assert rows[0]["status"] == "missing"
    assert rows[0]["approval_state"] == "missing"
    assert rows[0]["stage_id"] == "participants"
    assert rows[0]["handoff_target"] == "intersection-source-stage:participants"
    assert "Primary Alignment is required." in rows[0]["diagnostics"]
    assert rows[-1]["status"] == "missing"
    assert summary["status"] == "missing"
    assert summary["missing_count"] == 10
    assert summary["next_stage"] == "Participants"
    assert summary["preview_ready"] is False
    assert summary["apply_ready"] is False


def test_intersection_read_only_preview_rows_cover_result_sequence() -> None:
    rows = intersection_read_only_preview_rows(None, alignment_errors=["Primary Alignment is required."], control_region_count=0)

    assert [row["stage"] for row in rows] == [
        "Source Validation",
        "Topology",
        "Edge Network",
        "Surface Zones",
        "Grading",
        "Drainage",
        "Slope Loops",
    ]
    assert rows[0]["status"] == "missing"
    assert rows[0]["contract"] == "IntersectionModel source stages"
    assert rows[0]["handoff_target"] == "intersection-preview-stage:source_validation"
    assert rows[1]["contract"] == "IntersectionTopologyResult"
    assert all(row["status"] == "missing" for row in rows[1:])


def test_intersection_preset_panel_labels_map_to_source_kinds() -> None:
    labels = intersection_preset_labels()

    assert PRESET_SOURCE_MODES == ("Create From Preset", "Use Existing Alignments")
    assert labels == [
        "T Intersection - Basic",
        "Cross Intersection - Basic",
        "Roundabout - Single Lane",
    ]
    assert intersection_preset_kind_from_label("T Intersection - Basic") == "t_intersection"
    assert intersection_preset_kind_from_label("Cross Intersection - Basic") == "cross_intersection"
    assert intersection_preset_kind_from_label("Roundabout - Single Lane") == "roundabout"


def test_intersection_preset_source_creation_stores_intersection_model() -> None:
    doc = App.newDocument("CRV1IntersectionPresetSources")
    try:
        created = create_intersection_preset_sources(
            doc,
            preset_label="T Intersection - Basic",
            grading_policy="blend_primary_side",
            drainage_mode="outside_gutter",
        )
        obj = find_v1_intersection_model(doc)
        model = to_intersection_model(obj)

        assert any(line.startswith("IntersectionModel:") for line in created)
        assert obj is not None
        assert model is not None
        assert "intersection-preset:t_intersection:source-completeness" in model.source_refs
        assert len(model.intersection_rows) == 1
        row = model.intersection_rows[0]
        assert row.intersection_kind == "t_intersection"
        assert "Preset source completeness" in row.notes
        assert "source_completeness_ref=intersection-preset:t_intersection:source-completeness" in row.notes
        assert row.primary_alignment_ref
        assert row.secondary_alignment_refs
        assert len(row.control_region_refs) == 2
        assert "preset_anchor_review_required" in model.anchor_rows[0].diagnostic_rows
        assert all("preset_control_area_review_required" in control.diagnostic_rows for control in model.control_area_rows)
        assert all("preset_corner_review_required" in corner.diagnostic_rows for corner in model.corner_rows)
        assert all("preset_edge_family_review_required" in edge.diagnostic_rows for edge in model.edge_policy_rows)
        assert len(model.arm_policy_rows) == 2
        assert len(model.edge_policy_rows) == 4
        assert len(model.curb_return_policy_rows) == 1
        assert len(model.corner_rows) == 2
        assert model.curb_return_policy_rows[0].corner_refs == [row.corner_id for row in model.corner_rows]
        assert len(model.lane_connection_rows) == 2
        assert model.lane_connection_rows[0].approval_status == "draft"
        assert all("preset_lane_connection_review_required" in lane.diagnostic_rows for lane in model.lane_connection_rows)
        assert len(model.grading_policy_rows) == 1
        assert model.grading_policy_rows[0].mode == "blend_primary_side"
        assert "preset_grading_policy_review_required" in model.grading_policy_rows[0].diagnostic_rows
        assert len(model.drainage_policy_rows) == 1
        assert model.drainage_policy_rows[0].capture_mode == "outside_gutter"
        assert "preset_drainage_policy_review_required" in model.drainage_policy_rows[0].diagnostic_rows

        superelevation = to_superelevation_model(doc.getObject("V1IntersectionPresetSuperelevation"))
        drainage = to_drainage_model(doc.getObject("V1IntersectionPresetDrainage"))
        assembly = to_assembly_subassembly_model(find_v1_assembly_subassembly_model(doc))
        region_models = [
            to_region_model(region_obj)
            for region_obj in list(getattr(doc, "Objects", []) or [])
            if str(getattr(region_obj, "V1ObjectType", "") or "") == "V1RegionModel"
        ]
        region_models = [region_model for region_model in region_models if region_model is not None]
        assert superelevation is not None
        assert superelevation.superelevation_kind == "intersection_superelevation_handoff"
        assert len(superelevation.control_rows) == 0
        assert len(superelevation.constraint_rows) == 2
        assert superelevation.constraint_rows[0].value == "blend_primary_side"
        assert drainage is not None
        assert drainage.drainage_model_id == "drainage:intersection-preset-t-intersection"
        assert len(drainage.element_rows) == 2
        assert len(drainage.policy_rows) == 1
        assert len(drainage.flow_route_rows) == 1
        assert assembly is not None
        assert assembly.assembly_id
        assert assembly.active_template_id
        assert any(
            row.kind == "lane" for template in assembly.template_rows for row in template.subassembly_rows
        )
        assert any(
            row.kind == "shoulder" for template in assembly.template_rows for row in template.subassembly_rows
        )
        assert any(
            row.kind == "side_slope" for template in assembly.template_rows for row in template.subassembly_rows
        )
        assert region_models
        assert all(
            region_row.assembly_ref == assembly.assembly_id
            and region_row.template_ref == assembly.active_template_id
            for region_model in region_models
            for region_row in region_model.region_rows
        )

        completeness_rows = intersection_source_completeness_rows(model, control_region_count=len(row.control_region_refs))
        completeness_summary = intersection_source_completeness_summary(completeness_rows)
        rows_by_stage = {stage_row["stage"]: stage_row for stage_row in completeness_rows}
        assert rows_by_stage["Participants"]["status"] == "accepted"
        assert rows_by_stage["Anchor"]["status"] == "warning"
        assert rows_by_stage["Anchor"]["approval_state"] == "draft"
        assert rows_by_stage["Anchor"]["source_methods"] == ["detected"]
        assert rows_by_stage["Lane Connections"]["count"] == 2
        assert rows_by_stage["Lane Connections"]["approval_state"] == "draft"
        assert rows_by_stage["Drainage"]["status"] == "warning"
        assert rows_by_stage["Drainage"]["approval_state"] == "draft"
        assert completeness_summary["status"] == "warning"
        assert completeness_summary["missing_count"] == 0
        assert completeness_summary["next_stage"] == "Anchor"
        assert completeness_summary["preview_ready"] is True
        preview_rows = intersection_read_only_preview_rows(model, source_rows=completeness_rows)
        preview_by_stage = {stage_row["stage"]: stage_row for stage_row in preview_rows}
        assert preview_by_stage["Source Validation"]["status"] == "warning"
        assert preview_by_stage["Topology"]["contract"] == "IntersectionTopologyResult"
        assert preview_by_stage["Edge Network"]["count"] > 0
        assert preview_by_stage["Surface Zones"]["contract"] == "IntersectionSurfaceZoneResult"
        assert preview_by_stage["Grading"]["contract"] == "IntersectionGradingContextResult"
        assert preview_by_stage["Drainage"]["contract"] == "IntersectionDrainageHintResult"
        assert preview_by_stage["Slope Loops"]["contract"] == "IntersectionSlopeFaceLoopResult"
    finally:
        App.closeDocument(doc.Name)


def test_intersection_preset_t_source_builds_zero_mismatch_shared_breakline_preview() -> None:
    doc = App.newDocument("CRV1IntersectionPresetTBreaklineE2E")
    try:
        create_intersection_preset_sources(
            doc,
            preset_label="T Intersection - Basic",
            grading_policy="blend_primary_side",
            drainage_mode="outside_gutter",
        )
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        design_preview = create_corridor_design_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        slope_preview = create_corridor_daylight_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        rows = corridor_build_review_rows(doc)
        intersection_row = [row for row in rows if row["role"] == "intersection"][0]
        design_row = [row for row in rows if row["role"] == "design"][0]
        slope_row = [row for row in rows if row["role"] == "daylight"][0]

        assert len(applied.sections) > 0
        assert preview is not None
        assert design_preview is not None
        assert slope_preview is not None
        assert preview.SharedBreaklineResultId == "shared-breakline:intersection:intersection:starter-t_intersection"
        assert preview.SharedBreaklineAuditStatus == "ready"
        assert int(preview.SharedBreaklineCount) == 36
        assert int(preview.SharedBreaklineConsumedCount) == 36
        assert int(preview.SharedBreaklineGeometryMismatchCount) == 0
        assert int(preview.SharedBreaklineMeshMismatchCount) == 0
        assert int(preview.SharedBreaklineReversedEdgeCount) == 0
        assert any("curb-return-outer" in ref for ref in list(preview.SharedBreaklineRefs))
        assert any("curb-return-inner" in ref for ref in list(preview.SharedBreaklineRefs))
        assert any("curb-return-to-pavement" in ref for ref in list(preview.SharedBreaklineRefs))
        assert any("curb-return-to-shoulder" in ref for ref in list(preview.SharedBreaklineRefs))
        assert any("curb-return-to-slope-face" in ref for ref in list(preview.SharedBreaklineRefs))
        assert any("patch-to-shoulder" in ref for ref in list(preview.SharedBreaklineRefs))
        assert any("control_area_entry" in ref for ref in list(preview.SharedBreaklineRefs))
        assert any("control_area_exit" in ref for ref in list(preview.SharedBreaklineRefs))
        assert any("intersection_gutter_handoff" in ref for ref in list(preview.SharedBreaklineRefs))
        assert any("low_point_flow_split" in ref for ref in list(preview.SharedBreaklineRefs))
        assert preview.SharedBreaklineMaterialSummary == "curb_return=4, design_surface=4, drainage_surface=6, pavement=8, shoulder=5, side_slope=5, slope_face_surface=4"
        assert "control_area_entry=4" in preview.SharedBreaklineRoleSummary
        assert "control_area_exit=4" in preview.SharedBreaklineRoleSummary
        assert "patch_to_design_pavement_tie_in=2" in preview.SharedBreaklineRoleSummary
        assert "patch_to_design_stem_tie_in=2" in preview.SharedBreaklineRoleSummary
        assert "shared_breakline=ready consumed=36/36" in intersection_row["notes"]
        assert "audit=ready geometry=36/36 mesh=36/36" in intersection_row["notes"]
        assert any("curb-return-to-pavement" in ref for ref in list(design_preview.SharedBreaklineRefs))
        assert any("curb-return-to-shoulder" in ref for ref in list(design_preview.SharedBreaklineRefs))
        assert "pavement=8" in design_preview.SharedBreaklineMaterialSummary
        assert "shoulder=6" in design_preview.SharedBreaklineMaterialSummary
        assert "design_surface=34" in design_preview.SharedBreaklineMaterialSummary
        assert "control_area_entry=2" in design_preview.SharedBreaklineRoleSummary
        assert "control_area_exit=2" in design_preview.SharedBreaklineRoleSummary
        assert "patch_to_design_pavement_tie_in=2" in design_preview.SharedBreaklineRoleSummary
        assert "patch_to_design_stem_tie_in=2" in design_preview.SharedBreaklineRoleSummary
        assert int(design_preview.SharedBreaklineGeometryMismatchCount) == 0
        assert int(design_preview.SharedBreaklineMeshMismatchCount) == 0
        assert "audit=ready" in design_row["notes"]
        assert any("curb-return-to-slope-face" in ref for ref in list(slope_preview.SharedBreaklineRefs))
        assert "side_slope=5" in slope_preview.SharedBreaklineMaterialSummary
        assert "slope_face_surface=31" in slope_preview.SharedBreaklineMaterialSummary
        assert "shoulder=1" in slope_preview.SharedBreaklineMaterialSummary
        assert "control_area_entry=2" in slope_preview.SharedBreaklineRoleSummary
        assert "control_area_exit=2" in slope_preview.SharedBreaklineRoleSummary
        assert int(slope_preview.SharedBreaklineGeometryMismatchCount) == 0
        assert int(slope_preview.SharedBreaklineMeshMismatchCount) == 0
        assert "audit=ready" in slope_row["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_cross_intersection_preset_source_completeness_marks_default_rows_for_review() -> None:
    doc = App.newDocument("CRV1CrossIntersectionPresetSourceCompleteness")
    try:
        created = create_intersection_preset_sources(
            doc,
            preset_label="Cross Intersection - Basic",
            grading_policy="blend_primary_side",
            drainage_mode="review_low_points",
        )
        model = to_intersection_model(find_v1_intersection_model(doc))

        assert any("Source completeness: preset default/draft rows require review" in line for line in created)
        assert model is not None
        assert "intersection-preset:cross_intersection:source-completeness" in model.source_refs
        assert model.intersection_rows[0].intersection_kind == "cross_intersection"
        assert "source_completeness_ref=intersection-preset:cross_intersection:source-completeness" in model.intersection_rows[0].notes
        assert all(
            "source_completeness_ref=intersection-preset:cross_intersection:source-completeness" in row.notes
            for row in [
                *model.control_area_rows,
                *model.corner_rows,
                *model.edge_policy_rows,
                *model.lane_connection_rows,
                *model.grading_policy_rows,
                *model.drainage_policy_rows,
            ]
        )
        assert len(model.corner_rows) == 4
        assert len(model.edge_policy_rows) >= 4
        assert len(model.lane_connection_rows) >= 2
        assert all(row.approval_status == "draft" for row in model.control_area_rows)
        assert all("preset_control_area_review_required" in row.diagnostic_rows for row in model.control_area_rows)
        assert all("preset_corner_review_required" in row.diagnostic_rows for row in model.corner_rows)
        assert all("preset_edge_family_review_required" in row.diagnostic_rows for row in model.edge_policy_rows)
        assert all("preset_lane_connection_review_required" in row.diagnostic_rows for row in model.lane_connection_rows)
        assert "preset_grading_policy_review_required" in model.grading_policy_rows[0].diagnostic_rows
        assert "preset_drainage_policy_review_required" in model.drainage_policy_rows[0].diagnostic_rows

        completeness_rows = intersection_source_completeness_rows(
            model,
            control_region_count=len(model.intersection_rows[0].control_region_refs),
        )
        rows_by_stage = {stage_row["stage"]: stage_row for stage_row in completeness_rows}
        assert rows_by_stage["Control Areas"]["approval_state"] == "draft"
        assert rows_by_stage["Corners"]["approval_state"] == "draft"
        assert rows_by_stage["Edge Families"]["approval_state"] == "draft"
        assert rows_by_stage["Lane Connections"]["approval_state"] == "draft"
        assert rows_by_stage["Grading"]["approval_state"] == "draft"
        assert rows_by_stage["Drainage"]["approval_state"] == "draft"
    finally:
        App.closeDocument(doc.Name)


def test_intersection_editor_panel_exposes_source_completeness_table() -> None:
    doc = App.newDocument("CRV1IntersectionPanelSourceCompleteness")
    try:
        _ensure_qapp()
        panel = V1IntersectionEditorTaskPanel(document=doc)

        assert panel._source_stage_table.rowCount() == 10
        assert panel._source_stage_table.columnCount() == 6
        assert panel._source_stage_table.item(0, 0).text() == "Participants"
        assert panel._source_stage_table.item(0, 1).text() == "missing"
        assert panel._source_stage_table.item(0, 2).text() == "missing"
        assert panel._source_stage_table.item(0, 4).text() == "intersection-source-stage:participants"
        assert panel._preview_stage_table.rowCount() == 7
        assert panel._preview_stage_table.columnCount() == 5
        assert panel._preview_stage_table.item(0, 0).text() == "Source Validation"
        assert panel._preview_stage_table.item(0, 3).text() == "IntersectionModel source stages"
        assert "Source Summary: missing" in panel._status.toPlainText()
        assert "Next Source Stage: Participants" in panel._status.toPlainText()
        assert "Preview Ready: no" in panel._status.toPlainText()
        assert "Read-only Preview Sequence:" in panel._status.toPlainText()

        assert panel.focus_source_stage("intersection-source-stage:anchor") is True
        assert panel._source_stage_table.currentRow() == 1
        assert "Focused source stage: Anchor" in panel._status.toPlainText()
        assert panel.focus_source_stage("does-not-exist") is False
    finally:
        App.closeDocument(doc.Name)


def test_intersection_editor_panel_smoke_reports_preset_warning_stages_without_output_geometry() -> None:
    doc = App.newDocument("CRV1IntersectionPanelPresetSourceSmoke")
    try:
        create_starter_intersection_sources(doc, "cross_intersection")
        _ensure_qapp()
        panel = V1IntersectionEditorTaskPanel(document=doc)
        panel._type_combo.setCurrentText("Cross Intersection")
        panel._source_mode_combo.setCurrentText("Create Starter Sources")
        if panel._primary_alignment_combo.count() > 1:
            panel._primary_alignment_combo.setCurrentIndex(1)
        if panel._secondary_alignment_combo.count() > 2:
            panel._secondary_alignment_combo.setCurrentIndex(2)
        panel._update_status()

        assert find_v1_intersection_model(doc) is None
        assert panel._source_stage_table.rowCount() == 10
        rows_by_stage = {row["stage"]: row for row in panel._last_source_stage_rows}
        assert rows_by_stage["Participants"]["status"] == "accepted"
        assert rows_by_stage["Anchor"]["status"] == "warning"
        assert rows_by_stage["Anchor"]["approval_state"] == "draft"
        assert rows_by_stage["Corners"]["approval_state"] == "draft"
        assert rows_by_stage["Edge Families"]["approval_state"] == "draft"
        assert rows_by_stage["Lane Connections"]["approval_state"] == "draft"
        assert rows_by_stage["Grading"]["approval_state"] == "draft"
        assert rows_by_stage["Drainage"]["approval_state"] == "draft"
        assert any(
            diagnostic.startswith("handoff_target:intersection-source-stage:anchor:")
            for diagnostic in rows_by_stage["Anchor"]["diagnostics"]
        )
        assert any(
            diagnostic.startswith("handoff_target:intersection-source-stage:lane_connections:")
            for diagnostic in rows_by_stage["Lane Connections"]["diagnostics"]
        )
        assert any(
            diagnostic.startswith("handoff_target:intersection-source-stage:drainage:")
            for diagnostic in rows_by_stage["Drainage"]["diagnostics"]
        )

        preview_by_stage = {row["stage"]: row for row in panel._last_preview_stage_rows}
        assert preview_by_stage["Source Validation"]["status"] == "warning"
        assert preview_by_stage["Topology"]["contract"] == "IntersectionTopologyResult"
        assert preview_by_stage["Edge Network"]["contract"] == "IntersectionEdgeNetworkResult"
        assert any(
            diagnostic.startswith("handoff_target:intersection-preview-stage:grading:")
            for diagnostic in preview_by_stage["Grading"]["diagnostics"]
        )
        assert any(
            diagnostic.startswith("handoff_target:intersection-source-stage:drainage:")
            for diagnostic in preview_by_stage["Drainage"]["diagnostics"]
        )
        assert "source_lineage_status:source_warning" in preview_by_stage["Slope Loops"]["diagnostics"]
        assert "Source Summary: warning" in panel._status.toPlainText()
        assert "Preview Ready: yes" in panel._status.toPlainText()
        assert "Apply Ready: yes" in panel._status.toPlainText()
        assert panel.focus_source_stage("intersection-source-stage:drainage") is True
        assert panel._source_stage_table.currentRow() == 8
        assert "Focused source stage: Drainage" in panel._status.toPlainText()
        assert find_v1_intersection_model(doc) is None
    finally:
        App.closeDocument(doc.Name)


def test_intersection_preset_existing_alignment_mode_builds_model_from_selected_refs() -> None:
    doc = App.newDocument("CRV1IntersectionPresetExistingAlignments")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        model = to_intersection_model(find_v1_intersection_model(doc))
        primary_ref = model.intersection_rows[0].primary_alignment_ref
        secondary_ref = model.intersection_rows[0].secondary_alignment_refs[0]

        rebuilt, control_region_count = build_existing_alignment_intersection_model(
            doc,
            preset_label="T Intersection - Basic",
            primary_alignment_ref=primary_ref,
            secondary_alignment_ref=secondary_ref,
            grading_policy="keep_primary_crown",
            drainage_mode="central_island",
        )

        assert rebuilt.intersection_rows[0].source_mode == "use_existing_alignments"
        assert rebuilt.intersection_rows[0].primary_alignment_ref == primary_ref
        assert rebuilt.intersection_rows[0].secondary_alignment_refs == [secondary_ref]
        assert rebuilt.grading_policy_rows[0].mode == "keep_primary_crown"
        assert rebuilt.drainage_policy_rows[0].capture_mode == "central_island"
        assert control_region_count >= 2
    finally:
        App.closeDocument(doc.Name)


def test_intersection_preset_create_from_preset_mode_builds_edge_preview_model() -> None:
    doc = App.newDocument("CRV1IntersectionPresetPreviewFromPreset")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")

        model, control_region_count, detection = build_preset_source_intersection_model(
            doc,
            preset_label="T Intersection - Basic",
            grading_policy="blend_primary_side",
            drainage_mode="review_low_points",
        )
        edge_network = IntersectionEvaluationService().evaluate_edge_network(model)

        assert model.intersection_rows[0].source_mode == "create_starter_sources"
        assert control_region_count >= 2
        assert detection is not None
        assert edge_network.edge_count > 0
        assert any(row.edge_family == "curb_return" for row in edge_network.edge_rows)
    finally:
        App.closeDocument(doc.Name)


def test_intersection_topology_reports_source_completeness_diagnostics() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="corridorroad-v1",
        intersection_model_id="intersections:source-completeness",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:source-completeness",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=[],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="intersection:source-completeness:leg:01",
                        leg_role="primary_control",
                        alignment_ref="alignment:main",
                        intersection_id="intersection:source-completeness",
                        approach_station_start=10.0,
                        approach_station_end=40.0,
                        source_method="region_derived",
                        approval_status="draft",
                        span_source="control_region",
                    )
                ],
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="intersection:source-completeness:control-area:01",
                intersection_id="intersection:source-completeness",
                alignment_ref="alignment:main",
                station_ranges=[(10.0, 40.0)],
                source_method="region_derived",
                approval_status="draft",
                intent_status="region_derived",
                diagnostic_rows=["control_area_region_derived"],
            )
        ],
    )

    service = IntersectionEvaluationService()
    topology = service.evaluate_topology(model)
    edge_network = service.evaluate_edge_network(model, topology)

    assert topology.status == "warning"
    assert topology.anchor_count == 0
    assert "warning:source_intersection_anchor_rows_missing:intersection:source-completeness" in topology.diagnostic_rows
    assert topology.leg_span_rows[0].source_status == "warning"
    assert topology.leg_span_rows[0].source_method == "region_derived"
    assert topology.leg_span_rows[0].approval_status == "draft"
    assert topology.leg_span_rows[0].span_source == "control_region"
    assert "source_leg_approval_pending" in topology.leg_span_rows[0].source_diagnostic_rows
    assert "source_leg_span_control_region" in topology.leg_span_rows[0].source_diagnostic_rows
    assert "source_leg_profile_ref_missing" in topology.leg_span_rows[0].source_diagnostic_rows
    assert "source_leg_centerline3d_ref_missing" in topology.leg_span_rows[0].source_diagnostic_rows
    assert "source_leg_region_ref_missing" in topology.leg_span_rows[0].source_diagnostic_rows
    assert topology.control_area_rows[0].source_status == "warning"
    assert topology.control_area_rows[0].source_method == "region_derived"
    assert topology.control_area_rows[0].approval_status == "draft"
    assert topology.control_area_rows[0].intent_status == "region_derived"
    assert "control_area_region_derived" in topology.control_area_rows[0].source_diagnostic_rows
    assert "source_control_area_approval_pending" in topology.control_area_rows[0].source_diagnostic_rows
    assert "source_control_area_intent_region_derived" in topology.control_area_rows[0].source_diagnostic_rows
    assert "source_control_area_source_region_refs_missing" in topology.control_area_rows[0].source_diagnostic_rows
    assert "source_control_area_region_refs_missing" in topology.control_area_rows[0].source_diagnostic_rows
    assert "warning:source_intersection_control_region_refs_missing:intersection:source-completeness" in topology.diagnostic_rows
    assert "warning:source_intersection_curb_return_policy_rows_missing:intersection:source-completeness" in topology.diagnostic_rows
    assert any(row.startswith("warning:source_leg_profile_ref_missing:") for row in edge_network.diagnostic_rows)


def test_intersection_anchor_result_reports_unknown_source_method_and_status() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="corridorroad-v1",
        intersection_model_id="intersections:anchor-source-validation",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:anchor-source-validation",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=["region:main-control"],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="leg:main",
                        leg_role="primary_before",
                        alignment_ref="alignment:main",
                        intersection_id="intersection:anchor-source-validation",
                        profile_ref="profile:main",
                        centerline3d_ref="centerline:main",
                        region_ref="region:main-control",
                        approach_station_start=0.0,
                        approach_station_end=50.0,
                    )
                ],
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="control-area:main",
                intersection_id="intersection:anchor-source-validation",
                alignment_ref="alignment:main",
                station_ranges=[(0.0, 50.0)],
                control_region_refs=["region:main-control"],
            )
        ],
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:unknown-source",
                intersection_id="intersection:anchor-source-validation",
                source_method="mesh_repaired",
                approval_status="auto_accepted",
                primary_alignment_ref="alignment:main",
                primary_station=25.0,
                secondary_station_refs={"alignment:side": 12.5},
                point_x=25.0,
                point_y=0.0,
                tolerance=0.01,
            )
        ],
    )

    topology = IntersectionEvaluationService().evaluate_topology(model)

    assert topology.status == "warning"
    assert topology.anchor_count == 1
    anchor = topology.anchor_rows[0]
    assert anchor.source_method == "mesh_repaired"
    assert anchor.approval_status == "auto_accepted"
    assert anchor.source_status == "warning"
    assert anchor.status == "warning"
    assert anchor.station_lineage_status == "source_warning"
    assert anchor.handoff_target == "intersection-source-stage:anchor:anchor-unknown-source"
    assert "source_anchor_method_unknown" in anchor.source_diagnostic_rows
    assert "source_anchor_approval_status_unknown" in anchor.source_diagnostic_rows
    assert "source_anchor_approval_pending" in anchor.source_diagnostic_rows
    assert "warning:source_anchor_method_unknown:anchor:unknown-source:mesh_repaired" in topology.diagnostic_rows
    assert "warning:source_anchor_approval_status_unknown:anchor:unknown-source:auto_accepted" in topology.diagnostic_rows


def test_intersection_anchor_result_marks_missing_primary_alignment_as_error() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="corridorroad-v1",
        intersection_model_id="intersections:anchor-primary-missing",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:anchor-primary-missing",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=["region:main-control"],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="leg:main",
                        leg_role="primary_before",
                        alignment_ref="alignment:main",
                        intersection_id="intersection:anchor-primary-missing",
                        profile_ref="profile:main",
                        centerline3d_ref="centerline:main",
                        region_ref="region:main-control",
                        approach_station_start=0.0,
                        approach_station_end=50.0,
                    )
                ],
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="control-area:main",
                intersection_id="intersection:anchor-primary-missing",
                alignment_ref="alignment:main",
                station_ranges=[(0.0, 50.0)],
                control_region_refs=["region:main-control"],
            )
        ],
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:missing-primary",
                intersection_id="intersection:anchor-primary-missing",
                source_method="manual",
                approval_status="locked",
                primary_alignment_ref="",
                primary_station=25.0,
                secondary_station_refs={"alignment:side": 12.5},
                point_x=25.0,
                point_y=0.0,
                tolerance=0.01,
            )
        ],
    )

    topology = IntersectionEvaluationService().evaluate_topology(model)

    assert topology.status == "error"
    anchor = topology.anchor_rows[0]
    assert anchor.source_status == "error"
    assert anchor.status == "error"
    assert anchor.station_lineage_status == "primary_missing"
    assert "source_anchor_primary_alignment_ref_missing" in anchor.source_diagnostic_rows
    assert "error:source_anchor_primary_alignment_ref_missing:anchor:missing-primary" in topology.diagnostic_rows


def test_intersection_leg_result_reports_unknown_source_method_status_and_span_source() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="corridorroad-v1",
        intersection_model_id="intersections:leg-source-validation",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:leg-source-validation",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=["region:main-control"],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="leg:unknown-source",
                        leg_role="primary_before",
                        alignment_ref="alignment:main",
                        intersection_id="intersection:leg-source-validation",
                        profile_ref="profile:main",
                        centerline3d_ref="centerline:main",
                        region_ref="region:main-control",
                        approach_station_start=0.0,
                        approach_station_end=50.0,
                        source_method="mesh_repaired",
                        approval_status="auto_accepted",
                        span_source="mesh_extent",
                    )
                ],
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="control-area:main",
                intersection_id="intersection:leg-source-validation",
                alignment_ref="alignment:main",
                station_ranges=[(0.0, 50.0)],
                control_region_refs=["region:main-control"],
            )
        ],
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:accepted",
                intersection_id="intersection:leg-source-validation",
                source_method="manual",
                approval_status="locked",
                primary_alignment_ref="alignment:main",
                primary_station=25.0,
                secondary_station_refs={"alignment:side": 12.5},
                point_x=25.0,
                point_y=0.0,
                tolerance=0.01,
            )
        ],
    )

    topology = IntersectionEvaluationService().evaluate_topology(model)

    assert topology.status == "warning"
    assert topology.leg_span_count == 1
    leg = topology.leg_span_rows[0]
    assert leg.source_method == "mesh_repaired"
    assert leg.approval_status == "auto_accepted"
    assert leg.span_source == "mesh_extent"
    assert leg.source_status == "warning"
    assert leg.status == "warning"
    assert "source_leg_method_unknown" in leg.source_diagnostic_rows
    assert "source_leg_approval_status_unknown" in leg.source_diagnostic_rows
    assert "source_leg_approval_pending" in leg.source_diagnostic_rows
    assert "source_leg_span_source_unknown" in leg.source_diagnostic_rows
    assert "warning:source_leg_method_unknown:leg:unknown-source:mesh_repaired" in topology.diagnostic_rows
    assert "warning:source_leg_approval_status_unknown:leg:unknown-source:auto_accepted" in topology.diagnostic_rows
    assert "warning:source_leg_span_source_unknown:leg:unknown-source:mesh_extent" in topology.diagnostic_rows


def test_intersection_leg_result_marks_missing_alignment_as_error() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="corridorroad-v1",
        intersection_model_id="intersections:leg-alignment-missing",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:leg-alignment-missing",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=["region:main-control"],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="leg:missing-alignment",
                        leg_role="primary_before",
                        alignment_ref="",
                        intersection_id="intersection:leg-alignment-missing",
                        profile_ref="profile:main",
                        centerline3d_ref="centerline:main",
                        region_ref="region:main-control",
                        approach_station_start=0.0,
                        approach_station_end=50.0,
                        source_method="manual",
                        approval_status="locked",
                        span_source="explicit",
                    )
                ],
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="control-area:main",
                intersection_id="intersection:leg-alignment-missing",
                alignment_ref="alignment:main",
                station_ranges=[(0.0, 50.0)],
                control_region_refs=["region:main-control"],
            )
        ],
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:leg-alignment-missing",
                intersection_id="intersection:leg-alignment-missing",
                source_method="manual",
                approval_status="locked",
                primary_alignment_ref="alignment:main",
                primary_station=25.0,
                secondary_station_refs={"alignment:side": 12.5},
                point_x=25.0,
                point_y=0.0,
                tolerance=0.01,
            )
        ],
    )

    topology = IntersectionEvaluationService().evaluate_topology(model)

    assert topology.status == "error"
    leg = topology.leg_span_rows[0]
    assert leg.source_status == "error"
    assert leg.status == "error"
    assert "missing_alignment" in leg.source_diagnostic_rows
    assert "error:leg_missing_alignment_ref:leg:missing-alignment" in topology.diagnostic_rows


def test_intersection_control_area_result_reports_unknown_source_method_status_and_intent() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="corridorroad-v1",
        intersection_model_id="intersections:control-area-source-validation",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:control-area-source-validation",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=["region:main-control"],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="leg:main",
                        leg_role="primary_before",
                        alignment_ref="alignment:main",
                        intersection_id="intersection:control-area-source-validation",
                        profile_ref="profile:main",
                        centerline3d_ref="centerline:main",
                        region_ref="region:main-control",
                        approach_station_start=0.0,
                        approach_station_end=50.0,
                    )
                ],
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="control-area:unknown-source",
                intersection_id="intersection:control-area-source-validation",
                alignment_ref="alignment:main",
                station_ranges=[(0.0, 50.0)],
                control_region_refs=["region:main-control"],
                source_region_refs=["region:main-control"],
                source_method="mesh_repaired",
                approval_status="auto_accepted",
                intent_status="mesh_patch",
            )
        ],
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:accepted",
                intersection_id="intersection:control-area-source-validation",
                source_method="manual",
                approval_status="locked",
                primary_alignment_ref="alignment:main",
                primary_station=25.0,
                secondary_station_refs={"alignment:side": 12.5},
                point_x=25.0,
                point_y=0.0,
                tolerance=0.01,
            )
        ],
    )

    topology = IntersectionEvaluationService().evaluate_topology(model)

    assert topology.status == "warning"
    assert topology.control_area_count == 1
    control_area = topology.control_area_rows[0]
    assert control_area.source_method == "mesh_repaired"
    assert control_area.approval_status == "auto_accepted"
    assert control_area.intent_status == "mesh_patch"
    assert control_area.source_status == "warning"
    assert control_area.status == "warning"
    assert control_area.region_handoff_status == "review_required"
    assert control_area.clipping_handoff_status == "review_required"
    assert control_area.handoff_target == "intersection-source-stage:control_areas:control-area-unknown-source"
    assert "source_control_area_method_unknown" in control_area.source_diagnostic_rows
    assert "source_control_area_approval_status_unknown" in control_area.source_diagnostic_rows
    assert "source_control_area_approval_pending" in control_area.source_diagnostic_rows
    assert "source_control_area_intent_unknown" in control_area.source_diagnostic_rows
    assert "source_control_area_intent_mesh_patch" not in control_area.source_diagnostic_rows
    assert "warning:source_control_area_method_unknown:control-area:unknown-source:mesh_repaired" in topology.diagnostic_rows
    assert "warning:source_control_area_approval_status_unknown:control-area:unknown-source:auto_accepted" in topology.diagnostic_rows
    assert "warning:source_control_area_intent_unknown:control-area:unknown-source:mesh_patch" in topology.diagnostic_rows


def test_intersection_control_area_result_marks_missing_alignment_and_station_range_as_error() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="corridorroad-v1",
        intersection_model_id="intersections:control-area-blocking-source",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:control-area-blocking-source",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=["region:main-control"],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="leg:main",
                        leg_role="primary_before",
                        alignment_ref="alignment:main",
                        intersection_id="intersection:control-area-blocking-source",
                        profile_ref="profile:main",
                        centerline3d_ref="centerline:main",
                        region_ref="region:main-control",
                        approach_station_start=0.0,
                        approach_station_end=50.0,
                    )
                ],
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="control-area:blocking-source",
                intersection_id="intersection:control-area-blocking-source",
                alignment_ref="",
                station_ranges=[],
                control_region_refs=["region:main-control"],
                source_method="manual",
                approval_status="locked",
                intent_status="intersection_owned",
            )
        ],
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:control-area-blocking-source",
                intersection_id="intersection:control-area-blocking-source",
                source_method="manual",
                approval_status="locked",
                primary_alignment_ref="alignment:main",
                primary_station=25.0,
                secondary_station_refs={"alignment:side": 12.5},
                point_x=25.0,
                point_y=0.0,
                tolerance=0.01,
            )
        ],
    )

    topology = IntersectionEvaluationService().evaluate_topology(model)

    assert topology.status == "error"
    control_area = topology.control_area_rows[0]
    assert control_area.source_status == "error"
    assert control_area.status == "error"
    assert control_area.region_handoff_status == "review_required"
    assert control_area.clipping_handoff_status == "missing"
    assert "missing_alignment" in control_area.source_diagnostic_rows
    assert "missing_station_range" in control_area.source_diagnostic_rows
    assert "error:control_area_missing_alignment_ref:control-area:blocking-source" in topology.diagnostic_rows
    assert "error:control_area_station_ranges_missing:control-area:blocking-source" in topology.diagnostic_rows


def test_intersection_curb_return_edge_reports_corner_source_validation() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="corridorroad-v1",
        intersection_model_id="intersections:corner-source-validation",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:corner-source-validation",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=["region:main-control"],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="leg:main",
                        leg_role="primary_before",
                        alignment_ref="alignment:main",
                        intersection_id="intersection:corner-source-validation",
                        profile_ref="profile:main",
                        centerline3d_ref="centerline:main",
                        region_ref="region:main-control",
                        approach_station_start=0.0,
                        approach_station_end=50.0,
                    ),
                    IntersectionLegRow(
                        leg_id="leg:side",
                        leg_role="side_approach",
                        alignment_ref="alignment:side",
                        intersection_id="intersection:corner-source-validation",
                        profile_ref="profile:side",
                        centerline3d_ref="centerline:side",
                        region_ref="region:side-control",
                        approach_station_start=0.0,
                        approach_station_end=35.0,
                    ),
                ],
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="control-area:main",
                intersection_id="intersection:corner-source-validation",
                alignment_ref="alignment:main",
                station_ranges=[(0.0, 50.0)],
                control_region_refs=["region:main-control"],
            )
        ],
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:accepted",
                intersection_id="intersection:corner-source-validation",
                source_method="manual",
                approval_status="locked",
                primary_alignment_ref="alignment:main",
                primary_station=25.0,
                secondary_station_refs={"alignment:side": 12.5},
                point_x=25.0,
                point_y=0.0,
                tolerance=0.01,
            )
        ],
        corner_rows=[
            IntersectionCornerRow(
                corner_id="corner:unknown-source",
                intersection_id="intersection:corner-source-validation",
                from_leg_ref="leg:main",
                to_leg_ref="leg:side",
                side="",
                curb_return_policy_ref="curb-return:other",
                source_method="mesh_repaired",
                approval_status="auto_accepted",
            )
        ],
        curb_return_policy_rows=[
            IntersectionCurbReturnPolicyRow(
                policy_id="curb-return:corner-source-validation",
                intersection_id="intersection:corner-source-validation",
                radius=10.0,
                approach_leg_refs=["leg:main", "leg:side"],
                corner_refs=["corner:unknown-source"],
            )
        ],
    )

    service = IntersectionEvaluationService()
    topology = service.evaluate_topology(model)
    edge_network = service.evaluate_edge_network(model, topology)

    curb_rows = [row for row in edge_network.edge_rows if row.edge_family == "curb_return"]

    assert curb_rows
    corner_edge = curb_rows[0]
    assert corner_edge.source_corner_ref == "corner:unknown-source"
    assert edge_network.status == "error"
    assert corner_edge.source_status == "error"
    assert corner_edge.status == "error"
    assert "source_corner_method_unknown" in corner_edge.source_diagnostic_rows
    assert "source_corner_approval_status_unknown" in corner_edge.source_diagnostic_rows
    assert "source_corner_approval_pending" in corner_edge.source_diagnostic_rows
    assert "source_corner_control_area_ref_missing" in corner_edge.source_diagnostic_rows
    assert "source_corner_side_ref_missing" in corner_edge.source_diagnostic_rows
    assert "source_corner_curb_return_policy_ref_mismatch" in corner_edge.source_diagnostic_rows
    assert "warning:source_corner_method_unknown:corner:unknown-source:mesh_repaired" in edge_network.diagnostic_rows
    assert "warning:source_corner_approval_status_unknown:corner:unknown-source:auto_accepted" in edge_network.diagnostic_rows
    assert (
        "error:source_corner_curb_return_policy_ref_mismatch:"
        "corner:unknown-source:curb-return:other:curb-return:corner-source-validation"
        in edge_network.diagnostic_rows
    )


def test_intersection_edge_network_rows_report_source_policy_status() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="corridorroad-v1",
        intersection_model_id="intersections:edge-source-status",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:edge-source-status",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=["region:main"],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="intersection:edge-source-status:leg:01",
                        leg_role="primary_control",
                        alignment_ref="alignment:main",
                        intersection_id="intersection:edge-source-status",
                        region_ref="region:main",
                        approach_station_start=10.0,
                        approach_station_end=40.0,
                        edge_policy_refs=["edge-policy:intersection:edge-source-status:missing"],
                    )
                ],
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="intersection:edge-source-status:control-area:01",
                intersection_id="intersection:edge-source-status",
                alignment_ref="alignment:main",
                station_ranges=[(10.0, 40.0)],
                control_region_refs=["region:main"],
            )
        ],
    )

    edge_network = IntersectionEvaluationService().evaluate_edge_network(model)
    surface_zones = IntersectionEvaluationService().evaluate_surface_zones(model, edge_network)
    unresolved_rows = [row for row in edge_network.edge_rows if row.source_policy_ref.endswith(":missing")]
    warning_zones = [row for row in surface_zones.zone_rows if row.source_status == "warning"]

    assert unresolved_rows
    assert unresolved_rows[0].source_status == "warning"
    assert "source_edge_policy_ref_unresolved" in unresolved_rows[0].source_diagnostic_rows
    assert unresolved_rows[0].status == "warning"
    assert "warning:edge_network_policy_ref_unresolved:edge-policy:intersection:edge-source-status:missing" in edge_network.diagnostic_rows
    assert warning_zones
    assert any("source_edge_policy_ref_unresolved" in item for row in warning_zones for item in row.source_diagnostic_rows)


def test_intersection_edge_network_reports_unknown_edge_family_source_policy() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="corridorroad-v1",
        intersection_model_id="intersections:edge-family-source-validation",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:edge-family-source-validation",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=["region:main"],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="leg:main",
                        leg_role="primary_control",
                        alignment_ref="alignment:main",
                        intersection_id="intersection:edge-family-source-validation",
                        profile_ref="profile:main",
                        centerline3d_ref="centerline:main",
                        region_ref="region:main",
                        approach_station_start=10.0,
                        approach_station_end=40.0,
                        edge_policy_refs=["edge-policy:unknown-family"],
                    )
                ],
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="control-area:main",
                intersection_id="intersection:edge-family-source-validation",
                alignment_ref="alignment:main",
                station_ranges=[(10.0, 40.0)],
                control_region_refs=["region:main"],
            )
        ],
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:accepted",
                intersection_id="intersection:edge-family-source-validation",
                source_method="manual",
                approval_status="locked",
                primary_alignment_ref="alignment:main",
                primary_station=25.0,
                secondary_station_refs={"alignment:side": 12.5},
                point_x=25.0,
                point_y=0.0,
                tolerance=0.01,
            )
        ],
        edge_policy_rows=[
            IntersectionEdgePolicyRow(
                policy_id="edge-policy:unknown-family",
                intersection_id="intersection:edge-family-source-validation",
                leg_ref="leg:main",
                edge_role="pavement_edge",
                side="right",
                edge_family_intent="mesh_patch",
                source_method="mesh_repaired",
                approval_status="auto_accepted",
                source_policy_ref="",
                subassembly_kind="side_slope",
            )
        ],
    )

    service = IntersectionEvaluationService()
    topology = service.evaluate_topology(model)
    edge_network = service.evaluate_edge_network(model, topology)
    rows = [row for row in edge_network.edge_rows if row.source_policy_ref == "edge-policy:unknown-family"]

    assert rows
    edge = rows[0]
    assert edge.source_status == "warning"
    assert edge.status == "warning"
    assert "source_edge_family_intent_unknown" in edge.source_diagnostic_rows
    assert "source_edge_family_method_unknown" in edge.source_diagnostic_rows
    assert "source_edge_family_approval_status_unknown" in edge.source_diagnostic_rows
    assert "source_edge_family_approval_pending" in edge.source_diagnostic_rows
    assert "warning:source_edge_family_intent_unknown:edge-policy:unknown-family:mesh_patch" in edge_network.diagnostic_rows
    assert "warning:source_edge_family_method_unknown:edge-policy:unknown-family:mesh_repaired" in edge_network.diagnostic_rows
    assert "warning:source_edge_family_approval_status_unknown:edge-policy:unknown-family:auto_accepted" in edge_network.diagnostic_rows


def test_intersection_edge_network_marks_subassembly_edge_family_lineage_breaks_as_error() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="corridorroad-v1",
        intersection_model_id="intersections:edge-family-blocking-source",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:edge-family-blocking-source",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=["region:main"],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="leg:main",
                        leg_role="primary_control",
                        alignment_ref="alignment:main",
                        intersection_id="intersection:edge-family-blocking-source",
                        profile_ref="profile:main",
                        centerline3d_ref="centerline:main",
                        region_ref="region:main",
                        approach_station_start=10.0,
                        approach_station_end=40.0,
                        edge_policy_refs=["edge-policy:blocking-subassembly"],
                    )
                ],
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="control-area:main",
                intersection_id="intersection:edge-family-blocking-source",
                alignment_ref="alignment:main",
                station_ranges=[(10.0, 40.0)],
                control_region_refs=["region:main"],
            )
        ],
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:accepted",
                intersection_id="intersection:edge-family-blocking-source",
                source_method="manual",
                approval_status="locked",
                primary_alignment_ref="alignment:main",
                primary_station=25.0,
                secondary_station_refs={"alignment:side": 12.5},
                point_x=25.0,
                point_y=0.0,
                tolerance=0.01,
            )
        ],
        edge_policy_rows=[
            IntersectionEdgePolicyRow(
                policy_id="edge-policy:blocking-subassembly",
                intersection_id="intersection:edge-family-blocking-source",
                leg_ref="leg:main",
                edge_role="pavement_edge",
                side="right",
                edge_family_intent="lane",
                source_method="subassembly_bridge",
                approval_status="locked",
                source_policy_ref="",
                subassembly_kind="side_slope",
            )
        ],
    )

    edge_network = IntersectionEvaluationService().evaluate_edge_network(model)
    edge = [row for row in edge_network.edge_rows if row.source_policy_ref == "edge-policy:blocking-subassembly"][0]

    assert edge_network.status == "error"
    assert edge.source_status == "error"
    assert edge.status == "error"
    assert "source_edge_family_source_policy_ref_missing" in edge.source_diagnostic_rows
    assert "source_edge_family_subassembly_kind_mismatch" in edge.source_diagnostic_rows
    assert "error:source_edge_family_source_policy_ref_missing:edge-policy:blocking-subassembly" in edge_network.diagnostic_rows
    assert (
        "error:source_edge_family_subassembly_kind_mismatch:edge-policy:blocking-subassembly:side_slope:lane"
        in edge_network.diagnostic_rows
    )


def test_intersection_lane_connection_lineage_reports_edge_family_subassembly_mismatch() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="corridorroad-v1",
        intersection_model_id="intersections:edge-family-lineage-validation",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:edge-family-lineage-validation",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=["region:main"],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="leg:main",
                        leg_role="primary_control",
                        alignment_ref="alignment:main",
                        intersection_id="intersection:edge-family-lineage-validation",
                        profile_ref="profile:main",
                        centerline3d_ref="centerline:main",
                        region_ref="region:main",
                        approach_station_start=10.0,
                        approach_station_end=40.0,
                        edge_policy_refs=["edge-policy:lane-mismatch"],
                    ),
                    IntersectionLegRow(
                        leg_id="leg:side",
                        leg_role="side_approach",
                        alignment_ref="alignment:side",
                        intersection_id="intersection:edge-family-lineage-validation",
                        profile_ref="profile:side",
                        centerline3d_ref="centerline:side",
                        region_ref="region:side",
                        approach_station_start=0.0,
                        approach_station_end=25.0,
                        edge_policy_refs=["edge-policy:lane-mismatch"],
                    ),
                ],
            )
        ],
        lane_connection_rows=[
            IntersectionLaneConnectionRow(
                connection_id="lane-connection:mismatch",
                intersection_id="intersection:edge-family-lineage-validation",
                from_leg_ref="leg:main",
                to_leg_ref="leg:side",
                from_edge_policy_ref="edge-policy:lane-mismatch",
                to_edge_policy_ref="edge-policy:lane-mismatch",
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="control-area:main",
                intersection_id="intersection:edge-family-lineage-validation",
                alignment_ref="alignment:main",
                station_ranges=[(10.0, 40.0)],
                control_region_refs=["region:main"],
            )
        ],
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:accepted",
                intersection_id="intersection:edge-family-lineage-validation",
                source_method="manual",
                approval_status="locked",
                primary_alignment_ref="alignment:main",
                primary_station=25.0,
                secondary_station_refs={"alignment:side": 12.5},
                point_x=25.0,
                point_y=0.0,
                tolerance=0.01,
            )
        ],
        edge_policy_rows=[
            IntersectionEdgePolicyRow(
                policy_id="edge-policy:lane-mismatch",
                intersection_id="intersection:edge-family-lineage-validation",
                leg_ref="leg:main",
                edge_role="pavement_edge",
                side="right",
                edge_family_intent="lane",
                source_method="subassembly_bridge",
                approval_status="accepted",
                source_policy_ref="",
                subassembly_kind="side_slope",
            )
        ],
    )
    topology = IntersectionEvaluationService().evaluate_topology(model)

    assert topology.lane_connection_rows
    row = topology.lane_connection_rows[0]
    assert row.source_status == "error"
    assert row.status == "error"
    assert row.from_edge_source_status == "error"
    assert row.to_edge_source_status == "error"
    assert row.edge_handoff_status == "incomplete"
    assert "from_edge:source_edge_family_source_policy_ref_missing" in row.source_diagnostic_rows
    assert "from_edge:source_edge_family_subassembly_kind_mismatch" in row.source_diagnostic_rows
    assert "to_edge:source_edge_family_source_policy_ref_missing" in row.source_diagnostic_rows
    assert "to_edge:source_edge_family_subassembly_kind_mismatch" in row.source_diagnostic_rows


def test_intersection_lane_connection_result_reports_unknown_source_method_status_and_missing_edge_refs() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="corridorroad-v1",
        intersection_model_id="intersections:lane-connection-source-validation",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:lane-connection-source-validation",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                control_region_refs=["region:main"],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="leg:main",
                        leg_role="primary_control",
                        alignment_ref="alignment:main",
                        intersection_id="intersection:lane-connection-source-validation",
                        profile_ref="profile:main",
                        centerline3d_ref="centerline:main",
                        region_ref="region:main",
                        approach_station_start=10.0,
                        approach_station_end=40.0,
                    ),
                    IntersectionLegRow(
                        leg_id="leg:side",
                        leg_role="side_approach",
                        alignment_ref="alignment:side",
                        intersection_id="intersection:lane-connection-source-validation",
                        profile_ref="profile:side",
                        centerline3d_ref="centerline:side",
                        region_ref="region:side",
                        approach_station_start=0.0,
                        approach_station_end=25.0,
                    ),
                ],
            )
        ],
        lane_connection_rows=[
            IntersectionLaneConnectionRow(
                connection_id="lane-connection:unknown-source",
                intersection_id="intersection:lane-connection-source-validation",
                movement_type="mesh_patch",
                from_leg_ref="leg:main",
                to_leg_ref="leg:side",
                source_method="mesh_repaired",
                approval_status="auto_accepted",
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="control-area:main",
                intersection_id="intersection:lane-connection-source-validation",
                alignment_ref="alignment:main",
                station_ranges=[(10.0, 40.0)],
                control_region_refs=["region:main"],
            )
        ],
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:accepted",
                intersection_id="intersection:lane-connection-source-validation",
                source_method="manual",
                approval_status="locked",
                primary_alignment_ref="alignment:main",
                primary_station=25.0,
                secondary_station_refs={"alignment:side": 12.5},
                point_x=25.0,
                point_y=0.0,
                tolerance=0.01,
            )
        ],
    )

    topology = IntersectionEvaluationService().evaluate_topology(model)

    assert topology.status == "error"
    assert topology.lane_connection_count == 1
    row = topology.lane_connection_rows[0]
    assert row.source_method == "mesh_repaired"
    assert row.approval_status == "auto_accepted"
    assert row.movement_type == "mesh_patch"
    assert row.source_status == "error"
    assert row.status == "error"
    assert row.movement_lineage_status == "incomplete"
    assert row.leg_handoff_status == "review_required"
    assert row.edge_handoff_status == "missing"
    assert row.handoff_target == "intersection-source-stage:lane_connections:lane-connection-unknown-source"
    assert "source_lane_connection_movement_type_unknown" in row.source_diagnostic_rows
    assert "source_lane_connection_method_unknown" in row.source_diagnostic_rows
    assert "source_lane_connection_approval_status_unknown" in row.source_diagnostic_rows
    assert "source_lane_connection_approval_pending" in row.source_diagnostic_rows
    assert "source_lane_connection_from_edge_policy_missing" in row.source_diagnostic_rows
    assert "source_lane_connection_to_edge_policy_missing" in row.source_diagnostic_rows
    assert "warning:source_lane_connection_movement_type_unknown:lane-connection:unknown-source:mesh_patch" in topology.diagnostic_rows
    assert "warning:source_lane_connection_method_unknown:lane-connection:unknown-source:mesh_repaired" in topology.diagnostic_rows
    assert "warning:source_lane_connection_approval_status_unknown:lane-connection:unknown-source:auto_accepted" in topology.diagnostic_rows
    assert "error:source_lane_connection_from_edge_policy_missing:lane-connection:unknown-source" in topology.diagnostic_rows
    assert "error:source_lane_connection_to_edge_policy_missing:lane-connection:unknown-source" in topology.diagnostic_rows


def test_intersection_preset_options_are_reflected_in_edge_network_preview() -> None:
    doc = App.newDocument("CRV1IntersectionPresetPreviewOptions")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")

        model, _control_region_count, detection = build_preset_source_intersection_model(
            doc,
            preset_label="T Intersection - Basic",
            design_vehicle="bus_or_small_truck",
            radius=18.0,
            control_length=36.0,
            grading_policy="keep_primary_crown",
            drainage_mode="outside_gutter",
        )
        assert {row.design_vehicle_ref for row in model.arm_policy_rows} == {"bus_or_small_truck"}
        assert {round(float(row.radius), 3) for row in model.curb_return_policy_rows} == {18.0}
        assert model.curb_return_policy_rows[0].corner_refs == [row.corner_id for row in model.corner_rows]
        assert model.grading_policy_rows[0].mode == "keep_primary_crown"
        assert model.drainage_policy_rows[0].capture_mode == "outside_gutter"
        assert model.control_areas
    finally:
        App.closeDocument(doc.Name)


def test_intersection_preset_sources_route_to_intersections_tree_folder() -> None:
    doc = App.newDocument("CRV1IntersectionPresetTreeRouting")
    try:
        project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(project)
        tree = ensure_project_tree(project, include_references=False)

        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")

        labels = {
            str(getattr(obj, "Label", "") or "")
            for obj in list(getattr(tree[V1_TREE_INTERSECTIONS], "Group", []) or [])
        }
        assert any(label.startswith("Intersections") for label in labels)
        assert "Intersection Main Road FG Profile" in labels
        assert "Intersection Main Road Stations" in labels
        assert "Intersection Side Road FG Profile" in labels
        assert "Intersection Side Road Stations" in labels
        assert "Intersection Preset Superelevation" in labels
        assert "Intersection Preset Drainage" in labels
    finally:
        App.closeDocument(doc.Name)


def test_intersection_preset_tree_cleanup_routes_existing_root_leftovers() -> None:
    doc = App.newDocument("CRV1IntersectionPresetRootCleanup")
    try:
        project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(project)
        tree = ensure_project_tree(project, include_references=False)
        leftovers = []
        for name, label in [
            ("LegacyIntersectionProfile", "Intersection Main Road FG Profile"),
            ("LegacyIntersectionStations", "Intersection Main Road Stations"),
            ("LegacyIntersectionModel", "Intersections001"),
            ("LegacyIntersectionSuperelevation", "Intersection Preset Superelevation"),
            ("LegacyIntersectionDrainage", "Intersection Preset Drainage"),
        ]:
            obj = doc.addObject("App::FeaturePython", name)
            obj.Label = label
            leftovers.append(obj)
        leftovers[2].addProperty("App::PropertyString", "CRRecordKind", "CorridorRoad", "")
        leftovers[2].CRRecordKind = "v1_intersection_model"
        leftovers[3].addProperty("App::PropertyString", "CRRecordKind", "CorridorRoad", "")
        leftovers[3].addProperty("App::PropertyString", "SuperelevationKind", "CorridorRoad", "")
        leftovers[3].CRRecordKind = "v1_superelevation_source"
        leftovers[3].SuperelevationKind = "intersection_superelevation_handoff"
        leftovers[4].addProperty("App::PropertyString", "CRRecordKind", "CorridorRoad", "")
        leftovers[4].addProperty("App::PropertyString", "DrainageModelId", "CorridorRoad", "")
        leftovers[4].CRRecordKind = "v1_drainage_model"
        leftovers[4].DrainageModelId = "drainage:intersection-preset-t-intersection"
        _route_intersection_preset_objects(doc, project=project)

        intersection_names = {
            str(getattr(obj, "Name", "") or "")
            for obj in list(getattr(tree[V1_TREE_INTERSECTIONS], "Group", []) or [])
        }
        root_names = {str(getattr(obj, "Name", "") or "") for obj in list(getattr(doc, "RootObjects", []) or [])}
        for obj in leftovers:
            assert obj.Name in intersection_names
            assert obj.Name not in root_names
    finally:
        App.closeDocument(doc.Name)


def test_intersection_preset_sources_find_parametric_road_project_by_label() -> None:
    doc = App.newDocument("CRV1IntersectionPresetLabelProjectRouting")
    try:
        project = doc.addObject("App::DocumentObjectGroup", "ParametricRoadProject")
        project.Label = "Parametric Road Project"
        tree = ensure_project_tree(project, include_references=False)

        assert find_project(doc) == project

        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")

        root_labels = {str(getattr(obj, "Label", "") or "") for obj in list(getattr(doc, "RootObjects", []) or [])}
        intersection_labels = {
            str(getattr(obj, "Label", "") or "")
            for obj in list(getattr(tree[V1_TREE_INTERSECTIONS], "Group", []) or [])
        }
        for label in {
            "Intersection Main Road FG Profile",
            "Intersection Main Road Stations",
            "Intersection Side Road FG Profile",
            "Intersection Side Road Stations",
            "Intersection Preset Superelevation",
            "Intersection Preset Drainage",
        }:
            assert label in intersection_labels
            assert label not in root_labels
        assert any(label.startswith("Intersections") for label in intersection_labels)
    finally:
        App.closeDocument(doc.Name)


def test_intersection_preset_existing_alignment_mode_stores_model_object() -> None:
    doc = App.newDocument("CRV1IntersectionPresetExistingAlignmentObject")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        model = to_intersection_model(find_v1_intersection_model(doc))
        primary_ref = model.intersection_rows[0].primary_alignment_ref
        secondary_ref = model.intersection_rows[0].secondary_alignment_refs[0]

        obj, control_region_count = create_intersection_from_existing_alignments(
            doc,
            preset_label="T Intersection - Basic",
            primary_alignment_ref=primary_ref,
            secondary_alignment_ref=secondary_ref,
        )
        stored = to_intersection_model(obj)

        assert control_region_count >= 2
        assert stored is not None
        assert stored.intersection_rows[0].source_mode == "use_existing_alignments"
        assert stored.intersection_rows[0].primary_alignment_ref == primary_ref
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_preset_edge_network_exposes_roundabout_family_rows() -> None:
    doc = App.newDocument("CRV1RoundaboutPresetEdgeNetwork")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane")
        model = to_intersection_model(find_v1_intersection_model(doc))
        edge_network = IntersectionEvaluationService().evaluate_edge_network(model)
        roundabout_edges = [row for row in edge_network.edge_rows if row.edge_family == "roundabout"]
        roles = {row.edge_role for row in roundabout_edges}

        assert model is not None
        assert edge_network.intersection_kind == "roundabout"
        assert edge_network.status == "warning"
        assert "warning:roundabout_edge_network_first_slice_source_only" in edge_network.diagnostic_rows
        assert "central_island_edge" in roles
        assert "circulatory_outer_edge" in roles
        assert "entry_exit_edge" in roles
        assert len([row for row in roundabout_edges if row.edge_role == "entry_exit_edge"]) >= 2
        assert all(row.contact_station_refs for row in roundabout_edges)
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_preset_records_explicit_source_policy_rows() -> None:
    doc = App.newDocument("CRV1RoundaboutExplicitPolicy")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        model = to_intersection_model(find_v1_intersection_model(doc))
        policy_rows = [
            row
            for row in model.edge_policy_rows
            if row.edge_family_intent == "roundabout"
        ]
        policy_by_rule = {row.offset_rule: row for row in policy_rows}
        edge_network = IntersectionEvaluationService().evaluate_edge_network(model)
        roundabout_edges = [row for row in edge_network.edge_rows if row.edge_family == "roundabout"]
        central = next(row for row in roundabout_edges if row.edge_role == "central_island_edge")
        outer = next(row for row in roundabout_edges if row.edge_role == "circulatory_outer_edge")

        assert model is not None
        assert "roundabout_central_island_radius" in policy_by_rule
        assert "roundabout_circulatory_outer_radius" in policy_by_rule
        assert "roundabout_outer_apron_width" in policy_by_rule
        assert "roundabout_slope_face_width" in policy_by_rule
        assert "roundabout_approach_connector_length" in policy_by_rule
        assert "roundabout_splitter_island_length" not in policy_by_rule
        assert "roundabout_splitter_island_width" not in policy_by_rule
        assert "roundabout_subgrade_depth" in policy_by_rule
        assert round(policy_by_rule["roundabout_circulatory_outer_radius"].offset_value, 3) == 20.0
        assert policy_by_rule["roundabout_slope_face_width"].offset_value > 0.0
        assert round(policy_by_rule["roundabout_subgrade_depth"].offset_value, 3) == 0.3
        assert round(outer.radius, 3) == 20.0
        assert round(central.radius, 3) == 9.0
        assert all(row.source_status == "accepted" for row in roundabout_edges)
        assert all("roundabout_source_policy" in row.notes for row in roundabout_edges)
    finally:
        App.closeDocument(doc.Name)


def test_intersection_surface_zones_expose_priority_order() -> None:
    doc = App.newDocument("CRV1IntersectionSurfaceZonePriority")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        model = to_intersection_model(find_v1_intersection_model(doc))
        surface_zones = IntersectionEvaluationService().evaluate_surface_zones(model)
        priorities = {row.design_zone_role: row.surface_priority for row in surface_zones.zone_rows}

        assert model is not None
        assert surface_zones.zone_count == len(surface_zones.zone_rows)
        assert surface_zones.central_pavement_zone_count == 1
        assert surface_zones.curb_return_zone_count >= 1
        assert priorities["central_pavement"] > priorities["curb_return_pavement"]
        assert priorities["curb_return_pavement"] > priorities["main_pavement"]
        assert priorities["main_pavement"] > priorities["exterior_slope_face"]
        assert all(row.surface_priority > 0 for row in surface_zones.zone_rows)
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_preset_surface_zones_expose_roundabout_contracts() -> None:
    doc = App.newDocument("CRV1RoundaboutPresetSurfaceZones")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane")
        model = to_intersection_model(find_v1_intersection_model(doc))
        surface_zones = IntersectionEvaluationService().evaluate_surface_zones(model)
        roundabout_zones = [row for row in surface_zones.zone_rows if row.zone_family == "roundabout"]
        roles = {row.design_zone_role for row in roundabout_zones}

        assert model is not None
        assert surface_zones.intersection_kind == "roundabout"
        assert surface_zones.roundabout_zone_count == len(roundabout_zones)
        assert "roundabout_central_island" in roles
        assert "roundabout_circulatory_lane" in roles
        assert "roundabout_truck_apron" in roles
        assert "roundabout_outer_shoulder" in roles
        assert "roundabout_entry_exit_connector" in roles
        assert "roundabout_splitter_island" not in roles
        assert "roundabout_outer_shoulder_policy_missing" in " ".join(
            " ".join(row.diagnostic_rows) for row in roundabout_zones
        )
        assert all(row.surface_priority > 0 for row in roundabout_zones)
        assert all(row.vertical_policy_ref for row in roundabout_zones)
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_boundary_loops_expose_closed_island_and_circulatory_loops() -> None:
    doc = App.newDocument("CRV1RoundaboutBoundaryLoops")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        model = to_intersection_model(find_v1_intersection_model(doc))
        service = IntersectionEvaluationService()
        edge_network = service.evaluate_edge_network(model)
        surface_zones = service.evaluate_surface_zones(model, edge_network)
        boundary_loops = service.evaluate_boundary_loops(model, surface_zones, edge_network)
        loops_by_role = {row.loop_role: row for row in boundary_loops.loop_rows}

        assert model is not None
        assert boundary_loops.intersection_kind == "roundabout"
        assert boundary_loops.status in {"ready", "warning"}
        assert "roundabout_central_island_boundary" in loops_by_role
        assert "roundabout_circulatory_outer_boundary" in loops_by_role
        assert loops_by_role["roundabout_central_island_boundary"].closed is True
        assert loops_by_role["roundabout_circulatory_outer_boundary"].closed is True
        assert loops_by_role["roundabout_central_island_boundary"].point_count == 32
        assert loops_by_role["roundabout_circulatory_outer_boundary"].point_count == 32
        assert loops_by_role["roundabout_circulatory_outer_boundary"].area_xy > loops_by_role["roundabout_central_island_boundary"].area_xy
        assert any("roundabout_boundary_loop_source=explicit_roundabout_policy" in row for row in boundary_loops.diagnostic_rows)
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_boundary_loops_include_entry_exit_connector_loops() -> None:
    doc = App.newDocument("CRV1RoundaboutConnectorBoundaryLoops")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        model = to_intersection_model(find_v1_intersection_model(doc))
        service = IntersectionEvaluationService()
        edge_network = service.evaluate_edge_network(model)
        surface_zones = service.evaluate_surface_zones(model, edge_network)
        boundary_loops = service.evaluate_boundary_loops(model, surface_zones, edge_network)
        connector_loops = [
            row
            for row in boundary_loops.loop_rows
            if row.loop_role == "roundabout_entry_exit_connector_boundary"
        ]

        assert model is not None
        assert len(connector_loops) >= 4
        assert all(row.closed for row in connector_loops)
        assert all(row.point_count == 4 for row in connector_loops)
        assert all(row.area_xy > 0.0 for row in connector_loops)
        assert all("roundabout_entry_exit_connector" in row.consumer_roles for row in connector_loops)
        assert not any("roundabout_entry_exit_surface" in row.consumer_roles for row in connector_loops)
        assert {
            token
            for row in connector_loops
            for token in ("primary-start", "primary-end", "secondary-start", "secondary-end")
            if token in row.loop_id
        } == {"primary-start", "primary-end", "secondary-start", "secondary-end"}
        assert all(
            any(str(ref).startswith("intersection-roundabout-approach-leg:") for ref in row.source_refs)
            for row in connector_loops
        )
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_boundary_loops_do_not_emit_splitter_island_contracts() -> None:
    doc = App.newDocument("CRV1RoundaboutNoSplitterBoundaryLoops")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        model = to_intersection_model(find_v1_intersection_model(doc))
        service = IntersectionEvaluationService()
        edge_network = service.evaluate_edge_network(model)
        surface_zones = service.evaluate_surface_zones(model, edge_network)
        boundary_loops = service.evaluate_boundary_loops(model, surface_zones, edge_network)
        splitter_loops = [
            row
            for row in boundary_loops.loop_rows
            if row.loop_role == "roundabout_splitter_island_boundary"
        ]

        assert model is not None
        assert splitter_loops == []
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_boundary_loops_include_ownership_and_clip_handoff_boundaries() -> None:
    doc = App.newDocument("CRV1RoundaboutOwnershipClipBoundaryLoops")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        model = to_intersection_model(find_v1_intersection_model(doc))
        service = IntersectionEvaluationService()
        edge_network = service.evaluate_edge_network(model)
        surface_zones = service.evaluate_surface_zones(model, edge_network)
        boundary_loops = service.evaluate_boundary_loops(model, surface_zones, edge_network)
        loops_by_role = {row.loop_role: row for row in boundary_loops.loop_rows}
        approach_clip_loops = [
            row for row in boundary_loops.loop_rows if row.loop_role == "roundabout_approach_clip_boundary"
        ]
        subgrade_clip_loops = [
            row for row in boundary_loops.loop_rows if row.loop_role == "roundabout_subgrade_clip_boundary"
        ]
        slope_handoff_loops = [
            row for row in boundary_loops.loop_rows if row.loop_role == "roundabout_slope_handoff_boundary"
        ]

        assert model is not None
        assert "roundabout_outer_ownership_boundary" in loops_by_role
        assert loops_by_role["roundabout_outer_ownership_boundary"].closed is True
        assert loops_by_role["roundabout_outer_ownership_boundary"].point_count == 32
        assert (
            loops_by_role["roundabout_outer_ownership_boundary"].area_xy
            > loops_by_role["roundabout_circulatory_outer_boundary"].area_xy
        )
        assert len(approach_clip_loops) >= 4
        assert len(subgrade_clip_loops) == len(approach_clip_loops)
        assert len(slope_handoff_loops) == len(approach_clip_loops)
        assert all(row.closed for row in [*approach_clip_loops, *subgrade_clip_loops, *slope_handoff_loops])
        assert all(row.point_count == 4 for row in [*approach_clip_loops, *subgrade_clip_loops, *slope_handoff_loops])
        assert all(row.area_xy > 0.0 for row in [*approach_clip_loops, *subgrade_clip_loops, *slope_handoff_loops])
        assert all("design_surface" in row.consumer_roles for row in approach_clip_loops)
        assert all("subgrade_surface" in row.consumer_roles for row in subgrade_clip_loops)
        assert all("slope_face_surface" in row.consumer_roles for row in slope_handoff_loops)
        assert all(
            any(str(ref).startswith("intersection-roundabout-approach-leg:") for ref in row.source_refs)
            for row in [*approach_clip_loops, *subgrade_clip_loops, *slope_handoff_loops]
        )
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_intersection_surface_preview_builds_annular_ring() -> None:
    doc = App.newDocument("CRV1RoundaboutAnnularSurfacePreview")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )

        assert preview is not None
        assert preview.IntersectionKind == "roundabout"
        assert preview.PatchTriangulationMode == "roundabout_annular_strip"
        assert preview.PatchSurfaceBoundaryStrategy == "roundabout_authoritative_boundary_loops"
        assert int(preview.PatchStructuredStripCount) == 32
        assert int(preview.TriangleCount) == 64
        assert int(preview.VertexCount) == 64
        assert int(preview.PatchBoundaryPointCount) == 64
        assert int(preview.SharedBreaklineBoundaryLoopRefCount) == 64
        assert int(preview.SharedBreaklineBoundaryLoopConstraintSegmentCount) == 64
        assert int(preview.SharedBreaklineBoundaryLoopConstraintEdgeCount) == 64
        assert preview.SharedBreaklineBoundaryLoopConstraintRoleSummary == (
            "roundabout_circulatory_to_apron=32, roundabout_island_to_circulatory=32"
        )
        assert preview.SharedBreaklineAuditStatus == "ready"
        assert int(preview.SharedBreaklineMissingConsumerCount) == 0
        assert int(preview.SharedBreaklineGeometryMismatchCount) == 0
        assert int(preview.SharedBreaklineMeshMismatchCount) == 0
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_ordinary_surface_guardrail_clips_ownership_intrusion() -> None:
    doc = App.newDocument("CRV1RoundaboutOwnershipGuardrail")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        design_preview = create_corridor_design_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        subgrade_preview = create_corridor_subgrade_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        slope_preview = create_corridor_daylight_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )

        assert design_preview is not None
        assert subgrade_preview is not None
        assert slope_preview is not None
        assert design_preview.RoundaboutOwnershipIntrusionStatus == "ready"
        assert subgrade_preview.RoundaboutOwnershipIntrusionStatus == "ready"
        assert slope_preview.RoundaboutOwnershipIntrusionStatus == "ready"
        assert design_preview.RoundaboutOwnershipClipStatus == "ready"
        assert subgrade_preview.RoundaboutOwnershipClipStatus == "ready"
        assert slope_preview.RoundaboutOwnershipClipStatus == "ready"
        assert design_preview.RoundaboutClipBoundaryStatus == "ready"
        assert subgrade_preview.RoundaboutClipBoundaryStatus == "ready"
        assert slope_preview.RoundaboutClipBoundaryStatus == "ready"
        assert design_preview.RoundaboutClipBoundaryRole == "roundabout_approach_clip_boundary"
        assert subgrade_preview.RoundaboutClipBoundaryRole == "roundabout_subgrade_clip_boundary"
        assert slope_preview.RoundaboutClipBoundaryRole == "roundabout_slope_handoff_boundary"
        assert design_preview.RoundaboutActualClipBoundaryRoles == "roundabout_outer_ownership_boundary"
        assert subgrade_preview.RoundaboutActualClipBoundaryRoles == "roundabout_outer_ownership_boundary"
        assert slope_preview.RoundaboutActualClipBoundaryRoles == "roundabout_outer_ownership_boundary"
        expected_approach_roles = {
            "primary-start",
            "primary-end",
            "secondary-start",
            "secondary-end",
        }
        assert int(design_preview.RoundaboutClipBoundaryApproachLegCount) == 4
        assert int(subgrade_preview.RoundaboutClipBoundaryApproachLegCount) == 4
        assert int(slope_preview.RoundaboutClipBoundaryApproachLegCount) == 4
        assert set(design_preview.RoundaboutClipBoundaryApproachLegRoles) == expected_approach_roles
        assert set(subgrade_preview.RoundaboutClipBoundaryApproachLegRoles) == expected_approach_roles
        assert set(slope_preview.RoundaboutClipBoundaryApproachLegRoles) == expected_approach_roles
        assert design_preview.RoundaboutClipBoundaryApproachLegSource == "roundabout_approach_leg_contract"
        assert subgrade_preview.RoundaboutClipBoundaryApproachLegSource == "roundabout_approach_leg_contract"
        assert slope_preview.RoundaboutClipBoundaryApproachLegSource == "roundabout_approach_leg_contract"
        assert int(design_preview.RoundaboutClipBoundaryLoopCount) > 0
        assert int(subgrade_preview.RoundaboutClipBoundaryLoopCount) > 0
        assert int(slope_preview.RoundaboutClipBoundaryLoopCount) > 0
        assert int(design_preview.RoundaboutClipBoundarySegmentCount) > 0
        assert int(subgrade_preview.RoundaboutClipBoundarySegmentCount) > 0
        assert int(slope_preview.RoundaboutClipBoundarySegmentCount) > 0
        assert int(design_preview.RoundaboutOwnershipIntrusionTriangleCount) == 0
        assert int(subgrade_preview.RoundaboutOwnershipIntrusionTriangleCount) == 0
        assert int(slope_preview.RoundaboutOwnershipIntrusionTriangleCount) == 0
        assert int(design_preview.RoundaboutOwnershipClippedTriangleCount) > 0
        assert int(subgrade_preview.RoundaboutOwnershipClippedTriangleCount) > 0
        assert int(slope_preview.RoundaboutOwnershipClippedTriangleCount) > 0
        assert design_preview.RoundaboutOwnershipClipMode == "roundabout_boundary_loop"
        assert design_preview.RoundaboutOwnershipClipFallbackReason == ""
        assert int(design_preview.RoundaboutClipBoundaryCrossingCandidateCount) == int(
            design_preview.RoundaboutOwnershipClippedTriangleCount
        )
        assert int(design_preview.RoundaboutClipExactSupported) == 1
        assert int(design_preview.RoundaboutClipExactCandidateCount) > 0
        assert int(design_preview.RoundaboutClipExactGeneratedTriangleCount) > 0
        assert int(design_preview.RoundaboutClipExactFallbackCount) >= 0
        assert slope_preview.RoundaboutOwnershipClipMode == "roundabout_boundary_loop"
        assert slope_preview.RoundaboutOwnershipClipFallbackReason == ""
        assert int(slope_preview.RoundaboutClipBoundaryCrossingCandidateCount) == int(
            slope_preview.RoundaboutOwnershipClippedTriangleCount
        )
        assert int(slope_preview.RoundaboutClipExactSupported) == 1
        assert int(slope_preview.RoundaboutClipExactCandidateCount) > 0
        assert int(slope_preview.RoundaboutClipExactGeneratedTriangleCount) > 0
        assert int(slope_preview.RoundaboutClipExactFallbackCount) >= 0
        for preview in (subgrade_preview,):
            assert preview.RoundaboutOwnershipClipMode == "roundabout_boundary_loop"
            assert preview.RoundaboutOwnershipClipFallbackReason == ""
            assert int(preview.RoundaboutClipBoundaryCrossingCandidateCount) == int(
                preview.RoundaboutOwnershipClippedTriangleCount
            )
            assert int(preview.RoundaboutClipExactSupported) == 1
            assert int(preview.RoundaboutClipExactCandidateCount) > 0
            assert int(preview.RoundaboutClipExactGeneratedTriangleCount) > 0
            assert int(preview.RoundaboutClipExactFallbackCount) >= 0
            assert list(getattr(preview, "RoundaboutClipBoundaryLoopBBoxes", []) or [])
            assert list(getattr(preview, "RoundaboutClipBoundaryLoopAreas", []) or [])
            assert "centroid_inside=" in preview.RoundaboutOwnershipClipReasonSummary
            assert (
                int(preview.RoundaboutOwnershipClipCentroidInsideCount)
                + int(preview.RoundaboutOwnershipClipVertexInsideCount)
                + int(preview.RoundaboutOwnershipClipEdgeCrossesCount)
                + int(preview.RoundaboutOwnershipClipCenterInsideTriangleCount)
                == int(preview.RoundaboutOwnershipClippedTriangleCount)
            )
        assert (
            int(design_preview.RoundaboutOwnershipClipCentroidInsideCount)
            + int(design_preview.RoundaboutOwnershipClipVertexInsideCount)
            + int(design_preview.RoundaboutOwnershipClipEdgeCrossesCount)
            + int(design_preview.RoundaboutOwnershipClipCenterInsideTriangleCount)
            == int(design_preview.RoundaboutOwnershipClippedTriangleCount)
        )

        rows = corridor_build_review_rows(doc)
        design_row = next(row for row in rows if row["role"] == "design")
        subgrade_row = next(row for row in rows if row["role"] == "subgrade")
        slope_row = next(row for row in rows if row["role"] == "daylight")
        assert "roundabout_ownership=ready" in str(design_row["notes"])
        assert "roundabout_ownership=ready" in str(subgrade_row["notes"])
        assert "roundabout_ownership=ready" in str(slope_row["notes"])
        assert "roundabout_ownership=warning" not in str(design_row["notes"])
        assert "roundabout_ownership=warning" not in str(subgrade_row["notes"])
        assert "roundabout_ownership=warning" not in str(slope_row["notes"])
        assert "clipped_triangles=" in str(design_row["notes"])
        assert "clipped_triangles=" in str(subgrade_row["notes"])
        assert "clipped_triangles=" in str(slope_row["notes"])
        assert "clip_boundary=roundabout_approach_clip_boundary:ready" in str(design_row["notes"])
        assert "clip_boundary=roundabout_subgrade_clip_boundary:ready" in str(subgrade_row["notes"])
        assert "clip_boundary=roundabout_slope_handoff_boundary:ready" in str(slope_row["notes"])

        audit_rows = corridor_shared_breakline_audit_rows(doc)
        audit_by_role = {str(row.get("role", "") or ""): row for row in audit_rows}
        assert audit_by_role["design"]["roundabout_clip_boundary_status"] == "ready"
        assert audit_by_role["design"]["roundabout_clip_boundary_role"] == "roundabout_approach_clip_boundary"
        assert audit_by_role["design"]["roundabout_actual_clip_boundary_roles"] == ["roundabout_outer_ownership_boundary"]
        assert audit_by_role["subgrade"]["roundabout_clip_boundary_status"] == "ready"
        assert audit_by_role["subgrade"]["roundabout_clip_boundary_role"] == "roundabout_subgrade_clip_boundary"
        assert audit_by_role["subgrade"]["roundabout_actual_clip_boundary_roles"] == ["roundabout_outer_ownership_boundary"]
        assert audit_by_role["daylight"]["roundabout_clip_boundary_status"] == "ready"
        assert audit_by_role["daylight"]["roundabout_clip_boundary_role"] == "roundabout_slope_handoff_boundary"
        assert audit_by_role["daylight"]["roundabout_actual_clip_boundary_roles"] == ["roundabout_outer_ownership_boundary"]
        assert "roundabout_clip_boundary=roundabout_approach_clip_boundary:ready" in str(audit_by_role["design"]["notes"])
        assert "actual_clip_roles=roundabout_outer_ownership_boundary" in str(audit_by_role["design"]["notes"])
        assert "roundabout_clip_boundary=roundabout_subgrade_clip_boundary:ready" in str(audit_by_role["subgrade"]["notes"])
        assert "actual_clip_roles=roundabout_outer_ownership_boundary" in str(audit_by_role["subgrade"]["notes"])
        assert "roundabout_clip_boundary=roundabout_slope_handoff_boundary:ready" in str(audit_by_role["daylight"]["notes"])
        assert "actual_clip_roles=roundabout_outer_ownership_boundary" in str(audit_by_role["daylight"]["notes"])
        assert "approach_legs=4" in str(audit_by_role["design"]["notes"])
        assert "approach_legs=4" in str(audit_by_role["subgrade"]["notes"])
        assert "approach_legs=4" in str(audit_by_role["daylight"]["notes"])
        assert "primary-start" in str(audit_by_role["design"]["notes"])
        assert "secondary-end" in str(audit_by_role["daylight"]["notes"])
        assert "mode=roundabout_boundary_loop" in str(audit_by_role["design"]["notes"])
        assert "mode=roundabout_boundary_loop" in str(audit_by_role["subgrade"]["notes"])
        assert "mode=roundabout_boundary_loop" in str(audit_by_role["daylight"]["notes"])
        assert _breakline_audit_surface_row_focuses_source_only(audit_by_role["design"]) is True
        assert _breakline_audit_surface_row_focuses_source_only(audit_by_role["subgrade"]) is True
        assert _breakline_audit_surface_row_focuses_source_only(audit_by_role["daylight"]) is True
        internal_rows = shared_breakline_audit_display_rows(audit_rows, include_internal=True)
        diagnostic_detail_roles = {
            str(row.get("role", "") or ""): row
            for row in internal_rows
            if str(row.get("row_kind", "") or "") == "roundabout_clip_boundary_diagnostic"
        }
        assert diagnostic_detail_roles["design"]["status"] == "ready"
        assert diagnostic_detail_roles["subgrade"]["status"] == "ready"
        assert diagnostic_detail_roles["daylight"]["status"] == "ready"
        assert "approach_legs=4" in str(diagnostic_detail_roles["design"]["notes"])
        assert "approach_legs=4" in str(diagnostic_detail_roles["subgrade"]["notes"])
        assert "approach_legs=4" in str(diagnostic_detail_roles["daylight"]["notes"])
        assert "diagnostic_only=yes" in str(diagnostic_detail_roles["design"]["notes"])
        assert "diagnostic_only=yes" in str(diagnostic_detail_roles["subgrade"]["notes"])
        assert "diagnostic_only=yes" in str(diagnostic_detail_roles["daylight"]["notes"])
        assert "actual_clip_roles=roundabout_outer_ownership_boundary" in str(diagnostic_detail_roles["design"]["role_summary"])
        assert "actual_clip_roles=roundabout_outer_ownership_boundary" in str(diagnostic_detail_roles["daylight"]["role_summary"])
        assert diagnostic_detail_roles["design"]["graph_edge_refs"] == []
        assert diagnostic_detail_roles["subgrade"]["graph_edge_refs"] == []
        assert diagnostic_detail_roles["daylight"]["graph_edge_refs"] == []
        assert diagnostic_detail_roles["design"]["breakline_role_filter"] == ""
        assert diagnostic_detail_roles["subgrade"]["breakline_role_filter"] == ""
        assert diagnostic_detail_roles["daylight"]["breakline_role_filter"] == ""
        assert "not used for ordinary surface clipping" in str(diagnostic_detail_roles["design"]["recommended_action"])
        clip_leg_rows = [
            row
            for row in internal_rows
            if str(row.get("row_kind", "") or "") == "roundabout_clip_boundary_leg"
        ]
        assert clip_leg_rows == []

        prerequisite = corridor_intersection_patch_prerequisite_result(doc)
        intersection_model = to_intersection_model(find_v1_intersection_model(doc))
        shared_result = corridor_intersection_shared_breakline_result(
            applied,
            prerequisite=prerequisite,
            intersection_model=intersection_model,
        )
        rows_by_role = {}
        for row in list(getattr(shared_result, "breakline_rows", []) or []):
            rows_by_role.setdefault(str(getattr(row, "breakline_role", "") or ""), []).append(row)
        expected_clip_roles = {
            "roundabout_approach_clip_to_design_surface": "design_surface",
            "roundabout_subgrade_to_approach_subgrade": "subgrade_surface",
            "roundabout_slope_to_corridor_slope_face": "slope_face_surface",
        }
        for role, consumer in expected_clip_roles.items():
            assert rows_by_role.get(role)
            assert all(consumer in tuple(getattr(row, "consumer_refs", ()) or ()) for row in rows_by_role[role])
            assert all("intersection_surface" not in tuple(getattr(row, "consumer_refs", ()) or ()) for row in rows_by_role[role])
            assert all(str(getattr(row, "handoff_target", "") or "") == "roundabout_ordinary_surface_clip" for row in rows_by_role[role])
        assert all(
            "roundabout_subgrade_surface" in tuple(getattr(row, "consumer_refs", ()) or ())
            for row in rows_by_role["roundabout_subgrade_to_approach_subgrade"]
        )
        diagnostics = ";".join(str(value) for value in list(getattr(shared_result, "diagnostic_rows", []) or []))
        assert "roundabout_clip_boundary_shared_breaklines:" in diagnostics
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_lane_shoulder_guided_review_clips_to_approach_boundary() -> None:
    doc = App.newDocument("CRV1RoundaboutLaneShoulderGuidedReviewClip")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)

        lane_preview = focus_corridor_build_guided_review_step(doc, "subassembly_kind:lane")
        assert lane_preview is not None
        assert lane_preview.Label == "Applied Section Highlight - Lane"
        assert lane_preview.DisplayMode == "section_surface_strips"
        assert lane_preview.RoundaboutClipBoundaryRole == "roundabout_approach_clip_boundary"
        assert lane_preview.RoundaboutReportedBoundaryRole == "roundabout_approach_clip_boundary"
        assert lane_preview.RoundaboutActualClipBoundaryRole == "roundabout_outer_ownership_boundary"
        assert lane_preview.RoundaboutActualClipBoundaryRoles == "roundabout_outer_ownership_boundary"
        assert lane_preview.RoundaboutReviewClipMode == "actual_ownership_boundary"
        assert lane_preview.RoundaboutClipBoundaryStatus == "ready"
        assert lane_preview.RoundaboutClipFallbackReason == ""
        assert int(lane_preview.RoundaboutClipBoundaryLoopCount) > 0
        assert int(lane_preview.SkippedRoundaboutSectionCount) == 0
        assert int(lane_preview.SkippedRoundaboutStripTriangleCount) == 0
        assert int(lane_preview.SurfacePatchCount) > 0

        shoulder_preview = focus_corridor_build_guided_review_step(doc, "subassembly_kind:shoulder")
        assert shoulder_preview is not None
        assert shoulder_preview.Label == "Applied Section Highlight - Shoulder"
        assert shoulder_preview.DisplayMode == "section_surface_strips"
        assert shoulder_preview.RoundaboutClipBoundaryRole == "roundabout_approach_clip_boundary"
        assert shoulder_preview.RoundaboutReportedBoundaryRole == "roundabout_approach_clip_boundary"
        assert shoulder_preview.RoundaboutActualClipBoundaryRole == "roundabout_outer_ownership_boundary"
        assert shoulder_preview.RoundaboutActualClipBoundaryRoles == "roundabout_outer_ownership_boundary"
        assert shoulder_preview.RoundaboutReviewClipMode == "actual_ownership_boundary"
        assert shoulder_preview.RoundaboutClipBoundaryStatus == "ready"
        assert shoulder_preview.RoundaboutClipFallbackReason == ""
        assert int(shoulder_preview.RoundaboutClipBoundaryLoopCount) > 0
        assert int(shoulder_preview.SkippedRoundaboutSectionCount) == 0
        assert int(shoulder_preview.SkippedRoundaboutStripTriangleCount) == 0
        assert int(shoulder_preview.SurfacePatchCount) > 0
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_applied_sections_show_all_preview_is_not_clipping_source() -> None:
    doc = App.newDocument("CRV1RoundaboutAppliedPreviewNotClipSource")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)

        preview = show_all_applied_sections_preview_object(doc, applied)
        assert preview is not None
        assert preview.Name == "V1AppliedSectionsShowAllPreview"
        assert preview.CRRecordKind == "v1_applied_sections_show_all_preview"
        assert preview.V1ObjectType == "V1AppliedSectionsShowAllPreview"

        hidden_count = hide_applied_sections_preview_objects(doc)
        assert hidden_count >= 0
        assert doc.getObject("V1AppliedSectionsShowAllPreview") is preview
        if getattr(preview, "ViewObject", None) is not None:
            assert preview.ViewObject.Visibility is False

        apply_v1_corridor_model(document=doc, project=project)

        audit_rows = corridor_shared_breakline_audit_rows(doc)
        audit_by_role = {str(row.get("role", "") or ""): row for row in audit_rows}
        for role in ("design", "subgrade", "daylight"):
            assert audit_by_role[role]["roundabout_actual_clip_boundary_roles"] == ["roundabout_outer_ownership_boundary"]

        forbidden_tokens = {
            "V1AppliedSectionsShowAllPreview",
            "Applied Sections Preview - All",
            "v1_applied_sections_show_all_preview",
        }
        for row in audit_rows:
            searchable = " ".join(
                str(value)
                for value in (
                    row.get("notes", ""),
                    row.get("role_summary", ""),
                    row.get("material_summary", ""),
                    row.get("roundabout_clip_boundary_loop_refs", ""),
                    row.get("roundabout_clip_boundary_segment_refs", ""),
                    row.get("graph_edge_refs", ""),
                )
            )
            assert not any(token in searchable for token in forbidden_tokens), searchable

        internal_rows = shared_breakline_audit_display_rows(audit_rows, include_internal=True)
        diagnostic_rows = [
            row
            for row in internal_rows
            if str(row.get("row_kind", "") or "") == "roundabout_clip_boundary_diagnostic"
        ]
        assert diagnostic_rows
        assert all(str(row.get("breakline_role_filter", "") or "") == "" for row in diagnostic_rows)
        assert all(not list(row.get("graph_edge_refs", []) or []) for row in diagnostic_rows)
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_side_slope_guided_review_clips_to_slope_handoff_boundary() -> None:
    doc = App.newDocument("CRV1RoundaboutSideSlopeGuidedReviewClip")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)

        side_slope_preview = focus_corridor_build_guided_review_step(doc, "subassembly_kind:side_slope")

        assert side_slope_preview is not None
        assert side_slope_preview.Label == "Applied Section Highlight - Side Slope"
        assert side_slope_preview.DisplayMode == "section_breaklines"
        assert side_slope_preview.RoundaboutClipBoundaryRole == "roundabout_slope_handoff_boundary"
        assert side_slope_preview.RoundaboutReportedBoundaryRole == "roundabout_slope_handoff_boundary"
        assert side_slope_preview.RoundaboutActualClipBoundaryRole == "roundabout_outer_ownership_boundary"
        assert side_slope_preview.RoundaboutActualClipBoundaryRoles == "roundabout_outer_ownership_boundary"
        assert side_slope_preview.RoundaboutReviewClipMode == "source_breaklines_with_actual_boundary_metadata"
        assert side_slope_preview.RoundaboutClipBoundaryStatus == "ready"
        assert side_slope_preview.RoundaboutClipFallbackReason == ""
        assert int(side_slope_preview.RoundaboutClipBoundaryLoopCount) > 0
        assert int(side_slope_preview.SideCount) > 0
        assert int(side_slope_preview.DegenerateSideCount) > 0
        assert int(side_slope_preview.SkippedRoundaboutSectionCount) == 0
        assert int(side_slope_preview.SkippedRoundaboutSideCount) == 0
        assert int(side_slope_preview.RoundaboutClipBoundaryOnly) == 0
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_entry_exit_connector_surface_preview_is_disabled_for_generalization() -> None:
    doc = App.newDocument("CRV1RoundaboutEntryExitConnectorSurfaceDisabled")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        assert preview is not None
        assert doc.getObject("V1CorridorRoundaboutEntryExitSurfacePreview") is None
        assert doc.getObject("V1CorridorRoundaboutEntryExitConnectorSurfacePreview") is None
        assert preview.RoundaboutEntryExitSurfaceStatus == "not_applicable"
        assert preview.RoundaboutEntryExitSurfacePreviewRef == ""
        assert int(preview.RoundaboutEntryExitSurfaceTriangleCount) == 0
        assert preview.RoundaboutEntryExitConnectorSurfaceStatus == "not_applicable"
        assert preview.RoundaboutEntryExitConnectorSurfacePreviewRef == ""
        assert int(preview.RoundaboutEntryExitConnectorSurfaceTriangleCount) == 0
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_splitter_island_surface_preview_is_removed_for_generalization() -> None:
    doc = App.newDocument("CRV1RoundaboutNoSplitterIslandSurfacePreview")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )

        assert preview is not None
        assert doc.getObject("V1CorridorRoundaboutSplitterIslandSurfacePreview") is None
        assert preview.RoundaboutSplitterIslandSurfaceStatus == "not_applicable"
        assert preview.RoundaboutSplitterIslandSurfacePreviewRef == ""
        assert int(preview.RoundaboutSplitterIslandSurfaceTriangleCount) == 0
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_subgrade_surface_preview_uses_subgrade_clip_boundary_contracts() -> None:
    doc = App.newDocument("CRV1RoundaboutSubgradeSurfacePreview")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        subgrade = doc.getObject("V1CorridorRoundaboutSubgradeSurfacePreview")

        assert preview is not None
        assert subgrade is not None
        assert preview.RoundaboutSubgradeSurfaceStatus == "ready"
        assert preview.RoundaboutSubgradeSurfacePreviewRef == subgrade.Name
        assert int(subgrade.RoundaboutSubgradeBoundarySegmentCount) == 32
        assert int(subgrade.RoundaboutSubgradeClipLoopCount) > 0
        assert int(subgrade.RoundaboutSubgradeTriangleCount) == 32
        assert int(subgrade.TriangleCount) >= int(subgrade.RoundaboutSubgradeTriangleCount)
        assert subgrade.RoundaboutSubgradeGeometrySource == "roundabout_outer_ownership_boundary_fan"
        assert subgrade.RoundaboutSubgradeDepthSource == "roundabout_subgrade_depth_policy"
        assert subgrade.RoundaboutSubgradeApproachLegSource == "roundabout_approach_leg_contract"
        assert int(subgrade.RoundaboutSubgradeApproachLegCount) == 4
        assert set(subgrade.RoundaboutSubgradeApproachLegRoles) == {
            "primary-start",
            "primary-end",
            "secondary-start",
            "secondary-end",
        }
        subgrade_boundary_refs = list(subgrade.RoundaboutSubgradeBoundaryRefs)
        assert sum(1 for ref in subgrade_boundary_refs if ":subgrade-clip-" in str(ref)) == 4
        assert subgrade.SharedBreaklineAuditStatus == "ready"
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_generic_tie_slope_surface_preview_is_disabled_for_generalization() -> None:
    doc = App.newDocument("CRV1RoundaboutGenericTieSlopeDisabled")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        doc.addObject("Part::Feature", "V1CorridorIntersectionSlopeFaceSurfacePreview")
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        assert preview is not None
        assert preview.IntersectionKind == "roundabout"
        assert doc.getObject("V1CorridorIntersectionTieSlopeSurfacePreview") is None
        assert doc.getObject("V1CorridorIntersectionSlopeFaceSurfacePreview") is None
        assert preview.IntersectionTieSlopeSurfaceStatus == "not_applicable"
        assert preview.IntersectionTieSlopeSurfacePreviewRef == ""
        assert int(preview.IntersectionTieSlopeSurfaceTriangleCount) == 0
        assert preview.IntersectionTieSlopeStatus == "not_applicable"
        assert any(
            "roundabout_generic_intersection_tie_slope_disabled" in row
            for row in list(preview.IntersectionTieSlopeDiagnostics)
        )
        assert preview.IntersectionSlopeFaceSurfaceStatus == "not_applicable"
        assert preview.IntersectionSlopeFaceSurfacePreviewRef == ""
        assert int(preview.IntersectionSlopeFaceSurfaceTriangleCount) == 0
        assert "Roundabout Slope Face Surface" in preview.IntersectionSlopeFaceSurfaceRecommendedAction
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_slope_face_surface_preview_uses_exposed_outer_boundary_segments() -> None:
    doc = App.newDocument("CRV1RoundaboutSlopeFaceSurfacePreview")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        slope_face = doc.getObject("V1CorridorRoundaboutSlopeFaceSurfacePreview")
        apron = doc.getObject("V1CorridorRoundaboutApronSurfacePreview")
        subgrade = doc.getObject("V1CorridorRoundaboutSubgradeSurfacePreview")

        assert preview is not None
        assert apron is not None
        assert subgrade is not None
        assert slope_face is not None
        assert preview.IntersectionKind == "roundabout"
        assert preview.RoundaboutApronSurfaceStatus == "ready"
        assert preview.RoundaboutApronSurfacePreviewRef == apron.Name
        assert int(apron.RoundaboutApronBoundarySegmentCount) == 32
        assert int(apron.RoundaboutApronTriangleCount) == 64
        assert apron.RoundaboutApronGeometrySource == "roundabout_circulatory_outer_to_ownership_boundary"
        assert apron.SharedBreaklineAuditStatus == "ready"
        assert preview.RoundaboutSlopeFaceSurfaceStatus == "ready"
        assert preview.RoundaboutSlopeFaceSurfacePreviewRef == slope_face.Name
        assert doc.getObject("V1CorridorIntersectionSlopeFaceSurfacePreview") is None
        assert preview.IntersectionSlopeFaceSurfaceStatus == "not_applicable"
        assert preview.IntersectionSlopeFaceSurfacePreviewRef == ""
        assert int(slope_face.RoundaboutSlopeFaceBoundarySegmentCount) == 16
        assert int(slope_face.RoundaboutSlopeFaceSkippedConnectorSegmentCount) == 16
        assert int(slope_face.RoundaboutSlopeFaceSuppressionSpanCount) == 16
        assert int(slope_face.RoundaboutSlopeFaceHandoffLoopCount) == 4
        assert int(slope_face.RoundaboutSlopeFaceHandoffApproachLegCount) == 4
        assert slope_face.RoundaboutSlopeFaceHandoffApproachLegSource == "roundabout_approach_leg_contract"
        assert set(slope_face.RoundaboutSlopeFaceHandoffApproachLegRoles) == {
            "primary-start",
            "primary-end",
            "secondary-start",
            "secondary-end",
        }
        assert int(slope_face.RoundaboutSlopeFaceTriangleCount) == 32
        assert int(slope_face.TriangleCount) >= 32
        assert slope_face.RoundaboutSlopeFaceWidthSource == "roundabout_slope_face_width_policy"
        assert slope_face.RoundaboutSlopeFaceGeometrySource == "roundabout_outer_ownership_boundary_exposed_segments"
        assert slope_face.RoundaboutSlopeFaceSuppressionSource == "roundabout_connector_and_handoff_boundary_angle_spans"
        assert slope_face.SharedBreaklineAuditStatus == "ready"
        assert int(slope_face.SharedBreaklineGeometryMismatchCount) == 0
        assert int(slope_face.SharedBreaklineMeshMismatchCount) == 0
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_shared_boundary_graph_uses_semantic_roles_and_highlights_locally() -> None:
    doc = App.newDocument("CRV1RoundaboutSharedBoundaryGraphSemanticRoles")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )

        assert preview is not None
        graph_rows = [str(row or "") for row in list(preview.IntersectionSharedBoundaryGraphAuditRows)]
        assert any("|roundabout_island_to_circulatory|" in row for row in graph_rows)
        assert any("|roundabout_circulatory_to_apron|" in row for row in graph_rows)
        assert any("|roundabout_apron_to_slope_face|" in row for row in graph_rows)
        assert any("|roundabout_entry_exit_connector_boundary|" in row for row in graph_rows)
        assert not any("|roundabout_splitter_island_boundary|" in row for row in graph_rows)
        expected_consumers = {
            "roundabout_subgrade_to_approach_subgrade": ("subgrade_surface", "roundabout_subgrade_surface"),
            "roundabout_slope_to_corridor_slope_face": ("slope_face_surface",),
        }
        for role, consumers in expected_consumers.items():
            matching_rows = [row for row in graph_rows if f"|{role}|" in row]
            assert matching_rows
            for consumer in consumers:
                assert any(f"|{consumer}" in row or f",{consumer}" in row for row in matching_rows)
        assert not any("|roundabout_circulatory_to_slope_face|" in row for row in graph_rows)
        assert not any("|roundabout_circulatory_to_entry_exit|" in row for row in graph_rows)
        assert not any("|roundabout_entry_exit_to_design_surface|" in row for row in graph_rows)
        assert not any("|roundabout_connector_to_tie_slope|" in row for row in graph_rows)

        rows = corridor_intersection_contract_review_rows(doc, include_internal=True)
        for role in (
            "roundabout_apron_to_slope_face",
            "roundabout_entry_exit_connector_boundary",
            "roundabout_subgrade_to_approach_subgrade",
            "roundabout_slope_to_corridor_slope_face",
        ):
            target_index = next(
                index
                for index, row in enumerate(rows)
                if row.get("contract_family") == "shared_boundary_graph"
                and role in str(row.get("role", ""))
            )
            highlight = focus_corridor_intersection_contract_review_row(doc, target_index, include_internal=True)

            assert highlight is not None
            assert highlight.HighlightGeometrySource == "intersection_shared_boundary_graph_result"
            assert int(highlight.HighlightedShapeCount) >= 1
            assert str(highlight.ContractFamily) == "shared_boundary_graph"
            assert "intersection-shared-boundary-graph:intersection:starter-roundabout" in ",".join(
                list(highlight.HighlightedRefs)
            )
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_build_parametric_outputs_route_to_intersections_tree() -> None:
    doc = App.newDocument("CRV1RoundaboutOutputTreeRouting")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        tree = ensure_project_tree(project, include_references=False)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        slope_face = doc.getObject("V1CorridorRoundaboutSlopeFaceSurfacePreview")
        apron = doc.getObject("V1CorridorRoundaboutApronSurfacePreview")
        subgrade = doc.getObject("V1CorridorRoundaboutSubgradeSurfacePreview")

        assert preview is not None
        assert doc.getObject("V1CorridorRoundaboutEntryExitSurfacePreview") is None
        assert doc.getObject("V1CorridorRoundaboutEntryExitConnectorSurfacePreview") is None
        assert doc.getObject("V1CorridorIntersectionTieSlopeSurfacePreview") is None
        assert apron is not None
        assert slope_face is not None
        assert doc.getObject("V1CorridorRoundaboutSplitterIslandSurfacePreview") is None
        intersection_children = set(list(getattr(tree[V1_TREE_INTERSECTIONS], "Group", []) or []))
        root_objects = set(list(getattr(doc, "RootObjects", []) or []))
        assert apron in intersection_children
        assert apron not in root_objects
        assert subgrade in intersection_children
        assert subgrade not in root_objects
        assert slope_face in intersection_children
        assert slope_face not in root_objects
        assert "intersection:starter-roundabout" in str(getattr(apron, "Label", "") or "")
        assert "intersection:starter-roundabout" in str(getattr(subgrade, "Label", "") or "")
        assert "intersection:starter-roundabout" in str(getattr(slope_face, "Label", "") or "")
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_visibility_group_controls_production_outputs() -> None:
    doc = App.newDocument("CRV1RoundaboutVisibilityGroup")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)
        create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )

        production_names = (
            "V1CorridorIntersectionSurfacePreview",
            "V1CorridorRoundaboutApronSurfacePreview",
            "V1CorridorRoundaboutSubgradeSurfacePreview",
            "V1CorridorRoundaboutSlopeFaceSurfacePreview",
        )
        production_objects = [doc.getObject(name) for name in production_names]
        assert all(obj is not None for obj in production_objects)

        changed = set_corridor_build_visibility_group(doc, "intersection", False)
        assert changed >= len(production_objects)

        changed = set_corridor_build_visibility_group(doc, "intersection", True)
        assert changed >= len(production_objects)
        group_by_id = {str(row["group_id"]): row for row in corridor_build_visibility_groups()}
        intersection_group_names = set(group_by_id["intersection"]["object_names"])
        for name in production_names[1:]:
            assert name in intersection_group_names
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_results_tab_exposes_production_output_rows() -> None:
    doc = App.newDocument("CRV1RoundaboutResultsTabRows")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )

        results = corridor_build_review_rows(doc)
        result_titles = {str(row.get("result", "") or "") for row in results}
        rows_by_role = {str(row.get("role", "") or ""): row for row in results}

        assert "Roundabout Circulatory Surface" in result_titles
        assert "Roundabout Entry/Exit Connector Surface" not in result_titles
        assert "Roundabout Splitter Island Surface" not in result_titles
        assert "Roundabout Apron Surface" in result_titles
        assert "Roundabout Subgrade Surface" in result_titles
        assert "Roundabout Entry Exit Surface" not in result_titles
        assert "Roundabout Tie Slope Surface" not in result_titles
        assert "Intersection Tie Slope Surface" not in result_titles
        assert "Roundabout Breakline Readiness" in result_titles
        assert rows_by_role["roundabout_circulatory"]["status"] == "ready"
        assert rows_by_role["roundabout_apron"]["status"] == "ready"
        assert rows_by_role["roundabout_subgrade"]["status"] == "ready"
        assert "roundabout annular circulatory surface" in str(rows_by_role["roundabout_circulatory"]["notes"])
        assert "roundabout annular apron surface" in str(rows_by_role["roundabout_apron"]["notes"])
        assert "roundabout dedicated subgrade surface" in str(rows_by_role["roundabout_subgrade"]["notes"])
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_intersections_tab_hides_internal_contract_rows_by_default() -> None:
    doc = App.newDocument("CRV1RoundaboutIntersectionsTabProductionRows")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)
        create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )

        default_rows = corridor_intersection_contract_review_rows(doc)
        internal_rows = corridor_intersection_contract_review_rows(doc, include_internal=True)
        default_families = {str(row.get("contract_family", "") or "") for row in default_rows}
        internal_families = {str(row.get("contract_family", "") or "") for row in internal_rows}

        assert "drainage_hint" not in default_families
        assert "shared_boundary_graph" not in default_families
        assert "slope_face_cell" not in default_families
        assert "intersection_tie_slope_window" not in default_families
        assert "intersection_tie_slope_window" not in internal_families
        assert "drainage_hint" in internal_families
        assert any(str(row.get("contract_family", "") or "") == "boundary_loop" for row in default_rows)
        assert any(str(row.get("contract_family", "") or "") == "roundabout_boundary_readiness" for row in default_rows)
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_intersections_tab_exposes_boundary_readiness_row() -> None:
    doc = App.newDocument("CRV1RoundaboutBoundaryReadinessRow")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)

        rows = corridor_intersection_contract_review_rows(doc)
        readiness_rows = [
            row
            for row in rows
            if str(row.get("contract_family", "") or "") == "roundabout_boundary_readiness"
        ]

        assert len(readiness_rows) == 1
        row = readiness_rows[0]
        assert row["status"] == "ready"
        assert row["source_status"] == "accepted"
        assert row["role"] == "approach_clip_and_slope_handoff"
        assert row["output_path"] == "roundabout_boundary_readiness"
        assert "intersection-roundabout-approach-legs:" in str(row["source_refs"])
        assert "intersection-boundary-loop:" in str(row["boundary_refs"])
        notes = str(row["notes"])
        assert "approach_legs=4/4" in notes
        assert "primary_start" in notes
        assert "secondary_end" in notes
        assert "roundabout_approach_clip_boundary=4/4" in notes
        assert "roundabout_subgrade_clip_boundary=4/4" in notes
        assert "roundabout_slope_handoff_boundary=4/4" in notes
        assert "Roundabout ordinary-surface clip and slope handoff boundaries are ready." in notes
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_approach_leg_contract_splits_two_alignments_into_four_physical_approaches() -> None:
    doc = App.newDocument("CRV1RoundaboutApproachLegContract")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        model = to_intersection_model(find_v1_intersection_model(doc))
        service = IntersectionEvaluationService()
        topology = service.evaluate_topology(model)
        approach_legs = service.evaluate_roundabout_approach_legs(model, topology)

        assert approach_legs.status == "ready"
        assert approach_legs.intersection_kind == "roundabout"
        assert approach_legs.source_leg_count == 2
        assert approach_legs.approach_leg_count == 4
        assert approach_legs.accepted_approach_leg_count == 4
        assert approach_legs.alignment_count == 2
        assert {
            row.approach_role for row in approach_legs.approach_leg_rows
        } == {
            "primary_start",
            "primary_end",
            "secondary_start",
            "secondary_end",
        }
        assert {
            row.alignment_ref for row in approach_legs.approach_leg_rows
        } == {
            "alignment:intersection-primary",
            "alignment:intersection-secondary",
        }
        assert {
            row.approach_role: round(float(row.direction_angle_deg), 3)
            for row in approach_legs.approach_leg_rows
        } == {
            "primary_start": 180.0,
            "primary_end": 0.0,
            "secondary_start": 270.0,
            "secondary_end": 90.0,
        }
        assert any(
            "roundabout_approach_leg_contract_source=topology_leg_span_decomposition" in str(item)
            for item in approach_legs.diagnostic_rows
        )
        for row in approach_legs.approach_leg_rows:
            vx, vy = row.direction_vector_xy
            assert 0.999 <= (vx * vx + vy * vy) <= 1.001
            assert row.connector_boundary_role == "roundabout_entry_exit_connector_boundary"
            assert row.corridor_clip_boundary_role == "roundabout_approach_clip_boundary"
            assert row.subgrade_handoff_boundary_role == "roundabout_subgrade_clip_boundary"
            assert row.slope_handoff_boundary_role == "roundabout_slope_handoff_boundary"
            assert "roundabout_approach_clip_to_design_surface" in row.shared_breakline_roles
            assert "roundabout_slope_face_to_corridor_slope_face" in row.shared_breakline_roles
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_single_lane_full_smoke_validates_production_outputs() -> None:
    doc = App.newDocument("CRV1RoundaboutSingleLaneFullSmoke")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        tree = ensure_project_tree(project, include_references=False)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        design_preview = create_corridor_design_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        subgrade_preview = create_corridor_subgrade_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        slope_preview = create_corridor_daylight_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        intersection_preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )

        assert intersection_preview is not None
        assert intersection_preview.PatchTriangulationMode == "roundabout_annular_strip"
        assert int(intersection_preview.TriangleCount) > 0
        assert intersection_preview.IntersectionSharedBoundaryGraphStatus == "ready"
        assert int(intersection_preview.IntersectionSharedBoundaryGraphDuplicateEdgeCount) == 0
        assert int(intersection_preview.IntersectionSharedBoundaryGraphMissingConsumerCount) == 0

        for ordinary_preview in (design_preview, subgrade_preview, slope_preview):
            assert ordinary_preview is not None
            assert ordinary_preview.RoundaboutOwnershipIntrusionStatus == "ready"
            assert ordinary_preview.RoundaboutOwnershipClipStatus == "ready"
            assert int(ordinary_preview.RoundaboutOwnershipIntrusionTriangleCount) == 0
            assert int(ordinary_preview.RoundaboutOwnershipClippedTriangleCount) > 0

        production_names = (
            "V1CorridorIntersectionSurfacePreview",
            "V1CorridorRoundaboutApronSurfacePreview",
            "V1CorridorRoundaboutSubgradeSurfacePreview",
            "V1CorridorRoundaboutSlopeFaceSurfacePreview",
        )
        production_objects = [doc.getObject(name) for name in production_names]
        assert all(obj is not None for obj in production_objects)
        assert doc.getObject("V1CorridorRoundaboutEntryExitSurfacePreview") is None
        assert doc.getObject("V1CorridorRoundaboutEntryExitConnectorSurfacePreview") is None
        assert doc.getObject("V1CorridorIntersectionTieSlopeSurfacePreview") is None

        assert intersection_preview.RoundaboutEntryExitConnectorSurfaceStatus == "not_applicable"
        assert intersection_preview.RoundaboutEntryExitConnectorSurfacePreviewRef == ""
        assert int(intersection_preview.RoundaboutEntryExitConnectorSurfaceTriangleCount) == 0
        assert intersection_preview.RoundaboutSplitterIslandSurfaceStatus == "not_applicable"
        assert intersection_preview.RoundaboutSplitterIslandSurfacePreviewRef == ""
        assert int(intersection_preview.RoundaboutSplitterIslandSurfaceTriangleCount) == 0
        assert intersection_preview.RoundaboutApronSurfaceStatus == "ready"
        assert int(intersection_preview.RoundaboutApronSurfaceTriangleCount) > 0
        assert intersection_preview.RoundaboutSubgradeSurfaceStatus == "ready"
        assert int(intersection_preview.RoundaboutSubgradeSurfaceTriangleCount) > 0
        assert intersection_preview.RoundaboutSlopeFaceSurfaceStatus == "ready"
        assert int(intersection_preview.RoundaboutSlopeFaceSurfaceTriangleCount) > 0

        intersection_children = set(list(getattr(tree[V1_TREE_INTERSECTIONS], "Group", []) or []))
        root_objects = set(list(getattr(doc, "RootObjects", []) or []))
        for obj in production_objects[1:]:
            assert obj in intersection_children
            assert obj not in root_objects

        result_rows = corridor_build_review_rows(doc)
        rows_by_role = {str(row.get("role", "") or ""): row for row in result_rows}
        for role in (
            "roundabout_circulatory",
            "roundabout_apron",
            "roundabout_subgrade",
            "roundabout_breakline_readiness",
        ):
            assert rows_by_role[role]["status"] == "ready"

        audit_rows = corridor_shared_breakline_audit_rows(doc)
        audit_by_surface = {str(row.get("surface", "") or ""): row for row in audit_rows}
        assert audit_by_surface["Design Surface"]["status"] == "ready"
        assert audit_by_surface["Intersection Surface"]["status"] == "ready"
        assert audit_by_surface["Slope Face Surface"]["status"] == "ready"
        assert _breakline_audit_surface_row_focuses_source_only(audit_by_surface["Design Surface"]) is True
        assert _breakline_audit_surface_row_focuses_source_only(audit_by_surface["Slope Face Surface"]) is True

        internal_audit_rows = shared_breakline_audit_display_rows(audit_rows, include_internal=True)
        diagnostic_rows = [
            row
            for row in internal_audit_rows
            if str(row.get("row_kind", "") or "") == "roundabout_clip_boundary_diagnostic"
        ]
        assert len(diagnostic_rows) >= 3
        assert {
            str(row.get("status", "") or "")
            for row in diagnostic_rows
        } == {"ready"}
        assert all(str(row.get("breakline_role_filter", "") or "") == "" for row in diagnostic_rows)
        assert all(not list(row.get("graph_edge_refs", []) or []) for row in diagnostic_rows)
        assert all("diagnostic_only=yes" in str(row.get("notes", "") or "") for row in diagnostic_rows)
        assert any("primary-start" in str(row.get("role_summary", "") or "") for row in diagnostic_rows)
        assert any("secondary-end" in str(row.get("role_summary", "") or "") for row in diagnostic_rows)
        assert not [
            row
            for row in internal_audit_rows
            if str(row.get("row_kind", "") or "") == "roundabout_clip_boundary_leg"
        ]

        contract_rows = corridor_intersection_contract_review_rows(doc)
        contract_families = {str(row.get("contract_family", "") or "") for row in contract_rows}
        assert "edge_network" not in contract_families
        assert "surface_zone" not in contract_families
        assert "roundabout_boundary_readiness" in contract_families
    finally:
        App.closeDocument(doc.Name)


def test_intersection_grading_context_exposes_policy_and_crossfall_contracts() -> None:
    doc = App.newDocument("CRV1IntersectionGradingContext")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic", grading_policy="blend_primary_side")
        model = to_intersection_model(find_v1_intersection_model(doc))
        service = IntersectionEvaluationService()
        surface_zones = service.evaluate_surface_zones(model)
        grading_context = service.evaluate_grading_context(model, surface_zones)
        rows_by_zone = {row.zone_role: row for row in grading_context.context_rows}

        assert model is not None
        assert grading_context.status in {"ready", "warning"}
        assert grading_context.context_count == surface_zones.zone_count
        assert grading_context.intersection_override_count > 0
        assert rows_by_zone["central_pavement"].grading_mode == "blend_primary_side"
        assert rows_by_zone["central_pavement"].crossfall_context == "intersection_override"
        assert rows_by_zone["central_pavement"].crown_behavior == "blend_primary_side_crowns"
        assert rows_by_zone["central_pavement"].tie_in_rule == "blend_to_leg_profiles"
        assert rows_by_zone["central_pavement"].crossfall_transition == "linear"
        assert rows_by_zone["central_pavement"].low_point_strategy == "review_low_points"
        assert rows_by_zone["central_pavement"].source_status == "warning"
        assert "grading_policy_source_defaulted" in rows_by_zone["central_pavement"].source_diagnostic_rows
        assert rows_by_zone["exterior_slope_face"].crossfall_context == "normal_superelevation"
        assert rows_by_zone["central_pavement"].surface_priority > rows_by_zone["exterior_slope_face"].surface_priority
    finally:
        App.closeDocument(doc.Name)


def test_intersection_grading_context_reports_unknown_source_policy_values() -> None:
    doc = App.newDocument("CRV1IntersectionGradingContextSourceValidation")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic", grading_policy="blend_primary_side")
        model = to_intersection_model(find_v1_intersection_model(doc))
        assert model is not None
        policy_ref = model.grading_policy_rows[0].policy_id
        model.grading_policy_rows = [
            IntersectionGradingPolicyRow(
                policy_id=policy_ref,
                intersection_id=model.grading_policy_rows[0].intersection_id,
                mode="mesh_patch",
                target_crossfall_percent=0.0,
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                controlling_profile_ref="profile:main",
                crown_behavior="mesh_crown",
                tie_in_rule="mesh_tie",
                crossfall_transition="mesh_transition",
                low_point_strategy="mesh_low_point",
                source_method="mesh_repaired",
                approval_status="auto_accepted",
            )
        ]

        service = IntersectionEvaluationService()
        surface_zones = service.evaluate_surface_zones(model)
        grading_context = service.evaluate_grading_context(model, surface_zones)
        rows = [row for row in grading_context.context_rows if row.grading_policy_ref == policy_ref]

        assert rows
        row = rows[0]
        assert row.source_status == "warning"
        assert row.status == "warning"
        assert row.grading_mode == "mesh_patch"
        assert row.source_method == "mesh_repaired"
        assert row.approval_status == "auto_accepted"
        assert row.profile_handoff_status == "review_required"
        assert row.superelevation_handoff_status == "overridden"
        assert row.handoff_target.startswith("intersection-preview-stage:grading:")
        assert "source_grading_policy_mode_unknown" in row.source_diagnostic_rows
        assert "source_grading_policy_method_unknown" in row.source_diagnostic_rows
        assert "source_grading_policy_approval_status_unknown" in row.source_diagnostic_rows
        assert "source_grading_policy_approval_pending" in row.source_diagnostic_rows
        assert "source_grading_policy_crown_behavior_unknown" in row.source_diagnostic_rows
        assert "source_grading_policy_tie_in_rule_unknown" in row.source_diagnostic_rows
        assert "source_grading_policy_crossfall_transition_unknown" in row.source_diagnostic_rows
        assert "source_grading_policy_low_point_strategy_unknown" in row.source_diagnostic_rows
        assert any(item == f"warning:source_grading_policy_mode_unknown:{policy_ref}" for item in grading_context.diagnostic_rows)
        assert any(item == f"warning:source_grading_policy_method_unknown:{policy_ref}" for item in grading_context.diagnostic_rows)
        assert any(item == f"warning:source_grading_policy_approval_status_unknown:{policy_ref}" for item in grading_context.diagnostic_rows)
    finally:
        App.closeDocument(doc.Name)


def test_intersection_grading_context_marks_missing_override_profile_as_error() -> None:
    doc = App.newDocument("CRV1IntersectionGradingContextMissingProfile")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic", grading_policy="blend_primary_side")
        model = to_intersection_model(find_v1_intersection_model(doc))
        assert model is not None
        policy_ref = model.grading_policy_rows[0].policy_id
        model.grading_policy_rows = [
            IntersectionGradingPolicyRow(
                policy_id=policy_ref,
                intersection_id=model.grading_policy_rows[0].intersection_id,
                mode="blend_primary_side",
                target_crossfall_percent=0.0,
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                controlling_profile_ref="",
                crown_behavior="blend_primary_side_crowns",
                tie_in_rule="blend_to_leg_profiles",
                crossfall_transition="linear",
                low_point_strategy="review_low_points",
                source_method="manual",
                approval_status="locked",
            )
        ]

        service = IntersectionEvaluationService()
        surface_zones = service.evaluate_surface_zones(model)
        grading_context = service.evaluate_grading_context(model, surface_zones)
        rows = [row for row in grading_context.context_rows if row.grading_policy_ref == policy_ref]

        assert rows
        central = next(row for row in rows if row.crossfall_context == "intersection_override")
        assert grading_context.status == "warning"
        assert central.source_status == "error"
        assert central.status == "error"
        assert central.profile_lineage_status == "missing"
        assert central.profile_handoff_status == "blocked"
        assert central.vertical_handoff_status == "blocked"
        assert central.fallback_status == "none"
        assert central.handoff_target.startswith("intersection-preview-stage:grading:")
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_grading_context_uses_radial_crossfall_policy() -> None:
    doc = App.newDocument("CRV1RoundaboutGradingContext")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane")
        model = to_intersection_model(find_v1_intersection_model(doc))
        grading_context = IntersectionEvaluationService().evaluate_grading_context(model)
        roundabout_rows = [row for row in grading_context.context_rows if row.zone_role.startswith("roundabout_")]

        assert model is not None
        assert roundabout_rows
        assert all(row.grading_mode == "roundabout_radial_crossfall" for row in roundabout_rows)
        assert all(row.crossfall_context == "intersection_override" for row in roundabout_rows)
    finally:
        App.closeDocument(doc.Name)


def test_intersection_drainage_hints_include_grading_context_and_missing_coverage() -> None:
    doc = App.newDocument("CRV1IntersectionDrainageHints")
    try:
        create_intersection_preset_sources(
            doc,
            preset_label="T Intersection - Basic",
            grading_policy="blend_primary_side",
            drainage_mode="outside_gutter",
        )
        model = to_intersection_model(find_v1_intersection_model(doc))
        service = IntersectionEvaluationService()
        surface_zones = service.evaluate_surface_zones(model)
        grading_context = service.evaluate_grading_context(model, surface_zones)
        drainage_hints = service.evaluate_drainage_hints(model, surface_zones, grading_context)
        low_points = [row for row in drainage_hints.hint_rows if row.hint_kind == "low_point_candidate"]
        inlets = [row for row in drainage_hints.hint_rows if row.hint_kind == "inlet_recommendation"]
        outlets = [row for row in drainage_hints.hint_rows if row.hint_kind == "outlet_handoff"]

        assert model is not None
        assert drainage_hints.status == "warning"
        assert low_points
        assert inlets
        assert outlets
        assert drainage_hints.missing_coverage_count > 0
        assert all(row.drainage_mode == "outside_gutter" for row in drainage_hints.hint_rows)
        assert any(row.grading_context_ref for row in low_points)
        assert any(row.crossfall_context == "intersection_override" for row in low_points)
        assert any(row.drainage_intent_status == "hint_only" for row in low_points)
        assert any(row.source_lineage_status == "hint_only" for row in low_points)
        assert all(row.handoff_target.startswith("intersection-source-stage:drainage:") for row in drainage_hints.hint_rows)
        assert any(row.source_status == "warning" for row in low_points)
        assert any("source_drainage_policy_hint_only" in row.source_diagnostic_rows for row in low_points)
    finally:
        App.closeDocument(doc.Name)


def test_intersection_drainage_hints_report_unknown_source_policy_values() -> None:
    doc = App.newDocument("CRV1IntersectionDrainageSourceValidation")
    try:
        create_intersection_preset_sources(
            doc,
            preset_label="T Intersection - Basic",
            grading_policy="blend_primary_side",
            drainage_mode="outside_gutter",
        )
        model = to_intersection_model(find_v1_intersection_model(doc))
        assert model is not None
        policy_ref = model.drainage_policy_rows[0].policy_id
        model.drainage_policy_rows = [
            IntersectionDrainagePolicyRow(
                policy_id=policy_ref,
                intersection_id=model.drainage_policy_rows[0].intersection_id,
                capture_mode="mesh_gutter",
                intent_status="mesh_patch",
                source_method="mesh_repaired",
                approval_status="auto_accepted",
            )
        ]

        service = IntersectionEvaluationService()
        surface_zones = service.evaluate_surface_zones(model)
        grading_context = service.evaluate_grading_context(model, surface_zones)
        drainage_hints = service.evaluate_drainage_hints(model, surface_zones, grading_context)
        source_rows = [row for row in drainage_hints.hint_rows if row.source_drainage_policy_ref == policy_ref]

        assert drainage_hints.status == "warning"
        assert source_rows
        row = source_rows[0]
        assert row.drainage_mode == "mesh_gutter"
        assert row.drainage_intent_status == "mesh_patch"
        assert row.drainage_source_method == "mesh_repaired"
        assert row.drainage_approval_status == "auto_accepted"
        assert row.drainage_handoff_status == "review_required"
        assert row.drainage_source_scope == "review"
        assert row.source_lineage_status == "source_warning"
        assert row.handoff_target.startswith("intersection-source-stage:drainage:")
        assert row.source_status == "warning"
        assert "source_drainage_policy_capture_mode_unknown" in row.source_diagnostic_rows
        assert "source_drainage_policy_intent_status_unknown" in row.source_diagnostic_rows
        assert "source_drainage_policy_method_unknown" in row.source_diagnostic_rows
        assert "source_drainage_policy_approval_status_unknown" in row.source_diagnostic_rows
        assert "source_drainage_policy_approval_pending" in row.source_diagnostic_rows
        assert any(item == f"warning:source_drainage_policy_capture_mode_unknown:{policy_ref}" for item in drainage_hints.diagnostic_rows)
        assert any(item == f"warning:source_drainage_policy_intent_status_unknown:{policy_ref}" for item in drainage_hints.diagnostic_rows)
        assert any(item == f"warning:source_drainage_policy_method_unknown:{policy_ref}" for item in drainage_hints.diagnostic_rows)
    finally:
        App.closeDocument(doc.Name)


def test_intersection_drainage_hints_mark_accepted_source_missing_refs_as_error() -> None:
    doc = App.newDocument("CRV1IntersectionDrainageAcceptedMissingRefs")
    try:
        create_intersection_preset_sources(
            doc,
            preset_label="T Intersection - Basic",
            grading_policy="blend_primary_side",
            drainage_mode="outside_gutter",
        )
        model = to_intersection_model(find_v1_intersection_model(doc))
        assert model is not None
        policy_ref = model.drainage_policy_rows[0].policy_id
        model.drainage_policy_rows = [
            IntersectionDrainagePolicyRow(
                policy_id=policy_ref,
                intersection_id=model.drainage_policy_rows[0].intersection_id,
                capture_mode="outside_gutter",
                intent_status="accepted",
                source_method="manual",
                approval_status="locked",
                drainage_element_refs=[],
                flow_route_refs=[],
            )
        ]

        service = IntersectionEvaluationService()
        surface_zones = service.evaluate_surface_zones(model)
        grading_context = service.evaluate_grading_context(model, surface_zones)
        drainage_hints = service.evaluate_drainage_hints(model, surface_zones, grading_context)
        source_rows = [row for row in drainage_hints.hint_rows if row.source_drainage_policy_ref == policy_ref]

        assert drainage_hints.status == "warning"
        assert source_rows
        assert all(row.drainage_handoff_status == "accepted_source_incomplete" for row in source_rows)
        assert all(row.source_lineage_status == "source_incomplete" for row in source_rows)
        assert all(row.source_status == "error" for row in source_rows)
        assert all(row.status == "error" for row in source_rows)
        assert all(row.accepted_drainage_ref == "" for row in source_rows)
        assert any("source_drainage_element_refs_missing" in row.source_diagnostic_rows for row in source_rows)
        assert any("source_drainage_flow_route_refs_missing" in row.source_diagnostic_rows for row in source_rows)
    finally:
        App.closeDocument(doc.Name)


def test_intersection_slope_face_loops_preserve_surface_zone_source_lineage() -> None:
    doc = App.newDocument("CRV1IntersectionSlopeLoopSourceLineage")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        model = to_intersection_model(find_v1_intersection_model(doc))
        assert model is not None
        service = IntersectionEvaluationService()
        edge_network = service.evaluate_edge_network(model)
        surface_zones = service.evaluate_surface_zones(model, edge_network)
        slope_loops = service.evaluate_slope_face_loops(model, surface_zones, edge_network)
        loop_rows = list(slope_loops.loop_rows)

        assert loop_rows
        assert any(row.source_surface_zone_refs for row in loop_rows)
        assert any(row.source_edge_network_refs for row in loop_rows)
        assert any(row.source_surface_zone_status == "warning" for row in loop_rows)
        assert any(row.source_status == "warning" for row in loop_rows)
        assert any(row.source_lineage_status == "source_warning" for row in loop_rows)
        assert any(row.source_diagnostic_rows for row in loop_rows)
    finally:
        App.closeDocument(doc.Name)


def test_intersection_slope_face_loops_preserve_edge_network_source_lineage() -> None:
    doc = App.newDocument("CRV1IntersectionSlopeLoopEdgeSourceLineage")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        model = to_intersection_model(find_v1_intersection_model(doc))
        assert model is not None
        service = IntersectionEvaluationService()
        edge_network = service.evaluate_edge_network(model)
        surface_zones = service.evaluate_surface_zones(model, edge_network)
        assert edge_network.edge_rows

        source_edge_ref = edge_network.edge_rows[0].edge_id
        edge_network.edge_rows[0] = replace(
            edge_network.edge_rows[0],
            source_status="error",
            source_diagnostic_rows=("source_edge_family_policy_ref_missing",),
            status="error",
        )
        slope_loops = service.evaluate_slope_face_loops(model, surface_zones, edge_network)
        loop_rows = [
            row
            for row in slope_loops.loop_rows
            if source_edge_ref in tuple(row.source_edge_network_refs or ())
        ]

        assert loop_rows
        assert any(row.source_edge_network_status == "error" for row in loop_rows)
        assert any(row.source_lineage_status == "source_error" for row in loop_rows)
        assert any(row.source_status == "error" for row in loop_rows)
        assert any(row.status == "error" for row in loop_rows)
        assert any(
            f"source_edge_network:{source_edge_ref}:source_edge_family_policy_ref_missing" in row.source_diagnostic_rows
            for row in loop_rows
        )
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_drainage_hints_include_outside_gutter_handoff() -> None:
    doc = App.newDocument("CRV1RoundaboutDrainageHints")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane")
        model = to_intersection_model(find_v1_intersection_model(doc))
        drainage_hints = IntersectionEvaluationService().evaluate_drainage_hints(model)
        outlet_rows = [row for row in drainage_hints.hint_rows if row.hint_kind == "outlet_handoff"]

        assert model is not None
        assert drainage_hints.intersection_kind == "roundabout"
        assert drainage_hints.outlet_handoff_count == len(outlet_rows)
        assert outlet_rows
        assert all(row.drainage_mode == "outside_gutter" for row in outlet_rows)
        assert all(row.source_lineage_status == "hint_only" for row in outlet_rows)
        assert all(row.handoff_target.startswith("intersection-source-stage:drainage:") for row in outlet_rows)
        assert any(row.zone_role == "roundabout_circulatory_lane" for row in drainage_hints.hint_rows)
    finally:
        App.closeDocument(doc.Name)


def test_intersection_starter_region_model_omits_zero_length_rows() -> None:
    model = _starter_region_model_for_alignment(
        alignment_id="alignment:intersection-secondary",
        intersection_kind="t_intersection",
        role="secondary",
        length=100.0,
        project_id="project:test",
    )

    assert all(row.station_end > row.station_start for row in model.region_rows)
    assert [row.region_index for row in model.region_rows] == [1, 2]
    assert model.region_rows[0].region_id == "region:secondary-approach"
    assert model.region_rows[0].station_start == 0.0
    assert model.region_rows[0].station_end == 65.0
    assert model.region_rows[1].region_id == "region:secondary-intersection"
    assert model.region_rows[1].station_start == 65.0
    assert model.region_rows[1].station_end == 100.0


def test_intersection_existing_alignment_validation_requires_two_different_refs() -> None:
    assert validate_existing_alignment_selection("", "") == [
        "Primary Alignment is required.",
        "Secondary Alignment is required.",
    ]
    assert validate_existing_alignment_selection("alignment:main", "alignment:main") == [
        "Primary and Secondary Alignment must be different."
    ]
    assert validate_existing_alignment_selection("alignment:main", "alignment:side") == []


def test_intersection_alignment_choices_list_v1_alignments() -> None:
    doc = App.newDocument("CRV1IntersectionAlignmentChoices")
    try:
        main = create_sample_v1_alignment(doc, label="Main Road")
        side = create_sample_v1_alignment(doc, label="Side Road")
        side.AlignmentId = "alignment:side-road"

        choices = list_v1_alignment_choices(doc)

        assert (main.AlignmentId, "Main Road") in choices
        assert ("alignment:side-road", "Side Road") in choices
    finally:
        App.closeDocument(doc.Name)


def test_intersection_alignment_model_by_ref_returns_selected_alignment_model() -> None:
    doc = App.newDocument("CRV1IntersectionAlignmentByRef")
    try:
        alignment = create_sample_v1_alignment(doc, label="Main Road")
        model = alignment_model_by_ref(doc, alignment.AlignmentId)

        assert model is not None
        assert model.alignment_id == alignment.AlignmentId
    finally:
        App.closeDocument(doc.Name)


def test_intersection_review_overlay_includes_curb_return_preview_arcs() -> None:
    doc = App.newDocument("CRV1IntersectionCurbReturnOverlay")
    try:
        primary = create_sample_v1_alignment(doc, label="Primary Road")
        secondary = create_sample_v1_alignment(doc, label="Side Road")
        secondary.AlignmentId = "alignment:side-road"
        detection = SimpleNamespace(x=10.0, y=0.0, primary_station=10.0, secondary_station=10.0)

        obj = show_intersection_review_overlay(
            doc,
            intersection_kind="t_intersection",
            primary_alignment_ref=primary.AlignmentId,
            secondary_alignment_ref=secondary.AlignmentId,
            control_region_choices=[
                {
                    "control_region_ref": "regions:primary/region:primary-intersection",
                    "alignment_ref": primary.AlignmentId,
                    "station_start": 0.0,
                    "station_end": 20.0,
                },
                {
                    "control_region_ref": "regions:side/region:side-intersection",
                    "alignment_ref": secondary.AlignmentId,
                    "station_start": 0.0,
                    "station_end": 20.0,
                },
            ],
            detection_result=detection,
        )

        assert obj.Name == "V1IntersectionReviewOverlay"
        assert obj.CurbReturnPolicyRef == "curb-return:starter-t_intersection:default"
        assert obj.CurbReturnRadius == "12.000"
        assert int(obj.CurbReturnArcCount) == 2
        assert list(obj.CurbReturnDiagnostics) == []
        assert int(obj.ShapePartCount) >= 2
    finally:
        App.closeDocument(doc.Name)


def test_intersection_review_overlay_clips_long_control_region_highlight() -> None:
    doc = App.newDocument("CRV1IntersectionOverlayClipsLongRegion")
    try:
        primary = create_sample_v1_alignment(doc, label="Primary Road")
        secondary = create_sample_v1_alignment(doc, label="Side Road")
        secondary.AlignmentId = "alignment:side-road"
        detection = SimpleNamespace(x=10.0, y=0.0, primary_station=10.0, secondary_station=10.0)

        obj = show_intersection_review_overlay(
            doc,
            intersection_kind="t_intersection",
            primary_alignment_ref=primary.AlignmentId,
            secondary_alignment_ref=secondary.AlignmentId,
            control_region_choices=[
                {
                    "control_region_ref": "regions:primary/region:primary-intersection",
                    "alignment_ref": primary.AlignmentId,
                    "station_start": 0.0,
                    "station_end": 180.0,
                },
            ],
            detection_result=detection,
        )

        bound_box = obj.Shape.BoundBox
        assert float(bound_box.XLength) <= INTERSECTION_REVIEW_MAX_REGION_SPAN + 7.0
    finally:
        App.closeDocument(doc.Name)


def test_intersection_starter_alignment_ids_are_unique() -> None:
    doc = App.newDocument("CRV1IntersectionUniqueAlignmentId")
    try:
        alignment = create_sample_v1_alignment(doc, label="Intersection Main Road")
        alignment.AlignmentId = "alignment:intersection-primary"

        assert _unique_alignment_id(doc, "alignment:intersection-primary") == "alignment:intersection-primary-2"
        assert _unique_alignment_id(doc, "alignment:intersection-secondary") == "alignment:intersection-secondary"
    finally:
        App.closeDocument(doc.Name)


def test_intersection_command_is_active_only_with_document() -> None:
    command = CmdV1IntersectionPresets()
    doc = App.newDocument("CRV1IntersectionCommand")
    try:
        assert command.IsActive() is True
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] intersection command tests completed.")
