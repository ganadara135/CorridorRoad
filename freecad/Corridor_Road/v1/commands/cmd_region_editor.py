"""Region editor command for CorridorRoad v1."""

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
from ..models.source.region_model import REGION_PRIMARY_KINDS, RegionModel, RegionRow
from ..objects.obj_alignment import find_v1_alignment
from ..objects.obj_assembly import assembly_model_ids, list_v1_assembly_models, to_assembly_model
from ..objects.obj_region import (
    create_or_update_v1_region_model_object,
    find_v1_region_model,
    to_region_model,
)
from ..objects.obj_stationing import find_v1_stationing
from ..objects.obj_structure import find_v1_structure_model, to_structure_model
from ..services.evaluation.region_resolution_service import RegionValidationService


REGION_KIND_CHOICES = list(REGION_PRIMARY_KINDS)


REGION_PRESETS = {
    "Basic Road": {
        "note": "Single normal-road region across the available station range.",
        "rows": [
            {
                "id": "region:normal-01",
                "kind": "normal_road",
                "start": 0.0,
                "end": 1.0,
                "layers": [],
                "structures": [],
                "drainage": [],
                "priority": 10,
                "notes": "Preset normal road region.",
            }
        ],
    },
    "Bridge Segment": {
        "note": "Normal approach regions with one bridge work zone in the middle.",
        "rows": [
            {
                "id": "region:normal-before",
                "kind": "normal_road",
                "start": 0.0,
                "end": 0.35,
                "layers": [],
                "structures": [],
                "drainage": [],
                "priority": 10,
                "notes": "Approach road before bridge.",
            },
            {
                "id": "region:bridge-01",
                "kind": "bridge",
                "start": 0.35,
                "end": 0.65,
                "layers": ["drainage"],
                "structures": ["structure:bridge-01"],
                "drainage": ["drainage:deck-drain"],
                "priority": 80,
                "notes": "Bridge region with deck drainage layer.",
            },
            {
                "id": "region:normal-after",
                "kind": "normal_road",
                "start": 0.65,
                "end": 1.0,
                "layers": [],
                "structures": [],
                "drainage": [],
                "priority": 10,
                "notes": "Approach road after bridge.",
            },
        ],
    },
    "Intersection Zone": {
        "note": "Normal road with a central intersection control zone and drainage layer.",
        "rows": [
            {
                "id": "region:normal-before",
                "kind": "normal_road",
                "start": 0.0,
                "end": 0.40,
                "layers": [],
                "structures": [],
                "drainage": [],
                "priority": 10,
                "notes": "Mainline before intersection.",
            },
            {
                "id": "region:intersection-01",
                "kind": "intersection",
                "start": 0.40,
                "end": 0.60,
                "layers": ["drainage", "widening"],
                "structures": [],
                "drainage": ["drainage:intersection-inlets"],
                "priority": 70,
                "notes": "At-grade intersection influence zone.",
            },
            {
                "id": "region:normal-after",
                "kind": "normal_road",
                "start": 0.60,
                "end": 1.0,
                "layers": [],
                "structures": [],
                "drainage": [],
                "priority": 10,
                "notes": "Mainline after intersection.",
            },
        ],
    },
    "Ramp Tie-In": {
        "note": "Normal road with ramp influence, retaining/drainage layers, and transition zones.",
        "rows": [
            {
                "id": "region:transition-in",
                "kind": "transition",
                "start": 0.0,
                "end": 0.25,
                "layers": ["widening"],
                "structures": [],
                "drainage": [],
                "priority": 30,
                "notes": "Ramp approach transition.",
            },
            {
                "id": "region:ramp-01",
                "kind": "ramp",
                "start": 0.25,
                "end": 0.75,
                "layers": ["drainage", "retaining_wall"],
                "structures": ["structure:retaining-wall-01"],
                "drainage": ["drainage:ramp-ditch"],
                "priority": 75,
                "notes": "Ramp merge/diverge work zone.",
            },
            {
                "id": "region:transition-out",
                "kind": "transition",
                "start": 0.75,
                "end": 1.0,
                "layers": ["widening"],
                "structures": [],
                "drainage": [],
                "priority": 30,
                "notes": "Ramp departure transition.",
            },
        ],
    },
    "Drainage Control": {
        "note": "Normal road split by a drainage-control zone with ditch and culvert references.",
        "rows": [
            {
                "id": "region:normal-before",
                "kind": "normal_road",
                "start": 0.0,
                "end_sta": 100.0,
                "layers": [],
                "structures": [],
                "drainage": [],
                "priority": 10,
                "notes": "Normal road before drainage control.",
            },
            {
                "id": "region:drainage-01",
                "kind": "drainage",
                "start_sta": 100.0,
                "end": 1.0,
                "layers": ["ditch", "culvert"],
                "structures": ["structure:culvert-01"],
                "drainage": ["drainage:side-ditch-left", "drainage:culvert-01"],
                "priority": 65,
                "notes": "Drainage and culvert control region.",
            },
            {
                "id": "region:normal-after",
                "kind": "normal_road",
                "start": 1.0,
                "end": 1.0,
                "layers": [],
                "structures": [],
                "drainage": [],
                "priority": 10,
                "notes": "Normal road after drainage control.",
            },
        ],
    },
}


