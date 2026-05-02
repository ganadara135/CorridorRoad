"""FreeCAD result object for v1 AppliedSectionSet rows."""

from __future__ import annotations

import math

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
try:
    import Part
except Exception:  # pragma: no cover - Part is not available in plain Python.
    Part = None

from ..models.result.applied_section import AppliedSection, AppliedSectionComponentRow, AppliedSectionFrame, AppliedSectionPoint
from ..models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow


class V1AppliedSectionSetObject:
    """Document object proxy that stores v1 AppliedSectionSet result summaries."""

    Type = "V1AppliedSectionSet"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_applied_section_set_properties(obj)

    def execute(self, obj):
        ensure_v1_applied_section_set_properties(obj)
        if str(getattr(obj, "ReviewShapeStatus", "") or "") == "built":
            build_v1_applied_section_set_review_shape(obj)
        else:
            _set_empty_applied_section_set_shape(obj)
        return


class ViewProviderV1AppliedSectionSet:
    """Simple view provider for v1 AppliedSectionSet result objects."""

    Type = "ViewProviderV1AppliedSectionSet"

    def __init__(self, vobj):
        vobj.Proxy = self
        _style_applied_section_set_view(vobj, visible=False)

    def onChanged(self, vobj, prop):
        if str(prop or "") != "Visibility":
            return
        try:
            if bool(getattr(vobj, "Visibility", False)):
                build_v1_applied_section_set_review_shape(getattr(vobj, "Object", None), visible=True)
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("sections.svg")
        except Exception:
            return ""


def ensure_v1_applied_section_set_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 AppliedSectionSet result properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "AppliedSectionSetId", "CorridorRoad", "v1 applied section set id")
    _add_property(obj, "App::PropertyString", "CorridorId", "CorridorRoad", "corridor id")
    _add_property(obj, "App::PropertyString", "AlignmentId", "CorridorRoad", "alignment id")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "StationCount", "Stations", "applied section station count")
    _add_property(obj, "App::PropertyStringList", "StationRowIds", "Stations", "station row ids")
    _add_property(obj, "App::PropertyFloatList", "StationValues", "Stations", "station values")
    _add_property(obj, "App::PropertyStringList", "AppliedSectionIds", "Stations", "applied section ids")
    _add_property(obj, "App::PropertyStringList", "StationKinds", "Stations", "station kinds")
    _add_property(obj, "App::PropertyFloatList", "FrameXValues", "Frames", "applied section frame x values")
    _add_property(obj, "App::PropertyFloatList", "FrameYValues", "Frames", "applied section frame y values")
    _add_property(obj, "App::PropertyFloatList", "FrameZValues", "Frames", "applied section frame z values")
    _add_property(obj, "App::PropertyFloatList", "FrameTangentDirections", "Frames", "frame tangent directions in degrees")
    _add_property(obj, "App::PropertyFloatList", "FrameProfileGrades", "Frames", "profile grades")
    _add_property(obj, "App::PropertyStringList", "FrameAlignmentStatuses", "Frames", "alignment statuses")
    _add_property(obj, "App::PropertyStringList", "FrameProfileStatuses", "Frames", "profile statuses")
    _add_property(obj, "App::PropertyFloatList", "SurfaceLeftWidths", "Surface", "left design surface widths")
    _add_property(obj, "App::PropertyFloatList", "SurfaceRightWidths", "Surface", "right design surface widths")
    _add_property(obj, "App::PropertyFloatList", "SubgradeDepths", "Surface", "subgrade depths")
    _add_property(obj, "App::PropertyFloatList", "DaylightLeftWidths", "Surface", "left daylight widths")
    _add_property(obj, "App::PropertyFloatList", "DaylightRightWidths", "Surface", "right daylight widths")
    _add_property(obj, "App::PropertyFloatList", "DaylightLeftSlopes", "Surface", "left daylight slopes")
    _add_property(obj, "App::PropertyFloatList", "DaylightRightSlopes", "Surface", "right daylight slopes")
    _add_property(obj, "App::PropertyStringList", "PointRows", "Surface", "applied section point rows")
    _add_property(obj, "App::PropertyStringList", "ComponentRows", "Resolved Context", "applied section component rows")
    _add_property(obj, "App::PropertyStringList", "RegionIds", "Resolved Context", "resolved region ids")
    _add_property(obj, "App::PropertyStringList", "AssemblyIds", "Resolved Context", "resolved assembly ids")
    _add_property(obj, "App::PropertyStringList", "TemplateIds", "Resolved Context", "resolved template ids")
    _add_property(obj, "App::PropertyStringList", "ActiveStructureRows", "Resolved Context", "active structure ids by section")
    _add_property(obj, "App::PropertyStringList", "ActiveStructureRuleRows", "Resolved Context", "active structure interaction rule ids by section")
    _add_property(obj, "App::PropertyStringList", "ActiveStructureInfluenceZoneRows", "Resolved Context", "active structure influence zone ids by section")
    _add_property(obj, "App::PropertyStringList", "StructureDiagnosticRows", "Resolved Context", "structure context diagnostic rows")
    _add_property(obj, "App::PropertyIntegerList", "ComponentCounts", "Resolved Context", "component counts")
    _add_property(obj, "App::PropertyIntegerList", "DiagnosticCounts", "Diagnostics", "diagnostic counts")
    _add_property(obj, "App::PropertyStringList", "DiagnosticRows", "Diagnostics", "diagnostic summary rows")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Source", "source refs")
    _add_property(obj, "App::PropertyString", "ReviewShapeStatus", "Review", "full review shape build status")
    _add_property(obj, "App::PropertyInteger", "ReviewShapeStationCount", "Review", "station count used by the full review shape")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1AppliedSectionSet"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "AppliedSectionSetId", "") or ""):
        obj.AppliedSectionSetId = f"applied-sections:{str(getattr(obj, 'Name', '') or 'v1')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_applied_section_set"
    if not str(getattr(obj, "ReviewShapeStatus", "") or ""):
        obj.ReviewShapeStatus = "not_built"


