import csv
import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_all, find_first, find_project
from freecad.Corridor_Road.objects.obj_structure_set import (
    ALLOWED_BEHAVIOR_MODES,
    ALLOWED_SIDES,
    ALLOWED_TYPES,
    StructureSet,
    ViewProviderStructureSet,
    ensure_structure_set_properties,
)
from freecad.Corridor_Road.objects.project_links import link_project


COL_HEADERS = [
    "Id",
    "Type",
    "StartStation",
    "EndStation",
    "CenterStation",
    "Side",
    "Offset",
    "Width",
    "Height",
    "BottomElevation",
    "Cover",
    "RotationDeg",
    "BehaviorMode",
    "Notes",
]

COMBO_COLUMN_ITEMS = {
    1: [""] + list(ALLOWED_TYPES),
    5: [""] + list(ALLOWED_SIDES),
    12: [""] + list(ALLOWED_BEHAVIOR_MODES),
}
STATION_COMBO_COLUMNS = (2, 3, 4)


def _find_structure_sets(doc):
    return find_all(doc, proxy_type="StructureSet", name_prefixes=("StructureSet",))


def _find_stationing(doc):
    return find_first(doc, proxy_type="Stationing", name_prefixes=("Stationing",))


def _norm_col(name):
    return "".join(ch for ch in str(name or "").strip().lower() if ch.isalnum())


def _structure_csv_mapping(fieldnames):
    cols = list(fieldnames or [])
    by_norm = {_norm_col(c): c for c in cols}
    aliases = {
        "Id": ("id", "structureid"),
        "Type": ("type", "structuretype"),
        "StartStation": ("startstation", "startsta", "stationstart"),
        "EndStation": ("endstation", "endsta", "stationend"),
        "CenterStation": ("centerstation", "centersta", "stationcenter", "centrestation"),
        "Side": ("side",),
        "Offset": ("offset",),
        "Width": ("width",),
        "Height": ("height",),
        "BottomElevation": ("bottomelevation", "invert", "baseelevation"),
        "Cover": ("cover",),
        "RotationDeg": ("rotationdeg", "rotation", "angledeg"),
        "BehaviorMode": ("behaviormode", "mode"),
        "Notes": ("notes", "note", "remarks", "remark"),
    }
    out = {}
    for key, cand in aliases.items():
        hit = None
        for a in cand:
            k = _norm_col(a)
            if k in by_norm:
                hit = by_norm[k]
                break
        out[key] = hit
    return out


class StructureEditorTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._structures = []
        self._stationing = None
        self._station_values = []
        self._loading = False
        self.form = self._build_ui()
        self._refresh_context()

    def getStandardButtons(self):
        return int(QtWidgets.QDialogButtonBox.Close)

    def accept(self):
        Gui.Control.closeDialog()

    def reject(self):
        Gui.Control.closeDialog()

    def _build_ui(self):
        w = QtWidgets.QWidget()
        w.setWindowTitle("CorridorRoad - Edit Structures")

        main = QtWidgets.QVBoxLayout(w)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        main.addWidget(self.lbl_info)

        self.lbl_station_note = QtWidgets.QLabel(
            "Station fields note: `StartStation`, `EndStation`, and `CenterStation` are station-based values.\n"
            "They become effective after `Generate Stations` has created a `Stationing` object."
        )
        self.lbl_station_note.setWordWrap(True)
        main.addWidget(self.lbl_station_note)

        gb_target = QtWidgets.QGroupBox("Target")
        fs = QtWidgets.QFormLayout(gb_target)
        self.cmb_target = QtWidgets.QComboBox()
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")
        fs.addRow("Target StructureSet:", self.cmb_target)
        fs.addRow(self.btn_refresh)
        main.addWidget(gb_target)

        row_csv = QtWidgets.QHBoxLayout()
        self.ed_csv = QtWidgets.QLineEdit()
        self.ed_csv.setPlaceholderText("Optional structure CSV path")
        self.btn_browse_csv = QtWidgets.QPushButton("Browse CSV")
        self.btn_load_csv = QtWidgets.QPushButton("Load CSV")
        row_csv.addWidget(self.ed_csv, 1)
        row_csv.addWidget(self.btn_browse_csv)
        row_csv.addWidget(self.btn_load_csv)
        main.addLayout(row_csv)

        self.table = QtWidgets.QTableWidget(0, len(COL_HEADERS))
        self.table.setHorizontalHeaderLabels(COL_HEADERS)
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        try:
            hdr.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        except Exception:
            pass
        self.table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        for col, width in (
            (0, 110),
            (1, 130),
            (2, 105),
            (3, 105),
            (4, 105),
            (5, 90),
            (6, 90),
            (7, 90),
            (8, 90),
            (9, 120),
            (10, 90),
            (11, 100),
            (12, 130),
            (13, 220),
        ):
            self.table.setColumnWidth(col, width)
        main.addWidget(self.table)

        row_btn = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Row")
        self.btn_remove = QtWidgets.QPushButton("Remove Row")
        self.btn_sort = QtWidgets.QPushButton("Sort by Start")
        self.btn_apply = QtWidgets.QPushButton("Apply")
        row_btn.addWidget(self.btn_add)
        row_btn.addWidget(self.btn_remove)
        row_btn.addWidget(self.btn_sort)
        row_btn.addWidget(self.btn_apply)
        main.addLayout(row_btn)

        gb_status = QtWidgets.QGroupBox("Validation Guide")
        fg = QtWidgets.QFormLayout(gb_status)
        self.lbl_status = QtWidgets.QLabel("Idle")
        self.lbl_status.setWordWrap(True)
        self.lbl_help = QtWidgets.QLabel(
            "Allowed Type: "
            + ", ".join(ALLOWED_TYPES)
            + "\nAllowed Side: "
            + ", ".join(ALLOWED_SIDES)
            + "\nAllowed BehaviorMode: "
            + ", ".join(ALLOWED_BEHAVIOR_MODES)
            + "\nNote: structure station ranges are prepared here, but they should be defined after `Generate Stations`."
        )
        self.lbl_help.setWordWrap(True)
        fg.addRow("Status:", self.lbl_status)
        fg.addRow(self.lbl_help)
        main.addWidget(gb_status)

        self.btn_refresh.clicked.connect(self._refresh_context)
        self.cmb_target.currentIndexChanged.connect(self._on_target_changed)
        self.btn_browse_csv.clicked.connect(self._on_browse_csv)
        self.btn_load_csv.clicked.connect(self._on_load_csv)
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_sort.clicked.connect(self._sort_rows)
        self.btn_apply.clicked.connect(self._apply)

        self._set_rows(3)
        return w

    @staticmethod
    def _fmt_obj(prefix, obj):
        return f"[{prefix}] {obj.Label} ({obj.Name})"

    def _fill_targets(self, selected=None):
        self.cmb_target.clear()
        self.cmb_target.addItem("[New] Create new StructureSet")
        for o in self._structures:
            self.cmb_target.addItem(self._fmt_obj("StructureSet", o))
        idx = 0
        if selected is not None:
            for i, o in enumerate(self._structures):
                if o == selected:
                    idx = i + 1
                    break
        self.cmb_target.setCurrentIndex(idx)

    def _current_target(self):
        i = int(self.cmb_target.currentIndex())
        if i <= 0:
            return None
        j = i - 1
        if j < 0 or j >= len(self._structures):
            return None
        return self._structures[j]

    def _refresh_context(self):
        if self.doc is None:
            self.lbl_info.setText("No active document.")
            return

        self._loading = True
        try:
            self._structures = _find_structure_sets(self.doc)
            prj = find_project(self.doc)
            sel = getattr(prj, "StructureSet", None) if prj is not None and hasattr(prj, "StructureSet") else None
            self._fill_targets(selected=sel)
            st = getattr(prj, "Stationing", None) if prj is not None and hasattr(prj, "Stationing") else None
            if st is None:
                st = _find_stationing(self.doc)
            self._stationing = st
            self._station_values = list(getattr(st, "StationValues", []) or []) if st is not None else []
            self.lbl_info.setText(
                f"StructureSet: {len(self._structures)} found.\n"
                f"Stationing: {'FOUND' if st is not None else 'NOT FOUND'}\n"
                f"Station count: {len(self._station_values)}"
            )
            if st is None:
                self.lbl_station_note.setText(
                    "Station fields note: `StartStation`, `EndStation`, and `CenterStation` are station-based values.\n"
                    "Run `Generate Stations` first if you want these values to be ready for downstream section usage."
                )
            else:
                self.lbl_station_note.setText(
                    "Station fields note: `StartStation`, `EndStation`, and `CenterStation` are station-based values.\n"
                    "A `Stationing` object exists, so these values are ready for downstream section usage."
                )
            self.btn_apply.setEnabled(st is not None)
        finally:
            self._loading = False
        self._on_target_changed()

    def _set_rows(self, n):
        self._loading = True
        try:
            self.table.setRowCount(n)
            for r in range(n):
                for c in range(len(COL_HEADERS)):
                    if self.table.item(r, c) is None:
                        self.table.setItem(r, c, QtWidgets.QTableWidgetItem(""))
                self._ensure_combo_cells(r)
        finally:
            self._loading = False

    def _ensure_combo_cells(self, row):
        for col, items in COMBO_COLUMN_ITEMS.items():
            cmb = self.table.cellWidget(row, col)
            if cmb is None:
                cmb = QtWidgets.QComboBox()
                cmb.addItems(list(items))
                self.table.setCellWidget(row, col, cmb)
        for col in STATION_COMBO_COLUMNS:
            cmb = self.table.cellWidget(row, col)
            station_items = self._station_combo_items()
            if cmb is None:
                cmb = QtWidgets.QComboBox()
                self.table.setCellWidget(row, col, cmb)
            cur = str(cmb.currentText() or "")
            cmb.clear()
            cmb.addItems(station_items)
            cmb.setEnabled(bool(self._station_values))
            if cur:
                self._set_combo_value(cmb, cur)

    def _station_combo_items(self):
        items = [""]
        for s in list(self._station_values or []):
            try:
                items.append(f"{float(s):.3f}")
            except Exception:
                pass
        return items

    @staticmethod
    def _set_combo_value(cmb, value):
        txt = str(value or "")
        idx = cmb.findText(txt)
        if idx < 0 and txt != "":
            cmb.addItem(txt)
            idx = cmb.findText(txt)
        if idx < 0:
            idx = 0
        cmb.setCurrentIndex(idx)

    def _set_cell_text(self, r, c, txt):
        cmb = self.table.cellWidget(r, c)
        if cmb is not None and (c in COMBO_COLUMN_ITEMS or c in STATION_COMBO_COLUMNS):
            self._set_combo_value(cmb, str(txt or ""))
            return
        it = self.table.item(r, c)
        if it is None:
            it = QtWidgets.QTableWidgetItem("")
            self.table.setItem(r, c, it)
        it.setText(str(txt or ""))

    def _get_cell_text(self, r, c):
        cmb = self.table.cellWidget(r, c)
        if cmb is not None and (c in COMBO_COLUMN_ITEMS or c in STATION_COMBO_COLUMNS):
            return str(cmb.currentText() or "")
        it = self.table.item(r, c)
        return (it.text() if it else "") or ""

    def _get_cell_float(self, r, c):
        txt = self._get_cell_text(r, c).strip()
        if txt == "":
            return 0.0
        try:
            return float(txt)
        except Exception:
            return 0.0

    def _on_target_changed(self):
        if self._loading:
            return
        obj = self._current_target()
        if obj is None:
            self._loading = True
            try:
                self.table.setRowCount(0)
                self._set_rows(3)
                self.lbl_status.setText("New StructureSet will be created.")
            finally:
                self._loading = False
            return

        ensure_structure_set_properties(obj)
        recs = StructureSet.records(obj)
        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(max(3, len(recs)))
            for i, rec in enumerate(recs):
                self._set_cell_text(i, 0, rec.get("Id", ""))
                self._set_cell_text(i, 1, rec.get("Type", ""))
                self._set_cell_text(i, 2, f"{float(rec.get('StartStation', 0.0)):.3f}")
                self._set_cell_text(i, 3, f"{float(rec.get('EndStation', 0.0)):.3f}")
                self._set_cell_text(i, 4, f"{float(rec.get('CenterStation', 0.0)):.3f}")
                self._set_cell_text(i, 5, rec.get("Side", ""))
                self._set_cell_text(i, 6, f"{float(rec.get('Offset', 0.0)):.3f}")
                self._set_cell_text(i, 7, f"{float(rec.get('Width', 0.0)):.3f}")
                self._set_cell_text(i, 8, f"{float(rec.get('Height', 0.0)):.3f}")
                self._set_cell_text(i, 9, f"{float(rec.get('BottomElevation', 0.0)):.3f}")
                self._set_cell_text(i, 10, f"{float(rec.get('Cover', 0.0)):.3f}")
                self._set_cell_text(i, 11, f"{float(rec.get('RotationDeg', 0.0)):.3f}")
                self._set_cell_text(i, 12, rec.get("BehaviorMode", ""))
                self._set_cell_text(i, 13, rec.get("Notes", ""))
            self.lbl_status.setText(str(getattr(obj, "Status", "Loaded")))
        finally:
            self._loading = False

    def _read_rows(self):
        rows = []
        for r in range(self.table.rowCount()):
            row = [self._get_cell_text(r, c).strip() for c in range(len(COL_HEADERS))]
            if not any(row):
                continue
            rows.append(
                {
                    "Id": row[0],
                    "Type": row[1],
                    "StartStation": self._get_cell_float(r, 2),
                    "EndStation": self._get_cell_float(r, 3),
                    "CenterStation": self._get_cell_float(r, 4),
                    "Side": row[5],
                    "Offset": self._get_cell_float(r, 6),
                    "Width": self._get_cell_float(r, 7),
                    "Height": self._get_cell_float(r, 8),
                    "BottomElevation": self._get_cell_float(r, 9),
                    "Cover": self._get_cell_float(r, 10),
                    "RotationDeg": self._get_cell_float(r, 11),
                    "BehaviorMode": row[12],
                    "Notes": row[13],
                }
            )
        return rows

    def _ensure_target(self):
        obj = self._current_target()
        if obj is not None:
            if not hasattr(obj, "Shape"):
                legacy_label = str(getattr(obj, "Label", "Structure Set") or "Structure Set")
                try:
                    obj.ViewObject.Visibility = False
                except Exception:
                    pass
                obj = self.doc.addObject("Part::FeaturePython", "StructureSet")
                StructureSet(obj)
                ViewProviderStructureSet(obj.ViewObject)
                obj.Label = legacy_label
                self.lbl_status.setText("Legacy StructureSet upgraded to a 3D-capable target.")
                return obj
            ensure_structure_set_properties(obj)
            return obj
        obj = self.doc.addObject("Part::FeaturePython", "StructureSet")
        StructureSet(obj)
        ViewProviderStructureSet(obj.ViewObject)
        obj.Label = "Structure Set"
        return obj

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
        rows.sort(key=lambda x: float(x.get("StartStation", 0.0)))
        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(max(3, len(rows)))
            for i, rec in enumerate(rows):
                self._set_cell_text(i, 0, rec["Id"])
                self._set_cell_text(i, 1, rec["Type"])
                self._set_cell_text(i, 2, f"{float(rec['StartStation']):.3f}")
                self._set_cell_text(i, 3, f"{float(rec['EndStation']):.3f}")
                self._set_cell_text(i, 4, f"{float(rec['CenterStation']):.3f}")
                self._set_cell_text(i, 5, rec["Side"])
                self._set_cell_text(i, 6, f"{float(rec['Offset']):.3f}")
                self._set_cell_text(i, 7, f"{float(rec['Width']):.3f}")
                self._set_cell_text(i, 8, f"{float(rec['Height']):.3f}")
                self._set_cell_text(i, 9, f"{float(rec['BottomElevation']):.3f}")
                self._set_cell_text(i, 10, f"{float(rec['Cover']):.3f}")
                self._set_cell_text(i, 11, f"{float(rec['RotationDeg']):.3f}")
                self._set_cell_text(i, 12, rec["BehaviorMode"])
                self._set_cell_text(i, 13, rec["Notes"])
        finally:
            self._loading = False

    def _on_browse_csv(self):
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select structure CSV",
            str(self.ed_csv.text() or ""),
            "CSV Files (*.csv *.txt);;All Files (*.*)",
        )
        if path:
            self.ed_csv.setText(str(path))

    @staticmethod
    def _parse_float(v):
        txt = str(v or "").strip()
        if txt == "":
            return 0.0
        try:
            return float(txt)
        except Exception:
            return 0.0

    def _on_load_csv(self):
        path = str(self.ed_csv.text() or "").strip()
        if not path:
            QtWidgets.QMessageBox.warning(None, "Edit Structures", "CSV file path is empty.")
            return
        if not os.path.isfile(path):
            QtWidgets.QMessageBox.warning(None, "Edit Structures", f"CSV file not found:\n{path}")
            return

        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore", newline="") as f:
                rdr = csv.DictReader(f)
                mapping = _structure_csv_mapping(rdr.fieldnames)
                if not mapping.get("Type") or not mapping.get("StartStation") or not mapping.get("EndStation"):
                    raise Exception("CSV requires at least Type, StartStation, EndStation columns.")
                rows = []
                for row in rdr:
                    rows.append(
                        {
                            "Id": str(row.get(mapping.get("Id"), "") or "").strip(),
                            "Type": str(row.get(mapping.get("Type"), "") or "").strip(),
                            "StartStation": self._parse_float(row.get(mapping.get("StartStation"), "")),
                            "EndStation": self._parse_float(row.get(mapping.get("EndStation"), "")),
                            "CenterStation": self._parse_float(row.get(mapping.get("CenterStation"), "")),
                            "Side": str(row.get(mapping.get("Side"), "") or "").strip(),
                            "Offset": self._parse_float(row.get(mapping.get("Offset"), "")),
                            "Width": self._parse_float(row.get(mapping.get("Width"), "")),
                            "Height": self._parse_float(row.get(mapping.get("Height"), "")),
                            "BottomElevation": self._parse_float(row.get(mapping.get("BottomElevation"), "")),
                            "Cover": self._parse_float(row.get(mapping.get("Cover"), "")),
                            "RotationDeg": self._parse_float(row.get(mapping.get("RotationDeg"), "")),
                            "BehaviorMode": str(row.get(mapping.get("BehaviorMode"), "") or "").strip(),
                            "Notes": str(row.get(mapping.get("Notes"), "") or "").strip(),
                        }
                    )
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Edit Structures", f"CSV load failed: {ex}")
            return

        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(max(3, len(rows)))
            for i, rec in enumerate(rows):
                self._set_cell_text(i, 0, rec["Id"])
                self._set_cell_text(i, 1, rec["Type"])
                self._set_cell_text(i, 2, f"{float(rec['StartStation']):.3f}")
                self._set_cell_text(i, 3, f"{float(rec['EndStation']):.3f}")
                self._set_cell_text(i, 4, f"{float(rec['CenterStation']):.3f}")
                self._set_cell_text(i, 5, rec["Side"])
                self._set_cell_text(i, 6, f"{float(rec['Offset']):.3f}")
                self._set_cell_text(i, 7, f"{float(rec['Width']):.3f}")
                self._set_cell_text(i, 8, f"{float(rec['Height']):.3f}")
                self._set_cell_text(i, 9, f"{float(rec['BottomElevation']):.3f}")
                self._set_cell_text(i, 10, f"{float(rec['Cover']):.3f}")
                self._set_cell_text(i, 11, f"{float(rec['RotationDeg']):.3f}")
                self._set_cell_text(i, 12, rec["BehaviorMode"])
                self._set_cell_text(i, 13, rec["Notes"])
        finally:
            self._loading = False
        self.lbl_status.setText(f"Loaded CSV rows: {len(rows)}")

    def _apply(self):
        if self.doc is None:
            QtWidgets.QMessageBox.warning(None, "Edit Structures", "No active document.")
            return
        if self._stationing is None or not self._station_values:
            QtWidgets.QMessageBox.warning(
                None,
                "Edit Structures",
                "No Stationing found.\nRun `Generate Stations` first, then define StartStation/EndStation/CenterStation from the station list.",
            )
            return
        rows = self._read_rows()
        if not rows:
            QtWidgets.QMessageBox.warning(None, "Edit Structures", "No structure rows to save.")
            return

        try:
            obj = self._ensure_target()
            obj.StructureIds = [str(r["Id"] or "") for r in rows]
            obj.StructureTypes = [str(r["Type"] or "") for r in rows]
            obj.StartStations = [float(r["StartStation"]) for r in rows]
            obj.EndStations = [float(r["EndStation"]) for r in rows]
            obj.CenterStations = [float(r["CenterStation"]) for r in rows]
            obj.Sides = [str(r["Side"] or "") for r in rows]
            obj.Offsets = [float(r["Offset"]) for r in rows]
            obj.Widths = [float(r["Width"]) for r in rows]
            obj.Heights = [float(r["Height"]) for r in rows]
            obj.BottomElevations = [float(r["BottomElevation"]) for r in rows]
            obj.Covers = [float(r["Cover"]) for r in rows]
            obj.RotationsDeg = [float(r["RotationDeg"]) for r in rows]
            obj.BehaviorModes = [str(r["BehaviorMode"] or "") for r in rows]
            obj.Notes = [str(r["Notes"] or "") for r in rows]
            obj.touch()

            prj = find_project(self.doc)
            if prj is not None:
                link_project(prj, links={"StructureSet": obj}, adopt_extra=[obj])

            self.doc.recompute()
            issues = StructureSet.validate(obj)
            st = getattr(prj, "Stationing", None) if prj is not None and hasattr(prj, "Stationing") else None
            if st is None:
                st = _find_stationing(self.doc)
            self.lbl_status.setText(str(getattr(obj, "Status", "Applied")))
            try:
                obj.ViewObject.Visibility = True
            except Exception:
                pass
            if issues:
                QtWidgets.QMessageBox.information(
                    None,
                    "Edit Structures",
                    "Structure set saved with validation warnings.\n"
                    f"Records: {len(rows)}\n"
                    + "\n".join(issues[:10]),
                )
            else:
                msg = [f"Structure set saved.\nRecords: {len(rows)}"]
                if st is None:
                    msg.append("")
                    msg.append("Guide:")
                    msg.append("StartStation/EndStation based usage becomes effective after `Generate Stations` creates a `Stationing` object.")
                QtWidgets.QMessageBox.information(None, "Edit Structures", "\n".join(msg))
            self._refresh_context()
            try:
                Gui.ActiveDocument.ActiveView.fitAll()
            except Exception:
                pass
        except Exception as ex:
            self.lbl_status.setText(f"ERROR: {ex}")
            QtWidgets.QMessageBox.warning(None, "Edit Structures", f"Apply failed: {ex}")
