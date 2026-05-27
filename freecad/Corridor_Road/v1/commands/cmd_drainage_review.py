"""Drainage review command for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import replace

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
from ..objects.obj_quantity import find_v1_quantity_model, to_quantity_model
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
    quantity_model = to_quantity_model(find_v1_quantity_model(doc))
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
        quantity_model=quantity_model,
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
    status = _note_value(row.notes, "status")
    _set_preview_string_property(obj, "CandidateStatus", status)
    _set_preview_string_property(obj, "IssueKind", "drainage_pipeline_candidate")
    _set_preview_string_property(obj, "IssueStatus", status)
    _set_preview_string_property(obj, "DisplayMode", "drainage_pipeline_candidate_ready" if status == "ready" else "drainage_pipeline_issue")
    _set_preview_string_property(obj, "FromElementRef", _note_value(row.notes, "from_element_ref"))
    _set_preview_string_property(obj, "ToElementRef", _note_value(row.notes, "to_element_ref"))
    _set_preview_string_property(obj, "FromConnectionPointRef", _note_value(row.notes, "from_connection_point_ref"))
    _set_preview_string_property(obj, "ToConnectionPointRef", _note_value(row.notes, "to_connection_point_ref"))
    _set_preview_string_property(obj, "CoordinateMode", str(coordinate_frame.get("coordinate_mode", "") or "station_offset_fallback"))
    _style_pipeline_candidate_preview(obj, status=status)
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


def show_drainage_flow_route_issue_preview_object(document=None, row_index: int = 0, output=None):
    """Create or update a 3D review object for one Flow Route graph issue."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Drainage Flow Route issue preview.")
    payload = output or build_drainage_review_output(doc)
    rows = [row for row in list(getattr(payload, "element_rows", []) or []) if row.kind == "flow_route_issue"]
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Flow Route issue row index is out of range.")
    row = rows[row_index]
    coordinate_frame = _station_offset_coordinate_frame(doc)
    adapter = coordinate_frame.get("adapter")
    shape = _flow_route_issue_shape(row, adapter=adapter)
    obj = doc.getObject("V1DrainageFlowRouteIssuePreview")
    if obj is None:
        obj = doc.addObject("Part::Feature", "V1DrainageFlowRouteIssuePreview")
    obj.Label = "Drainage Flow Route Issue"
    obj.Shape = shape
    _set_preview_string_property(obj, "CRRecordKind", "v1_drainage_flow_route_issue_preview")
    _set_preview_string_property(obj, "V1ObjectType", "V1DrainageFlowRouteIssuePreview")
    _set_preview_string_property(obj, "IssueKind", str(getattr(row, "label", "") or "flow_route_issue"))
    _set_preview_string_property(obj, "IssueStatus", _note_value(row.notes, "severity") or "warning")
    _set_preview_string_property(obj, "DisplayMode", "drainage_flow_route_issue")
    _set_preview_string_property(obj, "FlowRouteRefs", str(getattr(row, "source_ref", "") or ""))
    _set_preview_string_property(obj, "FromElementRef", _note_value(row.notes, "from_element_ref"))
    _set_preview_string_property(obj, "OutletRefs", _note_value(row.notes, "outlet_refs"))
    _set_preview_string_property(obj, "CoordinateMode", str(coordinate_frame.get("coordinate_mode", "") or "station_offset_fallback"))
    _style_flow_route_issue_preview(obj)
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


