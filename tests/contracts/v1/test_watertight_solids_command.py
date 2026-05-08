import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, V1_TREE_WATERTIGHT_SOLIDS, ensure_project_tree
from freecad.Corridor_Road.init_gui import corridorroad_workflow_toolbar_commands
from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets
from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.models.result.corridor_model import CorridorModel, CorridorSamplingPolicy, CorridorStationRow
from freecad.Corridor_Road.v1.models.result.surface_model import SurfaceModel, SurfaceRow
from freecad.Corridor_Road.v1.objects.obj_applied_section import create_or_update_v1_applied_section_set_object
from freecad.Corridor_Road.v1.objects.obj_corridor import create_or_update_v1_corridor_model_object
from freecad.Corridor_Road.v1.objects.obj_surface import create_or_update_v1_surface_model_object
from freecad.Corridor_Road.v1.commands.cmd_watertight_solids import (
    CmdV1WatertightSolids,
    V1WatertightSolidsTaskPanel,
    WATERTIGHT_SOLIDS_BLOCKED_MESSAGE,
    WATERTIGHT_SOLIDS_COMMAND_ID,
    discover_watertight_solid_targets,
    watertight_solid_prerequisite_status,
)

_QAPP = None


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def _new_project_doc(name: str):
    doc = App.newDocument(name)
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def _sample_sections(*, include_component: bool = False) -> AppliedSectionSet:
    component_rows = [
        AppliedSectionComponentRow(
            "pavement:base",
            "pavement_layer",
            side="center",
            width=6.0,
            thickness=0.25,
            material="asphalt",
        )
    ] if include_component else []
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
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                component_rows=list(component_rows),
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:20",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=20.0,
                frame=AppliedSectionFrame(station=20.0, x=20.0, y=0.0, z=11.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                component_rows=list(component_rows),
            ),
        ],
    )


def _sample_corridor() -> CorridorModel:
    return CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        applied_section_set_ref="sections:main",
        surface_build_refs=["surface:main"],
        sampling_policy=CorridorSamplingPolicy("corridor:main:sampling", 20.0),
        station_rows=[
            CorridorStationRow("station:0", 0.0, source_reason="section:0"),
            CorridorStationRow("station:20", 20.0, source_reason="section:20"),
        ],
    )


def _sample_surface() -> SurfaceModel:
    return SurfaceModel(
        schema_version=1,
        project_id="proj-1",
        surface_model_id="surface:main",
        corridor_id="corridor:main",
        surface_rows=[
            SurfaceRow("corridor:main:design", "design_surface", "corridor:main:design:tin"),
            SurfaceRow("corridor:main:subgrade", "subgrade_surface", "corridor:main:subgrade:tin"),
        ],
    )


def _populate_ready_build_corridor_outputs(doc, project, *, include_component: bool = False) -> None:
    create_or_update_v1_applied_section_set_object(
        doc,
        project=project,
        applied_section_set=_sample_sections(include_component=include_component),
    )
    create_or_update_v1_corridor_model_object(doc, project=project, corridor_model=_sample_corridor())
    create_or_update_v1_surface_model_object(doc, project=project, surface_model=_sample_surface())


def test_watertight_solids_resources_are_final_v1_stage() -> None:
    resources = CmdV1WatertightSolids().GetResources()

    assert resources["MenuText"] == "Watertight Solids"
    assert "topology-first" in resources["ToolTip"]


def test_watertight_solids_toolbar_is_after_ai_assist() -> None:
    commands = corridorroad_workflow_toolbar_commands()

    assert commands[-2:] == ["CorridorRoad_AIAssist", WATERTIGHT_SOLIDS_COMMAND_ID]


