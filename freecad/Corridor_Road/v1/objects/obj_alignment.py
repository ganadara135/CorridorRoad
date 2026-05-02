"""FreeCAD source object for v1 alignment models."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
try:
    import Part
except Exception:  # pragma: no cover - Part is not available in plain Python.
    Part = None

from ..models.source.alignment_model import AlignmentElement, AlignmentModel


class V1AlignmentObject:
    """Document object proxy that stores a v1 AlignmentModel contract."""

    Type = "V1Alignment"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_alignment_properties(obj)

    def execute(self, obj):
        ensure_v1_alignment_properties(obj)
        try:
            obj.Shape = build_v1_alignment_shape(obj)
        except Exception:
            if Part is not None:
                try:
                    obj.Shape = Part.Shape()
                except Exception:
                    pass
        return


class ViewProviderV1Alignment:
    """Simple display provider for v1 alignment source geometry."""

    Type = "ViewProviderV1Alignment"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.LineColor = (0.16, 0.62, 1.0)
            vobj.PointColor = (1.0, 0.82, 0.24)
            vobj.LineWidth = 3.0
            vobj.PointSize = 5.0
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("alignment.svg")
        except Exception:
            return ""


def ensure_v1_alignment_properties(obj) -> None:
    """Ensure the FreeCAD object has the minimal v1 alignment properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "AlignmentId", "CorridorRoad", "v1 alignment id")
    _add_property(obj, "App::PropertyString", "AlignmentKind", "CorridorRoad", "v1 alignment kind")
    _add_property(obj, "App::PropertyStringList", "ElementIds", "Geometry", "alignment element ids")
    _add_property(obj, "App::PropertyStringList", "ElementKinds", "Geometry", "alignment element kinds")
    _add_property(obj, "App::PropertyFloatList", "StationStarts", "Geometry", "element station starts")
    _add_property(obj, "App::PropertyFloatList", "StationEnds", "Geometry", "element station ends")
    _add_property(obj, "App::PropertyFloatList", "ElementLengths", "Geometry", "element lengths")
    _add_property(obj, "App::PropertyStringList", "XValueRows", "Geometry", "comma-separated element x values")
    _add_property(obj, "App::PropertyStringList", "YValueRows", "Geometry", "comma-separated element y values")
    _add_property(obj, "App::PropertyVectorList", "IPPoints", "AlignmentInput", "intersection point rows")
    _add_property(obj, "App::PropertyFloatList", "CurveRadii", "AlignmentInput", "circular curve radius at each IP")
    _add_property(obj, "App::PropertyFloatList", "TransitionLengths", "AlignmentInput", "transition curve length at each IP")
    _add_property(obj, "App::PropertyBool", "UseTransitionCurves", "AlignmentInput", "enable transition curve intent")
    _add_property(obj, "App::PropertyInteger", "SpiralSegments", "AlignmentInput", "transition curve approximation segment count")
    _add_property(obj, "App::PropertyFloat", "DesignSpeedKph", "Criteria", "design speed")
    _add_property(obj, "App::PropertyFloat", "SuperelevationPct", "Criteria", "superelevation")
    _add_property(obj, "App::PropertyFloat", "SideFriction", "Criteria", "side friction")
    _add_property(obj, "App::PropertyFloat", "MinRadius", "Criteria", "minimum radius override")
    _add_property(obj, "App::PropertyFloat", "MinTangentLength", "Criteria", "minimum tangent length")
    _add_property(obj, "App::PropertyFloat", "MinTransitionLength", "Criteria", "minimum transition length")
    _add_property(obj, "App::PropertyStringList", "CriteriaMessages", "Criteria", "criteria messages")
    _add_property(obj, "App::PropertyString", "CriteriaStatus", "Criteria", "criteria status")
    _add_property(obj, "App::PropertyString", "CriteriaStandard", "Criteria", "criteria standard")
    _add_property(obj, "App::PropertyFloat", "TotalLength", "Geometry", "compiled alignment length")
    _add_property(obj, "App::PropertyInteger", "CompiledPointCount", "Geometry", "compiled XY display point count")
    _add_property(obj, "App::PropertyInteger", "CompiledEdgeCount", "Geometry", "compiled display edge count")
    _add_property(obj, "App::PropertyInteger", "CompiledCurveElementCount", "Geometry", "compiled curve element count")
    _add_property(obj, "App::PropertyInteger", "CompiledTransitionElementCount", "Geometry", "compiled transition element count")
    _add_property(obj, "App::PropertyString", "CompiledGeometryStatus", "Geometry", "compiled display geometry status")
    _add_property(obj, "Part::PropertyPartShape", "Shape", "Geometry", "compiled alignment display shape")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1Alignment"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "AlignmentId", "") or ""):
        obj.AlignmentId = f"alignment:{str(getattr(obj, 'Name', '') or 'v1-alignment')}"
    if not str(getattr(obj, "AlignmentKind", "") or ""):
        obj.AlignmentKind = "road_centerline"
    if int(getattr(obj, "SpiralSegments", 0) or 0) <= 0:
        obj.SpiralSegments = 16
    if float(getattr(obj, "DesignSpeedKph", 0.0) or 0.0) <= 0.0:
        obj.DesignSpeedKph = 60.0
    if float(getattr(obj, "SuperelevationPct", 0.0) or 0.0) <= 0.0:
        obj.SuperelevationPct = 8.0
    if float(getattr(obj, "SideFriction", 0.0) or 0.0) <= 0.0:
        obj.SideFriction = 0.15
    if float(getattr(obj, "MinTangentLength", 0.0) or 0.0) <= 0.0:
        obj.MinTangentLength = 20.0
    if float(getattr(obj, "MinTransitionLength", 0.0) or 0.0) <= 0.0:
        obj.MinTransitionLength = 20.0
    if not str(getattr(obj, "CriteriaStandard", "") or ""):
        obj.CriteriaStandard = "KDS"
    if not str(getattr(obj, "CriteriaStatus", "") or ""):
        obj.CriteriaStatus = "OK"
    if not str(getattr(obj, "CompiledGeometryStatus", "") or ""):
        obj.CompiledGeometryStatus = "pending"


