# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/ui/task_profile_editor.py
import csv
import math
import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_first, find_project
from freecad.Corridor_Road.objects.obj_profile_bundle import ProfileBundle, ViewProviderProfileBundle
from freecad.Corridor_Road.objects.obj_vertical_alignment import VerticalAlignment
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_project import local_to_world, world_to_local
from freecad.Corridor_Road.objects.project_links import link_project
from freecad.Corridor_Road.objects.terrain_sampler import TerrainSampler, is_mesh_object, is_shape_object
from freecad.Corridor_Road.ui.common.coord_ui import coord_hint_text, should_default_world_mode
from freecad.Corridor_Road.ui.common.profile_fg_helpers import (
    PROFILE_BUNDLE_LABEL,
    ensure_fg_display as _ensure_fg_display,
    find_fg_display as _find_fg_display,
    find_profile_bundle as _find_profile_bundle,
    find_stationing as _find_stationing,
    find_vertical_alignment as _find_vertical_alignment,
)


def _find_project(doc):
    return find_project(doc)


def _find_alignment(doc):
    return find_first(doc, name_prefixes=("HorizontalAlignment",))


def _find_terrain_sources(doc):
    out = []
    if doc is None:
        return out
    for o in doc.Objects:
        if is_mesh_object(o) or is_shape_object(o):
            out.append(o)
    return out


def _selected_terrain():
    try:
        sel = list(Gui.Selection.getSelection() or [])
        for o in sel:
            if is_mesh_object(o) or is_shape_object(o):
                return o
    except Exception:
        pass
    return None


def _try_float(value):
    try:
        if value is None:
            return None
        txt = str(value).strip()
        if txt == "":
            return None
        return float(txt)
    except Exception:
        return None


def _normalize_fg_header(text: str) -> str:
    raw = str(text or "").strip().lower()
    if not raw:
        return ""
    keep = []
    for ch in raw:
        if ch.isalnum():
            keep.append(ch)
    return "".join(keep)


class ProfileEditorTaskPanel:
    """
    Refactored Profile Editor:

    - ProfileBundle holds data: Stations/ElevEG/ElevFG/Delta.
    - ProfileBundle only draws EG (optional).
    - FGDisplay draws FG (optional).

    UI:
      - Table: Station, EG, FG, Delta
      - FG mode:
          * FG from VerticalAlignment (preferred): FG column is auto-populated and read-only.
          * Manual FG: FG column editable.
      - Display options:
          * Show EG wire -> ProfileBundle.ShowEGWire
          * Show FG wire -> FGDisplay.ShowWire
          * EG Z offset -> ProfileBundle.WireZOffset
          * FG Z offset -> FGDisplay.ZOffset
    """

    def __init__(self):
        self.doc = App.ActiveDocument

        # prevent AttributeError during UI build
        self.bundle = None
        self.project = None
        self.alignment = None
        self.stationing = None
        self.va = None
        self.fgdisp = None
        self._terrains = []
        self._coord_mode_initialized = False

        self._loading = False
        self.form = self._build_ui()

        self._refresh_context()
        self._load_from_document()

    # ---- TaskPanel protocol ----
    def getStandardButtons(self):
        return 0

    def accept(self):
        Gui.Control.closeDialog()

    def reject(self):
        Gui.Control.closeDialog()

    # ---- UI ----
    def _build_ui(self):
        w = QtWidgets.QWidget()
        w.setWindowTitle("CorridorRoad - Edit Profiles (Data/EG)")

        root = QtWidgets.QVBoxLayout(w)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # Top info
        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        root.addWidget(self.lbl_info)

        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setWordWrap(True)
        root.addWidget(self.lbl_status)

        self.lbl_fg_banner = QtWidgets.QLabel("")
        self.lbl_fg_banner.setWordWrap(True)
        self.lbl_fg_banner.setMargin(6)
        root.addWidget(self.lbl_fg_banner)

        self.lbl_state = QtWidgets.QLabel("")
        self.lbl_state.setWordWrap(True)
        root.addWidget(self.lbl_state)

        # Options group
        gb = QtWidgets.QGroupBox("Options")
        form = QtWidgets.QFormLayout(gb)

        self.chk_create_bundle = QtWidgets.QCheckBox("Create ProfileBundle if missing")
        self.chk_create_bundle.setChecked(True)

        self.chk_fg_from_va = QtWidgets.QCheckBox("FG from VerticalAlignment (lock FG column)")
        self.chk_fg_from_va.setChecked(True)

        self.chk_show_eg = QtWidgets.QCheckBox("Show EG wire (ProfileBundle)")
        self.chk_show_eg.setChecked(True)

        self.chk_show_fg = QtWidgets.QCheckBox("Show FG wire (Finished Grade (FG))")
        self.chk_show_fg.setChecked(True)

        self.spin_eg_zoff = QtWidgets.QDoubleSpinBox()
        self.spin_eg_zoff.setRange(-1e9, 1e9)
        self.spin_eg_zoff.setDecimals(3)
        self.spin_eg_zoff.setValue(0.0)

        self.spin_fg_zoff = QtWidgets.QDoubleSpinBox()
        self.spin_fg_zoff.setRange(-1e9, 1e9)
        self.spin_fg_zoff.setDecimals(3)
        self.spin_fg_zoff.setValue(0.0)

        self.cmb_eg_terrain = QtWidgets.QComboBox()
        self.cmb_terrain_coords = QtWidgets.QComboBox()
        self.cmb_terrain_coords.addItems(["Local (X/Y)", "World (E/N)"])
        self.lbl_coord_hint = QtWidgets.QLabel("")
        self.lbl_coord_hint.setWordWrap(True)
        self.btn_pick_terrain = QtWidgets.QPushButton("Use Selected Terrain")
        self.btn_apply = QtWidgets.QPushButton("Apply")
        self.btn_close = QtWidgets.QPushButton("Close")
        self.btn_open_pvi = QtWidgets.QPushButton("Open Edit PVI")
        self.btn_refresh_fg_from_va = QtWidgets.QPushButton("Refresh FG from VerticalAlignment")
        self.btn_import_fg = QtWidgets.QPushButton("Import FG CSV")
        self.btn_fg_wizard = QtWidgets.QPushButton("FG Wizard")

        form.addRow(self.chk_create_bundle)
        form.addRow(self.chk_fg_from_va)
        form.addRow(self.chk_show_eg)
        form.addRow(self.chk_show_fg)
        form.addRow("EG Z Offset:", self.spin_eg_zoff)
        form.addRow("FG Z Offset:", self.spin_fg_zoff)
        form.addRow("EG Terrain Source:", self.cmb_eg_terrain)
        row_coord_mode = QtWidgets.QHBoxLayout()
        row_coord_mode.addWidget(self.cmb_terrain_coords)
        row_coord_mode.addWidget(self.lbl_coord_hint, 1)
        w_coord_mode = QtWidgets.QWidget()
        w_coord_mode.setLayout(row_coord_mode)
        form.addRow("EG Terrain Coords:", w_coord_mode)
        form.addRow(self.btn_pick_terrain)
        row_nav = QtWidgets.QHBoxLayout()
        row_nav.addWidget(self.btn_open_pvi)
        row_nav.addWidget(self.btn_refresh_fg_from_va)
        w_nav = QtWidgets.QWidget()
        w_nav.setLayout(row_nav)
        form.addRow(w_nav)
        row_apply = QtWidgets.QHBoxLayout()
        row_apply.addWidget(self.btn_apply)
        row_apply.addWidget(self.btn_close)
        w_apply = QtWidgets.QWidget()
        w_apply.setLayout(row_apply)
        form.addRow(w_apply)

        root.addWidget(gb)

        gb_table = QtWidgets.QGroupBox("Profile Table")
        vtable = QtWidgets.QVBoxLayout(gb_table)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Station", "EG", "FG", "Delta (FG-EG)"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        vtable.addWidget(self.table)

        self.lbl_table_summary = QtWidgets.QLabel("")
        self.lbl_table_summary.setWordWrap(True)
        vtable.addWidget(self.lbl_table_summary)

        # Buttons row
        btn_row_top = QtWidgets.QHBoxLayout()
        btn_row_bottom = QtWidgets.QHBoxLayout()
        btn_rows = QtWidgets.QVBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Row")
        self.btn_remove = QtWidgets.QPushButton("Remove Row")
        self.btn_sort = QtWidgets.QPushButton("Sort by Station")
        self.btn_fill_stations = QtWidgets.QPushButton("Fill Stations from Stationing")
        self.btn_fill_fg_from_va = QtWidgets.QPushButton("Fill FG from VerticalAlignment")

        btn_row_top.addWidget(self.btn_add)
        btn_row_top.addWidget(self.btn_remove)
        btn_row_top.addWidget(self.btn_sort)
        btn_row_top.addWidget(self.btn_fill_stations)
        btn_row_bottom.addWidget(self.btn_fill_fg_from_va)
        btn_row_bottom.addWidget(self.btn_import_fg)
        btn_row_bottom.addWidget(self.btn_fg_wizard)
        btn_row_top.addStretch(1)
        btn_row_bottom.addStretch(1)
        btn_rows.addLayout(btn_row_top)
        btn_rows.addLayout(btn_row_bottom)
        vtable.addLayout(btn_rows)
        root.addWidget(gb_table)

        # Signals
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_sort.clicked.connect(self._sort_rows)
        self.btn_fill_stations.clicked.connect(self._fill_stations_from_stationing)
        self.btn_fill_fg_from_va.clicked.connect(self._fill_fg_from_va)
        self.btn_import_fg.clicked.connect(self._import_fg_from_file)
        self.btn_fg_wizard.clicked.connect(self._open_fg_wizard)
        self.btn_refresh_fg_from_va.clicked.connect(self._refresh_fg_from_va)
        self.btn_pick_terrain.clicked.connect(self._use_selected_terrain)
        self.btn_apply.clicked.connect(self._apply_changes)
        self.btn_close.clicked.connect(self.reject)
        self.btn_open_pvi.clicked.connect(self._open_edit_pvi)
        self.cmb_terrain_coords.currentIndexChanged.connect(self._on_terrain_coord_mode_changed)
        self.cmb_eg_terrain.currentIndexChanged.connect(self._on_terrain_source_changed)

        self.chk_fg_from_va.toggled.connect(self._on_fg_mode_toggled)
        self.table.itemChanged.connect(self._on_table_item_changed)

        # Start with a few empty rows
        self._set_rows(3)

        return w

    def _use_world_terrain_mode(self):
        return int(self.cmb_terrain_coords.currentIndex()) == 1

    def _coord_context_obj(self):
        if self.project is not None:
            return self.project
        return self.doc

    def _update_coord_hint(self):
        self.lbl_coord_hint.setText(coord_hint_text(self._coord_context_obj()))

    def _apply_default_coord_mode(self):
        if self._coord_mode_initialized:
            return
        self._loading = True
        try:
            if should_default_world_mode(self._coord_context_obj()):
                self.cmb_terrain_coords.setCurrentIndex(1)
            else:
                self.cmb_terrain_coords.setCurrentIndex(0)
        finally:
            self._loading = False
        self._coord_mode_initialized = True

    def _on_terrain_coord_mode_changed(self):
        if self._loading:
            return
        self._update_coord_hint()

    def _terrain_declared_world_mode(self, terrain_obj):
        if terrain_obj is None:
            return None
        try:
            mode = str(getattr(terrain_obj, "OutputCoords", "") or "")
            if mode == "World":
                return True
            if mode == "Local":
                return False
        except Exception:
            pass
        try:
            if getattr(terrain_obj, "Proxy", None) and getattr(terrain_obj.Proxy, "Type", "") == "PointCloudDEM":
                return False
        except Exception:
            pass
        return None

    def _sync_coord_mode_from_selected_terrain(self):
        terr = self._current_terrain()
        auto_world = self._terrain_declared_world_mode(terr)
        if auto_world is None:
            return
        self._loading = True
        try:
            self.cmb_terrain_coords.setCurrentIndex(1 if auto_world else 0)
        finally:
            self._loading = False

    def _effective_use_world_mode(self, terrain_obj):
        auto_world = self._terrain_declared_world_mode(terrain_obj)
        if auto_world is not None:
            return bool(auto_world)
        return self._use_world_terrain_mode()

    def _on_terrain_source_changed(self, *_args):
        if self._loading:
            return
        self._sync_coord_mode_from_selected_terrain()
        self._update_coord_hint()

    def _refresh_status_summary(self):
        fg_mode = "From VerticalAlignment" if bool(self.chk_fg_from_va.isChecked()) and self.va is not None else "Manual"
        va_linked = "Yes" if self.va is not None else "No"
        terr = self._current_terrain()
        if terr is not None:
            eg_src = terr.Label
        elif self.project is not None and getattr(self.project, "Terrain", None) is not None:
            eg_src = getattr(self.project.Terrain, "Label", "Project Terrain")
        else:
            eg_src = "None"

        self.lbl_status.setText(
            "\n".join(
                [
                    f"FG mode: {fg_mode}",
                    f"VerticalAlignment linked: {va_linked}",
                    f"EG source: {eg_src}",
                ]
            )
        )

        if bool(self.chk_fg_from_va.isChecked()) and self.va is not None:
            self.lbl_fg_banner.setStyleSheet("QLabel { background-color: #274b30; color: #f2f7f2; border: 1px solid #3e6d49; }")
            self.lbl_fg_banner.setText("FG is controlled by VerticalAlignment. The FG column is locked and table FG values follow the current vertical alignment.")
        else:
            self.lbl_fg_banner.setStyleSheet("QLabel { background-color: #4b3320; color: #fff6ec; border: 1px solid #6f4d32; }")
            self.lbl_fg_banner.setText("FG is in manual mode. Editing the FG column can diverge from VerticalAlignment until you refresh or switch the lock back on.")
        self._update_table_summary()

    def _update_table_summary(self):
        total = 0
        missing_eg = 0
        missing_fg = 0
        pos_delta = 0
        neg_delta = 0
        zero_delta = 0
        for r in range(self.table.rowCount()):
            sta = self._get_cell_float(r, 0)
            if sta is None:
                continue
            total += 1
            eg = self._get_cell_float(r, 1)
            fg = self._get_cell_float(r, 2)
            if eg is None:
                missing_eg += 1
            if fg is None:
                missing_fg += 1
            if eg is None or fg is None:
                continue
            d = float(fg - eg)
            if d > 1e-9:
                pos_delta += 1
            elif d < -1e-9:
                neg_delta += 1
            else:
                zero_delta += 1
        self.lbl_table_summary.setText(
            f"Rows with stations: {total} | Missing EG: {missing_eg} | Missing FG: {missing_fg} | "
            f"Delta > 0: {pos_delta} | Delta < 0: {neg_delta} | Delta = 0: {zero_delta}"
        )

    def _open_edit_pvi(self):
        try:
            from freecad.Corridor_Road.ui.task_pvi_editor import PviEditorTaskPanel

            Gui.Control.closeDialog()
            Gui.Control.showDialog(PviEditorTaskPanel())
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Edit Profiles", f"Could not open Edit PVI: {ex}")

    def _refresh_fg_from_va(self):
        if self.va is None:
            QtWidgets.QMessageBox.information(None, "Edit Profiles", "VerticalAlignment was not found. Open Edit PVI first.")
            return
        self._fill_fg_from_va(force=True)
        updated = 0
        for r in range(self.table.rowCount()):
            if self._get_cell_float(r, 0) is not None and self._get_cell_float(r, 2) is not None:
                updated += 1
        self._refresh_status_summary()
        QtWidgets.QMessageBox.information(
            None,
            "Edit Profiles",
            f"FG refreshed from VerticalAlignment.\nUpdated stations: {updated}\nFG source: VerticalAlignment",
        )

    def _ensure_manual_fg_mode(self, action_label: str) -> bool:
        if not bool(self.chk_fg_from_va.isChecked()):
            return True
        resp = QtWidgets.QMessageBox.question(
            None,
            "Edit Profiles",
            f"{action_label} writes manual FG values.\nSwitch FG mode from VerticalAlignment to Manual and continue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes,
        )
        if resp != QtWidgets.QMessageBox.Yes:
            return False
        self.chk_fg_from_va.setChecked(False)
        return True

    def _table_station_bounds(self):
        vals = []
        for r in range(self.table.rowCount()):
            sta = self._get_cell_float(r, 0)
            if sta is not None:
                vals.append(float(sta))
        if not vals:
            return 0.0, 0.0
        return min(vals), max(vals)

    @staticmethod
    def _parse_fg_import_file(path: str):
        if not path or not os.path.isfile(path):
            raise Exception("FG import file was not found.")

        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            sample = fh.read(2048)
            fh.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except Exception:
                class _SimpleDialect(csv.Dialect):
                    delimiter = ","
                    quotechar = '"'
                    doublequote = True
                    skipinitialspace = True
                    lineterminator = "\n"
                    quoting = csv.QUOTE_MINIMAL

                dialect = _SimpleDialect
            reader = csv.reader(fh, dialect)
            raw_rows = []
            for row in reader:
                vals = [str(v).strip() for v in list(row or [])]
                if not vals or all(v == "" for v in vals):
                    continue
                if str(vals[0]).strip().startswith("#"):
                    continue
                raw_rows.append(vals)

        if not raw_rows:
            raise Exception("FG import file has no usable rows.")

        station_aliases = {
            "station",
            "sta",
            "chainage",
            "pk",
            "kp",
            "distance",
            "dist",
        }
        fg_aliases = {
            "fg",
            "finishedgrade",
            "finishedgr",
            "finishedelevation",
            "fgelevation",
            "elevfg",
            "designfg",
            "designgrade",
            "designelevation",
            "grade",
            "z",
            "elevation",
        }

        first = list(raw_rows[0] or [])
        first_station = _try_float(first[0] if len(first) >= 1 else None)
        first_fg = _try_float(first[1] if len(first) >= 2 else None)
        has_header = (first_station is None) or (first_fg is None)

        station_idx = 0
        fg_idx = 1
        rows = list(raw_rows)
        if has_header:
            header = [_normalize_fg_header(v) for v in first]
            station_idx = -1
            fg_idx = -1
            for i, key in enumerate(header):
                if key in station_aliases and station_idx < 0:
                    station_idx = i
                if key in fg_aliases and fg_idx < 0:
                    fg_idx = i
            if station_idx < 0 and len(header) >= 1:
                station_idx = 0
            if fg_idx < 0 and len(header) >= 2:
                fg_idx = 1 if station_idx != 1 else (2 if len(header) >= 3 else -1)
            rows = rows[1:]

        if station_idx < 0 or fg_idx < 0:
            raise Exception("FG import file must include station and FG columns.")

        parsed = []
        seen = {}
        for row in rows:
            if max(station_idx, fg_idx) >= len(row):
                continue
            sta = _try_float(row[station_idx])
            fg = _try_float(row[fg_idx])
            if sta is None or fg is None:
                continue
            key = round(float(sta), 6)
            seen[key] = (float(sta), float(fg))

        parsed = [seen[k] for k in sorted(seen)]
        if not parsed:
            raise Exception("FG import file did not yield any valid Station/FG rows.")
        return parsed

    def _apply_imported_fg_rows(self, imported_rows):
        rows = list(imported_rows or [])
        if not rows:
            return 0, 0

        existing_station_rows = []
        for r in range(self.table.rowCount()):
            sta = self._get_cell_float(r, 0)
            if sta is None:
                continue
            existing_station_rows.append((r, float(sta)))

        self._loading = True
        updated = 0
        appended = 0
        try:
            if not existing_station_rows:
                self.table.setRowCount(0)
                self._set_rows(len(rows))
                for i, (sta, fg) in enumerate(rows):
                    self._set_cell_float(i, 0, sta)
                    self._set_cell_text(i, 1, "")
                    self._set_cell_float(i, 2, fg)
                    self._update_delta_row(i)
                updated = len(rows)
                return updated, 0

            row_by_station = {round(float(sta), 6): int(r) for r, sta in existing_station_rows}
            for sta, fg in rows:
                key = round(float(sta), 6)
                if key in row_by_station:
                    r = row_by_station[key]
                    self._set_cell_float(r, 2, fg)
                    self._update_delta_row(r)
                    updated += 1
                else:
                    r = self.table.rowCount()
                    self._set_rows(r + 1)
                    self._set_cell_float(r, 0, sta)
                    self._set_cell_text(r, 1, "")
                    self._set_cell_float(r, 2, fg)
                    self._update_delta_row(r)
                    row_by_station[key] = r
                    appended += 1
        finally:
            self._loading = False

        self._sort_rows()
        self._update_table_summary()
        return updated, appended

    def _import_fg_from_file(self):
        if not self._ensure_manual_fg_mode("FG import"):
            return
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Import FG CSV",
            "",
            "CSV Files (*.csv *.txt);;All Files (*.*)",
        )
        if not path:
            return
        try:
            rows = self._parse_fg_import_file(path)
            updated, appended = self._apply_imported_fg_rows(rows)
            self._refresh_status_summary()
            QtWidgets.QMessageBox.information(
                None,
                "Edit Profiles",
                f"FG import completed.\nFile: {os.path.basename(path)}\nRows read: {len(rows)}\nUpdated existing stations: {updated}\nAppended new stations: {appended}",
            )
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Edit Profiles", f"FG import failed: {ex}")

    def _apply_fg_wizard_values(self, mode: str, start_station: float, end_station: float, start_value: float, end_value: float):
        mode_key = str(mode or "").strip().lower()
        s0 = float(min(start_station, end_station))
        s1 = float(max(start_station, end_station))
        if abs(s1 - s0) <= 1e-9:
            s1 = s0

        updated = 0
        skipped_missing_eg = 0
        self._loading = True
        try:
            for r in range(self.table.rowCount()):
                sta = self._get_cell_float(r, 0)
                if sta is None:
                    continue
                sta = float(sta)
                if sta < (s0 - 1e-9) or sta > (s1 + 1e-9):
                    continue
                t = 0.0 if abs(s1 - s0) <= 1e-9 else ((sta - s0) / (s1 - s0))
                eg = self._get_cell_float(r, 1)
                fg = None
                if mode_key == "eg_offset":
                    if eg is None:
                        skipped_missing_eg += 1
                        continue
                    fg = float(eg) + float(start_value)
                elif mode_key == "eg_offset_ramp":
                    if eg is None:
                        skipped_missing_eg += 1
                        continue
                    delta = float(start_value) + (float(end_value) - float(start_value)) * t
                    fg = float(eg) + delta
                elif mode_key == "absolute_interp":
                    fg = float(start_value) + (float(end_value) - float(start_value)) * t
                else:
                    raise Exception(f"Unsupported FG wizard mode: {mode}")
                self._set_cell_float(r, 2, fg)
                self._update_delta_row(r)
                updated += 1
        finally:
            self._loading = False
        self._update_table_summary()
        return updated, skipped_missing_eg

    def _open_fg_wizard(self):
        if not self._ensure_manual_fg_mode("FG wizard"):
            return

        smin, smax = self._table_station_bounds()
        dlg = QtWidgets.QDialog(None)
        dlg.setWindowTitle("FG Wizard")
        lay = QtWidgets.QVBoxLayout(dlg)
        form = QtWidgets.QFormLayout()

        cmb_mode = QtWidgets.QComboBox()
        cmb_mode.addItem("EG + constant offset", "eg_offset")
        cmb_mode.addItem("EG + start/end offset ramp", "eg_offset_ramp")
        cmb_mode.addItem("Absolute FG interpolation", "absolute_interp")

        spin_s0 = QtWidgets.QDoubleSpinBox()
        spin_s0.setRange(-1e9, 1e9)
        spin_s0.setDecimals(3)
        spin_s0.setValue(float(smin))
        spin_s1 = QtWidgets.QDoubleSpinBox()
        spin_s1.setRange(-1e9, 1e9)
        spin_s1.setDecimals(3)
        spin_s1.setValue(float(smax))
        spin_v0 = QtWidgets.QDoubleSpinBox()
        spin_v0.setRange(-1e9, 1e9)
        spin_v0.setDecimals(3)
        spin_v0.setValue(0.0)
        spin_v1 = QtWidgets.QDoubleSpinBox()
        spin_v1.setRange(-1e9, 1e9)
        spin_v1.setDecimals(3)
        spin_v1.setValue(0.0)

        lbl_v0 = QtWidgets.QLabel("Offset:")
        lbl_v1 = QtWidgets.QLabel("End Offset:")
        lbl_hint = QtWidgets.QLabel("")
        lbl_hint.setWordWrap(True)

        form.addRow("Mode:", cmb_mode)
        form.addRow("Start Station:", spin_s0)
        form.addRow("End Station:", spin_s1)
        form.addRow(lbl_v0, spin_v0)
        form.addRow(lbl_v1, spin_v1)
        lay.addLayout(form)
        lay.addWidget(lbl_hint)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        lay.addWidget(btn_box)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)

        def _refresh_mode_widgets():
            mode_key = str(cmb_mode.currentData() or "eg_offset")
            if mode_key == "eg_offset":
                lbl_v0.setText("Offset:")
                lbl_v1.setText("End Offset:")
                spin_v1.setEnabled(False)
                lbl_hint.setText("Sets FG = EG + offset for all rows in the selected station range.")
            elif mode_key == "eg_offset_ramp":
                lbl_v0.setText("Start Offset:")
                lbl_v1.setText("End Offset:")
                spin_v1.setEnabled(True)
                lbl_hint.setText("Interpolates offset along the station range, then sets FG = EG + interpolated offset.")
            else:
                lbl_v0.setText("Start FG:")
                lbl_v1.setText("End FG:")
                spin_v1.setEnabled(True)
                lbl_hint.setText("Ignores EG and linearly interpolates absolute FG values across the selected station range.")

        cmb_mode.currentIndexChanged.connect(_refresh_mode_widgets)
        _refresh_mode_widgets()

        if dlg.exec_() != int(QtWidgets.QDialog.Accepted):
            return

        try:
            updated, skipped_missing_eg = self._apply_fg_wizard_values(
                str(cmb_mode.currentData() or "eg_offset"),
                float(spin_s0.value()),
                float(spin_s1.value()),
                float(spin_v0.value()),
                float(spin_v1.value()),
            )
            self._refresh_status_summary()
            msg = f"FG wizard applied.\nUpdated rows: {updated}"
            if skipped_missing_eg > 0:
                msg += f"\nSkipped rows missing EG: {skipped_missing_eg}"
            QtWidgets.QMessageBox.information(None, "Edit Profiles", msg)
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Edit Profiles", f"FG wizard failed: {ex}")

    # ---- Context ----
    def _refresh_context(self):
        if self.doc is None:
            self.bundle = None
            self.project = None
            self.alignment = None
            self.stationing = None
            self.va = None
            self._terrains = []
            self.lbl_info.setText("No active document.")
            return

        self.bundle = _find_profile_bundle(self.doc)
        self.project = _find_project(self.doc)
        self.alignment = None
        try:
            if self.project is not None and hasattr(self.project, "Alignment"):
                self.alignment = getattr(self.project, "Alignment", None)
        except Exception:
            self.alignment = None
        if self.alignment is None:
            self.alignment = _find_alignment(self.doc)
        self.stationing = _find_stationing(self.doc)
        self.va = _find_vertical_alignment(self.doc)
        self._terrains = _find_terrain_sources(self.doc)
        self._apply_default_coord_mode()
        self._update_coord_hint()

        self.fgdisp = None
        if self.va is not None:
            self.fgdisp = _ensure_fg_display(self.doc, self.va)
        else:
            self.fgdisp = _find_fg_display(self.doc)

        msg = []
        msg.append(f"ProfileBundle: {'FOUND' if self.bundle else 'NOT FOUND'}")
        msg.append(f"HorizontalAlignment: {'FOUND' if self.alignment else 'NOT FOUND'}")
        msg.append(f"Stationing: {'FOUND' if self.stationing else 'NOT FOUND'}")
        msg.append(f"VerticalAlignment: {'FOUND' if self.va else 'NOT FOUND'}")
        msg.append(f"Terrain sources: {len(self._terrains)} found (Mesh/Shape)")
        msg.append(f"EG terrain coord mode: {'World (E/N)' if self._use_world_terrain_mode() else 'Local (X/Y)'}")
        msg.append("")
        msg.append("Policy:")
        msg.append("- EG wire is drawn by ProfileBundle.")
        msg.append("- FG wire is drawn by Finished Grade (FG) display object.")
        self.lbl_info.setText("\n".join(msg))

        pref_terrain = None
        if self.project is not None and hasattr(self.project, "Terrain"):
            pref_terrain = getattr(self.project, "Terrain", None)
        if pref_terrain is None:
            pref_terrain = _selected_terrain()
        self._fill_terrain_combo(selected=pref_terrain)
        self._sync_coord_mode_from_selected_terrain()
        self.cmb_eg_terrain.setEnabled(bool(self._terrains))
        self.btn_pick_terrain.setEnabled(bool(self._terrains))
        self.btn_apply.setEnabled(True)
        self.btn_open_pvi.setEnabled(True)

        # default FG-from-VA checkbox based on VA existence
        if self.va is None:
            self.chk_fg_from_va.setChecked(False)

        self.btn_fill_fg_from_va.setEnabled(self.va is not None)
        self.btn_refresh_fg_from_va.setEnabled(self.va is not None)
        self._refresh_status_summary()
    # ---- Table helpers ----

    def _set_rows(self, n):
        self._loading = True
        try:
            self.table.setRowCount(n)
            for r in range(n):
                for c in range(4):
                    if self.table.item(r, c) is None:
                        it = QtWidgets.QTableWidgetItem("")
                        self.table.setItem(r, c, it)

            # Delta column always read-only
            for r in range(n):
                it = self.table.item(r, 3)
                it.setFlags(it.flags() & ~QtCore.Qt.ItemIsEditable)
        finally:
            self._loading = False

        self._apply_fg_lock()

    def _get_cell_text(self, r, c):
        it = self.table.item(r, c)
        return (it.text() if it else "") or ""

    def _set_cell_text(self, r, c, txt):
        it = self.table.item(r, c)
        if it is None:
            it = QtWidgets.QTableWidgetItem("")
            self.table.setItem(r, c, it)

        it.setText(txt)

    def _get_cell_float(self, r, c):
        txt = self._get_cell_text(r, c).strip()
        if txt == "":
            return None
        try:
            return float(txt)
        except Exception:
            return None

    def _set_cell_float(self, r, c, v):
        self._set_cell_text(r, c, f"{float(v):.3f}")

    def _apply_fg_lock(self):
        lock = bool(self.chk_fg_from_va.isChecked())

        # attribute-safe guard
        va = getattr(self, "va", None)
        if va is None:
            lock = False

        # if there is no VA, cannot lock
        if self.va is None:
            lock = False

        self._loading = True
        try:
            for r in range(self.table.rowCount()):
                fg_item = self.table.item(r, 2)
                if fg_item is None:
                    fg_item = QtWidgets.QTableWidgetItem("")
                    self.table.setItem(r, 2, fg_item)

                flags = fg_item.flags()
                if lock:
                    fg_item.setFlags(flags & ~QtCore.Qt.ItemIsEditable)
                else:
                    fg_item.setFlags(flags | QtCore.Qt.ItemIsEditable)
        finally:
            self._loading = False

    def _format_terrain_obj(self, obj):
        tag = "Mesh" if is_mesh_object(obj) else "Shape"
        return f"[{tag}] {obj.Label} ({obj.Name})"

    def _fill_terrain_combo(self, selected=None):
        self.cmb_eg_terrain.clear()
        for i, o in enumerate(self._terrains):
            self.cmb_eg_terrain.addItem(self._format_terrain_obj(o), i)
        if not self._terrains:
            return
        idx = 0
        if selected is not None:
            for i, o in enumerate(self._terrains):
                if o == selected:
                    idx = i
                    break
        self.cmb_eg_terrain.setCurrentIndex(idx)

    def _current_terrain(self):
        i = int(self.cmb_eg_terrain.currentIndex())
        if i < 0 or i >= len(self._terrains):
            return None
        return self._terrains[i]

    def _use_selected_terrain(self):
        sel = _selected_terrain()
        if sel is None:
            QtWidgets.QMessageBox.information(
                None,
                "Edit Profiles",
                "No terrain source selected. Select a Mesh/Shape object first.",
            )
            return
        for i, o in enumerate(self._terrains):
            if o == sel:
                self.cmb_eg_terrain.setCurrentIndex(i)
                return
        self._refresh_context()

    # ---- Actions ----
    def _add_row(self):
        self._set_rows(self.table.rowCount() + 1)
        self._update_table_summary()

    def _remove_row(self):
        r = self.table.currentRow()
        if r < 0:
            r = self.table.rowCount() - 1
        if r >= 0:
            self.table.removeRow(r)
        self._update_table_summary()

    def _sort_rows(self):
        rows = self._read_table_rows(keep_blanks=True)
        rows.sort(key=lambda x: x[0])

        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(len(rows))
            for i, (s, eg, fg) in enumerate(rows):
                self._set_cell_float(i, 0, s)
                if eg is None:
                    self._set_cell_text(i, 1, "")
                else:
                    self._set_cell_float(i, 1, eg)
                if fg is None:
                    self._set_cell_text(i, 2, "")
                else:
                    self._set_cell_float(i, 2, fg)
                self._update_delta_row(i)
        finally:
            self._loading = False

    def _fill_stations_from_stationing(self):
        if self.stationing is None or not hasattr(self.stationing, "StationValues"):
            raise Exception("Stationing.StationValues not found. Run Generate Stations first.")

        st = list(self.stationing.StationValues or [])
        if len(st) < 2:
            raise Exception("Stationing has fewer than 2 stations.")

        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(len(st))
            for i, s in enumerate(st):
                self._set_cell_float(i, 0, float(s))
                # keep EG/FG empty for now
                self._set_cell_text(i, 1, "")
                self._set_cell_text(i, 2, "")
                self._set_cell_text(i, 3, "")
        finally:
            self._loading = False

        # If FG locked, auto-fill from VA
        self._fill_fg_from_va()
        self._update_table_summary()

    def _fill_eg_from_terrain(self, overwrite: bool = True, show_message: bool = True, terrain_obj=None):
        if self.alignment is None:
            raise Exception("HorizontalAlignment not found.")
        terr = terrain_obj if terrain_obj is not None else self._current_terrain()
        if terr is None:
            raise Exception("No terrain source selected.")

        sampler = TerrainSampler.from_object(terr, max_triangles=300000)
        if sampler is None:
            raise Exception("Failed to build terrain sampler from selected source.")

        def _terrain_bounds_xy(src_obj):
            try:
                if is_mesh_object(src_obj):
                    bb = src_obj.Mesh.BoundBox
                else:
                    bb = src_obj.Shape.BoundBox
                return float(bb.XMin), float(bb.XMax), float(bb.YMin), float(bb.YMax)
            except Exception:
                return None

        def _estimate_fallback_step(samp):
            try:
                tris = list(getattr(samp, "triangles", []) or [])
                if not tris:
                    return 1.0
                xmin = min(t[3][0] for t in tris)
                xmax = max(t[3][1] for t in tris)
                ymin = min(t[3][2] for t in tris)
                ymax = max(t[3][3] for t in tris)
                area = max(1e-9, float(xmax - xmin) * float(ymax - ymin))
                n_cells = max(1.0, 0.5 * float(len(tris)))
                return max(0.5, min(50.0, math.sqrt(area / n_cells)))
            except Exception:
                return 1.0

        def _sample_with_fallback(samp, x, y, bounds_xy=None, step=2.0):
            z0 = samp.z_at(float(x), float(y))
            if z0 is not None:
                return z0, False

            dirs = (
                (1.0, 0.0),
                (-1.0, 0.0),
                (0.0, 1.0),
                (0.0, -1.0),
                (0.7071, 0.7071),
                (0.7071, -0.7071),
                (-0.7071, 0.7071),
                (-0.7071, -0.7071),
            )
            max_rings = 4
            step_use = max(0.2, float(step))
            max_radius = float(max_rings) * step_use

            if bounds_xy is not None:
                xmin, xmax, ymin, ymax = bounds_xy
                if (x < xmin - max_radius) or (x > xmax + max_radius) or (y < ymin - max_radius) or (y > ymax + max_radius):
                    return None, False

            best = None
            best_d2 = None
            for ring in range(1, max_rings + 1):
                r = float(ring) * step_use
                for dx, dy in dirs:
                    qx = float(x) + float(dx) * r
                    qy = float(y) + float(dy) * r
                    if bounds_xy is not None:
                        xmin, xmax, ymin, ymax = bounds_xy
                        if qx < xmin - 1e-9 or qx > xmax + 1e-9 or qy < ymin - 1e-9 or qy > ymax + 1e-9:
                            continue
                    zz = samp.z_at(qx, qy)
                    if zz is None:
                        continue
                    d2 = float((qx - x) * (qx - x) + (qy - y) * (qy - y))
                    if best is None or d2 < best_d2:
                        best = float(zz)
                        best_d2 = d2
                if best is not None:
                    return best, True
            return None, False

        sampled = 0
        nodata = 0
        sampled_fallback = 0
        use_world_mode = self._effective_use_world_mode(terr)
        bounds_xy = _terrain_bounds_xy(terr)
        fallback_step = _estimate_fallback_step(sampler)
        self._loading = True
        try:
            for r in range(self.table.rowCount()):
                s = self._get_cell_float(r, 0)
                if s is None:
                    continue
                eg_old = self._get_cell_float(r, 1)
                if (not overwrite) and (eg_old is not None):
                    continue
                p = HorizontalAlignment.point_at_station(self.alignment, float(s))
                qx = float(p.x)
                qy = float(p.y)
                if use_world_mode:
                    qx, qy, _qz = local_to_world(self._coord_context_obj(), qx, qy, float(p.z))
                z, used_fallback = _sample_with_fallback(
                    sampler,
                    float(qx),
                    float(qy),
                    bounds_xy=bounds_xy,
                    step=fallback_step,
                )
                if z is None:
                    nodata += 1
                    continue
                if used_fallback:
                    sampled_fallback += 1
                z_local = float(z)
                if use_world_mode:
                    _lx, _ly, z_local = world_to_local(self._coord_context_obj(), float(qx), float(qy), float(z))
                self._set_cell_float(r, 1, float(z_local))
                self._update_delta_row(r)
                sampled += 1
        finally:
            self._loading = False

        if sampled <= 0:
            raise Exception("No EG elevations sampled from terrain. Check terrain coverage and station range.")

        try:
            if self.project is not None and hasattr(self.project, "Terrain"):
                self.project.Terrain = terr
        except Exception:
            pass

        if show_message:
            msg = f"EG filled from terrain: {sampled} rows"
            if sampled_fallback > 0:
                msg += f", fallback: {sampled_fallback}"
            if nodata > 0:
                msg += f", no-data: {nodata} rows"
            QtWidgets.QMessageBox.information(None, "Edit Profiles", msg)
        self._update_table_summary()

    def _apply_changes(self):
        try:
            terr = self._current_terrain()
            if terr is not None and self.alignment is not None:
                self._fill_eg_from_terrain(overwrite=True, show_message=False, terrain_obj=terr)
            self._save_to_document()
            self._refresh_status_summary()
            total = 0
            for r in range(self.table.rowCount()):
                if self._get_cell_float(r, 0) is not None:
                    total += 1
            QtWidgets.QMessageBox.information(
                None,
                "Edit Profiles",
                f"Applied.\nRows with stations: {total}\nFG mode: {'VerticalAlignment' if bool(self.chk_fg_from_va.isChecked()) and self.va is not None else 'Manual'}",
            )
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Edit Profiles", f"Apply failed: {ex}")

    def _fill_fg_from_va(self, force: bool = False):
        if self.va is None:
            return

        # only fill if lock mode is on (to avoid surprising overwrites)
        if (not force) and (not self.chk_fg_from_va.isChecked()):
            return

        self._loading = True
        try:
            for r in range(self.table.rowCount()):
                s = self._get_cell_float(r, 0)
                if s is None:
                    continue
                z = float(VerticalAlignment.elevation_at_station(self.va, float(s)))
                self._set_cell_float(r, 2, z)
                self._update_delta_row(r)
        finally:
            self._loading = False
        self._update_table_summary()

    def _on_table_item_changed(self, item):
        if self._loading:
            return

        r = item.row()
        c = item.column()

        if c in (0, 1, 2):
            # If FG is locked from VA, station change should re-fill FG
            if c != 2 and self.chk_fg_from_va.isChecked() and self.va is not None:
                self._fill_fg_from_va()

            # If user edits FG manually (FG column) while NOT locked => hide FG wire
            if c == 2:
                if (not self.chk_fg_from_va.isChecked()) and (self.va is not None):
                    # user is manually editing FG -> force-hide FG wire to avoid mismatch
                    self._ensure_fg_hidden("FG cell edited manually")

            self._update_delta_row(r)
            self._update_table_summary()

    def _update_delta_row(self, r):
        it = self.table.item(r, 3)
        if it is None:
            it = QtWidgets.QTableWidgetItem("")
            self.table.setItem(r, 3, it)

        eg = self._get_cell_float(r, 1)
        fg = self._get_cell_float(r, 2)

        if eg is None or fg is None:
            self._set_cell_text(r, 3, "")
            it.setBackground(QtGui.QColor("#2a2d33"))
            it.setToolTip("Delta is unavailable until both EG and FG are filled.")
            self._update_table_summary()
            return

        delta = float(fg - eg)
        self._set_cell_float(r, 3, delta)
        it = self.table.item(r, 3)
        if delta > 1e-9:
            it.setBackground(QtGui.QColor("#284733"))
            it.setToolTip("Positive delta: FG is above EG.")
        elif delta < -1e-9:
            it.setBackground(QtGui.QColor("#4a3424"))
            it.setToolTip("Negative delta: FG is below EG.")
        else:
            it.setBackground(QtGui.QColor("#38404a"))
            it.setToolTip("Zero delta: FG equals EG.")
        self._update_table_summary()

    # ---- Load/Save ----
    def _load_from_document(self):
        # read current objects again
        self._refresh_context()

        # load display options
        if self.bundle is not None:
            try:
                self.chk_show_eg.setChecked(bool(self.bundle.ShowEGWire))
            except Exception:
                pass
            try:
                self.spin_eg_zoff.setValue(float(getattr(self.bundle, "WireZOffset", 0.0)))
            except Exception:
                pass

        # if self.va is not None:
        #     try:
        #         self.chk_show_fg.setChecked(bool(getattr(self.va, "ShowFGWire", True)))
        #     except Exception:
        #         pass
        #     try:
        #         self.spin_fg_zoff.setValue(float(getattr(self.va, "FGWireZOffset", 0.0)))
        #     except Exception:
        #         pass

        if self.fgdisp is not None:
            try:
                self.chk_show_fg.setChecked(bool(getattr(self.fgdisp, "ShowWire", True)))
            except Exception:
                pass
            try:
                self.spin_fg_zoff.setValue(float(getattr(self.fgdisp, "ZOffset", 0.0)))
            except Exception:
                pass
        else:
            try:
                # If FGDisplay is missing, keep FG display option off.
                self.chk_show_fg.setChecked(False)
            except Exception:
                pass

            # self.chk_show_fg.setChecked(False)

        # Restore FG mode from bundle state
        try:
            if self.bundle is not None and hasattr(self.bundle, "FGIsManual"):
                is_manual = bool(self.bundle.FGIsManual)
                # if manual => uncheck FG-from-VA
                self.chk_fg_from_va.setChecked(not is_manual and (self.va is not None))
        except Exception:
            pass

        # load table
        if self.bundle is None:
            # if Stationing exists, preload stations
            if self.stationing is not None and hasattr(self.stationing, "StationValues"):
                st = list(self.stationing.StationValues or [])
                if len(st) >= 2:
                    self._loading = True
                    try:
                        self.table.setRowCount(0)
                        self._set_rows(len(st))
                        for i, s in enumerate(st):
                            self._set_cell_float(i, 0, float(s))
                            self._set_cell_text(i, 1, "")
                            self._set_cell_text(i, 2, "")
                            self._set_cell_text(i, 3, "")
                    finally:
                        self._loading = False

                    self._fill_fg_from_va()

            self._refresh_status_summary()
            return

        st = list(getattr(self.bundle, "Stations", []) or [])
        eg = list(getattr(self.bundle, "ElevEG", []) or [])
        fg = list(getattr(self.bundle, "ElevFG", []) or [])
        n = min(len(st), len(eg), len(fg))

        if n < 1:
            return

        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(n)
            for i in range(n):
                self._set_cell_float(i, 0, float(st[i]))
                self._set_cell_float(i, 1, float(eg[i]))
                self._set_cell_float(i, 2, float(fg[i]))
                self._update_delta_row(i)
        finally:
            self._loading = False

        # if locked FG and VA exists, override FG display values from VA
        self._fill_fg_from_va()
        self._refresh_status_summary()

    def _read_table_rows(self, keep_blanks: bool):
        """
        Return list of (station, eg, fg) rows.
        - Station is required; EG/FG blanks become None if keep_blanks=True, else skipped/0 handling is outside.
        """
        rows = []
        for r in range(self.table.rowCount()):
            s = self._get_cell_float(r, 0)
            if s is None:
                continue

            eg = self._get_cell_float(r, 1)
            fg = self._get_cell_float(r, 2)

            if keep_blanks:
                rows.append((float(s), eg, fg))
            else:
                # if EG/FG missing, skip row
                if eg is None or fg is None:
                    continue
                rows.append((float(s), float(eg), float(fg)))

        return rows

    def _get_or_create_bundle(self):
        b = self.bundle
        if b is not None:
            return b

        if not self.chk_create_bundle.isChecked():
            raise Exception("ProfileBundle missing. Enable 'Create ProfileBundle if missing' or create it first.")

        b = self.doc.addObject("Part::FeaturePython", "ProfileBundle")
        ProfileBundle(b)
        if getattr(b, "ViewObject", None) is not None:
            ViewProviderProfileBundle(b.ViewObject)
        b.Label = PROFILE_BUNDLE_LABEL
        self.bundle = b

        return b

    def _save_to_document(self):
        if self.doc is None:
            return

        terr_sel = self._current_terrain()
        self._refresh_context()

        b = self._get_or_create_bundle()
        va = self.va  # may be None

        try:
            if terr_sel is not None and self.project is not None and hasattr(self.project, "Terrain"):
                self.project.Terrain = terr_sel
        except Exception:
            pass

        # Safety net: prevent empty EG cells from being serialized as 0
        # when a valid terrain source and alignment are available.
        terr_for_eg = terr_sel
        if terr_for_eg is None and self.project is not None and hasattr(self.project, "Terrain"):
            terr_for_eg = getattr(self.project, "Terrain", None)
        if terr_for_eg is not None and self.alignment is not None:
            try:
                self._fill_eg_from_terrain(overwrite=False, show_message=False, terrain_obj=terr_for_eg)
            except Exception:
                pass

        # Read stations + EG + FG
        # Policy:
        # - Station required
        # - EG blank -> 0.0 (you can change this policy later)
        # - FG:
        #     * If FG-from-VA enabled and VA exists => compute from VA
        #     * Else read from table; blank -> 0.0
        rows = self._read_table_rows(keep_blanks=True)
        if len(rows) < 2:
            raise Exception("Need at least 2 rows with Station values.")

        rows.sort(key=lambda x: x[0])
        stations = [r[0] for r in rows]

        # EG
        eg_list = []
        for _, eg, _ in rows:
            eg_list.append(float(eg) if eg is not None else 0.0)

        # FG
        fg_list = []
        if self.chk_fg_from_va.isChecked() and va is not None:
            for s in stations:
                fg_list.append(float(VerticalAlignment.elevation_at_station(va, float(s))))
        else:
            for _, _, fg in rows:
                fg_list.append(float(fg) if fg is not None else 0.0)

        # Save to ProfileBundle (data)
        b.Stations = [float(s) for s in stations]
        b.ElevEG = eg_list
        b.ElevFG = fg_list

        # Link to VA if exists
        try:
            b.VerticalAlignment = va
        except Exception:
            pass

        # Display options
        try:
            b.ShowEGWire = bool(self.chk_show_eg.isChecked())
        except Exception:
            pass

        # Persist FG source state (UX consistency across sessions)
        try:
            if self.chk_fg_from_va.isChecked() and va is not None:
                b.FGIsManual = False
            else:
                b.FGIsManual = True
                if self.fgdisp is not None:
                    self.fgdisp.ShowWire = False
                    try:
                        self.chk_show_fg.setChecked(False)
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            b.WireZOffset = float(self.spin_eg_zoff.value())
        except Exception:
            pass

        if self.fgdisp is not None:
            try:
                self.fgdisp.ShowWire = bool(self.chk_show_fg.isChecked())
            except Exception:
                pass
            try:
                self.fgdisp.ZOffset = float(self.spin_fg_zoff.value())
            except Exception:
                pass

            self.fgdisp.touch()

        b.touch()
        if self.fgdisp is not None:
            self.fgdisp.touch()
        self.doc.recompute()

        prj = self.project if self.project is not None else find_project(self.doc)
        if prj is not None:
            links = {}
            if terr_sel is not None:
                links["Terrain"] = terr_sel
            link_project(
                prj,
                links=links,
                links_if_empty={"Alignment": self.alignment, "Stationing": self.stationing},
                adopt_extra=[b, self.fgdisp, va, terr_sel],
            )

        # b.touch()
        # if va is not None:
        #     va.touch()

        # self.doc.recompute()

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass

    def _set_state_text(self, txt):
        try:
            self.lbl_state.setText(txt)
        except Exception:
            pass

    # def _ensure_va_fg_hidden(self, reason=""):
    #     # Hard rule: when manual FG, VA FG must be hidden to avoid mismatch UX
    #     if self.va is None:
    #         return

    #     try:
    #         self.chk_show_fg.setChecked(False)
    #     except Exception:
    #         pass

    #     try:
    #         self.va.ShowFGWire = False
    #         self.va.touch()
    #     except Exception:
    #         pass

    #     if reason:
    #         self._set_state_text(f"Manual FG mode: hiding VerticalAlignment FG wire. ({reason})")
    #     else:
    #         self._set_state_text("Manual FG mode: hiding VerticalAlignment FG wire.")
    def _ensure_fg_hidden(self, reason=""):
        # Hard rule: when manual FG, FG display must be hidden to avoid mismatch UX
        if self.fgdisp is None:
            return

        try:
            self.chk_show_fg.setChecked(False)
        except Exception:
            pass

        try:
            self.fgdisp.ShowWire = False
            self.fgdisp.touch()
        except Exception:
            pass

        if reason:
            self._set_state_text(f"Manual FG mode: hiding Finished Grade (FG) wire. ({reason})")
        else:
            self._set_state_text("Manual FG mode: hiding Finished Grade (FG) wire.")

    # def _ensure_va_fg_shown(self, reason=""):
    #     if self.va is None:
    #         return

    #     try:
    #         self.chk_show_fg.setChecked(True)
    #     except Exception:
    #         pass

    #     try:
    #         self.va.ShowFGWire = True
    #         self.va.touch()
    #     except Exception:
    #         pass

    #     if reason:
    #         self._set_state_text(f"FG from VerticalAlignment: showing VA FG wire. ({reason})")
    #     else:
    #         self._set_state_text("FG from VerticalAlignment: showing VA FG wire.")
    def _ensure_fg_shown(self, reason=""):
        if self.fgdisp is None:
            return

        try:
            self.chk_show_fg.setChecked(True)
        except Exception:
            pass

        try:
            self.fgdisp.ShowWire = True
            self.fgdisp.touch()
        except Exception:
            pass

        if reason:
            self._set_state_text(f"FG from VerticalAlignment: showing Finished Grade (FG) wire. ({reason})")
        else:
            self._set_state_text("FG from VerticalAlignment: showing Finished Grade (FG) wire.")

    def _on_fg_mode_toggled(self, checked):
        # checked=True => FG from VA mode
        self._apply_fg_lock()
        self._refresh_status_summary()

        # UX guardrails
        if checked and self.va is not None:
            # Switch to VA-driven FG
            self.btn_fill_fg_from_va.setEnabled(True)
            self.btn_refresh_fg_from_va.setEnabled(True)

            # Force show VA FG (so user sees the "source of truth")
            # self._ensure_va_fg_shown("mode toggled on")
            self._ensure_fg_shown("mode toggled on")

            # Also refresh FG values on table to match VA (prevents stale manual numbers)
            self._fill_fg_from_va()

        else:
            # Manual FG mode OR no VA
            self.btn_fill_fg_from_va.setEnabled(False)
            self.btn_refresh_fg_from_va.setEnabled(self.va is not None)

            # Prevent mismatch: hide VA FG wire immediately
            # self._ensure_va_fg_hidden("mode toggled off (manual FG)")
            self._ensure_fg_hidden("mode toggled off (manual FG)")
