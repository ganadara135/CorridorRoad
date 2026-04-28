"""Assembly editor command for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtWidgets

from ...objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from ..models.source.assembly_model import (
    ASSEMBLY_COMPONENT_KINDS,
    ASSEMBLY_COMPONENT_SIDES,
    AssemblyModel,
    SectionTemplate,
    TemplateComponent,
)
from ..objects.obj_alignment import find_v1_alignment
from ..objects.obj_assembly import (
    create_or_update_v1_assembly_model_object,
    find_v1_assembly_model,
    to_assembly_model,
)


def starter_assembly_model_from_document(document=None, *, project=None, alignment=None) -> AssemblyModel:
    """Build one non-destructive starter AssemblyModel."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prj = project or find_project(doc)
    alignment_obj = alignment or find_v1_alignment(doc)
    alignment_id = str(getattr(alignment_obj, "AlignmentId", "") or "")
    return AssemblyModel(
        schema_version=1,
        project_id=_project_id(prj),
        assembly_id="assembly:basic-road",
        alignment_id=alignment_id,
        active_template_id="template:basic-road",
        label="Basic Road Assembly",
        template_rows=[
            SectionTemplate(
                template_id="template:basic-road",
                template_kind="roadway",
                template_index=1,
                label="Basic Road",
                component_rows=[
                    TemplateComponent("lane:left", "lane", 1, "left", 3.5, -0.02, 0.25, "asphalt"),
                    TemplateComponent("lane:right", "lane", 2, "right", 3.5, -0.02, 0.25, "asphalt"),
                    TemplateComponent("shoulder:left", "shoulder", 3, "left", 1.5, -0.04, 0.20, "aggregate"),
                    TemplateComponent("shoulder:right", "shoulder", 4, "right", 1.5, -0.04, 0.20, "aggregate"),
                    TemplateComponent("side_slope:left", "side_slope", 5, "left", 4.0, -0.5, 0.0, "earth"),
                    TemplateComponent("side_slope:right", "side_slope", 6, "right", 4.0, -0.5, 0.0, "earth"),
                ],
                notes="Starter road assembly; edit before corridor generation.",
            )
        ],
    )


