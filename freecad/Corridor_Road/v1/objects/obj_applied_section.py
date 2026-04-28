"""FreeCAD result object for v1 AppliedSectionSet rows."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.result.applied_section import AppliedSection, AppliedSectionFrame
from ..models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow


class V1AppliedSectionSetObject:
    """Document object proxy that stores v1 AppliedSectionSet result summaries."""

    Type = "V1AppliedSectionSet"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_applied_section_set_properties(obj)

    def execute(self, obj):
        ensure_v1_applied_section_set_properties(obj)
        return


class ViewProviderV1AppliedSectionSet:
    """Simple view provider for v1 AppliedSectionSet result objects."""

    Type = "ViewProviderV1AppliedSectionSet"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
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
    _add_property(obj, "App::PropertyStringList", "RegionIds", "Resolved Context", "resolved region ids")
    _add_property(obj, "App::PropertyStringList", "AssemblyIds", "Resolved Context", "resolved assembly ids")
    _add_property(obj, "App::PropertyStringList", "TemplateIds", "Resolved Context", "resolved template ids")
    _add_property(obj, "App::PropertyIntegerList", "ComponentCounts", "Resolved Context", "component counts")
    _add_property(obj, "App::PropertyIntegerList", "DiagnosticCounts", "Diagnostics", "diagnostic counts")
    _add_property(obj, "App::PropertyStringList", "DiagnosticRows", "Diagnostics", "diagnostic summary rows")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Source", "source refs")

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
        obj = doc.addObject("App::FeaturePython", object_name)
        V1AppliedSectionSetObject(obj)
        try:
            ViewProviderV1AppliedSectionSet(obj.ViewObject)
        except Exception:
            pass
    else:
        V1AppliedSectionSetObject(obj)
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
    obj.RegionIds = [str(getattr(section_by_id.get(row.applied_section_id), "region_id", "") or "") for row in station_rows]
    obj.AssemblyIds = [str(getattr(section_by_id.get(row.applied_section_id), "assembly_id", "") or "") for row in station_rows]
    obj.TemplateIds = [str(getattr(section_by_id.get(row.applied_section_id), "template_id", "") or "") for row in station_rows]
    obj.ComponentCounts = [len(list(getattr(section_by_id.get(row.applied_section_id), "component_rows", []) or [])) for row in station_rows]
    obj.DiagnosticCounts = [len(list(getattr(section_by_id.get(row.applied_section_id), "diagnostic_rows", []) or [])) for row in station_rows]
    obj.DiagnosticRows = _diagnostic_rows(sections)
    obj.SourceRefs = [str(ref) for ref in list(getattr(applied_section_set, "source_refs", []) or []) if str(ref)]
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_applied_section_set(obj) -> AppliedSectionSet | None:
    """Build a summary AppliedSectionSet from a v1 result FreeCAD object."""

    if not _is_v1_applied_section_set(obj):
        return None
    ensure_v1_applied_section_set_properties(obj)
    station_values = _float_list(getattr(obj, "StationValues", []) or [])
    section_ids = list(getattr(obj, "AppliedSectionIds", []) or [])
    station_rows: list[AppliedSectionStationRow] = []
    sections: list[AppliedSection] = []
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
                station=float(station),
                surface_left_width=_float_value(getattr(obj, "SurfaceLeftWidths", []), index, 0.0),
                surface_right_width=_float_value(getattr(obj, "SurfaceRightWidths", []), index, 0.0),
                subgrade_depth=_float_value(getattr(obj, "SubgradeDepths", []), index, 0.0),
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