def region_preset_names() -> list[str]:
    """Return available v1 Region preset names."""

    return list(REGION_PRESETS.keys())


def starter_region_model_from_document(document=None, *, project=None, alignment=None) -> RegionModel:
    """Build one non-destructive starter RegionModel from station/alignment extent."""

    return region_preset_model_from_document("Basic Road", document=document, project=project, alignment=alignment)


def region_preset_model_from_document(
    preset_name: str,
    document=None,
    *,
    project=None,
    alignment=None,
) -> RegionModel:
    """Build a non-destructive RegionModel from a named station-range preset."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    preset = REGION_PRESETS.get(str(preset_name or "").strip())
    if preset is None:
        raise ValueError(f"Unknown Region preset: {preset_name}")
    prj = project or find_project(doc)
    alignment_obj = alignment or find_v1_alignment(doc)
    station_start, station_end = _document_station_range(doc, alignment_obj)
    alignment_id = str(getattr(alignment_obj, "AlignmentId", "") or "")
    assembly_ref, template_ref = _preferred_assembly_and_template_refs(doc)
    rows = _preset_region_rows(
        preset,
        station_start=station_start,
        station_end=station_end,
        assembly_ref=assembly_ref,
        template_ref=template_ref,
    )
    return RegionModel(
        schema_version=1,
        project_id=_project_id(prj),
        region_model_id="regions:main",
        alignment_id=alignment_id,
        label="Regions",
        region_rows=rows,
    )


def apply_v1_region_model(
    *,
    document=None,
    project=None,
    region_model: RegionModel,
):
    """Validate and persist a v1 RegionModel source object."""

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
    obj = create_or_update_v1_region_model_object(
        document=doc,
        project=prj,
        region_model=region_model,
    )
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def run_v1_region_editor_command():
    """Open the v1 Region editor panel."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    panel = V1RegionEditorTaskPanel(document=document)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return find_v1_region_model(document)