def create_or_update_v1_applied_section_set_object(
    document=None,
    applied_section_set: AppliedSectionSet | None = None,
    *,
    project=None,
    object_name: str = "V1AppliedSectionSet",
    label: str = "Applied Sections",
):
    """Create or update the durable v1 AppliedSectionSet result object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 AppliedSectionSet creation.")
    if applied_section_set is None:
        applied_section_set = AppliedSectionSet(
            schema_version=1,
            project_id=_project_id(project),
            applied_section_set_id="applied-sections:main",
        )

    obj = doc.getObject(object_name)
    if obj is None:
        try:
            obj = doc.addObject("Part::FeaturePython", object_name)
        except Exception:
            obj = doc.addObject("App::FeaturePython", object_name)
        V1AppliedSectionSetObject(obj)
        try:
            ViewProviderV1AppliedSectionSet(obj.ViewObject)
        except Exception:
            pass
    else:
        V1AppliedSectionSetObject(obj)
    _style_applied_section_set_view(getattr(obj, "ViewObject", None), visible=False)
    update_v1_applied_section_set_object(obj, applied_section_set, label=label)

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_applied_section_set_object(obj, applied_section_set: AppliedSectionSet, *, label: str = "Applied Sections"):
    """Write AppliedSectionSet result summaries into a FreeCAD object."""

    ensure_v1_applied_section_set_properties(obj)
    station_rows = list(getattr(applied_section_set, "station_rows", []) or [])
    sections = list(getattr(applied_section_set, "sections", []) or [])
    section_by_id = {str(section.applied_section_id): section for section in sections}

    obj.Label = label
    obj.SchemaVersion = int(getattr(applied_section_set, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(applied_section_set, "project_id", "") or "corridorroad-v1")
    obj.AppliedSectionSetId = str(getattr(applied_section_set, "applied_section_set_id", "") or "applied-sections:main")
    obj.CorridorId = str(getattr(applied_section_set, "corridor_id", "") or "")
    obj.AlignmentId = str(getattr(applied_section_set, "alignment_id", "") or "")
    obj.CRRecordKind = "v1_applied_section_set"
    obj.StationCount = len(station_rows)
    obj.StationRowIds = [str(row.station_row_id) for row in station_rows]
    obj.StationValues = [float(row.station) for row in station_rows]
    obj.AppliedSectionIds = [str(row.applied_section_id) for row in station_rows]
    obj.StationKinds = [str(row.kind) for row in station_rows]
    frames = [_section_frame(section_by_id.get(str(row.applied_section_id))) for row in station_rows]
    obj.FrameXValues = [float(getattr(frame, "x", 0.0) or 0.0) for frame in frames]
    obj.FrameYValues = [float(getattr(frame, "y", 0.0) or 0.0) for frame in frames]
    obj.FrameZValues = [float(getattr(frame, "z", 0.0) or 0.0) for frame in frames]
    obj.FrameTangentDirections = [float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0) for frame in frames]
    obj.FrameProfileGrades = [float(getattr(frame, "profile_grade", 0.0) or 0.0) for frame in frames]
    obj.FrameAlignmentStatuses = [str(getattr(frame, "alignment_status", "") or "") for frame in frames]
    obj.FrameProfileStatuses = [str(getattr(frame, "profile_status", "") or "") for frame in frames]
    obj.SurfaceLeftWidths = [float(getattr(section_by_id.get(str(row.applied_section_id)), "surface_left_width", 0.0) or 0.0) for row in station_rows]
    obj.SurfaceRightWidths = [float(getattr(section_by_id.get(str(row.applied_section_id)), "surface_right_width", 0.0) or 0.0) for row in station_rows]
    obj.SubgradeDepths = [float(getattr(section_by_id.get(str(row.applied_section_id)), "subgrade_depth", 0.0) or 0.0) for row in station_rows]
    obj.DaylightLeftWidths = [float(getattr(section_by_id.get(str(row.applied_section_id)), "daylight_left_width", 0.0) or 0.0) for row in station_rows]
    obj.DaylightRightWidths = [float(getattr(section_by_id.get(str(row.applied_section_id)), "daylight_right_width", 0.0) or 0.0) for row in station_rows]
    obj.DaylightLeftSlopes = [float(getattr(section_by_id.get(str(row.applied_section_id)), "daylight_left_slope", 0.0) or 0.0) for row in station_rows]
    obj.DaylightRightSlopes = [float(getattr(section_by_id.get(str(row.applied_section_id)), "daylight_right_slope", 0.0) or 0.0) for row in station_rows]
    obj.PointRows = _point_rows(station_rows, section_by_id)
    obj.ComponentRows = _component_rows(station_rows, section_by_id)
    obj.RegionIds = [str(getattr(section_by_id.get(row.applied_section_id), "region_id", "") or "") for row in station_rows]
    obj.AssemblyIds = [str(getattr(section_by_id.get(row.applied_section_id), "assembly_id", "") or "") for row in station_rows]
    obj.TemplateIds = [str(getattr(section_by_id.get(row.applied_section_id), "template_id", "") or "") for row in station_rows]
    obj.ActiveStructureRows = _section_list_rows(station_rows, section_by_id, "active_structure_ids")
    obj.ActiveStructureRuleRows = _section_list_rows(station_rows, section_by_id, "active_structure_rule_ids")
    obj.ActiveStructureInfluenceZoneRows = _section_list_rows(station_rows, section_by_id, "active_structure_influence_zone_ids")
    obj.StructureDiagnosticRows = _section_list_rows(station_rows, section_by_id, "structure_diagnostic_rows")
    obj.ComponentCounts = [len(list(getattr(section_by_id.get(row.applied_section_id), "component_rows", []) or [])) for row in station_rows]
    obj.DiagnosticCounts = [len(list(getattr(section_by_id.get(row.applied_section_id), "diagnostic_rows", []) or [])) for row in station_rows]
    obj.DiagnosticRows = _diagnostic_rows(sections)
    obj.SourceRefs = [str(ref) for ref in list(getattr(applied_section_set, "source_refs", []) or []) if str(ref)]
    obj.ReviewShapeStatus = "not_built"
    obj.ReviewShapeStationCount = 0
    _set_empty_applied_section_set_shape(obj)
    _style_applied_section_set_view(getattr(obj, "ViewObject", None), visible=False)
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def build_v1_applied_section_set_review_shape(obj, *, visible: bool | None = None):
    """Build and attach the full all-station review shape on demand."""

    if obj is None:
        return None
    ensure_v1_applied_section_set_properties(obj)
    shape = build_v1_applied_section_set_shape(obj)
    if shape is not None:
        try:
            obj.Shape = shape
            obj.ReviewShapeStatus = "built"
            obj.ReviewShapeStationCount = int(getattr(obj, "StationCount", 0) or 0)
        except Exception:
            pass
    _style_applied_section_set_view(getattr(obj, "ViewObject", None), visible=visible)
    return shape


def _set_empty_applied_section_set_shape(obj) -> None:
    if obj is None or Part is None:
        return
    try:
        obj.Shape = Part.Shape()
    except Exception:
        pass


def _style_applied_section_set_view(vobj, *, visible: bool | None = None) -> None:
    """Style the whole AppliedSectionSet review shape as a quiet, hidden reference layer."""

    if vobj is None:
        return
    try:
        review_color = (0.58, 0.70, 0.88)
        vobj.LineColor = review_color
        vobj.PointColor = review_color
        vobj.ShapeColor = review_color
        vobj.LineWidth = 1.0
        vobj.PointSize = 3.0
        if hasattr(vobj, "DrawStyle"):
            vobj.DrawStyle = "Solid"
        if visible is not None:
            target = bool(visible)
            if bool(getattr(vobj, "Visibility", False)) != target:
                vobj.Visibility = target
    except Exception:
        pass


def build_v1_applied_section_set_shape(obj):
    """Build a hidden-by-default 3D review shape for the whole AppliedSectionSet."""

    if App is None or Part is None:
        return None
    ensure_v1_applied_section_set_properties(obj)
    section_ids = list(getattr(obj, "AppliedSectionIds", []) or [])
    point_rows_by_section = _parse_point_rows(getattr(obj, "PointRows", []) or [])
    edges = []
    for index, section_id in enumerate(section_ids):
        section_key = str(section_id or "")
        point_rows = point_rows_by_section.get(section_key, [])
        for points in _applied_section_display_point_groups(point_rows):
            edge = _display_edge_from_applied_points(points)
            if edge is not None:
                edges.append(edge)
        if point_rows:
            continue
        fallback_edge = _fallback_section_width_edge(obj, index)
        if fallback_edge is not None:
            edges.append(fallback_edge)
    if not edges:
        return Part.Shape()
    if len(edges) == 1:
        return edges[0]
    return Part.Compound(edges)


def _applied_section_display_point_groups(point_rows: list[AppliedSectionPoint]) -> list[list[AppliedSectionPoint]]:
    rows = list(point_rows or [])
    if not rows:
        return []
    role_groups = [
        {"fg_surface", "ditch_surface", "side_slope_surface", "bench_surface", "daylight_marker"},
        {"subgrade_surface"},
    ]
    output: list[list[AppliedSectionPoint]] = []
    for roles in role_groups:
        points = [point for point in rows if str(getattr(point, "point_role", "") or "") in roles]
        points.sort(key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))
        unique_points = _unique_display_points(points)
        if len(unique_points) >= 2:
            output.append(unique_points)
    return output


def _unique_display_points(points: list[AppliedSectionPoint]) -> list[AppliedSectionPoint]:
    output: list[AppliedSectionPoint] = []
    for point in list(points or []):
        if output:
            previous = output[-1]
            if (
                abs(float(getattr(point, "x", 0.0) or 0.0) - float(getattr(previous, "x", 0.0) or 0.0)) <= 1.0e-9
                and abs(float(getattr(point, "y", 0.0) or 0.0) - float(getattr(previous, "y", 0.0) or 0.0)) <= 1.0e-9
                and abs(float(getattr(point, "z", 0.0) or 0.0) - float(getattr(previous, "z", 0.0) or 0.0)) <= 1.0e-9
            ):
                continue
        output.append(point)
    return output


def _display_edge_from_applied_points(points: list[AppliedSectionPoint]):
    vectors = [
        App.Vector(
            float(getattr(point, "x", 0.0) or 0.0),
            float(getattr(point, "y", 0.0) or 0.0),
            float(getattr(point, "z", 0.0) or 0.0),
        )
        for point in list(points or [])
    ]
    if len(vectors) < 2:
        return None
    try:
        return Part.makePolygon(vectors)
    except Exception:
        edges = []
        for start, end in zip(vectors, vectors[1:]):
            try:
                if (end - start).Length > 1.0e-9:
                    edges.append(Part.makeLine(start, end))
            except Exception:
                pass
        if not edges:
            return None
        return Part.Compound(edges) if len(edges) > 1 else edges[0]


def _fallback_section_width_edge(obj, index: int):
    frame_x = _float_value(getattr(obj, "FrameXValues", []), index, 0.0)
    frame_y = _float_value(getattr(obj, "FrameYValues", []), index, 0.0)
    frame_z = _float_value(getattr(obj, "FrameZValues", []), index, 0.0)
    heading = math.radians(_float_value(getattr(obj, "FrameTangentDirections", []), index, 0.0))
    normal_x = -math.sin(heading)
    normal_y = math.cos(heading)
    left_width = _float_value(getattr(obj, "SurfaceLeftWidths", []), index, 0.0)
    right_width = _float_value(getattr(obj, "SurfaceRightWidths", []), index, 0.0)
    if left_width <= 0.0 and right_width <= 0.0:
        return None
    left = App.Vector(frame_x + normal_x * left_width, frame_y + normal_y * left_width, frame_z)
    right = App.Vector(frame_x - normal_x * right_width, frame_y - normal_y * right_width, frame_z)
    try:
        return Part.makeLine(left, right)
    except Exception:
        return None


def to_applied_section_set(obj) -> AppliedSectionSet | None:
    """Build a summary AppliedSectionSet from a v1 result FreeCAD object."""

    if not _is_v1_applied_section_set(obj):
        return None
    ensure_v1_applied_section_set_properties(obj)
    station_values = _float_list(getattr(obj, "StationValues", []) or [])
    section_ids = list(getattr(obj, "AppliedSectionIds", []) or [])
    station_rows: list[AppliedSectionStationRow] = []
    sections: list[AppliedSection] = []
    point_rows_by_section = _parse_point_rows(getattr(obj, "PointRows", []) or [])
    active_structures_by_section = _parse_section_list_rows(getattr(obj, "ActiveStructureRows", []) or [])
    active_rules_by_section = _parse_section_list_rows(getattr(obj, "ActiveStructureRuleRows", []) or [])
    active_zones_by_section = _parse_section_list_rows(getattr(obj, "ActiveStructureInfluenceZoneRows", []) or [])
    structure_diagnostics_by_section = _parse_section_list_rows(getattr(obj, "StructureDiagnosticRows", []) or [])
    component_rows_by_section = _parse_component_rows(getattr(obj, "ComponentRows", []) or [])
    for index, station in enumerate(station_values):
        section_id = _list_value(section_ids, index, f"section:{index + 1}")
        station_rows.append(
            AppliedSectionStationRow(
                station_row_id=_list_value(getattr(obj, "StationRowIds", []), index, f"station:{index + 1}"),
                station=float(station),
                applied_section_id=section_id,
                kind=_list_value(getattr(obj, "StationKinds", []), index, "regular_sample"),
            )
        )
        sections.append(
            AppliedSection(
                schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
                project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
                applied_section_id=section_id,
                corridor_id=str(getattr(obj, "CorridorId", "") or ""),
                alignment_id=str(getattr(obj, "AlignmentId", "") or ""),
                assembly_id=_list_value(getattr(obj, "AssemblyIds", []), index, ""),
                station=float(station),
                template_id=_list_value(getattr(obj, "TemplateIds", []), index, ""),
                region_id=_list_value(getattr(obj, "RegionIds", []), index, ""),
                surface_left_width=_float_value(getattr(obj, "SurfaceLeftWidths", []), index, 0.0),
                surface_right_width=_float_value(getattr(obj, "SurfaceRightWidths", []), index, 0.0),
                subgrade_depth=_float_value(getattr(obj, "SubgradeDepths", []), index, 0.0),
                daylight_left_width=_float_value(getattr(obj, "DaylightLeftWidths", []), index, 0.0),
                daylight_right_width=_float_value(getattr(obj, "DaylightRightWidths", []), index, 0.0),
                daylight_left_slope=_float_value(getattr(obj, "DaylightLeftSlopes", []), index, 0.0),
                daylight_right_slope=_float_value(getattr(obj, "DaylightRightSlopes", []), index, 0.0),
                component_rows=component_rows_by_section.get(section_id)
                or _component_placeholders(
                    _integer_value(getattr(obj, "ComponentCounts", []), index, 0),
                    _list_value(getattr(obj, "TemplateIds", []), index, ""),
                    _list_value(getattr(obj, "RegionIds", []), index, ""),
                ),
                point_rows=point_rows_by_section.get(section_id, []),
                active_structure_ids=active_structures_by_section.get(section_id, []),
                active_structure_rule_ids=active_rules_by_section.get(section_id, []),
                active_structure_influence_zone_ids=active_zones_by_section.get(section_id, []),
                structure_diagnostic_rows=structure_diagnostics_by_section.get(section_id, []),
                frame=AppliedSectionFrame(
                    station=float(station),
                    x=_float_value(getattr(obj, "FrameXValues", []), index, 0.0),
                    y=_float_value(getattr(obj, "FrameYValues", []), index, 0.0),
                    z=_float_value(getattr(obj, "FrameZValues", []), index, 0.0),
                    tangent_direction_deg=_float_value(getattr(obj, "FrameTangentDirections", []), index, 0.0),
                    profile_grade=_float_value(getattr(obj, "FrameProfileGrades", []), index, 0.0),
                    alignment_status=_list_value(getattr(obj, "FrameAlignmentStatuses", []), index, ""),
                    profile_status=_list_value(getattr(obj, "FrameProfileStatuses", []), index, ""),
                ),
            )
        )
    return AppliedSectionSet(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        applied_section_set_id=str(getattr(obj, "AppliedSectionSetId", "") or "applied-sections:main"),
        corridor_id=str(getattr(obj, "CorridorId", "") or ""),
        alignment_id=str(getattr(obj, "AlignmentId", "") or ""),
        station_rows=station_rows,
        sections=sections,
        source_refs=[str(ref) for ref in list(getattr(obj, "SourceRefs", []) or []) if str(ref)],
    )


def find_v1_applied_section_set(document, preferred_applied_section_set=None):
    """Find a v1 AppliedSectionSet result object in a document."""

    if _is_v1_applied_section_set(preferred_applied_section_set):
        return preferred_applied_section_set
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_applied_section_set(obj):
            return obj
    return None


def _is_v1_applied_section_set(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1AppliedSectionSet":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_applied_section_set":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1AppliedSectionSet" or name.startswith("V1AppliedSectionSet")


def _diagnostic_rows(sections) -> list[str]:
    output: list[str] = []
    for section in list(sections or []):
        section_id = str(getattr(section, "applied_section_id", "") or "")
        for diagnostic in list(getattr(section, "diagnostic_rows", []) or []):
            output.append(
                f"{section_id}|{getattr(diagnostic, 'severity', '')}|{getattr(diagnostic, 'kind', '')}|{getattr(diagnostic, 'message', '')}"
            )
    return output


def _point_rows(station_rows, section_by_id: dict[str, AppliedSection]) -> list[str]:
    output: list[str] = []
    for station_row in list(station_rows or []):
        section_id = str(getattr(station_row, "applied_section_id", "") or "")
        section = section_by_id.get(section_id)
        for point in list(getattr(section, "point_rows", []) or []):
            output.append(
                "|".join(
                    [
                        section_id,
                        _escape_row_value(getattr(point, "point_id", "")),
                        _escape_row_value(getattr(point, "point_role", "")),
                        f"{float(getattr(point, 'lateral_offset', 0.0) or 0.0):.12g}",
                        f"{float(getattr(point, 'x', 0.0) or 0.0):.12g}",
                        f"{float(getattr(point, 'y', 0.0) or 0.0):.12g}",
                        f"{float(getattr(point, 'z', 0.0) or 0.0):.12g}",
                    ]
                )
            )
    return output


def _component_rows(station_rows, section_by_id: dict[str, AppliedSection]) -> list[str]:
    output: list[str] = []
    for station_row in list(station_rows or []):
        section_id = str(getattr(station_row, "applied_section_id", "") or "")
        section = section_by_id.get(section_id)
        for component in list(getattr(section, "component_rows", []) or []):
            output.append(
                "|".join(
                    [
                        section_id,
                        _escape_row_value(getattr(component, "component_id", "")),
                        _escape_row_value(getattr(component, "kind", "")),
                        _escape_row_value(getattr(component, "source_template_id", "")),
                        _escape_row_value(getattr(component, "region_id", "")),
                        _escape_row_value(getattr(component, "side", "")),
                        f"{float(getattr(component, 'width', 0.0) or 0.0):.12g}",
                        f"{float(getattr(component, 'slope', 0.0) or 0.0):.12g}",
                        f"{float(getattr(component, 'thickness', 0.0) or 0.0):.12g}",
                        _escape_row_value(getattr(component, "material", "")),
                        ",".join(
                            _escape_row_value(value)
                            for value in list(getattr(component, "structure_ids", []) or [])
                            if str(value or "")
                        ),
                    ]
                )
            )
    return output


def _section_list_rows(station_rows, section_by_id: dict[str, AppliedSection], attr_name: str) -> list[str]:
    output: list[str] = []
    for station_row in list(station_rows or []):
        section_id = str(getattr(station_row, "applied_section_id", "") or "")
        section = section_by_id.get(section_id)
        values = [
            _escape_row_value(value)
            for value in list(getattr(section, attr_name, []) or [])
            if str(value or "")
        ]
        if values:
            output.append(section_id + "|" + "|".join(values))
    return output


def _parse_section_list_rows(values) -> dict[str, list[str]]:
    output: dict[str, list[str]] = {}
    for raw in list(values or []):
        parts = str(raw or "").split("|")
        if len(parts) < 2:
            continue
        section_id = _unescape_row_value(parts[0])
        output[section_id] = [_unescape_row_value(value) for value in parts[1:] if str(value or "")]
    return output


def _parse_point_rows(values) -> dict[str, list[AppliedSectionPoint]]:
    output: dict[str, list[AppliedSectionPoint]] = {}
    for raw in list(values or []):
        parts = str(raw or "").split("|")
        if len(parts) < 7:
            continue
        section_id = _unescape_row_value(parts[0])
        if not section_id:
            continue
        output.setdefault(section_id, []).append(
            AppliedSectionPoint(
                point_id=_unescape_row_value(parts[1]),
                point_role=_unescape_row_value(parts[2]),
                lateral_offset=_safe_float(parts[3]),
                x=_safe_float(parts[4]),
                y=_safe_float(parts[5]),
                z=_safe_float(parts[6]),
            )
        )
    for rows in output.values():
        rows.sort(key=lambda point: (str(getattr(point, "point_role", "") or ""), float(getattr(point, "lateral_offset", 0.0) or 0.0)))
    return output


def _parse_component_rows(values) -> dict[str, list[AppliedSectionComponentRow]]:
    output: dict[str, list[AppliedSectionComponentRow]] = {}
    for raw in list(values or []):
        parts = str(raw or "").split("|")
        if len(parts) < 10:
            continue
        section_id = _unescape_row_value(parts[0])
        if not section_id:
            continue
        structure_ids = []
        if len(parts) > 10:
            structure_ids = [
                _unescape_row_value(value)
                for value in str(parts[10] or "").split(",")
                if str(value or "")
            ]
        output.setdefault(section_id, []).append(
            AppliedSectionComponentRow(
                component_id=_unescape_row_value(parts[1]),
                kind=_unescape_row_value(parts[2]),
                source_template_id=_unescape_row_value(parts[3]),
                region_id=_unescape_row_value(parts[4]),
                side=_unescape_row_value(parts[5]),
                width=_safe_float(parts[6]),
                slope=_safe_float(parts[7]),
                thickness=_safe_float(parts[8]),
                material=_unescape_row_value(parts[9]),
                structure_ids=structure_ids,
            )
        )
    return output


def _escape_row_value(value: object) -> str:
    return str(value or "").replace("\\", "\\\\").replace("|", "\\p")


def _unescape_row_value(value: object) -> str:
    text = str(value or "")
    return text.replace("\\p", "|").replace("\\\\", "\\")


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _section_frame(section) -> AppliedSectionFrame:
    frame = getattr(section, "frame", None)
    if frame is not None:
        return frame
    return AppliedSectionFrame(station=float(getattr(section, "station", 0.0) or 0.0))


def _add_property(obj, property_type: str, name: str, group: str, doc: str = "") -> None:
    if obj is None or hasattr(obj, name):
        return
    try:
        obj.addProperty(property_type, name, group, doc)
    except Exception:
        pass


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _list_value(values, index: int, default: str = "") -> str:
    try:
        values_list = list(values or [])
        return str(values_list[index]) if index < len(values_list) else str(default)
    except Exception:
        return str(default)


def _float_list(values) -> list[float]:
    output = []
    for value in list(values or []):
        try:
            output.append(float(value))
        except Exception:
            output.append(0.0)
    return output


def _float_value(values, index: int, default: float = 0.0) -> float:
    try:
        values_list = list(values or [])
        return float(values_list[index]) if index < len(values_list) else float(default)
    except Exception:
        return float(default)


def _integer_value(values, index: int, default: int = 0) -> int:
    try:
        values_list = list(values or [])
        return int(values_list[index]) if index < len(values_list) else int(default)
    except Exception:
        return int(default)


def _component_placeholders(count: int, template_id: str, region_id: str) -> list[AppliedSectionComponentRow]:
    rows = []
    for index in range(max(int(count or 0), 0)):
        rows.append(
            AppliedSectionComponentRow(
                component_id=f"component:{index + 1}",
                kind="component",
                source_template_id=str(template_id or ""),
                region_id=str(region_id or ""),
            )
        )
    return rows
