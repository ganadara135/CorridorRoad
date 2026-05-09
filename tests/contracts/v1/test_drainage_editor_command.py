import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, V1_TREE_DRAINAGE, ensure_project_tree
from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_drainage_editor import (
    CmdV1DrainageEditor,
    V1DrainageEditorTaskPanel,
    drainage_preset_model_from_document,
    drainage_preset_names,
    region_model_ids,
    run_v1_drainage_editor_command,
    starter_drainage_model_from_document,
)
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageElementRow, DrainageModel
from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.objects.obj_drainage import (
    create_or_update_v1_drainage_model_object,
    find_v1_drainage_model,
    to_drainage_model,
)
from freecad.Corridor_Road.v1.objects.obj_region import create_or_update_v1_region_model_object

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


def test_drainage_editor_resources_are_real_editor_entry() -> None:
    resources = CmdV1DrainageEditor().GetResources()

    assert resources["MenuText"] == "Drainage"
    assert "drainage design intent" in resources["ToolTip"]


def test_starter_drainage_model_has_element_policy_and_collection() -> None:
    model = starter_drainage_model_from_document()

    assert model.drainage_model_id == "drainage:main"
    assert model.element_rows[0].drainage_element_id == "drainage:side-ditch-right"
    assert model.element_rows[0].side == "right"
    assert model.element_rows[0].assembly_component_ref == "ditch:right"
    assert model.policy_rows[0].policy_set_id == "drainage-policy:lined-concrete"
    assert model.collection_region_rows[0].collection_region_id == "drainage-collection:main"


def test_drainage_presets_offer_practical_source_sets() -> None:
    names = drainage_preset_names()

    assert "Roadside Ditch" in names
    assert "Dual Side Ditches" in names
    assert "Culvert Crossing" in names

    model = drainage_preset_model_from_document("Culvert Crossing")

    assert model.drainage_model_id == "drainage:main"
    assert [row.drainage_element_id for row in model.element_rows] == [
        "drainage:side-ditch-left",
        "drainage:side-ditch-right",
        "drainage:culvert-01",
    ]
    assert model.element_rows[2].element_kind == "culvert_reference"
    assert model.element_rows[2].structure_ref == "structure:culvert-01"
    assert {row.policy_set_id for row in model.policy_rows} == {
        "drainage-policy:roadside-ditch",
        "drainage-policy:cross-drain",
    }


