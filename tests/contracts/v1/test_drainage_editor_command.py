import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, V1_TREE_DRAINAGE, ensure_project_tree
from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_drainage_editor import (
    CmdV1DrainageEditor,
    V1DrainageEditorTaskPanel,
    drainage_preset_model_from_document,
    drainage_preset_names,
    run_v1_drainage_editor_command,
    starter_drainage_model_from_document,
)
from freecad.Corridor_Road.v1.commands.cmd_structure_editor import structure_preset_model_from_document
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageElementRow, DrainageModel
from freecad.Corridor_Road.v1.models.source.structure_model import (
    StructureConnectionPoint,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from freecad.Corridor_Road.v1.objects.obj_drainage import (
    create_or_update_v1_drainage_model_object,
    find_v1_drainage_model,
    to_drainage_model,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_structure import create_or_update_v1_structure_model_object

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


def test_starter_drainage_model_has_element_policy_and_flow_route() -> None:
    model = starter_drainage_model_from_document()

    assert model.drainage_model_id == "drainage:main"
    assert model.element_rows[0].drainage_element_id == "drainage:side-ditch-right"
    assert model.element_rows[1].drainage_element_id == "drainage:outfall-main"
    assert model.element_rows[0].side == "right"
    assert model.element_rows[0].assembly_component_ref == "ditch:right"
    assert model.policy_rows[0].policy_set_id == "drainage-policy:lined-concrete"
    assert model.flow_route_rows[0].flow_route_id == "flow-route:flowId-01"
    assert model.flow_route_rows[0].to_element_ref == "drainage:outfall-main"


def test_drainage_presets_offer_practical_source_sets() -> None:
    names = drainage_preset_names()

    assert "Roadside Ditch" in names
    assert "Dual Side Ditches" in names
    assert "Culvert Crossing" in names
    assert "Drainage Structures Flow" in names

    model = drainage_preset_model_from_document("Culvert Crossing")

    assert model.drainage_model_id == "drainage:main"
    assert [row.drainage_element_id for row in model.element_rows[:3]] == [
        "drainage:side-ditch-left",
        "drainage:side-ditch-right",
        "drainage:culvert-01",
    ]
    assert model.element_rows[2].element_kind == "culvert_reference"
    assert model.element_rows[2].structure_ref == ""
    assert {row.policy_set_id for row in model.policy_rows} == {
        "drainage-policy:roadside-ditch",
        "drainage-policy:cross-drain",
    }

    model = drainage_preset_model_from_document("Drainage Structures Flow")

    assert [row.drainage_element_id for row in model.element_rows] == [
        "drainage:side-ditch-right-01",
        "drainage:side-ditch-right-02",
        "drainage:side-ditch-right-03",
        "drainage:inlet-01",
        "drainage:inlet-02",
        "drainage:inlet-03",
        "drainage:culvert-01",
        "drainage:outlet-01",
    ]
    assert [row.structure_ref for row in model.element_rows] == [
        "",
        "",
        "",
        "structure:inlet-01",
        "structure:inlet-02",
        "structure:inlet-03",
        "structure:culvert-01",
        "structure:outlet-01",
    ]
    assert [row.connection_point_ref for row in model.element_rows] == [
        "",
        "",
        "",
        "connection:inlet-01:pipe-out",
        "connection:inlet-02:pipe-out",
        "connection:inlet-03:pipe-out",
        "",
        "connection:outlet-01:pipe-in",
    ]
    assert [row.flow_route_id for row in model.flow_route_rows] == [
        "flow-route:flowId-01",
        "flow-route:flowId-02",
        "flow-route:flowId-03",
        "flow-route:flowId-04",
        "flow-route:flowId-05",
        "flow-route:flowId-06",
        "flow-route:flowId-07",
    ]
    assert model.flow_route_rows[0].from_element_ref == "drainage:side-ditch-right-01"
    assert model.flow_route_rows[0].to_element_ref == "drainage:inlet-01"
    assert model.flow_route_rows[1].from_element_ref == "drainage:side-ditch-right-02"
    assert model.flow_route_rows[1].to_element_ref == "drainage:inlet-02"
    assert model.flow_route_rows[2].from_element_ref == "drainage:side-ditch-right-03"
    assert model.flow_route_rows[2].to_element_ref == "drainage:inlet-03"
    assert model.flow_route_rows[3].from_element_ref == "drainage:inlet-01"
    assert model.flow_route_rows[3].to_element_ref == "drainage:inlet-02"
    assert model.flow_route_rows[4].from_element_ref == "drainage:inlet-02"
    assert model.flow_route_rows[4].to_element_ref == "drainage:inlet-03"
    assert model.flow_route_rows[5].from_element_ref == "drainage:inlet-03"
    assert model.flow_route_rows[5].to_element_ref == "drainage:culvert-01"
    assert model.flow_route_rows[6].from_element_ref == "drainage:culvert-01"
    assert model.flow_route_rows[6].to_element_ref == "drainage:outlet-01"
    assert [row.outlet_ref for row in model.flow_route_rows] == ["", "", "", "", "", "", "drainage:outlet-01"]


def test_drainage_editor_panel_loads_starter_and_applies_model() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1DrainageEditorApplyTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)

        assert panel._element_table.rowCount() == 2
        assert panel._policy_table.rowCount() == 1
        assert panel._flow_route_table.rowCount() == 1
        assert panel._element_table.item(0, 0).text() == "side-ditch-right"
        element_headers = [
            panel._element_table.horizontalHeaderItem(index).text()
            for index in range(panel._element_table.columnCount())
        ]
        assert "Region" not in element_headers
        assert panel._element_table.horizontalHeaderItem(2).text() == "Side"
        assert panel._element_table.horizontalHeaderItem(5).text() == "Assembly"
        assert panel._element_table.horizontalHeaderItem(6).text() == "Policy"
        assert panel._element_table.horizontalHeaderItem(7).text() == "Structure Ref"
        assert panel._element_table.horizontalHeaderItem(8).text() == "Connection Point"
        assert panel._tabs.tabText(2) == "Flow Routes"
        assert panel._flow_route_table.horizontalHeaderItem(0).text() == "Flow Route ID"
        assert panel._flow_route_table.horizontalHeaderItem(3).text() == "Outlet"
        assert panel._add_flow_route_button.text() == "Add Flow Route"
        assert panel._flow_route_table.item(0, 0).text() == "flowId-01"
        assert panel._flow_route_table.cellWidget(0, 1).currentText() == "side-ditch-right"
        assert panel._flow_route_table.cellWidget(0, 2).currentText() == "outfall-main"
        assert panel._flow_route_table.cellWidget(0, 3).currentText() == "outfall-main"
        assert "flowId-01: side-ditch-right -> outfall-main" in panel._flow_route_preview.text()
        assert panel._element_table.cellWidget(0, 6).currentText() == "lined-concrete"
        assert panel._element_table.cellWidget(0, 7).currentText() == ""
        assert not panel._element_table.cellWidget(0, 7).isEnabled()
        assert panel._element_table.cellWidget(0, 8).currentText() == ""
        assert not panel._element_table.cellWidget(0, 8).isEnabled()
        assert panel._element_table.item(1, 0).text() == "outfall-main"
        assert panel._element_table.cellWidget(1, 7).currentText() == ""
        assert "main" not in [
            panel._element_table.cellWidget(1, 7).itemText(index)
            for index in range(panel._element_table.cellWidget(1, 7).count())
        ]
        assert panel._element_table.item(1, 5).text() == ""
        assert not bool(panel._element_table.item(1, 5).flags() & QtCore.Qt.ItemIsEnabled)
        assert panel._policy_table.item(0, 0).text() == "lined-concrete"
        policy_items = [
            panel._element_table.cellWidget(0, 6).itemText(index)
            for index in range(panel._element_table.cellWidget(0, 6).count())
        ]
        assert "lined-concrete" in policy_items

        assert panel._apply(close_after=False) is True
        obj = find_v1_drainage_model(doc)
        model = to_drainage_model(obj)
        tree = ensure_project_tree(project, include_references=False)

        assert obj is not None
        assert obj.Name in {child.Name for child in tree[V1_TREE_DRAINAGE].Group}
        assert model.element_rows[0].policy_set_ref == "drainage-policy:lined-concrete"
        assert model.element_rows[0].side == "right"
        assert model.element_rows[0].assembly_component_ref == "ditch:right"
        assert model.element_rows[1].structure_ref == ""
        assert obj.ValidationStatus == "ok"
        assert model.flow_route_rows[0].from_element_ref == "drainage:side-ditch-right"
        assert model.flow_route_rows[0].to_element_ref == "drainage:outfall-main"
        assert model.flow_route_rows[0].outlet_ref == "drainage:outfall-main"
        assert "Applied to:" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_ditch_disables_structure_cell() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageEditorDitchStructureCellTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)
        kind_combo = panel._element_table.cellWidget(0, 1)
        assembly_item = panel._element_table.item(0, 5)
        structure_combo = panel._element_table.cellWidget(0, 7)
        connection_combo = panel._element_table.cellWidget(0, 8)

        assert assembly_item is not None
        assert structure_combo is not None
        assert kind_combo.currentText() == "ditch"
        assert bool(assembly_item.flags() & QtCore.Qt.ItemIsEnabled)
        assert not structure_combo.isEnabled()
        assert structure_combo.currentText() == ""
        assert not connection_combo.isEnabled()
        assert connection_combo.currentText() == ""

        kind_combo.setCurrentText("culvert_reference")
        assembly_item = panel._element_table.item(0, 5)
        structure_combo = panel._element_table.cellWidget(0, 7)
        connection_combo = panel._element_table.cellWidget(0, 8)
        assert not bool(assembly_item.flags() & QtCore.Qt.ItemIsEnabled)
        assert assembly_item.text() == ""
        assert structure_combo.isEnabled()
        assert connection_combo.isEnabled()
        structure_combo.setCurrentText("culvert-01")

        model = panel._model_from_tables()
        assert model.element_rows[0].assembly_component_ref == ""
        assert model.element_rows[0].structure_ref == "structure:culvert-01"

        kind_combo.setCurrentText("ditch")
        assembly_item = panel._element_table.item(0, 5)
        structure_combo = panel._element_table.cellWidget(0, 7)
        connection_combo = panel._element_table.cellWidget(0, 8)
        assert bool(assembly_item.flags() & QtCore.Qt.ItemIsEnabled)
        assembly_item.setText("ditch:right")
        assert panel._model_from_tables().element_rows[0].assembly_component_ref == "ditch:right"
        assert not structure_combo.isEnabled()
        assert structure_combo.currentText() == ""
        assert not connection_combo.isEnabled()
        assert connection_combo.currentText() == ""
        assert panel._model_from_tables().element_rows[0].structure_ref == ""
        assert panel._model_from_tables().element_rows[0].connection_point_ref == ""
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_structure_ref_uses_structure_id_combo() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1DrainageEditorStructureRefComboTest")
    try:
        create_or_update_v1_structure_model_object(
            doc,
            project=project,
            structure_model=StructureModel(
                schema_version=1,
                project_id="proj-1",
                structure_model_id="structures:main",
                structure_rows=[
                    StructureRow(
                        structure_id="structure:culvert-01",
                        structure_kind="culvert",
                        structure_role="crossing",
                        placement=StructurePlacement(
                            placement_id="placement:culvert-01",
                            alignment_id="alignment:main",
                            station_start=40.0,
                            station_end=60.0,
                        ),
                    )
                ],
                connection_point_rows=[
                    StructureConnectionPoint(
                        connection_point_id="connection:culvert-01:upstream",
                        structure_ref="structure:culvert-01",
                        point_role="upstream",
                        station=40.0,
                        offset=0.0,
                    ),
                    StructureConnectionPoint(
                        connection_point_id="connection:culvert-01:downstream",
                        structure_ref="structure:culvert-01",
                        point_role="downstream",
                        station=60.0,
                        offset=0.0,
                    ),
                ],
            ),
        )
        panel = V1DrainageEditorTaskPanel(document=doc)
        kind_combo = panel._element_table.cellWidget(0, 1)
        kind_combo.setCurrentText("culvert_reference")
        structure_combo = panel._element_table.cellWidget(0, 7)
        connection_combo = panel._element_table.cellWidget(0, 8)
        structure_items = [structure_combo.itemText(index) for index in range(structure_combo.count())]

        assert structure_combo.isEnabled()
        assert "culvert-01" in structure_items

        structure_combo.setCurrentText("culvert-01")
        connection_combo = panel._element_table.cellWidget(0, 8)
        connection_items = [connection_combo.itemText(index) for index in range(connection_combo.count())]
        assert "upstream" in connection_items
        connection_combo.setCurrentText("upstream")
        model = panel._model_from_tables()

        assert model.element_rows[0].structure_ref == "structure:culvert-01"
        assert model.element_rows[0].connection_point_ref == "connection:culvert-01:upstream"
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
        assert panel._add_flow_route_button.isHidden() is True

        panel._tabs.setCurrentIndex(1)
        assert panel._add_element_button.isHidden() is True
        assert panel._add_left_ditch_button.isHidden() is True
        assert panel._add_right_ditch_button.isHidden() is True
        assert panel._add_policy_button.isHidden() is False
        assert panel._add_flow_route_button.isHidden() is True

        panel._tabs.setCurrentIndex(2)
        assert panel._add_element_button.isHidden() is True
        assert panel._add_left_ditch_button.isHidden() is True
        assert panel._add_right_ditch_button.isHidden() is True
        assert panel._add_policy_button.isHidden() is True
        assert panel._add_flow_route_button.isHidden() is False
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_flow_route_link_cells_use_element_combos() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageEditorFlowRouteComboTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)
        panel._add_ditch_row("left")

        from_combo = panel._flow_route_table.cellWidget(0, 1)
        to_combo = panel._flow_route_table.cellWidget(0, 2)
        outlet_combo = panel._flow_route_table.cellWidget(0, 3)
        from_items = [from_combo.itemText(index) for index in range(from_combo.count())]
        to_items = [to_combo.itemText(index) for index in range(to_combo.count())]

        assert "side-ditch-right" in from_items
        assert "side-ditch-left" in from_items
        assert "side-ditch-left" in to_items
        assert outlet_combo.isEnabled() is True
        assert panel._flow_route_table.columnWidth(1) >= 150
        assert panel._flow_route_table.columnWidth(2) >= 150
        assert from_combo.minimumWidth() >= 150
        assert to_combo.minimumWidth() >= 150

        to_combo.setCurrentText("side-ditch-right")
        assert panel._model_from_tables().flow_route_rows[0].from_element_ref != panel._model_from_tables().flow_route_rows[0].to_element_ref
        to_combo.setCurrentText("side-ditch-left")
        model = panel._model_from_tables()

        assert model.flow_route_rows[0].to_element_ref == "drainage:side-ditch-left"
        assert model.flow_route_rows[0].outlet_ref == ""
        assert panel._flow_route_table.cellWidget(0, 3).isEnabled() is False
        assert "side-ditch-right -> side-ditch-left" in panel._flow_route_preview.text()

        to_combo.setCurrentText("outfall-main")
        model = panel._model_from_tables()

        assert model.flow_route_rows[0].to_element_ref == "drainage:outfall-main"
        assert model.flow_route_rows[0].outlet_ref == "drainage:outfall-main"
        assert panel._flow_route_table.cellWidget(0, 3).isEnabled() is True
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_element_policy_uses_policy_id_combo() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageEditorElementPolicyComboTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)
        panel._policy_table.item(0, 0).setText("custom-policy")

        policy_combo = panel._element_table.cellWidget(0, 6)
        policy_items = [policy_combo.itemText(index) for index in range(policy_combo.count())]

        assert "custom-policy" in policy_items

        policy_combo.setCurrentText("custom-policy")
        model = panel._model_from_tables()

        assert model.policy_rows[0].policy_set_id == "drainage-policy:custom-policy"
        assert model.element_rows[0].policy_set_ref == "drainage-policy:custom-policy"
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
        assert panel._element_table.cellWidget(0, 2).currentText() == "left"
        assert panel._element_table.item(0, 3).text() == "10.000"
        assert panel._element_table.item(0, 5).text() == "ditch:left"
        assert panel._model_from_tables().element_rows[0].region_ref == ""
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
        assert [row.side for row in model.element_rows[:2]] == ["left", "right"]
        assert [row.assembly_component_ref for row in model.element_rows[:2]] == ["ditch:left", "ditch:right"]
        assert [row.flow_route_id for row in model.flow_route_rows] == ["flow-route:flowId-01", "flow-route:flowId-02"]
        assert panel._policy_table.rowCount() == 1
        assert "Drainage preset loaded: Dual Side Ditches" in panel._status.toPlainText()

        panel._preset_combo.setCurrentText("Culvert Crossing")
        panel._load_selected_preset()
        model = panel._model_from_tables()

        assert panel._element_table.cellWidget(2, 7).currentText() == ""
        assert panel._element_table.cellWidget(2, 6).currentText() == "cross-drain"
        assert model.element_rows[2].structure_ref == ""
        assert model.element_rows[2].policy_set_ref == "drainage-policy:cross-drain"
        assert panel._flow_route_table.item(0, 0).text() == "flowId-01"
        assert panel._flow_route_table.cellWidget(0, 1).currentText() == "side-ditch-left"
        assert panel._flow_route_table.cellWidget(0, 2).currentText() == "culvert-01"
        assert panel._flow_route_table.cellWidget(0, 3).currentText() == ""
        assert panel._flow_route_table.cellWidget(0, 3).isEnabled() is False
        assert model.flow_route_rows[0].flow_route_id == "flow-route:flowId-01"
        assert model.flow_route_rows[0].from_element_ref == "drainage:side-ditch-left"
        assert model.flow_route_rows[0].to_element_ref == "drainage:culvert-01"
        assert model.flow_route_rows[0].outlet_ref == ""

        panel._preset_combo.setCurrentText("Drainage Structures Flow")
        panel._load_selected_preset()
        model = panel._model_from_tables()

        assert panel._element_table.item(3, 0).text() == "inlet-01"
        assert panel._element_table.cellWidget(3, 7).currentText() == "inlet-01"
        assert panel._element_table.cellWidget(3, 8).currentText() == "pipe-out"
        assert panel._element_table.item(6, 0).text() == "culvert-01"
        assert panel._element_table.cellWidget(6, 7).currentText() == "culvert-01"
        assert panel._element_table.cellWidget(6, 8).currentText() == ""
        assert panel._flow_route_table.item(6, 0).text() == "flowId-07"
        assert panel._flow_route_table.cellWidget(6, 1).currentText() == "culvert-01"
        assert panel._flow_route_table.cellWidget(6, 2).currentText() == "outlet-01"
        assert panel._flow_route_table.cellWidget(6, 3).currentText() == "outlet-01"
        assert panel._flow_route_table.cellWidget(0, 3).isEnabled() is False
        assert panel._flow_route_table.cellWidget(1, 3).isEnabled() is False
        assert panel._flow_route_table.cellWidget(6, 3).isEnabled() is True
        assert model.element_rows[3].structure_ref == "structure:inlet-01"
        assert model.element_rows[3].connection_point_ref == "connection:inlet-01:pipe-out"
        assert model.element_rows[6].connection_point_ref == ""
        assert model.flow_route_rows[6].flow_route_id == "flow-route:flowId-07"
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_double_click_flow_route_shows_pipe_segment_preview() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1DrainageEditorFlowRoutePreviewTest")
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        structure_model = structure_preset_model_from_document(
            "Drainage Structures",
            doc,
            project=project,
            alignment=alignment,
        )
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=structure_model)

        panel = V1DrainageEditorTaskPanel(document=doc)
        panel._preset_combo.setCurrentText("Drainage Structures Flow")
        panel._load_selected_preset()
        panel._show_flow_route_segment(5)

        preview = doc.getObject("V1DrainagePipelineSegmentPreview")

        assert preview is not None
        assert preview.CRRecordKind == "v1_drainage_pipeline_segment_preview"
        assert preview.FlowRouteRef == "flow-route:flowId-06"
        assert preview.FromConnectionPointRef == "connection:inlet-03:pipe-out"
        assert preview.ToConnectionPointRef == "connection:culvert-01:pipe-in"
        assert "Flow Route pipe segment preview shown." in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_side_specific_ditch_defaults_keep_ids_unique() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageEditorUniqueSideDefaultsTest")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)

        panel._add_ditch_row("right")
        model = panel._model_from_tables()

        ditch_ids = [row.drainage_element_id for row in model.element_rows if row.element_kind == "ditch"]
        assert ditch_ids == [
            "drainage:side-ditch-right",
            "drainage:side-ditch-right:2",
        ]
    finally:
        App.closeDocument(doc.Name)


