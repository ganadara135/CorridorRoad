"""v1 alignment source editor command."""

from __future__ import annotations

import math

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None
    Gui = None

from freecad.Corridor_Road.qt_compat import QtWidgets

from ...misc.resources import icon_path
from ...objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from ...objects.project_links import link_project
from ...objects import design_standards as _ds
from ...objects.csv_alignment_import import read_alignment_csv, write_alignment_csv
from ...objects.sketch_alignment_import import find_sketch_objects, sketch_to_alignment_rows
from ..objects.obj_alignment import (
    V1AlignmentObject,
    ViewProviderV1Alignment,
    ensure_v1_alignment_properties,
    find_v1_alignment,
)
from .selection_context import selected_alignment_profile_target


ALIGNMENT_PRESETS = {
    "Simple Tangent": {
        "note": "Straight starter with no circular curve intent.",
        "rows": [
            (0.0, 0.0, 0.0, 0.0),
            (80.0, 0.0, 0.0, 0.0),
            (160.0, 0.0, 0.0, 0.0),
        ],
    },
    "Single Curve": {
        "note": "One PI with circular-curve intent.",
        "rows": [
            (0.0, 0.0, 0.0, 0.0),
            (70.0, 0.0, 120.0, 0.0),
            (140.0, 45.0, 0.0, 0.0),
        ],
    },
    "S-C-S Curve": {
        "note": "One PI with spiral-circular-spiral intent.",
        "rows": [
            (0.0, 0.0, 0.0, 0.0),
            (80.0, 0.0, 180.0, 30.0),
            (170.0, 55.0, 0.0, 0.0),
        ],
    },
    "Reverse Curve": {
        "note": "Alternating curve intent for reverse-curve checks.",
        "rows": [
            (0.0, 0.0, 0.0, 0.0),
            (60.0, 0.0, 120.0, 20.0),
            (120.0, 45.0, 120.0, 20.0),
            (180.0, 0.0, 0.0, 0.0),
        ],
    },
    "Sample Local Alignment": {
        "note": "Multi-PI starter for quick table editing.",
        "rows": [
            (0.0, 0.0, 0.0, 0.0),
            (55.0, 0.0, 90.0, 15.0),
            (115.0, 40.0, 140.0, 20.0),
            (190.0, 60.0, 0.0, 0.0),
        ],
    },
}

ALIGNMENT_PRESET_PLACEMENTS = [
    "Pattern only",
    "Center on terrain",
    "Center on project origin",
]


def alignment_preset_placement_names() -> list[str]:
    """Return supported preset placement modes for the v1 Alignment editor."""

    return list(ALIGNMENT_PRESET_PLACEMENTS)


