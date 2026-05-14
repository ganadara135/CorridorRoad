import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_STRUCTURES,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_structure_editor import (
    CmdV1StructureEditor,
    V1StructureEditorTaskPanel,
    _bridge_spec_from_detail,
    _kind_detail_field_specs,
    _kind_detail_values,
    _project_xy_to_alignment,
    _replace_kind_spec,
    STRUCTURE_GEOMETRY_SPEC_REF_ROLE,
    apply_v1_structure_model,
    show_v1_structure_connection_points_preview_object,
    show_v1_structure_preview_object,
    starter_structure_model_from_document,
    structure_preset_model_from_document,
    structure_preset_names,
)
from freecad.Corridor_Road.v1.models.source.structure_model import (
    BridgeGeometrySpec,
    CulvertGeometrySpec,
    StructureConnectionPoint,
    StructureGeometrySpec,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from freecad.Corridor_Road.v1.models.result.applied_section import AppliedSection, AppliedSectionFrame
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_alignment import to_alignment_model
from freecad.Corridor_Road.v1.objects.obj_applied_section import create_or_update_v1_applied_section_set_object
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing
from freecad.Corridor_Road.v1.objects.obj_structure import find_v1_structure_model, to_structure_model
from freecad.Corridor_Road.v1.services.evaluation import AlignmentEvaluationService

_QAPP = None


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def _new_project_doc():
    doc = App.newDocument("V1StructureEditorCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def test_starter_structure_model_uses_generated_station_range() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        stationing = create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)

        model = starter_structure_model_from_document(doc, project=project, alignment=alignment)

        stations = list(stationing.StationValues)
        assert len(model.structure_rows) == 1
        assert model.structure_rows[0].structure_kind == "bridge"
        assert min(stations) <= model.structure_rows[0].placement.station_start <= max(stations)
        assert min(stations) <= model.structure_rows[0].placement.station_end <= max(stations)
        assert model.alignment_id == alignment.AlignmentId
    finally:
        App.closeDocument(doc.Name)


def test_structure_presets_offer_practical_structure_sets() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=50.0)
        names = structure_preset_names()

        assert "Bridge Segment" in names
        assert "Culvert Crossing" in names
        assert "Drainage Structures" in names
        assert "Retaining Wall" in names
        model = structure_preset_model_from_document("Culvert Crossing", doc, project=project, alignment=alignment)

        assert len(model.structure_rows) == 1
        assert model.structure_rows[0].structure_id == "structure:culvert-01"
        assert model.structure_rows[0].structure_kind == "culvert"
        assert model.structure_rows[0].geometry_spec_ref == "geometry-spec:culvert-01"
        assert model.geometry_spec_rows[0].structure_ref == "structure:culvert-01"
        assert model.geometry_spec_rows[0].shape_kind == "box"
        assert model.geometry_spec_rows[0].width == 3.0
        assert model.geometry_spec_rows[0].height == 2.0
        assert model.geometry_spec_rows[0].vertical_position_mode == "profile_frame"
        assert model.culvert_geometry_spec_rows[0].geometry_spec_ref == "geometry-spec:culvert-01"
        assert model.culvert_geometry_spec_rows[0].barrel_shape == "box"
        assert model.culvert_geometry_spec_rows[0].wall_thickness == 0.3
        assert model.structure_rows[0].placement.station_start < model.structure_rows[0].placement.station_end
    finally:
        App.closeDocument(doc.Name)


def test_structure_preset_drainage_structures_provides_outlet_and_culvert_refs() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=50.0)

        model = structure_preset_model_from_document("Drainage Structures", doc, project=project, alignment=alignment)

        assert [row.structure_id for row in model.structure_rows] == [
            "structure:culvert-01",
            "structure:inlet-01",
            "structure:outlet-01",
        ]
        assert [row.structure_kind for row in model.structure_rows] == ["culvert", "utility", "utility"]
        assert [row.native_type for row in model.structure_rows] == ["box_culvert", "inlet", "outlet"]
        assert [row.structure_ref for row in model.geometry_spec_rows] == [
            "structure:culvert-01",
            "structure:inlet-01",
            "structure:outlet-01",
        ]
        assert model.geometry_spec_rows[2].shape_kind == "outlet_headwall"
        assert model.culvert_geometry_spec_rows[0].geometry_spec_ref == "geometry-spec:culvert-01"
        assert model.culvert_geometry_spec_rows[0].headwall_type == "straight"
        assert [row.connection_point_id for row in model.connection_point_rows] == [
            "connection:culvert-01:upstream",
            "connection:culvert-01:downstream",
            "connection:inlet-01:inlet",
            "connection:inlet-01:pipe-out",
            "connection:outlet-01:pipe-in",
            "connection:outlet-01:discharge",
        ]
        assert [row.point_role for row in model.connection_point_rows] == [
            "upstream",
            "downstream",
            "inlet",
            "pipe_out",
            "pipe_in",
            "discharge",
        ]
        assert [row.structure_ref for row in model.connection_point_rows] == [
            "structure:culvert-01",
            "structure:culvert-01",
            "structure:inlet-01",
            "structure:inlet-01",
            "structure:outlet-01",
            "structure:outlet-01",
        ]
        assert model.connection_point_rows[0].station == model.structure_rows[0].placement.station_start
        assert model.connection_point_rows[1].station == model.structure_rows[0].placement.station_end
        assert model.connection_point_rows[0].width == 3.0
        assert model.connection_point_rows[0].height == 2.0
        assert model.connection_point_rows[3].diameter == 0.6
        assert model.connection_point_rows[3].shape_kind == "circular"
        assert model.connection_point_rows[4].diameter == 0.8
        assert model.connection_point_rows[4].direction == "in"
        assert all(row.region_ref == "" for row in model.connection_point_rows)
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_hides_structure_prefix_in_structure_id_rows() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=50.0)
        panel = V1StructureEditorTaskPanel(document=doc)
        panel._preset_combo.setCurrentText("Bridge Segment")

        panel._load_selected_preset()
        rows = panel._table_rows()

        assert panel._table.item(0, 0).text() == "bridge-01"
        assert rows[0].structure_id == "structure:bridge-01"
        assert "bridge-01" in panel._detail_summary.text()
        assert "structure:bridge-01" not in panel._detail_summary.text()
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_moves_geometry_ref_to_selected_detail() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            alignment_id="alignment:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:bridge-01",
                    structure_kind="bridge",
                    structure_role="interface",
                    placement=StructurePlacement(
                        placement_id="placement:bridge-01",
                        alignment_id="alignment:main",
                        station_start=10.0,
                        station_end=80.0,
                    ),
                    geometry_spec_ref="geometry-spec:bridge-01",
                    geometry_ref="external:bridge-solid",
                    reference_mode="source_ref",
                    geometry_source_mode="external_ref",
                )
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:bridge-01",
                    structure_ref="structure:bridge-01",
                    shape_kind="deck_slab",
                    width=12.0,
                    height=1.0,
                )
            ],
        )
        apply_v1_structure_model(document=doc, project=project, structure_model=model)

        panel = V1StructureEditorTaskPanel(document=doc)
        headers = [panel._table.horizontalHeaderItem(index).text() for index in range(panel._table.columnCount())]

        assert "Geometry Ref" not in headers
        assert "Region" not in headers
        assert headers == ["Structure Id", "Kind", "Role", "Start STA", "End STA", "Offset", "Notes"]
        assert panel._geometry_ref_field.text() == "external:bridge-solid"
        assert panel._geometry_ref_field.isEnabled()
        panel._geometry_ref_field.setText("ifc:bridge-solid")

        updated = panel._model_from_table()

        assert updated.structure_rows[0].geometry_ref == "ifc:bridge-solid"
        assert updated.structure_rows[0].reference_mode == "source_ref"
        assert updated.structure_rows[0].geometry_source_mode == "external_ref"
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_edits_common_geometry_in_selected_detail() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            alignment_id="alignment:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:culvert-01",
                    structure_kind="culvert",
                    structure_role="drainage",
                    placement=StructurePlacement(
                        placement_id="placement:culvert-01",
                        alignment_id="alignment:main",
                        station_start=40.0,
                        station_end=50.0,
                    ),
                    geometry_spec_ref="geometry-spec:culvert-01",
                    geometry_source_mode="native",
                    native_type="box_culvert",
                )
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:culvert-01",
                    structure_ref="structure:culvert-01",
                    shape_kind="box",
                    width=3.0,
                    height=2.0,
                )
            ],
        )
        apply_v1_structure_model(document=doc, project=project, structure_model=model)

        panel = V1StructureEditorTaskPanel(document=doc)

        assert panel._geometry_table.parent() is None
        assert not panel._geometry_ref_field.isEnabled()
        assert panel._common_shape_label.text() == "Shape (auto)"
        assert panel._common_shape_field.placeholderText() == "Auto from Native Type"
        assert "Auto-filled from Native Type" in panel._common_shape_field.toolTip()
        assert panel._connection_label.text() == "Drainage Connection Points"
        assert panel._apply_detail_button.text() == "Apply Selected Detail"
        assert "Drainage Connection Points" in panel._apply_detail_button.toolTip()
        assert panel._save_button.text() == "Save"
        assert "without creating a 3D preview" in panel._save_button.toolTip()
        assert panel._preview_button.text() == "Preview 3D"
        assert "without saving" in panel._preview_button.toolTip()
        assert panel._save_preview_button.text() == "Save + Preview"
        assert "then create a 3D preview" in panel._save_preview_button.toolTip()
        assert panel._common_shape_field.text() == "box"
        panel._common_shape_field.setText("pipe")
        panel._common_width_field.setText("1.800")
        panel._common_height_field.setText("1.800")
        panel._common_vertical_mode_combo.setCurrentText("absolute_elevation")
        panel._common_base_elev_field.setText("45.250")
        panel._common_top_elev_field.setText("47.050")
        panel._common_skew_field.setText("12.500")
        panel._common_material_field.setText("precast concrete")
        panel._common_notes_field.setText("edited in selected detail")

        updated = panel._model_from_table()
        spec = updated.geometry_spec_rows[0]

        assert spec.geometry_spec_id == "geometry-spec:culvert-01"
        assert spec.structure_ref == "structure:culvert-01"
        assert spec.shape_kind == "pipe"
        assert spec.width == 1.8
        assert spec.height == 1.8
        assert spec.vertical_position_mode == "absolute_elevation"
        assert spec.base_elevation == 45.25
        assert spec.top_elevation == 47.05
        assert spec.skew_angle_deg == 12.5
        assert spec.material == "precast concrete"
        assert spec.notes == "edited in selected detail"
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_double_click_loads_selected_structure_detail() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            alignment_id="alignment:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:inlet-01",
                    structure_kind="utility",
                    structure_role="reference",
                    placement=StructurePlacement(
                        placement_id="placement:inlet-01",
                        alignment_id="alignment:main",
                        station_start=10.0,
                        station_end=12.0,
                    ),
                    geometry_spec_ref="geometry-spec:inlet-01",
                    geometry_source_mode="native",
                    native_type="inlet",
                ),
                StructureRow(
                    structure_id="structure:outlet-01",
                    structure_kind="utility",
                    structure_role="reference",
                    placement=StructurePlacement(
                        placement_id="placement:outlet-01",
                        alignment_id="alignment:main",
                        station_start=90.0,
                        station_end=92.0,
                    ),
                    geometry_spec_ref="geometry-spec:outlet-01",
                    geometry_source_mode="native",
                    native_type="outlet",
                ),
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:inlet-01",
                    structure_ref="structure:inlet-01",
                    shape_kind="inlet_box",
                    width=1.0,
                    height=1.0,
                ),
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:outlet-01",
                    structure_ref="structure:outlet-01",
                    shape_kind="outlet_headwall",
                    width=1.5,
                    height=1.2,
                ),
            ],
        )
        apply_v1_structure_model(document=doc, project=project, structure_model=model)

        panel = V1StructureEditorTaskPanel(document=doc)
        panel._activate_structure_detail_row(1, 4)

        assert panel._table.currentRow() == 1
        assert "outlet-01" in panel._detail_summary.text()
        assert panel._native_type_combo.currentText() == "outlet"
        assert panel._common_shape_field.text() == "outlet_headwall"
        assert panel._common_width_field.text() == "1.500"
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_filters_detail_fields_by_native_type() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            alignment_id="alignment:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:pipe-culvert-01",
                    structure_kind="culvert",
                    structure_role="drainage",
                    placement=StructurePlacement(
                        placement_id="placement:pipe-culvert-01",
                        alignment_id="alignment:main",
                        station_start=40.0,
                        station_end=55.0,
                    ),
                    geometry_spec_ref="geometry-spec:pipe-culvert-01",
                    geometry_source_mode="native",
                    native_type="box_culvert",
                )
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:pipe-culvert-01",
                    structure_ref="structure:pipe-culvert-01",
                    shape_kind="box",
                    width=3.0,
                    height=2.0,
                )
            ],
        )
        apply_v1_structure_model(document=doc, project=project, structure_model=model)

        panel = V1StructureEditorTaskPanel(document=doc)
        panel._native_type_combo.setCurrentText("pipe_culvert")

        visible_labels = [
            label.text()
            for label in panel._detail_labels
            if not label.isHidden() and label.text()
        ]

        assert visible_labels == [
            "Barrel Count",
            "Pipe Diameter",
            "Wall Thickness",
            "Length",
            "Invert Elevation",
            "End Treatment",
        ]
        assert panel._common_shape_field.text() == "circular"
        assert panel._common_width_field.text() == "1.000"
        assert panel._common_height_field.text() == "1.000"

        panel._detail_fields[0].setText("2")
        panel._detail_fields[1].setText("1.200")
        panel._detail_fields[2].setText("0.150")
        panel._detail_fields[3].setText("15.000")
        panel._detail_fields[4].setText("44.500")
        panel._detail_fields[5].setText("headwall")
        panel._apply_selected_detail()
        updated = panel._model_from_table()

        assert updated.geometry_spec_rows[0].shape_kind == "circular"
        assert updated.geometry_spec_rows[0].width == 1.0
        assert updated.geometry_spec_rows[0].height == 1.0
        assert updated.culvert_geometry_spec_rows[0].barrel_shape == "circular"
        assert updated.culvert_geometry_spec_rows[0].barrel_count == 2
        assert updated.culvert_geometry_spec_rows[0].diameter == 1.2
        assert updated.culvert_geometry_spec_rows[0].span == 0.0
        assert updated.culvert_geometry_spec_rows[0].rise == 0.0
        assert updated.culvert_geometry_spec_rows[0].invert_elevation == 44.5
    finally:
        App.closeDocument(doc.Name)