def show_drainage_pipeline_networks_preview_object(document=None, output=None):
    """Create or update a 3D review object for all resolved Drainage pipeline networks."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Drainage pipeline network preview.")
    payload = output or build_drainage_review_output(doc)
    rows = list(getattr(payload, "pipeline_network_rows", []) or [])
    if not rows:
        raise RuntimeError("No resolved Drainage pipeline network is available.")
    _refresh_structure_preview_for_pipeline_network(doc)
    shapes = []
    network_ids: list[str] = []
    flow_route_refs: list[str] = []
    segment_refs: list[str] = []
    coordinate_modes: list[str] = []
    linked_objects: list[object] = []
    linked_connection_points: list[object] = []
    for row in rows:
        geometry_rows = _pipeline_geometry_rows_for_network(payload, row)
        geometry_rows = _geometry_rows_snapped_to_structure_previews(doc, payload, geometry_rows)
        shape = _pipeline_network_geometry_shape(geometry_rows)
        if shape is not None and not getattr(shape, "isNull", lambda: False)():
            shapes.append(shape)
        linked_objects.extend(_create_pipeline_geometry_preview_objects(doc, geometry_rows))
        linked_connection_points.extend(_create_pipeline_connection_point_preview_objects(doc, payload, geometry_rows))
        network_ids.append(str(getattr(row, "network_id", "") or ""))
        flow_route_refs.extend(str(value) for value in list(getattr(row, "flow_route_refs", []) or []) if str(value))
        segment_refs.extend(str(value) for value in list(getattr(row, "pipeline_segment_refs", []) or []) if str(value))
        coordinate_modes.append(str(getattr(row, "coordinate_mode", "") or "station_offset_fallback"))
    if not shapes:
        raise RuntimeError("Drainage pipeline network geometry could not be built.")
    obj = doc.getObject("V1DrainagePipelineNetworksPreview")
    if obj is None:
        obj = doc.addObject("Part::Feature", "V1DrainagePipelineNetworksPreview")
    obj.Label = "Drainage Pipeline Networks"
    obj.Shape = shapes[0] if len(shapes) == 1 else Part.Compound(shapes)
    _set_preview_string_property(obj, "CRRecordKind", "v1_drainage_pipeline_networks_preview")
    _set_preview_string_property(obj, "V1ObjectType", "V1DrainagePipelineNetworksPreview")
    _set_preview_string_property(obj, "NetworkIds", ",".join(_unique_text_values(network_ids)))
    _set_preview_string_property(obj, "FlowRouteRefs", ",".join(_unique_text_values(flow_route_refs)))
    _set_preview_string_property(obj, "PipelineSegmentRefs", ",".join(_unique_text_values(segment_refs)))
    _set_preview_string_property(obj, "ConnectionPointRefs", ",".join(_unique_text_values([str(getattr(item, "ConnectionPointRef", "") or "") for item in linked_connection_points])))
    _set_preview_string_property(obj, "LinkedPreviewObjects", ",".join(_unique_text_values([item.Name for item in [*linked_objects, *linked_connection_points]])))
    _set_preview_string_property(obj, "NetworkCount", str(len(rows)))
    _set_preview_string_property(obj, "CoordinateMode", ",".join(_unique_text_values(coordinate_modes)))
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


def _refresh_structure_preview_for_pipeline_network(document) -> None:
    structure_model = to_structure_model(find_v1_structure_model(document))
    if structure_model is None:
        return
    try:
        from .cmd_structure_editor import show_v1_structure_preview_object

        show_v1_structure_preview_object(document, structure_model, project=find_project(document))
    except Exception:
        pass


def _geometry_rows_snapped_to_structure_previews(document, output, geometry_rows: list[object]) -> list[object]:
    segment_by_id = {
        str(getattr(row, "pipeline_segment_id", "") or ""): row
        for row in list(getattr(output, "pipeline_segment_rows", []) or [])
        if str(getattr(row, "pipeline_segment_id", "") or "")
    }
    structure_model = to_structure_model(find_v1_structure_model(document))
    if structure_model is None:
        return list(geometry_rows or [])
    point_by_ref = {
        str(getattr(point, "connection_point_id", "") or ""): point
        for point in list(getattr(structure_model, "connection_point_rows", []) or [])
        if str(getattr(point, "connection_point_id", "") or "")
    }
    structure_by_ref = {
        str(getattr(row, "structure_id", "") or ""): row
        for row in list(getattr(structure_model, "structure_rows", []) or [])
        if str(getattr(row, "structure_id", "") or "")
    }
    if not point_by_ref or not structure_by_ref:
        return list(geometry_rows or [])
    try:
        from .cmd_structure_editor import _station_offset_xyz as structure_station_offset_xyz
        from .cmd_structure_editor import _structure_preview_path_source

        path = _structure_preview_path_source(document)
    except Exception:
        return list(geometry_rows or [])
    snapped_rows = []
    for row in list(geometry_rows or []):
        segment = segment_by_id.get(str(getattr(row, "pipeline_segment_id", "") or ""))
        points = list(getattr(row, "centerline_points", []) or [])
        if segment is None or len(points) < 2:
            snapped_rows.append(row)
            continue
        first = _snapped_culvert_endpoint_point(
            points[0],
            str(getattr(segment, "from_connection_point_ref", "") or ""),
            point_by_ref=point_by_ref,
            structure_by_ref=structure_by_ref,
            path=path,
            station_offset_xyz=structure_station_offset_xyz,
            direction="out",
        )
        last = _snapped_culvert_endpoint_point(
            points[-1],
            str(getattr(segment, "to_connection_point_ref", "") or ""),
            point_by_ref=point_by_ref,
            structure_by_ref=structure_by_ref,
            path=path,
            station_offset_xyz=structure_station_offset_xyz,
            direction="in",
        )
        if first == points[0] and last == points[-1]:
            snapped_rows.append(row)
            continue
        new_points = list(points)
        new_points[0] = first
        new_points[-1] = last
        snapped_rows.append(
            replace(
                row,
                centerline_points=new_points,
                notes=(str(getattr(row, "notes", "") or "") + ";preview_endpoint_snap=structure_culvert").strip(";"),
            )
        )
    return snapped_rows


def _snapped_culvert_endpoint_point(
    point_xyz,
    connection_point_ref: str,
    *,
    point_by_ref: dict[str, object],
    structure_by_ref: dict[str, object],
    path: dict[str, object],
    station_offset_xyz,
    direction: str,
):
    point = point_by_ref.get(str(connection_point_ref or ""))
    if point is None:
        return point_xyz
    structure = structure_by_ref.get(str(getattr(point, "structure_ref", "") or ""))
    if not _is_culvert_endpoint_preview_point(point, structure):
        return point_xyz
    placement = getattr(structure, "placement", None)
    if placement is None:
        return point_xyz
    start = float(getattr(placement, "station_start", 0.0) or 0.0)
    end = float(getattr(placement, "station_end", start) or start)
    role = str(getattr(point, "point_role", "") or "").strip().lower()
    use_start = role in {"pipe_in", "upstream", "inlet"} or direction == "in"
    station = min(start, end) if use_start else max(start, end)
    offset = float(getattr(placement, "offset", getattr(point, "offset", 0.0)) or 0.0)
    try:
        x, y, _z = station_offset_xyz(path, station, offset, 0.0)
    except Exception:
        return point_xyz
    original_z = float(point_xyz[2]) if len(point_xyz) >= 3 else 0.0
    return (float(x), float(y), original_z)


def _is_culvert_endpoint_preview_point(point, structure) -> bool:
    if point is None or structure is None:
        return False
    kind = str(getattr(structure, "structure_kind", "") or "").strip().lower()
    native_type = str(getattr(structure, "native_type", "") or "").strip().lower()
    if kind != "culvert" and native_type not in {"box_culvert", "pipe_culvert"}:
        return False
    role = str(getattr(point, "point_role", "") or "").strip().lower()
    return role in {"pipe_in", "pipe_out", "upstream", "downstream", "inlet", "outlet"}


def _create_pipeline_geometry_preview_objects(document, geometry_rows: list[object]) -> list[object]:
    objects: list[object] = []
    for row in list(geometry_rows or []):
        segment_id = str(getattr(row, "pipeline_segment_id", "") or "")
        if not segment_id:
            continue
        shape = _pipeline_geometry_shape(row)
        if shape is None or getattr(shape, "isNull", lambda: False)():
            continue
        object_name = "V1DrainagePipelineSegment_" + _safe_object_suffix(segment_id)
        obj = document.getObject(object_name)
        if obj is None:
            obj = document.addObject("Part::Feature", object_name)
        obj.Label = "Drainage Pipe - " + _display_source_ref(segment_id)
        obj.Shape = shape
        _set_preview_string_property(obj, "CRRecordKind", "v1_drainage_pipeline_segment_output_preview")
        _set_preview_string_property(obj, "V1ObjectType", "V1DrainagePipelineSegmentOutputPreview")
        _set_preview_string_property(obj, "PipelineSegmentId", segment_id)
        _set_preview_string_property(obj, "FlowRouteRef", str(getattr(row, "flow_route_ref", "") or ""))
        _set_preview_string_property(obj, "CoordinateMode", str(getattr(row, "coordinate_mode", "") or ""))
        _style_pipeline_segment_preview(obj)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(find_project(document), obj)
        except Exception:
            pass
        objects.append(obj)
    return objects


def _create_pipeline_connection_point_preview_objects(document, output, geometry_rows: list[object]) -> list[object]:
    geometry_by_segment = {
        str(getattr(row, "pipeline_segment_id", "") or ""): row
        for row in list(geometry_rows or [])
        if str(getattr(row, "pipeline_segment_id", "") or "")
    }
    point_by_ref = {
        str(getattr(point, "connection_point_id", "") or ""): point
        for point in list(getattr(to_structure_model(find_v1_structure_model(document)), "connection_point_rows", []) or [])
        if str(getattr(point, "connection_point_id", "") or "")
    }
    marker_specs: dict[str, dict[str, object]] = {}
    for segment in list(getattr(output, "pipeline_segment_rows", []) or []):
        segment_id = str(getattr(segment, "pipeline_segment_id", "") or "")
        geometry = geometry_by_segment.get(segment_id)
        points = _pipeline_geometry_display_points(geometry) if geometry is not None else []
        if not points:
            continue
        for ref, xyz, endpoint_kind in (
            (str(getattr(segment, "from_connection_point_ref", "") or ""), points[0], "from"),
            (str(getattr(segment, "to_connection_point_ref", "") or ""), points[-1], "to"),
        ):
            if not ref:
                continue
            marker_specs[ref] = {
                "point": point_by_ref.get(ref),
                "xyz": xyz,
                "endpoint_kind": endpoint_kind,
                "segment_id": segment_id,
                "flow_route_ref": str(getattr(segment, "flow_route_ref", "") or ""),
            }
    objects: list[object] = []
    for ref, spec in marker_specs.items():
        xyz = spec.get("xyz", (0.0, 0.0, 0.0))
        if len(xyz) < 3:
            continue
        point = spec.get("point")
        role = str(getattr(point, "point_role", "") or spec.get("endpoint_kind", "") or "")
        object_name = "V1StructurePipeConnectionPoint_" + _safe_object_suffix(ref)
        obj = document.getObject(object_name)
        if obj is None:
            obj = document.addObject("Part::Feature", object_name)
        obj.Label = _connection_point_preview_label(ref, role)
        obj.Shape = _pipeline_connection_point_marker_shape(point, xyz)
        _set_preview_string_property(obj, "CRRecordKind", "v1_structure_pipe_connection_point_preview")
        _set_preview_string_property(obj, "V1ObjectType", "V1StructurePipeConnectionPointPreview")
        _set_preview_string_property(obj, "ConnectionPointRef", ref)
        _set_preview_string_property(obj, "PointRole", role)
        _set_preview_string_property(obj, "StructureRef", str(getattr(point, "structure_ref", "") or ""))
        _set_preview_string_property(obj, "PipelineSegmentId", str(spec.get("segment_id", "") or ""))
        _set_preview_string_property(obj, "FlowRouteRef", str(spec.get("flow_route_ref", "") or ""))
        _style_pipeline_connection_point_preview(obj, role)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(find_project(document), obj)
        except Exception:
            pass
        objects.append(obj)
    return objects


class V1DrainageReviewTaskPanel:
    """Read-only review panel for Drainage source and resolved section context."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.output = None
        self._report_rows = []
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
        _populate_flow_route_table(self._flow_route_table, [row for row in self.output.element_rows if row.kind == "flow_route"])
        _populate_flow_route_issue_table(self._flow_route_issue_table, [row for row in self.output.element_rows if row.kind == "flow_route_issue"])
        _populate_pipeline_table(self._pipeline_table, [row for row in self.output.element_rows if row.kind == "pipeline_segment_candidate"])
        _populate_pipeline_segment_table(self._pipeline_segment_table, self.output.pipeline_segment_rows)
        _populate_pipeline_network_table(self._pipeline_network_table, self.output.pipeline_network_rows)
        _populate_pipeline_junction_table(self._pipeline_junction_table, self.output.pipeline_junction_rows)
        _populate_region_table(self._region_table, [row for row in self.output.element_rows if row.kind == "region_assignment"])
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

    def _show_flow_route_issue(self, row_index: int) -> None:
        try:
            flow_rows = [row for row in list(getattr(self.output, "element_rows", []) or []) if row.kind == "flow_route"]
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