def test_watertight_solids_prerequisites_block_without_build_corridor() -> None:
    doc = App.newDocument("V1WatertightSolidsMissingPrereqTest")
    try:
        status = watertight_solid_prerequisite_status(doc)

        assert status.ready is False
        assert WATERTIGHT_SOLIDS_BLOCKED_MESSAGE in status.messages
        assert status.applied_sections_ready is False
        assert status.corridor_model_ready is False
        assert status.surface_model_ready is False
        assert discover_watertight_solid_targets(doc).target_rows[0].readiness_status == "blocked"
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_prerequisites_ready_after_build_corridor_objects_exist() -> None:
    doc = App.newDocument("V1WatertightSolidsReadyPrereqTest")
    try:
        doc.addObject("App::FeaturePython", "V1AppliedSectionSet")
        doc.addObject("App::FeaturePython", "V1CorridorModel")
        doc.addObject("App::FeaturePython", "V1SurfaceModel")

        status = watertight_solid_prerequisite_status(doc)
        target_model = discover_watertight_solid_targets(doc)

        assert status.ready is True
        assert status.applied_sections_ready is True
        assert status.corridor_model_ready is True
        assert status.surface_model_ready is True
        assert target_model.target_rows[0].target_family == "road_body_envelope"
        assert target_model.target_rows[0].readiness_status == "blocked"
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_panel_shows_blocked_state_and_disables_build_buttons() -> None:
    _ensure_qapp()
    doc = App.newDocument("V1WatertightSolidsPanelBlockedTest")
    try:
        panel = V1WatertightSolidsTaskPanel(document=doc)

        assert WATERTIGHT_SOLIDS_BLOCKED_MESSAGE in panel._status.toPlainText()
        assert panel._target_table.rowCount() == 1
        assert panel._validate_button.isEnabled() is False
        assert panel._build_selected_button.isEnabled() is False
        assert panel._build_enabled_button.isEnabled() is False
        assert panel._show_button.isEnabled() is False
        assert panel._hide_button.isEnabled() is False
        assert panel._focus_button.isEnabled() is False
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_panel_selects_available_target_and_tracks_enabled_state() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsPanelTargetSelectionTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)

        panel = V1WatertightSolidsTaskPanel(document=doc)

        assert panel._target_table.rowCount() == 1
        assert panel._validate_button.isEnabled() is False

        panel._target_table.selectRow(0)
        assert panel._selected_target_id == "solid-target:road-body-envelope"
        assert panel._validate_button.isEnabled() is True
        assert panel._build_selected_button.isEnabled() is False
        assert panel._build_enabled_button.isEnabled() is False

        enabled_item = panel._target_table.item(0, 0)
        enabled_item.setCheckState(QtCore.Qt.Checked)

        assert panel._target_state_by_id["solid-target:road-body-envelope"].enabled is True
        assert "Enabled targets: 1" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_panel_validate_builds_profile_and_edge_network_counts() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsPanelValidateTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)

        panel = V1WatertightSolidsTaskPanel(document=doc)
        panel._target_table.selectRow(0)

        panel._validate_button.click()

        state = panel._target_state_by_id["solid-target:road-body-envelope"]
        assert state.validation_status == "ok"
        assert state.profile_count == 2
        assert state.face_count == 6
        assert state.edge_count == 12
        assert panel._target_table.item(0, 5).text() == "ok"
        assert panel._target_table.item(0, 6).text() == "2"
        assert panel._target_table.item(0, 7).text() == "6"
        assert panel._target_table.item(0, 8).text() == "12"
        assert "Selected validation: ok; profiles=2; faces=6; edges=12" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_panel_build_selected_creates_output_object() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsPanelBuildSelectedTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)

        panel = V1WatertightSolidsTaskPanel(document=doc)
        panel._target_table.selectRow(0)
        panel._validate_button.click()

        assert panel._build_selected_button.isEnabled() is True
        panel._build_selected_button.click()

        state = panel._target_state_by_id["solid-target:road-body-envelope"]
        obj = doc.getObject(state.output_object_ref)
        assert state.build_status == "built"
        assert state.volume > 0.0
        assert obj is not None
        assert obj.V1ObjectType == "V1WatertightSolidOutput"
        assert obj.SolidCount == 1
        assert obj.Shape.Volume > 0.0
        assert list(obj.TargetIds) == ["solid-target:road-body-envelope"]
        tree = ensure_project_tree(project, include_references=False)
        assert obj.Name in _group_names(tree[V1_TREE_WATERTIGHT_SOLIDS])
        assert panel._target_table.item(0, 9).text() == "built"
        assert panel._target_table.item(0, 10).text() != "-"
        assert panel._target_table.item(0, 11).text() == state.output_object_ref
        assert panel._show_button.isEnabled() is True
        assert panel._hide_button.isEnabled() is True
        assert panel._focus_button.isEnabled() is True
    finally:
        App.closeDocument(doc.Name)


