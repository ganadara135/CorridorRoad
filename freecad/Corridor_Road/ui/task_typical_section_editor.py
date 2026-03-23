import copy
import csv
import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_all, find_project
from freecad.Corridor_Road.objects.obj_typical_section_template import (
    ALLOWED_COMPONENT_SIDES,
    ALLOWED_COMPONENT_TYPES,
    ALLOWED_PAVEMENT_LAYER_TYPES,
    TypicalSectionTemplate,
    ViewProviderTypicalSectionTemplate,
    build_top_profile,
    component_rows,
    ensure_typical_section_template_properties,
    pavement_rows,
)
from freecad.Corridor_Road.objects.project_links import link_project


COL_HEADERS = [
    "Id",
    "Type",
    "Side",
    "Width",
    "CrossSlopePct",
    "Height",
    "Offset",
    "Order",
    "Enabled",
]

PAV_HEADERS = [
    "Id",
    "Type",
    "Thickness",
    "Enabled",
]


COMPONENT_TYPE_HINTS = {
    "lane": {"row": "Travel lane. CrossSlopePct is the primary control; Height is usually 0.", "highlight": "slope"},
    "shoulder": {"row": "Shoulder strip. CrossSlopePct is usually more important than Height.", "highlight": "slope"},
    "median": {"row": "Median/center strip. Width and CrossSlopePct usually control the profile.", "highlight": "slope"},
    "sidewalk": {"row": "Sidewalk surface. Width and CrossSlopePct define the walking surface.", "highlight": "slope"},
    "bike_lane": {"row": "Bike lane surface. CrossSlopePct usually matches adjacent pavement.", "highlight": "slope"},
    "green_strip": {"row": "Green strip or planted verge. Width and CrossSlopePct define the strip.", "highlight": "slope"},
    "gutter": {"row": "Gutter/drain strip. Width and CrossSlopePct control the shallow drainage break.", "highlight": "slope"},
    "curb": {"row": "Curb step. Height is the vertical curb rise; Width is the curb top width.", "highlight": "height"},
    "ditch": {"row": "Ditch profile. Height is treated as ditch depth; Width is the ditch span.", "highlight": "height"},
    "bench": {"row": "Bench/platform. Usually flat, so CrossSlopePct is often 0 and Height is usually 0.", "highlight": "width"},
}


