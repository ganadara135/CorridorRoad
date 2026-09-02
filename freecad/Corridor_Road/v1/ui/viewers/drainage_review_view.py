"""Drainage review presentation for CorridorRoad v1."""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtWidgets


def configure_drainage_review_task_panel_runtime(bindings) -> None:
    """Bind command/controller collaborators without importing the command module."""

    protected = {
        "V1DrainageReviewTaskPanel",
        "configure_drainage_review_task_panel_runtime",
    }
    for name, value in dict(bindings or {}).items():
        if name.startswith("__") or name in protected:
            continue
        globals()[name] = value


# Explicit runtime collaborators are replaced by the command callback map.
App = None
Gui = None
_drainage_review_navigation_targets = None
_filter_flow_route_rows_with_indices = None
_filter_pipeline_candidate_rows_with_indices = None
_filter_region_assignment_rows = None
_gui_available = None
_open_drainage_review_navigation_target = None
_populate_applied_table = None
_populate_element_table = None
_populate_flow_route_issue_table = None
_populate_flow_route_table = None
_populate_flowline_table = None
_populate_pipeline_junction_table = None
_populate_pipeline_network_table = None
_populate_pipeline_segment_table = None
_populate_pipeline_table = None
_populate_region_table = None
_populate_report_table = None
_populate_summary_table = None
_status_text = None
_table = None
apply_clickable_tab_style = None
build_drainage_review_output = None
show_drainage_flow_route_issue_preview_object = None
show_drainage_pipeline_candidate_preview_object = None
show_drainage_pipeline_network_preview_object = None
show_drainage_pipeline_segment_preview_object = None


