
import FreeCAD as App

from freecad.Corridor_Road.init_gui import corridorroad_workflow_command_groups, corridorroad_workflow_toolbar_commands
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.objects.obj_project import (
    CorridorRoadProject,
    V1_TREE_DRAINAGE,
    V1_TREE_INTERSECTIONS,
    V1_TREE_PROFILES,
    V1_TREE_REGIONS,
    V1_TREE_STATIONS,
    V1_TREE_SUPERELEVATION,
    ensure_project_tree,
    find_project,
)
from freecad.Corridor_Road.v1.commands.cmd_intersection_editor import (
    INTERSECTION_COMMAND_ID,
    INTERSECTION_SOURCE_MODES,
    NEXT_INTERSECTION_WORKFLOW_TEXT,
    alignment_model_by_ref,
    starter_intersection_source_specs,
    list_v1_alignment_choices,
    validate_existing_alignment_selection,
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
)
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
    corridor_subassembly_kind_guided_review_rows,
    focus_corridor_build_guided_review_step,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_intersection import find_v1_intersection_model, to_intersection_model
from freecad.Corridor_Road.v1.models.source.intersection_model import (
    IntersectionAnchorRow,
    IntersectionControlArea,
    IntersectionCornerRow,
    IntersectionCurbReturnPolicyRow,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
)

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


