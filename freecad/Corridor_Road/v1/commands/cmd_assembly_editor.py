"""Assembly editor command for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
    import Part
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None
    Part = None

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
from ..services.builders.applied_section_service import (
    ditch_component_local_profile,
    ditch_material_policy,
    ditch_component_validation_messages,
)


DITCH_SHAPES = ("trapezoid", "u", "l", "rectangular", "v", "custom_polyline")
DITCH_PARAMETER_KEYS = (
    "shape",
    "top_width",
    "bottom_width",
    "depth",
    "inner_slope",
    "outer_slope",
    "invert_offset",
    "wall_thickness",
    "lining_thickness",
    "wall_side",
    "section_points",
)
DITCH_PARAMETER_FIELDS = (
    ("top_width", "Top width"),
    ("bottom_width", "Bottom width"),
    ("depth", "Depth"),
    ("inner_slope", "Inner slope"),
    ("outer_slope", "Outer slope"),
    ("invert_offset", "Invert offset"),
    ("wall_thickness", "Wall thickness"),
    ("lining_thickness", "Lining thickness"),
    ("wall_side", "Wall side"),
    ("section_points", "Section points"),
)
DITCH_SHAPE_FIELDS = {
    "trapezoid": ("top_width", "bottom_width", "depth", "inner_slope", "outer_slope"),
    "u": ("bottom_width", "depth", "wall_thickness", "lining_thickness"),
    "l": ("top_width", "bottom_width", "depth", "wall_thickness", "wall_side", "lining_thickness"),
    "rectangular": ("bottom_width", "depth", "wall_thickness", "lining_thickness"),
    "v": ("top_width", "depth", "invert_offset", "inner_slope", "outer_slope"),
    "custom_polyline": ("section_points",),
}
DITCH_SHAPE_DEFAULTS = {
    "trapezoid": {"top_width": "1.800", "bottom_width": "0.600", "depth": "0.450", "inner_slope": "1.500", "outer_slope": "2.000"},
    "u": {"bottom_width": "0.600", "depth": "0.500", "wall_thickness": "0.150", "lining_thickness": "0.120"},
    "l": {"top_width": "1.000", "bottom_width": "0.700", "depth": "0.450", "wall_thickness": "0.150", "wall_side": "inner"},
    "rectangular": {"bottom_width": "0.800", "depth": "0.500", "wall_thickness": "0.150", "lining_thickness": "0.120"},
    "v": {"top_width": "1.600", "depth": "0.400", "invert_offset": "0.800", "inner_slope": "2.000", "outer_slope": "2.000"},
    "custom_polyline": {"section_points": "0,0,inner_edge;0.5,-0.4,invert;1.0,0,outer_edge"},
}


ASSEMBLY_PRESETS = {
    "Basic Road": {
        "assembly_id": "assembly:basic-road",
        "template_id": "template:basic-road",
        "label": "Basic Road Assembly",
        "template_label": "Basic Road",
        "note": "Two-lane rural starter with shoulders and earth side slopes.",
        "components": [
            ("lane:left", "lane", "left", 3.5, -0.02, 0.25, "asphalt", "Left travel lane"),
            ("lane:right", "lane", "right", 3.5, -0.02, 0.25, "asphalt", "Right travel lane"),
            ("shoulder:left", "shoulder", "left", 1.5, -0.04, 0.20, "aggregate", "Left shoulder"),
            ("shoulder:right", "shoulder", "right", 1.5, -0.04, 0.20, "aggregate", "Right shoulder"),
            ("side_slope:left", "side_slope", "left", 4.0, -0.5, 0.0, "earth", "Left slope face"),
            ("side_slope:right", "side_slope", "right", 4.0, -0.5, 0.0, "earth", "Right slope face"),
        ],
    },
    "Urban Curb & Gutter": {
        "assembly_id": "assembly:urban-curb-gutter",
        "template_id": "template:urban-curb-gutter",
        "label": "Urban Curb & Gutter Assembly",
        "template_label": "Urban Curb & Gutter",
        "note": "Urban road with lanes, gutters, curbs, sidewalks, and shallow grading strips.",
        "components": [
            ("lane:left", "lane", "left", 3.25, -0.02, 0.28, "asphalt", "Left urban lane"),
            ("lane:right", "lane", "right", 3.25, -0.02, 0.28, "asphalt", "Right urban lane"),
            ("gutter:left", "gutter", "left", 0.45, -0.03, 0.18, "concrete", "Left gutter pan"),
            ("gutter:right", "gutter", "right", 0.45, -0.03, 0.18, "concrete", "Right gutter pan"),
            ("curb:left", "curb", "left", 0.20, 0.0, 0.30, "concrete", "Left curb"),
            ("curb:right", "curb", "right", 0.20, 0.0, 0.30, "concrete", "Right curb"),
            ("sidewalk:left", "sidewalk", "left", 1.8, -0.015, 0.12, "concrete", "Left sidewalk"),
            ("sidewalk:right", "sidewalk", "right", 1.8, -0.015, 0.12, "concrete", "Right sidewalk"),
            ("green_strip:left", "green_strip", "left", 1.0, -0.03, 0.0, "landscape", "Left verge"),
            ("green_strip:right", "green_strip", "right", 1.0, -0.03, 0.0, "landscape", "Right verge"),
        ],
    },
    "Divided Road": {
        "assembly_id": "assembly:divided-road",
        "template_id": "template:divided-road",
        "label": "Divided Road Assembly",
        "template_label": "Divided Road",
        "note": "Four-lane divided road with center median, shoulders, barriers, and side slopes.",
        "components": [
            ("median:center", "median", "center", 3.0, 0.0, 0.18, "landscape", "Raised or depressed median allowance"),
            ("lane:left-1", "lane", "left", 3.5, -0.02, 0.30, "asphalt", "Inner left lane"),
            ("lane:left-2", "lane", "left", 3.5, -0.02, 0.30, "asphalt", "Outer left lane"),
            ("lane:right-1", "lane", "right", 3.5, -0.02, 0.30, "asphalt", "Inner right lane"),
            ("lane:right-2", "lane", "right", 3.5, -0.02, 0.30, "asphalt", "Outer right lane"),
            ("shoulder:left", "shoulder", "left", 2.5, -0.04, 0.22, "aggregate", "Left outside shoulder"),
            ("shoulder:right", "shoulder", "right", 2.5, -0.04, 0.22, "aggregate", "Right outside shoulder"),
            ("barrier:left", "barrier", "left", 0.4, 0.0, 0.0, "concrete", "Left roadside barrier placeholder"),
            ("barrier:right", "barrier", "right", 0.4, 0.0, 0.0, "concrete", "Right roadside barrier placeholder"),
            ("side_slope:left", "side_slope", "left", 5.0, -0.4, 0.0, "earth", "Left slope face"),
            ("side_slope:right", "side_slope", "right", 5.0, -0.4, 0.0, "earth", "Right slope face"),
        ],
    },
    "Bridge Interface": {
        "assembly_id": "assembly:bridge-interface",
        "template_id": "template:bridge-interface",
        "label": "Bridge Interface Assembly",
        "template_label": "Bridge Interface",
        "note": "Road deck handoff with barriers and structure-interface placeholders; slope faces are intentionally omitted.",
        "components": [
            ("lane:left", "lane", "left", 3.5, -0.02, 0.22, "asphalt", "Left bridge lane wearing surface"),
            ("lane:right", "lane", "right", 3.5, -0.02, 0.22, "asphalt", "Right bridge lane wearing surface"),
            ("shoulder:left", "shoulder", "left", 1.2, -0.02, 0.18, "asphalt", "Left bridge shoulder"),
            ("shoulder:right", "shoulder", "right", 1.2, -0.02, 0.18, "asphalt", "Right bridge shoulder"),
            ("barrier:left", "barrier", "left", 0.45, 0.0, 0.0, "concrete", "Left bridge barrier placeholder"),
            ("barrier:right", "barrier", "right", 0.45, 0.0, 0.0, "concrete", "Right bridge barrier placeholder"),
            ("structure_interface:deck", "structure_interface", "center", 0.0, 0.0, 0.0, "structure", "Bridge deck structure handoff"),
        ],
    },
    "Drainage Ditch Road": {
        "assembly_id": "assembly:drainage-ditch-road",
        "template_id": "template:drainage-ditch-road",
        "label": "Drainage Ditch Road Assembly",
        "template_label": "Drainage Ditch Road",
        "note": "Rural road with shoulders, ditch components, and wider side-slope grading.",
        "components": [
            ("lane:left", "lane", "left", 3.5, -0.02, 0.25, "asphalt", "Left travel lane"),
            ("lane:right", "lane", "right", 3.5, -0.02, 0.25, "asphalt", "Right travel lane"),
            ("shoulder:left", "shoulder", "left", 1.8, -0.04, 0.20, "aggregate", "Left shoulder"),
            ("shoulder:right", "shoulder", "right", 1.8, -0.04, 0.20, "aggregate", "Right shoulder"),
            ("ditch:left", "ditch", "left", 1.8, -0.02, 0.0, "earth", "Left trapezoid roadside ditch", {"shape": "trapezoid", "bottom_width": 0.6, "depth": 0.45, "inner_slope": 1.5, "outer_slope": 2.0}),
            ("ditch:right", "ditch", "right", 1.8, -0.02, 0.0, "earth", "Right trapezoid roadside ditch", {"shape": "trapezoid", "bottom_width": 0.6, "depth": 0.45, "inner_slope": 1.5, "outer_slope": 2.0}),
            ("side_slope:left", "side_slope", "left", 6.0, -0.33, 0.0, "earth", "Left slope face to terrain"),
            ("side_slope:right", "side_slope", "right", 6.0, -0.33, 0.0, "earth", "Right slope face to terrain"),
        ],
    },
}


def assembly_preset_names() -> list[str]:
    """Return available v1 Assembly preset names."""

    return list(ASSEMBLY_PRESETS.keys())


def starter_assembly_model_from_document(document=None, *, project=None, alignment=None) -> AssemblyModel:
    """Build one non-destructive starter AssemblyModel."""

    return assembly_preset_model_from_document("Basic Road", document=document, project=project, alignment=alignment)


def assembly_preset_model_from_document(
    preset_name: str,
    document=None,
    *,
    project=None,
    alignment=None,
) -> AssemblyModel:
    """Build a non-destructive AssemblyModel from a named preset."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    preset = ASSEMBLY_PRESETS.get(str(preset_name or "").strip())
    if preset is None:
        raise ValueError(f"Unknown Assembly preset: {preset_name}")
    prj = project or find_project(doc)
    alignment_obj = alignment or find_v1_alignment(doc)
    alignment_id = str(getattr(alignment_obj, "AlignmentId", "") or "")
    template_id = str(preset.get("template_id", "") or "template:assembly")
    return AssemblyModel(
        schema_version=1,
        project_id=_project_id(prj),
        assembly_id=str(preset.get("assembly_id", "") or "assembly:main"),
        alignment_id=alignment_id,
        active_template_id=template_id,
        label=str(preset.get("label", "") or str(preset_name or "Assembly")),
        template_rows=[
            SectionTemplate(
                template_id=template_id,
                template_kind="roadway",
                template_index=1,
                label=str(preset.get("template_label", "") or template_id),
                component_rows=_preset_components(preset),
                notes=str(preset.get("note", "") or "Assembly preset; edit before corridor generation."),
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


def show_assembly_preview_object(document, assembly_model: AssemblyModel):
    """Create or update a Front-view Assembly cross-section preview from source rows."""

    if document is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Assembly preview.")
    template = assembly_model.template_rows[0] if list(getattr(assembly_model, "template_rows", []) or []) else None
    if template is None:
        raise ValueError("Assembly preview requires at least one SectionTemplate.")
    points = _assembly_preview_points(template)
    if len(points) < 2:
        raise ValueError("Assembly preview requires at least one enabled component with width.")
    shape = _make_assembly_preview_shape(points, stroke_width=_assembly_preview_stroke_width(points))
    obj = document.getObject("V1AssemblyShowPreview")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1AssemblyShowPreview")
    obj.Label = "Assembly Show Preview"
    obj.Shape = shape
    _set_preview_string_property(obj, "CRRecordKind", "v1_assembly_show_preview")
    _set_preview_string_property(obj, "V1ObjectType", "V1AssemblyShowPreview")
    _set_preview_string_property(obj, "AssemblyId", str(getattr(assembly_model, "assembly_id", "") or ""))
    _set_preview_string_property(obj, "TemplateId", str(getattr(template, "template_id", "") or ""))
    _set_preview_integer_property(obj, "ComponentCount", len([row for row in template.component_rows if row.enabled]))
    _style_assembly_preview_object(obj)
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(find_project(document), obj)
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

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Preset:"))
        self._preset_combo = QtWidgets.QComboBox()
        self._preset_combo.addItems(assembly_preset_names())
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

        self._table = QtWidgets.QTableWidget(0, 10)
        self._table.setHorizontalHeaderLabels(
            ["Component ID", "Kind", "Side", "Width", "Slope", "Thickness", "Material", "Enabled", "Parameters", "Notes"]
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
        edit_row.addStretch(1)
        layout.addLayout(edit_row)

        self._ditch_group = QtWidgets.QGroupBox("Ditch Parameters")
        ditch_layout = QtWidgets.QVBoxLayout(self._ditch_group)
        ditch_hint = QtWidgets.QLabel(
            "Select a ditch row, edit shape parameters, then apply them back to the Parameters column."
        )
        ditch_hint.setWordWrap(True)
        ditch_layout.addWidget(ditch_hint)
        ditch_shape_row = QtWidgets.QHBoxLayout()
        ditch_shape_row.addWidget(QtWidgets.QLabel("Shape:"))
        self._ditch_shape_combo = QtWidgets.QComboBox()
        self._ditch_shape_combo.addItems(list(DITCH_SHAPES))
        self._ditch_shape_combo.currentIndexChanged.connect(self._update_ditch_shape_controls)
        ditch_shape_row.addWidget(self._ditch_shape_combo)
        load_ditch_button = QtWidgets.QPushButton("Load Selected Ditch")
        load_ditch_button.clicked.connect(self._load_ditch_parameters_from_selection)
        ditch_shape_row.addWidget(load_ditch_button)
        default_ditch_button = QtWidgets.QPushButton("Load Shape Defaults")
        default_ditch_button.clicked.connect(self._load_ditch_shape_defaults)
        ditch_shape_row.addWidget(default_ditch_button)
        apply_ditch_button = QtWidgets.QPushButton("Apply Ditch Parameters")
        apply_ditch_button.clicked.connect(self._apply_ditch_parameters_to_selection)
        ditch_shape_row.addWidget(apply_ditch_button)
        ditch_shape_row.addStretch(1)
        ditch_layout.addLayout(ditch_shape_row)
        self._ditch_shape_note = QtWidgets.QLabel("")
        self._ditch_shape_note.setWordWrap(True)
        ditch_layout.addWidget(self._ditch_shape_note)
        self._ditch_shape_diagram = QtWidgets.QLabel("")
        self._ditch_shape_diagram.setWordWrap(False)
        self._ditch_shape_diagram.setStyleSheet(
            "font-family: Consolas, monospace; background: #20242b; color: #dce8f2; padding: 6px;"
        )
        ditch_layout.addWidget(self._ditch_shape_diagram)
        ditch_form = QtWidgets.QGridLayout()
        self._ditch_fields = {}
        self._ditch_field_labels = {}
        for index, (key, label) in enumerate(DITCH_PARAMETER_FIELDS):
            edit = QtWidgets.QLineEdit()
            edit.setPlaceholderText(_ditch_parameter_placeholder(key))
            self._ditch_fields[key] = edit
            label_widget = QtWidgets.QLabel(f"{label}:")
            self._ditch_field_labels[key] = label_widget
            row_index = index // 2
            col_index = (index % 2) * 2
            ditch_form.addWidget(label_widget, row_index, col_index)
            ditch_form.addWidget(edit, row_index, col_index + 1)
        ditch_layout.addLayout(ditch_form)
        layout.addWidget(self._ditch_group)
        self._table.itemSelectionChanged.connect(self._load_ditch_parameters_from_selection)
        self._update_ditch_shape_controls()

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setFixedHeight(70)
        self._status.setPlainText("No assembly source object is selected.")
        layout.addWidget(self._status)

        action_row = QtWidgets.QHBoxLayout()
        validate_button = QtWidgets.QPushButton("Validate")
        validate_button.clicked.connect(self._validate)
        action_row.addWidget(validate_button)
        show_button = QtWidgets.QPushButton("Show")
        show_button.clicked.connect(self._show_current_assembly)
        action_row.addWidget(show_button)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        action_row.addWidget(apply_button)
        action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        action_row.addWidget(close_button)
        layout.addLayout(action_row)
        self._update_preset_note()
        return widget

    def _load_existing_rows(self) -> None:
        model = to_assembly_model(self.assembly_obj)
        if model is None:
            return
        self._replace_model(model)
        self._set_status(f"Loaded {sum(len(t.component_rows) for t in model.template_rows)} component row(s).")

    def _load_selected_preset(self) -> None:
        try:
            preset_name = str(self._preset_combo.currentText() or "Basic Road")
            self._replace_model(assembly_preset_model_from_document(preset_name, document=self.document))
            self._set_status(f"Assembly preset loaded: {preset_name}. Apply when ready.")
        except Exception as exc:
            self._set_status(f"Assembly preset was not loaded:\n{exc}")

    def _update_preset_note(self) -> None:
        if not hasattr(self, "_preset_note"):
            return
        preset = ASSEMBLY_PRESETS.get(str(self._preset_combo.currentText() or ""), {})
        self._preset_note.setText(str(preset.get("note", "") or ""))

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
            _join_parameters(row.parameters),
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

    def _load_ditch_parameters_from_selection(self) -> None:
        row_index = self._selected_row_index()
        if row_index < 0 or not hasattr(self, "_ditch_fields"):
            return
        if _item_text(self._table, row_index, 1) != "ditch":
            self._clear_ditch_parameter_fields()
            return
        params = _split_parameters(_item_text(self._table, row_index, 8))
        shape = str(params.get("shape", "") or "trapezoid").strip().lower().replace("-", "_")
        self._ditch_shape_combo.setCurrentText(shape if shape in DITCH_SHAPES else "trapezoid")
        for key, _label in DITCH_PARAMETER_FIELDS:
            self._ditch_fields[key].setText(str(params.get(key, "") or ""))
        self._update_ditch_shape_controls()

    def _update_ditch_shape_controls(self, *_args) -> None:
        if not hasattr(self, "_ditch_fields"):
            return
        shape = str(self._ditch_shape_combo.currentText() or "trapezoid").strip().lower().replace("-", "_")
        material = self._selected_ditch_material()
        visible_keys = set(_ditch_effective_field_keys(shape, material))
        for key, field in self._ditch_fields.items():
            visible = key in visible_keys
            field.setVisible(visible)
            label = self._ditch_field_labels.get(key)
            if label is not None:
                label.setVisible(visible)
        if hasattr(self, "_ditch_shape_note"):
            self._ditch_shape_note.setText(
                _ditch_shape_note(shape) + "\n" + _ditch_material_note(material, shape)
            )
        if hasattr(self, "_ditch_shape_diagram"):
            self._ditch_shape_diagram.setText(_ditch_shape_diagram(shape))

    def _load_ditch_shape_defaults(self) -> None:
        if not hasattr(self, "_ditch_fields"):
            return
        shape = str(self._ditch_shape_combo.currentText() or "trapezoid").strip().lower().replace("-", "_")
        for field in self._ditch_fields.values():
            field.clear()
        for key, value in _ditch_shape_defaults(shape).items():
            if key in self._ditch_fields:
                self._ditch_fields[key].setText(str(value))
        self._update_ditch_shape_controls()
        self._set_status(f"Loaded {shape} ditch defaults. Apply them to the selected ditch row when ready.")

    def _apply_ditch_parameters_to_selection(self) -> None:
        row_index = self._selected_row_index()
        if row_index < 0:
            self._set_status("Select a ditch component row before applying ditch parameters.")
            return
        if _item_text(self._table, row_index, 1) != "ditch":
            self._set_status("Selected component is not a ditch. Change Kind to ditch first.")
            return
        existing = _split_parameters(_item_text(self._table, row_index, 8))
        params = _merge_ditch_parameters(existing, self._ditch_editor_parameters())
        item = self._table.item(row_index, 8)
        if item is None:
            item = QtWidgets.QTableWidgetItem("")
            self._table.setItem(row_index, 8, item)
        item.setText(_join_parameters(params))
        try:
            messages = _validate_assembly_model(self._model_from_table())
        except Exception as exc:
            self._set_status(f"Ditch parameters were applied, but validation failed:\n{exc}")
            return
        self._set_status(
            "Ditch parameters applied to the selected row.\n"
            + ("\n".join(messages) if messages else "Validation status: ok")
        )

    def _ditch_editor_parameters(self) -> dict[str, str]:
        shape = str(self._ditch_shape_combo.currentText() or "trapezoid")
        params = {"shape": shape}
        for key in _ditch_effective_field_keys(shape, self._selected_ditch_material()):
            value = str(self._ditch_fields[key].text() or "").strip()
            if value:
                params[key] = value
        return params

    def _clear_ditch_parameter_fields(self) -> None:
        self._ditch_shape_combo.setCurrentText("trapezoid")
        for field in self._ditch_fields.values():
            field.clear()
        self._update_ditch_shape_controls()

    def _selected_row_index(self) -> int:
        rows = sorted({item.row() for item in list(self._table.selectedItems() or [])})
        if rows:
            return rows[0]
        return int(self._table.currentRow())

    def _selected_ditch_material(self) -> str:
        row_index = self._selected_row_index()
        if row_index >= 0 and _item_text(self._table, row_index, 1) == "ditch":
            return _item_text(self._table, row_index, 6)
        return ""

    def _validate(self) -> None:
        try:
            model = self._model_from_table()
            messages = _validate_assembly_model(model)
            self._set_status("\n".join(messages) if messages else "Validation status: ok")
        except Exception as exc:
            self._set_status(f"Assembly validation failed:\n{exc}")

    def _show_current_assembly(self) -> None:
        try:
            model = self._model_from_table()
            messages = _validate_assembly_model(model)
            if any(message.startswith("ERROR") for message in messages):
                self._set_status("\n".join(messages))
                _show_message(self.form, "Assembly", "Assembly preview was not shown because validation has errors.")
                return
            preview = show_assembly_preview_object(self.document, model)
            try:
                self.document.recompute()
            except Exception:
                pass
            if Gui is not None:
                try:
                    Gui.Selection.clearSelection()
                    Gui.Selection.addSelection(preview)
                except Exception:
                    pass
                _show_front_fit_selection()
            self._set_status(
                ("\n".join(messages) if messages else "Validation status: ok")
                + f"\n\nAssembly preview shown: {preview.Label}"
            )
        except Exception as exc:
            self._set_status(f"Assembly preview was not shown:\n{exc}")
            _show_message(self.form, "Assembly", f"Assembly preview was not shown.\n{exc}")

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
                    parameters=_split_parameters(_item_text(self._table, row_index, 8)),
                    notes=_item_text(self._table, row_index, 9),
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
            for message in ditch_component_validation_messages(component):
                messages.append(f"WARN: {message}")
    if not messages:
        messages.append("Validation status: ok")
    return messages


def _preset_components(preset: dict) -> list[TemplateComponent]:
    rows = []
    for index, row in enumerate(list(preset.get("components", []) or []), start=1):
        component_id, kind, side, width, slope, thickness, material, notes = row[:8]
        parameters = row[8] if len(row) > 8 else {}
        rows.append(
            TemplateComponent(
                component_id=str(component_id),
                kind=str(kind),
                component_index=index,
                side=str(side),
                width=float(width),
                slope=float(slope),
                thickness=float(thickness),
                material=str(material),
                parameters=dict(parameters or {}),
                notes=str(notes),
            )
        )
    return rows


def _assembly_preview_points(template: SectionTemplate):
    center_width = sum(
        max(float(getattr(component, "width", 0.0) or 0.0), 0.0)
        for component in list(getattr(template, "component_rows", []) or [])
        if bool(getattr(component, "enabled", True)) and str(getattr(component, "side", "") or "") == "center"
    )
    center_left = -center_width * 0.5
    center_right = center_width * 0.5
    left_points = _assembly_side_points(template, side="left", start_x=center_left, direction=-1.0)
    right_points = _assembly_side_points(template, side="right", start_x=center_right, direction=1.0)
    points = list(reversed(left_points))
    if center_width > 1.0e-9:
        points.append(App.Vector(center_right, 0.0, 0.0))
    points.extend(right_points[1:])
    return _unique_preview_points(points)


def _assembly_side_points(template: SectionTemplate, *, side: str, start_x: float, direction: float):
    x = float(start_x)
    z = 0.0
    points = [App.Vector(x, 0.0, z)]
    for component in list(getattr(template, "component_rows", []) or []):
        if not bool(getattr(component, "enabled", True)):
            continue
        component_side = str(getattr(component, "side", "") or "center")
        if component_side not in {side, "both"}:
            continue
        if str(getattr(component, "kind", "") or "") == "ditch":
            x, z = _append_ditch_preview_points(points, component, base_x=x, base_z=z, direction=direction)
            continue
        width = max(float(getattr(component, "width", 0.0) or 0.0), 0.0)
        if width <= 1.0e-9:
            continue
        slope = float(getattr(component, "slope", 0.0) or 0.0)
        x += float(direction) * width
        z += slope * width
        points.append(App.Vector(x, 0.0, z))
    return points


def _append_ditch_preview_points(points, component, *, base_x: float, base_z: float, direction: float) -> tuple[float, float]:
    profile = ditch_component_local_profile(component)
    if not profile:
        return float(base_x), float(base_z)
    last_x = float(base_x)
    last_z = float(base_z)
    for local_offset, z_delta, _role in profile[1:]:
        last_x = float(base_x) + float(direction) * float(local_offset)
        last_z = float(base_z) + float(z_delta)
        points.append(App.Vector(last_x, 0.0, last_z))
    return last_x, last_z


def _unique_preview_points(points):
    output = []
    for point in list(points or []):
        if output and _same_preview_point(output[-1], point):
            continue
        output.append(point)
    return output


def _same_preview_point(left, right, tolerance: float = 1.0e-7) -> bool:
    try:
        return (
            abs(float(left.x) - float(right.x)) <= tolerance
            and abs(float(left.y) - float(right.y)) <= tolerance
            and abs(float(left.z) - float(right.z)) <= tolerance
        )
    except Exception:
        return False


def _make_assembly_preview_shape(points, *, stroke_width: float):
    shapes = []
    for start, end in zip(points, points[1:]):
        try:
            if (end - start).Length <= 1.0e-9:
                continue
            stroke = _make_assembly_segment_stroke(start, end, stroke_width)
            shapes.append(stroke if stroke is not None else Part.makeLine(start, end))
        except Exception:
            pass
    return Part.Compound(shapes) if shapes else Part.Shape()


def _make_assembly_segment_stroke(start, end, stroke_width: float):
    width = float(stroke_width or 0.0)
    if width <= 0.0 or Part is None:
        return None
    try:
        dx = float(end.x) - float(start.x)
        dz = float(end.z) - float(start.z)
        length = (dx * dx + dz * dz) ** 0.5
        if length <= 1.0e-9:
            return None
        half = width * 0.5
        nx = -dz / length * half
        nz = dx / length * half
        points = [
            App.Vector(float(start.x) + nx, float(start.y), float(start.z) + nz),
            App.Vector(float(end.x) + nx, float(end.y), float(end.z) + nz),
            App.Vector(float(end.x) - nx, float(end.y), float(end.z) - nz),
            App.Vector(float(start.x) - nx, float(start.y), float(start.z) - nz),
            App.Vector(float(start.x) + nx, float(start.y), float(start.z) + nz),
        ]
        face = Part.Face(Part.makePolygon(points))
        return face.extrude(App.Vector(0.0, -max(0.05, width * 0.25), 0.0))
    except Exception:
        return None


def _assembly_preview_stroke_width(points) -> float:
    if not points:
        return 0.08
    min_x = min(float(point.x) for point in points)
    max_x = max(float(point.x) for point in points)
    min_z = min(float(point.z) for point in points)
    max_z = max(float(point.z) for point in points)
    span = max(max_x - min_x, max_z - min_z, 1.0)
    return max(0.05, min(0.25, span * 0.012))


def _style_assembly_preview_object(obj) -> None:
    vobj = getattr(obj, "ViewObject", None)
    if vobj is None:
        return
    try:
        vobj.Visibility = True
        vobj.DisplayMode = "Flat Lines"
        vobj.ShapeColor = (1.0, 0.62, 0.12)
        vobj.LineColor = (1.0, 0.62, 0.12)
        vobj.PointColor = (1.0, 0.62, 0.12)
        vobj.LineWidth = 6.0
        vobj.PointSize = 8.0
        if hasattr(vobj, "DrawStyle"):
            vobj.DrawStyle = "Solid"
        if hasattr(vobj, "Lighting"):
            try:
                vobj.Lighting = "Two side"
            except Exception:
                pass
        if hasattr(vobj, "Transparency"):
            vobj.Transparency = 0
    except Exception:
        pass


def _set_preview_string_property(obj, name: str, value: str) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyString", name, "CorridorRoad", name)
        setattr(obj, name, str(value or ""))
    except Exception:
        pass


def _set_preview_integer_property(obj, name: str, value: int) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyInteger", name, "CorridorRoad", name)
        setattr(obj, name, int(value or 0))
    except Exception:
        pass


def _show_front_fit_selection() -> None:
    if Gui is None:
        return
    try:
        if hasattr(Gui, "updateGui"):
            Gui.updateGui()
    except Exception:
        pass
    try:
        view = Gui.ActiveDocument.ActiveView
        if hasattr(view, "viewFront"):
            view.viewFront()
        else:
            Gui.SendMsgToActiveView("ViewFront")
    except Exception:
        try:
            Gui.SendMsgToActiveView("ViewFront")
        except Exception:
            pass
    try:
        if hasattr(Gui, "updateGui"):
            Gui.updateGui()
        view = Gui.ActiveDocument.ActiveView
        if hasattr(view, "fitSelection"):
            view.fitSelection()
        else:
            Gui.SendMsgToActiveView("ViewSelection")
    except Exception:
        try:
            Gui.SendMsgToActiveView("ViewSelection")
        except Exception:
            try:
                Gui.SendMsgToActiveView("ViewFit")
            except Exception:
                pass


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


def _join_parameters(parameters: dict[str, object]) -> str:
    return ";".join(f"{key}={value}" for key, value in sorted(dict(parameters or {}).items()) if str(key).strip())


def _merge_ditch_parameters(existing: dict[str, object], edited: dict[str, object]) -> dict[str, object]:
    output = {
        str(key): value
        for key, value in dict(existing or {}).items()
        if str(key).strip() and str(key).strip() not in DITCH_PARAMETER_KEYS
    }
    for key in DITCH_PARAMETER_KEYS:
        value = edited.get(key, "")
        if str(value).strip():
            output[key] = str(value).strip()
    return output


def _ditch_visible_field_keys(shape: str) -> tuple[str, ...]:
    key = str(shape or "trapezoid").strip().lower().replace("-", "_")
    return tuple(DITCH_SHAPE_FIELDS.get(key, DITCH_SHAPE_FIELDS["trapezoid"]))


def _ditch_effective_field_keys(shape: str, material: object = "") -> tuple[str, ...]:
    keys = list(_ditch_visible_field_keys(shape))
    policy = ditch_material_policy(material)
    additions: list[str] = []
    if policy == "lined":
        additions.append("lining_thickness")
    if policy == "structural" and str(shape or "").strip().lower().replace("-", "_") in {"u", "l", "rectangular"}:
        additions.extend(["wall_thickness", "lining_thickness"])
    for key in additions:
        if key not in keys:
            keys.append(key)
    return tuple(key for key, _label in DITCH_PARAMETER_FIELDS if key in set(keys))


def _ditch_shape_defaults(shape: str) -> dict[str, str]:
    key = str(shape or "trapezoid").strip().lower().replace("-", "_")
    return dict(DITCH_SHAPE_DEFAULTS.get(key, DITCH_SHAPE_DEFAULTS["trapezoid"]))


def _split_parameters(value: object) -> dict[str, str]:
    output: dict[str, str] = {}
    for token in str(value or "").split(";"):
        if "=" not in token:
            continue
        key, raw = token.split("=", 1)
        key = key.strip()
        if key:
            output[key] = raw.strip()
    return output


def _ditch_shape_note(shape: str) -> str:
    return {
        "trapezoid": "Trapezoid uses depth, bottom width, and side-slope runs to form an earth ditch.",
        "u": "U shape is represented as a rectangular lined channel approximation for this first slice.",
        "l": "L shape uses one wall side plus an open bottom/run side. wall_side should be inner or outer.",
        "rectangular": "Rectangular uses vertical sides and bottom width; wall and lining thickness are metadata for now.",
        "v": "V shape uses top width, depth, and invert offset. Leave invert offset centered for a symmetric V.",
        "custom_polyline": "Custom polyline uses section_points as offset,z,role tokens separated by semicolons.",
    }.get(str(shape or "").strip().lower().replace("-", "_"), "")


def _ditch_material_note(material: object, shape: str) -> str:
    policy = ditch_material_policy(material)
    if policy == "structural":
        if str(shape or "").strip().lower().replace("-", "_") in {"u", "l", "rectangular"}:
            return "Material policy: structural. wall_thickness is required for future solid/component-body handoff."
        return "Material policy: structural. Consider a U/L/rectangular shape when a physical channel body is intended."
    if policy == "lined":
        return "Material policy: lined surface. lining_thickness should be defined for quantity and review."
    if policy == "earth":
        return "Material policy: earth grading. This should normally remain a drainage_surface output."
    if policy == "unspecified":
        return "Material policy: unspecified. Use material such as earth, concrete, precast, riprap, or grass."
    return "Material policy: general. Add explicit material if this ditch needs quantity or structure handoff."


def _ditch_shape_diagram(shape: str) -> str:
    return {
        "trapezoid": (
            "inner edge           outer edge\n"
            "    \\               /\n"
            "     \\__ bottom ___/\n"
            "       depth"
        ),
        "u": (
            "wall              wall\n"
            " |                |\n"
            " |____ bottom ____|\n"
            "       depth"
        ),
        "l": (
            "wall side\n"
            " |____ bottom ____\\\n"
            " |                 \\\n"
            "       open side"
        ),
        "rectangular": (
            "vertical side   vertical side\n"
            " |              |\n"
            " |___ bottom ___|\n"
            "       depth"
        ),
        "v": (
            "inner edge       outer edge\n"
            "    \\           /\n"
            "     \\ invert /\n"
            "       depth"
        ),
        "custom_polyline": (
            "section_points:\n"
            "  offset,z,role; offset,z,role\n"
            "  0,0,edge; 0.5,-0.4,invert; 1,0,edge"
        ),
    }.get(str(shape or "").strip().lower().replace("-", "_"), "")


def _ditch_parameter_placeholder(key: str) -> str:
    return {
        "top_width": "e.g. 2.000",
        "bottom_width": "e.g. 0.600",
        "depth": "e.g. 0.450",
        "inner_slope": "run per depth, e.g. 1.5",
        "outer_slope": "run per depth, e.g. 2.0",
        "invert_offset": "V-shape invert offset",
        "wall_thickness": "concrete wall thickness",
        "lining_thickness": "lining thickness",
        "wall_side": "inner or outer",
        "section_points": "0,0,edge;0.5,-0.4,invert",
    }.get(str(key), "")


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditAssembly", CmdV1AssemblyEditor())