def alignment_preset_center(rows) -> tuple[float, float]:
    """Return the bounding-box center of local preset PI rows."""

    values = list(rows or [])
    if not values:
        return 0.0, 0.0
    xs = [float(row[0]) for row in values]
    ys = [float(row[1]) for row in values]
    return (min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5


def alignment_preset_rows_for_placement(
    rows,
    placement: str,
    *,
    terrain_center: tuple[float, float] | None = None,
    project_origin: tuple[float, float] = (0.0, 0.0),
) -> dict[str, object]:
    """Translate preset PI rows according to a user-selected placement mode."""

    rows_in = [tuple(row) for row in list(rows or [])]
    placement_text = str(placement or "Pattern only").strip() or "Pattern only"
    source_x, source_y = alignment_preset_center(rows_in)
    target = None
    placement_used = placement_text

    if placement_text == "Center on terrain":
        if terrain_center is not None:
            target = (float(terrain_center[0]), float(terrain_center[1]))
            note = f"Terrain center used: X={target[0]:.3f}, Y={target[1]:.3f}"
        else:
            target = (float(project_origin[0]), float(project_origin[1]))
            placement_used = "Center on project origin (fallback)"
            note = "Terrain was not available; project origin was used instead."
    elif placement_text == "Center on project origin":
        target = (float(project_origin[0]), float(project_origin[1]))
        note = f"Project origin used: X={target[0]:.3f}, Y={target[1]:.3f}"
    else:
        note = "Preset kept its original pattern position."

    if target is None:
        return {"rows": rows_in, "placement": placement_used, "note": note}

    dx = float(target[0]) - float(source_x)
    dy = float(target[1]) - float(source_y)
    return {
        "rows": [(float(x) + dx, float(y) + dy, float(radius), float(ls)) for x, y, radius, ls in rows_in],
        "placement": placement_used,
        "note": note,
    }


def alignment_element_rows(alignment) -> list[dict[str, object]]:
    """Return editable geometry rows from a V1Alignment object."""

    if alignment is None:
        return []
    ensure_v1_alignment_properties(alignment)
    element_ids = list(getattr(alignment, "ElementIds", []) or [])
    kinds = list(getattr(alignment, "ElementKinds", []) or [])
    starts = _float_list(getattr(alignment, "StationStarts", []) or [])
    ends = _float_list(getattr(alignment, "StationEnds", []) or [])
    lengths = _float_list(getattr(alignment, "ElementLengths", []) or [])
    x_rows = list(getattr(alignment, "XValueRows", []) or [])
    y_rows = list(getattr(alignment, "YValueRows", []) or [])
    count = max(len(element_ids), len(kinds), len(starts), len(ends), len(x_rows), len(y_rows))
    alignment_id = str(getattr(alignment, "AlignmentId", "") or getattr(alignment, "Name", "") or "alignment:v1")
    rows: list[dict[str, object]] = []
    for index in range(count):
        station_start = float(starts[index]) if index < len(starts) else 0.0
        station_end = float(ends[index]) if index < len(ends) else station_start
        rows.append(
            {
                "element_id": (
                    str(element_ids[index])
                    if index < len(element_ids) and str(element_ids[index] or "").strip()
                    else f"{alignment_id}:element:{index + 1}"
                ),
                "kind": str(kinds[index] if index < len(kinds) and kinds[index] else "tangent"),
                "station_start": station_start,
                "station_end": station_end,
                "length": float(lengths[index]) if index < len(lengths) else max(0.0, station_end - station_start),
                "x_values": str(x_rows[index] if index < len(x_rows) else ""),
                "y_values": str(y_rows[index] if index < len(y_rows) else ""),
            }
        )
    return rows


def apply_alignment_element_rows(alignment, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Validate, sort, and write geometry rows back to a V1Alignment object."""

    if alignment is None:
        raise ValueError("No V1Alignment object is available.")
    ensure_v1_alignment_properties(alignment)
    normalized = _normalized_element_rows(alignment, rows)
    alignment.ElementIds = [str(row["element_id"]) for row in normalized]
    alignment.ElementKinds = [str(row["kind"]) for row in normalized]
    alignment.StationStarts = [float(row["station_start"]) for row in normalized]
    alignment.StationEnds = [float(row["station_end"]) for row in normalized]
    alignment.ElementLengths = [float(row["length"]) for row in normalized]
    alignment.XValueRows = [str(row["x_values"]) for row in normalized]
    alignment.YValueRows = [str(row["y_values"]) for row in normalized]
    try:
        alignment.touch()
    except Exception:
        pass
    return normalized


def alignment_ip_rows(alignment) -> list[dict[str, float]]:
    """Return v0-style PI input rows from a V1Alignment object."""

    if alignment is None:
        return []
    ensure_v1_alignment_properties(alignment)
    points = list(getattr(alignment, "IPPoints", []) or [])
    radii = _float_list(getattr(alignment, "CurveRadii", []) or [])
    transitions = _float_list(getattr(alignment, "TransitionLengths", []) or [])
    if not points:
        return _ip_rows_from_element_rows(alignment_element_rows(alignment))
    rows: list[dict[str, float]] = []
    for index, point in enumerate(points):
        rows.append(
            {
                "x": float(getattr(point, "x", 0.0) or 0.0),
                "y": float(getattr(point, "y", 0.0) or 0.0),
                "radius": float(radii[index]) if index < len(radii) else 0.0,
                "transition_length": float(transitions[index]) if index < len(transitions) else 0.0,
            }
        )
    return rows


def alignment_compiled_summary_rows(alignment) -> list[dict[str, object]]:
    """Return review rows for compiled v1 station geometry."""

    rows: list[dict[str, object]] = []
    for index, row in enumerate(alignment_element_rows(alignment), start=1):
        x_values = _csv_float_row(row.get("x_values", ""))
        y_values = _csv_float_row(row.get("y_values", ""))
        point_count = min(len(x_values), len(y_values))
        rows.append(
            {
                "index": index,
                "kind": str(row.get("kind", "") or "tangent"),
                "station_start": float(row.get("station_start", 0.0) or 0.0),
                "station_end": float(row.get("station_end", 0.0) or 0.0),
                "length": float(row.get("length", 0.0) or 0.0),
                "point_count": point_count,
                "x_values": _format_csv_float_row(x_values),
                "y_values": _format_csv_float_row(y_values),
            }
        )
    return rows


def alignment_pi_review_rows(alignment) -> list[dict[str, object]]:
    """Return PI-centered review rows with approximate curve station data."""

    if alignment is None:
        return []
    ensure_v1_alignment_properties(alignment)
    ip_rows = alignment_ip_rows(alignment)
    curve_elements = [
        row
        for row in alignment_compiled_summary_rows(alignment)
        if str(row.get("kind", "") or "") in {"sampled_curve", "transition_curve", "circular_curve"}
    ]
    curve_info = _curve_infos_for_ip_rows(
        ip_rows,
        use_transition_curves=bool(getattr(alignment, "UseTransitionCurves", True)),
        spiral_segments=int(getattr(alignment, "SpiralSegments", 16) or 16),
    )
    review_rows: list[dict[str, object]] = []
    curve_cursor = 0
    for index, row in enumerate(ip_rows):
        input_radius = float(row.get("radius", 0.0) or 0.0)
        input_transition = float(row.get("transition_length", 0.0) or 0.0)
        info = curve_info.get(index)
        curve_element = None
        if info is not None and curve_cursor < len(curve_elements):
            curve_element = curve_elements[curve_cursor]
            curve_cursor += 1
        applied_radius = float(info.get("radius", 0.0) or 0.0) if info is not None else 0.0
        applied_transition = float(info.get("transition_length", 0.0) or 0.0) if info is not None else 0.0
        ts_station = float(curve_element.get("station_start", 0.0)) if curve_element is not None else None
        te_station = float(curve_element.get("station_end", 0.0)) if curve_element is not None else None
        sc_station = None
        cs_station = None
        if ts_station is not None and te_station is not None and applied_transition > 0.0:
            mid_station = 0.5 * (ts_station + te_station)
            sc_station = min(ts_station + applied_transition, mid_station)
            cs_station = max(te_station - applied_transition, mid_station)
        review_rows.append(
            {
                "ip_index": index + 1,
                "x": float(row.get("x", 0.0) or 0.0),
                "y": float(row.get("y", 0.0) or 0.0),
                "input_radius": input_radius,
                "input_transition": input_transition,
                "applied_radius": applied_radius,
                "applied_transition": applied_transition,
                "clamped": bool(
                    info is not None
                    and (
                        abs(applied_radius - input_radius) > 1.0e-6
                        or abs(applied_transition - input_transition) > 1.0e-6
                    )
                ),
                "ts_station": ts_station,
                "sc_station": sc_station,
                "cs_station": cs_station,
                "te_station": te_station,
                "curve_length": float(curve_element.get("length", 0.0)) if curve_element is not None else 0.0,
                "curve_point_count": int(curve_element.get("point_count", 0)) if curve_element is not None else 0,
                "kind": str(curve_element.get("kind", "endpoint" if index in {0, len(ip_rows) - 1} else "tangent_pi"))
                if curve_element is not None
                else ("endpoint" if index in {0, len(ip_rows) - 1} else "tangent_pi"),
            }
        )
    return review_rows


def apply_alignment_ip_rows(
    alignment,
    rows: list[dict[str, object]],
    *,
    use_transition_curves: bool = True,
    spiral_segments: int = 16,
    design_standard: str = "KDS",
    design_speed_kph: float = 60.0,
    superelevation_pct: float = 8.0,
    side_friction: float = 0.15,
    min_radius: float = 0.0,
    min_tangent_length: float = 20.0,
    min_transition_length: float = 20.0,
) -> list[dict[str, object]]:
    """Store v0-style PI rows and compile them into v1 station geometry rows."""

    if alignment is None:
        raise ValueError("No V1Alignment object is available.")
    ensure_v1_alignment_properties(alignment)
    normalized, warnings = _normalized_ip_rows(rows)
    compiled = _compile_ip_rows_to_element_rows(
        alignment,
        normalized,
        use_transition_curves=use_transition_curves,
        spiral_segments=spiral_segments,
    )
    criteria_messages = _criteria_messages(
        normalized,
        use_transition_curves=use_transition_curves,
        design_standard=design_standard,
        design_speed_kph=design_speed_kph,
        superelevation_pct=superelevation_pct,
        side_friction=side_friction,
        min_radius=min_radius,
        min_tangent_length=min_tangent_length,
        min_transition_length=min_transition_length,
        input_warnings=warnings,
    )

    alignment.IPPoints = [_vector(row["x"], row["y"]) for row in normalized]
    alignment.CurveRadii = [float(row["radius"]) for row in normalized]
    alignment.TransitionLengths = [float(row["transition_length"]) for row in normalized]
    alignment.UseTransitionCurves = bool(use_transition_curves)
    alignment.SpiralSegments = int(max(4, int(spiral_segments)))
    alignment.DesignSpeedKph = float(design_speed_kph)
    alignment.SuperelevationPct = float(superelevation_pct)
    alignment.SideFriction = float(side_friction)
    alignment.MinRadius = float(min_radius)
    alignment.MinTangentLength = float(min_tangent_length)
    alignment.MinTransitionLength = float(min_transition_length)
    alignment.CriteriaStandard = _ds.normalize_standard(design_standard)
    alignment.CriteriaMessages = criteria_messages
    alignment.CriteriaStatus = "OK" if not criteria_messages else f"WARN ({len(criteria_messages)})"
    alignment.TotalLength = float(compiled[-1]["station_end"]) if compiled else 0.0

    apply_alignment_element_rows(alignment, compiled)
    try:
        alignment.touch()
    except Exception:
        pass
    return compiled


def create_blank_v1_alignment(*, document=None, project=None, label: str = "Main Alignment"):
    """Create an empty v1 alignment source object for Apply-time authoring."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 alignment creation.")

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
    try:
        obj = doc.addObject("Part::FeaturePython", "V1Alignment")
    except Exception:
        obj = doc.addObject("App::FeaturePython", "V1Alignment")
    V1AlignmentObject(obj)
    try:
        ViewProviderV1Alignment(obj.ViewObject)
    except Exception:
        pass
    obj.Label = label
    obj.ProjectId = str(getattr(prj, "ProjectId", "") or "corridorroad-v1")
    obj.AlignmentId = f"alignment:{str(getattr(obj, 'Name', '') or 'main')}"
    obj.AlignmentKind = "road_centerline"
    link_project(prj, links={"Alignment": obj}, adopt_extra=[obj])
    return obj


class V1AlignmentEditorTaskPanel:
    """v1 alignment editor with the v0 IP-based workflow as the primary UI."""

    def __init__(self, *, alignment=None, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.alignment = alignment or find_v1_alignment(self.document)
        self.form = self._build_ui()

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
        widget.setWindowTitle("CorridorRoad v1 - Alignment")

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Alignment")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self._alignment_label = QtWidgets.QLabel(self._alignment_summary_text())
        self._alignment_label.setStyleSheet("color: #dfe8ff; background: #263142; padding: 6px;")
        layout.addWidget(self._alignment_label)

        hint = QtWidgets.QLabel(
            "Edit PI rows the same way as the previous Alignment UI. "
            "Apply compiles the PI input into v1 station geometry used by stations, profile, sections, and corridor tools."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._tabs = QtWidgets.QTabWidget()
        self._tabs.addTab(self._build_pi_tab(), "PI Geometry")
        self._tabs.addTab(self._build_compiled_tab(), "Compiled v1 Geometry")
        layout.addWidget(self._tabs, 1)

        button_row = QtWidgets.QHBoxLayout()
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        button_row.addWidget(apply_button)
        review_button = QtWidgets.QPushButton("Review Alignment")
        review_button.clicked.connect(self._open_alignment_review)
        button_row.addWidget(review_button)
        button_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        self._load_ip_rows()
        self._load_element_rows()
        self._load_criteria()
        self._refresh_report()
        return widget

    def _build_pi_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)

        sketch_row = QtWidgets.QHBoxLayout()
        self._sketch_combo = QtWidgets.QComboBox()
        self._sketch_combo.setMaximumWidth(280)
        refresh_sketch_button = QtWidgets.QPushButton("Refresh")
        refresh_sketch_button.clicked.connect(self._refresh_sketches)
        load_sketch_button = QtWidgets.QPushButton("Load from Sketch")
        load_sketch_button.clicked.connect(self._load_from_sketch)
        sketch_row.addWidget(QtWidgets.QLabel("Sketch:"))
        sketch_row.addWidget(self._sketch_combo, 1)
        sketch_row.addWidget(refresh_sketch_button)
        sketch_row.addWidget(load_sketch_button)
        layout.addLayout(sketch_row)

        csv_row = QtWidgets.QHBoxLayout()
        self._csv_path = QtWidgets.QLineEdit()
        self._csv_path.setPlaceholderText("Path to alignment CSV file")
        browse_csv_button = QtWidgets.QPushButton("Browse CSV")
        browse_csv_button.clicked.connect(self._browse_csv)
        load_csv_button = QtWidgets.QPushButton("Load CSV")
        load_csv_button.clicked.connect(self._load_from_csv)
        save_csv_button = QtWidgets.QPushButton("Save CSV")
        save_csv_button.clicked.connect(self._save_csv)
        csv_row.addWidget(QtWidgets.QLabel("CSV:"))
        csv_row.addWidget(self._csv_path, 1)
        csv_row.addWidget(browse_csv_button)
        csv_row.addWidget(load_csv_button)
        csv_row.addWidget(save_csv_button)
        layout.addLayout(csv_row)

        preset_row = QtWidgets.QHBoxLayout()
        self._preset_combo = QtWidgets.QComboBox()
        self._preset_combo.addItems(list(ALIGNMENT_PRESETS.keys()))
        self._preset_placement_combo = QtWidgets.QComboBox()
        self._preset_placement_combo.addItems(alignment_preset_placement_names())
        self._preset_placement_combo.setCurrentText("Center on terrain")
        self._preset_note = QtWidgets.QLabel("")
        self._preset_note.setWordWrap(True)
        load_preset_button = QtWidgets.QPushButton("Load Preset")
        load_preset_button.clicked.connect(self._load_selected_preset)
        self._preset_combo.currentIndexChanged.connect(self._update_preset_note)
        self._preset_placement_combo.currentIndexChanged.connect(self._update_preset_note)
        preset_row.addWidget(QtWidgets.QLabel("Preset:"))
        preset_row.addWidget(self._preset_combo)
        preset_row.addWidget(QtWidgets.QLabel("Placement:"))
        preset_row.addWidget(self._preset_placement_combo)
        preset_row.addWidget(load_preset_button)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)
        layout.addWidget(self._preset_note)

        self._ip_table = QtWidgets.QTableWidget(0, 4)
        self._ip_table.setHorizontalHeaderLabels(["X", "Y", "Radius (m)", "Transition Ls (m)"])
        self._ip_table.setMinimumHeight(220)
        try:
            self._ip_table.horizontalHeader().setStretchLastSection(True)
            self._ip_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self._ip_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        except Exception:
            pass
        layout.addWidget(self._ip_table)

        row_buttons = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add Row")
        add_button.clicked.connect(self._add_ip_row)
        remove_button = QtWidgets.QPushButton("Remove Row")
        remove_button.clicked.connect(self._remove_ip_row)
        sort_button = QtWidgets.QPushButton("Sort by X/Y")
        sort_button.clicked.connect(self._sort_ip_rows)
        row_buttons.addWidget(add_button)
        row_buttons.addWidget(remove_button)
        row_buttons.addWidget(sort_button)
        row_buttons.addStretch(1)
        layout.addLayout(row_buttons)

        criteria_group = QtWidgets.QGroupBox("Geometry / Criteria")
        form = QtWidgets.QFormLayout(criteria_group)
        self._use_transition_check = QtWidgets.QCheckBox("Use transition curves (S-C-S intent)")
        self._use_transition_check.setChecked(True)
        self._spiral_segments_spin = QtWidgets.QSpinBox()
        self._spiral_segments_spin.setRange(4, 128)
        self._spiral_segments_spin.setValue(16)
        self._design_standard_combo = QtWidgets.QComboBox()
        self._design_standard_combo.addItems(list(_ds.SUPPORTED_STANDARDS))
        self._design_speed_spin = self._double_spin(0.0, 300.0, 60.0, 1, " km/h")
        self._superelevation_spin = self._double_spin(0.0, 20.0, 8.0, 2, " %")
        self._side_friction_spin = self._double_spin(0.01, 0.40, 0.15, 3, "")
        self._min_radius_spin = self._double_spin(0.0, 100000.0, 0.0, 3, " m")
        self._min_radius_spin.setToolTip("0 = auto from selected standard and design speed")
        self._min_tangent_spin = self._double_spin(0.0, 100000.0, 20.0, 3, " m")
        self._min_transition_spin = self._double_spin(0.0, 100000.0, 20.0, 3, " m")
        form.addRow(self._use_transition_check)
        form.addRow("Design standard:", self._design_standard_combo)
        form.addRow("Spiral segments:", self._spiral_segments_spin)
        form.addRow("Design speed:", self._design_speed_spin)
        form.addRow("Superelevation e:", self._superelevation_spin)
        form.addRow("Side friction f:", self._side_friction_spin)
        form.addRow("Min radius override:", self._min_radius_spin)
        form.addRow("Min tangent length:", self._min_tangent_spin)
        form.addRow("Min transition length:", self._min_transition_spin)
        layout.addWidget(criteria_group)

        self._report = QtWidgets.QPlainTextEdit()
        self._report.setReadOnly(True)
        self._report.setFixedHeight(60)
        self._report.setPlaceholderText("Criteria messages will appear after Apply.")
        layout.addWidget(self._report)

        self._update_preset_note()
        self._refresh_sketches()
        return tab

    def _build_compiled_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)
        note = QtWidgets.QLabel(
            "Read-only v1 geometry compiled from PI rows. Downstream v1 tools consume this station-based geometry."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self._element_table = QtWidgets.QTableWidget(0, 7)
        self._element_table.setHorizontalHeaderLabels(
            ["Kind", "Start STA", "End STA", "Length", "Points", "X Values", "Y Values"]
        )
        self._element_table.setMinimumHeight(220)
        try:
            self._element_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        layout.addWidget(self._element_table, 1)
        return tab

    @staticmethod
    def _double_spin(minimum: float, maximum: float, value: float, decimals: int, suffix: str):
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(float(minimum), float(maximum))
        spin.setDecimals(int(decimals))
        spin.setValue(float(value))
        if suffix:
            spin.setSuffix(str(suffix))
        return spin

    def _load_ip_rows(self) -> None:
        self._ip_table.setRowCount(0)
        if self.alignment is None:
            self._set_default_starter_rows()
            return
        for row in alignment_ip_rows(self.alignment):
            self._append_ip_row(row)

    def _set_default_starter_rows(self) -> None:
        preset_name = "Sample Local Alignment"
        preset = ALIGNMENT_PRESETS.get(preset_name, {})
        index = self._preset_combo.findText(preset_name)
        if index >= 0:
            self._preset_combo.setCurrentIndex(index)
        self._set_ip_rows_data(list(preset.get("rows", []) or []))
        self._set_status("Starter PI rows are loaded. Apply to create the v1 alignment.", ok=True)

    def _append_ip_row(self, row: dict[str, object]) -> None:
        row_index = self._ip_table.rowCount()
        self._ip_table.insertRow(row_index)
        values = [
            _format_float(row.get("x", 0.0)),
            _format_float(row.get("y", 0.0)),
            _format_float(row.get("radius", 0.0)),
            _format_float(row.get("transition_length", 0.0)),
        ]
        for col, value in enumerate(values):
            self._ip_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))

    def _load_element_rows(self) -> None:
        self._element_table.setRowCount(0)
        for row in alignment_compiled_summary_rows(self.alignment):
            self._append_element_row(row)

    def _append_element_row(self, row: dict[str, object]) -> None:
        row_index = self._element_table.rowCount()
        self._element_table.insertRow(row_index)
        values = [
            str(row.get("kind", "") or "tangent"),
            _format_float(row.get("station_start", 0.0)),
            _format_float(row.get("station_end", 0.0)),
            _format_float(row.get("length", 0.0)),
            str(int(row.get("point_count", 0) or 0)),
            str(row.get("x_values", "") or ""),
            str(row.get("y_values", "") or ""),
        ]
        for col, value in enumerate(values):
            item = QtWidgets.QTableWidgetItem(value)
            try:
                item.setFlags(item.flags() & ~2)
            except Exception:
                pass
            self._element_table.setItem(row_index, col, item)

    def _load_criteria(self) -> None:
        alignment = self.alignment
        if alignment is None:
            return
        ensure_v1_alignment_properties(alignment)
        self._use_transition_check.setChecked(bool(getattr(alignment, "UseTransitionCurves", True)))
        self._spiral_segments_spin.setValue(int(getattr(alignment, "SpiralSegments", 16) or 16))
        standard = _ds.normalize_standard(str(getattr(alignment, "CriteriaStandard", "KDS") or "KDS"))
        index = self._design_standard_combo.findText(standard)
        if index >= 0:
            self._design_standard_combo.setCurrentIndex(index)
        self._design_speed_spin.setValue(float(getattr(alignment, "DesignSpeedKph", 60.0) or 60.0))
        self._superelevation_spin.setValue(float(getattr(alignment, "SuperelevationPct", 8.0) or 8.0))
        self._side_friction_spin.setValue(float(getattr(alignment, "SideFriction", 0.15) or 0.15))
        self._min_radius_spin.setValue(float(getattr(alignment, "MinRadius", 0.0) or 0.0))
        self._min_tangent_spin.setValue(float(getattr(alignment, "MinTangentLength", 20.0) or 20.0))
        self._min_transition_spin.setValue(float(getattr(alignment, "MinTransitionLength", 20.0) or 20.0))

    def _add_ip_row(self) -> None:
        rows = self._ip_rows(allow_empty=True)
        if rows:
            last = rows[-1]
            x = float(last["x"]) + 20.0
            y = float(last["y"])
        else:
            x = 0.0
            y = 0.0
        self._append_ip_row({"x": x, "y": y, "radius": 0.0, "transition_length": 0.0})
        self._set_status("Added a new PI row. Apply when ready.", ok=True)

    def _remove_ip_row(self) -> None:
        row_index = self._ip_table.currentRow()
        if row_index < 0:
            row_index = self._ip_table.rowCount() - 1
        if row_index >= 0:
            self._ip_table.removeRow(row_index)
            self._set_status("Removed selected PI row. Apply when ready.", ok=True)

    def _sort_ip_rows(self) -> None:
        try:
            rows, _warnings = _normalized_ip_rows(self._ip_rows(allow_empty=True), min_rows=0)
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            return
        rows.sort(key=lambda item: (float(item["x"]), float(item["y"])))
        self._ip_table.setRowCount(0)
        for row in rows:
            self._append_ip_row(row)
        self._set_status("PI rows sorted by X/Y. Apply when ready.", ok=True)

    def _load_selected_preset(self) -> None:
        preset = ALIGNMENT_PRESETS.get(str(self._preset_combo.currentText() or ""), {})
        rows = list(preset.get("rows", []) or [])
        placed = alignment_preset_rows_for_placement(
            rows,
            self._selected_preset_placement(),
            terrain_center=self._selected_terrain_center_for_preset(),
            project_origin=self._project_origin_anchor(),
        )
        self._set_ip_rows_data(list(placed.get("rows", []) or []))
        self._set_status(
            f"Preset loaded ({placed.get('placement')}). {placed.get('note')} Apply to compile v1 alignment geometry.",
            ok=True,
        )

    def _refresh_sketches(self) -> None:
        self._sketches = find_sketch_objects(self.document)
        self._sketch_combo.clear()
        for sketch in self._sketches:
            label = str(getattr(sketch, "Label", "") or getattr(sketch, "Name", "") or "Sketch")
            name = str(getattr(sketch, "Name", "") or "")
            self._sketch_combo.addItem(f"{label} ({name})")

    def _current_sketch(self):
        index = int(self._sketch_combo.currentIndex())
        if index < 0 or index >= len(getattr(self, "_sketches", [])):
            return None
        return self._sketches[index]

    def _load_from_sketch(self) -> None:
        sketch = self._current_sketch()
        if sketch is None:
            self._set_status("No sketch is selected.", ok=False)
            return
        try:
            rows = sketch_to_alignment_rows(sketch)
            self._set_ip_rows_data(rows)
            self._set_status(f"Loaded {len(rows)} PI row(s) from sketch. Apply when ready.", ok=True)
        except Exception as exc:
            self._set_status(f"Sketch import failed: {exc}", ok=False)

    def _browse_csv(self) -> None:
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select Alignment CSV",
            str(self._csv_path.text() or ""),
            "CSV Files (*.csv *.txt);;All Files (*.*)",
        )
        if str(path or "").strip():
            self._csv_path.setText(str(path))

    def _load_from_csv(self) -> None:
        path = str(self._csv_path.text() or "").strip()
        if not path:
            self._set_status("CSV path is empty.", ok=False)
            return
        try:
            info = read_alignment_csv(
                path,
                doc_or_project=self.document,
                encoding="auto",
                delimiter="auto",
                has_header="auto",
                sort_mode="input",
                drop_consecutive_duplicates=True,
                clamp_negative=True,
                enforce_endpoints=True,
            )
            rows = list(info.get("rows", []) or [])
            if len(rows) < 2:
                raise ValueError("CSV must provide at least 2 valid rows.")
            self._set_ip_rows_data(rows)
            self._set_status(f"Loaded {len(rows)} PI row(s) from CSV. Apply when ready.", ok=True)
        except Exception as exc:
            self._set_status(f"CSV import failed: {exc}", ok=False)

    def _save_csv(self) -> None:
        try:
            rows = self._ip_rows(allow_empty=True)
        except Exception as exc:
            self._set_status(f"CSV export failed: {exc}", ok=False)
            return
        path = str(self._csv_path.text() or "").strip() or "alignment_pi.csv"
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Save Alignment CSV",
            path,
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*.*)",
        )
        if not str(path or "").strip():
            return
        try:
            export_rows = [
                (
                    float(row["x"]),
                    float(row["y"]),
                    float(row.get("radius", 0.0) or 0.0),
                    float(row.get("transition_length", 0.0) or 0.0),
                )
                for row in rows
            ]
            info = write_alignment_csv(path, export_rows, doc_or_project=self.document)
            self._csv_path.setText(str(path))
            self._set_status(f"Saved {int(info.get('written', len(export_rows)))} PI row(s) to CSV.", ok=True)
        except Exception as exc:
            self._set_status(f"CSV export failed: {exc}", ok=False)

    def _set_ip_rows_data(self, rows) -> None:
        self._ip_table.setRowCount(0)
        for x, y, radius, transition_length in list(rows or []):
            self._append_ip_row(
                {
                    "x": float(x),
                    "y": float(y),
                    "radius": float(radius),
                    "transition_length": float(transition_length),
                }
            )

    def _update_preset_note(self) -> None:
        if not hasattr(self, "_preset_note"):
            return
        preset = ALIGNMENT_PRESETS.get(str(self._preset_combo.currentText() or ""), {})
        placement = self._selected_preset_placement()
        note = str(preset.get("note", "") or "")
        if note:
            note = f"{note} Placement: {placement}."
        else:
            note = f"Preset placement: {placement}."
        self._preset_note.setText(note)

    def _selected_preset_placement(self) -> str:
        if not hasattr(self, "_preset_placement_combo"):
            return "Pattern only"
        return str(self._preset_placement_combo.currentText() or "Pattern only").strip()

    def _selected_terrain_center_for_preset(self) -> tuple[float, float] | None:
        terrain = self._selected_terrain_for_preset()
        if terrain is None:
            return None
        try:
            if hasattr(terrain, "Mesh") and terrain.Mesh is not None:
                box = terrain.Mesh.BoundBox
            else:
                box = terrain.Shape.BoundBox
        except Exception:
            return None
        return (
            0.5 * (float(box.XMin) + float(box.XMax)),
            0.5 * (float(box.YMin) + float(box.YMax)),
        )

    def _selected_terrain_for_preset(self):
        project = find_project(self.document)
        if project is not None:
            try:
                terrain = getattr(project, "Terrain", None)
                if self._is_surface_like(terrain):
                    return terrain
            except Exception:
                pass
        if Gui is not None:
            try:
                for obj in list(Gui.Selection.getSelection() or []):
                    if self._is_surface_like(obj):
                        return obj
            except Exception:
                pass
        for obj in list(getattr(self.document, "Objects", []) or []):
            if self._is_surface_like(obj):
                return obj
        return None

    @staticmethod
    def _is_surface_like(obj) -> bool:
        if obj is None:
            return False
        try:
            from freecad.Corridor_Road.objects import surface_sampling_core as _ssc

            return bool(_ssc.is_mesh_object(obj) or _ssc.is_shape_object(obj))
        except Exception:
            return False

    def _project_origin_anchor(self) -> tuple[float, float]:
        project = find_project(self.document)
        if project is None:
            return 0.0, 0.0
        try:
            return (
                float(getattr(project, "LocalOriginX", 0.0) or 0.0),
                float(getattr(project, "LocalOriginY", 0.0) or 0.0),
            )
        except Exception:
            return 0.0, 0.0

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            input_rows = self._ip_rows(allow_empty=True)
            _normalized_ip_rows(input_rows)
            if self.alignment is None:
                self.alignment = create_blank_v1_alignment(document=self.document)
            compiled = apply_alignment_ip_rows(
                self.alignment,
                input_rows,
                use_transition_curves=bool(self._use_transition_check.isChecked()),
                spiral_segments=int(self._spiral_segments_spin.value()),
                design_standard=str(self._design_standard_combo.currentText() or "KDS"),
                design_speed_kph=float(self._design_speed_spin.value()),
                superelevation_pct=float(self._superelevation_spin.value()),
                side_friction=float(self._side_friction_spin.value()),
                min_radius=float(self._min_radius_spin.value()),
                min_tangent_length=float(self._min_tangent_spin.value()),
                min_transition_length=float(self._min_transition_spin.value()),
            )
            if self.document is not None:
                try:
                    self.document.recompute()
                except Exception:
                    pass
            self._load_element_rows()
            self._refresh_report()
            self._set_status(f"Applied {len(compiled)} compiled v1 geometry row(s).", ok=True)
            self._alignment_label.setText(self._alignment_summary_text())
            self._show_apply_complete_message(len(compiled))
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Alignment", f"Alignment was not applied.\n{exc}")
            return False

    def _show_apply_complete_message(self, compiled_count: int) -> None:
        try:
            QtWidgets.QMessageBox.information(
                self.form,
                "Alignment",
                f"Alignment has been applied successfully.\nCompiled geometry rows: {int(compiled_count)}",
            )
        except Exception:
            pass

    def _ip_rows(self, *, allow_empty: bool) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row_index in range(self._ip_table.rowCount()):
            x_text = self._item_text(self._ip_table, row_index, 0)
            y_text = self._item_text(self._ip_table, row_index, 1)
            radius_text = self._item_text(self._ip_table, row_index, 2)
            transition_text = self._item_text(self._ip_table, row_index, 3)
            if not x_text and not y_text and not radius_text and not transition_text and allow_empty:
                continue
            rows.append(
                {
                    "x": _required_float(x_text, f"Row {row_index + 1} X"),
                    "y": _required_float(y_text, f"Row {row_index + 1} Y"),
                    "radius": _optional_float(radius_text) or 0.0,
                    "transition_length": _optional_float(transition_text) or 0.0,
                }
            )
        return rows

    @staticmethod
    def _item_text(table, row_index: int, col_index: int) -> str:
        item = table.item(row_index, col_index)
        if item is None:
            return ""
        return str(item.text() or "").strip()

    def _refresh_report(self) -> None:
        if self.alignment is None:
            self._report.setPlainText("No v1 alignment object.")
            return
        ensure_v1_alignment_properties(self.alignment)
        lines = [
            f"Design standard: {str(getattr(self.alignment, 'CriteriaStandard', '') or 'KDS')}",
            f"Status: {str(getattr(self.alignment, 'CriteriaStatus', '') or 'OK')}",
            f"Total length: {_format_float(getattr(self.alignment, 'TotalLength', 0.0))} m",
            f"PI count: {len(alignment_ip_rows(self.alignment))}",
            f"Compiled element count: {len(alignment_element_rows(self.alignment))}",
            f"Compiled curve elements: {int(getattr(self.alignment, 'CompiledCurveElementCount', 0) or 0)}",
            f"Compiled transition elements: {int(getattr(self.alignment, 'CompiledTransitionElementCount', 0) or 0)}",
            f"Display edges: {int(getattr(self.alignment, 'CompiledEdgeCount', 0) or 0)}",
            f"Display status: {str(getattr(self.alignment, 'CompiledGeometryStatus', '') or 'pending')}",
        ]
        messages = list(getattr(self.alignment, "CriteriaMessages", []) or [])
        lines.append("")
        if messages:
            lines.append("Criteria warnings:")
            lines.extend(str(message) for message in messages)
        else:
            lines.append("Criteria warnings: none")
        pi_review_rows = alignment_pi_review_rows(self.alignment)
        if pi_review_rows:
            lines.append("")
            lines.append("PI Review:")
            for row in pi_review_rows:
                lines.append(_format_pi_review_line(row))
        compiled_rows = alignment_compiled_summary_rows(self.alignment)
        if compiled_rows:
            lines.append("")
            lines.append("Compiled Geometry:")
            for row in compiled_rows:
                lines.append(_format_compiled_review_line(row))
        self._report.setPlainText("\n".join(lines))

    def _open_alignment_review(self) -> None:
        dialog = QtWidgets.QDialog(self.form)
        dialog.setWindowTitle("Review Alignment")
        dialog.resize(760, 520)
        layout = QtWidgets.QVBoxLayout(dialog)
        note = QtWidgets.QLabel("Review the v1 alignment source input and compiled station geometry.")
        note.setWordWrap(True)
        layout.addWidget(note)
        text = QtWidgets.QPlainTextEdit()
        text.setReadOnly(True)
        self._refresh_report()
        text.setPlainText(str(self._report.toPlainText() or ""))
        layout.addWidget(text, 1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close_button)
        layout.addLayout(row)
        dialog.exec_()

    def _alignment_summary_text(self) -> str:
        if self.alignment is None:
            return "No V1Alignment is available."
        return (
            f"Alignment: {str(getattr(self.alignment, 'Label', '') or getattr(self.alignment, 'Name', '') or '')} | "
            f"AlignmentId: {str(getattr(self.alignment, 'AlignmentId', '') or '')}"
        )

    def _set_status(self, message: str, *, ok: bool) -> None:
        return

    def _show_message(self, title: str, message: str) -> None:
        try:
            QtWidgets.QMessageBox.information(self.form, title, message)
        except Exception:
            pass


