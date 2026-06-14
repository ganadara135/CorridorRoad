"""Assembly/Subassembly editor command for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

from ...objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from ..models.source.assembly_model import (
    ASSEMBLY_SUBASSEMBLY_KINDS,
    ASSEMBLY_SUBASSEMBLY_SIDES,
    AssemblySubassemblyModel,
    SubassemblySectionTemplate,
    TemplateSubassembly,
    normalize_bench_rows,
    parse_subassembly_parameters,
    serialize_subassembly_parameters,
    subassembly_bench_validation_messages,
)
from ..objects.obj_alignment import find_v1_alignment
from ..objects.obj_subassembly_assembly import (
    create_or_update_v1_assembly_subassembly_model_object,
    find_v1_assembly_subassembly_model,
    to_assembly_subassembly_model,
)
from .cmd_assembly_editor import (
    ASSEMBLY_BENCH_MODES,
    ASSEMBLY_DAYLIGHT_MODES,
    ASSEMBLY_PRESETS,
    DITCH_PARAMETER_FIELDS,
    DITCH_PARAMETER_KEYS,
    DITCH_SHAPE_DEFAULTS,
    DITCH_SHAPES,
    assembly_preset_names,
)


SUBASSEMBLY_COLUMNS = (
    "Enabled",
    "Subassembly ID",
    "Kind",
    "Side",
    "Width",
    "Slope",
    "Thickness",
    "Material",
    "Target Ref",
    "Parameters",
    "Notes",
)


def run_v1_assembly_subassembly_editor_command():
    """Open the v1 Assembly/Subassembly editor panel."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    panel = V1AssemblySubassemblyEditorTaskPanel(document=document)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return find_v1_assembly_subassembly_model(document)


