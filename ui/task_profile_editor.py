# CorridorRoad/ui/task_profile_editor.py
import FreeCAD as App
import FreeCADGui as Gui

from PySide2 import QtCore, QtWidgets

from objects.obj_profile_bundle import ProfileBundle, ViewProviderProfileBundle
from objects.obj_vertical_alignment import VerticalAlignment
from objects.obj_fg_display import FGDisplay, ViewProviderFGDisplay

def _find_profile_bundle(doc):
    for o in doc.Objects:
        if o.Name.startswith("ProfileBundle"):
            return o
    return None


def _find_stationing(doc):
    for o in doc.Objects:
        if o.Name.startswith("Stationing"):
            return o
    return None


def _find_vertical_alignment(doc):
    for o in doc.Objects:
        if o.Name.startswith("VerticalAlignment"):
            return o
    return None


def _find_fg_display(doc):
    for o in doc.Objects:
        if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "FGDisplay":
            return o

        # 이름 기반 fallback
        if o.Label == "Finished Grade (FG)":
            return o

    return None


def _ensure_fg_display(doc, va):
    fg = _find_fg_display(doc)
    if fg is not None:
        # ensure link
        try:
            if getattr(fg, "SourceVA", None) is None:
                fg.SourceVA = va
        except Exception:
            pass
        return fg

    fg = doc.addObject("Part::FeaturePython", "FinishedGradeFG")
    from objects.obj_fg_display import FGDisplay, ViewProviderFGDisplay

    FGDisplay(fg)
    ViewProviderFGDisplay(fg.ViewObject)

    fg.Label = "Finished Grade (FG)"

    try:
        fg.SourceVA = va
    except Exception:
        pass

    # migration: if old properties existed on VA, copy once
    try:
        fg.CurvesOnly = bool(getattr(va, "FGCurvesOnly", False))
    except Exception:
        pass

    try:
        fg.ZOffset = float(getattr(va, "FGWireZOffset", 0.0))
    except Exception:
        pass

    try:
        fg.ShowWire = True
    except Exception:
        pass

    fg.touch()
    doc.recompute()
    return fg