def run_v1_alignment_editor_command():
    """Open the v1 alignment editor without creating sample data on open."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    preferred_alignment, _preferred_profile = selected_alignment_profile_target(Gui, document)
    alignment = find_v1_alignment(document, preferred_alignment=preferred_alignment)
    if Gui is not None and hasattr(Gui, "Control"):
        if alignment is not None:
            try:
                Gui.Selection.clearSelection()
                Gui.Selection.addSelection(alignment)
            except Exception:
                pass
        Gui.Control.showDialog(V1AlignmentEditorTaskPanel(alignment=alignment, document=document))
    return alignment


class CmdV1AlignmentEditor:
    """Open the v1 alignment source editor."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("alignment.svg"),
            "MenuText": "Alignment",
            "ToolTip": "Create or edit the v1 alignment PI geometry and criteria",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_alignment_editor_command()


def _normalized_ip_rows(
    rows: list[dict[str, object]],
    *,
    min_rows: int = 2,
) -> tuple[list[dict[str, float]], list[str]]:
    normalized: list[dict[str, float]] = []
    warnings: list[str] = []
    for index, row in enumerate(rows):
        x = _required_float(row.get("x", None), f"Row {index + 1} X")
        y = _required_float(row.get("y", None), f"Row {index + 1} Y")
        radius = max(0.0, _optional_float(row.get("radius", 0.0)) or 0.0)
        transition_length = max(0.0, _optional_float(row.get("transition_length", 0.0)) or 0.0)
        normalized.append(
            {
                "x": float(x),
                "y": float(y),
                "radius": float(radius),
                "transition_length": float(transition_length),
            }
        )

    if len(normalized) < min_rows:
        raise ValueError(f"Alignment needs at least {min_rows} PI rows.")

    tolerance = 1.0e-6
    for index in range(len(normalized) - 1):
        current = normalized[index]
        next_row = normalized[index + 1]
        if _distance(current["x"], current["y"], next_row["x"], next_row["y"]) <= tolerance:
            raise ValueError(f"Rows {index + 1} and {index + 2} are duplicated or too close.")

    if normalized:
        if abs(float(normalized[0]["radius"])) > 1.0e-9 or abs(float(normalized[-1]["radius"])) > 1.0e-9:
            warnings.append("Endpoint radius values were forced to 0.")
        if abs(float(normalized[0]["transition_length"])) > 1.0e-9 or abs(float(normalized[-1]["transition_length"])) > 1.0e-9:
            warnings.append("Endpoint transition length values were forced to 0.")
        normalized[0]["radius"] = 0.0
        normalized[-1]["radius"] = 0.0
        normalized[0]["transition_length"] = 0.0
        normalized[-1]["transition_length"] = 0.0
    return normalized, warnings