def test_structure_model_roundtrips_geometry_source_and_connection_points() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            alignment_id="alignment:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:culvert-01",
                    structure_kind="culvert",
                    structure_role="active",
                    placement=StructurePlacement(
                        placement_id="placement:culvert-01",
                        alignment_id="alignment:main",
                        station_start=50.0,
                        station_end=60.0,
                    ),
                    geometry_spec_ref="geometry-spec:culvert-01",
                    geometry_source_mode="native",
                    native_type="box_culvert",
                )
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:culvert-01",
                    structure_ref="structure:culvert-01",
                    shape_kind="box",
                    width=3.0,
                    height=2.0,
                )
            ],
            connection_point_rows=[
                StructureConnectionPoint(
                    connection_point_id="connection:culvert-01:upstream",
                    structure_ref="structure:culvert-01",
                    point_role="upstream",
                    station=50.0,
                    offset=-3.0,
                    invert_elevation=45.0,
                    width=3.0,
                    height=2.0,
                    shape_kind="box",
                    direction="upstream",
                ),
                StructureConnectionPoint(
                    connection_point_id="connection:culvert-01:downstream",
                    structure_ref="structure:culvert-01",
                    point_role="downstream",
                    station=60.0,
                    offset=3.0,
                    invert_elevation=44.8,
                    width=3.0,
                    height=2.0,
                    shape_kind="box",
                    direction="downstream",
                ),
            ],
        )

        obj = apply_v1_structure_model(document=doc, project=project, structure_model=model)
        roundtrip = to_structure_model(obj)

        assert roundtrip.structure_rows[0].geometry_source_mode == "native"
        assert roundtrip.structure_rows[0].native_type == "box_culvert"
        assert [row.connection_point_id for row in roundtrip.connection_point_rows] == [
            "connection:culvert-01:upstream",
            "connection:culvert-01:downstream",
        ]
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_selected_detail_edits_geometry_source() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        panel = V1StructureEditorTaskPanel(document=doc)
        panel._append_row()
        panel._table.selectRow(0)
        panel._load_selected_detail()

        panel._geometry_source_combo.setCurrentText("native")
        panel._native_type_combo.setCurrentText("pipe_culvert")

        model = panel._model_from_table()

        assert model.structure_rows[0].geometry_source_mode == "native"
        assert model.structure_rows[0].native_type == "pipe_culvert"
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_apply_selected_detail_syncs_drainage_connection_points() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        panel = V1StructureEditorTaskPanel(document=doc)
        panel._append_row(
            StructureRow(
                structure_id="structure:outlet-01",
                structure_kind="utility",
                structure_role="reference",
                placement=StructurePlacement(
                    placement_id="placement:outlet-01",
                    alignment_id="alignment:main",
                    station_start=90.0,
                    station_end=92.0,
                ),
                geometry_spec_ref="geometry-spec:outlet-01",
                geometry_source_mode="native",
                native_type="outlet",
            )
        )
        panel._append_geometry_spec(
            StructureGeometrySpec(
                geometry_spec_id="geometry-spec:outlet-01",
                structure_ref="structure:outlet-01",
                shape_kind="outlet_headwall",
                width=1.5,
                height=1.2,
            )
        )
        panel._table.selectRow(0)
        panel._load_selected_detail()
        panel._append_connection_point(
            StructureConnectionPoint(
                connection_point_id="connection:outlet-01:pipe-in",
                structure_ref="structure:outlet-01",
                point_role="pipe_in",
                station=91.0,
                offset=-6.0,
                invert_elevation=44.5,
                diameter=0.9,
                direction="upstream",
            )
        )

        panel._apply_selected_detail()
        model = panel._model_from_table()

        assert model.connection_point_rows[0].connection_point_id == "connection:outlet-01:pipe-in"
        assert model.connection_point_rows[0].point_role == "pipe_in"
        assert model.connection_point_rows[0].diameter == 0.9
        assert "Selected detail applied" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_derives_default_culvert_connection_points() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=50.0)
        panel = V1StructureEditorTaskPanel(document=doc)
        panel._preset_combo.setCurrentText("Culvert Crossing")
        panel._load_selected_preset()
        panel._table.selectRow(0)
        panel._load_selected_detail()
        panel._geometry_source_combo.setCurrentText("native")
        panel._native_type_combo.setCurrentText("box_culvert")

        panel._derive_default_connection_points()
        model = panel._model_from_table()

        assert [row.point_role for row in model.connection_point_rows] == ["upstream", "downstream"]
        assert [row.structure_ref for row in model.connection_point_rows] == [
            "structure:culvert-01",
            "structure:culvert-01",
        ]
        assert model.connection_point_rows[0].width == 3.0
        assert model.connection_point_rows[0].height == 2.0
        assert model.connection_point_rows[0].shape_kind == "box"
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_derives_pipe_culvert_connection_points() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        panel = V1StructureEditorTaskPanel(document=doc)
        panel._append_row(
            StructureRow(
                structure_id="structure:pipe-culvert-01",
                structure_kind="culvert",
                structure_role="drainage",
                placement=StructurePlacement(
                    placement_id="placement:pipe-culvert-01",
                    alignment_id="alignment:main",
                    station_start=40.0,
                    station_end=55.0,
                ),
                geometry_spec_ref="geometry-spec:pipe-culvert-01",
                geometry_source_mode="native",
                native_type="pipe_culvert",
            )
        )
        panel._append_geometry_spec(
            StructureGeometrySpec(
                geometry_spec_id="geometry-spec:pipe-culvert-01",
                structure_ref="structure:pipe-culvert-01",
                shape_kind="circular",
                width=1.2,
                height=1.2,
            )
        )
        panel._culvert_geometry_spec_rows = [
            CulvertGeometrySpec(
                geometry_spec_ref="geometry-spec:pipe-culvert-01",
                barrel_shape="circular",
                diameter=1.2,
                invert_elevation=44.5,
            )
        ]
        panel._table.selectRow(0)
        panel._load_selected_detail()

        panel._derive_default_connection_points()
        model = panel._model_from_table()

        assert [row.point_role for row in model.connection_point_rows] == ["upstream", "downstream"]
        assert [row.diameter for row in model.connection_point_rows] == [1.2, 1.2]
        assert [row.width for row in model.connection_point_rows] == [0.0, 0.0]
        assert [row.height for row in model.connection_point_rows] == [0.0, 0.0]
        assert [row.shape_kind for row in model.connection_point_rows] == ["circular", "circular"]
        assert [row.invert_elevation for row in model.connection_point_rows] == [44.5, 44.5]
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_derives_inlet_and_outlet_connection_points() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        panel = V1StructureEditorTaskPanel(document=doc)
        panel._append_row(
            StructureRow(
                structure_id="structure:inlet-01",
                structure_kind="utility",
                structure_role="reference",
                placement=StructurePlacement(
                    placement_id="placement:inlet-01",
                    alignment_id="alignment:main",
                    station_start=30.0,
                    station_end=32.0,
                    offset=-4.5,
                ),
                geometry_spec_ref="geometry-spec:inlet-01",
                geometry_source_mode="native",
                native_type="inlet",
            )
        )
        panel._append_geometry_spec(
            StructureGeometrySpec(
                geometry_spec_id="geometry-spec:inlet-01",
                structure_ref="structure:inlet-01",
                shape_kind="inlet",
                width=1.2,
                height=1.0,
            )
        )
        panel._culvert_geometry_spec_rows = [
            CulvertGeometrySpec(
                geometry_spec_ref="geometry-spec:inlet-01",
                barrel_shape="inlet",
                span=1.2,
                rise=1.0,
                diameter=0.6,
                invert_elevation=44.2,
            )
        ]
        panel._table.selectRow(0)
        panel._load_selected_detail()

        panel._derive_default_connection_points()
        inlet_model = panel._model_from_table()

        assert [row.point_role for row in inlet_model.connection_point_rows] == ["inlet", "pipe_out"]
        assert inlet_model.connection_point_rows[1].diameter == 0.6
        assert inlet_model.connection_point_rows[1].shape_kind == "circular"

        panel._table.item(0, 0).setText("outlet-01")
        panel._table.item(0, 3).setText("90.000")
        panel._table.item(0, 4).setText("92.000")
        panel._set_row_native_type(0, "outlet")
        panel._set_row_geometry_source_mode(0, "native")
        panel._table.item(0, 0).setData(STRUCTURE_GEOMETRY_SPEC_REF_ROLE, "geometry-spec:outlet-01")
        panel._replace_geometry_specs([
            StructureGeometrySpec(
                geometry_spec_id="geometry-spec:outlet-01",
                structure_ref="structure:outlet-01",
                shape_kind="outlet",
                width=1.5,
                height=1.2,
            )
        ])
        panel._culvert_geometry_spec_rows = [
            CulvertGeometrySpec(
                geometry_spec_ref="geometry-spec:outlet-01",
                barrel_shape="outlet",
                span=1.5,
                rise=1.2,
                diameter=0.8,
                invert_elevation=43.6,
            )
        ]
        panel._load_selected_detail()

        panel._derive_default_connection_points()
        outlet_model = panel._model_from_table()

        assert [row.point_role for row in outlet_model.connection_point_rows] == ["pipe_in", "discharge"]
        assert outlet_model.connection_point_rows[0].diameter == 0.8
        assert outlet_model.connection_point_rows[0].shape_kind == "circular"
        assert outlet_model.connection_point_rows[1].shape_kind == "outlet"

        panel._table.item(0, 0).setText("headwall-01")
        panel._set_row_native_type(0, "headwall")
        panel._table.item(0, 0).setData(STRUCTURE_GEOMETRY_SPEC_REF_ROLE, "geometry-spec:headwall-01")
        panel._replace_geometry_specs([
            StructureGeometrySpec(
                geometry_spec_id="geometry-spec:headwall-01",
                structure_ref="structure:headwall-01",
                shape_kind="headwall",
                width=2.4,
                height=1.4,
            )
        ])
        panel._culvert_geometry_spec_rows = [
            CulvertGeometrySpec(
                geometry_spec_ref="geometry-spec:headwall-01",
                barrel_shape="headwall",
                span=2.4,
                rise=1.4,
                diameter=0.7,
                invert_elevation=43.4,
            )
        ]
        panel._load_selected_detail()

        panel._derive_default_connection_points()
        headwall_model = panel._model_from_table()

        assert [row.point_role for row in headwall_model.connection_point_rows] == ["pipe_in", "discharge"]
        assert headwall_model.connection_point_rows[0].diameter == 0.7
        assert headwall_model.connection_point_rows[1].shape_kind == "headwall"
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_connection_point_table_edits_persist_to_model() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        panel = V1StructureEditorTaskPanel(document=doc)
        panel._append_row(
            StructureRow(
                structure_id="structure:inlet-01",
                structure_kind="inlet",
                structure_role="active",
                placement=StructurePlacement(
                    placement_id="placement:inlet-01",
                    alignment_id="alignment:main",
                    station_start=20.0,
                    station_end=20.0,
                    offset=-4.0,
                ),
                geometry_source_mode="native",
                native_type="inlet",
            )
        )
        panel._table.selectRow(0)
        panel._load_selected_detail()

        panel._add_connection_point()
        panel._connection_table.item(0, 0).setText("connection:inlet-01:pipe-out")
        panel._connection_table.item(0, 1).setText("pipe_out")
        panel._connection_table.item(0, 5).setText("44.250")
        panel._connection_table.item(0, 9).setText("0.600")

        model = panel._model_from_table()

        assert len(model.connection_point_rows) == 1
        assert model.connection_point_rows[0].connection_point_id == "connection:inlet-01:pipe-out"
        assert model.connection_point_rows[0].point_role == "pipe_out"
        assert model.connection_point_rows[0].invert_elevation == 44.25
        assert model.connection_point_rows[0].diameter == 0.6
        assert model.connection_point_rows[0].region_ref == ""
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_projects_3d_pick_xy_to_station_offset() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment_obj = create_sample_v1_alignment(doc, project=project)
        alignment = to_alignment_model(alignment_obj)
        service = AlignmentEvaluationService()
        x, y = service.station_offset_to_xy(alignment, 30.0, 4.0)

        station, offset = _project_xy_to_alignment(alignment, x, y)

        assert abs(station - 30.0) < 1.0e-6
        assert abs(offset - 4.0) < 1.0e-6
    finally:
        App.closeDocument(doc.Name)