class V1RegionEditorTaskPanel:
    """Table-based v1 Region source editor."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.region_obj = find_v1_region_model(self.document)
        self._assembly_refs = assembly_model_ids(self.document)
        self._structure_refs = structure_model_ids(self.document)
        self._station_values = _document_station_values(self.document)
        self._station_range = _document_station_range(self.document, find_v1_alignment(self.document))
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
        widget.setWindowTitle("CorridorRoad v1 - Regions")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Regions")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        note = QtWidgets.QLabel(
            "Define station ranges with one primary kind plus optional layers and domain references. "
            "Apply stores source rows only; it does not build corridor geometry."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Preset:"))
        self._preset_combo = QtWidgets.QComboBox()
        self._preset_combo.addItems(region_preset_names())
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

        self._table = QtWidgets.QTableWidget(0, 9)
        self._table.setHorizontalHeaderLabels(
            ["Start STA", "End STA (Auto)", "Primary Kind", "Layers", "Assembly", "Structure", "Drainage", "Priority", "Notes"]
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
        add_button = QtWidgets.QPushButton("Add Region")
        add_button.clicked.connect(self._add_region_row)
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
        self._status.setFixedHeight(90)
        self._status.setPlainText("No region source object is selected.")
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
        self._update_preset_note()
        return widget

    def _load_existing_rows(self) -> None:
        model = to_region_model(self.region_obj)
        if model is None:
            return
        self._replace_rows(model.region_rows)
        self._set_status(f"Loaded {len(model.region_rows)} Region row(s) from {self.region_obj.Label}.")

    def _load_selected_preset(self) -> None:
        try:
            preset_name = str(self._preset_combo.currentText() or "Basic Road")
            model = region_preset_model_from_document(preset_name, document=self.document)
            self._replace_rows(model.region_rows)
            self._set_status(f"Region preset loaded: {preset_name}. Apply when ready.")
        except Exception as exc:
            self._set_status(f"Region preset was not loaded:\n{exc}")

    def _update_preset_note(self) -> None:
        if not hasattr(self, "_preset_note"):
            return
        preset = REGION_PRESETS.get(str(self._preset_combo.currentText() or ""), {})
        self._preset_note.setText(str(preset.get("note", "") or ""))

    def _replace_rows(self, rows: list[RegionRow]) -> None:
        self._table.setRowCount(0)
        for row in rows:
            self._append_row(row)
        self._refresh_derived_end_sta()

    def _append_row(self, row: RegionRow | None = None) -> None:
        row = row or RegionRow(
            region_id=f"region:{self._table.rowCount() + 1}",
            region_index=self._table.rowCount() + 1,
            primary_kind="normal_road",
            station_start=self._default_new_region_start(),
            station_end=float(self._station_range[1]),
            priority=10,
        )
        index = self._table.rowCount()
        self._table.insertRow(index)
        values = [
            _format_float(row.station_start),
            _format_float(row.station_end),
            row.primary_kind,
            _join_refs(row.applied_layers),
            row.assembly_ref,
            str(getattr(row, "structure_ref", "") or ""),
            _join_refs(row.drainage_refs),
            str(int(row.priority)),
            row.notes,
        ]
        for col, value in enumerate(values):
            if col == 0:
                combo = self._station_combo(value)
                try:
                    combo.currentTextChanged.connect(lambda _text: self._refresh_derived_end_sta())
                except Exception:
                    try:
                        combo.currentIndexChanged.connect(lambda _index: self._refresh_derived_end_sta())
                    except Exception:
                        pass
                self._table.setCellWidget(index, col, combo)
            elif col == 1:
                item = QtWidgets.QTableWidgetItem(str(value))
                try:
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                except Exception:
                    pass
                self._table.setItem(index, col, item)
            elif col == 2:
                combo = QtWidgets.QComboBox()
                combo.addItems(REGION_KIND_CHOICES)
                if str(value) in REGION_KIND_CHOICES:
                    combo.setCurrentText(str(value))
                self._table.setCellWidget(index, col, combo)
            elif col == 4:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItem("")
                combo.addItems(self._assembly_refs)
                combo.setCurrentText(str(value or ""))
                self._table.setCellWidget(index, col, combo)
            elif col == 5:
                combo = QtWidgets.QComboBox()
                combo.setEditable(True)
                combo.addItem("")
                combo.addItems(self._structure_refs)
                combo.setCurrentText(str(value or ""))
                self._table.setCellWidget(index, col, combo)
            else:
                self._table.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))
        self._refresh_derived_end_sta()

    def _station_combo(self, value: object):
        combo = QtWidgets.QComboBox()
        combo.setEditable(True)
        try:
            combo.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        except Exception:
            pass
        values = [_format_float(station) for station in list(getattr(self, "_station_values", []) or [])]
        current = _format_float(float(value))
        seen: set[str] = set()
        for text in values + ([current] if current not in values else []):
            if text in seen:
                continue
            seen.add(text)
            combo.addItem(text)
        combo.setCurrentText(current)
        return combo

    def _add_region_row(self) -> None:
        self._append_row()
        self._set_status("Added a Region row. Edit Start STA, then Validate or Apply. End STA is derived from the next row.")

    def _delete_selected_rows(self) -> None:
        rows = sorted({item.row() for item in list(self._table.selectedItems() or [])}, reverse=True)
        if not rows and self._table.currentRow() >= 0:
            rows = [self._table.currentRow()]
        for row_index in rows:
            self._table.removeRow(row_index)
        self._refresh_derived_end_sta()
        self._set_status(f"Deleted {len(rows)} Region row(s).")

    def _sort_rows(self) -> None:
        try:
            rows = self._table_rows(sort_by_start=True)
            self._replace_rows(rows)
            self._set_status("Region rows sorted by station.")
        except Exception as exc:
            self._set_status(f"Region rows were not sorted:\n{exc}")

    def _validate(self) -> None:
        try:
            model = self._model_from_table()
            station_errors = _region_station_membership_errors(model, self._station_values)
            result = RegionValidationService().validate(
                model,
                known_assembly_refs=self._assembly_refs,
                known_structure_refs=self._structure_refs,
            )
            self._set_status(
                _format_validation_result(result, model, self._assembly_refs, self._structure_refs, station_errors=station_errors)
            )
        except Exception as exc:
            self._set_status(f"Region validation failed:\n{exc}")

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            model = self._model_from_table()
            station_errors = _region_station_membership_errors(model, self._station_values)
            result = RegionValidationService().validate(
                model,
                known_assembly_refs=self._assembly_refs,
                known_structure_refs=self._structure_refs,
            )
            if result.status == "error" or station_errors:
                self._set_status(
                    _format_validation_result(result, model, self._assembly_refs, self._structure_refs, station_errors=station_errors)
                )
                _show_message(self.form, "Regions", "Regions were not applied because validation has errors.")
                return False
            self.region_obj = apply_v1_region_model(document=self.document, region_model=model)
            self._set_status(
                _format_validation_result(result, model, self._assembly_refs, self._structure_refs, station_errors=station_errors)
                + f"\n\nApplied to: {self.region_obj.Label}"
            )
            _show_message(self.form, "Regions", f"Regions have been applied.\nRows: {len(model.region_rows)}")
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_status(f"Regions were not applied:\n{exc}")
            _show_message(self.form, "Regions", f"Regions were not applied.\n{exc}")
            return False

    def _model_from_table(self) -> RegionModel:
        existing = to_region_model(self.region_obj)
        alignment = find_v1_alignment(self.document)
        return RegionModel(
            schema_version=1,
            project_id=_project_id(find_project(self.document)),
            region_model_id=str(getattr(existing, "region_model_id", "") or "regions:main"),
            alignment_id=str(getattr(existing, "alignment_id", "") or getattr(alignment, "AlignmentId", "") or ""),
            label="Regions",
            region_rows=self._table_rows(),
        )

    def _table_rows(self) -> list[RegionRow]:
        return self._table_rows_from_specs(sort_by_start=False)

    def _table_rows_from_specs(self, *, sort_by_start: bool = False) -> list[RegionRow]:
        specs: list[dict[str, object]] = []
        rows: list[RegionRow] = []
        for row_index in range(self._table.rowCount()):
            station_start = _required_float(_item_text(self._table, row_index, 0), f"Row {row_index + 1} start STA")
            primary_kind = _item_text(self._table, row_index, 2) or "normal_road"
            layers = _split_refs(_item_text(self._table, row_index, 3))
            assembly_ref = _item_text(self._table, row_index, 4)
            structure_ref = _item_text(self._table, row_index, 5)
            drainage_refs = _split_refs(_item_text(self._table, row_index, 6))
            priority = int(_required_float(_item_text(self._table, row_index, 7) or "10", f"Row {row_index + 1} priority"))
            notes = _item_text(self._table, row_index, 8)
            specs.append(
                {
                    "station_start": station_start,
                    "primary_kind": primary_kind,
                    "layers": layers,
                    "assembly_ref": assembly_ref,
                    "structure_ref": structure_ref,
                    "drainage_refs": drainage_refs,
                    "priority": priority,
                    "notes": notes,
                }
            )
        if sort_by_start:
            specs = sorted(specs, key=lambda row: (float(row["station_start"]), str(row.get("primary_kind", ""))))
        for row_index, spec in enumerate(specs):
            station_start = float(spec["station_start"])
            station_end = float(specs[row_index + 1]["station_start"]) if row_index < len(specs) - 1 else float(self._station_range[1])
            rows.append(
                RegionRow(
                    region_id=f"region:{row_index + 1}",
                    region_index=row_index + 1,
                    primary_kind=str(spec["primary_kind"]),
                    applied_layers=list(spec["layers"]),
                    station_start=station_start,
                    station_end=station_end,
                    assembly_ref=str(spec["assembly_ref"]),
                    structure_ref=str(spec["structure_ref"]),
                    drainage_refs=list(spec["drainage_refs"]),
                    priority=int(spec["priority"]),
                    notes=str(spec["notes"]),
                )
            )
        return rows

    def _default_new_region_start(self) -> float:
        starts: list[float] = []
        for row_index in range(self._table.rowCount()):
            try:
                starts.append(_required_float(_item_text(self._table, row_index, 0), "Start STA"))
            except Exception:
                continue
        available = [value for value in self._station_values if round(float(value), 6) not in {round(start, 6) for start in starts}]
        if available:
            return float(available[0])
        return float(self._station_range[0])

    def _refresh_derived_end_sta(self) -> None:
        if not hasattr(self, "_table"):
            return
        for row_index in range(self._table.rowCount()):
            try:
                end = _required_float(_item_text(self._table, row_index + 1, 0), "Next Start STA") if row_index < self._table.rowCount() - 1 else float(self._station_range[1])
                item = self._table.item(row_index, 1)
                if item is None:
                    item = QtWidgets.QTableWidgetItem("")
                    try:
                        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                    except Exception:
                        pass
                    self._table.setItem(row_index, 1, item)
                item.setText(_format_float(end))
            except Exception:
                item = self._table.item(row_index, 1)
                if item is not None:
                    item.setText("")

    def _set_status(self, text: str) -> None:
        self._status.setPlainText(str(text or ""))


class CmdV1RegionEditor:
    """Open the v1 Region source editor."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("edit_regions.svg"),
            "MenuText": "Regions",
            "ToolTip": "Define v1 corridor regions by station range, primary kind, layers, and references",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_region_editor_command()


