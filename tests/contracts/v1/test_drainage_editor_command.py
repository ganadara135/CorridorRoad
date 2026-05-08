import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, V1_TREE_DRAINAGE, ensure_project_tree
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_drainage_editor import (
    CmdV1DrainageEditor,
    V1DrainageEditorTaskPanel,
    run_v1_drainage_editor_command,
    starter_drainage_model_from_document,
)
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageElementRow, DrainageModel
from freecad.Corridor_Road.v1.objects.obj_drainage import (
    create_or_update_v1_drainage_model_object,
    find_v1_drainage_model,
    to_drainage_model,
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


def test_drainage_editor_panel_loads_starter_and_applies_model() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1DrainageEditorApplyTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)

        assert panel._element_table.rowCount() == 1
        assert panel._policy_table.rowCount() == 1
        assert panel._collection_table.rowCount() == 1

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
        assert panel._element_table.item(0, 0).text() == "drainage:side-ditch-left"
        assert panel._element_table.cellWidget(0, 2).currentText() == "left"
        assert panel._element_table.item(0, 3).text() == "10.000"
        assert panel._element_table.item(0, 5).text() == "region:drainage"
        assert panel._element_table.item(0, 6).text() == "ditch:left"
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_apply_blocks_error_validation() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageEditorValidationBlockTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)
        panel._element_table.item(0, 3).setText("100.000")
        panel._element_table.item(0, 4).setText("10.000")

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
        assert model.element_rows[0].side == "left"
        assert model.element_rows[0].assembly_component_ref == "ditch:left"
        assert model.element_rows[0].offset_rule == "left shoulder ditch"
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
