"""FreeCAD source object for v1 profile models."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
try:
    import Part
except Exception:  # pragma: no cover - Part is not available in plain Python.
    Part = None

from ..models.source.profile_model import (
    ProfileControlPoint,
    ProfileModel,
    VerticalCurveRow,
)
from .obj_alignment import (
    create_sample_v1_alignment,
    find_v1_alignment,
    to_alignment_model,
)
from ..services.evaluation import AlignmentEvaluationService, ProfileEvaluationService


class V1ProfileObject:
    """Document object proxy that stores a v1 ProfileModel contract."""

    Type = "V1Profile"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_profile_properties(obj)

    def execute(self, obj):
        ensure_v1_profile_properties(obj)
        try:
            obj.Shape = build_v1_profile_shape(obj)
        except Exception:
            if Part is not None:
                try:
                    obj.Shape = Part.Shape()
                except Exception:
                    pass
        return


class ViewProviderV1Profile:
    """Simple display provider for v1 finished-grade profile geometry."""

    Type = "ViewProviderV1Profile"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.LineColor = (0.95, 0.36, 0.14)
            vobj.PointColor = (1.0, 0.88, 0.30)
            vobj.LineWidth = 4.0
            vobj.PointSize = 5.0
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("profiles.svg")
        except Exception:
            return ""


def ensure_v1_profile_properties(obj) -> None:
    """Ensure the FreeCAD object has the minimal v1 profile properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "ProfileId", "CorridorRoad", "v1 profile id")
    _add_property(obj, "App::PropertyString", "AlignmentId", "CorridorRoad", "linked v1 alignment id")
    _add_property(obj, "App::PropertyString", "ProfileKind", "CorridorRoad", "v1 profile kind")
    _add_property(obj, "App::PropertyStringList", "ControlPointIds", "Controls", "profile control ids")
    _add_property(obj, "App::PropertyFloatList", "ControlStations", "Controls", "profile control stations")
    _add_property(obj, "App::PropertyFloatList", "ControlElevations", "Controls", "profile control elevations")
    _add_property(obj, "App::PropertyStringList", "ControlKinds", "Controls", "profile control kinds")
    _add_property(obj, "App::PropertyStringList", "VerticalCurveIds", "Vertical Curves", "vertical curve ids")
    _add_property(obj, "App::PropertyStringList", "VerticalCurveKinds", "Vertical Curves", "vertical curve kinds")
    _add_property(obj, "App::PropertyFloatList", "VerticalCurveStationStarts", "Vertical Curves", "curve start stations")
    _add_property(obj, "App::PropertyFloatList", "VerticalCurveStationEnds", "Vertical Curves", "curve end stations")
    _add_property(obj, "App::PropertyFloatList", "VerticalCurveLengths", "Vertical Curves", "curve lengths")
    _add_property(obj, "App::PropertyFloatList", "VerticalCurveParameters", "Vertical Curves", "curve parameters")
    _add_property(obj, "App::PropertyFloat", "DisplaySampleInterval", "Display", "profile display sample interval")
    _add_property(obj, "App::PropertyInteger", "DisplayPointCount", "Display", "profile display point count")
    _add_property(obj, "App::PropertyString", "DisplayStatus", "Display", "profile display build status")
    _add_property(obj, "Part::PropertyPartShape", "Shape", "Display", "3D finished-grade profile display shape")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1Profile"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "ProfileId", "") or ""):
        obj.ProfileId = f"profile:{str(getattr(obj, 'Name', '') or 'v1-profile')}"
    if not str(getattr(obj, "ProfileKind", "") or ""):
        obj.ProfileKind = "finished_grade"
    if float(getattr(obj, "DisplaySampleInterval", 0.0) or 0.0) <= 0.0:
        obj.DisplaySampleInterval = 10.0
    if not str(getattr(obj, "DisplayStatus", "") or ""):
        obj.DisplayStatus = "pending"


