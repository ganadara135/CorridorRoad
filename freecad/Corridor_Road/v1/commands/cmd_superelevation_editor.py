"""Superelevation editor command for CorridorRoad v1."""

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
    route_to_v1_tree,
)
from ..models.source.superelevation_model import (
    CrossfallControlRow,
    RunoffTransitionRow,
    SuperelevationConstraint,
    SuperelevationModel,
)
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
from ..objects.obj_profile import find_v1_profile
from ..objects.obj_stationing import find_v1_stationing
from ..objects.obj_superelevation import (
    create_or_update_v1_superelevation_source_object,
    find_v1_superelevation_source,
    to_superelevation_model,
)
from .cmd_centerline3d import build_document_centerline3d_result
from .cmd_alignment_editor import alignment_ip_rows, alignment_pi_review_rows
from ..services.evaluation.centerline3d_frame_service import Centerline3DFrameService
from ..services.evaluation.superelevation_auto_calculation_service import (
    SuperelevationAutoCalculationRequest,
    SuperelevationAutoCalculationService,
    SuperelevationCurveCandidate,
)
from ..services.evaluation.superelevation_service import SuperelevationService
from ..ui.common.styles import apply_clickable_tab_style


SUPERELEVATION_COMMAND_ID = "CorridorRoad_V1EditSuperelevation"


def superelevation_preset_names() -> list[str]:
    """Return available v1 Superelevation preset names.

    Preset data is intentionally removed from Superelevation authoring. Use
    Auto Calculate so Crossfall rows stay traceable to Alignment criteria.
    """

    return []


def starter_superelevation_model_from_document(document=None, *, project=None, alignment=None, profile=None) -> SuperelevationModel:
    """Build an empty starter SuperelevationModel without authoring rows."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    prj = project or find_project(doc)
    alignment_obj = alignment or find_v1_alignment(doc)
    profile_obj = profile or find_v1_profile(doc)
    return SuperelevationModel(
        schema_version=1,
        project_id=_project_id(prj),
        label="Superelevation",
        superelevation_id="superelevation:main",
        alignment_id=str(getattr(alignment_obj, "AlignmentId", "") or ""),
        profile_id=str(getattr(profile_obj, "ProfileId", "") or ""),
        superelevation_kind="roadway_superelevation",
    )


def superelevation_preset_model_from_document(
    preset_name: str,
    document=None,
    *,
    project=None,
    alignment=None,
    profile=None,
) -> SuperelevationModel:
    """Reject legacy Superelevation preset loading.

    Superelevation no longer owns starter preset data. The editor should use
    Auto Calculate from Alignment/Profile context or manual control rows.
    """

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    raise ValueError("Superelevation preset data has been removed. Use Auto Calculate.")


def apply_v1_superelevation_model(*, document=None, project=None, superelevation_model: SuperelevationModel):
    """Validate and persist a v1 SuperelevationModel source object."""

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
    obj = create_or_update_v1_superelevation_source_object(
        document=doc,
        project=prj,
        superelevation_model=superelevation_model,
    )
    validation = SuperelevationService().validate(superelevation_model, station_range=_document_station_range(doc, find_v1_alignment(doc)))
    obj.LastValidationStatus = validation.status
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def run_v1_superelevation_editor_command():
    """Open the v1 Superelevation editor panel."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    panel = V1SuperelevationEditorTaskPanel(document=document)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return find_v1_superelevation_source(document)