def _group_names(folder) -> set[str]:
    return {str(getattr(obj, "Name", "") or "") for obj in list(getattr(folder, "Group", []) or [])}


def test_watertight_solids_panel_show_hide_focus_controls_built_output_object() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsPanelShowHideFocusTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)

        panel = V1WatertightSolidsTaskPanel(document=doc)
        panel._target_table.selectRow(0)
        panel._validate_button.click()
        panel._build_selected_button.click()

        state = panel._target_state_by_id["solid-target:road-body-envelope"]
        obj = doc.getObject(state.output_object_ref)
        assert obj is not None

        panel._hide_button.click()
        if getattr(obj, "ViewObject", None) is not None:
            assert obj.ViewObject.Visibility is False
        assert f"Hidden solid: {obj.Name}" in panel._status.toPlainText()

        panel._show_button.click()
        if getattr(obj, "ViewObject", None) is not None:
            assert obj.ViewObject.Visibility is True
        assert f"Shown solid: {obj.Name}" in panel._status.toPlainText()

        if getattr(obj, "ViewObject", None) is not None:
            obj.ViewObject.Visibility = False
        panel._focus_button.click()
        if getattr(obj, "ViewObject", None) is not None:
            assert obj.ViewObject.Visibility is True
        assert f"Focused solid: {obj.Name}" in panel._status.toPlainText()

        if getattr(obj, "ViewObject", None) is not None:
            obj.ViewObject.Visibility = False
        panel._focus_target_row_output(panel._target_table.item(0, 1))
        if getattr(obj, "ViewObject", None) is not None:
            assert obj.ViewObject.Visibility is True
        assert panel._selected_target_id == "solid-target:road-body-envelope"
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_panel_build_enabled_builds_each_enabled_target_independently() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsPanelBuildEnabledTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project, include_component=True)

        panel = V1WatertightSolidsTaskPanel(document=doc)

        assert panel._target_table.rowCount() == 2
        assert panel._build_enabled_button.isEnabled() is False
        for row_index in range(panel._target_table.rowCount()):
            panel._target_table.item(row_index, 0).setCheckState(QtCore.Qt.Checked)

        assert panel._build_enabled_button.isEnabled() is True
        panel._build_enabled_button.click()

        road_state = panel._target_state_by_id["solid-target:road-body-envelope"]
        component_state = panel._target_state_by_id["solid-target:pavement-layer:pavement-base"]
        assert road_state.build_status == "built"
        assert component_state.build_status == "built"
        assert road_state.volume > 0.0
        assert component_state.volume > 0.0
        assert doc.getObject(road_state.output_object_ref) is not None
        assert doc.getObject(component_state.output_object_ref) is not None
        assert road_state.output_object_ref != component_state.output_object_ref
        tree = ensure_project_tree(project, include_references=False)
        names = _group_names(tree[V1_TREE_WATERTIGHT_SOLIDS])
        assert road_state.output_object_ref in names
        assert component_state.output_object_ref in names
        assert "Build Enabled summary: built=2; failed=0; targets=2; volume=" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)
