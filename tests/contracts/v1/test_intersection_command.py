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
    set_intersection_edge_network_preview_visible,
    show_intersection_edge_network_preview,
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
        "skewed_intersection": {"primary", "secondary_skew"},
        "urban_curb_gutter_intersection": {"primary", "secondary"},
        "drainage_sag_intersection": {"primary", "secondary"},
        "y_intersection": {"primary_approach", "left_branch", "right_branch"},
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
        "Skewed Intersection - Basic",
        "Urban Curb/Gutter - Basic",
        "Drainage-Sensitive Sag - Basic",
        "Y Intersection - Basic",
        "Roundabout - Single Lane",
    ]
    assert intersection_preset_kind_from_label("T Intersection - Basic") == "t_intersection"
    assert intersection_preset_kind_from_label("Cross Intersection - Basic") == "cross_intersection"
    assert intersection_preset_kind_from_label("Skewed Intersection - Basic") == "skewed_intersection"
    assert intersection_preset_kind_from_label("Urban Curb/Gutter - Basic") == "urban_curb_gutter_intersection"
    assert intersection_preset_kind_from_label("Drainage-Sensitive Sag - Basic") == "drainage_sag_intersection"
    assert intersection_preset_kind_from_label("Y Intersection - Basic") == "y_intersection"
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


def test_skewed_intersection_preset_creates_skew_source_and_review_diagnostics() -> None:
    spec = starter_intersection_source_specs("skewed_intersection")
    primary_points = list(spec["alignments"][0]["points"])
    secondary_points = list(spec["alignments"][1]["points"])
    primary_vector = (
        float(primary_points[-1][0]) - float(primary_points[0][0]),
        float(primary_points[-1][1]) - float(primary_points[0][1]),
    )
    secondary_vector = (
        float(secondary_points[-1][0]) - float(secondary_points[0][0]),
        float(secondary_points[-1][1]) - float(secondary_points[0][1]),
    )
    dot = primary_vector[0] * secondary_vector[0] + primary_vector[1] * secondary_vector[1]
    cross = primary_vector[0] * secondary_vector[1] - primary_vector[1] * secondary_vector[0]
    assert abs(dot) > 1.0e-6
    assert abs(cross) > 1.0e-6

    doc = App.newDocument("CRV1SkewedIntersectionPresetSources")
    try:
        created = create_intersection_preset_sources(
            doc,
            preset_label="Skewed Intersection - Basic",
            grading_policy="blend_primary_side",
            drainage_mode="review_low_points",
        )
        model = to_intersection_model(find_v1_intersection_model(doc))

        assert any("Skew Main Road" in line for line in created)
        assert any("Skew Crossing Road" in line for line in created)
        assert model is not None
        assert "intersection-preset:skewed_intersection:source-completeness" in model.source_refs
        assert "intersection-preset:skewed_intersection:skew-review" in model.source_refs
        row = model.intersection_rows[0]
        assert row.intersection_kind == "skewed_intersection"
        assert "source_completeness_ref=intersection-preset:skewed_intersection:source-completeness" in row.notes
        assert "skew_review_ref=intersection-preset:skewed_intersection:skew-review" in row.notes
        assert row.primary_alignment_ref
        assert len(row.secondary_alignment_refs) == 1
        assert len(row.control_region_refs) == 2
        assert len(model.corner_rows) == 4
        assert all("preset_corner_review_required" in corner.diagnostic_rows for corner in model.corner_rows)
        assert all("preset_skew_corner_geometry_review_required" in corner.diagnostic_rows for corner in model.corner_rows)
        assert all("skew_review_ref=intersection-preset:skewed_intersection:skew-review" in corner.notes for corner in model.corner_rows)
        assert len(model.edge_policy_rows) >= 4
        assert all("preset_skew_edge_family_review_required" in edge.diagnostic_rows for edge in model.edge_policy_rows)
        assert all("skew_review_ref=intersection-preset:skewed_intersection:skew-review" in edge.notes for edge in model.edge_policy_rows)
        assert {round(float(policy.radius), 3) for policy in model.curb_return_policy_rows} == {11.0}

        completeness_rows = intersection_source_completeness_rows(
            model,
            control_region_count=len(row.control_region_refs),
        )
        completeness_summary = intersection_source_completeness_summary(completeness_rows)
        rows_by_stage = {stage_row["stage"]: stage_row for stage_row in completeness_rows}
        assert rows_by_stage["Participants"]["status"] == "accepted"
        assert rows_by_stage["Corners"]["approval_state"] == "draft"
        assert rows_by_stage["Edge Families"]["approval_state"] == "draft"
        assert completeness_summary["status"] == "warning"
        assert completeness_summary["missing_count"] == 0
    finally:
        App.closeDocument(doc.Name)


