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
    _replace_kind_spec,
    apply_v1_structure_model,
    show_v1_structure_preview_object,
    structure_preset_model_from_document,
    structure_preset_names,
)
from freecad.Corridor_Road.v1.models.source.structure_model import (
    BridgeGeometrySpec,
    RetainingWallGeometrySpec,
    StructureGeometrySpec,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from freecad.Corridor_Road.v1.models.result.applied_section import AppliedSection, AppliedSectionFrame
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_applied_section import create_or_update_v1_applied_section_set_object
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing
from freecad.Corridor_Road.v1.objects.obj_structure import find_v1_structure_model, to_structure_model

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


def test_bridge_segment_structure_preset_uses_generated_station_range() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        stationing = create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)

        model = structure_preset_model_from_document("Bridge Segment", doc, project=project, alignment=alignment)

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
        assert "Retaining Wall" in names
        # culverts and the drainage chain are modelled in Drainage now
        assert "Culvert Crossing" not in names
        assert "Drainage Structures" not in names
        model = structure_preset_model_from_document("Bridge Segment", doc, project=project, alignment=alignment)

        assert len(model.structure_rows) == 1
        assert model.structure_rows[0].structure_id == "structure:bridge-01"
        assert model.structure_rows[0].structure_kind == "bridge"
        assert model.structure_rows[0].geometry_spec_ref == "geometry-spec:bridge-01"
        assert model.geometry_spec_rows[0].structure_ref == "structure:bridge-01"
        assert model.geometry_spec_rows[0].shape_kind == "deck_slab"
        assert model.geometry_spec_rows[0].width == 10.0
        assert model.geometry_spec_rows[0].height == 1.2
        assert model.geometry_spec_rows[0].vertical_position_mode == "profile_frame"
        assert model.bridge_geometry_spec_rows[0].geometry_spec_ref == "geometry-spec:bridge-01"
        assert model.bridge_geometry_spec_rows[0].deck_width == 10.0
        assert model.bridge_geometry_spec_rows[0].deck_thickness == 1.2
        assert model.structure_rows[0].placement.station_start < model.structure_rows[0].placement.station_end
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
                    structure_id="structure:bridge-01",
                    structure_kind="bridge",
                    structure_role="interface",
                    placement=StructurePlacement(
                        placement_id="placement:bridge-01",
                        alignment_id="alignment:main",
                        station_start=10.0,
                        station_end=40.0,
                    ),
                    geometry_spec_ref="geometry-spec:bridge-01",
                    geometry_source_mode="native",
                    native_type="bridge_deck",
                )
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:bridge-01",
                    structure_ref="structure:bridge-01",
                    shape_kind="deck_slab",
                    width=10.0,
                    height=1.2,
                )
            ],
        )
        apply_v1_structure_model(document=doc, project=project, structure_model=model)

        panel = V1StructureEditorTaskPanel(document=doc)

        assert panel._geometry_table.parent() is None
        assert panel._geometry_table.objectName() == "InternalGeometrySpecStore"
        assert panel._geometry_table.editTriggers() == QtWidgets.QAbstractItemView.NoEditTriggers
        assert not panel._geometry_ref_field.isEnabled()
        assert panel._common_shape_label.text() == "Shape (auto)"
        assert panel._common_shape_field.placeholderText() == "Auto from Native Type"
        assert "Auto-filled from Native Type" in panel._common_shape_field.toolTip()
        assert panel._apply_detail_button.text() == "Apply Selected Detail"
        assert not hasattr(panel, "_connection_table")
        assert panel._save_button.text() == "Apply"
        assert "without creating a 3D preview" in panel._save_button.toolTip()
        assert panel._preview_button.text() == "Preview 3D"
        assert "without applying" in panel._preview_button.toolTip()
        assert panel._save_preview_button.text() == "Apply + Preview"
        assert "then create a 3D preview" in panel._save_preview_button.toolTip()
        assert panel._common_shape_field.text() == "deck_slab"
        panel._common_shape_field.setText("box_girder")
        panel._common_width_field.setText("12.500")
        panel._common_height_field.setText("1.800")
        panel._common_vertical_mode_combo.setCurrentText("absolute_elevation")
        panel._common_base_elev_field.setText("45.250")
        panel._common_top_elev_field.setText("47.050")
        panel._common_skew_field.setText("12.500")
        panel._common_material_field.setText("precast concrete")
        panel._common_notes_field.setText("edited in selected detail")

        updated = panel._model_from_table()
        spec = updated.geometry_spec_rows[0]

        assert spec.geometry_spec_id == "geometry-spec:bridge-01"
        assert spec.structure_ref == "structure:bridge-01"
        assert spec.shape_kind == "box_girder"
        assert spec.width == 12.5
        assert spec.height == 1.8
        assert spec.vertical_position_mode == "absolute_elevation"
        assert spec.base_elevation == 45.25
        assert spec.top_elevation == 47.05
        assert spec.skew_angle_deg == 12.5
        assert spec.material == "precast concrete"
        assert spec.notes == "edited in selected detail"
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_reopens_with_applied_rows_and_selected_detail() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        create_sample_v1_alignment(doc, project=project)

        panel = V1StructureEditorTaskPanel(document=doc)
        panel._preset_combo.setCurrentText("Bridge Segment")
        panel._load_selected_preset()
        panel._table.selectRow(0)
        panel._load_selected_detail()
        panel._common_width_field.setText("12.000")

        # the panel calls the editor module's own injected binding, so patching the
        # command module would leave a real modal dialog in the way
        import freecad.Corridor_Road.v1.ui.editors.structure_editor as structure_editor_view

        original_show_message = structure_editor_view._show_message
        structure_editor_view._show_message = lambda *_args, **_kwargs: None
        try:
            assert panel._apply(close_after=False, show_preview=False) is True
        finally:
            structure_editor_view._show_message = original_show_message

        assert panel._table.rowCount() == 1
        assert panel._table.currentRow() == 0
        assert "bridge-01" in panel._detail_summary.text()
        assert panel._common_width_field.text() == "12.000"

        reopened = V1StructureEditorTaskPanel(document=doc)

        assert reopened._table.rowCount() == 1
        assert reopened._table.item(0, 0).text() == "bridge-01"

        reopened._table.selectRow(0)
        reopened._load_selected_detail()

        assert "bridge-01" in reopened._detail_summary.text()
        assert reopened._native_type_combo.currentText() == "bridge_deck"
        assert reopened._common_shape_field.text() == "deck_slab"
        assert reopened._common_width_field.text() == "12.000"
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
                    structure_id="structure:bridge-01",
                    structure_kind="bridge",
                    structure_role="interface",
                    placement=StructurePlacement(
                        placement_id="placement:bridge-01",
                        alignment_id="alignment:main",
                        station_start=10.0,
                        station_end=40.0,
                    ),
                    geometry_spec_ref="geometry-spec:bridge-01",
                    geometry_source_mode="native",
                    native_type="bridge_deck",
                ),
                StructureRow(
                    structure_id="structure:wall-01",
                    structure_kind="retaining_wall",
                    structure_role="active",
                    placement=StructurePlacement(
                        placement_id="placement:wall-01",
                        alignment_id="alignment:main",
                        station_start=90.0,
                        station_end=120.0,
                    ),
                    geometry_spec_ref="geometry-spec:wall-01",
                    geometry_source_mode="native",
                    native_type="retaining_wall",
                ),
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:bridge-01",
                    structure_ref="structure:bridge-01",
                    shape_kind="deck_slab",
                    width=10.0,
                    height=1.2,
                ),
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:wall-01",
                    structure_ref="structure:wall-01",
                    shape_kind="wall",
                    width=1.5,
                    height=3.2,
                ),
            ],
            bridge_geometry_spec_rows=[BridgeGeometrySpec("geometry-spec:bridge-01", deck_width=10.0, deck_thickness=1.2)],
            retaining_wall_geometry_spec_rows=[
                RetainingWallGeometrySpec("geometry-spec:wall-01", wall_height=3.2, wall_thickness=1.5)
            ],
        )
        apply_v1_structure_model(document=doc, project=project, structure_model=model)

        panel = V1StructureEditorTaskPanel(document=doc)
        panel._activate_structure_detail_row(1, 4)

        assert panel._table.currentRow() == 1
        assert "wall-01" in panel._detail_summary.text()
        assert panel._native_type_combo.currentText() == "retaining_wall"
        assert panel._common_shape_field.text() == "wall"
        assert panel._common_width_field.text() == "1.500"
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_single_click_loads_selected_structure_detail() -> None:
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
                        station_end=40.0,
                    ),
                    geometry_spec_ref="geometry-spec:bridge-01",
                    geometry_source_mode="native",
                    native_type="bridge_deck",
                ),
                StructureRow(
                    structure_id="structure:wall-01",
                    structure_kind="retaining_wall",
                    structure_role="active",
                    placement=StructurePlacement(
                        placement_id="placement:wall-01",
                        alignment_id="alignment:main",
                        station_start=90.0,
                        station_end=120.0,
                    ),
                    geometry_spec_ref="geometry-spec:wall-01",
                    geometry_source_mode="native",
                    native_type="retaining_wall",
                ),
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:bridge-01",
                    structure_ref="structure:bridge-01",
                    shape_kind="deck_slab",
                    width=10.0,
                    height=1.2,
                ),
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:wall-01",
                    structure_ref="structure:wall-01",
                    shape_kind="wall",
                    width=1.5,
                    height=3.2,
                ),
            ],
            bridge_geometry_spec_rows=[BridgeGeometrySpec("geometry-spec:bridge-01", deck_width=10.0, deck_thickness=1.2)],
            retaining_wall_geometry_spec_rows=[
                RetainingWallGeometrySpec("geometry-spec:wall-01", wall_height=3.2, wall_thickness=1.5)
            ],
        )
        apply_v1_structure_model(document=doc, project=project, structure_model=model)

        panel = V1StructureEditorTaskPanel(document=doc)

        assert "bridge-01" in panel._detail_summary.text()

        panel._table.cellClicked.emit(1, 0)

        assert panel._table.currentRow() == 1
        assert "wall-01" in panel._detail_summary.text()
        assert panel._native_type_combo.currentText() == "retaining_wall"
        assert panel._common_shape_field.text() == "wall"

        panel._table.cellClicked.emit(0, 1)

        assert panel._table.currentRow() == 0
        assert "bridge-01" in panel._detail_summary.text()
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_selected_detail_shows_structure_validation_summary() -> None:
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
                        station_end=40.0,
                    ),
                    geometry_spec_ref="geometry-spec:bridge-01",
                    geometry_source_mode="native",
                    native_type="bridge_deck",
                )
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:bridge-01",
                    structure_ref="structure:bridge-01",
                    shape_kind="deck_slab",
                    width=10.0,
                    height=1.2,
                )
            ],
        )
        apply_v1_structure_model(document=doc, project=project, structure_model=model)

        panel = V1StructureEditorTaskPanel(document=doc)

        # the bridge has no bridge-specific spec yet
        assert "Selected validation: error" in panel._detail_validation.text()
        assert "bridge_geometry_spec_missing" in panel._detail_validation.text()

        panel._detail_fields[0].setText("10.000")
        panel._detail_fields[1].setText("1.200")
        panel._apply_selected_detail()

        assert panel._detail_validation.text() == "Selected validation: ok"
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
                    structure_id="structure:bridge-01",
                    structure_kind="bridge",
                    structure_role="interface",
                    placement=StructurePlacement(
                        placement_id="placement:bridge-01",
                        alignment_id="alignment:main",
                        station_start=10.0,
                        station_end=40.0,
                    ),
                    geometry_spec_ref="geometry-spec:bridge-01",
                    geometry_source_mode="native",
                    native_type="bridge_deck",
                ),
                StructureRow(
                    structure_id="structure:wall-01",
                    structure_kind="retaining_wall",
                    structure_role="active",
                    placement=StructurePlacement(
                        placement_id="placement:wall-01",
                        alignment_id="alignment:main",
                        station_start=90.0,
                        station_end=120.0,
                    ),
                    geometry_spec_ref="geometry-spec:wall-01",
                    geometry_source_mode="native",
                    native_type="retaining_wall",
                ),
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:bridge-01",
                    structure_ref="structure:bridge-01",
                    shape_kind="deck_slab",
                    width=10.0,
                    height=1.2,
                ),
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:wall-01",
                    structure_ref="structure:wall-01",
                    shape_kind="wall",
                    width=1.5,
                    height=3.2,
                ),
            ],
            bridge_geometry_spec_rows=[BridgeGeometrySpec("geometry-spec:bridge-01", deck_width=10.0, deck_thickness=1.2)],
            retaining_wall_geometry_spec_rows=[
                RetainingWallGeometrySpec("geometry-spec:wall-01", wall_height=3.2, wall_thickness=1.5)
            ],
        )
        apply_v1_structure_model(document=doc, project=project, structure_model=model)

        panel = V1StructureEditorTaskPanel(document=doc)
        panel._native_type_combo.setCurrentText("retaining_wall")

        visible_labels = [
            label.text()
            for label in panel._detail_labels
            if not label.isHidden() and label.text()
        ]

        assert visible_labels == [
            "Wall Height",
            "Wall Thickness",
            "Footing Width",
            "Footing Thickness",
            "Retained Side",
            "Batter Slope",
            "Coping Height",
        ]
        assert panel._common_shape_field.text() == "wall"
        assert panel._common_width_field.text() == "0.900"
        assert panel._common_height_field.text() == "3.000"

        panel._detail_fields[0].setText("3.500")
        panel._detail_fields[1].setText("0.800")
        panel._detail_fields[2].setText("2.000")
        panel._detail_fields[3].setText("0.500")
        panel._detail_fields[4].setText("right")
        panel._detail_fields[5].setText("0.100")
        panel._detail_fields[6].setText("0.200")
        panel._apply_selected_detail()
        updated = panel._model_from_table()

        assert updated.geometry_spec_rows[0].shape_kind == "wall"
        assert updated.geometry_spec_rows[0].width == 0.9
        assert updated.geometry_spec_rows[0].height == 3.0
        # the bridge row became a wall, so its spec joined the one the wall row already had
        wall = next(row for row in updated.retaining_wall_geometry_spec_rows if row.geometry_spec_ref == "geometry-spec:bridge-01")
        assert wall.wall_height == 3.5
        assert wall.wall_thickness == 0.8
        assert wall.retained_side == "right"
        assert wall.coping_height == 0.2
    finally:
        App.closeDocument(doc.Name)


