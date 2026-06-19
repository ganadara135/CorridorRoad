"""Assembly/Subassembly editor command for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets

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
from ..models.source.subassembly_preset_model import SUBASSEMBLY_PRESET_STATUSES
from ..services.evaluation.subassembly_bench_row_parser import bench_rows_to_dicts, parse_bench_rows
from ..objects.obj_alignment import find_v1_alignment
from ..objects.obj_subassembly_assembly import (
    create_or_update_v1_assembly_subassembly_model_object,
    find_v1_assembly_subassembly_model,
    to_assembly_subassembly_model,
)
from ..objects.obj_subassembly_library import find_v1_subassembly_library, to_subassembly_library
from ..objects.obj_subassembly_preset_library import find_v1_subassembly_preset_library, to_subassembly_preset_library
from .assembly_preset_data import (
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
    "Subassembly Ref",
    "Template Ref",
    "Template Version",
    "Template Status",
    "Side",
    "Index",
    "Target Ref",
    "Notes",
    "Kind",
    "Width",
    "Slope",
    "Thickness",
    "Material",
    "Overrides",
    "Parameters",
    "Source Instance Ref",
)

COL_ENABLED = 0
COL_ID = 1
COL_DEFINITION_REF = 2
COL_PRESET_REF = 3
COL_PRESET_VERSION = 4
COL_PRESET_STATUS = 5
COL_SIDE = 6
COL_INDEX = 7
COL_TARGET_REF = 8
COL_NOTES = 9
COL_KIND = 10
COL_WIDTH = 11
COL_SLOPE = 12
COL_THICKNESS = 13
COL_MATERIAL = 14
COL_OVERRIDES = 15
COL_PARAMETERS = 16
COL_SOURCE_INSTANCE_REF = 17

HIDDEN_SOURCE_COLUMNS = (
    COL_PRESET_REF,
    COL_PRESET_VERSION,
    COL_PRESET_STATUS,
    COL_KIND,
    COL_WIDTH,
    COL_SLOPE,
    COL_THICKNESS,
    COL_MATERIAL,
    COL_OVERRIDES,
    COL_PARAMETERS,
    COL_SOURCE_INSTANCE_REF,
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


def create_or_update_assembly_subassembly_section_preview(
    *,
    document=None,
    assembly_model: AssemblySubassemblyModel,
    definition_library=None,
    object_name: str = "V1AssemblySubassemblySectionPreview",
):
    """Create a lightweight 3D View cross-section preview from Assembly/Subassembly source rows."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    try:
        import Part  # type: ignore
    except Exception as exc:
        raise RuntimeError("FreeCAD Part workbench is required for Assembly/Subassembly section preview.") from exc
    template = _active_template(assembly_model)
    rows = [row for row in list(getattr(template, "subassembly_rows", []) or []) if bool(getattr(row, "enabled", True))]
    wires = _assembly_section_preview_wires(rows, definition_library=definition_library, part_module=Part)
    if not wires:
        raise RuntimeError("No enabled Assembly/Subassembly rows are available for preview.")
    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("Part::Feature", object_name)
    obj.Shape = Part.Compound(wires) if len(wires) > 1 else wires[0]
    obj.Label = "Assembly / Subassembly Section Preview"
    _set_preview_property(obj, "CRRecordKind", "v1_assembly_subassembly_section_preview")
    _set_preview_property(obj, "V1ObjectType", "V1AssemblySubassemblySectionPreview")
    _set_preview_property(obj, "AssemblyId", str(getattr(assembly_model, "assembly_id", "") or ""))
    _set_preview_property(obj, "TemplateId", str(getattr(template, "template_id", "") or "") if template is not None else "")
    _set_preview_integer_property(obj, "SubassemblyCount", len(rows))
    _style_assembly_section_preview_object(obj)
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


class _AssemblyTableComboBox(QtWidgets.QComboBox):
    """Combo box that does not move the Assembly table selection on hover."""

    def __init__(self, table=None, row: int | None = None):
        super().__init__()
        self._table = table
        self._row = row
        try:
            self.setFocusPolicy(QtCore.Qt.ClickFocus)
            self.setMouseTracking(False)
            self.setAttribute(QtCore.Qt.WA_Hover, False)
            self.view().setMouseTracking(False)
            self.view().setAttribute(QtCore.Qt.WA_Hover, False)
        except Exception:
            pass

    def event(self, event):  # noqa: D401 - Qt event API
        """Ignore hover-only events inside QTableWidget cell widgets."""

        try:
            event_type = event.type()
            hover_types = {
                QtCore.QEvent.Enter,
                QtCore.QEvent.MouseMove,
                QtCore.QEvent.HoverEnter,
                QtCore.QEvent.HoverMove,
                QtCore.QEvent.HoverLeave,
            }
            if event_type in hover_types:
                self._restore_table_selection()
                return True
        except Exception:
            pass
        return super().event(event)

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt API name
        self._restore_table_selection()
        try:
            event.accept()
        except Exception:
            pass

    def mousePressEvent(self, event):  # noqa: N802 - Qt API name
        self._allow_table_selection_change()
        try:
            super().mousePressEvent(event)
        except Exception:
            pass

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt API name
        self._restore_table_selection()
        try:
            super().mouseReleaseEvent(event)
        except Exception:
            pass

    def showPopup(self):  # noqa: N802 - Qt API name
        self._allow_table_selection_change()
        return super().showPopup()

    def enterEvent(self, event):  # noqa: N802 - Qt API name
        self._restore_table_selection()
        try:
            event.accept()
        except Exception:
            pass

    def leaveEvent(self, event):  # noqa: N802 - Qt API name
        self._restore_table_selection()
        try:
            event.accept()
        except Exception:
            pass

    def _restore_table_selection(self) -> None:
        table = self._table
        if table is None:
            return
        try:
            locked = table.property("lockedAssemblyRow")
            locked_row = int(locked) if locked is not None else -1
        except Exception:
            locked_row = -1
        if locked_row < 0:
            try:
                selected_rows = [index.row() for index in table.selectionModel().selectedRows()]
                locked_row = int(selected_rows[0]) if selected_rows else -1
            except Exception:
                locked_row = -1
        if locked_row < 0:
            return
        try:
            selected_rows = {index.row() for index in table.selectionModel().selectedRows()}
            current_row = int(table.currentRow())
            if selected_rows == {locked_row} and current_row == locked_row:
                return
            previous_state = bool(table.blockSignals(True))
            try:
                table.clearSelection()
                table.selectRow(locked_row)
                table.setCurrentCell(locked_row, 0)
            finally:
                table.blockSignals(previous_state)
            table.setProperty("lockedAssemblyRow", locked_row)
            table.setProperty("allowAssemblySelectionChange", False)
        except Exception:
            pass

    def _allow_table_selection_change(self) -> None:
        table = self._table
        row = self._row
        if table is None or row is None:
            return
        try:
            table.setProperty("allowAssemblySelectionChange", True)
            table.setProperty("lockedAssemblyRow", int(row))
            table.selectRow(int(row))
            table.setCurrentCell(int(row), 0)
        except Exception:
            pass