def apply_v1_assembly_model(
    *,
    document=None,
    project=None,
    assembly_model: AssemblyModel,
):
    """Persist a v1 AssemblyModel source object."""

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
    obj = create_or_update_v1_assembly_model_object(
        document=doc,
        project=prj,
        assembly_model=assembly_model,
    )
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def run_v1_assembly_editor_command():
    """Open the v1 Assembly editor panel."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    panel = V1AssemblyEditorTaskPanel(document=document)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return find_v1_assembly_model(document)


class V1AssemblyEditorTaskPanel:
    """Table-based v1 Assembly source editor."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.assembly_obj = find_v1_assembly_model(self.document)
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
        widget.setWindowTitle("CorridorRoad v1 - Assembly")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Assembly")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        note = QtWidgets.QLabel(
            "Define reusable section components. Apply stores source rows only; it does not build corridor geometry."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        meta_row = QtWidgets.QHBoxLayout()
        meta_row.addWidget(QtWidgets.QLabel("Assembly ID:"))
        self._assembly_id = QtWidgets.QLineEdit("assembly:basic-road")
        meta_row.addWidget(self._assembly_id)
        meta_row.addWidget(QtWidgets.QLabel("Template ID:"))
        self._template_id = QtWidgets.QLineEdit("template:basic-road")
        meta_row.addWidget(self._template_id)
        layout.addLayout(meta_row)

        self._table = QtWidgets.QTableWidget(0, 9)
        self._table.setHorizontalHeaderLabels(
            ["Component ID", "Kind", "Side", "Width", "Slope", "Thickness", "Material", "Enabled", "Notes"]
        )
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        try:
            self._table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        layout.addWidget(self._table, 1)

        edit_row = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add Component")
        add_button.clicked.connect(self._add_component_row)
        edit_row.addWidget(add_button)
        delete_button = QtWidgets.QPushButton("Delete Selected")
        delete_button.clicked.connect(self._delete_selected_rows)
        edit_row.addWidget(delete_button)
        starter_button = QtWidgets.QPushButton("Load Starter Assembly")
        starter_button.clicked.connect(self._load_starter_rows)
        edit_row.addWidget(starter_button)
        edit_row.addStretch(1)
        layout.addLayout(edit_row)

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setFixedHeight(70)
        self._status.setPlainText("No assembly source object is selected.")
        layout.addWidget(self._status)

        action_row = QtWidgets.QHBoxLayout()
        validate_button = QtWidgets.QPushButton("Validate")
        validate_button.clicked.connect(self._validate)
        action_row.addWidget(validate_button)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        action_row.addWidget(apply_button)
        action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        action_row.addWidget(close_button)
        layout.addLayout(action_row)
        return widget

    def _load_existing_rows(self) -> None:
        model = to_assembly_model(self.assembly_obj)
        if model is None:
            return
        self._replace_model(model)
        self._set_status(f"Loaded {sum(len(t.component_rows) for t in model.template_rows)} component row(s).")

    def _load_starter_rows(self) -> None:
        try:
            self._replace_model(starter_assembly_model_from_document(self.document))
            self._set_status("Starter Assembly loaded. Apply when ready.")
        except Exception as exc:
            self._set_status(f"Starter Assembly was not loaded:\n{exc}")

    def _replace_model(self, model: AssemblyModel) -> None:
        self._assembly_id.setText(model.assembly_id or "assembly:basic-road")
        template = model.template_rows[0] if model.template_rows else SectionTemplate("template:basic-road", "roadway")
        self._template_id.setText(template.template_id)
        self._table.setRowCount(0)
        for row in template.component_rows:
            self._append_row(row)

    def _append_row(self, row: TemplateComponent | None = None) -> None:
        row = row or TemplateComponent(
            component_id=f"component:{self._table.rowCount() + 1}",
            component_index=self._table.rowCount() + 1,
            kind="lane",
            side="right",
            width=3.5,
            slope=-0.02,
        )
        index = self._table.rowCount()
        self._table.insertRow(index)
        values = [
            row.component_id,
            row.kind,
            row.side,
            _format_float(row.width),
            _format_float(row.slope),
            _format_float(row.thickness),
            row.material,
            "1" if row.enabled else "0",
            row.notes,
        ]
        for col, value in enumerate(values):
            if col == 1:
                combo = QtWidgets.QComboBox()
                combo.addItems(list(ASSEMBLY_COMPONENT_KINDS))
                combo.setCurrentText(str(value) if str(value) in ASSEMBLY_COMPONENT_KINDS else "lane")
                self._table.setCellWidget(index, col, combo)
            elif col == 2:
                combo = QtWidgets.QComboBox()
                combo.addItems(list(ASSEMBLY_COMPONENT_SIDES))
                combo.setCurrentText(str(value) if str(value) in ASSEMBLY_COMPONENT_SIDES else "center")
                self._table.setCellWidget(index, col, combo)
            elif col == 7:
                combo = QtWidgets.QComboBox()
                combo.addItems(["1", "0"])
                combo.setCurrentText(str(value))
                self._table.setCellWidget(index, col, combo)
            else:
                self._table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))

    def _add_component_row(self) -> None:
        self._append_row()
        self._set_status("Added an Assembly component row.")

    def _delete_selected_rows(self) -> None:
        rows = sorted({item.row() for item in list(self._table.selectedItems() or [])}, reverse=True)
        if not rows and self._table.currentRow() >= 0:
            rows = [self._table.currentRow()]
        for row_index in rows:
            self._table.removeRow(row_index)
        self._set_status(f"Deleted {len(rows)} component row(s).")

    def _validate(self) -> None:
        try:
            model = self._model_from_table()
            messages = _validate_assembly_model(model)
            self._set_status("\n".join(messages) if messages else "Validation status: ok")
        except Exception as exc:
            self._set_status(f"Assembly validation failed:\n{exc}")

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            model = self._model_from_table()
            messages = _validate_assembly_model(model)
            if any(message.startswith("ERROR") for message in messages):
                self._set_status("\n".join(messages))
                _show_message(self.form, "Assembly", "Assembly was not applied because validation has errors.")
                return False
            self.assembly_obj = apply_v1_assembly_model(document=self.document, assembly_model=model)
            self._set_status(("\n".join(messages) if messages else "Validation status: ok") + f"\n\nApplied to: {self.assembly_obj.Label}")
            _show_message(self.form, "Assembly", f"Assembly has been applied.\nComponents: {len(model.template_rows[0].component_rows)}")
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_status(f"Assembly was not applied:\n{exc}")
            _show_message(self.form, "Assembly", f"Assembly was not applied.\n{exc}")
            return False

    def _model_from_table(self) -> AssemblyModel:
        alignment = find_v1_alignment(self.document)
        template_id = self._template_id.text().strip() or "template:basic-road"
        return AssemblyModel(
            schema_version=1,
            project_id=_project_id(find_project(self.document)),
            assembly_id=self._assembly_id.text().strip() or "assembly:basic-road",
            alignment_id=str(getattr(alignment, "AlignmentId", "") or ""),
            active_template_id=template_id,
            label="Assembly",
            template_rows=[
                SectionTemplate(
                    template_id=template_id,
                    template_kind="roadway",
                    template_index=1,
                    label=template_id,
                    component_rows=self._table_rows(),
                )
            ],
        )

    def _table_rows(self) -> list[TemplateComponent]:
        rows: list[TemplateComponent] = []
        for row_index in range(self._table.rowCount()):
            rows.append(
                TemplateComponent(
                    component_id=_item_text(self._table, row_index, 0) or f"component:{row_index + 1}",
                    component_index=row_index + 1,
                    kind=_item_text(self._table, row_index, 1) or "lane",
                    side=_item_text(self._table, row_index, 2) or "center",
                    width=_required_float(_item_text(self._table, row_index, 3) or "0", f"Row {row_index + 1} width"),
                    slope=_required_float(_item_text(self._table, row_index, 4) or "0", f"Row {row_index + 1} slope"),
                    thickness=_required_float(_item_text(self._table, row_index, 5) or "0", f"Row {row_index + 1} thickness"),
                    material=_item_text(self._table, row_index, 6),
                    enabled=(_item_text(self._table, row_index, 7) != "0"),
                    notes=_item_text(self._table, row_index, 8),
                )
            )
        return rows

    def _set_status(self, text: str) -> None:
        self._status.setPlainText(str(text or ""))


class CmdV1AssemblyEditor:
    """Open the v1 Assembly source editor."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("typical_section.svg"),
            "MenuText": "Assembly",
            "ToolTip": "Define v1 assembly source components for region references",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_assembly_editor_command()


def _validate_assembly_model(model: AssemblyModel) -> list[str]:
    messages: list[str] = []
    if not model.assembly_id:
        messages.append("ERROR: assembly_id is required.")
    if not model.template_rows:
        messages.append("ERROR: at least one template row is required.")
    for template in model.template_rows:
        if not template.template_id:
            messages.append("ERROR: template_id is required.")
        component_ids = set()
        for component in template.component_rows:
            if not component.component_id:
                messages.append("ERROR: component_id is required.")
            if component.component_id in component_ids:
                messages.append(f"ERROR: duplicate component_id {component.component_id}.")
            component_ids.add(component.component_id)
            if component.width < 0.0:
                messages.append(f"ERROR: component {component.component_id} width must not be negative.")
    if not messages:
        messages.append("Validation status: ok")
    return messages


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


def _format_float(value: float) -> str:
    return f"{float(value):.3f}"


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditAssembly", CmdV1AssemblyEditor())
