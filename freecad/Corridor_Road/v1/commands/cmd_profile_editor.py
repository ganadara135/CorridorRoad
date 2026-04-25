"""v1 profile source editor command."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None
    Gui = None

from freecad.Corridor_Road.qt_compat import QtWidgets

from ...misc.resources import icon_path
from ..objects.obj_alignment import find_v1_alignment
from ..objects.obj_profile import ensure_v1_profile_properties, find_v1_profile
from ..ui.common import run_legacy_command
from .cmd_create_profile import create_v1_sample_profile
from .selection_context import selected_alignment_profile_target


def profile_control_rows(profile) -> list[dict[str, object]]:
    """Return editable PVI rows from a V1Profile object."""

    if profile is None:
        return []
    ensure_v1_profile_properties(profile)
    ids = list(getattr(profile, "ControlPointIds", []) or [])
    stations = _float_list(getattr(profile, "ControlStations", []) or [])
    elevations = _float_list(getattr(profile, "ControlElevations", []) or [])
    kinds = list(getattr(profile, "ControlKinds", []) or [])
    count = max(len(stations), len(elevations), len(ids), len(kinds))
    rows: list[dict[str, object]] = []
    profile_id = str(getattr(profile, "ProfileId", "") or getattr(profile, "Name", "") or "profile:v1")
    for index in range(count):
        rows.append(
            {
                "control_point_id": (
                    str(ids[index])
                    if index < len(ids) and str(ids[index] or "").strip()
                    else f"{profile_id}:pvi:{index + 1}"
                ),
                "station": float(stations[index]) if index < len(stations) else 0.0,
                "elevation": float(elevations[index]) if index < len(elevations) else 0.0,
                "kind": str(kinds[index] if index < len(kinds) and kinds[index] else "pvi"),
            }
        )
    return rows


def apply_profile_control_rows(profile, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Validate, sort, and write PVI rows back to a V1Profile object."""

    if profile is None:
        raise ValueError("No V1Profile object is available.")
    ensure_v1_profile_properties(profile)
    normalized = _normalized_control_rows(profile, rows)
    profile.ControlPointIds = [str(row["control_point_id"]) for row in normalized]
    profile.ControlStations = [float(row["station"]) for row in normalized]
    profile.ControlElevations = [float(row["elevation"]) for row in normalized]
    profile.ControlKinds = [str(row["kind"]) for row in normalized]
    try:
        profile.touch()
    except Exception:
        pass
    return normalized


def build_profile_editor_handoff_context(profile, *, selected_row: dict[str, object] | None = None) -> dict[str, object]:
    """Build Plan/Profile Review context after editing a v1 profile."""

    row = dict(selected_row or {})
    station = _optional_float(row.get("station", None))
    station_label = f"STA {station:.3f}" if station is not None else ""
    return {
        "source": "v1_profile_editor",
        "preferred_station": station,
        "preferred_profile_name": str(getattr(profile, "Name", "") or ""),
        "viewer_context": {
            "source_panel": "v1 Profile Editor",
            "focus_station": station,
            "focus_station_label": station_label,
            "selected_row_label": _selected_row_label(row),
        },
    }


