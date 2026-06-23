import FreeCAD as App
from types import SimpleNamespace

from freecad.Corridor_Road.init_gui import corridorroad_workflow_command_groups
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, V1_TREE_INTERSECTIONS, ensure_project_tree, find_project
from freecad.Corridor_Road.v1.commands.cmd_intersection_editor import (
    CmdV1IntersectionEditor,
    INTERSECTION_COMMAND_ID,
    INTERSECTION_SOURCE_MODES,
    NEXT_INTERSECTION_WORKFLOW_TEXT,
    alignment_model_by_ref,
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
from freecad.Corridor_Road.v1.objects.obj_region import to_region_model
from freecad.Corridor_Road.v1.objects.obj_subassembly_assembly import (
    find_v1_assembly_subassembly_model,
    to_assembly_subassembly_model,
)
from freecad.Corridor_Road.v1.objects.obj_superelevation import to_superelevation_model
from freecad.Corridor_Road.v1.services.evaluation.intersection_evaluation_service import IntersectionEvaluationService


def test_intersection_command_resources_are_specific() -> None:
    resources = CmdV1IntersectionEditor().GetResources()

    assert resources["MenuText"] == "Intersections"
    assert "intersection" in resources["ToolTip"].lower()
    assert str(resources["Pixmap"]).replace("\\", "/").endswith("intersections.svg")


def test_intersection_command_is_between_regions_and_structures() -> None:
    commands = corridorroad_workflow_command_groups()["assembly_region"]

    assert INTERSECTION_COMMAND_ID in commands
    assert INTERSECTION_PRESETS_COMMAND_ID in commands
    assert commands.index("CorridorRoad_V1EditRegions") < commands.index(INTERSECTION_COMMAND_ID)
    assert commands.index(INTERSECTION_COMMAND_ID) < commands.index(INTERSECTION_PRESETS_COMMAND_ID)
    assert commands.index(INTERSECTION_PRESETS_COMMAND_ID) < commands.index("CorridorRoad_V1EditStructures")


def test_intersection_presets_command_resources_are_specific() -> None:
    resources = CmdV1IntersectionPresets().GetResources()

    assert resources["MenuText"] == "Intersection Presets"
    assert "preset" in resources["ToolTip"].lower()
    assert str(resources["Pixmap"]).replace("\\", "/").endswith("intersections.svg")


def test_intersection_panel_constants_expose_first_slice_modes() -> None:
    assert INTERSECTION_SOURCE_MODES == ("Use Existing Alignments", "Create Starter Sources")
    assert NEXT_INTERSECTION_WORKFLOW_TEXT.endswith("Build Sections")


def test_intersection_starter_source_specs_cover_first_slice_types() -> None:
    for kind in ("t_intersection", "cross_intersection", "y_intersection", "roundabout"):
        spec = starter_intersection_source_specs(kind)
        alignments = list(spec["alignments"])

        assert spec["kind"] == kind
        assert len(alignments) == 2
        assert {row["role"] for row in alignments} == {"primary", "secondary"}
        assert all(len(row["points"]) >= 2 for row in alignments)


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
        assert len(model.intersection_rows) == 1
        row = model.intersection_rows[0]
        assert row.intersection_kind == "t_intersection"
        assert row.primary_alignment_ref
        assert row.secondary_alignment_refs
        assert len(row.control_region_refs) == 2
        assert len(model.arm_policy_rows) == 2
        assert len(model.edge_policy_rows) == 4
        assert len(model.curb_return_policy_rows) == 1
        assert len(model.grading_policy_rows) == 1
        assert model.grading_policy_rows[0].mode == "blend_primary_side"
        assert len(model.drainage_policy_rows) == 1
        assert model.drainage_policy_rows[0].capture_mode == "outside_gutter"

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
        assert rows_by_zone["exterior_slope_face"].crossfall_context == "normal_superelevation"
        assert rows_by_zone["central_pavement"].surface_priority > rows_by_zone["exterior_slope_face"].surface_priority
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
    command = CmdV1IntersectionEditor()
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