def _compile_ip_rows_to_element_rows(
    alignment,
    rows: list[dict[str, float]],
    *,
    use_transition_curves: bool = True,
    spiral_segments: int = 16,
) -> list[dict[str, object]]:
    alignment_id = str(getattr(alignment, "AlignmentId", "") or getattr(alignment, "Name", "") or "alignment:v1")
    compiled: list[dict[str, object]] = []
    station = 0.0
    chunks = _sampled_alignment_chunks_from_ip_rows(
        rows,
        use_transition_curves=use_transition_curves,
        spiral_segments=spiral_segments,
    )
    for index, chunk in enumerate(chunks, start=1):
        points = list(chunk.get("points", []) or [])
        length = _polyline_length(points)
        if length <= 1.0e-9:
            continue
        station_start = station
        station_end = station_start + length
        compiled.append(
            {
                "element_id": f"{alignment_id}:compiled:{index}",
                "kind": str(chunk.get("kind", "") or "tangent"),
                "station_start": station_start,
                "station_end": station_end,
                "length": length,
                "x_values": _format_csv_float_row([point[0] for point in points]),
                "y_values": _format_csv_float_row([point[1] for point in points]),
            }
        )
        station = station_end
    if not compiled:
        raise ValueError("Alignment could not compile PI rows into station geometry.")
    return compiled