class V1ProfileEditorTaskPanel:
    """Minimal editor for v1 profile control rows."""

    def __init__(self, *, profile=None, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.profile = profile or find_v1_profile(self.document)
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
        widget.setWindowTitle("CorridorRoad v1 - Profile Editor")

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Profile Editor")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self._profile_label = QtWidgets.QLabel(self._profile_summary_text())
        self._profile_label.setStyleSheet("color: #dfe8ff; background: #263142; padding: 6px;")
        layout.addWidget(self._profile_label)

        hint = QtWidgets.QLabel(
            "Edit station/elevation PVI rows. Apply writes directly to the selected V1Profile source object."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._table = QtWidgets.QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Station", "Elevation", "Kind"])
        self._table.setMinimumHeight(190)
        try:
            self._table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        layout.addWidget(self._table)
        self._load_rows()

        edit_row = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add PVI")
        add_button.clicked.connect(self._add_row)
        edit_row.addWidget(add_button)
        delete_button = QtWidgets.QPushButton("Delete Selected")
        delete_button.clicked.connect(self._delete_selected_rows)
        edit_row.addWidget(delete_button)
        sort_button = QtWidgets.QPushButton("Sort by Station")
        sort_button.clicked.connect(self._sort_table_rows)
        edit_row.addWidget(sort_button)
        edit_row.addStretch(1)
        layout.addLayout(edit_row)

        self._status_label = QtWidgets.QLabel("")
        self._status_label.setStyleSheet("color: #9bd19b; background: #142116; padding: 6px;")
        layout.addWidget(self._status_label)

        button_row = QtWidgets.QHBoxLayout()
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        button_row.addWidget(apply_button)
        review_button = QtWidgets.QPushButton("Apply + Review Plan/Profile")
        review_button.clicked.connect(self._apply_and_review)
        button_row.addWidget(review_button)
        open_review_button = QtWidgets.QPushButton("Review Plan/Profile")
        open_review_button.clicked.connect(self._open_review)
        button_row.addWidget(open_review_button)
        button_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        return widget

    def _load_rows(self) -> None:
        rows = profile_control_rows(self.profile)
        self._table.setRowCount(0)
        for row in rows:
            self._append_table_row(row)

    def _append_table_row(self, row: dict[str, object]) -> None:
        row_index = self._table.rowCount()
        self._table.insertRow(row_index)
        values = [
            _format_float(row.get("station", 0.0)),
            _format_float(row.get("elevation", 0.0)),
            str(row.get("kind", "") or "pvi"),
        ]
        for col, value in enumerate(values):
            self._table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))

    def _add_row(self) -> None:
        rows = self._table_rows(allow_empty=False)
        if rows:
            last = rows[-1]
            station = float(last["station"]) + 20.0
            elevation = float(last["elevation"])
        else:
            station = 0.0
            elevation = 0.0
        self._append_table_row({"station": station, "elevation": elevation, "kind": "pvi"})
        self._set_status("Added a new PVI row. Apply when ready.", ok=True)

    def _delete_selected_rows(self) -> None:
        selected = sorted({item.row() for item in list(self._table.selectedItems() or [])}, reverse=True)
        if not selected and self._table.currentRow() >= 0:
            selected = [self._table.currentRow()]
        for row_index in selected:
            self._table.removeRow(row_index)
        self._set_status(f"Deleted {len(selected)} row(s). Apply when ready.", ok=True)

    def _sort_table_rows(self) -> None:
        try:
            rows = _normalized_control_rows(self.profile, self._table_rows(allow_empty=False), min_rows=0)
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            return
        self._table.setRowCount(0)
        for row in rows:
            self._append_table_row(row)
        self._set_status("Rows sorted by station. Apply when ready.", ok=True)

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            normalized = apply_profile_control_rows(self.profile, self._table_rows(allow_empty=False))
            if self.document is not None:
                try:
                    self.document.recompute()
                except Exception:
                    pass
            self._set_status(f"Applied {len(normalized)} PVI row(s) to V1Profile.", ok=True)
            self._profile_label.setText(self._profile_summary_text())
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            return False

    def _apply_and_review(self) -> None:
        if self._apply(close_after=False):
            self._open_review()

    def _open_review(self) -> None:
        context = build_profile_editor_handoff_context(
            self.profile,
            selected_row=self._selected_or_first_row(),
        )
        success, message = run_legacy_command(
            "CorridorRoad_V1ReviewPlanProfile",
            gui_module=Gui,
            objects_to_select=[self.profile],
            context_payload=context,
        )
        self._set_status(message, ok=success)

    def _table_rows(self, *, allow_empty: bool) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row_index in range(self._table.rowCount()):
            station_text = self._item_text(row_index, 0)
            elevation_text = self._item_text(row_index, 1)
            kind_text = self._item_text(row_index, 2) or "pvi"
            if not station_text and not elevation_text and allow_empty:
                continue
            rows.append(
                {
                    "control_point_id": _existing_control_id(self.profile, row_index),
                    "station": _required_float(station_text, f"Row {row_index + 1} station"),
                    "elevation": _required_float(elevation_text, f"Row {row_index + 1} elevation"),
                    "kind": kind_text.strip() or "pvi",
                }
            )
        return rows

    def _selected_or_first_row(self) -> dict[str, object]:
        rows = self._table_rows(allow_empty=True)
        if not rows:
            return {}
        row_index = self._table.currentRow()
        if row_index < 0:
            return rows[0]
        if row_index >= len(rows):
            return rows[0]
        return rows[row_index]

    def _item_text(self, row_index: int, col_index: int) -> str:
        item = self._table.item(row_index, col_index)
        if item is None:
            return ""
        return str(item.text() or "").strip()

    def _profile_summary_text(self) -> str:
        if self.profile is None:
            return "No V1Profile is available."
        return (
            f"Profile: {str(getattr(self.profile, 'Label', '') or getattr(self.profile, 'Name', '') or '')} | "
            f"ProfileId: {str(getattr(self.profile, 'ProfileId', '') or '')} | "
            f"AlignmentId: {str(getattr(self.profile, 'AlignmentId', '') or '')}"
        )

    def _set_status(self, message: str, *, ok: bool) -> None:
        self._status_label.setText(str(message or ""))
        if ok:
            self._status_label.setStyleSheet("color: #bff4bf; background: #142116; padding: 6px;")
        else:
            self._status_label.setStyleSheet("color: #ffd5d5; background: #321818; padding: 6px;")


