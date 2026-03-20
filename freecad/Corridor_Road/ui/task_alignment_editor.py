# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.objects import design_standards as _ds
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment, ViewProviderHorizontalAlignment, ensure_alignment_properties
from freecad.Corridor_Road.objects.obj_project import (
    ensure_project_properties,
    find_project,
    get_design_standard,
    get_length_scale,
    local_to_world,
    world_to_local,
)
from freecad.Corridor_Road.objects.project_links import link_project
from freecad.Corridor_Road.objects.csv_alignment_import import inspect_alignment_csv, read_alignment_csv, write_alignment_csv
from freecad.Corridor_Road.objects.sketch_alignment_import import find_sketch_objects, sketch_to_alignment_rows
from freecad.Corridor_Road.ui.common.coord_ui import coord_hint_text, should_default_world_mode


def _find_alignments(doc):
    out = []
    if doc is None:
        return out
    for o in doc.Objects:
        if o.Name.startswith("HorizontalAlignment"):
            out.append(o)
    return out


def _find_assembly_template(doc, project=None):
    if project is not None:
        try:
            asm = getattr(project, "AssemblyTemplate", None)
            if asm is not None:
                return asm
        except Exception:
            pass
    if doc is None:
        return None
    for o in doc.Objects:
        try:
            pr = getattr(o, "Proxy", None)
            if pr is not None and getattr(pr, "Type", "") == "AssemblyTemplate":
                return o
        except Exception:
            pass
        try:
            if str(getattr(o, "Name", "") or "").startswith("AssemblyTemplate"):
                return o
        except Exception:
            pass
    return None


class AlignmentEditorTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self.aln = None
        self.prj = None
        self._alignments = []
        self._sketches = []
        self._csv_columns = []
        self._loading = False
        self._coord_mode_initialized = False
        self._last_apply_warnings = []
        self.form = self._build_ui()
        self._refresh_context()
        self._load_from_doc()

    def getStandardButtons(self):
        return 0

    def accept(self):
        Gui.Control.closeDialog()

    def reject(self):
        Gui.Control.closeDialog()

    def _build_ui(self):
        scale = get_length_scale(self.doc, default=1.0)

        w = QtWidgets.QWidget()
        w.setWindowTitle("CorridorRoad - Edit Alignment")

        root = QtWidgets.QVBoxLayout(w)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        root.addWidget(self.lbl_info)

        row_src = QtWidgets.QHBoxLayout()
        self.cmb_alignment = QtWidgets.QComboBox()
        self.btn_refresh_context = QtWidgets.QPushButton("Refresh Context")
        row_src.addWidget(QtWidgets.QLabel("Alignment:"))
        row_src.addWidget(self.cmb_alignment, 1)
        row_src.addWidget(self.btn_refresh_context)
        root.addLayout(row_src)

        row_sketch = QtWidgets.QHBoxLayout()
        self.cmb_sketch = QtWidgets.QComboBox()
        self.cmb_sketch_mode = QtWidgets.QComboBox()
        self.cmb_sketch_mode.addItems(["Replace Table", "Append Rows"])
        self.btn_load_sketch = QtWidgets.QPushButton("Load from Sketch")
        row_sketch.addWidget(QtWidgets.QLabel("Sketch:"))
        row_sketch.addWidget(self.cmb_sketch, 1)
        row_sketch.addWidget(self.cmb_sketch_mode)
        row_sketch.addWidget(self.btn_load_sketch)
        root.addLayout(row_sketch)

        row_csv = QtWidgets.QHBoxLayout()
        self.ed_csv_path = QtWidgets.QLineEdit()
        self.ed_csv_path.setPlaceholderText("Path to alignment CSV file")
        self.btn_browse_csv = QtWidgets.QPushButton("Browse CSV")
        self.btn_inspect_csv = QtWidgets.QPushButton("Inspect CSV")
        self.cmb_csv_mode = QtWidgets.QComboBox()
        self.cmb_csv_mode.addItems(["Replace Table", "Append Rows"])
        self.btn_load_csv = QtWidgets.QPushButton("Load from CSV")
        self.btn_save_csv = QtWidgets.QPushButton("Save CSV")
        row_csv.addWidget(QtWidgets.QLabel("CSV:"))
        row_csv.addWidget(self.ed_csv_path, 1)
        row_csv.addWidget(self.btn_browse_csv)
        row_csv.addWidget(self.btn_inspect_csv)
        row_csv.addWidget(self.cmb_csv_mode)
        row_csv.addWidget(self.btn_load_csv)
        row_csv.addWidget(self.btn_save_csv)
        root.addLayout(row_csv)

        gb_csv = QtWidgets.QGroupBox("CSV Import Options")
        fcsv = QtWidgets.QFormLayout(gb_csv)

        self.cmb_csv_coord = QtWidgets.QComboBox()
        self.cmb_csv_coord.addItems(["Use Panel Mode", "Local", "World"])
        self.cmb_csv_sort = QtWidgets.QComboBox()
        self.cmb_csv_sort.addItems(["Input Order", "By STA", "By X/Y"])
        self.cmb_csv_encoding = QtWidgets.QComboBox()
        self.cmb_csv_encoding.addItems(["Auto", "UTF-8-SIG", "CP949", "UTF-8", "Latin-1"])
        self.cmb_csv_delim = QtWidgets.QComboBox()
        self.cmb_csv_delim.addItems(["Auto", "Comma (,)", "Semicolon (;)", "Tab", "Pipe (|)"])
        self.cmb_csv_header = QtWidgets.QComboBox()
        self.cmb_csv_header.addItems(["Auto", "Yes", "No"])

        self.chk_csv_drop_dup = QtWidgets.QCheckBox("Drop consecutive duplicates")
        self.chk_csv_drop_dup.setChecked(True)
        self.chk_csv_clamp = QtWidgets.QCheckBox("Clamp negative Radius/Ls to 0")
        self.chk_csv_clamp.setChecked(True)
        self.chk_csv_end0 = QtWidgets.QCheckBox("Force endpoint Radius/Ls = 0")
        self.chk_csv_end0.setChecked(True)

        self.cmb_csv_map_x = QtWidgets.QComboBox()
        self.cmb_csv_map_y = QtWidgets.QComboBox()
        self.cmb_csv_map_r = QtWidgets.QComboBox()
        self.cmb_csv_map_ls = QtWidgets.QComboBox()
        self.cmb_csv_map_sta = QtWidgets.QComboBox()
        self._reset_csv_mapping_combos()

        fcsv.addRow("CSV Coords:", self.cmb_csv_coord)
        fcsv.addRow("Sort:", self.cmb_csv_sort)
        fcsv.addRow("Encoding:", self.cmb_csv_encoding)
        fcsv.addRow("Delimiter:", self.cmb_csv_delim)
        fcsv.addRow("Has Header:", self.cmb_csv_header)
        fcsv.addRow("Map X:", self.cmb_csv_map_x)
        fcsv.addRow("Map Y:", self.cmb_csv_map_y)
        fcsv.addRow("Map Radius:", self.cmb_csv_map_r)
        fcsv.addRow("Map Transition Ls:", self.cmb_csv_map_ls)
        fcsv.addRow("Map STA (optional):", self.cmb_csv_map_sta)
        fcsv.addRow(self.chk_csv_drop_dup)
        fcsv.addRow(self.chk_csv_clamp)
        fcsv.addRow(self.chk_csv_end0)
        root.addWidget(gb_csv)

        row_coord = QtWidgets.QHBoxLayout()
        self.cmb_coord_mode = QtWidgets.QComboBox()
        self.cmb_coord_mode.addItems(["Local (X/Y)", "World (E/N)"])
        self.lbl_coord_hint = QtWidgets.QLabel("")
        self.lbl_coord_hint.setWordWrap(True)
        row_coord.addWidget(QtWidgets.QLabel("Coord Input:"))
        row_coord.addWidget(self.cmb_coord_mode)
        row_coord.addWidget(self.lbl_coord_hint, 1)
        root.addLayout(row_coord)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["X", "Y", "Radius (m)", "Transition Ls (m)"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        root.addWidget(self.table)

        row_btns = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Row")
        self.btn_del = QtWidgets.QPushButton("Remove Row")
        self.btn_sort = QtWidgets.QPushButton("Sort by X/Y")
        row_btns.addWidget(self.btn_add)
        row_btns.addWidget(self.btn_del)
        row_btns.addWidget(self.btn_sort)
        root.addLayout(row_btns)

        gb_opts = QtWidgets.QGroupBox("Geometry / Criteria")
        form = QtWidgets.QFormLayout(gb_opts)

        self.chk_create = QtWidgets.QCheckBox("Create HorizontalAlignment if missing")
        self.chk_create.setChecked(True)
        self.chk_use_trans = QtWidgets.QCheckBox("Use transition curves (S-C-S)")
        self.chk_use_trans.setChecked(True)

        self.spin_spiral_segments = QtWidgets.QSpinBox()
        self.spin_spiral_segments.setRange(4, 128)
        self.spin_spiral_segments.setValue(16)

        self.spin_v = QtWidgets.QDoubleSpinBox()
        self.spin_v.setRange(0.0, 300.0)
        self.spin_v.setDecimals(1)
        self.spin_v.setValue(60.0)
        self.spin_v.setSuffix(" km/h")

        self.spin_e = QtWidgets.QDoubleSpinBox()
        self.spin_e.setRange(0.0, 20.0)
        self.spin_e.setDecimals(2)
        self.spin_e.setValue(8.0)
        self.spin_e.setSuffix(" %")

        self.spin_f = QtWidgets.QDoubleSpinBox()
        self.spin_f.setRange(0.01, 0.40)
        self.spin_f.setDecimals(3)
        self.spin_f.setValue(0.15)

        self.spin_min_r = QtWidgets.QDoubleSpinBox()
        self.spin_min_r.setRange(0.0, 100000.0)
        self.spin_min_r.setDecimals(3)
        self.spin_min_r.setValue(0.0)
        self.spin_min_r.setToolTip("0 = auto from V/e/f")

        self.spin_min_tan = QtWidgets.QDoubleSpinBox()
        self.spin_min_tan.setRange(0.0, 100000.0)
        self.spin_min_tan.setDecimals(3)
        self.spin_min_tan.setValue(20.0 * scale)

        self.spin_min_ls = QtWidgets.QDoubleSpinBox()
        self.spin_min_ls.setRange(0.0, 100000.0)
        self.spin_min_ls.setDecimals(3)
        self.spin_min_ls.setValue(20.0 * scale)

        self.cmb_design_standard = QtWidgets.QComboBox()
        self.cmb_design_standard.addItems(list(_ds.SUPPORTED_STANDARDS))

        form.addRow(self.chk_create)
        form.addRow(self.chk_use_trans)
        form.addRow("Design standard:", self.cmb_design_standard)
        form.addRow("Spiral segments:", self.spin_spiral_segments)
        form.addRow("Design speed:", self.spin_v)
        form.addRow("Superelevation e:", self.spin_e)
        form.addRow("Side friction f:", self.spin_f)
        form.addRow("Min radius (override):", self.spin_min_r)
        form.addRow("Min tangent length:", self.spin_min_tan)
        form.addRow("Min transition length:", self.spin_min_ls)
        root.addWidget(gb_opts)

        rep_row = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("Apply Alignment")
        self.btn_refresh = QtWidgets.QPushButton("Refresh Criteria Report")
        self.btn_close = QtWidgets.QPushButton("Close")
        rep_row.addWidget(self.btn_apply)
        rep_row.addWidget(self.btn_refresh)
        rep_row.addWidget(self.btn_close)
        root.addLayout(rep_row)

        self.txt_report = QtWidgets.QPlainTextEdit()
        self.txt_report.setReadOnly(True)
        self.txt_report.setPlaceholderText("Criteria messages will appear here after recompute.")
        root.addWidget(self.txt_report)

        self.btn_add.clicked.connect(self._add_row)
        self.btn_del.clicked.connect(self._remove_row)
        self.btn_sort.clicked.connect(self._sort_rows)
        self.btn_apply.clicked.connect(self._apply_changes)
        self.btn_refresh.clicked.connect(self._refresh_report)
        self.btn_close.clicked.connect(self.reject)
        self.cmb_alignment.currentIndexChanged.connect(self._on_alignment_changed)
        self.btn_refresh_context.clicked.connect(self._on_refresh_context)
        self.cmb_coord_mode.currentIndexChanged.connect(self._on_coord_mode_changed)
        self.cmb_design_standard.currentIndexChanged.connect(self._on_design_standard_changed)
        self.btn_load_sketch.clicked.connect(self._on_load_from_sketch)
        self.btn_browse_csv.clicked.connect(self._on_browse_csv)
        self.btn_inspect_csv.clicked.connect(self._on_inspect_csv)
        self.btn_load_csv.clicked.connect(self._on_load_from_csv)
        self.btn_save_csv.clicked.connect(self._on_save_csv)

        self._set_rows(4)
        self._update_coord_headers()
        return w

    @staticmethod
    def _fmt_alignment(o):
        return f"{o.Label} ({o.Name})"

    @staticmethod
    def _fmt_sketch(o):
        return f"{o.Label} ({o.Name})"

    def _use_world_mode(self):
        return int(self.cmb_coord_mode.currentIndex()) == 1

    def _update_coord_headers(self):
        if self._use_world_mode():
            self.table.setHorizontalHeaderLabels(["E", "N", "Radius (m)", "Transition Ls (m)"])
        else:
            self.table.setHorizontalHeaderLabels(["X", "Y", "Radius (m)", "Transition Ls (m)"])

    def _coord_context_obj(self):
        return self.prj if self.prj is not None else self.doc

    def _current_alignment_from_combo(self):
        i = int(self.cmb_alignment.currentIndex())
        if i < 0 or i >= len(self._alignments):
            return None
        return self._alignments[i]

    def _current_sketch_from_combo(self):
        i = int(self.cmb_sketch.currentIndex())
        if i < 0 or i >= len(self._sketches):
            return None
        return self._sketches[i]

    def _selected_design_standard(self):
        base = get_design_standard(self.prj if self.prj is not None else self.doc, default=_ds.DEFAULT_STANDARD)
        return _ds.normalize_standard(self.cmb_design_standard.currentText(), default=base)

    def _load_design_standard(self):
        std = get_design_standard(self.prj if self.prj is not None else self.doc, default=_ds.DEFAULT_STANDARD)
        std = _ds.normalize_standard(std, default=_ds.DEFAULT_STANDARD)
        self._loading = True
        try:
            idx = self.cmb_design_standard.findText(std)
            if idx >= 0:
                self.cmb_design_standard.setCurrentIndex(idx)
            else:
                self.cmb_design_standard.setCurrentText(std)
        finally:
            self._loading = False

    def _refresh_context(self, selected=None):
        if self.doc is None:
            self.prj = None
            self._alignments = []
            self._sketches = []
            self.aln = None
            self.cmb_alignment.clear()
            self.cmb_sketch.clear()
            self.lbl_coord_hint.setText("No coordinate setup.")
            self.lbl_info.setText("No active document.")
            return

        if selected is None:
            selected = self.aln

        self.prj = find_project(self.doc)
        self.lbl_coord_hint.setText(coord_hint_text(self.prj if self.prj is not None else self.doc))
        self.cmb_design_standard.setEnabled(self.prj is not None)

        if not self._coord_mode_initialized:
            self._loading = True
            try:
                if should_default_world_mode(self.prj if self.prj is not None else self.doc):
                    self.cmb_coord_mode.setCurrentIndex(1)
                else:
                    self.cmb_coord_mode.setCurrentIndex(0)
            finally:
                self._loading = False
            self._coord_mode_initialized = True

        self._alignments = _find_alignments(self.doc)
        prev_sketch = self._current_sketch_from_combo()
        self._sketches = find_sketch_objects(self.doc)

        self._loading = True
        try:
            self.cmb_alignment.clear()
            for o in self._alignments:
                self.cmb_alignment.addItem(self._fmt_alignment(o))

            idx = -1
            if selected is not None:
                for i, o in enumerate(self._alignments):
                    if o == selected:
                        idx = i
                        break
            if idx < 0 and self._alignments:
                idx = 0
            self.cmb_alignment.setCurrentIndex(idx)

            self.cmb_sketch.clear()
            for o in self._sketches:
                self.cmb_sketch.addItem(self._fmt_sketch(o))
            sidx = -1
            if prev_sketch is not None:
                for i, o in enumerate(self._sketches):
                    if o == prev_sketch:
                        sidx = i
                        break
            if sidx < 0 and self._sketches:
                sidx = 0
            self.cmb_sketch.setCurrentIndex(sidx)
        finally:
            self._loading = False

        self.aln = self._current_alignment_from_combo()
        if self.aln is None:
            self.lbl_info.setText(f"HorizontalAlignment: 0 found, Sketch: {len(self._sketches)} found")
        else:
            self.lbl_info.setText(
                f"HorizontalAlignment: {len(self._alignments)} found (selected: {self.aln.Label}), "
                f"Sketch: {len(self._sketches)} found"
            )

    def _on_alignment_changed(self):
        if self._loading:
            return
        self.aln = self._current_alignment_from_combo()
        self._load_from_doc()

    def _on_coord_mode_changed(self):
        if self._loading:
            return
        self._update_coord_headers()
        self._load_from_doc()

    def _on_refresh_context(self):
        self._refresh_context()
        self._load_from_doc()

    def _on_design_standard_changed(self):
        if self._loading:
            return
        self._refresh_report()

    @staticmethod
    def _combo_data(cmb):
        i = int(cmb.currentIndex())
        try:
            return cmb.itemData(i)
        except Exception:
            return None

    @staticmethod
    def _csv_delimiter_value(label: str):
        s = str(label or "").lower()
        if "comma" in s:
            return ","
        if "semicolon" in s:
            return ";"
        if "tab" in s:
            return "\t"
        if "pipe" in s:
            return "|"
        return "auto"

    def _csv_encoding_value(self):
        t = str(self.cmb_csv_encoding.currentText() or "Auto").strip().lower()
        if t == "auto":
            return "auto"
        return t

    def _csv_header_value(self):
        t = str(self.cmb_csv_header.currentText() or "Auto").strip().lower()
        if t.startswith("yes"):
            return "yes"
        if t.startswith("no"):
            return "no"
        return "auto"

    def _csv_sort_value(self):
        t = str(self.cmb_csv_sort.currentText() or "Input Order").strip().lower()
        if "sta" in t:
            return "sta"
        if "x/y" in t or "x" in t:
            return "xy"
        return "input"

    def _csv_coord_value(self):
        t = str(self.cmb_csv_coord.currentText() or "Use Panel Mode").strip().lower()
        if t.startswith("local"):
            return "local"
        if t.startswith("world"):
            return "world"
        return "panel"

    def _reset_csv_mapping_combos(self):
        for cmb in (self.cmb_csv_map_x, self.cmb_csv_map_y, self.cmb_csv_map_r, self.cmb_csv_map_ls, self.cmb_csv_map_sta):
            cmb.clear()
            cmb.addItem("<Auto>", "auto")
            cmb.addItem("<None>", -1)

    def _set_csv_columns(self, columns, guess=None):
        cols = list(columns or [])
        self._csv_columns = cols
        self._reset_csv_mapping_combos()

        for i, c in enumerate(cols):
            label = f"{i}: {str(c)}"
            for cmb in (self.cmb_csv_map_x, self.cmb_csv_map_y, self.cmb_csv_map_r, self.cmb_csv_map_ls, self.cmb_csv_map_sta):
                cmb.addItem(label, int(i))

        g = dict(guess or {})
        self._set_mapping_combo_default(self.cmb_csv_map_x, g.get("x", "auto"))
        self._set_mapping_combo_default(self.cmb_csv_map_y, g.get("y", "auto"))
        self._set_mapping_combo_default(self.cmb_csv_map_r, g.get("r", "auto"))
        self._set_mapping_combo_default(self.cmb_csv_map_ls, g.get("ls", "auto"))
        self._set_mapping_combo_default(self.cmb_csv_map_sta, g.get("sta", "auto"))

    @staticmethod
    def _set_mapping_combo_default(cmb, value):
        target = "auto" if value is None else value
        for i in range(cmb.count()):
            try:
                if cmb.itemData(i) == target:
                    cmb.setCurrentIndex(i)
                    return
            except Exception:
                continue
        cmb.setCurrentIndex(0)

    def _build_csv_mapping(self):
        pairs = {
            "x": self._combo_data(self.cmb_csv_map_x),
            "y": self._combo_data(self.cmb_csv_map_y),
            "r": self._combo_data(self.cmb_csv_map_r),
            "ls": self._combo_data(self.cmb_csv_map_ls),
            "sta": self._combo_data(self.cmb_csv_map_sta),
        }
        if all(v == "auto" for v in pairs.values()):
            return None

        out = {}
        for k, v in pairs.items():
            if v == "auto":
                continue
            try:
                out[k] = int(v)
            except Exception:
                out[k] = -1
        return out if out else None

    def _rows_from_world_rows(self, rows_world):
        out = []
        for x, y, rr, ls in list(rows_world or []):
            xv = float(x)
            yv = float(y)
            if not self._use_world_mode():
                lx, ly, _lz = world_to_local(self._coord_context_obj(), float(x), float(y), 0.0)
                xv = float(lx)
                yv = float(ly)
            out.append((float(xv), float(yv), float(rr), float(ls)))
        return out

    def _rows_from_csv_mode_rows(self, rows_csv, csv_coord_mode: str):
        mode = str(csv_coord_mode or "panel").strip().lower()
        if mode == "local":
            return self._rows_from_local_rows(rows_csv)
        if mode == "world":
            return self._rows_from_world_rows(rows_csv)
        return list(rows_csv or [])

    def _on_browse_csv(self):
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select Alignment CSV",
            str(self.ed_csv_path.text() or ""),
            "CSV Files (*.csv *.txt);;All Files (*.*)",
        )
        if str(path or "").strip() != "":
            self.ed_csv_path.setText(str(path))
            self._csv_columns = []
            self._reset_csv_mapping_combos()

    def _on_inspect_csv(self):
        path = str(self.ed_csv_path.text() or "").strip()
        if path == "":
            QtWidgets.QMessageBox.warning(None, "Inspect CSV", "CSV path is empty. Select a file first.")
            return
        try:
            info = inspect_alignment_csv(
                path,
                encoding=self._csv_encoding_value(),
                delimiter=self._csv_delimiter_value(self.cmb_csv_delim.currentText()),
            )
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Inspect CSV", f"Inspect failed: {ex}")
            return

        self._set_csv_columns(info.get("columns", []), guess=info.get("guess_mapping", {}))
        sample = list(info.get("sample_rows", []) or [])
        lines = [
            f"Rows: {int(info.get('row_count', 0))}",
            f"Delimiter: {str(info.get('delimiter', ','))}",
            f"Encoding: {str(info.get('encoding', ''))}",
            f"Header guess: {'Yes' if bool(info.get('header_guess', False)) else 'No'}",
        ]
        if sample:
            lines.append("")
            lines.append("Sample:")
            for r in sample[:3]:
                lines.append(", ".join([str(x) for x in r]))
        QtWidgets.QMessageBox.information(None, "Inspect CSV", "\n".join(lines))

    def _apply_import_rows(self, imported_rows, mode_text: str):
        if str(mode_text or "") == "Append Rows":
            rows = list(self._read_rows())
            if rows and imported_rows:
                x0, y0, _r0, _l0 = imported_rows[0]
                xl, yl, _rl, _ll = rows[-1]
                dx = float(x0) - float(xl)
                dy = float(y0) - float(yl)
                if (dx * dx + dy * dy) <= 1e-12:
                    imported_rows = imported_rows[1:]
            rows.extend(imported_rows)
        else:
            rows = list(imported_rows)

        self._set_rows_data(rows)
        self._last_apply_warnings = []
        self._refresh_report()

    def _on_load_from_sketch(self):
        sk = self._current_sketch_from_combo()
        if sk is None:
            QtWidgets.QMessageBox.warning(None, "Load from Sketch", "No sketch selected.")
            return
        try:
            rows_local = sketch_to_alignment_rows(sk)
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Load from Sketch", f"Import failed: {ex}")
            return
        if len(rows_local) < 2:
            QtWidgets.QMessageBox.warning(None, "Load from Sketch", "Sketch must provide at least 2 points.")
            return

        imported_rows = self._rows_from_local_rows(rows_local)
        self._apply_import_rows(imported_rows, self.cmb_sketch_mode.currentText())

    def _on_load_from_csv(self):
        path = str(self.ed_csv_path.text() or "").strip()
        if path == "":
            QtWidgets.QMessageBox.warning(None, "Load from CSV", "CSV path is empty. Select a file first.")
            return
        try:
            info = read_alignment_csv(
                path,
                encoding=self._csv_encoding_value(),
                delimiter=self._csv_delimiter_value(self.cmb_csv_delim.currentText()),
                has_header=self._csv_header_value(),
                mapping=self._build_csv_mapping(),
                sort_mode=self._csv_sort_value(),
                drop_consecutive_duplicates=bool(self.chk_csv_drop_dup.isChecked()),
                clamp_negative=bool(self.chk_csv_clamp.isChecked()),
                enforce_endpoints=bool(self.chk_csv_end0.isChecked()),
            )
            rows = list(info.get("rows", []) or [])
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Load from CSV", f"Import failed: {ex}")
            return
        if len(rows) < 2:
            QtWidgets.QMessageBox.warning(None, "Load from CSV", "CSV must provide at least 2 valid rows.")
            return

        rows_table = self._rows_from_csv_mode_rows(rows, self._csv_coord_value())
        self._apply_import_rows(rows_table, self.cmb_csv_mode.currentText())

        loaded = int(info.get("loaded", len(rows)))
        skipped = int(info.get("skipped", 0))
        delim = str(info.get("delimiter", ","))
        enc = str(info.get("encoding", ""))
        header = bool(info.get("header", False))
        reasons = list(info.get("skip_reasons", []) or [])
        msg_lines = [
            f"Loaded rows: {loaded}",
            f"Skipped rows: {skipped}",
            f"Delimiter: {delim}",
            f"Encoding: {enc}",
            f"Header: {'Yes' if header else 'No'}",
            f"Sort: {self.cmb_csv_sort.currentText()}",
            f"CSV Coords: {self.cmb_csv_coord.currentText()}",
        ]
        if reasons:
            msg_lines.append("")
            msg_lines.append("Skipped details:")
            msg_lines.extend(reasons)
        QtWidgets.QMessageBox.information(None, "Load from CSV", "\n".join(msg_lines))

    def _on_save_csv(self):
        rows = list(self._read_rows())
        if len(rows) < 1:
            QtWidgets.QMessageBox.warning(None, "Save CSV", "No valid table rows to export.")
            return

        cur_path = str(self.ed_csv_path.text() or "").strip()
        if cur_path == "":
            cur_path = "alignment_pi.csv"
        path, _flt = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Save Alignment CSV",
            cur_path,
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*.*)",
        )
        path = str(path or "").strip()
        if path == "":
            return

        delim = self._csv_delimiter_value(self.cmb_csv_delim.currentText())
        enc = self._csv_encoding_value()
        hdr_opt = self._csv_header_value()
        include_header = hdr_opt != "no"
        x_header = "E" if self._use_world_mode() else "X"
        y_header = "N" if self._use_world_mode() else "Y"

        try:
            info = write_alignment_csv(
                path,
                rows,
                x_header=x_header,
                y_header=y_header,
                delimiter=delim,
                encoding=enc,
                include_header=include_header,
            )
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Save CSV", f"Export failed: {ex}")
            return

        self.ed_csv_path.setText(str(path))
        msg_lines = [
            f"Saved rows: {int(info.get('written', 0))}",
            f"Delimiter: {str(info.get('delimiter', ','))}",
            f"Encoding: {str(info.get('encoding', 'utf-8-sig'))}",
            f"Header: {'Yes' if bool(info.get('header', True)) else 'No'}",
            f"Path: {str(info.get('path', path))}",
        ]
        QtWidgets.QMessageBox.information(None, "Save CSV", "\n".join(msg_lines))

    def _set_rows(self, n):
        self._loading = True
        try:
            self.table.setRowCount(n)
            for r in range(n):
                for c in range(4):
                    if self.table.item(r, c) is None:
                        self.table.setItem(r, c, QtWidgets.QTableWidgetItem(""))
        finally:
            self._loading = False

    def _set_rows_data(self, rows):
        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(len(rows) if rows else 4)
            for i, (x, y, rr, ls) in enumerate(rows):
                self._set_float(i, 0, x)
                self._set_float(i, 1, y)
                self._set_float(i, 2, rr)
                self._set_float(i, 3, ls)
        finally:
            self._loading = False

    def _table_xy_from_local(self, x: float, y: float, z: float = 0.0):
        xv = float(x)
        yv = float(y)
        if self._use_world_mode():
            e, n1, _z1 = local_to_world(self._coord_context_obj(), xv, yv, float(z))
            xv = float(e)
            yv = float(n1)
        return float(xv), float(yv)

    def _rows_from_local_rows(self, rows_local):
        out = []
        for x, y, rr, ls in list(rows_local or []):
            xv, yv = self._table_xy_from_local(float(x), float(y), 0.0)
            out.append((float(xv), float(yv), float(rr), float(ls)))
        return out

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

    def _read_rows(self):
        rows = []
        for r in range(self.table.rowCount()):
            x = self._get_float(r, 0)
            y = self._get_float(r, 1)
            if x is None or y is None:
                continue
            rr = self._get_float(r, 2)
            ls = self._get_float(r, 3)
            rows.append((float(x), float(y), float(rr if rr is not None else 0.0), float(ls if ls is not None else 0.0)))
        return rows

    def _load_from_doc(self):
        self._load_design_standard()
        if self.aln is None:
            self.table.setRowCount(0)
            self._set_rows(4)
            self._last_apply_warnings = []
            return

        ensure_alignment_properties(self.aln)

        pts = list(getattr(self.aln, "IPPoints", []) or [])
        rr = list(getattr(self.aln, "CurveRadii", []) or [])
        ls = list(getattr(self.aln, "TransitionLengths", []) or [])
        n = len(pts)

        if len(rr) < n:
            rr += [0.0] * (n - len(rr))
        if len(ls) < n:
            ls += [0.0] * (n - len(ls))

        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(n if n > 0 else 4)
            for i in range(n):
                p = pts[i]
                xv = float(p.x)
                yv = float(p.y)
                if self._use_world_mode():
                    e, n1, _z1 = local_to_world(self._coord_context_obj(), xv, yv, float(p.z))
                    xv = float(e)
                    yv = float(n1)
                self._set_float(i, 0, xv)
                self._set_float(i, 1, yv)
                self._set_float(i, 2, float(rr[i]))
                self._set_float(i, 3, float(ls[i]))

            self.chk_use_trans.setChecked(bool(getattr(self.aln, "UseTransitionCurves", True)))
            self.spin_spiral_segments.setValue(int(getattr(self.aln, "SpiralSegments", 16)))
            self.spin_v.setValue(float(getattr(self.aln, "DesignSpeedKph", 60.0)))
            self.spin_e.setValue(float(getattr(self.aln, "SuperelevationPct", 8.0)))
            self.spin_f.setValue(float(getattr(self.aln, "SideFriction", 0.15)))
            self.spin_min_r.setValue(float(getattr(self.aln, "MinRadius", 0.0)))
            self.spin_min_tan.setValue(float(getattr(self.aln, "MinTangentLength", 20.0)))
            self.spin_min_ls.setValue(float(getattr(self.aln, "MinTransitionLength", 20.0)))
        finally:
            self._loading = False

        self._refresh_report()

    def _refresh_report(self):
        self._refresh_context(selected=self.aln)
        if self.aln is None:
            self.txt_report.setPlainText("No alignment object.")
            return
        lines = []
        applied_std = str(getattr(self.aln, "CriteriaStandard", "") or get_design_standard(self.doc))
        editor_std = self._selected_design_standard()
        if editor_std == applied_std:
            lines.append(f"Design standard: {applied_std}")
        else:
            lines.append(f"Design standard: {applied_std} (applied)")
            lines.append(f"Design standard (editor): {editor_std} (pending apply)")
        lines.append(f"Status: {getattr(self.aln, 'CriteriaStatus', 'N/A')}")
        lines.append(f"Total length: {float(getattr(self.aln, 'TotalLength', 0.0)):.3f}")
        pts = list(getattr(self.aln, "IPPoints", []) or [])
        lines.append(f"IP count: {len(pts)}")
        if self._last_apply_warnings:
            lines.append("")
            lines.append("Input warnings:")
            lines.extend(self._last_apply_warnings)
        msgs = list(getattr(self.aln, "CriteriaMessages", []) or [])
        lines.append("")
        if msgs:
            lines.append("Criteria warnings:")
            lines.extend(msgs)
        else:
            lines.append("Criteria warnings: none")
        if pts and getattr(self.aln, "Shape", None) and (not self.aln.Shape.isNull()):
            lines.append("")
            lines.append("IP station (approx):")
            for i, p in enumerate(pts):
                try:
                    sta = float(HorizontalAlignment.station_at_xy(self.aln, float(p.x), float(p.y)))
                    lines.append(f"IP#{i}: {sta:.3f}")
                except Exception:
                    lines.append(f"IP#{i}: N/A")
        lines.append("")
        lines.append(f"Coordinate input mode: {'World (E/N)' if self._use_world_mode() else 'Local (X/Y)'}")
        self.txt_report.setPlainText("\n".join(lines))

    def _add_row(self):
        self._set_rows(self.table.rowCount() + 1)

    def _remove_row(self):
        r = self.table.currentRow()
        if r < 0:
            r = self.table.rowCount() - 1
        if r >= 0:
            self.table.removeRow(r)

    def _sort_rows(self):
        rows = self._read_rows()
        rows.sort(key=lambda t: (t[0], t[1]))
        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(len(rows))
            for i, (x, y, rr, ls) in enumerate(rows):
                self._set_float(i, 0, x)
                self._set_float(i, 1, y)
                self._set_float(i, 2, rr)
                self._set_float(i, 3, ls)
        finally:
            self._loading = False

    def _get_or_create_alignment(self):
        if self.aln is not None:
            return self.aln

        if self.doc is None:
            raise Exception("No active document.")
        if not self.chk_create.isChecked():
            raise Exception("HorizontalAlignment missing. Enable create option or create one first.")

        obj = self.doc.addObject("Part::FeaturePython", "HorizontalAlignment")
        HorizontalAlignment(obj)
        ViewProviderHorizontalAlignment(obj.ViewObject)
        obj.Label = "Alignment"
        self.aln = obj
        self._refresh_context(selected=obj)
        return obj

    def _validate_rows(self, rows):
        errs = []
        warns = []
        if len(rows) < 2:
            errs.append("Need at least 2 valid IP rows (X, Y).")
            return errs, warns

        tol = 1e-6
        for i in range(len(rows) - 1):
            x0, y0, _, _ = rows[i]
            x1, y1, _, _ = rows[i + 1]
            dx = float(x1 - x0)
            dy = float(y1 - y0)
            if (dx * dx + dy * dy) <= (tol * tol):
                errs.append(f"Rows {i} and {i + 1} are duplicated or too close.")

        if abs(float(rows[0][2])) > 1e-9 or abs(float(rows[-1][2])) > 1e-9:
            warns.append("Endpoint radius values are forced to 0.")
        if abs(float(rows[0][3])) > 1e-9 or abs(float(rows[-1][3])) > 1e-9:
            warns.append("Endpoint transition lengths are forced to 0.")

        return errs, warns

    def _save_to_doc(self):
        if self.doc is None:
            return

        rows_input = self._read_rows()
        rows = []
        for x, y, rr, ls in rows_input:
            if self._use_world_mode():
                lx, ly, _lz = world_to_local(self._coord_context_obj(), float(x), float(y), 0.0)
                rows.append((float(lx), float(ly), float(rr), float(ls)))
            else:
                rows.append((float(x), float(y), float(rr), float(ls)))

        errs, warns = self._validate_rows(rows)
        if errs:
            raise Exception("\n".join(errs))
        self._last_apply_warnings = list(warns)

        aln = self._get_or_create_alignment()
        ensure_alignment_properties(aln)
        prj = find_project(self.doc)
        if prj is not None:
            ensure_project_properties(prj)
            prj.DesignStandard = self._selected_design_standard()

        pts = [App.Vector(x, y, 0.0) for (x, y, _, _) in rows]
        rr = [max(0.0, r) for (_, _, r, _) in rows]
        ls = [max(0.0, l) for (_, _, _, l) in rows]

        rr[0] = 0.0
        rr[-1] = 0.0
        ls[0] = 0.0
        ls[-1] = 0.0

        aln.IPPoints = pts
        aln.CurveRadii = rr
        aln.TransitionLengths = ls

        aln.UseTransitionCurves = bool(self.chk_use_trans.isChecked())
        aln.SpiralSegments = int(self.spin_spiral_segments.value())
        aln.DesignSpeedKph = float(self.spin_v.value())
        aln.SuperelevationPct = float(self.spin_e.value())
        aln.SideFriction = float(self.spin_f.value())
        aln.MinRadius = float(self.spin_min_r.value())
        aln.MinTangentLength = float(self.spin_min_tan.value())
        aln.MinTransitionLength = float(self.spin_min_ls.value())

        # Sync alignment superelevation input to cross slope template defaults.
        asm = _find_assembly_template(self.doc, project=prj)
        if asm is not None:
            try:
                e_pct = float(self.spin_e.value())
                if hasattr(asm, "LeftSlopePct"):
                    asm.LeftSlopePct = e_pct
                if hasattr(asm, "RightSlopePct"):
                    asm.RightSlopePct = e_pct
                asm.touch()
            except Exception:
                pass

        aln.touch()
        self.doc.recompute()

        if prj is not None:
            link_project(prj, links={"Alignment": aln}, adopt_extra=[aln])

        self._refresh_report()

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass

    def _apply_changes(self):
        try:
            self._save_to_doc()
            QtWidgets.QMessageBox.information(None, "Edit Alignment", "Applied.")
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Edit Alignment", f"Apply failed: {ex}")