def apply_v1_assembly_subassembly_model(
    *,
    document=None,
    project=None,
    assembly_model: AssemblySubassemblyModel,
    assembly_obj=None,
    object_name: str | None = None,
):
    """Persist a v1 AssemblySubassemblyModel source object."""

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
        prj.Label = "Parametric Road Project"
    ensure_project_properties(prj)
    ensure_project_tree(prj, include_references=False)
    target_name = str(object_name or getattr(assembly_obj, "Name", "") or "V1AssemblySubassemblyModel")
    obj = create_or_update_v1_assembly_subassembly_model_object(
        document=doc,
        project=prj,
        assembly_model=assembly_model,
        object_name=target_name,
    )
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def assembly_subassembly_preset_model_from_document(
    preset_name: str,
    document=None,
    *,
    project=None,
    alignment=None,
) -> AssemblySubassemblyModel:
    """Build a non-destructive AssemblySubassemblyModel from an Assembly preset."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    preset = ASSEMBLY_PRESETS.get(str(preset_name or "").strip())
    if preset is None:
        raise ValueError(f"Unknown Assembly preset: {preset_name}")
    prj = project or find_project(doc)
    alignment_obj = alignment or find_v1_alignment(doc)
    alignment_id = str(getattr(alignment_obj, "AlignmentId", "") or "")
    template_id = str(preset.get("template_id", "") or "template:subassembly")
    return AssemblySubassemblyModel(
        schema_version=1,
        project_id=_project_id(prj),
        assembly_id=str(preset.get("assembly_id", "") or "assembly:subassembly-main"),
        alignment_id=alignment_id,
        active_template_id=template_id,
        label=str(preset.get("label", "") or str(preset_name or "Assembly / Subassembly")),
        template_rows=[
            SubassemblySectionTemplate(
                template_id=template_id,
                template_kind="roadway",
                template_index=1,
                label=str(preset.get("template_label", "") or template_id),
                subassembly_rows=_preset_subassemblies(preset),
                notes=str(preset.get("note", "") or "Subassembly preset; edit before section generation."),
            )
        ],
    )


class V1AssemblySubassemblyEditorTaskPanel:
    """Table-based v1 Assembly/Subassembly source editor."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.assembly_obj = find_v1_assembly_subassembly_model(self.document)
        self.model = to_assembly_subassembly_model(self.assembly_obj) if self.assembly_obj is not None else None
        if self.model is None:
            self.model = assembly_subassembly_preset_model_from_document("Basic Road", document=self.document)
        self.form = self._build_form()
        self._load_model(self.model)

    def getStandardButtons(self):  # noqa: N802 - Qt API name
        return 0

    def _build_form(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        title = QtWidgets.QLabel("Assembly / Subassembly")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        description = QtWidgets.QLabel(
            "Define assembly intent with explicit Subassembly rows. The existing Assembly panel remains available during transition."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Preset:"))
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItems(assembly_preset_names())
        preset_row.addWidget(self.preset_combo, 1)
        self.load_preset_button = QtWidgets.QPushButton("Load Preset")
        self.load_preset_button.clicked.connect(self._load_selected_preset)
        preset_row.addWidget(self.load_preset_button)
        layout.addLayout(preset_row)

        ids_row = QtWidgets.QHBoxLayout()
        ids_row.addWidget(QtWidgets.QLabel("Assembly ID:"))
        self.assembly_id_edit = QtWidgets.QLineEdit()
        ids_row.addWidget(self.assembly_id_edit, 1)
        ids_row.addWidget(QtWidgets.QLabel("Template ID:"))
        self.template_id_edit = QtWidgets.QLineEdit()
        ids_row.addWidget(self.template_id_edit, 1)
        layout.addLayout(ids_row)

        self.table = QtWidgets.QTableWidget(0, len(SUBASSEMBLY_COLUMNS))
        self.table.setHorizontalHeaderLabels(SUBASSEMBLY_COLUMNS)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._refresh_selected_detail)
        layout.addWidget(self.table, 1)

        self.detail_group = QtWidgets.QGroupBox("Selected Subassembly Detail")
        detail_layout = QtWidgets.QVBoxLayout(self.detail_group)
        self.detail_summary = QtWidgets.QLabel("Select a Subassembly row.")
        self.detail_summary.setWordWrap(True)
        detail_layout.addWidget(self.detail_summary)
        self.detail_table = QtWidgets.QTableWidget(0, 2)
        self.detail_table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.detail_table.horizontalHeader().setStretchLastSection(True)
        detail_layout.addWidget(self.detail_table)
        preview_label = QtWidgets.QLabel("Point / Link / Shape Preview")
        preview_label.setStyleSheet("font-weight: 600;")
        detail_layout.addWidget(preview_label)
        self.detail_preview = QtWidgets.QPlainTextEdit()
        self.detail_preview.setReadOnly(True)
        self.detail_preview.setMinimumHeight(110)
        detail_layout.addWidget(self.detail_preview)
        detail_button_row = QtWidgets.QHBoxLayout()
        self.load_detail_defaults_button = QtWidgets.QPushButton("Load Detail Defaults")
        self.load_detail_defaults_button.clicked.connect(self._load_selected_detail_defaults)
        detail_button_row.addWidget(self.load_detail_defaults_button)
        self.add_bench_row_button = QtWidgets.QPushButton("Add Bench Row")
        self.add_bench_row_button.clicked.connect(self._add_detail_bench_row)
        detail_button_row.addWidget(self.add_bench_row_button)
        self.apply_detail_button = QtWidgets.QPushButton("Apply Detail")
        self.apply_detail_button.clicked.connect(self._apply_selected_detail)
        detail_button_row.addWidget(self.apply_detail_button)
        detail_button_row.addStretch(1)
        detail_layout.addLayout(detail_button_row)
        layout.addWidget(self.detail_group)

        button_row = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Add Subassembly")
        self.add_button.clicked.connect(self._add_row)
        button_row.addWidget(self.add_button)
        self.delete_button = QtWidgets.QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self._delete_selected)
        button_row.addWidget(self.delete_button)
        self.validate_button = QtWidgets.QPushButton("Validate")
        self.validate_button.clicked.connect(self._validate)
        button_row.addWidget(self.validate_button)
        self.apply_button = QtWidgets.QPushButton("Apply")
        self.apply_button.clicked.connect(self._apply)
        button_row.addWidget(self.apply_button)
        button_row.addStretch(1)
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self._close)
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)

        self.summary = QtWidgets.QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMinimumHeight(90)
        layout.addWidget(self.summary)
        return widget

    def _load_model(self, model: AssemblySubassemblyModel) -> None:
        self.model = model
        self.assembly_id_edit.setText(str(model.assembly_id or ""))
        template = _active_template(model)
        self.template_id_edit.setText(str(getattr(template, "template_id", "") or ""))
        rows = list(getattr(template, "subassembly_rows", []) or [])
        self.table.setRowCount(0)
        for row in rows:
            self._append_subassembly(row)
        if rows:
            self.table.selectRow(0)
        self._refresh_selected_detail()
        self.summary.setPlainText(f"Loaded {len(rows)} subassembly rows. Apply writes a V1AssemblySubassemblyModel source object.")

    def _load_selected_preset(self) -> None:
        try:
            model = assembly_subassembly_preset_model_from_document(self.preset_combo.currentText(), document=self.document)
            self._load_model(model)
        except Exception as exc:
            _show_message(self.form, "Assembly / Subassembly", f"Preset load failed: {exc}")

    def _append_subassembly(self, subassembly: TemplateSubassembly) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        enabled_item = QtWidgets.QTableWidgetItem("Yes" if subassembly.enabled else "No")
        self.table.setItem(row, 0, enabled_item)
        self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(subassembly.subassembly_id)))
        self._set_combo(row, 2, ASSEMBLY_SUBASSEMBLY_KINDS, subassembly.kind)
        self._set_combo(row, 3, ASSEMBLY_SUBASSEMBLY_SIDES, subassembly.side)
        self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(_format_float(subassembly.width)))
        self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(_format_float(subassembly.slope)))
        self.table.setItem(row, 6, QtWidgets.QTableWidgetItem(_format_float(subassembly.thickness)))
        self.table.setItem(row, 7, QtWidgets.QTableWidgetItem(str(subassembly.material)))
        self.table.setItem(row, 8, QtWidgets.QTableWidgetItem(str(subassembly.target_ref)))
        self.table.setItem(row, 9, QtWidgets.QTableWidgetItem(serialize_subassembly_parameters(subassembly.parameters)))
        self.table.setItem(row, 10, QtWidgets.QTableWidgetItem(str(subassembly.notes)))
        if self.table.rowCount() == 1:
            self.table.selectRow(0)

    def _set_combo(self, row: int, column: int, values: tuple[str, ...], current: str) -> None:
        combo = QtWidgets.QComboBox()
        combo.addItems(list(values))
        index = combo.findText(str(current or ""))
        if index >= 0:
            combo.setCurrentIndex(index)
        self.table.setCellWidget(row, column, combo)

    def _add_row(self) -> None:
        index = self.table.rowCount() + 1
        self._append_subassembly(
            TemplateSubassembly(
                subassembly_id=f"subassembly:{index}",
                kind="lane",
                subassembly_index=index,
                side="center",
                width=3.5,
                slope=-0.02,
                material="asphalt",
            )
        )

    def _delete_selected(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
        self._refresh_selected_detail()

    def _selected_row(self) -> int:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if rows:
            return rows[0]
        return int(self.table.currentRow())

    def _refresh_selected_detail(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount():
            self.detail_summary.setText("Select a Subassembly row.")
            self.detail_table.setRowCount(0)
            self.detail_preview.setPlainText("")
            self.load_detail_defaults_button.setEnabled(False)
            self.add_bench_row_button.setEnabled(False)
            self.apply_detail_button.setEnabled(False)
            return
        subassembly_id = _item_text(self.table, row, 1)
        kind = _item_text(self.table, row, 2)
        side = _item_text(self.table, row, 3)
        params = parse_subassembly_parameters(_item_text(self.table, row, 9))
        self.detail_summary.setText(
            f"{subassembly_id} | {kind} | {side}\n"
            "Edit kind-specific parameters here, then Apply Detail to write them back to the Subassemblies table."
        )
        rows = _detail_parameter_rows(kind, params)
        self.detail_table.setRowCount(0)
        for key, value in rows:
            detail_row = self.detail_table.rowCount()
            self.detail_table.insertRow(detail_row)
            key_item = QtWidgets.QTableWidgetItem(str(key))
            key_item.setFlags(key_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.detail_table.setItem(detail_row, 0, key_item)
            self.detail_table.setItem(detail_row, 1, QtWidgets.QTableWidgetItem(str(value)))
        self.detail_preview.setPlainText(
            _subassembly_preview_text(
                subassembly_id=subassembly_id,
                kind=kind,
                side=side,
                width=_float(_item_text(self.table, row, 4)),
                slope=_float(_item_text(self.table, row, 5)),
                thickness=_float(_item_text(self.table, row, 6)),
                material=_item_text(self.table, row, 7),
                parameters=params,
            )
        )
        self.load_detail_defaults_button.setEnabled(kind == "ditch")
        self.add_bench_row_button.setEnabled(kind == "side_slope")
        self.apply_detail_button.setEnabled(kind in {"ditch", "side_slope", "lane", "shoulder", "pavement_layer", "subbase"})

    def _load_selected_detail_defaults(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount() or _item_text(self.table, row, 2) != "ditch":
            return
        shape = _detail_value(self.detail_table, "shape") or "trapezoid"
        defaults = dict(DITCH_SHAPE_DEFAULTS.get(shape, DITCH_SHAPE_DEFAULTS["trapezoid"]))
        defaults["shape"] = shape if shape in DITCH_SHAPES else "trapezoid"
        _replace_detail_rows(self.detail_table, _detail_parameter_rows("ditch", defaults))

    def _add_detail_bench_row(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount() or _item_text(self.table, row, 2) != "side_slope":
            return
        bench_rows = normalize_bench_rows(_detail_value(self.detail_table, "bench_rows"))
        bench_rows.append({"drop": 3.0, "width": 1.5, "slope": -0.02, "post_slope": _float(_item_text(self.table, row, 5), -0.5)})
        _set_detail_value(self.detail_table, "bench_mode", "rows")
        _set_detail_value(self.detail_table, "bench_rows", _compact_bench_rows(bench_rows))

    def _apply_selected_detail(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount():
            return
        kind = _item_text(self.table, row, 2)
        existing = parse_subassembly_parameters(_item_text(self.table, row, 9))
        edited = _detail_parameters(self.detail_table)
        params = _merge_detail_parameters(kind, existing, edited)
        _set_table_item_text(self.table, row, 9, serialize_subassembly_parameters(params))
        if kind == "ditch":
            _set_table_item_text(self.table, row, 10, _ditch_detail_note(params))
        elif kind == "side_slope":
            _set_table_item_text(self.table, row, 10, _bench_detail_note(params))
        self._refresh_selected_detail()
        self.summary.setPlainText(f"Detail applied to {_item_text(self.table, row, 1)}.")

    def _build_model_from_ui(self) -> AssemblySubassemblyModel:
        template_id = str(self.template_id_edit.text() or "template:subassembly").strip()
        subassemblies: list[TemplateSubassembly] = []
        for row in range(self.table.rowCount()):
            subassemblies.append(
                TemplateSubassembly(
                    subassembly_id=_item_text(self.table, row, 1) or f"subassembly:{row + 1}",
                    kind=_item_text(self.table, row, 2) or "lane",
                    subassembly_index=row + 1,
                    side=_item_text(self.table, row, 3) or "center",
                    width=_float(_item_text(self.table, row, 4)),
                    slope=_float(_item_text(self.table, row, 5)),
                    thickness=_float(_item_text(self.table, row, 6)),
                    material=_item_text(self.table, row, 7),
                    target_ref=_item_text(self.table, row, 8),
                    parameters=parse_subassembly_parameters(_item_text(self.table, row, 9)),
                    notes=_item_text(self.table, row, 10),
                    enabled=_truthy(_item_text(self.table, row, 0)),
                )
            )
        return AssemblySubassemblyModel(
            schema_version=1,
            project_id=_project_id(find_project(self.document)),
            assembly_id=str(self.assembly_id_edit.text() or "assembly:subassembly-main").strip(),
            active_template_id=template_id,
            template_rows=[
                SubassemblySectionTemplate(
                    template_id=template_id,
                    template_kind="roadway",
                    template_index=1,
                    label=template_id,
                    subassembly_rows=subassemblies,
                    notes="Subassembly-based assembly source.",
                )
            ],
        )

    def _validate(self) -> list[str]:
        model = self._build_model_from_ui()
        messages = _validate_subassembly_model(model)
        status = "ok" if not any(message.startswith("ERROR") for message in messages) else "error"
        self.summary.setPlainText("Validation: " + status + "\n" + ("\n".join(messages) if messages else "No diagnostics."))
        return messages

    def _apply(self) -> None:
        messages = self._validate()
        if any(message.startswith("ERROR") for message in messages):
            _show_message(self.form, "Assembly / Subassembly", "Validation failed. Fix errors before Apply.")
            return
        model = self._build_model_from_ui()
        try:
            self.assembly_obj = apply_v1_assembly_subassembly_model(
                document=self.document,
                assembly_model=model,
                assembly_obj=self.assembly_obj,
            )
            self.summary.setPlainText(
                f"Apply complete.\nAssembly/Subassembly object: {getattr(self.assembly_obj, 'Label', '')}\nSubassemblies: {self.table.rowCount()}"
            )
            _show_message(self.form, "Assembly / Subassembly", "Assembly / Subassembly source applied.")
        except Exception as exc:
            self.summary.setPlainText(f"Apply failed: {exc}")
            _show_message(self.form, "Assembly / Subassembly", f"Apply failed: {exc}")

    def _close(self) -> None:
        if Gui is not None and hasattr(Gui, "Control"):
            Gui.Control.closeDialog()


class CmdV1AssemblySubassemblyEditor:
    """Open the v1 Assembly/Subassembly source editor."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("typical_section.svg"),
            "MenuText": "Assembly / Subassembly",
            "ToolTip": "Define v1 assembly source using explicit Subassembly rows",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_assembly_subassembly_editor_command()


def _preset_subassemblies(preset: dict) -> list[TemplateSubassembly]:
    rows = []
    for index, row in enumerate(_preset_subassembly_rows(preset), start=1):
        subassembly_id, kind, side, width, slope, thickness, material, notes = row[:8]
        parameters = row[8] if len(row) > 8 else {}
        rows.append(
            TemplateSubassembly(
                subassembly_id=str(subassembly_id),
                kind=kind,
                subassembly_index=index,
                side=side,
                width=width,
                slope=slope,
                thickness=thickness,
                material=material,
                parameters=dict(parameters or {}),
                notes=notes,
                enabled=True,
            )
        )
    return rows


def _preset_subassembly_rows(preset: dict) -> list[tuple]:
    """Return active Subassembly preset rows, with old Assembly presets isolated."""

    rows = list(preset.get("subassemblies", []) or [])
    if rows:
        return [tuple(row) for row in rows]
    return _compatibility_component_preset_rows(preset)


def _compatibility_component_preset_rows(preset: dict) -> list[tuple]:
    """Convert old Assembly preset component rows for the Subassembly editor."""

    rows: list[tuple] = []
    for row in list(preset.get("components", []) or []):
        values = list(row)
        if values:
            values[0] = str(values[0]).replace("component:", "subassembly:")
        rows.append(tuple(values))
    return rows


def _validate_subassembly_model(model: AssemblySubassemblyModel) -> list[str]:
    messages: list[str] = []
    if not model.assembly_id:
        messages.append("ERROR: assembly_id is required.")
    if not model.template_rows:
        messages.append("ERROR: at least one template row is required.")
    for template in list(model.template_rows or []):
        if not template.template_id:
            messages.append("ERROR: template_id is required.")
        ids = set()
        for subassembly in list(template.subassembly_rows or []):
            if not subassembly.subassembly_id:
                messages.append("ERROR: subassembly_id is required.")
            if subassembly.subassembly_id in ids:
                messages.append(f"ERROR: duplicate subassembly_id {subassembly.subassembly_id}.")
            ids.add(subassembly.subassembly_id)
            if subassembly.width < 0.0:
                messages.append(f"ERROR: subassembly {subassembly.subassembly_id} width must not be negative.")
            messages.extend(f"WARNING: {message}" for message in subassembly_bench_validation_messages(subassembly))
    return messages


def _active_template(model: AssemblySubassemblyModel) -> SubassemblySectionTemplate | None:
    rows = list(getattr(model, "template_rows", []) or [])
    if not rows:
        return None
    active_id = str(getattr(model, "active_template_id", "") or "").strip()
    for row in rows:
        if str(getattr(row, "template_id", "") or "") == active_id:
            return row
    return rows[0]


def _item_text(table, row: int, col: int) -> str:
    widget = table.cellWidget(row, col)
    if widget is not None and hasattr(widget, "currentText"):
        return str(widget.currentText() or "").strip()
    item = table.item(row, col)
    return str(item.text() if item is not None else "").strip()


def _set_table_item_text(table, row: int, col: int, value: object) -> None:
    item = table.item(row, col)
    if item is None:
        item = QtWidgets.QTableWidgetItem("")
        table.setItem(row, col, item)
    item.setText(str(value or ""))


def _detail_parameter_rows(kind: object, parameters: dict[str, object]) -> list[tuple[str, object]]:
    params = dict(parameters or {})
    kind_text = str(kind or "").strip().lower().replace("-", "_")
    if kind_text == "ditch":
        shape = str(params.get("shape", "") or "trapezoid").strip().lower().replace("-", "_")
        shape = shape if shape in DITCH_SHAPES else "trapezoid"
        keys = ["shape"] + [key for key, _label in DITCH_PARAMETER_FIELDS if key != "shape"]
        return [(key, params.get(key, shape if key == "shape" else "")) for key in keys]
    if kind_text == "side_slope":
        rows = normalize_bench_rows(params.get("bench_rows", []))
        return [
            ("bench_mode", params.get("bench_mode", "none")),
            ("bench_rows", _compact_bench_rows(rows)),
            ("repeat_first_bench_to_daylight", "1" if _truthy(params.get("repeat_first_bench_to_daylight")) else "0"),
            ("daylight_mode", params.get("daylight_mode", "terrain")),
            ("daylight_search_step", params.get("daylight_search_step", "")),
            ("daylight_max_width", params.get("daylight_max_width", "")),
            ("daylight_max_width_delta", params.get("daylight_max_width_delta", "")),
            ("daylight_max_triangles", params.get("daylight_max_triangles", "")),
            ("cut_slope", params.get("cut_slope", "")),
            ("fill_slope", params.get("fill_slope", "")),
        ]
    if kind_text in {"lane", "shoulder"}:
        return [
            ("default_crossfall", params.get("default_crossfall", "")),
            ("superelevation_target", params.get("superelevation_target", "auto")),
            ("point_codes", params.get("point_codes", "")),
            ("link_codes", params.get("link_codes", "")),
            ("surface_role", params.get("surface_role", "design")),
        ]
    if kind_text in {"pavement_layer", "subbase"}:
        return [
            ("layer_width_source", params.get("layer_width_source", "parent")),
            ("shape_code", params.get("shape_code", "")),
            ("solid_family", params.get("solid_family", kind_text)),
            ("quantity_behavior", params.get("quantity_behavior", "volume")),
        ]
    return sorted(params.items())


def _detail_parameters(table) -> dict[str, object]:
    output: dict[str, object] = {}
    for row in range(table.rowCount()):
        key = _item_text(table, row, 0)
        value = _item_text(table, row, 1)
        if not key or not str(value).strip():
            continue
        output[key] = value
    return output


def _merge_detail_parameters(kind: object, existing: dict[str, object], edited: dict[str, object]) -> dict[str, object]:
    kind_text = str(kind or "").strip().lower().replace("-", "_")
    output = dict(existing or {})
    if kind_text == "ditch":
        for key in DITCH_PARAMETER_KEYS:
            output.pop(key, None)
        shape = str(edited.get("shape", "") or "trapezoid").strip().lower().replace("-", "_")
        output["shape"] = shape if shape in DITCH_SHAPES else "trapezoid"
        for key, _label in DITCH_PARAMETER_FIELDS:
            value = str(edited.get(key, "") or "").strip()
            if key != "shape" and value:
                output[key] = value
        return output
    if kind_text == "side_slope":
        for key in (
            "bench_mode",
            "bench_rows",
            "repeat_first_bench_to_daylight",
            "daylight_mode",
            "daylight_search_step",
            "daylight_max_width",
            "daylight_max_width_delta",
            "daylight_max_triangles",
            "cut_slope",
            "fill_slope",
        ):
            output.pop(key, None)
        mode = str(edited.get("bench_mode", "") or "none").strip().lower().replace("-", "_")
        output["bench_mode"] = mode if mode in ASSEMBLY_BENCH_MODES else "none"
        rows = normalize_bench_rows(edited.get("bench_rows", ""))
        if rows:
            output["bench_rows"] = rows
            output["bench_mode"] = "rows" if output["bench_mode"] == "none" else output["bench_mode"]
        if _truthy(edited.get("repeat_first_bench_to_daylight")):
            output["repeat_first_bench_to_daylight"] = True
        daylight_mode = str(edited.get("daylight_mode", "") or "").strip().lower().replace("-", "_")
        if daylight_mode and daylight_mode in ASSEMBLY_DAYLIGHT_MODES:
            output["daylight_mode"] = daylight_mode
        for key in ("daylight_search_step", "daylight_max_width", "daylight_max_width_delta", "daylight_max_triangles", "cut_slope", "fill_slope"):
            value = str(edited.get(key, "") or "").strip()
            if value:
                output[key] = value
        return output
    for key, value in dict(edited or {}).items():
        key_text = str(key or "").strip()
        if key_text and str(value).strip():
            output[key_text] = value
    return output


def _replace_detail_rows(table, rows: list[tuple[str, object]]) -> None:
    table.setRowCount(0)
    for key, value in rows:
        row = table.rowCount()
        table.insertRow(row)
        key_item = QtWidgets.QTableWidgetItem(str(key))
        key_item.setFlags(key_item.flags() & ~QtCore.Qt.ItemIsEditable)
        table.setItem(row, 0, key_item)
        table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(value or "")))


def _detail_value(table, key: str) -> str:
    for row in range(table.rowCount()):
        if _item_text(table, row, 0) == key:
            return _item_text(table, row, 1)
    return ""


def _set_detail_value(table, key: str, value: object) -> None:
    for row in range(table.rowCount()):
        if _item_text(table, row, 0) == key:
            _set_table_item_text(table, row, 1, value)
            return
    row = table.rowCount()
    table.insertRow(row)
    key_item = QtWidgets.QTableWidgetItem(str(key))
    key_item.setFlags(key_item.flags() & ~QtCore.Qt.ItemIsEditable)
    table.setItem(row, 0, key_item)
    table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(value or "")))


def _compact_bench_rows(rows: list[dict[str, object]]) -> str:
    parts = []
    for row in normalize_bench_rows(rows):
        parts.append(
            ",".join(
                [
                    str(row.get("drop", 0.0)),
                    str(row.get("width", 0.0)),
                    str(row.get("slope", 0.0)),
                    str(row.get("post_slope", 0.0)),
                ]
            )
        )
    return "|".join(parts)


def _ditch_detail_note(parameters: dict[str, object]) -> str:
    shape = str(dict(parameters or {}).get("shape", "") or "trapezoid")
    depth = str(dict(parameters or {}).get("depth", "") or "")
    bottom = str(dict(parameters or {}).get("bottom_width", "") or "")
    parts = [f"{shape} ditch"]
    if bottom:
        parts.append(f"bottom={bottom}")
    if depth:
        parts.append(f"depth={depth}")
    return "; ".join(parts)


def _bench_detail_note(parameters: dict[str, object]) -> str:
    rows = normalize_bench_rows(dict(parameters or {}).get("bench_rows", []))
    if not rows:
        return "side slope"
    repeat = " repeat-to-daylight" if _truthy(dict(parameters or {}).get("repeat_first_bench_to_daylight")) else ""
    return f"side slope bench rows={len(rows)}{repeat}"


def _subassembly_preview_text(
    *,
    subassembly_id: str,
    kind: str,
    side: str,
    width: float,
    slope: float,
    thickness: float,
    material: str,
    parameters: dict[str, object],
) -> str:
    kind_text = str(kind or "").strip().lower().replace("-", "_")
    side_text = str(side or "center").strip().lower().replace("-", "_") or "center"
    params = dict(parameters or {})
    lines = [
        f"subassembly_ref: {subassembly_id}",
        f"kind: {kind_text}, side: {side_text}, width={float(width):.3f}, slope={float(slope):.4f}, thickness={float(thickness):.3f}",
    ]
    if material:
        lines.append(f"material: {material}")
    lines.append("")
    lines.extend(_preview_points(subassembly_id, kind_text, side_text, width, slope, params))
    lines.append("")
    lines.extend(_preview_links(subassembly_id, kind_text, side_text, material, params))
    lines.append("")
    lines.extend(_preview_shapes(subassembly_id, kind_text, side_text, thickness, material, params))
    diagnostics = _preview_diagnostics(subassembly_id, kind_text, width, params)
    if diagnostics:
        lines.append("")
        lines.append("diagnostics:")
        lines.extend(f"- {message}" for message in diagnostics)
    return "\n".join(lines)


def _preview_points(subassembly_id: str, kind: str, side: str, width: float, slope: float, params: dict[str, object]) -> list[str]:
    prefix = _id_tail(subassembly_id)
    if kind == "ditch":
        shape = str(params.get("shape", "") or "trapezoid")
        return [
            "points:",
            f"- point:{prefix}:inner_edge | code=ditch_inner | offset=0.000",
            f"- point:{prefix}:invert | code=ditch_invert | shape={shape}",
            f"- point:{prefix}:outer_edge | code=ditch_outer | offset={float(width):.3f}",
        ]
    if kind == "side_slope":
        rows = normalize_bench_rows(params.get("bench_rows", []))
        output = [
            "points:",
            f"- point:{prefix}:hinge | code=slope_hinge | offset=0.000",
        ]
        for index, row in enumerate(rows, start=1):
            output.append(f"- point:{prefix}:bench_{index} | code=slope_bench | width={float(row.get('width', 0.0) or 0.0):.3f}")
        output.append(f"- point:{prefix}:daylight | code=slope_daylight | offset={float(width):.3f}")
        return output
    if kind in {"lane", "shoulder"}:
        return [
            "points:",
            f"- point:{prefix}:start | code={kind}_start | offset=0.000",
            f"- point:{prefix}:end | code={kind}_end | offset={float(width):.3f} | dz={float(width) * float(slope):.3f}",
        ]
    if kind in {"pavement_layer", "subbase"}:
        return [
            "points:",
            f"- point:{prefix}:top_left | code={kind}_top",
            f"- point:{prefix}:top_right | code={kind}_top",
            f"- point:{prefix}:bottom_right | code={kind}_bottom",
            f"- point:{prefix}:bottom_left | code={kind}_bottom",
        ]
    return [
        "points:",
        f"- point:{prefix}:start | code={kind}_start",
        f"- point:{prefix}:end | code={kind}_end",
    ]


def _preview_links(subassembly_id: str, kind: str, side: str, material: str, params: dict[str, object]) -> list[str]:
    prefix = _id_tail(subassembly_id)
    if kind == "ditch":
        role = "drainage_surface"
        return [
            "links:",
            f"- link:{prefix}:inner_to_invert | code=ditch_side | surface_role={role}",
            f"- link:{prefix}:invert_to_outer | code=ditch_side | surface_role={role}",
        ]
    if kind == "side_slope":
        role = "slope_face"
        return [
            "links:",
            f"- link:{prefix}:slope_face | code=slope_face | surface_role={role}",
        ]
    if kind in {"lane", "shoulder"}:
        role = str(params.get("surface_role", "") or "design")
        return [
            "links:",
            f"- link:{prefix}:top | code={kind}_top | surface_role={role}",
        ]
    if kind in {"pavement_layer", "subbase"}:
        return [
            "links:",
            f"- link:{prefix}:top | code={kind}_top | surface_role=subgrade",
            f"- link:{prefix}:bottom | code={kind}_bottom | surface_role=material_boundary",
        ]
    return [
        "links:",
        f"- link:{prefix}:main | code={kind}_link | surface_role=design",
    ]


def _preview_shapes(
    subassembly_id: str,
    kind: str,
    side: str,
    thickness: float,
    material: str,
    params: dict[str, object],
) -> list[str]:
    prefix = _id_tail(subassembly_id)
    if kind in {"pavement_layer", "subbase", "lane", "shoulder"} and float(thickness or 0.0) > 0.0:
        family = str(params.get("solid_family", "") or kind)
        return [
            "shapes:",
            f"- shape:{prefix}:body | code={kind}_body | solid_family={family} | material={material or '-'}",
        ]
    if kind == "ditch":
        shape = str(params.get("shape", "") or "trapezoid")
        lining = str(params.get("lining_thickness", "") or "")
        if lining:
            return [
                "shapes:",
                f"- shape:{prefix}:lining | code=ditch_lining | shape={shape} | material={material or '-'}",
            ]
    return [
        "shapes:",
        "- none for this first-slice source preview",
    ]


def _preview_diagnostics(subassembly_id: str, kind: str, width: float, params: dict[str, object]) -> list[str]:
    messages: list[str] = []
    if float(width or 0.0) < 0.0:
        messages.append(f"{subassembly_id}: width must not be negative.")
    if kind == "ditch":
        shape = str(params.get("shape", "") or "trapezoid").strip().lower().replace("-", "_")
        if shape not in DITCH_SHAPES:
            messages.append(f"{subassembly_id}: unknown ditch shape {shape}.")
        if not str(params.get("depth", "") or "").strip():
            messages.append(f"{subassembly_id}: ditch depth is not defined.")
    if kind == "side_slope":
        rows = normalize_bench_rows(params.get("bench_rows", []))
        if str(params.get("bench_mode", "") or "").strip().lower() == "rows" and not rows:
            messages.append(f"{subassembly_id}: bench_mode is rows but no valid bench_rows exist.")
    return messages


def _id_tail(value: object) -> str:
    text = str(value or "").strip()
    if ":" in text:
        return text.split(":")[-1]
    return text or "subassembly"


def _format_float(value: object) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "0.000"


def _float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditAssemblySubassembly", CmdV1AssemblySubassemblyEditor())
