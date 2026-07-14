"""Build Parametric task-panel presentation state and lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field

from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

from ..common.styles import apply_clickable_tab_style


@dataclass
class BuildCorridorViewModel:
    """UI-independent state consumed by the Build Parametric task panel."""

    document_identity: str = ""
    document_label: str = "No document"
    progress_value: int = 0
    progress_text: str = "Ready"
    summary_text: str = ""
    guided_review_rows: list[dict[str, object]] = field(default_factory=list)
    result_rows: list[dict[str, object]] = field(default_factory=list)
    slope_issue_rows: list[dict[str, object]] = field(default_factory=list)
    intersection_contract_rows: list[dict[str, object]] = field(
        default_factory=list
    )
    shared_breakline_rows: list[dict[str, object]] = field(default_factory=list)

    def set_progress(self, value: int, text: str = "") -> None:
        self.progress_value = max(0, min(100, int(value or 0)))
        self.progress_text = str(text or "").strip() or (
            "Ready" if self.progress_value == 0 else f"{self.progress_value}%"
        )

    def replace_rows(self, family: str, rows) -> None:
        target = {
            "guided": "guided_review_rows",
            "results": "result_rows",
            "slope_issues": "slope_issue_rows",
            "intersection_contracts": "intersection_contract_rows",
            "shared_breaklines": "shared_breakline_rows",
        }.get(str(family or ""))
        if target is None:
            raise ValueError(f"unknown Build Corridor row family: {family}")
        setattr(self, target, [dict(row or {}) for row in list(rows or [])])


class BuildCorridorTaskPanelPresentation:
    """Own task-panel lifecycle and shared presentation state.

    The command-side controller supplies UI construction and build callbacks.
    """

    def __init__(
        self,
        *,
        document=None,
        app_module=None,
        gui_module=None,
        document_identity=None,
        document_display_name=None,
    ) -> None:
        self._app_module = app_module
        self._gui_module = gui_module
        self.document = document or (
            getattr(app_module, "ActiveDocument", None)
            if app_module is not None
            else None
        )
        identity = (
            document_identity(self.document)
            if callable(document_identity)
            else ""
        )
        label = (
            document_display_name(self.document)
            if callable(document_display_name)
            else "No document"
        )
        self._document_identity = str(identity or "")
        self.view_model = BuildCorridorViewModel(
            document_identity=self._document_identity,
            document_label=str(label or "No document"),
        )
        self.form = self._build_ui()
        self._refresh_summary()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self._apply(close_after=True)

    def reject(self):
        gui = self._gui_module
        if gui is not None and hasattr(gui, "Control"):
            gui.Control.closeDialog()
        return True


def configure_build_corridor_task_panel_runtime(bindings) -> None:
    """Inject command/controller callbacks without a UI-to-command import."""

    protected = {
        "BuildCorridorTaskPanelPresentation",
        "BuildCorridorViewModel",
        "V1BuildCorridorTaskPanel",
        "configure_build_corridor_task_panel_runtime",
        "QtCore",
        "QtWidgets",
        "apply_clickable_tab_style",
    }
    for name, value in dict(bindings or {}).items():
        if name.startswith("__") or name in protected:
            continue
        globals()[name] = value


# Explicit placeholders are replaced by the command/controller callback map.
App = None
BUILD_CORRIDOR_PANEL_MAX_WIDTH = None
BUILD_CORRIDOR_PANEL_MIN_WIDTH = None
CORRIDOR_BUILD_REVIEW_OBJECTS = None
CORRIDOR_BUILD_REVIEW_ROW_COLORS = None
CORRIDOR_BUILD_REVIEW_TEXT_COLOR = None
Gui = None
SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD = None
SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG = None
SUPPLEMENTAL_SAMPLING_MAX_SPACING = None
SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL = None
SURFACE_TRANSITION_SPACING_PRESETS = None
_applied_section_supplemental_consumption_summary = None
_breakline_audit_surface_row_focuses_source_only = None
_build_parametric_compatibility_supplemental_sampling_enabled = None
_build_parametric_supplemental_apply_estimate = None
_compact_build_corridor_table = None
_confirm_message = None
_corridor_build_daylight_contact_marker_object = None
_corridor_build_preview_object = None
_display_source_id = None
_document_display_name = None
_document_identity = None
_drainage_review_context_label = None
_fit_build_corridor_table_to_rows = None
_format_structure_review_summary = None
_hide_applied_section_set_review_shape = None
_object_visibility = None
_process_panel_events = None
_region_boundary_display_diagnostics = None
_remove_preview_object = None
_select_and_fit_object = None
_set_object_visibility = None
_shared_breakline_consumer_for_review_role = None
_shared_breakline_summary_keys = None
_show_message = None
apply_v1_corridor_model = None
build_document_corridor_model = None
corridor_applied_sections_review_summary = None
corridor_build_guided_review_steps = None
corridor_build_preview_visibility_note = None
corridor_build_review_row_color = None
corridor_build_review_rows = None
corridor_build_visibility_group_visible = None
corridor_build_visibility_groups = None
corridor_drainage_review_rows = None
corridor_guided_review_step_available = None
corridor_guided_review_step_visibility = None
corridor_intersection_contract_review_rows = None
corridor_region_boundary_rows = None
corridor_shared_breakline_audit_rows = None
corridor_shared_breakline_audit_summary = None
corridor_slope_face_issue_rows = None
corridor_surface_transition_boundary_options = None
corridor_surface_transition_rows = None
create_corridor_surface_transition_from_region_boundary = None
create_or_update_corridor_surface_transition_for_boundary = None
find_v1_applied_section_set = None
find_v1_surface_model = None
focus_adjacent_corridor_slope_face_issue = None
focus_corridor_build_guided_review_step = None
focus_corridor_drainage_review_row = None
focus_corridor_intersection_contract_review_row = None
focus_corridor_region_boundary_row = None
focus_corridor_slope_face_issue = None
preferred_corridor_build_review_row_index = None
set_all_corridor_build_preview_visibility = None
set_corridor_build_daylight_contact_marker_visibility = None
set_corridor_build_preview_visibility = None
set_corridor_build_visibility_group = None
set_corridor_guided_review_step_visibility = None
shared_breakline_audit_display_rows = None
show_corridor_build_review_object = None
show_intersection_exclusion_near_boundary_highlight = None
show_intersection_shared_boundary_graph_highlight = None
show_shared_breakline_highlight = None
to_applied_section_set = None
toggle_corridor_surface_transition_enabled = None


class V1BuildCorridorTaskPanel(BuildCorridorTaskPanelPresentation):
    """Apply-gated Build Parametric task panel presentation."""

    def __init__(self, *, document=None):
        super().__init__(
            document=document,
            app_module=App,
            gui_module=Gui,
            document_identity=_document_identity,
            document_display_name=_document_display_name,
        )

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setObjectName("BuildParametricPanel")
        widget.setWindowTitle("ParametricRoad v1 - Build Parametric")
        widget.setStyleSheet(
            "QWidget#BuildParametricPanel QCheckBox { "
            "spacing: 10px; color: #f8fafc; padding: 3px 4px; border-radius: 4px; "
            "} "
            "QWidget#BuildParametricPanel QCheckBox:hover { "
            "background: #1f2937; color: #ffffff; "
            "} "
            "QWidget#BuildParametricPanel QCheckBox::indicator { "
            "width: 18px; height: 18px; border-radius: 4px; border: 2px solid #94a3b8; "
            "background: #0f172a; "
            "} "
            "QWidget#BuildParametricPanel QCheckBox::indicator:hover { "
            "border-color: #bfdbfe; background: #1e293b; "
            "} "
            "QWidget#BuildParametricPanel QCheckBox::indicator:checked { "
            "background: #2563eb; border-color: #93c5fd; "
            "} "
            "QWidget#BuildParametricPanel QCheckBox::indicator:unchecked { "
            "background: #111827; border-color: #64748b; "
            "} "
            "QWidget#BuildParametricPanel QCheckBox::indicator:disabled { "
            "background: #111827; border-color: #374151; "
            "} "
            "QWidget#BuildParametricPanel QCheckBox:disabled { "
            "color: #6b7280; "
            "}"
        )
        try:
            widget.setMinimumWidth(BUILD_CORRIDOR_PANEL_MIN_WIDTH)
            widget.setMaximumWidth(BUILD_CORRIDOR_PANEL_MAX_WIDTH)
            widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        except Exception:
            pass
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        title = QtWidgets.QLabel("Build Parametric")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        self._document_label = QtWidgets.QLabel(f"Document: {_document_display_name(self.document)}")
        self._document_label.setToolTip("This panel stays bound to the FreeCAD document it was opened from.")
        layout.addWidget(self._document_label)
        note = QtWidgets.QLabel(
            "Build the v1 CorridorModel from Applied Sections, review corridor surfaces, and package structure outputs when StructureModel source rows are available."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self._summary = QtWidgets.QPlainTextEdit()
        self._summary.setReadOnly(True)
        self._summary.setFixedHeight(150)
        try:
            self._summary.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        except Exception:
            pass
        layout.addWidget(self._summary)
        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("Ready")
        layout.addWidget(self._progress)
        tabs = QtWidgets.QTabWidget()
        self._tabs = tabs
        apply_clickable_tab_style(tabs, "BuildParametricTabs")
        try:
            tabs.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        except Exception:
            pass
        guided_tab = QtWidgets.QWidget()
        guided_layout = QtWidgets.QVBoxLayout(guided_tab)
        guided_layout.setContentsMargins(8, 8, 8, 8)
        guided_layout.setAlignment(QtCore.Qt.AlignTop)
        results_tab = QtWidgets.QWidget()
        results_layout = QtWidgets.QVBoxLayout(results_tab)
        results_layout.setContentsMargins(8, 8, 8, 8)
        results_layout.setAlignment(QtCore.Qt.AlignTop)
        issues_tab = QtWidgets.QWidget()
        issues_layout = QtWidgets.QVBoxLayout(issues_tab)
        issues_layout.setContentsMargins(8, 8, 8, 8)
        issues_layout.setAlignment(QtCore.Qt.AlignTop)
        intersections_tab = QtWidgets.QWidget()
        intersections_layout = QtWidgets.QVBoxLayout(intersections_tab)
        intersections_layout.setContentsMargins(8, 8, 8, 8)
        intersections_layout.setAlignment(QtCore.Qt.AlignTop)
        breakline_tab = QtWidgets.QWidget()
        breakline_layout = QtWidgets.QVBoxLayout(breakline_tab)
        breakline_layout.setContentsMargins(8, 8, 8, 8)
        breakline_layout.setAlignment(QtCore.Qt.AlignTop)
        regions_tab = QtWidgets.QWidget()
        regions_layout = QtWidgets.QVBoxLayout(regions_tab)
        regions_layout.setContentsMargins(8, 8, 8, 8)
        regions_layout.setAlignment(QtCore.Qt.AlignTop)
        drainage_tab = QtWidgets.QWidget()
        drainage_layout = QtWidgets.QVBoxLayout(drainage_tab)
        drainage_layout.setContentsMargins(8, 8, 8, 8)
        drainage_layout.setAlignment(QtCore.Qt.AlignTop)
        visibility_tab = QtWidgets.QWidget()
        visibility_layout = QtWidgets.QVBoxLayout(visibility_tab)
        visibility_layout.setContentsMargins(8, 8, 8, 8)
        visibility_layout.setAlignment(QtCore.Qt.AlignTop)
        tabs.addTab(guided_tab, "Guided Review")
        tabs.addTab(results_tab, "Results")
        tabs.addTab(issues_tab, "Slope Diagnostics")
        tabs.addTab(intersections_tab, "Intersections")
        tabs.addTab(breakline_tab, "Breakline Audit")
        tabs.addTab(regions_tab, "Regions")
        tabs.addTab(drainage_tab, "Drainage")
        tabs.addTab(visibility_tab, "Visibility")
        try:
            tabs.currentChanged.connect(lambda _index: self._sync_tabs_height_later())
        except Exception:
            pass
        layout.addWidget(tabs)
        guided_label = QtWidgets.QLabel("Guided Review")
        guided_label.setToolTip("Follow the practical corridor check order and focus the related 3D preview layer.")
        guided_layout.addWidget(guided_label)
        sampling_note = QtWidgets.QLabel(
            "Applied Section Sampling: supplemental density is configured in Applied Sections; Build Parametric consumes the resulting section rows."
        )
        sampling_note.setWordWrap(True)
        sampling_note.setToolTip(
            "Build Parametric now consumes supplemental Applied Sections generated by the Applied Sections stage."
        )
        guided_layout.addWidget(sampling_note)
        self._supplemental_sampling_frame_count_label = QtWidgets.QLabel("Applied Sections: n/a")
        self._supplemental_sampling_frame_count_label.setToolTip(
            "Source, supplemental, and total Applied Sections consumed by Build Parametric."
        )
        guided_layout.addWidget(self._supplemental_sampling_frame_count_label)
        self._sync_supplemental_sampling_frame_count_label()
        self._guided_table = QtWidgets.QTableWidget(0, 5)
        self._guided_table.setHorizontalHeaderLabels(["Step", "Status", "Focus", "Output Path", "Notes"])
        _compact_build_corridor_table(self._guided_table, [145, 76, 120, 105, 220])
        self._guided_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._guided_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._guided_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._guided_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._guided_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._guided_table.cellDoubleClicked.connect(lambda row_index, _col: self._focus_guided_review_row(row_index))
        guided_layout.addWidget(self._guided_table)
        self._review_table = QtWidgets.QTableWidget(0, 10)
        self._review_table.setHorizontalHeaderLabels(
            [
                "Result",
                "Status",
                "Object",
                "Vertices",
                "Triangles/Points",
                "Role",
                "Output Path",
                "Applied Sections",
                "Applied Diagnostics",
                "Notes",
            ]
        )
        _compact_build_corridor_table(self._review_table, [110, 72, 150, 70, 105, 90, 105, 150, 150, 220])
        self._review_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._review_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._review_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._review_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._review_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._review_table.cellDoubleClicked.connect(lambda row_index, _col: self._show_review_row(row_index))
        results_layout.addWidget(self._review_table)
        issue_label = QtWidgets.QLabel("Slope Face Diagnostics")
        issue_label.setToolTip("Double-click a fallback issue row to select and fit the related 3D review marker.")
        issues_layout.addWidget(issue_label)
        self._slope_issue_table = QtWidgets.QTableWidget(0, 5)
        self._slope_issue_table.setHorizontalHeaderLabels(["Station", "Side", "Reason", "Status", "Marker"])
        _compact_build_corridor_table(self._slope_issue_table, [90, 60, 150, 80, 130])
        self._slope_issue_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._slope_issue_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._slope_issue_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._slope_issue_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._slope_issue_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._slope_issue_table.cellDoubleClicked.connect(lambda row_index, _col: self._show_slope_face_issue_row(row_index))
        issues_layout.addWidget(self._slope_issue_table)
        issue_nav_row = QtWidgets.QHBoxLayout()
        previous_issue_button = QtWidgets.QPushButton("Previous Fallback Issue")
        previous_issue_button.clicked.connect(lambda: self._focus_adjacent_slope_face_issue(-1))
        issue_nav_row.addWidget(previous_issue_button)
        next_issue_button = QtWidgets.QPushButton("Next Fallback Issue")
        next_issue_button.clicked.connect(lambda: self._focus_adjacent_slope_face_issue(1))
        issue_nav_row.addWidget(next_issue_button)
        issue_nav_row.addStretch(1)
        issues_layout.addLayout(issue_nav_row)
        intersections_label = QtWidgets.QLabel("Intersection Contracts")
        intersections_label.setToolTip("Edge-network-first contracts for topology, edges, surface zones, and ordinary corridor clipping.")
        intersections_layout.addWidget(intersections_label)
        self._intersection_contract_table = QtWidgets.QTableWidget(0, 10)
        self._intersection_contract_table.setHorizontalHeaderLabels(
            ["Contract", "Status", "Source Status", "Output Path", "ID", "Role", "Source", "Boundary", "Source Diagnostics", "Notes"]
        )
        _compact_build_corridor_table(self._intersection_contract_table, [105, 72, 96, 105, 180, 120, 180, 220, 240, 260])
        self._intersection_contract_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._intersection_contract_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._intersection_contract_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._intersection_contract_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._intersection_contract_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._intersection_contract_table.cellDoubleClicked.connect(lambda row_index, _col: self._show_intersection_contract_review_row(row_index))
        intersections_layout.addWidget(self._intersection_contract_table)
        breakline_title = QtWidgets.QLabel("Shared Breakline Audit")
        breakline_title.setToolTip("Checks whether surfaces that share a boundary consume the same breakline contract and match its endpoints.")
        breakline_layout.addWidget(breakline_title)
        self._breakline_audit_status_label = QtWidgets.QLabel("Shared breakline audit not available")
        self._breakline_audit_status_label.setWordWrap(True)
        self._breakline_audit_status_label.setMinimumHeight(34)
        breakline_layout.addWidget(self._breakline_audit_status_label)
        self._breakline_audit_detail_label = QtWidgets.QLabel("")
        self._breakline_audit_detail_label.setWordWrap(True)
        breakline_layout.addWidget(self._breakline_audit_detail_label)
        self._breakline_audit_table = QtWidgets.QTableWidget(0, 12)
        self._breakline_audit_table.setHorizontalHeaderLabels(
            ["Surface", "Audit", "Consumed", "Geometry", "Mesh", "Missing", "Mismatch", "Reversed", "Roles", "Recommended Action", "Object", "Notes"]
        )
        _compact_build_corridor_table(self._breakline_audit_table, [130, 72, 72, 78, 78, 65, 70, 70, 185, 170, 145, 260])
        self._breakline_audit_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._breakline_audit_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._breakline_audit_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._breakline_audit_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._breakline_audit_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._breakline_audit_table.cellDoubleClicked.connect(lambda row_index, _col: self._show_breakline_audit_row(row_index))
        self._breakline_audit_table.itemSelectionChanged.connect(self._sync_breakline_highlight_filter_options)
        breakline_layout.addWidget(self._breakline_audit_table)
        breakline_button_row = QtWidgets.QHBoxLayout()
        self._breakline_highlight_filter_combo = QtWidgets.QComboBox()
        self._breakline_highlight_filter_combo.addItem("All roles", ("", ""))
        breakline_button_row.addWidget(self._breakline_highlight_filter_combo, 1)
        focus_breakline_button = QtWidgets.QPushButton("Highlight Breakline")
        focus_breakline_button.clicked.connect(self._show_selected_breakline_audit_row)
        breakline_button_row.addWidget(focus_breakline_button)
        refresh_breakline_button = QtWidgets.QPushButton("Refresh Audit")
        refresh_breakline_button.clicked.connect(self._refresh_shared_breakline_audit)
        breakline_button_row.addWidget(refresh_breakline_button)
        breakline_button_row.addStretch(1)
        breakline_layout.addLayout(breakline_button_row)
        regions_label = QtWidgets.QLabel("Region Boundaries")
        regions_label.setToolTip("Double-click a Region row to select its built 3D Region surface object.")
        regions_layout.addWidget(regions_label)
        self._region_table = QtWidgets.QTableWidget(0, 11)
        self._region_table.setHorizontalHeaderLabels(
            ["Alignment", "Region", "Start STA", "End STA", "Assembly", "Structure", "Drainage", "Intersection", "Surface", "Boundary", "Diagnostics"]
        )
        _compact_build_corridor_table(self._region_table, [125, 140, 80, 80, 105, 105, 90, 120, 80, 90, 240])
        self._region_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._region_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._region_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._region_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._region_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._region_table.cellDoubleClicked.connect(lambda row_index, _col: self._show_region_boundary_row(row_index))
        self._region_table.itemSelectionChanged.connect(self._sync_surface_transition_station_options_from_selected_region)
        regions_layout.addWidget(self._region_table)
        region_button_row = QtWidgets.QHBoxLayout()
        highlight_region_button = QtWidgets.QPushButton("Highlight Region")
        highlight_region_button.clicked.connect(self._show_selected_region_boundary_row)
        region_button_row.addWidget(highlight_region_button)
        refresh_regions_button = QtWidgets.QPushButton("Refresh Boundaries")
        refresh_regions_button.clicked.connect(self._refresh_region_boundary_rows)
        region_button_row.addWidget(refresh_regions_button)
        region_button_row.addStretch(1)
        regions_layout.addLayout(region_button_row)
        transitions_label = QtWidgets.QLabel("Surface Transitions")
        transitions_label.setToolTip("User-selected station ranges where Transition Surface treatment should be applied.")
        regions_layout.addWidget(transitions_label)
        self._surface_transition_table = QtWidgets.QTableWidget(0, 13)
        self._surface_transition_table.setHorizontalHeaderLabels(
            [
                "Transition",
                "Enabled",
                "STA",
                "Spacing",
                "Sample Count",
                "From",
                "To",
                "From Surface",
                "To Surface",
                "Targets",
                "Mode",
                "Status",
                "Diagnostics",
            ]
        )
        _compact_build_corridor_table(self._surface_transition_table, [135, 58, 90, 75, 65, 90, 90, 150, 150, 95, 135, 75, 190])
        self._surface_transition_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._surface_transition_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._surface_transition_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._surface_transition_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._surface_transition_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._surface_transition_table.itemSelectionChanged.connect(self._sync_selected_surface_transition_row_controls)
        regions_layout.addWidget(self._surface_transition_table)
        transition_range_row = QtWidgets.QHBoxLayout()
        transition_range_row.addWidget(QtWidgets.QLabel("Region STA"))
        self._surface_transition_boundary_combo = QtWidgets.QComboBox()
        self._surface_transition_boundary_combo.currentIndexChanged.connect(lambda _index: self._sync_selected_surface_transition_boundary_spacing())
        transition_range_row.addWidget(self._surface_transition_boundary_combo, 2)
        transition_range_row.addWidget(QtWidgets.QLabel("Spacing"))
        self._surface_transition_spacing_combo = QtWidgets.QComboBox()
        for label, value in SURFACE_TRANSITION_SPACING_PRESETS:
            self._surface_transition_spacing_combo.addItem(label, value)
        self._surface_transition_spacing_combo.currentIndexChanged.connect(lambda _index: self._sync_surface_transition_custom_spacing_state())
        transition_range_row.addWidget(self._surface_transition_spacing_combo)
        self._surface_transition_spacing_spin = QtWidgets.QDoubleSpinBox()
        self._surface_transition_spacing_spin.setRange(0.1, 10000.0)
        self._surface_transition_spacing_spin.setDecimals(3)
        self._surface_transition_spacing_spin.setSingleStep(0.5)
        self._surface_transition_spacing_spin.setSuffix(" m")
        self._surface_transition_spacing_spin.setValue(SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL)
        transition_range_row.addWidget(self._surface_transition_spacing_spin)
        create_update_transition_button = QtWidgets.QPushButton("Update")
        create_update_transition_button.clicked.connect(self._create_transition_from_selected_boundary_option)
        transition_range_row.addWidget(create_update_transition_button)
        transition_range_row.addStretch(1)
        regions_layout.addLayout(transition_range_row)
        transition_button_row = QtWidgets.QHBoxLayout()
        toggle_transition_button = QtWidgets.QPushButton("Toggle Enabled")
        toggle_transition_button.clicked.connect(self._toggle_selected_surface_transition)
        transition_button_row.addWidget(toggle_transition_button)
        refresh_transitions_button = QtWidgets.QPushButton("Refresh Transitions")
        refresh_transitions_button.clicked.connect(lambda: self._set_surface_transition_rows(corridor_surface_transition_rows(self.document)))
        transition_button_row.addWidget(refresh_transitions_button)
        transition_button_row.addStretch(1)
        regions_layout.addLayout(transition_button_row)
        drainage_label = QtWidgets.QLabel("Drainage Diagnostics")
        drainage_label.setToolTip("Roadside Drainage reviews station-range ditch surfaces; Intersection Drainage reviews low-point coverage inside intersection control Regions.")
        drainage_layout.addWidget(drainage_label)
        self._drainage_table = QtWidgets.QTableWidget(0, 7)
        self._drainage_table.setHorizontalHeaderLabels(["Context", "Station", "Status", "Points", "Left", "Right", "Notes"])
        _compact_build_corridor_table(self._drainage_table, [150, 90, 80, 65, 55, 55, 220])
        self._drainage_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._drainage_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._drainage_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._drainage_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._drainage_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._drainage_table.cellDoubleClicked.connect(lambda row_index, _col: self._show_drainage_review_row(row_index))
        drainage_layout.addWidget(self._drainage_table)
        visibility_label = QtWidgets.QLabel("Preview Visibility")
        visibility_label.setToolTip("Toggle corridor review objects in the 3D View without rebuilding the corridor.")
        visibility_layout.addWidget(visibility_label)
        group_visibility_label = QtWidgets.QLabel("Grouped Visibility")
        group_visibility_label.setToolTip("Toggle common review layer groups together.")
        visibility_layout.addWidget(group_visibility_label)
        group_visibility_grid = QtWidgets.QGridLayout()
        self._visibility_group_checks = {}
        for index, group in enumerate(corridor_build_visibility_groups()):
            group_id = str(group.get("group_id", "") or "")
            check = QtWidgets.QCheckBox(str(group.get("title", "") or group_id))
            check.setChecked(False)
            check.toggled.connect(lambda checked, group_id=group_id: self._set_visibility_group(group_id, checked))
            self._visibility_group_checks[group_id] = check
            group_visibility_grid.addWidget(check, index // 2, index % 2)
        visibility_layout.addLayout(group_visibility_grid)
        visibility_layout.addSpacing(8)
        visibility_grid = QtWidgets.QGridLayout()
        self._visibility_checks = {}
        for index, (role, title, _object_name) in enumerate(CORRIDOR_BUILD_REVIEW_OBJECTS):
            check = QtWidgets.QCheckBox(title)
            check.setChecked(True)
            check.toggled.connect(lambda checked, role=role: self._set_preview_visibility(role, checked))
            self._visibility_checks[role] = check
            visibility_grid.addWidget(check, index // 2, index % 2)
        visibility_layout.addLayout(visibility_grid)
        guided_visibility_label = QtWidgets.QLabel("Guided Review Visibility")
        guided_visibility_label.setToolTip("Show or hide objects represented by Guided Review rows.")
        visibility_layout.addWidget(guided_visibility_label)
        self._guided_visibility_grid = QtWidgets.QGridLayout()
        self._guided_visibility_checks = {}
        visibility_layout.addLayout(self._guided_visibility_grid)
        marker_row = QtWidgets.QHBoxLayout()
        self._daylight_contact_marker_check = QtWidgets.QCheckBox("Daylight Contact Markers")
        self._daylight_contact_marker_check.setToolTip("Show or hide the large daylight/EG contact markers.")
        self._daylight_contact_marker_check.setChecked(False)
        self._daylight_contact_marker_check.toggled.connect(self._set_daylight_contact_marker_visibility)
        marker_row.addWidget(self._daylight_contact_marker_check)
        marker_row.addStretch(1)
        visibility_layout.addLayout(marker_row)
        row = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_summary)
        row.addWidget(refresh_button)
        focus_button = QtWidgets.QPushButton("Focus")
        focus_button.clicked.connect(self._show_selected_row)
        row.addWidget(focus_button)
        structure_output_button = QtWidgets.QPushButton("Structure Output")
        structure_output_button.clicked.connect(self._open_structure_output_panel)
        row.addWidget(structure_output_button)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        row.addWidget(apply_button)
        row.addStretch(1)
        layout.addLayout(row)

        export_row = QtWidgets.QHBoxLayout()
        show_all_button = QtWidgets.QPushButton("Show All")
        show_all_button.clicked.connect(lambda: self._set_all_preview_visibility(True))
        export_row.addWidget(show_all_button)
        hide_all_button = QtWidgets.QPushButton("Hide All")
        hide_all_button.clicked.connect(lambda: self._set_all_preview_visibility(False))
        export_row.addWidget(hide_all_button)
        export_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        export_row.addWidget(close_button)
        layout.addLayout(export_row)
        layout.addStretch(1)
        self._sync_tabs_height_later()
        return widget

    def _sync_tabs_height_later(self) -> None:
        try:
            QtCore.QTimer.singleShot(0, self._sync_tabs_height)
        except Exception:
            self._sync_tabs_height()

    def _sync_tabs_height(self) -> None:
        tabs = getattr(self, "_tabs", None)
        if tabs is None:
            return
        try:
            current = tabs.currentWidget()
            if current is None:
                return
            page_layout = current.layout()
            page_height = int(page_layout.sizeHint().height()) if page_layout is not None else int(current.sizeHint().height())
            tab_bar_height = int(tabs.tabBar().sizeHint().height()) if tabs.tabBar() is not None else 28
            frame = int(tabs.style().pixelMetric(QtWidgets.QStyle.PM_DefaultFrameWidth, None, tabs)) * 2
            target_height = max(120, page_height + tab_bar_height + frame + 12)
            tabs.setMinimumHeight(target_height)
            tabs.setMaximumHeight(target_height)
            tabs.updateGeometry()
        except Exception:
            pass

    def _refresh_summary(self):
        applied_obj = find_v1_applied_section_set(self.document)
        applied = to_applied_section_set(applied_obj)
        if applied is None:
            summary_text = (
                "Applied Sections: missing\n"
                "Run Applied Sections before Build Parametric."
            )
            self.view_model.summary_text = summary_text
            self._summary.setPlainText(summary_text)
            self._set_guided_review_rows(corridor_build_guided_review_steps(self.document, supplemental_sampling_enabled=self._use_supplemental_sampling(), supplemental_sampling_max_spacing=self._supplemental_sampling_max_spacing(), supplemental_sampling_tangent_delta_deg=self._supplemental_sampling_tangent_delta_deg(), supplemental_sampling_chord_deviation=self._supplemental_sampling_chord_deviation()))
            self._set_review_rows(corridor_build_review_rows(self.document))
            self._set_slope_face_issue_rows(corridor_slope_face_issue_rows(self.document))
            self._set_intersection_contract_review_rows(corridor_intersection_contract_review_rows(self.document))
            self._refresh_shared_breakline_audit()
            self._set_region_boundary_rows(corridor_region_boundary_rows(self.document))
            self._sync_surface_transition_station_options_from_selected_region()
            self._set_surface_transition_rows(corridor_surface_transition_rows(self.document))
            self._set_drainage_review_rows(corridor_drainage_review_rows(self.document))
            self._sync_tabs_height_later()
            return
        applied_summary = corridor_applied_sections_review_summary(self.document)
        summary_text = "\n".join(
            [
                    f"Applied Sections: {applied.applied_section_set_id}",
                    f"Stations: {len(applied.station_rows)}",
                    f"Alignment: {applied.alignment_id}",
                    f"Source Review: {applied_summary.get('summary', '')}",
                    f"Source Structure: {_format_structure_review_summary(applied_summary)}",
                    f"Source Diagnostics: {applied_summary.get('diagnostics', '')}",
                    "",
                    "Click Apply to create or update the v1 CorridorModel.",
            ]
        )
        self.view_model.summary_text = summary_text
        self._summary.setPlainText(summary_text)
        self._set_guided_review_rows(corridor_build_guided_review_steps(self.document, supplemental_sampling_enabled=self._use_supplemental_sampling(), supplemental_sampling_max_spacing=self._supplemental_sampling_max_spacing(), supplemental_sampling_tangent_delta_deg=self._supplemental_sampling_tangent_delta_deg(), supplemental_sampling_chord_deviation=self._supplemental_sampling_chord_deviation()))
        self._sync_supplemental_sampling_frame_count_label()
        self._set_review_rows(corridor_build_review_rows(self.document))
        self._set_slope_face_issue_rows(corridor_slope_face_issue_rows(self.document))
        self._set_intersection_contract_review_rows(corridor_intersection_contract_review_rows(self.document))
        self._refresh_shared_breakline_audit()
        self._set_region_boundary_rows(corridor_region_boundary_rows(self.document))
        self._sync_surface_transition_station_options_from_selected_region()
        self._set_surface_transition_rows(corridor_surface_transition_rows(self.document))
        self._set_drainage_review_rows(corridor_drainage_review_rows(self.document))
        self._sync_tabs_height_later()

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            self._set_progress(0, "Preparing build...")
            self._set_progress(15, "Reading Applied Sections...")
            applied = to_applied_section_set(find_v1_applied_section_set(self.document))
            supplemental_estimate = _build_parametric_supplemental_apply_estimate(applied) if applied is not None else {}
            estimate_message = str(supplemental_estimate.get("message", "") or "")
            if estimate_message:
                self._summary.setPlainText(estimate_message)
                duration_text = str(supplemental_estimate.get("duration_text", "") or "")
                progress_text = "Supplemental Applied Sections detected"
                if duration_text:
                    progress_text = f"{progress_text}; estimated time about {duration_text}"
                self._set_progress(18, progress_text)
                if not _confirm_message(
                    self.form,
                    "Build Parametric",
                    f"{estimate_message}\n\nContinue Build Parametric?",
                ):
                    self._summary.setPlainText(
                        "Build Parametric was cancelled.\n"
                        "Supplemental Applied Sections are present; no corridor output was changed."
                    )
                    self._set_progress(0, "Build cancelled")
                    return False
            compatibility_supplemental_sampling = _build_parametric_compatibility_supplemental_sampling_enabled(
                self.document,
                supplemental_sampling_max_spacing=self._supplemental_sampling_max_spacing(),
                supplemental_sampling_tangent_delta_deg=self._supplemental_sampling_tangent_delta_deg(),
                supplemental_sampling_chord_deviation=self._supplemental_sampling_chord_deviation(),
            )
            result = build_document_corridor_model(self.document)
            self._set_progress(35, "Building model...")
            obj = apply_v1_corridor_model(
                document=self.document,
                corridor_model=result,
                show_daylight_contact_markers=self._show_daylight_contact_markers(),
                supplemental_sampling_enabled=compatibility_supplemental_sampling,
                supplemental_sampling_max_spacing=self._supplemental_sampling_max_spacing(),
                supplemental_sampling_tangent_delta_deg=self._supplemental_sampling_tangent_delta_deg(),
                supplemental_sampling_chord_deviation=self._supplemental_sampling_chord_deviation(),
                progress_callback=self._set_progress,
            )
            self._set_progress(96, "Reading surface summary...")
            surface_obj = find_v1_surface_model(self.document)
            surface_count = int(getattr(surface_obj, "SurfaceCount", 0) or 0) if surface_obj is not None else 0
            frame_summary = self._supplemental_sampling_summary()
            frame_message = (
                f"Applied Sections consumed: source {int(frame_summary.get('source_section_count', 0) or 0)}, "
                f"supplemental {int(frame_summary.get('supplemental_section_count', 0) or 0)}, "
                f"total {int(frame_summary.get('total_section_count', 0) or 0)}"
                if frame_summary
                else "Applied Sections consumed: n/a"
            )
            if compatibility_supplemental_sampling:
                frame_message = f"{frame_message}\nCompatibility fallback: hidden supplemental frames used; rebuild Applied Sections."
            message = f"CorridorModel has been built.\nStations: {len(result.station_rows)}\nSurface rows: {surface_count}\n{frame_message}"
            self._summary.setPlainText(message + f"\nObject: {obj.Label}")
            self._set_progress(97, "Refreshing review rows...")
            _hide_applied_section_set_review_shape(self.document)
            review_rows = corridor_build_review_rows(self.document)
            self._set_guided_review_rows(corridor_build_guided_review_steps(self.document, supplemental_sampling_enabled=compatibility_supplemental_sampling, supplemental_sampling_max_spacing=self._supplemental_sampling_max_spacing(), supplemental_sampling_tangent_delta_deg=self._supplemental_sampling_tangent_delta_deg(), supplemental_sampling_chord_deviation=self._supplemental_sampling_chord_deviation()))
            self._sync_supplemental_sampling_frame_count_label()
            self._set_review_rows(review_rows)
            self._set_slope_face_issue_rows(corridor_slope_face_issue_rows(self.document))
            self._set_intersection_contract_review_rows(corridor_intersection_contract_review_rows(self.document))
            self._refresh_shared_breakline_audit()
            self._set_region_boundary_rows(corridor_region_boundary_rows(self.document))
            self._sync_surface_transition_station_options_from_selected_region()
            self._set_surface_transition_rows(corridor_surface_transition_rows(self.document))
            self._set_drainage_review_rows(corridor_drainage_review_rows(self.document))
            self._sync_supplemental_sampling_frame_count_label()
            self._sync_tabs_height_later()
            self._set_progress(99, "Focusing review preview...")
            focused = self._show_preferred_review_row(review_rows)
            if focused:
                self._summary.setPlainText(
                    message + f"\nObject: {obj.Label}\nFocused: {getattr(focused, 'Label', getattr(focused, 'Name', ''))}"
                )
            self._set_progress(100, "Build complete")
            _show_message(self.form, "Build Parametric", message)
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_progress(0, "Build failed")
            self._summary.setPlainText(f"CorridorModel was not built:\n{exc}")
            _show_message(self.form, "Build Parametric", f"CorridorModel was not built.\n{exc}")
            return False

    def _set_progress(self, value: int, text: str = "") -> None:
        self.view_model.set_progress(value, text)
        progress = getattr(self, "_progress", None)
        if progress is None:
            return
        try:
            progress.setValue(max(0, min(100, int(value))))
            if text:
                progress.setFormat(text)
        except Exception:
            return
        _process_panel_events()

    def _use_supplemental_sampling(self) -> bool:
        return False

    def _supplemental_sampling_max_spacing(self) -> float:
        slider = getattr(self, "_supplemental_sampling_spacing_slider", None)
        if slider is None:
            return float(SUPPLEMENTAL_SAMPLING_MAX_SPACING)
        try:
            density = max(1, min(25, int(slider.value())))
            return float(max(1, 26 - density))
        except Exception:
            return float(SUPPLEMENTAL_SAMPLING_MAX_SPACING)

    def _supplemental_sampling_tangent_delta_deg(self) -> float:
        spin = getattr(self, "_supplemental_sampling_tangent_spin", None)
        if spin is None:
            return float(SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG)
        try:
            return float(spin.value())
        except Exception:
            return float(SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG)

    def _supplemental_sampling_chord_deviation(self) -> float:
        spin = getattr(self, "_supplemental_sampling_chord_spin", None)
        if spin is None:
            return float(SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD)
        try:
            return float(spin.value())
        except Exception:
            return float(SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD)

    def _supplemental_sampling_summary(self) -> dict[str, object]:
        applied = to_applied_section_set(find_v1_applied_section_set(self.document))
        if applied is None:
            return {}
        return _applied_section_supplemental_consumption_summary(applied)

    def _sync_supplemental_sampling_spacing_label(self) -> None:
        label = getattr(self, "_supplemental_sampling_spacing_value", None)
        if label is None:
            return
        try:
            slider = getattr(self, "_supplemental_sampling_spacing_slider", None)
            density = int(slider.value()) if slider is not None else 21
            spacing = self._supplemental_sampling_max_spacing()
            label.setText(f"{density}/25 ({spacing:g} m)")
            label.setToolTip(
                f"Supplemental curve density: {density}/25. Approximate max curved-span spacing: {spacing:g} m. Straight spans are not densified by spacing alone."
            )
            self._sync_supplemental_sampling_frame_count_label()
        except Exception:
            return

    def _sync_supplemental_sampling_frame_count_label(self) -> None:
        label = getattr(self, "_supplemental_sampling_frame_count_label", None)
        if label is None:
            return
        try:
            summary = self._supplemental_sampling_summary()
            if not summary:
                label.setText("Applied Sections: n/a")
                return
            kind_counts = dict(summary.get("kind_counts", {}) or {})
            kind_text = ", ".join(f"{key}={value}" for key, value in sorted(kind_counts.items())) or "none"
            label.setText(
                "Applied Sections: "
                f"source {int(summary.get('source_section_count', 0) or 0)}, "
                f"supplemental {int(summary.get('supplemental_section_count', 0) or 0)}, "
                f"total {int(summary.get('total_section_count', 0) or 0)}"
            )
            applied = to_applied_section_set(find_v1_applied_section_set(self.document))
            estimate = _build_parametric_supplemental_apply_estimate(applied) if applied is not None else {}
            estimate_text = str(estimate.get("duration_text", "") or "")
            estimate_note = (
                f" Estimated Build Parametric time with current supplemental rows: about {estimate_text}."
                if estimate_text
                else ""
            )
            label.setToolTip(
                f"kinds: {kind_text}; Build Parametric hidden supplemental frames are disabled.{estimate_note}"
            )
        except Exception:
            label.setText("Applied Sections: unavailable")

    def _open_structure_output_panel(self) -> bool:
        try:
            from .cmd_structure_output import run_v1_structure_output_command

            run_v1_structure_output_command(document=self.document)
            self._summary.setPlainText("Structure Output panel opened.")
            return True
        except Exception as exc:
            self._summary.setPlainText(f"Structure Output panel was not opened:\n{exc}")
            _show_message(self.form, "Build Parametric", f"Structure Output panel was not opened.\n{exc}")
            return False

    def _set_guided_review_rows(self, rows: list[dict[str, object]]) -> None:
        self.view_model.replace_rows("guided", rows)
        if not hasattr(self, "_guided_table"):
            return
        self._guided_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._guided_table.rowCount()
            self._guided_table.insertRow(row_index)
            values = [
                str(row.get("title", "") or ""),
                str(row.get("status", "") or ""),
                str(row.get("focus", "") or ""),
                str(row.get("output_path", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if col == 0:
                    item.setData(32, str(row.get("step_id", "") or ""))
                self._guided_table.setItem(row_index, col, item)
            self._apply_guided_row_style(row_index, str(row.get("status", "") or ""))
        if self._guided_table.rowCount() > 0:
            try:
                self._guided_table.selectRow(0)
            except Exception:
                pass
        _fit_build_corridor_table_to_rows(self._guided_table)
        self._set_guided_visibility_checks(list(rows or []))

    def _set_review_rows(self, rows: list[dict[str, object]]) -> None:
        self.view_model.replace_rows("results", rows)
        if not hasattr(self, "_review_table"):
            return
        self._review_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._review_table.rowCount()
            self._review_table.insertRow(row_index)
            values = [
                str(row.get("result", "") or ""),
                str(row.get("status", "") or ""),
                str(row.get("object_label", "") or row.get("object_name", "") or ""),
                str(row.get("vertex_count", "") or ""),
                str(row.get("triangle_or_point_count", "") or ""),
                str(row.get("role", "") or ""),
                str(row.get("output_path", "") or ""),
                str(row.get("applied_section_summary", "") or ""),
                str(row.get("applied_section_diagnostics", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                self._review_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))
            self._apply_review_row_style(row_index, str(row.get("status", "") or ""))
        preferred_index = preferred_corridor_build_review_row_index(list(rows or []))
        if preferred_index is not None:
            try:
                self._review_table.selectRow(int(preferred_index))
            except Exception:
                pass
        _fit_build_corridor_table_to_rows(self._review_table)
        self._sync_visibility_checks()

    def _set_slope_face_issue_rows(self, rows: list[dict[str, str]]) -> None:
        self.view_model.replace_rows("slope_issues", rows)
        if not hasattr(self, "_slope_issue_table"):
            return
        self._slope_issue_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._slope_issue_table.rowCount()
            self._slope_issue_table.insertRow(row_index)
            values = [
                str(row.get("station_label", "") or ""),
                str(row.get("side", "") or ""),
                str(row.get("reason", "") or ""),
                str(row.get("status", "") or ""),
                str(row.get("marker_object", "") or ""),
            ]
            for col, value in enumerate(values):
                self._slope_issue_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))
            self._apply_slope_issue_row_style(row_index)
        if self._slope_issue_table.rowCount() > 0:
            try:
                self._slope_issue_table.selectRow(0)
            except Exception:
                pass
        _fit_build_corridor_table_to_rows(self._slope_issue_table)

    def _set_intersection_contract_review_rows(self, rows: list[dict[str, object]]) -> None:
        self.view_model.replace_rows("intersection_contracts", rows)
        if not hasattr(self, "_intersection_contract_table"):
            return
        self._intersection_contract_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._intersection_contract_table.rowCount()
            self._intersection_contract_table.insertRow(row_index)
            values = [
                str(row.get("contract_family", "") or ""),
                str(row.get("status", "") or ""),
                str(row.get("source_status", "") or ""),
                str(row.get("output_path", "") or ""),
                str(row.get("row_id", "") or ""),
                str(row.get("role", "") or ""),
                str(row.get("source_refs", "") or ""),
                str(row.get("boundary_refs", "") or ""),
                str(row.get("source_diagnostics", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                self._intersection_contract_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))
            self._apply_intersection_contract_row_style(row_index, str(row.get("status", "") or ""))
        if self._intersection_contract_table.rowCount() > 0:
            try:
                self._intersection_contract_table.selectRow(0)
            except Exception:
                pass
        _fit_build_corridor_table_to_rows(self._intersection_contract_table)

    def _refresh_shared_breakline_audit(self) -> None:
        self._set_shared_breakline_audit_rows(corridor_shared_breakline_audit_rows(self.document))

    def _set_shared_breakline_audit_rows(self, rows: list[dict[str, object]]) -> None:
        self.view_model.replace_rows("shared_breaklines", rows)
        summary = corridor_shared_breakline_audit_summary(self.document)
        status_label = getattr(self, "_breakline_audit_status_label", None)
        detail_label = getattr(self, "_breakline_audit_detail_label", None)
        if status_label is not None:
            title = str(summary.get("title", "") or "")
            status = str(summary.get("status", "") or "")
            status_label.setText(title)
            if status == "ready":
                status_label.setStyleSheet("QLabel { color: #14532d; font-weight: 700; }")
            elif status == "warning":
                status_label.setStyleSheet("QLabel { color: #92400e; font-weight: 700; }")
            else:
                status_label.setStyleSheet("QLabel { color: #4b5563; font-weight: 700; }")
        if detail_label is not None:
            detail_label.setText(str(summary.get("notes", "") or ""))
        if not hasattr(self, "_breakline_audit_table"):
            return
        self._breakline_audit_table.setRowCount(0)
        display_rows = shared_breakline_audit_display_rows(rows)
        self._breakline_audit_display_rows = display_rows
        for row in display_rows:
            row_index = self._breakline_audit_table.rowCount()
            self._breakline_audit_table.insertRow(row_index)
            geometry_match = int(row.get("geometry_match_count", 0) or 0)
            geometry_mismatch = int(row.get("geometry_mismatch_count", 0) or 0)
            mesh_match = int(row.get("mesh_match_count", 0) or 0)
            mesh_mismatch = int(row.get("mesh_mismatch_count", 0) or 0)
            values = [
                str(row.get("surface", "") or ""),
                str(row.get("status", "") or ""),
                f"{int(row.get('consumed', 0) or 0)}/{int(row.get('total', 0) or 0)}",
                f"{geometry_match}/{geometry_match + geometry_mismatch}",
                f"{mesh_match}/{mesh_match + mesh_mismatch}",
                str(row.get("missing_consumer_count", "") or "0"),
                str(row.get("mismatch_count", "") or "0"),
                str(row.get("reversed_edge_count", "") or "0"),
                str(row.get("role_summary", "") or row.get("material_summary", "") or ""),
                str(row.get("recommended_action", "") or ""),
                str(row.get("object_label", "") or row.get("object_name", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if col == 0:
                    item.setData(32, str(row.get("role", "") or ""))
                    item.setData(33, str(row.get("breakline_role_filter", "") or ""))
                    item.setData(34, str(row.get("material_filter", "") or ""))
                self._breakline_audit_table.setItem(row_index, col, item)
            self._apply_breakline_audit_row_style(row_index, str(row.get("status", "") or ""))
        if self._breakline_audit_table.rowCount() > 0:
            try:
                self._breakline_audit_table.selectRow(0)
            except Exception:
                pass
        _fit_build_corridor_table_to_rows(self._breakline_audit_table)
        self._sync_breakline_highlight_filter_options()

    def _sync_breakline_highlight_filter_options(self) -> None:
        combo = getattr(self, "_breakline_highlight_filter_combo", None)
        table = getattr(self, "_breakline_audit_table", None)
        if combo is None or table is None:
            return
        selected = table.selectionModel().selectedRows() if table.selectionModel() is not None else []
        selected_index = int(selected[0].row()) if selected else 0
        rows = list(getattr(self, "_breakline_audit_display_rows", []) or shared_breakline_audit_display_rows(corridor_shared_breakline_audit_rows(self.document)))
        try:
            row = rows[selected_index]
        except Exception:
            row = {}
        previous = combo.currentData()
        try:
            combo.blockSignals(True)
        except Exception:
            pass
        combo.clear()
        combo.addItem("All roles", ("", ""))
        current_role = str(row.get("breakline_role_filter", "") or "")
        if current_role:
            combo.addItem(f"Selected role: {current_role}", ("role", current_role))
            combo.setCurrentIndex(1)
        for key in _shared_breakline_summary_keys(str(row.get("material_summary", "") or "")):
            combo.addItem(f"Material: {key}", ("material", key))
        for key in _shared_breakline_summary_keys(str(row.get("role_summary", "") or "")):
            combo.addItem(f"Role: {key}", ("role", key))
        if previous and not current_role:
            for index in range(combo.count()):
                if combo.itemData(index) == previous:
                    combo.setCurrentIndex(index)
                    break
        try:
            combo.blockSignals(False)
        except Exception:
            pass

    def _apply_breakline_audit_row_style(self, row_index: int, status: str) -> None:
        table = getattr(self, "_breakline_audit_table", None)
        if table is None:
            return
        color = corridor_build_review_row_color("empty" if str(status or "") in {"warn", "warning"} else status)
        if color is None:
            return
        for col in range(table.columnCount()):
            item = table.item(row_index, col)
            if item is not None:
                try:
                    from freecad.Corridor_Road.qt_compat import QtGui

                    item.setBackground(QtGui.QBrush(QtGui.QColor(*color)))
                    item.setForeground(QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR)))
                except Exception:
                    pass

    def _show_selected_breakline_audit_row(self) -> None:
        table = getattr(self, "_breakline_audit_table", None)
        if table is None:
            return
        rows = table.selectionModel().selectedRows()
        if not rows:
            _show_message(self.form, "Build Parametric", "Select one Breakline Audit row first.")
            return
        role_filter = ""
        material_filter = ""
        combo = getattr(self, "_breakline_highlight_filter_combo", None)
        try:
            filter_kind, filter_value = combo.currentData() if combo is not None else ("", "")
        except Exception:
            filter_kind, filter_value = ("", "")
        if str(filter_kind or "") == "role":
            role_filter = str(filter_value or "")
        elif str(filter_kind or "") == "material":
            material_filter = str(filter_value or "")
        self._show_breakline_audit_row(int(rows[0].row()), role_filter=role_filter, material_filter=material_filter)

    def _show_breakline_audit_row(self, row_index: int, *, role_filter: str = "", material_filter: str = "") -> None:
        rows = list(getattr(self, "_breakline_audit_display_rows", []) or shared_breakline_audit_display_rows(corridor_shared_breakline_audit_rows(self.document)))
        try:
            row = rows[int(row_index)]
        except Exception:
            _show_message(self.form, "Build Parametric", "Breakline Audit row is not available.")
            return
        obj = _corridor_build_preview_object(self.document, str(row.get("role", "") or ""))
        if obj is None:
            _show_message(self.form, "Build Parametric", "Breakline Audit surface object is not available.")
            return
        row_kind = str(row.get("row_kind", "") or "")
        graph_edge_refs = [str(value or "") for value in list(row.get("graph_edge_refs", []) or []) if str(value or "")]
        if row_kind == "roundabout_clip_boundary_diagnostic":
            try:
                _remove_preview_object(self.document, "ReviewSharedBreaklineHighlight")
                _remove_preview_object(self.document, "ReviewIntersectionSharedBoundaryGraphHighlight")
                _remove_preview_object(self.document, "ReviewIntersectionSharedBoundaryGraphInternalSeamHighlight")
                _set_object_visibility(obj, True)
                _select_and_fit_object(obj)
                self._sync_visibility_checks()
            except Exception as exc:
                _show_message(self.form, "Build Parametric", f"Roundabout diagnostic boundary focus was not shown.\n{exc}")
                return
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Roundabout diagnostic boundary selected.",
                        f"Surface: {row.get('surface', '')}",
                        f"Reported role: {row.get('roundabout_clip_boundary_role', '')}",
                        "This row is not used as an ordinary surface clipping boundary.",
                        f"Actual clipping roles: {','.join(list(row.get('roundabout_actual_clip_boundary_roles', []) or [])) or 'none'}",
                        f"Surface Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
            return
        if row_kind == "boundary_loop_handoff" and (
            bool(row.get("boundary_loop_near_kept_warning", False))
            or int(row.get("intersection_exclusion_near_boundary_kept_triangle_count", 0) or 0) > 0
        ):
            try:
                highlight = show_intersection_exclusion_near_boundary_highlight(self.document, obj)
                self._sync_visibility_checks()
            except Exception as exc:
                _show_message(self.form, "Build Parametric", f"Intersection exclusion residual highlight was not shown.\n{exc}")
                return
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Intersection exclusion near-boundary kept highlight shown.",
                        f"Surface: {row.get('surface', '')}",
                        f"Audit: {row.get('status', '')}",
                        f"Near-kept triangles: {int(row.get('intersection_exclusion_near_boundary_kept_triangle_count', 0) or 0)}",
                        f"Recommended Action: {row.get('recommended_action', '')}",
                        f"Surface Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                        f"Highlight Object: {getattr(highlight, 'Label', getattr(highlight, 'Name', ''))}",
                    ]
                )
            )
            return
        if (row_kind == "graph" or row_kind == "graph_pair" or row_kind.startswith("graph_") or row_kind == "boundary_loop_handoff") and graph_edge_refs:
            try:
                highlight = show_intersection_shared_boundary_graph_highlight(
                    self.document,
                    obj,
                    edge_refs=graph_edge_refs,
                    highlight_kind="internal_seam" if row_kind == "graph_internal_seam" else "",
                )
                self._sync_visibility_checks()
            except Exception as exc:
                _show_message(self.form, "Build Parametric", f"Shared Boundary Graph highlight was not shown.\n{exc}")
                return
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Shared Boundary Graph highlight shown.",
                        f"Row: {row.get('surface', '')}",
                        f"Audit: {row.get('status', '')}",
                        f"Edges: {len(graph_edge_refs)}",
                        f"Recommended Action: {row.get('recommended_action', '')}",
                        f"Source Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                        f"Highlight Object: {getattr(highlight, 'Label', getattr(highlight, 'Name', ''))}",
                    ]
                )
            )
            return
        if not role_filter:
            role_filter = str(row.get("breakline_role_filter", "") or "")
        if not material_filter:
            material_filter = str(row.get("material_filter", "") or "")
        if _breakline_audit_surface_row_focuses_source_only(row) and not role_filter and not material_filter:
            try:
                _remove_preview_object(self.document, "ReviewSharedBreaklineHighlight")
                _remove_preview_object(self.document, "ReviewIntersectionSharedBoundaryGraphHighlight")
                _remove_preview_object(self.document, "ReviewIntersectionSharedBoundaryGraphInternalSeamHighlight")
                _set_object_visibility(obj, True)
                _select_and_fit_object(obj)
                self._sync_visibility_checks()
            except Exception as exc:
                _show_message(self.form, "Build Parametric", f"Breakline Audit surface focus was not shown.\n{exc}")
                return
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Breakline Audit surface focused.",
                        f"Surface: {row.get('surface', '')}",
                        f"Audit: {row.get('status', '')}",
                        "Shared breakline overlay was skipped for this surface summary row.",
                        "Use a specific role/detail row or filter to inspect breakline geometry.",
                        f"Surface Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
            return
        try:
            consumer_filter = _shared_breakline_consumer_for_review_role(str(row.get("role", "") or ""))
            highlight = show_shared_breakline_highlight(
                self.document,
                obj,
                role_filter=role_filter,
                material_filter=material_filter,
                consumer_filter=consumer_filter,
                clip_to_source_bounds=str(row.get("role", "") or "") in {"intersection", "intersection_slope", "intersection_tie_slope"},
            )
            self._sync_visibility_checks()
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Shared Breakline highlight was not shown.\n{exc}")
            return
        self._summary.setPlainText(
            "\n".join(
                [
                    "Shared Breakline Audit highlight shown.",
                    f"Surface: {row.get('surface', '')}",
                    f"Audit: {row.get('status', '')}",
                    f"Geometry: {int(row.get('geometry_match_count', 0) or 0)}/"
                    f"{int(row.get('geometry_match_count', 0) or 0) + int(row.get('geometry_mismatch_count', 0) or 0)}",
                    f"Mesh: {int(row.get('mesh_match_count', 0) or 0)}/"
                    f"{int(row.get('mesh_match_count', 0) or 0) + int(row.get('mesh_mismatch_count', 0) or 0)}",
                    f"Roles: {row.get('material_summary', '') or row.get('role_summary', '')}",
                    f"Filter: {material_filter or role_filter or consumer_filter or 'all'}",
                    f"Missing consumers: {int(row.get('missing_consumer_count', 0) or 0)}",
                    f"Recommended Action: {row.get('recommended_action', '')}",
                    f"Surface Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    f"Highlight Object: {getattr(highlight, 'Label', getattr(highlight, 'Name', ''))}",
                ]
            )
        )

    def _set_drainage_review_rows(self, rows: list[dict[str, object]]) -> None:
        if not hasattr(self, "_drainage_table"):
            return
        self._drainage_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._drainage_table.rowCount()
            self._drainage_table.insertRow(row_index)
            station = row.get("station", "")
            station_text = "" if station == "" else f"{float(station):.3f}"
            values = [
                str(row.get("context_label", "") or _drainage_review_context_label(row)),
                station_text,
                str(row.get("status", "") or ""),
                str(row.get("ditch_point_count", "") or "0"),
                str(row.get("left_count", "") or "0"),
                str(row.get("right_count", "") or "0"),
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if col == 1:
                    item.setData(32, str(row.get("marker_object", "") or ""))
                self._drainage_table.setItem(row_index, col, item)
            self._apply_drainage_row_style(row_index, str(row.get("status", "") or ""))
        _fit_build_corridor_table_to_rows(self._drainage_table)

    def _set_region_boundary_rows(self, rows: list[dict[str, object]]) -> None:
        if not hasattr(self, "_region_table"):
            return
        self._region_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._region_table.rowCount()
            self._region_table.insertRow(row_index)
            start = row.get("station_start", "")
            end = row.get("station_end", "")
            values = [
                _display_source_id(str(row.get("alignment_id", "") or ""), "alignment:"),
                str(row.get("region_id", "") or ""),
                "" if start == "" else f"{float(start):.3f}",
                "" if end == "" else f"{float(end):.3f}",
                str(row.get("assembly", "") or ""),
                str(row.get("structure", "") or ""),
                str(row.get("drainage", "") or ""),
                str(row.get("intersection", "") or ""),
                str(row.get("surface_status", "") or ""),
                str(row.get("boundary_status", "") or ""),
                _region_boundary_display_diagnostics(row),
            ]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if col == 1:
                    item.setData(32, str(row.get("region_id", "") or ""))
                self._region_table.setItem(row_index, col, item)
            self._apply_region_boundary_row_style(row_index, str(row.get("boundary_status", "") or ""))
        if self._region_table.rowCount() > 0:
            try:
                self._region_table.selectRow(0)
            except Exception:
                pass
        _fit_build_corridor_table_to_rows(self._region_table)
        self._sync_surface_transition_station_options_from_selected_region()

    def _refresh_region_boundary_rows(self) -> None:
        self._set_region_boundary_rows(corridor_region_boundary_rows(self.document))
        self._sync_surface_transition_station_options_from_selected_region()

    def _selected_region_id(self) -> str:
        table = getattr(self, "_region_table", None)
        if table is None:
            return ""
        row_index = -1
        try:
            rows = table.selectionModel().selectedRows()
            if rows:
                row_index = int(rows[0].row())
        except Exception:
            row_index = -1
        if row_index < 0:
            try:
                row_index = int(table.currentRow())
            except Exception:
                row_index = -1
        if row_index < 0:
            return ""
        item = table.item(row_index, 0)
        if item is None:
            return ""
        try:
            value = item.data(32)
            if value:
                return str(value)
        except Exception:
            pass
        return str(item.text() or "")

    def _sync_surface_transition_station_options_from_selected_region(self) -> None:
        self._set_surface_transition_boundary_options(
            corridor_surface_transition_boundary_options(self.document, region_id=self._selected_region_id())
        )

    def _set_surface_transition_boundary_options(self, options: list[dict[str, object]]) -> None:
        combo = getattr(self, "_surface_transition_boundary_combo", None)
        if combo is None:
            return
        current_transition_id = ""
        try:
            current_transition_id = str(combo.itemData(combo.currentIndex()) or "")
        except Exception:
            current_transition_id = ""
        try:
            combo.blockSignals(True)
            combo.clear()
            for option in list(options or []):
                label = str(option.get("label", "") or "")
                transition_id = str(option.get("transition_id", "") or "")
                combo.addItem(label, transition_id)
            if combo.count() > 0:
                selected_index = 0
                if current_transition_id:
                    for index in range(combo.count()):
                        if str(combo.itemData(index) or "") == current_transition_id:
                            selected_index = index
                            break
                combo.setCurrentIndex(selected_index)
        finally:
            try:
                combo.blockSignals(False)
            except Exception:
                pass
        self._sync_selected_surface_transition_boundary_spacing()

    def _set_surface_transition_rows(self, rows: list[dict[str, object]]) -> None:
        if not hasattr(self, "_surface_transition_table"):
            return
        self._surface_transition_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._surface_transition_table.rowCount()
            self._surface_transition_table.insertRow(row_index)
            boundary = row.get("boundary_station", "")
            spacing = row.get("sample_interval", "")
            values = [
                str(row.get("transition_id", "") or ""),
                "yes" if bool(row.get("enabled", True)) else "no",
                "" if boundary == "" else f"{float(boundary):.3f}",
                "" if spacing == "" else f"{float(spacing):.3f}",
                str(row.get("sample_count", "") or ""),
                str(row.get("from_region_ref", "") or ""),
                str(row.get("to_region_ref", "") or ""),
                str(row.get("from_surface", "") or ""),
                str(row.get("to_surface", "") or ""),
                str(row.get("target_surfaces", "") or ""),
                str(row.get("transition_mode", "") or ""),
                str(row.get("status", "") or ""),
                str(row.get("diagnostics", "") or ""),
            ]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if col == 0:
                    item.setData(32, str(row.get("transition_id", "") or ""))
                self._surface_transition_table.setItem(row_index, col, item)
            self._apply_surface_transition_row_style(row_index, str(row.get("status", "") or ""))
        if self._surface_transition_table.rowCount() > 0:
            try:
                self._surface_transition_table.selectRow(0)
            except Exception:
                pass
            self._sync_selected_surface_transition_row_controls()
        _fit_build_corridor_table_to_rows(self._surface_transition_table)

    def _sync_selected_surface_transition_row_controls(self) -> None:
        if not hasattr(self, "_surface_transition_table"):
            return
        rows = self._surface_transition_table.selectionModel().selectedRows()
        if not rows:
            return
        row_index = int(rows[0].row())
        transition_item = self._surface_transition_table.item(row_index, 0)
        spacing_item = self._surface_transition_table.item(row_index, 3)
        transition_id = str(transition_item.text() if transition_item is not None else "")
        if transition_id:
            self._set_surface_transition_boundary_combo_transition(transition_id)
        try:
            spacing = float(spacing_item.text()) if spacing_item is not None and spacing_item.text() else SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL
            self._set_surface_transition_spacing_controls(spacing)
        except Exception:
            pass

    def _set_surface_transition_boundary_combo_transition(self, transition_id: str) -> None:
        combo = getattr(self, "_surface_transition_boundary_combo", None)
        if combo is None:
            return
        target = str(transition_id or "")
        if not target:
            return
        for index in range(combo.count()):
            if str(combo.itemData(index) or "") == target:
                try:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(index)
                finally:
                    try:
                        combo.blockSignals(False)
                    except Exception:
                        pass
                return

    def _sync_selected_surface_transition_boundary_spacing(self) -> None:
        combo = getattr(self, "_surface_transition_boundary_combo", None)
        if combo is None or combo.count() <= 0:
            return
        transition_id = str(combo.itemData(combo.currentIndex()) or "")
        for option in corridor_surface_transition_boundary_options(self.document, region_id=self._selected_region_id()):
            if str(option.get("transition_id", "") or "") == transition_id:
                self._set_surface_transition_spacing_controls(float(option.get("sample_interval", SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL) or SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL))
                return

    def _set_surface_transition_spacing_controls(self, sample_interval: float) -> None:
        combo = getattr(self, "_surface_transition_spacing_combo", None)
        spin = getattr(self, "_surface_transition_spacing_spin", None)
        value = max(0.1, float(sample_interval or SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL))
        if spin is not None:
            try:
                spin.blockSignals(True)
                spin.setValue(value)
            finally:
                try:
                    spin.blockSignals(False)
                except Exception:
                    pass
        if combo is not None:
            selected_index = combo.count() - 1
            for index in range(combo.count()):
                data = combo.itemData(index)
                if data is not None and abs(float(data) - value) <= 1.0e-9:
                    selected_index = index
                    break
            try:
                combo.blockSignals(True)
                combo.setCurrentIndex(max(0, selected_index))
            finally:
                try:
                    combo.blockSignals(False)
                except Exception:
                    pass
        self._sync_surface_transition_custom_spacing_state()

    def _sync_surface_transition_custom_spacing_state(self) -> None:
        combo = getattr(self, "_surface_transition_spacing_combo", None)
        spin = getattr(self, "_surface_transition_spacing_spin", None)
        if combo is None or spin is None:
            return
        try:
            spin.setEnabled(combo.itemData(combo.currentIndex()) is None)
        except Exception:
            pass

    def _surface_transition_spacing_value(self) -> float:
        combo = getattr(self, "_surface_transition_spacing_combo", None)
        spin = getattr(self, "_surface_transition_spacing_spin", None)
        if combo is not None:
            try:
                data = combo.itemData(combo.currentIndex())
                if data is not None:
                    return max(0.1, float(data))
            except Exception:
                pass
        if spin is not None:
            return max(0.1, float(spin.value()))
        return SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL

    def _show_selected_region_boundary_row(self) -> None:
        rows = self._region_table.selectionModel().selectedRows() if hasattr(self, "_region_table") else []
        if not rows:
            _show_message(self.form, "Build Parametric", "Select one Region row first.")
            return
        self._show_region_boundary_row(int(rows[0].row()))

    def _show_region_boundary_row(self, row_index: int) -> None:
        try:
            rows = corridor_region_boundary_rows(self.document)
            row = rows[int(row_index)]
            obj = focus_corridor_region_boundary_row(self.document, int(row_index))
            self._sync_visibility_checks()
            try:
                self._region_table.selectRow(int(row_index))
            except Exception:
                pass
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Region surface object selected.",
                        f"Region: {row.get('region_id', '')}",
                        f"Station: {float(row.get('station_start', 0.0) or 0.0):.3f} -> {float(row.get('station_end', 0.0) or 0.0):.3f}",
                        f"Boundary: {row.get('boundary_status', '')}",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Region surface object was not selected.\n{exc}")

    def _create_transition_from_selected_region_boundary(self) -> None:
        rows = self._region_table.selectionModel().selectedRows() if hasattr(self, "_region_table") else []
        if not rows:
            _show_message(self.form, "Build Parametric", "Select one Region row first.")
            return
        try:
            row_index = int(rows[0].row())
            obj = create_corridor_surface_transition_from_region_boundary(
                self.document,
                row_index,
                sample_interval=self._surface_transition_spacing_value(),
            )
            self._set_surface_transition_rows(corridor_surface_transition_rows(self.document))
            self._sync_surface_transition_station_options_from_selected_region()
            transition_rows = corridor_surface_transition_rows(self.document)
            if transition_rows:
                self._surface_transition_table.selectRow(max(0, len(transition_rows) - 1))
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Surface Transition range stored.",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                        "Source: Build Corridor Region boundary review.",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Surface Transition range was not created.\n{exc}")

    def _create_transition_from_selected_boundary_option(self) -> None:
        combo = getattr(self, "_surface_transition_boundary_combo", None)
        if combo is None or combo.count() <= 0:
            _show_message(self.form, "Build Parametric", "No Region boundary station is available.")
            return
        try:
            boundary_index = int(combo.currentIndex())
            spacing = self._surface_transition_spacing_value()
            obj = create_or_update_corridor_surface_transition_for_boundary(
                self.document,
                boundary_index,
                sample_interval=spacing,
                region_id=self._selected_region_id(),
            )
            self._sync_surface_transition_station_options_from_selected_region()
            self._set_surface_transition_rows(corridor_surface_transition_rows(self.document))
            transition_id = str(combo.itemData(combo.currentIndex()) or "")
            self._set_surface_transition_boundary_combo_transition(transition_id)
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Surface Transition spacing stored.",
                        f"Boundary: {combo.currentText()}",
                        f"Spacing: {spacing:.3f} m",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Surface Transition spacing was not stored.\n{exc}")

    def _toggle_selected_surface_transition(self) -> None:
        rows = self._surface_transition_table.selectionModel().selectedRows() if hasattr(self, "_surface_transition_table") else []
        if not rows:
            _show_message(self.form, "Build Parametric", "Select one Surface Transition row first.")
            return
        try:
            obj = toggle_corridor_surface_transition_enabled(self.document, int(rows[0].row()))
            self._set_surface_transition_rows(corridor_surface_transition_rows(self.document))
            self._sync_surface_transition_station_options_from_selected_region()
            self._surface_transition_table.selectRow(int(rows[0].row()))
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Surface Transition enabled state updated.",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Surface Transition range was not updated.\n{exc}")

    def _show_drainage_review_row(self, row_index: int) -> None:
        try:
            rows = corridor_drainage_review_rows(self.document)
            row = rows[int(row_index)]
            obj = focus_corridor_drainage_review_row(self.document, int(row_index))
            self._sync_visibility_checks()
            try:
                self._drainage_table.selectRow(int(row_index))
            except Exception:
                pass
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Drainage station highlight shown.",
                        f"Station: {float(row.get('station', 0.0) or 0.0):.3f}" if row.get("station", "") != "" else "Station: n/a",
                        f"Status: {row.get('status', '')}",
                        f"Points: {row.get('ditch_point_count', 0)}",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Drainage station highlight was not shown.\n{exc}")

    def _show_slope_face_issue_row(self, row_index: int) -> None:
        try:
            issue_rows = corridor_slope_face_issue_rows(self.document)
            issue = issue_rows[int(row_index)]
            obj = focus_corridor_slope_face_issue(self.document, int(row_index))
            self._sync_visibility_checks()
            try:
                self._slope_issue_table.selectRow(int(row_index))
            except Exception:
                pass
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Slope Face fallback issue marker shown.",
                        f"Station: {issue.get('station_label', '')}",
                        f"Side: {issue.get('side', '')}",
                        f"Reason: {issue.get('reason', '')}",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Slope Face fallback issue was not shown.\n{exc}")

    def _show_intersection_contract_review_row(self, row_index: int) -> None:
        try:
            rows = corridor_intersection_contract_review_rows(self.document)
            row = rows[int(row_index)]
            obj = focus_corridor_intersection_contract_review_row(self.document, int(row_index))
            try:
                self._intersection_contract_table.selectRow(int(row_index))
            except Exception:
                pass
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Intersection contract review object focused.",
                        f"Contract: {row.get('contract_family', '')}",
                        f"ID: {row.get('row_id', '')}",
                        f"Status: {row.get('status', '')}",
                        f"Role: {row.get('role', '')}",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Intersection contract row was not focused.\n{exc}")

    def _focus_adjacent_slope_face_issue(self, direction: int) -> None:
        try:
            current_index = self._selected_slope_face_issue_row_index()
            target_index, obj = focus_adjacent_corridor_slope_face_issue(
                self.document,
                current_index=current_index,
                direction=direction,
            )
            issue = corridor_slope_face_issue_rows(self.document)[target_index]
            self._sync_visibility_checks()
            try:
                self._slope_issue_table.selectRow(int(target_index))
            except Exception:
                pass
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Slope Face fallback issue marker shown.",
                        f"Issue: {target_index + 1} / {len(corridor_slope_face_issue_rows(self.document))}",
                        f"Station: {issue.get('station_label', '')}",
                        f"Side: {issue.get('side', '')}",
                        f"Reason: {issue.get('reason', '')}",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Slope Face fallback issue was not shown.\n{exc}")

    def _selected_slope_face_issue_row_index(self) -> int:
        rows = self._slope_issue_table.selectionModel().selectedRows() if hasattr(self, "_slope_issue_table") else []
        if not rows:
            return -1
        return int(rows[0].row())

    def _show_selected_row(self) -> None:
        rows = self._review_table.selectionModel().selectedRows() if hasattr(self, "_review_table") else []
        if not rows:
            _show_message(self.form, "Build Parametric", "Select one review row first.")
            return
        self._show_review_row(int(rows[0].row()))

    def _show_review_row(self, row_index: int) -> None:
        try:
            obj = show_corridor_build_review_object(self.document, int(row_index))
            self._summary.setPlainText(f"Review object shown.\nObject: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}")
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Review object was not shown.\n{exc}")

    def _focus_guided_review_row(self, row_index: int) -> None:
        try:
            item = self._guided_table.item(int(row_index), 0)
            step_id = str(item.data(32) if item is not None else "")
            obj = focus_corridor_build_guided_review_step(
                self.document,
                step_id,
                supplemental_sampling_max_spacing=self._supplemental_sampling_max_spacing(),
                supplemental_sampling_tangent_delta_deg=self._supplemental_sampling_tangent_delta_deg(),
                supplemental_sampling_chord_deviation=self._supplemental_sampling_chord_deviation(),
            )
            self._sync_visibility_checks()
            self._sync_guided_visibility_checks()
            self._summary.setPlainText(
                f"Guided review step focused.\nStep: {step_id}\nObject: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}"
            )
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Guided review step was not focused.\n{exc}")

    def _set_preview_visibility(self, role: str, visible: bool) -> None:
        obj = set_corridor_build_preview_visibility(self.document, role, visible)
        if obj is None:
            return
        state = "shown" if visible else "hidden"
        self._summary.setPlainText(f"Preview {state}.\nObject: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}")

    def _set_daylight_contact_marker_visibility(self, visible: bool) -> None:
        obj = set_corridor_build_daylight_contact_marker_visibility(self.document, visible)
        if obj is None:
            return
        state = "shown" if visible else "hidden"
        self._summary.setPlainText(f"Daylight contact markers {state}.\nObject: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}")

    def _set_all_preview_visibility(self, visible: bool) -> None:
        count = set_all_corridor_build_preview_visibility(self.document, visible, include_issue_markers=True)
        self._sync_visibility_checks()
        state = "shown" if visible else "hidden"
        self._summary.setPlainText(f"Corridor previews {state}.\nObjects updated: {count}")

    def _set_visibility_group(self, group_id: str, visible: bool) -> None:
        count = set_corridor_build_visibility_group(self.document, group_id, bool(visible))
        self._sync_visibility_checks()
        state = "shown" if visible else "hidden"
        self._summary.setPlainText(f"Visibility group {state}.\nGroup: {group_id}\nObjects updated: {count}")

    def _sync_visibility_checks(self) -> None:
        if not hasattr(self, "_visibility_checks"):
            return
        for role, check in dict(self._visibility_checks).items():
            obj = _corridor_build_preview_object(self.document, role)
            enabled = obj is not None
            visible = _object_visibility(obj) if obj is not None else False
            try:
                check.blockSignals(True)
                check.setEnabled(enabled)
                check.setChecked(bool(visible))
                check.setToolTip(corridor_build_preview_visibility_note(self.document, role))
            finally:
                try:
                    check.blockSignals(False)
                except Exception:
                    pass
        self._sync_daylight_contact_marker_check()
        self._sync_guided_visibility_checks()
        self._sync_visibility_group_checks()

    def _sync_visibility_group_checks(self) -> None:
        checks = getattr(self, "_visibility_group_checks", None)
        if not checks:
            return
        for group_id, check in dict(checks).items():
            try:
                check.blockSignals(True)
                check.setChecked(corridor_build_visibility_group_visible(self.document, group_id))
            finally:
                try:
                    check.blockSignals(False)
                except Exception:
                    pass

    def _set_guided_visibility_checks(self, rows: list[dict[str, object]]) -> None:
        grid = getattr(self, "_guided_visibility_grid", None)
        if grid is None:
            return
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._guided_visibility_checks = {}
        for index, row in enumerate(list(rows or [])):
            step_id = str(row.get("step_id", "") or "").strip()
            if not step_id:
                continue
            title = str(row.get("title", "") or step_id)
            check = QtWidgets.QCheckBox(title)
            check.setToolTip(str(row.get("notes", "") or ""))
            check.toggled.connect(lambda checked, step_id=step_id: self._set_guided_review_visibility(step_id, checked))
            self._guided_visibility_checks[step_id] = check
            grid.addWidget(check, index // 2, index % 2)
        self._sync_guided_visibility_checks()

    def _set_guided_review_visibility(self, step_id: str, visible: bool) -> None:
        count = set_corridor_guided_review_step_visibility(self.document, step_id, bool(visible))
        self._sync_visibility_checks()
        state = "shown" if visible else "hidden"
        self._summary.setPlainText(f"Guided review object(s) {state}.\nStep: {step_id}\nObjects updated: {count}")

    def _sync_guided_visibility_checks(self) -> None:
        checks = getattr(self, "_guided_visibility_checks", None)
        if not checks:
            return
        for step_id, check in dict(checks).items():
            visible = corridor_guided_review_step_visibility(self.document, step_id)
            enabled = corridor_guided_review_step_available(self.document, step_id)
            try:
                check.blockSignals(True)
                check.setEnabled(enabled)
                check.setChecked(bool(visible))
            finally:
                try:
                    check.blockSignals(False)
                except Exception:
                    pass

    def _sync_daylight_contact_marker_check(self) -> None:
        check = getattr(self, "_daylight_contact_marker_check", None)
        if check is None:
            return
        obj = _corridor_build_daylight_contact_marker_object(self.document)
        if obj is None:
            return
        try:
            check.blockSignals(True)
            check.setChecked(_object_visibility(obj))
        finally:
            try:
                check.blockSignals(False)
            except Exception:
                pass

    def _show_daylight_contact_markers(self) -> bool:
        check = getattr(self, "_daylight_contact_marker_check", None)
        if check is None:
            return True
        try:
            return bool(check.isChecked())
        except Exception:
            return True

    def _show_preferred_review_row(self, rows: list[dict[str, object]]):
        row_index = preferred_corridor_build_review_row_index(rows)
        if row_index is None:
            return None
        try:
            return show_corridor_build_review_object(self.document, int(row_index))
        except Exception:
            return None

    def _apply_review_row_style(self, row_index: int, status: str) -> None:
        color = corridor_build_review_row_color(status)
        if color is None:
            return
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*color))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._review_table.columnCount())):
                item = self._review_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass

    def _apply_guided_row_style(self, row_index: int, status: str) -> None:
        color = corridor_build_review_row_color("empty" if str(status or "") == "warn" else status)
        if color is None:
            return
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*color))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._guided_table.columnCount())):
                item = self._guided_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass

    def _apply_slope_issue_row_style(self, row_index: int) -> None:
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_ROW_COLORS["empty"]))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._slope_issue_table.columnCount())):
                item = self._slope_issue_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass

    def _apply_intersection_contract_row_style(self, row_index: int, status: str) -> None:
        color = corridor_build_review_row_color("empty" if str(status or "") in {"warn", "warning"} else status)
        if color is None:
            return
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*color))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._intersection_contract_table.columnCount())):
                item = self._intersection_contract_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass

    def _apply_drainage_row_style(self, row_index: int, status: str) -> None:
        color = corridor_build_review_row_color("empty" if str(status or "") == "warn" else status)
        if color is None:
            return
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*color))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._drainage_table.columnCount())):
                item = self._drainage_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass

    def _apply_region_boundary_row_style(self, row_index: int, status: str) -> None:
        color = corridor_build_review_row_color("empty" if str(status or "") == "warn" else status)
        if color is None:
            return
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*color))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._region_table.columnCount())):
                item = self._region_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass

    def _apply_surface_transition_row_style(self, row_index: int, status: str) -> None:
        color_key = "missing" if str(status or "") == "disabled" else "empty" if str(status or "") in {"warn", "draft"} else "ready"
        if str(status or "") == "error":
            color_key = "empty"
        color = corridor_build_review_row_color(color_key)
        if color is None:
            return
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*color))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._surface_transition_table.columnCount())):
                item = self._surface_transition_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass

    # __TASK_PANEL_METHODS_END__


__all__ = [
    "BuildCorridorTaskPanelPresentation",
    "BuildCorridorViewModel",
    "V1BuildCorridorTaskPanel",
    "configure_build_corridor_task_panel_runtime",
]
