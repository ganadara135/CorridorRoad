# CorridorRoad/ui/task_pvi_editor.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_project
from freecad.Corridor_Road.objects.obj_vertical_alignment import VerticalAlignment, ViewProviderVerticalAlignment
from freecad.Corridor_Road.objects.obj_profile_bundle import ProfileBundle, ViewProviderProfileBundle
from freecad.Corridor_Road.objects.obj_project import get_length_scale
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
        self._scale = get_length_scale(self.doc, default=1.0)
        self._loading = False
        self.form = self._build_ui()
        self._try_load_existing_va()

    # ---- TaskPanel API ----
    def getStandardButtons(self):
        return int(QtWidgets.QDialogButtonBox.Close)

    def accept(self):
        Gui.Control.closeDialog()

    def reject(self):
        Gui.Control.closeDialog()

    # ---- UI ----
    def _build_ui(self):
        w = QtWidgets.QWidget()
        w.setWindowTitle("CorridorRoad - PVI Editor (Generate FG)")

        main = QtWidgets.QVBoxLayout(w)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(10)

        # Top controls
        top = QtWidgets.QHBoxLayout()
        top.setSpacing(10)

        gb_left = QtWidgets.QGroupBox("PVI Input")
        gl = QtWidgets.QVBoxLayout(gb_left)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Row")
        self.btn_remove = QtWidgets.QPushButton("Remove Row")
        self.btn_sort = QtWidgets.QPushButton("Sort by Station")

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_sort)

        gl.addLayout(btn_row)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["PVI Station", "PVI Elev", "Curve Length"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed)

        gl.addWidget(self.table)

        gb_right = QtWidgets.QGroupBox("Generate FG")
        gr = QtWidgets.QFormLayout(gb_right)



        self.chk_clamp = QtWidgets.QCheckBox("Clamp overlapping vertical curves (auto adjust L)")
        self.chk_clamp.setChecked(True)

        self.spin_min_tan = QtWidgets.QDoubleSpinBox()
        self.spin_min_tan.setRange(0.0, 100000.0)
        self.spin_min_tan.setDecimals(3)
        self.spin_min_tan.setValue(0.0)
        self.spin_min_tan.setSuffix(" m")

        gr.addRow(self.chk_clamp)
        gr.addRow("Min Tangent:", self.spin_min_tan)

        # self.chk_curves_only = QtWidgets.QCheckBox("FG Curves Only (hide tangents)")
        # self.chk_curves_only.setChecked(False)
        # gr.addRow(self.chk_curves_only)

        self.lbl_info = QtWidgets.QLabel(
            "FG will be generated on Station list:\n"
            "- ProfileBundle.Stations (if exists)\n"
            "- else Stationing.StationValues\n\n"
            "Step 1: Linear grade only (no vertical curves)."
        )
        self.lbl_info.setWordWrap(True)

        self.chk_create_bundle = QtWidgets.QCheckBox("Create ProfileBundle if missing")
        self.chk_create_bundle.setChecked(True)

        self.chk_keep_eg = QtWidgets.QCheckBox("Keep existing EG values (do not overwrite)")
        self.chk_keep_eg.setChecked(True)

        self.btn_preview = QtWidgets.QPushButton("Preview FG (console)")
        self.btn_generate_only = QtWidgets.QPushButton("Generate FG Now (apply)")

        gr.addRow(self.lbl_info)
        gr.addRow(self.chk_create_bundle)
        gr.addRow(self.chk_keep_eg)
        gr.addRow(self.btn_preview)
        gr.addRow(self.btn_generate_only)

        top.addWidget(gb_left, 3)
        top.addWidget(gb_right, 2)

        main.addLayout(top)

        # Signals
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_sort.clicked.connect(self._sort_rows)
        self.btn_preview.clicked.connect(self._preview_fg)
        self.btn_generate_only.clicked.connect(self._generate_fg_to_profilebundle)

        # Start with 3 blank rows for convenience
        self._set_rows(3)

        return w

    # ---- Table helpers ----
    def _set_rows(self, n):
        self.table.setRowCount(n)
        for r in range(n):
            for c in range(3):
                if self.table.item(r, c) is None:
                    self.table.setItem(r, c, QtWidgets.QTableWidgetItem(""))

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
        n = self.table.rowCount()
        self._set_rows(n + 1)

    def _remove_row(self):
        r = self.table.currentRow()
        if r < 0:
            r = self.table.rowCount() - 1

        if r >= 0:
            self.table.removeRow(r)

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

    def _try_load_existing_va(self):
        if self.doc is None:
            return

        self._scale = get_length_scale(self.doc, default=1.0)
        va = _find_vertical_alignment(self.doc)
        if va is None:
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

        sc = max(1e-12, float(self._scale))
        rows = sorted(
            [(float(st[i]) / sc, float(el[i]) / sc, float(Ls[i]) / sc) for i in range(n)],
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
            self.spin_min_tan.setValue(float(getattr(va, "MinTangent", 0.0)) / sc)
        except Exception:
            pass

    # ---- Save VerticalAlignment ----
    def _save_vertical_alignment(self):
        if self.doc is None:
            return

        self._scale = get_length_scale(self.doc, default=1.0)
        sc = max(1e-12, float(self._scale))
        rows  = self._read_pvi()
        if len(rows) < 2:
            raise Exception("Need at least 2 valid PVI rows (Station & Elev).")

        va = _find_vertical_alignment(self.doc)
        if va is None:
            va = self.doc.addObject("Part::FeaturePython", "VerticalAlignment")
            VerticalAlignment(va)
            ViewProviderVerticalAlignment(va.ViewObject)
            va.Label = "Vertical Alignment (PVI)"
        _ensure_fg_display(self.doc, va)

        va.ClampOverlaps = bool(self.chk_clamp.isChecked())
        va.MinTangent = float(self.spin_min_tan.value()) * sc
        va.PVIStations = [float(p[0]) * sc for p in rows]
        va.PVIElevations = [float(p[1]) * sc for p in rows]
        va.CurveLengths  = [float(p[2]) * sc for p in rows]
        try:
            va.ShowPVIWire = False
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
            return []

        b = _find_profile_bundle(self.doc)
        if b is not None and getattr(b, "Stations", None):
            st = list(b.Stations or [])
            if len(st) >= 2:
                return st

        st_obj = _find_stationing(self.doc)
        if st_obj is not None and getattr(st_obj, "StationValues", None):
            st = list(st_obj.StationValues or [])
            if len(st) >= 2:
                return st

        return []

    def _preview_fg(self):
        if self.doc is None:
            return

        # Always persist current UI rows first so preview uses latest edits/scale conversion.
        self._save_vertical_alignment()
        va = _find_vertical_alignment(self.doc)
        if va is None:
            raise Exception("Failed to create/update VerticalAlignment from current PVI table.")

        stations = self._resolve_station_list()
        if len(stations) < 2:
            raise Exception("No station list found. Create Stationing or ProfileBundle first.")

        # print first 10 to console
        for s in stations[:10]:
            z = VerticalAlignment.elevation_at_station(va, float(s))
            App.Console.PrintMessage(f"[FG Preview] s={float(s):.3f} -> z={float(z):.3f}\n")

    def _generate_fg_to_profilebundle(self):
        if self.doc is None:
            return

        # Always persist current UI rows first so generated FG reflects latest edits/scale conversion.
        self._save_vertical_alignment()
        va = _find_vertical_alignment(self.doc)
        if va is None:
            raise Exception("Failed to create/update VerticalAlignment from current PVI table.")

        stations = self._resolve_station_list()
        if len(stations) < 2:
            raise Exception("No station list found. Create Stationing or ProfileBundle first.")

        b = _find_profile_bundle(self.doc)
        if b is None:
            if not self.chk_create_bundle.isChecked():
                raise Exception("ProfileBundle is missing. Enable 'Create ProfileBundle if missing' or create it first.")

            b = self.doc.addObject("Part::FeaturePython", "ProfileBundle")
            ProfileBundle(b)
            ViewProviderProfileBundle(b.ViewObject)
            b.Label = PROFILE_BUNDLE_LABEL

            # If we created from Stationing, set Stations now
            b.Stations = [float(s) for s in stations]

            # Create empty EG list (or zeros). We will not overwrite if keep_eg is checked later.
            b.ElevEG = [0.0 for _ in stations]
            b.ShowEGWire = True
            b.WireZOffset = 0.0

        else:
            # If bundle exists but station list differs, we will regenerate based on bundle stations
            stations = list(b.Stations or stations)

        # Compute FG using VerticalAlignment engine
        fg = [float(VerticalAlignment.elevation_at_station(va, float(s))) for s in stations]

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
        b.Stations = [float(s) for s in stations]
        b.ElevFG = fg
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

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass
