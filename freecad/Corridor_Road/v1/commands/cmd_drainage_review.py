"""Drainage review command for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
    import Part
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None
    Part = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.qt_compat import QtWidgets

from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_drainage import find_v1_drainage_model, to_drainage_model
from ..objects.obj_region import find_v1_region_model, to_region_model
from ..objects.obj_structure import find_v1_structure_model, to_structure_model
from ..services.evaluation.alignment_evaluation_service import AlignmentEvaluationService
from ..services.mapping.drainage_review_mapper import DrainageReviewMapper
from ..services.mapping.drainage_pipeline_geometry_mapper import build_drainage_pipeline_geometry_rows


class CmdV1DrainageReview:
    """Open a read-only Drainage Review panel."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("drainage_review.svg"),
            "MenuText": "Drainage Review",
            "ToolTip": "Review v1 Drainage Elements, Region assignments, Flow Routes, and Applied Section ditch context",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_drainage_review_command()


def run_v1_drainage_review_command(document=None):
    """Open the v1 Drainage Review task panel."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    panel = V1DrainageReviewTaskPanel(document=doc)
    if _gui_available() and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return panel


def build_drainage_review_output(document=None):
    """Build the read-only DrainageOutput payload from active document objects."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    alignment_model = to_alignment_model(find_v1_alignment(doc))
    drainage_model = to_drainage_model(find_v1_drainage_model(doc))
    region_model = to_region_model(find_v1_region_model(doc))
    structure_model = to_structure_model(find_v1_structure_model(doc))
    applied_section_set = to_applied_section_set(find_v1_applied_section_set(doc))
    project_id = (
        str(getattr(drainage_model, "project_id", "") or "")
        or str(getattr(region_model, "project_id", "") or "")
        or str(getattr(applied_section_set, "project_id", "") or "")
        or "corridorroad-v1"
    )
    coordinate_frame = _station_offset_coordinate_frame(doc)
    return DrainageReviewMapper().map(
        drainage_model=drainage_model,
        alignment_model=alignment_model,
        station_offset_to_xy=coordinate_frame.get("adapter"),
        coordinate_mode=str(coordinate_frame.get("coordinate_mode", "") or ""),
        region_model=region_model,
        structure_model=structure_model,
        applied_section_set=applied_section_set,
        project_id=project_id,
    )


