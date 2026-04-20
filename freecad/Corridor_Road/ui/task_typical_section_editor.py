import copy
import csv
import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_all, find_project
from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.obj_typical_section_template import (
    ALLOWED_COMPONENT_SIDES,
    ALLOWED_DITCH_SHAPES,
    ALLOWED_COMPONENT_TYPES,
    ALLOWED_PAVEMENT_LAYER_TYPES,
    TypicalSectionSelectionDisplay,
    TypicalSectionPavementDisplay,
    TypicalSectionTemplate,
    ViewProviderTypicalSectionSelectionDisplay,
    ViewProviderTypicalSectionPavementDisplay,
    ViewProviderTypicalSectionTemplate,
    component_rows,
    ensure_typical_section_template_properties,
    pavement_rows,
)
from freecad.Corridor_Road.objects.project_links import link_project


COL_HEADERS = [
    "Id",
    "Type",
    "Shape",
    "Side",
    "Width",
    "CrossSlopePct",
    "Height",
    "ExtraWidth",
    "BackSlopePct",
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
    "curb": {"row": "Curb step. Height is curb rise; Width is curb top width; ExtraWidth is curb face/gutter run; BackSlopePct is top/back slope.", "highlight": "height"},
    "ditch": {"row": "Ditch profile. Shape chooses v, u, or trapezoid. Width is total span; Height is ditch depth; ExtraWidth is flat bottom width; BackSlopePct is outer-side slope. Pavement preview stops before ditch rows.", "highlight": "height"},
    "berm": {"row": "Berm/platform. Width is bench width; CrossSlopePct is bench slope; ExtraWidth is outer taper width; BackSlopePct is taper slope. Pavement preview stops before berm rows.", "highlight": "width"},
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
            {"Id": "CURB-L", "Type": "curb", "Side": "left", "Width": 0.180, "CrossSlopePct": 0.0, "Height": 0.150, "ExtraWidth": 0.050, "BackSlopePct": 1.0, "Offset": 0.000, "Order": 40, "Enabled": True},
            {"Id": "SIDEWALK-L", "Type": "sidewalk", "Side": "left", "Width": 2.500, "CrossSlopePct": 1.5, "Height": 0.000, "Offset": 0.000, "Order": 50, "Enabled": True},
            {"Id": "GREEN-L", "Type": "green_strip", "Side": "left", "Width": 1.500, "CrossSlopePct": 5.0, "Height": 0.000, "Offset": 0.000, "Order": 60, "Enabled": True},
            {"Id": "LANE-R1", "Type": "lane", "Side": "right", "Width": 3.250, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
            {"Id": "LANE-R2", "Type": "lane", "Side": "right", "Width": 3.250, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
            {"Id": "BIKE-R", "Type": "bike_lane", "Side": "right", "Width": 1.800, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 30, "Enabled": True},
            {"Id": "CURB-R", "Type": "curb", "Side": "right", "Width": 0.180, "CrossSlopePct": 0.0, "Height": 0.150, "ExtraWidth": 0.050, "BackSlopePct": 1.0, "Offset": 0.000, "Order": 40, "Enabled": True},
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
            {"Id": "DITCH-L", "Type": "ditch", "Shape": "trapezoid", "Side": "left", "Width": 2.000, "CrossSlopePct": 2.0, "Height": 1.000, "ExtraWidth": 0.700, "BackSlopePct": -10.0, "Offset": 0.000, "Order": 40, "Enabled": True},
            {"Id": "BERM-L", "Type": "berm", "Side": "left", "Width": 1.500, "CrossSlopePct": 0.0, "Height": 0.000, "ExtraWidth": 1.000, "BackSlopePct": 8.0, "Offset": 0.000, "Order": 50, "Enabled": True},
            {"Id": "LANE-R", "Type": "lane", "Side": "right", "Width": 3.500, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
            {"Id": "SHL-R", "Type": "shoulder", "Side": "right", "Width": 1.500, "CrossSlopePct": 4.0, "Height": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
            {"Id": "GUT-R", "Type": "gutter", "Side": "right", "Width": 0.800, "CrossSlopePct": 6.0, "Height": 0.000, "Offset": 0.000, "Order": 30, "Enabled": True},
            {"Id": "DITCH-R", "Type": "ditch", "Shape": "trapezoid", "Side": "right", "Width": 2.000, "CrossSlopePct": 2.0, "Height": 1.000, "ExtraWidth": 0.700, "BackSlopePct": -10.0, "Offset": 0.000, "Order": 40, "Enabled": True},
            {"Id": "BERM-R", "Type": "berm", "Side": "right", "Width": 1.500, "CrossSlopePct": 0.0, "Height": 0.000, "ExtraWidth": 1.000, "BackSlopePct": 8.0, "Offset": 0.000, "Order": 50, "Enabled": True},
        ],
        "pavement": [],
    },
    "Boulevard With Raised Curb": {
        "components": [
            {"Id": "LANE-L", "Type": "lane", "Side": "left", "Width": 3.250, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
            {"Id": "CURB-L", "Type": "curb", "Side": "left", "Width": 0.180, "CrossSlopePct": 0.0, "Height": 0.180, "ExtraWidth": 0.080, "BackSlopePct": 1.5, "Offset": 0.000, "Order": 20, "Enabled": True},
            {"Id": "WALK-L", "Type": "sidewalk", "Side": "left", "Width": 2.000, "CrossSlopePct": 1.5, "Height": 0.000, "Offset": 0.000, "Order": 30, "Enabled": True},
            {"Id": "GREEN-L", "Type": "green_strip", "Side": "left", "Width": 1.200, "CrossSlopePct": 4.0, "Height": 0.000, "Offset": 0.000, "Order": 40, "Enabled": True},
            {"Id": "LANE-R", "Type": "lane", "Side": "right", "Width": 3.250, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
            {"Id": "CURB-R", "Type": "curb", "Side": "right", "Width": 0.180, "CrossSlopePct": 0.0, "Height": 0.180, "ExtraWidth": 0.080, "BackSlopePct": 1.5, "Offset": 0.000, "Order": 20, "Enabled": True},
            {"Id": "WALK-R", "Type": "sidewalk", "Side": "right", "Width": 2.000, "CrossSlopePct": 1.5, "Height": 0.000, "Offset": 0.000, "Order": 30, "Enabled": True},
            {"Id": "GREEN-R", "Type": "green_strip", "Side": "right", "Width": 1.200, "CrossSlopePct": 4.0, "Height": 0.000, "Offset": 0.000, "Order": 40, "Enabled": True},
        ],
        "pavement": [],
    },
    "Flat-Bottom Ditch Pair": {
        "components": [
            {"Id": "LANE-L", "Type": "lane", "Side": "left", "Width": 3.500, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
            {"Id": "SHL-L", "Type": "shoulder", "Side": "left", "Width": 1.500, "CrossSlopePct": 4.0, "Height": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
            {"Id": "DITCH-L", "Type": "ditch", "Shape": "trapezoid", "Side": "left", "Width": 3.000, "CrossSlopePct": 2.0, "Height": 1.100, "ExtraWidth": 1.000, "BackSlopePct": -12.0, "Offset": 0.000, "Order": 30, "Enabled": True},
            {"Id": "BERM-L", "Type": "berm", "Side": "left", "Width": 1.200, "CrossSlopePct": 0.0, "Height": 0.000, "ExtraWidth": 0.800, "BackSlopePct": 6.0, "Offset": 0.000, "Order": 40, "Enabled": True},
            {"Id": "LANE-R", "Type": "lane", "Side": "right", "Width": 3.500, "CrossSlopePct": 2.0, "Height": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
            {"Id": "SHL-R", "Type": "shoulder", "Side": "right", "Width": 1.500, "CrossSlopePct": 4.0, "Height": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
            {"Id": "DITCH-R", "Type": "ditch", "Shape": "trapezoid", "Side": "right", "Width": 3.000, "CrossSlopePct": 2.0, "Height": 1.100, "ExtraWidth": 1.000, "BackSlopePct": -12.0, "Offset": 0.000, "Order": 30, "Enabled": True},
            {"Id": "BERM-R", "Type": "berm", "Side": "right", "Width": 1.200, "CrossSlopePct": 0.0, "Height": 0.000, "ExtraWidth": 0.800, "BackSlopePct": 6.0, "Offset": 0.000, "Order": 40, "Enabled": True},
        ],
        "pavement": [],
    },
}


QUICK_COMPONENT_TEMPLATES = {
    "lane": {"Id": "LANE", "Type": "lane", "Side": "left", "Width": 3.500, "CrossSlopePct": 2.0, "Height": 0.000, "ExtraWidth": 0.000, "BackSlopePct": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
    "shoulder": {"Id": "SHL", "Type": "shoulder", "Side": "left", "Width": 1.500, "CrossSlopePct": 4.0, "Height": 0.000, "ExtraWidth": 0.000, "BackSlopePct": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
    "curb": {"Id": "CURB", "Type": "curb", "Side": "left", "Width": 0.180, "CrossSlopePct": 0.0, "Height": 0.150, "ExtraWidth": 0.050, "BackSlopePct": 1.000, "Offset": 0.000, "Order": 40, "Enabled": True},
    "ditch": {"Id": "DITCH", "Type": "ditch", "Shape": "trapezoid", "Side": "left", "Width": 2.000, "CrossSlopePct": 2.0, "Height": 1.000, "ExtraWidth": 0.700, "BackSlopePct": -10.000, "Offset": 0.000, "Order": 40, "Enabled": True},
    "berm": {"Id": "BERM", "Type": "berm", "Side": "left", "Width": 1.500, "CrossSlopePct": 0.0, "Height": 0.000, "ExtraWidth": 1.000, "BackSlopePct": 8.000, "Offset": 0.000, "Order": 50, "Enabled": True},
}


QUICK_COMPONENT_BUNDLES = {
    "rural_ditch_pair": [
        {"Id": "GUT-L", "Type": "gutter", "Side": "left", "Width": 0.800, "CrossSlopePct": 6.0, "Height": 0.000, "ExtraWidth": 0.000, "BackSlopePct": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
        {"Id": "DITCH-L", "Type": "ditch", "Shape": "trapezoid", "Side": "left", "Width": 2.400, "CrossSlopePct": 2.0, "Height": 1.000, "ExtraWidth": 0.800, "BackSlopePct": -10.0, "Offset": 0.000, "Order": 20, "Enabled": True},
        {"Id": "BERM-L", "Type": "berm", "Side": "left", "Width": 1.200, "CrossSlopePct": 0.0, "Height": 0.000, "ExtraWidth": 0.800, "BackSlopePct": 6.0, "Offset": 0.000, "Order": 30, "Enabled": True},
        {"Id": "GUT-R", "Type": "gutter", "Side": "right", "Width": 0.800, "CrossSlopePct": 6.0, "Height": 0.000, "ExtraWidth": 0.000, "BackSlopePct": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
        {"Id": "DITCH-R", "Type": "ditch", "Shape": "trapezoid", "Side": "right", "Width": 2.400, "CrossSlopePct": 2.0, "Height": 1.000, "ExtraWidth": 0.800, "BackSlopePct": -10.0, "Offset": 0.000, "Order": 20, "Enabled": True},
        {"Id": "BERM-R", "Type": "berm", "Side": "right", "Width": 1.200, "CrossSlopePct": 0.0, "Height": 0.000, "ExtraWidth": 0.800, "BackSlopePct": 6.0, "Offset": 0.000, "Order": 30, "Enabled": True},
    ],
    "urban_edge_pair": [
        {"Id": "CURB-L", "Type": "curb", "Side": "left", "Width": 0.180, "CrossSlopePct": 0.0, "Height": 0.150, "ExtraWidth": 0.060, "BackSlopePct": 1.0, "Offset": 0.000, "Order": 10, "Enabled": True},
        {"Id": "WALK-L", "Type": "sidewalk", "Side": "left", "Width": 2.000, "CrossSlopePct": 1.5, "Height": 0.000, "ExtraWidth": 0.000, "BackSlopePct": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
        {"Id": "GREEN-L", "Type": "green_strip", "Side": "left", "Width": 1.200, "CrossSlopePct": 4.0, "Height": 0.000, "ExtraWidth": 0.000, "BackSlopePct": 0.000, "Offset": 0.000, "Order": 30, "Enabled": True},
        {"Id": "CURB-R", "Type": "curb", "Side": "right", "Width": 0.180, "CrossSlopePct": 0.0, "Height": 0.150, "ExtraWidth": 0.060, "BackSlopePct": 1.0, "Offset": 0.000, "Order": 10, "Enabled": True},
        {"Id": "WALK-R", "Type": "sidewalk", "Side": "right", "Width": 2.000, "CrossSlopePct": 1.5, "Height": 0.000, "ExtraWidth": 0.000, "BackSlopePct": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
        {"Id": "GREEN-R", "Type": "green_strip", "Side": "right", "Width": 1.200, "CrossSlopePct": 4.0, "Height": 0.000, "ExtraWidth": 0.000, "BackSlopePct": 0.000, "Offset": 0.000, "Order": 30, "Enabled": True},
    ],
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


COMP_COL_ID = 0
COMP_COL_TYPE = 1
COMP_COL_SHAPE = 2
COMP_COL_SIDE = 3
COMP_COL_WIDTH = 4
COMP_COL_SLOPE = 5
COMP_COL_HEIGHT = 6
COMP_COL_EXTRA = 7
COMP_COL_BACK_SLOPE = 8
COMP_COL_OFFSET = 9
COMP_COL_ORDER = 10
COMP_COL_ENABLED = 11
CSV_COMMENT_PREFIX = "#"
CSV_LINEAR_UNIT_KEYS = {
    "linear",
    "linearunit",
    "linear_unit",
    "lengthunit",
    "length_unit",
    "unit",
    "units",
}


def _find_typical_section_templates(doc):
    return find_all(doc, proxy_type="TypicalSectionTemplate", name_prefixes=("TypicalSectionTemplate",))


def _normalize_csv_linear_unit(value):
    token = str(value or "").strip().lower()
    if token in ("m", "meter", "meters", "metre", "metres"):
        return "m"
    if token in ("mm", "millimeter", "millimeters", "millimetre", "millimetres"):
        return "mm"
    if token == "custom":
        return "custom"
    return ""


def _parse_csv_unit_metadata(lines):
    meta = {}
    for raw_line in list(lines or []):
        line = str(raw_line or "").strip()
        if not line.startswith(CSV_COMMENT_PREFIX):
            continue
        body = line[1:].strip()
        if not body:
            continue
        for part in body.replace(";", ",").split(","):
            seg = str(part or "").strip()
            if "=" not in seg:
                continue
            key, value = seg.split("=", 1)
            norm_key = "".join(ch for ch in str(key or "").strip().lower() if ch.isalnum() or ch == "_")
            if norm_key in CSV_LINEAR_UNIT_KEYS:
                token = _normalize_csv_linear_unit(value)
                if token:
                    meta["linear_unit"] = token
    return meta


def _read_csv_dict_rows(path: str):
    with open(path, "r", encoding="utf-8-sig", newline="") as fp:
        lines = list(fp.readlines())
    metadata = _parse_csv_unit_metadata(lines)
    data_lines = [line for line in lines if not str(line or "").lstrip().startswith(CSV_COMMENT_PREFIX)]
    if not data_lines:
        return {"rows": [], "fieldnames": [], "metadata": metadata}
    sample = "".join(data_lines[:20])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except Exception:
        dialect = csv.excel
    reader = csv.DictReader(data_lines, dialect=dialect)
    return {
        "rows": [dict(row) for row in reader],
        "fieldnames": list(reader.fieldnames or []),
        "metadata": metadata,
    }


class TypicalSectionEditorTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._templates = []
        self._loading = False
        self._active_component_row = 0
        self._active_pavement_row = 0
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

    def _unit_context(self):
        prj = find_project(self.doc)
        return prj if prj is not None else self.doc

    def _meters_from_csv(self, value, linear_unit: str = ""):
        return _units.meters_from_user_length(self._unit_context(), float(value or 0.0), unit=linear_unit, use_default="import")

    def _csv_from_meters(self, meters, linear_unit: str = ""):
        return _units.user_length_from_meters(self._unit_context(), float(meters or 0.0), unit=linear_unit, use_default="export")

    def _display_unit_label(self) -> str:
        return str(_units.get_linear_display_unit(self._unit_context()) or "m")

    def _meters_from_display(self, value):
        return _units.meters_from_user_length(self._unit_context(), float(value or 0.0), use_default="display")

    def _display_from_meters(self, meters):
        return _units.user_length_from_meters(self._unit_context(), float(meters or 0.0), use_default="display")

    def _format_display_length(self, meters, digits: int = 3) -> str:
        return f"{self._display_from_meters(meters):.{int(digits)}f}"

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
        main.addWidget(gb_target)

        helper_btns = QtWidgets.QHBoxLayout()
        self.btn_add_rural_ditch_pair = QtWidgets.QPushButton("Add Rural Ditch Pair")
        self.btn_add_urban_edge_pair = QtWidgets.QPushButton("Add Urban Edge Pair")
        helper_btns.addWidget(self.btn_add_rural_ditch_pair)
        helper_btns.addWidget(self.btn_add_urban_edge_pair)
        helper_btns.addStretch(1)
        main.addLayout(helper_btns)

        self.table = QtWidgets.QTableWidget(0, len(COL_HEADERS))
        self.table.setHorizontalHeaderLabels(COL_HEADERS)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setMouseTracking(False)
        self.table.viewport().setMouseTracking(False)
        self.table.setAttribute(QtCore.Qt.WA_Hover, False)
        self.table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table.setMinimumHeight(320)
        main.addWidget(self.table, 1)

        row_btns_wrap = QtWidgets.QVBoxLayout()
        row_btns_top = QtWidgets.QHBoxLayout()
        row_btns_bottom = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Row")
        self.btn_remove = QtWidgets.QPushButton("Remove Row")
        self.btn_move_up = QtWidgets.QPushButton("Move Up")
        self.btn_move_down = QtWidgets.QPushButton("Move Down")
        self.btn_mirror_l2r = QtWidgets.QPushButton("Mirror Left -> Right")
        self.btn_mirror_r2l = QtWidgets.QPushButton("Mirror Right -> Left")
        self.btn_sort = QtWidgets.QPushButton("Sort by Order")
        self.btn_refresh_preview = QtWidgets.QPushButton("Refresh Preview")
        row_btns_top.addWidget(self.btn_add)
        row_btns_top.addWidget(self.btn_remove)
        row_btns_top.addWidget(self.btn_move_up)
        row_btns_top.addWidget(self.btn_move_down)
        row_btns_top.addStretch(1)
        row_btns_bottom.addWidget(self.btn_mirror_l2r)
        row_btns_bottom.addWidget(self.btn_mirror_r2l)
        row_btns_bottom.addWidget(self.btn_sort)
        row_btns_bottom.addStretch(1)
        row_btns_bottom.addWidget(self.btn_refresh_preview)
        row_btns_wrap.addLayout(row_btns_top)
        row_btns_wrap.addLayout(row_btns_bottom)
        main.addLayout(row_btns_wrap)

        gb_pav = QtWidgets.QGroupBox("Pavement Layers")
        pav_layout = QtWidgets.QVBoxLayout(gb_pav)
        pav_preset_row = QtWidgets.QHBoxLayout()
        self.cmb_pavement_preset = QtWidgets.QComboBox()
        self.cmb_pavement_preset.addItem("")
        for name in sorted(PAVEMENT_PRESETS):
            self.cmb_pavement_preset.addItem(name)
        self.btn_load_pavement_preset = QtWidgets.QPushButton("Load Pavement Preset")
        pav_preset_row.addWidget(QtWidgets.QLabel("Preset:"))
        pav_preset_row.addWidget(self.cmb_pavement_preset, 1)
        pav_preset_row.addWidget(self.btn_load_pavement_preset)
        pav_preset_wrap = QtWidgets.QWidget()
        pav_preset_wrap.setLayout(pav_preset_row)
        pav_layout.addWidget(pav_preset_wrap)
        pav_csv_row = QtWidgets.QHBoxLayout()
        self.txt_pavement_csv = QtWidgets.QLineEdit()
        self.txt_pavement_csv.setPlaceholderText("Path to pavement-layer CSV")
        self.btn_browse_pavement_csv = QtWidgets.QPushButton("Browse Pavement CSV")
        self.btn_load_pavement_csv = QtWidgets.QPushButton("Load Pavement CSV")
        self.btn_export_pavement_csv = QtWidgets.QPushButton("Save Pavement CSV")
        pav_csv_row.addWidget(QtWidgets.QLabel("Pavement CSV:"))
        pav_csv_row.addWidget(self.txt_pavement_csv, 1)
        pav_csv_row.addWidget(self.btn_browse_pavement_csv)
        pav_csv_row.addWidget(self.btn_load_pavement_csv)
        pav_csv_row.addWidget(self.btn_export_pavement_csv)
        pav_csv_wrap = QtWidgets.QWidget()
        pav_csv_wrap.setLayout(pav_csv_row)
        pav_layout.addWidget(pav_csv_wrap)
        self.pav_table = QtWidgets.QTableWidget(0, len(PAV_HEADERS))
        self.pav_table.setHorizontalHeaderLabels(PAV_HEADERS)
        self.pav_table.setAlternatingRowColors(True)
        self.pav_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.pav_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.pav_table.setMouseTracking(False)
        self.pav_table.viewport().setMouseTracking(False)
        self.pav_table.setAttribute(QtCore.Qt.WA_Hover, False)
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
        fr.addRow("Status:", self.lbl_status)
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

        preview_row = QtWidgets.QHBoxLayout()
        self.chk_show_preview_wire = QtWidgets.QCheckBox("Show Preview Wire")
        self.chk_show_preview_wire.setChecked(True)
        self.chk_show_pavement_display = QtWidgets.QCheckBox("Show PavementDisplay")
        self.chk_show_pavement_display.setChecked(True)
        preview_row.addWidget(self.chk_show_preview_wire)
        preview_row.addWidget(self.chk_show_pavement_display)
        preview_row.addStretch(1)
        main.addLayout(preview_row)

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
        self.btn_add_rural_ditch_pair.clicked.connect(lambda: self._add_component_bundle("rural_ditch_pair"))
        self.btn_add_urban_edge_pair.clicked.connect(lambda: self._add_component_bundle("urban_edge_pair"))
        self.btn_browse_csv.clicked.connect(self._browse_csv)
        self.btn_load_csv.clicked.connect(self._load_csv)
        self.btn_export_csv.clicked.connect(self._export_csv)
        self.btn_browse_pavement_csv.clicked.connect(self._browse_pavement_csv)
        self.btn_load_pavement_csv.clicked.connect(self._load_pavement_csv)
        self.btn_export_pavement_csv.clicked.connect(self._export_pavement_csv)
        self.btn_load_pavement_preset.clicked.connect(self._load_pavement_preset)
        self.btn_add_pavement.clicked.connect(self._add_pavement_row)
        self.btn_remove_pavement.clicked.connect(self._remove_pavement_row)
        self.chk_show_preview_wire.toggled.connect(self._on_preview_visibility_changed)
        self.chk_show_pavement_display.toggled.connect(self._on_preview_visibility_changed)
        self.btn_refresh_preview.clicked.connect(self._refresh_preview)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_refresh.clicked.connect(self._refresh_context)
        self.btn_close.clicked.connect(self.reject)
        self.table.itemChanged.connect(self._on_component_table_changed)
        self.pav_table.itemChanged.connect(self._on_pavement_table_changed)
        self.table.itemDelegate().closeEditor.connect(self._on_component_editor_closed)
        self.pav_table.itemDelegate().closeEditor.connect(self._on_pavement_editor_closed)
        self.table.currentCellChanged.connect(self._on_component_current_cell_changed)
        self.pav_table.currentCellChanged.connect(self._on_pavement_current_cell_changed)
        self.table.itemSelectionChanged.connect(self._remember_component_selection)
        self.pav_table.itemSelectionChanged.connect(self._remember_pavement_selection)
        self.table.itemSelectionChanged.connect(self._lock_component_selection)
        self.pav_table.itemSelectionChanged.connect(self._lock_pavement_selection)

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
                f"TypicalSectionTemplate objects found: {len(self._templates)}\n"
                f"Display unit: {self._display_unit_label()}"
            )
        finally:
            self._loading = False
        self._on_target_changed()
        self._sync_preview_controls()
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
                self.lbl_status.setText("New TypicalSectionTemplate will be created.")
            finally:
                self._loading = False
            self._sync_preview_controls()
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
                self._set_cell_text(i, COMP_COL_ID, row.get("Id", ""))
                self._set_cell_text(i, COMP_COL_TYPE, row.get("Type", ""))
                self._set_cell_text(i, COMP_COL_SHAPE, row.get("Shape", ""))
                self._set_cell_text(i, COMP_COL_SIDE, row.get("Side", ""))
                self._set_cell_text(i, COMP_COL_WIDTH, self._format_display_length(row.get("Width", 0.0)))
                self._set_cell_text(i, COMP_COL_SLOPE, f"{float(row.get('CrossSlopePct', 0.0) or 0.0):.3f}")
                self._set_cell_text(i, COMP_COL_HEIGHT, self._format_display_length(row.get("Height", 0.0)))
                self._set_cell_text(i, COMP_COL_EXTRA, self._format_display_length(row.get("ExtraWidth", 0.0)))
                self._set_cell_text(i, COMP_COL_BACK_SLOPE, f"{float(row.get('BackSlopePct', 0.0) or 0.0):.3f}")
                self._set_cell_text(i, COMP_COL_OFFSET, self._format_display_length(row.get("Offset", 0.0)))
                self._set_cell_text(i, COMP_COL_ORDER, f"{int(row.get('Order', 0) or 0)}")
                self._set_cell_text(i, COMP_COL_ENABLED, "true" if bool(row.get("Enabled", True)) else "false")
            self.pav_table.setRowCount(0)
            self._set_pavement_rows(max(4, len(pav_rows)))
            for i, row in enumerate(pav_rows):
                self._set_pavement_cell_text(i, 0, row.get("Id", ""))
                self._set_pavement_cell_text(i, 1, row.get("Type", ""))
                self._set_pavement_cell_text(i, 2, self._format_display_length(row.get("Thickness", 0.0)))
                self._set_pavement_cell_text(i, 3, "true" if bool(row.get("Enabled", True)) else "false")
            self.lbl_status.setText(str(getattr(obj, "Status", "Loaded")))
        finally:
            self._loading = False
        self._sync_preview_controls()
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
            (COMP_COL_TYPE, [""] + list(ALLOWED_COMPONENT_TYPES)),
            (COMP_COL_SHAPE, list(ALLOWED_DITCH_SHAPES)),
            (COMP_COL_SIDE, [""] + list(ALLOWED_COMPONENT_SIDES)),
            (COMP_COL_ENABLED, ["true", "false"]),
        ):
            cmb = self.table.cellWidget(row, col)
            if cmb is None:
                cmb = QtWidgets.QComboBox()
                cmb.addItems(items)
                cmb.setProperty("table_row", row)
                cmb.setFocusPolicy(QtCore.Qt.NoFocus)
                cmb.setMouseTracking(False)
                cmb.setAttribute(QtCore.Qt.WA_Hover, False)
                cmb.currentIndexChanged.connect(self._on_component_combo_changed)
                self.table.setCellWidget(row, col, cmb)
            else:
                cmb.setProperty("table_row", row)
        self._sync_shape_combo_for_row(row)

    def _sync_shape_combo_for_row(self, row):
        cmb = self.table.cellWidget(row, COMP_COL_SHAPE)
        if cmb is None:
            return
        typ = str(self._get_cell_text(row, COMP_COL_TYPE) or "").strip().lower()
        is_ditch = typ == "ditch"
        self._loading = True
        try:
            if not is_ditch:
                self._set_combo_value(cmb, "")
            cmb.setEnabled(is_ditch)
            cmb.setFocusPolicy(QtCore.Qt.NoFocus)
            cmb.setMouseTracking(False)
            cmb.setAttribute(QtCore.Qt.WA_Hover, False)
            if is_ditch:
                cmb.setToolTip("Ditch shape: v, u, or trapezoid.")
            else:
                cmb.setToolTip("Shape is only used for ditch rows.")
        finally:
            self._loading = False

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
                cmb.setProperty("table_row", row)
                cmb.setFocusPolicy(QtCore.Qt.NoFocus)
                cmb.setMouseTracking(False)
                cmb.setAttribute(QtCore.Qt.WA_Hover, False)
                cmb.currentIndexChanged.connect(self._on_pavement_combo_changed)
                self.pav_table.setCellWidget(row, col, cmb)
            else:
                cmb.setProperty("table_row", row)

    def _remember_component_selection(self):
        if self._loading:
            return
        row = int(self.table.currentRow())
        if row >= 0:
            self._active_component_row = row

    def _remember_pavement_selection(self):
        if self._loading:
            return
        row = int(self.pav_table.currentRow())
        if row >= 0:
            self._active_pavement_row = row

    def _restore_component_selection(self):
        if self.table.rowCount() <= 0:
            return
        row = max(0, min(int(self._active_component_row or 0), self.table.rowCount() - 1))
        self.table.setCurrentCell(row, 0)
        self.table.selectRow(row)

    def _restore_pavement_selection(self):
        if self.pav_table.rowCount() <= 0:
            return
        row = max(0, min(int(self._active_pavement_row or 0), self.pav_table.rowCount() - 1))
        self.pav_table.setCurrentCell(row, 0)
        self.pav_table.selectRow(row)

    def _lock_component_selection(self):
        if self._loading or self.table.rowCount() <= 0:
            return
        row = max(0, min(int(self._active_component_row or 0), self.table.rowCount() - 1))
        if self.table.currentRow() != row:
            self.table.setCurrentCell(row, 0)
            self.table.selectRow(row)

    def _lock_pavement_selection(self):
        if self._loading or self.pav_table.rowCount() <= 0:
            return
        row = max(0, min(int(self._active_pavement_row or 0), self.pav_table.rowCount() - 1))
        if self.pav_table.currentRow() != row:
            self.pav_table.setCurrentCell(row, 0)
            self.pav_table.selectRow(row)

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
        if cmb is not None and c in (COMP_COL_TYPE, COMP_COL_SHAPE, COMP_COL_SIDE, COMP_COL_ENABLED):
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
        if cmb is not None and c in (COMP_COL_TYPE, COMP_COL_SHAPE, COMP_COL_SIDE, COMP_COL_ENABLED):
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
            typ = str(row[COMP_COL_TYPE] or "").strip().lower()
            if typ == "bench":
                typ = "berm"
            shape = str(row[COMP_COL_SHAPE] or "").strip().lower()
            if typ != "ditch":
                shape = ""
            rows.append(
                {
                    "Id": row[COMP_COL_ID] or f"COMP-{r+1:02d}",
                    "Type": typ,
                    "Shape": shape,
                    "Side": row[COMP_COL_SIDE],
                    "Width": self._meters_from_display(self._parse_float(row[COMP_COL_WIDTH])),
                    "CrossSlopePct": self._parse_float(row[COMP_COL_SLOPE]),
                    "Height": self._meters_from_display(self._parse_float(row[COMP_COL_HEIGHT])),
                    "ExtraWidth": self._meters_from_display(self._parse_float(row[COMP_COL_EXTRA])),
                    "BackSlopePct": self._parse_float(row[COMP_COL_BACK_SLOPE]),
                    "Offset": self._meters_from_display(self._parse_float(row[COMP_COL_OFFSET])),
                    "Order": self._parse_int(row[COMP_COL_ORDER]),
                    "Enabled": str(row[COMP_COL_ENABLED] or "true").strip().lower() not in ("0", "false", "no", "off"),
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
                    "Thickness": self._meters_from_display(self._parse_float(row[2])),
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
                self._set_cell_text(i, COMP_COL_ID, row.get("Id", ""))
                self._set_cell_text(i, COMP_COL_TYPE, row.get("Type", ""))
                self._set_cell_text(i, COMP_COL_SHAPE, row.get("Shape", ""))
                self._set_cell_text(i, COMP_COL_SIDE, row.get("Side", ""))
                self._set_cell_text(i, COMP_COL_WIDTH, self._format_display_length(row.get("Width", 0.0)))
                self._set_cell_text(i, COMP_COL_SLOPE, f"{float(row.get('CrossSlopePct', 0.0) or 0.0):.3f}")
                self._set_cell_text(i, COMP_COL_HEIGHT, self._format_display_length(row.get("Height", 0.0)))
                self._set_cell_text(i, COMP_COL_EXTRA, self._format_display_length(row.get("ExtraWidth", 0.0)))
                self._set_cell_text(i, COMP_COL_BACK_SLOPE, f"{float(row.get('BackSlopePct', 0.0) or 0.0):.3f}")
                self._set_cell_text(i, COMP_COL_OFFSET, self._format_display_length(row.get("Offset", 0.0)))
                self._set_cell_text(i, COMP_COL_ORDER, f"{int(row.get('Order', 0) or 0)}")
                self._set_cell_text(i, COMP_COL_ENABLED, "true" if bool(row.get("Enabled", True)) else "false")
        finally:
            self._loading = False
        self._restore_component_selection()
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
                self._set_pavement_cell_text(i, 2, self._format_display_length(row.get("Thickness", 0.0)))
                self._set_pavement_cell_text(i, 3, "true" if bool(row.get("Enabled", True)) else "false")
        finally:
            self._loading = False
        self._restore_pavement_selection()
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

    def _find_pavement_display(self, src_obj):
        if self.doc is None or src_obj is None:
            return None
        for o in list(getattr(self.doc, "Objects", []) or []):
            try:
                if getattr(getattr(o, "Proxy", None), "Type", "") == "TypicalSectionPavementDisplay":
                    if getattr(o, "SourceTypicalSection", None) == src_obj:
                        return o
            except Exception:
                pass
        return None

    def _ensure_pavement_display(self, src_obj):
        disp = self._find_pavement_display(src_obj)
        if disp is not None:
            disp.Label = "PavementDisplay"
            return disp
        disp = self.doc.addObject("Part::FeaturePython", "TypicalSectionPavementDisplay")
        TypicalSectionPavementDisplay(disp)
        ViewProviderTypicalSectionPavementDisplay(disp.ViewObject)
        disp.Label = "PavementDisplay"
        disp.SourceTypicalSection = src_obj
        return disp

    def _find_selection_display(self, src_obj):
        if self.doc is None or src_obj is None:
            return None
        for o in list(getattr(self.doc, "Objects", []) or []):
            try:
                if getattr(getattr(o, "Proxy", None), "Type", "") == "TypicalSectionSelectionDisplay":
                    if getattr(o, "SourceTypicalSection", None) == src_obj:
                        return o
            except Exception:
                pass
        return None

    def _ensure_selection_display(self, src_obj):
        disp = self._find_selection_display(src_obj)
        if disp is not None:
            disp.Label = "SelectedComponentPreview"
            self._style_selection_display(disp)
            return disp
        disp = self.doc.addObject("Part::FeaturePython", "TypicalSectionSelectionDisplay")
        TypicalSectionSelectionDisplay(disp)
        ViewProviderTypicalSectionSelectionDisplay(disp.ViewObject)
        disp.Label = "SelectedComponentPreview"
        disp.SourceTypicalSection = src_obj
        self._style_selection_display(disp)
        return disp

    def _style_selection_display(self, disp):
        try:
            vobj = getattr(disp, "ViewObject", None)
            if vobj is None:
                return
            vobj.Visibility = True
            vobj.DisplayMode = "Wireframe"
            vobj.LineWidth = 6
            vobj.LineColor = (0.20, 0.85, 0.95)
            vobj.PointColor = (0.20, 0.85, 0.95)
        except Exception:
            pass

    def _style_typical_preview_display(self, obj):
        try:
            vobj = getattr(obj, "ViewObject", None)
            if vobj is None:
                return
            vobj.Visibility = bool(self.chk_show_preview_wire.isChecked())
            vobj.DisplayMode = "Wireframe"
            vobj.LineWidth = 2
            vobj.LineColor = (0.55, 0.58, 0.62)
            vobj.PointColor = (0.55, 0.58, 0.62)
        except Exception:
            pass

    def _add_row(self):
        self._set_rows(self.table.rowCount() + 1)
        self._refresh_component_hints()
        self._update_summary()
        self._schedule_preview()

    def _remove_row(self):
        r = self.table.currentRow()
        if r < 0:
            r = self.table.rowCount() - 1
        if r >= 0:
            self.table.removeRow(r)
        self._refresh_component_hints()
        self._update_summary()
        self._schedule_preview()

    def _add_pavement_row(self):
        self._set_pavement_rows(self.pav_table.rowCount() + 1)
        self._update_summary()
        self._schedule_preview()

    def _remove_pavement_row(self):
        r = self.pav_table.currentRow()
        if r < 0:
            r = self.pav_table.rowCount() - 1
        if r >= 0:
            self.pav_table.removeRow(r)
        self._update_summary()
        self._schedule_preview()

    def _sort_rows(self):
        rows = self._read_rows()
        rows.sort(key=lambda row: (int(row.get("Order", 0) or 0), str(row.get("Side", "")), str(row.get("Id", ""))))
        self._write_rows_to_table(rows)
        self._schedule_preview()

    def _move_row_up(self):
        rows = self._read_rows()
        idx = int(self.table.currentRow())
        if idx <= 0 or idx >= len(rows):
            return
        rows[idx - 1], rows[idx] = rows[idx], rows[idx - 1]
        self._write_rows_to_table(rows)
        self.table.selectRow(idx - 1)
        self._schedule_preview()

    def _move_row_down(self):
        rows = self._read_rows()
        idx = int(self.table.currentRow())
        if idx < 0 or idx >= (len(rows) - 1):
            return
        rows[idx], rows[idx + 1] = rows[idx + 1], rows[idx]
        self._write_rows_to_table(rows)
        self.table.selectRow(idx + 1)
        self._schedule_preview()

    def _next_component_order(self):
        rows = self._read_rows()
        if not rows:
            return 10
        return max(int(r.get("Order", 0) or 0) for r in rows) + 10

    def _unique_component_id(self, base_id, rows=None):
        source_rows = rows if rows is not None else self._read_rows()
        existing = {str(r.get("Id", "") or "").strip() for r in source_rows}
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

    def _add_component_bundle(self, bundle_key):
        bundle = copy.deepcopy(list(QUICK_COMPONENT_BUNDLES.get(str(bundle_key or "").strip().lower() or "", []) or []))
        if not bundle:
            return
        rows = self._read_rows()
        base_order = min(int(row.get("Order", 0) or 0) for row in bundle)
        next_order = self._next_component_order()
        for row in bundle:
            row["Id"] = self._unique_component_id(row.get("Id", "COMP"), rows=rows)
            rel_order = int(row.get("Order", 0) or 0) - int(base_order or 0)
            row["Order"] = int(next_order + rel_order)
            rows.append(row)
        self._write_rows_to_table(rows)
        self.table.selectRow(max(0, len(rows) - len(bundle)))
        self._schedule_preview()

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
        self._schedule_preview()

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
        linear_unit = str(_units.get_linear_export_unit(self._unit_context()) or "m")
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as fp:
                fp.write(f"# CorridorRoadUnits,linear={linear_unit}\n")
                writer = csv.DictWriter(fp, fieldnames=list(COL_HEADERS))
                writer.writeheader()
                for row in rows:
                    writer.writerow(
                        {
                            "Id": row.get("Id", ""),
                            "Type": row.get("Type", ""),
                            "Shape": row.get("Shape", ""),
                            "Side": row.get("Side", ""),
                            "Width": f"{self._csv_from_meters(row.get('Width', 0.0), linear_unit):.3f}",
                            "CrossSlopePct": f"{float(row.get('CrossSlopePct', 0.0) or 0.0):.3f}",
                            "Height": f"{self._csv_from_meters(row.get('Height', 0.0), linear_unit):.3f}",
                            "ExtraWidth": f"{self._csv_from_meters(row.get('ExtraWidth', 0.0), linear_unit):.3f}",
                            "BackSlopePct": f"{float(row.get('BackSlopePct', 0.0) or 0.0):.3f}",
                            "Offset": f"{self._csv_from_meters(row.get('Offset', 0.0), linear_unit):.3f}",
                            "Order": int(row.get("Order", 0) or 0),
                            "Enabled": "true" if bool(row.get("Enabled", True)) else "false",
                        }
                    )
            self.txt_csv.setText(path)
            self.lbl_status.setText(f"Saved {len(rows)} component rows to CSV. | linear={linear_unit}")
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
        linear_unit = str(_units.get_linear_export_unit(self._unit_context()) or "m")
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as fp:
                fp.write(f"# CorridorRoadUnits,linear={linear_unit}\n")
                writer = csv.DictWriter(fp, fieldnames=list(PAV_HEADERS))
                writer.writeheader()
                for row in rows:
                    writer.writerow(
                        {
                            "Id": row.get("Id", ""),
                            "Type": row.get("Type", ""),
                            "Thickness": f"{self._csv_from_meters(row.get('Thickness', 0.0), linear_unit):.3f}",
                            "Enabled": "true" if bool(row.get("Enabled", True)) else "false",
                        }
                    )
            self.txt_pavement_csv.setText(path)
            self.lbl_status.setText(f"Saved {len(rows)} pavement rows to CSV. | linear={linear_unit}")
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
        self._schedule_preview()

    def _load_pavement_preset(self):
        name = str(self.cmb_pavement_preset.currentText() or "").strip()
        rows = copy.deepcopy(list(PAVEMENT_PRESETS.get(name, []) or []))
        if not rows:
            QtWidgets.QMessageBox.information(None, "Typical Section", "Select a pavement preset first.")
            return
        self._write_pavement_rows_to_table(rows)
        self.lbl_status.setText(f"Loaded pavement preset: {name}")
        self._schedule_preview()

    def _load_csv(self):
        path = self.txt_csv.text().strip()
        if not path:
            QtWidgets.QMessageBox.information(None, "Typical Section", "Select a CSV file first.")
            return
        if not os.path.exists(path):
            QtWidgets.QMessageBox.warning(None, "Typical Section", f"CSV not found:\n{path}")
            return

        try:
            payload = _read_csv_dict_rows(path)
            linear_unit = str((payload.get("metadata", {}) or {}).get("linear_unit", "") or "")
            rows = []
            for i, row_dict in enumerate(list(payload.get("rows", []) or []), start=1):
                if not any(str(v or "").strip() for v in dict(row_dict).values()):
                    continue
                rows.append(
                    {
                        "Id": str(self._find_col(row_dict, ("Id", "ComponentId"), f"COMP-{i:02d}") or f"COMP-{i:02d}").strip(),
                        "Type": str(self._find_col(row_dict, ("Type", "ComponentType"), "lane") or "lane").strip().lower(),
                        "Shape": str(self._find_col(row_dict, ("Shape", "ShapeMode"), "") or "").strip().lower(),
                        "Side": str(self._find_col(row_dict, ("Side",), "left") or "left").strip().lower(),
                        "Width": self._meters_from_csv(self._parse_float(self._find_col(row_dict, ("Width",), 0.0)), linear_unit),
                        "CrossSlopePct": self._parse_float(self._find_col(row_dict, ("CrossSlopePct", "CrossSlope", "SlopePct"), 0.0)),
                        "Height": self._meters_from_csv(self._parse_float(self._find_col(row_dict, ("Height", "StepHeight"), 0.0)), linear_unit),
                        "ExtraWidth": self._meters_from_csv(self._parse_float(self._find_col(row_dict, ("ExtraWidth", "BottomWidth", "FaceWidth", "OuterWidth"), 0.0)), linear_unit),
                        "BackSlopePct": self._parse_float(self._find_col(row_dict, ("BackSlopePct", "OuterSlopePct", "SecondarySlopePct"), 0.0)),
                        "Offset": self._meters_from_csv(self._parse_float(self._find_col(row_dict, ("Offset",), 0.0)), linear_unit),
                        "Order": self._parse_int(self._find_col(row_dict, ("Order", "SortOrder"), i * 10)),
                        "Enabled": str(self._find_col(row_dict, ("Enabled", "Use"), "true")).strip().lower() not in ("0", "false", "no", "off"),
                    }
                )
            if not rows:
                QtWidgets.QMessageBox.warning(None, "Typical Section", "No component rows were found in the CSV.")
                return
            for row in rows:
                if str(row.get("Type", "") or "").strip().lower() == "bench":
                    row["Type"] = "berm"
            self._write_rows_to_table(rows)
            self.lbl_status.setText(f"Loaded {len(rows)} component rows from CSV. | linear={linear_unit or _units.get_linear_import_unit(self._unit_context())}")
            self._schedule_preview()
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
            payload = _read_csv_dict_rows(path)
            linear_unit = str((payload.get("metadata", {}) or {}).get("linear_unit", "") or "")
            rows = []
            for i, row_dict in enumerate(list(payload.get("rows", []) or []), start=1):
                if not any(str(v or "").strip() for v in dict(row_dict).values()):
                    continue
                rows.append(
                    {
                        "Id": str(self._find_col(row_dict, ("Id", "LayerId"), f"LAYER-{i:02d}") or f"LAYER-{i:02d}").strip(),
                        "Type": str(self._find_col(row_dict, ("Type", "LayerType"), "base") or "base").strip().lower(),
                        "Thickness": self._meters_from_csv(self._parse_float(self._find_col(row_dict, ("Thickness", "Depth"), 0.0)), linear_unit),
                        "Enabled": str(self._find_col(row_dict, ("Enabled", "Use"), "true")).strip().lower() not in ("0", "false", "no", "off"),
                    }
                )
            if not rows:
                QtWidgets.QMessageBox.warning(None, "Typical Section", "No pavement rows were found in the CSV.")
                return
            self._write_pavement_rows_to_table(rows)
            self.lbl_status.setText(f"Loaded {len(rows)} pavement rows from CSV. | linear={linear_unit or _units.get_linear_import_unit(self._unit_context())}")
            self._schedule_preview()
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Typical Section", f"Pavement CSV load failed: {ex}")

    def _estimate_top_width(self, rows):
        left = 0.0
        right = 0.0
        center = 0.0
        for row in rows:
            if not bool(row.get("Enabled", True)):
                continue
            side = str(row.get("Side", "") or "").strip().lower()
            width = max(0.0, float(row.get("Width", 0.0) or 0.0))
            extra_width = max(0.0, float(row.get("ExtraWidth", 0.0) or 0.0))
            if str(row.get("Type", "") or "").strip().lower() in ("curb", "berm"):
                width += extra_width
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

    def _component_summary_snapshot(self):
        rows = self._read_rows()
        pav_rows = self._read_pavement_rows()
        enabled_rows = [r for r in rows if bool(r.get("Enabled", True))]
        enabled_pav = [r for r in pav_rows if bool(r.get("Enabled", True))]
        left_rows = [r for r in enabled_rows if str(r.get("Side", "") or "").strip().lower() == "left"]
        right_rows = [r for r in enabled_rows if str(r.get("Side", "") or "").strip().lower() == "right"]
        top_width = self._estimate_top_width(enabled_rows)
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
            self._sync_shape_combo_for_row(row)
            typ = str(self._get_cell_text(row, COMP_COL_TYPE) or "").strip().lower()
            hint = COMPONENT_TYPE_HINTS.get(typ, {})
            row_tip = hint.get("row", "Set component Type, Shape, Side, Width, CrossSlopePct, Height, ExtraWidth, BackSlopePct, Offset, Order, Enabled.")
            highlight = hint.get("highlight", "base")
            for col in range(len(COL_HEADERS)):
                it = self.table.item(row, col)
                if it is not None:
                    it.setToolTip(row_tip)
            for col in (COMP_COL_TYPE, COMP_COL_SHAPE, COMP_COL_SIDE, COMP_COL_ENABLED):
                cmb = self.table.cellWidget(row, col)
                if cmb is not None:
                    cmb.setToolTip(row_tip)
            for col, mode in (
                (COMP_COL_WIDTH, "width"),
                (COMP_COL_SLOPE, "slope"),
                (COMP_COL_HEIGHT, "height"),
                (COMP_COL_EXTRA, "width"),
                (COMP_COL_BACK_SLOPE, "slope"),
                (COMP_COL_OFFSET, "base"),
                (COMP_COL_ORDER, "base"),
            ):
                it = self.table.item(row, col)
                if it is None:
                    continue
                brush_key = mode
                if col == COMP_COL_SLOPE:
                    brush_key = "slope" if highlight == "slope" else "base"
                elif col == COMP_COL_HEIGHT:
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
            self.lbl_summary_width.setText(f"{self._format_display_length(snap['top_width'])} {self._display_unit_label()}")
            self.lbl_summary_edges.setText(f"{snap['left_edge']} / {snap['right_edge']}")
            self.lbl_summary_pavement.setText(
                f"{snap['pav_enabled']} enabled / {snap['pav_count']} total, {self._format_display_length(snap['pav_total'])} {self._display_unit_label()}"
            )
        except Exception:
            self.lbl_summary_components.setText("-")
            self.lbl_summary_width.setText("-")
            self.lbl_summary_edges.setText("-")
            self.lbl_summary_pavement.setText("-")

    def _on_component_combo_changed(self, *_args):
        if self._loading:
            return
        sender = self.form.sender() if hasattr(self.form, "sender") else None
        if sender is None:
            sender = QtWidgets.QApplication.instance().sender()
        try:
            row = int(sender.property("table_row"))
            self._active_component_row = row
            self.table.setCurrentCell(row, 0)
            self.table.selectRow(row)
        except Exception:
            pass
        self._sync_shape_combo_for_row(int(self._active_component_row or 0))
        self._refresh_component_hints()
        self._update_summary()
        self._schedule_preview()

    def _on_pavement_combo_changed(self, *_args):
        if self._loading:
            return
        sender = self.form.sender() if hasattr(self.form, "sender") else None
        if sender is None:
            sender = QtWidgets.QApplication.instance().sender()
        try:
            row = int(sender.property("table_row"))
            self._active_pavement_row = row
            self.pav_table.setCurrentCell(row, 0)
            self.pav_table.selectRow(row)
        except Exception:
            pass
        self._update_summary()
        self._schedule_preview()

    def _on_component_table_changed(self, *_args):
        if self._loading:
            return
        self._refresh_component_hints()
        self._update_summary()

    def _on_pavement_table_changed(self, *_args):
        if self._loading:
            return
        self._update_summary()

    def _on_component_editor_closed(self, _editor, hint):
        if self._loading:
            return
        if int(hint) == int(QtWidgets.QAbstractItemDelegate.NoHint):
            return
        self._schedule_preview(delay_ms=50)

    def _on_pavement_editor_closed(self, _editor, hint):
        if self._loading:
            return
        if int(hint) == int(QtWidgets.QAbstractItemDelegate.NoHint):
            return
        self._schedule_preview(delay_ms=50)

    def _on_component_current_cell_changed(self, current_row, _current_col, _prev_row, _prev_col):
        if self._loading:
            return
        if int(current_row) >= 0:
            self._active_component_row = int(current_row)

    def _on_pavement_current_cell_changed(self, current_row, _current_col, _prev_row, _prev_col):
        if self._loading:
            return
        if int(current_row) >= 0:
            self._active_pavement_row = int(current_row)

    def _sync_preview_controls(self):
        obj = self._current_target()
        pav_disp = self._find_pavement_display(obj) if obj is not None else None
        self._loading = True
        try:
            preview_checked = bool(getattr(obj, "ShowPreviewWire", True)) if obj is not None else True
            pavement_checked = bool(getattr(getattr(pav_disp, "ViewObject", None), "Visibility", True)) if pav_disp is not None else True
            self.chk_show_preview_wire.setChecked(preview_checked)
            self.chk_show_pavement_display.setChecked(pavement_checked)
        finally:
            self._loading = False

    def _on_preview_visibility_changed(self, *_args):
        if self._loading or self.doc is None:
            return
        obj = self._current_target()
        if obj is not None:
            try:
                obj.ShowPreviewWire = bool(self.chk_show_preview_wire.isChecked())
                if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
                    obj.ViewObject.Visibility = bool(self.chk_show_preview_wire.isChecked())
                self._style_typical_preview_display(obj)
                obj.touch()
            except Exception:
                pass
        pav_disp = self._find_pavement_display(obj) if obj is not None else None
        sel_disp = self._find_selection_display(obj) if obj is not None else None
        if pav_disp is not None:
            try:
                if hasattr(pav_disp, "ViewObject") and pav_disp.ViewObject is not None:
                    pav_disp.ViewObject.Visibility = bool(self.chk_show_pavement_display.isChecked())
                pav_disp.touch()
            except Exception:
                pass
        if sel_disp is not None:
            try:
                self._style_selection_display(sel_disp)
                sel_disp.touch()
            except Exception:
                pass
        if obj is not None:
            try:
                self.doc.recompute()
            except Exception:
                pass

    def _schedule_preview(self, delay_ms: int = 250):
        return

    def _sync_panel_to_typical_section(self, obj, pav_disp=None):
        rows = self._read_rows()
        pav_rows = self._read_pavement_rows()
        obj.ShowPreviewWire = bool(self.chk_show_preview_wire.isChecked())
        obj.ComponentIds = [str(r.get("Id", "") or "") for r in rows]
        obj.ComponentTypes = [str(r.get("Type", "") or "") for r in rows]
        obj.ComponentShapes = [str(r.get("Shape", "") or "") for r in rows]
        obj.ComponentSides = [str(r.get("Side", "") or "") for r in rows]
        obj.ComponentWidths = [float(r.get("Width", 0.0) or 0.0) for r in rows]
        obj.ComponentCrossSlopes = [float(r.get("CrossSlopePct", 0.0) or 0.0) for r in rows]
        obj.ComponentHeights = [float(r.get("Height", 0.0) or 0.0) for r in rows]
        obj.ComponentExtraWidths = [float(r.get("ExtraWidth", 0.0) or 0.0) for r in rows]
        obj.ComponentBackSlopes = [float(r.get("BackSlopePct", 0.0) or 0.0) for r in rows]
        obj.ComponentOffsets = [float(r.get("Offset", 0.0) or 0.0) for r in rows]
        obj.ComponentOrders = [int(r.get("Order", 0) or 0) for r in rows]
        obj.ComponentEnabled = [1 if bool(r.get("Enabled", True)) else 0 for r in rows]
        obj.PavementLayerIds = [str(r.get("Id", "") or "") for r in pav_rows]
        obj.PavementLayerTypes = [str(r.get("Type", "") or "") for r in pav_rows]
        obj.PavementLayerThicknesses = [float(r.get("Thickness", 0.0) or 0.0) for r in pav_rows]
        obj.PavementLayerEnabled = [1 if bool(r.get("Enabled", True)) else 0 for r in pav_rows]
        if pav_disp is not None:
            pav_disp.SourceTypicalSection = obj
            if hasattr(pav_disp, "ViewObject") and pav_disp.ViewObject is not None:
                pav_disp.ViewObject.Visibility = bool(self.chk_show_pavement_display.isChecked())
        if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
            obj.ViewObject.Visibility = bool(self.chk_show_preview_wire.isChecked())
        self._style_typical_preview_display(obj)
        return rows, pav_rows

    def _selected_component_preview_index(self):
        row = int(self.table.currentRow())
        if row < 0:
            row = int(self._active_component_row or -1)
        return int(row)

    def _refresh_preview(self):
        if self._loading or self.doc is None:
            return
        try:
            self._remember_component_selection()
            self._remember_pavement_selection()
            obj = self._ensure_target()
            pav_disp = self._ensure_pavement_display(obj)
            sel_disp = self._ensure_selection_display(obj)
            rows, pav_rows = self._sync_panel_to_typical_section(obj, pav_disp=pav_disp)
            obj.PreviewSelectedComponentIndex = -1
            if sel_disp is not None:
                sel_disp.SourceTypicalSection = obj
                sel_disp.SelectedComponentIndex = self._selected_component_preview_index()
                self._style_selection_display(sel_disp)
            if pav_disp is not None:
                pav_disp.touch()
            if sel_disp is not None:
                sel_disp.touch()
            obj.touch()
            self.doc.recompute()
            prj = find_project(self.doc)
            if prj is not None:
                extras = [obj]
                if pav_disp is not None:
                    extras.append(pav_disp)
                if sel_disp is not None:
                    extras.append(sel_disp)
                link_project(prj, links={"TypicalSectionTemplate": obj}, adopt_extra=extras)
            self._templates = _find_typical_section_templates(self.doc)
            self._fill_targets(selected=obj)
            self._restore_component_selection()
            self._restore_pavement_selection()
            self.lbl_status.setText(
                f"Preview updated: {len(rows)} components, {len(pav_rows)} pavement layers"
            )
            self._update_summary()
        except Exception as ex:
            self.lbl_status.setText(f"Preview failed: {ex}")

    def _apply(self):
        if self.doc is None:
            QtWidgets.QMessageBox.warning(None, "Typical Section", "No active document.")
            return
        try:
            obj = self._ensure_target()
            pav_disp = self._ensure_pavement_display(obj)
            sel_disp = self._find_selection_display(obj)
            rows, pav_rows = self._sync_panel_to_typical_section(obj, pav_disp=pav_disp)
            obj.PreviewSelectedComponentIndex = -1
            if pav_disp is not None:
                pav_disp.touch()
            if sel_disp is not None:
                sel_disp.SelectedComponentIndex = -1
                self._style_selection_display(sel_disp)
                sel_disp.touch()
            obj.touch()
            self.doc.recompute()
            prj = find_project(self.doc)
            if prj is not None:
                extras = [obj]
                if pav_disp is not None:
                    extras.append(pav_disp)
                if sel_disp is not None:
                    extras.append(sel_disp)
                link_project(prj, links={"TypicalSectionTemplate": obj}, adopt_extra=extras)
            self._refresh_context()
            self._fill_targets(selected=obj)
            self.lbl_status.setText(str(getattr(obj, "Status", "Updated")))
            QtWidgets.QMessageBox.information(
                None,
                "Typical Section",
                "Typical section template updated.\n"
                f"Components: {len(rows)}\n"
                f"Advanced components: {int(getattr(obj, 'AdvancedComponentCount', 0) or 0)}\n"
                f"Pavement layers: {len(pav_rows)}\n"
                f"Pavement total thickness: {self._format_display_length(getattr(obj, 'PavementTotalThickness', 0.0) or 0.0)} {self._display_unit_label()}",
            )
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Typical Section", f"Apply failed: {ex}")