class V1DrainageReviewTaskPanel:
    """Read-only review panel for Drainage source and resolved section context."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.output = None
        self._report_rows = []
        self._flow_route_rows = []
        self._flow_route_display_indices = []
        self._pipeline_candidate_rows = []
        self._pipeline_candidate_display_indices = []
        self._region_assignment_rows = []
        self.form = self._build_ui()
        self.refresh()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self.reject()

    def reject(self):
        if _gui_available():
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("ParametricRoad v1 - Drainage Review")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Drainage Review")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        self._summary_table = _table(["Metric", "Value", "Unit"])
        self._summary_table.setMaximumHeight(150)
        layout.addWidget(self._summary_table)

        self._tabs = QtWidgets.QTabWidget()
        apply_clickable_tab_style(self._tabs, "DrainageReviewTabs")
        self._element_table = _table(["Kind", "Label", "Start STA", "End STA", "Source", "Notes"])
        self._flow_route_table = _table(["Flow Route", "From", "To", "Outlet", "Risk", "Chain", "Notes"])
        self._flow_route_table.itemDoubleClicked.connect(lambda item: self._show_flow_route_issue(item.row()))
        self._flow_route_issue_table = _table(["Issue", "Severity", "Flow Route(s)", "From Element", "Outlet(s)", "Start STA", "End STA", "Message"])
        self._flow_route_issue_table.itemDoubleClicked.connect(lambda item: self._show_flow_route_issue_marker(item.row()))
        self._pipeline_table = _table(["Flow Route", "Status", "From CP", "To CP", "Start STA", "End STA", "Shape", "Diameter", "Notes"])
        self._pipeline_table.itemDoubleClicked.connect(lambda item: self._show_pipeline_candidate(item.row()))
        self._pipeline_segment_table = _table(["Segment", "Flow Route", "From CP", "To CP", "Start STA", "End STA", "Invert", "Shape", "Diameter", "Notes"])
        self._pipeline_segment_table.itemDoubleClicked.connect(lambda item: self._show_pipeline_segment(item.row()))
        self._pipeline_network_table = _table(["Network", "Segments", "Flow Routes", "Junctions", "Length", "Volume", "Status", "Notes"])
        self._pipeline_network_table.itemDoubleClicked.connect(lambda item: self._show_pipeline_network(item.row()))
        self._pipeline_junction_table = _table(["Kind", "Degree", "Point", "Structures", "Segments", "Flow Routes", "Mode", "Status", "Notes"])
        self._region_table = _table(["Region", "Element", "Start STA", "End STA", "Status", "Notes"])
        self._applied_table = _table(["Station", "Section", "Ditch Points", "Drainage Refs", "Notes"])
        self._flowline_table = _table(["Status", "Source", "Start STA", "End STA", "Fall", "Grade", "From Point", "To Point", "Notes"])
        self._report_table = _table(["Report", "Source", "Value", "Unit", "Family/Policy", "Refs", "Notes"])
        self._tabs.addTab(self._element_table, "Elements")
        self._tabs.addTab(self._flow_route_table, "Flow Routes")
        self._tabs.addTab(self._flow_route_issue_table, "Flow Route Issues")
        self._tabs.addTab(self._pipeline_table, "Pipeline Candidates")
        self._tabs.addTab(self._pipeline_segment_table, "Pipeline Segments")
        self._tabs.addTab(self._pipeline_network_table, "Pipeline Networks")
        self._tabs.addTab(self._pipeline_junction_table, "Pipeline Junctions")
        self._tabs.addTab(self._region_table, "Region Assignments")
        self._tabs.addTab(self._applied_table, "Applied Sections")
        self._tabs.addTab(self._flowline_table, "Flowline Continuity")
        self._tabs.addTab(self._report_table, "Reports")
        layout.addWidget(self._tabs, 1)

        review_filter_row = QtWidgets.QHBoxLayout()
        review_filter_row.addWidget(QtWidgets.QLabel("Flow Routes:"))
        self._flow_route_filter = QtWidgets.QComboBox()
        self._flow_route_filter.addItems(["All", "Pipe-producing", "Capture-only", "Unresolved"])
        self._flow_route_filter.currentIndexChanged.connect(lambda _index: self._populate_flow_routes())
        review_filter_row.addWidget(self._flow_route_filter)
        review_filter_row.addWidget(QtWidgets.QLabel("Pipeline Candidates:"))
        self._pipeline_candidate_filter = QtWidgets.QComboBox()
        self._pipeline_candidate_filter.addItems(["All", "Pipe-producing", "Capture-only", "Unresolved"])
        self._pipeline_candidate_filter.currentIndexChanged.connect(lambda _index: self._populate_pipeline_candidates())
        review_filter_row.addWidget(self._pipeline_candidate_filter)
        self._region_issues_only = QtWidgets.QCheckBox("Region issues only")
        self._region_issues_only.stateChanged.connect(lambda _state: self._populate_region_assignments())
        review_filter_row.addWidget(self._region_issues_only)
        review_filter_row.addStretch(1)
        layout.addLayout(review_filter_row)

        report_filter_row = QtWidgets.QHBoxLayout()
        report_filter_row.addWidget(QtWidgets.QLabel("Reports:"))
        self._report_warnings_only = QtWidgets.QCheckBox("Warnings only")
        self._report_warnings_only.stateChanged.connect(lambda _state: self._populate_reports())
        report_filter_row.addWidget(self._report_warnings_only)
        report_filter_row.addStretch(1)
        layout.addLayout(report_filter_row)

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setFixedHeight(80)
        layout.addWidget(self._status)

        action_row = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)
        action_row.addWidget(refresh_button)
        show_pipeline_button = QtWidgets.QPushButton("Show Pipeline Candidate")
        show_pipeline_button.clicked.connect(self._show_selected_pipeline_candidate)
        action_row.addWidget(show_pipeline_button)
        show_segment_button = QtWidgets.QPushButton("Show Pipeline Segment")
        show_segment_button.clicked.connect(self._show_selected_pipeline_segment)
        action_row.addWidget(show_segment_button)
        show_network_button = QtWidgets.QPushButton("Show Pipeline Network")
        show_network_button.clicked.connect(self._show_selected_pipeline_network)
        action_row.addWidget(show_network_button)
        action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        action_row.addWidget(close_button)
        layout.addLayout(action_row)

        navigation_row = QtWidgets.QHBoxLayout()
        navigation_row.addWidget(QtWidgets.QLabel("Open:"))
        for target, label in _drainage_review_navigation_targets():
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(lambda _checked=False, target=target: self._open_related_panel(target))
            navigation_row.addWidget(button)
        navigation_row.addStretch(1)
        layout.addLayout(navigation_row)
        return widget

    def refresh(self) -> None:
        self.output = build_drainage_review_output(self.document)
        _populate_summary_table(self._summary_table, self.output.summary_rows)
        _populate_element_table(self._element_table, [row for row in self.output.element_rows if row.kind == "drainage_element"])
        self._flow_route_rows = [row for row in self.output.element_rows if row.kind == "flow_route"]
        _populate_flow_route_issue_table(self._flow_route_issue_table, [row for row in self.output.element_rows if row.kind == "flow_route_issue"])
        self._pipeline_candidate_rows = [row for row in self.output.element_rows if row.kind == "pipeline_segment_candidate"]
        self._populate_flow_routes()
        self._populate_pipeline_candidates()
        _populate_pipeline_segment_table(self._pipeline_segment_table, self.output.pipeline_segment_rows)
        _populate_pipeline_network_table(self._pipeline_network_table, self.output.pipeline_network_rows)
        _populate_pipeline_junction_table(self._pipeline_junction_table, self.output.pipeline_junction_rows)
        self._region_assignment_rows = [row for row in self.output.element_rows if row.kind == "region_assignment"]
        self._populate_region_assignments()
        _populate_applied_table(
            self._applied_table,
            [row for row in self.output.element_rows if row.kind == "applied_section_ditch_context"],
        )
        _populate_flowline_table(self._flowline_table, [row for row in self.output.element_rows if row.kind == "flowline_continuity"])
        self._report_rows = [row for row in self.output.element_rows if row.kind == "drainage_report"]
        self._populate_reports()
        self._status.setPlainText(_status_text(self.output))

    def _populate_reports(self) -> None:
        warnings_only = bool(getattr(self, "_report_warnings_only", None) is not None and self._report_warnings_only.isChecked())
        _populate_report_table(self._report_table, self._report_rows, warnings_only=warnings_only)

    def _populate_flow_routes(self) -> None:
        mode = (
            str(self._flow_route_filter.currentText() or "All")
            if getattr(self, "_flow_route_filter", None) is not None
            else "All"
        )
        rows, indices = _filter_flow_route_rows_with_indices(
            self._flow_route_rows,
            self._pipeline_candidate_rows,
            mode=mode,
        )
        self._flow_route_display_indices = indices
        _populate_flow_route_table(self._flow_route_table, rows)

    def _populate_pipeline_candidates(self) -> None:
        mode = (
            str(self._pipeline_candidate_filter.currentText() or "All")
            if getattr(self, "_pipeline_candidate_filter", None) is not None
            else "All"
        )
        rows, indices = _filter_pipeline_candidate_rows_with_indices(self._pipeline_candidate_rows, mode=mode)
        self._pipeline_candidate_display_indices = indices
        _populate_pipeline_table(self._pipeline_table, rows)

    def _populate_region_assignments(self) -> None:
        issues_only = bool(getattr(self, "_region_issues_only", None) is not None and self._region_issues_only.isChecked())
        _populate_region_table(
            self._region_table,
            _filter_region_assignment_rows(self._region_assignment_rows, issues_only=issues_only),
        )

    def _show_selected_pipeline_candidate(self) -> None:
        row_index = self._pipeline_table.currentRow()
        if row_index < 0:
            row_index = 0
        self._show_pipeline_candidate(row_index)

    def _show_pipeline_candidate(self, row_index: int) -> None:
        try:
            source_index = row_index
            if getattr(self, "_pipeline_candidate_display_indices", None):
                source_index = self._pipeline_candidate_display_indices[row_index]
            preview = show_drainage_pipeline_candidate_preview_object(self.document, row_index=source_index, output=self.output)
            self._status.setPlainText(_status_text(self.output) + f"\nPipeline candidate preview: {preview.Name}")
        except Exception as exc:
            self._status.setPlainText(_status_text(self.output) + f"\nPipeline candidate preview failed: {exc}")

    def _show_flow_route_issue(self, row_index: int) -> None:
        try:
            flow_rows = [row for row in list(getattr(self.output, "element_rows", []) or []) if row.kind == "flow_route"]
            if getattr(self, "_flow_route_display_indices", None):
                row_index = self._flow_route_display_indices[row_index]
            if row_index < 0 or row_index >= len(flow_rows):
                raise IndexError("Flow Route row index is out of range.")
            flow_route_ref = str(getattr(flow_rows[row_index], "label", "") or "")
            candidate_rows = [row for row in list(getattr(self.output, "element_rows", []) or []) if row.kind == "pipeline_segment_candidate"]
            candidate_index = next(
                (
                    index
                    for index, row in enumerate(candidate_rows)
                    if str(getattr(row, "label", "") or "") == flow_route_ref
                ),
                None,
            )
            if candidate_index is None:
                raise RuntimeError(f"No Pipeline Candidate row is available for {flow_route_ref}.")
            preview = show_drainage_pipeline_candidate_preview_object(self.document, row_index=candidate_index, output=self.output)
            status = str(getattr(preview, "IssueStatus", "") or getattr(preview, "CandidateStatus", "") or "")
            self._status.setPlainText(_status_text(self.output) + f"\nFlow Route preview: {flow_route_ref}; status={status}; object={preview.Name}")
        except Exception as exc:
            self._status.setPlainText(_status_text(self.output) + f"\nFlow Route preview failed: {exc}")

    def _show_flow_route_issue_marker(self, row_index: int) -> None:
        try:
            preview = show_drainage_flow_route_issue_preview_object(self.document, row_index=row_index, output=self.output)
            issue_kind = str(getattr(preview, "IssueKind", "") or "")
            self._status.setPlainText(_status_text(self.output) + f"\nFlow Route issue preview: {issue_kind}; object={preview.Name}")
        except Exception as exc:
            self._status.setPlainText(_status_text(self.output) + f"\nFlow Route issue preview failed: {exc}")

    def _open_related_panel(self, target: str) -> None:
        try:
            _open_drainage_review_navigation_target(target, document=self.document)
        except Exception as exc:
            self._status.setPlainText(_status_text(self.output) + f"\nOpen {target} failed: {exc}")

    def _show_selected_pipeline_segment(self) -> None:
        row_index = self._pipeline_segment_table.currentRow()
        if row_index < 0:
            row_index = 0
        self._show_pipeline_segment(row_index)

    def _show_pipeline_segment(self, row_index: int) -> None:
        try:
            preview = show_drainage_pipeline_segment_preview_object(self.document, row_index=row_index, output=self.output)
            self._status.setPlainText(_status_text(self.output) + f"\nPipeline segment preview: {preview.Name}")
        except Exception as exc:
            self._status.setPlainText(_status_text(self.output) + f"\nPipeline segment preview failed: {exc}")

    def _show_selected_pipeline_network(self) -> None:
        row_index = self._pipeline_network_table.currentRow()
        if row_index < 0:
            row_index = 0
        self._show_pipeline_network(row_index)

    def _show_pipeline_network(self, row_index: int) -> None:
        try:
            preview = show_drainage_pipeline_network_preview_object(self.document, row_index=row_index, output=self.output)
            self._status.setPlainText(_status_text(self.output) + f"\nPipeline network preview: {preview.Name}")
        except Exception as exc:
            self._status.setPlainText(_status_text(self.output) + f"\nPipeline network preview failed: {exc}")


__all__ = [
    "V1DrainageReviewTaskPanel",
    "configure_drainage_review_task_panel_runtime",
]