def _corner_source_validation_model(curb_return_policy_ref: str) -> IntersectionModel:
    return IntersectionModel(
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
                curb_return_policy_ref=curb_return_policy_ref,
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
        assert model.control_area_rows
    finally:
        App.closeDocument(doc.Name)


# the preset routes each source into the project-tree folder for its kind
_INTERSECTION_PRESET_TREE_PLACEMENT = {
    "Intersection Main Road FG Profile": V1_TREE_PROFILES,
    "Intersection Main Road Stations": V1_TREE_STATIONS,
    "Intersection Main Road Regions": V1_TREE_REGIONS,
    "Intersection Side Road FG Profile": V1_TREE_PROFILES,
    "Intersection Side Road Stations": V1_TREE_STATIONS,
    "Intersection Side Road Regions": V1_TREE_REGIONS,
    "Intersection Preset Superelevation (primary)": V1_TREE_SUPERELEVATION,
    "Intersection Preset Superelevation (secondary)": V1_TREE_SUPERELEVATION,
    "Intersection Preset Drainage": V1_TREE_DRAINAGE,
}


def _tree_folder_labels(tree, tree_key) -> set:
    folder = tree[tree_key]
    return {str(getattr(obj, "Label", "") or "") for obj in list(getattr(folder, "Group", []) or [])}


def _document_root_labels(doc) -> set:
    return {str(getattr(obj, "Label", "") or "") for obj in list(getattr(doc, "RootObjects", []) or [])}


def test_intersection_preset_sources_route_to_project_tree_folders_by_kind() -> None:
    doc = App.newDocument("CRV1IntersectionPresetTreeRouting")
    try:
        project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(project)
        tree = ensure_project_tree(project, include_references=False)

        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")

        root_labels = _document_root_labels(doc)
        for label, tree_key in _INTERSECTION_PRESET_TREE_PLACEMENT.items():
            assert label in _tree_folder_labels(tree, tree_key)
            assert label not in root_labels
        # the intersection model itself is what the Intersections folder holds
        assert any(
            label == "Intersection Source"
            for label in _tree_folder_labels(tree, V1_TREE_INTERSECTIONS)
        )
    finally:
        App.closeDocument(doc.Name)


def test_intersection_preset_tree_cleanup_routes_existing_root_leftovers() -> None:
    doc = App.newDocument("CRV1IntersectionPresetRootCleanup")
    try:
        project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(project)
        tree = ensure_project_tree(project, include_references=False)
        # leftovers carry the names an earlier preset run gave them, because the tree
        # policy classifies profiles and stations by name and the rest by record kind
        specs = [
            ("V1Profile", "Intersection Main Road FG Profile", V1_TREE_PROFILES, ()),
            ("V1Stationing", "Intersection Main Road Stations", V1_TREE_STATIONS, ()),
            (
                "V1IntersectionModel",
                "Intersections001",
                V1_TREE_INTERSECTIONS,
                (("CRRecordKind", "v1_intersection_model"),),
            ),
            (
                "V1IntersectionPresetSuperelevationPrimary",
                "Intersection Preset Superelevation (primary)",
                V1_TREE_SUPERELEVATION,
                (
                    ("CRRecordKind", "v1_superelevation_source"),
                    ("SuperelevationKind", "intersection_superelevation_handoff"),
                ),
            ),
            (
                "V1IntersectionPresetDrainage",
                "Intersection Preset Drainage",
                V1_TREE_DRAINAGE,
                (
                    ("CRRecordKind", "v1_drainage_model"),
                    ("DrainageModelId", "drainage:intersection-preset-t-intersection"),
                ),
            ),
        ]
        leftovers = []
        for name, label, tree_key, properties in specs:
            obj = doc.addObject("App::FeaturePython", name)
            obj.Label = label
            for property_name, value in properties:
                obj.addProperty("App::PropertyString", property_name, "CorridorRoad", "")
                setattr(obj, property_name, value)
            leftovers.append((obj, tree_key))

        _route_intersection_preset_objects(doc, project=project)

        root_names = {
            str(getattr(obj, "Name", "") or "") for obj in list(getattr(doc, "RootObjects", []) or [])
        }
        for obj, tree_key in leftovers:
            folder_names = {
                str(getattr(child, "Name", "") or "")
                for child in list(getattr(tree[tree_key], "Group", []) or [])
            }
            assert obj.Name in folder_names
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

        root_labels = _document_root_labels(doc)
        for label, tree_key in _INTERSECTION_PRESET_TREE_PLACEMENT.items():
            assert label in _tree_folder_labels(tree, tree_key)
            assert label not in root_labels
        assert any(
            label == "Intersection Source"
            for label in _tree_folder_labels(tree, V1_TREE_INTERSECTIONS)
        )
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


def test_roundabout_lane_shoulder_guided_review_clips_to_the_kernel_boundary() -> None:
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
        assert lane_preview.RoundaboutClipBoundaryRole == "intersection_kernel_boundary"
        assert lane_preview.RoundaboutReportedBoundaryRole == "intersection_kernel_boundary"
        assert lane_preview.RoundaboutActualClipBoundaryRole == "intersection_kernel_boundary"
        assert lane_preview.RoundaboutActualClipBoundaryRoles == "intersection_kernel_boundary"
        assert lane_preview.RoundaboutReviewClipMode == "intersection_kernel_boundary"
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
        assert shoulder_preview.RoundaboutClipBoundaryRole == "intersection_kernel_boundary"
        assert shoulder_preview.RoundaboutReportedBoundaryRole == "intersection_kernel_boundary"
        assert shoulder_preview.RoundaboutActualClipBoundaryRole == "intersection_kernel_boundary"
        assert shoulder_preview.RoundaboutActualClipBoundaryRoles == "intersection_kernel_boundary"
        assert shoulder_preview.RoundaboutReviewClipMode == "intersection_kernel_boundary"
        assert shoulder_preview.RoundaboutClipBoundaryStatus == "ready"
        assert shoulder_preview.RoundaboutClipFallbackReason == ""
        assert int(shoulder_preview.RoundaboutClipBoundaryLoopCount) > 0
        assert int(shoulder_preview.SkippedRoundaboutSectionCount) == 0
        assert int(shoulder_preview.SkippedRoundaboutStripTriangleCount) == 0
        assert int(shoulder_preview.SurfacePatchCount) > 0
    finally:
        App.closeDocument(doc.Name)


def test_roundabout_side_slope_is_not_an_applied_section_guided_review_row() -> None:
    doc = App.newDocument("CRV1RoundaboutSideSlopeGuidedReviewClip")
    try:
        create_intersection_preset_sources(doc, preset_label="Roundabout - Single Lane", radius=20.0)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)

        rows = corridor_subassembly_kind_guided_review_rows(doc)

        assert all(str(row.get("step_id", "")) != "subassembly_kind:side_slope" for row in rows)
        assert doc.getObject("ReviewIssueSubassemblyKind_side_slope") is None
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
