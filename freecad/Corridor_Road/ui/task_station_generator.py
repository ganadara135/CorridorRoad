# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui
from freecad.Corridor_Road.qt_compat import QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_all, find_project
from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.obj_stationing import Stationing, ViewProviderStationing
from freecad.Corridor_Road.objects.project_links import link_project


def _find_alignments(doc):
    return find_all(doc, proxy_type="HorizontalAlignment", name_prefixes=("HorizontalAlignment",))


def _find_stationings(doc):
    return find_all(doc, proxy_type="Stationing", name_prefixes=("Stationing",))


class StationGeneratorTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._alignments = []
        self._stationings = []
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
        w.setWindowTitle("CorridorRoad - Stations")

        main = QtWidgets.QVBoxLayout(w)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        main.addWidget(self.lbl_info)

        gb_src = QtWidgets.QGroupBox("Source")
        fs = QtWidgets.QFormLayout(gb_src)
        self.cmb_alignment = QtWidgets.QComboBox()
        self.cmb_target = QtWidgets.QComboBox()
        self.btn_refresh = QtWidgets.QPushButton("Refresh Context")
        fs.addRow("Alignment:", self.cmb_alignment)
        fs.addRow("Target Stationing:", self.cmb_target)
        fs.addRow(self.btn_refresh)
        main.addWidget(gb_src)

        gb_opt = QtWidgets.QGroupBox("Options")
        form_opts = QtWidgets.QFormLayout(gb_opt)
        self.spin_interval = QtWidgets.QDoubleSpinBox()
        self.spin_interval.setRange(0.001, 1000000000.0)
        self.spin_interval.setDecimals(3)
        self.spin_tick = QtWidgets.QDoubleSpinBox()
        self.spin_tick.setRange(0.001, 100000000.0)
        self.spin_tick.setDecimals(3)
        self.chk_show_ticks = QtWidgets.QCheckBox("Show ticks")
        self.chk_show_ticks.setChecked(True)
        form_opts.addRow("Interval:", self.spin_interval)
        form_opts.addRow("Tick Length:", self.spin_tick)
        form_opts.addRow(self.chk_show_ticks)
        main.addWidget(gb_opt)

        row_btn = QtWidgets.QHBoxLayout()
        self.btn_generate = QtWidgets.QPushButton("Generate Stations")
        self.btn_close = QtWidgets.QPushButton("Close")
        row_btn.addWidget(self.btn_generate)
        row_btn.addWidget(self.btn_close)
        main.addLayout(row_btn)

        gb_run = QtWidgets.QGroupBox("Run")
        fr = QtWidgets.QFormLayout(gb_run)
        self.lbl_status = QtWidgets.QLabel("Idle")
        self.lbl_status.setWordWrap(True)
        fr.addRow("Status:", self.lbl_status)
        main.addWidget(gb_run)

        self.btn_refresh.clicked.connect(self._refresh_context)
        self.cmb_target.currentIndexChanged.connect(self._on_target_changed)
        self.btn_generate.clicked.connect(self._generate)
        self.btn_close.clicked.connect(self.reject)
        self._apply_display_unit_ui()
        return w

    def _display_unit(self) -> str:
        return _units.get_linear_display_unit(self.doc)

    def _apply_display_unit_ui(self):
        unit = self._display_unit()
        suffix = f" {unit}"
        self.spin_interval.setSuffix(suffix)
        self.spin_tick.setSuffix(suffix)

    def _display_from_meters(self, value: float) -> float:
        return _units.user_length_from_meters(self.doc, value, use_default="display")

    def _meters_from_display(self, value: float) -> float:
        return _units.meters_from_user_length(self.doc, value, use_default="display")

    def _format_display_value(self, value: float, digits: int = 3) -> str:
        return f"{float(value):.{int(digits)}f} {self._display_unit()}"

    def _status_summary_text(self, prefix: str) -> str:
        return (
            f"{prefix} | Display unit: {self._display_unit()} | "
            f"Interval={self._format_display_value(self.spin_interval.value())}, "
            f"tick={self._format_display_value(self.spin_tick.value())}"
        )

    @staticmethod
    def _fmt_obj(prefix: str, obj):
        return f"[{prefix}] {obj.Label} ({obj.Name})"

    def _fill_alignments(self, selected=None):
        self.cmb_alignment.clear()
        for o in self._alignments:
            self.cmb_alignment.addItem(self._fmt_obj("Alignment", o))
        if not self._alignments:
            return
        idx = 0
        if selected is not None:
            for i, o in enumerate(self._alignments):
                if o == selected:
                    idx = i
                    break
        self.cmb_alignment.setCurrentIndex(idx)

    def _fill_targets(self, selected=None):
        self.cmb_target.clear()
        self.cmb_target.addItem("[New] Create new Stationing")
        for o in self._stationings:
            self.cmb_target.addItem(self._fmt_obj("Stationing", o))
        idx = 0
        if selected is not None:
            for i, o in enumerate(self._stationings):
                if o == selected:
                    idx = i + 1
                    break
        self.cmb_target.setCurrentIndex(idx)

    def _current_alignment(self):
        i = int(self.cmb_alignment.currentIndex())
        if i < 0 or i >= len(self._alignments):
            return None
        return self._alignments[i]

    def _current_target(self):
        i = int(self.cmb_target.currentIndex())
        if i <= 0:
            return None
        j = i - 1
        if j < 0 or j >= len(self._stationings):
            return None
        return self._stationings[j]

    def _refresh_context(self):
        if self.doc is None:
            self.lbl_info.setText("No active document.")
            return
        self._apply_display_unit_ui()

        self._loading = True
        try:
            self._alignments = _find_alignments(self.doc)
            self._stationings = _find_stationings(self.doc)

            prj = find_project(self.doc)
            sel_aln = getattr(prj, "Alignment", None) if prj is not None else None
            sel_st = getattr(prj, "Stationing", None) if prj is not None else None

            self._fill_alignments(selected=sel_aln)
            self._fill_targets(selected=sel_st)
            self.lbl_info.setText(
                f"Alignment: {len(self._alignments)} found, Stationing: {len(self._stationings)} found.\n"
                f"Display unit: {self._display_unit()} | Interval/Tick inputs use the active display unit and save back to meter-native storage."
            )
        finally:
            self._loading = False
        self._on_target_changed()

    def _on_target_changed(self):
        if self._loading:
            return
        st = self._current_target()
        if st is None:
            self.spin_interval.setValue(_units.user_length_from_meters(self.doc, 20.0))
            self.spin_tick.setValue(_units.user_length_from_meters(self.doc, 2.0))
            self.chk_show_ticks.setChecked(True)
            self.lbl_status.setText(self._status_summary_text("New stationing will be created"))
            return

        try:
            self.spin_interval.setValue(self._display_from_meters(float(getattr(st, "Interval", 20.0))))
        except Exception:
            self.spin_interval.setValue(_units.user_length_from_meters(self.doc, 20.0))
        try:
            self.spin_tick.setValue(self._display_from_meters(float(getattr(st, "TickLength", 2.0))))
        except Exception:
            self.spin_tick.setValue(_units.user_length_from_meters(self.doc, 2.0))
        self.chk_show_ticks.setChecked(bool(getattr(st, "ShowTicks", True)))
        self.lbl_status.setText(self._status_summary_text("Ready"))

    def _ensure_target_stationing(self):
        st = self._current_target()
        if st is not None:
            return st
        st = self.doc.addObject("Part::FeaturePython", "Stationing")
        Stationing(st)
        if getattr(st, "ViewObject", None) is not None:
            ViewProviderStationing(st.ViewObject)
        st.Label = "Stations"
        return st

    def _generate(self):
        if self.doc is None:
            QtWidgets.QMessageBox.warning(None, "Stations", "No active document.")
            return

        aln = self._current_alignment()
        if aln is None:
            QtWidgets.QMessageBox.warning(
                None,
                "Stations",
                "No HorizontalAlignment found. Run Sample Alignment first.",
            )
            return

        try:
            st = self._ensure_target_stationing()
            st.Alignment = aln
            st.Interval = float(self._meters_from_display(self.spin_interval.value()))
            st.TickLength = float(self._meters_from_display(self.spin_tick.value()))
            st.ShowTicks = bool(self.chk_show_ticks.isChecked())
            st.touch()

            prj = find_project(self.doc)
            if prj is not None:
                link_project(
                    prj,
                    links={"Stationing": st},
                    links_if_empty={"Alignment": aln},
                    adopt_extra=[st],
                )

            self.doc.recompute()
            n = len(list(getattr(st, "StationValues", []) or []))
            self.lbl_status.setText(self._status_summary_text(f"OK: {n} stations"))
            QtWidgets.QMessageBox.information(
                None,
                "Stations",
                "Station generation completed.\n"
                f"Generated stations: {n}\n"
                f"Display unit: {self._display_unit()}\n"
                f"Interval: {self._format_display_value(self.spin_interval.value())}\n"
                f"Tick: {self._format_display_value(self.spin_tick.value())}",
            )
            self._refresh_context()
            try:
                Gui.ActiveDocument.ActiveView.fitAll()
            except Exception:
                pass
        except Exception as ex:
            self.lbl_status.setText(f"ERROR: {ex}")