def _sampled_alignment_chunks_from_ip_rows(
    rows: list[dict[str, float]],
    *,
    use_transition_curves: bool,
    spiral_segments: int,
) -> list[dict[str, object]]:
    points = [(float(row["x"]), float(row["y"])) for row in rows]
    curve_infos = _curve_infos_for_ip_rows(
        rows,
        use_transition_curves=use_transition_curves,
        spiral_segments=spiral_segments,
    )
    chunks: list[dict[str, object]] = []
    current = points[0]

    for index in range(len(points) - 1):
        next_curve = curve_infos.get(index + 1)
        line_end = next_curve["in_point"] if next_curve is not None else points[index + 1]
        if _distance(current[0], current[1], line_end[0], line_end[1]) > 1.0e-9:
            chunks.append({"kind": "tangent", "points": [current, line_end]})
            current = line_end
        if next_curve is not None:
            kind = "transition_curve" if float(next_curve.get("transition_length", 0.0) or 0.0) > 0.0 else "sampled_curve"
            arc_points = list(next_curve.get("points", []) or [])
            if len(arc_points) >= 2:
                chunks.append({"kind": kind, "points": arc_points})
                current = arc_points[-1]
    return chunks


def _curve_infos_for_ip_rows(
    rows: list[dict[str, float]],
    *,
    use_transition_curves: bool,
    spiral_segments: int,
) -> dict[int, dict[str, object]]:
    infos: dict[int, dict[str, object]] = {}
    sample_count_base = max(8, int(spiral_segments or 16))
    for index in range(1, len(rows) - 1):
        previous_row = rows[index - 1]
        row = rows[index]
        next_row = rows[index + 1]
        radius = float(row.get("radius", 0.0) or 0.0)
        if radius <= 1.0e-9:
            continue

        p0 = (float(previous_row["x"]), float(previous_row["y"]))
        pi = (float(row["x"]), float(row["y"]))
        p2 = (float(next_row["x"]), float(next_row["y"]))
        incoming_length = _distance(p0[0], p0[1], pi[0], pi[1])
        outgoing_length = _distance(pi[0], pi[1], p2[0], p2[1])
        if incoming_length <= 1.0e-9 or outgoing_length <= 1.0e-9:
            continue

        incoming = ((pi[0] - p0[0]) / incoming_length, (pi[1] - p0[1]) / incoming_length)
        outgoing = ((p2[0] - pi[0]) / outgoing_length, (p2[1] - pi[1]) / outgoing_length)
        delta = math.atan2(_cross_2d(incoming, outgoing), _dot_2d(incoming, outgoing))
        abs_delta = abs(delta)
        if abs_delta <= math.radians(1.0):
            continue

        tan_half = math.tan(0.5 * abs_delta)
        if abs(tan_half) <= 1.0e-12:
            continue
        requested_transition = float(row.get("transition_length", 0.0) or 0.0) if use_transition_curves else 0.0
        requested_setback = _tangent_setback(radius, requested_transition, abs_delta)
        max_setback = 0.45 * min(incoming_length, outgoing_length)
        scale = 1.0
        if requested_setback > max_setback and requested_setback > 1.0e-9:
            scale = max_setback / requested_setback
        setback = min(requested_setback, max_setback)
        if setback <= 1.0e-9:
            continue
        effective_radius = max(1.0e-9, radius * scale)
        effective_transition = max(0.0, requested_transition * scale)
        max_transition = max(0.0, 0.80 * abs_delta * effective_radius)
        if effective_transition > max_transition:
            effective_transition = max_transition
            setback = min(_tangent_setback(effective_radius, effective_transition, abs_delta), max_setback)

        turn_sign = 1.0 if delta > 0.0 else -1.0
        in_point = (pi[0] - incoming[0] * setback, pi[1] - incoming[1] * setback)
        out_point = (pi[0] + outgoing[0] * setback, pi[1] + outgoing[1] * setback)
        arc_points = _sample_scs_or_arc_points(
            in_point,
            out_point,
            incoming,
            abs_delta=abs_delta,
            turn_sign=turn_sign,
            radius=effective_radius,
            transition_length=effective_transition,
            sample_count_base=sample_count_base,
        )
        infos[index] = {
            "in_point": in_point,
            "out_point": out_point,
            "points": arc_points,
            "radius": effective_radius,
            "transition_length": effective_transition,
        }
    return infos