def test_show_v1_structure_connection_points_preview_object_creates_markers() -> None:
    doc, project, tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            alignment_id=str(getattr(alignment, "AlignmentId", "") or ""),
            structure_rows=[
                StructureRow(
                    structure_id="structure:culvert-01",
                    structure_kind="culvert",
                    structure_role="active",
                    placement=StructurePlacement(
                        placement_id="placement:culvert-01",
                        alignment_id=str(getattr(alignment, "AlignmentId", "") or ""),
                        station_start=20.0,
                        station_end=40.0,
                    ),
                )
            ],
            connection_point_rows=[
                StructureConnectionPoint(
                    connection_point_id="connection:culvert-01:upstream",
                    structure_ref="structure:culvert-01",
                    point_role="upstream",
                    station=20.0,
                    offset=-3.0,
                    invert_elevation=45.0,
                    width=3.0,
                    height=2.0,
                    shape_kind="box",
                ),
                StructureConnectionPoint(
                    connection_point_id="connection:culvert-01:downstream",
                    structure_ref="structure:culvert-01",
                    point_role="downstream",
                    station=40.0,
                    offset=3.0,
                    invert_elevation=44.5,
                    width=3.0,
                    height=2.0,
                    shape_kind="box",
                ),
            ],
        )

        preview = show_v1_structure_connection_points_preview_object(
            doc,
            model,
            structure_ref="structure:culvert-01",
            project=project,
        )

        assert preview.Name == "V1StructureConnectionPointPreview"
        assert preview.CRRecordKind == "v1_structure_connection_point_preview"
        assert preview.V1ObjectType == "V1StructureConnectionPointPreview"
        assert preview.ConnectionPointCount == 2
        assert list(preview.ConnectionPointIds) == [
            "connection:culvert-01:upstream",
            "connection:culvert-01:downstream",
        ]
        assert preview.Shape.BoundBox.XLength > 0.0
        assert preview.Name in _group_names(tree[V1_TREE_STRUCTURES])
    finally:
        App.closeDocument(doc.Name)


def test_show_v1_structure_connection_points_preview_object_can_focus_one_point() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        create_sample_v1_alignment(doc, project=project)
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            connection_point_rows=[
                StructureConnectionPoint(
                    connection_point_id="connection:inlet-01:pipe-out",
                    structure_ref="structure:inlet-01",
                    point_role="pipe_out",
                    station=20.0,
                    offset=-4.0,
                    invert_elevation=44.0,
                    diameter=0.6,
                )
            ],
        )

        preview = show_v1_structure_connection_points_preview_object(
            doc,
            model,
            structure_ref="structure:inlet-01",
            connection_point_ref="connection:inlet-01:pipe-out",
            project=project,
        )

        assert preview.ConnectionPointCount == 1
        assert preview.ConnectionPointRef == "connection:inlet-01:pipe-out"
        assert preview.Shape.BoundBox.ZLength > 0.0
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_structure_model_creates_structure_source_object_only() -> None:
    doc, project, tree = _new_project_doc()
    try:
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            alignment_id="alignment:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:bridge-01",
                    structure_kind="bridge",
                    structure_role="interface",
                    placement=StructurePlacement(
                        placement_id="placement:bridge-01",
                        alignment_id="alignment:main",
                        station_start=100.0,
                        station_end=180.0,
                    ),
                )
            ],
        )

        obj = apply_v1_structure_model(document=doc, project=project, structure_model=model)
        roundtrip = to_structure_model(obj)

        assert obj == find_v1_structure_model(doc)
        assert obj.V1ObjectType == "V1StructureModel"
        assert obj.CRRecordKind == "v1_structure_model"
        assert obj.StructureCount == 1
        assert roundtrip.structure_rows[0].structure_id == "structure:bridge-01"
        assert obj.Name in _group_names(tree[V1_TREE_STRUCTURES])
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_structure_model_reuses_existing_structure_object() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        first_model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:bridge-01",
                    structure_kind="bridge",
                    structure_role="interface",
                    placement=StructurePlacement(
                        placement_id="placement:bridge-01",
                        alignment_id="",
                        station_start=0.0,
                        station_end=100.0,
                    ),
                )
            ],
        )
        second_model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:wall-01",
                    structure_kind="retaining_wall",
                    structure_role="interface",
                    placement=StructurePlacement(
                        placement_id="placement:wall-01",
                        alignment_id="",
                        station_start=100.0,
                        station_end=160.0,
                    ),
                )
            ],
        )

        first = apply_v1_structure_model(document=doc, project=project, structure_model=first_model)
        second = apply_v1_structure_model(document=doc, project=project, structure_model=second_model)

        assert first.Name == second.Name
        assert second.StructureCount == 1
        assert list(second.StructureIds) == ["structure:wall-01"]
    finally:
        App.closeDocument(doc.Name)