def _document_station_range(document, alignment_obj=None) -> tuple[float, float]:
    values = _document_station_values(document)
    if values:
        return min(values), max(values)
    try:
        total_length = float(getattr(alignment_obj, "TotalLength", 0.0) or 0.0)
        if total_length > 0.0:
            return 0.0, total_length
    except Exception:
        pass
    return 0.0, 100.0


def _document_station_values(document) -> list[float]:
    stationing = find_v1_stationing(document)
    stations = list(getattr(stationing, "StationValues", []) or []) if stationing is not None else []
    values: dict[float, float] = {}
    for station in stations:
        try:
            value = float(station)
        except Exception:
            continue
        values[round(value, 6)] = value
    return [values[key] for key in sorted(values)]


def _region_station_membership_errors(region_model: RegionModel, station_values: list[float]) -> list[str]:
    known = {round(float(value), 6) for value in list(station_values or [])}
    if not known:
        return ["Stationing has no station values; Region Start STA and End STA cannot be checked."]
    errors: list[str] = []
    rows = list(getattr(region_model, "region_rows", []) or [])
    if rows:
        station_min = min(float(value) for value in list(station_values or []))
        station_max = max(float(value) for value in list(station_values or []))
        first_start = float(getattr(rows[0], "station_start", 0.0) or 0.0)
        last_end = float(getattr(rows[-1], "station_end", 0.0) or 0.0)
        if round(first_start, 6) != round(station_min, 6):
            errors.append(f"First Region Start STA must be the first Stationing value {station_min:.3f}.")
        if round(last_end, 6) != round(station_max, 6):
            errors.append(f"Last Region End STA must resolve to the last Stationing value {station_max:.3f}.")
    previous_start: float | None = None
    for row in rows:
        region_id = str(getattr(row, "region_id", "") or "")
        for attr, label in (("station_start", "Start STA"), ("station_end", "End STA")):
            try:
                station = float(getattr(row, attr, 0.0) or 0.0)
            except Exception:
                errors.append(f"{region_id} {label} is not numeric.")
                continue
            if round(station, 6) not in known:
                errors.append(f"{region_id} {label} {station:.3f} is not in Stationing.")
        current_start = float(getattr(row, "station_start", 0.0) or 0.0)
        if previous_start is not None and current_start <= previous_start + 1.0e-9:
            errors.append(f"{region_id} Start STA must be greater than the previous Region Start STA.")
        previous_start = current_start
    return errors