def test_urban_curb_gutter_preset_creates_edge_and_drainage_handoff_rows() -> None:
    doc = App.newDocument("CRV1UrbanCurbGutterPresetSources")
    try:
        created = create_intersection_preset_sources(
            doc,
            preset_label="Urban Curb/Gutter - Basic",
            grading_policy="blend_primary_side",
            drainage_mode="curb_gutter_inlets",
        )
        model = to_intersection_model(find_v1_intersection_model(doc))
        drainage = to_drainage_model(doc.getObject("V1IntersectionPresetDrainage"))

        assert any("Urban Main Street" in line for line in created)
        assert any("Urban Side Street" in line for line in created)
        assert any("Drainage rows: elements=6" in line for line in created)
        assert model is not None
        assert "intersection-preset:urban_curb_gutter_intersection:source-completeness" in model.source_refs
        assert "intersection-preset:urban_curb_gutter_intersection:urban-curb-gutter-review" in model.source_refs
        row = model.intersection_rows[0]
        assert row.intersection_kind == "urban_curb_gutter_intersection"
        assert "source_completeness_ref=intersection-preset:urban_curb_gutter_intersection:source-completeness" in row.notes
        assert "urban_review_ref=intersection-preset:urban_curb_gutter_intersection:urban-curb-gutter-review" in row.notes
        assert len(row.control_region_refs) == 2

        edge_roles = {edge.edge_role for edge in model.edge_policy_rows}
        assert {"curb_edge", "gutter_edge", "sidewalk_edge"}.issubset(edge_roles)
        urban_edges = [
            edge
            for edge in model.edge_policy_rows
            if edge.edge_role in {"curb_edge", "gutter_edge", "sidewalk_edge"}
        ]
        assert urban_edges
        assert {edge.source_method for edge in urban_edges} == {"urban_preset_default"}
        assert all(edge.approval_status == "draft" for edge in urban_edges)
        assert any("preset_urban_curb_review_required" in edge.diagnostic_rows for edge in urban_edges)
        assert any("preset_urban_gutter_review_required" in edge.diagnostic_rows for edge in urban_edges)
        assert any("preset_urban_sidewalk_review_required" in edge.diagnostic_rows for edge in urban_edges)
        assert all(
            "urban_review_ref=intersection-preset:urban_curb_gutter_intersection:urban-curb-gutter-review" in edge.notes
            for edge in urban_edges
        )

        drainage_policy = model.drainage_policy_rows[0]
        assert drainage_policy.capture_mode == "curb_gutter_inlets"
        assert drainage_policy.inlet_spacing == 45.0
        assert drainage_policy.gutter_edge_refs
        assert drainage_policy.inlet_candidate_refs
        assert drainage_policy.low_point_refs
        assert "preset_urban_inlet_review_required" in drainage_policy.diagnostic_rows
        assert "preset_urban_low_point_review_required" in drainage_policy.diagnostic_rows
        assert "urban_review_ref=intersection-preset:urban_curb_gutter_intersection:urban-curb-gutter-review" in drainage_policy.notes
        assert drainage is not None
        assert drainage.drainage_model_id == "drainage:intersection-preset-urban-curb-gutter-intersection"
        assert len(drainage.element_rows) == 6
        assert len([item for item in drainage.element_rows if item.element_kind == "inlet_candidate"]) == 4

        completeness_rows = intersection_source_completeness_rows(
            model,
            control_region_count=len(row.control_region_refs),
        )
        completeness_summary = intersection_source_completeness_summary(completeness_rows)
        rows_by_stage = {stage_row["stage"]: stage_row for stage_row in completeness_rows}
        assert rows_by_stage["Edge Families"]["approval_state"] == "draft"
        assert rows_by_stage["Drainage"]["approval_state"] == "draft"
        assert completeness_summary["status"] == "warning"
        assert completeness_summary["missing_count"] == 0
    finally:
        App.closeDocument(doc.Name)