def test_show_v1_structure_preview_object_creates_visible_3d_preview() -> None:
    doc, project, tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        model = structure_preset_model_from_document("Bridge Segment", doc, project=project, alignment=alignment)

        preview = show_v1_structure_preview_object(doc, model, project=project)

        assert preview is not None
        assert preview.Name == "V1StructureShowPreview"
        assert preview.CRRecordKind == "v1_structure_show_preview"
        assert preview.V1ObjectType == "V1StructureShowPreview"
        assert preview.StructureModelId == "structures:main"
        assert int(preview.StructureCount) == 1
        assert int(preview.GeometrySpecCount) == 1
        assert preview.PreviewGeometrySource == "geometry_spec"
        assert preview.PreviewPathSource == "alignment"
        assert preview.Shape.BoundBox.XLength > 0.0
        assert preview.Shape.BoundBox.ZLength > 0.0
        assert preview.Name in _group_names(tree[V1_TREE_STRUCTURES])
    finally:
        App.closeDocument(doc.Name)


def test_structure_preview_follows_3d_centerline_when_applied_sections_exist() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        applied = AppliedSectionSet(
            schema_version=1,
            project_id="proj-structure-editor",
            applied_section_set_id="applied-sections:main",
            station_rows=[
                AppliedSectionStationRow("station:0", 0.0, "section:0"),
                AppliedSectionStationRow("station:50", 50.0, "section:50"),
                AppliedSectionStationRow("station:100", 100.0, "section:100"),
            ],
            sections=[
                AppliedSection(
                    schema_version=1,
                    project_id="proj-structure-editor",
                    applied_section_id="section:0",
                    station=0.0,
                    frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=0.0),
                ),
                AppliedSection(
                    schema_version=1,
                    project_id="proj-structure-editor",
                    applied_section_id="section:50",
                    station=50.0,
                    frame=AppliedSectionFrame(station=50.0, x=50.0, y=0.0, z=5.0),
                ),
                AppliedSection(
                    schema_version=1,
                    project_id="proj-structure-editor",
                    applied_section_id="section:100",
                    station=100.0,
                    frame=AppliedSectionFrame(station=100.0, x=50.0, y=50.0, z=10.0),
                ),
            ],
        )
        create_or_update_v1_applied_section_set_object(
            document=doc,
            project=project,
            applied_section_set=applied,
        )
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:bridge-01",
                    structure_kind="bridge",
                    structure_role="interface",
                    placement=StructurePlacement(
                        placement_id="placement:bridge-01",
                        alignment_id="",
                        station_start=0.0,
                        station_end=100.0,
                        offset=0.0,
                    ),
                )
            ],
        )

        preview = show_v1_structure_preview_object(doc, model, project=project)

        assert preview.PreviewPathSource == "3d_centerline"
        assert len(list(preview.Shape.Solids)) > 1
        assert preview.Shape.BoundBox.YLength > 40.0
        assert preview.Shape.BoundBox.ZLength > 10.0
    finally:
        App.closeDocument(doc.Name)


