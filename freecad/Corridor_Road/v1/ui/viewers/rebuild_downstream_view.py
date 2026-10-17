"""Rebuild Downstream window for CorridorRoad v1.

Lists each result stage with its freshness and what changed, runs Rebuild Downstream with a
progress bar per stage, and shows the report. The command passes in how to read the freshness and
how to run the rebuild; this window edits no source.
"""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtWidgets

STAGE_COLUMNS = ("Stage", "Status", "Changed inputs")


class V1RebuildDownstreamDialog(QtWidgets.QDialog):
    def __init__(self, document, *, parent=None, freshness_rows, run_rebuild, stage_label):
        super().__init__(parent)
        self.document = document
        self._freshness_rows = freshness_rows
        self._run_rebuild = run_rebuild
        self._stage_label = stage_label
        self.setWindowTitle("Rebuild Downstream")
        self.resize(560, 420)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Stale results are rebuilt in workflow order with the options they were last built with."))
        self._table = QtWidgets.QTableWidget(0, len(STAGE_COLUMNS))
        self._table.setHorizontalHeaderLabels(list(STAGE_COLUMNS))
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table)
        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        layout.addWidget(self._progress)
        self._stage_text = QtWidgets.QLabel("")
        layout.addWidget(self._stage_text)
        self._report = QtWidgets.QPlainTextEdit()
        self._report.setReadOnly(True)
        layout.addWidget(self._report, 1)
        buttons = QtWidgets.QHBoxLayout()
        self._rebuild_button = QtWidgets.QPushButton("Rebuild")
        self._rebuild_button.clicked.connect(self._rebuild)
        buttons.addWidget(self._rebuild_button)
        buttons.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.close)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        self._refresh()

    def _refresh(self) -> None:
        rows = self._freshness_rows(self.document)
        self._table.setRowCount(0)
        for row in rows:
            index = self._table.rowCount()
            self._table.insertRow(index)
            for column, key in enumerate(("stage", "status", "changed")):
                self._table.setItem(index, column, QtWidgets.QTableWidgetItem(str(row[key])))
        self._table.resizeColumnsToContents()
        stale = sum(1 for row in rows if row["status"] == "stale")
        self._stage_text.setText(f"{stale} stale stage(s)." if stale else "Every built result is current.")

    def _on_progress(self, done: int, total: int, stage: str) -> None:
        self._progress.setRange(0, max(total, 1))
        self._progress.setValue(done)
        self._stage_text.setText("Done." if done >= total else f"Rebuilding {self._stage_label(stage)} ({done + 1}/{total})...")
        # let the window repaint between stages; the stages themselves run on this thread
        QtWidgets.QApplication.processEvents()

    def _rebuild(self) -> None:
        self._rebuild_button.setEnabled(False)
        self._report.clear()
        try:
            report = self._run_rebuild(self.document, self._on_progress)
            self._report.setPlainText(("Rebuild stopped at a failing stage.\n" if report.failed else "") + report.text)
        except RuntimeError as exc:
            self._report.setPlainText(f"Rebuild Downstream did not run: {exc}")
        finally:
            self._rebuild_button.setEnabled(True)
            self._refresh()
