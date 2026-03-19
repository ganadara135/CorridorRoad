import csv
import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_all, find_first, find_project
from freecad.Corridor_Road.objects.obj_structure_set import (
    ALLOWED_BEHAVIOR_MODES,
    ALLOWED_CORRIDOR_MODES,
    ALLOWED_GEOMETRY_MODES,
    ALLOWED_PLACEMENT_MODES,
    ALLOWED_SIDES,
    ALLOWED_TEMPLATE_NAMES,
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
    "GeometryMode",
    "TemplateName",
    "WallThickness",
    "FootingWidth",
    "FootingThickness",
    "CapHeight",
    "CellCount",
    "CorridorMode",
    "CorridorMargin",
    "Notes",
    "ShapeSourcePath",
    "ScaleFactor",
    "PlacementMode",
    "UseSourceBaseAsBottom",
]

COMBO_COLUMN_ITEMS = {
    1: [""] + list(ALLOWED_TYPES),
    5: [""] + list(ALLOWED_SIDES),
    12: [""] + list(ALLOWED_BEHAVIOR_MODES),
    13: [""] + list(ALLOWED_GEOMETRY_MODES[1:]),
    14: [""] + list(ALLOWED_TEMPLATE_NAMES[1:]),
    20: list(ALLOWED_CORRIDOR_MODES),
    25: [""] + list(ALLOWED_PLACEMENT_MODES[1:]),
    26: ["", "true", "false"],
}
STATION_COMBO_COLUMNS = (2, 3, 4)


def _split_shape_source_path(path: str):
    raw = str(path or "").strip()
    if not raw:
        return "", ""
    if "#" in raw:
        src, obj_name = raw.rsplit("#", 1)
        return os.path.abspath(os.path.expanduser(str(src).strip())), str(obj_name or "").strip()
    return os.path.abspath(os.path.expanduser(raw)), ""


def _recommended_corridor_mode(structure_type: str) -> str:
    typ = str(structure_type or "").strip().lower()
    if typ in ("culvert", "crossing"):
        return "notch"
    if typ in ("bridge_zone", "abutment_zone"):
        return "skip_zone"
    if typ == "retaining_wall":
        return "split_only"
    return ""


def _recommended_geometry_mode(structure_type: str) -> str:
    typ = str(structure_type or "").strip().lower()
    if typ in ("culvert", "crossing", "retaining_wall", "abutment_zone"):
        return "template"
    return "box"


def _recommended_template_name(structure_type: str) -> str:
    typ = str(structure_type or "").strip().lower()
    if typ == "culvert":
        return "box_culvert"
    if typ == "crossing":
        return "utility_crossing"
    if typ == "retaining_wall":
        return "retaining_wall"
    if typ == "abutment_zone":
        return "abutment_block"
    return ""