def test_structure_preview_uses_geometry_spec_dimensions_and_notes() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:bridge-wide",
                    structure_kind="bridge",
                    structure_role="interface",
                    placement=StructurePlacement(
                        placement_id="placement:bridge-wide",
                        alignment_id="",
                        station_start=0.0,
                        station_end=40.0,
                        offset=0.0,
                    ),
                    geometry_spec_ref="geometry-spec:bridge-wide",
                )
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:bridge-wide",
                    structure_ref="structure:bridge-wide",
                    shape_kind="deck_slab",
                    width=20.0,
                    height=2.5,
                    skew_angle_deg=7.5,
                    base_elevation=3.0,
                )
            ],
            bridge_geometry_spec_rows=[
                BridgeGeometrySpec(
                    geometry_spec_ref="geometry-spec:bridge-wide",
                    deck_width=22.0,
                    deck_thickness=2.8,
                )
            ],
        )

        preview = show_v1_structure_preview_object(doc, model, project=project)

        assert preview.PreviewGeometrySource == "geometry_spec"
        assert preview.Shape.BoundBox.YLength >= 21.0
        assert preview.Shape.BoundBox.ZLength >= 2.7
        assert any("warning|skew_angle|structure:bridge-wide|" in row for row in list(preview.PreviewReviewNotes))
    finally:
        App.closeDocument(doc.Name)