def create_sample_v1_profile(
    document=None,
    *,
    project=None,
    alignment=None,
    label: str = "Finished Grade Profile",
    create_alignment_if_missing: bool = True,
):
    """Create a practical sample v1 profile source object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 profile creation.")

    alignment_obj = alignment or find_v1_alignment(doc)
    if alignment_obj is None and create_alignment_if_missing:
        alignment_obj = create_sample_v1_alignment(doc, project=project)
    alignment_model = to_alignment_model(alignment_obj) if alignment_obj is not None else None
    alignment_id = str(getattr(alignment_model, "alignment_id", "") or "")

    try:
        obj = doc.addObject("Part::FeaturePython", "V1Profile")
    except Exception:
        obj = doc.addObject("App::FeaturePython", "V1Profile")
    V1ProfileObject(obj)
    try:
        ViewProviderV1Profile(obj.ViewObject)
    except Exception:
        pass
    obj.Label = label
    obj.ProjectId = _project_id(project)
    obj.ProfileId = f"profile:{str(getattr(obj, 'Name', '') or 'fg')}"
    obj.AlignmentId = alignment_id
    obj.ProfileKind = "finished_grade"
    obj.ControlPointIds = [
        f"{obj.ProfileId}:pvi:1",
        f"{obj.ProfileId}:pvi:2",
        f"{obj.ProfileId}:pvi:3",
    ]
    obj.ControlStations = [0.0, 90.0, 180.0]
    obj.ControlElevations = [12.0, 15.0, 13.5]
    obj.ControlKinds = ["grade_break", "pvi", "grade_break"]
    obj.VerticalCurveIds = [f"{obj.ProfileId}:curve:1"]
    obj.VerticalCurveKinds = ["parabolic_vertical_curve"]
    obj.VerticalCurveStationStarts = [75.0]
    obj.VerticalCurveStationEnds = [105.0]
    obj.VerticalCurveLengths = [30.0]
    obj.VerticalCurveParameters = [-0.05]
    try:
        obj.touch()
    except Exception:
        pass

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def build_v1_profile_shape(obj):
    """Build a 3D FG profile display shape along the linked v1 alignment."""

    if Part is None or App is None:
        return None
    ensure_v1_profile_properties(obj)
    profile_model = to_profile_model(obj)
    if profile_model is None:
        _set_display_status(obj, "no_profile", 0)
        return Part.Shape()
    document = getattr(obj, "Document", None)
    alignment_obj = _find_linked_alignment(document, str(getattr(obj, "AlignmentId", "") or ""))
    alignment_model = to_alignment_model(alignment_obj) if alignment_obj is not None else None
    if alignment_model is None:
        _set_display_status(obj, "no_alignment", 0)
        return Part.Shape()

    stations = _profile_display_stations(profile_model, float(getattr(obj, "DisplaySampleInterval", 10.0) or 10.0))
    if len(stations) < 2:
        _set_display_status(obj, "not_enough_stations", 0)
        return Part.Shape()

    alignment_service = AlignmentEvaluationService()
    profile_service = ProfileEvaluationService()
    points = []
    for station in stations:
        alignment_result = alignment_service.evaluate_station(alignment_model, float(station))
        profile_result = profile_service.evaluate_station(profile_model, float(station))
        if alignment_result.status != "ok" or profile_result.status != "ok":
            continue
        points.append(App.Vector(float(alignment_result.x), float(alignment_result.y), float(profile_result.elevation)))

    if len(points) < 2:
        _set_display_status(obj, "empty", len(points))
        return Part.Shape()
    try:
        shape = Part.makePolygon(points)
    except Exception:
        edges = []
        for start, end in zip(points, points[1:]):
            if (end - start).Length > 1.0e-9:
                edges.append(Part.makeLine(start, end))
        shape = Part.Compound(edges) if edges else Part.Shape()
    _set_display_status(obj, "ok", len(points))
    return shape


def find_v1_profile(document, preferred_profile=None):
    """Find a v1 profile object in a document, honoring an explicit preferred object."""

    if _is_v1_profile(preferred_profile):
        return preferred_profile
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_profile(obj):
            return obj
    return None


def _find_linked_alignment(document, alignment_id: str):
    if document is None:
        return None
    target = str(alignment_id or "")
    fallback = None
    for obj in list(getattr(document, "Objects", []) or []):
        if not _is_v1_alignment_object(obj):
            continue
        if fallback is None:
            fallback = obj
        if target and str(getattr(obj, "AlignmentId", "") or "") == target:
            return obj
    return fallback


def _profile_display_stations(profile: ProfileModel, interval: float) -> list[float]:
    controls = sorted(list(profile.control_rows or []), key=lambda row: float(row.station))
    if len(controls) < 2:
        return []
    start = float(controls[0].station)
    end = float(controls[-1].station)
    step = max(0.1, float(interval or 10.0))
    stations = {round(start, 6), round(end, 6)}
    current = start
    while current < end - 1.0e-9:
        current += step
        stations.add(round(min(current, end), 6))
    for control in controls:
        stations.add(round(float(control.station), 6))
    for curve in list(profile.vertical_curve_rows or []):
        stations.add(round(float(curve.station_start), 6))
        stations.add(round(float(curve.station_end), 6))
        stations.add(round(0.5 * (float(curve.station_start) + float(curve.station_end)), 6))
    return [station for station in sorted(stations) if start - 1.0e-9 <= station <= end + 1.0e-9]


def _set_display_status(obj, status: str, point_count: int) -> None:
    try:
        obj.DisplayStatus = str(status or "")
        obj.DisplayPointCount = int(point_count or 0)
    except Exception:
        pass


def to_profile_model(obj) -> ProfileModel | None:
    """Convert one v1 FreeCAD profile source object to a ProfileModel."""

    if not _is_v1_profile(obj):
        return None
    ensure_v1_profile_properties(obj)
    profile_id = str(getattr(obj, "ProfileId", "") or getattr(obj, "Name", "") or "profile:v1")
    control_ids = list(getattr(obj, "ControlPointIds", []) or [])
    control_stations = _float_list(getattr(obj, "ControlStations", []) or [])
    control_elevations = _float_list(getattr(obj, "ControlElevations", []) or [])
    control_kinds = list(getattr(obj, "ControlKinds", []) or [])
    control_count = min(len(control_stations), len(control_elevations))
    control_rows = [
        ProfileControlPoint(
            control_point_id=(
                str(control_ids[index])
                if index < len(control_ids) and control_ids[index]
                else f"{profile_id}:pvi:{index + 1}"
            ),
            station=float(control_stations[index]),
            elevation=float(control_elevations[index]),
            kind=str(control_kinds[index] if index < len(control_kinds) and control_kinds[index] else "pvi"),
        )
        for index in range(control_count)
    ]

    curve_ids = list(getattr(obj, "VerticalCurveIds", []) or [])
    curve_kinds = list(getattr(obj, "VerticalCurveKinds", []) or [])
    starts = _float_list(getattr(obj, "VerticalCurveStationStarts", []) or [])
    ends = _float_list(getattr(obj, "VerticalCurveStationEnds", []) or [])
    lengths = _float_list(getattr(obj, "VerticalCurveLengths", []) or [])
    parameters = _float_list(getattr(obj, "VerticalCurveParameters", []) or [])
    curve_count = min(len(starts), len(ends))
    vertical_curve_rows = [
        VerticalCurveRow(
            vertical_curve_id=(
                str(curve_ids[index])
                if index < len(curve_ids) and curve_ids[index]
                else f"{profile_id}:curve:{index + 1}"
            ),
            kind=str(
                curve_kinds[index]
                if index < len(curve_kinds) and curve_kinds[index]
                else "parabolic_vertical_curve"
            ),
            station_start=float(starts[index]),
            station_end=float(ends[index]),
            curve_length=(
                float(lengths[index])
                if index < len(lengths)
                else max(0.0, float(ends[index]) - float(starts[index]))
            ),
            curve_parameter=float(parameters[index]) if index < len(parameters) else 0.0,
        )
        for index in range(curve_count)
    ]

    return ProfileModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        profile_id=profile_id,
        alignment_id=str(getattr(obj, "AlignmentId", "") or ""),
        label=str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "v1 Profile"),
        profile_kind=str(getattr(obj, "ProfileKind", "") or "finished_grade"),
        source_refs=[str(getattr(obj, "Name", "") or profile_id)],
        control_rows=control_rows,
        vertical_curve_rows=vertical_curve_rows,
    )


def _is_v1_profile(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1Profile":
        return True
    proxy = getattr(obj, "Proxy", None)
    if str(getattr(proxy, "Type", "") or "") == "V1Profile":
        return True
    return str(getattr(obj, "Name", "") or "").startswith("V1Profile")


def _is_v1_alignment_object(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1Alignment":
        return True
    proxy = getattr(obj, "Proxy", None)
    if str(getattr(proxy, "Type", "") or "") == "V1Alignment":
        return True
    return str(getattr(obj, "Name", "") or "").startswith("V1Alignment")


def _add_property(obj, type_name: str, name: str, group: str, doc: str) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty(type_name, name, group, doc)
    except Exception:
        pass


def _float_list(values) -> list[float]:
    rows = []
    for value in list(values or []):
        try:
            rows.append(float(value))
        except Exception:
            rows.append(0.0)
    return rows


def _project_id(project) -> str:
    if project is None:
        return "corridorroad-v1"
    return str(getattr(project, "Name", "") or getattr(project, "Label", "") or "corridorroad-v1")
