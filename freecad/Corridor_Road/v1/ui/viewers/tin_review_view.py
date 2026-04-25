"""TIN review viewer for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD GUI is not available in tests.
    Gui = None

from freecad.Corridor_Road.qt_compat import QtWidgets
from ...services.evaluation import TinSamplingService
from ...services.mapping import enrich_tin_review_preview


class TinReviewViewerTaskPanel:
    """Minimal read-only TIN review panel with one explicit XY probe."""

    def __init__(self, preview: dict[str, object]):
        self.preview = dict(preview or {})
        self.form = self._build_ui()

    def getStandardButtons(self):
        return 0

    def accept(self):
        if Gui is not None:
            Gui.Control.closeDialog()
        return True

    def reject(self):
        if Gui is not None:
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("CorridorRoad v1 - TIN Review")

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("TIN Review")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        summary = QtWidgets.QPlainTextEdit()
        summary.setReadOnly(True)
        summary.setMinimumHeight(135)
        summary.setPlainText(str(self.preview.get("summary_text", "") or ""))
        self._summary_edit = summary
        layout.addWidget(summary)

        layout.addWidget(QtWidgets.QLabel("XY Probe"))
        probe_row = QtWidgets.QHBoxLayout()
        probe = dict(self.preview.get("probe", {}) or {})
        self._probe_x = QtWidgets.QLineEdit(str(probe.get("x", 0.0)))
        self._probe_y = QtWidgets.QLineEdit(str(probe.get("y", 0.0)))
        probe_row.addWidget(QtWidgets.QLabel("X"))
        probe_row.addWidget(self._probe_x)
        probe_row.addWidget(QtWidgets.QLabel("Y"))
        probe_row.addWidget(self._probe_y)
        run_button = QtWidgets.QPushButton("Sample XY")
        run_button.clicked.connect(self._run_probe)
        probe_row.addWidget(run_button)
        layout.addLayout(probe_row)

        self._probe_result_label = QtWidgets.QLabel(self._probe_result_text(self.preview.get("sample_result")))
        self._probe_result_label.setStyleSheet(self._probe_result_style(self.preview.get("sample_result")))
        layout.addWidget(self._probe_result_label)

        layout.addWidget(QtWidgets.QLabel("Quality Diagnostics"))
        layout.addWidget(
            self._table_widget(
                headers=["Kind", "Value", "Unit", "Notes"],
                rows=[
                    [
                        str(getattr(row, "kind", "") or ""),
                        str(getattr(row, "value", "") or ""),
                        str(getattr(row, "unit", "") or ""),
                        str(getattr(row, "notes", "") or ""),
                    ]
                    for row in list(getattr(self.preview.get("tin_surface"), "quality_rows", []) or [])
                ],
                empty_text="No quality rows.",
            )
        )

        layout.addWidget(QtWidgets.QLabel("Provenance"))
        layout.addWidget(
            self._table_widget(
                headers=["Kind", "Source", "Notes"],
                rows=[
                    [
                        str(getattr(row, "source_kind", "") or ""),
                        str(getattr(row, "source_ref", "") or ""),
                        str(getattr(row, "notes", "") or ""),
                    ]
                    for row in list(getattr(self.preview.get("tin_surface"), "provenance_rows", []) or [])
                ],
                empty_text="No provenance rows.",
            )
        )

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        return widget

    def _run_probe(self) -> None:
        surface = self.preview.get("tin_surface")
        try:
            x = float(str(self._probe_x.text() or "0").strip())
            y = float(str(self._probe_y.text() or "0").strip())
        except Exception:
            self._probe_result_label.setText("Probe error: X and Y must be numeric.")
            self._probe_result_label.setStyleSheet(self._probe_error_style())
            return

        result = TinSamplingService().sample_xy(surface=surface, x=x, y=y)
        self.preview["probe"] = {"x": x, "y": y}
        self.preview["sample_result"] = result
        self.preview = enrich_tin_review_preview(self.preview)
        self._summary_edit.setPlainText(str(self.preview.get("summary_text", "") or ""))
        self._probe_result_label.setText(self._probe_result_text(result))
        self._probe_result_label.setStyleSheet(self._probe_result_style(result))

    def _probe_result_text(self, result) -> str:
        if result is None:
            return "Probe result: not sampled."
        status = str(getattr(result, "status", "") or "")
        if bool(getattr(result, "found", False)):
            return (
                "Probe result: "
                f"status={status}, z={float(getattr(result, 'z', 0.0) or 0.0):.3f}, "
                f"face={getattr(result, 'face_id', '') or '(none)'}, "
                f"confidence={float(getattr(result, 'confidence', 0.0) or 0.0):.3f}, "
                f"extent={self.preview.get('probe_extent_status', '') or 'extent_unknown'}"
            )
        guidance = str(self.preview.get("probe_guidance", "") or "").strip()
        suffix = f", guidance={guidance}" if guidance else ""
        return (
            f"Probe result: status={status}, "
            f"extent={self.preview.get('probe_extent_status', '') or 'extent_unknown'}, "
            f"notes={getattr(result, 'notes', '') or ''}{suffix}"
        )

    def _probe_result_style(self, result) -> str:
        if result is None:
            return self._probe_base_style("#243044", "#d7e4ff", "#53657f")
        if bool(getattr(result, "found", False)):
            return self._probe_base_style("#163426", "#d8ffe8", "#3f8f65")
        if str(getattr(result, "status", "") or "") == "error":
            return self._probe_error_style()
        return self._probe_base_style("#3a2f16", "#ffe8a8", "#9a7a2c")

    def _probe_error_style(self) -> str:
        return self._probe_base_style("#3b1f24", "#ffd8df", "#9c4b5a")

    @staticmethod
    def _probe_base_style(background: str, color: str, border: str) -> str:
        return (
            f"color: {color}; "
            f"background: {background}; "
            f"border: 1px solid {border}; "
            "border-radius: 4px; "
            "padding: 6px 8px; "
            "font-weight: bold;"
        )

    def _table_widget(
        self,
        *,
        headers: list[str],
        rows: list[list[str]],
        empty_text: str,
    ):
        if not rows:
            empty = QtWidgets.QLabel(empty_text)
            empty.setStyleSheet("color: #666;")
            return empty

        table = QtWidgets.QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(True)

        for row_index, row_values in enumerate(rows):
            for col_index, value in enumerate(row_values):
                table.setItem(row_index, col_index, QtWidgets.QTableWidgetItem(str(value)))

        header = table.horizontalHeader()
        try:
            header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        except Exception:
            pass
        table.setMinimumHeight(95)
        return table


TinReviewPreviewTaskPanel = TinReviewViewerTaskPanel