def test_structure_preview_uses_pipe_culvert_circular_profile() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-preview",
            structure_model_id="structures:main",
            alignment_id=str(getattr(alignment, "AlignmentId", "") or ""),
            structure_rows=[
                StructureRow(
                    structure_id="structure:pipe-culvert-01",
                    structure_kind="culvert",
                    structure_role="drainage",
                    placement=StructurePlacement(
                        placement_id="placement:pipe-culvert-01",
                        alignment_id=str(getattr(alignment, "AlignmentId", "") or ""),
                        station_start=20.0,
                        station_end=50.0,
                    ),
                    geometry_spec_ref="geometry-spec:pipe-culvert-01",
                    geometry_source_mode="native",
                    native_type="pipe_culvert",
                )
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:pipe-culvert-01",
                    structure_ref="structure:pipe-culvert-01",
                    shape_kind="circular",
                    width=1.2,
                    height=1.2,
                )
            ],
            culvert_geometry_spec_rows=[
                CulvertGeometrySpec(
                    geometry_spec_ref="geometry-spec:pipe-culvert-01",
                    barrel_shape="circular",
                    diameter=1.2,
                    invert_elevation=44.5,
                )
            ],
        )

        preview = show_v1_structure_preview_object(doc, model, project=project)

        assert preview.PreviewGeometrySource == "geometry_spec"
        assert preview.Shape.BoundBox.ZMin >= 44.4
        assert preview.Shape.BoundBox.ZLength >= 1.1
        assert preview.Shape.BoundBox.ZLength < 1.4
        assert preview.Shape.BoundBox.YLength < 2.0
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_command_resources_are_v1_structures() -> None:
    resources = CmdV1StructureEditor().GetResources()

    assert resources["MenuText"] == "Structures"
    assert "v1" in resources["ToolTip"]


def test_structure_detail_helpers_update_kind_specific_bridge_spec() -> None:
    fields = _kind_detail_field_specs("bridge")
    spec = _bridge_spec_from_detail(
        "geometry-spec:bridge-01",
        {
            "deck_width": "14.0",
            "deck_thickness": "1.5",
            "girder_depth": "2.0",
            "barrier_height": "1.1",
            "clearance_height": "5.5",
            "abutment_start_offset": "0",
            "abutment_end_offset": "0",
            "pier_station_refs": "120, 150",
            "approach_slab_length": "6.5",
            "bearing_elevation_mode": "profile_frame",
        },
    )
    rows = _replace_kind_spec([BridgeGeometrySpec("geometry-spec:old", deck_width=9.0)], spec)
    values = _kind_detail_values("bridge", "geometry-spec:bridge-01", rows, [], [])

    assert ("deck_width", "Deck Width") in fields
    assert len(rows) == 2
    assert values["deck_width"] == "14.000"
    assert values["pier_station_refs"] == "120, 150"


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 structure editor command contract tests completed.")
