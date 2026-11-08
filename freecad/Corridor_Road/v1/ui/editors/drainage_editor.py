"""Drainage editor panel for CorridorRoad v1.

The panel edits the Drainage Policy, the Ditch Runs (which Assembly ditch drains which side of
which road over which stations), the Points (inlets and outfalls on a run, culverts crossing the
road) and the Links (which point drains into which). Nothing is written until Apply; opening the panel prefills the runs from the Regions and the
Assembly when the stored Drainage has none, and adding a suggestion only adds a table row.
"""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets
from freecad.Corridor_Road.v1.models.source.drainage_model import (
    DITCH_RUN_SIDES,
    DRAINAGE_POINT_KINDS,
    LOW_POINT_RULES,
    DitchRun,
    DrainageLink,
    DrainageModel,
    DrainagePoint,
    DrainagePolicy,
)
from freecad.Corridor_Road.v1.services.editing.drainage_editing_service import ditch_run_id, next_point_id
from freecad.Corridor_Road.v1.services.editing.drainage_flow_service import (
    CHECK_ERROR,
    add_downstream,
    add_upstream,
    build_flow_tree,
    flow_node_severity,
    trace_network,
)
from freecad.Corridor_Road.v1.ui.common.panel_width import fit_task_panel_width
from freecad.Corridor_Road.v1.ui.presentation.drainage_flow_tree_presentation import (
    LOOP_GROUP_TITLE,
    flow_group_title,
    flow_node_text,
    flow_tree_note,
)


def configure_drainage_editor_task_panel_runtime(bindings) -> None:
    """Bind command collaborators without importing the command module."""

    for name, value in dict(bindings or {}).items():
        globals()[name] = value


# Runtime collaborators, bound by the command module.
App = None
Gui = None
apply_v1_drainage_model = None
drainage_downhill_links = None
drainage_flow_result = None
drainage_flowlines = None
drainage_editor_inputs = None
drainage_status_text = None
drainage_suggestions = None
open_drainage_review = None
refresh_drainage_result = None

COLUMNS = ("ID", "Road", "Side", "Ditch", "Start STA", "End STA", "On")
ID_COLUMN, ROAD_COLUMN, SIDE_COLUMN, DITCH_COLUMN, START_COLUMN, END_COLUMN, ON_COLUMN = range(len(COLUMNS))
LOW_POINT_LABELS = {"require_inlet": "Needs an inlet or outfall", "allow_ponding": "May pond"}
POINT_COLUMNS = ("ID", "Kind", "Ditch Run", "STA")
POINT_ID_COLUMN, POINT_KIND_COLUMN, POINT_RUN_COLUMN, POINT_STATION_COLUMN = range(len(POINT_COLUMNS))
# A culvert crosses the road and collects from every run it meets, so it may name no run.
CROSSES_ROAD = ""
LINK_COLUMNS = ("ID", "From", "To")
LINK_ID_COLUMN, LINK_FROM_COLUMN, LINK_TO_COLUMN = range(len(LINK_COLUMNS))


