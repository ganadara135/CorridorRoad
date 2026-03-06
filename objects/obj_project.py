# CorridorRoad/objects/obj_project.py
import FreeCAD as App
import math


def _find_first(doc, name_prefix: str):
    for o in doc.Objects:
        if o.Name.startswith(name_prefix):
            return o

    return None


def find_project(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        if o.Name.startswith("CorridorRoadProject"):
            return o
    return None


def _safe_scale(v, default: float = 1.0) -> float:
    try:
        x = float(v)
    except Exception:
        return float(default)
    if x <= 1e-12:
        return float(default)
    return float(x)


def get_length_scale(doc_or_project, default: float = 1.0) -> float:
    """
    Length scale = internal units per meter.
    1.0 means meter-native; 1000.0 means millimeter-like internal units.
    """
    if doc_or_project is None:
        return float(default)

    if hasattr(doc_or_project, "Document") and hasattr(doc_or_project, "LengthScale"):
        return _safe_scale(getattr(doc_or_project, "LengthScale", default), default=default)

    prj = find_project(doc_or_project) if hasattr(doc_or_project, "Objects") else None
    if prj is None:
        return float(default)
    return _safe_scale(getattr(prj, "LengthScale", default), default=default)


def meters_to_internal(doc_or_project, meters: float, default_scale: float = 1.0) -> float:
    return float(meters) * get_length_scale(doc_or_project, default=default_scale)


def _safe_float(v, default: float = 0.0) -> float:
    try:
        x = float(v)
    except Exception:
        return float(default)
    if not math.isfinite(x):
        return float(default)
    return float(x)


def _safe_angle_deg(v, default: float = 0.0) -> float:
    return _safe_float(v, default=default)


def _resolve_project(doc_or_project):
    if doc_or_project is None:
        return None

    # Direct project object
    try:
        if (
            str(getattr(doc_or_project, "Name", "") or "").startswith("CorridorRoadProject")
            or (getattr(doc_or_project, "Proxy", None) and getattr(doc_or_project.Proxy, "Type", "") == "CorridorRoadProject")
        ):
            return doc_or_project
    except Exception:
        pass

    # Document
    try:
        if hasattr(doc_or_project, "Objects"):
            return find_project(doc_or_project)
    except Exception:
        pass

    # Any object with Document link
    try:
        doc = getattr(doc_or_project, "Document", None)
        if doc is not None:
            return find_project(doc)
    except Exception:
        pass

    return None


def get_coordinate_setup(doc_or_project):
    """
    Coordinate setup dictionary.
    - CRS/EPSG metadata
    - world origin (E/N/Z)
    - local origin (X/Y/Z)
    - north rotation (deg)
    """
    prj = _resolve_project(doc_or_project)
    if prj is None:
        return {
            "CRSEPSG": "",
            "HorizontalDatum": "",
            "VerticalDatum": "",
            "ProjectOriginE": 0.0,
            "ProjectOriginN": 0.0,
            "ProjectOriginZ": 0.0,
            "LocalOriginX": 0.0,
            "LocalOriginY": 0.0,
            "LocalOriginZ": 0.0,
            "NorthRotationDeg": 0.0,
            "CoordSetupLocked": False,
            "CoordSetupStatus": "Uninitialized",
        }

    return {
        "CRSEPSG": str(getattr(prj, "CRSEPSG", "") or "").strip(),
        "HorizontalDatum": str(getattr(prj, "HorizontalDatum", "") or "").strip(),
        "VerticalDatum": str(getattr(prj, "VerticalDatum", "") or "").strip(),
        "ProjectOriginE": _safe_float(getattr(prj, "ProjectOriginE", 0.0), default=0.0),
        "ProjectOriginN": _safe_float(getattr(prj, "ProjectOriginN", 0.0), default=0.0),
        "ProjectOriginZ": _safe_float(getattr(prj, "ProjectOriginZ", 0.0), default=0.0),
        "LocalOriginX": _safe_float(getattr(prj, "LocalOriginX", 0.0), default=0.0),
        "LocalOriginY": _safe_float(getattr(prj, "LocalOriginY", 0.0), default=0.0),
        "LocalOriginZ": _safe_float(getattr(prj, "LocalOriginZ", 0.0), default=0.0),
        "NorthRotationDeg": _safe_angle_deg(getattr(prj, "NorthRotationDeg", 0.0), default=0.0),
        "CoordSetupLocked": bool(getattr(prj, "CoordSetupLocked", False)),
        "CoordSetupStatus": str(getattr(prj, "CoordSetupStatus", "Uninitialized") or "Uninitialized"),
    }


def local_to_world(doc_or_project, x: float, y: float, z: float):
    """
    Convert local model XYZ to world ENZ using project coordinate setup.
    Rotation is around +Z, CCW positive (degrees).
    """
    c = get_coordinate_setup(doc_or_project)
    th = math.radians(float(c["NorthRotationDeg"]))
    cs = math.cos(th)
    sn = math.sin(th)

    dx = float(x) - float(c["LocalOriginX"])
    dy = float(y) - float(c["LocalOriginY"])

    de = cs * dx - sn * dy
    dn = sn * dx + cs * dy

    e = float(c["ProjectOriginE"]) + de
    n = float(c["ProjectOriginN"]) + dn
    zz = float(c["ProjectOriginZ"]) + (float(z) - float(c["LocalOriginZ"]))
    return float(e), float(n), float(zz)


def world_to_local(doc_or_project, e: float, n: float, z: float):
    """
    Convert world ENZ to local model XYZ using project coordinate setup.
    """
    c = get_coordinate_setup(doc_or_project)
    th = math.radians(float(c["NorthRotationDeg"]))
    cs = math.cos(th)
    sn = math.sin(th)

    de = float(e) - float(c["ProjectOriginE"])
    dn = float(n) - float(c["ProjectOriginN"])

    dx = cs * de + sn * dn
    dy = -sn * de + cs * dn

    x = float(c["LocalOriginX"]) + dx
    y = float(c["LocalOriginY"]) + dy
    zz = float(c["LocalOriginZ"]) + (float(z) - float(c["ProjectOriginZ"]))
    return float(x), float(y), float(zz)


def local_to_world_vec(doc_or_project, p_local):
    e, n, z = local_to_world(doc_or_project, float(p_local.x), float(p_local.y), float(p_local.z))
    return App.Vector(e, n, z)


def world_to_local_vec(doc_or_project, p_world):
    x, y, z = world_to_local(doc_or_project, float(p_world.x), float(p_world.y), float(p_world.z))
    return App.Vector(x, y, z)


def ensure_project_properties(obj):
    if not hasattr(obj, "Group"):
        obj.addProperty("App::PropertyLinkList", "Group", "CorridorRoad", "Contained objects")

    if not hasattr(obj, "Version"):
        obj.addProperty("App::PropertyString", "Version", "CorridorRoad", "Project schema version")
        obj.Version = "0.4"
    if not hasattr(obj, "LengthScale"):
        obj.addProperty("App::PropertyFloat", "LengthScale", "CorridorRoad", "Length scale (internal units per meter)")
        obj.LengthScale = 1.0

    if not hasattr(obj, "CRSEPSG"):
        obj.addProperty("App::PropertyString", "CRSEPSG", "CoordinateSystem", "CRS code (e.g., EPSG:5186)")
        obj.CRSEPSG = ""
    if not hasattr(obj, "HorizontalDatum"):
        obj.addProperty("App::PropertyString", "HorizontalDatum", "CoordinateSystem", "Horizontal datum metadata")
        obj.HorizontalDatum = ""
    if not hasattr(obj, "VerticalDatum"):
        obj.addProperty("App::PropertyString", "VerticalDatum", "CoordinateSystem", "Vertical datum metadata")
        obj.VerticalDatum = ""
    if not hasattr(obj, "ProjectOriginE"):
        obj.addProperty("App::PropertyFloat", "ProjectOriginE", "CoordinateSystem", "World origin Easting")
        obj.ProjectOriginE = 0.0
    if not hasattr(obj, "ProjectOriginN"):
        obj.addProperty("App::PropertyFloat", "ProjectOriginN", "CoordinateSystem", "World origin Northing")
        obj.ProjectOriginN = 0.0
    if not hasattr(obj, "ProjectOriginZ"):
        obj.addProperty("App::PropertyFloat", "ProjectOriginZ", "CoordinateSystem", "World origin elevation")
        obj.ProjectOriginZ = 0.0
    if not hasattr(obj, "LocalOriginX"):
        obj.addProperty("App::PropertyFloat", "LocalOriginX", "CoordinateSystem", "Local model origin X")
        obj.LocalOriginX = 0.0
    if not hasattr(obj, "LocalOriginY"):
        obj.addProperty("App::PropertyFloat", "LocalOriginY", "CoordinateSystem", "Local model origin Y")
        obj.LocalOriginY = 0.0
    if not hasattr(obj, "LocalOriginZ"):
        obj.addProperty("App::PropertyFloat", "LocalOriginZ", "CoordinateSystem", "Local model origin Z")
        obj.LocalOriginZ = 0.0
    if not hasattr(obj, "NorthRotationDeg"):
        obj.addProperty("App::PropertyFloat", "NorthRotationDeg", "CoordinateSystem", "North rotation (deg, CCW)")
        obj.NorthRotationDeg = 0.0
    if not hasattr(obj, "CoordSetupLocked"):
        obj.addProperty("App::PropertyBool", "CoordSetupLocked", "CoordinateSystem", "Lock coordinate setup edits")
        obj.CoordSetupLocked = False
    if not hasattr(obj, "CoordSetupStatus"):
        obj.addProperty("App::PropertyString", "CoordSetupStatus", "CoordinateSystem", "Coordinate setup status")
        obj.CoordSetupStatus = "Uninitialized"

    if not hasattr(obj, "Terrain"):
        obj.addProperty("App::PropertyLink", "Terrain", "CorridorRoad", "Link to EG terrain object")
    if not hasattr(obj, "Alignment"):
        obj.addProperty("App::PropertyLink", "Alignment", "CorridorRoad", "Link to horizontal alignment object")
    if not hasattr(obj, "Stationing"):
        obj.addProperty("App::PropertyLink", "Stationing", "CorridorRoad", "Link to stationing object")
    if not hasattr(obj, "Centerline3D"):
        obj.addProperty("App::PropertyLink", "Centerline3D", "CorridorRoad", "Link to 3D centerline object")
    if not hasattr(obj, "Centerline3DDisplay"):
        obj.addProperty("App::PropertyLink", "Centerline3DDisplay", "CorridorRoad", "Link to 3D centerline display object")
    if not hasattr(obj, "AssemblyTemplate"):
        obj.addProperty("App::PropertyLink", "AssemblyTemplate", "CorridorRoad", "Link to assembly template object")
    if not hasattr(obj, "SectionSet"):
        obj.addProperty("App::PropertyLink", "SectionSet", "CorridorRoad", "Link to section set object")
    if not hasattr(obj, "CorridorLoft"):
        obj.addProperty("App::PropertyLink", "CorridorLoft", "CorridorRoad", "Link to corridor loft object")
    if not hasattr(obj, "DesignGradingSurface"):
        obj.addProperty("App::PropertyLink", "DesignGradingSurface", "CorridorRoad", "Link to design grading surface object")
    if not hasattr(obj, "DesignTerrain"):
        obj.addProperty("App::PropertyLink", "DesignTerrain", "CorridorRoad", "Link to design terrain object")
    if not hasattr(obj, "CutFillCalc"):
        obj.addProperty("App::PropertyLink", "CutFillCalc", "CorridorRoad", "Link to cut/fill calc object")


class CorridorRoadProject:
    """
    Project container:
    - stores Links to key objects
    - optionally groups child objects via Group property (DocumentObjectGroup)
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "CorridorRoadProject"
        ensure_project_properties(obj)

    def execute(self, obj):
        ensure_project_properties(obj)
        # Container does not generate shape.
        return

    @staticmethod
    def adopt(obj_project, child):
        """Put child into project.Group if not already there."""
        if child is None:
            return

        group = list(getattr(obj_project, "Group", []) or [])
        if child not in group:
            group.append(child)
            obj_project.Group = group

    @staticmethod
    def auto_link(doc, obj_project):
        """Try to auto-detect first alignment/stationing/profile and link them."""
        if doc is None:
            return

        if obj_project.Alignment is None:
            a = _find_first(doc, "HorizontalAlignment")
            if a is not None:
                obj_project.Alignment = a

        if obj_project.Stationing is None:
            s = _find_first(doc, "Stationing")
            if s is not None:
                obj_project.Stationing = s

        if hasattr(obj_project, "Centerline3D") and obj_project.Centerline3D is None:
            c = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "Centerline3D":
                    c = o
                    break
                if o.Name.startswith("Centerline3D") and (not o.Name.startswith("Centerline3DDisplay")):
                    c = o
                    break
            if c is not None:
                obj_project.Centerline3D = c

        if hasattr(obj_project, "Centerline3DDisplay") and obj_project.Centerline3DDisplay is None:
            d = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "Centerline3DDisplay":
                    d = o
                    break
                if o.Name.startswith("Centerline3DDisplay"):
                    d = o
                    break
            if d is not None:
                obj_project.Centerline3DDisplay = d

        if hasattr(obj_project, "AssemblyTemplate") and obj_project.AssemblyTemplate is None:
            a = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "AssemblyTemplate":
                    a = o
                    break
                if o.Name.startswith("AssemblyTemplate"):
                    a = o
                    break
            if a is not None:
                obj_project.AssemblyTemplate = a

        if hasattr(obj_project, "SectionSet") and obj_project.SectionSet is None:
            s = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "SectionSet":
                    s = o
                    break
                if o.Name.startswith("SectionSet"):
                    s = o
                    break
            if s is not None:
                obj_project.SectionSet = s

        if hasattr(obj_project, "CorridorLoft") and obj_project.CorridorLoft is None:
            c = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "CorridorLoft":
                    c = o
                    break
                if o.Name.startswith("CorridorLoft"):
                    c = o
                    break
            if c is not None:
                obj_project.CorridorLoft = c

        if hasattr(obj_project, "DesignGradingSurface") and obj_project.DesignGradingSurface is None:
            g = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "DesignGradingSurface":
                    g = o
                    break
                if o.Name.startswith("DesignGradingSurface"):
                    g = o
                    break
            if g is not None:
                obj_project.DesignGradingSurface = g

        if hasattr(obj_project, "DesignTerrain") and obj_project.DesignTerrain is None:
            d = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "DesignTerrain":
                    d = o
                    break
                if o.Name.startswith("DesignTerrain"):
                    d = o
                    break
            if d is not None:
                obj_project.DesignTerrain = d

        if hasattr(obj_project, "CutFillCalc") and obj_project.CutFillCalc is None:
            s = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "CutFillCalc":
                    s = o
                    break
                if o.Name.startswith("CutFillCalc"):
                    s = o
                    break
            if s is not None:
                obj_project.CutFillCalc = s