def create_sample_v1_alignment(document=None, *, project=None, label: str = "Main Alignment"):
    """Create a practical sample v1 alignment source object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 alignment creation.")

    try:
        obj = doc.addObject("Part::FeaturePython", "V1Alignment")
    except Exception:
        obj = doc.addObject("App::FeaturePython", "V1Alignment")
    V1AlignmentObject(obj)
    try:
        ViewProviderV1Alignment(obj.ViewObject)
    except Exception:
        pass
    obj.Label = label
    obj.ProjectId = _project_id(project)
    obj.AlignmentId = f"alignment:{str(getattr(obj, 'Name', '') or 'main')}"
    obj.AlignmentKind = "road_centerline"
    obj.ElementIds = [
        f"{obj.AlignmentId}:tangent:1",
        f"{obj.AlignmentId}:sampled-curve:2",
        f"{obj.AlignmentId}:tangent:3",
    ]
    obj.ElementKinds = ["tangent", "sampled_curve", "tangent"]
    obj.StationStarts = [0.0, 60.0, 120.0]
    obj.StationEnds = [60.0, 120.0, 180.0]
    obj.ElementLengths = [60.0, 60.0, 60.0]
    obj.XValueRows = [
        "0.0,60.0",
        "60.0,90.0,120.0",
        "120.0,180.0",
    ]
    obj.YValueRows = [
        "0.0,0.0",
        "0.0,18.0,18.0",
        "18.0,18.0",
    ]
    obj.IPPoints = [
        App.Vector(0.0, 0.0, 0.0),
        App.Vector(60.0, 0.0, 0.0),
        App.Vector(120.0, 18.0, 0.0),
        App.Vector(180.0, 18.0, 0.0),
    ]
    obj.CurveRadii = [0.0, 120.0, 120.0, 0.0]
    obj.TransitionLengths = [0.0, 20.0, 20.0, 0.0]
    obj.UseTransitionCurves = True
    obj.SpiralSegments = 16
    obj.DesignSpeedKph = 60.0
    obj.SuperelevationPct = 8.0
    obj.SideFriction = 0.15
    obj.MinRadius = 0.0
    obj.MinTangentLength = 20.0
    obj.MinTransitionLength = 20.0
    obj.CriteriaStandard = "KDS"
    obj.CriteriaStatus = "OK"
    obj.CriteriaMessages = []
    obj.TotalLength = 180.0
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


def find_v1_alignment(document, preferred_alignment=None):
    """Find a v1 alignment object in a document, honoring an explicit preferred object."""

    if _is_v1_alignment(preferred_alignment):
        return preferred_alignment
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_alignment(obj):
            return obj
    return None


def build_v1_alignment_shape(obj):
    """Build a FreeCAD display shape from compiled v1 alignment element XY rows."""

    if Part is None:
        return None
    ensure_v1_alignment_properties(obj)
    edges = []
    display_points = []
    point_count = 0
    curve_count = 0
    transition_count = 0
    kinds = list(getattr(obj, "ElementKinds", []) or [])
    x_rows = list(getattr(obj, "XValueRows", []) or [])
    y_rows = list(getattr(obj, "YValueRows", []) or [])
    count = max(len(kinds), len(x_rows), len(y_rows))
    for index in range(count):
        kind = str(kinds[index] if index < len(kinds) else "" or "tangent")
        if kind in {"sampled_curve", "circular_curve"}:
            curve_count += 1
        if kind == "transition_curve":
            transition_count += 1
        x_values = _csv_float_row(x_rows[index]) if index < len(x_rows) else []
        y_values = _csv_float_row(y_rows[index]) if index < len(y_rows) else []
        points = _xy_points(x_values, y_values)
        point_count += len(points)
        display_points = _append_unique_points(display_points, points)

    edge = _display_edge_from_points(display_points)
    if edge is not None:
        edges.append(edge)

    try:
        obj.CompiledPointCount = int(point_count)
        obj.CompiledEdgeCount = int(len(edges))
        obj.CompiledCurveElementCount = int(curve_count)
        obj.CompiledTransitionElementCount = int(transition_count)
        obj.CompiledGeometryStatus = "ok" if edges else "empty"
    except Exception:
        pass

    if not edges:
        return Part.Shape()
    if len(edges) == 1:
        return edges[0]
    return Part.Compound(edges)


def to_alignment_model(obj) -> AlignmentModel | None:
    """Convert one v1 FreeCAD alignment source object to an AlignmentModel."""

    if not _is_v1_alignment(obj):
        return None
    ensure_v1_alignment_properties(obj)
    alignment_id = str(getattr(obj, "AlignmentId", "") or getattr(obj, "Name", "") or "alignment:v1")
    element_ids = list(getattr(obj, "ElementIds", []) or [])
    kinds = list(getattr(obj, "ElementKinds", []) or [])
    starts = _float_list(getattr(obj, "StationStarts", []) or [])
    ends = _float_list(getattr(obj, "StationEnds", []) or [])
    lengths = _float_list(getattr(obj, "ElementLengths", []) or [])
    x_rows = list(getattr(obj, "XValueRows", []) or [])
    y_rows = list(getattr(obj, "YValueRows", []) or [])
    count = max(len(element_ids), len(kinds), len(starts), len(ends), len(x_rows), len(y_rows))

    geometry_sequence: list[AlignmentElement] = []
    for index in range(count):
        station_start = starts[index] if index < len(starts) else 0.0
        station_end = ends[index] if index < len(ends) else station_start
        x_values = _csv_float_row(x_rows[index]) if index < len(x_rows) else []
        y_values = _csv_float_row(y_rows[index]) if index < len(y_rows) else []
        length = lengths[index] if index < len(lengths) else max(0.0, station_end - station_start)
        element_id = element_ids[index] if index < len(element_ids) and element_ids[index] else f"{alignment_id}:element:{index + 1}"
        geometry_sequence.append(
            AlignmentElement(
                element_id=str(element_id),
                kind=str(kinds[index] if index < len(kinds) and kinds[index] else "tangent"),
                station_start=float(station_start),
                station_end=float(station_end),
                length=float(length),
                geometry_payload={
                    "x_values": x_values,
                    "y_values": y_values,
                    "style_role": str(kinds[index] if index < len(kinds) and kinds[index] else "tangent"),
                },
            )
        )

    return AlignmentModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        alignment_id=alignment_id,
        label=str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "v1 Alignment"),
        alignment_kind=str(getattr(obj, "AlignmentKind", "") or "road_centerline"),
        source_refs=[str(getattr(obj, "Name", "") or alignment_id)],
        geometry_sequence=geometry_sequence,
    )


def _is_v1_alignment(obj) -> bool:
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


def _csv_float_row(text: str) -> list[float]:
    rows = []
    for token in str(text or "").split(","):
        try:
            rows.append(float(token.strip()))
        except Exception:
            pass
    return rows


def _xy_points(x_values: list[float], y_values: list[float]):
    if App is None:
        return []
    points = []
    for x, y in zip(list(x_values or []), list(y_values or [])):
        try:
            points.append(App.Vector(float(x), float(y), 0.0))
        except Exception:
            continue
    return points


def _append_unique_points(existing, points):
    output = list(existing or [])
    for point in list(points or []):
        if output and (point - output[-1]).Length <= 1.0e-9:
            continue
        output.append(point)
    return output


def _display_edge_from_points(points):
    clean = _append_unique_points([], points)
    if len(clean) < 2 or Part is None:
        return None
    if len(clean) == 2:
        try:
            return Part.makeLine(clean[0], clean[1])
        except Exception:
            return None
    try:
        curve = Part.BSplineCurve()
        curve.interpolate(clean)
        return curve.toShape()
    except Exception:
        return _polyline_compound_edge(clean)


def _polyline_compound_edge(points):
    edges = []
    for start, end in zip(list(points or []), list(points or [])[1:]):
        try:
            if (end - start).Length <= 1.0e-9:
                continue
            edges.append(Part.makeLine(start, end))
        except Exception:
            continue
    if not edges:
        return None
    if len(edges) == 1:
        return edges[0]
    try:
        return Part.Compound(edges)
    except Exception:
        return edges[0]


def _project_id(project) -> str:
    if project is None:
        return "corridorroad-v1"
    return str(getattr(project, "Name", "") or getattr(project, "Label", "") or "corridorroad-v1")