def show_drainage_pipeline_candidate_preview_object(document=None, row_index: int = 0, output=None):
    """Create or update a 3D review object for one Drainage pipeline segment candidate."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Drainage pipeline candidate preview.")
    payload = output or build_drainage_review_output(doc)
    rows = [row for row in list(getattr(payload, "element_rows", []) or []) if row.kind == "pipeline_segment_candidate"]
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Pipeline candidate row index is out of range.")
    row = rows[row_index]
    coordinate_frame = _station_offset_coordinate_frame(doc)
    adapter = coordinate_frame.get("adapter")
    shape = _pipeline_candidate_shape(row, adapter=adapter)
    obj = doc.getObject("V1DrainagePipelineCandidatePreview")
    if obj is None:
        obj = doc.addObject("Part::Feature", "V1DrainagePipelineCandidatePreview")
    obj.Label = "Drainage Pipeline Candidate"
    obj.Shape = shape
    _set_preview_string_property(obj, "CRRecordKind", "v1_drainage_pipeline_candidate_preview")
    _set_preview_string_property(obj, "V1ObjectType", "V1DrainagePipelineCandidatePreview")
    _set_preview_string_property(obj, "FlowRouteRef", str(getattr(row, "label", "") or ""))
    _set_preview_string_property(obj, "CandidateStatus", _note_value(row.notes, "status"))
    _set_preview_string_property(obj, "FromConnectionPointRef", _note_value(row.notes, "from_connection_point_ref"))
    _set_preview_string_property(obj, "ToConnectionPointRef", _note_value(row.notes, "to_connection_point_ref"))
    _set_preview_string_property(obj, "CoordinateMode", str(coordinate_frame.get("coordinate_mode", "") or "station_offset_fallback"))
    _style_pipeline_candidate_preview(obj)
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(find_project(doc), obj)
    except Exception:
        pass
    try:
        doc.recompute()
    except Exception:
        pass
    _select_and_fit_object(obj)
    return obj


def show_drainage_pipeline_segment_preview_object(document=None, row_index: int = 0, output=None):
    """Create or update a 3D review object for one resolved Drainage pipeline segment."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Drainage pipeline segment preview.")
    payload = output or build_drainage_review_output(doc)
    rows = list(getattr(payload, "pipeline_segment_rows", []) or [])
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Pipeline segment row index is out of range.")
    row = rows[row_index]
    geometry_row = _pipeline_geometry_row_for_segment(payload, row, doc)
    shape = _pipeline_geometry_shape(geometry_row)
    obj = doc.getObject("V1DrainagePipelineSegmentPreview")
    if obj is None:
        obj = doc.addObject("Part::Feature", "V1DrainagePipelineSegmentPreview")
    obj.Label = "Drainage Pipeline Segment"
    obj.Shape = shape
    _set_preview_string_property(obj, "CRRecordKind", "v1_drainage_pipeline_segment_preview")
    _set_preview_string_property(obj, "V1ObjectType", "V1DrainagePipelineSegmentPreview")
    _set_preview_string_property(obj, "PipelineSegmentId", str(getattr(row, "pipeline_segment_id", "") or ""))
    _set_preview_string_property(obj, "FlowRouteRef", str(getattr(row, "flow_route_ref", "") or ""))
    _set_preview_string_property(obj, "FromConnectionPointRef", str(getattr(row, "from_connection_point_ref", "") or ""))
    _set_preview_string_property(obj, "ToConnectionPointRef", str(getattr(row, "to_connection_point_ref", "") or ""))
    _set_preview_string_property(obj, "CoordinateMode", str(getattr(geometry_row, "coordinate_mode", "") or "station_offset_fallback"))
    _style_pipeline_segment_preview(obj)
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(find_project(doc), obj)
    except Exception:
        pass
    try:
        doc.recompute()
    except Exception:
        pass
    _select_and_fit_object(obj)
    return obj