def test_drainage_sag_preset_creates_sag_profile_and_drainage_handoff_rows() -> None:
    doc = App.newDocument("CRV1DrainageSagPresetSources")
    try:
        created = create_intersection_preset_sources(
            doc,
            preset_label="Drainage-Sensitive Sag - Basic",
            grading_policy="blend_primary_side",
            drainage_mode="sag_low_point_inlets",
        )
        model = to_intersection_model(find_v1_intersection_model(doc))
        drainage = to_drainage_model(doc.getObject("V1IntersectionPresetDrainage"))
        profile_models = [
            to_profile_model(obj)
            for obj in list(getattr(doc, "Objects", []) or [])
            if str(getattr(obj, "V1ObjectType", "") or "") == "V1Profile"
        ]
        profile_models = [profile for profile in profile_models if profile is not None]

        assert any("Sag Main Road" in line for line in created)
        assert any("Sag Side Road" in line for line in created)
        assert any("Drainage rows: elements=6" in line for line in created)
        assert model is not None
        assert "intersection-preset:drainage_sag_intersection:source-completeness" in model.source_refs
        assert "intersection-preset:drainage_sag_intersection:sag-drainage-review" in model.source_refs
        row = model.intersection_rows[0]
        assert row.intersection_kind == "drainage_sag_intersection"
        assert "source_completeness_ref=intersection-preset:drainage_sag_intersection:source-completeness" in row.notes
        assert "sag_review_ref=intersection-preset:drainage_sag_intersection:sag-drainage-review" in row.notes
        assert len(row.control_region_refs) == 2

        assert profile_models
        assert all(len(profile.control_rows) == 3 for profile in profile_models)
        assert all(profile.control_rows[1].kind == "sag_low_point" for profile in profile_models)
        assert all(profile.control_rows[1].elevation < profile.control_rows[0].elevation for profile in profile_models)
        assert all(profile.control_rows[1].elevation < profile.control_rows[2].elevation for profile in profile_models)

        grading_policy = model.grading_policy_rows[0]
        assert grading_policy.low_point_strategy == "sag_low_point_review"
        assert "preset_sag_profile_review_required" in grading_policy.diagnostic_rows
        assert "preset_sag_low_point_review_required" in grading_policy.diagnostic_rows
        assert "sag_review_ref=intersection-preset:drainage_sag_intersection:sag-drainage-review" in grading_policy.notes

        drainage_policy = model.drainage_policy_rows[0]
        assert drainage_policy.capture_mode == "sag_low_point_inlets"
        assert drainage_policy.inlet_spacing == 35.0
        assert drainage_policy.drainage_element_refs
        assert drainage_policy.flow_route_refs
        assert drainage_policy.inlet_candidate_refs
        assert drainage_policy.low_point_refs
        assert "preset_sag_inlet_review_required" in drainage_policy.diagnostic_rows
        assert "preset_sag_flow_route_review_required" in drainage_policy.diagnostic_rows
        assert "preset_sag_hydraulic_sizing_required" in drainage_policy.diagnostic_rows
        assert "sag_review_ref=intersection-preset:drainage_sag_intersection:sag-drainage-review" in drainage_policy.notes
        assert drainage is not None
        assert drainage.drainage_model_id == "drainage:intersection-preset-drainage-sag-intersection"
        assert len(drainage.element_rows) == 6
        assert len([item for item in drainage.element_rows if item.element_kind == "sag_low_point"]) == 2
        assert len([item for item in drainage.element_rows if item.element_kind == "inlet_candidate"]) == 2
        assert drainage.flow_route_rows[0].risk_level == "critical"

        completeness_rows = intersection_source_completeness_rows(
            model,
            control_region_count=len(row.control_region_refs),
        )
        completeness_summary = intersection_source_completeness_summary(completeness_rows)
        rows_by_stage = {stage_row["stage"]: stage_row for stage_row in completeness_rows}
        assert rows_by_stage["Grading"]["approval_state"] == "draft"
        assert rows_by_stage["Drainage"]["approval_state"] == "draft"
        assert completeness_summary["status"] == "warning"
        assert completeness_summary["missing_count"] == 0
    finally:
        App.closeDocument(doc.Name)