def _tangent_setback(radius: float, transition_length: float, deflection_angle: float) -> float:
    radius = max(0.0, float(radius))
    transition_length = max(0.0, float(transition_length))
    theta = max(0.0, float(deflection_angle))
    if radius <= 1.0e-9 or theta <= 1.0e-9:
        return 0.0
    shift = (transition_length * transition_length) / (24.0 * radius) if transition_length > 1.0e-9 else 0.0
    return (radius + shift) * math.tan(0.5 * theta) + 0.5 * transition_length


def _sample_scs_or_arc_points(
    in_point: tuple[float, float],
    out_point: tuple[float, float],
    incoming: tuple[float, float],
    *,
    abs_delta: float,
    turn_sign: float,
    radius: float,
    transition_length: float,
    sample_count_base: int,
) -> list[tuple[float, float]]:
    if transition_length > 1.0e-9:
        return _sample_scs_points(
            in_point,
            out_point,
            incoming,
            abs_delta=abs_delta,
            turn_sign=turn_sign,
            radius=radius,
            transition_length=transition_length,
            sample_count_base=sample_count_base,
        )
    return _sample_arc_points(
        in_point,
        out_point,
        incoming,
        abs_delta=abs_delta,
        turn_sign=turn_sign,
        radius=radius,
        sample_count_base=sample_count_base,
    )