def _drainage_review_navigation_targets() -> list[tuple[str, str]]:
    return [
        ("drainage", "Drainage"),
        ("regions", "Regions"),
        ("assembly", "Assembly"),
        ("structures", "Structures"),
        ("sections", "Cross Sections"),
    ]


def _open_drainage_review_navigation_target(target: str, *, document=None):
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    _activate_document(doc)
    if _gui_available() and hasattr(Gui, "Control"):
        try:
            Gui.Control.closeDialog()
        except Exception:
            pass
    target = str(target or "").strip().lower()
    if target == "drainage":
        from .cmd_drainage_editor import run_v1_drainage_editor_command

        return run_v1_drainage_editor_command(document=doc)
    if target == "regions":
        from .cmd_region_editor import run_v1_region_editor_command

        return run_v1_region_editor_command()
    if target == "assembly":
        from .cmd_assembly_editor import run_v1_assembly_editor_command

        return run_v1_assembly_editor_command()
    if target == "structures":
        from .cmd_structure_editor import run_v1_structure_editor_command

        return run_v1_structure_editor_command()
    if target == "sections":
        from .cmd_view_sections import run_v1_section_view_command

        return run_v1_section_view_command()
    raise ValueError(f"Unsupported Drainage Review navigation target: {target}")


def _activate_document(document) -> None:
    if App is None or document is None:
        return
    try:
        App.setActiveDocument(document.Name)
    except Exception:
        pass


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


