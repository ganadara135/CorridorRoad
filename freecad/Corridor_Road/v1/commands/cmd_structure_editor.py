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
from freecad.Corridor_Road.qt_compat import QtWidgets

from ...objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from ..models.source.structure_model import (
    StructureInfluenceZone,
    StructureInteractionRule,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
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
        self._replace_rows(model.structure_rows)
        self._set_status(f"Loaded {len(model.structure_rows)} Structure row(s) from {self.structure_obj.Label}.")

    def _load_selected_preset(self) -> None:
        try:
            preset_name = str(self._preset_combo.currentText() or "Bridge Segment")
            model = structure_preset_model_from_document(preset_name, document=self.document)
            self._replace_rows(model.structure_rows)
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
                self._table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))

    def _add_structure_row(self) -> None:
        self._append_row()
        self._set_status("Added a Structure row. Edit values, then Validate or Apply.")

    def _delete_selected_rows(self) -> None:
        rows = sorted({item.row() for item in list(self._table.selectedItems() or [])}, reverse=True)
        if not rows and self._table.currentRow() >= 0:
            rows = [self._table.currentRow()]
        for row_index in rows:
            self._table.removeRow(row_index)
        self._set_status(f"Deleted {len(rows)} Structure row(s).")

    def _sort_rows(self) -> None:
        try:
            rows = sorted(self._table_rows(), key=lambda row: (row.placement.station_start, row.placement.station_end, row.structure_id))
            self._replace_rows(rows)
            self._set_status("Structure rows sorted by station.")
        except Exception as exc:
            self._set_status(f"Structure rows were not sorted:\n{exc}")

    def _validate(self) -> None:
        try:
            model = self._model_from_table()
            self._set_status(_format_validation_result(model))
        except Exception as exc:
            self._set_status(f"Structure validation failed:\n{exc}")

    def _apply(self, *, close_after: bool = False, show_preview: bool = True) -> bool:
        try:
            model = self._model_from_table()
            diagnostics = validate_structure_model(model)
            if any(str(row).startswith("error|") for row in diagnostics):
                self._set_status(_format_validation_result(model))
                _show_message(self.form, "Structures", "Structures were not applied because validation has errors.")
                return False
            self.structure_obj = apply_v1_structure_model(document=self.document, structure_model=model)
            preview_text = ""
            if show_preview and list(model.structure_rows or []):
                preview = show_v1_structure_preview_object(self.document, model)
                self._focus_preview_object(preview)
                preview_text = f"\n3D Preview: {preview.Label}"
            self._set_status(_format_validation_result(model) + f"\n\nApplied to: {self.structure_obj.Label}{preview_text}")
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
                self._set_status(_format_validation_result(model))
                return
            preview = show_v1_structure_preview_object(self.document, model)
            self._focus_preview_object(preview)
            self._set_status(_format_validation_result(model) + f"\n\n3D Preview shown: {preview.Label}")
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
        return StructureModel(
            schema_version=1,
            project_id=_project_id(find_project(self.document)),
            structure_model_id=str(getattr(existing, "structure_model_id", "") or "structures:main"),
            alignment_id=str(getattr(existing, "alignment_id", "") or getattr(alignment, "AlignmentId", "") or ""),
            label="Structures",
            structure_rows=self._table_rows(),
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
                    geometry_ref=geometry_ref,
                    reference_mode="native" if not geometry_ref else "source_ref",
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
                geometry_ref=str(spec.get("geometry", "") or ""),
                reference_mode="native",
            )
        )
    return rows


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


def _format_validation_result(structure_model: StructureModel) -> str:
    diagnostics = validate_structure_model(structure_model)
    lines = ["Validation status: " + ("warning" if diagnostics else "ok")]
    if not diagnostics:
        lines.append("No diagnostics.")
    else:
        lines.append("Diagnostics:")
        lines.extend(f"- {row}" for row in diagnostics)
    lines.append(f"Structure rows: {len(list(structure_model.structure_rows or []))}")
    return "\n".join(lines)


def _make_structure_preview_shape(document, structure_model: StructureModel):
    rows = list(getattr(structure_model, "structure_rows", []) or [])
    path = _structure_preview_path_source(document)
    shapes = []
    for row in rows:
        shape = _structure_row_preview_shape(row, path)
        if shape is not None:
            shapes.append(shape)
    if not shapes:
        return Part.Shape()
    return Part.Compound(shapes)


def _structure_row_preview_shape(row: StructureRow, path: dict[str, object]):
    placement = getattr(row, "placement", None)
    if placement is None:
        return None
    start_sta = float(getattr(placement, "station_start", 0.0) or 0.0)
    end_sta = float(getattr(placement, "station_end", start_sta) or start_sta)
    if end_sta < start_sta:
        start_sta, end_sta = end_sta, start_sta
    offset = float(getattr(placement, "offset", 0.0) or 0.0)
    half_width, height = _structure_preview_size(row)
    base_z = _structure_preview_base_z(row)
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


def _structure_preview_size(row: StructureRow) -> tuple[float, float]:
    kind = str(getattr(row, "structure_kind", "") or "").strip().lower()
    if kind == "bridge":
        return 5.0, 1.2
    if kind == "culvert":
        return 1.5, 1.5
    if kind in {"retaining_wall", "wall"}:
        return 0.45, 3.0
    if kind == "utility":
        return 0.75, 0.75
    return 2.0, 1.0


def _structure_preview_base_z(row: StructureRow) -> float:
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


def _format_float(value: float) -> str:
    return f"{float(value):.3f}"


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditStructures", CmdV1StructureEditor())