def _sample_arc_points(
    in_point: tuple[float, float],
    out_point: tuple[float, float],
    incoming: tuple[float, float],
    *,
    abs_delta: float,
    turn_sign: float,
    radius: float,
    sample_count_base: int,
) -> list[tuple[float, float]]:
    normal_in = _left_normal(incoming)
    center = (
        in_point[0] + turn_sign * radius * normal_in[0],
        in_point[1] + turn_sign * radius * normal_in[1],
    )
    start_angle = math.atan2(in_point[1] - center[1], in_point[0] - center[0])
    end_angle = start_angle + turn_sign * abs_delta
    samples = max(4, int(math.ceil(sample_count_base * abs_delta / (0.5 * math.pi))))
    points = []
    for sample_index in range(samples + 1):
        ratio = float(sample_index) / float(samples)
        angle = start_angle + (end_angle - start_angle) * ratio
        points.append((center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle)))
    points[0] = in_point
    points[-1] = out_point
    return points


def _sample_scs_points(
    in_point: tuple[float, float],
    out_point: tuple[float, float],
    incoming: tuple[float, float],
    *,
    abs_delta: float,
    turn_sign: float,
    radius: float,
    transition_length: float,
    sample_count_base: int,
) -> list[tuple[float, float]]:
    transition_length = max(0.0, min(float(transition_length), 0.80 * float(abs_delta) * float(radius)))
    circular_angle = max(0.0, float(abs_delta) - (transition_length / float(radius)))
    circular_length = float(radius) * circular_angle
    heading = math.atan2(float(incoming[1]), float(incoming[0]))
    x, y = float(in_point[0]), float(in_point[1])
    points = [(x, y)]

    def _advance(length: float, k_start: float, k_end: float, steps: int) -> None:
        nonlocal x, y, heading
        if length <= 1.0e-9 or steps <= 0:
            return
        ds = float(length) / float(steps)
        for step in range(steps):
            t0 = float(step) / float(steps)
            t1 = float(step + 1) / float(steps)
            k0 = float(k_start) + (float(k_end) - float(k_start)) * t0
            k1 = float(k_start) + (float(k_end) - float(k_start)) * t1
            d_heading = turn_sign * 0.5 * (k0 + k1) * ds
            mid_heading = heading + 0.5 * d_heading
            x += ds * math.cos(mid_heading)
            y += ds * math.sin(mid_heading)
            heading += d_heading
            points.append((x, y))

    spiral_steps = max(4, int(sample_count_base))
    circular_steps = max(2, int(math.ceil(sample_count_base * circular_angle / (0.5 * math.pi)))) if circular_length > 1.0e-9 else 0
    full_curvature = 1.0 / float(radius)
    _advance(transition_length, 0.0, full_curvature, spiral_steps)
    _advance(circular_length, full_curvature, full_curvature, circular_steps)
    _advance(transition_length, full_curvature, 0.0, spiral_steps)

    # Numerical integration plus short-layout clamping can leave a small endpoint gap.
    # Distribute the correction so adjacent tangent chunks connect exactly.
    end_x, end_y = points[-1]
    err_x = float(out_point[0]) - float(end_x)
    err_y = float(out_point[1]) - float(end_y)
    corrected = []
    count = max(1, len(points) - 1)
    for index, point in enumerate(points):
        ratio = float(index) / float(count)
        corrected.append((point[0] + err_x * ratio, point[1] + err_y * ratio))
    corrected[0] = in_point
    corrected[-1] = out_point
    return corrected