def _populate_flow_route_issue_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        _append_items(
            table,
            [
                row.label,
                _note_value(row.notes, "severity"),
                row.source_ref,
                _note_value(row.notes, "from_element_ref"),
                _note_value(row.notes, "outlet_refs"),
                _format_float(row.station_start),
                _format_float(row.station_end),
                _note_value(row.notes, "message"),
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


def _populate_flowline_table(table, rows) -> None:
    table.setRowCount(0)
    for row in list(rows or []):
        _append_items(
            table,
            [
                row.label,
                row.source_ref,
                _format_float(row.station_start),
                _format_float(row.station_end),
                _note_value(row.notes, "fall"),
                _note_value(row.notes, "grade"),
                _note_value(row.notes, "from_point"),
                _note_value(row.notes, "to_point"),
                row.notes,
            ],
        )


def _populate_report_table(table, rows, *, warnings_only: bool = False) -> None:
    table.setRowCount(0)
    for row in _filter_report_rows(rows, warnings_only=warnings_only):
        _append_items(
            table,
            [
                row.label,
                row.source_ref,
                _note_value(row.notes, "value"),
                _note_value(row.notes, "unit"),
                _note_value(row.notes, "family")
                or _note_value(row.notes, "policy_ref")
                or _note_value(row.notes, "policy_refs")
                or _note_value(row.notes, "quantity_kind"),
                _note_value(row.notes, "element_refs") or _note_value(row.notes, "flow_route_refs"),
                row.notes,
            ],
        )


def _filter_report_rows(rows, *, warnings_only: bool = False) -> list:
    output = list(rows or [])
    if not warnings_only:
        return output
    return [
        row
        for row in output
        if _note_value(row.notes, "severity").lower() == "warning" or str(getattr(row, "label", "") or "").endswith("_warning")
    ]


def _pipeline_candidate_shape(row, *, adapter=None):
    station_start = float(getattr(row, "station_start", 0.0) or 0.0)
    station_end = float(getattr(row, "station_end", station_start) or station_start)
    from_offset = _note_float(row.notes, "from_offset", 0.0)
    to_offset = _note_float(row.notes, "to_offset", from_offset)
    invert_start = _note_float(row.notes, "invert_start", 0.0)
    invert_end = _note_float(row.notes, "invert_end", invert_start)
    diameter = max(_note_float(row.notes, "diameter", 0.0), 0.2)
    axis_offset = diameter / 2.0
    point0 = _station_offset_vector(station_start, from_offset, invert_start + axis_offset, adapter=adapter)
    point1 = _station_offset_vector(station_end, to_offset, invert_end + axis_offset, adapter=adapter)
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


def _flow_route_issue_shape(row, *, adapter=None):
    station_start = float(getattr(row, "station_start", 0.0) or 0.0)
    station_end = float(getattr(row, "station_end", station_start) or station_start)
    point0 = _station_offset_vector(station_start, 0.0, 1.5, adapter=adapter)
    point1 = _station_offset_vector(station_end, 0.0, 1.5, adapter=adapter)
    direction = point1.sub(point0)
    if direction.Length <= 1.0e-9:
        return Part.makeSphere(1.0, point0)
    marker0 = Part.makeSphere(0.8, point0)
    marker1 = Part.makeSphere(0.8, point1)
    line = Part.makePolygon([point0, point1])
    return Part.Compound([marker0, line, marker1])


def _pipeline_geometry_shape(row):
    points = [App.Vector(float(point[0]), float(point[1]), float(point[2])) for point in _pipeline_geometry_display_points(row)]
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


def _pipeline_geometry_display_points(row) -> list[tuple[float, float, float]]:
    if row is None:
        return []
    axis_offset = _pipeline_display_axis_z_offset(row)
    points: list[tuple[float, float, float]] = []
    for point in list(getattr(row, "centerline_points", []) or []):
        if len(point) < 3:
            continue
        points.append((float(point[0]), float(point[1]), float(point[2]) + axis_offset))
    return points


def _pipeline_display_axis_z_offset(row) -> float:
    diameter = float(getattr(row, "diameter", 0.0) or 0.0)
    shape_kind = str(getattr(row, "shape_kind", "") or "").strip().lower()
    if diameter <= 0.0:
        return 0.0
    if shape_kind and shape_kind not in {"circular", "pipe", "round", "circular_pipe"}:
        return 0.0
    return diameter / 2.0


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


def _pipeline_connection_point_marker_shape(point, xyz):
    x, y, z = float(xyz[0]), float(xyz[1]), float(xyz[2])
    radius = _pipeline_connection_point_marker_radius(point)
    center = App.Vector(x, y, z)
    try:
        return Part.makeSphere(radius, center)
    except Exception:
        return Part.Vertex(center)


def _pipeline_connection_point_marker_radius(point) -> float:
    diameter = float(getattr(point, "diameter", 0.0) or 0.0)
    width = float(getattr(point, "width", 0.0) or 0.0)
    height = float(getattr(point, "height", 0.0) or 0.0)
    return max(0.55, min(max(diameter, width, height, 0.8) * 0.45, 2.5))


def _connection_point_preview_label(connection_point_ref: str, role: str) -> str:
    role_text = str(role or "").replace("_", " ").strip().title() or "Connection Point"
    return f"{role_text} - {_display_source_ref(connection_point_ref)}"


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

    def _adapter(station: float, offset: float) -> tuple[float, float, float]:
        frame = frame_service.resolve_station_offset(result, station, offset)
        return float(frame.x), float(frame.y), float(frame.z)

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


def _style_pipeline_candidate_preview(obj, *, status: str = "") -> None:
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return
        status = str(status or "").strip().lower()
        vobj.Visibility = True
        if status == "ready":
            vobj.ShapeColor = (0.0, 0.85, 0.95)
            vobj.LineColor = (0.0, 0.95, 0.55)
            vobj.PointColor = (0.0, 0.95, 0.55)
            vobj.Transparency = 15
            vobj.LineWidth = 5.0
        elif status == "capture_only":
            vobj.ShapeColor = (1.0, 0.7, 0.0)
            vobj.LineColor = (1.0, 0.7, 0.0)
            vobj.PointColor = (1.0, 0.7, 0.0)
            vobj.Transparency = 5
            vobj.LineWidth = 7.0
        else:
            vobj.ShapeColor = (1.0, 0.25, 0.0)
            vobj.LineColor = (1.0, 0.25, 0.0)
            vobj.PointColor = (1.0, 0.25, 0.0)
            vobj.Transparency = 0
            vobj.LineWidth = 8.0
    except Exception:
        pass


def _style_flow_route_issue_preview(obj) -> None:
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return
        vobj.Visibility = True
        vobj.ShapeColor = (1.0, 0.45, 0.0)
        vobj.LineColor = (1.0, 0.45, 0.0)
        vobj.PointColor = (1.0, 0.9, 0.0)
        vobj.Transparency = 0
        vobj.LineWidth = 8.0
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


def _style_pipeline_connection_point_preview(obj, role: str) -> None:
    role_text = str(role or "").strip().lower()
    if role_text in {"pipe_in", "upstream", "inlet", "to"}:
        color = (1.0, 0.65, 0.0)
    elif role_text in {"pipe_out", "downstream", "outlet", "discharge", "from"}:
        color = (0.1, 1.0, 0.25)
    else:
        color = (1.0, 1.0, 0.0)
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return
        vobj.Visibility = True
        vobj.ShapeColor = color
        vobj.LineColor = color
        vobj.PointColor = color
        vobj.Transparency = 0
        vobj.LineWidth = 5.0
        vobj.PointSize = 12.0
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


def _unique_text_values(values: list[object]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _safe_object_suffix(value: object) -> str:
    text = str(value or "").strip()
    output = []
    for char in text:
        output.append(char if char.isalnum() else "_")
    return "".join(output).strip("_") or "unknown"


def _display_source_ref(value: object) -> str:
    text = str(value or "").strip()
    if ":" not in text:
        return text
    return text.split(":", 1)[1]


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
    flow_route_issues = int(summary.get("summary:flow-route-issues", 0) or 0)
    if flow_route_issues:
        lines.append(f"Flow Route Issues: {flow_route_issues} outlet-chain issue(s) can be focused in 3D.")
    flowline_spans = int(summary.get("summary:flowline-continuity-spans", 0) or 0)
    flowline_issues = int(summary.get("summary:flowline-continuity-issues", 0) or 0)
    if flowline_spans:
        lines.append(f"Flowline Continuity: {flowline_spans} span(s), {flowline_issues} issue(s).")
    inlet_count = int(summary.get("summary:report-inlet-count", 0) or 0)
    culvert_count = int(summary.get("summary:report-culvert-count", 0) or 0)
    outlet_count = int(summary.get("summary:report-outlet-count", 0) or 0)
    pipe_length = float(summary.get("summary:report-pipe-length", 0.0) or 0.0)
    policy_warnings = int(summary.get("summary:report-pipe-policy-warnings", 0) or 0)
    if inlet_count or culvert_count or outlet_count or pipe_length:
        lines.append(
            f"Reports: inlets={inlet_count}, culverts={culvert_count}, outlets={outlet_count}, pipe_length={pipe_length:.3f} m, policy_warnings={policy_warnings}."
        )
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