class V1DrainageEditorTaskPanel:
    """Drainage Policy, Ditch Runs, Points and Links editor."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        inputs = drainage_editor_inputs(self.document)
        self._model: DrainageModel = inputs["model"]
        self._choices = list(inputs["choices"])
        self._alignment_ids = [value for value in inputs["alignment_ids"]] or [""]
        self._prefill: list[DitchRun] = list(inputs["prefill"])
        self._suggestions: list = []
        self._trace = None  # the Trace Network proposal while it waits for Accept or Discard
        self.form = fit_task_panel_width(self._build_ui())
        self._load(self._model)
        self._refresh_flow_tree()
        self._refresh_suggestions()
        if inputs["prefilled"]:
            self._set_status(
                f"{len(self._model.ditch_run_rows)} Ditch Run(s) filled from the Regions and the Assembly. "
                "Apply to keep them."
            )
        elif not self._choices:
            self._set_status("The Assembly has no ditch. Add a ditch Subassembly to the Assembly first.")
        else:
            self._set_status(drainage_status_text(self.document))

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self._apply(close_after=True)

    def reject(self):
        if _gui_available():
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("ParametricRoad v1 - Drainage")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # The Policy is its own tab so a short task panel cannot cut it off above the tables.
        policy_tab = QtWidgets.QWidget()
        policy_form = QtWidgets.QFormLayout(policy_tab)
        self._min_grade = QtWidgets.QDoubleSpinBox()
        self._min_grade.setRange(0.0, 20.0)
        self._min_grade.setDecimals(2)
        self._min_grade.setSingleStep(0.1)
        self._min_grade.setSuffix(" %")
        policy_form.addRow("Minimum flowline grade:", self._min_grade)
        self._max_spacing = QtWidgets.QDoubleSpinBox()
        self._max_spacing.setRange(0.0, 1000.0)
        self._max_spacing.setDecimals(1)
        self._max_spacing.setSingleStep(5.0)
        self._max_spacing.setSuffix(" m")
        policy_form.addRow("Maximum inlet spacing:", self._max_spacing)
        self._low_point_rule = QtWidgets.QComboBox()
        for rule in LOW_POINT_RULES:
            self._low_point_rule.addItem(LOW_POINT_LABELS.get(rule, rule), rule)
        policy_form.addRow("Low point:", self._low_point_rule)

        self._tabs = QtWidgets.QTabWidget()
        self._tabs.addTab(policy_tab, "Policy")
        runs_tab = QtWidgets.QWidget()
        runs_layout = QtWidgets.QVBoxLayout(runs_tab)
        runs_layout.addWidget(QtWidgets.QLabel("The Assembly ditches that drain the road"))
        self._table = QtWidgets.QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(list(COLUMNS))
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        try:
            self._table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._table.setColumnHidden(ROAD_COLUMN, len(self._alignment_ids) <= 1)
        runs_layout.addWidget(self._table, 1)

        edit_row = QtWidgets.QHBoxLayout()
        fill_button = QtWidgets.QPushButton("Fill from Assembly")
        fill_button.setToolTip("Replace the Ditch Runs with one run per Assembly ditch and side over the Region spans.")
        fill_button.clicked.connect(self._fill_from_assembly)
        edit_row.addWidget(fill_button)
        add_button = QtWidgets.QPushButton("Add Run")
        add_button.clicked.connect(lambda: self._append_row(None))
        edit_row.addWidget(add_button)
        delete_button = QtWidgets.QPushButton("Delete Run")
        delete_button.clicked.connect(self._delete_selected_row)
        edit_row.addWidget(delete_button)
        edit_row.addStretch(1)
        runs_layout.addLayout(edit_row)
        self._tabs.addTab(runs_tab, "Ditch Runs")
        self._flow_tab = self._build_flow_tab()
        self._tabs.addTab(self._flow_tab, "Flow")
        self._tabs.addTab(self._build_points_tab(), "Points")
        self._tabs.addTab(self._build_links_tab(), "Links")
        # Points name runs and Links name points, so their lists follow the other tabs
        self._tabs.currentChanged.connect(self._tab_changed)
        layout.addWidget(self._tabs, 1)

        self._status = QtWidgets.QPlainTextEdit()
        self._status.setReadOnly(True)
        self._status.setFixedHeight(160)
        layout.addWidget(self._status)

        action_row = QtWidgets.QHBoxLayout()
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        action_row.addWidget(apply_button)
        review_button = QtWidgets.QPushButton("Drainage Review")
        review_button.setToolTip("Close this panel and open Drainage Review. Apply first to keep your edits.")
        review_button.clicked.connect(lambda: open_drainage_review(self.document))
        action_row.addWidget(review_button)
        action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        action_row.addWidget(close_button)
        layout.addLayout(action_row)
        return widget

    def _build_flow_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.addWidget(QtWidgets.QLabel("Where the water goes: each point sits under the point it drains into"))
        self._flow_tree = QtWidgets.QTreeWidget()
        self._flow_tree.setHeaderHidden(True)
        self._flow_tree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._flow_tree.itemSelectionChanged.connect(self._flow_selection_changed)
        layout.addWidget(self._flow_tree, 1)
        continue_row = QtWidgets.QHBoxLayout()
        self._continue_buttons = []
        upstream_button = QtWidgets.QPushButton("Add Upstream")
        upstream_button.setToolTip("Add an inlet one step up the ditch from the selected point, draining into it. Press again to walk on.")
        upstream_button.clicked.connect(lambda: self._continue_flow(upstream=True))
        continue_row.addWidget(upstream_button)
        self._continue_buttons.append(upstream_button)
        downstream_button = QtWidgets.QPushButton("Add Downstream")
        downstream_button.setToolTip("Link the selected point, which drains nowhere, to the nearest lower point, or to a new outfall at the run end.")
        downstream_button.clicked.connect(lambda: self._continue_flow(upstream=False))
        continue_row.addWidget(downstream_button)
        self._continue_buttons.append(downstream_button)
        continue_row.addStretch(1)
        layout.addLayout(continue_row)
        trace_row = QtWidgets.QHBoxLayout()
        self._trace_button = QtWidgets.QPushButton("Trace Network")
        self._trace_button.setToolTip(
            "Propose the missing outfalls, inlets and links for the whole network. Nothing is added until you Accept."
        )
        self._trace_button.clicked.connect(self._trace_network)
        trace_row.addWidget(self._trace_button)
        self._accept_button = QtWidgets.QPushButton("Accept")
        self._accept_button.setToolTip("Add the proposed points and links to the tables; Apply keeps them.")
        self._accept_button.clicked.connect(self._accept_trace)
        trace_row.addWidget(self._accept_button)
        self._discard_button = QtWidgets.QPushButton("Discard")
        self._discard_button.clicked.connect(self._discard_trace)
        trace_row.addWidget(self._discard_button)
        trace_row.addStretch(1)
        layout.addLayout(trace_row)
        self._set_trace(None)
        self._flow_note = QtWidgets.QLabel("")
        self._flow_note.setWordWrap(True)
        layout.addWidget(self._flow_note)
        return tab

    def _tab_changed(self, _index: int) -> None:
        # Points name runs and Links name points, and the flow tree reads both tables
        self._refresh_reference_choices()
        if self._tabs.currentWidget() is self._flow_tab:
            self._refresh_flow_tree()

    def _refresh_flow_tree(self) -> None:
        """Rebuild the tree from the tables as they stand, edits not yet applied included."""

        self._flow_tree.clear()
        try:
            points, links = self._points(), self._links()
        except ValueError as exc:
            self._flow_note.setText(f"The tree needs a valid Points table: {exc}")
            return
        checks, link_rows, result_note = drainage_flow_result(self.document)
        proposal = self._trace
        tree = build_flow_tree(
            points + list(proposal.points if proposal else ()),
            links + list(proposal.links if proposal else ()),
            check_rows=checks,
            link_rows=link_rows,
            pending_point_ids=frozenset(point.point_id for point in (proposal.points if proposal else ())),
            pending_link_ids=frozenset(link.link_id for link in (proposal.links if proposal else ())),
        )
        by_road = len({node.alignment_ref for node in tree.roots}) > 1
        groups: dict[str, object] = {}
        for node in tree.roots:
            parent = self._flow_tree.invisibleRootItem()
            if by_road:
                if node.alignment_ref not in groups:
                    groups[node.alignment_ref] = QtWidgets.QTreeWidgetItem(self._flow_tree, [""])
                parent = groups[node.alignment_ref]
            self._add_flow_item(parent, node)
        for alignment_ref, group in groups.items():
            members = sum(1 + _descendants(group.child(index)) for index in range(group.childCount()))
            group.setText(0, flow_group_title(alignment_ref, members))
        if tree.loop_nodes:
            loop_group = QtWidgets.QTreeWidgetItem(self._flow_tree, [LOOP_GROUP_TITLE])
            for node in tree.loop_nodes:
                self._add_flow_item(loop_group, node)
        self._flow_tree.expandAll()
        self._flow_note.setText(
            flow_tree_note(
                point_count=tree.node_count,
                root_count=len(tree.roots),
                loop_count=len(tree.loop_nodes),
                result_note=result_note,
            )
        )

    def _add_flow_item(self, parent, node) -> None:
        item = QtWidgets.QTreeWidgetItem(parent, [flow_node_text(node)])
        item.setData(0, QtCore.Qt.UserRole, node.point_id)
        if node.pending:
            font = item.font(0)
            font.setItalic(True)
            item.setFont(0, font)
            item.setForeground(0, QtGui.QBrush(QtGui.QColor(0, 90, 160)))
            item.setToolTip(0, "Proposed by Trace Network: Accept adds it to the tables.")
        severity = flow_node_severity(node)
        if severity:
            colour = QtGui.QColor(176, 0, 32) if severity == CHECK_ERROR else QtGui.QColor(176, 96, 0)
            item.setForeground(0, QtGui.QBrush(colour))
            item.setToolTip(0, "\n".join(row.message for row in node.check_rows))
        for child in node.children:
            self._add_flow_item(item, child)

    def _continue_flow(self, *, upstream: bool) -> None:
        """Add the next point or link of the flow from the selected node; Apply keeps it."""

        items = self._flow_tree.selectedItems()
        point_id = str(items[0].data(0, QtCore.Qt.UserRole) or "") if items else ""
        if not point_id:
            self._set_status("Select a point in the tree first.")
            return
        try:
            points, links = self._points(), self._links()
        except ValueError as exc:
            self._set_status(str(exc))
            return
        flowlines, note = drainage_flowlines(self.document)
        if not flowlines:
            self._set_status(note)
            return
        if upstream:
            step = add_upstream(point_id, points, links, flowlines, float(self._max_spacing.value()))
        else:
            step = add_downstream(point_id, points, links, flowlines)
        if not step.added:
            self._set_status(step.message)
            return
        for point in step.points:
            self._append_point(point)
        for link in step.links:
            self._append_link(link)
        self._refresh_flow_tree()
        self._select_flow_node(step.select_point_id)
        self._set_status(f"{step.message} Apply to keep it.")

    def _set_trace(self, proposal) -> None:
        """Hold the proposal (or none) and enable only the buttons that make sense with it."""

        self._trace = proposal if proposal is not None and proposal.found else None
        pending = self._trace is not None
        self._accept_button.setEnabled(pending)
        self._discard_button.setEnabled(pending)
        self._trace_button.setEnabled(not pending)
        # Adding by hand while a proposal waits could clash with its ids
        for button in self._continue_buttons:
            button.setEnabled(not pending)

    def _trace_network(self) -> None:
        """Propose the missing network from the tables and the stored flowlines; Accept adds it."""

        try:
            points, links = self._points(), self._links()
        except ValueError as exc:
            self._set_status(str(exc))
            return
        flowlines, note = drainage_flowlines(self.document)
        if not flowlines:
            self._set_status(note)
            return
        proposal = trace_network(
            points,
            links,
            flowlines,
            low_point_rule=str(self._low_point_rule.currentData() or LOW_POINT_RULES[0]),
            max_inlet_spacing_m=float(self._max_spacing.value()),
        )
        self._set_trace(proposal)
        self._refresh_flow_tree()
        self._set_status(proposal.message)

    def _accept_trace(self) -> None:
        proposal = self._trace
        if proposal is None:
            return
        point_ids = self._point_ids()
        link_ids = {self._link_text(row, LINK_ID_COLUMN) for row in range(self._link_table.rowCount())}
        known = point_ids | {point.point_id for point in proposal.points}
        clash = any(point.point_id in point_ids for point in proposal.points) or any(
            link.link_id in link_ids or link.from_ref not in known or link.to_ref not in known for link in proposal.links
        )
        self._set_trace(None)
        if clash:
            self._refresh_flow_tree()
            self._set_status("The tables changed since the trace, so the proposal was dropped. Trace Network again.")
            return
        for point in proposal.points:
            self._append_point(point)
        for link in proposal.links:
            self._append_link(link)
        self._refresh_flow_tree()
        self._set_status(
            f"{len(proposal.points)} point(s) and {len(proposal.links)} link(s) added to the tables. Apply to keep them."
        )

    def _discard_trace(self) -> None:
        self._set_trace(None)
        self._refresh_flow_tree()
        self._set_status("The proposal was discarded.")

    def _select_flow_node(self, point_id: str) -> None:
        iterator = QtWidgets.QTreeWidgetItemIterator(self._flow_tree)
        while iterator.value():
            item = iterator.value()
            if str(item.data(0, QtCore.Qt.UserRole) or "") == point_id:
                self._flow_tree.setCurrentItem(item)
                return
            iterator += 1

    def _flow_selection_changed(self) -> None:
        """Select the point's row in the Points table and its outgoing Link in the Links table."""

        items = self._flow_tree.selectedItems()
        point_id = str(items[0].data(0, QtCore.Qt.UserRole) or "") if items else ""
        if not point_id:
            return
        for row in range(self._point_table.rowCount()):
            if self._point_text(row, POINT_ID_COLUMN) == point_id:
                self._point_table.selectRow(row)
                break
        self._link_table.clearSelection()
        for row in range(self._link_table.rowCount()):
            if self._link_text(row, LINK_FROM_COLUMN, combo=True) == point_id:
                self._link_table.selectRow(row)
                break

    def _build_points_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.addWidget(QtWidgets.QLabel("Inlets and outfalls on a Ditch Run; culverts crossing the road"))
        self._point_table = QtWidgets.QTableWidget(0, len(POINT_COLUMNS))
        self._point_table.setHorizontalHeaderLabels(list(POINT_COLUMNS))
        self._point_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        try:
            self._point_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        layout.addWidget(self._point_table, 1)
        point_row = QtWidgets.QHBoxLayout()
        for label, kind in (("Add Inlet", "inlet"), ("Add Outfall", "outfall"), ("Add Culvert", "culvert")):
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(lambda _checked=False, kind=kind: self._append_point(None, kind=kind))
            point_row.addWidget(button)
        delete_button = QtWidgets.QPushButton("Delete Point")
        delete_button.clicked.connect(self._delete_selected_points)
        point_row.addWidget(delete_button)
        point_row.addStretch(1)
        layout.addLayout(point_row)

        layout.addWidget(QtWidgets.QLabel("Suggestions from the Drainage checks"))
        self._suggestion_list = QtWidgets.QListWidget()
        self._suggestion_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        # A bounded list keeps the Add buttons below it on screen in a short task panel.
        self._suggestion_list.setMinimumHeight(70)
        self._suggestion_list.setMaximumHeight(150)
        layout.addWidget(self._suggestion_list)
        self._suggestion_note = QtWidgets.QLabel("")
        self._suggestion_note.setWordWrap(True)
        layout.addWidget(self._suggestion_note)
        suggestion_row = QtWidgets.QHBoxLayout()
        add_selected = QtWidgets.QPushButton("Add Selected Suggestions")
        add_selected.setToolTip("Add the selected suggestions as points; Apply keeps them.")
        add_selected.clicked.connect(lambda: self._add_suggestions(selected_only=True))
        suggestion_row.addWidget(add_selected)
        add_all = QtWidgets.QPushButton("Add All Suggestions")
        add_all.clicked.connect(lambda: self._add_suggestions(selected_only=False))
        suggestion_row.addWidget(add_all)
        suggestion_row.addStretch(1)
        layout.addLayout(suggestion_row)
        return tab

    def _build_links_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.addWidget(QtWidgets.QLabel("Which point drains into which; an inlet must drain somewhere"))
        self._link_table = QtWidgets.QTableWidget(0, len(LINK_COLUMNS))
        self._link_table.setHorizontalHeaderLabels(list(LINK_COLUMNS))
        self._link_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        try:
            self._link_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        layout.addWidget(self._link_table, 1)
        row = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add Link")
        add_button.clicked.connect(lambda: self._append_link(None))
        row.addWidget(add_button)
        downhill_button = QtWidgets.QPushButton("Link Downhill")
        downhill_button.setToolTip("Link every inlet that drains nowhere to the nearest lower point on its run.")
        downhill_button.clicked.connect(self._link_downhill)
        row.addWidget(downhill_button)
        delete_button = QtWidgets.QPushButton("Delete Link")
        delete_button.clicked.connect(self._delete_selected_links)
        row.addWidget(delete_button)
        row.addStretch(1)
        layout.addLayout(row)
        return tab

    def _append_link(self, link: DrainageLink | None) -> None:
        point_ids = sorted(self._point_ids())
        if link is None:
            used = {self._link_text(row, LINK_ID_COLUMN) for row in range(self._link_table.rowCount())}
            first = point_ids[0] if point_ids else ""
            second = point_ids[1] if len(point_ids) > 1 else first
            link = DrainageLink(next_point_id("link", used), first, second)
        row = self._link_table.rowCount()
        self._link_table.insertRow(row)
        id_item = QtWidgets.QTableWidgetItem(link.link_id)
        id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
        self._link_table.setItem(row, LINK_ID_COLUMN, id_item)
        self._link_table.setCellWidget(row, LINK_FROM_COLUMN, _combo(point_ids, link.from_ref))
        self._link_table.setCellWidget(row, LINK_TO_COLUMN, _combo(point_ids, link.to_ref))

    def _delete_selected_links(self) -> None:
        for row in sorted({index.row() for index in self._link_table.selectionModel().selectedRows()}, reverse=True):
            self._link_table.removeRow(row)

    def _link_downhill(self) -> None:
        try:
            added, note = drainage_downhill_links(self.document, self._points(), self._links())
        except ValueError as exc:
            self._set_status(str(exc))
            return
        for link in added:
            self._append_link(link)
        self._set_status(note)

    def _links(self) -> list[DrainageLink]:
        return [
            DrainageLink(
                self._link_text(row, LINK_ID_COLUMN),
                self._link_text(row, LINK_FROM_COLUMN, combo=True),
                self._link_text(row, LINK_TO_COLUMN, combo=True),
            )
            for row in range(self._link_table.rowCount())
        ]

    def _link_text(self, row: int, column: int, *, combo: bool = False) -> str:
        if combo:
            widget = self._link_table.cellWidget(row, column)
            return str(widget.currentText() if widget is not None else "").strip()
        item = self._link_table.item(row, column)
        return str(item.text() if item is not None else "").strip()

    def _refresh_reference_choices(self) -> None:
        self._refresh_point_run_choices()
        point_ids = sorted(self._point_ids())
        for row in range(self._link_table.rowCount()):
            for column in (LINK_FROM_COLUMN, LINK_TO_COLUMN):
                current = self._link_text(row, column, combo=True)
                self._link_table.setCellWidget(row, column, _combo(point_ids, current))

    def _append_point(self, point: DrainagePoint | None, *, kind: str = "inlet") -> None:
        if point is None:
            runs = self._run_ids()
            run_ref = CROSSES_ROAD if kind == "culvert" or not runs else runs[0]
            point = DrainagePoint(next_point_id(kind, self._point_ids()), kind, 0.0, ditch_run_ref=run_ref)
        row = self._point_table.rowCount()
        self._point_table.insertRow(row)
        id_item = QtWidgets.QTableWidgetItem(point.point_id)
        id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
        self._point_table.setItem(row, POINT_ID_COLUMN, id_item)
        self._point_table.setCellWidget(row, POINT_KIND_COLUMN, _combo(list(DRAINAGE_POINT_KINDS), point.kind))
        self._point_table.setCellWidget(row, POINT_RUN_COLUMN, _combo([CROSSES_ROAD, *self._run_ids()], point.ditch_run_ref))
        self._point_table.setItem(row, POINT_STATION_COLUMN, _station_item(point.station))

    def _delete_selected_points(self) -> None:
        for row in sorted({index.row() for index in self._point_table.selectionModel().selectedRows()}, reverse=True):
            self._point_table.removeRow(row)

    def _refresh_point_run_choices(self) -> None:
        runs = [CROSSES_ROAD, *self._run_ids()]
        for row in range(self._point_table.rowCount()):
            current = self._point_text(row, POINT_RUN_COLUMN, combo=True)
            self._point_table.setCellWidget(row, POINT_RUN_COLUMN, _combo(runs, current))

    def _refresh_suggestions(self) -> None:
        self._suggestions, note = drainage_suggestions(self.document)
        self._suggestion_list.clear()
        for row in self._suggestions:
            self._suggestion_list.addItem(f"{row.kind} | {row.ditch_run_ref} | STA {row.station:.3f} | {row.message}")
        self._suggestion_note.setText(note)

    def _add_suggestions(self, *, selected_only: bool) -> None:
        if not self._suggestions:
            # Say why nothing happens instead of reporting "0 added".
            self._set_status(self._suggestion_note.text() or "There are no suggestions to add.")
            return
        if selected_only and not self._suggestion_list.selectedItems():
            self._set_status("Select one or more suggestions first, or use Add All Suggestions.")
            return
        indexes = (
            sorted(self._suggestion_list.row(item) for item in self._suggestion_list.selectedItems())
            if selected_only
            else range(len(self._suggestions))
        )
        present = {(point.kind, point.ditch_run_ref, round(point.station, 3)) for point in self._points()}
        added = 0
        for index in indexes:
            row = self._suggestions[index]
            if (row.kind, row.ditch_run_ref, round(row.station, 3)) in present:
                continue
            self._append_point(DrainagePoint(next_point_id(row.kind, self._point_ids()), row.kind, row.station, ditch_run_ref=row.ditch_run_ref))
            added += 1
        self._set_status(f"{added} suggested point(s) added to the Points table. Apply to keep them.")

    def _run_ids(self) -> list[str]:
        return [self._text(row, ID_COLUMN) for row in range(self._table.rowCount())]

    def _point_ids(self) -> set[str]:
        return {self._point_text(row, POINT_ID_COLUMN) for row in range(self._point_table.rowCount())}

    def _points(self) -> list[DrainagePoint]:
        runs = {run.ditch_run_id: run for run in (self._run(row) for row in range(self._table.rowCount()))}
        points = []
        for row in range(self._point_table.rowCount()):
            run_ref = self._point_text(row, POINT_RUN_COLUMN, combo=True)
            run = runs.get(run_ref)
            station = _station(self._point_table.item(row, POINT_STATION_COLUMN), f"Point row {row + 1}: STA")
            points.append(
                DrainagePoint(
                    point_id=self._point_text(row, POINT_ID_COLUMN),
                    kind=self._point_text(row, POINT_KIND_COLUMN, combo=True),
                    station=station,
                    side=run.side if run is not None else "",
                    ditch_run_ref=run_ref,
                    # a point takes its run's road; a crossing culvert the first road
                    alignment_ref=run.alignment_ref if run is not None else self._alignment_ids[0],
                )
            )
        return points

    def _point_text(self, row: int, column: int, *, combo: bool = False) -> str:
        if combo:
            widget = self._point_table.cellWidget(row, column)
            return str(widget.currentText() if widget is not None else "").strip()
        item = self._point_table.item(row, column)
        return str(item.text() if item is not None else "").strip()

    def _load(self, model: DrainageModel) -> None:
        policy = model.policy
        self._min_grade.setValue(float(policy.min_grade_percent))
        self._max_spacing.setValue(float(policy.max_inlet_spacing_m))
        index = self._low_point_rule.findData(policy.low_point_rule)
        self._low_point_rule.setCurrentIndex(max(index, 0))
        self._set_runs(model.ditch_run_rows)
        self._point_table.setRowCount(0)
        for point in model.point_rows:
            self._append_point(point)
        self._link_table.setRowCount(0)
        for link in model.link_rows:
            self._append_link(link)

    def _set_runs(self, runs: list[DitchRun]) -> None:
        self._table.setRowCount(0)
        for run in list(runs or []):
            self._append_row(run)

    def _append_row(self, run: DitchRun | None) -> None:
        if run is None:
            run = self._new_run()
        row = self._table.rowCount()
        self._table.insertRow(row)
        id_item = QtWidgets.QTableWidgetItem(run.ditch_run_id)
        id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
        self._table.setItem(row, ID_COLUMN, id_item)
        self._table.setCellWidget(row, ROAD_COLUMN, _combo(self._alignment_ids, run.alignment_ref))
        self._table.setCellWidget(row, SIDE_COLUMN, _combo(list(DITCH_RUN_SIDES), run.side))
        self._table.setCellWidget(row, DITCH_COLUMN, _combo([choice.subassembly_ref for choice in self._choices], run.subassembly_ref))
        self._table.setItem(row, START_COLUMN, _station_item(run.station_start))
        self._table.setItem(row, END_COLUMN, _station_item(run.station_end))
        on_item = QtWidgets.QTableWidgetItem("")
        on_item.setFlags((on_item.flags() | QtCore.Qt.ItemIsUserCheckable) & ~QtCore.Qt.ItemIsEditable)
        on_item.setCheckState(QtCore.Qt.Checked if run.enabled else QtCore.Qt.Unchecked)
        self._table.setItem(row, ON_COLUMN, on_item)

    def _new_run(self) -> DitchRun:
        """A run on the first ditch and side, over the span the prefill gives that road."""

        choice = self._choices[0] if self._choices else None
        subassembly_ref = choice.subassembly_ref if choice is not None else ""
        side = choice.sides[0] if choice is not None and choice.sides else DITCH_RUN_SIDES[0]
        alignment_id = self._alignment_ids[0]
        spans = [run for run in self._prefill if run.alignment_ref == alignment_id] or self._prefill
        start = min((run.station_start for run in spans), default=0.0)
        end = max((run.station_end for run in spans), default=0.0)
        used = {self._text(row, ID_COLUMN) for row in range(self._table.rowCount())}
        index = 1
        road = alignment_id if len(self._alignment_ids) > 1 else ""
        while ditch_run_id(subassembly_ref, side, index, road=road) in used:
            index += 1
        run_id = ditch_run_id(subassembly_ref, side, index, road=road)
        return DitchRun(run_id, side, subassembly_ref, start, end, alignment_ref=alignment_id)

    def _fill_from_assembly(self) -> None:
        if not self._prefill:
            self._set_status("The Assembly has no ditch on any Region, so there is nothing to fill.")
            return
        self._set_runs(self._prefill)
        self._set_status(f"{len(self._prefill)} Ditch Run(s) filled from the Regions and the Assembly. Apply to keep them.")

    def _delete_selected_row(self) -> None:
        rows = sorted({index.row() for index in self._table.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self._table.removeRow(row)

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            model = self._model_from_panel()
            obj = apply_v1_drainage_model(document=self.document, drainage_model=model)
        except (ValueError, RuntimeError) as exc:
            self._set_status(str(exc))
            return False
        self._model = model
        try:
            evaluation = refresh_drainage_result(self.document)
        except RuntimeError as exc:
            evaluation = f"The Drainage was not evaluated: {exc}"
        self._set_status(
            f"Applied to {obj.Label}: {len(model.ditch_run_rows)} Ditch Run(s), {len(model.point_rows)} point(s), "
            f"{len(model.link_rows)} link(s).\n{evaluation}"
        )
        self._refresh_suggestions()
        self._refresh_flow_tree()
        if close_after and _gui_available():
            Gui.Control.closeDialog()
        return True

    def _model_from_panel(self) -> DrainageModel:
        policy = DrainagePolicy(
            min_grade_percent=float(self._min_grade.value()),
            max_inlet_spacing_m=float(self._max_spacing.value()),
            low_point_rule=str(self._low_point_rule.currentData() or LOW_POINT_RULES[0]),
        )
        return DrainageModel(
            schema_version=self._model.schema_version,
            project_id=self._model.project_id,
            label=self._model.label or "Drainage",
            drainage_model_id=self._model.drainage_model_id,
            policy=policy,
            ditch_run_rows=[self._run(row) for row in range(self._table.rowCount())],
            point_rows=self._points(),
            link_rows=self._links(),
        )

    def _run(self, row: int) -> DitchRun:
        on_item = self._table.item(row, ON_COLUMN)
        return DitchRun(
            ditch_run_id=self._text(row, ID_COLUMN),
            side=self._combo_text(row, SIDE_COLUMN),
            subassembly_ref=self._combo_text(row, DITCH_COLUMN),
            station_start=_station(self._table.item(row, START_COLUMN), f"Ditch Run row {row + 1}: Start STA"),
            station_end=_station(self._table.item(row, END_COLUMN), f"Ditch Run row {row + 1}: End STA"),
            alignment_ref=self._combo_text(row, ROAD_COLUMN),
            enabled=on_item is None or on_item.checkState() == QtCore.Qt.Checked,
        )

    def _text(self, row: int, column: int) -> str:
        item = self._table.item(row, column)
        return str(item.text() if item is not None else "").strip()

    def _combo_text(self, row: int, column: int) -> str:
        combo = self._table.cellWidget(row, column)
        return str(combo.currentText() if combo is not None else "").strip()

    def _set_status(self, text: str) -> None:
        self._status.setPlainText(str(text or ""))


def _descendants(item) -> int:
    return sum(1 + _descendants(item.child(index)) for index in range(item.childCount()))


def _combo(values: list[str], current: str):
    combo = QtWidgets.QComboBox()
    items = list(values)
    if current and current not in items:
        # keep a value the Assembly no longer has visible, so Apply reports it instead of hiding it
        items.append(current)
    combo.addItems(items)
    if current:
        combo.setCurrentText(current)
    return combo


# A station cell shows 3 decimals but keeps the exact value behind them: stations come from the
# Stations and Regions with more decimals, and writing the rounded text back would move a run's end
# off the last section or an outfall past the flowline's end.
_EXACT_STATION_ROLE = QtCore.Qt.UserRole


def _station_item(value: float):
    item = QtWidgets.QTableWidgetItem(f"{float(value):.3f}")
    item.setData(_EXACT_STATION_ROLE, float(value))
    return item


def _station(item, label: str) -> float:
    """The cell's exact station while its text is unchanged, else the number typed into it."""

    text = str(item.text() if item is not None else "").strip()
    exact = item.data(_EXACT_STATION_ROLE) if item is not None else None
    if exact is not None and text == f"{float(exact):.3f}":
        return float(exact)
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"{label} '{text}' is not a number.") from None


def _gui_available() -> bool:
    return bool(Gui is not None and getattr(App, "GuiUp", False))
