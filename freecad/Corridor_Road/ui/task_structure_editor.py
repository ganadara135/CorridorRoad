# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

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

PROFILE_COL_HEADERS = [
    "StructureId",
    "Station",
    "Offset",
    "Width",
    "Height",
    "BottomElevation",
    "Cover",
    "WallThickness",
    "FootingWidth",
    "FootingThickness",
    "CapHeight",
    "CellCount",
]

BASIC_VISIBLE_COLS = {0, 1, 2, 3, 4, 5, 6, 7, 8, 13, 20}
TEMPLATE_COLS = {14, 15, 16, 17, 18, 19}
EXTERNAL_SHAPE_COLS = {23, 24, 25, 26}
ADVANCED_COLS = {9, 10, 11, 12, 21, 22}
COMMON_STRUCTURE_TYPES = ["culvert", "crossing", "retaining_wall", "abutment_zone", "bridge_zone", "other", "external_shape"]
STRUCTURE_PRESET_NAMES = [
    "Drainage Sample",
    "Wall Sample",
    "Mixed Sample",
    "Variable Size Sample",
]
PROFILE_PRESET_NAMES = [
    "2-Point Linear",
    "3-Point Mid Bulge",
    "3-Point Mid Narrow",
    "Culvert 1-2-1 Cells",
    "Crossing Shallow Mid",
    "Wall Step-Up",
    "Wall Step-Down",
]
DETAIL_FIELD_SPECS = [
    ("BehaviorMode", 12, "combo"),
    ("BottomElevation", 9, "line"),
    ("Cover", 10, "line"),
    ("RotationDeg", 11, "line"),
    ("GeometryMode", 13, "combo"),
    ("TemplateName", 14, "combo"),
    ("WallThickness", 15, "line"),
    ("FootingWidth", 16, "line"),
    ("FootingThickness", 17, "line"),
    ("CapHeight", 18, "line"),
    ("CellCount", 19, "line"),
    ("CorridorMode", 20, "combo"),
    ("CorridorMargin", 21, "line"),
    ("ShapeSourcePath", 23, "line"),
    ("ScaleFactor", 24, "line"),
    ("PlacementMode", 25, "combo"),
    ("UseSourceBaseAsBottom", 26, "combo"),
    ("Notes", 22, "line"),
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


class _RowAwareComboBox(QtWidgets.QComboBox):
    def __init__(self, on_interact=None, parent=None):
        super().__init__(parent)
        self._on_interact = on_interact

    def _notify_interact(self):
        cb = getattr(self, "_on_interact", None)
        if cb is None:
            return
        try:
            cb(self)
        except Exception:
            pass

    def mousePressEvent(self, event):
        self._notify_interact()
        super().mousePressEvent(event)

    def focusInEvent(self, event):
        self._notify_interact()
        super().focusInEvent(event)

    def showPopup(self):
        self._notify_interact()
        super().showPopup()


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


def _earthwork_behavior_text(structure_type: str, corridor_mode: str) -> str:
    typ = str(structure_type or "").strip().lower()
    mode = str(corridor_mode or "").strip().lower()
    if typ in ("culvert", "crossing"):
        return f"{mode or 'notch'} earthwork / buried crossing behavior"
    if typ == "retaining_wall":
        return f"{mode or 'split_only'} retaining wall side override"
    if typ in ("abutment_zone", "bridge_zone"):
        return f"{mode or 'skip_zone'} bridge/abutment trim zone"
    if typ == "other":
        return f"{mode or 'none'} generic structure behavior"
    return mode or "not set"


def _default_profile_preset_for_structure_type(structure_type: str) -> str:
    typ = str(structure_type or "").strip().lower()
    if typ == "culvert":
        return "Culvert 1-2-1 Cells"
    if typ == "crossing":
        return "Crossing Shallow Mid"
    if typ == "retaining_wall":
        return "Wall Step-Up"
    if typ == "abutment_zone":
        return "3-Point Mid Bulge"
    if typ in ("bridge_zone", "other"):
        return "2-Point Linear"
    return "2-Point Linear"


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


def _structure_profile_csv_mapping(fieldnames):
    cols = list(fieldnames or [])
    by_norm = {_norm_col(c): c for c in cols}
    aliases = {
        "StructureId": ("structureid", "id", "parentid"),
        "Station": ("station", "sta"),
        "Offset": ("offset",),
        "Width": ("width",),
        "Height": ("height",),
        "BottomElevation": ("bottomelevation", "invert", "baseelevation"),
        "Cover": ("cover",),
        "WallThickness": ("wallthickness", "wall", "wallthk"),
        "FootingWidth": ("footingwidth", "footing", "basewidth"),
        "FootingThickness": ("footingthickness", "basethickness"),
        "CapHeight": ("capheight", "cap", "topcapheight"),
        "CellCount": ("cellcount", "cells", "numberofcells"),
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
        self._profile_rows = []
        self._active_profile_structure_id = ""
        self._active_structure_row = -1
        self._enforcing_structure_selection = False
        self._loading = False
        self.form = self._build_ui()
        self._refresh_context()

    @staticmethod
    def _brush(color_hex: str):
        return QtGui.QBrush(QtGui.QColor(color_hex))

    def _item_brushes(self):
        return {
            "text": self._brush("#ececec"),
            "base": self._brush("#2f2f2f"),
            "disabled_text": self._brush("#989898"),
            "disabled_base": self._brush("#262626"),
            "ok_base": self._brush("#2f2f2f"),
            "warn_base": self._brush("#5a481c"),
            "err_base": self._brush("#5a2323"),
            "good_base": self._brush("#1f4d36"),
        }

    @staticmethod
    def _apply_table_theme(table):
        try:
            table.setMouseTracking(False)
            table.viewport().setMouseTracking(False)
            table.setFocusPolicy(QtCore.Qt.ClickFocus)
            table.setAttribute(QtCore.Qt.WA_Hover, False)
            table.viewport().setAttribute(QtCore.Qt.WA_Hover, False)
        except Exception:
            pass
        table.setStyleSheet(
            """
            QTableWidget {
                background-color: #2f2f2f;
                color: #ececec;
                gridline-color: #505050;
                selection-background-color: #4a90d9;
                selection-color: #ffffff;
            }
            QTableWidget::item {
                background-color: #2f2f2f;
                color: #ececec;
            }
            QTableWidget::item:hover {
                background-color: #2f2f2f;
                color: #ececec;
            }
            QTableWidget::item:selected {
                background-color: #4a90d9;
                color: #ffffff;
            }
            QTableWidget QLineEdit {
                background-color: #2f2f2f;
                color: #ececec;
                selection-background-color: #4a90d9;
                selection-color: #ffffff;
            }
            QTableWidget QComboBox {
                background-color: #3a3a3a;
                color: #ececec;
                selection-background-color: #4a90d9;
                selection-color: #ffffff;
            }
            """
        )

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

        row_profile_csv = QtWidgets.QHBoxLayout()
        self.ed_profile_csv = QtWidgets.QLineEdit()
        self.ed_profile_csv.setPlaceholderText("Optional structure station-profile CSV path")
        self.btn_browse_profile_csv = QtWidgets.QPushButton("Browse Profile CSV")
        self.btn_load_profile_csv = QtWidgets.QPushButton("Load Profile CSV")
        row_profile_csv.addWidget(self.ed_profile_csv, 1)
        row_profile_csv.addWidget(self.btn_browse_profile_csv)
        row_profile_csv.addWidget(self.btn_load_profile_csv)
        main.addLayout(row_profile_csv)

        self.lbl_profile_status = QtWidgets.QLabel("Station-profile points: 0")
        self.lbl_profile_status.setWordWrap(True)
        main.addWidget(self.lbl_profile_status)

        row_structure_preset = QtWidgets.QHBoxLayout()
        self.cmb_structure_preset = QtWidgets.QComboBox()
        self.cmb_structure_preset.addItems(list(STRUCTURE_PRESET_NAMES))
        self.btn_load_structure_preset = QtWidgets.QPushButton("Load Preset")
        row_structure_preset.addWidget(QtWidgets.QLabel("Preset:"))
        row_structure_preset.addWidget(self.cmb_structure_preset)
        row_structure_preset.addWidget(self.btn_load_structure_preset)
        row_structure_preset.addStretch(1)
        main.addLayout(row_structure_preset)

        row_shape = QtWidgets.QHBoxLayout()
        self.btn_browse_shape = QtWidgets.QPushButton("Browse Shape")
        self.btn_pick_fcstd_object = QtWidgets.QPushButton("Pick FCStd Object")
        self.lbl_shape_status = QtWidgets.QLabel("External shape row: no selection")
        self.lbl_shape_status.setWordWrap(True)
        row_shape.addWidget(self.btn_browse_shape)
        row_shape.addWidget(self.btn_pick_fcstd_object)
        row_shape.addWidget(self.lbl_shape_status, 1)
        main.addLayout(row_shape)

        row_column_filters = QtWidgets.QHBoxLayout()
        self.chk_cols_basic = QtWidgets.QCheckBox("Basic")
        self.chk_cols_template = QtWidgets.QCheckBox("Template")
        self.chk_cols_external = QtWidgets.QCheckBox("External Shape")
        self.chk_cols_advanced = QtWidgets.QCheckBox("Advanced")
        self.chk_cols_basic.setChecked(True)
        self.chk_cols_template.setChecked(False)
        self.chk_cols_external.setChecked(False)
        self.chk_cols_advanced.setChecked(False)
        self.chk_cols_basic.setEnabled(False)
        row_column_filters.addWidget(QtWidgets.QLabel("Columns:"))
        row_column_filters.addWidget(self.chk_cols_basic)
        row_column_filters.addWidget(self.chk_cols_template)
        row_column_filters.addWidget(self.chk_cols_external)
        row_column_filters.addWidget(self.chk_cols_advanced)
        row_column_filters.addStretch(1)
        main.addLayout(row_column_filters)

        row_quick = QtWidgets.QHBoxLayout()
        self.cmb_common_structure = QtWidgets.QComboBox()
        self.cmb_common_structure.addItems(list(COMMON_STRUCTURE_TYPES))
        self.btn_add_common_structure = QtWidgets.QPushButton("Add Common Structure")
        self.btn_clone_structure = QtWidgets.QPushButton("Clone Selected")
        row_quick.addWidget(QtWidgets.QLabel("Quick Add:"))
        row_quick.addWidget(self.cmb_common_structure)
        row_quick.addWidget(self.btn_add_common_structure)
        row_quick.addWidget(self.btn_clone_structure)
        row_quick.addStretch(1)
        main.addLayout(row_quick)

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
        self._apply_table_theme(self.table)
        self._apply_default_column_visibility()
        main.addWidget(self.table)

        row_structure_btn = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Row")
        self.btn_remove = QtWidgets.QPushButton("Remove Row")
        self.btn_sort = QtWidgets.QPushButton("Sort by Start")
        row_structure_btn.addWidget(self.btn_add)
        row_structure_btn.addWidget(self.btn_remove)
        row_structure_btn.addWidget(self.btn_sort)
        row_structure_btn.addStretch(1)
        main.addLayout(row_structure_btn)

        self.gb_details = QtWidgets.QGroupBox("Selected Structure Details")
        fd = QtWidgets.QGridLayout(self.gb_details)
        fd.setContentsMargins(8, 8, 8, 8)
        fd.setHorizontalSpacing(10)
        fd.setVerticalSpacing(6)
        self._detail_widgets = {}
        for idx, (label, col, kind) in enumerate(DETAIL_FIELD_SPECS):
            if kind == "combo":
                w_detail = QtWidgets.QComboBox()
                if col in COMBO_COLUMN_ITEMS:
                    w_detail.addItems(list(COMBO_COLUMN_ITEMS[col]))
                w_detail.currentTextChanged.connect(lambda _txt, cc=col: self._on_detail_widget_changed(cc))
            else:
                w_detail = QtWidgets.QLineEdit()
                w_detail.editingFinished.connect(lambda cc=col: self._on_detail_widget_changed(cc))
            self._detail_widgets[col] = w_detail
            row = idx // 2
            block = idx % 2
            label_widget = QtWidgets.QLabel(f"{label}:")
            label_widget.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            fd.addWidget(label_widget, row, block * 2)
            fd.addWidget(w_detail, row, block * 2 + 1)
        fd.setColumnStretch(1, 1)
        fd.setColumnStretch(3, 1)
        main.addWidget(self.gb_details)

        self.lbl_profile_table = QtWidgets.QLabel("Station profiles for selected structure: no selection")
        self.lbl_profile_table.setWordWrap(True)
        main.addWidget(self.lbl_profile_table)

        row_profile_preset = QtWidgets.QHBoxLayout()
        self.cmb_profile_preset = QtWidgets.QComboBox()
        self.cmb_profile_preset.addItems(list(PROFILE_PRESET_NAMES))
        self.chk_profile_preset_append = QtWidgets.QCheckBox("Append")
        self.btn_load_profile_preset = QtWidgets.QPushButton("Load Profile Preset")
        row_profile_preset.addWidget(QtWidgets.QLabel("Profile Preset:"))
        row_profile_preset.addWidget(self.cmb_profile_preset)
        row_profile_preset.addWidget(self.chk_profile_preset_append)
        row_profile_preset.addWidget(self.btn_load_profile_preset)
        row_profile_preset.addStretch(1)
        main.addLayout(row_profile_preset)

        self.profile_table = QtWidgets.QTableWidget(0, len(PROFILE_COL_HEADERS))
        self.profile_table.setHorizontalHeaderLabels(PROFILE_COL_HEADERS)
        profile_hdr = self.profile_table.horizontalHeader()
        profile_hdr.setStretchLastSection(False)
        try:
            profile_hdr.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        except Exception:
            pass
        self.profile_table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.profile_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.profile_table.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.profile_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.profile_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.profile_table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        for col, width in (
            (0, 110),
            (1, 105),
            (2, 90),
            (3, 90),
            (4, 90),
            (5, 120),
            (6, 90),
            (7, 95),
            (8, 95),
            (9, 110),
            (10, 90),
            (11, 85),
        ):
            self.profile_table.setColumnWidth(col, width)
        self._apply_table_theme(self.profile_table)
        main.addWidget(self.profile_table)

        row_profile_btn = QtWidgets.QHBoxLayout()
        self.btn_add_profile = QtWidgets.QPushButton("Add Profile Row")
        self.btn_remove_profile = QtWidgets.QPushButton("Remove Profile Row")
        self.btn_sort_profile = QtWidgets.QPushButton("Sort by Station")
        self.btn_duplicate_profile = QtWidgets.QPushButton("Duplicate Profile Row")
        self.btn_add_profile_midpoint = QtWidgets.QPushButton("Add Midpoint")
        self.btn_clear_profile = QtWidgets.QPushButton("Delete All for Selected")
        row_profile_btn.addWidget(self.btn_add_profile)
        row_profile_btn.addWidget(self.btn_remove_profile)
        row_profile_btn.addWidget(self.btn_sort_profile)
        row_profile_btn.addWidget(self.btn_duplicate_profile)
        row_profile_btn.addStretch(1)
        main.addLayout(row_profile_btn)

        row_profile_actions = QtWidgets.QHBoxLayout()
        row_profile_actions.addWidget(self.btn_add_profile_midpoint)
        row_profile_actions.addWidget(self.btn_clear_profile)
        row_profile_actions.addStretch(1)
        self.btn_apply = QtWidgets.QPushButton("Apply")
        self.btn_close = QtWidgets.QPushButton("Close")
        row_profile_actions.addWidget(self.btn_apply)
        row_profile_actions.addWidget(self.btn_close)
        main.addLayout(row_profile_actions)

        gb_status = QtWidgets.QGroupBox("Validation Guide")
        fg = QtWidgets.QFormLayout(gb_status)
        self.lbl_status = QtWidgets.QLabel("Idle")
        self.lbl_status.setWordWrap(True)
        self.lbl_validation_summary = QtWidgets.QLabel("Validation summary: idle")
        self.lbl_validation_summary.setWordWrap(True)
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
             + "\nAdvanced station-profile workflow:"
             + "\n- load the base structure header CSV first"
             + "\n- then load the station-profile CSV"
             + "\n- Apply saves both datasets into the same StructureSet"
         )
        self.lbl_help.setWordWrap(True)
        fg.addRow("Status:", self.lbl_status)
        fg.addRow("Validation:", self.lbl_validation_summary)
        fg.addRow(self.lbl_help)
        main.addWidget(gb_status)

        self.btn_refresh.clicked.connect(self._refresh_context)
        self.cmb_target.currentIndexChanged.connect(self._on_target_changed)
        self.btn_browse_csv.clicked.connect(self._on_browse_csv)
        self.btn_load_csv.clicked.connect(self._on_load_csv)
        self.btn_browse_profile_csv.clicked.connect(self._on_browse_profile_csv)
        self.btn_load_profile_csv.clicked.connect(self._on_load_profile_csv)
        self.btn_browse_shape.clicked.connect(self._on_browse_shape)
        self.btn_pick_fcstd_object.clicked.connect(self._on_pick_fcstd_object)
        self.chk_cols_template.toggled.connect(self._apply_column_group_visibility)
        self.chk_cols_external.toggled.connect(self._apply_column_group_visibility)
        self.chk_cols_advanced.toggled.connect(self._apply_column_group_visibility)
        self.btn_add_common_structure.clicked.connect(self._add_common_structure)
        self.btn_clone_structure.clicked.connect(self._clone_selected_structure)
        self.btn_load_structure_preset.clicked.connect(self._load_structure_preset)
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_add_profile.clicked.connect(self._add_profile_row)
        self.btn_remove_profile.clicked.connect(self._remove_profile_row)
        self.btn_load_profile_preset.clicked.connect(self._load_profile_preset)
        self.btn_sort_profile.clicked.connect(self._sort_profile_rows)
        self.btn_duplicate_profile.clicked.connect(self._duplicate_profile_row)
        self.btn_add_profile_midpoint.clicked.connect(self._add_profile_midpoint)
        self.btn_clear_profile.clicked.connect(self._clear_profile_rows_for_selected)
        self.btn_sort.clicked.connect(self._sort_rows)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_close.clicked.connect(self.reject)
        self.table.cellPressed.connect(self._on_structure_row_pressed)
        self.table.itemSelectionChanged.connect(self._enforce_structure_row_selection)
        self.table.itemChanged.connect(self._on_table_item_changed)
        self.profile_table.itemChanged.connect(self._on_profile_item_changed)

        self._set_rows(3)
        self._set_profile_table_rows([])
        self._update_shape_status()
        self._refresh_detail_panel()
        self._apply_column_group_visibility()
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

    def _apply_default_column_visibility(self):
        try:
            for col in range(len(COL_HEADERS)):
                self.table.setColumnHidden(col, col not in BASIC_VISIBLE_COLS)
        except Exception:
            pass

    def _apply_column_group_visibility(self):
        try:
            visible = set(BASIC_VISIBLE_COLS)
            if self.chk_cols_template.isChecked():
                visible.update(TEMPLATE_COLS)
            if self.chk_cols_external.isChecked():
                visible.update(EXTERNAL_SHAPE_COLS)
            if self.chk_cols_advanced.isChecked():
                visible.update(ADVANCED_COLS)
            for col in range(len(COL_HEADERS)):
                self.table.setColumnHidden(col, col not in visible)
        except Exception:
            pass

    def _station_span_bounds(self):
        vals = []
        for s in list(self._station_values or []):
            try:
                vals.append(float(s))
            except Exception:
                pass
        if vals:
            return min(vals), max(vals)
        return 0.0, 100.0

    def _station_at_fraction(self, frac):
        s0, s1 = self._station_span_bounds()
        frac = max(0.0, min(1.0, float(frac)))
        return s0 + frac * (s1 - s0)

    def _current_structure_row(self):
        row = int(self._active_structure_row)
        if 0 <= row < self.table.rowCount():
            row_vals = [self._get_cell_text(row, c).strip() for c in range(len(COL_HEADERS))]
            if any(row_vals):
                return row
        return -1

    def _set_active_structure_row(self, row):
        try:
            row = int(row)
        except Exception:
            row = -1
        if row < 0 or row >= self.table.rowCount():
            self._active_structure_row = -1
            return
        self._active_structure_row = row
        self._select_structure_row(row)

    def _select_structure_row(self, row):
        try:
            self._enforcing_structure_selection = True
            self.table.blockSignals(True)
            self.table.clearSelection()
            self.table.setCurrentCell(int(row), 0)
            self.table.selectRow(int(row))
        except Exception:
            pass
        finally:
            try:
                self.table.blockSignals(False)
            except Exception:
                pass
            self._enforcing_structure_selection = False

    def _enforce_structure_row_selection(self):
        if self._loading or self._enforcing_structure_selection:
            return
        row = int(self._active_structure_row)
        if row < 0 or row >= self.table.rowCount():
            return
        try:
            selected_rows = list(self.table.selectionModel().selectedRows())
        except Exception:
            selected_rows = []
        if len(selected_rows) == 1:
            try:
                if int(selected_rows[0].row()) == row:
                    return
            except Exception:
                pass
        self._select_structure_row(row)

    def _activate_structure_row_from_widget(self, widget):
        if self._loading or widget is None:
            return
        try:
            pos = widget.mapTo(self.table.viewport(), QtCore.QPoint(1, 1))
            idx = self.table.indexAt(pos)
            row = int(idx.row())
        except Exception:
            row = -1
        if row < 0 or row >= self.table.rowCount():
            return
        if row != int(self._active_structure_row):
            self._set_active_structure_row(row)
            self._on_structure_selection_changed()

    def _selected_structure_record(self):
        row = self._current_structure_row()
        if row < 0:
            return None
        return {
            "Id": self._get_cell_text(row, 0).strip(),
            "Type": self._get_cell_text(row, 1).strip().lower(),
            "StartStation": self._get_cell_float(row, 2),
            "EndStation": self._get_cell_float(row, 3),
            "CenterStation": self._get_cell_float(row, 4),
            "Side": self._get_cell_text(row, 5).strip(),
            "Offset": self._get_cell_float(row, 6),
            "Width": self._get_cell_float(row, 7),
            "Height": self._get_cell_float(row, 8),
            "BottomElevation": self._get_cell_float(row, 9),
            "Cover": self._get_cell_float(row, 10),
            "WallThickness": self._get_cell_float(row, 15),
            "FootingWidth": self._get_cell_float(row, 16),
            "FootingThickness": self._get_cell_float(row, 17),
            "CapHeight": self._get_cell_float(row, 18),
            "CellCount": max(1.0, self._get_cell_float(row, 19) or 1.0),
        }

    @staticmethod
    def _structure_record(
        sid,
        typ,
        start,
        end,
        side,
        offset,
        width,
        height,
        geom="",
        tpl="",
        corridor="",
        behavior="",
        bottom=0.0,
        cover=0.0,
        notes="",
        wall=0.3,
        footing_w=0.0,
        footing_t=0.0,
        cap_h=0.0,
        cell_count=1.0,
        shape_path="",
    ):
        center = 0.5 * (float(start) + float(end))
        rec_geom = str(geom or "")
        if rec_geom == "external_shape":
            rec_type = typ if typ in ALLOWED_TYPES else "other"
        else:
            rec_type = typ
        return {
            "Id": sid,
            "Type": rec_type,
            "StartStation": float(start),
            "EndStation": float(end),
            "CenterStation": float(center),
            "Side": side,
            "Offset": float(offset),
            "Width": float(width),
            "Height": float(height),
            "BottomElevation": float(bottom),
            "Cover": float(cover),
            "RotationDeg": 0.0,
            "BehaviorMode": behavior,
            "GeometryMode": rec_geom or _recommended_geometry_mode(rec_type),
            "TemplateName": tpl or _recommended_template_name(rec_type),
            "WallThickness": float(wall),
            "FootingWidth": float(footing_w),
            "FootingThickness": float(footing_t),
            "CapHeight": float(cap_h),
            "CellCount": float(cell_count),
            "CorridorMode": corridor or _recommended_corridor_mode(rec_type),
            "CorridorMargin": 0.0,
            "Notes": notes,
            "ShapeSourcePath": shape_path,
            "ScaleFactor": 1.0,
            "PlacementMode": "",
            "UseSourceBaseAsBottom": "",
        }

    def _rows_for_common_structure(self, structure_type: str):
        typ = str(structure_type or "").strip().lower()
        mid = self._station_at_fraction(0.5)
        span = max(10.0, 0.08 * (self._station_span_bounds()[1] - self._station_span_bounds()[0]))
        start = mid - 0.5 * span
        end = mid + 0.5 * span
        if typ == "culvert":
            return self._structure_record(
                "CULV-NEW", "culvert", start, end, "center", 0.0, 6.0, 2.5,
                geom="template", tpl="box_culvert", corridor="notch", cover=1.0, wall=0.3, cell_count=2.0,
                notes="Quick-add culvert",
            )
        if typ == "crossing":
            return self._structure_record(
                "XING-NEW", "crossing", start, end, "center", 0.0, 4.0, 1.8,
                geom="template", tpl="utility_crossing", corridor="notch", cover=0.8, wall=0.2,
                notes="Quick-add crossing",
            )
        if typ == "retaining_wall":
            return self._structure_record(
                "RW-NEW", "retaining_wall", start, end, "right", 8.0, 0.6, 3.5,
                geom="template", tpl="retaining_wall", corridor="split_only", bottom=101.0,
                wall=0.35, footing_w=2.2, footing_t=0.5, cap_h=0.25, notes="Quick-add retaining wall",
            )
        if typ == "abutment_zone":
            return self._structure_record(
                "ABUT-NEW", "abutment_zone", start, end, "both", 0.0, 10.0, 4.0,
                geom="template", tpl="abutment_block", corridor="skip_zone", bottom=101.0,
                wall=0.45, footing_w=3.0, footing_t=0.7, cap_h=0.3, notes="Quick-add abutment",
            )
        if typ == "bridge_zone":
            return self._structure_record(
                "BRDG-NEW", "bridge_zone", start, end, "both", 0.0, 14.0, 4.0,
                geom="box", tpl="", corridor="skip_zone", bottom=101.0, notes="Quick-add bridge zone",
            )
        if typ == "external_shape":
            return self._structure_record(
                "EXT-NEW", "other", start, end, "center", 0.0, 6.0, 2.5,
                geom="external_shape", tpl="", corridor="", notes="Quick-add external shape placeholder",
            )
        return self._structure_record(
            "STR-NEW", "other", start, end, "center", 0.0, 5.0, 2.5,
            geom="box", tpl="", corridor="", notes="Quick-add generic structure",
        )

    def _make_structure_preset(self, name: str):
        preset = str(name or "").strip()
        rows = []
        profile_rows = []
        if preset == "Drainage Sample":
            rows = [
                self._structure_record(
                    "CULV-P01", "culvert",
                    self._station_at_fraction(0.20), self._station_at_fraction(0.28),
                    "center", 0.0, 6.0, 2.5, geom="template", tpl="box_culvert",
                    corridor="notch", cover=1.0, wall=0.3, cell_count=2.0, notes="Preset culvert",
                ),
                self._structure_record(
                    "XING-P01", "crossing",
                    self._station_at_fraction(0.56), self._station_at_fraction(0.62),
                    "center", 0.0, 4.0, 1.8, geom="template", tpl="utility_crossing",
                    corridor="notch", cover=0.8, wall=0.2, notes="Preset crossing",
                ),
            ]
        elif preset == "Wall Sample":
            rows = [
                self._structure_record(
                    "RW-P01", "retaining_wall",
                    self._station_at_fraction(0.30), self._station_at_fraction(0.44),
                    "right", 8.0, 0.6, 3.2, geom="template", tpl="retaining_wall",
                    corridor="split_only", bottom=101.0, wall=0.35, footing_w=2.2, footing_t=0.5, cap_h=0.25,
                    notes="Preset retaining wall",
                ),
                self._structure_record(
                    "ABUT-P01", "abutment_zone",
                    self._station_at_fraction(0.68), self._station_at_fraction(0.76),
                    "both", 0.0, 10.0, 4.2, geom="template", tpl="abutment_block",
                    corridor="skip_zone", bottom=101.0, wall=0.45, footing_w=3.2, footing_t=0.7, cap_h=0.3,
                    notes="Preset abutment",
                ),
            ]
        elif preset == "Variable Size Sample":
            rows = [
                self._structure_record(
                    "CULV-V01", "culvert",
                    self._station_at_fraction(0.18), self._station_at_fraction(0.36),
                    "center", 0.0, 5.0, 2.2, geom="template", tpl="box_culvert",
                    corridor="notch", cover=1.0, wall=0.3, cell_count=1.0, notes="Variable culvert",
                ),
                self._structure_record(
                    "RW-V01", "retaining_wall",
                    self._station_at_fraction(0.55), self._station_at_fraction(0.72),
                    "right", 7.5, 0.6, 3.0, geom="template", tpl="retaining_wall",
                    corridor="split_only", bottom=101.0, wall=0.35, footing_w=2.0, footing_t=0.5, cap_h=0.25,
                    notes="Variable retaining wall",
                ),
            ]
            culv_s0 = rows[0]["StartStation"]
            culv_s1 = rows[0]["EndStation"]
            rw_s0 = rows[1]["StartStation"]
            rw_s1 = rows[1]["EndStation"]
            profile_rows = [
                {"StructureId": "CULV-V01", "Station": culv_s0, "Offset": 0.0, "Width": 4.0, "Height": 2.0, "BottomElevation": 0.0, "Cover": 1.0, "WallThickness": 0.28, "FootingWidth": 0.0, "FootingThickness": 0.0, "CapHeight": 0.0, "CellCount": 1},
                {"StructureId": "CULV-V01", "Station": 0.5 * (culv_s0 + culv_s1), "Offset": 0.0, "Width": 6.0, "Height": 2.5, "BottomElevation": 0.0, "Cover": 1.0, "WallThickness": 0.30, "FootingWidth": 0.0, "FootingThickness": 0.0, "CapHeight": 0.0, "CellCount": 2},
                {"StructureId": "CULV-V01", "Station": culv_s1, "Offset": 0.0, "Width": 4.5, "Height": 2.1, "BottomElevation": 0.0, "Cover": 1.0, "WallThickness": 0.28, "FootingWidth": 0.0, "FootingThickness": 0.0, "CapHeight": 0.0, "CellCount": 1},
                {"StructureId": "RW-V01", "Station": rw_s0, "Offset": 7.5, "Width": 0.6, "Height": 2.8, "BottomElevation": 101.2, "Cover": 0.0, "WallThickness": 0.34, "FootingWidth": 2.0, "FootingThickness": 0.5, "CapHeight": 0.2, "CellCount": 1},
                {"StructureId": "RW-V01", "Station": 0.5 * (rw_s0 + rw_s1), "Offset": 8.0, "Width": 0.65, "Height": 4.6, "BottomElevation": 101.0, "Cover": 0.0, "WallThickness": 0.38, "FootingWidth": 2.4, "FootingThickness": 0.6, "CapHeight": 0.3, "CellCount": 1},
                {"StructureId": "RW-V01", "Station": rw_s1, "Offset": 8.3, "Width": 0.6, "Height": 3.6, "BottomElevation": 100.9, "Cover": 0.0, "WallThickness": 0.35, "FootingWidth": 2.1, "FootingThickness": 0.55, "CapHeight": 0.25, "CellCount": 1},
            ]
        else:
            rows = [
                self._structure_record(
                    "CULV-M01", "culvert",
                    self._station_at_fraction(0.16), self._station_at_fraction(0.24),
                    "center", 0.0, 6.0, 2.5, geom="template", tpl="box_culvert",
                    corridor="notch", cover=1.0, wall=0.3, cell_count=2.0, notes="Mixed culvert",
                ),
                self._structure_record(
                    "RW-M01", "retaining_wall",
                    self._station_at_fraction(0.38), self._station_at_fraction(0.50),
                    "right", 8.0, 0.6, 3.5, geom="template", tpl="retaining_wall",
                    corridor="split_only", bottom=101.0, wall=0.35, footing_w=2.2, footing_t=0.5, cap_h=0.25, notes="Mixed retaining wall",
                ),
                self._structure_record(
                    "ABUT-M01", "abutment_zone",
                    self._station_at_fraction(0.62), self._station_at_fraction(0.70),
                    "both", 0.0, 10.0, 4.0, geom="template", tpl="abutment_block",
                    corridor="skip_zone", bottom=101.0, wall=0.45, footing_w=3.0, footing_t=0.7, cap_h=0.3, notes="Mixed abutment",
                ),
                self._structure_record(
                    "BRDG-M01", "bridge_zone",
                    self._station_at_fraction(0.70), self._station_at_fraction(0.82),
                    "both", 0.0, 14.0, 4.0, geom="box", tpl="", corridor="skip_zone", bottom=101.0, notes="Mixed bridge zone",
                ),
                self._structure_record(
                    "EXT-M01", "other",
                    self._station_at_fraction(0.84), self._station_at_fraction(0.90),
                    "center", 0.0, 6.0, 2.5, geom="external_shape", tpl="", corridor="", notes="Mixed external shape placeholder",
                ),
            ]
        covered_ids = {
            str(row.get("StructureId", "") or "").strip()
            for row in list(profile_rows or [])
            if str(row.get("StructureId", "") or "").strip()
        }
        for rec in list(rows or []):
            sid = str(rec.get("Id", "") or "").strip()
            if not sid or sid in covered_ids:
                continue
            preset_name = _default_profile_preset_for_structure_type(rec.get("Type", ""))
            auto_rows = list(self._make_profile_preset_rows(preset_name, rec) or [])
            if not auto_rows:
                continue
            profile_rows.extend(auto_rows)
            covered_ids.add(sid)
        return rows, profile_rows

    def _make_profile_preset_rows(self, preset_name: str, rec: dict):
        sid = str(rec.get("Id", "") or "").strip()
        start = float(rec.get("StartStation", 0.0) or 0.0)
        end = float(rec.get("EndStation", 0.0) or 0.0)
        if end <= start + 1e-9:
            return []
        width = float(rec.get("Width", 0.0) or 0.0)
        height = float(rec.get("Height", 0.0) or 0.0)
        offset = float(rec.get("Offset", 0.0) or 0.0)
        bottom = float(rec.get("BottomElevation", 0.0) or 0.0)
        cover = float(rec.get("Cover", 0.0) or 0.0)
        wall = float(rec.get("WallThickness", 0.0) or 0.0)
        footing_w = float(rec.get("FootingWidth", 0.0) or 0.0)
        footing_t = float(rec.get("FootingThickness", 0.0) or 0.0)
        cap_h = float(rec.get("CapHeight", 0.0) or 0.0)
        cells = int(round(float(rec.get("CellCount", 1.0) or 1.0)))
        base = {
            "StructureId": sid,
            "Offset": offset,
            "Width": width,
            "Height": height,
            "BottomElevation": bottom,
            "Cover": cover,
            "WallThickness": wall,
            "FootingWidth": footing_w,
            "FootingThickness": footing_t,
            "CapHeight": cap_h,
            "CellCount": max(1, cells),
        }

        def at(frac, **overrides):
            out = dict(base)
            out["Station"] = start + float(frac) * (end - start)
            out.update(overrides)
            return out

        name = str(preset_name or "").strip()
        if name == "2-Point Linear":
            return [at(0.0), at(1.0)]
        if name == "3-Point Mid Bulge":
            return [
                at(0.0),
                at(0.5, Width=1.2 * width, Height=1.2 * height),
                at(1.0),
            ]
        if name == "3-Point Mid Narrow":
            return [
                at(0.0),
                at(0.5, Width=0.8 * width, Height=0.9 * height),
                at(1.0),
            ]
        if name == "Culvert 1-2-1 Cells":
            return [
                at(0.0, CellCount=1, Width=max(width * 0.85, width - 1.0), Height=max(height * 0.95, height - 0.2)),
                at(0.5, CellCount=max(2, cells, 2), Width=max(width, width * 1.15), Height=max(height, height * 1.10)),
                at(1.0, CellCount=1, Width=max(width * 0.85, width - 1.0), Height=max(height * 0.95, height - 0.2)),
            ]
        if name == "Crossing Shallow Mid":
            return [
                at(0.0),
                at(0.5, Height=max(0.5, 0.7 * height), Cover=max(0.0, cover + 0.2)),
                at(1.0),
            ]
        if name == "Wall Step-Up":
            return [
                at(0.0),
                at(0.5, Height=1.25 * height, Offset=offset + 0.25, FootingWidth=max(footing_w, footing_w + 0.2)),
                at(1.0, Height=1.5 * height, Offset=offset + 0.5, FootingWidth=max(footing_w, footing_w + 0.4), CapHeight=max(cap_h, cap_h + 0.05)),
            ]
        if name == "Wall Step-Down":
            return [
                at(0.0, Height=1.5 * height, Offset=offset + 0.5, FootingWidth=max(footing_w, footing_w + 0.4), CapHeight=max(cap_h, cap_h + 0.05)),
                at(0.5, Height=1.2 * height, Offset=offset + 0.25, FootingWidth=max(footing_w, footing_w + 0.2)),
                at(1.0),
            ]
        return [at(0.0), at(1.0)]

    def _set_detail_widget_value(self, col, value):
        w = self._detail_widgets.get(int(col))
        if w is None:
            return
        if isinstance(w, QtWidgets.QComboBox):
            txt = str(value or "")
            idx = w.findText(txt)
            if idx < 0 and txt != "":
                w.addItem(txt)
                idx = w.findText(txt)
            w.setCurrentIndex(max(0, idx))
        else:
            w.setText(str(value or ""))

    def _refresh_detail_panel(self):
        row = self._current_structure_row()
        if row < 0:
            self.gb_details.setTitle("Selected Structure Details")
            self.gb_details.setToolTip("")
            for col in list(self._detail_widgets.keys()):
                self._set_detail_widget_value(col, "")
                try:
                    self._detail_widgets[col].setEnabled(False)
                except Exception:
                    pass
            return

        corr = self._get_cell_text(row, 20).strip() or "-"
        sid = self._get_cell_text(row, 0).strip() or f"row {row + 1}"
        pcount = len(self._filtered_profile_rows(sid))
        sev, msgs = self._row_validation_messages(row)
        status_txt = "OK"
        if sev == 2:
            status_txt = "ERROR"
        elif sev == 1:
            status_txt = "WARNING"
        first_msg = msgs[0] if msgs else "Validation looks good."
        self.gb_details.setTitle(
            "Selected Structure Details - {sid} | {status_txt} | {corr} | profiles={pcount}".format(
                sid=sid,
                status_txt=status_txt,
                corr=corr,
                pcount=pcount,
            )
        )
        self.gb_details.setToolTip(first_msg)
        for _label, col, _kind in DETAIL_FIELD_SPECS:
            self._set_detail_widget_value(col, self._get_cell_text(row, col))
        self._refresh_detail_widget_state(row)

    def _refresh_detail_widget_state(self, row):
        typ = self._get_cell_text(int(row), 1).strip()
        geom = self._get_cell_text(int(row), 13).strip()
        use_bottom, use_cover, _note = _vertical_input_policy(typ)
        highlight_cols = set()
        if str(typ).strip().lower() in ("culvert", "crossing"):
            highlight_cols.update({10, 15, 19, 20})
        elif str(typ).strip().lower() in ("retaining_wall", "abutment_zone", "bridge_zone"):
            highlight_cols.update({9, 16, 17, 18, 20})
        if geom == "template":
            highlight_cols.update({14, 15, 16, 17, 18, 19})
        if geom == "external_shape":
            highlight_cols.update({23, 24, 25, 26})
        for col, enabled in (
            (9, use_bottom),
            (10, use_cover),
            (14, geom == "template"),
            (15, geom == "template"),
            (16, geom == "template"),
            (17, geom == "template"),
            (18, geom == "template"),
            (19, geom == "template"),
            (23, geom == "external_shape"),
            (24, geom == "external_shape"),
            (25, geom == "external_shape"),
            (26, geom == "external_shape"),
        ):
            w = self._detail_widgets.get(int(col))
            if w is not None:
                try:
                    w.setEnabled(bool(enabled))
                    if enabled and int(col) in highlight_cols:
                        w.setStyleSheet("background-color: rgb(48, 58, 72); color: rgb(235, 235, 235);")
                    elif enabled:
                        w.setStyleSheet("")
                    else:
                        w.setStyleSheet("background-color: rgb(42, 42, 42); color: rgb(145, 145, 145);")
                except Exception:
                    pass
        for col, widget in list(self._detail_widgets.items()):
            tip = ""
            if int(col) == 9:
                tip = "BottomElevation is typically used for retaining walls, abutments, and bridge zones."
            elif int(col) == 10:
                tip = "Cover is typically used for buried culverts and crossings."
            elif int(col) in (14, 15, 16, 17, 18, 19):
                tip = "Template parameters are used only when GeometryMode=template."
            elif int(col) in (23, 24, 25, 26):
                tip = "External shape fields are used only when GeometryMode=external_shape."
            elif int(col) == 20:
                tip = f"Recommended corridor mode: {_recommended_corridor_mode(typ) or 'none'}"
            try:
                widget.setToolTip(tip)
            except Exception:
                pass

    def _on_detail_widget_changed(self, col):
        if self._loading:
            return
        row = self._current_structure_row()
        if row < 0:
            return
        w = self._detail_widgets.get(int(col))
        if w is None:
            return
        try:
            if isinstance(w, QtWidgets.QComboBox):
                val = str(w.currentText() or "")
            else:
                val = str(w.text() or "")
            self._set_cell_text(row, int(col), val)
            if int(col) == 1:
                self._on_type_changed(row)
            self._apply_vertical_input_policy(row)
            self._apply_shape_source_visual(row)
            self._update_shape_status()
            self._refresh_detail_panel()
        except Exception:
            pass

    def _set_profile_rows(self, rows):
        self._profile_rows = list(rows or [])
        count = len(self._profile_rows)
        by_structure = {}
        for row in self._profile_rows:
            sid = str(row.get("StructureId", "") or "").strip()
            if sid:
                by_structure[sid] = by_structure.get(sid, 0) + 1
        if by_structure:
            summary = ", ".join(f"{sid}={count}" for sid, count in list(sorted(by_structure.items()))[:5])
            if len(by_structure) > 5:
                summary += ", ..."
            self.lbl_profile_status.setText(f"Station-profile points: {count} ({summary})")
        else:
            self.lbl_profile_status.setText(f"Station-profile points: {count}")
        self._refresh_validation_visuals()

    def _selected_structure_id(self):
        row = self._current_structure_row()
        if row < 0:
            return ""
        return str(self._get_cell_text(row, 0) or "").strip()

    def _filtered_profile_rows(self, structure_id):
        sid = str(structure_id or "").strip()
        if not sid:
            return []
        return [dict(row) for row in self._profile_rows if str(row.get("StructureId", "") or "").strip() == sid]

    def _row_validation_messages(self, row):
        rid = self._get_cell_text(row, 0).strip() or f"row {row + 1}"
        typ = self._get_cell_text(row, 1).strip().lower()
        geom = self._get_cell_text(row, 13).strip()
        cor_mode = self._get_cell_text(row, 20).strip().lower()
        start = self._get_cell_float(row, 2)
        end = self._get_cell_float(row, 3)
        center = self._get_cell_float(row, 4)
        corridor_margin = self._get_cell_float(row, 21)
        msgs = []
        severity = 0

        if not typ:
            msgs.append(f"{rid}: Type is empty")
            severity = max(severity, 2)
        elif typ not in [str(x).lower() for x in ALLOWED_TYPES]:
            msgs.append(f"{rid}: Type is not allowed")
            severity = max(severity, 2)

        if end < start:
            msgs.append(f"{rid}: EndStation is less than StartStation")
            severity = max(severity, 2)

        rec_mode = _recommended_corridor_mode(typ)
        if rec_mode and cor_mode and cor_mode != rec_mode:
            msgs.append(f"{rid}: CorridorMode differs from recommended '{rec_mode}'")
            severity = max(severity, 1)

        if geom == "template" and not self._get_cell_text(row, 14).strip():
            msgs.append(f"{rid}: template geometry requires TemplateName")
            severity = max(severity, 2)

        if geom not in ("", "box", "template", "external_shape"):
            msgs.append(f"{rid}: GeometryMode is not allowed")
            severity = max(severity, 2)

        use_bottom, use_cover, _note = _vertical_input_policy(typ)
        if not use_bottom and abs(self._get_cell_float(row, 9)) > 1e-9:
            msgs.append(f"{rid}: BottomElevation is usually not used for this type")
            severity = max(severity, 1)
        if not use_cover and abs(self._get_cell_float(row, 10)) > 1e-9:
            msgs.append(f"{rid}: Cover is usually not used for this type")
            severity = max(severity, 1)

        if geom == "external_shape":
            src = self._get_cell_text(row, 23).strip()
            src_file, src_obj = _split_shape_source_path(src)
            if not src:
                msgs.append(f"{rid}: external_shape requires ShapeSourcePath")
                severity = max(severity, 2)
            elif str(src_file).lower().endswith(".fcstd") and not src_obj:
                msgs.append(f"{rid}: FCStd path needs #ObjectName")
                severity = max(severity, 2)
            elif src_file and (not os.path.isfile(src_file)):
                msgs.append(f"{rid}: external shape file not found")
                severity = max(severity, 1)
            msgs.append(f"{rid}: external_shape may drive an indirect bbox-based earthwork proxy; direct solid consumption is still unsupported")
            severity = max(severity, 1)
            if cor_mode in ("notch", "boolean_cut"):
                msgs.append(f"{rid}: {cor_mode} does not yet consume the imported external solid directly; current runtime can only use bbox proxy or Type/Width/Height")
                severity = max(severity, 1)

        has_start_end = abs(start) > 1e-9 or abs(end) > 1e-9 or abs(end - start) > 1e-9
        has_center = abs(center) > 1e-9
        if cor_mode in ("skip_zone", "notch", "boolean_cut"):
            if not has_start_end and not has_center:
                msgs.append(f"{rid}: corridor mode '{cor_mode}' has no usable station span")
                severity = max(severity, 1)
            elif abs(end - start) <= 1e-9 and corridor_margin <= 1e-9:
                msgs.append(f"{rid}: corridor mode '{cor_mode}' is point-like; add CorridorMargin or explicit Start/End span")
                severity = max(severity, 1)

        prow = self._filtered_profile_rows(rid)
        if len(prow) == 1:
            msgs.append(f"{rid}: structure profile has only 1 point")
            severity = max(severity, 1)
        elif len(prow) >= 2:
            prev = None
            for rec in prow:
                ss = float(rec.get("Station", 0.0) or 0.0)
                if prev is not None:
                    if ss < prev - 1e-9:
                        msgs.append(f"{rid}: structure profile stations are not sorted ascending")
                        severity = max(severity, 2)
                        break
                    if abs(ss - prev) <= 1e-9:
                        msgs.append(f"{rid}: duplicate profile station {ss:.3f}")
                        severity = max(severity, 2)
                        break
                prev = ss
        return severity, msgs

    def _refresh_validation_visuals(self):
        brushes = self._item_brushes()
        ok_count, warn_count, err_count, lines = self._validation_snapshot()
        row_states = []
        for row in range(self.table.rowCount()):
            row_vals = [self._get_cell_text(row, c).strip() for c in range(len(COL_HEADERS))]
            if not any(row_vals):
                continue
            sev, msgs = self._row_validation_messages(row)
            row_states.append((row, sev, msgs))
        for row, sev, msgs in row_states:
            tip = "\n".join(msgs) if msgs else "Validation: OK"
            brush_bg = brushes["ok_base"]
            if sev == 2:
                brush_bg = brushes["err_base"]
            elif sev == 1:
                brush_bg = brushes["warn_base"]
            for col in BASIC_VISIBLE_COLS:
                item = self.table.item(row, col)
                if item is None:
                    item = QtWidgets.QTableWidgetItem("")
                    self.table.setItem(row, col, item)
                item.setForeground(brushes["text"])
                item.setBackground(brush_bg)
                item.setToolTip(tip)
            if row == self._current_structure_row():
                try:
                    self.gb_details.setToolTip(tip)
                except Exception:
                    pass
        if not lines and (warn_count + err_count) == 0:
            self.lbl_validation_summary.setText(f"Validation summary: OK | ok={ok_count}")
            self.lbl_validation_summary.setStyleSheet("color: #cfd8dc;")
        else:
            body = " | ".join(lines[:4])
            self.lbl_validation_summary.setText(
                f"Validation summary: ok={ok_count}, errors={err_count}, warnings={warn_count} | {body}"
            )
            if err_count:
                self.lbl_validation_summary.setStyleSheet("color: #ffb3b3;")
            else:
                self.lbl_validation_summary.setStyleSheet("color: #ffd27f;")

    def _validation_snapshot(self):
        ok_count = 0
        warn_count = 0
        err_count = 0
        lines = []
        for row in range(self.table.rowCount()):
            row_vals = [self._get_cell_text(row, c).strip() for c in range(len(COL_HEADERS))]
            if not any(row_vals):
                continue
            sev, msgs = self._row_validation_messages(row)
            if sev == 2:
                err_count += 1
            elif sev == 1:
                warn_count += 1
            else:
                ok_count += 1
            if msgs:
                lines.extend(msgs[:2])
        return ok_count, warn_count, err_count, lines

    def _set_profile_table_rows(self, rows, structure_id=""):
        sid = str(structure_id or "").strip()
        self._loading = True
        try:
            self.profile_table.setRowCount(max(0, len(rows)))
            for r in range(len(rows)):
                for c in range(len(PROFILE_COL_HEADERS)):
                    if self.profile_table.item(r, c) is None:
                        self.profile_table.setItem(r, c, QtWidgets.QTableWidgetItem(""))
            for i, rec in enumerate(rows):
                vals = [
                    sid or str(rec.get("StructureId", "") or ""),
                    f"{float(rec.get('Station', 0.0) or 0.0):.3f}",
                    f"{float(rec.get('Offset', 0.0) or 0.0):.3f}",
                    f"{float(rec.get('Width', 0.0) or 0.0):.3f}",
                    f"{float(rec.get('Height', 0.0) or 0.0):.3f}",
                    f"{float(rec.get('BottomElevation', 0.0) or 0.0):.3f}",
                    f"{float(rec.get('Cover', 0.0) or 0.0):.3f}",
                    f"{float(rec.get('WallThickness', 0.0) or 0.0):.3f}",
                    f"{float(rec.get('FootingWidth', 0.0) or 0.0):.3f}",
                    f"{float(rec.get('FootingThickness', 0.0) or 0.0):.3f}",
                    f"{float(rec.get('CapHeight', 0.0) or 0.0):.3f}",
                    f"{int(round(float(rec.get('CellCount', 0.0) or 0.0))):d}",
                ]
                for c, val in enumerate(vals):
                    it = self.profile_table.item(i, c)
                    if it is None:
                        it = QtWidgets.QTableWidgetItem("")
                        self.profile_table.setItem(i, c, it)
                    it.setText(val)
                    if c == 0:
                        it.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self._active_profile_structure_id = sid
            if rows:
                stas = [float(rec.get("Station", 0.0) or 0.0) for rec in rows]
                self.lbl_profile_table.setText(
                    f"Station profiles for selected structure: {sid if sid else 'no selection'} | "
                    f"points={len(rows)} | range={min(stas):.3f} ~ {max(stas):.3f}"
                )
            else:
                self.lbl_profile_table.setText(
                    f"Station profiles for selected structure: {sid if sid else 'no selection'} | points=0"
                )
        finally:
            self._loading = False

    def _sync_profile_table_to_store(self):
        sid = str(self._active_profile_structure_id or "").strip()
        if not sid:
            return
        kept = [dict(row) for row in self._profile_rows if str(row.get("StructureId", "") or "").strip() != sid]
        for r in range(self.profile_table.rowCount()):
            station_txt = str((self.profile_table.item(r, 1).text() if self.profile_table.item(r, 1) else "") or "").strip()
            if not station_txt and not any(
                str((self.profile_table.item(r, c).text() if self.profile_table.item(r, c) else "") or "").strip()
                for c in range(2, len(PROFILE_COL_HEADERS))
            ):
                continue
            kept.append(
                {
                    "StructureId": sid,
                    "Station": self._parse_float(station_txt),
                    "Offset": self._parse_float(self.profile_table.item(r, 2).text() if self.profile_table.item(r, 2) else ""),
                    "Width": self._parse_float(self.profile_table.item(r, 3).text() if self.profile_table.item(r, 3) else ""),
                    "Height": self._parse_float(self.profile_table.item(r, 4).text() if self.profile_table.item(r, 4) else ""),
                    "BottomElevation": self._parse_float(self.profile_table.item(r, 5).text() if self.profile_table.item(r, 5) else ""),
                    "Cover": self._parse_float(self.profile_table.item(r, 6).text() if self.profile_table.item(r, 6) else ""),
                    "WallThickness": self._parse_float(self.profile_table.item(r, 7).text() if self.profile_table.item(r, 7) else ""),
                    "FootingWidth": self._parse_float(self.profile_table.item(r, 8).text() if self.profile_table.item(r, 8) else ""),
                    "FootingThickness": self._parse_float(self.profile_table.item(r, 9).text() if self.profile_table.item(r, 9) else ""),
                    "CapHeight": self._parse_float(self.profile_table.item(r, 10).text() if self.profile_table.item(r, 10) else ""),
                    "CellCount": int(round(self._parse_float(self.profile_table.item(r, 11).text() if self.profile_table.item(r, 11) else ""))),
                }
            )
        self._set_profile_rows(sorted(kept, key=lambda row: (str(row.get("StructureId", "") or ""), float(row.get("Station", 0.0) or 0.0))))

    def _refresh_profile_table(self):
        sid = self._selected_structure_id()
        self._set_profile_table_rows(self._filtered_profile_rows(sid), structure_id=sid)
        self._refresh_detail_panel()
        self._refresh_validation_visuals()

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
            if self._current_target() is None:
                self._set_profile_rows([])
        finally:
            self._loading = False
        self._on_target_changed()
        self._refresh_detail_panel()
        self._refresh_validation_visuals()

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
                cmb = _RowAwareComboBox(on_interact=self._activate_structure_row_from_widget)
                try:
                    cmb.setFocusPolicy(QtCore.Qt.NoFocus)
                    cmb.setMouseTracking(False)
                    cmb.setAttribute(QtCore.Qt.WA_Hover, False)
                    cmb.view().setMouseTracking(False)
                except Exception:
                    pass
                cmb.addItems(list(items))
                self.table.setCellWidget(row, col, cmb)
                if col == 1:
                    cmb.currentTextChanged.connect(lambda _txt, rr=row: self._on_type_changed(rr))
        for col in STATION_COMBO_COLUMNS:
            cmb = self.table.cellWidget(row, col)
            station_items = self._station_combo_items()
            if cmb is None:
                cmb = _RowAwareComboBox(on_interact=self._activate_structure_row_from_widget)
                try:
                    cmb.setFocusPolicy(QtCore.Qt.NoFocus)
                    cmb.setMouseTracking(False)
                    cmb.setAttribute(QtCore.Qt.WA_Hover, False)
                    cmb.view().setMouseTracking(False)
                except Exception:
                    pass
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
        brushes = self._item_brushes()
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
                it.setForeground(brushes["text"])
                it.setBackground(brushes["base"])
            else:
                it.setForeground(brushes["disabled_text"])
                it.setBackground(brushes["disabled_base"])
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
        brushes = self._item_brushes()
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
                it.setForeground(brushes["text"])
                it.setBackground(brushes["base"])
                return
            if not src:
                it.setToolTip("ShapeSourcePath is required for GeometryMode=external_shape.")
                it.setForeground(brushes["text"])
                it.setBackground(brushes["err_base"])
                return
            if str(src_file).lower().endswith(".fcstd") and not src_obj:
                it.setToolTip("FCStd external shape requires 'path.FCStd#ObjectName'.")
                it.setForeground(brushes["text"])
                it.setBackground(brushes["err_base"])
                return
            if os.path.isfile(src_file):
                it.setToolTip(f"External shape file found:\n{src}")
                it.setForeground(brushes["text"])
                it.setBackground(brushes["good_base"])
            else:
                it.setToolTip(f"External shape file not found:\n{src}")
                it.setForeground(brushes["text"])
                it.setBackground(brushes["err_base"])
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
            self._refresh_detail_panel()
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
                self._set_profile_rows([])
                self._set_profile_table_rows([])
                self._active_structure_row = -1
                self.lbl_status.setText("New StructureSet will be created.")
            finally:
                self._loading = False
            self._refresh_detail_panel()
            return

        ensure_structure_set_properties(obj)
        recs = StructureSet.records(obj)
        profile_rows = StructureSet.raw_profile_points(obj)
        self._populate_structure_table(recs)
        self._set_profile_rows(profile_rows)
        self._refresh_profile_table()
        self.lbl_status.setText(str(getattr(obj, "Status", "Loaded")))
        self._update_shape_status()
        self._refresh_detail_panel()

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

    def _populate_structure_table(self, rows):
        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(max(3, len(rows)))
            for i, rec in enumerate(rows):
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
                self._apply_shape_source_visual(i)
        finally:
            self._loading = False
        if rows:
            try:
                self._set_active_structure_row(0)
            except Exception:
                pass
        else:
            self._active_structure_row = -1
        self._refresh_detail_panel()
        self._refresh_validation_visuals()

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
        self._set_active_structure_row(self.table.rowCount() - 1)
        self._refresh_detail_panel()
        self._refresh_validation_visuals()

    def _remove_row(self):
        r = self._current_structure_row()
        if r < 0:
            r = self.table.rowCount() - 1
        if r >= 0:
            self.table.removeRow(r)
        if self.table.rowCount() <= 0:
            self._active_structure_row = -1
        else:
            self._set_active_structure_row(min(r, self.table.rowCount() - 1))
        self._update_shape_status()
        self._refresh_detail_panel()
        self._refresh_validation_visuals()

    def _add_profile_row(self):
        sid = self._selected_structure_id()
        if not sid:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Select a structure row first.")
            return
        self._sync_profile_table_to_store()
        rows = self._filtered_profile_rows(sid)
        rec = self._selected_structure_record() or {}
        if rows:
            try:
                station_val = float(rows[-1].get("Station", 0.0) or 0.0)
            except Exception:
                station_val = 0.0
        else:
            station_val = float(rec.get("CenterStation", 0.0) or 0.0)
            if abs(station_val) <= 1e-9:
                station_val = float(rec.get("StartStation", 0.0) or 0.0)
        new_row = {
            "StructureId": sid,
            "Station": float(station_val),
            "Offset": float(rec.get("Offset", 0.0) or 0.0),
            "Width": float(rec.get("Width", 0.0) or 0.0),
            "Height": float(rec.get("Height", 0.0) or 0.0),
            "BottomElevation": float(rec.get("BottomElevation", 0.0) or 0.0),
            "Cover": float(rec.get("Cover", 0.0) or 0.0),
            "WallThickness": float(rec.get("WallThickness", 0.0) or 0.0),
            "FootingWidth": float(rec.get("FootingWidth", 0.0) or 0.0),
            "FootingThickness": float(rec.get("FootingThickness", 0.0) or 0.0),
            "CapHeight": float(rec.get("CapHeight", 0.0) or 0.0),
            "CellCount": int(round(float(rec.get("CellCount", 1.0) or 1.0))),
        }
        kept = [dict(row) for row in self._profile_rows if str(row.get("StructureId", "") or "").strip() != sid]
        rows.append(new_row)
        kept.extend(rows)
        self._set_profile_rows(sorted(kept, key=lambda row: (str(row.get("StructureId", "") or ""), float(row.get("Station", 0.0) or 0.0))))
        self._refresh_profile_table()
        try:
            self.profile_table.selectRow(max(0, self.profile_table.rowCount() - 1))
        except Exception:
            pass

    def _remove_profile_row(self):
        r = self.profile_table.currentRow()
        if r < 0:
            r = self.profile_table.rowCount() - 1
        if r >= 0:
            self.profile_table.removeRow(r)
            self._sync_profile_table_to_store()
            self._refresh_profile_table()

    def _sort_profile_rows(self):
        sid = self._selected_structure_id()
        if not sid:
            return
        self._sync_profile_table_to_store()
        self._refresh_profile_table()

    def _duplicate_profile_row(self):
        sid = self._selected_structure_id()
        if not sid:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Select a structure row first.")
            return
        r = self.profile_table.currentRow()
        if r < 0:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Select a profile row to duplicate.")
            return
        vals = []
        for c in range(len(PROFILE_COL_HEADERS)):
            it = self.profile_table.item(r, c)
            vals.append(str((it.text() if it else "") or ""))
        self._loading = True
        try:
            ins = r + 1
            self.profile_table.insertRow(ins)
            for c, val in enumerate(vals):
                it = QtWidgets.QTableWidgetItem(val)
                self.profile_table.setItem(ins, c, it)
            self.profile_table.item(ins, 0).setText(sid)
            self.profile_table.item(ins, 0).setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.profile_table.selectRow(ins)
        finally:
            self._loading = False
        self._sync_profile_table_to_store()
        self._refresh_profile_table()

    def _add_profile_midpoint(self):
        sid = self._selected_structure_id()
        if not sid:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Select a structure row first.")
            return
        self._sync_profile_table_to_store()
        rows = self._filtered_profile_rows(sid)
        if len(rows) < 2:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "At least two profile points are needed to add a midpoint.")
            return
        r = self.profile_table.currentRow()
        if r < 0 or r >= self.profile_table.rowCount() - 1:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Select a profile row that has a next row to create a midpoint.")
            return
        a = rows[r]
        b = rows[r + 1]
        mid = {
            "StructureId": sid,
            "Station": 0.5 * (float(a.get("Station", 0.0) or 0.0) + float(b.get("Station", 0.0) or 0.0)),
            "Offset": 0.5 * (float(a.get("Offset", 0.0) or 0.0) + float(b.get("Offset", 0.0) or 0.0)),
            "Width": 0.5 * (float(a.get("Width", 0.0) or 0.0) + float(b.get("Width", 0.0) or 0.0)),
            "Height": 0.5 * (float(a.get("Height", 0.0) or 0.0) + float(b.get("Height", 0.0) or 0.0)),
            "BottomElevation": 0.5 * (float(a.get("BottomElevation", 0.0) or 0.0) + float(b.get("BottomElevation", 0.0) or 0.0)),
            "Cover": 0.5 * (float(a.get("Cover", 0.0) or 0.0) + float(b.get("Cover", 0.0) or 0.0)),
            "WallThickness": 0.5 * (float(a.get("WallThickness", 0.0) or 0.0) + float(b.get("WallThickness", 0.0) or 0.0)),
            "FootingWidth": 0.5 * (float(a.get("FootingWidth", 0.0) or 0.0) + float(b.get("FootingWidth", 0.0) or 0.0)),
            "FootingThickness": 0.5 * (float(a.get("FootingThickness", 0.0) or 0.0) + float(b.get("FootingThickness", 0.0) or 0.0)),
            "CapHeight": 0.5 * (float(a.get("CapHeight", 0.0) or 0.0) + float(b.get("CapHeight", 0.0) or 0.0)),
            "CellCount": int(round(0.5 * (float(a.get("CellCount", 0.0) or 0.0) + float(b.get("CellCount", 0.0) or 0.0)))),
        }
        kept = [dict(row) for row in self._profile_rows if str(row.get("StructureId", "") or "").strip() != sid]
        rows.insert(r + 1, mid)
        kept.extend(rows)
        self._set_profile_rows(sorted(kept, key=lambda row: (str(row.get("StructureId", "") or ""), float(row.get("Station", 0.0) or 0.0))))
        self._refresh_profile_table()
        try:
            self.profile_table.selectRow(r + 1)
        except Exception:
            pass

    def _clear_profile_rows_for_selected(self):
        sid = self._selected_structure_id()
        if not sid:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Select a structure row first.")
            return
        kept = [dict(row) for row in self._profile_rows if str(row.get("StructureId", "") or "").strip() != sid]
        self._set_profile_rows(kept)
        self._refresh_profile_table()

    def _add_common_structure(self):
        rec = self._rows_for_common_structure(self.cmb_common_structure.currentText())
        rows = self._read_rows()
        rows.append(rec)
        self._populate_structure_table(rows)
        self._set_active_structure_row(max(0, len(rows) - 1))
        self.lbl_status.setText(f"Added common structure: {rec.get('Type', '')}")
        self._refresh_detail_panel()
        self._refresh_validation_visuals()

    def _clone_selected_structure(self):
        row = self._current_structure_row()
        if row < 0:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Select a structure row to clone.")
            return
        rows = self._read_rows()
        if row >= len(rows):
            return
        rec = dict(rows[row])
        sid = str(rec.get("Id", "") or "").strip() or f"row{row + 1}"
        rec["Id"] = f"{sid}-COPY"
        start = float(rec.get("StartStation", 0.0) or 0.0)
        end = float(rec.get("EndStation", 0.0) or 0.0)
        shift = max(5.0, 0.05 * max(1.0, self._station_span_bounds()[1] - self._station_span_bounds()[0]))
        rec["StartStation"] = start + shift
        rec["EndStation"] = end + shift
        rec["CenterStation"] = 0.5 * (rec["StartStation"] + rec["EndStation"])
        rows.append(rec)
        old_sid = sid
        new_sid = str(rec["Id"])
        extra_profiles = []
        for prow in self._filtered_profile_rows(old_sid):
            p = dict(prow)
            p["StructureId"] = new_sid
            p["Station"] = float(p.get("Station", 0.0) or 0.0) + shift
            extra_profiles.append(p)
        self._populate_structure_table(rows)
        self._set_profile_rows(list(self._profile_rows) + extra_profiles)
        self._set_active_structure_row(max(0, len(rows) - 1))
        self._refresh_profile_table()
        self.lbl_status.setText(f"Cloned structure: {new_sid}")

    def _load_structure_preset(self):
        preset_name = str(self.cmb_structure_preset.currentText() or "").strip()
        rows, profile_rows = self._make_structure_preset(preset_name)
        if not rows:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Preset has no structure rows.")
            return
        self._populate_structure_table(rows)
        self._set_profile_rows(profile_rows)
        self._refresh_profile_table()
        self.lbl_status.setText(f"Loaded structure preset: {preset_name}")

    def _load_profile_preset(self):
        rec = self._selected_structure_record()
        if not rec:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Select a structure row first.")
            return
        sid = str(rec.get("Id", "") or "").strip()
        if not sid:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Selected structure needs an Id before loading a profile preset.")
            return
        if float(rec.get("EndStation", 0.0) or 0.0) <= float(rec.get("StartStation", 0.0) or 0.0):
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Selected structure needs a valid StartStation/EndStation span.")
            return
        preset_name = str(self.cmb_profile_preset.currentText() or "").strip()
        rows = self._make_profile_preset_rows(preset_name, rec)
        if not rows:
            QtWidgets.QMessageBox.information(None, "Edit Structures", "Profile preset could not create any rows.")
            return
        append = bool(self.chk_profile_preset_append.isChecked())
        if append:
            kept = list(self._profile_rows)
            kept.extend(rows)
        else:
            kept = [dict(row) for row in self._profile_rows if str(row.get("StructureId", "") or "").strip() != sid]
            kept.extend(rows)
        self._set_profile_rows(sorted(kept, key=lambda row: (str(row.get("StructureId", "") or ""), float(row.get("Station", 0.0) or 0.0))))
        self._refresh_profile_table()
        self.lbl_status.setText(
            f"Loaded profile preset: {preset_name} | structure={sid} | rows={len(rows)} | mode={'append' if append else 'replace'}"
        )

    def _sort_rows(self):
        rows = self._read_rows()
        rows.sort(key=lambda x: float(x.get("StartStation", 0.0)))
        self._populate_structure_table(rows)

    def _on_browse_csv(self):
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select structure CSV",
            str(self.ed_csv.text() or ""),
            "CSV Files (*.csv *.txt);;All Files (*.*)",
        )
        if path:
            self.ed_csv.setText(str(path))

    def _on_browse_profile_csv(self):
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select structure station-profile CSV",
            str(self.ed_profile_csv.text() or ""),
            "CSV Files (*.csv *.txt);;All Files (*.*)",
        )
        if path:
            self.ed_profile_csv.setText(str(path))

    def _on_browse_shape(self):
        row = self._current_structure_row()
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
        row = self._current_structure_row()
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
        row = self._current_structure_row()
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

    def _on_structure_selection_changed(self):
        if self._loading:
            return
        try:
            self._sync_profile_table_to_store()
            self._refresh_profile_table()
            self._update_shape_status()
            self._refresh_validation_visuals()
        except Exception:
            pass

    def _on_structure_row_pressed(self, row, _col):
        if self._loading:
            return
        self._set_active_structure_row(row)
        self._on_structure_selection_changed()

    def _on_table_item_changed(self, item):
        if self._loading:
            return
        try:
            if item is not None and int(item.column()) == 0:
                new_sid = self._selected_structure_id()
                old_sid = str(self._active_profile_structure_id or "").strip()
                if old_sid and new_sid and old_sid != new_sid:
                    for row in self._profile_rows:
                        if str(row.get("StructureId", "") or "").strip() == old_sid:
                            row["StructureId"] = new_sid
                    self._active_profile_structure_id = new_sid
                    self._refresh_profile_table()
                    self._set_profile_rows(self._profile_rows)
            if item is not None and int(item.column()) in (13, 23):
                self._apply_shape_source_visual(int(item.row()))
                self._update_shape_status()
            self._refresh_detail_panel()
            self._refresh_validation_visuals()
        except Exception:
            pass

    def _on_profile_item_changed(self, item):
        if self._loading:
            return
        try:
            if item is not None and int(item.column()) == 0:
                sid = str(self._active_profile_structure_id or "").strip()
                self._loading = True
                try:
                    item.setText(sid)
                    item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                finally:
                    self._loading = False
            self._sync_profile_table_to_store()
            self._refresh_validation_visuals()
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

        self._populate_structure_table(rows)
        self._refresh_profile_table()
        self.lbl_status.setText(f"Loaded CSV rows: {len(rows)}")
        self._refresh_validation_visuals()

    def _on_load_profile_csv(self):
        path = str(self.ed_profile_csv.text() or "").strip()
        if not path:
            QtWidgets.QMessageBox.warning(None, "Edit Structures", "Profile CSV file path is empty.")
            return
        if not os.path.isfile(path):
            QtWidgets.QMessageBox.warning(None, "Edit Structures", f"Profile CSV file not found:\n{path}")
            return

        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore", newline="") as f:
                rdr = csv.DictReader(f)
                mapping = _structure_profile_csv_mapping(rdr.fieldnames)
                if not mapping.get("StructureId") or not mapping.get("Station"):
                    raise Exception("Profile CSV requires at least StructureId and Station columns.")
                rows = []
                for row in rdr:
                    if not any(str(v or "").strip() for v in row.values()):
                        continue
                    rows.append(
                        {
                            "StructureId": str(row.get(mapping.get("StructureId"), "") or "").strip(),
                            "Station": self._parse_float(row.get(mapping.get("Station"), "")),
                            "Offset": self._parse_float(row.get(mapping.get("Offset"), "")),
                            "Width": self._parse_float(row.get(mapping.get("Width"), "")),
                            "Height": self._parse_float(row.get(mapping.get("Height"), "")),
                            "BottomElevation": self._parse_float(row.get(mapping.get("BottomElevation"), "")),
                            "Cover": self._parse_float(row.get(mapping.get("Cover"), "")),
                            "WallThickness": self._parse_float(row.get(mapping.get("WallThickness"), "")),
                            "FootingWidth": self._parse_float(row.get(mapping.get("FootingWidth"), "")),
                            "FootingThickness": self._parse_float(row.get(mapping.get("FootingThickness"), "")),
                            "CapHeight": self._parse_float(row.get(mapping.get("CapHeight"), "")),
                            "CellCount": self._parse_float(row.get(mapping.get("CellCount"), "")),
                        }
                    )
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Edit Structures", f"Profile CSV load failed: {ex}")
            return

        self._set_profile_rows(rows)
        self._refresh_profile_table()
        self.lbl_status.setText(f"Loaded profile CSV rows: {len(rows)}")
        self._refresh_validation_visuals()

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
        self._sync_profile_table_to_store()
        if not rows:
            QtWidgets.QMessageBox.warning(None, "Edit Structures", "No structure rows to save.")
            return
        ok_count, warn_count, err_count, lines = self._validation_snapshot()
        if err_count > 0:
            msg = [
                "Fix validation errors before Apply.",
                f"OK rows: {ok_count}",
                f"Warnings: {warn_count}",
                f"Errors: {err_count}",
            ]
            if lines:
                msg.append("")
                msg.extend(list(lines[:10]))
            QtWidgets.QMessageBox.warning(None, "Edit Structures", "\n".join(msg))
            return
        if warn_count > 0:
            msg = [
                "Apply with validation warnings?",
                f"OK rows: {ok_count}",
                f"Warnings: {warn_count}",
            ]
            if lines:
                msg.append("")
                msg.extend(list(lines[:8]))
            reply = QtWidgets.QMessageBox.question(
                None,
                "Edit Structures",
                "\n".join(msg),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
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
            obj.ProfileStructureIds = [str(r.get("StructureId", "") or "") for r in self._profile_rows]
            obj.ProfileStations = [float(r.get("Station", 0.0) or 0.0) for r in self._profile_rows]
            obj.ProfileOffsets = [float(r.get("Offset", 0.0) or 0.0) for r in self._profile_rows]
            obj.ProfileWidths = [float(r.get("Width", 0.0) or 0.0) for r in self._profile_rows]
            obj.ProfileHeights = [float(r.get("Height", 0.0) or 0.0) for r in self._profile_rows]
            obj.ProfileBottomElevations = [float(r.get("BottomElevation", 0.0) or 0.0) for r in self._profile_rows]
            obj.ProfileCovers = [float(r.get("Cover", 0.0) or 0.0) for r in self._profile_rows]
            obj.ProfileWallThicknesses = [float(r.get("WallThickness", 0.0) or 0.0) for r in self._profile_rows]
            obj.ProfileFootingWidths = [float(r.get("FootingWidth", 0.0) or 0.0) for r in self._profile_rows]
            obj.ProfileFootingThicknesses = [float(r.get("FootingThickness", 0.0) or 0.0) for r in self._profile_rows]
            obj.ProfileCapHeights = [float(r.get("CapHeight", 0.0) or 0.0) for r in self._profile_rows]
            obj.ProfileCellCounts = [int(round(float(r.get("CellCount", 0.0) or 0.0))) for r in self._profile_rows]
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
                    f"Profile points: {len(self._profile_rows)}",
                    f"Status: {getattr(obj, 'Status', 'Applied')}",
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
                msg = [
                    f"Structure set saved.\nRecords: {len(rows)}\nProfile points: {len(self._profile_rows)}\nStatus: {getattr(obj, 'Status', 'Applied')}"
                ]
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