class V1AssemblySubassemblyEditorTaskPanel:
    """Table-based v1 Assembly/Subassembly source editor."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self._locked_assembly_row_index: int | None = None
        self._allow_assembly_selection_change = False
        self._loading = False
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
        preset_row.addWidget(QtWidgets.QLabel("Assembly Template:"))
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItems(assembly_preset_names())
        preset_row.addWidget(self.preset_combo, 1)
        self.load_preset_button = QtWidgets.QPushButton("Load Assembly Template")
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

        guess_ref_row = QtWidgets.QHBoxLayout()
        self.guess_subassembly_refs_button = QtWidgets.QPushButton("Guess Missing Subassembly Refs")
        self.guess_subassembly_refs_button.setToolTip(
            "Fill empty Subassembly Ref cells by guessing from each Subassembly ID. Existing refs are not overwritten."
        )
        self.guess_subassembly_refs_button.clicked.connect(lambda _checked=False: _guess_missing_subassembly_refs_for_panel(self))
        guess_ref_row.addWidget(self.guess_subassembly_refs_button)
        self.guess_subassembly_refs_note = QtWidgets.QLabel(
            "Subassembly Ref guesses are based on Subassembly ID text and may be inaccurate. Review the assigned refs before Apply."
        )
        self.guess_subassembly_refs_note.setWordWrap(True)
        self.guess_subassembly_refs_note.setStyleSheet(
            "QLabel {"
            "background: #302b1c;"
            "color: #f2d38a;"
            "border: 1px solid #7f6427;"
            "border-left: 4px solid #d9a441;"
            "border-radius: 4px;"
            "padding: 4px 6px;"
            "}"
        )
        guess_ref_row.addWidget(self.guess_subassembly_refs_note, 1)
        layout.addLayout(guess_ref_row)

        self.table = QtWidgets.QTableWidget(0, len(SUBASSEMBLY_COLUMNS))
        self.table.setHorizontalHeaderLabels(SUBASSEMBLY_COLUMNS)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        try:
            self.table.setMouseTracking(False)
            self.table.viewport().setMouseTracking(False)
            self.table.viewport().setAttribute(QtCore.Qt.WA_Hover, False)
        except Exception:
            pass
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellPressed.connect(self._assembly_row_pressed)
        self.table.cellClicked.connect(self._assembly_row_clicked)
        self.table.currentCellChanged.connect(self._assembly_current_cell_changed)
        for column in HIDDEN_SOURCE_COLUMNS:
            self.table.setColumnHidden(column, True)
        layout.addWidget(self.table, 1)
        self.preset_status_legend = QtWidgets.QLabel(_preset_status_legend_text())
        self.preset_status_legend.setWordWrap(True)
        self.preset_status_legend.setToolTip(
            "Template status colors are visual review aids only; Apply writes the Assembly source object."
        )
        self.preset_status_legend.setStyleSheet(
            "QLabel {"
            "background: #202936;"
            "color: #d8e0ea;"
            "border: 1px solid #435066;"
            "border-left: 4px solid #6f7f95;"
            "border-radius: 4px;"
            "padding: 4px 6px;"
            "}"
        )
        layout.addWidget(self.preset_status_legend)

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
        self.load_detail_defaults_button.setToolTip("Load kind-specific detail defaults into the selected row editor.")
        self.load_detail_defaults_button.clicked.connect(self._load_selected_detail_defaults)
        detail_button_row.addWidget(self.load_detail_defaults_button)
        self.refresh_from_preset_button = QtWidgets.QPushButton("Refresh from Template")
        self.refresh_from_preset_button.setToolTip("Replace the selected linked row with current reusable Subassembly template defaults and clear local overrides.")
        self.refresh_from_preset_button.clicked.connect(self._refresh_selected_from_preset)
        detail_button_row.addWidget(self.refresh_from_preset_button)
        self.detach_as_custom_button = QtWidgets.QPushButton("Detach as Custom")
        self.detach_as_custom_button.setToolTip("Convert the selected template-linked row into a local snapshot that no longer follows template updates.")
        self.detach_as_custom_button.clicked.connect(self._detach_selected_as_custom)
        detail_button_row.addWidget(self.detach_as_custom_button)
        self.add_bench_row_button = QtWidgets.QPushButton("Add Bench Row")
        self.add_bench_row_button.setToolTip("Append a side-slope bench row to the selected detail parameters.")
        self.add_bench_row_button.clicked.connect(self._add_detail_bench_row)
        detail_button_row.addWidget(self.add_bench_row_button)
        self.reset_overrides_button = QtWidgets.QPushButton("Reset Overrides")
        self.reset_overrides_button.setToolTip("Clear local overrides on the selected row and return it to linked template defaults where possible.")
        self.reset_overrides_button.clicked.connect(self._reset_selected_overrides)
        detail_button_row.addWidget(self.reset_overrides_button)
        self.apply_detail_button = QtWidgets.QPushButton("Apply Detail")
        self.apply_detail_button.setToolTip("Apply detail-table edits to the selected Assembly row without writing the FreeCAD source object yet.")
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
        self.refresh_outdated_presets_button = QtWidgets.QPushButton("Refresh Outdated Templates")
        self.refresh_outdated_presets_button.setToolTip(
            "Refresh rows whose reusable Subassembly template version is outdated; modified, missing, and snapshot rows are skipped."
        )
        self.refresh_outdated_presets_button.clicked.connect(self._refresh_outdated_presets)
        button_row.addWidget(self.refresh_outdated_presets_button)
        self.apply_button = QtWidgets.QPushButton("Apply")
        self.apply_button.setToolTip("Validate and write the Assembly/Subassembly source object.")
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

        preview_button_row = QtWidgets.QHBoxLayout()
        preview_button_row.addStretch(1)
        self.show_section_preview_button = QtWidgets.QPushButton("Show Section Preview")
        self.show_section_preview_button.setToolTip("Refresh the in-panel preview of the current Assembly/Subassembly cross-section source.")
        self.show_section_preview_button.clicked.connect(self._show_section_preview)
        preview_button_row.addWidget(self.show_section_preview_button)
        layout.addLayout(preview_button_row)

        self.section_preview_group = QtWidgets.QGroupBox("Section Preview")
        section_preview_layout = QtWidgets.QVBoxLayout(self.section_preview_group)
        self.section_preview_scene = QtWidgets.QGraphicsScene()
        self.section_preview_view = _AssemblySectionPreviewView(self.section_preview_scene)
        try:
            self.section_preview_view.setRenderHint(QtGui.QPainter.Antialiasing, True)
        except Exception:
            pass
        self.section_preview_view.setMinimumHeight(240)
        section_preview_layout.addWidget(self.section_preview_view, 1)
        self.section_preview_status = QtWidgets.QLabel("Click Show Section Preview to review the current Assembly/Subassembly section.")
        self.section_preview_status.setWordWrap(True)
        section_preview_layout.addWidget(self.section_preview_status)
        layout.addWidget(self.section_preview_group)
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
        self._refresh_preset_status_indicators()
        if rows:
            self.table.selectRow(0)
            self._lock_assembly_selection(0)
        else:
            self._lock_assembly_selection(None)
        self._refresh_selected_detail()
        self.summary.setPlainText(f"Loaded {len(rows)} subassembly rows. Apply writes a V1AssemblySubassemblyModel source object.")

    def _load_selected_preset(self) -> None:
        try:
            model = assembly_subassembly_preset_model_from_document(self.preset_combo.currentText(), document=self.document)
            self._load_model(model)
        except Exception as exc:
            _show_message(self.form, "Assembly / Subassembly", f"Assembly Template load failed: {exc}")

    def _append_subassembly(self, subassembly: TemplateSubassembly) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._set_combo(row, COL_ENABLED, ("Yes", "No"), "Yes" if subassembly.enabled else "No")
        self.table.setItem(row, COL_ID, QtWidgets.QTableWidgetItem(str(subassembly.subassembly_id)))
        self._set_definition_combo(row, COL_DEFINITION_REF, subassembly.definition_ref)
        self._set_preset_combo(row, COL_PRESET_REF, getattr(subassembly, "preset_ref", ""))
        self.table.setItem(row, COL_PRESET_VERSION, QtWidgets.QTableWidgetItem(str(getattr(subassembly, "preset_version", "") or "")))
        self._set_combo(
            row,
            COL_PRESET_STATUS,
            ("",) + tuple(SUBASSEMBLY_PRESET_STATUSES),
            _preset_status_display(subassembly),
        )
        self._set_combo(row, COL_SIDE, ASSEMBLY_SUBASSEMBLY_SIDES, subassembly.side)
        self.table.setItem(row, COL_INDEX, QtWidgets.QTableWidgetItem(str(int(subassembly.subassembly_index or row + 1))))
        self.table.setItem(row, COL_TARGET_REF, QtWidgets.QTableWidgetItem(str(subassembly.target_ref)))
        self.table.setItem(row, COL_NOTES, QtWidgets.QTableWidgetItem(str(subassembly.notes)))
        self.table.setItem(row, COL_KIND, QtWidgets.QTableWidgetItem(str(subassembly.kind)))
        self.table.setItem(row, COL_WIDTH, QtWidgets.QTableWidgetItem(_format_float(subassembly.width)))
        self.table.setItem(row, COL_SLOPE, QtWidgets.QTableWidgetItem(_format_float(subassembly.slope)))
        self.table.setItem(row, COL_THICKNESS, QtWidgets.QTableWidgetItem(_format_float(subassembly.thickness)))
        self.table.setItem(row, COL_MATERIAL, QtWidgets.QTableWidgetItem(str(subassembly.material)))
        self.table.setItem(row, COL_OVERRIDES, QtWidgets.QTableWidgetItem(serialize_subassembly_parameters(subassembly.parameter_overrides)))
        self.table.setItem(row, COL_PARAMETERS, QtWidgets.QTableWidgetItem(serialize_subassembly_parameters(subassembly.parameters)))
        self.table.setItem(row, COL_SOURCE_INSTANCE_REF, QtWidgets.QTableWidgetItem(str(getattr(subassembly, "source_instance_ref", "") or "")))
        self._style_subassembly_row(row)
        if self.table.rowCount() == 1:
            self.table.selectRow(0)

    def _set_combo(self, row: int, column: int, values: tuple[str, ...], current: str) -> None:
        combo = _AssemblyTableComboBox(self.table, row)
        combo.addItems(list(values))
        index = combo.findText(str(current or ""))
        if index >= 0:
            combo.setCurrentIndex(index)
        combo.currentTextChanged.connect(lambda _value, table_row=row: self._preset_ref_changed(table_row))
        self.table.setCellWidget(row, column, combo)

    def _preset_ref_changed(self, row: int) -> None:
        if row < 0 or row >= self.table.rowCount():
            return
        preset_ref = _item_text(self.table, row, COL_PRESET_REF)
        if not preset_ref:
            _set_table_item_text(self.table, row, COL_PRESET_VERSION, "")
            _set_combo_text(self.table, row, COL_PRESET_STATUS, "snapshot")
            self._style_subassembly_row(row)
            return
        preset = _subassembly_preset_for_ref(self.document, preset_ref)
        if preset is None:
            versions = _subassembly_preset_version_map(self.document)
            _set_table_item_text(self.table, row, COL_PRESET_VERSION, versions.get(preset_ref, ""))
            _set_combo_text(self.table, row, COL_PRESET_STATUS, "missing_preset")
            self._style_subassembly_row(row)
            self._refresh_selected_detail()
            return
        _apply_preset_defaults_to_row(self.table, row, preset, clear_overrides=False)
        self._style_subassembly_row(row)
        self._refresh_selected_detail()

    def _assembly_row_pressed(self, row: int, _column: int) -> None:
        self._allow_assembly_selection_change = True
        self._locked_assembly_row_index = int(row)
        try:
            self.table.setProperty("lockedAssemblyRow", int(row))
            self.table.setProperty("allowAssemblySelectionChange", True)
        except Exception:
            pass

    def _assembly_row_clicked(self, row: int, _column: int) -> None:
        if self._loading or row is None or row < 0:
            return
        self._lock_assembly_selection(int(row))
        self._refresh_selected_detail()

    def _assembly_current_cell_changed(self, row: int, _column: int, _previous_row: int, _previous_column: int) -> None:
        if self._loading:
            return
        if row is None or row < 0:
            return
        locked_index = self._locked_assembly_row_index
        if locked_index is None:
            self._lock_assembly_selection(int(row))
            return
        allow_change = bool(self._allow_assembly_selection_change)
        self._allow_assembly_selection_change = False
        if int(row) != int(locked_index) and not allow_change:
            self._restore_assembly_selection(locked_index)
        else:
            self._lock_assembly_selection(int(row))

    def _lock_assembly_selection(self, row: int | None) -> None:
        self._locked_assembly_row_index = None if row is None else int(row)
        try:
            self.table.setProperty("lockedAssemblyRow", -1 if row is None else int(row))
            self.table.setProperty("allowAssemblySelectionChange", False)
        except Exception:
            pass

    def _restore_assembly_selection(self, row: int | None) -> None:
        if row is None or not (0 <= int(row) < self.table.rowCount()):
            return
        was_loading = self._loading
        self._loading = True
        try:
            previous_state = bool(self.table.blockSignals(True))
            try:
                self.table.clearSelection()
                self.table.selectRow(int(row))
                self.table.setCurrentCell(int(row), 0)
            finally:
                self.table.blockSignals(previous_state)
        finally:
            self._loading = was_loading
        self._lock_assembly_selection(int(row))

    def _style_subassembly_row(self, row: int) -> None:
        if row < 0 or row >= self.table.rowCount():
            return
        status = _item_text(self.table, row, COL_PRESET_STATUS)
        preset_ref = _item_text(self.table, row, COL_PRESET_REF)
        if not status:
            status = "linked" if preset_ref else "snapshot"
        colors = {
            "linked": (31, 54, 40),
            "modified": (62, 51, 28),
            "snapshot": (37, 44, 56),
            "missing_preset": (62, 36, 40),
            "preset_outdated": (65, 47, 30),
            "outdated": (65, 47, 30),
        }
        rgb = colors.get(status, (37, 44, 56))
        try:
            background_color = QtGui.QColor(*rgb)
            foreground_color = QtGui.QColor(232, 238, 246)
            background = QtGui.QBrush(background_color)
            foreground = QtGui.QBrush(foreground_color)
            selected_background = QtGui.QBrush(QtGui.QColor(74, 160, 236))
            selected_foreground = QtGui.QBrush(QtGui.QColor(255, 255, 255))
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item is not None:
                    item.setBackground(background)
                    item.setForeground(foreground)
                    item.setData(QtCore.Qt.BackgroundRole, background)
                    item.setData(QtCore.Qt.ForegroundRole, foreground)
                    item.setData(QtCore.Qt.UserRole + 51, selected_background)
                    item.setData(QtCore.Qt.UserRole + 52, selected_foreground)
                widget = self.table.cellWidget(row, column)
                if widget is not None:
                    widget.setStyleSheet(
                        "QComboBox {"
                        f"background-color: rgb({rgb[0]}, {rgb[1]}, {rgb[2]});"
                        "color: rgb(232, 238, 246);"
                        "selection-background-color: rgb(74, 160, 236);"
                        "selection-color: rgb(255, 255, 255);"
                        "border: 1px solid rgb(67, 80, 102);"
                        "}"
                        "QComboBox QAbstractItemView {"
                        "background-color: rgb(31, 38, 50);"
                        "color: rgb(232, 238, 246);"
                        "selection-background-color: rgb(74, 160, 236);"
                        "selection-color: rgb(255, 255, 255);"
                        "}"
                    )
        except Exception:
            return

    def _refresh_preset_status_indicators(self) -> None:
        versions = _subassembly_preset_version_map(self.document)
        for row in range(self.table.rowCount()):
            preset_ref = _item_text(self.table, row, COL_PRESET_REF)
            status = _item_text(self.table, row, COL_PRESET_STATUS)
            if not preset_ref:
                if not status:
                    _set_combo_text(self.table, row, COL_PRESET_STATUS, "snapshot")
                self._style_subassembly_row(row)
                continue
            library_version = str(versions.get(preset_ref, "") or "")
            row_version = _item_text(self.table, row, COL_PRESET_VERSION)
            if not library_version:
                _set_combo_text(self.table, row, COL_PRESET_STATUS, "missing_preset")
            elif status != "modified" and row_version and row_version != library_version:
                _set_combo_text(self.table, row, COL_PRESET_STATUS, "preset_outdated")
            elif status in {"", "missing_preset", "preset_outdated", "outdated"}:
                _set_combo_text(self.table, row, COL_PRESET_STATUS, "linked")
            self._style_subassembly_row(row)

    def _set_definition_combo(self, row: int, column: int, current: str) -> None:
        combo = _AssemblyTableComboBox(self.table, row)
        combo.addItems(_subassembly_definition_ref_values(self.document))
        index = combo.findText(str(current or ""))
        if index >= 0:
            combo.setCurrentIndex(index)
        self.table.setCellWidget(row, column, combo)

    def _set_preset_combo(self, row: int, column: int, current: str) -> None:
        combo = _AssemblyTableComboBox(self.table, row)
        combo.addItems(_subassembly_preset_ref_values(self.document))
        current_text = str(current or "").strip()
        index = combo.findText(current_text)
        if index < 0 and current_text:
            combo.addItem(current_text)
            index = combo.findText(current_text)
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
            self.refresh_from_preset_button.setEnabled(False)
            self.detach_as_custom_button.setEnabled(False)
            self.add_bench_row_button.setEnabled(False)
            self.reset_overrides_button.setEnabled(False)
            self.apply_detail_button.setEnabled(False)
            return
        subassembly_id = _item_text(self.table, row, COL_ID)
        definition_ref = _item_text(self.table, row, COL_DEFINITION_REF)
        preset_ref = _item_text(self.table, row, COL_PRESET_REF)
        preset_status = _item_text(self.table, row, COL_PRESET_STATUS) or ("linked" if preset_ref else "snapshot")
        definition = _subassembly_definition_for_ref(self.document, definition_ref)
        kind = _item_text(self.table, row, COL_KIND)
        side = _item_text(self.table, row, COL_SIDE)
        params = parse_subassembly_parameters(_item_text(self.table, row, COL_PARAMETERS))
        overrides = parse_subassembly_parameters(_item_text(self.table, row, COL_OVERRIDES))
        self.detail_summary.setText(
            f"{subassembly_id} | {kind} | {side} | index={_item_text(self.table, row, COL_INDEX) or row + 1} | "
            f"subassembly_ref={definition_ref or '-'}\n"
            "Assembly places Subassemblies. Edit values here only when this placement needs parameter overrides."
        )
        rows = _definition_override_rows(definition, overrides) if definition is not None else _detail_parameter_rows(kind, params)
        self.detail_table.setRowCount(0)
        for key, value in rows:
            detail_row = self.detail_table.rowCount()
            self.detail_table.insertRow(detail_row)
            key_item = QtWidgets.QTableWidgetItem(str(key))
            key_item.setFlags(key_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.detail_table.setItem(detail_row, 0, key_item)
            self.detail_table.setItem(detail_row, 1, QtWidgets.QTableWidgetItem(str(value)))
        self.detail_preview.setPlainText(
            _definition_preview_text(definition, overrides)
            if definition is not None
            else _subassembly_preview_text(
                subassembly_id=subassembly_id,
                kind=kind,
                side=side,
                width=_float(_item_text(self.table, row, COL_WIDTH)),
                slope=_float(_item_text(self.table, row, COL_SLOPE)),
                thickness=_float(_item_text(self.table, row, COL_THICKNESS)),
                material=_item_text(self.table, row, COL_MATERIAL),
                parameters=params,
            )
        )
        self.load_detail_defaults_button.setEnabled(definition is None and kind == "ditch")
        self.refresh_from_preset_button.setEnabled(bool(preset_ref))
        self.detach_as_custom_button.setEnabled(bool(preset_ref))
        self.add_bench_row_button.setEnabled(definition is None and kind == "side_slope")
        self.reset_overrides_button.setEnabled(definition is not None and bool(overrides))
        self.apply_detail_button.setEnabled(
            definition is not None or kind in {"ditch", "side_slope", "lane", "shoulder", "pavement_layer", "subbase"}
        )

    def _load_selected_detail_defaults(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount() or _item_text(self.table, row, COL_KIND) != "ditch":
            return
        shape = _detail_value(self.detail_table, "shape") or "trapezoid"
        defaults = dict(DITCH_SHAPE_DEFAULTS.get(shape, DITCH_SHAPE_DEFAULTS["trapezoid"]))
        defaults["shape"] = shape if shape in DITCH_SHAPES else "trapezoid"
        _replace_detail_rows(self.detail_table, _detail_parameter_rows("ditch", defaults))

    def _refresh_selected_from_preset(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount():
            return
        preset_ref = _item_text(self.table, row, COL_PRESET_REF)
        if not preset_ref:
            self.summary.setPlainText("Select a Subassembly row with a template ref before refreshing.")
            return
        preset = _subassembly_preset_for_ref(self.document, preset_ref)
        if preset is None:
            _set_combo_text(self.table, row, COL_PRESET_STATUS, "missing_preset")
            self._style_subassembly_row(row)
            self.summary.setPlainText(f"Reusable Subassembly Template was not found: {preset_ref}")
            self._refresh_selected_detail()
            return
        _apply_preset_defaults_to_row(self.table, row, preset, clear_overrides=True)
        self._style_subassembly_row(row)
        self._refresh_selected_detail()
        self.summary.setPlainText(f"Refreshed {_item_text(self.table, row, COL_ID)} from template {preset_ref}.")

    def _detach_selected_as_custom(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount():
            return
        subassembly_id = _item_text(self.table, row, COL_ID)
        preset_ref = _item_text(self.table, row, COL_PRESET_REF)
        if not preset_ref:
            self.summary.setPlainText(f"{subassembly_id} is already a custom snapshot.")
            return
        current_parameters = parse_subassembly_parameters(_item_text(self.table, row, COL_PARAMETERS))
        current_overrides = parse_subassembly_parameters(_item_text(self.table, row, COL_OVERRIDES))
        snapshot_parameters = dict(current_parameters)
        snapshot_parameters.update(current_overrides)
        _set_table_item_text(self.table, row, COL_PARAMETERS, serialize_subassembly_parameters(snapshot_parameters))
        _set_table_item_text(self.table, row, COL_OVERRIDES, "")
        _set_combo_text(self.table, row, COL_PRESET_REF, "")
        _set_table_item_text(self.table, row, COL_PRESET_VERSION, "")
        _set_combo_text(self.table, row, COL_PRESET_STATUS, "snapshot")
        if not _item_text(self.table, row, COL_SOURCE_INSTANCE_REF):
            _set_table_item_text(self.table, row, COL_SOURCE_INSTANCE_REF, subassembly_id)
        self._style_subassembly_row(row)
        self._refresh_selected_detail()
        self.summary.setPlainText(f"Detached {subassembly_id} from template {preset_ref}; row is now a custom snapshot.")

    def _add_detail_bench_row(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount() or _item_text(self.table, row, COL_KIND) != "side_slope":
            return
        bench_rows = normalize_bench_rows(_detail_value(self.detail_table, "bench_rows"))
        bench_rows.append({"drop": 3.0, "width": 1.5, "slope": -0.02, "post_slope": _float(_item_text(self.table, row, COL_SLOPE), -0.5)})
        _set_detail_value(self.detail_table, "bench_mode", "rows")
        _set_detail_value(self.detail_table, "bench_rows", _compact_bench_rows(bench_rows))

    def _apply_selected_detail(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount():
            return
        kind = _item_text(self.table, row, COL_KIND)
        definition_ref = _item_text(self.table, row, COL_DEFINITION_REF)
        edited = _detail_parameters(self.detail_table)
        if definition_ref:
            definition = _subassembly_definition_for_ref(self.document, definition_ref)
            defaults = _definition_parameter_defaults(definition)
            overrides = {
                key: value
                for key, value in edited.items()
                if _override_value_changed(key, value, defaults.get(key, ""))
            }
            _set_table_item_text(self.table, row, COL_OVERRIDES, serialize_subassembly_parameters(overrides))
            if _item_text(self.table, row, COL_PRESET_REF):
                _set_combo_text(self.table, row, COL_PRESET_STATUS, "modified" if overrides else "linked")
                self._style_subassembly_row(row)
        else:
            existing = parse_subassembly_parameters(_item_text(self.table, row, COL_PARAMETERS))
            params = _merge_detail_parameters(kind, existing, edited)
            _set_table_item_text(self.table, row, COL_PARAMETERS, serialize_subassembly_parameters(params))
            if kind == "ditch":
                _set_table_item_text(self.table, row, COL_NOTES, _ditch_detail_note(params))
            elif kind == "side_slope":
                _set_table_item_text(self.table, row, COL_NOTES, _bench_detail_note(params))
        self._refresh_selected_detail()
        self.summary.setPlainText(f"Detail applied to {_item_text(self.table, row, COL_ID)}.")

    def _reset_selected_overrides(self) -> None:
        row = self._selected_row()
        if row < 0 or row >= self.table.rowCount():
            return
        _set_table_item_text(self.table, row, COL_OVERRIDES, "")
        if _item_text(self.table, row, COL_PRESET_REF):
            _set_combo_text(self.table, row, COL_PRESET_STATUS, "linked")
            self._style_subassembly_row(row)
        self._refresh_selected_detail()
        self.summary.setPlainText(f"Overrides reset for {_item_text(self.table, row, COL_ID)}.")

    def _refresh_outdated_presets(self) -> None:
        preset_versions = _subassembly_preset_version_map(self.document)
        refreshed: list[str] = []
        skipped: list[str] = []
        for row in range(self.table.rowCount()):
            subassembly_id = _item_text(self.table, row, COL_ID) or f"row:{row + 1}"
            preset_ref = _item_text(self.table, row, COL_PRESET_REF)
            if not preset_ref:
                continue
            preset = _subassembly_preset_for_ref(self.document, preset_ref)
            if preset is None:
                _set_combo_text(self.table, row, COL_PRESET_STATUS, "missing_preset")
                self._style_subassembly_row(row)
                skipped.append(f"{subassembly_id}:missing")
                continue
            status = _item_text(self.table, row, COL_PRESET_STATUS)
            row_version = _item_text(self.table, row, COL_PRESET_VERSION)
            library_version = str(preset_versions.get(preset_ref, "") or "")
            if status == "modified":
                skipped.append(f"{subassembly_id}:modified")
                continue
            if row_version == library_version and status not in {"preset_outdated", "outdated"}:
                continue
            _apply_preset_defaults_to_row(self.table, row, preset, clear_overrides=True)
            self._style_subassembly_row(row)
            refreshed.append(subassembly_id)
        self._refresh_selected_detail()
        parts = [f"Refreshed outdated template rows: {len(refreshed)}"]
        if refreshed:
            parts.append("rows=" + ", ".join(refreshed[:5]) + (f", +{len(refreshed) - 5} more" if len(refreshed) > 5 else ""))
        if skipped:
            parts.append("skipped=" + ", ".join(skipped[:5]) + (f", +{len(skipped) - 5} more" if len(skipped) > 5 else ""))
        self.summary.setPlainText("\n".join(parts))

    def _guess_missing_subassembly_refs(self) -> None:
        _guess_missing_subassembly_refs_for_panel(self)

    def _build_model_from_ui(self) -> AssemblySubassemblyModel:
        template_id = str(self.template_id_edit.text() or "template:subassembly").strip()
        subassemblies: list[TemplateSubassembly] = []
        for row in range(self.table.rowCount()):
            subassemblies.append(
                TemplateSubassembly(
                    subassembly_id=_item_text(self.table, row, COL_ID) or f"subassembly:{row + 1}",
                    definition_ref=_item_text(self.table, row, COL_DEFINITION_REF),
                    preset_ref=_item_text(self.table, row, COL_PRESET_REF),
                    preset_version=_item_text(self.table, row, COL_PRESET_VERSION),
                    preset_status=_item_text(self.table, row, COL_PRESET_STATUS),
                    source_instance_ref=_item_text(self.table, row, COL_SOURCE_INSTANCE_REF),
                    kind=_item_text(self.table, row, COL_KIND) or "lane",
                    subassembly_index=int(_float(_item_text(self.table, row, COL_INDEX), row + 1)),
                    side=_item_text(self.table, row, COL_SIDE) or "center",
                    width=_float(_item_text(self.table, row, COL_WIDTH)),
                    slope=_float(_item_text(self.table, row, COL_SLOPE)),
                    thickness=_float(_item_text(self.table, row, COL_THICKNESS)),
                    material=_item_text(self.table, row, COL_MATERIAL),
                    target_ref=_item_text(self.table, row, COL_TARGET_REF),
                    parameter_overrides=parse_subassembly_parameters(_item_text(self.table, row, COL_OVERRIDES)),
                    parameters=parse_subassembly_parameters(_item_text(self.table, row, COL_PARAMETERS)),
                    notes=_item_text(self.table, row, COL_NOTES),
                    enabled=_truthy(_item_text(self.table, row, COL_ENABLED)),
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
        messages = _validate_subassembly_model(
            model,
            available_definition_ids=_subassembly_definition_ref_set(self.document),
            available_preset_ids=_subassembly_preset_ref_set(self.document),
            preset_versions=_subassembly_preset_version_map(self.document),
        )
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

    def _show_section_preview(self) -> None:
        try:
            self._draw_section_preview(
                self._build_model_from_ui(),
                definition_library=_subassembly_library_model(self.document),
            )
        except Exception as exc:
            self.summary.setPlainText(f"Section preview failed: {exc}")
            _show_message(self.form, "Assembly / Subassembly", f"Section preview failed:\n{exc}")
            return
        self.summary.setPlainText("Section preview updated in the panel.")

    def _draw_section_preview(self, assembly_model: AssemblySubassemblyModel, *, definition_library=None) -> None:
        scene = self.section_preview_scene
        scene.clear()
        template = _active_template(assembly_model)
        rows = [
            row
            for row in list(getattr(template, "subassembly_rows", []) or [])
            if bool(getattr(row, "enabled", True))
        ]
        segments = _assembly_section_preview_segments(rows, definition_library=definition_library)
        if not segments:
            text = scene.addText("No enabled Assembly/Subassembly rows are available for preview.")
            text.setDefaultTextColor(QtGui.QColor("#d8e0ea"))
            self.section_preview_status.setText("Preview: no enabled rows.")
            return
        scale = 42.0
        pen_axis = QtGui.QPen(QtGui.QColor("#6f7f95"))
        pen_axis.setStyle(QtCore.Qt.DashLine)
        pen_top = QtGui.QPen(QtGui.QColor("#ffd45a"))
        pen_top.setWidthF(2.4)
        pen_shape = QtGui.QPen(QtGui.QColor("#35c878"))
        pen_shape.setWidthF(1.2)
        brush_shape = QtGui.QBrush(QtGui.QColor(53, 200, 120, 55))
        pen_point = QtGui.QPen(QtGui.QColor("#111111"))
        brush_point = QtGui.QBrush(QtGui.QColor("#ffd45a"))
        scene.addLine(-320, 0, 320, 0, pen_axis)
        scene.addLine(0, -160, 0, 120, pen_axis)
        for segment in segments:
            row = segment["row"]
            side_label = str(segment["side"])
            points = list(segment["points"])
            topline = list(segment.get("topline", []) or points[:2])
            polygon = QtGui.QPolygonF([QtCore.QPointF(float(x) * scale, -float(z) * scale) for x, z in points])
            if len(points) >= 3:
                scene.addPolygon(polygon, pen_shape, brush_shape)
            for start, end in zip(topline, topline[1:]):
                scene.addLine(start[0] * scale, -start[1] * scale, end[0] * scale, -end[1] * scale, pen_top)
            for x, z in topline:
                scene.addEllipse(x * scale - 3.0, -z * scale - 3.0, 6.0, 6.0, pen_point, brush_point)
            top_end = topline[-1]
            label = scene.addText(f"{str(getattr(row, 'subassembly_id', '') or '')} ({side_label})")
            label.setDefaultTextColor(QtGui.QColor("#d8e0ea"))
            label.setPos(top_end[0] * scale + 5, -top_end[1] * scale - 18)
        bounds = scene.itemsBoundingRect().adjusted(-28, -28, 28, 28)
        scene.setSceneRect(bounds)
        try:
            self.section_preview_view.reset_zoom_for_bounds(bounds)
        except Exception:
            pass
        self.section_preview_status.setText(f"Preview: {len(rows)} row(s), {len(segments)} segment(s).")

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
    """Return active Subassembly preset rows."""

    rows = list(preset.get("subassemblies", []) or [])
    return [tuple(row) for row in rows]


def _validate_subassembly_model(
    model: AssemblySubassemblyModel,
    *,
    available_definition_ids: set[str] | None = None,
    available_preset_ids: set[str] | None = None,
    preset_versions: dict[str, str] | None = None,
) -> list[str]:
    messages: list[str] = []
    available_refs = set(available_definition_ids or set())
    available_presets = set(available_preset_ids or set())
    version_by_preset = dict(preset_versions or {})
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
            if subassembly.definition_ref and subassembly.definition_ref not in available_refs:
                messages.append(
                    f"ERROR: subassembly {subassembly.subassembly_id} references missing definition {subassembly.definition_ref}."
                )
            preset_ref = str(getattr(subassembly, "preset_ref", "") or "").strip()
            preset_version = str(getattr(subassembly, "preset_version", "") or "").strip()
            if preset_ref and preset_ref not in available_presets:
                messages.append(f"WARNING: subassembly {subassembly.subassembly_id} references missing preset {preset_ref}.")
            elif preset_ref and preset_version and version_by_preset.get(preset_ref, preset_version) != preset_version:
                messages.append(
                    f"WARNING: subassembly {subassembly.subassembly_id} preset {preset_ref} is outdated "
                    f"(row={preset_version}, library={version_by_preset.get(preset_ref)})."
                )
            if subassembly.width < 0.0:
                messages.append(f"ERROR: subassembly {subassembly.subassembly_id} width must not be negative.")
            messages.extend(f"WARNING: {message}" for message in subassembly_bench_validation_messages(subassembly))
    return messages


def _guess_missing_subassembly_refs_for_panel(panel) -> None:
    filled: list[str] = []
    skipped_existing: list[str] = []
    no_guess: list[str] = []
    table = getattr(panel, "table", None)
    if table is None:
        return
    for row in range(table.rowCount()):
        subassembly_id = _item_text(table, row, COL_ID) or f"subassembly:{row + 1}"
        if _item_text(table, row, COL_DEFINITION_REF):
            skipped_existing.append(subassembly_id)
            continue
        guessed_ref = _guess_subassembly_definition_ref(
            getattr(panel, "document", None),
            subassembly_id,
            kind=_item_text(table, row, COL_KIND),
            side=_item_text(table, row, COL_SIDE),
        )
        if not guessed_ref:
            no_guess.append(subassembly_id)
            continue
        _set_combo_text(table, row, COL_DEFINITION_REF, guessed_ref)
        try:
            panel._style_subassembly_row(row)
        except Exception:
            pass
        filled.append(f"{subassembly_id} -> {guessed_ref}")
    try:
        panel._refresh_selected_detail()
    except Exception:
        pass
    parts = [
        "Guessed missing Subassembly Refs.",
        "Warning: guesses are based on Subassembly ID text and may be inaccurate. Review before Apply.",
        f"filled: {len(filled)}",
    ]
    if filled:
        parts.append("assigned: " + ", ".join(filled[:6]) + (f", +{len(filled) - 6} more" if len(filled) > 6 else ""))
    if skipped_existing:
        parts.append("kept existing: " + ", ".join(skipped_existing[:6]) + (f", +{len(skipped_existing) - 6} more" if len(skipped_existing) > 6 else ""))
    if no_guess:
        parts.append("no confident guess: " + ", ".join(no_guess[:6]) + (f", +{len(no_guess) - 6} more" if len(no_guess) > 6 else ""))
    summary = getattr(panel, "summary", None)
    if summary is not None and hasattr(summary, "setPlainText"):
        summary.setPlainText("\n".join(parts))


def _active_template(model: AssemblySubassemblyModel) -> SubassemblySectionTemplate | None:
    rows = list(getattr(model, "template_rows", []) or [])
    if not rows:
        return None
    active_id = str(getattr(model, "active_template_id", "") or "").strip()
    for row in rows:
        if str(getattr(row, "template_id", "") or "") == active_id:
            return row
    return rows[0]


def _assembly_section_preview_wires(rows: list[TemplateSubassembly], *, definition_library=None, part_module=None) -> list[object]:
    if App is None or part_module is None:
        return []
    wires = []
    for segment in _assembly_section_preview_segments(rows, definition_library=definition_library):
        topline = list(segment.get("topline", []) or [])
        if len(topline) >= 2:
            for start, end in zip(topline, topline[1:]):
                if start != end:
                    wires.extend(_assembly_section_preview_segment_wires(part_module, start, end, end, start))
            continue
        top_start, top_end, bottom_end, bottom_start = segment["points"]
        wires.extend(_assembly_section_preview_segment_wires(part_module, top_start, top_end, bottom_end, bottom_start))
    return wires


def _assembly_section_preview_segments(rows: list[TemplateSubassembly], *, definition_library=None) -> list[dict[str, object]]:
    segments: list[dict[str, object]] = []
    edge_by_side = {"left": (0.0, 0.0), "right": (0.0, 0.0)}
    ordered_rows = sorted(
        list(rows or []),
        key=lambda row: (int(getattr(row, "subassembly_index", 0) or 0), str(getattr(row, "subassembly_id", "") or "")),
    )
    for row in ordered_rows:
        side = str(getattr(row, "side", "") or "center").strip().lower()
        if side == "both":
            sides = ("left", "right")
        elif side in {"left", "right"}:
            sides = (side,)
        else:
            sides = ("left",)
        for side_label in sides:
            start_offset, start_z = edge_by_side.get(side_label, (0.0, 0.0))
            segment = _assembly_section_preview_segment(row, side_label=side_label, start_offset=start_offset, start_z=start_z, definition_library=definition_library)
            if segment is None:
                continue
            segments.append({"row": row, "side": side_label, **segment})
            edge_by_side[side_label] = segment["end"]
    return segments


def _assembly_section_preview_segment(row: TemplateSubassembly, *, side_label: str, start_offset: float, start_z: float, definition_library=None):
    definition = _definition_by_ref_in_library(definition_library, str(getattr(row, "definition_ref", "") or ""))
    if definition is not None:
        segment = _assembly_section_preview_definition_segment(
            row,
            definition,
            side_label=side_label,
            start_offset=start_offset,
            start_z=start_z,
        )
        if segment is not None:
            return segment
    params = _assembly_section_preview_parameters(row, definition_library=definition_library)
    kind = str(getattr(row, "kind", "") or "").strip().lower().replace("-", "_")
    width = _float(params.get("width", getattr(row, "width", 0.0)), 0.0)
    if kind == "side_slope":
        width = _float(params.get("side_slope_width", width), width)
    if width <= 1.0e-9:
        return None
    slope = _float(params.get("slope", params.get("default_slope", getattr(row, "slope", 0.0))), 0.0)
    thickness = abs(_float(params.get("thickness", getattr(row, "thickness", 0.0)), 0.0))
    if thickness <= 1.0e-9 and kind in {"lane", "shoulder", "bike_lane", "sidewalk", "median"}:
        thickness = 0.2
    direction = 1.0 if side_label == "left" else -1.0
    end_offset = float(start_offset) + direction * width
    end_z = float(start_z) + width * slope / 100.0
    bottom_start = (float(start_offset), float(start_z) - thickness)
    bottom_end = (end_offset, end_z - thickness)
    top_start = (float(start_offset), float(start_z))
    top_end = (end_offset, end_z)
    return {
        "points": (top_start, top_end, bottom_end, bottom_start),
        "topline": (top_start, top_end),
        "end": top_end,
    }


def _assembly_section_preview_definition_segment(
    row: TemplateSubassembly,
    definition,
    *,
    side_label: str,
    start_offset: float,
    start_z: float,
):
    try:
        from ..services.evaluation.subassembly_expression_service import SubassemblyExpressionService
    except Exception:
        return None
    params = _assembly_section_preview_parameters(row, definition_library=None)
    try:
        evaluation = SubassemblyExpressionService().evaluate_definition(definition, parameter_overrides=params)
    except Exception:
        return None
    evaluated_points = {
        str(getattr(point, "point_id", "") or "").strip(): point
        for point in list(getattr(evaluation, "point_rows", []) or [])
        if str(getattr(point, "point_id", "") or "").strip()
    }
    if not evaluated_points:
        return None
    direction = 1.0 if side_label == "left" else -1.0

    def placed(point_id: str) -> tuple[float, float] | None:
        point = evaluated_points.get(str(point_id or "").strip())
        if point is None:
            return None
        return (
            float(start_offset) + direction * float(getattr(point, "x", 0.0) or 0.0),
            float(start_z) + float(getattr(point, "z", 0.0) or 0.0),
        )

    topline: list[tuple[float, float]] = []
    for link in list(getattr(definition, "link_rows", []) or []):
        start = placed(str(getattr(link, "start_point_ref", "") or ""))
        end = placed(str(getattr(link, "end_point_ref", "") or ""))
        if start is None or end is None:
            continue
        if not topline or topline[-1] != start:
            topline.append(start)
        topline.append(end)
    if not topline:
        for point in sorted(evaluated_points.values(), key=lambda item: float(getattr(item, "x", 0.0) or 0.0)):
            value = placed(str(getattr(point, "point_id", "") or ""))
            if value is not None:
                topline.append(value)
    topline = _unique_preview_points(topline)
    if len(topline) < 2:
        return None
    polygon_points = _assembly_section_preview_definition_polygon(definition, placed)
    if len(polygon_points) < 3:
        polygon_points = tuple(topline)
    end = max(topline, key=lambda point: abs(float(point[0]) - float(start_offset)))
    return {
        "points": tuple(polygon_points),
        "topline": tuple(topline),
        "end": end,
    }


def _assembly_section_preview_definition_polygon(definition, placed) -> tuple[tuple[float, float], ...]:
    for shape in list(getattr(definition, "shape_rows", []) or []):
        points = [
            placed(point_ref)
            for point_ref in list(getattr(shape, "point_refs", []) or [])
        ]
        output = _unique_preview_points([point for point in points if point is not None])
        if len(output) >= 3:
            return tuple(output)
    return ()


def _unique_preview_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    output: list[tuple[float, float]] = []
    for point in list(points or []):
        if output and abs(output[-1][0] - point[0]) <= 1.0e-9 and abs(output[-1][1] - point[1]) <= 1.0e-9:
            continue
        output.append(point)
    return output


def _assembly_section_preview_parameters(row: TemplateSubassembly, *, definition_library=None) -> dict[str, object]:
    params = {}
    definition = _definition_by_ref_in_library(definition_library, str(getattr(row, "definition_ref", "") or ""))
    if definition is not None:
        for parameter in list(getattr(definition, "parameter_rows", []) or []):
            key = str(getattr(parameter, "parameter_id", "") or "").strip()
            if key:
                params[key] = getattr(parameter, "value", "")
    params.update(dict(getattr(row, "parameters", {}) or {}))
    params.update(dict(getattr(row, "parameter_overrides", {}) or {}))
    if "width" not in params:
        params["width"] = getattr(row, "width", 0.0)
    if "slope" not in params:
        params["slope"] = getattr(row, "slope", 0.0)
    if "thickness" not in params:
        params["thickness"] = getattr(row, "thickness", 0.0)
    return params


def _definition_by_ref_in_library(library, definition_ref: str):
    ref = str(definition_ref or "").strip()
    if not ref or library is None:
        return None
    for row in list(getattr(library, "definition_rows", []) or []):
        if str(getattr(row, "definition_id", "") or "").strip() == ref:
            return row
    return None


def _assembly_section_preview_segment_wires(part_module, top_start, top_end, bottom_end, bottom_start) -> list[object]:
    vectors = [_preview_vector(top_start), _preview_vector(top_end), _preview_vector(bottom_end), _preview_vector(bottom_start), _preview_vector(top_start)]
    wires = []
    for start, end in ((vectors[0], vectors[1]), (vectors[1], vectors[2]), (vectors[2], vectors[3]), (vectors[3], vectors[0])):
        if _same_preview_vector(start, end):
            continue
        wires.append(part_module.makeLine(start, end))
    return wires


def _preview_vector(point: tuple[float, float]):
    return App.Vector(float(point[0]), 0.0, float(point[1]))


def _same_preview_vector(first, second, tolerance: float = 1.0e-9) -> bool:
    try:
        return (
            abs(float(first.x) - float(second.x)) <= tolerance
            and abs(float(first.y) - float(second.y)) <= tolerance
            and abs(float(first.z) - float(second.z)) <= tolerance
        )
    except Exception:
        return False


def _style_assembly_section_preview_object(obj) -> None:
    view = getattr(obj, "ViewObject", None)
    if view is None:
        return
    try:
        view.LineColor = (0.05, 0.85, 1.0)
        view.PointColor = (1.0, 0.8, 0.1)
        view.LineWidth = 3.0
        view.PointSize = 5.0
        view.Visibility = True
    except Exception:
        pass


def _set_preview_property(obj, name: str, value: object) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyString", name, "CorridorRoad")
        except Exception:
            return
    try:
        setattr(obj, name, str(value or ""))
    except Exception:
        pass


def _set_preview_integer_property(obj, name: str, value: int) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyInteger", name, "CorridorRoad")
        except Exception:
            return
    try:
        setattr(obj, name, int(value or 0))
    except Exception:
        pass


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


def _set_combo_text(table, row: int, col: int, value: object) -> None:
    widget = table.cellWidget(row, col)
    text = str(value or "").strip()
    if widget is not None and hasattr(widget, "findText") and hasattr(widget, "setCurrentIndex"):
        index = widget.findText(text)
        if index < 0 and text and hasattr(widget, "addItem"):
            widget.addItem(text)
            index = widget.findText(text)
        if index >= 0:
            widget.setCurrentIndex(index)
        return
    _set_table_item_text(table, row, col, text)


def _preset_status_display(subassembly: TemplateSubassembly) -> str:
    status = str(getattr(subassembly, "preset_status", "") or "").strip()
    if status:
        return status
    return "linked" if str(getattr(subassembly, "preset_ref", "") or "").strip() else "snapshot"


def _preset_status_legend_text() -> str:
    return (
        "Template status colors: "
        "linked=green, modified=yellow, snapshot=gray, missing=red, outdated=orange. "
        "Refresh updates linked outdated template rows; Detach keeps a local custom snapshot."
    )


def _subassembly_library_model(document):
    library_obj = find_v1_subassembly_library(document)
    return to_subassembly_library(library_obj) if library_obj is not None else None


def _subassembly_preset_library_model(document):
    library_obj = find_v1_subassembly_preset_library(document)
    return to_subassembly_preset_library(library_obj) if library_obj is not None else None


def _subassembly_definition_ref_values(document) -> list[str]:
    library = _subassembly_library_model(document)
    values = [""]
    if library is not None:
        values.extend(str(row.definition_id) for row in list(getattr(library, "definition_rows", []) or []) if str(row.definition_id))
    return values


def _subassembly_definition_ref_set(document) -> set[str]:
    return {value for value in _subassembly_definition_ref_values(document) if value}


def _guess_subassembly_definition_ref(document, subassembly_id: str, *, kind: str = "", side: str = "") -> str:
    candidates = _subassembly_definition_guess_candidates(document)
    if not candidates:
        return ""
    wanted_tokens = _guess_tokens(subassembly_id)
    kind_tokens = _guess_tokens(kind)
    side_tokens = [token for token in _guess_tokens(side) if token not in {"center", "both"}]
    best_ref = ""
    best_score = 0
    for candidate in candidates:
        candidate_ref = str(candidate.get("definition_id", "") or "").strip()
        if not candidate_ref:
            continue
        candidate_text = str(candidate.get("search_text", "") or candidate_ref)
        candidate_tokens = set(_guess_tokens(candidate_text))
        candidate_compact = _compact_guess_text(candidate_text)
        subassembly_compact = _compact_guess_text(subassembly_id)
        score = 0
        if subassembly_compact and subassembly_compact in candidate_compact:
            score += 90
        for token in wanted_tokens:
            if token in candidate_tokens:
                score += 12
            elif token and token in candidate_compact:
                score += 6
        for token in kind_tokens:
            if token in candidate_tokens:
                score += 24
            elif token and token in candidate_compact:
                score += 12
        for token in side_tokens:
            if token in candidate_tokens:
                score += 3
        if score > best_score:
            best_score = score
            best_ref = candidate_ref
    return best_ref if best_score >= 12 else ""


def _subassembly_definition_guess_candidates(document) -> list[dict[str, str]]:
    library = _subassembly_library_model(document)
    if library is None:
        return [{"definition_id": value, "search_text": value} for value in _subassembly_definition_ref_values(document) if value]
    candidates: list[dict[str, str]] = []
    for row in list(getattr(library, "definition_rows", []) or []):
        definition_id = str(getattr(row, "definition_id", "") or "").strip()
        if not definition_id:
            continue
        search_parts = [
            definition_id,
            getattr(row, "name", ""),
            getattr(row, "kind", ""),
            getattr(row, "category", ""),
            getattr(row, "side", ""),
            getattr(row, "notes", ""),
        ]
        candidates.append(
            {
                "definition_id": definition_id,
                "search_text": " ".join(str(part or "") for part in search_parts),
            }
        )
    return candidates


def _guess_tokens(value: object) -> list[str]:
    text = str(value or "").strip().lower()
    for separator in (":", ";", ",", ".", "/", "\\", "-", "_", "(", ")", "[", "]", "{", "}"):
        text = text.replace(separator, " ")
    return [token for token in text.split() if token and token not in {"subassembly", "definition", "preset", "basic"}]


def _compact_guess_text(value: object) -> str:
    return "".join(_guess_tokens(value))


def _subassembly_preset_ref_values(document) -> list[str]:
    library = _subassembly_preset_library_model(document)
    values = [""]
    if library is not None:
        values.extend(
            str(row.preset_id)
            for row in list(getattr(library, "subassembly_preset_rows", []) or [])
            if str(row.preset_id)
        )
    return values


def _subassembly_preset_ref_set(document) -> set[str]:
    return {value for value in _subassembly_preset_ref_values(document) if value}


def _subassembly_preset_for_ref(document, preset_ref: str):
    ref = str(preset_ref or "").strip()
    if not ref:
        return None
    library = _subassembly_preset_library_model(document)
    if library is None:
        return None
    return library.subassembly_preset_by_id(ref)


def _subassembly_preset_version_map(document) -> dict[str, str]:
    library = _subassembly_preset_library_model(document)
    if library is None:
        return {}
    return {
        str(getattr(row, "preset_id", "") or ""): str(getattr(row, "version", "") or "")
        for row in list(getattr(library, "subassembly_preset_rows", []) or [])
        if str(getattr(row, "preset_id", "") or "")
    }


def _apply_preset_defaults_to_row(table, row: int, preset, *, clear_overrides: bool) -> None:
    parameters = dict(getattr(preset, "parameter_defaults", {}) or {})
    kind = str(getattr(preset, "kind", "") or _item_text(table, row, COL_KIND) or "lane")
    _set_table_item_text(table, row, COL_KIND, kind)
    definition_ref = str(getattr(preset, "definition_ref", "") or "").strip()
    if definition_ref:
        _set_combo_text(table, row, COL_DEFINITION_REF, definition_ref)
    _set_table_item_text(table, row, COL_PRESET_VERSION, str(getattr(preset, "version", "") or ""))
    _set_combo_text(table, row, COL_PRESET_STATUS, "linked")
    _set_table_item_text(
        table,
        row,
        COL_WIDTH,
        _format_float(_first_numeric_parameter(parameters, ("width", "side_slope_width"), _float(_item_text(table, row, COL_WIDTH)))),
    )
    _set_table_item_text(
        table,
        row,
        COL_SLOPE,
        _format_float(_first_numeric_parameter(parameters, ("slope", "default_slope"), _float(_item_text(table, row, COL_SLOPE)))),
    )
    _set_table_item_text(
        table,
        row,
        COL_THICKNESS,
        _format_float(_first_numeric_parameter(parameters, ("thickness",), _float(_item_text(table, row, COL_THICKNESS)))),
    )
    if "material" in parameters:
        _set_table_item_text(table, row, COL_MATERIAL, str(parameters.get("material", "") or ""))
    if clear_overrides:
        _set_table_item_text(table, row, COL_PARAMETERS, serialize_subassembly_parameters(parameters))
        _set_table_item_text(table, row, COL_OVERRIDES, "")
    else:
        merged_parameters = dict(parameters)
        merged_parameters.update(parse_subassembly_parameters(_item_text(table, row, COL_PARAMETERS)))
        _set_table_item_text(table, row, COL_PARAMETERS, serialize_subassembly_parameters(merged_parameters))
    if not _item_text(table, row, COL_SOURCE_INSTANCE_REF):
        _set_table_item_text(table, row, COL_SOURCE_INSTANCE_REF, _item_text(table, row, COL_ID))


def _subassembly_definition_for_ref(document, definition_ref: str):
    ref = str(definition_ref or "").strip()
    if not ref:
        return None
    library = _subassembly_library_model(document)
    if library is None:
        return None
    return library.definition_by_id(ref)


def _definition_override_rows(definition, overrides: dict[str, object]) -> list[tuple[str, object]]:
    override_values = dict(overrides or {})
    rows = []
    for parameter in list(getattr(definition, "parameter_rows", []) or []):
        key = str(getattr(parameter, "parameter_id", "") or "").strip()
        if not key:
            continue
        rows.append((key, override_values.get(key, getattr(parameter, "value", ""))))
    for key, value in sorted(override_values.items()):
        if not any(existing_key == key for existing_key, _existing_value in rows):
            rows.append((key, value))
    return rows


def _definition_parameter_defaults(definition) -> dict[str, object]:
    if definition is None:
        return {}
    return {
        str(getattr(parameter, "parameter_id", "") or "").strip(): getattr(parameter, "value", "")
        for parameter in list(getattr(definition, "parameter_rows", []) or [])
        if str(getattr(parameter, "parameter_id", "") or "").strip()
    }


def _override_value_changed(key: object, value: object, default: object) -> bool:
    key_text = str(key or "").strip()
    if key_text == "bench_rows":
        return _normalize_bench_rows_text(value) != _normalize_bench_rows_text(default)
    return str(value or "").strip() != str(default or "").strip()


def _definition_preview_text(definition, overrides: dict[str, object]) -> str:
    if definition is None:
        return ""
    values = {
        str(getattr(row, "parameter_id", "") or ""): getattr(row, "value", "")
        for row in list(getattr(definition, "parameter_rows", []) or [])
        if str(getattr(row, "parameter_id", "") or "")
    }
    values.update(dict(overrides or {}))
    lines = [
        f"definition_ref: {getattr(definition, 'definition_id', '')}",
        f"kind: {getattr(definition, 'kind', '')}, side_behavior: {getattr(definition, 'side_behavior', '')}",
        "",
        "parameters:",
    ]
    if values:
        lines.extend(f"- {key} = {value}" for key, value in sorted(values.items()))
    else:
        lines.append("- none")
    lines.append("")
    lines.append("points:")
    point_rows = list(getattr(definition, "point_rows", []) or [])
    if point_rows:
        lines.extend(
            f"- {getattr(row, 'point_id', '')} | x={getattr(row, 'x_expr', '')} | z={getattr(row, 'z_expr', '')} | code={getattr(row, 'code', '')}"
            for row in point_rows
        )
    else:
        lines.append("- none")
    lines.append("")
    lines.append("links:")
    link_rows = list(getattr(definition, "link_rows", []) or [])
    if link_rows:
        lines.extend(
            f"- {getattr(row, 'link_id', '')} | {getattr(row, 'start_point_ref', '')}->{getattr(row, 'end_point_ref', '')} | surface_role={getattr(row, 'surface_role', '')}"
            for row in link_rows
        )
    else:
        lines.append("- none")
    return "\n".join(lines)


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
    for row in _parsed_bench_row_dicts(rows):
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
    return "; ".join(parts)


def _normalize_bench_rows_text(value: object) -> str:
    return _compact_bench_rows(_parsed_bench_row_dicts(value))


def _parsed_bench_row_dicts(value: object) -> list[dict[str, object]]:
    result = parse_bench_rows(value)
    if result.rows:
        return bench_rows_to_dicts(result.rows)
    return normalize_bench_rows(value)


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


def _first_numeric_parameter(parameters: dict[str, object], keys: tuple[str, ...], default: float = 0.0) -> float:
    for key in keys:
        if key in dict(parameters or {}):
            return _float(dict(parameters or {}).get(key), default)
    return _float(default)


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


class _AssemblySectionPreviewView(QtWidgets.QGraphicsView):
    """Graphics view with mouse-wheel zoom for the Assembly/Subassembly section preview."""

    def __init__(self, scene=None):
        super().__init__(scene)
        self._zoom_factor = 1.0
        try:
            self.setFocusPolicy(QtCore.Qt.StrongFocus)
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
            self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        except Exception:
            pass

    def wheelEvent(self, event):  # noqa: N802 - Qt API name
        try:
            delta = event.angleDelta().y()
        except Exception:
            delta = 0
        if not delta:
            try:
                super().wheelEvent(event)
            except Exception:
                pass
            return
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        next_zoom = self._zoom_factor * factor
        if next_zoom < 0.15 or next_zoom > 12.0:
            try:
                event.accept()
            except Exception:
                pass
            return
        self._zoom_factor = next_zoom
        self.scale(factor, factor)
        try:
            event.accept()
        except Exception:
            pass

    def reset_zoom_for_bounds(self, bounds) -> None:
        try:
            self.resetTransform()
            self._zoom_factor = 1.0
            self.fitInView(bounds, QtCore.Qt.KeepAspectRatio)
        except Exception:
            pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditAssemblySubassembly", CmdV1AssemblySubassemblyEditor())