def test_drainage_editor_show_flow_network_applies_model_and_creates_preview() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1DrainageEditorShowFlowNetworkTest")
    try:
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
                        placement=StructurePlacement("placement:inlet-01", "alignment:main", 38.0, 40.0),
                    ),
                    StructureRow(
                        structure_id="structure:culvert-01",
                        structure_kind="culvert",
                        structure_role="crossing",
                        placement=StructurePlacement("placement:culvert-01", "alignment:main", 45.0, 55.0),
                    ),
                    StructureRow(
                        structure_id="structure:outlet-01",
                        structure_kind="utility",
                        structure_role="reference",
                        placement=StructurePlacement("placement:outlet-01", "alignment:main", 58.0, 62.0),
                    ),
                ],
                connection_point_rows=[
                    StructureConnectionPoint(
                        connection_point_id="connection:inlet-01:pipe-out",
                        structure_ref="structure:inlet-01",
                        point_role="pipe_out",
                        station=40.0,
                        offset=-5.2,
                        diameter=0.75,
                    ),
                    StructureConnectionPoint(
                        connection_point_id="connection:culvert-01:upstream",
                        structure_ref="structure:culvert-01",
                        point_role="upstream",
                        station=45.0,
                        offset=-5.2,
                        diameter=0.9,
                    ),
                    StructureConnectionPoint(
                        connection_point_id="connection:outlet-01:pipe-in",
                        structure_ref="structure:outlet-01",
                        point_role="pipe_in",
                        station=62.0,
                        offset=6.4,
                        diameter=0.9,
                    ),
                ],
            ),
        )
        panel = V1DrainageEditorTaskPanel(document=doc)
        panel._preset_combo.setCurrentText("Drainage Structures Flow")
        panel._load_selected_preset()

        panel._show_flow_network()

        preview = doc.getObject("V1DrainagePipelineNetworksPreview")
        model = to_drainage_model(find_v1_drainage_model(doc))
        assert preview is not None
        assert preview.CRRecordKind == "v1_drainage_pipeline_networks_preview"
        assert preview.FlowRouteRefs == "flow-route:flowId-02,flow-route:flowId-03"
        assert "Drainage Flow Network preview shown." in panel._status.toPlainText()
        assert model is not None
        assert [row.flow_route_id for row in model.flow_route_rows] == [
            "flow-route:flowId-01",
            "flow-route:flowId-02",
            "flow-route:flowId-03",
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
