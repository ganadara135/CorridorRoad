import csv
import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_all, find_project
from freecad.Corridor_Road.objects.obj_typical_section_template import (
    ALLOWED_COMPONENT_SIDES,
    ALLOWED_COMPONENT_TYPES,
    TypicalSectionTemplate,
    ViewProviderTypicalSectionTemplate,
    component_rows,
    ensure_typical_section_template_properties,
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


def _find_typical_section_templates(doc):
    return find_all(doc, proxy_type="TypicalSectionTemplate", name_prefixes=("TypicalSectionTemplate",))


class TypicalSectionEditorTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._templates = []
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
        csv_row = QtWidgets.QHBoxLayout()
        self.txt_csv = QtWidgets.QLineEdit()
        self.txt_csv.setPlaceholderText("Path to typical section CSV")
        self.btn_browse_csv = QtWidgets.QPushButton("Browse CSV")
        self.btn_load_csv = QtWidgets.QPushButton("Load CSV")
        csv_row.addWidget(self.txt_csv, 1)
        csv_row.addWidget(self.btn_browse_csv)
        csv_row.addWidget(self.btn_load_csv)
        csv_wrap = QtWidgets.QWidget()
        csv_wrap.setLayout(csv_row)
        fs.addRow("Component CSV:", csv_wrap)
        main.addWidget(gb_target)

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
        self.btn_sort = QtWidgets.QPushButton("Sort by Order")
        row_btns.addWidget(self.btn_add)
        row_btns.addWidget(self.btn_remove)
        row_btns.addWidget(self.btn_sort)
        main.addLayout(row_btns)

        gb_status = QtWidgets.QGroupBox("Status")
        fr = QtWidgets.QFormLayout(gb_status)
        self.lbl_status = QtWidgets.QLabel("Idle")
        self.lbl_status.setWordWrap(True)
        fr.addRow("Status:", self.lbl_status)
        main.addWidget(gb_status)

        bottom = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("Apply")
        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_close = QtWidgets.QPushButton("Close")
        bottom.addWidget(self.btn_apply)
        bottom.addWidget(self.btn_refresh)
        bottom.addWidget(self.btn_close)
        main.addLayout(bottom)

        self.cmb_target.currentIndexChanged.connect(self._on_target_changed)
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_sort.clicked.connect(self._sort_rows)
        self.btn_browse_csv.clicked.connect(self._browse_csv)
        self.btn_load_csv.clicked.connect(self._load_csv)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_refresh.clicked.connect(self._refresh_context)
        self.btn_close.clicked.connect(self.reject)

        self._set_rows(4)
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

    def _on_target_changed(self):
        if self._loading:
            return
        obj = self._current_target()
        if obj is None:
            self._loading = True
            try:
                self.table.setRowCount(0)
                self._set_rows(4)
                self.lbl_status.setText("New TypicalSectionTemplate will be created.")
            finally:
                self._loading = False
            return

        ensure_typical_section_template_properties(obj)
        rows = component_rows(obj)
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
            self.lbl_status.setText(str(getattr(obj, "Status", "Loaded")))
        finally:
            self._loading = False

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
                self.table.setCellWidget(row, col, cmb)

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

    def _get_cell_text(self, r, c):
        cmb = self.table.cellWidget(r, c)
        if cmb is not None and c in (1, 2, 8):
            return str(cmb.currentText() or "")
        it = self.table.item(r, c)
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

    def _remove_row(self):
        r = self.table.currentRow()
        if r < 0:
            r = self.table.rowCount() - 1
        if r >= 0:
            self.table.removeRow(r)

    def _sort_rows(self):
        rows = self._read_rows()
        rows.sort(key=lambda row: (int(row.get("Order", 0) or 0), str(row.get("Side", "")), str(row.get("Id", ""))))
        self._write_rows_to_table(rows)

    def _browse_csv(self):
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select Typical Section CSV",
            self.txt_csv.text().strip() or "",
            "CSV Files (*.csv);;All Files (*.*)",
        )
        if path:
            self.txt_csv.setText(path)

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

    def _apply(self):
        if self.doc is None:
            QtWidgets.QMessageBox.warning(None, "Typical Section", "No active document.")
            return
        try:
            obj = self._ensure_target()
            rows = self._read_rows()
            obj.ComponentIds = [str(r.get("Id", "") or "") for r in rows]
            obj.ComponentTypes = [str(r.get("Type", "") or "") for r in rows]
            obj.ComponentSides = [str(r.get("Side", "") or "") for r in rows]
            obj.ComponentWidths = [float(r.get("Width", 0.0) or 0.0) for r in rows]
            obj.ComponentCrossSlopes = [float(r.get("CrossSlopePct", 0.0) or 0.0) for r in rows]
            obj.ComponentHeights = [float(r.get("Height", 0.0) or 0.0) for r in rows]
            obj.ComponentOffsets = [float(r.get("Offset", 0.0) or 0.0) for r in rows]
            obj.ComponentOrders = [int(r.get("Order", 0) or 0) for r in rows]
            obj.ComponentEnabled = [1 if bool(r.get("Enabled", True)) else 0 for r in rows]
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
                f"Components: {len(rows)}",
            )
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Typical Section", f"Apply failed: {ex}")
