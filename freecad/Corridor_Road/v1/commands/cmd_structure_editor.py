"""Structure editor command for CorridorRoad v1."""

from __future__ import annotations

import math

try:
    import FreeCAD as App
    import FreeCADGui as Gui
    import Part
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None
    Part = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

from ...objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from ..models.source.structure_model import (
    BridgeGeometrySpec,
    CulvertGeometrySpec,
    RetainingWallGeometrySpec,
    StructureGeometrySpec,
    StructureInfluenceZone,
    StructureInteractionRule,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
from ..objects.obj_exchange_package import find_v1_exchange_package
from ..objects.obj_stationing import find_v1_stationing
from ..objects.obj_structure import (
    create_or_update_v1_structure_model_object,
    find_v1_structure_model,
    to_structure_model,
    validate_structure_model,
)
from ..services.evaluation import AlignmentEvaluationService


STRUCTURE_KIND_CHOICES = ["bridge", "culvert", "retaining_wall", "wall", "utility", "custom"]
STRUCTURE_ROLE_CHOICES = ["active", "interface", "clearance_control", "split_zone", "reference"]
LENGTH_MODE_CHOICES = ["station_range", "explicit_length", "reference_geometry"]
VERTICAL_POSITION_MODE_CHOICES = ["profile_frame", "absolute_elevation", "terrain_relative", "structure_reference"]


STRUCTURE_PRESETS = {
    "Empty": {
        "note": "Create a blank v1 StructureModel source object.",
        "rows": [],
    },
    "Bridge Segment": {
        "note": "One bridge structure covering the middle of the available station range.",
        "rows": [
            {
                "id": "structure:bridge-01",
                "kind": "bridge",
                "role": "interface",
                "start": 0.35,
                "end": 0.65,
                "offset": 0.0,
                "geometry": "",
                "spec": "geometry-spec:bridge-01",
                "width": 10.0,
                "height": 1.2,
                "shape": "deck_slab",
                "material": "concrete",
                "bridge": {
                    "deck_width": 10.0,
                    "deck_thickness": 1.2,
                    "girder_depth": 1.8,
                    "barrier_height": 1.1,
                    "clearance_height": 5.0,
                    "approach_slab_length": 6.0,
                    "bearing_elevation_mode": "profile_frame",
                },
                "notes": "Bridge deck/source handoff.",
            }
        ],
    },
    "Culvert Crossing": {
        "note": "One culvert influence band around the center station.",
        "rows": [
            {
                "id": "structure:culvert-01",
                "kind": "culvert",
                "role": "clearance_control",
                "start": 0.45,
                "end": 0.55,
                "offset": 0.0,
                "geometry": "",
                "spec": "geometry-spec:culvert-01",
                "width": 3.0,
                "height": 2.0,
                "shape": "box",
                "material": "concrete",
                "culvert": {
                    "barrel_shape": "box",
                    "barrel_count": 1,
                    "span": 3.0,
                    "rise": 2.0,
                    "wall_thickness": 0.3,
                    "headwall_type": "straight",
                    "wingwall_type": "none",
                },
                "notes": "Culvert section interaction zone.",
            }
        ],
    },
    "Retaining Wall": {
        "note": "One retaining wall zone on the right side of the corridor.",
        "rows": [
            {
                "id": "structure:retaining-wall-01",
                "kind": "retaining_wall",
                "role": "interface",
                "start": 0.20,
                "end": 0.80,
                "offset": 7.5,
                "geometry": "",
                "spec": "geometry-spec:retaining-wall-01",
                "width": 0.9,
                "height": 3.0,
                "shape": "wall",
                "material": "concrete",
                "retaining_wall": {
                    "wall_height": 3.0,
                    "wall_thickness": 0.9,
                    "footing_width": 2.0,
                    "footing_thickness": 0.45,
                    "retained_side": "right",
                    "top_elevation_mode": "profile_frame",
                    "bottom_elevation_mode": "terrain_relative",
                    "coping_height": 0.2,
                },
                "notes": "Retaining wall source handoff.",
            }
        ],
    },
}


def structure_preset_names() -> list[str]:
    """Return available v1 Structure preset names."""

    return list(STRUCTURE_PRESETS.keys())


def starter_structure_model_from_document(document=None, *, project=None, alignment=None) -> StructureModel:
    """Build one non-destructive starter StructureModel."""

    return structure_preset_model_from_document("Bridge Segment", document=document, project=project, alignment=alignment)


def structure_preset_model_from_document(
    preset_name: str,
    document=None,
    *,
    project=None,
    alignment=None,
) -> StructureModel:
    """Build a non-destructive StructureModel from a named preset."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    preset = STRUCTURE_PRESETS.get(str(preset_name or "").strip())
    if preset is None:
        raise ValueError(f"Unknown Structure preset: {preset_name}")
    prj = project or find_project(doc)
    alignment_obj = alignment or find_v1_alignment(doc)
    station_start, station_end = _document_station_range(doc, alignment_obj)
    alignment_id = str(getattr(alignment_obj, "AlignmentId", "") or "")
    return StructureModel(
        schema_version=1,
        project_id=_project_id(prj),
        structure_model_id="structures:main",
        alignment_id=alignment_id,
        label="Structures",
        structure_rows=_preset_structure_rows(
            preset,
            station_start=station_start,
            station_end=station_end,
            alignment_id=alignment_id,
        ),
        geometry_spec_rows=_preset_geometry_spec_rows(preset),
        bridge_geometry_spec_rows=_preset_bridge_geometry_spec_rows(preset),
        culvert_geometry_spec_rows=_preset_culvert_geometry_spec_rows(preset),
        retaining_wall_geometry_spec_rows=_preset_retaining_wall_geometry_spec_rows(preset),
        interaction_rule_rows=[],
        influence_zone_rows=[],
    )


def apply_v1_structure_model(
    *,
    document=None,
    project=None,
    structure_model: StructureModel,
):
    """Validate and persist a v1 StructureModel source object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prj = project or find_project(doc)
    if prj is None:
        try:
            prj = doc.addObject("App::DocumentObjectGroupPython", "CorridorRoadProject")
        except Exception:
            prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(prj)
        prj.Label = "CorridorRoad Project"
    ensure_project_properties(prj)
    ensure_project_tree(prj, include_references=False)
    obj = create_or_update_v1_structure_model_object(
        document=doc,
        project=prj,
        structure_model=structure_model,
    )
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def show_v1_structure_preview_object(document, structure_model: StructureModel, *, project=None):
    """Create or update a 3D preview object from v1 StructureModel source rows."""

    if document is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Structure preview.")
    rows = list(getattr(structure_model, "structure_rows", []) or [])
    if not rows:
        raise ValueError("Structure preview requires at least one Structure row.")
    shape = _make_structure_preview_shape(document, structure_model)
    obj = document.getObject("V1StructureShowPreview")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1StructureShowPreview")
    obj.Label = "Structures 3D Preview"
    obj.Shape = shape
    _set_preview_string_property(obj, "CRRecordKind", "v1_structure_show_preview")
    _set_preview_string_property(obj, "V1ObjectType", "V1StructureShowPreview")
    _set_preview_string_property(obj, "StructureModelId", str(getattr(structure_model, "structure_model_id", "") or ""))
    _set_preview_integer_property(obj, "StructureCount", len(rows))
    _set_preview_string_property(obj, "PreviewPathSource", _structure_preview_path_source_name(document))
    context = _structure_preview_context(structure_model)
    _set_preview_integer_property(obj, "GeometrySpecCount", len(context["geometry_specs"]))
    _set_preview_string_property(obj, "PreviewGeometrySource", "geometry_spec" if context["geometry_specs"] else "fallback")
    _set_preview_string_list_property(obj, "PreviewReviewNotes", _structure_preview_review_notes(structure_model, context))
    _style_structure_preview_object(obj)
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(project or find_project(document), obj)
    except Exception:
        pass
    try:
        document.recompute()
    except Exception:
        pass
    return obj


def run_v1_structure_editor_command():
    """Open the v1 Structure editor panel."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    panel = V1StructureEditorTaskPanel(document=document)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return find_v1_structure_model(document)


class V1StructureEditorTaskPanel:
    """Table-based v1 Structure source editor."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.structure_obj = find_v1_structure_model(self.document)
        self._geometry_spec_rows: list[StructureGeometrySpec] = []
        self._bridge_geometry_spec_rows: list[BridgeGeometrySpec] = []
        self._culvert_geometry_spec_rows: list[CulvertGeometrySpec] = []
        self._retaining_wall_geometry_spec_rows: list[RetainingWallGeometrySpec] = []
        self.form = self._build_ui()
        self._load_existing_rows()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self._apply(close_after=True)

    def reject(self):
        if Gui is not None:
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("CorridorRoad v1 - Structures")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Structures")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        note = QtWidgets.QLabel(
            "Define station-bounded v1 structure source rows. Apply stores source intent only; "
            "rebuild Applied Sections to reflect structure context in section results."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Preset:"))
        self._preset_combo = QtWidgets.QComboBox()
        self._preset_combo.addItems(structure_preset_names())
        preset_row.addWidget(self._preset_combo)
        load_preset_button = QtWidgets.QPushButton("Load Preset")
        load_preset_button.clicked.connect(self._load_selected_preset)
        preset_row.addWidget(load_preset_button)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)

        self._preset_note = QtWidgets.QLabel("")
        self._preset_note.setWordWrap(True)
        layout.addWidget(self._preset_note)
        self._preset_combo.currentIndexChanged.connect(self._update_preset_note)

        self._table = QtWidgets.QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels(
            ["Structure Id", "Kind", "Role", "Start STA", "End STA", "Offset", "Geometry Ref", "Notes"]
        )
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        self._table.itemSelectionChanged.connect(self._load_selected_detail)
        try:
            self._table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        layout.addWidget(self._table, 1)

        edit_row = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add Structure")
        add_button.clicked.connect(self._add_structure_row)
        edit_row.addWidget(add_button)
        delete_button = QtWidgets.QPushButton("Delete Selected")
        delete_button.clicked.connect(self._delete_selected_rows)
        edit_row.addWidget(delete_button)
        sort_button = QtWidgets.QPushButton("Sort by Station")
        sort_button.clicked.connect(self._sort_rows)
        edit_row.addWidget(sort_button)
        edit_row.addStretch(1)
        layout.addLayout(edit_row)

        geometry_label = QtWidgets.QLabel("Geometry Specs")
        geometry_label.setToolTip("Native v1 source dimensions linked from Structure rows.")
        layout.addWidget(geometry_label)

        self._geometry_table = QtWidgets.QTableWidget(0, 12)
        self._geometry_table.setHorizontalHeaderLabels(
            [
                "Spec Id",
                "Structure Ref",
                "Shape",
                "Width",
                "Height",
                "Length Mode",
                "Skew",
                "Vertical Mode",
                "Base Elev",
                "Top Elev",
                "Material",
                "Notes",
            ]
        )
        self._geometry_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._geometry_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._geometry_table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        try:
            self._geometry_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        layout.addWidget(self._geometry_table, 1)

        geometry_edit_row = QtWidgets.QHBoxLayout()
        add_specs_button = QtWidgets.QPushButton("Add Missing Specs")
        add_specs_button.clicked.connect(self._add_missing_geometry_specs)
        geometry_edit_row.addWidget(add_specs_button)
        delete_specs_button = QtWidgets.QPushButton("Delete Selected Spec")
        delete_specs_button.clicked.connect(self._delete_selected_geometry_specs)
        geometry_edit_row.addWidget(delete_specs_button)
        geometry_edit_row.addStretch(1)
        layout.addLayout(geometry_edit_row)

        detail_group = QtWidgets.QGroupBox("Selected Structure Detail")
        detail_layout = QtWidgets.QVBoxLayout(detail_group)
        self._detail_summary = QtWidgets.QLabel("No structure row is selected.")
        detail_layout.addWidget(self._detail_summary)
        detail_form = QtWidgets.QFormLayout()
        self._detail_labels = []
        self._detail_fields = []
        for _index in range(10):
            label = QtWidgets.QLabel("")
            field = QtWidgets.QLineEdit()
            detail_form.addRow(label, field)
            self._detail_labels.append(label)
            self._detail_fields.append(field)
        detail_layout.addLayout(detail_form)
        detail_action_row = QtWidgets.QHBoxLayout()
        apply_detail_button = QtWidgets.QPushButton("Apply Detail")
        apply_detail_button.clicked.connect(self._apply_selected_detail)
        detail_action_row.addWidget(apply_detail_button)
        detail_action_row.addStretch(1)
        detail_layout.addLayout(detail_action_row)
        layout.addWidget(detail_group)

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setFixedHeight(100)
        self._status.setPlainText("No structure source object is selected.")
        layout.addWidget(self._status)

        action_row = QtWidgets.QHBoxLayout()
        validate_button = QtWidgets.QPushButton("Validate")
        validate_button.clicked.connect(self._validate)
        action_row.addWidget(validate_button)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        action_row.addWidget(apply_button)
        show_button = QtWidgets.QPushButton("Show in 3D")
        show_button.clicked.connect(self._show_preview)
        action_row.addWidget(show_button)
        apply_show_button = QtWidgets.QPushButton("Apply + Show")
        apply_show_button.clicked.connect(lambda: self._apply(close_after=False, show_preview=True))
        action_row.addWidget(apply_show_button)
        action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        action_row.addWidget(close_button)
        layout.addLayout(action_row)
        self._update_preset_note()
        return widget

    def _load_existing_rows(self) -> None:
        model = to_structure_model(self.structure_obj)
        if model is None:
            return
        self._geometry_spec_rows = list(getattr(model, "geometry_spec_rows", []) or [])
        self._bridge_geometry_spec_rows = list(getattr(model, "bridge_geometry_spec_rows", []) or [])
        self._culvert_geometry_spec_rows = list(getattr(model, "culvert_geometry_spec_rows", []) or [])
        self._retaining_wall_geometry_spec_rows = list(getattr(model, "retaining_wall_geometry_spec_rows", []) or [])
        self._replace_rows(model.structure_rows)
        self._replace_geometry_specs(self._geometry_spec_rows)
        self._select_first_structure_row()
        self._set_status(f"Loaded {len(model.structure_rows)} Structure row(s) from {self.structure_obj.Label}.")

    def _load_selected_preset(self) -> None:
        try:
            preset_name = str(self._preset_combo.currentText() or "Bridge Segment")
            model = structure_preset_model_from_document(preset_name, document=self.document)
            self._geometry_spec_rows = list(getattr(model, "geometry_spec_rows", []) or [])
            self._bridge_geometry_spec_rows = list(getattr(model, "bridge_geometry_spec_rows", []) or [])
            self._culvert_geometry_spec_rows = list(getattr(model, "culvert_geometry_spec_rows", []) or [])
            self._retaining_wall_geometry_spec_rows = list(getattr(model, "retaining_wall_geometry_spec_rows", []) or [])
            self._replace_rows(model.structure_rows)
            self._replace_geometry_specs(self._geometry_spec_rows)
            self._select_first_structure_row()
            self._set_status(f"Structure preset loaded: {preset_name}. Apply when ready.")
        except Exception as exc:
            self._set_status(f"Structure preset was not loaded:\n{exc}")

    def _update_preset_note(self) -> None:
        if not hasattr(self, "_preset_note"):
            return
        preset = STRUCTURE_PRESETS.get(str(self._preset_combo.currentText() or ""), {})
        self._preset_note.setText(str(preset.get("note", "") or ""))

    def _replace_rows(self, rows: list[StructureRow]) -> None:
        self._table.setRowCount(0)
        for row in rows:
            self._append_row(row)

    def _replace_geometry_specs(self, rows: list[StructureGeometrySpec]) -> None:
        self._geometry_table.setRowCount(0)
        for row in rows:
            self._append_geometry_spec(row)

    def _append_row(self, row: StructureRow | None = None) -> None:
        row = row or StructureRow(
            structure_id=f"structure:{self._table.rowCount() + 1}",
            structure_kind="bridge",
            structure_role="interface",
            placement=StructurePlacement(
                placement_id=f"placement:{self._table.rowCount() + 1}",
                alignment_id=_alignment_id(self.document),
                station_start=0.0,
                station_end=100.0,
            ),
            geometry_spec_ref=f"geometry-spec:{self._table.rowCount() + 1}",
        )
        index = self._table.rowCount()
        self._table.insertRow(index)
        values = [
            row.structure_id,
            row.structure_kind,
            row.structure_role,
            _format_float(row.placement.station_start),
            _format_float(row.placement.station_end),
            _format_float(row.placement.offset),
            row.geometry_ref,
            "",
        ]
        for col, value in enumerate(values):
            if col == 1:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(STRUCTURE_KIND_CHOICES)
                combo.setCurrentText(str(value or "bridge"))
                self._table.setCellWidget(index, col, combo)
            elif col == 2:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(STRUCTURE_ROLE_CHOICES)
                combo.setCurrentText(str(value or "interface"))
                self._table.setCellWidget(index, col, combo)
            else:
                item = QtWidgets.QTableWidgetItem(str(value))
                if col == 0:
                    item.setData(QtCore.Qt.UserRole, str(getattr(row, "geometry_spec_ref", "") or ""))
                self._table.setItem(index, col, item)

    def _append_geometry_spec(self, row: StructureGeometrySpec | None = None) -> None:
        row = row or StructureGeometrySpec(
            geometry_spec_id=f"geometry-spec:{self._geometry_table.rowCount() + 1}",
            structure_ref=f"structure:{self._geometry_table.rowCount() + 1}",
            shape_kind="deck_slab",
            width=10.0,
            height=1.2,
        )
        index = self._geometry_table.rowCount()
        self._geometry_table.insertRow(index)
        values = [
            row.geometry_spec_id,
            row.structure_ref,
            row.shape_kind,
            _format_float(row.width),
            _format_float(row.height),
            row.length_mode,
            _format_float(row.skew_angle_deg),
            row.vertical_position_mode,
            _format_optional_float(row.base_elevation),
            _format_optional_float(row.top_elevation),
            row.material,
            row.notes,
        ]
        for col, value in enumerate(values):
            if col == 5:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(LENGTH_MODE_CHOICES)
                combo.setCurrentText(str(value or "station_range"))
                self._geometry_table.setCellWidget(index, col, combo)
            elif col == 7:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItems(VERTICAL_POSITION_MODE_CHOICES)
                combo.setCurrentText(str(value or "profile_frame"))
                self._geometry_table.setCellWidget(index, col, combo)
            else:
                self._geometry_table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))

    def _add_structure_row(self) -> None:
        self._append_row()
        self._add_missing_geometry_specs()
        self._table.selectRow(max(0, self._table.rowCount() - 1))
        self._set_status("Added a Structure row. Edit values, then Validate or Apply.")

    def _delete_selected_rows(self) -> None:
        rows = sorted({item.row() for item in list(self._table.selectedItems() or [])}, reverse=True)
        if not rows and self._table.currentRow() >= 0:
            rows = [self._table.currentRow()]
        for row_index in rows:
            self._table.removeRow(row_index)
        self._load_selected_detail()
        self._set_status(f"Deleted {len(rows)} Structure row(s).")

    def _add_missing_geometry_specs(self) -> None:
        existing_spec_ids = {str(row.geometry_spec_id) for row in self._geometry_spec_table_rows(allow_blank=True)}
        existing_structure_refs = {str(row.structure_ref) for row in self._geometry_spec_table_rows(allow_blank=True)}
        added = 0
        for row in self._table_rows():
            structure_ref = str(row.structure_id)
            spec_ref = str(row.geometry_spec_ref or f"geometry-spec:{structure_ref.split(':')[-1]}")
            if spec_ref in existing_spec_ids or structure_ref in existing_structure_refs:
                continue
            self._append_geometry_spec(
                StructureGeometrySpec(
                    geometry_spec_id=spec_ref,
                    structure_ref=structure_ref,
                    shape_kind=_default_shape_kind(row.structure_kind),
                    width=_default_geometry_width(row.structure_kind),
                    height=_default_geometry_height(row.structure_kind),
                    length_mode="station_range",
                    vertical_position_mode="profile_frame",
                    style_role=str(row.structure_kind),
                )
            )
            added += 1
        self._set_status(f"Added {added} missing Geometry Spec row(s).")

    def _delete_selected_geometry_specs(self) -> None:
        rows = sorted({item.row() for item in list(self._geometry_table.selectedItems() or [])}, reverse=True)
        if not rows and self._geometry_table.currentRow() >= 0:
            rows = [self._geometry_table.currentRow()]
        for row_index in rows:
            self._geometry_table.removeRow(row_index)
        self._set_status(f"Deleted {len(rows)} Geometry Spec row(s).")

    def _sort_rows(self) -> None:
        try:
            current_id = self._current_structure_id()
            rows = sorted(self._table_rows(), key=lambda row: (row.placement.station_start, row.placement.station_end, row.structure_id))
            self._replace_rows(rows)
            self._select_structure_id(current_id)
            self._set_status("Structure rows sorted by station.")
        except Exception as exc:
            self._set_status(f"Structure rows were not sorted:\n{exc}")

    def _load_selected_detail(self) -> None:
        row = self._current_structure_row()
        if row is None:
            self._detail_summary.setText("No structure row is selected.")
            for label, field in zip(self._detail_labels, self._detail_fields):
                label.setText("")
                label.hide()
                field.setText("")
                field.hide()
            return
        spec_ref = self._ensure_row_geometry_spec_ref(self._table.currentRow(), row)
        kind = str(row.structure_kind or "").strip().lower()
        self._detail_summary.setText(f"{row.structure_id} | {kind or 'custom'} | {spec_ref}")
        values = _kind_detail_values(
            kind,
            spec_ref,
            self._bridge_geometry_spec_rows,
            self._culvert_geometry_spec_rows,
            self._retaining_wall_geometry_spec_rows,
        )
        fields = _kind_detail_field_specs(kind)
        for index, (key, label_text) in enumerate(fields):
            self._detail_labels[index].setText(label_text)
            self._detail_labels[index].show()
            self._detail_fields[index].setText(str(values.get(key, "")))
            self._detail_fields[index].show()
        for index in range(len(fields), len(self._detail_fields)):
            self._detail_labels[index].setText("")
            self._detail_labels[index].hide()
            self._detail_fields[index].setText("")
            self._detail_fields[index].hide()

    def _apply_selected_detail(self) -> None:
        try:
            row_index = self._table.currentRow()
            row = self._current_structure_row()
            if row is None or row_index < 0:
                self._set_status("Select a Structure row before applying detail fields.")
                return
            spec_ref = self._ensure_row_geometry_spec_ref(row_index, row)
            self._add_or_update_common_spec_for_row(row, spec_ref)
            kind = str(row.structure_kind or "").strip().lower()
            values = {
                key: str(self._detail_fields[index].text() or "").strip()
                for index, (key, _label) in enumerate(_kind_detail_field_specs(kind))
            }
            if kind == "bridge":
                self._bridge_geometry_spec_rows = _replace_kind_spec(
                    self._bridge_geometry_spec_rows,
                    _bridge_spec_from_detail(spec_ref, values),
                )
            elif kind == "culvert":
                self._culvert_geometry_spec_rows = _replace_kind_spec(
                    self._culvert_geometry_spec_rows,
                    _culvert_spec_from_detail(spec_ref, values),
                )
            elif kind in {"retaining_wall", "wall"}:
                self._retaining_wall_geometry_spec_rows = _replace_kind_spec(
                    self._retaining_wall_geometry_spec_rows,
                    _retaining_wall_spec_from_detail(spec_ref, values),
                )
            else:
                self._set_status(f"No kind-specific detail fields are defined for {kind or 'custom'}.")
                return
            self._load_selected_detail()
            self._set_status(f"Detail fields applied for {row.structure_id}. Apply the model to persist changes.")
        except Exception as exc:
            self._set_status(f"Structure detail was not applied:\n{exc}")

    def _validate(self) -> None:
        try:
            model = self._model_from_table()
            self._set_status(_format_validation_result(model, document=self.document))
        except Exception as exc:
            self._set_status(f"Structure validation failed:\n{exc}")

    def _apply(self, *, close_after: bool = False, show_preview: bool = True) -> bool:
        try:
            model = self._model_from_table()
            diagnostics = validate_structure_model(model)
            if any(str(row).startswith("error|") for row in diagnostics):
                self._set_status(_format_validation_result(model, document=self.document))
                _show_message(self.form, "Structures", "Structures were not applied because validation has errors.")
                return False
            self.structure_obj = apply_v1_structure_model(document=self.document, structure_model=model)
            preview_text = ""
            if show_preview and list(model.structure_rows or []):
                preview = show_v1_structure_preview_object(self.document, model)
                self._focus_preview_object(preview)
                preview_text = f"\n3D Preview: {preview.Label}"
            self._set_status(_format_validation_result(model, document=self.document) + f"\n\nApplied to: {self.structure_obj.Label}{preview_text}")
            _show_message(self.form, "Structures", f"Structures have been applied.\nRows: {len(model.structure_rows)}")
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_status(f"Structures were not applied:\n{exc}")
            _show_message(self.form, "Structures", f"Structures were not applied.\n{exc}")
            return False

    def _show_preview(self) -> None:
        try:
            model = self._model_from_table()
            diagnostics = validate_structure_model(model)
            if any(str(row).startswith("error|") for row in diagnostics):
                self._set_status(_format_validation_result(model, document=self.document))
                return
            preview = show_v1_structure_preview_object(self.document, model)
            self._focus_preview_object(preview)
            self._set_status(_format_validation_result(model, document=self.document) + f"\n\n3D Preview shown: {preview.Label}")
        except Exception as exc:
            self._set_status(f"Structure preview was not shown:\n{exc}")

    def _focus_preview_object(self, preview) -> None:
        if Gui is None or preview is None:
            return
        try:
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(preview)
        except Exception:
            pass
        try:
            view = getattr(getattr(Gui, "ActiveDocument", None), "ActiveView", None)
            if view is not None and hasattr(view, "fitSelection"):
                view.fitSelection()
        except Exception:
            pass

    def _model_from_table(self) -> StructureModel:
        existing = to_structure_model(self.structure_obj)
        alignment = find_v1_alignment(self.document)
        structure_rows = self._table_rows()
        structure_ids = {str(row.structure_id) for row in structure_rows}
        geometry_spec_rows = [
            row
            for row in self._geometry_spec_table_rows()
            if str(getattr(row, "structure_ref", "") or "") in structure_ids
        ]
        return StructureModel(
            schema_version=1,
            project_id=_project_id(find_project(self.document)),
            structure_model_id=str(getattr(existing, "structure_model_id", "") or "structures:main"),
            alignment_id=str(getattr(existing, "alignment_id", "") or getattr(alignment, "AlignmentId", "") or ""),
            label="Structures",
            structure_rows=structure_rows,
            geometry_spec_rows=geometry_spec_rows,
            bridge_geometry_spec_rows=_filter_kind_specs(
                self._bridge_geometry_spec_rows or getattr(existing, "bridge_geometry_spec_rows", []),
                geometry_spec_rows,
            ),
            culvert_geometry_spec_rows=_filter_kind_specs(
                self._culvert_geometry_spec_rows or getattr(existing, "culvert_geometry_spec_rows", []),
                geometry_spec_rows,
            ),
            retaining_wall_geometry_spec_rows=_filter_kind_specs(
                self._retaining_wall_geometry_spec_rows or getattr(existing, "retaining_wall_geometry_spec_rows", []),
                geometry_spec_rows,
            ),
            interaction_rule_rows=[],
            influence_zone_rows=[],
        )

    def _table_rows(self) -> list[StructureRow]:
        rows: list[StructureRow] = []
        alignment_id = _alignment_id(self.document)
        for row_index in range(self._table.rowCount()):
            structure_id = _item_text(self._table, row_index, 0) or f"structure:{row_index + 1}"
            kind = _item_text(self._table, row_index, 1) or "bridge"
            role = _item_text(self._table, row_index, 2) or "interface"
            station_start = _required_float(_item_text(self._table, row_index, 3), f"Row {row_index + 1} start STA")
            station_end = _required_float(_item_text(self._table, row_index, 4), f"Row {row_index + 1} end STA")
            offset = _required_float(_item_text(self._table, row_index, 5) or "0", f"Row {row_index + 1} offset")
            geometry_ref = _item_text(self._table, row_index, 6)
            rows.append(
                StructureRow(
                    structure_id=structure_id,
                    structure_kind=kind,
                    structure_role=role,
                    placement=StructurePlacement(
                        placement_id=f"placement:{row_index + 1}",
                        alignment_id=alignment_id,
                        station_start=station_start,
                        station_end=station_end,
                        offset=offset,
                    ),
                    geometry_spec_ref=_item_user_data(self._table, row_index, 0),
                    geometry_ref=geometry_ref,
                    reference_mode="native" if not geometry_ref else "source_ref",
                )
            )
        return rows

    def _current_structure_id(self) -> str:
        row = self._current_structure_row()
        return str(getattr(row, "structure_id", "") or "") if row is not None else ""

    def _current_structure_row(self) -> StructureRow | None:
        row_index = self._table.currentRow()
        if row_index < 0 and self._table.selectedItems():
            row_index = self._table.selectedItems()[0].row()
        if row_index < 0 or row_index >= self._table.rowCount():
            return None
        return self._structure_row_from_table_index(row_index)

    def _structure_row_from_table_index(self, row_index: int) -> StructureRow:
        alignment_id = _alignment_id(self.document)
        structure_id = _item_text(self._table, row_index, 0) or f"structure:{row_index + 1}"
        kind = _item_text(self._table, row_index, 1) or "bridge"
        role = _item_text(self._table, row_index, 2) or "interface"
        station_start = _required_float(_item_text(self._table, row_index, 3), f"Row {row_index + 1} start STA")
        station_end = _required_float(_item_text(self._table, row_index, 4), f"Row {row_index + 1} end STA")
        offset = _required_float(_item_text(self._table, row_index, 5) or "0", f"Row {row_index + 1} offset")
        geometry_ref = _item_text(self._table, row_index, 6)
        return StructureRow(
            structure_id=structure_id,
            structure_kind=kind,
            structure_role=role,
            placement=StructurePlacement(
                placement_id=f"placement:{row_index + 1}",
                alignment_id=alignment_id,
                station_start=station_start,
                station_end=station_end,
                offset=offset,
            ),
            geometry_spec_ref=_item_user_data(self._table, row_index, 0),
            geometry_ref=geometry_ref,
            reference_mode="native" if not geometry_ref else "source_ref",
        )

    def _select_first_structure_row(self) -> None:
        if self._table.rowCount() > 0:
            self._table.selectRow(0)
        self._load_selected_detail()

    def _select_structure_id(self, structure_id: str) -> None:
        for row_index in range(self._table.rowCount()):
            if _item_text(self._table, row_index, 0) == structure_id:
                self._table.selectRow(row_index)
                return
        self._select_first_structure_row()

    def _ensure_row_geometry_spec_ref(self, row_index: int, row: StructureRow) -> str:
        spec_ref = str(getattr(row, "geometry_spec_ref", "") or "")
        if not spec_ref:
            spec_ref = f"geometry-spec:{str(row.structure_id).split(':')[-1]}"
            item = self._table.item(row_index, 0)
            if item is not None:
                item.setData(QtCore.Qt.UserRole, spec_ref)
        return spec_ref

    def _add_or_update_common_spec_for_row(self, row: StructureRow, spec_ref: str) -> None:
        specs = self._geometry_spec_table_rows(allow_blank=True)
        for index, spec in enumerate(specs):
            if spec.geometry_spec_id == spec_ref:
                specs[index] = StructureGeometrySpec(
                    geometry_spec_id=spec.geometry_spec_id,
                    structure_ref=row.structure_id,
                    shape_kind=spec.shape_kind or _default_shape_kind(row.structure_kind),
                    width=spec.width if spec.width > 0.0 else _default_geometry_width(row.structure_kind),
                    height=spec.height if spec.height > 0.0 else _default_geometry_height(row.structure_kind),
                    length_mode=spec.length_mode,
                    skew_angle_deg=spec.skew_angle_deg,
                    vertical_position_mode=spec.vertical_position_mode,
                    base_elevation=spec.base_elevation,
                    top_elevation=spec.top_elevation,
                    material=spec.material,
                    style_role=spec.style_role or row.structure_kind,
                    notes=spec.notes,
                )
                self._replace_geometry_specs(specs)
                return
        specs.append(
            StructureGeometrySpec(
                geometry_spec_id=spec_ref,
                structure_ref=row.structure_id,
                shape_kind=_default_shape_kind(row.structure_kind),
                width=_default_geometry_width(row.structure_kind),
                height=_default_geometry_height(row.structure_kind),
                length_mode="station_range",
                vertical_position_mode="profile_frame",
                style_role=row.structure_kind,
            )
        )
        self._replace_geometry_specs(specs)

    def _geometry_spec_table_rows(self, *, allow_blank: bool = False) -> list[StructureGeometrySpec]:
        rows: list[StructureGeometrySpec] = []
        for row_index in range(self._geometry_table.rowCount()):
            geometry_spec_id = _item_text(self._geometry_table, row_index, 0) or f"geometry-spec:{row_index + 1}"
            structure_ref = _item_text(self._geometry_table, row_index, 1)
            if not allow_blank and not structure_ref:
                raise ValueError(f"Geometry Spec row {row_index + 1} Structure Ref is required.")
            rows.append(
                StructureGeometrySpec(
                    geometry_spec_id=geometry_spec_id,
                    structure_ref=structure_ref,
                    shape_kind=_item_text(self._geometry_table, row_index, 2),
                    width=_required_float(_item_text(self._geometry_table, row_index, 3) or "0", f"Geometry Spec row {row_index + 1} width"),
                    height=_required_float(_item_text(self._geometry_table, row_index, 4) or "0", f"Geometry Spec row {row_index + 1} height"),
                    length_mode=_item_text(self._geometry_table, row_index, 5) or "station_range",
                    skew_angle_deg=_required_float(_item_text(self._geometry_table, row_index, 6) or "0", f"Geometry Spec row {row_index + 1} skew"),
                    vertical_position_mode=_item_text(self._geometry_table, row_index, 7) or "profile_frame",
                    base_elevation=_optional_float_text(_item_text(self._geometry_table, row_index, 8)),
                    top_elevation=_optional_float_text(_item_text(self._geometry_table, row_index, 9)),
                    material=_item_text(self._geometry_table, row_index, 10),
                    notes=_item_text(self._geometry_table, row_index, 11),
                )
            )
        return rows

    def _set_status(self, text: str) -> None:
        self._status.setPlainText(str(text or ""))


class CmdV1StructureEditor:
    """Open the v1 Structure source editor."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("edit_structures.svg"),
            "MenuText": "Structures",
            "ToolTip": "Define v1 corridor structures by station range and source references",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_structure_editor_command()


def _preset_structure_rows(
    preset: dict,
    *,
    station_start: float,
    station_end: float,
    alignment_id: str,
) -> list[StructureRow]:
    span = max(float(station_end) - float(station_start), 0.0)
    if span <= 0.0:
        span = 100.0
        station_end = float(station_start) + span
    rows: list[StructureRow] = []
    for index, spec in enumerate(list(preset.get("rows", []) or []), start=1):
        start_ratio = max(0.0, min(1.0, float(spec.get("start", 0.0) or 0.0)))
        end_ratio = max(0.0, min(1.0, float(spec.get("end", 1.0) or 1.0)))
        start_sta = float(station_start) + span * start_ratio
        end_sta = float(station_start) + span * end_ratio
        if end_sta < start_sta:
            start_sta, end_sta = end_sta, start_sta
        structure_id = str(spec.get("id", "") or f"structure:{index}")
        rows.append(
            StructureRow(
                structure_id=structure_id,
                structure_kind=str(spec.get("kind", "") or "bridge"),
                structure_role=str(spec.get("role", "") or "interface"),
                placement=StructurePlacement(
                    placement_id=f"placement:{index}",
                    alignment_id=alignment_id,
                    station_start=start_sta,
                    station_end=end_sta,
                    offset=float(spec.get("offset", 0.0) or 0.0),
                ),
                geometry_spec_ref=str(spec.get("spec", "") or ""),
                geometry_ref=str(spec.get("geometry", "") or ""),
                reference_mode="native",
            )
        )
    return rows


def _preset_geometry_spec_rows(preset: dict) -> list[StructureGeometrySpec]:
    rows: list[StructureGeometrySpec] = []
    for spec in list(preset.get("rows", []) or []):
        geometry_spec_id = str(spec.get("spec", "") or "")
        structure_id = str(spec.get("id", "") or "")
        if not geometry_spec_id or not structure_id:
            continue
        rows.append(
            StructureGeometrySpec(
                geometry_spec_id=geometry_spec_id,
                structure_ref=structure_id,
                shape_kind=str(spec.get("shape", "") or ""),
                width=float(spec.get("width", 0.0) or 0.0),
                height=float(spec.get("height", 0.0) or 0.0),
                length_mode="station_range",
                material=str(spec.get("material", "") or ""),
                style_role=str(spec.get("kind", "") or ""),
                notes=str(spec.get("notes", "") or ""),
            )
        )
    return rows


def _preset_bridge_geometry_spec_rows(preset: dict) -> list[BridgeGeometrySpec]:
    rows: list[BridgeGeometrySpec] = []
    for spec in list(preset.get("rows", []) or []):
        values = dict(spec.get("bridge", {}) or {})
        geometry_spec_ref = str(spec.get("spec", "") or "")
        if not geometry_spec_ref or not values:
            continue
        rows.append(
            BridgeGeometrySpec(
                geometry_spec_ref=geometry_spec_ref,
                deck_width=float(values.get("deck_width", 0.0) or 0.0),
                deck_thickness=float(values.get("deck_thickness", 0.0) or 0.0),
                girder_depth=float(values.get("girder_depth", 0.0) or 0.0),
                barrier_height=float(values.get("barrier_height", 0.0) or 0.0),
                clearance_height=float(values.get("clearance_height", 0.0) or 0.0),
                abutment_start_offset=float(values.get("abutment_start_offset", 0.0) or 0.0),
                abutment_end_offset=float(values.get("abutment_end_offset", 0.0) or 0.0),
                pier_station_refs=list(values.get("pier_station_refs", []) or []),
                approach_slab_length=float(values.get("approach_slab_length", 0.0) or 0.0),
                bearing_elevation_mode=str(values.get("bearing_elevation_mode", "") or ""),
            )
        )
    return rows


def _preset_culvert_geometry_spec_rows(preset: dict) -> list[CulvertGeometrySpec]:
    rows: list[CulvertGeometrySpec] = []
    for spec in list(preset.get("rows", []) or []):
        values = dict(spec.get("culvert", {}) or {})
        geometry_spec_ref = str(spec.get("spec", "") or "")
        if not geometry_spec_ref or not values:
            continue
        rows.append(
            CulvertGeometrySpec(
                geometry_spec_ref=geometry_spec_ref,
                barrel_shape=str(values.get("barrel_shape", "box") or "box"),
                barrel_count=int(values.get("barrel_count", 1) or 1),
                span=float(values.get("span", 0.0) or 0.0),
                rise=float(values.get("rise", 0.0) or 0.0),
                diameter=float(values.get("diameter", 0.0) or 0.0),
                wall_thickness=float(values.get("wall_thickness", 0.0) or 0.0),
                length=float(values.get("length", 0.0) or 0.0),
                invert_elevation=_optional_float_text(values.get("invert_elevation", "")),
                inlet_skew_angle_deg=float(values.get("inlet_skew_angle_deg", 0.0) or 0.0),
                outlet_skew_angle_deg=float(values.get("outlet_skew_angle_deg", 0.0) or 0.0),
                headwall_type=str(values.get("headwall_type", "") or ""),
                wingwall_type=str(values.get("wingwall_type", "") or ""),
            )
        )
    return rows


def _preset_retaining_wall_geometry_spec_rows(preset: dict) -> list[RetainingWallGeometrySpec]:
    rows: list[RetainingWallGeometrySpec] = []
    for spec in list(preset.get("rows", []) or []):
        values = dict(spec.get("retaining_wall", {}) or {})
        geometry_spec_ref = str(spec.get("spec", "") or "")
        if not geometry_spec_ref or not values:
            continue
        rows.append(
            RetainingWallGeometrySpec(
                geometry_spec_ref=geometry_spec_ref,
                wall_height=float(values.get("wall_height", 0.0) or 0.0),
                wall_thickness=float(values.get("wall_thickness", 0.0) or 0.0),
                footing_width=float(values.get("footing_width", 0.0) or 0.0),
                footing_thickness=float(values.get("footing_thickness", 0.0) or 0.0),
                retained_side=str(values.get("retained_side", "") or ""),
                top_elevation_mode=str(values.get("top_elevation_mode", "") or ""),
                bottom_elevation_mode=str(values.get("bottom_elevation_mode", "") or ""),
                batter_slope=float(values.get("batter_slope", 0.0) or 0.0),
                coping_height=float(values.get("coping_height", 0.0) or 0.0),
                drainage_layer_ref=str(values.get("drainage_layer_ref", "") or ""),
            )
        )
    return rows


def _filter_kind_specs(rows, geometry_spec_rows: list[StructureGeometrySpec]) -> list:
    geometry_spec_ids = {str(row.geometry_spec_id) for row in geometry_spec_rows}
    return [
        row
        for row in list(rows or [])
        if str(getattr(row, "geometry_spec_ref", "") or "") in geometry_spec_ids
    ]


def _replace_kind_spec(rows, new_row):
    output = []
    replaced = False
    new_ref = str(getattr(new_row, "geometry_spec_ref", "") or "")
    for row in list(rows or []):
        if str(getattr(row, "geometry_spec_ref", "") or "") == new_ref:
            output.append(new_row)
            replaced = True
        else:
            output.append(row)
    if not replaced:
        output.append(new_row)
    return output


def _kind_detail_field_specs(structure_kind: str) -> list[tuple[str, str]]:
    kind = str(structure_kind or "").strip().lower()
    if kind == "bridge":
        return [
            ("deck_width", "Deck Width"),
            ("deck_thickness", "Deck Thickness"),
            ("girder_depth", "Girder Depth"),
            ("barrier_height", "Barrier Height"),
            ("clearance_height", "Clearance Height"),
            ("abutment_start_offset", "Abutment Start Offset"),
            ("abutment_end_offset", "Abutment End Offset"),
            ("pier_station_refs", "Pier Station Refs"),
            ("approach_slab_length", "Approach Slab Length"),
            ("bearing_elevation_mode", "Bearing Elevation Mode"),
        ]
    if kind == "culvert":
        return [
            ("barrel_shape", "Barrel Shape"),
            ("barrel_count", "Barrel Count"),
            ("span", "Span"),
            ("rise", "Rise"),
            ("diameter", "Diameter"),
            ("wall_thickness", "Wall Thickness"),
            ("length", "Length"),
            ("invert_elevation", "Invert Elevation"),
            ("headwall_type", "Headwall Type"),
            ("wingwall_type", "Wingwall Type"),
        ]
    if kind in {"retaining_wall", "wall"}:
        return [
            ("wall_height", "Wall Height"),
            ("wall_thickness", "Wall Thickness"),
            ("footing_width", "Footing Width"),
            ("footing_thickness", "Footing Thickness"),
            ("retained_side", "Retained Side"),
            ("top_elevation_mode", "Top Elevation Mode"),
            ("bottom_elevation_mode", "Bottom Elevation Mode"),
            ("batter_slope", "Batter Slope"),
            ("coping_height", "Coping Height"),
            ("drainage_layer_ref", "Drainage Layer Ref"),
        ]
    return []


def _kind_detail_values(
    structure_kind: str,
    geometry_spec_ref: str,
    bridge_rows: list[BridgeGeometrySpec],
    culvert_rows: list[CulvertGeometrySpec],
    retaining_wall_rows: list[RetainingWallGeometrySpec],
) -> dict[str, str]:
    kind = str(structure_kind or "").strip().lower()
    if kind == "bridge":
        row = _find_kind_spec(bridge_rows, geometry_spec_ref) or BridgeGeometrySpec(geometry_spec_ref=geometry_spec_ref)
        return {
            "deck_width": _format_float(row.deck_width),
            "deck_thickness": _format_float(row.deck_thickness),
            "girder_depth": _format_float(row.girder_depth),
            "barrier_height": _format_float(row.barrier_height),
            "clearance_height": _format_float(row.clearance_height),
            "abutment_start_offset": _format_float(row.abutment_start_offset),
            "abutment_end_offset": _format_float(row.abutment_end_offset),
            "pier_station_refs": ", ".join(list(row.pier_station_refs or [])),
            "approach_slab_length": _format_float(row.approach_slab_length),
            "bearing_elevation_mode": row.bearing_elevation_mode,
        }
    if kind == "culvert":
        row = _find_kind_spec(culvert_rows, geometry_spec_ref) or CulvertGeometrySpec(geometry_spec_ref=geometry_spec_ref)
        return {
            "barrel_shape": row.barrel_shape,
            "barrel_count": str(int(row.barrel_count)),
            "span": _format_float(row.span),
            "rise": _format_float(row.rise),
            "diameter": _format_float(row.diameter),
            "wall_thickness": _format_float(row.wall_thickness),
            "length": _format_float(row.length),
            "invert_elevation": _format_optional_float(row.invert_elevation),
            "headwall_type": row.headwall_type,
            "wingwall_type": row.wingwall_type,
        }
    if kind in {"retaining_wall", "wall"}:
        row = _find_kind_spec(retaining_wall_rows, geometry_spec_ref) or RetainingWallGeometrySpec(geometry_spec_ref=geometry_spec_ref)
        return {
            "wall_height": _format_float(row.wall_height),
            "wall_thickness": _format_float(row.wall_thickness),
            "footing_width": _format_float(row.footing_width),
            "footing_thickness": _format_float(row.footing_thickness),
            "retained_side": row.retained_side,
            "top_elevation_mode": row.top_elevation_mode,
            "bottom_elevation_mode": row.bottom_elevation_mode,
            "batter_slope": _format_float(row.batter_slope),
            "coping_height": _format_float(row.coping_height),
            "drainage_layer_ref": row.drainage_layer_ref,
        }
    return {}


def _find_kind_spec(rows, geometry_spec_ref: str):
    for row in list(rows or []):
        if str(getattr(row, "geometry_spec_ref", "") or "") == str(geometry_spec_ref or ""):
            return row
    return None


def _bridge_spec_from_detail(geometry_spec_ref: str, values: dict[str, str]) -> BridgeGeometrySpec:
    return BridgeGeometrySpec(
        geometry_spec_ref=geometry_spec_ref,
        deck_width=_required_float(values.get("deck_width", "0"), "Deck Width"),
        deck_thickness=_required_float(values.get("deck_thickness", "0"), "Deck Thickness"),
        girder_depth=_required_float(values.get("girder_depth", "0"), "Girder Depth"),
        barrier_height=_required_float(values.get("barrier_height", "0"), "Barrier Height"),
        clearance_height=_required_float(values.get("clearance_height", "0"), "Clearance Height"),
        abutment_start_offset=_required_float(values.get("abutment_start_offset", "0"), "Abutment Start Offset"),
        abutment_end_offset=_required_float(values.get("abutment_end_offset", "0"), "Abutment End Offset"),
        pier_station_refs=_csv_text_values(values.get("pier_station_refs", "")),
        approach_slab_length=_required_float(values.get("approach_slab_length", "0"), "Approach Slab Length"),
        bearing_elevation_mode=str(values.get("bearing_elevation_mode", "") or ""),
    )


def _culvert_spec_from_detail(geometry_spec_ref: str, values: dict[str, str]) -> CulvertGeometrySpec:
    return CulvertGeometrySpec(
        geometry_spec_ref=geometry_spec_ref,
        barrel_shape=str(values.get("barrel_shape", "box") or "box"),
        barrel_count=int(_required_float(values.get("barrel_count", "1"), "Barrel Count")),
        span=_required_float(values.get("span", "0"), "Span"),
        rise=_required_float(values.get("rise", "0"), "Rise"),
        diameter=_required_float(values.get("diameter", "0"), "Diameter"),
        wall_thickness=_required_float(values.get("wall_thickness", "0"), "Wall Thickness"),
        length=_required_float(values.get("length", "0"), "Length"),
        invert_elevation=_optional_float_text(values.get("invert_elevation", "")),
        headwall_type=str(values.get("headwall_type", "") or ""),
        wingwall_type=str(values.get("wingwall_type", "") or ""),
    )


def _retaining_wall_spec_from_detail(geometry_spec_ref: str, values: dict[str, str]) -> RetainingWallGeometrySpec:
    return RetainingWallGeometrySpec(
        geometry_spec_ref=geometry_spec_ref,
        wall_height=_required_float(values.get("wall_height", "0"), "Wall Height"),
        wall_thickness=_required_float(values.get("wall_thickness", "0"), "Wall Thickness"),
        footing_width=_required_float(values.get("footing_width", "0"), "Footing Width"),
        footing_thickness=_required_float(values.get("footing_thickness", "0"), "Footing Thickness"),
        retained_side=str(values.get("retained_side", "") or ""),
        top_elevation_mode=str(values.get("top_elevation_mode", "") or ""),
        bottom_elevation_mode=str(values.get("bottom_elevation_mode", "") or ""),
        batter_slope=_required_float(values.get("batter_slope", "0"), "Batter Slope"),
        coping_height=_required_float(values.get("coping_height", "0"), "Coping Height"),
        drainage_layer_ref=str(values.get("drainage_layer_ref", "") or ""),
    )


def _csv_text_values(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _document_station_range(document, alignment_obj=None) -> tuple[float, float]:
    stationing = find_v1_stationing(document)
    stations = list(getattr(stationing, "StationValues", []) or []) if stationing is not None else []
    values = []
    for station in stations:
        try:
            values.append(float(station))
        except Exception:
            pass
    if values:
        return min(values), max(values)
    try:
        total_length = float(getattr(alignment_obj, "TotalLength", 0.0) or 0.0)
        if total_length > 0.0:
            return 0.0, total_length
    except Exception:
        pass
    return 0.0, 100.0


def _format_validation_result(structure_model: StructureModel, *, document=None) -> str:
    diagnostics = validate_structure_model(structure_model)
    lines = ["Validation status: " + ("warning" if diagnostics else "ok")]
    if not diagnostics:
        lines.append("No diagnostics.")
    else:
        lines.append("Diagnostics:")
        lines.extend(f"- {row}" for row in diagnostics)
    package_obj = find_v1_exchange_package(document)
    if package_obj is not None:
        lines.append(
            "Export readiness: "
            + str(getattr(package_obj, "ExportReadinessStatus", "") or "unknown")
            + f" ({int(getattr(package_obj, 'ExportDiagnosticCount', 0) or 0)} diagnostics)"
        )
    else:
        lines.append("Export readiness: not built")
    lines.append(f"Structure rows: {len(list(structure_model.structure_rows or []))}")
    return "\n".join(lines)


def _make_structure_preview_shape(document, structure_model: StructureModel):
    rows = list(getattr(structure_model, "structure_rows", []) or [])
    path = _structure_preview_path_source(document)
    context = _structure_preview_context(structure_model)
    shapes = []
    for row in rows:
        shape = _structure_row_preview_shape(row, path, context)
        if shape is not None:
            shapes.append(shape)
    if not shapes:
        return Part.Shape()
    return Part.Compound(shapes)


def _structure_row_preview_shape(row: StructureRow, path: dict[str, object], context: dict[str, object]):
    placement = getattr(row, "placement", None)
    if placement is None:
        return None
    start_sta = float(getattr(placement, "station_start", 0.0) or 0.0)
    end_sta = float(getattr(placement, "station_end", start_sta) or start_sta)
    if end_sta < start_sta:
        start_sta, end_sta = end_sta, start_sta
    offset = float(getattr(placement, "offset", 0.0) or 0.0)
    half_width, height = _structure_preview_size(row, context)
    base_z = _structure_preview_base_z(row, context)
    stations = _structure_preview_sample_stations(start_sta, end_sta, path)
    points = [_station_offset_xyz(path, station, offset, base_z) for station in stations]
    segment_shapes = []
    for point0, point1 in zip(points, points[1:]):
        segment = _structure_segment_prism(point0, point1, half_width, height)
        if segment is not None:
            segment_shapes.append(segment)
    if not segment_shapes:
        return None
    return Part.Compound(segment_shapes)


def _structure_segment_prism(point0, point1, half_width: float, height: float):
    x0, y0, z0 = point0
    x1, y1, z1 = point1
    dx = float(x1) - float(x0)
    dy = float(y1) - float(y0)
    length = math.hypot(dx, dy)
    if length <= 1.0e-9:
        return None
    nx = -dy / length
    ny = dx / length
    z_base0 = float(z0)
    z_base1 = float(z1)
    corners = [
        App.Vector(x0 + nx * half_width, y0 + ny * half_width, z_base0),
        App.Vector(x1 + nx * half_width, y1 + ny * half_width, z_base1),
        App.Vector(x1 - nx * half_width, y1 - ny * half_width, z_base1),
        App.Vector(x0 - nx * half_width, y0 - ny * half_width, z_base0),
        App.Vector(x0 + nx * half_width, y0 + ny * half_width, z_base0),
    ]
    try:
        face = Part.Face(Part.makePolygon(corners))
        return face.extrude(App.Vector(0.0, 0.0, height))
    except Exception:
        try:
            return Part.makePolygon(corners)
        except Exception:
            return None


def _structure_preview_path_source(document) -> dict[str, object]:
    centerline = _applied_section_centerline_path_source(document)
    if centerline is not None:
        return centerline
    alignment_adapter = _station_offset_adapter(document)
    if alignment_adapter is not None:
        return {
            "source": "alignment",
            "adapter": lambda station, offset: (*_station_offset_xy(alignment_adapter, station, offset), 0.0),
            "stations": [],
        }
    return {
        "source": "station_offset_fallback",
        "adapter": lambda station, offset: (float(station), float(offset), 0.0),
        "stations": [],
    }


def _structure_preview_path_source_name(document) -> str:
    return str(_structure_preview_path_source(document).get("source", "") or "")


def _applied_section_centerline_path_source(document) -> dict[str, object] | None:
    applied_obj = find_v1_applied_section_set(document)
    applied = to_applied_section_set(applied_obj)
    if applied is None:
        return None
    frames = []
    for section in list(getattr(applied, "sections", []) or []):
        frame = getattr(section, "frame", None)
        if frame is None:
            continue
        frames.append(
            {
                "station": float(getattr(frame, "station", getattr(section, "station", 0.0)) or 0.0),
                "x": float(getattr(frame, "x", 0.0) or 0.0),
                "y": float(getattr(frame, "y", 0.0) or 0.0),
                "z": float(getattr(frame, "z", 0.0) or 0.0),
                "tangent": float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0),
            }
        )
    frames.sort(key=lambda row: row["station"])
    if len(frames) < 2:
        return None

    def _adapter(station: float, offset: float) -> tuple[float, float, float]:
        return _interpolate_centerline_station_offset(frames, station, offset)

    return {
        "source": "3d_centerline",
        "adapter": _adapter,
        "stations": [row["station"] for row in frames],
    }


def _interpolate_centerline_station_offset(frames: list[dict[str, float]], station: float, offset: float) -> tuple[float, float, float]:
    station = float(station)
    lower = frames[0]
    upper = frames[-1]
    for index in range(len(frames) - 1):
        current = frames[index]
        next_row = frames[index + 1]
        if current["station"] <= station <= next_row["station"]:
            lower = current
            upper = next_row
            break
    span = max(float(upper["station"]) - float(lower["station"]), 0.0)
    ratio = 0.0 if span <= 1.0e-9 else max(0.0, min(1.0, (station - float(lower["station"])) / span))
    x = float(lower["x"]) + (float(upper["x"]) - float(lower["x"])) * ratio
    y = float(lower["y"]) + (float(upper["y"]) - float(lower["y"])) * ratio
    z = float(lower["z"]) + (float(upper["z"]) - float(lower["z"])) * ratio
    dx = float(upper["x"]) - float(lower["x"])
    dy = float(upper["y"]) - float(lower["y"])
    length = math.hypot(dx, dy)
    if length > 1.0e-9:
        nx = -dy / length
        ny = dx / length
    else:
        heading = math.radians(float(lower.get("tangent", 0.0) or 0.0))
        nx = -math.sin(heading)
        ny = math.cos(heading)
    return x + float(offset) * nx, y + float(offset) * ny, z


def _structure_preview_sample_stations(start_sta: float, end_sta: float, path: dict[str, object]) -> list[float]:
    span = max(float(end_sta) - float(start_sta), 0.0)
    if span <= 1.0e-9:
        return [float(start_sta), float(start_sta) + 1.0]
    count = max(2, min(32, int(math.ceil(span / 10.0)) + 1))
    values = [float(start_sta) + span * index / float(count - 1) for index in range(count)]
    for station in list(path.get("stations", []) or []):
        value = float(station)
        if float(start_sta) < value < float(end_sta):
            values.append(value)
    return sorted({round(value, 9) for value in values})


def _station_offset_adapter(document):
    alignment_obj = find_v1_alignment(document)
    alignment_model = to_alignment_model(alignment_obj) if alignment_obj is not None else None
    if alignment_model is None:
        return None
    try:
        return AlignmentEvaluationService().station_offset_adapter(alignment_model)
    except Exception:
        return None


def _station_offset_xy(adapter, station: float, offset: float) -> tuple[float, float]:
    if adapter is not None:
        try:
            x, y = adapter(float(station), float(offset))
            return float(x), float(y)
        except Exception:
            pass
    return float(station), float(offset)


def _station_offset_xyz(path: dict[str, object], station: float, offset: float, base_z: float) -> tuple[float, float, float]:
    adapter = path.get("adapter", None)
    if adapter is not None:
        try:
            x, y, z = adapter(float(station), float(offset))
            return float(x), float(y), float(z) + float(base_z)
        except Exception:
            pass
    return float(station), float(offset), float(base_z)


def _structure_preview_context(structure_model: StructureModel) -> dict[str, object]:
    geometry_specs = {
        str(row.geometry_spec_id): row
        for row in list(getattr(structure_model, "geometry_spec_rows", []) or [])
    }
    return {
        "geometry_specs": geometry_specs,
        "bridge_specs": {
            str(row.geometry_spec_ref): row
            for row in list(getattr(structure_model, "bridge_geometry_spec_rows", []) or [])
        },
        "culvert_specs": {
            str(row.geometry_spec_ref): row
            for row in list(getattr(structure_model, "culvert_geometry_spec_rows", []) or [])
        },
        "retaining_wall_specs": {
            str(row.geometry_spec_ref): row
            for row in list(getattr(structure_model, "retaining_wall_geometry_spec_rows", []) or [])
        },
    }


def _structure_geometry_spec_for_row(row: StructureRow, context: dict[str, object]) -> StructureGeometrySpec | None:
    specs = context.get("geometry_specs", {})
    if not isinstance(specs, dict):
        return None
    spec_ref = str(getattr(row, "geometry_spec_ref", "") or "")
    spec = specs.get(spec_ref)
    if spec is not None:
        return spec
    structure_id = str(getattr(row, "structure_id", "") or "")
    for candidate in specs.values():
        if str(getattr(candidate, "structure_ref", "") or "") == structure_id:
            return candidate
    return None


def _kind_spec_for_ref(values, geometry_spec_ref: str):
    if not isinstance(values, dict):
        return None
    return values.get(str(geometry_spec_ref or ""))


def _structure_preview_review_notes(structure_model: StructureModel, context: dict[str, object]) -> list[str]:
    notes = []
    for row in list(getattr(structure_model, "structure_rows", []) or []):
        structure_id = str(getattr(row, "structure_id", "") or "")
        spec = _structure_geometry_spec_for_row(row, context)
        if spec is None:
            notes.append(f"warning|geometry_spec|{structure_id}|Preview used fallback dimensions because no native geometry spec was found.")
            continue
        if float(getattr(spec, "skew_angle_deg", 0.0) or 0.0) != 0.0:
            notes.append(f"warning|skew_angle|{structure_id}|Preview records skew but does not yet skew generated review geometry.")
        kind = str(getattr(row, "structure_kind", "") or "").strip().lower()
        spec_ref = str(getattr(spec, "geometry_spec_id", "") or "")
        if kind == "culvert":
            culvert = _kind_spec_for_ref(context.get("culvert_specs", {}), spec_ref)
            barrel_shape = str(getattr(culvert, "barrel_shape", "") or getattr(spec, "shape_kind", "") or "")
            if barrel_shape and barrel_shape not in {"box", "rectangular", "circular"}:
                notes.append(f"warning|culvert_shape|{structure_id}|Preview uses a simplified envelope for unsupported culvert shape {barrel_shape}.")
        elif kind not in {"bridge", "retaining_wall", "wall", "utility", "custom"}:
            notes.append(f"warning|structure_kind|{structure_id}|Preview uses a generic envelope for unsupported structure kind {kind}.")
    return notes


def _structure_preview_size(row: StructureRow, context: dict[str, object] | None = None) -> tuple[float, float]:
    context = context or {}
    spec = _structure_geometry_spec_for_row(row, context)
    width = float(getattr(spec, "width", 0.0) or 0.0) if spec is not None else 0.0
    height = float(getattr(spec, "height", 0.0) or 0.0) if spec is not None else 0.0
    kind = str(getattr(row, "structure_kind", "") or "").strip().lower()
    if kind == "bridge":
        bridge = _kind_spec_for_ref(context.get("bridge_specs", {}), getattr(row, "geometry_spec_ref", ""))
        width = float(getattr(bridge, "deck_width", 0.0) or width or 10.0) if bridge is not None else width
        height = float(getattr(bridge, "deck_thickness", 0.0) or height or 1.2) if bridge is not None else height
        return max(width, 10.0) / 2.0, max(height, 1.2)
    if kind == "culvert":
        culvert = _kind_spec_for_ref(context.get("culvert_specs", {}), getattr(row, "geometry_spec_ref", ""))
        if culvert is not None:
            width = float(getattr(culvert, "span", 0.0) or getattr(culvert, "diameter", 0.0) or width or 3.0)
            height = float(getattr(culvert, "rise", 0.0) or getattr(culvert, "diameter", 0.0) or height or 1.5)
        return max(width, 3.0) / 2.0, max(height, 1.5)
    if kind in {"retaining_wall", "wall"}:
        wall = _kind_spec_for_ref(context.get("retaining_wall_specs", {}), getattr(row, "geometry_spec_ref", ""))
        if wall is not None:
            width = float(getattr(wall, "wall_thickness", 0.0) or width or 0.9)
            height = float(getattr(wall, "wall_height", 0.0) or height or 3.0)
        return max(width, 0.9) / 2.0, max(height, 3.0)
    if kind == "utility":
        return max(width, 1.5) / 2.0, max(height, 0.75)
    return max(width, 4.0) / 2.0, max(height, 1.0)


def _structure_preview_base_z(row: StructureRow, context: dict[str, object] | None = None) -> float:
    context = context or {}
    spec = _structure_geometry_spec_for_row(row, context)
    base_elevation = getattr(spec, "base_elevation", None) if spec is not None else None
    if base_elevation is not None:
        try:
            return float(base_elevation)
        except Exception:
            pass
    placement = getattr(row, "placement", None)
    value = str(getattr(placement, "elevation_reference", "") or "").strip() if placement is not None else ""
    try:
        return float(value)
    except Exception:
        return 0.0


def _style_structure_preview_object(obj) -> None:
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return
        vobj.Visibility = True
        vobj.ShapeColor = (0.45, 0.68, 0.95)
        vobj.LineColor = (0.08, 0.18, 0.32)
        vobj.PointColor = (0.95, 0.85, 0.20)
        vobj.Transparency = 35
        vobj.LineWidth = 2.0
    except Exception:
        pass


def _set_preview_string_property(obj, name: str, value: str) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyString", name, "CorridorRoad", name)
        except Exception:
            pass
    try:
        setattr(obj, name, str(value or ""))
    except Exception:
        pass


def _set_preview_integer_property(obj, name: str, value: int) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyInteger", name, "CorridorRoad", name)
        except Exception:
            pass
    try:
        setattr(obj, name, int(value or 0))
    except Exception:
        pass


def _set_preview_string_list_property(obj, name: str, values: list[str]) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyStringList", name, "CorridorRoad", name)
        except Exception:
            pass
    try:
        setattr(obj, name, [str(value) for value in list(values or [])])
    except Exception:
        pass


def _alignment_id(document) -> str:
    alignment = find_v1_alignment(document)
    return str(getattr(alignment, "AlignmentId", "") or "")


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _required_float(value: object, label: str) -> float:
    try:
        return float(value)
    except Exception:
        raise ValueError(f"{label} must be a number.") from None


def _item_text(table, row: int, col: int) -> str:
    widget = table.cellWidget(row, col)
    if widget is not None and hasattr(widget, "currentText"):
        return str(widget.currentText() or "").strip()
    item = table.item(row, col)
    return str(item.text() if item is not None else "").strip()


def _item_user_data(table, row: int, col: int) -> str:
    item = table.item(row, col)
    if item is None:
        return ""
    try:
        return str(item.data(QtCore.Qt.UserRole) or "").strip()
    except Exception:
        return ""


def _format_float(value: float) -> str:
    return f"{float(value):.3f}"


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return _format_float(float(value))


def _optional_float_text(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    return _required_float(text, "Optional elevation")


def _default_shape_kind(structure_kind: str) -> str:
    kind = str(structure_kind or "").strip().lower()
    if kind == "bridge":
        return "deck_slab"
    if kind == "culvert":
        return "box"
    if kind in {"retaining_wall", "wall"}:
        return "wall"
    if kind == "utility":
        return "envelope"
    return "envelope"


def _default_geometry_width(structure_kind: str) -> float:
    kind = str(structure_kind or "").strip().lower()
    if kind == "bridge":
        return 10.0
    if kind == "culvert":
        return 3.0
    if kind in {"retaining_wall", "wall"}:
        return 0.9
    if kind == "utility":
        return 1.5
    return 4.0


def _default_geometry_height(structure_kind: str) -> float:
    kind = str(structure_kind or "").strip().lower()
    if kind == "bridge":
        return 1.2
    if kind == "culvert":
        return 2.0
    if kind in {"retaining_wall", "wall"}:
        return 3.0
    if kind == "utility":
        return 1.5
    return 1.0


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditStructures", CmdV1StructureEditor())
