import FreeCAD as App
import FreeCADGui as Gui

from PySide2 import QtWidgets

from objects.obj_alignment import HorizontalAlignment, ViewProviderHorizontalAlignment, ensure_alignment_properties
from objects.obj_project import get_length_scale


def _find_alignment(doc):
    for o in doc.Objects:
        if o.Name.startswith("HorizontalAlignment"):
            return o
    return None


class AlignmentEditorTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self.aln = None
        self._loading = False
        self._last_apply_warnings = []
        self.form = self._build_ui()
        self._refresh_context()
        self._load_from_doc()

    def getStandardButtons(self):
        return int(QtWidgets.QDialogButtonBox.Close)

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

        form.addRow(self.chk_create)
        form.addRow(self.chk_use_trans)
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
        rep_row.addWidget(self.btn_apply)
        rep_row.addWidget(self.btn_refresh)
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

        self._set_rows(4)
        return w

    def _refresh_context(self):
        if self.doc is None:
            self.aln = None
            self.lbl_info.setText("No active document.")
            return

        self.aln = _find_alignment(self.doc)
        self.lbl_info.setText(
            "HorizontalAlignment: " + ("FOUND" if self.aln is not None else "NOT FOUND")
        )

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
        self._refresh_context()
        if self.aln is None:
            return

        ensure_alignment_properties(self.aln)

        pts = list(getattr(self.aln, "IPPoints", []) or [])
        rr = list(getattr(self.aln, "CurveRadii", []) or [])
        ls = list(getattr(self.aln, "TransitionLengths", []) or [])
        n = len(pts)
        if n < 2:
            return

        if len(rr) < n:
            rr += [0.0] * (n - len(rr))
        if len(ls) < n:
            ls += [0.0] * (n - len(ls))

        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(n)
            for i, p in enumerate(pts):
                self._set_float(i, 0, float(p.x))
                self._set_float(i, 1, float(p.y))
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
        self._refresh_context()
        if self.aln is None:
            self.txt_report.setPlainText("No alignment object.")
            return
        lines = []
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

        rows = self._read_rows()
        errs, warns = self._validate_rows(rows)
        if errs:
            raise Exception("\n".join(errs))
        self._last_apply_warnings = list(warns)

        aln = self._get_or_create_alignment()
        ensure_alignment_properties(aln)

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

        aln.touch()
        self.doc.recompute()
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