def show_v1_superelevation_review_object(
    document=None,
    *,
    superelevation_model: SuperelevationModel | None = None,
    stations: list[float] | None = None,
    bar_width: float = 6.0,
):
    """Create or update a 3D Superelevation review object with station crossfall bars."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Superelevation review.")
    model = superelevation_model
    if model is None:
        model = to_superelevation_model(find_v1_superelevation_source(doc))
    if model is None:
        model = starter_superelevation_model_from_document(doc)
    active_stations = list(stations or _document_station_values(doc) or [])
    if not active_stations:
        start, end = _document_station_range(doc)
        active_stations = [start, (start + end) * 0.5, end] if end > start else [start]
    centerline_result = build_document_centerline3d_result(doc)
    sample_rows = SuperelevationService().sample_stations(model, active_stations)
    frame_service = Centerline3DFrameService()
    applied_sections_by_station = _applied_sections_by_station(doc)
    shapes = []
    station_labels: list[str] = []
    geometry_sources: list[str] = []
    for row in sample_rows:
        frame = frame_service.resolve_station(centerline_result, float(row.station))
        if str(getattr(frame, "status", "") or "") == "blocked":
            continue
        section = _nearest_applied_section(applied_sections_by_station, float(row.station))
        shape = _superelevation_applied_section_shape(section) if section is not None else None
        geometry_source = "applied_sections" if shape is not None else "centerline3d"
        if shape is None:
            shape = _superelevation_crossfall_bar_shape(frame, row, float(bar_width))
        if shape is not None:
            shapes.append(shape)
            station_labels.append(f"{float(row.station):.3f}")
            geometry_sources.append(geometry_source)
    obj = doc.getObject("V1SuperelevationReview")
    if obj is None:
        obj = doc.addObject("Part::Feature", "V1SuperelevationReview")
    obj.Label = "Superelevation Crossfall Review"
    obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else (shapes[0] if shapes else Part.Shape())
    _set_review_string(obj, "CRRecordKind", "v1_superelevation_review")
    _set_review_string(obj, "V1ObjectType", "V1SuperelevationReview")
    _set_review_string(obj, "SuperelevationId", str(getattr(model, "superelevation_id", "") or ""))
    _set_review_string(obj, "GeometrySource", "applied_sections" if "applied_sections" in geometry_sources else "centerline3d")
    _set_review_string_list(obj, "StationLabels", station_labels)
    _set_review_integer(obj, "SampleCount", len(station_labels))
    _set_review_float(obj, "BarWidth", float(bar_width))
    _style_superelevation_review_object(obj)
    try:
        route_to_v1_tree(find_project(doc), obj)
    except Exception:
        pass
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


class V1SuperelevationEditorTaskPanel:
    """Table-based v1 Superelevation source editor."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.superelevation_obj = find_v1_superelevation_source(self.document)
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
        widget.setWindowTitle("Parametric Road v1 - Superelevation")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Superelevation")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        note = QtWidgets.QLabel(
            "Define station-based crossfall controls and transitions. "
            "Assembly keeps default slopes; Superelevation overrides lane/shoulder crossfall by station."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self._tabs = QtWidgets.QTabWidget()
        apply_clickable_tab_style(self._tabs, "SuperelevationEditorTabs")
        self._control_table = self._build_table(["Control ID", "STA", "Side", "Crossfall %", "Kind"], [150, 90, 80, 100, 130])
        self._transition_table = self._build_table(["Transition ID", "Start STA", "End STA", "Kind", "Policy"], [150, 90, 90, 100, 100])
        self._constraint_table = self._build_table(["Constraint ID", "Kind", "Value", "Unit", "Mode"], [150, 180, 90, 80, 80])
        self._sample_table = self._build_table(["STA", "Left %", "Right %", "Transition", "Source"], [90, 90, 90, 140, 220])
        self._tabs.addTab(self._wrap_table(self._control_table, [("Add Control", self._add_control_row), ("Delete Selected", lambda: self._delete_selected(self._control_table))]), "Control Rows")
        self._tabs.addTab(self._wrap_table(self._transition_table, [("Add Transition", self._add_transition_row), ("Delete Selected", lambda: self._delete_selected(self._transition_table))]), "Transitions")
        self._tabs.addTab(self._wrap_table(self._constraint_table, [("Add Constraint", self._add_constraint_row), ("Delete Selected", lambda: self._delete_selected(self._constraint_table))]), "Constraints")
        self._tabs.addTab(self._sample_table, "Review Samples")
        layout.addWidget(self._tabs, 1)

        self._status = QtWidgets.QTextEdit()
        self._status.setReadOnly(True)
        self._status.setMinimumHeight(90)
        layout.addWidget(self._status)

        buttons = QtWidgets.QHBoxLayout()
        auto_button = QtWidgets.QPushButton("Auto Calculate")
        auto_button.clicked.connect(self._auto_calculate)
        validate_button = QtWidgets.QPushButton("Validate")
        validate_button.clicked.connect(self._validate)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        samples_button = QtWidgets.QPushButton("Show Samples")
        samples_button.clicked.connect(self._show_samples)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        for button in (auto_button, validate_button, apply_button, samples_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        return widget

    def _build_table(self, labels: list[str], widths: list[int]):
        table = QtWidgets.QTableWidget(0, len(labels))
        table.setHorizontalHeaderLabels(labels)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.SelectedClicked)
        for index, width in enumerate(widths):
            table.setColumnWidth(index, int(width))
        try:
            table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        return table

    def _wrap_table(self, table, buttons: list[tuple[str, object]]):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(table, 1)
        button_row = QtWidgets.QHBoxLayout()
        for label, callback in buttons:
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(callback)
            button_row.addWidget(button)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        return widget

    def _load_existing_rows(self):
        model = to_superelevation_model(self.superelevation_obj) if self.superelevation_obj is not None else starter_superelevation_model_from_document(self.document)
        self._set_model(model)
        if self.superelevation_obj is None:
            self._set_status("No Superelevation source object is available. Use Auto Calculate or add rows, then Apply.", ok=True)
        else:
            self._set_status("Loaded existing Superelevation source object.", ok=True)

    def _set_model(self, model: SuperelevationModel):
        self._set_control_rows(list(getattr(model, "control_rows", []) or []))
        self._set_transition_rows(list(getattr(model, "transition_rows", []) or []))
        self._set_constraint_rows(list(getattr(model, "constraint_rows", []) or []))
        self._show_samples()

    def _set_control_rows(self, rows: list[CrossfallControlRow]):
        self._control_table.setRowCount(0)
        for row in rows:
            self._add_control_row(
                [
                    row.control_row_id,
                    f"{float(row.station):.3f}",
                    row.side,
                    f"{float(row.crossfall_value):.3f}",
                    row.kind,
                ]
            )

    def _set_transition_rows(self, rows: list[RunoffTransitionRow]):
        self._transition_table.setRowCount(0)
        for row in rows:
            self._add_transition_row(
                [
                    row.transition_id,
                    f"{float(row.station_start):.3f}",
                    f"{float(row.station_end):.3f}",
                    row.kind,
                    row.transition_policy,
                ]
            )

    def _set_constraint_rows(self, rows: list[SuperelevationConstraint]):
        self._constraint_table.setRowCount(0)
        for row in rows:
            self._add_constraint_row(
                [
                    row.constraint_id,
                    row.kind,
                    str(row.value),
                    row.unit,
                    row.hard_or_soft,
                ]
            )

    def _add_control_row(self, values: list[str] | None = None):
        start, _end = self._station_range
        values = values or [f"control:{self._control_table.rowCount() + 1}", f"{start:.3f}", "both", "-2.000", "reference_crossfall"]
        self._append_text_row(self._control_table, values)

    def _add_transition_row(self, values: list[str] | None = None):
        start, end = self._station_range
        values = values or [f"transition:{self._transition_table.rowCount() + 1}", f"{start:.3f}", f"{end:.3f}", "runoff", "linear"]
        self._append_text_row(self._transition_table, values)

    def _add_constraint_row(self, values: list[str] | None = None):
        values = values or [f"constraint:{self._constraint_table.rowCount() + 1}", "max_superelevation_rate", "8.000", "percent", "soft"]
        self._append_text_row(self._constraint_table, values)

    def _append_text_row(self, table, values: list[str]):
        row_index = table.rowCount()
        table.insertRow(row_index)
        for column, value in enumerate(values):
            table.setItem(row_index, column, QtWidgets.QTableWidgetItem(str(value)))
        return row_index

    def _delete_selected(self, table):
        rows = sorted({index.row() for index in table.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            table.removeRow(row)

    def _auto_calculate(self):
        alignment = find_v1_alignment(self.document)
        if alignment is None:
            self._set_status("Auto Calculate requires a V1Alignment source object.", ok=False)
            return None
        try:
            request = _auto_calculation_request_from_document(self.document, alignment)
            result = SuperelevationAutoCalculationService().calculate(request)
            self._set_model(result.superelevation_model)
            diagnostic_text = _format_auto_calculation_diagnostics(result.diagnostic_rows)
            self._set_status(
                "Auto Calculate complete. "
                f"Curves: {len(request.curve_candidates)}; "
                f"Control rows: {len(result.superelevation_model.control_rows)}; "
                f"Transitions: {len(result.superelevation_model.transition_rows)}."
                f"{diagnostic_text}",
                ok=not any(row.severity == "error" for row in result.diagnostic_rows),
            )
            return result
        except Exception as exc:
            self._set_status(f"Auto Calculate failed. {exc}", ok=False)
            return None

    def _model_from_table(self) -> SuperelevationModel:
        base = starter_superelevation_model_from_document(self.document)
        return SuperelevationModel(
            schema_version=1,
            project_id=base.project_id,
            label="Superelevation",
            superelevation_id=base.superelevation_id,
            alignment_id=base.alignment_id,
            profile_id=base.profile_id,
            superelevation_kind=base.superelevation_kind,
            control_rows=self._control_rows(),
            transition_rows=self._transition_rows(),
            constraint_rows=self._constraint_rows(),
        )

    def _control_rows(self) -> list[CrossfallControlRow]:
        rows: list[CrossfallControlRow] = []
        for index in range(self._control_table.rowCount()):
            rows.append(
                CrossfallControlRow(
                    control_row_id=_item_text(self._control_table, index, 0) or f"control:{index + 1}",
                    station=_float_text(_item_text(self._control_table, index, 1), 0.0),
                    side=_item_text(self._control_table, index, 2) or "both",
                    crossfall_value=_float_text(_item_text(self._control_table, index, 3), 0.0),
                    crossfall_unit="percent",
                    kind=_item_text(self._control_table, index, 4) or "reference_crossfall",
                )
            )
        return rows

    def _transition_rows(self) -> list[RunoffTransitionRow]:
        rows: list[RunoffTransitionRow] = []
        for index in range(self._transition_table.rowCount()):
            rows.append(
                RunoffTransitionRow(
                    transition_id=_item_text(self._transition_table, index, 0) or f"transition:{index + 1}",
                    station_start=_float_text(_item_text(self._transition_table, index, 1), 0.0),
                    station_end=_float_text(_item_text(self._transition_table, index, 2), 0.0),
                    kind=_item_text(self._transition_table, index, 3) or "runoff",
                    transition_policy=_item_text(self._transition_table, index, 4) or "linear",
                )
            )
        return rows

    def _constraint_rows(self) -> list[SuperelevationConstraint]:
        rows: list[SuperelevationConstraint] = []
        for index in range(self._constraint_table.rowCount()):
            rows.append(
                SuperelevationConstraint(
                    constraint_id=_item_text(self._constraint_table, index, 0) or f"constraint:{index + 1}",
                    kind=_item_text(self._constraint_table, index, 1),
                    value=_item_text(self._constraint_table, index, 2),
                    unit=_item_text(self._constraint_table, index, 3),
                    hard_or_soft=_item_text(self._constraint_table, index, 4) or "soft",
                )
            )
        return rows

    def _validate(self):
        model = self._model_from_table()
        result = SuperelevationService().validate(model, station_range=self._station_range)
        self._set_status(_format_validation_result(result), ok=result.status != "error")
        return result

    def _apply(self, *, close_after: bool = False):
        result = self._validate()
        if result.status == "error":
            return False
        try:
            self.superelevation_obj = apply_v1_superelevation_model(
                document=self.document,
                superelevation_model=self._model_from_table(),
            )
            self._set_status(f"Applied Superelevation source rows. Validation: {result.status}", ok=True)
            self._show_apply_complete_message(result.status)
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_status(f"Superelevation was not applied. {exc}", ok=False)
            return False

    def _show_samples(self):
        model = self._model_from_table() if hasattr(self, "_control_table") else starter_superelevation_model_from_document(self.document)
        stations = _document_station_values(self.document)
        if not stations:
            start, end = self._station_range
            stations = [start, (start + end) * 0.5, end] if end > start else [start]
        rows = SuperelevationService().sample_stations(model, stations)
        self._sample_table.setRowCount(0)
        for result in rows:
            self._append_text_row(
                self._sample_table,
                [
                    f"{float(result.station):.3f}",
                    f"{float(result.left_crossfall):.3f}",
                    f"{float(result.right_crossfall):.3f}",
                    result.active_transition_id,
                    ",".join(result.active_control_ids),
                ],
            )
        self._tabs.setCurrentIndex(3)
        preview_message = ""
        try:
            obj = show_v1_superelevation_review_object(
                self.document,
                superelevation_model=model,
                stations=stations,
            )
            preview_message = f" 3D preview bars: {int(getattr(obj, 'SampleCount', 0) or 0)}."
        except Exception as exc:
            preview_message = f" 3D preview skipped: {exc}"
        self._set_status(f"Review samples: {len(rows)} station(s).{preview_message}", ok=True)

    def _show_apply_complete_message(self, validation_status: str) -> None:
        try:
            QtWidgets.QMessageBox.information(
                self.form,
                "Superelevation",
                f"Superelevation has been applied successfully.\nValidation: {validation_status}",
            )
        except Exception:
            pass

    def _set_status(self, text: str, *, ok: bool = True):
        self._status.setPlainText(str(text or ""))
        try:
            self._status.setStyleSheet("background-color:#2f3b2f;" if ok else "background-color:#4a3030;")
        except Exception:
            pass


class CmdV1SuperelevationEditor:
    """FreeCAD command wrapper for the v1 Superelevation editor."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("superelevation.svg"),
            "MenuText": "Superelevation",
            "ToolTip": "Edit station-based Superelevation crossfall controls and transitions",
        }

    def Activated(self):
        return run_v1_superelevation_editor_command()

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None


def _superelevation_crossfall_bar_shape(frame, sample_row, bar_width: float):
    if App is None or Part is None:
        return None
    width = max(float(bar_width), 0.5)
    half_width = width * 0.5
    angle = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal = App.Vector(-math.sin(angle), math.cos(angle), 0.0)
    center = App.Vector(float(frame.x), float(frame.y), float(frame.z))
    left_crossfall = float(getattr(sample_row, "left_crossfall", 0.0) or 0.0) / 100.0
    right_crossfall = float(getattr(sample_row, "right_crossfall", 0.0) or 0.0) / 100.0
    left = center + normal * half_width + App.Vector(0.0, 0.0, left_crossfall * half_width)
    right = center - normal * half_width + App.Vector(0.0, 0.0, right_crossfall * half_width)
    vertical = App.Vector(0.0, 0.0, max(0.25, width * 0.04))
    ticks = [
        Part.makePolygon([left - vertical, left + vertical]),
        Part.makePolygon([center - vertical, center + vertical]),
        Part.makePolygon([right - vertical, right + vertical]),
    ]
    return Part.makeCompound([Part.makePolygon([left, center, right]), *ticks])


def _applied_sections_by_station(document) -> dict[float, object]:
    """Return the latest AppliedSection rows keyed by station for Superelevation review alignment."""

    try:
        section_set = to_applied_section_set(find_v1_applied_section_set(document))
    except Exception:
        section_set = None
    output: dict[float, object] = {}
    for section in list(getattr(section_set, "sections", []) or []):
        try:
            output[round(float(getattr(section, "station", 0.0) or 0.0), 6)] = section
        except Exception:
            continue
    return output


def _nearest_applied_section(sections_by_station: dict[float, object], station: float):
    if not sections_by_station:
        return None
    target = round(float(station), 6)
    if target in sections_by_station:
        return sections_by_station[target]
    best_key = min(sections_by_station, key=lambda value: abs(float(value) - float(station)))
    if abs(float(best_key) - float(station)) <= 1.0e-4:
        return sections_by_station[best_key]
    return None


def _superelevation_applied_section_shape(section):
    """Draw Superelevation review from AppliedSection FG points when available."""

    if section is None or App is None or Part is None:
        return None
    rows = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == "fg_surface"
    ]
    if len(rows) < 2:
        return None
    rows.sort(key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))
    points = []
    for point in rows:
        try:
            points.append(App.Vector(float(point.x), float(point.y), float(point.z)))
        except Exception:
            pass
    if len(points) < 2:
        return None
    tick_points = [points[0], _nearest_zero_offset_point(rows, points), points[-1]]
    vertical = App.Vector(0.0, 0.0, 0.35)
    ticks = [Part.makePolygon([point - vertical, point + vertical]) for point in tick_points if point is not None]
    return Part.makeCompound([Part.makePolygon(points), *ticks])


def _nearest_zero_offset_point(rows, points):
    if not rows or not points:
        return None
    index = min(
        range(len(rows)),
        key=lambda row_index: abs(float(getattr(rows[row_index], "lateral_offset", 0.0) or 0.0)),
    )
    return points[index]


def _style_superelevation_review_object(obj) -> None:
    try:
        obj.ViewObject.LineColor = (1.0, 0.78, 0.05)
        obj.ViewObject.PointColor = (1.0, 0.78, 0.05)
        obj.ViewObject.LineWidth = 4.0
        obj.ViewObject.PointSize = 6.0
        obj.ViewObject.Visibility = True
    except Exception:
        pass


def _set_review_string(obj, name: str, value: str) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyString", name, "Superelevation Review", name)
        setattr(obj, name, str(value or ""))
    except Exception:
        pass


def _set_review_string_list(obj, name: str, values: list[str]) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyStringList", name, "Superelevation Review", name)
        setattr(obj, name, [str(value or "") for value in list(values or [])])
    except Exception:
        pass


def _set_review_integer(obj, name: str, value: int) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyInteger", name, "Superelevation Review", name)
        setattr(obj, name, int(value))
    except Exception:
        pass


def _set_review_float(obj, name: str, value: float) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyFloat", name, "Superelevation Review", name)
        setattr(obj, name, float(value))
    except Exception:
        pass


def _format_validation_result(result) -> str:
    lines = [f"Validation: {result.status}", f"Diagnostics: {len(result.diagnostic_rows)}"]
    for row in list(result.diagnostic_rows or []):
        lines.append(f"{row.severity}:{row.kind}: {row.message}")
    return "\n".join(lines)


def _document_station_values(document=None) -> list[float]:
    stationing = find_v1_stationing(document)
    values = [float(value) for value in list(getattr(stationing, "StationValues", []) or [])]
    output: list[float] = []
    seen: set[float] = set()
    for value in sorted(values):
        key = round(value, 9)
        if key not in seen:
            seen.add(key)
            output.append(value)
    return output


def _document_station_range(document=None, alignment=None) -> tuple[float, float]:
    stations = _document_station_values(document)
    if stations:
        return min(stations), max(stations)
    alignment_obj = alignment or find_v1_alignment(document)
    alignment_model = to_alignment_model(alignment_obj) if alignment_obj is not None else None
    sequence = list(getattr(alignment_model, "geometry_sequence", []) or [])
    if sequence:
        starts = [float(getattr(row, "station_start", 0.0) or 0.0) for row in sequence]
        ends = [float(getattr(row, "station_end", 0.0) or 0.0) for row in sequence]
        return min(starts), max(ends)
    return 0.0, 100.0


def _auto_calculation_request_from_document(document, alignment) -> SuperelevationAutoCalculationRequest:
    station_start, station_end = _document_station_range(document, alignment)
    profile = find_v1_profile(document)
    return SuperelevationAutoCalculationRequest(
        project_id=_project_id(find_project(document)),
        alignment_id=str(getattr(alignment, "AlignmentId", "") or ""),
        profile_id=str(getattr(profile, "ProfileId", "") or ""),
        station_start=station_start,
        station_end=station_end,
        design_speed_kph=float(getattr(alignment, "DesignSpeedKph", 60.0) or 60.0),
        max_superelevation_percent=float(getattr(alignment, "SuperelevationPct", 8.0) or 8.0),
        side_friction=float(getattr(alignment, "SideFriction", 0.15) or 0.15),
        normal_crossfall_percent=-2.0,
        min_transition_length=float(getattr(alignment, "MinTransitionLength", 20.0) or 20.0),
        curve_candidates=_alignment_curve_candidates(alignment),
    )


def _alignment_curve_candidates(alignment) -> list[SuperelevationCurveCandidate]:
    ip_rows = alignment_ip_rows(alignment)
    candidates: list[SuperelevationCurveCandidate] = []
    for row in alignment_pi_review_rows(alignment):
        radius = float(row.get("applied_radius", 0.0) or 0.0)
        start = row.get("ts_station")
        end = row.get("te_station")
        if radius <= 0.0 or start is None or end is None:
            continue
        ip_index = int(row.get("ip_index", 0) or 0)
        candidates.append(
            SuperelevationCurveCandidate(
                curve_id=f"curve:{ip_index}",
                station_start=float(start),
                station_end=float(end),
                radius=radius,
                direction=_curve_direction(ip_rows, ip_index),
                transition_length=float(row.get("applied_transition", 0.0) or 0.0),
            )
        )
    return candidates


def _curve_direction(ip_rows: list[dict[str, float]], ip_index: int) -> str:
    index = int(ip_index) - 1
    if index <= 0 or index >= len(ip_rows) - 1:
        return "right"
    previous = ip_rows[index - 1]
    current = ip_rows[index]
    following = ip_rows[index + 1]
    v1x = float(current.get("x", 0.0) or 0.0) - float(previous.get("x", 0.0) or 0.0)
    v1y = float(current.get("y", 0.0) or 0.0) - float(previous.get("y", 0.0) or 0.0)
    v2x = float(following.get("x", 0.0) or 0.0) - float(current.get("x", 0.0) or 0.0)
    v2y = float(following.get("y", 0.0) or 0.0) - float(current.get("y", 0.0) or 0.0)
    cross = v1x * v2y - v1y * v2x
    return "left" if cross > 0.0 else "right"


def _format_auto_calculation_diagnostics(rows) -> str:
    diagnostics = list(rows or [])
    if not diagnostics:
        return ""
    lines = ["", f"Diagnostics: {len(diagnostics)}"]
    for row in diagnostics:
        notes = f" ({row.notes})" if str(getattr(row, "notes", "") or "").strip() else ""
        lines.append(f"{row.severity}:{row.kind}: {row.message}{notes}")
    return "\n" + "\n".join(lines)


def _item_text(table, row: int, column: int) -> str:
    item = table.item(int(row), int(column))
    return "" if item is None else str(item.text() or "").strip()


def _float_text(text: str, default: float = 0.0) -> float:
    try:
        return float(text)
    except Exception:
        return float(default)


def _project_id(project) -> str:
    if project is None:
        return "corridorroad-v1"
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand(SUPERELEVATION_COMMAND_ID, CmdV1SuperelevationEditor())