def run_v1_profile_editor_command():
    """Open the v1 profile editor, creating a sample profile when needed."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    preferred_alignment, preferred_profile = selected_alignment_profile_target(Gui, document)
    profile = find_v1_profile(document, preferred_profile=preferred_profile)
    if profile is None:
        alignment = find_v1_alignment(document, preferred_alignment=preferred_alignment)
        profile = create_v1_sample_profile(document=document, alignment=alignment)
    if Gui is not None:
        try:
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(profile)
        except Exception:
            pass
        Gui.Control.showDialog(V1ProfileEditorTaskPanel(profile=profile, document=document))
    return profile


class CmdV1ProfileEditor:
    """Open the v1 profile source editor."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("profiles.svg"),
            "MenuText": "Edit Profile (v1)",
            "ToolTip": "Edit v1 profile PVI source rows and review the result",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_profile_editor_command()


def _normalized_control_rows(
    profile,
    rows: list[dict[str, object]],
    *,
    min_rows: int = 2,
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    seen_stations: set[float] = set()
    profile_id = str(getattr(profile, "ProfileId", "") or getattr(profile, "Name", "") or "profile:v1")
    for index, row in enumerate(rows):
        station = _required_float(row.get("station", None), f"Row {index + 1} station")
        elevation = _required_float(row.get("elevation", None), f"Row {index + 1} elevation")
        station_key = round(station, 6)
        if station_key in seen_stations:
            raise ValueError(f"Duplicate station is not allowed: {station:.3f}")
        seen_stations.add(station_key)
        kind = str(row.get("kind", "") or "pvi").strip() or "pvi"
        control_id = str(row.get("control_point_id", "") or "").strip()
        if not control_id:
            control_id = f"{profile_id}:pvi:{index + 1}"
        normalized.append(
            {
                "control_point_id": control_id,
                "station": station,
                "elevation": elevation,
                "kind": kind,
            }
        )
    if len(normalized) < min_rows:
        raise ValueError(f"Profile needs at least {min_rows} PVI/control rows.")
    normalized.sort(key=lambda item: float(item["station"]))
    return normalized


def _existing_control_id(profile, row_index: int) -> str:
    ids = list(getattr(profile, "ControlPointIds", []) or []) if profile is not None else []
    if row_index < len(ids):
        return str(ids[row_index] or "")
    return ""


def _float_list(values) -> list[float]:
    result = []
    for value in list(values or []):
        result.append(_optional_float(value) or 0.0)
    return result


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


def _selected_row_label(row: dict[str, object]) -> str:
    if not row:
        return ""
    station = _optional_float(row.get("station", None))
    elevation = _optional_float(row.get("elevation", None))
    kind = str(row.get("kind", "") or "pvi")
    parts = []
    if station is not None:
        parts.append(f"STA {station:.3f}")
    if elevation is not None:
        parts.append(f"FG {elevation:.3f}")
    parts.append(kind)
    return " | ".join(parts)


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditProfile", CmdV1ProfileEditor())