def region_assembly_reference_warnings(region_model: RegionModel, assembly_refs: list[str]) -> list[str]:
    """Return Region editor warnings for Assembly refs that do not exist yet."""

    known = {str(value).strip() for value in list(assembly_refs or []) if str(value).strip()}
    warnings: list[str] = []
    for row in list(getattr(region_model, "region_rows", []) or []):
        assembly_ref = str(getattr(row, "assembly_ref", "") or "").strip()
        if assembly_ref and assembly_ref not in known:
            warnings.append(f"WARNING: {row.region_id} references missing assembly_ref {assembly_ref}.")
    return warnings


def structure_model_ids(document) -> list[str]:
    """Return v1 Structure ids available for Region structure_ref selection."""

    structure_obj = find_v1_structure_model(document)
    model = to_structure_model(structure_obj)
    if model is None:
        return []
    output: list[str] = []
    seen: set[str] = set()
    for row in list(getattr(model, "structure_rows", []) or []):
        structure_id = str(getattr(row, "structure_id", "") or "").strip()
        if not structure_id or structure_id in seen:
            continue
        seen.add(structure_id)
        output.append(structure_id)
    return output


def region_structure_reference_warnings(region_model: RegionModel, structure_refs: list[str]) -> list[str]:
    """Return Region editor warnings for Structure refs that do not exist yet."""

    known = {str(value).strip() for value in list(structure_refs or []) if str(value).strip()}
    warnings: list[str] = []
    for row in list(getattr(region_model, "region_rows", []) or []):
        structure_ref = str(getattr(row, "structure_ref", "") or "").strip()
        if structure_ref and structure_ref not in known:
            warnings.append(f"WARNING: {row.region_id} references missing structure_ref {structure_ref}.")
    return warnings