def show_drainage_pipeline_network_preview_object(document=None, row_index: int = 0, output=None):
    """Create or update a 3D review object for one resolved Drainage pipeline network."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Drainage pipeline network preview.")
    payload = output or build_drainage_review_output(doc)
    rows = list(getattr(payload, "pipeline_network_rows", []) or [])
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Pipeline network row index is out of range.")
    row = rows[row_index]
    geometry_rows = _pipeline_geometry_rows_for_network(payload, row)
    shape = _pipeline_network_geometry_shape(geometry_rows)
    obj = doc.getObject("V1DrainagePipelineNetworkPreview")
    if obj is None:
        obj = doc.addObject("Part::Feature", "V1DrainagePipelineNetworkPreview")
    obj.Label = "Drainage Pipeline Network"
    obj.Shape = shape
    _set_preview_string_property(obj, "CRRecordKind", "v1_drainage_pipeline_network_preview")
    _set_preview_string_property(obj, "V1ObjectType", "V1DrainagePipelineNetworkPreview")
    _set_preview_string_property(obj, "NetworkId", str(getattr(row, "network_id", "") or ""))
    _set_preview_string_property(obj, "FlowRouteRefs", ",".join(list(getattr(row, "flow_route_refs", []) or [])))
    _set_preview_string_property(obj, "PipelineSegmentRefs", ",".join(list(getattr(row, "pipeline_segment_refs", []) or [])))
    _set_preview_string_property(obj, "CoordinateMode", str(getattr(row, "coordinate_mode", "") or "station_offset_fallback"))
    _set_preview_string_property(obj, "FuseMode", _note_value(str(getattr(row, "notes", "") or ""), "fuse_mode"))
    _style_pipeline_network_preview(obj)
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(find_project(doc), obj)
    except Exception:
        pass
    try:
        doc.recompute()
    except Exception:
        pass
    _select_and_fit_object(obj)
    return obj


class V1DrainageReviewTaskPanel:
    """Read-only review panel for Drainage source and resolved section context."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.output = None
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
        widget.setWindowTitle("CorridorRoad v1 - Drainage Review")
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
        self._element_table = _table(["Kind", "Label", "Start STA", "End STA", "Source", "Notes"])
        self._flow_route_table = _table(["Flow Route", "From", "To", "Outlet", "Risk", "Chain", "Notes"])
        self._pipeline_table = _table(["Flow Route", "Status", "From CP", "To CP", "Start STA", "End STA", "Shape", "Diameter", "Notes"])
        self._pipeline_table.itemDoubleClicked.connect(lambda item: self._show_pipeline_candidate(item.row()))
        self._pipeline_segment_table = _table(["Segment", "Flow Route", "From CP", "To CP", "Start STA", "End STA", "Invert", "Shape", "Diameter", "Notes"])
        self._pipeline_segment_table.itemDoubleClicked.connect(lambda item: self._show_pipeline_segment(item.row()))
        self._pipeline_network_table = _table(["Network", "Segments", "Flow Routes", "Junctions", "Length", "Volume", "Status", "Notes"])
        self._pipeline_network_table.itemDoubleClicked.connect(lambda item: self._show_pipeline_network(item.row()))
        self._pipeline_junction_table = _table(["Kind", "Degree", "Point", "Structures", "Segments", "Flow Routes", "Mode", "Status", "Notes"])
        self._region_table = _table(["Region", "Element", "Start STA", "End STA", "Status", "Notes"])
        self._applied_table = _table(["Station", "Section", "Ditch Points", "Drainage Refs", "Notes"])
        self._tabs.addTab(self._element_table, "Elements")
        self._tabs.addTab(self._flow_route_table, "Flow Routes")
        self._tabs.addTab(self._pipeline_table, "Pipeline Candidates")
        self._tabs.addTab(self._pipeline_segment_table, "Pipeline Segments")
        self._tabs.addTab(self._pipeline_network_table, "Pipeline Networks")
        self._tabs.addTab(self._pipeline_junction_table, "Pipeline Junctions")
        self._tabs.addTab(self._region_table, "Region Assignments")
        self._tabs.addTab(self._applied_table, "Applied Sections")
        layout.addWidget(self._tabs, 1)

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
        return widget

    def refresh(self) -> None:
        self.output = build_drainage_review_output(self.document)
        _populate_summary_table(self._summary_table, self.output.summary_rows)
        _populate_element_table(self._element_table, [row for row in self.output.element_rows if row.kind == "drainage_element"])
        _populate_flow_route_table(self._flow_route_table, [row for row in self.output.element_rows if row.kind == "flow_route"])
        _populate_pipeline_table(self._pipeline_table, [row for row in self.output.element_rows if row.kind == "pipeline_segment_candidate"])
        _populate_pipeline_segment_table(self._pipeline_segment_table, self.output.pipeline_segment_rows)
        _populate_pipeline_network_table(self._pipeline_network_table, self.output.pipeline_network_rows)
        _populate_pipeline_junction_table(self._pipeline_junction_table, self.output.pipeline_junction_rows)
        _populate_region_table(self._region_table, [row for row in self.output.element_rows if row.kind == "region_assignment"])
        _populate_applied_table(
            self._applied_table,
            [row for row in self.output.element_rows if row.kind == "applied_section_ditch_context"],
        )
        self._status.setPlainText(_status_text(self.output))

    def _show_selected_pipeline_candidate(self) -> None:
        row_index = self._pipeline_table.currentRow()
        if row_index < 0:
            row_index = 0
        self._show_pipeline_candidate(row_index)

    def _show_pipeline_candidate(self, row_index: int) -> None:
        try:
            preview = show_drainage_pipeline_candidate_preview_object(self.document, row_index=row_index, output=self.output)
            self._status.setPlainText(_status_text(self.output) + f"\nPipeline candidate preview: {preview.Name}")
        except Exception as exc:
            self._status.setPlainText(_status_text(self.output) + f"\nPipeline candidate preview failed: {exc}")

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