def _criteria_messages(
    rows: list[dict[str, float]],
    *,
    use_transition_curves: bool,
    design_standard: str,
    design_speed_kph: float,
    superelevation_pct: float,
    side_friction: float,
    min_radius: float,
    min_tangent_length: float,
    min_transition_length: float,
    input_warnings: list[str],
) -> list[str]:
    messages = list(input_warnings or [])
    standard = _ds.normalize_standard(design_standard)
    defaults = _ds.criteria_defaults(standard, design_speed_kph)
    radius_limit = float(min_radius) if float(min_radius) > 0.0 else float(defaults.get("min_radius", 0.0) or 0.0)
    transition_limit = max(float(min_transition_length), float(defaults.get("min_transition", 0.0) or 0.0))
    tangent_limit = max(float(min_tangent_length), float(defaults.get("min_tangent", 0.0) or 0.0))

    for index, row in enumerate(rows[1:-1], start=2):
        radius = float(row.get("radius", 0.0) or 0.0)
        transition = float(row.get("transition_length", 0.0) or 0.0)
        if radius > 0.0 and radius_limit > 0.0 and radius < radius_limit - 1.0e-6:
            messages.append(f"[RADIUS] IP#{index} R={radius:.3f}m < min {radius_limit:.3f}m.")
        if use_transition_curves and transition > 0.0 and transition < transition_limit - 1.0e-6:
            messages.append(f"[TRANSITION] IP#{index} Ls={transition:.3f}m < min {transition_limit:.3f}m.")

    for index in range(len(rows) - 1):
        a = rows[index]
        b = rows[index + 1]
        length = _distance(a["x"], a["y"], b["x"], b["y"])
        if length < tangent_limit - 1.0e-6:
            messages.append(f"[TANGENT] Segment {index + 1}-{index + 2} length={length:.3f}m < min {tangent_limit:.3f}m.")

    if any(float(row.get("radius", 0.0) or 0.0) > 0.0 for row in rows):
        messages.append("[INFO] v1 compiles PI curves as sampled station geometry; full analytic clothoid objects remain a follow-up task.")
    if superelevation_pct < 0.0 or side_friction <= 0.0:
        messages.append("[CRITERIA] Superelevation and side friction inputs should be positive.")
    return messages


def _ip_rows_from_element_rows(rows: list[dict[str, object]]) -> list[dict[str, float]]:
    out: list[dict[str, float]] = []
    for row in rows:
        x_values = _csv_float_row(row.get("x_values", ""))
        y_values = _csv_float_row(row.get("y_values", ""))
        count = min(len(x_values), len(y_values))
        for index in range(count):
            x = float(x_values[index])
            y = float(y_values[index])
            if out and _distance(out[-1]["x"], out[-1]["y"], x, y) <= 1.0e-6:
                continue
            out.append({"x": x, "y": y, "radius": 0.0, "transition_length": 0.0})
    return out


def _normalized_element_rows(
    alignment,
    rows: list[dict[str, object]],
    *,
    min_rows: int = 1,
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    alignment_id = str(getattr(alignment, "AlignmentId", "") or getattr(alignment, "Name", "") or "alignment:v1")
    for index, row in enumerate(rows):
        station_start = _required_float(row.get("station_start", None), f"Row {index + 1} start station")
        station_end = _required_float(row.get("station_end", None), f"Row {index + 1} end station")
        if station_end < station_start:
            raise ValueError(f"Row {index + 1} end station must be greater than or equal to start station.")
        x_values = _csv_float_row(row.get("x_values", ""))
        y_values = _csv_float_row(row.get("y_values", ""))
        if len(x_values) != len(y_values):
            raise ValueError(f"Row {index + 1} X/Y value counts must match.")
        if len(x_values) < 2:
            raise ValueError(f"Row {index + 1} needs at least two XY points.")
        kind = str(row.get("kind", "") or "tangent").strip() or "tangent"
        element_id = str(row.get("element_id", "") or "").strip()
        if not element_id:
            element_id = f"{alignment_id}:element:{index + 1}"
        normalized.append(
            {
                "element_id": element_id,
                "kind": kind,
                "station_start": station_start,
                "station_end": station_end,
                "length": max(0.0, station_end - station_start),
                "x_values": _format_csv_float_row(x_values),
                "y_values": _format_csv_float_row(y_values),
            }
        )
    if len(normalized) < min_rows:
        raise ValueError(f"Alignment needs at least {min_rows} geometry element row.")
    normalized.sort(key=lambda item: (float(item["station_start"]), float(item["station_end"])))
    return normalized


def _existing_element_id(alignment, row_index: int) -> str:
    ids = list(getattr(alignment, "ElementIds", []) or []) if alignment is not None else []
    if row_index < len(ids):
        return str(ids[row_index] or "")
    return ""


def _float_list(values) -> list[float]:
    result = []
    for value in list(values or []):
        result.append(_optional_float(value) or 0.0)
    return result


def _csv_float_row(text) -> list[float]:
    values = []
    for token in str(text or "").split(","):
        token = token.strip()
        if not token:
            continue
        values.append(_required_float(token, "XY value"))
    return values


def _format_csv_float_row(values: list[float]) -> str:
    return ",".join(_format_float(value) for value in values)


def _required_float(value, label: str) -> float:
    try:
        return float(value)
    except Exception:
        raise ValueError(f"{label} must be a number.") from None


def _optional_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _format_float(value) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "0.000"


def _format_optional_station(value) -> str:
    if value is None:
        return "-"
    return _format_float(value)


def _format_pi_review_line(row: dict[str, object]) -> str:
    curve_bits = [
        f"IP#{int(row.get('ip_index', 0) or 0)}",
        f"kind={str(row.get('kind', '') or '-')}",
        f"XY=({_format_float(row.get('x', 0.0))}, {_format_float(row.get('y', 0.0))})",
        f"R in/app={_format_float(row.get('input_radius', 0.0))}/{_format_float(row.get('applied_radius', 0.0))}",
        f"Ls in/app={_format_float(row.get('input_transition', 0.0))}/{_format_float(row.get('applied_transition', 0.0))}",
    ]
    if bool(row.get("clamped", False)):
        curve_bits.append("clamped=yes")
    if row.get("ts_station", None) is not None or row.get("te_station", None) is not None:
        curve_bits.append(
            "TS/SC/CS/ST="
            f"{_format_optional_station(row.get('ts_station', None))}/"
            f"{_format_optional_station(row.get('sc_station', None))}/"
            f"{_format_optional_station(row.get('cs_station', None))}/"
            f"{_format_optional_station(row.get('te_station', None))}"
        )
        curve_bits.append(f"curve_len={_format_float(row.get('curve_length', 0.0))}")
        curve_bits.append(f"pts={int(row.get('curve_point_count', 0) or 0)}")
    return " | ".join(curve_bits)


def _format_compiled_review_line(row: dict[str, object]) -> str:
    return (
        f"#{int(row.get('index', 0) or 0)} "
        f"{str(row.get('kind', '') or 'tangent')} | "
        f"STA {_format_float(row.get('station_start', 0.0))} -> {_format_float(row.get('station_end', 0.0))} | "
        f"L={_format_float(row.get('length', 0.0))} | "
        f"pts={int(row.get('point_count', 0) or 0)}"
    )


def _distance(x0: float, y0: float, x1: float, y1: float) -> float:
    return math.hypot(float(x1) - float(x0), float(y1) - float(y0))


def _polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(
        _distance(float(a[0]), float(a[1]), float(b[0]), float(b[1]))
        for a, b in zip(points, points[1:])
    )


def _dot_2d(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(a[0]) * float(b[0]) + float(a[1]) * float(b[1])


def _cross_2d(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(a[0]) * float(b[1]) - float(a[1]) * float(b[0])


def _left_normal(v: tuple[float, float]) -> tuple[float, float]:
    return -float(v[1]), float(v[0])


def _vector(x: float, y: float):
    if App is not None and hasattr(App, "Vector"):
        return App.Vector(float(x), float(y), 0.0)
    return type("_Vector", (), {"x": float(x), "y": float(y), "z": 0.0})()


def _shift_last_coordinate_row(text: str, delta: float) -> str:
    values = _csv_float_row(text)
    if not values:
        return "0.0,20.0"
    last = values[-1]
    return _format_csv_float_row([last, last + float(delta)])


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditAlignment", CmdV1AlignmentEditor())