def test_structure_model_roundtrips_geometry_source_and_native_type() -> None:
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
                    structure_role="active",
                    placement=StructurePlacement(
                        placement_id="placement:bridge-01",
                        alignment_id="alignment:main",
                        station_start=50.0,
                        station_end=60.0,
                    ),
                    geometry_spec_ref="geometry-spec:bridge-01",
                    geometry_source_mode="native",
                    native_type="bridge_deck",
                )
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:bridge-01",
                    structure_ref="structure:bridge-01",
                    shape_kind="deck_slab",
                    width=10.0,
                    height=1.2,
                )
            ],
        )

        obj = apply_v1_structure_model(document=doc, project=project, structure_model=model)
        roundtrip = to_structure_model(obj)

        assert roundtrip.structure_rows[0].geometry_source_mode == "native"
        assert roundtrip.structure_rows[0].native_type == "bridge_deck"
        # connection points were removed with the culverts: no property holds them any more
        assert not hasattr(obj, "ConnectionPointRows")
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
        panel._native_type_combo.setCurrentText("retaining_wall")

        model = panel._model_from_table()

        assert model.structure_rows[0].geometry_source_mode == "native"
        assert model.structure_rows[0].native_type == "retaining_wall"
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_native_type_apply_sets_practical_defaults() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        panel = V1StructureEditorTaskPanel(document=doc)
        panel._append_row(
            StructureRow(
                structure_id="structure:wall-auto-01",
                structure_kind="custom",
                structure_role="reference",
                placement=StructurePlacement(
                    placement_id="placement:wall-auto-01",
                    alignment_id="alignment:main",
                    station_start=30.0,
                    station_end=60.0,
                    offset=-5.0,
                ),
                geometry_spec_ref="geometry-spec:wall-auto-01",
            )
        )
        panel._table.selectRow(0)
        panel._load_selected_detail()

        panel._geometry_source_combo.setCurrentText("native")
        panel._native_type_combo.setCurrentText("retaining_wall")
        panel._detail_fields[0].setText("3.000")
        panel._apply_selected_detail()
        model = panel._model_from_table()

        assert model.structure_rows[0].structure_kind == "retaining_wall"
        assert model.structure_rows[0].structure_role == "active"
        assert model.structure_rows[0].native_type == "retaining_wall"
        assert model.geometry_spec_rows[0].shape_kind == "wall"
        assert model.geometry_spec_rows[0].width == 0.9
        assert model.geometry_spec_rows[0].height == 3.0
        assert model.retaining_wall_geometry_spec_rows[0].wall_height == 3.0
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
        row_preview = doc.getObject("V1StructurePreview_structure_bridge_01")
        assert row_preview is not None
        assert row_preview.CRRecordKind == "v1_structure_row_preview"
        assert row_preview.StructureRef == "structure:bridge-01"
        assert row_preview.Name in _group_names(tree[V1_TREE_STRUCTURES])
        assert row_preview.Name in list(preview.LinkedPreviewObjects)
    finally:
        App.closeDocument(doc.Name)