def _table(headers: list[str]):
    table = QtWidgets.QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    try:
        table.horizontalHeader().setStretchLastSection(True)
    except Exception:
        pass
    return table


def _populate_summary_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        _append_items(table, [row.label, str(row.value), row.unit])


def _populate_element_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        _append_items(table, [row.kind, row.label, _format_float(row.station_start), _format_float(row.station_end), row.source_ref, row.notes])


def _populate_flow_route_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        _append_items(
            table,
            [
                row.label,
                _note_value(row.notes, "from_element_ref"),
                _note_value(row.notes, "to_element_ref"),
                _note_value(row.notes, "outlet_ref"),
                _note_value(row.notes, "risk_level"),
                _note_value(row.notes, "chain"),
                row.notes,
            ],
        )


def _populate_pipeline_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        _append_items(
            table,
            [
                row.label,
                _note_value(row.notes, "status"),
                _note_value(row.notes, "from_connection_point_ref"),
                _note_value(row.notes, "to_connection_point_ref"),
                _format_float(row.station_start),
                _format_float(row.station_end),
                _note_value(row.notes, "shape_kind"),
                _note_value(row.notes, "diameter"),
                row.notes,
            ],
        )


def _populate_pipeline_segment_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        _append_items(
            table,
            [
                getattr(row, "pipeline_segment_id", ""),
                getattr(row, "flow_route_ref", ""),
                getattr(row, "from_connection_point_ref", ""),
                getattr(row, "to_connection_point_ref", ""),
                _format_float(getattr(row, "station_start", 0.0)),
                _format_float(getattr(row, "station_end", 0.0)),
                _invert_text(getattr(row, "invert_start", None), getattr(row, "invert_end", None)),
                getattr(row, "shape_kind", ""),
                _format_float(getattr(row, "diameter", 0.0)),
                getattr(row, "notes", ""),
            ],
        )


def _populate_pipeline_network_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        _append_items(
            table,
            [
                getattr(row, "network_id", ""),
                str(int(getattr(row, "segment_count", 0) or 0)),
                ", ".join(list(getattr(row, "flow_route_refs", []) or [])),
                str(int(getattr(row, "junction_count", 0) or 0)),
                _format_float(getattr(row, "length", 0.0)),
                _format_float(getattr(row, "volume", 0.0)),
                getattr(row, "validation_status", ""),
                getattr(row, "notes", ""),
            ],
        )


def _populate_pipeline_junction_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        point = getattr(row, "point", (0.0, 0.0, 0.0))
        _append_items(
            table,
            [
                getattr(row, "junction_kind", ""),
                str(int(getattr(row, "degree", 0) or 0)),
                _point_text(point),
                _note_value(str(getattr(row, "notes", "") or ""), "structure_refs"),
                ", ".join(list(getattr(row, "pipeline_segment_refs", []) or [])),
                ", ".join(list(getattr(row, "flow_route_refs", []) or [])),
                getattr(row, "coordinate_mode", ""),
                getattr(row, "status", ""),
                getattr(row, "notes", ""),
            ],
        )


def _populate_region_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        status = _note_value(row.notes, "status")
        _append_items(table, [row.label, row.source_ref, _format_float(row.station_start), _format_float(row.station_end), status, row.notes])


def _populate_applied_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        _append_items(
            table,
            [
                _format_float(row.station_start),
                row.source_ref,
                _note_value(row.notes, "ditch_points"),
                _note_value(row.notes, "drainage_refs"),
                row.notes,
            ],
        )


