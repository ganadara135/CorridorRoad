# CorridorRoad/ui/task_profile_editor.py
import FreeCAD as App
import FreeCADGui as Gui

from PySide2 import QtCore, QtWidgets

from objects.doc_query import find_first, find_project
from objects.obj_profile_bundle import ProfileBundle, ViewProviderProfileBundle
from objects.obj_vertical_alignment import VerticalAlignment
from objects.obj_alignment import HorizontalAlignment
from objects.obj_project import get_coordinate_setup, local_to_world, world_to_local
from objects.terrain_sampler import TerrainSampler, is_mesh_object, is_shape_object
from ui.common.profile_fg_helpers import (
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
        return int(QtWidgets.QDialogButtonBox.Close)

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
        form.addRow(self.btn_apply)

        root.addWidget(gb)

        # Signals
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_sort.clicked.connect(self._sort_rows)
        self.btn_fill_stations.clicked.connect(self._fill_stations_from_stationing)
        self.btn_fill_fg_from_va.clicked.connect(self._fill_fg_from_va)
        self.btn_pick_terrain.clicked.connect(self._use_selected_terrain)
        self.btn_apply.clicked.connect(self._apply_changes)
        self.cmb_terrain_coords.currentIndexChanged.connect(self._on_terrain_coord_mode_changed)

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
        cst = get_coordinate_setup(self._coord_context_obj())
        epsg = str(cst.get("CRSEPSG", "") or "").strip()
        st = str(cst.get("CoordSetupStatus", "Uninitialized") or "Uninitialized")
        self.lbl_coord_hint.setText(f"CRS: {epsg if epsg else 'N/A'} / Status: {st}")

    def _apply_default_coord_mode(self):
        if self._coord_mode_initialized:
            return
        cst = get_coordinate_setup(self._coord_context_obj())
        epsg = str(cst.get("CRSEPSG", "") or "").strip()
        st = str(cst.get("CoordSetupStatus", "Uninitialized") or "Uninitialized")
        self._loading = True
        try:
            if st != "Uninitialized" or bool(epsg):
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
        self.cmb_eg_terrain.setEnabled(bool(self._terrains))
        self.btn_pick_terrain.setEnabled(bool(self._terrains))
        self.btn_apply.setEnabled(True)

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

    def _fill_eg_from_terrain(self, overwrite: bool = True, show_message: bool = True, terrain_obj=None):
        if self.alignment is None:
            raise Exception("HorizontalAlignment not found.")
        terr = terrain_obj if terrain_obj is not None else self._current_terrain()
        if terr is None:
            raise Exception("No terrain source selected.")

        sampler = TerrainSampler.from_object(terr, max_triangles=300000)
        if sampler is None:
            raise Exception("Failed to build terrain sampler from selected source.")

        sampled = 0
        nodata = 0
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
                if self._use_world_terrain_mode():
                    qx, qy, _qz = local_to_world(self._coord_context_obj(), qx, qy, float(p.z))
                z = sampler.z_at(float(qx), float(qy))
                if z is None:
                    nodata += 1
                    continue
                z_local = float(z)
                if self._use_world_terrain_mode():
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
            if nodata > 0:
                msg += f", no-data: {nodata} rows"
            QtWidgets.QMessageBox.information(None, "Edit Profiles", msg)

    def _apply_changes(self):
        try:
            terr = self._current_terrain()
            if terr is not None and self.alignment is not None:
                self._fill_eg_from_terrain(overwrite=True, show_message=False, terrain_obj=terr)
            self._save_to_document()
            QtWidgets.QMessageBox.information(None, "Edit Profiles", "Applied.")
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Edit Profiles", f"Apply failed: {ex}")

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

            # If user edits FG manually (FG column) while NOT locked => hide FG wire
            if c == 2:
                if (not self.chk_fg_from_va.isChecked()) and (self.va is not None):
                    # user is manually editing FG -> force-hide FG wire to avoid mismatch
                    self._ensure_fg_hidden("FG cell edited manually")

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