def test_drainage_editor_panel_loads_starter_and_applies_model() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1DrainageEditorApplyTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)

        assert panel._element_table.rowCount() == 1
        assert panel._policy_table.rowCount() == 1
        assert panel._collection_table.rowCount() == 1
        assert panel._element_table.item(0, 0).text() == "side-ditch-right"
        assert panel._element_table.horizontalHeaderItem(2).text() == "Region"
        assert panel._element_table.horizontalHeaderItem(3).text() == "Side"
        assert panel._element_table.horizontalHeaderItem(6).text() == "Assembly"
        assert panel._element_table.horizontalHeaderItem(7).text() == "Policy"
        assert panel._element_table.horizontalHeaderItem(8).text() == "Structure"
        assert panel._element_table.item(0, 7).text() == "lined-concrete"
        assert panel._element_table.item(0, 8).text() == ""
        assert not bool(panel._element_table.item(0, 8).flags() & QtCore.Qt.ItemIsEnabled)
        assert panel._policy_table.item(0, 0).text() == "lined-concrete"

        assert panel._apply(close_after=False) is True
        obj = find_v1_drainage_model(doc)
        model = to_drainage_model(obj)
        tree = ensure_project_tree(project, include_references=False)

        assert obj is not None
        assert obj.Name in {child.Name for child in tree[V1_TREE_DRAINAGE].Group}
        assert model.element_rows[0].policy_set_ref == "drainage-policy:lined-concrete"
        assert model.element_rows[0].side == "right"
        assert model.element_rows[0].assembly_component_ref == "ditch:right"
        assert obj.ValidationStatus == "ok"
        assert "Applied to:" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_ditch_disables_structure_cell() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageEditorDitchStructureCellTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)
        kind_combo = panel._element_table.cellWidget(0, 1)
        structure_item = panel._element_table.item(0, 8)

        assert structure_item is not None
        assert kind_combo.currentText() == "ditch"
        assert not bool(structure_item.flags() & QtCore.Qt.ItemIsEnabled)
        assert structure_item.text() == ""

        kind_combo.setCurrentText("culvert_reference")
        structure_item = panel._element_table.item(0, 8)
        assert bool(structure_item.flags() & QtCore.Qt.ItemIsEnabled)
        structure_item.setText("structure:culvert-01")

        model = panel._model_from_tables()
        assert model.element_rows[0].structure_ref == "structure:culvert-01"

        kind_combo.setCurrentText("ditch")
        structure_item = panel._element_table.item(0, 8)
        assert not bool(structure_item.flags() & QtCore.Qt.ItemIsEnabled)
        assert structure_item.text() == ""
        assert panel._model_from_tables().element_rows[0].structure_ref == ""
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_add_buttons_follow_active_tab() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageEditorTabActionsTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)

        assert panel._add_element_button.isHidden() is False
        assert panel._add_left_ditch_button.isHidden() is False
        assert panel._add_right_ditch_button.isHidden() is False
        assert panel._add_policy_button.isHidden() is True
        assert panel._add_collection_button.isHidden() is True

        panel._tabs.setCurrentIndex(1)
        assert panel._add_element_button.isHidden() is True
        assert panel._add_left_ditch_button.isHidden() is True
        assert panel._add_right_ditch_button.isHidden() is True
        assert panel._add_policy_button.isHidden() is False
        assert panel._add_collection_button.isHidden() is True

        panel._tabs.setCurrentIndex(2)
        assert panel._add_element_button.isHidden() is True
        assert panel._add_left_ditch_button.isHidden() is True
        assert panel._add_right_ditch_button.isHidden() is True
        assert panel._add_policy_button.isHidden() is True
        assert panel._add_collection_button.isHidden() is False
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_panel_loads_existing_model() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1DrainageEditorLoadExistingTest")
    try:
        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-1",
                drainage_model_id="drainage:main",
                element_rows=[
                    DrainageElementRow(
                        drainage_element_id="drainage:side-ditch-left",
                        element_kind="ditch",
                        side="left",
                        region_ref="region:drainage",
                        assembly_component_ref="ditch:left",
                        station_start=10.0,
                        station_end=80.0,
                    )
                ],
            ),
        )

        panel = V1DrainageEditorTaskPanel(document=doc)

        assert panel._element_table.rowCount() == 1
        assert panel._element_table.item(0, 0).text() == "side-ditch-left"
        assert panel._element_table.cellWidget(0, 2).currentText() == "region:drainage"
        assert panel._element_table.cellWidget(0, 3).currentText() == "left"
        assert panel._element_table.item(0, 4).text() == "10.000"
        assert panel._element_table.item(0, 6).text() == "ditch:left"
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_element_region_column_uses_region_combo() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1DrainageEditorRegionComboTest")
    try:
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=RegionModel(
                schema_version=1,
                project_id="proj-1",
                region_model_id="regions:main",
                region_rows=[
                    RegionRow("region:normal", 0.0, 40.0),
                    RegionRow("region:drainage", 40.0, 100.0),
                ],
            ),
        )
        panel = V1DrainageEditorTaskPanel(document=doc)
        region_combo = panel._element_table.cellWidget(0, 2)

        assert region_model_ids(doc) == ["region:normal", "region:drainage"]
        assert region_combo is not None
        assert [region_combo.itemText(index) for index in range(region_combo.count())] == [
            "",
            "region:normal",
            "region:drainage",
        ]
        region_combo.setCurrentText("region:drainage")
        model = panel._model_from_tables()

        assert model.element_rows[0].region_ref == "region:drainage"
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_validate_checks_region_station_boundary() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1DrainageEditorRegionBoundaryValidationTest")
    try:
        create_or_update_v1_region_model_object(
            doc,
            project=project,
            region_model=RegionModel(
                schema_version=1,
                project_id="proj-1",
                region_model_id="regions:main",
                region_rows=[RegionRow("region:drainage", 20.0, 60.0)],
            ),
        )
        panel = V1DrainageEditorTaskPanel(document=doc)
        panel._element_table.cellWidget(0, 2).setCurrentText("region:drainage")
        panel._element_table.item(0, 4).setText("10.000")
        panel._element_table.item(0, 5).setText("50.000")

        panel._validate()

        assert "drainage_element_outside_region_station_range" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_apply_blocks_error_validation() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageEditorValidationBlockTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)
        panel._element_table.item(0, 4).setText("100.000")
        panel._element_table.item(0, 5).setText("10.000")

        assert panel._apply(close_after=False) is False
        assert find_v1_drainage_model(doc) is None
        assert "invalid_drainage_element_station_range" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_adds_side_specific_ditch_defaults() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageEditorSideDefaultsTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)
        panel._element_table.setRowCount(0)

        panel._add_ditch_row("left")
        model = panel._model_from_tables()

        assert model.element_rows[0].drainage_element_id == "drainage:side-ditch-left"
        assert panel._element_table.item(0, 0).text() == "side-ditch-left"
        assert model.element_rows[0].side == "left"
        assert model.element_rows[0].assembly_component_ref == "ditch:left"
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_loads_selected_preset_into_tables() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageEditorPresetLoadTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)
        panel._preset_combo.setCurrentText("Dual Side Ditches")

        panel._load_selected_preset()
        model = panel._model_from_tables()

        assert panel._element_table.item(0, 0).text() == "side-ditch-left"
        assert panel._policy_table.item(0, 0).text() == "lined-concrete"
        assert [row.side for row in model.element_rows] == ["left", "right"]
        assert [row.assembly_component_ref for row in model.element_rows] == ["ditch:left", "ditch:right"]
        assert panel._policy_table.rowCount() == 1
        assert "Drainage preset loaded: Dual Side Ditches" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_side_specific_ditch_defaults_keep_ids_unique() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageEditorUniqueSideDefaultsTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)

        panel._add_ditch_row("right")
        model = panel._model_from_tables()

        assert [row.drainage_element_id for row in model.element_rows] == [
            "drainage:side-ditch-right",
            "drainage:side-ditch-right:2",
        ]
    finally:
        App.closeDocument(doc.Name)


def test_run_v1_drainage_editor_command_returns_panel() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageEditorRunCommandTest")
    try:
        panel = run_v1_drainage_editor_command(document=doc)

        assert isinstance(panel, V1DrainageEditorTaskPanel)
        assert panel.document == doc
    finally:
        App.closeDocument(doc.Name)