def _pipeline_candidate_shape(row, *, adapter=None):
    station_start = float(getattr(row, "station_start", 0.0) or 0.0)
    station_end = float(getattr(row, "station_end", station_start) or station_start)
    from_offset = _note_float(row.notes, "from_offset", 0.0)
    to_offset = _note_float(row.notes, "to_offset", from_offset)
    invert_start = _note_float(row.notes, "invert_start", 0.0)
    invert_end = _note_float(row.notes, "invert_end", invert_start)
    diameter = max(_note_float(row.notes, "diameter", 0.0), 0.2)
    point0 = _station_offset_vector(station_start, from_offset, invert_start, adapter=adapter)
    point1 = _station_offset_vector(station_end, to_offset, invert_end, adapter=adapter)
    direction = point1.sub(point0)
    length = direction.Length
    if length <= 1.0e-9:
        return Part.makeSphere(diameter / 2.0, point0)
    status = _note_value(row.notes, "status")
    if status == "ready":
        try:
            return Part.makeCylinder(diameter / 2.0, length, point0, direction)
        except Exception:
            pass
    return Part.makePolygon([point0, point1])


def _pipeline_geometry_shape(row):
    points = [
        App.Vector(float(point[0]), float(point[1]), float(point[2]))
        for point in list(getattr(row, "centerline_points", []) or [])
        if len(point) >= 3
    ]
    diameter = max(float(getattr(row, "diameter", 0.0) or 0.0), 0.2)
    if not points:
        return Part.Shape()
    if len(points) == 1:
        return Part.makeSphere(diameter / 2.0, points[0])
    shapes = []
    for point0, point1 in zip(points, points[1:]):
        direction = point1.sub(point0)
        length = direction.Length
        if length <= 1.0e-9:
            continue
        try:
            shapes.append(Part.makeCylinder(diameter / 2.0, length, point0, direction))
        except Exception:
            try:
                shapes.append(Part.makePolygon([point0, point1]))
            except Exception:
                pass
    if not shapes:
        return Part.makePolygon(points)
    if len(shapes) == 1:
        return shapes[0]
    return Part.Compound(shapes)


def _pipeline_geometry_row_for_segment(output, segment_row, document):
    segment_id = str(getattr(segment_row, "pipeline_segment_id", "") or "")
    for row in list(getattr(output, "pipeline_geometry_rows", []) or []):
        if str(getattr(row, "pipeline_segment_id", "") or "") == segment_id:
            return row
    alignment_model = to_alignment_model(find_v1_alignment(document))
    coordinate_frame = _station_offset_coordinate_frame(document)
    rows = build_drainage_pipeline_geometry_rows(
        [segment_row],
        alignment_model=alignment_model,
        station_offset_to_xy=coordinate_frame.get("adapter"),
        coordinate_mode=str(coordinate_frame.get("coordinate_mode", "") or ""),
    )
    if rows:
        return rows[0]
    raise RuntimeError("Pipeline segment geometry row could not be built.")


def _pipeline_geometry_rows_for_network(output, network_row):
    solid_refs = set(str(value) for value in list(getattr(network_row, "solid_row_refs", []) or []) if str(value))
    geometry_refs = {
        str(getattr(row, "geometry_row_ref", "") or "")
        for row in list(getattr(output, "pipeline_solid_rows", []) or [])
        if str(getattr(row, "solid_row_id", "") or "") in solid_refs
    }
    rows = [
        row for row in list(getattr(output, "pipeline_geometry_rows", []) or [])
        if str(getattr(row, "geometry_row_id", "") or "") in geometry_refs
    ]
    if rows:
        return rows
    segment_refs = set(str(value) for value in list(getattr(network_row, "pipeline_segment_refs", []) or []) if str(value))
    rows = [
        row for row in list(getattr(output, "pipeline_geometry_rows", []) or [])
        if str(getattr(row, "pipeline_segment_id", "") or "") in segment_refs
    ]
    if rows:
        return rows
    raise RuntimeError("Pipeline network geometry rows could not be resolved.")


def _pipeline_network_geometry_shape(rows):
    shapes = []
    for row in list(rows or []):
        shape = _pipeline_geometry_shape(row)
        if shape is not None:
            shapes.append(shape)
    if not shapes:
        return Part.Shape()
    if len(shapes) == 1:
        return shapes[0]
    return Part.Compound(shapes)