TYPICAL_SECTION_PRESETS = {
    "2-Lane Rural": {
        "components": [
            {"Id": "LANE-L", "Type": "lane", "Side": "left", "Width": 3.500, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
            {"Id": "SHL-L", "Type": "shoulder", "Side": "left", "Width": 1.500, "CrossSlopePct": 4.0, "Height": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
            {"Id": "LANE-R", "Type": "lane", "Side": "right", "Width": 3.500, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
            {"Id": "SHL-R", "Type": "shoulder", "Side": "right", "Width": 1.500, "CrossSlopePct": 4.0, "Height": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
        ],
        "pavement": [],
    },
    "Urban Complete Street": {
        "components": [
            {"Id": "MED", "Type": "median", "Side": "center", "Width": 2.000, "CrossSlopePct": 0.0, "Height": 0.000, "Offset": 0.000, "Order": 5, "Enabled": True},
            {"Id": "LANE-L1", "Type": "lane", "Side": "left", "Width": 3.250, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
            {"Id": "LANE-L2", "Type": "lane", "Side": "left", "Width": 3.250, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
            {"Id": "BIKE-L", "Type": "bike_lane", "Side": "left", "Width": 1.800, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 30, "Enabled": True},
            {"Id": "CURB-L", "Type": "curb", "Side": "left", "Width": 0.180, "CrossSlopePct": 0.0, "Height": 0.150, "Offset": 0.000, "Order": 40, "Enabled": True},
            {"Id": "SIDEWALK-L", "Type": "sidewalk", "Side": "left", "Width": 2.500, "CrossSlopePct": 1.5, "Height": 0.000, "Offset": 0.000, "Order": 50, "Enabled": True},
            {"Id": "GREEN-L", "Type": "green_strip", "Side": "left", "Width": 1.500, "CrossSlopePct": 5.0, "Height": 0.000, "Offset": 0.000, "Order": 60, "Enabled": True},
            {"Id": "LANE-R1", "Type": "lane", "Side": "right", "Width": 3.250, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
            {"Id": "LANE-R2", "Type": "lane", "Side": "right", "Width": 3.250, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
            {"Id": "BIKE-R", "Type": "bike_lane", "Side": "right", "Width": 1.800, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 30, "Enabled": True},
            {"Id": "CURB-R", "Type": "curb", "Side": "right", "Width": 0.180, "CrossSlopePct": 0.0, "Height": 0.150, "Offset": 0.000, "Order": 40, "Enabled": True},
            {"Id": "SIDEWALK-R", "Type": "sidewalk", "Side": "right", "Width": 2.500, "CrossSlopePct": 1.5, "Height": 0.000, "Offset": 0.000, "Order": 50, "Enabled": True},
            {"Id": "GREEN-R", "Type": "green_strip", "Side": "right", "Width": 1.500, "CrossSlopePct": 5.0, "Height": 0.000, "Offset": 0.000, "Order": 60, "Enabled": True},
        ],
        "pavement": [],
    },
    "Road With Ditch": {
        "components": [
            {"Id": "LANE-L", "Type": "lane", "Side": "left", "Width": 3.500, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
            {"Id": "SHL-L", "Type": "shoulder", "Side": "left", "Width": 1.500, "CrossSlopePct": 4.0, "Height": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
            {"Id": "GUT-L", "Type": "gutter", "Side": "left", "Width": 0.800, "CrossSlopePct": 6.0, "Height": 0.000, "Offset": 0.000, "Order": 30, "Enabled": True},
            {"Id": "DITCH-L", "Type": "ditch", "Side": "left", "Width": 2.000, "CrossSlopePct": 2.0, "Height": 1.000, "Offset": 0.000, "Order": 40, "Enabled": True},
            {"Id": "BENCH-L", "Type": "bench", "Side": "left", "Width": 1.500, "CrossSlopePct": 0.0, "Height": 0.000, "Offset": 0.000, "Order": 50, "Enabled": True},
            {"Id": "LANE-R", "Type": "lane", "Side": "right", "Width": 3.500, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
            {"Id": "SHL-R", "Type": "shoulder", "Side": "right", "Width": 1.500, "CrossSlopePct": 4.0, "Height": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
            {"Id": "GUT-R", "Type": "gutter", "Side": "right", "Width": 0.800, "CrossSlopePct": 6.0, "Height": 0.000, "Offset": 0.000, "Order": 30, "Enabled": True},
            {"Id": "DITCH-R", "Type": "ditch", "Side": "right", "Width": 2.000, "CrossSlopePct": 2.0, "Height": 1.000, "Offset": 0.000, "Order": 40, "Enabled": True},
            {"Id": "BENCH-R", "Type": "bench", "Side": "right", "Width": 1.500, "CrossSlopePct": 0.0, "Height": 0.000, "Offset": 0.000, "Order": 50, "Enabled": True},
        ],
        "pavement": [],
    },
}


QUICK_COMPONENT_TEMPLATES = {
    "lane": {"Id": "LANE", "Type": "lane", "Side": "left", "Width": 3.500, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
    "shoulder": {"Id": "SHL", "Type": "shoulder", "Side": "left", "Width": 1.500, "CrossSlopePct": 4.0, "Height": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
    "curb": {"Id": "CURB", "Type": "curb", "Side": "left", "Width": 0.180, "CrossSlopePct": 0.0, "Height": 0.150, "Offset": 0.000, "Order": 40, "Enabled": True},
    "ditch": {"Id": "DITCH", "Type": "ditch", "Side": "left", "Width": 2.000, "CrossSlopePct": 2.0, "Height": 1.000, "Offset": 0.000, "Order": 40, "Enabled": True},
    "bench": {"Id": "BENCH", "Type": "bench", "Side": "left", "Width": 1.500, "CrossSlopePct": 0.0, "Height": 0.000, "Offset": 0.000, "Order": 50, "Enabled": True},
}


PAVEMENT_PRESETS = {
    "Asphalt Basic": [
        {"Id": "SURF", "Type": "surface", "Thickness": 0.050, "Enabled": True},
        {"Id": "BINDER", "Type": "binder", "Thickness": 0.070, "Enabled": True},
        {"Id": "BASE", "Type": "base", "Thickness": 0.200, "Enabled": True},
        {"Id": "SUBBASE", "Type": "subbase", "Thickness": 0.250, "Enabled": True},
    ],
    "Asphalt Thin": [
        {"Id": "SURF", "Type": "surface", "Thickness": 0.040, "Enabled": True},
        {"Id": "BINDER", "Type": "binder", "Thickness": 0.060, "Enabled": True},
        {"Id": "BASE", "Type": "base", "Thickness": 0.150, "Enabled": True},
        {"Id": "SUBBASE", "Type": "subbase", "Thickness": 0.200, "Enabled": True},
    ],
    "Concrete Road": [
        {"Id": "SURF", "Type": "surface", "Thickness": 0.280, "Enabled": True},
        {"Id": "BASE", "Type": "base", "Thickness": 0.150, "Enabled": True},
        {"Id": "SUBBASE", "Type": "subbase", "Thickness": 0.200, "Enabled": True},
        {"Id": "SUBGRADE", "Type": "subgrade", "Thickness": 0.150, "Enabled": True},
    ],
}


def _find_typical_section_templates(doc):
    return find_all(doc, proxy_type="TypicalSectionTemplate", name_prefixes=("TypicalSectionTemplate",))


class TypicalSectionEditorTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._templates = []
        self._loading = False
        self._component_tint_brushes = {
            "base": None,
            "slope": QtGui.QBrush(QtGui.QColor(52, 68, 92)),
            "height": QtGui.QBrush(QtGui.QColor(88, 66, 44)),
            "width": QtGui.QBrush(QtGui.QColor(56, 78, 52)),
        }
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
        w.setWindowTitle("CorridorRoad - Edit Typical Section")

        main = QtWidgets.QVBoxLayout(w)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        main.addWidget(self.lbl_info)

        gb_target = QtWidgets.QGroupBox("Target")
        fs = QtWidgets.QFormLayout(gb_target)
        self.cmb_target = QtWidgets.QComboBox()
        fs.addRow("Typical Section Template:", self.cmb_target)
        preset_row = QtWidgets.QHBoxLayout()
        self.cmb_preset = QtWidgets.QComboBox()
        self.cmb_preset.addItem("")
        for name in sorted(TYPICAL_SECTION_PRESETS):
            self.cmb_preset.addItem(name)
        self.btn_load_preset = QtWidgets.QPushButton("Load Preset")
        preset_row.addWidget(self.cmb_preset, 1)
        preset_row.addWidget(self.btn_load_preset)
        preset_wrap = QtWidgets.QWidget()
        preset_wrap.setLayout(preset_row)
        fs.addRow("Preset:", preset_wrap)
        csv_row = QtWidgets.QHBoxLayout()
        self.txt_csv = QtWidgets.QLineEdit()
        self.txt_csv.setPlaceholderText("Path to typical section CSV")
        self.btn_browse_csv = QtWidgets.QPushButton("Browse CSV")
        self.btn_load_csv = QtWidgets.QPushButton("Load CSV")
        self.btn_export_csv = QtWidgets.QPushButton("Save Component CSV")
        csv_row.addWidget(self.txt_csv, 1)
        csv_row.addWidget(self.btn_browse_csv)
        csv_row.addWidget(self.btn_load_csv)
        csv_row.addWidget(self.btn_export_csv)
        csv_wrap = QtWidgets.QWidget()
        csv_wrap.setLayout(csv_row)
        fs.addRow("Component CSV:", csv_wrap)
        pav_csv_row = QtWidgets.QHBoxLayout()
        self.txt_pavement_csv = QtWidgets.QLineEdit()
        self.txt_pavement_csv.setPlaceholderText("Path to pavement-layer CSV")
        self.btn_browse_pavement_csv = QtWidgets.QPushButton("Browse Pavement CSV")
        self.btn_load_pavement_csv = QtWidgets.QPushButton("Load Pavement CSV")
        self.btn_export_pavement_csv = QtWidgets.QPushButton("Save Pavement CSV")
        pav_csv_row.addWidget(self.txt_pavement_csv, 1)
        pav_csv_row.addWidget(self.btn_browse_pavement_csv)
        pav_csv_row.addWidget(self.btn_load_pavement_csv)
        pav_csv_row.addWidget(self.btn_export_pavement_csv)
        pav_csv_wrap = QtWidgets.QWidget()
        pav_csv_wrap.setLayout(pav_csv_row)
        fs.addRow("Pavement CSV:", pav_csv_wrap)
        main.addWidget(gb_target)

        quick_btns = QtWidgets.QHBoxLayout()
        self.btn_add_lane = QtWidgets.QPushButton("Add Lane")
        self.btn_add_shoulder = QtWidgets.QPushButton("Add Shoulder")
        self.btn_add_curb = QtWidgets.QPushButton("Add Curb")
        self.btn_add_ditch = QtWidgets.QPushButton("Add Ditch")
        self.btn_add_bench = QtWidgets.QPushButton("Add Bench")
        quick_btns.addWidget(self.btn_add_lane)
        quick_btns.addWidget(self.btn_add_shoulder)
        quick_btns.addWidget(self.btn_add_curb)
        quick_btns.addWidget(self.btn_add_ditch)
        quick_btns.addWidget(self.btn_add_bench)
        main.addLayout(quick_btns)

        self.table = QtWidgets.QTableWidget(0, len(COL_HEADERS))
        self.table.setHorizontalHeaderLabels(COL_HEADERS)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table.setMinimumHeight(320)
        main.addWidget(self.table, 1)

        row_btns = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Row")
        self.btn_remove = QtWidgets.QPushButton("Remove Row")
        self.btn_move_up = QtWidgets.QPushButton("Move Up")
        self.btn_move_down = QtWidgets.QPushButton("Move Down")
        self.btn_mirror_l2r = QtWidgets.QPushButton("Mirror Left -> Right")
        self.btn_mirror_r2l = QtWidgets.QPushButton("Mirror Right -> Left")
        self.btn_sort = QtWidgets.QPushButton("Sort by Order")
        row_btns.addWidget(self.btn_add)
        row_btns.addWidget(self.btn_remove)
        row_btns.addWidget(self.btn_move_up)
        row_btns.addWidget(self.btn_move_down)
        row_btns.addWidget(self.btn_mirror_l2r)
        row_btns.addWidget(self.btn_mirror_r2l)
        row_btns.addWidget(self.btn_sort)
        main.addLayout(row_btns)

        gb_pav = QtWidgets.QGroupBox("Pavement Layers")
        pav_layout = QtWidgets.QVBoxLayout(gb_pav)
        pav_preset_row = QtWidgets.QHBoxLayout()
        self.cmb_pavement_preset = QtWidgets.QComboBox()
        self.cmb_pavement_preset.addItem("")
        for name in sorted(PAVEMENT_PRESETS):
            self.cmb_pavement_preset.addItem(name)
        self.btn_load_pavement_preset = QtWidgets.QPushButton("Load Pavement Preset")
        pav_preset_row.addWidget(self.cmb_pavement_preset, 1)
        pav_preset_row.addWidget(self.btn_load_pavement_preset)
        pav_preset_wrap = QtWidgets.QWidget()
        pav_preset_wrap.setLayout(pav_preset_row)
        pav_layout.addWidget(pav_preset_wrap)
        self.pav_table = QtWidgets.QTableWidget(0, len(PAV_HEADERS))
        self.pav_table.setHorizontalHeaderLabels(PAV_HEADERS)
        self.pav_table.setAlternatingRowColors(True)
        self.pav_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.pav_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.pav_table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.pav_table.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.pav_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.pav_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        hh_pav = self.pav_table.horizontalHeader()
        hh_pav.setStretchLastSection(False)
        hh_pav.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.pav_table.setMinimumHeight(170)
        pav_layout.addWidget(self.pav_table)
        pav_btns = QtWidgets.QHBoxLayout()
        self.btn_add_pavement = QtWidgets.QPushButton("Add Layer")
        self.btn_remove_pavement = QtWidgets.QPushButton("Remove Layer")
        pav_btns.addWidget(self.btn_add_pavement)
        pav_btns.addWidget(self.btn_remove_pavement)
        pav_layout.addLayout(pav_btns)
        main.addWidget(gb_pav)

        gb_status = QtWidgets.QGroupBox("Status")
        fr = QtWidgets.QFormLayout(gb_status)
        self.lbl_status = QtWidgets.QLabel("Idle")
        self.lbl_status.setWordWrap(True)
        self.chk_show_pavement_preview = QtWidgets.QCheckBox("Show pavement preview")
        self.chk_show_pavement_preview.setChecked(True)
        fr.addRow("Status:", self.lbl_status)
        fr.addRow(self.chk_show_pavement_preview)
        main.addWidget(gb_status)

        gb_summary = QtWidgets.QGroupBox("Summary")
        sr = QtWidgets.QFormLayout(gb_summary)
        self.lbl_summary_components = QtWidgets.QLabel("-")
        self.lbl_summary_components.setWordWrap(True)
        self.lbl_summary_width = QtWidgets.QLabel("-")
        self.lbl_summary_edges = QtWidgets.QLabel("-")
        self.lbl_summary_pavement = QtWidgets.QLabel("-")
        sr.addRow("Components:", self.lbl_summary_components)
        sr.addRow("Top width:", self.lbl_summary_width)
        sr.addRow("Edge types:", self.lbl_summary_edges)
        sr.addRow("Pavement:", self.lbl_summary_pavement)
        main.addWidget(gb_summary)

        bottom = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("Apply")
        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_close = QtWidgets.QPushButton("Close")
        bottom.addWidget(self.btn_apply)
        bottom.addWidget(self.btn_refresh)
        bottom.addWidget(self.btn_close)
        main.addLayout(bottom)

        self.cmb_target.currentIndexChanged.connect(self._on_target_changed)
        self.cmb_preset.currentIndexChanged.connect(self._update_summary)
        self.btn_load_preset.clicked.connect(self._load_preset)
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_move_up.clicked.connect(self._move_row_up)
        self.btn_move_down.clicked.connect(self._move_row_down)
        self.btn_mirror_l2r.clicked.connect(lambda: self._mirror_selected_row("left", "right"))
        self.btn_mirror_r2l.clicked.connect(lambda: self._mirror_selected_row("right", "left"))
        self.btn_sort.clicked.connect(self._sort_rows)
        self.btn_add_lane.clicked.connect(lambda: self._add_component_template("lane"))
        self.btn_add_shoulder.clicked.connect(lambda: self._add_component_template("shoulder"))
        self.btn_add_curb.clicked.connect(lambda: self._add_component_template("curb"))
        self.btn_add_ditch.clicked.connect(lambda: self._add_component_template("ditch"))
        self.btn_add_bench.clicked.connect(lambda: self._add_component_template("bench"))
        self.btn_browse_csv.clicked.connect(self._browse_csv)
        self.btn_load_csv.clicked.connect(self._load_csv)
        self.btn_export_csv.clicked.connect(self._export_csv)
        self.btn_browse_pavement_csv.clicked.connect(self._browse_pavement_csv)
        self.btn_load_pavement_csv.clicked.connect(self._load_pavement_csv)
        self.btn_export_pavement_csv.clicked.connect(self._export_pavement_csv)
        self.btn_load_pavement_preset.clicked.connect(self._load_pavement_preset)
        self.btn_add_pavement.clicked.connect(self._add_pavement_row)
        self.btn_remove_pavement.clicked.connect(self._remove_pavement_row)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_refresh.clicked.connect(self._refresh_context)
        self.btn_close.clicked.connect(self.reject)
        self.table.itemChanged.connect(self._on_component_table_changed)
        self.pav_table.itemChanged.connect(self._on_pavement_table_changed)

        self._set_rows(4)
        self._set_pavement_rows(4)
        self._update_summary()
        return w

    @staticmethod
    def _fmt_obj(prefix, obj):
        return f"[{prefix}] {obj.Label} ({obj.Name})"

    @staticmethod
    def _find_col(row_dict, names, default=""):
        for name in names:
            if name in row_dict:
                return row_dict.get(name, default)
        lowered = {str(k).strip().lower(): v for k, v in dict(row_dict).items()}
        for name in names:
            key = str(name).strip().lower()
            if key in lowered:
                return lowered.get(key, default)
        return default

    def _fill_targets(self, selected=None):
        self.cmb_target.clear()
        self.cmb_target.addItem("[New] Create new Typical Section Template")
        for o in self._templates:
            self.cmb_target.addItem(self._fmt_obj("TypicalSectionTemplate", o))
        idx = 0
        if selected is not None:
            for i, o in enumerate(self._templates):
                if o == selected:
                    idx = i + 1
                    break
        self.cmb_target.setCurrentIndex(idx)

    def _current_target(self):
        i = int(self.cmb_target.currentIndex())
        if i <= 0:
            return None
        j = i - 1
        if j < 0 or j >= len(self._templates):
            return None
        return self._templates[j]

    def _refresh_context(self):
        if self.doc is None:
            self.lbl_info.setText("No active document.")
            return
        self._loading = True
        try:
            self._templates = _find_typical_section_templates(self.doc)
            prj = find_project(self.doc)
            pref = getattr(prj, "TypicalSectionTemplate", None) if prj is not None and hasattr(prj, "TypicalSectionTemplate") else None
            self._fill_targets(selected=pref)
            self.lbl_info.setText(
                "Typical section components define the finished-grade top profile.\n"
                "You can also load component rows from CSV.\n"
                f"TypicalSectionTemplate objects found: {len(self._templates)}"
            )
        finally:
            self._loading = False
        self._on_target_changed()
        self._update_summary()

    def _on_target_changed(self):
        if self._loading:
            return
        obj = self._current_target()
        if obj is None:
            self._loading = True
            try:
                self.table.setRowCount(0)
                self._set_rows(4)
                self.pav_table.setRowCount(0)
                self._set_pavement_rows(4)
                self.chk_show_pavement_preview.setChecked(True)
                self.lbl_status.setText("New TypicalSectionTemplate will be created.")
            finally:
                self._loading = False
            self._refresh_component_hints()
            self._update_summary()
            return

        ensure_typical_section_template_properties(obj)
        rows = component_rows(obj)
        pav_rows = pavement_rows(obj)
        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(max(4, len(rows)))
            for i, row in enumerate(rows):
                self._set_cell_text(i, 0, row.get("Id", ""))
                self._set_cell_text(i, 1, row.get("Type", ""))
                self._set_cell_text(i, 2, row.get("Side", ""))
                self._set_cell_text(i, 3, f"{float(row.get('Width', 0.0) or 0.0):.3f}")
                self._set_cell_text(i, 4, f"{float(row.get('CrossSlopePct', 0.0) or 0.0):.3f}")
                self._set_cell_text(i, 5, f"{float(row.get('Height', 0.0) or 0.0):.3f}")
                self._set_cell_text(i, 6, f"{float(row.get('Offset', 0.0) or 0.0):.3f}")
                self._set_cell_text(i, 7, f"{int(row.get('Order', 0) or 0)}")
                self._set_cell_text(i, 8, "true" if bool(row.get("Enabled", True)) else "false")
            self.pav_table.setRowCount(0)
            self._set_pavement_rows(max(4, len(pav_rows)))
            for i, row in enumerate(pav_rows):
                self._set_pavement_cell_text(i, 0, row.get("Id", ""))
                self._set_pavement_cell_text(i, 1, row.get("Type", ""))
                self._set_pavement_cell_text(i, 2, f"{float(row.get('Thickness', 0.0) or 0.0):.3f}")
                self._set_pavement_cell_text(i, 3, "true" if bool(row.get("Enabled", True)) else "false")
            self.chk_show_pavement_preview.setChecked(bool(getattr(obj, "ShowPavementPreview", True)))
            self.lbl_status.setText(str(getattr(obj, "Status", "Loaded")))
        finally:
            self._loading = False
        self._refresh_component_hints()
        self._update_summary()

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
        for col, items in (
            (1, [""] + list(ALLOWED_COMPONENT_TYPES)),
            (2, [""] + list(ALLOWED_COMPONENT_SIDES)),
            (8, ["true", "false"]),
        ):
            cmb = self.table.cellWidget(row, col)
            if cmb is None:
                cmb = QtWidgets.QComboBox()
                cmb.addItems(items)
                cmb.currentIndexChanged.connect(self._on_component_combo_changed)
                self.table.setCellWidget(row, col, cmb)

    def _set_pavement_rows(self, n):
        self._loading = True
        try:
            self.pav_table.setRowCount(n)
            for r in range(n):
                for c in range(len(PAV_HEADERS)):
                    if self.pav_table.item(r, c) is None:
                        self.pav_table.setItem(r, c, QtWidgets.QTableWidgetItem(""))
                self._ensure_pavement_combo_cells(r)
        finally:
            self._loading = False

    def _ensure_pavement_combo_cells(self, row):
        for col, items in (
            (1, [""] + list(ALLOWED_PAVEMENT_LAYER_TYPES)),
            (3, ["true", "false"]),
        ):
            cmb = self.pav_table.cellWidget(row, col)
            if cmb is None:
                cmb = QtWidgets.QComboBox()
                cmb.addItems(items)
                cmb.currentIndexChanged.connect(self._on_pavement_combo_changed)
                self.pav_table.setCellWidget(row, col, cmb)

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
        if cmb is not None and c in (1, 2, 8):
            self._set_combo_value(cmb, str(txt or ""))
            return
        it = self.table.item(r, c)
        if it is None:
            it = QtWidgets.QTableWidgetItem("")
            self.table.setItem(r, c, it)
        it.setText(str(txt or ""))

    def _set_pavement_cell_text(self, r, c, txt):
        cmb = self.pav_table.cellWidget(r, c)
        if cmb is not None and c in (1, 3):
            self._set_combo_value(cmb, str(txt or ""))
            return
        it = self.pav_table.item(r, c)
        if it is None:
            it = QtWidgets.QTableWidgetItem("")
            self.pav_table.setItem(r, c, it)
        it.setText(str(txt or ""))

    def _get_cell_text(self, r, c):
        cmb = self.table.cellWidget(r, c)
        if cmb is not None and c in (1, 2, 8):
            return str(cmb.currentText() or "")
        it = self.table.item(r, c)
        return (it.text() if it else "") or ""

    def _get_pavement_cell_text(self, r, c):
        cmb = self.pav_table.cellWidget(r, c)
        if cmb is not None and c in (1, 3):
            return str(cmb.currentText() or "")
        it = self.pav_table.item(r, c)
        return (it.text() if it else "") or ""

    @staticmethod
    def _parse_float(txt):
        try:
            return float(str(txt or "").strip())
        except Exception:
            return 0.0

    @staticmethod
    def _parse_int(txt):
        try:
            return int(round(float(str(txt or "").strip())))
        except Exception:
            return 0

    def _read_rows(self):
        rows = []
        for r in range(self.table.rowCount()):
            row = [self._get_cell_text(r, c).strip() for c in range(len(COL_HEADERS))]
            if not any(row):
                continue
            rows.append(
                {
                    "Id": row[0] or f"COMP-{r+1:02d}",
                    "Type": row[1],
                    "Side": row[2],
                    "Width": self._parse_float(row[3]),
                    "CrossSlopePct": self._parse_float(row[4]),
                    "Height": self._parse_float(row[5]),
                    "Offset": self._parse_float(row[6]),
                    "Order": self._parse_int(row[7]),
                    "Enabled": str(row[8] or "true").strip().lower() not in ("0", "false", "no", "off"),
                }
            )
        return rows

    def _read_pavement_rows(self):
        rows = []
        for r in range(self.pav_table.rowCount()):
            row = [self._get_pavement_cell_text(r, c).strip() for c in range(len(PAV_HEADERS))]
            if not any(row):
                continue
            rows.append(
                {
                    "Id": row[0] or f"LAYER-{r+1:02d}",
                    "Type": row[1],
                    "Thickness": self._parse_float(row[2]),
                    "Enabled": str(row[3] or "true").strip().lower() not in ("0", "false", "no", "off"),
                }
            )
        return rows

    def _write_rows_to_table(self, rows):
        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(max(4, len(rows)))
            for i, row in enumerate(rows):
                self._set_cell_text(i, 0, row.get("Id", ""))
                self._set_cell_text(i, 1, row.get("Type", ""))
                self._set_cell_text(i, 2, row.get("Side", ""))
                self._set_cell_text(i, 3, f"{float(row.get('Width', 0.0) or 0.0):.3f}")
                self._set_cell_text(i, 4, f"{float(row.get('CrossSlopePct', 0.0) or 0.0):.3f}")
                self._set_cell_text(i, 5, f"{float(row.get('Height', 0.0) or 0.0):.3f}")
                self._set_cell_text(i, 6, f"{float(row.get('Offset', 0.0) or 0.0):.3f}")
                self._set_cell_text(i, 7, f"{int(row.get('Order', 0) or 0)}")
                self._set_cell_text(i, 8, "true" if bool(row.get("Enabled", True)) else "false")
        finally:
            self._loading = False
        self._refresh_component_hints()
        self._update_summary()

    def _write_pavement_rows_to_table(self, rows):
        self._loading = True
        try:
            self.pav_table.setRowCount(0)
            self._set_pavement_rows(max(4, len(rows)))
            for i, row in enumerate(rows):
                self._set_pavement_cell_text(i, 0, row.get("Id", ""))
                self._set_pavement_cell_text(i, 1, row.get("Type", ""))
                self._set_pavement_cell_text(i, 2, f"{float(row.get('Thickness', 0.0) or 0.0):.3f}")
                self._set_pavement_cell_text(i, 3, "true" if bool(row.get("Enabled", True)) else "false")
        finally:
            self._loading = False
        self._update_summary()

    def _ensure_target(self):
        obj = self._current_target()
        if obj is not None:
            ensure_typical_section_template_properties(obj)
            return obj
        obj = self.doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
        TypicalSectionTemplate(obj)
        ViewProviderTypicalSectionTemplate(obj.ViewObject)
        obj.Label = "Typical Section Template"
        return obj

    def _add_row(self):
        self._set_rows(self.table.rowCount() + 1)
        self._refresh_component_hints()
        self._update_summary()

    def _remove_row(self):
        r = self.table.currentRow()
        if r < 0:
            r = self.table.rowCount() - 1
        if r >= 0:
            self.table.removeRow(r)
        self._refresh_component_hints()
        self._update_summary()

    def _add_pavement_row(self):
        self._set_pavement_rows(self.pav_table.rowCount() + 1)
        self._update_summary()

    def _remove_pavement_row(self):
        r = self.pav_table.currentRow()
        if r < 0:
            r = self.pav_table.rowCount() - 1
        if r >= 0:
            self.pav_table.removeRow(r)
        self._update_summary()

    def _sort_rows(self):
        rows = self._read_rows()
        rows.sort(key=lambda row: (int(row.get("Order", 0) or 0), str(row.get("Side", "")), str(row.get("Id", ""))))
        self._write_rows_to_table(rows)

    def _move_row_up(self):
        rows = self._read_rows()
        idx = int(self.table.currentRow())
        if idx <= 0 or idx >= len(rows):
            return
        rows[idx - 1], rows[idx] = rows[idx], rows[idx - 1]
        self._write_rows_to_table(rows)
        self.table.selectRow(idx - 1)

    def _move_row_down(self):
        rows = self._read_rows()
        idx = int(self.table.currentRow())
        if idx < 0 or idx >= (len(rows) - 1):
            return
        rows[idx], rows[idx + 1] = rows[idx + 1], rows[idx]
        self._write_rows_to_table(rows)
        self.table.selectRow(idx + 1)

    def _next_component_order(self):
        rows = self._read_rows()
        if not rows:
            return 10
        return max(int(r.get("Order", 0) or 0) for r in rows) + 10

    def _unique_component_id(self, base_id):
        existing = {str(r.get("Id", "") or "").strip() for r in self._read_rows()}
        candidate = str(base_id or "COMP").strip() or "COMP"
        if candidate not in existing:
            return candidate
        i = 2
        while True:
            test = f"{candidate}-{i:02d}"
            if test not in existing:
                return test
            i += 1

    def _add_component_template(self, template_key):
        tpl = copy.deepcopy(QUICK_COMPONENT_TEMPLATES.get(str(template_key or "").strip().lower() or ""))
        if not tpl:
            return
        rows = self._read_rows()
        tpl["Id"] = self._unique_component_id(tpl.get("Id", "COMP"))
        tpl["Order"] = self._next_component_order()
        rows.append(tpl)
        self._write_rows_to_table(rows)
        self.table.selectRow(max(0, len(rows) - 1))

    def _mirror_selected_row(self, from_side, to_side):
        idx = int(self.table.currentRow())
        rows = self._read_rows()
        if idx < 0 or idx >= len(rows):
            QtWidgets.QMessageBox.information(None, "Typical Section", "Select a component row first.")
            return
        row = copy.deepcopy(rows[idx])
        src_side = str(row.get("Side", "") or "").strip().lower()
        if src_side != str(from_side or "").strip().lower():
            QtWidgets.QMessageBox.information(None, "Typical Section", f"Selected row is not on the {from_side} side.")
            return
        row["Side"] = str(to_side or "").strip().lower()
        base_id = str(row.get("Id", "") or "").strip() or "COMP"
        if base_id.endswith("-L"):
            base_id = base_id[:-2] + "-R"
        elif base_id.endswith("-R"):
            base_id = base_id[:-2] + "-L"
        elif base_id.endswith("_L"):
            base_id = base_id[:-2] + "_R"
        elif base_id.endswith("_R"):
            base_id = base_id[:-2] + "_L"
        else:
            base_id = f"{base_id}-{to_side[:1].upper()}"
        row["Id"] = self._unique_component_id(base_id)
        rows.insert(idx + 1, row)
        self._write_rows_to_table(rows)
        self.table.selectRow(idx + 1)

    def _browse_csv(self):
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select Typical Section CSV",
            self.txt_csv.text().strip() or "",
            "CSV Files (*.csv);;All Files (*.*)",
        )
        if path:
            self.txt_csv.setText(path)

    def _export_csv(self):
        path, _flt = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Save Typical Section CSV",
            self.txt_csv.text().strip() or "",
            "CSV Files (*.csv);;All Files (*.*)",
        )
        if not path:
            return
        rows = self._read_rows()
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as fp:
                writer = csv.DictWriter(fp, fieldnames=list(COL_HEADERS))
                writer.writeheader()
                for row in rows:
                    writer.writerow(
                        {
                            "Id": row.get("Id", ""),
                            "Type": row.get("Type", ""),
                            "Side": row.get("Side", ""),
                            "Width": f"{float(row.get('Width', 0.0) or 0.0):.3f}",
                            "CrossSlopePct": f"{float(row.get('CrossSlopePct', 0.0) or 0.0):.3f}",
                            "Height": f"{float(row.get('Height', 0.0) or 0.0):.3f}",
                            "Offset": f"{float(row.get('Offset', 0.0) or 0.0):.3f}",
                            "Order": int(row.get("Order", 0) or 0),
                            "Enabled": "true" if bool(row.get("Enabled", True)) else "false",
                        }
                    )
            self.txt_csv.setText(path)
            self.lbl_status.setText(f"Saved {len(rows)} component rows to CSV.")
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Typical Section", f"CSV save failed: {ex}")

    def _browse_pavement_csv(self):
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select Pavement Layer CSV",
            self.txt_pavement_csv.text().strip() or "",
            "CSV Files (*.csv);;All Files (*.*)",
        )
        if path:
            self.txt_pavement_csv.setText(path)

    def _export_pavement_csv(self):
        path, _flt = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Save Pavement Layer CSV",
            self.txt_pavement_csv.text().strip() or "",
            "CSV Files (*.csv);;All Files (*.*)",
        )
        if not path:
            return
        rows = self._read_pavement_rows()
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as fp:
                writer = csv.DictWriter(fp, fieldnames=list(PAV_HEADERS))
                writer.writeheader()
                for row in rows:
                    writer.writerow(
                        {
                            "Id": row.get("Id", ""),
                            "Type": row.get("Type", ""),
                            "Thickness": f"{float(row.get('Thickness', 0.0) or 0.0):.3f}",
                            "Enabled": "true" if bool(row.get("Enabled", True)) else "false",
                        }
                    )
            self.txt_pavement_csv.setText(path)
            self.lbl_status.setText(f"Saved {len(rows)} pavement rows to CSV.")
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Typical Section", f"Pavement CSV save failed: {ex}")

    def _load_preset(self):
        name = str(self.cmb_preset.currentText() or "").strip()
        data = TYPICAL_SECTION_PRESETS.get(name)
        if not data:
            QtWidgets.QMessageBox.information(None, "Typical Section", "Select a preset first.")
            return
        self._write_rows_to_table(copy.deepcopy(list(data.get("components", []) or [])))
        self._write_pavement_rows_to_table(copy.deepcopy(list(data.get("pavement", []) or [])))
        self.lbl_status.setText(f"Loaded preset: {name}")

    def _load_pavement_preset(self):
        name = str(self.cmb_pavement_preset.currentText() or "").strip()
        rows = copy.deepcopy(list(PAVEMENT_PRESETS.get(name, []) or []))
        if not rows:
            QtWidgets.QMessageBox.information(None, "Typical Section", "Select a pavement preset first.")
            return
        self._write_pavement_rows_to_table(rows)
        self.lbl_status.setText(f"Loaded pavement preset: {name}")

    def _load_csv(self):
        path = self.txt_csv.text().strip()
        if not path:
            QtWidgets.QMessageBox.information(None, "Typical Section", "Select a CSV file first.")
            return
        if not os.path.exists(path):
            QtWidgets.QMessageBox.warning(None, "Typical Section", f"CSV not found:\n{path}")
            return

        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as fp:
                sample = fp.read(4096)
                fp.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
                except Exception:
                    dialect = csv.excel
                reader = csv.DictReader(fp, dialect=dialect)
                rows = []
                for i, row_dict in enumerate(reader, start=1):
                    if not any(str(v or "").strip() for v in dict(row_dict).values()):
                        continue
                    rows.append(
                        {
                            "Id": str(self._find_col(row_dict, ("Id", "ComponentId"), f"COMP-{i:02d}") or f"COMP-{i:02d}").strip(),
                            "Type": str(self._find_col(row_dict, ("Type", "ComponentType"), "lane") or "lane").strip().lower(),
                            "Side": str(self._find_col(row_dict, ("Side",), "left") or "left").strip().lower(),
                            "Width": self._parse_float(self._find_col(row_dict, ("Width",), 0.0)),
                            "CrossSlopePct": self._parse_float(self._find_col(row_dict, ("CrossSlopePct", "CrossSlope", "SlopePct"), 0.0)),
                            "Height": self._parse_float(self._find_col(row_dict, ("Height", "StepHeight"), 0.0)),
                            "Offset": self._parse_float(self._find_col(row_dict, ("Offset",), 0.0)),
                            "Order": self._parse_int(self._find_col(row_dict, ("Order", "SortOrder"), i * 10)),
                            "Enabled": str(self._find_col(row_dict, ("Enabled", "Use"), "true")).strip().lower() not in ("0", "false", "no", "off"),
                        }
                    )
            if not rows:
                QtWidgets.QMessageBox.warning(None, "Typical Section", "No component rows were found in the CSV.")
                return
            self._write_rows_to_table(rows)
            self.lbl_status.setText(f"Loaded {len(rows)} component rows from CSV.")
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Typical Section", f"CSV load failed: {ex}")

    def _load_pavement_csv(self):
        path = self.txt_pavement_csv.text().strip()
        if not path:
            QtWidgets.QMessageBox.information(None, "Typical Section", "Select a pavement CSV file first.")
            return
        if not os.path.exists(path):
            QtWidgets.QMessageBox.warning(None, "Typical Section", f"Pavement CSV not found:\n{path}")
            return

        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as fp:
                sample = fp.read(4096)
                fp.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
                except Exception:
                    dialect = csv.excel
                reader = csv.DictReader(fp, dialect=dialect)
                rows = []
                for i, row_dict in enumerate(reader, start=1):
                    if not any(str(v or "").strip() for v in dict(row_dict).values()):
                        continue
                    rows.append(
                        {
                            "Id": str(self._find_col(row_dict, ("Id", "LayerId"), f"LAYER-{i:02d}") or f"LAYER-{i:02d}").strip(),
                            "Type": str(self._find_col(row_dict, ("Type", "LayerType"), "base") or "base").strip().lower(),
                            "Thickness": self._parse_float(self._find_col(row_dict, ("Thickness", "Depth"), 0.0)),
                            "Enabled": str(self._find_col(row_dict, ("Enabled", "Use"), "true")).strip().lower() not in ("0", "false", "no", "off"),
                        }
                    )
            if not rows:
                QtWidgets.QMessageBox.warning(None, "Typical Section", "No pavement rows were found in the CSV.")
                return
            self._write_pavement_rows_to_table(rows)
            self.lbl_status.setText(f"Loaded {len(rows)} pavement rows from CSV.")
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Typical Section", f"Pavement CSV load failed: {ex}")

    def _sync_preview_object(self, obj, rows, pav_rows):
        if obj is None:
            return None
        ensure_typical_section_template_properties(obj)
        obj.ComponentIds = [str(r.get("Id", "") or "") for r in rows]
        obj.ComponentTypes = [str(r.get("Type", "") or "") for r in rows]
        obj.ComponentSides = [str(r.get("Side", "") or "") for r in rows]
        obj.ComponentWidths = [float(r.get("Width", 0.0) or 0.0) for r in rows]
        obj.ComponentCrossSlopes = [float(r.get("CrossSlopePct", 0.0) or 0.0) for r in rows]
        obj.ComponentHeights = [float(r.get("Height", 0.0) or 0.0) for r in rows]
        obj.ComponentOffsets = [float(r.get("Offset", 0.0) or 0.0) for r in rows]
        obj.ComponentOrders = [int(r.get("Order", 0) or 0) for r in rows]
        obj.ComponentEnabled = [1 if bool(r.get("Enabled", True)) else 0 for r in rows]
        obj.PavementLayerIds = [str(r.get("Id", "") or "") for r in pav_rows]
        obj.PavementLayerTypes = [str(r.get("Type", "") or "") for r in pav_rows]
        obj.PavementLayerThicknesses = [float(r.get("Thickness", 0.0) or 0.0) for r in pav_rows]
        obj.PavementLayerEnabled = [1 if bool(r.get("Enabled", True)) else 0 for r in pav_rows]
        return obj

    def _estimate_top_width(self, rows):
        left = 0.0
        right = 0.0
        center = 0.0
        for row in rows:
            if not bool(row.get("Enabled", True)):
                continue
            side = str(row.get("Side", "") or "").strip().lower()
            width = max(0.0, float(row.get("Width", 0.0) or 0.0))
            offset = max(0.0, abs(float(row.get("Offset", 0.0) or 0.0)))
            if side == "center":
                center += width
            elif side == "left":
                left += width + offset
            elif side == "right":
                right += width + offset
            elif side == "both":
                left += width + offset
                right += width + offset
        return float(left + right + center)

    def _ensure_preview_object(self, rows, pav_rows):
        obj = self._current_target()
        return self._sync_preview_object(obj, rows, pav_rows)

    def _component_summary_snapshot(self):
        rows = self._read_rows()
        pav_rows = self._read_pavement_rows()
        enabled_rows = [r for r in rows if bool(r.get("Enabled", True))]
        enabled_pav = [r for r in pav_rows if bool(r.get("Enabled", True))]
        left_rows = [r for r in enabled_rows if str(r.get("Side", "") or "").strip().lower() == "left"]
        right_rows = [r for r in enabled_rows if str(r.get("Side", "") or "").strip().lower() == "right"]
        obj = self._ensure_preview_object(rows, pav_rows)
        top_width = self._estimate_top_width(enabled_rows)
        if obj is not None:
            pts = list(build_top_profile(obj) or [])
            if pts:
                xs = [float(p.x) for p in pts]
                top_width = max(xs) - min(xs)
        pav_thk = sum(float(r.get("Thickness", 0.0) or 0.0) for r in enabled_pav)
        return {
            "total": len(rows),
            "enabled": len(enabled_rows),
            "left_edge": str(left_rows[-1].get("Type", "") or "") if left_rows else "-",
            "right_edge": str(right_rows[-1].get("Type", "") or "") if right_rows else "-",
            "top_width": float(top_width),
            "pav_count": len(pav_rows),
            "pav_enabled": len(enabled_pav),
            "pav_total": float(pav_thk),
        }

    def _refresh_component_hints(self):
        base_brush = self.table.palette().brush(QtGui.QPalette.Base)
        text_brush = self.table.palette().brush(QtGui.QPalette.Text)
        for row in range(self.table.rowCount()):
            typ = str(self._get_cell_text(row, 1) or "").strip().lower()
            hint = COMPONENT_TYPE_HINTS.get(typ, {})
            row_tip = hint.get("row", "Set component Type, Side, Width, CrossSlopePct, Height, Offset, Order, Enabled.")
            highlight = hint.get("highlight", "base")
            for col in range(len(COL_HEADERS)):
                it = self.table.item(row, col)
                if it is not None:
                    it.setToolTip(row_tip)
            for col in (1, 2, 8):
                cmb = self.table.cellWidget(row, col)
                if cmb is not None:
                    cmb.setToolTip(row_tip)
            for col, mode in ((3, "width"), (4, "slope"), (5, "height"), (6, "base"), (7, "base")):
                it = self.table.item(row, col)
                if it is None:
                    continue
                brush_key = mode
                if col == 4:
                    brush_key = "slope" if highlight == "slope" else "base"
                elif col == 5:
                    brush_key = "height" if highlight == "height" else "base"
                it.setForeground(text_brush)
                if brush_key == "base":
                    it.setBackground(base_brush)
                else:
                    it.setBackground(self._component_tint_brushes.get(brush_key, base_brush))

    def _update_summary(self, *_args):
        if self._loading or self.doc is None:
            return
        try:
            snap = self._component_summary_snapshot()
            self.lbl_summary_components.setText(f"{snap['enabled']} enabled / {snap['total']} total")
            self.lbl_summary_width.setText(f"{snap['top_width']:.3f} m")
            self.lbl_summary_edges.setText(f"{snap['left_edge']} / {snap['right_edge']}")
            self.lbl_summary_pavement.setText(
                f"{snap['pav_enabled']} enabled / {snap['pav_count']} total, {snap['pav_total']:.3f} m"
            )
        except Exception:
            self.lbl_summary_components.setText("-")
            self.lbl_summary_width.setText("-")
            self.lbl_summary_edges.setText("-")
            self.lbl_summary_pavement.setText("-")

    def _on_component_combo_changed(self, *_args):
        if self._loading:
            return
        self._refresh_component_hints()
        self._update_summary()

    def _on_pavement_combo_changed(self, *_args):
        if self._loading:
            return
        self._update_summary()

    def _on_component_table_changed(self, *_args):
        if self._loading:
            return
        self._refresh_component_hints()
        self._update_summary()

    def _on_pavement_table_changed(self, *_args):
        if self._loading:
            return
        self._update_summary()

    def _apply(self):
        if self.doc is None:
            QtWidgets.QMessageBox.warning(None, "Typical Section", "No active document.")
            return
        try:
            obj = self._ensure_target()
            rows = self._read_rows()
            pav_rows = self._read_pavement_rows()
            obj.ComponentIds = [str(r.get("Id", "") or "") for r in rows]
            obj.ComponentTypes = [str(r.get("Type", "") or "") for r in rows]
            obj.ComponentSides = [str(r.get("Side", "") or "") for r in rows]
            obj.ComponentWidths = [float(r.get("Width", 0.0) or 0.0) for r in rows]
            obj.ComponentCrossSlopes = [float(r.get("CrossSlopePct", 0.0) or 0.0) for r in rows]
            obj.ComponentHeights = [float(r.get("Height", 0.0) or 0.0) for r in rows]
            obj.ComponentOffsets = [float(r.get("Offset", 0.0) or 0.0) for r in rows]
            obj.ComponentOrders = [int(r.get("Order", 0) or 0) for r in rows]
            obj.ComponentEnabled = [1 if bool(r.get("Enabled", True)) else 0 for r in rows]
            obj.PavementLayerIds = [str(r.get("Id", "") or "") for r in pav_rows]
            obj.PavementLayerTypes = [str(r.get("Type", "") or "") for r in pav_rows]
            obj.PavementLayerThicknesses = [float(r.get("Thickness", 0.0) or 0.0) for r in pav_rows]
            obj.PavementLayerEnabled = [1 if bool(r.get("Enabled", True)) else 0 for r in pav_rows]
            obj.ShowPavementPreview = bool(self.chk_show_pavement_preview.isChecked())
            obj.touch()
            self.doc.recompute()
            prj = find_project(self.doc)
            if prj is not None:
                link_project(prj, links={"TypicalSectionTemplate": obj}, adopt_extra=[obj])
            self._refresh_context()
            self._fill_targets(selected=obj)
            self.lbl_status.setText(str(getattr(obj, "Status", "Updated")))
            QtWidgets.QMessageBox.information(
                None,
                "Typical Section",
                "Typical section template updated.\n"
                f"Components: {len(rows)}\n"
                f"Pavement layers: {len(pav_rows)}\n"
                f"Pavement total thickness: {float(getattr(obj, 'PavementTotalThickness', 0.0) or 0.0):.3f} m",
            )
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Typical Section", f"Apply failed: {ex}")