def _preset_region_rows(
    preset: dict,
    *,
    station_start: float,
    station_end: float,
    assembly_ref: str,
    template_ref: str,
) -> list[RegionRow]:
    span = max(float(station_end) - float(station_start), 0.0)
    if span <= 0.0:
        span = 100.0
        station_end = float(station_start) + span
    rows: list[RegionRow] = []
    for index, spec in enumerate(list(preset.get("rows", []) or []), start=1):
        start_sta = _preset_station_value(
            spec,
            ratio_key="start",
            absolute_key="start_sta",
            default_ratio=0.0,
            station_start=station_start,
            station_end=station_end,
            span=span,
        )
        end_sta = _preset_station_value(
            spec,
            ratio_key="end",
            absolute_key="end_sta",
            default_ratio=1.0,
            station_start=station_start,
            station_end=station_end,
            span=span,
        )
        if end_sta < start_sta:
            start_sta, end_sta = end_sta, start_sta
        rows.append(
            RegionRow(
                region_id=str(spec.get("id", "") or f"region:{index}"),
                region_index=index,
                primary_kind=str(spec.get("kind", "") or "normal_road"),
                applied_layers=list(spec.get("layers", []) or []),
                station_start=start_sta,
                station_end=end_sta,
                assembly_ref=str(spec.get("assembly_ref", "") or assembly_ref or ""),
                template_ref=str(spec.get("template_ref", "") or template_ref or ""),
                structure_ref=_first_ref(spec.get("structures", []) or []),
                drainage_refs=list(spec.get("drainage", []) or []),
                priority=int(spec.get("priority", 10) or 10),
                notes=str(spec.get("notes", "") or ""),
            )
        )
    return rows


