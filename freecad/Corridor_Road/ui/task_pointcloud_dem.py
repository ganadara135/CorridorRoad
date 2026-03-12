import os

import FreeCAD as App
import FreeCADGui as Gui
from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_project
from freecad.Corridor_Road.objects.obj_pointcloud_dem import (
    PointCloudDEM,
    ViewProviderPointCloudDEM,
    ensure_pointcloud_dem_properties,
)
from freecad.Corridor_Road.objects.obj_project import get_length_scale
from freecad.Corridor_Road.objects.project_links import link_project
from freecad.Corridor_Road.ui.common.coord_ui import coord_hint_text


def _find_pointcloud_dem(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        try:
            if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "PointCloudDEM":
                return o
        except Exception:
            pass
        if o.Name.startswith("PointCloudDEM"):
            return o
    return None


class PointCloudDEMTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._scale = get_length_scale(self.doc, default=1.0)
        self._project = None
        self._loading = False
        self._running = False
        self._cancel_requested = False
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
        w.setWindowTitle("CorridorRoad - Import PointCloud DEM")

        main = QtWidgets.QVBoxLayout(w)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        main.addWidget(self.lbl_info)

        gb_src = QtWidgets.QGroupBox("CSV Source")
        fs = QtWidgets.QFormLayout(gb_src)

        row_csv = QtWidgets.QHBoxLayout()
        self.ed_csv = QtWidgets.QLineEdit()
        self.ed_csv.setPlaceholderText("Path to point cloud CSV (UTM E/N/Z)")
        self.btn_browse = QtWidgets.QPushButton("Browse CSV")
        row_csv.addWidget(self.ed_csv, 1)
        row_csv.addWidget(self.btn_browse)
        w_csv = QtWidgets.QWidget()
        w_csv.setLayout(row_csv)

        self.cmb_coords = QtWidgets.QComboBox()
        self.cmb_coords.addItems(["World", "Local"])
        self.cmb_out_coords = QtWidgets.QComboBox()
        self.cmb_out_coords.addItems(["Local", "World"])
        self.cmb_delim = QtWidgets.QComboBox()
        self.cmb_delim.addItems(["Auto", "Comma", "Semicolon", "Tab", "Pipe"])
        self.chk_header = QtWidgets.QCheckBox("CSV has header row")
        self.chk_header.setChecked(True)
        self.lbl_coord_hint = QtWidgets.QLabel("")
        self.lbl_coord_hint.setWordWrap(True)
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")

        fs.addRow("CSV File:", w_csv)
        fs.addRow("Input Coords:", self.cmb_coords)
        fs.addRow("Output Mesh Coords:", self.cmb_out_coords)
        fs.addRow("Delimiter:", self.cmb_delim)
        fs.addRow(self.chk_header)
        fs.addRow("Coordinate Setup:", self.lbl_coord_hint)
        fs.addRow(self.btn_refresh)
        main.addWidget(gb_src)

        gb_dem = QtWidgets.QGroupBox("DEM Options")
        form_dem = QtWidgets.QFormLayout(gb_dem)
        self.spin_cell = QtWidgets.QDoubleSpinBox()
        self.spin_cell.setRange(0.2 * self._scale, 10000.0 * self._scale)
        self.spin_cell.setDecimals(3)
        self.spin_cell.setValue(1.0 * self._scale)
        self.cmb_agg = QtWidgets.QComboBox()
        self.cmb_agg.addItems(["Mean", "Median", "Min", "Max"])
        self.spin_max_cells = QtWidgets.QSpinBox()
        self.spin_max_cells.setRange(1000, 2000000000)
        self.spin_max_cells.setValue(2000000)
        self.chk_auto = QtWidgets.QCheckBox("Auto update on parameter changes")
        self.chk_auto.setChecked(True)
        form_dem.addRow("Cell Size (scaled):", self.spin_cell)
        form_dem.addRow("Aggregation:", self.cmb_agg)
        form_dem.addRow("Max Cells:", self.spin_max_cells)
        form_dem.addRow(self.chk_auto)
        main.addWidget(gb_dem)

        self.btn_build = QtWidgets.QPushButton("Import CSV and Build DEM")
        main.addWidget(self.btn_build)

        gb_run = QtWidgets.QGroupBox("Run")
        fr = QtWidgets.QFormLayout(gb_run)
        self.lbl_run = QtWidgets.QLabel("Idle")
        self.pbar = QtWidgets.QProgressBar()
        self.pbar.setRange(0, 100)
        self.pbar.setValue(0)
        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        fr.addRow("Status:", self.lbl_run)
        fr.addRow("Progress:", self.pbar)
        fr.addRow(self.btn_cancel)
        main.addWidget(gb_run)

        self.btn_browse.clicked.connect(self._on_browse)
        self.btn_refresh.clicked.connect(self._refresh_context)
        self.btn_build.clicked.connect(self._build)
        self.btn_cancel.clicked.connect(self._request_cancel)
        self.cmb_coords.currentIndexChanged.connect(self._update_coord_hint)
        return w

    def _coord_context_obj(self):
        if self._project is not None:
            return self._project
        return self.doc

    def _update_coord_hint(self, *_args):
        self.lbl_coord_hint.setText(coord_hint_text(self._coord_context_obj()))

    def _refresh_context(self):
        if self.doc is None:
            self.lbl_info.setText("No active document.")
            return
        self._project = find_project(self.doc)
        obj = _find_pointcloud_dem(self.doc)
        self._update_coord_hint()

        if obj is not None:
            try:
                ensure_pointcloud_dem_properties(obj)
            except Exception:
                pass
            self._loading = True
            try:
                self.ed_csv.setText(str(getattr(obj, "CsvPath", "") or ""))
                self.cmb_coords.setCurrentText(str(getattr(obj, "InputCoords", "World") or "World"))
                self.cmb_out_coords.setCurrentText(str(getattr(obj, "OutputCoords", "Local") or "Local"))
                self.cmb_delim.setCurrentText(str(getattr(obj, "Delimiter", "Auto") or "Auto"))
                self.chk_header.setChecked(bool(getattr(obj, "HasHeader", True)))
                self.spin_cell.setValue(float(getattr(obj, "CellSize", 1.0 * self._scale)))
                self.cmb_agg.setCurrentText(str(getattr(obj, "Aggregation", "Mean") or "Mean"))
                self.spin_max_cells.setValue(int(getattr(obj, "MaxCells", 2000000)))
                self.chk_auto.setChecked(bool(getattr(obj, "AutoUpdate", True)))
            finally:
                self._loading = False

            self.lbl_info.setText(
                "\n".join(
                    [
                        "PointCloudDEM object: FOUND (will update)",
                        f"Last status: {str(getattr(obj, 'Status', '') or '')}",
                    ]
                )
            )
        else:
            self.lbl_info.setText("PointCloudDEM object: NOT FOUND (will create)")

    def _on_browse(self):
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select point cloud CSV",
            str(self.ed_csv.text() or ""),
            "CSV Files (*.csv *.txt);;All Files (*.*)",
        )
        if path:
            self.ed_csv.setText(str(path))

    def _create_or_get_dem(self):
        obj = _find_pointcloud_dem(self.doc)
        if obj is not None:
            try:
                ensure_pointcloud_dem_properties(obj)
            except Exception:
                pass
            return obj

        obj = self.doc.addObject("Mesh::FeaturePython", "PointCloudDEM")
        PointCloudDEM(obj)
        ViewProviderPointCloudDEM(obj.ViewObject)
        obj.Label = "Point Cloud DEM Terrain"
        return obj

    def _build(self):
        if bool(getattr(self, "_running", False)):
            QtWidgets.QMessageBox.information(None, "PointCloud DEM", "Already running.")
            return
        if self.doc is None:
            return

        csv_path = str(self.ed_csv.text() or "").strip()
        if not csv_path:
            QtWidgets.QMessageBox.warning(None, "PointCloud DEM", "CSV file path is empty.")
            return
        if not os.path.isfile(csv_path):
            QtWidgets.QMessageBox.warning(None, "PointCloud DEM", f"CSV file not found:\n{csv_path}")
            return

        dem = self._create_or_get_dem()
        proxy = getattr(dem, "Proxy", None)
        self._running = True
        self._cancel_requested = False
        self.btn_cancel.setEnabled(True)
        self.btn_build.setEnabled(False)
        self.lbl_run.setText("Running")
        self.pbar.setValue(0)

        if proxy is not None:
            try:
                proxy._progress_cb = self._on_progress
            except Exception:
                pass

        try:
            if proxy is not None and hasattr(proxy, "_bulk_updating"):
                proxy._bulk_updating = True

            dem.CsvPath = csv_path
            dem.InputCoords = str(self.cmb_coords.currentText() or "World")
            dem.OutputCoords = str(self.cmb_out_coords.currentText() or "Local")
            dem.Delimiter = str(self.cmb_delim.currentText() or "Auto")
            dem.HasHeader = bool(self.chk_header.isChecked())
            dem.CellSize = float(self.spin_cell.value())
            dem.Aggregation = str(self.cmb_agg.currentText() or "Mean")
            dem.MaxCells = int(self.spin_max_cells.value())
            dem.AutoUpdate = bool(self.chk_auto.isChecked())
            dem.RebuildNow = True
        finally:
            if proxy is not None and hasattr(proxy, "_bulk_updating"):
                proxy._bulk_updating = False

        prj = find_project(self.doc)
        if prj is not None:
            link_project(
                prj,
                links={
                    "Terrain": dem,
                },
                adopt_extra=[dem],
            )

        dem.touch()
        try:
            if proxy is not None:
                proxy.execute(dem)
                try:
                    dem.purgeTouched()
                except Exception:
                    pass
            else:
                self.doc.recompute()
        finally:
            if proxy is not None:
                try:
                    proxy._progress_cb = None
                except Exception:
                    pass
            self._running = False
            self.btn_cancel.setEnabled(False)
            self.btn_build.setEnabled(True)

        status = str(getattr(dem, "Status", "Done"))
        self.lbl_run.setText(status)
        if not (status.startswith("ERROR") or status.startswith("CANCELED")):
            self.pbar.setValue(100)

        msg = [
            status,
            f"CSV: {str(getattr(dem, 'CsvPath', '') or '')}",
            f"Coords: {str(getattr(dem, 'InputCoords', 'World') or 'World')}",
            f"OutputCoords: {str(getattr(dem, 'OutputCoords', 'Local') or 'Local')}",
            f"CellSize: {float(getattr(dem, 'CellSize', 0.0)):.3f} (scaled)",
            f"Aggregation: {str(getattr(dem, 'Aggregation', 'Mean') or 'Mean')}",
            f"Points used/raw: {int(getattr(dem, 'PointCountUsed', 0))} / {int(getattr(dem, 'PointCountRaw', 0))}",
            f"Skipped rows: {int(getattr(dem, 'SkippedRows', 0))}",
            f"Grid: {int(getattr(dem, 'GridNX', 0))} x {int(getattr(dem, 'GridNY', 0))}, NoData: {int(getattr(dem, 'NoDataCount', 0))}",
            f"Z range: {float(getattr(dem, 'ZMin', 0.0)):.3f} .. {float(getattr(dem, 'ZMax', 0.0)):.3f}",
        ]
        QtWidgets.QMessageBox.information(None, "PointCloud DEM", "\n".join(msg))

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass
        self._refresh_context()

    def _request_cancel(self):
        self._cancel_requested = True
        self.lbl_run.setText("Cancel requested...")

    def _on_progress(self, pct, message):
        try:
            self.pbar.setValue(int(max(0.0, min(100.0, float(pct)))))
        except Exception:
            pass
        try:
            self.lbl_run.setText(str(message or "Running"))
        except Exception:
            pass
        try:
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass
        return bool(self._cancel_requested)