def _station_offset_adapter(document):
    return _station_offset_coordinate_frame(document).get("adapter")


def _station_offset_coordinate_frame(document) -> dict[str, object]:
    centerline_frame = _centerline3d_coordinate_frame(document)
    if centerline_frame is not None:
        return centerline_frame
    alignment_obj = find_v1_alignment(document)
    alignment_model = to_alignment_model(alignment_obj) if alignment_obj is not None else None
    if alignment_model is None:
        return {"adapter": None, "coordinate_mode": "station_offset_fallback"}
    try:
        return {
            "adapter": AlignmentEvaluationService().station_offset_adapter(alignment_model),
            "coordinate_mode": "alignment_station_offset",
        }
    except Exception:
        return {"adapter": None, "coordinate_mode": "station_offset_fallback"}


def _centerline3d_coordinate_frame(document) -> dict[str, object] | None:
    try:
        from .cmd_centerline3d import build_document_centerline3d_result
        from ..services.evaluation import Centerline3DFrameService

        result = build_document_centerline3d_result(document)
    except Exception:
        return None
    point_rows = list(getattr(result, "point_rows", []) or [])
    if str(getattr(result, "status", "") or "") != "ready" or len(point_rows) < 2:
        return None
    frame_service = Centerline3DFrameService()

    def _adapter(station: float, offset: float) -> tuple[float, float]:
        frame = frame_service.resolve_station_offset(result, station, offset)
        return float(frame.x), float(frame.y)

    return {
        "adapter": _adapter,
        "coordinate_mode": "centerline3d_result",
    }


def _station_offset_vector(station: float, offset: float, z: float, *, adapter=None):
    if adapter is not None:
        try:
            x, y = adapter(float(station), float(offset))
            return App.Vector(float(x), float(y), float(z))
        except Exception:
            pass
    return App.Vector(float(station), float(offset), float(z))


def _style_pipeline_candidate_preview(obj) -> None:
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return
        vobj.Visibility = True
        vobj.ShapeColor = (0.0, 0.85, 0.95)
        vobj.LineColor = (0.0, 0.95, 0.55)
        vobj.PointColor = (0.0, 0.95, 0.55)
        vobj.Transparency = 15
        vobj.LineWidth = 5.0
    except Exception:
        pass


def _style_pipeline_segment_preview(obj) -> None:
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return
        vobj.Visibility = True
        vobj.ShapeColor = (0.0, 0.75, 0.95)
        vobj.LineColor = (0.0, 0.95, 0.85)
        vobj.PointColor = (0.0, 0.95, 0.85)
        vobj.Transparency = 5
        vobj.LineWidth = 6.0
    except Exception:
        pass


def _style_pipeline_network_preview(obj) -> None:
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return
        vobj.Visibility = True
        vobj.ShapeColor = (0.1, 0.9, 0.7)
        vobj.LineColor = (0.0, 1.0, 0.45)
        vobj.PointColor = (0.0, 1.0, 0.45)
        vobj.Transparency = 0
        vobj.LineWidth = 7.0
    except Exception:
        pass


def _set_preview_string_property(obj, name: str, value: str) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyString", name, "Drainage Review", name)
        except Exception:
            pass
    try:
        setattr(obj, name, str(value or ""))
    except Exception:
        pass


def _select_and_fit_object(obj) -> None:
    if obj is None or Gui is None:
        return
    try:
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(obj)
    except Exception:
        pass
    try:
        view = getattr(getattr(Gui, "ActiveDocument", None), "ActiveView", None)
        if view is not None and hasattr(view, "fitSelection"):
            view.fitSelection()
    except Exception:
        pass


def _append_items(table, values: list[object]) -> None:
    index = table.rowCount()
    table.insertRow(index)
    for column, value in enumerate(values):
        table.setItem(index, column, QtWidgets.QTableWidgetItem(str(value or "")))