def _preset_station_value(
    spec: dict,
    *,
    ratio_key: str,
    absolute_key: str,
    default_ratio: float,
    station_start: float,
    station_end: float,
    span: float,
) -> float:
    lower = min(float(station_start), float(station_end))
    upper = max(float(station_start), float(station_end))
    if absolute_key in spec:
        try:
            absolute = float(spec.get(absolute_key))
        except Exception:
            absolute = lower
        return min(max(absolute, lower), upper)
    try:
        raw = float(spec.get(ratio_key, default_ratio))
    except Exception:
        raw = float(default_ratio)
    ratio = max(0.0, min(1.0, raw))
    return float(station_start) + float(span) * ratio


def _format_validation_result(
    result,
    region_model: RegionModel | None = None,
    assembly_refs: list[str] | None = None,
    structure_refs: list[str] | None = None,
    station_errors: list[str] | None = None,
) -> str:
    del region_model, assembly_refs, structure_refs
    station_rows = list(station_errors or [])
    status = "error" if station_rows else (getattr(result, "status", "") or "unknown")
    lines = [f"Validation status: {status}"]
    diagnostics = list(getattr(result, "diagnostic_rows", []) or [])
    if not diagnostics and not station_rows:
        lines.append("No diagnostics.")
    else:
        lines.append("Diagnostics:")
        for message in station_rows:
            lines.append(f"- error: station_not_found: {message}")
        for row in diagnostics:
            lines.append(f"- {row.severity}: {row.kind}: {row.message}")
    return "\n".join(lines)


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


def _split_refs(value: object) -> list[str]:
    return [token.strip() for token in str(value or "").replace(";", ",").split(",") if token.strip()]


def _join_refs(values) -> str:
    return ",".join(str(value).strip() for value in list(values or []) if str(value).strip())


def _first_ref(values) -> str:
    for value in list(values or []):
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _format_float(value: float) -> str:
    return f"{float(value):.3f}"


def _preferred_assembly_and_template_refs(document) -> tuple[str, str]:
    for assembly_obj in list_v1_assembly_models(document):
        model = to_assembly_model(assembly_obj)
        if model is None:
            continue
        assembly_ref = str(getattr(model, "assembly_id", "") or "").strip()
        template_ref = str(getattr(model, "active_template_id", "") or "").strip()
        if assembly_ref:
            return assembly_ref, template_ref
    return "", ""


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditRegions", CmdV1RegionEditor())