def _vertical_input_policy(structure_type: str):
    typ = str(structure_type or "").strip().lower()
    if typ in ("culvert", "crossing"):
        return False, True, "Use Cover for buried culvert/crossing placement."
    if typ in ("retaining_wall", "abutment_zone", "bridge_zone"):
        return True, False, "Use BottomElevation for wall/abutment/bridge-zone placement."
    return True, True, "BottomElevation and Cover are both available for this structure type."


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
        "GeometryMode": ("geometrymode", "geomode"),
        "TemplateName": ("templatename", "template", "structuretemplate"),
        "WallThickness": ("wallthickness", "wall", "wallthk"),
        "FootingWidth": ("footingwidth", "footing", "basewidth"),
        "FootingThickness": ("footingthickness", "basethickness"),
        "CapHeight": ("capheight", "cap", "topcapheight"),
        "CellCount": ("cellcount", "cells", "numberofcells"),
        "CorridorMode": ("corridormode", "corridormodepolicy", "corridorpolicy", "corridormodevalue"),
        "CorridorMargin": ("corridormargin", "margin", "voidmargin"),
        "Notes": ("notes", "note", "remarks", "remark"),
        "ShapeSourcePath": ("shapesourcepath", "shapepath", "sourcepath", "modelpath"),
        "ScaleFactor": ("scalefactor", "scale"),
        "PlacementMode": ("placementmode", "placemode"),
        "UseSourceBaseAsBottom": ("usesourcebaseasbottom", "sourcebaseasbottom", "alignsourcebasetobottom"),
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
        return 0

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

        row_shape = QtWidgets.QHBoxLayout()
        self.btn_browse_shape = QtWidgets.QPushButton("Browse Shape")
        self.btn_pick_fcstd_object = QtWidgets.QPushButton("Pick FCStd Object")
        self.lbl_shape_status = QtWidgets.QLabel("External shape row: no selection")
        self.lbl_shape_status.setWordWrap(True)
        row_shape.addWidget(self.btn_browse_shape)
        row_shape.addWidget(self.btn_pick_fcstd_object)
        row_shape.addWidget(self.lbl_shape_status, 1)
        main.addLayout(row_shape)

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
            (13, 110),
            (14, 130),
            (15, 95),
            (16, 95),
            (17, 110),
            (18, 90),
            (19, 85),
            (20, 120),
            (21, 110),
            (22, 220),
            (23, 220),
            (24, 90),
            (25, 130),
            (26, 150),
        ):
            self.table.setColumnWidth(col, width)
        main.addWidget(self.table)

        row_btn = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Row")
        self.btn_remove = QtWidgets.QPushButton("Remove Row")
        self.btn_sort = QtWidgets.QPushButton("Sort by Start")
        self.btn_apply = QtWidgets.QPushButton("Apply")
        self.btn_close = QtWidgets.QPushButton("Close")
        row_btn.addWidget(self.btn_add)
        row_btn.addWidget(self.btn_remove)
        row_btn.addWidget(self.btn_sort)
        row_btn.addWidget(self.btn_apply)
        row_btn.addWidget(self.btn_close)
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
            + "\nAllowed GeometryMode: "
            + ", ".join([m for m in ALLOWED_GEOMETRY_MODES if m])
            + "\nAllowed TemplateName: "
            + ", ".join([m for m in ALLOWED_TEMPLATE_NAMES if m])
            + "\nAllowed PlacementMode: "
            + ", ".join([m for m in ALLOWED_PLACEMENT_MODES if m])
            + "\nAllowed CorridorMode: "
            + ", ".join([m for m in ALLOWED_CORRIDOR_MODES if m])
            + "\nRecommended Geometry:"
            + "\n- culvert -> template / box_culvert"
            + "\n- crossing -> template / utility_crossing"
            + "\n- retaining_wall -> template / retaining_wall"
            + "\n- abutment_zone -> template / abutment_block"
            + "\n- bridge_zone, other -> box"
            + "\n- external imported models -> external_shape"
            + "\nRecommended CorridorMode:"
            + "\n- culvert, crossing -> notch"
            + "\n- bridge_zone, abutment_zone -> skip_zone"
            + "\n- retaining_wall -> split_only"
            + "\nVertical input policy:"
            + "\n- culvert, crossing -> Cover enabled / BottomElevation disabled"
            + "\n- retaining_wall, abutment_zone, bridge_zone -> BottomElevation enabled / Cover disabled"
            + "\n- other -> both enabled"
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
        self.btn_browse_shape.clicked.connect(self._on_browse_shape)
        self.btn_pick_fcstd_object.clicked.connect(self._on_pick_fcstd_object)
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_sort.clicked.connect(self._sort_rows)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_close.clicked.connect(self.reject)
        self.table.itemSelectionChanged.connect(self._update_shape_status)
        self.table.itemChanged.connect(self._on_table_item_changed)

        self._set_rows(3)
        self._update_shape_status()
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
                self._apply_vertical_input_policy(r)
                self._apply_shape_source_visual(r)
        finally:
            self._loading = False

    def _ensure_combo_cells(self, row):
        for col, items in COMBO_COLUMN_ITEMS.items():
            cmb = self.table.cellWidget(row, col)
            if cmb is None:
                cmb = QtWidgets.QComboBox()
                cmb.addItems(list(items))
                self.table.setCellWidget(row, col, cmb)
                if col == 1:
                    cmb.currentTextChanged.connect(lambda _txt, rr=row: self._on_type_changed(rr))
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
            if c == 23:
                self._update_shape_status()
            return
        it = self.table.item(r, c)
        if it is None:
            it = QtWidgets.QTableWidgetItem("")
            self.table.setItem(r, c, it)
        it.setText(str(txt or ""))
        if c == 23:
            self._update_shape_status()

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

    def _set_item_enabled(self, row, col, enabled, tooltip=""):
        it = self.table.item(row, col)
        if it is None:
            it = QtWidgets.QTableWidgetItem("")
            self.table.setItem(row, col, it)
        flags = QtCore.Qt.ItemIsSelectable
        if enabled:
            flags |= QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
        it.setFlags(flags)
        it.setToolTip(str(tooltip or ""))
        try:
            if enabled:
                it.setForeground(self.table.palette().brush(QtGui.QPalette.Text))
                it.setBackground(self.table.palette().brush(QtGui.QPalette.Base))
            else:
                it.setForeground(self.table.palette().brush(QtGui.QPalette.Disabled, QtGui.QPalette.Text))
                it.setBackground(self.table.palette().brush(QtGui.QPalette.Disabled, QtGui.QPalette.Base))
        except Exception:
            pass

    def _apply_vertical_input_policy(self, row):
        try:
            use_bottom, use_cover, note = _vertical_input_policy(self._get_cell_text(int(row), 1))
            self._set_item_enabled(int(row), 9, use_bottom, note)
            self._set_item_enabled(int(row), 10, use_cover, note)
        except Exception:
            pass

    def _apply_shape_source_visual(self, row):
        try:
            it = self.table.item(int(row), 23)
            if it is None:
                it = QtWidgets.QTableWidgetItem("")
                self.table.setItem(int(row), 23, it)
            geom = self._get_cell_text(int(row), 13).strip()
            src = self._get_cell_text(int(row), 23).strip()
            src_file, src_obj = _split_shape_source_path(src)
            if geom != "external_shape":
                it.setToolTip("ShapeSourcePath is used only when GeometryMode=external_shape.")
                it.setForeground(self.table.palette().brush(QtGui.QPalette.Text))
                it.setBackground(self.table.palette().brush(QtGui.QPalette.Base))
                return
            if not src:
                it.setToolTip("ShapeSourcePath is required for GeometryMode=external_shape.")
                it.setForeground(QtGui.QBrush(QtGui.QColor(150, 40, 40)))
                it.setBackground(QtGui.QBrush(QtGui.QColor(255, 238, 238)))
                return
            if str(src_file).lower().endswith(".fcstd") and not src_obj:
                it.setToolTip("FCStd external shape requires 'path.FCStd#ObjectName'.")
                it.setForeground(QtGui.QBrush(QtGui.QColor(150, 40, 40)))
                it.setBackground(QtGui.QBrush(QtGui.QColor(255, 238, 238)))
                return
            if os.path.isfile(src_file):
                it.setToolTip(f"External shape file found:\n{src}")
                it.setForeground(self.table.palette().brush(QtGui.QPalette.Text))
                it.setBackground(QtGui.QBrush(QtGui.QColor(238, 255, 238)))
            else:
                it.setToolTip(f"External shape file not found:\n{src}")
                it.setForeground(QtGui.QBrush(QtGui.QColor(150, 40, 40)))
                it.setBackground(QtGui.QBrush(QtGui.QColor(255, 238, 238)))
        except Exception:
            pass

    def _on_type_changed(self, row):
        if self._loading:
            return
        try:
            typ = self._get_cell_text(int(row), 1).strip()
            current_geom = self._get_cell_text(int(row), 13).strip()
            current_tpl = self._get_cell_text(int(row), 14).strip()
            current_mode = self._get_cell_text(int(row), 20).strip()
            rec_geom = _recommended_geometry_mode(typ)
            rec_tpl = _recommended_template_name(typ)
            rec_mode = _recommended_corridor_mode(typ)
            if (not current_geom) and rec_geom:
                self._set_cell_text(int(row), 13, rec_geom)
            if (not current_tpl) and rec_tpl:
                self._set_cell_text(int(row), 14, rec_tpl)
            if (not current_mode) and rec_mode:
                self._set_cell_text(int(row), 20, rec_mode)
            self._apply_vertical_input_policy(int(row))
            self._apply_shape_source_visual(int(row))
        except Exception:
            pass

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
                self._set_cell_text(i, 13, rec.get("GeometryMode", ""))
                self._set_cell_text(i, 14, rec.get("TemplateName", ""))
                self._set_cell_text(i, 15, f"{float(rec.get('WallThickness', 0.0)):.3f}")
                self._set_cell_text(i, 16, f"{float(rec.get('FootingWidth', 0.0)):.3f}")
                self._set_cell_text(i, 17, f"{float(rec.get('FootingThickness', 0.0)):.3f}")
                self._set_cell_text(i, 18, f"{float(rec.get('CapHeight', 0.0)):.3f}")
                self._set_cell_text(i, 19, f"{float(rec.get('CellCount', 0.0)):.0f}")
                self._set_cell_text(i, 20, rec.get("CorridorMode", ""))
                self._set_cell_text(i, 21, f"{float(rec.get('CorridorMargin', 0.0)):.3f}")
                self._set_cell_text(i, 22, rec.get("Notes", ""))
                self._set_cell_text(i, 23, rec.get("ShapeSourcePath", ""))
                self._set_cell_text(i, 24, f"{float(rec.get('ScaleFactor', 1.0) or 1.0):.3f}")
                self._set_cell_text(i, 25, rec.get("PlacementMode", ""))
                self._set_cell_text(i, 26, rec.get("UseSourceBaseAsBottom", ""))
                self._apply_vertical_input_policy(i)
            self.lbl_status.setText(str(getattr(obj, "Status", "Loaded")))
        finally:
            self._loading = False
        self._update_shape_status()

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
                    "GeometryMode": row[13],
                    "TemplateName": row[14],
                    "WallThickness": self._get_cell_float(r, 15),
                    "FootingWidth": self._get_cell_float(r, 16),
                    "FootingThickness": self._get_cell_float(r, 17),
                    "CapHeight": self._get_cell_float(r, 18),
                    "CellCount": self._get_cell_float(r, 19),
                    "CorridorMode": row[20],
                    "CorridorMargin": self._get_cell_float(r, 21),
                    "Notes": row[22],
                    "ShapeSourcePath": row[23],
                    "ScaleFactor": self._get_cell_float(r, 24) or 1.0,
                    "PlacementMode": row[25],
                    "UseSourceBaseAsBottom": row[26],
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
        self._update_shape_status()

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
                self._set_cell_text(i, 13, rec.get("GeometryMode", ""))
                self._set_cell_text(i, 14, rec.get("TemplateName", ""))
                self._set_cell_text(i, 15, f"{float(rec.get('WallThickness', 0.0)):.3f}")
                self._set_cell_text(i, 16, f"{float(rec.get('FootingWidth', 0.0)):.3f}")
                self._set_cell_text(i, 17, f"{float(rec.get('FootingThickness', 0.0)):.3f}")
                self._set_cell_text(i, 18, f"{float(rec.get('CapHeight', 0.0)):.3f}")
                self._set_cell_text(i, 19, f"{float(rec.get('CellCount', 0.0)):.0f}")
                self._set_cell_text(i, 20, rec.get("CorridorMode", ""))
                self._set_cell_text(i, 21, f"{float(rec.get('CorridorMargin', 0.0)):.3f}")
                self._set_cell_text(i, 22, rec["Notes"])
                self._set_cell_text(i, 23, rec.get("ShapeSourcePath", ""))
                self._set_cell_text(i, 24, f"{float(rec.get('ScaleFactor', 1.0) or 1.0):.3f}")
                self._set_cell_text(i, 25, rec.get("PlacementMode", ""))
                self._set_cell_text(i, 26, rec.get("UseSourceBaseAsBottom", ""))
                self._apply_vertical_input_policy(i)
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

    def _on_browse_shape(self):
        row = int(self.table.currentRow())
        if row < 0:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Select a structure row first.")
            return
        current = self._get_cell_text(row, 23).strip()
        current_file, current_obj = _split_shape_source_path(current)
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select external shape file",
            current_file or current,
            "External Shape Files (*.step *.stp *.brep *.brp *.FCStd);;All Files (*.*)",
        )
        if path:
            if str(path).lower().endswith(".fcstd") and current_obj:
                self._set_cell_text(row, 23, f"{path}#{current_obj}")
            else:
                self._set_cell_text(row, 23, str(path))
            self._update_shape_status()

    @staticmethod
    def _fcstd_shape_candidates(path: str):
        src_file, _src_obj = _split_shape_source_path(path)
        if not src_file or not str(src_file).lower().endswith(".fcstd"):
            return [], "not_fcstd"
        if not os.path.isfile(src_file):
            return [], "not_found"

        doc_ref = None
        opened_here = False
        try:
            for d in list(getattr(App, "listDocuments", lambda: {})().values()):
                try:
                    if os.path.abspath(str(getattr(d, "FileName", "") or "")) == src_file:
                        doc_ref = d
                        break
                except Exception:
                    continue
            if doc_ref is None:
                try:
                    doc_ref = App.openDocument(src_file, True)
                except Exception:
                    try:
                        doc_ref = App.openDocument(src_file, hidden=True)
                    except Exception:
                        doc_ref = App.openDocument(src_file)
                opened_here = doc_ref is not None
            if doc_ref is None:
                return [], "open_failed"

            items = []
            for obj in list(getattr(doc_ref, "Objects", []) or []):
                try:
                    shp = getattr(obj, "Shape", None)
                    if shp is None or shp.isNull():
                        continue
                    name = str(getattr(obj, "Name", "") or "").strip()
                    label = str(getattr(obj, "Label", "") or "").strip()
                    if not name:
                        continue
                    display = name if not label or label == name else f"{name} | {label}"
                    items.append((display, name))
                except Exception:
                    continue
            return items, "ok"
        except Exception:
            return [], "open_failed"
        finally:
            if opened_here and doc_ref is not None:
                try:
                    App.closeDocument(str(doc_ref.Name))
                except Exception:
                    pass

    def _on_pick_fcstd_object(self):
        row = int(self.table.currentRow())
        if row < 0:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Select a structure row first.")
            return

        current = self._get_cell_text(row, 23).strip()
        src_file, current_obj = _split_shape_source_path(current)
        if not src_file:
            QtWidgets.QMessageBox.information(
                None,
                "Edit Structures",
                "Select an .FCStd file first in ShapeSourcePath or with Browse Shape.",
            )
            return
        if not str(src_file).lower().endswith(".fcstd"):
            QtWidgets.QMessageBox.information(
                None,
                "Edit Structures",
                "FCStd object picker works only when ShapeSourcePath points to an .FCStd file.",
            )
            return

        items, status = self._fcstd_shape_candidates(src_file)
        if status == "not_found":
            QtWidgets.QMessageBox.warning(None, "Edit Structures", f"FCStd file not found:\n{src_file}")
            return
        if status != "ok":
            QtWidgets.QMessageBox.warning(None, "Edit Structures", f"Could not open FCStd file:\n{src_file}")
            return
        if not items:
            QtWidgets.QMessageBox.warning(
                None,
                "Edit Structures",
                "No shape-bearing objects were found in the selected FCStd file.",
            )
            return

        labels = [it[0] for it in items]
        initial = 0
        if current_obj:
            for i, (_display, obj_name) in enumerate(items):
                if obj_name == current_obj:
                    initial = i
                    break
        picked, ok = QtWidgets.QInputDialog.getItem(
            None,
            "Pick FCStd Object",
            "Object:",
            labels,
            initial,
            False,
        )
        if not ok or not picked:
            return
        obj_name = items[labels.index(str(picked))][1]
        self._set_cell_text(row, 23, f"{src_file}#{obj_name}")
        self._update_shape_status()

    def _update_shape_status(self):
        row = int(self.table.currentRow())
        if row < 0:
            self.lbl_shape_status.setText("External shape row: no selection")
            return
        geom = self._get_cell_text(row, 13).strip()
        src = self._get_cell_text(row, 23).strip()
        src_file, src_obj = _split_shape_source_path(src)
        rid = self._get_cell_text(row, 0).strip() or f"row {row + 1}"
        self._apply_shape_source_visual(row)
        if geom != "external_shape":
            self.lbl_shape_status.setText(f"External shape row: {rid} is not using GeometryMode=external_shape")
            return
        if not src:
            self.lbl_shape_status.setText(f"External shape row: {rid} has no ShapeSourcePath")
            return
        if str(src_file).lower().endswith(".fcstd") and not src_obj:
            self.lbl_shape_status.setText(
                f"External shape row: {rid} | FCSTD OBJECT MISSING | use path.FCStd#ObjectName"
            )
            return
        ok = os.path.isfile(src_file)
        kind = "FCSTD" if str(src_file).lower().endswith(".fcstd") else "FILE"
        suffix = f" | object={src_obj}" if src_obj else ""
        self.lbl_shape_status.setText(
            f"External shape row: {rid} | {kind} | {'FOUND' if ok else 'NOT FOUND'}{suffix} | {src}"
        )

    def _on_table_item_changed(self, item):
        if self._loading:
            return
        try:
            if item is not None and int(item.column()) in (13, 23):
                self._apply_shape_source_visual(int(item.row()))
                self._update_shape_status()
        except Exception:
            pass

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
                            "GeometryMode": str(row.get(mapping.get("GeometryMode"), "") or "").strip(),
                            "TemplateName": str(row.get(mapping.get("TemplateName"), "") or "").strip(),
                            "WallThickness": self._parse_float(row.get(mapping.get("WallThickness"), "")),
                            "FootingWidth": self._parse_float(row.get(mapping.get("FootingWidth"), "")),
                            "FootingThickness": self._parse_float(row.get(mapping.get("FootingThickness"), "")),
                            "CapHeight": self._parse_float(row.get(mapping.get("CapHeight"), "")),
                            "CellCount": self._parse_float(row.get(mapping.get("CellCount"), "")),
                            "CorridorMode": str(row.get(mapping.get("CorridorMode"), "") or "").strip(),
                            "CorridorMargin": self._parse_float(row.get(mapping.get("CorridorMargin"), "")),
                            "Notes": str(row.get(mapping.get("Notes"), "") or "").strip(),
                            "ShapeSourcePath": str(row.get(mapping.get("ShapeSourcePath"), "") or "").strip(),
                            "ScaleFactor": self._parse_float(row.get(mapping.get("ScaleFactor"), "")) or 1.0,
                            "PlacementMode": str(row.get(mapping.get("PlacementMode"), "") or "").strip(),
                            "UseSourceBaseAsBottom": str(row.get(mapping.get("UseSourceBaseAsBottom"), "") or "").strip(),
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
                self._set_cell_text(i, 13, rec.get("GeometryMode", ""))
                self._set_cell_text(i, 14, rec.get("TemplateName", ""))
                self._set_cell_text(i, 15, f"{float(rec.get('WallThickness', 0.0)):.3f}")
                self._set_cell_text(i, 16, f"{float(rec.get('FootingWidth', 0.0)):.3f}")
                self._set_cell_text(i, 17, f"{float(rec.get('FootingThickness', 0.0)):.3f}")
                self._set_cell_text(i, 18, f"{float(rec.get('CapHeight', 0.0)):.3f}")
                self._set_cell_text(i, 19, f"{float(rec.get('CellCount', 0.0)):.0f}")
                self._set_cell_text(i, 20, rec.get("CorridorMode", ""))
                self._set_cell_text(i, 21, f"{float(rec.get('CorridorMargin', 0.0)):.3f}")
                self._set_cell_text(i, 22, rec["Notes"])
                self._set_cell_text(i, 23, rec.get("ShapeSourcePath", ""))
                self._set_cell_text(i, 24, f"{float(rec.get('ScaleFactor', 1.0) or 1.0):.3f}")
                self._set_cell_text(i, 25, rec.get("PlacementMode", ""))
                self._set_cell_text(i, 26, rec.get("UseSourceBaseAsBottom", ""))
                self._apply_vertical_input_policy(i)
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
            obj.GeometryModes = [str(r["GeometryMode"] or "") for r in rows]
            obj.TemplateNames = [str(r["TemplateName"] or "") for r in rows]
            obj.WallThicknesses = [float(r["WallThickness"]) for r in rows]
            obj.FootingWidths = [float(r["FootingWidth"]) for r in rows]
            obj.FootingThicknesses = [float(r["FootingThickness"]) for r in rows]
            obj.CapHeights = [float(r["CapHeight"]) for r in rows]
            obj.CellCounts = [float(r["CellCount"]) for r in rows]
            obj.CorridorModes = [str(r["CorridorMode"] or "") for r in rows]
            obj.CorridorMargins = [float(r["CorridorMargin"]) for r in rows]
            obj.Notes = [str(r["Notes"] or "") for r in rows]
            obj.ShapeSourcePaths = [str(r["ShapeSourcePath"] or "") for r in rows]
            obj.ScaleFactors = [float(r["ScaleFactor"] or 1.0) for r in rows]
            obj.PlacementModes = [str(r["PlacementMode"] or "") for r in rows]
            obj.UseSourceBaseAsBottoms = [str(r["UseSourceBaseAsBottom"] or "") for r in rows]
            obj.touch()

            prj = find_project(self.doc)
            if prj is not None:
                link_project(prj, links={"StructureSet": obj}, adopt_extra=[obj])

            self.doc.recompute()
            issues = StructureSet.validate(obj)
            shape_status_notes = list(getattr(obj, "ResolvedShapeStatusNotes", []) or [])
            frame_status_notes = list(getattr(obj, "ResolvedFrameStatusNotes", []) or [])
            st = getattr(prj, "Stationing", None) if prj is not None and hasattr(prj, "Stationing") else None
            if st is None:
                st = _find_stationing(self.doc)
            self.lbl_status.setText(str(getattr(obj, "Status", "Applied")))
            try:
                obj.ViewObject.Visibility = True
            except Exception:
                pass
            if issues:
                msg = [
                    "Structure set saved with validation warnings.",
                    f"Records: {len(rows)}",
                ]
                msg.extend(list(issues[:10]))
                if shape_status_notes:
                    msg.append("")
                    msg.append("External shape diagnostics:")
                    msg.extend(list(shape_status_notes[:10]))
                if frame_status_notes:
                    msg.append("")
                    msg.append("Frame diagnostics:")
                    msg.extend(list(frame_status_notes[:10]))
                QtWidgets.QMessageBox.information(
                    None,
                    "Edit Structures",
                    "\n".join(msg),
                )
            else:
                msg = [f"Structure set saved.\nRecords: {len(rows)}"]
                if shape_status_notes:
                    msg.append("")
                    msg.append("External shape diagnostics:")
                    msg.extend(list(shape_status_notes[:10]))
                if frame_status_notes:
                    msg.append("")
                    msg.append("Frame diagnostics:")
                    msg.extend(list(frame_status_notes[:10]))
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