def test_y_intersection_preset_creates_branch_roles_and_review_diagnostics() -> None:
    doc = App.newDocument("CRV1YIntersectionPresetSources")
    try:
        created = create_intersection_preset_sources(
            doc,
            preset_label="Y Intersection - Basic",
            grading_policy="blend_primary_side",
            drainage_mode="review_low_points",
        )
        model = to_intersection_model(find_v1_intersection_model(doc))

        assert any("Y Left Branch Road" in line for line in created)
        assert any("Y Right Branch Road" in line for line in created)
        assert model is not None
        assert "intersection-preset:y_intersection:source-completeness" in model.source_refs
        assert "intersection-preset:y_intersection:branch-review" in model.source_refs
        row = model.intersection_rows[0]
        assert row.intersection_kind == "y_intersection"
        assert "source_completeness_ref=intersection-preset:y_intersection:source-completeness" in row.notes
        assert "branch_review_ref=intersection-preset:y_intersection:branch-review" in row.notes
        assert len(row.secondary_alignment_refs) == 2
        assert len(row.control_region_refs) == 3

        leg_roles = {leg.leg_role for leg in row.leg_rows}
        assert {"primary_approach", "left_branch", "right_branch"}.issubset(leg_roles)
        assert len(model.corner_rows) == 2
        assert {corner.side for corner in model.corner_rows} == {"left_branch", "right_branch"}
        assert all("preset_y_branch_geometry_review_required" in corner.diagnostic_rows for corner in model.corner_rows)
        assert all("branch_review_ref=intersection-preset:y_intersection:branch-review" in corner.notes for corner in model.corner_rows)
        assert len(model.lane_connection_rows) == 3
        assert {lane.movement_type for lane in model.lane_connection_rows} == {"diverge", "merge"}
        assert all("preset_lane_connection_review_required" in lane.diagnostic_rows for lane in model.lane_connection_rows)
        assert all("preset_y_diverge_merge_review_required" in lane.diagnostic_rows for lane in model.lane_connection_rows)
        assert all("branch_review_ref=intersection-preset:y_intersection:branch-review" in lane.notes for lane in model.lane_connection_rows)

        completeness_rows = intersection_source_completeness_rows(
            model,
            control_region_count=len(row.control_region_refs),
        )
        completeness_summary = intersection_source_completeness_summary(completeness_rows)
        rows_by_stage = {stage_row["stage"]: stage_row for stage_row in completeness_rows}
        assert rows_by_stage["Participants"]["status"] == "accepted"
        assert rows_by_stage["Lane Connections"]["approval_state"] == "draft"
        assert completeness_summary["status"] == "warning"
        assert completeness_summary["missing_count"] == 0
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
        create_starter_intersection_sources(doc, "drainage_sag_intersection")
        _ensure_qapp()
        panel = V1IntersectionEditorTaskPanel(document=doc)
        panel._type_combo.setCurrentText("Drainage-Sensitive Sag Intersection")
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
        assert "source_lineage_status:hint_only" in rows_by_stage["Drainage"]["diagnostics"]

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
        assert "source_lineage_status:hint_only" in preview_by_stage["Drainage"]["diagnostics"]
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
        preview = show_intersection_edge_network_preview(doc, intersection_model=model, detection_result=detection)

        assert {row.design_vehicle_ref for row in model.arm_policy_rows} == {"bus_or_small_truck"}
        assert {round(float(row.radius), 3) for row in model.curb_return_policy_rows} == {18.0}
        assert model.curb_return_policy_rows[0].corner_refs == [row.corner_id for row in model.corner_rows]
        assert model.grading_policy_rows[0].mode == "keep_primary_crown"
        assert model.drainage_policy_rows[0].capture_mode == "outside_gutter"
        assert preview.CurbReturnRadius == "18.000"
        assert "bus_or_small_truck" in list(preview.DesignVehicles)
        assert "keep_primary_crown" in list(preview.GradingPolicies)
        assert "outside_gutter" in list(preview.DrainageModes)
        assert list(preview.ControlAreaRanges)
    finally:
        App.closeDocument(doc.Name)


def test_intersection_edge_network_preview_can_be_hidden_after_creation() -> None:
    doc = App.newDocument("CRV1IntersectionPresetPreviewHide")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        model, _control_region_count, detection = build_preset_source_intersection_model(
            doc,
            preset_label="T Intersection - Basic",
        )

        preview = show_intersection_edge_network_preview(doc, intersection_model=model, detection_result=detection)
        hidden = set_intersection_edge_network_preview_visible(doc, False)

        assert hidden == preview
        assert hidden.Name == "V1IntersectionEdgeNetworkPreview"
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
            ("LegacyIntersectionEdgeNetwork", "Intersection Edge Network Preview"),
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
        leftovers[5].addProperty("App::PropertyString", "CRRecordKind", "CorridorRoad", "")
        leftovers[5].CRRecordKind = "v1_intersection_edge_network_preview"

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
        assert "roundabout_circulatory_pavement" in roles
        assert "roundabout_entry_exit_pavement" in roles
        assert all(row.surface_priority > 0 for row in roundabout_zones)
        assert all(row.vertical_policy_ref for row in roundabout_zones)
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
        assert any(row.zone_role == "roundabout_circulatory_pavement" for row in drainage_hints.hint_rows)
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