class ProfileEditorTaskPanel:
    """
    Refactored Profile Editor:

    - ProfileBundle holds data: Stations/ElevEG/ElevFG/Delta.
    - ProfileBundle only draws EG (optional).
    - VerticalAlignment draws FG (optional).

    UI:
      - Table: Station, EG, FG, Delta
      - FG mode:
          * FG from VerticalAlignment (preferred): FG column is auto-populated and read-only.
          * Manual FG: FG column editable.
      - Display options:
          * Show EG wire -> ProfileBundle.ShowEGWire
          * Show FG wire -> VerticalAlignment.ShowFGWire
          * EG Z offset -> ProfileBundle.WireZOffset
          * FG Z offset -> VerticalAlignment.FGWireZOffset
    """

    def __init__(self):
        self.doc = App.ActiveDocument

        # prevent AttributeError during UI build
        self.bundle = None
        self.stationing = None
        self.va = None
        self.fgdisp = None

        self._loading = False
        self.form = self._build_ui()

        self._refresh_context()
        self._load_from_document()

    # ---- TaskPanel protocol ----
    def getStandardButtons(self):
        return int(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

    def accept(self):
        self._save_to_document()
        Gui.Control.closeDialog()

    def reject(self):
        Gui.Control.closeDialog()

    # ---- UI ----
    def _build_ui(self):
        w = QtWidgets.QWidget()
        w.setWindowTitle("CorridorRoad - Edit Profiles (EG/FG)")

        root = QtWidgets.QVBoxLayout(w)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # Top info
        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        root.addWidget(self.lbl_info)

        # Table
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

        root.addWidget(self.table)

        # Buttons row
        btn_row = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Row")
        self.btn_remove = QtWidgets.QPushButton("Remove Row")
        self.btn_sort = QtWidgets.QPushButton("Sort by Station")
        self.btn_fill_stations = QtWidgets.QPushButton("Fill Stations from Stationing")
        self.btn_fill_fg_from_va = QtWidgets.QPushButton("Fill FG from VerticalAlignment")

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_sort)
        btn_row.addWidget(self.btn_fill_stations)
        btn_row.addWidget(self.btn_fill_fg_from_va)
        root.addLayout(btn_row)

        # Options group
        gb = QtWidgets.QGroupBox("Options")
        form = QtWidgets.QFormLayout(gb)

        self.chk_create_bundle = QtWidgets.QCheckBox("Create ProfileBundle if missing")
        self.chk_create_bundle.setChecked(True)

        self.chk_fg_from_va = QtWidgets.QCheckBox("FG from VerticalAlignment (lock FG column)")
        self.chk_fg_from_va.setChecked(True)

        self.chk_show_eg = QtWidgets.QCheckBox("Show EG wire (ProfileBundle)")
        self.chk_show_eg.setChecked(True)

        self.chk_show_fg = QtWidgets.QCheckBox("Show FG wire (VerticalAlignment)")
        self.chk_show_fg.setChecked(True)

        self.spin_eg_zoff = QtWidgets.QDoubleSpinBox()
        self.spin_eg_zoff.setRange(-1e9, 1e9)
        self.spin_eg_zoff.setDecimals(3)
        self.spin_eg_zoff.setValue(0.0)

        self.spin_fg_zoff = QtWidgets.QDoubleSpinBox()
        self.spin_fg_zoff.setRange(-1e9, 1e9)
        self.spin_fg_zoff.setDecimals(3)
        self.spin_fg_zoff.setValue(0.0)

        form.addRow(self.chk_create_bundle)
        form.addRow(self.chk_fg_from_va)
        form.addRow(self.chk_show_eg)
        form.addRow(self.chk_show_fg)
        form.addRow("EG Z Offset:", self.spin_eg_zoff)
        form.addRow("FG Z Offset:", self.spin_fg_zoff)

        root.addWidget(gb)

        # Signals
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_sort.clicked.connect(self._sort_rows)
        self.btn_fill_stations.clicked.connect(self._fill_stations_from_stationing)
        self.btn_fill_fg_from_va.clicked.connect(self._fill_fg_from_va)

        self.chk_fg_from_va.toggled.connect(self._on_fg_mode_toggled)
        self.table.itemChanged.connect(self._on_table_item_changed)

        # Start with a few empty rows
        self._set_rows(3)

        return w

    # ---- Context ----
    def _refresh_context(self):
        if self.doc is None:
            self.bundle = None
            self.stationing = None
            self.va = None
            self.lbl_info.setText("No active document.")
            return
        
        self.bundle = _find_profile_bundle(self.doc)
        self.stationing = _find_stationing(self.doc)
        self.va = _find_vertical_alignment(self.doc)

        self.fgdisp = None
        if self.va is not None:
            self.fgdisp = _ensure_fg_display(self.doc, self.va)
        else:
            self.fgdisp = _find_fg_display(self.doc)

        msg = []
        msg.append(f"ProfileBundle: {'FOUND' if self.bundle else 'NOT FOUND'}")
        msg.append(f"Stationing: {'FOUND' if self.stationing else 'NOT FOUND'}")
        msg.append(f"VerticalAlignment: {'FOUND' if self.va else 'NOT FOUND'}")
        msg.append("")
        msg.append("Policy:")
        msg.append("- EG wire is drawn by ProfileBundle.")
        msg.append("- FG wire is drawn by VerticalAlignment (analytic Bezier vertical curves).")
        self.lbl_info.setText("\n".join(msg))

        # default FG-from-VA checkbox based on VA existence
        if self.va is None:
            self.chk_fg_from_va.setChecked(False)

        self.btn_fill_fg_from_va.setEnabled(self.va is not None)


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

    # ---- Actions ----
    def _add_row(self):
        self._set_rows(self.table.rowCount() + 1)

    def _remove_row(self):
        r = self.table.currentRow()
        if r < 0:
            r = self.table.rowCount() - 1
        if r >= 0:
            self.table.removeRow(r)

    def _sort_rows(self):
        rows = self._read_table_rows(keep_blanks=False)
        rows.sort(key=lambda x: x[0])

        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(len(rows))
            for i, (s, eg, fg) in enumerate(rows):
                self._set_cell_float(i, 0, s)
                self._set_cell_float(i, 1, eg)
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

    def _fill_fg_from_va(self):
        if self.va is None:
            return

        # only fill if lock mode is on (to avoid surprising overwrites)
        if not self.chk_fg_from_va.isChecked():
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


    def _on_table_item_changed(self, item):
        if self._loading:
            return

        r = item.row()
        c = item.column()

        if c in (0, 1, 2):
            # If FG is locked from VA, station change should re-fill FG
            if c != 2 and self.chk_fg_from_va.isChecked() and self.va is not None:
                self._fill_fg_from_va()

            # If user edits FG manually (FG column) while NOT locked => hide VA FG wire
            if c == 2:
                if (not self.chk_fg_from_va.isChecked()) and (self.va is not None):
                    # user is manually editing FG -> force-hide VA FG wire to avoid mismatch
                    self._ensure_va_fg_hidden("FG cell edited manually")

            self._update_delta_row(r)


    def _update_delta_row(self, r):
        eg = self._get_cell_float(r, 1)
        fg = self._get_cell_float(r, 2)

        if eg is None or fg is None:
            self._set_cell_text(r, 3, "")
            return

        self._set_cell_float(r, 3, float(fg - eg))

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
                # FGDisplay가 없으면 FG표시 옵션 비활성 추천                
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
        ViewProviderProfileBundle(b.ViewObject)
        b.Label = "Profiles (EG/FG)"
        self.bundle = b

        return b

    def _save_to_document(self):
        if self.doc is None:
            return

        self._refresh_context()

        b = self._get_or_create_bundle()
        va = self.va  # may be None

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
                va.ShowFGWire = bool(self.chk_show_fg.isChecked())
            else:
                b.FGIsManual = True
                if va is not None:
                    va.ShowFGWire = False
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

        # FG display is owned by VA
        # if va is not None:
        #     try:
        #         va.ShowFGWire = bool(self.chk_show_fg.isChecked())
        #     except Exception:
        #         pass
        #     try:
        #         va.FGWireZOffset = float(self.spin_fg_zoff.value())
        #     except Exception:
        #         pass
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
        # Hard rule: when manual FG, VA FG must be hidden to avoid mismatch UX
        if self.va is None:
            return

        try:
            self.chk_show_fg.setChecked(False)
        except Exception:
            pass

        try:
            self.va.ShowFGWire = False
            self.va.touch()
        except Exception:
            pass

        if reason:
            self._set_state_text(f"Manual FG mode: hiding VerticalAlignment FG wire. ({reason})")
        else:
            self._set_state_text("Manual FG mode: hiding VerticalAlignment FG wire.")

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
        if self.va is None:
            return

        try:
            self.chk_show_fg.setChecked(True)
        except Exception:
            pass

        try:
            self.va.ShowFGWire = True
            self.va.touch()
        except Exception:
            pass

        if reason:
            self._set_state_text(f"FG from VerticalAlignment: showing VA FG wire. ({reason})")
        else:
            self._set_state_text("FG from VerticalAlignment: showing VA FG wire.")


    def _on_fg_mode_toggled(self, checked):
        # checked=True => FG from VA mode
        self._apply_fg_lock()

        # UX guardrails
        if checked and self.va is not None:
            # Switch to VA-driven FG
            self.btn_fill_fg_from_va.setEnabled(True)

            # Force show VA FG (so user sees the "source of truth")
            # self._ensure_va_fg_shown("mode toggled on")
            self._ensure_fg_shown("mode toggled on")

            # Also refresh FG values on table to match VA (prevents stale manual numbers)
            self._fill_fg_from_va()

        else:
            # Manual FG mode OR no VA
            self.btn_fill_fg_from_va.setEnabled(False)

            # Prevent mismatch: hide VA FG wire immediately
            # self._ensure_va_fg_hidden("mode toggled off (manual FG)")
            self._ensure_fg_hidden("mode toggled off (manual FG)")