def _status_text(output) -> str:
    summary = {row.summary_id: row.value for row in list(getattr(output, "summary_rows", []) or [])}
    region_issues = int(summary.get("summary:region-assignment-issues", 0) or 0)
    flow_routes = int(summary.get("summary:flow-routes", 0) or 0)
    pipeline_candidates = int(summary.get("summary:pipeline-segment-candidates", 0) or 0)
    pipeline_segments = int(summary.get("summary:pipeline-segments", 0) or 0)
    pipeline_geometries = int(summary.get("summary:pipeline-geometries", 0) or 0)
    pipeline_solids = int(summary.get("summary:pipeline-solid-candidates", 0) or 0)
    pipeline_solid_length = float(summary.get("summary:pipeline-solid-length", 0.0) or 0.0)
    pipeline_networks = int(summary.get("summary:pipeline-networks", 0) or 0)
    pipeline_network_length = float(summary.get("summary:pipeline-network-length", 0.0) or 0.0)
    pipeline_junctions = int(summary.get("summary:pipeline-junctions", 0) or 0)
    pipeline_terminals = int(summary.get("summary:pipeline-terminals", 0) or 0)
    ditch_points = int(summary.get("summary:ditch-surface-points", 0) or 0)
    ditch_with_refs = int(summary.get("summary:ditch-surface-points-with-drainage", 0) or 0)
    lines = [
        f"Drainage Review rows: {len(list(getattr(output, 'element_rows', []) or []))}",
        f"Source refs: {', '.join(list(getattr(output, 'source_refs', []) or []))}",
    ]
    if region_issues:
        lines.append(f"Warnings: {region_issues} Drainage Element Region assignment issue(s).")
    if flow_routes:
        lines.append(f"Flow Routes: {flow_routes} source route(s) are available for review.")
    if pipeline_candidates:
        lines.append(f"Pipeline Candidates: {pipeline_candidates} route segment candidate(s) resolved from Structure connection points.")
    if pipeline_segments:
        lines.append(f"Pipeline Segments: {pipeline_segments} ready segment result(s) are available for output preview.")
    if pipeline_geometries:
        lines.append(f"Pipeline Geometry: {pipeline_geometries} centerline geometry row(s) are available.")
    if pipeline_solids:
        lines.append(f"Pipeline Solids: {pipeline_solids} capped candidate(s), length={pipeline_solid_length:.3f} m.")
    if pipeline_networks:
        lines.append(f"Pipeline Networks: {pipeline_networks} network candidate(s), length={pipeline_network_length:.3f} m.")
    if pipeline_junctions or pipeline_terminals:
        lines.append(f"Pipeline Junctions: {pipeline_junctions} junction(s), {pipeline_terminals} terminal(s).")
    if ditch_points and ditch_with_refs < ditch_points:
        lines.append(f"Warnings: {ditch_points - ditch_with_refs} ditch_surface point(s) have no drainage_ref.")
    if len(lines) == 2:
        lines.append("No blocking Drainage Review diagnostics in the first-slice checks.")
    return "\n".join(lines)


def _note_value(notes: str, key: str) -> str:
    prefix = str(key or "") + "="
    for token in str(notes or "").split(";"):
        if token.startswith(prefix):
            return token[len(prefix) :]
    return ""


def _note_float(notes: str, key: str, fallback: float = 0.0) -> float:
    value = _note_value(notes, key)
    if value == "":
        return float(fallback)
    try:
        return float(value)
    except Exception:
        return float(fallback)


def _format_float(value: object) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "0.000"


def _point_text(point: object) -> str:
    try:
        values = list(point)
        return f"{float(values[0]):.3f}, {float(values[1]):.3f}, {float(values[2]):.3f}"
    except Exception:
        return "0.000, 0.000, 0.000"


def _invert_text(start: object, end: object) -> str:
    return f"{_format_float(start)} -> {_format_float(end)}"


def _gui_available() -> bool:
    return bool(Gui is not None and getattr(App, "GuiUp", False))


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1DrainageReview", CmdV1DrainageReview())