def test_structure_preview_follows_applied_section_frame_when_applied_sections_exist() -> None:
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

        assert preview.PreviewPathSource == "applied_section_frame"
        assert len(list(preview.Shape.Solids)) > 1
        assert preview.Shape.BoundBox.YLength > 40.0
        assert preview.Shape.BoundBox.ZLength > 10.0
    finally:
        App.closeDocument(doc.Name)


def test_structure_preview_prefers_centerline3d_result_when_available() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
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
                        alignment_id=str(getattr(alignment, "AlignmentId", "") or ""),
                        station_start=0.0,
                        station_end=120.0,
                        offset=0.0,
                    ),
                )
            ],
        )

        preview = show_v1_structure_preview_object(doc, model, project=project)

        assert preview.PreviewPathSource == "centerline3d_result"
        assert preview.Shape.BoundBox.ZMin > 10.0
        assert preview.Shape.BoundBox.ZLength > 0.0
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
    values = _kind_detail_values("bridge", "geometry-spec:bridge-01", rows, [])

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


def test_structure_editor_leaves_out_culverts_saved_before_drainage_took_them_over() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        create_sample_v1_alignment(doc, project=project)
        old = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            alignment_id="alignment:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:bridge-01",
                    structure_kind="bridge",
                    structure_role="interface",
                    placement=StructurePlacement("placement:bridge-01", "alignment:main", 10.0, 40.0),
                    geometry_spec_ref="geometry-spec:bridge-01",
                    native_type="bridge_deck",
                ),
                StructureRow(
                    structure_id="structure:culvert-01",
                    structure_kind="culvert",
                    structure_role="clearance_control",
                    placement=StructurePlacement("placement:culvert-01", "alignment:main", 60.0, 70.0),
                    geometry_spec_ref="geometry-spec:culvert-01",
                    native_type="box_culvert",
                ),
            ],
            geometry_spec_rows=[
                StructureGeometrySpec("geometry-spec:bridge-01", "structure:bridge-01", "deck_slab", 10.0, 1.2),
                StructureGeometrySpec("geometry-spec:culvert-01", "structure:culvert-01", "box", 3.0, 2.0),
            ],
            bridge_geometry_spec_rows=[BridgeGeometrySpec("geometry-spec:bridge-01", deck_width=10.0, deck_thickness=1.2)],
        )
        # written straight to the object, the way an older document would hold it
        from freecad.Corridor_Road.v1.objects.obj_structure import create_or_update_v1_structure_model_object

        create_or_update_v1_structure_model_object(doc, project=project, structure_model=old)
        assert len(to_structure_model(find_v1_structure_model(doc)).structure_rows) == 2

        panel = V1StructureEditorTaskPanel(document=doc)

        assert panel._table.rowCount() == 1
        assert panel._table.item(0, 0).text() == "bridge-01"
        status = panel._status.toPlainText()
        assert "1 culvert or drainage structure(s)" in status and "structure:culvert-01" in status
        assert "model them in Drainage" in status

        import freecad.Corridor_Road.v1.ui.editors.structure_editor as structure_editor_view

        original_show_message = structure_editor_view._show_message
        structure_editor_view._show_message = lambda *_args, **_kwargs: None
        try:
            assert panel._apply(close_after=False, show_preview=False) is True
        finally:
            structure_editor_view._show_message = original_show_message

        stored = to_structure_model(find_v1_structure_model(doc))
        assert [row.structure_id for row in stored.structure_rows] == ["structure:bridge-01"]
        assert [row.geometry_spec_id for row in stored.geometry_spec_rows] == ["geometry-spec:bridge-01"]
    finally:
        App.closeDocument(doc.Name)
