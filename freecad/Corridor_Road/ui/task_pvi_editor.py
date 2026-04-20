# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/ui/task_pvi_editor.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.doc_query import find_project
from freecad.Corridor_Road.objects.obj_vertical_alignment import VerticalAlignment, ViewProviderVerticalAlignment
from freecad.Corridor_Road.objects.obj_profile_bundle import ProfileBundle, ViewProviderProfileBundle
from freecad.Corridor_Road.objects.project_links import link_project
from freecad.Corridor_Road.ui.common.profile_fg_helpers import (
    PROFILE_BUNDLE_LABEL,
    ensure_fg_display as _ensure_fg_display,
    find_profile_bundle as _find_profile_bundle,
    find_stationing as _find_stationing,
    find_vertical_alignment as _find_vertical_alignment,
)


class PviEditorTaskPanel:
    """
    PVI editor + FG generator (linear grades only).
    """

    def __init__(self):
        self.doc = App.ActiveDocument
        self._loading = False
        self._starter_source_name = ""
        self.form = self._build_ui()
        self._try_load_existing_va()

    # ---- TaskPanel API ----
    def getStandardButtons(self):
        return 0

    def accept(self):
        Gui.Control.closeDialog()

    def reject(self):
        Gui.Control.closeDialog()

    # ---- UI ----
    def _build_ui(self):
        w = QtWidgets.QWidget()
        w.setWindowTitle("CorridorRoad - Edit PVI (Vertical Alignment / FG)")

        main = QtWidgets.QVBoxLayout(w)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(10)

        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setWordWrap(True)
        main.addWidget(self.lbl_status)

        gb_left = QtWidgets.QGroupBox("PVI Input")
        gl = QtWidgets.QVBoxLayout(gb_left)

        self.lbl_pvi_guide = QtWidgets.QLabel(
            "How to fill the table:\n"
            "- Grade Break Station (PVI): station where the incoming and outgoing grades meet\n"
            "- FG Elev at PVI: finished-grade elevation at that same station\n"
            "- Vertical Curve L: total vertical-curve length centered on that PVI\n"
            "  Use 0 for a sharp grade break. L is not the distance to the next row."
        )
        self.lbl_pvi_guide.setWordWrap(True)
        gl.addWidget(self.lbl_pvi_guide)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row2 = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Row")
        self.btn_remove = QtWidgets.QPushButton("Remove Row")
        self.btn_sort = QtWidgets.QPushButton("Sort by Station")
        self.btn_load_starter = QtWidgets.QPushButton("Load Starter PVI")
        self.btn_clear_blank = QtWidgets.QPushButton("Clear to Blank")

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_sort)
        btn_row2.addWidget(self.btn_load_starter)
        btn_row2.addWidget(self.btn_clear_blank)

        gl.addLayout(btn_row)
        gl.addLayout(btn_row2)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Grade Break Station", "FG Elev at PVI", "Vertical Curve L"])
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed)
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 150)
        self.table.setToolTip(
            "Enter grade-break stations in ascending order.\n"
            "PVI elevation is the finished grade at that station.\n"
            "Vertical Curve L is the total curve length centered on the PVI."
        )
        self.table.horizontalHeaderItem(0).setToolTip("Station where the incoming and outgoing grades meet (PVI station).")
        self.table.horizontalHeaderItem(1).setToolTip("Finished-grade elevation at that PVI station.")
        self.table.horizontalHeaderItem(2).setToolTip("Total vertical-curve length L centered on that PVI. Use 0 for no curve.")

        gl.addWidget(self.table)

        self.lbl_pvi_summary = QtWidgets.QLabel("")
        self.lbl_pvi_summary.setWordWrap(True)
        gl.addWidget(self.lbl_pvi_summary)

        gb_right = QtWidgets.QGroupBox("Generate FG")
        gr = QtWidgets.QFormLayout(gb_right)
        self.chk_clamp = QtWidgets.QCheckBox("Clamp overlapping vertical curves (auto adjust L)")
        self.chk_clamp.setChecked(True)

        self.spin_min_tan = QtWidgets.QDoubleSpinBox()
        self.spin_min_tan.setRange(0.0, 100000.0)
        self.spin_min_tan.setDecimals(3)
        self.spin_min_tan.setValue(0.0)

        gr.addRow(self.chk_clamp)
        gr.addRow("Min Tangent:", self.spin_min_tan)

        # self.chk_curves_only = QtWidgets.QCheckBox("FG Curves Only (hide tangents)")
        # self.chk_curves_only.setChecked(False)
        # gr.addRow(self.chk_curves_only)

        self.lbl_info = QtWidgets.QLabel(
            "FG will be generated on Station list:\n"
            "- ProfileBundle.Stations (if exists)\n"
            "- else Stationing.StationValues\n\n"
            "Use Edit PVI when FG should be controlled by vertical geometry.\n"
            "Use Edit Profiles manual FG tools when you want CSV import or quick offset/interpolation workflows."
        )
        self.lbl_info.setWordWrap(True)

        self.chk_create_bundle = QtWidgets.QCheckBox("Create ProfileBundle if missing")
        self.chk_create_bundle.setChecked(True)

        self.chk_keep_eg = QtWidgets.QCheckBox("Keep existing EG values (do not overwrite)")
        self.chk_keep_eg.setChecked(True)

        self.btn_open_profiles = QtWidgets.QPushButton("Open Edit Profiles")
        self.btn_preview = QtWidgets.QPushButton("Preview FG (console)")
        self.btn_generate_only = QtWidgets.QPushButton("Generate FG Now (apply)")
        self.btn_close = QtWidgets.QPushButton("Close")

        gr.addRow(self.lbl_info)
        gr.addRow(self.chk_create_bundle)
        gr.addRow(self.chk_keep_eg)
        gr.addRow(self.btn_open_profiles)
        gr.addRow(self.btn_preview)
        row_apply = QtWidgets.QHBoxLayout()
        row_apply.addWidget(self.btn_generate_only)
        row_apply.addWidget(self.btn_close)
        w_apply = QtWidgets.QWidget()
        w_apply.setLayout(row_apply)
        gr.addRow(w_apply)

        main.addWidget(gb_left)
        main.addWidget(gb_right)

        # Signals
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_sort.clicked.connect(self._sort_rows)
        self.btn_load_starter.clicked.connect(self._load_starter_pvi)
        self.btn_clear_blank.clicked.connect(self._clear_to_blank)
        self.btn_open_profiles.clicked.connect(self._open_edit_profiles)
        self.btn_preview.clicked.connect(self._preview_fg)
        self.btn_generate_only.clicked.connect(self._generate_fg_to_profilebundle)
        self.btn_close.clicked.connect(self.reject)
        self.table.itemChanged.connect(self._on_table_item_changed)

        # Start with 3 blank rows for convenience
        self._set_rows(3)
        self._apply_display_unit_ui()
        self._refresh_pvi_summary()

        return w

    def _display_unit(self) -> str:
        return _units.get_linear_display_unit(self.doc)

    def _apply_display_unit_ui(self):
        unit = self._display_unit()
        self.table.setHorizontalHeaderLabels(
            [
                f"Grade Break Station ({unit})",
                f"FG Elev at PVI ({unit})",
                f"Vertical Curve L ({unit})",
            ]
        )
        self.spin_min_tan.setSuffix(f" {unit}")

    def _display_from_internal(self, value: float) -> float:
        return _units.display_length_from_internal(self.doc, value, use_default="display")

    def _internal_from_display(self, value: float) -> float:
        return _units.internal_length_from_display(self.doc, value, use_default="display")

    def _display_from_meters(self, value: float) -> float:
        return _units.user_length_from_meters(self.doc, value, use_default="display")

    def _meters_from_display(self, value: float) -> float:
        return _units.meters_from_user_length(self.doc, value, use_default="display")

    def _format_display_value(self, value: float, digits: int = 3) -> str:
        return f"{float(value):.{int(digits)}f}"

    def _format_display_with_unit(self, value: float, digits: int = 3) -> str:
        return f"{self._format_display_value(value, digits=digits)} {self._display_unit()}"

    def _starter_load_summary_text(self, rows_count: int, source_name: str) -> str:
        return (
            "Starter PVI loaded.\n"
            f"Rows: {int(rows_count)}\n"
            f"Display unit: {self._display_unit()}\n"
            f"Seed source: {str(source_name or '-')}"
        )

    def _fg_generation_summary_text(self, station_count: int) -> str:
        return (
            "FG generation completed.\n"
            f"Stations updated: {int(station_count)}\n"
            f"Display unit: {self._display_unit()}\n"
            "VerticalAlignment updated.\n"
            "Profiles FG refreshed."
        )

    # ---- Table helpers ----
    def _set_rows(self, n):
        self._loading = True
        try:
            self.table.setRowCount(n)
            for r in range(n):
                for c in range(3):
                    if self.table.item(r, c) is None:
                        it = QtWidgets.QTableWidgetItem("")
                        if c == 0:
                            it.setToolTip("Station where grade changes at this PVI.")
                        elif c == 1:
                            it.setToolTip("Finished-grade elevation at this PVI station.")
                        else:
                            it.setToolTip("Total vertical-curve length L centered on this PVI. Use 0 for no curve.")
                        self.table.setItem(r, c, it)
        finally:
            self._loading = False

    def _get_float(self, r, c):
        it = self.table.item(r, c)
        if it is None:
            return None

        txt = (it.text() or "").strip()
        if txt == "":
            return None

        try:
            return float(txt)
        except Exception:
            return None

    def _set_float(self, r, c, v):
        it = self.table.item(r, c)
        if it is None:
            it = QtWidgets.QTableWidgetItem("")
            self.table.setItem(r, c, it)

        it.setText(f"{float(v):.3f}")

    def _read_pvi(self):
        pairs = []
        for r in range(self.table.rowCount()):
            s = self._get_float(r, 0)
            z = self._get_float(r, 1)
            L = self._get_float(r, 2)
            if s is None or z is None:
                continue

            pairs.append((float(s), float(z), float(L) if L is not None else 0.0))

        pairs.sort(key=lambda x: x[0])
        return pairs

    # ---- Actions ----
    def _add_row(self):
        insert_at = self.table.currentRow()
        if insert_at < 0:
            insert_at = self.table.rowCount() - 1
        insert_at += 1

        self._loading = True
        try:
            self.table.insertRow(insert_at)
            for c in range(3):
                it = QtWidgets.QTableWidgetItem("")
                if c == 0:
                    it.setToolTip("Station where grade changes at this PVI.")
                elif c == 1:
                    it.setToolTip("Finished-grade elevation at this PVI station.")
                else:
                    it.setToolTip("Total vertical-curve length L centered on this PVI. Use 0 for no curve.")
                self.table.setItem(insert_at, c, it)
        finally:
            self._loading = False

        self.table.setCurrentCell(insert_at, 0)
        self._refresh_pvi_summary()

    def _remove_row(self):
        r = self.table.currentRow()
        if r < 0:
            r = self.table.rowCount() - 1

        if r >= 0:
            self.table.removeRow(r)
        self._refresh_pvi_summary()

    def _sort_rows(self):
        pairs = self._read_pvi()
        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(len(pairs))
            for i, (s, z, L) in enumerate(pairs):
                self._set_float(i, 0, s)
                self._set_float(i, 1, z)
                self._set_float(i, 2, L)
        finally:
            self._loading = False
        self._refresh_pvi_summary()

    @staticmethod
    def _station_key(value):
        return round(float(value), 6)

    def _resolve_starter_seed_values(self, station_source, stations_m):
        bundle = _find_profile_bundle(self.doc) if self.doc is not None else None
        if bundle is not None:
            bundle_stations = [float(s) for s in list(getattr(bundle, "Stations", []) or [])]
            if len(bundle_stations) >= 2:
                fg_vals = list(getattr(bundle, "ElevFG", []) or [])
                eg_vals = list(getattr(bundle, "ElevEG", []) or [])
                stations_conv = [_units.meters_from_internal_length(self.doc, float(s)) for s in bundle_stations]
                if len(fg_vals) == len(bundle_stations) and any(abs(float(v)) > 1e-9 for v in fg_vals):
                    return "ProfileBundle FG", {
                        self._station_key(stations_conv[i]): _units.meters_from_internal_length(self.doc, float(fg_vals[i]))
                        for i in range(len(bundle_stations))
                    }
                if len(eg_vals) == len(bundle_stations) and any(abs(float(v)) > 1e-9 for v in eg_vals):
                    return "ProfileBundle EG", {
                        self._station_key(stations_conv[i]): _units.meters_from_internal_length(self.doc, float(eg_vals[i]))
                        for i in range(len(bundle_stations))
                    }
        tag = "Stationing" if station_source == "stationing" else f"Flat {self._format_display_with_unit(0.0)}"
        return tag, {self._station_key(s): 0.0 for s in stations_m}

    def _build_starter_pvi_rows(self):
        station_source, station_values = self._resolve_station_list()
        stations_m = sorted({float(s) for s in station_values})
        if len(stations_m) < 2:
            return [], ""

        chosen_m = [stations_m[0]]
        if len(stations_m) >= 3 and abs(stations_m[-1] - stations_m[0]) > 1e-9:
            interior = [float(s) for s in stations_m[1:-1]]
            if interior:
                target_mid = 0.5 * (stations_m[0] + stations_m[-1])
                mid = min(interior, key=lambda s: abs(float(s) - target_mid))
                if abs(mid - chosen_m[0]) > 1e-9 and abs(stations_m[-1] - mid) > 1e-9:
                    chosen_m.append(mid)
        chosen_m.append(stations_m[-1])

        source_name, value_map = self._resolve_starter_seed_values(station_source, station_values)
        rows = []
        for station_m in chosen_m:
            elev = value_map.get(self._station_key(station_m), 0.0)
            rows.append([float(station_m), float(elev), 0.0])

        if len(rows) >= 3:
            total_range = max(0.0, chosen_m[-1] - chosen_m[0])
            base_length = min(40.0, max(20.0, total_range * 0.10))
            for i in range(1, len(rows) - 1):
                left = max(0.0, chosen_m[i] - chosen_m[i - 1])
                right = max(0.0, chosen_m[i + 1] - chosen_m[i])
                limit = max(0.0, 1.6 * min(left, right))
                rows[i][2] = min(base_length, limit) if limit > 1e-9 else 0.0

        return [(r[0], r[1], r[2]) for r in rows], source_name

    def _apply_pvi_rows(self, rows):
        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(max(3, len(rows)))
            for i, (s, z, L) in enumerate(rows):
                self._set_float(i, 0, s)
                self._set_float(i, 1, z)
                self._set_float(i, 2, L)
            for i in range(len(rows), self.table.rowCount()):
                self.table.item(i, 0).setText("")
                self.table.item(i, 1).setText("")
                self.table.item(i, 2).setText("")
        finally:
            self._loading = False
        self._refresh_pvi_summary()

    def _load_starter_pvi(self, checked=False, show_message=True):
        del checked
        rows, source_name = self._build_starter_pvi_rows()
        if len(rows) < 2:
            if show_message:
                QtWidgets.QMessageBox.information(
                    None,
                    "Edit PVI",
                    "Starter PVI could not be generated.\nCreate Stationing or ProfileBundle first.",
                )
            return False

        display_rows = [
            (
                self._display_from_meters(float(s)),
                self._display_from_meters(float(z)),
                self._display_from_meters(float(L)),
            )
            for s, z, L in rows
        ]
        self._starter_source_name = source_name
        self._apply_pvi_rows(display_rows)
        self._refresh_status_summary()

        if show_message:
            QtWidgets.QMessageBox.information(
                None,
                "Edit PVI",
                self._starter_load_summary_text(len(display_rows), source_name),
            )
        return True

    def _clear_to_blank(self):
        self._starter_source_name = ""
        self._apply_pvi_rows([])
        self._refresh_status_summary()

    def _format_grade_pct(self, z0, z1, s0, s1):
        ds = float(s1) - float(s0)
        if abs(ds) < 1e-12:
            return "n/a"
        return f"{((float(z1) - float(z0)) / ds) * 100.0:+.3f}%"

    def _refresh_pvi_summary(self):
        rows = self._read_pvi()
        if len(rows) < 2:
            self.lbl_pvi_summary.setText(
                "Input guide:\n"
                "- Add at least 2 rows.\n"
                "- Start and end rows usually use `Vertical Curve L = 0`.\n"
                "- Interior rows use `Vertical Curve L` only when you want a smooth vertical curve through that PVI."
            )
            return

        lines = [
            f"Valid PVI rows: {len(rows)}",
            "Preview meaning:",
        ]

        grade_count = min(len(rows) - 1, 3)
        for i in range(grade_count):
            s0, z0, _l0 = rows[i]
            s1, z1, _l1 = rows[i + 1]
            lines.append(
                f"- Grade {i + 1}: {self._format_display_value(s0)} -> {self._format_display_value(s1)} {self._display_unit()} = {self._format_grade_pct(z0, z1, s0, s1)}"
            )

        curve_lines = []
        for i in range(1, min(len(rows) - 1, 4)):
            si, _zi, Li = rows[i]
            Li = max(0.0, float(Li))
            if Li <= 0.0:
                curve_lines.append(f"- PVI @{self._format_display_value(si)} {self._display_unit()}: no vertical curve (L=0 {self._display_unit()})")
            else:
                curve_lines.append(
                    f"- PVI @{self._format_display_value(si)} {self._display_unit()}: "
                    f"L={self._format_display_with_unit(Li)} -> "
                    f"BVC {self._format_display_value(si - 0.5 * Li)}, "
                    f"EVC {self._format_display_value(si + 0.5 * Li)} {self._display_unit()}"
                )

        if curve_lines:
            lines.append("Curve preview:")
            lines.extend(curve_lines)

        self.lbl_pvi_summary.setText("\n".join(lines))

    def _on_table_item_changed(self, _item):
        if self._loading:
            return
        self._refresh_pvi_summary()

    def _refresh_status_summary(self):
        if self.doc is None:
            self.lbl_status.setText("No active document.")
            return
        va = _find_vertical_alignment(self.doc)
        bundle = _find_profile_bundle(self.doc)
        stationing = _find_stationing(self.doc)
        target = bundle.Label if bundle is not None else ("Stationing" if stationing is not None else "None")
        linked = "Yes" if bundle is not None else "No"
        self.lbl_status.setText(
            "\n".join(
                [
                    f"Target ProfileBundle: {target}",
                    f"Linked Profiles: {linked}",
                    f"Display unit: {self._display_unit()}",
                    f"Starter PVI seed: {self._starter_source_name or '-'}",
                    "PVI = grade-break point for FG vertical alignment.",
                    "Generate FG Now will update the profile FG values from the current vertical alignment.",
                ]
            )
        )

    def _open_edit_profiles(self):
        try:
            from freecad.Corridor_Road.ui.task_profile_editor import ProfileEditorTaskPanel

            Gui.Control.closeDialog()
            Gui.Control.showDialog(ProfileEditorTaskPanel())
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Edit PVI", f"Could not open Edit Profiles: {ex}")

    def _try_load_existing_va(self):
        if self.doc is None:
            self._refresh_status_summary()
            return

        self._apply_display_unit_ui()
        va = _find_vertical_alignment(self.doc)
        if va is None:
            self._refresh_status_summary()
            self._refresh_pvi_summary()
            self._load_starter_pvi(show_message=False)
            return

        st = list(getattr(va, "PVIStations", []) or [])
        el = list(getattr(va, "PVIElevations", []) or [])
        Ls = list(getattr(va, "CurveLengths", []) or [])

        n = min(len(st), len(el))
        if n < 1:
            return

        if len(Ls) < n:
            Ls = list(Ls) + [0.0] * (n - len(Ls))
        else:
            Ls = Ls[:n]

        rows = sorted(
            [
                (
                    self._display_from_meters(float(st[i])),
                    self._display_from_meters(float(el[i])),
                    self._display_from_meters(float(Ls[i])),
                )
                for i in range(n)
            ],
            key=lambda x: x[0],
        )

        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(len(rows))
            for i, (s, z, L) in enumerate(rows):
                self._set_float(i, 0, s)
                self._set_float(i, 1, z)
                self._set_float(i, 2, L)
        finally:
            self._loading = False

        try:
            self.chk_clamp.setChecked(bool(getattr(va, "ClampOverlaps", True)))
            self.spin_min_tan.setValue(self._display_from_meters(float(getattr(va, "MinTangent", 0.0))))
        except Exception:
            pass
        self._refresh_status_summary()
        self._refresh_pvi_summary()

    # ---- Save VerticalAlignment ----
    def _save_vertical_alignment(self):
        if self.doc is None:
            return

        rows = self._read_pvi()
        if len(rows) < 2:
            raise Exception("Need at least 2 valid PVI rows (Station & Elev).")

        va = _find_vertical_alignment(self.doc)
        if va is None:
            va = self.doc.addObject("Part::FeaturePython", "VerticalAlignment")
            VerticalAlignment(va)
            if getattr(va, "ViewObject", None) is not None:
                ViewProviderVerticalAlignment(va.ViewObject)
            va.Label = "Vertical Alignment (PVI)"
        _ensure_fg_display(self.doc, va)

        va.ClampOverlaps = bool(self.chk_clamp.isChecked())
        va.MinTangent = self._meters_from_display(float(self.spin_min_tan.value()))
        va.PVIStations = [self._meters_from_display(float(p[0])) for p in rows]
        va.PVIElevations = [self._meters_from_display(float(p[1])) for p in rows]
        va.CurveLengths = [self._meters_from_display(float(p[2])) for p in rows]
        try:
            va.ShowPVIWire = True
            if hasattr(va, "ViewObject") and va.ViewObject is not None:
                va.ViewObject.Visibility = True
        except Exception:
            pass
        va.touch()

        self.doc.recompute()

        prj = find_project(self.doc)
        if prj is not None:
            fgdisp = _ensure_fg_display(self.doc, va)
            st_obj = _find_stationing(self.doc)
            link_project(
                prj,
                links_if_empty={"Stationing": st_obj},
                adopt_extra=[va, fgdisp, st_obj],
            )

    # ---- Generate FG ----
    def _resolve_station_list(self):
        if self.doc is None:
            return "", []

        b = _find_profile_bundle(self.doc)
        if b is not None and getattr(b, "Stations", None):
            st = list(b.Stations or [])
            if len(st) >= 2:
                return "bundle", [_units.meters_from_internal_length(self.doc, float(s)) for s in st]

        st_obj = _find_stationing(self.doc)
        if st_obj is not None and getattr(st_obj, "StationValues", None):
            st = list(st_obj.StationValues or [])
            if len(st) >= 2:
                return "stationing", [float(s) for s in st]

        return "", []

    def _preview_fg(self):
        if self.doc is None:
            return

        # Always persist current UI rows first so preview uses latest edits/scale conversion.
        self._save_vertical_alignment()
        va = _find_vertical_alignment(self.doc)
        if va is None:
            raise Exception("Failed to create/update VerticalAlignment from current PVI table.")

        _station_source, stations = self._resolve_station_list()
        if len(stations) < 2:
            raise Exception("No station list found. Create Stationing or ProfileBundle first.")

        # print first 10 to console
        for s in stations[:10]:
            z = VerticalAlignment.elevation_at_station(va, float(s))
            s_disp = self._display_from_meters(float(s))
            z_disp = self._display_from_meters(float(z))
            App.Console.PrintMessage(
                f"[FG Preview] s={self._format_display_value(s_disp)} {self._display_unit()} -> z={self._format_display_value(z_disp)} {self._display_unit()}\n"
            )

    def _generate_fg_to_profilebundle(self):
        if self.doc is None:
            return

        # Always persist current UI rows first so generated FG reflects latest edits/scale conversion.
        self._save_vertical_alignment()
        va = _find_vertical_alignment(self.doc)
        if va is None:
            raise Exception("Failed to create/update VerticalAlignment from current PVI table.")

        station_source, stations = self._resolve_station_list()
        if len(stations) < 2:
            raise Exception("No station list found. Create Stationing or ProfileBundle first.")

        b = _find_profile_bundle(self.doc)
        if b is None:
            if not self.chk_create_bundle.isChecked():
                raise Exception("ProfileBundle is missing. Enable 'Create ProfileBundle if missing' or create it first.")

            b = self.doc.addObject("Part::FeaturePython", "ProfileBundle")
            ProfileBundle(b)
            if getattr(b, "ViewObject", None) is not None:
                ViewProviderProfileBundle(b.ViewObject)
            b.Label = PROFILE_BUNDLE_LABEL

            # If we created from Stationing, set Stations now
            b.Stations = [_units.internal_length_from_meters(self.doc, float(s)) for s in stations]

            # Create empty EG list (or zeros). We will not overwrite if keep_eg is checked later.
            b.ElevEG = [0.0 for _ in stations]
            b.ShowEGWire = True
            b.WireZOffset = 0.0

        else:
            # If bundle exists but station list differs, we will regenerate based on bundle stations
            stations = [_units.meters_from_internal_length(self.doc, float(s)) for s in list(b.Stations or [])] or list(stations)

        # Compute FG using VerticalAlignment engine
        fg_m = [float(VerticalAlignment.elevation_at_station(va, float(s))) for s in stations]

        # fg.Label = "Finished Grade (FG)"

        # Optionally preserve EG (we only touch EG if it's missing length)
        if self.chk_keep_eg.isChecked():
            eg = list(getattr(b, "ElevEG", []) or [])
            if len(eg) != len(stations):
                b.ElevEG = [0.0 for _ in stations]
        else:
            # If user wants, keep existing if same length, else zeros
            b.ElevEG = list(getattr(b, "ElevEG", []) or [0.0 for _ in stations])
            if len(b.ElevEG) != len(stations):
                b.ElevEG = [0.0 for _ in stations]

        # Save to bundle (data)
        b.Stations = [_units.internal_length_from_meters(self.doc, float(s)) for s in stations]
        b.ElevFG = [_units.internal_length_from_meters(self.doc, float(z)) for z in fg_m]
        try:
            st_obj = _find_stationing(self.doc)
            if st_obj is not None:
                b.Stationing = st_obj
        except Exception:
            st_obj = _find_stationing(self.doc)

        # Link bundle -> vertical alignment (for traceability / future use)
        try:
            b.VerticalAlignment = va
        except Exception:
            pass

        fgdisp = _ensure_fg_display(self.doc, va)
        try:
            fgdisp.ShowWire = True
            fgdisp.touch()
        except Exception:
            pass
        b.touch()
        va.touch()
        self.doc.recompute()

        prj = find_project(self.doc)
        if prj is not None:
            link_project(
                prj,
                links_if_empty={"Stationing": st_obj},
                adopt_extra=[va, b, fgdisp, st_obj],
            )

        QtWidgets.QMessageBox.information(
            None,
            "Edit PVI",
            self._fg_generation_summary_text(len(stations)),
        )
        self._refresh_status_summary()

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass
